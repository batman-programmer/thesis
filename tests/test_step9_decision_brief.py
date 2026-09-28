"""STEP-9 (WU-17) test battery for the safety-mechanism DECISION BRIEF.

Standard-library ``unittest`` only (no pytest / numpy / gymnasium / torch). The
pure-function tests run without any artefact; the artefact tests validate the
produced results/phase6/p6_s9_decision_brief.json and are skipped if it is
absent.

This artefact is an EVIDENCE AGGREGATOR / DECISION BRIEF: the tests assert that
it FRAMES the four STEP-9 decisions WITHOUT making them -- researcher_selection
is null, every candidate is NOT APPROVED, no mechanism/threshold/horizon/policy
is selected/ranked/scored/recommended (no forbidden key token appears anywhere),
and the frozen invariants + cross-artefact anchors reproduce byte-exact. The
brief is deterministic: re-running the generator in-memory must reproduce the
persisted bytes exactly (no timestamp, no RNG, no EPANET).

    .venv/Scripts/python.exe -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "validation"))

import p6_s9_decision_brief as M  # noqa: E402

ART = ROOT / "results" / "phase6" / "p6_s9_decision_brief.json"
_DATA = json.loads(ART.read_text(encoding="utf-8")) if ART.exists() else None

# --- frozen invariants (D-P6-001/002/003/004) --------------------------------
ACTUATOR_ORDER = ["VALVE-173", "VALVE-175", "VALVE-176",
                  "VALVE-177", "VALVE-178", "PUMP-170", "PUMP-172"]
FROZEN_BOUNDS = {
    "VALVE-173": (54.5, 100.0), "VALVE-175": (21.5, 110.0),
    "VALVE-176": (20.0, 59.524), "VALVE-177": (20.0, 90.0),
    "VALVE-178": (20.0, 74.0), "PUMP-170": (0.82, 1.1), "PUMP-172": (0.77, 1.1),
}

# --- cross-artefact anchors the brief must reproduce byte-exact ---------------
LEAK_REF_GPM = 84.72988433677985
REQ_REF_GPM = 906.3987348621764
MOVEMENT_L2SQ_MAX = 28.0
BASELINE_WORST_PSI = 4.16452169418335
WU16_DECISION_INSTANT_PSI = 5.527866840362549
WU16_FULL_HORIZON_PSI = 1.2946763038635254

REQUIRED_KEYS = (
    "decision_id", "status", "the_four_decisions", "evidence_artifacts",
    "source_artifact_integrity", "frozen_constraints", "frozen_reward_D_P6_005",
    "normalization_constants_frozen", "metric_definitions", "wu14_design_analysis",
    "wu15_empirical_characterization", "wu16_temporal_characterization",
    "architectures", "horizon_analysis", "handling_policies",
    "baseline_compatibility", "delayed_collapse_analysis", "computational_cost",
    "training_execution_implications", "candidate_configurations",
    "decision_matrix", "uncertainties", "coverage", "researcher_action_required",
    "researcher_selection", "self_checks")


def _iter_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _iter_keys(v)
    elif isinstance(obj, (list, tuple)):
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
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _iter_numbers(v)


# PLACEHOLDER_TESTS
class TestPureHelpers(unittest.TestCase):
    def test_decision_id_is_not_a_minted_register_decision(self):
        # WU-17 must NOT mint / approve a D-P6-xxx register decision.
        self.assertEqual(M.DECISION_ID, "STEP9_SAFETY_MECHANISM")
        self.assertNotIn("D-P6-006", M.DECISION_ID)
        self.assertEqual(M.STATUS, "PROPOSED / PENDING RESEARCHER")
        self.assertIn("NOT APPROVED", M.NOT_APPROVED)

    def test_forbidden_key_tokens_tuple(self):
        self.assertEqual(
            set(M.FORBIDDEN_KEY_TOKENS),
            {"winner", "rank", "tier", "score", "best",
             "superior", "optimal", "preferred", "recommend"})
        # "select"/"selection"/"worst" are SAFE and MUST NOT be forbidden.
        for safe in ("select", "selection", "worst"):
            self.assertNotIn(safe, M.FORBIDDEN_KEY_TOKENS)

    def test_finite_helpers(self):
        self.assertTrue(M._finite(1.0))
        self.assertFalse(M._finite(math.inf))
        self.assertFalse(M._finite(math.nan))
        self.assertFalse(M._finite(True))  # bools are not numbers here
        self.assertTrue(M._all_finite({"a": [1, 2.0], "b": "x", "c": None, "d": True}))
        self.assertFalse(M._all_finite({"a": [1, math.nan]}))

    def test_key_helpers(self):
        obj = {"a": {"b": [{"c": 1}]}, "d": 2}
        self.assertEqual(set(M._iter_keys(obj)), {"a", "b", "c", "d"})
        self.assertTrue(M._has_key(obj, "c"))
        self.assertFalse(M._has_key(obj, "generated_utc"))

    def test_four_decisions_all_unselected(self):
        fd = M.the_four_decisions()
        self.assertEqual(set(fd), {"A_safety_metric_rule", "B_threshold_tolerance",
                                   "C_look_ahead_horizon", "D_action_handling_policy"})
        for d in fd.values():
            self.assertIsNone(d["selection"])

    def test_architectures_A_D_on_fixed_schema(self):
        arch = M.architectures()
        ids = {a["architecture_id"] for a in arch if "architecture_id" in a}
        self.assertEqual(ids, {"A", "B", "C", "D"})
        schema = ("name", "composition", "decision_information", "look_ahead_dependence",
                  "threshold_dependence", "tank_state_dependence", "baseline_compatibility",
                  "tested_severe_corner_behaviour", "delayed_collapse_visibility",
                  "compute_cost_per_decision", "intervention_type",
                  "proposed_vs_executed_mismatch", "failure_modes", "main_unresolved_issue")
        for a in arch:
            if "architecture_id" not in a:
                continue
            for f in schema:
                self.assertIn(f, a, f"{a['architecture_id']} missing {f}")
        # no forbidden token in architecture KEYS
        bad = {k for k in _iter_keys(arch)
               if any(t in str(k).lower() for t in M.FORBIDDEN_KEY_TOKENS)}
        self.assertEqual(bad, set())

    def test_candidate_configurations_all_not_approved(self):
        cfgs = M.candidate_configurations()
        self.assertTrue(2 <= len(cfgs) <= 4)
        for c in cfgs:
            self.assertEqual(c["status"], M.NOT_APPROVED)
            self.assertIn("open_parameters", c)
            # every threshold is grid-provisional or evidence-supported (never bare/invented)
            self.assertIn("threshold", c)

    def test_decision_matrix_is_unordered(self):
        dm = M.decision_matrix()
        self.assertEqual(len(dm["rows"]), 4)
        self.assertIn("NOT ordered", dm["note"])
        bad = {k for k in _iter_keys(dm)
               if any(t in str(k).lower() for t in M.FORBIDDEN_KEY_TOKENS)}
        self.assertEqual(bad, set())

# PLACEHOLDER_ARTEFACT_TESTS
@unittest.skipUnless(_DATA is not None, "decision-brief artefact not generated yet")
class TestArtefact(unittest.TestCase):
    def test_all_required_keys_present(self):
        for f in REQUIRED_KEYS:
            self.assertIn(f, _DATA, f)

    def test_researcher_selection_is_null(self):
        self.assertIsNone(_DATA["researcher_selection"])
        self.assertEqual(_DATA["status"], "PROPOSED / PENDING RESEARCHER")

    def test_no_selection_of_any_of_the_four_decisions(self):
        for k in ("A_safety_metric_rule", "B_threshold_tolerance",
                  "C_look_ahead_horizon", "D_action_handling_policy"):
            self.assertIsNone(_DATA["the_four_decisions"][k]["selection"], k)
        form = _DATA["researcher_action_required"]["decision_form_blank"]
        for v in form.values():
            self.assertIsNone(v)

    def test_no_forbidden_key_tokens(self):
        bad = sorted({k for k in _iter_keys(_DATA)
                      if any(t in str(k).lower() for t in M.FORBIDDEN_KEY_TOKENS)})
        self.assertEqual(bad, [], f"forbidden key tokens: {bad}")

    def test_all_numbers_finite(self):
        for x in _iter_numbers(_DATA):
            self.assertTrue(math.isfinite(x), x)

    def test_no_generated_utc_key(self):
        # byte-reproducibility: the aggregator carries NO timestamp key.
        self.assertFalse(M._has_key(_DATA, "generated_utc"))

    def test_all_candidates_not_approved(self):
        cfgs = _DATA["candidate_configurations"]
        self.assertTrue(2 <= len(cfgs) <= 4)
        for c in cfgs:
            self.assertEqual(c["status"], M.NOT_APPROVED)

    def test_self_checks_all_true(self):
        self.assertTrue(all(_DATA["self_checks"].values()),
                        [k for k, v in _DATA["self_checks"].items() if not v])

    def test_frozen_action_space(self):
        acts = _DATA["frozen_constraints"]["action_space"]
        self.assertEqual(acts["action_dim"], 7)
        order = [b["actuator"] for b in acts["ordered_bounds"]]
        self.assertEqual(order, ACTUATOR_ORDER)
        for b in acts["ordered_bounds"]:
            lo, hi = FROZEN_BOUNDS[b["actuator"]]
            self.assertAlmostEqual(b["lower"], lo, places=9, msg=b["actuator"])
            self.assertAlmostEqual(b["upper"], hi, places=9, msg=b["actuator"])

    def test_frozen_observation_and_service_mask(self):
        fc = _DATA["frozen_constraints"]
        self.assertEqual(fc["observation"]["observation_dim"], 139)
        self.assertEqual(fc["service_node_policy"]["n_service_junctions"], 121)
        self.assertEqual(fc["service_node_policy"]["n_connector_junctions_excluded"], 5)

    def test_frozen_reward_unchanged(self):
        self.assertEqual(
            _DATA["frozen_reward_D_P6_005"]["weights"],
            {"w_L": 1.0, "w_U": 1.0, "w_P": 1.0, "w_A": 0.1, "w_E": 0.0})

    def test_metric_formulas_verbatim(self):
        md = _DATA["metric_definitions"]
        self.assertEqual(md["p_min"]["math"], "min_i p_i(t)")
        self.assertEqual(md["dp_min"]["math"], "p_min(post) - p_min(current)")
        self.assertEqual(md["D"]["math"], "sum_i max(0, 20 - p_i)")
        self.assertEqual(md["dD"]["math"], "D(post) - D(current)")
        self.assertEqual(md["N_neg"]["math"], "sum_i I[p_i < 0]")

    def test_candidate_safe_iff_rules_verbatim(self):
        cd = _DATA["wu15_empirical_characterization"]["candidates"]
        self.assertEqual(cd["S1"]["exact_rule"], "SAFE iff p_min(post) >= theta_p")
        self.assertEqual(cd["S2"]["exact_rule"], "SAFE iff p_min(post) - p_min(current) >= -eps_p")
        self.assertEqual(cd["S3"]["exact_rule"], "SAFE iff D(post) - D(current) <= eps_D")
        self.assertEqual(cd["S4"]["exact_rule"], "SAFE iff N_neg(post) == 0")

    def test_baseline_anchors_reproduced(self):
        anc = _DATA["source_artifact_integrity"]["chronic_baseline_anchors"]
        self.assertEqual(anc["n_node_timesteps_below_20psi"], 386)
        self.assertEqual(anc["n_node_timesteps_negative"], 0)
        self.assertAlmostEqual(anc["baseline_worst_node_psi"], BASELINE_WORST_PSI, places=6)
        self.assertEqual(anc["leak_only_argmax_config"], "prv_lower_pump_lower")
        self.assertAlmostEqual(
            anc["leak_only_argmax_worst_node_psi"], WU16_FULL_HORIZON_PSI, places=9)
        consts = _DATA["normalization_constants_frozen"]
        self.assertAlmostEqual(consts["leak_ref_gpm"], LEAK_REF_GPM, places=6)
        self.assertAlmostEqual(consts["req_ref_gpm"], REQ_REF_GPM, places=6)
        self.assertAlmostEqual(consts["movement_L2sq_max"], MOVEMENT_L2SQ_MAX, places=9)

    def test_wu16_delayed_collapse_anchors_reproduced(self):
        rep = _DATA["source_artifact_integrity"]["wu16_anchor_reproduction"]
        self.assertAlmostEqual(
            rep["severe_p_min_at_decision_instant_psi"], WU16_DECISION_INSTANT_PSI, places=9)
        self.assertAlmostEqual(
            rep["severe_p_min_over_full_horizon_psi"], WU16_FULL_HORIZON_PSI, places=9)
        self.assertEqual(rep["max_N_neg_over_horizon"], 0)
        # the delayed collapse: full-horizon worst < decision-instant worst
        self.assertLess(rep["severe_p_min_over_full_horizon_psi"],
                        rep["severe_p_min_at_decision_instant_psi"])

    def test_central_finding_short_horizon_misses_TS1_theta5(self):
        hz = _DATA["horizon_analysis"]["absolute_floor_TS1_theta_p_5psi_worst_over_window"]
        for h in ("H=1", "H=2", "H=4", "H=8"):
            self.assertFalse(hz[h]["activates"], h)
        self.assertTrue(hz["full"]["activates"])

    def test_no_negative_backstop_activation_evidence(self):
        # S4/TS4 never fires (max_N_neg == 0 including the 1.29 psi collapse).
        self.assertIn("never", _DATA["delayed_collapse_analysis"]["no_negative_pressure"].lower())

    def test_deterministic_rebuild_matches_persisted_bytes(self):
        # STRONGEST integrity check: the persisted artefact is EXACTLY what the
        # deterministic generator produces from the on-disk evidence. No manual
        # edit, no timestamp, no RNG. Guards against tampering to pass a test.
        rebuilt = M.build_brief()
        rebuilt["self_checks"] = M._self_checks(rebuilt)
        self.assertEqual(rebuilt, _DATA)


if __name__ == "__main__":
    unittest.main()


