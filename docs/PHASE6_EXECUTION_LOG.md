# PHASE6_EXECUTION_LOG.md — Chronological Work Units

Per-unit template (instruction §5): Objective · Starting state · Evidence
inspected · Action taken · Result · Decision · Decision class · Files changed ·
Tests · Risks/caveats · Next action. **No fictional entries.** Entries WU-1 and
WU-2 are reconstructed from on-disk artefacts produced in earlier sessions
(clearly marked); WU-3 is the current session.

Decision-class labels (do not mix): VALIDATED FACT · ENGINEERING DECISION ·
RESEARCH ASSUMPTION · HYPOTHESIS TO TEST · DECISION REQUIRED.

---

## WU-1 — STEP 3: PRV fine characterization & G5 admission (earlier session; reconstructed from artefacts)

- **Objective:** Decide, on measured grounds, which PRVs are safe to expose as RL
  action dimensions (G5).
- **Starting state:** Phase 5 found 5 PRVs responsive; VALVE-174/179/180 uncertain.
- **Evidence inspected:** `results/phase6/p6_s3_prv_finechar.json`,
  `p6_s3b_v179_refine.json`, `p6_s3c_zone_interaction.json`.
- **Action taken:** Fine setpoint sweeps of VALVE-179 (38–60 psi), VALVE-174
  (80–110), VALVE-180 (16.45–120, incl. control-released); joint responsive-valve
  test at 0.75/0.90/1.00× nominal; VALVE-179 vs VALVE-178 interaction grid.
- **Result:** VALVE-179 safety cliff — last clean 44.7 psi, last non-negative
  44.8, first negative 44.9. VALVE-174 adverse reopen 95->96 psi. VALVE-180
  commanded shut by `[CONTROLS]`. Per-valve box constraint sufficient on the
  tested set (no joint case with 179<=44.7 produced negative pressure).
- **Decision:** Action space = 5 PRVs {173,175,176,177,178}; exclude {174,179,180}.
- **Decision class:** VALIDATED FACT (measurements) + ENGINEERING DECISION (exclusion).
- **Files changed:** results/phase6/p6_s3*.json; docs/phase6_g5_g12_resolution.md.
- **Tests:** characterization runs; echo/continuity checks embedded in JSON.
- **Risks/caveats:** per-valve *bounds* for the 5 admitted PRVs not yet swept.
- **Next action:** STEP 4 (pump), then STEP 5/6.

---

## WU-2 — STEP 4: Pump control strategy A/B/C & G12 resolution (earlier session; reconstructed from artefacts)

- **Objective:** Choose a pump-control abstraction that persists a commanded
  speed across an EPS without corrupting native tank-refill logic (G12).
- **Starting state:** Phase 5 G12 CONDITIONAL — commanded speed not retained;
  `STATUS IS OPEN` overwrites speed to 1.0.
- **Evidence inspected:** `results/phase6/p6_s4_pump_strategy.json` (cases:
  reference native 1.0, command-once monolithic, stepped mechanism check,
  Option A re-issue each step, Option A first-step-only control, Option B
  monolithic, Option B stepped-FAILED).
- **Action taken:** Measured reopen semantics (isolated rule test) and compared
  Options A/B/C on the segmented 1800 s loop at commanded speed 0.85.
- **Result:** `SETTING IS` does not reopen a closed pump; `STATUS IS OPEN`
  reopens but sets speed=1.0. Re-issue every step -> 98.62% speed-hold; command
  once -> 1.72%. Option B (rule rewrite) halts the segmented run at t=79.5h
  (unbalanced). Stepped mechanism check reproduces the monolithic reference
  (validates the segmented carry-forward: tank init_level + pump initial_status +
  options.time.pattern_start; requested demand computed once over full horizon).
- **Decision:** G12 = **Option C on Option A mechanism** — DRL commands SPEED
  only, re-issued each control step; native rules keep STATUS; info logs
  commanded-vs-realised separately.
- **Decision class:** VALIDATED FACT (measurements) + ENGINEERING DECISION (Option C).
- **Files changed:** results/phase6/p6_s4_pump_strategy.json; docs/phase6_g5_g12_resolution.md.
- **Tests:** echo checks, continuity residual < 7e-7, mechanism-reproduction check.
- **Risks/caveats:** Option B disqualified (R2). Pump speed *bounds* to finalize in STEP 6.
- **Next action:** STEP 5 (encoding) and STEP 6 (bounds).

---

## WU-3 — Recovery audit + interruption-resistance persistence scaffolding (2026-09-26, current session)

- **Objective:** Execute the "PHASE 6 — CONTINUE FROM VERIFIED STATE + PERSIST
  EVERYTHING TO DISK" instruction: audit actual repo state, then make state
  recoverable from disk without chat.
- **Starting state:** No root `PROJECT_STATE.yaml`, no `docs/RECOVERY.md`, no
  Phase 6 execution/decision/evidence docs. Backup committed (8dc8151).
- **Evidence inspected (this session):** git status/log; `CLAUDE.md`; `AGENTS.md`
  (full); `docs/phase6_g5_g12_resolution.md` (full, 733 lines); all four
  `results/phase6/*.json` (structure + values); `results/phase5/g3_pump_speed.json`
  (pump feasible bounds); `.venv` dependency import check; `src/validation/` and
  empty `tests/` listings.
- **Action taken:** Verified (not inferred from filenames) that STEP 3/STEP 4 are
  COMPLETE and STEP 5+ unstarted; deps missing. Wrote `PROJECT_STATE.yaml`,
  `docs/RECOVERY.md`, `docs/PHASE6_EXECUTION_LOG.md`,
  `docs/PHASE6_DECISION_REGISTER.md`, `docs/PHASE6_EVIDENCE_INDEX.md`.
- **Result:** State now reconstructable from disk. Dependency blocker recorded.
  YAML structural check: 0 tab-lines (full PyYAML parse deferred — PyYAML absent,
  not installed by policy §20).
- **Decision:** Persist-before-proceed; classify Phase 6 as IN PROGRESS.
- **Decision class:** ENGINEERING DECISION.
- **Files changed:** PROJECT_STATE.yaml, docs/RECOVERY.md, docs/PHASE6_EXECUTION_LOG.md,
  docs/PHASE6_DECISION_REGISTER.md, docs/PHASE6_EVIDENCE_INDEX.md.
- **Tests:** YAML tab/indent scan (stdlib).
- **Risks/caveats:** Full YAML parse validation pending PyYAML availability.
- **Next action:** STEP 6 per-valve PRV bound sweep (D-P6-003) -> `results/phase6/p6_s6_active_prv_bounds.json`.

---

## WU-4 — STEP 6: per-PRV operating-bound characterization (2026-09-27, current session)

- **Objective:** Derive defensible per-valve operating bounds for the five RL PRVs
  (VALVE-173/175/176/177/178) by measuring their physical response — NOT to
  optimize setpoints, NOT to start PPO, NOT to freeze the action space (§3, §11).
- **Starting state:** G5 fixed the RL PRV set; D-P6-003 OPEN — only a *joint*
  0.75–1.00× nominal test existed; 173/175/176/177 had no per-valve fine sweep.
- **Evidence inspected:** `src/validation/p6_s3_prv_finechar.py` (API template:
  `service_nodes`/`build`/`assert_solver`/`measure`/`run_case`, leak-sizing
  pattern); `phase5_common`, `g6_g7_g8_leak_pda`; PROJECT_STATE.yaml; the four
  Phase 6 JSONs and `results/phase5/g3_pump_speed.json`.
- **Action taken:** Wrote and ran `src/validation/p6_s6_active_prv_bounds.py`.
  Deterministic per-valve fine setpoint sweep centered on each Phase 5 nominal
  (173=70, 175=55, 176=29.762, 177=45, 178=37), other four PRVs at nominal, leak
  instrument on, PDA, 96 h EPS, solver 1e-5/2000/180s/1800s asserted each load.
  Adaptive grid extended outward from nominal (FLOOR 5 psi, CEIL 2.0× nominal) and
  refined to 0.25 psi around every negative-pressure and <20 psi transition.
  Per setpoint recorded (§5): commanded/echoed setting + transmission error, valve
  state + realization rate, mean/min/max service pressure, n<20psi, n_new<20psi vs
  baseline, n_negative, valve flow, leakage, DSR, continuity residual, solver-clean.
  Then a cross-actuator joint lower-corner run (all five at proposed lowers).
- **Exact setpoints evaluated (n):** 173=15, 175=22, 176=23, 177=20, 178=19, plus
  1 reference nominal and 1 joint lower-corner case.
- **Result (measured; baseline 386 <20psi, 0 negative, mean 94.787, leak 84.730):**
  - 173 (nom 70): observed [5,110], hard-safe [5,110], service-clean [5,110],
    PROPOSED [5.0,70.0]. Flow 4.72 gpm, leak span 0.825 gpm, save 0.279 gpm/0.329%,
    `closes_below_domain` (inert below ~55 psi) — weak actuator in isolation.
  - 175 (nom 55): observed [5,110], hard-safe [5,110], service-clean [21.5,110],
    PROPOSED [21.5,55.0]. Strongest actuator (362.91 gpm), save 1.883 gpm/2.222%;
    service transition resolved 21.25->21.5 psi.
  - 176 (nom 29.762): observed [10,59.524], hard-safe [13,59.524], service-clean
    [20,59.524], PROPOSED [20.0,29.762]. ONLY valve with a hard negative-pressure
    cliff: negative <=12.75 psi, first non-negative 13.0 (localized at JUNCTION-126);
    service transition 19.75->20.0; save 0.632 gpm/0.746%.
  - 177 (nom 45): observed [5,90], hard-safe [5,90], service-clean [20,90],
    PROPOSED [20.0,45.0]. No negative to 5 psi; service transition 19.75->20.0;
    save 0.346 gpm/0.408%.
  - 178 (nom 37): observed [5,74], hard-safe [5,74], service-clean [20,74],
    PROPOSED [20.0,37.0]. No negative to 5 psi; service transition 19.75->20.0;
    save 0.208 gpm/0.245%.
  - Joint lower corner (173=5,175=21.5,176=20,177=20,178=20): SERVICE-CLEAN —
    0 negative, 0 new <20psi, min 4.190 psi @ JUNCTION-29, leak 81.383 gpm
    (−3.347 vs baseline). Box constraints jointly sufficient at the tested corner.
- **Failures / negatives NOT hidden (§15):** VALVE-173 is nearly inert (weak action
  dimension, HYPOTHESIS TO TEST); per-valve leakage savings are modest (0.2–2.2%);
  the chronic low node JUNCTION-29 (~4.16 psi) is unaffected by these PRVs; the
  intended 176 negative cliff was the only negative pressure observed (expected).
- **Decision:** Propose asymmetric [service-clean lower, nominal] domains per valve
  (D-P6-003). PROPOSED, not final. Upper = nominal so the action space cannot
  command higher-than-baseline leakage.
- **Decision class:** VALIDATED FACT (measurements) + ENGINEERING DECISION (proposed
  domains) + DECISION REQUIRED (researcher approval of bounds & upper-bound policy).
- **Files changed:** src/validation/p6_s6_active_prv_bounds.py (new);
  results/phase6/p6_s6_active_prv_bounds.json (new); PROJECT_STATE.yaml;
  docs/PHASE6_DECISION_REGISTER.md; docs/PHASE6_EVIDENCE_INDEX.md;
  docs/PHASE6_EXECUTION_LOG.md; docs/RECOVERY.md.
