# PHASE6_EVIDENCE_INDEX.md — Claim → Evidence Map

Every non-trivial Phase 6 claim maps to an on-disk artefact. Columns: Claim ·
File · Section/Key · Result · Interpretation. All values were read from the JSONs
listed, not from memory. (instruction §7)

---

## Reference / network

| Claim | File | Section/Key | Result | Interpretation |
|---|---|---|---|---|
| 121 service junctions, 5 excluded | p6_s3_prv_finechar.json | service_node_policy | connector_nodes = 105/106/109/110/128 | connector artefacts excluded from all stats |
| Nominal reference state | p6_s3_prv_finechar.json | cases.reference_nominal | mean 94.787 psi, min 4.165 @ J-29, 386 ts<20psi, 0 neg, leak 84.730 gpm, DSR 0.98334 | baseline all Phase 6 deltas compare against |
| Working INP hash | p6_s4_pump_strategy.json | env.working_inp_sha256 | 53015ba9…a20a9 (orig 510af942…1956f1) | reproducibility anchor |
| Solver policy asserted | p6_s4_pump_strategy.json | solver_policy | acc 1e-5, trials 2000, rule 180s, report 1800s | non-negotiable config |

## G5 — action space

| Claim | File | Section/Key | Result | Interpretation |
|---|---|---|---|---|
| VALVE-179 safety cliff | p6_s3b_v179_refine.json | highest/lowest_setting… | clean 44.7, last non-neg 44.8, first neg 44.9 | exclude 179; if ever controlled, hard-clamp <=44.7 |
| VALVE-174 adverse reopen | p6_s3_prv_finechar.json | cases.VALVE-174@95/96psi | reopens 95->96 psi | exclude 174 |
| VALVE-180 shut by controls | p6_s3_prv_finechar.json | cases.VALVE-180@*_control_released | control-released cases differ | exclude 180 (native shut) |
| Box constraint sufficient | p6_s3c_zone_interaction.json | box_constraint_sufficient_on_tested_set | true; cases_violating_bound = {} | per-valve clip safe on tested set |
| 5 responsive PRVs (joint) | p6_s3c_zone_interaction.json | joint_responsive_valves / joint_scales | {173,175,176,177,178} at 0.75/0.90/1.00× | admitted set responsive; per-valve bounds still TODO |

## G12 — pump control

| Claim | File | Section/Key | Result | Interpretation |
|---|---|---|---|---|
| SETTING-IS ≠ reopen; STATUS-IS resets speed | p6_s4_pump_strategy.json | reopen_semantics.verdict | setting_is_reopens=False; status_is_open resets speed to 1.0 | neither rule action alone suffices |
| Re-issue holds speed | p6_s4_pump_strategy.json | cases.optionA_reissue_each_step | speed_hold_rate 0.9862 | Option A/C mechanism works |
| Command-once fails | p6_s4_pump_strategy.json | cases.optionA_control_command_first_step_only | speed_hold_rate 0.0172 | must re-issue each step |
| Option B halts sim | p6_s4_pump_strategy.json | cases.optionB_rules_rewritten_stepped | HALTED t=79.5h, unbalanced | Option B disqualified |
| Segmented arch reproduces monolithic | p6_s4_pump_strategy.json | cases.mechanism_check_stepped_native | mean 94.788 vs ref 94.787 | carry-forward validated |

## Pump feasible speed (Phase 5)

| Claim | File | Section/Key | Result | Interpretation |
|---|---|---|---|---|
| PUMP-170 min feasible speed | g3_pump_speed.json | feasible_speed_bounds.PUMP-170 | 0.8152 (shut 0.80, ran 0.85) | lower bound for D-P6-002 |
| PUMP-172 min feasible speed | g3_pump_speed.json | feasible_speed_bounds.PUMP-172 | 0.7655 (shut 0.70, ran 0.80) | lower bound for D-P6-002 |
| No overspeed infeasibility to 1.10 | g3_pump_speed.json | response_summary.*.n_speeds_beyond_curve_qmax | 0 for both | headroom exists if needed |

## Dependencies (this session)

| Claim | Source | Result | Interpretation |
|---|---|---|---|
| DRL deps missing | .venv import check (WU-3) | gymnasium/stable_baselines3/torch/pyyaml MISSING | STEP 11/13 BLOCKED; no auto-install |
| Sim stack present | .venv import check (WU-3) | wntr 1.5.0, epyt 2.3.5.2, numpy 2.5.2, pandas 3.0.5, scipy 1.18.1 | characterization runs OK |

## STEP 6 — per-PRV operating bounds (D-P6-003, PROPOSED)

All rows from `results/phase6/p6_s6_active_prv_bounds.json`. Domains: observed (A) /
hard-safe & service-clean (B) / proposed (C). Bounds PROPOSED — PENDING APPROVAL.

| Claim | Section/Key | Result | Interpretation |
|---|---|---|---|
| Reference nominal reproduced | reference_nominal_case | mean 94.787, min 4.165 @ J-29, 386 <20psi, 0 neg, leak 84.730 | sweep baseline == Phase 5 reference; reproducibility anchor |
| 173 domains + authority | proposed_bounds_table.VALVE-173 / per_valve | obs/safe/svc [5,110]; PROPOSED [5,70]; flow 4.72 gpm; save 0.329%; closes_below_domain | nearly inert; weak actuator in isolation (HYPOTHESIS) |
| 175 domains + authority | proposed_bounds_table.VALVE-175 / per_valve | obs/safe [5,110], svc [21.5,110]; PROPOSED [21.5,55]; flow 362.91 gpm; save 2.222% | strongest actuator; service transition 21.25->21.5 |
| 176 negative cliff | per_valve.VALVE-176.low_side_negative_transition_psi | neg <=12.75, first non-neg 13.0 (bracket 0.25) @ JUNCTION-126 | ONLY hard negative-pressure cliff; hard-safe lower = 13 |
| 176 service + proposed | proposed_bounds_table.VALVE-176 | svc [20,59.524]; PROPOSED [20,29.762]; save 0.746% | service transition 19.75->20.0 |
| 177 domains + authority | proposed_bounds_table.VALVE-177 / per_valve | obs/safe [5,90], svc [20,90]; PROPOSED [20,45]; flow 20.61 gpm; save 0.408% | no negative to 5 psi; service transition 19.75->20.0 |
| 178 domains + authority | proposed_bounds_table.VALVE-178 / per_valve | obs/safe [5,74], svc [20,74]; PROPOSED [20,37]; flow 39.24 gpm; save 0.245% | no negative to 5 psi; service transition 19.75->20.0 |
| Joint lower-corner safe (ONE corner) | cross_actuator_joint_lower_corner | 0 neg, 0 new <20psi, min 4.190 psi, leak 81.383 gpm (−3.347) | validates ONLY the single all-PRVs-at-proposed-lowers corner; NOT the whole 5-D box (mixed corners/interior UNTESTED → STEP-9/STEP-12) |
| Bounds are asymmetric | proposed_bounds_table.* | one-sided [svc-lower, nominal], differ per valve | no shared %-band (§7 satisfied) |

