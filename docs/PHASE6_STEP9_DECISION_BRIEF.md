# PHASE 6 — STEP 9: State-Dependent Safety-Mechanism **Decision Brief** (WU-17)

**Status:** `PROPOSED / PENDING RESEARCHER` — this brief **FRAMES** the four STEP-9 decisions
and **makes none of them**. No safety architecture, threshold, look-ahead horizon, or
action-handling policy is selected, ranked, scored, or recommended. No production safety
wrapper, no `reward.py`, no PPO. The project is **NOT PPO-ready**; STEP-9 selection is the
researcher's decision.

**Date:** 2026-09-28 · **Work unit:** WU-17 · **Type:** evidence synthesis / decision-brief
preparation (measures nothing new).

## Artefacts

| Artefact | Path |
|---|---|
| This decision brief | `docs/PHASE6_STEP9_DECISION_BRIEF.md` |
| Machine-readable brief | `results/phase6/p6_s9_decision_brief.json` |
| Pure-aggregator generator | `src/validation/p6_s9_decision_brief.py` |
| Test battery | `tests/test_step9_decision_brief.py` (26 tests) |
| Design analysis (WU-14) | `results/phase6/p6_s9_safety_design_analysis.json` |
| Empirical characterization (WU-15) | `results/phase6/p6_s9_safety_mechanism_characterization.json` |
| Temporal characterization (WU-16) | `results/phase6/p6_s9_temporal_safety_characterization.json` |
| Frozen reward brief (WU-11) | `results/phase6/p6_d_p6_005_decision_brief.json` |

The generator is a **pure aggregator**: it re-loads the four frozen JSON artefacts, copies their
evidence sub-trees verbatim, re-checks the frozen normalisation constants and the cross-artefact
baseline/collapse anchors, and writes the brief with `researcher_selection = null`. It runs **no**
EPANET / PPO / RNG, carries **no** `generated_utc`, and **byte-reproduces** on re-run (verified by
`test_deterministic_rebuild_matches_persisted_bytes`).

## 1. Context — the four decisions this brief frames (does NOT make)

STEP-9 is an **execution-level admissibility layer** distinct from the frozen action bounds and
from the approved reward. The researcher must decide four coupled questions; this brief supplies
the evidence for each and leaves the `selection` field `null`:

- **A. Safety metric / admissibility rule** — which signal governs whether a proposed action is
  executed: S1/TS1 absolute worst-node floor, S2/TS2 worst-node degradation, S3/TS3 aggregate-deficit
  increase, or S4/TS4 negative-pressure hard backstop.
- **B. Threshold / tolerance** — which numeric gate (`theta_p` / `eps_p` / `eps_D`) or evidence-supported
  backstop is used. All thresholds here are **swept provisional grids**, never invented or selected.
- **C. Look-ahead horizon** — over how many forward control steps `H` the rule is evaluated
  (characterised at `H ∈ {1,2,4,8,192}` control steps = `{0.5,1,2,4,96}` h).
- **D. Action-handling policy** — on an inadmissible action: reject to previous (H1), clip toward
  previous (H2), or fall back to a reference action (H3).

## 2. Frozen constraints (STEP-9 must NOT modify)

Copied verbatim from the WU-11 reward brief `frozen_constraints`:

- **Action space (D-P6-001/002/003, FROZEN):** `action_dim = 7`; order
  `[VALVE-173, VALVE-175, VALVE-176, VALVE-177, VALVE-178, PUMP-170, PUMP-172]`;
  bounds `173[54.5,100] · 175[21.5,110] · 176[20,59.524] · 177[20,90] · 178[20,74] ·
  PUMP-170[0.82,1.10] · PUMP-172[0.77,1.10]`; encoding `physical = lower + ((a+1)/2)·(upper−lower)`,
  `a ∈ [−1,1]`; excluded valves `{174,179,180}` kept in model; pumps SPEED-only, re-issued each step.
- **Observation (D-P6-004, FROZEN):** `observation_dim = 139`, `float32`.
- **Service-node policy:** 121 service junctions; 5 connector junctions excluded
  (`JUNCTION-105/106/109/110/128`).
- **Reward (D-P6-005, APPROVED 2026-09-27, FROZEN):** `C-A_F1_balanced_dense`, weights
  `w_L=1.0, w_U=1.0, w_P=1.0, w_A=0.1, w_E=0.0`. STEP-9 is an admissibility layer and must NOT change
  reward, observation, or action bounds.
