from __future__ import annotations

from typing import Any

try:
    from .oficio_config import load_config
    from .oficio_tool_schemas import JsonDict
    from .oficio_tools import OficioTools
except Exception:  # pragma: no cover - direct import mode
    from oficio_config import load_config
    from oficio_tool_schemas import JsonDict
    from oficio_tools import OficioTools


TOOLS = OficioTools()


def _handle_config(args: JsonDict, **kw: Any) -> str:
    return TOOLS.config(args, **kw)


def _handle_scan(args: JsonDict, **kw: Any) -> str:
    return TOOLS.scan(args, **kw)


def _handle_read(args: JsonDict, **kw: Any) -> str:
    return TOOLS.read(args, **kw)


def _handle_today(args: JsonDict, **kw: Any) -> str:
    return TOOLS.today(args, **kw)


def _handle_start(args: JsonDict, **kw: Any) -> str:
    return TOOLS.start(args, **kw)


def _handle_complete(args: JsonDict, **kw: Any) -> str:
    return TOOLS.complete(args, **kw)


def _handle_fail(args: JsonDict, **kw: Any) -> str:
    return TOOLS.fail(args, **kw)


def _handle_replace(args: JsonDict, **kw: Any) -> str:
    return TOOLS.replace(args, **kw)


def _slash(raw_args: str) -> str:
    return TOOLS.slash(raw_args)


def register(ctx) -> None:
    load_config()
    for spec in TOOLS.tool_specs():
        ctx.register_tool(spec.name, "oficio", spec.schema, spec.handler, emoji="📝")

    ctx.register_command(
        "oficio",
        _slash,
        description="Scan and inspect the ofício Obsidian command surface.",
        args_hint="scan|config|status|today|start|complete|fail",
    )
