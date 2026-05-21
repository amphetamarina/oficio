# ofício
  [![PyPI version](https://img.shields.io/pypi/v/oficio.svg)](https://pypi.org/project/oficio/)
  [![Python versions](https://img.shields.io/pypi/pyversions/oficio.svg)](https://pypi.org/project/oficio/)
  [![License](https://img.shields.io/pypi/l/oficio.svg)](https://github.com/marinaleitecabrera/oficio/blob/main/LICENSE)

Write `- [ ] @agent <request>` in today's Obsidian daily note. Your coding
agent answers in place. That's it.

```markdown
- [x] @agent id:20260520-1 summarize the notes from this meeting.
  Status: completed - summary written | Session: 20260520_…
  Agent response:
  ## Summary
  - The main decision was…
```

Unchecked = open, checked = closed, trace stays visible.

## Setup

Add `oficio-mcp` to your MCP-capable agent (Claude Code, Codex, OpenCode,
Cursor, Continue, Zed, …):

```jsonc
{
  "mcpServers": {
    "oficio": { "command": "uvx", "args": ["--from", "oficio", "oficio-mcp"] }
  }
}
```

That's the whole integration. Eight tools land in your agent
(`oficio_scan`, `oficio_start`, `oficio_complete`, …).

## Optional: trigger automatically from Obsidian

A small companion plugin watches daily notes and launches your agent when it
sees a pending `@agent` task:

```bash
git clone https://github.com/amphetamarina/oficio ~/git/oficio
ln -s ~/git/oficio/obsidian-plugin /path/to/vault/.obsidian/plugins/oficio-trigger
```

Enable **Ofício Trigger** in Obsidian → *Settings → Community plugins*, then
set your agent CLI (`claude`, `codex`, `opencode`, …) in its settings tab.

## Why

ofício keeps the agent inside the texture of daily notes, where context,
memory, and unfinished work already live. One repeated shape — checkbox in,
status + response out — instead of another inbox to remember.

## More

- [DEVELOPMENT.md](DEVELOPMENT.md) — local setup, env vars, tool reference, publishing.
- [AGENTS.md](AGENTS.md) — conventions when an AI agent edits this repo.

MIT.
