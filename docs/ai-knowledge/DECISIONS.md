# DECISIONS.md

Every meaningful decision taken in this project, oldest first, with the reason,
the alternatives considered, why they were rejected, the evidence, the
consequences and the current status.

Where a decision was later amended, **both** the original and the amendment are
preserved — per `CLAUDE.md` §18, *"If a decision changes, preserve the history and
explain why."*

Status values: `ACTIVE` · `AMENDED` · `RETRACTED` · `PENDING`.

---

## D-01 · Treat the proposal and seminar report as binding but not infallible
**Phase:** project setup · **Status:** `ACTIVE` · **Label:** `DECISION`

**Context.** `D:\Thesis\proposal\proposal.pdf` and `seminar\seminar.pdf` define
the advisor-approved scope.

**Decision.** They are mandatory constraints on scope, terminology and objectives,
**and** they are not assumed scientifically infallible. Where they contain an
error, prefer the smallest scientifically sound correction that preserves the
approved direction; surface any major correction to the researcher rather than
applying it silently.

**Reason.** Both failure modes are real: silent scope drift makes the thesis
undefendable to the advisor, and blindly reproducing a proposal error makes it
undefendable to an examiner.

**Alternatives rejected.** (a) Treat the proposal as ground truth — rejected
because two proposal errors have already been found (see D-19, D-20).
(b) Optimise for scientific correctness alone and ignore approved scope —
rejected because the advisor approved a specific direction.

**Consequence.** A conflict-priority hierarchy is written into `CLAUDE.md` §1:
scientific validity > approved scope > researcher-approved decisions >
implementation convenience. **When validity and the approved documents conflict,
the conflict is surfaced explicitly, never resolved silently.**

---

## D-02 · BWSN-1 is the primary network; Net3 is demoted to a comparability arm
**Phase:** 4 · **Status:** `ACTIVE` · **Label:** `DECISION`

**Context.** Earlier phases had assumed Net3 would be the primary network.

**Decision.** **BWSN-1** primary. Net3 secondary, for comparability with Hu, Gao &
Zhong (2023) only.

**Reason.** Net3's `[VALVES]` section is **empty** — 0 valves. Every PRV would be
the author's own, so the thesis would be reporting the performance of its own
valve-siting decisions as if it were a controller result. BWSN-1 ships **8 PRVs
whose locations were fixed by the BWSN organisers in 2008 for a
contamination-sensor objective** — therefore exogenous to this thesis's reward.

**Alternatives rejected.**
- Net3 as primary — the empty `[VALVES]` section; and Hu/Gao/Zhong already occupy
  exactly the configuration Net3 would force.
- Jowitt & Xu (1990) — **no official `.inp` exists**; would have to be
  reconstructed from the paper. Retained as an optional tertiary arm for
  comparability with Negm (2024) only.
- Kentucky KY1–KY17 / KYV — **excluded**: `Duration 0`, `[CURVES]` empty, pumps
  declared by `POWER`, so affinity-law speed control is impossible without
  inventing pump curves.
- D-Town — retained as a **fallback** only, if the pre-flight check failed. It
  did not; no gate FAILED.

**Evidence.** Phase 4 §2–§3 (weighted ranking + sensitivity analysis), §5 (a
20-dimension Jowitt & Xu vs Net3 head-to-head), and the counts parsed from all 13
candidate `.inp` files.

**Consequence.** Exogenous valve placement becomes a *defence*, not a limitation:
it is what makes novelty claim N11 (placement vs control) askable at all.

---

## D-03 · PRV placement design D3 — native 8 PRVs headline, GA subset as sensitivity only
**Phase:** 4 · **Status:** `ACTIVE` · **Label:** `DECISION`

**Decision.** The headline arm uses BWSN-1's native 8 PRVs exactly as distributed
(70, 80, 55, 29.762, 45, 37, 40, 16.45 psi). A GA-selected **subset** of those
same 8 valves is a sensitivity study. **The GA never invents new locations.**

**Reason.** Re-running placement optimisation against the thesis reward would be
**co-optimisation bias** — the controller would be evaluated on valve positions
chosen to flatter it.

