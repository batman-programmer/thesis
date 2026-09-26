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

