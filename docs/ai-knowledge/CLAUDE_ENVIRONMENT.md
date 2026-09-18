# CLAUDE_ENVIRONMENT.md — complete Claude configuration inventory

**Scope rule (PART L of the backup request):**

> "Do not assume that everything lives inside the project. Document exactly what
> you inspected."

Every path below was inspected directly. Anything not inspected is marked as
such. Every file named as "copied" exists in this backup at the stated path.

**Inspection dates: 2026-09-07 (primary sweep) and 2026-09-18 (re-verification).**
Where a value changed between the two, both are shown.

---

## 1. Locations inspected

| # | Path | What it is | Exists? |
|---|---|---|---|
| 1 | `D:\Thesis\CLAUDE.md` | Project constitution | **Yes**, 18 435 B |
| 2 | `D:\Thesis\AGENTS.md` | **Codex** port of the constitution | **Yes**, 18 427 B |
| 3 | `D:\Thesis\.claude\settings.local.json` | Project permission allow-list | **Yes**, 10 554 B |
| 4 | `D:\Thesis\.claude\skills\` | 4 project Skills | **Yes** |
| 5 | `D:\Thesis\.agents\skills\` | **Codex** copies of the 4 Skills | **Yes** |
| 6 | `C:\Users\ABN\.claude\settings.json` | User-level Claude Code settings | **Yes**, 923 B |
| 7 | `C:\Users\ABN\.claude.json` | Global Claude Code state | **Yes** |
| 8 | `C:\Users\ABN\.claude\plugins\` | Plugin cache, marketplaces, manifests | **Yes** |
| 9 | `C:\Users\ABN\.claude\` (top level) | 16 entries — see §7 | **Yes** |
| 10 | `C:\Users\ABN\CLAUDE.md` | User-level instructions | **NO — does not exist** |
| 11 | `C:\Users\ABN\.claude\CLAUDE.md` | User-level instructions | **NO — does not exist** |
| 12 | `D:\CLAUDE.md` (parent-dir instructions) | Parent CLAUDE.md | **NO — does not exist** |
| 13 | `%APPDATA%\Claude\claude_desktop_config.json` | Claude Desktop (Roaming) | **Yes**, 1 323 B |
| 14 | `%APPDATA%\Claude\config.json` | Claude Desktop state incl. OAuth | **Yes** — redacted copy only |
| 15 | `%APPDATA%\Claude\developer_settings.json` | Desktop dev settings | **Yes**, 27 B |
| 16 | `%LOCALAPPDATA%\Claude-3p\claude_desktop_config.json` | Claude Desktop 3p deployment | **Yes**, 1 797 B |
| 17 | Desktop `local-agent-mode-sessions/skills-plugin/` | Desktop Skills store | **Yes** — see §8 |
| 18 | Desktop `rpm/` | Desktop remote-plugin store | **Yes** — see §8 |
| 19 | `%LOCALAPPDATA%\Claude-3p\ccd-session-secrets\` | Session secrets | **Yes** — `SECRET PRESENT — NOT EXPORTED` |
| 20 | `D:\Thesis\.venv\` | Project Python environment | **Yes** |

`DIRECT_OBSERVATION`. **There is no user-level `CLAUDE.md` and no parent-directory
`CLAUDE.md`.** The project `CLAUDE.md` is the *only* instruction file Claude Code
loads for this project. Anything a migrating agent needs to know about how the
user wants work done is in that one file (backed up at
`config-backup/project--CLAUDE.md`) plus
[USER_PROJECT_CONTEXT.md](USER_PROJECT_CONTEXT.md).

---

## 2. Project-level configuration

### 2.1 `CLAUDE.md` — the constitution

`VERIFIED_FACT`. 18 435 B, last modified **2026-08-23 23:03** — i.e. written
*before* the first recorded session (`a4cbf1ac`, 2026-08-24 21:45) and **never
edited since**. 23 numbered sections. Copied verbatim to
`config-backup/project--CLAUDE.md`. Analysed in
[USER_PROJECT_CONTEXT.md](USER_PROJECT_CONTEXT.md).

### 2.2 `AGENTS.md` — the Codex port  ⚠ NEW, 2026-09-18

`DIRECT_OBSERVATION`. 18 427 B, created **2026-09-18 03:09**. A `diff` against
`CLAUDE.md` shows **exactly four differing lines**:

| Line | `CLAUDE.md` | `AGENTS.md` |
|---|---|---|
| 1 | `# CLAUDE.md — Research Engineering Constitution` | `# AGENTS.md — Research Engineering Constitution` |
| 492 | "The main **Claude** instance should synthesize their findings…" | "The main **Codex** instance should synthesize their findings…" |
| 527 | "**Claude's** job is to make those decisions better informed…" | "**Codex's** job is to make those decisions better informed…" |
| 624 | "**Claude Code** is the primary coding/research orchestration interface." | "**Codex** is the primary coding/research orchestration interface." |

