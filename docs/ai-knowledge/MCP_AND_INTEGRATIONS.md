# MCP_AND_INTEGRATIONS.md — Model Context Protocol servers and external integrations

**Governing rule (PART P of the backup request):**

> "**NEVER copy:** API keys, passwords, access tokens, OAuth secrets, cookies,
> session tokens, private credentials. Instead record
> `SECRET PRESENT — NOT EXPORTED`. Preserve non-secret configuration where safe."

That rule was applied. Every configuration value reproduced below is
non-secret: public endpoint URLs, public OAuth client IDs, port numbers and
package names. **No token, key, cookie or credential from any store was copied
into this backup.** The enumerated secrets left behind are listed in §7.

---

## 1. Headline finding: Claude Code has ZERO MCP servers

`VERIFIED_FACT`, measured 2026-09-18 by reading the live configuration files:

| Scope | Key | Value |
|---|---|---|
| `~/.claude.json` top level | `mcpServers` | **`null`** |
| `~/.claude.json` top level | any key containing "mcp" | **none** |
| `~/.claude.json` → `projects["d:/Thesis"]` | `mcpServers` | **`{}`** |
| `~/.claude.json` → `projects["D:/Thesis"]` | `mcpServers` | **`{}`** |
| `~/.claude.json` → `projects["C:/Users/ABN"]` | `mcpServers` | **`{}`** |
| `~/.claude.json` → `projects["C:/Users/ABN/Desktop"]` | `mcpServers` | **`{}`** |
| `~/.claude.json` → `projects["D:\\Thesis"]` | `mcpServers` | **key absent entirely** |
| all five project keys | `enabledMcpjsonServers` | **`[]`** |
| all five project keys | `disabledMcpjsonServers` | **`[]`** |
| `~/.claude/settings.json` | any key containing "mcp" | **none** (keys are `model`, `enabledPlugins`, `extraKnownMarketplaces`, `modelSettings`, `theme`) |
| `D:\Thesis\.claude\settings.local.json` | top-level keys | **`["permissions"]`** only — no MCP key of any kind |
| `D:\Thesis\.mcp.json` | — | **does not exist** |
| anywhere in `D:\Thesis` (depth 3) | any `*mcp*` file | **none** outside this backup |

`INFERENCE`. **Not one Claude Code result in this project came through an MCP
server.** Every fact in `FINDINGS.md` and `EXPERIMENTS.md` was produced by direct
`Bash` invocations of `D:\Thesis\.venv\Scripts\python.exe` against WNTR, by
`Read`/`Grep`/`Glob` over local files, or by `WebSearch`/`WebFetch` — which are
built-in tools, not MCP.

`INFERENCE`. **A migrating agent needs no MCP server to resume this project.**
See [CLAUDE_ENVIRONMENT.md](CLAUDE_ENVIRONMENT.md) §12 for the six-item minimum
environment.

---

## 2. The only MCP configuration on this machine: two Claude Desktop plugins

`DIRECT_OBSERVATION`. Exactly two `.mcp.json` files exist in any Claude
directory on this machine. Both ship inside Claude **Desktop** remote plugins,
are invisible to Claude Code, and were never used in this project. Both are
copied verbatim to `mcp-backup/`.

Original locations:

```
C:\Users\ABN\AppData\Roaming\Claude\local-agent-mode-sessions\
  f5bd7f1b-9c8f-406b-b55c-361505f4d7a6\dd34952f-303f-4ac1-a910-6eec07239b70\rpm\
    plugin_011v5h6QUzBZvas64y44XLhy\.mcp.json     (pdf-viewer)
    plugin_01FTLa86dhbVJ3HB1LdHdhN7\.mcp.json     (engineering)
```

### 2.1 pdf-viewer — 1 stdio server

`mcp-backup/desktop-plugin-pdf-viewer.mcp.json`, verbatim:

```json
{
  "mcpServers": {
    "pdf": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-pdf", "--stdio"]
    }
  }
}
```

| Field | Value |
|---|---|
| Transport | **stdio** (local subprocess) |
| Launcher | `npx -y @modelcontextprotocol/server-pdf --stdio` |
| Credentials required | **none** |
| Network dependency | npm registry, at first launch only |
| Portable? | **Yes** — any MCP-capable harness with Node can run this line unchanged |