## STEP 6b — focused VALVE-173 low-side refinement (D-P6-003 evidence; NEW file)

All rows from `results/phase6/p6_s6b_v173_lowside_refine.json`. Focused refinement of
the single unmeasured (50,60] coarse-grid bracket; `p6_s6_active_prv_bounds.json`
NOT overwritten (§12). Bounds still PROPOSED — PENDING APPROVAL.

| Claim | Section/Key | Result | Interpretation |
|---|---|---|---|
| Reference reproduced | reference_nominal_case | 386 <20psi, 0 neg, mean 94.787, leak 84.730 | step6b anchored to the same reference; reproducibility confirmed |
| 173 last closed / first active | derived | last fully closed 54.25 psi; first active 54.5 psi; bracket width 0.25 | sharp closed→active step; no partial-activation zone |
| 173 practical regulating lower edge | derived.practical_regulating_lower_edge_psi | 54.5 psi | repo now supports ~55 psi lower bound (was unmeasured 50→60) |
| 173 low side safe but inert | sweep[] | (50,60]: min 4.165 psi, n<20=386 (0 new), 0 neg, leak 84.451→84.554 | weak actuator; safe; ~0.1 gpm leakage span across the bracket |
| A/B/C corrected | activity_definitions + p6_s6 high_side_regulation | A{173:110,175:110,176:59.524,177:90,178:74}; B{173:100, others=cap}; C{173:110 observed, others UNTESTED} | only 173 has an observed Active→Open onset; the four caps are "highest tested regulating", not ceilings |

## Approved action space (D-P6-001/002/003, APPROVED 2026-09-27)

Spec: `docs/PHASE6_ACTION_SPACE_SPEC.md`. Register: APPROVAL section of
`docs/PHASE6_DECISION_REGISTER.md`. State: `PROJECT_STATE.yaml :: action_space.approved`.
The approved *values* are an ENGINEERING DECISION built on the VALIDATED-FACT
measurements already indexed above; this section maps each approved value to that
underlying evidence.

| Approved item | Value | Evidence backing the value |
|---|---|---|
| Encoding (D-P6-001) | ABSOLUTE; `a_i∈[-1,1]`; `physical_i = lower_i + ((a_i+1)/2)*(upper_i-lower_i)` | p6_s4_pump_strategy.json (native STATUS resets speed→1.0 ⇒ absolute robust); ENGINEERING DECISION |
| PRV set | {173,175,176,177,178}; exclude {174,179,180} (kept in model) | p6_s3_prv_finechar.json, p6_s3b_v179_refine.json, p6_s3c_zone_interaction.json |
| VALVE-173 bounds | [54.5, 100.0] psi | p6_s6b_v173_lowside_refine.json (first-active 54.5); p6_s6 high_side_regulation (Active→Open 100→110) |
| VALVE-175 bounds | [21.5, 110.0] psi | p6_s6_active_prv_bounds.json (svc 21.5; cap 110 still Active) |
| VALVE-176 bounds | [20.0, 59.524] psi | p6_s6_active_prv_bounds.json (svc 20; neg-cliff <=12.75; cap 59.524) |
| VALVE-177 bounds | [20.0, 90.0] psi | p6_s6_active_prv_bounds.json (svc 20; cap 90 still Active) |
| VALVE-178 bounds | [20.0, 74.0] psi | p6_s6_active_prv_bounds.json (svc 20; cap 74 still Active) |
| Pump bounds (D-P6-002) | PUMP-170 [0.82,1.10]; PUMP-172 [0.77,1.10] | g3_pump_speed.json (shut-off 0.8152/0.7655; feasible to 1.10) |
| Pump strategy | SPEED only, re-issue each step; native STATUS kept | p6_s4_pump_strategy.json (speed_hold 0.9862 vs 0.0172) |
| Upper-bound terminology | 175/176/177/178 uppers = highest tested REGULATING, NOT ceilings | p6_s6b_v173 activity_definitions; p6_s6 high_side_regulation (four caps still Active) |
| Joint-box safety | single lower-corner only; NOT exhaustive | p6_s6 cross_actuator_joint_lower_corner (ONE corner) → STEP-9/12 |

## STEP 7 — DRL observation / state design (D-P6-004, PROPOSED)

Spec: `docs/PHASE6_STATE_SPEC.md` (§7.1–§7.14). Register: D-P6-004 (PROPOSED) in
`docs/PHASE6_DECISION_REGISTER.md`. State: `PROJECT_STATE.yaml :: state_space` and
`session_checkpoint.step7_2026_09_27`. Design is PROPOSED, layout NOT frozen until
approved. Raw evidence: `results/phase6/p6_s7_state_spec.json`; tests
`tests/test_state_builder.py`.

| Claim | Evidence file | Key |
|---|---|---|
| observation_dim = 139, float32 | p6_s7_state_spec.json | `observation_dim`, `dtype` |
| Block layout (7 blocks, index ranges) | p6_s7_state_spec.json | `block_layout_index_ranges` |
| 121 service nodes, 5 connectors excluded | p6_s7_state_spec.json | `service_node_count`, `connector_nodes_excluded` |
| Tank level bounds (130 [0,32.1], 131 [0,41.9] ft) | p6_s7_state_spec.json | `tank_level_bounds_ft` |
| Approved actuator bounds echoed consistently | p6_s7_state_spec.json | `prv_bounds_psi`, `pump_bounds_rel_speed` |
| Pressure norm band [-20,300] psi | p6_s7_state_spec.json | `pressure_norm_band_psi` |
| Module constants match frozen spec + live INP | p6_s7_state_spec.json | `consistency_with_frozen_spec` (all true) |
| One genuine observation @ t=43200 s, checks pass | p6_s7_state_spec.json | `sample_observation`, `sample_checks` (all true) |
| Deterministic builder, 9-test battery | tests/test_state_builder.py | `discover -s tests` → 9 ok |
| No future information (contract) | tests/test_state_builder.py | test_7_no_future_information |
| Connector exclusion enforced | tests/test_state_builder.py | test_8_connector_exclusion |
| Prev-commanded vs realized kept distinct | tests/test_state_builder.py | test_9_prev_action_semantics |

