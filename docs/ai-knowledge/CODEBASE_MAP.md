# CODEBASE_MAP.md — actual filesystem inventory of `D:\Thesis`

Every entry below was read from the filesystem during this backup
(`DIRECT_OBSERVATION`). Sizes and line counts are measured, not estimated.
Directories recorded as empty were checked and are empty.

Inventory date: **2026-09-07**.

---

## 1. Top level

```
D:\Thesis\
├── .claude\                 project-local Claude Code configuration (5 files)
├── .git\                    git repository, branch main
├── .venv\                   Python 3.13.15 virtual environment (NOT backed up)
├── CLAUDE.md                18 435 B — the operating constitution, 23 sections
├── data\                    the network models (2 files)
├── docs\                    phase reports + this backup
├── experiments\             EMPTY
├── notes\                   EMPTY
├── papers\                  42 PDFs (not copied — copyrighted; indexed in LITERATURE.md)
├── proposal\                proposal.pdf
├── results\                 gate artefacts + a 459 MB scratch directory
├── seminar\                 seminar.pdf
├── src\                     validation modules only — src/env/ DOES NOT EXIST
├── tests\                   EMPTY
├── theses\                  EMPTY
├── 2026-09-01-230559-local-command-caveatcaveat-the-messages-below.txt   1 138 444 B
└── 2026-09-06-232706-this-session-is-being-continued-from-a-previous-c.txt  124 794 B
```

The two root `.txt` files are exported conversation transcripts. Both were copied
into `session-backup/`.

**Git.** Branch `main`. Recent commits: `d921024 10-06-1405`, `abd0ec6 02-06-1405`,
`5455046 Create README.md`. At the start of this session, `data/`, `docs/*.md` (the
four phase reports), `results/`, `src/` and the two root `.txt` files were all
**untracked**. `CLAUDE.md` is tracked. **There is no `README.md` in the working
tree** despite the commit message, and no `.gitignore` was observed.

---

## 2. `src\` — 13 Python modules, 297 337 B total

