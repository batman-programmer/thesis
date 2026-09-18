# PROJECT_CONTEXT.md

Complete technical and scientific context. Exact values, equations, names and
configurations are preserved verbatim wherever they were available.

Every statement carries a label. See [INDEX.md](INDEX.md) for the label
convention.

---

## 1. Identity and purpose

| Field | Value | Label |
|---|---|---|
| Thesis title | *Adaptive Pressure Control in Water Distribution Networks Using Deep Reinforcement Learning (DRL/PPO) Integrated with EPANET to Reduce Leakage Under Uncertain Demand* | `USER_PROVIDED` |
| Degree | Master's | `USER_PROVIDED` |
| Field | Industrial Engineering | `USER_PROVIDED` |
| Working directory | `D:\Thesis` | `DIRECT_OBSERVATION` |
| Git repository | yes, branch `main`, 3 commits (`d921024` "10-06-1405", `abd0ec6` "02-06-1405", `5455046` "Create README.md") | `DIRECT_OBSERVATION` |
| Language of work | Persian and English mixed; reports written in English | `DIRECT_OBSERVATION` |

**Purpose (`USER_PROVIDED`).** Reduce background leakage in a water
distribution network by learning a control policy that continuously adjusts
pressure-control actuators, while maintaining customer service pressure, under
demand the controller cannot predict.

**Approved-scope anchors (`USER_PROVIDED`).** `D:\Thesis\proposal\proposal.pdf`
and `D:\Thesis\seminar\seminar.pdf` are mandatory project constraints defining
approved scope, terminology, objectives and commitments. Per `CLAUDE.md` §1 they
are binding *but not assumed scientifically infallible*: where they contain an
error, the smallest scientifically sound correction that preserves the approved
direction is preferred, and a major correction must be surfaced to the
researcher, never applied silently.

---

## 2. Research questions

`INFERENCE` — these are reconstructed from the phase reports and the novelty
audit. `docs/research_questions.md` exists but is **0 bytes**, so the canonical
statement lives only in the proposal PDF (not machine-read during this backup).

1. Can a PPO agent, acting on PRV setpoints and variable-speed pump speeds,
   reduce background leakage on a public benchmark network relative to native
   control and to classical optimisation baselines, at a matched service-violation
   budget?
2. How much of that benefit comes from *control* rather than from valve
   *placement*? (novelty claim N11)
3. What is the marginal contribution of variable-speed pump operation given
   coordinated PRV control? (N6 — the PRV-only / VSP-only / joint ablation)
4. Does the policy hold up out of distribution — demand outside the training
   distribution (N7), and model-parameter error to a declared 10 % bound (N8),
   separately and jointly?
5. Does the choice of pressure-driven (PDA) versus demand-driven (DDA) analysis
   change the learned policy and the reported leakage? (N9)

---

## 3. Hypotheses

| ID | Hypothesis | Label |
|---|---|---|
| H1 | A learned continuous policy outperforms a static optimised setting vector under stochastic demand, because it can react to state the static vector cannot see. | `HYPOTHESIS` |
| H2 | Joint PRV + VSP control outperforms either alone by a measurable margin. | `HYPOTHESIS` (this is N6; the ablation is the test) |
| H3 | Robustness to out-of-distribution demand is *not* implied by in-distribution performance. | `HYPOTHESIS` (motivates N7) |
| H4 | A scalarised reward hides the trade-off; a constraint-matched comparison changes the ranking of methods. | `HYPOTHESIS` (motivates N10) |
| H5 | Some of the leakage reduction reported in prior work is attributable to optimised valve placement rather than to the controller. | `HYPOTHESIS` (motivates N11) |
| H6 | The 1.38 % residual pump override does not materially damage PPO's credit assignment. | `HYPOTHESIS TO TEST` — explicitly deferred past Phase 6 |

---

## 4. Scope and boundaries

**In scope (`DECISION`).** BWSN-1 as the primary network; PRV setpoint and pump
speed control; background leakage via emitters; PDA; demand uncertainty and
model-parameter uncertainty as two separate axes; PPO single agent; four
baselines plus an optional oracle; multi-seed reporting.

**Explicitly out of scope (`DECISION`).**

- Leak *detection* or *localisation*. This is a control thesis.
- Topology optimisation, pipe sizing, network design.
- Re-running PRV *placement* optimisation against the thesis reward on the
  primary network — that is the co-optimisation bias documented in Phase 4 §7 and
  it invalidates the headline claim.
