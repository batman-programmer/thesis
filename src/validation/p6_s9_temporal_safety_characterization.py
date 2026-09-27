#!/usr/bin/env python3
"""WU-16 - STEP 9 TEMPORAL (sustained-action) safety characterization.

EVIDENCE ONLY. Central empirical question: can a purely SINGLE-STEP post-action
safety check MISS delayed hydraulic deterioration that emerges over the sustained
horizon as tank states evolve? Motivating WU-15 finding: the severe command
prv_lower_pump_lower has a decision-instant (report index 0, identical initial
tank levels) worst-node service pressure ~5.53 psi, but its sustained-horizon
worst ~1.29 psi (tanks drain over the 96 h EPS).

This script:
  * reuses the VALIDATED p6_s8 instrument (same 96 h EPS, solver policy, leak/PDA
    instrument, frozen 121-node service mask, native controls untouched) and the
    WU-15 module's pure helpers (encode/decode/project_state/rules) UNCHANGED;
  * extends one run to capture the raw WNTR result object so tank levels, pump
    realized speeds, and native-rule (pump STATUS) events become visible over the
    full horizon - quantities component_series does NOT expose;
  * loads the EXACT severe action from the persisted WU-15 JSON and verifies the
    ~5.53 / ~1.29 decision-instant / sustained values reproduce from disk;
  * contrasts SINGLE-STEP vs TRAJECTORY-AWARE safety and sweeps look-ahead
    horizons H in {1,2,4,8} control steps + full, purely by truncating the
    extracted trajectory (no extra solves);
  * does NOT select, rank, score, prefer, or recommend any mechanism, policy, or
    horizon; researcher_selection = null. No production wrapper, no reward.py,
    no PPO.

Reproducibility: EPANET is deterministic, so re-running reproduces every value.
The JSON carries a generated_utc stamp (NOT byte-reproduced), matching the p6_s8
measurement-script convention. _self_checks raises SystemExit on any failure.
"""
from __future__ import annotations

import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "results" / "phase6"
OUT = RESULTS / "p6_s9_temporal_safety_characterization.json"
P6S8_JSON = RESULTS / "p6_s8_reward_scale_analysis.json"
WU15_JSON = RESULTS / "p6_s9_safety_mechanism_characterization.json"

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src" / "env"))

import p6_s8_reward_scale_analysis as R8   # noqa: E402  (validated instrument)
import p6_s9_safety_mechanism_characterization as R9  # noqa: E402  (WU-15 helpers)

# ---------------------------------------------------------------------------
# Reused, UNCHANGED helpers from the WU-15 module (no re-definition -> no drift).
# ---------------------------------------------------------------------------
C = R8.C
S3 = R8.S3
L = R8.L
SB = R8.SB
FORBIDDEN_KEY_TOKENS = R9.FORBIDDEN_KEY_TOKENS
ACTION_DIM = R9.ACTION_DIM
ACTUATOR_ORDER = R9.ACTUATOR_ORDER
ACT_BOUNDS = R9.ACT_BOUNDS
encode_action = R9.encode_action
decode_action = R9.decode_action
project_state = R9.project_state
STATE_METRIC_KEYS = R9.STATE_METRIC_KEYS
arr_stats = R9.arr_stats
rule_s1_safe = R9.rule_s1_safe
rule_s2_safe = R9.rule_s2_safe
rule_s3_safe = R9.rule_s3_safe
rule_s4_safe = R9.rule_s4_safe

SERVICE_PSI = R8.SERVICE_PSI                # 20.0 psi service target
REPORT_TIMESTEP_S = 1800.0                   # hydraulic report step (30 min)

# Provisional temporal-rule grids: REUSE the WU-15 single-step grids verbatim so
# the temporal (TS*) lift is directly comparable. Provisional -> swept to expose
# behaviour, NOT tuned or selected.
TS1_THETA_P_PSI = list(R9.S1_THETA_P_PSI)               # [0,5,10,15,20]
TS2_EPS_P_PSI = list(R9.S2_EPS_P_PSI)                   # [0,2,5]
TS3_EPS_D_PSI_NODESUM = list(R9.S3_EPS_D_PSI_NODESUM)   # [0,2,5]

# Look-ahead horizons in CONTROL STEPS (1 step = one 30-min report instant).
# H = 1,2,4,8 control steps -> 0.5,1,2,4 h; plus the full 96 h horizon. These are
# CHARACTERISED, NOT selected (PART 21: do NOT select the look-ahead horizon).
HORIZONS_STEPS = [1, 2, 4, 8]

REPRO_TOL = 1e-3         # documented tolerance for WU-15 5.53/1.29 reproduction


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fl(x) -> float:
    return float(x)


def to_list(arr) -> list:
    return [float(x) for x in np.asarray(arr).ravel()]

PRV_IDS = list(R8.PRV_IDS)
PUMP_IDS = list(R8.PUMP_IDS)


