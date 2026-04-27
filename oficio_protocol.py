from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, TypedDict

HERMES_MARKER = "@hermes"
AUTO_ID_FALLBACK = "pedido"

ID_PATTERN = re.compile(r"\bid:([A-Za-z0-9_.:-]+)")
STATUS_LINE_PATTERN = re.compile(r"^\s+Status:\s*")
AGENT_RESPONSE_PATTERN = re.compile(r"^\s*Agent response:\s*$")
CHECKBOX_PATTERN = re.compile(r"^\s*-\s*\[\s*[ x]\]")
OPEN_CHECKBOX_PATTERN = re.compile(r"^\s*-\s*\[\s*\]")


class PendingRequest(TypedDict, total=False):
    id: str
    path: str
    line: int
    lines: list[int]
    text: str
    has_explicit_id: bool


@dataclass(frozen=True)
class RequestBlock:
    marker_index: int
    checkbox_index: int
    end_index: int
    marker_line: str
    has_explicit_id: bool

    @property
    def line_number(self) -> int:
        return self.marker_index + 1

    @property
    def checkbox_line_number(self) -> int:
        return self.checkbox_index + 1

    @property
    def is_split_line(self) -> bool:
        return self.marker_index != self.checkbox_index


class SessionLogs:
    def __init__(self, home: Path | None = None) -> None:
        self.home = home or Path.home()

    def current_session_id(self) -> str:
        env_session = os.environ.get("HERMES_SESSION_ID", "").strip()
        if env_session:
            return env_session

        latest_session = self._latest_session_file()
        if latest_session is None:
            return ""

        try:
            data = json.loads(latest_session.read_text()[:4096])
        except Exception:
            return ""
        return str(data.get("session_id", ""))

    def log_path(self, session_id: str) -> str:
        if not session_id:
            return ""
        return str(self.home / ".hermes" / "sessions" / f"session_{session_id}.json")

    def log_link(self, session_id: str) -> str:
        path = self.log_path(session_id)
        return f"[{path}](file://{path})" if path else ""

    def _latest_session_file(self) -> Path | None:
        sessions_dir = self.home / ".hermes" / "sessions"
        if not sessions_dir.exists():
            return None
        sessions = [
            path for path in sessions_dir.iterdir()
            if path.is_file() and path.suffix == ".json" and "cron" not in path.name
        ]
        return max(sessions, key=lambda path: path.stat().st_mtime, default=None)