`INFERENCE`. This is the **only MCP server in the whole backup that a migrating
agent could stand up immediately**, because it needs no account and no token.
Whether it is *useful* is a separate question: the project's 42 PDFs were read
through Claude Code's own PDF handling, not through this server.

### 2.2 engineering — 10 HTTP servers, all needing their own auth

`mcp-backup/desktop-plugin-engineering.mcp.json`, verbatim:

```json
{
  "mcpServers": {
    "slack": {
      "type": "http",
      "url": "https://mcp.slack.com/mcp",
      "oauth": {
        "clientId": "1601185624273.8899143856786",
        "callbackPort": 3118
      }
    },
    "linear":     { "type": "http", "url": "https://mcp.linear.app/mcp" },
    "asana":      { "type": "http", "url": "https://mcp.asana.com/v2/mcp" },
    "atlassian":  { "type": "http", "url": "https://mcp.atlassian.com/v1/mcp" },
    "notion":     { "type": "http", "url": "https://mcp.notion.com/mcp" },
    "github":     { "type": "http", "url": "https://api.githubcopilot.com/mcp/" },
    "pagerduty":  { "type": "http", "url": "https://mcp.pagerduty.com/mcp" },
    "datadog":    { "type": "http", "url": "https://mcp.datadoghq.com/api/unstable/mcp-server/mcp" },
    "google calendar": { "type": "http", "url": "" },
    "gmail":           { "type": "http", "url": "" }
  }
}
```

| Server | Endpoint | Auth | Usable after migration? |
|---|---|---|---|
| `slack` | `https://mcp.slack.com/mcp` | OAuth | Only after the user authorises a Slack workspace |
| `linear` | `https://mcp.linear.app/mcp` | account | No, without a Linear account |
| `asana` | `https://mcp.asana.com/v2/mcp` | account | No |
| `atlassian` | `https://mcp.atlassian.com/v1/mcp` | account | No |
| `notion` | `https://mcp.notion.com/mcp` | account | No |
| `github` | `https://api.githubcopilot.com/mcp/` | GitHub Copilot | No |
| `pagerduty` | `https://mcp.pagerduty.com/mcp` | account | No |
| `datadog` | `https://mcp.datadoghq.com/api/unstable/mcp-server/mcp` | account | No |
| `google calendar` | **`""` — empty** | — | **Not configured** |
| `gmail` | **`""` — empty** | — | **Not configured** |

`DIRECT_OBSERVATION`. The Slack `clientId` `1601185624273.8899143856786` is a
**public OAuth client identifier**, not a secret — it is the value a client app
presents before the user authorises it, and it is embedded in the plugin as
shipped by Anthropic. It is preserved here under the PART P allowance to
"preserve non-secret configuration where safe". **No Slack token, refresh token
or authorisation code appears anywhere in this backup.**

`DIRECT_OBSERVATION`. Two servers ship with **empty `url` strings**. They are
declarations without endpoints — the plugin expects the Desktop connector UI to
fill them in. Neither was ever connected.

`INFERENCE`. **Eleven MCP servers are declared across both plugins; nine of the
ten HTTP ones require credentials this backup deliberately does not carry, and
two of those ten have no endpoint at all.** Only the stdio `pdf` server is
immediately runnable.

---

## 3. Claude Desktop's own MCP state

### 3.1 `mcp-user-tool-toggles.json` — 143 B

`mcp-backup/desktop-3p--mcp-user-tool-toggles.json`, verbatim:

```json
{
  "v": 3,
  "owners": {
    "3p": [
      "local:mcp-registry:search_mcp_registry",
      "local:mcp-registry:suggest_connectors"
    ]
  }
}
```

`DIRECT_OBSERVATION`. Two tools are toggled on, both belonging to a **local MCP
registry** (`search_mcp_registry`, `suggest_connectors`). These are Claude
Desktop's built-in discovery tools for *finding* connectors — not connectors
themselves. **No third-party MCP server is enabled here.**

### 3.2 `extensions-blocklist.json` — 177 B

`config-backup/desktop-roaming--extensions-blocklist.json`, verbatim:

```json
[
  {
    "entries": [],
    "lastUpdated": "2026-09-01T19:01:43.697Z",
    "url": "https://claude.ai/api/organizations/dd34952f-303f-4ac1-a910-6eec07239b70/dxt/blocklist"
  }
]
```

