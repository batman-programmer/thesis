# ROADMAP.md — completed, active, blocked, pending

Position as of **2026-09-07**: **Phase 6, step 4 of 15 complete.**

The hydraulic environment has been validated exhaustively. The Gymnasium
environment itself has **not been written**. `src/env/` does not exist, `tests/`
is empty, and `gymnasium` / `stable-baselines3` / `torch` are not installed.

Priorities below are the brief's own STEP order (§36), not invented ones. The
dependency chain is real: STEP 8 cannot start before STEP 7, and STEP 11 cannot
start before 5–10.

---

## 1. Completed

`COMPLETED` — each item produced an artefact on disk.

| Phase | Work | Artefact | Note |
|---|---|---|---|
| 1 | Repository / corpus audit | — | **No report file in `docs/`.** Survives only in `session-backup/` transcripts and paste-cache prompts |
| 1.5 | Deep literature review | — | Same gap |
| 1.5-B | Evidence completion | — | Same gap |
| 2 | Methodology review and scientific design | — | Same gap. Its launch prompt references "42 research sources" and a Phase 1 Audit |
| 3 | Decision review, methodology lock, implementation gate | — | Same gap |
| 4 | Network selection + full methodology lock | `docs/phase4_decision_report.md` (86 728 B), `docs/phase4_network_evidence.md` (18 212 B) | Contains the master "Locked configuration" block |
| 5 | BWSN-1 pre-flight: 13 gates G0–G12 | `docs/phase5_bwsn_preflight.md` (101 210 B) + 7 modules in `src/validation/` + 8 JSONs in `results/phase5/` | Verdict **CONDITIONAL PASS**; no gate FAILED |
| 6 steps 1–4 | Discharge the two Phase 5 CONDITIONALs | `docs/phase6_g5_g12_resolution.md` (44 930 B) + 4 modules + 4 JSONs in `results/phase6/` | **G5 RESOLVED, G12 RESOLVED** |

### What "completed" bought, concretely

- Solver settings established as the dominant correctness lever, and the
  `assert_solver` discipline that enforces them.
- The action space reduced from 8 PRVs to **5**, each exclusion resting on a
  measured quantity.
- Pump control strategy decided: **Option C on Option A's mechanism**, with the
  1.38 % residual override quantified rather than assumed away.
- The stepped-EPS harness that the RL `step()` will be built on, validated
  against the monolithic reference to 1.5e-05.
- The 121-junction service node set, the leakage instrument, the PDA
  configuration, the deficit floor, and the pump speed bounds — all measured.

---

## 2. Active

Nothing is in progress. Phase 6 STEP 4 closed with a written report; STEP 5 has
not been started.

The only work in flight outside the phase sequence is this backup package itself
(`docs/ai-knowledge/`), which is a preservation task, not research.

---

## 3. Blocked

| Item | Blocked on | How to unblock |
|---|---|---|
| **STEP 11** — implement `src/env/` | `gymnasium`, `stable-baselines3`, `torch` not installed in `D:\Thesis\.venv` | Install with **pinned** versions and record the exact version strings. The PPO hyperparameters currently recorded are `PROVISIONAL` and must be verified against the installed SB3 version |
| **STEP 12** — the 16 mandated tests | `src/env/` must exist | `tests/` is currently empty |
| **STEP 13** — SB3 compatibility smoke test | STEP 11 + STEP 12 | And it is **only** a compatibility check. Brief §0: «در این Phase به هیچ عنوان هنوز آزمایش علمی PPO انجام نده» |
| **Negm Table 5-4 citation** | The PDF must be re-read directly | Debt carried from Phase 4. Do not cite the table until verified from the source |
| **The BWSN-1 baseline-deficit question** | The BWSN-1 problem statement, which the author has not obtained | `OPEN_QUESTION`: is the deficit an intentional feature of the benchmark scenario or an artefact of its construction? Phase 5 recorded the same UNKNOWN for whether BWSN-1 declares a service pressure threshold at all |

---

## 4. Pending — Phase 6 STEP 5 to 15

In dependency order. **Do not reorder.**

### STEP 5 — Action formulation: absolute vs delta

`PLANNED`. Both are live. The brief demands **one** primary choice with a stated
reason.

