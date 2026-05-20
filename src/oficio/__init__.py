"""ofício — a calm interface between an Obsidian daily note and your agent.

Importable from any Python ≥ 3.11 process. The MCP server lives in
``oficio.mcp`` and is exposed as the ``oficio-mcp`` console script.
"""

from .config import default_config, load_config, resolve_daily_path, vault_abspath
from .protocol import (
    DEFAULT_AGENT_MARKER,
    agent_marker,
    find_pending_requests,
    mark_request_completed,
    mark_request_failed,
    mark_request_in_progress,
    replace_once,
    request_exists,
    upsert_agent_response,
    upsert_status_line,
)
from .tools import OficioTools

__version__ = "0.3.0"

__all__ = [
    "DEFAULT_AGENT_MARKER",
    "OficioTools",
    "__version__",
    "agent_marker",
    "default_config",
    "find_pending_requests",
    "load_config",
    "mark_request_completed",
    "mark_request_failed",
    "mark_request_in_progress",
    "replace_once",
    "request_exists",
    "resolve_daily_path",
    "upsert_agent_response",
    "upsert_status_line",
    "vault_abspath",
]
