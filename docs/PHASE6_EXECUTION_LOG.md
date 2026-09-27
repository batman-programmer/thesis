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

