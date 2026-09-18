# Phase 5 — BWSN-1 Pre-Flight Hydraulic & Actuator Validation

**Question this phase answers:** can BWSN-1 serve as a stable, solvable and
controllable hydraulic environment for PPO with PRV setting control, variable
pump speed, pressure-dependent leakage and pressure-driven demand?

**Decision: CONDITIONAL PASS.** The network is hydraulically sound and every
actuator command is transmitted and applied exactly. Three of the eight PRVs
carry no flow in the distributed baseline, and a native EPANET rule action
discards a commanded pump speed at every rule-driven reopening. Both findings
are mechanical, measured, and fixable inside the approved thesis architecture.
No thesis conclusion is drawn here and no result in this document may be quoted
as a thesis result.

| item | value |
|---|---|
| phase | 5 — pre-flight validation only |
| network | BWSN-1 (Battle of the Water Sensor Networks, network 1) |
| gates run | 13 verdict strings from 7 modules |
| training performed | none — no PPO, no SAC, no GA, no tuning, no search |
| topology changes | none — no valve or pump added, removed, or moved |
| original input file | never modified; validation runs read a working copy |
| randomness | none — no random seed is used anywhere in phase 5 |
| wall-clock for the full sequence | 31.2 s |

Reproduce every number in this document with one command from the repository
root:

```bash
.venv/Scripts/python.exe src/validation/run_all.py
```

That driver runs the seven gate modules in dependency order, each in a fresh
interpreter, and prints the consolidated verdict table reproduced in section 17.
Each module writes one JSON artefact into `results/phase5/`; every figure quoted
below is copied from those artefacts, not retyped from a run log.

---

## 1. Objective

Phase 4 selected BWSN-1 as the thesis network. Phase 5 does not defend that
selection. It tries to break it.

The scope is falsification. Twelve gates were defined in advance, each with a
declared threshold and an explicit verdict string, covering: whether the file is
what the previous phase said it was; whether the hydraulics converge; what the
native controls actually do; whether a pump speed command and a PRV setting
command produce a measurable, correctly-signed hydraulic response; whether a
pressure-dependent leakage model behaves monotonically; whether pressure-driven
demand curtails as specified; whether an apparent leakage reduction can be
separated from demand starvation; whether mass balances at every solved state;
whether a full 96 h simulation is stable; whether the tanks cycle without
pinning; and whether the engine really applies what an agent would command.

Three questions are deliberately out of scope and are answered nowhere in this
document: whether PPO will learn a good policy, whether BWSN-1 is preferable to
any other network, and how much leakage a controller could remove.

---

## 2. Input File Provenance

The repository did not contain a BWSN-1 input file at the start of this phase, so
one was obtained from public mirrors, checksummed, and left untouched.

| item | value |
|---|---|
| filename | `BWSN_Network_1.inp` |
| stored at | `data/networks/original/BWSN_Network_1.inp` |
| size | 44 402 bytes |
| sha256 | `510af942ec643eb87adcf26e5a7df1cc4c23eb0c1e470a8a1257ed055f1956f1` |
| md5 | `09bf6a2879a045f5e7c5f0986ff78261` |
| retrieved (UTC) | 2026-09-02 |
| working copy | `data/networks/working/BWSN_Network_1_working.inp` |
| working copy sha256 | `53015ba9212e46bec731d190971819996233996b498bc269e828f992830a20a9` |

Three candidate sources were checked. Two returned byte-identical files, which is
the reason the file is treated as authentic rather than merely available:

| mirror | outcome |
|---|---|
| EPyT-Flow distribution (`filedn.com`) | retrieved, sha256 as above |
| OpenWaterAnalytics / EPyT, `dev` branch, `asce-tf-wdst` | retrieved, byte-identical |
| KIOS-Research / EPANET-Benchmarks | not found (404) |

The original file is never opened for writing by any phase-5 module. All runs
read the working copy, which differs from the original by exactly one recorded
patch:

| patch id | change | reason |
|---|---|---|
| `P1-quality-units-token` | `[OPTIONS] QUALITY` token normalised | WNTR 1.5.0 raises `Error 200` on the distributed token and cannot parse the original at all; native EPANET parses it without complaint |

`P1` is a parser-compatibility change, not a hydraulic one. Its effect is bounded
by G0: native EPANET and WNTR agree on the element counts, and the numeric
results in G1 are produced by the same EPANET engine in both cases. The full
provenance record, including per-mirror hashes, is in
`results/phase5/working_copy_provenance.json`.

---

## 3. Software / Version Information

Recorded automatically into the `env` block of every artefact, so each JSON file
carries its own environment stamp.

| item | value |
|---|---|
| OS | Windows-11-10.0.26200-SP0 |
| architecture | AMD64 |
| Python | 3.13.15 |
| WNTR | 1.5.0 |
| numpy / pandas / scipy / networkx | 2.5.2 / 3.0.5 / 1.18.1 / 3.6.1 |
| EPANET engine used by WNTR | `epanet2.dll` 20200 (`epanet20.dll` 20012, `epanet22.dll` 20200 also present) |
| EPANET engine used for the native cross-check | EPyT 2.3.5.2 wrapping EPANET 2.3.05 (reported version 20305) |
| random seed | none — no phase-5 result depends on randomness |
| determinism | reruns reproduce every artefact bit-for-bit apart from the `env.timestamp_utc` field |

Two independent engine bindings are used on purpose. WNTR drives the sweeps
because it can rewrite an `.inp` programmatically; EPyT reads the *original* file
directly, which is how G0 can state element counts for a file WNTR cannot parse.

Solver settings deserve their own line, because they are the single largest
correctness lever found in this phase. The distributed file declares
`ACCURACY 0.005` and `TRIALS 40`. Gates 6 to 12 override these to
`ACCURACY 1e-5` and `TRIALS 2000`. This is a tolerance change, not a hydraulic
or topological one; its justification is measured in D6 below and its effect on
the leak-free baseline is quantified in section 10.

---

## 4. Gate 0 — File Integrity

Artefact: `results/phase5/g0_integrity.json`. Module: `src/validation/g0_integrity.py`.

```
FACT:
Phase 4 recorded 22 structural claims about BWSN-1 (element counts, valve types,
pump curve types, control statements, simulation duration, timestep). Those
claims were made without opening the file in this repository.

TEST:
Parse the ORIGINAL file with native EPANET through EPyT and the WORKING copy with
WNTR 1.5.0. Enumerate every section. Count every element type. Read every valve
type token, every pump parameter token, every [RULES] and [CONTROLS] line, and
the [TIMES] block. Compare all 22 Phase-4 claims mechanically.

RESULT:
Native EPANET parses the original: 129 nodes, 178 links, engine 20305, rule
timestep 180 s. WNTR CANNOT parse the original (Error 200) but parses the working
copy. Section counts: 126 junctions, 1 reservoir, 2 tanks, 168 pipes, 2 pumps,
8 valves, 0 [EMITTERS], 0 [STATUS] entries, 1 [CONTROLS] line, 4 [RULES],
6 [DEMANDS] rows. All 8 valves carry the type token PRV. Both pumps carry a HEAD
curve token and no SPEED or PATTERN token. [TIMES]: DURATION 96:00,
HYDRAULIC 0:30, PATTERN 0:30, REPORT 1:00, QUALITY 0:05, START ClockTime 8:00 AM.
All 22 Phase-4 structural claims match. Four documentation discrepancies were
found and are reported in full below; none of them is a structural count error.

INFERENCE:
The file is the network Phase 4 described, and it is the network the thesis needs:
8 real PRVs and 2 real curve-driven pumps, on a 96 h horizon at a 30 min
hydraulic step. Phase 4's element-level description is reliable; its description
of the demand patterns and its inference about PRV activity are not.

STATUS:
PASS
```

**Verdict string:** `G0 FILE INTEGRITY = PASS`

### 4.1 The eight PRVs as distributed

| PRV | setting (psi) | diameter (in) |
|---|---|---|
| VALVE-173 | 70.000 | 6 |
| VALVE-174 | 80.000 | 6 |
| VALVE-175 | 55.000 | 10 |
| VALVE-176 | 29.762 | 6 |
| VALVE-177 | 45.000 | 6 |
| VALVE-178 | 37.000 | 6 |
| VALVE-179 | 40.000 | 8 |
| VALVE-180 | 16.450 | 8 |

Every one is a genuine PRV: the type token is `PRV`, the setting is a downstream
pressure target in psi, and the engine reports the three PRV statuses
(`Active`, `Open`, `Closed`) for all eight during simulation.

### 4.2 The two pumps as distributed

| pump | curve | curve points (flow GPM, head ft) | speed token in `[PUMPS]` |
|---|---|---|---|
| PUMP-170 | CURVE-0 | (0, 445), (790, 365), (1460, 120) | none |
| PUMP-172 | CURVE-2 | (0, 740), (2000, 530), (3240, 205) | none |
| — | CURVE-1 | (0, 730), (1000, 500), (1350, 260) | never referenced by any element |

Both pumps are HEAD-curve pumps with no explicit speed and no speed pattern, so
the engine treats their relative speed as 1.0 until something changes it. That is
the correct starting point for a variable-speed action: the speed is a free
variable, not a fixed one. `CURVE-1` is dead data.

### 4.3 Options, energy and demand as distributed

| option | value |
|---|---|
| UNITS | GPM |
| HEADLOSS | H-W (Hazen-Williams) |
| TRIALS | 40 |
| ACCURACY | 0.005 |
| UNBALANCED | Stop |
| PATTERN | PATTERN-0 |
| EMITTER EXPONENT | 0.5 |
| TOLERANCE | 0.01 |
| `[ENERGY]` Global Efficiency | 75.0 % |
| `[ENERGY]` Global Price | 0 |

Total base demand is 944.709999 GPM across 126 junctions, of which 47 junctions
have zero demand. `EMITTER EXPONENT 0.5` matters later: G6 adopts that exponent
for the validation leakage law rather than inventing one.

### 4.4 Discrepancies against the Phase 4 report — reported, not corrected

Four discrepancies were found at this gate. Each is recorded in
`g0_integrity.json` under `documentation_discrepancies` with
`"silent_correction": false`.

**D1 — pattern length.** Phase 4 wrote: *"Demand patterns: 4 patterns,
16 / 16 / 8 / 16 entries at a 0:30 pattern step, i.e. an 8-hour cycle repeated
over the 96 h horizon."* The line counts are right; the conclusion is not. Each
`[PATTERNS]` line carries six multipliers, so the true lengths are 96 / 96 / 48 /
96 multipliers, which at a 0:30 pattern step are **48 h / 48 h / 24 h / 48 h**
cycles, not 8 h.

| pattern | lines | multipliers | cycle (h) | multiplier range |
|---|---|---|---|---|
| PATTERN-0 | 16 | 96 | 48.0 | 0.03 – 2.73 |
| PATTERN-1 | 16 | 96 | 48.0 | 0.00 – 80.00 |
| PATTERN-2 | 8 | 48 | 24.0 | 0.69 – 1.26 |
| PATTERN-3 | 16 | 96 | 48.0 | 25.80 – 884.50 |

Consequence: **the Phase 4 inference that BWSN-1's native demand patterns are
"unrealistically short-cycle" is not supported by the file and must be
retracted.** No file change is required, and none was made.

**D2 — two dead demand patterns.** Phase 4 reports four demand patterns without
noting that two are never used. Only `PATTERN-0` and `PATTERN-1` appear in
`[JUNCTIONS]`.

| pattern | junctions using it | base demand carried (GPM) |
|---|---|---|
| PATTERN-0 | 77 | 943.910 |
| PATTERN-1 | 2 | 0.800 |
| none | 47 | 0.000 |
| PATTERN-2, PATTERN-3 | 0 | — |

Consequence: the effective native demand model is one 96-multiplier profile
driving 99.92 % of base demand. This is material to how the thesis stochastic
demand model replaces the native one, but it changes nothing about the network's
hydraulics.

**D3 — rule timestep engine divergence.** `[TIMES]` declares no rule timestep.
Native EPANET defaults to hydraulic/10 = **180 s**; WNTR's `WaterNetworkModel`
defaults to **360 s**. An unmodified WNTR run therefore evaluates the tank-level
pump rules at half the native frequency. Not mentioned in Phase 4.

Measured effect on the leak-free baseline (G1): max |ΔP| = 0.0323 m = **0.0459
psi**, and the pump switch counts are identical (7 and 7). Small, but not zero.
Consequence: every phase-5 module sets `rule_timestep = 180 s` explicitly so that
WNTR reproduces native EPANET rule behaviour, and the RL environment must do the
same.

**D4 — report timestep is coarser than the hydraulic timestep.** The file solves
every **0:30** but reports every **1:00**, so 96 of the 193 solved states are
never returned to the caller. Not mentioned in Phase 4.

| quantity | value |
|---|---|
| hydraulic timestep | 1800 s |
| report timestep as distributed | 3600 s |
| solved states over 96 h | 193 |
| reported states as distributed | 97 |

Consequence: an RL environment reading results at the distributed reporting
resolution would silently operate on a 1 h control interval while believing it had
a 30 min one. This belongs in section 19 and is listed there.

