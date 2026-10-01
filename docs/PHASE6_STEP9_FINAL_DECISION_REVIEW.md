# PHASE 6 — STEP-9 SAFETY-ARCHITECTURE **FINAL DECISION REVIEW** (WU-18)

**Decision ID:** `STEP9_SAFETY_MECHANISM_FINAL_REVIEW`
**Status:** PROPOSED / PENDING RESEARCHER — **no D-P6-006 minted**
**Readiness verdict:** **DECISION-READY**
**Companion artefact:** [`results/phase6/p6_s9_final_decision_review.json`](../results/phase6/p6_s9_final_decision_review.json)
**Generator:** [`src/validation/p6_s9_final_decision_review.py`](../src/validation/p6_s9_final_decision_review.py)

> **⚑ SUPERSEDED-BY-FINALIZATION BANNER (2026-10-01).** This WU-18 review and its
> companion JSON were correctly `researcher_selection = null` and are **preserved
> UNCHANGED** as the pre-decision snapshot (the byte-reproducible JSON is NOT edited; the
> §18 blank form below is kept as history, per CLAUDE.md §14/§18). On the researcher's
> explicit "STAGE B — FINALIZE D-P6-006" directive, the STEP-9 safety architecture has
> since been **FINALIZED** → **D-P6-006** (architecture F1). The authoritative record is
> [`docs/PHASE6_DECISION_REGISTER.md`](PHASE6_DECISION_REGISTER.md) → D-P6-006; the filled
> form is reproduced in **§19** below. The header's "no D-P6-006 minted" / "PROPOSED"
> wording describes the state **at WU-18** and is left intact for traceability.

> This is the final scientific **review** immediately preceding production
> safety-wrapper implementation. It judges whether the STEP-9 safety-architecture
> decision is defensible and implementable, and packages the (≤3) final
> **provisional** designs — **WITHOUT** selecting a mechanism, threshold, horizon,
> or handling policy. It measures nothing new (no EPANET, no PPO, no RNG), and it
> is byte-reproducible from the frozen WU-14/15/16/17 + WU-11 evidence.
>
> **The researcher makes the STEP-9 selection.** This review does not, and must
> not, make it.

---

## §1 — Current state

STEP 9 (execution-safety / admissibility layer) is the last open design decision
before the environment is PPO-ready. Prior STEP-9 work units are complete and
frozen on disk:

| WU | Artefact | Role |
|----|----------|------|
| WU-14 | `p6_s9_safety_design_analysis.json` | design analysis (S1–S4 candidates) |
| WU-15 | `p6_s9_safety_mechanism_characterization.json` | empirical characterisation |
| WU-16 | `p6_s9_temporal_safety_characterization.json` | temporal (look-ahead) evidence |
| WU-17 | `p6_s9_decision_brief.json` | decision brief (FRAMES the 4 decisions) |
| WU-11 | `p6_d_p6_005_decision_brief.json` | frozen reward D-P6-005 |

Four decisions remain **open and unselected**: (A) safety metric/rule, (B)
threshold/tolerance, (C) look-ahead horizon, (D) action-handling policy. STEP-9
remains **PROPOSED / PENDING RESEARCHER**; the project is **not PPO-ready** until
the researcher selects and approves D-P6-006.

### Accuracy correction surfaced against WU-17 (not silent)

WU-17's `horizon_analysis.crossover_interval_untested` stated the delayed-collapse
onset is "NOT persisted as a per-index p_min series" and is "UNTESTED". **Disk
contradicts this.** WU-16 persists the full 193-point per-report-index worst-node
series (`delayed_collapse_case.series.p_min_psi`) and pins the θ_p = 5 psi
crossover at **report index 13 (6.5 h)** in `first_report_index_below_theta_p`.
Per CLAUDE.md §1/§7/§21 and TRUST-DISK, this review reports the **persisted**
onset and narrows the residual gap accordingly (see §11).
---

## §2 — Frozen invariants (STEP-9 must not modify)

STEP-9 is an **execution-level admissibility layer**. It must not modify any of:

- **Action space** (D-P6-001/002/003): `action_dim=7`; order
  `[VALVE-173,175,176,177,178, PUMP-170, PUMP-172]`; ABSOLUTE encoding
  `physical = lower + ((a+1)/2)·(upper−lower)`, a∈[−1,1]; bounds
  173[54.5,100], 175[21.5,110], 176[20,59.524], 177[20,90], 178[20,74],
  PUMP-170[0.82,1.10], PUMP-172[0.77,1.10]; excluded valves {174,179,180} kept;
  pumps SPEED-only, re-issued each step, native STATUS rules intact.
- **Observation** (D-P6-004): `observation_dim=139`, float32.
- **Reward** (D-P6-005, APPROVED 2026-09-27, C-A_F1_balanced_dense): weights
  w_L=1.0, w_U=1.0, w_P=1.0, w_A=0.1, w_E=0.0; constants leak_ref=84.72988433677985,
  req_ref=906.3987348621764, deficit_ref=28.671793365478514, power_ref=88.10062475649187,
  movement_L2sq_max=28.0. The effort term ‖Δa‖² is defined on the **COMMANDED** action.
- **Network topology / native EPANET STATUS & rule logic.**
- **Service-node policy:** 121 service junctions; 5 connector junctions excluded
  (JUNCTION-105/106/109/110/128).
- **Solver policy:** PDA required 20 psi, minimum 0, exponent 0.5; report step 1800 s.

## §3 — Evidence summary

Central anchors (verbatim from WU-16, reproduced by the generator self-checks):

| Quantity | Value | Source |
|----------|-------|--------|
| Baseline worst-node p_min | **4.16452169418335 psi** @ report idx 49 (24.5 h) | `reference_nominal` |
| Severe corner p_min @ decision instant | **5.527866840362549 psi** (idx 0) | `prv_lower_pump_lower` |
| Severe corner p_min over full horizon | **1.2946763038635254 psi** @ idx 192 (96 h) | `prv_lower_pump_lower` |
| Severe corner D_max | 31.727617263793945 psi·node | `prv_lower_pump_lower` |
| Severe corner DSR_min | 0.9141979346467793 | `prv_lower_pump_lower` |
| Severe corner max N_neg | **0** (never negative) | `prv_lower_pump_lower` |

**Evidence grade:** characterisation-grade, **not** a full admissible-set proof.
Empirical corners are limited to R1b (single severe corner `prv_lower_pump_lower`)
plus `reference_nominal` and `prv_all_lower`. **No validated safe/unsafe oracle
exists**; activation counts are descriptive, not false-positive/false-negative rates.

## §4 — Exact metric definitions

| Metric | Definition | Unit |
|--------|-----------|------|
| p_min | min_i p_i(t) over 121 service nodes | psi |
| Δp_min | p_min(post) − p_min(current) | psi |
| D | Σ_i max(0, 20 − p_i) | psi·node |
| ΔD | D(post) − D(current) | psi·node |
| N_neg | Σ_i 𝟙[p_i < 0] | count |
| N_20 | Σ_i 𝟙[p_i < 20] (descriptive, not an oracle) | count |
| DSR | Q_served / Q_req | ratio |
| Q_unserved | max(0, Q_req − Q_served) | gpm |
| action_deviation_L2 | ‖a_exec − a_prop‖ | — |

**SAFE-iff rules** (True = SAFE = do **not** intervene):
S1 `p_min(post) ≥ θ_p`; S2 `Δp_min ≥ −ε_p`; S3 `ΔD ≤ ε_D`; S4 `N_neg(post) == 0`.
Temporal variants TS1–TS4 apply the same over the forward window [0..H].
---

## §5 — K1 analysis (architecture D: backstop + relative)

**Composition:** S4/TS4 negative-pressure hard backstop **layered with** S2/TS2
worst-node degradation over a short window. **Threshold:** negative gate
`N_neg==0` (evidence-supported); ε_p provisional grid {0,2,5}. **Horizon:** short;
TS2 reacts at H=1 on the severe corner. **Handling:** H1 or H2, open.

