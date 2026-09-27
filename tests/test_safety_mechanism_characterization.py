"""STEP 9 (WU-15) test battery for the safety-mechanism CHARACTERIZATION.

Standard-library `unittest` + numpy only (no pytest / gymnasium / torch). The
pure-function tests run without EPANET; the artefact tests validate the produced
results/phase6/p6_s9_safety_mechanism_characterization.json and are skipped if it
is absent. This artefact is EVIDENCE ONLY: the tests assert that NO mechanism or
policy is selected/ranked/scored/recommended (researcher_selection is null and no
forbidden key token appears anywhere in the JSON).

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

import p6_s9_safety_mechanism_characterization as M  # noqa: E402

ART = ROOT / "results" / "phase6" / "p6_s9_safety_mechanism_characterization.json"
_DATA = json.loads(ART.read_text(encoding="utf-8")) if ART.exists() else None

PART22_FIELDS = (
    "experiment_metadata", "metric_definitions", "candidates",
    "provisional_thresholds", "test_case_classes", "tested_states",
    "tested_actions", "current_state_metrics", "proposed_action_metrics",
    "post_action_metrics", "delta_metrics", "safety_rule_outputs",
    "handling_policy_outputs", "intervention_metrics", "baseline_compatibility",
    "severe_degradation_cases", "intermediate_control_cases",
    "local_collapse_examples", "computational_cost", "PPO_compatibility",
    "limitations", "researcher_selection")


def _iter_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _iter_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_keys(v)


class TestPureHelpers(unittest.TestCase):
    def test_action_dim_and_bounds(self):
        self.assertEqual(M.ACTION_DIM, 7)
        self.assertEqual(len(M.ACTUATOR_ORDER), 7)
        self.assertEqual(len(M.ACT_BOUNDS), 7)

    def test_encode_decode_round_trip(self):
        # midpoint command -> a ~ 0; round-trip must be an identity.
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

    def test_decode_endpoints(self):
        lo_a = [-1.0] * 7
        hi_a = [1.0] * 7
        prv_lo, pump_lo = M.decode_action(lo_a)
        prv_hi, pump_hi = M.decode_action(hi_a)
        for k in M.ACTUATOR_ORDER:
            lo, hi = M.ACT_BOUNDS[k]
            got_lo = (prv_lo if k in M.R8.PRV_IDS else pump_lo)[k]
            got_hi = (prv_hi if k in M.R8.PRV_IDS else pump_hi)[k]
            self.assertAlmostEqual(got_lo, lo, places=9)
            self.assertAlmostEqual(got_hi, hi, places=9)

    def test_safety_rules_semantics(self):
        # True == SAFE (do NOT intervene).
        self.assertTrue(M.rule_s1_safe(20.0, 20.0))
        self.assertFalse(M.rule_s1_safe(19.999, 20.0))
        self.assertTrue(M.rule_s2_safe(-1.0, 2.0))
        self.assertFalse(M.rule_s2_safe(-3.0, 2.0))
        self.assertTrue(M.rule_s3_safe(1.0, 2.0))
        self.assertFalse(M.rule_s3_safe(3.0, 2.0))
        self.assertTrue(M.rule_s4_safe(0.0))
        self.assertFalse(M.rule_s4_safe(1.0))

    def test_l2_helpers(self):
        self.assertAlmostEqual(M.l2([3.0, 4.0]), 5.0)
        self.assertAlmostEqual(M.l2sq([3.0, 4.0]), 25.0)

    def test_delta_scalars(self):
        cur = {"p_min": 10.0, "D": 5.0, "Q_leak": 80.0, "DSR": 0.9,
               "Q_unserved": 1.0}
        post = {"p_min": 8.0, "D": 7.0, "Q_leak": 78.0, "DSR": 0.88,
                "Q_unserved": 1.5}
        d = M.delta_scalars(cur, post)
        self.assertAlmostEqual(d["dp_min"], -2.0)
        self.assertAlmostEqual(d["dD"], 2.0)
        self.assertAlmostEqual(d["dQ_leak"], -2.0)
        self.assertAlmostEqual(d["dDSR"], -0.02)
        self.assertAlmostEqual(d["dQ_unserved"], 0.5)

    def test_four_candidates_only(self):
        c = M.candidate_descriptors()
        self.assertEqual(set(c), {"S1", "S2", "S3", "S4"})


@unittest.skipUnless(_DATA is not None, "characterization artefact not generated yet")
class TestArtefact(unittest.TestCase):
    def test_all_part22_fields_present(self):
        for f in PART22_FIELDS:
            self.assertIn(f, _DATA, f)

    def test_researcher_selection_is_null(self):
        self.assertIsNone(_DATA["researcher_selection"])

    def test_no_forbidden_key_tokens(self):
        forb = M.FORBIDDEN_KEY_TOKENS
        bad = sorted({k for k in _iter_keys(_DATA)
                      if any(t in str(k).lower() for t in forb)})
        self.assertEqual(bad, [], f"forbidden key tokens: {bad}")

    def test_frozen_invariants(self):
        meta = _DATA["experiment_metadata"]
        self.assertEqual(meta["action_dim"], 7)
        self.assertEqual(meta["observation_dim"], 139)
        self.assertEqual(meta["n_service_junctions"], 121)
        self.assertEqual(meta["n_connector_junctions"], 5)

    def test_reference_reproduces_frozen_baseline(self):
        ref = _DATA["tested_states"]["reference_nominal"]["validated_accounting"]
        self.assertAlmostEqual(ref["leakage_mean_gpm"], 84.72988433677985, places=6)
        self.assertEqual(ref["n_node_timesteps_below_20psi"], 386)
        self.assertEqual(ref["n_node_timesteps_negative_pressure"], 0)

    def test_only_four_candidates(self):
        self.assertEqual(set(_DATA["candidates"]), {"S1", "S2", "S3", "S4"})

    def test_every_tested_state_finite_and_full_horizon(self):
        for name, s in _DATA["tested_states"].items():
            self.assertTrue(s["all_finite"], name)
            self.assertEqual(s["n_timesteps"], 193, name)

    def test_safety_rule_outputs_are_descriptive_not_rates(self):
        # descriptive activation fields only; NO false-positive/negative keys.
        for tr, cands in _DATA["safety_rule_outputs"].items():
            for cand in ("S1", "S2", "S3", "S4"):
                for key, rec in cands[cand].items():
                    self.assertIn("activation_fraction_sustained", rec)
                    self.assertIn("rule_activates_at_shared_initial", rec)
                    self.assertGreaterEqual(rec["activation_fraction_sustained"], 0.0)
                    self.assertLessEqual(rec["activation_fraction_sustained"], 1.0)

    def test_s4_never_activates_on_measured_evidence(self):
        # No swept in-bounds config produced a negative-pressure node.
        for tr, cands in _DATA["safety_rule_outputs"].items():
            rec = cands["S4"]["hard_backstop"]
            self.assertEqual(rec["n_activations_sustained"], 0, tr)

    def test_s1_20psi_flags_chronic_baseline(self):
        # Governing chronic-baseline fact: an absolute 20-psi rule flags the
        # native baseline (identity hold) at every timestep.
        bc = _DATA["baseline_compatibility"]["identity_hold_rule_activation"]
        self.assertAlmostEqual(
            bc["S1"]["theta_p_psi=20"]["activation_fraction_sustained"], 1.0)

    def test_relative_rules_baseline_compatible_on_hold(self):
        bc = _DATA["baseline_compatibility"]["identity_hold_rule_activation"]
        for key, rec in bc["S2"].items():
            self.assertEqual(rec["n_activations_sustained"], 0, f"S2 {key}")
        for key, rec in bc["S3"].items():
            self.assertEqual(rec["n_activations_sustained"], 0, f"S3 {key}")

    def test_handling_policies_present(self):
        for seg in ("reference_to_severe", "high_pressure_to_severe"):
            pol = _DATA["handling_policy_outputs"][seg]
            self.assertEqual(set(pol), {"H1", "H2", "H3"})
            self.assertIn("per_rule_admissible_alpha", pol["H2"])

    def test_h1_h3_state_dependent(self):
        # From the high-pressure current state, previous-action (H1) and the
        # documented fallback (H3) differ; from reference they coincide.
        hp = _DATA["handling_policy_outputs"]["high_pressure_to_severe"]
        self.assertNotEqual(hp["H1"]["executed_action"], hp["H3"]["executed_action"])


if __name__ == "__main__":
    unittest.main()