- **Tests:** reference nominal reproduced EXACTLY twice; py_compile clean; every
  setpoint solver-clean, continuity residual < 1e-3; realization error 0 psi when
  Active; no truncation at grid cap.
- **Risks/caveats:** leak instrument uncalibrated (R3); bounds PROPOSED — PENDING
  APPROVAL (§14/§18), NOT frozen; STEP-9 safety layer must still clamp to approved
  bounds; upper-bound policy (nominal vs headroom) and 173 domain narrowing are
  open researcher decisions.
- **Next action:** researcher approval of D-P6-003 (and D-P6-002 pump upper bound);
  confirm D-P6-001 (absolute encoding); then STEP 7 observation/state design.

---

## WU-5 — STEP 6 decision review (four-question methodological brief) (2026-09-27, current session)

- **Objective:** Answer four researcher questions before bound approval —
  (1) VALVE-173 authority/dead-zone, (2) PRV upper-bound policy (nominal vs
  headroom), (3) pump upper bound (1.0 vs 1.10), (4) absolute vs delta action.
  NO re-run, NO freeze, NO action-space modification.
- **Starting state:** STEP 6 accepted as complete; D-P6-003 PROPOSED/PENDING.
- **Evidence inspected (existing files only):** `p6_s6_active_prv_bounds.json`
  (per-valve full sweeps, high_side_regulation, actuator_authority),
  `results/phase5/g3_pump_speed.json` (feasible_speed_bounds, response_summary).
- **Action taken:** Extracted exact per-setpoint measured values; produced the
  four-question decision brief; recorded a decision-review addendum in
  PHASE6_DECISION_REGISTER.md.
- **Result (measured highlights):** 173 fully closed (0 gpm) for 5–50 psi, first
  active at 60 psi, saturates at 110 → ~77% dead-zone within proposed [5,70],
  authority 0.279 gpm. VALVE-176 recovers service above nominal (n<20 386→193 at
  ≥35 psi) at +leakage; the other four only add leakage above nominal. Pump: 1.10
  measured feasible, 1.0 is a design choice. Native STATUS reset to speed 1.0 makes
  absolute encoding the robust choice.
- **Decision:** review recommendations recorded (173→regulating range B + ablation;
  PRV upper→headroom ceiling with reward-side trade-off; pump upper consistent with
  PRV policy; absolute confirmed). All PENDING researcher approval.
- **Decision class:** DECISION REQUIRED (researcher). No VALIDATED FACT changed.
- **Files changed:** docs/PHASE6_DECISION_REGISTER.md, docs/PHASE6_EXECUTION_LOG.md,
  PROJECT_STATE.yaml (session checkpoint only). No script, no result JSON, no env.
- **Tests:** none (analysis only; no simulation re-run).
- **Risks/caveats:** review SUPERSEDES the earlier "upper = nominal" leaning
  (Q2); the proposed-bounds table in the JSON is unchanged and still records
  [service-clean lower, nominal] — it is NOT frozen and will be reconciled only
  after the researcher chooses the upper-bound policy.
- **Next action:** await researcher decisions on Q1–Q4; then reconcile D-P6-003 and
  proceed to STEP 7.

---

## WU-6 — STEP 6 terminology/evidence clarification + focused VALVE-173 low-side refinement (2026-09-27, current session)

- **Objective:** Before bound approval, tighten the PRV upper-bound terminology
  (item 1), resolve the one unmeasured VALVE-173 coarse-grid gap (item 2), and
  narrow the over-general cross-actuator claim (item 3) — then present a final
  per-PRV decision table (item 4). NO full STEP 6 re-run, NO freeze, NO APPROVED.
- **Starting state:** D-P6-003 PROPOSED/PENDING. STEP 6 JSON records A/B/C domains
  but earlier prose called the four non-173 grid caps a "regulation ceiling"; the
  VALVE-173 coarse grid jumped 50→60 psi (no data in the open interval); the
  cross-actuator note read "jointly sufficient at the most aggressive tested corner".
- **Evidence inspected:** `results/phase6/p6_s6_active_prv_bounds.json` (per-valve
  `high_side_regulation`, `frac_time_active/open/closed`, `observed_domain_psi`,
  `cross_actuator_joint_lower_corner`); `src/validation/p6_s6_active_prv_bounds.py`
  and `p6_s3_prv_finechar.py` (`run_case`/`measure`/`build`/`service_nodes`
  machinery reused).
- **Action taken:** (a) Extracted the precise A/B/C values from disk; confirmed only
  VALVE-173 has an OBSERVED Active→Open transition (Active through 100, Open at 110);
  175/176/177/178 remain Active at their 2×nominal grid cap → true Open ceiling
  UNTESTED. (b) Wrote and ran `src/validation/p6_s6b_v173_lowside_refine.py` — a
  focused sweep of VALVE-173 ONLY across 50..60 psi (integer grid, refined to
  0.25 psi around the activation crossings), other four PRVs + both pumps at nominal,
  identical solver/PDA/leak instrument; wrote a NEW file (STEP 6 JSON preserved, §12).
  (c) Rewrote the cross-actuator claim to the single tested corner and flagged mixed
  corners/interior as a future STEP-9/STEP-12 test.
- **Exact setpoints evaluated (n=14):** 50, 51, 52, 53, 54, 54.25, 54.5, 54.75, 55,
  56, 57, 58, 59, 60 psi (+ reference nominal).
- **Result (measured; reference reproduced EXACTLY: 386 <20psi, 0 neg, 84.730 gpm):**
  - VALVE-173 is fully CLOSED (0.00 gpm, frac_active=0, frac_closed=1.0) at every
    setpoint **≤ 54.25 psi**, and flips fully ACTIVE (frac_active=1.0, 4.441 gpm) at
    **54.5 psi** — a sharp 0.25 psi step, NO partial-activation zone.
  - **last definitely closed = 54.25 psi; first definitely active = 54.5 psi;
    practical regulating lower edge = 54.5 psi.**
  - Across the whole (50,60] range: min service pressure flat at 4.165 psi, n<20psi
    = 386 (0 new violations), 0 negative, leakage nearly flat (84.451 gpm closed →
    84.554 gpm at 60) — the low side of VALVE-173 is safe but nearly inert.
  - The repo now SUPPORTS a ~55 psi lower bound for 173 (measured 54.5), which the
    earlier coarse grid did NOT.
- **A/B/C corrected terminology (item 1):** A = highest tested no-negative setpoint
  {173:110, 175:110, 176:59.524, 177:90, 178:74}; B = highest tested REGULATING
  setpoint {173:100, 175:110, 176:59.524, 177:90, 178:74}; C = observed Active→Open
  onset {173:110; 175/176/177/178 = UNTESTED, still Active at cap}. The caps for the
  four non-173 valves are **highest tested regulating setpoints, not demonstrated
  ceilings.**
- **Cross-actuator claim (item 3), narrowed:** the joint run tested ONE corner only
  (all five at proposed lowers, 173=5/175=21.5/176=20/177=20/178=20) and was
  service-clean there. That validates that single corner — NOT the whole 5-D box.
  Mixed corners, interior points, and pump+stochastic-demand combinations are
  UNTESTED → future STEP-9 safety-layer / STEP-12 joint-safety test. The tested
  corner also used 173=5 (closed); re-scoping 173's lower to ≥54.5 changes it.
- **Failures / negatives NOT hidden (§7/§12):** VALVE-173 remains a weak actuator
  (≈4.4–4.5 gpm flow, ~0.1 gpm leakage span across (50,60]); its [5,70] proposal
  carries a ~70% closed dead-zone. No negative pressure and no new <20 psi violation
  anywhere in this refinement (as expected for a near-inert valve).
- **Decision:** Propose re-scoping VALVE-173's DRL domain to its measured regulating
  range **[54.5, 100]**; keep A/B/C terminology precise; keep the cross-actuator
  claim to the single tested corner. All PROPOSED — PENDING APPROVAL.
- **Decision class:** VALIDATED FACT (step6b measurements + A/B/C extraction) +
  ENGINEERING DECISION (proposed 173 re-scope) + DECISION REQUIRED (researcher
  approval; nothing frozen).
- **Files changed:** src/validation/p6_s6b_v173_lowside_refine.py (new);
  results/phase6/p6_s6b_v173_lowside_refine.json (new); PROJECT_STATE.yaml;
  docs/PHASE6_DECISION_REGISTER.md; docs/PHASE6_EVIDENCE_INDEX.md; docs/RECOVERY.md;
  docs/PHASE6_EXECUTION_LOG.md. **p6_s6_active_prv_bounds.json NOT overwritten (§12).**
- **Tests:** py_compile clean; reference nominal reproduced exactly (386/0/84.730);
  all 14 setpoints solver-clean, continuity residual < 1e-3, 0 negative, 0 new <20psi.
- **Risks/caveats:** leak instrument uncalibrated (R3); single-corner joint result
  not generalizable (R1b); VALVE-173 weak-actuator hypothesis stands; bounds PROPOSED,
  NOT frozen; D-P6-003 NOT APPROVED.
- **Next action:** researcher approval of the clarified D-P6-003 (173 re-scope +
  per-valve upper-bound policy) and D-P6-002 (pump upper); confirm D-P6-001; STEP 7.

---

## WU-7 — Action-space APPROVAL persisted + spec + git checkpoint (2026-09-27, current session)

- **Objective:** Persist the researcher's explicit approval of the DRL action space
  (D-P6-001 encoding, D-P6-002 pump bounds, D-P6-003 PRV set + bounds), create the
  frozen action-space specification, and git-checkpoint it as a SEPARATE commit
  BEFORE any STEP 7 work (per the ACTION-SPACE approval instruction §8–§10).
- **Starting state:** D-P6-001/002/003 were PROPOSED/REVIEWED but PENDING; no
  `docs/PHASE6_ACTION_SPACE_SPEC.md`; PROJECT_STATE `action_space.status` not frozen.
- **Approval received (researcher, 2026-09-27):**
  - D-P6-001 = ABSOLUTE encoding; `a_i ∈ [-1,1]`;
    `physical_i = lower_i + ((a_i + 1)/2)*(upper_i - lower_i)`. Delta = separate future ablation.
  - D-P6-003 PRV bounds (psi): 173 [54.5,100.0]; 175 [21.5,110.0]; 176 [20.0,59.524];
    177 [20.0,90.0]; 178 [20.0,74.0]. Controlled {173,175,176,177,178}; excluded
    {174,179,180} KEEP in the hydraulic model; 179 stays excluded (safety-critical).
  - D-P6-002 pump bounds (rel speed): PUMP-170 [0.82,1.10]; PUMP-172 [0.77,1.10].
  - Pump strategy = keep native STATUS rules, agent controls SPEED only, re-issue
    speed each control step; commanded vs realized vs status kept explicit.
- **Action taken:** Flipped D-P6-001/002/003 headers + Status/Approval lines to
  APPROVED 2026-09-27 in the decision register and appended a consolidated APPROVAL
  section (exact values + PROPOSED→REVIEWED→APPROVED provenance, proposed history
  retained, NOT erased). Updated PROJECT_STATE.yaml (`action_space.approved` frozen
  block, step5/step6 APPROVED, `state_space` → IN PROGRESS, session_checkpoint,
  next_action). Created `docs/PHASE6_ACTION_SPACE_SPEC.md` (§9.1–§9.10 + the exact
  ordered 7-element action vector). Updated EVIDENCE_INDEX and RECOVERY.