- Absolute: the agent emits the setpoint directly. Simple, stateless, but a large
  jump between consecutive steps is physically implausible for a real PRV.
- Delta: the agent emits a change. Naturally rate-limited, but makes the
  observation history-dependent and the action space's reachable set
  time-dependent.
- Whatever is chosen must interact correctly with the STEP 9 safety layer and with
  the actuator-movement reward term.

### STEP 6 — Derive all five PRV bounds from measurement

`PLANNED`. Brief §14: **"DO NOT choose arbitrary actuator bounds."**

Method is already established — sweep each valve as
`src/validation/p6_s3_prv_finechar.py` does, read the safe domain off the
measurement, then check joint action as `p6_s3c_zone_interaction.py` does. Nominal
settings to sweep around: VALVE-173 at 70 psi, VALVE-175 at 55, VALVE-176 at
29.762, VALVE-177 at 45, VALVE-178 at 37.

Already known: VALVE-178 moves mean leakage by only about ±0.1 GPM over
0.75–1.25× and produced no negative pressure in the §4.5 grid; VALVE-175 carries
38.495 % of system demand across a 115.00 psi setpoint span.

Also fix in this step: pump speed bounds from the measured feasible range
(shut-off 0.8152 for PUMP-170, 0.7655 for PUMP-172), **not** 0.5–1.1.

### STEP 7 — Observation design and deterministic normalisation

`PLANNED`. Brief §11, §13, §21.

- Include what a real SCADA system could measure. **Never** the true leak flow or
  the true leak location — that is data leakage.
- No future information of any kind.
- Normalisation constants computed **once** and **frozen**; not recomputed per
  episode, not adapted online.
- Statistics over the **121** service junctions only.
- «اما همه را کورکورانه وارد نکن» — do not include every available signal blindly.

### STEP 8 — Measure reward metric scales first, then weight

`PLANNED`. Brief §20: «اما ضرایب را با حدس انتخاب نکن».

**Weights are currently not chosen and must not be guessed.** Required order:

1. Run a measurement pass to obtain the *scales* of leakage, pressure violation,
   energy and actuator movement over a representative action range.
2. Only then set normalisation and weights.
3. State every service penalty **relative to the measured deficit floor**: 386
   node-timesteps below 20 psi, minimum 4.1645 psi at JUNCTION-29.
4. Guard explicitly against the starvation pathway — an agent cutting leakage by
   starving customers. Measured stakes: at all PRVs ×0.25, only **3.39 %** of the
   inflow reduction is leakage saving and **99.67 %** is unserved demand.
5. Re-derive the pump energy relationship under the Option C mechanism first; the
   Phase 5 measurement is contaminated by the non-persistence defect.

### STEP 9 — Safety / action-mapping layer

`PLANNED`. Brief §16: «Safety باید فقط به reward واگذار نشود» — safety must not be
left to the reward alone.

Requirements already established by measurement:

- Negative service pressure must be excluded **by construction**, not merely
  penalised: at negative pressure the signed emitter law makes the leakage
  instrument report water *entering* the network, so the accounting is corrupted,
  not just the physics.
- VALVE-179 hard-clamped ≤ 44.7 psi if ever actuated.
- The layer must **detect the VALVE-179-class failure at runtime**, because
  separability of the box constraints is a `HYPOTHESIS`, verified only on the 18
  tested cases, not proved over the full joint action space including pump-speed
  variation.

### STEP 10 — Demand uncertainty and scenario separation

`PLANNED`. Brief §21, §26.

Train / validation / test / **OOD** sets kept separate; seeds recorded; scenario
IDs assigned and stored with results. `env.reset(seed=123)` must reproduce
exactly (brief §23).

### STEP 11 — Implement `src/env/`

`PLANNED`, **blocked** (see §3). Eight modules named by the brief §27:

```
src/env/bwsn_env.py         Gymnasium API surface
src/env/epanet_adapter.py   the stepped-EPS loop, three-part carry-forward
src/env/state_builder.py    observation assembly + frozen normalisation
src/env/action_mapper.py    absolute-or-delta → PRV setpoints, pump speeds
src/env/safety.py           the STEP 9 layer
src/env/reward.py           the STEP 8 terms and weights
src/env/demand_scenarios.py the STEP 10 generator
src/env/metrics.py          evaluation metrics, never the scalarised reward
```