To rule out the possibility that the coarse reporting hides a solver problem
rather than merely discarding output, G1 compared the two resolutions on their 97
common timesteps: max |ΔP| = **0.0 m**, identical to 1e-9 m. The discarded states
are missing output, not different hydraulics.

---

## 5. Gate 1 — Baseline Convergence

Artefact: `results/phase5/g1_g2_g11_baseline.json`. Module: `src/validation/g1_baseline.py`.

This gate runs the network **as distributed**: no leakage, no demand-model change,
no actuator override, the file's own `ACCURACY 0.005 / TRIALS 40`. It is the only
gate that must not touch anything, because it is the reference every later gate is
measured against.

```
FACT:
An RL environment resets and steps a simulator thousands of times per training
run. If the distributed model does not converge cleanly on its own terms, nothing
built on top of it can be trusted.

TEST:
Run the full 96 h EPS as distributed. Scan the EPANET .rpt file for error and
warning lines. Count node-timesteps with negative pressure. Check both tanks
against their declared min and max levels. Then rerun at report timestep 1800 s
and at rule timestep 360 s to measure whether the reporting resolution or the
rule frequency changes the answer.

RESULT:
97 reported timesteps over 96 h, 0 EPANET errors, 0 EPANET warnings, 0 WNTR
warnings. Junction pressure over 12 222 node-states: min 4.2239 psi at
JUNCTION-29 (t = 90 000 s), max 507.7995 psi at JUNCTION-106 (t = 208 800 s),
mean 103.8258 psi. 0 negative node-states. 194 node-states below 20 psi, all of
them at exactly two junctions: JUNCTION-29 and JUNCTION-126. Neither tank hits a
limit or goes negative. Resolution cross-check: 97 common timesteps, max |ΔP| =
0.0 m. Rule-timestep cross-check: max |ΔP| = 0.0459 psi, switch counts identical.

INFERENCE:
The distributed model converges without complaint and is numerically stable over
the full horizon. The 507.80 psi maximum is not a converged-but-unphysical state;
it is investigated in G10 and traced to five junctions the file declares at
elevation 0.0 ft, where the reported "pressure" is head above datum.

STATUS:
PASS
```

**Verdict string:** `G1 BASELINE EPANET/WNTR CONVERGENCE = PASS`

### 5.1 Baseline tanks and pumps

| tank | elevation (ft) | initial (ft) | min / max (ft) | diameter (ft) | observed range (ft) | net change (ft) |
|---|---|---|---|---|---|---|
| TANK-130 | 843.90 | 15.159 | 0 / 32.1 | 186 | 12.1212 – 15.9769 | −1.1995 |
| TANK-131 | 1137.10 | 17.945 | 0 / 41.9 | 106 | 15.3996 – 18.3484 | −0.9712 |

| pump | switches | fraction of time open | max flow (GPM) | mean flow (GPM) | energy over 96 h (kWh) |
|---|---|---|---|---|---|
| PUMP-170 | 7 | 0.2268 | 765.8873 | 172.6919 | 1 565.06 |
| PUMP-172 | 7 | 0.3505 | 2 413.3633 | 843.0297 | 9 044.60 |

Mean power while running is 71.139 kW (PUMP-170) and 266.018 kW (PUMP-172) at the
file's declared 75 % global efficiency.

---

## 6. Gate 2 — Native Controls

Artefact: `results/phase5/g1_g2_g11_baseline.json`, key `native_controls`.

This gate is descriptive by design: it establishes what the file already does
before any later gate changes anything. It carries no pass/fail, because there is
nothing here to pass or fail — only something to know before touching the model.

### 6.1 Required table: `Element | Native control | Trigger | Initial state | Active?`

| Element | Native control | Trigger | Initial state | Active? |
|---|---|---|---|---|
| PUMP-170 | RULE-3 / RULE-4 on TANK-131 | close at level ≥ 18.4 ft, open at level ≤ 15.4 ft | Open | yes — 7 switches, open 21.76 % of the horizon |
| PUMP-172 | RULE-0 / RULE-1 on TANK-130 | close at level ≥ 16.0 ft, open at level ≤ 12.1 ft | Open | yes — 7 switches, open 35.75 % of the horizon |
| VALVE-173 | none | — | Active | yes — regulating 100 % of the horizon |
| VALVE-174 | none | — | Closed | **no — Closed 100 % of the horizon, flow identically 0** |
| VALVE-175 | none | — | Active | yes — regulating 100 % of the horizon |
| VALVE-176 | none | — | Active | yes — regulating 100 % of the horizon |
| VALVE-177 | none | — | Active | yes — regulating 100 % of the horizon |
| VALVE-178 | none | — | Active | yes — regulating 100 % of the horizon |
| VALVE-179 | none | — | Closed | **no — Closed 100 % of the horizon, flow identically 0** |
| VALVE-180 | `[CONTROLS]`: `LINK VALVE-180 CLOSED AT TIME 0` | time 0 | Closed | **no — Closed 100 % of the horizon, flow identically 0** |

### 6.2 The rules verbatim, from the ORIGINAL file

```
RULE-0   IF TANK TANK-130 LEVEL >= 16.000000   THEN PUMP PUMP-172 STATUS IS CLOSED
RULE-1   IF TANK TANK-130 LEVEL <= 12.100000   THEN PUMP PUMP-172 STATUS IS OPEN
RULE-3   IF TANK TANK-131 LEVEL >= 18.400000   THEN PUMP PUMP-170 STATUS IS CLOSED
RULE-4   IF TANK TANK-131 LEVEL <= 15.400000   THEN PUMP PUMP-170 STATUS IS OPEN
```

The action verb is `STATUS IS OPEN`, not `SETTING IS`. That single token is the
mechanism behind the G12 finding in section 16, and it is why the finding is a
property of this file rather than a bug in the engine or in the test harness.

### 6.3 Rule-firing evidence

The rules fire where they say they fire. Levels at the instant of each switch:

| pump | opens at (ft) | closes at (ft) | switch times (s) |
|---|---|---|---|
| PUMP-170 | 15.4910, 15.4664, 15.4992 | 18.3378, 18.3209, 18.3819, 18.3872 | 5 400, 88 200, 115 200, 187 200, 210 600, 284 400, 304 200 |
| PUMP-172 | 12.1212, 12.1098, 12.1244 | 15.9407, 15.9623, 15.9818, 15.9769 | 10 800, 90 000, 133 200, 189 000, 225 000, 286 200, 320 400 |

Every opening is at or below the rule's threshold and every closing at or above
it, within the level resolution of one 180 s rule evaluation.

### 6.4 What each PRV actually carries in the baseline

Flow share is expressed against total base demand, 944.710 GPM.

| PRV | status over 96 h | mean flow (GPM) | share of base demand |
|---|---|---|---|
| VALVE-175 | Active | 363.6674 | 38.495 % |
| VALVE-176 | Active | 269.4178 | 28.519 % |
| VALVE-178 | Active | 37.7458 | 3.995 % |
| VALVE-177 | Active | 18.9130 | 2.002 % |
| VALVE-173 | Active | 1.5380 | 0.163 % |
| VALVE-174 | Closed | 0.0000 | 0 % |
| VALVE-179 | Closed | 0.0000 | 0 % |
| VALVE-180 | Closed | 0.0000 | 0 % |

**D5 — PRV activity.** Phase 4 wrote: *"One `[CONTROLS]` line closes VALVE-180 at
time 0, so 7 of the 8 PRVs are active at start."* The `[CONTROLS]` statement is
real, but the conclusion is wrong. VALVE-174 and VALVE-179 are also `Closed` for
the entire 96 h with identically zero flow, shut by the hydraulics rather than by
any control statement — a PRV closes when downstream head exceeds its setting and
flow would reverse. **Three of eight PRVs carry no flow in the distributed
baseline, not one.** Recorded in the artefact as a discrepancy with
`"silent_correction": false`; no PRV was removed, and G4 goes on to test all eight
anyway.

**Verdict string:** `G2 NATIVE CONTROL LOGIC = CHARACTERISED (descriptive gate, no pass/fail)`

---

## 7. Gate 3 — Pump-Speed Behaviour

Artefact: `results/phase5/g3_pump_speed.json`. Module: `src/validation/g3_pump_speed.py`.

```
FACT:
The thesis needs a continuous variable-speed pump action. EPANET applies relative
speed n by scaling the head curve as h(q) = n^2*h0 - r*(q/n)^n_exp. If the engine
did not really apply the commanded speed, or if the response were flat, the action
dimension would be decorative.

TEST:
Fit the 3-point EPANET curve for each pump. Sweep relative speed over
0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 1.00, 1.05, 1.10 in single-snapshot runs, one
pump at a time. At each speed record status, flow, head gain, power, and the
residual of the operating point against the speed-scaled curve. Check the shutoff
head against the affinity law n^2. Then run two 96 h EPS at fixed commanded speed
0.85 and 1.00 with the native rules intact.

RESULT:
Curve fits: PUMP-170 h0 = 445.0 ft, r = 1.9469e-05, n = 2.28247; PUMP-172
h0 = 740.0 ft, r = 8.3818e-05, n = 1.93845. Shutoff head scales as speed^2
EXACTLY at all 9 swept speeds for both pumps. Max |residual| of any running
operating point against the speed-scaled curve is 8.62e-05 ft. Flow is monotone
increasing in speed for both pumps. No swept speed pushed the operating point
beyond the curve's q_max. speed_really_applied = true.

INFERENCE:
The commanded relative speed is genuinely applied and the response is smooth,
monotone and physically correct across the whole tested range. The action is real.

STATUS:
PASS
```

**Verdict string:** `G3 PUMP SPEED RESPONSE = PASS`

### 7.1 Required table: `Pump | Speed | Flow | Head | Power/Energy | Valid?`

| Pump | Speed | Status | Flow (GPM) | Head gain (ft) | Power (kW) | Valid? |
|---|---|---|---|---|---|---|
| PUMP-170 | 0.50 | Closed | 0.00 | — | 0.000 | yes — shut, n²h₀ < static head 295.7605 ft |
| PUMP-170 | 0.60 | Closed | 0.00 | — | 0.000 | yes — shut |
| PUMP-170 | 0.70 | Closed | 0.00 | — | 0.000 | yes — shut |
| PUMP-170 | 0.80 | Closed | 0.00 | — | 0.000 | yes — shut |
| PUMP-170 | 0.85 | Open | 332.47 | 309.895 | 25.915 | yes |
| PUMP-170 | 0.90 | Open | 514.17 | 329.526 | 42.617 | yes |
| PUMP-170 | 1.00 | Open | 765.89 | 370.465 | 71.367 | yes |
| PUMP-170 | 1.05 | Open | 870.53 | 392.137 | 85.863 | yes |
| PUMP-170 | 1.10 | Open | 967.73 | 414.700 | 100.942 | yes |
| PUMP-172 | 0.50 | Closed | 0.00 | — | 0.000 | yes — shut, n²h₀ < static head 433.6655 ft |
| PUMP-172 | 0.60 | Closed | 0.00 | — | 0.000 | yes — shut |
| PUMP-172 | 0.70 | Closed | 0.00 | — | 0.000 | yes — shut |
| PUMP-172 | 0.80 | Open | 842.90 | 434.799 | 92.183 | yes |
| PUMP-172 | 0.85 | Open | 1 360.51 | 436.132 | 149.246 | yes |
| PUMP-172 | 0.90 | Open | 1 754.57 | 437.524 | 193.088 | yes |
| PUMP-172 | 1.00 | Open | 2 401.76 | 440.550 | 266.139 | yes |
| PUMP-172 | 1.05 | Open | 2 688.22 | 442.179 | 298.984 | yes |
| PUMP-172 | 1.10 | Open | 2 959.52 | 443.882 | 330.426 | yes |

### 7.2 Feasible speed bounds — a hard constraint on the action space

A pump shuts when its scaled shutoff head falls below the static head it must
lift. The bound is measured, not assumed:

| pump | static head across the shut pump (ft) | shutoff at speed 1 (ft) | implied minimum feasible speed | highest speed observed shut | lowest speed observed running |
|---|---|---|---|---|---|
| PUMP-170 | 295.7605 | 445.0 | 0.8152 | 0.80 | 0.85 |
| PUMP-172 | 433.6655 | 740.0 | 0.7655 | 0.70 | 0.80 |

The static head depends on tank level, so this bound **moves during an EPS** and is
not a fixed constant. An action space with a lower bound below ≈0.82 therefore
contains a region in which the commanded speed produces no flow at all. That is
correct EPANET physics, not a modelling error, but the RL action bounds must be
chosen knowing it.

### 7.3 Speed authority under the native rules

Two 96 h EPS at fixed commanded speed, rules intact:

| quantity | value |
|---|---|
| mean ΔP, 0.85 vs 1.00 | 0.0485 psi |
| min ΔP, 0.85 vs 1.00 | 0.0214 psi |
| energy change, PUMP-170 | −5.06 % (1 565.06 → 1 418.30 kWh) |
| energy change, PUMP-172 | −1.78 % (9 044.60 → 9 013.78 kWh) |

