# INDEX — Portable AI Knowledge Backup

**Backup root:** `D:\Thesis\docs\ai-knowledge\`
**Created:** 2026-09-07
**Created by:** Claude Code (Claude Opus 5, client 2.1.255) working in `D:\Thesis`
**Purpose:** a complete, loss-minimised, portable handoff package so that a
*different* AI agent or environment (OpenClaw, GPT, Gemini, DeepSeek, GLM, a
future Claude, or a human) can continue this Master's thesis project without
manual reconstruction.

This is **not a summary of a conversation**. It is a preservation package: real
artefacts copied verbatim, plus authored index/knowledge documents that explain
them.

---

## Read this first

1. **[AI_HANDOFF.md](AI_HANDOFF.md)** — the single most important
   human-readable file. Start here, always.
2. **[PROJECT_CONTEXT.md](PROJECT_CONTEXT.md)** — what the project is, the
   research questions, the full locked technical specification.
3. **[PROJECT_STATE.yaml](PROJECT_STATE.yaml)** — the same state in
   machine-readable form.
4. **[ROADMAP.md](ROADMAP.md)** — what to do next.

Then, as needed: DECISIONS.md, FINDINGS.md, EXPERIMENTS.md,
FAILED_APPROACHES.md, CODEBASE_MAP.md.

---

## Every file in this backup root

### Authored knowledge documents (20)

| File | What it holds |
|---|---|
| [INDEX.md](INDEX.md) | This file. Map of the backup. |
| [AI_HANDOFF.md](AI_HANDOFF.md) | Highest-priority handoff briefing. What is established, what is assumed, what must not be revisited. |
| [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) | Thesis purpose, research questions, hypotheses, scope, methodology, architecture, full locked configuration with exact values. |
| [PROJECT_STATE.yaml](PROJECT_STATE.yaml) | Valid YAML state snapshot: status, phase, objectives, decisions, findings, experiments, risks, next steps. |
| [DECISIONS.md](DECISIONS.md) | Every meaningful decision with context, reason, alternatives, why rejected, evidence, consequences, status. |
| [FINDINGS.md](FINDINGS.md) | All findings with evidence, source, confidence, validation status, implications. |
| [EXPERIMENTS.md](EXPERIMENTS.md) | Every experiment run, partial or planned, with exact numerical results and reproduction commands. |
| [FAILED_APPROACHES.md](FAILED_APPROACHES.md) | What was tried and failed, and **why** — so the next agent does not repeat it. |
| [ROADMAP.md](ROADMAP.md) | Completed / active / blocked / pending work, priorities, dependencies. |
| [CODEBASE_MAP.md](CODEBASE_MAP.md) | Actual filesystem inventory of `D:\Thesis`, module by module. |
| [LITERATURE.md](LITERATURE.md) | The local research corpus and the externally verified citations. |
| [MEMORY_BACKUP.md](MEMORY_BACKUP.md) | All accessible persistent memory (and the verified fact that it is empty). |
| [SESSION_HISTORY.md](SESSION_HISTORY.md) | Index of every conversation transcript, with pointers into `session-backup/`. |
| [CLAUDE_ENVIRONMENT.md](CLAUDE_ENVIRONMENT.md) | Claude Code + Claude Desktop configuration, exactly as inspected. |
| [SKILLS_INDEX.md](SKILLS_INDEX.md) | Every Skill found anywhere on the machine, with portability assessment. |
| [PLUGINS_INDEX.md](PLUGINS_INDEX.md) | Every plugin/bundle found, with what was copied. |
| [MCP_AND_INTEGRATIONS.md](MCP_AND_INTEGRATIONS.md) | MCP servers and integrations. Secrets excluded by policy. |
| [PROMPTS_AND_WORKFLOWS.md](PROMPTS_AND_WORKFLOWS.md) | The actual phase-launch prompts, slash commands, hooks, agents, workflows. |
| [USER_PROJECT_CONTEXT.md](USER_PROJECT_CONTEXT.md) | How the user wants this project handled. Working conventions. |
| [MISSING_OR_UNRECOVERABLE.md](MISSING_OR_UNRECOVERABLE.md) | Everything that could **not** be backed up, why, and how to recover it. |

### Copied-artefact directories (9)

| Directory | Contents | Size |
|---|---|---|
| `skills-backup/` | 4 project skills + 11 Claude Desktop skills, verbatim | 4.1 MB |
| `plugins-backup/` | 5 full plugin source trees, verbatim | 52 MB |
| `mcp-backup/` | The 2 `.mcp.json` files that exist on the machine | 5 KB |
| `commands-backup/` | 20 slash-command definition files | 54 KB |
| `hooks-backup/` | Both plugins' hook configs **and** their hook scripts | 35 KB |
| `agents-backup/` | 45 agent/subagent definition files (42 under academic-research-skills `agents/`, 3 document-skills skill-creator) | 1.2 MB |
| `session-backup/` | 14 thesis Claude Code transcripts + 5 non-thesis Code transcripts, 2 Claude Desktop transcripts (+ their audit logs), 10 paste-cache prompts, 98-entry prompt history, 2 root `.txt` transcripts | 23.0 MB |
| `config-backup/` | 11 configuration files (1 redacted) **plus** a 4-file Desktop usage-ledger | 58 KB |
| `_backup_tools/` | `mk_session_aux.py` — the script that generated two of the session-backup files, kept so extraction is reproducible not asserted | 3 KB |

**Total: 672 directories (including the backup root), 2 919 files, ~75 MB.**
Re-measured 2026-09-26 after the 5 non-thesis Code transcripts were copied in
(exact: 78 626 331 bytes).

---

## Evidence-label convention used throughout

Every non-trivial statement in these documents carries exactly one label. This
convention is mandated by the user and is not decorative.

| Label | Meaning |
|---|---|
| `VERIFIED_FACT` | Measured by running code, or read directly from a file on this machine. |
| `USER_PROVIDED` | Stated by the researcher. Authoritative as intent, not as physics. |
| `DIRECT_OBSERVATION` | Observed on the filesystem / in tool output during backup. |
| `DECISION` | A choice made and recorded. Has a rationale. |
| `ASSUMPTION` | Believed, load-bearing, not yet measured. |
| `HYPOTHESIS` | To be tested by a future experiment. |
| `INFERENCE` | Reasoned from evidence. Weaker than `VERIFIED_FACT`. |
| `OPEN_QUESTION` | Known unknown. |
| `UNRESOLVED` | Known problem without a chosen fix. |
| `FAILED_APPROACH` | Tried; did not work; reason recorded. |
| `COMPLETED` | Finished and verified. |
| `PLANNED` | Intended, not started. |
| `PROVISIONAL` | In place but expected to change. |

The project's own internal reports (`docs/phase*.md`) use a parallel four-label
scheme mandated by the Phase 6 brief — `VALIDATED FACT`, `ENGINEERING DECISION`,
`RESEARCH ASSUMPTION`, `HYPOTHESIS TO TEST`. Where this backup quotes those
reports, the original label is preserved verbatim. The two schemes map as:
`VALIDATED FACT` → `VERIFIED_FACT`, `ENGINEERING DECISION` → `DECISION`,
`RESEARCH ASSUMPTION` → `ASSUMPTION`, `HYPOTHESIS TO TEST` → `HYPOTHESIS`.

---

## What is NOT in this backup

Fully enumerated with reasons in
[MISSING_OR_UNRECOVERABLE.md](MISSING_OR_UNRECOVERABLE.md). Summary:

- **Secrets.** Deliberately excluded by policy. Recorded as `SECRET PRESENT —
  NOT EXPORTED`. A whole-backup scan for `sk-ant-`, `ghp_`, `xox[baprs]-`,
  `AKIA` and PEM private-key headers returned **zero matches**.
- **`.venv/`** — reconstructible from the exact pinned package list in
  CLAUDE_ENVIRONMENT.md.
- **`papers/`** (42 PDFs, copyrighted) — indexed by exact filename in
  LITERATURE.md, files left in place at `D:\Thesis\papers\`.
- **`results/phase5/_tmp/`** (459 MB, 3963 EPANET scratch files) —
  regenerable by rerunning the validation modules.
- **ARS plugin `evals/`** (15 MB of eval logs) — not project knowledge.
- **Claude Code's own built-in tools and system prompt** — not files, cannot be
  exported.
