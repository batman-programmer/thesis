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
| Joint lower-corner safe | cross_actuator_joint_lower_corner | 0 neg, 0 new <20psi, min 4.190 psi, leak 81.383 gpm (−3.347) | per-valve box constraints jointly sufficient at aggressive corner |
| Bounds are asymmetric | proposed_bounds_table.* | one-sided [svc-lower, nominal], differ per valve | no shared %-band (§7 satisfied) |

## Still-missing evidence (drives next action)

| Needed claim | Why missing | How to obtain |
|---|---|---|
| Researcher approval of proposed PRV bounds | D-P6-003 is characterization only | explicit approval (§14) — then freeze |
| Pump upper bound policy | D-P6-002 open | researcher choice 1.0 vs 1.10 |
| Observation/state design | STEP 7 not started | STEP 7 |
