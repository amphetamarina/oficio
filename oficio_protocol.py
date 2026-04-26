from __future__ import annotations

import re
from datetime import datetime
from typing import Dict, List

_PENDING_RE = re.compile(r"^(?P<indent>\s*)- \[ \] (?P<body>.*@hermes\b.*)$", re.MULTILINE)
_ID_RE = re.compile(r"\bid:([A-Za-z0-9_.:-]+)")

# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------

def _auto_id(index: int) -> str:
    """Generate an auto-ID from today's date + a sequence number."""
    date = datetime.now().strftime("%Y%m%d")
    return f"{date}-{index + 1}"


def _find_max_auto_id(text: str) -> int:
    """Find the highest auto-ID number for today's date in the given text.

    Returns the max N found, or 0 if none exist. This lets subsequent scans
    continue incrementing from where previous completions left off, since
    _mark_request injects `id:YYYYMMDD-N` into the source line on completion.
    """
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


def _format_indented_field(name: str, value: str) -> str:
    safe = str(value).replace("\n", "\n  ")
    return f"  - {name}: {safe}"


# ---------------------------------------------------------------------------
# Split-line detection
# ---------------------------------------------------------------------------

def _is_split_hermes(lines: List[str], idx: int) -> bool:
    """Return True if lines[idx] is a standalone @hermes line followed by a - [ ] line.

    Supports both `@hermes id:...` and plain `@hermes` (no explicit id).
    """
    line = lines[idx]
    if "@hermes" not in line or re.match(r"^\s*- \[ \] ", line):
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


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

def find_pending_requests(path: str, text: str, start_index: int = 0) -> List[Dict[str, object]]:
    """Find pending @hermes requests. start_index offsets auto-ID counters (for multi-file scans)."""
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
            # Use the standalone @hermes line for id detection
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
    """Mark a pending request as [x] and append metadata fields.

    If line_number is provided (1-indexed), finds the request at that line.
    Otherwise searches by explicit id: match. For auto-generated IDs,
    the id is injected into the @hermes line at mark time.
    """
    lines = text.splitlines()

    # --- Path A: locate by line number (most reliable) ---
    if line_number is not None:
        idx = line_number - 1  # convert to 0-indexed
        if idx < 0 or idx >= len(lines):
            raise ValueError(f"line_number {line_number} out of range")

        line = lines[idx]

        # Standard format: - [ ] @hermes on the same line
        if re.match(r"^\s*- \[ \] ", line) and "@hermes" in line:
            end = _block_end(lines, idx)
            # Inject auto-ID if missing
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
                # Inject auto-ID if missing
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

        # Standard format: @hermes and - [ ] on the same line
        if re.match(r"^\s*- \[ \] ", line):
            end = _block_end(lines, idx)
            lines[idx] = line.replace("- [ ]", "- [x]", 1)
            lines[end:end] = fields
            return "\n".join(lines) + "\n"

        # Split-line format
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
) -> str:
    stamp = _timestamp(timestamp)
    return _mark_request(
        text,
        request_id,
        [
            _format_indented_field("completed", stamp),
            _format_indented_field("note", note),
        ],
        line_number=line_number,
    )


def mark_request_failed(
    text: str,
    request_id: str,
    error: str,
    *,
    timestamp: str | None = None,
    line_number: int | None = None,
) -> str:
    stamp = _timestamp(timestamp)
    return _mark_request(
        text,
        request_id,
        [
            _format_indented_field("status", "failed"),
            _format_indented_field("failed", stamp),
            _format_indented_field("error", error),
        ],
        line_number=line_number,
    )


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
# Log entries
# ---------------------------------------------------------------------------

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