`DIRECT_OBSERVATION`. The blocklist is **empty**; nothing has been blocked. The
`dd34952f-…` value is the organisation ID, which also appears in the Roaming
install's plugin path. Recorded as a non-secret identifier.

### 3.3 No `claude_desktop_config.json` MCP block

`DIRECT_OBSERVATION`. Both Desktop installs' `claude_desktop_config.json` were
read in full (quoted in [CLAUDE_ENVIRONMENT.md](CLAUDE_ENVIRONMENT.md) §8).
**Neither contains an `mcpServers` key.** They hold only UI preferences, the
Cowork file path, per-account toggles and the `localAgentModeTrustedFolders`
list — which contains exactly one entry, `"D:\\Thesis"`.

---

## 4. Non-MCP integrations that DID matter

`DIRECT_OBSERVATION`. The project's only genuine external dependencies were
built-in tools, not integrations:

| Capability | Mechanism | Used for |
|---|---|---|
| Web search | Claude Code built-in `WebSearch` | Phase 1.5 / 1.5-B / 2 literature work; DOI and venue verification |
| Web fetch | Claude Code built-in `WebFetch` | retrieving paper metadata and abstracts |
| Local execution | built-in `Bash` → `D:\Thesis\.venv\Scripts\python.exe` | **every hydraulic result in the thesis** |
| Local file I/O | built-in `Read`/`Write`/`Edit`/`Grep`/`Glob` | corpus, reports, network files |
| Version control | `git` via `Bash` | 3 commits on `main` |

`VERIFIED_FACT` from the Desktop usage ledger (§5): across the 10 recorded turn
blocks the tool mix was `Bash` 400, `Edit` 234, `Read` 53, `WebSearch` 52,
`WebFetch` 44, `Write` 32, `Agent` 13, `Grep` 7, `Glob` 4 — **and zero MCP tool
calls of any kind.**

---

## 5. ⚠ NEW — the Desktop usage ledger, a live telemetry source found 2026-09-18

`DIRECT_OBSERVATION`. Four `.ndjson` files were found at

```
C:\Users\ABN\AppData\Local\Claude-3p\local-agent-mode-sessions\
  e9dacc82\00000000\usage-ledger\{2026-09-01,-02,-03,-07}.ndjson
```

and copied to `config-backup/desktop-3p-usage-ledger/`. They contain **no
credentials** — only per-turn token counts, tool-call counts and list-basis cost.

Aggregate over all four files (10 turn-block records, 2 session IDs
`local_2f9ccf61-…` and `local_b46ed63f-…`):

| Metric | Value |
|---|---|
| Input tokens | 66 003 261 |
| Output tokens | 834 757 |
| Cache-read tokens | 7 423 274 |
| Cache-write tokens | 18 430 504 |
| Web-search requests | 50 |
| Cost (list basis) | **USD 470.29** |

Per day: 2026-09-01 → 3 records / \$39.15; 2026-09-02 → 2 / \$62.47;
2026-09-03 → 2 / \$243.18; 2026-09-07 → 3 / \$125.49.

`INFERENCE`. This ledger covers the **Phase 4–6 Code-tab work** and is therefore
the complement to `~/.claude/stats-cache.json`, which is frozen at 2026-08-27 and
covers only Phases 1–2. Neither is a complete project total: the ledger records
only four days and only the Desktop `3p` account, and no record exists for
2026-09-18. **Do not cite either as a project total.**

`OPEN_QUESTION`. Why only four days are recorded, and whether a matching ledger
exists for the Roaming install, was not determined.

---

## 6. ⚠ NEW — two Claude Desktop session transcripts, found and backed up 2026-09-18

