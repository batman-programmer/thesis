#!/usr/bin/env python3
"""STEP-9 FINAL safety-architecture DECISION REVIEW - evidence aggregator (WU-18).

PURPOSE
-------
This is the final scientific REVIEW that precedes production safety-wrapper
implementation. It re-loads the ALREADY-FROZEN STEP-9 evidence

  * WU-14  results/phase6/p6_s9_safety_design_analysis.json           (design analysis)
  * WU-15  results/phase6/p6_s9_safety_mechanism_characterization.json (empirical)
  * WU-16  results/phase6/p6_s9_temporal_safety_characterization.json  (temporal)
  * WU-17  results/phase6/p6_s9_decision_brief.json                    (decision brief)
  * WU-11  results/phase6/p6_d_p6_005_decision_brief.json             (frozen reward)

and consolidates it into ONE review that judges whether the STEP-9 decision is
DECISION-READY and packages the (<=3) implementable final PROVISIONAL designs -
WITHOUT selecting a mechanism, threshold, horizon, or handling policy.

Binding constraints honoured (STEP-9 FINAL DECISION REVIEW):
  * MEASURES NOTHING NEW: no EPANET, no PPO, no RNG, no generated_utc.
  * does NOT implement the wrapper / reward.py; does NOT modify env, reward,
    action bounds, observation, topology, or native EPANET rules.
  * does NOT select / rank / score / declare a winner among mechanisms,
    thresholds, horizons, or handling policies; the final designs are NOT ordered
    by quality; researcher_selection is null.
  * does NOT invent a threshold: every threshold is a swept provisional-grid value,
    an evidence-supported gate, or explicitly "THRESHOLD NOT YET EMPIRICALLY JUSTIFIED".
  * STEP-9 final mechanism stays PROPOSED / PENDING RESEARCHER; no D-P6-006 minted.

ACCURACY CORRECTION (surfaced, not silent): the WU-17 brief wording said the
delayed-collapse crossover onset is "NOT persisted as a per-index p_min series"
and is "UNTESTED". The WU-16 artefact DOES persist the full per-report-index
worst-node series (delayed_collapse_case.series.p_min_psi) and pins the theta_p=5
crossover at report index 13 (6.5 h) in first_report_index_below_theta_p. This
review reports the persisted crossover and narrows the residual gap accordingly.

Byte-reproducible: pure re-shaping of on-disk evidence; running it twice yields
identical bytes.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "phase6"
WU14_PATH = RESULTS / "p6_s9_safety_design_analysis.json"
WU15_PATH = RESULTS / "p6_s9_safety_mechanism_characterization.json"
WU16_PATH = RESULTS / "p6_s9_temporal_safety_characterization.json"
WU17_PATH = RESULTS / "p6_s9_decision_brief.json"
WU11_PATH = RESULTS / "p6_d_p6_005_decision_brief.json"
OUT_PATH = RESULTS / "p6_s9_final_decision_review.json"

DECISION_ID = "STEP9_SAFETY_MECHANISM_FINAL_REVIEW"
STATUS = "PROPOSED / PENDING RESEARCHER"
NOT_APPROVED = "PROVISIONAL - NOT APPROVED"
READINESS = "DECISION-READY"
NOT_READY = "NOT-YET-DECISION-READY"
THRESH_UNJUSTIFIED = "THRESHOLD NOT YET EMPIRICALLY JUSTIFIED"

# Scanned over KEYS only (same convention as WU-16/WU-17: source disclaimers legitimately
# contain these tokens inside negations such as "no ranking/scoring"; a value scan would
# be self-defeating). "select"/"selection"/"worst"/"readiness" are NOT forbidden.
FORBIDDEN_KEY_TOKENS = ("winner", "rank", "tier", "score", "best",
                        "superior", "optimal", "preferred", "recommend")


# ---------------------------------------------------------------------------
# loaders / small numeric helpers (mirror WU-17 exactly; no new measurement)
# ---------------------------------------------------------------------------
def _load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _finite(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x))


def _all_finite(obj) -> bool:
    """Recursively assert every numeric leaf is finite (no NaN, no +/-inf)."""
    if isinstance(obj, dict):
        return all(_all_finite(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return all(_all_finite(v) for v in obj)
    if isinstance(obj, bool):
        return True
    if isinstance(obj, (int, float)):
        return math.isfinite(float(obj))
    return True  # str / None


def _iter_keys(obj):
    """Yield every dict key appearing anywhere in a nested structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _iter_keys(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _iter_keys(v)


def _has_forbidden_key(obj) -> str | None:
    for k in _iter_keys(obj):
        low = str(k).lower()
        for tok in FORBIDDEN_KEY_TOKENS:
            if tok in low:
                return f"{k} (token '{tok}')"
    return None


def _close(x, target, tol=1e-9) -> bool:
    return _finite(x) and abs(float(x) - float(target)) <= tol


# ---------------------------------------------------------------------------
# 1/13 decision_context
# ---------------------------------------------------------------------------
def build_decision_context(wu17: dict) -> dict:
    return {
        "decision_id": DECISION_ID,
        "status": STATUS,
        "title": "STEP-9 safety-architecture FINAL decision review (WU-18)",
        "generated_by": "src/validation/p6_s9_final_decision_review.py (WU-18)",
        "role": ("Final scientific REVIEW immediately preceding production "
                 "safety-wrapper implementation. It judges whether the STEP-9 "
                 "safety-architecture decision is DECISION-READY and packages the "
                 "implementable final PROVISIONAL designs WITHOUT making the "
                 "decision."),
        "measures_nothing_new": True,
        "no_epanet_no_ppo_no_rng": True,
        "no_production_wrapper_implemented": True,
        "does_not_select_or_order_designs": True,
        "final_mechanism_state": "PROPOSED / PENDING RESEARCHER (no D-P6-006 minted)",
        "the_four_open_decisions": [
            "A_safety_metric_rule (S1/S2/S3/S4 or temporal TS1-TS4; NOT selected)",
            "B_threshold_tolerance (theta_p / eps_p / eps_D grids; NOT selected)",
            "C_look_ahead_horizon (H control steps; NOT selected)",
            "D_action_handling_policy (H1 reject / H2 clip / H3 fallback; NOT selected)",
        ],
        "researcher_is_final_authority": True,
        "builds_on": {
            "wu17_decision_brief_decision_id": wu17.get("decision_id"),
            "wu17_status": wu17.get("status"),
        },
        "accuracy_correction_vs_wu17": {
            "surfaced_not_silent": True,
            "wu17_wording": ("WU-17 horizon_analysis.crossover_interval_untested "
                             "stated the delayed-collapse onset is 'NOT persisted as a "
                             "per-index p_min series' and that intermediate horizons are "
                             "'UNTESTED'."),
            "disk_evidence": ("WU-16 delayed_collapse_case.series.p_min_psi persists the "
                              "full 193-point per-report-index worst-node series, and "
                              "delayed_collapse_case.horizon_pmin_sweep."
                              "first_report_index_below_theta_p pins the theta_p=5 psi "
                              "crossover at report_index=13 (6.5 h)."),
            "correction": ("This review reports the PERSISTED crossover onset (H=13 "
                           "control steps / 6.5 h for theta_p=5 on the severe "
                           "prv_lower_pump_lower corner). The residual genuine gap is "
                           "narrower than WU-17 implied: only the temporal RULE-ACTIVATION "
                           "booleans were tabulated at coarse H in {1,2,4,8,192}; "
                           "intermediate thresholds 5<theta_p<10 and non-severe action "
                           "corners are not swept, though computable from the persisted "
                           "series without new EPANET runs."),
            "policy_basis": "CLAUDE.md sections 1/7/21 + TRUST-DISK; disk overrides prior wording.",
        },
    }


# ---------------------------------------------------------------------------
# 2/13 frozen_invariants  (copied VERBATIM from WU-17; nothing re-derived)
# ---------------------------------------------------------------------------
def build_frozen_invariants(wu17: dict) -> dict:
    return {
        "note": ("Copied verbatim from the WU-17 brief. STEP-9 is an EXECUTION-LEVEL "
                 "admissibility layer and MUST NOT modify any of these frozen items."),
        "action_space": wu17["frozen_constraints"]["action_space"],
        "observation": wu17["frozen_constraints"]["observation"],
        "service_node_policy": wu17["frozen_constraints"]["service_node_policy"],
        "solver_policy": wu17["frozen_constraints"]["solver_policy"],
        "frozen_reward_D_P6_005": wu17["frozen_reward_D_P6_005"],
        "normalization_constants_frozen": wu17["normalization_constants_frozen"],
        "step9_must_not_modify": [
            "reward (D-P6-005 C-A_F1_balanced_dense)",
            "observation (D-P6-004, dim 139)",
            "action bounds / order / encoding (D-P6-001/002/003)",
            "network topology / native EPANET STATUS & rule logic",
        ],
    }


# ---------------------------------------------------------------------------
# 3/13 evidence  (source artefacts + central anchors, pulled verbatim)
# ---------------------------------------------------------------------------
def build_evidence(wu14: dict, wu15: dict, wu16: dict, wu17: dict, wu11: dict) -> dict:
    tm = wu16["trajectory_metrics"]
    dcc = wu16["delayed_collapse_case"]
    sweep = dcc["horizon_pmin_sweep"]
    return {
        "source_artifacts": {
            "WU14_design_analysis": "results/phase6/p6_s9_safety_design_analysis.json",
            "WU15_mechanism_characterization": "results/phase6/p6_s9_safety_mechanism_characterization.json",
            "WU16_temporal_characterization": "results/phase6/p6_s9_temporal_safety_characterization.json",
            "WU17_decision_brief": "results/phase6/p6_s9_decision_brief.json",
            "WU11_frozen_reward_brief": "results/phase6/p6_d_p6_005_decision_brief.json",
        },
        "source_ids": {
            "wu17_decision_id": wu17.get("decision_id"),
            "wu11_decision_id": wu11.get("decision_id"),
        },
        "central_anchors": {
            "baseline_worst_node_p_min_psi": tm["reference_nominal"]["p_min_horizon_psi"],
            "baseline_worst_node_report_index": tm["reference_nominal"]["t_pmin_report_index"],
            "baseline_worst_node_hours": tm["reference_nominal"]["t_pmin_hours"],
            "severe_corner_decision_instant_p_min_psi":
                tm["prv_lower_pump_lower"]["p_min_at_decision_instant_psi"],
            "severe_corner_full_horizon_p_min_psi":
                tm["prv_lower_pump_lower"]["p_min_horizon_psi"],
            "severe_corner_full_horizon_report_index":
                tm["prv_lower_pump_lower"]["t_pmin_report_index"],
            "severe_corner_full_horizon_hours":
                tm["prv_lower_pump_lower"]["t_pmin_hours"],
            "severe_corner_D_max_psi_nodesum": tm["prv_lower_pump_lower"]["D_max_psi_nodesum"],
            "severe_corner_DSR_min": tm["prv_lower_pump_lower"]["DSR_min"],
            "severe_corner_max_N_neg": tm["prv_lower_pump_lower"]["max_N_neg"],
        },
        "persisted_delayed_collapse": {
            "series_key": "wu16.delayed_collapse_case.series.p_min_psi",
            "series_length": len(dcc["series"]["p_min_psi"]),
            "series_first_value_psi": dcc["series"]["p_min_psi"][0],
            "series_last_value_psi": dcc["series"]["p_min_psi"][-1],
            "worst_p_min_over_window": sweep["worst_p_min_over_window"],
            "first_report_index_below_theta_p": sweep["first_report_index_below_theta_p"],
        },
        "computational_cost": wu16["computational_cost"],
        "evidence_grade_note": (
            "Empirical corners are LIMITED: R1b single severe corner "
            "(prv_lower_pump_lower) plus reference_nominal and prv_all_lower. "
            "No oracle for true minimum-pressure safety. Findings are "
            "characterisation-grade, not a full admissible-set proof."),
    }


# ---------------------------------------------------------------------------
# 4/13 metric_definitions  (copied VERBATIM from WU-17)
# ---------------------------------------------------------------------------
def build_metric_definitions(wu17: dict) -> dict:
    md = dict(wu17["metric_definitions"])
    md["safe_iff_rules"] = {
        "note": "SAFE == True == do NOT intervene. Immediate (S*) and temporal (TS* over [0..H]).",
        "S1": "p_min(post) >= theta_p            (absolute worst-node floor)",
        "S2": "dp_min = p_min(post)-p_min(cur) >= -eps_p   (worst-node non-degradation)",
        "S3": "dD = D(post)-D(cur) <= eps_D       (aggregate-deficit non-increase)",
        "S4": "N_neg(post) == 0                   (negative-pressure hard backstop)",
        "TS1": "min_{0..H} p_min >= theta_p",
        "TS2": "min_{0..H} dp_min >= -eps_p",
        "TS3": "max_{0..H} dD <= eps_D",
        "TS4": "max_{0..H} N_neg == 0",
    }
    return md


# ---------------------------------------------------------------------------
# 5/13 candidate_analysis  (K1-K4; WU-17 blocks verbatim + conceptual stress-tests)
# ---------------------------------------------------------------------------
def _candidate_stress_tests(wu16: dict) -> dict:
    tm = wu16["trajectory_metrics"]["prv_lower_pump_lower"]
    sweep = wu16["delayed_collapse_case"]["horizon_pmin_sweep"]
    inst = tm["p_min_at_decision_instant_psi"]
    full = tm["p_min_horizon_psi"]
    return {
        "K1_backstop_plus_relative": {
            "architecture": "D",
            "conceptual_stress_test": (
                "S4 negative backstop is INERT on every tested corner (max_N_neg=0 "
                "including the {full} psi collapse), so protection rests entirely on the "
                "layered TS2 relative rule; TS2 eps_p=0 activates from H=1 on the severe "
                "corner. Failure surface: if TS2 threshold/horizon is mis-set the backstop "
                "adds NO 20-psi protection.").format(full=full),
                "descriptive_only": True,
        },
        "K2_aggregate_deficit_lookahead": {
            "architecture": "C",
            "conceptual_stress_test": (
                "TS3 aggregate deficit is baseline-safe but can MASK a localised worst-node "
                "collapse: aggregate D and worst-node p_min are only weakly anti-correlated "
                "(deficit<->leak corr -0.7735 in WU-14). On the tested corner D_max rises to "
                "31.727617263793945 while p_min falls to {full} psi; an aggregate tolerance "
                "could pass a step whose single worst node has collapsed.").format(full=full),
            "descriptive_only": True,
        },
        "K3_immediate_well_posed_absolute": {
            "architecture": "A",
            "conceptual_stress_test": (
                "S1 at the decision instant reads {inst} psi on the severe corner and NEVER "
                "sees the {full} psi 96 h collapse (H=0 blindness). A well-posed absolute "
                "floor must sit strictly below the baseline worst node ~4.16452169418335 psi, "
                "so it cannot enforce a useful 20-psi floor without flagging the chronic "
                "baseline.").format(inst=inst, full=full),
            "descriptive_only": True,
        },
        "K4_rolling_absolute_lookahead": {
            "architecture": "B",
            "conceptual_stress_test": (
                "TS1 theta_p=5 does NOT activate for H in {1,2,4,8} (worst-over-window "
                "5.4615/5.4045/5.3083/5.1472 psi) and activates only once the window reaches "
                "the persisted crossover at report_index 13 (6.5 h); it inherits S1 "
                "ill-posedness above ~4.16452169418335 psi. CORRECTION vs WU-17: the onset is "
                "PERSISTED (not untested) via first_report_index_below_theta_p."),
            "persisted_crossover_theta_p_5": sweep["first_report_index_below_theta_p"].get("theta_p_psi=5.0"),
            "descriptive_only": True,
        },
    }


def build_candidate_analysis(wu16: dict, wu17: dict) -> dict:
    return {
        "note": ("K1-K4 are PROVISIONAL CANDIDATES - NOT APPROVED, NOT ranked, NOT scored. "
                 "Architecture blocks and candidate configs copied verbatim from WU-17; the "
                 "conceptual_stress_tests are WU-18 review layers, descriptive only."),
        "architectures": wu17["architectures"],
        "candidate_configurations": wu17["candidate_configurations"],
        "decision_matrix": wu17["decision_matrix"],
        "conceptual_stress_tests": _candidate_stress_tests(wu16),
    }


# ---------------------------------------------------------------------------
# 6/13 horizon_analysis  (WU-17 verbatim + PERSISTED crossover correction)
# ---------------------------------------------------------------------------
def build_horizon_analysis(wu16: dict, wu17: dict) -> dict:
    sweep = wu16["delayed_collapse_case"]["horizon_pmin_sweep"]
    return {
        "note": ("WU-17 horizon_analysis reproduced verbatim, then CORRECTED: the delayed "
                 "collapse onset IS persisted in WU-16 (not untested)."),
        "wu17_horizon_analysis_verbatim": wu17["horizon_analysis"],
        "crossover_onset_correction": {
            "supersedes": "wu17.horizon_analysis.crossover_interval_untested",
            "reason": ("WU-16 persists the full per-report-index worst-node series "
                       "(delayed_collapse_case.series.p_min_psi) and the first-crossing "
                       "index per theta_p. The onset is therefore KNOWN, not untested."),
            "worst_p_min_over_window": sweep["worst_p_min_over_window"],
            "first_report_index_below_theta_p": sweep["first_report_index_below_theta_p"],
            "severe_corner_smallest_sufficient_H_for_theta_p_5": {
                "report_index": sweep["first_report_index_below_theta_p"]["theta_p_psi=5.0"]["report_index"],
                "hours": sweep["first_report_index_below_theta_p"]["theta_p_psi=5.0"]["hours"],
                "control_steps": sweep["first_report_index_below_theta_p"]["theta_p_psi=5.0"]["report_index"],
                "interpretation": ("On the severe prv_lower_pump_lower corner an absolute "
                                   "floor at theta_p=5 psi is first breached at report index "
                                   "13 (6.5 h). A rolling window (arch B) must reach H>=13 "
                                   "control steps to catch this corner under theta_p=5."),
            },
            "residual_genuine_gap": (
                "Only the temporal RULE-ACTIVATION booleans were tabulated at coarse H in "
                "{1,2,4,8,192}. Intermediate thresholds 5<theta_p<10 and non-severe action "
                "corners are not swept. Both are COMPUTABLE from the persisted series "
                "without new EPANET runs; neither is a STEP-9 blocker."),
        },
    }


# ---------------------------------------------------------------------------
# 7/13 threshold_analysis  (NO threshold invented; every value labelled)
# ---------------------------------------------------------------------------
def build_threshold_analysis(wu16: dict) -> dict:
    baseline_worst = wu16["trajectory_metrics"]["reference_nominal"]["p_min_horizon_psi"]
    return {
        "principle": ("No threshold is invented or selected. Each is a swept provisional "
                      "grid value, an evidence-supported gate, or explicitly "
                      "'" + THRESH_UNJUSTIFIED + "'."),
        "negative_pressure_gate": {
            "rule": "N_neg(post)==0",
            "label": "EVIDENCE-SUPPORTED",
            "basis": ("Baseline holds max_N_neg=0 across the full 96 h horizon on every "
                      "tested corner; the only well-posed hard absolute gate that never "
                      "flags the baseline."),
        },
        "absolute_floor_theta_p_psi": {
            "grid": [0.0, 5.0, 10.0, 15.0, 20.0],
            "label": "PROVISIONAL - swept, not selected",
            "well_posedness_bound_psi": baseline_worst,
            "well_posedness_rule": (
                "A well-posed absolute floor must sit STRICTLY BELOW the baseline worst "
                "node ({b} psi); otherwise it flags the chronic native baseline at some "
                "instant. theta_p=0 degenerates to the negative-pressure gate (S4). "
                "theta_p in {{5,10,15,20}} all exceed the baseline worst node and are "
                "therefore ill-posed as baseline-compatible absolute floors.").format(b=baseline_worst),
            "useful_20psi_floor_status": THRESH_UNJUSTIFIED,
            "useful_20psi_floor_reason": (
                "A 20-psi absolute floor is NOT empirically justifiable as baseline-"
                "compatible: 386 baseline node-timesteps sit below 20 psi (WU-14)."),
        },
        "relative_degradation_eps_p_psi": {
            "grid": [0.0, 2.0, 5.0],
            "label": "PROVISIONAL - swept, not selected",
            "basis": ("Relative rule is baseline-safe (identity hold -> no activation at "
                      "eps_p=0). Exact operating eps_p is a researcher value judgement; "
                      + THRESH_UNJUSTIFIED + " for any single value."),
        },
        "aggregate_deficit_eps_D_psi_nodesum": {
            "grid": [0.0, 2.0, 5.0],
            "label": "PROVISIONAL - swept, not selected",
            "basis": ("Relative aggregate rule is baseline-safe but can mask localised "
                      "collapse; exact eps_D is " + THRESH_UNJUSTIFIED + "."),
        },
        "clip_alpha_H2": {
            "grid": [0.0, 0.25, 0.5, 0.75, 1.0],
            "label": "PROVISIONAL - coarse grid, not selected",
            "basis": "Interpolation fraction toward a_prev; one solve per inspected alpha (WU-15).",
        },
        "summary": ("The ONLY evidence-supported hard threshold is the negative-pressure "
                    "gate N_neg==0. All pressure/deficit tolerances remain PROVISIONAL; a "
                    "useful absolute 20-psi floor is " + THRESH_UNJUSTIFIED + " as "
                    "baseline-compatible."),
    }


# ---------------------------------------------------------------------------
# 8/13 action_handling_analysis  (H1/H2/H3; WU-17 verbatim + framing)
# ---------------------------------------------------------------------------
def build_action_handling_analysis(wu17: dict) -> dict:
    return {
        "note": ("H1/H2/H3 are NOT selected. Handling policies copied verbatim from WU-17; "
                 "framing is descriptive, not ordered."),
        "handling_policies": wu17["handling_policies"],
        "framing": {
            "H1_reject_to_previous": "discontinuous; 0 extra solves; executed=a_prev on breach.",
            "H2_clip_toward_previous": ("continuous action image (PPO-friendly); one solve per "
                                        "inspected alpha on the {0,0.25,0.5,0.75,1.0} grid."),
            "H3_fallback_reference_action": "discontinuous; 0 extra solves; executed=reference_nominal.",
            "shared_consequence": ("Every policy makes executed != proposed on intervention, "
                                   "coupling to the effort-term train/execute decision "
                                   "(see train_execute_analysis)."),
        },
    }


# ---------------------------------------------------------------------------
# 9/13 train_execute_analysis  (WU-17 verbatim + effort-term open question)
# ---------------------------------------------------------------------------
def build_train_execute_analysis(wu17: dict) -> dict:
    tei = wu17["training_execution_implications"]
    return {
        "note": ("Copied verbatim from WU-17. The effort-term integration is FLAGGED, not "
                 "decided; the frozen reward definition is untouched."),
        "ppo_compatibility_wu15": tei["ppo_compatibility_wu15"],
        "ppo_compatibility_wu16": tei["ppo_compatibility_wu16"],
        "proposed_vs_executed_mismatch": tei["proposed_vs_executed_mismatch"],
        "effort_term_open_question": tei["effort_term_open_question"],
        "continuity": tei["continuity"],
        "interval": tei["interval"],
        "carried_into_d_p6_006": (
            "The proposed-vs-executed effort-term convention is a training-integration "
            "decision COUPLED to the handling policy. It is a D-P6-006 companion item, not "
            "a STEP-9 blocker, and does not modify D-P6-005."),
    }


# ---------------------------------------------------------------------------
# 10/13 repeated_intervention_analysis  (conceptual; no new measurement)
# ---------------------------------------------------------------------------
def build_repeated_intervention_analysis(wu16: dict) -> dict:
    return {
        "note": ("Conceptual analysis of what happens under REPEATED admissibility "
                 "interventions across consecutive control steps. Descriptive only; no new "
                 "EPANET runs. No single mechanism is preferred."),
        "H1_reject_to_previous_risk": (
            "Repeatedly rejecting to a_prev freezes the actuator at the last-admitted "
            "action. If that held action is itself on a slow tank-drawdown trajectory, "
            "repeated holds can COMPOUND toward the delayed collapse the immediate rule "
            "cannot see: the severe corner reads {inst} psi at the decision instant but "
            "{full} psi at 96 h.").format(
                inst=wu16["trajectory_metrics"]["prv_lower_pump_lower"]["p_min_at_decision_instant_psi"],
                full=wu16["trajectory_metrics"]["prv_lower_pump_lower"]["p_min_horizon_psi"]),
        "H2_clip_risk": (
            "Repeated clipping toward a_prev keeps executed actions in a shrinking "
            "neighbourhood of the last admitted action; continuous but can stall policy "
            "exploration near a safe-but-suboptimal operating point."),
        "H3_fallback_risk": (
            "Repeated fallback to reference_nominal repeatedly overrides the policy with "
            "the native setpoints; reference_nominal itself holds the chronic ~4.16 psi "
            "baseline worst node, i.e. the fallback is baseline-safe but not 20-psi safe."),
        "backstop_interaction": (
            "A negative-pressure backstop (S4/TS4) is INERT on every tested corner "
            "(max_N_neg=0), so it does not bound repeated-intervention drift in-range; the "
            "temporal layer governs that behaviour."),
        "mitigation_note": (
            "A look-ahead architecture (B/C/D) that inspects the forward window is the only "
            "characterised way to detect drawdown-driven compounding before it materialises; "
            "the required horizon is the persisted crossover (>=13 steps for theta_p=5 on "
            "the severe corner). This is design guidance, NOT a selection."),
        "coverage_limit": (
            "Repeated-intervention dynamics are NOT empirically simulated (no closed-loop "
            "policy rollout in STEP-9); this is a reasoned risk map, deferred to STEP-12 "
            "testing."),
    }


# ---------------------------------------------------------------------------
# 11/13 final_provisional_designs  (<=3; definitional order, NOT ranked/scored)
# ---------------------------------------------------------------------------
def build_final_provisional_designs(wu16: dict) -> dict:
    sweep = wu16["delayed_collapse_case"]["horizon_pmin_sweep"]
    onset5 = sweep["first_report_index_below_theta_p"]["theta_p_psi=5.0"]
    baseline_worst = wu16["trajectory_metrics"]["reference_nominal"]["p_min_horizon_psi"]
    return {
        "order_is_definitional_not_quality": True,
        "not_ordered_by_quality": True,
        "count": 3,
        "count_limit": "<=3 (STEP-9 FINAL REVIEW PART-19 cap)",
        "all_status": NOT_APPROVED,
        "designs": [
            {
                "design_id": "F1",
                "label": "negative backstop LAYERED with short-window relative degradation",
                "status": NOT_APPROVED,
                "architecture": "D",
                "metric_rule": "S4/TS4 (N_neg==0) LAYERED with S2/TS2 (worst-node non-degradation over [0..H]).",
                "threshold": {
                    "negative_gate": "N_neg==0 (EVIDENCE-SUPPORTED)",
                    "eps_p_psi": "PROVISIONAL grid {0,2,5} - not selected",
                },
                "horizon": "PROVISIONAL short window; TS2 reacts at H=1 on the severe corner.",
                "handling_policy": "H1 or H2 - OPEN, not selected.",
                "baseline_compatibility": "baseline-safe (backstop never fires; relative layer identity-safe).",
                "properties": "reacts at H=1; no absolute floor; backstop inert in-range.",
                "open_parameters": ["eps_p", "H", "clip-vs-reject", "effort-term convention"],
            },
            {
                "design_id": "F2",
                "label": "rolling absolute worst-node floor over a finite look-ahead window",
                "status": NOT_APPROVED,
                "architecture": "B (subsumes A as the H=0 degenerate limit)",
                "metric_rule": "TS1 min_{0..H} p_min >= theta_p.",
                "threshold": {
                    "theta_p_psi": "PROVISIONAL grid {0,5,10,15,20}; well-posed only strictly below baseline worst node ~" + repr(baseline_worst) + " psi.",
                },
                "horizon": {
                    "status": "PERSISTED for the severe corner (correction vs WU-17).",
                    "smallest_sufficient_H_for_theta_p_5_report_index": onset5["report_index"],
                    "smallest_sufficient_H_for_theta_p_5_hours": onset5["hours"],
                },
                "handling_policy": "H1 or H2 - OPEN, not selected.",
                "baseline_compatibility": "ill-posed as a useful 20-psi floor (inherits S1); " + THRESH_UNJUSTIFIED + " above ~4.16 psi.",
                "properties": "absolute guarantee within window; A is the H=0 special case whose documented limitation is blindness to the 96 h collapse.",
                "open_parameters": ["theta_p (bounded < ~4.16 psi for well-posedness)", "H", "clip-vs-reject"],
            },
            {
                "design_id": "F3",
                "label": "aggregate-deficit non-increase over a finite look-ahead window",
                "status": NOT_APPROVED,
                "architecture": "C",
                "metric_rule": "TS3 max_{0..H} (D(post)-D(base)) <= eps_D.",
                "threshold": {
                    "eps_D_psi_nodesum": "PROVISIONAL grid {0,2,5} - not selected",
                },
                "horizon": "PROVISIONAL finite window; relative rule reacts at H=1 on the severe corner.",
                "handling_policy": "H1 or H2 - OPEN, not selected.",
                "baseline_compatibility": "baseline-safe (relative aggregate).",
                "properties": "baseline-safe; masking risk conceptually possible (deficit<->leak corr -0.7735) but not exhibited on the tested corner; no absolute floor.",
                "open_parameters": ["eps_D", "H", "aggregate-vs-worst-node masking risk"],
            },
        ],
        "common_note": ("All three are implementable admissibility layers over the frozen "
                        "action/observation/reward. None is selected, ranked, or scored; the "
                        "researcher composes the final D-P6-006 design."),
    }


# ---------------------------------------------------------------------------
# 12/13 unresolved_issues  (WU-17 uncertainties, superseded item corrected)
# ---------------------------------------------------------------------------
def build_unresolved_issues(wu16: dict, wu17: dict) -> dict:
    onset5 = wu16["delayed_collapse_case"]["horizon_pmin_sweep"]["first_report_index_below_theta_p"]["theta_p_psi=5.0"]
    src = list(wu17["uncertainties"])
    corrected = []
    for u in src:
        if "not persisted as a per-index series" in u or "is UNTESTED" in u and "crossover" in u:
            corrected.append(
                "SUPERSEDED: the delayed-collapse onset IS persisted "
                "(wu16.delayed_collapse_case.series.p_min_psi) and the theta_p=5 crossover "
                "is pinned at report_index {ri} ({h} h). Residual gap: temporal RULE "
                "activations tabulated only at coarse H in {{1,2,4,8,192}}; intermediate "
                "thresholds 5<theta_p<10 and non-severe corners are computable from the "
                "persisted series without new EPANET runs.".format(
                    ri=onset5["report_index"], h=onset5["hours"]))
        else:
            corrected.append(u)
    return {
        "note": "WU-17 uncertainties carried forward; the crossover item is corrected against disk.",
        "items": corrected,
        "coverage": wu17["coverage"],
        "classification": {
            "step9_blockers": [],
            "accepted_known_limitations_for_step12": [
                "no validated safe/unsafe oracle",
                "R1b single-corner empirical coverage",
                "coarse H2 alpha grid",
                "uncalibrated leakage emitter",
            ],
            "d_p6_006_companion_decisions": [
                "exact threshold value(s) within the provisional grids (researcher value judgement)",
                "effort-term proposed-vs-executed convention under intervention",
                "smallest-sufficient horizon IF an absolute-floor architecture is chosen "
                "(persisted at >=13 steps for theta_p=5 on the severe corner)",
            ],
        },
    }


# ---------------------------------------------------------------------------
# 13/13 decision_readiness  (READY verdict; states missing evidence if any)
# ---------------------------------------------------------------------------
def build_decision_readiness() -> dict:
    return {
        "readiness_verdict": READINESS,
        "verdict_is_not_a_selection": True,
        "basis": (
            "The four open STEP-9 decisions are fully FRAMED with reproducible evidence: "
            "(1) the metric/rule menu (S1-S4 / TS1-TS4) with baseline-compatibility and "
            "tested-corner behaviour characterised; (2) provisional threshold grids with "
            "the ONLY evidence-supported hard gate (N_neg==0) identified and the useful "
            "20-psi floor explicitly labelled " + THRESH_UNJUSTIFIED + "; (3) the "
            "look-ahead horizon behaviour PERSISTED, including the theta_p=5 crossover at "
            "13 steps (6.5 h) on the severe corner; (4) the handling policies H1/H2/H3 with "
            "compute cost and continuity. A researcher can compose a defensible D-P6-006 "
            "from this evidence."),
        "why_ready_not_blocked": (
            "The remaining unknowns are either researcher value judgements (exact threshold; "
            "leakage<->service<->safety exchange rate) or accepted STEP-12 limitations "
            "(oracle, single-corner coverage), NOT missing evidence that this review could "
            "or should produce without new measurement."),
        "conditions_carried_into_d_p6_006_not_blockers": [
            "exact threshold within provisional grids is a researcher value judgement bounded "
            "by well-posedness (< ~4.16 psi for an absolute floor)",
            "effort-term proposed-vs-executed convention under intervention",
        ],
        "missing_evidence_if_not_ready": "N/A - verdict is DECISION-READY.",
        "status_after_this_review": ("STEP-9 remains PROPOSED / PENDING RESEARCHER; no "
                                     "D-P6-006 minted; project is NOT PPO-ready until the "
                                     "researcher selects and approves."),
    }


# ---------------------------------------------------------------------------
# researcher decision form (BLANK) + top-level assembly
# ---------------------------------------------------------------------------
def build_researcher_action_required() -> dict:
    return {
        "instruction": ("The researcher makes the STEP-9 selection: choose/compose the "
                        "architecture (A/B/C/D or F1/F2/F3), fix the metric/rule, the "
                        "threshold, the look-ahead horizon, and the action-handling policy. "
                        "This review does NOT select any of them."),
        "decision_form_blank": {
            "A_architecture": None,
            "B_metric_rule": None,
            "C_threshold": None,
            "D_look_ahead_horizon": None,
            "E_action_handling_policy": None,
            "F_effort_term_action_under_intervention": None,
            "G_rationale": None,
        },
        "status_after_this_review": "STEP-9 remains PROPOSED / PENDING RESEARCHER; project is NOT PPO-ready.",
    }


def build_review(wu14, wu15, wu16, wu17, wu11) -> dict:
    review = {
        "decision_context": build_decision_context(wu17),
        "frozen_invariants": build_frozen_invariants(wu17),
        "evidence": build_evidence(wu14, wu15, wu16, wu17, wu11),
        "metric_definitions": build_metric_definitions(wu17),
        "candidate_analysis": build_candidate_analysis(wu16, wu17),
        "horizon_analysis": build_horizon_analysis(wu16, wu17),
        "threshold_analysis": build_threshold_analysis(wu16),
        "action_handling_analysis": build_action_handling_analysis(wu17),
        "train_execute_analysis": build_train_execute_analysis(wu17),
        "repeated_intervention_analysis": build_repeated_intervention_analysis(wu16),
        "final_provisional_designs": build_final_provisional_designs(wu16),
        "unresolved_issues": build_unresolved_issues(wu16, wu17),
        "decision_readiness": build_decision_readiness(),
        "researcher_action_required": build_researcher_action_required(),
        "researcher_selection": None,
    }
    review["self_checks"] = _self_checks(review, wu14, wu15, wu16, wu17, wu11)
    return review


def _forbidden_scan_targets(review: dict) -> dict:
    """Scan review keys EXCLUDING self_checks (which legitimately names tokens)."""
    return {k: v for k, v in review.items() if k != "self_checks"}


def _self_checks(review, wu14, wu15, wu16, wu17, wu11) -> dict:
    # frozen anchor targets
    LEAK_REF = 84.72988433677985
    REQ_REF = 906.3987348621764
    MOVEMENT_L2SQ_MAX = 28.0
    BASELINE_WORST = 4.16452169418335
    WU16_DECISION_INSTANT = 5.527866840362549
    WU16_FULL_HORIZON = 1.2946763038635254

    fc = review["frozen_invariants"]
    aspace = fc["action_space"]
    rew = fc["frozen_reward_D_P6_005"]["weights"]
    nconst = fc["normalization_constants_frozen"]
    tm = wu16["trajectory_metrics"]
    sweep = wu16["delayed_collapse_case"]["horizon_pmin_sweep"]
    onset5 = sweep["first_report_index_below_theta_p"]["theta_p_psi=5.0"]
    designs = review["final_provisional_designs"]["designs"]

    ordered = [b["actuator"] for b in aspace["ordered_bounds"]]
    expected_order = ["VALVE-173", "VALVE-175", "VALVE-176", "VALVE-177",
                      "VALVE-178", "PUMP-170", "PUMP-172"]

    checks = {
        "status_is_proposed": review["decision_context"]["status"] == STATUS,
        "researcher_selection_is_null": review["researcher_selection"] is None,
        "measures_nothing_new": review["decision_context"]["measures_nothing_new"] is True,
        "no_epanet_no_ppo_no_rng": review["decision_context"]["no_epanet_no_ppo_no_rng"] is True,
        "does_not_select_or_order_designs": review["decision_context"]["does_not_select_or_order_designs"] is True,
        "no_forbidden_key_tokens": _has_forbidden_key(_forbidden_scan_targets(review)) is None,
        "no_disallowed_top_level_keys": not any(
            k in review for k in ("winner", "ranking", "score", "recommendation")),
        "observation_dim_139": fc["observation"]["observation_dim"] == 139,
        "action_dim_7": aspace["action_dim"] == 7,
        "action_ordering_unchanged": ordered == expected_order,
        "reward_weights_frozen": (rew["w_L"] == 1.0 and rew["w_U"] == 1.0
                                  and rew["w_P"] == 1.0 and rew["w_A"] == 0.1
                                  and rew["w_E"] == 0.0),
        "leak_ref_frozen": _close(nconst["leak_ref_gpm"], LEAK_REF),
        "req_ref_frozen": _close(nconst["req_ref_gpm"], REQ_REF),
        "movement_L2sq_max_frozen": _close(nconst["movement_L2sq_max"], MOVEMENT_L2SQ_MAX),
        "baseline_worst_node_reproduced": _close(
            tm["reference_nominal"]["p_min_horizon_psi"], BASELINE_WORST),
        "wu16_decision_instant_5p53": _close(
            tm["prv_lower_pump_lower"]["p_min_at_decision_instant_psi"], WU16_DECISION_INSTANT),
        "wu16_full_horizon_1p29": _close(
            tm["prv_lower_pump_lower"]["p_min_horizon_psi"], WU16_FULL_HORIZON),
        "wu16_max_N_neg_0": tm["prv_lower_pump_lower"]["max_N_neg"] == 0,
        "crossover_onset_persisted_index_13": onset5["report_index"] == 13,
        "crossover_onset_persisted_hours_6p5": _close(onset5["hours"], 6.5),
        "metric_definitions_present": "p_min" in review["metric_definitions"],
        "safe_iff_rules_present": "safe_iff_rules" in review["metric_definitions"],
        "architectures_A_D_present": [a.get("architecture_id") for a in review["candidate_analysis"]["architectures"] if a.get("architecture_id")] == ["A", "B", "C", "D"],
        "n_final_designs_between_2_and_4": 2 <= len(designs) <= 4,
        "all_final_designs_not_approved": all(d["status"] == NOT_APPROVED for d in designs),
        "final_designs_not_ordered_by_quality": review["final_provisional_designs"]["not_ordered_by_quality"] is True,
        "readiness_verdict_valid": review["decision_readiness"]["readiness_verdict"] in (READINESS, NOT_READY),
        "decision_form_blank_all_none": all(
            v is None for v in review["researcher_action_required"]["decision_form_blank"].values()),
        "no_d_p6_006_minted": "STEP-9 remains PROPOSED" in review["decision_readiness"]["status_after_this_review"],
        "no_generated_utc_key": "generated_utc" not in set(_iter_keys(review)),
        "all_values_finite": _all_finite(review),
    }
    return checks


def serialize(review: dict) -> str:
    """Canonical byte-reproducible serialization (indent=2, ascii, trailing newline)."""
    return json.dumps(review, indent=2, ensure_ascii=True, sort_keys=False) + "\n"


def load_all():
    return (
        _load(WU14_PATH),
        _load(WU15_PATH),
        _load(WU16_PATH),
        _load(WU17_PATH),
        _load(WU11_PATH),
    )


def build() -> dict:
    wu14, wu15, wu16, wu17, wu11 = load_all()
    return build_review(wu14, wu15, wu16, wu17, wu11)


def main() -> int:
    review = build()
    failed = [k for k, v in review["self_checks"].items() if v is not True]
    if failed:
        raise SystemExit("SELF-CHECK FAILURES: " + ", ".join(failed))
    OUT_PATH.write_text(serialize(review), encoding="utf-8")
    print(f"WROTE {OUT_PATH}")
    print(f"self_checks: {len(review['self_checks'])} gates, all pass")
    print(f"readiness_verdict: {review['decision_readiness']['readiness_verdict']}")
    print(f"final_provisional_designs: {review['final_provisional_designs']['count']} "
          f"({', '.join(d['design_id'] for d in review['final_provisional_designs']['designs'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

