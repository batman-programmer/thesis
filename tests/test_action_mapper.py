"""STAGE-D correctness battery: action encode/decode (D-P6-001/002/003).

Pure algebra, no EPANET -- fast. Verifies the FROZEN 7-dim action contract:
order, bounds, the absolute affine map, round-trip identity, native-point
reconstruction, out-of-box clipping, and the gym float32 cast. Run:

    .venv/Scripts/python.exe -m unittest tests.test_action_mapper -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

_SRC = Path(__file__).resolve().parents[1] / "src"
# env modules resolve their siblings by BARE name (import state_builder, etc.),
# so src/env and src/validation must be on the path -- the same bootstrap the
# driver and env use at runtime.
for _p in (str(_SRC / "env"), str(_SRC / "validation")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import action_mapper as AM  # noqa: E402

# Frozen contract (docs/PHASE6_ACTION_SPACE_SPEC.md), re-stated here as the
# INDEPENDENT oracle the module must match -- not imported from state_builder.
FROZEN_ORDER = ("VALVE-173", "VALVE-175", "VALVE-176", "VALVE-177", "VALVE-178",
                "PUMP-170", "PUMP-172")
FROZEN_LOW = np.array([54.5, 21.5, 20.0, 20.0, 20.0, 0.82, 0.77])
FROZEN_HIGH = np.array([100.0, 110.0, 59.524, 90.0, 74.0, 1.10, 1.10])
NATIVE_PRV = {"VALVE-173": 70.0, "VALVE-175": 55.0, "VALVE-176": 29.762,
              "VALVE-177": 45.0, "VALVE-178": 37.0}
NATIVE_PUMP = {"PUMP-170": 1.0, "PUMP-172": 1.0}


class TestActionMapper(unittest.TestCase):
    def test_1_dim_order_bounds(self):
        self.assertEqual(AM.ACTION_DIM, 7)
        self.assertEqual(AM.ACTION_IDS, FROZEN_ORDER)
        np.testing.assert_allclose(AM.ACTION_LOW, FROZEN_LOW, atol=0)
        np.testing.assert_allclose(AM.ACTION_HIGH, FROZEN_HIGH, atol=0)

    def test_2_affine_endpoints_and_midpoint(self):
        # a = -1 -> lower, a = +1 -> upper, a = 0 -> exact midpoint.
        np.testing.assert_allclose(AM.to_physical(-np.ones(7)), FROZEN_LOW, atol=0)
        np.testing.assert_allclose(AM.to_physical(np.ones(7)), FROZEN_HIGH, atol=0)
        np.testing.assert_allclose(AM.to_physical(np.zeros(7)),
                                   0.5 * (FROZEN_LOW + FROZEN_HIGH), rtol=1e-12)

    def test_3_roundtrip_identity(self):
        rng = np.random.default_rng(0)
        for _ in range(1000):
            a = rng.uniform(-1.0, 1.0, size=7)
            np.testing.assert_allclose(AM.to_normalized(AM.to_physical(a)), a,
                                       atol=1e-12)
        # and physical -> normalized -> physical
        for _ in range(1000):
            phys = FROZEN_LOW + rng.uniform(0, 1, size=7) * (FROZEN_HIGH - FROZEN_LOW)
            np.testing.assert_allclose(AM.to_physical(AM.to_normalized(phys)), phys,
                                       rtol=1e-12)

    def test_4_native_reconstruction(self):
        a = AM.command_to_normalized(NATIVE_PRV, NATIVE_PUMP)
        self.assertEqual(a.shape, (7,))
        self.assertTrue(np.all(a >= -1.0) and np.all(a <= 1.0))
        prv, pump = AM.to_command(a)
        for v in FROZEN_ORDER[:5]:
            self.assertAlmostEqual(prv[v], NATIVE_PRV[v], places=9)
        for p in ("PUMP-170", "PUMP-172"):
            self.assertAlmostEqual(pump[p], NATIVE_PUMP[p], places=9)

    def test_5_out_of_box_clips(self):
        # proposals past the box saturate at the nearest actuator bound.
        np.testing.assert_allclose(AM.to_physical(np.full(7, 5.0)), FROZEN_HIGH, atol=0)
        np.testing.assert_allclose(AM.to_physical(np.full(7, -5.0)), FROZEN_LOW, atol=0)
        # physical beyond the box -> normalized clips to +/-1.
        over = FROZEN_HIGH + 10.0
        np.testing.assert_allclose(AM.to_normalized(over), np.ones(7), atol=0)

    def test_6_to_command_split_keys(self):
        a = np.linspace(-0.9, 0.9, 7)
        prv, pump = AM.to_command(a)
        self.assertEqual(tuple(prv.keys()), FROZEN_ORDER[:5])
        self.assertEqual(tuple(pump.keys()), ("PUMP-170", "PUMP-172"))
        phys = AM.to_physical(a)
        for i, v in enumerate(FROZEN_ORDER[:5]):
            self.assertAlmostEqual(prv[v], float(phys[i]), places=12)

    def test_7_as_float32_dtype_shape_clip(self):
        out = AM.as_float32([2.0, -2.0, 0.0, 0.3, -0.3, 1.0, -1.0])
        self.assertEqual(out.dtype, np.float32)
        self.assertEqual(out.shape, (7,))
        self.assertTrue(np.all(out >= -1.0) and np.all(out <= 1.0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