- **Normalisation constants (FROZEN):** `leak_ref=84.72988433677985`, `req_ref=906.3987348621764`,
  `deficit_ref=28.671793365478514`, `power_ref=88.10062475649187`, `movement_L2sq_max=28.0`.
  Verified byte-identical across WU-14 and WU-11 (`source_artifact_integrity.normalization_constants.all_match = true`).

<!-- PLACEHOLDER_DOC -->

## 3. WU-14 evidence — design analysis

Four candidate mechanisms (S1–S4) characterised on a fixed factual schema; **no mechanism
selected/scored/ordered** (WU-14). Governing baseline finding: a **naive absolute 20-psi reject is
ill-posed** — the native baseline already holds ≥1 service node < 20 psi at *every* report instant:

- `n_node_timesteps_below_20psi = 386`, `frac_ts_any_node_below_20psi = 1.0`
- `n_node_timesteps_negative = 0`, `frac_ts_any_node_negative = 0.0`
- `baseline_worst_node_psi = 4.16452 psi`

The leak-only reward's highest-reward tested command sits on the PRV lower corner
(`prv_lower_pump_lower`, `argmax_sits_on_action_bound = true`) with worst-node service pressure
**~1.29 psi** yet **0 negative-pressure nodes**. The only *hard absolute* condition well-posed on
this network is **negative** pressure. Action-space coverage is a single characterised lower corner
(R1b); interior/mixed corners and joint action × uncertain-demand space are **unverified**.

## 4. WU-15 evidence — empirical characterization

Static one-step look-ahead on the frozen network (carries `generated_utc`; EPANET-deterministic).
19 verbatim metric definitions; S1–S4 SAFE-iff rules; **provisional swept grids**
`theta_p ∈ {0,5,10,15,20}`, `eps_p ∈ {0,2,5}`, `eps_D ∈ {0,2,5}`, `H2 alpha ∈ {0,0.25,0.5,0.75,1.0}`.
Handling-policy outputs measured on the reference→severe transition: H1/H3 reject the full-lower
proposal (`action_deviation_L2 = 2.4050194704019527`) to `a_prev` / fallback; `n_extra_hydraulic_evals = 0`
for reject/fallback. Cost: `hydraulic_evals_per_proposed_action_look_ahead = 1`,
`h2_alpha_grid_evals_per_transition = 5`, `n_epanet_solves_total = 10`. Activation counts are
**descriptive** — there is **no validated safe/unsafe oracle**, so they are NOT
false-positive/false-negative rates (7 documented limitations).

## 5. WU-16 evidence — temporal characterization

Look-ahead over `H ∈ {1,2,4,8,192}` control steps (`{0.5,1,2,4,96}` h) on TS1–TS4. **Central
finding — delayed collapse:** on the severe corner the worst-node pressure is
**5.527866840362549 psi at the decision instant** (report index 0) but **collapses to
1.2946763038635254 psi at report index 192 (96 h)** as the tanks drain (`max_N_neg = 0` throughout).

- **TS1 absolute `theta_p=5`** worst-over-window: `5.4615 / 5.4045 / 5.3083 / 5.1472` psi at
  `H=1/2/4/8` (**does NOT activate**) and `1.2947` psi at full (**activates**).
- **TS2 relative `eps_p=0`** activates from `H=1` onward.
- **TS4 negative backstop NEVER activates** on any tested command (`max_N_neg=0`).
- **Identity-hold** reproduces the chronic ill-posedness: absolute `theta_p=20` flags the *unchanged*
  baseline; relative `eps_p=0` never fires on the hold.

## 6. Metric definitions (verbatim, WU-15)

| Metric | Definition | Unit |
|---|---|---|
| `p_min` | `min_i p_i(t)` | psi |
| `dp_min` | `p_min(post) − p_min(current)` | psi |
| `D` | `sum_i max(0, 20 − p_i)` | psi·nodesum |
| `dD` | `D(post) − D(current)` | psi·nodesum |
| `N_neg` | `sum_i I[p_i < 0]` | count |
| `DSR` | `Q_served / Q_req` | ratio |

SAFE-iff rules (True = SAFE = do NOT intervene): **S1** `p_min(post) ≥ theta_p`; **S2**
`p_min(post) − p_min(current) ≥ −eps_p`; **S3** `D(post) − D(current) ≤ eps_D`; **S4** `N_neg(post) == 0`.

## 7. Architectures A–D (fixed factual schema — NOT ordered/scored)

