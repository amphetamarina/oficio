"""Tool surface called by the MCP server.

Each method returns the JSON envelope produced by ``_result.tool_result`` /
``tool_error``, so the same shape comes back regardless of which agent
invoked it.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from ._result import tool_error, tool_result
from .config import load_config, resolve_daily_path, vault_abspath
from .obsidian import read_note, write_note
from .protocol import (
    PendingRequest,
    current_session_id,
    find_max_auto_id,
    find_pending_requests,
    mark_request_completed,
    mark_request_failed,
    mark_request_in_progress,
    replace_once,
    request_exists,
)

JsonDict = dict[str, Any]


@dataclass(slots=True, kw_only=True)
class RequestUpdate:
    id: str
    path: str
    line: int | None
    session_id: str
    note: str = ""
    error: str = ""
    response: str = ""

    @property
    def result(self) -> JsonDict:
        return {
            "success": True,
            "id": self.id,
            "path": self.path,
            "session_id": self.session_id,
        }


class OficioTools:
    def config(self, args: JsonDict) -> str:
        return tool_result({"success": True, "config": load_config()})

    def scan(self, args: JsonDict) -> str:
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

        return tool_result(
            {
                "success": True,
                "path": requested_path or paths[0],
                "pending": pending,
                "count": len(pending),
                "scanned": paths,
                "errors": errors or None,
            }
        )

    def read(self, args: JsonDict) -> str:
        path = self._string(args, "path")
        if not path:
            return tool_error("path is required")

        try:
            cfg = load_config()
            vault_abspath(cfg, path)
            return tool_result({"success": True, "path": path, "content": read_note(path)})
        except Exception as exc:
            return tool_error(f"oficio_read failed: {exc}")

    def today(self, args: JsonDict) -> str:
        return tool_result({"success": True, "daily_path": resolve_daily_path(load_config())})

    def start(self, args: JsonDict) -> str:
        return self._update_request(
            args,
            action_name="oficio_start",
            update=lambda text, request: mark_request_in_progress(
                text,
                request.id,
                session_id=request.session_id,
                line_number=request.line,
            ),
        )

    def complete(self, args: JsonDict) -> str:
        return self._update_request(
            args,
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

    def fail(self, args: JsonDict) -> str:
        return self._update_request(
            args,
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

    def replace(self, args: JsonDict) -> str:
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

    def _update_request(
        self,
        args: JsonDict,
        *,
        action_name: str,
        update: Callable[[str, RequestUpdate], str],
        required_field: str | None = None,
    ) -> str:
        try:
            cfg = load_config()
            request = self._request_update(args, cfg, required_field)
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

    def _request_update(self, args: JsonDict, cfg: JsonDict, required_field: str | None) -> RequestUpdate:
        request_id = self._string(args, "id")
        if not request_id:
            raise ValueError("id is required")

        request = RequestUpdate(
            id=request_id,
            path=self._string(args, "path") or resolve_daily_path(cfg),
            line=self._optional_int(args.get("line")),
            session_id=self._string(args, "session_id") or current_session_id(),
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
        except (OSError, RuntimeError, ValueError):
            target = vault_abspath(cfg, path)
            if not target.exists():
                raise FileNotFoundError(f"note not found: {path}") from None
            return target.read_text()

    def _highest_auto_id(self, paths: list[str], cfg: JsonDict) -> int:
        highest = 0
        for path in paths:
            try:
                highest = max(highest, find_max_auto_id(self._read_note(cfg, path)))
            except (OSError, RuntimeError, ValueError):
                continue
        return highest

    def _string(self, args: Mapping[str, Any], key: str) -> str:
        return str(args.get(key) or "").strip()

    def _optional_int(self, value: Any) -> int | None:
        if value is None or value == "":
            return None
        return int(value)
