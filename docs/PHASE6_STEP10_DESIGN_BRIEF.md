# PHASE6_STEP10_DESIGN_BRIEF.md — Demand Uncertainty, Scenario Separation & Evaluation Protocol

**Status: DECISION-READY — PROPOSED, NOT APPROVED. Nothing in this document is a
scientific decision until the researcher completes §10.**
Prepared 2026-10-15. Register ID: **D-P6-007** (next free ID after D-P6-000a/b,
D-P6-001 … D-P6-006). A focused methodology review (2026-10-19) added two clearly
labelled **[RECOMMENDED for consideration]** addenda — evaluation-episode
determinism (§5 D5) and training-scenario presentation (§5 D4) — plus one
`D4_training_presentation` field in the §10 form. They are **recommendations
awaiting researcher selection, not approvals**; every other line of this brief is
unchanged.

This brief exists because STEP 10 is the last *design* layer before scientific PPO
training. Every value below marked **[PROPOSED]** is a candidate, not a decision.
No code implementing a demand-scenario model has been written, and no code will be
until §10 is signed.

---

## 1. Decision context (reconstructed from disk, not from chat)

| Fact | Evidence (verified on disk) |
|---|---|
| STEP 10 status is **NOT STARTED** | `PROJECT_STATE.yaml` `phase6.steps.step10_demand_uncertainty_and_splits: {status: "NOT STARTED"}`; `demand_uncertainty.status: "NOT STARTED (step10)"` |
| `src/env/demand_scenarios.py` does not exist | directory listing of `src/env/` (9 modules, none is the scenario module) |
| The environment is fully deterministic | `bwsn_env.reset(seed=...)` calls `gym.Env.reset` only; it seeds nothing stochastic because nothing stochastic exists |
| No split, scenario ID, or seed policy exists | absent from `src/env/`, `experiments/ppo/`, `tests/` |
| Baseline comparison is **interface only** | `src/env/baselines.py` defines action masks (`native`/`prv_only`/`vsp_only`/`joint`); it is imported **only** by `tests/test_baselines.py` and is deliberately not wired into `step()` |
| Evaluation exists but is PPO-only | `experiments/ppo/evaluate.py` loads one SB3 model and rolls it out; it has no baseline mode and no multi-scenario driver |
| The hydraulic demand path is native-pattern only | `epanet_adapter.SteppingHydraulicDriver._build_segment` sets `pattern_start`; `reset()` computes the requested-demand series once via `wntr.metrics.expected_demand(wn_full)` |
| WNTR 1.5.0 exposes the needed hooks | `wn.options.hydraulic.demand_multiplier`, per-junction `demand_timeseries_list` / `base_demand` (introspected read-only) |

## 2. Frozen constraints STEP 10 must not violate

Hydraulics / episode: BWSN-1; WNTR 1.5.0 / EPANET 2.2; accuracy `1e-5`; trials
`2000`; rule timestep `180 s`; control/report `1800 s`; 96 h; **192** transitions;
**193** report instants; PDA (20 psi required / 0 psi minimum / exponent 0.5);
native rules, pump-status controls, topology, service mask, leak instrument and the
working INP all preserved.

Observation (D-P6-004): **139** float32 dimensions, fixed order, **no future
demand**, fixed physical normalisation, time-of-day sin/cos over **24 h**.

Action (D-P6-001/002/003): 7 normalised dims in the order
`[VALVE-173, VALVE-175, VALVE-176, VALVE-177, VALVE-178, PUMP-170, PUMP-172]`
with the approved bounds (`173 [54.5,100]`, `175 [21.5,110]`, `176 [20,59.524]`,
`177 [20,90]`, `178 [20,74]` psi; `170 [0.82,1.10]`, `172 [0.77,1.10]`).

Reward / safety: D-P6-005 `C-A_F1_balanced_dense`; D-P6-006 architecture F1
(`N_neg == 0` backstop + relative worst-node-vs-HOLD guard, `ε_p = 0`, `H = 1`).
Reward weights, normalisers, safety code and wrapper are out of scope for STEP 10.

