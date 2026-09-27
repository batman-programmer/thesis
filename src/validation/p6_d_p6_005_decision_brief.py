#!/usr/bin/env python3
"""D-P6-005 reward decision brief — evidence aggregator (WU-11).

PURPOSE
-------
Assemble the machine-readable D-P6-005 decision brief from the ALREADY-FROZEN
STEP 8 evidence artefacts (WU-9 scale analysis + WU-10 formulation comparison).

This script MEASURES NOTHING NEW. It re-loads the two committed JSON artefacts,
re-checks their frozen normalisation constants and reproducibility markers, adds
the PROVISIONAL (NOT APPROVED) candidate parameterisations derived analytically
from the measured scales, and writes
``results/phase6/p6_d_p6_005_decision_brief.json`` with ``researcher_selection``
set to ``null``.

Binding constraints honoured (D-P6-005 DECISION GATE):
  * does NOT run EPANET, does NOT run PPO;
  * does NOT select / rank / score / declare a winner among F1-F4;
  * does NOT modify the approved action space or the frozen observation spec;
  * does NOT add a STEP-9 safety clamp;
  * D-P6-005 stays PROPOSED / DECISION PENDING RESEARCHER.

The only NEW content is descriptive: candidate parameterisations whose numeric
constants are each traced to a MEASURED scale in the WU-9/WU-10 artefacts, plus
an analytic (not-fitted) low/central/high reading of parameters. No candidate is
tuned to a preferred result and none is ranked.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "phase6"
WU9_PATH = RESULTS / "p6_s8_reward_scale_analysis.json"
WU10_PATH = RESULTS / "p6_s8_reward_formulation_comparison.json"
STATE_SPEC_PATH = RESULTS / "p6_s7_state_spec.json"
OUT_PATH = RESULTS / "p6_d_p6_005_decision_brief.json"

DECISION_ID = "D-P6-005"
STATUS = "PROPOSED / DECISION PENDING RESEARCHER"
NOT_APPROVED = "PROVISIONAL CANDIDATE - NOT APPROVED"


def _load(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _finite(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _all_finite(obj) -> bool:
    if isinstance(obj, dict):
        return all(_all_finite(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return all(_all_finite(v) for v in obj)
    if isinstance(obj, bool) or obj is None or isinstance(obj, str):
        return True
    return _finite(obj)


def candidate_parameterizations(consts: dict) -> list:
    """PROVISIONAL, NOT APPROVED. Each numeric constant is traced to a MEASURED
    scale in WU-9/WU-10. None is tuned to a preferred result; none is ranked."""
    leak_ref = consts["leak_ref_gpm"]
    req_ref = consts["req_ref_gpm"]
    deficit_ref = consts["deficit_ref_psi_nodesum"]
    power_ref = consts["power_ref_kw"]
    l2sq = consts["movement_L2sq_max"]
    unserved_ref = req_ref * (1.0 - 0.9833370137001072)  # baseline DSR-implied; see note
    # WU-9/WU-10 measured anchors used to JUSTIFY (not fit) the constants below:
    #   leak-term dynamic range across in-bounds configs ~ 0.108 (WU-10 pathology C)
    #   max single-step movement cost (normalised) = 1.0  (28/28)
    #   deficit<->leak corr -0.7735 ; min_svc dense (WU-9 cross_component_correlation)
    return [
        {
            "candidate_id": "C-A_F1_balanced_dense",
            "status": NOT_APPROVED,
            "base_formulation": "F1_normalized_weighted_sum",
            "equation": (
                "r_t = - w_L*(leak_t/leak_ref) - w_U*(unserved_t^+/req_ref) "
                "- w_P*(deficit_t/deficit_ref) - w_A*(||da_t||^2/L2sq_max) "
                "- w_E*(power_t/power_ref)"
            ),
            "constants": {
                "leak_ref_gpm": leak_ref, "req_ref_gpm": req_ref,
                "deficit_ref_psi_nodesum": deficit_ref, "power_ref_kw": power_ref,
                "movement_L2sq_max": l2sq,
            },
            "provisional_weights": {"w_L": 1.0, "w_U": 1.0, "w_P": 1.0, "w_A": 0.1, "w_E": 0.0},
            "scale_derivation": (
                "All four active terms are pre-normalised to O(1) by the FROZEN WU-9 "
                "constants, so unit weights are the neutral starting point. w_A=0.1 is "
                "read from WU-10 pathology C: the leak-term dynamic range across in-bounds "
                "commands is ~0.108, while one max-movement step costs 1.0 at w_A=1; scaling "
                "w_A to ~0.1 keeps a full-swing action step commensurate with (not dominating) "
                "the measured leakage signal. w_E=0 keeps the (optional, hydraulic-only) energy "
                "term out to avoid parameter proliferation."
            ),
            "plausibility": "dense, differentiable, PPO-continuous friendly (INFERRED).",
            "tradeoff": (
                "Balanced leakage/service/safety/effort; but WU-10 induced-incentive argmax "
                "under unit weights is prv_176_upper and the leak-only optimum sits at the PRV "
                "lower corner (OBSERVED) -> a STEP-9 clamp is required, not optional."
            ),
            "risk": (
                "WU-10 F1_vary_w_P shows w_P=0 -> prv_175_lower; w_P>=0.5 -> prv_176_upper. "
                "w_P below ~0.5 lets the incentive drift toward the low-pressure corner."
            ),
            "validation_experiment": (
                "After the STEP-9 clamp exists: short deterministic PPO smoke test to confirm "
                "the per-step reward is non-flat and finite; measure realised ||da||^2 to replace "
                "the analytic effort ceiling (HYPOTHESIS)."
            ),
        },
        {
            "candidate_id": "C-B_F1_safety_leaning",
            "status": NOT_APPROVED,
            "base_formulation": "F1_normalized_weighted_sum",
            "equation": "same functional form as C-A",
            "constants": {
                "leak_ref_gpm": leak_ref, "req_ref_gpm": req_ref,
                "deficit_ref_psi_nodesum": deficit_ref, "power_ref_kw": power_ref,
                "movement_L2sq_max": l2sq,
            },
            "provisional_weights": {"w_L": 1.0, "w_U": 1.0, "w_P": 2.0, "w_A": 0.1, "w_E": 0.0},
            "scale_derivation": (
                "Identical to C-A except w_P=2.0. Motivated by the measured deficit<->leak "
                "correlation -0.7735 and the dense worst-node min-pressure signal (WU-9): a "
                "heavier normalised deficit weight more strongly protects worst-node pressure. "
                "w_P=2 is still O(1) after normalisation."
            ),
            "plausibility": "dense, differentiable; a safety-leaning emphasis of C-A (INFERRED).",
            "tradeoff": (
                "More weight on pressure safety may reduce achievable leakage cuts; this is a "
                "different emphasis, NOT a ranking versus C-A."
            ),
            "risk": "Over-weighting deficit could flatten the leakage gradient (leak span ~+/-6%).",
            "validation_experiment": "Same smoke test as C-A; compare realised min-pressure margin.",
        },
        {
            "candidate_id": "C-C_F3_baseline_relative",
            "status": NOT_APPROVED,
            "base_formulation": "F3_baseline_relative_improvement",
            "equation": (
                "r_t = (leak_ref - leak_t)/leak_ref "
                "- w_U*max(0, unserved_t - unserved_ref)/req_ref "
                "- w_P_safety*(deficit_t/deficit_ref)"
            ),
            "constants": {
                "leak_ref_gpm": leak_ref, "req_ref_gpm": req_ref,
                "deficit_ref_psi_nodesum": deficit_ref, "unserved_ref_gpm": unserved_ref,
            },
            "provisional_weights": {"w_U": 1.0, "w_P_safety": 1.0},
            "scale_derivation": (
                "Leakage improvement term is intrinsically normalised (fraction of baseline "
                "leakage) and zero-centred at the native controller, so no leak weight is needed. "
                "unserved_ref is the baseline unserved implied by DSR=0.98334 (~15.10 GPM; the "
                "WU-9 accounting value is 14.985 GPM). w_P_safety=1 uses the FROZEN deficit_ref. "
                "WU-10 F3 sweep: w_P_safety=0 -> prv_175_lower/prv_lower_pump_lower; "
                "w_P_safety>=1 -> prv_176_upper, so keep w_P_safety>=1."
            ),
            "plausibility": "interpretable as % leakage reduction vs native baseline (INFERRED).",
            "tradeoff": (
                "Directly answers the thesis objective (reduction vs baseline) but the leakage "
                "improvement dynamic range is small (~+/-6%), so signal-to-noise must be checked."
            ),
            "risk": "Small reward magnitude may need reward/advantage scaling at training time.",
            "validation_experiment": "Smoke test: confirm advantage estimates are non-degenerate.",
        },
        {
            "candidate_id": "C-D_dense_deficit_no_hard_count",
            "status": NOT_APPROVED,
            "base_formulation": "F2/F4_family_dense_safety_variant",
            "equation": (
                "r_t = -(leak_t/leak_ref) - LAMBDA*(deficit_t/deficit_ref) "
                "- BIG*max(0, n_negative_t)   # hard term on NEGATIVE nodes only"
            ),
            "constants": {
                "leak_ref_gpm": leak_ref, "deficit_ref_psi_nodesum": deficit_ref,
            },
            "provisional_weights": {"LAMBDA_service": 5.0, "BIG_hard_negative": 100.0},
            "scale_derivation": (
                "Explicitly REPLACES the F2 hard n_below_20 term with the dense deficit term, "
                "because WU-10 pathology F/G show the 20-psi count fires on the native baseline "
                "itself (frac_ts_any_node_below_20psi = 1.0) -> a hard 20-psi term is ill-posed on "
                "this network. The hard term is retained ONLY on NEGATIVE nodes (baseline count 0, "
                "frac_negative=0.0) so it is well-posed and fires only if a control drives a node "
                "sub-zero. LAMBDA=5 keeps the normalised deficit term within ~1 order of magnitude "
                "of the O(1) leak term (deficit_ref-normalised); it is a central value in [1,10], "
                "not fitted."
            ),
            "plausibility": "service protected by construction with a well-posed hard backstop (INFERRED).",
            "tradeoff": (
                "Avoids the ill-posed 20-psi penalty; but LAMBDA is unmeasured and sets the "
                "leakage/service exchange rate, which the researcher must choose."
            ),
            "risk": (
                "WU-10 F2 lambda/big sweep argmax is stable at prv_176_upper (incentive direction "
                "robust) but reward MAGNITUDE is untuned; a very large LAMBDA suppresses the "
                "leakage gradient."
            ),
            "validation_experiment": (
                "Smoke test with STEP-9 clamp active; confirm the negative-node hard term never "
                "fires in-bounds and only activates on genuine violations."
            ),
        },
    ]


def decision_dimensions() -> list:
    """FACTUAL comparison dimensions. NOT scored, NOT weighted, NOT ranked."""
    return [
        "leakage_management_signal",
        "service_preservation",
        "pressure_safety_signal_density",
        "signal_density_dense_vs_sparse",
        "scale_stability_fixed_normalisation",
        "interpretability_thesis_explainability",
        "parameter_count_and_sensitivity",
        "reward_hacking_resistance",
        "ppo_continuous_action_compatibility",
        "step9_safety_layer_compatibility",
        "reproducibility_no_leakage",
        "baseline_relatability",
    ]


def chronic_baseline_service_issue(wu10: dict) -> dict:
    ref = wu10["per_configuration_metrics"]["reference_nominal"]
    return {
        "observation": (
            "The frozen native baseline already holds >=1 service node < 20 psi at EVERY "
            "report timestep (frac_ts_any_node_below_20psi = 1.0; 386 node-timesteps < 20 psi; "
            "min service pressure 4.16452 psi @ JUNCTION-29) with 0 negative-pressure nodes."
        ),
        "baseline_metrics": {
            "n_node_timesteps_below_20psi": ref["validated_accounting_subset"][
                "n_node_timesteps_below_20psi"],
            "n_node_timesteps_negative": ref["validated_accounting_subset"][
                "n_node_timesteps_negative_pressure"],
            "frac_ts_any_node_below_20psi": ref["violating_fractions"][
                "frac_ts_any_node_below_20psi"],
            "frac_ts_any_node_negative": ref["violating_fractions"]["frac_ts_any_node_negative"],
            "min_service_psi_over_horizon": ref["violating_fractions"][
                "min_service_psi_over_horizon"],
        },
        "threshold_handling_options": {
            "absolute_hard_20psi_constraint": (
                "ILL-POSED on this network: it penalises the native baseline itself at every "
                "timestep and cannot separate agent-caused violations from pre-existing ones."
            ),
            "deficit_based_penalty": (
                "WELL-POSED: dense, smooth sum of max(0, 20 - p_i) over service nodes; normalised "
                "by deficit_ref (28.6718). Measured deficit<->leak corr -0.7735."
            ),
            "improvement_relative_to_baseline": (
                "WELL-POSED: penalise only unserved/deficit ABOVE the baseline level; zero-centred "
                "at the native controller (F3 / C-C)."
            ),
            "worst_node_min_pressure": (
                "WELL-POSED: dense min_service_pressure signal (WU-9 mean 4.77 psi, range "
                "[1.09, 5.93]); used as the lexicographic trigger in F4."
            ),
            "min_pressure_hard_constraint": (
                "ONLY well-posed on NEGATIVE pressure (baseline count 0). A hard 20-psi min "
                "constraint is NOT well-posed (baseline violates it)."
            ),
            "fraction_below_threshold": (
                "Degenerate as a hard term (fraction = 1.0 at baseline); usable only as a dense/"
                "relative signal, not a hard gate."
            ),
        },
        "conclusion": (
            "No formulation can use a HARD 20-psi constraint without penalising the native "
            "baseline itself. Dense deficit / worst-node min-pressure / baseline-relative service "
            "signals are the defensible safety channels; any hard gate must key on NEGATIVE "
            "pressure (or on a threshold strictly below the baseline worst-node ~4.16 psi), and "
            "the enforced 20-psi guarantee belongs to the STEP-9 execution-level clamp, not to a "
            "reward-level hard term."
        ),
    }


def build_brief() -> dict:
    wu9 = _load(WU9_PATH)
    wu10 = _load(WU10_PATH)
    state_spec = _load(STATE_SPEC_PATH) if STATE_SPEC_PATH.exists() else {}

    consts = wu9["proposed_normalization_constants"]
    consts10 = wu10["normalization_constants"]
    # Reproducibility re-check: the two artefacts must carry identical frozen constants.
    shared = ["leak_ref_gpm", "req_ref_gpm", "deficit_ref_psi_nodesum",
              "power_ref_kw", "movement_L2sq_max"]
    const_match = {k: (abs(float(consts[k]) - float(consts10[k])) < 1e-9) for k in shared}

    repro = wu10.get("reproducibility_information", {})
    brief = {
        "decision_id": DECISION_ID,
        "status": STATUS,
        "generated_by": "src/validation/p6_d_p6_005_decision_brief.py (WU-11)",
        "measures_nothing_new": True,
        "no_epanet_no_ppo_no_selection": True,
        "evidence_artifacts": {
            "wu9_scale_analysis": "results/phase6/p6_s8_reward_scale_analysis.json",
            "wu10_formulation_comparison": "results/phase6/p6_s8_reward_formulation_comparison.json",
            "state_spec": "results/phase6/p6_s7_state_spec.json",
            "reward_spec_doc": "docs/PHASE6_REWARD_SPEC.md",
            "action_space_spec_doc": "docs/PHASE6_ACTION_SPACE_SPEC.md",
        },
        "frozen_constraints": {
            "action_space": {
                "decision": "D-P6-001/002/003 APPROVED & FROZEN",
                "action_dim": 7,
                "encoding": "ABSOLUTE a_i in [-1,1]; physical = lower + ((a+1)/2)*(upper-lower)",
                "ordered_bounds": [
                    {"index": 0, "actuator": "VALVE-173", "lower": 54.5, "upper": 100.0, "unit": "psi"},
                    {"index": 1, "actuator": "VALVE-175", "lower": 21.5, "upper": 110.0, "unit": "psi"},
                    {"index": 2, "actuator": "VALVE-176", "lower": 20.0, "upper": 59.524, "unit": "psi"},
                    {"index": 3, "actuator": "VALVE-177", "lower": 20.0, "upper": 90.0, "unit": "psi"},
                    {"index": 4, "actuator": "VALVE-178", "lower": 20.0, "upper": 74.0, "unit": "psi"},
                    {"index": 5, "actuator": "PUMP-170", "lower": 0.82, "upper": 1.10, "unit": "rel_speed"},
                    {"index": 6, "actuator": "PUMP-172", "lower": 0.77, "upper": 1.10, "unit": "rel_speed"},
                ],
                "excluded_valves_kept_in_model": ["VALVE-174", "VALVE-179", "VALVE-180"],
                "pump_strategy": "SPEED only, re-issued each step; native STATUS rules intact",
            },
            "observation": {
                "decision": "D-P6-004 APPROVED & FROZEN",
                "observation_dim": state_spec.get("observation_dim", 139),
                "dtype": state_spec.get("dtype", "float32"),
                "reward_must_not_modify_state": True,
            },
            "service_node_policy": {
                "n_service_junctions": 121,
                "n_connector_junctions_excluded": 5,
                "connector_nodes": ["JUNCTION-105", "JUNCTION-106", "JUNCTION-109",
                                    "JUNCTION-110", "JUNCTION-128"],
            },
            "solver_policy": wu10.get("experiment_metadata", {}).get("solver_policy",
                                                                     wu9["integrity"]["solver_policy"]),
        },
        "normalization_constants_frozen": consts,
        "normalization_constants_match_across_artifacts": const_match,
        "candidate_formulations": wu10["formulations"],
        "decision_dimensions": decision_dimensions(),
        "quantitative_evidence": {
            "pooled_component_stats": wu9["pooled_component_stats"],
            "cross_component_correlation": wu9["cross_component_correlation"],
            "pathology_checks_wu9": wu9["pathology_checks"],
            "pathology_results_wu10": wu10["pathology_results"],
            "induced_incentive_per_formulation": wu10["induced_incentive_per_formulation"],
            "pooled_reward_statistics": wu10["pooled_statistics"],
            "temporal_reward_statistics": wu10["temporal_statistics"],
            "actuator_effort_analytic": wu10["actuator_effort_analytic"],
            "tested_configurations": list(wu10["per_configuration_metrics"].keys()),
            "n_tested_configs": len(wu10["per_configuration_metrics"]),
        },
        "chronic_baseline_service_issue": chronic_baseline_service_issue(wu10),
        "candidate_parameterizations": candidate_parameterizations(consts),
        "sensitivity_results": {
            "source": "WU-10 sensitivity_results (deterministic parameter sweeps; no re-run)",
            "note": (
                "Low/central/high parameter sweeps already on disk. These indicate INCENTIVE "
                "DIRECTION (argmax config), NOT a formulation ranking or score."
            ),
            "sweeps": wu10["sensitivity_results"],
            "analytic_effort_weight_reading": {
                "parameter": "w_A (movement weight, F1 family, candidates C-A/C-B)",
                "low": {"w_A": 0.0, "effect": "no smoothness pressure; realised movement unconstrained"},
                "central": {"w_A": 0.1, "effect": "max-move step (~1.0) ~ leak-term range (~0.108)"},
                "high": {"w_A": 1.0, "effect": "one max-move step (1.0) dominates the leak signal (~0.108)"},
                "basis": "ANALYTIC (static runs have 0 movement); realised effort is a training HYPOTHESIS",
            },
        },
        "safety_dependencies": {
            "reward_level_D_P6_005": (
                "Dense/relative service and pressure terms SHAPE behaviour but do NOT guarantee "
                "any pressure bound."
            ),
            "execution_level_STEP_9": (
                "A state-dependent safety clamp to the APPROVED action bounds is REQUIRED to "
                "enforce feasibility; WU-9/WU-10 boundary-seeking checks show the leak optimum "
                "sits on the PRV lower corner. STEP-9 is a SEPARATE decision, not part of "
                "D-P6-005, and is NOT implemented here."
            ),
            "separation_of_concerns": (
                "action bounds (frozen) != reward shaping (D-P6-005) != safety clamp (STEP-9)."
            ),
        },
        "constraints": {
            "no_hard_20psi_reward_term": "ill-posed on native baseline (see chronic_baseline_service_issue)",
            "effort_uses_commanded_action": True,
            "fixed_normalisation_no_running_stats": True,
            "no_future_information": bool(repro.get("no_future_information_used", True)) if repro else True,
        },
        "uncertainties": [
            "Realised actuator-movement distribution is unknown (static runs = 0 movement); "
            "effort scale is analytic -> HYPOTHESIS until a policy trajectory exists.",
            "Leakage is a VALIDATION instrument, not field-calibrated; only RELATIVE response is meaningful.",
            "Joint 5-D in-box safety is characterised at a single lower corner only; interior/mixed "
            "corners are a STEP-9/STEP-12 job.",
            "Reward weights / LAMBDA / thresholds set leakage<->service exchange rates that are "
            "value judgements for the researcher, not measured quantities.",
            "Pump power is HYDRAULIC only (no efficiency curve); energy term optional.",
        ],
        "reproducibility_information": repro,
        "researcher_selection": None,
    }
    return brief


def _self_checks(brief: dict) -> dict:
    checks = {}
    checks["status_is_proposed"] = brief["status"] == STATUS
    checks["researcher_selection_is_null"] = brief["researcher_selection"] is None
    checks["constants_match_across_artifacts"] = all(
        brief["normalization_constants_match_across_artifacts"].values())
    checks["all_values_finite"] = _all_finite(brief)
    checks["observation_dim_139"] = brief["frozen_constraints"]["observation"]["observation_dim"] == 139
    checks["action_dim_7"] = brief["frozen_constraints"]["action_space"]["action_dim"] == 7
    order = [b["actuator"] for b in brief["frozen_constraints"]["action_space"]["ordered_bounds"]]
    checks["action_ordering_unchanged"] = order == [
        "VALVE-173", "VALVE-175", "VALVE-176", "VALVE-177", "VALVE-178", "PUMP-170", "PUMP-172"]
    checks["service_mask_121_5"] = (
        brief["frozen_constraints"]["service_node_policy"]["n_service_junctions"] == 121
        and brief["frozen_constraints"]["service_node_policy"]["n_connector_junctions_excluded"] == 5)
    checks["all_candidates_not_approved"] = all(
        c["status"] == NOT_APPROVED for c in brief["candidate_parameterizations"])
    checks["n_candidates_between_2_and_4"] = 2 <= len(brief["candidate_parameterizations"]) <= 4
    checks["no_winner_key"] = not any(
        k in brief for k in ("winner", "selected_formulation", "ranking", "scores", "best"))
    return checks


def main() -> None:
    brief = build_brief()
    checks = _self_checks(brief)
    brief["self_checks"] = checks
    failed = [k for k, v in checks.items() if not v]
    if failed:
        raise SystemExit(f"D-P6-005 brief self-checks FAILED: {failed}")
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(brief, fh, indent=2, ensure_ascii=True)
    print(f"wrote {OUT_PATH}")
    print("self_checks:", json.dumps(checks, indent=1))


if __name__ == "__main__":
    main()


