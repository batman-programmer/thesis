# PHASE6_D_P6_005_DECISION_BRIEF.md — Reward Formulation & Parameter Selection

**Decision ID:** D-P6-005 — Final reward formulation and parameter selection
**Status:** **PROPOSED / DECISION PENDING RESEARCHER**
**Prepared:** 2026-09-27 (UTC) · **Prepared by:** Claude Opus 4.8 (AI research partner)
**Authority:** This is a DECISION BRIEF, not a decision. The researcher — not the AI —
selects ONE formulation and its parameters. Nothing here selects, ranks, scores, or
declares a winner among F1–F4 (constitution §16; task PART 12).

> **This brief converts the completed STEP 8 evidence (WU-9 scale analysis + WU-10
> formulation comparison) into a decision-ready package.** It runs no new EPANET
> simulation, trains no PPO, adds no STEP-9 safety clamp, and modifies neither the
> approved action space (D-P6-001/002/003) nor the frozen observation spec (D-P6-004).

Machine-readable companion: [`results/phase6/p6_d_p6_005_decision_brief.json`](../results/phase6/p6_d_p6_005_decision_brief.json)
(`researcher_selection: null`). Test battery: [`tests/test_decision_brief.py`](../tests/test_decision_brief.py).

---

## 1. Decision context (reconstructed from disk)

State reconstructed from the repository, not from chat. Where chat and disk could
disagree, disk governs (task PART 1).

| Item | Value (from disk) |
|---|---|
| Project phase | Phase 6 — design & validate a defensible DRL environment (NOT train PPO) |
| Current STEP | STEP 8 (reward design) COMPLETE as *measurement*; this brief is the D-P6-005 decision gate |
| Git HEAD | `262b738` — "phase6: record reward-formulation-comparison commit hash (checkpoint)" |
| Branch | `main`, 12 commits ahead of `origin/main`, 0 behind |
| Working tree | clean apart from pre-existing untracked/modified scratch under `results/phase5/_tmp/*` and `__pycache__/*.pyc` (excluded from commits) |
| D-P6-004 (observation) | **APPROVED & FROZEN** 2026-09-27 — `observation_dim = 139` |
| D-P6-005 (reward) | **PROPOSED** 2026-09-27 — NOT resolved; this brief prepares the selection |
| STEP 8 status | WU-9 (scale analysis) + WU-10 (formulation comparison) COMPLETE; no formulation selected |
| Contradictions on disk | **None.** The two-commit checkpoint pattern (`a9654c2` deliverable → `262b738` records its hash) is intentional, not a conflict |

**What D-P6-005 decides:** the reward *formulation* (functional form) and its *parameters*
(weights / penalties / thresholds / normalisation constants). **What it does not decide:**
the STEP-9 execution-level safety clamp (separate), the action space (frozen), the
observation (frozen), or any PPO hyperparameter.

---

## 2. Frozen constraints the reward must respect

### 2.1 Action space — D-P6-001/002/003 (APPROVED & FROZEN)

- Encoding: **ABSOLUTE**, `a_i ∈ [-1,1]`, `physical_i = lower_i + ((a_i+1)/2)·(upper_i−lower_i)`.
- `action_dim = 7`, `Box([-1,1]^7)`, float32. Ordered vector:

| idx | actuator | lower | upper | unit |
|---|---|---|---|---|
| 0 | VALVE-173 | 54.5 | 100.0 | psi |
| 1 | VALVE-175 | 21.5 | 110.0 | psi |
| 2 | VALVE-176 | 20.0 | 59.524 | psi |
| 3 | VALVE-177 | 20.0 | 90.0 | psi |
| 4 | VALVE-178 | 20.0 | 74.0 | psi |
| 5 | PUMP-170 | 0.82 | 1.10 | rel. speed |
| 6 | PUMP-172 | 0.77 | 1.10 | rel. speed |

- Pumps: **SPEED only**, re-issued every control step; native STATUS rules intact.
- Excluded valves {174, 179, 180} **remain in the hydraulic model** (179 safety-critical).
- Upper bounds for 175/176/177/178 are "highest tested REGULATING setpoints" (grid cap),
  NOT physical ceilings. Joint 5-D box safety is characterised at ONE lower corner only.

### 2.2 Observation — D-P6-004 (APPROVED & FROZEN)