**Conceptual stress test.** The S4 backstop is **inert on every tested corner**
(max N_neg = 0 including the 1.29 psi collapse), so protection rests entirely on
the layered TS2 relative rule; TS2 at ε_p=0 activates from H=1 onward. Failure
surface: if the TS2 threshold/horizon is mis-set, the backstop adds **no** 20-psi
protection. Baseline-safe (backstop never fires; relative layer identity-safe).

## §6 — K2 analysis (architecture C: aggregate-deficit look-ahead)

**Composition:** S3/TS3 aggregate-deficit increase `D(post) − D(base) ≤ ε_D` over
a finite window. **Threshold:** ε_D provisional {0,2,5}. **Handling:** H1 (reject),
open.

**Conceptual stress test.** Baseline-safe, but the aggregate can **mask** a
localised worst-node collapse: aggregate D and worst-node p_min are only weakly
anti-correlated (deficit↔leak corr −0.7735, WU-14). On the tested corner D_max
rises to 31.73 psi·node while p_min falls to 1.29 psi; an aggregate tolerance
could pass a step whose single worst node has collapsed. No absolute floor.

## §7 — K3 analysis (architecture A: immediate well-posed absolute)

**Composition:** S1 absolute worst-node floor `p_min(post) ≥ θ_p` at the decision
instant (H=0). **Threshold:** θ_p grid {0,5,10,15,20}, constrained well-posed only
strictly below the baseline worst node ~4.16452 psi. **Handling:** H3 fallback,
open.

**Conceptual stress test.** S1 reads **5.53 psi** at the decision instant and
**never** sees the 1.29 psi 96 h collapse (H=0 blindness). A well-posed absolute
floor must sit strictly below ~4.16452 psi, so it cannot enforce a useful 20-psi
floor without flagging the chronic baseline. θ_p=0 degenerates to the S4 negative
gate. Cheapest (1 solve).

## §8 — K4 analysis (architecture B: rolling absolute look-ahead)

**Composition:** TS1 absolute worst-node floor `min_{0..H} p_min ≥ θ_p` over a
rolling window. **Threshold:** θ_p grid {0,5,10,15,20}, inherits S1 ill-posedness
above ~4.16452 psi. **Horizon:** must reach the crossover onset. **Handling:** H1
or H2, open.

**Conceptual stress test.** TS1 at θ_p=5 does **not** activate for H∈{1,2,4,8}
(worst-over-window 5.4615/5.4045/5.3083/5.1472 psi) and activates once the window
reaches the **persisted crossover at report index 13 (6.5 h)**.

> **Correction vs WU-17:** the onset is **persisted, not untested**, via
> `first_report_index_below_theta_p` (θ_p=5 → index 13, 6.5 h). Cost is linear in
> H (full = 192× single-step).
---

## §9 — Immediate vs delayed safety

Two distinct safety objectives, **not** combined into a single score:

- **Immediate protection** (H=0): the decision-instant state. On the severe corner
  this reads a benign 5.53 psi — an immediate rule sees no danger.
- **Delayed protection** (over the horizon): tank drawdown drives the worst node
  from 5.53 psi (idx 0) down through the θ_p=5 crossover at **idx 13 (6.5 h)** to
  1.29 psi at idx 192 (96 h). An immediate rule is **blind** to this; only a
  look-ahead architecture (B/C/D) can see it.
- **Control freedom** (a third, competing objective): every intervention forces
  executed ≠ proposed and constrains the policy. Over-tight rules trade away the
  leakage-reduction control the policy is meant to learn.

These three are reported separately; the researcher weighs the trade-off.

## §10 — Baseline compatibility

The frozen native baseline holds a chronic worst node of ~**4.16452 psi** and
**386 node-timesteps below 20 psi** (WU-14), with **0 negative** nodes across the
full horizon. Consequences:

- **Absolute floor (S1/TS1)** is **ill-posed** as a useful 20-psi rule: any θ_p ≥
  ~4.16 psi flags the baseline itself. Only θ_p < ~4.16 psi is baseline-compatible,
  which no longer enforces 20 psi.
