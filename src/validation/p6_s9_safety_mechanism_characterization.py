#!/usr/bin/env python3
"""WU-15 - STEP 9 EMPIRICAL characterization of candidate state-dependent safety
mechanisms (S1-S4) and candidate action-handling policies (H1-H3).

EVIDENCE ONLY. This script:
  * reuses the VALIDATED p6_s8 measurement instrument UNCHANGED (same 96 h EPS,
    solver policy, leak/PDA instrument, frozen 121-node service mask, native
    controls untouched) - it imports p6_s8_reward_scale_analysis and calls its
    run_config / component_series;
  * measures a small, bounded set of static in-bounds commands (operating points)
    and constructs (current-state -> proposed-action post-state) transition PAIRS
    so the delta metrics (dp_min, dD, dQ_leak, dDSR, dQ_unserved) and the safety
    rules / handling policies can be evaluated on real hydraulic evidence;
  * does NOT select, rank, score, prefer, or recommend any mechanism or policy;
    researcher_selection = null. It does NOT implement the production safety
    wrapper, reward.py, or PPO.

Reproducibility: EPANET is deterministic, so re-running reproduces every value;
re-running the shared operating points reproduces the frozen p6_s8 accounting
(asserted in self_checks). The JSON is NOT byte-reproduced (it carries a
generated_utc stamp), matching the p6_s8 measurement-script convention.
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
OUT = RESULTS / "p6_s9_safety_mechanism_characterization.json"
P6S8_JSON = RESULTS / "p6_s8_reward_scale_analysis.json"

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src" / "env"))

import p6_s8_reward_scale_analysis as R8  # noqa: E402  (validated instrument)

# Same forbidden-key discipline as the WU-14 design analysis: no evaluative or
# ordering key may appear anywhere in the emitted JSON (expressed as VALUES only).
FORBIDDEN_KEY_TOKENS = ("winner", "rank", "tier", "score", "best",
                        "superior", "optimal", "preferred", "recommend")

# --- Frozen action space (D-P6-001/002/003; mirror of state_builder / spec) ----
# Ordered exactly as docs/PHASE6_ACTION_SPACE_SPEC.md (index -> actuator).
ACTUATOR_ORDER = list(R8.PRV_IDS) + list(R8.PUMP_IDS)   # 7 actuators
ACT_BOUNDS = {v: tuple(R8.SB.PRV_BOUNDS_PSI[v]) for v in R8.PRV_IDS}
ACT_BOUNDS.update({p: tuple(R8.SB.PUMP_BOUNDS[p]) for p in R8.PUMP_IDS})
ACTION_DIM = len(ACTUATOR_ORDER)                        # 7
I_MODIFIED_TOL = 1e-9                                   # PART 4.18 numeric tol

# --- PROVISIONAL threshold sets (PART 8-11). Documented, NOT selected. ---------
S1_THETA_P_PSI = [0.0, 5.0, 10.0, 15.0, 20.0]          # absolute worst-node floor
S2_EPS_P_PSI = [0.0, 2.0, 5.0]                          # worst-node degradation tol
S3_EPS_D_PSI_NODESUM = [0.0, 2.0, 5.0]                  # aggregate deficit tol
H2_ALPHA_GRID = [0.0, 0.25, 0.5, 0.75, 1.0]            # H2 interpolation grid


def encode_action(prv_psi: dict, pump_speed: dict) -> list:
    """Physical command -> normalized action a in [-1, 1]^7 (inverse of D-P6-001):
    a_i = 2*(phys_i - lo_i)/(hi_i - lo_i) - 1. Ordered by ACTUATOR_ORDER."""
    phys = {**{k: float(v) for k, v in prv_psi.items()},
            **{k: float(v) for k, v in pump_speed.items()}}
    out = []
    for act in ACTUATOR_ORDER:
        lo, hi = ACT_BOUNDS[act]
        out.append(2.0 * (phys[act] - lo) / (hi - lo) - 1.0)
    return out


def decode_action(a) -> tuple:
    """Normalized action a in [-1,1]^7 -> (prv_setpoints_psi, pump_speeds), the
    exact D-P6-001 mapping phys_i = lo_i + ((a_i+1)/2)*(hi_i-lo_i)."""
    prv, pump = {}, {}
    for act, ai in zip(ACTUATOR_ORDER, a):
        lo, hi = ACT_BOUNDS[act]
        phys = lo + ((float(ai) + 1.0) / 2.0) * (hi - lo)
        (prv if act in R8.PRV_IDS else pump)[act] = phys
    return prv, pump


def l2(vec) -> float:
    return float(np.sqrt(np.sum(np.asarray(vec, dtype=float) ** 2)))


def l2sq(vec) -> float:
    return float(np.sum(np.asarray(vec, dtype=float) ** 2))


# --- Safety rules (PART 7-11). Return True == SAFE (do NOT intervene). ---------
def rule_s1_safe(p_min_post: float, theta_p: float) -> bool:
    return bool(p_min_post >= theta_p)


def rule_s2_safe(dp_min: float, eps_p: float) -> bool:
    return bool(dp_min >= -eps_p)


def rule_s3_safe(d_delta: float, eps_d: float) -> bool:
    return bool(d_delta <= eps_d)


def rule_s4_safe(n_neg_post: float) -> bool:
    return bool(n_neg_post == 0)

# --- State-metric projection over the validated per-timestep component series --
# Maps the p6_s8 component_series keys to the STEP-9 metric names (PART 4).
def project_state(series: dict) -> dict:
    """Per-timestep STEP-9 state metrics (numpy arrays) from a validated series."""
    return {
        "p_min": np.asarray(series["min_service_pressure_psi"], dtype=float),
        "D": np.asarray(series["pressure_deficit_psi_nodesum"], dtype=float),
        "N_neg": np.asarray(series["n_service_nodes_negative"], dtype=float),
        "N_20": np.asarray(series["n_service_nodes_below_20psi"], dtype=float),
        "DSR": np.asarray(series["dsr"], dtype=float),
        "Q_unserved": np.clip(np.asarray(series["unserved_demand_gpm"],
                                         dtype=float), 0.0, None),  # PART 4.10
        "Q_leak": np.asarray(series["leakage_gpm"], dtype=float),
        "Q_req": np.asarray(series["requested_demand_gpm"], dtype=float),
        "Q_served": np.asarray(series["served_demand_gpm"], dtype=float),
    }


STATE_METRIC_KEYS = ("p_min", "D", "N_neg", "N_20", "DSR",
                     "Q_unserved", "Q_leak", "Q_req", "Q_served")


def scalar_at(state: dict, i: int) -> dict:
    """Scalar snapshot of every state metric at report instant i."""
    return {k: float(state[k][i]) for k in STATE_METRIC_KEYS}


def arr_stats(a) -> dict:
    """min/mean/max distribution summary of one per-instant metric array."""
    a = np.asarray(a, dtype=float)
    return {"min": float(a.min()), "mean": float(a.mean()),
            "max": float(a.max())}


def delta_scalars(cur: dict, post: dict) -> dict:
    """PART 4 delta metrics at one instant (post-action minus current-state)."""
    return {
        "dp_min": post["p_min"] - cur["p_min"],          # 4.3
        "dD": post["D"] - cur["D"],                       # 4.5
        "dQ_leak": post["Q_leak"] - cur["Q_leak"],        # 4.13
        "dDSR": post["DSR"] - cur["DSR"],                 # 4.14
        "dQ_unserved": post["Q_unserved"] - cur["Q_unserved"],  # 4.15
    }

# --- Operating points (static in-bounds commands) measured with the instrument -
# CLASS A reference, CLASS C intermediate control, CLASS B severe degradation,
# a distinct high-pressure current state (for state-dependence), and the H2
# interpolation grid between the reference and the severe command.
def base_operating_points() -> list:
    """(label, class, prv_setpoints_psi, pump_speeds). All strictly in bounds."""
    P = R8
    pts = [
        ("reference_nominal", "A_reference",
         dict(P.PRV_NOMINAL), dict(P.PUMP_NOMINAL)),
        ("prv_all_lower", "C_intermediate_control",
         dict(P.PRV_LOWER), dict(P.PUMP_NOMINAL)),
        ("prv_all_upper", "reference_high_pressure_state",
         dict(P.PRV_UPPER), dict(P.PUMP_NOMINAL)),
        ("prv_lower_pump_lower", "B_severe_degradation",
         dict(P.PRV_LOWER), dict(P.PUMP_LOWER)),
    ]
    return pts


def interpolated_points(a_prev, a_prop, label_prefix: str) -> list:
    """H2 interpolation configs a_exec = a_prev + alpha*(a_prop - a_prev) decoded
    to physical commands. alpha in (0,1) only (0->prev, 1->prop already measured)."""
    a_prev = np.asarray(a_prev, dtype=float)
    a_prop = np.asarray(a_prop, dtype=float)
    pts = []
    for alpha in H2_ALPHA_GRID:
        if alpha in (0.0, 1.0):
            continue
        a_exec = a_prev + alpha * (a_prop - a_prev)
        prv, pump = decode_action(a_exec)
        pts.append((f"{label_prefix}_alpha{alpha:.2f}", "h2_interpolation",
                    prv, pump))
    return pts


def run_operating_point(label, prv_psi, pump_speed, coeff_us, svc, n_native):
    """Run one static command with the validated instrument; time it; project."""
    t0 = time.perf_counter()
    cfg = R8.run_config(label, prv_psi, pump_speed, coeff_us, svc, n_native)
    wall = time.perf_counter() - t0
    state = project_state(cfg["_series"])
    return {
        "label": label,
        "commanded": cfg["commanded"],
        "normalized_action": encode_action(prv_psi, pump_speed),
        "n_timesteps": int(cfg["n_timesteps"]),
        "validated_accounting": cfg["validated_accounting"],
        "all_finite": bool(cfg["all_finite"]),
        "wall_clock_s": float(wall),
        "_state": state,
    }

# --- Transition construction (current-state -> proposed-action) ----------------
# Two measurement views per transition (PART 14 state-dependence + PART 5 honesty):
#   * shared_initial_state (report index 0): both configs start from the identical
#     INP initial tank levels, so the delta at t0 is a STRICT one-step look-ahead
#     (pure command effect, no trajectory divergence).
#   * sustained_horizon: per-instant distribution over all 193 instants; LABELED
#     as including tank-trajectory divergence (NOT a strict single-step
#     look-ahead) so the severe-collapse instants remain visible.
def _instant_snapshot(cur_state: dict, post_state: dict, i: int) -> dict:
    """Full (current, post, delta) snapshot at one report instant i."""
    cur = scalar_at(cur_state, i)
    post = scalar_at(post_state, i)
    return {
        "report_index": int(i),
        "current_state_metrics": cur,
        "post_action_metrics": post,
        "delta_metrics": delta_scalars(cur, post),
    }


def _horizon_deltas(cur_state: dict, post_state: dict) -> dict:
    """Per-instant delta arrays over the full horizon (post minus current)."""
    return {
        "dp_min": post_state["p_min"] - cur_state["p_min"],
        "dD": post_state["D"] - cur_state["D"],
        "dQ_leak": post_state["Q_leak"] - cur_state["Q_leak"],
        "dDSR": post_state["DSR"] - cur_state["DSR"],
        "dQ_unserved": post_state["Q_unserved"] - cur_state["Q_unserved"],
    }


def transition_record(cur_run: dict, post_run: dict, class_label: str) -> dict:
    """One (current-state -> proposed-action) transition on both views."""
    cur_state, post_state = cur_run["_state"], post_run["_state"]
    n = int(min(len(cur_state["p_min"]), len(post_state["p_min"])))
    dh = {k: v[:n] for k, v in _horizon_deltas(cur_state, post_state).items()}
    i_worst_pmin = int(np.argmin(post_state["p_min"][:n]))
    i_max_dD = int(np.argmax(dh["dD"]))
    return {
        "current_label": cur_run["label"],
        "proposed_label": post_run["label"],
        "transition_class": class_label,
        "n_shared_timesteps": n,
        "shared_initial_state": _instant_snapshot(cur_state, post_state, 0),
        "sustained_horizon": {
            "note": ("per-instant over full horizon; includes tank-trajectory "
                     "divergence, NOT a strict single-step look-ahead"),
            "post_action_distribution": {
                k: arr_stats(post_state[k][:n]) for k in
                ("p_min", "D", "N_neg", "N_20", "DSR", "Q_unserved", "Q_leak")},
            "delta_distribution": {k: arr_stats(v) for k, v in dh.items()},
            "worst_post_p_min_instant": _instant_snapshot(
                cur_state, post_state, i_worst_pmin),
            "max_deficit_increase_instant": _instant_snapshot(
                cur_state, post_state, i_max_dD),
        },
    }

# --- Safety-rule outputs (descriptive activation, NOT FP/FN rates) -------------
def safety_rule_outputs(cur_run: dict, post_run: dict) -> dict:
    """Descriptive rule activation on both views. Rules return True==SAFE, so an
    activation (intervention) is NOT-safe. Reports whether each rule activates at
    the shared-initial instant and its activation fraction over the sustained
    horizon. These are DESCRIPTIVE activation counts, NOT false-positive or
    false-negative rates (PART 5: no validated safe/unsafe oracle exists)."""
    cs, ps = cur_run["_state"], post_run["_state"]
    n = int(min(len(cs["p_min"]), len(ps["p_min"])))
    p_min_post = ps["p_min"][:n]
    dp_min = ps["p_min"][:n] - cs["p_min"][:n]
    d_delta = ps["D"][:n] - cs["D"][:n]
    n_neg_post = ps["N_neg"][:n]

    def summarize(safe_arr, safe0: bool) -> dict:
        activates = ~np.asarray(safe_arr, dtype=bool)
        return {
            "rule_activates_at_shared_initial": bool(not safe0),
            "activation_fraction_sustained": float(np.mean(activates)),
            "n_activations_sustained": int(np.sum(activates)),
            "n_instants": int(n),
        }

    out = {"S1": {}, "S2": {}, "S3": {}, "S4": {}}
    for th in S1_THETA_P_PSI:
        out["S1"][f"theta_p_psi={th:g}"] = summarize(
            p_min_post >= th, rule_s1_safe(float(p_min_post[0]), th))
    for eps in S2_EPS_P_PSI:
        out["S2"][f"eps_p_psi={eps:g}"] = summarize(
            dp_min >= -eps, rule_s2_safe(float(dp_min[0]), eps))
    for eps in S3_EPS_D_PSI_NODESUM:
        out["S3"][f"eps_D_psi_nodesum={eps:g}"] = summarize(
            d_delta <= eps, rule_s3_safe(float(d_delta[0]), eps))
    out["S4"]["hard_backstop"] = summarize(
        n_neg_post == 0, rule_s4_safe(float(n_neg_post[0])))
    return out


def separation_question(rules_severe: dict, rules_intermediate: dict) -> dict:
    """PART 18 empirical fact table: for each rule@threshold, does it ACTIVATE on
    the previously observed severe-degradation transition AND NOT activate on the
    intermediate-control transition? Booleans only; no ordering or selection."""
    out = {}
    for cand in ("S1", "S2", "S3", "S4"):
        out[cand] = {}
        for key in rules_severe[cand]:
            sev, itm = rules_severe[cand][key], rules_intermediate[cand][key]
            a_sev0 = sev["rule_activates_at_shared_initial"]
            a_itm0 = itm["rule_activates_at_shared_initial"]
            a_sevh = sev["activation_fraction_sustained"] > 0.0
            a_itmh = itm["activation_fraction_sustained"] > 0.0
            out[cand][key] = {
                "activates_on_severe_shared_initial": bool(a_sev0),
                "activates_on_intermediate_shared_initial": bool(a_itm0),
                "blocks_severe_and_spares_intermediate_shared_initial":
                    bool(a_sev0 and not a_itm0),
                "activates_on_severe_sustained": bool(a_sevh),
                "activates_on_intermediate_sustained": bool(a_itmh),
                "blocks_severe_and_spares_intermediate_sustained":
                    bool(a_sevh and not a_itmh),
            }
    return out

# --- Action-handling policies H1/H2/H3 (PART 12-13) ----------------------------
_POST_KEYS = ("p_min", "D", "N_neg", "N_20", "DSR", "Q_unserved", "Q_leak")


def _policy_metrics(a_prop, a_exec, i_reject: bool, post_state, i: int = 0) -> dict:
    """PART 13 intervention metrics for one executed action at report instant i."""
    dev = np.asarray(a_exec, dtype=float) - np.asarray(a_prop, dtype=float)
    snap = scalar_at(post_state, i)
    return {
        "proposed_action": [float(x) for x in a_prop],
        "executed_action": [float(x) for x in a_exec],
        "action_deviation_L2": float(l2(dev)),
        "action_deviation_L2sq": float(l2sq(dev)),
        "I_modified": bool(float(l2(dev)) > I_MODIFIED_TOL),
        "I_reject": bool(i_reject),
        "post_intervention_shared_initial": {k: snap[k] for k in _POST_KEYS},
    }


def _h2_for_rule(cur0: dict, alpha_runs: list, safe_fn) -> tuple:
    """Largest admissible alpha on the a_prev->a_prop segment (PART 12). Counts
    every alpha-grid point inspected as one look-ahead hydraulic evaluation. If no
    alpha is admissible, holds a_prev (alpha=0)."""
    sel_alpha, sel_run, n_eval = None, None, 0
    for alpha, run in alpha_runs:
        n_eval += 1
        post0 = scalar_at(run["_state"], 0)
        if safe_fn(cur0, post0) and (sel_alpha is None or alpha > sel_alpha):
            sel_alpha, sel_run = alpha, run
    if sel_alpha is None:
        sel_alpha, sel_run = alpha_runs[0]
    return float(sel_alpha), sel_run, n_eval

def handling_policy_outputs(prev_run: dict, prop_run: dict,
                            fallback_run: dict, alpha_runs: list) -> dict:
    """H1/H2/H3 intervention metrics on the a_prev -> a_prop transition.

    prev_run = current/previous config (a_prev, H1); prop_run = proposed config
    (a_prop); fallback_run = documented persisted reference action (H3);
    alpha_runs = [(alpha, run)] on the a_prev->a_prop segment incl endpoints.
    Post-intervention metrics are at the shared-initial instant (index 0, a
    strict single-step look-ahead). No policy is selected here."""
    a_prop = prop_run["normalized_action"]
    a_prev = prev_run["normalized_action"]
    a_fb = fallback_run["normalized_action"]
    cur0 = scalar_at(prev_run["_state"], 0)

    h1 = _policy_metrics(a_prop, a_prev, True, prev_run["_state"])
    h1["executed_action_source"] = "previous_action_a_prev"
    h1["n_extra_hydraulic_evals"] = 0

    h3 = _policy_metrics(a_prop, a_fb, True, fallback_run["_state"])
    h3["executed_action_source"] = "documented_fallback"
    h3["fallback_definition"] = "reference_nominal native PRV/pump setpoints"
    h3["n_extra_hydraulic_evals"] = 0

    safe_fns = {}
    for th in S1_THETA_P_PSI:
        safe_fns[("S1", f"theta_p_psi={th:g}")] = (
            lambda c, p, th=th: rule_s1_safe(p["p_min"], th))
    for eps in S2_EPS_P_PSI:
        safe_fns[("S2", f"eps_p_psi={eps:g}")] = (
            lambda c, p, eps=eps: rule_s2_safe(p["p_min"] - c["p_min"], eps))
    for eps in S3_EPS_D_PSI_NODESUM:
        safe_fns[("S3", f"eps_D_psi_nodesum={eps:g}")] = (
            lambda c, p, eps=eps: rule_s3_safe(p["D"] - c["D"], eps))
    safe_fns[("S4", "hard_backstop")] = lambda c, p: rule_s4_safe(p["N_neg"])

    h2 = {"policy": "clip_toward_previous", "per_rule_admissible_alpha": {}}
    for (cand, key), fn in safe_fns.items():
        alpha, run, n_eval = _h2_for_rule(cur0, alpha_runs, fn)
        m = _policy_metrics(a_prop, run["normalized_action"],
                            alpha == 0.0, run["_state"])
        m["executed_alpha"] = float(alpha)
        m["n_extra_hydraulic_evals"] = int(n_eval)
        h2["per_rule_admissible_alpha"].setdefault(cand, {})[key] = m

    return {"H1": h1, "H2": h2, "H3": h3}

# --- Static descriptors (PART 4 / 7 / 17 / 23) ---------------------------------
def metric_definitions() -> dict:
    """PART 4 / PART 23 metric-definition table (math, unit, interpretation)."""
    return {
        "p_i": {"math": "service pressure at node i", "unit": "psi",
                "interpretation": "121 service-junction pressures"},
        "p_min": {"math": "min_i p_i(t)", "unit": "psi",
                  "interpretation": "worst-node service pressure"},
        "dp_min": {"math": "p_min(post) - p_min(current)", "unit": "psi",
                   "interpretation": "worst-node change (post-action)"},
        "D": {"math": "sum_i max(0, 20 - p_i)", "unit": "psi_nodesum",
              "interpretation": "aggregate pressure deficit vs 20 psi"},
        "dD": {"math": "D(post) - D(current)", "unit": "psi_nodesum",
               "interpretation": "aggregate deficit change"},
        "N_neg": {"math": "sum_i I[p_i < 0]", "unit": "count",
                  "interpretation": "negative-pressure service nodes"},
        "N_20": {"math": "sum_i I[p_i < 20]", "unit": "count",
                 "interpretation": "DESCRIPTIVE sub-20-psi count (not an oracle)"},
        "Q_req": {"math": "sum requested demand", "unit": "gpm",
                  "interpretation": "requested demand"},
        "Q_served": {"math": "sum served demand (PDA)", "unit": "gpm",
                     "interpretation": "PDA-served demand"},
        "Q_unserved": {"math": "max(0, Q_req - Q_served)", "unit": "gpm",
                       "interpretation": "clipped unserved demand"},
        "DSR": {"math": "Q_served / Q_req", "unit": "ratio",
                "interpretation": "demand satisfaction ratio"},
        "Q_leak": {"math": "sum_j sign(p_j) C_j |p_j|^0.5", "unit": "gpm",
                   "interpretation": "emitter leakage (NOT calibrated)"},
        "dQ_leak": {"math": "Q_leak(post) - Q_leak(current)", "unit": "gpm",
                    "interpretation": "leakage change"},
        "dDSR": {"math": "DSR(post) - DSR(current)", "unit": "ratio",
                 "interpretation": "DSR change"},
        "dQ_unserved": {"math": "Q_unserved(post) - Q_unserved(current)",
                        "unit": "gpm", "interpretation": "unserved change"},
        "movement_L2sq": {"math": "||da_t||^2 on COMMANDED action", "unit": "-",
                          "interpretation": "reward effort term input (frozen)"},
        "action_deviation_L2": {"math": "||a_exec - a_prop||", "unit": "-",
                                "interpretation": "executed-vs-proposed gap"},
        "I_modified": {"math": "I[||a_exec - a_prop|| > tol]", "unit": "bool",
                       "interpretation": f"executed != proposed (tol {I_MODIFIED_TOL:g})"},
        "I_reject": {"math": "I[action rejected to a_prev/fallback]",
                     "unit": "bool", "interpretation": "hard rejection flag"},
    }

def candidate_descriptors() -> dict:
    """PART 7 candidate mechanisms S1-S4 (empirical descriptors only; enumeration
    order is definitional, NOT evaluative; no candidate is ordered or selected)."""
    return {
        "S1": {
            "exact_rule": "SAFE iff p_min(post) >= theta_p",
            "signal": "absolute_worst_node_pressure",
            "information_required": "post-action worst-node pressure (look-ahead)",
            "requires_look_ahead": True, "requires_extra_solve": True,
            "baseline_relation": "absolute",
            "note": "theta_p provisional; theta_p=20 psi vs chronic baseline "
                    "(worst node ~4.16 psi) examined empirically below"},
        "S2": {
            "exact_rule": "SAFE iff p_min(post) - p_min(current) >= -eps_p",
            "signal": "worst_node_degradation_vs_current",
            "information_required": "current + post worst-node pressure",
            "requires_look_ahead": True, "requires_extra_solve": True,
            "baseline_relation": "relative",
            "note": "eps_p provisional; relative, gives no absolute-min guarantee"},
        "S3": {
            "exact_rule": "SAFE iff D(post) - D(current) <= eps_D",
            "signal": "aggregate_deficit_increase",
            "information_required": "current + post deficit nodesum",
            "requires_look_ahead": True, "requires_extra_solve": True,
            "baseline_relation": "relative_aggregate",
            "note": "eps_D provisional; aggregate can mask localised collapse"},
        "S4": {
            "exact_rule": "SAFE iff N_neg(post) == 0",
            "signal": "negative_pressure_hard_backstop",
            "information_required": "post negative-node count",
            "requires_look_ahead": True, "requires_extra_solve": True,
            "baseline_relation": "absolute_negative_only",
            "note": "only well-posed HARD absolute gate; not a 20-psi guarantee"},
    }


def ppo_compatibility() -> dict:
    """PART 17 descriptive compatibility per mechanism (booleans + notes)."""
    common = {
        "deterministic": True, "continuous_action_preserved_under_clip": True,
        "differentiable": False, "discontinuous_under_reject": True,
        "requires_look_ahead": True, "requires_extra_epanet_solve": True,
        "compatible_30min_interval": True,
        "introduces_proposed_vs_executed_mismatch_under_intervention": True,
        "layer_need_not_be_differentiable": True}
    return {c: dict(common) for c in ("S1", "S2", "S3", "S4")}

def limitations() -> list:
    """PART 19 coverage limits + honesty caveats (values, not selections)."""
    return [
        "R1b: only the single lower corner (prv_lower / prv_lower_pump_lower) has "
        "measured near-collapse worst-node pressure; interior points, mixed PRV "
        "corners, and joint action x uncertain-demand space are NOT characterised.",
        "No validated safe/unsafe oracle exists; activation counts are DESCRIPTIVE "
        "and are NOT false-positive/false-negative rates or classification accuracy.",
        "sustained_horizon deltas include tank-trajectory divergence and are NOT a "
        "strict single-step look-ahead; only shared_initial_state (report index 0) "
        "is a pure command-effect one-step look-ahead.",
        "H2 alpha grid is coarse (0, 0.25, 0.5, 0.75, 1.0) and is demonstrated only "
        "on the reference->severe transition; not an exhaustive alpha search.",
        "Do NOT claim the 7-D action box is globally or jointly safe (STEP-9 "
        "mechanism + STEP-12 test job).",
        "Leakage emitter instrument is NOT field-calibrated; leak values are "
        "internally consistent evidence, not calibrated predictions.",
        "EVIDENCE ONLY: no mechanism/policy selected, ranked, scored, or "
        "recommended; no production wrapper, no reward.py, no PPO training.",
    ]


def _iter_keys(obj):
    """Yield every mapping key anywhere in a nested JSON-like structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _iter_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_keys(v)


