# development

## Requirements

- Obsidian desktop, with daily notes shaped like `Daily/YYYY-MM-DD.md`.
- Python 3.11+ (3.13 recommended).
- An MCP-capable agent (Claude Code, Codex, OpenCode, Cursor, Continue, Zed, …).

## Layout

```
.
├── mise.toml              # Toolchain (python, uv) + task runner
├── pyproject.toml         # PyPI packaging, ruff, pytest, pyright
├── src/oficio/            # Python package (publishable to PyPI)
│   ├── __init__.py
│   ├── _result.py         # JSON envelope
│   ├── config.py
│   ├── obsidian.py        # vault read/write (obsidian-cli or direct FS)
│   ├── protocol.py        # public API surface
│   ├── request_blocks.py
│   ├── request_document.py
│   ├── request_ids.py     # marker + auto-id + slug helpers
│   ├── response_block.py
│   ├── sessions.py        # OFICIO_SESSION_ID resolution
│   ├── tools.py           # OficioTools — JSON-returning operations
│   └── mcp.py             # MCP stdio server (oficio-mcp)
├── tests/
├── .github/workflows/     # ci.yml + publish.yml (Trusted Publishing)
└── obsidian-plugin/       # Obsidian companion plugin (JS)
```

## Toolchain

Pinned via `mise.toml`: Python 3.13 + `uv`. Linting/formatting via `ruff`.
Optional typecheck via `pyright`.

```bash
mise install              # python 3.13 + uv
mise run install          # uv sync --all-extras
mise run check            # ruff check + pytest
mise run format           # ruff format
mise run build            # uv build → dist/
```

Plain `uv` works the same:

```bash
uv sync --all-extras
uv run pytest
uv run ruff check .
uv run ruff format .
uv run pyright
uv build
```

## MCP server

```bash
uvx --from oficio oficio-mcp    # installs and runs in one step
# or, from a checkout:
uv run oficio-mcp
```

Stdio transport. Wire it into Claude Code, Codex, OpenCode, Cursor, Continue,
Zed, etc. by adding an entry to that client's MCP config:

```jsonc
{
  "mcpServers": {
    "oficio": { "command": "uvx", "args": ["--from", "oficio", "oficio-mcp"] }
  }
}
```

## Tools

| tool | what it does |
|---|---|
| `oficio_scan` | finds pending `@agent` requests in the daily note |
| `oficio_read` | reads a vault note |
| `oficio_start` | writes `Status: in progress` without checking the box |
| `oficio_complete` | checks the box, writes `Status: completed`, can add `Agent response:` |
| `oficio_fail` | checks the box, writes `Status: failed` |
| `oficio_replace` | replaces one exact string in one note |
| `oficio_today` | shows today's daily note path |
| `oficio_config_show` | shows the active configuration |

## Environment variables

| var | default | meaning |
|---|---|---|
| `OFICIO_AGENT_MARKER` | `@agent` | text that marks a task as an agent request |
| `OFICIO_SESSION_ID` | *(empty)* | string echoed back inline as `Session:` |
| `OFICIO_CONFIG_DIR` | `<vault>/agent/oficio` | where `config.yaml` lives |
| `OBSIDIAN_CLI` | `obsidian-cli` on PATH | binary used for vault read/write |

## Obsidian trigger

The companion plugin watches `Daily/YYYY-MM-DD.md` and launches your
configured agent CLI when it sees a pending `@agent` request. Configuration
lives in *Settings → Community plugins → Ofício Trigger*. See
[obsidian-plugin/README.md](obsidian-plugin/README.md).

The trigger does not edit the vault — the agent does, through the MCP tools.

## Publishing to PyPI

`.github/workflows/publish.yml` uses **PyPI Trusted Publishing** (OIDC) and
generates Sigstore attestations — no long-lived API tokens.

1. On https://pypi.org/manage/account/publishing/, register
   `amphetamarina/oficio` (workflow `publish.yml`, environment `pypi`) as a
   trusted publisher.
2. Create a GitHub release (tag `vX.Y.Z`). The workflow builds and publishes
   with attestations automatically.

Bump `version` in **both** `pyproject.toml` and `src/oficio/__init__.py`
(`__version__`).
