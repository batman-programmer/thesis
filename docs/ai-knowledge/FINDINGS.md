# FINDINGS.md

Every finding produced by this project, small ones included. Each carries
evidence, source artefact, confidence, validation status, implications and any
unresolved aspect.

Confidence scale: **High** = measured by code on this machine with the result
written to a JSON artefact; **Medium** = measured once, or read from a file
without independent confirmation; **Low** = inferred.

---

## Group A — Solver and numerical integrity

### F-01 · The file's shipped solver settings silently return non-solutions
`VERIFIED_FACT` · **High** · VALIDATED

**Finding.** At the `.inp` file's own `ACCURACY 0.005 / TRIALS 40`, EPANET returns
states that violate the emitter law by **2.0135 GPM** and continuity by
**9.9692 GPM**, with a maximum instantaneous imbalance of **25.6669 GPM** and
**58 of 193 states** over the residual threshold — while reporting **0 EPANET
errors and 0 warnings**. At `ACCURACY 1e-5 / TRIALS 2000` the same violation is
**0.0008 GPM**.

**Evidence.** Phase 5 discrepancy D6; Gate 9 counter-test case D.
Max relative residual 1.767e-02 at shipped settings vs 5.180e-07 at 1e-5/2000.
Volume residual 6.171e-04 vs 1.192e-08.

**Source.** `results/phase5/g9_g10_full.json`;
`docs/phase5_bwsn_preflight.md` §10.5, §13.

**Implication.** This is the single most important finding in the project. Every
other number depends on it. `ACCURACY 1e-5 / TRIALS 2000` must be set in code on
every model load and **asserted**, because a `.inp` loaded anywhere else silently
reverts. *"This must be enforced in code, not documented in prose."*

**Unresolved.** None. It was converted from assertion to measurement by the Gate 9
counter-test.

---

### F-02 · Mass balance holds at the adopted settings, verified by two independent routes
`VERIFIED_FACT` · **High** · VALIDATED

**Finding.** Instantaneous max relative residual **1.401e-05** (DDA no leak),
**4.502e-07** (DDA + leak), **5.180e-07** (PDA + leak). Volume relative residual
7.167e-07 / 1.778e-08 / 1.192e-08. **0 of 193 states** above the pre-declared
1e-4 threshold in each case.

**Evidence.** The second route recovers storage change from tank geometry
(`V = π d²/4 · level`), never touching the solver's own storage bookkeeping. A
separate 5e-3 tolerance applies to that geometric route, declared in advance and
never relaxed.

**Source.** Gate 9, `results/phase5/g9_g10_full.json`.

**Implication.** The hydraulic base is trustworthy. Threshold declared *before*
the run, in the module header.

---

### F-03 · Report cadence changes what is written, not what is computed
`VERIFIED_FACT` · **High** · VALIDATED

**Finding.** Cross-check at report timestep 1800 s vs 3600 s: **max |ΔP| = 0.0 m**
over the 97 common timesteps. But at 3600 s only **97 of 193** hydraulic states
are observable.

**Source.** Phase 5 discrepancy D4.

**Implication.** Use 1800 s. An RL environment whose observation interval is twice
its hydraulic interval discards half its own states — for no physical reason.

---

### F-04 · Rule timestep 180 vs 360 s barely matters, but 180 s is what the file declares
`VERIFIED_FACT` · **High** · VALIDATED

**Finding.** The file declares 180 s; WNTR defaults to **360 s**. Measured
difference: **max |ΔP| 0.0459 psi**, **7/7 pump switches identical**.

**Source.** Phase 5 discrepancy D3.

**Implication.** Small, but there is no reason to run coarser than the model
specifies. Set it explicitly.

---

## Group B — Network structure and shipped configuration

### F-05 · Composition verified from the `.inp`
`VERIFIED_FACT` · **High** · VALIDATED

126 junctions · 1 reservoir · 2 tanks · 168 pipes · 2 pumps (HEAD CURVE-0,
CURVE-2) · 8 PRVs · 4 `[RULES]` · Duration 96:00 @ 0:30 · GPM/psi/ft ·
Hazen-Williams. `CURVE-1` exists but is referenced by nothing. `[EMITTERS]` is
empty. `[ENERGY]` Global Efficiency 75 %, Global Price 0.

**Source.** Gate 0, `results/phase5/g0_integrity.json`.

---

### F-06 · The demand patterns are 48/48/24/48-hour cycles, not 8-hour
`VERIFIED_FACT` · **High** · VALIDATED — **and it retracts a Phase 4 claim**

**Finding.** The four patterns have **96 / 96 / 48 / 96 multipliers** at the 0:30
pattern step, i.e. **48 / 48 / 24 / 48 hour cycles**.