`DIRECT_OBSERVATION`. Two previously-unindexed Desktop transcripts were found
under `Claude-3p\local-agent-mode-sessions\e9dacc82\00000000\<session>\.claude\projects\session\`
and copied to `session-backup/claude-desktop-transcripts/`:

| File | Bytes | Lines | Timestamp | Content |
|---|---|---|---|---|
| `ce2196aa-caa8-4f83-94a5-6d08fafc3bdd.jsonl` | 11 995 | 9 | 2026-09-06T19:31:32Z | prompt `hi`; assistant reply is `API Error: 402 Budget pool quota has been exhausted` |
| `31ef5175-4d1d-477a-b543-6cb364147ee2.jsonl` | 13 040 | 9 | 2026-09-06T19:55:39Z | prompt asking to "Schedule a daily briefing that reaches me every morning…"; same 402 error |

Their two `audit.jsonl` files (9 123 B and 8 277 B) were copied alongside as
`d363756e--audit.jsonl` and `d79b6d6a--audit.jsonl`.

`DIRECT_OBSERVATION`. **Neither is thesis-related.** Both are Claude Desktop
local-agent-mode sessions that failed immediately with a budget error and
produced no work. They are in the backup because the instruction was
preservation, not curation — the same rule applied to the nine stub transcripts
in [SESSION_HISTORY.md](SESSION_HISTORY.md) §2.

`DIRECT_OBSERVATION`. Their sibling `.audit-key` files were **NOT copied** —
`SECRET PRESENT — NOT EXPORTED`.

`DIRECT_OBSERVATION`. The `memory/memory/` directory beside them is **empty**
(0 files), consistent with [MEMORY_BACKUP.md](MEMORY_BACKUP.md) §1: no
persistent memory exists in any store, Code or Desktop.

---

## 7. Secrets found and deliberately NOT exported

`DIRECT_OBSERVATION`. Every item below was located on disk and left in place.
Each is recorded as **`SECRET PRESENT — NOT EXPORTED`**.

| Location | What it holds |
|---|---|
| `~/.claude/daemon/control.key` | daemon control secret |
| `~/.claude/daemon/pipe.key` | daemon pipe secret |
| `~/.claude/sessions/*.key` (2 files) | session secrets |
| `~/.claude.json` → `userID` | account identifier |
| `~/.claude.json` → `machineID` | machine identifier |
| `~/.claude/backups/*.backup.*` (5 files) | full copies of `~/.claude.json`, therefore of the two IDs above |
| Roaming `config.json` → keys beginning `oauth:` | OAuth token caches (`oauth:tokenCache`, `oauth:tokenCacheV2`) |
| Roaming `config.json` → `dxt:allowlistCache:dd34952f-…` | opaque cache blob |
| `Claude-3p\ccd-session-secrets\` | per-session secrets |
| `Claude-3p\custom3p-bootstrap-oidc.json` | OIDC bootstrap material |
| `Claude-3p\host-creds-dae3e33d-fe65-44df-ab99-46538de53fba.json` | host credentials |
| `Claude-3p\...\<session>\.audit-key` (2 files) | audit signing keys |
| `Preferences` → `device_id_salt` (both installs) | device fingerprint salt |
| `~/.claude/history.jsonl` (51 444 B) | not a keystore, but may echo secrets typed into prompts from unrelated sessions — excluded on precaution |

The single redaction actually performed inside a copied file is recorded in
`config-backup/desktop-roaming--config.REDACTED.json` under its own
`_backup_note`, which names exactly the three keys replaced and states that
everything else in that file is verbatim.

---

## 8. Instructions to the migrating agent

`INFERENCE`, in order:

1. **Configure no MCP server to resume this project.** Zero were used; zero are
   needed. The hydraulic work is `python.exe` + WNTR 1.5.0 + EPANET.
2. **If you want the PDF server**, the one runnable line is
   `npx -y @modelcontextprotocol/server-pdf --stdio`. It needs no credentials.
   It was never used here.
3. **Do not attempt to restore the engineering plugin's ten HTTP servers.** They
   are Slack/Linear/Asana/Atlassian/Notion/GitHub/PagerDuty/Datadog endpoints
   from an unrelated Anthropic plugin, two of them with empty URLs, none ever
   connected, and every one gated behind an account this project does not have.
4. **Every credential must be re-issued by the user on the new machine.** Nothing
   in §7 travels with this backup, by design.
5. **`WebSearch` and `WebFetch` are the two external capabilities that actually
   mattered** — 52 and 44 calls respectively in the recorded window. If the
   destination harness names them differently, remap them; the superpowers
   `.kimi-plugin` mapping table in [PLUGINS_INDEX.md](PLUGINS_INDEX.md) §3.2
   shows the pattern (`WebFetch` → `FetchURL` in that harness).
