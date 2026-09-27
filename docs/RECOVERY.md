# RECOVERY.md — Fresh-Session Entry Point

**If you are a new AI session (or a human) resuming this project, read this file
first, then `PROJECT_STATE.yaml`, then the three Phase 6 docs listed below. You
should be able to reconstruct the whole project state from disk WITHOUT the old
chat.**

Last updated: 2026-09-27 (UTC) by Claude Opus 4.8.

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
7. Phase 5 evidence: `results/phase5/*.json`; Phase 6 evidence: `results/phase6/*.json`.

The `docs/ai-knowledge/` directory is a separate **portable backup** (committed
in 8dc8151). Do not confuse `docs/ai-knowledge/PROJECT_STATE.yaml` (backup
snapshot) with the live root `PROJECT_STATE.yaml` (this workflow's state file).

---

## 2. Verified current state (from on-disk evidence, 2026-09-26 audit)

- Git: branch `main`, working tree clean, HEAD `8dc8151`.
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

- **STEP 5** action encoding *absolute vs delta*: decision brief prepared,
  recommendation = **absolute**, PENDING researcher confirmation (D-P6-001).
- **STEP 6** numeric action bounds:
  - Pump upper bound proposed = **1.0** (rated), PENDING confirmation (D-P6-002).
  - **Per-valve PRV setpoint bounds MEASURED (D-P6-003) — PROPOSED, PENDING
    APPROVAL.** Evidence in `results/phase6/p6_s6_active_prv_bounds.json`. Proposed
    DRL domains (psi): 173 [5.0,70.0]; 175 [21.5,55.0]; 176 [20.0,29.762];
    177 [20.0,45.0]; 178 [20.0,37.0] (= [service-clean lower, nominal] per valve).
    Only VALVE-176 has a hard negative cliff (neg <=12.75, first non-neg 13.0); the
    other four are limited by the softer <20 psi service criterion; VALVE-173 is
    nearly inert. Joint lower corner is service-clean (0 new <20psi, 0 negative,
    min 4.190 psi, leak 81.383 gpm = −3.347 vs baseline). **NOT frozen** (§18).
- STEP 7 observation design, STEP 8 reward, STEP 9 safety layer, STEP 10 demand
  uncertainty/splits: NOT STARTED. STEP-9 must hard-clamp to the approved bounds.
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
- **DO NOT** start scientific PPO training. A tiny smoke test is allowed ONLY after
  the env is implemented and validated, and only to prove the loop runs.
- **DO NOT** auto-install gymnasium / stable_baselines3 / torch.
- **DO NOT** make silent research-impacting decisions (encoding, bounds, reward,
  observation, exclusions) — register them first and get approval where required.
- **DO NOT** delete or rewrite `docs/ai-knowledge/` backup material or `session-backup/`.
- **DO NOT** treat VALVE-174/179/180 as controllable — they are excluded on evidence.

