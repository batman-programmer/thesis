# MISSING_OR_UNRECOVERABLE.md — what is absent, truncated, or excluded, and why

**Governing rule (PART Y of the backup request):**

> "Document what is missing or could not be recovered … **Do not hide missing
> information.**"

This file is the honest ledger of every gap in the backup. Three categories are
distinguished: **UNRECOVERABLE** (existed, cannot be reconstructed), **EXCLUDED
BY CHOICE** (exists, deliberately not copied — with the reason), and **NEVER
EXISTED** (a thing a migrating agent might expect but which was never created).
Classification tags follow PART C. Every size and count below was re-verified on
disk 2026-09-26 unless marked otherwise.

---

## 1. Persistent memory — NEVER EXISTED (four empty stores)

`DIRECT_OBSERVATION`. There is **no persistent agent memory anywhere**, in either
Claude Code or Claude Desktop. Verified 2026-09-26:

| Store | Path | Files |
|---|---|---|
| Code, project | `C:\Users\ABN\.claude\projects\D--Thesis\memory\` | **0** |
| Code, home | `C:\Users\ABN\.claude\projects\C--Users-ABN\memory\` | **0** |
| Code, desktop | `C:\Users\ABN\.claude\projects\C--Users-ABN-Desktop\memory\` | **0** |
| Desktop 3p | `Claude-3p\…\<session>\memory\memory\` | **0** (see [MCP_AND_INTEGRATIONS.md](MCP_AND_INTEGRATIONS.md) §6) |

`DIRECT_OBSERVATION`. **No `MEMORY.md` exists anywhere under `~/.claude`**
(`find … -iname MEMORY.md` → empty). See [MEMORY_BACKUP.md](MEMORY_BACKUP.md).

`INFERENCE`. Nothing was lost here — the project simply never used file-based
memory. All durable knowledge lives in `docs/` and this backup. A migrating
agent should **not** search for a memory export; there is none to find.

---

## 2. The prompt record stops at Phase 4 — PARTIAL GAP

`DIRECT_OBSERVATION`. `session-backup/prompt-history--D--Thesis.jsonl` (98
entries) and the live `~/.claude/history.jsonl` (51 727 B as of 2026-09-18
02:50) contain **no task prompt after 2026-09-01 22:58 local**. Everything later
is slash commands only.

`OPEN_QUESTION`. **The Phase 5, Phase 6, and backup-request briefs are absent
from `history.jsonl`.** They were unquestionably sent — the work exists — but the
prompt store does not hold them. Why was not determined. See
[PROMPTS_AND_WORKFLOWS.md](PROMPTS_AND_WORKFLOWS.md) §6.1.

`DIRECT_OBSERVATION`. **Recovery path:** those briefs survive only in the
transcript `session-backup/claude-code-transcripts--D--Thesis/32df42f5-06e0-4c73-91f0-0a6aea86fc15.jsonl`
(12.4 MB) and in the human-readable `/export` file
`session-backup/2026-09-06-232706-…txt` (124 794 B). Grep the transcript; do not
read it linearly. **A migrating agent must not treat the 40 task prompts in
`history.jsonl` as the complete set of instructions given to this project.**

## 3. Three head-truncated phase-brief files — PARTIAL LOSS

`DIRECT_OBSERVATION`. Three of the ten paste-cache files begin mid-sentence,
verified 2026-09-26 by reading their first bytes:

| File | First characters | Phase |
|---|---|---|
| `paste-cache/bd95a48af8c554d8.txt` | *"een completed.  Your job now is to convert the exi…"* | Phase 3 rewrite |
| `paste-cache/d0720659c2ef2862.txt` | *"ssure control in water distribution networks using…"* | methodology inheritance |
| `paste-cache/d8f25a13d721f88a.txt` | *"حمایت نکن.  هدف این فاز این ا…"* | Phase 4 network re-review |

`INFERENCE`. The paste-cache stores only the portion of a paste above the inline
threshold; the **head of each is in the corresponding transcript**. The body of
each file is intact — only the opening lines are clipped. A migrating agent that
needs the full text of these three should recover the heads from transcript
`32df42f5`. The other seven paste-cache files are complete.

---

## 4. Phases 1, 1.5, 1.5-B, 2, 3 have no report in `docs/` — NEVER WRITTEN

`DIRECT_OBSERVATION`. Only Phases 4, 5 (and this Phase 6, in progress) produced
persisted reports. For Phases 1 → 3 the **phase-brief files plus the session
transcripts are the only surviving specification** of what was asked and done.

`DIRECT_OBSERVATION`. The Phase 2 background job explicitly offered *"writing
this Phase's content into `docs/` after approval"* as its closing option —
**that option was never taken** (see
[PROMPTS_AND_WORKFLOWS.md](PROMPTS_AND_WORKFLOWS.md) §7). This is why Phase 2 has
no report despite substantial completed work (42-source text extraction, the
Jowitt & Xu evidence, the methodology design).

`OPEN_QUESTION`. Per-paper reading notes from the Phase 1.5 / 1.5-B literature
review **survive only inside transcripts**, not as standalone files. The
`docs/` §18 files the constitution names (`research_questions.md`,
`assumptions.md`, `novelty.md`, `open_questions.md`, …) exist as **six zero-byte
stubs**; their intended content lives in this `docs/ai-knowledge/` backup
instead.

---

## 5. Source artefacts not copied — EXCLUDED BY CHOICE (text IS preserved)

`DIRECT_OBSERVATION`. The two governing source documents were **not copied as
PDFs**, but their **extracted plain text IS in the backup**:

| Source PDF (on disk, not copied) | Size | Extracted text (in backup) | Size |
|---|---|---|---|
| `D:\Thesis\proposal\proposal.pdf` | 952 351 B | `session-backup/background-job-10b7b88f/txt/prop_def.txt` | 113 243 B |
| `D:\Thesis\seminar\seminar.pdf` | 3 620 347 B | `session-backup/background-job-10b7b88f/txt/sem_def.txt` | 297 335 B |

`INFERENCE`. The PDFs remain in the working project untouched (the backup rule
forbids modifying the project), so nothing is lost — the text is portable and
the binaries are one directory away. A migrating agent needing the figures or
exact layout must open the original PDFs; for all textual content, use the two
`.txt` extractions.

## 6. Large data excluded by size/copyright choice — EXCLUDED BY CHOICE

`DIRECT_OBSERVATION`. These exist in the working project and were deliberately
**not** copied into the backup, for size or copyright reasons. All remain in
place; none is destroyed.

| Item | Size / count | Why excluded |
|---|---|---|
| `results/phase5/_tmp` | 459 MB / 3963 files | transient solver scratch; regenerable |
| `.venv` | large | reconstructable from pinned versions (see [CLAUDE_ENVIRONMENT.md](CLAUDE_ENVIRONMENT.md)) |
| `papers/` | 42 PDFs | copyrighted source literature; cited in [LITERATURE.md](LITERATURE.md) |
| `jobs/10b7b88f/tmp/corpus/` | 4.2 MB | copyrighted extracted corpus text |
| ARS plugin `evals/` | ~15 MB | third-party plugin test fixtures; not project data |
| ARS `.in_use` marker | tiny | runtime lock, not content |

`INFERENCE`. The 42 PDFs are the one exclusion a migrating agent cannot
regenerate without the user: the papers must be re-supplied on the new machine.
Their bibliographic identity is preserved in [LITERATURE.md](LITERATURE.md); the
**filename → citation mapping for all 42 was never built** (see §9).

---

## 7. Secret-risk files not copied — EXCLUDED BY CHOICE (precaution)

`DIRECT_OBSERVATION`. `~/.claude/history.jsonl` (51 727 B) is **not a keystore**,
but it may echo secrets typed into prompts from unrelated sessions on this
machine. It was excluded on precaution. The project-scoped prompt subset that
matters — the 98 `D:\Thesis` entries — was extracted into
`session-backup/prompt-history--D--Thesis.jsonl` without carrying the whole
cross-project store.

---

## 8. Secrets located and deliberately left unexported — BY DESIGN

`DIRECT_OBSERVATION`. Every credential found on disk was left in place and
recorded as **`SECRET PRESENT — NOT EXPORTED`**. The full enumeration is in
[MCP_AND_INTEGRATIONS.md](MCP_AND_INTEGRATIONS.md) §7: daemon `control.key` /
`pipe.key`, session `*.key` files, `userID` / `machineID` in `~/.claude.json`
and its 5 backups, Roaming `config.json` `oauth:` token caches, `Claude-3p`
per-session secrets / OIDC bootstrap / host-creds, the two `.audit-key` files,
and the `device_id_salt` in both installs' `Preferences`.

`DIRECT_OBSERVATION`. The single in-file redaction is documented inside
`config-backup/desktop-roaming--config.REDACTED.json` under its own
`_backup_note`, which names the exact three keys replaced. **No token, key,
cookie or credential was copied into this backup.**

`INFERENCE`. **Every credential must be re-issued by the user on the new
machine.** Nothing in this list travels with the backup, by design.

## 9. Located but NOT inspected / NOT diffed — HONEST LIMITATION

`DIRECT_OBSERVATION`, stated per the rule *"Do not claim to have inspected files
that you did not actually inspect."*

- **Two subagent task-output files** under
  `AppData\Local\Temp\claude\…\tasks\` were located but **neither copied nor
  opened**. Their content is unknown; they may duplicate transcript material or
  be empty. A migrating agent may inspect them if subagent output matters.
- **Two `.pre-import` files** were found but **never diffed** against their
  imported counterparts, so whether the import changed anything is unverified.
- **The `filename → citation` mapping for the 42 PDFs was never built.**
  [LITERATURE.md](LITERATURE.md) records the citations; matching each to its
  exact PDF filename on disk remains undone.

---

## 10. Not portable to another environment — STRUCTURAL

`DIRECT_OBSERVATION`.

- **`D:\Thesis\.claude\settings.local.json`** holds ~149 `permissions.allow`
  entries. These are **Claude-Code-specific permission grants** and do **not**
  port to another harness; a migrating agent will re-grant its own permissions.
- **Claude Code's built-in tools and system prompt are not exportable** — they
  are the harness, not project files. The functional equivalents that mattered
  were `Bash`, `Read`/`Write`/`Edit`/`Grep`/`Glob`, `WebSearch`, `WebFetch`
  (see [MCP_AND_INTEGRATIONS.md](MCP_AND_INTEGRATIONS.md) §4). Remap by
  capability, not by name.
- **The five Skill storage systems and two plugin systems** are described in
  [SKILLS_INDEX.md](SKILLS_INDEX.md) / [PLUGINS_INDEX.md](PLUGINS_INDEX.md); the
  ARS `skills/` symlink directory was checked out on Windows as **plain text
  files containing target paths** (no symlink support), so those Skill bodies
  are recoverable only via the plugin cache, not the broken symlinks.

---

## 11. Carried-over research debts — UNRESOLVED (not lost, not yet done)

`UNRESOLVED`. Two corrections owed since Phase 4, still open:

1. **Hu MARL mis-citation** — the proposal cites Hu et al.'s MARL paper
   incorrectly; the correct target is *Water Supply* **23(7):2833**,
   doi **10.2166/ws.2023.163**. The proposal PDF has not been edited.
2. **Negm Table 5-4** — must be **re-verified directly from the PDF** before any
   thesis citation; the value was flagged as needing first-hand confirmation and
   that confirmation is not yet recorded.

`UNRESOLVED`. **EPyT 2.3.5.2 / EPANET 2.3.05 was never cross-validated** against
the WNTR-bundled EPANET 20200. The two engines are installed side by side; no
run has compared them. Any claim of engine-agnostic results is currently
unsupported.

---

## 12. Summary — the one-glance gap table

| Gap | Category | Recoverable? |
|---|---|---|
| Persistent memory | NEVER EXISTED | N/A — none was ever used |
| Phase 5/6/backup briefs absent from history.jsonl | PARTIAL GAP | Yes — transcript `32df42f5` + `/export` .txt |
| 3 head-truncated paste-cache files | PARTIAL LOSS | Heads only, from the transcript |
| Phase 1–3 reports | NEVER WRITTEN | Only via briefs + transcripts |
| proposal/seminar PDFs | EXCLUDED (text kept) | Yes — `.txt` in backup; PDFs in project |
| 42 paper PDFs, corpus, `_tmp`, `.venv` | EXCLUDED BY CHOICE | Papers need re-supply; rest regenerable |
| All secrets | BY DESIGN | Re-issue on new machine |
| 2 task-output + 2 `.pre-import` files | NOT INSPECTED | Present on disk if needed |
| filename→citation map (42 PDFs) | NEVER BUILT | Must be built |
| settings.local.json allow-list | NOT PORTABLE | Re-grant per harness |
| Hu citation, Negm table, EPyT cross-val | UNRESOLVED | Open research tasks |

`INFERENCE`. Nothing in this file is **hidden**; nothing critical is
**unrecoverable**. The only items a migrating agent cannot reconstruct alone are
the 42 copyrighted PDFs and the re-issued credentials — both require the user.
