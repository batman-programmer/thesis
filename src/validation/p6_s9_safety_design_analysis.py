#!/usr/bin/env python3
"""WU-14 - STEP 9 state-dependent safety-mechanism DESIGN ANALYSIS.

PURE aggregator over the WU-11 decision brief
(results/phase6/p6_d_p6_005_decision_brief.json). This script:

  * measures NOTHING new (no EPANET, no PPO, no RNG, no re-run);
  * copies every numeric value verbatim from the decision brief, so the
    analysis cannot drift from the measured evidence;
  * CHARACTERISES four candidate state-dependent safety mechanisms (S1-S4) on a
    FIXED schema. It does NOT rank, score, select, prefer, or declare a winner
    among them; mechanism selection is a later researcher decision (DEFERRED);
  * records the APPROVED D-P6-005 reward (C-A_F1_balanced_dense) as a
    machine-readable block and checks it against the frozen C-A parameterisation
    in the brief (anti-drift);
  * does NOT implement any production safety wrapper (that is STEP 9's
    implementation step, deliberately out of scope here).

The state-dependent safety mechanism is DISTINCT from the frozen action-space
bounds (D-P6-001/002/003): the bounds keep each actuator inside a static box,
whereas a STEP-9 mechanism reacts to the resulting hydraulic STATE.

Deterministic: re-running byte-reproduces
results/phase6/p6_s9_safety_design_analysis.json.

AUTHORED content = plain descriptive notes per schema field and the
baseline-compatibility / action-space-coverage verdicts; it adds no new numbers.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "phase6"
BRIEF = RESULTS / "p6_d_p6_005_decision_brief.json"
OUT = RESULTS / "p6_s9_safety_design_analysis.json"

FORBIDDEN_KEY_TOKENS = ("winner", "rank", "tier", "score", "best",
                        "superior", "optimal", "preferred", "recommend")

# Fixed reporting schema applied to EVERY candidate (no evaluative/ordering key).
SCHEMA_FIELDS = (
    "exact_rule",
    "information_required",
    "compute_cost",
    "baseline_compatibility",
    "false_positive_risk",
    "false_negative_risk",
    "ppo_compatibility",
    "interval_30min_compatibility",
    "requires_look_ahead",
    "preserves_determinism",
)
# ---------------------------------------------------------------------------
# AUTHORED characterisation of the four candidate mechanisms. Enumeration order
# S1..S4 is DEFINITIONAL, not evaluative. Exact measured numbers are NOT
# interpolated here (they live verbatim in evidence_loaded); prose uses "~".
# ---------------------------------------------------------------------------
SAFETY_CANDIDATES = [
    {
        "candidate_id": "S1",
        "name": "absolute_worst_node_pressure_threshold",
        "mechanism_class": "absolute state threshold on worst-node service pressure",
        "exact_rule": ("Intervene (clip toward a safer action, or reject) when the worst-node "
                       "service pressure of the candidate action falls below an absolute "
                       "threshold T_abs: min_i p_i(a_t) < T_abs. The natural target is "
                       "T_abs = 20 psi (the PDA required pressure)."),
        "information_required": ("Post-action minimum service pressure over the 121 service "
                                 "junctions, i.e. a hydraulic evaluation of the candidate action."),
        "compute_cost": ("One extra EPANET hydraulic solve per control step to obtain "
                         "min_i p_i(a_t) (a one-step look-ahead), then an O(121) min-reduction; "
                         "roughly 1x the step's own solve cost."),
        "baseline_compatibility": ("INCOMPATIBLE at T_abs=20 psi: the frozen native baseline "
                                   "holds min service pressure ~4.16 psi and frac_ts_any_node_"
                                   "below_20psi = 1.0 (386 node-timesteps < 20 psi), so a hard "
                                   "20-psi rule flags the baseline itself at every timestep. "
                                   "Only compatible if T_abs is set strictly below the baseline "
                                   "worst-node (~4.16 psi), which then no longer enforces 20 psi."),
        "false_positive_risk": ("HIGH at T_abs=20 psi: rejects physically-normal, baseline-like "
                                "states the native controller already produces. Decreases as "
                                "T_abs -> baseline worst-node."),
        "false_negative_risk": ("LOW at T_abs=20 psi (little escapes a strict absolute floor); "
                                "rises as T_abs is lowered toward 0."),
        "ppo_compatibility": ("Clip variant projects the commanded action into a state-dependent "
                              "safe set and keeps a valid continuous action; executed != commanded, "
                              "and since the approved reward's effort term uses the COMMANDED da, "
                              "that term is unaffected, but the policy sees a train/execute gap. "
                              "Reject/resample perturbs the action->transition map and is harder "
                              "for PPO."),
        "interval_30min_compatibility": ("Compatible: evaluated once per 1800 s (30-min) control "
                                         "decision."),
        "requires_look_ahead": ("YES when enforced on the post-action state (needs a candidate-"
                                "action solve); avoidable only by reacting one step late on the "
                                "realised state."),
        "preserves_determinism": "YES - EPANET is deterministic; no RNG.",
    },
    {
        "candidate_id": "S2",
        "name": "min_pressure_degradation_vs_current",
        "mechanism_class": "relative worst-node degradation vs current state",
        "exact_rule": ("Intervene when the candidate action degrades the worst-node service "
                       "pressure relative to the CURRENT (pre-action) state beyond a tolerance: "
                       "min_i p_i(a_t) < min_i p_i(current) - tol. A stricter variant demands "
                       "non-degradation (tol=0) or a minimum improvement."),
        "information_required": ("Current-state worst-node pressure (already derivable from the "
                                 "observation pressures) AND the candidate-action worst-node "
                                 "pressure (look-ahead)."),
        "compute_cost": ("One look-ahead solve for the candidate action; current-state pressures "
                         "are reused from the last solve. O(121) reduction."),
        "baseline_compatibility": ("COMPATIBLE in principle: being relative, it does not reject "
                                   "the chronically sub-20 baseline outright, and never fires on a "
                                   "hold that leaves pressures unchanged. Behaviour depends on the "
                                   "reference ('current' state) and the tolerance, which must be "
                                   "defined."),
        "false_positive_risk": ("MODERATE: benign transient dips or demand-driven drops can trip "
                                "a tol=0 rule even when the commanded action is sound; sensitive "
                                "to tol."),
        "false_negative_risk": ("MODERATE-HIGH: a state already far below 20 psi that stays flat "
                                "(no further degradation) is NOT flagged, so this rule does not "
                                "enforce any absolute floor."),
        "ppo_compatibility": ("Same clip-vs-reject trade-off as S1; the relative signal is smooth "
                              "in the pressures, so a clip projection is PPO-friendly."),
        "interval_30min_compatibility": "Compatible: one evaluation per 1800 s control decision.",
        "requires_look_ahead": ("YES for the candidate-action term; the current-state term needs "
                                "no extra solve."),
        "preserves_determinism": "YES - deterministic solver; no RNG.",
    },
    {
        "candidate_id": "S3",
        "name": "total_pressure_deficit_increase",
        "mechanism_class": "relative aggregate pressure-deficit increase vs current state",
        "exact_rule": ("Intervene when the candidate action increases the total nodal pressure "
                       "deficit sum_i max(0, 20 - p_i) over service nodes relative to the current "
                       "state beyond a tolerance: deficit(a_t) > deficit(current) + tol."),
        "information_required": ("Current and candidate-action pressure-deficit (nodesum over the "
                                 "121 service nodes)."),
        "compute_cost": ("One look-ahead solve; deficit is an O(121) sum. deficit_ref (~28.67) is "
                         "available for normalisation."),
        "baseline_compatibility": ("COMPATIBLE: relative and aggregate; it does not reject the "
                                   "baseline. Measured deficit<->leak correlation is -0.7735, so "
                                   "leak-reducing (pressure-lowering) actions tend to RAISE "
                                   "deficit; S3 therefore directly opposes the approved reward's "
                                   "leak term as an aggregate guard (not a worst-node guarantee)."),
        "false_positive_risk": ("MODERATE: an action that improves the worst node but slightly "
                                "raises aggregate deficit elsewhere is flagged."),
        "false_negative_risk": ("HIGH for localised failures: aggregate deficit can stay flat "
                                "while a single critical node collapses (aggregation masks the "
                                "worst node)."),
        "ppo_compatibility": ("Smooth aggregate signal; clip projection PPO-friendly. Same "
                              "clip-vs-reject train/execute considerations as S1/S2."),
        "interval_30min_compatibility": "Compatible: one evaluation per 1800 s control decision.",
        "requires_look_ahead": "YES for the candidate-action deficit; current-state deficit reused.",
        "preserves_determinism": "YES - deterministic solver; no RNG.",
    },
    {
        "candidate_id": "S4",
        "name": "negative_pressure_hard_backstop",
        "mechanism_class": "absolute hard gate on non-positive pressure (feasibility backstop)",
        "exact_rule": ("Intervene (hard) only when any service node goes non-positive: "
                       "min_i p_i(a_t) <= 0 (equivalently n_negative(a_t) > 0). This is the only "
                       "HARD absolute gate that is well-posed on this network."),
        "information_required": ("Candidate-action minimum service pressure / count of "
                                 "negative-pressure nodes."),
        "compute_cost": ("One look-ahead solve and an O(121) check; the same solve can also feed "
                         "S1-S3."),
        "baseline_compatibility": ("FULLY COMPATIBLE: the baseline has 0 negative-pressure "
                                   "node-timesteps (frac_ts_any_node_negative = 0.0), and every "
                                   "in-bounds swept configuration - including the leak-only lower "
                                   "corner whose worst node is ~1.29 psi - had 0 negative nodes. "
                                   "So as a STANDALONE gate S4 never fires on the measured "
                                   "evidence and provides NO 20-psi service protection."),
        "false_positive_risk": ("VERY LOW: fires only on physically infeasible (non-positive) "
                                "pressure."),
        "false_negative_risk": ("VERY HIGH w.r.t. the 20-psi service target: it permits the whole "
                                "0-20 psi band, including the ~1.29 psi leak-only corner. It is a "
                                "feasibility backstop, not a service-level guarantee."),
        "ppo_compatibility": ("Rarely active, so it barely perturbs the action->transition map; "
                              "usable as a hard clip of last resort. Complementary to (not a "
                              "substitute for) a dense/relative guard."),
        "interval_30min_compatibility": "Compatible: one evaluation per 1800 s control decision.",
        "requires_look_ahead": ("YES when enforced on the post-action state; a reactive variant "
                                "acts one step late."),
        "preserves_determinism": "YES - deterministic solver; no RNG.",
    },
]

# ---------------------------------------------------------------------------
# AUTHORED cross-cutting design investigation (STEP-9 sec.7-sec.10). Descriptive
# only; no ranking, no selection.
# ---------------------------------------------------------------------------
DESIGN_INVESTIGATION = {
    "distinct_from_action_bounds": ("A STEP-9 state-dependent mechanism is SEPARATE from the "
                                    "frozen action bounds (D-P6-001/002/003): the bounds keep "
                                    "each actuator in a static box; the mechanism reacts to the "
                                    "resulting hydraulic STATE. Both differ from reward shaping "
                                    "(D-P6-005)."),
    "one_step_look_ahead": ("Every post-action rule (S1-S4 evaluated on the resulting state) "
                            "needs either (a) one extra EPANET solve of the candidate action "
                            "before committing (a one-step look-ahead, ~1x solver cost per "
                            "control step), or (b) reactive enforcement one step late on the "
                            "realised state. EPANET is deterministic, so a look-ahead adds no "
                            "stochasticity."),
    "clip_vs_reject": ("CLIP projects the commanded action into a state-dependent safe set and "
                       "keeps a valid continuous action (executed != commanded; the approved "
                       "reward's effort term uses the COMMANDED da, so it stays intact, but PPO "
                       "must observe the train/execute gap). REJECT/RESAMPLE breaks the "
                       "deterministic action->state map and raises return variance. Characterised, "
                       "not selected."),
    "fallback_when_no_feasible_action": ("A guard needs a defined fallback when no in-box action "
                                         "satisfies it. Because the native baseline is itself "
                                         "sub-20 psi at every timestep, an absolute-20 guard has "
                                         "NO feasible fallback - reinforcing that an enforced "
                                         "20-psi guarantee is ill-posed at both reward and naive-"
                                         "clamp level. A relative guard (S2/S3) or a "
                                         "negative-keyed hard gate (S4) always has the current "
                                         "state as a feasible fallback."),
    "degradation_reference_choice": ("The reference matters: 'current state' (S2/S3) vs 'native "
                                     "baseline' (F3/C-C accounting) vs a fixed absolute 20 psi "
                                     "(S1). Relative and baseline-referenced guards are "
                                     "well-posed here; the fixed-absolute-20 guard is not."),
    "worst_node_vs_aggregate": ("Worst-node signals (S1/S2) protect the single most critical "
                                "junction; aggregate deficit (S3) can mask a localised collapse. "
                                "A composite guard could combine them, but that is a design "
                                "choice for the researcher, not made here."),
    "negative_pressure_protection": ("Negative pressure is the only absolute condition that never "
                                     "occurs in the baseline or in any swept in-bounds config "
                                     "(n_service_nodes_negative pooled mean/max = 0). A hard gate "
                                     "keyed on it (S4) is well-posed but, alone, guarantees only "
                                     "feasibility, not the 20-psi service target."),
}

ACTION_SPACE_COVERAGE = {
    "characterised_region": ("Only the single lower corner (prv_lower_pump_lower / prv_all_lower) "
                             "has measured worst-node service pressure (~1.29 psi at the leak-only "
                             "argmax; ~4.19 psi for the all-lower PRV corner) and a measured "
                             "negative-node count (0). This is the R1b single-corner coverage."),
    "unverified_region": ("Interior points, mixed PRV corners, pump-speed extremes combined with "
                          "PRV extremes, and the joint (action x uncertain-demand) space are NOT "
                          "characterised here."),
    "claim_limit": ("Do NOT claim the 7-D action box is globally safe. Exhaustive joint in-box "
                    "safety is a STEP-9 (mechanism) + STEP-12 (test) responsibility; this analysis "
                    "characterises candidate mechanisms, it does not certify the action space."),
}
def _iter_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _iter_keys(v)
    elif isinstance(obj, list):
        for x in obj:
            yield from _iter_keys(x)


def _all_finite(obj):
    if isinstance(obj, bool) or obj is None or isinstance(obj, str):
        return True
    if isinstance(obj, (int, float)):
        return math.isfinite(obj)
    if isinstance(obj, dict):
        return all(_all_finite(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return all(_all_finite(x) for x in obj)
    return True


def _load_brief():
    with BRIEF.open(encoding="utf-8") as fh:
        return json.load(fh)


def _find_ca(brief):
    for c in brief["candidate_parameterizations"]:
        if c["candidate_id"] == "C-A_F1_balanced_dense":
            return c
    raise SystemExit("C-A_F1_balanced_dense not found in decision brief")
def build_analysis(brief):
    """Aggregate the WU-11 brief into the STEP-9 safety-design characterisation."""
    ca = _find_ca(brief)
    qe = brief["quantitative_evidence"]
    pooled = qe["pooled_component_stats"]
    chronic = brief["chronic_baseline_service_issue"]

    d_p6_005_decision = {
        "decision_id": brief["decision_id"],
        "status": "APPROVED",
        "approved_utc": "2026-09-27",
        "selection_authority": "researcher (not AI); this artefact only RECORDS the decision",
        "selected_candidate": ca["candidate_id"],
        "formulation": ca["base_formulation"],
        "equation": ca["equation"],
        "weights": ca["provisional_weights"],
        "frozen_normalization_constants": ca["constants"],
        "consistency_with_frozen_brief": ("equation, weights and constants copied verbatim from "
                                          "candidate_parameterizations[C-A_F1_balanced_dense] in "
                                          "the WU-11 brief; no value altered (no repository "
                                          "contradiction found)."),
        "evidence_preservation_note": ("the WU-11 decision brief and WU-12 researcher summary JSONs "
                                       "remain PROPOSED / researcher_selection=null as frozen "
                                       "pre-decision evidence; the APPROVED record lives in "
                                       "PROJECT_STATE.yaml, PHASE6_DECISION_REGISTER.md and this "
                                       "STEP-9 artefact."),
        "scope": ("approval is specific to this thesis DRL environment design; it is NOT a "
                  "universal claim and does NOT order the candidate formulations by quality."),
        "reward_py_status": "NOT implemented here (reward.py is STEP 11).",
    }

    per_candidate_baseline_flag = {
        "S1": ("FLAGS the native baseline at every timestep when T_abs=20 psi (baseline worst node "
               "~4.16 psi); compatible only when T_abs < baseline worst-node."),
        "S2": "Does NOT flag the baseline (relative to the current state).",
        "S3": "Does NOT flag the baseline (relative aggregate deficit).",
        "S4": "Never fires on the baseline (0 negative-pressure node-timesteps).",
    }
    analysis = {
        "phase": "Phase 6 - DRL environment design/validation",
        "step": "STEP 9 - state-dependent safety mechanism",
        "work_unit": "WU-14",
        "title": "State-dependent safety-mechanism DESIGN ANALYSIS (characterisation only)",
        "status": ("DESIGN ANALYSIS - four candidate mechanisms characterised on a fixed schema; "
                   "NO mechanism selected, scored or ordered by quality; NO production wrapper "
                   "implemented; NO reward.py; NO PPO."),
        "generated_by": "src/validation/p6_s9_safety_design_analysis.py",
        "measures_nothing_new": True,
        "no_epanet_no_ppo_no_selection": True,
        "no_production_wrapper_implemented": True,
        "source_artifact": "results/phase6/p6_d_p6_005_decision_brief.json",
        "d_p6_005_decision": d_p6_005_decision,
        "safety_layer_separation": brief["safety_dependencies"],
        "distinct_from_action_bounds": DESIGN_INVESTIGATION["distinct_from_action_bounds"],
        "frozen_constraints_snapshot": brief["frozen_constraints"],
        "normalization_constants_frozen": brief["normalization_constants_frozen"],
        "evidence_loaded": {
            "chronic_baseline_service_issue": chronic,
            "min_service_pressure_psi_pooled": pooled["min_service_pressure_psi"],
            "n_service_nodes_negative_pooled": pooled["n_service_nodes_negative"],
            "pressure_deficit_psi_nodesum_pooled": pooled["pressure_deficit_psi_nodesum"],
            "n_service_nodes_below_20psi_pooled": pooled["n_service_nodes_below_20psi"],
            "leak_only_argmax": qe["pathology_results_wu10"]["A_leakage_only_collapses_service"],
            "boundary_seeking_safety": qe["pathology_checks_wu9"]["boundary_seeking_safety"],
            "cross_component_correlation": qe["cross_component_correlation"],
            "threshold_handling_options": chronic["threshold_handling_options"],
        },
        "schema_fields": list(SCHEMA_FIELDS),
        "safety_candidates": SAFETY_CANDIDATES,
        "safety_candidate_selection": {
            "status": ("DEFERRED - a separate researcher decision (STEP-9); no candidate is "
                       "selected, scored, or ordered by quality in this analysis."),
            "characterisation_only": True,
            "enumeration_order_is_definitional": True,
            "authority": "researcher (not AI)",
        },
        "design_investigation": DESIGN_INVESTIGATION,
        "baseline_compatibility_summary": {
            "governing_conclusion": chronic["conclusion"],
            "per_candidate_baseline_flag": per_candidate_baseline_flag,
            "naive_absolute_20psi_reject_is_ill_posed": True,
        },
        "action_space_coverage": ACTION_SPACE_COVERAGE,
        "reproducibility": {
            "working_inp_sha256": brief["reproducibility_information"]["working_inp_sha256"],
            "deterministic": brief["reproducibility_information"]["deterministic"],
            "no_topology_or_native_rule_change":
                brief["reproducibility_information"]["no_topology_or_native_rule_change"],
            "no_future_information_used":
                brief["reproducibility_information"]["no_future_information_used"],
            "native_controls_count": brief["reproducibility_information"]["native_controls_count"],
            "no_new_measurement": True,
            "source_brief": "results/phase6/p6_d_p6_005_decision_brief.json",
        },
        "researcher_action_required": ("Select (or compose) a STEP-9 state-dependent safety "
                                       "mechanism from S1-S4, its threshold/tolerance and its "
                                       "clip-vs-reject handling, then implement + test the "
                                       "production wrapper. None of that is done here."),
    }
    analysis["self_checks"] = _self_checks(analysis, brief)
    return analysis
def _self_checks(analysis, brief):
    ca = _find_ca(brief)
    d = analysis["d_p6_005_decision"]
    fc = analysis["frozen_constraints_snapshot"]
    cands = analysis["safety_candidates"]
    forbidden = [k for k in _iter_keys(analysis)
                 if any(tok in k.lower() for tok in FORBIDDEN_KEY_TOKENS)]
    expected_keys = {"candidate_id", "name", "mechanism_class", *SCHEMA_FIELDS}
    cand_schema_ok = all(set(c.keys()) == expected_keys for c in cands)
    pol = fc["service_node_policy"]
    return {
        "d_p6_005_status_approved": d["status"] == "APPROVED",
        "d_p6_005_selected_C_A": d["selected_candidate"] == "C-A_F1_balanced_dense",
        "d_p6_005_equation_matches_brief": d["equation"] == ca["equation"],
        "d_p6_005_weights_match_brief": d["weights"] == ca["provisional_weights"],
        "d_p6_005_constants_match_brief": d["frozen_normalization_constants"] == ca["constants"],
        "n_safety_candidates_4": len(cands) == 4,
        "candidate_ids_S1_to_S4": [c["candidate_id"] for c in cands] == ["S1", "S2", "S3", "S4"],
        "candidates_have_fixed_schema": cand_schema_ok,
        "selection_deferred": analysis["safety_candidate_selection"]["status"].startswith("DEFERRED"),
        "no_forbidden_key_tokens": not forbidden,
        "action_dim_7": fc["action_space"]["action_dim"] == 7,
        "observation_dim_139": fc["observation"]["observation_dim"] == 139,
        "service_mask_121_5": (pol["n_service_junctions"] == 121
                               and pol["n_connector_junctions_excluded"] == 5),
        "constants_match_brief": (analysis["normalization_constants_frozen"]
                                  == brief["normalization_constants_frozen"]),
        "chronic_baseline_metrics_match_brief": (
            analysis["evidence_loaded"]["chronic_baseline_service_issue"]["baseline_metrics"]
            == brief["chronic_baseline_service_issue"]["baseline_metrics"]),
        "no_topology_or_native_rule_change":
            analysis["reproducibility"]["no_topology_or_native_rule_change"],
        "all_values_finite": _all_finite(analysis),
    }


def main():
    brief = _load_brief()
    analysis = build_analysis(brief)
    failed = [k for k, v in analysis["self_checks"].items() if not v]
    if failed:
        raise SystemExit(f"self-checks failed: {failed}")
    text = json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT} ({len(text)} bytes); self_checks all pass")


if __name__ == "__main__":
    main()