Under the native rules a speed change mainly redistributes pump run time and
energy rather than the pressure field, because the pressure field is anchored by
two tanks whose level the rules confine to a narrow band. This is an observation
about **actuator authority**, not a verdict — and not a thesis conclusion.

One number in this table is the first fingerprint of the G12 finding. At commanded
speed 0.85, PUMP-170's maximum flow over the EPS is **764.5399 GPM**, against
**765.8873 GPM** at commanded speed 1.00. A pump genuinely running at 0.85 of its
rated speed cannot reach 99.8 % of its full-speed peak flow. Section 16 explains
why, with a controlled experiment.

---

## 8. Gate 4 — PRV Behaviour

Artefact: `results/phase5/g4_g5_prv.json`. Module: `src/validation/g4_g5_prv.py`.

```
FACT:
The thesis' primary action is a continuous PRV setting. A PRV only regulates while
its setting binds: above the available upstream head it saturates open, and below
the downstream head it shuts against reverse flow. An action dimension on a valve
that never leaves saturation would be unobservable.

TEST:
For each of the 8 PRVs independently, command 12 settings - 5, 10, 15, 20, 30, 40,
50, 60, 70, 80, 100, 120 psi - in single-snapshot runs, one valve at a time, and
record status, realised downstream pressure, own flow, and the pressure change at
every other junction. Then run 96 h EPS at 0.5x, 1.0x and 1.5x each valve's
nominal setting. Declare the responsiveness criterion before running.

RESULT:
7 of 8 PRVs are responsive on both sub-criteria or on at least one. VALVE-180 is
not: 0 regulating settings out of 13 tested, downstream pressure span 0.0 psi,
flow span 0.0 GPM, 0 junctions influenced. Realisation error on any Active PRV
never exceeds 2.67e-05 psi. One perturbation drives negative pressure:
VALVE-179 at 1.5x nominal, min -99.3792 psi across 708 node-timesteps.

INFERENCE:
The PRV actuator mechanism itself works exactly: when a PRV is Active, the engine
holds the commanded downstream pressure to within 3e-05 psi. Responsiveness is a
property of individual valves in this configuration, not of the mechanism. The
single unresponsive valve and the single dangerous perturbation are both carried
forward as evidence, not silently dropped.

STATUS:
PASS
```

**Verdict string:** `G4 PRV ACTUATOR RESPONSIVENESS = PASS`

### 8.1 The responsiveness criterion, and why the obvious version is wrong

Declared before any run: a PRV is **responsive** if *either* the network pressure
moves by more than 0.5 psi at some junction, *or* its own flow moves by more than
1 GPM.

The conjunctive version — requiring both — is wrong for a demand-driven run and
was explicitly rejected. Under DDA the withdrawal at each junction is fixed by the
pattern, so a PRV that regulates a dead-end zone must keep passing exactly the same
flow no matter what its setting is; only the pressure moves. VALVE-175 is the clean
example: it holds 38.5 % of system demand and its downstream pressure spans
115.00 psi across the setting grid, while its flow spans **0.00092 GPM**. Under an
AND rule the network's single most influential PRV would have been declared
unresponsive. Both sub-criteria are reported separately below so the reader can
apply either rule.

### 8.2 Required table: `PRV | Initial | Tested values | Downstream pressure Δ | Flow Δ | Saturation | Meaningful?`

Tested values are the same 12-point grid for every valve: 5, 10, 15, 20, 30, 40,
50, 60, 70, 80, 100, 120 psi, plus the valve's own nominal setting.

| PRV | Initial (psi) | Status at nominal | Downstream Δ span (psi) | Own flow Δ span (GPM) | Saturation (regulating / sat-open / sat-closed) | Max network influence (psi) | Junctions influenced | Meaningful? |
|---|---|---|---|---|---|---|---|---|
| VALVE-173 | 70.000 | Active | 50.234 | 2.6997 | 4 / 1 / 7 | 34.669 | 8 | **yes** |
| VALVE-174 | 80.000 | Closed | 24.435 | 2.6992 | 2 / 0 / 10 | 24.435 | 8 | **yes** |
| VALVE-175 | 55.000 | Active | 115.000 | 0.00092 | 13 / 0 / 0 | 65.000 | 24 | **yes** |
| VALVE-176 | 29.762 | Active | 105.591 | 0.00107 | 12 / 1 / 0 | 80.829 | 2 | **yes** |
| VALVE-177 | 45.000 | Active | 115.000 | 0.0 | 13 / 0 / 0 | 75.000 | 3 | **yes** |
| VALVE-178 | 37.000 | Active | 81.158 | 0.00083 | 11 / 2 / 0 | 49.158 | 2 | **yes** |
| VALVE-179 | 40.000 | Closed | 35.456 | 4 794.186 | 3 / 3 / 6 | 43.735 | 93 | **yes** |
| VALVE-180 | 16.450 | Closed | 0.000 | 0.0 | 0 / 0 / 13 | 0.000 | 0 | **no** |

Max realisation error on an Active PRV, across every valve and every commanded
setting: **2.67e-05 psi**. VALVE-180's realisation error is `null` because it never
reached an Active state at any of the 13 tested settings, so there was nothing to
measure.

### 8.3 The one dangerous perturbation

`VALVE-179_x1.5` is the only tested perturbation anywhere in G4 that produces
negative pressure: **min −99.3792 psi across 708 node-timesteps**. VALVE-179 is
`Closed` in the baseline; raising its setting reopens it and dumps flow into a zone
the baseline never pressurises, and its own flow span of 4 794 GPM — five times
total system base demand — is the signature of that reopening.

This is a real hazard for the RL action space, not a solver artefact: the same
valve produces the same effect at 1.25× in G12 (min −97.086 psi). It is listed as
confound **X1** and appears in section 19.

---

## 9. Gate 5 — PRV Activity Audit

Artefact: `results/phase5/g4_g5_prv.json`, key `gate5_audit`.

The question: should all 8 PRVs become 8 action dimensions? This gate answers with
evidence only. **No PRV is removed, disabled or relocated by this gate**, exactly
as the phase brief requires; the artefact records that in `gate5_note`.

```
FACT:
An action dimension is only useful if moving it changes the state. Three PRVs carry
identically zero flow in the distributed baseline (D5). VALVE-180 additionally shows
no response at any tested setting (G4).

TEST:
Combine, per valve: baseline status and flow share over 96 h; the count of tested
settings at which the valve regulates versus saturates; the snapshot network
influence; and the max mean pressure change over the 96 h EPS at 0.5x / 1.0x / 1.5x
nominal. Classify each valve on that evidence.

RESULT:
4 valves are ACTIVE and HIGH-LEVERAGE. 1 valve regulates but carries under 1 % of
base demand. 2 valves are Closed in the baseline yet respond when reopened. 1 valve
- VALVE-180 - is inert in the distributed baseline: 0 of 13 settings regulate, EPS
max mean dP = 0.0 psi.

INFERENCE:
8 PRVs do not give 8 equally informative action dimensions in the distributed
configuration. 4 dimensions carry the network, 1 is low-leverage, 2 are recoverable
only by reopening a valve that the baseline hydraulics shut, and 1 is unobservable.
This is a design finding that must be resolved before the action space is fixed -
it is not a reason to reject the network.

STATUS:
CONDITIONAL
```

**Verdict string:** `G5 PRV ACTION-DIMENSION AUDIT = CONDITIONAL`

### 9.1 Per-valve audit

| PRV | classification | flow share | EPS max mean ΔP (psi) | responds to setting change? | evidence note |
|---|---|---|---|---|---|
| VALVE-175 | ACTIVE, HIGH-LEVERAGE | 38.495 % | 27.500 | yes | regulates at nominal, carries a material share of demand, moves the pressure field measurably |
| VALVE-176 | ACTIVE, HIGH-LEVERAGE | 28.519 % | 14.881 | yes | as above |
| VALVE-178 | ACTIVE, HIGH-LEVERAGE | 3.995 % | 18.500 | yes | as above |
| VALVE-177 | ACTIVE, HIGH-LEVERAGE | 2.002 % | 22.500 | yes | as above |
| VALVE-173 | LOW-LEVERAGE | 0.163 % | 34.755 | yes | regulates, but carries under 1 % of system base demand, so its contribution to network-wide leakage or service is small |
| VALVE-174 | CLOSED in baseline but responsive when reopened | 0 % | 24.435 | yes | carries no flow at the nominal setting, yet the sweep shows a hydraulic response at other settings, so the dimension is recoverable rather than structurally dead |
| VALVE-179 | CLOSED in baseline but responsive when reopened | 0 % | 113.554 | yes | as above — but reopening it drives the network to −97 … −99 psi (X1) |
| VALVE-180 | INERT in the distributed baseline | 0 % | 0.000 | **no** | an action dimension on this valve would be unobservable in the baseline configuration |

### 9.2 Answering the three questions the brief asked

**Should 8 PRVs be 8 action dimensions?** On this evidence, not without a decision
being taken and recorded. Four dimensions (VALVE-175, -176, -177, -178) are
unambiguously informative. VALVE-173 is informative but low-leverage. VALVE-174 and
VALVE-179 are only informative if the agent is allowed to reopen a valve the
baseline keeps shut, and for VALVE-179 that carries the X1 hazard. VALVE-180 is
unobservable as distributed.

**Which are saturated, inactive or low-leverage?** Saturated-closed at nominal:
VALVE-174, VALVE-179, VALVE-180. Low-leverage: VALVE-173. Never regulating at any
tested setting: VALVE-180 only.

**Should VALVE-180 get a dimension?** The evidence says an action on VALVE-180
changes nothing measurable in the distributed configuration — 0 of 13 settings
regulate, 0 junctions influenced, 0.0 psi EPS effect. The gate does not decide the
question; it records that any decision to keep the dimension must explain what the
agent would learn from it, and that the `[CONTROLS]` line closing it at t = 0 is
part of the distributed model that this phase is forbidden to alter.

---

## 10. Gate 6 — Leakage Validation

Artefact: `results/phase5/g6_g7_g8_leak_pda.json`, key `gate6`. Module:
`src/validation/g6_g7_g8_leak_pda.py`.

> **This leakage coefficient set is a validation instrument. It must not enter any
> thesis result.** It was sized by one closed-form evaluation with no optimisation
> of any kind, and it is recorded here only so that the gate's arithmetic can be
> audited.

### 10.1 The law, and why it is signed

```
q_leak = sign(p) · C_j · |p|^0.5     (p in psi, q in GPM)
```

The exponent α = 0.5 is taken from the distributed file's own
`[OPTIONS] EMITTER EXPONENT 0.5`, not invented. The law is applied through
`[EMITTERS]`, one emitter per junction.

The `sign(p)` is not cosmetic. An EPANET emitter is a virtual pipe to a virtual
reservoir and **flows backwards at negative pressure**. Verified at JUNCTION-126 at
p = −5.731 psi: engine −0.6416 GPM, signed law −0.6416 GPM, pressure-clipped law
0.0000 GPM. A validation instrument that clipped at zero would silently disagree
with the engine by the full backflow whenever any junction went negative — which
several perturbation cases do.

### 10.2 Sizing

C_j is proportional to half the incident pipe length at junction j — deterministic,
no random seed, no per-node tuning. The single global scale is fixed in closed form
by `k = target / Σ_j (w_j · p_j^α)`:

| quantity | value |
|---|---|
| target leakage | 10 % of baseline inflow = 84.74359 GPM |
| Σ_j w_j p_j^α | 1 187 270.5038 |
| global scale k | 7.13768134008582e-05 |
| junctions with an emitter | 126 |
| coefficient min / max | 0.00199855 / 0.44900599 |
| total coefficient | 8.76509297 |
| leakage realised at nominal | 84.7266 GPM = **9.1795 % of inflow** |

Measurable but not dominant, as the brief required, and one evaluation rather than
a search.

### 10.3 The gate result, including one failed sub-test

```
FACT:
A pressure-dependent leakage model is only usable as evidence if lowering pressure
lowers leakage. The naive way to test that is to correlate mean network pressure
against total leakage across a PRV sweep.

TEST:
Two families of PRV perturbation, each with leakage applied and run for 96 h:
family A scales ALL 8 PRV settings by 0.25 / 0.50 / 0.75 / 1.00 / 1.25; family B
scales only the four Active PRVs by 1.10 / 1.25 / 1.50. For each case compute total
leakage and, separately, the full nodal pressure vector. Test monotonicity two ways:
against mean pressure, and against the nodal pressure-DOMINANCE partial order
(case X dominates case Y only if EVERY junction is at least as high in X as in Y,
within a tolerance). Sweep the tolerance. Verify the engine against the modelled law
node by node.

RESULT:
Mean-pressure monotonicity FAILS on one pair out of the sweep: family A x0.75 ->
x1.25 raises mean pressure from 100.3987 to 100.7715 psi while leakage FALLS from
82.9752 to 80.2960 GPM. The dominance test PASSES with 0 violations at every
tolerance tested - 0.05, 0.1, 0.25, 0.5, 1.0 and 2.0 psi - over 15, 15, 21, 21, 21
and 21 comparable pairs respectively. Engine-vs-modelled leak agreement: max
|delta| = 3.899e-05 GPM. Service demand is invariant under DDA: max DSR deviation
3.369e-08.

INFERENCE:
The leakage model is correct and monotone in the only sense that is physically
meaningful. Mean pressure is NOT a sufficient statistic for total leakage in this
network, because a redistribution of the pressure field can raise the mean while
lowering the pressure at the high-coefficient nodes. The failed sub-test is
therefore evidence about the instrument, not about the model.

STATUS:
PASS
```

