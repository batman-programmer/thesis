# EXPERIMENTS.md — every experiment, with exact numbers

Scope: every computational experiment performed in this project that left an
artefact on disk, plus the experiments that are *planned* and not yet run.

**No experiment in this project involves machine learning.** Nothing has been
trained. Every run listed below is a deterministic hydraulic simulation or a
sweep of such simulations. `USER_PROVIDED` prohibition still in force:
«در این Phase به هیچ عنوان هنوز آزمایش علمی PPO انجام نده».

**Reproducibility, global (`VERIFIED_FACT`).** No random seed is used anywhere in
Phase 5 or Phase 6 — every module is deterministic, so a rerun reproduces its
artefact bit-for-bit apart from the timestamps in the `env` block. Interpreter:
`D:\Thesis\.venv\Scripts\python.exe`, Python 3.13.15, WNTR 1.5.0, EPANET DLL
20200. Working directory for every command: `D:\Thesis`.

**Naming.** `E-P5-*` = Phase 5 gate experiment. `E-P6-*` = Phase 6 step
experiment. `E-PL-*` = planned, not run.

---

## 0. Master artefact index

| Artefact | Written by | Experiments it holds |
|---|---|---|
| `results/phase5/g0_integrity.json` | `src/validation/g0_integrity.py` | E-P5-00 |
| `results/phase5/g1_g2_g11_baseline.json` | `src/validation/g1_baseline.py` | E-P5-01, E-P5-02, E-P5-11 |
| `results/phase5/g3_pump_speed.json` | `src/validation/g3_pump_speed.py` | E-P5-03 |
| `results/phase5/g4_g5_prv.json` | `src/validation/g4_g5_prv.py` | E-P5-04, E-P5-05 |
| `results/phase5/g6_g7_g8_leak_pda.json` | `src/validation/g6_g7_g8_leak_pda.py` | E-P5-06, E-P5-07, E-P5-08 |
| `results/phase5/g9_g10_full.json` | `src/validation/g9_g10_full.py` | E-P5-09, E-P5-10 |
| `results/phase5/g12_realizability.json` | `src/validation/g12_realizability.py` | E-P5-12 |
| `results/phase5/working_copy_provenance.json` | `src/validation/phase5_common.py` | provenance record, not an experiment |
| `results/phase5/run_all_console.txt` | `src/validation/run_all.py` | consolidated console log of the full sequence |
| `results/phase6/p6_s3_prv_finechar.json` | `src/validation/p6_s3_prv_finechar.py` | E-P6-03a |
| `results/phase6/p6_s3b_v179_refine.json` | `src/validation/p6_s3b_v179_refine.py` | E-P6-03b |
| `results/phase6/p6_s3c_zone_interaction.json` | `src/validation/p6_s3c_zone_interaction.py` | E-P6-03c |
| `results/phase6/p6_s4_pump_strategy.json` | `src/validation/p6_s4_pump_strategy.py` | E-P6-04a … E-P6-04e |

Reproduce everything in Phase 5 with one command:

```bash
.venv/Scripts/python.exe src/validation/run_all.py
```

