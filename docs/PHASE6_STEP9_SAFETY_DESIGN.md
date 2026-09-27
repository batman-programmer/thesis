# PHASE 6 — STEP 9: State-Dependent Safety-Mechanism Design Analysis (WU-14)

**Status:** DESIGN ANALYSIS ONLY — four candidate mechanisms characterised; **no mechanism
selected, scored, or ordered by quality**; **no production safety wrapper implemented**; no
`reward.py`; no PPO. Mechanism selection + implementation is a later STEP-9 step and a separate
researcher decision (DEFERRED).

**Date:** 2026-09-27 · **Work unit:** WU-14 · **Preceded by:** D-P6-005 = APPROVED
(C-A_F1_balanced_dense) recorded in [PHASE6_DECISION_REGISTER.md](PHASE6_DECISION_REGISTER.md)
and `PROJECT_STATE.yaml :: reward.approved`.

## Artefacts

| Artefact | Path |
|---|---|
| This design note | `docs/PHASE6_STEP9_SAFETY_DESIGN.md` |
| Machine-readable analysis | `results/phase6/p6_s9_safety_design_analysis.json` |
| Pure-aggregator generator | `src/validation/p6_s9_safety_design_analysis.py` |
| Test battery | `tests/test_safety_design_analysis.py` (21 tests) |

The generator is a **pure aggregator**: it re-loads the WU-11 decision brief
(`results/phase6/p6_d_p6_005_decision_brief.json`), copies every number verbatim (no drift),
runs **no** EPANET / PPO / RNG, and byte-reproduces the JSON on re-run.

## 1. Three distinct layers (do not conflate)

STEP 9 concerns a **state-dependent** safety mechanism, which is DISTINCT from the frozen
action-space bounds:

1. **Action bounds (D-P6-001/002/003, FROZEN):** keep each of the 7 actuators inside a *static*
   box (e.g. VALVE-173 ∈ [54.5, 100] psi). Independent of the resulting hydraulic state.
2. **Reward shaping (D-P6-005, APPROVED — C-A/F1):** dense normalized weighted cost. It *shapes*
   behaviour but **guarantees no pressure bound** (`safety_dependencies` in the brief).
3. **State-dependent safety mechanism (STEP 9, this analysis):** reacts to the *resulting*
   hydraulic STATE (worst-node pressure, deficit, negative pressure) and can clip or reject an
   action. This is what is characterised here.

`separation_of_concerns` (from the brief): *action bounds (frozen) ≠ reward shaping (D-P6-005)
≠ safety clamp (STEP 9).*

## 2. Why a naive absolute 20-psi reject is ill-posed (measured)

The frozen native baseline already holds **≥1 service node < 20 psi at every report timestep**:

- `n_node_timesteps_below_20psi = 386`, `frac_ts_any_node_below_20psi = 1.0`
- `n_node_timesteps_negative = 0`, `frac_ts_any_node_negative = 0.0`
- `min_service_psi_over_horizon = 4.16452 psi` (@ JUNCTION-29)

A hard rule *"reject any state with min pressure < 20 psi"* would therefore reject the native
baseline **itself** at every timestep and cannot separate agent-caused violations from
pre-existing chronic ones. The leak-only reward's highest-reward tested command sits on the PRV
lower corner (`prv_lower_pump_lower`) with worst-node service pressure **~1.29 psi** — yet still
**0 negative-pressure nodes**. So the only *hard absolute* condition that is well-posed on this
network is **negative** pressure; the enforced 20-psi service target belongs to a dense/relative
signal or to the STEP-9 execution-level clamp, not to a hard reward term.

## 3. Candidate mechanisms (S1–S4) — characterised, NOT ranked

The four candidates are reported on a **fixed 10-field schema**: `exact_rule`,
`information_required`, `compute_cost`, `baseline_compatibility`, `false_positive_risk`,
`false_negative_risk`, `ppo_compatibility`, `interval_30min_compatibility`, `requires_look_ahead`,
`preserves_determinism`. The enumeration order S1→S4 is **definitional, not evaluative** — no
candidate is called best/optimal/preferable, and none carries a score or rank.