- Contamination / water-quality objectives (BWSN's original purpose).
- Real-world field deployment.

**Hard prohibitions currently in force (`USER_PROVIDED`, Phase 6 brief).**

| Prohibition | Verbatim |
|---|---|
| No PPO science yet | «در این Phase به هیچ عنوان هنوز آزمایش علمی PPO انجام نده» |
| Solver settings must not fall back to WNTR defaults | «این تنظیمات نباید به defaultهای WNTR واگذار شوند» |
| Benchmark and actuator topology must not change | «اصل benchmark topology و actuator topology نباید تغییر کند» |
| No silent rule removal | «Silent rule removal ممنوع است» |
| Do not drop inactive PRVs without investigation | «آنها را بدون بررسی حذف نکن» |
| No unconstrained action on VALVE-179 | "DO NOT expose unconstrained continuous action over VALVE-179" |
| No arbitrary actuator bounds | "DO NOT choose arbitrary actuator bounds" |
| No future information in observation or action mapping | «هیچ future information نباید وارد observation یا action mapping شود» |
| Never mix the four decision labels | «هیچ کدام را با هم مخلوط نکن» |

---

## 5. Methodology and architecture

### 5.1 Simulation stack

| Component | Version | Label |
|---|---|---|
| Python | 3.13.15 (`D:\Thesis\.venv`) | `VERIFIED_FACT` |
| WNTR | 1.5.0 | `VERIFIED_FACT` |
| EPANET | 2.2, DLL version reported as 20200, driven via `wntr.sim.EpanetSimulator` | `VERIFIED_FACT` |
| EPyT | 2.3.5.2, wrapping EPANET 2.3.05 | `VERIFIED_FACT` — a **different engine**; never cross-validated against WNTR in this project |
| numpy / pandas / scipy | 2.5.2 / 3.0.5 / 1.18.1 | `VERIFIED_FACT` |
| `gymnasium`, `stable-baselines3`, `torch` | **ABSENT** | `VERIFIED_FACT` — must be installed before Phase 6 STEP 11 |

A separate system Python 3.14 exists at `C:\Python314` and is **not** the
project interpreter (`DIRECT_OBSERVATION`).

### 5.2 Planned RL architecture

`PLANNED` — module layout mandated by Phase 6 brief §27, with the instruction
«از overengineering پرهیز کن» (avoid overengineering):

```
src/env/
├── bwsn_env.py          Gymnasium Env: reset/step/render/close
├── epanet_adapter.py    stepped EPS, 3-part carry-forward, solver assertion
├── state_builder.py      observation vector + frozen normalisation
├── action_mapper.py      normalised action -> physical setpoints, bounds, rate limits
├── safety.py             hard constraints; NOT delegated to reward
├── reward.py             the four weighted terms
├── demand_scenarios.py   scenario generation, seeds, scenario IDs
└── metrics.py            leakage, violations, DSR, energy, movement
```

`epanet_adapter.py` should be built on the validated stepped harness already in
`src/validation/p6_s4_pump_strategy.py` — that code is the measurement that
proved the stepping mechanism reproduces a monolithic run.

### 5.3 Control loop timing

| Quantity | Value | Label |
|---|---|---|
| EPS duration | 96 h | `VERIFIED_FACT` (file `Duration 96:00`) |
| Hydraulic timestep | 30 min (`0:30`) | `VERIFIED_FACT` |
| Native rule timestep | 180 s (file-declared; WNTR defaults to 360 s) | `VERIFIED_FACT` |
| RL control / report timestep | 1800 s | `DECISION` |
| Control steps per episode | 192 | `VERIFIED_FACT` (96 h / 0.5 h) |
| Intra-step rule evaluation | rules fire at 180 s inside each 1800 s control step | `VERIFIED_FACT` |

---

## 6. The network

### 6.1 Files

| Path | Role | Label |
|---|---|---|
| `data/networks/BWSN_Network_1.inp` | Original benchmark. **Never edited.** | `VERIFIED_FACT` |
| `data/networks/working/BWSN_Network_1_working.inp` | Working copy, rebuilt by code | `VERIFIED_FACT` |
| `results/phase5/working_copy_provenance.json` | Provenance record of the copy | `DIRECT_OBSERVATION` |

**The only patch applied to the working copy (`VERIFIED_FACT`):**
`Quality Chemical TIME` → `Quality Chemical mg/L`.

### 6.2 Composition — frozen, verified from the `.inp`

`VERIFIED_FACT`: 126 junctions · 1 reservoir · 2 tanks · 168 pipes · 2 pumps ·
8 PRVs · 4 `[RULES]` · Duration 96:00 @ 0:30 · GPM / psi / ft ·
Hazen-Williams.

**«Topological modifications are forbidden unless separately justified and
explicitly approved.»**

### 6.3 The 8 PRVs

`VERIFIED_FACT` — nominal settings and nominal solved states:

| PRV | Nominal setting (psi) | Nominal state | RL-controlled? |
|---|---|---|---|
| VALVE-173 | 70 | Active | **Yes** |
| VALVE-174 | 80 | Closed (hydraulic) | No |
| VALVE-175 | 55 | Active | **Yes** |
| VALVE-176 | 29.762 | Active | **Yes** |
| VALVE-177 | 45 | Active | **Yes** |
| VALVE-178 | 37 | Active | **Yes** |
| VALVE-179 | 40 | Closed (hydraulic) | No |
| VALVE-180 | 16.45 | Closed by `[CONTROLS]` | No |

`[CONTROLS]` closes VALVE-180 at time 0, so 7 of 8 are notionally active at
t = 0 (`VERIFIED_FACT`).

**Exclusion reasons — each measured, see FINDINGS.md F-11/F-12/F-13.** No PRV is
deleted from the model.

### 6.4 The 2 pumps

`VERIFIED_FACT`:

| Pump | Head curve | Tank rule | Measured shut-off speed |
|---|---|---|---|
| PUMP-170 | CURVE-0 | TANK-131: open ≤ 15.4 ft, closed ≥ 18.4 ft | **0.8152** |
| PUMP-172 | CURVE-2 | TANK-130: open ≤ 12.1 ft, closed ≥ 16.0 ft | **0.7655** |

`CURVE-1` is present in the file but referenced by nothing (`VERIFIED_FACT`).
`[ENERGY]`: Global Efficiency 75 %, Global Price 0 (`VERIFIED_FACT`) — a price
must be chosen to report cost, and that choice is an assumption to be reported.

### 6.5 Demand patterns — as shipped

`VERIFIED_FACT` (Phase 5 discrepancy D1, which **retracted** a Phase 4
inference):

- The four patterns have **96 / 96 / 48 / 96 multipliers**, i.e. 48 / 48 / 24 /
  48 hour cycles at the 0:30 pattern step.
- Phase 4 had inferred "16/16/8/16 entries → an 8-hour cycle". **That inference
  is retracted.**

`VERIFIED_FACT` (D2) — pattern assignment:

| Pattern | Junctions | Base demand |
|---|---|---|
| PATTERN-0 | 77 | 943.910 GPM |
| PATTERN-1 | 2 | 0.800 GPM |
| (none) | 47 | — |
| PATTERN-2, PATTERN-3 | defined, referenced by nothing | — |
| **Total** | 126 | **944.710 GPM** |

### 6.6 The five connector-node artefacts

`VERIFIED_FACT` — JUNCTION-105, -106, -109, -110, -128: degree-2, zero base
demand, pump/reservoir-adjacent, declared elevation **exactly 0.0 ft**. EPANET
reports head-above-datum there; JUNCTION-106 reads **501.6 psi**.

Effect of including them: mean pressure 94.787 → 101.49 psi (+9.01 psi), maximum
+219.5 psi, 7 spurious inter-report jumps above 25 psi.

**Every pressure observation, pressure reward term, pressure metric and leak
emitter uses the 121 demand-bearing junctions.** The rule is mechanical —
elevation exactly 0.0 ft AND zero total base demand — and unambiguous, since the
next lowest elevation in the file is 192.0 ft. They carry 0.5998 % of mean leak
flow and 0.3555 % of total emitter coefficient, so excluding them from the leak
instrument too is a small but real correction.

---

## 7. LOCKED CONFIGURATION (verbatim from `docs/phase4_decision_report.md`)

This is the master specification. Reproduced here **verbatim** so the handoff
does not depend on the report file surviving. `DECISION` throughout, with `FACT`
/ `TO TUNE` / `UNKNOWN` markers as the original wrote them.

> The block below is a **specification**, not code. Every field is either a decision
> with its justification, or explicitly marked `TO TUNE` / `UNKNOWN`.

```text
NETWORK
  primary        BWSN_Network_1.inp  (BWSN 2008, "Battle of the Water Sensor
                 Networks", Ostfeld et al.)  — 126 junctions, 1 reservoir,
                 2 tanks, 168 pipes, 2 pumps (HEAD CURVE-0 / CURVE-2),
                 8 PRV, 4 RULES on tank levels, Duration 96:00 @ 0:30,
                 GPM / psi / ft, Hazen-Williams.  Counts verified from the .inp.
  secondary      Net3.inp (EPANET distribution) — comparability with
                 Hu, Gao & Zhong (2023) ONLY. 92 junctions, 117 pipes,
                 2 pumps, 0 valves; 4 PRVs inserted at Hu's locations.
  tertiary       Jowitt & Xu (1990), unmodified, reconstructed from the paper
                 (JWRPM 116(4):455-472).  OPTIONAL. Comparability with
                 Negm (2024) ONLY. No official .inp exists — record this.
  generalisation L-TOWN.inp (Zenodo 4017659) if and only if compute permits.
                 782 junctions, 905 pipes, 1 pump, 3 PRV, CMH/m.
  fallback       d-town.inp, if pre-flight check P1 fails.
  EXCLUDED       Kentucky KY1-KY17 / KYV series — Duration 0, [CURVES] empty,
                 pumps declared by POWER; affinity-law speed control impossible
                 without inventing pump curves.
  UNITS NOTE     BWSN-1 and Net3 are US units; L-Town is metric. All reported
                 pressures converted to metres of head; conversion stated in
                 the thesis.

LEAKAGE MODEL
  mechanism      EPANET [EMITTERS] / WNTR leak nodes.  Orifice form
                 q = C * p^alpha.
  exponent       alpha = 0.5 for discrete orifice leaks (theoretical orifice
                 exponent).  Background-leakage runs additionally reported at
                 alpha = 1.0 as a sensitivity, since field-reported exponents
                 for background leakage exceed 0.5.  Both values stated, neither
                 presented as the single truth.
  coefficients   C values NOT yet set.  TO TUNE: calibrate so that baseline
                 uncontrolled leakage is a stated fraction of total system
                 input, that fraction fixed in advance and reported.
  justification  FACT: [EMITTERS] is empty in all 13 candidate .inp files
                 parsed. Leakage must be added on every network, so this is a
                 common modelling cost, not a network-specific concession.
  DO NOT         change C or alpha between the RL agent and the baselines.
```

```text
DEMAND MODEL
  base           node base demands as distributed in the .inp — never edited.
  pattern        REPLACE BWSN-1's native patterns.  FACT: BWSN-1 ships 4
                 patterns of 16/16/8/16 entries at a 0:30 pattern step, i.e. an
                 8-hour cycle repeated over 96 h — not diurnal.  Imposed model:
                 24-hour diurnal multiplier profile + multiplicative stochastic
                 noise per node per step.
  stochasticity  noise distribution and magnitude TO TUNE.  Requirement: the
                 training distribution must be documented as a distribution, so
                 that "out of distribution" has a defined meaning for the test
                 protocol below.
  weekday/weekend  adopted only on L-Town, where BattLeDIM defines it.  Not
                 invented for BWSN-1.
  justification  Any credible uncertainty study needs its own demand model on
                 any of these networks. Documented as a modification.

PDA/DDA
  training       PDA (EPANET 2.2 DEMAND MODEL PDA / WNTR pressure-driven).
  reason         Under active pressure reduction and leakage, DDA delivers full
                 demand at physically impossible pressures and overstates
                 achievable savings.
  PDA parameters minimum and required pressure TO SET explicitly and reported.
                 For L-Town, BattLeDIM states the service target verbatim:
                 "a pressure head of at least 20m to all of its consumers" —
                 use 20 m there.  For BWSN-1 (psi units) the equivalent service
                 threshold must be set and justified separately; UNKNOWN
                 whether BWSN documentation states one.
  extra result   Run the FINAL trained policy under DDA as well, and report the
                 difference. This is claim N9 and it is a result, not a setting.

PRV PLACEMENT               (design D3 — dual placement, from section 7)
  headline arm   BWSN-1's native 8 PRVs, exactly as distributed. Locations fixed
                 by the BWSN organisers in 2008 for a contamination-sensor
                 objective, therefore exogenous to this thesis's reward.
                 Native settings: 70, 80, 55, 29.762, 45, 37, 40, 16.45 psi.
                 FACT: [CONTROLS] closes VALVE-180 at time 0, so 7 of 8 are
                 active at t=0. Preserve this unless deliberately changed.
  sensitivity    GA-selected SUBSET of those same 8 valves (k of 8, k stated).
                 Purpose: quantify how much benefit comes from placement vs
                 control (claim N11). The GA never invents new locations.
  comparability  Net3 with 4 PRVs at Hu, Gao & Zhong's (2023) locations.
  insertion      where a valve must be added, use the paired-node pattern BWSN-1
                 itself uses (valve link between two artificial nodes, one
                 incident pipe per side) so hydraulics are unchanged apart from
                 the valve.
  DO NOT         re-run placement optimisation against the thesis reward on the
                 primary network. That is the co-optimisation bias documented in
                 section 7 and it invalidates the headline claim.
```

```text
PUMP MODEL
  base           BWSN-1's 2 existing pumps, PUMP-170 (CURVE-0) and PUMP-172
                 (CURVE-2).  CURVE-1 is present but unused in the .inp.
  change         relative speed becomes a controlled variable. This is a native
                 EPANET pump property, NOT a topology edit — the head curves
                 required for affinity-law scaling already exist.
  speed bounds   TO SET, and must be stated. Requirement: bounds must keep the
                 operating point on the supplied curve's valid range; do not
                 allow speeds that extrapolate the curve into nonsense.
  native rules   FACT: 4 [RULES] tie the pumps to tank levels — PUMP-170 on
                 TANK-131 (open <= 15.4, closed >= 18.4), PUMP-172 on TANK-130
                 (open <= 12.1, closed >= 16.0).  DECISION: keep these rules as
                 the on/off envelope for the PRV-only baseline, and disable them
                 only in the arms where the agent controls the pump. State which
                 arms have them active — this is a comparability trap if left
                 implicit.
  energy         [ENERGY] Global Efficiency 75 %, Global Price 0 in the .inp.
                 A price must be set to report energy cost; the value chosen is
                 an assumption and must be reported, not buried.

STATE
  observation    tank levels (2 on BWSN-1); pressures at a defined sensor subset;
                 total inflow; current PRV settings; current pump speed(s);
                 time-of-day encoding.
  sensor subset  MUST be a realistic subset, NOT all 126 junctions.  Selection
                 rule TO DECIDE and to be stated.  Precedent for a principled
                 subset: BattLeDIM placed 33 sensors "using a methodology which
                 maximizes the collective sensitivity of the sensors to any
                 possible leak".  UNKNOWN whether BWSN-1 documentation defines a
                 sensor set; if not, the rule used here is an author decision and
                 must be declared.
  normalisation  fixed per-variable scaling, computed ONCE from the baseline
                 configuration and frozen across all arms, seeds and test sets.
  DO NOT         include the true leak flow, the true leak location, or any
                 quantity a real SCADA system could not measure. That is data
                 leakage and it is the first thing an examiner will look for.

ACTION
  space          continuous Box.
  components     8 PRV pressure setpoints + N pump relative speeds.
  bounds         PRV setpoints bounded per valve within a stated range tied to
                 that valve's own hydraulic context; pump speed bounded as
                 above.  Negm's precedent for reference: "0 to 70 for valves and
                 unbounded speeds for the pumps" — the unbounded pump speed is
                 NOT adopted here; unbounded speed invites physically invalid
                 operating points.
  rate limits    a per-step change limit on setpoints, to prevent policies that
                 are unimplementable on real actuators. Value TO SET.
  arms           PRV-only  |  VSP-only  |  joint PRV+VSP.  This triple IS the
                 ablation of claim N6 and is not optional.
```

> **Phase 6 amendment to the ACTION block (`DECISION`, supersedes "8 PRV
> pressure setpoints"):** the controlled set is **five** PRVs —
> VALVE-173, 175, 176, 177, 178. VALVE-174, -179 and -180 are held at nominal
> for measured reasons. See §8 below and FINDINGS.md.

```text
REWARD
  terms          (1) leakage volume  (2) pressure-service violation
                 (3) pump energy  (4) actuator-movement penalty.
  form           weighted sum for TRAINING only.
  weights        TO TUNE.  Negm's precedent, verbatim: "a ratio of 3:1 favouring
                 the leakage objective produces the best trade-off".  This thesis
                 does NOT inherit that ratio, because section 9 / Q14 argues the
                 3:1 setting is what produced his 264-304 violations against a
                 classical optimiser's 46-78.
  weight study   report results across a SET of weightings, not one. The output
                 is a trade-off surface (claim N10).
  EVALUATION     never by scalarised reward.  Violations are reported as a
                 separate, non-negotiable axis, and methods are compared at
                 MATCHED violation budgets.
  reward hacking explicit check: inspect whether the policy achieves leakage
                 reduction by starving nodes (PDA delivery shortfall) rather than
                 by managing pressure. Report delivered-vs-required demand.

UNCERTAINTY                 (two axes, deliberately separated — claims N7, N8)
  axis 1         DEMAND. Stochastic multipliers during training; test includes an
                 out-of-distribution regime (magnitude/shape outside the training
                 distribution).  Contrast with Hu, Gao & Zhong (2023), FACT,
                 verbatim: they tested "five random test cases from the same
                 distribution of the training".
  axis 2         MODEL PARAMETERS. Pipe roughness and diameter perturbation.
                 Precedent for the magnitude, BattLeDIM verbatim: "the EPANET
                 model parameters may be different from the actual network
                 parameters (e.g., diameters, roughness coefficients), and it is
                 assumed than in general this difference is no greater than 10%
                 of the nominal values".  Adopt 10 % as the declared bound and
                 cite that source.
  reporting      the two axes are reported SEPARATELY and then jointly. Merging
                 them destroys the contribution.

PPO
  library        Stable-Baselines3 PPO (single agent).  Version to be pinned in
                 the thesis; UNKNOWN until the environment is built.
  hyperparams    START from the library defaults and tune from there. The default
                 set (learning rate 3e-4, n_steps 2048, batch 64, 10 epochs,
                 gamma 0.99, GAE lambda 0.95, clip 0.2, vf coef 0.5, max grad
                 norm 0.5) is recorded here as a STARTING POINT, to be verified
                 against the installed version rather than quoted from memory.
                 Every value actually used must be logged per run.
  episode        one 96-hour EPS = 192 control steps on BWSN-1 (0:30 hydraulic
                 step).  Control interval may be coarser than the hydraulic
                 step; if so, state the ratio.
  budget         total timesteps TO SET.  Constraint: the budget must be
                 identical across all arms and all networks being compared.
  MADDPG arm     optional: single-agent PPO vs multi-agent baseline (claim N13).
                 Drop before dropping the ablation or the OOD test.
```

```text
BASELINES                   (all on the identical environment, leak model,
                             demand realisations and PDA settings)
  B0  no control            native PRV settings + native pump rules. The floor.
  B1  fixed optimised       one static PRV setting vector + one pump schedule,
                            optimised offline on the MEAN demand profile.
  B2  classical online      a metaheuristic re-optimising per timestep with full
                            knowledge of the current state.  Precedent set:
                            Negm uses Nelder-Mead, PSO and DE; Hu uses GA, PSO
                            and DE.  Choose at least two, and say which.
  B3  rule-based            a time-of-day PRV modulation rule of the kind
                            utilities actually deploy.
  UPPER BOUND               optional oracle: the same optimiser as B2 given
                            PERFECT foresight of future demand. Bounds how much
                            of the gap is attributable to uncertainty itself.
  fairness rule             baselines get the same actuators, the same bounds and
                            the same rate limits as the agent. A baseline denied
                            an actuator the agent has is not a baseline.
  compute note              report the wall-clock cost of B2 per decision. Online
                            metaheuristics are frequently infeasible in real time;
                            that is a legitimate advantage of a trained policy and
                            it should be measured, not asserted.

TEST PROTOCOL
  separation     demand realisations used for training are never reused for
                 testing. Fixed, saved test sets.
  T1 in-dist.    held-out realisations from the training distribution.
  T2 OOD demand  realisations outside the training distribution (claim N7).
  T3 param.      roughness/diameter perturbed to the declared 10 % bound
                 (claim N8), with demand held in-distribution so the axes stay
                 separable.
  T4 joint       T2 and T3 together. The hardest case; report it even if it fails.
  T5 PDA vs DDA  the final policy re-evaluated under DDA (claim N9).
  T6 transfer    optional: BWSN-1-trained policy applied zero-shot to Net3 and
                 L-Town (claim N16). Only claim transferability if T6 is run.
  metrics        leakage volume; number and magnitude of service violations;
                 delivered/required demand ratio; pump energy; actuator movement;
                 constraint-matched comparison against every baseline.
  reporting      mean AND spread across seeds for every number. No single-run
                 results in the thesis.

SEEDS
  training       >= 5 independent seeds per arm per network. Non-negotiable —
                 FACT: neither Hu, Gao & Zhong (2023) nor Negm (2024) reports
                 seed variance, and Jun, Yoo & Jung (2025, JWRPM,
                 doi 10.1061/JWRMD5.WRENG-6868, "Toward Transparent and
                 Reproducible Machine Learning-Based Research in Urban Water
                 Networks") argues directly for this reporting standard.
  evaluation     test-set generation seeded separately from training and fixed
                 once, so every arm and every baseline sees identical scenarios.
  logging        every seed, every config, every library version recorded per
                 run. Results reported as distributions, never as best-of-n.
```

**Note on the DEMAND MODEL block's `FACT` line.** It states "4 patterns of
16/16/8/16 entries … an 8-hour cycle". **Phase 5 measured 96/96/48/96
multipliers → 48/48/24/48 hour cycles and formally retracted the 8-hour
inference (D1).** The *decision* to replace the native patterns with a 24-hour
diurnal profile stands; only the description of what is being replaced was wrong.

---

## 8. Phase 6 amendments to the locked configuration

`DECISION`, each backed by measurement. Full evidence in
`docs/phase6_g5_g12_resolution.md`.

### 8.1 Solver configuration — NON-NEGOTIABLE

```text
ACCURACY          = 1e-5      (file ships 0.005)
TRIALS            = 2000      (file ships 40)
RULE TIMESTEP     = 180 s     (WNTR defaults to 360 s)
CONTROL / REPORT  = 1800 s
DEMAND MODEL      = PDA
required_pressure = 20 psi
minimum_pressure  = 0 psi
pressure_exponent = 0.5
emitter exponent  = 0.5       (from the file's own [OPTIONS])
```

Set in code on **every** load, then **asserted**. Reference implementation:
`assert_solver()` at `src/validation/p6_s3_prv_finechar.py:117`.

### 8.2 Action space — five PRVs

```text
RL-controlled : VALVE-173, VALVE-175, VALVE-176, VALVE-177, VALVE-178
Fixed at nominal : VALVE-174 (80 psi), VALVE-179 (40 psi), VALVE-180 (16.45 psi)
VALVE-179 : if ever actuated, hard clamp <= 44.7 psi. Cliff at 44.8/44.9 psi.
Bounds for the five : TO BE DERIVED BY MEASUREMENT in STEP 6. Not yet set.
```

### 8.3 Pump strategy — Option C on Option A's mechanism

```text
1. Native rules, controls and topology untouched. No rule removed or rewritten.
2. EPS advances in 1800 s segments, carrying forward tank levels, pump status,
   AND pattern time.
3. The agent's pump action is written to base_speed and RE-ISSUED every control
   step. A command's lifetime in this architecture is exactly one control step
   (hold rate 1.72 % without re-issue, 98.62 % with).
4. The agent commands SPEED ONLY. Status stays with the native rules, because
   STATUS IS OPEN is the only mechanism that restarts a shut pump.
5. info reports commanded and realised speed SEPARATELY, so the 1.38 % of open
   time in which native logic overrides the controller is visible in the record
   rather than assumed away.
6. Speed lower bound at or above the measured shut-off: 0.8152 (PUMP-170),
   0.7655 (PUMP-172). NOT 0.5.
```

### 8.4 Service statistics

```text
Service junctions        : 121 (demand-bearing)
Excluded                 : JUNCTION-105, -106, -109, -110, -128
Exclusion rule           : declared elevation exactly 0.0 ft AND zero total base demand
Service pressure threshold : 20 psi
Baseline deficit floor   : 386 node-timesteps below 20 psi; min 4.1645 psi at JUNCTION-29
```

Reference implementation: `service_nodes()` at
`src/validation/p6_s3_prv_finechar.py:79`.

### 8.5 The leakage instrument used so far

`ASSUMPTION` — and the brief forbids misrepresenting it:

> «Leak coefficientهای Phase 5 را بدون justification به‌عنوان field-calibrated
> leakage model معرفی نکن.»
> *Do not present the Phase 5 leak coefficients as a field-calibrated leakage
> model without justification.*

What it actually is: half-pipe-length weights, a **single closed-form global
scale** solved so that mean leakage equals a target fraction (10 %) of the
leak-free baseline's mean system inflow, exponent 0.5 taken from the file's own
`[OPTIONS] Emitter Exponent`. Signed form to keep negative-pressure states from
corrupting the accounting:

```
q = sign(p) · C · |p|^0.5
```

It is a **validation instrument**. The thesis's leakage model (`C` `TO TUNE`,
α = 0.5 with an α = 1.0 sensitivity) is a separate, still-open item.

---

## 9. Novelty position

`DECISION` — from the Phase 4 novelty re-audit (16 claims, N1–N16). Verbatim
verdicts:

**REJECTED — do not claim:**
- **N1** first continuous action space for WDN pressure control — *total*
  overlap with Negm (2024).
- **N2** first EPANET + PPO — *total* overlap; Hu et al. E-PPO, Pei et al.
  (JWRPM, doi 10.1061/JWRMD5.WRENG-6476, PPO on Anytown + D-Town), Xu et al.
  KA-PPO.
- **N3** first coordinated PRV + pump control — *total* overlap; Shao et al.
  *Energies* 12(15):2969, Brentan et al., Hu/Gao/Zhong MADDPG.
- **N4** first multi-objective reward — *total* overlap.

**HIGH novelty:**
- **N6** the PRV-only / VSP-only / joint ablation isolating the marginal
  contribution of variable-speed pump operation. Negm §7.3 names it explicitly
  as *future work*.
- **N7** out-of-distribution robustness of a joint PRV+VSP controller. Hu tested
  "five random test cases from **the same distribution of the training**".
- **N8** separating model-parameter uncertainty from demand uncertainty.
- **N10** Pareto / constraint-matched evaluation instead of a scalarised cost.
- **N11** quantifying how much of the reported RL benefit comes from optimised
  valve *placement* rather than from *control*. Marked *"freshest claim in this
  list."*

**Moderate / low:** N5 (first DRL on BWSN-1 — true but low-value alone),
N9 (PDA vs DDA — a real search gap remains), N12 (multi-seed reporting — low
novelty, high defensibility), N13 (PPO vs MADDPG), N14 (open environment —
substantially pre-empted by Locatelli et al.'s Dyn-WNTR), N15 (a sourced
correction of Cyriac & Chacko's priority claim), N16 (transfer — only claimable
if T6 is actually run).

**A methodological warning recorded in Phase 4 §9.2 and worth preserving.** The
OpenAlex counts (`"pressure reducing valve" AND "reinforcement learning"` → 2
results) **must never be quoted in the thesis as proof of novelty**, because
OpenAlex indexes abstracts and Hu/Gao/Zhong — the single most relevant paper —
does not appear in that query, since its abstract says "valve" rather than
"pressure reducing valve".

---

## 10. Known limitations

| Limitation | Label |
|---|---|
| The leakage model is synthetic. `[EMITTERS]` is empty in all 13 candidate `.inp` files, so leakage must be *added* on any network. | `VERIFIED_FACT` |
| The demand model is imposed, not observed. BWSN-1's native patterns are replaced with a 24-h diurnal profile plus noise. | `DECISION` |
| No official Jowitt & Xu `.inp` exists; it would be reconstructed from the 1990 paper. | `VERIFIED_FACT` |
| BWSN-1's PRV locations were chosen in 2008 for a *contamination-sensor* objective — good for exogeneity, but they were never optimised for pressure control. | `VERIFIED_FACT` and simultaneously the reason they are defensible |
| Whether BWSN documentation defines a service-pressure threshold or a sensor set | `UNKNOWN` |
| EPyT (EPANET 2.3.05) and WNTR (EPANET 2.2) have never been cross-validated in this project | `OPEN_QUESTION` |
| 1.38 % of pump open time is overridden by native tank protection | `VERIFIED_FACT`, accepted as an `ASSUMPTION` |
| VALVE-180's `[CONTROLS]` closure suppresses a 273 GPM path and doubles the sub-20 psi count. Retained for comparability. | `VERIFIED_FACT` + `DECISION` |
| `docs/research_questions.md`, `decisions.md`, `assumptions.md`, `literature.md`, `experiments.md`, `open_questions.md` are all **0 bytes** — the `CLAUDE.md` §18 documentation structure was never populated | `DIRECT_OBSERVATION` |

---

## 11. Unresolved scientific issues

1. `OPEN_QUESTION` — the sensor-subset selection rule. Must be principled and
   declared; BattLeDIM's 33-sensor sensitivity-maximising methodology is the
   cited precedent.
2. `OPEN_QUESTION` — the leak coefficient `C` for the thesis proper, and the
   baseline leakage fraction to calibrate it against.
3. `OPEN_QUESTION` — reward weights. Must come from measured metric scales
   (STEP 8), not from Negm's 3:1.
4. `OPEN_QUESTION` — PRV rate limits (per-step change cap).
5. `OPEN_QUESTION` — the energy price, needed to report cost; `[ENERGY]` ships
   Global Price 0.
6. `OPEN_QUESTION` — the total training timestep budget, which must be identical
   across all arms.
7. `UNRESOLVED` — whether Pei et al. (2025)'s test demands are genuinely
   out-of-distribution or merely stochastic. Affects the strength of N7. Full
   text not read.
8. `UNRESOLVED` — whether Locatelli et al.'s Dyn-WNTR is actually released.
   Affects N14.
9. **Debt** — the proposal mis-cites Hu's MARL paper. Correct to *Water Supply*
   **23(7):2833**, doi **10.2166/ws.2023.163**.
10. **Debt** — Negm's Table 5-4 must be re-verified **directly from the PDF**
    before it is cited.