That driver runs the seven gate modules in dependency order **in separate
processes** (so a failure in one cannot corrupt another's interpreter state), then
reads the artefacts back and prints the consolidated verdict table of
`docs/phase5_bwsn_preflight.md` §17.

---

## 1. Phase 5 — the 13 pre-flight gates

### E-P5-00 — G0: model integrity

- **Objective.** Establish that the distributed `.inp` parses, that the working
  copy differs from it by exactly one known patch, and that the declared
  composition matches the brief.
- **Hypothesis.** The file is usable as-is under WNTR 1.5.0.
- **Setup.** Parse `data/networks/BWSN_Network_1.inp`; construct
  `data/networks/working/BWSN_Network_1_working.inp`; diff; count elements; hash.
- **Exact results (`VERIFIED_FACT`).**
  - Original size **44 402 bytes**, SHA-256
    `510af942ec643eb87adcf26e5a7df1cc4c23eb0c1e470a8a1257ed055f1956f1`.
  - The only patch applied: `Quality Chemical TIME` → `Quality Chemical mg/L`.
    Required for WNTR 1.5.0 to parse; hydraulically neutral because EPANET solves
    hydraulics independently of the water-quality module and this thesis performs
    no water-quality analysis.
  - Composition: **126 junctions, 1 reservoir, 2 tanks, 168 pipes, 2 pumps,
    8 PRVs**. Matches the brief exactly.
  - All eight PRVs are declared **`Active`** in `[VALVES]`, with settings
    70, 80, 55, 29.762, 45, 37, 40, 16.45 psi.
  - `[CONTROLS]` contains exactly one line:
    `LINK VALVE-180 Closed At Time 0.000000`.
  - Four `[RULES]`, all tank-level pump logic (see E-P6-04 for their text).
- **Verdict.** G0 **PASS**.
- **Next step it triggered.** The `[CONTROLS]` line became the whole of the
  VALVE-180 analysis in Phase 6 §6.

### E-P5-01 / E-P5-02 / E-P5-11 — G1 baseline, G2 solver characterisation, G11 mass balance

- **Objective.** Produce the reference 96 h EPS, and determine whether the
  shipped solver settings are trustworthy.
- **Hypothesis (falsified).** EPANET's zero-error report indicates a converged,
  physically consistent solution.
- **Setup.** 96 h EPS, hydraulic timestep 30 min, DDA and PDA arms, leak-free and
  leak arms, `ACCURACY`/`TRIALS` swept.
- **Exact results — the solver characterisation, the single most important
  measurement in the project (`VERIFIED_FACT`).**

  | Setting | Max emitter-law violation | Max continuity violation | Max instantaneous imbalance | States over threshold | Errors | Warnings |
  |---|---|---|---|---|---|---|
  | `ACCURACY 0.005 / TRIALS 40` (as shipped) | **2.0135 GPM** | **9.9692 GPM** | **25.6669 GPM** | 58 / 193 | **0** | **0** |
  | `ACCURACY 1e-5 / TRIALS 2000` (adopted) | **0.0008 GPM** | negligible | — | 0 | 0 | 0 |

  At `ACCURACY 1e-5` with only **200** trials the leak-free run **halts at
  19:00 h** with "System unbalanced" — trials must rise with accuracy.
- **Mass balance (G11), two independent routes.** Max relative continuity
  residual **5.18e-07** over the reference run; **1.4e-05** for the leak-active
  reference of Phase 6 §2.
- **Reporting cadence.** Changing `report_timestep` changes what is written, not
  what is solved: max |ΔP| = **0.0 m** between 1800 s and 3600 s reporting, but
  **193** vs **97** observable states.
- **Verdicts.** G1 **PASS**, G2 **CHARACTERISED**, G11 **PASS**.
- **Consequence.** `ACCURACY = 1e-5`, `TRIALS = 2000`, rule timestep 180 s,
  report timestep 1800 s became non-negotiable and must be **asserted** after
  every model load. See `assert_solver()` in
  `src/validation/p6_s3_prv_finechar.py:117`.

### E-P5-03 — G3: pump speed controllability

- **Objective.** Determine whether a commanded relative speed is transmitted to
  and realised by the solver.
- **Setup.** Sweep relative speed over 9 values per pump; fit the head curve;
  compare shut-off head against the affinity law; issue speed commands through
  native rules and read back `res.link["setting"]`.
- **Exact results (`VERIFIED_FACT`).**
  - Curve fits: **PUMP-170** h₀ = 445.0 ft, r = 1.9469e-05, n = 2.28247;
    **PUMP-172** h₀ = 740.0 ft, r = 8.3818e-05, n = 1.93845.
  - EPANET scales the curve as `h(q) = n²·h₀ − r·(q/n)^n_exp`. Shut-off head
    scales as speed² **exactly** at all 9 swept speeds for both pumps; max
    |residual| of any running operating point **8.62e-05 ft**.
  - Measured **shut-off speed**: **0.8152 for PUMP-170**, **0.7655 for
    PUMP-172**. A 0.70 command yields **zero** open states. The bound *moves*
    during an EPS as tank level changes, so it is a floor, not a constant.
  - **Non-persistence fingerprint.** A commanded 0.85 produced a mean flow of
    **764.5399 GPM** where the true 0.85 behaviour is **765.8873 GPM** — the
    discrepancy that revealed the speed reset.
- **Verdict.** G3 **PASS** (transmission works) — but the persistence question
  was escalated and became **G12 CONDITIONAL**.
- **Failure recorded.** `ControlAction(pump, 'speed', ...)` raises; valid pump
  attributes are `base_speed`, `setting`, `status`.

### E-P5-04 / E-P5-05 — G4/G5: PRV responsiveness and action-space candidacy

- **Objective.** Classify each of the 8 PRVs as responsive or not.
- **Setup.** Per-valve sweep at ×0.75 … ×1.25 of nominal, one 96 h EPS each.
- **Instrument defect, disclosed (`VERIFIED_FACT`).** `g4_g5_prv.py` **did not
  set** accuracy or trials and therefore inherited the file's `0.005 / 40`. The
  *classification* conclusions survive — they turn on whether a valve responds at
  all — but **no numeric value from this harness is carried into Phase 6**, and
  its snapshot harness was deliberately not reused.
- **Exact results.** PRV setpoint realisation error ≤ **2.67e-05 psi**. Five
  valves (173, 175, 176, 177, 178) responsive; three (174, 179, 180) solved to
  `Closed`.
- **Verdicts.** G4 **PASS**, G5 **CONDITIONAL** — the conditional being that the
  three closed valves had not been characterised finely enough to justify
  excluding them. Discharged by E-P6-03a/b/c.
- **Method finding.** The *conjunctive* responsiveness criterion (require
  simultaneous movement in flow **and** pressure **and** leakage) is **wrong**: it
  would have rejected VALVE-175, which carries **38.495 %** of system demand
  across a **115.00 psi** setpoint span while its own flow span is only
  **0.00092 GPM**.

### E-P5-06 / E-P5-07 / E-P5-08 — G6/G7/G8: leak instrument, PDA, and their interaction

- **Objective.** Build a background-leakage instrument and verify PDA behaviour.
- **Leak sizing, exact (`VERIFIED_FACT`).**

  | Quantity | Value |
  |---|---|
  | Target leakage (10 % of leak-free mean inflow) | **84.74359 GPM** |
  | Σ_j (w_j · p_j^α) over service junctions | **1 187 270.5038** |
  | Global scale `k = target / Σ` | **7.13768134008582e-05** |
  | Σ of assigned emitter coefficients | **8.76509297** |
  | Realised mean leakage | **84.7266 GPM** |
  | Realised fraction of inflow | **9.1795 %** |

  Method: half of each incident pipe's length assigned to each junction as weight
  `w_j`; **one** global closed-form scale evaluated once, no iteration and no
  search; α = **0.5** taken from the file's own `[OPTIONS] Emitter Exponent`.
  Connector junctions excluded from the instrument as well as from the statistics.
- **`ASSUMPTION`, stated as the brief's §18 requires.** This is a **validation
  instrument**, not a field-calibrated leakage model. It is not calibrated against
  any measurement of the BWSN-1 system, no such measurement is known to the author
  to exist, and no thesis result may be presented as a calibrated leakage estimate.
- **Signed emitter law (`VERIFIED_FACT`).** At JUNCTION-126, p = **−5.731 psi**:
  engine **−0.6416 GPM**, signed law `q = sign(p)·C·|p|^0.5` **−0.6416 GPM**,
  pressure-clipped law **0.0000 GPM**. An EPANET emitter is a virtual pipe to a
  virtual reservoir and **flows backwards** at negative pressure — so any state
  with negative service pressure is numerically corrupting to leakage accounting,
  not merely physically meaningless.
- **PDA vs DDA at nominal (`VERIFIED_FACT`).** DDA DSR **0.99999998**;
  PDA DSR **0.9833382** (leak-free) / **0.9818803** (leak-active); max unserved
  **47.6861 GPM**. PDA therefore bites at nominal settings — the deficit is
  pre-existing, not controller-induced.
- **Two permanently deficient junctions.** JUNCTION-29, elevation 846.28 ft,
  pressure 5.1202 psi (leak-free) / **4.1645 psi** (leak-active) — the network
  minimum. JUNCTION-126, elevation 434.00 ft, 16.7387 / 16.6168 psi.
- **DSR > 1 is numerical**, not physical: the reported-minus-modelled leakage
  decomposition leaves a small residual at full service. A value of 1.00016 means
  "no unserved demand".
- **Verdicts.** G6 **PASS**, G7 **PASS**, G8 **PASS**.

### E-P5-09 / E-P5-10 — G9/G10: full-horizon stability and pressure statistics

- **Objective.** Confirm 96 h stability and decide which node set the pressure
  statistics are computed over.
- **Exact results — the connector-node artefact (`VERIFIED_FACT`).**

  | Statistic | All 126 junctions | 121 service junctions |
  |---|---|---|
  | Mean pressure | **103.7944 psi** | **94.7867 psi** |
  | Max pressure | **507.7488** (JUNCTION-106) | **288.2206** (JUNCTION-34) |
  | Max inter-report change | **25.8712 psi** | **6.7257 psi** |
  | States with change > 25 psi | **7** | **0** |

  The five excluded junctions — JUNCTION-105, -106, -109, -110, -128 — have
  declared elevation **exactly 0.0 ft** and **zero** total base demand, all have
  degree two, and each is an endpoint of a pump or the reservoir connector pipe.
  Next lowest elevation in the file is **192.0 ft**, so the rule is unambiguous.
  EPANET reports head-above-datum at them.
- **Disclosure (`VERIFIED_FACT`).** G10's pressure criterion was reported on
  **both** node sets rather than only the favourable one.
- **Verdicts.** G9 **PASS**, G10 **PASS**.

### E-P5-12 — G12: actuator realizability

- **Objective.** Verify that commanded actuator values are realised.
- **Result.** PRV setpoints: realised. Pump speed: transmitted and realised **at
  the instant of issuance**, but **not persistent**.
- **Verdict.** G12 **CONDITIONAL**. Discharged by E-P6-04.

### Phase 5 consolidated verdict

G0 PASS · G1 PASS · G2 CHARACTERISED · G3 PASS · G4 PASS · **G5 CONDITIONAL** ·
G6 PASS · G7 PASS · G8 PASS · G9 PASS · G10 PASS · G11 PASS · **G12 CONDITIONAL**.
**No gate FAILED. Overall: CONDITIONAL PASS.**

---

## 2. Phase 5 side experiments — the pressure-management confounds

These were run inside the gate modules but are separable, and they are the most
methodologically important results in the project.

### E-P5-S1 — Is mean pressure a sufficient statistic for a monotonicity test?

- **Hypothesis (falsified).** If leakage falls, mean pressure fell.
- **Method.** Sweep families of PRV scalings; test the **pressure-dominance
  partial order** — case X dominates Y only if **every** junction is at least as
  high in X, within tolerance — against the mean-pressure test.
- **Exact result (`VERIFIED_FACT`).** The mean-pressure test **FAILS on one pair**:
  family A ×0.75 → ×1.25 *raises* mean pressure **100.3987 → 100.7715 psi** while
  leakage **falls**. Pressure dominance passes with **0 violations at all six
  tolerances**.
- **Conclusion.** Mean pressure is **not** a sufficient statistic. Use dominance.

### E-P5-S2 — Confound X2: the PDA feedback loop

- **Finding (`VERIFIED_FACT`).** Curtailment reduces withdrawal → reduces friction
  loss → **raises** pressure downstream of curtailed nodes. Scaling all PRVs to
  ×0.25 leaves **84 junctions higher and 33 lower** relative to ×0.75.
- **Implication.** "Lower setpoints ⇒ lower pressure everywhere" is false under
  PDA. Any reward that assumes it is monotone in the setpoints is wrong.

### E-P5-S3 — Leakage saving vs customer starvation

- **Objective.** Quantify the single most dangerous confound in pressure-management
  research: an agent can cut leakage by starving customers.
- **Exact result at all PRVs ×0.25 (`VERIFIED_FACT`).** Inflow falls
  **1.1571 Mgal**, of which:
  - **0.0392 Mgal (3.39 %)** is genuine leakage saving,
  - **1.1533 Mgal (99.67 %)** is **unserved demand**,
  - at DSR **0.7596**.
- **Consequence.** `USER_PROVIDED`, brief §19: "lower leakage ≠ necessarily better
  solution." Evaluation must never be by scalarised reward, and the reward must
  contain an explicit service term calibrated against the **pre-existing** deficit
  floor (386 node-timesteps, min 4.1645 psi).

### E-P5-S4 — Baseline pump duty and the effect of speed

- **Exact results (`VERIFIED_FACT`).** PUMP-172 consumes **5.8×** PUMP-170's
  energy at baseline. Speed changes **redistribute energy between the two pumps
  rather than changing network pressure**.
- **Caveat, stated.** This measurement is **contaminated by the non-persistence
  defect** of E-P5-03 and must be re-derived under the Option C mechanism before
  it is used for reward design.

### E-P5-S5 — Tank behaviour over 96 h

- **Result (`VERIFIED_FACT`).** Both tanks cycle without emptying or overflowing
  at nominal settings. Reference final levels: TANK-130 **13.782 ft**,
  TANK-131 **16.874 ft**.

---

## 3. Phase 6 STEP 3 — fine characterisation of the three closed PRVs

Common setup for E-P6-03a/b/c (`VERIFIED_FACT`): working copy; solver
`ACCURACY 1e-5`, `TRIALS 2000`, rule timestep 180 s, report timestep 1800 s, all
**asserted after load**; PDA required 20 psi / minimum 0 psi / exponent 0.5;
leakage instrument active; 96 h EPS, 193 reporting timesteps; statistics over the
**121** service junctions; echo check (write `.inp`, read back) on every case.

**Reference state, all eight PRVs nominal (`VERIFIED_FACT`).**

| Quantity | Value |
|---|---|
| Mean service pressure (121 junctions) | 94.787 psi |
| Minimum service pressure | 4.165 psi, at JUNCTION-29 |
| Node-timesteps below 20 psi | 386 |
| Node-timesteps at negative pressure | **0** |
| Mean leakage | 84.730 GPM |
| Mean served demand | 891.414 GPM |
| Mean unserved demand | 14.985 GPM |
| Mean DSR | 0.983337 |
| Mean pressure deficit | 18.14 psi·nodes |
| Max relative continuity residual | 1.4e-05 |

The baseline contains **no** negative pressure, so any negative pressure below is
caused by the perturbation under test.

### E-P6-03a — coarse sweep of VALVE-179, -174, -180

`src/validation/p6_s3_prv_finechar.py` → `results/phase6/p6_s3_prv_finechar.json`

Grids as coded:

```python
GRIDS = {
    "VALVE-179": [38.0, 39.0, 40.0, 41.0, 42.0, 43.0, 44.0, 45.0, 46.0,
                  47.0, 48.0, 49.0, 50.0, 52.0, 55.0, 60.0],
    "VALVE-174": [80.0, 85.0, 90.0, 92.0, 94.0, 95.0, 96.0, 98.0, 100.0, 110.0],
    "VALVE-180": [16.45, 20.0, 30.0, 40.0, 60.0, 80.0, 120.0],
}
```

**VALVE-179 (nominal 40 psi) — exact results.**

| Setting (psi) | ×nom | Active/Open/Closed | q̄ (GPM) | q_max (GPM) | min P (psi) | n<20 | n neg | leak (GPM) | served (GPM) | DSR |
|---|---|---|---|---|---|---|---|---|---|---|
| 38 | 0.950 | 0.000/0.000/1.000 | 0.00 | 0.00 | 4.165 | 386 | 0 | 84.730 | 891.41 | 0.983337 |
| 39 | 0.975 | 0.000/0.000/1.000 | 0.00 | 0.00 | 4.165 | 386 | 0 | 84.730 | 891.41 | 0.983337 |
| **40** | **1.000** | 0.000/0.000/1.000 | 0.00 | 0.00 | 4.165 | 386 | 0 | 84.730 | 891.41 | 0.983337 |
| 41 | 1.025 | 0.000/0.000/1.000 | 0.00 | 0.00 | 4.165 | 386 | 0 | 84.730 | 891.41 | 0.983337 |
| 42 | 1.050 | 0.000/0.000/1.000 | 0.00 | 0.00 | 4.165 | 386 | 0 | 84.730 | 891.41 | 0.983337 |
| 43 | 1.075 | 0.202/0.000/0.798 | 59.52 | 632.88 | 4.189 | 386 | 0 | 84.735 | 891.41 | 0.983337 |
| 44 | 1.100 | 0.808/0.000/0.192 | 417.67 | 926.62 | 4.203 | 386 | 0 | 84.764 | 891.41 | 0.983337 |
| **45** | **1.125** | 0.984/0.016/0.000 | 860.55 | 1209.73 | **−96.984** | **513** | **49** | 84.259 | 875.47 | **0.970328** |
| 46 | 1.150 | 0.751/0.249/0.000 | 1110.28 | 1374.33 | −97.032 | 821 | 342 | 81.642 | 817.00 | 0.906180 |
| 47 | 1.175 | 0.389/0.611/0.000 | 1227.47 | 1437.59 | −97.026 | 960 | 532 | 79.935 | 806.50 | 0.894200 |
| 48 | 1.200 | 0.249/0.751/0.000 | 1268.85 | 1532.04 | −97.112 | 996 | 580 | 79.485 | 797.02 | 0.888270 |
| 49 | 1.225 | 0.207/0.793/0.000 | 1294.02 | 1706.58 | −97.016 | 1028 | 612 | 79.208 | 791.03 | 0.883450 |
| 50 | 1.250 | 0.171/0.829/0.000 | 1309.61 | 1882.00 | −97.086 | 1052 | 640 | 78.970 | 790.61 | 0.879500 |
| 52 | 1.300 | 0.135/0.865/0.000 | 1330.80 | 2198.63 | −97.014 | 1081 | 668 | 78.728 | 789.83 | 0.875520 |
| 55 | 1.375 | 0.104/0.896/0.000 | 1345.69 | 2608.73 | −97.004 | 1103 | 692 | 78.524 | 787.86 | 0.872130 |
| 60 | 1.500 | 0.083/0.917/0.000 | 1367.13 | 3200.71 | −97.026 | 1118 | 708 | 78.383 | 785.83 | 0.869180 |

The 50 psi row **reproduces Phase 5's −97.086 psi at ×1.25 exactly**. But the
brief's picture was coarse: the transition is at **45**, not 50, and the valve
begins to open at **43**.

**VALVE-174 (nominal 80 psi) — exact results.**

| Setting (psi) | ×nom | Active/Open/Closed | q̄ (GPM) | mean P (psi) | min P (psi) | n<20 | leak (GPM) | served (GPM) | DSR |
|---|---|---|---|---|---|---|---|---|---|
| 80 | 1.000 | 0.000/0.000/1.000 | 0.00 | 94.787 | 4.165 | 386 | 84.730 | 891.41 | 0.983337 |
| 85 | 1.062 | 0.000/0.000/1.000 | 0.00 | 94.787 | 4.165 | 386 | 84.730 | 891.41 | 0.983337 |
| 90 | 1.125 | 0.000/0.000/1.000 | 0.00 | 94.787 | 4.165 | 386 | 84.730 | 891.41 | 0.983337 |
| 92 | 1.150 | 0.000/0.000/1.000 | 0.00 | 94.787 | 4.165 | 386 | 84.730 | 891.41 | 0.983337 |
| 94 | 1.175 | 0.000/0.000/1.000 | 0.00 | 94.787 | 4.165 | 386 | 84.730 | 891.41 | 0.983337 |
| 95 | 1.188 | 0.000/0.000/1.000 | 0.00 | 94.787 | 4.165 | 386 | 84.730 | 891.41 | 0.983337 |
| **96** | **1.200** | **1.000**/0.000/0.000 | 4.73 | 94.815 | 4.164 | 386 | 84.737 | 891.41 | 0.983337 |
| 98 | 1.225 | 1.000/0.000/0.000 | 4.76 | 94.948 | 4.164 | 386 | 84.771 | 891.41 | 0.983337 |
| 100 | 1.250 | 1.000/0.000/0.000 | 4.79 | 95.080 | 4.164 | 386 | 84.805 | 891.41 | 0.983337 |
| 110 | 1.375 | 1.000/0.000/0.000 | 4.96 | 95.742 | 4.164 | 386 | **84.968** | 891.41 | 0.983337 |

Reopening threshold bracketed between **95 and 96 psi** (1.188–1.200 × nominal).
Throughput **4.7–5.0 GPM** against ≈944.7 GPM total demand — about **0.5 %**.
Served demand unchanged to six decimals; n<20 constant at 386; the **only**
quantity that moves monotonically is **leakage, upward**.

**VALVE-180 (nominal 16.45 psi) — exact results, control in force.** `Closed`
for **100 % of the horizon at every setting from 16.45 to 120 psi** (up to 7.3 ×
nominal), zero flow, every service statistic bit-identical to the reference. No
setting can reopen it — the `[CONTROLS]` line overrides the PRV entirely.

**VALVE-180 — diagnostic only, control released. Not adopted anywhere.**

| Setting (psi) | Active | q̄ (GPM) | mean P (psi) | n<20 | n neg | leak (GPM) | served (GPM) | DSR | deficit |
|---|---|---|---|---|---|---|---|---|---|
| 16.45 | 0.000 | 0.00 | 94.787 | 386 | 0 | 84.730 | 891.41 | 0.983337 | 18.14 |
| 40 | 1.000 | 273.02 | 95.175 | **193** | 0 | 85.803 | **906.46** | **1.00016** | 14.88 |
| 80 | 1.000 | 274.34 | 95.834 | **193** | 0 | 87.118 | 906.46 | 1.00016 | 14.89 |

**Roughly half of BWSN-1's baseline pressure deficit is downstream of a valve the
benchmark deliberately commands shut**, removable at a cost of 1.07 GPM more
leakage. **`DECISION`: retained, recorded, not exploited.** Releasing it would be
the largest single service gain available and would destroy comparability with
every baseline and with the published benchmark.

### E-P6-03b — 0.1 psi refinement of the VALVE-179 cliff

`src/validation/p6_s3b_v179_refine.py` → `results/phase6/p6_s3b_v179_refine.json`

| Setting (psi) | Active | Open | Closed | q̄ (GPM) | min P (psi) | n<20 | n neg | leak (GPM) | served (GPM) | DSR |
|---|---|---|---|---|---|---|---|---|---|---|
| 44.0 | 0.808 | 0.000 | 0.192 | 417.67 | 4.203 | 386 | 0 | 84.764 | 891.41 | 0.983337 |
| 44.1 | 0.865 | 0.000 | 0.135 | 455.33 | 4.227 | 386 | 0 | 84.775 | 891.41 | 0.983337 |
| 44.2 | 0.896 | 0.000 | 0.104 | 496.50 | 4.206 | 386 | 0 | 84.782 | 891.41 | 0.983337 |
| 44.3 | 0.922 | 0.000 | 0.078 | 552.85 | 4.235 | 386 | 0 | 84.786 | 891.41 | 0.983337 |
| 44.4 | 0.969 | 0.000 | 0.031 | 600.65 | 4.234 | 386 | 0 | 84.769 | 891.41 | 0.983337 |
| 44.5 | 0.990 | 0.000 | 0.010 | 645.14 | 4.222 | 386 | 0 | 84.754 | 891.41 | 0.983337 |
| 44.6 | 1.000 | 0.000 | 0.000 | 709.45 | 4.210 | 386 | 0 | 84.739 | 891.41 | 0.983337 |
| **44.7** | 1.000 | 0.000 | 0.000 | 751.14 | 4.224 | **386** | 0 | 84.719 | 891.41 | **0.983337** |
| 44.8 | 1.000 | 0.000 | 0.000 | 790.48 | 4.206 | **423** | 0 | 84.699 | 891.27 | 0.983178 |
| **44.9** | 0.990 | 0.010 | 0.000 | 830.11 | **−96.981** | 454 | **18** | 84.521 | 884.43 | 0.976794 |
| 45.0 | 0.984 | 0.016 | 0.000 | 860.55 | −96.984 | 513 | 49 | 84.259 | 875.47 | 0.970328 |

**Three distinct measured boundaries.**

| Boundary | Value | Definition |
|---|---|---|
| Last **fully clean** setting | **44.7 psi** (1.1175 × nominal) | Every service statistic identical to the reference: n<20 = 386, DSR = 0.983337 |
| Last **non-negative** setting | 44.8 psi | No negative pressure, but service already degrading: n<20 → 423, DSR → 0.983178 |
| First **failing** setting | 44.9 psi | 18 negative node-timesteps, minimum −96.981 psi |

**`DECISION`.** Bound at **44.7 psi**, not 44.8: 44.8 is already outside the
reference service envelope, and the 0.1 psi margin to first failure is finer than
any resolution at which a physical PRV could be commanded. Cost of the extra
margin: 39 GPM of valve throughput, worth ≈0 in leakage terms.

**Mechanism — the failure is elevation-driven, not a valve defect.** VALVE-179
runs JUNCTION-123 → JUNCTION-124. At 44 psi **no** service node goes negative and
the minimum head at JUNCTION-123 is **120.88 psi**. At 45 psi, four nodes go
negative, and they are the four **highest-elevation nodes in the network**:

| Node | Elevation (ft) | Base demand (GPM) | Hops from JUNCTION-124 | n neg | min (psi) | First negative |
|---|---|---|---|---|---|---|
| JUNCTION-102 | 1094.1 | 102.10 | 5 | 15 | −96.984 | 75.0 h |
| JUNCTION-103 | 1031.7 | 0.76 | 4 | 14 | −69.972 | 75.0 h |
| JUNCTION-121 | 957.0 | 0.00 | 3 | 10 | −37.998 | 75.0 h |
| JUNCTION-122 | 957.0 | 1.52 | 2 | 10 | −37.998 | 75.0 h |

At 46 psi the same four nodes fail far more often (**117, 103, 61, 61**
timesteps) and starting at **34.0 h** instead of 75.0 h.

Causal chain, each link measured: (1) above ≈43 psi the valve opens, throughput
0 → 418 GPM at 44 psi → 861 GPM at 45 psi; (2) the diverted flow collapses
upstream head — minimum at JUNCTION-123 falls **120.88 → 44.82 psi**; (3) the
valve can no longer regulate and goes hydraulically **Open** (open fraction
0.000 → 0.016); (4) the upper zone at 957–1094 ft can no longer be lifted;
(5) failure is time-dependent because it needs a tank drawdown to co-occur.

JUNCTION-121 and JUNCTION-122 are exactly the upstream and downstream nodes of
**VALVE-178** — the two valves share the failing zone. That is why the bound could
not be assumed separable, and why E-P6-03c was run.

**VALVE-179 has essentially no leakage authority.** Across the whole safe range
38.0 → 44.7 psi, while throughput goes **0 → 751 GPM**: leakage moves only between
**84.699 and 84.786 GPM** (spread **0.087 GPM ≈ 0.10 %**); served demand
**constant at 891.41 GPM**; DSR **constant at 0.983337**; n<20 **constant at 386**.
The safe range is not narrow — it is **empty of benefit**.

### E-P6-03c — does the VALVE-179 bound survive joint action?

`src/validation/p6_s3c_zone_interaction.py` → `results/phase6/p6_s3c_zone_interaction.json`

Two designs, both **fixed before execution**:

1. A 2-D grid over (VALVE-179, VALVE-178) — the two valves sharing the failing
   zone — with VALVE-179 ∈ {40, 44, 44.7, 44.8, 45} psi and VALVE-178 ∈ {27.75,
   32, 37, 42, 46.25} psi (0.75× … 1.25× of its 37 psi nominal).
2. A worst-case-for-head test: all five responsive PRVs (173, 175, 176, 177, 178)
   simultaneously at 0.75×, 0.90× and 1.00× nominal, with VALVE-179 held at
   44.7 psi.

**Exact result (`VERIFIED_FACT`).** Of the **18** tested cases with VALVE-179 at or
below 44.7 psi, **all 18 produced zero negative service pressures**, including the
0.75× joint case. Every case with VALVE-179 at 45 psi failed **identically** — 49
negative node-timesteps at the same four nodes — regardless of VALVE-178's
setting. VALVE-178's setting moves mean leakage by about **±0.1 GPM** and changes
nothing else.

**Conclusion, with scope stated.** `VERIFIED_FACT` on the tested set: a per-valve
box constraint on VALVE-179 is sufficient and the cliff is governed by VALVE-179's
own setting essentially independently of VALVE-178. `HYPOTHESIS` — that this
separability holds over the **full** joint action space, including combinations not
covered by these two designs and including pump-speed variation. Not proved;
therefore the safety layer of STEP 9 must **detect the failure at runtime** rather
than rely on the box constraint alone.

**G5 verdict: RESOLVED.** Action space = **{VALVE-173, VALVE-175, VALVE-176,
VALVE-177, VALVE-178}**, five continuous actuators. No PRV deleted from the model.

---

## 4. Phase 6 STEP 4 — pump speed strategy

`src/validation/p6_s4_pump_strategy.py` → `results/phase6/p6_s4_pump_strategy.json`

**The four native rules, read from the file (`VERIFIED_FACT`).**

| Rule | Text as loaded | Effect |
|---|---|---|
| RULE-0 | `IF TANK TANK-130 LEVEL >= 4.8768 THEN PUMP PUMP-172 STATUS IS CLOSED PRIORITY 1` | shuts PUMP-172 when TANK-130 is full (16.0 ft) |
| RULE-1 | `IF TANK TANK-130 LEVEL <= 3.68808 THEN PUMP PUMP-172 STATUS IS OPEN PRIORITY 1` | reopens PUMP-172 when TANK-130 is low (12.1 ft) |
| RULE-3 | `IF TANK TANK-131 LEVEL >= 5.60832 THEN PUMP PUMP-170 STATUS IS CLOSED PRIORITY 1` | shuts PUMP-170 when TANK-131 is full (18.4 ft) |
| RULE-4 | `IF TANK TANK-131 LEVEL <= 4.69392 THEN PUMP PUMP-170 STATUS IS OPEN PRIORITY 1` | reopens PUMP-170 when TANK-131 is low (15.4 ft) |

The two `OPEN` actions are the ones that destroy a speed command; they are also
the **only** mechanism by which a shut pump ever restarts. That coupling is the
entire difficulty.

### E-P6-04a — validate the stepped-EPS harness before judging any option

- **Objective.** Prove the segmented loop reproduces a monolithic run **before**
  any option is measured on it, because the same loop will be the RL environment's
  `step()`.
- **Setup.** Native speed, no override at all; 1800 s segments; compare against the
  uninterrupted 96 h reference.
- **Three defects found and fixed (`VERIFIED_FACT`), each recorded because each
  produced plausible-looking wrong results.**

  | Defect | Symptom if left in | Fix |
  |---|---|---|
  | Pump status not carried across the segment boundary | Both pumps reset to the file's declared `Open` every step: **193/193** open states against the reference's **42/193**; TANK-130 draining to **7.659 ft** against 13.782 | carry `initial_status`, updated from each segment's final status |
  | Pattern time not advanced | Every segment replays the hour-0 demand multipliers. Verified at JUNCTION-0: without the fix all segments return **1.192 GPM**; with `pattern_start = k·1800` the monolithic sequence **1.192, 1.039, 0.894, 0.864, 0.826, 0.795, 0.917, 0.490** is reproduced exactly | set `options.time.pattern_start = t_elapsed` |
  | `wntr.metrics.expected_demand` called per segment | It builds from the model's own time index **and ignores `pattern_start` entirely**, so each 30-min segment returns hour-0 multipliers over one step. Measured: DSR **4.179**, served **1605.10 GPM**; after stitching, requested demand **1631 GPM** against the true **906.40** | compute requested demand **once** over the full horizon on the `pattern_start = 0` model — it is a property of the patterns and the absolute clock, not of how the solve was segmented |

- **Cadence decision (`DECISION`).** The stitched frame keeps the **1800 s**
  control cadence so every case is time-averaged over the same **193** instants as
  the monolithic reference. Segments additionally report at the **180 s** native
  rule cadence, but those interior rows are used **only** to detect rule firings;
  mixing them into the statistics would silently change the time-weighting. This
  matters: at 1800 s resolution Option A's speed realisation reads a clean
  **1.000**, and only the 180 s scan reveals that it is not.
- **Exact mechanism-check result.**

  | Quantity | Monolithic reference | Stepped, native speed | Relative difference |
  |---|---|---|---|
  | Mean service pressure | 94.78673 psi | 94.78831 psi | 1.5e-05 |
  | n node-timesteps < 20 psi | 386 | 386 | 0 |
  | n node-timesteps negative | 0 | 0 | 0 |
  | Leakage | 84.72988 GPM | 84.73060 GPM | 7.5e-06 |
  | Served demand | 891.41390 GPM | 891.41390 GPM | 3.6e-09 |
  | Requested demand | 906.39873 GPM | 906.39873 GPM | **0** |
  | DSR | 0.9833370 | 0.9833370 | 6.8e-09 |
  | PUMP-170 open fraction | 0.2176 | 0.2176 | 0 |
  | PUMP-172 open fraction | 0.3834 | 0.3834 | 0 |
  | TANK-130 final level | 13.782 ft | 13.784 ft | +0.002 ft |
  | TANK-131 final level | 16.874 ft | 16.844 ft | −0.030 ft |
  | Intra-step speed resets | — | **0** | — |

- **Conclusion.** `VERIFIED_FACT`: the stepping mechanism is sound. Pump duty
  cycles are identical, requested demand is exact, residual pressure and tank
  differences are at the level of the solver's own convergence tolerance. The
  STEP 11 environment may use this loop.

### E-P6-04b — the decisive semantic measurement

- **Question the 96 h runs cannot answer** (there pump state is confounded with
  demand pattern and tank trajectory): does
  `THEN PUMP p SETTING IS <speed>` reopen a pump whose status is `Closed`, as
  `THEN PUMP p STATUS IS OPEN` does?
- **Isolated setup.** PUMP-170 started `Closed`; TANK-131 forced to **10.0 ft** so
  RULE-4's condition is **already true at t = 0**; 6 h duration; 180 s reporting;
  leak instrument active; commanded speed **0.85**. The two arms differ **only** in
  the rule action text.
- **Exact result (`VERIFIED_FACT`).**

  | Arm | Open states | First open | Realised speed | Flow | TANK-131 |
  |---|---|---|---|---|---|
  | Native `STATUS IS OPEN` | **120 / 121** | 0.05 h | **1.0** — not 0.85 | 773.96 GPM | 10.000 → **12.653 ft** (refills) |
  | Option B `SETTING IS 0.85` | **0 / 121** | **never** | — | **0.00 GPM** | 10.000 → **8.433 ft** (drains) |

- **Conclusion.** `SETTING IS` writes the speed but does **not** reopen a shut
  pump. `STATUS IS OPEN` restores flow but **overwrites the speed with 1.0**.
  **Neither rule action gives both.** The problem cannot be solved by editing rule
  text, because the action that carries the speed command is the action the
  tank-refill logic depends on.

### E-P6-04c — Option B, measured and disqualified

- **Monolithic appearance.** Clean success: realisation rate **1.000** on both
  pumps, leakage **84.684 GPM**, tanks ending at **13.339** and **18.195 ft**, no
  warnings.
- **Stepped reality (`VERIFIED_FACT`).** Option B **does not complete**. Replayed
  segment by segment: by **k = 156 (t = 78.0 h)** TANK-131 is **empty at
  0.000 ft**, TANK-130 is at **3.406 ft**, and **both pumps are `Closed` with no
  mechanism to restart**. TANK-130 then falls 3.406 → 3.275 → 3.129 → 2.999 ft,
  and inside segment 159 (**t = 79.5 h**) EPANET reports:

  ```
  WARNING: System unbalanced at 0:18:00 hrs. EXECUTION HALTED.
  ```

- **Why this is not a harness defect.** Direct consequence of E-P6-04b: once the
  native `CLOSED` rules have fired, the rewritten `SETTING IS` rules cannot bring
  the pumps back, so the network drains until the solver cannot balance. The
  monolithic run completes only because it never enters a state requiring a closed
  pump to be reopened.
- **Significance.** An environment that can drive the simulator into an unbalanced
  halt part-way through an episode is not defensible: the episode cannot be
  completed, reward is **undefined** from that point onward, and the failure is
  **trajectory-dependent** rather than a function of the action bounds — so **no
  action-space clamp can prevent it**. **Option B is disqualified on evidence.**
- **Bonus.** This settles the brief's "silent rule removal ممنوع است" concern in
  the strongest available way: the rewrite was implemented, applied in memory,
  reported verbatim before and after, measured — and rejected.

### E-P6-04d — Option A: re-issue every control step

| Case | Speed hold rate at 180 s | Intra-step reset events | Open states off-command |
|---|---|---|---|
| `optionA_reissue_each_step` | **0.9862** | **5** | 35 |
| `optionA_control_command_first_step_only` | **0.0172** | 120 | 1254 |
| `mechanism_check_stepped_native` | — (no override) | **0** | 0 |

The control case is **not** "one command that decays": each segment is a fresh
model load, so `base_speed` reverts to the file's declared 1.0 whenever it is not
re-issued. What it demonstrates is sharper — **in this architecture a speed
command has a lifetime of exactly one control step and nothing more.** Hold rate
**1.72 %**.

Re-issuing raises the hold rate to **98.62 %**. The residual **1.38 %** is real and
is reported rather than rounded away — five events at which a native rule fired
*inside* a control step, re-opened the pump, and reverted the speed to 1.0 until
the next re-issue:

| Event | Control step | Pump | Interval lost |
|---|---|---|---|
| 1 | k = 58 | PUMP-172 | 29.10 – 29.50 h |
| 2 | k = 60 | PUMP-170 | 30.10 – 30.50 h |
| 3 | k = 112 | PUMP-170 | 56.30 – 56.50 h |
| 4 | k = 154 | PUMP-172 | 77.30 – 77.50 h |
| 5 | k = 159 | PUMP-170 | 79.70 – 80.00 h |

**`ASSUMPTION`, stated as such.** Option A does **not** achieve perfect actuator
authority and the environment must not claim that it does. The command is honoured
for **98.62 %** of pump-open time at 180 s resolution; in the remaining 1.38 % the
native tank-protection logic overrides the controller. That is correct engineering
behaviour — a safety interlock winning over a setpoint — but it must be
**observable**, which is why `info` will report commanded and realised speed
separately (brief §25).

**Cost of the re-issue, measured.** Both pumps run substantially more: PUMP-170
**101/193** open against the reference's **42/193**; PUMP-172 **129/193** against
**74/193** — because a pump genuinely held at 0.85 refills the tanks more slowly,
so the `CLOSED` rules fire later. Service outcomes unchanged: mean pressure
**94.719 psi**, n<20 = **386**, DSR **0.983337**, leakage **84.698 GPM**. TANK-131
ends **higher** (17.781 ft against 16.874). **No service metric degrades.**

### E-P6-04e — Option C

Option C — separating status and speed at the DRL abstraction level while leaving
native logic intact — is **not a distinct hydraulic experiment**. Its hydraulic
behaviour is exactly Option A's, so Option A's measurements are its evidence. The
difference is an interface property: the agent emits a **speed only**, status
remains entirely under native rule control, and the environment never issues a
status command.

This is the **only** defensible division given E-P6-04b: since `STATUS IS OPEN` is
the sole mechanism that restarts a shut pump, any agent authority over pump status
would either duplicate or fight the tank-protection rules. **The agent gets speed;
the rules keep status.**

### Option comparison against the brief's eight criteria

| Criterion | Option A (re-issue, rules intact) | Option B (rewrite rules) | Option C (A + interface separation) |
|---|---|---|---|
| **Benchmark fidelity** | High. Zero rules changed; stepped loop at native speed reproduces the reference to 1.5e-05 | **Broken.** Tank-level control logic no longer functions; the network drains | High. Identical to A |
| **Scientific defensibility** | Good. Every deviation from the command is counted and reported | **None.** Cannot complete a 96 h episode | **Best.** As A, plus an explicit stated division of authority |
| **Reproducibility** | Yes. Deterministic; three-part carry-forward fully specified | Irrelevant — halts | Yes. As A |
| **Implementation complexity** | Moderate: segmented EPS with three-part carry-forward | Low to write, but requires re-applying the rewrite every segment **and does not work** | Same as A; the separation is a naming discipline, not extra machinery |
| **Hidden actuator interference** | Measured, not hidden: **1.38 %** of open time, 5 events, all localised in time | Total — the pumps latch off permanently | Same residual as A, but *surfaced by construction* in `info` |
| **PPO suitability** | Good: fixed 193-step horizon, bounded continuous action, no episode-terminating simulator failure | **Unusable:** trajectory-dependent halt, reward undefined after t = 79.5 h | Good, and cleaner semantics — one continuous speed per pump, no discrete status head |
| **Effect on native tank-control logic** | **None.** Rules fire exactly as authored | **Destroys it** | **None** |
| **Interpretability** | Good | Poor — behaviour diverges from the benchmark for reasons unrelated to control | **Best.** "The agent sets speed; the rules protect the tanks" is a one-sentence auditable description |

**G12 verdict: RESOLVED. Primary strategy: Option C implemented on Option A's
mechanism.** Five implementation points, as they will be built in STEP 11:

1. Native rules, controls and topology **untouched** — no rule removed, rewritten
   or reordered.
2. The EPS advances in **1800 s** control-step segments, carrying forward tank
   levels, pump status, **and pattern time**.
3. At each control step the pump action is written to `base_speed` and
   **re-issued** (lifetime of a command is exactly one control step).
4. The agent commands **speed only**; status stays entirely with the native rules.
5. `info` reports **commanded and realised speed separately** at every step.

---

## 5. Planned experiments — not yet run

None of these has been started. `PLANNED` throughout.

| ID | Objective | Blocks on | Notes |
|---|---|---|---|
| **E-PL-06** | Sweep each of the five controlled PRVs to read its safe action domain off measurement | nothing | Brief §14: "DO NOT choose arbitrary actuator bounds." Method: as E-P6-03a, per valve, plus a joint check as E-P6-03c |
| **E-PL-07** | Compute the observation normalisation constants once over the training scenario set and freeze them | E-PL-06 | Brief §13, §21: deterministic, no future information, never observe true leak flow or location |
| **E-PL-08** | Measure the *scales* of the four reward terms — leakage, pressure violation, energy, actuator movement — **before** any weight is chosen | E-PL-07 | Brief §20: "اما ضرایب را با حدس انتخاب نکن." Weights are currently **not chosen** |
| **E-PL-08b** | Re-derive the pump energy/pressure relationship under the Option C mechanism | E-P6-04d | E-P5-S4 is contaminated by the non-persistence defect |
| **E-PL-09** | Verify the safety layer catches the VALVE-179-class failure at runtime, including combinations outside E-P6-03c's designs | E-PL-06 | Discharges the `HYPOTHESIS` left open by E-P6-03c |
| **E-PL-10** | Generate and separate demand-uncertainty scenario sets: train / validation / test / OOD, with recorded seeds and scenario IDs | E-PL-08 | Brief §26 |
| **E-PL-12** | The 16 mandated automated environment tests | `src/env/` exists | `tests/` is currently empty |
| **E-PL-13** | SB3 PPO **compatibility smoke test only** — a few hundred timesteps to prove the API wires up | `gymnasium`, `stable-baselines3`, `torch` installed | **Not a training run and not a result.** Brief §0 prohibition still in force |
| **E-PL-Nx** | The actual PPO training and baseline comparison experiments | Phase 6 frozen and reported | **Explicitly forbidden in Phase 6** |

### Constraints that any future experiment inherits

- Solver: `ACCURACY 1e-5`, `TRIALS 2000`, rule timestep 180 s, report timestep
  1800 s, set in code and **asserted**.
- Statistics over the **121** service junctions only.
- `C` and `α` of the leakage model **identical** between the RL agent and every
  baseline — changing them between arms invalidates the comparison.
- Evaluation **never** by scalarised reward; the weighted sum exists for training
  only.
- Report the pre-existing deficit floor (386 node-timesteps, min 4.1645 psi)
  alongside any service metric.
- Echo check every model write: write the `.inp` out, read it back, compare.