def run_config_capture(label, prv_psi, pump_speed, coeff_us, svc, n_native):
    """One 96 h EPS at a static in-bounds command, MIRRORING R8.run_config's build
    path EXACTLY (p6_s8 lines 195-204) but additionally returning the raw WNTR
    (wn, res) so tank levels / pump realized speeds / native-rule events - which
    component_series does NOT expose - become visible over the full horizon.

    The static command is HELD for the whole horizon: this is precisely the
    'command re-issued at every 30-min control interval' case (PART 10). Validated
    scalars come from the SAME reused helpers (R8.component_series, L.accounting),
    so the frozen numbers (84.7298.. / 386 / 0) reproduce deterministically.
    """
    wn = S3.build(None, None)                 # solver+PDA set; controls untouched
    for v, s in prv_psi.items():
        wn.get_link(v).initial_setting = C.psi_to_m(float(s))
    for p, sp in pump_speed.items():
        wn.get_link(p).base_speed = float(sp)
    _ = S3.assert_solver(wn)
    assert len(wn.control_name_list) == n_native, (
        label, len(wn.control_name_list), n_native)
    L.apply_leak(wn, coeff_us)
    t0 = time.perf_counter()
    res, _msgs, _used = L._run_with_retry(wn, "p6s9temporal_" + label)
    wall = time.perf_counter() - t0

    series = R8.component_series(wn, res, coeff_us, svc)     # validated series
    acc = L.accounting(wn, res, coeff_us)                    # validated scalars
    finite = all(np.isfinite(np.asarray(v, dtype=float)).all()
                 for v in series.values())
    return {
        "label": label,
        "commanded": {
            "prv_setpoints_psi": {k: float(v) for k, v in prv_psi.items()},
            "pump_speeds": {k: float(v) for k, v in pump_speed.items()}},
        "n_timesteps": int(len(series["leakage_gpm"])),
        "wall_clock_s": float(wall),
        "validated_accounting": {
            "leakage_mean_gpm": acc["leakage_mean_gpm"],
            "dsr_mean": acc["dsr_mean"], "dsr_min": acc["dsr_min"],
            "n_node_timesteps_below_20psi": acc["n_node_timesteps_below_20psi"],
            "n_node_timesteps_negative_pressure":
                acc["n_node_timesteps_negative_pressure"],
        },
        "all_finite": bool(finite),
        "_series": series,
        "_wn": wn,
        "_res": res,
    }

def _status_name(code) -> str:
    from wntr.network.base import LinkStatus
    try:
        return LinkStatus(int(round(float(code)))).name
    except Exception:
        return str(code)


def res_extras(wn, res) -> dict:
    """Tank levels (ft), pump realized speeds / status, PRV realized setpoints /
    active flags, and native STATUS-rule events - all per report instant - from
    the raw WNTR result. Uses the FROZEN STEP-7 idioms (state_builder / p6_s7):
    tank level ft = m_to_ft(head - elevation); pump realized = setting if the
    reported status is Open else 0; PRV active <=> reported status code Active(2).
    """
    head = res.node["head"]                     # metres, index = report times (s)
    status = res.link["status"]
    setting = res.link["setting"]
    times_s = np.asarray(head.index, dtype=float)
    hours = times_s / 3600.0

    tanks = list(wn.tank_name_list)
    tank_levels_ft, tank_bounds_ft = {}, {}
    for tk in tanks:
        el = float(wn.get_node(tk).elevation)
        tank_levels_ft[tk] = to_list(C.m_to_ft(head[tk].to_numpy() - el))
        nd = wn.get_node(tk)
        tank_bounds_ft[tk] = [float(C.m_to_ft(nd.min_level)),
                              float(C.m_to_ft(nd.max_level))]

    pumps = {}
    for u in PUMP_IDS:
        st = status[u].to_numpy().astype(float)
        sp = setting[u].to_numpy().astype(float)
        realized = np.where(st >= 1.0, sp, 0.0)
        pumps[u] = {
            "status_code": to_list(st),
            "realized_speed": to_list(realized),
            "fraction_open": float(np.mean(st >= 1.0)),
        }

    prvs = {}
    for v in PRV_IDS:
        st = status[v].to_numpy().astype(float)
        realized_psi = C.m_to_psi(setting[v].to_numpy())
        prvs[v] = {
            "status_code": to_list(st),
            "realized_setpoint_psi": to_list(realized_psi),
            "fraction_active": float(np.mean(st == 2.0)),
        }

    # Native STATUS-rule events: pump status transitions (RULE-1/RULE-4 reopen a
    # pump when a tank drains below its level trigger). We report transitions as
    # 'coincident with' tank levels - NOT a causal attribution to a named rule.
    events = []
    for u in PUMP_IDS:
        st = status[u].to_numpy().astype(float)
        chg = np.nonzero(np.diff(st) != 0.0)[0] + 1
        for i in chg:
            events.append({
                "pump": u,
                "report_index": int(i),
                "hours": float(hours[i]),
                "from_status": _status_name(st[i - 1]),
                "to_status": _status_name(st[i]),
                "tank_levels_ft_at_event": {
                    tk: tank_levels_ft[tk][int(i)] for tk in tanks},
            })
    return {
        "report_index": list(range(len(times_s))),
        "hours": to_list(hours),
        "tank_bounds_ft": tank_bounds_ft,
        "tank_levels_ft": tank_levels_ft,
        "pumps": pumps,
        "prvs": prvs,
        "native_rule_events": events,
        "n_native_rule_events": int(len(events)),
    }

