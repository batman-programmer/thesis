"""Deterministic evaluation entry point (PHASE 7 / PHASE 16).

Loads a trained PPO model and rolls it out on a FRESH environment instance
(separate from any training env -- no shared mutable state, no shared RNG) with
``deterministic=True``. Aggregates ONLY the frozen metric definitions already
produced by ``src/env`` (D-P6-004/005 + the safety audit); it introduces no new
metric definition.

Writes one JSON per evaluated seed into ``runs/<id>/evaluation/``. The reported
numbers are EVALUATION evidence for whatever model/scenario is passed; they are
NOT final thesis comparison results unless the STEP-10 protocol is frozen and
explicitly invoked (see PHASE 14/15 boundary).

Usage
-----
    python -m experiments.ppo.evaluate --model runs/dev_run_s0/final_model.zip \
        --experiment-id dev_run_s0 --episodes 1 --seed 0
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
from make_env import make_env   # noqa: E402


def evaluate_model(model, env, n_episodes: int = 1) -> dict:
    """Deterministic rollout; aggregate frozen metrics + safety audit per episode."""
    episodes = []
    for _ in range(n_episodes):
        obs, _info = env.reset()
        ep = {k: [] for k in ("leak", "dsr", "unserved_pos", "deficit",
                              "min_pressure", "n_neg", "reward", "pump_speed_mean")}
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
            if dec is not None:
                ep["n_neg"].append(int(getattr(dec, "n_neg_proposed", 0)))
                ep["min_pressure"].append(float(getattr(dec, "min_dp_min_psi", np.nan)))
            outcomes[info["outcome"]] = outcomes.get(info["outcome"], 0) + 1
            done = terminated or truncated
        n = max(sum(outcomes.values()), 1)
        episodes.append({
            "n_steps": len(ep["reward"]),
            "leak_mean_gpm": float(np.mean(ep["leak"])),
            "dsr_mean": float(np.nanmean(ep["dsr"])),
            "unserved_pos_mean_gpm": float(np.mean(ep["unserved_pos"])),
            "deficit_mean_psi_nodesum": float(np.mean(ep["deficit"])),
            "cumulative_reward": float(np.sum(ep["reward"])),
            "mean_step_reward": float(np.mean(ep["reward"])),
            "safety_outcomes": outcomes,
            "safety_accept_rate": outcomes.get("accepted", 0) / n,
        })
    return {"n_episodes": n_episodes, "episodes": episodes}


def run(model_path: str, experiment_id: str, episodes: int = 1, seed: int = 0,
        enable_safety: bool = True) -> dict:
    from stable_baselines3 import PPO
    layout = CFG.RunLayout(experiment_id)
    CFG.set_global_seeds(seed)
    env = make_env(enable_safety=enable_safety)          # fresh, unmonitored instance
    model = PPO.load(model_path, device=CFG.resolve_device("auto"))
    result = evaluate_model(model, env, n_episodes=episodes)
    result["model_path"] = str(model_path)
    result["seed"] = seed
    result["enable_safety"] = enable_safety
    out = layout.evaluation / f"eval_seed{seed}.json"
    out.write_text(json.dumps(result, indent=2))
    result["output"] = str(out)
    return result


def _parse(argv=None):
    p = argparse.ArgumentParser(description="BWSN-1 PPO deterministic evaluation")
    p.add_argument("--model", required=True)
    p.add_argument("--experiment-id", required=True)
    p.add_argument("--episodes", type=int, default=1)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--no-safety", action="store_true")
    return p.parse_args(argv)


if __name__ == "__main__":
    a = _parse()
    print("EVAL DONE:", json.dumps(
        run(a.model, a.experiment_id, a.episodes, a.seed, not a.no_safety), indent=2))
