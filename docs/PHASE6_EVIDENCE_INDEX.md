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

## Still-missing evidence (drives next action)

| Needed claim | Why missing | How to obtain |
|---|---|---|
| Per-valve safe bounds for 173/175/176/177 | only joint 0.75–1.00× tested | D-P6-003 per-valve sweep -> p6_s6_active_prv_bounds.json |
