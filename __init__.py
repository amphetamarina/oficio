from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

try:
    from tools.registry import tool_error, tool_result
except Exception:  # pragma: no cover - lets tests/imports run outside Hermes
    import json

    def tool_result(payload: Any) -> str:
        return json.dumps(payload, ensure_ascii=False)

    def tool_error(message: str, **extra: Any) -> str:
        payload = {"success": False, "error": message}
        payload.update(extra)
        return json.dumps(payload, ensure_ascii=False)

try:
    from .oficio_config import load_config, vault_abspath
    from .oficio_obsidian import append_note, read_note
    from .oficio_protocol import find_pending_requests
except Exception:  # pragma: no cover - direct import mode
    from oficio_config import load_config, vault_abspath
    from oficio_obsidian import append_note, read_note
    from oficio_protocol import find_pending_requests

CONFIG_SCHEMA = {
    "name": "oficio_config_show",
    "description": "Show the active ofício configuration paths.",
    "parameters": {"type": "object", "properties": {}},
}

SCAN_SCHEMA = {
    "name": "oficio_scan",
    "description": "Scan the ofício inbox for pending '- [ ] @hermes id:...' requests.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Vault-relative Markdown path. Defaults to configured inbox_path."}
        },
    },
}

READ_SCHEMA = {
    "name": "oficio_read",
    "description": "Read a vault note through obsidian-cli, using a vault-relative path.",
    "parameters": {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
}

APPEND_SCHEMA = {
    "name": "oficio_append",
    "description": "Append text to a vault note through obsidian-cli, using a vault-relative path.",
    "parameters": {
        "type": "object",
        "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
        "required": ["path", "content"],
    },
}


def _handle_config(args: Dict[str, Any], **kw: Any) -> str:
    return tool_result({"success": True, "config": load_config()})


def _handle_scan(args: Dict[str, Any], **kw: Any) -> str:
    cfg = load_config()
    path = str(args.get("path") or cfg["inbox_path"])
    try:
        text = read_note(path)
    except Exception:
        # If Obsidian is not running or CLI is unavailable, fall back to direct file read.
        target = vault_abspath(cfg, path)
        if not target.exists():
            return tool_error(f"note not found: {path}")
        text = target.read_text()
    pending = find_pending_requests(path, text)
    return tool_result({"success": True, "path": path, "pending": pending, "count": len(pending)})


def _handle_read(args: Dict[str, Any], **kw: Any) -> str:
    path = str(args.get("path") or "").strip()
    if not path:
        return tool_error("path is required")
    try:
        return tool_result({"success": True, "path": path, "content": read_note(path)})
    except Exception as exc:
        return tool_error(f"oficio_read failed: {exc}")


def _handle_append(args: Dict[str, Any], **kw: Any) -> str:
    path = str(args.get("path") or "").strip()
    content = str(args.get("content") or "")
    if not path:
        return tool_error("path is required")
    if not content:
        return tool_error("content is required")
    try:
        result = append_note(path, content)
        return tool_result({"success": True, "path": path, "result": result})
    except Exception as exc:
        return tool_error(f"oficio_append failed: {exc}")


def _slash(raw_args: str) -> str:
    argv = raw_args.strip().split()
    sub = argv[0] if argv else "scan"
    if sub in {"config", "status"}:
        return _handle_config({})
    if sub == "scan":
        path = argv[1] if len(argv) > 1 else ""
        return _handle_scan({"path": path} if path else {})
    return "Usage: /oficio [scan [path]|config|status]"


def register(ctx) -> None:
    load_config()
    ctx.register_tool("oficio_config_show", "oficio", CONFIG_SCHEMA, _handle_config, emoji="📝")
    ctx.register_tool("oficio_scan", "oficio", SCAN_SCHEMA, _handle_scan, emoji="📝")
    ctx.register_tool("oficio_read", "oficio", READ_SCHEMA, _handle_read, emoji="📝")
    ctx.register_tool("oficio_append", "oficio", APPEND_SCHEMA, _handle_append, emoji="📝")
    ctx.register_command("oficio", _slash, description="Scan and inspect the ofício Obsidian command surface.", args_hint="scan|config")