### S1 — absolute worst-node pressure threshold
- **Rule:** intervene when `min_i p_i(a_t) < T_abs`; natural target `T_abs = 20 psi` (PDA required).
- **Info / cost:** post-action worst-node pressure → one look-ahead EPANET solve (~1× step cost).
- **Baseline compatibility:** **INCOMPATIBLE at 20 psi** (flags the baseline at every timestep;
  baseline worst node ~4.16 psi). Compatible only with `T_abs` strictly below the baseline worst node.
- **False-pos / false-neg:** HIGH at 20 psi / LOW at 20 psi.
- **PPO / interval / look-ahead / determinism:** clip-vs-reject trade-off / compatible (30 min) /
  YES (post-action) / YES.

### S2 — worst-node degradation vs current state
- **Rule:** intervene when `min_i p_i(a_t) < min_i p_i(current) − tol` (relative; tol configurable).
- **Info / cost:** current worst node (from observation) + candidate worst node (look-ahead).
- **Baseline compatibility:** **COMPATIBLE** (relative; never rejects an unchanged hold).
- **False-pos / false-neg:** MODERATE (tol-sensitive) / MODERATE–HIGH (a flat, already-low state escapes).
- **PPO / interval / look-ahead / determinism:** smooth → clip-friendly / compatible / YES / YES.

### S3 — total pressure-deficit increase
- **Rule:** intervene when `deficit(a_t) > deficit(current) + tol`, `deficit = Σ max(0, 20 − p_i)`.
- **Info / cost:** current + candidate deficit nodesum (look-ahead); `deficit_ref ~28.67` for norm.
- **Baseline compatibility:** **COMPATIBLE** (relative aggregate). Note deficit↔leak corr = **−0.7735**,
  so S3 directly opposes the reward's leak term as an *aggregate* guard.
- **False-pos / false-neg:** MODERATE / **HIGH for localised failures** (aggregation masks a single node).
- **PPO / interval / look-ahead / determinism:** smooth → clip-friendly / compatible / YES / YES.

### S4 — negative-pressure hard backstop
- **Rule:** intervene (hard) only when `min_i p_i(a_t) ≤ 0`. The only well-posed *hard absolute* gate.
- **Info / cost:** candidate negative-node count (look-ahead); shares the solve with S1–S3.
- **Baseline compatibility:** **FULLY COMPATIBLE** (baseline & every swept in-bounds config have
  0 negative nodes) — so, standalone, **it never fires on measured evidence and gives no 20-psi
  protection**.
- **False-pos / false-neg:** VERY LOW / **VERY HIGH w.r.t. 20 psi** (permits the whole 0–20 psi band).
- **PPO / interval / look-ahead / determinism:** rarely active → last-resort clip / compatible / YES / YES.

## 4. Baseline compatibility (STEP-9 §12)

Governing conclusion (from the brief): *no formulation can use a HARD 20-psi constraint without
penalising the native baseline itself; dense deficit / worst-node min-pressure / baseline-relative
service signals are the defensible channels; any hard gate must key on NEGATIVE pressure (or a
threshold strictly below the baseline worst node ~4.16 psi); the enforced 20-psi guarantee belongs
to the STEP-9 execution-level clamp.* Per-candidate flag: **S1** flags the baseline (at 20 psi);
**S2/S3** do not (relative); **S4** never fires on it.

## 5. Design investigation (STEP-9 §7–§10)

- **One-step look-ahead:** every post-action rule needs either one extra EPANET solve of the
  candidate action (~1× solver cost per 30-min decision) or reactive enforcement one step late.
  EPANET is deterministic, so a look-ahead adds no stochasticity.
- **Clip vs reject:** *clip* projects the commanded action into a state-dependent safe set and keeps
  a valid continuous action (executed ≠ commanded; the approved reward's effort term uses the
  **COMMANDED** `da`, so it stays intact, but PPO must observe the train/execute gap). *Reject/resample*
  breaks the deterministic action→state map and raises return variance. Characterised, not selected.
- **Fallback:** a guard needs a defined fallback when no in-box action satisfies it. Because the
  baseline is itself sub-20 everywhere, an absolute-20 guard has **no feasible fallback** — a
  relative guard (S2/S3) or a negative-keyed gate (S4) always has the current state as fallback.
