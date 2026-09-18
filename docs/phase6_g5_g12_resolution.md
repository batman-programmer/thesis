# Phase 6 — Deliverable A: Resolution of the two Phase 5 CONDITIONAL gates

Adaptive Pressure Control in Water Distribution Networks Using Deep Reinforcement
Learning (DRL/PPO) Integrated with EPANET to Reduce Leakage Under Uncertain Demand

Network: BWSN Network 1. Phase 6, STEP 3 and STEP 4 of the work order.

---

## 0. What this document is, and what it is not

Phase 5 returned CONDITIONAL PASS. Nothing failed, but two gates were left
qualified, and both were qualified for the same reason: they concerned the
**action space**, not the hydraulics.

- **G5 (8-PRV action space) = CONDITIONAL.** Three of the eight PRVs solve to a
  Closed state in the distributed baseline, and one of them (VALVE-179) was
  found to drive service pressure to approximately −97 psi when its setting was
  raised to 1.25 × nominal. Phase 5 explicitly did not bracket that threshold
  more finely than the interval ×1.00 to ×1.25, and recorded that measurement as
  owed.
- **G12 (actuator realisability) = CONDITIONAL.** A commanded pump speed is
  transmitted and realised at the moment of issuance, but does not persist: the
  native rule action `THEN PUMP <p> STATUS IS OPEN` restores relative speed to
  ≈1.0 at every rule-driven reopening, discarding the command.

This document resolves both, on measurement. Every number below is produced by
the EPANET 2.x solver through WNTR 1.5.0 from the working copy, with the
benchmark topology, controls and rules untouched except in three explicitly
labelled diagnostic runs that are named as such wherever they appear.

It is **not** an optimisation study. No setting is recommended because it
performs well. The question throughout is the one the brief poses: *what is the
safe operational domain*, so that a DRL action space can be defined inside it.

Every claim carries exactly one label:

| Label | Meaning |
|---|---|
| **VALIDATED FACT** | Produced by the solver or read directly from the model file, in a run recorded in a Phase 5 or Phase 6 artefact. |
| **ENGINEERING DECISION** | A design choice made by the author. Defensible, but not forced by the evidence. |
| **RESEARCH ASSUMPTION** | Taken as given for this thesis without being proved here. |
| **HYPOTHESIS TO TEST** | Not yet established. Names the experiment that would settle it. |

---

## 1. Method and provenance

**VALIDATED FACT.** All Phase 6 STEP 3 runs use the working copy
`data/networks/working/BWSN_Network_1_working.inp`, derived from the distributed
`BWSN_Network_1.inp` (44 402 bytes, SHA-256
`510af942ec643eb87adcf26e5a7df1cc4c23eb0c1e470a8a1257ed055f1956f1`) by the single
patch `Quality Chemical TIME` → `Quality Chemical mg/L`, which is required for
WNTR 1.5.0 to parse the file and is hydraulically neutral because EPANET solves
hydraulics independently of the water-quality module and this thesis performs no
water-quality analysis.

**VALIDATED FACT.** Solver configuration, set explicitly on every model load and
asserted after the load in `assert_solver()`, per brief section 3:

| Option | Value | Why not the default |
|---|---|---|
| `ACCURACY` | `1e-5` | Phase 5 D6: at the file's shipped `0.005`, EPANET returns states violating the emitter law by 2.0135 GPM and continuity by 9.9692 GPM **while reporting zero errors and zero warnings**. |
| `TRIALS` | `2000` | Must rise with ACCURACY. At `1e-5` with 200 trials the leak-free run halts at 19:00 h with "System unbalanced". |
| rule timestep | `180 s` | The distributed `[TIMES]` declares none; native EPANET defaults to 1/10 of the hydraulic timestep = 180 s, whereas WNTR's own default is 360 s. An unpatched WNTR run evaluates the tank-level pump rules at half the native frequency. |
| report timestep | `1800 s` | Output resolution only. Does not change the solution. |
| demand model | `PDA`, required 20 psi, minimum 0 psi, exponent 0.5 | Carried from Phase 5 G7. |

The Phase 5 module `src/validation/g4_g5_prv.py` did **not** set accuracy or
trials, and therefore inherited the file's `0.005 / 40`. Its snapshot harness is
deliberately **not** reused here. This is a correction to the instrument, not to
a result: the Phase 5 G4/G5 *classification* conclusions are unaffected, because
they turn on whether a valve responds at all, but no numeric value from that
harness is carried into Phase 6.

**VALIDATED FACT.** Service statistics are computed over the **121
service-bearing junctions only**. Five junctions — JUNCTION-105, -106, -109,
-110, -128 — are excluded by a rule derived from the model's own declared
properties (declared elevation exactly 0.0 ft **and** zero total base demand),
not by a hard-coded list. Justification, measured: the next lowest elevation in
the file is 192.0 ft, all five have degree two, and each is an endpoint of a pump
or of the reservoir connector pipe, so elevation 0 is a datum placeholder and
EPANET's reported "pressure" there is head above datum with no service meaning.
In the reference run JUNCTION-106 reads **501.6 psi**. Including the five raises
the reported mean network pressure from **94.787 psi to 101.49 psi** — a 6.7 psi
artefact that would silently inflate every pressure statistic and every
pressure-based reward term.