Baseline reference (frozen anchors, leak instrument is a **model-based research
instrument, not field-calibrated leakage**): mean leakage `84.72988433677985` GPM;
min service pressure `4.16452169418335` psi at JUNCTION-29; **0** negative-pressure
node-instants; mean DSR `0.9833370137001072`. The baseline is **chronically below
20 psi**, so no absolute 20-psi guarantee may be introduced and pre-existing sub-20
observations must not be attributed to the agent.

## 3. Measured evidence that constrains the design

### 3.1 The demand pattern is 48 h, the observation is 24 h

Measured from the working INP (read-only):

* `[TIMES] Pattern Timestep 0:30`, `Duration 96:00`; **PATTERN-0 has 96 multipliers
  → 48 h**, so it repeats **exactly twice** per episode.
* PATTERN-0 is the `[OPTIONS] Pattern` default and drives **~124 of 126 junctions**
  (77 explicit in `[JUNCTIONS]`, 47 defaulted, 2 use PATTERN-1; `[DEMANDS]` adds
  3 + 3).
* The two 24 h halves are **not identical**: **46 of 48** slots differ, max |Δ| =
  **1.17**, **day-1 mean 0.7327 vs day-2 mean 1.0385** (~42 % apart).
* The observation encodes only **24 h** sin/cos, so hour *h* on day 1 and on day 3
  are **aliased** while facing systematically different demand.

**Classification: confirmed implementation fact; existing partial-observability
limitation, not a defect.** The environment is already documented as a POMDP
(D-P6-004). Resolving it by changing the temporal features would reopen a frozen
decision and is **not** proposed here (§5, D5).

### 3.2 What a scenario must perturb, mechanically

`reset()` snapshots tank levels and pump statuses, then computes the requested
series **once** on a `pattern_start=0` model with `expected_demand(wn_full)`. Each
control step rebuilds a fresh segment from the working copy and sets
`pattern_start = t_elapsed`. Consequences for any design:

1. A perturbation applied only to the segment models would leave the **requested**
   series (and therefore DSR and unserved demand) unperturbed → **silently wrong
   accounting**. The perturbation must reach `wn_full` too.
2. Because every segment is rebuilt from the WORKING COPY, the perturbation must be
   a **pure deterministic function of (scenario_id, junction, absolute time)** —
   otherwise the demand sequence resets or jumps at segment boundaries.
3. `pattern_start` advances with `t_elapsed`; scenario application must use the same
   absolute clock so the 48 h pattern phase is preserved.

### 3.3 The closest prior work already in the project record

`docs/phase4_decision_report.md` records (as FACT, quoting the paper) that
Hu, Gao & Zhong (2023), *Water Supply* 23(7):2833, doi 10.2166/ws.2023.163, used
demand-uncertainty multipliers *"following a truncated normal distribution with a
range from 0.7 to 1.3"* on EPANET Net3. That is the **only** demand-uncertainty
range with any project-record precedent. It is a **design precedent from one paper
on a different network** — it is *not* evidence about BWSN-1 field demand, and no
claim to that effect will be made.

## 4. Open decisions (all five are unresolved on disk)

| ID | Decision | Why it is scientific, not engineering |
|---|---|---|
| **D1** | Uncertainty **family / temporal structure** | Determines what the agent must actually adapt to; a per-episode level shift is a different problem from per-step noise |
| **D2** | **Magnitude / distribution** of the perturbation | Sets the tested operating envelope; too wide and the reference hydraulics become unrepresentative, too narrow and "uncertainty" is cosmetic |
| **D3** | **Spatial structure** (one global factor vs per-junction) | Changes whether uncertainty is a level shift or spatially heterogeneous |
| **D4** | **Split** (train / validation / test / OOD) and **seed / scenario-ID policy** | Determines whether reported performance is generalisation or interpolation; leakage here invalidates every later claim |
| **D5** | **Baseline & evaluation protocol** (what is trained, what is fixed, how many episodes, what is primary) | Determines whether the comparison answers the thesis question fairly |

## 5. Candidate options — definitional order, not ranked, not scored

> No option is preferred, ranked, or scored here. The alternatives are listed so the
> researcher can choose. Escape hatches are stated explicitly.

### D1 — Temporal structure of the perturbation