- **Worst-node vs aggregate:** worst-node signals (S1/S2) protect the single critical junction;
  aggregate deficit (S3) can mask a localised collapse. A composite is a researcher design choice.

## 6. Action-space coverage limits (STEP-9 §13, R1b)

Only the **single lower corner** (`prv_lower_pump_lower` / `prv_all_lower`) has measured worst-node
service pressure (~1.29 psi leak-only argmax; ~4.19 psi all-lower) and negative-node count (0).
Interior points, mixed PRV corners, pump-speed extremes with PRV extremes, and the joint
(action × uncertain-demand) space are **not** characterised here. **Do NOT claim the 7-D action box
is globally safe** — exhaustive joint in-box safety is a STEP-9 (mechanism) + STEP-12 (test) job.

## 7. D-P6-005 record embedded here (for consistency)

The analysis embeds a machine-readable `d_p6_005_decision` block with `status = APPROVED`,
`selected_candidate = C-A_F1_balanced_dense`, and the equation/weights
(`w_L=1.0, w_U=1.0, w_P=1.0, w_A=0.1, w_E=0.0`) / five frozen constants copied **verbatim** from the
brief's C-A parameterisation. The WU-11 brief and WU-12 summary JSONs remain **PROPOSED /
researcher_selection = null** as frozen pre-decision evidence; the APPROVED record lives in
`PROJECT_STATE.yaml`, the decision register, and this artefact.

## 8. Reproducibility & tests

- Deterministic: re-running the generator byte-reproduces the JSON (no RNG, no re-measurement).
- `working_inp_sha256 = 53015ba9…20a9`; no topology / native-rule change; no future information used.
- `tests/test_safety_design_analysis.py` (21 tests): schema completeness, no-ranking / no-forbidden-key
  guarantees, D-P6-005↔C-A consistency, chronic-baseline & leak-only-argmax preservation, frozen
  action/observation/service-mask invariants, all-finite, and byte-reproduction.

## 9. Researcher action required (NOT done here)

Select (or compose) a STEP-9 mechanism from S1–S4, fix its threshold/tolerance and its
clip-vs-reject handling, then implement and test the production wrapper. **None of that is performed
in this work unit** — this is characterisation only.

---

# PHASE 6 — STEP 9 (WU-15): Empirical Characterisation of Candidate Safety Mechanisms & Action-Handling Policies

**Status:** EMPIRICAL EVIDENCE ONLY — candidate mechanisms **S1–S4** and candidate action-handling
policies **H1–H3** are *measured* on the frozen network so the researcher can make the STEP-9
decision **later**. **No mechanism or policy is selected, ranked, scored, or recommended**
(`researcher_selection = null`). No production safety wrapper, no `reward.py`, no PPO. This section is
**appended below** the WU-14 conceptual analysis (§1–§9 above) and does **not** replace it.

**Date:** 2026-09-28 · **Work unit:** WU-15 · **Preceded by:** WU-14 design analysis (§1–§9) and
D-P6-005 = APPROVED (C-A_F1_balanced_dense).

## Artefacts (WU-15)

| Artefact | Path |
|---|---|
| Machine-readable characterisation | `results/phase6/p6_s9_safety_mechanism_characterization.json` |
| Measurement generator | `src/validation/p6_s9_safety_mechanism_characterization.py` |
| Test battery | `tests/test_safety_mechanism_characterization.py` (26 tests) |

The generator **reuses the validated WU-8 instrument** (`p6_s8_reward_scale_analysis.py`) unchanged
for every hydraulic solve — same working INP (`sha256 53015ba9…20a9`), same PDA accounting, same
service mask (121 service / 5 connector junctions). It runs **10 EPANET solves** (4 base operating
points + 6 H2 α-interpolation points), ~8 s wall-clock, no RNG, no PPO. EPANET is deterministic, so
the numeric values reproduce on re-run; the JSON carries a `generated_utc` stamp and is therefore
**not** byte-reproduced (this deliberately differs from the frozen WU-11/WU-12 pre-decision JSONs).

## 10.1 Metric definitions (PART 4 / PART 23)

