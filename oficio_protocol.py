from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, List

_PENDING_RE = re.compile(r"^(?P<indent>\s*)- \[ \] (?P<body>.*@hermes\b.*)$", re.MULTILINE)
_ID_RE = re.compile(r"\bid:([A-Za-z0-9_.:-]+)")
_STATUS_LINE_RE = re.compile(r"^(\s+)Status:\s*(.+)$")

# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------


def _auto_id(index: int) -> str:
    """Generate an auto-ID from today's date + a sequence number."""
    date = datetime.now().strftime("%Y%m%d")
    return f"{date}-{index + 1}"


def _find_max_auto_id(text: str) -> int:
    """Find the highest auto-ID number for today's date in the given text."""
    date = datetime.now().strftime("%Y%m%d")
    pattern = re.compile(rf"\bid:{date}-(\d+)\b")
    max_n = 0
    for m in pattern.finditer(text):
        n = int(m.group(1))
        if n > max_n:
            max_n = n
    return max_n


def _request_id(body: str, path: str, index: int) -> str:
    """Extract explicit id:... or generate an auto-ID."""
    match = _ID_RE.search(body)
    if match:
        return match.group(1)
    return _auto_id(index)


def slugify_request_id(text: str, *, fallback: str = "pedido") -> str:
    """Generate a human-readable request id slug from request text."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_text.lower()
    lowered = re.sub(r"\bid:[A-Za-z0-9_.:-]+\b", " ", lowered)
    lowered = lowered.replace("@hermes", " ")
    lowered = re.sub(r"^-\s*\[ \]\s*", " ", lowered)
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    slug = lowered.strip("-")
    return slug or fallback


def next_available_request_id(preferred_id: str, *texts: str) -> str:
    """Return a unique request id, suffixing with -2, -3, ... when needed."""
    candidate = preferred_id.strip()
    if not candidate:
        raise ValueError("preferred_id is required")
    corpus = "\n".join(texts)
    if f"## {candidate}" not in corpus and f"id:{candidate}" not in corpus:
        return candidate
    suffix = 2
    while True:
        alt = f"{candidate}-{suffix}"
        if f"## {alt}" not in corpus and f"id:{alt}" not in corpus:
            return alt
        suffix += 1


# ---------------------------------------------------------------------------
# Block helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Session ID discovery
# ---------------------------------------------------------------------------


def _get_current_session_id() -> str:
    """Discover the current Hermes session ID from the most recent session file."""
    sessions_dir = Path.home() / ".hermes" / "sessions"
    if not sessions_dir.exists():
        return ""
    files = [
        f for f in sessions_dir.iterdir()
        if f.is_file() and "cron" not in f.name and f.suffix == ".json"
    ]
    if not files:
        return ""
    latest = max(files, key=lambda f: f.stat().st_mtime)
    try:
        data = json.loads(latest.read_text()[:4096])
        return str(data.get("session_id", ""))
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Split-line detection
# ---------------------------------------------------------------------------


def _is_split_hermes(lines: List[str], idx: int) -> bool:
    """Return True if lines[idx] is a standalone @hermes line followed by a - [ ] line."""
    line = lines[idx]
    if "@hermes" not in line or re.match(r"^\s*- \[ \] ", line):
        return False
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


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------


def find_pending_requests(path: str, text: str, start_index: int = 0) -> List[Dict[str, object]]:
    """Find pending @hermes requests in daily notes."""
    lines = text.splitlines()
    pending: List[Dict[str, object]] = []
    auto_count = 0
    for idx, line in enumerate(lines):
        # Standard format: - [ ] @hermes ... on the same line
        if re.match(r"^\s*- \[ \] ", line) and "@hermes" in line:
            end = _block_end(lines, idx)
            block = "\n".join(lines[idx:end]).strip()
            has_explicit = bool(_ID_RE.search(line))
            request_id = _request_id(line, path, start_index + auto_count)
            if not has_explicit:
                auto_count += 1
            pending.append(
                {
                    "id": request_id,
                    "path": path,
                    "line": idx + 1,
                    "text": block,
                    "has_explicit_id": has_explicit,
                }
            )
            continue
        # Split-line format: @hermes ... on a standalone line, - [ ] on the next
        if _is_split_hermes(lines, idx):
            j = _split_next_idx(lines, idx)
            end = _block_end(lines, j)
            block = "\n".join(lines[idx:end]).strip()
            has_explicit = bool(_ID_RE.search(line))
            request_id = _request_id(line, path, start_index + auto_count)
            if not has_explicit:
                auto_count += 1
            pending.append(
                {
                    "id": request_id,
                    "path": path,
                    "line": idx + 1,
                    "lines": [idx + 1, j + 1],
                    "text": block,
                    "has_explicit_id": has_explicit,
                }
            )
    return pending


# ---------------------------------------------------------------------------
# Mark request (complete / fail)
# ---------------------------------------------------------------------------


def _mark_request(
    text: str,
    request_id: str,
    fields: List[str],
    *,
    line_number: int | None = None,
) -> str:
    """Mark a pending request as [x] and append metadata fields."""
    lines = text.splitlines()

    # --- Path A: locate by line number (most reliable) ---
    if line_number is not None:
        idx = line_number - 1
        if idx < 0 or idx >= len(lines):
            raise ValueError(f"line_number {line_number} out of range")

        line = lines[idx]

        # Standard format: - [ ] @hermes on the same line
        if re.match(r"^\s*- \[ \] ", line) and "@hermes" in line:
            end = _block_end(lines, idx)
            if not _ID_RE.search(line):
                lines[idx] = re.sub(
                    r"(@hermes\b)",
                    f"@hermes id:{request_id}",
                    line,
                    count=1,
                )
            else:
                lines[idx] = line
            lines[idx] = lines[idx].replace("- [ ]", "- [x]", 1)
            lines[end:end] = fields
            return "\n".join(lines) + "\n"

        # Split-line format: @hermes on standalone line
        if "@hermes" in line and not re.match(r"^\s*- \[ \] ", line):
            j = _split_next_idx(lines, idx)
            if j < len(lines) and re.match(r"^\s*- \[ \] ", lines[j]) and "@hermes" not in lines[j]:
                end = _block_end(lines, j)
                if not _ID_RE.search(line):
                    lines[idx] = re.sub(
                        r"(@hermes\b)",
                        f"@hermes id:{request_id}",
                        line,
                        count=1,
                    )
                lines[j] = lines[j].replace("- [ ]", "- [x]", 1)
                lines[end:end] = fields
                return "\n".join(lines) + "\n"

        raise ValueError(f"no @hermes request found at line {line_number}")

    # --- Path B: search by explicit id ---
    for idx, line in enumerate(lines):
        if "@hermes" not in line:
            continue
        match = _ID_RE.search(line)
        if not match or match.group(1) != request_id:
            continue

        if re.match(r"^\s*- \[ \] ", line):
            end = _block_end(lines, idx)
            lines[idx] = line.replace("- [ ]", "- [x]", 1)
            lines[end:end] = fields
            return "\n".join(lines) + "\n"

        j = _split_next_idx(lines, idx)
        if j < len(lines) and re.match(r"^\s*- \[ \] ", lines[j]) and "@hermes" not in lines[j]:
            end = _block_end(lines, j)
            lines[j] = lines[j].replace("- [ ]", "- [x]", 1)
            lines[end:end] = fields
            return "\n".join(lines) + "\n"

    raise ValueError(f"pending request not found: {request_id}")


def request_exists(text: str, request_id: str, *, line_number: int | None = None) -> bool:
    try:
        _mark_request(text, request_id, [], line_number=line_number)
        return True
    except ValueError:
        return False


def mark_request_completed(
    text: str,
    request_id: str,
    note: str,
    *,
    timestamp: str | None = None,
    line_number: int | None = None,
    session_id: str = "",
) -> str:
    status_msg = f"completed - {note}"
    if session_id:
        status_msg += f" | Session: {session_id}"

    try:
        intermediate = _mark_request(text, request_id, [], line_number=line_number)
    except ValueError:
        if line_number is None or not request_exists(text, request_id):
            raise
        intermediate = _mark_request(text, request_id, [])

    return upsert_status_line(intermediate, request_id, status_msg)


def mark_request_failed(
    text: str,
    request_id: str,
    error: str,
    *,
    timestamp: str | None = None,
    line_number: int | None = None,
    session_id: str = "",
) -> str:
    status_msg = f"failed - {error}"
    if session_id:
        status_msg += f" | Session: {session_id}"

    try:
        intermediate = _mark_request(text, request_id, [], line_number=line_number)
    except ValueError:
        if line_number is None or not request_exists(text, request_id):
            raise
        intermediate = _mark_request(text, request_id, [])

    return upsert_status_line(intermediate, request_id, status_msg)


# ---------------------------------------------------------------------------
# Mark request in progress
# ---------------------------------------------------------------------------


def mark_request_in_progress(
    text: str,
    request_id: str,
    *,
    session_id: str = "",
    line_number: int | None = None,
) -> str:
    """Set a request's Status to 'in progress' without changing its checkbox.

    For auto-generated IDs, injects the id: marker at *line_number* first
    so that upsert_status_line can locate the request block.
    """
    intermediate = text

    # For auto-generated IDs, inject the id: marker at the given line
    if line_number is not None:
        lines = text.splitlines()
        idx = line_number - 1
        if 0 <= idx < len(lines):
            line = lines[idx]
            if "@hermes" in line and not _ID_RE.search(line):
                lines[idx] = re.sub(
                    r"(@hermes\b)",
                    f"@hermes id:{request_id}",
                    line,
                    count=1,
                )
            intermediate = "\n".join(lines) + "\n"

    status_msg = f"in progress"
    if session_id:
        status_msg += f" | Session: {session_id}"

    return upsert_status_line(intermediate, request_id, status_msg)


# ---------------------------------------------------------------------------
# Exact replace
# ---------------------------------------------------------------------------


def replace_once(text: str, old: str, new: str) -> str:
    if not old:
        raise ValueError("old text is required")
    count = text.count(old)
    if count == 0:
        raise ValueError("old text not found")
    if count > 1:
        raise ValueError("old text occurs multiple times")
    return text.replace(old, new, 1)


# ---------------------------------------------------------------------------
# Status line (daily-note-first architecture)
# ---------------------------------------------------------------------------


def upsert_status_line(text: str, request_id: str, status_message: str) -> str:
    """Add or update a Status line inside the request block for *request_id*.

    The Status line is inserted as the first indented line after the @hermes
    marker.  If one already exists it is replaced in-place.
    """
    lines = text.splitlines()

    for idx, line in enumerate(lines):
        if "@hermes" not in line:
            continue
        match = _ID_RE.search(line)
        if not match or match.group(1) != request_id:
            continue

        # Standard format: - [ ] @hermes id:xxx on same line
        if re.match(r"^\s*- \[\s*[ x]\]", line):
            end = _block_end(lines, idx)
            status_idx = None
            for i in range(idx + 1, end):
                if _STATUS_LINE_RE.match(lines[i]):
                    status_idx = i
                    break

            new_status = f"  Status: {status_message}"

            if status_idx is not None:
                lines[status_idx] = new_status
            else:
                lines.insert(idx + 1, new_status)

            return "\n".join(lines) + "\n"

        # Split-line / standalone @hermes id:xxx line
        if not re.match(r"^\s*- \[", line):
            j = idx + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and re.match(r"^\s*- \[\s*[ x]\]", lines[j]) and "@hermes" not in lines[j]:
                end = _block_end(lines, j)
                status_idx = None
                for i in range(j + 1, end):
                    if _STATUS_LINE_RE.match(lines[i]):
                        status_idx = i
                        break

                new_status = f"  Status: {status_message}"

                if status_idx is not None:
                    lines[status_idx] = new_status
                else:
                    lines.insert(j + 1, new_status)

                return "\n".join(lines) + "\n"

    raise ValueError(f"pending request not found: {request_id}")