## STEP 8 — reward-component scale analysis (D-P6-005, PROPOSED)

Spec: `docs/PHASE6_REWARD_SPEC.md` (§8.1–§8.8). Register: D-P6-005 (PROPOSED) in
`docs/PHASE6_DECISION_REGISTER.md`. State: `PROJECT_STATE.yaml :: reward` and
`session_checkpoint`. Raw evidence: `results/phase6/p6_s8_reward_scale_analysis.json`;
generator `src/validation/p6_s8_reward_scale_analysis.py`; tests
`tests/test_reward_scale_analysis.py`. **This step MEASURES only** — no weights
chosen, no PPO trained. 19 static in-bounds configs × 193 report ts = 3667 pooled instants.

| Claim | Section/Key | Result | Interpretation |
|---|---|---|---|
| Per-ts extraction == validated water balance | integrity.per_timestep_vs_validated_accounting_max_abs_diff | 0.0 GPM | reward components read the SAME instrument as Phase-5 accounting |
| Reference reproduces frozen baseline | configurations.reference_nominal.validated_accounting | leak 84.730, DSR 0.98334, 386 ts<20psi, 0 neg | measurement anchored to the frozen reference |
| 10 candidate components, 121 svc / 5 connector | service_node_policy | n_service_junctions 121, n_connector_junctions 5 | safety terms use 121 service nodes only |
| Leakage natural scale | pooled_component_stats.leakage_gpm | mean 84.95, median 84.68, std 2.52, [79.92, 90.15] | narrow ±~6% band → baseline-relative/normalised objective |
| Requested-demand scale | pooled_component_stats.requested_demand_gpm | median 774.0 (mean 906.4) | ~10× leakage → raw sum dominated by demand |
| DSR discriminating | pooled_component_stats.dsr | mean 0.9734, [0.9142, 1.00246] | dense usable service signal (clip unserved≥0) |
| Pressure deficit scale | pooled_component_stats.pressure_deficit_psi_nodesum | mean 19.86, max 31.73 | dense safety signal |
| Min service pressure | pooled_component_stats.min_service_pressure_psi | mean 4.77, [1.09, 5.93] | worst-node dense safety signal |
| Hard-violation degenerate | pooled_component_stats.n_service_nodes_negative | identically 0 (frac_zero 1.0) | pure hard-violation term sparse → dense safety needed |
| Pump power bimodal | pooled_component_stats.pump_hydraulic_power_kw | mean 79.85, median 0.0, max 323.6 | native-STATUS-driven; energy term optional, hydraulic-only |
| Objectives oppose | cross_component_correlation | leak↔dsr +0.750, leak↔deficit −0.774, leak↔n_below20 −0.742, dsr↔deficit −0.965 | pressing leakage down erodes service → protect service explicitly |
| Leakage-only collapses service | pathology_checks (prv_all_lower) | leak 84.73→81.38 (−4.0%), DSR 0.98334→0.91940 (−6.4 pts) | leakage-only unsafe |
| Pressure-only raises leakage | pathology_checks (prv_all_upper) | leak 84.73→89.76 (+5.9%), n_below20 386→193 | objectives oppose |
| Scale imbalance | pathology_checks | penalty-term median max/min ratio 7.15 | fixed normalisation mandatory |
| Actuator effort (analytic) | actuator_effort_analytic | dim 7, L1 max 14.0, L2² max 28.0, L2 max 5.2915 | static runs = 0 movement → analytic ceiling; effort ÷ 28 |
| Boundary-seeking optimum | pathology_checks | leak optimum at PRV lower bound; worst pooled min svc 1.09 psi | STEP-9 hard clamp REQUIRED |
| Fixed normalisation constants | proposed_normalization_constants | leak_ref 84.72988, req_ref 906.39873, deficit_ref 28.67179, power_ref 88.10062, L2sq_max 28.0 | frozen once, no running stats → no train/eval leakage |
| 4 formulations all PROPOSED | proposed_formulations[].status | F1 norm-weighted-sum, F2 constrained-penalty, F3 baseline-relative, F4 safety-first-lexicographic | none selected; weights NOT chosen |
| Determinism + integrity | integrity | all finite; no topology/native-rule change; no future info; native controls unchanged | reproducible, no leakage |
| Test battery | tests/test_reward_scale_analysis.py | 12 STEP 8 + 9 STEP 7 = 21/21 ok | pure helpers + artefact checks |

## STEP 8 — reward-formulation comparison (D-P6-005 evidence, PROPOSED)

Spec: `docs/PHASE6_REWARD_SPEC.md` §8.9–§8.11. Register: D-P6-005 comparison-evidence
note (status UNCHANGED — still PROPOSED). Raw evidence:
`results/phase6/p6_s8_reward_formulation_comparison.json`; generator
`src/validation/p6_s8_reward_formulation_comparison.py`; tests
`tests/test_reward_formulation_comparison.py`. **Comparison only — no formulation
selected/scored/ranked, no weights tuned, no STEP-9 clamp, no PPO.** Same 19 static
in-bounds commands × 193 report ts as the WU-9 measurement; frozen constants loaded
from the WU-9 artefact.