- **Result:** Action space APPROVED & FROZEN on disk; reconstructable without chat.
  Exact ordered vector: action[0..4] → VALVE-173/175/176/177/178 (psi);
  action[5..6] → PUMP-170/172 (rel speed); action_dim 7; normalized box [-1,1]^7.
- **Decision:** Freeze the action space; proceed to STEP 7 only after checkpoint.
- **Decision class:** ENGINEERING DECISION (bounds/encoding) on VALIDATED FACT
  (measured characterization); researcher-approved.
- **Files changed:** docs/PHASE6_ACTION_SPACE_SPEC.md (new); PROJECT_STATE.yaml;
  docs/PHASE6_DECISION_REGISTER.md; docs/PHASE6_EVIDENCE_INDEX.md; docs/RECOVERY.md;
  docs/PHASE6_EXECUTION_LOG.md. NO result JSON overwritten; NO env/reward/PPO code.
- **Tests:** doc/state consistency check — approved values equal the item-4
  clarification table + step6b 173 lower edge (54.5); YAML tab-line scan clean.
- **Risks/caveats:** joint 5-D box safety still UNTESTED (R1b); leak instrument
  uncalibrated (R3); deps still missing (R4). Approval freezes per-actuator bounds
  ONLY, not exhaustive joint safety.
- **Git checkpoint:** commit **e91c363** `phase6: approve drl actuator action space`
  (docs + PROJECT_STATE + spec). Supporting VALVE-173 step6b evidence committed
  first at **8c89ba2** `phase6: add VALVE-173 low-side refinement evidence (step6b)`
  so the cited evidence lands before the decision. Scratch `results/phase5/_tmp/*`
  and `__pycache__/*.pyc` deliberately excluded.
- **Next action:** STEP 7 — DRL state/observation design (WU-8).

## WU-8 — STEP 7: DRL state/observation design (2026-09-27, current session)

- **Objective:** Define exactly what the PPO agent observes at each control step
  (state design ONLY — no reward/safety/demand/env), fully justified, labelled, and
  reproducible. Register as D-P6-004 (Level-2), keep PROPOSED (not frozen).
- **Starting state:** Action space APPROVED & FROZEN (D-P6-001/002/003, WU-7, commit
  e91c363). No observation defined yet. Deps: numpy present; gymnasium/torch/SB3
  absent (state builder needs only numpy → not blocked).
- **Evidence inspected:** approved action vector (order 173/175/176/177/178/170/172);
  121 service nodes / 5 connectors excluded (Phase-5 gate-10 rule via `p6_s3`); tank
  bounds (130 [0,32.1] ft, 131 [0,41.9] ft); pump STATUS reset → realized≠commanded
  (G12, `p6_s4_pump_strategy.json`); reference safety numbers (`p6_s3_prv_finechar.json`,
  386 nodes <20 psi, 0 negative, min 4.165 psi); measured service pressure range
  ≈4.2–288 psi (p99 ≈184).
- **Action taken:** Designed a 139-dim float32 observation: pressures[0:121],
  tank_levels[121:123], prev_cmd_prv_setpoint[123:128], prv_is_active[128:133],
  prev_cmd_pump_speed[133:135], pump_realized_speed[135:137], time_of_day sin/cos
  [137:139]. Fixed physical normalization only (pressure band [-20,300] psi). Demand
  = Option A (no explicit demand; time-of-day diurnal prior; future demand FORBIDDEN).
  Wrote `docs/PHASE6_STATE_SPEC.md` (§7.1–§7.14). Implemented the pure numpy builder
  `src/env/state_builder.py` (+ `src/env/__init__.py`), 9-test battery
  `tests/test_state_builder.py`, and evidence generator `src/validation/p6_s7_state_spec.py`
  → `results/phase6/p6_s7_state_spec.json`.
- **Result:** `observation_dim = 139`; `consistency_with_frozen_spec` all true; one
  genuine observation @ t=43200 s (5 PRVs Active → is_active=1; both pumps CLOSED →
  realized 0; vec min/max/mean −1.0/1.0/0.359); all `sample_checks` true; 9/9 tests
  pass. No future information; connectors excluded from features but kept in the model.
- **Decision:** Observation design PROPOSED as **D-P6-004** — PENDING RESEARCHER
  APPROVAL. Layout WORKING, NOT frozen until approved. 5 review points recorded.
- **Decision class:** ENGINEERING DECISION + RESEARCH ASSUMPTION (Level-2).
- **Files changed:** src/env/state_builder.py (new); src/env/__init__.py (new);
  tests/test_state_builder.py (new); src/validation/p6_s7_state_spec.py (new);
  results/phase6/p6_s7_state_spec.json (new); docs/PHASE6_STATE_SPEC.md (new);
  PROJECT_STATE.yaml; docs/PHASE6_DECISION_REGISTER.md; docs/PHASE6_EVIDENCE_INDEX.md;
  docs/RECOVERY.md; docs/PHASE6_EXECUTION_LOG.md. NO action-space file reopened; NO
  reward/PPO/demand/safety code.
- **Tests:** `.venv/Scripts/python.exe -m unittest discover -s tests -v` → 9 ok.
- **Risks/caveats:** POMDP — approximate sufficient statistic, not exact Markov
  (instantaneous demand hidden by design); single-step obs may under-react to fast
  demand transients (HYPOTHESIS; remedy = Option-B inflow or frame-stack/LSTM, future).
  Design NOT frozen until D-P6-004 approved. Joint-box safety (R1b), leak calibration
  (R3), missing deps (R4) unchanged.
- **Next action:** Present D-P6-004 to the researcher for approval of the 5 review
  points; on approval freeze the layout, then STEP 8 (reward).

---

## WU-9 — STEP 8: reward-component scale analysis (2026-09-27, current session)

- **Objective:** EMPIRICALLY MEASURE the natural scale / variability / temporal
  behaviour / cross-correlation of every candidate reward component under
  representative in-bounds trajectories, run the reward-pathology checks against
  measured evidence, and PROPOSE a small set of principled reward formulations.
  This step MEASURES only — it chooses NO weights, selects NO formulation, and
  trains NO PPO (§5–§12, §16). Register as D-P6-005 (Level-2), keep PROPOSED.
- **Starting state:** Action space APPROVED & FROZEN (D-P6-001/002/003, commit
  e91c363); observation APPROVED & FROZEN (D-P6-004, observation_dim=139, commit
  0cd7f2e). No reward defined. Sim stack present (wntr/epyt/numpy) → not dep-blocked.
- **Evidence inspected:** approved action bounds (7-D) and 121 service / 5 connector
  policy via `p6_s3.service_nodes`; the Phase-5 leak/PDA instrument `g6_g7_g8_leak_pda`
  (signed emitter law, k=7.13768e-05, PDA 20/0/0.5); solver policy (1e-5/2000/180s/1800s);
  frozen reference (`p6_s3_prv_finechar.json`: leak 84.730, DSR 0.98334, 386 ts<20psi, 0 neg).
- **Action taken:** Wrote and ran `src/validation/p6_s8_reward_scale_analysis.py`.
  19 static full-96 h EPS configurations (reference_nominal; prv_all_lower/upper; each
  PRV edge singly ×10; pump_all_lower/upper; 4 mixed PRV×pump corners), each setting all
  5 PRV setpoints + both pump speeds explicitly, native STATUS rules/topology untouched.
  Per report timestep (193/config → 3667 pooled instants) extracted 10 candidate
  components: leakage_gpm, served/requested/unserved_demand_gpm, dsr,
  pressure_deficit_psi_nodesum, n_service_nodes_below_20psi, min_service_pressure_psi,
  n_service_nodes_negative, pump_hydraulic_power_kw. Computed pooled + within-config
  mean/median/std/min/max, mean |step-to-step Δ|, 10×10 Pearson correlation, pathology
  checks, and analytic actuator-effort ceiling from the frozen `[-1,1]^7` box. Fixed the
  normalisation constants once from the baseline/pooled stats. Wrote
  `docs/PHASE6_REWARD_SPEC.md` (§8.1–§8.8) and the 12-test battery
  `tests/test_reward_scale_analysis.py`.
- **Result (measured; per-ts extraction reproduces validated water balance to 0.0 GPM;
  reference reproduces frozen baseline exactly):**
  - Pooled scales: leakage 84.95 GPM mean (79.92–90.15, ±~6% band); requested ~906 GPM
    (median 774) ≈10× leakage; DSR 0.9734 (0.9142–1.00246); deficit 19.86 psi·nodes
    (max 31.73); min svc pressure 4.77 psi (1.09–5.93); n_negative identically 0;
    pump power mean ~80 kW, median 0 (bimodal, native-STATUS-driven).
  - Correlations: leak↔dsr +0.750, leak↔deficit −0.774, leak↔n_below20 −0.742,
    dsr↔deficit −0.965, served↔requested +0.999 — objectives GENUINELY OPPOSE.
  - Pathologies confirmed on measured evidence: (1) leakage-only (prv_all_lower) cuts
    leak −4.0% but drops DSR 0.98334→0.91940 (−6.4 pts) → service must be protected;
    (2) pressure-only (prv_all_upper) +5.9% leakage; (3) scale imbalance ratio 7.15 →
    fixed normalisation mandatory; (4) hard-violation term degenerate (0 at 100% of
    instants) → dense safety = deficit/min-pressure; (5) actuator L2² up to 28 would
    dominate → effort ÷ 28 and use COMMANDED action (closed-pump reset ambiguity);
    (6) leakage optimum sits at the PRV lower bound → STEP-9 hard clamp REQUIRED.
  - Fixed normalisation constants (frozen, no running stats): leak_ref 84.72988,
    req_ref 906.39873, deficit_ref 28.67179 (=max(baseline mean, pooled p95)),
    power_ref 88.10062, movement_L2sq_max 28.0.
  - 4 PROPOSED formulations: F1 normalised weighted sum, F2 constrained penalty
    (service protected by construction), F3 baseline-relative improvement,
    F4 safety-first lexicographic. All status "PROPOSED".
- **Failures / negatives NOT hidden (§7):** the controllable leakage signal is small in
  absolute terms (±~6% band) → absolute-GPM objective is weak, argues for normalised /
  baseline-relative; actuator movement is 0 in every static run → its scale is ANALYTIC,
  a training-time HYPOTHESIS, not a measured fact; only ONE joint corner (prv_all_lower)
  is characterised → full interior/joint safety NOT claimed (STEP-9/STEP-12).
- **Decision:** Reward formulation PROPOSED as **D-P6-005** — measurement complete,
  formulation and weights NOT selected. PENDING RESEARCHER SELECTION of ONE formulation
  + weights, plus the STEP-9 hard safety clamp the boundary-seeking check proves is required.
- **Decision class:** VALIDATED FACT (measured scales/correlations/pathologies) +
  ENGINEERING DECISION (candidate set, normalisation constants, proposed formulations) +
  DECISION REQUIRED (researcher selection of formulation + weights).
