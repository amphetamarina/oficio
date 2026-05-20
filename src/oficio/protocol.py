from .request_blocks import PendingRequest, RequestBlock
from .request_document import RequestDocument
from .request_ids import (
    DEFAULT_AGENT_MARKER,
    agent_marker,
    auto_id,
    find_max_auto_id,
    next_available_request_id,
    slugify_request_id,
    today_id_prefix,
)
from .sessions import current_session_id, format_status

__all__ = [
    "DEFAULT_AGENT_MARKER",
    "PendingRequest",
    "RequestBlock",
    "RequestDocument",
    "agent_marker",
    "auto_id",
    "current_session_id",
    "find_max_auto_id",
    "find_pending_requests",
    "format_status",
    "mark_request_completed",
    "mark_request_failed",
    "mark_request_in_progress",
    "next_available_request_id",
    "replace_once",
    "request_exists",
    "slugify_request_id",
    "today_id_prefix",
    "upsert_agent_response",
    "upsert_status_line",
]


def find_pending_requests(path: str, text: str, start_index: int = 0) -> list[PendingRequest]:
    return RequestDocument(text).pending_requests(path, start_index=start_index)


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
