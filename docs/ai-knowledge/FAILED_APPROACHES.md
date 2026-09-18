# FAILED_APPROACHES.md — what was tried, and why it failed

Mandated by PART H of the backup brief: *"Explain WHY each one failed. The next AI
must be able to avoid repeating our previous mistakes."*

Every entry is `FAILED_APPROACH`. Each records what was tried, what happened, the
mechanism of the failure, and the rule that replaced it. Nothing here is
speculative — each failure was observed on this machine.

**Read §1 first.** Both of this project's most expensive failures were *silent*: a
solver that reported success on wrong answers, and a control mechanism that
accepted a command and quietly discarded it. That pattern is the reason the
project's evidence standard is set as high as it is.

---

## 1. The two silent failures

### FA-01 — Trusting EPANET's zero-error report

**Tried.** Running the network at its shipped solver settings
(`ACCURACY 0.005`, `TRIALS 40`) and treating "0 errors, 0 warnings" as evidence of
a converged, physically consistent solution.

**What happened.** EPANET reported **0 errors and 0 warnings** on hydraulic states
that violated the **emitter law by 2.0135 GPM** and **continuity by 9.9692 GPM**,
with a maximum instantaneous imbalance of **25.6669 GPM** across **58 of 193**
reported states. At `ACCURACY 1e-5 / TRIALS 2000` the same emitter violation is
**0.0008 GPM**.

**Why it failed.** `ACCURACY` is EPANET's *convergence criterion*, not a
diagnostic. When the criterion is loose, the solver stops early and declares
success. It has no notion of "this answer is wrong" — only "the change between
iterations was below the threshold I was given."

**What replaced it.** `ACCURACY = 1e-5`, `TRIALS = 2000`, rule timestep 180 s,
report timestep 1800 s — set **in code** on every model load and then
**asserted**. Reference implementation: `assert_solver()` at
`src/validation/p6_s3_prv_finechar.py:117`. Never inherit WNTR defaults.

**Related trap.** `TRIALS` must rise **with** `ACCURACY`. At `1e-5` with only
**200** trials the leak-free run halts at **19:00 h** with "System unbalanced."
Tightening accuracy alone converts a wrong answer into a crash.

**Rule.** Silence is not validation. Verify continuity and the emitter law
independently of what the solver says about itself.

### FA-02 — Assuming a commanded pump speed persists

**Tried.** Issuing a relative-speed command once and assuming it held for the rest
of the simulation.

**What happened.** The measured **hold rate was 1.72 %**. The fingerprint that
exposed it: a commanded 0.85 produced a mean flow of **764.5399 GPM** where the
true 0.85 behaviour is **765.8873 GPM**.

**Why it failed.** `THEN PUMP <p> STATUS IS OPEN` in the network's native
tank-level rules **restores relative speed to 1.0**, silently discarding the
commanded speed. And in the segmented architecture each segment is a fresh model
load, so `base_speed` reverts to the file's declared 1.0 whenever it is not
re-issued. A speed command's lifetime in this architecture is **exactly one
control step**.

**What replaced it.** Re-issue the speed at every control step — hold rate
**98.62 %**. The residual **1.38 %** (five events, listed in EXPERIMENTS.md
E-P6-04d) is native tank protection winning over the controller, and is reported in
`info` as commanded vs realised speed rather than hidden.

**Rule.** For every actuator, measure realisation separately from issuance. Never
let `commanded` stand in for `realised`.

---

## 2. Approaches implemented, measured, and rejected on evidence

### FA-03 — Option B: rewriting the native rules' `STATUS IS OPEN` into `SETTING IS <speed>`

**Tried.** Patching the four native rules in the working copy so that the action
carrying the pump command also carries the speed, thereby avoiding the reset of
FA-02.

**What happened.** Monolithically it looked like a clean success — realisation rate
**1.000** on both pumps, leakage **84.684 GPM**, tanks ending at **13.339** and
**18.195 ft**, no warnings. In the **stepped** architecture it **does not
complete**. By **k = 156 (t = 78.0 h)** TANK-131 is **empty at 0.000 ft**,
TANK-130 is at 3.406 ft, and **both pumps are `Closed` with no mechanism to
restart**. Inside segment 159 (**t = 79.5 h**):