**Alternatives rejected.** Free GA placement optimisation — invalidates the
headline claim.

**Consequence.** *"DO NOT re-run placement optimisation against the thesis reward
on the primary network."* This is one of the project's hard prohibitions.

---

## D-04 · PDA for training; DDA as a final re-run that is a *result*
**Phase:** 4 · **Status:** `ACTIVE` · **Label:** `DECISION`

**Decision.** Train under pressure-driven analysis. Re-run the **final** trained
policy under DDA and report the difference. That difference is novelty claim N9.

**Reason.** Under DDA, EPANET delivers requested demand regardless of pressure,
including at negative pressure. A leakage-reduction study under DDA cannot detect
the service damage it causes and therefore overstates achievable savings.

**Evidence.** Gate 7 measured it: DDA gives DSR mean 0.99999998; PDA at the same
nominal settings gives DSR mean 0.9833382 with demand curtailed at all 193
timesteps.

**Consequence.** PDA parameters set to required 20 psi, minimum 0 psi, pressure
exponent 0.5. **The threshold is an author choice, recorded as an assumption** —
whether BWSN documentation declares one is `UNKNOWN`.

---

## D-05 · Replace BWSN-1's native demand patterns with a 24-hour diurnal profile plus noise
**Phase:** 4 · **Status:** `ACTIVE` (with an amended rationale — see D-14) · **Label:** `DECISION`

**Decision.** Keep base demands exactly as distributed, never edited. Replace the
patterns with a 24-h diurnal multiplier profile plus multiplicative per-node
per-step stochastic noise.

**Reason.** Any credible uncertainty study needs its own documented demand
distribution, so that "out of distribution" has a defined meaning for the test
protocol. Documented as a modification, not hidden.

**Alternatives rejected.** Keeping the native patterns — they are not diurnal and
carry no declared distribution, so OOD would be undefinable. Inventing a
weekday/weekend split for BWSN-1 — rejected; adopted only on L-Town, where
BattLeDIM defines it.

---

## D-06 · Two uncertainty axes, reported separately and then jointly
**Phase:** 4 · **Status:** `ACTIVE` · **Label:** `DECISION`

**Decision.** Axis 1 = demand (stochastic multipliers in training; an OOD regime
in test) → claim N7. Axis 2 = model parameters (pipe roughness and diameter, to a
declared **10 %** bound) → claim N8. Report separately, then jointly (T4).

**Reason.** *"Merging them destroys the contribution."* The 10 % bound is not
invented — BattLeDIM states verbatim that model-vs-actual parameter differences are
"no greater than 10% of the nominal values".

**Evidence.** Hu, Gao & Zhong tested "five random test cases from **the same
distribution of the training**" — the gap N7 exploits.

---

## D-07 · Never observe the true leak flow or location; never any future information
**Phase:** 4 · **Status:** `ACTIVE` · **Label:** `DECISION`

**Decision.** The observation contains only quantities a real SCADA system could
measure. No true leak flow, no true leak location, no future demand.

**Reason.** Data leakage. *"It is the first thing an examiner will look for."*
Reinforced by the Phase 6 brief: «هیچ future information نباید وارد observation یا
action mapping شود.»

**Consequence.** The pressure sensor subset must be a **realistic subset, not all
126 junctions**, with a declared selection rule. That rule is still `PENDING` —
see O-01 in ROADMAP.md. BattLeDIM's 33-sensor sensitivity-maximising methodology
is the cited precedent.

---

## D-08 · Evaluation is never by scalarised reward
**Phase:** 4 · **Status:** `ACTIVE` · **Label:** `DECISION`

**Decision.** The weighted sum exists for **training only**. Service violations are
reported as a separate, non-negotiable axis, and methods are compared at **matched
violation budgets**. Report a trade-off surface across a *set* of weightings, not
one.

**Reason.** Negm reports scalar reward at a fixed 3:1 weight and states "a ratio of
3:1 favouring the leakage objective produces the best trade-off" — and Phase 4 §9
argues that this very setting is what produced his **264–304 violations against a
classical optimiser's 46–78**. A scalarised metric hid the cost.