«از overengineering پرهیز کن» — avoid overengineering.

Build `epanet_adapter.py` on `src/validation/p6_s4_pump_strategy.py`, which is the
validated stepped harness. Copy `assert_solver` and `service_nodes` from
`src/validation/p6_s3_prv_finechar.py` (lines 117 and 79).

Must not reintroduce: missing pump-status carry-forward, missing
`pattern_start` advance, or `wntr.metrics.expected_demand` per segment.

`info` must report commanded and realised speed **separately** (brief §25).

### STEP 12 — The 16 mandated automated tests

`PLANNED`, blocked on STEP 11. `tests/` is empty. Brief §28 requires all 16 to
pass **before** any PPO work.

### STEP 13 — SB3 PPO compatibility smoke test

`PLANNED`, blocked. Brief §29. A few hundred timesteps to prove the API wires up.
**Not a training run. Not a result.** The §0 prohibition remains in force.

### STEP 14 — Freeze the environment specification

`PLANNED`. Once frozen, changing any of it invalidates results computed against it.

### STEP 15 — Phase 6 report

`PLANNED`. Deliverables A–J (§33), the formal decision table (§31), the
mathematical formalisation (§32), every statement carrying exactly one of the four
labels (§35 — «هیچ کدام را با هم مخلوط نکن»), and **exactly one** overall verdict:
PASS, CONDITIONAL or FAIL (§34).

---

## 5. Debts and housekeeping

| Item | Type | Priority |
|---|---|---|
| Correct the proposal's mis-citation of Hu et al.'s MARL paper to *Water Supply* **23(7):2833**, doi **10.2166/ws.2023.163** | Phase 4 debt | Before any thesis text cites it |
| Re-verify Negm's Table 5-4 **directly from the PDF** before citing | Phase 4 debt | Before citing |
| Six zero-byte stubs in `docs/`: `assumptions.md`, `decisions.md`, `experiments.md`, `literature.md`, `open_questions.md`, `research_questions.md` | Housekeeping — noted, not requested | Low. `CLAUDE.md` §18 names these files; the content currently lives in the phase reports and in `docs/ai-knowledge/` |
| `results/phase5/_tmp` holds **459 MB** / 3963 EPANET scratch files | Housekeeping — noted, not requested | Low. Regenerable by rerunning the validation modules |
| Phases 1–3 have no report in `docs/` | Documentation gap | Medium. Recoverable only by reading `session-backup/` transcripts. See `MISSING_OR_UNRECOVERABLE.md` |

---

## 6. Unresolved scientific questions

Carried forward as `OPEN_QUESTION` / `HYPOTHESIS`. None blocks STEP 5.

1. **Does box-constraint separability hold over the full joint action space?**
   `HYPOTHESIS`. Verified on 18 cases; not proved, and pump-speed variation was
   not part of either design. Drives the STEP 9 runtime-detection requirement.
2. **Does the 1.38 % pump override matter for PPO's credit assignment?**
   `HYPOTHESIS`, to test after Phase 6. The agent will occasionally be credited or
   blamed for a state the native rules produced.
3. **Is BWSN-1's baseline service deficit intentional?** `OPEN_QUESTION`. Needs the
   benchmark's problem statement.
4. **Does BWSN-1 declare a service pressure threshold at all?** `OPEN_QUESTION`,
   recorded as UNKNOWN in Phase 5. The 20 psi PDA threshold is this project's
   choice, not the benchmark's declaration.
5. **How should absolute-vs-delta interact with a rate limit that a real PRV
   would have?** `OPEN_QUESTION` for STEP 5.
6. **What is the correct scale relationship between the four reward terms?**
   `OPEN_QUESTION` — deliberately unanswered until STEP 8 measures it.
7. **Are the surviving novelty claims (N6, N7, N8, N10, N11) still HIGH after the
   2026 literature?** `OPEN_QUESTION`. The OpenAlex sweep is a lower bound on the
   field, not coverage — Hu et al. 2023 does not appear in its counts.

---

## 7. The single next action

**Phase 6 STEP 5.** Decide absolute vs delta PRV action formulation, with a stated
reason, then STEP 6's bound measurements.

Before touching anything: read `D:\Thesis\CLAUDE.md`. It overrides defaults.