**`src\env\` does not exist.** No Gymnasium environment has been written. The
entire `src/` tree is validation code.

```
src\validation\
```

| File | Bytes | Lines | Purpose (first line of its own docstring) |
|---|---|---|---|
| `phase5_common.py` | 10 611 | 299 | *Phase 5 — BWSN-1 pre-flight validation: shared utilities.* |
| `g0_integrity.py` | 18 464 | 408 | *Gate 0 — file integrity and conformance with the Phase 4 report.* |
| `g1_baseline.py` | 20 492 | 457 | *Gates 1, 2 and 11 — baseline convergence, native control logic, tank dynamics.* |
| `g3_pump_speed.py` | 22 550 | 440 | *Gate 3 — pump speed response.* |
| `g4_g5_prv.py` | 20 537 | 388 | *Gates 4 and 5 — PRV actuator responsiveness and action-dimension audit.* |
| `g6_g7_g8_leak_pda.py` | 53 277 | 974 | *Gates 6, 7 and 8 — leakage validation, PDA response, leakage/service separation.* |
| `g9_g10_full.py` | 41 798 | 844 | *Gates 9 and 10 — system mass balance and the full 96 h pre-flight EPS.* |
| `g12_realizability.py` | 40 251 | 803 | *Gate 12 — actuator realizability in the configuration the RL agent will drive.* |
| `p6_s3_prv_finechar.py` | 16 094 | 348 | *Phase 6 / STEP 3 — fine characterisation of VALVE-179, VALVE-174, VALVE-180.* |
| `p6_s3b_v179_refine.py` | 7 126 | 173 | *Phase 6 / STEP 3b — sub-psi refinement of the VALVE-179 safety cliff.* |
| `p6_s3c_zone_interaction.py` | 8 125 | 188 | *Phase 6 / STEP 3c — is the VALVE-179 safe bound valid under JOINT action?* |
| `p6_s4_pump_strategy.py` | 33 812 | 665 | *Phase 6 / STEP 4 — pump control strategy: measure Options A, B, C.* |
| `run_all.py` | 4 345 | 113 | *Phase 5 driver: run every gate in order and collect the verdicts.* |

Also present: `src\validation\__pycache__\` with 6 `.pyc` files. Note that
`phase5_common` has **both** a `cpython-313` and a `cpython-314` bytecode file —
evidence that the module was at some point imported by the **system** Python 3.14
at `C:\Python314` rather than by the project venv. Always invoke
`.venv\Scripts\python.exe` explicitly.

### The three modules that matter most to a new agent

**`p6_s3_prv_finechar.py`** — the cleanest reference for how a validated
measurement module is written here. Copy from it rather than reinventing:

- `assert_solver(wn, *, report_timestep_s=REPORT_TIMESTEP_S) -> dict` at **line
  117** — sets and then **asserts** `ACCURACY 1e-5`, `TRIALS 2000`, rule timestep
  180 s, report timestep 1800 s. Non-negotiable on every model load.
- `service_nodes(wn) -> tuple[list[str], list[str]]` at **line 79** — the
  mechanical connector-node exclusion:

  ```python
  def service_nodes(wn) -> tuple[list[str], list[str]]:
      conn, svc = [], []
      for j in wn.junction_name_list:
          nd = wn.get_node(j)
          el_ft = float(C.m_to_ft(nd.elevation))
          base = float(sum(d.base_value for d in nd.demand_timeseries_list))
          (conn if (el_ft == 0.0 and base == 0.0) else svc).append(j)
      return sorted(svc), sorted(conn)
  ```

  Asserted downstream as `assert len(svc) == 121 and len(conn) == 5`.
- Module-level constants: `SOLVER_ACCURACY = 1e-5`, `SOLVER_TRIALS = 2000`,
  `RULE_TIMESTEP_S = 180`, `REPORT_TIMESTEP_S = 1800`,
  `SERVICE_PRESSURE_PSI = 20.0`, `TARGETS = ["VALVE-179", "VALVE-174",
  "VALVE-180"]`, and the `GRIDS` dict.
- Other functions: `build(setting_psi, valve, *,
  release_valve180_control=False)` at line 95, `measure(wn, res, coeff_us, svc,
  conn, valve)` at line 148, `run_case(...)` at line 223, `main()` at line 251.
- Its docstring records that Phase 5's `g4_g5_prv.py` did **not** set
  accuracy/trials and inherited `0.005/40`, so "its snapshot harness is therefore
  deliberately not reused here."

**`p6_s4_pump_strategy.py`** — the stepped-EPS harness. **This is the code the RL
environment's `step()` will be built on.** It implements the three-part
carry-forward (tank `init_level`, pump `initial_status`,
`options.time.pattern_start`) and the dual-cadence reporting (1800 s statistics,
180 s rule-firing detection).

**`phase5_common.py`** — the shared harness: unit conversions (imported as `C`
elsewhere), working-copy construction, environment capture. Also writes
`results/phase5/working_copy_provenance.json`.

### Reproduce all of Phase 5

```bash
.venv/Scripts/python.exe src/validation/run_all.py
```

`run_all.py` runs the seven gate modules **in separate processes** in dependency
order — `g0_integrity.py`, `g1_baseline.py`, `g3_pump_speed.py`, `g4_g5_prv.py`,
`g6_g7_g8_leak_pda.py`, `g9_g10_full.py`, `g12_realizability.py` — so a failure in
one cannot corrupt another's interpreter state, then reads the artefacts back and
prints the consolidated verdict table. It accepts **two** artefact shapes (a single
`verdict` string or a `verdicts` mapping) so single-gate modules are not silently
dropped from the table. Its docstring records: *"Nothing here tunes, searches,
optimises or trains. Every gate is deterministic: no random seed is used anywhere
in phase 5."*

The four Phase 6 modules are run individually; there is no Phase 6 driver.

---

## 3. `data\` — exactly 2 files

| File | Bytes | Note |
|---|---|---|
| `data\networks\BWSN_Network_1.inp` | **44 402** | The distributed benchmark. SHA-256 `510af942ec643eb87adcf26e5a7df1cc4c23eb0c1e470a8a1257ed055f1956f1`. **Never edited.** |
| `data\networks\working\BWSN_Network_1_working.inp` | **45 063** | The working copy. Differs by exactly one patch: `Quality Chemical TIME` → `Quality Chemical mg/L`. All work uses this file. |

The size difference is the patch plus whatever WNTR's writer normalises. Provenance
is recorded in `results/phase5/working_copy_provenance.json` (2 142 B).

**No demand-scenario data exists.** Nothing has been generated for STEP 10.

---

## 4. `results\` — 13 artefacts, plus 459 MB of scratch

### `results\phase5\` — 9 files

| File | Bytes | Written by |
|---|---|---|
| `g0_integrity.json` | 21 359 | `g0_integrity.py` |
| `g1_g2_g11_baseline.json` | 38 258 | `g1_baseline.py` |
| `g3_pump_speed.json` | 59 493 | `g3_pump_speed.py` |
| `g4_g5_prv.json` | 222 829 | `g4_g5_prv.py` — **produced at `0.005/40`; numerics not carried into Phase 6** |
| `g6_g7_g8_leak_pda.json` | 375 489 | `g6_g7_g8_leak_pda.py` |
| `g9_g10_full.json` | 46 259 | `g9_g10_full.py` |
| `g12_realizability.json` | 93 417 | `g12_realizability.py` |
| `working_copy_provenance.json` | 2 142 | `phase5_common.py` |
| `run_all_console.txt` | 7 672 | `run_all.py` — consolidated console log |

### `results\phase6\` — 4 files

| File | Bytes | Written by |
|---|---|---|
| `p6_s3_prv_finechar.json` | 253 885 | `p6_s3_prv_finechar.py` |
| `p6_s3b_v179_refine.json` | 82 438 | `p6_s3b_v179_refine.py` |
| `p6_s3c_zone_interaction.json` | 181 129 | `p6_s3c_zone_interaction.py` |
| `p6_s4_pump_strategy.json` | 435 006 | `p6_s4_pump_strategy.py` |

### `results\phase5\_tmp\`

**3 963 files, 459 MB** of EPANET scratch output (`.inp`, `.rpt`, `.bin` per solve).
**Deliberately not backed up** — regenerable by rerunning the validation modules,
and it is intermediate solver output, not research evidence. Every JSON artefact it
supports *is* backed up in place.

Every artefact carries an `env` block with the interpreter and library versions, so
each result is self-describing. No random seed appears anywhere in Phase 5 or
Phase 6 — reruns reproduce artefacts bit-for-bit apart from timestamps.

---

## 5. `docs\` — four real reports, six empty stubs, and this backup

### The phase reports

| File | Bytes | Content |
|---|---|---|
| `phase4_decision_report.md` | **86 728** | The master specification. The **"Locked configuration" block at lines 942–1200** defines network, leakage, demand, PDA/DDA, PRV placement, pump model, state, action, reward, uncertainty, PPO, baselines, test protocol and seeds. §9 is the N1–N16 novelty re-audit. |
| `phase4_network_evidence.md` | **18 212** | The network-selection evidence: why BWSN-1, why not Net3, why not Kentucky KY1–KY17. |
| `phase5_bwsn_preflight.md` | **101 210** | The 13 gates G0–G12. **§17** is the gate verdict table; **§19 is the nine exact changes required before RL** and is effectively the Phase 6 implementation checklist. |
| `phase6_g5_g12_resolution.md` | **44 930** | Current state of the art. Part I = G5 (§7 has the action-space table). Part II = G12 (§16 has the pump decision). 17 numbered sections. |

### Zero-byte stubs

`assumptions.md`, `decisions.md`, `experiments.md`, `literature.md`,
`open_questions.md`, `research_questions.md` — **all 0 bytes**. These are the
filenames `CLAUDE.md` §18 nominates for durable project knowledge; they were
created and never filled. Their intended content currently lives in the phase
reports and in `docs/ai-knowledge/`.

**Consequence for a new agent:** `docs/research_questions.md` being empty is why
the research questions in `PROJECT_CONTEXT.md` are labelled `INFERENCE` rather than
`USER_PROVIDED`.

### `docs\ai-knowledge\` — this backup

Nine copied-artefact directories plus the authored documents:

| Directory | Contents | Size |
|---|---|---|
| `skills-backup\` | 4 project skills + 11 Claude Desktop skills, verbatim | 4.1 MB |
| `plugins-backup\` | 5 full plugin source trees, verbatim | 52 MB |
| `mcp-backup\` | the 2 `.mcp.json` files that exist on the machine | 5 KB |
| `commands-backup\` | 18 slash-command definition files | 54 KB |
| `hooks-backup\` | both plugins' hook configs **and** their hook scripts | 35 KB |
| `agents-backup\` | 39 subagent definition files | 1.4 MB |
| `session-backup\` | 14 Claude Code transcripts, 10 paste-cache prompts, a 98-entry prompt history, 2 root `.txt` transcripts | 20 MB |
| `config-backup\` | 9 configuration files (1 redacted) | 61 KB |
| `_backup_tools\` | `mk_session_aux.py` — the script that generated two session-backup files, kept so extraction is reproducible rather than asserted | 3 KB |

---

## 6. `.claude\` — project-local configuration, 5 files

```
.claude\
├── settings.local.json                          ~140-entry tool allow-list
└── skills\
    ├── change-impact\SKILL.md
    ├── methodology-review\SKILL.md
    ├── novelty-check\SKILL.md
    └── research-review\SKILL.md
