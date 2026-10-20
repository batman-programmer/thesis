# PHASE6_DECISION_REGISTER.md — Decisions (open + resolved)

Per-decision template (instruction §6): ID · Date · Topic · Question · Evidence ·
Options · Recommendation · Reasoning · Status · Approval · Implementation ·
Validation. Resolved decisions from Deliverable A are recorded first for
traceability; live decisions (D-P6-001..003) follow.

Status vocabulary: OPEN · RECOMMENDED (pending researcher confirmation) ·
PROPOSED (measured/designed, awaiting researcher selection) ·
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

## D-P6-001 — Action encoding: ABSOLUTE setpoint vs DELTA increment  [APPROVED 2026-09-27]

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
- **Status:** APPROVED (2026-09-27) — see the APPROVAL section at the end of this
  register. The RECOMMENDED reasoning above is retained as history (PROPOSED →
  REVIEWED → APPROVED).
- **Implementation:** deferred to STEP 11 `action_mapper.py`. Not yet coded.
- **Validation:** STEP 12 unit test: action ∈ {-1,0,1} maps to {lo, mid, hi} per valve.

---

## D-P6-002 — Pump speed action bounds  [APPROVED 2026-09-27]

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
- **Status:** APPROVED (2026-09-27) — approved bounds are **PUMP-170 ∈ [0.82, 1.10]**
  and **PUMP-172 ∈ [0.77, 1.10]** (Option B headroom, per the Q3 review), which
  **SUPERSEDES** this section's original Option-A ([min, 1.0]) recommendation. Lowers
  keep the margin above measured shut-off; 1.10 is the highest tested feasible speed,
  NOT the pump's absolute maximum. See the APPROVAL section at the end. Original
  reasoning retained above as history.
- **Implementation:** deferred to STEP 11. Not yet coded.
- **Validation:** env must never command a speed outside the bound; smoke test
  confirms pumps do not shut from commanded speed within bounds.

---

## D-P6-003 — Per-valve safe setpoint bounds for the 5 RL PRVs  [APPROVED 2026-09-27]

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
- **Status:** APPROVED (2026-09-27). Approved bounds are the item-4 clarification
  table (measured lower, highest-tested-regulating upper): 173 [54.5, 100.0];
  175 [21.5, 110.0]; 176 [20.0, 59.524]; 177 [20.0, 90.0]; 178 [20.0, 74.0]. The
  body's original "[service-clean lower, nominal]" proposal (e.g. 173 [5,70]) is
  retained as history and **superseded** by the approved values. See the APPROVAL
  section at the end.
- **Approval:** GRANTED by researcher, 2026-09-27 (explicit). Provenance PROPOSED →
  REVIEWED → APPROVED preserved in this register.
- **Implementation:** none. No env code, no action_mapper written. Deferred to STEP 11.
- **Validation:** reference nominal reproduced exactly twice; every setpoint
  solver-clean with continuity residual < 1e-3; box-constraint joint sufficiency
  verified at the lower corner.

### D-P6-003 — Decision-review addendum (2026-09-27, no re-run)

Researcher requested a four-question methodological review before approval. No
sweeps were re-run; all values below are read from `p6_s6_active_prv_bounds.json`
and `results/phase5/g3_pump_speed.json`. **Status unchanged: PENDING APPROVAL.**
This addendum records the review; it does NOT freeze or modify the action space.

- **Q1 VALVE-173 authority (measured):** fully CLOSED (flow 0.00 gpm, frac_closed
  1.00, leak flat 84.451 gpm) for every setpoint 5–50 psi; first Active at 60 psi
  (4.54 gpm); Active through 100 (5.20 gpm); saturates Open at 110. Regulating band
  ≈ (50, 100] psi; closing threshold unresolved in (50, 60] (10 psi grid there).
  Within proposed [5, 70]: ~[5, 55] ≈ 77% of the range is a single flat closed
  state; leakage authority only 0.279 gpm (0.329%). **Review recommendation:**
  restrict 173 to its measured regulating range (Option B) to remove the degenerate
  dead-zone, keeping G5's 5-PRV structure, with a STEP-13+ ablation to test dropping
  it (Option C). Exclusion (C) reopens G5 → researcher decision.
- **Q2 PRV upper-bound policy (measured):** above nominal, four valves only add
  leakage with no service benefit (n<20 stays 386), but **VALVE-176 recovers
  service above nominal** — n<20 drops 386→193 (−193) at ≥35 psi, costing +0.28…
  +1.31 gpm leakage (84.730→86.044 at 59.524). Capping every valve at nominal makes
  the action space leakage-only and removes the one measured service-recovery lever
  under uncertain demand. **Review recommendation:** set the *experimental* upper
  bound = per-valve regulation/headroom ceiling (173≈100, 175≥110, 176=59.524,
  177=90, 178=74; all hard-safe, 0 negative), and encode the leakage/service
  trade-off in the STEP-8 reward — NOT in the action clamp. Distinguish: physical
  safety bound (regulation ceiling) ⊃ experimental domain ⊇ preferred operating
  domain (≤ nominal for leakage, a reward/analysis concept). This SUPERSEDES the
  earlier "upper = nominal" leaning in the proposed table, pending approval.
- **Q3 pump upper bound:** 1.0 is rated/design, NOT a measured max; Phase 5 measured
  feasible to 1.10 with 0 speeds beyond curve Qmax (min-feasible speeds 0.8152 /
  0.7655 are tank-level-dependent snapshots, not fixed). **Review recommendation:**
  keep the decision CONSISTENT with Q2 — if PRV upper = headroom, pump upper = 1.10
  (measured feasible) with energy/leakage penalized in reward; if PRV upper =
  nominal, pump upper = 1.0. Researcher decision (D-P6-002).
- **Q4 absolute vs delta:** confirm **absolute** (D-P6-001). Decisive
  environment-specific reason: native `STATUS IS OPEN` resets pump speed to 1.0
  mid-episode (measured, G12), which would desync a delta integrator from the
  realized state; absolute is robust to native resets, mirrors the 1800 s re-issue
  architecture, gives exact safety clipping and clean attribution. Smoothness via a
  reward actuation-change penalty.
- **Status after review:** D-P6-003 = PENDING RESEARCHER APPROVAL. No bound frozen,
  no action space modified.

### D-P6-003 — Clarification / refinement addendum (2026-09-27, item-1/2/3 pass)

Researcher requested a terminology + evidence tightening pass before approval. One
focused refinement WAS run (VALVE-173 only, the single unmeasured coarse-grid
bracket); the full STEP 6 sweep was NOT re-run and `p6_s6_active_prv_bounds.json`
was NOT overwritten. New evidence: `results/phase6/p6_s6b_v173_lowside_refine.json`.
**Status unchanged: PENDING APPROVAL. Nothing frozen.**

- **Item 1 — three precise concepts per PRV (terminology corrected).** The earlier
  wording called each valve's highest tested value a "regulation ceiling". That is
  only defensible for VALVE-173. Corrected definitions and measured values:
  - **A = highest tested feasible (no-negative) setpoint** — the top of the swept
    range with zero negative service pressure.
  - **B = highest tested REGULATING setpoint** — highest setpoint at which the valve
    is still Active (frac_time_active ≥ 0.5) in the swept data.
  - **C = observed Active→Open (saturation) onset** — reported ONLY where an
    Active→Open transition was actually observed.

  | Valve | Nominal | A: highest tested no-negative | B: highest tested regulating | C: observed Active→Open onset |
  |---|---|---|---|---|
  | 173 | 70.0 | 110.0 | **100.0** | **110.0 (observed)** |
  | 175 | 55.0 | 110.0 | 110.0 (grid cap) | UNTESTED — still Active at cap |
  | 176 | 29.762 | 59.524 | 59.524 (grid cap) | UNTESTED — still Active at cap |
  | 177 | 45.0 | 90.0 | 90.0 (grid cap) | UNTESTED — still Active at cap |
  | 178 | 37.0 | 74.0 | 74.0 (grid cap) | UNTESTED — still Active at cap |

  **Only VALVE-173 has a measured Active→Open transition** (Active through 100 psi,
  Open at 110 psi). For 175/176/177/178 the highest tested value is the 2×nominal
  grid cap at which the valve REMAINS Active; their true saturation ceiling is
  **UNTESTED above the cap**. These caps must be described as "highest tested
  regulating setpoint", never as a demonstrated "regulation ceiling".

