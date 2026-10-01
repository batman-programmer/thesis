"""D-P6-005 per-step reward (variant C-A_F1_balanced_dense, APPROVED).

The reward is a weighted sum of five NORMALISED penalties, all non-positive, so
the agent maximises by driving leakage, unserved demand, pressure deficit, and
actuator movement toward zero:

    r_t = - w_L * (leak_t          / leak_ref)
          - w_U * (unserved_t^+    / req_ref)
          - w_P * (deficit_t       / deficit_ref)
          - w_A * (||da_t||^2      / movement_L2sq_max)
          - w_E * (power_t         / power_ref)

FROZEN WEIGHTS / NORMALISERS (docs/PHASE6_REWARD_SPEC.md, byte-exact)
--------------------------------------------------------------------
    w_L = 1.0   leak_ref            = 84.72988433677985   GPM
    w_U = 1.0   req_ref             = 906.3987348621764   GPM
    w_P = 1.0   deficit_ref         = 28.671793365478514  psi*nodes (pooled p95)
    w_A = 0.1   movement_L2sq_max   = 28.0                (= 7 * 2^2, the box max)
    w_E = 0.0   power_ref           = 88.10062475649187   kW

The energy term is REPRESENTED but DISABLED (w_E = 0.0); power_ref is retained so
it can be re-enabled later without a schema change (D-P6-005).

MOVEMENT SEMANTICS (A2 resolution, D-P6-005 UNCHANGED)
------------------------------------------------------
``da_t = a_exec_t - a_exec_{t-1}`` in NORMALISED action space, where ``a_exec`` is
the EXECUTED (post-safety-layer) action -- "commanded" is defined to mean what
was actually executed. A static hold therefore gives ``da_t = 0`` EXACTLY and
contributes no movement penalty. At step 0 the previous executed action is the
native operating point (seeded at ``reset``), so the first movement is measured
against a real normalised vector, not against zero. ``movement_L2sq_max = 28`` is
the largest possible ``||da||^2`` on ``[-1, 1]^7`` (each of 7 components can move
by at most 2), so the normalised movement term lies in [0, 1].

All of leak_t, unserved_t^+, deficit_t, power_t are computed from the EXECUTED
hydraulic state by :mod:`metrics` (the frozen accounting law). This module only
applies the weights and normalisers; it performs no hydraulics.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from metrics import StepMetrics


@dataclass(frozen=True)
class RewardConfig:
    """Frozen D-P6-005 weights and reference normalisers (variant C-A_F1)."""
    w_leak: float = 1.0
    w_unserved: float = 1.0
    w_deficit: float = 1.0
    w_movement: float = 0.1
    w_energy: float = 0.0
    leak_ref: float = 84.72988433677985
    req_ref: float = 906.3987348621764
    deficit_ref: float = 28.671793365478514
    power_ref: float = 88.10062475649187
    movement_l2sq_max: float = 28.0


@dataclass
class RewardBreakdown:
    """Signed total plus every weighted term, for logging and audit (s.12)."""
    total: float
    leak_term: float          # weighted, >= 0 (subtracted from reward)
    unserved_term: float
    deficit_term: float
    movement_term: float
    energy_term: float
    movement_l2sq: float      # raw ||da||^2 before normalisation (diagnostic)


def movement_l2sq(da_norm: np.ndarray) -> float:
    """``||da||^2`` for a normalised executed-action delta ``a_t - a_{t-1}``."""
    d = np.asarray(da_norm, dtype=float).ravel()
    return float(np.dot(d, d))


def compute_reward(metrics: StepMetrics, da_norm: np.ndarray,
                   config: RewardConfig = RewardConfig()) -> RewardBreakdown:
    """Evaluate the frozen D-P6-005 reward for one control step.

    ``metrics``  the executed-state :class:`metrics.StepMetrics`.
    ``da_norm``  normalised executed-action delta ``a_exec_t - a_exec_{t-1}``.
    ``config``   weights + normalisers (defaults = frozen C-A_F1 values).

    Returns a :class:`RewardBreakdown`; ``total`` is the scalar reward.
    """
    l2sq = movement_l2sq(da_norm)

    leak_term = config.w_leak * (metrics.leak_gpm / config.leak_ref)
    unserved_term = config.w_unserved * (metrics.unserved_pos_gpm / config.req_ref)
    deficit_term = config.w_deficit * (metrics.deficit_psi_nodesum / config.deficit_ref)
    movement_term = config.w_movement * (l2sq / config.movement_l2sq_max)
    energy_term = config.w_energy * (metrics.power_kw / config.power_ref)

    total = -(leak_term + unserved_term + deficit_term + movement_term + energy_term)
    return RewardBreakdown(
        total=float(total),
        leak_term=float(leak_term),
        unserved_term=float(unserved_term),
        deficit_term=float(deficit_term),
        movement_term=float(movement_term),
        energy_term=float(energy_term),
        movement_l2sq=float(l2sq),
    )
