"""Deterministic observation (state) builder for the BWSN-1 PPO environment.

STEP 7 (Phase 6) deliverable — STATE DESIGN ONLY. This module maps a raw
hydraulic snapshot at control-decision time `t` to the fixed-length, normalized
observation vector the PPO policy will see. It contains **no reward, no PPO, no
demand model, and no EPANET/WNTR call** — it is a pure, side-effect-free
transform so it can be unit-tested with numpy alone and reused unchanged by the
STEP 11 environment.

Single source of truth for the action space (bounds, ordering, encoding) is
`docs/PHASE6_ACTION_SPACE_SPEC.md` (APPROVED & FROZEN 2026-09-27,
D-P6-001/002/003). The frozen actuator bounds are mirrored here as constants and
verified against that spec / the live INP by `src/validation/p6_s7_state_spec.py`.

Observation contract (see docs/PHASE6_STATE_SPEC.md for full justification):

    index range   block                              dims  normalized range
    [0:121]       service-node pressures             121   [0, 1]  (clipped)
    [121:123]     tank levels (TANK-130, TANK-131)     2   [0, 1]
    [123:128]     previous COMMANDED PRV setpoints     5   [0, 1]
    [128:133]     PRV is_active (regulating) flags     5   {0, 1}
    [133:135]     previous COMMANDED pump speeds       2   [0, 1]
    [135:137]     pump REALIZED speeds (0 = closed)    2   [0, 1]
    [137:139]     time-of-day (sin, cos), 24 h period  2   [-1, 1]
    total dim = 139, dtype = float32

Timing convention: the observation at step t is built from the hydraulic state
AFTER the simulator has advanced to t under the PREVIOUS action (t-1) and BEFORE
the agent's action at t is applied. The "previous commanded" fields therefore
hold action_{t-1}. No future information (see docs/PHASE6_STATE_SPEC.md §20).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping

import numpy as np

DTYPE = np.float32

# --- Frozen approved action space (mirror of docs/PHASE6_ACTION_SPACE_SPEC.md) ---
PRV_IDS: tuple[str, ...] = (
    "VALVE-173", "VALVE-175", "VALVE-176", "VALVE-177", "VALVE-178",
)
PRV_BOUNDS_PSI: dict[str, tuple[float, float]] = {
    "VALVE-173": (54.5, 100.0),
    "VALVE-175": (21.5, 110.0),
    "VALVE-176": (20.0, 59.524),
    "VALVE-177": (20.0, 90.0),
    "VALVE-178": (20.0, 74.0),
}
PUMP_IDS: tuple[str, ...] = ("PUMP-170", "PUMP-172")
PUMP_BOUNDS: dict[str, tuple[float, float]] = {
    "PUMP-170": (0.82, 1.10),
    "PUMP-172": (0.77, 1.10),
}

# --- Pressure normalization band (ENGINEERING DECISION, STEP 7) ---------------
# Fixed physical band chosen to bracket the full service-node pressure range
# measured on BWSN-1 (~4 to 288 psi) with head-room for adverse actions
# (negative pressures) and overshoot, WITHOUT saturating the majority of nodes.
# See docs/PHASE6_STATE_SPEC.md §17. These are fixed constants, NOT data-derived
# running statistics (which would risk train/eval leakage).
P_MIN_PSI: float = -20.0
P_MAX_PSI: float = 300.0

DAY_SECONDS: float = 86400.0  # diurnal (24 h) period for cyclical time encoding


@dataclass(frozen=True)
class ObservationConfig:
    """Fixed observation layout + normalization constants for one network.

    `service_nodes` is the ordered (sorted) list of service junctions; connector
    artefacts (`connector_nodes`) are recorded for audit but are NEVER placed in
    the observation (docs/PHASE6_STATE_SPEC.md §16). Actuator bounds default to
    the frozen approved values; tank level bounds must be supplied from the INP.
    """

    service_nodes: tuple[str, ...]
    connector_nodes: tuple[str, ...]
    tank_ids: tuple[str, ...]
    tank_level_bounds_ft: Mapping[str, tuple[float, float]]
    prv_ids: tuple[str, ...] = PRV_IDS
    prv_bounds_psi: Mapping[str, tuple[float, float]] = field(
        default_factory=lambda: dict(PRV_BOUNDS_PSI))
    pump_ids: tuple[str, ...] = PUMP_IDS
    pump_bounds: Mapping[str, tuple[float, float]] = field(
        default_factory=lambda: dict(PUMP_BOUNDS))
    p_min_psi: float = P_MIN_PSI
    p_max_psi: float = P_MAX_PSI
    day_seconds: float = DAY_SECONDS

    @property
    def dim(self) -> int:
        return (len(self.service_nodes) + len(self.tank_ids)
                + 2 * len(self.prv_ids) + 2 * len(self.pump_ids) + 2)

    def slices(self) -> dict[str, slice]:
        """Named half-open index ranges into the observation vector."""
        n_p = len(self.service_nodes)
        n_t = len(self.tank_ids)
        n_v = len(self.prv_ids)
        n_u = len(self.pump_ids)
        i = 0
        out: dict[str, slice] = {}
        out["pressures"] = slice(i, i + n_p); i += n_p
        out["tank_levels"] = slice(i, i + n_t); i += n_t
        out["prev_cmd_prv_setpoint"] = slice(i, i + n_v); i += n_v
        out["prv_is_active"] = slice(i, i + n_v); i += n_v
        out["prev_cmd_pump_speed"] = slice(i, i + n_u); i += n_u
        out["pump_realized_speed"] = slice(i, i + n_u); i += n_u
        out["time_of_day"] = slice(i, i + 2); i += 2
        return out


@dataclass
class RawState:
    """Raw hydraulic snapshot at control step t (physical units).

    All actuator fields are keyed by actuator id. `prev_cmd_*` hold the action
    the agent COMMANDED at step t-1 (post action->physical mapping); the pump
    `realized` field holds the speed actually in effect after the native STATUS
    rules ran (0.0 when the pump is CLOSED). This commanded-vs-realized split is
    mandated by docs/PHASE6_ACTION_SPACE_SPEC.md §9.7 and §15 of the brief.
    """

    pressures_psi: Mapping[str, float]
    tank_levels_ft: Mapping[str, float]
    prev_cmd_prv_setpoint_psi: Mapping[str, float]
    prv_is_active: Mapping[str, bool]
    prev_cmd_pump_speed: Mapping[str, float]
    pump_realized_speed: Mapping[str, float]
    sim_time_s: float


def _affine01(x: float, lo: float, hi: float) -> float:
    """Map x from [lo, hi] to [0, 1], clipped. Deterministic, pure."""
    if hi == lo:
        return 0.0
    return min(1.0, max(0.0, (x - lo) / (hi - lo)))


def build_observation(config: ObservationConfig, raw: RawState) -> np.ndarray:
    """Assemble the fixed-length, normalized observation vector.

    Pure function: identical (config, raw) -> identical output. No RNG, no wall
    clock, no I/O. Missing actuator/node keys raise KeyError (fail loud) rather
    than silently defaulting.
    """
    vec = np.empty(config.dim, dtype=DTYPE)
    sl = config.slices()

    # [pressures] fixed physical band, clipped to [0, 1]
    p_lo, p_hi = config.p_min_psi, config.p_max_psi
    vec[sl["pressures"]] = [
        _affine01(float(raw.pressures_psi[n]), p_lo, p_hi)
        for n in config.service_nodes
    ]

    # [tank levels] per-tank physical [min, max] level from the INP
    vec[sl["tank_levels"]] = [
        _affine01(float(raw.tank_levels_ft[t]),
                  *config.tank_level_bounds_ft[t])
        for t in config.tank_ids
    ]

    # [prev commanded PRV setpoints] per-valve approved bounds
    vec[sl["prev_cmd_prv_setpoint"]] = [
        _affine01(float(raw.prev_cmd_prv_setpoint_psi[v]),
                  *config.prv_bounds_psi[v])
        for v in config.prv_ids
    ]

    # [PRV is_active] regulating flag (Active=1) else 0
    vec[sl["prv_is_active"]] = [
        1.0 if bool(raw.prv_is_active[v]) else 0.0 for v in config.prv_ids
    ]

    # [prev commanded pump speeds] per-pump [lower, 1.10]
    vec[sl["prev_cmd_pump_speed"]] = [
        _affine01(float(raw.prev_cmd_pump_speed[u]), *config.pump_bounds[u])
        for u in config.pump_ids
    ]

    # [pump realized speeds] realized / upper; 0.0 (closed) maps cleanly to 0
    vec[sl["pump_realized_speed"]] = [
        min(1.0, max(0.0, float(raw.pump_realized_speed[u])
                     / config.pump_bounds[u][1]))
        for u in config.pump_ids
    ]

    # [time of day] cyclical sin/cos, 24 h period (current time, never future)
    frac = (float(raw.sim_time_s) % config.day_seconds) / config.day_seconds
    ang = 2.0 * math.pi * frac
    vec[sl["time_of_day"]] = [math.sin(ang), math.cos(ang)]

    return vec


def observation_bounds(config: ObservationConfig) -> tuple[np.ndarray, np.ndarray]:
    """Per-dimension (low, high) arrays for a gymnasium Box (built in STEP 11).

    All blocks are normalized to [0, 1] except the cyclical time-of-day pair,
    which is in [-1, 1]. Returned as float32 arrays; gymnasium is NOT imported
    here so this module has no RL dependency.
    """
    low = np.zeros(config.dim, dtype=DTYPE)
    high = np.ones(config.dim, dtype=DTYPE)
    tod = config.slices()["time_of_day"]
    low[tod] = -1.0
    return low, high
