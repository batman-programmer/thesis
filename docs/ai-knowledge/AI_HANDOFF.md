# AI_HANDOFF.md — Read this first

You are taking over a Master's thesis research-engineering project mid-flight.
This file tells you what it is, what has happened, what is proven, what is
merely believed, and what to do next. Everything here is either measured on
this machine or explicitly labelled as something weaker.

**Reading order:** this file → [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) →
[PROJECT_STATE.yaml](PROJECT_STATE.yaml) → [ROADMAP.md](ROADMAP.md). Then
DECISIONS.md and FINDINGS.md when you need the reasoning behind a specific
choice.

---

## 1. What the project is

**Thesis title (`USER_PROVIDED`):** *Adaptive Pressure Control in Water
Distribution Networks Using Deep Reinforcement Learning (DRL/PPO) Integrated
with EPANET to Reduce Leakage Under Uncertain Demand.*

**Degree (`USER_PROVIDED`):** Master's, Industrial Engineering.

**Aim (`USER_PROVIDED`):** train a PPO agent that continuously adjusts pressure
control actuators — PRV setpoints and variable-speed pump speeds — in a water
distribution network so that background leakage falls while customer service
pressure is maintained, under demand that the agent cannot predict.

**Network (`DECISION`, Phase 4):** BWSN-1 (Battle of the Water Sensor Networks,
network 1). 126 junctions, 1 reservoir, 2 tanks, 168 pipes, 2 pumps, 8 PRVs,
96 h extended-period simulation.

**Simulation stack (`VERIFIED_FACT`):** EPANET 2.2 driven through WNTR 1.5.0's
`EpanetSimulator`, Python 3.13.15 in `D:\Thesis\.venv`.

**Where the project is right now (`VERIFIED_FACT`):** Phase 6, step 4 of 15
complete. The hydraulic environment has been validated exhaustively; the
Gymnasium environment itself has **not been written yet**. `src/env/` does not
exist. `tests/` is empty. `gymnasium`, `stable-baselines3` and `torch` are not
installed.

---

## 2. What has happened, phase by phase

All `VERIFIED_FACT` — each phase produced a report on disk.

| Phase | What it did | Artefact |
|---|---|---|
| 1 | Repository / corpus audit | (no standalone report on disk) |
| 1.5 + 1.5-B | Deep literature review, then evidence completion | (no standalone report on disk) |
| 2 | Methodology review and scientific design | (no standalone report on disk) |
| 3 | Decision review, methodology lock, implementation gate | (no standalone report on disk) |
| 4 | Network selection + full methodology lock | `docs/phase4_decision_report.md` (86,728 B), `docs/phase4_network_evidence.md` (18,212 B) |
| 5 | BWSN-1 pre-flight: 13 validation gates G0–G12 | `docs/phase5_bwsn_preflight.md` (101,210 B) + 7 modules in `src/validation/` + 8 JSONs in `results/phase5/` |
| 6 (steps 1–4) | Discharge the two Phase 5 CONDITIONALs | `docs/phase6_g5_g12_resolution.md` (44,930 B) + 4 modules + 4 JSONs in `results/phase6/` |

**Phases 1–3 have no report file in `docs/`.** Their content survives only in
the conversation transcripts (`session-backup/`) and in the launch prompts
(`session-backup/paste-cache/`). This is a real gap — see
[MISSING_OR_UNRECOVERABLE.md](MISSING_OR_UNRECOVERABLE.md).

---

## 3. What is scientifically established

These are `VERIFIED_FACT` — produced by running code on this machine, recorded
in `results/`, and written up in the phase reports. **Do not re-derive them.**

### 3.1 The solver settings are the single most important thing in this project

The shipped `.inp` file declares `ACCURACY 0.005` and `TRIALS 40`. At those
values EPANET returns hydraulic states that **violate the emitter law by
2.0135 GPM and continuity by 9.9692 GPM while reporting 0 errors and 0
warnings.** At `ACCURACY 1e-5 / TRIALS 2000` the same violation is 0.0008 GPM.