class RequestDocument:
    def __init__(self, text: str) -> None:
        self.lines = text.splitlines()

    def pending_requests(self, path: str, start_index: int = 0) -> list[PendingRequest]:
        pending: list[PendingRequest] = []
        auto_count = 0

        for block in self._pending_blocks():
            request_id = self._request_id(block.marker_line, start_index + auto_count)
            if not block.has_explicit_id:
                auto_count += 1

            item = PendingRequest(
                id=request_id,
                path=path,
                line=block.line_number,
                text="\n".join(self.lines[block.marker_index:block.end_index]).strip(),
                has_explicit_id=block.has_explicit_id,
            )
            if block.is_split_line:
                item["lines"] = [block.line_number, block.checkbox_line_number]
            pending.append(item)

        return pending

    def has_request(self, request_id: str, line_number: int | None = None) -> bool:
        try:
            self._find_markable_request(request_id, line_number=line_number)
        except ValueError:
            return False
        return True

    def mark_in_progress(self, request_id: str, *, session_id: str = "", line_number: int | None = None) -> str:
        block = self._find_status_target(request_id, line_number=line_number)
        self._ensure_request_id(block.marker_index, request_id)
        return self._upsert_status(request_id, format_status("in progress", session_id=session_id))

    def mark_completed(
        self,
        request_id: str,
        note: str,
        *,
        line_number: int | None = None,
        session_id: str = "",
        response: str = "",
    ) -> str:
        updated = self._mark_finished(request_id, f"completed - {note}", line_number, session_id)
        if response.strip():
            updated = RequestDocument(updated).upsert_agent_response(request_id, response)
        return updated

    def mark_failed(
        self,
        request_id: str,
        error: str,
        *,
        line_number: int | None = None,
        session_id: str = "",
    ) -> str:
        return self._mark_finished(request_id, f"failed - {error}", line_number, session_id)

    def upsert_status(self, request_id: str, status_message: str) -> str:
        return self._upsert_status(request_id, status_message)

    def upsert_agent_response(self, request_id: str, response: str) -> str:
        block = self._find_status_target(request_id)
        response_range = self._find_response_range(block)
        insert_at = self._response_insert_index(block)

        if response_range is not None:
            start, end = response_range
            del self.lines[start:end]
            insert_at = start

        self.lines[insert_at:insert_at] = self._response_block(response)
        return self.render()

    def render(self) -> str:
        return "\n".join(self.lines) + "\n"

    def _mark_finished(
        self,
        request_id: str,
        status: str,
        line_number: int | None,
        session_id: str,
    ) -> str:
        try:
            block = self._find_markable_request(request_id, line_number=line_number)
        except ValueError:
            if line_number is None or not self.has_request(request_id):
                raise
            block = self._find_markable_request(request_id)

        self._ensure_request_id(block.marker_index, request_id)
        self.lines[block.checkbox_index] = self._checked_line(self.lines[block.checkbox_index])
        return self._upsert_status(request_id, format_status(status, session_id=session_id))

    def _pending_blocks(self) -> Iterable[RequestBlock]:
        for index, line in enumerate(self.lines):
            if self._is_standard_request(line):
                yield self._block(index, index, line)
                continue

            checkbox_index = self._split_checkbox_index(index)
            if checkbox_index is not None:
                yield self._block(index, checkbox_index, line)

    def _all_blocks(self) -> Iterable[RequestBlock]:
        for index, line in enumerate(self.lines):
            if self._is_checkbox(line) and self._has_marker(line):
                yield self._block(index, index, line)
                continue

            if not self._has_marker(line) or self._is_checkbox(line):
                continue

            checkbox_index = self._next_non_empty_line(index + 1)
            if self._is_split_request_checkbox(checkbox_index):
                yield self._block(index, checkbox_index, line)

    def _block(self, marker_index: int, checkbox_index: int, marker_line: str) -> RequestBlock:
        return RequestBlock(
            marker_index=marker_index,
            checkbox_index=checkbox_index,
            end_index=self._block_end(checkbox_index),
            marker_line=marker_line,
            has_explicit_id=bool(ID_PATTERN.search(marker_line)),
        )

    def _find_markable_request(self, request_id: str, *, line_number: int | None = None) -> RequestBlock:
        if line_number is not None:
            return self._request_at_line(line_number)

        for block in self._pending_blocks():
            if self._line_request_id(block.marker_line) == request_id:
                return block
        raise ValueError(f"pending request not found: {request_id}")

    def _find_status_target(self, request_id: str, *, line_number: int | None = None) -> RequestBlock:
        if line_number is not None:
            block = self._request_at_line(line_number)
            if not self._line_request_id(block.marker_line):
                self._ensure_request_id(block.marker_index, request_id)
                return self._block(block.marker_index, block.checkbox_index, self.lines[block.marker_index])
            return block

        for block in self._all_blocks():
            if self._line_request_id(block.marker_line) == request_id:
                return block
        raise ValueError(f"pending request not found: {request_id}")

    def _request_at_line(self, line_number: int) -> RequestBlock:
        index = line_number - 1
        if index < 0 or index >= len(self.lines):
            raise ValueError(f"line_number {line_number} out of range")

        line = self.lines[index]
        if self._is_standard_request(line):
            return self._block(index, index, line)

        checkbox_index = self._split_checkbox_index(index)
        if checkbox_index is not None:
            return self._block(index, checkbox_index, line)

        raise ValueError(f"no @hermes request found at line {line_number}")

    def _upsert_status(self, request_id: str, status_message: str) -> str:
        block = self._find_status_target(request_id)
        status_index = self._find_status_line(block)
        new_status = f"  Status: {status_message}"

        if status_index is None:
            self.lines.insert(block.checkbox_index + 1, new_status)
        else:
            self.lines[status_index] = new_status
        return self.render()

    def _find_status_line(self, block: RequestBlock) -> int | None:
        for index in range(block.checkbox_index + 1, block.end_index):
            if STATUS_LINE_PATTERN.match(self.lines[index]):
                return index
        return None

    def _response_insert_index(self, block: RequestBlock) -> int:
        status_index = self._find_status_line(block)
        return status_index + 1 if status_index is not None else block.checkbox_index + 1

    def _find_response_range(self, block: RequestBlock) -> tuple[int, int] | None:
        for index in range(block.checkbox_index + 1, block.end_index):
            if AGENT_RESPONSE_PATTERN.match(self.lines[index]):
                return index, self._response_block_end(index, block.end_index)
        return None

    def _response_block_end(self, label_index: int, block_end: int) -> int:
        fence_index = label_index + 1
        if fence_index >= block_end:
            return fence_index

        fence = self.lines[fence_index].strip()
        if not fence.startswith("```"):
            return fence_index

        index = fence_index + 1
        while index < block_end and self.lines[index].strip() != fence:
            index += 1
        return min(index + 1, block_end)

    def _response_block(self, response: str) -> list[str]:
        fence = self._safe_fence(response)
        lines = ["  Agent response:", f"  {fence}markdown"]
        lines.extend(f"  {line}" if line else "  " for line in response.strip().splitlines())
        lines.append(f"  {fence}")
        return lines

    def _safe_fence(self, text: str) -> str:
        fence = "````"
        while fence in text:
            fence += "`"
        return fence

    def _ensure_request_id(self, marker_index: int, request_id: str) -> None:
        if ID_PATTERN.search(self.lines[marker_index]):
            return
        self.lines[marker_index] = re.sub(
            r"(@hermes\b)",
            f"@hermes id:{request_id}",
            self.lines[marker_index],
            count=1,
        )

    def _split_checkbox_index(self, marker_index: int) -> int | None:
        marker = self.lines[marker_index]
        if not self._has_marker(marker) or self._is_checkbox(marker):
            return None

        checkbox_index = self._next_non_empty_line(marker_index + 1)
        if self._is_split_request_checkbox(checkbox_index, open_only=True):
            return checkbox_index
        return None

    def _is_split_request_checkbox(self, checkbox_index: int, *, open_only: bool = False) -> bool:
        if checkbox_index >= len(self.lines) or self._has_marker(self.lines[checkbox_index]):
            return False
        matcher = self._is_open_checkbox if open_only else self._is_checkbox
        return matcher(self.lines[checkbox_index])

    def _block_end(self, start_index: int) -> int:
        index = start_index + 1
        while index < len(self.lines) and self._line_belongs_to_block(self.lines[index]):
            index += 1
        return index

    def _next_non_empty_line(self, start_index: int) -> int:
        index = start_index
        while index < len(self.lines) and not self.lines[index].strip():
            index += 1
        return index

    def _line_belongs_to_block(self, line: str) -> bool:
        if self._is_checkbox(line):
            return False
        return not line or line.startswith((" ", "\t", "#"))

    def _line_request_id(self, line: str) -> str:
        match = ID_PATTERN.search(line)
        return match.group(1) if match else ""

    def _request_id(self, marker_line: str, index: int) -> str:
        return self._line_request_id(marker_line) or _auto_id(index)

    def _has_marker(self, line: str) -> bool:
        return HERMES_MARKER in line

    def _is_open_checkbox(self, line: str) -> bool:
        return bool(OPEN_CHECKBOX_PATTERN.match(line))

    def _is_checkbox(self, line: str) -> bool:
        return bool(CHECKBOX_PATTERN.match(line))

    def _is_standard_request(self, line: str) -> bool:
        return self._is_open_checkbox(line) and self._has_marker(line)

    def _checked_line(self, line: str) -> str:
        return re.sub(r"-\s*\[\s*\]", "- [x]", line, count=1)


