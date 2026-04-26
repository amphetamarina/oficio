#!/usr/bin/env python3
"""ofício vault sync — debounced scanner for pending @hermes requests.

Runs as a poller (designed for Hermes cron): each invocation checks whether
the watched vault files have been stable long enough to scan, then reports
any *new* pending requests that haven't been seen before.

Debounce: files modified less than DEBOUNCE_SECONDS ago are skipped
(the user may still be writing). Only files stable for >= DEBOUNCE_SECONDS
are scanned for pending requests.

Usage:
  python scripts/oficio-sync.py              # scan inbox + daily note
  python scripts/oficio-sync.py --once        # scan immediately, skip debounce
  python scripts/oficio-sync.py --watch       # loop forever (for terminal use)

Output: JSON with "new_requests" list (empty if none) + "scanned" paths.
Exit code 0 always (errors go to stderr); cron sees new requests via stdout.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Bootstrap — add parent dir to sys.path so we can import oficio modules
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO))

from oficio_config import default_config, load_config, resolve_daily_path, resolve_inbox_path, vault_abspath
from oficio_protocol import find_pending_requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DEBOUNCE_SECONDS = float(os.environ.get("OFICIO_DEBOUNCE", "15"))
POLL_INTERVAL = float(os.environ.get("OFICIO_POLL_INTERVAL", "10"))
STATE_FILE_NAME = ".oficio-sync-state.json"


def _state_path(cfg: Dict[str, Any]) -> Path:
    """State file lives in the vault agent dir."""
    agent_dir = Path(str(cfg.get("agent_dir", ""))).expanduser()
    return agent_dir / STATE_FILE_NAME


def _load_state(cfg: Dict[str, Any]) -> Dict[str, Any]:
    path = _state_path(cfg)
    if not path.exists():
        return {"seen_ids": [], "last_mtimes": {}}
    try:
        with open(path) as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {"seen_ids": [], "last_mtimes": {}}


def _save_state(cfg: Dict[str, Any], state: Dict[str, Any]) -> None:
    path = _state_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        json.dump(state, fh, indent=2, default=str)


def _file_is_stable(abspath: Path) -> bool:
    """Return True if the file hasn't been modified in the debounce window."""
    if not abspath.exists():
        return True  # nothing to scan
    age = time.time() - abspath.stat().st_mtime
    return age >= DEBOUNCE_SECONDS


def _gather_paths(cfg: Dict[str, Any], once: bool = False) -> List[str]:
    """Return vault-relative paths to scan."""
    paths = [resolve_inbox_path(cfg)]
    if cfg.get("scan_daily", True):
        paths.append(resolve_daily_path(cfg))
    return paths


def scan(cfg: Dict[str, Any], once: bool = False) -> Dict[str, Any]:
    """Scan watched paths for pending requests, debouncing unstable files.

    Returns a dict with:
      - new_requests: list of pending requests not seen before
      - scanned: paths that were actually scanned (stable or --once)
      - skipped: paths skipped due to debounce
    """
    paths = _gather_paths(cfg, once=once)
    state = _load_state(cfg)
    seen_ids: List[str] = state.get("seen_ids", [])
    last_mtimes: Dict[str, float] = state.get("last_mtimes", {})

    new_requests: List[Dict[str, Any]] = []
    scanned: List[str] = []
    skipped: List[str] = []

    for rel_path in paths:
        try:
            abspath = vault_abspath(cfg, rel_path)
        except ValueError:
            continue

        if not abspath.exists():
            continue

        current_mtime = abspath.stat().st_mtime
        if not once and not _file_is_stable(abspath):
            skipped.append(rel_path)
            continue

        # Only re-scan if the file has actually changed since last scan
        prev_mtime = last_mtimes.get(rel_path, 0)
        if not once and current_mtime <= prev_mtime:
            scanned.append(rel_path)
            continue

        scanned.append(rel_path)
        last_mtimes[rel_path] = current_mtime

        try:
            text = abspath.read_text()
            pending = find_pending_requests(rel_path, text)

            for req in pending:
                req_id = str(req["id"])
                if req_id not in seen_ids:
                    new_requests.append(req)
                    seen_ids.append(req_id)
        except (OSError, ValueError) as exc:
            print(f"oficio-sync: error reading {rel_path}: {exc}", file=sys.stderr)

    # Prune seen_ids — keep only IDs that still exist as pending
    all_current_ids: List[str] = []
    for rel_path in paths:
        try:
            abspath = vault_abspath(cfg, rel_path)
            if abspath.exists():
                pending = find_pending_requests(rel_path, abspath.read_text())
                all_current_ids.extend(str(r["id"]) for r in pending)
        except Exception:
            pass

    seen_ids = [i for i in seen_ids if i in set(all_current_ids)]
    state["seen_ids"] = seen_ids
    state["last_mtimes"] = last_mtimes
    _save_state(cfg, state)

    return {
        "new_requests": new_requests,
        "scanned": scanned,
        "skipped": skipped,
        "debounce_seconds": DEBOUNCE_SECONDS,
    }


def main() -> None:
    once = "--once" in sys.argv
    watch = "--watch" in sys.argv

    cfg = load_config()
    if "--paths" in sys.argv:  # hidden debug flag
        for p in _gather_paths(cfg):
            print(p)
        return

    if watch:
        print(f"oficio-sync: watching with {DEBOUNCE_SECONDS}s debounce…", file=sys.stderr)
        try:
            while True:
                result = scan(cfg, once=False)
                if result["new_requests"]:
                    print(json.dumps(result, ensure_ascii=False))
                time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print("\noficio-sync: stopped.", file=sys.stderr)
            return
    else:
        result = scan(cfg, once=once)
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
