# PHASE6_DECISION_REGISTER.md — Decisions (open + resolved)

Per-decision template (instruction §6): ID · Date · Topic · Question · Evidence ·
Options · Recommendation · Reasoning · Status · Approval · Implementation ·
Validation. Resolved decisions from Deliverable A are recorded first for
traceability; live decisions (D-P6-001..003) follow.

Status vocabulary: OPEN · RECOMMENDED (pending researcher confirmation) ·
APPROVED · IMPLEMENTED · SUPERSEDED.

---

## D-P6-000a — G5 action-space membership  [RESOLVED / IMPLEMENTED]

- **Date:** earlier session (documented in docs/phase6_g5_g12_resolution.md)
- **Topic:** Which PRVs become RL action dimensions.
- **Question:** Which of the 8 PRVs are safe and effective to expose to the agent?
- **Evidence:** results/phase6/p6_s3_prv_finechar.json, p6_s3b_v179_refine.json,
  p6_s3c_zone_interaction.json.
- **Decision:** Control {VALVE-173,175,176,177,178}; exclude {174,179,180}.
- **Reasoning:** 174 reopens with adverse effect (95->96 psi); 179 has a negative-
  pressure cliff just below nominal (clean <=44.7); 180 is commanded shut by
  `[CONTROLS]`. The other five are responsive and safe on the tested set.
- **Status:** IMPLEMENTED (recorded as VALIDATED FACT + ENGINEERING DECISION).
- **Validation:** joint 0.75–1.00× test showed box constraint sufficient on tested set.

## D-P6-000b — G12 pump-control abstraction  [RESOLVED / IMPLEMENTED]

- **Topic:** How the agent controls pumps without corrupting native logic.
- **Decision:** Option C on Option A mechanism — command SPEED only, re-issue each
  1800 s step; native rules keep STATUS.
- **Evidence:** results/phase6/p6_s4_pump_strategy.json.
- **Reasoning:** re-issue holds speed 98.62% vs 1.72%; Option B halts sim at 79.5h.
- **Status:** IMPLEMENTED (VALIDATED FACT + ENGINEERING DECISION).

---

## D-P6-001 — Action encoding: ABSOLUTE setpoint vs DELTA increment  [RECOMMENDED]

- **Date:** 2026-09-26
- **Topic:** How the continuous PRV action is encoded (STEP 5).
- **Question:** Should each PRV action be an **absolute target setpoint** (psi,
  re-set every control step) or a **delta** applied to the current setpoint?
- **Level:** 2 (research-impacting — action representation). Register before locking.
- **Evidence available:** segmented-EPS re-issue mechanism already validated for
  pumps (p6_s4_pump_strategy.json); PRV setpoints are likewise re-writable each
  1800 s step; VALVE-179 cliff evidence shows hard bounds matter for safety.
- **Options & 9-criterion comparison** (A = absolute, B = delta):

  | # | Criterion | A: Absolute | B: Delta |
  |---|-----------|-------------|----------|
  | 1 | Actuator mapping | 1:1 to `valve.setting` each step; stateless per step | needs running integral of setpoint |
  | 2 | Safety clamping | trivial: clip to [lo,hi] psi | must clamp integrated state; wind-up risk |
  | 3 | Control stability | direct, no accumulation | slow drift/oscillation possible |
  | 4 | Exploration | samples the whole feasible box | local moves; may not reach bounds early |
  | 5 | Markov property | action fully determines command | requires current setpoint in observation |
  | 6 | Reproducibility | deterministic given action | depends on trajectory of prior deltas |
  | 7 | Fit to segmented re-issue arch. | native (mirrors pump speed re-issue) | extra per-step state to carry |
  | 8 | Reward attribution | action == commanded state | action != state; harder to attribute |
  | 9 | Impl. + test surface | smaller; easy to unit-test the mapper | larger; must test integration + clamp |

- **Recommendation:** **A (absolute setpoint)**, normalized action in `[-1,1]`
  mapped affinely to each valve's `[lo, hi]` psi bound (bounds from D-P6-003).