def _today_id_prefix() -> str:
    return datetime.now().strftime("%Y%m%d")


def _auto_id(index: int) -> str:
    return f"{_today_id_prefix()}-{index + 1}"


def _find_max_auto_id(text: str) -> int:
    pattern = re.compile(rf"\bid:{_today_id_prefix()}-(\d+)\b")
    return max((int(match.group(1)) for match in pattern.finditer(text)), default=0)


def slugify_request_id(text: str, *, fallback: str = AUTO_ID_FALLBACK) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_text.lower()
    lowered = re.sub(r"\bid:[A-Za-z0-9_.:-]+\b", " ", lowered)
    lowered = lowered.replace(HERMES_MARKER, " ")
    lowered = re.sub(r"^-\s*\[ \]\s*", " ", lowered)
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or fallback


def next_available_request_id(preferred_id: str, *texts: str) -> str:
    candidate = preferred_id.strip()
    if not candidate:
        raise ValueError("preferred_id is required")
    corpus = "\n".join(texts)
    if _id_is_available(candidate, corpus):
        return candidate
    return _next_suffixed_id(candidate, corpus)


def _id_is_available(request_id: str, corpus: str) -> bool:
    return f"## {request_id}" not in corpus and f"id:{request_id}" not in corpus


def _next_suffixed_id(candidate: str, corpus: str) -> str:
    suffix = 2
    while not _id_is_available(f"{candidate}-{suffix}", corpus):
        suffix += 1
    return f"{candidate}-{suffix}"


def find_pending_requests(path: str, text: str, start_index: int = 0) -> list[PendingRequest]:
    return RequestDocument(text).pending_requests(path, start_index=start_index)


def _get_current_session_id() -> str:
    return SessionLogs().current_session_id()


def session_log_path(session_id: str) -> str:
    return SessionLogs().log_path(session_id)


def session_log_link(session_id: str) -> str:
    return SessionLogs().log_link(session_id)


def format_status(status: str, *, session_id: str = "") -> str:
    if not session_id:
        return status
    return f"{status} | Session: {session_id} | Log: {session_log_link(session_id)}"


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
