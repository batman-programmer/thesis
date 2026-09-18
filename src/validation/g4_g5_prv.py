"""Gates 4 and 5 - PRV actuator responsiveness and action-dimension audit.

Each of the eight native PRVs is perturbed on its own, deterministically, over a
fixed absolute setting grid. No optimisation, no GA, no search: the grid is
declared here and every run is reported, including the ones that show no effect.

No PRV is added, removed or relocated. Gate 5 produces evidence about which
action dimensions carry leverage; it does not delete any of them.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import phase5_common as C  # noqa: E402

VALVES = ["VALVE-173", "VALVE-174", "VALVE-175", "VALVE-176",
          "VALVE-177", "VALVE-178", "VALVE-179", "VALVE-180"]
NOMINAL_PSI = {"VALVE-173": 70.0, "VALVE-174": 80.0, "VALVE-175": 55.0,
               "VALVE-176": 29.762, "VALVE-177": 45.0, "VALVE-178": 37.0,
               "VALVE-179": 40.0, "VALVE-180": 16.45}
# Absolute grid in psi. Spans well below and well above every nominal setting so
# that both ends of the saturation envelope are observed for every valve.
GRID_PSI = [5.0, 10.0, 15.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 100.0, 120.0]
EPS_FACTORS = [0.5, 1.0, 1.5]


def status_label(v: float) -> str:
    try:
        from wntr.network.base import LinkStatus

        return LinkStatus(int(v)).name
    except Exception:
        return f"code {v}"


def _rpt_errors(prefix: str) -> int | None:
    rpt = C.RESULTS / "_tmp" / f"{prefix}.rpt"
    if not rpt.exists():
        return None
    txt = rpt.read_text(encoding="utf-8", errors="replace")
    return sum(1 for ln in txt.splitlines() if "Error" in ln or "ERROR" in ln)
def prv_snapshot(setting_psi: dict[str, float], prefix: str) -> dict:
    """Single-period run with the given PRV settings. Tanks are fixed-head, so
    the observed response is the valve's own hydraulic effect only."""
    wn = C.load_wn(rule_timestep=180)
    wn.options.time.duration = 0
    wn.options.time.report_timestep = 0
    for v, s in setting_psi.items():
        wn.get_link(v).initial_setting = C.psi_to_m(s)
    res, msgs = C.run_epanet(wn, prefix)

    pj = res.node["pressure"][[j for j in wn.junction_name_list]]
    out = {
        "settings_commanded_psi": setting_psi,
        "wntr_warnings": msgs,
        "report_scan_errors": _rpt_errors(prefix),
        "pressure_psi": {j: float(C.m_to_psi(pj.iloc[0][j])) for j in pj.columns},
        "min_junction_pressure_psi": float(C.m_to_psi(pj.iloc[0].min())),
        "min_at_node": str(pj.iloc[0].idxmin()),
        "mean_junction_pressure_psi": float(C.m_to_psi(pj.iloc[0].mean())),
        "valves": {},
    }
    for v in wn.valve_name_list:
        link = wn.get_link(v)
        up, dn = link.start_node_name, link.end_node_name
        st = float(res.link["status"][v].iloc[0])
        cmd = setting_psi.get(v, float(C.m_to_psi(link.initial_setting)))
        p_dn = float(C.m_to_psi(res.node["pressure"][dn].iloc[0]))
        p_up = float(C.m_to_psi(res.node["pressure"][up].iloc[0]))
        out["valves"][v] = {
            "upstream_node": up, "downstream_node": dn,
            "setting_commanded_psi": cmd,
            "status": st, "status_label": status_label(st),
            "pressure_upstream_psi": p_up,
            "pressure_downstream_psi": p_dn,
            "realised_minus_commanded_psi": p_dn - cmd,
            "regulating": status_label(st) == "Active",
            "flow_gpm": float(C.m3s_to_gpm(res.link["flowrate"][v].iloc[0])),
            "headloss_ft": float(C.m_to_ft(
                res.node["head"][up].iloc[0] - res.node["head"][dn].iloc[0])),
        }
    return out