- **A — Immediate Rule (H=0):** evaluate one of S1–S4 at the post-action decision instant.
  1 solve/decision; **blind to the delayed 96-h collapse** (reads 5.53 psi); an absolute floor is
  ill-posed above ~4.16 psi.
- **B — Rolling Short-Horizon Look-Ahead:** TS1 absolute floor over `t+1..t+H`. `H` solves/decision
  (linear; full = 192×). `theta_p=5` misses the severe corner for `H≤8` and fires only at full; the
  well-posed crossover `H` is **untested**.
- **C — Look-Ahead + State-Degradation:** TS2/TS3 relative rule over `H` vs the aligned baseline.
  Baseline-safe; **reacts at H=1** on the tested corner; gives **no absolute floor guarantee**;
  aggregate deficit (S3) can **mask** a localised worst-node collapse.
- **D — Backstop + Temporal:** S4/TS4 negative gate LAYERED with a TS1/TS2/TS3 temporal check. The
  backstop is well-posed but **inert in-range** (never fires above 0 psi); all in-range protection
  comes from the temporal layer, which still needs the A/B/C/D choices.

A machine-readable `decision_matrix` (columns × 4 rows) is included; **rows are NOT ordered or
marked and no metric is aggregated into a single figure.**

## 8. Look-ahead horizon analysis

The metric, threshold well-posedness, and required horizon are **coupled**. An absolute floor needs
a *long* horizon to catch the severe corner but is ill-posed above ~4.16 psi; a relative rule reacts
at *short* horizon but gives no absolute guarantee. **Crossover interval UNTESTED:** under a
well-posed absolute floor, the horizon at which the collapse is first caught lies strictly between
`H=8` (4 h) and full (96 h). No per-index `p_min` series is persisted, so intermediate horizons
(16/24/48/96 steps) are untested. Testing them is a **conditional** design question — required only
if the researcher selects an absolute-threshold look-ahead (B) and wants the smallest sufficient `H`;
a relative architecture (C) already reacts at `H=1` and needs no such test. **This brief mandates no
new experiment.**

## 9. Action-handling policies (H1/H2/H3)

- **H1 reject → previous:** execute `a_prev`; discontinuous; 0 extra solves.
- **H2 clip toward previous:** `a_exec = a_prev + alpha·(a_prop − a_prev)`; continuous (PPO-friendly);
  provisional `alpha` grid `{0,0.25,0.5,0.75,1.0}`; one solve per inspected `alpha`.
- **H3 fallback reference:** execute documented `reference_nominal` native setpoints; discontinuous; 0 extra solves.

Measured outputs copied verbatim from WU-15. **No policy is selected.**

## 10. Baseline compatibility

- **Governing conclusion (WU-14):** a hard absolute 20-psi reject is ill-posed on the native baseline.
- **Per-candidate:** S1 (absolute) flags the baseline at `theta_p ≥ ~4.16` psi; S2/S3 (relative) are
  baseline-safe; S4 (negative) never fires on the baseline.
- **Identity-hold (WU-16):** confirms it empirically — absolute `theta_p=20` activates on the
  *unchanged* baseline; relative `eps_p=0` never does. A hard absolute gate penalises the native
  controller itself.

## 11. Delayed-collapse analysis

On the tested severe corner: **5.527866840362549 psi at the decision instant → 1.2946763038635254
psi at 96 h**. This is single-step non-activation followed by delayed deterioration — **NOT a false
negative** (no safe/unsafe oracle exists). `max_N_neg = 0` across the entire horizon **including** the
1.29-psi collapse, so a negative-pressure backstop (S4/TS4) never fires on any tested command. Tank
drawdown is **coincident** with the collapse; no causal over-claim is made. **Implication:** the
metric (A) and horizon (C) decisions are coupled — an immediate/short-horizon absolute rule cannot
see this collapse; a relative rule flags it early; a long absolute horizon can see it but is ill-posed
above ~4.16 psi and costly.

## 12. Computational implications

- **Immediate (A):** 1 forward EPANET solve/decision.
- **Rolling/temporal (B/C/D temporal layer):** `H` solves/decision, **linear in `H`**, full = 192×
  the single-step cost (`est_wall_s_per_control_step_linear = 0.0013685203125011942`; measured
  full-96 h run = 0.2627559 s).
- **H2 clip:** one extra solve per inspected `alpha`.
- EPANET is deterministic; look-ahead adds **no** stochasticity. Longer horizons buy delayed-collapse
  visibility at proportional per-decision cost. The linear split is an approximation (WU-16 note).

