"""Phase 6 / STEP 6 - per-PRV operating-bound characterisation for the five
candidate DRL-controlled PRVs (VALVE-173, VALVE-175, VALVE-176, VALVE-177,
VALVE-178).

PURPOSE (Phase 6 STEP 6 brief, sections 3-8). This module does NOT optimise PRV
settings and does NOT choose bounds to make PPO easier to train. It measures the
physical response of each candidate actuator over its own setpoint range and
derives a *defensible operating domain* on hydraulic grounds. No optimisation,
no search, no reward, no RL of any kind occurs here. Every number is produced by
the EPANET solver from the working copy with native controls and rules
untouched, under PDA with the Phase-5 leakage instrument active.

METHOD. For each valve, one full 96 h EPS is run per candidate setpoint, with
that one valve overridden and the other seven PRVs (and both pumps) left at their
distributed values - so the response attributed to a valve is not confounded by
simultaneously moving another actuator. Grids are anchored on the Phase-5 nominal
of each valve (173=70.0, 175=55.0, 176=29.762, 177=45.0, 178=37.0 psi) and are
NOT forced to a common percentage band (brief s.4): a fixed coarse grid is run
first, then the grid is *extended* downward until the negative-pressure cliff is
bracketed and upward until the valve stops regulating (saturates Open), and
finally *refined* to 0.25 psi around every safety transition. The domain is
therefore allowed to be asymmetric, one-sided or disconnected (brief s.7); it is
never assumed symmetric.

SAFETY CRITERION (brief s.6 - not defined on leakage). A setpoint is flagged
UNSAFE if, relative to the reference nominal run measured in this same script,
it produces any of: negative service pressure at any junction-timestep; an
EPANET solver error or an "EXECUTION HALTED"; an abnormal continuity residual;
or an implausible actuator realisation (commanded-vs-realised mismatch while the
valve reports Active). A *separate, stricter* service criterion also flags any
setpoint that introduces NEW <20 psi service-pressure violations beyond the
baseline count the nominal network already carries. Both are reported per
setpoint; neither threshold is invented for convenience - each is the measured
reference behaviour.

THREE DOMAINS ARE REPORTED SEPARATELY (brief s.8), never conflated:
  (A) observed domain          - the full setpoint range actually swept;
  (B) safe / service-clean     - the experimentally supported safe domain;
  (C) proposed DRL domain      - an ENGINEERING DECISION, requiring explicit
                                 justification and researcher approval, and NOT
                                 automatically equal to (B). Registered as
                                 D-P6-003, status PENDING APPROVAL.

CROSS-ACTUATOR SAFETY (brief s.10). Per-valve bounds are measured with the other
four PRVs at nominal. A joint verification run then places all five valves
simultaneously at their proposed lower bounds; if that corner produces negative
pressure or new service violations, per-valve box constraints are NOT jointly
sufficient and the fact is reported (it does not silently alter any bound).

Output -> results/phase6/p6_s6_active_prv_bounds.json. Bounds are PROPOSED, never
FINAL, until explicit researcher approval (brief s.18).
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import phase5_common as C            # noqa: E402
import g6_g7_g8_leak_pda as L        # noqa: E402
import p6_s3_prv_finechar as S3      # noqa: E402

# The five G5-admitted RL-controlled PRVs (D-P6-000a). VALVE-174/179/180 are
# excluded on measured grounds and are NOT characterised here.
RL_VALVES = ["VALVE-173", "VALVE-175", "VALVE-176", "VALVE-177", "VALVE-178"]
NOMINAL_PSI = {v: S3.NOMINAL_PSI[v] for v in RL_VALVES}

# --- fixed coarse grids (psi), each anchored on and including its nominal ------
# Chosen wide enough that the adaptive extension below usually only has to refine,
# not relocate, a transition. Values are physically plausible PRV setpoints for
# each valve's zone; they are not a common percentage band (brief s.4/s.7).
COARSE_GRID = {
    "VALVE-173": [40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0],
    "VALVE-175": [30.0, 40.0, 50.0, 55.0, 65.0, 75.0, 85.0],
    "VALVE-176": [15.0, 20.0, 25.0, 29.762, 35.0, 45.0, 55.0],
    "VALVE-177": [25.0, 30.0, 40.0, 45.0, 55.0, 65.0, 75.0],
    "VALVE-178": [20.0, 27.75, 32.0, 37.0, 42.0, 46.25, 55.0],
}

# --- adaptive extension / refinement policy (all fixed before execution) -------
DOWN_STEP_PSI = 5.0        # step for extending the grid below the coarse minimum
UP_STEP_PSI = 10.0         # step for extending the grid above the coarse maximum
FLOOR_PSI = 5.0            # never command a PRV below this (physically meaningless)
CEIL_MULT = 2.0            # never extend a valve above CEIL_MULT x its nominal
REFINE_LEVELS_PSI = [1.0, 0.25]   # progressive refinement resolution at each cliff
ACTIVE_FLOOR = 0.05        # frac_time_active below which the valve is "saturated Open"
MAX_RUNS_PER_VALVE = 90    # hard cap; truncation (if ever hit) is recorded as a caveat

# --- safety-classification tolerances (measured references, not conveniences) --
CONT_TOL = 1.0e-3          # relative continuity residual above which a run is flagged
REALIZE_TOL_PSI = 1.0      # commanded-vs-realised mismatch (while Active) above which
                           # the actuator realisation is flagged implausible


def _prefix(valve: str, s: float) -> str:
    return f"p6s6_{valve.split('-')[1]}_{('%g' % s).replace('.', 'p')}"


def _frange(lo: float, hi: float, step: float) -> list[float]:
    """Points strictly inside (lo, hi) at `step`, aligned on lo. Closed-form."""
    out, k = [], 1
    while True:
        x = round(lo + k * step, 3)
        if x >= hi - 1e-9:
            break
        out.append(x)
        k += 1
    return out


# --- measured safety classification of a single 96 h EPS row -------------------
def _solver_clean(row: dict) -> bool:
    """No EPANET error, no halt, continuity residual within tolerance.

    The benign WNTR write-time warning ("Not all curves were used ...") is emitted
    for every run in the whole harness and is deliberately ignored; classification
    uses the authoritative EPANET .rpt scan, not the captured Python warnings.
    """
    rs = row.get("report_scan", {})
    if not rs.get("rpt_found", False):
        return False
    if rs.get("n_error_lines", 0) > 0:
        return False
    if any("HALTED" in ln.upper() for ln in rs.get("flagged_lines", [])):
        return False
    return float(row.get("continuity_residual_rel_max", 1.0)) <= CONT_TOL


def _realisation_ok(row: dict) -> bool:
    """Plausible actuator state: either the valve is not Active, or the realised
    setpoint matches the command while Active. A PRV that cannot reach a high
    command goes Open - that is a valid state, not an implausible one."""
    sv = row.get("swept_valve")
    if not sv or not sv.get("ever_active"):
        return True
    err = sv.get("max_abs_realisation_error_when_active_psi")
    return err is None or float(err) <= REALIZE_TOL_PSI


def _no_negative(row: dict) -> bool:
    return int(row.get("n_node_timesteps_negative", 1)) == 0


def _hard_safe(row: dict) -> bool:
    """No negative pressure, solver converged, actuator state plausible."""
    return _no_negative(row) and _solver_clean(row) and _realisation_ok(row)


def _service_clean(row: dict, ref_below20: int) -> bool:
    """Hard-safe AND introduces no NEW <20 psi service violations vs baseline."""
    return (_hard_safe(row)
            and int(row.get("n_node_timesteps_below_20psi", 10 ** 9)) <= ref_below20)


def _compact(row: dict, ref_below20: int) -> dict:
    """Small per-setpoint summary for the JSON alongside the full raw case."""
    sv = row.get("swept_valve") or {}
    return {
        "setting_psi": row["setting_psi"],
        "ratio_of_nominal": row["setting_ratio_of_nominal"],
        "mean_service_pressure_psi": row["mean_service_pressure_psi"],
        "min_service_pressure_psi": row["min_service_pressure_psi"],
        "argmin_service_node": row["argmin_service_node"],
        "n_node_timesteps_below_20psi": row["n_node_timesteps_below_20psi"],
        "n_new_below_20psi_vs_baseline":
            int(row["n_node_timesteps_below_20psi"]) - int(ref_below20),
        "n_node_timesteps_negative": row["n_node_timesteps_negative"],
        "leakage_mean_gpm": row["leakage_mean_gpm"],
        "dsr_mean": row["dsr_mean"],
        "dsr_min": row["dsr_min"],
        "frac_time_active": sv.get("frac_time_active"),
        "frac_time_open": sv.get("frac_time_open"),
        "frac_time_closed": sv.get("frac_time_closed"),
        "valve_flow_mean_gpm": sv.get("flow_mean_gpm"),
        "max_abs_realisation_error_when_active_psi":
            sv.get("max_abs_realisation_error_when_active_psi"),
        "continuity_residual_rel_max": row["continuity_residual_rel_max"],
        "solver_clean": _solver_clean(row),
        "no_negative_pressure": _no_negative(row),
        "hard_safe": _hard_safe(row),
        "service_clean": _service_clean(row, ref_below20),
    }


def _interval_containing(settings: list[float], ok: dict, anchor: float):
    """Maximal contiguous run of ok==True containing the tested point nearest
    the anchor (nominal, which is always safe). Returns [lo, hi] or None."""
    trues = [s for s in settings if ok[s]]
    if not trues:
        return None
    start = min(trues, key=lambda s: abs(s - anchor))
    i = settings.index(start)
    lo = hi = i
    while lo - 1 >= 0 and ok[settings[lo - 1]]:
        lo -= 1
    while hi + 1 < len(settings) and ok[settings[hi + 1]]:
        hi += 1
    return [settings[lo], settings[hi]]


def sweep_valve(valve: str, coeff_us, svc, conn, ref_below20: int) -> dict:
    """Coarse grid -> adaptive extension -> refinement, then derive the domains.

    Pure characterisation: the grid is data-adaptive only in WHERE it measures
    (to bracket transitions), never in WHAT it optimises. No objective is
    maximised at any point.
    """
    nominal = NOMINAL_PSI[valve]
    ceil_psi = round(CEIL_MULT * nominal, 3)
    rows: dict[float, dict] = {}
    truncated = False

    def ensure(s: float):
        nonlocal truncated
        key = round(float(s), 3)
        if key in rows:
            return rows[key]
        if len(rows) >= MAX_RUNS_PER_VALVE:
            truncated = True
            return None
        label = (f"{valve} setting {key:g} psi ({key / nominal:.3f} x nominal), "
                 "other four RL PRVs at nominal")
        rows[key] = S3.run_case(label, _prefix(valve, key), valve, key,
                                coeff_us, svc, conn)
        return rows[key]

    for s in COARSE_GRID[valve]:
        ensure(s)

    # Extend DOWN until the negative-pressure cliff is bracketed (lowest tested
    # point turns negative) or the physical floor is reached.
    while len(rows) < MAX_RUNS_PER_VALVE:
        s = min(rows)
        if not _no_negative(rows[s]) or s <= FLOOR_PSI:
            break
        nxt = round(s - DOWN_STEP_PSI, 3)
        if nxt < FLOOR_PSI:
            nxt = FLOOR_PSI
        if nxt in rows:
            break
        ensure(nxt)

    # Extend UP until the valve stops regulating (saturates Open), a high-side
    # negative cliff appears, or the ceiling is reached.
    while len(rows) < MAX_RUNS_PER_VALVE:
        s = max(rows)
        sv = rows[s].get("swept_valve") or {}
        fa = float(sv.get("frac_time_active") or 0.0)
        if fa < ACTIVE_FLOOR or not _no_negative(rows[s]) or s >= ceil_psi:
            break
        nxt = round(s + UP_STEP_PSI, 3)
        if nxt > ceil_psi:
            nxt = ceil_psi
        if nxt in rows:
            break
        ensure(nxt)

    # Refine every safety transition to 0.25 psi. Two predicates: hard-safety
    # (negative pressure / solver / realisation) and the stricter service
    # criterion (no new <20 psi). Refinement fills the flip bracket at each
    # resolution, then re-detects, so it converges on the actual boundary.
    def refine(pred):
        for level in REFINE_LEVELS_PSI:
            while len(rows) < MAX_RUNS_PER_VALVE:
                settings = sorted(rows)
                flag = {s: pred(rows[s]) for s in settings}
                bracket = next(((a, b) for a, b in zip(settings, settings[1:])
                                if flag[a] != flag[b] and (b - a) > level + 1e-9),
                               None)
                if bracket is None:
                    break
                added = False
                for x in _frange(bracket[0], bracket[1], level):
                    if x not in rows:
                        ensure(x)
                        added = True
                if not added:
                    break

    refine(_hard_safe)
    refine(lambda r: _service_clean(r, ref_below20))

    return _derive(valve, rows, ref_below20, truncated, ceil_psi)


def _derive(valve: str, rows: dict, ref_below20: int, truncated: bool,
            ceil_psi: float) -> dict:
    """Turn the measured rows into observed / safe / service-clean domains, the
    high-side regulation ceiling, and a PROPOSED (not final) DRL domain."""
    nominal = NOMINAL_PSI[valve]
    settings = sorted(rows)
    hard = {s: _hard_safe(rows[s]) for s in settings}
    clean = {s: _service_clean(rows[s], ref_below20) for s in settings}

    safe_dom = _interval_containing(settings, hard, nominal)
    clean_dom = _interval_containing(settings, clean, nominal)

    # Low-side transitions (values below the safe/clean interval that fail).
    def last_failing_below(dom, flag):
        if dom is None:
            return None
        below = [s for s in settings if s < dom[0] and not flag[s]]
        return max(below) if below else None

    neg_fail_below = last_failing_below(safe_dom, hard)
    svc_fail_below = last_failing_below(clean_dom, clean)

    # High-side regulation: where the valve is mostly Active vs mostly Open.
    def frac(s, key):
        sv = rows[s].get("swept_valve") or {}
        return float(sv.get(key) or 0.0)

    mostly_active = [s for s in settings if frac(s, "frac_time_active") >= 0.5]
    open_above_nom = [s for s in settings
                      if s >= nominal and frac(s, "frac_time_open") >= 0.5]
    regulation_ceiling = max(mostly_active) if mostly_active else None
    saturation_onset = min(open_above_nom) if open_above_nom else None

    # (C) PROPOSED DRL domain - ENGINEERING DECISION, PENDING APPROVAL.
    # Primary proposal: a service-clean, leakage-reduction-aligned interval whose
    # lower bound is the lowest measured setpoint that adds no new <20 psi
    # violation and no negative pressure, and whose upper bound is the nominal
    # setpoint (the agent reduces pressure below nominal; it does not raise
    # leakage above the distributed baseline). The permissive alternatives are
    # recorded so the researcher can widen the domain deliberately, not silently.
    proposed_lower = clean_dom[0] if clean_dom else None
    proposed_upper = nominal
    alt_lower_hardsafe = safe_dom[0] if safe_dom else None
    alt_upper_headroom = (None if regulation_ceiling is None
                          else min(regulation_ceiling,
                                   clean_dom[1] if clean_dom else regulation_ceiling))

    # Actuator AUTHORITY (brief s.5): how much leakage this valve can actually
    # move within its proposed [lower, nominal] domain, and whether it regulates
    # or merely closes when driven low. A valve that closes below its domain, or
    # whose leakage span is ~0, is a weak RL action dimension in isolation - a
    # measured caveat for the researcher, never used to alter a bound.
    def leak_at(s):
        r = rows.get(round(float(s), 3))
        return None if r is None else float(r.get("leakage_mean_gpm"))

    leaks = [float(rows[s].get("leakage_mean_gpm")) for s in settings]
    leak_nom = leak_at(nominal)
    lo_active = frac(settings[0], "frac_time_active")
    lo_open = frac(settings[0], "frac_time_open")
    low_side_behaviour = ("closes_below_domain"
                          if lo_active < ACTIVE_FLOOR and lo_open < ACTIVE_FLOOR
                          else "regulates_across_domain")
    prop_leak_lower = leak_at(proposed_lower) if proposed_lower is not None else None
    leak_saving = (None if prop_leak_lower is None or leak_nom is None
                   else round(leak_nom - prop_leak_lower, 3))
    authority = {
        "valve_flow_mean_at_nominal_gpm": frac(nominal, "flow_mean_gpm"),
        "leakage_at_nominal_gpm": leak_nom,
        "leakage_min_over_observed_gpm": round(min(leaks), 3),
        "leakage_max_over_observed_gpm": round(max(leaks), 3),
        "leakage_span_over_observed_gpm": round(max(leaks) - min(leaks), 3),
        "leakage_reduction_within_proposed_domain_gpm": leak_saving,
        "leakage_reduction_within_proposed_domain_pct": (
            None if leak_saving is None or not leak_nom
            else round(100.0 * leak_saving / leak_nom, 3)),
        "low_side_actuator_behaviour": low_side_behaviour,
        "note": ("Leakage-reduction authority within the proposed [lower, nominal] "
                 "domain, measured with the other four PRVs at nominal. A small "
                 "span or 'closes_below_domain' means a weak action dimension in "
                 "isolation; joint action with the other PRVs may still contribute. "
                 "Evidence only - not used to alter any bound."),
    }

    return {
        "valve": valve,
        "nominal_setpoint_psi": nominal,
        "n_setpoints_evaluated": len(settings),
        "grid_extension_truncated_at_cap": truncated,
        "ceiling_used_psi": ceil_psi,
        "actuator_authority": authority,
        # (A) observed
        "observed_domain_psi": [settings[0], settings[-1]],
        # (B) experimentally supported safe domains
        "safe_observed_domain_psi": safe_dom,
        "service_clean_domain_psi": clean_dom,
        "low_side_negative_transition_psi": {
            "highest_setpoint_with_negative_pressure": neg_fail_below,
            "lowest_setpoint_with_no_negative": safe_dom[0] if safe_dom else None,
            "resolved_bracket_width_psi": (
                None if neg_fail_below is None or safe_dom is None
                else round(safe_dom[0] - neg_fail_below, 3)),
        },
        "low_side_service_transition_psi": {
            "highest_setpoint_with_new_below20_violation": svc_fail_below,
            "lowest_setpoint_service_clean": clean_dom[0] if clean_dom else None,
            "resolved_bracket_width_psi": (
                None if svc_fail_below is None or clean_dom is None
                else round(clean_dom[0] - svc_fail_below, 3)),
        },
        "high_side_regulation": {
            "highest_setpoint_mostly_active_psi": regulation_ceiling,
            "saturation_onset_setpoint_psi": saturation_onset,
            "note": ("Above the saturation onset the commanded setpoint exceeds "
                     "the available upstream head; the valve passes flow (Open) "
                     "and raising the setpoint further has no hydraulic effect. "
                     "This is an effectiveness limit, not a safety limit."),
        },
        # (C) proposed DRL domain - PENDING APPROVAL (brief s.8/s.14/s.18)
        "proposed_drl_domain_psi": (
            None if proposed_lower is None else [proposed_lower, proposed_upper]),
        "proposed_drl_domain_rationale": (
            "PROPOSED, not final. Lower = lowest measured service-clean setpoint "
            "(no new <20 psi violation, no negative pressure); upper = nominal, so "
            "the action space reduces pressure below the distributed baseline and "
            "cannot command higher leakage than baseline. This is an engineering "
            "decision aligned with the leakage-reduction objective, awaiting "
            "researcher approval."),
        "proposed_drl_domain_alternatives_psi": {
            "permissive_lower_hard_safe_only": alt_lower_hardsafe,
            "headroom_upper_to_regulation_ceiling": alt_upper_headroom,
            "note": ("The permissive lower bound admits setpoints that add <20 psi "
                     "violations but no negative pressure (to be handled by the "
                     "reward / STEP-9 safety layer). The headroom upper bound gives "
                     "the agent room to RAISE pressure for service recovery, at the "
                     "cost of admitting leakage-increasing actions. Both widen the "
                     "domain and must be chosen by the researcher, not by default."),
        },
        "sweep": [_compact(rows[s], ref_below20) for s in settings],
        "cases": {f"{valve}@{s:g}psi": rows[s] for s in settings},
    }


# --- cross-actuator joint verification (brief s.10) ----------------------------
def _build_joint(settings_by_valve: dict):
    """Load the working copy and apply SEVERAL PRV overrides at once.

    Mirrors S3.build's solver/PDA configuration exactly; the only difference is
    that more than one valve is overridden, so the joint corner can be measured.
    """
    wn = C.load_wn(rule_timestep=S3.RULE_TIMESTEP_S,
                   report_timestep=S3.REPORT_TIMESTEP_S)
    wn.options.hydraulic.accuracy = S3.SOLVER_ACCURACY
    wn.options.hydraulic.trials = S3.SOLVER_TRIALS
    wn.options.hydraulic.demand_model = "PDA"
    wn.options.hydraulic.required_pressure = C.psi_to_m(S3.PDA_REQUIRED_PSI)
    wn.options.hydraulic.minimum_pressure = C.psi_to_m(S3.PDA_MINIMUM_PSI)
    wn.options.hydraulic.pressure_exponent = S3.PDA_EXPONENT
    for v, s in settings_by_valve.items():
        wn.get_link(v).initial_setting = C.psi_to_m(float(s))
    return wn


def run_joint(label: str, prefix: str, settings_by_valve: dict,
              coeff_us, svc, conn) -> dict:
    """One 96 h EPS with several PRVs overridden simultaneously (valve=None so
    the per-valve realisation dict still covers all eight PRVs)."""
    wn = _build_joint(settings_by_valve)
    if coeff_us is not None:
        L.apply_leak(wn, coeff_us)
    solver = S3.assert_solver(wn)
    echo = L.echo_check(wn, prefix)
    res, msgs, used_prefix = L._run_with_retry(wn, prefix)
    row = {
        "label": label,
        "swept_valve_name": None,
        "joint_settings_psi": {v: float(s) for v, s in settings_by_valve.items()},
        "solver": solver,
        "echo_check": echo,
        "wntr_warnings": msgs,
        "report_scan": L._rpt_errors(used_prefix),
        "leak_applied": coeff_us is not None,
    }
    row.update(S3.measure(wn, res, coeff_us, svc, conn, None))
    return row

# <<APPEND-MAIN>>


def main() -> dict:
    import json

    C.build_working_copy(verbose=False)
    wn0 = S3.build(None, None)
    svc, conn = S3.service_nodes(wn0)
    assert len(svc) == 121 and len(conn) == 5, (len(svc), len(conn))

    # Leak instrument: recomputed by the same Phase 5 closed form from the same
    # leak-free baseline, so this module does not depend on any Phase 5 artefact
    # being present. VALIDATION INSTRUMENT only (brief s.2/s.18); not calibrated.
    base_p, base_inflow, weights = L.baseline_pressures("p6s6_size")
    sizing = L.leak_coefficients(weights, base_p,
                                 L.LEAK_TARGET_FRACTION * base_inflow)
    coeff_us = sizing["coefficient_gpm_per_psi_alpha"]

    # Reference: all PRVs at nominal, measured in THIS script. The STEP 6 safety
    # criteria are defined RELATIVE TO THIS RUN (brief s.6), not to an external
    # file: 0 negative node-timesteps and the baseline <20 psi count are the
    # measured references against which every swept setpoint is classified.
    ref = S3.run_case("reference: all PRVs at nominal, leakage on, PDA",
                      "p6s6_ref", None, None, coeff_us, svc, conn)
    ref_below20 = int(ref["n_node_timesteps_below_20psi"])
    ref_neg = int(ref["n_node_timesteps_negative"])

    valves_out: dict[str, dict] = {}
    for valve in RL_VALVES:
        valves_out[valve] = sweep_valve(valve, coeff_us, svc, conn, ref_below20)

    # <<APPEND-JOINT>>

    # Cross-actuator safety (brief s.10). Per-valve bounds above are each measured
    # with the other four PRVs at nominal. Here all five are placed at their
    # PROPOSED lower bounds simultaneously - the most aggressive corner of the
    # proposed box. If that corner is unsafe or introduces new service violations,
    # per-valve box constraints are NOT jointly sufficient; this is reported and a
    # joint-action safety layer / STEP-9 test is flagged. It NEVER silently alters
    # any per-valve bound.
    proposed_lowers = {v: valves_out[v]["proposed_drl_domain_psi"][0]
                       for v in RL_VALVES
                       if valves_out[v].get("proposed_drl_domain_psi")}
    joint = None
    if len(proposed_lowers) == len(RL_VALVES):
        jrow = run_joint(
            "joint verification: all five RL PRVs at proposed lower bounds "
            "simultaneously (most aggressive corner of the proposed box)",
            "p6s6_joint_lo", proposed_lowers, coeff_us, svc, conn)
        j_hard = _hard_safe(jrow)
        j_clean = _service_clean(jrow, ref_below20)
        joint = {
            "settings_psi": {v: float(s) for v, s in proposed_lowers.items()},
            "n_node_timesteps_negative": jrow["n_node_timesteps_negative"],
            "n_node_timesteps_below_20psi": jrow["n_node_timesteps_below_20psi"],
            "n_new_below_20psi_vs_baseline":
                int(jrow["n_node_timesteps_below_20psi"]) - ref_below20,
            "min_service_pressure_psi": jrow["min_service_pressure_psi"],
            "argmin_service_node": jrow["argmin_service_node"],
            "leakage_mean_gpm": jrow["leakage_mean_gpm"],
            "leakage_reduction_vs_baseline_gpm":
                round(float(ref["leakage_mean_gpm"])
                      - float(jrow["leakage_mean_gpm"]), 3),
            "no_negative_pressure": _no_negative(jrow),
            "solver_clean": _solver_clean(jrow),
            "hard_safe": j_hard,
            "service_clean": j_clean,
            "box_constraints_jointly_sufficient_at_lower_corner": j_clean,
            "interpretation": (
                ("The simultaneous lower-bound corner is service-clean: no negative "
                 "pressure and no new <20 psi violation beyond baseline. Per-valve "
                 "box constraints are jointly sufficient at the tested corner.")
                if j_clean else
                ("The simultaneous lower-bound corner is NOT service-clean. "
                 "Per-valve box constraints are NOT jointly sufficient at this "
                 "corner: a joint-action safety layer (STEP 9) or a tighter joint "
                 "test is required before the proposed boxes can be used together. "
                 "This does not alter any per-valve bound; it is reported as a "
                 "cross-actuator caveat (brief s.10).")),
            "case": jrow,
        }

    # <<APPEND-PAYLOAD>>

    # Compact per-valve bound table (brief s.17 evidence table columns).
    bounds_table = {
        v: {
            "nominal_psi": valves_out[v]["nominal_setpoint_psi"],
            "observed_domain_psi": valves_out[v]["observed_domain_psi"],
            "safe_observed_domain_psi": valves_out[v]["safe_observed_domain_psi"],
            "service_clean_domain_psi": valves_out[v]["service_clean_domain_psi"],
            "proposed_drl_domain_psi": valves_out[v]["proposed_drl_domain_psi"],
            "n_setpoints_evaluated": valves_out[v]["n_setpoints_evaluated"],
            "grid_extension_truncated_at_cap":
                valves_out[v]["grid_extension_truncated_at_cap"],
        }
        for v in RL_VALVES
    }
    any_truncated = any(valves_out[v]["grid_extension_truncated_at_cap"]
                        for v in RL_VALVES)

    payload = {
        "phase": 6,
        "step": 6,
        "title": ("Per-PRV operating-bound characterisation for the five "
                  "candidate DRL-controlled PRVs (VALVE-173/175/176/177/178)"),
        "env": C.env_info(),
        "decision_ref": "D-P6-003",
        "decision_status": "PROPOSED - PENDING RESEARCHER APPROVAL",
        "scope_statement": (
            "Characterisation only. No optimisation, no search, no reward, no RL. "
            "Each candidate setpoint is one full 96 h EPS produced by the EPANET "
            "solver from the working copy with native controls and rules "
            "untouched, under PDA with the Phase-5 leakage validation instrument "
            "active. Bounds are PROPOSED, never FINAL, until explicit researcher "
            "approval (brief s.18)."),
        "solver_policy": {
            "accuracy": S3.SOLVER_ACCURACY, "trials": S3.SOLVER_TRIALS,
            "rule_timestep_s": S3.RULE_TIMESTEP_S,
            "report_timestep_s": S3.REPORT_TIMESTEP_S,
            "demand_model": "PDA",
            "required_pressure_psi": S3.PDA_REQUIRED_PSI,
            "minimum_pressure_psi": S3.PDA_MINIMUM_PSI,
            "pressure_exponent": S3.PDA_EXPONENT,
            "asserted_after_every_load": True,
        },
        "service_node_policy": {
            "rule": ("declared elevation exactly 0.0 ft AND zero total base "
                     "demand -> connector artefact, excluded from every service "
                     "and pressure statistic"),
            "n_service_junctions": len(svc),
            "n_connector_junctions": len(conn),
            "connector_nodes": conn,
        },
        "leak_instrument": {
            "status": ("VALIDATION INSTRUMENT, not a calibrated field leakage "
                       "model. Half-pipe-length weights, single closed-form "
                       "global scale, exponent 0.5 from the file's [OPTIONS]."),
            "sizing": {k: val for k, val in sizing.items()
                       if k != "coefficient_gpm_per_psi_alpha"},
            "coefficients_gpm_per_psi_alpha": coeff_us,
        },
        "safety_criterion": {
            "definition": ("A setpoint is UNSAFE (fails hard-safety) if it "
                           "produces ANY negative service pressure, an EPANET "
                           "solver error / EXECUTION HALTED, a continuity residual "
                           f"> {CONT_TOL:g} (relative), or an implausible actuator "
                           f"realisation (>|{REALIZE_TOL_PSI:g}| psi command-vs-"
                           "realised while Active). A stricter SERVICE-CLEAN "
                           "criterion additionally requires no NEW <20 psi service "
                           "violation beyond the measured baseline count. Not "
                           "defined on leakage (brief s.6)."),
            "reference_baseline_below20_count": ref_below20,
            "reference_baseline_negative_count": ref_neg,
            "continuity_tol_rel": CONT_TOL,
            "realisation_tol_psi": REALIZE_TOL_PSI,
            "active_floor_frac_time": ACTIVE_FLOOR,
        },
        "grid_policy": {
            "coarse_grids_psi": COARSE_GRID,
            "down_step_psi": DOWN_STEP_PSI, "up_step_psi": UP_STEP_PSI,
            "floor_psi": FLOOR_PSI, "ceiling_multiple_of_nominal": CEIL_MULT,
            "refine_levels_psi": REFINE_LEVELS_PSI,
            "max_runs_per_valve": MAX_RUNS_PER_VALVE,
            "note": ("Fixed coarse grid, then extend DOWN to bracket the negative "
                     "cliff and UP to the saturation/ceiling, then refine to "
                     "0.25 psi at every safety transition. Grid is data-adaptive "
                     "only in WHERE it measures, never in WHAT it optimises. "
                     "Domains may be asymmetric / one-sided / disconnected "
                     "(brief s.7); symmetry is never assumed."),
        },
        "reference_nominal_case": ref,
        "proposed_bounds_table": bounds_table,
        "any_grid_truncated_at_cap": any_truncated,
        "cross_actuator_joint_lower_corner": joint,
        "per_valve": valves_out,
    }

    # <<APPEND-WRITE>>

    out = C.REPO / "results" / "phase6"
    out.mkdir(parents=True, exist_ok=True)
    path = out / "p6_s6_active_prv_bounds.json"
    path.write_text(json.dumps(payload, indent=2, default=str),
                    encoding="utf-8")
    print(f"[written] {path}")

    # --- console summary (traceable, not a substitute for the JSON) -----------
    print(f"[reference] all-nominal: mean_service="
          f"{ref['mean_service_pressure_psi']:.3f} psi, min="
          f"{ref['min_service_pressure_psi']:.3f} @ {ref['argmin_service_node']}, "
          f"<20psi_ts={ref_below20}, neg_ts={ref_neg}, "
          f"leak={ref['leakage_mean_gpm']:.3f} gpm")
    print("[proposed bounds - PENDING APPROVAL] "
          "valve: observed | safe | service-clean | PROPOSED")
    for v in RL_VALVES:
        d = valves_out[v]
        print(f"  {v} (nom {d['nominal_setpoint_psi']:g}): "
              f"obs {d['observed_domain_psi']} | "
              f"safe {d['safe_observed_domain_psi']} | "
              f"clean {d['service_clean_domain_psi']} | "
              f"PROPOSED {d['proposed_drl_domain_psi']} "
              f"[{d['n_setpoints_evaluated']} setpoints"
              f"{', TRUNCATED' if d['grid_extension_truncated_at_cap'] else ''}]")
    if joint is not None:
        print(f"[joint lower-corner] hard_safe={joint['hard_safe']} "
              f"service_clean={joint['service_clean']} "
              f"new_<20psi={joint['n_new_below_20psi_vs_baseline']} "
              f"neg_ts={joint['n_node_timesteps_negative']} "
              f"min={joint['min_service_pressure_psi']:.3f} psi")
    else:
        print("[joint lower-corner] SKIPPED - not all five valves yielded a "
              "proposed lower bound")
    print("[status] STEP 6 characterisation done; bounds PROPOSED, D-P6-003 "
          "PENDING APPROVAL. Not FINAL until explicit researcher approval.")
    return payload


if __name__ == "__main__":
    main()




