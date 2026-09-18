# MEMORY_BACKUP.md — persistent memory state

## 1. Memory system architecture

`DIRECT_OBSERVATION`. Claude Code's persistent memory lives in
`C:\Users\ABN\.claude\projects\<project-dir>/memory/` as individual `.md` files
with YAML frontmatter, indexed by `MEMORY.md`.

Three project directories exist under `~/.claude/projects/`:
- `C--Users-ABN/memory`
- `C--Users-ABN-Desktop/memory`
- `D--Thesis/memory`

All three were inspected on 2026-09-07 05:16 UTC. **All three are empty** — zero
files inside any `memory/` directory.

`DIRECT_OBSERVATION`. No `MEMORY.md` index file exists anywhere under
`~/.claude/` (searched to depth 4).

`DIRECT_OBSERVATION`. No user-level `CLAUDE.md` exists at `~/.claude/CLAUDE.md`
or `C:\Users\ABN\CLAUDE.md`.

`INFERENCE`. **No persistent memory has been written by any Claude Code session
in this project.** The memory system is available (the directories exist) but
unused.

---

## 2. What this means for migration

The absence of memory files is itself a finding: **there is no accumulated
session-to-session persistent memory to migrate.** Everything this project knows
lives in:

1. The codebase itself (`src/`, `data/`, `results/`, `.claude/`).
2. The four phase reports in `docs/`.
3. The 14 session transcripts under `session-backup/`.
4. The project `CLAUDE.md` (18 435 B, last modified 2026-08-23 23:03).
5. The four project Skills under `.claude/skills/`.
6. The three installed plugins (academic-research-skills, document-skills,
   superpowers).
7. The 42 PDFs in `papers/` (not in this backup).
8. The proposal and seminar PDFs at `proposal/proposal.pdf` and
   `seminar/seminar.pdf` (not in this backup, but their extracted text **is**:
   `session-backup/background-job-10b7b88f/txt/`).

No ephemeral or undocumented knowledge exists in a memory store.

---

## 3. Other memory-like stores inspected

`DIRECT_OBSERVATION`. The following directories under `~/.claude/` were inspected
for any memory-like content:

| Directory | File count | Contents |
|---|---|---|
| `backups/` | 5 | `.claude.json.backup.*` timestamp-named JSON backups of the main settings file |
| `cache/` | 1 | `changelog.md` only |
| `file-history/` | 0 | Empty |
| `jobs/` | 50 | One job dir `10b7b88f/` (background Phase 2 session, state `"failed"`, 129 326 tokens, `"reapedMidWorkAt"` 2026-08-26T20:38:36.404Z) with `state.json`, `timeline.jsonl` and `tmp/` containing 42 corpus `.txt` files (4.2 MB extracted text of the 42 PDFs, **NOT copied** — copyrighted third-party full text) plus 5 `txt/` files (proposal/seminar extractions, 672 KB, **copied** into `session-backup/background-job-10b7b88f/`) |
| `session-env/` | 0 | Empty |
| `sessions/` | 3 | Two `.key` files (session secrets, **NOT copied**) and one `9072.json` |
| `telemetry/` | 14 | `1p_failed_events.*` JSON files for session `32df42f5-06e0-4c73-91f0-0a6aea86fc15` (this session) |
| `downloads/` | 2 | `claude-2.1.241-win32-x64.exe` and its `.stderr` |
| `ide/` | 1 | `16000.lock` |
| `history.jsonl` | 1 file | 51 444 B, last modified 2026-09-06 23:27 |

`INFERENCE`. `history.jsonl` (51 KB) is the only file that might hold
session-spanning memory-like state. It was **not copied** because it may contain
secrets or sensitive data from unrelated sessions. A migrating agent should
inspect it manually if session history matters.

---

## 4. The background job `10b7b88f` — Phase 2

`VERIFIED_FACT`. Job `10b7b88f` corresponds to session
`10b7b88f-d1a5-4ce4-b370-a3813b0631ee`, launched 2026-08-26T18:45:51.589Z, cwd
`D:\Thesis`, model `opus[1m]`, effort `max`, permission mode `default`, cli
version `2.1.240`. State `"failed"`, final update 2026-08-28T23:21:59.876Z,
`"reapedMidWorkAt"` 2026-08-26T20:38:36.404Z. Token count 129 326.

`DIRECT_OBSERVATION` from `state.json` field `"detail"` (Persian text):

> منتظر دستور بعدی شما هستم. اگر بخواهید، Phase بعدی می‌تواند یکی از این‌ها
> باشد: `novelty-check` مستقل (برای بستن G8 و AD3)، بستن شکاف‌های G1/G3 با
> خواندن دستی صفحات مشخص‌شده، یا نوشتن محتوای این Phase در `docs/` پس از تأیید.

Translation: "I'm waiting for your next instruction. If you want, the next Phase
can be one of these: an independent `novelty-check` (to close G8 and AD3),
closing gaps G1/G3 by manually reading the specified pages, or writing this
Phase's content into `docs/` after approval."

`DIRECT_OBSERVATION` from `timeline.jsonl` first entry (truncated):

> تو اکنون وارد Phase 2 پروژه می‌شوی: # Methodology Review & Scientific Design
> هدف این Phase این است که بر اساس: - Proposal - Seminar Report - Research
> Corpus موجود - 42 منبع پژوهشی - یافته‌های Phase 1 Audit - یافته‌های Phase 1.5
> Literature Review - یافته‌های Phase 1.5-B Evidence Completion - و ادبیات علمی
> معتبر و به‌روز در صورت نیاز یک روش‌شناسی دقیق، علمی، قابل اجرا، قابل تکرار
> و قابل دفاع برای پروژه طراحی و ارزیابی کنی.