| Claim | Section/Key | Result | Interpretation |
|---|---|---|---|
| Reproduces frozen baseline exactly | reproducibility_information.reference_reproduces_frozen_baseline | leak_ref_abs_diff 0.0, req 0.0, below20 386, neg 0, per-ts vs accounting 0.0 | comparison anchored to the validated instrument; no drift |
| Provisional params labelled comparison-only | provisional_parameters | F1 w_·=1/w_E=0; F2 Λ=20,BIG=100; F3 w_U=w_P_safety=1; F4 θ=20,c_soft=10,c_hard=100 | illustrative constants, NOT proposed weights |
| Induced incentive (all four) | induced_incentive_per_formulation | argmax = `prv_176_upper` for F1/F2/F3/F4; spreads F1 0.541 / F2 110.5 / F3 0.525 / F4 0.526 | incentive-direction indicator, NOT a formulation ranking |
| Leak-only collapses service (A) | pathology_results.A_leakage_only_collapses_service | argmax `prv_lower_pump_lower`, min svc 1.295 psi (ref 4.165) | leakage-driving incentive → PRV lower corner, unsafe worst-node |
| Service-only raises leakage (B) | pathology_results.B_service_only_raises_leakage | argmax `prv_176_upper`, leak_norm 1.0155 (ref 1.0) | objectives oppose (consistent with WU-9 correlations) |
| Actuator-penalty domination (C) | pathology_results.C_actuator_penalty_domination | leak-term range 0.108 vs max move cost 1.0 (w_A=1) | un-tuned effort weight could dominate leakage; ANALYTIC (da=0 in statics) |
| Boundary-seeking (D) | pathology_results.D_boundary_seeking_per_formulation | all argmax on_bound=True, min svc 4.166, n_below20 1.0 | provisional-weight incentive sits on a bound → STEP-9 clamp required |
| Flat/weak signal (E) | pathology_results.E_flat_or_weak_signal_per_formulation | within-config std F1 0.032 / F3 0.030 / F4 0.023 / F2 2.55 | reward varies mostly across commands, little within a static hold |
| Sparse/degenerate violation (F) | pathology_results.F_sparse_or_degenerate_violation_signal | frac<20psi 1.0, frac<0psi 0.0, ref n_below20 2.0 | hard-20 term fires on baseline; <0 term never fires in-bounds |
| Reward-hacking / degeneracy (G) | pathology_results.G_reward_hacking_and_degeneracy | hard-20 ill-posed; θ=0 permissive; effort must use COMMANDED action | formulation-design considerations for D-P6-005 |
| Weight/penalty sensitivity (H) | sensitivity_results | F1 w_P 0→`prv_175_lower`, ≥0.5→`prv_176_upper`; F4 θ 0↔20 flips argmax | incentive shifts with parameters → selection is the researcher's |
| Analytic effort probe | actuator_effort_analytic | dim implied 7, L2sq_max 28, max-move norm 1.0, static-hold norm 0.0 | effort ÷ 28; realised distribution is a training-time HYPOTHESIS |
| Test battery | tests/test_reward_formulation_comparison.py | 23 comparison ok; full battery 44/44 | normalization/signs/branches/mask/reproducibility/no-future-info |

## STEP 8 — D-P6-005 reward decision brief (WU-11, D-P6-005 PROPOSED / DECISION PENDING RESEARCHER)

Doc: `docs/PHASE6_D_P6_005_DECISION_BRIEF.md` (11 sections; researcher decision block BLANK).
Register: D-P6-005 decision-brief note (status UNCHANGED — still PROPOSED). Raw artefact:
`results/phase6/p6_d_p6_005_decision_brief.json` (**researcher_selection=null**); generator
`src/validation/p6_d_p6_005_decision_brief.py`; tests `tests/test_decision_brief.py`.
**Decision-gate PREP only — no formulation selected/scored/ranked, no weights tuned, no
STEP-9 clamp, no PPO.** Pure aggregator of the WU-9 + WU-10 artefacts: no EPANET, no PPO,
no RNG, no new measurement.

| Claim | Section/Key | Result | Interpretation |
|---|---|---|---|
| Brief keeps D-P6-005 PROPOSED, no selection | status / researcher_selection | status "PROPOSED / DECISION PENDING RESEARCHER"; researcher_selection null; no winner/ranking/scores keys | AI prepares the gate; the researcher makes the scientific decision |
| Frozen normalisation reused without drift | normalization_constants_frozen / _match_across_artifacts | leak 84.72988, req 906.39873, deficit 28.67179, power 88.10062, L2sq 28.0; cross-artefact abs diff <1e-9 (all true) | no online/running/test-set stats; no data leakage; matches WU-9 |
| Frozen constraints untouched | frozen_constraints | action_dim 7 + ordered bounds [173,175,176,177,178,170,172]; observation_dim 139; service mask 121/5; solver policy | reward brief does NOT reopen D-P6-001/002/003 or D-P6-004 |
| Four provisional candidates, all NOT APPROVED | candidate_parameterizations | C-A/C-B F1 (w_A=0.1 from measured 0.108 leak range); C-C F3 baseline-relative; C-D dense deficit + negative-only hard gate {Λ=5,BIG=100} | constants traced to measured scales, NOT tuned to a preferred result |
| Chronic sub-20-psi baseline → hard 20-psi ill-posed | chronic_baseline_service_issue | frac_ts_any_node_below_20psi 1.0; frac_ts_any_node_negative 0.0; "ILL-POSED" | no formulation can use a hard absolute 20-psi reward constraint without penalising the baseline; use dense deficit / worst-node / baseline-relative / negative-only gate |
| Reward vs STEP-9 separation | safety_dependencies | reward shaping (D-P6-005) DISTINCT from the enforced clamp (STEP-9) | the enforced 20-psi guarantee is STEP-9's, not the reward's |
| Deterministic regeneration | (test) test_17 | rebuilt JSON byte-reproduces the on-disk artefact | reproducible; no RNG / running stats |
| Test battery | tests/test_decision_brief.py | 19 decision-brief ok; full battery 63/63 | status/null-selection/no-ranking/finite/constants/action-order/obs-dim/service-mask/candidates/reproducibility/integrity |

## STEP 8 — D-P6-005 researcher summary (WU-12, D-P6-005 PROPOSED / DECISION PENDING RESEARCHER)

Doc: `docs/PHASE6_D_P6_005_RESEARCHER_SUMMARY.md` (§A–§H; researcher §G decision form BLANK).
State: `PROJECT_STATE.yaml :: reward.researcher_summary` and `session_checkpoint`. Raw artefact:
`results/phase6/p6_d_p6_005_researcher_summary.json` (**researcher_selection=null**); generator
`src/validation/p6_d_p6_005_researcher_summary.py`; tests `tests/test_researcher_summary.py`.
**Presentation only — no formulation selected/scored/ranked/recommended, no weights, no STEP-9
clamp, no reward.py, no PPO.** PURE re-shaping of the WU-11 brief: no EPANET, no PPO, no RNG, no
new measurement; every equation/constant/weight copied verbatim (only Persian/English prose authored).