Phase 4 had written "4 patterns of 16/16/8/16 entries … an 8-hour cycle repeated
over 96 h". **That inference is formally retracted.**

**Source.** Phase 5 discrepancy D1.

**Implication.** The *decision* to replace the native patterns with a 24-h diurnal
profile stands. Only the description of what is being replaced was wrong. Any
thesis text repeating "8-hour cycle" must be corrected.

---

### F-07 · Pattern assignment is sparse and two patterns are dead
`VERIFIED_FACT` · **High** · VALIDATED

| Pattern | Junctions | Base demand |
|---|---|---|
| PATTERN-0 | 77 | 943.910 GPM |
| PATTERN-1 | 2 | 0.800 GPM |
| (no pattern) | 47 | — |
| PATTERN-2, PATTERN-3 | defined, referenced by nothing | — |
| **Total** | 126 | **944.710 GPM** |

**Source.** Phase 5 discrepancy D2.

**Implication.** 47 junctions have a constant demand. Two patterns are dead
weight. The imposed diurnal model must decide explicitly what to do with the 47.

---

### F-08 · Five junctions at elevation 0.0 ft bias every pressure statistic
`VERIFIED_FACT` · **High** · VALIDATED

**Finding.** JUNCTION-105, -106, -109, -110, -128 are degree-2, zero-demand,
pump/reservoir-adjacent, declared elevation **exactly 0.0 ft**. EPANET reports
head-above-datum there.

| Statistic | All 126 junctions | 121 demand-bearing |
|---|---|---|
| Mean pressure | 103.7944 psi | **94.7867 psi** (−9.01) |
| Max pressure | 507.7488 at JUNCTION-106 | **288.2206 at JUNCTION-34** (−219.5) |
| Max inter-report change | 25.8712 psi | **6.7257 psi** |
| States > 25 psi jump | 7 | **0** |

**Source.** Phase 5 discrepancy D7, Gate 10 §14.5.

**Implication.** The Gate 10 pressure criterion **FAILED** on its 300 psi ceiling
over all 126 junctions and **PASSED** over the 121. Every pressure observation,
reward term, metric and leak emitter must use the 121. Exclusion rule: elevation
exactly 0.0 ft AND zero total base demand — unambiguous, since the next lowest
elevation in the file is 192.0 ft.

**Unresolved.** None. Confound X3 quantified the leakage side too — see F-19.

---

### F-09 · Two junctions are permanently below the service threshold in the shipped network
`VERIFIED_FACT` · **High** · VALIDATED

**Finding.** With no perturbation at all:

| Junction | Mean pressure | Min pressure | Elevation |
|---|---|---|---|
| JUNCTION-29 | 5.1202 psi | **4.1645 psi** | 846.28 ft |
| JUNCTION-126 | 16.7387 psi | 16.6168 psi | 434.00 ft |

**386 node-states below 20 psi = 2 junctions × 193 states.** The same two
junctions were the only ones below 20 psi in the leak-free DDA baseline (194
node-states there, out of 12 222).

**Source.** Gate 7 §11.2, Gate 1.

**Implication.** **This is a property of the distributed network, not of PDA or of
the leakage instrument.** Any service-pressure penalty must be stated *relative to
this floor*, or a metric will attribute pre-existing deficit to the controller.
Recorded in `results/phase5/g9_g10_full.json`.

---

## Group C — Actuator behaviour

### F-10 · The PRV mechanism itself is essentially exact
`VERIFIED_FACT` · **High** · VALIDATED

**Finding.** When a PRV is Active, EPANET holds the commanded downstream pressure
to within **2.67e-05 psi** — across every valve and every commanded setting in a
13-point grid.

**Source.** Gate 4, `results/phase5/g4_g5_prv.json`.

**Implication.** Responsiveness is a property of *individual valves in this
configuration*, not of the mechanism. Where a valve is unresponsive, that is
hydraulics, not a modelling defect.

---

### F-11 · VALVE-174 has benign but strictly adverse authority
`VERIFIED_FACT` · **High** · VALIDATED

**Finding.** Hydraulically Closed at its nominal 80 psi. Reopens between **95 and
96 psi**; Active 100 % of the time above that. When open it carries only
**4.7–5.0 GPM ≈ 0.5 % of demand**. Reopening raises leakage **84.730 → 84.968 GPM**
with **zero** measured change in served demand or in the pressure-deficit count.

**Source.** `results/phase6/p6_s3_prv_finechar.json`;
`docs/phase6_g5_g12_resolution.md` §7.

**Implication.** Its only measured effect is adverse. Excluded from the action
space, fixed at 80 psi, **not removed from the model**.

---

### F-12 · VALVE-179 is a cliff actuator: the cliff is between 44.8 and 44.9 psi
`VERIFIED_FACT` · **High** · VALIDATED

