"""D-P6-006 execution-time admissibility layer (architecture F1, FINALIZED).

Before a proposed action is committed, F1 forward-simulates it over the window
[0..H] from the IDENTICAL current real state and compares it to the HOLD
counterfactual (the previous executed action, forward-simulated from the same
state). A proposal is ADMISSIBLE iff, at EVERY instant in the window:

    TS4  (hard negative-pressure backstop)   N_neg(proposed) == 0
    TS2  (relative worst-node guard)         p_min(proposed) - p_min(hold) >= -eps_p

Both signals are read over the 121 SERVICE junctions (connectors are excluded
artefacts), at the 180 s intra-step rule cadence carried in each ``StepResult``.

ESCALATION LADDER (handling)
----------------------------
  H1  reject-to-hold (PRIMARY)      : proposal inadmissible -> execute the hold
                                       action (previous executed command). Hold
                                       cannot violate TS2 against itself, so it is
                                       accepted whenever it is TS4-safe.
  H3  reference-fallback (ESCALATE) : if the hold is ALSO not TS4-safe (its own
                                       window already drives a service node
                                       negative), execute the native reference
                                       operating point instead.

  (H2 clip-toward-previous / alpha-blend is documented in the decision register
   but is NOT the primary handler and is not implemented here.)

FROZEN DEFAULTS (reconfigurable): eps_p = 0.0 psi, H = 1 control step (1800 s).
The admissibility predicates reuse the SAFE-iff primitives characterised in
``p6_s9_*`` (S4 -> TS4, S2 -> TS2 over the temporal window).

SCOPE (non-universal, D-P6-006): this layer guarantees admissibility ONLY against
the simulated BWSN-1 model under the frozen solver settings; it makes no
universal safety claim about the real network or unmodelled conditions.

This module performs NO hydraulics itself: it drives ``driver.probe`` (the
non-committing forward simulation) and ``action_mapper`` only. It has no gym /
torch / SB3 dependency, so it is testable under STAGE C/D without those deps.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

import action_mapper as AM


@dataclass(frozen=True)
class SafetyConfig:
    """F1 admissibility parameters (defaults = frozen D-P6-006 values)."""
    eps_p_psi: float = 0.0        # TS2 slack; 0.0 = proposal may not worsen worst node
    horizon_steps: int = 1        # window H in control steps (1 = 1800 s)


@dataclass
class SafetyDecision:
    """What the layer executed, why, and the window diagnostics (audit trail)."""
    executed_prv: dict            # PRV setpoints (psi) actually committed
    executed_pump: dict           # pump speeds actually committed
    outcome: str                  # "accepted" | "reject_to_hold" | "reference_fallback"
    proposed_admissible: bool
    hold_ts4_safe: bool
    min_dp_min_psi: float         # worst (most negative) p_min(proposed)-p_min(hold)
    n_neg_proposed: int           # total service negative-pressure instants (proposed)
    n_neg_hold: int               # total service negative-pressure instants (hold)
    window_instants: int


def _window_trace(results: list) -> tuple[np.ndarray, np.ndarray]:
    """Concatenate the intra-step (p_min, n_neg) service traces over the window."""
    n_neg = np.array([n for r in results for n in r.intra_n_neg], dtype=float)
    p_min = np.array([p for r in results for p in r.intra_p_min_psi], dtype=float)
    return n_neg, p_min


def ts4_safe(n_neg_trace: np.ndarray) -> bool:
    """Hard negative-pressure backstop: no service node negative anywhere."""
    return bool((n_neg_trace == 0).all())


def ts2_safe(p_min_proposed: np.ndarray, p_min_hold: np.ndarray,
             eps_p_psi: float) -> bool:
    """Relative worst-node guard: proposal never worse than hold by > eps_p."""
    return bool((p_min_proposed - p_min_hold >= -eps_p_psi).all())


def resolve_action(driver, proposed_norm: np.ndarray, prev_exec_norm: np.ndarray,
                   native_prv: dict, native_pump: dict,
                   config: SafetyConfig = SafetyConfig()) -> SafetyDecision:
    """Decide the executed action for one control step under F1 admissibility.

    ``driver``          a reset ``SteppingHydraulicDriver`` at the current state.
    ``proposed_norm``   the policy's normalised action a_t in [-1,1]^7.
    ``prev_exec_norm``  previous EXECUTED normalised action (the hold baseline).
    ``native_prv/pump`` the reference operating point for H3 escalation.
    ``config``          eps_p / horizon (defaults = frozen).

    Non-committing: probes both branches, then returns the physical command the
    env should pass to ``driver.step``. Does not advance the episode.
    """
    proposed_prv, proposed_pump = AM.to_command(proposed_norm)
    hold_prv, hold_pump = AM.to_command(prev_exec_norm)

    pr = driver.probe(proposed_prv, proposed_pump, config.horizon_steps)
    hr = driver.probe(hold_prv, hold_pump, config.horizon_steps)
    nn_p, pm_p = _window_trace(pr)
    nn_h, pm_h = _window_trace(hr)

    proposed_ts4 = ts4_safe(nn_p)
    proposed_ts2 = ts2_safe(pm_p, pm_h, config.eps_p_psi)
    proposed_ok = proposed_ts4 and proposed_ts2
    hold_ts4 = ts4_safe(nn_h)

    min_dp = float(np.min(pm_p - pm_h)) if pm_p.size else float("nan")
    diag = dict(min_dp_min_psi=min_dp,
                n_neg_proposed=int(nn_p.sum()), n_neg_hold=int(nn_h.sum()),
                hold_ts4_safe=hold_ts4, window_instants=int(nn_p.size))

    if proposed_ok:
        return SafetyDecision(proposed_prv, proposed_pump, "accepted",
                              proposed_admissible=True, **diag)
    if hold_ts4:
        return SafetyDecision(hold_prv, hold_pump, "reject_to_hold",
                              proposed_admissible=False, **diag)
    return SafetyDecision(dict(native_prv), dict(native_pump), "reference_fallback",
                          proposed_admissible=False, **diag)