```

The four skills encode the project's own review workflow. They are plain Markdown
with no Claude-specific tooling, so they are the most **directly portable** asset in
the repository — a non-Claude agent can follow them as instructions. All four are
copied verbatim to `skills-backup/project-skills/`.

`settings.local.json` is a permission allow-list only; it contains no secrets and is
copied to `config-backup/`.

---

## 7. Research corpus

| Path | Contents | Backed up? |
|---|---|---|
| `papers\` | **42 PDFs** — 36 English, 6 Persian | **No.** Copyrighted. Indexed by exact filename in `LITERATURE.md`; files left in place |
| `proposal\proposal.pdf` | 1 file — the approved proposal | No. Binding project constraint per `CLAUDE.md` §1 and §5 |
| `seminar\seminar.pdf` | 1 file — the seminar report | No. Same status |
| `theses\` | **EMPTY** | — |
| `notes\` | **EMPTY** | — |

The proposal and seminar are **mandatory project constraints**, not optional
context. A new agent cannot fully honour `CLAUDE.md` §1 without reading them, and
they are not in this backup — see `MISSING_OR_UNRECOVERABLE.md`.

---

## 8. Directories that exist but are empty

| Path | Meaning |
|---|---|
| `tests\` | **The 16 mandated environment tests do not exist.** Phase 6 STEP 12 |
| `experiments\` | No experiment-runner scaffolding yet |
| `notes\` | — |
| `theses\` | — |

None of these is an error. Each is a placeholder for work that Phase 6 has not
reached.

---

## 9. `.venv\` — not backed up, exactly reconstructible

Python **3.13.15** at `D:\Thesis\.venv`. Excluded from the backup because it is
fully reconstructible from the pinned list recorded in `CLAUDE_ENVIRONMENT.md`:

```
cffi 2.1.1 · contourpy 1.3.3 · cycler 0.12.1 · epyt 2.3.5.2 · fonttools 4.64.0
kiwisolver 1.5.1 · matplotlib 3.11.1 · networkx 3.6.1 · numpy 2.5.2
packaging 26.3 · pandas 3.0.5 · pillow 12.3.0 · pip 26.2.1 · pycparser 3.0
pyparsing 3.3.2 · python-dateutil 2.9.0.post0 · scipy 1.18.1 · setuptools 84.0.0
six 1.17.0 · tzdata 2026.3 · wntr 1.5.0 · xlsxwriter 3.2.9
```

**`gymnasium`, `stable-baselines3` and `torch` are ABSENT.** Installing them with
pinned versions is a prerequisite for STEP 11.

`epyt 2.3.5.2` wraps **EPANET 2.3.05** — a *different engine* from the EPANET
**2.2 / DLL 20200** that WNTR drives. The two have **never been cross-validated** in
this project. Do not mix results from them.

A separate system Python **3.14** exists at `C:\Python314` and is not the project
interpreter.

---

## 10. Where to start reading the code

1. `CLAUDE.md` — the constitution. Read before touching anything.
2. `src\validation\p6_s3_prv_finechar.py` — how a measurement module is written
   here; copy `assert_solver` (line 117) and `service_nodes` (line 79).
3. `src\validation\p6_s4_pump_strategy.py` — the stepped-EPS loop the RL `step()`
   will be built on.
4. `src\validation\phase5_common.py` — shared unit conversions and working-copy
   construction.
5. `src\validation\run_all.py` — how the suite is driven and how verdicts are
   collected.
6. `docs\phase5_bwsn_preflight.md` §19 — the nine changes required before RL.
7. `docs\phase6_g5_g12_resolution.md` §7 and §16 — the action space and the pump
   decision.