**Finding.** Closed at nominal 40 psi. Opens at **43 psi**. The transition to
catastrophe is **between 44.8 and 44.9 psi** — a 0.1 psi bracket.

- Inside the safe range (up to 44.7 psi) the valve carries 0–751 GPM but moves
  leakage by only **0.087 GPM (0.10 %)** — i.e. it changes nothing the objective
  measures.
- 0.2 psi beyond it: four highest-elevation nodes reach **−97 psi**, **15.9 GPM**
  of served demand is lost, **DSR 0.983 → 0.970**.
- Phase 5 at ×1.5 nominal: **min −99.3792 psi across 708 node-timesteps**; own
  flow span **4794.186 GPM** — five times total system base demand, the signature
  of the reopening.
- Phase 5 at ×1.25 (Gate 12): min **−97.086 psi**.

**Source.** Gate 4 §8.3 (confound X1), Gate 12 §16.6,
`results/phase6/p6_s3b_v179_refine.json`.

**Implication.** Empty benefit, catastrophic downside. Excluded from the action
space; fixed at 40 psi; hard-clamped ≤ **44.7 psi** if ever actuated. The brief's
instruction *"DO NOT expose unconstrained continuous action over VALVE-179"* is
satisfied in its strongest form: no action at all.

**Note on precision gained.** Phase 5 left the threshold bracketed only between
×1.00 and ×1.25 of nominal and recorded that measurement as *owed*. Phase 6 paid
that debt: the bracket is now **0.1 psi**.

---

### F-13 · VALVE-180 is inert only because a `[CONTROLS]` line holds it shut
`VERIFIED_FACT` · **High** · VALIDATED

**Finding.** With the control in place: **zero flow at every setting up to
120 psi**; 0 of 13 tested settings regulate; 0 junctions influenced; EPS max mean
ΔP = 0.0 psi.

With the `[CONTROLS]` closure **released** at 40 psi (a labelled diagnostic run,
never adopted): the valve carries **273 GPM** and the sub-20 psi count **halves,
386 → 193**.

**Source.** Gate 4/5, and the three explicitly-labelled diagnostic runs in
`src/validation/p6_s3_prv_finechar.py` (`release_valve180_control=True`).

**Implication.** Its closure is a **benchmark scenario decision, not an authority
limit**. Releasing it is the largest single service gain available in this
network — and taking it would destroy comparability with every baseline and with
the published benchmark. **The closure is retained. The finding is recorded, not
exploited.** This is the cleanest example in the project of measuring something
and deliberately declining to use it.

---

### F-14 · A conjunctive responsiveness criterion would have rejected the network's most influential valve
`VERIFIED_FACT` · **High** · VALIDATED — a methodological finding

**Finding.** VALVE-175 holds **38.495 %** of system demand and its downstream
pressure spans **115.00 psi** across the setting grid, while its own flow spans
**0.00092 GPM**.

**Why.** Under demand-driven analysis the withdrawal at each junction is fixed by
the pattern, so a PRV regulating a dead-end zone must pass exactly the same flow
regardless of its setting. Only the pressure moves.

**Implication.** The declared criterion — responsive if *either* network pressure
moves > 0.5 psi at some junction **or** own flow moves > 1 GPM — is disjunctive
for this reason. Under an AND rule the single most influential PRV in the network
would have been declared unresponsive. Both sub-criteria are reported separately
so a reader can apply either.

---

### F-15 · PRV leverage is very unevenly distributed
`VERIFIED_FACT` · **High** · VALIDATED

| PRV | Class | Flow share | EPS max mean ΔP |
|---|---|---|---|
| VALVE-175 | active, high-leverage | **38.495 %** | 27.500 psi |
| VALVE-176 | active, high-leverage | **28.519 %** | 14.881 psi |
| VALVE-178 | active, high-leverage | 3.995 % | 18.500 psi |
| VALVE-177 | active, high-leverage | 2.002 % | 22.500 psi |
| VALVE-173 | **low-leverage** | **0.163 %** | 34.755 psi |
| VALVE-174 | closed, responsive if reopened | 0 % | 24.435 psi |
| VALVE-179 | closed, responsive if reopened | 0 % | 113.554 psi |
| VALVE-180 | inert as distributed | 0 % | 0.000 psi |

**Implication.** Two valves carry 67 % of demand. VALVE-173 is retained in the
action space despite carrying 0.163 % of demand, because it *regulates* and moves
the pressure field by 34.755 psi — leverage over pressure, not over flow, is what
matters for a leakage objective. `INFERENCE`, and worth stating in the thesis.

---

### F-16 · Pump speed is genuinely applied and physically exact
`VERIFIED_FACT` · **High** · VALIDATED

