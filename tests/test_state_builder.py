"""STEP 7 test battery for the deterministic observation builder.

Nine tests mandated by the Phase 6 brief (§24). Uses only the standard-library
`unittest` and numpy so it runs without pytest / gymnasium / torch. Run:

    .venv/Scripts/python.exe -m unittest discover -s tests -v
"""

from __future__ import annotations

import math
import sys
import unittest
from dataclasses import fields
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from env.state_builder import (  # noqa: E402
    ObservationConfig, RawState, build_observation, observation_bounds,
)

TANK_BOUNDS = {"TANK-130": (0.0, 32.1), "TANK-131": (0.0, 41.9)}
SERVICE = tuple(f"S{i}" for i in range(121))
CONNECTORS = ("JUNCTION-105", "JUNCTION-106", "JUNCTION-109",
              "JUNCTION-110", "JUNCTION-128")
SENTINEL = 999.0  # a connector pressure that must never reach the observation


def make_config() -> ObservationConfig:
    return ObservationConfig(
        service_nodes=SERVICE,
        connector_nodes=CONNECTORS,
        tank_ids=("TANK-130", "TANK-131"),
        tank_level_bounds_ft=TANK_BOUNDS,
    )


def make_raw(cfg: ObservationConfig, *, pressure=140.0, tank_frac=0.5,
             prv_frac=0.5, prv_active=True, pump_cmd_frac=0.5,
             pump_realized=None, time_s=0.0) -> RawState:
    pressures = {n: pressure for n in cfg.service_nodes}
    # connector nodes carry a sentinel that must be excluded from the vector
    for c in cfg.connector_nodes:
        pressures[c] = SENTINEL
    tanks = {t: lo + tank_frac * (hi - lo)
             for t, (lo, hi) in cfg.tank_level_bounds_ft.items()}
    prv_sp = {v: lo + prv_frac * (hi - lo)
              for v, (lo, hi) in cfg.prv_bounds_psi.items()}
    prv_act = {v: prv_active for v in cfg.prv_ids}
    pump_cmd = {u: lo + pump_cmd_frac * (hi - lo)
                for u, (lo, hi) in cfg.pump_bounds.items()}
    if pump_realized is None:
        pump_realized = {u: cfg.pump_bounds[u][0] for u in cfg.pump_ids}
    return RawState(
        pressures_psi=pressures, tank_levels_ft=tanks,
        prev_cmd_prv_setpoint_psi=prv_sp, prv_is_active=prv_act,
        prev_cmd_pump_speed=pump_cmd, pump_realized_speed=pump_realized,
        sim_time_s=time_s,
    )


