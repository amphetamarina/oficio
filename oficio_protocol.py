from __future__ import annotations

import re
from datetime import datetime
from typing import Dict, List

_PENDING_RE = re.compile(r"^(?P<indent>\s*)- \[ \] (?P<body>.*@hermes\b.*)$", re.MULTILINE)
_ID_RE = re.compile(r"\bid:([A-Za-z0-9_.:-]+)")


def _request_id(body: str, path: str, index: int) -> str:
    match = _ID_RE.search(body)
    if match:
        return match.group(1)
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", path).strip("-") or "request"
    return f"{safe}-{index + 1}"


def _block_end(lines: List[str], start: int) -> int:
    end = start + 1
    while end < len(lines):
        line = lines[end]
        if line.startswith("- [") or (line and not line.startswith((" ", "\t")) and not line.startswith("#")):
            break
        end += 1
    return end


def _timestamp(timestamp: str | None = None) -> str:
    return timestamp or datetime.now().astimezone().isoformat(timespec="seconds")


def _format_indented_field(name: str, value: str) -> str:
    safe = str(value).replace("\n", "\n  ")
    return f"  - {name}: {safe}"


def find_pending_requests(path: str, text: str) -> List[Dict[str, object]]:
    lines = text.splitlines()
    pending: List[Dict[str, object]] = []
    for idx, line in enumerate(lines):
        if not re.match(r"^\s*- \[ \] ", line) or "@hermes" not in line:
            continue
        end = _block_end(lines, idx)
        block = "\n".join(lines[idx:end]).strip()
        pending.append(
            {
                "id": _request_id(line, path, len(pending)),
                "path": path,
                "line": idx + 1,
                "text": block,
            }
        )
    return pending


def _mark_request(text: str, request_id: str, fields: List[str]) -> str:
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if "@hermes" not in line:
            continue
        match = _ID_RE.search(line)
        if not match or match.group(1) != request_id:
            continue
        if not re.match(r"^\s*- \[ \] ", line):
            continue
        end = _block_end(lines, idx)
        lines[idx] = line.replace("- [ ]", "- [x]", 1)
        lines[end:end] = fields
        return "\n".join(lines) + "\n"
    raise ValueError(f"pending request not found: {request_id}")


def mark_request_completed(text: str, request_id: str, note: str, *, timestamp: str | None = None) -> str:
    stamp = _timestamp(timestamp)
    return _mark_request(
        text,
        request_id,
        [
            _format_indented_field("completed", stamp),
            _format_indented_field("note", note),
        ],
    )


def mark_request_failed(text: str, request_id: str, error: str, *, timestamp: str | None = None) -> str:
    stamp = _timestamp(timestamp)
    return _mark_request(
        text,
        request_id,
        [
            _format_indented_field("status", "failed"),
            _format_indented_field("failed", stamp),
            _format_indented_field("error", error),
        ],
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


def append_request_log_entry(
    existing_log: str,
    request_id: str,
    status: str,
    source_path: str,
    message: str,
    *,
    timestamp: str | None = None,
) -> str:
    stamp = _timestamp(timestamp)
    entry = (
        f"\n## {request_id}\n\n"
        f"- status: {status}\n"
        f"- at: {stamp}\n"
        f"- source: {source_path}\n\n"
        f"{message.strip()}\n"
    )
    base = existing_log.rstrip() or "# ofício log"
    return base + "\n" + entry