def trajectory_metrics(state: dict, hours) -> dict:
    """PART 4 trajectory-level metrics from a per-instant project_state.

    4.1 p_min_horizon = min_t p_min(t); 4.2 t_pmin (index + hours);
    4.3 D_max; 4.4 D_cum = Sum_t D(t)*dt (dt = report step = 0.5 h; rectangular);
    4.5 any_negative; 4.6 any_sub20 (descriptive, NOT an oracle); 4.7 DSR_min;
    4.8 Q_unserved_max; 4.9 Q_leak min/mean/max.
    """
    p = np.asarray(state["p_min"], dtype=float)
    D = np.asarray(state["D"], dtype=float)
    nneg = np.asarray(state["N_neg"], dtype=float)
    n20 = np.asarray(state["N_20"], dtype=float)
    dsr = np.asarray(state["DSR"], dtype=float)
    qun = np.asarray(state["Q_unserved"], dtype=float)
    qlk = np.asarray(state["Q_leak"], dtype=float)
    hours = np.asarray(hours, dtype=float)
    i_min = int(np.argmin(p))
    dt_h = REPORT_TIMESTEP_S / 3600.0
    return {
        "p_min_horizon_psi": float(np.min(p)),                        # 4.1
        "t_pmin_report_index": i_min,                                 # 4.2
        "t_pmin_hours": float(hours[i_min]),
        "p_min_at_decision_instant_psi": float(p[0]),                 # single-step
        "D_max_psi_nodesum": float(np.max(D)),                        # 4.3
        "D_cum_psi_nodesum_hours": float(np.sum(D) * dt_h),           # 4.4
        "D_cum_dt_hours": dt_h,
        "any_negative": int(np.max(nneg) > 0),                        # 4.5
        "max_N_neg": int(np.max(nneg)),
        "any_sub20_descriptive": int(np.max(n20) > 0),                # 4.6
        "max_N_20": int(np.max(n20)),
        "DSR_min": float(np.min(dsr)),                                # 4.7
        "Q_unserved_max_gpm": float(np.max(qun)),                     # 4.8
        "Q_leak_min_gpm": float(np.min(qlk)),                         # 4.9
        "Q_leak_mean_gpm": float(np.mean(qlk)),
        "Q_leak_max_gpm": float(np.max(qlk)),
    }


def trajectory_series(state: dict) -> dict:
    """Per-instant arrays for the primary temporal evidence (PART 6/7)."""
    return {
        "p_min_psi": to_list(state["p_min"]),
        "D_psi_nodesum": to_list(state["D"]),
        "N_neg": [int(x) for x in np.asarray(state["N_neg"])],
        "N_20_descriptive": [int(x) for x in np.asarray(state["N_20"])],
        "DSR": to_list(state["DSR"]),
        "Q_unserved_gpm": to_list(state["Q_unserved"]),
        "Q_leak_gpm": to_list(state["Q_leak"]),
    }


def horizon_pmin_sweep(p_min_arr, hours) -> dict:
    """PART 9: worst (min) p_min over the look-ahead window [0..H] for each H in
    HORIZONS_STEPS plus the full horizon - obtained purely by truncating the
    already-extracted trajectory (0 extra solves). Also reports the first report
    index/hours at which p_min drops below each provisional theta_p (how far ahead
    the delayed deterioration becomes visible)."""
    p = np.asarray(p_min_arr, dtype=float)
    hours = np.asarray(hours, dtype=float)
    n = p.size
    per_h = {}
    for H in HORIZONS_STEPS + [n - 1]:
        H = min(int(H), n - 1)
        w = p[:H + 1]
        key = "full" if H == n - 1 else f"H={H}"
        per_h[key] = {
            "control_steps": H,
            "hours_ahead": float(hours[H]),
            "worst_p_min_psi_over_window": float(np.min(w)),
            "worst_at_report_index": int(np.argmin(w)),
        }
    first_below = {}
    for theta in TS1_THETA_P_PSI:
        idx = np.nonzero(p < theta)[0]
        first_below[f"theta_p_psi={theta}"] = (
            {"report_index": int(idx[0]), "hours": float(hours[idx[0]])}
            if idx.size else None)
    return {"worst_p_min_over_window": per_h,
            "first_report_index_below_theta_p": first_below}

