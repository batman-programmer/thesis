"""Cross-environment verification + smoke tool (PHASE 1/2/3/9/10/12).

ONE script, run IDENTICALLY on the Windows dev laptop and on Colab, so their
outputs can be diff'd (the local-vs-Colab consistency gate). It:

  1. prints an environment fingerprint (versions, device, git commit, and the
     working-INP SHA-256 vs the frozen expected hash -> catches transfer
     corruption; the digest is LINE-ENDING-INDEPENDENT so a CRLF Windows
     checkout and an LF Linux/Colab checkout of identical content agree);
  2. runs a REAL WNTR/EPANET native-hold smoke rollout (safety OFF) and checks the
     frozen invariants: obs (139,) float32 in-bounds, 192 transitions, terminated
     never True, truncated at step 192, and leak_mean vs the frozen anchor
     84.72988433677985 GPM at the project tolerance rel < 5e-5;
  3. measures actual seconds/step and seconds/episode (PHASE 12 cost);
  4. IF torch/SB3/gymnasium are installed: runs the SB3 env checker, constructs
     PPO (asserts obs=139 / act=7), performs a tiny learn, and only THEN does the
     checkpoint round-trip (predict trained -> save -> load -> predict reloaded ->
     compare on the same observation);
  5. writes ``runs/_verify/fingerprint_<host>.json`` for cross-machine comparison.

Exit status is driven by ``evaluate_report``: every required hydraulic, checksum
and (when the SB3 block ran) PPO subcheck must pass, exceptions are recorded as
required failures, and optional diagnostics/warnings never fail the run.

Nothing here is research evidence; it is an INTEGRATION gate. It never mocks the
hydraulics, and the tiny learn proves nothing about learning quality.
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
        "working_inp_sha256_raw_diagnostic": CFG._working_inp_sha256_raw(),
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


def roundtrip_check(model, obs, ckpt_path, load_fn, atol: float = 1e-6) -> dict:
    """Checkpoint save/load round-trip on a TRAINED policy.

    Correct ordering (both predictions come from the SAME policy state):
    predict(trained) -> save -> load -> predict(reloaded) -> compare.

    The caller must have already performed any learning BEFORE calling this; the
    earlier implementation compared a PRE-learning prediction against the reloaded
    one, which learning legitimately changes, so it tested nothing about
    checkpoint fidelity. The identical ``obs`` array and ``deterministic=True``
    are used for both predictions.
    """
    a_trained, _ = model.predict(obs, deterministic=True)
    model.save(str(ckpt_path))
    reloaded = load_fn(str(ckpt_path))
    a_reloaded, _ = reloaded.predict(obs, deterministic=True)
    a_trained = np.asarray(a_trained)
    a_reloaded = np.asarray(a_reloaded)
    return {
        "observation_shape": list(np.asarray(obs).shape),
        "action_shape": list(a_trained.shape),
        "action_in_bounds": bool(np.all(a_trained >= -1.0001)
                                 and np.all(a_trained <= 1.0001)),
        "checkpoint_exists": bool(ckpt_path.exists()),
        "reload_prediction_matches": bool(
            a_trained.shape == a_reloaded.shape
            and np.allclose(a_trained, a_reloaded, atol=atol)),
    }


def sb3_smoke() -> dict:
    """SB3 contract + PPO construct/tiny-learn + TRAINED checkpoint round-trip.

    INTEGRATION ONLY: the tiny learn exists to prove the pipeline runs. It says
    NOTHING about learning quality, leakage reduction, or any thesis claim.

    Any exception inside the required block is captured under ``error`` so the
    caller's exit-status logic treats it as a REQUIRED FAILURE rather than letting
    a crash or a partially-filled report pass.
    """
    try:
        from stable_baselines3 import PPO
        from stable_baselines3.common.env_checker import check_env
    except Exception as e:  # noqa: BLE001
        return {"available": False, "reason": f"{type(e).__name__}: {e}"}

    out = {"available": True}
    try:
        check_env(make_env(enable_safety=True), warn=True, skip_render_check=True)
        out["check_env"] = "OK"

        env = make_env(enable_safety=True)
        device = CFG.resolve_device("auto")
        model = PPO("MlpPolicy", env, n_steps=8, batch_size=8, n_epochs=1,
                    policy_kwargs=dict(net_arch=[64, 64]), seed=0, device=device,
                    verbose=0)
        out["device"] = device
        out["obs_dim"] = int(model.observation_space.shape[0])
        out["act_dim"] = int(model.action_space.shape[0])

        # Fixed observation reused for BOTH post-training predictions.
        obs, _ = env.reset()

        t0 = time.perf_counter()
        model.learn(total_timesteps=16)          # tiny learn FIRST
        out["tiny_learn_seconds"] = round(time.perf_counter() - t0, 2)

        ckpt = CFG.RUNS_DIR / "_verify" / "smoke_ckpt.zip"
        ckpt.parent.mkdir(parents=True, exist_ok=True)
        out.update(roundtrip_check(
            model, obs, ckpt, lambda p: PPO.load(p, device=device)))
    except Exception as e:  # noqa: BLE001 - recorded as a required failure
        out["error"] = f"{type(e).__name__}: {e}"
    return out


def evaluate_report(report: dict, full: bool = False,
                    require_ppo: bool = False) -> tuple[bool, list[str]]:
    """Decide PASS/FAIL from a report and return every REQUIRED failure message.

    Required always : working-INP checksum match + the reset/step observation
                      bounds. With ``full``: the three hydraulic anchors + horizon.
    Required for PPO: when the SB3 block actually ran (``available``), ALL of its
                      subchecks are required -- no exception, no wrong dimension,
                      no missing checkpoint, no round-trip mismatch. With
                      ``require_ppo`` the block must also BE available (so a
                      machine that silently lacks the RL stack cannot pass a gate
                      that is supposed to exercise PPO).

    Optional diagnostics are deliberately NOT failures: SB3's "MlpPolicy on GPU"
    advisory, timings, device choice and version strings are informational only.
    A missing/undetermined value for a required check counts as a FAILURE (never
    as a pass), so a truncated or crashed report cannot exit 0.
    """
    fp = report.get("fingerprint", {})
    hs = report.get("hydraulic_smoke", {})
    sb = report.get("sb3_smoke", {})
    checks: list[tuple[str, bool, str]] = [
        ("checksum/working_inp_sha256_match",
         bool(fp.get("working_inp_sha256_match")),
         f"got {fp.get('working_inp_sha256')} != expected "
         f"{fp.get('working_inp_sha256_expected')}"),
        ("hydraulic/reset_in_bounds", bool(hs.get("reset_in_bounds")),
         "reset observation outside the frozen bounds"),
        ("hydraulic/obs_in_bounds_all_steps", bool(hs.get("obs_in_bounds_all_steps")),
         "an observation left the frozen bounds during the rollout"),
    ]
    if full:
        checks += [
            ("hydraulic/leak_anchor_match", bool(hs.get("leak_anchor_match")),
             f"leak_mean {hs.get('leak_mean_gpm')} vs anchor "
             f"{hs.get('leak_anchor_gpm')} (rel {hs.get('leak_rel_err')})"),
            ("hydraulic/min_service_pressure_anchor_match",
             bool(hs.get("min_service_pressure_anchor_match")),
             f"min service pressure {hs.get('min_service_pressure_psi')} vs anchor "
             f"{hs.get('min_service_pressure_anchor_psi')}"),
            ("hydraulic/negative_pressure_anchor_match",
             bool(hs.get("negative_pressure_anchor_match")),
             f"negative instants {hs.get('n_service_node_instants_negative')} != 0"),
            ("hydraulic/horizon_ok", bool(hs.get("horizon_ok")),
             "episode horizon / truncation semantics wrong"),
        ]
    if require_ppo:
        checks.append(("ppo/available", bool(sb.get("available")),
                       f"SB3/PPO stack unavailable: {sb.get('reason')}"))
    if sb.get("available"):
        checks += [
            ("ppo/no_exception", "error" not in sb,
             f"exception during the PPO block: {sb.get('error')}"),
            ("ppo/check_env", sb.get("check_env") == "OK",
             "SB3 env checker did not report OK"),
            ("ppo/obs_dim_139", sb.get("obs_dim") == 139,
             f"policy observation dim {sb.get('obs_dim')} != 139"),
            ("ppo/act_dim_7", sb.get("act_dim") == 7,
             f"policy action dim {sb.get('act_dim')} != 7"),
            ("ppo/action_shape", sb.get("action_shape") == [7],
             f"predicted action shape {sb.get('action_shape')} != [7]"),
            ("ppo/action_in_bounds", bool(sb.get("action_in_bounds")),
             "predicted action left the [-1,1] box"),
            ("ppo/checkpoint_exists", bool(sb.get("checkpoint_exists")),
             "checkpoint file was not written"),
            ("ppo/reload_prediction_matches", bool(sb.get("reload_prediction_matches")),
             "reloaded policy's deterministic prediction differs from the trained "
             "policy's on the same observation"),
        ]
    failures = [f"{name}: {detail}" for name, ok, detail in checks if not ok]
    return (not failures), failures


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="BWSN-1 env/PPO verification + smoke")
    p.add_argument("--full", action="store_true",
                   help="run the full 192-step episode and assert the leak anchor")
    p.add_argument("--no-sb3", action="store_true", help="skip the SB3 block")
    p.add_argument("--require-ppo", action="store_true",
                   help="treat an unavailable SB3/PPO stack as a FAILURE (use on "
                        "the training runtime, where PPO must actually be present)")
    args = p.parse_args(argv)

    report: dict = {}
    try:
        report["fingerprint"] = fingerprint()
        report["hydraulic_smoke"] = hydraulic_smoke(full=args.full)
        report["sb3_smoke"] = ({"available": False, "skipped": True}
                               if args.no_sb3 else sb3_smoke())
    except Exception as e:  # noqa: BLE001 - never let a crash exit 0
        report["fatal_error"] = f"{type(e).__name__}: {e}"

    out_dir = CFG.RUNS_DIR / "_verify"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"fingerprint_{socket.gethostname()}.json"
    out_path.write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps(report, indent=2, default=str))
    print(f"\nwrote {out_path}")

    if "fatal_error" in report:
        print(f"\nREQUIRED CHECK FAILURES:\n  - fatal: {report['fatal_error']}")
        print("VERIFY: FAIL")
        return 1

    ok, failures = evaluate_report(report, full=args.full,
                                   require_ppo=args.require_ppo)
    if failures:
        print("\nREQUIRED CHECK FAILURES:")
        for f in failures:
            print(f"  - {f}")
    if args.no_sb3 or not report["sb3_smoke"].get("available"):
        print("\nNOTE: PPO subchecks were NOT exercised"
              + (" (--require-ppo would make this a failure)."
                 if not args.require_ppo else "."))
    print(f"VERIFY: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