def prv_eps(setting_psi: dict[str, float], prefix: str) -> dict:
    """96 h run with the given PRV settings, native controls untouched."""
    wn = C.load_wn(rule_timestep=180, report_timestep=1800)
    for v, s in setting_psi.items():
        wn.get_link(v).initial_setting = C.psi_to_m(s)
    res, msgs = C.run_epanet(wn, prefix)
    pj = res.node["pressure"][[j for j in wn.junction_name_list]]
    out = {
        "settings_commanded_psi": setting_psi,
        "wntr_warnings": msgs,
        "report_scan_errors": _rpt_errors(prefix),
        "n_timesteps": int(len(pj.index)),
        "min_junction_pressure_psi": float(C.m_to_psi(pj.min().min())),
        "mean_junction_pressure_psi": float(C.m_to_psi(pj.stack().mean())),
        "n_negative_node_timesteps": int((pj < 0).sum().sum()),
        "n_node_timesteps_below_20psi": int((pj < C.psi_to_m(20.0)).sum().sum()),
        "mean_pressure_by_node_psi": {j: float(C.m_to_psi(pj[j].mean())) for j in pj.columns},
        "valves": {},
    }
    for v in wn.valve_name_list:
        link = wn.get_link(v)
        st = res.link["status"][v]
        q = C.m3s_to_gpm(res.link["flowrate"][v])
        p_dn = C.m_to_psi(res.node["pressure"][link.end_node_name])
        cmd = setting_psi.get(v, float(C.m_to_psi(link.initial_setting)))
        labels = [status_label(x) for x in st]
        out["valves"][v] = {
            "setting_commanded_psi": cmd,
            "frac_time_active": float(sum(1 for x in labels if x == "Active") / len(labels)),
            "frac_time_open": float(sum(1 for x in labels if x == "Open") / len(labels)),
            "frac_time_closed": float(sum(1 for x in labels if x == "Closed") / len(labels)),
            "states_observed": sorted(set(labels)),
            "flow_mean_gpm": float(q.mean()),
            "flow_max_gpm": float(q.max()),
            "downstream_pressure_mean_psi": float(p_dn.mean()),
            "max_abs_realisation_error_when_active_psi": (
                float((p_dn - cmd).abs()[[x == "Active" for x in labels]].max())
                if any(x == "Active" for x in labels) else None),
        }
    for t in wn.tank_name_list:
        lev = res.node["head"][t] - wn.get_node(t).elevation
        out.setdefault("tanks", {})[t] = {
            "level_min_ft": float(C.m_to_ft(lev.min())),
            "level_max_ft": float(C.m_to_ft(lev.max())),
            "emptied": bool(lev.min() <= wn.get_node(t).min_level + 1e-9),
        }
    return out
