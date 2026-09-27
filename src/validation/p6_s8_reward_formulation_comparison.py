"""Phase 6 / STEP 8 (evidence extension) - empirical comparison of the four
PROPOSED reward formulations (F1-F4) for the BWSN-1 PPO environment.

Purpose: produce TRANSPARENT, REPRODUCIBLE evidence so the researcher can make
and document reward-formulation decision D-P6-005. This module DOES NOT select a
formulation, DOES NOT assign any score / rank / tier / winner, DOES NOT tune
final weights, DOES NOT add a state-dependent safety clamp (that is STEP 9), and
DOES NOT train PPO. Every comparison weight / penalty here is PROVISIONAL FOR
COMPARISON ONLY (see PROVISIONAL below); none is endorsed.

Method (no new science, no data leakage):
  * The candidate reward COMPONENTS are extracted by the *validated* STEP 8
    machinery, imported verbatim (p6_s8_reward_scale_analysis.run_config /
    .component_series), so every hydraulic/service number is identical to the
    Phase 5/6 instrument: 121-service-node mask, ACC 1e-5 / TRIALS 2000 / rule
    180 s / report 1800 s, PDA 20/0/0.5, signed emitter leak law, native
    controls and topology untouched.
  * The FIXED normalisation constants are LOADED from the persisted STEP 8
    artefact (results/phase6/p6_s8_reward_scale_analysis.json), never re-derived
    online. A deterministic cross-check re-derives leak_ref / req_ref from a
    fresh reference run and records the absolute discrepancy (expected 0).
  * The four formulations are evaluated per report timestep over the SAME
    representative in-bounds set of 19 static commands (reference/native, PRV
    lower/upper edges, pump edges, joint PRV+pump corners). Coverage is the
    edges + corners + reference of the 7-D action box; it is NOT exhaustive over
    the interior of the joint action space.

Static-command caveat (inherited from STEP 8): a static hold has zero
step-to-step COMMANDED movement, so da_t = 0 and the movement/effort term is
identically 0 in every configuration here. Its scale is characterised
ANALYTICALLY (a synthetic maximal move) and flagged as a training-time
HYPOTHESIS, never fabricated as measured.

Action-space bounds (fixed, STEP 6) are kept STRICTLY separate from any
state-dependent safety mechanism (STEP 9, unapproved): where a formulation is
unsafe without a clamp, that is reported as a STEP-9 requirement, never patched
in here.

Output: results/phase6/p6_s8_reward_formulation_comparison.json.
Deterministic: EPANET is deterministic, no RNG, no seed.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "env"))

import numpy as np  # noqa: E402
import phase5_common as C  # noqa: E402
import g6_g7_g8_leak_pda as L  # noqa: E402
import p6_s3_prv_finechar as S3  # noqa: E402
import state_builder as SB  # noqa: E402
import p6_s8_reward_scale_analysis as R8  # noqa: E402  (validated extractor)

STEP8_ARTEFACT = C.REPO / "results" / "phase6" / "p6_s8_reward_scale_analysis.json"

# --- PROVISIONAL comparison parameters (FOR COMPARISON ONLY, NOT approved) ----
# None of these are tuned, selected, or recommended. They exist solely to make
# the four PROPOSED formulations concrete enough to evaluate side by side. The
# sensitivity sweep deliberately varies them to show how the induced incentive
# shifts; no single setting is endorsed and no formulation is declared best.
PROVISIONAL = {
    "F1_normalized_weighted_sum": {
        "w_L": 1.0, "w_U": 1.0, "w_P": 1.0, "w_A": 1.0, "w_E": 0.0},
    "F2_constrained_penalty": {"lambda_service": 20.0, "big_hard": 100.0},
    "F3_baseline_relative": {"w_U": 1.0, "w_P_safety": 1.0},
    "F4_safety_first_lexicographic": {
        "safety_threshold_psi": 20.0, "c_soft_service": 10.0,
        "c_hard_negative": 100.0, "eps_effort": 0.01},
}

EPS = 1e-12  # zero-denominator guard for any ratio not covered by a fixed const


def _norm_primitives(series: dict, norm: dict) -> dict:
    """Per-timestep normalised primitives shared by the formulations.

    Uses the FIXED normalisation constants (`norm`, loaded from the STEP 8
    artefact). `unserved` is clipped at 0 for the service-deficit reading
    (served can marginally exceed requested, DSR up to ~1.002). Movement is 0
    for a static hold (da_t = 0)."""
    leak = np.asarray(series["leakage_gpm"], float)
    unserved = np.asarray(series["unserved_demand_gpm"], float)
    deficit = np.asarray(series["pressure_deficit_psi_nodesum"], float)
    power = np.asarray(series["pump_hydraulic_power_kw"], float)
    n_below = np.asarray(series["n_service_nodes_below_20psi"], float)
    n_neg = np.asarray(series["n_service_nodes_negative"], float)
    min_p = np.asarray(series["min_service_pressure_psi"], float)
    return {
        "leak_norm": leak / norm["leak_ref_gpm"],
        "unserved_norm": np.clip(unserved, 0.0, None) / norm["req_ref_gpm"],
        "deficit_norm": deficit / norm["deficit_ref_psi_nodesum"],
        "power_norm": power / norm["power_ref_kw"],
        "movement_norm": np.zeros_like(leak),
        "n_below20": n_below, "n_negative": n_neg, "min_service_psi": min_p,
        "unserved_raw": unserved, "leak_raw": leak,
    }


def reward_F1(prim: dict, norm: dict, p: dict) -> np.ndarray:
    """F1 - normalised weighted sum (all terms ~O(1), negative = cost)."""
    return -(p["w_L"] * prim["leak_norm"] + p["w_U"] * prim["unserved_norm"]
             + p["w_P"] * prim["deficit_norm"] + p["w_A"] * prim["movement_norm"]
             + p["w_E"] * prim["power_norm"])


def reward_F2(prim: dict, norm: dict, p: dict) -> np.ndarray:
    """F2 - constrained penalty; service protected by an explicit large term."""
    return -(prim["leak_norm"] + p["lambda_service"] * prim["deficit_norm"]
             + p["big_hard"] * np.clip(prim["n_below20"], 0.0, None))


def reward_F3(prim: dict, norm: dict, p: dict, unserved_ref: float) -> np.ndarray:
    """F3 - baseline-relative fractional leakage improvement vs native."""
    improve = (norm["leak_ref_gpm"] - prim["leak_raw"]) / norm["leak_ref_gpm"]
    excess_unserved = (np.clip(prim["unserved_raw"] - unserved_ref, 0.0, None)
                       / norm["req_ref_gpm"])
    return improve - p["w_U"] * excess_unserved - p["w_P_safety"] * prim["deficit_norm"]


def reward_F4(prim: dict, norm: dict, p: dict) -> np.ndarray:
    """F4 - safety-first lexicographic (dominant penalty when unsafe, else leak).

    Threshold `safety_threshold_psi` is a design choice; both 20 psi and 0 psi
    are reported in the sensitivity sweep. Effort is a tie-break (0 here: da=0).
    """
    minp = prim["min_service_psi"]
    theta = p["safety_threshold_psi"]
    neg = minp < 0.0
    soft = (~neg) & (minp < theta)
    ok = ~(neg | soft)
    r = np.empty_like(prim["leak_norm"])
    r[neg] = -p["c_hard_negative"] - prim["deficit_norm"][neg]
    r[soft] = -p["c_soft_service"] - prim["deficit_norm"][soft]
    r[ok] = -prim["leak_norm"][ok] - p["eps_effort"] * prim["movement_norm"][ok]
    return r


FORMULATIONS = ("F1", "F2", "F3", "F4")
BASE_KEY = {"F1": "F1_normalized_weighted_sum",
            "F2": "F2_constrained_penalty",
            "F3": "F3_baseline_relative",
            "F4": "F4_safety_first_lexicographic"}


def _reward_for(fkey: str, prim: dict, norm: dict, unserved_ref: float,
                params: dict) -> np.ndarray:
    if fkey == "F1":
        return reward_F1(prim, norm, params)
    if fkey == "F2":
        return reward_F2(prim, norm, params)
    if fkey == "F3":
        return reward_F3(prim, norm, params, unserved_ref)
    if fkey == "F4":
        return reward_F4(prim, norm, params)
    raise KeyError(fkey)


def _violating_fractions(prim: dict) -> dict:
    """Fraction of report timesteps in each safety band (descriptive)."""
    return {
        "frac_ts_any_node_below_20psi":
            float(np.mean(prim["n_below20"] > 0.0)),
        "frac_ts_any_node_negative":
            float(np.mean(prim["n_negative"] > 0.0)),
        "mean_n_nodes_below_20psi": float(np.mean(prim["n_below20"])),
        "min_service_psi_over_horizon": float(np.min(prim["min_service_psi"])),
    }


def _incentive_argmax(mean_by_cfg: dict) -> dict:
    """The highest-MEAN-reward configuration among the tested static set.

    This is the static command a reward-greedy agent would prefer WITHIN this
    non-exhaustive edges+corners set - it characterises the incentive DIRECTION
    a formulation induces (e.g. boundary-seeking). It is NOT a ranking of the
    formulations against each other, and NOT an optimum over the joint box."""
    label = max(mean_by_cfg, key=mean_by_cfg.get)
    return {"argmax_config_within_tested_set": label,
            "argmax_mean_reward": float(mean_by_cfg[label]),
            "reward_spread_across_tested_configs":
                float(max(mean_by_cfg.values()) - min(mean_by_cfg.values()))}


def analytic_effort_probe(norm: dict) -> dict:
    """Analytic magnitude of the movement/effort term (static runs give 0).

    A synthetic maximal single-step move da with ||da||^2 = L2sq_max maps to a
    normalised movement term of 1.0; a no-op maps to 0.0. Compared against the
    leak term's dynamic range so the researcher can see whether an effort weight
    of O(1) could dominate the objective. HYPOTHESIS (training-time), not
    measured - static holds cannot exercise movement."""
    return {
        "movement_L2sq_max": norm["movement_L2sq_max"],
        "normalised_movement_for_max_single_step_move": 1.0,
        "normalised_movement_for_static_hold": 0.0,
        "note": ("realised movement is 0 in every static configuration here; a "
                 "boundary-to-boundary single-step move would add w_A*1.0 of "
                 "cost. Whether that dominates depends on the (unchosen) weights "
                 "and the realised policy trajectory - a training-time "
                 "HYPOTHESIS. The effort term MUST use the COMMANDED normalised "
                 "action, never realised pump speed (native STATUS resets it)."),
    }


def _means(fkey: str, params: dict, prim_by_cfg: dict, norm: dict,
           unserved_ref: float) -> dict:
    """Per-configuration MEAN reward for one formulation + parameter set."""
    return {lab: float(np.mean(_reward_for(fkey, prim, norm, unserved_ref, params)))
            for lab, prim in prim_by_cfg.items()}


def _at_action_bound(label: str) -> bool:
    """reference_nominal is the interior native command; every other tested
    configuration sits on one or more action-space bounds (edge/corner)."""
    return label != "reference_nominal"


def pathology_analysis(prim_by_cfg: dict, norm: dict, unserved_ref: float,
                       base_means: dict) -> dict:
    """Structured, MEASURED evidence for reward-design failure modes A-H.

    Descriptive only: reports the incentive DIRECTION each formulation induces
    over the tested set and the service state at that incentive. No score, no
    rank, no winner. Action-space bounds (STEP 6, fixed) are reported as facts;
    any need for a state-dependent clamp is flagged as a STEP-9 requirement and
    NOT inserted here."""
    ref = prim_by_cfg["reference_nominal"]
    leak_span = {lab: float(np.mean(p["leak_norm"])) for lab, p in prim_by_cfg.items()}
    svc_min = {lab: float(np.min(p["min_service_psi"])) for lab, p in prim_by_cfg.items()}
    below20 = {lab: float(np.mean(p["n_below20"])) for lab, p in prim_by_cfg.items()}

    # A) leakage-only incentive (F1 with only w_L)
    lo_means = _means("F1", {"w_L": 1.0, "w_U": 0.0, "w_P": 0.0, "w_A": 0.0,
                             "w_E": 0.0}, prim_by_cfg, norm, unserved_ref)
    lo_arg = max(lo_means, key=lo_means.get)
    # B) service/safety-only incentive (F1 with no leak term)
    so_means = _means("F1", {"w_L": 0.0, "w_U": 1.0, "w_P": 1.0, "w_A": 0.0,
                             "w_E": 0.0}, prim_by_cfg, norm, unserved_ref)
    so_arg = max(so_means, key=so_means.get)

    leak_dynamic_range = max(leak_span.values()) - min(leak_span.values())
    pooled_below = np.concatenate([p["n_below20"] for p in prim_by_cfg.values()])
    pooled_neg = np.concatenate([p["n_negative"] for p in prim_by_cfg.values()])

    boundary = {}
    for fk in FORMULATIONS:
        arg = max(base_means[fk], key=base_means[fk].get)
        boundary[fk] = {
            "incentive_argmax_config": arg,
            "argmax_sits_on_action_bound": _at_action_bound(arg),
            "min_service_psi_at_argmax": svc_min[arg],
            "mean_n_below20_at_argmax": below20[arg],
            "mean_leak_norm_at_argmax": leak_span[arg]}

    flat = {fk: {"reward_spread_across_configs":
                 float(max(base_means[fk].values()) - min(base_means[fk].values())),
                 "mean_within_config_std":
                 float(np.mean([np.std(_reward_for(fk, prim, norm, unserved_ref,
                                                   PROVISIONAL[BASE_KEY[fk]]))
                                for prim in prim_by_cfg.values()]))}
            for fk in FORMULATIONS}

    return {
        "A_leakage_only_collapses_service": {
            "incentive_argmax_config": lo_arg,
            "argmax_sits_on_action_bound": _at_action_bound(lo_arg),
            "min_service_psi_at_argmax": svc_min[lo_arg],
            "reference_min_service_psi": svc_min["reference_nominal"],
            "mean_leak_norm_at_argmax": leak_span[lo_arg],
            "observation": ("a leak-only reward's highest-reward tested command "
                            "sits at the PRV lower bound; its worst-node service "
                            "pressure is reported for the researcher to judge."),
        },
        "B_service_only_raises_leakage": {
            "incentive_argmax_config": so_arg,
            "argmax_sits_on_action_bound": _at_action_bound(so_arg),
            "mean_leak_norm_at_argmax": leak_span[so_arg],
            "reference_mean_leak_norm": leak_span["reference_nominal"],
            "observation": ("a service/safety-only reward's highest-reward tested "
                            "command raises leakage relative to the leak-only "
                            "incentive; the two objectives pull in opposite "
                            "directions (consistent with STEP 8 correlations)."),
        },
        "C_actuator_penalty_domination": {
            "leak_term_dynamic_range_across_configs": float(leak_dynamic_range),
            "max_single_step_movement_cost_at_w_A_1": 1.0,
            "note": ("realised movement is 0 in all static configs; ANALYTIC "
                     "only. A unit-weight max move (cost 1.0) is comparable to "
                     "the entire measured leak-term range across tested commands "
                     f"(~{leak_dynamic_range:.3f}), so an un-tuned effort weight "
                     "could dominate the leakage objective - weight choice is a "
                     "D-P6-005 concern, not resolved here."),
        },
        "D_boundary_seeking_per_formulation": boundary,
        "E_flat_or_weak_signal_per_formulation": flat,
        "F_sparse_or_degenerate_violation_signal": {
            "frac_pooled_ts_any_node_below_20psi": float(np.mean(pooled_below > 0.0)),
            "frac_pooled_ts_any_node_negative": float(np.mean(pooled_neg > 0.0)),
            "reference_mean_n_below20": below20["reference_nominal"],
            "observation": ("the <0 psi hard term is identically inactive in "
                            "bounds (sparse), while the <20 psi term is active at "
                            "~every timestep INCLUDING the native baseline "
                            "(2 chronically low nodes). A hard 20 psi constraint "
                            "term therefore fires on the baseline itself; the "
                            "smooth deficit / min-pressure terms carry the dense "
                            "safety signal."),
        },
        "G_reward_hacking_and_degeneracy": {
            "closed_pump_realized_speed": (
                "effort/smoothness MUST be computed on the COMMANDED normalised "
                "action; realised pump speed is reset to 1.0 by STATUS-IS-OPEN "
                "or 0 when closed (G12), so penalising realised speed is gameable."),
            "hard_20psi_constraint_degeneracy": (
                "F2 (BIG*n_below20) and F4 (threshold 20 psi) treat the network's "
                "chronic sub-20 nodes as a constraint violation on EVERY tested "
                "command, so the leakage objective receives little/no gradient "
                "under those parameters - an ill-posed hard constraint, not a "
                "learning signal."),
            "lexicographic_0psi_permissiveness": (
                "F4 with a 0 psi threshold never triggers in bounds, so it "
                "reduces to pure leak minimisation and inherits the boundary-"
                "seeking-to-lower-PRV incentive while reporting 'safe'."),
        },
        "H_weight_penalty_sensitivity": {
            "note": ("see `sensitivity_results`: varying the PROVISIONAL weights "
                     "shifts the incentive-argmax configuration; this is expected "
                     "and is exactly why weight selection is deferred to the "
                     "researcher (D-P6-005)."),
        },
    }


def formulation_specs(norm: dict, unserved_ref: float) -> list:
    """Exact, self-contained spec of each PROPOSED formulation (PART 6)."""
    common = {
        "status": "PROPOSED",
        "sign_convention": "reward is a NEGATIVE cost; higher (less negative) is better",
        "time_aggregation": ("per report timestep (1800 s); episode return = sum "
                             "over the 193 report steps of a 96 h EPS. Reported "
                             "here as per-step temporal statistics + per-config "
                             "mean. No discounting applied in this measurement."),
        "terminal_behavior": ("fixed-horizon EPS, no early termination in Phase 6; "
                              "a STEP-9 safety termination/clamp is NOT part of "
                              "this measurement."),
        "normalization_constants_used": norm,
    }
    return [
        {**common, "id": "F1", "name": "normalized_weighted_sum",
         "expression": ("r_t = -w_L*(leak_t/leak_ref) - w_U*(unserved_t^+/req_ref) "
                        "- w_P*(deficit_t/deficit_ref) - w_A*(||da_t||^2/L2sq_max) "
                        "- w_E*(power_t/power_ref)"),
         "components": ["leakage", "unserved_demand", "pressure_deficit",
                        "actuator_movement", "pump_power(optional)"],
         "clipping": "unserved clipped at >=0; da=0 for static holds",
         "epsilon_handling": "all denominators are fixed nonzero constants",
         "provisional_weights": PROVISIONAL["F1_normalized_weighted_sum"]},
        {**common, "id": "F2", "name": "constrained_penalty_service_protected",
         "expression": ("r_t = -(leak_t/leak_ref) - LAMBDA*(deficit_t/deficit_ref) "
                        "- BIG*max(0, n_below20_t)"),
         "components": ["leakage", "pressure_deficit", "n_below20(hard)"],
         "clipping": "n_below20 clipped at >=0 (a count, already >=0)",
         "epsilon_handling": "fixed nonzero denominators",
         "provisional_parameters": PROVISIONAL["F2_constrained_penalty"]},
        {**common, "id": "F3", "name": "baseline_relative_improvement",
         "expression": ("r_t = (leak_ref - leak_t)/leak_ref "
                        "- w_U*max(0, unserved_t - unserved_ref)/req_ref "
                        "- w_P_safety*(deficit_t/deficit_ref)"),
         "components": ["fractional_leak_reduction_vs_native", "excess_unserved",
                        "pressure_deficit"],
         "clipping": "excess unserved clipped at >=0",
         "epsilon_handling": "fixed nonzero denominators",
         "baseline_constants": {"unserved_ref_gpm": unserved_ref,
                                "source": "native reference req-served (frozen)"},
         "provisional_weights": PROVISIONAL["F3_baseline_relative"]},
        {**common, "id": "F4", "name": "safety_first_lexicographic",
         "expression": ("if min_svc_p_t < 0: r_t = -c_hard - deficit_t/deficit_ref; "
                        "elif min_svc_p_t < theta: r_t = -c_soft - deficit_t/deficit_ref; "
                        "else: r_t = -(leak_t/leak_ref) - eps*(||da_t||^2/L2sq_max)"),
         "components": ["safety_band(min_service_pressure)", "pressure_deficit",
                        "leakage", "actuator_movement(tie-break)"],
         "clipping": "branch selection by min service pressure vs threshold",
         "epsilon_handling": "fixed nonzero denominators; eps effort tie-break",
         "provisional_parameters": PROVISIONAL["F4_safety_first_lexicographic"]},
    ]


def _sweep_point(fkey: str, params: dict, prim_by_cfg: dict, norm: dict,
                 unserved_ref: float) -> dict:
    m = _means(fkey, params, prim_by_cfg, norm, unserved_ref)
    arg = max(m, key=m.get)
    lower = m.get("prv_all_lower", float("nan"))
    return {"params": dict(params), "incentive_argmax_config": arg,
            "argmax_mean_reward": float(m[arg]),
            "reference_mean_reward": float(m["reference_nominal"]),
            "prv_all_lower_mean_reward": float(lower),
            "reference_minus_prv_all_lower": float(m["reference_nominal"] - lower)}


def sensitivity_analysis(prim_by_cfg: dict, norm: dict, unserved_ref: float) -> dict:
    """Vary PROVISIONAL parameters; report how the induced incentive shifts.

    Descriptive: reports which tested configuration becomes the incentive-argmax
    as a parameter changes. No formulation is ranked against another."""
    f1 = [_sweep_point("F1", {"w_L": 1.0, "w_U": 1.0, "w_P": wp, "w_A": 0.0,
                              "w_E": 0.0}, prim_by_cfg, norm, unserved_ref)
          for wp in (0.0, 0.5, 1.0, 2.0, 5.0)]
    f1u = [_sweep_point("F1", {"w_L": 1.0, "w_U": wu, "w_P": 1.0, "w_A": 0.0,
                               "w_E": 0.0}, prim_by_cfg, norm, unserved_ref)
           for wu in (0.0, 1.0, 5.0)]
    f2 = [_sweep_point("F2", {"lambda_service": lam, "big_hard": big},
                       prim_by_cfg, norm, unserved_ref)
          for lam in (5.0, 20.0, 100.0) for big in (10.0, 100.0, 1000.0)]
    f3 = [_sweep_point("F3", {"w_U": wu, "w_P_safety": wp},
                       prim_by_cfg, norm, unserved_ref)
          for wu in (0.0, 1.0, 5.0) for wp in (0.0, 1.0, 5.0)]
    f4 = [_sweep_point("F4", {"safety_threshold_psi": th, "c_soft_service": 10.0,
                              "c_hard_negative": 100.0, "eps_effort": 0.01},
                       prim_by_cfg, norm, unserved_ref) for th in (0.0, 20.0)]
    return {"F1_vary_w_P": f1, "F1_vary_w_U": f1u,
            "F2_vary_lambda_big": f2, "F3_vary_w_U_w_P": f3,
            "F4_vary_threshold": f4,
            "note": ("PROVISIONAL FOR COMPARISON ONLY. The incentive-argmax "
                     "shifting with weights is the intended demonstration that "
                     "weight/formulation selection is a researcher decision "
                     "(D-P6-005), not an automatable one.")}


def _category(label: str) -> str:
    if label == "reference_nominal":
        return "native_reference"
    if label == "prv_all_lower":
        return "joint_prv_lower_edge_lower_pressure"
    if label == "prv_all_upper":
        return "joint_prv_upper_edge_higher_pressure"
    if label.startswith("pump_all_"):
        return "pump_only_edge"
    if "_pump_" in label:
        return "joint_prv_pump_corner"
    return "single_prv_edge"


def main() -> dict:
    step8 = json.loads(STEP8_ARTEFACT.read_text(encoding="utf-8"))
    norm = {k: step8["proposed_normalization_constants"][k] for k in
            ("leak_ref_gpm", "req_ref_gpm", "deficit_ref_psi_nodesum",
             "power_ref_kw", "movement_L2sq_max")}
    ra0 = step8["configurations"]["reference_nominal"]["validated_accounting"]
    unserved_ref = ra0["requested_demand_mean_gpm"] - ra0["served_demand_mean_gpm"]

    C.build_working_copy(verbose=False)
    wn0 = S3.build(None, None)
    svc, conn = S3.service_nodes(wn0)
    assert len(svc) == 121 and len(conn) == 5, (len(svc), len(conn))
    n_native_controls = len(wn0.control_name_list)

    base_p, base_inflow, weights = L.baseline_pressures("p6s8cmp_size")
    sizing = L.leak_coefficients(weights, base_p, L.LEAK_TARGET_FRACTION * base_inflow)
    coeff_us = sizing["coefficient_gpm_per_psi_alpha"]

    prim_by_cfg: dict = {}
    runs: dict = {}
    for label, prv_psi, pump_speed in R8._configurations():
        r = R8.run_config(label, prv_psi, pump_speed, coeff_us, svc, n_native_controls)
        prim_by_cfg[label] = _norm_primitives(r["_series"], norm)
        r.pop("_series", None)
        runs[label] = r

    # --- Reproducibility gate: reference must reproduce the frozen baseline ----
    ref = runs["reference_nominal"]
    ref_prim = prim_by_cfg["reference_nominal"]
    fresh_leak_ref = float(np.mean(ref_prim["leak_raw"]))
    fresh_req_ref = ref["validated_accounting"]["requested_demand_mean_gpm"]
    xcheck_max = max(max(runs[c]["per_timestep_vs_accounting_cross_check"].values())
                     for c in runs)
    reproduce = {
        "reference_leak_mean_gpm": fresh_leak_ref,
        "frozen_leak_ref_gpm": norm["leak_ref_gpm"],
        "leak_ref_abs_diff": abs(fresh_leak_ref - norm["leak_ref_gpm"]),
        "req_ref_abs_diff": abs(fresh_req_ref - norm["req_ref_gpm"]),
        "reference_dsr_mean": ref["validated_accounting"]["dsr_mean"],
        "reference_n_node_ts_below_20psi":
            ref["validated_accounting"]["n_node_timesteps_below_20psi"],
        "reference_n_node_ts_negative":
            ref["validated_accounting"]["n_node_timesteps_negative_pressure"],
        "per_timestep_vs_validated_accounting_max_abs_diff": float(xcheck_max),
    }
    assert reproduce["leak_ref_abs_diff"] < 1e-6, reproduce
    assert reproduce["req_ref_abs_diff"] < 1e-6, reproduce
    assert ref["validated_accounting"]["n_node_timesteps_below_20psi"] == 386
    assert ref["validated_accounting"]["n_node_timesteps_negative_pressure"] == 0
    assert xcheck_max < 1e-6, xcheck_max

    # --- Reward series, per-config metrics, pooling ----------------------------
    reward_series = {lab: {fk: _reward_for(fk, prim_by_cfg[lab], norm, unserved_ref,
                                           PROVISIONAL[BASE_KEY[fk]])
                           for fk in FORMULATIONS} for lab in prim_by_cfg}
    per_cfg = {}
    for lab in prim_by_cfg:
        va = runs[lab]["validated_accounting"]
        per_cfg[lab] = {
            "commanded": runs[lab]["commanded"],
            "n_timesteps": runs[lab]["n_timesteps"],
            "validated_accounting_subset": {
                "leakage_mean_gpm": va["leakage_mean_gpm"],
                "dsr_mean": va["dsr_mean"],
                "n_node_timesteps_below_20psi": va["n_node_timesteps_below_20psi"],
                "n_node_timesteps_negative_pressure":
                    va["n_node_timesteps_negative_pressure"]},
            "per_timestep_vs_accounting_max_abs_diff":
                float(max(runs[lab]["per_timestep_vs_accounting_cross_check"].values())),
            "violating_fractions": _violating_fractions(prim_by_cfg[lab]),
            "reward_temporal_stats": {fk: R8.stats(reward_series[lab][fk])
                                      for fk in FORMULATIONS},
            "all_reward_finite": bool(all(np.isfinite(reward_series[lab][fk]).all()
                                          for fk in FORMULATIONS)),
        }

    pooled = {fk: R8.stats(np.concatenate([reward_series[lab][fk]
                                           for lab in prim_by_cfg]))
              for fk in FORMULATIONS}
    temporal = {fk: {
        "mean_within_config_std":
            float(np.mean([np.std(reward_series[lab][fk]) for lab in prim_by_cfg])),
        "mean_within_config_abs_step_diff":
            float(np.mean([R8.stats(reward_series[lab][fk])["mean_abs_step_diff"]
                           for lab in prim_by_cfg]))} for fk in FORMULATIONS}

    base_means = {fk: _means(fk, PROVISIONAL[BASE_KEY[fk]], prim_by_cfg, norm,
                             unserved_ref) for fk in FORMULATIONS}
    incentive = {fk: _incentive_argmax(base_means[fk]) for fk in FORMULATIONS}

    checks = pathology_analysis(prim_by_cfg, norm, unserved_ref, base_means)
    sens = sensitivity_analysis(prim_by_cfg, norm, unserved_ref)
    effort = analytic_effort_probe(norm)

    # __MAIN_TAIL__
    all_finite = bool(all(per_cfg[lab]["all_reward_finite"] for lab in per_cfg)
                      and all(np.isfinite(list(pooled[fk].values())).all()
                              for fk in FORMULATIONS))
    payload = {
        "experiment_metadata": {
            "phase": 6, "step": 8,
            "title": ("Empirical comparison of the four PROPOSED reward "
                      "formulations (F1-F4) for the BWSN-1 PPO environment"),
            "status": ("EVIDENCE ONLY. No formulation selected, no score/rank/tier/"
                       "winner assigned, no weights tuned, no safety clamp added "
                       "(STEP 9), no PPO trained. D-P6-005 remains PROPOSED."),
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "env": C.env_info(),
            "purpose": ("transparent, reproducible evidence for the researcher to "
                        "make and document decision D-P6-005; measurement over "
                        "preference, evidence over intuition."),
            "coverage_statement": (
                "19 static in-bounds commands x 193 report timesteps = 3667 "
                "instants: native reference, joint PRV lower/upper edges, each PRV "
                "isolated at its lower/upper edge, both pump edges, and four mixed "
                "PRV+pump corners. This is the edges+corners+reference of the 7-D "
                "action box and is NOT exhaustive over the joint-action interior; "
                "interior/mixed-corner joint safety is a STEP-9 + STEP-12 job."),
            "solver_policy": {
                "accuracy": S3.SOLVER_ACCURACY, "trials": S3.SOLVER_TRIALS,
                "rule_timestep_s": S3.RULE_TIMESTEP_S,
                "report_timestep_s": S3.REPORT_TIMESTEP_S,
                "pda_required_psi": L.PDA_REQUIRED_PSI,
                "pda_minimum_psi": L.PDA_MINIMUM_PSI, "pda_exponent": L.PDA_EXPONENT,
                "asserted_after_every_load": True},
            "service_node_policy": {
                "n_service_junctions": len(svc), "n_connector_junctions": len(conn),
                "connector_nodes": conn},
            "leak_instrument_status": (
                "VALIDATION instrument, NOT field-calibrated; only RELATIVE "
                "leakage response is meaningful (brief 18)."),
            "action_space_reference": {
                "source": "docs/PHASE6_ACTION_SPACE_SPEC.md (D-P6-001/002/003, FROZEN)",
                "prv_bounds_psi": {v: list(SB.PRV_BOUNDS_PSI[v]) for v in SB.PRV_IDS},
                "pump_bounds_rel_speed": {p: list(SB.PUMP_BOUNDS[p]) for p in SB.PUMP_IDS}},
            "separation_of_concerns": (
                "action-space bounds (STEP 6, fixed) are NOT a safety mechanism; "
                "any state-dependent clamp is STEP 9 (unapproved) and is NOT "
                "applied in this measurement."),
        },
        "formulations": formulation_specs(norm, unserved_ref),
        "provisional_parameters": {
            "disclaimer": "PROVISIONAL FOR COMPARISON ONLY - none selected or tuned",
            "values": PROVISIONAL},
        "normalization_constants": {
            **norm,
            "derived_baseline_unserved_ref_gpm": unserved_ref,
            "source": ("LOADED verbatim from results/phase6/"
                       "p6_s8_reward_scale_analysis.json (frozen, no online/running "
                       "statistics, no test-set fitting)."),
            "note": step8["proposed_normalization_constants"]["note"]},
        "tested_configurations": [
            {"label": lab, "category": _category(lab),
             "commanded": runs[lab]["commanded"]} for lab in prim_by_cfg],
        "per_configuration_metrics": per_cfg,
        "pooled_statistics": pooled,
        "temporal_statistics": temporal,
        "induced_incentive_per_formulation": incentive,
        "actuator_effort_analytic": effort,
        "pathology_results": checks,
        "sensitivity_results": sens,
        "limitations": [
            "Static-command runs: realised actuator movement is 0, so the F1/F4 "
            "effort term is identically 0 here; its scale is ANALYTIC (HYPOTHESIS).",
            "Leakage is a VALIDATION instrument, not field-calibrated; only "
            "relative response is meaningful, never an absolute leakage claim.",
            "Coverage is edges+corners+reference of the 7-D action box; the joint "
            "interior is NOT covered - no exhaustive joint-safety claim.",
            "Provisional weights/penalties are for side-by-side comparison only; "
            "no formulation is scored, ranked, or selected (D-P6-005 stays PROPOSED).",
            "The <20 psi service threshold is chronically unmet by the native "
            "BWSN-1 baseline (2 nodes), so hard 20 psi constraint terms fire on "
            "the baseline itself - a formulation-design consideration, not a bug.",
        ],
        "reproducibility_information": {
            "working_inp_sha256": C.sha256_file(C.WORKING_INP),
            "step8_artefact_used": str(STEP8_ARTEFACT.name),
            "deterministic": "EPANET deterministic; no RNG; no seed",
            "reference_reproduces_frozen_baseline": reproduce,
            "no_topology_or_native_rule_change": True,
            "no_future_information_used": True,
            "native_controls_count": n_native_controls,
            "all_reward_values_finite": all_finite,
            "generator": "src/validation/p6_s8_reward_formulation_comparison.py",
            "component_extractor": "src/validation/p6_s8_reward_scale_analysis.py",
        },
    }

    out = C.REPO / "results" / "phase6"
    out.mkdir(parents=True, exist_ok=True)
    path = out / "p6_s8_reward_formulation_comparison.json"
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"[written] {path}")
    return payload


if __name__ == "__main__":
    main()