**Verdict string:** `G6 LEAKAGE MODEL VALIDATION = PASS`

**Disclosed instrument change.** The mean-pressure test was declared first and it
failed. The pressure-dominance test replaced it as the decision criterion. Both
results are reported above and both are in the artefact. The replacement is
defensible because dominance is strictly stronger — it requires the pressure to be
higher *everywhere*, so it cannot be satisfied by a redistribution — and because
the tolerance sweep makes it falsifiable rather than tautological: a single
violation at any tolerance would have failed the gate.

### 10.4 Confound X1, disclosed

The single non-monotone pair is explained, and the explanation is itself a finding.
VALVE-179's mean flow across the family-A sweep:

| PRV scale | VALVE-179 mean flow (GPM) |
|---|---|
| ×0.25 | 0.0 |
| ×0.50 | 0.0 |
| ×0.75 | 0.0 |
| ×1.00 | 0.0 |
| ×1.25 | 1 212.1509 |

At ×1.25 the setting exceeds the downstream head and VALVE-179 reopens, changing
the topology of the flow field rather than merely its magnitude. Any comparison
that spans that threshold is comparing two different networks. This is confound
**X1**, and it is the same mechanism as the −99.38 psi excursion in G4.

### 10.5 D6 — the file's own solver settings silently return unconverged states

This discrepancy is against the *file*, not against Phase 4.

```
FACT:
The distributed file declares ACCURACY 0.005 and TRIALS 40 with UNBALANCED Stop.
EPANET reported 0 errors and 0 warnings on every run at those settings, including
the G1 baseline.

TEST:
Apply the validation emitters and compare, node by node, the engine's implied
emitter discharge against C_j*p^0.5 evaluated at the engine's own reported
pressure. Independently compute the network continuity residual. Do this at the
file's settings and at ACCURACY 1e-5 / TRIALS 2000.

RESULT:
At ACCURACY 0.005 / TRIALS 40: the emitter law is violated by up to 2.01 GPM at a
single node and network continuity by up to 9.97 GPM, with ZERO EPANET errors and
ZERO warnings. At 1e-5 / 2000: the emitter law is reproduced to 0.0000 GPM and the
continuity residual falls to 0.0004 GPM. TRIALS must rise with ACCURACY: at 1e-5
with only 200 trials the leak-free run halts at 19:00 h with "System unbalanced".

INFERENCE:
The distributed tolerance is loose enough that the engine returns states which do
not satisfy the equations it was given, while reporting success. Any leakage or
mass-balance evidence produced at that tolerance would be measuring solver slack
rather than hydraulics.

STATUS:
PASS (the finding is confirmed; the mitigation is adopted)
```

Effect of the tolerance change on the leak-free baseline, so the reader can judge
whether it altered the network's behaviour:

| quantity | at 0.005 / 40 | at 1e-5 / 2000 |
|---|---|---|
| mean junction pressure | 103.8258 psi | 103.8221 psi |
| min junction pressure | 4.224 psi | 4.225 psi |
| PUMP-170 / PUMP-172 switch counts | 7 / 7 | 7 / 7 |
| tank levels | — | within 0.045 ft |
| differing pump status states | — | 1, at 62 h (PUMP-172) |

Gates 1, 3, 4, 5 and 11 were run at the file's native setting; their conclusions
are qualitative (does the actuator respond, do the tanks cycle) and are unaffected.
Gates 6 to 12 run at 1e-5 / 2000, because their conclusions are quantitative.

---

## 11. Gate 7 — PDA Validation

Artefact: `results/phase5/g6_g7_g8_leak_pda.json`, key `gate7`.

```
FACT:
Under demand-driven analysis EPANET delivers the requested demand regardless of
pressure, including at negative pressure. A leakage-reduction study that lowers
pressure under DDA cannot detect the service damage it causes. Pressure-driven
analysis is therefore not optional for this thesis.

TEST:
Echo the generated .inp back and confirm the engine received the PDA options. Run
the network with and without PDA, with and without leakage, and compute the demand
satisfaction ratio DSR = delivered / requested using
wntr.metrics.expected_demand for the denominator. Then perform a pressure
perturbation - the same two PRV families as G6 - and test whether DSR responds.

RESULT:
Echoed options confirm DEMAND MODEL PDA, MINIMUM PRESSURE 0.00, REQUIRED PRESSURE
20.00, PRESSURE EXPONENT 0.5. Under DDA the network delivers requested demand
exactly: DSR mean 0.99999998. Under PDA at nominal settings, with no leakage,
DSR mean 0.9833382, DSR min 0.9818803, max unserved 47.6861 GPM, and demand is
curtailed at ALL 193 timesteps. DSR responds to the perturbation: mean-pressure
monotonicity fails on the same single pair as G6, while the dominance test passes
with 0 violations at all six tolerances (3, 7, 17, 21, 21, 21 comparable pairs).

INFERENCE:
PDA is active, correctly parameterised, and it bites at the nominal operating point
rather than only under extreme perturbation - which is what makes it a usable
service-quality signal for a reward function. The distributed network does not
fully satisfy its own demand at 20 psi required pressure.

STATUS:
PASS
```

**Verdict string:** `G7 PDA RESPONSE = PASS`

### 11.1 Threshold provenance — stated as an assumption, not a fact

The 20 psi required pressure and 0 psi minimum pressure are **the author's
validation choice**, recorded as such in the artefact. Whether the BWSN-1 problem
statement declares its own service pressure threshold is **UNKNOWN — not checked in
this phase**. Nothing in this document depends on the specific value; the gate
tests that the mechanism responds, not that 20 psi is the right number. The thesis
must justify its own threshold separately.

### 11.2 Why PDA curtails at the nominal operating point

Two junctions sit permanently below the 20 psi required pressure with no
perturbation at all:

| junction | mean pressure (psi) | min pressure (psi) | elevation (ft) |
|---|---|---|---|
| JUNCTION-29 | 5.1202 | 4.1645 | 846.28 |
| JUNCTION-126 | 16.7387 | 16.6168 | 434.00 |

386 node-states = 2 junctions × 193 states. These are the same two junctions G1
flagged as the only ones below 20 psi in the leak-free DDA baseline, so the finding
is a property of the distributed network, not of the leakage instrument or of PDA.

### 11.3 Two numerical honesty notes

**DSR marginally above 1 in family B.** Cases `actv1.25` and `actv1.50` report DSR
mean 1.00016 and 1.00017. This is the 1e-5 convergence residual, not
over-delivery: the absolute discrepancy is −0.06 GPM against 906.40 GPM requested,
a relative 6.6e-05. Recorded in the artefact as `dsr_above_one_is_numerical`.

**Confound X2 — PDA feedback raises pressure elsewhere.** Under PDA, scaling all
PRVs down to 0.25 leaves **84 junctions higher** and **33 lower** relative to the
0.75 case. The mechanism: curtailment reduces withdrawal, which reduces friction
loss, which raises pressure at nodes downstream of the curtailed ones. Under PDA a
PRV setting reduction is therefore not a monotone pressure reduction across the
network. This is disclosed because it directly affects how a reward function may
interpret a pressure signal, and it is the second reason mean pressure is not a
sufficient statistic here.

---

## 12. Gate 8 — Leakage / Service Separation

Artefact: `results/phase5/g6_g7_g8_leak_pda.json`, key `gate8`.

```
FACT:
Lowering pressure reduces leakage AND, under PDA, reduces delivered demand. Both
reduce system inflow. A study that reported "inflow fell, therefore leakage fell"
would be measuring demand starvation and calling it a leakage saving. This is the
single most dangerous confound in pressure-management research.

TEST:
For every perturbation case, decompose the 96 h volume balance into served demand,
leakage, and storage change SEPARATELY, against the reference case (PDA, leakage,
all PRVs x1.00). Attribute the inflow change to each component and report the
closure residual, so that the decomposition cannot hide anything.

RESULT:
Separable: true. Both components quantified in every case. Max absolute closure
residual across all cases: 5.31e-06 Mgal. Max relative volume-closure error:
1.556e-06. In the deepest perturbation (all PRVs x0.25) the inflow falls by
1.1571 Mgal, of which 0.0392 Mgal (3.39 %) is leakage saving and 1.1533 Mgal
(99.67 %) is unserved demand, at DSR 0.7596.

INFERENCE:
The two effects are separable to six significant figures, and at the deepest
perturbation they move together with the service loss dominating by a factor of 29.
This is exactly the confound the gate exists to expose, and it is now measured
rather than assumed. Any thesis result that reports a leakage reduction MUST report
the DSR alongside it.

STATUS:
PASS
```

**Verdict string:** `G8 LEAKAGE/SERVICE SEPARATION = PASS`

### 12.1 The decomposition in full

Reference: PDA, validation leakage, all PRVs ×1.00. All volumes in Mgal over 96 h.
"leak %" and "unserved %" are the shares of the inflow change attributable to each
component; they need not sum to 100 % because storage absorbs the remainder.

| family | scale | mean P (psi) | Δinflow | leak saving | service loss | Δstorage | closure residual | leak % | unserved % | DSR |
|---|---|---|---|---|---|---|---|---|---|---|
| A all PRVs | 0.25 | 93.690 | −1.15712 | 0.03918 | 1.15328 | +0.03534 | −2.09e-07 | 3.39 | 99.67 | 0.7596 |
| A all PRVs | 0.50 | 97.059 | −0.72353 | 0.02220 | 0.69419 | −0.00713 | +1.42e-07 | 3.07 | 95.95 | 0.8486 |
| A all PRVs | 0.75 | 100.420 | −0.28967 | 0.01010 | 0.23663 | −0.04294 | −1.14e-07 | 3.49 | 81.69 | 0.9374 |
| A all PRVs | 1.00 | 103.794 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | — | — | 0.9833 |
| A all PRVs | 1.25 | 100.828 | −1.88740 | 0.02542 | 0.49651 | −1.36546 | −5.31e-06 | 1.35 | 26.31 | 0.8963 |
| B active only | 1.10 | 104.700 | +0.00011 | −0.00303 | −0.07925 | −0.08217 | +1.08e-08 | — | — | 0.9987 |
| B active only | 1.25 | 106.067 | +0.00010 | −0.00739 | −0.08712 | −0.09440 | −4.59e-07 | — | — | 1.0002 |
| B active only | 1.50 | 108.345 | +0.00010 | −0.01416 | −0.08713 | −0.10119 | −3.34e-07 | — | — | 1.0002 |

Three things in this table are worth stating plainly.

**The A×1.25 row is dominated by storage, not by service or leakage.** Inflow falls
by 1.887 Mgal, of which 1.365 Mgal is storage. That is VALVE-179 reopening (X1) and
redirecting flow, and it is why the leak % and unserved % shares are small there
while the inflow change is the largest in the table.

**The family-B percentage columns are meaningless and are suppressed.** In those
cases the inflow change is ~1e-04 Mgal — the numerator of the share is a physical
change of ~0.003 to 0.014 Mgal while the denominator is numerical noise, which
produces the absurd raw values (up to 85 000 %) that are recorded verbatim in the
artefact. Reported here as dashes rather than deleted from the record.

**Reducing pressure in this network buys very little leakage and costs a great deal
of service.** At the deepest perturbation the ratio is 29:1 against. That is a
statement about the *distributed* network under the *validation* leakage instrument
at *uniform* PRV scaling — not a thesis result, not a prediction about a trained
controller, and not transferable to a tuned leakage model. It is stated because a
gate that found this and did not say it would be selecting evidence.

### 12.2 Per-case volume closure

Every one of the 18 cases closes far inside the 1e-4 relative threshold declared
before the runs:

| statistic | value |
|---|---|
| worst relative volume-closure error | 1.556e-06 (`PDA_leak_prv1.25`) |
| worst absolute closure residual | 5.31e-06 Mgal |
| worst instantaneous continuity residual (relative) | 1.399e-05 (`DDA_noleak_nominal`) |
| cases exceeding threshold | 0 of 18 |

---

## 13. Gate 9 — Mass Balance

Artefact: `results/phase5/g9_g10_full.json`, key `gate9`. Module:
`src/validation/g9_g10_full.py`.

**Threshold declared before any run**, in the module header, and never relaxed:
relative residual **< 1e-4**, normalised by total nodal withdrawal at the same
timestep. A second, independent tolerance of **5e-3** applies to the geometric
storage route, for reasons given in 13.2.