def start_request_log_entry(
    existing_log: str,
    request_id: str,
    source_path: str,
    summary: str,
    *,
    timestamp: str | None = None,
) -> str:
    """Write a pending log entry when an agent starts working on a request.

    Idempotent: if a log section for this request_id already exists, returns
    existing_log unchanged.
    """
    # Check if a section for this id already exists
    if re.search(rf"^## {re.escape(request_id)}$", existing_log, re.MULTILINE):
        return existing_log

    return append_request_log_entry(
        existing_log,
        request_id,
        "pending",
        source_path,
        summary,
        timestamp=timestamp,
    )


def update_request_log_status(
    existing_log: str,
    request_id: str,
    new_status: str,
    message: str,
    *,
    timestamp: str | None = None,
) -> str:
    """Update the status of an existing log section from pending → completed/failed.

    Finds the `## request_id` section and replaces `status: pending` with the
    new status, appending the message and timestamp.
    """
    section_header = f"## {request_id}"

    # Find the section
    idx = existing_log.find(section_header)
    if idx == -1:
        # No pending entry — create one directly
        return append_request_log_entry(
            existing_log, request_id, new_status, "", message, timestamp=timestamp
        )

    # Find the end of this section (next ## or end of string)
    rest = existing_log[idx + len(section_header):]
    next_section = re.search(r"\n## ", rest)
    if next_section:
        section_body = rest[:next_section.start()]
        after = rest[next_section.start():]
    else:
        section_body = rest
        after = ""

    # Replace status: pending with new status
    updated_body = section_body.replace("- status: pending", f"- status: {new_status}", 1)

    # Append the message
    if message.strip():
        if not updated_body.endswith("\n"):
            updated_body += "\n"
        updated_body += f"\n{message.strip()}\n"

    return existing_log[:idx] + section_header + updated_body + after


def summarize_log_entries(log_text: str, *, source_path: str, default_date: str = "") -> List[Dict[str, str]]:
    entries: List[Dict[str, str]] = []
    sections = re.split(r"(?m)^## ", log_text)
    for section in sections[1:]:
        lines = section.splitlines()
        if not lines:
            continue
        request_id = lines[0].strip()
        status = "unknown"
        at = ""
        source = source_path
        message_lines: List[str] = []
        body_started = False
        for raw in lines[1:]:
            line = raw.strip()
            if line.startswith("- status:"):
                status = line.split(":", 1)[1].strip()
                continue
            if line.startswith("- at:"):
                at = line.split(":", 1)[1].strip()
                continue
            if line.startswith("- source:"):
                source = line.split(":", 1)[1].strip()
                continue
            if raw.strip() == "" and not body_started:
                continue
            body_started = True
            if raw.strip():
                message_lines.append(raw.strip())
        entry_date = default_date or (at[:10] if len(at) >= 10 else "")
        entries.append(
            {
                "date": entry_date,
                "id": request_id,
                "status": status,
                "at": at,
                "source": source,
                "note": " ".join(message_lines).strip(),
            }
        )
    return entries


def render_summary_markdown(entries: List[Dict[str, str]]) -> str:
    lines = [
        "| Date | ID | Status | Note |",
        "|---|---|---|---|",
    ]
    for entry in entries:
        note = entry.get("note", "").replace("|", "\\|")
        lines.append(
            f"| {entry.get('date', '')} | {entry.get('id', '')} | {entry.get('status', '')} | {note} |"
        )
    return "\n".join(lines)


def render_summary_plain(entries: List[Dict[str, str]]) -> str:
    return "\n".join(
        f"{entry.get('date', '')} | {entry.get('id', '')} | {entry.get('status', '')} | {entry.get('note', '')}"
        for entry in entries
    )


def append_inbox_request(
    text: str,
    description: str,
    *,
    request_id: str,
    marker: str = "@hermes",
) -> str:
    description = description.strip()
    if not description:
        raise ValueError("description is required")
    request_id = request_id.strip()
    if not request_id:
        raise ValueError("id is required")
    request_line = f"- [ ] {marker} id:{request_id} {description}"
    base = text.rstrip()
    if base:
        return base + "\n\n" + request_line + "\n"
    return request_line + "\n"
