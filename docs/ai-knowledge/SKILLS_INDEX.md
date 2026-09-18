# SKILLS_INDEX.md — complete Skills inventory

**Governing rule (PART M of the backup request):**

> "DO NOT replace actual Skill files with summaries."

Every Skill listed here exists as its **original file** in this backup. This
document is a finding aid over those files, not a substitute for them.

**Counts, verified on disk 2026-09-18:**

| Location in backup | SKILL.md files | Total files | Size |
|---|---|---|---|
| `skills-backup/project-skills/` | **4** | 4 | 62 KB |
| `skills-backup/codex-agents-skills/` | **4** | 4 | 62 KB |
| `skills-backup/claude-desktop-skills/anthropic-skills/` | **11** | 208 | 4.0 MB |
| `skills-backup/plugin-provided-skills/` | 0 | 0 | — (empty by design, see §6) |
| `plugins-backup/` (inside plugin sources) | **69** | — | — |
| **TOTAL** | **88** | — | — |

Breakdown of the 69 plugin-provided, each count measured with
`find … -name SKILL.md | wc -l`:

| Plugin | SKILL.md |
|---|---|
| `academic-research-skills-3.21.1` | 4 |
| `document-skills-41bbe19d1a1a` | 20 (19 skills + 1 `template/`) |
| `document-skills-53048666b05b-ORPHANED` | 20 (19 skills + 1 `template/`) |
| `superpowers-6.3.0` | 14 |
| `claude-desktop-remote-plugins` | 11 (1 pdf-viewer + 10 engineering) |
| **Sum** | **69** |

---

## 1. Taxonomy — the five distinct Skill systems on this machine

`DIRECT_OBSERVATION`. Skills reach an agent on this machine through **five
independent mechanisms with different storage layouts**. A migrating agent must
not conflate them.

| # | System | Storage layout | Loaded by |
|---|---|---|---|
| 1 | **Project Skills** | `D:\Thesis\.claude\skills\<name>\SKILL.md` | Claude Code, this project only |
| 2 | **Codex Skills** (new) | `D:\Thesis\.agents\skills\<name>\SKILL.md` | Codex — **not** Claude Code |
| 3 | **Claude Code plugin Skills** | `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/skills/<name>/SKILL.md` | Claude Code, all projects |
| 4 | **Claude Desktop Skills** | `local-agent-mode-sessions/skills-plugin/<org>/<account>/anthropic-skills/skills/<name>/SKILL.md` | Claude Desktop only |
| 5 | **Claude Desktop remote plugins** | `rpm/plugin_<id>/skills/<name>/SKILL.md` | Claude Desktop only |

`DIRECT_OBSERVATION`. Claude Desktop's layout (#4, #5) is **not** the same as
Claude Code's (#3) — the PART N instruction not to assume they are identical is
borne out by the filesystem.

---

## 2. The four PROJECT Skills — the ones that matter for this thesis

`VERIFIED_FACT`. Original path `D:\Thesis\.claude\skills\<name>\SKILL.md`. One
file per skill, no scripts, no references, no assets. Copied byte-for-byte to
`skills-backup/project-skills/`.

Source: **project-local**, written by the user (or with the user) before the
first session. Not third-party, not Claude-provided.

### 2.1 `research-review` — 16 850 B, modified 2026-08-24 23:30

Frontmatter `description` (verbatim):

> Perform rigorous, evidence-based literature review for research-impacting
> questions and decisions. Use the project's local research corpus first,
> including the approved proposal and seminar report, then perform external
> up-to-date research when needed. Protect the approved project scope while
> actively detecting scientific errors, overlooked concepts, contradictory
> evidence, recent work, and novelty risks. Do not silently change the research
> direction.

**Trigger conditions:** research-impacting literature questions.
**Dependencies:** `papers/`, `proposal/proposal.pdf`, `seminar/seminar.pdf`,
`CLAUDE.md`. **Tools referenced:** WebSearch, WebFetch, file reads.
**Claude-specific assumptions:** names `CLAUDE.md` at line 64 (the Codex copy
says `AGENTS.md`); otherwise harness-neutral.
**Portability: HIGH** — plain Markdown reasoning protocol, directly reusable by
any agent.