**Finding.** Curve fits: PUMP-170 h₀ = 445.0 ft, r = 1.9469e-05, n = 2.28247;
PUMP-172 h₀ = 740.0 ft, r = 8.3818e-05, n = 1.93845. Shut-off head scales as
**speed² exactly** at all 9 swept speeds for both pumps. Max |residual| of any
running operating point against the speed-scaled curve: **8.62e-05 ft**. Flow
monotone increasing in speed. No swept speed exceeded the curve's q_max.

**Source.** Gate 3, `results/phase5/g3_pump_speed.json`.

**Implication.** The speed action is real, smooth, monotone and correct. The
problem is not the actuator — it is the *persistence* of the command (F-18).

---

### F-17 · Pump speed bounds are hydraulically determined and they move during an EPS
`VERIFIED_FACT` · **High** · VALIDATED

**Finding.** A pump shuts when its scaled shut-off head falls below the static
head it must lift.

| Pump | Static head across the shut pump | Shut-off at speed 1 | Implied minimum feasible speed | Highest speed observed shut | Lowest observed running |
|---|---|---|---|---|---|
| PUMP-170 | 295.7605 ft | 445.0 ft | **0.8152** | 0.80 | 0.85 |
| PUMP-172 | 433.6655 ft | 740.0 ft | **0.7655** | 0.70 | 0.80 |

**The static head depends on tank level, so this bound moves during an EPS and is
not a fixed constant.**

**Implication.** A speed action spanning 0.5–1.1 spends a third of its range on
hydraulically void commands. Lower bound must sit at or above the measured
shut-off. Because the bound moves, a *fixed* lower bound is a design choice that
must be stated, not a derived constant.

---

### F-18 · Pump speed commands do not persist — and neither EPANET mechanism fixes it alone
`VERIFIED_FACT` · **High** · VALIDATED (Phase 5 G12 CONDITIONAL → Phase 6 RESOLVED)

**Finding.** `THEN PUMP <p> STATUS IS OPEN` in the native rules **restores relative
speed to 1.0**, silently discarding a commanded speed. Mechanism confirmed by
controlled experiment for **both** pumps.

- `SETTING IS <speed>` writes the speed but does **not** reopen a shut pump.
- `STATUS IS OPEN` reopens the pump but overwrites its speed with **1.0**.

**Measured hold rate:** **1.72 %** if commanded once; **98.62 %** if re-issued
every control step. Residual override: **1.38 %** of open time.

**First fingerprint, found earlier and only explained later.** At commanded speed
0.85, PUMP-170's max flow over the EPS is **764.5399 GPM**, against **765.8873**
at commanded speed 1.00. A pump genuinely at 0.85 of rated speed cannot reach
99.8 % of its full-speed peak flow. That anomaly in Gate 3 §7.3 is what Gate 12
went on to explain.

**Source.** Gate 12 §16.4–16.5, `results/phase5/g12_realizability.json`;
`results/phase6/p6_s4_pump_strategy.json`.

**Implication.** Drove the whole pump-strategy decision: re-issue every control
step, agent commands **speed only**, `info` reports commanded and realised speed
separately.

**Unresolved.** Whether the 1.38 % residual matters for PPO's credit assignment —
`HYPOTHESIS TO TEST`, deferred past Phase 6.

---

## Group D — Leakage and demand

### F-19 · The emitter law must be signed, or the instrument disagrees with the engine
`VERIFIED_FACT` · **High** · VALIDATED

**Finding.** An EPANET emitter is a virtual pipe to a virtual reservoir and
**flows backwards at negative pressure**. Verified at JUNCTION-126 at
p = −5.731 psi: **engine −0.6416 GPM, signed law −0.6416 GPM, pressure-clipped law
0.0000 GPM.**

```
q_leak = sign(p) · C_j · |p|^0.5      (p in psi, q in GPM)
```

α = 0.5 is taken from the file's own `[OPTIONS] EMITTER EXPONENT 0.5`, not
invented.

**Implication.** A validation instrument that clipped at zero would silently
disagree with the engine by the full backflow whenever any junction went
negative — which several perturbation cases do. **Confound X3 quantified the
connector-node contribution to leakage: 0.508205 of 84.72988 GPM = 0.5998 % of
leak flow, 0.3555 % of the total coefficient 8.765093.** Real but negligible;
excluded from the RL instrument as a precaution.

---

### F-20 · The leak instrument's exact sizing
`VERIFIED_FACT` · **High** · VALIDATED — but see the status warning