| Symbol | Definition | Note |
|---|---|---|
| `p_i` | PDA service pressure at junction `i` (psi) | 121 service nodes only |
| `p_min` | `min_i p_i` over service nodes | worst-node signal |
| `Δp_min` | `p_min(post) − p_min(current)` | relative worst-node change |
| `D` | `Σ_i max(0, 20 − p_i)` (psi·node) | aggregate deficit; `deficit_ref ≈ 28.67` |
| `ΔD` | `D(post) − D(current)` | aggregate deficit change |
| `N_neg` | `Σ_i I[p_i < 0]` | negative-pressure node count |
| `N_20` | `Σ_i I[p_i < 20]` | **descriptive only — not a safety oracle** |
| `Q_leak` | `Σ sign(p)·C·|p|^0.5` (gpm) | pressure-driven; **NOT calibrated** |
| `DSR` | `Q_served / Q_req` (PDA) | demand-satisfaction ratio |
| `Q_unserved` | `max(0, Q_req − Q_served)` (gpm) | PDA shortfall |
| `‖Δa‖²` | squared L2 of **commanded** normalized action step | reward-effort term uses COMMANDED |
| `action_deviation_L2` | `‖a_exec − a_prop‖` | executed-vs-proposed gap |

## 10.2 Candidate safety rules (PART 7 / PART 23) — SAFE means "do NOT intervene"

| Cand. | Rule (SAFE condition) | Type | Provisional grid measured |
|---|---|---|---|
| **S1** | `p_min(post) ≥ θ_p` | absolute worst-node | `θ_p ∈ {0, 5, 10, 15, 20}` psi |
| **S2** | `Δp_min ≥ −ε_p` | relative worst-node | `ε_p ∈ {0, 2, 5}` psi |
| **S3** | `ΔD ≤ ε_D` | aggregate deficit | `ε_D ∈ {0, 2, 5}` psi·node |
| **S4** | `N_neg(post) = 0` | negative-pressure hard backstop | (no threshold) |

The S1→S4 order is **definitional, not evaluative**. Each threshold value is **provisional** — swept
to expose behaviour, **not** tuned or selected. `safety_rule_outputs` reports, per rule × threshold,
only DESCRIPTIVE fields: `rule_activates_at_shared_initial`, `activation_fraction_sustained`,
`n_activations_sustained`, `n_instants`. Because there is **no validated safe/unsafe oracle**
(PART 5), **no** false-positive / false-negative rate or classification accuracy is computed.

## 10.3 Candidate action-handling policies (PART 12 / PART 23)

| Pol. | Executed action `a_exec` | Look-ahead cost | Determinism |
|---|---|---|---|
| **H1** | REJECT → previous action (`a_exec = a_prev`) | 0 extra solves (uses observed prev state) | deterministic |
| **H2** | CLIP toward previous: `a_exec = a_prev + α(a_prop − a_prev)`, largest `α` on grid `{0,¼,½,¾,1}` satisfying the rule | ≤ 5 solves per rule (one per grid α) | deterministic |
| **H3** | FALLBACK → documented reference action (`reference_nominal`, persisted) | 0 extra solves | deterministic |

Policies are **characterised, not auto-selected**. H2's admissible `α` is reported **per rule**
(`per_rule_admissible_alpha`) because the largest safe step depends on which rule is active.

## 10.4 Two look-ahead views per transition (honest severity accounting)

Every (current → proposed) transition is measured in **two** distinct ways:

- **`shared_initial_state` (report index 0):** a **strict single-step 30-min look-ahead** — every
  configuration shares *identical* initial tank levels at `t=0`, so `Δ`-metrics are a **pure command
  effect** with no tank-trajectory divergence.
- **`sustained_horizon` (per-instant over all 193 report instants):** descriptive distribution over
  the full 96 h EPS, explicitly **including tank-trajectory divergence** — **not** a strict
  single-step look-ahead.

**Key measured caveat.** For the severe command (`prv_lower_pump_lower`), the worst-node service
pressure at the shared-initial instant is **≈ 5.53 psi**, but its **sustained** worst-node minimum is
**≈ 1.29 psi** (tanks drain over the horizon). A naive single-step look-ahead at the decision instant
therefore **substantially understates** the command's sustained-horizon danger. Any look-ahead-based
STEP-9 mechanism inherits this gap; both views are persisted so the effect is visible, not hidden.

