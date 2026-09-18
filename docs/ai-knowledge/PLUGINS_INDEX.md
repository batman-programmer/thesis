# PLUGINS_INDEX.md — complete plugin inventory

**Governing rule (PART O of the backup request):**

> "Back up all Plugins/Bundles … **Do NOT merely describe them.**"

All five plugin trees below exist as **complete source copies** under
`plugins-backup/`. This document indexes them; it does not stand in for them.

**Measured on disk 2026-09-18:**

| Directory under `plugins-backup/` | Files | Size | SKILL.md |
|---|---|---|---|
| `academic-research-skills-3.21.1/` | 1 483 | 27 MB | 4 |
| `document-skills-41bbe19d1a1a/` | 419 | 12 MB | 20 |
| `document-skills-53048666b05b-ORPHANED/` | 420 | 12 MB | 20 |
| `superpowers-6.3.0/` | 195 | 2.1 MB | 14 |
| `claude-desktop-remote-plugins/` | 25 | 120 KB | 11 |
| **TOTAL** | **2 542** | **~53 MB** | **69** |

---

## 1. Two independent plugin systems

`DIRECT_OBSERVATION`. Plugins on this machine come from **two unrelated
mechanisms** with different manifests, different install records and different
hosts:

| System | Install record | Cache location | Host |
|---|---|---|---|
| **Claude Code plugins** | `~/.claude/plugins/installed_plugins.json` + `known_marketplaces.json` | `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/` | Claude Code CLI |
| **Claude Desktop remote plugins** | `rpm/manifest.json` | `…/Claude-3p/…/rpm/plugin_<id>/` | Claude Desktop only |

Three plugins are installed in the first system; two in the second.

---

## 2. academic-research-skills 3.21.1 — the largest, and the least used

**Backup:** `plugins-backup/academic-research-skills-3.21.1/`
**Original:** `~/.claude/plugins/cache/academic-research-skills/academic-research-skills/3.21.1/`
**Source:** third-party, GitHub `Imbad0202/academic-research-skills`
**Licence:** **CC-BY-NC-4.0** (non-commercial)
**Author:** Cheng-I Wu

`plugin.json` verbatim description:

