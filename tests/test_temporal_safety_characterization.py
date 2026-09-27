"""STEP 9 (WU-16) test battery for the TEMPORAL safety CHARACTERIZATION.

Standard-library `unittest` + numpy only (no pytest / gymnasium / torch). The
pure-function tests run without EPANET; the artefact tests validate the produced
results/phase6/p6_s9_temporal_safety_characterization.json and are skipped if it
is absent. This artefact is EVIDENCE ONLY: the tests assert that NO mechanism,
policy, or look-ahead horizon is selected/ranked/scored/recommended
(researcher_selection is null and no forbidden key token appears anywhere).

    .venv/Scripts/python.exe -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "validation"))
sys.path.insert(0, str(ROOT / "src" / "env"))

import p6_s9_temporal_safety_characterization as M  # noqa: E402

ART = ROOT / "results" / "phase6" / "p6_s9_temporal_safety_characterization.json"
_DATA = json.loads(ART.read_text(encoding="utf-8")) if ART.exists() else None

REQUIRED_KEYS = (
    "experiment_metadata", "metric_definitions", "temporal_candidates",
    "horizons_tested", "wu15_delayed_collapse_reproduction",
    "baseline_trajectory", "delayed_collapse_case", "trajectory_metrics",
    "single_step_metrics", "single_step_vs_trajectory", "temporal_rule_outputs",
    "action_persistence_cases", "tank_state_evolution", "pump_state_evolution",
    "native_rule_events", "computational_cost", "PPO_compatibility",
    "limitations", "researcher_selection")

# WU-15 anchors that WU-16 must reproduce from persisted data (PART 6).
WU15_DECISION_PSI = 5.527866840362549
WU15_SUSTAINED_PSI = 1.2946763038635254
BASELINE_LEAK_GPM = 84.72988433677985
BASELINE_WORST_PSI = 4.16452169418335


def _iter_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _iter_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_keys(v)


def _iter_numbers(obj):
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_numbers(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_numbers(v)


class TestPureHelpers(unittest.TestCase):
    def test_action_dim_and_bounds(self):
        self.assertEqual(M.ACTION_DIM, 7)
        self.assertEqual(len(M.ACTUATOR_ORDER), 7)
        self.assertEqual(len(M.ACT_BOUNDS), 7)

    def test_horizons_and_grids_are_provisional(self):
        # PART 9: H in {1,2,4,8} control steps; grids reuse the WU-15 sweep.
        self.assertEqual(M.HORIZONS_STEPS, [1, 2, 4, 8])
        self.assertEqual(list(M.TS1_THETA_P_PSI), [0.0, 5.0, 10.0, 15.0, 20.0])
        self.assertEqual(list(M.TS2_EPS_P_PSI), [0.0, 2.0, 5.0])
        self.assertEqual(list(M.TS3_EPS_D_PSI_NODESUM), [0.0, 2.0, 5.0])

    def test_encode_decode_round_trip(self):
        prv = {v: 0.5 * (lo + hi) for v, (lo, hi) in
               {k: M.ACT_BOUNDS[k] for k in M.R8.PRV_IDS}.items()}
        pump = {p: 0.5 * (lo + hi) for p, (lo, hi) in
                {k: M.ACT_BOUNDS[k] for k in M.R8.PUMP_IDS}.items()}
        a = M.encode_action(prv, pump)
        self.assertTrue(np.allclose(a, 0.0, atol=1e-12))
        prv2, pump2 = M.decode_action(a)
        for k in M.R8.PRV_IDS:
            self.assertAlmostEqual(prv2[k], prv[k], places=9)
        for k in M.R8.PUMP_IDS:
            self.assertAlmostEqual(pump2[k], pump[k], places=9)

    def test_safety_rules_semantics(self):
        # True == SAFE (do NOT intervene) -- shared with WU-15.
        self.assertTrue(M.rule_s1_safe(20.0, 20.0))
        self.assertFalse(M.rule_s1_safe(19.999, 20.0))
        self.assertTrue(M.rule_s2_safe(-1.0, 2.0))
        self.assertFalse(M.rule_s2_safe(-3.0, 2.0))
        self.assertTrue(M.rule_s3_safe(1.0, 2.0))
        self.assertFalse(M.rule_s3_safe(3.0, 2.0))
        self.assertTrue(M.rule_s4_safe(0.0))
        self.assertFalse(M.rule_s4_safe(1.0))

    def test_four_temporal_candidates_only(self):
        c = M.temporal_candidate_descriptors()
        self.assertEqual(set(c), {"TS1", "TS2", "TS3", "TS4"})


@unittest.skipUnless(_DATA is not None, "temporal artefact not generated yet")
class TestArtefact(unittest.TestCase):
    def test_all_required_keys_present(self):
        for f in REQUIRED_KEYS:
            self.assertIn(f, _DATA, f)

    def test_researcher_selection_is_null(self):
        self.assertIsNone(_DATA["researcher_selection"])

    def test_no_forbidden_key_tokens(self):
        forb = M.FORBIDDEN_KEY_TOKENS
        bad = sorted({k for k in _iter_keys(_DATA)
                      if any(t in str(k).lower() for t in forb)})
        self.assertEqual(bad, [], f"forbidden key tokens: {bad}")

    def test_all_numbers_finite(self):
        for x in _iter_numbers(_DATA):
            self.assertTrue(np.isfinite(x), x)

    def test_frozen_invariants(self):
        meta = _DATA["experiment_metadata"]
        self.assertEqual(meta["action_dim"], 7)
        self.assertEqual(meta["observation_dim"], 139)
        self.assertEqual(meta["n_service_junctions"], 121)
        self.assertEqual(meta["n_connector_junctions"], 5)
        self.assertEqual(meta["report_instants"], 193)
        self.assertEqual(meta["hydraulic_report_timestep_s"], 1800.0)

    def test_only_four_temporal_candidates(self):
        self.assertEqual(set(_DATA["temporal_candidates"]), {"TS1", "TS2", "TS3", "TS4"})

    def test_horizons_tested_are_provisional(self):
        h = _DATA["horizons_tested"]
        self.assertEqual(h["control_steps"], [1, 2, 4, 8, 192])
        self.assertEqual(h["hours"], [0.5, 1.0, 2.0, 4.0, 96.0])

    def test_baseline_reproduces_frozen_chronic_state(self):
        # PART 5: the native baseline trajectory, from persisted accounting.
        bt = _DATA["baseline_trajectory"]
        acc = bt["validated_accounting"]
        self.assertAlmostEqual(acc["leakage_mean_gpm"], BASELINE_LEAK_GPM, places=6)
        self.assertEqual(acc["n_node_timesteps_below_20psi"], 386)
        self.assertEqual(acc["n_node_timesteps_negative_pressure"], 0)
        self.assertAlmostEqual(
            bt["trajectory_metrics"]["p_min_horizon_psi"], BASELINE_WORST_PSI, places=5)

    def test_wu15_collapse_reproduced_within_tolerance(self):
        # PART 6: verify 5.53 / 1.29 reproduce from persisted WU-15 data.
        r = _DATA["wu15_delayed_collapse_reproduction"]
        tol = r["tolerance"]
        self.assertAlmostEqual(
            r["reproduced_decision_instant_p_min_psi"], WU15_DECISION_PSI, places=4)
        self.assertAlmostEqual(
            r["reproduced_sustained_worst_p_min_psi"], WU15_SUSTAINED_PSI, places=4)
        self.assertLess(r["decision_instant_abs_diff_psi"], tol)
        self.assertLess(r["sustained_worst_abs_diff_psi"], tol)
        self.assertLess(r["normalized_action_max_abs_diff"], 1e-9)
        # The sustained worst must be strictly BELOW the decision instant:
        # this IS the delayed-collapse phenomenon (PART 3/7).
        self.assertLess(
            r["reproduced_sustained_worst_p_min_psi"],
            r["reproduced_decision_instant_p_min_psi"])
        self.assertGreater(r["sustained_understatement_psi"], 0.0)

    def test_delayed_collapse_is_late_in_horizon(self):
        # The severe worst-node instant lands deep in the horizon, so any
        # finite look-ahead shorter than full understates the collapse.
        sev = _DATA["trajectory_metrics"]["prv_lower_pump_lower"]
        self.assertGreater(sev["t_pmin_report_index"], 8)
        self.assertLess(sev["p_min_horizon_psi"], sev["p_min_at_decision_instant_psi"])

    def test_single_step_vs_trajectory_views_present(self):
        for name in ("reference_nominal", "prv_lower_pump_lower", "prv_all_lower"):
            rec = _DATA["single_step_vs_trajectory"][name]
            self.assertIn("view_A_single_step_decision_instant", rec)
            self.assertIn("view_B_trajectory_over_full_horizon", rec)

    def test_short_horizon_misses_severe_collapse_TS1(self):
        # CENTRAL FINDING: TS1 at theta_p=5 does NOT activate on the severe
        # command for short look-aheads (H<=8) but DOES over the full horizon.
        # This is single-step non-activation followed by delayed deterioration.
        tr = _DATA["temporal_rule_outputs"]["prv_lower_pump_lower_vs_baseline"]
        ts1 = tr["TS1"]["theta_p_psi=5.0"]
        for h in ("H=1", "H=2", "H=4", "H=8"):
            self.assertFalse(ts1[h]["activates"], h)
        self.assertTrue(ts1["full"]["activates"])

    def test_negative_backstop_never_activates(self):
        # TS4: no swept in-bounds config produced a negative-pressure node at
        # any horizon -> standalone it gives no 20-psi protection.
        tr = _DATA["temporal_rule_outputs"]
        for seg in tr.values():
            for h, rec in seg["TS4"]["hard_backstop"].items():
                self.assertFalse(rec["activates"], h)

    def test_identity_hold_reproduces_chronic_ill_posedness(self):
        # PART 5/8: absolute-20 flags the baseline over the horizon;
        # relative TS2 never fires on an unchanged hold.
        ih = _DATA["temporal_rule_outputs"]["baseline_identity_hold"]
        self.assertTrue(ih["TS1"]["theta_p_psi=20.0"]["full"]["activates"])
        for h, rec in ih["TS2"]["eps_p_psi=0.0"].items():
            self.assertFalse(rec["activates"], h)

    def test_tank_state_evolution_present_for_severe(self):
        te = _DATA["tank_state_evolution"]["prv_lower_pump_lower"]
        self.assertIn("at_t0_ft", te)
        self.assertIn("tank_bounds_ft", te)


if __name__ == "__main__":
    unittest.main()