def _windows(n):
    for H in HORIZONS_STEPS + [n - 1]:
        H = min(int(H), n - 1)
        yield ("full" if H == n - 1 else f"H={H}"), H


def temporal_rule_outputs(post_state: dict, base_state: dict, hours) -> dict:
    """PART 8 temporal candidates TS1-TS4 - CHARACTERISED, not ranked/selected.
    'activates' == the rule would INTERVENE (its SAFE condition is violated)
    somewhere in the look-ahead window [0..H]. Relative rules (TS2/TS3) compare
    the post trajectory against the aligned reference (baseline) trajectory.

      TS1: SAFE iff  min_[0..H] p_min(t) >= theta_p        (absolute horizon floor)
      TS2: SAFE iff  min_[0..H] (p_min_post - p_min_base) >= -eps_p   (relative)
      TS3: SAFE iff  max_[0..H] (D_post - D_base) <= eps_D            (relative)
      TS4: SAFE iff  N_neg_post(t) == 0  for all t in [0..H]  (negative backstop)
    """
    p = np.asarray(post_state["p_min"], dtype=float)
    D = np.asarray(post_state["D"], dtype=float)
    nneg = np.asarray(post_state["N_neg"], dtype=float)
    pb = np.asarray(base_state["p_min"], dtype=float)
    Db = np.asarray(base_state["D"], dtype=float)
    n = p.size
    dpm = p - pb            # relative worst-node change vs baseline trajectory
    dD = D - Db             # relative aggregate-deficit change vs baseline
    out = {"TS1": {}, "TS2": {}, "TS3": {}, "TS4": {}}
    for key, H in _windows(n):
        wp, wnn = p[:H + 1], nneg[:H + 1]
        wdpm, wdD = dpm[:H + 1], dD[:H + 1]
        for theta in TS1_THETA_P_PSI:
            out["TS1"].setdefault(f"theta_p_psi={theta}", {})[key] = {
                "activates": bool(np.min(wp) < theta),
                "worst_p_min_over_window_psi": float(np.min(wp))}
        for eps in TS2_EPS_P_PSI:
            out["TS2"].setdefault(f"eps_p_psi={eps}", {})[key] = {
                "activates": bool(np.min(wdpm) < -eps),
                "worst_dp_min_over_window_psi": float(np.min(wdpm))}
        for eps in TS3_EPS_D_PSI_NODESUM:
            out["TS3"].setdefault(f"eps_D_psi_nodesum={eps}", {})[key] = {
                "activates": bool(np.max(wdD) > eps),
                "max_dD_over_window_psi_nodesum": float(np.max(wdD))}
        out["TS4"].setdefault("hard_backstop", {})[key] = {
            "activates": bool(np.max(wnn) > 0),
            "max_N_neg_over_window": int(np.max(wnn))}
    return out

def metric_definitions() -> dict:
    return {
        "p_min_psi": "min over 121 service nodes of PDA service pressure at instant t",
        "D_psi_nodesum": "Sum_i max(0, 20 - p_i(t)) over service nodes (psi*node)",
        "N_neg": "count of service nodes with p_i(t) < 0",
        "N_20_descriptive": "count of service nodes with p_i(t) < 20 (DESCRIPTIVE, not a safety oracle)",
        "DSR": "demand-satisfaction ratio Q_served/Q_req (PDA) at instant t",
        "Q_unserved_gpm": "max(0, Q_req - Q_served) at instant t (gpm)",
        "Q_leak_gpm": "pressure-driven leakage Sum sign(p)*C*|p|^0.5 (gpm, UNCALIBRATED)",
        "p_min_horizon_psi": "min_t p_min(t) over the look-ahead horizon",
        "t_pmin": "argmin_t p_min(t): report index and hours of the worst-node minimum",
        "D_max_psi_nodesum": "max_t D(t) over the horizon",
        "D_cum_psi_nodesum_hours": "Sum_t D(t)*dt, dt = report step = 0.5 h (rectangular)",
        "tank_level_ft": "m_to_ft(head_m(t) - tank elevation_m): water depth above bottom",
        "realized_pump_speed": "reported pump setting when status is Open, else 0 (closed)",
        "native_rule_event": "a pump STATUS transition per report instant, coincident-with tank levels",
    }


def temporal_candidate_descriptors() -> dict:
    """TS1-TS4 - definitional order, NOT evaluative. No candidate is called
    best/optimal/preferred and none carries a rank or a score."""
    return {
        "TS1": {"safe_condition": "min_[0..H] p_min(t) >= theta_p",
                "type": "absolute horizon worst-node floor",
                "provisional_theta_p_psi": TS1_THETA_P_PSI,
                "note": "inherits the chronic-baseline ill-posedness at theta_p above ~4.16 psi"},
        "TS2": {"safe_condition": "min_[0..H] (p_min_post(t) - p_min_base(t)) >= -eps_p",
                "type": "relative worst-node degradation vs aligned baseline trajectory",
                "provisional_eps_p_psi": TS2_EPS_P_PSI},
        "TS3": {"safe_condition": "max_[0..H] (D_post(t) - D_base(t)) <= eps_D",
                "type": "relative aggregate-deficit increase vs aligned baseline trajectory",
                "provisional_eps_D_psi_nodesum": TS3_EPS_D_PSI_NODESUM},
        "TS4": {"safe_condition": "N_neg_post(t) == 0 for all t in [0..H]",
                "type": "negative-pressure hard backstop over the look-ahead horizon",
                "note": "only well-posed HARD absolute gate on this chronically sub-20 network"},
    }


