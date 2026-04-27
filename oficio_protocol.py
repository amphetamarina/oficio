from __future__ import annotations

try:
    from .oficio_request_blocks import PendingRequest, RequestBlock
    from .oficio_request_document import RequestDocument
    from .oficio_request_ids import (
        HERMES_MARKER,
        auto_id,
        find_max_auto_id,
        next_available_request_id,
        slugify_request_id,
        today_id_prefix,
    )
    from .oficio_sessions import SessionLogs
    from .oficio_sessions import format_status as _format_status
    from .oficio_sessions import session_log_link as _session_log_link
    from .oficio_sessions import session_log_path as _session_log_path
except Exception:  # pragma: no cover - direct import mode
    from oficio_request_blocks import PendingRequest, RequestBlock
    from oficio_request_document import RequestDocument
    from oficio_request_ids import (
        HERMES_MARKER,
        auto_id,
        find_max_auto_id,
        next_available_request_id,
        slugify_request_id,
        today_id_prefix,
    )
    from oficio_sessions import SessionLogs
    from oficio_sessions import format_status as _format_status
    from oficio_sessions import session_log_link as _session_log_link
    from oficio_sessions import session_log_path as _session_log_path


def find_pending_requests(path: str, text: str, start_index: int = 0) -> list[PendingRequest]:
    return RequestDocument(text).pending_requests(path, start_index=start_index)


def _today_id_prefix() -> str:
    return today_id_prefix()


def _auto_id(index: int) -> str:
    return auto_id(index)


def _find_max_auto_id(text: str) -> int:
    return find_max_auto_id(text)


def _get_current_session_id() -> str:
    return SessionLogs().current_session_id()


def session_log_path(session_id: str) -> str:
    return _session_log_path(session_id)


def session_log_link(session_id: str) -> str:
    return _session_log_link(session_id)


def format_status(status: str, *, session_id: str = "") -> str:
    return _format_status(status, session_id=session_id)


def request_exists(text: str, request_id: str, *, line_number: int | None = None) -> bool:
    return RequestDocument(text).has_request(request_id, line_number=line_number)


def mark_request_in_progress(
    text: str,
    request_id: str,
    *,
    session_id: str = "",
    line_number: int | None = None,
) -> str:
    return RequestDocument(text).mark_in_progress(request_id, session_id=session_id, line_number=line_number)


def mark_request_completed(
    text: str,
    request_id: str,
    note: str,
    *,
    timestamp: str | None = None,
    line_number: int | None = None,
    session_id: str = "",
    response: str = "",
) -> str:
    return RequestDocument(text).mark_completed(
        request_id,
        note,
        line_number=line_number,
        session_id=session_id,
        response=response,
    )


def mark_request_failed(
    text: str,
    request_id: str,
    error: str,
    *,
    timestamp: str | None = None,
    line_number: int | None = None,
    session_id: str = "",
) -> str:
    return RequestDocument(text).mark_failed(
        request_id,
        error,
        line_number=line_number,
        session_id=session_id,
    )


def replace_once(text: str, old: str, new: str) -> str:
    if not old:
        raise ValueError("old text is required")
    count = text.count(old)
    if count == 0:
        raise ValueError("old text not found")
    if count > 1:
        raise ValueError("old text occurs multiple times")
    return text.replace(old, new, 1)


def upsert_status_line(text: str, request_id: str, status_message: str) -> str:
    return RequestDocument(text).upsert_status(request_id, status_message)


def upsert_agent_response(text: str, request_id: str, response: str) -> str:
    return RequestDocument(text).upsert_agent_response(request_id, response)
