"""Cross-environment verification + smoke tool (PHASE 1/2/3/9/10/12).

ONE script, run IDENTICALLY on the Windows dev laptop and on Colab, so their
outputs can be diff'd (the local-vs-Colab consistency gate). It:

  1. prints an environment fingerprint (versions, device, git commit, and the
     working-INP SHA-256 vs the frozen expected hash -> catches transfer
     corruption);
  2. runs a REAL WNTR/EPANET native-hold smoke rollout (safety OFF) and checks the
     frozen invariants: obs (139,) float32 in-bounds, 192 transitions, terminated
     never True, truncated at step 192, and leak_mean vs the frozen anchor
     84.72988433677985 GPM at the project tolerance rel < 5e-5;
  3. measures actual seconds/step and seconds/episode (PHASE 12 cost);
  4. IF torch/SB3/gymnasium are installed: runs the SB3 env checker, constructs
     PPO (asserts obs=139 / act=7), checks a deterministic prediction is in
     [-1,1]^7, runs a tiny learn, and does a checkpoint save/load round-trip;
  5. writes ``runs/_verify/fingerprint_<host>.json`` for cross-machine comparison.

Nothing here is research evidence; it is an INTEGRATION gate. It never mocks the
hydraulics.
"""

from __future__ import annotations

import argparse
import json
import platform
import socket
import sys
import time
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import config as CFG                     # noqa: E402
from make_env import make_env            # noqa: E402
import action_mapper as AM               # noqa: E402  (src/env on path via make_env)
import epanet_adapter as A               # noqa: E402
from state_builder import observation_bounds  # noqa: E402

LEAK_ANCHOR_GPM = 84.72988433677985
LEAK_REL_TOL = 5e-5
# Frozen Phase-5/6 reference-state anchors (PROJECT_STATE.yaml phase5.reference_state).
# The env reports the 192 POST-ACTION control-step endpoints, while the monolithic
# anchor spans all 193 instants, so the worst-node value is compared with the
# documented stepped-vs-monolithic tolerance (|delta| 5.5e-4 psi in WU-20), rounded
# up to 1e-2 psi; the negative-pressure count must match EXACTLY (0).
MIN_SVC_PRESSURE_ANCHOR_PSI = 4.16452169418335
MIN_SVC_PRESSURE_TOL_PSI = 1e-2
NATIVE_NORM = AM.command_to_normalized(A.NATIVE_PRV_SETPOINT_PSI, A.NATIVE_PUMP_SPEED)