```
FACT:
Mass balance is the one check that cannot be argued with: inflow must equal served
demand plus leakage plus storage change, at every solved state and on the 96 h
totals. If it does not, every other number in this document is unsafe.

TEST:
Four 96 h cases: A = DDA no leakage, B = DDA with leakage, C = PDA with leakage
(identical to the gate 10 run, so the two gates cannot disagree about the same
hydraulics), D = identical to C but at the file's own ACCURACY 0.005 / TRIALS 40 as
a counter-test. For each, compute the instantaneous residual at all 193 states and
the integrated 96 h volume balance. Then recover the storage change a SECOND time
from tank geometry, V = pi*d^2/4 * level, which never touches the solver's storage
bookkeeping.

RESULT:
Cases A, B and C pass on both routes. Instantaneous max relative residual:
1.401e-05 (A), 4.502e-07 (B), 5.180e-07 (C). Volume relative residual: 7.167e-07
(A), 1.778e-08 (B), 1.192e-08 (C). 0 of 193 states above threshold in each. The
counter-test D FAILS as expected: max relative residual 1.767e-02 with 58 of 193
states above threshold, and a volume residual of 6.171e-04.

INFERENCE:
The model conserves mass at the adopted solver setting, confirmed by two
independent routes. The counter-test converts D6 from an assertion into a
measurement: at the file's own settings the maximum instantaneous imbalance is
25.6669 GPM while EPANET reports 0 errors and 0 warnings; at 1e-5 / 2000 it is
0.0008 GPM.

STATUS:
PASS
```

**Verdict string:** `G9 MASS BALANCE = PASS`

### 13.1 The four cases

Case D is excluded from the verdict by design — it exists to be failed.

| case | demand model | leakage | solver | inflow (Mgal) | served (Mgal) | leaked (Mgal) | Δstorage (Mgal) | max inst. rel. residual | states over threshold | volume rel. residual |
|---|---|---|---|---|---|---|---|---|---|---|
| A | DDA | no | 1e-5 / 2000 | 4.90665 | 5.19907 | 0.0 | −0.29242 | 1.401e-05 | 0 / 193 | 7.167e-07 |
| B | DDA | yes | 1e-5 / 2000 | 5.34415 | 5.19907 | 0.48803 | −0.34295 | 4.502e-07 | 0 / 193 | 1.778e-08 |
| C | PDA | yes | 1e-5 / 2000 | 5.34396 | 5.11310 | 0.48805 | −0.25720 | 5.180e-07 | 0 / 193 | 1.192e-08 |
| **D** | PDA | yes | **0.005 / 40** | 5.34393 | 5.11737 | 0.48805 | −0.26479 | **1.767e-02** | **58 / 193** | **6.171e-04** |

A and B deliver identical served volume to 7 significant figures (5.199073 Mgal),
which is the DDA invariance check: adding 0.488 Mgal of leakage under DDA changes
the inflow and the storage trajectory but not one gallon of delivered demand. C
delivers 0.0860 Mgal less — that is PDA curtailment, and it is the same effect G7
measured as DSR 0.9833.

### 13.2 The second, independent route — and its declared exclusion

Route 1 uses the solver's own nodal flows. Route 2 recovers the storage change from
tank geometry and never touches the solver's storage bookkeeping; agreement between
them is what makes the closure evidence rather than a tautology. Both tanks are
plain cylinders (`vol_curve_name is None`), so V = πd²/4 × level is exact, not an
approximation.

**Declared before any run:** the geometric comparison is evaluated on intervals in
which **no pump switched**. The reason is mechanical, not convenient. EPANET
subdivides the hydraulic timestep at a control-triggered switch, so the flow
reported at the start of such an interval is not the interval-average flow, and the
resulting error is arithmetic bookkeeping rather than a mass-balance failure. The
numbers show how large the distinction is:

| case | intervals with a pump switch | worst error, switch-free intervals | worst error, switch intervals |
|---|---|---|---|
| A (TANK-130) | 14 / 192 | 23.66 gal (2.68e-04 rel) | 65 184.97 gal (0.740 rel) |
| A (TANK-131) | 14 / 192 | 12.51 gal (5.94e-04 rel) | 20 704.30 gal (0.984 rel) |
| C (TANK-130) | 11 / 192 | 24.70 gal (3.62e-04 rel) | 57 493.53 gal (0.842 rel) |
| C (TANK-131) | 11 / 192 | 12.65 gal (6.19e-04 rel) | 18 371.67 gal (0.899 rel) |

The exclusion is disclosed rather than hidden, and both columns are in the artefact.

### 13.3 Why the geometric tolerance is 5e-3 and not 1e-4

EPANET writes its binary output in **float32**. The quantisation of a tank *level*
is therefore the quantisation of a large head value: TANK-131's head reaches
1155.5 ft, so one float32 step is 1.38e-04 ft, which for an 819.8 m² tank is a
storage floor of 9.09 gal. Against the largest interval storage change actually
observed, that floor is:

| tank | float32 level quantisation (ft) | storage floor (gal) | largest interval ΔV (gal) | floor / ΔV | headroom to the 5e-3 tolerance |
|---|---|---|---|---|---|
| TANK-130 | 1.025e-04 | 20.84 | 88 139.5 | 2.36e-04 | 21.2× |
| TANK-131 | 1.377e-04 | 9.09 | 21 051.3 | 4.32e-04 | 11.6× |

So the geometric route cannot in principle resolve better than ≈2.4e-04 to 4.3e-04
relative, and the declared 5e-3 tolerance sits an order of magnitude above that
floor with 11× to 21× headroom. The instantaneous flow-based route, which reads
flows rather than differences of large heads, is held to the much tighter 1e-4. The
two tolerances differ because the two instruments differ, and the reason is
computed rather than asserted.

---

## 14. Gate 10 — Full 96 h EPS

Artefact: `results/phase5/g9_g10_full.json`, key `gate10`.

Configuration: the full pre-flight environment — PDA at required 20 psi / minimum
0 psi, the G6 validation leakage on every junction, the distributed `[RULES]` and
`[CONTROLS]` exactly as shipped, solver 1e-5 / 2000, rule timestep 180 s, report
timestep 1800 s. This is the identical run to G9 case C, so the two gates cannot
disagree about the same hydraulics.

```
FACT:
Every earlier gate tested one thing in isolation. An RL environment runs all of them
at once, for the whole horizon, thousands of times. The question is whether the
combination is stable.

TEST:
One 96 h EPS in the full configuration. Check five criteria declared in advance: no
solver error; no actuator chattering (status changes in under 25 % of intervals);
tanks inside their declared limits with no pinning; every pump switch inside the
band its [RULES] declares; and physically sensible pressures - no negative pressure
at any junction at any state, and no pressure above 300 psi.

RESULT:
193 reported states over 96 h, 0 EPANET errors, 0 EPANET warnings, 0 WNTR warnings.
Both pumps switch 7 times = 3.6 % of 192 intervals, against the 25 % chatter
threshold; all 14 switches are inside the declared rule bands, 0 inconsistent. No
valve changes status at all. Both tanks stay inside their limits with 0 states
pinned at either limit and 7 direction reversals each. Mass balance: max relative
residual 5.180e-07, 0 of 193 states above threshold. The pressure criterion FAILED
on its ceiling when evaluated over all 126 junctions - 507.75 psi at JUNCTION-106 -
and PASSED when evaluated over the 121 demand-bearing junctions, max 288.22 psi at
JUNCTION-34.

INFERENCE:
The full configuration is stable over the whole horizon: no solver failure, no
chatter, no tank pinning, no rule violation, mass balance six orders of magnitude
inside threshold. The pressure ceiling failure is an instrument artefact, traced
below to five junctions the file declares at elevation 0.0 ft.

STATUS:
PASS
```

**Verdict string:** `G10 FULL PRE-FLIGHT EPS = PASS`

### 14.1 Actuator behaviour over the full horizon

| element | states observed | status changes | fraction of intervals | mean flow (GPM) | max \|flow\| (GPM) |
|---|---|---|---|---|---|
| PUMP-170 | Closed, Open | 7 | 0.0365 | 165.783 | 766.202 |
| PUMP-172 | Closed, Open | 7 | 0.0365 | 922.566 | 2 416.465 |
| VALVE-173 | Active | 0 | 0.0 | 4.719 | 7.904 |
| VALVE-174 | Closed | 0 | 0.0 | 0.000 | 0.000 |
| VALVE-175 | Active | 0 | 0.0 | 362.914 | 1 082.331 |
| VALVE-176 | Active | 0 | 0.0 | 256.905 | 782.033 |
| VALVE-177 | Active | 0 | 0.0 | 20.611 | 55.153 |
| VALVE-178 | Active | 0 | 0.0 | 39.239 | 94.298 |
| VALVE-179 | Closed | 0 | 0.0 | 0.000 | 0.000 |
| VALVE-180 | Closed | 0 | 0.0 | 0.000 | 0.000 |

Pump switch times (h): PUMP-170 at 1.5, 24.0, 31.5, 51.5, 58.0, 78.5, 84.0;
PUMP-172 at 3.0, 24.0, 37.5, 51.5, 62.0, 78.5, 88.5. Every one is verified against
the driving tank's level at that instant and every one is consistent with the rule.

### 14.2 Rule conformance, verified switch by switch

Declared bands, read from the file's own `[RULES]`:

- PUMP-172 follows TANK-130: open at level ≤ 12.1 ft, close at level ≥ 16.0 ft
- PUMP-170 follows TANK-131: open at level ≤ 15.4 ft, close at level ≥ 18.4 ft

Levels at which the switches actually fired:

| pump | driving tank | firing levels, in order (ft) |
|---|---|---|
| PUMP-172 | TANK-130 | 15.9646, 12.0829, 15.9359, 12.0748, 16.0111, 12.1017, 16.0002 |
| PUMP-170 | TANK-131 | 18.3283, 15.5222, 18.3690, 15.5512, 18.3853, 15.5412, 18.4104 |

14 of 14 switches consistent, 0 inconsistent. The small overshoots — 12.1017 against
a 12.1 open threshold, 18.4104 against an 18.4 close threshold — are the expected
consequence of a finite rule timestep: the rule is evaluated every 180 s and the
level moves between evaluations. They are reported rather than smoothed away.

### 14.3 Tank dynamics over the full horizon

| tank | observed range (ft) | declared limits (ft) | start | end | net | reversals | max interval Δ (ft) | states at a limit |
|---|---|---|---|---|---|---|---|---|
| TANK-130 | 11.9904 – 16.0111 | 0 – 32.1 | 15.1590 | 13.7820 | −1.3770 | 7 | 0.3361 | 0 |
| TANK-131 | 15.4149 – 18.4104 | 0 – 41.9 | 17.9451 | 16.8742 | −1.0709 | 7 | 0.3096 | 0 |

Both tanks cycle inside a narrow band well clear of both limits, never pin, and
reverse direction 7 times each — the signature of a working fill/draw cycle rather
than monotonic drift. Neither tank ends where it started; over 96 h TANK-130 loses
1.38 ft and TANK-131 loses 1.07 ft.

```
FACT:
An RL episode that starts from the shipped initial tank levels inherits this drift.

INFERENCE:
The net drawdown is small - 1.38 ft of a 32.1 ft tank, 1.07 ft of 41.9 ft - and does
not threaten stability over 96 h. It does mean the shipped initial condition is not
a periodic steady state, so an episode's start state and end state are not
interchangeable. This is recorded as a risk in section 18, not as a gate failure:
nothing in the brief requires a periodic initial condition, and manufacturing one
would change the network's shipped configuration.

STATUS:
PASS (reported, with the drift disclosed)
```

### 14.4 The pressure criterion, both node sets, and the instrument change

The pre-declared criterion was: no negative pressure anywhere, and no pressure above
300 psi. It was evaluated twice. Both results are reported.

| statistic | all 126 junctions | 121 demand-bearing junctions |
|---|---|---|
| mean pressure (psi) | 103.7944 | 94.7867 |
| min pressure (psi) | 4.1645 (JUNCTION-29) | 4.1645 (JUNCTION-29) |
| max pressure (psi) | **507.7488 (JUNCTION-106)** | **288.2206 (JUNCTION-34)** |
| negative-pressure states | 0 | 0 |
| node-states below 20 psi | 386 | 386 |
| max change between reports (psi) | 25.8712 (JUNCTION-105) | 6.7257 (JUNCTION-104) |
| states with a >25 psi change | 7 | 0 |
| physically sensible | **False** | **True** |

The instrument change is disclosed verbatim from the artefact, key
`gate10.pressure_instrument_note`:

> "The pre-declared criterion - no negative pressure anywhere and no pressure above
> 300 psi - was first evaluated over all 126 junctions and FAILED on the ceiling:
> 507.75 psi at JUNCTION-106. Investigation of the ORIGINAL file showed that value is
> not an unphysical hydraulic state but the head above datum at PUMP-170's discharge
> node, one of five junctions the file declares at elevation 0.0 ft with zero demand.
> The criterion is therefore evaluated a second time over the 121 demand-bearing
> junctions. Both results are reported; the verdict uses the service-junction set, and
> the reason for that choice is the declared elevation placeholder, not the outcome of
> the test."

The exclusion rule was fixed before it was applied and is stated in the artefact as:
"declared elevation exactly 0.0 ft AND zero total base demand; reported for
transparency, applied only to the pressure statistic". It selects exactly five nodes
and no others: the minimum non-zero elevation in the file is 192.0 ft and the maximum
is 1094.07 ft, so there is no borderline case — 0.0 ft is separated from the next
lowest elevation by 192 ft.

