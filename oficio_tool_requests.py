from __future__ import annotations

try:
    from .oficio_tool_schemas import JsonDict
    from .oficio_protocol import session_log_path
except Exception:  # pragma: no cover - direct import mode
    from oficio_tool_schemas import JsonDict
    from oficio_protocol import session_log_path


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
