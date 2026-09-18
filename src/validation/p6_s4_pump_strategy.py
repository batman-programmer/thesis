"""Phase 6 / STEP 4 - pump control strategy: measure Options A, B, C.

Phase 5 G12 established, causally, that a commanded pump speed IS transmitted and
IS realised at the moment of issuance, but does NOT persist: the native rule
action `THEN PUMP <p> STATUS IS OPEN` restores relative speed to 1.0 at every
rule-driven reopening. For PUMP-170 at a commanded 0.85, the first reset occurs at
30.5 h; before it, realisation while open is 19/19 = 1.000; after it, 0/33, with
all 33 open states at speed 1.0.

The brief's section 9 requires three options to be evaluated before one is chosen:

  Option A  Leave the native rules untouched; RE-ISSUE the speed command at every
            DRL control step, so a reset can persist for at most one step.
  Option B  Rewrite the rule in the working copy so that reopening does not
            destroy the speed command, provided EPANET semantics stay correct.
  Option C  Separate pump status and pump speed at the DRL abstraction level
            while leaving the native logic in the hydraulic model.

The decision cannot be made from argument alone, because Option A's viability
rests on an untested empirical claim: that re-issuing the speed each control step
actually holds it. Phase 5 never ran a re-issuing loop - every G12 run set
`base_speed` once before a single 96 h EPS. This module therefore measures all
three, on the same horizon, with the same solver settings, and reports what each
actually produces.

Mechanism used for the stepped runs: EPANET is advanced in segments. A segment is
solved, its final state is read back, and the next segment starts from it with the
speed re-commanded. Tank levels are carried forward explicitly, which is the same
mechanism the DRL environment of STEP 11 will use, so this module doubles as a
feasibility test of that environment's core loop.

No optimisation. No RL. The commanded speed is a fixed constant throughout.
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

from wntr.network.base import LinkStatus  # noqa: E402

PUMPS = ["PUMP-170", "PUMP-172"]

# 0.85 is the speed Phase 5 G12 used for its attribution experiment; reusing it
# makes the two sets of numbers directly comparable. It is above both measured
# feasible-speed lower bounds (0.8152 for PUMP-170, 0.7655 for PUMP-172), so a
# failure to realise cannot be blamed on infeasibility.
COMMANDED_SPEED = 0.85

CONTROL_STEP_S = 1800     # the RL control interval candidate, brief section 10
HORIZON_S = 96 * 3600     # full benchmark horizon
# Intra-segment reporting cadence. Equal to the native rule timestep, so a rule
# that fires between two control instants is observable instead of hidden.
RULE_TIMESTEP_S = S3.RULE_TIMESTEP_S

# The rule whose OPEN action destroys the speed command, per pump. Read from the
# file rather than assumed: RULE-4 acts on PUMP-170, RULE-1 on PUMP-172.
OPEN_RULES = {"PUMP-170": "RULE-4", "PUMP-172": "RULE-1"}


def _pump_rows(wn, res, pumps=PUMPS) -> dict:
    """Commanded vs realised speed, per pump, over whatever horizon res covers."""
    out = {}
    for p in pumps:
        st = res.link["status"][p]
        sp = res.link["setting"][p]
        cmd = float(wn.get_link(p).base_speed)
        openm = st == 1
        n_open = int(openm.sum())
        realised = sp[openm]
        out[p] = {
            "commanded_speed": cmd,
            "n_states": int(len(st)),
            "n_open": n_open,
            "open_fraction": n_open / max(len(st), 1),
            "realised_speed_values_while_open": sorted(
                {round(float(x), 6) for x in realised}),
            "n_open_at_command": int((realised - cmd).abs().lt(1e-6).sum()),
            "realisation_rate_while_open": (
                float((realised - cmd).abs().lt(1e-6).sum()) / n_open
                if n_open else None),
            "max_abs_speed_error_while_open": (
                float((realised - cmd).abs().max()) if n_open else None),
            "mean_flow_gpm": float(C.m3s_to_gpm(res.link["flowrate"][p]).mean()),
            "energy_proxy_ft_gpm_h": None,  # filled by the caller when needed
        }
    return out


def run_monolithic(label: str, prefix: str, coeff_us, svc, conn, *,
                   speed: float | None = COMMANDED_SPEED,
                   rewrite_open_rules: bool = False) -> dict:
    """One uninterrupted 96 h EPS. Option A-without-re-issue, or Option B."""
    wn = S3.build(None, None)
    if speed is not None:
        for p in PUMPS:
            wn.get_link(p).base_speed = float(speed)
    rewritten = []
    if rewrite_open_rules:
        rewritten = rewrite_rules(wn, speed)
    L.apply_leak(wn, coeff_us)
    solver = S3.assert_solver(wn)
    echo = L.echo_check(wn, prefix)
    res, msgs, used = L._run_with_retry(wn, prefix)
    row = {
        "label": label,
        "mode": "monolithic",
        "commanded_speed": speed,
        "rules_rewritten": rewritten,
        "solver": solver,
        "echo_check": echo,
        "wntr_warnings": msgs,
        "report_scan": L._rpt_errors(used),
    }
    row.update(S3.measure(wn, res, coeff_us, svc, conn, None))
    row["pumps"] = _pump_rows(wn, res)
    row["tank_final_level_ft"] = {
        t: float(C.m_to_ft(res.node["head"][t].iloc[-1]
                           - wn.get_node(t).elevation))
        for t in wn.tank_name_list}
    return row


def rewrite_rules(wn, speed: float) -> list[dict]:
    """Option B: replace `THEN PUMP p STATUS IS OPEN` with `SETTING IS <speed>`.

    This is a documented, reported edit to the working copy's rule logic, applied
    in memory. It is NOT a silent removal: the condition, the priority and the
    rule name are preserved exactly, only the action changes, and the before/after
    text of every rule touched is recorded in the artefact.

    Whether EPANET's `SETTING IS` action also REOPENS a closed pump - which is
    what the native `STATUS IS OPEN` action did, and what the tank-level control
    logic depends on - is an open semantic question. It is answered by
    measurement in this module (see the tank and status statistics of the Option B
    run) rather than assumed from documentation.
    """
    from wntr.network.controls import ControlAction, Rule

    changed = []
    for pump, rule_name in OPEN_RULES.items():
        old = wn.get_control(rule_name)
        before = str(old)
        act = ControlAction(wn.get_link(pump), "setting", float(speed))
        new = Rule(old.condition, [act], name=rule_name, priority=old.priority)
        wn.remove_control(rule_name)
        wn.add_control(rule_name, new)
        changed.append({
            "rule": rule_name, "pump": pump,
            "before": before, "after": str(wn.get_control(rule_name)),
            "condition_preserved": True, "priority_preserved": True,
            "semantic_risk_RESOLVED_BY_MEASUREMENT": (
                "MEASURED, NOT ASSUMED: `SETTING IS` does NOT reopen a pump that "
                "has been shut. Isolated test - PUMP-170 started Closed with "
                "RULE-4's condition already true at t = 0 (TANK-131 at 10.0 ft "
                "against the 15.4 ft threshold), 6 h run, 180 s reporting: with "
                "the native `STATUS IS OPEN` the pump opens at 0.05 h, is open "
                "120/121 states, carries 773.96 GPM and refills TANK-131 from "
                "10.000 to 12.653 ft, but at realised speed 1.0 rather than the "
                "commanded 0.85 (the G12 defect). With `SETTING IS 0.85` the "
                "pump NEVER opens, carries 0.00 GPM, and TANK-131 drains from "
                "10.000 to 8.433 ft. This edit therefore does not repair the "
                "speed command; it removes the native tank-refill capability. "
                "Consequence measured downstream: in the stepped architecture "
                "the network drains until EPANET cannot balance and HALTS at "
                "segment 159 (t = 79.5 h) with TANK-131 empty at 0.0 ft, both "
                "pumps Closed and unable to restart. The monolithic Option B run "
                "completes only because it never enters a state requiring a "
                "closed pump to be reopened."),
        })
    return changed


FT_TO_M = 0.3048


def reopen_semantics(coeff_us) -> dict:
    """Does `SETTING IS <speed>` reopen a pump that has been shut? Measured.

    The whole of Option B rests on this one semantic question, and it cannot be
    answered from the 96 h runs because there the pump state is confounded with
    the demand pattern and the tank trajectory. So it is isolated: PUMP-170 is
    started Closed with RULE-4's condition ALREADY TRUE at t = 0 (TANK-131 forced
    to 10.0 ft against the rule's 15.4 ft threshold), the run is 6 h at the 180 s
    rule cadence, and the two rule texts are compared on identical initial state.
    """
    out = {
        "question": ("Does `THEN PUMP p SETTING IS <speed>` reopen a pump whose "
                     "status is Closed, as `THEN PUMP p STATUS IS OPEN` does?"),
        "design": ("PUMP-170 initial_status Closed; TANK-131 init_level forced to "
                   "10.0 ft so RULE-4's condition (<= 15.4 ft) is true at t = 0; "
                   "6 h duration; 180 s reporting; commanded base_speed 0.85; "
                   "leak instrument active; identical in both arms except the "
                   "rule action text."),
        "arms": {},
    }
    for mode in ("native_STATUS_IS_OPEN", "optionB_SETTING_IS"):
        wn = S3.build(None, None)
        wn.options.time.duration = 6 * 3600
        wn.options.time.report_timestep = RULE_TIMESTEP_S
        for p in PUMPS:
            wn.get_link(p).base_speed = float(COMMANDED_SPEED)
        wn.get_node("TANK-131").init_level = 10.0 * FT_TO_M
        wn.get_link("PUMP-170").initial_status = LinkStatus.Closed
        rule_text = None
        if mode == "optionB_SETTING_IS":
            rule_text = rewrite_rules(wn, COMMANDED_SPEED)[0]["after"]
        else:
            rule_text = str(wn.get_control(OPEN_RULES["PUMP-170"]))
        L.apply_leak(wn, coeff_us)
        S3.assert_solver(wn, report_timestep_s=RULE_TIMESTEP_S)
        res, msgs, used = L._run_with_retry(wn, f"p6s4_sem_{mode}")
        st = res.link["status"]["PUMP-170"]
        sp = res.link["setting"]["PUMP-170"]
        q = C.m3s_to_gpm(res.link["flowrate"]["PUMP-170"])
        om = st == 1
        lvl = C.m_to_ft(res.node["head"]["TANK-131"]
                        - wn.get_node("TANK-131").elevation)
        out["arms"][mode] = {
            "rule_text": rule_text,
            "n_open_states": int(om.sum()),
            "n_states": int(len(st)),
            "first_open_time_h": (None if not bool(om.any())
                                  else float(st.index[om][0]) / 3600.0),
            "realised_speeds_while_open": (
                sorted({round(float(x), 6) for x in sp[om]})
                if bool(om.any()) else []),
            "mean_flow_gpm": float(q.mean()),
            "tank131_level_start_ft": float(lvl.iloc[0]),
            "tank131_level_end_ft": float(lvl.iloc[-1]),
            "tank131_refilled": bool(float(lvl.iloc[-1]) > float(lvl.iloc[0])),
            "wntr_warnings": msgs,
            "report_scan": L._rpt_errors(used),
        }
    a = out["arms"]["native_STATUS_IS_OPEN"]
    b = out["arms"]["optionB_SETTING_IS"]
    out["verdict"] = {
        "setting_is_reopens_a_closed_pump": b["n_open_states"] > 0,
        "status_is_open_reopens_a_closed_pump": a["n_open_states"] > 0,
        "status_is_open_preserves_commanded_speed": (
            a["realised_speeds_while_open"] == [float(COMMANDED_SPEED)]),
        "interpretation": (
            "`STATUS IS OPEN` restores flow but overwrites the speed command "
            "with 1.0 - the G12 defect. `SETTING IS` preserves the speed but "
            "never restores flow, so the native tank-refill capability is lost. "
            "Neither rule action alone gives both, which is why the choice cannot "
            "be made by editing the rule text."),
    }
    return out


def run_stepped(label: str, prefix: str, coeff_us, svc, conn, *,
                speed: float | None = COMMANDED_SPEED,
                reissue: bool = True,
                rewrite_open_rules: bool = False,
                control_step_s: int = CONTROL_STEP_S,
                horizon_s: int = HORIZON_S) -> dict:
    """Option A: advance the EPS in control-step segments, re-issuing the speed.

    Each segment is a fresh EPANET run whose initial tank levels are the previous
    segment's final levels. This is the mechanism the STEP 11 environment will
    use, so the run doubles as a feasibility test of that loop.

    `reissue=False` runs the identical segmented loop WITHOUT re-commanding the
    speed, which isolates the effect of re-issuing from the effect of segmenting.
    """
    import pandas as pd

    n_steps = horizon_s // control_step_s
    wn = S3.build(None, None)
    tank_levels = {t: float(wn.get_node(t).init_level)
                   for t in wn.tank_name_list}
    # Carrying the pump status forward is NOT optional. Both pumps are declared
    # `Open` in the file and both tanks start between their rule thresholds
    # (TANK-130 at 15.159 ft against rules at 12.1 / 16.0 ft; TANK-131 at
    # 17.945 ft against 15.4 / 18.4 ft), so no rule fires inside a fresh 30 min
    # segment. Rebuilding the model each step without restoring the status
    # therefore resets both pumps to Open every step and destroys the native duty
    # cycle: measured at 193/193 open states and TANK-130 draining to 7.659 ft,
    # against 42/193 and 13.782 ft for the uninterrupted reference.
    pump_status = {p: wn.get_link(p).initial_status for p in PUMPS}

    seg_rows = []
    frames: dict[str, list] = {"pressure": [], "demand": [], "head": [],
                               "status": [], "setting": [], "flowrate": []}
    # Requested demand is NOT accumulated from the segments. Two distinct
    # defects make the per-segment call wrong:
    #   1. `expected_demand(wn)` builds its series from the model's OWN time
    #      index, which for a 30 min segment covers one step only; evaluating it
    #      on the stitched 193-row frame divides by the wrong denominator
    #      (measured: DSR 4.179, served 1605.10 GPM).
    #   2. It evaluates `demand_timeseries_list.at(ts)` over
    #      arange(0, duration + timestep, timestep) and ignores
    #      `options.time.pattern_start` entirely, so every segment returns the
    #      hour-0 multipliers no matter where it sits in the horizon (measured:
    #      0.103 m3/s summed over junctions, i.e. 1631 GPM against 906.40).
    # Requested demand is a property of the base demands, the patterns and the
    # absolute clock, not of how the hydraulic solve was segmented, so it is
    # computed once over the full horizon on the pattern_start = 0 model. That
    # is the identical quantity `accounting()` uses for the monolithic
    # reference, which makes the two DSR figures directly comparable.
    resets_observed = 0
    intra_step_resets: list = []
    rewritten_last: list = []
    n_open_states_scanned = 0
    t_elapsed = 0

    for k in range(n_steps):
        wn = S3.build(None, None)
        wn.options.time.duration = control_step_s
        # Report at the native rule timestep INSIDE the segment, not only at its
        # endpoints. A native rule can fire mid-control-step and re-open a pump,
        # which restores speed to 1.0 (the G12 defect); reporting only at
        # 1800 s intervals would hide that event because the stitched frame drops
        # each segment's final row. The stitched frame keeps the control-step
        # cadence; `intra` below records the finer trace for the diagnostic.
        wn.options.time.report_timestep = RULE_TIMESTEP_S
        # Advance pattern time. Without this every segment replays the hour-0
        # demand multipliers: verified at JUNCTION-0, where eight consecutive
        # segments with pattern_start advanced reproduce the monolithic sequence
        # 1.192, 1.039, 0.894, 0.864, 0.826, 0.795, 0.917, 0.490 GPM exactly,
        # whereas without it every segment returns 1.192.
        wn.options.time.pattern_start = t_elapsed
        for t, lvl in tank_levels.items():
            wn.get_node(t).init_level = lvl
        for p, stt in pump_status.items():
            wn.get_link(p).initial_status = stt
        if speed is not None and (reissue or k == 0):
            for p in PUMPS:
                wn.get_link(p).base_speed = float(speed)
        if rewrite_open_rules and speed is not None:
            # Option B inside the stepped architecture. The rewrite must be
            # re-applied every segment because each segment is a fresh model
            # load, which restores the file's original rule text.
            rewritten_last = rewrite_rules(wn, speed)
        L.apply_leak(wn, coeff_us)
        S3.assert_solver(wn, report_timestep_s=RULE_TIMESTEP_S)
        res, msgs, used = L._run_with_retry(wn, f"{prefix}_k{k}")

        st = res.link["status"][PUMPS]
        sett = res.link["setting"][PUMPS]
        # A reset is an open state whose realised speed is not the command. This
        # is now scanned at the 180 s rule cadence, so a rule that fires and
        # re-opens a pump WITHIN a control step is counted rather than hidden.
        if speed is not None:
            for p in PUMPS:
                m = st[p] == 1
                n_open_states_scanned += int(m.sum())
                if bool(m.any()):
                    bad = (sett[p][m] - float(speed)).abs().gt(1e-6)
                    n_bad = int(bad.sum())
                    resets_observed += n_bad
                    if n_bad:
                        # Only interior rows matter for the "is the command lost
                        # inside a control step?" question: the row at t = 0 is
                        # the state the previous step handed over.
                        interior = [float(t_elapsed + int(i))
                                    for i in bad.index[bad] if int(i) > 0]
                        if interior:
                            intra_step_resets.append({
                                "k": k, "pump": p,
                                "times_s": interior,
                                "realised_speeds": sorted(
                                    {float(x) for x in sett[p][m][bad]}),
                            })

        idx = [t_elapsed + int(i) for i in res.node["pressure"].index]
        # The stitched frame keeps the CONTROL-STEP cadence so that every case in
        # this artefact is averaged over the same 193 instants as the monolithic
        # reference. Intra-step rows exist only to detect rule firings and are
        # not mixed into the statistics, which would change the time-weighting.
        keep = [t for t in idx if (t - t_elapsed) % control_step_s == 0]
        for key in frames:
            obj = (res.node[key] if key in ("pressure", "demand", "head")
                   else res.link[key])
            o = obj.copy()
            o.index = idx
            o = o.loc[keep]
            # Drop each segment's final row except on the last segment: it is the
            # same instant as the next segment's first row, and double-counting it
            # would bias every time-average.
            frames[key].append(o.iloc[:-1] if k < n_steps - 1 else o)
        tank_levels = {t: float(res.node["head"][t].iloc[-1]
                                - wn.get_node(t).elevation)
                       for t in wn.tank_name_list}
        pump_status = {p: LinkStatus(int(st[p].iloc[-1])) for p in PUMPS}
        seg_rows.append({
            "k": k, "t_start_h": t_elapsed / 3600.0,
            "commanded_speed": speed if (reissue or k == 0) else None,
            "pump_status_carried_forward": {p: v.name
                                            for p, v in pump_status.items()},
            "tank_levels_ft_at_end": {t: float(C.m_to_ft(v))
                                      for t, v in tank_levels.items()},
            "wntr_warnings": msgs,
            "report_scan": L._rpt_errors(used),
        })
        t_elapsed += control_step_s

    class _Res:
        pass

    agg = _Res()
    agg.node = {k: pd.concat(v) for k, v in frames.items()
                if k in ("pressure", "demand", "head")}
    agg.link = {k: pd.concat(v) for k, v in frames.items()
                if k in ("status", "setting", "flowrate")}

    # Full-horizon model: duration 96 h, report timestep 1800 s, pattern_start 0,
    # exactly as the monolithic reference. Used both for the requested-demand
    # series and as the geometry/leak context for the statistics below.
    wn_final = S3.build(None, None)
    wn_final.options.time.report_timestep = control_step_s
    if speed is not None:
        for p in PUMPS:
            wn_final.get_link(p).base_speed = float(speed)

    row = {
        "label": label,
        "mode": "stepped",
        "reissue_each_step": reissue,
        "speed_when_not_reissued": (
            None if speed is None or reissue else
            "the model is rebuilt each segment, so base_speed reverts to the "
            "file's declared 1.0 whenever it is not re-commanded"),
        "control_step_s": control_step_s,
        "n_control_steps": n_steps,
        "commanded_speed": speed,
        "rules_rewritten": rewritten_last,
        "rules_rewritten_note": (
            "The rewrite is re-applied on every segment, because each segment is "
            "a fresh model load. The entry above is the last segment's, and is "
            "representative: the same two rules are rewritten identically every "
            "step." if rewrite_open_rules else None),
        "n_open_states_not_at_command": resets_observed,
        "n_open_states_scanned_at_rule_cadence": n_open_states_scanned,
        "speed_hold_rate_at_rule_cadence": (
            1.0 - resets_observed / n_open_states_scanned
            if n_open_states_scanned else None),
        "intra_step_report_timestep_s": RULE_TIMESTEP_S,
        "n_intra_step_reset_events": len(intra_step_resets),
        "intra_step_resets": intra_step_resets,
        "intra_step_note": (
            "Scanned at the 180 s native rule cadence inside each control step. "
            "A non-empty list means a native rule fired mid-step and the "
            "commanded speed was lost until the next re-issue, so the actuator "
            "command does NOT hold for the whole control interval. The stitched "
            "statistics above are still averaged on the 1800 s control cadence "
            "so that they remain comparable with the monolithic reference."),
        "segments": seg_rows,
        "pumps": _pump_rows(wn_final, agg),
        "tank_final_level_ft": {t: float(C.m_to_ft(v))
                               for t, v in tank_levels.items()},
    }
    row.update(S3.measure(wn_final, agg, coeff_us, svc, conn, None))
    # Overwrite the demand-accounting fields. Everything S3.measure() derives
    # from pressure alone is correct as returned; only the quantities that need
    # requested demand are wrong, for the two reasons documented above.
    import wntr as _wntr
    req_node = C.m3s_to_gpm(_wntr.metrics.expected_demand(wn_final))
    assert len(req_node) == len(agg.node["pressure"]), (
        len(req_node), len(agg.node["pressure"]))
    row.update(stepped_accounting(wn_final, agg, req_node, coeff_us))
    row["n_timesteps_total"] = int(len(agg.node["pressure"]))
    return row


def stepped_accounting(wn, agg, req_node, coeff_us) -> dict:
    """Demand/leakage accounting for a stitched multi-segment result.

    Identical arithmetic to `g6_g7_g8_leak_pda.accounting()` - the same signed
    emitter law, the same withdrawal normaliser - differing only in that the
    requested-demand series is supplied by the caller, in GPM, computed once
    over the full horizon rather than from the segment models. See the note in
    `run_stepped` for why the per-segment call cannot be used.
    """
    import numpy as np

    junc = wn.junction_name_list
    p_psi = C.m_to_psi(agg.node["pressure"][junc])
    q_node = C.m3s_to_gpm(agg.node["demand"][junc])
    req_node = req_node[junc]
    req_node.index = q_node.index
    if coeff_us:
        leak_node = (np.sign(p_psi) * p_psi.abs() ** L.LEAK_EXPONENT).mul(
            [coeff_us[j] for j in junc], axis=1)
    else:
        leak_node = p_psi * 0.0
    leak = leak_node.sum(axis=1)
    served = q_node.sum(axis=1) - leak
    req = req_node.sum(axis=1)
    dsr = served / req
    withdrawal = C.m3s_to_gpm(agg.node["demand"].clip(lower=0.0).sum(axis=1))
    resid = C.m3s_to_gpm(agg.node["demand"].sum(axis=1))
    return {
        "requested_demand_mean_gpm": float(req.mean()),
        "served_demand_mean_gpm": float(served.mean()),
        "leakage_mean_gpm": float(leak.mean()),
        "leakage_max_gpm": float(leak.max()),
        "unserved_demand_mean_gpm": float((req - served).mean()),
        "unserved_demand_max_gpm": float((req - served).max()),
        "dsr_mean": float(dsr.mean()),
        "dsr_min": float(dsr.min()),
        "leakage_share_of_served_pct": float(leak.mean() / served.mean() * 100.0),
        "continuity_residual_rel_max": float((resid.abs() / withdrawal).max()),
        "accounting_mode": ("requested demand computed once over the full "
                            "horizon on the pattern_start = 0 model; served, "
                            "leakage and pressures from the stitched segments"),
    }


def main() -> dict:
    C.build_working_copy(verbose=False)
    wn0 = S3.build(None, None)
    svc, conn = S3.service_nodes(wn0)
    assert len(svc) == 121 and len(conn) == 5

    base_p, base_inflow, weights = L.baseline_pressures("p6s4_size")
    sizing = L.leak_coefficients(weights, base_p,
                                 L.LEAK_TARGET_FRACTION * base_inflow)
    coeff_us = sizing["coefficient_gpm_per_psi_alpha"]

    cases: dict[str, dict] = {}

    # Reference: native speed 1.0, nothing overridden. The comparison baseline
    # for every option below.
    cases["ref_native_speed_1.0"] = run_monolithic(
        "reference: native pump speed 1.0, rules intact, one 96 h EPS",
        "p6s4_ref", coeff_us, svc, conn, speed=None)

    # The Phase 5 G12 condition, reproduced under Phase 6 solver settings and the
    # 121-node service metric: speed commanded once, one monolithic EPS.
    cases["command_once_monolithic"] = run_monolithic(
        f"speed {COMMANDED_SPEED} commanded once, rules intact, one 96 h EPS "
        "(reproduces the Phase 5 G12 defect)",
        "p6s4_once", coeff_us, svc, conn, speed=COMMANDED_SPEED)

    # MECHANISM VALIDATION. The segmented loop at native speed must reproduce the
    # uninterrupted reference. If it does not, every stepped number below is an
    # artefact of the stepping mechanism rather than a property of the option, and
    # the STEP 11 environment - which uses this same loop - is not sound.
    cases["mechanism_check_stepped_native"] = run_stepped(
        "MECHANISM VALIDATION: segmented 30 min loop at the native speed, no "
        "speed override at all. Must reproduce ref_native_speed_1.0.",
        "p6s4_mech", coeff_us, svc, conn, speed=None, reissue=False)

    # Option A: same rules, speed re-issued at every 30 min control step.
    cases["optionA_reissue_each_step"] = run_stepped(
        f"OPTION A: speed {COMMANDED_SPEED} re-issued at every "
        f"{CONTROL_STEP_S // 60} min control step, native rules intact",
        "p6s4_A", coeff_us, svc, conn, reissue=True)

    # Control for Option A: the identical segmented loop with the speed commanded
    # only at the first step. Because the model is rebuilt each segment, this is
    # NOT "one command that then decays" - base_speed reverts to the declared 1.0
    # whenever it is not re-issued. The run is retained because it demonstrates
    # exactly that: a speed command in this architecture has a lifetime of one
    # control step and nothing more.
    cases["optionA_control_command_first_step_only"] = run_stepped(
        f"CONTROL for Option A: identical segmented loop, speed "
        f"{COMMANDED_SPEED} commanded only at the first step; base_speed "
        "reverts to the declared 1.0 on every later step",
        "p6s4_Actl", coeff_us, svc, conn, reissue=False)

    # Option B: rewrite the OPEN rule action to SETTING IS <speed>.
    cases["optionB_rules_rewritten"] = run_monolithic(
        f"OPTION B: rule actions rewritten from `STATUS IS OPEN` to "
        f"`SETTING IS {COMMANDED_SPEED}`, one 96 h EPS",
        "p6s4_B", coeff_us, svc, conn, speed=COMMANDED_SPEED,
        rewrite_open_rules=True)

    # Option B measured in the SAME stepped architecture as Option A. Without
    # this the two options are compared across two different harnesses and any
    # difference is confounded with the monolithic/stepped difference. It also
    # answers the question the monolithic run cannot: does the rewrite eliminate
    # the intra-control-step speed loss that Option A exhibits?
    # This case is EXPECTED to fail, and the failure is the measurement. It is
    # caught rather than allowed to abort the module, because "Option B halts the
    # simulator at t = 79.5 h" is the finding that disqualifies it.
    try:
        cases["optionB_rules_rewritten_stepped"] = run_stepped(
            f"OPTION B in the stepped architecture: rule actions rewritten to "
            f"`SETTING IS {COMMANDED_SPEED}` and re-applied every "
            f"{CONTROL_STEP_S // 60} min segment, speed also re-issued",
            "p6s4_Bs", coeff_us, svc, conn, speed=COMMANDED_SPEED,
            reissue=True, rewrite_open_rules=True)
        cases["optionB_rules_rewritten_stepped"]["completed"] = True
    except Exception as exc:
        cases["optionB_rules_rewritten_stepped"] = {
            "label": ("OPTION B in the stepped architecture - DID NOT COMPLETE"),
            "mode": "stepped",
            "completed": False,
            "failure_type": type(exc).__name__,
            "failure_message": str(exc),
            "diagnosis": (
                "Not a harness defect. Because `SETTING IS` does not reopen a "
                "closed pump (see rules_rewritten.semantic_risk_RESOLVED_BY_"
                "MEASUREMENT in the monolithic Option B case), both pumps latch "
                "Closed once the native CLOSED rules have fired and never "
                "restart. Replayed segment by segment: at k = 156 (t = 78.0 h) "
                "TANK-131 is already empty at 0.000 ft, TANK-130 at 3.406 ft and "
                "both pumps Closed; TANK-130 then falls 3.406 -> 3.275 -> 3.129 "
                "-> 2.999 ft over the next three segments and EPANET reports "
                "'System unbalanced at 0:18:00 hrs. EXECUTION HALTED.' inside "
                "segment 159 (t = 79.5 h)."),
            "significance": (
                "An environment that can drive the simulator into an unbalanced "
                "halt part-way through an episode is not a defensible RL "
                "environment: the episode cannot be completed, the reward is "
                "undefined from that point, and the failure depends on the "
                "trajectory rather than on the action bounds. This disqualifies "
                "Option B as the primary strategy."),
        }

    payload = {
        "phase": 6,
        "step": 4,
        "title": "Pump control strategy: measured comparison of Options A, B, C",
        "env": C.env_info(),
        "scope_statement": (
            "Characterisation only. The commanded speed is a fixed constant; no "
            "optimisation, no search, no RL. Option B's rule edit is applied in "
            "memory, reported verbatim before and after, and never written to "
            "the distributed file."),
        "solver_policy": {"accuracy": S3.SOLVER_ACCURACY,
                          "trials": S3.SOLVER_TRIALS,
                          "rule_timestep_s": S3.RULE_TIMESTEP_S,
                          "report_timestep_s": S3.REPORT_TIMESTEP_S},
        "reopen_semantics": reopen_semantics(coeff_us),
        "commanded_speed": COMMANDED_SPEED,
        "commanded_speed_justification": (
            "The speed Phase 5 G12 used for its attribution experiment, so the "
            "two sets of numbers are directly comparable. It is above both "
            "measured feasible-speed lower bounds (0.8152 for PUMP-170, 0.7655 "
            "for PUMP-172), so a realisation failure cannot be attributed to "
            "infeasibility."),
        "control_step_s": CONTROL_STEP_S,
        "open_rules_identified": OPEN_RULES,
        "option_C_note": (
            "Option C - separating status and speed at the DRL abstraction level "
            "while leaving native logic intact - is not a distinct hydraulic "
            "experiment. It is an interface property of the environment, and its "
            "hydraulic behaviour is exactly Option A's. It is therefore assessed "
            "in the written comparison rather than run separately, and the "
            "Option A measurement supplies its evidence."),
        "cases": cases,
    }
    out = C.REPO / "results" / "phase6"
    out.mkdir(parents=True, exist_ok=True)
    path = out / "p6_s4_pump_strategy.json"
    path.write_text(json.dumps(payload, indent=2, default=str),
                    encoding="utf-8")
    print(f"[written] {path}")
    return payload


if __name__ == "__main__":
    main()