- **Reasoning:** the environment already re-issues actuator commands each step;
  absolute encoding mirrors that, keeps the per-step command stateless, makes the
  safety clamp exact, and preserves clean reward attribution. Action smoothness
  (delta's main advantage) can instead be encouraged by an actuation-change
  penalty in the reward (STEP 8) without paying delta's wind-up/Markov costs.
- **Counter-arguments:** delta gives inherently smaller per-step moves (gentler
  actuation) and can be smoother; if the reward's actuation penalty proves
  insufficient this should be revisited.
- **Open item:** confirm framing against the local corpus / literature during
  methodology-review (do not assert specific prior work uncited).
- **Status:** RECOMMENDED — pending researcher confirmation.
- **Implementation:** deferred to STEP 11 `action_mapper.py`. Not yet coded.
- **Validation:** STEP 12 unit test: action ∈ {-1,0,1} maps to {lo, mid, hi} per valve.

---

## D-P6-002 — Pump speed action bounds  [RECOMMENDED]

- **Date:** 2026-09-26
- **Topic:** Numeric speed range exposed to the agent per pump (STEP 6).
- **Question:** What `[min, max]` relative speed should each pump action span?
- **Evidence:** results/phase5/g3_pump_speed.json :: feasible_speed_bounds — 
  PUMP-170 min feasible 0.8152 (shut at 0.80); PUMP-172 min feasible 0.7655
  (shut at 0.70); sweep 0.50–1.10, none beyond curve Qmax up to 1.10.
- **Options:** (A) [min_feasible, 1.0]; (B) [min_feasible, 1.10]; (C) fixed speed.
- **Recommendation:** **A** — PUMP-170 ∈ [0.82, 1.0], PUMP-172 ∈ [0.77, 1.0],
  using a small safety margin above each measured shut-off speed.
- **Reasoning:** 1.0 is rated speed; overspeed (>1.0) raises pressure and thus
  leakage — counter to the objective — so excluding it is both safe and aligned.
  A margin above the measured min avoids episodes that skirt the shut-off cliff.
- **Counter-arguments:** capping at 1.0 removes any transient benefit of brief
  overspeed for tank refill; the measured headroom to 1.10 exists if needed.
- **Status:** RECOMMENDED — pending researcher confirmation (exact margins to fix
  alongside D-P6-003 sweep so pump+PRV bounds are set from one evidence pass).
- **Implementation:** deferred to STEP 11. Not yet coded.
- **Validation:** env must never command a speed outside the bound; smoke test
  confirms pumps do not shut from commanded speed within bounds.

---

## D-P6-003 — Per-valve safe setpoint bounds for the 5 RL PRVs  [OPEN — measurement pending]

- **Date:** 2026-09-26
- **Topic:** `[lo, hi]` psi setpoint bound for each of VALVE-173/175/176/177/178.
- **Question:** How low/high can each admitted PRV's setpoint go before it causes
  service-pressure violations (<20 psi PDA threshold) or negative pressure?
- **Evidence gap:** only a *joint* 0.75–1.00× nominal test exists
  (p6_s3c_zone_interaction.json); VALVE-178 has an individual grid, but
  173/175/176/177 have **no per-valve fine sweep**. Bounds cannot be set yet.
- **Plan (next action):** run a deterministic per-valve fine setpoint sweep
  (leak instrument on, PDA, 96 h EPS, other PRVs at nominal), record per setting:
  min/mean service pressure, n_node_ts<20psi, n_negative, leakage, DSR. Derive
  each valve's safe lower bound (lowest setting with 0 negative and no increase in
  <20 psi violations beyond the nominal 386 baseline) and a justified upper bound.
  Output -> `results/phase6/p6_s6_active_prv_bounds.json`; script
  `src/validation/p6_s6_active_prv_bounds.py`.
- **Status:** OPEN — measurement not yet run. This is characterization (allowed),
  not RL training. Result feeds D-P6-001 mapping and D-P6-002 evidence pass.
- **Validation:** bounds must reproduce; box-constraint sufficiency to be re-checked
  jointly if per-valve bounds widen beyond the already-tested 0.75× envelope.

