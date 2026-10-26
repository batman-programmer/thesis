"""Focused F5/F6 regressions for wrapper scenario access and seed provenance.

The local venv intentionally has no gymnasium/SB3, so these tests exercise the
headless BaselineMaskWrapper branch and the same underlying env API. The real
Gymnasium branch contains explicit pass-through methods with identical behavior
and is verified on the Colab RL runtime.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT / "experiments" / "ppo"),
           str(_ROOT / "src" / "env"), str(_ROOT / "src" / "validation")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import baselines as BL  # noqa: E402
import make_env as ME  # noqa: E402
import phase5_common as C  # noqa: E402


class TestWrappedScenarioAndSeedAccess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._old_results = C.RESULTS
        cls._scratch = Path(tempfile.mkdtemp(prefix="p6_f5_f6_scratch_"))
        C.RESULTS = cls._scratch

    @classmethod
    def tearDownClass(cls):
        C.RESULTS = cls._old_results
        import shutil
        shutil.rmtree(cls._scratch, ignore_errors=True)

    def test_wrapper_exposes_fixed_scenario_and_provenance(self):
        env = ME.make_env(enable_safety=False, baseline_mode="prv_only",
                          demand_scenario="native")
        env.set_demand_scenario("val/0")
        _obs, info = env.reset()
        self.assertEqual(env.demand_scenario.to_dict()["scenario_id"], "val/0")
        self.assertEqual(info["demand_scenario"]["scenario_id"], "val/0")
        prov = info["scenario_seed_provenance"]
        self.assertEqual(prov["mode"], "fixed")
        self.assertEqual(prov["master_seed"], 20261019)
        self.assertEqual(prov["scenario_id"], "val/0")
        # A fixed scenario is NOT drawn from a stream: no stream seed may be
        # reported, and a gym reset seed must not be presented as one.
        self.assertNotIn("effective_stream_seed", prov)
        self.assertNotIn("draw_index", prov)
        self.assertEqual(prov["master_seed_role"], "SeedSequence entropy")
        self.assertIsNone(prov["reset_seed_arg_gym_only"])

    def test_fixed_scenario_ignores_gym_reset_seed(self):
        env = ME.make_env(enable_safety=False, demand_scenario="val/1")
        _o1, i1 = env.reset(seed=7)
        _o2, i2 = env.reset(seed=999)
        self.assertEqual(i1["demand_scenario"]["multiplier"],
                         i2["demand_scenario"]["multiplier"],
                         "reset(seed=...) must not change a FIXED scenario")
        self.assertEqual(i1["scenario_seed_provenance"]["reset_seed_arg_gym_only"], 7)
        self.assertEqual(i2["scenario_seed_provenance"]["reset_seed_arg_gym_only"], 999)

    def test_train_reset_records_effective_seed_and_draw_index(self):
        env = ME.make_env(enable_safety=False, demand_scenario="train")
        _obs, info = env.reset(seed=123)
        prov = info["scenario_seed_provenance"]
        self.assertEqual(prov["mode"], "train")
        self.assertEqual(prov["reset_seed_arg"], 123)
        self.assertEqual(prov["effective_stream_seed"], 123)
        self.assertEqual(prov["draw_index"], 0)
        self.assertEqual(info["demand_scenario"]["draw_index"], 0)

    def test_mask_remains_active_when_scenario_is_accessed(self):
        env = ME.make_env(enable_safety=False, baseline_mode="prv_only",
                          demand_scenario="native")
        _obs, _info = env.reset()
        proposed = np.ones(7, dtype=np.float32)
        _obs, _r, _term, _trunc, info = env.step(proposed)
        native = BL.native_action()
        executed = np.asarray(info["executed_action_norm"])
        self.assertTrue(np.allclose(executed[5:], native[5:]))
        self.assertEqual(info["demand_scenario"]["scenario_id"], "native")


if __name__ == "__main__":
    unittest.main(verbosity=2)