**Consequence:** every load of the network model must set
`accuracy = 1e-5`, `trials = 2000`, `rule_timestep = 180 s`,
`report_timestep = 1800 s` **in code**, and then **assert** them. Never inherit
WNTR defaults. `src/validation/p6_s3_prv_finechar.py:117` (`assert_solver`) is
the reference implementation of this check — copy it.

### 3.2 The action space is five PRVs, not eight

Measured, not assumed. Final table in `docs/phase6_g5_g12_resolution.md` §7.

**RL-controlled: {VALVE-173, VALVE-175, VALVE-176, VALVE-177, VALVE-178}.**

Three PRVs are excluded, each for a *measured* reason, and **none is deleted
from the model**:

- **VALVE-174** — hydraulically closed at its nominal 80 psi; reopens between
  95 and 96 psi. When open it carries only 4.7–5.0 GPM (≈0.5 % of demand) and
  its only measured effect is to *raise* leakage (84.730 → 84.968 GPM) with
  **zero** change in served demand or pressure-deficit count. Adverse authority
  only. Fixed at 80 psi.
- **VALVE-179** — a **cliff actuator**. Inert from 40 psi up; opens at 43 psi;
  the cliff is between **44.8 and 44.9 psi**. Inside the safe range it moves
  leakage by 0.087 GPM (0.10 %) — nothing. 0.2 psi past the cliff, four
  high-elevation nodes hit **−97 psi** and 15.9 GPM of served demand is lost
  (DSR 0.983 → 0.970). Empty benefit, catastrophic downside. Fixed at 40 psi,
  hard-clamped ≤ 44.7 psi if ever actuated.
- **VALVE-180** — held shut by an explicit `[CONTROLS]` statement, not by
  hydraulics. Zero flow at every setting up to 120 psi while the control holds.
  With the control *released* at 40 psi it carries 273 GPM and halves the
  sub-20 psi count (386 → 193). That is the largest single service gain
  available in this network — and taking it would destroy comparability with
  every baseline and with the published benchmark. **The closure is retained.
  The finding is recorded, not exploited.**

### 3.3 Pump speed commands do not persist

`THEN PUMP <p> STATUS IS OPEN` in the native rules **restores relative speed to
1.0**, silently discarding a commanded speed. Confirmed by controlled
experiment for both pumps.

Neither EPANET mechanism does both jobs:
- `SETTING IS <speed>` writes the speed but does **not** reopen a shut pump.
- `STATUS IS OPEN` reopens the pump but overwrites its speed with 1.0.

**Measured hold rate:** 1.72 % if the speed is commanded once. **98.62 %** if
it is re-issued every control step.

### 3.4 Segmented EPS requires three-part state carry-forward

To step EPANET in 1800 s segments and reproduce a monolithic run you must carry
forward **all three** of:
1. tank levels (`init_level`),
2. pump status (`initial_status`),
3. **pattern time** (`options.time.pattern_start`).

Miss the third and demand silently restarts from hour 0 every segment.

Related trap: `wntr.metrics.expected_demand(wn)` has **two independent
defects** for segmented use — it builds its series from the model's own time
index (`np.arange(start_time, end_time+timestep, timestep)`), *and* it ignores
`options.time.pattern_start` entirely. Do not use it to compute requested
demand in a stepped environment.

### 3.5 Five junctions must be excluded from every pressure statistic

JUNCTION-105, -106, -109, -110, -128 have declared elevation **exactly
0.0 ft** and zero base demand. They are pump/reservoir connector artefacts.
EPANET reports head-above-datum at them, so JUNCTION-106 reads **501.6 psi**.

Including them raises mean service pressure from **94.787 → 101.49 psi** and
manufactures 7 spurious pressure jumps. Use the **121 demand-bearing
junctions** for every observation, every reward term and every metric. The
exclusion rule is mechanical and auditable: elevation exactly 0.0 ft **and**
zero total base demand. (Next lowest elevation in the file is 192.0 ft, so the
rule is unambiguous.)

