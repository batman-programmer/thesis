"""STEP-9 (WU-18) test battery for the FINAL safety-architecture DECISION REVIEW.

Standard-library ``unittest`` only (no pytest / numpy / gymnasium / torch). The
pure-function tests run without any artefact; the artefact tests validate the
produced results/phase6/p6_s9_final_decision_review.json and are skipped if it
is absent.

This artefact is the FINAL REVIEW that precedes production safety-wrapper
implementation. The tests assert that it JUDGES readiness and PACKAGES the (<=3)
final PROVISIONAL designs WITHOUT making the STEP-9 decision: researcher_selection
is null, every final design is NOT APPROVED and NOT ordered by quality, no
mechanism/threshold/horizon/policy is selected/ranked/scored/recommended (no
forbidden key token appears anywhere), the frozen invariants + cross-artefact
anchors reproduce byte-exact, and the WU-17 "crossover untested" wording is
corrected to the PERSISTED onset (theta_p=5 -> report index 13 / 6.5 h). The
review is deterministic: re-running the generator in-memory must reproduce the
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

import p6_s9_final_decision_review as M  # noqa: E402

ART = ROOT / "results" / "phase6" / "p6_s9_final_decision_review.json"
_TEXT = ART.read_text(encoding="utf-8") if ART.exists() else None
_DATA = json.loads(_TEXT) if _TEXT is not None else None

# --- frozen invariants (D-P6-001/002/003/004) --------------------------------
ACTUATOR_ORDER = ["VALVE-173", "VALVE-175", "VALVE-176",
                  "VALVE-177", "VALVE-178", "PUMP-170", "PUMP-172"]
FROZEN_BOUNDS = {
    "VALVE-173": (54.5, 100.0), "VALVE-175": (21.5, 110.0),
    "VALVE-176": (20.0, 59.524), "VALVE-177": (20.0, 90.0),
    "VALVE-178": (20.0, 74.0), "PUMP-170": (0.82, 1.1), "PUMP-172": (0.77, 1.1),
}
# --- cross-artefact anchors the review must reproduce byte-exact --------------
LEAK_REF_GPM = 84.72988433677985
REQ_REF_GPM = 906.3987348621764
MOVEMENT_L2SQ_MAX = 28.0
BASELINE_WORST_PSI = 4.16452169418335
WU16_DECISION_INSTANT_PSI = 5.527866840362549
WU16_FULL_HORIZON_PSI = 1.2946763038635254
CROSSOVER_ONSET_INDEX = 13
CROSSOVER_ONSET_HOURS = 6.5

REQUIRED_KEYS = (
    "decision_context", "frozen_invariants", "evidence", "metric_definitions",
    "candidate_analysis", "horizon_analysis", "threshold_analysis",
    "action_handling_analysis", "train_execute_analysis",
    "repeated_intervention_analysis", "final_provisional_designs",
    "unresolved_issues", "decision_readiness", "researcher_action_required",
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


class TestPureHelpers(unittest.TestCase):
    def test_decision_id_is_a_review_not_a_minted_decision(self):
        # WU-18 is the FINAL REVIEW; it must NOT mint / approve D-P6-006.
        self.assertEqual(M.DECISION_ID, "STEP9_SAFETY_MECHANISM_FINAL_REVIEW")
        self.assertNotIn("D-P6-006", M.DECISION_ID)
        self.assertEqual(M.STATUS, "PROPOSED / PENDING RESEARCHER")
        self.assertIn("NOT APPROVED", M.NOT_APPROVED)
        self.assertEqual(M.READINESS, "DECISION-READY")
        self.assertEqual(M.NOT_READY, "NOT-YET-DECISION-READY")
        self.assertIn("THRESHOLD NOT YET EMPIRICALLY JUSTIFIED", M.THRESH_UNJUSTIFIED)

    def test_forbidden_key_tokens_tuple(self):
        self.assertEqual(
            set(M.FORBIDDEN_KEY_TOKENS),
            {"winner", "rank", "tier", "score", "best",
             "superior", "optimal", "preferred", "recommend"})
        # "select"/"selection"/"worst"/"readiness" are SAFE and MUST NOT be forbidden.
        for safe in ("select", "selection", "worst", "readiness"):
            self.assertNotIn(safe, M.FORBIDDEN_KEY_TOKENS)

    def test_finite_helpers(self):
        self.assertTrue(M._finite(1.0))
        self.assertFalse(M._finite(math.inf))
        self.assertFalse(M._finite(math.nan))
        self.assertFalse(M._finite(True))  # bools are not numbers here
        self.assertTrue(M._all_finite({"a": [1, 2.0], "b": "x", "c": None, "d": True}))
        self.assertFalse(M._all_finite({"a": [1, math.nan]}))
        self.assertFalse(M._all_finite([1.0, math.inf]))

    def test_key_and_forbidden_helpers(self):
        obj = {"a": {"b": [{"c": 1}]}, "d": 2}
        self.assertEqual(set(M._iter_keys(obj)), {"a", "b", "c", "d"})
        self.assertIsNone(M._has_forbidden_key(obj))
        self.assertIsNotNone(M._has_forbidden_key({"ranking": 1}))
        self.assertIsNotNone(M._has_forbidden_key({"nested": {"best_pick": 2}}))

    def test_close_helper(self):
        self.assertTrue(M._close(1.0, 1.0 + 1e-12))
        self.assertFalse(M._close(1.0, 1.1))
        self.assertFalse(M._close(math.nan, 1.0))

    def test_build_final_designs_are_three_unordered_not_approved(self):
        wu14, wu15, wu16, wu17, wu11 = M.load_all()
        fpd = M.build_final_provisional_designs(wu16)
        self.assertTrue(fpd["not_ordered_by_quality"] is True)
        self.assertTrue(fpd["order_is_definitional_not_quality"] is True)
        ids = [d["design_id"] for d in fpd["designs"]]
        self.assertEqual(ids, ["F1", "F2", "F3"])
        self.assertTrue(2 <= len(fpd["designs"]) <= 3)
        for d in fpd["designs"]:
            self.assertEqual(d["status"], M.NOT_APPROVED)
        # no forbidden token anywhere in the designs KEYS
        self.assertIsNone(M._has_forbidden_key(fpd))

    def test_build_readiness_is_decision_ready_not_a_selection(self):
        dr = M.build_decision_readiness()
        self.assertEqual(dr["readiness_verdict"], M.READINESS)
        self.assertTrue(dr["verdict_is_not_a_selection"] is True)

    def test_build_researcher_form_is_blank(self):
        rar = M.build_researcher_action_required()
        form = rar["decision_form_blank"]
        self.assertEqual(set(form), {"A_architecture", "B_metric_rule", "C_threshold",
                                     "D_look_ahead_horizon", "E_action_handling_policy",
                                     "F_effort_term_action_under_intervention", "G_rationale"})
        for v in form.values():
            self.assertIsNone(v)


@unittest.skipUnless(_DATA is not None, "final-decision-review artefact not generated yet")
class TestArtefact(unittest.TestCase):
    def test_all_required_keys_present(self):
        for f in REQUIRED_KEYS:
            self.assertIn(f, _DATA, f)
        self.assertEqual(len(_DATA), len(REQUIRED_KEYS))

    def test_researcher_selection_is_null(self):
        self.assertIsNone(_DATA["researcher_selection"])
        self.assertEqual(_DATA["decision_context"]["status"], "PROPOSED / PENDING RESEARCHER")

    def test_no_disallowed_top_level_keys(self):
        for bad in ("winner", "ranking", "score", "recommendation"):
            self.assertNotIn(bad, _DATA, bad)

    def test_no_forbidden_key_tokens_anywhere(self):
        bad = sorted({k for k in _iter_keys(_DATA)
                      if any(t in str(k).lower() for t in M.FORBIDDEN_KEY_TOKENS)})
        self.assertEqual(bad, [], f"forbidden key tokens: {bad}")

    def test_all_numbers_finite(self):
        for x in _iter_numbers(_DATA):
            self.assertTrue(math.isfinite(x), x)

    def test_no_generated_utc_key(self):
        # byte-reproducibility: the aggregator carries NO timestamp key.
        self.assertNotIn("generated_utc", set(_iter_keys(_DATA)))

    def test_self_checks_all_true(self):
        self.assertTrue(all(v is True for v in _DATA["self_checks"].values()),
                        [k for k, v in _DATA["self_checks"].items() if v is not True])
        # the review carries the full gate battery (>=30 gates)
        self.assertGreaterEqual(len(_DATA["self_checks"]), 30)

    def test_readiness_verdict_is_decision_ready(self):
        dr = _DATA["decision_readiness"]
        self.assertEqual(dr["readiness_verdict"], "DECISION-READY")
        self.assertTrue(dr["verdict_is_not_a_selection"] is True)
        self.assertIn("STEP-9 remains PROPOSED", dr["status_after_this_review"])


    def test_frozen_action_space(self):
        acts = _DATA["frozen_invariants"]["action_space"]
        self.assertEqual(acts["action_dim"], 7)
        order = [b["actuator"] for b in acts["ordered_bounds"]]
        self.assertEqual(order, ACTUATOR_ORDER)
        for b in acts["ordered_bounds"]:
            lo, hi = FROZEN_BOUNDS[b["actuator"]]
            self.assertAlmostEqual(b["lower"], lo, places=9, msg=b["actuator"])
            self.assertAlmostEqual(b["upper"], hi, places=9, msg=b["actuator"])

    def test_frozen_observation_dim(self):
        self.assertEqual(_DATA["frozen_invariants"]["observation"]["observation_dim"], 139)

    def test_frozen_reward_unchanged(self):
        self.assertEqual(
            _DATA["frozen_invariants"]["frozen_reward_D_P6_005"]["weights"],
            {"w_L": 1.0, "w_U": 1.0, "w_P": 1.0, "w_A": 0.1, "w_E": 0.0})
        consts = _DATA["frozen_invariants"]["normalization_constants_frozen"]
        self.assertAlmostEqual(consts["leak_ref_gpm"], LEAK_REF_GPM, places=6)
        self.assertAlmostEqual(consts["req_ref_gpm"], REQ_REF_GPM, places=6)
        self.assertAlmostEqual(consts["movement_L2sq_max"], MOVEMENT_L2SQ_MAX, places=9)

    def test_safe_iff_rules_verbatim(self):
        r = _DATA["metric_definitions"]["safe_iff_rules"]
        self.assertTrue(r["S1"].startswith("p_min(post) >= theta_p"))
        self.assertTrue(r["S4"].startswith("N_neg(post) == 0"))
        self.assertEqual(r["TS1"], "min_{0..H} p_min >= theta_p")
        self.assertEqual(r["TS3"], "max_{0..H} dD <= eps_D")

    def test_architectures_A_D_present(self):
        arch = _DATA["candidate_analysis"]["architectures"]
        ids = [a["architecture_id"] for a in arch if "architecture_id" in a]
        self.assertEqual(ids, ["A", "B", "C", "D"])

    def test_baseline_and_severe_corner_anchors_reproduced(self):
        anc = _DATA["evidence"]["central_anchors"]
        self.assertAlmostEqual(anc["baseline_worst_node_p_min_psi"], BASELINE_WORST_PSI, places=9)
        self.assertAlmostEqual(anc["severe_corner_decision_instant_p_min_psi"],
                               WU16_DECISION_INSTANT_PSI, places=9)
        self.assertAlmostEqual(anc["severe_corner_full_horizon_p_min_psi"],
                               WU16_FULL_HORIZON_PSI, places=9)
        self.assertEqual(anc["severe_corner_max_N_neg"], 0)
        # the delayed collapse: full-horizon worst < decision-instant worst
        self.assertLess(anc["severe_corner_full_horizon_p_min_psi"],
                        anc["severe_corner_decision_instant_p_min_psi"])


    def test_crossover_onset_correction_persisted(self):
        # CORRECTION vs WU-17: the onset is PERSISTED, not untested.
        corr = _DATA["horizon_analysis"]["crossover_onset_correction"]
        self.assertEqual(corr["supersedes"],
                         "wu17.horizon_analysis.crossover_interval_untested")
        onset = corr["severe_corner_smallest_sufficient_H_for_theta_p_5"]
        self.assertEqual(onset["report_index"], CROSSOVER_ONSET_INDEX)
        self.assertAlmostEqual(onset["hours"], CROSSOVER_ONSET_HOURS, places=9)
        self.assertEqual(onset["control_steps"], CROSSOVER_ONSET_INDEX)

    def test_absolute_20psi_floor_labelled_unjustified(self):
        ta = _DATA["threshold_analysis"]
        self.assertEqual(ta["negative_pressure_gate"]["label"], "EVIDENCE-SUPPORTED")
        self.assertEqual(ta["absolute_floor_theta_p_psi"]["useful_20psi_floor_status"],
                         M.THRESH_UNJUSTIFIED)
        self.assertIn(M.THRESH_UNJUSTIFIED, ta["summary"])

    def test_final_designs_three_unordered_not_approved(self):
        fpd = _DATA["final_provisional_designs"]
        designs = fpd["designs"]
        self.assertTrue(2 <= len(designs) <= 3)
        self.assertEqual([d["design_id"] for d in designs], ["F1", "F2", "F3"])
        self.assertTrue(fpd["not_ordered_by_quality"] is True)
        for d in designs:
            self.assertEqual(d["status"], M.NOT_APPROVED)
        # F2 carries the PERSISTED smallest-sufficient horizon for theta_p=5
        f2 = next(d for d in designs if d["design_id"] == "F2")
        self.assertEqual(f2["horizon"]["smallest_sufficient_H_for_theta_p_5_report_index"],
                         CROSSOVER_ONSET_INDEX)

    def test_researcher_form_blank_all_none(self):
        form = _DATA["researcher_action_required"]["decision_form_blank"]
        self.assertEqual(len(form), 7)
        for v in form.values():
            self.assertIsNone(v)

    def test_deterministic_rebuild_matches_persisted_object(self):
        # STRONGEST integrity check: the persisted artefact is EXACTLY what the
        # deterministic generator produces from the on-disk evidence.
        self.assertEqual(M.build(), _DATA)

    def test_deterministic_rebuild_matches_persisted_bytes(self):
        # byte-for-byte reproducibility guards against manual tampering to pass.
        self.assertEqual(M.serialize(M.build()), _TEXT)


if __name__ == "__main__":
    unittest.main()
