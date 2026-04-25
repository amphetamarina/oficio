from oficio_protocol import (
    append_request_log_entry,
    find_pending_requests,
    mark_request_completed,
    mark_request_failed,
    replace_once,
)


def test_find_pending_requests_detects_marked_checkbox():
    text = """# Inbox

- [ ] @hermes id:test-1
  Please summarize [[Note]].

- [x] @hermes id:done
  Already done.
"""

    pending = find_pending_requests("agent/oficio/inbox.md", text)

    assert len(pending) == 1
    assert pending[0]["id"] == "test-1"
    assert pending[0]["path"] == "agent/oficio/inbox.md"
    assert "Please summarize" in pending[0]["text"]


def test_mark_request_completed_records_timestamp_and_note():
    text = """# Inbox

- [ ] @hermes id:test-1
  Please summarize [[Note]].
"""

    updated = mark_request_completed(
        text,
        "test-1",
        "summary written",
        timestamp="2026-04-25T20:00:00-03:00",
    )

    assert "- [x] @hermes id:test-1" in updated
    assert "- completed: 2026-04-25T20:00:00-03:00" in updated
    assert "- note: summary written" in updated


def test_mark_request_completed_uses_exact_id_not_prefix_match():
    text = """# Inbox

- [ ] @hermes id:test-10
  Please do later thing.

- [ ] @hermes id:test-1
  Please do exact thing.
"""

    updated = mark_request_completed(
        text,
        "test-1",
        "exact one done",
        timestamp="2026-04-25T20:00:00-03:00",
    )

    assert "- [ ] @hermes id:test-10\n  Please do later thing." in updated
    assert "- [x] @hermes id:test-1" in updated
    assert "- note: exact one done" in updated


def test_mark_request_failed_records_status_timestamp_and_error():
    text = """# Inbox

- [ ] @hermes id:test-1
  Please summarize [[Note]].
"""

    updated = mark_request_failed(
        text,
        "test-1",
        "note not found",
        timestamp="2026-04-25T20:00:00-03:00",
    )

    assert "- [x] @hermes id:test-1" in updated
    assert "- status: failed" in updated
    assert "- failed: 2026-04-25T20:00:00-03:00" in updated
    assert "- error: note not found" in updated


def test_replace_once_replaces_unique_text():
    updated = replace_once("hello old world", "old", "new")

    assert updated == "hello new world"


def test_replace_once_rejects_missing_text():
    try:
        replace_once("hello world", "missing", "new")
    except ValueError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_replace_once_rejects_ambiguous_text():
    try:
        replace_once("old and old", "old", "new")
    except ValueError as exc:
        assert "multiple" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_replace_once_rejects_empty_old_text():
    try:
        replace_once("hello", "", "new")
    except ValueError as exc:
        assert "old text is required" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_append_request_log_entry_creates_heading_and_fields():
    updated = append_request_log_entry(
        "# ofício log · 2026-04-25\n",
        "test-1",
        "completed",
        "agent/oficio/inbox.md",
        "summary written",
        timestamp="2026-04-25T20:00:00-03:00",
    )

    assert "## test-1" in updated
    assert "- status: completed" in updated
    assert "- at: 2026-04-25T20:00:00-03:00" in updated
    assert "- source: agent/oficio/inbox.md" in updated
    assert "summary written" in updated
