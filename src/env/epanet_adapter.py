"""Step-by-step EPANET hydraulic driver for the Phase-6 DRL environment.

This module advances a BWSN-1 EPANET simulation one *control step* (1800 s) at a
time, carrying the physical state forward between steps so that a reinforcement-
learning agent can issue a fresh 7-dim command (5 PRV setpoints + 2 pump speeds)
at every step. It is pure hydraulics: no reward, no action normalisation, no gym
dependency. Those live in sibling modules.

PROVENANCE / VALIDATION
-----------------------
The segmented re-solve loop used here is the SAME mechanism measured in
``p6_s4_pump_strategy.run_stepped``. Its ``mechanism_check_stepped_native`` case
(segmented 30-min loop at native settings) reproduced the monolithic 96-h EPS
(``ref_native_speed_1.0``):

  * n_node_timesteps_below_20psi : 386  vs 386   (EXACT)
  * n_node_timesteps_negative    :   0  vs   0   (EXACT)
  * argmin_service_node          : JUNCTION-29 vs JUNCTION-29 (EXACT)
  * leakage_mean_gpm             : 84.73052 vs 84.72988 (rel 7.5e-6)
  * min_service_pressure_psi     : 4.16397 vs 4.16452 (|Δ| 5.5e-4 psi)

i.e. the stepped loop equals the monolithic reference to within the EPANET
ACCURACY=1e-5 floor on continuous metrics and EXACTLY on the discrete anchors.
``run_stepped`` exercised only PUMP commands at native PRV setpoints; this module
GENERALISES the loop to also command the five PRV setpoints each step. That
extension was re-validated by a static-command rollout (all five PRVs at their
UPPER bounds, pumps at 1.0) solved both monolithically (single 96 h EPS) and
through this driver. Over the 192 POST-ACTION control-step endpoints the two
agree to the same solver floor:

  * n_node_timesteps_below_20psi : 192 vs 192 (EXACT)
  * n_node_timesteps_negative    :   0 vs   0 (EXACT)
  * argmin_service_node          : JUNCTION-29 vs JUNCTION-29 (EXACT)
  * leakage_mean_gpm             : rel 5.1e-6
  * min_service_pressure_psi     : |Δ| 7.9e-4 psi

The t=0 reset instant is EXCLUDED from this comparison by construction: ``reset``
reports the PRE-ACTION state at the NATIVE operating point (correct RL semantics),
which has no counterpart in a monolithic EPS that applies the test command from
t=0. Episode reward/accounting consume only the post-action endpoints, so this
exclusion is exactly the validated window. The check is enshrined under tests.


ENGINE COMPARABILITY (why WNTR, not epyt)
-----------------------------------------
Every frozen Phase-5/6 anchor was produced by WNTR 1.5.0's EpanetSimulator, which
runs EPANET engine version 2.2. The installed ``epyt`` bundles EPANET 2.3.5
(getVersion -> 20305), a DIFFERENT solver whose results would not be comparable to
the frozen anchors without re-freezing them. This driver therefore stays on the
WNTR/2.2 path via the mandated ``p6_s3_prv_finechar.build`` loader.

The carried state is {tank levels, pump statuses, pattern phase}; this set was
proven SUFFICIENT by the native mechanism check above. PRV Active/Open/Closed
status is solver-determined from the setpoint and surrounding heads each step and
is NOT carried (matching ``p6_s8_reward_scale_analysis.run_config``, which sets
only ``initial_setting`` for PRVs).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
_VALIDATION = _HERE.parent / "validation"
for _p in (str(_HERE), str(_VALIDATION)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import phase5_common as C  # noqa: E402
import g6_g7_g8_leak_pda as L  # noqa: E402
import p6_s3_prv_finechar as S3  # noqa: E402
import state_builder as SB  # noqa: E402
import demand_scenarios as DS  # noqa: E402

from wntr.network.base import LinkStatus  # noqa: E402
import wntr as _wntr  # noqa: E402

# --- control / horizon geometry (frozen) --------------------------------------
CONTROL_STEP_S = 1800            # DRL control interval (D-P6 brief s.10)
HORIZON_S = 96 * 3600            # BWSN-1 benchmark horizon
RULE_TIMESTEP_S = S3.RULE_TIMESTEP_S   # 180 s native-rule / intra-step cadence
N_CONTROL_STEPS = HORIZON_S // CONTROL_STEP_S     # 192
SERVICE_PSI = 20.0               # PDA/service threshold (frozen)

PRV_IDS = list(SB.PRV_IDS)
PUMP_IDS = list(SB.PUMP_IDS)

def default_leak_coefficients(prefix: str = "p6_env_size") -> dict[str, float]:
    """Reproduce the frozen leak field (10% of mean inflow, one closed-form step).

    Identical sizing to ``p6_s4_pump_strategy.main`` /
    ``p6_s8_reward_scale_analysis``: baseline pressures -> half-length weights ->
    emitter coefficients. Computed once over the full horizon so the leak field is
    a deterministic property of the network, not of how the solve was segmented.
    """
    base_p, base_inflow, weights = L.baseline_pressures(prefix)
    sizing = L.leak_coefficients(weights, base_p, L.LEAK_TARGET_FRACTION * base_inflow)
    return dict(sizing["coefficient_gpm_per_psi_alpha"])


@dataclass
class DriverConfig:
    """Static configuration for one episode's hydraulic rollout."""
    coeff_us: dict[str, float]                 # leak coefficients (full-horizon)
    service_nodes: list[str]                   # 121 service-bearing junctions
    connector_nodes: list[str]                 # 5 connector artefacts (excluded)
    control_step_s: int = CONTROL_STEP_S
    horizon_s: int = HORIZON_S
    rule_timestep_s: int = RULE_TIMESTEP_S
    n_native_controls: int | None = None       # asserted each step if provided

    @property
    def n_steps(self) -> int:
        return self.horizon_s // self.control_step_s