| Option | Definition | What it tests | Main drawback |
|---|---|---|---|
| **U1 — persistent per-episode factor** | One multiplier per junction (or one global), drawn once per episode, held constant over all 96 h | Adaptation to a *different demand level* — closest to "the network serves a different day than the one calibrated" | The agent only has to re-learn a level; the diurnal shape is untouched |
| **U2 — per-control-step factor** | A new multiplier every 30 min (independent draws or a smooth process) | Adaptation to *transient* demand variation | White noise at 30 min is not physical demand behaviour; a smooth (e.g. AR(1)) process would be needed and adds a second assumption |
| **U3 — diurnal-shape perturbation** | Shift/scale the 48 h pattern (e.g. time shift ±Δ, amplitude scale) while preserving its shape | Adaptation to a *different daily profile* — the most realistic reading of "uncertain demand" | Two extra parameters (shift, scale); interacts with the 24 h/48 h aliasing in §3.1 |

**[PROPOSED for consideration]** U1 as the minimal design that is unambiguously
"demand uncertainty" and requires no extra temporal-process assumption. U3 is the
scientifically richer alternative; U2 is the easiest to implement and the easiest
to criticise as unrealistically white.

### D2 — Magnitude and distribution

| Option | Definition |
|---|---|
| **M1 — truncated normal [0.7, 1.3], μ = 1.0, σ = 0.1** | The only range with project-record precedent (Hu et al. 2023, Net3). **[PROPOSED]** |
| **M2 — truncated normal [0.8, 1.2], σ = 0.05** | Narrower envelope; keeps the simulation closer to the calibrated anchor |
| **M3 — uniform [0.7, 1.3]** | Same support, no central tendency; simpler to state, weaker justification |

**All three are engineering choices.** None is claimed to represent a measured
BWSN-1 demand distribution. The choice must be written into the thesis as an
assumption, not as a calibrated fact.

### D3 — Spatial structure

| Option | Definition | Consequence |
|---|---|---|
| **S1 — one global factor** | Same multiplier for every junction at a given time | Cleanest; the whole network sees the same demand level |
| **S2 — per-junction i.i.d.** | Independent draw per junction | Spatially heterogeneous; more realistic in principle, but i.i.d. independence across 126 junctions is itself an unverified assumption |
| **S3 — spatially smooth** | Correlated field (e.g. one factor per hydraulic zone) | Most realistic; requires a zone definition that does not exist in the project and would be a **new** assumption |

**[PROPOSED for consideration]** S1 for the training family (minimal, defensible),
with S2 explicitly **excluded** from the training distribution and used only as an
OOD family if the researcher wants spatial generalisation tested (§7).

### D4 — Split and seed policy

Proposed structure (**all counts and proportions are [PROPOSED], not approved**):

| Group | Purpose | Scenario composition [PROPOSED] | Rule |
|---|---|---|---|
| **N-native** | Anchor reproducibility | 1 scenario, `scenario_id = "native"` | Exact native pattern; must reproduce the frozen anchors |
| **T-train** | PPO training | 8 scenarios | U1 + M1 + S1, seeds `train/0…7` |
| **V-validation** | Checkpoint selection, hyper-parameter decisions | 4 scenarios | **Same family and range as train**, disjoint seeds |
| **E-test** | Final reported performance | 4 scenarios | **Same family and range as train**, seeds never used in V or T |
| **O-OOD** | Robustness only, reported separately | 2 scenarios | Outside the training envelope (e.g. M2-extreme or S2), **never used for selection** |

Rules that make the split meaningful (these are protocol, not parameter choices):

1. **Disjointness by construction**: a scenario is identified by
   `scenario_id = "<family>/<index>"` and its seed is derived from a master seed via
   `numpy.random.SeedSequence(master).spawn(...)`, so no two groups can collide.
2. **Identical ranges are not independence.** Train / validation / test share the
   same family **on purpose** (so test measures in-distribution generalisation, not
   extrapolation). Separation comes from disjoint seeds *and* from never reusing a
   realised multiplier vector.
3. **Test is written once, never read during training or selection.** Checkpoint
   selection uses validation only.
4. **OOD is reported separately and never blended into the primary result.**
5. `env.reset(seed=...)` seeds **only** the scenario sampler; hydraulics remain
   deterministic. Seed → scenario is recorded in run metadata.

