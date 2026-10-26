"""F1 regression: pump REALIZED speed must be 0.0 when EPANET reports the link Closed.

A Closed pump retains its commanded speed in the binary result's ``setting``
column (EPANET stores the last speed value even though the link is closed).
The frozen observation contract (state_builder: "pump REALIZED speeds
(0 = closed)") requires realized speed to be 0.0 at Closed status, independent
of the *commanded* speed. This suite exercises the REAL ``_extract`` path and
the full observation assembly; it never supplies realized_speed by hand.

The real-EPANET case uses a small fixture network built in memory (not the
thesis INP): PUMP-170 is built Closed-at-init while PUMP-172 runs Open at
speed 1.0, so the status column distinguishes the two actuators. Solver
scratch stays in the WNTR temp directory, never in results/.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

_SRC = Path(__file__).resolve().parents[1] / "src"
for _p in (str(_SRC / "env"), str(_SRC / "validation")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import epanet_adapter as A  # noqa: E402
import bwsn_env as E  # noqa: E402
import g6_g7_g8_leak_pda as L  # noqa: E402
import p6_s3_prv_finechar as S3  # noqa: E402
import state_builder as SB  # noqa: E402
from wntr.network.base import LinkStatus  # noqa: E402

PUMPS = list(A.PUMP_IDS)                       # ["PUMP-170", "PUMP-172"]
CLOSED = int(LinkStatus.Closed)              # 0
OPEN = int(LinkStatus.Open)                  # 1
SETTINGS = {"PUMP-170": 0.5, "PUMP-172": 1.0}

_JUNC = None
_TANKS = None


def _ref_wn():
    global _JUNC, _TANKS
    if _JUNC is None:
        ref = S3.build(None, None)
        _JUNC = list(ref.junction_name_list)
        _TANKS = list(ref.tank_name_list)
        _ref_wn.ref = ref
    return _ref_wn.ref


def _fake_wn():
    """Minimal working-network stand-in consumed by ``_extract``.

    Real junction/tank ids from the frozen network; node elevations and pump
    endpoints are taken from the live INP so tank-level and power math match
    production paths.
    """
    ref = _ref_wn()
    nodes = {n: SimpleNamespace(elevation=float(ref.get_node(n).elevation))
             for n in list(ref.junction_name_list) + list(ref.tank_name_list)}
    links = {p: SimpleNamespace(
        start_node_name=ref.get_link(p).start_node_name,
        end_node_name=ref.get_link(p).end_node_name) for p in PUMPS}
    return SimpleNamespace(
        junction_name_list=list(ref.junction_name_list),
        tank_name_list=list(ref.tank_name_list),
        get_node=lambda n: nodes[n],
        get_link=lambda l: links[l])


def _fake_res(wn):
    """One-row EPANET result: PUMP-170 Closed@0.5, PUMP-172 Open@1.0."""
    idx = pd.Index([0])
    node = {
        "pressure": pd.DataFrame({j: [50.0] for j in wn.junction_name_list},
                                 index=idx),
        "head": pd.DataFrame({n: [100.0] for n in
                              wn.junction_name_list + wn.tank_name_list},
                             index=idx),
        "demand": pd.DataFrame({j: [0.0] for j in wn.junction_name_list},
                               index=idx),
    }
    status_vals = {**{v: 2 for v in A.PRV_IDS},
                   **{"PUMP-170": CLOSED, "PUMP-172": OPEN}}
    setting_vals = {**{v: 50.0 for v in A.PRV_IDS}, **SETTINGS}
    link = {
        "status": pd.DataFrame({k: [v] for k, v in status_vals.items()},
                               index=idx),
        "setting": pd.DataFrame({k: [v] for k, v in setting_vals.items()},
                                index=idx),
        "flowrate": pd.DataFrame({k: [0.0] for k in list(A.PRV_IDS) + PUMPS},
                                 index=idx),
    }
    return SimpleNamespace(node=node, link=link)


def _driver():
    d = A.SteppingHydraulicDriver.__new__(A.SteppingHydraulicDriver)
    wn = _fake_wn()
    d._svc = list(wn.junction_name_list)
    d._req_gpm = None
    d.cfg = A.DriverConfig(coeff_us={}, service_nodes=d._svc, connector_nodes=[])
    return d, wn


# --------------------------------------------------------------------------- #
# Isolation helpers (context-managed; restore globals and clean scratch)       #
# --------------------------------------------------------------------------- #
from contextlib import contextmanager  # noqa: E402


@contextmanager
def _isolated_epanet_scratch():
    """Point ``phase5_common.RESULTS`` at a fresh temp dir for ONE test.

    ``L._run_with_retry`` writes solver scratch under ``C.RESULTS/_tmp``; the
    real ``results/phase5/_tmp`` holds tracked historical evidence. The global
    is restored in ``finally`` so even a failing test cannot leak the override,
    and the whole temp tree is removed afterwards.
    """
    import shutil
    import tempfile
    import phase5_common as C
    original = C.RESULTS
    tmp = Path(tempfile.mkdtemp(prefix="p6_f1_scratch_"))
    try:
        C.RESULTS = tmp
        yield tmp
    finally:
        C.RESULTS = original
        shutil.rmtree(tmp, ignore_errors=True)


@contextmanager
def _closed_pump_fixture():
    """Small in-memory EPANET network: PUMP-170 Closed@1.0, PUMP-172 Open@1.0.

    Not the thesis INP: a two-tank fixture whose only purpose is to make EPANET
    report a Closed link that still carries a nonzero ``setting`` -- the exact
    defect under test. The fixture leaves no on-disk state.
    """
    import wntr
    wn = wntr.network.WaterNetworkModel()
    wn.add_junction("J0", base_demand=0.01, elevation=0.0)
    wn.add_reservoir("R0", base_head=100.0)
    wn.add_tank("T0", elevation=50.0, init_level=5.0, min_level=0.0,
                max_level=20.0, diameter=20.0)
    wn.add_tank("T1", elevation=50.0, init_level=5.0, min_level=0.0,
                max_level=20.0, diameter=20.0)
    wn.add_pipe("P0", "R0", "J0", length=1000.0, diameter=0.3,
                roughness=100.0)
    wn.add_curve("C0", "HEAD", [(0.0, 100.0), (0.02, 50.0)])
    wn.add_pump("PUMP-170", "J0", "T0", pump_type="HEAD",
                pump_parameter="C0", speed=1.0)
    wn.add_pump("PUMP-172", "J0", "T1", pump_type="HEAD",
                pump_parameter="C0", speed=1.0)
    wn.get_link("PUMP-170").initial_status = LinkStatus.Closed
    yield wn


class TestPumpRealizedSpeedExtraction(unittest.TestCase):
    """``_extract`` must convert EPANET (status, setting) into realized speed."""

    def setUp(self):
        d, wn = _driver()
        self.sr = d._extract(wn, _fake_res(wn), step_index=0,
                             sim_time_s=1800.0, row=-1)

    def test_closed_pump_nonzero_setting_realizes_zero(self):
        self.assertEqual(self.sr.pump_status["PUMP-170"], CLOSED)
        self.assertEqual(self.sr.pump_realized_speed["PUMP-170"], 0.0,
                         "Closed pump carrying setting=0.5 must realize 0.0")

    def test_open_pump_setting_preserved(self):
        self.assertEqual(self.sr.pump_status["PUMP-172"], OPEN)
        self.assertEqual(self.sr.pump_realized_speed["PUMP-172"], 1.0)

    def test_both_controlled_pumps_covered(self):
        # Keyed on the status column for every PUMP_IDS entry, not a pump-name
        # special case: Open preserves setting, Closed -> 0.
        self.assertEqual(self.sr.pump_realized_speed["PUMP-170"], 0.0)
        self.assertEqual(self.sr.pump_realized_speed["PUMP-172"], 1.0)

    def test_observation_realized_block_and_commanded_independence(self):
        cfg = E.make_observation_config(_ref_wn())
        sl = cfg.slices()
        obs = SB.build_observation(cfg, SB.RawState(
            pressures_psi=self.sr.pressures_psi,
            tank_levels_ft=self.sr.tank_levels_ft,
            prev_cmd_prv_setpoint_psi=dict(A.NATIVE_PRV_SETPOINT_PSI),
            prv_is_active=self.sr.prv_is_active,
            prev_cmd_pump_speed=dict(A.NATIVE_PUMP_SPEED),   # commanded = 1.0
            pump_realized_speed=self.sr.pump_realized_speed,
            sim_time_s=self.sr.sim_time_s,
        ))
        self.assertEqual(obs.shape, (139,))
        self.assertEqual(obs.dtype, np.float32)
        realized = obs[sl["pump_realized_speed"]]
        commanded = obs[sl["prev_cmd_pump_speed"]]
        self.assertEqual(float(realized[0]), 0.0,
                         "closed PUMP-170 realized observation component")
        self.assertAlmostEqual(float(realized[1]), 1.0 / 1.10, places=6)
        # commanded block holds the EXECUTED action (native 1.0), not the
        # realized 0.0 — the two blocks must stay distinct.
        lo170, hi170 = cfg.pump_bounds["PUMP-170"]
        self.assertAlmostEqual(float(commanded[0]),
                               (1.0 - lo170) / (hi170 - lo170), places=6)
        self.assertNotEqual(float(commanded[0]), float(realized[0]))

    def test_observation_bounds_contract(self):
        cfg = E.make_observation_config(_ref_wn())
        low, high = SB.observation_bounds(cfg)
        self.assertEqual(cfg.dim, 139)
        start = cfg.slices()["pump_realized_speed"].start
        self.assertEqual(float(low[start]), 0.0)
        self.assertEqual(float(high[start]), 1.0)


class TestPumpRealizedSpeedRealEpanet(unittest.TestCase):
    """Bounded real-EPANET check through the production ``_extract`` path.

    Fixture network only (in-memory, never persisted): PUMP-170 Closed@1.0 and
    PUMP-172 Open@1.0 each lift J0 water into identical tanks. Asserts EPANET
    really reports Closed-with-nonzero-setting — the defect — and that
    ``_extract`` returns the contracted realized speeds.
    """

    def test_extract_on_real_epanet_result(self):
        def _body(wn):
            res, _msgs, _used = L._run_with_retry(
                wn, "p6_f1_closed_pump_fixture")

            # The defect exists in raw EPANET output: Closed + nonzero setting.
            st = res.link["status"]
            setting = res.link["setting"]
            self.assertEqual(int(st["PUMP-170"].iloc[-1]), CLOSED)
            self.assertGreater(float(setting["PUMP-170"].iloc[-1]), 0.0)
            self.assertEqual(int(st["PUMP-172"].iloc[-1]), OPEN)
            self.assertAlmostEqual(float(setting["PUMP-172"].iloc[-1]), 1.0)

            # The real ``_extract`` also reads PRV status/setting columns; pad
            # them onto the fixture result with solver-plausible placeholders so
            # the SAME code path runs, exactly like production. Fixture-only.
            import pandas as _pd
            idx = res.link["status"].index
            res.link["status"] = _pd.concat(
                [st, _pd.DataFrame({v: 2 for v in A.PRV_IDS}, index=idx)],
                axis=1)
            res.link["setting"] = _pd.concat(
                [setting, _pd.DataFrame({v: 50.0 for v in A.PRV_IDS},
                                       index=idx)], axis=1)
            res.link["flowrate"] = _pd.concat(
                [res.link["flowrate"],
                 _pd.DataFrame({v: 0.0 for v in A.PRV_IDS}, index=idx)], axis=1)

            d, _ = _driver()
            d._svc = ["J0"]         # fixture's only service node
            sr = d._extract(wn, res, step_index=0, sim_time_s=3600.0, row=-1)
            self.assertEqual(sr.pump_realized_speed["PUMP-170"], 0.0)
            self.assertEqual(sr.pump_realized_speed["PUMP-172"], 1.0)

        with _isolated_epanet_scratch(), _closed_pump_fixture() as wn:
            _body(wn)


if __name__ == "__main__":
    unittest.main(verbosity=2)
