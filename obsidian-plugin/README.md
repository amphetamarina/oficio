# Ofício Trigger — Obsidian Plugin

Watches vault modifications and automatically launches your coding agent when
a daily note contains unchecked `@agent` requests without a `Status:` line.
The agent is expected to be configured separately to speak to the ofício MCP
server (`oficio-mcp`).

## How it works

1. Listens to `vault.on('modify')` events.
2. Filters for daily notes (`Daily/YYYY-MM-DD.md` — folder configurable).
3. 5-minute debounce per file, plus a 2-second save-settle window.
4. Checks for an unchecked `- [ ] @agent` (marker configurable) without a
   `Status:` line.
5. Spawns the configured agent command. The trigger does not write to the
   vault — the agent does, through the ofício MCP tools.

A new session ID (`obsidian_<base36 timestamp>`) is exported as
`OFICIO_SESSION_ID` for each launch so the agent can echo it back via
`oficio_start` / `oficio_complete`.

## Settings

Open *Settings → Community plugins → Ofício Trigger → Options*:

| setting | what it does | default |
|---|---|---|
| **Agent marker** | text that marks a task as an agent request | `@agent` |
| **Agent command** | executable to run (e.g. `claude`, `codex`, `opencode`) | *(empty — required)* |
| **Agent arguments** | space-separated argv; `{prompt}`, `{filePath}`, `{sessionId}` are substituted | *(empty — passes prompt as a single positional argument)* |
| **Prompt template** | sent to the agent; `{filePath}` and `{marker}` are substituted | sensible default |
| **Daily folder** | vault-relative folder to watch | `Daily` |

### Examples

**Claude Code:** `claude` with args `-p "{prompt}"`

**OpenAI Codex:** `codex` with args `-p "{prompt}"`

**OpenCode:** `opencode` with args `run "{prompt}"`

## Installation

Replace `/path/to/vault`:

```bash
mkdir -p /path/to/vault/.obsidian/plugins
rm -rf /path/to/vault/.obsidian/plugins/oficio-trigger
ln -s ~/git/oficio/obsidian-plugin /path/to/vault/.obsidian/plugins/oficio-trigger
```

Then enable **Ofício Trigger** in Obsidian → *Settings → Community plugins*.

## Requirements

- Obsidian desktop (uses `child_process.spawn`).
- Your agent CLI on `PATH`, connected to the ofício MCP server (see the repo
  `README.md`).
