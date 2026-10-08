"""PHASE-4 proposed-vs-executed traceability regression (real EPANET, no RL stack).

Guards the chronology the D-P6-005 movement term depends on. These run through
the REAL env (WNTR/EPANET), need no torch/SB3, and are deliberately short
(~5 control steps) so they add little to the suite runtime; the full 192-step
horizon semantics are already covered by test_env_integration (not duplicated).

What is asserted:
  * info exposes proposed_action_norm / executed_action_norm /
    prev_executed_action_norm, each shape (7,) (the observability-only Phase-4
    keys, which must not alter obs/action/reward/safety);
  * chronology: step k's prev_executed == step k-1's executed;
  * the reward's raw movement ||da||^2 equals ||executed_t - prev_executed_t||^2
    (i.e. the movement term is built from the EXECUTED delta, D-P6-005 A2 -- NOT
    the proposed action). The executed!=proposed divergence under an inadmissible
    proposal is proven separately by the FakeDriver cases in test_safety.py;
  * on the admissible native path (safety ON) every outcome is "accepted" and
    proposed==executed, so the traceability keys agree with the reward chronology.

Run: .venv/Scripts/python.exe -m unittest tests.test_ppo_traceability -v
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

NATIVE = AM.command_to_normalized(A.NATIVE_PRV_SETPOINT_PSI, A.NATIVE_PUMP_SPEED)
A1 = np.zeros(7, dtype=np.float32)            # box midpoint
A2 = (0.5 * np.ones(7)).astype(np.float32)    # a distinct in-box action


def _roll(actions, enable_safety):
    env = E.BWSNPressureControlEnv(enable_safety=enable_safety)
    env.reset()
    recs = []
    for a in actions:
        _obs, r, term, trunc, info = env.step(a)
        recs.append((r, term, trunc, info))
    return recs


class TestProposedExecutedTraceability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # safety OFF: proposed == executed, so chronology/movement are clean to check.
        cls.off = _roll([A1, A2, A2, A1, A2], enable_safety=False)
        # safety ON on the native path: must be admissible (accepted) every step.
        cls.on = _roll([NATIVE, NATIVE, NATIVE], enable_safety=True)

    def test_info_keys_and_shapes(self):
        for _r, _t, _tr, info in self.off:
            for k in ("proposed_action_norm", "executed_action_norm",
                      "prev_executed_action_norm"):
                self.assertIn(k, info)
                self.assertEqual(np.asarray(info[k]).shape, (7,))

    def test_terminated_never(self):
        self.assertFalse(any(t for _r, t, _tr, _i in self.off))

    def test_chronology_prev_equals_last_executed(self):
        for i in range(1, len(self.off)):
            prev = np.asarray(self.off[i][3]["prev_executed_action_norm"], dtype=float)
            last_exec = np.asarray(self.off[i - 1][3]["executed_action_norm"], dtype=float)
            self.assertTrue(np.allclose(prev, last_exec, atol=1e-6),
                            f"step {i}: prev_executed != previous executed")

    def test_movement_uses_executed_delta(self):
        # reward_breakdown.movement_l2sq must equal ||executed_t - prev_executed_t||^2.
        for _r, _t, _tr, info in self.off:
            ex = np.asarray(info["executed_action_norm"], dtype=float)
            prev = np.asarray(info["prev_executed_action_norm"], dtype=float)
            expected = float(np.dot(ex - prev, ex - prev))
            self.assertAlmostEqual(info["reward_breakdown"].movement_l2sq, expected,
                                   places=6)

    def test_safety_off_proposed_equals_executed(self):
        for _r, _t, _tr, info in self.off:
            self.assertTrue(np.allclose(
                np.asarray(info["proposed_action_norm"], dtype=float),
                np.asarray(info["executed_action_norm"], dtype=float), atol=1e-5))

    def test_native_path_accepted_and_identity(self):
        for _r, _t, _tr, info in self.on:
            self.assertEqual(info["outcome"], "accepted")
            self.assertTrue(np.allclose(
                np.asarray(info["proposed_action_norm"], dtype=float),
                np.asarray(info["executed_action_norm"], dtype=float), atol=1e-5))

    def test_service_pressure_diagnostics(self):
        # Observability-only endpoint diagnostics over the frozen 121 service nodes.
        # On the native path the frozen reference state has ZERO negative-pressure
        # instants, and the worst service node sits well below the 20 psi service
        # threshold (chronic sub-20 baseline, min 4.16452169418335 psi) -- so the
        # value must be positive and far under 300 psi, and the count exactly 0.
        for _r, _t, _tr, info in self.on:
            mp = info["min_service_pressure_psi"]
            self.assertTrue(np.isfinite(mp))
            self.assertGreater(mp, 0.0)
            self.assertLess(mp, 300.0)
            self.assertEqual(info["n_service_nodes_negative"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
