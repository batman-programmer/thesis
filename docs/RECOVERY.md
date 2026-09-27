# RECOVERY.md — Fresh-Session Entry Point

**If you are a new AI session (or a human) resuming this project, read this file
first, then `PROJECT_STATE.yaml`, then the three Phase 6 docs listed below. You
should be able to reconstruct the whole project state from disk WITHOUT the old
chat.**

Last updated: 2026-09-27 (UTC) by Claude Opus 4.8. **Action space APPROVED & FROZEN
2026-09-27 (D-P6-001/002/003); STEP 7 observation design APPROVED & FROZEN 2026-09-27
(D-P6-004, observation_dim=139); STEP 8 (reward design — MEASURE component scales, do
NOT train) MEASUREMENT COMPLETE 2026-09-27 (WU-9), FORMULATION COMPARISON COMPLETE
2026-09-27 (WU-10, evidence only), and D-P6-005 DECISION BRIEF PREPARED 2026-09-27
(WU-11). D-P6-005 remains PROPOSED / DECISION PENDING RESEARCHER — formulation & weights
NOT selected; researcher_selection=null.**

---

## 0. What this project is (30-second version)

Master's thesis: **Adaptive Pressure Control in Water Distribution Networks using
Deep RL (PPO), integrated with EPANET/WNTR**, to **reduce background leakage
under uncertain demand**. Benchmark network: **BWSN-1**. We are in **Phase 6**:
*design, implement and validate a defensible DRL environment for PPO.* The goal
of Phase 6 is **NOT** to make PPO learn — it is to build a correct, reproducible,
physically meaningful environment that PPO could later be run on.

