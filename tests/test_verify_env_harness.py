"""Focused regression tests for three verify_env/checksum harness defects.

Fast and dependency-light: no EPANET solve, no torch/SB3, no PPO training. They
target the HARNESS, not the hydraulics or the research design (the frozen
anchors, action/observation/reward/safety specs are untouched here).

Covers:
  1. line-ending-independent checksum -- LF and CRLF renderings of identical text
     hash equal, a real content change still differs, and the live working INP
     matches the frozen expected anchor on THIS platform;
  2. the corrected checkpoint round-trip comparison -- both predictions must come
     from the SAME trained policy state (a fake model proves the old pre-learning
     comparison would have been meaningless, and that genuine policy drift across
     save/load is still detected);
  3. exit-status propagation -- any failing REQUIRED subcheck (hydraulic,
     checksum, or PPO) makes the checker fail, exceptions cannot pass, and
     optional diagnostics do not fail a run.

Run: .venv/Scripts/python.exe -m unittest tests.test_verify_env_harness -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT / "experiments" / "ppo"),
           str(_ROOT / "src" / "env"), str(_ROOT / "src" / "validation")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import config as CFG            # noqa: E402
import verify_env as VE         # noqa: E402

_INP_TEXT = "[TITLE]\nBWSN demo\n[JUNCTIONS]\n J1  100.0  1.0\n"


# --------------------------------------------------------------------------- #
# Issue 1 -- line-ending-independent checksum                                  #
# --------------------------------------------------------------------------- #
class TestNormalizedChecksum(unittest.TestCase):
    def test_lf_and_crlf_hash_equal(self):
        lf = _INP_TEXT.encode()
        crlf = _INP_TEXT.replace("\n", "\r\n").encode()
        self.assertNotEqual(lf, crlf, "fixtures must differ in raw bytes")
        self.assertEqual(CFG.normalized_sha256(lf), CFG.normalized_sha256(crlf))

    def test_lone_cr_also_normalizes(self):
        cr = _INP_TEXT.replace("\n", "\r").encode()
        self.assertEqual(CFG.normalized_sha256(_INP_TEXT.encode()),
                         CFG.normalized_sha256(cr))

    def test_content_change_still_mismatches(self):
        # A meaningful hydraulic edit (elevation 100.0 -> 101.0) must NOT be
        # absorbed by normalization.
        changed = _INP_TEXT.replace("100.0", "101.0").encode()
        self.assertNotEqual(CFG.normalized_sha256(_INP_TEXT.encode()),
                            CFG.normalized_sha256(changed))

    def test_whitespace_change_still_mismatches(self):
        # Normalization must only touch line endings, not other whitespace.
        changed = _INP_TEXT.replace(" J1 ", " J1  ").encode()
        self.assertNotEqual(CFG.normalized_sha256(_INP_TEXT.encode()),
                            CFG.normalized_sha256(changed))

    def test_live_working_inp_matches_frozen_anchor(self):
        # Real evidence: the on-disk INP must match the expected anchor on THIS
        # platform regardless of how git materialised its line endings.
        self.assertTrue(CFG.WORKING_INP.exists(), CFG.WORKING_INP)
        self.assertEqual(CFG._working_inp_sha256(),
                         CFG.FROZEN_SPEC["working_inp_sha256_expected"])

    def test_fingerprint_reports_match(self):
        fp = VE.fingerprint()
        self.assertTrue(fp["working_inp_sha256_match"],
                        f"{fp['working_inp_sha256']} != {fp['working_inp_sha256_expected']}")


# --------------------------------------------------------------------------- #
# Issue 2 -- checkpoint round-trip must compare the TRAINED policy              #
# --------------------------------------------------------------------------- #
class _FakeModel:
    """Minimal predict/save stand-in whose policy changes when "trained".

    ``predict`` returns ``base`` plus a drift that is applied on save/load, so a
    harness that compared a PRE-learning prediction against the reloaded one
    would silently pass while a correct harness compares like with like.
    """

    def __init__(self, base, reload_drift=0.0, saved_registry=None):
        self.base = np.asarray(base, dtype=float)
        self.reload_drift = reload_drift
        self._registry = saved_registry if saved_registry is not None else {}

    def predict(self, obs, deterministic=True):
        assert deterministic, "round-trip must use deterministic prediction"
        return self.base.copy(), None

    def save(self, path):
        Path(path).write_text("fake-checkpoint")
        self._registry[str(path)] = self.base.copy()

    def load(self, path):
        base = self._registry[str(path)] + self.reload_drift
        return _FakeModel(base, 0.0, self._registry)


class TestRoundtripCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = _ROOT / "experiments" / "ppo" / "runs" / "_verify"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.ckpt = self.tmp / "unittest_fake_ckpt.zip"
        self.obs = np.zeros(139, dtype=np.float32)

    def tearDown(self):
        self.ckpt.unlink(missing_ok=True)

    def test_faithful_roundtrip_matches(self):
        m = _FakeModel(np.full(7, 0.25))
        r = VE.roundtrip_check(m, self.obs, self.ckpt, m.load)
        self.assertEqual(r["observation_shape"], [139])
        self.assertEqual(r["action_shape"], [7])
        self.assertTrue(r["action_in_bounds"])
        self.assertTrue(r["checkpoint_exists"])
        self.assertTrue(r["reload_prediction_matches"])

    def test_policy_drift_across_save_load_is_detected(self):
        m = _FakeModel(np.full(7, 0.25), reload_drift=0.5)
        r = VE.roundtrip_check(m, self.obs, self.ckpt, m.load)
        self.assertFalse(r["reload_prediction_matches"],
                         "a reloaded policy that predicts differently must FAIL")

    def test_out_of_box_action_flagged(self):
        m = _FakeModel(np.full(7, 1.5))
        r = VE.roundtrip_check(m, self.obs, self.ckpt, m.load)
        self.assertFalse(r["action_in_bounds"])

    def test_learn_precedes_roundtrip_in_sb3_smoke(self):
        # Source-order guard so the original defect (predicting BEFORE learning
        # and comparing that stale action to the reloaded one) cannot return.
        import inspect
        src = inspect.getsource(VE.sb3_smoke)
        self.assertIn("model.learn(", src)
        self.assertIn("roundtrip_check(", src)
        self.assertLess(src.index("model.learn("), src.index("roundtrip_check("),
                        "the tiny learn must happen BEFORE the round-trip check")


# --------------------------------------------------------------------------- #
# Issue 3 -- required subcheck failures must drive a nonzero exit               #
# --------------------------------------------------------------------------- #
def _passing_report():
    """A report in which every required check passes (PPO block available)."""
    return {
        "fingerprint": {"working_inp_sha256_match": True,
                        "working_inp_sha256": "abc", "working_inp_sha256_expected": "abc"},
        "hydraulic_smoke": {
            "reset_in_bounds": True, "obs_in_bounds_all_steps": True,
            "leak_anchor_match": True, "min_service_pressure_anchor_match": True,
            "negative_pressure_anchor_match": True, "horizon_ok": True},
        "sb3_smoke": {
            "available": True, "check_env": "OK", "obs_dim": 139, "act_dim": 7,
            "action_shape": [7], "action_in_bounds": True,
            "checkpoint_exists": True, "reload_prediction_matches": True},
    }


class TestExitStatusPropagation(unittest.TestCase):
    def test_passing_report_passes(self):
        ok, failures = VE.evaluate_report(_passing_report(), full=True,
                                          require_ppo=True)
        self.assertTrue(ok, failures)
        self.assertEqual(failures, [])

    def test_each_required_ppo_subcheck_failure_fails(self):
        falsify = {
            "check_env": "WARN", "obs_dim": 7, "act_dim": 139,
            "action_shape": [1, 7], "action_in_bounds": False,
            "checkpoint_exists": False, "reload_prediction_matches": False,
        }
        for key, bad in falsify.items():
            with self.subTest(subcheck=key):
                rep = _passing_report()
                rep["sb3_smoke"][key] = bad
                ok, failures = VE.evaluate_report(rep, full=True, require_ppo=True)
                self.assertFalse(ok, f"{key}={bad!r} must fail the checker")
                self.assertTrue(any(key.split('_')[0] in f for f in failures),
                                failures)

    def test_exception_in_ppo_block_fails(self):
        rep = _passing_report()
        rep["sb3_smoke"]["error"] = "RuntimeError: boom"
        ok, failures = VE.evaluate_report(rep, full=True, require_ppo=True)
        self.assertFalse(ok)
        self.assertTrue(any("no_exception" in f for f in failures), failures)

    def test_each_required_hydraulic_and_checksum_failure_fails(self):
        for section, key in (("fingerprint", "working_inp_sha256_match"),
                             ("hydraulic_smoke", "reset_in_bounds"),
                             ("hydraulic_smoke", "obs_in_bounds_all_steps"),
                             ("hydraulic_smoke", "leak_anchor_match"),
                             ("hydraulic_smoke", "min_service_pressure_anchor_match"),
                             ("hydraulic_smoke", "negative_pressure_anchor_match"),
                             ("hydraulic_smoke", "horizon_ok")):
            with self.subTest(section=section, key=key):
                rep = _passing_report()
                rep[section][key] = False
                ok, _ = VE.evaluate_report(rep, full=True, require_ppo=True)
                self.assertFalse(ok)

    def test_missing_required_value_is_a_failure_not_a_pass(self):
        rep = _passing_report()
        del rep["sb3_smoke"]["reload_prediction_matches"]
        ok, failures = VE.evaluate_report(rep, full=True, require_ppo=True)
        self.assertFalse(ok, "an absent required value must never count as a pass")
        self.assertTrue(any("reload_prediction_matches" in f for f in failures))

    def test_unavailable_ppo_fails_only_when_required(self):
        rep = _passing_report()
        rep["sb3_smoke"] = {"available": False, "reason": "ModuleNotFoundError"}
        ok_req, failures = VE.evaluate_report(rep, full=True, require_ppo=True)
        self.assertFalse(ok_req, "a gate that requires PPO must fail without it")
        self.assertTrue(any("available" in f for f in failures), failures)
        ok_opt, _ = VE.evaluate_report(rep, full=True, require_ppo=False)
        self.assertTrue(ok_opt, "without --require-ppo a missing stack is skipped")

    def test_full_anchors_only_required_with_full(self):
        rep = _passing_report()
        rep["hydraulic_smoke"]["leak_anchor_match"] = False
        self.assertFalse(VE.evaluate_report(rep, full=True)[0])
        self.assertTrue(VE.evaluate_report(rep, full=False)[0],
                        "anchor checks apply to --full runs only")

    def test_optional_diagnostics_do_not_fail(self):
        rep = _passing_report()
        rep["sb3_smoke"].update({
            "device": "cuda", "tiny_learn_seconds": 3.2,
            "warning": "You are trying to run PPO on the GPU, but it is "
                       "primarily intended to run on the CPU with MlpPolicy"})
        ok, failures = VE.evaluate_report(rep, full=True, require_ppo=True)
        self.assertTrue(ok, failures)

    def test_empty_report_fails(self):
        ok, failures = VE.evaluate_report({}, full=True, require_ppo=True)
        self.assertFalse(ok)
        self.assertTrue(failures)


if __name__ == "__main__":
    unittest.main(verbosity=2)
