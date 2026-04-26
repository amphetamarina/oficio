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
    from .oficio_config import load_config, resolve_daily_path, resolve_inbox_path, resolve_log_path, vault_abspath
    from .oficio_obsidian import append_note, read_note, write_note
    from .oficio_protocol import (
        _find_max_auto_id,
        append_inbox_request,
        find_pending_requests,
        mark_request_completed,
        mark_request_failed,
        render_summary_markdown,
        render_summary_plain,
        replace_once,
        request_exists,
        start_request_log_entry,
        summarize_log_entries,
        update_request_log_status,
    )
except Exception:  # pragma: no cover - direct import mode
    from oficio_config import load_config, resolve_daily_path, resolve_inbox_path, resolve_log_path, vault_abspath
    from oficio_obsidian import append_note, read_note, write_note
    from oficio_protocol import (
        _find_max_auto_id,
        append_inbox_request,
        find_pending_requests,
        mark_request_completed,
        mark_request_failed,
        render_summary_markdown,
        render_summary_plain,
        replace_once,
        request_exists,
        start_request_log_entry,
        summarize_log_entries,
        update_request_log_status,
    )

CONFIG_SCHEMA = {
    "name": "oficio_config_show",
    "description": "Show the active ofício configuration paths.",
    "parameters": {"type": "object", "properties": {}},
}

SCAN_SCHEMA = {
    "name": "oficio_scan",
    "description": "Scan the ofício inbox for pending '- [ ] @hermes ...' requests.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Vault-relative Markdown path. Defaults to configured/resolved inbox."}
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

COMPLETE_SCHEMA = {
    "name": "oficio_complete",
    "description": "Mark an ofício request complete and append an audit entry to the daily log.",
    "parameters": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "path": {"type": "string", "description": "Vault-relative source path. Defaults to configured/resolved inbox."},
            "note": {"type": "string"},
            "line": {"type": "integer", "description": "Line number of the request (from scan output). Required for auto-generated IDs."},
        },
        "required": ["id", "note"],
    },
}

FAIL_SCHEMA = {
    "name": "oficio_fail",
    "description": "Mark an ofício request failed and append an audit entry to the daily log.",
    "parameters": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "path": {"type": "string", "description": "Vault-relative source path. Defaults to configured/resolved inbox."},
            "error": {"type": "string"},
            "line": {"type": "integer", "description": "Line number of the request (from scan output). Required for auto-generated IDs."},
        },
        "required": ["id", "error"],
    },
}

START_SCHEMA = {
    "name": "oficio_start",
    "description": "Mark an ofício request as in-progress by writing a pending entry to the daily log.",
    "parameters": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "summary": {"type": "string", "description": "Brief summary of what the agent is about to do."},
            "path": {"type": "string", "description": "Vault-relative source path. Defaults to configured/resolved inbox."},
        },
        "required": ["id", "summary"],
    },
}

REPLACE_SCHEMA = {
    "name": "oficio_replace",
    "description": "Safely replace one exact string in a vault note.",
    "parameters": {
        "type": "object",
        "properties": {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}},
        "required": ["path", "old", "new"],
    },
}

TODAY_SCHEMA = {
    "name": "oficio_today",
    "description": "Show today's resolved ofício inbox and log paths.",
    "parameters": {"type": "object", "properties": {}},
}

SUMMARY_SCHEMA = {
    "name": "oficio_summary",
    "description": "Aggregate recent daily logs into a compact plain-text or markdown summary.",
    "parameters": {
        "type": "object",
        "properties": {
            "days": {"type": "integer", "description": "How many recent daily logs to scan.", "default": 7},
            "status": {"type": "string", "description": "Filter by status: all|pending|completed|failed", "default": "all"},
            "format": {"type": "string", "description": "Output format: plain|markdown", "default": "plain"},
        },
    },
}

REQUEST_SCHEMA = {
    "name": "oficio_request",
    "description": "Create a new pending @hermes follow-up request in the inbox.",
    "parameters": {
        "type": "object",
        "properties": {
            "description": {"type": "string", "description": "Request text to add to the inbox."},
            "id": {"type": "string", "description": "Optional explicit request id. Auto-generated if omitted."},
            "path": {"type": "string", "description": "Vault-relative destination path. Defaults to configured/resolved inbox."},
        },
        "required": ["description"],
    },
}


def _handle_config(args: Dict[str, Any], **kw: Any) -> str:
    return tool_result({"success": True, "config": load_config()})


