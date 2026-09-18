"""Gates 1, 2 and 11 - baseline convergence, native control logic, tank dynamics.

The model is run exactly as distributed: no leakage, no demand-model change, no
actuator override. The only deviations from a naive WNTR run are the two runtime
notes recorded in phase5_common.RUNTIME_NOTES (native rule timestep restored;
optional finer reporting), both of which are logged with the run.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import phase5_common as C  # noqa: E402

RPT_FLAGS = ("WARNING", "Error", "ERROR", "unbalanced", "negative pressures",
             "cannot deliver", "disconnected", "closed because", "open because",
             "emptied", "full")


def scan_report(prefix: str) -> dict:
    """Parse the EPANET .rpt written by the run for engine-level messages."""
    rpt = C.RESULTS / "_tmp" / f"{prefix}.rpt"
    if not rpt.exists():
        return {"rpt_found": False}
    lines = rpt.read_text(encoding="utf-8", errors="replace").splitlines()
    flagged = [ln.strip() for ln in lines
               if any(f in ln for f in RPT_FLAGS) and ln.strip()]
    return {
        "rpt_found": True,
        "rpt_path": str(rpt),
        "n_lines": len(lines),
        "n_flagged_lines": len(flagged),
        "flagged_lines": flagged[:200],
        "n_errors": sum(1 for ln in flagged if "Error" in ln or "ERROR" in ln),
        "n_warnings": sum(1 for ln in flagged if "WARNING" in ln),
    }
def summarise_run(wn, res, msgs, prefix: str) -> dict:
    """Convert one EPANET run into an auditable, unit-explicit summary."""
    import pandas as pd

    p = res.node["pressure"]
    junc = [n for n in wn.junction_name_list if n in p.columns]
    pj = p[junc]
    out: dict = {
        "n_timesteps_returned": int(len(p.index)),
        "t_first_s": float(p.index[0]),
        "t_last_s": float(p.index[-1]),
        "report_timestep_s": wn.options.time.report_timestep,
        "hydraulic_timestep_s": wn.options.time.hydraulic_timestep,
        "rule_timestep_s": wn.options.time.rule_timestep,
        "duration_s": wn.options.time.duration,
        "wntr_warnings": msgs,
        "report_scan": scan_report(prefix),
    }

    pmin_node = pj.min().idxmin()
    pmax_node = pj.max().idxmax()
    out["pressure_junctions_psi"] = {
        "min": float(C.m_to_psi(pj.min().min())),
        "min_at_node": pmin_node,
        "min_at_time_s": float(pj[pmin_node].idxmin()),
        "max": float(C.m_to_psi(pj.max().max())),
        "max_at_node": pmax_node,
        "max_at_time_s": float(pj[pmax_node].idxmax()),
        "mean": float(C.m_to_psi(pj.stack().mean())),
        "n_node_timesteps": int(pj.size),
        "n_negative": int((pj < 0).sum().sum()),
        "n_below_20psi": int((pj < C.psi_to_m(20.0)).sum().sum()),
        "nodes_ever_negative": sorted(pj.columns[(pj < 0).any()].tolist()),
        "nodes_ever_below_20psi": sorted(pj.columns[(pj < C.psi_to_m(20.0)).any()].tolist()),
    }

    tanks = {}
    for t in wn.tank_name_list:
        node = wn.get_node(t)
        lev = res.node["head"][t] - node.elevation
        tanks[t] = {
            "elevation_ft": float(C.m_to_ft(node.elevation)),
            "init_level_ft": float(C.m_to_ft(node.init_level)),
            "min_level_ft": float(C.m_to_ft(node.min_level)),
            "max_level_ft": float(C.m_to_ft(node.max_level)),
            "diameter_ft": float(C.m_to_ft(node.diameter)),
            "level_min_ft": float(C.m_to_ft(lev.min())),
            "level_max_ft": float(C.m_to_ft(lev.max())),
            "level_first_ft": float(C.m_to_ft(lev.iloc[0])),
            "level_last_ft": float(C.m_to_ft(lev.iloc[-1])),
            "level_range_ft": float(C.m_to_ft(lev.max() - lev.min())),
            "hit_min_level": bool(lev.min() <= node.min_level + 1e-9),
            "exceeded_max_level": bool(lev.max() > node.max_level + 1e-9),
            "went_negative": bool(lev.min() < -1e-9),
            "net_level_change_ft": float(C.m_to_ft(lev.iloc[-1] - lev.iloc[0])),
        }
    out["tanks"] = tanks

    links = {}
    st = res.link["status"]
    fl = res.link["flowrate"]
    for lname in wn.pump_name_list + wn.valve_name_list:
        s = st[lname]
        switches = int((s.diff().fillna(0) != 0).sum())
        links[lname] = {
            "type": wn.get_link(lname).link_type,
            "status_initial": float(s.iloc[0]),
            "status_final": float(s.iloc[-1]),
            "n_status_changes": switches,
            "frac_time_open": float((s > 0).mean()),
            "distinct_status_values": sorted(set(float(x) for x in s.unique())),
            "flow_min_gpm": float(C.m3s_to_gpm(fl[lname].min())),
            "flow_max_gpm": float(C.m3s_to_gpm(fl[lname].max())),
            "flow_mean_gpm": float(C.m3s_to_gpm(fl[lname].mean())),
        }
        if lname in wn.valve_name_list:
            links[lname]["setting_psi"] = float(C.m_to_psi(wn.get_link(lname).initial_setting))
    out["pumps_and_valves"] = links
    out["pump_energy"] = _pump_energy(wn, res)
    return out


def _pump_energy(wn, res) -> dict:
    """Pump shaft power and energy from the EPANET results.

    wntr.metrics.pump_power returns W; wntr.metrics.pump_energy returns J
    (power x report_timestep). Both use wn.options.energy.global_efficiency,
    which the file sets to 75 %.
    """
    try:
        import wntr

        pw = wntr.metrics.pump_power(res.link["flowrate"], res.node["head"], wn)
        en = wntr.metrics.pump_energy(res.link["flowrate"], res.node["head"], wn)
        out = {"global_efficiency_pct": wn.options.energy.global_efficiency}
        for p in wn.pump_name_list:
            out[p] = {
                "power_mean_kW": float(pw[p].mean()) / 1e3,
                "power_max_kW": float(pw[p].max()) / 1e3,
                "power_when_running_mean_kW": (
                    float(pw[p][res.link["status"][p] > 0].mean()) / 1e3
                    if (res.link["status"][p] > 0).any() else 0.0),
                "energy_total_kWh": float(en[p].sum()) / 3.6e6,
            }
        return out
    except Exception as exc:
        return {"unavailable": f"{type(exc).__name__}: {exc}"}

def status_label(v: float) -> str:
    try:
        from wntr.network.base import LinkStatus

        return LinkStatus(int(v)).name
    except Exception:
        return f"code {v}"


def native_controls(wn, res) -> dict:
    """Gate 2 - what the distributed file controls, and whether it really fires."""
    sec = C.read_sections(C.ORIGINAL_INP)
    st = res.link["status"]
    rows = []

    # Map each rule to the pump it acts on, from the raw [RULES] text.
    rule_text: dict[str, list[str]] = {}
    cur = None
    for ln in sec.get("RULES", []):
        t = ln.split()
        if t[0].upper() == "RULE":
            cur = t[1]
            rule_text[cur] = []
        elif cur:
            rule_text[cur].append(ln)

    acted_on: dict[str, list[str]] = {}
    for rid, body in rule_text.items():
        for ln in body:
            t = ln.split()
            if len(t) >= 3 and t[0].upper() in ("THEN", "ELSE") and t[1].upper() in ("LINK", "PUMP", "VALVE"):
                acted_on.setdefault(t[2], []).append(rid)
            elif len(t) >= 3 and t[0].upper() == "THEN" and t[1].upper() == "PUMP":
                acted_on.setdefault(t[2], []).append(rid)
    # BWSN-1 writes 'THEN PUMP-170 STATUS IS CLOSED' (no LINK keyword), so also
    # match any token that is a known link id.
    known_links = set(wn.link_name_list)
    for rid, body in rule_text.items():
        for ln in body:
            for tok in ln.split():
                if tok in known_links:
                    acted_on.setdefault(tok, [])
                    if rid not in acted_on[tok]:
                        acted_on[tok].append(rid)

    control_lines = list(sec.get("CONTROLS", []))
    for lname in wn.pump_name_list + wn.valve_name_list:
        s = st[lname]
        rules = acted_on.get(lname, [])
        ctrls = [ln for ln in control_lines if lname in ln.split()]
        native = []
        if rules:
            native.append(f"[RULES] {', '.join(rules)}")
        if ctrls:
            native.append(f"[CONTROLS] {'; '.join(ctrls)}")
        if not native:
            native.append("none (uncontrolled)")
        trigger = []
        for rid in rules:
            for ln in rule_text[rid]:
                t = ln.split()
                if t[0].upper() in ("IF", "AND", "OR"):
                    trigger.append(" ".join(t))
        for ln in ctrls:
            trigger.append(ln)
        changes = s.index[s.diff().fillna(0) != 0].tolist()
        rows.append({
            "element": lname,
            "type": wn.get_link(lname).link_type,
            "native_control": " + ".join(native),
            "trigger": trigger or ["-"],
            "initial_state": status_label(s.iloc[0]),
            "final_state": status_label(s.iloc[-1]),
            "states_observed": sorted({status_label(x) for x in s.unique()}),
            "n_switches_over_run": len(changes),
            "switch_times_s": [float(x) for x in changes[:40]],
            "active_in_baseline": bool(len(changes) > 0 or s.iloc[0] != 0),
            "frac_time_open": float((s > 0).mean()),
        })
    return {
        "rules_raw": rule_text,
        "controls_raw": control_lines,
        "table": rows,
        "rule_timestep_used_s": wn.options.time.rule_timestep,
    }


def switch_evidence(wn, res) -> dict:
    """Do the tank-level rules fire at the levels the file declares?"""
    st = res.link["status"]
    ev = {}
    pairs = {"PUMP-170": "TANK-131", "PUMP-172": "TANK-130"}
    for pump, tank in pairs.items():
        if pump not in st.columns or tank not in wn.tank_name_list:
            ev[pump] = "UNKNOWN - element absent"
            continue
        lev = res.node["head"][tank] - wn.get_node(tank).elevation
        s = st[pump]
        idx = s.index[s.diff().fillna(0) != 0].tolist()
        ev[pump] = {
            "driving_tank": tank,
            "events": [
                {"t_s": float(t), "new_status": status_label(s.loc[t]),
                 "tank_level_ft": float(C.m_to_ft(lev.loc[t]))}
                for t in idx[:40]
            ],
            "tank_level_when_open_ft": [
                float(C.m_to_ft(lev.loc[t])) for t in idx if s.loc[t] > 0
            ][:40],
            "tank_level_when_closed_ft": [
                float(C.m_to_ft(lev.loc[t])) for t in idx if s.loc[t] == 0
            ][:40],
        }
    return ev
def valve_activity(wn, res, total_demand_gpm: float) -> dict:
    """Flow actually carried by each PRV over the baseline run."""
    fl = res.link["flowrate"]
    st = res.link["status"]
    out = {}
    for v in wn.valve_name_list:
        q = C.m3s_to_gpm(fl[v])
        out[v] = {
            "setting_psi": float(C.m_to_psi(wn.get_link(v).initial_setting)),
            "diameter_in": float(C.m_to_ft(wn.get_link(v).diameter) * 12.0),
            "status_states": sorted({status_label(x) for x in st[v].unique()}),
            "flow_mean_gpm": float(q.mean()),
            "flow_max_gpm": float(q.max()),
            "flow_abs_max_gpm": float(q.abs().max()),
            "share_of_total_base_demand_pct": float(q.mean() / total_demand_gpm * 100.0),
            "zero_flow_at_all_times": bool((q.abs() < 1e-9).all()),
            "frac_time_zero_flow": float((q.abs() < 1e-9).mean()),
        }
    return out


def phase4_discrepancy_valves(activity: dict) -> list:
    """Phase 4 claimed 7 of 8 PRVs are active at start. Test that claim."""
    dead = sorted(k for k, v in activity.items() if v["zero_flow_at_all_times"])
    if dead == ["VALVE-180"]:
        return []
    return [{
        "id": "D5-prv-activity",
        "phase4_text": ("'One [CONTROLS] line closes VALVE-180 at time 0, so 7 of the 8 "
                        "PRVs are active at start.'"),
        "observed": {
            "valves_with_identically_zero_flow_over_96h": dead,
            "per_valve": {k: {"status_states": v["status_states"],
                              "flow_mean_gpm": v["flow_mean_gpm"],
                              "share_pct": v["share_of_total_base_demand_pct"]}
                          for k, v in activity.items()},
        },
        "explanation": ("Only VALVE-180 is closed by a [CONTROLS] line, but the baseline "
                        "solution also holds VALVE-174 and VALVE-179 Closed for the entire "
                        "96 h with identically zero flow. A PRV closes when downstream head "
                        "exceeds the setting and flow would reverse, so these two are shut "
                        "by the hydraulics, not by a control statement. Three of eight PRVs, "
                        "not one, carry no flow in the distributed baseline."),
        "consequence": ("Directly material to Gate 5: an action dimension on a permanently "
                        "shut PRV cannot influence the network. Reported as evidence only; "
                        "no PRV is removed in this phase."),
        "silent_correction": False,
    }]


def main() -> dict:
    runs = {}
    # (a) exactly as distributed except the native rule timestep restored.
    wn_a = C.load_wn(rule_timestep=180)
    res_a, msg_a = C.run_epanet(wn_a, "g1_asdistributed")
    runs["as_distributed_report_3600s"] = summarise_run(wn_a, res_a, msg_a, "g1_asdistributed")

    # (b) same solve, finer reporting - evidences that D4 is output-only.
    wn_b = C.load_wn(rule_timestep=180, report_timestep=1800)
    res_b, msg_b = C.run_epanet(wn_b, "g1_report1800")
    runs["report_1800s"] = summarise_run(wn_b, res_b, msg_b, "g1_report1800")

    # (c) WNTR's own default rule timestep - evidences D3's practical effect.
    wn_c = C.load_wn(rule_timestep=360, report_timestep=1800)
    res_c, msg_c = C.run_epanet(wn_c, "g1_rule360")
    runs["wntr_default_rule_360s"] = summarise_run(wn_c, res_c, msg_c, "g1_rule360")

    # Agreement between (a) and (b) at the timestamps they share.
    common = res_a.node["pressure"].index.intersection(res_b.node["pressure"].index)
    dp = (res_a.node["pressure"].loc[common] - res_b.node["pressure"].loc[common]).abs()
    agree = {
        "n_common_timesteps": int(len(common)),
        "max_abs_pressure_diff_m": float(dp.max().max()),
        "identical_to_1e-9_m": bool(dp.max().max() < 1e-9),
    }
    # Effect of the rule timestep on the solution itself.
    common2 = res_b.node["pressure"].index.intersection(res_c.node["pressure"].index)
    dp2 = (res_b.node["pressure"].loc[common2] - res_c.node["pressure"].loc[common2]).abs()
    rule_effect = {
        "max_abs_pressure_diff_m": float(dp2.max().max()),
        "max_abs_pressure_diff_psi": float(C.m_to_psi(dp2.max().max())),
        "identical": bool(dp2.max().max() < 1e-9),
        "n_pump_switches_rule180": {
            p: runs["report_1800s"]["pumps_and_valves"][p]["n_status_changes"]
            for p in wn_b.pump_name_list},
        "n_pump_switches_rule360": {
            p: runs["wntr_default_rule_360s"]["pumps_and_valves"][p]["n_status_changes"]
            for p in wn_c.pump_name_list},
    }

    ctrl = native_controls(wn_b, res_b)
    sw = switch_evidence(wn_b, res_b)
    total_base_gpm = float(sum(
        C.m3s_to_gpm(wn_b.get_node(j).demand_timeseries_list[0].base_value)
        for j in wn_b.junction_name_list if wn_b.get_node(j).demand_timeseries_list))
    activity = valve_activity(wn_b, res_b, total_base_gpm)
    disc = phase4_discrepancy_valves(activity)

    ref = runs["report_1800s"]
    scan = ref["report_scan"]
    n_err = scan.get("n_errors", 0) if scan.get("rpt_found") else None
    tanks = ref["tanks"]
    g1 = "PASS" if (
        ref["n_timesteps_returned"] == 193
        and n_err == 0
        and not any(t["exceeded_max_level"] for t in tanks.values())
        and not any(t["went_negative"] for t in tanks.values())
    ) else "FAIL"
    g11 = "PASS" if (
        not any(t["went_negative"] for t in tanks.values())
        and not any(t["exceeded_max_level"] for t in tanks.values())
        and all(t["level_range_ft"] > 0.01 for t in tanks.values())
        and all(r["n_switches_over_run"] > 0 for r in ctrl["table"]
                if r["element"] in wn_b.pump_name_list)
    ) else "FAIL"

    payload = {
        "gate": "G1+G2+G11",
        "title": "Baseline convergence, native control logic, tank dynamics",
        "env": C.env_info(),
        "runtime_notes": C.RUNTIME_NOTES,
        "leakage_added": False,
        "demand_model_changed": False,
        "actuators_overridden": False,
        "runs": runs,
        "resolution_agreement": agree,
        "rule_timestep_effect": rule_effect,
        "native_controls": ctrl,
        "rule_firing_evidence": sw,
        "total_base_demand_gpm": total_base_gpm,
        "valve_activity_baseline": activity,
        "documentation_discrepancies": disc,
        "verdicts": {
            "g1": f"G1 BASELINE EPANET/WNTR CONVERGENCE = {g1}",
            "g11": f"G11 TANK DYNAMICS = {g11}",
            "g2": "G2 NATIVE CONTROL LOGIC = CHARACTERISED (descriptive gate, no pass/fail)",
        },
    }
    C.jdump("g1_g2_g11_baseline.json", payload)

    print("\n--- G1 baseline (report 1800 s, rule 180 s) ---------------------")
    print(f"timesteps returned      {ref['n_timesteps_returned']}")
    print(f"rpt errors / warnings   {scan.get('n_errors')} / {scan.get('n_warnings')}")
    print(f"wntr warnings           {ref['wntr_warnings']}")
    pp = ref["pressure_junctions_psi"]
    print(f"junction pressure psi   min {pp['min']:.3f} @ {pp['min_at_node']} t={pp['min_at_time_s']:.0f}s"
          f" | max {pp['max']:.3f} @ {pp['max_at_node']} | mean {pp['mean']:.3f}")
    print(f"negative-pressure count {pp['n_negative']}  |  <20 psi count {pp['n_below_20psi']}")
    print(f"nodes ever <20 psi      {pp['nodes_ever_below_20psi']}")
    for t, v in tanks.items():
        print(f"tank {t}: level {v['level_min_ft']:.3f}-{v['level_max_ft']:.3f} ft "
              f"(bounds {v['min_level_ft']:.1f}-{v['max_level_ft']:.1f}) "
              f"net {v['net_level_change_ft']:+.3f} ft  hit_min={v['hit_min_level']} "
              f"over_max={v['exceeded_max_level']}")
    print("\n--- G2 native controls -----------------------------------------")
    for r in ctrl["table"]:
        print(f"  {r['element']:<10} {r['type']:<5} init={r['initial_state']:<7} "
              f"final={r['final_state']:<7} states={r['states_observed']} "
              f"switches={r['n_switches_over_run']} open={r['frac_time_open']:.3f}")
    print("\n--- rule firing levels -----------------------------------------")
    for p, v in sw.items():
        if isinstance(v, dict):
            print(f"  {p} (tank {v['driving_tank']}): opened at levels "
                  f"{[round(x,3) for x in v['tank_level_when_open_ft']]}")
            print(f"  {p} closed at levels "
                  f"{[round(x,3) for x in v['tank_level_when_closed_ft']]}")
    print("\n--- D3 / D4 evidence -------------------------------------------")
    print(f"report-resolution agreement: {agree}")
    print(f"rule-timestep effect: max |dP| = {rule_effect['max_abs_pressure_diff_psi']:.4f} psi, "
          f"switches 180s={rule_effect['n_pump_switches_rule180']} "
          f"360s={rule_effect['n_pump_switches_rule360']}")
    print("\n--- baseline PRV activity --------------------------------------")
    print(f"total base demand {total_base_gpm:.3f} GPM")
    for k, v in activity.items():
        print(f"  {k:<10} set={v['setting_psi']:7.3f} psi d={v['diameter_in']:5.2f} in "
              f"q_mean={v['flow_mean_gpm']:9.3f} GPM ({v['share_of_total_base_demand_pct']:6.3f} %) "
              f"states={v['status_states']} dead={v['zero_flow_at_all_times']}")
    print("\n--- documentation discrepancies (reported, not corrected) ------")
    for d in disc:
        print(f"  {d['id']}: {d['explanation']}")
    print("\n--- pump power / energy ----------------------------------------")
    for k, v in ref["pump_energy"].items():
        if isinstance(v, dict):
            print(f"  {k}: mean {v['power_mean_kW']:.2f} kW, running-mean "
                  f"{v['power_when_running_mean_kW']:.2f} kW, max {v['power_max_kW']:.2f} kW, "
                  f"{v['energy_total_kWh']:.1f} kWh/96h")
    print(f"\n{payload['verdicts']['g1']}")
    print(f"{payload['verdicts']['g11']}")
    return payload


if __name__ == "__main__":
    main()