class TestStateBuilder(unittest.TestCase):
    def setUp(self):
        self.cfg = make_config()

    def test_1_shape_constant(self):
        for kwargs in ({}, dict(time_s=43200.0), dict(prv_active=False),
                       dict(pressure=10.0, tank_frac=0.9)):
            obs = build_observation(self.cfg, make_raw(self.cfg, **kwargs))
            self.assertEqual(obs.shape, (139,))
            self.assertEqual(self.cfg.dim, 139)

    def test_2_dtype_constant(self):
        obs = build_observation(self.cfg, make_raw(self.cfg))
        self.assertEqual(obs.dtype, np.float32)

    def test_3_no_nan_inf(self):
        for kwargs in ({}, dict(pressure=-1e6), dict(pressure=1e6),
                       dict(time_s=345600.0), dict(pump_realized={
                           "PUMP-170": 0.0, "PUMP-172": 0.0})):
            obs = build_observation(self.cfg, make_raw(self.cfg, **kwargs))
            self.assertTrue(np.all(np.isfinite(obs)))

    def test_4_deterministic_normalization(self):
        obs = build_observation(self.cfg, make_raw(
            self.cfg, pressure=140.0, tank_frac=0.5, prv_frac=0.5,
            pump_cmd_frac=0.5, time_s=0.0))
        sl = self.cfg.slices()
        # pressure 140 psi over band [-20, 300] -> exactly 0.5
        np.testing.assert_allclose(obs[sl["pressures"]], 0.5, atol=1e-6)
        np.testing.assert_allclose(obs[sl["tank_levels"]], 0.5, atol=1e-6)
        np.testing.assert_allclose(obs[sl["prev_cmd_prv_setpoint"]], 0.5,
                                   atol=1e-6)
        # realized pump defaults to lower bound -> lower/upper
        exp = [self.cfg.pump_bounds[u][0] / self.cfg.pump_bounds[u][1]
               for u in self.cfg.pump_ids]
        np.testing.assert_allclose(obs[sl["pump_realized_speed"]], exp,
                                   atol=1e-6)
        # time 0 -> sin 0, cos 1
        np.testing.assert_allclose(obs[sl["time_of_day"]], [0.0, 1.0],
                                   atol=1e-6)
        # bounds sanity
        low, high = observation_bounds(self.cfg)
        self.assertTrue(np.all(obs >= low - 1e-6))
        self.assertTrue(np.all(obs <= high + 1e-6))

    def test_5_same_state_same_obs(self):
        raw = make_raw(self.cfg, time_s=21600.0)
        a = build_observation(self.cfg, raw)
        b = build_observation(self.cfg, raw)
        self.assertTrue(np.array_equal(a, b))

    def test_6_different_state_expected_diff(self):
        base = build_observation(self.cfg, make_raw(self.cfg))
        # perturb exactly one service node
        raw2 = make_raw(self.cfg)
        raw2.pressures_psi[self.cfg.service_nodes[7]] = 200.0
        obs2 = build_observation(self.cfg, raw2)
        diff = np.flatnonzero(~np.isclose(base, obs2))
        self.assertEqual(list(diff), [7])
        # perturb one tank only
        raw3 = make_raw(self.cfg)
        raw3.tank_levels_ft["TANK-131"] = 41.9
        obs3 = build_observation(self.cfg, raw3)
        sl = self.cfg.slices()
        changed = np.flatnonzero(~np.isclose(base, obs3))
        self.assertEqual(list(changed), [sl["tank_levels"].start + 1])

    def test_7_no_future_information(self):
        # contract test: RawState exposes only current/past quantities; no field
        # names a future/forecast/next-step or a raw demand signal.
        banned = ("future", "forecast", "next", "demand", "ahead", "predict")
        for f in fields(RawState):
            low = f.name.lower()
            self.assertFalse(any(b in low for b in banned),
                             f"RawState.{f.name} may leak future/demand info")
        # time encoding at t depends only on t (current), verified by determinism
        r = make_raw(self.cfg, time_s=1000.0)
        self.assertTrue(np.array_equal(build_observation(self.cfg, r),
                                       build_observation(self.cfg, r)))

    def test_8_connector_exclusion(self):
        raw = make_raw(self.cfg)  # connectors set to SENTINEL=999 psi
        obs = build_observation(self.cfg, raw)
        sl = self.cfg.slices()
        sentinel_norm = min(1.0, max(0.0, (SENTINEL - self.cfg.p_min_psi)
                                     / (self.cfg.p_max_psi - self.cfg.p_min_psi)))
        press = obs[sl["pressures"]]
        # sentinel would normalize to 1.0 (clipped); no pressure entry may be it
        self.assertFalse(np.any(np.isclose(press, sentinel_norm)))
        for c in self.cfg.connector_nodes:
            self.assertNotIn(c, self.cfg.service_nodes)

    def test_9_prev_action_semantics(self):
        # pump commanded 0.90 but native reopen realized 1.10 -> distinct blocks
        raw = make_raw(self.cfg)
        raw.prev_cmd_pump_speed["PUMP-170"] = 0.90
        raw.pump_realized_speed["PUMP-170"] = 1.10
        obs = build_observation(self.cfg, raw)
        sl = self.cfg.slices()
        cmd = obs[sl["prev_cmd_pump_speed"]][0]
        realized = obs[sl["pump_realized_speed"]][0]
        self.assertFalse(math.isclose(cmd, realized),
                         "commanded and realized pump speed must stay distinct")
        # commanded 0.90 in [0.82,1.10] -> (0.90-0.82)/0.28; realized 1.10 -> 1.0
        self.assertAlmostEqual(cmd, (0.90 - 0.82) / (1.10 - 0.82), places=5)
        self.assertAlmostEqual(realized, 1.0, places=5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
