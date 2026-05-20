"""MCP server exposing ofício tools over stdio.

Lets Claude Code, Codex, OpenCode, Cursor, and any other MCP-capable agent
drive the same tool surface the Hermes plugin provides:

    oficio-mcp

Each tool returns the JSON envelope produced by ``OficioTools`` — identical to
what the Hermes plugin returns, so prompts and post-processing transfer
unchanged between agents.
"""

from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import load_config
from .tools import OficioTools

_TOOLS = OficioTools()


def _drop_none(args: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in args.items() if value is not None}


def build_server() -> FastMCP:
    server = FastMCP("oficio")

    @server.tool(description="Show the active ofício configuration paths.")
    def oficio_config_show() -> str:
        return _TOOLS.config({})

    @server.tool(description="Scan the daily note for pending '- [ ] @agent ...' requests.")
    def oficio_scan(path: str | None = None) -> str:
        return _TOOLS.scan({"path": path} if path else {})

    @server.tool(description="Read a vault note (vault-relative path).")
    def oficio_read(path: str) -> str:
        return _TOOLS.read({"path": path})

    @server.tool(description="Show today's resolved ofício daily note path.")
    def oficio_today() -> str:
        return _TOOLS.today({})

    @server.tool(description="Mark an ofício request as 'in progress' with inline Status.")
    def oficio_start(
        id: str,
        path: str | None = None,
        session_id: str | None = None,
        line: int | None = None,
    ) -> str:
        return _TOOLS.start(_drop_none({"id": id, "path": path, "session_id": session_id, "line": line}))

    @server.tool(
        description="Mark an ofício request complete with inline Status and an optional Agent response block.",
    )
    def oficio_complete(
        id: str,
        note: str,
        path: str | None = None,
        response: str | None = None,
        session_id: str | None = None,
        line: int | None = None,
    ) -> str:
        return _TOOLS.complete(
            _drop_none(
                {
                    "id": id,
                    "note": note,
                    "path": path,
                    "response": response,
                    "session_id": session_id,
                    "line": line,
                }
            )
        )

    @server.tool(description="Mark an ofício request failed with inline Status.")
    def oficio_fail(
        id: str,
        error: str,
        path: str | None = None,
        session_id: str | None = None,
        line: int | None = None,
    ) -> str:
        return _TOOLS.fail(_drop_none({"id": id, "error": error, "path": path, "session_id": session_id, "line": line}))

    @server.tool(description="Safely replace one exact string in a vault note.")
    def oficio_replace(path: str, old: str, new: str) -> str:
        return _TOOLS.replace({"path": path, "old": old, "new": new})

    return server


def main() -> None:
    """Console entry point (``oficio-mcp``). Runs the server on stdio."""
    load_config()
    build_server().run()


if __name__ == "__main__":
    main()
