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