- `observation_dim = 139`, float32. The reward reads this state but **MUST NOT modify it**.
- Layout: pressures[0:121] (121 sorted service junctions), tank_levels[121:123],
  prev_cmd_prv_setpoint[123:128], prv_is_active[128:133], prev_cmd_pump_speed[133:135],
  pump_realized_speed[135:137], time_of_day sin/cos[137:139].
- Demand = Option A (no explicit demand; diurnal time-of-day prior; **future demand FORBIDDEN**).
- Fixed physical normalisation only (no running statistics).

### 2.3 Service-node policy & solver policy (non-negotiable)

- **121 service junctions**; **5 connector junctions excluded** from service features/metrics
  but kept in the model (JUNCTION-105/106/109/110/128; elevation 0.0 ft AND zero base demand).
- Solver: ACCURACY 1e-5, TRIALS 2000, rule 180 s, report 1800 s; PDA 20 psi required /
  0 minimum / exponent 0.5. 96 h EPS → 193 report timesteps.
- `working_inp_sha256 = 53015ba9…a20a9`.

---

## 3. Evidence base

All numbers below are read from committed artefacts, not from memory.

| Artefact | Role | Coverage |
|---|---|---|
| [`results/phase6/p6_s8_reward_scale_analysis.json`](../results/phase6/p6_s8_reward_scale_analysis.json) (WU-9) | natural scales, correlations, pathologies, frozen normalisation constants | 19 static in-bounds configs × 193 ts = **3667 pooled instants** |
| [`results/phase6/p6_s8_reward_formulation_comparison.json`](../results/phase6/p6_s8_reward_formulation_comparison.json) (WU-10) | F1–F4 per-config reward behaviour, induced incentives, pathologies A–H, sensitivity sweeps | same 19 configs × 193 ts |
| [`docs/PHASE6_REWARD_SPEC.md`](PHASE6_REWARD_SPEC.md) §8.1–§8.11 | prose evidence base | — |

**Coverage caveat (do not overstate):** the 19 configs are the reference plus per-PRV
edges and joint corners — **NOT** an interior sweep of the 5-D box. Every claim here is a
*relative* response on this in-bounds set. Leakage is a **validation instrument, not
field-calibrated**; only relative leakage response is meaningful.

**Frozen normalisation constants (measured once, no running stats — no train/eval leakage):**

| constant | value | provenance |
|---|---|---|
| `leak_ref_gpm` | 84.72988433677985 | baseline mean leakage |
| `req_ref_gpm` | 906.3987348621764 | baseline requested demand |
| `deficit_ref_psi_nodesum` | 28.671793365478514 | max(baseline mean deficit, pooled p95) |
| `power_ref_kw` | 88.10062475649187 | baseline pump hydraulic power |
| `movement_L2sq_max` | 28.0 | analytic max of ‖Δa‖² over `[-1,1]^7` |

Derived baseline reference (for F3): `unserved_ref ≈ 14.985 GPM` (accounting); DSR-implied
≈ 15.10 GPM. The two artefacts carry **identical** constants (checked, abs diff < 1e-9).

---

## 4. Candidate formulations (F1–F4)

All four are **PROPOSED**; negative-cost sign convention; evaluated per 1800 s report step;
no discounting applied in measurement. Provisional parameters shown are the **comparison-only
illustrative constants from WU-10 — they are NOT proposed weights.** Evidence labels:
**OBSERVED** (measured), **INFERRED** (reasoned from measurements), **PROPOSED** (design choice).

### F1 — normalized_weighted_sum
```
r_t = - w_L·(leak_t/leak_ref) - w_U·(unserved_t⁺/req_ref) - w_P·(deficit_t/deficit_ref)
      - w_A·(‖Δa_t‖²/28) - w_E·(power_t/power_ref)
```
- **Components:** leakage, unserved-demand⁺, pressure deficit, actuator movement (on the
  **commanded** normalised action), optional hydraulic energy.
- **Params to approve (PART 7):** `w_L, w_U, w_P, w_A, w_E` (5). WU-10 illustrative: {1,1,1,1,0}.
- **Assumptions:** all terms pre-normalised to O(1) (OBSERVED via frozen constants); effort
  uses commanded action to avoid the closed-pump realized-speed gaming (OBSERVED, pathology G).
