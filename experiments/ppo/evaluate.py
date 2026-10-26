"""Deterministic evaluation entry point (PHASE 7 / PHASE 16 / STEP-10 D5).

Loads a trained PPO model and rolls it out on a FRESH environment instance
(separate from any training env -- no shared mutable state, no shared RNG) with
``deterministic=True``. Aggregates ONLY the frozen metric definitions already
produced by ``src/env`` (D-P6-004/005 + the safety audit); it introduces no new
metric definition.

STEP-10 evaluation protocol (D-P6-007 / design brief s.5 D5, researcher
selections of 2026-10-19):
  * PAIRED design: every condition is evaluated on the SAME fixed scenario IDs
    (native + val/0..3 + test/0..3 + ood/0..1), so differences are attributable
    to control, not to scenario luck.
  * K = 1 deterministic episode per (condition, scenario): the env has no
    stochastic element and predictions are deterministic, so K > 1 episodes on
    the same (condition, scenario) are exact duplicates. ONE explicit
    REPEATABILITY check re-runs a representative scenario and asserts identical
    metrics (a determinism check, NOT an independent sample).
  * The ``native`` condition needs NO model: a constant native-action predictor
    reuses the same rollout loop.
  * Failures (solver failure, incomplete episode, exception) are recorded under
    the scenario's record as failures -- never silently dropped.
  * NO composite score: each metric is reported separately; mean+/-spread are
    derived across SCENARIOS, never across duplicated episodes.

Writes one JSON per evaluated condition/seed into ``runs/<id>/evaluation/``.
The reported numbers are EVALUATION evidence for whatever model/condition is
passed; they are NOT final thesis comparison results unless the STEP-10
protocol is frozen and explicitly invoked (see PHASE 14/15 boundary).

Usage
-----
    # trained condition (default: paired fixed scenario set, K=1 + check):
    python -m experiments.ppo.evaluate --model runs/dev_run_s0/final_model.zip \
        --experiment-id dev_run_s0 --seed 0

    # native baseline (no model; identical fixed scenario IDs):
    python -m experiments.ppo.evaluate --native-baseline \
        --experiment-id eval_native --seed 0

    # legacy single-scenario mode (K episodes on the env's default scenario):
    python -m experiments.ppo.evaluate --model <path> --experiment-id id \
        --episodes 1
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import config as CFG            # noqa: E402
from make_env import make_env, scenario_config_from  # noqa: E402

# Metric keys compared exactly in the repeatability (determinism) check.
_REPEAT_KEYS = ("n_steps", "leak_mean_gpm", "dsr_mean", "unserved_pos_mean_gpm",
                "deficit_mean_psi_nodesum", "min_service_pressure_psi_min",
                "min_service_pressure_psi_mean",
                "n_service_node_instants_negative", "cumulative_reward",
                "safety_accept_rate")


class _NativePredictor:
    """Constant native-action stand-in for the un-trained baseline condition.

    The native condition is the FIXED native operating point re-issued every
    step (``src/env/baselines.py``); it needs no policy, and reusing the
    episode-rollout loop keeps the accounting identical to the trained
    conditions.
    """

    def __init__(self):
        import baselines as BL
        self._action = BL.native_action()

    def predict(self, obs, deterministic=True):
        assert deterministic, "the native condition is deterministic by definition"
        return self._action.copy(), None


def _roll_episode(model, env) -> dict:
    """One deterministic rollout on the env's currently installed scenario."""
    obs, _info = env.reset()
    ep = {k: [] for k in ("leak", "dsr", "unserved_pos", "deficit",
                          "min_service_pressure", "n_neg", "reward",
                          "safety_dp_min")}
    outcomes = {}
    done = False
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, r, terminated, truncated, info = env.step(action)
        m, dec = info["metrics"], info.get("safety")
        ep["leak"].append(m.leak_gpm)
        ep["dsr"].append(m.dsr)
        ep["unserved_pos"].append(m.unserved_pos_gpm)
        ep["deficit"].append(m.deficit_psi_nodesum)
        ep["reward"].append(r)
        # TRUE endpoint service-pressure diagnostics (frozen 121-node definitions).
        ep["min_service_pressure"].append(info["min_service_pressure_psi"])
        ep["n_neg"].append(info["n_service_nodes_negative"])
        if dec is not None:
            # NOTE: min_dp_min_psi is the RELATIVE guard margin
            # p_min(proposed) - p_min(hold), NOT an absolute pressure.
            ep["safety_dp_min"].append(float(getattr(dec, "min_dp_min_psi", np.nan)))
        outcomes[info["outcome"]] = outcomes.get(info["outcome"], 0) + 1
        done = terminated or truncated
    n = max(sum(outcomes.values()), 1)
    out = {
        "n_steps": len(ep["reward"]),
        "leak_mean_gpm": float(np.mean(ep["leak"])),
        "dsr_mean": float(np.nanmean(ep["dsr"])),
        "unserved_pos_mean_gpm": float(np.mean(ep["unserved_pos"])),
        "deficit_mean_psi_nodesum": float(np.mean(ep["deficit"])),
        "min_service_pressure_psi_min": float(np.min(ep["min_service_pressure"])),
        "min_service_pressure_psi_mean": float(np.mean(ep["min_service_pressure"])),
        "n_service_node_instants_negative": int(np.sum(ep["n_neg"])),
        "cumulative_reward": float(np.sum(ep["reward"])),
        "mean_step_reward": float(np.mean(ep["reward"])),
        "safety_outcomes": outcomes,
        "safety_accept_rate": outcomes.get("accepted", 0) / n,
    }
    if ep["safety_dp_min"]:
        out["safety_worst_relative_dp_min_psi"] = float(np.nanmin(ep["safety_dp_min"]))
    return out


