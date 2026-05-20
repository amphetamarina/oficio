"""JSON envelope returned by every ofício tool.

Every tool returns a string so MCP can pass it through unchanged. Successful
calls embed ``"success": true`` plus the payload; errors carry the message
under ``"error"``.
"""

import json
from typing import Any


def tool_result(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False)


def tool_error(message: str, **extra: Any) -> str:
    return json.dumps({"success": False, "error": message, **extra}, ensure_ascii=False)


__all__ = ["tool_error", "tool_result"]