> **Review addendum (2026-10-19, focused methodology review — RECOMMENDATION ONLY,
> not a decision; D-P6-007 remains PROPOSED): training-scenario presentation.**
> The T-train row above describes training on **eight fixed, enumerated demand
> realisations**. Note the dimension of what is being sampled: under the proposed
> U1 + S1 combination each realisation is **one persistent global scalar
> multiplier** in [0.7, 1.3] held for 96 h, so eight enumerated training scenarios
> sample a 1-D interval at 8 points and the policy cycles over the same eight
> episodes for the entire run. Two coherent presentations exist, and the seeded
> scenario generator (§9.2 acceptance criteria) is required by **both**, so the
> marginal implementation cost of Option B is near zero:
>
> | | Option A — fixed enumerated training set | Option B — per-episode seeded sampling (eval sets stay fixed) |
> |---|---|---|
> | What it is | Train only on `train/0..7` (8 fixed draws), cycled | Each training episode draws a fresh U1+S1 multiplier from a seeded RNG stream; V / E / OOD remain the fixed, disjoint IDs above |
> | Establishes | Exact replay of the precise training sequence; trivially auditable | Exposure to the continuous in-family distribution (standard domain-randomisation practice) |
> | Does NOT establish | Distribution-level coverage during training; no guard against memorising 8 specific scalars | Replay of the exact draw *sequence* (rather than the family) depends on the recorded RNG stream |
> | Principal risk | Overfitting to 8 specific multipliers; test-set drop attributable to narrow training coverage | Slightly weaker "which scenarios were seen" audit trail (mitigated by logging every drawn multiplier) |
> | Added cost | Baseline | ≈ zero code delta (same module, same per-step compute); requires per-draw logging |
>
> **[RECOMMENDED for consideration]** Option B: the generator exists under either
> option, the cost delta is near zero, and it converts the 8-point coverage risk
> into standard in-family domain randomisation while the fixed, disjoint
> validation / test / OOD IDs keep selection and reporting paired and reproducible.
> Option A remains fully defensible if exact enumerated replay is valued above
> coverage. **This is a recommendation awaiting researcher selection, not an
> approval.**

### D5 — Baseline and evaluation protocol

**Distinction that must be preserved** (it is the easiest thing to get wrong):

| Condition | What it is | Needs training? |
|---|---|---|
| `native` | The fixed native operating point (nominal PRV setpoints, pump speed 1.0), re-issued every step. This is the **frozen hydraulic baseline**, not a controller. | **No** |
| safety-HOLD | The **previous executed action** re-issued — a dynamic reference inside D-P6-006, not a baseline on its own | No |
| `prv_only` | A PPO policy **trained with only the five PRV dims free** (pump dims masked to native) | **Yes — a separate policy** |
| `vsp_only` | A PPO policy **trained with only the two pump dims free** | **Yes — a separate policy** |
| `joint` | The PPO policy with all seven dims free | **Yes** |

`src/env/baselines.py` provides the **mask**, not the policy. Applying the `prv_only`
mask to a `joint`-trained policy is **not** the `prv_only` condition and must not be
reported as one.

Proposed evaluation rules (**[PROPOSED]**):
* Every condition is evaluated on the **same** scenario IDs (paired design), with the
  same seeds and the same episode length, so differences are attributable to control.
