"""Baseline action-masking interfaces for the BWSN-1 comparison conditions.

The thesis compares adaptive control against reference operating modes. Each mode
differs ONLY in which of the 7 frozen actuators a controller is allowed to move;
the rest are PINNED to the native operating point. This module is the single,
pure place that defines those masks and projects a proposed normalised action
onto a mode -- it adds NO hydraulics and is deliberately NOT wired into
``bwsn_env.step`` (the environment's action semantics stay frozen; an experiment
harness composes this helper in front of ``step``).

    MODE          free actuators                      pinned to native
    native        (none)                              all 7  -> do-nothing reference
    prv_only      5 PRV setpoints  (idx 0..4)          2 pumps
    vsp_only      2 pump speeds    (idx 5..6)          5 PRVs
    joint         all 7                                (none) -> full action space

"native" is the do-nothing baseline whose trajectory already reproduces the
frozen anchors (see test_env_integration). "joint" is the unrestricted space the
PPO agent trains on. "prv_only" / "vsp_only" are the single-actuator-class
ablations. Masking is done in NORMALISED space against the native normalised
action, so a pinned component maps back to exactly its native physical value.

SCOPE (D-P6, not yet minted as a decision): this fixes the action-MASKING
interface for the four comparison conditions only. The evaluation PROTOCOL that
consumes them (metrics reported, demand scenario, train/eval split, seeds, which
conditions are run) is a separate Level-2 experiment-design decision that remains
open and requires researcher approval -- it is intentionally NOT encoded here.
"""

from __future__ import annotations

import numpy as np

import action_mapper as AM
import epanet_adapter as A

# Free-actuator index sets per mode (indices into the frozen 7-dim action).
_PRV_IDX = tuple(range(len(AM.ACTION_IDS) - 2))      # 0..4  (five PRV setpoints)
_PUMP_IDX = tuple(range(len(AM.ACTION_IDS) - 2, len(AM.ACTION_IDS)))  # 5..6

MODES: dict[str, tuple[int, ...]] = {
    "native": (),                       # nothing free: constant native hold
    "prv_only": _PRV_IDX,               # valves free, pumps native
    "vsp_only": _PUMP_IDX,              # pumps free, valves native
    "joint": tuple(range(len(AM.ACTION_IDS))),  # everything free
}


def native_action() -> np.ndarray:
    """The native operating point as a normalised action (float32 gym dtype)."""
    return AM.as_float32(
        AM.command_to_normalized(A.NATIVE_PRV_SETPOINT_PSI, A.NATIVE_PUMP_SPEED))


def free_mask(mode: str) -> np.ndarray:
    """Boolean mask (len 7): True where the mode lets a controller move the actuator."""
    if mode not in MODES:
        raise KeyError(f"unknown baseline mode {mode!r}; choose from {sorted(MODES)}")
    mask = np.zeros(len(AM.ACTION_IDS), dtype=bool)
    for i in MODES[mode]:
        mask[i] = True
    return mask


def apply_mask(proposed_norm: np.ndarray, mode: str) -> np.ndarray:
    """Project a proposed normalised action onto ``mode``.

    Free components are taken (clipped) from ``proposed_norm``; pinned components
    are overwritten with the native normalised value, so they map back to exactly
    the native physical setpoint/speed. Returns a float32 action in [-1, 1]^7.
    """
    a = AM.as_float32(proposed_norm)
    nat = native_action()
    mask = free_mask(mode)
    return np.where(mask, a, nat).astype(AM.DTYPE)