**Alternatives rejected.** Inheriting Negm's 3:1 ratio — explicitly not adopted,
for the reason above.

**Consequence.** This is novelty claim N10, rated HIGH. Also mandates the explicit
reward-hacking check: inspect whether the policy cuts leakage by **starving nodes**
rather than by managing pressure; report delivered-vs-required demand.

---

## D-09 · `C` and `alpha` are identical between the agent and every baseline
**Phase:** 4 · **Status:** `ACTIVE` · **Label:** `DECISION`

Leakage model `q = C·p^α`, α = 0.5 (theoretical orifice exponent), with α = 1.0
reported as a **sensitivity** because field-reported background-leakage exponents
exceed 0.5. Both values stated; neither presented as the single truth.

*"DO NOT change C or alpha between the RL agent and the baselines."* Changing them
between arms invalidates every comparison. `C` itself is still `TO TUNE`.

---

## D-10 · Baselines B0–B3 plus an optional oracle, under a fairness rule
**Phase:** 4 · **Status:** `ACTIVE` · **Label:** `DECISION`

B0 no control (native settings + native pump rules — the floor). B1 fixed vector
optimised offline on the **mean** demand profile. B2 a classical online
metaheuristic re-optimising per timestep with full state knowledge — **at least
two** of Nelder-Mead / PSO / DE, and say which. B3 a time-of-day PRV modulation
rule of the kind utilities actually deploy. Optional oracle: B2's optimiser with
**perfect foresight**, to bound how much of the gap is attributable to uncertainty
itself.

**Fairness rule.** *"Baselines get the same actuators, the same bounds and the same
rate limits as the agent. A baseline denied an actuator the agent has is not a
baseline."*

**Also decided:** report B2's **wall-clock cost per decision**. Online
metaheuristics are frequently infeasible in real time; that is a legitimate
advantage of a trained policy and it should be **measured, not asserted**.

---

## D-11 · ≥ 5 seeds per arm per network; results reported as distributions
**Phase:** 4 · **Status:** `ACTIVE` · **Label:** `DECISION`

Non-negotiable. Test-set generation is seeded **separately** from training and
fixed once, so every arm and every baseline sees identical scenarios. Every seed,
config and library version logged per run. **Never best-of-n.**

