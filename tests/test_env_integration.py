"""STAGE-D integration battery: BWSNPressureControlEnv over a REAL EPANET episode.

SLOW (real WNTR/EPANET-2.2 solves): two full 192-step native episodes are run
ONCE in setUpClass (~40 s total) and every test asserts against the cached
rollouts. Verifies, end to end through driver -> metrics -> reward -> observation:

  * native static hold reproduces the frozen leak anchor (84.72988 GPM, rel<5e-5);
  * horizon semantics: terminated never True; truncated True exactly at step 192;
  * every observation is shape (139,) float32 inside the frozen bounds;
  * the D-P6-005 movement invariant (da == 0 exactly for every repeated step);
  * the D-P6-006 safety layer is a NO-OP on the admissible native trajectory
    (all outcomes "accepted"; leak anchor byte-identical to the safety-off run).

Run:  .venv/Scripts/python.exe -m unittest tests.test_env_integration -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

_SRC = Path(__file__).resolve().parents[1] / "src"
for _p in (str(_SRC / "env"), str(_SRC / "validation")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import bwsn_env as E  # noqa: E402
import action_mapper as AM  # noqa: E402
import epanet_adapter as A  # noqa: E402
from state_builder import observation_bounds  # noqa: E402

LEAK_REF = 84.72988433677985
NATIVE_NORM = AM.command_to_normalized(A.NATIVE_PRV_SETPOINT_PSI, A.NATIVE_PUMP_SPEED)


def _rollout(enable_safety):
    """Drive one full native episode; return cached per-step diagnostics."""
    env = E.BWSNPressureControlEnv(enable_safety=enable_safety)
    low, high = observation_bounds(env.observation_config)
    obs, _ = env.reset()
    rec = dict(leaks=[], mv=[], outcomes=[], obs_ok=True,
               terminated_any=False, trunc_step=None, shapes_ok=True)
    rec["obs_ok"] = bool(obs.shape == (139,) and str(obs.dtype) == "float32"
                         and np.all(obs >= low - 1e-6) and np.all(obs <= high + 1e-6))
    k, done = 0, False
    while not done:
        obs, r, terminated, truncated, info = env.step(NATIVE_NORM)
        k += 1
        rec["shapes_ok"] = rec["shapes_ok"] and obs.shape == (139,) and obs.dtype == np.float32
        rec["obs_ok"] = rec["obs_ok"] and bool(np.all(obs >= low - 1e-6)
                                               and np.all(obs <= high + 1e-6))
        rec["leaks"].append(info["metrics"].leak_gpm)
        rec["mv"].append(info["reward_breakdown"].movement_term)
        rec["outcomes"].append(info["outcome"])
        rec["terminated_any"] = rec["terminated_any"] or terminated
        if truncated and rec["trunc_step"] is None:
            rec["trunc_step"] = k
        done = terminated or truncated
    rec["n_steps"] = k
    rec["leak_mean"] = float(np.mean(rec["leaks"]))
    return rec


class TestEnvIntegration(unittest.TestCase):
    OFF = None
    ON = None

    @classmethod
    def setUpClass(cls):
        cls.OFF = _rollout(enable_safety=False)
        cls.ON = _rollout(enable_safety=True)

    def test_1_native_leak_anchor(self):
        rel = abs(self.OFF["leak_mean"] - LEAK_REF) / LEAK_REF
        self.assertLess(rel, 5e-5, f"leak_mean={self.OFF['leak_mean']} rel={rel:.2e}")

    def test_2_horizon_semantics(self):
        self.assertEqual(self.OFF["n_steps"], 192)
        self.assertFalse(self.OFF["terminated_any"])     # no absorbing state
        self.assertEqual(self.OFF["trunc_step"], 192)    # time limit at the 192nd step

    def test_3_observations_shape_dtype_bounds(self):
        self.assertTrue(self.OFF["shapes_ok"])
        self.assertTrue(self.OFF["obs_ok"])

    def test_4_movement_invariant_static_hold(self):
        mv = self.OFF["mv"]
        # repeated identical float32 action -> da == 0 EXACTLY for steps 2..192.
        self.assertTrue(all(v == 0.0 for v in mv[1:]),
                        "static hold must give zero movement penalty after step 1")
        # step 1 carries only the float32-vs-float64 reset-boundary residual.
        self.assertLess(mv[0], 1e-12)

    def test_5_safety_noop_on_native_path(self):
        self.assertTrue(all(o == "accepted" for o in self.ON["outcomes"]),
                        "native action must be admissible at every step")
        self.assertEqual(self.ON["n_steps"], 192)
        # anchor byte-identical to the safety-off run: the layer changed nothing.
        self.assertLess(abs(self.ON["leak_mean"] - self.OFF["leak_mean"]), 1e-9)


if __name__ == "__main__":
    unittest.main(verbosity=2)
