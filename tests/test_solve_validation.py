"""F3 regression tests for transactional EPANET transition handling.

Contract under test: if the solve, the result validation, the extraction, or the
carry-state build fails, NO mutable driver field may change -- step_index,
t_elapsed, tank levels, pump statuses, done, requested-demand series, or the
episode scenario stamp. A numerical failure must never become a transition,
reward, or observation.

One real working-INP segment is solved in ``setUpClass`` to obtain a genuine
result object whose structure the corruption cases reuse. Solver scratch is
redirected to a TemporaryDirectory and ``phase5_common.RESULTS`` is restored in
``finally`` (class teardown) even when a test fails.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT / "src" / "env"), str(_ROOT / "src" / "validation")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import epanet_adapter as A  # noqa: E402
import g6_g7_g8_leak_pda as L  # noqa: E402
import phase5_common as C  # noqa: E402
import p6_s3_prv_finechar as S3  # noqa: E402

STATE_FIELDS = ("_step_index", "_t_elapsed", "_tank_levels_m", "_pump_status",
                "_done", "_req_gpm", "_scenario", "_episode_scenario")


def _state(driver) -> dict:
    """Comparable snapshot of every field the transactional contract protects."""
    snap = {}
    for name in STATE_FIELDS:
        value = getattr(driver, name)
        if name == "_req_gpm":
            value = None if value is None else value.copy()
        elif isinstance(value, dict):
            value = dict(value)
        snap[name] = value
    return snap


def _assert_state_equal(case: unittest.TestCase, before: dict, after: dict):
    for name in STATE_FIELDS:
        with case.subTest(field=name):
            b, a = before[name], after[name]
            if hasattr(b, "equals"):
                case.assertTrue(b.equals(a), f"{name} changed")
            else:
                case.assertEqual(b, a, f"{name} changed")


class TestSolveValidation(unittest.TestCase):
    """Invalid results fail before the driver commits a transition."""

    @classmethod
    def setUpClass(cls):
        cls._old_results = C.RESULTS
        cls._scratch = Path(tempfile.mkdtemp(prefix="p6_f3_scratch_"))
        C.RESULTS = cls._scratch
        try:
            wn = S3.build(None, None)
            svc, conn = S3.service_nodes(wn)
            cls.driver = A.SteppingHydraulicDriver(A.DriverConfig(
                coeff_us={}, service_nodes=svc, connector_nodes=conn))
            cls.driver.reset()
            seg = cls.driver._build_segment(cls.driver.cfg.control_step_s,
                                            cls.driver.t_elapsed_s)
            cls.driver._apply_command(seg, A.NATIVE_PRV_SETPOINT_PSI,
                                      A.NATIVE_PUMP_SPEED)
            cls.valid_result, _m, _u = L._run_with_retry(seg, "p6_f3_valid")
            cls.wn = seg
            cls.expected_index = (cls.driver.cfg.control_step_s
                                  // cls.driver.cfg.rule_timestep_s)
        except Exception:
            C.RESULTS = cls._old_results
            shutil.rmtree(cls._scratch, ignore_errors=True)
            raise

    @classmethod
    def tearDownClass(cls):
        C.RESULTS = cls._old_results
        shutil.rmtree(cls._scratch, ignore_errors=True)

    def setUp(self):
        self.before = _state(self.driver)

    def assert_state_unchanged(self):
        _assert_state_equal(self, self.before, _state(self.driver))

    # -- direct validation behaviour ---------------------------------------
    def validate(self, result):
        return self.driver._validate_solve(
            self.wn, result, expected_index=self.expected_index,
            expected_timestep_s=self.driver.cfg.rule_timestep_s, context="test")

    def test_valid_result_is_accepted(self):
        self.validate(self.valid_result)

    def test_truncated_report_is_rejected(self):
        result = SimpleNamespace(
            node={k: v.iloc[:1].copy() for k, v in self.valid_result.node.items()},
            link={k: v.iloc[:1].copy() for k, v in self.valid_result.link.items()},
        )
        with self.assertRaisesRegex(RuntimeError, "report instants"):
            self.validate(result)
        self.assert_state_unchanged()

    def test_missing_required_column_is_rejected(self):
        link = dict(self.valid_result.link)
        del link["setting"]
        with self.assertRaisesRegex(RuntimeError, "missing"):
            self.validate(SimpleNamespace(node=self.valid_result.node, link=link))
        self.assert_state_unchanged()

    def test_nonfinite_endpoint_is_rejected(self):
        link = {k: v.copy() for k, v in self.valid_result.link.items()}
        setting = link["setting"]
        setting.iloc[-1, setting.columns.get_loc("PUMP-170")] = np.nan
        link["setting"] = setting
        with self.assertRaisesRegex(RuntimeError, "non-finite"):
            self.validate(SimpleNamespace(node=self.valid_result.node, link=link))
        self.assert_state_unchanged()

    # -- step-level transactionality ---------------------------------------
    def _bad_results(self):
        """Yield (label, result) pairs that must all abort ``step``."""
        yield "truncated", SimpleNamespace(
            node={k: v.iloc[:1].copy() for k, v in self.valid_result.node.items()},
            link={k: v.iloc[:1].copy() for k, v in self.valid_result.link.items()})
        link = dict(self.valid_result.link)
        del link["setting"]
        yield "missing_column", SimpleNamespace(node=self.valid_result.node,
                                                link=link)
        nan_link = {k: v.copy() for k, v in self.valid_result.link.items()}
        st = nan_link["setting"]
        st.iloc[-1, st.columns.get_loc("PUMP-170")] = np.nan
        nan_link["setting"] = st
        yield "nonfinite", SimpleNamespace(node=self.valid_result.node,
                                           link=nan_link)

    def test_step_aborts_on_invalid_result_without_state_change(self):
        for label, result in self._bad_results():
            with self.subTest(case=label):
                self.before = _state(self.driver)
                with mock.patch.object(L, "_run_with_retry",
                                       return_value=(result, [], "invalid")):
                    with self.assertRaises(RuntimeError):
                        self.driver.step(A.NATIVE_PRV_SETPOINT_PSI,
                                         A.NATIVE_PUMP_SPEED)
                self.assert_state_unchanged()

    def test_step_aborts_when_extraction_raises(self):
        self.before = _state(self.driver)
        with mock.patch.object(L, "_run_with_retry",
                               return_value=(self.valid_result, [], "ok")), \
             mock.patch.object(self.driver, "_extract",
                               side_effect=ValueError("extract boom")):
            with self.assertRaisesRegex(ValueError, "extract boom"):
                self.driver.step(A.NATIVE_PRV_SETPOINT_PSI, A.NATIVE_PUMP_SPEED)
        self.assert_state_unchanged()

    def test_step_aborts_when_carry_state_build_raises(self):
        """A failure AFTER extraction must still leave the driver untouched."""
        self.before = _state(self.driver)
        real_extract = self.driver._extract

        def extract_then_blow_up(wn, res, **kwargs):
            real_extract(wn, res, **kwargs)
            raise RuntimeError("carry-state boom")

        with mock.patch.object(L, "_run_with_retry",
                               return_value=(self.valid_result, [], "ok")), \
             mock.patch.object(self.driver, "_extract",
                               side_effect=extract_then_blow_up):
            with self.assertRaisesRegex(RuntimeError, "carry-state boom"):
                self.driver.step(A.NATIVE_PRV_SETPOINT_PSI, A.NATIVE_PUMP_SPEED)
        self.assert_state_unchanged()

    # -- probe / reset restoration -----------------------------------------
    def test_probe_restores_state_after_solve_failure(self):
        self.before = _state(self.driver)
        with mock.patch.object(L, "_run_with_retry",
                               side_effect=RuntimeError("solver boom")):
            with self.assertRaisesRegex(RuntimeError, "solver boom"):
                self.driver.probe(A.NATIVE_PRV_SETPOINT_PSI,
                                  A.NATIVE_PUMP_SPEED, horizon_steps=1)
        self.assert_state_unchanged()

    def test_probe_restores_state_after_extraction_failure(self):
        self.before = _state(self.driver)
        with mock.patch.object(L, "_run_with_retry",
                               return_value=(self.valid_result, [], "ok")), \
             mock.patch.object(self.driver, "_extract",
                               side_effect=ValueError("probe extract boom")):
            with self.assertRaisesRegex(ValueError, "probe extract boom"):
                self.driver.probe(A.NATIVE_PRV_SETPOINT_PSI,
                                  A.NATIVE_PUMP_SPEED, horizon_steps=1)
        self.assert_state_unchanged()

    def test_probe_success_leaves_real_state_intact(self):
        self.before = _state(self.driver)
        self.driver.probe(A.NATIVE_PRV_SETPOINT_PSI, A.NATIVE_PUMP_SPEED,
                          horizon_steps=1)
        self.assert_state_unchanged()

    def test_reset_restores_state_after_failed_initial_solve(self):
        self.before = _state(self.driver)
        with mock.patch.object(L, "_run_with_retry",
                               side_effect=RuntimeError("reset solve boom")):
            with self.assertRaisesRegex(RuntimeError, "reset solve boom"):
                self.driver.reset()
        self.assert_state_unchanged()


if __name__ == "__main__":
    unittest.main(verbosity=2)