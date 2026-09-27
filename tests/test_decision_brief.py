#!/usr/bin/env python3
"""PART 15 test battery for the D-P6-005 decision brief (WU-11).

Pure artefact/​reproducibility checks. No EPANET, no PPO, no RNG. Verifies the
decision brief is internally consistent, keeps D-P6-005 PROPOSED with a null
researcher selection, reuses the FROZEN normalisation constants without drift,
and does not touch the approved action space (dim 7 / ordering) or frozen
observation spec (dim 139) or the 121/5 service mask.
"""
from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "phase6"
BRIEF = RESULTS / "p6_d_p6_005_decision_brief.json"
WU9 = RESULTS / "p6_s8_reward_scale_analysis.json"
WU10 = RESULTS / "p6_s8_reward_formulation_comparison.json"


def _load(p):
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _all_finite(obj):
    if isinstance(obj, dict):
        return all(_all_finite(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return all(_all_finite(v) for v in obj)
    if isinstance(obj, bool) or obj is None or isinstance(obj, str):
        return True
    return isinstance(obj, (int, float)) and math.isfinite(obj)


class TestDecisionBrief(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.brief = _load(BRIEF)
        cls.wu9 = _load(WU9)
        cls.wu10 = _load(WU10)

    def test_01_status_proposed(self):
        self.assertEqual(self.brief["status"], "PROPOSED / DECISION PENDING RESEARCHER")
        self.assertEqual(self.brief["decision_id"], "D-P6-005")

    def test_02_researcher_selection_null(self):
        self.assertIsNone(self.brief["researcher_selection"])

    def test_03_no_winner_or_ranking_keys(self):
        for k in ("winner", "selected_formulation", "ranking", "scores", "best",
                  "recommended_formulation"):
            self.assertNotIn(k, self.brief)

    def test_04_all_values_finite(self):
        self.assertTrue(_all_finite(self.brief))

    def test_05_no_nan_inf_in_constants(self):
        for k, v in self.brief["normalization_constants_frozen"].items():
            if isinstance(v, (int, float)):
                self.assertTrue(math.isfinite(v), k)

    def test_06_normalization_constants_match_frozen_wu9(self):
        c = self.brief["normalization_constants_frozen"]
        f = self.wu9["proposed_normalization_constants"]
        for k in ("leak_ref_gpm", "req_ref_gpm", "deficit_ref_psi_nodesum",
                  "power_ref_kw", "movement_L2sq_max"):
            self.assertAlmostEqual(float(c[k]), float(f[k]), places=9, msg=k)

    def test_07_constants_match_across_artifacts(self):
        self.assertTrue(all(self.brief["normalization_constants_match_across_artifacts"].values()))

    def test_08_action_dim_and_ordering_unchanged(self):
        a = self.brief["frozen_constraints"]["action_space"]
        self.assertEqual(a["action_dim"], 7)
        order = [b["actuator"] for b in a["ordered_bounds"]]
        self.assertEqual(order, ["VALVE-173", "VALVE-175", "VALVE-176", "VALVE-177",
                                 "VALVE-178", "PUMP-170", "PUMP-172"])

    def test_09_action_bounds_match_frozen(self):
        expect = {"VALVE-173": (54.5, 100.0), "VALVE-175": (21.5, 110.0),
                  "VALVE-176": (20.0, 59.524), "VALVE-177": (20.0, 90.0),
                  "VALVE-178": (20.0, 74.0), "PUMP-170": (0.82, 1.10),
                  "PUMP-172": (0.77, 1.10)}
        for b in self.brief["frozen_constraints"]["action_space"]["ordered_bounds"]:
            lo, hi = expect[b["actuator"]]
            self.assertAlmostEqual(b["lower"], lo, places=6)
            self.assertAlmostEqual(b["upper"], hi, places=6)

    def test_10_observation_dim_139(self):
        self.assertEqual(self.brief["frozen_constraints"]["observation"]["observation_dim"], 139)

    def test_11_service_mask_121_5(self):
        sp = self.brief["frozen_constraints"]["service_node_policy"]
        self.assertEqual(sp["n_service_junctions"], 121)
        self.assertEqual(sp["n_connector_junctions_excluded"], 5)

    def test_12_candidates_provisional_not_approved(self):
        cands = self.brief["candidate_parameterizations"]
        self.assertTrue(2 <= len(cands) <= 4)
        for c in cands:
            self.assertEqual(c["status"], "PROVISIONAL CANDIDATE - NOT APPROVED")

    def test_13_four_formulations_present(self):
        names = {f["name"] for f in self.brief["candidate_formulations"]}
        for n in ("normalized_weighted_sum", "constrained_penalty_service_protected",
                  "baseline_relative_improvement", "safety_first_lexicographic"):
            self.assertIn(n, names)

    def test_14_no_future_information_flag(self):
        self.assertTrue(self.brief["constraints"]["no_future_information"])

    def test_15_wu10_reproducibility_preserved(self):
        r = self.wu10["reproducibility_information"]
        # native controls + no topology/native-rule change + per-ts vs accounting exact
        self.assertTrue(r["no_topology_or_native_rule_change"])
        self.assertTrue(r["no_future_information_used"])

    def test_16_wu9_integrity_preserved(self):
        it = self.wu9["integrity"]
        self.assertTrue(it["no_topology_or_native_rule_change"])
        self.assertTrue(it["native_controls_unchanged_in_every_config"])
        self.assertEqual(it["per_timestep_vs_validated_accounting_max_abs_diff"], 0.0)
        self.assertEqual(it["topology"]["n_service_junctions"], 121)
        self.assertEqual(it["topology"]["n_connector_junctions"], 5)

    def test_17_deterministic_regeneration(self):
        # Re-running the aggregator must byte-reproduce the artefact (no RNG / running stats).
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "p6_dp6005", ROOT / "src" / "validation" / "p6_d_p6_005_decision_brief.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        rebuilt = mod.build_brief()
        rebuilt["self_checks"] = mod._self_checks(rebuilt)
        on_disk = {k: v for k, v in self.brief.items()}
        self.assertEqual(json.dumps(rebuilt, sort_keys=True),
                         json.dumps(on_disk, sort_keys=True))

    def test_18_chronic_baseline_documented(self):
        cb = self.brief["chronic_baseline_service_issue"]
        self.assertEqual(cb["baseline_metrics"]["frac_ts_any_node_below_20psi"], 1.0)
        self.assertEqual(cb["baseline_metrics"]["frac_ts_any_node_negative"], 0.0)
        self.assertIn("ILL-POSED", cb["threshold_handling_options"]["absolute_hard_20psi_constraint"])

    def test_19_safety_separation_documented(self):
        sd = self.brief["safety_dependencies"]
        self.assertIn("STEP-9", sd["execution_level_STEP_9"])
        self.assertIn("separation_of_concerns", sd)


if __name__ == "__main__":
    unittest.main(verbosity=2)
