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

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SRC = PROJECT_ROOT / "src"
for _p in (_SRC / "env", _SRC / "validation"):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

import bwsn_env as _E  # noqa: E402

BWSNPressureControlEnv = _E.BWSNPressureControlEnv


def make_env(enable_safety: bool = True, reward_config=None, safety_config=None,
             monitor: bool = False, monitor_path=None):
    """Build one BWSN-1 PPO episode environment (frozen D-P6-001..006 semantics).

    ``enable_safety``   apply the D-P6-006 F1 admissibility layer (default True).
    ``reward_config``   RW.RewardConfig; default = frozen C-A_F1 weights/normalisers.
    ``safety_config``   SF.SafetyConfig; default = frozen eps_p=0, H=1.
    ``monitor``         wrap with SB3 ``Monitor`` for episode reward/length logging
                        (imported lazily; requires stable-baselines3).
    """
    env = BWSNPressureControlEnv(reward_config=reward_config,
                                 safety_config=safety_config,
                                 enable_safety=enable_safety)
    if monitor:
        from stable_baselines3.common.monitor import Monitor  # lazy
        env = Monitor(env, filename=str(monitor_path) if monitor_path else None)
    return env