| Quantity | Value |
|---|---|
| Target leakage | 10 % of baseline inflow = **84.74359 GPM** |
| Σⱼ wⱼ pⱼ^α | 1 187 270.5038 |
| Global scale k | **7.13768134008582e-05** |
| Junctions with an emitter | 126 |
| Coefficient min / max | 0.00199855 / 0.44900599 |
| Total coefficient | **8.76509297** |
| Leakage realised at nominal | **84.7266 GPM = 9.1795 % of inflow** |

`Cⱼ` is proportional to **half the incident pipe length** at junction j —
deterministic, no random seed, no per-node tuning. The global scale is fixed in
**closed form**: `k = target / Σⱼ (wⱼ · pⱼ^α)`. One evaluation, not a search.

**Status warning, quoted from the report itself:** *"This leakage coefficient set
is a validation instrument. It must not enter any thesis result."*

The Phase 6 brief reinforces it: «Leak coefficientهای Phase 5 را بدون
justification به‌عنوان field-calibrated leakage model معرفی نکن.»

---

### F-21 · Mean pressure is NOT a sufficient statistic for leakage
`VERIFIED_FACT` · **High** · VALIDATED — a genuinely surprising result

**Finding.** Mean-pressure monotonicity **FAILS** on one pair in the sweep: family
A ×0.75 → ×1.25 **raises** mean pressure from 100.3987 to 100.7715 psi while
leakage **falls**.

The **nodal pressure-dominance partial order** test — case X dominates case Y only
if *every* junction is at least as high in X as in Y — passes with **0 violations
at all six tolerances**.

**Source.** Gate 6, Gate 7.

**Implication.** Two reasons mean pressure misleads here:
1. The failing pair is a redistribution, not a uniform lift.
2. **Confound X2:** under PDA, curtailment reduces withdrawal → reduces friction
   loss → *raises* pressure at nodes downstream of curtailed ones. Scaling all PRVs
   down to ×0.25 leaves **84 junctions higher and 33 lower** relative to ×0.75.

**Therefore, under PDA a PRV setting reduction is not a monotone pressure
reduction across the network.** A reward function that treats mean pressure as a
proxy for leakage will be wrong in a way that is invisible in aggregate. Use nodal
statistics.

---

### F-22 · PDA bites at the nominal operating point, not only under perturbation
`VERIFIED_FACT` · **High** · VALIDATED

**Finding.** Echoed options confirm the engine received `DEMAND MODEL PDA`,
`MINIMUM PRESSURE 0.00`, `REQUIRED PRESSURE 20.00`, `PRESSURE EXPONENT 0.5`.

- Under **DDA**: DSR mean **0.99999998** — the network delivers requested demand
  exactly.
- Under **PDA** at nominal, no leakage: DSR mean **0.9833382**, DSR min
  **0.9818803**, max unserved **47.6861 GPM**, and demand is curtailed at **all
  193 timesteps**.

**Implication.** PDA is a *usable service-quality signal for a reward function*
precisely because it responds at the nominal operating point. Also: **the
distributed network does not fully satisfy its own demand at 20 psi required
pressure.**

**Unresolved.** The 20 psi / 0 psi thresholds are **the author's validation
choice**, recorded as such. Whether BWSN-1's problem statement declares a service
threshold is **UNKNOWN — not checked**. The thesis must justify its own threshold
separately.

---

### F-23 · Leakage saving and demand starvation are separable — and starvation dominates under deep perturbation
`VERIFIED_FACT` · **High** · VALIDATED — **the most important confound in the field**

**Finding.** The 96 h volume balance decomposes into served demand, leakage and
storage change with max absolute closure residual **5.31e-06 Mgal** and max
relative volume-closure error **1.556e-06**.

**In the deepest perturbation (all PRVs ×0.25): inflow falls by 1.1571 Mgal, of
which 0.0392 Mgal (3.39 %) is leakage saving and 1.1533 Mgal (99.67 %) is unserved
demand, at DSR 0.7596.**

**Source.** Gate 8, `results/phase5/g6_g7_g8_leak_pda.json`.

**Implication.** A study reporting "inflow fell, therefore leakage fell" would be
measuring demand starvation and calling it a leakage saving — and would be **96 %
wrong** in this case. This is why the brief insists *"lower leakage ≠ necessarily
better solution"* and why an explicit reward-hacking check on PDA delivery
shortfall is mandatory.

---

### F-24 · A DSR marginally above 1 is numerical, not over-delivery
`VERIFIED_FACT` · **High** · VALIDATED

Cases `actv1.25` and `actv1.50` report DSR mean 1.00016 and 1.00017. The absolute
discrepancy is **−0.06 GPM against 906.40 GPM requested = relative 6.6e-05** —
the 1e-5 convergence residual. Recorded in the artefact as
`dsr_above_one_is_numerical`.

**Implication.** A small honesty note, preserved because a future reader will
otherwise think the accounting is broken.

---

## Group E — Stability over the full horizon