def _all_finite(obj) -> bool:
    """True iff every numeric leaf is finite (bools/strings/None ignored)."""
    if isinstance(obj, bool):
        return True
    if isinstance(obj, (int, float)):
        return math.isfinite(float(obj))
    if isinstance(obj, dict):
        return all(_all_finite(v) for v in obj.values())
    if isinstance(obj, list):
        return all(_all_finite(v) for v in obj)
    return True

def local_collapse_scan(cur_run: dict, prop_run: dict) -> dict:
    """PART 10 evidence: instants where a small aggregate deficit increase (dD)
    coincides with a large NEGATIVE worst-node change (dp_min) - i.e. an aggregate
    guard can mask a localised worst-node collapse. Descriptive; no selection."""
    cs, ps = cur_run["_state"], prop_run["_state"]
    n = int(min(len(cs["p_min"]), len(ps["p_min"])))
    dp = ps["p_min"][:n] - cs["p_min"][:n]
    d_delta = ps["D"][:n] - cs["D"][:n]
    i_min_dp = int(np.argmin(dp))
    neg = dp < 0.0
    idx = np.where(neg)[0]
    i_masked = int(idx[np.argmin(d_delta[idx])]) if idx.size else i_min_dp
    return {
        "current_label": cur_run["label"], "proposed_label": prop_run["label"],
        "most_negative_dp_min_instant": {
            "report_index": i_min_dp, "dp_min": float(dp[i_min_dp]),
            "dD": float(d_delta[i_min_dp])},
        "min_deficit_increase_among_negative_dp_min_instants": {
            "report_index": i_masked, "dp_min": float(dp[i_masked]),
            "dD": float(d_delta[i_masked])},
        "n_negative_dp_min_instants": int(idx.size), "n_instants": n,
    }