**Reason.** Neither Hu, Gao & Zhong (2023) nor Negm (2024) reports seed variance,
and Jun, Yoo & Jung (2025, *JWRPM*, doi 10.1061/JWRMD5.WRENG-6868, "Toward
Transparent and Reproducible Machine Learning-Based Research in Urban Water
Networks") argues directly for this reporting standard.

---

## D-12 · Four novelty claims are abandoned; five are pursued
**Phase:** 4 · **Status:** `ACTIVE` · **Label:** `DECISION`

**Abandoned (total prior overlap):** N1 first continuous action space, N2 first
EPANET+PPO, N3 first coordinated PRV+pump, N4 first multi-objective reward.

**Pursued as HIGH:** N6 the PRV-only/VSP-only/joint ablation (Negm §7.3 names it
as future work, which *authorises* it), N7 OOD robustness of a joint controller,
N8 separating parameter uncertainty from demand uncertainty, N10
Pareto/constraint-matched evaluation, N11 quantifying placement vs control
("freshest claim in this list").

**Consequence.** The thesis's contribution is **methodological rigour, not
algorithmic firstness.** This reframing is the single most important outcome of
Phase 4.

---

## D-13 · The original `.inp` is never edited; work on a code-built working copy
**Phase:** 5 · **Status:** `ACTIVE` · **Label:** `DECISION`

`data/networks/BWSN_Network_1.inp` untouched. Working copy at
`data/networks/working/BWSN_Network_1_working.inp`, rebuilt by
`phase5_common.build_working_copy()`, with provenance recorded in
`results/phase5/working_copy_provenance.json`.

**The only patch:** `Quality Chemical TIME` → `Quality Chemical mg/L`.

---

## D-14 · The "8-hour cycle" claim is retracted
**Phase:** 5 · **Status:** `RETRACTED` (supersedes part of D-05's stated rationale) · **Label:** `DECISION`

Phase 4 wrote "4 patterns of 16/16/8/16 entries … an 8-hour cycle repeated over
96 h". Phase 5 measured **96/96/48/96 multipliers → 48/48/24/48 hour cycles** and
formally retracted the inference (discrepancy D1).

**Consequence.** D-05's *decision* stands; only its description of what is being
replaced was wrong. Any thesis text repeating "8-hour cycle" must be corrected.
This is recorded rather than quietly fixed, per `CLAUDE.md` §18.

---

## D-15 · Solver settings 1e-5 / 2000 / 180 s / 1800 s, set in code and asserted
**Phase:** 5 → 6 · **Status:** `ACTIVE` · **Label:** `DECISION`

**Decision.** On **every** model load: `accuracy = 1e-5`, `trials = 2000`,
`rule_timestep = 180 s`, `report_timestep = 1800 s`. Then **assert** them.

**Reason.** At the file's shipped 0.005 / 40 the engine violates the emitter law by
2.0135 GPM and continuity by 9.9692 GPM **while reporting 0 errors and 0
warnings**. At 1e-5 / 2000 the same violation is 0.0008 GPM. Gate 9's counter-test
case D converted this from an assertion into a measurement: max relative residual
1.767e-02 with 58/193 states over threshold.

**Alternatives rejected.** Documenting the requirement in prose — *"This must be
enforced in code, not documented in prose."* A `.inp` loaded anywhere else
silently reverts.

**Consequence.** `assert_solver()` at `src/validation/p6_s3_prv_finechar.py:117`
is the reference implementation. Reporting cadence is the only parameter a caller
may vary, and only with a stated reason.

**Note.** The Phase 5 module `g4_g5_prv.py` did **not** set accuracy/trials and
inherited the file's 0.005/40. Its snapshot harness is therefore **deliberately not
reused** in Phase 6. This is disclosed in the Phase 6 module docstring rather than
quietly worked around.

---

## D-16 · Service statistics use the 121 demand-bearing junctions
**Phase:** 5 → 6 · **Status:** `ACTIVE` · **Label:** `DECISION`

Exclude JUNCTION-105, -106, -109, -110, -128 from every pressure observation,
pressure reward term, pressure metric **and** leak emitter.

**Reason.** They are declared at elevation exactly 0.0 ft with zero base demand;
EPANET reports head-above-datum there, so JUNCTION-106 reads 501.6 psi. Including
them inflates mean pressure by 9.01 psi and the maximum by 219.5 psi, and
manufactures 7 spurious pressure jumps. Gate 10's pressure criterion **FAILED** on
its ceiling over all 126 and **PASSED** over the 121.

**Rule, not a hard-coded list.** Elevation exactly 0.0 ft AND zero total base
demand. Unambiguous — the next lowest elevation in the file is 192.0 ft. The rule
is implemented so it would find whatever a different file happens to contain:
`service_nodes()` at `src/validation/p6_s3_prv_finechar.py:79`.

**Also excluded from the leak instrument**, even though they carry only 0.5998 %
of mean leak flow — because it is reward the agent could learn to chase for a
reason that is an elevation placeholder.

---

## D-17 · The responsiveness criterion is disjunctive
**Phase:** 5 · **Status:** `ACTIVE` · **Label:** `DECISION`

A PRV is responsive if **either** network pressure moves > 0.5 psi at some
junction **or** its own flow moves > 1 GPM. Declared before any run.

**Reason.** Under DDA the withdrawal at each junction is fixed by the pattern, so a
PRV regulating a dead-end zone passes identical flow at every setting; only
pressure moves. VALVE-175 holds **38.495 %** of system demand with a downstream
span of 115.00 psi and a flow span of **0.00092 GPM**. Under a conjunctive rule the
network's most influential PRV would have been declared unresponsive.

**Consequence.** Both sub-criteria are reported separately so a reader can apply
either rule.

---

## D-18 · The Phase 5 leak coefficients are a validation instrument, not a leakage model
**Phase:** 5 · **Status:** `ACTIVE` · **Label:** `DECISION`

Half-pipe-length weights, one **closed-form** global scale
`k = 7.13768134008582e-05`, exponent 0.5 from the file's own `[OPTIONS]`, signed
law `q = sign(p)·C·|p|^0.5`. One evaluation, no search, no seed, no per-node
tuning.

**Quoted from the report:** *"This leakage coefficient set is a validation
instrument. It must not enter any thesis result."*

Reinforced by the Phase 6 brief: do not present it as a field-calibrated leakage
model without justification.

**Why signed.** An EPANET emitter is a virtual pipe to a virtual reservoir and
flows backwards at negative pressure. Verified: at JUNCTION-126, p = −5.731 psi →
engine −0.6416 GPM, signed law −0.6416 GPM, **clipped law 0.0000 GPM.** A clipped
instrument would silently disagree with the engine by the full backflow.

---

## D-19 · Correct the proposal's Hu MARL citation
**Phase:** 4 · **Status:** `PENDING` — a carried debt · **Label:** `DECISION`

The proposal mis-cites Hu et al.'s MARL paper. Correct to *Water Supply*
**23(7):2833**, doi **10.2166/ws.2023.163**.

**Not yet done.** Requires editing the proposal text.

---

## D-20 · Re-verify Negm's Table 5-4 directly from the PDF before citing
**Phase:** 4 · **Status:** `PENDING` — a carried debt · **Label:** `DECISION`

Negm's Table 5-4 is load-bearing for the argument in D-08 (the 264–304 vs 46–78
violation comparison). It must be re-read **from the PDF**, not from a secondary
note, before it appears in the thesis.

---

## D-21 · The RL action space is five PRVs
**Phase:** 6 STEP 3 · **Status:** `ACTIVE` · **Label:** `DECISION` · **Amends the ACTION block of D-03's locked configuration**

**Decision.** RL-controlled: **VALVE-173, VALVE-175, VALVE-176, VALVE-177,
VALVE-178**. Fixed at nominal: VALVE-174 (80 psi), VALVE-179 (40 psi), VALVE-180
(16.45 psi). **No PRV is removed from the model.**

**Reason — each exclusion is a measurement, and the two hydraulically-closed
valves are excluded for opposite reasons.**

| Valve | Measured basis for exclusion |
|---|---|
| VALVE-174 | Reopens at 95→96 psi; carries 4.7–5.0 GPM (≈0.5 % of demand); reopening **raises** leakage 84.730 → 84.968 GPM with **zero** change in served demand or deficit count. Only measured effect is adverse. |
| VALVE-179 | Cliff between **44.8 and 44.9 psi**. Inside the safe range it moves leakage by 0.087 GPM (0.10 %) — nothing. 0.2 psi past it: four nodes at **−97 psi**, 15.9 GPM served demand lost, DSR 0.983 → 0.970. Empty benefit, catastrophic downside. Hard clamp ≤ 44.7 psi if ever actuated. |
| VALVE-180 | Zero flow at every setting to 120 psi while its `[CONTROLS]` closure holds. Released at 40 psi it carries 273 GPM and halves the sub-20 psi count (386 → 193) — the largest single service gain available, and taking it would destroy comparability with every baseline. **Recorded, not exploited.** |

**Alternatives rejected.**
- Eight action dimensions — three would be uninformative or dangerous. Gate 5
  measured that 8 PRVs do not give 8 equally informative dimensions.
- Deleting the three valves from the model — **forbidden** by the brief
  («آنها را بدون بررسی حذف نکن») and unnecessary: not actuating a valve is not the
  same as removing it.
- Releasing VALVE-180's `[CONTROLS]` — the single most tempting option, and
  rejected: the closure is a benchmark scenario decision, and releasing it would
  make every baseline and the published benchmark incomparable.

**Consequence.** G5 CONDITIONAL → **RESOLVED**. Bounds for the five are still
`PENDING` (STEP 6) and must come from measurement — *"DO NOT choose arbitrary
actuator bounds."*

---

## D-22 · Pump strategy: Option C implemented on Option A's mechanism
**Phase:** 6 STEP 4 · **Status:** `ACTIVE` · **Label:** `DECISION`

**Decision.**
1. Native rules, controls and topology **untouched**. No rule removed, rewritten
   or reordered.
2. The EPS advances in **1800 s** segments, carrying forward tank levels, pump
   status **and pattern time**.
3. At each control step the pump action is written to `base_speed` and
   **re-issued**, because a command's lifetime in this architecture is exactly one
   control step.
4. The agent commands **speed only**. Status stays entirely with the native rules,
   since `STATUS IS OPEN` is the only mechanism that restarts a shut pump.
5. `info` reports **commanded and realised speed separately** at every step.

**Reason.** Measured hold rate **1.72 % without re-issue, 98.62 % with**.

**Alternatives rejected.**
- **Option B** — rewrite the native rules' `STATUS IS OPEN` into
  `SETTING IS <speed>`. Clean monolithically (hold rate 1.000, leak 84.684 GPM,
  tanks 13.339/18.195 ft) but it **halts EPANET at t = 79.5 h in the stepped
  architecture**, which would leave reward undefined mid-episode.
  **Disqualified on evidence, not on preference.**
- Letting the agent command pump **status** — rejected; status must stay with the
  native rules, which are the network's tank-protection logic.
- Removing the native rules so the command persists — forbidden («Silent rule
  removal ممنوع است») and it would break comparability with the native-controls
  baseline.

**Consequence.** G12 CONDITIONAL → **RESOLVED**. A **1.38 % residual override**
remains, where native tank protection wins over the controller. It is accepted as
an `ASSUMPTION`, stated quantitatively rather than assumed away, and made visible
in `info`. Whether it damages PPO's credit assignment is a `HYPOTHESIS TO TEST`
after Phase 6.

---

## D-23 · Pump speed lower bound at or above the measured shut-off
**Phase:** 5 §19 item 8 · **Status:** `ACTIVE` · **Label:** `DECISION`

Not 0.5–1.1. Lower bound at or above **0.8152** (PUMP-170) and **0.7655**
(PUMP-172).

**Reason.** Below those speeds the pump cannot overcome its static lift and the
command is hydraulically void — a 0.70 command yields zero open states. A
0.5–1.1 range spends a third of itself on actions with no possible effect.

**Caveat preserved.** The static head depends on tank level, so **this bound moves
during an EPS**. A fixed lower bound is therefore a design choice to be stated,
not a derived constant.

---

## D-24 · Record the baseline pressure-deficit floor before designing the reward
**Phase:** 5 §19 item 9 · **Status:** `ACTIVE` · **Label:** `DECISION`

At nominal settings the full pre-flight EPS already has **386 node-states below
20 psi** and a **minimum service pressure of 4.1645 psi** (JUNCTION-29).

Any service-pressure penalty must be stated **relative to this floor**, or a metric
will attribute pre-existing deficit to the controller. The floor is measured and
available in `results/phase5/g9_g10_full.json`.

---

## D-25 · Disclose instrument and criterion changes rather than quietly applying them
**Phase:** 5 · **Status:** `ACTIVE` · **Label:** `DECISION` — a process decision

Two disclosures were made rather than buried:

1. **Gate 12's criterion was changed after it first returned FAIL** (§16.3). The
   change and its reason are documented in the report.
2. **Gate 10's pressure criterion was evaluated on both node sets** — it failed on
   all 126 and passed on the 121 — and the instrument change was disclosed rather
   than the failing version being deleted.

**Reason.** A criterion changed after seeing a result is a legitimate move only if
it is visible. The report also carries an explicit §17.6 *"what this decision does
not claim"* and a §17.5 *"instrument and criterion changes, disclosed"*.

**Consequence.** This is the strongest available evidence of process integrity to
an examiner, and it is worth preserving as a working norm.

---

## D-26 · Confounds are numbered, quantified and disclosed
**Phase:** 5 · **Status:** `ACTIVE` · **Label:** `DECISION`

X1 the VALVE-179 negative-pressure hazard. X2 PDA feedback raising pressure at
nodes downstream of curtailed ones (84 junctions higher, 33 lower, ×0.25 vs
×0.75). X3 whether the connector nodes dominate the leakage instrument —
quantified as 0.5998 % of leak flow and 0.3555 % of total coefficient: **real but
negligible**, excluded anyway as a precaution.

**Reason.** Naming a confound and measuring its size is the difference between
disclosing a limitation and being caught by one.

---

## D-27 · Create a portable AI knowledge backup
**Date:** 2026-09-07 · **Status:** `ACTIVE` · **Label:** `DECISION`

**Context.** The researcher intends to migrate the project to a different AI
agent or environment.

**Decision.** Build `docs/ai-knowledge/` as a preservation package: real artefacts
copied verbatim (skills, plugins, configs, hooks, commands, agents, transcripts)
plus 20 authored knowledge documents that explain them. **Preservation, not
compression.**

**Constraints honoured.**
- Nothing outside `docs/ai-knowledge/` was created or modified. All copying was
  read-only with respect to sources.
- **No secrets copied.** A whole-backup scan for `sk-ant-`, `ghp_`,
  `xox[baprs]-`, `AKIA` and PEM private-key headers returned **zero matches**.
  Secrets are recorded as `SECRET PRESENT — NOT EXPORTED`.
- Four trees excluded by choice with reasons recorded: `results/phase5/_tmp`
  (459 MB of regenerable EPANET scratch), `.venv` (reconstructible from a pinned
  list), `papers/` (42 copyrighted PDFs, indexed by filename instead), the ARS
  plugin's `evals/` (15 MB of eval logs, not project knowledge).

**Consequence.** 661 directories, 2871 files, ~77 MB. See
[MISSING_OR_UNRECOVERABLE.md](MISSING_OR_UNRECOVERABLE.md) for everything that
could not be included.

---

## Pending decisions — required before Phase 6 can finish

These are decisions that have been *identified* but not *taken*. They are listed
here so the next agent does not mistake an open question for a settled choice.

| ID | Decision required | Blocking | Constraint |
|---|---|---|---|
| P-01 | Absolute vs delta PRV action formulation | STEP 5 | Choose ONE primary and state why |
| P-02 | Bounds for the five controlled PRVs | STEP 6 | **Must be derived from measurement.** "DO NOT choose arbitrary actuator bounds" |
| P-03 | PRV per-step rate limit | STEP 6 | Must exist, to keep policies implementable on real actuators |
| P-04 | The pressure sensor subset and its selection rule | STEP 7 | Realistic subset, not all 126. Rule must be declared. BattLeDIM's 33-sensor methodology is the precedent |
| P-05 | Observation normalisation constants | STEP 7 | Computed **once** from the baseline, then **frozen** across all arms, seeds and test sets |
| P-06 | Reward weights | STEP 8 | Derive from **measured** metric scales. Do not inherit Negm's 3:1 |
| P-07 | Leak coefficient `C` for the thesis proper, and the baseline leakage fraction | before experiments | Fraction fixed **in advance** and reported |
| P-08 | Energy price | before energy reporting | `[ENERGY]` ships Global Price 0; the chosen value is an assumption to report |
| P-09 | Total training timestep budget | before training | Must be **identical** across all arms and networks |
| P-10 | Demand noise distribution and magnitude | STEP 10 | Must be documented as a *distribution*, so OOD has a defined meaning |
| P-11 | Episode horizon and termination logic | STEP 10 | 96 h = 192 control steps is the working assumption |
| P-12 | Whether the native pump rules stay active in the PRV-only arm | before the ablation | Phase 4 flags this as *"a comparability trap if left implicit"* |
| P-13 | Pinned versions of `gymnasium`, `stable-baselines3`, `torch` | STEP 11 | Currently absent from `.venv`; record exact versions |
| P-14 | Whether to populate the `CLAUDE.md` §18 docs structure or redirect it at the phase reports | housekeeping | Six `docs/*.md` files are 0 bytes |
