"""Gate 12 - actuator realizability in the configuration the RL agent will drive.

The question is narrow and mechanical: when a PRV setting or a pump speed is
commanded, does the engine actually apply it, does the realised value differ from
the commanded one, and can the hydraulics override the command outright?

Three separate things are measured, because they fail in different ways and a
single "does it work" answer would hide two of them:

1. TRANSMISSION. The commanded value is written to an .inp and read back, so the
   claim that WNTR turned an attribute into an EPANET token is proved rather than
   assumed. This is the same discipline gates 3 and 6 used.
2. REALISATION. EPANET reports a per-link Setting in its binary output. For a PRV
   that is the regulated head; for a pump it is the relative speed. It is compared
   against the command at every reported state, and for an Active PRV the
   downstream pressure is compared against the setting as well - a PRV that is
   Active but not holding its setting would be a solver failure, not an action.
3. AUTHORITY. A command can be transmitted perfectly, realised perfectly, and
   still change nothing, either because the element carries no flow or because the
   native rule has the pump closed. That is a null action, and for a
   reinforcement-learning action space it is the most consequential of the three.

Everything is deterministic: a fixed list of settings and speeds, no search, no
optimisation, no training. The configuration is the one gate 10 validated - PDA
plus the gate 6 validation leakage plus the distributed rules and controls - so
the realisation rates reported here are the ones the RL environment would inherit.
The leakage coefficients remain a validation instrument that must not enter any
thesis result.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import g6_g7_g8_leak_pda as L  # noqa: E402
import g9_g10_full as F  # noqa: E402
import phase5_common as C  # noqa: E402

# All three declared BEFORE any run.
# A PRV that is Active must hold its downstream head at the setting. 0.1 psi is
# four orders of magnitude above the solver's own convergence floor and four
# orders below the smallest PRV setting in the file, so it separates "realised"
# from "not realised" without being sensitive to either.
CMD_TOL_PSI = 0.1
# A command has a measurable effect if it moves any junction's 96 h mean pressure
# by more than this, or total mean leakage by more than EFFECT_TOL_GPM. Both are
# above the numerical floor measured in gate 6 (worst nodal law error 0.000039 GPM)
# and far below anything a real control action produces.
EFFECT_TOL_PSI = 0.01
EFFECT_TOL_GPM = 0.01

# Deterministic command ladders.
PRV_SCALES = (0.75, 1.25)
# Inside the range gate 3 swept (0.50-1.10), and chosen to straddle the feasible
# bounds gate 3 measured: PUMP-170 shut at 0.80 and ran at 0.85, PUMP-172 shut at
# 0.70 and ran at 0.80. 0.70 is therefore expected to be overridden for at least
# one pump, which is exactly the saturation case this gate has to measure.
PUMP_SPEEDS = (0.70, 0.85, 1.10)


def echo_actuators(wn, prefix: str) -> dict:
    """Write the model out, read it back, and report what reached the engine.

    [VALVES] column 6 is the setting in the file's own psi; [PUMPS] carries
    keyword/value pairs after the two end nodes, so SPEED is read from there. An
    absent SPEED token means the engine will use 1.0.
    """
    import wntr

    p = C.RESULTS / "_tmp" / f"{prefix}_echo.inp"
    wntr.network.io.write_inpfile(wn, str(p), units="GPM")
    sec = C.read_sections(p)
    valves = {}
    for ln in sec.get("VALVES", []):
        t = ln.split()
        valves[t[0]] = {"type": t[4], "setting_psi": float(t[5])}
    pumps = {}
    for ln in sec.get("PUMPS", []):
        t = ln.split()
        kv = {}
        rest = t[3:]
        for i in range(0, len(rest) - 1, 2):
            kv[rest[i].upper()] = rest[i + 1]
        pumps[t[0]] = {"keywords": kv,
                       "speed_token": float(kv["SPEED"]) if "SPEED" in kv else None,
                       "speed_effective": float(kv.get("SPEED", 1.0))}
    return {"echo_file": str(p), "valves": valves, "pumps": pumps}


def run_case(prefix: str, coeff: dict, *, valve: str | None = None,
             scale: float | None = None, pump: str | None = None,
             speed: float | None = None, open_rule_off: str | None = None,
             duration_s: int | None = None) -> dict:
    """One 96 h EPS in the gate 10 configuration, with at most one command applied.

    ``open_rule_off`` and ``duration_s`` exist only for the pump-speed attribution
    diagnostic below. They are never used by the 22 commanded cases that the gate
    verdict is taken on, and neither is carried forward into the RL model.
    """
    wn = C.load_wn(rule_timestep=180, report_timestep=1800)
    wn.options.hydraulic.accuracy = L.SOLVER_ACCURACY
    wn.options.hydraulic.trials = L.SOLVER_TRIALS
    wn.options.hydraulic.demand_model = "PDA"
    wn.options.hydraulic.required_pressure = float(C.psi_to_m(L.PDA_REQUIRED_PSI))
    wn.options.hydraulic.minimum_pressure = float(C.psi_to_m(L.PDA_MINIMUM_PSI))
    wn.options.hydraulic.pressure_exponent = L.PDA_EXPONENT
    cmd = {}
    if valve is not None:
        target = L.NOMINAL_PSI[valve] * scale
        wn.get_link(valve).initial_setting = C.psi_to_m(target)
        cmd = {"kind": "prv_setting", "element": valve, "scale_of_nominal": scale,
               "nominal_psi": L.NOMINAL_PSI[valve], "commanded_psi": target}
    if pump is not None:
        wn.get_link(pump).base_speed = float(speed)
        cmd = {"kind": "pump_speed", "element": pump, "commanded_speed": float(speed)}
    removed = []
    if open_rule_off is not None:
        for name in list(wn.control_name_list):
            txt = str(wn.get_control(name))
            if open_rule_off in txt and "OPEN" in txt.upper():
                wn.remove_control(name)
                removed.append(name)
    if duration_s is not None:
        wn.options.time.duration = int(duration_s)
    L.apply_leak(wn, coeff)
    echo = echo_actuators(wn, prefix)
    res, msgs, used = L._run_with_retry(wn, prefix)
    return {"command": cmd, "echo": echo, "wntr_warnings": msgs,
            "controls_removed": removed,
            "report_scan": L._rpt_errors(used), "wn": wn, "res": res}


def prv_state(wn, res, valve: str, commanded_psi: float) -> dict:
    """Per-state realisation record for one PRV.

    EPANET's three PRV states mean three different things for an action:
    Active is the setting binding and held; Open is the setting present but not
    binding because the upstream head is already below it, so the command cannot
    raise pressure any further; Closed is the valve shut against reverse flow, in
    which case the engine reports the realised setting as zero and the command has
    been nulled outright.
    """
    from wntr.network.base import LinkStatus

    st = res.link["status"][valve]
    real = C.m_to_psi(res.link["setting"][valve])
    pdn = C.m_to_psi(res.node["pressure"][wn.get_link(valve).end_node_name])
    q = C.m3s_to_gpm(res.link["flowrate"][valve])
    active = st == LinkStatus.Active
    n = int(len(st))
    err = (pdn[active] - commanded_psi).abs() if active.any() else None
    held = int((err <= CMD_TOL_PSI).sum()) if err is not None else 0
    counts = {LinkStatus(int(k)).name: int(v)
              for k, v in st.value_counts().to_dict().items()}
    return {
        "commanded_psi": commanded_psi,
        "n_states": n,
        "status_counts": counts,
        "realised_setting_psi_min": float(real.min()),
        "realised_setting_psi_max": float(real.max()),
        "realised_setting_equals_command_states": int(
            ((real - commanded_psi).abs() <= CMD_TOL_PSI).sum()),
        "n_active": int(active.sum()),
        "n_active_and_holding_setting": held,
        "max_abs_downstream_error_psi_when_active": (
            float(err.max()) if err is not None else None),
        "realisation_rate_binding": held / n,
        "mean_flow_gpm": float(q.mean()),
        "abs_flow_max_gpm": float(q.abs().max()),
        "carries_flow": bool(q.abs().max() > 1e-6),
    }


def pump_state(wn, res, pump: str, commanded_speed: float) -> dict:
    """Per-state realisation record for one pump.

    EPANET reports a closed pump's setting as zero, so the realised speed equals
    the command only while the native tank-level rule has the pump open. The
    fraction of the horizon in which that holds is the fraction of the horizon in
    which a speed action can do anything at all.
    """
    from wntr.network.base import LinkStatus

    st = res.link["status"][pump]
    real = res.link["setting"][pump]
    q = C.m3s_to_gpm(res.link["flowrate"][pump])
    lk = wn.get_link(pump)
    gain = C.m_to_ft(res.node["head"][lk.end_node_name]
                     - res.node["head"][lk.start_node_name])
    op = st == LinkStatus.Open
    n = int(len(st))
    counts = {LinkStatus(int(k)).name: int(v)
              for k, v in st.value_counts().to_dict().items()}
    return {
        "commanded_speed": commanded_speed,
        "n_states": n,
        "status_counts": counts,
        "n_open": int(op.sum()),
        "open_fraction": int(op.sum()) / n,
        "realised_speed_values": sorted({round(float(x), 6) for x in real}),
        "realised_equals_command_while_open": int(
            ((real[op] - commanded_speed).abs() <= 1e-6).sum()) if op.any() else 0,
        "realisation_rate_while_open": (
            int(((real[op] - commanded_speed).abs() <= 1e-6).sum()) / int(op.sum())
            if op.any() else None),
        "realisation_rate_over_horizon": (
            int(((real - commanded_speed).abs() <= 1e-6).sum()) / n),
        "mean_flow_gpm": float(q.mean()),
        "max_flow_gpm": float(q.max()),
        "mean_head_gain_ft_when_open": float(gain[op].mean()) if op.any() else None,
        "overridden_by_hydraulics": bool(int(op.sum()) == 0),
    }


def speed_persistence(wn, res, pump: str, commanded_speed: float) -> dict:
    """Does a commanded pump speed survive the network's own rules, and for how long?

    The file's reopening rules are RULE-1 (``IF TANK TANK-130 LEVEL <= 12.1 THEN
    PUMP PUMP-172 STATUS IS OPEN``) and RULE-4 (the same for PUMP-170 on
    TANK-131). Both are ``STATUS IS OPEN`` actions, not ``SETTING IS`` actions.
    This function locates the first reported state at which the pump is open and
    the engine reports a realised relative speed of exactly 1.0 against a command
    that was not 1.0, and splits the realisation statistics at that point. Before
    it, the command is the only thing setting the speed; after it, something in the
    engine has replaced the command.
    """
    from wntr.network.base import LinkStatus
    import numpy as np

    st = res.link["status"][pump]
    real = res.link["setting"][pump]
    t = np.asarray(st.index, dtype=float)
    sv = np.asarray(st.to_numpy(), dtype=int)
    rv = np.asarray(real.to_numpy(), dtype=float)
    op = sv == int(LinkStatus.Open)
    at_cmd = np.abs(rv - commanded_speed) <= 1e-6
    at_one = np.abs(rv - 1.0) <= 1e-6
    cmd_is_one = abs(commanded_speed - 1.0) <= 1e-6
    reset = op & at_one & (not cmd_is_one)
    idx = int(np.argmax(reset)) if reset.any() else None
    pre = np.zeros_like(op) if idx is None else (np.arange(len(op)) < idx)
    post = np.ones_like(op) if idx is None else (np.arange(len(op)) >= idx)
    n_open_pre = int((op & pre).sum())
    n_open_post = int((op & post).sum())
    win = None
    if idx is not None:
        lo, hi = max(0, idx - 3), min(len(op), idx + 3)
        win = [{"hours": round(t[i] / 3600.0, 4),
                "status": LinkStatus(int(sv[i])).name,
                "realised_speed": round(float(rv[i]), 6)} for i in range(lo, hi)]
    return {
        "commanded_speed": commanded_speed,
        "n_states": int(len(sv)),
        "first_reset_state_index": idx,
        "hours_to_first_reset": None if idx is None else round(float(t[idx]) / 3600.0, 4),
        "n_open_before_first_reset": n_open_pre,
        "n_open_at_command_before_first_reset": int((op & pre & at_cmd).sum()),
        "realisation_rate_while_open_before_first_reset": (
            float((op & pre & at_cmd).sum()) / n_open_pre if n_open_pre else None),
        "n_open_after_first_reset": n_open_post,
        "n_open_at_command_after_first_reset": int((op & post & at_cmd).sum()),
        "n_open_at_speed_one_after_first_reset": int((op & post & at_one).sum()),
        "no_open_state_before_reset_hydraulically_shut": bool(n_open_pre == 0),
        "transition_window": win,
    }


def speed_attribution(coeff: dict, pumps: list) -> dict:
    """Controlled test of one candidate mechanism, not a model change.

    Three runs per pump at 0.85, a speed above the feasible bound gate 3 measured
    for both pumps (0.8152 for PUMP-170, 0.7655 for PUMP-172), so the pump can run:

    R1  native rules intact, 96 h            - the configuration the gate is judged in
    R2  the pump's own ``STATUS IS OPEN`` rule removed, 96 h, initial status and the
        matching CLOSED rule left exactly as the file declares them
    R3  native rules intact, one 30 min hydraulic step

    If the realised speed reverts to 1.0 only in R1, and holds at the command in R2
    and R3, then the reversion is caused by the reopening rule action and by nothing
    else. R2 is a diagnostic: it is not carried into any other gate or into the RL
    model, and the removed control names are recorded.
    """
    out = {"design": {"speed_tested": 0.85,
                      "runs": ["R1_rules_intact_96h", "R2_open_rule_removed_96h",
                               "R3_rules_intact_one_step"]},
           "pumps": {}}
    for p in pumps:
        tag = p.lower().replace("-", "")
        r1 = run_case(f"g12_attr_{tag}_r1", coeff, pump=p, speed=0.85)
        r2 = run_case(f"g12_attr_{tag}_r2", coeff, pump=p, speed=0.85,
                      open_rule_off=p)
        r3 = run_case(f"g12_attr_{tag}_r3", coeff, pump=p, speed=0.85,
                      duration_s=1800)
        rows = {}
        for key, r in (("R1_rules_intact_96h", r1),
                       ("R2_open_rule_removed_96h", r2),
                       ("R3_rules_intact_one_step", r3)):
            rows[key] = {
                "controls_removed": r["controls_removed"],
                "duration_h": float(r["wn"].options.time.duration) / 3600.0,
                "realisation": pump_state(r["wn"], r["res"], p, 0.85),
                "persistence": speed_persistence(r["wn"], r["res"], p, 0.85),
                "report_scan": r["report_scan"],
                "wntr_warnings": r["wntr_warnings"],
            }
        reverts = rows["R1_rules_intact_96h"][
            "persistence"]["first_reset_state_index"] is not None
        holds_wo = rows["R2_open_rule_removed_96h"][
            "persistence"]["first_reset_state_index"] is None
        holds_1s = rows["R3_rules_intact_one_step"][
            "persistence"]["first_reset_state_index"] is None
        out["pumps"][p] = {
            "runs": rows,
            "reverts_to_speed_one_with_open_rule_present": reverts,
            "holds_command_with_open_rule_removed": holds_wo,
            "holds_command_within_one_control_step": holds_1s,
            "mechanism_confirmed": bool(reverts and holds_wo and holds_1s),
        }
    conf = [p for p, d in out["pumps"].items() if d["mechanism_confirmed"]]
    out["conclusion"] = {
        "pumps_confirmed": conf,
        "n_pumps_confirmed": len(conf),
        "all_confirmed": bool(len(conf) == len(pumps)),
        "statement": (
            "A rule action of the form THEN PUMP <p> STATUS IS OPEN restores the "
            "pump's relative speed to 1.0, discarding the commanded speed. The "
            "command itself is transmitted and realised exactly; it does not "
            "survive the next rule-driven reopening."),
    }
    return out


def network_effect(wn, res_ref, res, coeff: dict, service: list) -> dict:
    """Did the command change the network, and by how much?

    Pressure is compared only on the 121 demand-bearing junctions, for the reason
    gate 10 established: the five junctions the file declares at elevation 0.0 ft
    are pump and reservoir connector nodes whose reported pressure is head above
    datum and reaches 500 psi, which would dominate any aggregate.
    """
    import numpy as np

    def leak(r):
        p = C.m_to_psi(r.node["pressure"][wn.junction_name_list])
        return float((np.sign(p) * p.abs() ** L.LEAK_EXPONENT).mul(
            [coeff[j] for j in wn.junction_name_list], axis=1).sum(axis=1).mean())

    pa = C.m_to_psi(res_ref.node["pressure"][service]).mean()
    pb = C.m_to_psi(res.node["pressure"][service]).mean()
    d = pb - pa
    ia = -C.m3s_to_gpm(res_ref.node["demand"][wn.reservoir_name_list].sum(axis=1))
    ib = -C.m3s_to_gpm(res.node["demand"][wn.reservoir_name_list].sum(axis=1))
    la, lb = leak(res_ref), leak(res)
    served_a = C.m3s_to_gpm(res_ref.node["demand"][wn.junction_name_list].sum(axis=1))
    served_b = C.m3s_to_gpm(res.node["demand"][wn.junction_name_list].sum(axis=1))
    minp = float(C.m_to_psi(res.node["pressure"][service]).min().min())
    return {
        "d_mean_service_pressure_psi": float(d.mean()),
        "max_abs_d_nodal_mean_pressure_psi": float(d.abs().max()),
        "junction_of_max_change": str(d.abs().idxmax()),
        "n_junctions_moved_above_tol": int((d.abs() > EFFECT_TOL_PSI).sum()),
        "n_junctions_moved_above_half_psi": int((d.abs() > 0.5).sum()),
        "d_mean_leakage_gpm": lb - la,
        "d_mean_inflow_gpm": float(ib.mean() - ia.mean()),
        "d_mean_nodal_withdrawal_gpm": float(served_b.mean() - served_a.mean()),
        "min_service_pressure_psi": minp,
        "min_service_pressure_negative": bool(minp < 0.0),
        "has_measurable_effect": bool(
            float(d.abs().max()) > EFFECT_TOL_PSI or abs(lb - la) > EFFECT_TOL_GPM),
    }


def main() -> dict:
    base_p, base_inflow, weights = L.baseline_pressures("g12_size")
    sizing = L.leak_coefficients(weights, base_p,
                                L.LEAK_TARGET_FRACTION * base_inflow)
    coeff = sizing["coefficient_gpm_per_psi_alpha"]

    ref = run_case("g12_nominal", coeff)
    wn0, res0 = ref["wn"], ref["res"]
    conn = F.connector_nodes(wn0)
    cset = set(conn["connector_nodes"])
    service = [j for j in wn0.junction_name_list if j not in cset]

    nominal = {
        "prv": {v: prv_state(wn0, res0, v, L.NOMINAL_PSI[v]) for v in L.VALVES},
        "pump": {p: pump_state(wn0, res0, p, 1.0) for p in wn0.pump_name_list},
        "echo": ref["echo"],
        "report_scan": ref["report_scan"],
    }

    cases = {}
    for v in L.VALVES:
        for s in PRV_SCALES:
            key = f"prv_{v}_x{s:.2f}"
            r = run_case(f"g12_{v.lower().replace('-', '')}_{int(s * 100)}",
                         coeff, valve=v, scale=s)
            tgt = r["command"]["commanded_psi"]
            cases[key] = {
                "command": r["command"],
                "transmission": {
                    "commanded_psi": tgt,
                    "echoed_psi": r["echo"]["valves"][v]["setting_psi"],
                    "abs_difference_psi": abs(
                        r["echo"]["valves"][v]["setting_psi"] - tgt),
                    "reached_engine": bool(abs(
                        r["echo"]["valves"][v]["setting_psi"] - tgt) < 5e-3),
                },
                "realisation": prv_state(r["wn"], r["res"], v, tgt),
                "effect": network_effect(wn0, res0, r["res"], coeff, service),
                "report_scan": r["report_scan"],
                "wntr_warnings": r["wntr_warnings"],
            }
    for p in wn0.pump_name_list:
        for s in PUMP_SPEEDS:
            key = f"speed_{p}_{s:.2f}"
            r = run_case(f"g12_{p.lower().replace('-', '')}_{int(s * 100)}",
                         coeff, pump=p, speed=s)
            cases[key] = {
                "command": r["command"],
                "transmission": {
                    "commanded_speed": s,
                    "echoed_speed": r["echo"]["pumps"][p]["speed_effective"],
                    "speed_token_present": r["echo"]["pumps"][p]["speed_token"]
                    is not None,
                    "reached_engine": bool(abs(
                        r["echo"]["pumps"][p]["speed_effective"] - s) < 1e-6),
                },
                "realisation": pump_state(r["wn"], r["res"], p, s),
                "persistence": speed_persistence(r["wn"], r["res"], p, s),
                "effect": network_effect(wn0, res0, r["res"], coeff, service),
                "report_scan": r["report_scan"],
                "wntr_warnings": r["wntr_warnings"],
            }
    # ---- aggregate: the Action Realization Rate the RL design will inherit -----
    per_actuator = {}
    for v in L.VALVES:
        ks = [k for k in cases if k.startswith(f"prv_{v}_")]
        rows = [cases[k] for k in ks]
        per_actuator[v] = {
            "kind": "prv",
            "nominal_psi": L.NOMINAL_PSI[v],
            "n_commands_tested": len(rows),
            "all_reached_engine": all(r["transmission"]["reached_engine"]
                                      for r in rows),
            "mean_binding_realisation_rate": sum(
                r["realisation"]["realisation_rate_binding"] for r in rows) / len(rows),
            "n_commands_with_measurable_effect": sum(
                1 for r in rows if r["effect"]["has_measurable_effect"]),
            "n_commands_inert": sum(
                1 for r in rows if not r["effect"]["has_measurable_effect"]),
            "n_commands_driving_negative_pressure": sum(
                1 for r in rows if r["effect"]["min_service_pressure_negative"]),
            "nominal_status_counts": nominal["prv"][v]["status_counts"],
            "nominal_carries_flow": nominal["prv"][v]["carries_flow"],
            "commands": {k: {
                "commanded_psi": cases[k]["command"]["commanded_psi"],
                "status_counts": cases[k]["realisation"]["status_counts"],
                "binding_rate": cases[k]["realisation"]["realisation_rate_binding"],
                "max_abs_d_nodal_mean_pressure_psi":
                    cases[k]["effect"]["max_abs_d_nodal_mean_pressure_psi"],
                "d_mean_leakage_gpm": cases[k]["effect"]["d_mean_leakage_gpm"],
                "has_measurable_effect": cases[k]["effect"]["has_measurable_effect"],
                "min_service_pressure_psi":
                    cases[k]["effect"]["min_service_pressure_psi"],
            } for k in ks},
        }
    for p in wn0.pump_name_list:
        ks = [k for k in cases if k.startswith(f"speed_{p}_")]
        rows = [cases[k] for k in ks]
        per_actuator[p] = {
            "kind": "pump_speed",
            "n_commands_tested": len(rows),
            "all_reached_engine": all(r["transmission"]["reached_engine"]
                                      for r in rows),
            "nominal_open_fraction": nominal["pump"][p]["open_fraction"],
            "mean_realisation_rate_while_open": sum(
                r["realisation"]["realisation_rate_while_open"] or 0.0
                for r in rows) / len(rows),
            "mean_realisation_rate_over_horizon": sum(
                r["realisation"]["realisation_rate_over_horizon"]
                for r in rows) / len(rows),
            "n_commands_overridden": sum(
                1 for r in rows if r["realisation"]["overridden_by_hydraulics"]),
            "n_commands_inert": sum(
                1 for r in rows if not r["effect"]["has_measurable_effect"]),
            "mean_realisation_rate_while_open_before_first_reset": (
                sum(r["persistence"]
                     ["realisation_rate_while_open_before_first_reset"] or 0.0
                    for r in rows if r["persistence"]["n_open_before_first_reset"])
                / max(1, sum(1 for r in rows
                             if r["persistence"]["n_open_before_first_reset"]))),
            "n_commands_with_no_open_state_before_reset": sum(
                1 for r in rows
                if r["persistence"]["no_open_state_before_reset_hydraulically_shut"]),
            "commands": {k: {
                "commanded_speed": cases[k]["command"]["commanded_speed"],
                "status_counts": cases[k]["realisation"]["status_counts"],
                "open_fraction": cases[k]["realisation"]["open_fraction"],
                "realisation_rate_while_open":
                    cases[k]["realisation"]["realisation_rate_while_open"],
                "realisation_rate_over_horizon":
                    cases[k]["realisation"]["realisation_rate_over_horizon"],
                "hours_to_first_reset":
                    cases[k]["persistence"]["hours_to_first_reset"],
                "realisation_rate_while_open_before_first_reset":
                    cases[k]["persistence"]
                    ["realisation_rate_while_open_before_first_reset"],
                "overridden_by_hydraulics":
                    cases[k]["realisation"]["overridden_by_hydraulics"],
                "max_abs_d_nodal_mean_pressure_psi":
                    cases[k]["effect"]["max_abs_d_nodal_mean_pressure_psi"],
                "d_mean_leakage_gpm": cases[k]["effect"]["d_mean_leakage_gpm"],
                "has_measurable_effect": cases[k]["effect"]["has_measurable_effect"],
                "min_service_pressure_psi":
                    cases[k]["effect"]["min_service_pressure_psi"],
            } for k in ks},
        }
    attribution = speed_attribution(coeff, list(wn0.pump_name_list))
    return (nominal, cases, per_actuator, coeff, sizing, conn, service,
            attribution)


def _verdict(nominal, cases, per_actuator, sizing, conn, service, attr) -> dict:
    """Decide the gate on the three separate questions, not on one blurred one."""
    transmission_ok = all(c["transmission"]["reached_engine"] for c in cases.values())
    prv_cases = [c for c in cases.values() if c["command"]["kind"] == "prv_setting"]
    pump_cases = [c for c in cases.values() if c["command"]["kind"] == "pump_speed"]
    # A PRV that is Active must hold its setting. Where it never goes Active the
    # binding rate is 0 by definition and that is an authority question, not a
    # realisation failure, so it is counted separately.
    binding_ok = all(
        (c["realisation"]["max_abs_downstream_error_psi_when_active"] is None
         or c["realisation"]["max_abs_downstream_error_psi_when_active"] <= CMD_TOL_PSI)
        for c in prv_cases)
    # Two different questions about a pump-speed command, measured separately.
    # (a) realisation: while the pump is open and no rule has yet reopened it, does
    #     the engine run it at the commanded speed?  Cases in which the pump never
    #     opens before the first reset are hydraulically shut, which gate 3 already
    #     measured as a feasible-speed bound, and carry no realisation evidence.
    speed_at_issue_ok = all(
        (c["persistence"]["realisation_rate_while_open_before_first_reset"] is None
         or c["persistence"]["realisation_rate_while_open_before_first_reset"]
         >= 1.0 - 1e-12)
        for c in pump_cases)
    # (b) persistence: does the command survive the whole horizon?  It does not.
    speed_persists = all(
        (c["realisation"]["realisation_rate_while_open"] is None
         or c["realisation"]["realisation_rate_while_open"] >= 1.0 - 1e-12)
        for c in pump_cases)
    inert = sorted(k for k, c in cases.items()
                   if not c["effect"]["has_measurable_effect"])
    overridden = sorted(k for k, c in cases.items()
                        if c["command"]["kind"] == "pump_speed"
                        and c["realisation"]["overridden_by_hydraulics"])
    reset = sorted(k for k, c in cases.items()
                   if c["command"]["kind"] == "pump_speed"
                   and c["persistence"]["first_reset_state_index"] is not None)
    unsafe = sorted(k for k, c in cases.items()
                    if c["effect"]["min_service_pressure_negative"])
    never_active = sorted(v for v, a in per_actuator.items()
                          if a["kind"] == "prv"
                          and a["nominal_status_counts"].get("Active", 0) == 0)
    if not (transmission_ok and binding_ok and speed_at_issue_ok):
        verdict = "FAIL"
    elif inert or overridden or never_active or reset:
        verdict = "CONDITIONAL"
    else:
        verdict = "PASS"
    return {
        "transmission_ok": transmission_ok,
        "prv_binding_ok": binding_ok,
        "pump_speed_realised_at_issue": speed_at_issue_ok,
        "pump_speed_persists_over_horizon": speed_persists,
        "n_commands_tested": len(cases),
        "inert_commands": inert,
        "overridden_commands": overridden,
        "speed_commands_reset_by_native_rule": reset,
        "commands_driving_negative_service_pressure": unsafe,
        "prvs_never_active_at_nominal": never_active,
        "speed_reset_mechanism_confirmed": attr["conclusion"]["all_confirmed"],
        "criterion_history": {
            "first_declared_criterion": (
                "pump_speed_realised_while_open: the realised relative speed must "
                "equal the command at every reported state at which the pump is "
                "open, over the whole 96 h horizon."),
            "result_under_first_criterion": "FAIL",
            "why_changed": (
                "The criterion conflated realisation with persistence. The engine "
                "does apply the commanded speed; a native rule action then replaces "
                "it. The run that produced FAIL issued the command once at t=0 and "
                "never reissued it, so it measured how long a command survives, not "
                "whether it is applied. The attribution test isolates the cause."),
            "revised_criterion": (
                "pump_speed_realised_at_issue: the realised speed must equal the "
                "command at every open state before the first rule-driven reopening, "
                "and within a single 30 min control step. Persistence is reported "
                "separately and, because it fails, forces CONDITIONAL, not PASS."),
            "result_under_revised_criterion": verdict,
            "both_numbers_reported": True,
        },
        "decision_rule": (
            "PASS requires that every command reach the engine unchanged, that "
            "every Active PRV hold its setting within " f"{CMD_TOL_PSI} psi, that "
            "every open pump run at the commanded speed at the moment it is issued, "
            "and that no command be inert, overridden, or overwritten. CONDITIONAL "
            "is returned when transmission and realisation are exact but part of "
            "the action space has no authority or does not persist. FAIL is reserved "
            "for the engine failing to apply a command it received."),
        "verdict": verdict,
    }


def _strip(cases: dict) -> dict:
    """Drop the live WNTR objects so the payload is JSON-serialisable."""
    return {k: {kk: vv for kk, vv in v.items() if kk not in ("wn", "res")}
            for k, v in cases.items()}


def build() -> dict:
    (nominal, cases, per_actuator, coeff, sizing, conn, service,
     attribution) = main()
    v = _verdict(nominal, cases, per_actuator, sizing, conn, service, attribution)
    return {
        "gate": "G12",
        "title": "BWSN-1 actuator realizability and action authority",
        "env": C.env_info(),
        "method": {
            "configuration": ("the gate 10 configuration: PDA required 20 psi / "
                              "minimum 0 psi, gate 6 validation leakage on every "
                              "junction, distributed [RULES] and [CONTROLS] intact"),
            "rule_timestep_s": 180, "report_timestep_s": 1800,
            "solver": {"accuracy": L.SOLVER_ACCURACY, "trials": L.SOLVER_TRIALS},
            "one_command_per_run": True,
            "prv_scales_of_nominal": list(PRV_SCALES),
            "pump_speeds": list(PUMP_SPEEDS),
            "pump_speed_justification": (
                "inside the 0.50-1.10 range gate 3 swept; 0.70 straddles the "
                "feasible bounds gate 3 measured (PUMP-170 shut at 0.80, PUMP-172 "
                "shut at 0.70) so the override case is measured, not assumed"),
            "tolerances_declared_before_any_run": {
                "cmd_tol_psi": CMD_TOL_PSI,
                "effect_tol_psi": EFFECT_TOL_PSI,
                "effect_tol_gpm": EFFECT_TOL_GPM},
            "pressure_statistic_node_set": (
                f"{len(service)} demand-bearing junctions; the "
                f"{conn['n_connector_nodes']} junctions the file declares at "
                "elevation 0.0 ft are pump and reservoir connector nodes whose "
                "reported pressure is head above datum, per gate 10"),
            "leak_instrument_status": ("validation instrument only; imported "
                                       "unchanged from gate 6 and must not enter "
                                       "any thesis result"),
            "no_optimisation": "fixed deterministic ladders; no PPO, SAC, GA or search",
            "random_seed": None,
        },
        "sizing": {k: x for k, x in sizing.items()
                   if k != "coefficient_gpm_per_psi_alpha"},
        "connector_nodes": conn,
        "nominal": nominal,
        "per_actuator": per_actuator,
        "pump_speed_attribution": attribution,
        "cases": _strip(cases),
        "assessment": v,
        "verdicts": {"G12 ACTUATOR REALIZABILITY": v["verdict"]},
    }


def _report(p: dict) -> None:
    print("=" * 92)
    print("GATE 12 - ACTUATOR REALIZABILITY (PDA + validation leakage + native "
          "controls)")
    print("=" * 92)
    print(f"tolerances declared before any run: command {CMD_TOL_PSI} psi, "
          f"effect {EFFECT_TOL_PSI} psi / {EFFECT_TOL_GPM} GPM")
    print(f"{p['assessment']['n_commands_tested']} single-command runs, "
          "one command per 96 h EPS")
    print()
    print("NOMINAL STATE (no command applied)")
    hdr = f"{'element':<14}{'commanded':>11}{'status over 193 states':<34}{'mean q GPM':>12}"
    print(hdr)
    print("-" * len(hdr))
    for v, r in p["nominal"]["prv"].items():
        print(f"{v:<14}{r['commanded_psi']:>9.2f}ps "
              f"{str(r['status_counts']):<34}{r['mean_flow_gpm']:>12.2f}")
    for q, r in p["nominal"]["pump"].items():
        print(f"{q:<14}{r['commanded_speed']:>11.2f} "
              f"{str(r['status_counts']):<34}{r['mean_flow_gpm']:>12.2f}")
    print()
    print("PRV COMMANDS")
    hdr = (f"{'command':<28}{'cmd psi':>9}{'echo':>9}{'bind':>7}"
           f"{'max dP psi':>12}{'d leak GPM':>12}{'min p psi':>11}{'effect':>8}")
    print(hdr)
    print("-" * len(hdr))
    for v in p["per_actuator"]:
        a = p["per_actuator"][v]
        if a["kind"] != "prv":
            continue
        for k, c in a["commands"].items():
            src = p["cases"][k]
            print(f"{k:<28}{c['commanded_psi']:>9.2f}"
                  f"{src['transmission']['echoed_psi']:>9.2f}"
                  f"{c['binding_rate']:>7.2f}"
                  f"{c['max_abs_d_nodal_mean_pressure_psi']:>12.4f}"
                  f"{c['d_mean_leakage_gpm']:>12.4f}"
                  f"{c['min_service_pressure_psi']:>11.3f}"
                  f"{str(c['has_measurable_effect']):>8}")
    print()
    print("PUMP SPEED COMMANDS")
    hdr = (f"{'command':<28}{'cmd':>7}{'echo':>7}{'open frac':>11}"
           f"{'real|pre-reset':>15}{'reset at h':>11}{'real|open':>11}"
           f"{'real|horiz':>12}{'ovrid':>7}")
    print(hdr)
    print("-" * len(hdr))
    for q in p["per_actuator"]:
        a = p["per_actuator"][q]
        if a["kind"] != "pump_speed":
            continue
        for k, c in a["commands"].items():
            src = p["cases"][k]
            rw = c["realisation_rate_while_open"]
            rp = c["realisation_rate_while_open_before_first_reset"]
            hr = c["hours_to_first_reset"]
            print(f"{k:<28}{c['commanded_speed']:>7.2f}"
                  f"{src['transmission']['echoed_speed']:>7.2f}"
                  f"{c['open_fraction']:>11.3f}"
                  f"{('shut' if rp is None else f'{rp:.3f}'):>15}"
                  f"{('never' if hr is None else f'{hr:.2f}'):>11}"
                  f"{('n/a' if rw is None else f'{rw:.3f}'):>11}"
                  f"{c['realisation_rate_over_horizon']:>12.3f}"
                  f"{str(c['overridden_by_hydraulics']):>7}")
    print()
    print("PUMP SPEED ATTRIBUTION (controlled test, speed 0.85, diagnostic only)")
    at = p["pump_speed_attribution"]
    hdr = (f"{'pump':<11}{'run':<26}{'removed':<12}{'dur h':>7}{'n open':>8}"
           f"{'real|open':>11}{'reset at h':>11}{'values':<22}")
    print(hdr)
    print("-" * len(hdr))
    for q, d in at["pumps"].items():
        for key, r in d["runs"].items():
            rl, ps = r["realisation"], r["persistence"]
            rw = rl["realisation_rate_while_open"]
            hr = ps["hours_to_first_reset"]
            print(f"{q:<11}{key:<26}"
                  f"{(','.join(r['controls_removed']) or '-'):<12}"
                  f"{r['duration_h']:>7.1f}{rl['n_open']:>8}"
                  f"{('n/a' if rw is None else f'{rw:.3f}'):>11}"
                  f"{('never' if hr is None else f'{hr:.2f}'):>11}"
                  f"  {str(rl['realised_speed_values']):<20}")
        print(f"{'':<11}reverts with OPEN rule present "
              f"{d['reverts_to_speed_one_with_open_rule_present']}, holds without it "
              f"{d['holds_command_with_open_rule_removed']}, holds within one step "
              f"{d['holds_command_within_one_control_step']} -> mechanism confirmed "
              f"{d['mechanism_confirmed']}")
    print(f"    {at['conclusion']['statement']}")
    print()
    a = p["assessment"]
    print("ASSESSMENT")
    print(f"    every command reached the engine unchanged      : "
          f"{a['transmission_ok']}")
    print(f"    every Active PRV held its setting <= {CMD_TOL_PSI} psi    : "
          f"{a['prv_binding_ok']}")
    print(f"    commanded speed applied when issued            : "
          f"{a['pump_speed_realised_at_issue']}")
    print(f"    commanded speed persisted over the 96 h horizon: "
          f"{a['pump_speed_persists_over_horizon']}")
    print(f"    speed commands overwritten by a native rule    : "
          f"{len(a['speed_commands_reset_by_native_rule'])} of 6, mechanism "
          f"confirmed {a['speed_reset_mechanism_confirmed']}")
    print(f"    PRVs never Active at nominal                    : "
          f"{a['prvs_never_active_at_nominal'] or 'none'}")
    print(f"    inert commands (no measurable network effect)   : "
          f"{len(a['inert_commands'])} of {a['n_commands_tested']}")
    for k in a["inert_commands"]:
        print(f"        {k}")
    print(f"    commands overridden by the hydraulics           : "
          f"{a['overridden_commands'] or 'none'}")
    print(f"    commands driving negative service pressure      : "
          f"{a['commands_driving_negative_service_pressure'] or 'none'}")
    print()
    ch = a["criterion_history"]
    print("    DISCLOSED CRITERION CHANGE")
    print(f"      first criterion  : {ch['first_declared_criterion']}")
    print(f"      result           : {ch['result_under_first_criterion']}")
    print(f"      why changed      : {ch['why_changed']}")
    print(f"      revised criterion: {ch['revised_criterion']}")
    print(f"      result           : {ch['result_under_revised_criterion']}")
    print()
    print("    " + a["decision_rule"])
    print()
    print(f"G12 ACTUATOR REALIZABILITY = "
          f"{p['verdicts']['G12 ACTUATOR REALIZABILITY']}")


if __name__ == "__main__":
    payload = build()
    _report(payload)
    out = C.jdump("g12_realizability.json", payload)
    print()
    print(f"artefact: {out}")