def computational_cost(full_run_wall_s: float, n_steps: int) -> dict:
    """PART 13. A trajectory-aware guard needs H sequential forward EPANET solves
    per 30-min decision (one per control step in the window). Here horizon
    truncation is FREE (the full trajectory is extracted in one solve); the costs
    below are the per-decision cost a real look-ahead mechanism would incur,
    approximated linearly from the measured full 96 h run."""
    per_step = full_run_wall_s / max(1, n_steps - 1)
    per_h = {}
    for H in HORIZONS_STEPS + [n_steps - 1]:
        key = "full" if H == n_steps - 1 else f"H={H}"
        per_h[key] = {
            "control_steps_ahead": int(H),
            "hours_ahead": float(H * REPORT_TIMESTEP_S / 3600.0),
            "forward_solves_per_decision": int(H),
            "est_wall_s_per_decision_linear": float(H * per_step),
            "relative_to_single_step": float(H),
        }
    return {
        "measured_full_96h_run_wall_s": float(full_run_wall_s),
        "measured_report_instants": int(n_steps),
        "est_wall_s_per_control_step_linear": float(per_step),
        "horizon_truncation_extra_solves": 0,
        "per_horizon_lookahead_cost": per_h,
        "note": "EPANET is deterministic; a look-ahead adds no stochasticity. "
                "Linear per-step split is an approximation, not a per-step benchmark.",
    }


def ppo_compatibility() -> dict:
    """PART 14 - per look-ahead horizon; booleans + notes, NO selection."""
    per_h = {}
    for H in HORIZONS_STEPS + ["full"]:
        steps = 192 if H == "full" else int(H)
        key = "full" if H == "full" else f"H={H}"
        per_h[key] = {
            "deterministic": True,
            "extra_forward_solves_per_decision": steps,
            "adds_action_latency": bool(steps > 1),
            "interval_30min_compatible": True,
            "executed_may_differ_from_commanded": True,
            "env_differentiability_required": False,
        }
    return {
        "per_horizon": per_h,
        "note": "PPO is model-free: the env need not be differentiable. A clip/reject "
                "guard makes executed != commanded, so the train/execute gap must be "
                "observable to the policy. Latency is wall-clock, not learning-theoretic.",
    }


def limitations() -> list:
    return [
        "Finite look-ahead is NOT a long-term / infinite-horizon safety guarantee: "
        "a horizon of H control steps only certifies behaviour within that window.",
        "Detection capability != safety guarantee: a trajectory-aware rule may DETECT "
        "delayed deterioration without any mechanism yet being selected to ENFORCE a bound.",
        "Applied-once (single-application then revert) is NOT separately simulated: it "
        "would require adding non-native time-based controls to the frozen instrument "
        "(changing the native control count). The re-issued/sustained case IS measured; "
        "the applied-once case is characterised via the near-term trajectory and the "
        "pump realized-speed evolution.",
        "Coverage: only reference (baseline), the single severe corner (prv_lower_pump_lower), "
        "and one intermediate corner (prv_all_lower) are measured over the horizon. Interior "
        "points, mixed corners, and the joint (action x uncertain-demand) space are NOT covered.",
        "No validated safe/unsafe oracle: single-step non-activation vs delayed deterioration "
        "is reported descriptively; NO false-positive/false-negative/accuracy is computed.",
        "Provisional thresholds (theta_p, eps_p, eps_D) are swept to expose behaviour, NOT tuned "
        "or selected; horizons {1,2,4,8,full} are characterised, NOT selected.",
        "Q_leak uses an uncalibrated emitter coefficient (relative use only).",
    ]

def _decision_instant_metrics(state: dict) -> dict:
    """PART 7 VIEW A - the strict single-step / decision-instant (report index 0)
    post-action state: what a naive one-shot look-ahead would see."""
    return {
        "report_index": 0,
        "hours": 0.0,
        "p_min_psi": float(np.asarray(state["p_min"])[0]),
        "D_psi_nodesum": float(np.asarray(state["D"])[0]),
        "N_neg": int(np.asarray(state["N_neg"])[0]),
        "N_20_descriptive": int(np.asarray(state["N_20"])[0]),
        "DSR": float(np.asarray(state["DSR"])[0]),
        "Q_unserved_gpm": float(np.asarray(state["Q_unserved"])[0]),
    }