def _self_checks(analysis: dict) -> list:
    """Return failed-check descriptions (empty list == all pass)."""
    failed = []
    bad = sorted({k for k in _iter_keys(analysis)
                  if any(t in str(k).lower() for t in FORBIDDEN_KEY_TOKENS)})
    if bad:
        failed.append(f"forbidden key tokens present: {bad}")
    meta = analysis["experiment_metadata"]
    if meta["action_dim"] != 7:
        failed.append("action_dim != 7")
    if meta["observation_dim"] != 139:
        failed.append("observation_dim != 139")
    if meta["n_service_junctions"] != 121:
        failed.append("n_service_junctions != 121")
    if analysis["researcher_selection"] is not None:
        failed.append("researcher_selection is not null")
    if not _all_finite(analysis):
        failed.append("non-finite numeric leaf present")
    ref = analysis["tested_states"]["reference_nominal"]["validated_accounting"]
    if abs(ref["leakage_mean_gpm"] - 84.72988433677985) > 1e-6:
        failed.append("reference leakage_mean_gpm drift vs frozen p6_s8")
    if ref["n_node_timesteps_below_20psi"] != 386:
        failed.append("reference sub-20 node-ts != 386")
    if ref["n_node_timesteps_negative_pressure"] != 0:
        failed.append("reference negative node-ts != 0")
    if P6S8_JSON.exists():
        d8 = json.loads(P6S8_JSON.read_text(encoding="utf-8"))
        r8 = d8["configurations"]["reference_nominal"]["validated_accounting"]
        if abs(r8["leakage_mean_gpm"] - ref["leakage_mean_gpm"]) > 1e-9:
            failed.append("reference leakage differs from persisted p6_s8 JSON")
    return failed