def evaluate_model(model, env, n_episodes: int = 1) -> dict:
    """Deterministic rollout; aggregate frozen metrics + safety audit per episode.

    Legacy single-scenario entry point (kept for backward compatibility with the
    pre-STEP-10 invocation): K episodes on the env's default demand mode. NOTE
    (STEP-10 review addendum): under deterministic rollouts a fixed scenario
    makes K > 1 exact duplicates -- the paired protocol in
    :func:`run_scenario_eval` is the STEP-10 reporting path.
    """
    episodes = []
    for _ in range(n_episodes):
        episodes.append(_roll_episode(model, env))
    return {"n_episodes": n_episodes, "episodes": episodes}


def _episode_metrics_equal(a: dict, b: dict) -> bool:
    """Exact float equality on the reported episode metrics (determinism check)."""
    return all(a.get(k) == b.get(k) for k in _REPEAT_KEYS)


def evaluate_on_fixed_scenarios(model, env, scenario_ids,
                                repeatability_scenario_id=None) -> dict:
    """STEP-10 D5 paired evaluation: ONE deterministic episode per scenario.

    The env is re-parameterised per scenario id and the SAME env instance is
    reused (fresh state each reset; no cross-scenario carry-over). Each record
    carries the scenario's full metadata. Exceptions are recorded per scenario
    and NEVER dropped. When ``repeatability_scenario_id`` is given, that
    representative scenario is re-run once and its metrics must match the
    first run EXACTLY -- a determinism check, not an independent sample.
    """
    records = []
    failures = []
    base_for_repeat = None
    for sid in scenario_ids:
        env.set_demand_scenario(sid)
        try:
            rec = _roll_episode(model, env)
            rec["scenario_id"] = sid
            rec["scenario"] = env.demand_scenario.to_dict()
            rec["seed_provenance"] = env.seed_provenance
            if sid == repeatability_scenario_id:
                base_for_repeat = rec
            records.append(rec)
        except Exception as e:  # noqa: BLE001 - recorded, never dropped
            failures.append({"scenario_id": sid,
                             "error": f"{type(e).__name__}: {e}"})
    out = {"condition_records": records}
    if failures:
        out["failures"] = failures
    if repeatability_scenario_id is not None and base_for_repeat is not None:
        env.set_demand_scenario(repeatability_scenario_id)
        try:
            rerun = _roll_episode(model, env)
            rerun["scenario_id"] = repeatability_scenario_id
            rerun["repeatability"] = {
                "note": ("determinism check, not an independent sample: the env "
                         "has no stochastic element and predictions are "
                         "deterministic, so a repeated rollout must be an exact "
                         "duplicate"),
                "repeated_metrics_identical": bool(
                    _episode_metrics_equal(base_for_repeat, rerun)),
            }
        except Exception as e:  # noqa: BLE001
            rerun = {"scenario_id": repeatability_scenario_id,
                     "error": f"{type(e).__name__}: {e}"}
        out["repeatability_check"] = rerun
    return out


def _scenario_ids_from_arg(arg: str | None) -> list[str] | None:
    if arg is None:
        return None
    ids = [s.strip() for s in arg.split(",") if s.strip()]
    if not ids:
        raise ValueError("--scenarios produced an empty scenario list")
    return ids


def run(model_path: str | None, experiment_id: str, episodes: int = 1,
        seed: int = 0, enable_safety: bool = True,
        native_baseline: bool = False) -> dict:
    """Legacy single-scenario evaluation (pre-STEP-10 invocation contract)."""
    from stable_baselines3 import PPO
    layout = CFG.RunLayout(experiment_id)
    CFG.set_global_seeds(seed)
    env = make_env(enable_safety=enable_safety)          # fresh, unmonitored instance
    model = (_NativePredictor() if native_baseline
             else PPO.load(model_path, device=CFG.resolve_device("auto")))
    result = evaluate_model(model, env, n_episodes=episodes)
    result["model_path"] = str(model_path) if model_path else None
    result["seed"] = seed
    result["condition"] = "native" if native_baseline else "joint"
    result["enable_safety"] = enable_safety
    out = layout.evaluation / f"eval_seed{seed}.json"
    result["output"] = str(out)
    out.write_text(json.dumps(result, indent=2))
    return result