Governing constitution: `CLAUDE.md` and `AGENTS.md` (identical "Research
Engineering Constitution", one addressed to Claude, one to Codex). Read them.

---

## 1. Read-order for a full reconstruction

1. `RECOVERY.md` (this file) — where we are, what not to redo.
2. `PROJECT_STATE.yaml` (repo root) — machine-readable full state.
3. `docs/PHASE6_EXECUTION_LOG.md` — chronological work units with evidence.
4. `docs/PHASE6_DECISION_REGISTER.md` — every decision (open + resolved).
5. `docs/PHASE6_EVIDENCE_INDEX.md` — claim -> file/section/result mapping.
6. `docs/phase6_g5_g12_resolution.md` — Deliverable A (G5 + G12), 733 lines.
7. `docs/PHASE6_ACTION_SPACE_SPEC.md` — **APPROVED & FROZEN action space** (the
   single source of truth for what the agent may command; §9 spec).
8. Phase 5 evidence: `results/phase5/*.json`; Phase 6 evidence: `results/phase6/*.json`.

The `docs/ai-knowledge/` directory is a separate **portable backup** (committed
in 8dc8151). Do not confuse `docs/ai-knowledge/PROJECT_STATE.yaml` (backup
snapshot) with the live root `PROJECT_STATE.yaml` (this workflow's state file).

---

## 2. Verified current state (from on-disk evidence, 2026-09-26 audit)

- Git: branch `main`, HEAD `e91c363` (`phase6: approve drl actuator action space`).
  Preceding: `8c89ba2` (step6b VALVE-173 evidence), `627567b` (step6 bounds). Working
  tree carries only untracked `results/phase5/_tmp/*` scratch + `__pycache__/*.pyc`
  (pre-existing debt, not committed).
- Phase 5: COMPLETE. Do not rerun its gates.
- Phase 6 Deliverable A COMPLETE: **G5 (action space)** and **G12 (pump speed
  persistence)** both RESOLVED with measured evidence in
  `docs/phase6_g5_g12_resolution.md`.

### 2.1 G5 result (action space) — VALIDATED FACT

- **5 RL-controlled PRVs** (continuous setpoint): `VALVE-173` (nom 70 psi),
  `VALVE-175` (55), `VALVE-176` (29.762), `VALVE-177` (45), `VALVE-178` (37).
- **Excluded**: `VALVE-174` (adverse reopen 95->96 psi), `VALVE-179` (safety
  cliff — clean <=44.7 psi, first negative at 44.9), `VALVE-180` (commanded shut
  by `[CONTROLS]`).

### 2.2 G12 result (pump control) — VALIDATED FACT / ENGINEERING DECISION

- **Option C on Option A's mechanism**: agent commands **pump SPEED only**,
  re-issued at every 1800 s control step; native rules keep pump **STATUS**.
- Measured: re-issue every step holds commanded speed 98.62% of the time vs
  1.72% if commanded once. `SETTING IS <s>` does not reopen a shut pump;
  `STATUS IS OPEN` reopens but overwrites speed to 1.0 — neither rule action
  alone suffices, hence the abstraction-level split.
- **Option B disqualified**: rewriting rule actions to `SETTING IS` halts the
  segmented simulator at t=79.5h (both pumps latch Closed, tank empties,
  "System unbalanced ... EXECUTION HALTED"). An env that can halt mid-episode is
  not defensible.

### 2.3 Pump feasible speed (measured) — VALIDATED FACT

Source `results/phase5/g3_pump_speed.json`:
- PUMP-170 min feasible speed **0.8152**, shut at 0.80, ran at 0.85.
- PUMP-172 min feasible speed **0.7655**, shut at 0.70, ran at 0.80.
- Sweep 0.50–1.10; no speed exceeded curve Qmax up to 1.10; affinity law holds.

---

## 3. What is NOT done yet (the live frontier)

- **STEP 5 (encoding) — APPROVED 2026-09-27 (D-P6-001).** ABSOLUTE encoding:
  `a_i ∈ [-1,1]`, `physical_i = lower_i + ((a_i+1)/2)*(upper_i-lower_i)`. Delta is a
  separate future ablation only. Do not silently change this.
- **STEP 6 (action bounds) — APPROVED 2026-09-27 (D-P6-002 pump, D-P6-003 PRV).**
  FROZEN in `docs/PHASE6_ACTION_SPACE_SPEC.md`. Exact ordered 7-D action vector:
  - action[0] VALVE-173 [54.5, 100.0] psi · action[1] VALVE-175 [21.5, 110.0] ·
    action[2] VALVE-176 [20.0, 59.524] · action[3] VALVE-177 [20.0, 90.0] ·
    action[4] VALVE-178 [20.0, 74.0] · action[5] PUMP-170 [0.82, 1.10] rel speed ·
    action[6] PUMP-172 [0.77, 1.10] rel speed. `action_dim=7`, box `[-1,1]^7`, float32.
  - Excluded {174,179,180} REMAIN in the hydraulic model (179 stays excluded,
    safety-critical). Pump = SPEED only, native STATUS rules kept, re-issue each step.
  - **Terminology (do not overstate):** for 175/176/177/178 the uppers are highest
    tested REGULATING setpoints (grid cap, valve still Active), NOT physical maxima
    or demonstrated ceilings. 173: 54.5 = first measured Active; 100 = highest tested
    regulating; 110 = Open/non-regulating. Pump 1.10 = highest tested feasible, not
    absolute max; 0.82/0.77 carry margin above shut-off (0.8152/0.7655).
  - **Joint 5-D box safety NOT proven** — only a single lower-corner test exists.
    No exhaustive joint-safety claim; STEP-9 (safety layer) + STEP-12 (tests) must
    cover mixed corners / interior / pump+demand (R1b). Provenance PROPOSED→REVIEWED
    →APPROVED preserved in the register + PROJECT_STATE (proposed values NOT erased).
- **STEP 7 observation design — APPROVED & FROZEN 2026-09-27 (D-P6-004).** Researcher
  signed off all 5 review points; the 139-dim layout is now frozen exactly as the action
  vector was (values unchanged on approval). On disk:
  `docs/PHASE6_STATE_SPEC.md` (§7.1–§7.14), `src/env/state_builder.py` (+ `__init__.py`),
  `tests/test_state_builder.py` (9/9), `src/validation/p6_s7_state_spec.py`,
  `results/phase6/p6_s7_state_spec.json`. `observation_dim = 139`, float32; blocks:
  pressures[0:121], tank_levels[121:123], prev_cmd_prv_setpoint[123:128],
  prv_is_active[128:133], prev_cmd_pump_speed[133:135], pump_realized_speed[135:137],
  time_of_day sin/cos[137:139]. Fixed physical normalization (pressure band [-20,300]
  psi); demand = Option A (no explicit demand; time-of-day diurnal prior; future demand
  FORBIDDEN); POMDP (approximate Markov; tanks = observed memory). 5/5 review points
  accepted in D-P6-004. STEP 8 (reward) reads this state but MUST NOT alter it.
- **STEP 8 reward design — MEASUREMENT COMPLETE 2026-09-27 (D-P6-005 PROPOSED).**
  Empirically MEASURED the natural scale/variability/temporal behaviour/cross-correlation
  of 10 candidate reward components over 19 static in-bounds configs × 193 report ts
  (3667 pooled instants), ran the reward-pathology checks against measured evidence, and
  PROPOSED 4 principled formulations. **No weights chosen, no formulation selected, no PPO
  trained.** On disk: `docs/PHASE6_REWARD_SPEC.md` (§8.1–§8.8),
  `src/validation/p6_s8_reward_scale_analysis.py`,
  `results/phase6/p6_s8_reward_scale_analysis.json`,
  `tests/test_reward_scale_analysis.py` (21/21: 12 STEP 8 + 9 STEP 7). Key measured
  findings: leakage 84.95 GPM mean (79.92–90.15, ±~6% band) ≈10× smaller than demand
  (~906 GPM); objectives GENUINELY OPPOSE (leak↔dsr +0.750, leak↔deficit −0.774,
  dsr↔deficit −0.965); leakage-only (prv_all_lower) cuts leak −4.0% but drops DSR −6.4 pts
  → service must be protected explicitly; scale imbalance ratio 7.15 → fixed normalisation
  mandatory; hard-violation term degenerate (0 at 100% of instants) → dense safety =
  deficit/min-pressure; actuator L2² up to 28 → effort ÷ 28 and use COMMANDED action;
  leakage optimum at the PRV lower bound → STEP-9 hard clamp REQUIRED. Fixed normalisation
  constants (frozen, no running stats): leak_ref 84.72988, req_ref 906.39873, deficit_ref
  28.67179, power_ref 88.10062, movement_L2sq_max 28.0. 4 PROPOSED formulations: F1
  normalised weighted sum, F2 constrained penalty (service protected by construction), F3
  baseline-relative improvement, F4 safety-first lexicographic. **STEP 8 COMPARISON also
  done (WU-10, 2026-09-27):** F1–F4 evaluated per-timestep over the same 19 validated
  static commands with PROVISIONAL comparison-only params (F1 w_·=1; F2 Λ=20,BIG=100; F3
  w_U=w_P_safety=1; F4 θ=20). On disk: `src/validation/p6_s8_reward_formulation_comparison.py`,
  `results/phase6/p6_s8_reward_formulation_comparison.json`,
  `tests/test_reward_formulation_comparison.py` (44/44 full battery), spec §8.9–§8.11. Key:
  under provisional weights all four incentive-argmax = `prv_176_upper` (bound, min svc
  ~4.17 psi); leak-only → `prv_lower_pump_lower` (min svc 1.295 psi); hard-20-psi terms
  (F2/F4@20) fire on the native baseline (2 chronic <20 nodes) → ill-posed; θ=0 never
  fires but permissive; leak-term dynamic range 0.108 vs unit max-move cost 1.0. NO winner
  selected. **STEP 8 D-P6-005 DECISION BRIEF also done (WU-11, 2026-09-27):** WU-9 + WU-10
  evidence converted into a decision-ready brief so the researcher can select ONE formulation
  + parameters. On disk: `docs/PHASE6_D_P6_005_DECISION_BRIEF.md` (11 sections, researcher
  decision block BLANK), `src/validation/p6_d_p6_005_decision_brief.py` (pure aggregator —
  no EPANET/PPO/RNG; deterministic regeneration byte-reproduces the JSON),
  `results/phase6/p6_d_p6_005_decision_brief.json` (**researcher_selection=null**),
  `tests/test_decision_brief.py` (63/63 full battery). FOUR "PROVISIONAL CANDIDATE — NOT
  APPROVED" parameterizations traced to measured scales (C-A/C-B F1 with w_A=0.1 from the
  measured 0.108 leak range, C-C F3 baseline-relative, C-D dense-deficit + negative-only hard
  gate); chronic-baseline finding: a HARD absolute 20-psi reward constraint is ILL-POSED
  (frac_ts_any_node_below_20psi=1.0 on the native baseline) → use dense deficit / worst-node /
  baseline-relative / negative-only gate at reward level, and leave the enforced 20-psi
  guarantee to STEP-9. NO formulation selected/scored/ranked. NEXT: researcher completes the
  decision block (resolves D-P6-005). Do NOT choose final weights, do NOT start PPO.
- STEP 9 safety layer, STEP 10 demand uncertainty/splits: NOT STARTED.
  STEP-9 must hard-clamp to the approved bounds.
- STEP 11 `src/env/` (8 modules) + STEP 12 `tests/` (16 tests) + STEP 13 SB3
  smoke test: BLOCKED — deps missing.

## 4. Hard blocker

`gymnasium`, `stable_baselines3`, `torch` are **MISSING** from `.venv`
(`pyyaml` also missing). Recorded as **BLOCKED**. Do **not** auto-install; needs
researcher approval (instruction §20). Present: wntr 1.5.0, epyt 2.3.5.2,
numpy 2.5.2, pandas 3.0.5, scipy 1.18.1, networkx 3.6.1, python 3.13.15.

## 5. How to run anything

Use the venv Python from Git Bash: `.venv/Scripts/python.exe`. EPANET is
deterministic; no seed needed for characterization runs. Every characterization
result is written to `results/phase6/` as JSON (raw + summary + interpretation).

---

## 6. DO NOT REPEAT

- **DO NOT** rerun Phase 5 gates or the benchmark build — Phase 5 is COMPLETE.
- **DO NOT** re-derive G5 or G12 — both RESOLVED in `docs/phase6_g5_g12_resolution.md`.
- **DO NOT** redo the portable backup in `docs/ai-knowledge/` — done, committed 8dc8151.
- **DO NOT** re-run the VALVE-179 fine characterization — bound is 44.7 psi (clean),
  44.8 (last non-negative), 44.9 (first negative). Already in `p6_s3b_v179_refine.json`.
- **DO NOT** re-run the pump strategy A/B/C comparison — done in `p6_s4_pump_strategy.json`.
- **DO NOT** re-measure pump feasible speed bounds — in `g3_pump_speed.json`.
- **DO NOT** re-run the STEP 6 per-PRV setpoint sweep — done in
  `p6_s6_active_prv_bounds.json` (D-P6-003). Proposed domains recorded; bounds are
  PROPOSED — PENDING APPROVAL, not frozen. Re-run only if the leak instrument,
  solver policy, or admitted PRV set changes.
- **DO NOT** re-run the VALVE-173 (50,60] low-side refinement — done in
  `p6_s6b_v173_lowside_refine.json` (2026-09-27). Measured: fully closed to 54.25 psi,
  fully active from 54.5 psi. Practical regulating lower edge = 54.5 psi.
- **DO NOT** re-run the STEP 8 reward-component scale analysis
  (`src/validation/p6_s8_reward_scale_analysis.py`) or rewrite `docs/PHASE6_REWARD_SPEC.md`
  — the measurement is on disk (`results/phase6/p6_s8_reward_scale_analysis.json`, 19 configs
  × 193 ts, 21/21 tests). It is **D-P6-005, PROPOSED 2026-09-27**. The measured scales,
  correlations, pathology evidence, fixed normalisation constants, and 4 PROPOSED
  formulations are frozen as evidence; re-run only if the leak instrument, solver policy,
  action bounds, or 121-service-node set changes. Do NOT choose reward weights, do NOT
  select a formulation, and do NOT implement `src/env/reward.py` (STEP 11) without the
  researcher's D-P6-005 selection. Do NOT start scientific PPO training.
- **DO NOT** re-run the STEP 8 reward-formulation comparison
  (`src/validation/p6_s8_reward_formulation_comparison.py`) or rewrite §8.9–§8.11 of
  `docs/PHASE6_REWARD_SPEC.md` — the comparison is on disk (WU-10, 2026-09-27:
  `results/phase6/p6_s8_reward_formulation_comparison.json`, 44/44 tests). The PROVISIONAL
  comparison params are illustrative ONLY (NOT proposed weights). It adds evidence for
  D-P6-005 but does NOT resolve it — no formulation is selected/scored/ranked, no weights
  tuned, no STEP-9 clamp added, no PPO trained. Re-run only if the leak instrument, solver
  policy, action bounds, or 121-service-node set changes.
- **DO NOT** re-run the STEP 8 D-P6-005 decision-brief aggregator
  (`src/validation/p6_d_p6_005_decision_brief.py`) or rewrite
  `docs/PHASE6_D_P6_005_DECISION_BRIEF.md` — the brief is on disk (WU-11, 2026-09-27:
  `results/phase6/p6_d_p6_005_decision_brief.json` with **researcher_selection=null**, 63/63
  tests). It is a PURE aggregator of WU-9 + WU-10 (no EPANET/PPO/RNG; deterministic
  regeneration byte-reproduces the JSON), so re-running changes nothing unless those two
  artefacts change. The FOUR candidate parameterizations are "PROVISIONAL CANDIDATE — NOT
  APPROVED" — do NOT treat any as chosen. The brief PREPARES the D-P6-005 gate but does NOT
  resolve it: no formulation selected/scored/ranked, no weights tuned. Do NOT fill in the
  researcher's decision block, do NOT set researcher_selection, do NOT implement
  `src/env/reward.py` (STEP 11) or a STEP-9 clamp, and do NOT start PPO — those await the
  researcher's D-P6-005 selection.
- **DO NOT** start scientific PPO training. A tiny smoke test is allowed ONLY after
  the env is implemented and validated, and only to prove the loop runs.
- **DO NOT** auto-install gymnasium / stable_baselines3 / torch.
- **DO NOT** make silent research-impacting decisions (encoding, bounds, reward,
  observation, exclusions) — register them first and get approval where required.
- **DO NOT** delete or rewrite `docs/ai-knowledge/` backup material or `session-backup/`.
- **DO NOT** treat VALVE-174/179/180 as controllable — they are excluded on evidence.
- **DO NOT** reopen the APPROVED & FROZEN action space (D-P6-001/002/003, 2026-09-27)
  without new contradictory evidence. Exact frozen values live in
  `docs/PHASE6_ACTION_SPACE_SPEC.md`; do not silently change encoding, bounds,
  ordering, or the excluded set. Excluded {174,179,180} MUST stay in the hydraulic model.
- **DO NOT** claim exhaustive joint 5-D action-box safety — only a single lower-corner
  test exists (R1b); that is a STEP-9/STEP-12 job.
- **DO NOT** re-run the STEP 7 observation builder or its evidence generator
  (`src/validation/p6_s7_state_spec.py`) or rewrite `docs/PHASE6_STATE_SPEC.md` — the
  design is on disk (`observation_dim=139`, 9/9 tests, `results/phase6/p6_s7_state_spec.json`).
  It is **D-P6-004, APPROVED & FROZEN 2026-09-27** — the 139-dim layout is frozen exactly
  as the action vector was (values unchanged on approval). Do NOT silently alter the
  layout, ordering, normalization, or the demand/Markov framing while designing the reward.
  Do not add reward/PPO/demand/safety logic to the state builder (those are STEP 8/9/10/11).