`VERIFIED_FACT`. **This is the only Skill in the entire project that was ever
formally invoked.** `~/.claude.json` → `skillUsage.research-review.usageCount = 1`,
`lastUsedAt = 1787608726842`, in session `a4cbf1ac` (Phase 1.5). Its invocation
is visible in that transcript as the preamble
`Base directory for this skill: D:\Thesis\.claude\skills\research-review`.

`INFERENCE`. Its mtime (2026-08-24 23:30) falls 17 minutes after session
`a4cbf1ac` ended (23:13) — it was **edited immediately after first use**, i.e.
refined in light of how it actually performed.

### 2.2 `methodology-review` — 15 772 B, modified 2026-08-23 22:28

> Review the scientific and methodological soundness of project decisions while
> preserving the approved scope and direction defined by the proposal and
> seminar report. Use when evaluating or changing methodology, assumptions,
> state/observation, action space, reward/objective, model design, experiment
> design, simulator configuration, baselines, metrics, training protocol, or any
> other decision that can affect scientific validity.

**Portability: HIGH.** `usageCount`: **absent — never formally invoked.**

### 2.3 `novelty-check` — 15 037 B, modified 2026-08-23 22:28

> Evaluate the novelty and contribution of ideas, methods, designs, experiments,
> and claims within the approved scope of the thesis/project. Compare the
> proposal and seminar report with the project's actual implementation and with
> relevant local and current external literature. Detect duplicate or closely
> overlapping work, weak novelty claims, mistaken assumptions, and missed
> adjacent research. Never declare novelty with unjustified certainty and never
> silently change the approved project scope.

**Portability: HIGH.** `usageCount`: **absent — never formally invoked.**

`DIRECT_OBSERVATION`. The Phase 2 background job's hand-back message explicitly
proposed running this Skill — *"`novelty-check` مستقل (برای بستن G8 و AD3)"*
("an independent `novelty-check`, to close G8 and AD3"). It was never run. The
N1–N16 novelty audit in `docs/phase4_decision_report.md` was produced by the
main instance instead. See [LITERATURE.md](LITERATURE.md) §4.

### 2.4 `change-impact` — 14 039 B, modified 2026-08-23 22:29

> Analyze the technical, methodological, experimental, proposal/scope,
> literature, novelty, reproducibility, and thesis consequences of a proposed
> change before implementation. Use whenever a change may affect research
> validity, approved scope, assumptions, experiments, results, metrics,
> conclusions, or contribution claims.

**Portability: HIGH.** `usageCount`: **absent — never formally invoked.**

### 2.5 The finding that matters

`VERIFIED_FACT`. `CLAUDE.md` §15 names all four as "expected research-control
capabilities". `skillUsage` records **one invocation of one of them.**

