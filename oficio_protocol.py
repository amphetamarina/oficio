from __future__ import annotations

import re
from datetime import datetime, timezone
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


def mark_request_completed(text: str, request_id: str, result: str) -> str:
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if "@hermes" not in line or f"id:{request_id}" not in line:
            continue
        if "- [ ]" not in line:
            continue
        end = _block_end(lines, idx)
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        lines[idx] = line.replace("- [ ]", "- [x]", 1)
        addition = ["", f"  Result: ({stamp})"]
        addition.extend(f"  {part}" if part else "" for part in result.splitlines())
        lines[end:end] = addition
        return "\n".join(lines) + "\n"
    raise ValueError(f"pending request not found: {request_id}")
