from __future__ import annotations

import json
import os
from pathlib import Path


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
        except (OSError, json.JSONDecodeError):
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


def current_session_id() -> str:
    return SessionLogs().current_session_id()


def session_log_path(session_id: str) -> str:
    return SessionLogs().log_path(session_id)


def session_log_link(session_id: str) -> str:
    return SessionLogs().log_link(session_id)


def format_status(status: str, *, session_id: str = "") -> str:
    if not session_id:
        return status
    return f"{status} | Session: {session_id} | Log: {session_log_link(session_id)}"
