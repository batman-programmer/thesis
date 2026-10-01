"""STAGE-D correctness battery: D-P6-006 F1 admissibility layer.

The admissibility PREDICATES (TS4 hard backstop, TS2 relative worst-node guard)
and the full ESCALATION LADDER are exercised deterministically with a FakeDriver
that returns canned intra-step window traces -- so every branch is covered
WITHOUT hydraulics. The REAL-EPANET probe-non-mutation + native->accepted checks
live in test_env_integration.py. Run:

    .venv/Scripts/python.exe -m unittest tests.test_safety -v
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

import action_mapper as AM  # noqa: E402
import safety as SF  # noqa: E402


class FR:
    """A canned per-segment trace: intra-step n_neg and p_min service signals."""
    def __init__(self, n_neg, p_min):
        self.intra_n_neg = list(n_neg)
        self.intra_p_min_psi = list(p_min)


class FakeDriver:
    """Returns queued window traces: probe(proposed) then probe(hold)."""
    def __init__(self, seq):
        self.seq = list(seq)

    def probe(self, prv, pump, horizon_steps):
        return self.seq.pop(0)


A_PROP = np.full(7, 0.3)        # distinct from hold so we can tell which executed
A_HOLD = np.full(7, -0.2)
NAT_PRV = {v: 1.0 for v in AM.ACTION_IDS[:5]}
NAT_PUMP = {p: 2.0 for p in AM.ACTION_IDS[5:]}
PROP_PRV, _ = AM.to_command(A_PROP)
HOLD_PRV, _ = AM.to_command(A_HOLD)


def _run(seq):
    return SF.resolve_action(FakeDriver(seq), A_PROP, A_HOLD, NAT_PRV, NAT_PUMP)


class TestPredicates(unittest.TestCase):
    def test_ts4_safe(self):
        self.assertTrue(SF.ts4_safe(np.array([0, 0, 0], dtype=float)))
        self.assertFalse(SF.ts4_safe(np.array([0, 1, 0], dtype=float)))

    def test_ts2_safe_and_eps_slack(self):
        prop = np.array([30.0, 28.0, 27.0])
        hold = np.array([30.0, 29.0, 28.0])          # prop worse by 1 psi at idx1,2
        self.assertFalse(SF.ts2_safe(prop, hold, 0.0))
        self.assertTrue(SF.ts2_safe(prop, hold, 1.0))   # eps slack admits a 1 psi dip
        self.assertTrue(SF.ts2_safe(hold, hold, 0.0))   # a hold cannot beat itself


class TestEscalationLadder(unittest.TestCase):
    def test_1_accepted_executes_proposed(self):
        # proposed TS4-ok and >= hold everywhere -> accept, execute proposed.
        r = _run([[FR([0, 0, 0], [30, 29, 28])], [FR([0, 0, 0], [30, 28, 27])]])
        self.assertEqual(r.outcome, "accepted")
        self.assertTrue(r.proposed_admissible)
        self.assertEqual(r.executed_prv, PROP_PRV)
        self.assertEqual(r.n_neg_proposed, 0)
        self.assertEqual(r.window_instants, 3)

    def test_2_reject_to_hold_via_ts2(self):
        # proposed TS4-ok but worse than hold at an instant -> reject to hold.
        r = _run([[FR([0, 0, 0], [30, 20, 15])], [FR([0, 0, 0], [30, 28, 27])]])
        self.assertEqual(r.outcome, "reject_to_hold")
        self.assertFalse(r.proposed_admissible)
        self.assertEqual(r.executed_prv, HOLD_PRV)
        self.assertLess(r.min_dp_min_psi, 0.0)           # proposal dipped below hold

    def test_3_reject_to_hold_via_ts4(self):
        # proposed drives a node negative; hold is TS4-safe -> reject to hold.
        r = _run([[FR([0, 1, 0], [30, -1, 28])], [FR([0, 0, 0], [30, 28, 27])]])
        self.assertEqual(r.outcome, "reject_to_hold")
        self.assertEqual(r.executed_prv, HOLD_PRV)
        self.assertGreater(r.n_neg_proposed, 0)
        self.assertTrue(r.hold_ts4_safe)

    def test_4_reference_fallback(self):
        # proposed AND hold both TS4-unsafe -> escalate to the native reference.
        r = _run([[FR([0, 1, 0], [30, -1, 28])], [FR([0, 0, 1], [30, 28, -2])]])
        self.assertEqual(r.outcome, "reference_fallback")
        self.assertFalse(r.proposed_admissible)
        self.assertFalse(r.hold_ts4_safe)
        self.assertEqual(r.executed_prv, NAT_PRV)

    def test_5_diagnostics_counts(self):
        r = _run([[FR([0, 2, 0], [30, -1, 28])], [FR([1, 0, 0], [25, 28, 27])]])
        self.assertEqual(r.n_neg_proposed, 2)
        self.assertEqual(r.n_neg_hold, 1)
        self.assertEqual(r.window_instants, 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
