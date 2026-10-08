"""BWSN-1 Phase-6 PPO environment (STEP 11): the gym-facing episode.

Ties the frozen pieces together into one 192-step episode over the 96 h BWSN-1
horizon:

    policy action a_t in [-1,1]^7
      -> safety.resolve_action  (D-P6-006 F1 admissibility: execute / hold / ref)
      -> driver.step            (epanet_adapter: EPANET-2.2 segmented re-solve)
      -> metrics.step_metrics   (frozen accounting law)
      -> reward.compute_reward  (D-P6-005 C-A_F1_balanced_dense)
      -> state_builder.build_observation (frozen 139-dim observation)

TIMING (state_builder docstring, D-P6-004): the observation returned for step t
is built from the hydraulic state AFTER the simulator advanced to t under the
EXECUTED action of t, whose normalized vector fills the "previous commanded"
blocks. ``reset`` returns the t=0 pre-action snapshot at the native operating
point. ``terminated`` is always False (no absorbing MDP state); the 96 h horizon
is a time limit, so ``truncated`` becomes True at the 192nd step.

DEPENDENCIES: gymnasium is an OPTIONAL import -- when it is absent the env still
runs (``reset``/``step`` return plain numpy), so the STAGE C/D correctness tests
need no RL stack. torch / stable-baselines3 are NOT imported here (they gate PPO
training, STAGE E, not the environment).

DEMAND SCENARIO (OPEN DECISION -- NOT frozen): this env runs the INP's NATIVE
(nominal) demand pattern, which is what reproduces every frozen anchor. The
proposal's "uncertain demand" is in scope, but the SPECIFIC stochastic demand
model (perturbation family, magnitude, train/eval split, seeding) is a Level 2-3
research decision that has not been minted as a D-P6 decision. It is therefore
left as an explicit injection point (``demand_scenarios`` is intentionally NOT
yet implemented) and surfaced to the researcher rather than improvised here
(CLAUDE.md s.19 scope discipline, s.21 no silent scientific change).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
_VALIDATION = _HERE.parent / "validation"
for _p in (str(_HERE), str(_VALIDATION)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import phase5_common as C  # noqa: E402
import p6_s3_prv_finechar as S3  # noqa: E402
import epanet_adapter as A  # noqa: E402
import action_mapper as AM  # noqa: E402
import metrics as MX  # noqa: E402
import reward as RW  # noqa: E402
import safety as SF  # noqa: E402
from state_builder import (  # noqa: E402
    ObservationConfig, RawState, build_observation, observation_bounds,
)

try:  # gymnasium is OPTIONAL (env core is RL-stack-free)
    import gymnasium as gym
    from gymnasium import spaces
    _HAS_GYM = True
    _BASE = gym.Env
except Exception:  # noqa: BLE001 - any import failure means "no gym installed"
    gym = None
    spaces = None
    _HAS_GYM = False
    _BASE = object

def make_observation_config(wn) -> ObservationConfig:
    """Build the frozen 139-dim observation config from the live working INP.

    Identical construction to ``p6_s7_state_spec.main`` (the STEP 7 evidence
    generator): service/connector split from ``S3.service_nodes``, per-tank level
    band from the INP's ``min_level``/``max_level`` (ft). Single source of truth,
    so the env's observation can never disagree with the frozen state spec.
    """
    svc, conn = S3.service_nodes(wn)
    tank_bounds = {
        t: (float(C.m_to_ft(wn.get_node(t).min_level)),
            float(C.m_to_ft(wn.get_node(t).max_level)))
        for t in wn.tank_name_list
    }
    return ObservationConfig(
        service_nodes=tuple(svc), connector_nodes=tuple(conn),
        tank_ids=tuple(wn.tank_name_list), tank_level_bounds_ft=tank_bounds,
    )


class BWSNPressureControlEnv(_BASE):
    """One PPO episode: 192 control steps of adaptive PRV/pump pressure control.

    Parameters
    ----------
    reward_config : RW.RewardConfig, optional
        Weights + normalisers; defaults to the frozen D-P6-005 C-A_F1 values.
    safety_config : SF.SafetyConfig, optional
        F1 admissibility parameters; defaults to the frozen D-P6-006 values
        (eps_p = 0 psi, H = 1 control step).
    enable_safety : bool, default True
        When False the proposed action is executed verbatim (no admissibility
        layer). Used by the STAGE-F clean baselines and by native-equivalence
        tests that must exercise pure hydraulics.
    """

    metadata = {"render_modes": []}

    def __init__(self, reward_config: RW.RewardConfig | None = None,
                 safety_config: SF.SafetyConfig | None = None,
                 enable_safety: bool = True):
        if _HAS_GYM:
            super().__init__()
        self._wn0 = S3.build(None, None)
        self._svc, self._conn = S3.service_nodes(self._wn0)
        self._coeff = A.default_leak_coefficients()
        self._driver = A.SteppingHydraulicDriver(A.DriverConfig(
            coeff_us=self._coeff, service_nodes=self._svc,
            connector_nodes=self._conn,
            n_native_controls=len(self._wn0.control_name_list)))
        self._obs_cfg = make_observation_config(self._wn0)
        self._reward_cfg = reward_config or RW.RewardConfig()
        self._safety_cfg = safety_config or SF.SafetyConfig()
        self._enable_safety = bool(enable_safety)
        self._native_norm = AM.command_to_normalized(
            A.NATIVE_PRV_SETPOINT_PSI, A.NATIVE_PUMP_SPEED)
        self._prev_exec_norm = self._native_norm.copy()
        self._k = 0
        self._low, self._high = observation_bounds(self._obs_cfg)
        if _HAS_GYM:
            self.observation_space = spaces.Box(self._low, self._high, dtype=np.float32)
            self.action_space = spaces.Box(
                low=-1.0, high=1.0, shape=(AM.ACTION_DIM,), dtype=np.float32)

    # -- observation assembly -------------------------------------------------
    def _observation(self, sr, prev_exec_norm: np.ndarray) -> np.ndarray:
        """Build the frozen observation from a StepResult + the EXECUTED command.

        The "previous commanded" blocks hold the EXECUTED action that advanced the
        sim to ``sr`` (post-safety), per the A2 "commanded == executed" resolution.
        PRV is_active and realized pump speed come from the solved state.
        """
        prv_cmd, pump_cmd = AM.to_command(prev_exec_norm)
        raw = RawState(
            pressures_psi=sr.pressures_psi,
            tank_levels_ft=sr.tank_levels_ft,
            prev_cmd_prv_setpoint_psi=prv_cmd,
            prv_is_active=sr.prv_is_active,
            prev_cmd_pump_speed=pump_cmd,
            pump_realized_speed=sr.pump_realized_speed,
            sim_time_s=sr.sim_time_s,
        )
        return build_observation(self._obs_cfg, raw)

    # -- gym API --------------------------------------------------------------
    def reset(self, *, seed=None, options=None):
        """Return (obs, info) at the t=0 native pre-action snapshot."""
        if _HAS_GYM:
            super().reset(seed=seed)
        sr0 = self._driver.reset()
        self._prev_exec_norm = self._native_norm.copy()
        self._k = 0
        obs = self._observation(sr0, self._prev_exec_norm)
        info = {"sim_time_s": sr0.sim_time_s, "step_index": sr0.step_index,
                "n_steps": self._driver.cfg.n_steps}
        return obs, info

    def step(self, action):
        """Apply one action: resolve admissibility, advance, reward, observe."""
        a = AM.as_float32(action)
        prev_exec_norm = self._prev_exec_norm.copy()   # chronology baseline (pre-update)
        if self._enable_safety:
            dec = SF.resolve_action(
                self._driver, a, self._prev_exec_norm,
                A.NATIVE_PRV_SETPOINT_PSI, A.NATIVE_PUMP_SPEED, self._safety_cfg)
            exec_prv, exec_pump, outcome = dec.executed_prv, dec.executed_pump, dec.outcome
        else:
            exec_prv, exec_pump = AM.to_command(a)
            outcome = "no_safety"
            dec = None
        sr = self._driver.step(exec_prv, exec_pump)
        exec_norm = AM.command_to_normalized(exec_prv, exec_pump)
        da = exec_norm - prev_exec_norm              # D-P6-005: EXECUTED delta (unchanged)
        m = MX.step_metrics(sr, self._coeff, self._svc)
        rb = RW.compute_reward(m, da, self._reward_cfg)

        self._prev_exec_norm = exec_norm
        self._k += 1
        truncated = bool(self._driver.done)
        terminated = False
        obs = self._observation(sr, exec_norm)
        info = {
            "outcome": outcome,
            "safety": dec,
            "reward_breakdown": rb,
            "metrics": m,
            # Phase-4 traceability (OBSERVABILITY ONLY -- these keys do not feed
            # the observation, action, safety decision, or reward mathematics):
            "proposed_action_norm": a,                 # what the policy emitted
            "executed_action_norm": exec_norm,         # what the actuator received (post-safety)
            "prev_executed_action_norm": prev_exec_norm,  # movement baseline a_exec_{t-1}
            "sim_time_s": sr.sim_time_s,
            "step_index": sr.step_index,
        }
        return obs, rb.total, terminated, truncated, info

    @property
    def observation_config(self) -> ObservationConfig:
        return self._obs_cfg

    @property
    def coeff_us(self) -> dict:
        return self._coeff