- **Files changed:** src/validation/p6_s8_reward_scale_analysis.py (new);
  results/phase6/p6_s8_reward_scale_analysis.json (new); docs/PHASE6_REWARD_SPEC.md (new);
  tests/test_reward_scale_analysis.py (new); PROJECT_STATE.yaml;
  docs/PHASE6_DECISION_REGISTER.md; docs/PHASE6_EVIDENCE_INDEX.md; docs/RECOVERY.md;
  docs/PHASE6_EXECUTION_LOG.md. NO action-space/observation file reopened; NO
  reward-function env code (that is STEP 11); NO PPO.
- **Tests:** `.venv/Scripts/python.exe -m unittest discover -s tests -v` → 21 ok
  (12 STEP 8 + 9 STEP 7): pure-helper determinism, 10 components, analytic effort
  (dim 7 / L1 14 / L2² 28), integrity flags, service set 121/5, per-ts vs validated
  accounting <1e-6, reference reproduces baseline, every config finite & 193 ts,
  10×10 correlation matrix, pooled stats finite, formulations PROPOSED not APPROVED.
- **Risks/caveats:** leak instrument uncalibrated → RELATIVE response only, never a
  calibrated leakage claim (R3); actuator-effort scale analytic (realised movement is a
  HYPOTHESIS TO TEST); scales cover a representative in-bounds set, not the full joint
  interior (R1b → STEP-9/STEP-12); weight choice can still induce reward hacking → must
  be validated after selection. Deps for PPO still missing (R4). Nothing frozen.
- **Next action:** researcher reviews D-P6-005 and selects ONE formulation + weights
  (separate approved decision); then STEP 9 hard safety clamp (clamp to approved bounds,
  protect worst-node pressure); reward function itself is STEP 11. DO NOT start PPO (§16).


## WU-10 — STEP 8: empirical comparison of the four candidate formulations (2026-09-27, current session)

- **Trigger:** researcher instruction to produce transparent, reproducible evidence
  comparing F1–F4 for the D-P6-005 decision — explicitly WITHOUT selecting a winner,
  assigning scores/ranks/tiers, tuning weights, adding a STEP-9 safety clamp, or
  training PPO. Continuation of WU-9 (measurement), not a re-measurement.
- **Method:** re-ran the SAME 19 validated static in-bounds commands (reference,
  joint PRV lower/upper, 10 per-PRV edges, 2 pump edges, 4 mixed corners) under the
  validated 96 h protocol (1800 s report / 180 s rule / ACC 1e-5 / TRIALS 2000 / PDA),
  reusing the WU-9 component extractor verbatim, and evaluated F1–F4 per report
  timestep. Frozen normalisation constants (§8.6) + derived `unserved_ref=14.98484`
  were LOADED from the WU-9 artefact — no online/running/test-set statistics.
- **PROVISIONAL comparison-only parameters (NOT proposed weights):** F1 `w_L=w_U=w_P=w_A=1,
  w_E=0`; F2 `Λ=20,BIG=100`; F3 `w_U=w_P_safety=1`; F4 `θ=20 psi,c_soft=10,c_hard=100,
  eps_effort=0.01`. Labelled "PROVISIONAL FOR COMPARISON ONLY" in code, JSON, and spec.
- **Reproducibility gate (asserted, all passed):** leak_ref_abs_diff 0.0, req_ref_abs_diff
  0.0, reference n_below20 386, n_negative 0, per-timestep vs validated accounting max
  abs diff 0.0, all reward values finite, native_controls_count 5, no topology / native-
  rule change, no future information.