- **Expected behaviour:** dense, differentiable, smooth — PPO-continuous friendly (INFERRED).
- **Observed behaviour:** induced-incentive argmax = `prv_176_upper` under unit weights;
  leak-only optimum at the PRV lower corner (OBSERVED).
- **Pathologies:** boundary-seeking (needs STEP-9 clamp); un-normalised movement (L2²≤28)
  would dominate O(1) terms if `w_A` not scaled (OBSERVED, pathology C).
- **Uncertainty:** realised movement distribution unknown (static runs = 0 movement) → the
  effort scale is analytic (HYPOTHESIS).

### F2 — constrained_penalty_service_protected
```
r_t = -(leak_t/leak_ref) - Λ·(deficit_t/deficit_ref) - BIG·max(0, n_below20_t)
```
- **Params to approve:** `Λ (lambda_service)`, `BIG (big_hard)` (2). WU-10 illustrative: {20, 100}.
- **Assumptions:** service protected "by construction" via a large penalty (PROPOSED).
- **Observed behaviour:** bimodal reward (pooled mean −194.3, std 42.4); the hard 20-psi
  count term **fires on the native baseline itself** (frac 1.0) → **ill-posed as written**
  on this network (OBSERVED, pathologies F/G). See §6.
- **Uncertainty:** Λ sets the leakage↔service exchange rate; value judgement, not measured.

### F3 — baseline_relative_improvement
```
r_t = (leak_ref - leak_t)/leak_ref - w_U·max(0, unserved_t - unserved_ref)/req_ref
      - w_P_safety·(deficit_t/deficit_ref)
```
- **Params to approve:** `w_U`, `w_P_safety` (2); baseline `unserved_ref` fixed. WU-10 illustrative: {1,1}.
- **Assumptions:** interpretable as fractional leakage reduction vs the native controller;
  zero-centred at baseline (INFERRED).
- **Observed behaviour:** argmax `prv_176_upper`; small dynamic range (leak span ~±6%).
- **Uncertainty:** small reward magnitude → advantage/return scaling may be needed at training.

### F4 — safety_first_lexicographic
```
if min_svc_p < 0:      r_t = -c_hard - deficit_t/deficit_ref
elif min_svc_p < θ:    r_t = -c_soft - deficit_t/deficit_ref
else:                  r_t = -(leak_t/leak_ref) - ε·(‖Δa_t‖²/28)
```
- **Params to approve:** `θ (safety_threshold)`, `c_soft`, `c_hard`, `ε (eps_effort)` (4).
  WU-10 illustrative: {20, 10, 100, 0.01}.
- **Assumptions:** encodes the priority hierarchy safety > service > leakage > effort (PROPOSED).
- **Observed behaviour:** θ=20 makes the soft branch fire on the baseline (min svc 4.16 psi);
  θ=0 never fires but is permissive (OBSERVED, pathology G; sensitivity F4). See §6.
- **Uncertainty:** threshold choice interacts with the chronic sub-20-psi baseline (§6).

---

## 5. Quantitative evidence & factual decision dimensions

### 5.1 Measured component scales (WU-9 pooled, 3667 instants)

| component | mean | median | std | range [min, max] |
|---|---|---|---|---|
| leakage (GPM) | 84.95 | 84.68 | 2.52 | [79.92, 90.15] |
| requested demand (GPM) | 906.40 | 774.01 | 578.20 | [28.3, 2736.9] |
| unserved demand (GPM) | 23.80 | 11.85 | 33.79 | [−0.07, 221.79] |
| DSR | 0.9734 | 0.9827 | 0.0288 | [0.9142, 1.00246] |
| pressure deficit (psi node-sum) | 19.86 | 18.31 | 4.67 | [14.08, 31.73] |
| n nodes < 20 psi | 1.79 | 2.0 | 0.41 | [1, 3] |
| min service pressure (psi) | 4.77 | 4.93 | 1.08 | [1.09, 5.93] |
| n nodes negative | 0.0 | 0.0 | 0.0 | [0, 0] |
| pump hydraulic power (kW) | 79.85 | 0.0 | 104.92 | [0, 323.6] |