**VALIDATED FACT.** The leakage instrument is the Phase 5 one, recomputed here by
the identical closed form from the identical baseline: half of each incident
pipe's length assigned to each junction, one global scale
`k = target / Σ_j (w_j · p_j^α)` evaluated once with no iteration and no search,
α = 0.5 taken from the file's own `[OPTIONS] Emitter Exponent`, target = 10 % of
the mean system inflow of the leak-free baseline. **RESEARCH ASSUMPTION**, stated
as the brief's section 18 requires: this is a *validation instrument*, not a
field-calibrated leakage model. It is not calibrated against any measurement from
the BWSN-1 system, no such measurement is known to the author to exist, and no
result in this thesis may be presented as a calibrated leakage estimate.

Artefacts: `results/phase6/p6_s3_prv_finechar.json`,
`p6_s3b_v179_refine.json`, `p6_s3c_zone_interaction.json`. Code:
`src/validation/p6_s3_prv_finechar.py`, `p6_s3b_v179_refine.py`,
`p6_s3c_zone_interaction.py`.

---

## 2. Reference state: what "no change" looks like

**VALIDATED FACT.** All eight PRVs at their nominal settings, leakage instrument
active, PDA, 96 h EPS, 193 reporting timesteps:

| Quantity | Value |
|---|---|
| Mean service pressure (121 junctions) | 94.787 psi |
| Minimum service pressure | 4.165 psi, at JUNCTION-29 |
| Node-timesteps below 20 psi | 386 |
| Node-timesteps at negative pressure | 0 |
| Mean leakage | 84.730 GPM |
| Mean served demand | 891.414 GPM |
| Mean unserved demand | 14.985 GPM |
| Mean DSR | 0.983337 |
| Mean pressure deficit | 18.14 psi·nodes |
| Max relative continuity residual | 1.4 × 10⁻⁵ |

Two points that matter for reward design later: the baseline is **already in
service deficit** (386 node-timesteps below the 20 psi threshold, DSR 0.9833),
and it contains **no** negative pressure. Any negative pressure observed in this
document is therefore caused by the perturbation under test, not inherited.

---

## 3. A correction to the premise: what "nominally Closed" means

**VALIDATED FACT.** The brief's section 5 lists nominal states as 173 Active,
174 **Closed**, 175 Active, 176 Active, 177 Active, 178 Active, 179 **Closed**,
180 **Closed**. That is an accurate description of the *solved* states. It is not
a description of the file.

Read directly from `[VALVES]` in the working copy, **all eight PRVs are declared
`Active`** with settings 70, 80, 55, 29.762, 45, 37, 40, 16.45 psi. The Closed
states of 174, 179 and 180 are outcomes, and they have **two different causes**:

| PRV | Cause of the Closed state | Evidence |
|---|---|---|
| VALVE-174, VALVE-179 | Hydraulic. EPANET shuts a PRV against reverse flow when its setting is below what the downstream node already sits at. | Declared `Active` in `[VALVES]`; solves to Closed; reopens when the setting is raised (see §4, §5). |
| VALVE-180 | **An explicit control statement.** `[CONTROLS]` contains exactly one line: `LINK VALVE-180 Closed At Time 0.000000`. | Read from the file; echoed back after write as `Valve VALVE-180 Closed AT TIME 0`; confirmed by the release diagnostic in §6. |

This distinction was not stated in Phase 5 and it changes the reasoning for one
of the three valves. VALVE-180 is not a valve with no authority — it is a valve
the benchmark **commands** shut. Treating the two causes as one would have led to
the wrong conclusion about it.

---

## 4. VALVE-179: the safety cliff, bracketed and explained

### 4.1 The 1 psi bracket

**VALIDATED FACT.** Sweep of VALVE-179 alone, all other PRVs nominal, leakage on,
PDA, full 96 h EPS per setting (`p6_s3_prv_finechar.json`). Nominal is 40 psi.

| Setting (psi) | ×nominal | Active/Open/Closed | q̄ (GPM) | q_max (GPM) | min P (psi) | n<20 psi | n negative | leak (GPM) | served (GPM) | DSR |
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

The 50 psi row reproduces Phase 5's −97.086 psi at ×1.25 exactly, and the brief's
description of VALVE-179 (nominal 40, transition at 50, minimum ≈ −97 psi) is
confirmed against the artefacts. But the brief's picture was coarse in one
important way: **the transition is not at 50 psi. It is at 45 psi, and the valve
begins to open at 43.**

### 4.2 The 0.1 psi refinement

**VALIDATED FACT.** `p6_s3b_v179_refine.json`, 0.1 psi steps across the cliff:

| Setting (psi) | Active | Open | Closed | q̄ (GPM) | min P (psi) | n<20 psi | n negative | leak (GPM) | served (GPM) | DSR |
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

Three boundaries, all measured, all distinct — and the distinction matters:

| Boundary | Value | Definition |
|---|---|---|
| Last **fully clean** setting | **44.7 psi** (1.1175 × nominal) | Every service statistic identical to the reference: n<20 = 386, DSR = 0.983337. |
| Last **non-negative** setting | 44.8 psi | No negative pressure, but service has already begun to degrade: n<20 rises to 423, DSR falls to 0.983178. |
| First **failing** setting | 44.9 psi | 18 negative node-timesteps, minimum −96.981 psi. |

**ENGINEERING DECISION.** The action bound is placed at **44.7 psi**, the last
fully clean setting, not at 44.8. Rationale: 44.8 is already outside the
reference service envelope, and the 0.1 psi margin between 44.8 and the first
failure is smaller than any resolution at which a physical PRV could be
commanded. Choosing the last setting with *no* measurable service degradation
buys a 0.2 psi margin to the cliff at a cost of 39 GPM of valve throughput,
which §4.4 shows is worth almost nothing in leakage terms.

### 4.3 The mechanism: this is not a VALVE-179 problem

**VALIDATED FACT.** For each setting in {44, 45, 46} psi, the identity, elevation
and timing of every service node that goes negative (`p6_s3b_v179_refine.json`,
`mechanism`). VALVE-179 runs JUNCTION-123 → JUNCTION-124.

At 44 psi: **no** service node ever goes negative; head at the valve's upstream
node JUNCTION-123 has a minimum of **120.88 psi**.

At 45 psi, four nodes go negative — and they are the four **highest-elevation
nodes in the network**:

| Node | Elevation (ft) | Base demand (GPM) | Hops from JUNCTION-124 | n negative | min (psi) | First negative |
|---|---|---|---|---|---|---|
| JUNCTION-102 | 1094.1 | 102.10 | 5 | 15 | −96.984 | 75.0 h |
| JUNCTION-103 | 1031.7 | 0.76 | 4 | 14 | −69.972 | 75.0 h |
| JUNCTION-121 | 957.0 | 0.00 | 3 | 10 | −37.998 | 75.0 h |
| JUNCTION-122 | 957.0 | 1.52 | 2 | 10 | −37.998 | 75.0 h |

At 46 psi the same four nodes fail, but far more often (117, 103, 61, 61
timesteps) and starting at **34.0 h** instead of 75.0 h.

The causal chain, each link measured:

1. Raising VALVE-179's setting above ≈43 psi lets it open; throughput rises from
   0 GPM to 418 GPM at 44 psi and 861 GPM at 45 psi.
2. That diverted flow collapses the head available upstream of the valve: the
   minimum pressure at JUNCTION-123 falls from **120.88 psi at 44 psi** to
   **44.82 psi at 45 psi**.
3. At that point the valve can no longer regulate — its setting exceeds what the
   upstream head can produce — so it goes hydraulically **Open** (open fraction
   0.000 → 0.016) and stops holding its downstream node.
4. The upper pressure zone, whose nodes sit at 957–1094 ft, can no longer be
   lifted, and its pressures go negative.
5. The failure is time-dependent because it needs a tank drawdown to co-occur:
   at 45 psi it appears only after 75 h; at 46 psi, after 34 h.

**This is an elevation-driven loss of available head in the upper pressure zone,
not a valve-authority defect.** Note in particular that JUNCTION-121 and
JUNCTION-122 are exactly the upstream and downstream nodes of **VALVE-178** —
the two valves share the failing zone. That observation is what motivated the
joint test in §4.5, and it is the reason a per-valve bound could not simply be
assumed valid.

**A note on what "negative pressure" means here.** EPANET reports it; it is not a
physical state. A real network would cavitate, draw in contaminants, or separate
the column. Phase 5 established that the emitter law EPANET applies at negative
pressure is the *signed* form `q = sign(p)·C·|p|^0.5`, so an emitter at negative
pressure flows **backwards** — the leakage instrument reports water entering the
network. Any state with negative service pressure is therefore both physically
meaningless and numerically corrupting to the leakage accounting. It must be
excluded by construction, not merely penalised. This is the central argument for
§9's safety layer.

### 4.4 VALVE-179 has essentially no leakage authority

**VALIDATED FACT.** Across the entire safe range 38.0 → 44.7 psi, while
VALVE-179's mean throughput goes from **0 to 751 GPM**:

- mean leakage moves between **84.699 and 84.786 GPM** — a spread of **0.087
  GPM, about 0.10 %** of the 84.730 GPM reference;
- served demand is **constant at 891.41 GPM**;
- DSR is **constant at 0.983337**;
- node-timesteps below 20 psi are **constant at 386**.

**This is the decisive finding for VALVE-179.** Within its safe domain the valve
changes nothing that the thesis's objective function measures. Outside its safe
domain it destroys service: 45 psi costs 15.94 GPM of served demand and produces
49 physically meaningless node-states. Its measured risk/benefit ratio is
therefore extremely unfavourable — **not** because the safe range is narrow, but
because the safe range is *empty of benefit*.

### 4.5 Does the bound survive joint action?

A per-valve bound measured with every other valve at nominal is only sound if it
survives the other valves moving. A DRL agent emits all PRV settings at once, so
this was tested rather than assumed (`p6_s3c_zone_interaction.json`).

**VALIDATED FACT.** Two designs, both fixed before execution:

1. A 2-D grid over (VALVE-179, VALVE-178) — the two valves sharing the failing
   zone — with VALVE-179 ∈ {40, 44, 44.7, 44.8, 45} psi and VALVE-178 ∈ {27.75,
   32, 37, 42, 46.25} psi, i.e. 0.75× to 1.25× of VALVE-178's 37 psi nominal.
2. A worst-case-for-head test: all five PRVs Phase 5 found responsive (173, 175,
   176, 177, 178) simultaneously at 0.75×, 0.90× and 1.00× nominal, with
   VALVE-179 held at its per-valve bound of 44.7 psi.

Result: of the **18 tested cases with VALVE-179 at or below 44.7 psi, all 18
produced zero negative service pressures**, including the 0.75× joint case. Every
case with VALVE-179 at 45 psi failed identically — 49 negative node-timesteps at
the same four nodes — regardless of VALVE-178's setting. VALVE-178's setting
moves mean leakage by about ±0.1 GPM and changes nothing else.

**VALIDATED FACT, with its scope stated.** On the tested set, a per-valve box
constraint on VALVE-179 is sufficient, and the cliff is governed by VALVE-179's
own setting essentially independently of VALVE-178. **HYPOTHESIS TO TEST:** that
separability holds over the *full* joint action space, including combinations not
covered by these two designs and including pump-speed variation. This is not
proved, and the safety layer of §9 is therefore designed to detect the failure at
runtime rather than to rely on the box constraint alone.

---

## 5. VALVE-174: reopens, but its only measured effect is more leakage

**VALIDATED FACT.** Sweep of VALVE-174 alone, nominal 80 psi
(`p6_s3_prv_finechar.json`):

| Setting (psi) | ×nominal | Active/Open/Closed | q̄ (GPM) | mean P (psi) | min P (psi) | n<20 psi | leak (GPM) | served (GPM) | DSR |
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
| 110 | 1.375 | 1.000/0.000/0.000 | 4.96 | 95.742 | 4.164 | 386 | 84.968 | 891.41 | 0.983337 |

**VALIDATED FACT.** The reopening threshold is bracketed between **95 and 96
psi** (1.188–1.200 × nominal). Above it the valve is Active 100 % of the horizon
— it regulates cleanly, with no instability and no negative pressure anywhere up
to 110 psi. So VALVE-174 is *not* inert, and Phase 5's refusal to delete it
unexamined was correct.

But the authority it has is not useful authority:

- throughput is **4.7 to 5.0 GPM**, against a total system demand of ≈944.7 GPM
  — about **0.5 %**;
- served demand is **unchanged to six decimal places** at every setting;
- node-timesteps below 20 psi are **unchanged at 386**;
- the only quantity that moves monotonically is **leakage, upward**: 84.730 →
  84.968 GPM as the setting rises, because raising the setting raises mean
  network pressure (94.787 → 95.742 psi) and leakage is an increasing function of
  pressure.

**VALIDATED FACT.** VALVE-174's entire measured effect within its reopenable
range is to **increase leakage with no service benefit**. Under any reward that
penalises leakage, the optimal policy for this valve is the one the benchmark
already implements: leave it shut.

---

## 6. VALVE-180: commanded shut by the benchmark, and it matters

### 6.1 With the benchmark control in place

**VALIDATED FACT.** VALVE-180 is `Closed` for **100 % of the horizon at every
setting tested from 16.45 to 120 psi** (up to 7.3 × nominal), with zero flow and
every service statistic bit-identical to the reference. This is not weak
authority. It is the `[CONTROLS]` statement `LINK VALVE-180 Closed At Time 0`
overriding the PRV entirely — no setting can reopen it.

### 6.2 With the control released (diagnostic only)

**VALIDATED FACT.** Three runs with that one control statement removed, reported
as a diagnostic and **not** adopted anywhere:

| Setting (psi) | Active | q̄ (GPM) | mean P (psi) | n<20 psi | n negative | leak (GPM) | served (GPM) | DSR | deficit |
|---|---|---|---|---|---|---|---|---|---|
| 16.45 | 0.000 | 0.00 | 94.787 | 386 | 0 | 84.730 | 891.41 | 0.983337 | 18.14 |
| 40 | 1.000 | 273.02 | 95.175 | **193** | 0 | 85.803 | **906.46** | **1.00016** | 14.88 |
| 80 | 1.000 | 274.34 | 95.834 | **193** | 0 | 87.118 | 906.46 | 1.00016 | 14.89 |