```
WARNING: System unbalanced at 0:18:00 hrs. EXECUTION HALTED.
```

**Why it failed.** The decisive isolated measurement: `SETTING IS <speed>` writes
the speed but **does not reopen a shut pump** (0/121 open states, 0.00 GPM, tank
drains 10.000 → 8.433 ft), whereas `STATUS IS OPEN` reopens the pump but
**overwrites the speed with 1.0** (120/121 open states, 773.96 GPM, tank refills
10.000 → 12.653 ft). **Neither mechanism does both jobs.** The action that carries
the speed command is the same action the tank-refill logic depends on, so rewriting
it destroys the tank protection. The monolithic run completes only because it never
enters a state requiring a closed pump to be reopened.

**Why the failure is disqualifying, not merely inconvenient.** An environment that
can drive the simulator into an unbalanced halt part-way through an episode is not
defensible: the episode cannot be completed, the reward is **undefined** from that
point onward, and the failure is **trajectory-dependent** rather than a function of
the action bounds — so **no action-space clamp can prevent it**.

**What replaced it.** Option C on Option A's mechanism: native rules untouched,
1800 s segments with three-part carry-forward, speed re-issued every control step,
agent commands speed only.

**Do not retry this.** It was implemented, applied in memory, echoed verbatim
before and after, measured on a validated harness, and rejected. Retrying it costs
the same days again.

### FA-04 — `ControlAction(pump, 'speed', ...)`

**Tried.** Constructing a WNTR control action on the attribute `speed`.

**What happened.** Raises. `speed` is not a valid pump attribute.

**Why it failed.** WNTR's pump object exposes `base_speed`, `setting` and `status`.
`speed` is the *concept*, not the attribute name.

**What replaced it.** Write `base_speed`.

### FA-05 — Assuming an in-memory attribute reached the solver

**Tried.** Setting an attribute on the `WaterNetworkModel` and assuming EPANET
received it.

**What happened.** Real discrepancies between what was set in memory and what
appeared in the generated `.inp`.

**Why it failed.** WNTR is a modelling layer over a file-driven engine. Several
attributes are only honoured if they survive serialisation into the `.inp` tokens
EPANET actually parses.

**What replaced it.** The **echo check**: write the `.inp` out,
read it back, and compare the tokens against the intent. Every Phase 6 case does
this.

### FA-06 — `wntr.metrics.expected_demand(wn)` in a segmented run

**Tried.** Calling `expected_demand` per segment to compute requested demand.

**What happened.** DSR of **4.179** and served demand of **1605.10 GPM**; after
stitching, requested demand **1631 GPM** against the true **906.40 GPM**.