### 14.5 Discrepancy D7 — five junctions at elevation 0.0 ft bias every pressure statistic

| node | attached links | degree | base demand | elevation | mean pressure in the full EPS (psi) |
|---|---|---|---|---|---|
| JUNCTION-105 | LINK-166, PUMP-170 | 2 | 0 | 0.0 ft | 366.27 |
| JUNCTION-106 | LINK-167, PUMP-170 | 2 | 0 | 0.0 ft | 501.55 |
| JUNCTION-109 | LINK-15, PUMP-172 | 2 | 0 | 0.0 ft | 184.09 |
| JUNCTION-110 | LINK-17, PUMP-172 | 2 | 0 | 0.0 ft | 372.84 |
| JUNCTION-128 | LINK-18, LINK-19 | 2 | 0 | 0.0 ft | 184.15 |

All five are degree-2 pass-through nodes carrying zero demand, and
`all_touch_pump_or_reservoir` is True — four of them are pump suction/discharge nodes.
With elevation declared as 0.0 ft, EPANET reports pressure as head above datum, which
is why JUNCTION-106 reads 501.55 psi mean and 507.75 psi peak while no demand-bearing
junction exceeds 288.22 psi.

```
FACT:
The .inp declares five junctions at elevation exactly 0.0 ft with zero base demand.
The lowest non-zero elevation in the file is 192.0 ft.

TEST:
Recompute every pressure statistic in the full EPS over both node sets and compare.

RESULT:
Mean pressure 103.7944 psi over 126 junctions vs 94.7867 psi over 121: a +9.01 psi
bias. Max pressure 507.7488 psi (JUNCTION-106) vs 288.2206 psi (JUNCTION-34): a
+219.5 psi bias. Max inter-report pressure change 25.8712 psi (JUNCTION-105) vs
6.7257 psi (JUNCTION-104), and 7 states exceed a 25 psi jump vs 0.

INFERENCE:
These are almost certainly elevation placeholders, not surveyed values - a 0.0 ft
datum node adjacent to a pump is a common EPANET modelling shortcut. Whatever their
origin, including them in an aggregate pressure statistic inflates the mean by 9 psi,
inflates the maximum by 220 psi, and manufactures spurious 26 psi jumps that would
appear to an RL agent as pressure volatility. Reported as a discrepancy, not silently
corrected: the original file is untouched and the five nodes remain in the network.

STATUS:
PASS (discrepancy reported; the affected instrument is disclosed in 14.4)
```

### 14.6 Confound X3 — do the connector nodes contaminate the leakage instrument too?

The five nodes of D7 sit at 184–502 psi. The G6 validation leakage law is
`q = C·p^0.5`, so a high-pressure node leaks more than a low-pressure one for the same
coefficient. If a large share of total leakage came from placeholder-elevation nodes,
every leakage number in this report would be measuring the placeholder, not the
network.

```
FACT:
The G6 validation emitter is placed on every junction, including the five connector
nodes, with coefficients allocated by base demand.

TEST:
Sum the mean leak flow at the five connector nodes over the full EPS and divide by the
total mean leak flow. Separately, sum their emitter coefficients and divide by the
total.

RESULT:
Total mean leakage 84.72988 GPM; connector-node leakage 0.508205 GPM; share 0.5998 %.
Per node (mean GPM): 105 -> 0.11542, 106 -> 0.06714, 109 -> 0.06053, 110 -> 0.08545,
128 -> 0.17968. Coefficient share 0.3555 % of the total 8.765093.

INFERENCE:
The confound is real but negligible in magnitude. Because coefficients are allocated
by base demand and all five nodes have zero base demand, they receive only the
floor allocation - 0.36 % of the coefficient - which their high pressure amplifies to
0.60 % of the flow. No leakage conclusion in this report changes if they are removed.
The recommendation in section 19 is nevertheless to exclude them from the RL leakage
instrument, because 0.6 % of a reward signal attributable to an elevation placeholder
is 0.6 % of reward the agent could learn to chase.

STATUS:
PASS (confound quantified, bounded at 0.60 % of leak flow)
```

---

## 15. Gate 11 — Tank Dynamics

Artefact: `results/phase5/g1_g2_g11_baseline.json`, key
`runs.as_distributed_report_3600s.tanks`. Section 14.3 reports the tanks in the full
pre-flight configuration; this gate reports them in the baseline configuration — no
leakage, DDA, shipped solver settings — so the two can be compared and the effect of
the added instrumentation isolated.

| property | TANK-130 | TANK-131 |
|---|---|---|
| elevation (ft) | 843.90 | 1137.10 |
| diameter (ft) | 186 | 106 |
| declared min / max level (ft) | 0 / 32.1 | 0 / 41.9 |
| initial level (ft) | 15.159 | 17.945 |
| observed range (ft) | 12.1212 – 15.9769 | 15.3996 – 18.3484 |
| first / last level (ft) | 15.1590 / 13.9595 | 17.9451 / 16.9739 |
| range spanned (ft) | 3.8556 | 2.9488 |
| net change over 96 h (ft) | −1.1995 | −0.9712 |
| hit min level | False | False |
| exceeded max level | False | False |
| went negative | False | False |

```
FACT:
BWSN-1 has two tanks, both plain cylinders (vol_curve_name is None for both), driven
by two pumps under level-triggered [RULES].

TEST:
Run the baseline 96 h EPS and record, for each tank, the observed level range against
the declared limits, the number of direction reversals, the net change over the
horizon, and whether the level ever reaches a limit or goes negative.

RESULT:
TANK-130 cycles 12.1212 - 15.9769 ft inside declared limits 0 - 32.1 ft; TANK-131
cycles 15.3996 - 18.3484 ft inside 0 - 41.9 ft. Neither hits min, exceeds max, or goes
negative. Net change over 96 h: -1.1995 ft and -0.9712 ft respectively.

INFERENCE:
Tank dynamics are well behaved and the storage is not a binding constraint: both tanks
use roughly a tenth of their available depth and never approach a limit, so an RL agent
manipulating PRVs and pump speeds has room to move without immediately driving a tank
empty or overflowing. The small net drawdown is present in the baseline too - it is a
property of the shipped initial condition and demand pattern, not of the leakage or PDA
instrumentation added later. Comparing with 14.3: adding leakage and PDA widens the
observed band slightly (TANK-130 11.9904 - 16.0111 vs 12.1212 - 15.9769) and deepens
the drift from -1.1995 to -1.3770 ft, both in the expected direction for an added
withdrawal, and neither anywhere near a limit.

STATUS:
PASS
```

**Verdict string:** `G11 TANK DYNAMICS = PASS`

---

## 16. Gate 12 — Actuator Realizability

Artefact: `results/phase5/g12_realizability.json`.

This gate exists because every gate before it tested what the *network* does. G12 tests
what the *engine* does with a command — the property an RL action space actually
depends on. A commanded action is only an action if it reaches the solver, is applied,
and survives long enough to have an effect.

### 16.1 Method, declared before any run

Configuration: identical to the G10 full pre-flight configuration. Rule timestep 180 s,
report timestep 1800 s, solver 1e-5 / 2000. One command per run — 22 runs, no
compound commands, so no interaction can be mistaken for a realisation failure.

- PRV ladders: setting × 0.75 and × 1.25 of nominal, each valve separately.
- Pump speeds: 0.70, 0.85, 1.10. Justification recorded in the artefact: "inside the
  0.50-1.10 range gate 3 swept; 0.70 straddles the feasible bounds gate 3 measured
  (PUMP-170 shut at 0.80, PUMP-172 shut at 0.70) so the override case is measured, not
  assumed".
- Tolerances fixed before any run: command match 0.1 psi, pressure effect 0.01 psi,
  flow effect 0.01 GPM.
- Pressure statistic: the 121 demand-bearing junctions, per the D7 exclusion.
- No optimisation: "fixed deterministic ladders; no PPO, SAC, GA or search". No random
  seed — nothing in this gate is stochastic.

The decision rule, quoted from the artefact so it cannot be re-read after the fact:

> "PASS requires that every command reach the engine unchanged, that every Active PRV
> hold its setting within 0.1 psi, that every open pump run at the commanded speed at
> the moment it is issued, and that no command be inert, overridden, or overwritten.
> CONDITIONAL is returned when transmission and realisation are exact but part of the
> action space has no authority or does not persist. FAIL is reserved for the engine
> failing to apply a command it received."

### 16.2 Result

| measurable | result |
|---|---|
| command transmission (written value == read-back value) | **True** |
| Active PRV holds commanded setting within 0.1 psi | **True** |
| pump runs at commanded speed at the moment of issue | **True** |
| commanded pump speed persists over the horizon | **False** |
| commands tested | 22 |
| inert commands (no measurable effect anywhere) | 4 |
| overridden commands (engine substituted a different value) | 0 |
| speed commands reset by a native rule | 6 of 6 |
| commands driving negative service pressure | 1 |
| reset mechanism confirmed by controlled experiment | **True** |

Inert commands: `prv_VALVE-174_x0.75`, `prv_VALVE-179_x0.75`, `prv_VALVE-180_x0.75`,
`prv_VALVE-180_x1.25`. PRVs never Active at nominal: VALVE-174, VALVE-179, VALVE-180 —
the same three valves G5 identified, reached here by an independent measurement.

```
FACT:
An RL action space assumes a commanded value becomes a realised value.

TEST:
22 single-command runs in the full configuration. For each, read the setting back out
of the model after writing it, then read the realised setting out of the simulation
results at every reported state, and compare against the command within the declared
0.1 psi / 0.01 GPM tolerances.

RESULT:
Transmission is exact for all 22. Every Active PRV holds its commanded setting to
within tolerance for the whole horizon. Every pump applies the commanded speed at the
state it is issued. Four commands are inert - all on the three never-Active valves. Zero
commands are overridden. All 6 pump-speed commands are reset to 1.0 later in the
horizon by a native rule action.

INFERENCE:
The engine is faithful: it does what it is told, when it is told. Two separate defects
sit on top of that faithfulness - part of the PRV action space has no authority (the
inert commands), and no pump-speed command survives the next rule-driven reopening.
Neither is an engine failure, so neither is FAIL; both are real defects in the action
space as it currently stands, so this is not PASS.

STATUS:
CONDITIONAL
```

**Verdict string:** `G12 ACTUATOR REALIZABILITY = CONDITIONAL`

### 16.3 Disclosure — this gate's criterion was changed after it first returned FAIL

Quoted verbatim from `g12_realizability.json`, key `criterion_history`:

> **first_declared_criterion:** "pump_speed_realised_while_open: the realised relative
> speed must equal the command at every reported state at which the pump is open, over
> the whole 96 h horizon."
>
> **result_under_first_criterion:** "FAIL"
>
> **why_changed:** "The criterion conflated realisation with persistence. The engine does
> apply the commanded speed; a native rule action then replaces it. The run that produced
> FAIL issued the command once at t=0 and never reissued it, so it measured how long a
> command survives, not whether it is applied. The attribution test isolates the cause."
>
> **revised_criterion:** "pump_speed_realised_at_issue: the realised speed must equal the
> command at every open state before the first rule-driven reopening, and within a single
> 30 min control step. Persistence is reported separately and, because it fails, forces
> CONDITIONAL, not PASS."
>
> **result_under_revised_criterion:** "CONDITIONAL"
>
> **both_numbers_reported:** true

This is the one place in Phase 5 where a gate's criterion was rewritten after seeing a
result, so the reasoning is exposed rather than summarised. The change is defensible only
because the revision *splits* the original criterion into two measurables and reports
both — realisation passes, persistence fails — and because the failing half still
prevents a PASS verdict. It would not be defensible if the revision had discarded the
failing measurement. The original FAIL stands on the record above.

### 16.4 Attribution — a controlled experiment identifying the reset mechanism

Three runs per pump at commanded speed 0.85, differing only in the rules present:

- **R1** — rules intact, 96 h, command issued once at t = 0.
- **R2** — the one rule that reopens this pump removed, everything else identical.
- **R3** — a single 0.5 h step, so no rule can fire before the run ends.

| pump | run | open states | realisation \| open | first reset | realised speed values observed |
|---|---|---|---|---|---|
| PUMP-170 | R1 rules intact | 52 | 0.365 | 30.50 h | 0.0, 0.85, **1.0** |
| PUMP-170 | R2 RULE-4 removed | 19 | **1.000** | never | 0.0, 0.85 |
| PUMP-170 | R3 single step | 2 | **1.000** | n/a | 0.85 |
| PUMP-172 | R1 rules intact | 80 | 0.212 | 26.00 h | 0.0, 0.85, **1.0** |
| PUMP-172 | R2 RULE-1 removed | 17 | **1.000** | never | 0.0, 0.85 |
| PUMP-172 | R3 single step | 2 | **1.000** | n/a | 0.85 |

`mechanism_confirmed = True` for both pumps.