def main() -> dict:
    C.build_working_copy(verbose=False)
    wn0 = S3.build(None, None)
    svc, conn = S3.service_nodes(wn0)
    assert len(svc) == 121 and len(conn) == 5, (len(svc), len(conn))
    n_native = len(wn0.control_name_list)

    # Leak instrument sized VERBATIM as p6_s8 (same 10 % target, reused helpers).
    base_p, base_inflow, weights = L.baseline_pressures("p6s9temporal_size")
    sizing = L.leak_coefficients(weights, base_p,
                                 L.LEAK_TARGET_FRACTION * base_inflow)
    coeff_us = sizing["coefficient_gpm_per_psi_alpha"]

    # ---- PART 6: load the EXACT commands + anchors from the persisted WU-15 JSON.
    wu15 = json.loads(WU15_JSON.read_text(encoding="utf-8"))
    inp_sha = wu15["experiment_metadata"]["working_inp_sha256"]

    def _cmd(name):
        c = wu15["tested_states"][name]["commanded"]
        return dict(c["prv_setpoints_psi"]), dict(c["pump_speeds"])

    ref_prv, ref_pump = _cmd("reference_nominal")
    sev_prv, sev_pump = _cmd("prv_lower_pump_lower")
    int_prv, int_pump = _cmd("prv_all_lower")
    sev_norm_persisted = list(wu15["tested_actions"]["prv_lower_pump_lower"])
    anchor_decision = float(wu15["transitions"]["T1_reference_to_severe"]
                            ["shared_initial_state"]["post_action_metrics"]["p_min"])
    anchor_sustained = float(wu15["transitions"]["T1_reference_to_severe"]
                             ["sustained_horizon"]["post_action_distribution"]
                             ["p_min"]["min"])

    order = [("reference_nominal", ref_prv, ref_pump),
             ("prv_lower_pump_lower", sev_prv, sev_pump),
             ("prv_all_lower", int_prv, int_pump)]
    cfgs, states, extras = {}, {}, {}
    for label, prv, pump in order:
        cfgs[label] = run_config_capture(label, prv, pump, coeff_us, svc, n_native)
        states[label] = project_state(cfgs[label]["_series"])
        extras[label] = res_extras(cfgs[label]["_wn"], cfgs[label]["_res"])

    hours = extras["reference_nominal"]["hours"]
    base_state = states["reference_nominal"]
    sev_state = states["prv_lower_pump_lower"]
    int_state = states["prv_all_lower"]
    n_steps = int(len(hours))

    # ---- PART 6/18: verify the WU-15 5.53 / 1.29 anchors reproduce from disk.
    repro_decision = float(np.asarray(sev_state["p_min"])[0])
    repro_sustained = float(np.min(np.asarray(sev_state["p_min"])))
    sev_norm_recomputed = [float(x) for x in encode_action(sev_prv, sev_pump)]
    wu15_reproduction = {
        "persisted_decision_instant_p_min_psi": anchor_decision,
        "reproduced_decision_instant_p_min_psi": repro_decision,
        "decision_instant_abs_diff_psi": abs(repro_decision - anchor_decision),
        "persisted_sustained_worst_p_min_psi": anchor_sustained,
        "reproduced_sustained_worst_p_min_psi": repro_sustained,
        "sustained_worst_abs_diff_psi": abs(repro_sustained - anchor_sustained),
        "sustained_understatement_psi": repro_decision - repro_sustained,
        "t_pmin_report_index": int(np.argmin(np.asarray(sev_state["p_min"]))),
        "t_pmin_hours": float(hours[int(np.argmin(np.asarray(sev_state["p_min"])))]),
        "persisted_normalized_action": sev_norm_persisted,
        "recomputed_normalized_action": sev_norm_recomputed,
        "normalized_action_max_abs_diff": float(np.max(np.abs(
            np.asarray(sev_norm_recomputed) - np.asarray(sev_norm_persisted)))),
        "tolerance": REPRO_TOL,
    }

    def _tank_evolution(label):
        ex = extras[label]
        i_min = int(np.argmin(np.asarray(states[label]["p_min"])))
        out = {"tank_bounds_ft": ex["tank_bounds_ft"], "tank_levels_ft": ex["tank_levels_ft"],
               "at_t0_ft": {tk: ex["tank_levels_ft"][tk][0] for tk in ex["tank_levels_ft"]},
               "at_t_pmin_ft": {tk: ex["tank_levels_ft"][tk][i_min] for tk in ex["tank_levels_ft"]},
               "level_change_to_t_pmin_ft": {
                   tk: ex["tank_levels_ft"][tk][i_min] - ex["tank_levels_ft"][tk][0]
                   for tk in ex["tank_levels_ft"]},
               "t_pmin_report_index": i_min}
        return out

    def _pump_evolution(label):
        ex = extras[label]
        return {"commanded_pump_speeds": cfgs[label]["commanded"]["pump_speeds"],
                "per_pump": ex["pumps"]}

    analysis = {
        "experiment_metadata": {
            "work_unit": "WU-16",
            "purpose": ("EVIDENCE ONLY: characterise whether a purely SINGLE-STEP "
                        "post-action safety check can MISS delayed hydraulic "
                        "deterioration emerging over the sustained horizon as tank "
                        "states evolve. Contrast single-step vs trajectory-aware; "
                        "sweep look-ahead horizons. No mechanism/policy/horizon "
                        "selected, ranked, or scored."),
            "generated_utc": _now_utc(),
            "instrument": "p6_s8_reward_scale_analysis (validated, reused unchanged)",
            "wu15_source": WU15_JSON.name,
            "working_inp_sha256": inp_sha,
            "action_dim": ACTION_DIM,
            "actuator_order": ACTUATOR_ORDER,
            "observation_dim": 139,
            "n_service_junctions": 121,
            "n_connector_junctions": 5,
            "n_native_controls": int(n_native),
            "report_instants": n_steps,
            "hydraulic_report_timestep_s": REPORT_TIMESTEP_S,
            "reward_layer_frozen": "D-P6-005 C-A_F1_balanced_dense (NOT modified here)",
            "prohibitions": ("no mechanism/policy/horizon selection; no ranking/scoring; "
                             "no production wrapper; no reward.py; no PPO"),
        },
        "metric_definitions": metric_definitions(),
        "temporal_candidates": temporal_candidate_descriptors(),
        "horizons_tested": {
            "control_steps": HORIZONS_STEPS + [n_steps - 1],
            "hours": [float(h * REPORT_TIMESTEP_S / 3600.0) for h in HORIZONS_STEPS]
                     + [float((n_steps - 1) * REPORT_TIMESTEP_S / 3600.0)],
            "note": "1 control step = one 30-min report instant; 'full' = 96 h horizon. "
                    "Horizons are CHARACTERISED, not selected.",
        },
        "wu15_delayed_collapse_reproduction": wu15_reproduction,
        "baseline_trajectory": {                                      # PART 5
            "config": "reference_nominal (native/reference control)",
            "commanded": cfgs["reference_nominal"]["commanded"],
            "validated_accounting": cfgs["reference_nominal"]["validated_accounting"],
            "trajectory_metrics": trajectory_metrics(base_state, hours),
            "series": trajectory_series(base_state),
            "interpretation": ("pre-existing baseline deficiency: chronic sub-20 psi at "
                               "the worst node is present WITHOUT any agent action; this "
                               "is distinct from control-induced deterioration."),
        },
        "delayed_collapse_case": {                                    # PART 6
            "config": "prv_lower_pump_lower (WU-15 severe corner, all-lower)",
            "commanded": cfgs["prv_lower_pump_lower"]["commanded"],
            "normalized_action": sev_norm_recomputed,
            "validated_accounting": cfgs["prv_lower_pump_lower"]["validated_accounting"],
            "trajectory_metrics": trajectory_metrics(sev_state, hours),
            "series": trajectory_series(sev_state),
            "tank_levels_ft": extras["prv_lower_pump_lower"]["tank_levels_ft"],
            "horizon_pmin_sweep": horizon_pmin_sweep(sev_state["p_min"], hours),  # PART 9
            "primary_temporal_evidence": True,
        },
        "trajectory_metrics": {                                       # PART 4
            k: trajectory_metrics(states[k], hours) for k in states},
        "single_step_metrics": {                                      # PART 7 VIEW A
            k: _decision_instant_metrics(states[k]) for k in states},
        "single_step_vs_trajectory": {                                # PART 7/12
            k: {"view_A_single_step_decision_instant":
                    _decision_instant_metrics(states[k]),
                "view_B_trajectory_over_full_horizon": {
                    "p_min_horizon_psi": float(np.min(states[k]["p_min"])),
                    "D_max_psi_nodesum": float(np.max(states[k]["D"])),
                    "DSR_min": float(np.min(states[k]["DSR"])),
                    "max_N_neg": int(np.max(states[k]["N_neg"]))}}
            for k in states},
        "temporal_rule_outputs": {                                    # PART 8/12
            "prv_lower_pump_lower_vs_baseline":
                temporal_rule_outputs(sev_state, base_state, hours),
            "prv_all_lower_vs_baseline":
                temporal_rule_outputs(int_state, base_state, hours),
            "baseline_identity_hold":
                temporal_rule_outputs(base_state, base_state, hours),
        },
        "action_persistence_cases": {                                 # PART 10
            "reissued_sustained": {
                "measured": True,
                "description": ("static command HELD for the full 96 h horizon = command "
                                "re-issued at every 30-min control interval (the realistic "
                                "env case; pump speed re-issued each control step)."),
                "p_min_horizon_psi": float(np.min(sev_state["p_min"])),
                "t_pmin_report_index": int(np.argmin(np.asarray(sev_state["p_min"]))),
            },
            "applied_once_characterization": {
                "measured": False,
                "decision_instant_p_min_psi": float(np.asarray(sev_state["p_min"])[0]),
                "one_control_step_p_min_psi": float(np.asarray(sev_state["p_min"])[1]),
                "pump_realized_speed_evolution": {
                    u: extras["prv_lower_pump_lower"]["pumps"][u]["realized_speed"]
                    for u in PUMP_IDS},
                "note": ("a genuine single-application-then-revert run would require adding "
                         "non-native time-based controls to the frozen instrument "
                         "(changing the native control count); NOT simulated here. The "
                         "near-term indices approximate the one-interval effect; the pump "
                         "realized-speed trajectory shows whether native rules override a "
                         "non-reissued command."),
            },
        },
        "tank_state_evolution": {k: _tank_evolution(k) for k in states},     # PART 11
        "pump_state_evolution": {k: _pump_evolution(k) for k in states},     # PART 11
        "native_rule_events": {                                              # PART 11
            k: {"events": extras[k]["native_rule_events"],
                "n_events": extras[k]["n_native_rule_events"]} for k in states},
        "computational_cost":                                               # PART 13
            computational_cost(cfgs["prv_lower_pump_lower"]["wall_clock_s"], n_steps),
        "PPO_compatibility": ppo_compatibility(),                           # PART 14
        "limitations": limitations(),                                       # PART 15
        "researcher_selection": None,
    }

    return analysis

