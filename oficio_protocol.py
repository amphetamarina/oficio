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


def _is_split_hermes(lines: List[str], idx: int) -> bool:
    """Return True if lines[idx] is a standalone @hermes id:... line followed by a - [ ] line."""
    line = lines[idx]
    if "@hermes" not in line or re.match(r"^\s*- \[ \] ", line):
        return False
    _id_match = _ID_RE.search(line)
    if not _id_match:
        return False
    # Look ahead for the - [ ] line, skipping blank lines
    j = idx + 1
    while j < len(lines) and not lines[j].strip():
        j += 1
    return j < len(lines) and bool(re.match(r"^\s*- \[ \] ", lines[j])) and "@hermes" not in lines[j]


def _split_next_idx(lines: List[str], idx: int) -> int:
    """After a split @hermes line, return the index of the following - [ ] line."""
    j = idx + 1
    while j < len(lines) and not lines[j].strip():
        j += 1
    return j


def find_pending_requests(path: str, text: str) -> List[Dict[str, object]]:
    lines = text.splitlines()
    pending: List[Dict[str, object]] = []
    for idx, line in enumerate(lines):
        # Standard format: - [ ] @hermes id:... on the same line
        if re.match(r"^\s*- \[ \] ", line) and "@hermes" in line:
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
            continue
        # Split-line format: @hermes id:... on a standalone line, - [ ] on the next
        if _is_split_hermes(lines, idx):
            j = _split_next_idx(lines, idx)
            end = _block_end(lines, j)
            block = "\n".join(lines[idx:end]).strip()
            pending.append(
                {
                    "id": _request_id(line, path, len(pending)),
                    "path": path,
                    "line": idx + 1,
                    "lines": [idx + 1, j + 1],  # both line numbers for _mark_request
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

        # Standard format: @hermes and - [ ] on the same line
        if re.match(r"^\s*- \[ \] ", line):
            end = _block_end(lines, idx)
            lines[idx] = line.replace("- [ ]", "- [x]", 1)
            lines[end:end] = fields
            return "\n".join(lines) + "\n"

        # Split-line format: @hermes on a standalone line, - [ ] on the next
        j = _split_next_idx(lines, idx)
        if j < len(lines) and re.match(r"^\s*- \[ \] ", lines[j]) and "@hermes" not in lines[j]:
            end = _block_end(lines, j)
            lines[j] = lines[j].replace("- [ ]", "- [x]", 1)
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
