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

## D-P6-003 — Per-valve safe setpoint bounds for the 5 RL PRVs  [PROPOSED — PENDING RESEARCHER APPROVAL]

- **Date:** 2026-09-26 (opened); 2026-09-27 (measured, PROPOSED).
- **approval_required:** true. **Do NOT mark APPROVED without explicit researcher approval (§14).**
- **Topic:** `[lo, hi]` psi setpoint bound for each of VALVE-173/175/176/177/178.
- **Question:** How low/high can each admitted PRV's setpoint go before it causes
  service-pressure violations (<20 psi PDA threshold) or negative pressure?
- **Method (executed):** deterministic per-valve fine setpoint sweep, leak
  instrument on, PDA (required 20 / minimum 0 / exponent 0.5), 96 h EPS, solver
  1e-5 / 2000 / rule 180 s / report 1800 s asserted each load, other four PRVs held
  at nominal. Adaptive grid extended outward from nominal and refined to 0.25 psi
  around every safety/service transition. Per setpoint recorded: commanded/echoed
  setting + transmission error, valve state (Active/Open/Closed) + realization rate,
  mean/min/max service pressure, n_node_ts<20psi, n_new<20psi vs baseline,
  n_negative, valve flow, leakage, DSR, continuity residual, solver-clean flag.
  Reference nominal reproduced EXACTLY (mean 94.787 psi, min 4.165 @ JUNCTION-29,
  386 <20 psi, 0 negative, leak 84.730 gpm).
- **Three separate concepts reported per valve (§8):** (A) observed domain (grid
  actually evaluated), (B) hard-safe / service-clean supported domains (measured),
  (C) proposed DRL domain (engineering decision, NOT automatically = B).
- **Measured evidence** (`results/phase6/p6_s6_active_prv_bounds.json`):

  | Valve | Nominal | Observed (A) | Hard-safe | Service-clean (B) | **Proposed (C)** | Flow@nom (gpm) | Leak save in domain | Low-side behaviour |
  |---|---|---|---|---|---|---|---|---|
  | 173 | 70.0 | [5,110] | [5,110] | [5,110] | **[5.0, 70.0]** | 4.72 | 0.279 gpm / 0.329% | closes_below_domain (inert <~55 psi) |
  | 175 | 55.0 | [5,110] | [5,110] | [21.5,110] | **[21.5, 55.0]** | 362.91 | 1.883 gpm / 2.222% | regulates_across_domain |
  | 176 | 29.762 | [10,59.524] | [13,59.524] | [20,59.524] | **[20.0, 29.762]** | 256.91 | 0.632 gpm / 0.746% | regulates_across_domain |
  | 177 | 45.0 | [5,90] | [5,90] | [20,90] | **[20.0, 45.0]** | 20.61 | 0.346 gpm / 0.408% | regulates_across_domain |
  | 178 | 37.0 | [5,74] | [5,74] | [20,74] | **[20.0, 37.0]** | 39.24 | 0.208 gpm / 0.245% | regulates_across_domain |

- **Safety criterion (measured, not invented, §6):** unsafe = any negative service
  pressure, OR any *new* <20 psi violation beyond the 386-timestep nominal baseline,
  OR solver failure / non-convergence / discontinuity / impossible actuator state.
  Only **VALVE-176** exhibits a hard negative-pressure cliff (negative ≤12.75 psi,
  first non-negative 13.0 psi; localized at JUNCTION-126). The other four are limited
  only by the softer <20 psi service criterion (service-clean lower: 175=21.5,
  176/177/178=20.0; 173 service-clean to the 5 psi floor because it is nearly inert).
- **Bounds are asymmetric / non-uniform (§7):** proposed domains are one-sided
  [service-clean lower, nominal] and differ per valve; NOT a shared percentage band.
- **Alternatives recorded per valve (not chosen by default):** permissive lower =
  hard-safe floor (admits <20 psi violations, no negative — deferred to reward /
  STEP-9 safety layer); headroom upper = regulation ceiling (lets the agent RAISE
  pressure for service recovery, but admits leakage-increasing actions above nominal).
- **Recommendation (C):** proposed domain = [service-clean lower, nominal] per valve.
  Upper = nominal so the action space can only reduce pressure below the distributed
  baseline and cannot command higher leakage than baseline — aligned with the
  leakage-reduction objective.
- **Cross-actuator check (§10):** all five PRVs at their proposed lower bounds
  simultaneously (173=5, 175=21.5, 176=20, 177=20, 178=20) is SERVICE-CLEAN — 0
  negative, 0 new <20 psi, min service 4.190 psi @ JUNCTION-29, leak 81.383 gpm
  (−3.347 vs baseline). Per-valve box constraints are jointly sufficient at the
  most aggressive tested corner.
- **Uncertainty / caveats:** (1) leak instrument is validation-only, uncalibrated —
  absolute leakage numbers are not field-meaningful; only relative response is used.
  (2) Per-valve leakage savings are modest (0.2–2.2% in isolation); joint lower
  corner saves ~3.95%. (3) VALVE-173 is nearly inert (4.72 gpm at nominal, closes
  below ~55 psi) — weak action dimension in isolation (HYPOTHESIS TO TEST); its
  proposed [5,70] domain carries a large closed-valve dead-zone. (4) The chronic low
  node (JUNCTION-29 ~4.16 psi) is governed by network structure, not by these PRVs.
  (5) Upper bound choice (nominal vs headroom) and VALVE-173 domain narrowing are
  open researcher decisions.
- **Status:** PROPOSED — PENDING RESEARCHER APPROVAL. This is characterization
  (allowed), not RL training or optimization. Bounds feed D-P6-001 (mapping) and
  the D-P6-002 evidence pass; they are NOT final and NOT frozen.
- **Approval:** required (researcher). Not yet given.
- **Implementation:** none. No env code, no action_mapper written. Deferred to STEP 11.
- **Validation:** reference nominal reproduced exactly twice; every setpoint
  solver-clean with continuity residual < 1e-3; box-constraint joint sufficiency
  verified at the lower corner.