## 13. Training / execution implications

Any intervention (reject H1 / clip H2 / fallback H3) makes the **executed** action differ from the
policy's **proposed** action (WU-15 `action_deviation_L2 = 2.4050194704019527` on the reference→severe
reject). The **FROZEN** reward effort term `||da||²` is defined on the **commanded** action; whether
the effort term and the env transition use the *proposed* or *executed* action under an intervention
is a **training-integration decision COUPLED to the handling policy** — flagged here, **NOT decided**,
and it does not modify the frozen reward. Clip (H2) preserves a continuous action image (PPO-friendly);
reject/fallback (H1/H3) are discontinuous. The safety layer need not be differentiable. All candidates
are compatible with the 30-min control interval.

## 14. Candidate configurations (PROVISIONAL — NOT APPROVED)

Every threshold below is a **swept provisional-grid value** or an **evidence-supported gate**; none is
fitted, ordered, or marked. These populate the decision space; they are not a shortlist.

| Config | Architecture | Metric/rule | Threshold source | Open parameters |
|---|---|---|---|---|
| **K1** backstop+relative | D | S4 negative gate LAYERED with S2/TS2 degradation | negative gate evidence-supported (baseline count 0); `eps_p` grid `{0,2,5}` | `eps_p`, `H`, clip-vs-reject |
| **K2** aggregate-deficit look-ahead | C | S3/TS3 `D(post)−D(base) ≤ eps_D` over window | `eps_D` grid `{0,2,5}` | `eps_D`, `H`, masking risk |
| **K3** immediate well-posed absolute | A | S1 `p_min(post) ≥ theta_p` at instant | `theta_p` grid `{0,5,10,15,20}`, constrained `< ~4.16` psi for well-posedness | `theta_p`, delayed-collapse blindness |
| **K4** rolling absolute look-ahead | B | TS1 `min_[0..H] p_min ≥ theta_p` | `theta_p` grid `{0,5,10,15,20}` | `theta_p`, `H` (crossover untested), clip-vs-reject |

All four carry `status = "PROVISIONAL CANDIDATE - NOT APPROVED"`.

## 15. Uncertainties

1. **No validated safe/unsafe oracle** — activation counts are descriptive, not FP/FN rates.
2. **R1b coverage** — only the single lower corner has measured near-collapse; interior/mixed corners
   and joint action × uncertain-demand space are uncharacterised.
3. **Crossover onset untested** — well-posed absolute-floor onset lies between `H=8` (4 h) and full (96 h).
4. **Sustained deltas include tank-trajectory divergence** — only report index 0 is a pure one-step
   command-effect look-ahead.
5. **H2 `alpha` grid is coarse** and demonstrated on one transition only.
6. **Leakage instrument is not field-calibrated** — internally consistent evidence, not calibrated predictions.
7. **Effort-term action under intervention** is an open training-integration question coupled to D.
8. **Thresholds encode a value judgement** — the leakage↔service↔safety exchange rate is the
   researcher's, not a measured quantity.

## 16. Coverage limits

Characterised horizons: `{1,2,4,8,192}` control steps. Intermediate horizons `{16,24,48,96}`
**untested**. No safe/unsafe oracle; thresholds swept, not selected. Characterised region = single
lower corner (R1b); joint 5-D in-box space and uncertain-demand realisations are a later STEP-9/STEP-12 job.

## 17. Researcher decision block (BLANK — to be completed by the researcher)

STEP-9 remains `PROPOSED / PENDING RESEARCHER`; the project is **NOT PPO-ready**. The researcher makes
the STEP-9 selection; this brief selects nothing.

| Decision | Selection |
|---|---|
| A — architecture (A/B/C/D or composition) | ☐ _____________ |
| B — safety metric / rule | ☐ _____________ |
| C — threshold (`theta_p` / `eps_p` / `eps_D` / gate) | ☐ _____________ |
| D — look-ahead horizon `H` | ☐ _____________ |
| E — action-handling policy (H1/H2/H3, `alpha`) | ☐ _____________ |
| F — effort-term action under intervention (proposed vs executed) | ☐ _____________ |
| G — rationale / evidence cited | ☐ _____________ |

Once completed, record the decision in
[PHASE6_DECISION_REGISTER.md](PHASE6_DECISION_REGISTER.md) (a new `D-P6-006`), update
`PROJECT_STATE.yaml`, and only then proceed to the STEP-9 wrapper implementation and PPO readiness.