| Claim | Section/Key | Result | Interpretation |
|---|---|---|---|
| Summary keeps D-P6-005 PROPOSED, no selection | current_status / researcher_selection | current_status "PROPOSED / DECISION PENDING RESEARCHER" (== brief status); researcher_selection null; no winner/rank/tier/score keys | AI presents the gate; the researcher makes the scientific decision |
| Four candidates copied verbatim, all NOT APPROVED | candidate_formulations[] | ids C-A/C-B/C-C/C-D; each status "PROVISIONAL CANDIDATE - NOT APPROVED"; equation/constants/weights/base_formulation == WU-11 brief | anti-drift: numeric fields re-loaded from the brief, not re-authored |
| Two DISTINCT unserved_ref values preserved | candidate_parameters."C-C…".normalization_constants / formulation_families F3.baseline_constants | C-C DSR-implied 15.103309701248634 vs F3 accounting 14.98483697365873 (NOT conflated) | each reported exactly as in the brief |
| Frozen constants unchanged | normalization_constants_frozen | leak_ref 84.72988433677985, movement_L2sq_max 28.0 (== brief) | reward presentation does NOT reopen STEP 8 constants |
| Frozen constraints unchanged | frozen_constraints_snapshot | action_dim 7 + excluded {174,179,180}; observation_dim 139; service mask 121/5 | does NOT reopen D-P6-001/002/003 or D-P6-004 |
| Plain-language Persian per candidate | candidate_formulations[].plain_language_fa | four questions q1_encourages / q2_leak_down_service_down / q3_pressure_up / q4_action_moves_a_lot (C-C/C-D q4 = NOT SPECIFIED IN SOURCE) | descriptive, no recommendation |
| No forbidden key tokens | self_checks.no_forbidden_key_tokens | true (scan for winner/rank/tier/score/best/superior/optimal/preferred/recommend) | no ranking/winner language anywhere |
| Deterministic regeneration | (test) test_20 | rebuilt JSON byte-reproduces the on-disk artefact | reproducible; no RNG / running stats |
| Test battery | tests/test_researcher_summary.py | 21 researcher-summary ok; full battery 84/84 | load/decision-id/status/null-selection/candidate-ids/not-approved/numbers-match-brief/unserved-ref-distinct/frozen-constants/no-forbidden-tokens/action-space/obs-dim/service-mask/families/plain-language/no-topology-change/finite/self-checks/byte-reproduce/evidence-refs |

## Still-missing evidence (drives next action)

| Needed claim | Why missing | How to obtain |
|---|---|---|
| Joint 5-D action-box safety (mixed corners/interior/pump+demand) | only single lower-corner tested (R1b) | STEP 9 safety layer + STEP 12 automated joint tests |
| Reward formulation + weights (D-P6-005 selection) | **OBTAINED 2026-09-27 (WU-13): D-P6-005 = APPROVED, C-A_F1_balanced_dense (F1, w_L=1.0,w_U=1.0,w_P=1.0,w_A=0.1,w_E=0.0)** | recorded in `PROJECT_STATE.yaml :: reward.approved` + `docs/PHASE6_DECISION_REGISTER.md` (D-P6-005 RESOLUTION) + §11/§G banners in the two decision docs; STEP 11 implements `src/env/reward.py` (deps-blocked) |
| Realised actuator-movement distribution | static runs = 0 movement; effort scale is analytic (R5-effort, HYPOTHESIS) | measured at training time once a policy trajectory exists |
| Leak calibration | instrument uncalibrated (R3) | out of Phase 6 scope; relative response only |
| Observation/state design | DELIVERABLES PRODUCED; D-P6-004 PROPOSED — awaiting researcher approval (not frozen) | researcher sign-off on the 5 review points → freeze 139-dim layout |

## STEP 8 — D-P6-005 RESOLUTION (WU-13, APPROVED 2026-09-27 — C-A_F1_balanced_dense)

Researcher decision recorded (AI did not select). Authoritative records:
`PROJECT_STATE.yaml :: reward.approved` and `docs/PHASE6_DECISION_REGISTER.md` (D-P6-005
RESOLUTION). Human-readable forms filled: `docs/PHASE6_D_P6_005_DECISION_BRIEF.md` §11 and
`docs/PHASE6_D_P6_005_RESEARCHER_SUMMARY.md` §G (RESOLUTION banners added). The WU-11/WU-12
generated JSON snapshots + generators + byte-reproduction tests are **retained UNCHANGED**
(still PROPOSED / researcher_selection=null) as frozen pre-decision evidence (CLAUDE.md §11/§12).

| Claim | Source | Value | Interpretation |
|---|---|---|---|
| Selected formulation | reward.approved.selected_candidate / formulation | C-A_F1_balanced_dense — F1 normalized weighted sum | one dense negative-cost reward (higher = better) |
| Approved weights | reward.approved.weights | w_L=1.0, w_U=1.0, w_P=1.0, w_A=0.1, w_E=0.0 | leakage + unserved + deficit protected equally; effort lightly regularised; energy off but explicit |
| Approved equation | reward.approved.equation | r_t = -w_L(leak/leak_ref) -w_U(unserved⁺/req_ref) -w_P(deficit/deficit_ref) -w_A(‖da‖²/movement_L2sq_max) -w_E(power/power_ref) | unserved⁺=max(0,unserved); da on COMMANDED normalised actions (static → 0) |
| Frozen constants (adopted as-is) | reward.approved.frozen_normalization_constants | leak_ref 84.72988433677985, req_ref 906.3987348621764, deficit_ref 28.671793365478514, power_ref 88.10062475649187, movement_L2sq_max 28.0 | byte-identical to WU-9 and to brief `normalization_constants_frozen`; no drift |
| Consistency vs frozen repo | reward.approved.consistency_check | equals `candidate_parameterizations[C-A]` (w_A=0.1,w_E=0.0) exactly | §1 "do not alter unless contradiction" satisfied — no contradiction found |
| Unselected candidates retained | reward.approved.unselected_candidates_retained | C-B (w_P=2.0), C-C (F3), C-D — not deleted | decision history preserved |
| C-C unserved_ref debt | reward.approved.c_c_unserved_ref_debt | 15.103309701248634 (DSR-implied) vs 14.98483697365873 (F3 accounting) preserved distinct | non-blocking (F1/C-A does not use unserved_ref) |
| Rationale scope | reward.approved.rationale_factual | specific to this thesis env/design; no best/optimal/superior/winner; no ranking | approval is scoped, not a universal claim |

## STEP 9 — state-dependent safety-mechanism DESIGN ANALYSIS (WU-14, IN PROGRESS 2026-09-27)

Doc: `docs/PHASE6_STEP9_SAFETY_DESIGN.md`. Raw artefact:
`results/phase6/p6_s9_safety_design_analysis.json`; generator
`src/validation/p6_s9_safety_design_analysis.py`; tests `tests/test_safety_design_analysis.py`.
**Characterisation only — candidates NOT ranked, no production wrapper implemented, no reward.py,
no PPO.** Pure aggregator: RE-LOADS measured evidence (no new EPANET / PPO / RNG).