- **Descriptive findings (NO ranking, NO winner):**
  1. **Induced incentive (provisional weights):** all four rewards place their
     incentive-argmax (highest-mean-reward tested command = incentive direction, NOT a
     formulation ranking) on the SAME bound command `prv_176_upper` (min service ≈4.17
     psi, mean n_below20 1.0). Reward spreads: F1 0.541, F3 0.525, F4 0.526, F2 110.5.
  2. **Isolated objectives oppose (Pathology A/B):** leak-only argmax `prv_lower_pump_lower`
     (min service 1.295 psi vs ref 4.165); service-only argmax `prv_176_upper` (leak_norm
     1.0155 > ref 1.0). Consistent with WU-9 correlations.
  3. **Hard-20-psi degeneracy (Pathology F/G):** frac pooled ts with ≥1 node <20 psi = 1.0
     (incl. baseline's 2 chronic nodes); frac with a negative node = 0.0. F2 (BIG·n_below20)
     and F4 (θ=20) therefore fire on the baseline itself (ill-posed constraint, little leak
     gradient); F4 at θ=0 never triggers → collapses to leak-corner-seeking while "safe".
  4. **Actuator-penalty domination (Pathology C, analytic):** normalised leak term spans
     only 0.108 across the tested set vs a unit-weight max single-step move cost of 1.0 →
     an un-tuned effort weight could dominate leakage; realised movement is 0 in static
     runs (HYPOTHESIS TO TEST); effort MUST use the COMMANDED action (G12 reset ambiguity).
  5. **Weight sensitivity (Pathology H):** varying provisional weights shifts the
     incentive-argmax (F1 `w_P=0`→`prv_175_lower`, `w_P≥0.5`→`prv_176_upper`; F3 safety=0
     →`prv_lower_pump_lower`; F4 θ 0↔20 flips) — exactly why selection is the researcher's.
- **Safety implication:** a leakage-driving reward sends its incentive to the PRV lower
  corner (min service ≈1.3 psi) → a state-dependent safety mechanism is REQUIRED, but that
  is STEP 9 (unapproved) and was NOT added. Action bounds (STEP 6) kept distinct from a
  safety clamp; no clamp inserted into any formulation or the env.
- **Decision:** D-P6-005 **remains PROPOSED** — this WU adds comparison evidence only; no
  formulation/weights selected, no score/rank/tier/winner assigned.
- **Decision class:** VALIDATED FACT (per-timestep measured reward behaviour under the
  validated instrument) + DECISION REQUIRED (researcher selection of formulation + weights).
- **Files changed:** src/validation/p6_s8_reward_formulation_comparison.py (new);
  results/phase6/p6_s8_reward_formulation_comparison.json (new);
  tests/test_reward_formulation_comparison.py (new); docs/PHASE6_REWARD_SPEC.md (§8.9–§8.11);
  docs/PHASE6_DECISION_REGISTER.md (D-P6-005 comparison-evidence note, status UNCHANGED);
  docs/PHASE6_EVIDENCE_INDEX.md; docs/RECOVERY.md; PROJECT_STATE.yaml;
  docs/PHASE6_EXECUTION_LOG.md. NO action-space/observation file reopened; NO
  reward-function env code (STEP 11); NO STEP-9 clamp; NO PPO.
- **Tests:** `.venv/Scripts/python.exe -m unittest discover -s tests -v` → 44 ok
  (23 comparison + 12 STEP 8 + 9 STEP 7): normalization exactness/signs, F1 monotonic in
  leak, F2 count scaling, F3 baseline-relative zero point, F4 lexicographic branches,
  unserved clip ≥0, movement 0 for static hold, analytic effort dim-7 ceiling, incentive-
  argmax picks max mean, PART-13 keys present, reference reproduces baseline, per-ts
  accounting <1e-6, service mask 121/5, frozen constants, no topology/future info,
  status asserts D-P6-005 PROPOSED and 4 formulations.
- **Risks/caveats:** effort scale analytic (realised movement a HYPOTHESIS); leak
  instrument uncalibrated → RELATIVE only (R3); coverage = edges+corners+reference, NOT the
  joint interior (R1b → STEP-9/STEP-12); provisional weights are illustrative — a different
  choice shifts incentives; PPO deps still missing (R4). Nothing frozen; D-P6-005 open.
- **Next action:** researcher selects ONE formulation + weights (resolves D-P6-005); then
  STEP 9 hard safety clamp; reward function is STEP 11. DO NOT start PPO (§16).

---

## WU-11 — STEP 8: D-P6-005 reward decision brief (this session)

- **Objective:** Convert the completed STEP 8 evidence (WU-9 scale analysis + WU-10
  formulation comparison) into a decision-ready scientific brief so the researcher can
  explicitly select ONE reward formulation + parameters. The AI prepares; the researcher decides.
- **Starting state:** HEAD `262b738`; STEP 8 measurement + comparison COMPLETE; D-P6-004
  APPROVED & FROZEN; D-P6-005 PROPOSED; action space frozen. No decision-brief files existed.
- **Evidence inspected:** `results/phase6/p6_s8_reward_scale_analysis.json` (pooled stats,
  correlations, pathologies, frozen constants), `results/phase6/p6_s8_reward_formulation_comparison.json`
  (per-config metrics, induced incentives, pathologies A–H, sensitivity sweeps, reproducibility),
  `results/phase6/p6_s7_state_spec.json`, `docs/PHASE6_DECISION_REGISTER.md`.
- **Action taken:** Wrote a pure aggregator (`src/validation/p6_d_p6_005_decision_brief.py`)
  that RE-LOADS the two frozen artefacts (no EPANET, no PPO, no RNG), re-checks the frozen
  normalisation constants match across artefacts (abs diff <1e-9), assembles the decision-brief
  JSON with `researcher_selection: null`, and runs 11 internal self-checks. Authored the 11-section
  `docs/PHASE6_D_P6_005_DECISION_BRIEF.md`. Defined FOUR "PROVISIONAL CANDIDATE — NOT APPROVED"
  parameterizations whose constants trace to measured scales (e.g. C-A `w_A=0.1` from the measured
  0.108 leak-term range), NOT tuned to any result.
- **Result:** `docs/PHASE6_D_P6_005_DECISION_BRIEF.md` + `results/phase6/p6_d_p6_005_decision_brief.json`
  created. The chronic sub-20-psi analysis concludes a HARD 20-psi reward constraint is ill-posed on
  the native baseline (frac_ts_any_node_below_20psi = 1.0); dense deficit / worst-node / baseline-relative
  signals are the defensible reward-level channels; the enforced 20-psi guarantee is STEP-9's.
- **Decision:** D-P6-005 **remains PROPOSED / DECISION PENDING RESEARCHER** — the brief prepares the
  gate; no formulation selected/scored/ranked, no weights tuned, no STEP-9 clamp, no PPO.
- **Decision class:** DECISION REQUIRED (researcher selection) + VALIDATED FACT (re-used measured evidence).
- **Files changed:** src/validation/p6_d_p6_005_decision_brief.py (new);
  results/phase6/p6_d_p6_005_decision_brief.json (new); docs/PHASE6_D_P6_005_DECISION_BRIEF.md (new);
  tests/test_decision_brief.py (new); docs/PHASE6_DECISION_REGISTER.md (WU-11 note, status UNCHANGED);
  docs/PHASE6_EVIDENCE_INDEX.md; docs/RECOVERY.md; PROJECT_STATE.yaml; docs/PHASE6_EXECUTION_LOG.md.
  NO action-space/observation file reopened; NO STEP-11 env reward code; NO STEP-9 clamp; NO PPO.
- **Tests:** `.venv/Scripts/python.exe -m unittest discover -s tests -v` → **63 ok**
  (19 decision-brief + 23 comparison + 12 STEP 8 + 9 STEP 7): brief status PROPOSED,
  researcher_selection null, no winner/ranking keys, all values finite, constants match frozen WU-9,
  action dim 7 + ordering + bounds unchanged, observation dim 139, service mask 121/5, candidates all
  NOT APPROVED (2–4), deterministic regeneration byte-reproduces the artefact, chronic-baseline &
  safety-separation documented, WU-9/WU-10 integrity preserved.
- **Risks/caveats:** realised movement distribution unknown → effort scale analytic (HYPOTHESIS);
  leak instrument uncalibrated → RELATIVE only (R3); joint 5-D box safety single-corner only (R1b →
  STEP-9/12); weights/Λ/θ are researcher value judgements; PPO deps still missing (R4). D-P6-005 open.
- **Next action:** researcher completes the decision block (selects ONE formulation + parameters);
  then STEP 9 safety clamp; reward function is STEP 11. DO NOT start PPO (§16).

---

## WU-12 — STEP 8: D-P6-005 researcher-facing decision presentation (this session)

- **Objective:** Transform the already-persisted D-P6-005 evidence (WU-9/10/11) into a
  concise, researcher-facing decision presentation so the researcher can make an explicit
  D-P6-005 decision. DOCUMENTATION / DATA-EXTRACTION ONLY — measures nothing new, selects
  no formulation, chooses no weights, adds no STEP-9 clamp, implements no reward.py, starts
  no PPO. D-P6-005 stays PROPOSED; researcher_selection stays null.
- **Starting state:** HEAD `1ad6392`; STEP 8 measurement (WU-9) + comparison (WU-10) +
  decision brief (WU-11) COMPLETE; D-P6-004 APPROVED & FROZEN; D-P6-005 PROPOSED; action
  space frozen. No researcher-summary files existed.
- **Evidence inspected:** `results/phase6/p6_d_p6_005_decision_brief.json` (WU-11, the sole
  numeric source), and — for provenance references only — `p6_s8_reward_scale_analysis.json`
  (WU-9) and `p6_s8_reward_formulation_comparison.json` (WU-10). No EPANET, no re-run:
  Git HEAD + working tree verified consistent, so no genuine inconsistency was found and no
  experiment was repeated.
- **Action taken:** Wrote a PURE re-shaping generator `src/validation/p6_d_p6_005_researcher_summary.py`
  that RE-LOADS the WU-11 brief, copies every equation/constant/weight verbatim (anti-drift),
  authors ONLY plain-language Persian interpretation + short descriptive dimension notes, keeps
  `researcher_selection=null`, and runs 12 internal self-checks (incl. a forbidden-key-token scan
  for winner/rank/tier/score/best/superior/optimal/preferred/recommend). Emitted
  `results/phase6/p6_d_p6_005_researcher_summary.json` (deterministic; re-running byte-reproduces
  it). Authored `docs/PHASE6_D_P6_005_RESEARCHER_SUMMARY.md` (§A current state; §B exact C-A/C-B/C-C/C-D
  definitions verbatim; §C plain-language Persian per candidate; §D OBSERVED/INFERRED/UNRESOLVED;
  §E the 12 decision dimensions descriptive-only; §F the central trade-off + reward-vs-STEP-9
  two-layer separation; §G the BLANK 7-field researcher decision form; §H provenance). Added the
  21-test battery `tests/test_researcher_summary.py`.
- **Result:** Presentation on disk. Two DISTINCT `unserved_ref` values preserved exactly (F3
  accounting 14.98483697365873 vs C-C DSR-implied 15.103309701248634 — NOT conflated). All four
  candidates labelled "PROVISIONAL CANDIDATE — NOT APPROVED"; no ranking/winner/score keys; frozen
  constants, action_dim 7, observation_dim 139, service mask 121/5 all unchanged; researcher_selection
  null; 12 self_checks all true.
- **Decision:** D-P6-005 **remains PROPOSED / DECISION PENDING RESEARCHER** — WU-12 only presents;
  nothing selected/scored/ranked/recommended; scientific state unchanged.
- **Decision class:** DECISION REQUIRED (researcher selection) + VALIDATED FACT (re-used measured evidence).
- **Files changed:** src/validation/p6_d_p6_005_researcher_summary.py (new);
  results/phase6/p6_d_p6_005_researcher_summary.json (new); docs/PHASE6_D_P6_005_RESEARCHER_SUMMARY.md (new);
  tests/test_researcher_summary.py (new); PROJECT_STATE.yaml; docs/PHASE6_EVIDENCE_INDEX.md;
  docs/RECOVERY.md; docs/PHASE6_EXECUTION_LOG.md. NO action-space/observation file reopened; NO
  STEP-11 env reward code; NO STEP-9 clamp; NO PPO; NO evidence artefact modified.
- **Tests:** `.venv/Scripts/python.exe -m unittest discover -s tests -v` → **84 ok**
  (21 researcher-summary + 19 decision-brief + 23 comparison + 12 STEP 8 + 9 STEP 7): summary loads,
  decision_id D-P6-005, status PROPOSED, researcher_selection null, four exact candidate ids all NOT
  APPROVED, candidate numbers match the WU-11 brief, C-C unserved_ref==15.103309701248634 distinct from
  F3 accounting 14.98483697365873, frozen constants match brief, no forbidden key tokens, action space
  unchanged, obs dim 139, service 121/5, families F1–F4, plain_language_fa four questions, no
  topology/native-rule change, all finite, self_checks all true, deterministic byte-reproduce,
  evidence_references present.
- **Risks/caveats:** presentation faithfully mirrors WU-11 — it inherits, does not resolve, the open
  D-P6-005 selection; leak instrument uncalibrated → RELATIVE only (R3); effort scale analytic
  (HYPOTHESIS); joint 5-D box safety single-corner only (R1b → STEP-9/12); PPO deps missing (R4).
  Nothing frozen; D-P6-005 open.
- **Next action:** researcher completes the §G decision form (selects ONE formulation + parameters,
  resolves D-P6-005); then STEP 9 safety clamp; reward function is STEP 11. DO NOT start PPO (§16).

---

## WU-13 — Record D-P6-005 = APPROVED (researcher selected C-A_F1_balanced_dense) — 2026-09-27

- **Objective:** Record the researcher's explicit D-P6-005 decision. The researcher selected
  **C-A_F1_balanced_dense** (Formulation F1 — normalized weighted sum) with weights
  `w_L=1.0, w_U=1.0, w_P=1.0, w_A=0.1, w_E=0.0`. DOCUMENTATION ONLY — verify the selection is
  internally consistent with the frozen repository, record it in the authoritative state/register/
  human-readable docs, preserve all evidence; select/score/rank NOTHING new, implement no reward.py,
  start no PPO.
- **Starting state:** HEAD `4f20a3a`; STEP 8 WU-9/WU-10/WU-11/WU-12 COMPLETE; D-P6-004 APPROVED &
  FROZEN; D-P6-005 **PROPOSED / researcher_selection=null**; action space APPROVED & FROZEN.
- **Evidence inspected:** `results/phase6/p6_d_p6_005_decision_brief.json`
  `candidate_parameterizations[C-A_F1_balanced_dense]` (equation, constants,
  `provisional_weights` w_A=0.1/w_E=0.0) and `normalization_constants_frozen`
  (leak_ref 84.72988433677985, req_ref 906.3987348621764, deficit_ref 28.671793365478514,
  power_ref 88.10062475649187, movement_L2sq_max 28.0); `PROJECT_STATE.yaml`
  `reward.fixed_normalization_constants`; `docs/PHASE6_DECISION_REGISTER.md` D-P6-005 section.
- **Action taken:** (1) Verified the researcher's approved equation, weights and five constants equal
  the on-disk `C-A_F1_balanced_dense` candidate and the frozen normalisation block **exactly** — no
  contradiction, so §1's "do not alter unless a contradiction is found" holds and no value was changed.
  (2) Recorded `D-P6-005 = APPROVED` in `PROJECT_STATE.yaml` (`reward.approved` block +
  `reward.status`/`register_id`/`next`; `step8_reward_design`→APPROVED; `step9`→IN PROGRESS;
  `next_action`/`still_open`/`session_checkpoint`). (3) Appended a
  "**D-P6-005 — RESOLUTION: APPROVED (C-A_F1_balanced_dense)**" section to
  `docs/PHASE6_DECISION_REGISTER.md` (factual rationale; C-B/C-C/C-D retained as unselected; both
  C-C `unserved_ref` values preserved with provenance as non-blocking debt; evidence-preservation
  note). (4) Added RESOLUTION banners + filled the decision forms in
  `docs/PHASE6_D_P6_005_DECISION_BRIEF.md` (§11) and `docs/PHASE6_D_P6_005_RESEARCHER_SUMMARY.md` (§G).
  (5) **Left UNCHANGED** the WU-11/WU-12 generated JSON snapshots, their pure generators, and their
  byte-reproduction test batteries (`tests/test_decision_brief.py`, `tests/test_researcher_summary.py`)
  — they are the frozen pre-decision evidence (status PROPOSED, researcher_selection=null) and are
  intentionally not rewritten (CLAUDE.md §11/§12).
- **Result:** D-P6-005 resolved. Approved reward (per-step NEGATIVE cost, higher = better):
  `r_t = -w_L*(leak_t/leak_ref) -w_U*(unserved_t^+/req_ref) -w_P*(deficit_t/deficit_ref)
  -w_A*(||da_t||^2/movement_L2sq_max) -w_E*(power_t/power_ref)`, `unserved_t^+=max(0,unserved_t)`,
  `da_t` on COMMANDED normalised actions (static hold → 0), `w_E=0` disables energy numerically
  while keeping the term explicit. Authoritative machine-readable record = `reward.approved`
  (+ the STEP-9 JSON `d_p6_005_decision` block, WU-14); authoritative human-readable record =
  the register RESOLUTION + the two decision-doc banners.
- **Decision:** **D-P6-005 = APPROVED (2026-09-27), C-A_F1_balanced_dense.** Approval is specific to
  THIS thesis environment/experimental design — NOT a claim that C-A is best/optimal/superior for
  water-network DRL in general; no formulation was scored or ranked.
- **Decision class:** RESEARCHER DECISION (recorded) + VALIDATED FACT (consistency check vs frozen repo).
- **Files changed:** PROJECT_STATE.yaml; docs/PHASE6_DECISION_REGISTER.md;
  docs/PHASE6_D_P6_005_DECISION_BRIEF.md; docs/PHASE6_D_P6_005_RESEARCHER_SUMMARY.md;
  docs/PHASE6_EXECUTION_LOG.md; docs/PHASE6_EVIDENCE_INDEX.md; docs/RECOVERY.md. UNCHANGED (deliberate):
  results/phase6/p6_d_p6_005_decision_brief.json, results/phase6/p6_d_p6_005_researcher_summary.json,
  their generators, tests/test_decision_brief.py, tests/test_researcher_summary.py. NO reward.py, NO
  PPO, NO action-space/observation reopened.
- **Tests:** existing full battery re-run after the doc edits (the byte-reproduction batteries read
  only the untouched JSON snapshots, so they must still pass at **84 ok**); see WU-14 for the run that
  also adds the STEP-9 tests.
- **Risks/caveats:** the reward SHAPES toward service but does NOT enforce a pressure bound — the
  boundary-seeking optimum at the PRV lower corner (min svc ~1.295 psi) means a state-dependent hard
  safety mechanism is required (STEP 9). Leak instrument uncalibrated → relative response only (R3);
  effort scale analytic in statics (HYPOTHESIS); joint 5-D box safety single-corner only (R1b);
  C-C `unserved_ref` discrepancy documented non-blocking (C-A/F1 does not use it); PPO deps missing (R4).
- **Next action:** WU-14 — STEP 9 state-dependent safety-mechanism DESIGN ANALYSIS (characterise
  S1-S4, NOT ranked; no production wrapper; no reward.py; no PPO).

---

## WU-14 — STEP 9 state-dependent safety-mechanism DESIGN ANALYSIS (characterisation only) — 2026-09-27

- **Objective:** Begin STEP 9 — design (not implement) a state-dependent safety mechanism that
  protects the hydraulic system from unsafe consequences of DRL actions, kept DISTINCT from the frozen
  action-space bounds. Characterise four candidate admissibility mechanisms against measured evidence,
  report each on a fixed schema, test baseline-compatibility, and state action-space-coverage limits.
  **Do NOT rank the candidates, do NOT choose the final rule, do NOT implement the production wrapper,
  do NOT implement reward.py, do NOT start PPO.**
- **Starting state:** D-P6-005 APPROVED (WU-13, C-A_F1_balanced_dense). No STEP-9 artefacts existed.
- **Evidence inspected (LOADED, not re-measured):** `results/phase6/p6_d_p6_005_decision_brief.json`
  (`chronic_baseline_service_issue`: 386 node-ts <20psi, 0 negative, frac_ts_any<20psi=1.0, min svc
  4.16452169418335 psi; `pathology_results_wu10.A_leakage_only_collapses_service`: leak-only argmax
  `prv_lower_pump_lower`, min svc 1.2946763038635254 psi; `threshold_handling_options`),
  `results/phase6/p6_s8_reward_scale_analysis.json` (frozen constants; boundary-seeking finding),
  `results/phase6/p6_s7_state_spec.json` (observation_dim 139, service mask 121/5), and the frozen
  action space (action_dim 7, bounds, ordering).
- **Action taken:** Wrote a PURE aggregator `src/validation/p6_s9_safety_design_analysis.py` (no
  EPANET / PPO / RNG / new measurement) that RE-LOADS the measured evidence, characterises
  **S1** (absolute worst-node pressure threshold), **S2** (min-pressure degradation vs current state),
  **S3** (pressure-deficit increase vs current state), **S4** (negative-pressure hard backstop) on a
  fixed 11-field schema (exact rule · information required · computational cost · baseline
  compatibility · false-positive risk · false-negative risk · PPO compatibility · 30-min-interval
  compatibility · requires-hydraulic-look-ahead · preserves-determinism · notes), records the §12
  baseline-compatibility verdicts and §13 action-space-coverage limits, embeds the `d_p6_005_decision`
  block (C-A, APPROVED), and runs self-checks (action_dim 7, observation_dim 139, D-P6-005 equation
  consistent with C-A, all values finite, forbidden-key-token scan). Emitted
  `results/phase6/p6_s9_safety_design_analysis.json` (deterministic byte-reproduce). Authored
  `docs/PHASE6_STEP9_SAFETY_DESIGN.md`. Added `tests/test_safety_design_analysis.py`.
- **Result:** (to be finalised in this work unit; see the JSON + doc for the characterisation).
- **Decision class:** DESIGN ANALYSIS (characterisation only; no mechanism selected or ranked).
- **Files changed:** src/validation/p6_s9_safety_design_analysis.py (new);
  results/phase6/p6_s9_safety_design_analysis.json (new); docs/PHASE6_STEP9_SAFETY_DESIGN.md (new);
  tests/test_safety_design_analysis.py (new); PROJECT_STATE.yaml; docs/PHASE6_EVIDENCE_INDEX.md;
  docs/RECOVERY.md; docs/PHASE6_EXECUTION_LOG.md.
- **Tests:** `.venv/Scripts/python.exe -m unittest discover -s tests -v` → full battery (84 prior +
  STEP-9 tests).
- **Risks/caveats:** all four candidates are action-consequence checks → each needs a one-step
  hydraulic look-ahead (or verify-and-fallback); a naive absolute min<20 reject is ILL-POSED on the
  chronic-sub-20 baseline; joint 5-D box safety is single-corner only (R1b) so coverage is explicitly
  partial; no production wrapper implemented; deps for PPO still missing (R4).
- **Next action:** researcher selects a STEP-9 mechanism; the enforced production safety wrapper and
  reward.py are STEP 11 (deps-blocked). No PPO.


---

## WU-15 — STEP 9 empirical characterisation of candidate mechanisms & handling policies — 2026-09-28

- **Objective:** Empirically MEASURE candidate safety mechanisms S1-S4 and action-handling policies
  H1-H3 on the frozen network so the researcher can make the STEP-9 decision later. **EVIDENCE ONLY —
  nothing selected/ranked/scored/recommended (researcher_selection=null).** No wrapper, no reward.py,
  no PPO.
- **Action taken:** Wrote `src/validation/p6_s9_safety_mechanism_characterization.py` reusing the
  validated WU-8 instrument unchanged (10 EPANET solves, ~8s, no RNG); measured per rule × provisional
  threshold the descriptive activation fields (no FP/FN — no oracle) and per policy the executed action;
  reported TWO look-ahead views per transition (strict single-step shared_initial vs sustained 96h
  horizon), surfacing the tank-divergence caveat (severe `prv_lower_pump_lower` ~5.53 psi worst-node at
  shared-initial vs ~1.29 psi sustained). Emitted
  `results/phase6/p6_s9_safety_mechanism_characterization.json` (carries `generated_utc`, NOT
  byte-reproduced), appended sections 10.1-10.9 to `docs/PHASE6_STEP9_SAFETY_DESIGN.md` (WU-14
  sections 1-9 preserved), added `tests/test_safety_mechanism_characterization.py` (26 tests).
- **Result:** committed as e09264c (deliverable) + 0ed1c9e (checkpoint). Full battery 125 OK.
- **Decision class:** EMPIRICAL EVIDENCE (characterisation only; nothing selected).
- **Next action:** WU-16 — TEMPORAL characterisation (single-step vs trajectory-aware safety).

---

## WU-16 — STEP 9 TEMPORAL characterisation (single-step vs trajectory-aware safety) — 2026-09-28

- **Objective:** Determine empirically whether a purely SINGLE-STEP (or short few-step) post-action
  safety check can MISS delayed hydraulic deterioration that emerges over the sustained 96h horizon as
  tank states evolve — the central single-step-vs-trajectory-aware comparison. Motivated by the WU-15
  finding that `prv_lower_pump_lower` reads ~5.53 psi worst-node at the decision instant but ~1.29 psi
  sustained. **EVIDENCE ONLY — no mechanism, handling policy, or look-ahead HORIZON is
  selected/ranked/scored/recommended (researcher_selection=null).** No wrapper, no reward.py, no PPO.
- **Starting state:** WU-14 (0086a0a) + WU-15 (e09264c) done. Reward D-P6-005 APPROVED; observation
  and action space FROZEN. No temporal artefact existed.
- **Action taken:** Wrote `src/validation/p6_s9_temporal_safety_characterization.py` reusing the WU-8
  instrument (p6_s8) and the WU-15 module (p6_s9 safety_mechanism_characterization) unchanged — same
  working INP (sha256 53015ba9…20a9), same 121/5 mask, `n_native_controls=5` read from disk. Ran 3 full
  96h EPS solves (reference_nominal, prv_lower_pump_lower, prv_all_lower); read the WU-15 commands and
  5.53/1.29 anchors from persisted data and reproduced them exactly (abs diff 0.0, normalized action
  [-1]×7 exact). Measured per-config trajectory metrics (p_min_horizon, t_pmin index+hours, D_max/D_cum,
  DSR_min, Q_unserved_max, Q_leak stats, any_negative/sub20 descriptive), VIEW A (single-step decision
  instant) vs VIEW B (full-horizon trajectory), temporal rules TS1-TS4 across look-ahead horizons
  H=1/2/4/8/full, tank/pump/native-rule evolution, computational cost, and PPO compatibility per
  horizon. Emitted `results/phase6/p6_s9_temporal_safety_characterization.json` (carries
  `generated_utc`, NOT byte-reproduced), appended section 11 to `docs/PHASE6_STEP9_SAFETY_DESIGN.md`
  (WU-14 §1-9 and WU-15 §10.1-10.9 preserved), added `tests/test_temporal_safety_characterization.py`
  (20 tests).
- **Result:** Central finding on the tested corner — severe worst-node p_min sits at ~5.53 psi at the
  decision instant, ~5.15-5.46 psi over horizons H=1/2/4/8 (0.5-4h), then collapses to ~1.29 psi at
  report index 192 (96.0h, the horizon END; understatement 4.23 psi). It first drops below θ_p=5 psi at
  index 13 (6.5h) — beyond H=8 (4h) — so TS1@θ=5 does NOT activate for H≤8 yet DOES over the full
  horizon: single-step non-activation followed by delayed deterioration (NOT "false negative"; no
  oracle → no FP/FN). Relative TS2@ε=0 reacts even at H=1 (worst Δp_min −0.097→−4.30); negative backstop
  TS4 never fires (max_N_neg=0 everywhere); identity hold reproduces the chronic absolute-20
  ill-posedness (TS1@20 activates on baseline worst 4.16452 psi, TS2 never). Tank drawdown
  (TANK-130 −9.79 ft, TANK-131 −12.74 ft by t_pmin) is coincident with the collapse (no causal
  overclaim); native pump-rule events 0 (severe) vs 14 (reference/prv_all_lower). Committed as 6bf4820
  (deliverable) + checkpoint. Full battery 145 OK (125 prior + 20 new).
- **Decision class:** EMPIRICAL EVIDENCE (temporal characterisation only; nothing selected).
- **Files changed:** src/validation/p6_s9_temporal_safety_characterization.py (new);
  results/phase6/p6_s9_temporal_safety_characterization.json (new);
  tests/test_temporal_safety_characterization.py (new);
  docs/PHASE6_STEP9_SAFETY_DESIGN.md (appended §11); PROJECT_STATE.yaml;
  docs/PHASE6_EVIDENCE_INDEX.md; docs/RECOVERY.md; docs/PHASE6_EXECUTION_LOG.md.
- **Risks/caveats:** finite look-ahead ≠ long-term safety guarantee, and even the full-horizon check is
  bounded by the 96h EPS; coverage is 3 operating points only (R1b — do NOT claim the 7-D box globally
  safe); no oracle → no FP/FN; apply-once-then-revert not simulated (would change n_native_controls);
  detection ≠ enforcement/guarantee; PPO deps still missing (R4).
- **Next action:** researcher selects a STEP-9 mechanism + threshold + clip-vs-reject handling + look
  ahead horizon (all PENDING, not auto-made); production wrapper and reward.py are STEP 11
  (deps-blocked). No PPO.


## WU-17 — STEP 9 state-dependent safety-mechanism DECISION BRIEF (evidence synthesis / decision-gate prep) — 2026-09-28

- **Situation:** WU-14 (design), WU-15 (empirical), and WU-16 (temporal) had each MEASURED the STEP-9
  candidate evidence, but the four coupled STEP-9 decisions (A safety metric/rule; B threshold/tolerance;
  C look-ahead horizon; D action-handling policy) were scattered across three artefacts. The researcher
  needs ONE decision-ready brief that consolidates the evidence and makes the four decisions explicit
  WITHOUT making any of them.
- **Starting state:** WU-16 (6bf4820 + checkpoint 287b1b2) done; reward D-P6-005 APPROVED & FROZEN;
  observation D-P6-004 and action space D-P6-001/002/003 APPROVED & FROZEN. No decision brief existed.
- **Action taken:** Wrote `src/validation/p6_s9_decision_brief.py` as a PURE AGGREGATOR (matching the
  WU-11 pattern) — imports only `json/math/pathlib`; re-loads the four frozen JSON artefacts
  (`p6_s9_safety_design_analysis.json` WU-14, `p6_s9_safety_mechanism_characterization.json` WU-15,
  `p6_s9_temporal_safety_characterization.json` WU-16, `p6_d_p6_005_decision_brief.json` WU-11); copies
  their evidence sub-trees verbatim; re-checks the 5 frozen normalisation constants and the
  cross-artefact baseline/collapse anchors; writes `researcher_selection=null`; runs 32 self-checks
  (SystemExit on any failure). Runs NO EPANET/PPO/RNG, carries NO `generated_utc`, and byte-reproduces
  on re-run. Emitted `results/phase6/p6_s9_decision_brief.json` (32 top-level keys), wrote the
  17-section `docs/PHASE6_STEP9_DECISION_BRIEF.md` (§17 researcher decision block A-G left BLANK), and
  added `tests/test_step9_decision_brief.py` (26 tests, incl. a deterministic
  rebuild-equals-persisted-bytes integrity check).
- **Result:** The brief FRAMES the four decisions and makes none. Four candidate configurations —
  K1 (arch D backstop+relative), K2 (arch C aggregate-deficit look-ahead), K3 (arch A immediate
  well-posed absolute), K4 (arch B rolling absolute look-ahead) — are ALL `PROVISIONAL CANDIDATE - NOT
  APPROVED`; the `decision_matrix` (4 rows A-D) is explicitly NOT ordered/scored/marked; no forbidden
  key token (winner/rank/tier/score/best/superior/optimal/preferred/recommend) appears in any KEY;
  every threshold is a swept provisional grid value or an evidence-supported gate (none invented). The
  WU-16 central finding is carried verbatim: severe `prv_lower_pump_lower` reads 5.527866840362549 psi
  worst-node at the decision instant but collapses to 1.2946763038635254 psi at report index 192 (96h);
  TS1 θ_p=5 does NOT activate for H≤8 yet DOES at full; TS2 rel ε_p=0 fires from H=1; TS4 negative
  backstop never fires (max_N_neg=0); a naive absolute-20 reject is ill-posed on the chronic baseline
  (386 sub-20 node-ts, worst 4.16452 psi). Committed 58e1790 (deliverable) + checkpoint. Full battery
  171 OK (145 prior + 26 new WU-17).
- **Decision class:** DECISION-GATE PREPARATION (evidence synthesis only; nothing selected/ranked/scored/
  recommended; researcher_selection=null). STEP-9 stays PROPOSED / PENDING RESEARCHER; project NOT
  PPO-ready.
- **Files changed:** src/validation/p6_s9_decision_brief.py (new);
  results/phase6/p6_s9_decision_brief.json (new); tests/test_step9_decision_brief.py (new);
  docs/PHASE6_STEP9_DECISION_BRIEF.md (new); PROJECT_STATE.yaml; docs/PHASE6_EVIDENCE_INDEX.md;
  docs/RECOVERY.md; docs/PHASE6_EXECUTION_LOG.md.
- **Risks/caveats:** the brief inherits every WU-14/15/16 coverage limit — no validated safe/unsafe
  oracle (activation counts are descriptive, NOT FP/FN rates); single lower-corner coverage only (R1b);
  the well-posed absolute-floor crossover horizon between H=8 (4h) and full (96h) is UNTESTED (no new
  experiment mandated); thresholds encode a value judgement that is the researcher's, not a measured
  quantity; the effort-term-under-intervention (proposed vs executed action) is an open training-
  integration question coupled to decision D. Aggregation faithfulness is guaranteed by the
  rebuild-equals-persisted-bytes test, not by manual inspection.
- **Next action:** researcher completes the §17 decision block (A-G), records the selection as a NEW
  D-P6-006 in docs/PHASE6_DECISION_REGISTER.md, updates PROJECT_STATE.yaml, and only then proceeds to
  the STEP-9 wrapper implementation and PPO readiness. No wrapper, no reward.py, no PPO until then.


## WU-18 — STEP 9 FINAL SAFETY-ARCHITECTURE DECISION REVIEW (readiness judgement + final-design packaging) — 2026-09-28

- **Situation:** WU-14/15/16 MEASURED the STEP-9 candidate evidence and WU-17 FRAMED the four coupled decisions, but no artefact had yet JUDGED whether the STEP-9 safety architecture is scientifically defensible and operationally implementable, nor PACKAGED the final provisional designs for the researcher. This is the FINAL scientific review immediately preceding production safety-wrapper implementation. **It JUDGES readiness and PACKAGES the (<=3) final PROVISIONAL designs WITHOUT making the STEP-9 selection** (researcher_selection=null; no mechanism/threshold/horizon/handling policy selected/ranked/scored/recommended).
- **Starting state:** WU-17 (58e1790 + checkpoint f49114b) done; reward D-P6-005 APPROVED & FROZEN; observation D-P6-004 and action space D-P6-001/002/003 APPROVED & FROZEN. No final review artefact existed.
- **Action taken:** Wrote `src/validation/p6_s9_final_decision_review.py` as a PURE AGGREGATOR (matching the WU-11/WU-17 pattern) — imports only `json/math/pathlib`; re-loads the frozen WU-14/15/16/17 + WU-11 artefacts; copies evidence sub-trees verbatim; re-checks the 5 frozen normalisation constants and the cross-artefact baseline/collapse anchors; writes `researcher_selection=null` and a BLANK 7-field D-P6-006 form; runs 31 self-checks (SystemExit on any failure). Runs NO EPANET/PPO/RNG, carries NO `generated_utc`, byte-reproduces on re-run. Emitted `results/phase6/p6_s9_final_decision_review.json` (16 top-level keys), wrote the 18-section `docs/PHASE6_STEP9_FINAL_DECISION_REVIEW.md` (§18 D-P6-006 form A-G BLANK), and added `tests/test_step9_final_decision_review.py` (28 tests, incl. deterministic rebuild-equals-persisted-object AND rebuild-equals-persisted-bytes).
- **Result:** Readiness verdict = **DECISION-READY** (`verdict_is_not_a_selection=true`; `status_after_this_review` reaffirms STEP-9 remains PROPOSED). Three final PROVISIONAL designs packaged in DEFINITIONAL order only (`not_ordered_by_quality=true`, `order_is_definitional_not_quality=true`), all `PROVISIONAL - NOT APPROVED`: F1 (arch D negative backstop layered with short-window relative degradation), F2 (arch B rolling absolute worst-node floor over a finite window, subsuming A as the H=0 limit), F3 (arch C aggregate-deficit non-increase over a finite window). No forbidden key token (winner/rank/tier/score/best/superior/optimal/preferred/recommend) appears in any KEY. **Accuracy correction vs WU-17 (TRUST DISK, CLAUDE.md §1/§7/§21):** the delayed-collapse onset is **PERSISTED, not untested** — WU-16 pins the θ_p=5 crossover at report index 13 (6.5h) via `first_report_index_below_theta_p`; `horizon_analysis.crossover_onset_correction` supersedes `wu17.horizon_analysis.crossover_interval_untested`, F2 carries `smallest_sufficient_H_for_theta_p_5_report_index=13`, and the smallest sufficient absolute-floor horizon for θ_p=5 on the severe corner is therefore a KNOWN ≥13 control steps. A useful absolute 20-psi floor stays `THRESHOLD NOT YET EMPIRICALLY JUSTIFIED`; only the N_neg==0 negative gate is `EVIDENCE-SUPPORTED`. Frozen invariants (action space, observation_dim=139, reward D-P6-005) and all byte-reproduced prior artefacts unchanged. Committed 2291cce (deliverable) + checkpoint. Full battery **199 OK** (171 prior + 28 new WU-18).
- **Decision class:** FINAL DECISION REVIEW (readiness judgement + design packaging; nothing selected/ranked/scored/recommended; researcher_selection=null). STEP-9 stays PROPOSED / PENDING RESEARCHER; project NOT PPO-ready; no D-P6-006 minted.
- **Files changed:** src/validation/p6_s9_final_decision_review.py (new); results/phase6/p6_s9_final_decision_review.json (new); tests/test_step9_final_decision_review.py (new); docs/PHASE6_STEP9_FINAL_DECISION_REVIEW.md (new); PROJECT_STATE.yaml; docs/PHASE6_EVIDENCE_INDEX.md; docs/RECOVERY.md; docs/PHASE6_EXECUTION_LOG.md.
- **Risks/caveats:** the review inherits every WU-14/15/16 coverage limit — no validated safe/unsafe oracle (activation counts are descriptive, NOT FP/FN rates); single lower-corner empirical coverage (R1b); coarse H2 α grid; uncalibrated leakage emitter. Residual GENUINE gap: only the temporal rule-activation booleans were tabulated at coarse H∈{1,2,4,8,192}; intermediate thresholds 5<θ_p<10 and non-severe corners are not swept — both computable from the persisted series WITHOUT new EPANET, and neither is a STEP-9 blocker. Readiness = decision-readiness, NOT a guarantee of long-term safety; the finite look-ahead is bounded by the 96h EPS. Aggregation faithfulness guaranteed by the rebuild-equals-persisted-bytes test, not by manual inspection.
- **Next action:** researcher composes the final D-P6-006 design from F1/F2/F3 (selecting architecture + metric/rule + threshold + look-ahead horizon + action-handling policy + effort-term proposed-vs-executed convention), records it as a NEW D-P6-006 in docs/PHASE6_DECISION_REGISTER.md, updates PROJECT_STATE.yaml, and only then proceeds to the STEP-9 wrapper implementation and PPO readiness. No wrapper, no reward.py, no PPO until then.


## WU-19 — STEP 9 D-P6-006 FINALIZATION (STAGE A close-out + STAGE B decision mint) — 2026-10-01

- **Situation:** WU-18 left STEP-9 DECISION-READY with three open questions (A1 relative-rule base semantics; A2 reward movement-term proposed-vs-executed; A3 PPO-readiness wording) and a BLANK D-P6-006 form. The researcher's STAGE-B directive instructed finalization of D-P6-006. This WU closes the three questions and mints the decision.
- **Starting state:** HEAD bfab19e (WU-18 checkpoint); src/env/ has only state_builder.py; register ends at D-P6-005; full battery 199 OK. All frozen invariants (D-P6-001/002/003 action, D-P6-004 observation, D-P6-005 reward) APPROVED & FROZEN.
- **Action taken (DOC/DECISION ONLY — no code, no EPANET, no PPO):**
  - **A1** (DECISION_REGISTER D-P6-006 §A1): relative-rule `base` = **HOLD counterfactual** — forward-simulate the previous command `a_prev` from the IDENTICAL current real state over `[0..H]` and compare the proposed trajectory against it. Three interpretations evaluated; (1) current-pre-advance = H=0 limit, (2) fixed reference_nominal = t=0 zero-drift special case (the WU-16 usage), (3) HOLD = the general causal (treatment-vs-control) definition, SELECTED. Identity hold ⇒ Δ≡0 ⇒ baseline-safe by construction. Residual limitation documented (cannot catch slow deterioration under a held low command; no finite H guarantees against the 96h endpoint).
  - **A2** (REWARD_SPEC §8.12): movement term uses the **EXECUTED (post-safety = commanded)** action — exactly D-P6-005's "commanded" (which excluded only *realised pump speed*, G12). Disambiguation + documentation; D-P6-005 formula/weights/constants UNCHANGED. H1-reject da=0 flagged as a benign monitor item (not reward-hackable).
  - **A3** (DECISION_REGISTER D-P6-006 §A3): recorded the 5-step gate (1 finalize → 2 implement env → 3 validate behaviour → 4 integration tests with real EPANET/WNTR → 5 ONLY THEN PPO-ready); corrected the §18 "minting makes it PPO-ready" wording in FINAL_DECISION_REVIEW §19.
  - **STAGE B** (D-P6-006 minted in DECISION_REGISTER; filled §19 form in FINAL_DECISION_REVIEW; WU-19 finalization §12 in SAFETY_DESIGN): architecture **F1** (= WU-18 arch D) = hard `N_neg==0` backstop (S4/TS4) + relative worst-node guard (S2/TS2, base=HOLD) over `[0..H]`; NO absolute floor; S3 not a primary gate. Defaults (reconfigurable, STEP-12 sweep): ε_p=0.0 psi {0,2,5}; H=1 control step {1,2,4,8}; NO finite H claimed universally sufficient. Handling H1 reject-to-hold + H3 reference fallback (H2 clip documented). Check timing BEFORE execution via forward probe. Non-universal claim scope recorded.
- **Result:** D-P6-006 **FINALIZED 2026-10-01**. The WU-18 byte-reproducible JSON and its §18 BLANK form are PRESERVED UNCHANGED (the pre-decision snapshot); `tests/test_step9_final_decision_review.py` still **28 OK** (verified — the finalization lives in human-readable docs + the register, not the aggregator). No frozen invariant changed; **no STAGE-I stop condition triggered** (the safety layer is an execution-time admissibility wrapper; it does not alter reward math — A2/F fixes the executed-vs-proposed convention only). Deliverable commit **0dc1e8c**; this entry is the checkpoint.
- **Decision class:** DECISION MINT (Level 3). D-P6-006 composed by the AI research partner from the evidence-forced architecture under the researcher's explicit STAGE-B finalization directive; every value knob (ε_p, H, handling, claim scope) flagged reconfigurable with a mandated STEP-12 sweep (CLAUDE.md §16/§21).
- **Files changed:** docs/PHASE6_DECISION_REGISTER.md (D-P6-006 minted); docs/PHASE6_REWARD_SPEC.md (§8.12, A2); docs/PHASE6_STEP9_SAFETY_DESIGN.md (§12 WU-19); docs/PHASE6_STEP9_FINAL_DECISION_REVIEW.md (banner + §19 filled form, §18 blank preserved); PROJECT_STATE.yaml; docs/PHASE6_EVIDENCE_INDEX.md; docs/RECOVERY.md; docs/PHASE6_EXECUTION_LOG.md.
- **Risks/caveats:** D-P6-006's guarantees are non-universal (negative-pressure backstop + worst-node-vs-hold over `[0..H]` only); no 20-psi floor; no protection beyond H; joint 5-D-box + stochastic-demand safety UNTESTED (R1b, STEP-10/12); no validated safe/unsafe oracle (detection ≠ guarantee). ε_p=0 training-restrictiveness is a HYPOTHESIS_TO_TEST with {2,5} pre-registered relaxations.
- **Next action:** STAGE C — implement `src/env/` (epanet_adapter, action_mapper, safety, reward, metrics, demand_scenarios, bwsn_env) reusing state_builder.py + phase5_common + the R8 run_config instrument + the WU-16 forward-probe; gymnasium optional-import. torch/stable_baselines3 remain MISSING → STAGE E (PPO) is a hard STAGE-I stop pending researcher-approved install. STAGE D = 20 correctness tests with real EPANET/WNTR solves (reproducing the frozen anchors). No PPO training.


## WU-20 — STEP 11/12 production RL environment implementation + correctness/integration test battery (STAGE C+D+F) — 2026-10-01

- **Situation:** D-P6-006 FINALIZED (WU-19) unblocked STEP-11 environment implementation. The frozen design layers (D-P6-001/002/003 action, D-P6-004 observation, D-P6-005 reward, D-P6-006 safety) were all APPROVED/FINALIZED but existed only as specs + the state-only `state_builder.py`. This WU IMPLEMENTS the production environment and its test battery, under the standing directives "do the work, do not merely describe what should be done" and "do not say 'PPO-ready' unless the environment integration tests genuinely support that statement."
- **Starting state:** HEAD `1a5fa2d` (WU-19 checkpoint); `src/env/` held only `__init__.py` + `state_builder.py`; `tests/` held the STEP-7/8/9 validation suites. torch/stable_baselines3/gymnasium MISSING (R4). All frozen invariants unchanged.
- **Action taken (STAGE C — implementation; reuses frozen specs, adds NO new hydraulics / scientific meaning):** 7 new `src/env/` modules —
  - `action_mapper.py` — the D-P6-001/002/003 ABSOLUTE affine map (7-dim, order VALVE-173/175/176/177/178, PUMP-170/172); clip→forward and inverse→clip; `to_command` splits to PRV-psi / pump-speed dicts; `command_to_normalized`; `as_float32`. Bounds imported from `state_builder` (single source of truth).
  - `metrics.py` — the frozen `g6_g7_g8` accounting law: signed emitter `q=sign(p)·C·|p|^0.5` over the full coefficient-junction set; served = Σreported − leak; unserved⁺ = max(0, req − served); deficit over the 121 SERVICE nodes only; power = Σ pump kW; dsr.
  - `reward.py` — D-P6-005 F1 `C-A_F1_balanced_dense`: weights (1,1,1,0.1,0) + the 5 frozen normalisers; movement `||da||²` on the EXECUTED normalised action (A2); returns a decomposed `RewardBreakdown`.
  - `safety.py` — the D-P6-006 F1 execution-time admissibility wrapper: `ts4_safe` (N_neg==0 backstop), `ts2_safe` (relative worst-node vs HOLD with ε_p slack), `resolve_action` escalation ladder accepted → reject_to_hold (H1) → reference_fallback (H3); NO gym/torch dependency.
  - `epanet_adapter.py` — `SteppingHydraulicDriver` (reset/step/probe) over WNTR 1.5.0 / EPANET 2.2 with the mandated solver policy; `probe()` is non-committing (snapshots + restores state in `finally`) for the D-P6-006 forward look-ahead; emits intra-step worst-node / N_neg window traces.
  - `bwsn_env.py` — the episode wrapper; gym-optional (`_HAS_GYM` graceful fallback, confirmed usable headless); `reset`/`step`; 192 control steps; `terminated` always False, `truncated` at step 192; `step()` composes action_mapper → (safety | direct) → driver → metrics → reward and returns the frozen 139-dim observation + a full `info` diagnostics dict.
  `demand_scenarios.py` was DELIBERATELY NOT written (stochastic demand is the still-open STEP-10 Level-2/3 decision — scope discipline, §19).
- **Action taken (STAGE F — baseline interfaces):** added `src/env/baselines.py` — a PURE action-masking helper (no hydraulics) for the four comparison conditions native / prv_only / vsp_only / joint; `free_mask` + `apply_mask` pin non-free actuators to the native normalised action. DELIBERATELY NOT wired into `step()` (the env action semantics stay frozen; an experiment harness composes it); the evaluation PROTOCOL that consumes it is flagged an OPEN Level-2 decision, not encoded.
- **Action taken (STAGE D+F — tests, stdlib `unittest`):** 5 new test modules — `test_action_mapper.py` (7, independent frozen-contract oracle with bounds RE-stated not imported), `test_metrics_reward.py` (12, closed-form accounting + reward algebra), `test_safety.py` (7, FakeDriver escalation ladder + predicates, no EPANET), `test_baselines.py` (7, masking), `test_env_integration.py` (5, REAL EPANET — two full 192-step native episodes cached in `setUpClass`).
- **Result:** full new battery **38 tests OK in 40.2 s** (33 fast + 5 real-EPANET), exit 0, verified on disk this WU. The real-EPANET integration confirms end-to-end: native static hold reproduces the frozen leak anchor (leak_mean ≈ 84.7294 GPM, rel < 5e-5); horizon semantics (192 steps, `terminated` never True, `truncated` at step 192); every observation shape (139,) float32 within the frozen bounds; the D-P6-005 movement invariant (da == 0 EXACTLY for steps 2..192); the D-P6-006 safety layer is a NO-OP on the admissible native path (all 192 outcomes "accepted"; leak_mean byte-identical safety ON vs OFF, |Δ| < 1e-9).
- **Investigated finding (NOT a contradiction; env NOT modified):** step-1 movement penalty is a tiny float32 reset-boundary residual (`mv_step1` ≈ 4.2e-18, below float32 eps), because `reset()` seeds `prev_exec_norm` as exact float64 native_norm while the executed action passes a float32 cast; steps 2..192 are EXACTLY 0 (deterministic). Root-caused with a pure no-EPANET diagnostic per CLAUDE.md §12; the TEST assertion was relaxed to the true invariant (`mv[2..192]==0` exactly AND `mv[1] < 1e-12`), NOT the env. No scientific meaning changed; no STAGE-I stop triggered.
- **Decision class:** IMPLEMENTATION of already-frozen decisions (STEP 11/12). No new research decision; no frozen invariant altered; D-P6-004/005/006 + the action space implemented faithfully and validated.
- **PPO-readiness (honest):** the ENVIRONMENT satisfies D-P6-006 §A3 gate steps 1–4 (finalize ✓, implement ✓, validate anchors ✓, real-EPANET integration tests ✓). It is NOT yet PPO-ready: step 5 additionally requires the PPO stack (torch / stable_baselines3 / gymnasium — all MISSING, R4) + an SB3 smoke test, which need researcher-approved install (do NOT auto-install, §20). The integration tests validate the ENV, not that PPO can run.
- **Files changed:** src/env/{action_mapper,metrics,reward,safety,epanet_adapter,bwsn_env,baselines}.py (all new); tests/{test_action_mapper,test_metrics_reward,test_safety,test_baselines,test_env_integration}.py (all new); docs/PHASE6_EXECUTION_LOG.md, docs/PHASE6_EVIDENCE_INDEX.md, docs/PHASE6_DECISION_REGISTER.md, docs/RECOVERY.md, PROJECT_STATE.yaml.
- **Risks/caveats:** real-EPANET validation covers the NATIVE trajectory only — the safety layer's reject/fallback branches are proven by FakeDriver unit tests, not yet exercised on a real adversarial EPANET episode (needs a policy or a crafted unsafe command; STEP-12 extension). Joint 5-D-box + stochastic-demand safety still UNTESTED (R1b, STEP-10/12). Leak instrument uncalibrated (R3). No `demand_scenarios.py`, no eval protocol (open decisions). torch/SB3 absent (R4).
- **Next action:** researcher decision gate on STAGE E — approve installing torch/stable_baselines3/gymnasium (R4) to run the STEP-13 SB3 smoke test; and STEP-10 stochastic-demand + evaluation-protocol design (Level-2). Until then the env is implementation-complete + behaviourally validated but the project is NOT PPO-ready. No PPO training performed.