Key facts: leakage is ~10× smaller than demand and varies within a **narrow ±~6% band**
(OBSERVED) → a raw weighted sum is dominated by demand; **fixed normalisation is mandatory**
(scale imbalance ratio 7.15, OBSERVED). Negative-pressure count is identically 0 in-bounds →
a pure hard-violation term is **sparse/degenerate** (OBSERVED). Pump power is bimodal
(median 0), native-STATUS driven → energy term optional, hydraulic-only.

### 5.2 Cross-component correlations (WU-9) — objectives genuinely oppose

- leak ↔ DSR **+0.750**, leak ↔ deficit **−0.774**, leak ↔ n_below20 **−0.742**,
  DSR ↔ deficit **−0.965**, unserved ↔ DSR −0.736 (OBSERVED).
- **Interpretation:** pressing leakage down erodes service and raises pressure deficit →
  **service must be protected explicitly**; leakage cannot be the sole objective (OBSERVED).

### 5.3 Pathology evidence (WU-9 + WU-10 A–H)

- Leakage-only (`prv_all_lower`): leak 84.73→81.38 GPM (**−4.0%**) but DSR 0.98334→0.91940
  (**−6.4 pts**), min svc 4.19 psi — leakage-only is unsafe (OBSERVED).
- Pressure-only (`prv_all_upper`): leak 84.73→89.76 GPM (**+5.9%**), n_below20 386→193 (OBSERVED).
- **Induced-incentive argmax = `prv_176_upper` for ALL FOUR formulations** under provisional
  params (spreads F1 0.541 / F2 110.5 / F3 0.525 / F4 0.526) — an incentive-direction
  indicator, **NOT a ranking** (OBSERVED).
- Actuator penalty domination: leak-term dynamic range **0.108** vs max single-step move
  cost **1.0** → effort must be normalised by 28 and weighted down (OBSERVED, pathology C).
- Boundary-seeking: leak optimum on the PRV lower corner, worst pooled min svc 1.09–1.29 psi
  → **STEP-9 hard clamp REQUIRED** (OBSERVED).

### 5.4 Factual decision dimensions (PART 5 — NOT scored, NOT ranked)

Use these to reason about trade-offs; **do not** convert them into a score or ranking (PART 12):

1. Leakage-management signal (dense vs relative).
2. Service preservation (explicit vs by-construction).
3. Pressure-safety signal density (dense deficit / worst-node vs sparse hard count).
4. Signal density (dense vs sparse/degenerate terms).
5. Scale stability under fixed normalisation.
6. Interpretability / thesis explainability.
7. Parameter count and sensitivity (fewer = fewer value judgements).
8. Reward-hacking resistance (commanded-action effort; closed-pump ambiguity).
9. PPO-continuous-action compatibility (smoothness, boundedness).
10. STEP-9 safety-layer compatibility (does the reward assume a clamp?).
11. Reproducibility / no data leakage (fixed constants).
12. Baseline relatability (zero-centred at the native controller?).

---

## 6. The chronic baseline sub-20-psi service issue (PART 8)

**Observation (OBSERVED):** the frozen native baseline already holds ≥1 service node below
20 psi at **every** report timestep — `frac_ts_any_node_below_20psi = 1.0`, 386 node-timesteps
< 20 psi, min service pressure **4.16452 psi** @ JUNCTION-29 — with **0** negative-pressure
nodes. Above-nominal PRV settings recover service (`prv_all_upper` and `prv_176_upper` both
drop 386→193 below-20 node-timesteps), but no in-bounds config reaches zero nodes below 20 psi.

**How each threshold-handling choice behaves on THIS network:**

| Handling | Well-posed here? | Note |
|---|---|---|
| Absolute hard 20-psi constraint | **NO** | Penalises the native baseline at every step; cannot separate agent-caused from pre-existing violations. |
| Deficit-based penalty (∑ max(0, 20−p_i)) | **YES** | Dense, smooth, normalised by `deficit_ref`; deficit↔leak −0.774. |
| Improvement-relative-to-baseline | **YES** | Penalise only unserved/deficit ABOVE baseline; zero-centred (F3 / C-C). |
| Worst-node min-pressure | **YES** | Dense min-pressure signal (mean 4.77, range [1.09, 5.93]); F4 trigger. |
| Min-pressure hard constraint | Only on **negative** pressure | Baseline negative count = 0 → well-posed; a hard 20-psi min is NOT (baseline violates it). |
| Fraction-below-threshold | Degenerate as a gate | Fraction = 1.0 at baseline; usable only as a dense/relative signal. |