| Claim | Section/Key | Result | Interpretation |
|---|---|---|---|
| Naive absolute min<20 reject is ill-posed | baseline_compatibility / chronic_baseline | 386 node-ts <20psi, 0 negative, frac_ts_any<20psi 1.0, min svc 4.16452 psi | a rule that rejects any sub-20 state would reject the native baseline itself |
| Leakage-driven behaviour endangers service | evidence_loaded.leak_only_min_service | min svc 1.2946763038635254 psi at `prv_lower_pump_lower` | motivates a state-dependent safety mechanism distinct from the reward |
| Four candidate mechanisms characterised (not ranked) | safety_candidates[] | S1 absolute worst-node threshold; S2 min-pressure degradation vs current; S3 deficit increase; S4 negative-pressure hard backstop | each on an 11-field schema; NO ranking/winner/score |
| Baseline-compatibility verdicts | baseline_compatibility[] | per-candidate: does it falsely flag the chronic-sub-20 baseline as unsafe? | S1@20 flags baseline; S4 (negative-only) does not; S2/S3 depend on reference |
| Action-space coverage limits | action_space_coverage | single lower-corner only (R1b); interior/mixed corners/pump+demand unverified | do not claim the 7-D box globally safe |
| Frozen invariants unchanged | frozen_constraints_snapshot | action_dim 7; observation_dim 139; service mask 121/5; bounds/ordering/native rules/leak instrument | STEP-9 is an external layer; no topology/native-rule change |
| Determinism | self_checks / (test) byte-reproduce | rebuilt JSON byte-reproduces the artefact; all values finite; no forbidden key tokens | reproducible; no RNG |
| Test battery | tests/test_safety_design_analysis.py | STEP-9 tests + prior 84 full battery | schema/finite/no-ranking/D-P6-005-consistency/frozen-invariants/byte-reproduce |

## STEP 9 — empirical characterisation of candidate mechanisms & handling policies (WU-15, 2026-09-28)

Doc: `docs/PHASE6_STEP9_SAFETY_DESIGN.md` §10.1-10.9. Raw artefact:
`results/phase6/p6_s9_safety_mechanism_characterization.json`; generator
`src/validation/p6_s9_safety_mechanism_characterization.py`; tests
`tests/test_safety_mechanism_characterization.py` (26). Committed e09264c/0ed1c9e.
**EVIDENCE ONLY — nothing selected/ranked/scored/recommended (researcher_selection=null).** Reuses the
WU-8 instrument unchanged (10 EPANET solves); descriptive activation only (no FP/FN — no oracle); JSON
carries `generated_utc` (NOT byte-reproduced; EPANET-deterministic values do reproduce).

| Claim | Section/Key | Result | Interpretation |
|---|---|---|---|
| Decision-instant vs sustained gap | single_step_vs_trajectory (severe) | worst-node ~5.53 psi at shared-initial vs ~1.29 psi sustained | a single-step look-ahead understates sustained danger |
| Only S2@ε=0 separates severe from intermediate | most_important_question | razor-thin ~0.01 psi margin at one instant | not claimed to generalise |
| S4 never fires on measured evidence | safety_rule_outputs / S4 | 0 negative-pressure nodes in every swept config | negative backstop gives no 20-psi protection standalone |
| Chronic-baseline ill-posedness on identity hold | baseline_compatibility | S1@20 activates 1.0; S2/S3/S4 activate 0.0 | hard absolute-20 penalises the baseline; relative/negative gates compatible |

## STEP 9 — TEMPORAL characterisation: single-step vs trajectory-aware safety (WU-16, 2026-09-28)

Doc: `docs/PHASE6_STEP9_SAFETY_DESIGN.md` §11. Raw artefact:
`results/phase6/p6_s9_temporal_safety_characterization.json`; generator
`src/validation/p6_s9_temporal_safety_characterization.py`; tests
`tests/test_temporal_safety_characterization.py` (20). Committed 6bf4820 (+ checkpoint).
**EVIDENCE ONLY — no mechanism, handling policy, or look-ahead HORIZON selected/ranked/scored/
recommended (researcher_selection=null).** Reuses the WU-8 instrument + WU-15 module unchanged (3 full
96h EPS solves); reproduces the WU-15 5.53/1.29 anchors from persisted data (abs diff 0.0); JSON carries
`generated_utc` (NOT byte-reproduced; EPANET-deterministic values do reproduce). No wrapper, no
reward.py, no PPO.

| Claim | Section/Key | Result | Interpretation |
|---|---|---|---|
| Severe collapse is late in the horizon | trajectory_metrics.prv_lower_pump_lower | p_min_horizon 1.2947 psi at report index 192 = 96.0h (END); decision instant 5.5279 psi; understatement 4.23 psi | any finite look-ahead shorter than full understates it |
| Short look-ahead misses it (central finding) | temporal_rule_outputs / TS1 θ_p=5 | worst p_min H=1/2/4/8 = 5.4615/5.4045/5.3083/5.1472; activates false for H≤8, true only at full | single-step non-activation followed by delayed deterioration (NOT false negative) |
| First sub-θ_p=5 instant beyond short horizons | horizon_pmin_sweep (severe) | first index below θ_p=5 at report index 13 = 6.5h | > H=8 (4h): a ≤4h look-ahead keyed to 5 psi stays quiet |
| Relative worst-node guard more temporally sensitive | temporal_rule_outputs / TS2 ε_p=0 | activates at every horizon incl. H=1 (worst Δp_min −0.097 → −4.30) | reported as measured behaviour, not a virtue |
| Negative backstop never fires | temporal_rule_outputs / TS4 | max_N_neg 0 at every horizon, every config | no 20-psi protection standalone |
| Chronic ill-posedness over the horizon | temporal_rule_outputs / baseline_identity_hold | TS1@20 activates (worst 4.16452 psi); TS2@0 never | hard absolute-20 window gate penalises baseline; relative compatible |
| Tank drawdown coincident with collapse | tank_state_evolution.prv_lower_pump_lower | TANK-130 −9.79 ft, TANK-131 −12.74 ft by t_pmin | coincident, NO causal overclaim |
| Native pump-rule events | native_rule_events | 0 (severe) vs 14 (reference / prv_all_lower) | severe pumps held at reduced fixed speed, never toggle |
| WU-15 anchors reproduced | wu15_delayed_collapse_reproduction | 5.5279 / 1.2947 psi, abs diff 0.0; normalized action [-1]×7 exact | deterministic reproduction from persisted data |
| Frozen invariants unchanged | experiment_metadata | action_dim 7; observation_dim 139; service mask 121/5; 193 instants; ts 1800s; n_native 5 | temporal layer; no topology/native-rule change |
| Test battery | tests/test_temporal_safety_characterization.py | 20 new; full battery 145 OK | keys/finite/no-forbidden-tokens/researcher_selection-null/frozen-dims/WU-15-repro/central-finding |