def _read_note_with_fallback(cfg: Dict[str, Any], path: str) -> str:
    vault_abspath(cfg, path)
    try:
        return read_note(path)
    except Exception:
        target = vault_abspath(cfg, path)
        if not target.exists():
            raise FileNotFoundError(f"note not found: {path}")
        return target.read_text()


def _read_or_new_log(cfg: Dict[str, Any], path: str) -> str:
    try:
        return _read_note_with_fallback(cfg, path)
    except Exception:
        title = Path(path).stem
        date_str = title if title != "log" else ""
        try:
            from .oficio_config import _frontmatter  # type: ignore[import]
        except Exception:
            from oficio_config import _frontmatter  # type: ignore[import]
        if date_str:
            fm = _frontmatter({"tags": ["oficio/log"], "type": "log", "date": date_str})
        else:
            fm = _frontmatter({"tags": ["oficio/log"], "type": "log"})
        return fm + f"# ofício log · {title}\n"


def _handle_scan(args: Dict[str, Any], **kw: Any) -> str:
    cfg = load_config()
    explicit_path = str(args.get("path") or "").strip()

    if explicit_path:
        paths_to_scan = [explicit_path]
    else:
        paths_to_scan = [resolve_inbox_path(cfg)]
        if cfg.get("scan_daily", True):
            paths_to_scan.append(resolve_daily_path(cfg))

    all_pending: List[Dict[str, object]] = []
    errors: List[str] = []
    auto_index = 0
    for path in paths_to_scan:
        try:
            text = _read_note_with_fallback(cfg, path)
            auto_index = max(auto_index, _find_max_auto_id(text))
        except Exception:
            pass
    for path in paths_to_scan:
        try:
            text = _read_note_with_fallback(cfg, path)
            pending = find_pending_requests(path, text, start_index=auto_index)
            auto_index += sum(1 for r in pending if not r.get("has_explicit_id"))
            all_pending.extend(pending)
        except Exception as exc:
            errors.append(f"{path}: {exc}")

    if not all_pending and errors and not explicit_path:
        return tool_result({"success": True, "path": paths_to_scan[0], "pending": [], "count": 0, "scanned": paths_to_scan, "errors": errors})

    return tool_result({
        "success": True,
        "path": explicit_path or paths_to_scan[0],
        "pending": all_pending,
        "count": len(all_pending),
        "scanned": paths_to_scan if not explicit_path else [explicit_path],
        "errors": errors if errors else None,
    })


def _handle_read(args: Dict[str, Any], **kw: Any) -> str:
    cfg = load_config()
    path = str(args.get("path") or "").strip()
    if not path:
        return tool_error("path is required")
    try:
        vault_abspath(cfg, path)
        return tool_result({"success": True, "path": path, "content": read_note(path)})
    except Exception as exc:
        return tool_error(f"oficio_read failed: {exc}")


def _handle_append(args: Dict[str, Any], **kw: Any) -> str:
    cfg = load_config()
    path = str(args.get("path") or "").strip()
    content = str(args.get("content") or "")
    if not path:
        return tool_error("path is required")
    if not content:
        return tool_error("content is required")
    try:
        vault_abspath(cfg, path)
        result = append_note(path, content)
        return tool_result({"success": True, "path": path, "result": result})
    except Exception as exc:
        return tool_error(f"oficio_append failed: {exc}")


def _handle_today(args: Dict[str, Any], **kw: Any) -> str:
    cfg = load_config()
    return tool_result({"success": True, "inbox_path": resolve_inbox_path(cfg), "log_path": resolve_log_path(cfg)})


def _handle_start(args: Dict[str, Any], **kw: Any) -> str:
    cfg = load_config()
    request_id = str(args.get("id") or "").strip()
    summary = str(args.get("summary") or "").strip()
    source_path = str(args.get("path") or resolve_inbox_path(cfg))
    if not request_id:
        return tool_error("id is required")
    if not summary:
        return tool_error("summary is required")
    try:
        log_path = resolve_log_path(cfg)
        log = _read_or_new_log(cfg, log_path)
        updated_log = start_request_log_entry(log, request_id, source_path, summary)
        write_note(log_path, updated_log)
        return tool_result({"success": True, "id": request_id, "status": "pending", "log_path": log_path})
    except Exception as exc:
        return tool_error(f"oficio_start failed: {exc}")


