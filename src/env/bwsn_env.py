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

DEMAND SCENARIO (STEP 10 / D-P6-007, IMPLEMENTED): by default this env runs
the INP's NATIVE (nominal) demand pattern, which is what reproduces every
frozen anchor. ``demand_scenario=`` selects the STEP-10 demand-uncertainty
mode (researcher selections of 2026-10-19, recorded in
``docs/PHASE6_DECISION_REGISTER.md`` D-P6-007): "train" draws a NEW U1+S1
truncated-normal global multiplier from a reproducible stream at every
reset; "val/<i>" / "test/<i>" / "ood/<i>" install the FIXED, reproducible
evaluation scenarios (S2 per-junction factors for ood, resolved against
this INP's demand-junction list); a ``DemandScenario`` instance is installed
verbatim. The perturbation reaches BOTH the segment solves and the
full-horizon requested-demand accounting (driver-level, see
``epanet_adapter``); the frozen 139-dim observation, 7-dim action, reward
and safety layers are untouched, and scenario identity rides in ``info``
only -- never in the observation vector.
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
import demand_scenarios as DS  # noqa: E402
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
    demand_scenario : str | DemandScenario, default "native"
        STEP-10 (D-P6-007) episode demand mode. "native" keeps the frozen
        nominal path (default, so pre-STEP-10 callers and every frozen anchor
        are unchanged). "train" draws a NEW U1+S1 truncated-normal multiplier
        from ``TrainingScenarioStream`` at every ``reset`` (reseeding with the
        same seed reproduces the same sequence). "val/<i>", "test/<i>",
        "ood/<i>" install the FIXED evaluation scenarios. A
        ``DemandScenario`` instance is installed verbatim.
    scenario_config : DS.ScenarioConfig, optional
        Master seed + truncated-normal parameters; defaults to the frozen
        D-P6-007 selection (master seed 20261019, mu 1.0, sigma 0.1,
        [0.7, 1.3]).
    """

    metadata = {"render_modes": []}

    def __init__(self, reward_config: RW.RewardConfig | None = None,
                 safety_config: SF.SafetyConfig | None = None,
                 enable_safety: bool = True,
                 demand_scenario="native",
                 scenario_config: DS.ScenarioConfig | None = None):
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
        # STEP-10 demand-uncertainty mode (D-P6-007). Resolved once here; the
        # S2 (ood) fixed scenarios need this INP's demand-junction list.
        self._scenario_config = (scenario_config if scenario_config is not None
                                 else DS.DEFAULT_CONFIG)
        self._demand_junctions = DS.demand_junctions(self._wn0)
        self._scenario = None            # active scenario, set in reset()
        self._seed_provenance = None     # F6: set in reset(), read by step()
        self._install_mode(demand_scenario)
        if _HAS_GYM:
            self.observation_space = spaces.Box(self._low, self._high, dtype=np.float32)
            self.action_space = spaces.Box(
                low=-1.0, high=1.0, shape=(AM.ACTION_DIM,), dtype=np.float32)

    # -- scenario mode management (STEP-10 D5) -------------------------------
    def _install_mode(self, demand_scenario) -> None:
        """Resolve a scenario-mode selection onto this env (before any reset).

        Accepts "native", "train", "<group>/<index>", or a DemandScenario
        instance. "train" arms the per-episode stream; every fixed selection is
        resolved in ``reset`` from its identifier (deterministic). Validated
        EAGERLY (including one probe resolution of a fixed id) so a typo fails
        at construction, not 200 steps into an evaluation.
        """
        if isinstance(demand_scenario, DS.DemandScenario):
            self._demand_mode = demand_scenario
            self._scenario_stream = None
            return
        mode = str(demand_scenario)
        if mode == "train":
            self._demand_mode = mode
            self._scenario_stream = DS.TrainingScenarioStream(self._scenario_config)
            return
        # Eager validation: resolve the identifier once against this INP.
        DS.fixed_scenario(mode, config=self._scenario_config,
                          demand_junctions_list=self._demand_junctions)
        self._demand_mode = mode
        self._scenario_stream = None

    def set_demand_scenario(self, scenario) -> None:
        """Switch the scenario mode AFTER construction (paired evaluation).

        A wrapper/harness may re-parameterise the env between episodes (e.g.
        the STEP-10 D5 paired evaluator iterates the fixed scenario IDs). The
        change takes effect at the NEXT ``reset``; resetting mid-episode is
        fine (the driver re-stamps its scenario of record at every reset).
        """
        self._install_mode(scenario)

    @property
    def demand_scenario(self) -> DS.DemandScenario:
        """Active episode scenario (None before the first reset)."""
        return self._scenario

    @property
    def scenario_config(self) -> DS.ScenarioConfig:
        return self._scenario_config

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
        """Return (obs, info) at the t=0 native pre-action snapshot.

        STEP-10: the active demand scenario is selected and installed on the
        driver BEFORE ``driver.reset()`` so the t=0 segment AND the
        full-horizon requested-demand accounting both see it. In "train" mode a
        NEW multiplier is drawn from the reproducible stream every reset; an
        explicit ``seed`` reseeds that stream (gym contract: same seed ->
        same scenario sequence). In fixed mode the scenario is resolved from
        its identifier, so every reset of the same ID is the SAME scenario.
        Scenario metadata rides in ``info["demand_scenario"]`` only.
        """
        if _HAS_GYM:
            super().reset(seed=seed)
        if self._scenario_stream is not None:          # "train" mode
            if seed is not None:
                self._scenario_stream.reseed(int(seed))
            self._scenario = self._scenario_stream.next()
        elif isinstance(self._demand_mode, DS.DemandScenario):
            self._scenario = self._demand_mode         # fixed instance, verbatim
        else:                                          # fixed identifier: re-resolved
            self._scenario = DS.fixed_scenario(        # (deterministic) each reset
                self._demand_mode, config=self._scenario_config,
                demand_junctions_list=self._demand_junctions)
        self._driver.scenario = self._scenario
        sr0 = self._driver.reset()
        self._prev_exec_norm = self._native_norm.copy()
        self._k = 0
        obs = self._observation(sr0, self._prev_exec_norm)
        info = {"sim_time_s": sr0.sim_time_s, "step_index": sr0.step_index,
                "n_steps": self._driver.cfg.n_steps,
                "demand_scenario": self._scenario.to_dict()}
        # Seed provenance (OBSERVABILITY ONLY; changes nothing random). Records
        # only values that ARE available at runtime, without conflating them:
        #   train  -> the stream RNG is seeded by ``reset(seed=...)`` when given,
        #             else by ``scenario_master_seed``; ``draw_index`` is the
        #             stream's own counter for THIS episode.
        #   fixed  -> the scenario is a pure function of
        #             ``SeedSequence(entropy=scenario_master_seed,
        #             spawn_key=(group_key, index))``; ``reset(seed=...)`` seeds
        #             the gym RNG only and does NOT affect the scenario, so it is
        #             recorded as ``reset_seed_arg_gym_only`` to prevent it being
        #             misread as the scenario's seed.
        prov = {"master_seed": int(self._scenario_config.master_seed),
                "reset_seed_arg": None if seed is None else int(seed)}
        if self._scenario_stream is not None:
            prov["mode"] = "train"
            prov["effective_stream_seed"] = (
                int(seed) if seed is not None
                else int(self._scenario_config.master_seed))
            prov["draw_index"] = getattr(self._scenario, "draw_index", None)
        else:
            prov["mode"] = "fixed"
            prov["scenario_id"] = self._scenario.to_dict()["scenario_id"]
            prov["master_seed_role"] = "SeedSequence entropy"
            prov["reset_seed_arg_gym_only"] = prov.pop("reset_seed_arg")
        info["scenario_seed_provenance"] = prov
        self._seed_provenance = prov
        return obs, info

    @property
    def seed_provenance(self) -> dict | None:
        """Seed-provenance dict for the CURRENT episode (None before reset)."""
        return getattr(self, "_seed_provenance", None)

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

        # Endpoint service-pressure diagnostics (OBSERVABILITY ONLY -- not reward
        # inputs). Same 121-service-node set and the same <0 / min conventions the
        # frozen Phase-5/6 anchors use (min_service_pressure_psi 4.16452169418335,
        # n_service_nodes_negative 0), so no new metric definition is introduced.
        _p_svc = [sr.pressures_psi[j] for j in self._svc]
        min_service_pressure_psi = float(min(_p_svc))
        n_service_nodes_negative = int(sum(1 for v in _p_svc if v < 0.0))

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
            "min_service_pressure_psi": min_service_pressure_psi,
            "n_service_nodes_negative": n_service_nodes_negative,
            "sim_time_s": sr.sim_time_s,
            "step_index": sr.step_index,
            # STEP-10: the episode's scenario identity (constant within the
            # episode by construction; OBSERVABILITY ONLY).
            "demand_scenario": self._scenario.to_dict(),
            # F6: seed provenance stamped at reset(); carried forward per step
            # so evaluators can record it without re-deriving.
            "scenario_seed_provenance": self._seed_provenance,
        }
        return obs, rb.total, terminated, truncated, info

    @property
    def observation_config(self) -> ObservationConfig:
        return self._obs_cfg

    @property
    def coeff_us(self) -> dict:
        return self._coeff