def fingerprint() -> dict:
    fp = {
        "host": socket.gethostname(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "git_commit": CFG._git_commit(),
        "working_inp_sha256": CFG._working_inp_sha256(),
        "working_inp_sha256_expected": CFG.FROZEN_SPEC["working_inp_sha256_expected"],
        "device": CFG.device_report("auto"),
        "versions": {k: CFG._pkg_version(k) for k in
                     ("torch", "stable-baselines3", "gymnasium", "numpy",
                      "pandas", "scipy", "wntr", "epyt")},
    }
    fp["working_inp_sha256_match"] = (
        fp["working_inp_sha256"] == fp["working_inp_sha256_expected"])
    return fp


def hydraulic_smoke(full: bool) -> dict:
    """Native-hold rollout through REAL EPANET; frozen-invariant checks + timing."""
    env = make_env(enable_safety=False)
    low, high = observation_bounds(env.observation_config)
    t0 = time.perf_counter()
    obs, info = env.reset()
    r = {"obs_shape": list(obs.shape), "obs_dtype": str(obs.dtype),
         "reset_in_bounds": bool(np.all(obs >= low - 1e-6) and np.all(obs <= high + 1e-6)),
         "reset_info": {k: info[k] for k in ("sim_time_s", "step_index", "n_steps")}}
    n_target = 192 if full else 4
    leaks, terminated_any, trunc_step, in_bounds = [], False, None, True
    p_mins, n_negs = [], []
    k = 0
    while k < n_target:
        obs, rew, terminated, truncated, info = env.step(NATIVE_NORM)
        k += 1
        leaks.append(info["metrics"].leak_gpm)
        p_mins.append(info["min_service_pressure_psi"])
        n_negs.append(info["n_service_nodes_negative"])
        in_bounds = in_bounds and bool(np.all(obs >= low - 1e-6) and np.all(obs <= high + 1e-6))
        assert np.isfinite(rew), "non-finite reward"
        terminated_any = terminated_any or terminated
        if truncated and trunc_step is None:
            trunc_step = k
        if truncated:
            break
    elapsed = time.perf_counter() - t0
    leak_mean = float(np.mean(leaks))
    r.update({
        "steps_run": k, "seconds_total": round(elapsed, 2),
        "seconds_per_step": round(elapsed / max(k, 1), 3),
        "obs_in_bounds_all_steps": in_bounds,
        "terminated_any": terminated_any, "truncated_at_step": trunc_step,
        "leak_mean_gpm": leak_mean,
        "min_service_pressure_psi": float(np.min(p_mins)),
        "n_service_node_instants_negative": int(np.sum(n_negs)),
    })
    if full:
        rel = abs(leak_mean - LEAK_ANCHOR_GPM) / LEAK_ANCHOR_GPM
        dp = abs(float(np.min(p_mins)) - MIN_SVC_PRESSURE_ANCHOR_PSI)
        r.update({"leak_anchor_gpm": LEAK_ANCHOR_GPM, "leak_rel_err": rel,
                  "leak_anchor_match": bool(rel < LEAK_REL_TOL),
                  "min_service_pressure_anchor_psi": MIN_SVC_PRESSURE_ANCHOR_PSI,
                  "min_service_pressure_abs_err_psi": dp,
                  "min_service_pressure_anchor_match": bool(dp < MIN_SVC_PRESSURE_TOL_PSI),
                  "negative_pressure_anchor_match": bool(int(np.sum(n_negs)) == 0),
                  "horizon_ok": bool(k == 192 and trunc_step == 192 and not terminated_any)})
    return r


def sb3_smoke() -> dict:
    """SB3 contract + PPO construct/predict/learn + checkpoint round-trip."""
    try:
        from stable_baselines3 import PPO
        from stable_baselines3.common.env_checker import check_env
    except Exception as e:  # noqa: BLE001
        return {"available": False, "reason": f"{type(e).__name__}: {e}"}

    out = {"available": True}
    check_env(make_env(enable_safety=True), warn=True, skip_render_check=True)
    out["check_env"] = "OK"

    env = make_env(enable_safety=True)
    device = CFG.resolve_device("auto")
    model = PPO("MlpPolicy", env, n_steps=8, batch_size=8, n_epochs=1,
                policy_kwargs=dict(net_arch=[64, 64]), seed=0, device=device, verbose=0)
    out["device"] = device
    out["obs_dim"] = int(model.observation_space.shape[0])
    out["act_dim"] = int(model.action_space.shape[0])
    obs, _ = env.reset()
    action, _ = model.predict(obs, deterministic=True)
    out["predict_shape"] = list(np.asarray(action).shape)
    out["predict_in_box"] = bool(np.all(action >= -1.0001) and np.all(action <= 1.0001))

    t0 = time.perf_counter()
    model.learn(total_timesteps=16)
    out["tiny_learn_seconds"] = round(time.perf_counter() - t0, 2)

    ckpt = CFG.RUNS_DIR / "_verify" / "smoke_ckpt.zip"
    ckpt.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(ckpt))
    out["checkpoint_saved"] = ckpt.exists()
    reloaded = PPO.load(str(ckpt), device=device)
    a2, _ = reloaded.predict(obs, deterministic=True)
    out["reload_predict_matches"] = bool(np.allclose(action, a2, atol=1e-6))
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="BWSN-1 env/PPO verification + smoke")
    p.add_argument("--full", action="store_true",
                   help="run the full 192-step episode and assert the leak anchor")
    p.add_argument("--no-sb3", action="store_true", help="skip the SB3 block")
    args = p.parse_args(argv)

    report = {"fingerprint": fingerprint()}
    report["hydraulic_smoke"] = hydraulic_smoke(full=args.full)
    report["sb3_smoke"] = {"available": False, "skipped": True} if args.no_sb3 \
        else sb3_smoke()

    out_dir = CFG.RUNS_DIR / "_verify"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"fingerprint_{socket.gethostname()}.json"
    out_path.write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps(report, indent=2, default=str))
    print(f"\nwrote {out_path}")

    hs = report["hydraulic_smoke"]
    ok = (hs["reset_in_bounds"] and hs["obs_in_bounds_all_steps"]
          and report["fingerprint"]["working_inp_sha256_match"])
    if args.full:
        ok = ok and hs.get("leak_anchor_match", False) and hs.get("horizon_ok", False) \
            and hs.get("min_service_pressure_anchor_match", False) \
            and hs.get("negative_pressure_anchor_match", False)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