> "Contract-audited academic research pipeline for Claude Code: research → write
> → review → revise → finalize. 4 skills, 27 modes, 39 prompt roles (3
> plugin-exposed agents; the rest run inline by default), v3.7.3 + v3.8 L3
> claim-faithfulness gate, v3.9.0 cross-index triangulation, v3.10 triangulation
> policy layer, v3.11 deterministic citation verification gate (#182). Capability
> ceilings: docs/STAGE_CAPABILITY_MATRIX.md."

### 2.1 Structure

| Top-level dir | Size | What it is |
|---|---|---|
| `academic-paper/` | 1.2 MB | Skill + 12 agents |
| `academic-paper-reviewer/` | 673 KB | Skill + 7 agents |
| `academic-pipeline/` | 660 KB | Skill + 5 agents |
| `deep-research/` | 872 KB | Skill + 15 agents |
| `agents/` | 84 KB | 3 top-level agents |
| `shared/` | 2.0 MB | shared agent (`compliance_agent.md`) + shared resources |
| `commands/` | 38 KB | **16 `/ars-*` slash commands** |
| `docs/` | 4.4 MB | `ARCHITECTURE.md`, `STAGE_CAPABILITY_MATRIX.md`, `RISK_REGISTER.md`, `DATA_FLOWS.md`, `CONTROL_AVAILABILITY.md`, roadmaps, design notes, migration notes |
| `scripts/` | 12 MB | the plugin's own tooling (largest single component) |
| `examples/` | 2.8 MB | worked examples |
| `audits/` | 220 KB | contract audits |
| `tests/` | 648 KB | plugin self-tests |
| `tools/` | 78 KB | helper tools |
| `hooks/` | 17 KB | `hooks.json` + `run_guard.sh` |
| `pi/` | 33 KB | **a second-harness wrapper** — `wrapper.js`, `wrapper.test.mjs`, `package.json` |
| `.claude/` | — | the plugin's own `CLAUDE.md` + `CHANGELOG.md` |

The 16 commands: `ars-3w`, `ars-abstract`, `ars-cache-invalidate`,
`ars-citation-check`, `ars-disclosure`, `ars-format-convert`, `ars-full`,
`ars-lit-review`, `ars-mark-read`, `ars-outline`, `ars-plan`,
`ars-rebuttal-audit`, `ars-reviewer`, `ars-revision`, `ars-revision-coach`,
`ars-unmark-read`. All 16 are separately copied to `commands-backup/`.

### 2.2 What was excluded, and proof of what was not

`DIRECT_OBSERVATION`. `diff <(ls -1a live) <(ls -1a backup)` returns exactly two
lines: the live tree additionally contains **`evals/` (15 MB)** and
**`.in_use`** (a runtime lock marker). Every other top-level entry is present in
the backup.

`DECISION`. `evals/` was excluded — 15 MB of the plugin author's own evaluation
harness, reproducible by re-installing the plugin from its public GitHub
repository, and irrelevant to this thesis. Recorded in
[MISSING_OR_UNRECOVERABLE.md](MISSING_OR_UNRECOVERABLE.md). `.in_use` is
runtime state with no information content.

### 2.3 Hooks

`hooks/hooks.json` registers a `PreToolUse` guard on `Write|Edit|MultiEdit|Bash`
running `bash "${CLAUDE_PLUGIN_ROOT}/hooks/run_guard.sh"`, and a `SessionStart`
announcement running
`bash "${CLAUDE_PLUGIN_ROOT}/scripts/announce-ars-loaded.sh"`. Both are quoted in
full in [CLAUDE_ENVIRONMENT.md](CLAUDE_ENVIRONMENT.md) §5 and copied to
`hooks-backup/`.

`DIRECT_OBSERVATION`. The SessionStart announcement is why every session in this
project — including the one writing this file — opens with the line *"ARS plugin
still loaded after compact. Slash commands: /ars-full …"*.

### 2.4 Usage reality

| Signal | Value |
|---|---|
| `pluginUsage["academic-research-skills@inline"]` | **214** |
| `pluginUsage["academic-research-skills@academic-research-skills"]` | **90** |
| `/ars-*` commands in the 98-entry prompt history | **0** |
| ARS skills in `skillUsage` | **0** |
| Surviving artefacts produced by ARS agents | **0** |

`INFERENCE`. The 304 combined counts measure **plugin loads**, not deliberate
invocations. **No part of this plugin contributed to any result in this thesis.**
The literature work in Phases 1.5–2 was done with the project-local
`research-review` Skill and direct WebSearch/WebFetch, not with ARS.

`DIRECT_OBSERVATION`. The `skills/` subdirectory is broken on Windows — see
[SKILLS_INDEX.md](SKILLS_INDEX.md) §5.1 for the four text-file-instead-of-symlink
observation.

**Portability: MEDIUM.** Markdown prompt bodies port anywhere. The `/ars-*`
command surface, the `${CLAUDE_PLUGIN_ROOT}` hooks and the agent dispatch do
not. `pi/wrapper.js` shows the author anticipated one non-Claude harness.
**Licence restricts commercial redistribution.**

---

## 3. superpowers 6.3.0 — the one built to be ported ⭐

**Backup:** `plugins-backup/superpowers-6.3.0/`
**Original:** `~/.claude/plugins/cache/superpowers-dev/superpowers/6.3.0/`
**Source:** third-party, GitHub `obra/superpowers`, author Jesse Vincent
**Licence:** **MIT** — the only unrestricted plugin here

### 3.1 Eight harness manifests — the single most migration-relevant artefact

`VERIFIED_FACT`. This plugin ships a parallel manifest for **eight different
agent harnesses**, all present in the backup:

| Harness | Manifest file |
|---|---|
| Claude Code | `.claude-plugin/plugin.json` + `marketplace.json` |
| Codex | `.codex-plugin/plugin.json` |
| Cursor | `.cursor-plugin/plugin.json` |
| Devin | `.devin-plugin/plugin.json` |
| Hermes | `.hermes-plugin/plugin.yaml` + `__init__.py` |
| Kimi | `.kimi-plugin/plugin.json` |
| OpenCode | `.opencode/plugins/superpowers.js` + `INSTALL.md` |
| Pi | `.pi/extensions/superpowers.ts` (+ `pi` block in `package.json`) |
| Gemini | `gemini-extension.json` (`contextFileName: "GEMINI.md"`) |
| *(generic)* | `.agents/plugins/marketplace.json` |

It also ships **three instruction files side by side** — `CLAUDE.md`,
`AGENTS.md` and `GEMINI.md` — the same convention the user has now applied by
hand to this project (see [SKILLS_INDEX.md](SKILLS_INDEX.md) §3).

### 3.2 The Kimi tool-mapping table — read this before porting anything

`DIRECT_OBSERVATION`. `.kimi-plugin/plugin.json` carries a
`skillInstructions` string that is a **complete tool-name translation table**
from Claude Code's tool surface to another vendor's. Quoted in full because it is
the clearest available template for what a migration actually has to remap:

> Kimi Code tool mapping for Superpowers skills:
>
> - When a Superpowers skill says to ask the user, ask clarifying questions, ask
>   one question at a time, present multiple-choice options, use the terminal for
>   a question, or wait for the user's choice, call Kimi Code's
>   `AskUserQuestion` tool. Do not render those choices as plain assistant text
>   unless `AskUserQuestion` is unavailable or the session is in auto permission
>   mode.
> - For `AskUserQuestion`, provide 1 question with 2-4 concrete options when
>   possible. Put the recommended option first and suffix its label with
>   `(Recommended)`.
> - When a Superpowers skill refers to `TodoWrite`, use Kimi Code's `TodoList`
>   tool.
> - When a Superpowers skill says `Task tool (general-purpose)` or asks you to
>   dispatch an implementer/reviewer subagent, use Kimi Code's `Agent` tool with
>   a Kimi subagent type. Do not pass `general-purpose` as `subagent_type`.
> - For implementation, code review, spec review, quality review, and filled
>   Superpowers subagent prompt templates, call `Agent` with
>   `subagent_type: "coder"`, paste the fully filled prompt into `prompt`, and
>   provide a short `description`.
> - For read-only codebase exploration that would take several searches, use
>   `Agent` with `subagent_type: "explore"`.
> - For read-only planning or architecture design, use `Agent` with
>   `subagent_type: "plan"`.
> - Keep dependent Superpowers subagent steps sequential. Use multiple `Agent`
>   calls, or `run_in_background: true` only when the work is independent and
>   background agents are available.
> - When a Superpowers skill refers to the `Skill` tool, use Kimi Code's native
>   `Skill` tool.
> - Use Kimi Code's `Read`, `Write`, `Edit`, `Bash`, `Grep`, `Glob`, `FetchURL`,
>   `WebSearch`, and MCP tools by their actual exposed names.
> - When a skill asks to search file contents, use `Grep`; when it asks to find
>   files by path or pattern, use `Glob`; when it asks to fetch a URL, use
>   `FetchURL`; when it asks to search the web, use `WebSearch`.

`INFERENCE`. **A migrating agent should apply the same mapping discipline to this
project's own four Skills and to `CLAUDE.md`.** The Claude-specific tool names
that appear in this project's instructions are: `Read`, `Write`, `Edit`, `Bash`,
`Grep`, `Glob`, `Task`, `WebSearch`, `WebFetch`, `TodoWrite`, `Skill`. Nothing
else in `.claude/skills/` depends on a Claude-only capability.

### 3.3 Hooks

`hooks/hooks.json` — `SessionStart` with matcher `startup|clear|compact`,
command `"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd" session-start`,
`shell: "bash"`, `async: false`.

`hooks/hooks-cursor.json` — `{"version": 1, "hooks": {"sessionStart":
[{"command": "./hooks/run-hook.cmd session-start"}]}}` — a **different schema**
(integer `version`, lowercase camelCase event name, relative path) for the same
behaviour. Direct evidence that hook definitions do **not** port unchanged.

`hooks/session-start` (2 274 B, executable) is the actual hook body. All copied
to `hooks-backup/`.

`DIRECT_OBSERVATION`. The matcher includes `compact`, which is why the full
`using-superpowers` skill text is re-injected into this session after every
context compaction.

### 3.4 Usage

| Signal | Value |
|---|---|
| `pluginUsage["superpowers@superpowers-dev"]` | **44** |
| `pluginUsage["superpowers@inline"]` | **6** |

`INFERENCE`. Unlike ARS, superpowers **did** shape behaviour — its
`using-superpowers` skill is injected as a system-level directive into every
session and is visibly acting on the agent's process discipline. Its
`systematic-debugging` and `verification-before-completion` skills are consistent
with how the Phase 5 diagnostic work was actually conducted, though no transcript
records an explicit `Skill` call to either.

**Portability: HIGH — the highest of any plugin here.** MIT-licensed, ships its
own manifests for eight harnesses, and explicitly documents its tool
dependencies.

---

## 4. document-skills — installed, never used

**Backup:** `plugins-backup/document-skills-41bbe19d1a1a/` (current) and
`plugins-backup/document-skills-53048666b05b-ORPHANED/` (superseded)
**Original:** `~/.claude/plugins/cache/anthropic-agent-skills/document-skills/<sha>/`
**Source:** Anthropic (marketplace `anthropic-agent-skills`, owner Keith Lazuka,
`klazuka@anthropic.com`)

`DIRECT_OBSERVATION`. The marketplace manifest declares **five separate plugins**
sharing one source tree:

| Plugin in manifest | Skills |
|---|---|
| `document-skills` | `xlsx`, `docx`, `pptx`, `pdf` |
| `example-skills` | `algorithmic-art`, `brand-guidelines`, `canvas-design`, `doc-coauthoring`, `frontend-design`, `internal-comms`, `mcp-builder`, `skill-creator`, `slack-gif-creator`, `theme-factory`, `web-artifacts-builder`, `webapp-testing` |
| `claude-api` | `claude-api` |
| `academy-guide` | `academy-guide` |
| `discernment-nudge` | `discernment-nudge` |

Only `document-skills` is listed in `installed_plugins.json`.

`VERIFIED_FACT`. The two cached copies differ in exactly two files
(`diff -rq`): the orphan has an extra `.claude-plugin/plugin.json`, and
`skills/frontend-design/SKILL.md` differs. All other ~419 files are identical.

`VERIFIED_FACT`. **Never used.** `document-skills@inline` = 0,
`document-skills@anthropic-agent-skills` = 0, `41bbe19d1a1a@inline` = 0. No
`.docx`, `.pptx`, `.xlsx` or generated PDF exists anywhere in `D:\Thesis`.

**Portability: MIXED.** `docx`/`pdf`/`pptx`/`xlsx` carry
`license: Proprietary` in their frontmatter — do not redistribute. The other 15
carry no licence restriction in-file, but `THIRD_PARTY_NOTICES.md` (present in
the backup) should be read before reuse.

---

## 5. Claude Desktop remote plugins — a separate world

**Backup:** `plugins-backup/claude-desktop-remote-plugins/`
**Original:** Claude Desktop `rpm/` remote-plugin store
**Marketplace:** `knowledge-work-plugins`
(`marketplace_01QRn9XAjzzeAokB5nPWVMxP`)

`manifest.json` verbatim:

```json
{
  "lastUpdated": 1788290081474,
  "plugins": [
    {
      "id": "plugin_011v5h6QUzBZvas64y44XLhy",
      "name": "pdf-viewer",
      "updatedAt": "2026-09-01T14:06:57.189555Z",
      "updatedAtVerified": true,
      "displayName": "PDF Viewer",
      "marketplaceId": "marketplace_01QRn9XAjzzeAokB5nPWVMxP",
      "marketplaceName": "knowledge-work-plugins",
      "installedBy": "user",
      "installationPreference": "available"
    },
    {
      "id": "plugin_01FTLa86dhbVJ3HB1LdHdhN7",
      "name": "engineering",
      "updatedAt": "2026-09-01T14:07:00.281513Z",
      "updatedAtVerified": true,
      "displayName": "Engineering",
      "marketplaceId": "marketplace_01QRn9XAjzzeAokB5nPWVMxP",
      "marketplaceName": "knowledge-work-plugins",
      "installedBy": "user",
      "installationPreference": "available"
    }
  ]
}
```

### 5.1 pdf-viewer 0.2.0 (Anthropic)

> "View, annotate, and sign PDFs in a live interactive viewer. Mark up contracts,
> fill forms with visual feedback, stamp approvals, and place signatures — then
> download the annotated copy."

1 skill (`view-pdf`), 4 commands (`/annotate`, `/fill-form`, `/open`, `/sign`),
1 MCP server, `CONNECTORS.md`, `LICENSE`, `README.md`. Complete — 6 files.

### 5.2 engineering 1.2.0 (Anthropic)

> "Streamline engineering workflows — standups, code review, architecture
> decisions, incident response, and technical documentation. Works with your
> existing tools or standalone."

10 skills (`architecture`, `code-review`, `debug`, `deploy-checklist`,
`documentation`, `incident-response`, `standup`, `system-design`, `tech-debt`,
`testing-strategy`), 0 commands, **10 MCP servers** in `.mcp.json`. Complete —
14 files. No `LICENSE` file ships with it.

`DIRECT_OBSERVATION`. Neither plugin was used in this project. Both are
Desktop-only and invisible to Claude Code. The MCP servers they declare are
indexed in [MCP_AND_INTEGRATIONS.md](MCP_AND_INTEGRATIONS.md) and every one
requires its own authentication that this backup deliberately does not carry.

**Portability: LOW for the plugin, MEDIUM for the skill bodies.** The skill
Markdown is reusable; the viewer UI, the connectors and the MCP endpoints are
not.

---

## 6. Install records, copied to `config-backup/`

| File | What it pins |
|---|---|
| `user--plugins--installed_plugins.json` | the three Claude Code plugins with marketplace, version and commit SHA |
| `user--plugins--known_marketplaces.json` | five marketplaces, incl. `ecc` known-but-never-installed |
| `user--claude--settings.json` | `enabledPlugins` (3) + `extraKnownMarketplaces` (4) |

`DIRECT_OBSERVATION`. All three Claude Code plugins were installed on
**2026-09-02**, within a 2 min 6 s window. `INFERENCE`: they were installed in
one sitting, **after Phase 3 had already finished** (Phase 3 ended
2026-09-01 19:49). They therefore cannot have contributed to Phases 1–3, and §2.4
and §4 show they did not contribute to Phases 4–6 either.

---

## 7. What a migrating agent should do about plugins

`INFERENCE`, in order:

1. **Install nothing at first.** No plugin was load-bearing for any scientific
   result. The project resumes with Python + WNTR + the four project Skills.
2. **If the destination harness supports skills, port superpowers.** MIT, eight
   harness manifests, and the `.kimi-plugin` mapping table tells you exactly what
   to remap. Start with `using-superpowers`, `systematic-debugging`,
   `verification-before-completion`.
3. **Treat ARS as optional.** CC-BY-NC-4.0, 27 MB, broken `skills/` symlinks on
   Windows, and zero demonstrated contribution. If academic-writing automation is
   wanted later, re-install it from GitHub rather than porting this tree.
4. **Do not port document-skills or the Desktop plugins.** Proprietary licences
   on the four document Skills; zero usage; Desktop-only hosting; MCP endpoints
   that need credentials this backup does not carry.
5. **Do port the hook *lessons*, not the hook files.** `hooks.json` vs
   `hooks-cursor.json` in superpowers is the proof that hook schemas differ per
   harness. Re-author, don't copy.
