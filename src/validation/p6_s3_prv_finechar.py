"""Phase 6 / STEP 3 - fine characterisation of VALVE-179, VALVE-174, VALVE-180.

Purpose (Phase 6 brief sections 6 and 7): decide, on measurement rather than on
convenience, whether each of the three PRVs that the distributed baseline solves
to a Closed/inert state belongs in the DRL action space, and if so over what
domain. The goal is *finding safe operational behaviour*, not optimisation. No
optimisation, no search, no tuning of any kind occurs in this module.

What is measured, per PRV and per setting, over a full 96 h EPS with the native
controls and rules untouched and the leakage instrument active under PDA:

    status fractions (Active / Open / Closed), realised-vs-commanded error,
    valve flow, mean service pressure, minimum service pressure, number of
    node-timesteps below the 20 psi service threshold, number of node-timesteps
    at negative pressure, leakage, served demand, unserved demand, DSR,
    tank level ranges.

Service statistics are computed over the 121 service-bearing junctions only.
The five connector junctions (declared elevation exactly 0.0 ft, zero base
demand, each an endpoint of a pump or of the reservoir connector pipe) are
excluded, because EPANET reports head above datum at those nodes: JUNCTION-106
reads 501.6 psi in the baseline and would dominate any pressure mean.

Solver settings are set explicitly on every load and asserted after the write /
read echo, per Phase 6 brief section 3: ACCURACY 1e-5, TRIALS 2000, rule
timestep 180 s, report timestep 1800 s. The Phase 5 module `g4_g5_prv.py` did
NOT set accuracy/trials and inherited the file's 0.005/40; its snapshot harness
is therefore deliberately not reused here.

The leak coefficients are recomputed here by the same closed-form Phase 5
function, from the same baseline, so this module does not depend on the Phase 5
artefact being present. They are a VALIDATION instrument, not a calibrated
field leakage model - see Phase 6 brief section 18.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import phase5_common as C  # noqa: E402
import g6_g7_g8_leak_pda as L  # noqa: E402

SOLVER_ACCURACY = 1e-5
SOLVER_TRIALS = 2000
RULE_TIMESTEP_S = 180
REPORT_TIMESTEP_S = 1800

SERVICE_PRESSURE_PSI = 20.0   # same threshold Phase 5 used for the G7 statistic
PDA_REQUIRED_PSI = L.PDA_REQUIRED_PSI
PDA_MINIMUM_PSI = L.PDA_MINIMUM_PSI
PDA_EXPONENT = L.PDA_EXPONENT

NOMINAL_PSI = dict(L.NOMINAL_PSI)

# The three PRVs the distributed baseline solves to Closed. Phase 5 G5 flagged
# these as the CONDITIONAL part of the 8-PRV action space.
TARGETS = ["VALVE-179", "VALVE-174", "VALVE-180"]

# Section 6 mandates 40..50 psi in 1 psi steps for VALVE-179. Two settings below
# nominal are added to confirm the inert region is genuinely flat, and three
# above the transition to measure how fast the damage grows once it opens.
GRIDS = {
    "VALVE-179": [38.0, 39.0, 40.0, 41.0, 42.0, 43.0, 44.0, 45.0, 46.0,
                  47.0, 48.0, 49.0, 50.0, 52.0, 55.0, 60.0],
    # VALVE-174 first showed flow at 100 psi in the Phase 5 snapshot sweep while
    # remaining Closed at 80. Bracket that interval, then step past it.
    "VALVE-174": [80.0, 85.0, 90.0, 92.0, 94.0, 95.0, 96.0, 98.0, 100.0, 110.0],
    # VALVE-180 is held shut by an explicit [CONTROLS] statement, not by valve
    # hydraulics. The sweep is retained to demonstrate the flatness rather than
    # assert it, and one run is made with that control removed (see below).
    "VALVE-180": [16.45, 20.0, 30.0, 40.0, 60.0, 80.0, 120.0],
}


def service_nodes(wn) -> tuple[list[str], list[str]]:
    """Split junctions into service-bearing and connector artefacts.

    Derived from the model's own declared properties by the same rule Phase 5
    gate 10 used, not hard-coded, so the rule is auditable and would find
    whatever a different file happens to contain.
    """
    conn, svc = [], []
    for j in wn.junction_name_list:
        nd = wn.get_node(j)
        el_ft = float(C.m_to_ft(nd.elevation))
        base = float(sum(d.base_value for d in nd.demand_timeseries_list))
        (conn if (el_ft == 0.0 and base == 0.0) else svc).append(j)
    return sorted(svc), sorted(conn)


def build(setting_psi: float | None, valve: str | None, *,
          release_valve180_control: bool = False):
    """Load the working copy, configure the solver, apply one PRV override."""
    wn = C.load_wn(rule_timestep=RULE_TIMESTEP_S,
                   report_timestep=REPORT_TIMESTEP_S)
    wn.options.hydraulic.accuracy = SOLVER_ACCURACY
    wn.options.hydraulic.trials = SOLVER_TRIALS
    wn.options.hydraulic.demand_model = "PDA"
    wn.options.hydraulic.required_pressure = C.psi_to_m(PDA_REQUIRED_PSI)
    wn.options.hydraulic.minimum_pressure = C.psi_to_m(PDA_MINIMUM_PSI)
    wn.options.hydraulic.pressure_exponent = PDA_EXPONENT
    if valve is not None and setting_psi is not None:
        wn.get_link(valve).initial_setting = C.psi_to_m(setting_psi)
    if release_valve180_control:
        # Removal is explicit, reported, and confined to this one diagnostic run.
        for name in list(wn.control_name_list):
            ctrl = wn.get_control(name)
            if "VALVE-180" in str(ctrl):
                wn.remove_control(name)
    return wn


def assert_solver(wn, *, report_timestep_s: float = REPORT_TIMESTEP_S) -> dict:
    """Fail loudly rather than silently inherit a WNTR default (brief s.3).

    `report_timestep_s` is a parameter, not a relaxation: ACCURACY, TRIALS, the
    rule timestep and the PDA parameters remain fixed at the brief's mandated
    values in every caller. Only the REPORTING cadence is allowed to differ, and
    only where a caller states why - the STEP 4 stepped loop reports at the
    180 s rule timestep inside each control step so that a rule firing between
    two control instants is observable. Reporting cadence changes what is
    written out, not what the solver computes.
    """
    got = {
        "accuracy": float(wn.options.hydraulic.accuracy),
        "trials": int(wn.options.hydraulic.trials),
        "rule_timestep_s": float(wn.options.time.rule_timestep),
        "report_timestep_s": float(wn.options.time.report_timestep),
        "demand_model": str(wn.options.hydraulic.demand_model),
        "required_pressure_psi": float(C.m_to_psi(
            wn.options.hydraulic.required_pressure)),
        "minimum_pressure_psi": float(C.m_to_psi(
            wn.options.hydraulic.minimum_pressure)),
        "pressure_exponent": float(wn.options.hydraulic.pressure_exponent),
    }
    assert got["accuracy"] == SOLVER_ACCURACY, got
    assert got["trials"] == SOLVER_TRIALS, got
    assert got["rule_timestep_s"] == RULE_TIMESTEP_S, got
    assert got["report_timestep_s"] == report_timestep_s, got
    assert got["demand_model"].upper() == "PDA", got
    return got


def measure(wn, res, coeff_us, svc, conn, valve) -> dict:
    """All service, leakage and actuator statistics for one EPS run."""
    acc = L.accounting(wn, res, coeff_us)
    p_psi = C.m_to_psi(res.node["pressure"])
    p_svc = p_psi[svc]

    out = {
        # --- service quality, service-bearing junctions only ----------------
        "n_service_junctions": len(svc),
        "n_connector_junctions_excluded": len(conn),
        "mean_service_pressure_psi": float(p_svc.mean().mean()),
        "min_service_pressure_psi": float(p_svc.min().min()),
        "max_service_pressure_psi": float(p_svc.max().max()),
        "n_node_timesteps_below_20psi": int((p_svc < SERVICE_PRESSURE_PSI)
                                           .to_numpy().sum()),
        "n_node_timesteps_negative": int((p_svc < 0.0).to_numpy().sum()),
        "pressure_deficit_mean_psi": float(
            (SERVICE_PRESSURE_PSI - p_svc).clip(lower=0.0).sum(axis=1).mean()),
        "argmin_service_node": str(p_svc.min().idxmin()),
        # --- contamination check: what the connector nodes would have done --
        "mean_pressure_all_126_psi": float(p_psi.mean().mean()),
        # --- leakage and demand accounting ---------------------------------
        "leakage_mean_gpm": acc["leakage_mean_gpm"],
        "leakage_max_gpm": acc["leakage_max_gpm"],
        "served_demand_mean_gpm": acc["served_demand_mean_gpm"],
        "requested_demand_mean_gpm": acc["requested_demand_mean_gpm"],
        "unserved_demand_mean_gpm": acc["unserved_demand_mean_gpm"],
        "unserved_demand_max_gpm": acc["unserved_demand_max_gpm"],
        "dsr_mean": acc["dsr_mean"],
        "dsr_min": acc["dsr_min"],
        "leakage_share_of_served_pct": acc["leakage_share_of_served_pct"],
        "continuity_residual_rel_max": acc["continuity_residual_rel_max"],
        "n_timesteps": acc["n_timesteps"],
    }

    # --- actuator realisation, all eight PRVs ------------------------------
    st = res.link["status"]
    sett = res.link["setting"]
    flow = C.m3s_to_gpm(res.link["flowrate"])
    valves = {}
    for v in sorted(NOMINAL_PSI):
        s = st[v]
        n = max(len(s), 1)
        # EPANET status codes: 0 Closed, 1 Open, 2 Active for a valve.
        frac = {lbl: float((s == code).sum()) / n
                for code, lbl in ((0, "closed"), (1, "open"), (2, "active"))}
        active = s == 2
        realised = C.m_to_psi(sett[v])
        cmd_psi = float(C.m_to_psi(wn.get_link(v).initial_setting))
        err = (realised[active] - cmd_psi).abs()
        valves[v] = {
            "commanded_setting_psi": cmd_psi,
            "nominal_setting_psi": NOMINAL_PSI[v],
            "frac_time_closed": frac["closed"],
            "frac_time_open": frac["open"],
            "frac_time_active": frac["active"],
            "ever_active": bool(active.any()),
            "max_abs_realisation_error_when_active_psi": (
                float(err.max()) if bool(active.any()) else None),
            "flow_mean_gpm": float(flow[v].mean()),
            "flow_max_abs_gpm": float(flow[v].abs().max()),
        }
    out["valves"] = valves
    out["swept_valve"] = valves[valve] if valve else None

    # --- tanks -------------------------------------------------------------
    out["tank_level_range_ft"] = {
        t: [float(C.m_to_ft((res.node["head"][t]
                            - wn.get_node(t).elevation).min())),
            float(C.m_to_ft((res.node["head"][t]
                            - wn.get_node(t).elevation).max()))]
        for t in wn.tank_name_list}
    return out


def run_case(label: str, prefix: str, valve: str | None,
             setting_psi: float | None, coeff_us, svc, conn, *,
             release_valve180_control: bool = False) -> dict:
    wn = build(setting_psi, valve,
               release_valve180_control=release_valve180_control)
    if coeff_us is not None:
        L.apply_leak(wn, coeff_us)
    solver = assert_solver(wn)
    echo = L.echo_check(wn, prefix)
    res, msgs, used_prefix = L._run_with_retry(wn, prefix)
    row = {
        "label": label,
        "swept_valve_name": valve,
        "setting_psi": setting_psi,
        "setting_ratio_of_nominal": (
            None if valve is None or setting_psi is None
            else setting_psi / NOMINAL_PSI[valve]),
        "valve180_control_released": release_valve180_control,
        "solver": solver,
        "echo_check": echo,
        "wntr_warnings": msgs,
        "report_scan": L._rpt_errors(used_prefix),
        "leak_applied": coeff_us is not None,
    }
    row.update(measure(wn, res, coeff_us, svc, conn, valve))
    return row


def main() -> dict:
    C.build_working_copy(verbose=False)
    wn0 = build(None, None)
    svc, conn = service_nodes(wn0)
    assert len(svc) == 121 and len(conn) == 5, (len(svc), len(conn))

    # Leak instrument, recomputed by the Phase 5 closed form from the same
    # baseline. Validation instrument only - see brief section 18.
    # The Phase 5 sizing target is 10 % of the mean system inflow of the
    # leak-free baseline run. The call is reproduced verbatim so the instrument
    # is identical to the one Phase 5 validated.
    base_p, base_inflow, weights = L.baseline_pressures("p6s3_size")
    sizing = L.leak_coefficients(weights, base_p,
                                 L.LEAK_TARGET_FRACTION * base_inflow)
    coeff_us = sizing["coefficient_gpm_per_psi_alpha"]

    cases: dict[str, dict] = {}

    ref = run_case("reference: all PRVs at nominal, leakage on, PDA",
                   "p6s3_ref", None, None, coeff_us, svc, conn)
    cases["reference_nominal"] = ref

    for valve in TARGETS:
        for s in GRIDS[valve]:
            key = f"{valve}@{s:g}psi"
            cases[key] = run_case(
                f"{valve} setting {s:g} psi "
                f"({s / NOMINAL_PSI[valve]:.3f} x nominal), other PRVs nominal",
                f"p6s3_{valve.split('-')[1]}_{s:g}".replace(".", "p"),
                valve, s, coeff_us, svc, conn)

    # VALVE-180 diagnostic: the [CONTROLS] statement removed, so the question
    # "is this valve inert, or is it merely commanded shut?" is answered by
    # measurement instead of inference. Reported, never silently adopted.
    for s in [16.45, 40.0, 80.0]:
        cases[f"VALVE-180@{s:g}psi_control_released"] = run_case(
            f"VALVE-180 setting {s:g} psi with its [CONTROLS] closure removed "
            "(diagnostic only; the benchmark control is retained everywhere else)",
            f"p6s3_180rel_{s:g}".replace(".", "p"),
            "VALVE-180", s, coeff_us, svc, conn,
            release_valve180_control=True)

    payload = {
        "phase": 6,
        "step": 3,
        "title": ("Fine characterisation of VALVE-179 / VALVE-174 / VALVE-180 "
                  "for action-space admission"),
        "env": C.env_info(),
        "scope_statement": (
            "Validation and characterisation only. No optimisation, no search, "
            "no reward tuning, no RL. Every number is produced by the EPANET "
            "solver from the working copy with native controls and rules "
            "untouched, except in the three explicitly labelled VALVE-180 "
            "diagnostic runs where the benchmark [CONTROLS] closure is removed "
            "and reported as such."),
        "solver_policy": {
            "accuracy": SOLVER_ACCURACY, "trials": SOLVER_TRIALS,
            "rule_timestep_s": RULE_TIMESTEP_S,
            "report_timestep_s": REPORT_TIMESTEP_S,
            "asserted_after_every_load": True,
            "note": ("Phase 5 g4_g5_prv.py did not set accuracy/trials and "
                     "inherited the file's 0.005/40, at which EPANET returns "
                     "states violating continuity by ~10 GPM while reporting "
                     "no error. That harness is deliberately not reused."),
        },
        "service_node_policy": {
            "rule": ("declared elevation exactly 0.0 ft AND zero total base "
                     "demand -> connector artefact, excluded from every "
                     "service and pressure statistic"),
            "n_service_junctions": len(svc),
            "n_connector_junctions": len(conn),
            "connector_nodes": conn,
        },
        "leak_instrument": {
            "status": ("VALIDATION INSTRUMENT, not a calibrated field leakage "
                       "model. Half-pipe-length weights, single closed-form "
                       "global scale, exponent 0.5 taken from the file's own "
                       "[OPTIONS] Emitter Exponent."),
            "sizing": {k: v for k, v in sizing.items()
                       if k != "coefficient_gpm_per_psi_alpha"},
            "coefficients_gpm_per_psi_alpha": coeff_us,
        },
        "grids_psi": GRIDS,
        "nominal_settings_psi": NOMINAL_PSI,
        "cases": cases,
    }
    out = C.REPO / "results" / "phase6"
    out.mkdir(parents=True, exist_ok=True)
    import json
    path = out / "p6_s3_prv_finechar.json"
    path.write_text(json.dumps(payload, indent=2, default=str),
                    encoding="utf-8")
    print(f"[written] {path}")
    return payload


if __name__ == "__main__":
    main()
