#!/usr/bin/env python3
"""Test battery for the STEP-9 safety-mechanism design analysis (WU-14).

Pure artefact/reproducibility checks. No EPANET, no PPO, no RNG. Verifies the
STEP-9 analysis is a faithful aggregation of the WU-11 decision brief that:
  * records D-P6-005 = APPROVED (C-A_F1_balanced_dense) with equation/weights/
    constants copied verbatim from the brief's C-A parameterisation (anti-drift);
  * characterises exactly four candidate mechanisms S1-S4 on a FIXED schema and
    does NOT select, score, or order them (selection DEFERRED);
  * preserves the chronic-baseline evidence (386 sub-20 node-ts, 0 negative,
    frac 1.0, min service ~4.16 psi) and the leak-only argmax (~1.29 psi);
  * carries no ranking/winner keys and does not touch the frozen action space
    (dim 7), observation spec (dim 139) or the 121/5 service mask;
  * implements NO production safety wrapper;
  * regenerates deterministically (byte-reproduces the on-disk JSON).
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
ANALYSIS = RESULTS / "p6_s9_safety_design_analysis.json"
GEN = ROOT / "src" / "validation" / "p6_s9_safety_design_analysis.py"

FORBIDDEN_KEY_TOKENS = ("winner", "rank", "tier", "score", "best",
                        "superior", "optimal", "preferred", "recommend")
CANDIDATE_IDS = ["S1", "S2", "S3", "S4"]
SCHEMA_FIELDS = {
    "exact_rule", "information_required", "compute_cost", "baseline_compatibility",
    "false_positive_risk", "false_negative_risk", "ppo_compatibility",
    "interval_30min_compatibility", "requires_look_ahead", "preserves_determinism",
}


def _load(p):
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _load_module():
    spec = importlib.util.spec_from_file_location("wu14_safety_design", GEN)
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


class TestSafetyDesignAnalysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.brief = _load(BRIEF)
        cls.analysis = _load(ANALYSIS)
        cls.mod = _load_module()
        cls.ca = next(c for c in cls.brief["candidate_parameterizations"]
                      if c["candidate_id"] == "C-A_F1_balanced_dense")

    def test_01_artifacts_load(self):
        self.assertIsInstance(self.brief, dict)
        self.assertIsInstance(self.analysis, dict)

    def test_02_is_design_analysis_only(self):
        self.assertTrue(self.analysis["measures_nothing_new"])
        self.assertTrue(self.analysis["no_epanet_no_ppo_no_selection"])
        self.assertTrue(self.analysis["no_production_wrapper_implemented"])

    def test_03_d_p6_005_approved_C_A(self):
        d = self.analysis["d_p6_005_decision"]
        self.assertEqual(d["status"], "APPROVED")
        self.assertEqual(d["selected_candidate"], "C-A_F1_balanced_dense")
        self.assertEqual(d["formulation"], "F1_normalized_weighted_sum")

    def test_04_d_p6_005_matches_brief_C_A(self):
        d = self.analysis["d_p6_005_decision"]
        self.assertEqual(d["equation"], self.ca["equation"])
        self.assertEqual(d["weights"], self.ca["provisional_weights"])
        self.assertEqual(d["frozen_normalization_constants"], self.ca["constants"])

    def test_05_approved_weights_exact(self):
        w = self.analysis["d_p6_005_decision"]["weights"]
        self.assertEqual(w, {"w_L": 1.0, "w_U": 1.0, "w_P": 1.0, "w_A": 0.1, "w_E": 0.0})
    def test_06_four_candidates_ids_S1_S4(self):
        ids = [c["candidate_id"] for c in self.analysis["safety_candidates"]]
        self.assertEqual(ids, CANDIDATE_IDS)

    def test_07_each_candidate_has_fixed_schema(self):
        for c in self.analysis["safety_candidates"]:
            keys = set(c.keys())
            self.assertEqual(keys, {"candidate_id", "name", "mechanism_class", *SCHEMA_FIELDS})
            for f in SCHEMA_FIELDS:
                self.assertIsInstance(c[f], str)
                self.assertTrue(c[f])

    def test_08_selection_is_deferred_not_ranked(self):
        sel = self.analysis["safety_candidate_selection"]
        self.assertTrue(sel["status"].startswith("DEFERRED"))
        self.assertTrue(sel["characterisation_only"])
        # no candidate carries a numeric quality/ranking field
        for c in self.analysis["safety_candidates"]:
            self.assertNotIn("rank", set(c.keys()))
            self.assertNotIn("score", set(c.keys()))

    def test_09_no_forbidden_key_tokens(self):
        bad = [k for k in _iter_keys(self.analysis)
               if any(tok in k.lower() for tok in FORBIDDEN_KEY_TOKENS)]
        self.assertEqual(bad, [])

    def test_10_action_space_unchanged(self):
        acts = self.analysis["frozen_constraints_snapshot"]["action_space"]
        self.assertEqual(acts["action_dim"], 7)
        self.assertEqual(acts["excluded_valves_kept_in_model"],
                         ["VALVE-174", "VALVE-179", "VALVE-180"])

    def test_11_observation_dim_139(self):
        self.assertEqual(
            self.analysis["frozen_constraints_snapshot"]["observation"]["observation_dim"], 139)

    def test_12_service_mask_121_5(self):
        pol = self.analysis["frozen_constraints_snapshot"]["service_node_policy"]
        self.assertEqual(pol["n_service_junctions"], 121)
        self.assertEqual(pol["n_connector_junctions_excluded"], 5)

    def test_13_chronic_baseline_preserved(self):
        m = self.analysis["evidence_loaded"]["chronic_baseline_service_issue"]["baseline_metrics"]
        self.assertEqual(m, self.brief["chronic_baseline_service_issue"]["baseline_metrics"])
        self.assertEqual(m["n_node_timesteps_below_20psi"], 386)
        self.assertEqual(m["n_node_timesteps_negative"], 0)
        self.assertEqual(m["frac_ts_any_node_below_20psi"], 1.0)
        self.assertEqual(m["min_service_psi_over_horizon"], 4.16452169418335)

    def test_14_leak_only_argmax_preserved(self):
        a = self.analysis["evidence_loaded"]["leak_only_argmax"]
        self.assertEqual(a["min_service_psi_at_argmax"], 1.2946763038635254)
        self.assertEqual(a["incentive_argmax_config"], "prv_lower_pump_lower")

    def test_15_frozen_constants_match_brief(self):
        self.assertEqual(self.analysis["normalization_constants_frozen"],
                         self.brief["normalization_constants_frozen"])
        self.assertEqual(
            self.analysis["normalization_constants_frozen"]["movement_L2sq_max"], 28.0)

    def test_16_naive_absolute_20psi_reject_ill_posed(self):
        s = self.analysis["baseline_compatibility_summary"]
        self.assertTrue(s["naive_absolute_20psi_reject_is_ill_posed"])
        self.assertIn("S1", s["per_candidate_baseline_flag"])

    def test_17_no_topology_or_native_rule_change(self):
        rep = self.analysis["reproducibility"]
        self.assertTrue(rep["no_topology_or_native_rule_change"])
        self.assertTrue(rep["no_future_information_used"])
        self.assertEqual(rep["native_controls_count"], 5)

    def test_18_all_values_finite(self):
        self.assertTrue(_all_finite(self.analysis))

    def test_19_self_checks_all_true(self):
        self.assertTrue(all(self.analysis["self_checks"].values()))

    def test_20_deterministic_regeneration_byte_reproduce(self):
        built = self.mod.build_analysis(self.mod._load_brief())
        text = json.dumps(built, ensure_ascii=False, indent=2) + "\n"
        on_disk = ANALYSIS.read_text(encoding="utf-8")
        self.assertEqual(text, on_disk)

    def test_21_source_artifact_reference(self):
        self.assertEqual(self.analysis["source_artifact"],
                         "results/phase6/p6_d_p6_005_decision_brief.json")


if __name__ == "__main__":
    unittest.main(verbosity=2)
