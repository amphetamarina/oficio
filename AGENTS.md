# AGENTS.md

Conventions for AI agents (Claude Code, Codex, OpenCode, Cursor, …) working
in this repository.

## What this project is

ofício is an agent-agnostic interface between an Obsidian daily note and a
coding agent. Two surfaces ship from this repository:

1. **`oficio-mcp`** — an MCP stdio server (the single integration point).
2. **Obsidian Trigger** — a small JS plugin in `obsidian-plugin/` that
   watches daily notes and launches a configured agent CLI.

The Python package is published to PyPI from `src/oficio/`.

## Project layout

```
.
├── mise.toml              # Toolchain pins + task runner
├── pyproject.toml         # Packaging, ruff, pytest, pyright
├── src/oficio/            # Importable Python package + MCP server
├── tests/                 # pytest suite
├── .github/workflows/     # CI + Trusted Publishing
└── obsidian-plugin/       # Obsidian-side trigger
```

Edit code under `src/oficio/`. There is no Hermes shim and no root-level
Python — the MCP server is the only integration point.

## Toolchain

Canonical toolchain: `mise` + `uv` + `ruff` (+ `pyright` optional).

```bash
mise install
mise run install
mise run check        # ruff check + pytest
mise run format
mise run build
```

If `mise` is unavailable, the equivalent `uv` commands in `mise.toml` work
verbatim.

## Before opening a PR

1. `mise run format`
2. `mise run check`
3. Confirm the MCP server boots: `uv run python -c "from oficio.mcp import build_server; build_server()"`

## Code style (modern Python, 3.11+)

- No `from __future__ import annotations` (PEP 649 ships in 3.14; we don't
  need string-mode annotations on 3.11–3.13).
- `X | None` over `Optional[X]`. Lowercase `list[int]`, `dict[str, Any]`.
- `from collections.abc import Iterable, Mapping, Sequence` for ABCs.
- `@dataclass(slots=True, frozen=True, kw_only=True)` for new value objects
  where appropriate.
- `match`/`case` for tagged-union-style dispatch.
- `pathlib.Path` over `os.path`. `tomllib` over third-party TOML.
- Public names live in `src/oficio/__init__.py` and `src/oficio/protocol.py`.
- Avoid `try / except ImportError` fallback blocks — the package is real.
- Comments only when they explain a non-obvious *why*.

## Tests

`tests/` exercises scenarios end-to-end through `oficio.*` and the MCP
server. Add new behaviour there in the same scenario style.

```bash
uv run pytest
```

## MCP contract

`src/oficio/mcp.py` exposes the eight tools via the `FastMCP` SDK on stdio.
Each tool returns the JSON envelope produced by `OficioTools` — same shape
across every agent.

Adding a tool:

1. Implement the behaviour in `src/oficio/tools.py`.
2. Register a `@server.tool(...)` wrapper in `src/oficio/mcp.py`.
3. Cover it in `tests/`.

## Configurable surface

- `OFICIO_AGENT_MARKER` (default `@agent`) — text that marks a task as an
  agent request. The marker only constrains the trigger and the regex that
  inserts an `id:`; everything else is marker-agnostic.
- `OFICIO_SESSION_ID` — echoed back inline as `Session:`.

If you add a new env var, document it in `DEVELOPMENT.md` and surface a
sensible default.

## Versioning & publishing

- Bump `version` in both `pyproject.toml` and `src/oficio/__init__.py`
  (`__version__`). They must match.
- Tag releases as `vX.Y.Z` and create a GitHub release.
- `.github/workflows/publish.yml` builds and publishes via PyPI Trusted
  Publishing (OIDC, no long-lived tokens) with Sigstore attestations.

## When in doubt

- `README.md` — user-visible gesture, MCP one-liner.
- `DEVELOPMENT.md` — moving parts, env vars, publishing.
- `mise run check` passing is necessary; if the change touches the MCP
  server, smoke-test it too.