### F-25 · The full configuration is stable for 96 h
`VERIFIED_FACT` · **High** · VALIDATED

**Finding.** 193 reported states, **0 EPANET errors, 0 warnings, 0 WNTR
warnings**. Both pumps switch **7 times = 3.6 %** of 192 intervals against a 25 %
chatter threshold; **all 14 switches inside their declared rule bands, 0
inconsistent**. **No valve changes status at all.** Both tanks inside limits, **0
states pinned**, 7 direction reversals each. Mass balance max relative residual
5.180e-07.

**Source.** Gate 10, same run as Gate 9 case C — so the two gates cannot disagree
about the same hydraulics.

**Implication.** No chatter, no pinning, no rule violation. The environment can be
reset and stepped thousands of times safely.

---

### F-26 · Tanks use about a tenth of their depth and never approach a limit
`VERIFIED_FACT` · **High** · VALIDATED

| Property | TANK-130 | TANK-131 |
|---|---|---|
| Elevation | 843.90 ft | 1137.10 ft |
| Diameter | 186 ft | 106 ft |
| Declared min / max | 0 / 32.1 ft | 0 / 41.9 ft |
| Initial level | 15.159 ft | 17.945 ft |
| Observed range (baseline) | 12.1212 – 15.9769 ft | 15.3996 – 18.3484 ft |
| Net change over 96 h | **−1.1995 ft** | **−0.9712 ft** |
| Hit min / exceeded max / negative | False / False / False | False / False / False |

Adding leakage and PDA widens the band slightly (TANK-130: 11.9904 – 16.0111) and
deepens the drift to −1.3770 ft — both in the expected direction.

**Implication.** Storage is **not a binding constraint**. An RL agent has room to
move without immediately emptying or overflowing a tank. The small net drawdown is
a property of the **shipped initial condition and demand pattern**, present in the
baseline too — not an artefact of the added instrumentation.

---

### F-27 · Baseline pump duty
`VERIFIED_FACT` · **High** · VALIDATED

| Pump | Switches | Fraction open | Max flow | Mean flow | Energy over 96 h | Mean power while running |
|---|---|---|---|---|---|---|
| PUMP-170 | 7 | 0.2268 | 765.8873 GPM | 172.6919 GPM | 1 565.06 kWh | 71.139 kW |
| PUMP-172 | 7 | 0.3505 | 2 413.3633 GPM | 843.0297 GPM | 9 044.60 kWh | 266.018 kW |

At the file's declared 75 % global efficiency. **PUMP-172 uses 5.8× the energy of
PUMP-170** — the energy reward term will be dominated by it.

---

### F-28 · Under native rules, speed changes redistribute run time and energy, not the pressure field
`VERIFIED_FACT` · **High** · VALIDATED

Two 96 h EPS at fixed commanded speed, rules intact:

| Quantity | 0.85 vs 1.00 |
|---|---|
| Mean ΔP | **0.0485 psi** |
| Min ΔP | 0.0214 psi |
| PUMP-170 energy | −5.06 % (1 565.06 → 1 418.30 kWh) |
| PUMP-172 energy | −1.78 % (9 044.60 → 9 013.78 kWh) |

**Why.** The pressure field is anchored by two tanks whose level the rules confine
to a narrow band.

**Implication.** An observation about **actuator authority**, explicitly *not* a
verdict and *not* a thesis conclusion. It matters for the N6 ablation: if VSP has
little pressure authority under native rules, the ablation must say so honestly
rather than presenting a null result as a failure of method. `INFERENCE`.

**Caveat.** Part of this measurement is contaminated by F-18 — the 0.85 command
was not fully realised. Re-measure under the Option C mechanism before drawing
conclusions.

---

## Group F — Architecture findings from Phase 6

### F-29 · Segmented EPS requires three-part state carry-forward
`VERIFIED_FACT` · **High** · VALIDATED

To step EPANET in 1800 s segments and reproduce a monolithic run, all three must
be carried:

1. tank levels (`init_level`)
2. pump status (`initial_status`)
3. **pattern time (`options.time.pattern_start`)**

**Implication.** Miss the third and demand silently restarts from hour 0 in every
segment — a bug that produces plausible-looking output. The stepping mechanism was
verified to reproduce the monolithic reference.

---

### F-30 · `wntr.metrics.expected_demand` has two independent defects for segmented use
`VERIFIED_FACT` · **High** · VALIDATED

1. It builds its series from the model's **own time index**:
   `tsteps = np.arange(start_time, end_time + timestep, timestep)`.
2. It **ignores `options.time.pattern_start` entirely.**

**Implication.** Do not use it to compute requested demand in a stepped
environment. Requested-demand accounting must be computed independently. This
matters because DSR is the reward-hacking guard (F-23) and a wrong denominator
would disable exactly the check that protects the thesis.

