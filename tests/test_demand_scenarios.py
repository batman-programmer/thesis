"""STEP-10 demand-scenario unit tests (D-P6-007) — pure, no EPANET solve.

Covers the scenario module's contract (see the design brief s.9 acceptance
criteria 1-3 and the researcher's 2026-10-19 selections):

  * exact truncated-normal sampling: correct mean/std over a large sample,
    bounds respected, and the distribution is NOT clipped-normal (the inverse
    CDF of the truncated support differs from clipping an ordinary normal);
  * determinism: same identifier + same config -> byte-identical scenario;
    different master seeds -> different scenarios;
  * split integrity: train stream vs val/test/ood fixed scenarios use
    logically disjoint RNG streams (spawn keys 0..3); fixed scenarios differ
    from each other and are stable;
  * the training stream DRAWS NEW multipliers (never cycles a fixed set) and
    honours the reseed contract (same seed -> same sequence);
  * S2 per-junction factors are reproducible and vary across junctions;
  * native scenario is a pure identity (apply() mutates nothing);
  * demand_junctions on the frozen working INP yields 79 junctions;
  * apply() scales base demands EXACTLY and touches nothing else.

A tiny FakeWn with junctions/demand timeseries exercises apply() without any
WNTR dependency; the 79-junction check loads the real INP once.

Run:  .venv/Scripts/python.exe -m unittest tests.test_demand_scenarios -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

_SRC = Path(__file__).resolve().parents[1] / "src"
for _p in (str(_SRC / "env"), str(_SRC / "validation")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import demand_scenarios as DS  # noqa: E402

MU, SIGMA, LO, HI = DS.MU, DS.SIGMA, DS.LOWER, DS.UPPER


class _TS:
    """Minimal WNTR TimeSeries stand-in: only base_value is needed."""

    def __init__(self, base_value, pattern_name="PATTERN-0"):
        self.base_value = float(base_value)
        self.pattern_name = pattern_name


class _Node:
    def __init__(self, base_values):
        self.demand_timeseries_list = [_TS(b) for b in base_values]


class FakeWn:
    """Minimal wn stand-in: junction names + per-junction demand categories."""

    def __init__(self, junctions: dict[str, list[float]]):
        self.junction_name_list = sorted(junctions)
        self._nodes = {j: _Node(v) for j, v in junctions.items()}

    def get_node(self, j):
        return self._nodes[j]


# --------------------------------------------------------------------------- #
# exact truncated-normal sampling                                              #
# --------------------------------------------------------------------------- #
class TestTruncnormSampling(unittest.TestCase):
    def test_bounds_respected_over_many_draws(self):
        rng = np.random.default_rng(123)
        for _ in range(5000):
            x = DS.sample_truncnorm(rng)
            self.assertGreaterEqual(x, LO)
            self.assertLessEqual(x, HI)

    def test_ppf_matches_analytic_values(self):
        # u=0.5 must map to the truncated median, which for a symmetric
        # interval around mu equals mu itself.
        self.assertAlmostEqual(DS.truncnorm_ppf(0.5), MU, places=12)
        # monotone in u
        us = np.linspace(0.0, 1.0, 21)
        xs = [DS.truncnorm_ppf(float(u)) for u in us]
        self.assertTrue(all(xs[i] <= xs[i + 1] for i in range(len(xs) - 1)))
        # endpoint guards: u=0 -> (just above) lower, u=1 -> (just below) upper
        self.assertAlmostEqual(xs[0], LO, places=9)
        self.assertAlmostEqual(xs[-1], HI, places=9)

    def test_not_a_clipped_normal(self):
        # Clipping an ordinary N(mu, sigma) to [LO, HI] piles exactly LO/HI
        # mass at the bounds; the exact inverse-CDF transform does not.
        rng = np.random.default_rng(7)
        draws = np.array([DS.sample_truncnorm(rng) for _ in range(20000)])
        self.assertFalse(np.any(draws == LO), "exact ppf must not hit the lower bound")
        self.assertFalse(np.any(draws == HI), "exact ppf must not hit the upper bound")
        # Moments close to the analytic truncated-normal (scipy.stats.truncnorm
        # with a=-3, b=3: mean 1.0, std 0.0986578).
        self.assertLess(abs(draws.mean() - MU), 2e-3)
        self.assertLess(abs(draws.std() - 0.098658), 2e-3)

    def test_sample_mean_and_std_analytic(self):
        # scipy.stats.truncnorm(a=-3, b=3, loc=1, scale=0.1): mean 1.0,
        # std 0.0986578. Asserted to 2e-3 on 50k draws.
        rng = np.random.default_rng(20261019)
        xs = np.array([DS.sample_truncnorm(rng) for _ in range(50000)])
        self.assertLess(abs(xs.mean() - MU), 2e-3)
        self.assertLess(abs(xs.std() - 0.098658), 2e-3)


# --------------------------------------------------------------------------- #
# determinism / split integrity / no leakage                                   #
# --------------------------------------------------------------------------- #
class TestDeterminismAndSplitIntegrity(unittest.TestCase):
    def test_same_id_and_config_same_scenario(self):
        djs = DS.demand_junctions(_real_wn())
        for sid in DS.all_fixed_scenario_ids():
            s1 = DS.fixed_scenario(sid, demand_junctions_list=djs)
            s2 = DS.fixed_scenario(sid, demand_junctions_list=djs)
            self.assertEqual(s1.to_dict(), s2.to_dict(), sid)

    def test_different_master_seed_different_scenario(self):
        s_a = DS.fixed_scenario("val/0", DS.ScenarioConfig(master_seed=1))
        s_b = DS.fixed_scenario("val/0", DS.ScenarioConfig(master_seed=2))
        self.assertNotEqual(s_a.multiplier, s_b.multiplier)

    def test_fixed_scenarios_distinct_within_group(self):
        mults = [DS.fixed_scenario(s).multiplier for s in DS.validation_scenario_ids()]
        self.assertEqual(len(mults), DS.N_VALIDATION)
        self.assertEqual(len(set(mults)), len(mults), "val multipliers must differ")

    def test_train_stream_disjoint_from_fixed_groups(self):
        # The train stream draws must never equal ANY fixed evaluation draw,
        # and the fixed groups must differ from one another (spawn keys 0..3).
        djs = DS.demand_junctions(_real_wn())
        train = TrainingDraws(200)
        fixed = set()
        for sid in ["val/0", "val/1", "test/0", "test/2"]:
            fixed.add(round(DS.fixed_scenario(sid).multiplier, 12))
        ood0 = DS.fixed_scenario("ood/0", demand_junctions_list=djs)
        fixed.add(round(ood0.factors[djs[0]], 12))
        for m in train.mults:
            self.assertNotIn(round(m, 12), fixed,
                             "train draw coincides with a fixed eval scenario")

    def test_train_stream_draws_new_not_cycled(self):
        # 60 draws: a cycling implementation over 8 fixed realisations would
        # repeat within the first 9 draws.
        stream = DS.TrainingScenarioStream()
        ids = [stream.next().scenario_id for _ in range(60)]
        self.assertEqual(len(set(ids)), 60, "scenario ids must be unique per draw")
        mults = [m for m in TrainingDraws(60).mults]
        self.assertGreater(len(set(mults)), 8, "draws must not cycle a fixed set")

    def test_train_stream_reseed_contract(self):
        s1 = DS.TrainingScenarioStream()
        seq1 = [s1.next().multiplier for _ in range(5)]
        s2 = DS.TrainingScenarioStream()
        s2.reseed(DS.MASTER_SEED)
        seq2 = [s2.next().multiplier for _ in range(5)]
        self.assertEqual(seq1, seq2, "reseed(master) must reproduce the stream")


class TrainingDraws:
    """Collect training-stream multipliers (helper, no leakage of class state)."""

    def __init__(self, n):
        stream = DS.TrainingScenarioStream()
        self.mults = [stream.next().multiplier for _ in range(n)]


def _real_wn():
    """Load the frozen working INP once for junction-list/scaling checks."""
    import p6_s3_prv_finechar as S3
    return S3.build(None, None)


# --------------------------------------------------------------------------- #
# scenario application                                                         #
# --------------------------------------------------------------------------- #
class TestApply(unittest.TestCase):
    def _fake(self):
        # J1/J2 demand-bearing, J3 zero-demand, J4 zero-demand (spatial S2 test)
        return FakeWn({"J1": [100.0], "J2": [50.0, 25.0], "J3": [0.0], "J4": [0.0]})

    def test_native_identity(self):
        wn = self._fake()
        bases = wn.get_node("J2").demand_timeseries_list[0].base_value
        DS.NativeScenario().apply(wn)
        self.assertEqual(wn.get_node("J2").demand_timeseries_list[0].base_value, bases)

    def test_global_factor_scales_all_categories_exactly(self):
        wn = self._fake()
        DS.GlobalFactorScenario(1.5, "t").apply(wn)
        self.assertAlmostEqual(wn.get_node("J1").demand_timeseries_list[0].base_value, 150.0)
        self.assertAlmostEqual(wn.get_node("J2").demand_timeseries_list[0].base_value, 75.0)
        self.assertAlmostEqual(wn.get_node("J2").demand_timeseries_list[1].base_value, 37.5)
        # zero-demand junctions untouched (base stays exactly 0.0)
        self.assertEqual(wn.get_node("J3").demand_timeseries_list[0].base_value, 0.0)

    def test_junction_factors_target_only_named_junctions(self):
        wn = self._fake()
        DS.JunctionFactorScenario({"J1": 1.2}, "t").apply(wn)
        self.assertAlmostEqual(wn.get_node("J1").demand_timeseries_list[0].base_value, 120.0)
        self.assertAlmostEqual(wn.get_node("J2").demand_timeseries_list[0].base_value, 50.0)

    def test_multiplier_within_bounds_by_construction(self):
        djs = DS.demand_junctions(_real_wn())
        for sid in DS.all_fixed_scenario_ids():
            sc = DS.fixed_scenario(sid, demand_junctions_list=djs)
            if isinstance(sc, DS.NativeScenario):
                continue
            if isinstance(sc, DS.GlobalFactorScenario):
                self.assertGreaterEqual(sc.multiplier, LO, sid)
                self.assertLessEqual(sc.multiplier, HI, sid)
            else:                                    # S2 per-junction factors
                for j, f in sc.factors.items():
                    self.assertGreaterEqual(f, LO, f"{sid}:{j}")
                    self.assertLessEqual(f, HI, f"{sid}:{j}")

    def test_demand_junctions_on_working_inp(self):
        wn = _real_wn()
        djs = DS.demand_junctions(wn)
        self.assertEqual(len(djs), 79)
        self.assertEqual(djs, sorted(djs))
        # every listed junction carries positive base demand; every unlisted
        # junction carries none
        for j in wn.junction_name_list:
            pos = any(ts.base_value > 0.0
                      for ts in wn.get_node(j).demand_timeseries_list)
            self.assertEqual(pos, j in djs, j)

    def test_apply_on_real_inp_scales_expected_demand_exactly(self):
        # Acceptance criterion: uniform global scaling scales expected demand
        # exactly proportionally at every report instant (zero-demand rows of
        # the ratio are NaN/0 and masked out).
        wn = _real_wn()
        import wntr
        wn.options.time.report_timestep = 1800
        ref = wntr.metrics.expected_demand(wn)
        DS.GlobalFactorScenario(1.5, "t").apply(wn)
        pert = wntr.metrics.expected_demand(wn)
        ratio = (pert / ref).to_numpy().ravel()
        ref_v = np.asarray(ref).ravel()
        mask = np.isfinite(ratio) & (ref_v > 0.0)
        self.assertTrue(mask.sum() > 100, "mask must retain meaningful rows")
        self.assertTrue(np.allclose(ratio[mask], 1.5, rtol=1e-9),
                        f"expected_demand ratio not exactly 1.5: {ratio[mask][:5]}")


# --------------------------------------------------------------------------- #
# fixed scenario ids                                                           #
# --------------------------------------------------------------------------- #
class TestScenarioIds(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(DS.validation_scenario_ids(), ["val/0", "val/1", "val/2", "val/3"])
        self.assertEqual(DS.test_scenario_ids(),
                         ["test/0", "test/1", "test/2", "test/3"])
        self.assertEqual(DS.ood_scenario_ids(), ["ood/0", "ood/1"])
        self.assertEqual(DS.all_fixed_scenario_ids(),
                         ["native"] + DS.validation_scenario_ids()
                         + DS.test_scenario_ids() + DS.ood_scenario_ids())

    def test_unknown_id_rejected(self):
        for bad in ("val/4", "test/9", "ood/2", "bogus/0", "train/0"):
            with self.assertRaises(ValueError, msg=bad):
                DS.fixed_scenario(bad, demand_junctions_list=["J1"])
        # ood without the junction list is rejected:
        with self.assertRaises(ValueError):
            DS.fixed_scenario("ood/0")

    def test_native_alias(self):
        self.assertIsInstance(DS.fixed_scenario("native"), DS.NativeScenario)
        self.assertIsInstance(DS.fixed_scenario("native_nominal"), DS.NativeScenario)


if __name__ == "__main__":
    unittest.main(verbosity=2)