## STEP 9 — SAFETY DECISION BRIEF: framing the four STEP-9 decisions (WU-17, 2026-09-28)

Doc: `docs/PHASE6_STEP9_DECISION_BRIEF.md` (17 sections; §17 researcher decision block BLANK). Raw
artefact: `results/phase6/p6_s9_decision_brief.json` (researcher_selection=null); generator
`src/validation/p6_s9_decision_brief.py`; tests `tests/test_step9_decision_brief.py` (26). Committed
58e1790 (+ checkpoint). **DECISION-GATE PREP — FRAMES the four STEP-9 decisions (A metric/rule;
B threshold; C look-ahead horizon; D action-handling policy) WITHOUT making any (nothing selected/
ranked/scored/recommended; researcher_selection=null).** PURE AGGREGATOR: re-loads the four frozen JSON
artefacts (WU-14 + WU-15 + WU-16 + WU-11 reward brief), copies evidence sub-trees verbatim, re-checks
the 5 frozen normalisation constants + cross-artefact anchors; runs NO EPANET/PPO/RNG; carries NO
`generated_utc`; byte-reproduces on re-run (verified by test). STEP-9 stays PROPOSED / PENDING
RESEARCHER; project NOT PPO-ready. No wrapper, no reward.py, no PPO.

| Claim | Section/Key | Result | Interpretation |
|---|---|---|---|
| Four decisions framed, none made | the_four_decisions / researcher_selection | A/B/C/D each `selection:null`; top-level `researcher_selection:null` | decision gate prepared, not resolved |
| Four candidate configurations, all unapproved | candidate_configurations[] | K1 (D backstop+relative), K2 (C aggregate-deficit), K3 (A immediate absolute), K4 (B rolling absolute look-ahead), each `status:"PROVISIONAL CANDIDATE - NOT APPROVED"` | populate the decision space; NOT a shortlist |
| Decision matrix is neutral | decision_matrix | 4 rows A-D; note "rows are NOT ordered or marked"; no metric aggregated to a single figure | no winner/rank/score |
| No selection language anywhere | self_checks.no_forbidden_key_tokens | KEY scan for winner/rank/tier/score/best/superior/optimal/preferred/recommend = [] | brief cannot smuggle a recommendation |
| Frozen invariants unchanged | frozen_constraints / frozen_reward_D_P6_005 / normalization_constants_frozen | action_dim 7; observation_dim 139; service 121/5; reward weights w_L/w_U/w_P/w_A/w_E; 5 constants byte-identical | STEP-9 is an admissibility layer; changes nothing frozen |
| Central delayed-collapse evidence carried | source_artifact_integrity.wu16_anchor_reproduction | 5.527866840362549 psi at decision instant → 1.2946763038635254 psi over full horizon; max_N_neg 0 | metric (A) and horizon (C) decisions are coupled |
| Chronic-baseline ill-posedness carried | baseline_compatibility / chronic_baseline_anchors | 386 sub-20 node-ts; worst 4.16452 psi; 0 negative | a hard absolute-20 reject penalises the native controller itself |
| Determinism | self_checks / test_deterministic_rebuild_matches_persisted_bytes | in-memory rebuild byte-equals the persisted artefact; all 32 self-checks true; all numbers finite | reproducible aggregation; no RNG, no timestamp |
| Test battery | tests/test_step9_decision_brief.py | 26 new; full battery 171 OK | required-keys/null-selection/no-forbidden-tokens/frozen-invariants/verbatim-rules/anchors/rebuild-equals-bytes |

## STEP 9 — FINAL SAFETY-ARCHITECTURE DECISION REVIEW: readiness judgement + final-design packaging (WU-18, 2026-09-28)

Doc: `docs/PHASE6_STEP9_FINAL_DECISION_REVIEW.md` (18 sections; §18 researcher decision form D-P6-006 BLANK). Raw
artefact: `results/phase6/p6_s9_final_decision_review.json` (16 top-level keys; researcher_selection=null); generator
`src/validation/p6_s9_final_decision_review.py`; tests `tests/test_step9_final_decision_review.py` (28). Committed
2291cce (+ checkpoint). **FINAL REVIEW before production wrapper — JUDGES decision-readiness and PACKAGES the <=3
final PROVISIONAL designs WITHOUT selecting a mechanism/threshold/horizon/handling policy (nothing selected/ranked/
scored/recommended; researcher_selection=null; BLANK D-P6-006 form).** PURE AGGREGATOR: re-loads the frozen WU-14 +
WU-15 + WU-16 + WU-17 + WU-11 artefacts, copies evidence sub-trees verbatim, re-checks the 5 frozen normalisation
constants + cross-artefact anchors; runs NO EPANET/PPO/RNG; carries NO `generated_utc`; byte-reproduces on re-run
(verified by test). STEP-9 stays PROPOSED / PENDING RESEARCHER; project NOT PPO-ready; no D-P6-006 minted. No wrapper,
no reward.py, no PPO.

