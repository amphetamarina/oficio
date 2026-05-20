"""Session identity is agent-defined.

ofício only cares about a string the agent attaches to a request so the trace
inline in the note matches whatever the agent calls a thread/session. Set
``OFICIO_SESSION_ID`` in the agent's environment (or pass ``session_id`` to
each tool) and it shows up next to the request's ``Status:``.
"""

import os


def current_session_id() -> str:
    return os.environ.get("OFICIO_SESSION_ID", "").strip()


def format_status(status: str, *, session_id: str = "") -> str:
    if not session_id:
        return status
    return f"{status} | Session: {session_id}"
