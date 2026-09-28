#!/usr/bin/env python3
"""STEP-9 safety-mechanism decision brief — evidence aggregator (WU-17).

PURPOSE
-------
Aggregate the ALREADY-FROZEN STEP-9 evidence artefacts

  * WU-14  results/phase6/p6_s9_safety_design_analysis.json          (design analysis)
  * WU-15  results/phase6/p6_s9_safety_mechanism_characterization.json (empirical)
  * WU-16  results/phase6/p6_s9_temporal_safety_characterization.json  (temporal)

plus the frozen reward brief (WU-11) that carries the chronic-baseline anchors,
into a single decision-ready brief that FRAMES the four STEP-9 decisions

  A. safety metric / admissibility rule
  B. threshold / tolerance
  C. look-ahead horizon
  D. action-handling policy (clip vs reject vs fallback)

WITHOUT making any of them.

This script MEASURES NOTHING NEW. It re-loads the committed JSON artefacts, copies
their evidence sub-trees verbatim, re-checks the frozen normalisation constants and
the cross-artefact baseline anchors, characterises the four candidate ARCHITECTURES
(A-D) on a fixed factual schema, lists PROVISIONAL (NOT APPROVED) candidate
configurations whose every threshold is either a swept provisional-grid value or an
evidence-supported gate, and writes ``results/phase6/p6_s9_decision_brief.json`` with
``researcher_selection`` set to ``null``.

Binding constraints honoured (STEP-9 DECISION GATE):
  * does NOT run EPANET, does NOT run PPO, uses no RNG, adds no generated_utc;
  * does NOT select / rank / score / declare a winner among architectures, metrics,
    thresholds, horizons, or handling policies;
  * does NOT invent a threshold (each is grid-provisional or evidence-supported);
  * does NOT implement the production safety wrapper or reward.py;
  * does NOT modify the frozen action space, observation spec, or reward;
  * STEP-9 stays PROPOSED / PENDING RESEARCHER.

Byte-reproducible: pure re-shaping of on-disk evidence; no timestamp, no wall-clock,
no environment-dependent value is introduced. Running it twice yields identical bytes.
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
WU11_PATH = RESULTS / "p6_d_p6_005_decision_brief.json"
OUT_PATH = RESULTS / "p6_s9_decision_brief.json"

DECISION_ID = "STEP9_SAFETY_MECHANISM"
STATUS = "PROPOSED / PENDING RESEARCHER"
NOT_APPROVED = "PROVISIONAL CANDIDATE - NOT APPROVED"

# Scanned over KEYS only (matches the WU-16 convention: source disclaimers legitimately
# contain these tokens inside negations such as "no ranking/scoring", so a value scan
# would be self-defeating). "select"/"selection" are NOT forbidden.
FORBIDDEN_KEY_TOKENS = ("winner", "rank", "tier", "score", "best",
                        "superior", "optimal", "preferred", "recommend")

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


def _iter_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _iter_keys(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _iter_keys(v)


def _has_key(obj, target: str) -> bool:
    return any(k == target for k in _iter_keys(obj))


def the_four_decisions() -> dict:
    """The four STEP-9 decisions the brief FRAMES but does NOT make."""
    return {
        "A_safety_metric_rule": {
            "question": "Which admissibility signal/rule governs whether a proposed action is executed?",
            "evidence_candidates": ["S1/TS1 absolute worst-node floor",
                                    "S2/TS2 worst-node degradation vs current/baseline",
                                    "S3/TS3 aggregate-deficit increase",
                                    "S4/TS4 negative-pressure hard backstop"],
            "evidence_sources": ["wu14_design_analysis", "wu15_empirical_characterization",
                                 "wu16_temporal_characterization"],
            "selection": None,
        },
        "B_threshold_tolerance": {
            "question": "Which numeric threshold (theta_p / eps_p / eps_D) or gate is used?",
            "provisional_grids_swept_not_selected": {
                "S1_TS1_theta_p_psi": [0.0, 5.0, 10.0, 15.0, 20.0],
                "S2_TS2_eps_p_psi": [0.0, 2.0, 5.0],
                "S3_TS3_eps_D_psi_nodesum": [0.0, 2.0, 5.0],
            },
            "well_posedness_constraint": (
                "An ABSOLUTE worst-node floor is well-posed only for theta_p strictly below the "
                "chronic-baseline worst node (~4.16452 psi); at theta_p >= ~4.16 it flags the "
                "native baseline itself. The only well-posed HARD absolute gate is negative "
                "pressure (baseline count 0)."
            ),
            "selection": None,
        },
        "C_look_ahead_horizon": {
            "question": "Over how many forward control steps is the rule evaluated (H)?",
            "horizons_characterised_control_steps": [1, 2, 4, 8, 192],
            "horizons_characterised_hours": [0.5, 1.0, 2.0, 4.0, 96.0],
            "selection": None,
        },
        "D_action_handling_policy": {
            "question": "On an inadmissible action, reject to previous, clip toward previous, or fall back?",
            "evidence_candidates": ["H1 reject -> previous action a_prev",
                                    "H2 clip toward previous (alpha grid)",
                                    "H3 fallback reference action"],
            "selection": None,
        },
    }


def architectures() -> list:
    """Four candidate safety ARCHITECTURES on a FIXED FACTUAL schema.

    Each field is a factual reading of the WU-14/15/16 evidence. No architecture is
    scored, ordered, or marked; the schema is identical across all four so the
    researcher can compare them on their own terms.
    """
    schema_note = (
        "Fixed schema per architecture: composition, decision_information, "
        "look_ahead_dependence, threshold_dependence, tank_state_dependence, "
        "baseline_compatibility, tested_severe_corner_behaviour, delayed_collapse_visibility, "
        "compute_cost_per_decision, intervention_type, proposed_vs_executed_mismatch, "
        "failure_modes, main_unresolved_issue. Descriptive only; NOT scored or ordered."
    )
    A = {
        "architecture_id": "A",
        "name": "Immediate Rule (post-action decision instant only)",
        "composition": "Evaluate one of S1/S2/S3/S4 at the post-action decision instant (H=0); no forward window.",
        "decision_information": "post-action state at the decision instant (one look-ahead solve).",
        "look_ahead_dependence": "none beyond the single post-action instant.",
        "threshold_dependence": "one of theta_p (S1) / eps_p (S2) / eps_D (S3) / negative-gate (S4).",
        "tank_state_dependence": "uses the decision-instant tank state only; does not model tank drawdown.",
        "baseline_compatibility": (
            "S1 flags the chronic baseline at theta_p >= ~4.16 psi (ill-posed at 20 psi); "
            "S2/S3 relative rules do not flag the baseline; S4 never fires on the baseline (0 negatives)."
        ),
        "tested_severe_corner_behaviour": (
            "At the severe prv_lower_pump_lower decision instant p_min=5.527866840362549 psi, "
            "D=27.494426727294922, N_neg=0, DSR=0.9227158066978032 (WU-16 view A); an immediate "
            "absolute rule at theta_p=5 does NOT flag it, an absolute rule at theta_p>=10 does but "
            "also flags the baseline."
        ),
        "delayed_collapse_visibility": (
            "CANNOT see the 96 h collapse to p_min=1.2946763038635254 psi: the decision instant "
            "reads 5.53 psi (WU-16 single_step_vs_trajectory)."
        ),
        "compute_cost_per_decision": "1 forward EPANET solve (WU-15 hydraulic_evals_per_proposed_action_look_ahead=1).",
        "intervention_type": "reject or clip at the decision instant (H1/H2/H3).",
        "proposed_vs_executed_mismatch": "yes when it intervenes (WU-15 PPO_compatibility).",
        "failure_modes": [
            "misses delayed tank-drawdown collapse that only materialises later in the horizon;",
            "an absolute floor is ill-posed above the baseline worst node (~4.16 psi).",
        ],
        "main_unresolved_issue": "blind to delayed deterioration; well-posed absolute floor sits below the useful range.",
    }
    B = {
        "architecture_id": "B",
        "name": "Rolling Short-Horizon Look-Ahead (absolute floor over t+1..t+H)",
        "composition": "Evaluate TS1 (absolute worst-node floor) over a finite forward window of H control steps.",
        "decision_information": "worst-node pressure at each of H forward instants (H look-ahead solves).",
        "look_ahead_dependence": "finite H; behaviour depends strongly on H (see horizon_analysis).",
        "threshold_dependence": "theta_p (absolute).",
        "tank_state_dependence": "captures tank drawdown only within the H-step window.",
        "baseline_compatibility": "inherits S1 ill-posedness: theta_p >= ~4.16 psi flags the chronic baseline.",
        "tested_severe_corner_behaviour": (
            "TS1 theta_p=5 worst-over-window is 5.4615/5.4045/5.3083/5.1472 psi at H=1/2/4/8 (does NOT "
            "activate) and 1.2947 psi at full (activates) - WU-16 temporal_rule_outputs."
        ),
        "delayed_collapse_visibility": (
            "sees the collapse only if H reaches the (untested) onset between H=8 (4 h) and full (96 h)."
        ),
        "compute_cost_per_decision": "H forward solves (linear; full=192x single-step, WU-16 per_horizon_lookahead_cost).",
        "intervention_type": "reject or clip when the window floor is breached.",
        "proposed_vs_executed_mismatch": "yes when it intervenes.",
        "failure_modes": [
            "short H misses the delayed collapse; long H is costly and still absolute-threshold ill-posed;",
            "the H at which the severe corner is caught under a well-posed theta_p is UNTESTED.",
        ],
        "main_unresolved_issue": "horizon length vs cost vs absolute-threshold well-posedness are coupled and unresolved.",
    }
    C = {
        "architecture_id": "C",
        "name": "Look-Ahead + State-Degradation (finite window + relative rule)",
        "composition": "Evaluate TS2 (worst-node degradation) and/or TS3 (aggregate-deficit increase) over H steps vs the aligned baseline trajectory.",
        "decision_information": "post-action AND aligned-baseline worst-node/deficit over H forward instants.",
        "look_ahead_dependence": "finite H; the relative rule reacts even at H=1 on the tested corner.",
        "threshold_dependence": "eps_p (TS2) and/or eps_D (TS3), relative.",
        "tank_state_dependence": "compares post-action vs baseline tank trajectories over the window.",
        "baseline_compatibility": "well-posed: relative rules do not flag the chronic baseline (identity hold -> no activation at eps=0).",
        "tested_severe_corner_behaviour": (
            "TS2 eps_p=0 activates at H=1 (worst dp_min ~ -0.0968 psi) through full (~ -4.3007 psi) - "
            "reacts at short horizon (WU-16); S3 aggregate can mask localised collapse (WU-14 note; "
            "deficit<->leak corr -0.7735)."
        ),
        "delayed_collapse_visibility": (
            "detects worsening-vs-baseline early, but a RELATIVE rule gives no ABSOLUTE min-pressure guarantee."
        ),
        "compute_cost_per_decision": "H forward solves for the action + aligned baseline trajectory (WU-16).",
        "intervention_type": "reject or clip on relative degradation beyond tolerance.",
        "proposed_vs_executed_mismatch": "yes when it intervenes.",
        "failure_modes": [
            "relative rule cannot enforce an absolute floor;",
            "aggregate deficit (S3/TS3) can mask a localised worst-node collapse.",
        ],
        "main_unresolved_issue": "provides no absolute guarantee; tolerance eps and horizon H are unset.",
    }
    D = {
        "architecture_id": "D",
        "name": "Backstop + Temporal (negative-pressure gate LAYERED with temporal/degradation check)",
        "composition": "Layer S4/TS4 immediate negative-pressure hard backstop WITH a temporal TS1/TS2/TS3 check over H.",
        "decision_information": "post negative-node count (immediate) PLUS windowed worst-node/deficit over H.",
        "look_ahead_dependence": "backstop is immediate (H=0); the temporal layer adds finite H.",
        "threshold_dependence": "negative gate (fixed, evidence-supported) PLUS theta_p/eps_p/eps_D for the temporal layer.",
        "tank_state_dependence": "temporal layer captures drawdown within H; backstop is instantaneous.",
        "baseline_compatibility": "S4 backstop never fires on the baseline (0 negatives); temporal relative layer also baseline-safe.",
        "tested_severe_corner_behaviour": (
            "TS4 negative backstop NEVER activates on any tested corner (max_N_neg=0 including the "
            "1.2947 psi collapse); the temporal layer supplies the non-negative protection."
        ),
        "delayed_collapse_visibility": "the temporal layer inherits its window's visibility; the backstop only catches sub-zero.",
        "compute_cost_per_decision": "1 solve for the backstop PLUS H solves for the temporal layer.",
        "intervention_type": "hard reject on negative pressure; reject/clip on temporal-layer breach.",
        "proposed_vs_executed_mismatch": "yes when either layer intervenes.",
        "failure_modes": [
            "the negative backstop alone gives NO 20-psi protection (never fires above 0 psi);",
            "overall protection depends entirely on the temporal layer's metric/threshold/horizon choices.",
        ],
        "main_unresolved_issue": "the backstop is well-posed but inert in-range; the layered temporal rule still needs A/B/C/D decisions.",
    }
    return [{"schema_note": schema_note}, A, B, C, D]


def horizon_analysis(wu16: dict) -> dict:
    """Factual reading of the look-ahead horizon sweep on the tested severe corner.

    All numbers are copied from WU-16 temporal_rule_outputs / single_step_vs_trajectory.
    No horizon is selected; the crossover interval is reported as characterised evidence
    plus an explicit UNTESTED gap.
    """
    sev_tro = wu16["temporal_rule_outputs"]["prv_lower_pump_lower_vs_baseline"]
    sev_view = wu16["single_step_vs_trajectory"]["prv_lower_pump_lower"]
    ts1_theta5 = sev_tro["TS1"]["theta_p_psi=5.0"]
    ts2_eps0 = sev_tro["TS2"]["eps_p_psi=0.0"]
    return {
        "tested_command": "prv_lower_pump_lower (severe lower-corner; R1b single characterised corner)",
        "decision_instant_state": sev_view["view_A_single_step_decision_instant"],
        "full_horizon_state": sev_view["view_B_trajectory_over_full_horizon"],
        "absolute_floor_TS1_theta_p_5psi_worst_over_window": {
            "H=1": ts1_theta5["H=1"], "H=2": ts1_theta5["H=2"], "H=4": ts1_theta5["H=4"],
            "H=8": ts1_theta5["H=8"], "full": ts1_theta5["full"],
        },
        "relative_degradation_TS2_eps_p_0_over_window": {
            "H=1": ts2_eps0["H=1"], "H=2": ts2_eps0["H=2"], "H=4": ts2_eps0["H=4"],
            "H=8": ts2_eps0["H=8"], "full": ts2_eps0["full"],
        },
        "observed_pattern": (
            "The severe corner reads 5.527866840362549 psi worst-node at the decision instant and "
            "5.461512565612793 / 5.404520511627197 / 5.308281421661377 / 5.147222042083740 psi over "
            "H=1/2/4/8 (0.5-4 h), then collapses to 1.2946763038635254 psi at report index 192 (96 h) "
            "as the tanks drain. An absolute floor TS1 at theta_p=5 therefore does NOT activate for any "
            "tested finite H<=8 but DOES activate over the full horizon; a relative-degradation rule TS2 "
            "at eps_p=0 activates from H=1 onward."
        ),
        "crossover_interval_untested": {
            "statement": (
                "Under a well-posed absolute floor, the horizon at which the severe collapse is first "
                "caught lies strictly between H=8 (4 h) and full (96 h). The exact onset index is NOT "
                "persisted as a per-index p_min series in the STEP-9 artefacts, so intermediate horizons "
                "(e.g. 16/24/48/96 control steps) are UNTESTED."
            ),
            "conditional_open_item": (
                "Testing intermediate horizons is required ONLY IF the researcher selects an "
                "absolute-threshold look-ahead architecture (B) AND wants the smallest sufficient H. "
                "A relative-degradation architecture (C) already reacts at H=1 on this corner and needs "
                "no such test. This is a conditional design question, NOT a pending experiment mandated "
                "by this brief."
            ),
        },
        "cost_coupling": (
            "Look-ahead cost is linear in H (H forward solves per decision; full = 192x the single-step "
            "cost, WU-16 per_horizon_lookahead_cost). Longer horizons buy delayed-collapse visibility at "
            "proportional per-decision cost."
        ),
        "interdependency": (
            "Metric choice, threshold well-posedness, and required horizon are COUPLED: an absolute floor "
            "needs a long horizon to catch this corner but is ill-posed above ~4.16 psi; a relative rule "
            "reacts at short horizon but gives no absolute guarantee."
        ),
    }


def handling_policies(wu15: dict) -> dict:
    """H1/H2/H3 factual descriptions plus the WU-15 measured outputs copied verbatim."""
    return {
        "H1_reject_to_previous": {
            "definition": "On an inadmissible action, execute the previous action a_prev instead.",
            "continuity": "discontinuous (hard switch); introduces proposed != executed.",
            "extra_hydraulic_evals": 0,
        },
        "H2_clip_toward_previous": {
            "definition": "Interpolate a_exec = a_prev + alpha*(a_prop - a_prev) toward previous by an admissible alpha.",
            "alpha_grid_provisional": [0.0, 0.25, 0.5, 0.75, 1.0],
            "continuity": "continuous under clip (preserves a continuous action image).",
            "extra_hydraulic_evals": "one solve per inspected alpha (WU-15 h2_alpha_grid_evals_per_transition=5).",
        },
        "H3_fallback_reference_action": {
            "definition": "On an inadmissible action, execute a documented fallback (reference_nominal native PRV/pump setpoints).",
            "continuity": "discontinuous; introduces proposed != executed.",
            "extra_hydraulic_evals": 0,
        },
        "measured_outputs_wu15": wu15["handling_policy_outputs"],
        "note": (
            "Handling outputs are copied verbatim from WU-15. On the reference->severe transition H1/H3 "
            "reject the full-lower proposal (action_deviation_L2=2.4050194704019527) to a_prev/fallback; "
            "H2 admissible alpha is per-rule. No policy is selected."
        ),
    }


def candidate_configurations() -> list:
    """PROVISIONAL, NOT APPROVED. Four configurations spanning architectures A-D.

    Threshold discipline (do NOT invent thresholds): every threshold below is either a
    value from the WU-15/WU-16 provisional swept grids (labelled 'provisional design
    value - swept, not selected') or an evidence-supported gate (negative pressure,
    baseline count 0). None is fitted, ordered, or marked. These are alternatives that
    populate the decision space, not a shortlist.
    """
    return [
        {
            "config_id": "K1_backstop_plus_relative",
            "status": NOT_APPROVED,
            "architecture": "D (backstop + temporal)",
            "metric_rule": "S4/TS4 negative-pressure hard backstop LAYERED with S2/TS2 worst-node degradation.",
            "threshold": {
                "negative_gate": "N_neg(post)==0 (EVIDENCE-SUPPORTED: baseline negative count 0; only well-posed hard absolute gate).",
                "eps_p_psi": "provisional design value - swept, not selected (grid {0,2,5})",
            },
            "look_ahead_horizon": "provisional - short window swept {1,2,4,8} steps; TS2 reacts at H=1 on the tested corner.",
            "handling_policy": "H2 clip toward previous (continuous) OR H1 reject to a_prev - not selected.",
            "fallback_action": "previous action a_prev.",
            "evidence_basis": "S4 well-posed and inert in-range (WU-14/15); TS2 eps_p=0 activates from H=1 (WU-16).",
            "open_parameters": ["eps_p", "H", "clip-vs-reject"],
        },
        {
            "config_id": "K2_aggregate_deficit_lookahead",
            "status": NOT_APPROVED,
            "architecture": "C (look-ahead + state-degradation)",
            "metric_rule": "S3/TS3 aggregate-deficit increase D(post)-D(base) <= eps_D over a finite window.",
            "threshold": {
                "eps_D_psi_nodesum": "provisional design value - swept, not selected (grid {0,2,5})",
            },
            "look_ahead_horizon": "provisional - swept {1,2,4,8} steps.",
            "handling_policy": "H1 reject to a_prev - not selected.",
            "fallback_action": "previous action a_prev.",
            "evidence_basis": "relative aggregate is baseline-safe (WU-14) but can MASK localised collapse (deficit<->leak corr -0.7735).",
            "open_parameters": ["eps_D", "H", "aggregate-vs-worst-node masking risk"],
        },
        {
            "config_id": "K3_immediate_well_posed_absolute",
            "status": NOT_APPROVED,
            "architecture": "A (immediate rule)",
            "metric_rule": "S1 absolute worst-node floor p_min(post) >= theta_p at the decision instant.",
            "threshold": {
                "theta_p_psi": (
                    "constrained to be well-posed: theta_p must be STRICTLY BELOW the baseline worst node "
                    "~4.16452 psi, else it flags the chronic baseline; at theta_p=0 it degenerates to the "
                    "negative-pressure gate (S4). Grid {0,5,10,15,20} swept, not selected."
                ),
            },
            "look_ahead_horizon": "H=0 (decision instant only); 1 solve.",
            "handling_policy": "H3 fallback reference action - not selected.",
            "fallback_action": "reference_nominal native PRV/pump setpoints.",
            "evidence_basis": "cheapest (1 solve) but blind to the delayed 96 h collapse (decision instant reads 5.53 psi vs 1.29 psi at 96 h).",
            "open_parameters": ["theta_p (bounded < ~4.16 psi for well-posedness)", "delayed-collapse blindness"],
        },
        {
            "config_id": "K4_rolling_absolute_lookahead",
            "status": NOT_APPROVED,
            "architecture": "B (rolling short-horizon look-ahead)",
            "metric_rule": "TS1 absolute worst-node floor min_[0..H] p_min >= theta_p over a rolling window.",
            "threshold": {
                "theta_p_psi": "provisional design value - swept, not selected (grid {0,5,10,15,20}); inherits absolute ill-posedness above ~4.16 psi.",
            },
            "look_ahead_horizon": (
                "provisional - must reach the UNTESTED onset between H=8 (4 h) and full (96 h) to catch the "
                "severe corner under a well-posed theta_p; cost linear in H (full=192x)."
            ),
            "handling_policy": "H1 reject to a_prev OR H2 clip - not selected.",
            "fallback_action": "previous action a_prev.",
            "evidence_basis": "TS1 theta_p=5 misses the severe corner for H<=8 and fires at full (WU-16).",
            "open_parameters": ["theta_p", "H (crossover untested)", "clip-vs-reject"],
        },
    ]


def decision_matrix() -> dict:
    """FACTUAL side-by-side of the four architectures. Rows are NOT ordered, NOT scored,
    NOT marked. Column values are short factual readings of the same evidence."""
    columns = [
        "architecture", "decision_information", "look_ahead_dependence", "threshold_dependence",
        "tank_state_dependence", "baseline_compatibility", "delayed_collapse_visibility",
        "compute_cost_per_decision", "intervention_type", "proposed_vs_executed_mismatch",
        "main_unresolved_issue",
    ]
    rows = [
        {
            "architecture": "A immediate rule",
            "decision_information": "decision-instant post-action state",
            "look_ahead_dependence": "none (H=0)",
            "threshold_dependence": "one of theta_p/eps_p/eps_D/negative-gate",
            "tank_state_dependence": "instant only",
            "baseline_compatibility": "S1 ill-posed >=~4.16 psi; S2/S3/S4 baseline-safe",
            "delayed_collapse_visibility": "none (reads 5.53 psi, misses 1.29 psi at 96 h)",
            "compute_cost_per_decision": "1 solve",
            "intervention_type": "reject/clip at instant",
            "proposed_vs_executed_mismatch": "yes on intervention",
            "main_unresolved_issue": "blind to delayed collapse",
        },
        {
            "architecture": "B rolling absolute look-ahead",
            "decision_information": "worst-node floor over H forward instants",
            "look_ahead_dependence": "finite H (strong)",
            "threshold_dependence": "theta_p (absolute)",
            "tank_state_dependence": "within H-step window",
            "baseline_compatibility": "ill-posed >=~4.16 psi (inherits S1)",
            "delayed_collapse_visibility": "only if H reaches untested onset (8..192 steps)",
            "compute_cost_per_decision": "H solves (full=192x)",
            "intervention_type": "reject/clip on window floor breach",
            "proposed_vs_executed_mismatch": "yes on intervention",
            "main_unresolved_issue": "horizon vs cost vs absolute well-posedness coupled",
        },
        {
            "architecture": "C look-ahead + degradation",
            "decision_information": "post vs aligned-baseline worst-node/deficit over H",
            "look_ahead_dependence": "finite H (reacts at H=1 on tested corner)",
            "threshold_dependence": "eps_p/eps_D (relative)",
            "tank_state_dependence": "post-vs-baseline trajectory over window",
            "baseline_compatibility": "baseline-safe (relative)",
            "delayed_collapse_visibility": "early relative signal; no absolute guarantee",
            "compute_cost_per_decision": "H solves (action + baseline)",
            "intervention_type": "reject/clip on relative degradation",
            "proposed_vs_executed_mismatch": "yes on intervention",
            "main_unresolved_issue": "no absolute floor; aggregate can mask local collapse",
        },
        {
            "architecture": "D backstop + temporal",
            "decision_information": "immediate negative count + windowed worst-node/deficit",
            "look_ahead_dependence": "immediate backstop + finite H layer",
            "threshold_dependence": "negative-gate + theta_p/eps_p/eps_D",
            "tank_state_dependence": "instant backstop + windowed layer",
            "baseline_compatibility": "backstop never fires on baseline; relative layer baseline-safe",
            "delayed_collapse_visibility": "inherits temporal layer's window",
            "compute_cost_per_decision": "1 + H solves",
            "intervention_type": "hard reject on negative; reject/clip on layer breach",
            "proposed_vs_executed_mismatch": "yes on intervention",
            "main_unresolved_issue": "backstop inert in-range; layer still needs A/B/C/D choices",
        },
    ]
    return {"columns": columns, "rows": rows,
            "note": "Descriptive comparison only; rows are NOT ordered or marked; no metric is aggregated into a single figure."}


def _check_constants(wu14: dict, wu15: dict, wu16: dict, wu11: dict) -> dict:
    """Re-check the 5 frozen normalisation constants agree across the artefacts that carry
    the full dict (WU-14 design analysis and WU-11 reward brief). WU-15/WU-16 reference the
    frozen reward by name only (reward_layer_frozen is a label string), so they are recorded
    as name-references, not re-compared numerically."""
    keys = ["leak_ref_gpm", "req_ref_gpm", "deficit_ref_psi_nodesum",
            "power_ref_kw", "movement_L2sq_max"]
    c14 = wu14["normalization_constants_frozen"]
    c11 = wu11["normalization_constants_frozen"]
    match = {k: abs(float(c14[k]) - float(c11[k])) < 1e-9 for k in keys}
    return {
        "constants_checked": keys,
        "match_wu14_vs_wu11": match,
        "all_match": all(match.values()),
        "value": {k: float(c14[k]) for k in keys},
        "wu15_reward_reference": wu15["experiment_metadata"]["reward_layer_frozen"],
        "wu16_reward_reference": wu16["experiment_metadata"]["reward_layer_frozen"],
    }


def _baseline_anchors(wu14: dict) -> dict:
    """Chronic-baseline anchors copied verbatim from WU-14 evidence_loaded."""
    cb = wu14["evidence_loaded"]["chronic_baseline_service_issue"]["baseline_metrics"]
    la = wu14["evidence_loaded"]["leak_only_argmax"]
    return {
        "n_node_timesteps_below_20psi": cb["n_node_timesteps_below_20psi"],
        "n_node_timesteps_negative": cb["n_node_timesteps_negative"],
        "frac_ts_any_node_below_20psi": cb["frac_ts_any_node_below_20psi"],
        "frac_ts_any_node_negative": cb["frac_ts_any_node_negative"],
        "baseline_worst_node_psi": cb["min_service_psi_over_horizon"],
        "leak_only_argmax_config": la["incentive_argmax_config"],
        "leak_only_argmax_on_action_bound": la["argmax_sits_on_action_bound"],
        "leak_only_argmax_worst_node_psi": la["min_service_psi_at_argmax"],
    }


def build_brief() -> dict:
    wu14 = _load(WU14_PATH)
    wu15 = _load(WU15_PATH)
    wu16 = _load(WU16_PATH)
    wu11 = _load(WU11_PATH)

    const_check = _check_constants(wu14, wu15, wu16, wu11)
    anchors = _baseline_anchors(wu14)
    # cross-artefact WU-16 anchor reproduction (decision-instant vs full-horizon worst node)
    sev = wu16["trajectory_metrics"]["prv_lower_pump_lower"]

    brief = {
        "decision_id": DECISION_ID,
        "status": STATUS,
        "title": "STEP-9 state-dependent safety mechanism - decision brief (WU-17)",
        "generated_by": "src/validation/p6_s9_decision_brief.py (WU-17)",
        "measures_nothing_new": True,
        "no_epanet_no_ppo_no_selection": True,
        "no_production_wrapper_implemented": True,
        "purpose": (
            "Aggregate WU-14/WU-15/WU-16 evidence into a decision-ready brief that FRAMES the four "
            "STEP-9 decisions (metric/rule, threshold, look-ahead horizon, action-handling) WITHOUT "
            "making them. The researcher makes the final STEP-9 selection."
        ),
        "the_four_decisions": the_four_decisions(),
        "evidence_artifacts": {
            "wu14_design_analysis": "results/phase6/p6_s9_safety_design_analysis.json",
            "wu15_empirical_characterization": "results/phase6/p6_s9_safety_mechanism_characterization.json",
            "wu16_temporal_characterization": "results/phase6/p6_s9_temporal_safety_characterization.json",
            "reward_brief_wu11": "results/phase6/p6_d_p6_005_decision_brief.json",
            "decision_register": "docs/PHASE6_DECISION_REGISTER.md",
            "step9_safety_design_doc": "docs/PHASE6_STEP9_SAFETY_DESIGN.md",
            "step9_decision_brief_doc": "docs/PHASE6_STEP9_DECISION_BRIEF.md",
        },
        "source_artifact_integrity": {
            "normalization_constants": const_check,
            "chronic_baseline_anchors": anchors,
            "wu16_anchor_reproduction": {
                "severe_p_min_at_decision_instant_psi": sev["p_min_at_decision_instant_psi"],
                "severe_p_min_over_full_horizon_psi": sev["p_min_horizon_psi"],
                "t_pmin_report_index": sev["t_pmin_report_index"],
                "t_pmin_hours": sev["t_pmin_hours"],
                "max_N_neg_over_horizon": sev["max_N_neg"],
            },
            "note": "All numbers copied verbatim from the frozen STEP-9 artefacts; no value is recomputed.",
        },
        "frozen_constraints": wu11["frozen_constraints"],
        "frozen_reward_D_P6_005": {
            "status": "APPROVED & FROZEN (D-P6-005 RESOLUTION 2026-09-27)",
            "formulation": "C-A_F1_balanced_dense (normalized weighted sum)",
            "weights": {"w_L": 1.0, "w_U": 1.0, "w_P": 1.0, "w_A": 0.1, "w_E": 0.0},
            "step9_must_not_modify": (
                "STEP-9 is an EXECUTION-LEVEL admissibility layer and MUST NOT silently change the "
                "reward, observation, or action bounds. Effort term ||da||^2 is defined on the COMMANDED "
                "action; under an intervention the executed action differs (see training_execution_implications)."
            ),
        },
        "normalization_constants_frozen": wu14["normalization_constants_frozen"],
        "metric_definitions": wu15["metric_definitions"],
        "wu14_design_analysis": {
            "safety_candidates": wu14["safety_candidates"],
            "baseline_compatibility_summary": wu14["baseline_compatibility_summary"],
            "design_investigation": wu14["design_investigation"],
            "action_space_coverage": wu14["action_space_coverage"],
        },
        "wu15_empirical_characterization": {
            "candidates": wu15["candidates"],
            "provisional_thresholds": wu15["provisional_thresholds"],
            "safety_rule_outputs": wu15["safety_rule_outputs"],
            "intervention_metrics": wu15["intervention_metrics"],
            "baseline_compatibility": wu15["baseline_compatibility"],
            "severe_degradation_cases": wu15["severe_degradation_cases"],
            "local_collapse_examples": wu15["local_collapse_examples"],
            "computational_cost": wu15["computational_cost"],
            "PPO_compatibility": wu15["PPO_compatibility"],
            "limitations": wu15["limitations"],
        },
        "wu16_temporal_characterization": {
            "temporal_candidates": wu16["temporal_candidates"],
            "horizons_tested": wu16["horizons_tested"],
            "single_step_vs_trajectory": wu16["single_step_vs_trajectory"],
            "trajectory_metrics": wu16["trajectory_metrics"],
            "temporal_rule_outputs": wu16["temporal_rule_outputs"],
            "computational_cost": wu16["computational_cost"],
            "PPO_compatibility": wu16["PPO_compatibility"],
            "limitations": wu16["limitations"],
        },
        "architectures": architectures(),
        "horizon_analysis": horizon_analysis(wu16),
        "handling_policies": handling_policies(wu15),
        "baseline_compatibility": {
            "governing_conclusion": wu14["baseline_compatibility_summary"]["governing_conclusion"],
            "per_candidate_baseline_flag": wu14["baseline_compatibility_summary"]["per_candidate_baseline_flag"],
            "naive_absolute_20psi_reject_is_ill_posed": wu14["baseline_compatibility_summary"]["naive_absolute_20psi_reject_is_ill_posed"],
            "identity_hold_evidence": (
                "WU-16 baseline_identity_hold reproduces the chronic ill-posedness: TS1 at theta_p=20 "
                "activates on the unchanged baseline, TS2 at eps_p=0 never activates. A hard absolute "
                "20-psi gate penalises the native controller itself."
            ),
        },
        "delayed_collapse_analysis": {
            "finding": (
                "On the tested severe corner the worst-node pressure is 5.527866840362549 psi at the "
                "decision instant but collapses to 1.2946763038635254 psi at report index 192 (96 h) as "
                "the tanks drain. This is single-step non-activation followed by delayed deterioration - "
                "NOT a false negative (no safe/unsafe oracle exists)."
            ),
            "no_negative_pressure": (
                "max_N_neg=0 across the entire horizon including the 1.29 psi collapse, so a "
                "negative-pressure backstop (S4/TS4) NEVER fires on any tested command."
            ),
            "implication_for_the_four_decisions": (
                "The metric (A) and horizon (C) decisions are coupled: an immediate or short-horizon "
                "absolute rule cannot see this collapse; a relative-degradation rule flags it early; a "
                "long absolute horizon can see it but is ill-posed above ~4.16 psi and costly."
            ),
            "tank_state_note": (
                "Tank drawdown (WU-16 tank_state_evolution) is COINCIDENT with the collapse; no causal "
                "over-claim is made. Sustained deltas include tank-trajectory divergence (WU-15 limitation)."
            ),
        },
        "computational_cost": {
            "single_step_look_ahead_wu15": {
                "hydraulic_evals_per_proposed_action": wu15["computational_cost"]["hydraulic_evals_per_proposed_action_look_ahead"],
                "h2_alpha_grid_evals_per_transition": wu15["computational_cost"]["h2_alpha_grid_evals_per_transition"],
                "n_epanet_solves_total": wu15["computational_cost"]["n_epanet_solves_total"],
            },
            "per_horizon_look_ahead_wu16": wu16["computational_cost"]["per_horizon_lookahead_cost"],
            "est_wall_s_per_control_step_linear": wu16["computational_cost"]["est_wall_s_per_control_step_linear"],
            "reading": (
                "Immediate (A): 1 solve/decision. Rolling/temporal (B/C/D temporal layer): H solves/decision, "
                "linear in H, full=192x. H2 clip adds one solve per inspected alpha. EPANET is deterministic; "
                "look-ahead adds no stochasticity. Linear split is an approximation (WU-16 note)."
            ),
        },
        "training_execution_implications": {
            "ppo_compatibility_wu15": wu15["PPO_compatibility"],
            "ppo_compatibility_wu16": wu16["PPO_compatibility"],
            "proposed_vs_executed_mismatch": (
                "Any intervention (reject H1 / clip H2 / fallback H3) makes the executed action differ "
                "from the policy's proposed action. WU-15 measures action_deviation_L2=2.4050194704019527 "
                "on the reference->severe reject."
            ),
            "effort_term_open_question": (
                "The FROZEN reward effort term ||da||^2 is defined on the COMMANDED action. Under an "
                "intervention, commanded (proposed) != executed. Whether the effort term (and the env "
                "transition) uses the proposed or the executed action is a training-integration decision "
                "COUPLED to the handling policy; it is flagged here, NOT decided, and does not modify the "
                "frozen reward definition."
            ),
            "continuity": (
                "Clip (H2) preserves a continuous action image (PPO-friendly); reject/fallback (H1/H3) are "
                "discontinuous. The safety layer need not be differentiable (WU-15 PPO_compatibility)."
            ),
            "interval": "All candidates are compatible with the 30-min control interval (WU-15).",
        },
        "candidate_configurations": candidate_configurations(),
        "decision_matrix": decision_matrix(),
        "uncertainties": [
            "No validated safe/unsafe oracle exists: activation counts are DESCRIPTIVE, not false-positive/"
            "false-negative rates (WU-15/WU-16).",
            "R1b: only the single lower corner (prv_lower_pump_lower) has measured near-collapse; interior "
            "points, mixed PRV corners, and joint action x uncertain-demand space are UNCHARACTERISED.",
            "The exact delayed-collapse onset index is not persisted as a per-index series; the crossover "
            "horizon for a well-posed absolute floor lies between H=8 (4 h) and full (96 h) and is UNTESTED.",
            "Sustained/horizon deltas include tank-trajectory divergence and are NOT a strict single-step "
            "look-ahead; only report index 0 is a pure command-effect one-step look-ahead (WU-15).",
            "H2 alpha grid is coarse (0,0.25,0.5,0.75,1.0) and demonstrated on one transition only (WU-15).",
            "The leakage emitter instrument is NOT field-calibrated; leak values are internally consistent "
            "evidence, not calibrated predictions.",
            "Whether the frozen effort term uses the proposed or executed action under intervention is an "
            "open training-integration question coupled to the handling policy.",
            "Thresholds theta_p/eps_p/eps_D are PROVISIONAL swept grids; the leakage<->service<->safety "
            "exchange rate they encode is a researcher value judgement, not a measured quantity.",
        ],
        "coverage": {
            "characterised_region": wu14["action_space_coverage"].get("characterised_region"),
            "unverified_region": wu14["action_space_coverage"].get("unverified_region"),
            "claim_limit": wu14["action_space_coverage"].get("claim_limit"),
            "horizons_characterised_control_steps": [1, 2, 4, 8, 192],
            "intermediate_horizons_untested": [16, 24, 48, 96],
            "no_safe_unsafe_oracle": True,
            "thresholds_swept_not_selected": True,
        },
        "researcher_action_required": {
            "instruction": (
                "The researcher makes the STEP-9 selection: choose/compose the architecture (A/B/C/D), fix "
                "the metric/rule, the threshold, the look-ahead horizon, and the action-handling policy. "
                "This brief does NOT select any of them."
            ),
            "decision_form_blank": {
                "A_architecture": None,
                "B_metric_rule": None,
                "C_threshold": None,
                "D_look_ahead_horizon": None,
                "E_action_handling_policy": None,
                "F_effort_term_action_under_intervention": None,
                "G_rationale": None,
            },
            "status_after_this_brief": "STEP-9 remains PROPOSED / PENDING RESEARCHER; project is NOT PPO-ready.",
        },
        "researcher_selection": None,
    }
    return brief


def _close(x, target: float, tol: float = 1e-9) -> bool:
    return _finite(x) and abs(float(x) - target) < tol


def _self_checks(brief: dict) -> dict:
    """Boolean gate checks. Every check must be True or main() raises SystemExit.

    These enforce the STEP-9 DECISION-GATE prohibitions structurally: no selection,
    no winner/rank/score key, frozen invariants intact, cross-artefact anchors
    reproduced byte-exact, no generated_utc, STEP-9 still PROPOSED / PENDING RESEARCHER.
    """
    checks = {}
    # --- status / non-selection ---
    checks["status_is_proposed"] = brief["status"] == STATUS
    checks["researcher_selection_is_null"] = brief["researcher_selection"] is None
    checks["measures_nothing_new"] = brief["measures_nothing_new"] is True
    checks["no_epanet_no_ppo_no_selection"] = brief["no_epanet_no_ppo_no_selection"] is True
    checks["no_production_wrapper_implemented"] = brief["no_production_wrapper_implemented"] is True
    checks["four_decisions_all_unselected"] = all(
        brief["the_four_decisions"][k]["selection"] is None
        for k in ("A_safety_metric_rule", "B_threshold_tolerance",
                  "C_look_ahead_horizon", "D_action_handling_policy"))
    checks["decision_form_blank_all_none"] = all(
        v is None for v in brief["researcher_action_required"]["decision_form_blank"].values())
    # --- no ranking / scoring / winner language in KEYS ---
    checks["no_verdict_key_top_level"] = not any(
        k in brief for k in ("winner", "selected_architecture", "ranking", "scores", "best", "recommendation"))
    lowered_keys = [str(k).lower() for k in _iter_keys(brief)]
    checks["no_forbidden_key_tokens"] = not any(
        tok in key for key in lowered_keys for tok in FORBIDDEN_KEY_TOKENS)
    # --- frozen invariants ---
    checks["observation_dim_139"] = brief["frozen_constraints"]["observation"]["observation_dim"] == 139
    checks["action_dim_7"] = brief["frozen_constraints"]["action_space"]["action_dim"] == 7
    order = [b["actuator"] for b in brief["frozen_constraints"]["action_space"]["ordered_bounds"]]
    checks["action_ordering_unchanged"] = order == [
        "VALVE-173", "VALVE-175", "VALVE-176", "VALVE-177", "VALVE-178", "PUMP-170", "PUMP-172"]
    checks["service_mask_121_5"] = (
        brief["frozen_constraints"]["service_node_policy"]["n_service_junctions"] == 121
        and brief["frozen_constraints"]["service_node_policy"]["n_connector_junctions_excluded"] == 5)
    checks["frozen_reward_weights"] = brief["frozen_reward_D_P6_005"]["weights"] == {
        "w_L": 1.0, "w_U": 1.0, "w_P": 1.0, "w_A": 0.1, "w_E": 0.0}
    # --- candidate discipline ---
    cfgs = brief["candidate_configurations"]
    checks["all_candidates_not_approved"] = all(c["status"] == NOT_APPROVED for c in cfgs)
    checks["n_candidates_between_2_and_4"] = 2 <= len(cfgs) <= 4
    # --- architectures A-D present on the fixed schema ---
    arch_ids = {a.get("architecture_id") for a in brief["architectures"] if "architecture_id" in a}
    checks["architectures_A_D_present"] = arch_ids == {"A", "B", "C", "D"}
    # --- horizon evidence present ---
    hz = brief["horizon_analysis"]["absolute_floor_TS1_theta_p_5psi_worst_over_window"]
    checks["horizons_present"] = all(h in hz for h in ("H=1", "H=2", "H=4", "H=8", "full"))
    # --- metric definitions carried through ---
    checks["metric_definitions_present"] = len(brief["metric_definitions"]) > 0
    # --- cross-artefact constant + anchor reproduction ---
    checks["constants_match_across_artifacts"] = (
        brief["source_artifact_integrity"]["normalization_constants"]["all_match"] is True)
    consts = brief["normalization_constants_frozen"]
    checks["leak_ref_frozen"] = _close(consts["leak_ref_gpm"], 84.72988433677985)
    checks["req_ref_frozen"] = _close(consts["req_ref_gpm"], 906.3987348621764)
    checks["movement_L2sq_max_frozen"] = _close(consts["movement_L2sq_max"], 28.0)
    anc = brief["source_artifact_integrity"]["chronic_baseline_anchors"]
    checks["baseline_below20_count_386"] = anc["n_node_timesteps_below_20psi"] == 386
    checks["baseline_negative_count_0"] = anc["n_node_timesteps_negative"] == 0
    checks["baseline_worst_node_reproduced"] = _close(anc["baseline_worst_node_psi"], 4.16452169418335)
    checks["leak_argmax_worst_node_reproduced"] = _close(
        anc["leak_only_argmax_worst_node_psi"], 1.2946763038635254)
    rep = brief["source_artifact_integrity"]["wu16_anchor_reproduction"]
    checks["wu16_decision_instant_5p53"] = _close(
        rep["severe_p_min_at_decision_instant_psi"], 5.527866840362549)
    checks["wu16_full_horizon_1p29"] = _close(
        rep["severe_p_min_over_full_horizon_psi"], 1.2946763038635254)
    checks["wu16_max_N_neg_0"] = rep["max_N_neg_over_horizon"] == 0
    # --- byte-reproducibility: no timestamp ---
    checks["no_generated_utc_key"] = not _has_key(brief, "generated_utc")
    # --- finiteness last (whole tree) ---
    checks["all_values_finite"] = _all_finite(brief)
    return checks


def main() -> None:
    brief = build_brief()
    checks = _self_checks(brief)
    brief["self_checks"] = checks
    failed = [k for k, v in checks.items() if not v]
    if failed:
        raise SystemExit(f"STEP-9 decision-brief self-checks FAILED: {failed}")
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(brief, fh, indent=2, ensure_ascii=True)
    print(f"wrote {OUT_PATH}")
    print("self_checks:", json.dumps(checks, indent=1))


if __name__ == "__main__":
    main()
