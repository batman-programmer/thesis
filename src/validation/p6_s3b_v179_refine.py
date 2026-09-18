"""Phase 6 / STEP 3b - sub-psi refinement of the VALVE-179 safety cliff, and
identification of the physical mechanism that produces it.

STEP 3a bracketed the cliff to a single psi: at 44 psi the valve is Active 80.8 %
of the horizon, carries 418 GPM mean, and leaves every service statistic at its
baseline value; at 45 psi 49 node-timesteps go negative with a minimum of
-96.98 psi and the demand satisfaction ratio falls from 0.9833 to 0.9703.

An action bound must not be placed by interpolation across that discontinuity,
so this module (a) refines the interval in 0.1 psi steps and (b) reports, for the
first setting that produces negative pressure, exactly which nodes go negative,
their elevations, at which timesteps, and what the valve is doing at those
timesteps. Without the mechanism the bound would be a curve-fit rather than a
physical statement.

No optimisation. The grid is fixed before the runs and reported in the artefact.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import phase5_common as C  # noqa: E402
import g6_g7_g8_leak_pda as L  # noqa: E402
import p6_s3_prv_finechar as S3  # noqa: E402

VALVE = "VALVE-179"

# Fixed before execution. 0.1 psi is finer than any actuator in the field could
# be commanded, so refining further would characterise the solver rather than
# the network.
REFINE_PSI = [44.0, 44.1, 44.2, 44.3, 44.4, 44.5,
              44.6, 44.7, 44.8, 44.9, 45.0]

# Settings whose full spatial/temporal detail is dumped for the mechanism study:
# the last safe integer setting, the refined boundary neighbourhood, and the
# first clearly unsafe integer setting.
MECHANISM_PSI = [44.0, 45.0, 46.0]


def detail(wn, res, svc, valve) -> dict:
    """Where and when the negative pressures occur, and what the valve does."""
    p = C.m_to_psi(res.node["pressure"][svc])
    neg_nodes = [j for j in svc if bool((p[j] < 0.0).any())]
    st = res.link["status"][valve]
    q = C.m3s_to_gpm(res.link["flowrate"][valve])
    dn = wn.get_link(valve).end_node_name
    up = wn.get_link(valve).start_node_name

    rows = {}
    for j in neg_nodes:
        mask = p[j] < 0.0
        t_neg = [float(t) for t in p.index[mask]]
        rows[j] = {
            "elevation_ft": float(C.m_to_ft(wn.get_node(j).elevation)),
            "base_demand_gpm": float(C.m3s_to_gpm(
                sum(d.base_value for d in wn.get_node(j)
                    .demand_timeseries_list))),
            "n_timesteps_negative": int(mask.sum()),
            "min_psi": float(p[j].min()),
            "mean_psi": float(p[j].mean()),
            "first_negative_time_h": t_neg[0] / 3600.0 if t_neg else None,
            "last_negative_time_h": t_neg[-1] / 3600.0 if t_neg else None,
            "valve_status_at_negative_times": sorted(
                {int(x) for x in st[mask]}),
            "valve_flow_gpm_at_negative_times": [
                float(x) for x in q[mask].head(6)],
            "hops_from_valve_downstream_node": None,  # filled by caller
        }

    # Graph distance from the valve's downstream node, so "the damage is local
    # to the zone the valve feeds" is a measurement rather than an assertion.
    import networkx as nx
    g = wn.to_graph().to_undirected()
    try:
        dist = nx.single_source_shortest_path_length(g, dn)
    except Exception:  # pragma: no cover - diagnostic only
        dist = {}
    for j in rows:
        rows[j]["hops_from_valve_downstream_node"] = dist.get(j)

    return {
        "valve_upstream_node": up,
        "valve_downstream_node": dn,
        "n_service_nodes_ever_negative": len(neg_nodes),
        "nodes_ever_negative": rows,
        "valve_downstream_pressure_min_psi": float(
            C.m_to_psi(res.node["pressure"][dn]).min()),
        "valve_upstream_pressure_min_psi": float(
            C.m_to_psi(res.node["pressure"][up]).min()),
        "valve_status_fractions": {
            lbl: float((st == code).sum()) / max(len(st), 1)
            for code, lbl in ((0, "closed"), (1, "open"), (2, "active"))},
        "valve_flow_max_abs_gpm": float(q.abs().max()),
    }


def main() -> dict:
    C.build_working_copy(verbose=False)
    wn0 = S3.build(None, None)
    svc, conn = S3.service_nodes(wn0)
    assert len(svc) == 121 and len(conn) == 5

    base_p, base_inflow, weights = L.baseline_pressures("p6s3b_size")
    sizing = L.leak_coefficients(weights, base_p,
                                 L.LEAK_TARGET_FRACTION * base_inflow)
    coeff_us = sizing["coefficient_gpm_per_psi_alpha"]

    cases: dict[str, dict] = {}
    for s in REFINE_PSI:
        key = f"{VALVE}@{s:g}psi"
        prefix = f"p6s3b_{s:g}".replace(".", "p")
        row = S3.run_case(f"{VALVE} setting {s:g} psi, other PRVs nominal",
                          prefix, VALVE, s, coeff_us, svc, conn)
        cases[key] = row

    mech: dict[str, dict] = {}
    for s in MECHANISM_PSI:
        wn = S3.build(s, VALVE)
        L.apply_leak(wn, coeff_us)
        S3.assert_solver(wn)
        res, msgs, _ = L._run_with_retry(wn, f"p6s3bm_{s:g}".replace(".", "p"))
        mech[f"{VALVE}@{s:g}psi"] = {"wntr_warnings": msgs,
                                     **detail(wn, res, svc, VALVE)}

    # The last setting at which no service node ever goes negative and no
    # service statistic departs from the reference. Read off the runs, not
    # assumed: reported together with the first setting that fails.
    safe = [s for s in REFINE_PSI
            if cases[f"{VALVE}@{s:g}psi"]["n_node_timesteps_negative"] == 0]
    unsafe = [s for s in REFINE_PSI
              if cases[f"{VALVE}@{s:g}psi"]["n_node_timesteps_negative"] > 0]

    payload = {
        "phase": 6,
        "step": "3b",
        "title": ("Sub-psi refinement of the VALVE-179 safety cliff and its "
                  "physical mechanism"),
        "env": C.env_info(),
        "scope_statement": (
            "Characterisation only. The grid was fixed before execution. No "
            "optimisation, no search, no reward, no RL. Native controls, rules "
            "and topology untouched in every run."),
        "solver_policy": {"accuracy": S3.SOLVER_ACCURACY,
                          "trials": S3.SOLVER_TRIALS,
                          "rule_timestep_s": S3.RULE_TIMESTEP_S,
                          "report_timestep_s": S3.REPORT_TIMESTEP_S},
        "refine_grid_psi": REFINE_PSI,
        "mechanism_grid_psi": MECHANISM_PSI,
        "nominal_setting_psi": S3.NOMINAL_PSI[VALVE],
        "highest_setting_with_no_negative_pressure_psi": (
            max(safe) if safe else None),
        "lowest_setting_with_negative_pressure_psi": (
            min(unsafe) if unsafe else None),
        "cases": cases,
        "mechanism": mech,
    }
    out = C.REPO / "results" / "phase6"
    out.mkdir(parents=True, exist_ok=True)
    path = out / "p6_s3b_v179_refine.json"
    path.write_text(json.dumps(payload, indent=2, default=str),
                    encoding="utf-8")
    print(f"[written] {path}")
    return payload


if __name__ == "__main__":
    main()
