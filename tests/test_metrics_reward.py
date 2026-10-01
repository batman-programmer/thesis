"""STAGE-D correctness battery: per-step metrics + D-P6-005 reward.

Pure / synthetic (no EPANET) -- exercises the frozen accounting LAW and the
reward algebra directly on hand-built states, so the numbers are known in closed
form. The REAL-EPANET native-anchor reproduction is in test_env_integration.py.
Run:

    .venv/Scripts/python.exe -m unittest tests.test_metrics_reward -v
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np

_SRC = Path(__file__).resolve().parents[1] / "src"
for _p in (str(_SRC / "env"), str(_SRC / "validation")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import metrics as MX  # noqa: E402
import reward as RW  # noqa: E402


class _FakeStep:
    """Minimal StepResult stand-in: only the fields step_metrics reads."""
    def __init__(self, pressures, demand, requested, pump_power):
        self.pressures_psi = pressures
        self.demand_gpm = demand
        self.requested_gpm = requested
        self.pump_power_kw = pump_power


class TestMetrics(unittest.TestCase):
    def test_1_leak_signed_emitter_law(self):
        # q_j = sign(p)|p|^0.5 * C over the coefficient (full-junction) set.
        coeff = {"A": 2.0, "B": 0.5}
        p = {"A": 100.0, "B": 36.0, "SVC": 50.0}  # SVC has no coeff -> no leak
        step = _FakeStep(p, {"A": 0.0, "B": 0.0, "SVC": 0.0}, {}, {})
        m = MX.step_metrics(step, coeff, ["SVC"])
        expect = math.sqrt(100.0) * 2.0 + math.sqrt(36.0) * 0.5   # 20 + 3 = 23
        self.assertAlmostEqual(m.leak_gpm, expect, places=9)

    def test_2_leak_negative_pressure_is_signed(self):
        # a negative pressure draws BACK (negative emitter flow), per the law.
        coeff = {"A": 3.0}
        step = _FakeStep({"A": -16.0}, {"A": 0.0}, {}, {})
        m = MX.step_metrics(step, coeff, ["A"])
        self.assertAlmostEqual(m.leak_gpm, -math.sqrt(16.0) * 3.0, places=9)  # -12

    def test_3_served_unserved_balance(self):
        coeff = {"A": 2.0}
        p = {"A": 100.0}                 # leak = 20
        dem = {"A": 120.0}               # reported demand (incl. emitter)
        reqd = {"A": 150.0}              # expected demand
        m = MX.step_metrics(_FakeStep(p, dem, reqd, {}), coeff, ["A"])
        self.assertAlmostEqual(m.leak_gpm, 20.0, places=9)
        self.assertAlmostEqual(m.served_gpm, 120.0 - 20.0, places=9)       # 100
        self.assertAlmostEqual(m.requested_gpm, 150.0, places=9)
        self.assertAlmostEqual(m.unserved_gpm, 150.0 - 100.0, places=9)    # 50
        self.assertAlmostEqual(m.unserved_pos_gpm, 50.0, places=9)
        self.assertAlmostEqual(m.dsr, 100.0 / 150.0, places=9)

    def test_4_unserved_pos_floors_at_zero(self):
        # over-service (served > requested) -> unserved negative, unserved_pos = 0.
        coeff = {"A": 1.0}
        m = MX.step_metrics(_FakeStep({"A": 100.0}, {"A": 200.0}, {"A": 50.0}, {}),
                            coeff, ["A"])
        self.assertLess(m.unserved_gpm, 0.0)
        self.assertEqual(m.unserved_pos_gpm, 0.0)

    def test_5_deficit_service_nodes_only(self):
        # deficit sums (20 - p)^+ over SERVICE nodes only; a low connector that is
        # NOT in service_nodes must not contribute.
        coeff = {}
        p = {"S1": 12.0, "S2": 25.0, "CONN": -100.0}
        m = MX.step_metrics(_FakeStep(p, {}, {}, {}), coeff, ["S1", "S2"])
        self.assertAlmostEqual(m.deficit_psi_nodesum, (20.0 - 12.0) + 0.0, places=9)

    def test_6_power_sums_pumps(self):
        m = MX.step_metrics(_FakeStep({"A": 50.0}, {}, {}, {"P1": 10.0, "P2": 5.0}),
                            {}, ["A"])
        self.assertAlmostEqual(m.power_kw, 15.0, places=9)


def _metrics(leak, unserved_pos, deficit, power):
    return MX.StepMetrics(leak_gpm=leak, served_gpm=0.0, requested_gpm=0.0,
                          unserved_gpm=0.0, unserved_pos_gpm=unserved_pos,
                          deficit_psi_nodesum=deficit, power_kw=power, dsr=0.0)


class TestReward(unittest.TestCase):
    def setUp(self):
        self.cfg = RW.RewardConfig()

    def test_1_frozen_weights_and_refs(self):
        c = self.cfg
        self.assertEqual((c.w_leak, c.w_unserved, c.w_deficit, c.w_movement,
                          c.w_energy), (1.0, 1.0, 1.0, 0.1, 0.0))
        self.assertEqual(c.leak_ref, 84.72988433677985)
        self.assertEqual(c.req_ref, 906.3987348621764)
        self.assertEqual(c.deficit_ref, 28.671793365478514)
        self.assertEqual(c.power_ref, 88.10062475649187)
        self.assertEqual(c.movement_l2sq_max, 28.0)

    def test_2_decomposition_and_sign(self):
        m = _metrics(leak=84.72988433677985, unserved_pos=906.3987348621764,
                     deficit=28.671793365478514, power=88.10062475649187)
        rb = RW.compute_reward(m, np.zeros(7), self.cfg)
        self.assertAlmostEqual(rb.leak_term, 1.0, places=12)
        self.assertAlmostEqual(rb.unserved_term, 1.0, places=12)
        self.assertAlmostEqual(rb.deficit_term, 1.0, places=12)
        self.assertAlmostEqual(rb.movement_term, 0.0, places=12)
        self.assertAlmostEqual(rb.energy_term, 0.0, places=12)   # w_E = 0
        self.assertAlmostEqual(rb.total, -3.0, places=12)        # -(1+1+1+0+0)

    def test_3_static_hold_zero_movement(self):
        rb = RW.compute_reward(_metrics(0, 0, 0, 0), np.zeros(7), self.cfg)
        self.assertEqual(rb.movement_l2sq, 0.0)
        self.assertEqual(rb.movement_term, 0.0)

    def test_4_movement_max_is_box_diagonal(self):
        # full box swing: each of 7 components moves by 2 -> ||da||^2 = 28 -> the
        # normalised movement penalty is exactly 1, times w_movement = 0.1.
        da = np.full(7, 2.0)
        rb = RW.compute_reward(_metrics(0, 0, 0, 0), da, self.cfg)
        self.assertAlmostEqual(rb.movement_l2sq, 28.0, places=12)
        self.assertAlmostEqual(rb.movement_term, 0.1, places=12)

    def test_5_energy_disabled_but_representable(self):
        m = _metrics(0, 0, 0, power=1e6)
        rb = RW.compute_reward(m, np.zeros(7), self.cfg)
        self.assertEqual(rb.energy_term, 0.0)
        # re-enabling the weight makes the SAME power contribute.
        cfg_e = RW.RewardConfig(w_energy=1.0)
        rb_e = RW.compute_reward(m, np.zeros(7), cfg_e)
        self.assertAlmostEqual(rb_e.energy_term, 1e6 / cfg_e.power_ref, places=6)

    def test_6_native_leak_anchor(self):
        # native-equivalent instant: leak at the ref, no unserved/deficit, static
        # hold -> total == -1.0 exactly (leak_term only).
        m = _metrics(leak=self.cfg.leak_ref, unserved_pos=0.0, deficit=0.0, power=0.0)
        rb = RW.compute_reward(m, np.zeros(7), self.cfg)
        self.assertAlmostEqual(rb.leak_term, 1.0, places=12)
        self.assertAlmostEqual(rb.total, -1.0, places=12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
