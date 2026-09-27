"""Scientific-correctness tests for the STEP 8 reward-formulation comparison.

Standard-library `unittest` + numpy only (no pytest / gymnasium / torch). The
pure-function tests exercise the reward math on synthetic primitives and run
without EPANET; the artefact tests validate the produced
results/phase6/p6_s8_reward_formulation_comparison.json and are skipped if it
is absent.

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

import p6_s8_reward_formulation_comparison as M  # noqa: E402

ART = ROOT / "results" / "phase6" / "p6_s8_reward_formulation_comparison.json"
_DATA = json.loads(ART.read_text(encoding="utf-8")) if ART.exists() else None

# A synthetic FIXED normalisation set (values irrelevant to correctness, only
# that they are non-zero constants; matches the on-disk key names).
NORM = {
    "leak_ref_gpm": 80.0,
    "req_ref_gpm": 900.0,
    "deficit_ref_psi_nodesum": 25.0,
    "power_ref_kw": 88.0,
    "movement_L2sq_max": 28.0,
}
UNSERVED_REF = 15.0


def _series(leak, unserved, deficit, power, n_below, n_neg, min_p):
    n = len(leak)
    return {
        "leakage_gpm": np.asarray(leak, float),
        "unserved_demand_gpm": np.asarray(unserved, float),
        "pressure_deficit_psi_nodesum": np.asarray(deficit, float),
        "pump_hydraulic_power_kw": np.asarray(power, float),
        "n_service_nodes_below_20psi": np.asarray(n_below, float),
        "n_service_nodes_negative": np.asarray(n_neg, float),
        "min_service_pressure_psi": np.asarray(min_p, float),
    }


def _typical_prim():
    s = _series(
        leak=[84.0, 86.0], unserved=[14.0, 16.0], deficit=[18.0, 22.0],
        power=[80.0, 90.0], n_below=[2.0, 1.0], n_neg=[0.0, 0.0],
        min_p=[4.5, 6.0])
    return M._norm_primitives(s, NORM)


class TestNormalization(unittest.TestCase):
    def test_leak_normalization_exact(self):
        prim = _typical_prim()
        np.testing.assert_allclose(prim["leak_norm"], np.array([84.0, 86.0]) / 80.0)

    def test_deficit_normalization_exact(self):
        prim = _typical_prim()
        np.testing.assert_allclose(prim["deficit_norm"], np.array([18.0, 22.0]) / 25.0)

    def test_unserved_clipped_nonnegative(self):
        # served can marginally exceed requested -> negative unserved -> clip 0
        s = _series([80.0], [-5.0], [10.0], [80.0], [2.0], [0.0], [5.0])
        prim = M._norm_primitives(s, NORM)
        self.assertEqual(prim["unserved_norm"][0], 0.0)

    def test_movement_zero_for_static_hold(self):
        prim = _typical_prim()
        np.testing.assert_array_equal(prim["movement_norm"], np.zeros(2))

    def test_norm_constants_nonzero(self):
        for k in ("leak_ref_gpm", "req_ref_gpm", "deficit_ref_psi_nodesum",
                  "power_ref_kw", "movement_L2sq_max"):
            self.assertGreater(NORM[k], 0.0)
        self.assertGreater(M.EPS, 0.0)


class TestRewardMathAndSigns(unittest.TestCase):
    def test_all_rewards_finite(self):
        prim = _typical_prim()
        for fk in M.FORMULATIONS:
            r = M._reward_for(fk, prim, NORM, UNSERVED_REF, M.PROVISIONAL[M.BASE_KEY[fk]])
            self.assertTrue(np.all(np.isfinite(r)), f"{fk} produced non-finite reward")

    def test_f1_sign_and_exact(self):
        prim = _typical_prim()
        p = {"w_L": 1.0, "w_U": 0.0, "w_P": 0.0, "w_A": 0.0, "w_E": 0.0}
        r = M.reward_F1(prim, NORM, p)
        np.testing.assert_allclose(r, -(np.array([84.0, 86.0]) / 80.0))
        self.assertTrue(np.all(r < 0.0))  # cost -> negative

    def test_f1_monotonic_decreasing_in_leak(self):
        lo = M.reward_F1(M._norm_primitives(
            _series([70.0], [14.0], [18.0], [80.0], [2.0], [0.0], [5.0]), NORM),
            NORM, M.PROVISIONAL["F1_normalized_weighted_sum"])[0]
        hi = M.reward_F1(M._norm_primitives(
            _series([95.0], [14.0], [18.0], [80.0], [2.0], [0.0], [5.0]), NORM),
            NORM, M.PROVISIONAL["F1_normalized_weighted_sum"])[0]
        self.assertGreater(lo, hi)  # more leakage -> lower reward

    def test_f2_hard_term_scales_with_count(self):
        p = {"lambda_service": 20.0, "big_hard": 100.0}
        r1 = M.reward_F2(M._norm_primitives(
            _series([80.0], [14.0], [18.0], [80.0], [1.0], [0.0], [5.0]), NORM), NORM, p)[0]
        r2 = M.reward_F2(M._norm_primitives(
            _series([80.0], [14.0], [18.0], [80.0], [2.0], [0.0], [5.0]), NORM), NORM, p)[0]
        self.assertAlmostEqual(r1 - r2, 100.0, places=6)  # one extra sub-20 node = -BIG

    def test_f3_zero_improvement_at_baseline_leak(self):
        # leak == leak_ref, unserved <= ref, deficit 0 -> improvement 0
        prim = M._norm_primitives(
            _series([80.0], [10.0], [0.0], [80.0], [0.0], [0.0], [25.0]), NORM)
        r = M.reward_F3(prim, NORM, {"w_U": 1.0, "w_P_safety": 1.0}, UNSERVED_REF)[0]
        self.assertAlmostEqual(r, 0.0, places=6)

    def test_f3_positive_when_leak_below_baseline(self):
        prim = M._norm_primitives(
            _series([60.0], [10.0], [0.0], [80.0], [0.0], [0.0], [25.0]), NORM)
        r = M.reward_F3(prim, NORM, {"w_U": 0.0, "w_P_safety": 0.0}, UNSERVED_REF)[0]
        self.assertAlmostEqual(r, (80.0 - 60.0) / 80.0, places=6)

    def test_f4_lexicographic_branches(self):
        p = M.PROVISIONAL["F4_safety_first_lexicographic"]  # threshold 20
        neg = M.reward_F4(M._norm_primitives(
            _series([80.0], [14.0], [18.0], [80.0], [3.0], [1.0], [-2.0]), NORM), NORM, p)[0]
        soft = M.reward_F4(M._norm_primitives(
            _series([80.0], [14.0], [18.0], [80.0], [2.0], [0.0], [5.0]), NORM), NORM, p)[0]
        ok = M.reward_F4(M._norm_primitives(
            _series([80.0], [14.0], [18.0], [80.0], [0.0], [0.0], [25.0]), NORM), NORM, p)[0]
        self.assertLess(neg, soft)       # negative node dominates
        self.assertLess(soft, ok)        # sub-threshold penalised below the safe leak term
        self.assertAlmostEqual(ok, -(80.0 / 80.0), places=6)  # safe -> pure leak term


class TestActuatorAndIncentive(unittest.TestCase):
    def test_analytic_effort_dim_and_ceiling(self):
        probe = M.analytic_effort_probe(NORM)
        # actuator mapping is 7-D; a max single-step move normalises to 1.0
        self.assertEqual(NORM["movement_L2sq_max"], 28.0)
        self.assertAlmostEqual(probe["normalised_movement_for_max_single_step_move"], 1.0, places=6)
        self.assertAlmostEqual(probe["normalised_movement_for_static_hold"], 0.0, places=6)

    def test_incentive_argmax_picks_max_mean(self):
        pick = M._incentive_argmax({"a": -2.0, "b": -0.5, "c": -3.0})
        self.assertEqual(pick["argmax_config_within_tested_set"], "b")
        self.assertAlmostEqual(pick["argmax_mean_reward"], -0.5)
        self.assertAlmostEqual(pick["reward_spread_across_tested_configs"], 2.5)

    def test_effort_uses_commanded_not_realised(self):
        # movement primitive is derived from commanded action (0 for static holds),
        # never from realised pump speed (reset by STATUS-IS rules, G12).
        prim = _typical_prim()
        np.testing.assert_array_equal(prim["movement_norm"], np.zeros_like(prim["leak_norm"]))


@unittest.skipIf(_DATA is None, "comparison artefact not present")
class TestArtefact(unittest.TestCase):
    def test_part13_keys_present(self):
        for k in ("experiment_metadata", "formulations", "provisional_parameters",
                  "normalization_constants", "tested_configurations",
                  "per_configuration_metrics", "pooled_statistics",
                  "temporal_statistics", "pathology_results", "sensitivity_results",
                  "limitations", "reproducibility_information"):
            self.assertIn(k, _DATA)

    def test_reference_reproduces_frozen_baseline(self):
        rep = _DATA["reproducibility_information"]["reference_reproduces_frozen_baseline"]
        self.assertLess(rep["leak_ref_abs_diff"], 1e-6)
        self.assertLess(rep["req_ref_abs_diff"], 1e-6)
        self.assertEqual(rep["reference_n_node_ts_below_20psi"], 386)
        self.assertEqual(rep["reference_n_node_ts_negative"], 0)

    def test_per_timestep_accounting_consistent(self):
        rep = _DATA["reproducibility_information"]["reference_reproduces_frozen_baseline"]
        self.assertLess(rep["per_timestep_vs_validated_accounting_max_abs_diff"], 1e-6)

    def test_no_topology_or_future_info(self):
        r = _DATA["reproducibility_information"]
        self.assertTrue(r["no_topology_or_native_rule_change"])
        self.assertTrue(r["no_future_information_used"])
        self.assertTrue(r["all_reward_values_finite"])
        self.assertEqual(r["native_controls_count"], 5)

    def test_service_mask_121_5(self):
        pol = _DATA["experiment_metadata"]["service_node_policy"]
        self.assertEqual(pol["n_service_junctions"], 121)
        self.assertEqual(pol["n_connector_junctions"], 5)
        self.assertEqual(len(pol["connector_nodes"]), 5)

    def test_normalization_constants_frozen(self):
        c = _DATA["normalization_constants"]
        self.assertAlmostEqual(c["leak_ref_gpm"], 84.72988433677985, places=6)
        self.assertAlmostEqual(c["req_ref_gpm"], 906.3987348621764, places=6)
        self.assertAlmostEqual(c["deficit_ref_psi_nodesum"], 28.671793365478514, places=6)
        self.assertAlmostEqual(c["movement_L2sq_max"], 28.0, places=6)

    def test_all_pooled_rewards_finite(self):
        for fk, v in _DATA["pooled_statistics"].items():
            for stat in ("mean", "std", "min", "max"):
                self.assertTrue(np.isfinite(v[stat]), f"{fk}.{stat} not finite")

    def test_status_no_selection(self):
        status = _DATA["experiment_metadata"]["status"].lower()
        self.assertIn("d-p6-005 remains proposed", status)
        self.assertEqual(len(_DATA["formulations"]), 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
