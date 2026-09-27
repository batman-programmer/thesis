"""STEP 8 test battery for the reward-component scale analysis.

Standard-library `unittest` + numpy only (no pytest / gymnasium / torch). The
pure-function tests run without EPANET; the artefact tests validate the produced
results/phase6/p6_s8_reward_scale_analysis.json and are skipped if it is absent.

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

import p6_s8_reward_scale_analysis as R  # noqa: E402

ART = ROOT / "results" / "phase6" / "p6_s8_reward_scale_analysis.json"
_DATA = json.loads(ART.read_text(encoding="utf-8")) if ART.exists() else None


class TestPureHelpers(unittest.TestCase):
    def test_stats_deterministic(self):
        a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        self.assertEqual(R.stats(a), R.stats(a.copy()))

    def test_stats_values(self):
        s = R.stats(np.array([0.0, 10.0]))
        self.assertEqual(s["n"], 2)
        self.assertAlmostEqual(s["mean"], 5.0)
        self.assertAlmostEqual(s["min"], 0.0)
        self.assertAlmostEqual(s["max"], 10.0)
        self.assertAlmostEqual(s["mean_abs_step_diff"], 10.0)

    def test_ten_candidate_components(self):
        self.assertEqual(len(R.COMPONENT_KEYS), 10)
        self.assertEqual(len(set(R.COMPONENT_KEYS)), 10)

    def test_actuator_effort_analytic(self):
        e = R.actuator_effort_analytic()
        self.assertEqual(e["action_dim"], 7)
        self.assertEqual(e["max_per_step_L1_movement"], 14.0)
        self.assertEqual(e["max_per_step_L2sq_movement"], 28.0)


@unittest.skipUnless(_DATA is not None, "analysis artefact not generated yet")
class TestArtefact(unittest.TestCase):
    def test_integrity_flags(self):
        ig = _DATA["integrity"]
        self.assertTrue(ig["all_component_values_finite"])
        self.assertTrue(ig["no_topology_or_native_rule_change"])
        self.assertTrue(ig["no_future_information_used"])
        self.assertTrue(ig["native_controls_unchanged_in_every_config"])

    def test_service_node_set(self):
        self.assertEqual(_DATA["service_node_policy"]["n_service_junctions"], 121)
        self.assertEqual(_DATA["service_node_policy"]["n_connector_junctions"], 5)

    def test_per_timestep_matches_validated_accounting(self):
        # per-timestep component extraction must equal the validated instrument
        self.assertLess(
            _DATA["integrity"]["per_timestep_vs_validated_accounting_max_abs_diff"],
            1e-6)

    def test_reference_reproduces_baseline(self):
        ref = _DATA["configurations"]["reference_nominal"]["validated_accounting"]
        self.assertAlmostEqual(ref["leakage_mean_gpm"], 84.730, places=2)
        self.assertAlmostEqual(ref["dsr_mean"], 0.98334, places=4)
        self.assertEqual(ref["n_node_timesteps_below_20psi"], 386)
        self.assertEqual(ref["n_node_timesteps_negative_pressure"], 0)

    def test_every_config_finite_and_full_horizon(self):
        for name, c in _DATA["configurations"].items():
            self.assertTrue(c["all_finite"], name)
            self.assertEqual(c["n_timesteps"], 193, name)

    def test_correlation_matrix_square_10(self):
        m = _DATA["cross_component_correlation"]["matrix"]
        self.assertEqual(len(m), 10)
        self.assertTrue(all(len(row) == 10 for row in m))

    def test_pooled_stats_finite(self):
        for k, s in _DATA["pooled_component_stats"].items():
            for key, val in s.items():
                self.assertTrue(np.isfinite(val), f"{k}.{key}")

    def test_formulations_are_proposed_not_approved(self):
        for f in _DATA["proposed_formulations"]:
            self.assertEqual(f.get("status"), "PROPOSED", f.get("name"))
        self.assertNotIn("APPROVED", _DATA["status"])


if __name__ == "__main__":
    unittest.main()