def _handle_complete(args: Dict[str, Any], **kw: Any) -> str:
    cfg = load_config()
    request_id = str(args.get("id") or "").strip()
    note = str(args.get("note") or "").strip()
    source_path = str(args.get("path") or resolve_inbox_path(cfg))
    line_number = args.get("line")
    if line_number is not None:
        line_number = int(line_number)
    if not request_id:
        return tool_error("id is required")
    if not note:
        return tool_error("note is required")
    try:
        source = _read_note_with_fallback(cfg, source_path)
        try:
            updated_source = mark_request_completed(source, request_id, note, line_number=line_number)
        except ValueError:
            if line_number is None or not request_exists(source, request_id):
                raise
            updated_source = mark_request_completed(source, request_id, note)
        write_note(source_path, updated_source)
        log_path = resolve_log_path(cfg)
        log = _read_or_new_log(cfg, log_path)
        updated_log = update_request_log_status(log, request_id, "completed", note)
        write_note(log_path, updated_log)
        return tool_result({"success": True, "id": request_id, "path": source_path, "log_path": log_path})
    except Exception as exc:
        return tool_error(f"oficio_complete failed: {exc}")


def _handle_fail(args: Dict[str, Any], **kw: Any) -> str:
    cfg = load_config()
    request_id = str(args.get("id") or "").strip()
    error = str(args.get("error") or "").strip()
    source_path = str(args.get("path") or resolve_inbox_path(cfg))
    line_number = args.get("line")
    if line_number is not None:
        line_number = int(line_number)
    if not request_id:
        return tool_error("id is required")
    if not error:
        return tool_error("error is required")
    try:
        source = _read_note_with_fallback(cfg, source_path)
        try:
            updated_source = mark_request_failed(source, request_id, error, line_number=line_number)
        except ValueError:
            if line_number is None or not request_exists(source, request_id):
                raise
            updated_source = mark_request_failed(source, request_id, error)
        write_note(source_path, updated_source)
        log_path = resolve_log_path(cfg)
        log = _read_or_new_log(cfg, log_path)
        updated_log = update_request_log_status(log, request_id, "failed", error)
        write_note(log_path, updated_log)
        return tool_result({"success": True, "id": request_id, "path": source_path, "log_path": log_path})
    except Exception as exc:
        return tool_error(f"oficio_fail failed: {exc}")


def _handle_replace(args: Dict[str, Any], **kw: Any) -> str:
    cfg = load_config()
    path = str(args.get("path") or "").strip()
    old = str(args.get("old") or "")
    new = str(args.get("new") or "")
    if not path:
        return tool_error("path is required")
    try:
        text = _read_note_with_fallback(cfg, path)
        updated = replace_once(text, old, new)
        write_note(path, updated)
        return tool_result({"success": True, "path": path, "replacements": 1})
    except Exception as exc:
        return tool_error(f"oficio_replace failed: {exc}")


def _handle_summary(args: Dict[str, Any], **kw: Any) -> str:
    cfg = load_config()
    days = int(args.get("days") or 7)
    status_filter = str(args.get("status") or "all").strip().lower()
    output_format = str(args.get("format") or "plain").strip().lower()
    if days < 1:
        return tool_error("days must be >= 1")
    if status_filter not in {"all", "pending", "completed", "failed"}:
        return tool_error("status must be one of: all, pending, completed, failed")
    if output_format not in {"plain", "markdown"}:
        return tool_error("format must be one of: plain, markdown")
    try:
        log_dir_rel = str(cfg.get("log_daily_dir") or "agent/oficio/log/daily").rstrip("/")
        log_dir = vault_abspath(cfg, log_dir_rel)
        if not log_dir.exists():
            return tool_result({"success": True, "count": 0, "entries": [], "summary": ""})
        files = sorted(log_dir.glob("*.md"), reverse=True)[:days]
        entries: List[Dict[str, str]] = []
        for file in reversed(files):
            text = file.read_text()
            entries.extend(
                summarize_log_entries(
                    text,
                    source_path=f"{log_dir_rel}/{file.name}",
                    default_date=file.stem,
                )
            )
        if status_filter != "all":
            entries = [entry for entry in entries if entry.get("status") == status_filter]
        summary = render_summary_markdown(entries) if output_format == "markdown" else render_summary_plain(entries)
        return tool_result({"success": True, "count": len(entries), "entries": entries, "summary": summary})
    except Exception as exc:
        return tool_error(f"oficio_summary failed: {exc}")


