#!/usr/bin/env python3
"""Test battery for the D-P6-005 researcher summary (WU-12).

Pure artefact/reproducibility checks. No EPANET, no PPO, no RNG. Verifies the
researcher summary is a faithful re-shaping of the WU-11 decision brief: it keeps
D-P6-005 PROPOSED with a null researcher_selection, copies every candidate
equation/constant/weight from the brief without drift, preserves the two DISTINCT
unserved_ref values (F3 accounting 14.985 vs C-C DSR-implied 15.103), carries no
ranking/winner keys, and does not touch the approved action space (dim 7),
frozen observation spec (dim 139) or the 121/5 service mask. Regeneration is
deterministic (byte-reproduces the on-disk JSON).
"""
from __future__ import annotations

import importlib.util
import json
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "phase6"
BRIEF = RESULTS / "p6_d_p6_005_decision_brief.json"
SUMMARY = RESULTS / "p6_d_p6_005_researcher_summary.json"
GEN = ROOT / "src" / "validation" / "p6_d_p6_005_researcher_summary.py"

FORBIDDEN_KEY_TOKENS = ("winner", "rank", "tier", "score", "best",
                        "superior", "optimal", "preferred", "recommend")
CANDIDATE_IDS = [
    "C-A_F1_balanced_dense",
    "C-B_F1_safety_leaning",
    "C-C_F3_baseline_relative",
    "C-D_dense_deficit_no_hard_count",
]


def _load(p):
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _load_module():
    spec = importlib.util.spec_from_file_location("wu12_researcher_summary", GEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _iter_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _iter_keys(v)
    elif isinstance(obj, list):
        for x in obj:
            yield from _iter_keys(x)


def _all_finite(obj):
    if isinstance(obj, dict):
        return all(_all_finite(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return all(_all_finite(v) for v in obj)
    if isinstance(obj, bool) or obj is None or isinstance(obj, str):
        return True
    return isinstance(obj, (int, float)) and math.isfinite(obj)


class TestResearcherSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.brief = _load(BRIEF)
        cls.summary = _load(SUMMARY)
        cls.mod = _load_module()

    def test_01_source_and_summary_load(self):
        self.assertIsInstance(self.brief, dict)
        self.assertIsInstance(self.summary, dict)

    def test_02_decision_id(self):
        self.assertEqual(self.summary["decision_id"], "D-P6-005")

    def test_03_status_proposed(self):
        self.assertTrue(self.summary["current_status"].startswith("PROPOSED"))
        self.assertEqual(self.summary["current_status"], self.brief["status"])

    def test_04_researcher_selection_null(self):
        self.assertIsNone(self.summary["researcher_selection"])

    def test_05_four_candidates_exact_ids(self):
        ids = [c["candidate_id"] for c in self.summary["candidate_formulations"]]
        self.assertEqual(ids, CANDIDATE_IDS)

    def test_06_all_candidates_not_approved(self):
        for c in self.summary["candidate_formulations"]:
            self.assertEqual(c["status"], "PROVISIONAL CANDIDATE - NOT APPROVED")

    def test_07_candidate_numbers_match_brief(self):
        by_id = {c["candidate_id"]: c for c in self.brief["candidate_parameterizations"]}
        for c in self.summary["candidate_formulations"]:
            src = by_id[c["candidate_id"]]
            self.assertEqual(c["equation"], src["equation"])
            self.assertEqual(c["normalization_constants"], src["constants"])
            self.assertEqual(c["provisional_weights"], src["provisional_weights"])
            self.assertEqual(c["base_formulation"], src["base_formulation"])

    def test_08_cc_unserved_ref_dsr_implied(self):
        cc = self.summary["candidate_parameters"]["C-C_F3_baseline_relative"]
        self.assertEqual(cc["normalization_constants"]["unserved_ref_gpm"],
                         15.103309701248634)

    def test_09_f3_accounting_unserved_ref_distinct(self):
        f3 = next(f for f in self.summary["formulation_families"] if f["id"] == "F3")
        self.assertEqual(f3["baseline_constants"]["unserved_ref_gpm"],
                         14.98483697365873)
        self.assertNotEqual(f3["baseline_constants"]["unserved_ref_gpm"],
                            15.103309701248634)

    def test_10_frozen_constants_match_brief(self):
        self.assertEqual(self.summary["normalization_constants_frozen"],
                         self.brief["normalization_constants_frozen"])
        self.assertEqual(
            self.summary["normalization_constants_frozen"]["leak_ref_gpm"],
            84.72988433677985)
        self.assertEqual(
            self.summary["normalization_constants_frozen"]["movement_L2sq_max"], 28.0)

    def test_11_no_forbidden_key_tokens(self):
        bad = [k for k in _iter_keys(self.summary)
               if any(tok in k.lower() for tok in FORBIDDEN_KEY_TOKENS)]
        self.assertEqual(bad, [])

    def test_12_action_space_unchanged(self):
        acts = self.summary["frozen_constraints_snapshot"]["action_space"]
        self.assertEqual(acts["action_dim"], 7)
        self.assertEqual(acts["excluded_valves_kept_in_model"],
                         ["VALVE-174", "VALVE-179", "VALVE-180"])

    def test_13_observation_dim_139(self):
        self.assertEqual(
            self.summary["frozen_constraints_snapshot"]["observation"]["observation_dim"],
            139)

    def test_14_service_mask_121_5(self):
        pol = self.summary["frozen_constraints_snapshot"]["service_node_policy"]
        self.assertEqual(pol["n_service_junctions"], 121)
        self.assertEqual(pol["n_connector_junctions_excluded"], 5)

    def test_15_formulation_families_f1_f4(self):
        ids = [f["id"] for f in self.summary["formulation_families"]]
        self.assertEqual(ids, ["F1", "F2", "F3", "F4"])

    def test_16_plain_language_fa_four_questions(self):
        for c in self.summary["candidate_formulations"]:
            fa = c["plain_language_fa"]
            self.assertEqual(set(fa), {"q1_encourages", "q2_leak_down_service_down",
                                       "q3_pressure_up", "q4_action_moves_a_lot"})
            self.assertTrue(all(isinstance(v, str) and v for v in fa.values()))

    def test_17_no_topology_or_native_rule_change(self):
        rep = self.summary["reproducibility"]
        self.assertTrue(rep["no_topology_or_native_rule_change"])
        self.assertTrue(rep["no_future_information_used"])
        self.assertEqual(rep["native_controls_count"], 5)

    def test_18_all_values_finite(self):
        self.assertTrue(_all_finite(self.summary))

    def test_19_self_checks_all_true(self):
        self.assertTrue(all(self.summary["self_checks"].values()))

    def test_20_deterministic_regeneration_byte_reproduce(self):
        built = self.mod.build_summary(self.mod._load_brief())
        text = json.dumps(built, ensure_ascii=False, indent=2) + "\n"
        on_disk = SUMMARY.read_text(encoding="utf-8")
        self.assertEqual(text, on_disk)

    def test_21_evidence_references_present(self):
        ref = self.summary["evidence_references"]
        for key in ("wu9_scale_analysis", "wu10_formulation_comparison",
                    "wu11_decision_brief"):
            self.assertIn(key, ref)


if __name__ == "__main__":
    unittest.main(verbosity=2)