# --- Driver --------------------------------------------------------------------
def main() -> dict:
    R8.C.build_working_copy(verbose=False)
    wn0 = R8.S3.build(None, None)
    svc, conn = R8.S3.service_nodes(wn0)
    assert len(svc) == 121 and len(conn) == 5, (len(svc), len(conn))
    n_native = len(wn0.control_name_list)
    base_p, base_inflow, weights = R8.L.baseline_pressures("p6s9_size")
    sizing = R8.L.leak_coefficients(
        weights, base_p, R8.L.LEAK_TARGET_FRACTION * base_inflow)
    coeff_us = sizing["coefficient_gpm_per_psi_alpha"]

    # Bounded operating-point set (Class A/B/C + high-pressure current state).
    runs = {}
    for label, klass, prv, pump in base_operating_points():
        r = run_operating_point(label, prv, pump, coeff_us, svc, n_native)
        r["test_case_class"] = klass
        runs[label] = r

    # H2 interpolation grids: reference->severe and high_pressure->severe.
    a_ref = runs["reference_nominal"]["normalized_action"]
    a_hi = runs["prv_all_upper"]["normalized_action"]
    a_sev = runs["prv_lower_pump_lower"]["normalized_action"]
    interp = {"reference_to_severe": [], "high_pressure_to_severe": []}
    for label, klass, prv, pump in interpolated_points(a_ref, a_sev, "ref_sev"):
        r = run_operating_point(label, prv, pump, coeff_us, svc, n_native)
        r["test_case_class"] = klass
        runs[label] = r
        interp["reference_to_severe"].append(r)
    for label, klass, prv, pump in interpolated_points(a_hi, a_sev, "hi_sev"):
        r = run_operating_point(label, prv, pump, coeff_us, svc, n_native)
        r["test_case_class"] = klass
        runs[label] = r
        interp["high_pressure_to_severe"].append(r)
    mid = [a for a in H2_ALPHA_GRID if a not in (0.0, 1.0)]

    # Transitions (current-state -> proposed-action) on both measurement views.
    def T(cur, prop, klass):
        return transition_record(runs[cur], runs[prop], klass)

    transitions = {
        "T0_reference_to_reference": T(
            "reference_nominal", "reference_nominal", "identity_hold"),
        "T1_reference_to_severe": T(
            "reference_nominal", "prv_lower_pump_lower", "reference_to_severe"),
        "T2_reference_to_intermediate": T(
            "reference_nominal", "prv_all_lower", "reference_to_intermediate"),
        "T3_high_pressure_to_severe": T(
            "prv_all_upper", "prv_lower_pump_lower", "high_pressure_to_severe"),
        "T4_high_pressure_to_intermediate": T(
            "prv_all_upper", "prv_all_lower", "high_pressure_to_intermediate"),
    }
    rule_out = {name: safety_rule_outputs(runs[rec["current_label"]],
                                          runs[rec["proposed_label"]])
                for name, rec in transitions.items()}
    separation = {
        "from_reference_state": separation_question(
            rule_out["T1_reference_to_severe"],
            rule_out["T2_reference_to_intermediate"]),
        "from_high_pressure_state": separation_question(
            rule_out["T3_high_pressure_to_severe"],
            rule_out["T4_high_pressure_to_intermediate"]),
    }

    # Handling policies on the two severe transitions (alpha grid incl endpoints).
    ref_sev_alpha = ([(0.0, runs["reference_nominal"])]
                     + list(zip(mid, interp["reference_to_severe"]))
                     + [(1.0, runs["prv_lower_pump_lower"])])
    hi_sev_alpha = ([(0.0, runs["prv_all_upper"])]
                    + list(zip(mid, interp["high_pressure_to_severe"]))
                    + [(1.0, runs["prv_lower_pump_lower"])])
    policies = {
        "reference_to_severe": handling_policy_outputs(
            runs["reference_nominal"], runs["prv_lower_pump_lower"],
            runs["reference_nominal"], ref_sev_alpha),
        "high_pressure_to_severe": handling_policy_outputs(
            runs["prv_all_upper"], runs["prv_lower_pump_lower"],
            runs["reference_nominal"], hi_sev_alpha),
    }

    # Derived evidence blocks.
    baseline_compat = {
        "identity_hold_rule_activation": rule_out["T0_reference_to_reference"],
        "note": ("S1 flags the chronic baseline for theta_p above the baseline "
                 "worst node (~4.16 psi); S2/S3 never activate on an unchanged "
                 "hold (dp_min=0, dD=0); S4 never activates (0 negative nodes)."),
    }
    severe = {"prv_lower_pump_lower": {
        "test_case_class": "B_severe_degradation",
        "validated_accounting": runs["prv_lower_pump_lower"]["validated_accounting"],
        "sustained_worst_post_p_min": transitions["T1_reference_to_severe"][
            "sustained_horizon"]["worst_post_p_min_instant"],
        "reference_to_severe_rule_activation": rule_out["T1_reference_to_severe"],
        "high_pressure_to_severe_rule_activation":
            rule_out["T3_high_pressure_to_severe"]}}
    intermediate = {"prv_all_lower": {
        "test_case_class": "C_intermediate_control",
        "validated_accounting": runs["prv_all_lower"]["validated_accounting"],
        "reference_to_intermediate_rule_activation":
            rule_out["T2_reference_to_intermediate"],
        "high_pressure_to_intermediate_rule_activation":
            rule_out["T4_high_pressure_to_intermediate"]}}
    local_collapse = {
        "reference_to_severe": local_collapse_scan(
            runs["reference_nominal"], runs["prv_lower_pump_lower"]),
        "high_pressure_to_severe": local_collapse_scan(
            runs["prv_all_upper"], runs["prv_lower_pump_lower"])}
    comp_cost = {
        "n_epanet_solves_total": len(runs),
        "n_operating_points_measured": len(runs),
        "wall_clock_s_per_run": {lbl: r["wall_clock_s"] for lbl, r in runs.items()},
        "wall_clock_s_total": float(sum(r["wall_clock_s"] for r in runs.values())),
        "hydraulic_evals_per_proposed_action_look_ahead": 1,
        "h2_alpha_grid_evals_per_transition": len(mid) + 2,
        "determinism": ("EPANET deterministic: re-running reproduces every value; "
                        "JSON carries a generated_utc stamp so it is NOT "
                        "byte-identical across runs"),
        "note": ("each rule needs one post-action look-ahead solve per proposed "
                 "action; H2 needs one solve per alpha-grid point inspected."),
    }

    meta = {
        "work_unit": "WU-15",
        "purpose": ("EMPIRICAL characterization of candidate state-dependent "
                    "safety mechanisms S1-S4 and action-handling policies H1-H3; "
                    "evidence only, no selection/ordering/scoring/recommendation"),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "instrument": "p6_s8_reward_scale_analysis (validated, reused unchanged)",
        "working_inp_sha256": R8.C.sha256_file(R8.C.WORKING_INP),
        "protocol": {"eps_hours": 96, "hydraulic_timestep_s": 1800,
                     "native_rule_timestep_s": 180, "report_instants": 193,
                     "pda_required_psi": 20.0, "pda_min_psi": 0.0,
                     "pda_exponent": 0.5},
        "action_dim": ACTION_DIM, "actuator_order": ACTUATOR_ORDER,
        "action_bounds": {str(k): list(v) for k, v in ACT_BOUNDS.items()},
        "observation_dim": 139, "n_service_junctions": len(svc),
        "n_connector_junctions": len(conn), "n_native_controls": n_native,
        "reward_layer_frozen": "D-P6-005 C-A_F1_balanced_dense (NOT modified here)",
        "solver_policy": R8.S3.assert_solver(wn0),
    }
    provisional = {
        "S1_theta_p_psi": S1_THETA_P_PSI, "S2_eps_p_psi": S2_EPS_P_PSI,
        "S3_eps_D_psi_nodesum": S3_EPS_D_PSI_NODESUM, "H2_alpha_grid": H2_ALPHA_GRID,
        "note": "PROVISIONAL documented sets; NOT selected or tuned to an objective",
    }
    classes = {
        "A_reference": "native-control reference/baseline state",
        "B_severe_degradation": "previously observed near-collapse (min svc ~1.29 psi)",
        "C_intermediate_control": "regulation without Class B extremes",
        "reference_high_pressure_state": "distinct high-pressure current state",
        "note": "no class is claimed universally safe or unsafe (PART 5/6)",
    }
    tested_states = {lbl: {
        "test_case_class": r["test_case_class"], "commanded": r["commanded"],
        "normalized_action": r["normalized_action"], "n_timesteps": r["n_timesteps"],
        "validated_accounting": r["validated_accounting"],
        "all_finite": r["all_finite"], "wall_clock_s": r["wall_clock_s"]}
        for lbl, r in runs.items()}
    tested_actions = {lbl: r["normalized_action"] for lbl, r in runs.items()}
    current_state_metrics = {n: rec["shared_initial_state"]["current_state_metrics"]
                             for n, rec in transitions.items()}
    proposed_action_metrics = {n: rec["shared_initial_state"]["post_action_metrics"]
                               for n, rec in transitions.items()}
    post_action_metrics = {
        "note": ("raw transitions apply no intervention, so post == proposed here; "
                 "executed post-intervention states are under "
                 "handling_policy_outputs"),
        "by_transition_shared_initial": proposed_action_metrics,
    }
    delta_metrics = {n: rec["shared_initial_state"]["delta_metrics"]
                     for n, rec in transitions.items()}

    def _summ(pm):
        return {k: pm[k] for k in ("I_modified", "I_reject",
                                   "action_deviation_L2", "action_deviation_L2sq")}
    intervention_metrics = {seg: {
        "H1": _summ(pol["H1"]), "H3": _summ(pol["H3"]),
        "H2_per_rule_executed_alpha": {
            cand: {k: v["executed_alpha"] for k, v in d.items()}
            for cand, d in pol["H2"]["per_rule_admissible_alpha"].items()}}
        for seg, pol in policies.items()}

    analysis = {
        "experiment_metadata": meta,
        "metric_definitions": metric_definitions(),
        "candidates": candidate_descriptors(),
        "provisional_thresholds": provisional,
        "test_case_classes": classes,
        "tested_states": tested_states,
        "tested_actions": tested_actions,
        "transitions": transitions,
        "current_state_metrics": current_state_metrics,
        "proposed_action_metrics": proposed_action_metrics,
        "post_action_metrics": post_action_metrics,
        "delta_metrics": delta_metrics,
        "safety_rule_outputs": rule_out,
        "empirical_separation_question": separation,
        "handling_policy_outputs": policies,
        "intervention_metrics": intervention_metrics,
        "baseline_compatibility": baseline_compat,
        "severe_degradation_cases": severe,
        "intermediate_control_cases": intermediate,
        "local_collapse_examples": local_collapse,
        "computational_cost": comp_cost,
        "PPO_compatibility": ppo_compatibility(),
        "limitations": limitations(),
        "researcher_selection": None,
    }
    failed = _self_checks(analysis)
    if failed:
        raise SystemExit(f"self-checks failed: {failed}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(analysis, indent=2, default=str) + "\n",
                   encoding="utf-8")
    return analysis


if __name__ == "__main__":
    main()