def _handle_request(args: Dict[str, Any], **kw: Any) -> str:
    cfg = load_config()
    description = str(args.get("description") or "").strip()
    inbox_path = str(args.get("path") or resolve_inbox_path(cfg))
    request_id = str(args.get("id") or "").strip()
    if not description:
        return tool_error("description is required")
    try:
        text = _read_note_with_fallback(cfg, inbox_path)
        if not request_id:
            request_id = _find_next_request_id(text)
        updated = append_inbox_request(text, description, request_id=request_id, marker=str(cfg.get("pending_marker") or "@hermes"))
        write_note(inbox_path, updated)
        return tool_result({"success": True, "id": request_id, "path": inbox_path})
    except Exception as exc:
        return tool_error(f"oficio_request failed: {exc}")


def _find_next_request_id(text: str) -> str:
    current = _find_max_auto_id(text)
    date = Path(resolve_log_path(load_config())).stem.replace(".md", "")
    if not date or len(date) != 10:
        from datetime import datetime
        date = datetime.now().strftime("%Y%m%d")
    else:
        date = date.replace("-", "")
    return f"{date}-{current + 1}"


def _session_start_context(*args: Any, **kwargs: Any) -> Dict[str, Any] | None:
    try:
        cfg = load_config(ensure=False)
        paths_to_scan = [resolve_inbox_path(cfg)]
        if cfg.get("scan_daily", True):
            paths_to_scan.append(resolve_daily_path(cfg))
    except Exception:
        return None

    all_pending: List[Dict[str, object]] = []
    for path in paths_to_scan:
        target = vault_abspath(cfg, path)
        if not target.exists():
            continue
        try:
            text = target.read_text()
            pending = find_pending_requests(path, text)
            all_pending.extend(pending)
        except Exception:
            continue

    if not all_pending:
        return None
    ids = [str(item["id"]) for item in all_pending]
    return {
        "context": f"ofício: {len(all_pending)} pending request(s) in {', '.join(paths_to_scan)} — {', '.join(ids)}. Proactively inform the user and ask if they want these executed now.",
        "oficio": {"pending_count": len(all_pending), "paths": paths_to_scan, "ids": ids},
    }


def _slash(raw_args: str) -> str:
    argv = raw_args.strip().split()
    sub = argv[0] if argv else "scan"
    if sub in {"config", "status"}:
        return _handle_config({})
    if sub == "scan":
        path = argv[1] if len(argv) > 1 else ""
        return _handle_scan({"path": path} if path else {})
    if sub == "today":
        return _handle_today({})
    if sub == "start" and len(argv) >= 3:
        return _handle_start({"id": argv[1], "summary": " ".join(argv[2:])})
    if sub == "complete" and len(argv) >= 3:
        return _handle_complete({"id": argv[1], "note": " ".join(argv[2:])})
    if sub == "fail" and len(argv) >= 3:
        return _handle_fail({"id": argv[1], "error": " ".join(argv[2:])})
    if sub == "summary":
        return _handle_summary({})
    return "Usage: /oficio [scan [path]|config|status|today|start <id> <summary>|complete <id> <note...>|fail <id> <error...>|summary]"


def register(ctx) -> None:
    load_config()
    ctx.register_tool("oficio_config_show", "oficio", CONFIG_SCHEMA, _handle_config, emoji="📝")
    ctx.register_tool("oficio_scan", "oficio", SCAN_SCHEMA, _handle_scan, emoji="📝")
    ctx.register_tool("oficio_read", "oficio", READ_SCHEMA, _handle_read, emoji="📝")
    ctx.register_tool("oficio_append", "oficio", APPEND_SCHEMA, _handle_append, emoji="📝")
    ctx.register_tool("oficio_start", "oficio", START_SCHEMA, _handle_start, emoji="📝")
    ctx.register_tool("oficio_complete", "oficio", COMPLETE_SCHEMA, _handle_complete, emoji="📝")
    ctx.register_tool("oficio_fail", "oficio", FAIL_SCHEMA, _handle_fail, emoji="📝")
    ctx.register_tool("oficio_replace", "oficio", REPLACE_SCHEMA, _handle_replace, emoji="📝")
    ctx.register_tool("oficio_today", "oficio", TODAY_SCHEMA, _handle_today, emoji="📝")
    ctx.register_tool("oficio_summary", "oficio", SUMMARY_SCHEMA, _handle_summary, emoji="📝")
    ctx.register_tool("oficio_request", "oficio", REQUEST_SCHEMA, _handle_request, emoji="📝")
    ctx.register_command(
        "oficio",
        _slash,
        description="Scan and inspect the ofício Obsidian command surface.",
        args_hint="scan|config|status|today|start|complete|fail|summary",
    )
    if hasattr(ctx, "register_hook"):
        ctx.register_hook("on_session_start", _session_start_context)