Reference implementation: `service_nodes()` in
`src/validation/p6_s3_prv_finechar.py:79`.

### 3.6 Pump speed bounds are measured, not chosen

Shut-off speed is **0.8152 for PUMP-170** and **0.7655 for PUMP-172**. A 0.70
command yields zero open states. A speed action spanning 0.5–1.1 would waste a
third of its range on hydraulically void commands.

### 3.7 The baseline already has a service deficit

At nominal settings the pre-flight EPS has **386 node-timesteps below the
20 psi PDA threshold** and a **minimum service pressure of 4.1645 psi**
(JUNCTION-29). Any service penalty must be stated *relative to this floor*, or
a metric will blame the controller for a pre-existing deficit.

### 3.8 Phase 5 gate verdicts — settled, do not re-litigate

G0 PASS, G1 PASS, G2 CHARACTERISED, G3 PASS, G4 PASS, **G5 CONDITIONAL**,
G6 PASS, G7 PASS, G8 PASS, G9 PASS, G10 PASS, G11 PASS, **G12 CONDITIONAL**.
No gate FAILED. Overall: **CONDITIONAL PASS**. Mass balance 5.18e-07 relative.

**Both CONDITIONALs are now discharged by Phase 6** (§3.2 and §3.3 above).

---

## 4. What is only assumed

Do not present these as facts.

| Statement | Label |
|---|---|
| The leak coefficients used in Phase 5/6 are a **validation instrument**, not a calibrated field leakage model. Half-pipe-length weights, one global closed-form scale, exponent 0.5 taken from the file's own `[OPTIONS] Emitter Exponent`. | `ASSUMPTION` — and the brief explicitly forbids calling it calibrated |
| The 1.38 % residual pump override (native tank protection winning over the controller) is acceptable | `ASSUMPTION` |
| Whether that residual matters for PPO's credit assignment | `HYPOTHESIS` — to test after Phase 6 |
| PPO hyperparameters (lr 3e-4, n_steps 2048, batch 64, 10 epochs, γ 0.99, GAE λ 0.95, clip 0.2) | `PROVISIONAL` starting point, to be verified against the installed SB3 version |
| Reward weights | **Not chosen.** Must be derived from measured metric scales in STEP 8. |
| Lower leakage is a better solution | **FALSE as stated.** The brief warns: *"lower leakage ≠ necessarily better solution."* An agent can cut leakage by starving customers. Guard against this explicitly. |

---

## 5. What failed — do not repeat

Full detail in [FAILED_APPROACHES.md](FAILED_APPROACHES.md). The four that will
bite you fastest:

1. **Trusting EPANET's zero-error report.** It reported 0 errors and 0 warnings
   on states violating continuity by ~10 GPM. Silence is not validation.
2. **`Option B` for the pump-speed fix** — rewriting the native rules'
   `STATUS IS OPEN` into `SETTING IS <speed>`. Looks perfect monolithically
   (hold rate 1.000, leak 84.684 GPM) but **halts EPANET at t = 79.5 h** in the
   stepped architecture, which would leave reward undefined mid-episode.
   Disqualified on evidence.
3. **`ControlAction(pump, 'speed', ...)`** — `speed` is not a valid attribute.
   Use `base_speed`, `setting` or `status`.
4. **Assuming an in-memory attribute reached the solver.** Always write the
   `.inp` out and read it back. This "echo check" caught real discrepancies.

---

## 6. Decisions that must NOT be revisited without strong new evidence

Each is backed by a written report and measured data. Reopening them costs
weeks and invalidates existing results.

1. **BWSN-1 is the primary network.** Net3 is retained only for comparability
   with Hu et al.'s MARL paper. Kentucky KY1–KY17 were **excluded** for
   concrete reasons: `Duration 0`, empty `[CURVES]`, POWER pumps.
2. **Topology is frozen.** 126/1/2/168/2/8. *"Topological modifications are
   forbidden unless separately justified and explicitly approved."*