At its nominal 16.45 psi the valve stays Closed even with the control removed —
the setting is below the downstream pressure, so EPANET shuts it hydraulically.
At 40 psi it carries 273 GPM and the effect is substantial: **node-timesteps
below 20 psi halve, 386 → 193**, served demand rises to 906.46 GPM, and DSR
reaches 1.0002 (marginally above 1 because the reported-minus-modelled leakage
decomposition leaves a small residual at full service; the value means "no
unserved demand", not "more than requested").

**VALIDATED FACT.** Roughly **half of the baseline pressure deficit of BWSN-1 is
downstream of a valve the benchmark deliberately commands shut**, and it can be
removed by opening that valve, at a cost of 1.07 GPM more leakage (84.730 →
85.803).

### 6.3 Why this must not be exploited

**ENGINEERING DECISION.** VALVE-180's `[CONTROLS]` closure is **retained**, and
VALVE-180 is **excluded from the action space**.

The reasoning is a scope-and-comparability argument, and it deserves to be
explicit because the temptation runs the other way — releasing this control is
the single largest service improvement available anywhere in this study, and it
would flatter any agent that was allowed to do it:

1. **It is a scenario definition, not a defect.** A modeller wrote a control
   statement to close this valve at t=0. That defines the benchmark's operating
   scenario. Removing it changes the problem, not the solution.
2. **It would destroy comparability.** Every Phase 5 baseline, and any published
   BWSN-1 result, is computed with that control in force. An agent permitted to
   release it would show a large improvement attributable entirely to the
   scenario change, and the comparison to the native-controls baseline would be
   meaningless.
3. **The brief forbids it.** Section 4: "اصل benchmark topology و actuator
   topology نباید تغییر کند." Section 30 lists silent removal of native rules as
   prohibited. A control statement is native control logic.
4. **It is not silently discarded.** It is measured, reported here, and recorded
   in §10 as a bounded observation about the benchmark. **HYPOTHESIS TO TEST**,
   for future work outside this thesis's approved scope: whether BWSN-1's
   baseline service deficit is an intentional feature of the benchmark scenario
   or an artefact of its construction. Settling that needs the BWSN-1 problem
   statement, which the author has not obtained; Phase 5 recorded the same
   UNKNOWN for the question of whether BWSN-1 declares a service pressure
   threshold at all.

---

## 7. G5 resolution: the required table

**The action space is finalized as five PRVs.** Required table, brief section 7:

| PRV | Nominal state | Tested authority | Safe action domain | RL-controlled? | Reason |
|---|---|---|---|---|---|
| **VALVE-173** | Active, 70 psi | Responsive (Phase 5 G4) | To be set in STEP 5/6 from measured response | **Yes** | Active, responsive, no unsafe region found in the Phase 5 sweep. |
| **VALVE-174** | Closed (hydraulic) at 80 psi | Reopens 95→96 psi; Active 100 % above it; **4.7–5.0 GPM, ≈0.5 % of demand** | Fixed at nominal 80 psi | **No** | Reopening raises mean pressure and therefore **leakage** (84.730 → 84.968 GPM) with **zero** measured change in served demand or pressure-deficit count. Its only measured effect is adverse. Not removed from the model; simply not actuated. |
| **VALVE-175** | Active, 55 psi | Responsive (Phase 5 G4) | To be set in STEP 5/6 | **Yes** | As VALVE-173. |
| **VALVE-176** | Active, 29.762 psi | Responsive (Phase 5 G4) | To be set in STEP 5/6 | **Yes** | As VALVE-173. |
| **VALVE-177** | Active, 45 psi | Responsive (Phase 5 G4) | To be set in STEP 5/6 | **Yes** | As VALVE-173. |
| **VALVE-178** | Active, 37 psi | Responsive; ±0.1 GPM leakage over 0.75–1.25× | To be set in STEP 5/6 | **Yes** | Active and responsive. Shares the upper zone with VALVE-179; its own perturbation never produced negative pressure in the §4.5 grid. |
| **VALVE-179** | Closed (hydraulic) at 40 psi | Opens at 43; **cliff between 44.8 and 44.9 psi**; safe range carries 0–751 GPM but moves leakage by only **0.087 GPM (0.10 %)**; beyond it, −97 psi and DSR 0.983 → 0.970 | **Fixed at nominal 40 psi**, hard-clamped ≤ 44.7 psi if ever actuated | **No** | Empty benefit, severe downside. Within the safe domain it changes **no** metric the objective measures; 0.2 psi beyond it, four highest-elevation nodes reach −97 psi and 15.9 GPM of served demand is lost. The brief's instruction — "DO NOT expose unconstrained continuous action over VALVE-179" — is satisfied in its strongest form: no action at all. |
| **VALVE-180** | Closed by `[CONTROLS]` at 16.45 psi | **Zero at every setting to 120 psi** while the control holds; with the control released at 40 psi it carries 273 GPM and halves n<20 (386 → 193) | Not actuated; `[CONTROLS]` closure retained | **No** | Its closure is a benchmark scenario decision, not an authority limit. Releasing it is the largest single service gain available and would destroy comparability with every baseline. Retained as-is; the finding is recorded, not exploited. |

**Result: RL-controlled PRVs = {VALVE-173, VALVE-175, VALVE-176, VALVE-177,
VALVE-178}, five continuous actuators.** This is exactly the "more responsive"
set the brief's section 5 anticipated, but it is now reached from measurement
rather than from the nominal-state listing — including the finding that the two
excluded hydraulically-closed valves are excluded for *opposite* reasons
(VALVE-174 has benign but adverse authority; VALVE-179 has catastrophic
authority).

**G5 verdict: RESOLVED.** The Phase 5 CONDITIONAL is discharged. The action space
is five PRVs; each of the three exclusions rests on a measured quantity, not on
convenience; no PRV was deleted from the model; and the owed VALVE-179 bracket is
now 0.1 psi rather than the ×1.00–×1.25 interval Phase 5 left open.

---

# Part II — G12: pump speed command persistence

## 8. What Phase 5 established, and what it left open

Phase 5 G12 was closed as **CONDITIONAL** on a three-part finding, restated here
as the brief's section 8 requires and **not re-derived**:

| Layer | Phase 5 verdict |
|---|---|
| Transmission — does the speed reach the INP file? | **Correct.** |
| Realisation at issuance — does EPANET apply it? | **Correct.** |
| Long-term persistence — does it hold for the horizon? | **NOT correct.** |

The attributed cause: a native rule action `THEN PUMP <p> STATUS IS OPEN`
restores the pump's relative speed to ≈1.0, discarding the commanded value.

Phase 6 reproduces this under the mandated solver settings (ACCURACY 1e-5,
TRIALS 2000, rule timestep 180 s) and the 121-node service metric, then answers
the question Phase 5 did not: **what should the environment do about it?**

`command_once_monolithic` — speed 0.85 commanded once, one uninterrupted 96 h
EPS — reproduces the defect exactly:

| Pump | Open states | Realised speeds while open | Fraction at the command |
|---|---|---|---|
| PUMP-170 | 52 / 193 | {0.85, 1.0} | **0.3654** |
| PUMP-172 | 83 / 193 | {0.85, 1.0} | **0.2771** |

**VALIDATED FACT.** Roughly two thirds of the pumps' operating time is spent at a
speed the controller did not ask for.

## 9. The rules involved, read from the file

| Rule | Text (as loaded) | Effect |
|---|---|---|
| RULE-0 | `IF TANK TANK-130 LEVEL >= 4.8768 THEN PUMP PUMP-172 STATUS IS CLOSED PRIORITY 1` | shuts PUMP-172 when TANK-130 is full (16.0 ft) |
| RULE-1 | `IF TANK TANK-130 LEVEL <= 3.68808 THEN PUMP PUMP-172 STATUS IS OPEN PRIORITY 1` | reopens PUMP-172 when TANK-130 is low (12.1 ft) |
| RULE-3 | `IF TANK TANK-131 LEVEL >= 5.60832 THEN PUMP PUMP-170 STATUS IS CLOSED PRIORITY 1` | shuts PUMP-170 when TANK-131 is full (18.4 ft) |
| RULE-4 | `IF TANK TANK-131 LEVEL <= 4.69392 THEN PUMP PUMP-170 STATUS IS OPEN PRIORITY 1` | reopens PUMP-170 when TANK-131 is low (15.4 ft) |

These four rules are the network's entire tank-level control logic. The two
`OPEN` actions are the ones that destroy the speed command; they are also the
only mechanism by which a shut pump ever restarts. **That coupling is the whole
difficulty**, and it is what §11 measures.

## 10. The stepped architecture, and why it had to be validated first

Options A and C both require advancing the EPS in control-step segments so that
a command can be re-issued. That loop is also what the STEP 11 environment will
use, so an error in it would contaminate every later number. It is therefore
validated before any option is judged, by running it at the **native** speed with
no override at all and requiring it to reproduce the uninterrupted reference.

Three defects were found and fixed in the course of that validation. Each is
recorded because each would have produced plausible-looking but wrong results,
and because the STEP 11 environment must not reintroduce them.

| Defect | Symptom if left in | Fix |
|---|---|---|
| Pump status not carried across the segment boundary | Both pumps reset to the file's declared `Open` every step: **193/193** open states against the reference's 42/193, TANK-130 draining to **7.659 ft** against 13.782 | carry `initial_status`, updated from each segment's final status |
| Pattern time not advanced | Every segment replays the hour-0 demand multipliers. Verified at JUNCTION-0: without the fix all segments return **1.192 GPM**; with `pattern_start = k·1800` the monolithic sequence 1.192, 1.039, 0.894, 0.864, 0.826, 0.795, 0.917, 0.490 is reproduced exactly | set `options.time.pattern_start = t_elapsed` |
| `wntr.metrics.expected_demand` called per segment | It builds from the model's own time index **and ignores `pattern_start` entirely**, so each 30-min segment returns hour-0 multipliers over one step. Measured: DSR **4.179**, served **1605.10 GPM**; then, after stitching, requested demand **1631 GPM** against the true 906.40 | compute requested demand once over the full horizon on the `pattern_start = 0` model — it is a property of the patterns and the absolute clock, not of how the solve was segmented |

**ENGINEERING DECISION.** The stitched frame keeps the **1800 s control cadence**
so that every case is time-averaged over the same 193 instants as the monolithic
reference. Segments additionally report at the **180 s native rule cadence**, but
those interior rows are used only to detect rule firings; mixing them into the
statistics would silently change the time-weighting. This distinction matters:
at 1800 s resolution Option A's speed realisation reads a clean 1.000, and only
the 180 s scan reveals that it is not.

### Mechanism check result

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

**VALIDATED FACT: the stepping mechanism is sound.** Pump duty cycles are
identical to the state, requested demand is exact, and the residual pressure and
tank differences are at the level of the solver's own convergence tolerance. The
STEP 11 environment may use this loop.

## 11. The decisive semantic measurement

Every option turns on one question that the 96 h runs cannot answer, because
there pump state is confounded with the demand pattern and the tank trajectory:

> Does `THEN PUMP p SETTING IS <speed>` reopen a pump whose status is `Closed`,
> as `THEN PUMP p STATUS IS OPEN` does?

Isolated test: PUMP-170 started `Closed`, TANK-131 forced to 10.0 ft so RULE-4's
condition is **already true at t = 0**, 6 h duration, 180 s reporting, leak
instrument active, commanded speed 0.85. The two arms differ only in the rule
action text.

| Arm | Open states | First open | Realised speed | Flow | TANK-131 |
|---|---|---|---|---|---|
| Native `STATUS IS OPEN` | **120 / 121** | 0.05 h | **1.0** — not 0.85 | 773.96 GPM | 10.000 → **12.653 ft** (refills) |
| Option B `SETTING IS 0.85` | **0 / 121** | **never** | — | **0.00 GPM** | 10.000 → **8.433 ft** (drains) |

**VALIDATED FACT.** `SETTING IS` writes the speed but does **not** reopen a shut
pump. `STATUS IS OPEN` restores flow but overwrites the speed with 1.0.

**Neither rule action gives both.** This is the finding that decides STEP 4: the
problem cannot be solved by editing the rule text, because the same action that
carries the speed command is the action the tank-refill logic depends on.

## 12. Option B fails, and the failure is the measurement

Monolithically, Option B looks like a clean success — realisation rate 1.000 on
both pumps, leakage 84.684 GPM, tanks ending at 13.339 and 18.195 ft, no
warnings. That appearance is misleading, and the stepped run shows why.

In the stepped architecture Option B **does not complete**. Replayed segment by
segment: by k = 156 (t = 78.0 h) TANK-131 is **empty at 0.000 ft**, TANK-130 is
at 3.406 ft, and both pumps are `Closed` with no mechanism to restart. TANK-130
then falls 3.406 → 3.275 → 3.129 → 2.999 ft, and inside segment 159
(**t = 79.5 h**) EPANET reports:

```
WARNING: System unbalanced at 0:18:00 hrs. EXECUTION HALTED.
```

**This is not a harness defect.** It is the direct consequence of §11: once the
native `CLOSED` rules have fired, the rewritten `SETTING IS` rules cannot bring
the pumps back, so the network drains until the solver cannot balance. The
monolithic run completes only because it never enters a state requiring a closed
pump to be reopened.

**Significance for the environment.** An environment that can drive the simulator
into an unbalanced halt part-way through an episode is not defensible: the
episode cannot be completed, the reward is undefined from that point onward, and
the failure is *trajectory-dependent* rather than a function of the action
bounds — so no action-space clamp can prevent it. **Option B is disqualified.**

This also settles the brief's "silent rule removal ممنوع است" concern in the
strongest available way: the rule rewrite was implemented, applied in memory,
reported verbatim before and after, measured — and rejected on evidence.

## 13. What Option A actually delivers

Option A leaves every native rule untouched and re-issues the speed command at
each 30-min control step.

| Case | Speed hold rate at 180 s | Intra-step reset events | Open states off-command |
|---|---|---|---|
| `optionA_reissue_each_step` | **0.9862** | **5** | 35 |
| `optionA_control_command_first_step_only` | **0.0172** | 120 | 1254 |
| `mechanism_check_stepped_native` | — (no override) | **0** | 0 |

The control case is worth stating precisely, because it is easy to misread. It is
**not** "one command that decays": each segment is a fresh model load, so
`base_speed` reverts to the file's declared 1.0 whenever it is not re-issued.
What it demonstrates is therefore sharper — **in this architecture a speed
command has a lifetime of exactly one control step and nothing more.** Hold rate
1.72 %.

Re-issuing raises the hold rate to **98.62 %**. The residual 1.38 % is real and
is reported rather than rounded away: five events at which a native rule fired
*inside* a control step, re-opened the pump, and reverted the speed to 1.0 until
the next re-issue.

| Event | Control step | Pump | Interval lost |
|---|---|---|---|
| 1 | k = 58 | PUMP-172 | 29.10 – 29.50 h |
| 2 | k = 60 | PUMP-170 | 30.10 – 30.50 h |
| 3 | k = 112 | PUMP-170 | 56.30 – 56.50 h |
| 4 | k = 154 | PUMP-172 | 77.30 – 77.50 h |
| 5 | k = 159 | PUMP-170 | 79.70 – 80.00 h |

**RESEARCH ASSUMPTION, stated as such.** Option A does not achieve perfect
actuator authority, and the environment must not claim that it does. The command
is honoured for 98.62 % of pump-open time at the 180 s resolution; in the
remaining 1.38 % the native tank-protection logic overrides the controller. This
is the correct engineering behaviour — a safety interlock winning over a setpoint
— but it must be **observable**, not hidden, which is why `info` will report
commanded and realised speed separately (brief §25) and why the residual is
recorded here as a property of the environment rather than an implementation bug.

Cost of the re-issue, measured: both pumps run substantially more
(PUMP-170 101/193 open against the reference's 42/193; PUMP-172 129/193 against
74/193), because a pump genuinely held at 0.85 refills the tanks more slowly and
so the `CLOSED` rules fire later. Service outcomes are unchanged (mean pressure
94.719 psi, n<20 = 386, DSR 0.983337, leakage 84.698 GPM). TANK-131 ends higher
(17.781 ft against 16.874). **No service metric degrades.**

## 14. Option C

Option C — separating status and speed at the DRL abstraction level while leaving
native logic intact — is **not a distinct hydraulic experiment.** Its hydraulic
behaviour is exactly Option A's, so Option A's measurements are its evidence. The
difference is an interface property: the agent emits a *speed* only, status
remains entirely under native rule control, and the environment never issues a
status command.

Phase 6 adopts that interface property, and it is worth being explicit that this
is the *only* defensible division given §11. Since `STATUS IS OPEN` is the sole
mechanism that restarts a shut pump, any agent authority over pump status would
either duplicate or fight the tank-protection rules. **The agent gets speed; the
rules keep status.**

## 15. Option comparison against the brief's eight criteria

Brief §9 names eight criteria. Each is answered from the measurements above.

| Criterion | Option A (re-issue, rules intact) | Option B (rewrite rules) | Option C (A + interface separation) |
|---|---|---|---|
| **Benchmark fidelity** | **High.** Zero rules changed; the stepped loop at native speed reproduces the reference to 1.5e-05 | **Broken.** The tank-level control logic no longer functions; the network drains | **High.** Identical to A |
| **Scientific defensibility** | **Good.** Every deviation from the command is counted and reported | **None.** Cannot complete a 96 h episode | **Best.** As A, plus an explicit, stated division of authority between agent and native logic |
| **Reproducibility** | **Yes.** Deterministic; carry-forward of tank level, pump status and pattern time fully specified | Irrelevant — halts | **Yes.** As A |
| **Implementation complexity** | Moderate: segmented EPS with three-part state carry-forward | Low to write, but requires re-applying the rewrite every segment **and does not work** | Same as A; the separation is a naming discipline, not extra machinery |
| **Hidden actuator interference** | **Measured, not hidden: 1.38 % of open time, 5 events, all localised in time** | Total — the pumps latch off permanently | Same residual as A, but *surfaced by construction* in `info` |
| **PPO suitability** | Good: fixed 193-step horizon, bounded continuous action, no episode-terminating simulator failure | **Unusable:** trajectory-dependent halt, undefined reward after t = 79.5 h | Good, and the action semantics are cleaner — one continuous speed per pump, no discrete status head |
| **Effect on native tank-control logic** | **None.** Rules fire exactly as authored | **Destroys it** (§11, §12) | **None** |
| **Interpretability** | Good | Poor — behaviour diverges from the benchmark for reasons unrelated to control | **Best.** "The agent sets speed; the rules protect the tanks" is a one-sentence, auditable description |

## 16. G12 resolution: the decision

**Primary strategy: Option C, implemented on Option A's mechanism.**

Concretely, and as it will be implemented in STEP 11:

1. **Native rules, controls and topology are untouched.** No rule is removed,
   rewritten, or reordered.
2. The EPS advances in **1800 s** control-step segments, carrying forward tank
   levels, pump status, **and pattern time**.
3. At each control step the agent's pump action is written to `base_speed` and
   **re-issued**, because a command's lifetime in this architecture is exactly
   one control step (hold rate 1.72 % without re-issue, 98.62 % with).
4. The agent commands **speed only**. Pump status stays entirely with the native
   rules, since `STATUS IS OPEN` is the only mechanism that restarts a shut pump.
5. `info` reports **commanded and realised speed separately** at every step, so
   the 1.38 % of open time in which the native logic overrides the controller is
   visible in the record rather than assumed away.

**G12 verdict: RESOLVED.** The Phase 5 CONDITIONAL is discharged. The
non-persistence is confirmed under Phase 6 solver settings, its mechanism is
measured rather than inferred, the two candidate repairs are measured against
each other on a validated harness, one is disqualified on evidence, and the
selected strategy states its own residual imperfection quantitatively instead of
claiming perfect actuator authority.

### Label summary for Part II

| Statement | Label |
|---|---|
| Speed does not persist; ≈2/3 of open time is off-command when commanded once | **VALIDATED FACT** |
| `SETTING IS` does not reopen a shut pump; `STATUS IS OPEN` resets speed to 1.0 | **VALIDATED FACT** |
| Option B halts EPANET at t = 79.5 h in the stepped architecture | **VALIDATED FACT** |
| The stepping mechanism reproduces the monolithic reference | **VALIDATED FACT** |
| Re-issue every control step; agent commands speed only | **ENGINEERING DECISION** |
| The 1.38 % residual override is acceptable because it is native tank protection | **RESEARCH ASSUMPTION** |
| Whether the residual matters for PPO's credit assignment | **HYPOTHESIS TO TEST** (after Phase 6) |

---

*Part I (G5) and Part II (G12) complete. Evidence:*
`results/phase6/p6_s3_prv_finechar.json`,
`results/phase6/p6_s3b_v179_refine.json`,
`results/phase6/p6_s3c_zone_interaction.json`,
`results/phase6/p6_s4_pump_strategy.json`.