```
FACT:
Under intact rules, a commanded speed of 0.85 is realised at only 21-37 % of open states,
and the value 1.0 appears in the realised series even though it was never commanded.

TEST:
Remove only the rule that reopens the pump (R2), and separately shorten the horizon so no
rule can fire (R3). Change nothing else.

RESULT:
In both R2 and R3, for both pumps, realisation is exactly 1.000 and the value 1.0 never
appears. Removing the rule removes the reset; the reset time under R1 (30.50 h, 26.00 h)
coincides with a rule-driven reopening.

INFERENCE:
This is a demonstrated causal mechanism, not a correlation: the rule action
THEN PUMP <p> STATUS IS OPEN restores relative speed to 1.0, discarding the commanded
speed. The engine is not ignoring the command - it applies it, then a later rule
overwrites it. This is confound X4 and it is the reason G12 is CONDITIONAL rather than
PASS. The fix is stated in section 19 and requires no topology change.

STATUS:
Mechanism confirmed
```

### 16.5 Per-command persistence

| command | open fraction | realised before first reset | first reset (h) | realisation \| open | realisation \| horizon |
|---|---|---|---|---|---|
| speed PUMP-170 = 0.70 | 0.223 | shut (no open state) | 12.00 | 0.000 | 0.124 |
| speed PUMP-170 = 0.85 | 0.269 | **1.000** | 30.50 | 0.365 | 0.098 |
| speed PUMP-170 = 1.10 | 0.223 | **1.000** | 23.50 | 0.047 | 0.010 |
| speed PUMP-172 = 0.70 | 0.373 | shut (no open state) | 12.00 | 0.000 | 0.124 |
| speed PUMP-172 = 0.85 | 0.415 | **1.000** | 26.00 | 0.212 | 0.088 |
| speed PUMP-172 = 1.10 | 0.373 | **1.000** | 24.00 | 0.069 | 0.026 |

The two 0.70 cases have no open state *before* the reset, and this is not a realisation
failure: G3 measured the feasible speed bounds at 0.8152 for PUMP-170 and 0.7655 for
PUMP-172, so 0.70 is below shut-off for both and the pump is hydraulically incapable of
delivering against its static lift. Their non-zero open fractions (0.223, 0.373) are
entirely *post*-reset states, running at the rule-restored 1.0 rather than at the command —
which is why realisation-given-open is exactly 0.000 for both. G12 deliberately included a
speed below G3's bounds so that this case would be measured rather than assumed, and the
result confirms G3 from a second direction.

Reading the last two columns together separates the two defects. `realisation | open` is low
for every command (0.047–0.365) because it averages over the whole horizon, most of which is
post-reset. `realised before first reset` is exactly 1.000 wherever the pump can physically
run. The engine is faithful; the rule is what erases the command.

Realised statuses at nominal settings, for reference: VALVE-173, -175, -176, -177, -178
Active at all 193 states; VALVE-174, -179, -180 Closed at all 193 states. VALVE-180 is
commanded 16.45 psi and reports a realised setting of 0.00 psi — EPANET reports a closed
PRV's setting as 0. PUMP-170 is Closed at 151 and Open at 42 states; PUMP-172 Closed at
119 and Open at 74.

### 16.6 The one command that produced negative service pressure

`prv_VALVE-179_x1.25` — raising VALVE-179's setting by 25 % — drove the minimum pressure
over the 121 demand-bearing junctions to **−97.086 psi**, changed mean leakage by
−5.7594 GPM, and produced a maximum pressure change of 102.1483 psi somewhere in the
network. This is the same hazard G4 found by a different route (confound X1: VALVE-179
carries identically zero flow at scales × 0.25 through × 1.00, then 1212.15 GPM at × 1.25;
at × 1.5 the minimum pressure reached −99.3792 psi across 708 node-timesteps).

```
FACT:
VALVE-179 is Closed at every state under nominal settings and carries zero flow. Raising
its setting above a threshold between 1.00x and 1.25x of nominal reopens it.

INFERENCE:
This is a discontinuous, one-sided actuator: inert over the whole lower part of its range,
then abruptly admitting over a thousand GPM and pulling the network to large negative
pressures. For an RL agent this is the worst possible action geometry - a flat region that
teaches nothing, adjacent to a cliff that produces catastrophic states. It is not a
network defect and not something Phase 5 may fix: the brief forbids removing any PRV at
this stage. It is the single most important item in section 19.

STATUS:
Hazard confirmed and quantified (two independent measurements)
```

---

## 17. Overall Decision

### 17.1 Gate verdict table

| gate | subject | verdict |
|---|---|---|
| G0 | file integrity | **PASS** |
| G1 | baseline EPANET/WNTR convergence | **PASS** |
| G2 | native control logic | **CHARACTERISED** (descriptive gate, no pass/fail) |
| G3 | pump speed response | **PASS** |
| G4 | PRV actuator responsiveness | **PASS** |
| G5 | PRV action-dimension audit | **CONDITIONAL** |
| G6 | leakage model validation | **PASS** |
| G7 | PDA response | **PASS** |
| G8 | leakage/service separation | **PASS** |
| G9 | mass balance | **PASS** |
| G10 | full 96 h pre-flight EPS | **PASS** |
| G11 | tank dynamics | **PASS** |
| G12 | actuator realizability | **CONDITIONAL** |

Reproduced end to end by `src/validation/run_all.py`: 7 modules, 0 non-zero exits,
≈ 31 s total (2.8 / 2.7 / 3.6 / 7.8 / 5.5 / 3.2 / 5.6 s). Console log preserved at
`results/phase5/run_all_console.txt`.

### 17.2 Decision

**OVERALL = CONDITIONAL PASS**

The hydraulics pass without qualification. Eleven of thirteen gates PASS, one is
descriptive, and the two that are CONDITIONAL — G5 and G12 — are both about the *action
space*, not about whether the network solves. Specifically:

- Nothing failed. No gate returned FAIL.
- The solver converges, mass balance closes to 5.18e-07 relative, the 96 h EPS runs with
  0 errors and 0 warnings, tanks never pin, no actuator chatters, and every native rule
  fires where it says it will.
- The leakage model and PDA both respond monotonically and separably (G6, G7, G8), so the
  reward signal a later phase will build is measurable.
- The engine faithfully applies every command it receives (G12 transmission and
  realisation both exact).

What is *not* ready is the action space as the shipped file presents it:

- 3 of the 8 PRVs (VALVE-174, -179, -180) are Closed at every state and carry identically
  zero flow. Two independent gates found this (G5 by flow share, G12 by inert command).
  Four of the 22 G12 commands were inert, all on those three valves.
- No commanded pump speed survives the horizon: all 6 speed commands are reset to 1.0 by a
  native rule action, mechanism confirmed by controlled experiment.
- VALVE-179 is a cliff actuator: inert to × 1.00, then −97 psi service pressure at × 1.25.

CONDITIONAL PASS is the correct verdict because every one of those three items has a known,
non-invasive fix that requires no change to BWSN-1's topology and no removal or addition of
any PRV (section 19). Per the brief, D-Town is not proposed — the failure conditions that
would justify it (a fundamental hydraulic defect with no standard correction) are absent —
and no other change to the thesis architecture is proposed here.

### 17.3 Consolidated discrepancies between the `.inp` and the Phase 4 report

All seven are reported, none silently corrected. The original file is untouched.

| # | discrepancy | evidence | consequence |
|---|---|---|---|
| D1 | pattern length | 4 patterns with 96/96/48/96 multipliers = 48/48/24/48 h cycles at the 0:30 pattern timestep, not 8 h; Phase 4 counted lines in the `.inp`, not multipliers | Phase 4's "unrealistically short demand cycle" inference must be **retracted**; the patterns are multi-day |
| D2 | dead patterns | PATTERN-0 on 77 junctions (943.910 GPM), PATTERN-1 on 2 junctions (0.800 GPM), no pattern on 47 junctions; total 944.710 GPM. PATTERN-2 and PATTERN-3 are defined but referenced by nothing | 2 of 4 patterns are inert; demand stochasticity in a later phase cannot be built by perturbing them |
| D3 | rule timestep | file declares 180 s; WNTR's default is 360 s. Max \|ΔP\| between the two = 0.0459 psi, and 7/7 pump switches identical | small but real; adopt 180 s to match the file |
| D4 | report vs hydraulic timestep | report 3600 s against a 0:30 hydraulic step → 97 states instead of 193. Cross-check at both resolutions: max \|ΔP\| = 0.0 m | half the hydraulic states were invisible; adopt 1800 s |
| D5 | PRV activity | Phase 4's "7 of 8 PRVs active at start" is wrong: VALVE-174, -179, -180 all carry identically zero flow. Only VALVE-180 is closed by `[CONTROLS]`; the other two are closed by hydraulics | the usable PRV count is **5**, not 7 or 8 |
| D6 | shipped solver settings return unconverged states | at the file's `ACCURACY 0.005 / TRIALS 40`: emitter law violated by 2.01 GPM, continuity by 9.97 GPM, max instantaneous imbalance 25.6669 GPM, 58/193 states over threshold — with **0 EPANET errors and 0 warnings**. At 1e-5/2000: 0.0008 GPM | the engine reports success while silently returning non-solutions; `ACCURACY 1e-5 / TRIALS 2000` is mandatory, not a preference |
| D7 | five junctions at elevation 0.0 ft | mean pressure 103.7944 vs 94.7867 psi (+9.01); max 507.7488 at JUNCTION-106 vs 288.2206 at JUNCTION-34 (+219.5); max inter-report change 25.8712 vs 6.7257 psi; 7 states >25 psi vs 0 | every aggregate pressure statistic over all 126 junctions is biased; use the 121 demand-bearing junctions |

### 17.4 Consolidated confounds

Each of these is an alternative explanation that was tested rather than assumed away.

| # | confound | how it was tested | outcome |
|---|---|---|---|
| X1 | VALVE-179 reopening could make any PRV sweep look responsive for the wrong reason | swept the setting from × 0.25 to × 1.5 and recorded flow and minimum service pressure at each step | **real and severe.** Mean flow 0 GPM at × 0.25 – × 1.00, then 1212.1509 GPM at × 1.25; min service pressure −97.086 psi at × 1.25 (G12) and −99.3792 psi across 708 node-timesteps at × 1.5 (G4). Handled by section 19 item 1 |
| X2 | apparent leakage reduction could be PDA demand starvation, not pressure management | decomposed the change into a leakage term and a delivered-demand term per case (G8), and compared nodal pressures between × 0.25 and × 0.75 | **real but bounded and explained.** 84 junctions rise and 33 fall — curtailment reduces withdrawal, which reduces friction loss, which raises pressure elsewhere. G8 closes the decomposition per case, so leakage and service are separable |
| X3 | the D7 connector nodes could dominate the leakage instrument because they sit at 184–502 psi | summed their leak flow and emitter coefficients as a share of the total | **real but negligible.** 0.508205 of 84.72988 GPM = **0.5998 %** of leak flow; 0.3555 % of the total coefficient 8.765093. No leakage conclusion changes; excluded from the RL instrument as a precaution |
| X4 | the pump-speed failure could be an engine defect rather than a rule action | removed only the reopening rule (R2), and separately shortened the horizon so no rule can fire (R3) | **mechanism identified.** Realisation is exactly 1.000 in R2 and R3 for both pumps and the value 1.0 never appears; `THEN PUMP <p> STATUS IS OPEN` restores relative speed to 1.0. Not an engine defect — a rule side-effect. Fix in section 19 item 5 |

### 17.5 Instrument and criterion changes, disclosed

Four places in this phase measure something differently from the first thing tried. Each is
listed with what changed, why, and where both numbers appear.

| gate | what changed | why | both results reported |
|---|---|---|---|
| G6, G7 | mean pressure replaced by a nodal **pressure-dominance partial order** plus a tolerance sweep | mean pressure is not a sufficient statistic for total leakage: a redistribution can lower the mean and raise total leakage. A partial order over all nodes is falsifiable; a mean is not | yes — §10, §11 |
| G9 | geometric storage agreement evaluated on **switch-free intervals only**, tolerance 5e-3 not 1e-4 | EPANET subdivides the hydraulic timestep at a control-triggered switch, so a switch interval's endpoints do not bracket a single timestep. The exclusion was pre-declared in the module header, before the run. The 5e-3 tolerance is set by float32 binary-output quantisation (2.36e-04 and 4.32e-04 relative), not chosen to fit | yes — §13.2, §13.3; the independent flow-route check keeps the 1e-4 threshold and passes at 5.180e-07 |
| G10 | pressure criterion evaluated over **121 demand-bearing junctions** instead of all 126 | five junctions are declared at elevation exactly 0.0 ft with zero demand; EPANET reports their pressure as head above datum. The reason is the declared placeholder, not the outcome | yes — §14.4 table, both columns, and the verbatim note |
| G12 | one criterion split into **realisation** and **persistence** | the original criterion conflated the two and returned FAIL for a reason that was actually a rule side-effect. The split reports both; persistence still fails and still blocks PASS | yes — §16.3 quotes the original FAIL verbatim |

### 17.6 What this decision does not claim

Stated explicitly, because the brief requires it. Nothing in this report claims or implies:

- that PPO will succeed on this environment;
- that BWSN-1 is the best available network for this thesis;
- that BWSN-1 is better or worse than D-Town;
- that leakage will drop by any particular percentage;
- that a learned controller will beat any baseline.

Phase 5 asked one question — can BWSN-1 be a stable, solvable, controllable hydraulic
environment — and answers it with **CONDITIONAL PASS** on hydraulic and actuator evidence
only. Every number in this report comes from a deterministic run recorded in
`results/phase5/`. The G6 validation leak coefficient exists solely to make leakage
measurable in this phase and **must not enter any thesis result**.

---

## 18. Remaining Risks

Risks that survive the corrections in section 19, ordered by how much they could distort a
later result.

**R1 — the effective PRV action space is 5, not 8.** VALVE-174, -179 and -180 are Closed at
every one of 193 states and carry identically zero flow. Section 19 handles VALVE-179's
cliff, but handling it does not make the valve useful. If all 8 are kept as action
dimensions, 3 dimensions are noise the agent must learn to ignore, which costs sample
efficiency and makes any policy-interpretability claim harder to defend. Phase 5 is
forbidden from removing a PRV, so this is recorded, not fixed. *Evidence: G5, G12 inert
commands.*

**R2 — pump speed is a weak actuator unless the rules are addressed.** Even with re-issue
after every reopen (section 19 item 5), the pumps are open only 22–42 % of the horizon, so a
speed command has no effect most of the time. G3 also bounds the usable range from below:
below 0.8152 (PUMP-170) and 0.7655 (PUMP-172) the pump cannot deliver against its static
lift and simply shuts. The usable speed band is therefore roughly 0.8–1.1, not 0.5–1.1.
*Evidence: G3 feasible bounds, G12 open fractions.*

**R3 — the shipped initial condition is not a periodic steady state.** Over 96 h TANK-130
loses 1.377 ft and TANK-131 loses 1.071 ft in the full configuration (−1.200 and −0.971 ft in
the baseline). Episodes starting from the shipped levels inherit a drift, so an episode's
start and end states are not interchangeable and reward accumulated late in an episode is
not directly comparable with reward accumulated early. Constructing a periodic initial
condition would change the shipped configuration and is out of scope here. *Evidence: G11,
§14.3.*

**R4 — 386 node-states below 20 psi in the baseline full EPS, before any agent acts.** The
PDA required pressure is 20 psi, so the network already curtails demand somewhere at
nominal settings, and the minimum service pressure is 4.1645 psi at JUNCTION-29. A reward
that penalises sub-threshold pressure will therefore carry a non-zero floor the agent cannot
remove, and a naive "pressure violations" metric will look bad for reasons that predate the
controller. This needs an explicit baseline subtraction in the reward or metric design.
*Evidence: G10 pressure statistics, both node sets.*

**R5 — demand stochasticity cannot be built by perturbing the shipped patterns alone.**
PATTERN-0 drives 77 junctions (943.910 GPM), PATTERN-1 drives 2 junctions (0.800 GPM),
47 junctions have no pattern at all, and PATTERN-2 and PATTERN-3 are defined but referenced
by nothing. Scaling PATTERN-1 moves 0.08 % of demand; the 47 unpatterned junctions do not
respond to pattern perturbation at all. The uncertainty component of the research question
will need a demand-perturbation mechanism designed deliberately, not inherited from the
file. *Evidence: D2.*

**R6 — the solver setting is load-bearing and easy to lose.** At the file's own
`ACCURACY 0.005 / TRIALS 40` the engine returns states violating the emitter law by 2.01 GPM
and continuity by 9.97 GPM while reporting 0 errors and 0 warnings. Any script, notebook or
config that loads the `.inp` without re-applying `1e-5 / 2000` will silently train on
non-solutions. This must be enforced in code, not documented in prose. *Evidence: D6, G9
case D — 25.6669 GPM max imbalance, 58/193 states over threshold.*

**R7 — leak-coefficient magnitude is unvalidated against any field data.** The G6 coefficient
was sized so leakage is measurable but not dominant (total 84.72988 GPM mean against
944.710 GPM base demand ≈ 9 %). That is a deliberate instrument choice for feasibility
testing, and it is explicitly **not** calibrated to BWSN-1 or to any real network. Phase 5
forbids optimising it, and this report forbids reusing it. Whatever coefficient the thesis
eventually uses needs its own justification. *Evidence: G6 §10.2.*

**R8 — PDA feedback couples the two reward terms.** Curtailment at one node reduces
withdrawal, reduces friction loss, and raises pressure at other nodes: 84 junctions rose
while 33 fell between × 0.25 and × 0.75. Leakage and service are separable (G8 closes the
decomposition per case) but they are not independent, so a multi-objective reward cannot
treat the two terms as orthogonal without justification. *Evidence: X2, G8.*

**R9 — reproducibility depends on one pinned toolchain.** All results here come from
wntr 1.5.0 with EPANET DLL 20200 (`epanet2.dll`), on Python 3.13.15 / Windows 11. The EPyT
engine present in the same environment is EPANET 20305 — a *different engine version*. No
result in this report was cross-validated between the two engines, so an engine change is an
untested variable. *Evidence: §3.*

---

## 19. Exact Changes Required Before RL

Nine changes. None alters BWSN-1's topology, and none adds or removes a PRV. The original
`.inp` stays untouched; every change belongs in the environment-construction code or in the
working copy.

**1. Constrain or reshape VALVE-179's action range — highest priority.** The valve is inert
from × 0.25 to × 1.00 of nominal and then admits 1212.1509 GPM at × 1.25, driving service
pressure to −97.086 psi (G12) and −99.3792 psi across 708 node-timesteps at × 1.5 (G4). An
unconstrained action dimension here lets a random early-training action produce catastrophic
states. Two admissible options, both of which keep the valve in the network: cap its
commanded setting below the reopening threshold, or bound the whole PRV action space to
settings verified not to produce negative service pressure. The threshold lies between
× 1.00 and × 1.25 and has **not** been bracketed more finely — that measurement is owed
before the bound is chosen. *Do not remove the valve: the brief forbids it, and G5 was
explicitly instructed to present evidence only.*

**2. Set `ACCURACY = 1e-5` and `TRIALS = 2000` in code, on every load.** The file ships
`0.005 / 40`, which returns states violating the emitter law by 2.01 GPM and continuity by
9.97 GPM while EPANET reports 0 errors and 0 warnings (D6). At 1e-5 / 2000 the same
violation is 0.0008 GPM. This must be applied programmatically after every
`WaterNetworkModel` load, and asserted, so it cannot be lost by loading the `.inp` somewhere
else. It is the single change without which every other number is unreliable.

**3. Set the rule timestep to 180 s.** The file declares 180 s; WNTR defaults to 360 s. The
measured difference is small — max |ΔP| 0.0459 psi, 7/7 pump switches identical — but the
file's own declared value is the correct one and there is no reason to run at a coarser rule
resolution than the model specifies (D3).

**4. Set the report timestep to 1800 s to match the 0:30 hydraulic step.** At 3600 s only 97
of 193 hydraulic states are observable. A cross-check at both resolutions found max |ΔP| =
0.0 m, so this changes nothing physically — it changes what the agent and the metrics can
*see* (D4). An RL environment whose observation interval is twice its hydraulic interval
discards half its own states.

**5. Handle the pump-speed reset.** `THEN PUMP <p> STATUS IS OPEN` restores relative speed to
1.0, discarding a commanded speed; mechanism confirmed by controlled experiment for both
pumps (X4, §16.4). Two admissible fixes:

- **(a)** re-issue the commanded speed after every rule-driven reopening — i.e. write the
  speed at every control step rather than once, which an RL environment stepping every 30 min
  does naturally; or
- **(b)** in the working copy, replace the rules' `STATUS IS OPEN` action with
  `SETTING IS <speed>`, which opens the pump *at* a speed instead of at 1.0.

Option (a) is preferred: it leaves the shipped control logic intact and puts the fix in the
environment, which keeps the native-controls baseline directly comparable with the learned
controller. Whichever is chosen, **verify realisation after the fix** — the G12 per-command
persistence table (§16.5) is the before-measurement to compare against.

**6. Exclude the five elevation-0.0 ft junctions from every pressure statistic.** JUNCTION-105,
-106, -109, -110, -128 are degree-2, zero-demand, pump-adjacent nodes whose declared elevation
is exactly 0.0 ft. Including them inflates mean pressure by 9.01 psi, inflates the maximum by
219.5 psi, and manufactures 7 spurious inter-report jumps above 25 psi (D7). Every pressure
observation, every pressure reward term and every pressure metric should use the 121
demand-bearing junctions. The exclusion rule is mechanical — elevation exactly 0.0 ft and zero
base demand — and unambiguous, since the next lowest elevation in the file is 192.0 ft.

**7. Exclude the same five junctions from the leakage instrument.** They carry 0.5998 % of mean
leak flow and 0.3555 % of the total emitter coefficient (X3). The effect is small enough that
no conclusion in this report depends on it, and large enough that it is reward the agent could
learn to chase for a reason that is an elevation placeholder. Place leak emitters on
demand-bearing junctions only.

**8. Bound the pump-speed action to the measured feasible range, not 0.5–1.1.** G3 measured
shut-off at 0.8152 for PUMP-170 and 0.7655 for PUMP-172; G12 confirmed it independently — a
0.70 command yields zero open states. Below those bounds the pump cannot overcome its static
lift and the command is hydraulically void, so a speed dimension spanning 0.5–1.1 spends a
third of its range on actions with no possible effect. Use a lower bound at or above each
pump's measured shut-off point.

**9. Record the baseline pressure-deficit floor before designing the reward.** At nominal
settings the full pre-flight EPS already has 386 node-states below the 20 psi PDA threshold and
a minimum service pressure of 4.1645 psi (JUNCTION-29). Any service-pressure penalty must be
stated relative to this floor, otherwise a metric will attribute pre-existing deficit to the
controller. The floor is measured and available in `results/phase5/g9_g10_full.json`.

Two items are explicitly **not** in this list, and their absence is deliberate. Removing
VALVE-174, -179 or -180 from the action space is forbidden at this stage — G5 was instructed to
present evidence only, so the evidence is in §9 and §16 and the decision belongs to the
researcher. And no change to the thesis architecture, network choice, or experimental design is
proposed: D-Town is not proposed, because no gate returned FAIL and no fundamental hydraulic
defect was found.

---

## 20. Summary

```
NETWORK = BWSN-1
HYDRAULIC CONVERGENCE = PASS
PDA = PASS
LEAKAGE = PASS
PUMP SPEED CONTROL = PASS
PRV CONTROL = PASS
8-PRV ACTION SPACE = CONDITIONAL
MASS BALANCE = PASS
96h EPS = PASS

OVERALL = CONDITIONAL PASS

NEXT STEP =
Implement the RL environment on BWSN-1, applying the nine changes in section 19 before any
training. Two of those changes must be verified by measurement, not assumed: (i) bracket
VALVE-179's reopening threshold between x1.00 and x1.25 of nominal and bound the PRV action
range below it, and (ii) confirm that a commanded pump speed is realised at every open state
once it is re-issued at each control step. Both re-use the existing Phase 5 harness, so both
are cheap. The two CONDITIONAL gates - G5 (effective PRV action space is 5 of 8) and G12
(commanded pump speed does not persist) - are action-space defects with known non-invasive
fixes, not hydraulic failures; no gate returned FAIL, so BWSN-1 is retained and no change to
the approved thesis architecture is proposed. The G6 validation leak coefficient must not
enter any thesis result.
```

The block above uses the mandated keys, which admit only PASS/FAIL on most lines. To
prevent a line from being quoted more broadly than it was measured, each key maps to
these gates:

| summary key | gate(s) it reports | caveat carried elsewhere in this report |
|---|---|---|
| HYDRAULIC CONVERGENCE | G1, and G9/G10 in the full configuration | requires `ACCURACY 1e-5 / TRIALS 2000`; at the file's shipped `0.005 / 40` this line would not be PASS (D6) |
| PDA | G7 | — |
| LEAKAGE | G6, separability by G8 | validation coefficient only; not calibrated, must not enter thesis results |
| PUMP SPEED CONTROL | G3 — hydraulic response to a speed change | the *command* does not persist: G12 persistence = False, fixed by §19 item 5; usable range is ~0.8–1.1, not 0.5–1.1 |
| PRV CONTROL | G4 — actuator responsiveness of the Active valves | VALVE-179's reopening cliff (X1) must be bounded first, §19 item 1 |
| 8-PRV ACTION SPACE | G5, corroborated by G12 inert commands | 5 of 8 valves carry flow; no PRV removed in this phase, per the brief |
| MASS BALANCE | G9 | flow route at 1e-4; geometric route at 5e-3 on switch-free intervals (§13.2, §13.3) |
| 96h EPS | G10 | pressure criterion evaluated on the 121 demand-bearing junctions (§14.4, D7) |

*End of Phase 5 pre-flight report. Every number above is traceable to a deterministic
artefact in `results/phase5/`; the whole phase reproduces with
`.venv/Scripts/python.exe src/validation/run_all.py` in ≈ 31 s.*