**Why it failed. Two independent defects.** (1) It builds its series from the
model's **own** time index — `tsteps = np.arange(start_time, end_time+timestep,
timestep)` — so a 30-minute segment yields a one-step series. (2) It **ignores
`options.time.pattern_start` entirely**, so every segment returns hour-0
multipliers.

**What replaced it.** Compute requested demand **once** over the full horizon on
the `pattern_start = 0` model. Requested demand is a property of the patterns and
the absolute clock, **not** of how the solve was segmented.

### FA-07 — Segmenting the EPS without carrying pump status

**Tried.** Stepping EPANET in 1800 s segments carrying only tank levels.

**What happened.** Both pumps reset to the file's declared `Open` every step:
**193/193** open states against the reference's **42/193**; TANK-130 drained to
**7.659 ft** against the reference 13.782 ft.

**Why it failed.** Each segment is a fresh model load, so `initial_status` reverts
to whatever the file declares.

**What replaced it.** Carry `initial_status`, updated from each segment's final
status.

### FA-08 — Segmenting the EPS without advancing pattern time

**Tried.** Carrying tank levels and pump status, but leaving
`options.time.pattern_start` at its default.

**What happened.** Every segment silently replayed the **hour-0** demand
multipliers. Verified at JUNCTION-0: without the fix every segment returns
**1.192 GPM**; with `pattern_start = k·1800` the true monolithic sequence
**1.192, 1.039, 0.894, 0.864, 0.826, 0.795, 0.917, 0.490** is reproduced exactly.

**Why it failed.** The demand pattern is indexed from the model's own clock, which
resets on every load.

**What replaced it.** Set `options.time.pattern_start = t_elapsed`. Together with
FA-07 and tank levels this is the **three-part carry-forward**; missing any one of
the three silently corrupts the run while producing plausible numbers.

### FA-09 — Mixing the 180 s and 1800 s cadences in one statistic

**Tried.** Computing time-averaged statistics over whatever rows the segments
produced.

**Why it failed.** Segments report at the 180 s native rule cadence as well as at
the 1800 s control cadence. Mixing them **silently changes the time-weighting**, so
cases are no longer averaged over the same instants as the monolithic reference.
This one also cuts the other way: at 1800 s resolution Option A's speed realisation
reads a clean **1.000**, and only the 180 s scan reveals that it is **0.9862**.

**What replaced it.** Statistics on the **1800 s / 193-instant** frame; the 180 s
interior rows used **only** to detect rule firings.

---

## 3. Measurement instruments that were wrong

### FA-10 — Phase 5's `g4_g5_prv.py` harness

**Tried.** Reusing the Phase 5 G4/G5 PRV snapshot harness for Phase 6.

**Why it failed.** It **did not set** accuracy or trials and therefore inherited the
file's `0.005 / 40` — the settings FA-01 disqualified.

**Disposition, stated honestly.** This is a correction to the *instrument*, not to
a *result*: the G4/G5 **classification** conclusions survive, because they turn on
whether a valve responds at all. But **no numeric value from that harness is
carried into Phase 6**, and the harness itself is deliberately not reused. Recorded
in the module docstring of `src/validation/p6_s3_prv_finechar.py`.

### FA-11 — The conjunctive PRV responsiveness criterion

**Tried.** Classifying a PRV as responsive only if flow **and** pressure **and**
leakage all move together.

**Why it failed.** It would have **rejected VALVE-175**, which carries **38.495 %
of system demand** across a **115.00 psi** setpoint span while its own flow span is
only **0.00092 GPM**. A regulating PRV holding a downstream setpoint can have near-
constant throughput and enormous authority at the same time.

**What replaced it.** Disjunctive classification plus explicit per-valve
characterisation, and the full 8-valve leverage table.

### FA-12 — Mean pressure as a sufficient statistic

**Tried.** Testing monotonicity of leakage against pressure using mean network
pressure.

**Why it failed.** Measured counter-example: PRV-scaling family A from ×0.75 to
×1.25 **raises** mean pressure **100.3987 → 100.7715 psi** while leakage **falls**.
The mean-pressure test fails on that pair; the **pressure-dominance partial
order** — case X dominates Y only if **every** junction is at least as high in X,
within tolerance — passes with **0 violations at all six tolerances**.

**What replaced it.** Pressure dominance, not the mean.

**Related confound (X2), and why the intuition is wrong.** Under PDA, curtailment
reduces withdrawal → reduces friction loss → **raises** pressure downstream of
curtailed nodes. Scaling all PRVs to ×0.25 leaves **84 junctions higher and 33
lower** relative to ×0.75. "Lower setpoints ⇒ lower pressure everywhere" is false.

### FA-13 — Reading "pressure" at all 126 junctions

**Tried.** Computing pressure statistics over every junction in the model.

**What happened.**

| Statistic | All 126 junctions | 121 service junctions |
|---|---|---|
| Mean pressure | **103.7944 psi** | **94.7867 psi** |
| Max pressure | **507.7488** (JUNCTION-106) | **288.2206** (JUNCTION-34) |
| Max inter-report change | **25.8712 psi** | **6.7257 psi** |
| States with change > 25 psi | **7** | **0** |

**Why it failed.** JUNCTION-105, -106, -109, -110 and -128 have declared elevation
**exactly 0.0 ft** and **zero** base demand. They are pump/reservoir connector
artefacts, and EPANET reports **head above datum** at them. JUNCTION-106 reads
**501.6 psi**. Including them inflates mean pressure by **6.7 psi** and manufactures
**7 spurious** pressure jumps.

**What replaced it.** The **121 demand-bearing junctions** for every observation,
every reward term and every metric. The exclusion rule is mechanical and auditable —
elevation exactly 0.0 ft **and** zero total base demand — not a hard-coded list. The
next lowest elevation in the file is **192.0 ft**, so the rule is unambiguous.
Reference implementation: `service_nodes()` at
`src/validation/p6_s3_prv_finechar.py:79`.

### FA-14 — The pressure-clipped emitter law

**Tried.** Assuming an EPANET emitter delivers zero flow at negative pressure,
i.e. `q = C·max(p,0)^α`.

**What happened.** At JUNCTION-126 with p = **−5.731 psi**: engine
**−0.6416 GPM**, signed law `q = sign(p)·C·|p|^0.5` **−0.6416 GPM**, clipped law
**0.0000 GPM**.

**Why it failed.** An EPANET emitter is a virtual pipe to a virtual reservoir. At
negative pressure it **flows backwards** — the leakage instrument reports water
*entering* the network.

**Consequence, which matters for the safety design.** Any state with negative
service pressure is not merely physically meaningless; it is **numerically
corrupting to the leakage accounting**. It must be excluded **by construction**, not
merely penalised in the reward. This is the central argument for the STEP 9 safety
layer.

---

## 4. Interpretations that were retracted

### FA-15 — The "8-hour demand cycle"

**Tried.** Inferring from the demand patterns that BWSN-1 has an 8-hour demand
cycle, and recording it as a FACT.

**Why it failed.** The inference did not survive Phase 5's direct examination of the
pattern assignments. **Retracted** (Phase 5 D1); the decision record keeps it as
`RETRACTED` rather than deleting it, and the pattern assignment table is sparse in a
way the inference did not account for.

**Rule.** Do not upgrade a plausible reading of input data into a FACT without
measuring what the solver does with it.

### FA-16 — Novelty claims N1–N4

**Tried.** Four candidate novelty claims for the thesis contribution.

**Why they failed.** Each has **strong overlap with prior work** — full
claim-by-claim table with closest prior work, year, exact overlap, remaining
difference, verdict, confidence and search gap in `docs/phase4_decision_report.md`
§9. The surviving HIGH-confidence claims are **N6, N7, N8, N10, N11**.

**Methodological warning attached to the audit.** The OpenAlex sweep does **not**
prove absence: Hu et al. 2023 — a paper directly in scope, held locally — does
**not appear** in the OpenAlex counts used for the sweep. Treat database counts as
a lower bound on the field, never as coverage.

### FA-17 — Calling the leak coefficients a calibrated leakage model

**Tried.** Nothing was published, but the temptation is recorded because the brief
forbids it explicitly (§18).

**Why it would fail.** The instrument is: half of each incident pipe's length as the
junction weight, **one** global closed-form scale
`k = target / Σ_j (w_j·p_j^α)` evaluated once with no iteration and no search,
α = 0.5 taken from the file's own `[OPTIONS] Emitter Exponent`, target = 10 % of the
leak-free mean inflow. It is **not calibrated against any measurement** of the
BWSN-1 system, and no such measurement is known to the author to exist.

**Rule.** It is a **validation instrument**. `C` and `α` must be **identical**
between the RL agent and every baseline; changing them between arms invalidates the
comparison. No result may be presented as a calibrated leakage estimate.

---

## 5. Networks and scenarios rejected

### FA-18 — Net3 as the primary network

**Why it failed.** Its `[VALVES]` section is **empty**. A thesis about PRV setpoint
control cannot use a network with no PRVs.

**Disposition.** Net3 is **retained** only for comparability with Hu et al.'s MARL
paper, not as the primary network.

### FA-19 — Kentucky KY1–KY17

**Why they failed.** Three concrete defects: `Duration 0` (no extended-period
simulation), **empty `[CURVES]`** (no pump curves), and **POWER pumps** (constant-
power rather than curve-driven, so relative speed has no well-defined meaning).

**Disposition.** Excluded. BWSN-1 selected instead.

### FA-20 — Releasing VALVE-180's `[CONTROLS]` closure

**Tried.** As a **diagnostic only**, removing the single line
`LINK VALVE-180 Closed At Time 0.000000`.

**What happened.** At 40 psi the valve carries **273.02 GPM**, node-timesteps below
20 psi **halve (386 → 193)**, served demand rises to **906.46 GPM**, DSR reaches
**1.00016**, and mean leakage rises only **84.730 → 85.803 GPM**. **Roughly half of
BWSN-1's baseline pressure deficit is downstream of a valve the benchmark
deliberately commands shut.** This is the **largest single service gain available
anywhere in this study**.

**Why it must not be exploited.** Not a hydraulic failure — a
**scope-and-comparability** failure, and it is recorded here precisely because the
temptation runs the other way:

1. **It is a scenario definition, not a defect.** A modeller wrote a control
   statement to close this valve at t = 0. That *defines* the benchmark's operating
   scenario. Removing it changes the problem, not the solution.
2. **It would destroy comparability.** Every Phase 5 baseline and any published
   BWSN-1 result is computed with that control in force. An agent permitted to
   release it would show a large improvement attributable **entirely** to the
   scenario change.
3. **The brief forbids it.** §4: «اصل benchmark topology و actuator topology نباید
   تغییر کند». §30 lists silent removal of native rules as prohibited, and a control
   statement is native control logic.

**Disposition.** The closure is **retained**; VALVE-180 is excluded from the action
space; the finding is **recorded, not exploited**. `HYPOTHESIS`, for work outside
this thesis's approved scope: whether BWSN-1's baseline service deficit is an
intentional feature of the benchmark scenario or an artefact of its construction.
Settling that needs the BWSN-1 problem statement, which the author has not obtained.

### FA-21 — Deleting the three non-actuated PRVs from the model

**Why it would fail.** Brief §7: «آنها را بدون بررسی حذف نکن» — do not delete them
without examination. Deleting a valve changes the **topology**, which §4 forbids, and
would make results incomparable with the benchmark. VALVE-174 in particular is *not*
inert: it reopens between 95 and 96 psi and regulates cleanly to 110 psi.

**What was done instead.** All three are **left in the model** and simply **not
actuated**: VALVE-174 fixed at 80 psi, VALVE-179 fixed at 40 psi (hard-clamped
≤ 44.7 psi if ever actuated), VALVE-180's `[CONTROLS]` closure retained.

### FA-22 — Proposing D-Town instead

**Why it was not done.** No Phase 5 gate **FAILED** — the overall verdict was
CONDITIONAL PASS and both CONDITIONALs have since been discharged. Switching networks
would discard all validated work for no evidenced reason.

---

## 6. Actuator bounds that would have been wrong

### FA-23 — A pump speed action spanning 0.5–1.1

**Why it would fail.** Measured shut-off speed is **0.8152 for PUMP-170** and
**0.7655 for PUMP-172**. A 0.70 command yields **zero** open states. An action range
of 0.5–1.1 would spend roughly a third of its span on hydraulically **void**
commands — the agent would be exploring actions that cannot produce flow.

**Caveat that must survive into the environment.** The bound **moves** during an EPS
as tank level changes. It is a floor, not a constant.

**What replaced it.** Bound pump speed to the **measured feasible range**.

### FA-24 — Placing VALVE-179's bound at 44.8 psi

**Why it would fail.** 44.8 psi is already **outside the reference service
envelope**: n<20 rises **386 → 423** and DSR falls **0.983337 → 0.983178**. The
margin from 44.8 to the first failure at 44.9 is **0.1 psi** — finer than any
resolution at which a physical PRV could be commanded. 0.2 psi past the cliff, four
of the highest-elevation nodes reach **−97 psi** and **15.94 GPM** of served demand
is lost.

**What replaced it.** The bound is **44.7 psi**, the last **fully clean** setting.
Cost of the extra margin: **39 GPM** of valve throughput, worth ≈0 in leakage terms
— across the entire safe range 38.0 → 44.7 psi, while throughput goes 0 → 751 GPM,
leakage moves only **0.087 GPM (0.10 %)**.

### FA-25 — Actuating VALVE-179 at all

**Why it would fail.** Within its safe domain the valve changes **nothing** the
objective measures: leakage spread **0.087 GPM**, served demand **constant** at
891.41 GPM, DSR **constant** at 0.983337, n<20 **constant** at 386. Outside it,
catastrophic. **Empty benefit, severe downside.** The brief's instruction — "DO NOT
expose unconstrained continuous action over VALVE-179" — is satisfied in its
strongest form: **no action at all.**

### FA-26 — Actuating VALVE-174

**Why it would fail.** Throughput **4.7–5.0 GPM** against ≈944.7 GPM total demand
(**≈0.5 %**). Served demand unchanged to six decimals; n<20 constant at 386. The
**only** quantity that moves monotonically is **leakage, upward**: 84.730 → 84.968
GPM as the setting rises, because raising the setting raises mean network pressure
(94.787 → 95.742 psi). **Its entire measured effect is adverse.** Under any reward
that penalises leakage, the optimal policy for this valve is the one the benchmark
already implements: leave it shut.

### FA-27 — Assuming a per-valve bound is automatically valid under joint action

**Why it would be unsound.** A DRL agent emits all PRV settings at once. JUNCTION-121
and JUNCTION-122 — two of the four nodes that fail at VALVE-179 = 45 psi — are
exactly the upstream and downstream nodes of **VALVE-178**, so the two valves share
the failing zone.

**What was done.** Tested rather than assumed
(`results/phase6/p6_s3c_zone_interaction.json`): of **18** cases with VALVE-179 at
or below 44.7 psi, **all 18** produced **zero** negative service pressures, including
the 0.75× joint case; every case at 45 psi failed **identically** regardless of
VALVE-178.

**What is still open.** `HYPOTHESIS`: that separability holds over the **full** joint
action space, including combinations outside those two designs and including
pump-speed variation. **Not proved.** The STEP 9 safety layer must therefore detect
the failure **at runtime** rather than rely on the box constraint alone.

---

## 7. Reward and evaluation traps

### FA-28 — "Lower leakage is a better solution"

**`FALSE as stated`**, and the most dangerous available failure mode. Measured: at
all PRVs ×0.25, inflow falls **1.1571 Mgal**, of which only **0.0392 Mgal (3.39 %)**
is genuine leakage saving and **1.1533 Mgal (99.67 %)** is **unserved demand**, at
DSR **0.7596**.

**Why it fails.** An agent can cut leakage by **starving customers**. Any objective
that rewards leakage reduction without an explicit, correctly scaled service term
rewards exactly that. Brief §19: "lower leakage ≠ necessarily better solution."

**Rules that follow.** (a) The reward must contain an explicit service term.
(b) Evaluation is **never** by scalarised reward — the weighted sum exists for
training only. (c) Report leakage saving and unserved demand **separately**.

### FA-29 — Penalising service violation without the pre-existing floor

**Why it would fail.** At nominal settings the baseline already has **386
node-timesteps below the 20 psi PDA threshold** and a minimum service pressure of
**4.1645 psi** (JUNCTION-29, elevation 846.28 ft). A metric stated in absolute terms
would blame the controller for a deficit that exists before it acts.

**What must be done.** State every service penalty **relative to this floor**, and
report the floor alongside every service metric.

### FA-30 — Choosing reward weights by judgement

**Why it would fail.** Brief §20: «اما ضرایب را با حدس انتخاب نکن» — do not pick the
coefficients by guessing. The four terms (leakage, pressure violation, energy,
actuator movement) have **different physical units and wildly different numeric
scales**; weights chosen before the scales are known encode an unintended objective.

**Status.** Reward weights are **not chosen**. The scales must be **measured first**
(E-PL-08) and only then weighted.

### FA-31 — Observing the true leak flow or leak location

**Why it would fail.** A real SCADA system cannot measure either. Including them is
**data leakage**, and any result obtained with them is not transferable.

**Rule.** Never place true leak flow or true leak location in the observation. Brief
§21: «هیچ future information نباید وارد observation یا action mapping شود».

### FA-32 — Treating DSR > 1 as a physical result

**Why it would mislead.** DSR values marginally above 1 (e.g. **1.00016**) arise
because the reported-minus-modelled leakage decomposition leaves a small residual at
full service. The value means **"no unserved demand"**, not "more than requested."

### FA-33 — Reusing the baseline pump energy/pressure relationship as measured

**Why it is not yet usable.** The Phase 5 finding — PUMP-172 consumes **5.8×**
PUMP-170's energy at baseline, and speed changes **redistribute energy between the
pumps rather than changing network pressure** — was measured **before** the
non-persistence defect (FA-02) was understood, and is therefore **contaminated**.

**What must be done.** Re-derive it under the Option C mechanism (E-PL-08b) before
using it for reward design.

---

## 8. Tooling failures during this backup

These are not research failures, but they cost real time and will recur on the same
machine. All four are Windows / Git Bash issues.

### FA-34 — `UnicodeEncodeError: 'charmap' codec can't encode characters`