- **Item 2 — VALVE-173 lower-bound evidence (measured, step6b).** The STEP 6 coarse
  grid jumped 50→60 psi, so the repository did NOT contain evidence to justify a
  ~55 psi lower bound. A small focused refinement (integer grid 50..60 psi, refined
  to 0.25 psi; other four PRVs + pumps at nominal; same solver/PDA/leak instrument)
  resolved the single bracket:
  - **last definitely closed setting = 54.25 psi** (0 gpm, frac_closed = 1.0);
  - **first definitely active setting = 54.5 psi** (frac_active = 1.0, 4.441 gpm);
  - **practical regulating lower edge = 54.5 psi** — a sharp 0.25 psi step, no
    partial-activation band. Reference reproduced exactly (386 <20psi / 0 neg /
    84.730 gpm); the whole (50,60] range is safe (min 4.165 psi, 0 new <20psi, 0 neg)
    and leakage-flat. The repo now supports ~55 psi (measured 54.5).
  - **Recommendation:** re-scope VALVE-173's proposed DRL domain from [5,70] to its
    measured regulating range **[54.5, 100]**, removing the ~70 % closed dead-zone,
    with a STEP-13+ ablation to test dropping this weak actuator. PENDING APPROVAL.

- **Item 3 — cross-actuator claim narrowed.** Previous wording ("per-valve box
  constraints jointly sufficient at the most aggressive tested corner") over-claimed.
  Precise statement: the joint run tested **exactly one** configuration — all five
  PRVs simultaneously at their proposed LOWER bounds (173=5, 175=21.5, 176=20,
  177=20, 178=20) — and that single corner was service-clean (0 negative, 0 new
  <20 psi, min 4.190 psi, leak 81.383 gpm). This validates **that one lower corner
  only**. It does NOT prove that every point of the 5-D action box is safe. Mixed
  corners (some valves high, some low), interior points, and combination with pump
  speed + stochastic demand are **UNTESTED** and are deferred to a **future joint
  safety test (STEP 9 safety layer + STEP 12 automated tests)**. The tested corner
  also used 173=5 (closed); if 173's lower is re-scoped to ≥54.5 psi the corner
  changes and must be re-run before it can be cited.

- **Item 4 — final per-PRV decision table (PROPOSED — PENDING APPROVAL).**

  | PRV | Nominal | Highest tested safe (A) | Highest tested regulating (B) | Proposed DRL lower | Proposed DRL upper | Evidence status |
  |---|---|---|---|---|---|---|
  | 173 | 70.0 | 110.0 | 100.0 | **54.5** (regulating edge; measured step6b) | **100.0** (highest tested regulating; 110 goes Open→ineffective) | lower MEASURED (step6b); upper measured-regulating; **re-scope from [5,70] PENDING** |
  | 175 | 55.0 | 110.0 | 110.0 (cap) | **21.5** (service-clean lower) | **110.0** (highest tested regulating; true ceiling UNTESTED above cap) | lower MEASURED; upper = grid cap, ceiling UNTESTED |
  | 176 | 29.762 | 59.524 | 59.524 (cap) | **20.0** (service-clean; hard neg cliff at ≤12.75) | **59.524** (highest tested regulating; UNTESTED above; recovers service ≥35 at +leakage) | lower MEASURED; upper = grid cap, ceiling UNTESTED |
  | 177 | 45.0 | 90.0 | 90.0 (cap) | **20.0** (service-clean lower) | **90.0** (highest tested regulating; UNTESTED above cap) | lower MEASURED; upper = grid cap, ceiling UNTESTED |
  | 178 | 37.0 | 74.0 | 74.0 (cap) | **20.0** (service-clean lower) | **74.0** (highest tested regulating; UNTESTED above cap) | lower MEASURED; upper = grid cap, ceiling UNTESTED |

  Proposed uppers reflect the researcher-accepted direction (above-nominal headroom
  allowed, with the leakage/service trade-off handled in the STEP-8 reward, not by
  an action clamp). For four valves the proposed upper equals the highest tested
  regulating setpoint (the 2×nominal grid cap) — safe and regulating there, but the
  true Active→Open ceiling above it is UNTESTED; extending the grid to locate it is
  an OPTIONAL future measurement, not required to set a safe upper at/below the cap.

- **Status after clarification (historical, end of the 2026-09-27 clarification
  pass):** D-P6-003 was PENDING RESEARCHER APPROVAL — nothing frozen. This state was
  **superseded on 2026-09-27** by explicit researcher approval; see the APPROVAL
  section immediately below.

---

## APPROVAL — D-P6-001 / D-P6-002 / D-P6-003  [APPROVED 2026-09-27]

- **Date:** 2026-09-27.
- **Granted by:** researcher (explicit approval message; recorded verbatim intent).
- **Provenance preserved:** PROPOSED (2026-09-26/27) → REVIEWED (four-question review
  + item-1/2/3 clarification) → **APPROVED** (this section). Earlier proposed/reviewed
  values above are retained as history and are NOT erased.
- **Decision class:** ENGINEERING DECISION (bounds/encoding selection) built on
  VALIDATED FACT (the measured characterization); researcher-approved (constitution
  priority level 3).

### D-P6-001 — Action encoding = ABSOLUTE  [APPROVED]

The DRL agent directly specifies the PRV pressure setting and pump relative speed
(not a delta). Normalized action per actuator `a_i ∈ [-1, 1]`, affine map:

```text
physical_i = lower_i + ((a_i + 1) / 2) * (upper_i - lower_i)
```

Do not silently change this representation. A future delta-action study is a
**separate research ablation** and must not replace this primary formulation.

### D-P6-002 — Pump speed bounds = APPROVED (exact)

```text
PUMP-170 = [0.82, 1.10]   # relative speed
PUMP-172 = [0.77, 1.10]   # relative speed
```

- 0.82 / 0.77 = practical lower bounds with margin above the measured shut-off
  speeds (0.8152 / 0.7655, `results/phase5/g3_pump_speed.json`).
- 1.10 = highest tested feasible speed in characterization, **NOT** a claim of the
  pump's absolute physical maximum.

### D-P6-003 — PRV setpoint bounds = APPROVED (exact, psi)

```text
VALVE-173 = [54.5, 100.0]
VALVE-175 = [21.5, 110.0]
VALVE-176 = [20.0, 59.524]
VALVE-177 = [20.0, 90.0]
VALVE-178 = [20.0, 74.0]
```

- Controlled PRVs: {173, 175, 176, 177, 178}. Excluded: {174, 179, 180} — these
  **remain in the hydraulic model**; VALVE-179 stays excluded (safety-critical
  negative-pressure transition ~44.8–44.9 psi); any future 179 reconsideration is a
  separate research decision.
- **Terminology (do not overstate):** for 175/176/177/178 the upper bounds are the
  **highest tested regulating setpoints** (grid cap = 2× nominal, valve still
  Active) — NOT the true physical maximum or a demonstrated regulation ceiling
  (UNTESTED above the cap). For 173: 54.5 psi = first measured Active point (step6b);
  100 psi = highest tested Active/regulating; 110 psi transitioned to Open/inactive.

### Pump control strategy — APPROVED

Keep the benchmark's native pump STATUS rules (do NOT remove or rewrite them). The
agent controls pump SPEED only. Each DRL control step: map the normalized action to
physical speed → issue the speed command → allow native STATUS rules to keep
OPEN/CLOSED → **re-issue the speed command every step** so the native reopen rule
cannot silently replace the intended speed. `commanded speed` / `realized speed` /
`pump status` remain explicit; persistent speed is claimed only when the realized
speed confirms it.

### Ordered action vector (stable; do not reorder without a new research decision)

```text
action[0] -> VALVE-173   (psi,  [54.5, 100.0])
action[1] -> VALVE-175   (psi,  [21.5, 110.0])
action[2] -> VALVE-176   (psi,  [20.0, 59.524])
action[3] -> VALVE-177   (psi,  [20.0, 90.0])
action[4] -> VALVE-178   (psi,  [20.0, 74.0])
action[5] -> PUMP-170    (rel speed, [0.82, 1.10])
action[6] -> PUMP-172    (rel speed, [0.77, 1.10])
```

### Joint-safety limitation (carried, NOT closed by this approval)

Approving per-actuator bounds does **not** prove that every point of the 5-D PRV box
(× 2 pump dims × uncertain demand) is safe. Only a single lower-corner joint test
exists. **No claim of exhaustive joint action-space safety.** STEP 9 (safety layer)
and STEP 12 (automated tests) must address mixed corners, the box interior, and
pump + stochastic-demand combinations (risk R1b).

- **Spec:** frozen values written to `docs/PHASE6_ACTION_SPACE_SPEC.md`.
- **Persistence:** `PROJECT_STATE.yaml` (`action_space.approved`), this register,
  `PHASE6_EXECUTION_LOG.md` (WU-7), `PHASE6_EVIDENCE_INDEX.md`, `RECOVERY.md`.
- **Git checkpoint:** commit subject `phase6: approve drl actuator action space`
  (hash recorded in PROJECT_STATE.yaml / RECOVERY.md / PHASE6_EXECUTION_LOG.md).

---

## D-P6-004 — DRL observation / state design (STEP 7)

- **Date:** 2026-09-27
- **Topic:** What the PPO agent observes at each control step (state design only —
  NOT reward, safety, demand model, or the env).
- **Decision class:** ENGINEERING DECISION + RESEARCH ASSUMPTION (Level-2,
  research-impacting, CLAUDE.md §3).
- **Status:** **APPROVED & FROZEN — researcher sign-off 2026-09-27.** The 139-dim
  observation layout is now frozen exactly as the action vector was (D-P6-001/002/003).
  Superseded prior status was *PROPOSED — PENDING RESEARCHER APPROVAL* (2026-09-27);
  provenance preserved below, values not erased. Do not silently alter the layout,
  normalization, ordering, or the demand/Markov framing while designing the reward
  (STEP 8) or thereafter without new contradictory evidence.

### Question

Which quantities, in which fixed order and normalization, form the observation
vector `o_t` — such that it (a) supports the leakage objective and the ≥20 psi
service constraint, (b) never contains future information, (c) keeps the
"uncertain demand" framing intact, and (d) is a stable, reproducible fixed-shape
transform?

### Proposed design

- `observation_dim = 139`, `float32`, fixed shape every step.
- Block layout (frozen order once approved): pressures `[0:121]`; tank levels
  `[121:123]`; prev-commanded PRV setpoints `[123:128]`; PRV `is_active` flags
  `[128:133]`; prev-commanded pump speeds `[133:135]`; pump realized speeds
  `[135:137]`; time-of-day sin/cos `[137:139]`.
- Actuator sub-orders match the approved action vector (173/175/176/177/178;
  170/172) so action index and observation echo align.
- Fixed physical normalization only (no data-derived running statistics); pressure
  band `[-20, 300]` psi → `(p+20)/320` clipped.
- Timing: `o_t` = state after the sim advanced to `t` under `a_{t-1}`, before `a_t`;
  "previous commanded" fields hold `a_{t-1}`; reset uses native initial settings.

### Evidence

- `results/phase6/p6_s7_state_spec.json` — dim 139, block layout, 121 sorted service
  nodes, 5 connectors excluded, tank bounds, approved actuator bounds,
  `consistency_with_frozen_spec` all true, one genuine observation @ t=43200 s with
  all `sample_checks` true.
- `tests/test_state_builder.py` — 9/9 passing (stdlib unittest, numpy only).
- `docs/PHASE6_STATE_SPEC.md` — full §7.1–§7.14 justification, per-variable rationale,
  Markov analysis, future-leakage audit.
- Reused facts: 121 service nodes / 5 connectors (Phase-5 gate 10 rule); pump STATUS
  reset → realized≠commanded (`p6_s4_pump_strategy.json`, G12); reference safety
  numbers (`p6_s3_prv_finechar.json`).

<!-- D-P6-004 continues below -->

### Options / review points (each to accept or amend)

1. **Pressure observability** — full 121-node vector (adopted baseline) vs a
   realistic reduced sensor subset (documented future ablation, not adopted; would
   change scope).
2. **Demand exposure (§7.5)** — Option A: no explicit demand (adopted); B:
   instantaneous total inflow; C: zonal; D: local nodal (rejected — leaks hidden
   state); E: history/forecast (forecast FORBIDDEN). Time-of-day supplies the
   diurnal prior; pressures/tanks are the demand consequences.
3. **Normalization band** — fixed global `[-20, 300]` psi (adopted) vs per-node
   elevation-derived bands (future refinement).
4. **Actuator state representation** — carry BOTH prev-commanded and realized
   (adopted; +9 dims) vs commanded-only (loses the native-override signal).
5. **Temporal structure** — single-step MLP observation (adopted; approximate
   Markovity, tank levels = observed memory) vs frame-stack / recurrent policy
   (future remedy if instability appears).

### Recommendation

Adopt the proposed 139-dim design as the defensible baseline: full-field pressure +
tank levels + dual (commanded/realized) actuator state + cyclical time, Option-A
demand, fixed physical normalization. It is the standard simulation-based WDN-DRL
observation, keeps the uncertain-demand framing, contains no future information, and
is a bounded fixed-shape transform. Richer/leaner variants are explicit future
ablations, not silent changes.

### Reasoning / counter-arguments

- Pressures are the direct signal for both objective (pressure-driven leakage) and
  constraint (≥20 psi); tank levels are the slow memory that keeps the process
  approximately Markov; dual actuator state exposes the native STATUS override the
  agent must learn around. **Risk:** without any demand signal the policy may
  under-react to fast demand transients — first documented remedy is adding metered
  total inflow (Option B, one scalar), recorded as a future ablation.

### Status / Approval / Implementation / Validation

- **Status:** APPROVED & FROZEN (researcher sign-off 2026-09-27). Prior status
  PROPOSED — PENDING RESEARCHER APPROVAL (2026-09-27); history preserved, not erased.
- **Approval — the 5 review points are accepted as the frozen baseline:**
  1. **Pressure observability:** full 121-node service-pressure vector accepted for the
     baseline (reduced sensor subset remains a documented future ablation, not adopted).
  2. **Demand exposure:** Option A — demand is NOT observed; time-of-day sin/cos is the
     only diurnal prior; pressures/tanks are the demand consequences; future/forecast
     demand remains FORBIDDEN.
  3. **Normalization band:** fixed physical band `[-20, 300]` psi → `(p+20)/320` clipped,
     no data-derived running statistics (per-node elevation bands remain a future refinement).
  4. **Actuator state representation:** retain BOTH previous-commanded and realized
     actuator state (+9 dims) so the native STATUS/regulation override is observable.
  5. **Temporal structure:** single-step MLP observation accepted as approximate-Markov /
     POMDP (tank levels are the observed memory); frame-stack / recurrent policy remains a
     future remedy only if training instability appears.
- **Implementation:** `src/env/state_builder.py` (pure numpy), `ObservationConfig` +
  `RawState` + `build_observation` + `observation_bounds`; `docs/PHASE6_STATE_SPEC.md`.
- **Validation:** `tests/test_state_builder.py` 9/9; `results/phase6/p6_s7_state_spec.json`
  consistency + sample checks all true.
- **Frozen — downstream contract:** the 139-dim layout, ordering, normalization and the
  demand/Markov framing are now FROZEN. STEP 8 (reward) reads the environment state but
  MUST NOT alter the observation specification. Reopen only on new contradictory evidence,
  registered as a superseding decision.

---

## D-P6-005 — Reward formulation (STEP 8)  [PROPOSED 2026-09-27 — measurement complete, formulation not selected]

- **Date:** 2026-09-27
- **Topic:** How the per-step scalar reward is composed from the candidate
  components (STEP 8). **This decision is PROPOSED only** — STEP 8 MEASURES the
  natural scale/variability/correlation of every candidate component and PROPOSES
  formulations; it does NOT select one, choose weights, or train PPO.
- **Question:** Which reward formulation and normalisation should PPO optimise so
  that leakage is reduced **without** sacrificing service or safety, with all
  terms on a comparable scale and no train/eval leakage?
- **Level:** 2 (research-impacting — objective definition). Register before locking.
- **Evidence:** `results/phase6/p6_s8_reward_scale_analysis.json` (generator
  `src/validation/p6_s8_reward_scale_analysis.py`; tests
  `tests/test_reward_scale_analysis.py`, 12/12 STEP 8 + 9/9 STEP 7). 19 static
  in-bounds configurations × 193 report timesteps (3667 pooled instants), same
  96 h EPS + solver policy + leak/PDA instrument as `p6_s3`/`g6_g7_g8`.
  Per-timestep extraction reproduces the validated water balance to **0.0 GPM**;
  `reference_nominal` reproduces the frozen baseline exactly (leak 84.730 GPM,
  DSR 0.98334, 386 node-timesteps <20 psi, 0 negative).
- **Measured natural scales (pooled):** leakage 84.95 GPM mean (79.92–90.15, ±~6%
  band); requested demand ~906 GPM; DSR 0.9734 (0.914–1.002); pressure deficit
  19.86 psi·nodes (14.08–31.73); min service pressure 4.77 psi (1.09–5.93);
  negative-node count **identically 0** in-bounds; hydraulic pump power mean ~80
  kW, median 0 (bimodal, native-STATUS-driven).
- **Measured pathologies (evidence, not assertion):**
  1. **Objectives oppose:** leakage↔DSR r=+0.750, leakage↔deficit r=−0.774,
     leakage↔n_below20 r=−0.742 — pushing leakage down erodes service.
  2. **Leakage-only collapses service:** `prv_all_lower` cuts leak −4.0% but drops
     DSR 0.98334→0.91940 (−6.4 pts) → service must be protected explicitly.
  3. **Pressure-only raises leakage:** `prv_all_upper` +5.9% leakage.
  4. **Scale imbalance:** penalty-term median max/min ratio 7.15 → **fixed
     normalisation mandatory** before weighting.
  5. **Sparse hard signal:** negative-pressure term is 0 at 100% of in-bounds
     instants → dense safety must come from deficit / min-pressure.
  6. **Actuator-penalty domination + closed-pump ambiguity:** unnormalised L2²
     movement up to 28 would dominate; effort MUST use the COMMANDED normalised
     action (realised pump speed is reset to 1.0/0 by native STATUS rules).
  7. **Boundary-seeking:** the leakage optimum sits at the PRV lower bound; only
     this single corner is characterised → a STEP-9 hard safety clamp is REQUIRED.
- **Options (all PROPOSED, none selected):**
  - **F1 Normalised weighted sum** — dense, differentiable; every term ÷ its fixed
    reference: `−w_L(leak/leak_ref) − w_U(unserved/req_ref) − w_P(deficit/deficit_ref) − w_A(‖da‖²/L2sq_max) [− w_E(power/power_ref)]`.
  - **F2 Constrained penalty (service protected by construction):**
    `−(leak/leak_ref) − Λ(deficit/deficit_ref) − BIG·max(0,n_below20)`, Λ≫1, BIG≫Λ.
  - **F3 Baseline-relative improvement:** fractional leakage reduction vs the
    native controller, zero-centred at baseline, with a service floor + safety term.
  - **F4 Safety-first lexicographic:** safety > service > leakage > effort, via
    masking / large penalties; pairs with the STEP-9 clamp.
- **Fixed normalisation constants (measured once, frozen — no running stats):**
  `leak_ref=84.72988 GPM`, `req_ref=906.39873 GPM`,
  `deficit_ref=28.67179 psi·nodes` (=max(baseline mean, pooled p95)),
  `power_ref=88.10062 kW`, `movement_L2sq_max=28.0`.
- **Recommendation (for researcher review, NOT adopted):** the evidence favours a
  **normalised, service-protecting** objective (F1 or F2) paired with the STEP-9
  hard safety clamp; F3 is attractive for interpretability given the narrow
  absolute leakage band. **No weights are recommended** — they must be chosen by
  the researcher, ideally with a small sensitivity sweep, as a separate decision.
- **Counter-arguments / risks:** static-run effort scale is analytic (realised
  movement is a HYPOTHESIS TO TEST); the leak instrument is uncalibrated (relative
  response only); scales cover a representative in-bounds set, not the full joint
  interior (STEP-9/STEP-12). Weight choice can still induce reward hacking — must
  be validated after selection.
- **Status:** **PROPOSED** — measurement complete; formulation and weights NOT
  selected. Awaiting researcher decision.
- **Approval:** PENDING. Researcher to select ONE formulation + weights (this
  resolves D-P6-005) after reviewing the measured scales and pathology evidence.
- **Implementation:** measurement instrument + evidence + spec on disk
  (`src/validation/p6_s8_reward_scale_analysis.py`,
  `results/phase6/p6_s8_reward_scale_analysis.json`,
  `docs/PHASE6_REWARD_SPEC.md`). The reward function itself
  (`src/env/reward.py`) is STEP 11 and is NOT implemented here.
- **Validation:** `tests/test_reward_scale_analysis.py` 21/21 pass; integrity
  flags all true (finite, no topology/native-rule change, no future information,
  per-timestep vs validated accounting max abs diff 0.0).
- **Additional comparison evidence (2026-09-27, status UNCHANGED — still
  PROPOSED):** the four formulations F1–F4 were evaluated per-timestep over the
  same 19 validated static commands with PROVISIONAL comparison-only parameters
  (F1 `w_·=1,w_E=0`; F2 `Λ=20,BIG=100`; F3 `w_U=w_P_safety=1`; F4 `θ=20 psi,
  c_soft=10,c_hard=100`). Evidence:
  `results/phase6/p6_s8_reward_formulation_comparison.json`; generator
  `src/validation/p6_s8_reward_formulation_comparison.py`; tests
  `tests/test_reward_formulation_comparison.py` (23/23 pass; full battery 44/44);
  spec §8.9–§8.11 of `docs/PHASE6_REWARD_SPEC.md`. **No formulation is selected,
  scored, ranked, or labelled; no weights are tuned; no safety clamp is added
  (STEP 9); no PPO is trained.** Key descriptive findings: (a) under the
  provisional weights all four rewards place their incentive-argmax on the same
  bound command `prv_176_upper` (min service ≈4.17 psi, 1 sub-20 node); (b) a
  leak-only incentive drives to `prv_lower_pump_lower` (min service 1.295 psi),
  a service-only incentive raises leakage — the two oppose; (c) every pooled
  timestep has ≥1 node <20 psi (incl. the native baseline's 2 nodes) and 0
  negative nodes, so hard-20-psi terms (F2 count, F4 θ=20) fire on the baseline
  itself (ill-posed constraint) while θ=0 is trivially satisfied yet permissive;
  (d) the normalized leak term spans only 0.108 across the tested set vs a
  unit-weight max move cost of 1.0 (effort-domination is a weight-choice concern,
  analytic only). This evidence **informs but does not resolve** D-P6-005.

### D-P6-005 — decision-brief note (WU-11, 2026-09-27; status UNCHANGED — still PROPOSED)

A **decision brief** was assembled to convert the WU-9 + WU-10 evidence into a
decision-ready package for the researcher: `docs/PHASE6_D_P6_005_DECISION_BRIEF.md`
(11 sections) and `results/phase6/p6_d_p6_005_decision_brief.json`
(`researcher_selection: null`), generator
`src/validation/p6_d_p6_005_decision_brief.py`, tests
`tests/test_decision_brief.py` (19 tests; full battery **63/63**). **No new EPANET
run, no PPO, no STEP-9 clamp; no formulation selected/scored/ranked/labelled; no
weights tuned.** The brief (i) reconstructs state from disk; (ii) restates the frozen
action space (D-P6-001/002/003) and observation (D-P6-004); (iii) extracts the WU-9/WU-10
quantitative evidence; (iv) states 12 FACTUAL decision dimensions (not scored); (v) gives
the exact math + parameters-to-approve for F1–F4; (vi) analyses the chronic sub-20-psi
baseline and concludes **no formulation can use a hard 20-psi constraint without penalising
the native baseline itself** — dense deficit / worst-node min-pressure / baseline-relative
signals are the defensible reward-level safety channels, and any hard gate must key on
negative pressure (STEP-9 owns the enforced 20-psi guarantee); (vii) offers **four
PROVISIONAL CANDIDATE — NOT APPROVED** parameterizations (C-A F1 balanced `w_A=0.1` from the
measured 0.108 leak-term range; C-B F1 safety-leaning `w_P=2`; C-C F3 baseline-relative;
C-D dense-deficit with a negative-only hard gate) whose constants trace to measured scales
and are NOT tuned to a preferred result; (viii) presents the WU-10 low/central/high
sensitivity sweeps as an incentive-direction indicator, NOT a ranking; (ix) keeps the
reward (D-P6-005) separate from the STEP-9 safety clamp; (x) leaves the researcher decision
block blank. **D-P6-005 remains PROPOSED / DECISION PENDING RESEARCHER.**

### D-P6-005 — RESOLUTION: APPROVED (2026-09-27) — researcher selected C-A_F1_balanced_dense

- **Decision:** **D-P6-005 = APPROVED.** The researcher selected
  **`C-A_F1_balanced_dense`** — **Formulation F1 (normalised weighted sum)** — as the
  reward for the DRL environment of this thesis.
- **Approved reward equation (verbatim; a per-step NEGATIVE cost, higher = better):**

  ```
  r_t = - w_L*(leak_t/leak_ref)
        - w_U*(unserved_t^+/req_ref)
        - w_P*(deficit_t/deficit_ref)
        - w_A*(||da_t||^2/movement_L2sq_max)
        - w_E*(power_t/power_ref)
  ```

- **Approved parameters (weights):** `w_L=1.0, w_U=1.0, w_P=1.0, w_A=0.1, w_E=0.0`.
- **Frozen normalisation constants (unchanged from WU-9; measured once, no running stats):**
  `leak_ref=84.72988433677985 GPM`, `req_ref=906.3987348621764 GPM`,
  `deficit_ref=28.671793365478514 psi·nodes`, `power_ref=88.10062475649187 kW`,
  `movement_L2sq_max=28.0`.
- **Term semantics (verbatim):** `unserved_t^+ = max(0, unserved_t)`;
  `da_t = commanded normalised action_t − previous commanded normalised action`
  (a static hold gives `da_t = 0`); `w_E=0` disables the energy term numerically but the
  term stays explicitly represented for a future energy ablation.
- **Consistency check (no repository contradiction):** the approved equation, weights and
  constants equal `candidate_parameterizations[C-A_F1_balanced_dense]` and
  `normalization_constants_frozen` in `results/phase6/p6_d_p6_005_decision_brief.json`
  **exactly** (weights `w_A=0.1, w_E=0.0`; five constants byte-identical). No value was
  altered; §1's "do not alter unless a contradiction is found" is satisfied — none was found.
- **Rationale (factual, per researcher; NOT a claim of universal superiority):** C-A gives a
  single dense, differentiable reward that simultaneously represents leakage management,
  service/unserved protection, pressure-deficit protection and actuator-movement
  regularisation, with fixed normalisation and interpretable unit-ish weights, built on the
  existing STEP 8 measured evidence. This approval is specific to **this thesis environment
  and experimental design**; it is **not** a finding that C-A is best/optimal/superior for
  water-network DRL in general, and no formulation was scored or ranked to reach it.
- **Unselected candidates (retained, NOT deleted):** `C-B_F1_safety_leaning`
  (`w_P=2.0`), `C-C_F3_baseline_relative`, and `C-D_dense_deficit_no_hard_count` remain on
  disk as unselected provisional candidates. They are preserved as decision history, not
  removed.
- **C-C `unserved_ref` provenance (§5, documented non-blocking research debt):** two
  DISTINCT persisted values are **preserved, not merged** — `15.103309701248634` GPM
  (C-C DSR-implied, `candidate_parameterizations[C-C].constants.unserved_ref_gpm`) vs
  `14.98483697365873` GPM (F3-family accounting, WU-9/WU-10 `unserved_ref`). Because the
  approved formulation is **C-A (F1)**, which does **not** use `unserved_ref`, this
  discrepancy does **not** affect the approved reward and is recorded as a documented,
  non-blocking research-debt item. Neither WU-9/WU-10 evidence nor either persisted value
  was falsified or overwritten.
- **Preserved frozen decisions (unchanged by this approval):** action space
  D-P6-001/002/003 (encoding ABSOLUTE; PRV bounds 173[54.5,100]/175[21.5,110]/176[20,59.524]/
  177[20,90]/178[20,74]; pump bounds P170[0.82,1.10]/P172[0.77,1.10]; order
  [173,175,176,177,178,P170,P172]; `action_dim=7`) and observation D-P6-004
  (`observation_dim=139`). Topology, service-node mask (121/5), native pump STATUS rules,
  leak instrument, hydraulic/rule/report timesteps and solver settings are unchanged.
- **Reproducibility / evidence-preservation note (disclosed, deliberate):** the
  decision-preparation artefacts `results/phase6/p6_d_p6_005_decision_brief.json` (WU-11) and
  `results/phase6/p6_d_p6_005_researcher_summary.json` (WU-12), together with their pure
  generators and byte-reproduction test batteries (`tests/test_decision_brief.py`,
  `tests/test_researcher_summary.py`), are **retained UNCHANGED** as the frozen snapshot of
  the state *before* the decision (`status: PROPOSED`, `researcher_selection: null`). They are
  historical decision-preparation evidence (CLAUDE.md §11/§12) and are intentionally not
  rewritten. The **authoritative machine-readable record** of this APPROVAL is
  `PROJECT_STATE.yaml` (`reward.approved`) plus the new STEP-9 artefact
  `results/phase6/p6_s9_safety_design_analysis.json` (`d_p6_005_decision` block); the
  **authoritative human-readable record** is this register entry and the RESOLUTION banners
  added to `docs/PHASE6_D_P6_005_DECISION_BRIEF.md` (§11) and
  `docs/PHASE6_D_P6_005_RESEARCHER_SUMMARY.md` (§G).
- **Status:** **APPROVED 2026-09-27.** Supersedes the PROPOSED status above; the PROPOSED
  history (and WU-9/WU-10/WU-11/WU-12 notes) is preserved intact.
- **Approval:** researcher (explicit selection, 2026-09-27).
- **Next:** STEP 9 — state-dependent safety mechanism (design analysis only; see
  `docs/PHASE6_STEP9_SAFETY_DESIGN.md`). The reward function `src/env/reward.py` is STEP 11
  and is NOT implemented by this decision. No PPO training.

---

## D-P6-006 — STEP-9 execution-safety / admissibility layer — FINALIZED (2026-10-01)

- **Level:** 3 (research-critical — a thesis-level methodological decision governing how
  the agent's proposed actions are admitted to the simulator).
- **Status:** **FINALIZED 2026-10-01**, on the researcher's explicit "STAGE B — FINALIZE
  D-P6-006" directive. Composed by the AI research partner from the **evidence-forced**
  architecture of WU-14…WU-18; every residual value judgement (ε_p, H, claim scope) is
  flagged below as a reconfigurable parameter with a mandated STEP-12 sweep (CLAUDE.md
  §16/§21: the researcher remains the final scientific authority and may re-set any
  flagged knob).
- **Provenance:** WU-14 design → WU-15 empirical grids
  (`p6_s9_safety_mechanism_characterization`) → WU-16 temporal look-ahead
  (`p6_s9_temporal_safety_characterization`) → WU-17 decision brief → WU-18 final review
  (`p6_s9_final_decision_review`, all with `researcher_selection: null`, D-P6-006 form
  BLANK) → **WU-19 finalization (this entry)**.
- **Consistency:** consistent with ALL accepted evidence WU-13…WU-18; introduces NO new
  measurement and NO global/universal safety claim; does NOT alter any frozen invariant
  (D-P6-001/002/003 action, D-P6-004 observation, D-P6-005 reward).

### Decision form (WU-18 §18 fields A–G, now filled)

- **A — Architecture:** **F1** (= WU-18 architecture **D**): a **hard negative-pressure
  backstop** (rule S4/TS4, `N_neg == 0`) **layered with** a **relative worst-node
  degradation guard** (rule S2/TS2) over a short forward window `[0..H]`. **NO absolute
  pressure floor** (S1/TS1 rejected — ill-posed on the chronic sub-20-psi baseline, §10).
  Aggregate deficit (S3/TS3) is **NOT** a primary gate (it can mask a localised worst-node
  collapse; WU-14 corr(D, p_min) ≈ −0.77).
- **B — Metric / rule (an action is ADMISSIBLE iff BOTH hold over the probed window):**
  - **Backstop (hard, evidence-supported):** for every probed instant k ∈ [0..H],
    `N_neg(proposed_post, k) == 0` (no service node at negative pressure).
  - **Relative guard (A1):** for every k ∈ [0..H],
    `p_min(proposed_post, k) − p_min(hold_post, k) ≥ −ε_p`, where `hold_post` is the
    **HOLD counterfactual** (continue the previous command `a_prev` from the identical
    current real state). See **A1** below for the `base`-semantics derivation.
- **C — Threshold(s):** backstop `N_neg == 0` is **fixed** (EVIDENCE-SUPPORTED; the only
  well-posed hard absolute gate on this network). `ε_p` = relative worst-node tolerance;
  **DEFAULT ε_p = 0.0 psi** (strict "no worst-node degradation vs hold"; the only value
  shown to separate the severe transition at the decision instant in WU-15 §10.5 —
  razor-thin, NOT claimed to generalise — and the conservative safety-first default).
  **Mandated STEP-12 sweep ε_p ∈ {0, 2, 5} psi.** **NO absolute θ_p floor** (no useful
  20-psi floor is baseline-compatible: "THRESHOLD NOT YET EMPIRICALLY JUSTIFIED").

- **D — Look-ahead horizon H:** **DEFAULT H = 1 control step** (1800 s / 0.5 h look-ahead).
  The **primary temporal protection is the per-step re-check** (the gate runs every
  control step, so protection is renewed continuously). **Mandated STEP-12 sweep
  H ∈ {1, 2, 4, 8} control steps.** **Explicit non-sufficiency statement (binding):** no
  finite H < full episode guarantees against demand/tank-driven *delayed* deterioration
  under a HELD command — the severe corner reaches its worst `p_min = 1.2946763038635254`
  psi at the **96 h episode endpoint** (report index 192), and the first θ_p=5 crossover is
  at report index 13 (6.5 h), already beyond H=8. D-P6-006 is **NOT** claimed to prevent
  deterioration beyond H; within [0..H] it prevents negative pressure (backstop) and
  worst-node degradation vs hold (relative guard).
- **E — Unsafe-action handling:** **H1 reject-to-hold** (execute `a_prev` on breach) as the
  primary rule, with **H3 reference-fallback** (execute the `reference_nominal` native PRV
  setpoints / pump speeds) escalation when the HOLD itself breaches the backstop over the
  window. **H2 clip-toward-previous** (`a_exec = a_prev + α(a_prop − a_prev)`, largest safe
  α) is documented as the **PPO-friendlier continuous alternative** for a future ablation.
  Implementation reuses the two probe solves (hold-probe + proposed-probe): the EXECUTED
  branch's probe result **IS** the committed next state, so no re-solve is needed and no
  tank-state discontinuity is introduced (STAGE-I-safe).
- **F — Effort/movement term action under intervention:** **EXECUTED** (= commanded-to-
  actuator = post-safety) action. This is exactly D-P6-005's "commanded" action. Full
  derivation + the H1-reject `da=0` monitor note: `docs/PHASE6_REWARD_SPEC.md` §8.12.
  **D-P6-005 formula / weights / constants are UNCHANGED** — this fixes an integration
  convention only.
- **G — Rationale:** evidence-forced composition. The backstop is the **only well-posed
  hard absolute gate** (every service node ≥ 0 psi is unambiguous and baseline-satisfied:
  the native baseline already has 0 negatives). The relative guard is **baseline-safe by
  construction** (identity hold ⇒ Δ ≡ 0, no false intervention) and the **most temporally
  sensitive** rule in WU-15/16 (TS2 at ε_p=0 reacts from H=1). The absolute floor is
  **ill-posed** (386 baseline node-ts already < 20 psi). The aggregate-deficit rule **masks
  localised collapse**. No value in the design licenses a universal/global safety claim.

### A1 — relative-rule reference ("base") semantics [resolves WU-18 open question A1]

The relative rules S2/TS2 (and F3's `max_{0..H}(D(post) − D(base)) ≤ ε_D`) require a
precisely defined `base`. Three interpretations were evaluated:

1. **base = current observed pre-advance state** (`p_min` as measured now). This is the
   **H=0 instantaneous** descriptive metric used in WU-15 §10.2. **REJECTED** as the
   production per-step gate: over a window it conflates the *action's* effect with the
   demand/tank *evolution* (every action lowers p_min during a drawdown; a refilling tank
   raises it regardless of the action), so it measures "the state got worse," not "this
   action made it worse."
2. **base = fixed native baseline trajectory** (`reference_nominal`, index-aligned). This
   is the WU-16 characterization choice, **valid only at t=0** (shared initial state, zero
   drift). **REJECTED** as the production per-step gate: once the agent's past actions have
   drifted the tanks away from the native trajectory, it conflates harm-from-this-action
   with accumulated-drift-from-past-actions.
3. **base = HOLD counterfactual** — forward-simulate `a_prev` (continue the previous
   executed command) from the **identical current real state** over `[0..H]`, and compare
   the proposed trajectory against it. **SELECTED.** It isolates the **pure causal effect**
   of the proposed action versus continuing the status quo from the same starting state
   (treatment-vs-control at a common initial condition). Identity hold (`a_prop = a_prev`)
   ⇒ `Δp_min ≡ 0` ⇒ no activation at ε_p=0 ⇒ the "baseline-safe by construction" property
   (SAFETY_DESIGN §10 / §11.5) holds **exactly**.

**Reconciliation (no contradiction with accepted evidence).** Interpretation (1) is the
H=0 instantaneous limit of HOLD; interpretation (2) is the t=0 zero-drift special case of
HOLD; both coincide with HOLD at their points of validity. WU-16's
`base_state = reference_nominal` is therefore **reconciled as the zero-drift
characterization special case**, NOT overturned, and the WU-16 `baseline_identity_hold`
self-check (zero activation) is exactly the ε_p=0 identity-hold property above.

**Cost & STAGE-I safety.** HOLD requires the hold-probe (H solves) in addition to the
proposed-probe (H solves) = **2H forward solves per decision**. The EXECUTED branch's probe
becomes the committed next state, so no solve is wasted and no tank-state discontinuity is
introduced.

**Residual limitation (documented, binding).** A relative-to-hold guard **cannot** catch
slow demand/tank-driven deterioration under an *already-held* positive-but-low command
(where Δ vs hold ≈ 0 yet absolute pressure drifts down over many steps). Only the
`N_neg == 0` backstop catches an absolute negative collapse, and **no finite H guarantees**
against the 96 h-endpoint deterioration. This honours the directive's "no horizon is
universally sufficient."

### A3 — PPO-readiness progression (wording correction) [resolves WU-18 open question A3]

The accurate ordered gate (no step may be skipped; "PPO-ready" is **only** step 5):

1. **Finalize the safety design** — D-P6-006 (this entry).
2. **Implement** the environment modules (wrapper + EPANET adapter + action mapper +
   safety layer + reward + metrics).
3. **Validate environment behaviour** — reproduce the frozen anchors (baseline leak
   `84.72988433677985` GPM, 386 node-ts < 20 psi, 0 negative; deterministic re-run).
4. **Integration tests** with REAL EPANET/WNTR solves (not only mocks).
5. **ONLY THEN** may the environment be described as **PPO-ready**.

The project is currently at step 1 → 2. **No prior Phase-6 document claimed
PPO-readiness**; the docs already state "NOT PPO-ready." A3 records the gate explicitly so
the claim cannot be made prematurely.

### Claim scope (non-universal — binding)

D-P6-006 guarantees, **within the tested research setting** and **over the probed window
[0..H] only**: (i) no service node at **negative** pressure, and (ii) no worst-node
degradation greater than ε_p relative to holding the previous command. It does **NOT**
claim: a 20-psi service floor (ill-posed on this network); protection **beyond** horizon H
(delayed demand/tank-driven deterioration under a held command is explicitly out of
guarantee); global/joint 5-D-action-box safety across mixed corners / interior / pump +
stochastic demand (R1b, UNTESTED); any safety claim under **stochastic** demand (STEP 10,
not yet designed); false-positive / false-negative rates (there is no validated safe/unsafe
oracle — detection ≠ guarantee, SAFETY_DESIGN §11.7). Consistent with SAFETY_DESIGN §11.9
and FINAL_DECISION_REVIEW §12/§17.

### Evidence consistency (WU-13…WU-18 anchors, byte-exact)

- Baseline worst-node `p_min = 4.16452169418335` psi (JUNCTION-29, 24.5 h); baseline leak
  `84.72988433677985` GPM; 386 node-ts < 20 psi; **0 negative** → the backstop
  `N_neg == 0` is **baseline-satisfied** and the absolute 20-psi floor is **ill-posed**.
- Severe corner: decision-instant `p_min = 5.527866840362549`; full-horizon
  `p_min = 1.2946763038635254` (96 h endpoint) → **delayed collapse**, motivating the
  per-step re-check + the explicit no-universal-H statement.
- θ_p=5 smallest-sufficient horizon persisted at report index 13 (6.5 h) → beyond default
  H=1 and the swept H∈{1,2,4,8}; recorded, not claimed sufficient.
- Reference→severe reject `action_deviation_L2 = 2.4050`; TS4 never fires (max N_neg = 0);
  TS2 at ε_p=0 activates from H=1 → the relative guard is the active temporal signal.

### Preserved / unchanged

- Frozen invariants D-P6-001/002/003 (action), D-P6-004 (observation), D-P6-005 (reward)
  are **UNCHANGED**. D-P6-006 is an **execution-time admissibility layer** between the
  policy's proposed action and the simulator; it does not touch the reward math (A2/F fixes
  only the executed-vs-proposed convention). **No STAGE-I stop condition is triggered.**
- WU-14…WU-18 artefacts and their byte-reproduction tests are retained UNCHANGED as the
  pre-decision snapshot (`researcher_selection: null`). This register entry is the
  authoritative human-readable record; `PROJECT_STATE.yaml` is the authoritative
  machine-readable record.
- **Approval:** FINALIZED on researcher directive (2026-10-01); all flagged knobs (ε_p, H,
  handling, claim scope) remain researcher-adjustable and are pre-registered for the
  STEP-12 sweep.
- **Next:** STAGE C — implement `src/env/` (epanet_adapter, action_mapper, safety, reward,
  metrics, demand_scenarios, bwsn_env) reusing `state_builder.py`, `phase5_common`, the R8
  `run_config` instrument, and the WU-16 forward-probe. gymnasium is an optional import
  (R4); torch / stable_baselines3 remain MISSING and gate STAGE E (hard STAGE-I stop until
  researcher-approved install). No PPO training by this decision.

---

## IMPLEMENTATION STATUS — STEP 11/12 env modules (WU-20, 2026-10-01)

This is an IMPLEMENTATION record, **not a new decision**. The frozen design decisions are now
realised in code under `src/env/` and validated by a test battery; **no decision value was
changed**, no frozen invariant altered, no STAGE-I stop triggered.

- **D-P6-001/002/003 (action space)** → IMPLEMENTED in `src/env/action_mapper.py` (ABSOLUTE
  affine map, 7-dim ordered bounds VALVE-173/175/176/177/178 + PUMP-170/172). Validated:
  `tests/test_action_mapper.py` (7) + the real-EPANET round-trip in `test_env_integration`.
- **D-P6-004 (observation, dim 139)** → already IMPLEMENTED in `state_builder.py`; exercised
  end-to-end by `test_env_integration` (shape/dtype/bounds at every one of 192 steps).
- **D-P6-005 (reward, C-A_F1_balanced_dense)** → IMPLEMENTED in `src/env/reward.py` +
  `metrics.py`. Validated: `tests/test_metrics_reward.py` (12, closed-form) + the movement
  invariant in `test_env_integration`. Formula / weights (1,1,1,0.1,0) / 5 normalisers
  byte-identical to the approved spec; energy term disabled (w_E=0) but re-enablable.
- **D-P6-006 (safety / admissibility layer, arch F1)** → IMPLEMENTED in `src/env/safety.py` +
  `epanet_adapter.probe()` (non-committing forward look-ahead). Validated:
  `tests/test_safety.py` (7, FakeDriver escalation ladder + TS2/TS4 predicates) + the
  real-EPANET NO-OP-on-native-path check (`test_env_integration.test_5`: all 192 outcomes
  "accepted", leak byte-identical safety ON vs OFF). The reject-to-hold (H1) /
  reference-fallback (H3) branches are proven by unit tests; a real-EPANET **adversarial**
  exercise (a command that genuinely trips the layer on live hydraulics) is a STEP-12 extension.
- **STAGE F (baseline interfaces)** → IMPLEMENTED in `src/env/baselines.py` (pure masking:
  native / prv_only / vsp_only / joint), NOT wired into `step()`. The evaluation PROTOCOL that
  consumes these masks (metrics reported, demand scenario, train/eval split, seeds, conditions
  run) remains an **OPEN Level-2 experiment-design decision** awaiting researcher approval.
- **Status vs D-P6-006 §A3 gate:** the environment satisfies gate steps 1–4 (finalize →
  implement → validate anchors → real-EPANET integration tests). **Step 5 (PPO-ready) remains
  BLOCKED by R4** (torch / stable_baselines3 / gymnasium MISSING; do NOT auto-install, §20).
  `demand_scenarios.py` stays DEFERRED (open STEP-10 decision). Deliverable commit recorded in
  `PROJECT_STATE.yaml` git block.





---

## D-P6-007 — Demand uncertainty, scenario separation & evaluation protocol (STEP 10)  [SELECTIONS RECEIVED 2026-10-19 via implementation directive; IMPLEMENTED + LOCALLY VERIFIED — status below]

- **Date:** 2026-10-15
- **Topic:** How uncertain demand is generated, how train / validation / test / OOD
  scenarios are separated, how seeds and scenario identities are assigned, and how
  the comparison conditions are evaluated. **PROPOSED only** — this entry records a
  decision-ready package; it selects nothing and implements nothing.
- **Level:** 2–3 (research-impacting; defines the tested operating envelope and the
  validity of every later generalisation claim).
- **Brief:** `docs/PHASE6_STEP10_DESIGN_BRIEF.md` (§1–§11; §10 researcher decision
  form is BLANK).
- **Why now:** STEP 10 was the last design layer before scientific PPO training.
  Disk evidence: `PROJECT_STATE.yaml phase6.steps.step10…` = NOT STARTED;
  `src/env/demand_scenarios.py` absent; `src/env/baselines.py` is an action-mask
  interface imported only by its unit test; `experiments/ppo/evaluate.py` evaluates
  a single PPO model with no scenario or baseline support.
- **Measured evidence carried (read-only, from the working INP):** PATTERN-0 has 96
  multipliers at a 30-min pattern timestep (48 h) and is the default pattern for
  ~124 of 126 junctions, so it repeats exactly twice per 96 h episode; its two 24 h
  halves are NOT identical (46/48 slots differ, max |Δ| 1.17, day-1 mean 0.7327 vs
  day-2 mean 1.0385); the frozen observation carries only 24 h sin/cos, so
  same-hour states on different days are aliased. Classified as an existing
  POMDP limitation (D-P6-004), NOT a defect and NOT grounds to change the
  observation.
- **Mechanical constraint recorded:** `SteppingHydraulicDriver.reset()` computes the
  requested-demand series once via `expected_demand(wn_full)`, while each control
  step rebuilds a fresh segment from the working copy. A scenario must therefore
  perturb BOTH paths and must be a pure deterministic function of
  (scenario_id, junction, absolute time), or DSR/unserved accounting silently drifts
  and the demand sequence restarts at segment boundaries.
- **Open decisions (all unresolved):** D1 temporal structure (U1 persistent /
  U2 per-step / U3 diurnal-shape); D2 magnitude & distribution (M1 truncated normal
  [0.7,1.3] — the only range with project-record precedent, Hu et al. 2023, a
  precedent on Net3, NOT evidence for BWSN-1; M2 [0.8,1.2]; M3 uniform); D3 spatial
  structure (S1 global / S2 per-junction i.i.d. / S3 spatially smooth); D4 split &
  seed policy; D5 baseline/evaluation protocol; D6 handling of the 48 h/24 h
  aliasing.
- **Protocol invariants proposed (not parameter choices):** scenario identity +
  seed derived from a master seed via `SeedSequence.spawn` so groups cannot collide;
  train/validation/test deliberately share the SAME family and range (in-distribution
  generalisation) and are separated by disjoint seeds; OOD reported separately and
  never used for selection; test evaluated once, checkpoints selected on validation;
  every condition evaluated on identical scenario IDs (paired); no composite score.
- **Baseline semantic that must not be conflated:** `native` is the fixed frozen
  hydraulic baseline requiring no training; `prv_only` / `vsp_only` / `joint` are
  LEARNED conditions requiring separately trained policies. Applying an action mask
  to a joint-trained policy is NOT the corresponding ablation condition.
- **Scope conflict recorded (narrow):** the D-P6-006 register mandates the
  ε_p ∈ {0,2,5} psi and H ∈ {1,2,4,8} sweep as a **STEP-12** activity, while the
  `docs/RECOVERY.md` banner lists it under STEP-10. The register is authoritative;
  the sweep is NOT part of STEP 10 and was not run.
- **Status:** PROPOSED / DECISION PENDING RESEARCHER. No scenario module, no split,
  no baseline harness and no evaluation driver were implemented. No frozen decision
  changed. No PPO training performed.
- **Focused review addendum (2026-10-19, methodology review — recommendations only,
  no approval implied):** two clearly labelled addenda were inserted into the brief:
  (1) §5 D5 — under deterministic rollouts (`reset` seeds nothing stochastic;
  `model.predict(deterministic=True)`) K>1 evaluation episodes per (condition,
  scenario) are exact duplicates, so K=1 + an explicit determinism check is
  RECOMMENDED, with mean ± spread taken across scenarios/training seeds instead;
  (2) §5 D4 — training presentation (fixed 8-scenario enumerated set vs per-episode
  seeded sampling over the same family, evaluation sets fixed either way):
  per-episode seeded sampling is RECOMMENDED (near-zero cost delta). A
  `D4_training_presentation` field was added to the §10 decision form. Both remain
  researcher selections.
- **Next (superseded 2026-10-19):** see the implementation record below.

- **Selection + implementation record (2026-10-19).** The researcher's STEP-10
  implementation directive (2026-10-19) communicated the D-P6-007 selections and
  authorised implementation in the same act; they are recorded verbatim in the
  brief's §10 form with truthful provenance (an implementation-authorising
  selection, not a separately signed "APPROVED & FROZEN" act of the D-P6-001..006
  kind — this register entry remains the status authority). Selections:
  **U1** (one multiplier per 96 h episode) · **M1** exact truncated normal
  (inverse-CDF, μ=1.0, σ=0.1, [0.7, 1.3], analytic std 0.0986578) · **S1** for
  training + in-distribution eval, **S2** (independent per-junction factors, 79
  demand junctions) for OOD · master seed **20261019** (SeedSequence spawn keys
  train=0/val=1/test=2/ood=3, disjoint streams, no leakage) · training =
  **B** per-episode seeded sampling (NEW multiplier at every reset, never a cycled
  set; scenario id + multiplier logged every episode) · fixed evaluation set =
  4 validation + 4 test (U1/M1/S1) + 2 OOD (U1/M1/S2), stable IDs · **K=1**
  deterministic rollout per (condition, scenario) + one explicit repeatability
  check (a duplicate rollout is a determinism check, not an independent sample) ·
  3 training seeds planned for the final Colab evaluation (not part of this
  implementation) · 48 h/24 h aliasing **accepted and documented** · ε_p–H sweep
  confirmed **STEP-12** (unchanged). D-P6-001..006 were not reopened.
- **Implemented & verified (2026-10-19, laptop only; no PPO training, no STEP-12
  sweep, no commit):** `src/env/demand_scenarios.py` (scenario module) +
  integration into `src/env/epanet_adapter.py` (scenario applied to BOTH the
  1800 s segment solves and the full-horizon `expected_demand` accounting
  path; mid-episode swap guard) and `src/env/bwsn_env.py` (modes native/train/
  val/test/ood/instance, `set_demand_scenario`, scenario metadata in `info`
  ONLY) + `experiments/ppo/` wiring (`make_env.py` baseline-mask wrappers,
  `config.py` demand_scenario/baseline_mode/scenario_master_seed,
  `evaluate.py` paired fixed-scenario protocol with native baseline via
  `_NativePredictor`, `train.py` scenario + baseline-mode flags,
  `callbacks.py` env/scenario_id + env/scenario_multiplier logging). Frozen
  observation (139), action (7), reward, safety and every D-P6-001..006 value
  UNCHANGED. Default `demand_scenario="native"` reproduces the frozen anchors:
  `verify_env --full` PASS (leak 84.72943575468366, rel 5.29e-6 < 5e-5; min
  service pressure 4.163939952850342, |Δ| 5.82e-4 psi < 1e-2; 0 negative
  instants; horizon 192; working-INP SHA-256 match). Tests:
  `tests/test_demand_scenarios.py` (19) + `tests/test_env_scenarios.py` (16,
  real EPANET) all OK; full battery **298 tests OK in 40.8 s**. NOT exercised
  locally: SB3/gymnasium-dependent subchecks (torch/SB3 intentionally not
  installed on the laptop — Colab's job). No scientific training, no
  performance claim.
