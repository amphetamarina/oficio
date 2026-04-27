from __future__ import annotations

from dataclasses import dataclass

try:
    from .oficio_tool_schemas import JsonDict
    from .oficio_protocol import session_log_path
except ImportError:  # pragma: no cover - direct import mode
    from oficio_tool_schemas import JsonDict
    from oficio_protocol import session_log_path


@dataclass(slots=True)
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
            "log_path": session_log_path(self.session_id),
        }