| Claim | Section/Key | Result | Interpretation |
|---|---|---|---|
| Decision is READY, not made | decision_readiness | readiness_verdict `DECISION-READY`; `verdict_is_not_a_selection:true`; status reaffirms STEP-9 PROPOSED | the four decisions are fully framed with reproducible evidence; remaining unknowns are researcher value judgements or accepted STEP-12 limits |
| Three final designs, unordered, unapproved | final_provisional_designs.designs[] | F1 (arch D backstop+relative), F2 (arch B rolling absolute look-ahead subsuming A), F3 (arch C aggregate-deficit), each `status:"PROVISIONAL - NOT APPROVED"` | `not_ordered_by_quality:true`, `order_is_definitional_not_quality:true` — definitional order carries NO quality judgement |
| No selection language anywhere | self_checks / no_forbidden_key_tokens | KEY scan for winner/rank/tier/score/best/superior/optimal/preferred/recommend = [] | the review cannot smuggle a recommendation; researcher_selection=null |
| WU-17 crossover slip CORRECTED (TRUST DISK) | horizon_analysis.crossover_onset_correction | supersedes `wu17.horizon_analysis.crossover_interval_untested`; θ_p=5 onset PERSISTED at report index 13 (6.5h); control_steps 13 | the delayed-collapse onset is a KNOWN quantity from `first_report_index_below_theta_p`, not "untested" |
| Smallest sufficient absolute-floor horizon carried on F2 | final_provisional_designs.designs (F2) | `smallest_sufficient_H_for_theta_p_5_report_index:13` | an absolute θ_p=5 floor on the severe corner needs H ≥ 13 control steps (6.5h) |
| Useful absolute-20 floor NOT justified | threshold_analysis.absolute_floor_theta_p_psi | `useful_20psi_floor_status:"THRESHOLD NOT YET EMPIRICALLY JUSTIFIED"`; negative gate `EVIDENCE-SUPPORTED` | only N_neg==0 is an evidence-supported hard threshold; a useful 20-psi floor flags the chronic baseline |
| Central collapse anchors reproduced | evidence.central_anchors | baseline worst 4.16452169418335 psi; severe decision-instant 5.527866840362549 psi; full-horizon 1.2946763038635254 psi; max_N_neg 0 | full-horizon worst < decision-instant worst — the delayed collapse an immediate rule is blind to |
| Frozen invariants unchanged | frozen_invariants | action_dim 7 + ordered bounds; observation_dim 139; reward weights w_L/w_U/w_P/w_A/w_E + 5 constants byte-identical | STEP-9 is an admissibility layer; changes nothing frozen |
| Researcher form BLANK | researcher_action_required.decision_form_blank | 7 fields A_architecture..G_rationale all null | completing + approving it mints D-P6-006; this review does NOT fill it |
| Determinism | self_checks / test_deterministic_rebuild_matches_persisted_bytes | in-memory rebuild byte-equals the persisted artefact; all 31 self-checks true; all numbers finite | reproducible aggregation; no RNG, no timestamp |
| Test battery | tests/test_step9_final_decision_review.py | 28 new; full battery 199 OK | required-keys(16)/null-selection/no-forbidden-tokens/frozen-invariants/verbatim-rules/anchors/crossover-correction/blank-form/rebuild-equals-object+bytes |

## STEP 9 — D-P6-006 FINALIZED: execution-safety / admissibility layer (WU-19, 2026-10-01)

Authoritative record: `docs/PHASE6_DECISION_REGISTER.md` entry **D-P6-006 — FINALIZED 2026-10-01** (Form A–G).
Supporting human-readable docs: `docs/PHASE6_STEP9_SAFETY_DESIGN.md` §12 (WU-19 finalization), `docs/PHASE6_STEP9_FINAL_DECISION_REVIEW.md` §19 (FILLED researcher decision form; §18 BLANK form preserved above it as the WU-18 pre-decision snapshot), `docs/PHASE6_REWARD_SPEC.md` §8.12 (A2 effort-term convention). **No new generator, no EPANET/PPO/RNG, no new raw artefact** — the WU-18 JSON `results/phase6/p6_s9_final_decision_review.json` and its §18 BLANK form are PRESERVED UNCHANGED; D-P6-006 is a human/register decision composed from the frozen WU-14→WU-18 evidence under the researcher's STAGE-B finalization directive. Deliverable commit `0dc1e8c`.

| Claim | Section/Key | Result | Interpretation |
|---|---|---|---|
| D-P6-006 minted & finalized | DECISION_REGISTER / D-P6-006 | architecture **F1** = hard N_neg==0 backstop (S4/TS4) + relative worst-node guard (S2/TS2, base=HOLD) over [0..H]; NO absolute floor; S3 not primary | the STEP-9 execution-time admissibility layer is now a committed design, unblocking STAGE C |
| Relative-rule base = HOLD counterfactual (A1) | DECISION_REGISTER D-P6-006 §A1 | forward-sim a_prev from identical current real state over [0..H]; compare proposed vs this hold | isolates the pure causal effect; identity hold ⇒ Δ≡0 ⇒ baseline-safe by construction at ε_p=0 |
| Movement term uses EXECUTED action (A2) | REWARD_SPEC §8.12 | post-safety commanded action = D-P6-005's "commanded"; formula/weights/constants UNCHANGED | disambiguation, NOT a reward change; no STAGE-I stop; H1-reject da=0 is a benign monitor item |
| PPO-readiness is a 5-step gate (A3) | DECISION_REGISTER D-P6-006 §A3 | 1 finalize → 2 implement env → 3 validate anchors → 4 real-EPANET/WNTR integration tests → 5 THEN PPO-ready; project at step 1→2 | minting D-P6-006 unblocks implementation (STAGE C), NOT PPO-readiness; corrects §18 wording |
| Value knobs flagged, sweep mandated | DECISION_REGISTER D-P6-006 §C/§D | ε_p default 0.0 psi {0,2,5}; H default 1 step {1,2,4,8}; backstop N_neg==0 FIXED (evidence-supported) | the researcher-chosen knobs are reconfigurable; STEP-12 sweep pre-registered (CLAUDE.md §16/§21) |
| Handling policy | DECISION_REGISTER D-P6-006 §E | H1 reject-to-hold primary + H3 reference fallback when hold breaches backstop; H2 clip documented | executed-branch probe = committed next state (no re-solve, no tank discontinuity; STAGE-I-safe) |
| Claim scope is non-universal | DECISION_REGISTER D-P6-006 / claim scope | guarantees ONLY: no negative service pressure + no worst-node degradation > ε_p vs hold, over [0..H], in the tested setting | NO 20-psi floor; NO protection beyond H; NO joint 5-D-box (R1b) / stochastic-demand (STEP-10) safety; NO FP/FN rates |
| No finite H is universally sufficient | DECISION_REGISTER D-P6-006 §D | worst 1.2946763038635254 psi @ idx192 (96h); θ_p=5 crossover @ idx13 (6.5h) beyond H=8 | per-step re-check is primary; the horizon knob cannot guarantee against the delayed 96h collapse |
| Frozen invariants unchanged | DECISION_REGISTER D-P6-006 / preserved | D-P6-001/002/003 action (dim 7); D-P6-004 observation (dim 139); D-P6-005 reward (weights + 5 constants) byte-identical | STEP-9 is an admissibility wrapper; it changes nothing frozen |
| Determinism preserved | tests/test_step9_final_decision_review.py | 28 OK after the finalization edits (verified) | the finalization lives in docs + the register; the WU-18 aggregator JSON + §18 blank form are untouched |