- **Relative rules (S2/S3, TS2/TS3)** are **baseline-safe** by construction (an
  identity hold produces no activation at ε=0).
- **Negative backstop (S4/TS4)** **never fires** on the baseline (0 negatives) —
  the only well-posed hard absolute gate.

## §11 — Horizon analysis (with the persisted crossover)

Worst-p_min over the rolling window on the severe corner (WU-16):

| H (steps / h) | worst p_min over window (psi) | TS1 θ_p=5 activates? |
|---------------|------------------------------|----------------------|
| 1 / 0.5 | 5.461512565612793 | no |
| 2 / 1.0 | 5.404520511627197 | no |
| 4 / 2.0 | 5.308281421661377 | no |
| 8 / 4.0 | 5.147222042083740 | no |
| **13 / 6.5** | *(first crossing below θ_p=5)* | **yes (onset)** |
| full 192 / 96 | 1.2946763038635254 | yes |

**Persisted crossover** (`first_report_index_below_theta_p`): θ_p=0 → never;
θ_p=5 → **idx 13 (6.5 h)**; θ_p∈{10,15,20} → idx 0 (0.0 h). A relative-degradation
rule (TS2, ε_p=0) instead activates from **H=1**.

**Smallest sufficient horizon** for an absolute floor at θ_p=5 on this corner is
therefore **H ≥ 13 control steps (6.5 h)** — a *known* quantity, correcting WU-17.

**Residual genuine gap:** only the temporal rule-activation booleans were tabulated
at coarse H∈{1,2,4,8,192}; intermediate thresholds 5<θ_p<10 and non-severe corners
are not swept — both **computable from the persisted series without new EPANET
runs**, and neither is a STEP-9 blocker.

## §12 — Threshold analysis (no threshold invented)

| Threshold | Grid / value | Label |
|-----------|-------------|-------|
| Negative gate N_neg==0 | fixed | **EVIDENCE-SUPPORTED** |
| Absolute floor θ_p | {0,5,10,15,20} psi | PROVISIONAL (well-posed only < ~4.16 psi) |
| Relative ε_p | {0,2,5} psi | PROVISIONAL |
| Aggregate ε_D | {0,2,5} psi·node | PROVISIONAL |
| Clip α (H2) | {0,0.25,0.5,0.75,1.0} | PROVISIONAL (coarse) |

The **only** evidence-supported hard threshold is `N_neg==0`. A useful absolute
20-psi floor is explicitly **THRESHOLD NOT YET EMPIRICALLY JUSTIFIED** as
baseline-compatible. All pressure/deficit tolerances remain provisional; the exact
value encodes a leakage↔service↔safety exchange rate that is a **researcher value
judgement**, not a measured quantity.
---

## §13 — Action-handling analysis (H1 / H2 / H3)

| Policy | Definition | Continuity | Extra solves |
|--------|-----------|-----------|--------------|
| **H1** reject-to-previous | execute a_prev on breach | discontinuous | 0 |
| **H2** clip-toward-previous | a_exec = a_prev + α(a_prop − a_prev) | continuous | 1 per α inspected |
| **H3** fallback reference | execute reference_nominal native setpoints | discontinuous | 0 |

Every policy makes **executed ≠ proposed** on intervention (WU-15 measures
action_deviation_L2 = 2.4050 on the reference→severe reject). H2 preserves a
continuous action image (PPO-friendly); H1/H3 are discontinuous. Not selected.

## §14 — PPO / train-execute implications

- PPO is **model-free**: the environment (and the safety layer) need **not** be
  differentiable. All candidates are deterministic and compatible with the 30-min
  control interval (WU-15/WU-16).
- Look-ahead cost is **linear in H** (H forward solves per decision; full = 192×).
- **Effort-term open question (flagged, not decided):** the frozen reward effort
  term ‖Δa‖² is defined on the **COMMANDED** action. Under an intervention,
  commanded (proposed) ≠ executed. Whether the effort term (and the env transition)
  uses the proposed or executed action is a **training-integration decision coupled
  to the handling policy** — a **D-P6-006 companion item**, not a STEP-9 blocker,
  and it does **not** modify the frozen D-P6-005 definition.

