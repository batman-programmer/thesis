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

## Still-missing evidence (drives next action)

| Needed claim | Why missing | How to obtain |
|---|---|---|
| Joint 5-D action-box safety (mixed corners/interior/pump+demand) | only single lower-corner tested (R1b) | STEP 9 safety layer + STEP 12 automated joint tests |
| Reward formulation + weights (D-P6-005 selection) | STEP 8 MEASURES scales/pathologies (WU-9), COMPARES F1–F4 under provisional params (WU-10), and PREPARES a decision brief with 4 provisional NOT-APPROVED candidates (WU-11); no formulation selected, no weights chosen | researcher completes the decision block in `docs/PHASE6_D_P6_005_DECISION_BRIEF.md` (selects ONE formulation + parameters, resolves D-P6-005); STEP 11 implements `src/env/reward.py` |
| Realised actuator-movement distribution | static runs = 0 movement; effort scale is analytic (R5-effort, HYPOTHESIS) | measured at training time once a policy trajectory exists |
| Leak calibration | instrument uncalibrated (R3) | out of Phase 6 scope; relative response only |
| Observation/state design | DELIVERABLES PRODUCED; D-P6-004 PROPOSED — awaiting researcher approval (not frozen) | researcher sign-off on the 5 review points → freeze 139-dim layout |