Translation (abbreviated): "You are now entering Phase 2 of the project:
Methodology Review & Scientific Design. The goal of this Phase is to design and
evaluate a precise, scientific, executable, reproducible and defensible
methodology for the project based on: Proposal, Seminar Report, the existing
Research Corpus of 42 sources, Phase 1 Audit findings, Phase 1.5 Literature
Review findings, Phase 1.5-B Evidence Completion findings, and credible
up-to-date scientific literature where necessary."

`INFERENCE`. This background job is **Phase 2**, which ran before Phase 4 (the
network decision, 2026-09-01) and before the current Phase 6 work. Its `tmp/`
directory holds:

- **42 extracted corpus `.txt` files** (4.2 MB) — full text of the 42 papers.
  **NOT copied** — copyrighted third-party material.
- **5 proposal/seminar `.txt` files** (672 KB) — the user's own documents.
  **Copied** into `session-backup/background-job-10b7b88f/txt/`:
  - `proposal.txt` (48 099 B, 0 Persian chars — English only)
  - `prop_raw.txt` (101 254 B, 39 008 Persian chars)
  - `prop_def.txt` (113 243 B, 39 008 Persian chars)
  - `seminar.txt` (101 588 B, 0 Persian chars)
  - `sem_def.txt` (297 335 B, 108 225 Persian chars)

The `*_def.txt` variants are the definitive extractions with Persian text intact.
The `proposal.txt` and `seminar.txt` variants appear to be English-only
post-processed versions or earlier attempts.

`INFERENCE`. The Phase 2 job's state is `"failed"`, but `"detail"` shows it
completed its work and was waiting for the user's next instruction — not a crash
or error, just idle. The `"reapedMidWorkAt"` timestamp suggests the daemon killed
it after ~2 hours of inactivity (18:45 launch → 20:38 reap).

---

## 5. Where the proposal and seminar constraints live

`VERIFIED_FACT`. The binding project constraints are:

1. **`proposal/proposal.pdf`** — the approved thesis proposal. **Not in this
   backup** (copyrighted binding document, left in place). Extracted text
   **is in the backup** as
   `session-backup/background-job-10b7b88f/txt/prop_def.txt` (113 KB, 39 008
   Persian chars).
2. **`seminar/seminar.pdf`** — the seminar report. **Not in this backup**
   (copyrighted binding document, left in place). Extracted text **is in the
   backup** as `session-backup/background-job-10b7b88f/txt/sem_def.txt` (297 KB,
   108 225 Persian chars).

`INFERENCE`. A migrating agent must read `prop_def.txt` and `sem_def.txt` to
understand the approved project scope, objectives, research questions, hypotheses,
methodology, and advisor expectations. The PDFs themselves are at
`D:\Thesis\proposal\proposal.pdf` and `D:\Thesis\seminar\seminar.pdf` on the
original machine.

---

## 6. What was NOT found, and where it was searched

`DIRECT_OBSERVATION`. The following were searched and found absent:

- No `MEMORY.md` index anywhere under `~/.claude/` (depth 4 search).
- No user-level `CLAUDE.md` at `~/.claude/CLAUDE.md` or `C:\Users\ABN\CLAUDE.md`.
- No `.memory` or `*memory*` or `*knowledge*` files anywhere under `~/.claude/`
  except the three empty `projects/*/memory/` directories.
- No `todos/` directory entries (on 2026-09-07 the directory existed but was
  empty, `ls -1 todos | wc -l` → 0; on a re-check 2026-09-18 the directory no
  longer exists at all — Claude Code appears to remove it when empty).
- No files in `file-history/` or `session-env/`.

`INFERENCE`. There is no hidden or undiscovered memory store. The backup is
complete with respect to persistent memory: **none exists.**

---

## 7. Instruction to the next agent

Three findings:

1. **No persistent memory exists.** The memory system is available but unused.
   Everything the project knows lives in the codebase, the four phase reports,
   the 14 session transcripts, the project `CLAUDE.md`, the four project Skills,
   the three installed plugins, and the 42 local PDFs (not in this backup).
2. **The proposal and seminar text extractions are in the backup** at
   `session-backup/background-job-10b7b88f/txt/prop_def.txt` and
   `sem_def.txt`. Read those to understand the approved project scope.
3. **`history.jsonl` (51 KB) was not copied** because it may contain secrets or
   sensitive data from unrelated sessions. Inspect it manually if
   session-spanning command history matters.

If the migrating agent needs to reconstruct the project's accumulated knowledge,
the complete sources are:

- This backup (`docs/ai-knowledge/`).
- The 14 session transcripts in `session-backup/`.
- The project `CLAUDE.md` (`config-backup/project-CLAUDE.md`).
- The four phase reports (`docs/phase4_decision_report.md`,
  `phase4_network_evidence.md`, `phase5_bwsn_preflight.md`,
  `phase6_g5_g12_resolution.md`).
- The proposal/seminar text extractions in
  `session-backup/background-job-10b7b88f/txt/`.
- The 42 PDFs in `papers/` on the original machine (filenames indexed in
  `LITERATURE.md` §2).

No ephemeral or undocumented knowledge was lost.