## §15 — Repeated-intervention risk (conceptual)

No closed-loop rollout is simulated in STEP-9; this is a reasoned risk map deferred
to STEP-12 testing.

- **H1 repeated:** freezing at a_prev can **compound** toward the delayed collapse
  an immediate rule cannot see (5.53 psi instant → 1.29 psi at 96 h).
- **H2 repeated:** keeps executed actions in a shrinking neighbourhood of a_prev;
  continuous but can stall exploration near a safe-but-suboptimal point.
- **H3 repeated:** repeatedly overrides the policy with reference_nominal, which is
  baseline-safe but only ~4.16 psi — not 20-psi safe.
- **Backstop:** inert in-range (N_neg=0), so it does not bound in-range drift; the
  temporal layer governs that.

Mitigation guidance (not a selection): only a look-ahead architecture (B/C/D) that
inspects the forward window can detect drawdown-driven compounding before it
materialises; the required horizon is the persisted crossover (≥ 13 steps for
θ_p=5 on the severe corner).
---

## §16 — Final provisional designs (≤3, NOT ranked, NOT scored)

Presented in **definitional order only** — the order carries **no** quality
judgement. All three are **PROVISIONAL — NOT APPROVED** implementable admissibility
layers over the frozen action/observation/reward. The researcher composes the final
D-P6-006 design from these.

### F1 — negative backstop **layered with** short-window relative degradation (arch D)
- **Rule:** S4/TS4 (`N_neg==0`) layered with S2/TS2 (worst-node non-degradation over [0..H]).
- **Threshold:** negative gate evidence-supported; ε_p provisional {0,2,5}.
- **Horizon:** short; TS2 reacts at H=1 on the severe corner.
- **Properties:** baseline-safe; reacts early; **no absolute floor**; backstop inert in-range.
- **Open:** ε_p, H, clip-vs-reject, effort-term convention.

### F2 — rolling absolute worst-node floor over a finite window (arch B, subsuming A)
- **Rule:** TS1 `min_{0..H} p_min ≥ θ_p` (A is the H=0 degenerate limit, blind to the 96 h collapse).
- **Threshold:** θ_p provisional {0,5,10,15,20}; well-posed only strictly below ~4.16452 psi.
- **Horizon:** **persisted** — smallest sufficient H for θ_p=5 is **13 steps (6.5 h)** on the severe corner.
- **Properties:** absolute guarantee within window; ill-posed as a useful 20-psi floor (THRESHOLD NOT YET EMPIRICALLY JUSTIFIED above ~4.16 psi).
- **Open:** θ_p (bounded < ~4.16 psi), H, clip-vs-reject.

### F3 — aggregate-deficit non-increase over a finite window (arch C)
- **Rule:** TS3 `max_{0..H} (D(post) − D(base)) ≤ ε_D`.
- **Threshold:** ε_D provisional {0,2,5}.
- **Horizon:** finite; relative rule reacts at H=1 on the severe corner.
- **Properties:** baseline-safe; masking risk conceptually possible (corr −0.7735) but not exhibited on the tested corner; **no absolute floor**.
- **Open:** ε_D, H, aggregate-vs-worst-node masking risk.

## §17 — Unresolved issues

**STEP-9 blockers:** *none.*

**Accepted known limitations (deferred to STEP-12):** no validated safe/unsafe
oracle; R1b single-corner empirical coverage; coarse H2 α grid; uncalibrated
leakage emitter.

**D-P6-006 companion decisions (researcher):** exact threshold value(s) within the
provisional grids (a value judgement bounded by well-posedness < ~4.16 psi for an
absolute floor); the effort-term proposed-vs-executed convention; the
smallest-sufficient horizon **if** an absolute-floor architecture is chosen
(persisted at ≥ 13 steps for θ_p=5 on the severe corner).

**Readiness:** **DECISION-READY.** The four open decisions are fully framed with
reproducible evidence; the remaining unknowns are researcher value judgements or
accepted STEP-12 limitations, not missing evidence this review could produce
without new measurement.