3. **The original `.inp` is never edited.** Work on
   `data/networks/working/BWSN_Network_1_working.inp`. The only patch applied is
   `Quality Chemical TIME` → `Quality Chemical mg/L`.
4. **Solver settings 1e-5 / 2000 / 180 s / 1800 s are non-negotiable.**
5. **The action space is the five PRVs of §3.2.**
6. **Pump strategy is Option C on Option A's mechanism:** native rules
   untouched; 1800 s segments with three-part carry-forward; speed re-issued
   every control step; agent commands **speed only** (status stays with the
   native rules); `info` reports commanded and realised speed **separately**.
7. **PDA is the demand model for training** (required 20 psi, minimum 0 psi,
   pressure exponent 0.5). DDA only as the final re-run that supports claim N9.
8. **Never observe the true leak flow or the true leak location.** A real SCADA
   system cannot measure them. Including them is data leakage.
9. **`C` and `alpha` in the leakage model must be identical between the RL
   agent and every baseline.** Changing them between arms invalidates the
   comparison.
10. **Evaluation is never by scalarised reward.** The weighted sum exists for
    training only.

---

## 7. What remains unfinished

Phase 6 has 15 steps. **Steps 1–4 are done. Steps 5–15 are not.**

| Step | Work | Status |
|---|---|---|
| 5 | Absolute vs delta action formulation; choose one | `PLANNED` |
| 6 | Derive all five PRV bounds from measurement (not from guesses) | `PLANNED` |
| 7 | Observation design + deterministic normalisation | `PLANNED` |
| 8 | Measure reward metric scales **first**, then weight | `PLANNED` |
| 9 | Safety / action-mapping layer — safety must not be left to reward alone | `PLANNED` |
| 10 | Demand uncertainty; train/val/test/OOD separation; seeds; scenario IDs | `PLANNED` |
| 11 | Implement `src/env/` (8 modules, Gymnasium API) | `PLANNED` — blocked on installing `gymnasium`, `stable-baselines3`, `torch` |
| 12 | The 16 mandated automated tests | `PLANNED` — `tests/` is empty |
| 13 | Very short SB3 PPO **compatibility smoke test only** | `PLANNED` |
| 14 | Freeze the environment specification | `PLANNED` |
| 15 | Phase 6 report: deliverables A–J, decision table, formalisation, one verdict | `PLANNED` |

**Hard prohibition still in force (`USER_PROVIDED`, Phase 6 brief §0):**
> «در این Phase به هیچ عنوان هنوز آزمایش علمی PPO انجام نده»
> *Do not, under any circumstances, run a scientific PPO experiment in this
> phase.*

Step 13 is a compatibility check that the API wires up — not a training run,
not a result.

Two debts carried from Phase 4:
- Correct the proposal's mis-citation of Hu et al.'s MARL paper to *Water
  Supply* **23(7):2833**, doi **10.2166/ws.2023.163**.
- Re-verify Negm's Table 5-4 **directly from the PDF** before citing it.

---

## 8. Files to inspect first, in order

1. `D:\Thesis\CLAUDE.md` — the project's operating constitution. 23 sections.
   Binding on any agent working here. Read it before touching anything.
2. `docs/phase6_g5_g12_resolution.md` — the current state of the art. §7 has the
   action-space table; §16 has the pump decision.
3. `docs/phase5_bwsn_preflight.md` — §17 for the gate table, **§19 for the nine
   exact changes required before RL**. §19 is effectively the implementation
   checklist for Phase 6.
4. `docs/phase4_decision_report.md` — the "Locked configuration" block
   (lines 942–1200) is the master specification: network, leakage, demand,
   PDA/DDA, PRV placement, pump model, state, action, reward, uncertainty, PPO,
   baselines, test protocol, seeds.
5. `src/validation/phase5_common.py` — shared harness: unit conversions,
   working-copy construction, environment capture.
6. `src/validation/p6_s3_prv_finechar.py` — the cleanest reference for how a
   validated measurement module is written here: explicit solver config,
   `assert_solver`, `service_nodes`, echo check, JSON output.