def main() -> dict:
    ref = prv_snapshot({}, "g4_ref")
    base_p = ref["pressure_psi"]

    sweep: dict[str, list] = {}
    for v in VALVES:
        rows = []
        for s in sorted(set(GRID_PSI + [NOMINAL_PSI[v]])):
            tag = f"g4_{v.split('-')[1]}_{int(round(s*10)):04d}"
            r = prv_snapshot({v: s}, tag)
            vd = r["valves"][v]
            dp = {j: r["pressure_psi"][j] - base_p[j] for j in base_p}
            moved = {j: d for j, d in dp.items() if abs(d) > 0.01}
            vd.update({
                "is_nominal": abs(s - NOMINAL_PSI[v]) < 1e-9,
                "network_min_pressure_psi": r["min_junction_pressure_psi"],
                "network_mean_pressure_psi": r["mean_junction_pressure_psi"],
                "n_junctions_moved_gt_0p01psi": len(moved),
                "n_junctions_moved_gt_1psi": sum(1 for d in dp.values() if abs(d) > 1.0),
                "max_abs_dP_psi": max(abs(d) for d in dp.values()),
                "max_abs_dP_node": max(dp, key=lambda j: abs(dp[j])),
                "influenced_nodes": sorted(moved),
                "report_scan_errors": r["report_scan_errors"],
            })
            rows.append(vd)
        sweep[v] = rows

    # Gate 4 per-valve summary.
    g4 = {}
    for v, rows in sweep.items():
        act = [r for r in rows if r["regulating"]]
        nom = next(r for r in rows if r["is_nominal"])
        p_dn = [r["pressure_downstream_psi"] for r in rows]
        q = [r["flow_gpm"] for r in rows]
        # Responsiveness sub-criteria are reported separately and combined with OR.
        # Under a demand-driven snapshot the nodal demands are fixed, so a PRV that
        # is the sole supply path into a zone passes exactly that zone's demand at
        # every setting. Flow invariance is then the expected physics and is not
        # evidence of an unresponsive actuator; the pressure field is.
        resp_p = max(r["max_abs_dP_psi"] for r in rows) > 0.5
        resp_q = (max(q) - min(q)) > 1.0
        resp_dn = (max(p_dn) - min(p_dn)) > 1.0
        g4[v] = {
            "nominal_setting_psi": NOMINAL_PSI[v],
            "upstream_node": nom["upstream_node"],
            "downstream_node": nom["downstream_node"],
            "settings_tested_psi": [r["setting_commanded_psi"] for r in rows],
            "status_at_nominal": nom["status_label"],
            "n_settings_regulating": len(act),
            "n_settings_saturated_open": sum(1 for r in rows if r["status_label"] == "Open"),
            "n_settings_saturated_closed": sum(1 for r in rows if r["status_label"] == "Closed"),
            "regulating_setting_range_psi": (
                [min(r["setting_commanded_psi"] for r in act),
                 max(r["setting_commanded_psi"] for r in act)] if act else None),
            "downstream_pressure_span_psi": max(p_dn) - min(p_dn),
            "flow_span_gpm": max(q) - min(q),
            "flow_range_gpm": [min(q), max(q)],
            "max_abs_realisation_error_when_active_psi": (
                max(abs(r["realised_minus_commanded_psi"]) for r in act) if act else None),
            "max_network_influence_psi": max(r["max_abs_dP_psi"] for r in rows),
            "max_n_junctions_influenced": max(r["n_junctions_moved_gt_0p01psi"] for r in rows),
            "influence_union_nodes": sorted({n for r in rows for n in r["influenced_nodes"]}),
            "responds_network_pressure_gt_0p5psi": bool(resp_p),
            "responds_downstream_pressure_gt_1psi": bool(resp_dn),
            "responds_flow_gt_1gpm": bool(resp_q),
            "meaningful": bool(resp_p or resp_q),
        }

    eps: dict[str, dict] = {}
    eps["nominal"] = prv_eps({}, "g4_eps_nominal")
    for v in VALVES:
        for f in EPS_FACTORS:
            if f == 1.0:
                continue
            s = round(NOMINAL_PSI[v] * f, 4)
            eps[f"{v}_x{f}"] = prv_eps({v: s}, f"g4_eps_{v.split('-')[1]}_{int(f*100)}")
    base_eps = eps["nominal"]["mean_pressure_by_node_psi"]
    eps_influence = {}
    for k, r in eps.items():
        if k == "nominal":
            continue
        d = {j: r["mean_pressure_by_node_psi"][j] - base_eps[j] for j in base_eps}
        eps_influence[k] = {
            "max_abs_mean_dP_psi": max(abs(x) for x in d.values()),
            "n_junctions_mean_moved_gt_0p5psi": sum(1 for x in d.values() if abs(x) > 0.5),
            "network_mean_dP_psi": r["mean_junction_pressure_psi"]
                                   - eps["nominal"]["mean_junction_pressure_psi"],
            "network_min_pressure_psi": r["min_junction_pressure_psi"],
            "n_negative_node_timesteps": r["n_negative_node_timesteps"],
            "n_below_20psi": r["n_node_timesteps_below_20psi"],
            "report_scan_errors": r["report_scan_errors"],
        }
    # Perturbations that drove the 96 h run into physically invalid territory.
    unsafe = {k: {"min_pressure_psi": e["network_min_pressure_psi"],
                  "n_negative_node_timesteps": e["n_negative_node_timesteps"]}
              for k, e in eps_influence.items() if e["n_negative_node_timesteps"] > 0}
    # ---- Gate 5: action-dimension audit (evidence only, nothing removed) ----
    nominal_eps = eps["nominal"]["valves"]
    total_demand_gpm = 944.710  # from Gate 0, [JUNCTIONS] base demands
    audit = {}
    for v in VALVES:
        s = g4[v]
        n = nominal_eps[v]
        ei = [eps_influence[k]["max_abs_mean_dP_psi"]
              for k in eps_influence if k.startswith(v + "_")]
        audit[v] = {
            "nominal_setting_psi": NOMINAL_PSI[v],
            "baseline_state_over_96h": n["states_observed"],
            "baseline_frac_time_active": n["frac_time_active"],
            "baseline_frac_time_closed": n["frac_time_closed"],
            "baseline_flow_mean_gpm": n["flow_mean_gpm"],
            "baseline_flow_share_of_demand_pct": n["flow_mean_gpm"] / total_demand_gpm * 100.0,
            "snapshot_settings_regulating": s["n_settings_regulating"],
            "snapshot_settings_saturated_closed": s["n_settings_saturated_closed"],
            "snapshot_settings_saturated_open": s["n_settings_saturated_open"],
            "snapshot_max_network_influence_psi": s["max_network_influence_psi"],
            "snapshot_downstream_pressure_span_psi": s["downstream_pressure_span_psi"],
            "snapshot_flow_span_gpm": s["flow_span_gpm"],
            "snapshot_n_junctions_influenced": s["max_n_junctions_influenced"],
            "eps_max_mean_dP_psi_over_tested_factors": max(ei) if ei else None,
            "responds_to_setting_change": s["meaningful"],
            "classification": None,
            "evidence_note": None,
        }
    for v, a in audit.items():
        if a["baseline_flow_mean_gpm"] == 0.0 and not a["responds_to_setting_change"]:
            a["classification"] = "INERT in the distributed baseline"
            a["evidence_note"] = (
                "Zero flow at every timestep of the 96 h baseline and no measurable "
                "pressure response to any tested setting. An action dimension on this "
                "valve would be unobservable in the baseline configuration.")
        elif a["baseline_flow_mean_gpm"] == 0.0:
            a["classification"] = "CLOSED in baseline but responsive when reopened"
            a["evidence_note"] = (
                "Carries no flow at the nominal setting, yet the sweep shows a hydraulic "
                "response at other settings, so the dimension is recoverable rather than "
                "structurally dead.")
        elif a["baseline_flow_share_of_demand_pct"] < 1.0:
            a["classification"] = "LOW-LEVERAGE"
            a["evidence_note"] = (
                "Regulates, but carries under 1 % of system base demand, so its "
                "contribution to network-wide leakage or service is small.")
        elif a["snapshot_max_network_influence_psi"] < 1.0:
            a["classification"] = "LOCAL-ONLY"
            a["evidence_note"] = (
                "Carries meaningful flow but its setting moves no junction pressure by "
                "more than 1 psi.")
        else:
            a["classification"] = "ACTIVE, HIGH-LEVERAGE"
            a["evidence_note"] = (
                "Regulates at the nominal setting, carries a material share of demand, "
                "and its setting moves the pressure field measurably.")

    inert = [v for v, a in audit.items() if a["classification"].startswith("INERT")]
    responsive = [v for v, a in audit.items() if a["responds_to_setting_change"]]
    g4_verdict = ("PASS" if len(responsive) >= 6 else
                  "CONDITIONAL" if len(responsive) >= 3 else "FAIL")
    g5_verdict = "CONDITIONAL" if inert else "PASS"
    payload = {
        "gate": "G4+G5",
        "title": "PRV actuator responsiveness and action-dimension audit",
        "env": C.env_info(),
        "method": {
            "grid_psi": GRID_PSI,
            "eps_factors_of_nominal": EPS_FACTORS,
            "primary": ("Single-period snapshot per valve per setting, one valve varied at a "
                        "time, all others at their distributed settings."),
            "secondary": ("96 h EPS at 0.5x and 1.5x the nominal setting per valve, native "
                          "controls untouched."),
            "no_optimisation": ("The grid is fixed and declared in advance. No GA, no search, "
                                "no placement change, no valve added or removed."),
            "saturation_definition": (
                "Active = the PRV is regulating and holds its downstream node at the setting. "
                "Open = the setting is above what the upstream head can produce, so the valve "
                "is not binding. Closed = EPANET shut it to prevent reverse flow."),
            "responsiveness_criterion": (
                "A valve counts as responsive if EITHER the network pressure field moves by "
                "more than 0.5 psi at some node OR its own flow moves by more than 1 GPM "
                "across the grid. The two sub-criteria are reported separately. An AND rule "
                "would be wrong here: the runs are demand-driven, so a PRV that is the only "
                "supply path into a zone must pass exactly that zone's fixed demand at every "
                "setting, and its flow is invariant by construction rather than by any lack "
                "of actuator authority."),
        },
        "nominal_settings_psi": NOMINAL_PSI,
        "reference_snapshot": {k: v for k, v in ref.items() if k != "pressure_psi"},
        "snapshot_sweep": sweep,
        "gate4_per_valve": g4,
        "eps_runs": {k: {kk: vv for kk, vv in v.items()
                         if kk != "mean_pressure_by_node_psi"} for k, v in eps.items()},
        "eps_influence": eps_influence,
        "eps_perturbations_producing_negative_pressure": unsafe,
        "gate5_audit": audit,
        "gate5_note": ("No PRV is removed, disabled or relocated by this gate. The "
                       "classification is evidence for a later design decision."),
        "verdicts": {
            "g4": f"G4 PRV ACTUATOR RESPONSIVENESS = {g4_verdict}",
            "g5": f"G5 PRV ACTION-DIMENSION AUDIT = {g5_verdict}",
        },
    }
    C.jdump("g4_g5_prv.json", payload)

    print("\n--- G4 per-valve single-period sweep ---------------------------")
    hdr = (f"{'valve':<10} {'nom':>7} {'regul':>6} {'satO':>5} {'satC':>5} {'regRange':>14} "
           f"{'q_range_gpm':>18} {'dPdn':>7} {'maxdP':>7} {'nJunc':>6} {'realErr':>8} "
           f"{'meaningful':>11}")
    print(hdr)
    for v in VALVES:
        s = g4[v]
        rr = (f"{s['regulating_setting_range_psi'][0]:.1f}-{s['regulating_setting_range_psi'][1]:.1f}"
              if s["regulating_setting_range_psi"] else "none")
        re_ = (f"{s['max_abs_realisation_error_when_active_psi']:.2e}"
               if s["max_abs_realisation_error_when_active_psi"] is not None else "-")
        print(f"{v:<10} {s['nominal_setting_psi']:7.3f} {s['n_settings_regulating']:6d} "
              f"{s['n_settings_saturated_open']:5d} {s['n_settings_saturated_closed']:5d} "
              f"{rr:>14} {s['flow_range_gpm'][0]:8.2f}-{s['flow_range_gpm'][1]:<9.2f} "
              f"{s['downstream_pressure_span_psi']:7.3f} "
              f"{s['max_network_influence_psi']:7.3f} {s['max_n_junctions_influenced']:6d} "
              f"{re_:>8} {str(s['meaningful']):>11}")

    print("\n--- G5 action-dimension audit (evidence only) ------------------")
    for v in VALVES:
        a = audit[v]
        print(f"  {v:<10} {a['classification']}")
        print(f"      96h states={a['baseline_state_over_96h']} active={a['baseline_frac_time_active']:.2f} "
              f"closed={a['baseline_frac_time_closed']:.2f} q={a['baseline_flow_mean_gpm']:.2f} GPM "
              f"({a['baseline_flow_share_of_demand_pct']:.2f} % of demand)")
        print(f"      snapshot: regulating at {a['snapshot_settings_regulating']} settings, "
              f"maxdP={a['snapshot_max_network_influence_psi']:.3f} psi over "
              f"{a['snapshot_n_junctions_influenced']} junctions; EPS maxdP="
              f"{a['eps_max_mean_dP_psi_over_tested_factors']}")

    print("\n--- EPS sensitivity to +-50 % of nominal setting ----------------")
    for k in sorted(eps_influence):
        e = eps_influence[k]
        print(f"  {k:<20} meandP_net={e['network_mean_dP_psi']:+8.4f} psi  "
              f"maxdP={e['max_abs_mean_dP_psi']:8.4f} psi  "
              f"nJunc>0.5psi={e['n_junctions_mean_moved_gt_0p5psi']:3d}  "
              f"minP={e['network_min_pressure_psi']:7.3f}  <20psi={e['n_below_20psi']:4d}  "
              f"err={e['report_scan_errors']}")
    print(f"\nvalves inert in the distributed baseline: {inert or 'none'}")
    print(f"perturbations giving negative pressure: {sorted(unsafe) or 'none'}")
    print(f"{payload['verdicts']['g4']}")
    print(f"{payload['verdicts']['g5']}")
    return payload


if __name__ == "__main__":
    main()