`INFERENCE`. The four Skills functioned as **written doctrine rather than
executed tooling** — their content shaped the work by being read as project
context (they are loaded into every session's skill listing), not by being
dispatched. A migrating agent should treat them as **required reading**, not as
callable functions. This is why they port at HIGH fidelity: nothing about them
depends on the Skill dispatch mechanism.

---

## 3. The four CODEX Skills — evidence of an in-progress migration ⚠

`DIRECT_OBSERVATION`. `D:\Thesis\.agents\skills\` created **2026-09-18 03:09**,
holding copies of all four project Skills. Copied to
`skills-backup/codex-agents-skills/`.

`VERIFIED_FACT`, by `diff`:

| Skill | Difference from `.claude/skills/` original |
|---|---|
| `change-impact` | **byte-identical** |
| `methodology-review` | **byte-identical** |
| `novelty-check` | **byte-identical** |
| `research-review` | **one line** — line 64, `` `CLAUDE.md` `` → `` `AGENTS.md` `` |

`INFERENCE`. Someone has already begun porting this project to Codex, and the
port consists of exactly: `CLAUDE.md` → `AGENTS.md` (4 lines changed) plus
`.claude/skills/` → `.agents/skills/` (1 line changed). **Nothing else has been
ported** — no settings, no allow-list, no plugin, no transcript.

`OPEN_QUESTION`. Provenance and completeness unverified. Confirm with the user
before treating `.agents/` as authoritative. See
[CLAUDE_ENVIRONMENT.md](CLAUDE_ENVIRONMENT.md) §2.2.

`INFERENCE`. **This is strong practical evidence for the portability claims in
this document**: the four project Skills required a five-line diff to move to a
different vendor's harness.

---

## 4. Claude Desktop Skills — `anthropic-skills` v1.0.0

`DIRECT_OBSERVATION`. 11 Skills, 208 files, 4.0 MB. Origin: **Claude-provided /
Anthropic-authored**, delivered through Claude Desktop's skills-plugin store —
**not** installed by the user from a marketplace and **not** visible to Claude
Code. Copied in full (including `.claude-plugin/` manifest) to
`skills-backup/claude-desktop-skills/anthropic-skills/`.

| Skill | Bytes | Licence | Purpose (from frontmatter) |
|---|---|---|---|
| `consolidate-memory` | 1 983 | — | "Reflective pass over your memory files — merge duplicates, fix stale facts, prune the index." |
| `docx` | 7 079 | **Proprietary** | Create/read/edit Word `.docx`/`.dotx` |
| `explain-usage` | 1 384 | — | "Explain where this session's tokens went" |
| `import-memory` | 10 689 | — | "Import a memory export from another AI assistant into Claude's memory" |
| `morning` | 18 163 | — | Render a morning brief as a styled HTML artifact |
| `pdf` | 8 072 | **Proprietary** | All PDF operations incl. OCR, forms, merge/split |
| `pptx` | 21 574 | **Proprietary** | Create/read/edit PowerPoint `.pptx`/`.potx` |
| `schedule` | 2 399 | — | Create/update scheduled tasks |
| `setup-cowork` | 12 029 | — | Guided Cowork setup |
| `skill-creator` | 33 351 | — | Create, modify, eval and benchmark Skills |
| `xlsx` | 8 598 | **Proprietary** | Create/read/edit spreadsheets |

`DIRECT_OBSERVATION`. Four carry the frontmatter line
`license: Proprietary. LICENSE.txt has complete terms` — `docx`, `pdf`, `pptx`,
`xlsx`. **Portability: LEGALLY RESTRICTED.** They are physically in the backup
because they were physically on disk and the instruction was preservation, but
**do not redistribute them to a third-party harness.** The other seven carry no
licence line.

`DIRECT_OBSERVATION`. `skillUsage` records
`anthropic-skills:consolidate-memory` with `usageCount = 1`,
`lastUsedAt = 1788717822920`. `INFERENCE`: someone ran the memory-consolidation
Skill once — which is consistent with the finding in
[MEMORY_BACKUP.md](MEMORY_BACKUP.md) that all three `memory/` directories are
**empty**: the consolidation ran and found nothing to consolidate, or was run in
a Desktop context whose memory store is separate.

`INFERENCE`. **Two of these are directly relevant to the migration task itself**:
`import-memory` ("Import a memory export from another AI assistant… treated as
data") and `consolidate-memory`. If the destination is another Claude surface,
`import-memory` is the intended mechanism for ingesting
[MEMORY_BACKUP.md](MEMORY_BACKUP.md).

`DIRECT_OBSERVATION`. **None of these 11 was used for any scientific work in this
project.** No `.docx`, `.pptx` or `.xlsx` deliverable exists anywhere in
`D:\Thesis`; every project document is Markdown.

---

## 5. Plugin-provided Skills — 69 files

Full plugin detail in [PLUGINS_INDEX.md](PLUGINS_INDEX.md). Skill-level summary:

### 5.1 academic-research-skills 3.21.1 — 4 top-level Skills

`plugins-backup/academic-research-skills-3.21.1/`

| Skill | Nested agents |
|---|---|
| `academic-paper` | 12 |
| `academic-paper-reviewer` | 7 |
| `academic-pipeline` | 5 |
| `deep-research` | 14 |

Plus a `shared/agents/compliance_agent.md` and 3 top-level agents. 16 slash
commands (`/ars-*`). **Most-used plugin on the machine** —
`pluginUsage: academic-research-skills@inline = 214`,
`@academic-research-skills = 90`.

`DIRECT_OBSERVATION`. Despite those counters, **no ARS slash command appears in
the 98-entry prompt history** and no ARS subagent produced a surviving artefact.
`INFERENCE`: the counts reflect the SessionStart hook loading the plugin on every
startup, not deliberate use.

`DIRECT_OBSERVATION` — **the `skills/` directory is broken on this machine.**
`academic-research-skills-3.21.1/skills/` contains four *plain files* of 17, 26,
20 and 16 bytes whose entire content is the text `../academic-paper`,
`../academic-paper-reviewer`, `../academic-pipeline`, `../deep-research`. These
are Git symlinks that were checked out on Windows **without symlink support**, so
they became text files containing their target path. The same is true of the live
install at
`~/.claude/plugins/cache/academic-research-skills/academic-research-skills/3.21.1/skills/`
— this is not a copying artefact of the backup. The four real `SKILL.md` files
live one level up, at `academic-paper/SKILL.md`, `academic-paper-reviewer/SKILL.md`,
`academic-pipeline/SKILL.md` and `deep-research/SKILL.md`, and those are intact.

`INFERENCE`, **unverified**: if Claude Code discovers plugin skills by scanning
`<plugin>/skills/*/SKILL.md`, these four would not resolve, which would explain
why no ARS skill ever appears in `skillUsage` despite the plugin being loaded 214
times. Not proven — the loader's behaviour was not tested. Recorded because a
migrating agent that re-installs ARS on a POSIX machine may see different
behaviour from what this project saw.

**Portability: MEDIUM.** The Skill and agent bodies are Markdown and port; the
`/ars-*` dispatch and the `${CLAUDE_PLUGIN_ROOT}` hooks do not.

### 5.2 superpowers 6.3.0 — 14 Skills

`plugins-backup/superpowers-6.3.0/skills/`: `brainstorming`,
`dispatching-parallel-agents`, `executing-plans`,
`finishing-a-development-branch`, `receiving-code-review`,
`requesting-code-review`, `subagent-driven-development`, `systematic-debugging`,
`test-driven-development`, `using-git-worktrees`, `using-superpowers`,
`verification-before-completion`, `writing-plans`, `writing-skills`.

`DIRECT_OBSERVATION`. `using-superpowers/SKILL.md` is injected into **every**
session by the SessionStart hook with matcher `startup|clear|compact`, so it is
re-injected after every context compaction. Its text is visible in this session.

`DIRECT_OBSERVATION`. **superpowers ships manifests for eight harnesses**,
including `hooks-cursor.json` and a `.kimi-plugin/plugin.json` containing an
explicit **tool-name mapping table** for a non-Claude harness.

**Portability: HIGHEST of any plugin here** — it is the only one designed
cross-harness. See [PLUGINS_INDEX.md](PLUGINS_INDEX.md) for the mapping table.

### 5.3 document-skills — 19 Skills + 1 template, twice over

`plugins-backup/document-skills-41bbe19d1a1a/skills/`: `academy-guide`,
`algorithmic-art`, `brand-guidelines`, `canvas-design`, `claude-api`,
`discernment-nudge`, `doc-coauthoring`, `docx`, `frontend-design`,
`internal-comms`, `mcp-builder`, `pdf`, `pptx`, `skill-creator`,
`slack-gif-creator`, `theme-factory`, `web-artifacts-builder`,
`webapp-testing`, `xlsx` — plus `template/SKILL.md`. **20 `SKILL.md` files.**

`DIRECT_OBSERVATION`. A second copy exists at
`plugins-backup/document-skills-53048666b05b-ORPHANED/` — an **earlier install**
left in the cache when the plugin updated to `41bbe19d1a1a`. It is not
referenced by `installed_plugins.json`. Copied anyway; the `-ORPHANED` suffix is
this backup's own labelling, not the original directory name.

`VERIFIED_FACT`, by `diff -rq` over the two trees: they differ in **exactly two
places** — the orphan carries an extra `.claude-plugin/plugin.json`, and
`skills/frontend-design/SKILL.md` differs between them. Every other one of the
~419 files is byte-identical. The orphan is therefore **not** dead weight worth
deleting blind, but neither does it hold a second skill set.

`VERIFIED_FACT`. **document-skills has never been used**: all three of its
`pluginUsage` counters (`document-skills@inline`,
`document-skills@anthropic-agent-skills`, `41bbe19d1a1a@inline`) are **0**.

**Portability: MIXED.** `docx`/`pdf`/`pptx`/`xlsx` are the proprietary-licensed
ones again; the rest are unrestricted.

### 5.4 Claude Desktop remote plugins — 11 Skills

`plugins-backup/claude-desktop-remote-plugins/`:

| Plugin dir | Skills |
|---|---|
| `plugin_011v5h6QUzBZvas64y44XLhy` (**pdf-viewer**) | `view-pdf` |
| `plugin_01FTLa86dhbVJ3HB1LdHdhN7` (**engineering**) | `architecture`, `code-review`, `debug`, `deploy-checklist`, `documentation`, `incident-response`, `standup`, `system-design`, `tech-debt`, `testing-strategy` |

Marketplace: `knowledge-work-plugins`. **Portability: MEDIUM** for the Skill
bodies; the engineering plugin's 10 MCP servers all need their own auth — see
[MCP_AND_INTEGRATIONS.md](MCP_AND_INTEGRATIONS.md).

`DIRECT_OBSERVATION`. Neither was used in this project.

---

## 6. `skills-backup/plugin-provided-skills/` is empty — on purpose

`DIRECT_OBSERVATION`. The directory exists and contains zero files.

`DECISION`. Plugin Skills were **not** duplicated into `skills-backup/`, because
they are already preserved inside their complete plugin sources under
`plugins-backup/`, where their `references/`, `scripts/`, `assets/` and plugin
manifests stay attached. Splitting a Skill from its plugin would have produced a
Skill that no longer works. The empty directory is left in place so that a
reader who expects the PART M category structure finds an explicit answer rather
than a silent absence.

The PART M instruction to create category subdirectories "when supported by
actual evidence" was applied the same way: the four subdirectories that exist
(`project-skills`, `codex-agents-skills`, `claude-desktop-skills`,
`plugin-provided-skills`) correspond to actually-distinct storage systems found
on disk, not to invented taxonomy.

---

## 7. Built-in Skills that could NOT be exported

`DIRECT_OBSERVATION`. The following are **not files on disk** and therefore
cannot be copied. Recorded here and in
[MISSING_OR_UNRECOVERABLE.md](MISSING_OR_UNRECOVERABLE.md):

| Item | Why unexportable |
|---|---|
| Claude Code's built-in tool set (Read, Write, Edit, Bash, Grep, Glob, Task, WebFetch, WebSearch, …) | Compiled into the CLI binary |
| Claude Code's system prompt | Server-side |
| Claude Desktop's built-in behaviours (Cowork, artifacts, connectors UI) | Application code |
| Any server-side Skill not cached locally | Never written to this filesystem |

`DIRECT_OBSERVATION`. Searched for local caches of built-in Skills under
`~/.claude/` (depth 4), `%APPDATA%\Claude\` and `%LOCALAPPDATA%\Claude-3p\`.
The only Skill **files** found anywhere are the 88 indexed above.

---

## 8. What a migrating agent should actually load

`INFERENCE`, in priority order:

1. **`skills-backup/project-skills/` — all four, in full.** These encode the
   project's research-control doctrine and are the only Skills with any bearing
   on the science. Load them as standing instructions alongside
   `config-backup/project--CLAUDE.md`.
2. **`skills-backup/codex-agents-skills/`** if the destination is Codex — the
   port is already done.
3. **`plugins-backup/superpowers-6.3.0/skills/using-superpowers/SKILL.md`** and
   `systematic-debugging` — if the destination harness has a skill mechanism,
   these are the two that actually shaped working behaviour in this session, and
   superpowers is built to be ported.
4. **Nothing else is required.** Every remaining Skill is either unused in this
   project, proprietary-licensed, or tied to a Desktop feature that does not
   exist elsewhere.

`VERIFIED_FACT` supporting point 4: no `.docx`/`.pptx`/`.xlsx` artefact exists in
the project; no ARS command appears in the prompt history; document-skills has
`usageCount` 0 across all three counters; no subagent produced a surviving
artefact; and every scientific result was produced by direct `python.exe`
invocations against WNTR.
