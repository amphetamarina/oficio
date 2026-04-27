from __future__ import annotations

from typing import Any, Callable, Mapping

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
    from .oficio_config import load_config, resolve_daily_path, vault_abspath
    from .oficio_obsidian import read_note, write_note
    from .oficio_protocol import (
        PendingRequest,
        _find_max_auto_id,
        _get_current_session_id,
        find_pending_requests,
        mark_request_completed,
        mark_request_failed,
        mark_request_in_progress,
        replace_once,
        request_exists,
        session_log_path,
    )
except Exception:  # pragma: no cover - direct import mode
    from oficio_config import load_config, resolve_daily_path, vault_abspath
    from oficio_obsidian import read_note, write_note
    from oficio_protocol import (
        PendingRequest,
        _find_max_auto_id,
        _get_current_session_id,
        find_pending_requests,
        mark_request_completed,
        mark_request_failed,
        mark_request_in_progress,
        replace_once,
        request_exists,
        session_log_path,
    )

JsonDict = dict[str, Any]
ToolHandler = Callable[[JsonDict], str]


class ToolSpec:
    def __init__(self, name: str, schema: JsonDict, handler: Callable[..., str]) -> None:
        self.name = name
        self.schema = schema
        self.handler = handler


class RequestUpdate:
    def __init__(
        self,
        *,
        id: str,
        path: str,
        line: int | None,
        session_id: str,
        note: str = "",
        error: str = "",
        response: str = "",
    ) -> None:
        self.id = id
        self.path = path
        self.line = line
        self.session_id = session_id
        self.note = note
        self.error = error
        self.response = response

    @property
    def result(self) -> JsonDict:
        return {
            "success": True,
            "id": self.id,
            "path": self.path,
            "session_id": self.session_id,
            "log_path": session_log_path(self.session_id),
        }


class ToolSchema:
    PATH = {
        "type": "string",
        "description": "Vault-relative source path. Defaults to today's daily note.",
    }
    LINE = {
        "type": "integer",
        "description": "Line number of the request from scan output. Required for auto-generated IDs.",
    }
    SESSION = {
        "type": "string",
        "description": "Current Hermes session ID from --pass-session-id.",
    }

    @classmethod
    def build(
        cls,
        name: str,
        description: str,
        properties: JsonDict,
        required: list[str] | None = None,
    ) -> JsonDict:
        parameters: JsonDict = {"type": "object", "properties": properties}
        if required:
            parameters["required"] = required
        return {"name": name, "description": description, "parameters": parameters}


CONFIG_SCHEMA = ToolSchema.build("oficio_config_show", "Show the active ofício configuration paths.", {})
SCAN_SCHEMA = ToolSchema.build(
    "oficio_scan",
    "Scan the daily note for pending '- [ ] @hermes ...' requests.",
    {"path": {"type": "string", "description": "Vault-relative daily note path. Defaults to today's daily note."}},
)
READ_SCHEMA = ToolSchema.build(
    "oficio_read",
    "Read a vault note through obsidian-cli, using a vault-relative path.",
    {"path": {"type": "string"}},
    ["path"],
)
START_SCHEMA = ToolSchema.build(
    "oficio_start",
    "Mark an ofício request as 'in progress' with inline Status in the daily note.",
    {"id": {"type": "string"}, "path": ToolSchema.PATH, "session_id": ToolSchema.SESSION, "line": ToolSchema.LINE},
    ["id"],
)
COMPLETE_SCHEMA = ToolSchema.build(
    "oficio_complete",
    "Mark an ofício request complete with inline Status in the daily note.",
    {
        "id": {"type": "string"},
        "path": ToolSchema.PATH,
        "note": {"type": "string"},
        "response": {
            "type": "string",
            "description": "Full response to write under the request as an Agent response block.",
        },
        "session_id": ToolSchema.SESSION,
        "line": ToolSchema.LINE,
    },
    ["id", "note"],
)
FAIL_SCHEMA = ToolSchema.build(
    "oficio_fail",
    "Mark an ofício request failed with inline Status in the daily note.",
    {
        "id": {"type": "string"},
        "path": ToolSchema.PATH,
        "error": {"type": "string"},
        "session_id": ToolSchema.SESSION,
        "line": ToolSchema.LINE,
    },
    ["id", "error"],
)
REPLACE_SCHEMA = ToolSchema.build(
    "oficio_replace",
    "Safely replace one exact string in a vault note.",
    {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}},
    ["path", "old", "new"],
)
TODAY_SCHEMA = ToolSchema.build("oficio_today", "Show today's resolved ofício daily note path.", {})