---

### F-31 · `ControlAction` has no `speed` attribute
`VERIFIED_FACT` · **High** · VALIDATED

Valid pump attributes are **`base_speed`, `setting`, `status`**. `speed` raises.

---

### F-32 · Echo-checking catches real discrepancies
`VERIFIED_FACT` · **High** · VALIDATED — a methodological finding

An in-memory attribute on a `WaterNetworkModel` is not evidence that EPANET
received the corresponding input token. **Write the `.inp` out, read it back,
compare.** This discipline (`echo_check`) is used in every Phase 5/6 module and
caught real mismatches.

---

### F-33 · Zone interaction between VALVE-178 and VALVE-179 was measured, not assumed
`VERIFIED_FACT` · **Medium** · VALIDATED

VALVE-178 and VALVE-179 share the upper zone. VALVE-178's own perturbation never
produced negative pressure anywhere in the §4.5 grid, and it shows ±0.1 GPM
leakage variation over 0.75–1.25× nominal.

**Source.** `results/phase6/p6_s3c_zone_interaction.json`,
`src/validation/p6_s3c_zone_interaction.py`.

**Implication.** VALVE-178 is admitted to the action space on measurement, despite
sharing a zone with the project's one dangerous valve. Confidence is Medium rather
than High because the interaction was probed on a grid, not exhaustively.

---

## Group G — Literature and novelty findings

### F-34 · Four novelty claims are dead on arrival
`VERIFIED_FACT` · **High** · VALIDATED

N1 (first continuous action space), N2 (first EPANET+PPO), N3 (first coordinated
PRV+pump), N4 (first multi-objective reward) all show **total** overlap with prior
work — Negm (2024), Hu et al. E-PPO, Pei et al. (JWRPM
doi 10.1061/JWRMD5.WRENG-6476), Xu et al. KA-PPO, Shao et al. *Energies*
12(15):2969, Brentan et al.

**Implication.** **Do not claim any of them.** The defensible contributions are
N6, N7, N8, N10, N11.

---

### F-35 · Net3 is unsuitable as the primary network
`VERIFIED_FACT` · **High** · VALIDATED

Net3's `[VALVES]` section is **empty**: 92 junctions, 117 pipes, 2 pumps, **0
valves**. Every PRV would be the author's own. The thesis would then be reporting
the performance of its own valve-siting decisions as if it were a controller
result. Hu, Gao & Zhong (2023) already occupy the exact configuration Net3 would
force.

---

### F-36 · Kentucky KY1–KY17 are unusable for speed control
`VERIFIED_FACT` · **High** · VALIDATED

`Duration 0`, `[CURVES]` empty, pumps declared by **POWER**. Affinity-law speed
control is impossible without inventing pump curves.

---

### F-37 · `[EMITTERS]` is empty in all 13 candidate `.inp` files
`VERIFIED_FACT` · **High** · VALIDATED

**Implication.** Leakage must be *added* on any network. This is a common
modelling cost, **not** a BWSN-1-specific concession — which is a defence against
the examiner question "why did you have to invent leakage?"

---

### F-38 · The OpenAlex novelty counts must never be quoted as proof of novelty
`VERIFIED_FACT` + `INFERENCE` · **High** · VALIDATED — a methodological finding

Search `"pressure reducing valve" AND ("reinforcement learning" OR "deep
reinforcement")`, all years → **2 results total**. `"variable speed pump" AND
"reinforcement learning"` → 2 results, both on pumped-storage hydropower, not WDN.
`("C-Town" OR "D-Town" OR "L-Town" OR "Anytown" OR "BWSN") AND "reinforcement
learning"` → 6 results, **none on BWSN-1, C-Town or L-Town for pressure control.**

**But:** OpenAlex indexes abstracts, not full texts. **Hu, Gao & Zhong (2023) —
the single most relevant paper — does not appear in the PRV query, because its
abstract says "valve" rather than "pressure reducing valve."**

**Implication.** The "2 results" figure may only be quoted as evidence that the
intersection is under-represented in indexed abstracts, **alongside the
counter-example.** Never as proof of novelty. A forward-citation sweep of Hu 2023
(15 citing works), Negm 2023 (4), Javed 2025 (17), Pei 2025 (17) and Hajgató 2020
(89) surfaced **no** paper performing joint continuous PRV + VSP DRL control on a
public benchmark under demand uncertainty.

---

### F-39 · Cyriac & Chacko (2026) publish a priority claim this thesis must not repeat
`VERIFIED_FACT` (abstract-level) · **Medium** · PARTIAL

