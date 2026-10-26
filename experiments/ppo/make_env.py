"""Portable environment factory for the BWSN-1 PPO pipeline.

Resolves the project root FROM THIS FILE (never a hard-coded drive), bootstraps
``sys.path`` to the frozen ``src/env`` + ``src/validation`` packages, and returns
a ready :class:`BWSNPressureControlEnv`. The identical call works on the Windows
development laptop and on a Colab checkout at ``/content/Thesis`` (or anywhere
else) -- only ``__file__`` matters, so no path, drive, or username is assumed.

This module imports numpy + WNTR (already validated) but NOT torch / SB3; the
optional ``Monitor`` wrapper is imported lazily so the factory can be used on a
machine that has no RL stack yet (e.g. for the real-EPANET smoke test).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SRC = PROJECT_ROOT / "src"
for _p in (_SRC / "env", _SRC / "validation"):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

import bwsn_env as _E  # noqa: E402
import demand_scenarios as _DS  # noqa: E402
import baselines as BL  # noqa: E402

BWSNPressureControlEnv = _E.BWSNPressureControlEnv

try:
    from gymnasium import Wrapper as _GymWrapper
except Exception:  # noqa: BLE001 - no gymnasium -> plain delegation base
    _GymWrapper = None


def scenario_config_from(master_seed: int) -> _DS.ScenarioConfig:
    """ScenarioConfig for a run: frozen M1 parameters + the run's master seed."""
    return _DS.ScenarioConfig(master_seed=int(master_seed))


if _GymWrapper is not None:

    class BaselineMaskWrapper(_GymWrapper):
        """Project a proposed action onto a baseline mode IN FRONT of ``step``.

        STEP-10 D5: the masked comparison conditions (``prv_only`` /
        ``vsp_only``) are SEPARATE TRAINED POLICIES -- the mask is applied
        during TRAINING so the policy learns inside its actuator subset, and
        the same mask is applied when that policy is EVALUATED (the condition's
        physical definition pins the other actuators to native). What this
        wrapper must never be used for: masking a ``joint``-trained policy and
        reporting it as ``prv_only``/``vsp_only`` (see ``src/env/baselines.py``
        -- the mask helper is deliberately NOT wired into ``bwsn_env.step``).
        """

        def __init__(self, env, mode: str):
            super().__init__(env)
            self.mode = mode
            self.free_mask = BL.free_mask(mode)

        def step(self, action):
            return self.env.step(BL.apply_mask(np.asarray(action), self.mode))

        # F5: explicit pass-through so evaluators can set/read the demand
        # scenario on the wrapped env (gymnasium.Wrapper does not forward
        # attribute SETS to the env; the headless twin __getattr__ already does).
        def set_demand_scenario(self, scenario) -> None:
            self.env.set_demand_scenario(scenario)

        @property
        def demand_scenario(self):
            return self.env.demand_scenario

        @property
        def seed_provenance(self):
            return self.env.seed_provenance

else:

    class BaselineMaskWrapper:  # type: ignore[no-redef]
        """Headless twin of the gymnasium BaselineMaskWrapper (no RL stack)."""

        def __init__(self, env, mode: str):
            self.env = env
            self.mode = mode
            self.free_mask = BL.free_mask(mode)

        def reset(self, *, seed=None, options=None):
            return self.env.reset(seed=seed, options=options)

        def step(self, action):
            return self.env.step(BL.apply_mask(np.asarray(action), self.mode))

        # F5: explicit pass-through mirrors the gymnasium branch so both
        # wrappers expose the same scenario API to evaluators.
        def set_demand_scenario(self, scenario) -> None:
            self.env.set_demand_scenario(scenario)

        @property
        def demand_scenario(self):
            return self.env.demand_scenario

        @property
        def seed_provenance(self):
            return self.env.seed_provenance

        def __getattr__(self, name):
            if name.startswith("__"):
                raise AttributeError(name)
            return getattr(self.env, name)


def make_env(enable_safety: bool = True, reward_config=None, safety_config=None,
             monitor: bool = False, monitor_path=None,
             demand_scenario="native",
             scenario_config: _DS.ScenarioConfig | None = None,
             baseline_mode: str = "joint"):
    """Build one BWSN-1 PPO episode environment (frozen D-P6-001..006 semantics).

    ``enable_safety``   apply the D-P6-006 F1 admissibility layer (default True).
    ``reward_config``   RW.RewardConfig; default = frozen C-A_F1 weights/normalisers.
    ``safety_config``   SF.SafetyConfig; default = frozen eps_p=0, H=1.
    ``monitor``         wrap with SB3 ``Monitor`` for episode reward/length logging
                        (imported lazily; requires stable-baselines3).
    ``demand_scenario`` STEP-10 (D-P6-007) demand mode: "native" (frozen anchor
                        path, default), "train" (new U1+S1 draw per episode from
                        the reproducible stream), "val/<i>" / "test/<i>" /
                        "ood/<i>" (fixed evaluation scenario), or a
                        DemandScenario instance.
    ``scenario_config`` DS.ScenarioConfig; default = frozen master seed 20261019,
                        mu 1.0, sigma 0.1, bounds [0.7, 1.3].
    ``baseline_mode``   "joint" (default, all 7 dims free) or "prv_only" /
                        "vsp_only" -- masked TRAINING conditions, applied by
                        wrapping the env with BaselineMaskWrapper (a separate
                        policy must be trained per mode; never a post-hoc mask
                        of a joint policy).
    """
    env = BWSNPressureControlEnv(reward_config=reward_config,
                                 safety_config=safety_config,
                                 enable_safety=enable_safety,
                                 demand_scenario=demand_scenario,
                                 scenario_config=scenario_config)
    if baseline_mode not in BL.MODES:
        raise KeyError(f"unknown baseline mode {baseline_mode!r}; "
                       f"choose from {sorted(BL.MODES)}")
    if baseline_mode in ("prv_only", "vsp_only"):
        env = BaselineMaskWrapper(env, baseline_mode)
    if monitor:
        from stable_baselines3.common.monitor import Monitor  # lazy
        env = Monitor(env, filename=str(monitor_path) if monitor_path else None)
    return env