**When.** Printing transcript metadata whose first user text is Persian or CJK.

**Why.** The Windows console defaults to cp1252.

**Fix.** Run with `PYTHONUTF8=1 PYTHONIOENCODING=utf-8`, and write structured output
to a JSON file rather than to stdout.

### FA-35 — `SyntaxError: (unicode error) 'unicodeescape' codec can't decode bytes ... truncated \UXXXXXXXX escape`

**When.** A heredoc Python literal contained `C:\Users\ABN\.claude\paste-cache\`.

**Why.** `\U` begins a Unicode escape in a normal Python string literal.

**Fix.** Use raw strings for Windows paths, and prefer writing the logic to a real
`.py` file over a heredoc. Done here as
`docs/ai-knowledge/_backup_tools/mk_session_aux.py`.

### FA-36 — `can't open file 'D:\proc\self\fd\0'`

**When.** Attempting `python /dev/stdin` under Git Bash.

**Why.** Git Bash **path-mangles** `/dev/stdin` into a Windows path before the
interpreter sees it.

**Fix.** Write a real `.py` file and invoke it by path.

### FA-37 — A prompt-history filter that silently wrote 0 entries

**When.** Filtering `history.jsonl` for this project's entries.

**Why.** The comparison string had been mangled by shell/heredoc escaping, so no
record matched — and the script reported success with an empty result. Diagnosed by
counting distinct `project` values: `'D:\\Thesis'` **98**,
`'C:\\Users\\ABN\\Desktop'` **6**, `'C:\\Users\\ABN'` **2**.

**Fix.** Compare `TARGET_PROJECT = "d:\\thesis"` against
`(obj.get("project") or "").lower()` → **98** entries written.

**Rule, and it is the same rule as FA-01.** A filter that returns nothing is
indistinguishable from a filter that matched nothing. Always assert the expected
count.

---

## 9. The pattern

| Failure | What was silent about it |
|---|---|
| FA-01 solver settings | Reported 0 errors on states violating continuity by 10 GPM |
| FA-02 pump speed | Accepted the command, discarded it |
| FA-06 `expected_demand` | Returned a number, the wrong one |
| FA-07 pump status | Ran to completion with the wrong duty cycle |
| FA-08 pattern time | Ran to completion on hour-0 demand |
| FA-09 mixed cadence | Reported hold rate 1.000 where the truth is 0.9862 |
| FA-13 all-126 statistics | Produced a plausible mean pressure inflated by 6.7 psi |
| FA-37 history filter | Reported success on an empty result |

**Eight of the project's failures produced no error message.** That is why every
number in this project is required to name the measurement that produced it, and why
the standing instruction is: when you are about to write a number into the
environment, ask where it was measured. If the answer is "it seemed reasonable",
measure it.