Cyriac, Unni & Chacko, Sibi (2026), "Deep Reinforcement Learning for Pressure
Optimization in Water Distribution Networks with Multiple Pumping Stations",
*JWRPM*, published 2026-05-05, doi **10.1061/JWRMD5.WRENG-7303**, Heriot-Watt
University Malaysia. Closed access; 0 citations at time of search.

Verbatim from the abstract: a case study on a WDN in **Abu Dhabi**; "A custom
training environment was developed using the Gym framework"; the agent adjusts
**pumping station pressure setpoints**.

Three differences protect this thesis (`INFERENCE`): different actuator (station
setpoints, not PRV settings or pump speed); a **private** Abu Dhabi utility model,
not a public benchmark, so their result cannot be reproduced or contested; no
leakage objective, no PRVs and no demand-uncertainty treatment in the abstract
(`UNKNOWN` for the full text).

**Warning.** They publish the claim about "pressure control using RL with
continuous action spaces" in a top journal. This thesis must **cite them, not
repeat the claim**, and may note in one sentence that their framing overlooks Negm
(2024) and Hu et al. (2023). That note is novelty claim N15.

---

### F-40 · One 2026 item is recorded but explicitly not treated as evidence
`DIRECT_OBSERVATION` · **High** · VALIDATED

Korviakov, *World Journal of Civil Engineering and Architecture*,
doi 10.31586/wjcea.2026.6596 — single author, hierarchical RL + digital twin on a
"2,400-node benchmark network", in a venue that could not be verified as
peer-reviewed to a normal standard. **Recorded for completeness; not to be cited
without independent verification.**

---

## Group H — Environment and tooling findings

### F-41 · The Python environment lacks the entire RL stack
`VERIFIED_FACT` · **High** · VALIDATED

`.venv` (Python 3.13.15) has wntr 1.5.0, epyt 2.3.5.2, numpy 2.5.2, pandas 3.0.5,
scipy 1.18.1, matplotlib 3.11.1, networkx 3.6.1 and support packages.
**`gymnasium`, `stable-baselines3` and `torch` are absent.**

**Implication.** Phase 6 STEP 11 is blocked until they are installed with pinned
versions.

---

### F-42 · EPyT wraps a different EPANET than WNTR does
`VERIFIED_FACT` · **High** · VALIDATED

EPyT 2.3.5.2 wraps **EPANET 2.3.05**; WNTR 1.5.0 drives **EPANET 2.2** (DLL
reported as 20200). **They have never been cross-validated in this project.**

**Implication.** `OPEN_QUESTION`. Do not mix results from the two engines without
first establishing they agree.

---

### F-43 · Git Bash on Windows mangles `/dev/stdin`
`VERIFIED_FACT` · **High** · VALIDATED

`python /dev/stdin` fails with `can't open file 'D:\proc\self\fd\0'`. Heredoc
Python also needs `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` for Persian/CJK output
(default cp1252 raises `UnicodeEncodeError`), and Windows paths inside string
literals must be raw or escaped (`C:\Users\...` contains `\U`, a valid escape
prefix).

**Implication.** Write real `.py` files rather than fighting heredoc quoting. See
`_backup_tools/mk_session_aux.py` for the pattern.

---

### F-44 · Persistent agent memory is empty everywhere
`DIRECT_OBSERVATION` · **High** · VALIDATED

All three `~/.claude/projects/*/memory/` directories contain **zero files**, and
no `MEMORY.md` exists anywhere under `~/.claude`.

**Implication.** The project's durable knowledge lives entirely in `docs/*.md` and
`CLAUDE.md`. This is not a backup gap — it is the actual state. See
[MEMORY_BACKUP.md](MEMORY_BACKUP.md).

---

### F-45 · The `CLAUDE.md` §18 documentation structure was never populated
`DIRECT_OBSERVATION` · **High** · VALIDATED

`docs/research_questions.md`, `decisions.md`, `assumptions.md`, `literature.md`,
`experiments.md`, `open_questions.md` all exist at **0 bytes**.

**Implication.** The canonical statements of the research questions and the
decision log live only in the four `docs/phase*.md` reports and in the proposal
PDF. This backup's DECISIONS.md and FINDINGS.md are the first consolidated
versions. `OPEN_QUESTION` whether to populate the `CLAUDE.md` structure or
redirect it at these files.

---

### F-46 · Claude Code has no MCP servers configured
`DIRECT_OBSERVATION` · **High** · VALIDATED

Global `mcpServers` is `null`; every project entry is `{}` with empty
`enabledMcpjsonServers` / `disabledMcpjsonServers` / `mcpContextUris` /
`allowedTools`. The only `.mcp.json` files on the machine belong to two Claude
**Desktop** remote plugins.

**Implication.** **No project functionality depends on MCP.** A migrating agent
needs no MCP setup to continue this work.