class OficioTools:
    def config(self, args: JsonDict, **kw: Any) -> str:
        return tool_result({"success": True, "config": load_config()})

    def scan(self, args: JsonDict, **kw: Any) -> str:
        cfg = load_config()
        requested_path = self._string(args, "path")
        paths = [requested_path] if requested_path else [resolve_daily_path(cfg)]
        auto_index = self._highest_auto_id(paths, cfg)
        pending: list[PendingRequest] = []
        errors: list[str] = []

        for path in paths:
            try:
                requests = find_pending_requests(path, self._read_note(cfg, path), start_index=auto_index)
            except Exception as exc:
                errors.append(f"{path}: {exc}")
                continue

            auto_index += sum(1 for request in requests if not request.get("has_explicit_id"))
            pending.extend(requests)

        return tool_result({
            "success": True,
            "path": requested_path or paths[0],
            "pending": pending,
            "count": len(pending),
            "scanned": paths,
            "errors": errors or None,
        })

    def read(self, args: JsonDict, **kw: Any) -> str:
        path = self._string(args, "path")
        if not path:
            return tool_error("path is required")

        try:
            cfg = load_config()
            vault_abspath(cfg, path)
            return tool_result({"success": True, "path": path, "content": read_note(path)})
        except Exception as exc:
            return tool_error(f"oficio_read failed: {exc}")

    def today(self, args: JsonDict, **kw: Any) -> str:
        return tool_result({"success": True, "daily_path": resolve_daily_path(load_config())})

    def start(self, args: JsonDict, **kw: Any) -> str:
        return self._update_request(
            args,
            kw,
            action_name="oficio_start",
            update=lambda text, request: mark_request_in_progress(
                text,
                request.id,
                session_id=request.session_id,
                line_number=request.line,
            ),
        )

    def complete(self, args: JsonDict, **kw: Any) -> str:
        return self._update_request(
            args,
            kw,
            required_field="note",
            action_name="oficio_complete",
            update=lambda text, request: mark_request_completed(
                text,
                request.id,
                request.note,
                line_number=request.line,
                session_id=request.session_id,
                response=request.response,
            ),
        )

    def fail(self, args: JsonDict, **kw: Any) -> str:
        return self._update_request(
            args,
            kw,
            required_field="error",
            action_name="oficio_fail",
            update=lambda text, request: mark_request_failed(
                text,
                request.id,
                request.error,
                line_number=request.line,
                session_id=request.session_id,
            ),
        )

    def replace(self, args: JsonDict, **kw: Any) -> str:
        path = self._string(args, "path")
        old = str(args.get("old") or "")
        new = str(args.get("new") or "")
        if not path:
            return tool_error("path is required")

        try:
            cfg = load_config()
            updated = replace_once(self._read_note(cfg, path), old, new)
            write_note(path, updated)
            return tool_result({"success": True, "path": path, "replacements": 1})
        except Exception as exc:
            return tool_error(f"oficio_replace failed: {exc}")

    def slash(self, raw_args: str) -> str:
        argv = raw_args.strip().split()
        command = argv[0] if argv else "scan"

        if command in {"config", "status"}:
            return self.config({})
        if command == "scan":
            return self.scan({"path": argv[1]} if len(argv) > 1 else {})
        if command == "today":
            return self.today({})
        if command == "start" and len(argv) >= 2:
            return self.start({"id": argv[1], "line": self._optional_int(argv[2]) if len(argv) > 2 else None})
        if command == "complete" and len(argv) >= 3:
            return self.complete({"id": argv[1], "note": " ".join(argv[2:])})
        if command == "fail" and len(argv) >= 3:
            return self.fail({"id": argv[1], "error": " ".join(argv[2:])})

        return (
            "Usage: /oficio "
            "[scan [path]|config|status|today|start <id> [line]|complete <id> <note...>|fail <id> <error...>]"
        )

    def tool_specs(self) -> list[ToolSpec]:
        return [
            ToolSpec("oficio_config_show", CONFIG_SCHEMA, self.config),
            ToolSpec("oficio_scan", SCAN_SCHEMA, self.scan),
            ToolSpec("oficio_read", READ_SCHEMA, self.read),
            ToolSpec("oficio_start", START_SCHEMA, self.start),
            ToolSpec("oficio_complete", COMPLETE_SCHEMA, self.complete),
            ToolSpec("oficio_fail", FAIL_SCHEMA, self.fail),
            ToolSpec("oficio_replace", REPLACE_SCHEMA, self.replace),
            ToolSpec("oficio_today", TODAY_SCHEMA, self.today),
        ]

    def _update_request(
        self,
        args: JsonDict,
        kw: Mapping[str, Any],
        *,
        action_name: str,
        update: Callable[[str, RequestUpdate], str],
        required_field: str | None = None,
    ) -> str:
        try:
            cfg = load_config()
            request = self._request_update(args, kw, cfg, required_field)
            source = self._read_note(cfg, request.path)
            try:
                updated = update(source, request)
            except ValueError:
                if request.line is None or not request_exists(source, request.id):
                    raise
                request.line = None
                updated = update(source, request)
            write_note(request.path, updated)
            return tool_result(request.result)
        except Exception as exc:
            return tool_error(f"{action_name} failed: {exc}")

    def _request_update(
        self,
        args: JsonDict,
        kw: Mapping[str, Any],
        cfg: JsonDict,
        required_field: str | None,
    ) -> RequestUpdate:
        request_id = self._string(args, "id")
        if not request_id:
            raise ValueError("id is required")

        request = RequestUpdate(
            id=request_id,
            path=self._string(args, "path") or resolve_daily_path(cfg),
            line=self._optional_int(args.get("line")),
            session_id=self._session_id(args, kw),
            note=self._string(args, "note"),
            error=self._string(args, "error"),
            response=self._string(args, "response"),
        )

        if required_field and not getattr(request, required_field):
            raise ValueError(f"{required_field} is required")
        return request

    def _read_note(self, cfg: JsonDict, path: str) -> str:
        vault_abspath(cfg, path)
        try:
            return read_note(path)
        except Exception:
            target = vault_abspath(cfg, path)
            if not target.exists():
                raise FileNotFoundError(f"note not found: {path}")
            return target.read_text()

    def _highest_auto_id(self, paths: list[str], cfg: JsonDict) -> int:
        highest = 0
        for path in paths:
            try:
                highest = max(highest, _find_max_auto_id(self._read_note(cfg, path)))
            except Exception:
                continue
        return highest

    def _session_id(self, args: JsonDict, kw: Mapping[str, Any]) -> str:
        return self._string(args, "session_id") or self._string(kw, "session_id") or _get_current_session_id()

    def _string(self, args: Mapping[str, Any], key: str) -> str:
        return str(args.get(key) or "").strip()

    def _optional_int(self, value: Any) -> int | None:
        if value is None or value == "":
            return None
        return int(value)


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