## 10.5 The most important empirical question (PART 18) — reported as a fact table

Can a candidate, at the shared-initial instant, BOTH (A) activate on the previously observed severe
degradation AND (B) *not* activate on legitimate intermediate control? Measured (booleans only — **no
selection**):

- **S4** activates on **neither** (no swept in-bounds config produced a negative-pressure node — see
  §10.6), so standalone it gives **no 20-psi protection**.
- **S1** at `θ_p ≥ 10` psi activates on **both** the severe and the intermediate transition at the
  shared-initial instant.
- **S3** at the measured `ε_D` grid activates on **both**.
- Only **S2 at `ε_p = 0`** activates on the severe transition while sparing the intermediate one at
  the shared-initial instant, and only by a **razor-thin margin** (severe `Δp_min ≈ −0.0102` psi vs
  intermediate `Δp_min ≈ +0.0006` psi). This separation is **not** claimed to generalise: it rests on
  a ~0.01 psi gap at a single instant on a single action corner.

This is **evidence, not a verdict**. The generator records the booleans; it does not conclude that any
candidate "passes" or "wins".

## 10.6 Baseline compatibility (PART 8 / §4 recap, now measured on identity hold)

The identity hold (`reference → reference`, `a_exec = a_prev`) reproduces the chronic-baseline
ill-posedness:

| Rule / threshold | `activation_fraction_sustained` on identity hold |
|---|---|
| S1 `θ_p = 20` | **1.0** (flags the native baseline at *every* instant) |
| S1 `θ_p = 5` | ≈ 0.451 |
| S1 `θ_p ≤ 4.16` | 0.0 (below the baseline worst node) |
| S2 (all `ε_p`) | **0.0** (relative rule never rejects an unchanged hold) |
| S3 (all `ε_D`) | **0.0** |
| S4 | **0.0** |

Confirms §4: a HARD absolute-20 gate penalises the baseline itself; relative (S2/S3) and
negative-keyed (S4) gates are baseline-compatible on the hold.

## 10.7 Aggregate-vs-worst-node interaction & local collapse (PART 10)

On the severe transition the aggregate deficit and worst-node signals **move together**: the
most-negative-worst-node instant shows `Δp_min ≈ −4.30` psi with `ΔD ≈ +14.06`, and the smallest
deficit-increase among negative-`Δp_min` instants is still `ΔD ≈ +9.72` (at `Δp_min ≈ −0.006`). So on
the *tested* corner, S3 (aggregate) is not observed to **mask** a worst-node collapse — but this is a
property of the single measured corner, **not** a general guarantee (see §10.8 / §6 R1b). The
"small ΔD hiding a large local collapse" failure mode is **conceptually possible** (§5 above) and was
simply **not exhibited** on the tested transitions; absence of evidence is recorded as such.

## 10.8 State-dependence of handling (PART 14)

The same proposed severe command handled from **two** current states yields **different** executed
actions: H1/H3 **coincide** on `reference → severe` (the current state *is* the documented fallback),
but **differ** on `high_pressure → severe` (previous-action fallback ≠ fixed reference fallback). This
directly demonstrates that action-handling output is **state-dependent**, as required.

## 10.9 Limitations carried forward (PART 19 / R1b)

- **Coverage:** only 4 base operating points + 6 α-interpolants on the PRV/pump corners are measured;
  interior points, mixed PRV corners, and the joint (action × uncertain-demand) space are **not**
  characterised. **Do NOT claim the 7-D action box is globally safe.**
- **No oracle:** no validated safe/unsafe ground truth ⇒ no FP/FN/accuracy (PART 5).
- **Look-ahead gap:** strict single-step look-ahead understates sustained danger (§10.4).
- **Coarse H2 grid:** `α ∈ {0,¼,½,¾,1}` — admissible-`α` values are lower bounds on the true largest
  safe step, not exact.
- **Uncalibrated leak:** `Q_leak` uses an uncalibrated emitter coefficient (relative use only).
- **Evidence only:** `researcher_selection = null`; mechanism/policy selection + production wrapper +
  `reward.py` + PPO are **out of scope** and deferred to the researcher (§9).