@dataclass
class StepResult:
    """Raw end-of-control-step hydraulic state plus the intra-step trace.

    All pressures/heads in psi/ft, flows in GPM, speeds dimensionless. The reward,
    observation and safety layers consume these fields; this struct intentionally
    carries no derived RL quantities.
    """
    step_index: int                            # 0-based control step just solved
    sim_time_s: float                          # ABSOLUTE clock at the step endpoint
    pressures_psi: dict[str, float]            # endpoint, every junction
    tank_levels_ft: dict[str, float]           # endpoint tank water level (head-elev)
    pump_realized_speed: dict[str, float]      # endpoint realized speed (0 = Closed)
    pump_status: dict[str, int]                # endpoint pump status code
    pump_power_kw: dict[str, float]            # endpoint pump hydraulic power
    prv_realized_setting_psi: dict[str, float] # endpoint PRV setting
    prv_is_active: dict[str, bool]             # endpoint PRV status == Active
    demand_gpm: dict[str, float]               # endpoint reported nodal demand
    requested_gpm: dict[str, float]            # endpoint requested demand (full-horizon)
    # intra-step trace at the 180 s rule cadence (safety / rule-firing diagnostics)
    intra_hours: list[float] = field(default_factory=list)
    intra_p_min_psi: list[float] = field(default_factory=list)
    intra_n_neg: list[int] = field(default_factory=list)
    wntr_warnings: list = field(default_factory=list)

NATIVE_PRV_SETPOINT_PSI = {v: float(S3.NOMINAL_PSI[v]) for v in PRV_IDS}
NATIVE_PUMP_SPEED = {p: 1.0 for p in PUMP_IDS}   # file declares pumps Open @ 1.0