def _iter_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _iter_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_keys(v)


def _iter_numbers(obj):
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_numbers(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_numbers(v)


def _self_checks(analysis: dict) -> None:
    fails = []

    bad = sorted({k for k in _iter_keys(analysis)
                  if any(t in str(k).lower() for t in FORBIDDEN_KEY_TOKENS)})
    if bad:
        fails.append(f"forbidden key tokens present: {bad}")

    if analysis["researcher_selection"] is not None:
        fails.append("researcher_selection must be null")

    meta = analysis["experiment_metadata"]
    for key, want in (("action_dim", 7), ("observation_dim", 139),
                      ("n_service_junctions", 121), ("n_connector_junctions", 5)):
        if meta.get(key) != want:
            fails.append(f"{key}={meta.get(key)} expected {want}")

    ref = analysis["baseline_trajectory"]["validated_accounting"]
    if abs(ref["leakage_mean_gpm"] - 84.72988433677985) > 1e-6:
        fails.append(f"baseline leakage {ref['leakage_mean_gpm']} != 84.72988433677985")
    if ref["n_node_timesteps_below_20psi"] != 386:
        fails.append(f"baseline sub-20 {ref['n_node_timesteps_below_20psi']} != 386")
    if ref["n_node_timesteps_negative_pressure"] != 0:
        fails.append("baseline negative-pressure count != 0")

    rep = analysis["wu15_delayed_collapse_reproduction"]
    if rep["decision_instant_abs_diff_psi"] > REPRO_TOL:
        fails.append(f"WU-15 decision-instant repro diff {rep['decision_instant_abs_diff_psi']}")
    if rep["sustained_worst_abs_diff_psi"] > REPRO_TOL:
        fails.append(f"WU-15 sustained repro diff {rep['sustained_worst_abs_diff_psi']}")
    if rep["normalized_action_max_abs_diff"] > 1e-9:
        fails.append(f"severe normalized-action mismatch {rep['normalized_action_max_abs_diff']}")
    if not (rep["reproduced_decision_instant_p_min_psi"]
            > rep["reproduced_sustained_worst_p_min_psi"]):
        fails.append("expected decision-instant p_min > sustained worst p_min")

    nbad = [x for x in _iter_numbers(analysis)
            if not math.isfinite(float(x))]
    if nbad:
        fails.append(f"{len(nbad)} non-finite numbers in analysis")

    # Cross-disk: the frozen baseline leakage constant must also be present in the
    # persisted p6_s8 validated instrument (best-effort; skipped if absent).
    if P6S8_JSON.exists():
        vals = list(_iter_numbers(json.loads(P6S8_JSON.read_text(encoding="utf-8"))))
        if not any(abs(float(v) - 84.72988433677985) <= 1e-6 for v in vals):
            fails.append("frozen baseline leakage not found in persisted p6_s8 JSON")

    if fails:
        raise SystemExit("SELF-CHECK FAILED:\n  - " + "\n  - ".join(fails))


if __name__ == "__main__":
    analysis = main()
    _self_checks(analysis)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(analysis, indent=2, default=str) + "\n",
                   encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
    rep = analysis["wu15_delayed_collapse_reproduction"]
    print(f"WU-15 reproduce: decision {rep['reproduced_decision_instant_p_min_psi']:.4f} psi, "
          f"sustained worst {rep['reproduced_sustained_worst_p_min_psi']:.4f} psi "
          f"@ t={rep['t_pmin_hours']:.1f} h "
          f"(understatement {rep['sustained_understatement_psi']:.4f} psi)")