`DIRECT_OBSERVATION`. `D:\Thesis\.agents\skills\` was created at the same
timestamp and holds copies of all four project Skills. Three are **byte-identical**
to their `.claude/skills/` originals; `research-review/SKILL.md` differs on
**one line only** (line 64: `` `CLAUDE.md` `` → `` `AGENTS.md` ``).

`INFERENCE`. **A migration to Codex (OpenAI's agent harness) has already been
started by hand.** The constitution and the four Skills have been ported by
mechanical find-and-replace. Nothing else has been ported.

`OPEN_QUESTION`. Who created these and when in the workflow is **not recorded**.
They appear as untracked files in `git status`, are dated 2026-09-18 03:09, and
no session transcript covers that timestamp with substantive work. Do not assume
they are complete or authoritative — verify with the user.

Both are copied into this backup:
- `config-backup/project--AGENTS.md`
- `skills-backup/codex-agents-skills/{change-impact,methodology-review,novelty-check,research-review}/SKILL.md`

### 2.3 `.claude/settings.local.json`

`VERIFIED_FACT`. 10 554 B. Exactly one key, `permissions`, containing exactly
one sub-key, `allow`, with **149 entries** (the 2026-09-07 sweep recorded ~140;
it has grown). No `deny`, no `ask`, no `defaultMode`, no `additionalDirectories`,
no hooks, no MCP servers at project level.

First twelve entries verbatim:

```
Bash(pdftotext -l 2 -enc UTF-8 proposal/proposal.pdf -)
Bash(pdftotext -enc UTF-8 proposal/proposal.pdf -)
Bash(pdfinfo proposal/proposal.pdf)
Bash(pdftotext -l 1 -enc UTF-8 seminar/seminar.pdf -)
Bash(pdftotext -enc UTF-8 seminar/seminar.pdf -)
Bash(pdfinfo seminar/seminar.pdf)
Bash(git ls-tree *)
Bash(pdftotext *)
Bash(command -v magick convert mutool qpdf gswin64c)
Bash(python -c ' *)
WebSearch
WebFetch(domain:doi.org)
```

`INFERENCE`. This is an accreted per-approval list, not a designed policy. It is
**Claude-Code-specific syntax and will not port** to another harness — see
[MISSING_OR_UNRECOVERABLE.md](MISSING_OR_UNRECOVERABLE.md). Copied verbatim to
`config-backup/project--claude--settings.local.json`.

### 2.4 `.claude/skills/` — the four project Skills

`VERIFIED_FACT`. Four directories, one `SKILL.md` each:

| Skill | Bytes | Last modified |
|---|---|---|
| `change-impact` | 14 039 | 2026-08-23 22:29 |
| `methodology-review` | 15 772 | 2026-08-23 22:28 |
| `novelty-check` | 15 037 | 2026-08-23 22:28 |
| `research-review` | 16 850 | **2026-08-24 23:30** |

`INFERENCE`. `research-review` was edited *during* the first session
(`a4cbf1ac` ran 21:45 → 23:13 on 2026-08-24; the file is stamped 23:30). The other
three are untouched since creation. Full detail in
[SKILLS_INDEX.md](SKILLS_INDEX.md); files copied to
`skills-backup/project-skills/`.

`DIRECT_OBSERVATION`. `.claude/` contains **only** `settings.local.json` and
`skills/`. No project-level `commands/`, `agents/`, `hooks/`, `.mcp.json`,
`settings.json`, or `CLAUDE.local.md`.

---

## 3. User-level Claude Code configuration

### 3.1 `~/.claude/settings.json` (923 B) — copied verbatim

```json
{
  "model": "opus[1m]",
  "enabledPlugins": {
    "academic-research-skills@academic-research-skills": true,
    "document-skills@anthropic-agent-skills": true,
    "superpowers@superpowers-dev": true
  },
  "extraKnownMarketplaces": {
    "academic-research-skills": { "source": { "source": "git", "url": "https://github.com/Imbad0202/academic-research-skills.git" } },
    "anthropic-agent-skills":   { "source": { "source": "git", "url": "https://github.com/anthropics/skills.git" } },
    "superpowers-dev":          { "source": { "source": "git", "url": "https://github.com/obra/superpowers.git" } },
    "ecc":                      { "source": { "source": "git", "url": "https://github.com/affaan-m/ECC.git" } }
  },
  "modelSettings": { "claude-opus-5": { "effortLevel": "high" } },
  "theme": "dark"
}
```

`VERIFIED_FACT`. Four settings that matter for reproducing behaviour:

1. **Model `opus[1m]`** — Opus 5 with the 1 M-token context window. Phase 5 and
   Phase 6 analyses were produced at this context size; a harness with a smaller
   window may not be able to hold the same working set.
2. **Effort `high`** on `claude-opus-5`. Sessions `a4cbf1ac` and `10b7b88f` were
   run at effort `max` via explicit `/effort` commands (visible in the
   transcripts); the *default* is `high`.
3. **Three plugins enabled**, four marketplaces known.
4. `theme: dark` — cosmetic.

Copied to `config-backup/user--claude--settings.json`.

### 3.2 `~/.claude.json` — global state

`DIRECT_OBSERVATION`. Top-level keys inspected (30): `agentLastUsed`,
`cachedExperimentData`, `cachedExperimentFeatures`, `cachedGrowthBookFeatures`,
`cachedGrowthBookFeaturesAt`, `changelogLastFetched`, `closedIssuesLastChecked`,
`customApiKeyResponses`, `firstStartTime`, `firstStartVersion`,
`githubRepoPaths`, `hasAcknowledgedCostThreshold`, `hasAvailableSubscription`,
`hasCompletedOnboarding`, `hasOpenedAgentsView`,
`hasResetAutoModeOptInForDefaultOffer`, `lastOnboardingVersion`,
`lastReleaseNotesSeen`, `machineID`, `metricsStatusCache`, `migrationVersion`,
`numStartups`, `officialMarketplaceAutoInstallAttempted`,
`officialMarketplaceAutoInstalled`, `opusProMigrationComplete`, `pluginUsage`,
`projects`, `promptQueueUseCount`, `seenNotifications`,
`shiftEnterKeyBindingInstalled`, `skillUsage`, `sonnet1m45MigrationComplete`,
`subscriptionNoticeCount`, `tipLifetimeShownCounts`, `tipsHistory`,
`unpinFable5LaunchEffort`, `unpinOpus47LaunchEffort`, `unpinOpus48LaunchEffort`,
`userID`.

**This whole file was NOT copied.** It holds `userID` and `machineID`
(`SECRET PRESENT — NOT EXPORTED`). The non-secret fields that matter are
transcribed below.

`VERIFIED_FACT`. `numStartups` = **36**.

`VERIFIED_FACT`. `skillUsage` (as of 2026-09-18):

| Skill | usageCount | lastUsedAt (epoch ms) |
|---|---|---|
| `research-review` | 1 | 1787608726842 |
| `anthropic-skills:consolidate-memory` | 1 | 1788717822920 |

`INFERENCE`. **Only one project Skill was ever formally invoked** —
`research-review`, once, in the very first session. `methodology-review`,
`novelty-check` and `change-impact` have `usageCount` absent, i.e. **never
invoked through the Skill mechanism**, despite `CLAUDE.md` §15 naming all four.
Their *content* may still have shaped the work by being read into context.
See [FINDINGS.md](FINDINGS.md).

`VERIFIED_FACT`. `pluginUsage` (as of 2026-09-18; the 2026-09-07 sweep recorded
lower numbers, shown in brackets):

| Entry | usageCount | lastUsedNumStartups |
|---|---|---|
| `academic-research-skills@inline` | **214** (was 141) | 35 |
| `academic-research-skills@academic-research-skills` | **90** (was 34) | 36 |
| `superpowers@superpowers-dev` | **44** (was 31) | 36 |
| `superpowers@inline` | **6** (was 3) | 35 |
| `anthropic-skills@inline` | 1 | 33 |
| `document-skills@inline` | 0 | 31 |
| `document-skills@anthropic-agent-skills` | 0 | 34 |
| `41bbe19d1a1a@inline` | 0 | 34 |

`INFERENCE`. academic-research-skills is by far the most-exercised plugin;
document-skills has **never** been used (all three of its counters are 0).

`VERIFIED_FACT`. `projects` has five keys — `d:/Thesis`, `C:/Users/ABN`,
`D:/Thesis`, `C:/Users/ABN/Desktop`, `D:\Thesis`. Note the **same directory
recorded three ways** (`d:/Thesis`, `D:/Thesis`, `D:\Thesis`), which is the same
case/separator inconsistency that broke the prompt-history filter (see
[FAILED_APPROACHES.md](FAILED_APPROACHES.md)). MCP state per project:

| Project key | `mcpServers` | `enabledMcpjsonServers` |
|---|---|---|
| `d:/Thesis` | `{}` | `[]` |
| `C:/Users/ABN` | `{}` | `[]` |
| `D:/Thesis` | `{}` | `[]` |
| `C:/Users/ABN/Desktop` | `{}` | `[]` |
| `D:\Thesis` | **`null`** | `[]` |

`VERIFIED_FACT`. **Claude Code has zero configured MCP servers.** See
[MCP_AND_INTEGRATIONS.md](MCP_AND_INTEGRATIONS.md).

### 3.3 `~/.claude/stats-cache.json` — usage statistics

`DIRECT_OBSERVATION`. `lastComputedDate` **2026-08-27** — stale; it predates
Phases 4, 5 and 6 entirely. What it does record:

| Field | Value |
|---|---|
| `firstSessionDate` | 2026-08-24T21:39:58.811Z |
| `totalSessions` | 6 |
| `totalMessages` | 638 |
| `longestSession` | `4f550550-…` — 180 621 524 ms ≈ **50.2 h**, 114 messages |
| 2026-08-24 | 347 messages, 3 sessions, 96 tool calls, 49 509 473 tokens |
| 2026-08-26 | 291 messages, 3 sessions, 85 tool calls, 31 855 774 tokens |
| `modelUsage.claude-opus-5` | in 57 639 / out 959 617 / cache-read 65 060 299 / cache-create 15 287 692 |

`INFERENCE`. **These are Phase-1-and-2 figures only.** The Phase 4–6 workload
(session `32df42f5`, 12.4 MB of transcript) is not counted here. Do not cite
these as project totals.

---

## 4. Installed plugins

### 4.1 `installed_plugins.json` — copied verbatim

`VERIFIED_FACT`. Three plugins, all `scope: "user"`:

| Plugin | Version | Git commit SHA | Installed | Last updated |
|---|---|---|---|---|
| `academic-research-skills@academic-research-skills` | **3.21.1** | `94436237913091d4739870159d241660527e8338` | 2026-09-02T22:18:01.248Z | 2026-09-02T22:18:01.248Z |
| `document-skills@anthropic-agent-skills` | `41bbe19d1a1a` | `41bbe19d1a1a7eaab5e7bb9050a417e5c6cffc8f` | 2026-09-02T22:19:32.748Z | **2026-09-06T19:41:29.516Z** |
| `superpowers@superpowers-dev` | **6.3.0** | `b36e0829c6d0140e93cfef2ca599b1b07d4a7797` | 2026-09-02T22:20:07.505Z | 2026-09-02T22:20:07.505Z |

Install paths: `C:\Users\ABN\.claude\plugins\cache\<marketplace>\<plugin>\<version>\`.

`INFERENCE`. All three were installed within **2 minutes 6 seconds** on
2026-09-02 — a single deliberate setup action, taken *after* Phase 3 ended and
*during* Phase 4. They played no part in Phases 1–3.

### 4.2 `known_marketplaces.json` — copied verbatim

`VERIFIED_FACT`. Five marketplaces:

| Marketplace | Source | Last updated |
|---|---|---|
| `claude-plugins-official` | github `anthropics/claude-plugins-official` | 2026-09-06T19:57:20.318Z |
| `academic-research-skills` | git `https://github.com/Imbad0202/academic-research-skills.git` | 2026-09-02T22:16:02.466Z |
| `anthropic-agent-skills` | git `https://github.com/anthropics/skills.git` | 2026-09-06T19:57:26.152Z |
| `superpowers-dev` | git `https://github.com/obra/superpowers.git` | 2026-09-02T22:19:57.246Z |
| `ecc` | git `https://github.com/affaan-m/ECC.git` | 2026-09-02T22:21:27.880Z |

`DIRECT_OBSERVATION`. **`ecc` is known but no plugin from it is installed**, and
`claude-plugins-official` is known but absent from `extraKnownMarketplaces` in
`settings.json` (it is auto-installed —
`officialMarketplaceAutoInstalled` is set in `~/.claude.json`).

Plugin sources themselves are copied to `plugins-backup/` — see
[PLUGINS_INDEX.md](PLUGINS_INDEX.md).

---

## 5. Hooks

`VERIFIED_FACT`. **No project-level hooks exist.** All hooks come from plugins.
All hook definitions and scripts are copied to `hooks-backup/` (7 files).

### 5.1 academic-research-skills — `hooks-backup/academic-research-skills/hooks.json`

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [ { "type": "command",
          "command": "bash \"${CLAUDE_PLUGIN_ROOT}/scripts/announce-ars-loaded.sh\"" } ] }
    ],
    "PreToolUse": [
      { "matcher": "Write|Edit|MultiEdit|Bash",
        "hooks": [ { "type": "command",
          "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/run_guard.sh\"" } ] }
    ]
  }
}
```

Scripts copied: `announce-ars-loaded.sh`, `run_guard.sh`.

`DIRECT_OBSERVATION`. `announce-ars-loaded.sh` is **not** under the plugin's
`hooks/` directory as the path layout would suggest — it lives at
`academic-research-skills/3.21.1/scripts/`. This cost real debugging time (see
[FAILED_APPROACHES.md](FAILED_APPROACHES.md)).

`DIRECT_OBSERVATION`. The `PreToolUse` guard fires on **every** `Write`, `Edit`,
`MultiEdit` and `Bash` call in this project. It is therefore active for all of
Phases 4–6 and for the production of this backup.

### 5.2 superpowers — `hooks-backup/superpowers/hooks.json`

```json
{
  "hooks": {
    "SessionStart": [
      { "matcher": "startup|clear|compact",
        "hooks": [ { "type": "command",
          "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd\" session-start",
          "shell": "bash", "async": false } ] }
    ]
  }
}
```

Also copied: `hooks-cursor.json` (a **Cursor**-harness variant, schema `version: 1`,
lowercase `sessionStart`, no `${CLAUDE_PLUGIN_ROOT}`) and the `run-hook.cmd` /
`session-start` scripts.

`INFERENCE`. `matcher: "startup|clear|compact"` means the superpowers preamble is
**re-injected after every context compaction** — which is why the
`using-superpowers` skill text reappears in this session after each compaction.

`INFERENCE`. `hooks-cursor.json` is direct evidence that superpowers is designed
for cross-harness portability. Together with the `.kimi-plugin/plugin.json`
tool-name mapping table (see [PLUGINS_INDEX.md](PLUGINS_INDEX.md)), it is the
most migration-relevant artefact in the plugin tree.

---

## 6. Slash commands and subagents

`VERIFIED_FACT`. **No project-level commands or agents.** All come from plugins.

### 6.1 Commands — `commands-backup/`, 20 files

| Source | Count | Commands |
|---|---|---|
| academic-research-skills | 16 | `/ars-3w`, `/ars-abstract`, `/ars-cache-invalidate`, `/ars-citation-check`, `/ars-disclosure`, `/ars-format-convert`, `/ars-full`, `/ars-lit-review`, `/ars-mark-read`, `/ars-outline`, `/ars-plan`, `/ars-rebuttal-audit`, `/ars-reviewer`, `/ars-revision-coach`, `/ars-revision`, `/ars-unmark-read` |
| Claude Desktop pdf-viewer plugin | 4 | `/annotate`, `/fill-form`, `/open`, `/sign` |

`DIRECT_OBSERVATION`. The 16 ARS commands are announced by the SessionStart hook
in every session. **None appears in the 98-entry prompt history** — see
[PROMPTS_AND_WORKFLOWS.md](PROMPTS_AND_WORKFLOWS.md).

### 6.2 Subagents — `agents-backup/`, 45 files

| Source group | Count |
|---|---|
| ARS `academic-paper/agents/` | 12 |
| ARS `academic-paper-reviewer/agents/` | 7 |
| ARS `academic-pipeline/agents/` | 5 |
| ARS top-level `agents/` | 3 (`report_compiler_agent`, `research_architect_agent`, `synthesis_agent`) |
| ARS `deep-research/agents/` | 14 |
| ARS `shared/agents/` | 1 (`compliance_agent`) |
| document-skills `skill-creator` | 3 (`analyzer`, `comparator`, `grader`) |

`DIRECT_OBSERVATION`. Only the three ARS **top-level** agents are exposed to the
Agent tool in this session (`academic-research-skills:report_compiler_agent`,
`:research_architect_agent`, `:synthesis_agent`). The other 42 are nested inside
skill directories and are invoked by those skills, not directly.

`DIRECT_OBSERVATION`. `~/.claude.json` has an `agentLastUsed` key.
**No subagent from any plugin was used in any phase of this project** — all
Phase 4/5/6 work was done by the main instance. The two
`<task-notification> … <status>failed</status>` entries in session `32df42f5`
are the only subagent dispatches on record, and both failed.

---

## 7. `~/.claude/` top-level inventory

`DIRECT_OBSERVATION`, re-verified 2026-09-18:

| Entry | What it is | In backup? |
|---|---|---|
| `backups/` | 5 `.claude.json.backup.*` files | No — same secrets as `.claude.json` |
| `cache/` | `changelog.md` only | No |
| `daemon/` | `control.key`, `pipe.key` | **No — `SECRET PRESENT — NOT EXPORTED`** |
| `daemon.log` | Daemon log | No |
| `downloads/` | `claude-2.1.241-win32-x64.exe` + `.stderr` | No — installer binary |
| `file-history/` | Empty | n/a |
| `history.jsonl` | 51 444 B global prompt history, all projects | **No** — filtered copy only (98 D:\Thesis entries) |
| `ide/` | `16000.lock` | No |
| `jobs/` | Job `10b7b88f/` (Phase 2) | **Partially** → `session-backup/background-job-10b7b88f/` |
| `paste-cache/` | 10 pasted prompt blocks | **Yes** → `session-backup/paste-cache/` |
| `plugins/` | `cache/`, `marketplaces/`, `data/`, `.install-manifests/`, `installed_plugins.json`, `known_marketplaces.json` | **Yes** → `plugins-backup/`, `config-backup/` |
| `projects/` | 20 session transcripts across 3 dirs | **Yes** → `session-backup/` |
| `session-env/` | Empty | n/a |
| `sessions/` | 2 `.key` + `9072.json` | **No — `SECRET PRESENT — NOT EXPORTED`** |
| `settings.json` | User settings | **Yes** → `config-backup/user--claude--settings.json` |
| `shell-snapshots/` | 4 shell environment snapshots | No — machine-specific |
| `stats-cache.json` | Usage statistics (stale, 2026-08-27) | No — transcribed in §3.3 |
| `telemetry/` | 14 `1p_failed_events.*` for session `32df42f5` | No |

`DIRECT_OBSERVATION`. `todos/` existed and was empty on 2026-09-07; on
2026-09-18 it **no longer exists**. Claude Code appears to remove it when empty.

---

## 8. Claude Desktop — a separate installation

`DIRECT_OBSERVATION`. **Two** Claude Desktop configurations exist on this
machine, under different accounts, with different deployment modes. This is not
a duplicate — they are genuinely separate installs.

### 8.1 Roaming install — `%APPDATA%\Claude\`

Copied to `config-backup/desktop-roaming--claude_desktop_config.json` (1 323 B):

| Setting | Value |
|---|---|
| `coworkUserFilesPath` | `C:\Users\ABN\Claude` |
| account | `f5bd7f1b-9c8f-406b-b55c-361505f4d7a6` |
| `sidebarMode` | `"task"` |
| `orgWorkAcrossAppsDisabled` | **`true`** |
| `coworkScheduledTasksEnabled` / `ccdScheduledTasksEnabled` | `false` / `false` |
| `coworkBrowserToolsEnabled` / `coworkWebSearchEnabled` | `true` / `true` |
| `coworkPreferredBrowser` | `"built_in"` |
| `remoteToolsDeviceName` | `"ali-y"` |
| `bypassPermissionsGateByAccount` | `false` |

`config-backup/desktop-roaming--developer_settings.json` (27 B):
`{"allowDevTools": true}`.

`config-backup/desktop-roaming--config.REDACTED.json` (1 314 B) — a redacted copy
of `%APPDATA%\Claude\config.json`. Non-secret fields preserved verbatim:
`updaterLastSeenVersion "1.40609.1"`, `first_launch_at 1787501321692`,
`locale "en-US"`, `userThemeMode "dark"`,
`lastKnownAccountUuid "f5bd7f1b-…"`, `bootFrameLayout {sidebarWidth: 288,
collapsed: false, narrowViewportMaxWidth: 700}`,
`version_first_launch {version "1.40609.1", at 1788288829286}`. **Three keys
replaced with the marker string `"SECRET PRESENT - NOT EXPORTED"`:**
`oauth:tokenCache`, `oauth:tokenCacheV2`,
`dxt:allowlistCache:dd34952f-303f-4ac1-a910-6eec07239b70`. A `_backup_note` field
inside the file records exactly what was redacted.

### 8.2 3p install — `%LOCALAPPDATA%\Claude-3p\`

Copied to `config-backup/desktop-3p--claude_desktop_config.json` (1 797 B):

| Setting | Value |
|---|---|
| `deploymentMode` | **`"3p"`** |
| account | `e9dacc82-0cfe-4352-ba92-d8df277d2a8d` |
| **`localAgentModeTrustedFolders`** | **`["D:\\Thesis"]`** |
| `sidebarMode` | `"epitaxy"` |
| `orgWorkAcrossAppsDisabled` | `false` |
| `coworkScheduledTasksEnabled` | **`true`** |
| `ccdScheduledTasksEnabled` | `false` |
| `cc-landing-worktree-enabled` | `false` |

`VERIFIED_FACT`. **`localAgentModeTrustedFolders: ["D:\\Thesis"]`** — the 3p
Desktop install has this thesis directory explicitly trusted for local agent
mode. This is the Desktop install that touches the project.

### 8.3 Desktop Skills and remote plugins

`DIRECT_OBSERVATION`. Claude Desktop stores Skills under
`local-agent-mode-sessions/skills-plugin/<org>/<account>/` — a **different**
layout from Claude Code's `~/.claude/plugins/cache/`. Contents found:

- `anthropic-skills` **v1.0.0** — 11 skills, 208 files, 4.0 MB. Copied to
  `skills-backup/claude-desktop-skills/anthropic-skills/`.

`DIRECT_OBSERVATION`. A separate `rpm/` (remote-plugin) store holds two plugins
from marketplace `knowledge-work-plugins`:

- **pdf-viewer** — 4 slash commands + 1 stdio MCP server
- **engineering** — 10 HTTP MCP server definitions

Both copied to `plugins-backup/claude-desktop-remote-plugins/` (120 KB); their
MCP manifests also to `mcp-backup/`. Full detail in
[PLUGINS_INDEX.md](PLUGINS_INDEX.md) and
[MCP_AND_INTEGRATIONS.md](MCP_AND_INTEGRATIONS.md).

`DIRECT_OBSERVATION`. `%LOCALAPPDATA%\Claude-3p\ccd-session-secrets\` and
`custom3p-bootstrap-oidc.json` exist and were **not copied** —
`SECRET PRESENT — NOT EXPORTED`. The `Preferences` file's `device_id_salt` was
likewise left in place.

---

## 9. Python environment — the part that actually reproduces the science

### 9.1 `D:\Thesis\.venv` — the project interpreter

`VERIFIED_FACT`. Exact `pip list --format=freeze` output, 2026-09-18:

```
cffi==2.1.1
contourpy==1.3.3
cycler==0.12.1
epyt==2.3.5.2
fonttools==4.64.0
kiwisolver==1.5.1
matplotlib==3.11.1
networkx==3.6.1
numpy==2.5.2
packaging==26.3
pandas==3.0.5
pillow==12.3.0
pip==26.2.1
pycparser==3.0
pyparsing==3.3.2
python-dateutil==2.9.0.post0
scipy==1.18.1
setuptools==84.0.0
six==1.17.0
tzdata==2026.3
wntr==1.5.0
xlsxwriter==3.2.9
```

`VERIFIED_FACT`. **`gymnasium`, `stable-baselines3` and `torch` are ABSENT.** No
RL stack is installed. This is consistent with the Phase 6 constraint that no
PPO training may begin yet, and it is a blocking prerequisite for Phase 6
STEP 11–13. See [ROADMAP.md](ROADMAP.md).

`VERIFIED_FACT`. The two simulator packages are **different engines**:
- `wntr==1.5.0` bundles the **EPANET DLL 20200** (2.2.0) — used for all Phase 5
  and Phase 6 work.
- `epyt==2.3.5.2` wraps **EPANET 2.3.05** — installed but **never
  cross-validated against WNTR**. See [FINDINGS.md](FINDINGS.md).

### 9.2 Interpreter invocation — a portability trap

`DIRECT_OBSERVATION`. A **system Python 3.14 at `C:\Python314`** also exists.

`DIRECT_OBSERVATION`. Under Git Bash on this machine, bare `python3` is
intercepted by the Windows App Execution Alias shim and fails with:

> Python was not found; run without arguments to install from the Microsoft
> Store, or disable this shortcut from Settings > Apps > Advanced app settings >
> App execution aliases.

**The project interpreter must be invoked explicitly as
`D:\Thesis\.venv\Scripts\python.exe`.** Every script in this project depends on
that. See [FAILED_APPROACHES.md](FAILED_APPROACHES.md) for this and the related
heredoc / `/dev/stdin` / UTF-8 shell traps.

---

## 10. Client versions observed

`DIRECT_OBSERVATION`, from transcript `version` fields:

| Version | Sessions |
|---|---|
| 2.1.240 | all early sessions; still present in `32df42f5` |
| 2.1.255 | `4cbcd32e`, `e1b0711e`, `32df42f5` |
| 2.1.257 | `4f550550` |
| 2.1.263 | `32df42f5` (most recent) |

An installer for **2.1.241** sits unused in `~/.claude/downloads/`.

`INFERENCE`. Long-running sessions survive client upgrades in place —
`4f550550` spans 2.1.240 → 2.1.257 and `32df42f5` spans 2.1.240 → 2.1.263.

---

## 11. What does NOT port to another harness

`INFERENCE`. Ranked by how much re-work the loss costs:

| Artefact | Portability | Note |
|---|---|---|
| `CLAUDE.md` / `AGENTS.md` | **Full** | Plain Markdown. Already ported to Codex. |
| The 4 project Skills | **Full** | Plain Markdown + YAML frontmatter. Already ported. |
| `.venv` package pins | **Full** | Reproduce with the freeze list in §9.1. |
| Session transcripts | **Full** | JSONL, harness-independent to read. |
| Plugin skill *content* | **High** | Markdown; superpowers ships 8 harness manifests. |
| Plugin hooks | **Medium** | `${CLAUDE_PLUGIN_ROOT}` and the `PreToolUse`/`SessionStart` event names are Claude-Code-specific; superpowers ships a Cursor variant showing the shape of the translation. |
| ARS slash commands | **Medium** | Markdown bodies port; the `/name` dispatch does not. |
| `settings.local.json` allow-list (149) | **None** | Claude Code permission syntax. Rebuild from scratch. |
| `~/.claude.json` usage counters | **None** | Telemetry, not knowledge. |
| Desktop `rpm/` MCP servers | **Config only** | 11 server definitions port as config; every one needs its own auth. |
| Claude Code's built-in tools and system prompt | **None** | Not exportable files. See [MISSING_OR_UNRECOVERABLE.md](MISSING_OR_UNRECOVERABLE.md). |

---

## 12. Minimum environment to resume this project elsewhere

`INFERENCE`. To pick the project up on another machine or harness you need, in
order:

1. **Python** with the exact `.venv` pins of §9.1 — `wntr==1.5.0` above all,
   because the EPANET DLL version is bundled with it and every Phase 5/6 number
   was produced by that DLL.
2. **`D:\Thesis\data\networks\working\BWSN_Network_1_working.inp`** — the working
   copy, with the `Quality Chemical TIME` → `Quality Chemical mg/L` patch
   applied.
3. **The solver configuration asserted after every load**: `ACCURACY = 1e-5`,
   `TRIALS = 2000`, rule timestep `180 s`, control/report timestep `1800 s`.
   These must never be left to WNTR defaults.
4. **`CLAUDE.md`** (or `AGENTS.md`) as the agent's standing instructions.
5. **The four project Skills** as reference documents, even if the harness has no
   Skill mechanism.
6. *Nothing else.* No plugin, no MCP server, no hook and no Desktop feature was
   load-bearing for any scientific result in this project.

`VERIFIED_FACT` for point 6: the only Skill ever formally invoked was
`research-review` (once, Phase 1); no subagent produced any surviving artefact;
zero MCP servers were configured in Claude Code; and every Phase 4/5/6 number was
produced by direct `python.exe` invocations against WNTR.