## §18 — Researcher decision form (D-P6-006 — BLANK)

> STEP-9 remains **PROPOSED / PENDING RESEARCHER**. The following form is
> intentionally blank; completing and approving it mints **D-P6-006** and makes the
> project PPO-ready. This review does **not** fill it in.

| Field | Selection |
|-------|-----------|
| A — architecture (A/B/C/D or F1/F2/F3) | ☐ *(blank)* |
| B — metric / rule | ☐ *(blank)* |
| C — threshold (θ_p / ε_p / ε_D) | ☐ *(blank)* |
| D — look-ahead horizon H | ☐ *(blank)* |
| E — action-handling policy (H1/H2/H3) | ☐ *(blank)* |
| F — effort-term action under intervention (proposed / executed) | ☐ *(blank)* |
| G — rationale | ☐ *(blank)* |

**Status after this review:** STEP-9 remains PROPOSED / PENDING RESEARCHER;
project is **NOT PPO-ready**; **no D-P6-006 minted**.

---

*Byte-reproducible companion: `results/phase6/p6_s9_final_decision_review.json`
(31 self-check gates, all pass). This review makes no selection, ranks nothing,
and approves nothing.*

---

## §19 — Researcher decision form (D-P6-006 — FILLED, 2026-10-01)

> **This section supersedes the §18 blank form** (§18 is preserved above as the WU-18
> history). D-P6-006 was **FINALIZED** on the researcher's explicit "STAGE B — FINALIZE
> D-P6-006" directive, composed by the AI research partner from the evidence-forced
> architecture; every value knob is flagged as reconfigurable with a mandated STEP-12
> sweep. **Authoritative record:** [`docs/PHASE6_DECISION_REGISTER.md`](PHASE6_DECISION_REGISTER.md) → D-P6-006.

| Field | Selection |
|-------|-----------|
| A — architecture | **F1** (= arch D): hard `N_neg==0` backstop (S4/TS4) **+** relative worst-node guard (S2/TS2) over `[0..H]`; **no** absolute floor; S3 not a primary gate |
| B — metric / rule | ADMISSIBLE iff over `[0..H]`: `N_neg(proposed_post)==0` **AND** `p_min(proposed_post) − p_min(hold_post) ≥ −ε_p` |
| C — threshold | backstop `N_neg==0` fixed; `ε_p` **default 0.0 psi** (sweep {0,2,5}); **no absolute θ_p** |
| D — look-ahead horizon H | **default 1 control step** (sweep {1,2,4,8}); per-step re-check primary; **no finite H claimed universally sufficient** |
| E — action-handling policy | **H1 reject-to-hold** primary + **H3 reference-fallback**; H2 clip documented as the PPO-friendlier alternative |
| F — effort-term action under intervention | **executed** (= commanded; D-P6-005 "commanded"); see `PHASE6_REWARD_SPEC.md` §8.12; D-P6-005 UNCHANGED |
| G — rationale | backstop = only well-posed hard gate (baseline 0 negatives); relative guard = baseline-safe by construction + most temporally sensitive; absolute floor ill-posed; aggregate masks localised collapse; non-universal claims only |

**`base` semantics (A1):** `hold_post` = HOLD counterfactual (continue `a_prev` from the
identical current real state over `[0..H]`); the WU-16 `reference_nominal` base is the t=0
zero-drift special case. **Reward term (A2):** executed action. Full derivations in the
register (D-P6-006 §A1) and `PHASE6_REWARD_SPEC.md` §8.12.

**Status after finalization (A3 correction):** D-P6-006 is FINALIZED, but the project is
**NOT yet PPO-ready**. Minting the decision is **step 1** of a 5-step gate
(1 finalize → 2 implement env → 3 validate behaviour → 4 integration tests with real
EPANET/WNTR → 5 **only then** PPO-ready). The §18 wording "completing and approving it …
makes the project PPO-ready" is **corrected here**: finalization unblocks **implementation**
(STAGE C), not PPO-readiness.





