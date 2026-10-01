"""Action encode/decode for the BWSN-1 PPO environment (D-P6-001/002/003).

The policy emits a normalized action ``a ∈ [-1, 1]^7``; the hydraulic driver
consumes PHYSICAL quantities (PRV setpoints in psi, pump relative speeds). This
module is the ONLY place that converts between the two, so the frozen encoding
lives in exactly one spot.

FROZEN CONTRACT (docs/PHASE6_ACTION_SPACE_SPEC.md, APPROVED 2026-09-27):

    index  element     quantity              bounds [lower, upper]
    0      VALVE-173   PRV setpoint (psi)     [54.5, 100.0]
    1      VALVE-175   PRV setpoint (psi)     [21.5, 110.0]
    2      VALVE-176   PRV setpoint (psi)     [20.0, 59.524]
    3      VALVE-177   PRV setpoint (psi)     [20.0, 90.0]
    4      VALVE-178   PRV setpoint (psi)     [20.0, 74.0]
    5      PUMP-170    relative speed         [0.82, 1.10]
    6      PUMP-172    relative speed         [0.77, 1.10]

Encoding is ABSOLUTE (not delta): every step the agent emits the full setpoint /
speed, not an increment (D-P6-001). The excluded valves {174, 179, 180} and the
native pump STATUS rules are NOT touched here -- they remain hydraulic elements
driven by the INP (D-P6-002/003).

    forward : physical_i = lower_i + ((a_i + 1) / 2) * (upper_i - lower_i)
    inverse : a_i        = 2 * (physical_i - lower_i) / (upper_i - lower_i) - 1

The ordering, ids and bounds are IMPORTED from ``state_builder`` (the frozen
mirror of the spec) so the action vector and the observation's "previous
commanded" blocks can never disagree about what index means what.
"""

from __future__ import annotations

import numpy as np

from state_builder import (  # frozen single source of truth
    PRV_IDS,
    PRV_BOUNDS_PSI,
    PUMP_IDS,
    PUMP_BOUNDS,
    DTYPE,
)

# Canonical flat action order: 5 PRV setpoints then 2 pump speeds.
ACTION_IDS: tuple[str, ...] = tuple(PRV_IDS) + tuple(PUMP_IDS)
ACTION_DIM: int = len(ACTION_IDS)  # 7
_BOUNDS: dict[str, tuple[float, float]] = {**PRV_BOUNDS_PSI, **PUMP_BOUNDS}

# Per-index (lower, upper) arrays, frozen at import for vectorised mapping.
ACTION_LOW: np.ndarray = np.array([_BOUNDS[k][0] for k in ACTION_IDS], dtype=float)
ACTION_HIGH: np.ndarray = np.array([_BOUNDS[k][1] for k in ACTION_IDS], dtype=float)


def to_physical(action: np.ndarray) -> np.ndarray:
    """Map a normalized action ``a ∈ [-1, 1]^7`` to the physical 7-vector.

    The action is CLIPPED to [-1, 1] first: a PPO Gaussian policy can propose
    values slightly outside the box, and the frozen bounds are hard actuator
    limits, so out-of-box proposals saturate at the nearest bound rather than
    extrapolating past it. Pure; no side effects.
    """
    a = np.clip(np.asarray(action, dtype=float).reshape(ACTION_DIM), -1.0, 1.0)
    return ACTION_LOW + 0.5 * (a + 1.0) * (ACTION_HIGH - ACTION_LOW)


def to_normalized(physical: np.ndarray) -> np.ndarray:
    """Inverse map physical 7-vector -> normalized ``a ∈ [-1, 1]^7`` (clipped)."""
    phys = np.asarray(physical, dtype=float).reshape(ACTION_DIM)
    a = 2.0 * (phys - ACTION_LOW) / (ACTION_HIGH - ACTION_LOW) - 1.0
    return np.clip(a, -1.0, 1.0)


def to_command(action: np.ndarray) -> tuple[dict[str, float], dict[str, float]]:
    """Split a normalized action into the ``(prv_setpoints_psi, pump_speeds)``
    dict pair that ``SteppingHydraulicDriver.step`` consumes."""
    phys = to_physical(action)
    prv = {v: float(phys[i]) for i, v in enumerate(PRV_IDS)}
    pump = {p: float(phys[len(PRV_IDS) + i]) for i, p in enumerate(PUMP_IDS)}
    return prv, pump


def command_to_normalized(prv_setpoints_psi: dict[str, float],
                          pump_speeds: dict[str, float]) -> np.ndarray:
    """Inverse of :func:`to_command`: physical command dicts -> normalized action.

    Used to seed the "previous commanded action" at ``reset`` (the native
    operating point) so the step-0 movement penalty is measured against a real
    normalized vector, and to log the executed command in observation space.
    """
    phys = np.array(
        [prv_setpoints_psi[v] for v in PRV_IDS]
        + [pump_speeds[p] for p in PUMP_IDS], dtype=float)
    return to_normalized(phys)


def as_float32(action: np.ndarray) -> np.ndarray:
    """Return a contiguous float32 copy clipped to the box (gym action dtype)."""
    return np.clip(np.asarray(action, dtype=DTYPE).reshape(ACTION_DIM), -1.0, 1.0)