**Conclusion (stated plainly, PART 8):** **No formulation can use a hard 20-psi constraint
without penalising the baseline itself.** The defensible reward-level safety channels are the
**dense deficit**, **worst-node min-pressure**, and **baseline-relative** signals. Any hard
gate must key on **negative pressure** (or a threshold strictly below the baseline worst-node
~4.16 psi). The enforced 20-psi guarantee belongs to the **STEP-9 execution-level clamp**, not
to a reward-level hard term. This directly affects F2 (drop/replace the hard 20-psi term) and
F4 (θ=20 fires on the baseline; θ must sit below the baseline worst-node, or the soft branch
must be read as baseline-relative).

---

## 7. Provisional candidate parameterizations (PART 9)

The following are a **small decision-ready menu**. Every one is labelled
**"PROVISIONAL CANDIDATE — NOT APPROVED"**. Each numeric constant is traced to a MEASURED
scale; **none is tuned to a preferred result and none is ranked** (PART 12). The researcher
may adopt, adjust, or reject any of them. Full machine-readable specs (equations, constants,
derivations, trade-offs, risks, validation experiments) are in the companion JSON under
`candidate_parameterizations`.

**C-A — F1 balanced dense** · *PROVISIONAL CANDIDATE — NOT APPROVED*
- Form: F1. Weights: `w_L=1, w_U=1, w_P=1, w_A=0.1, w_E=0`.
- Scale derivation: all active terms pre-normalised to O(1) by frozen constants → unit weights
  are the neutral start. `w_A=0.1` from measured leak-term dynamic range **0.108** vs max-move
  cost 1.0, so a full-swing step is commensurate with (not dominating) the leakage signal.
  `w_E=0` avoids parameter proliferation.
- Trade-off: balanced, dense, PPO-friendly; boundary-seeking → STEP-9 clamp required.
- Risk: `w_P<0.5` lets the incentive drift to the low-pressure corner (WU-10 F1 sweep).
- Validation: after STEP-9, short PPO smoke test; measure realised ‖Δa‖² to replace the
  analytic effort ceiling (HYPOTHESIS).

**C-B — F1 safety-leaning** · *PROVISIONAL CANDIDATE — NOT APPROVED*
- Form: F1. Weights: `w_L=1, w_U=1, w_P=2, w_A=0.1, w_E=0` (a different emphasis of C-A, NOT
  a ranking).
- Scale derivation: heavier normalised deficit weight (still O(1)) motivated by deficit↔leak
  −0.774 and the dense worst-node min-pressure signal.
- Trade-off: stronger worst-node protection may reduce achievable leakage cuts.
- Risk: over-weighting deficit can flatten the (~±6%) leakage gradient.

**C-C — F3 baseline-relative** · *PROVISIONAL CANDIDATE — NOT APPROVED*
- Form: F3. Weights: `w_U=1, w_P_safety=1`; `unserved_ref` fixed at baseline.
- Scale derivation: leak improvement term intrinsically normalised (fraction of baseline) and
  zero-centred → no leak weight needed; keep `w_P_safety≥1` (WU-10 F3 sweep: 0 → low corner).
- Trade-off: directly expresses the thesis objective (reduction vs baseline); small dynamic
  range (~±6%) → check signal-to-noise.
- Risk: small reward magnitude may need return/advantage scaling at training.

**C-D — dense-deficit, no hard count** · *PROVISIONAL CANDIDATE — NOT APPROVED*
- Form: F2/F4 family. `r = -(leak/leak_ref) - Λ·(deficit/deficit_ref) - BIG·max(0, n_negative)`.
- Weights: `Λ=5, BIG=100`.
- Scale derivation: **explicitly replaces** the ill-posed hard 20-psi count (§6) with the dense
  deficit term; the hard term is retained **only on negative nodes** (baseline count 0 → well
  posed). `Λ=5` keeps the normalised deficit term within ~1 order of magnitude of the O(1) leak
  term; central value in [1,10], not fitted.