def run_scenario_eval(model_path: str | None, experiment_id: str, seed: int = 0,
                      enable_safety: bool = True, native_baseline: bool = False,
                      scenario_ids: list[str] | None = None,
                      repeatability_scenario_id: str | None = "test/0",
                      baseline_mode: str = "joint") -> dict:
    """STEP-10 D5 paired evaluation over the fixed scenario set (K=1 + check)."""
    from stable_baselines3 import PPO
    import demand_scenarios as DS
    if scenario_ids is None:
        scenario_ids = DS.all_fixed_scenario_ids()
    if not scenario_ids:
        raise ValueError("scenario_ids must not be empty")
    layout = CFG.RunLayout(experiment_id)
    CFG.set_global_seeds(seed)
    scenario_config = scenario_config_from(DS.MASTER_SEED)
    env = make_env(enable_safety=enable_safety,
                   demand_scenario=scenario_ids[0],
                   scenario_config=scenario_config,
                   baseline_mode=baseline_mode)
    model = (_NativePredictor() if native_baseline
             else PPO.load(model_path, device=CFG.resolve_device("auto")))
    result = evaluate_on_fixed_scenarios(
        model, env, scenario_ids,
        repeatability_scenario_id=repeatability_scenario_id)
    result["model_path"] = str(model_path) if model_path else None
    result["seed"] = seed
    result["condition"] = "native" if native_baseline else baseline_mode
    result["enable_safety"] = enable_safety
    result["scenario_ids"] = list(scenario_ids)
    result["master_seed"] = scenario_config.master_seed
    result["protocol"] = {
        "step": "STEP-10 D5",
        "k_per_condition_per_scenario": 1,
        "paired_scenario_ids_across_conditions": True,
        "repeatability_check": repeatability_scenario_id,
        "note": ("K=1 deterministic rollout per (condition, scenario); the "
                 "repeatability re-run is a determinism check, not an "
                 "independent sample. No composite score."),
    }
    out = layout.evaluation / f"eval_seed{seed}.json"
    result["output"] = str(out)
    out.write_text(json.dumps(result, indent=2))
    return result


def _parse(argv=None):
    p = argparse.ArgumentParser(
        description="BWSN-1 PPO deterministic evaluation (STEP-10 D5 paired mode)")
    p.add_argument("--model", default=None,
                   help="path to a trained PPO checkpoint (omit when "
                        "--native-baseline is given)")
    p.add_argument("--native-baseline", action="store_true",
                   help="evaluate the native condition (constant native action, "
                        "no model) on the SAME fixed scenario IDs")
    p.add_argument("--experiment-id", required=True)
    p.add_argument("--episodes", type=int, default=None,
                   help="legacy single-scenario mode: K episodes on the env's "
                        "default demand scenario (default when omitted: the "
                        "STEP-10 paired protocol)")
    p.add_argument("--scenarios", default=None,
                   help="comma-separated fixed scenario ids (default: native + "
                        "val/0..3 + test/0..3 + ood/0..1)")
    p.add_argument("--repeatability-scenario", default="test/0",
                   help="representative scenario re-run for the explicit "
                        "determinism check (default test/0; 'none' disables)")
    p.add_argument("--baseline-mode", default="joint",
                   choices=["joint", "prv_only", "vsp_only"],
                   help="the condition being evaluated (must match how the "
                        "model was TRAINED: masked conditions are separate "
                        "policies, never a post-hoc mask of a joint policy)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--no-safety", action="store_true")
    return p.parse_args(argv)


def main(argv=None) -> int:
    a = _parse(argv)
    if a.native_baseline and a.model:
        raise SystemExit("--native-baseline and --model are mutually exclusive")
    if not a.native_baseline and not a.model:
        raise SystemExit("either --model or --native-baseline is required")
    enable_safety = not a.no_safety
    rep = None if a.repeatability_scenario == "none" else a.repeatability_scenario
    if a.episodes is not None:
        result = run(a.model, a.experiment_id, a.episodes, a.seed,
                     enable_safety, a.native_baseline)
    else:
        result = run_scenario_eval(
            a.model, a.experiment_id, a.seed, enable_safety, a.native_baseline,
            scenario_ids=_scenario_ids_from_arg(a.scenarios),
            repeatability_scenario_id=rep,
            baseline_mode=a.baseline_mode)
    print("EVAL DONE:", json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