* Deterministic rollouts; **K = 3** evaluation episodes per (condition, scenario) is
  the proposed minimum, reported per episode **and** aggregated per scenario.
  > **Review addendum (2026-10-19 — determinism clarification, RECOMMENDATION ONLY):**
  > as implemented, the environment contains **no stochastic element**: `reset(seed=...)`
  > seeds nothing the dynamics consume, EPANET runs the same deterministic solve every
  > time, and the evaluator uses `model.predict(deterministic=True)` (documented
  > behaviour in `experiments/ppo/evaluate.py`). Therefore, once the scenario model is
  > implemented per §9.2, a fixed `scenario_id` fully determines the demand series and
  > thus the whole trajectory: **K > 1 episodes on the same (condition, scenario) would
  > be deterministic duplicates** — same actions, same hydraulics, same metrics, exact
  > re-runs. This is the intended determinism (acceptance criterion §9.2: "same seed +
  > same config ⇒ byte-identical scenario data") — but it means the repetitions
  > supply **no independent statistical evidence** in the deterministic-evaluation
  > setting.
  >
  >  **What the repetition axes actually are:**
  >
  >  | Axis | Source of variation | Effect on results |
  >  |---|---|---|
  >  | Training seed | PPO initialisation + action-sampling noise during training | **Independent** trained policies → the genuine seed-to-seed variation axis |
  >  | Scenario ID | Distinct multi-factor draw (family, magnitude, spatial) | **Independent demand conditions** → the generalisation axis |
  >  | Evaluation episodes (K) | None, under deterministic rollouts on a fixed scenario | **Exact duplicates** — useful only as a determinism check |
  >
  > **[RECOMMENDED for consideration]:** treat **K = 1 deterministic episode per
  > (condition, scenario)** as the default reporting unit, with K = 3 retained only as
  > an **explicit determinism check** (report identical-metrics status, not
  > mean ± spread); derive any mean ± spread across **scenarios** (and, if used,
  > across training seeds), never across duplicated episodes. If the researcher later
  > selects stochastic policy rollouts (`deterministic=False`) or a temporally
  > stochastic demand family (U2/U3), K > 1 becomes genuinely informative and this
  > recommendation should be revisited. No change to the paired-scenario design.
* **Checkpoint selection on validation scenarios only**; the test set is evaluated once.
* **No composite score.** Report separately: mean modelled leakage, DSR, unserved
  demand, minimum service pressure, negative-pressure instants, pressure deficit,
  cumulative reward (labelled as reward), safety outcome counts / acceptance rate,
  and wall-clock cost.
* **Primary outcome**: mean modelled leakage. **Hard reporting constraint**: a lower
  leakage accompanied by worse DSR / deficit / negative-pressure behaviour is
  reported as a failure of the condition, not as a win.
* Failures (solver failure, incomplete episode, exception) are reported as failures
  with the scenario and seed, never silently dropped.

## 6. The 48 h / 24 h observation aliasing — explicit handling

Three options, none of which changes a frozen decision:

1. **Accept and document** (§3.1) as a known POMDP limitation. **[PROPOSED]**
2. **Quantify it** with a read-only diagnostic (no training): measure how much the
   observed tank levels and pressures already disambiguate hour *h* on day 1 from
   hour *h* on day 3 along the native trajectory. This is *analysis*, not a design
   change, and can be done before or after approval.
3. **Modify the observation** (e.g. 48 h encode) — **requires reopening D-P6-004**;
   not proposed in STEP 10.

## 7. Scope conflict recorded (narrow, unresolved)

The D-P6-006 register mandates the `ε_p` / `H` sensitivity sweep as a **STEP-12**
activity:

> "**Mandated STEP-12 sweep ε_p ∈ {0, 2, 5} psi.**"
> "**Mandated STEP-12 sweep**" (for `H`)

The `docs/RECOVERY.md` banner lists the same sweep under **STEP-10**. **The register
is authoritative; the sweep is STEP-12.** STEP 10 will **not** run the 12-cell
sweep. The RECOVERY wording is left unchanged in this brief and is flagged for
correction at the next persistence update so the two records agree.

## 8. Expected consequences of the alternatives (summary)

| Choice | If U1 + S1 (persistent, global) | If U2 (per-step) | If U3 (shape shift) |
|---|---|---|---|
| Learning difficulty | Moderate: the agent must infer a level shift from pressures/tanks | High: no demand observation plus fast noise | Moderate–high: the diurnal prior in the observation is now misleading |
| Comparability to Hu et al. (2023) | Close (same family) | Not comparable | Not comparable |
| Risk of an unfair baseline | Low — native is unaffected | Low | Low |
| Risk to the frozen anchors | None if `scenario_id="native"` bypasses perturbation | Same | Same |

## 9. Acceptance criteria for STEP-10 implementation (after approval)

STEP 10 is complete only when **all** of the following hold:

1. `src/env/demand_scenarios.py` exists and the `native` scenario reproduces the
   native demand pattern **exactly** (verified against the working INP).
2. Same seed + same config ⇒ byte-identical scenario data (determinism test).
3. Train / validation / test / OOD allocations are disjoint and reproducible from
   recorded metadata (split-integrity test).
4. The perturbed demand reaches **both** the segment models **and** the requested
   series used by DSR / unserved accounting (no silent accounting drift).
5. The **native** scenario still reproduces the frozen hydraulic anchors
   (leak 84.72988… GPL, min 4.16452…, 0 negative) through real EPANET.
6. Observation stays **exactly 139** dims and contains no future demand.
7. Action dim / order / bounds unchanged.
8. The baseline harness evaluates `native` and the trained conditions on **identical
   scenario IDs**, with metrics reported separately.
9. No PPO scientific training is implied by any of the above.

## 10. Researcher decision form — SELECTIONS RECORDED 2026-10-19

The selections below were communicated by the researcher in their 2026-10-19
STEP-10 implementation directive (the directive that authorised implementing
`src/env/demand_scenarios.py` and the integration). They are recorded here as
received, with truthful provenance: the directive selected the parameters and
instructed recording them; it is an implementation-authorising selection, not a
separately signed "APPROVED & FROZEN" act in the sense of D-P6-001..006. The
D-P6-007 register entry remains the authority on status.

```yaml
D-P6-007:
  researcher_selection: "selected via 2026-10-19 implementation directive (see header note)"
  D1_temporal_structure: "U1"         # one multiplier per 96 h episode (persistent)
  D2_distribution: "M1"               # exact truncated normal (inverse-CDF), NOT clipped
  D2_parameters:
    family: "truncated_normal"
    lower: 0.7
    upper: 1.3
    mu: 1.0
    sigma: 0.1                        # a=-3, b=3 in sigma units; analytic std 0.0986578
  D3_spatial_structure: "S1 (train + in-distribution eval); S2 (OOD only)"
  D4_policy:
    scenarios_train: "unbounded stream — NEW draw per episode reset (B), never a cycled fixed set"
    scenarios_validation: 4           # val/0..3, U1+M1+S1, fixed reproducible
    scenarios_test: 4                 # test/0..3, U1+M1+S1, fixed reproducible
    scenarios_ood: 2                  # ood/0..1, U1+M1+S2 (independent per-junction factors)
    ood_definition: "S2: per-junction i.i.d. truncated-normal factors over the 79 demand junctions (spatial heterogeneity unseen in training)"
    master_seed: 20261019             # SpawnSequence keys: train=0, val=1, test=2, ood=3
    test_written_once: true
  D5_evaluation:
    episodes_per_condition_per_scenario: 1    # K=1 + explicit determinism check (deterministic rollouts make K>1 duplicates)
    checkpoint_selection_split: "validation"   # fixed by protocol; change only with reason
    primary_outcome: "mean_modelled_leakage"   # fixed by protocol; change only with reason
    paired_scenario_ids_across_conditions: true
  D4_training_presentation: "B_seeded_per_episode_sampling"
  D6_48h_24h_handling: "accept_and_document"
  D7_sweep_stage_confirmation: "sweep is STEP-12 (register)"
  additional_selections:
    training_seeds: "3 seeds for the final Colab evaluation (planned; not part of the 2026-10-19 implementation)"
    scenario_logging: "scenario id + multiplier logged EVERY training episode (env/scenario_id, env/scenario_multiplier)"
  rationale: "Researcher directive of 2026-10-19: smallest uncertainty layer consistent with the approved scope — persistent global multipliers (U1+S1) for training and in-distribution evaluation, spatially heterogeneous S2 reserved for OOD reporting; exact truncated normal per the M1 range precedent; disjoint SeedSequence streams guarantee train/eval separation with no leakage."
  decision_date: "2026-10-19 (selections communicated); implementation recorded same date"
  approved_by: "researcher (selection + implementation authorisation via directive; register retains status authority)"
```

## 11. Provenance and non-claims

* Every measured number in §3 comes from read-only inspection of
  `data/networks/working/BWSN_Network_1_working.inp` and `src/env/*`.
* The only external source cited is the one already recorded in
  `docs/phase4_decision_report.md` (Hu, Gao & Zhong 2023, *Water Supply* 23(7):2833,
  doi 10.2166/ws.2023.163). No new citation is introduced.
* No option in this brief is approved, preferred, ranked or scored.
* No frozen decision (D-P6-001 … D-P6-006) is reopened or modified.
* This document does not execute STEP 10 and makes no performance claim.
