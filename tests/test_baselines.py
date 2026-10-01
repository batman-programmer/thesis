"""STAGE-F correctness battery: baseline action-masking interface.

Pure (no EPANET). Verifies the four comparison modes pin exactly the right
actuators to the native operating point and leave the rest free. Run:

    .venv/Scripts/python.exe -m unittest tests.test_baselines -v
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

import action_mapper as AM  # noqa: E402
import baselines as B  # noqa: E402
import epanet_adapter as A  # noqa: E402

NATIVE = B.native_action()


class TestBaselines(unittest.TestCase):
    def test_1_modes_and_free_indices(self):
        self.assertEqual(set(B.MODES), {"native", "prv_only", "vsp_only", "joint"})
        np.testing.assert_array_equal(B.free_mask("native"), np.zeros(7, bool))
        np.testing.assert_array_equal(B.free_mask("joint"), np.ones(7, bool))
        np.testing.assert_array_equal(
            B.free_mask("prv_only"), np.array([1, 1, 1, 1, 1, 0, 0], bool))
        np.testing.assert_array_equal(
            B.free_mask("vsp_only"), np.array([0, 0, 0, 0, 0, 1, 1], bool))

    def test_2_native_action_matches_operating_point(self):
        self.assertEqual(NATIVE.dtype, np.float32)
        ref = AM.command_to_normalized(A.NATIVE_PRV_SETPOINT_PSI, A.NATIVE_PUMP_SPEED)
        np.testing.assert_allclose(NATIVE, ref.astype(np.float32), atol=0)
        # round-trips to the native physical setpoints/speeds.
        prv, pump = AM.to_command(NATIVE)
        for v in A.PRV_IDS:
            self.assertAlmostEqual(prv[v], A.NATIVE_PRV_SETPOINT_PSI[v], places=5)
        for p in A.PUMP_IDS:
            self.assertAlmostEqual(pump[p], A.NATIVE_PUMP_SPEED[p], places=5)

    def test_3_native_mode_is_constant_hold(self):
        rng = np.random.default_rng(1)
        for _ in range(50):
            a = rng.uniform(-1, 1, size=7)
            np.testing.assert_array_equal(B.apply_mask(a, "native"), NATIVE)

    def test_4_joint_mode_is_identity_clip(self):
        a = np.array([0.2, -0.4, 0.6, -0.8, 0.1, -0.3, 0.5])
        np.testing.assert_allclose(B.apply_mask(a, "joint"), AM.as_float32(a), atol=0)
        # out-of-box proposal clips to the box.
        np.testing.assert_allclose(B.apply_mask(np.full(7, 9.0), "joint"),
                                   np.ones(7, np.float32), atol=0)

    def test_5_prv_only_pins_pumps(self):
        a = np.full(7, 0.5)
        out = B.apply_mask(a, "prv_only")
        np.testing.assert_allclose(out[:5], AM.as_float32(a)[:5], atol=0)   # free
        np.testing.assert_allclose(out[5:], NATIVE[5:], atol=0)             # pinned
        _, pump = AM.to_command(out)
        for p in A.PUMP_IDS:
            self.assertAlmostEqual(pump[p], A.NATIVE_PUMP_SPEED[p], places=5)

    def test_6_vsp_only_pins_valves(self):
        a = np.full(7, 0.5)
        out = B.apply_mask(a, "vsp_only")
        np.testing.assert_allclose(out[5:], AM.as_float32(a)[5:], atol=0)   # free
        np.testing.assert_allclose(out[:5], NATIVE[:5], atol=0)             # pinned
        prv, _ = AM.to_command(out)
        for v in A.PRV_IDS:
            self.assertAlmostEqual(prv[v], A.NATIVE_PRV_SETPOINT_PSI[v], places=5)

    def test_7_unknown_mode_raises(self):
        with self.assertRaises(KeyError):
            B.free_mask("bogus")


if __name__ == "__main__":
    unittest.main(verbosity=2)