7. `src/validation/p6_s4_pump_strategy.py` — the stepped-EPS harness. This is
   the code the RL environment's `step()` will be built on.

---

## 9. Skills, plugins and integrations

Full detail in [SKILLS_INDEX.md](SKILLS_INDEX.md),
[PLUGINS_INDEX.md](PLUGINS_INDEX.md),
[MCP_AND_INTEGRATIONS.md](MCP_AND_INTEGRATIONS.md).

- **4 project skills** (`.claude/skills/`): `research-review`,
  `methodology-review`, `novelty-check`, `change-impact`. These encode the
  project's own review workflow and are the most directly reusable by another
  agent — they are plain Markdown instructions with no Claude-specific tooling.
- **3 Claude Code plugins installed:** `academic-research-skills` v3.21.1 (14
  slash commands, 36 subagents), `document-skills` (docx/pdf/pptx/xlsx),
  `superpowers` v6.3.0.
- **`superpowers` ships manifests for eight harnesses** — `.claude-plugin`,
  `.codex-plugin`, `.cursor-plugin`, `.devin-plugin`, `.hermes-plugin`,
  `.kimi-plugin`, `.opencode`, `.pi`. If you are a non-Claude agent, read
  `plugins-backup/superpowers-6.3.0/.kimi-plugin/plugin.json` — it contains an
  explicit tool-name mapping table for exactly this situation.
- **MCP: Claude Code has zero MCP servers configured.** Global `mcpServers` is
  `null`; every project entry is empty. The only MCP definitions on the machine
  belong to two Claude *Desktop* remote plugins (11 servers, 2 with empty URLs).
  **No project functionality depends on MCP.**

---

## 10. How to interpret Memory

**Persistent memory is empty. This is a verified observation, not a gap in the
backup.**

All three `~/.claude/projects/*/memory/` directories contain zero files, and no
`MEMORY.md` exists anywhere under `~/.claude`. The project's durable knowledge
lives in `docs/*.md` and `CLAUDE.md`, not in an agent memory store.

**Practical consequence:** treat `docs/` as the memory. If you are an agent with
a memory facility, seed it from `PROJECT_STATE.yaml` and §3 and §6 of this file.

---

## 11. Immediate next steps

In dependency order. Do not reorder — step 8 depends on step 7, step 11 depends
on 5–10.

1. **Read `CLAUDE.md`.** It overrides your defaults.
2. **Phase 6 STEP 5** — decide absolute vs delta PRV action. Both are live; the
   brief demands one primary choice with a stated reason.
3. **Phase 6 STEP 6** — measure and set the bounds for all five controlled PRVs.
   *"DO NOT choose arbitrary actuator bounds."* Sweep each valve as
   `p6_s3_prv_finechar.py` does and read the safe domain off the measurement.
4. **Phase 6 STEP 7** — observation vector + normalisation constants computed
   once and frozen. No future information. No true leak flow or location.
5. **Phase 6 STEP 8** — run a measurement pass to get the *scales* of leakage,
   pressure violation, energy and actuator movement, and only then set weights.
6. **Install the RL stack** with pinned versions: `gymnasium`,
   `stable-baselines3`, `torch`. Record the exact versions.
7. **Phase 6 STEP 11–12** — write `src/env/` and the 16 tests.
8. **Only then** the SB3 smoke test, then freeze, then report.

---

## 12. One thing to internalise before you start

This project's standard of evidence is unusually high, deliberately. Its two
recurring failure modes were both *silent*: a solver that reported success on
wrong answers, and a control mechanism that accepted a command and quietly
discarded it. Every subsequent design decision has been made by **measuring**
rather than reasoning — the five-PRV action space, the 44.8/44.9 psi cliff, the
0.8152 shut-off speed, the 98.62 % hold rate.

Continue that. When you are about to write a number into the environment, ask
where it was measured. If the answer is "it seemed reasonable", measure it.