- Trade-off: well-posed on this network; `Λ` sets the leakage↔service exchange rate (researcher's).
- Risk: WU-10 F2 sweep argmax stable (direction robust) but magnitude untuned; large `Λ`
  suppresses the leakage gradient.

---

## 8. Sensitivity evidence (PART 10)

**Small, deterministic parameter sweeps already on disk (WU-10 `sensitivity_results`) — no
re-run, no PPO, no broad HPO. These show INCENTIVE DIRECTION (argmax config), NOT a ranking
or score.**

| Sweep | Low | Central | High |
|---|---|---|---|
| F1 vary `w_P` | 0 → `prv_175_lower` | 0.5 → `prv_176_upper` | ≥1 → `prv_176_upper` |
| F1 vary `w_U` | all `prv_176_upper` | all `prv_176_upper` | all `prv_176_upper` |
| F2 vary `Λ/BIG` | all `prv_176_upper` | all `prv_176_upper` | all `prv_176_upper` |
| F3 vary `w_U/w_P_safety` | `w_P_safety=0` → `prv_175_lower`/`prv_lower_pump_lower` | ≥1 → `prv_176_upper` | ≥1 → `prv_176_upper` |
| F4 vary `θ` | θ=0 → `prv_lower_pump_lower` | — | θ=20 → `prv_176_upper` |

**Analytic reading of the movement weight `w_A`** (new in C-A/C-B; static runs have 0 movement,
so this is ANALYTIC, not fitted): low `w_A=0` (no smoothness pressure) · central `w_A=0.1`
(max-move step ≈ leak-term range ~0.108) · high `w_A=1.0` (one max-move step, cost 1.0,
dominates the leak signal ~0.108). Realised effort is a training-time HYPOTHESIS.

**Reading:** incentive direction is largely stable at `prv_176_upper` once a minimal
pressure/service weight is present; it collapses toward the low-pressure corner only when the
safety weight is set to 0 or the lexicographic threshold is 0. This is a property of the
incentive landscape, **not** a basis for declaring any formulation superior.

---

## 9. Reward vs safety: separation of concerns (PART 11)

- **Reward level (D-P6-005, this decision):** dense / relative service and pressure terms
  **shape** behaviour. They do **not** and **cannot** guarantee any pressure bound.
- **Execution level (STEP-9, separate, NOT in this brief):** a state-dependent safety clamp to
  the APPROVED action bounds is **required** to enforce feasibility. WU-9/WU-10 boundary-seeking
  checks show the leak optimum sits on the PRV lower corner, so a clamp is mandatory, not optional.
- **Boundary:** `action bounds (frozen) ≠ reward shaping (D-P6-005) ≠ safety clamp (STEP-9)`.
  This brief adds no clamp and starts no STEP-9 work.

---

## 10. Open uncertainties

1. **Realised actuator-movement distribution is unknown** (static runs = 0 movement); the
   effort/smoothness scale is analytic → HYPOTHESIS until a policy trajectory exists.
2. **Leakage is a validation instrument, not field-calibrated**; only relative response is
   meaningful — never an absolute leakage claim.
3. **Joint 5-D in-box safety** is characterised at a single lower corner only; interior/mixed
   corners and pump+demand interactions are a STEP-9 / STEP-12 job.
4. **Weights / Λ / thresholds set leakage↔service exchange rates** that are value judgements
   for the researcher, not measured quantities.
5. **Pump power is hydraulic only** (no efficiency curve); an energy term is optional.

---

## 11. Researcher decision block

*To be completed by the researcher. The AI must NOT fill this in (task PART 13).*

```
D-P6-005 — Reward formulation & parameter selection

Selected formulation:        __________________________________________
                             (F1 / F2 / F3 / F4 / a named candidate / other)

Selected parameters:         __________________________________________
                             (exact weights / Λ / BIG / θ / c_soft / c_hard / ε / w_A / w_E)

Normalisation constants:     [ ] adopt frozen WU-9 constants as-is
                             [ ] other: ___________________________________

Safety-term choice (§6):     __________________________________________
                             (dense deficit / worst-node min-pressure / baseline-relative /
                              negative-only hard gate; NO hard 20-psi reward term)

Rationale:                   __________________________________________

Approval date:               __________________________________________

Approval status:             [ ] APPROVED   [ ] REVISIONS REQUESTED   [ ] REJECTED
```

---

*End of brief. D-P6-005 remains **PROPOSED / DECISION PENDING RESEARCHER**. Nothing in this
document selects, ranks, scores, or declares a winner among F1–F4.*