def _pump_power_kw(wn, res) -> dict[str, float]:
    """Per-pump endpoint hydraulic power (kW), reusing R8's exact formula.

    P = rho*g*Q*dH clipped at 0; dH = head(end) - head(start). HYDRAULIC proxy,
    no efficiency curve. Matches p6_s8_reward_scale_analysis.pump_hydraulic_power_kw.
    """
    flow = res.link["flowrate"]
    head = res.node["head"]
    out = {}
    for p in PUMP_IDS:
        link = wn.get_link(p)
        q = float(flow[p].iloc[-1])
        dh = float(head[link.end_node_name].iloc[-1] - head[link.start_node_name].iloc[-1])
        out[p] = max(1000.0 * 9.81 * q * dh, 0.0) / 1000.0
    return out


class SteppingHydraulicDriver:
    """Advance a BWSN-1 EPANET EPS one control step at a time, carrying state.

    Usage:
        drv = SteppingHydraulicDriver(DriverConfig(coeff_us=..., service_nodes=...))
        s0 = drv.reset()                          # t = 0 snapshot, native settings
        s1 = drv.step(prv_setpoints_psi, pump_speeds)   # applies action, advances 1800 s
        ...
    The driver NEVER mutates the distributed INP; every segment reloads the
    single-quality-patch working copy via ``p6_s3_prv_finechar.build``.
    """

    def __init__(self, config: DriverConfig):
        self.cfg = config
        self._svc = list(config.service_nodes)
        self._t_elapsed = 0
        self._step_index = -1
        self._tank_levels_m: dict[str, float] = {}
        self._pump_status: dict[str, LinkStatus] = {}
        self._req_gpm = None          # full-horizon requested-demand series (DataFrame)
        self._done = False
        # STEP-10 (D-P6-007): episode-level demand scenario. Defaults to the
        # native (identity) scenario so an unset scenario leaves the frozen
        # anchor path byte-identical; the env installs the active scenario on
        # this attribute BEFORE calling reset(). apply() reaches BOTH paths:
        # every segment model built by _build_segment (step/probe/reset t=0)
        # and the full-horizon accounting model in reset().
        self._scenario: DS.DemandScenario = DS.NativeScenario()
        self._episode_scenario: DS.DemandScenario | None = None

    @property
    def scenario(self) -> DS.DemandScenario:
        """Active demand scenario (NativeScenario when unset)."""
        return self._scenario

    @scenario.setter
    def scenario(self, scenario: DS.DemandScenario) -> None:
        if not isinstance(scenario, DS.DemandScenario):
            raise TypeError(
                f"scenario must be a DemandScenario, got {type(scenario).__name__}")
        self._scenario = scenario
        self._scenario = scenario

    # -- segment construction -------------------------------------------------
    def _build_segment(self, duration_s: int, pattern_start_s: int):
        """Fresh working-copy load configured for one segment, state restored.

        The active demand scenario is applied AFTER ``S3.build`` and BEFORE the
        tank/pump restore, so every segment solve (step, probe, and reset's t=0
        segment) sees the episode's perturbed demands while the native demand
        pattern, its phase, PDA options and solver settings stay untouched.
        """
        wn = S3.build(None, None)                       # solver + PDA policy
        self._scenario.apply(wn)                        # STEP-10 demand perturbation
        wn.options.time.duration = int(duration_s)
        wn.options.time.report_timestep = int(self.cfg.rule_timestep_s)
        wn.options.time.pattern_start = int(pattern_start_s)
        for t, lvl_m in self._tank_levels_m.items():
            wn.get_node(t).init_level = float(lvl_m)
        for p, stt in self._pump_status.items():
            wn.get_link(p).initial_status = stt
        if self.cfg.n_native_controls is not None:
            assert len(wn.control_name_list) == self.cfg.n_native_controls, (
                len(wn.control_name_list), self.cfg.n_native_controls)
        return wn

    def _apply_command(self, wn, prv_setpoints_psi: dict, pump_speeds: dict) -> None:
        """Issue the 7-dim command onto a freshly built segment model.

        PRVs: set ``initial_setting`` (the setpoint persists; status is solver-
        determined). Pumps: set ``base_speed`` (re-issued EVERY step, so a native
        rule's STATUS-IS-OPEN reset of speed can persist for at most one step --
        the G12 defect, bounded by re-issuance). Leak field applied last.
        """
        for v in PRV_IDS:
            wn.get_link(v).initial_setting = float(C.psi_to_m(prv_setpoints_psi[v]))
        for p in PUMP_IDS:
            wn.get_link(p).base_speed = float(pump_speeds[p])
        L.apply_leak(wn, self.cfg.coeff_us)
        S3.assert_solver(wn, report_timestep_s=self.cfg.rule_timestep_s)

    # -- F3 solve-validation (raise BEFORE any state commits) -------------------
    def _validate_solve(self, wn, res, *, expected_index: int,
                        expected_timestep_s: int, context: str) -> None:
        """Refuse an incomplete/invalid EPANET result before it touches state.

        A solve is unusable when the binary report is missing rows/columns or
        holds non-finite endpoints: propagating it would corrupt the observation,
        the reward, and (worse) the carried tank/pump state that the next
        segment depends on. This raises a descriptive error so ``step``/``reset``
        /``probe`` abort BEFORE any driver state mutates -- a numerical failure
        is reported as such, never converted into a reward or an action outcome.
        """
        link = getattr(res, "link", None)
        node = getattr(res, "node", None)
        if node is None or link is None:
            raise RuntimeError(
                f"{context}: EPANET result missing node/link blocks "
                f"(got node={type(node).__name__}, link={type(link).__name__})")
        status = link.get("status")
        setting = link.get("setting")
        flow = link.get("flowrate")
        pressure = node.get("pressure")
        head = node.get("head")
        missing = [k for k, v in (("link.status", status), ("link.setting", setting),
                                ("link.flowrate", flow), ("node.pressure", pressure),
                                ("node.head", head)) if v is None]
        if missing:
            raise RuntimeError(f"{context}: EPANET result missing {missing}")
        # Every controlled actuator must appear as a column; every demand
        # junction must appear in pressure/head.
        for col in ("status", "setting", "flowrate"):
            df = link[col]
            absent = [a for a in list(PUMP_IDS) + list(PRV_IDS)
                      if a not in df.columns]
            if absent:
                raise RuntimeError(
                    f"{context}: link.{col} missing actuator columns {absent}")
        for col in ("pressure", "head", "demand"):
            df = node.get(col)
            if df is None:
                raise RuntimeError(f"{context}: EPANET result missing node.{col}")
            absent = [j for j in wn.junction_name_list if j not in df.columns]
            if absent:
                raise RuntimeError(
                    f"{context}: node.{col} missing junction columns "
                    f"{absent[:5]}{'...' if len(absent) > 5 else ''}")
        # EPANET returns exactly (expected_index + 1) report instants: the
        # segment start (pattern_start) plus one instant per rule timestep.
        # Fewer means the solve ended early / was truncated; more means an
        # unexpected sub-step -- both are unusable for the frozen extraction.
        n_expected = expected_index + 1
        got = len(status.index)
        if got != n_expected:
            raise RuntimeError(
                f"{context}: EPANET returned {got} report instants; expected "
                f"{n_expected} (segment start + {expected_index} rule steps)")
        times = np.asarray(status.index, dtype=float)
        expected_times = np.arange(n_expected, dtype=float) * float(expected_timestep_s)
        if (not np.all(np.isfinite(times))
                or not np.allclose(times, expected_times, rtol=0.0, atol=1e-6)):
            raise RuntimeError(
                f"{context}: invalid report time grid {times.tolist()} expected "
                f"{expected_times.tolist()}")
        if not np.all(np.isfinite(pressure[wn.junction_name_list].to_numpy(dtype=float))):
            raise RuntimeError(
                f"{context}: non-finite service pressure trace")
        # Endpoint finiteness over the quantities the env actually consumes.
        checks = (("link.status", status, list(PRV_IDS) + list(PUMP_IDS)),
                  ("link.setting", setting, list(PRV_IDS) + list(PUMP_IDS)),
                  ("link.flowrate", flow, list(PRV_IDS) + list(PUMP_IDS)),
                  ("node.pressure", pressure, wn.junction_name_list),
                  ("node.demand", node["demand"], wn.junction_name_list),
                  ("node.head", head, wn.tank_name_list))
        for name, df, cols in checks:
            vals = df[cols].iloc[-1].to_numpy(dtype=float)
            if not np.all(np.isfinite(vals)):
                bad = [c for c, v in zip(cols, vals) if not np.isfinite(v)]
                raise RuntimeError(
                    f"{context}: non-finite endpoint in {name} for {bad[:5]}")

    def _extract(self, wn, res, step_index: int, sim_time_s: float,
                 row: int) -> StepResult:
        """Build a StepResult from one solved segment; `row` selects the instant."""
        p_psi = C.m_to_psi(res.node["pressure"])
        head = res.node["head"]
        status = res.link["status"]
        setting = res.link["setting"]
        junc = wn.junction_name_list

        # intra-step trace at the rule cadence over the whole segment
        svc = self._svc
        p_svc = p_psi[svc]
        local_idx = list(p_psi.index)
        rows = range(len(local_idx)) if step_index >= 0 else [0]
        intra_hours = [float((sim_time_s - (local_idx[-1] - local_idx[i])) / 3600.0)
                       for i in rows]
        intra_pmin = [float(p_svc.iloc[i].min()) for i in rows]
        intra_nneg = [int((p_svc.iloc[i] < 0.0).sum()) for i in rows]

        req_row = self._req_gpm.loc[int(sim_time_s)] if self._req_gpm is not None else None
        return StepResult(
            step_index=step_index,
            sim_time_s=float(sim_time_s),
            pressures_psi={j: float(p_psi[j].iloc[row]) for j in junc},
            tank_levels_ft={t: float(C.m_to_ft(head[t].iloc[row] - wn.get_node(t).elevation))
                            for t in wn.tank_name_list},
            # Realized speed = setting only while the link is Open; a Closed pump
            # retains its last setting in the result file but moves no water, so
            # the observation contract reports 0.0 (D-P6-004 "0 = closed").
            pump_realized_speed={p: (0.0 if int(status[p].iloc[row]) == int(LinkStatus.Closed)
                                     else float(setting[p].iloc[row]))
                                 for p in PUMP_IDS},
            pump_status={p: int(status[p].iloc[row]) for p in PUMP_IDS},
            pump_power_kw=_pump_power_kw(wn, res),
            prv_realized_setting_psi={v: float(C.m_to_psi(setting[v].iloc[row])) for v in PRV_IDS},
            prv_is_active={v: int(status[v].iloc[row]) == int(LinkStatus.Active) for v in PRV_IDS},
            demand_gpm={j: float(C.m3s_to_gpm(res.node["demand"][j]).iloc[row]) for j in junc},
            requested_gpm=({j: float(req_row[j]) for j in junc} if req_row is not None else {}),
            intra_hours=intra_hours,
            intra_p_min_psi=intra_pmin,
            intra_n_neg=intra_nneg,
        )

    def _state_snapshot(self) -> tuple:
        """Snapshot every mutable driver field a failed transition must preserve."""
        return (self._step_index, self._t_elapsed, dict(self._tank_levels_m),
                dict(self._pump_status), self._done, self._req_gpm,
                self._scenario, self._episode_scenario)

    def _state_restore(self, snapshot: tuple) -> None:
        (self._step_index, self._t_elapsed, self._tank_levels_m,
         self._pump_status, self._done, self._req_gpm,
         self._scenario, self._episode_scenario) = snapshot

    def reset(self) -> StepResult:
        """Reset transactionally: any failure restores the prior driver state."""
        snapshot = self._state_snapshot()
        try:
            return self._reset_impl()
        except Exception:
            self._state_restore(snapshot)
            raise

    def _reset_impl(self) -> StepResult:
        """Initialise carried state from the INP and return the t=0 snapshot.

        prev-executed command at t=0 is the NATIVE operating point (PRV nominal
        setpoints, pump speed 1.0). The requested-demand series is computed ONCE
        over the full horizon on the pattern_start=0 model (the same quantity
        the monolithic accounting uses), so DSR/unserved figures stay comparable.
        """
        self._episode_scenario = self._scenario
        base = S3.build(None, None)
        self._tank_levels_m = {t: float(base.get_node(t).init_level)
                               for t in base.tank_name_list}
        self._pump_status = {p: base.get_link(p).initial_status for p in PUMP_IDS}
        self._t_elapsed = 0
        self._step_index = -1
        self._done = False

        wn_full = S3.build(None, None)
        self._scenario.apply(wn_full)      # DSR/unserved accounting sees the SAME
        # perturbation as the segment solves (STEP-10 consistency requirement)
        wn_full.options.time.report_timestep = self.cfg.control_step_s
        req = C.m3s_to_gpm(_wntr.metrics.expected_demand(wn_full))
        req.index = [int(i) for i in req.index]
        self._req_gpm = req

        wn = self._build_segment(self.cfg.rule_timestep_s, 0)
        self._apply_command(wn, NATIVE_PRV_SETPOINT_PSI, NATIVE_PUMP_SPEED)
        res, msgs, _ = L._run_with_retry(wn, "p6_env_reset")
        self._validate_solve(wn, res, expected_index=1,
                             expected_timestep_s=self.cfg.rule_timestep_s,
                             context="reset")
        out = self._extract(wn, res, step_index=-1, sim_time_s=0.0, row=0)
        out.wntr_warnings = msgs
        return out

    def step(self, prv_setpoints_psi: dict, pump_speeds: dict) -> StepResult:
        """Apply one 7-dim command and advance the EPS by one control step.

        Returns the realised hydraulic state at the control-step ENDPOINT (the
        instant whose quantities feed D-P6-005's per-step reward and D-P6-004's
        observation), plus the 180 s intra-step trace used by the safety layer and
        for G12 pump-reset diagnostics. Carries tank levels and pump statuses to
        the next step; advances the pattern phase by the control step. Refuses to
        run if the demand scenario was swapped after this episode's ``reset``
        (STEP-10 consistency guard).
        """
        if self._done:
            raise RuntimeError("episode finished; call reset() before stepping")
        if (getattr(self, "_episode_scenario", None) is not None
                and self._scenario is not self._episode_scenario):
            raise RuntimeError(
                "demand scenario changed after reset(): episode segments and "
                "requested-demand accounting would become inconsistent; reset() "
                "the episode under the new scenario instead")
        # F3: build/solve/validate/extract/carry into TEMPORARIES first; commit
        # atomically at the end. Any failure (solve, retry-read, validation,
        # extraction, carry-state build) leaves every driver field untouched, so
        # a numerical failure can never become a transition, reward, observation.
        snapshot = self._state_snapshot()
        try:
            k = self._step_index + 1
            pattern_start = self._t_elapsed
            wn = self._build_segment(self.cfg.control_step_s, pattern_start)
            self._apply_command(wn, prv_setpoints_psi, pump_speeds)
            res, msgs, used = L._run_with_retry(wn, f"p6_env_k{k}")

            n_instants = self.cfg.control_step_s // self.cfg.rule_timestep_s
            self._validate_solve(wn, res, expected_index=n_instants,
                                 expected_timestep_s=self.cfg.rule_timestep_s,
                                 context=f"step k={k}")
            next_time = self._t_elapsed + self.cfg.control_step_s
            out = self._extract(wn, res, step_index=k, sim_time_s=float(next_time),
                                row=-1)
            out.wntr_warnings = msgs
            # carry forward (temporaries): final tank levels + pump statuses
            head = res.node["head"]
            next_tanks = {t: float(head[t].iloc[-1] - wn.get_node(t).elevation)
                          for t in wn.tank_name_list}
            next_pumps = {p: LinkStatus(int(res.link["status"][p].iloc[-1]))
                          for p in PUMP_IDS}
            next_done = bool(k + 1 >= self.cfg.n_steps)
        except Exception:
            self._state_restore(snapshot)
            raise
        # atomic commit: nothing above touched driver state
        self._step_index = k
        self._t_elapsed = next_time
        self._tank_levels_m = next_tanks
        self._pump_status = next_pumps
        self._done = next_done
        return out

    def probe(self, prv_setpoints_psi: dict, pump_speeds: dict,
              horizon_steps: int = 1) -> list[StepResult]:
        """Forward-simulate a candidate command WITHOUT committing (D-P6-006).

        The execution-time admissibility layer must look ahead over the window
        [0..H] from the IDENTICAL current real state for both the proposed action
        and the HOLD counterfactual. This method advances a CLONE of the carried
        state (tank levels, pump statuses, pattern phase) ``horizon_steps`` control
        steps forward, returns one ``StepResult`` per step (whose 180 s intra-step
        traces give the window's p_min / n_neg signals), and RESTORES the driver's
        real state on exit -- so probing never changes what ``step`` will later
        commit. Re-issues ``base_speed`` every segment, exactly like ``step`` (the
        G12 fix), so the look-ahead sees the same pump behaviour the commit will.

        Determinism note: for the action that is ultimately executed, a probe over
        H=1 solves the SAME segment from the SAME state as the subsequent
        ``step``, so the committed state equals the probed admissible state.
        """
        # Probe works entirely on an in-method clone; the REAL state is restored
        # in `finally`, so a failure anywhere (solve, validation, extraction,
        # carry-state build) cannot leak into the driver. `_done` and the
        # scenario fields are part of the snapshot because the clone may be
        # advanced past the horizon.
        snap = self._state_snapshot()
        results: list[StepResult] = []
        try:
            for _ in range(int(horizon_steps)):
                self._step_index += 1
                k = self._step_index
                pattern_start = self._t_elapsed
                wn = self._build_segment(self.cfg.control_step_s, pattern_start)
                self._apply_command(wn, prv_setpoints_psi, pump_speeds)
                res, msgs, _ = L._run_with_retry(wn, f"p6_env_probe_k{k}")
                n_instants = self.cfg.control_step_s // self.cfg.rule_timestep_s
                self._validate_solve(wn, res, expected_index=n_instants,
                                     expected_timestep_s=self.cfg.rule_timestep_s,
                                     context=f"probe k={k}")
                next_time = self._t_elapsed + self.cfg.control_step_s
                out = self._extract(wn, res, step_index=k,
                                    sim_time_s=float(next_time), row=-1)
                out.wntr_warnings = msgs
                # carry the CLONE forward for multi-step look-ahead
                head = res.node["head"]
                next_tanks = {t: float(head[t].iloc[-1] - wn.get_node(t).elevation)
                              for t in wn.tank_name_list}
                next_pumps = {p: LinkStatus(int(res.link["status"][p].iloc[-1]))
                              for p in PUMP_IDS}
                results.append(out)
                self._t_elapsed = next_time
                self._tank_levels_m = next_tanks
                self._pump_status = next_pumps
        finally:
            self._state_restore(snap)
        return results

    @property
    def done(self) -> bool:
        return self._done

    @property
    def t_elapsed_s(self) -> int:
        return self._t_elapsed
