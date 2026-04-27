import re

import pytest

from oficio_protocol import (
    _get_current_session_id,
    find_pending_requests,
    mark_request_completed,
    mark_request_failed,
    mark_request_in_progress,
    replace_once,
    session_log_path,
    upsert_agent_response,
)


def test_scan_finds_standard_split_and_auto_id_requests():
    text = """# Daily

- [ ] @hermes id:explicit-one
  Do one thing.

@hermes
- [ ] Do the split-line thing.

- [x] @hermes id:done
  Already done.
"""

    pending = find_pending_requests("Daily/2026-04-27.md", text)

    assert [item["id"] for item in pending[:1]] == ["explicit-one"]
    assert len(pending) == 2
    assert pending[1]["has_explicit_id"] is False
    assert re.match(r"\d{8}-1", str(pending[1]["id"]))
    assert pending[1]["lines"] == [6, 7]


def test_start_injects_auto_id_and_writes_session_log_link(monkeypatch):
    monkeypatch.setenv("HOME", "/home/marina")
    text = "# Daily\n\n- [ ] @hermes do it.\n"

    updated = mark_request_in_progress(
        text,
        "20260427-1",
        line_number=3,
        session_id="20260427_091500_8da571",
    )

    assert "- [ ] @hermes id:20260427-1 do it." in updated
    assert "Status: in progress | Session: 20260427_091500_8da571" in updated
    assert "[/home/marina/.hermes/sessions/session_20260427_091500_8da571.json]" in updated


def test_complete_marks_checkbox_and_adds_agent_response():
    text = """# Daily

- [ ] @hermes id:summary
  Summarize [[Meeting]].
"""

    updated = mark_request_completed(
        text,
        "summary",
        "summary written",
        session_id="session-123",
        response="## Summary\n\nDone.",
    )

    assert "- [x] @hermes id:summary" in updated
    assert "Status: completed - summary written | Session: session-123" in updated
    assert "Agent response:" in updated
    assert "````markdown" in updated
    assert "  ## Summary" in updated


def test_complete_uses_exact_id_not_prefix():
    text = """# Daily

- [ ] @hermes id:test-10
  Later.

- [ ] @hermes id:test-1
  Now.
"""

    updated = mark_request_completed(text, "test-1", "done")

    assert "- [ ] @hermes id:test-10" in updated
    assert "- [x] @hermes id:test-1" in updated


def test_split_line_complete_and_fail_keep_marker_and_mark_checkbox():
    text = """# Daily

@hermes id:split
- [ ] Do the thing.
"""

    completed = mark_request_completed(text, "split", "done")
    failed = mark_request_failed(text, "split", "nope")

    assert "@hermes id:split" in completed
    assert "- [x] Do the thing." in completed
    assert "Status: completed - done" in completed
    assert "Status: failed - nope" in failed


def test_line_number_protects_auto_id_completion():
    text = """# Daily

- [ ] @hermes first.

- [ ] @hermes second.
"""

    updated = mark_request_completed(text, "20260427-2", "second done", line_number=5)

    assert "- [ ] @hermes first." in updated
    assert "- [x] @hermes id:20260427-2 second." in updated


def test_stale_line_falls_back_to_matching_id():
    text = """# Daily

- [x] @hermes id:other
  Status: completed - done
  Other.

- [ ] @hermes id:target
  Target.
"""

    updated = mark_request_completed(text, "target", "done", line_number=3)

    assert "- [x] @hermes id:target" in updated


def test_agent_response_updates_existing_block():
    text = """# Daily

- [x] @hermes id:task
  Status: completed - old
  Agent response:
  ```markdown
  old
  ```
"""

    updated = upsert_agent_response(text, "task", "new")

    assert "  old\n" not in updated
    assert "  new\n" in updated


def test_replace_once_is_exact_and_unambiguous():
    assert replace_once("alpha beta", "beta", "gamma") == "alpha gamma"
    with pytest.raises(ValueError):
        replace_once("same same", "same", "x")
    with pytest.raises(ValueError):
        replace_once("abc", "", "x")


def test_session_log_path_uses_hermes_session_location(monkeypatch):
    monkeypatch.setenv("HOME", "/home/marina")

    assert session_log_path("abc") == "/home/marina/.hermes/sessions/session_abc.json"


def test_current_session_id_prefers_environment(monkeypatch):
    monkeypatch.setenv("HERMES_SESSION_ID", "from-env")

    assert _get_current_session_id() == "from-env"
