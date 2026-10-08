"""PPO training entry point for the BWSN-1 environment (PHASE 5/9/11).

A CONFIGURATION-DRIVEN launcher, not research logic: it wires the frozen
environment to stable-baselines3 PPO (MlpPolicy), runs the SB3 env checker as a
gate, trains for a configurable budget, logs via ThesisLoggingCallback, and saves
checkpoints + a full reproducibility record. It imports torch / SB3 lazily, so it
only requires the RL stack at RUN time (the laptop may run a tiny ``--smoke``; the
expensive runs are intended for Colab GPU).

Examples
--------
    # laptop integration smoke (tiny; NOT research evidence)
    python -m experiments.ppo.train --smoke --experiment-id dev_smoke

    # Colab development run (still DEVELOPMENT evidence until STEP-10 is frozen)
    python -m experiments.ppo.train --experiment-id dev_run_s0 \
        --total-timesteps 50000 --seed 0 --device auto

    # resume from a checkpoint
    python -m experiments.ppo.train --experiment-id dev_run_s0 \
        --resume experiments/ppo/runs/dev_run_s0/checkpoints/ppo_20000_steps.zip \
        --total-timesteps 50000
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import config as CFG            # noqa: E402
from make_env import make_env   # noqa: E402


def _activation(name: str):
    import torch.nn as nn
    return {"tanh": nn.Tanh, "relu": nn.ReLU}.get(name, nn.Tanh)


def build_model(config: CFG.PPOConfig, env, device: str, tb_dir):
    from stable_baselines3 import PPO
    policy_kwargs = dict(net_arch=list(config.net_arch),
                         activation_fn=_activation(config.activation))
    return PPO(
        "MlpPolicy", env,
        learning_rate=config.learning_rate, n_steps=config.n_steps,
        batch_size=config.batch_size, n_epochs=config.n_epochs,
        gamma=config.gamma, gae_lambda=config.gae_lambda,
        clip_range=config.clip_range, ent_coef=config.ent_coef,
        vf_coef=config.vf_coef, max_grad_norm=config.max_grad_norm,
        policy_kwargs=policy_kwargs, seed=config.seed, device=device,
        tensorboard_log=str(tb_dir) if config.tensorboard else None, verbose=1)


def run(config: CFG.PPOConfig, resume: str | None = None,
        run_check_env: bool = True) -> dict:
    from stable_baselines3.common.callbacks import CheckpointCallback
    from stable_baselines3.common.env_checker import check_env
    from callbacks import ThesisLoggingCallback

    if not config.minibatch_divides():
        raise ValueError(f"batch_size {config.batch_size} must divide "
                         f"n_steps {config.n_steps}")

    layout = CFG.RunLayout(config.experiment_id)
    CFG.set_global_seeds(config.seed)
    device = CFG.resolve_device(config.device)

    # PHASE 2 gate: SB3 env checker on a RAW (unwrapped, unmonitored) instance.
    if run_check_env:
        check_env(make_env(enable_safety=config.enable_safety),
                  warn=True, skip_render_check=True)

    sf_cfg = _safety_config(config)
    env = make_env(enable_safety=config.enable_safety, safety_config=sf_cfg,
                   monitor=True, monitor_path=layout.logs / "monitor.csv")

    if resume:
        from stable_baselines3 import PPO
        model = PPO.load(resume, env=env, device=device)
        reset_timesteps = False
    else:
        model = build_model(config, env, device, layout.logs)
        reset_timesteps = True

    cfg_path = layout.write_config(config)
    callbacks = [ThesisLoggingCallback()]
    if config.checkpoint_freq > 0:
        callbacks.append(CheckpointCallback(
            save_freq=config.checkpoint_freq, save_path=str(layout.checkpoints),
            name_prefix="ppo"))

    model.learn(total_timesteps=config.total_timesteps, callback=callbacks,
                reset_num_timesteps=reset_timesteps,
                tb_log_name=config.experiment_id)
    model.save(str(layout.final_model))
    return {"device": device, "final_model": str(layout.final_model),
            "config_path": str(cfg_path), "run_dir": str(layout.root)}


def _safety_config(config: CFG.PPOConfig):
    import sys as _s
    _s.path.insert(0, str(CFG.PROJECT_ROOT / "src" / "env"))
    import safety as SF
    return SF.SafetyConfig(eps_p_psi=config.safety_eps_p_psi,
                           horizon_steps=config.safety_horizon_steps)


def _parse(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="BWSN-1 PPO training launcher")
    p.add_argument("--experiment-id", default="dev_smoke")
    p.add_argument("--smoke", action="store_true", help="tiny integration budget")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    p.add_argument("--total-timesteps", type=int, default=None)
    p.add_argument("--n-steps", type=int, default=None)
    p.add_argument("--batch-size", type=int, default=None)
    p.add_argument("--learning-rate", type=float, default=None)
    p.add_argument("--checkpoint-freq", type=int, default=None)
    p.add_argument("--no-safety", action="store_true")
    p.add_argument("--resume", default=None)
    p.add_argument("--no-check-env", action="store_true")
    return p.parse_args(argv)


def _config_from_args(a: argparse.Namespace) -> CFG.PPOConfig:
    c = CFG.smoke_config(a.experiment_id) if a.smoke else CFG.PPOConfig(
        experiment_id=a.experiment_id)
    c.seed, c.device = a.seed, a.device
    if a.total_timesteps is not None: c.total_timesteps = a.total_timesteps
    if a.n_steps is not None: c.n_steps = a.n_steps
    if a.batch_size is not None: c.batch_size = a.batch_size
    if a.learning_rate is not None: c.learning_rate = a.learning_rate
    if a.checkpoint_freq is not None: c.checkpoint_freq = a.checkpoint_freq
    if a.no_safety: c.enable_safety = False
    return c


if __name__ == "__main__":
    args = _parse()
    cfg = _config_from_args(args)
    result = run(cfg, resume=args.resume, run_check_env=not args.no_check_env)
    print("TRAIN DONE:", result)
