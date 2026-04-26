from oficio_protocol import (
    append_request_log_entry,
    find_pending_requests,
    mark_request_completed,
    mark_request_failed,
    replace_once,
    start_request_log_entry,
    update_request_log_status,
)


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

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
    assert pending[0]["has_explicit_id"] is True


def test_find_pending_requests_without_explicit_id_generates_auto_id():
    text = """# Inbox

- [ ] @hermes do something simple.
"""

    pending = find_pending_requests("agent/oficio/inbox.md", text)

    assert len(pending) == 1
    assert pending[0]["path"] == "agent/oficio/inbox.md"
    assert pending[0]["has_explicit_id"] is False
    # Auto-ID should be date-based: YYYYMMDD-N
    assert len(pending[0]["id"]) >= 9  # at least YYYYMMDD-1
    assert "do something simple" in pending[0]["text"]


def test_find_pending_requests_multiple_auto_ids_increment():
    text = """# Inbox

- [ ] @hermes first task.

- [ ] @hermes second task.
"""

    pending = find_pending_requests("agent/oficio/inbox.md", text)

    assert len(pending) == 2
    assert pending[0]["has_explicit_id"] is False
    assert pending[1]["has_explicit_id"] is False
    assert pending[0]["id"] != pending[1]["id"]
    # Both should be date-based
    assert pending[0]["id"].endswith("-1")
    assert pending[1]["id"].endswith("-2")


def test_find_pending_requests_mixed_explicit_and_auto_ids():
    text = """# Inbox

- [ ] @hermes id:explicit-one
  I have an id.

- [ ] @hermes I am auto-generated.
"""

    pending = find_pending_requests("agent/oficio/inbox.md", text)

    assert len(pending) == 2
    assert pending[0]["id"] == "explicit-one"
    assert pending[0]["has_explicit_id"] is True
    assert pending[1]["has_explicit_id"] is False
    assert pending[1]["id"].endswith("-2")


# ---------------------------------------------------------------------------
# Split-line format
# ---------------------------------------------------------------------------

def test_find_pending_requests_detects_split_line_format():
    text = """# Daily

@hermes id:iterate-001
- [ ] cheque os templates no Obsidian.

Some other content.
"""

    pending = find_pending_requests("Daily/2026-04-25.md", text)

    assert len(pending) == 1
    assert pending[0]["id"] == "iterate-001"
    assert pending[0]["path"] == "Daily/2026-04-25.md"
    assert "cheque os templates" in pending[0]["text"]
    assert "@hermes id:iterate-001" in pending[0]["text"]
    assert pending[0]["has_explicit_id"] is True


def test_find_pending_requests_split_line_without_explicit_id():
    text = """# Daily

@hermes
- [ ] cheque os templates no Obsidian.
"""

    pending = find_pending_requests("Daily/2026-04-25.md", text)

    assert len(pending) == 1
    assert pending[0]["has_explicit_id"] is False
    assert "cheque os templates" in pending[0]["text"]
    assert "lines" in pending[0]  # split-line has lines field
    assert len(pending[0]["id"]) >= 9


def test_find_pending_requests_split_line_ignores_standalone_hermes_without_checkbox():
    text = """# Daily

@hermes id:no-checkbox
Some text without a checkbox item.

- [ ] @hermes id:normal-001
  This is a normal request.
"""

    pending = find_pending_requests("Daily/2026-04-25.md", text)

    assert len(pending) == 1
    assert pending[0]["id"] == "normal-001"


# ---------------------------------------------------------------------------
# Mark completed (with explicit IDs)
# ---------------------------------------------------------------------------

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


def test_mark_request_completed_split_line_format():
    text = """# Daily

@hermes id:iterate-001
- [ ] cheque os templates no Obsidian.
"""

    updated = mark_request_completed(
        text,
        "iterate-001",
        "templates configurados",
        timestamp="2026-04-25T21:00:00-03:00",
    )

    assert "- [x] cheque os templates no Obsidian." in updated
    assert "- completed: 2026-04-25T21:00:00-03:00" in updated
    assert "- note: templates configurados" in updated
    assert "@hermes id:iterate-001" in updated  # preserved


# ---------------------------------------------------------------------------
# Mark completed (with line_number — auto-generated IDs)
# ---------------------------------------------------------------------------

def test_mark_request_completed_with_line_number_injects_auto_id():
    text = """# Inbox

- [ ] @hermes do something simple.
"""

    updated = mark_request_completed(
        text,
        "20260425-1",
        "task done",
        timestamp="2026-04-25T20:00:00-03:00",
        line_number=3,  # 1-indexed line where @hermes appears
    )

    assert "- [x] @hermes id:20260425-1" in updated
    assert "- completed: 2026-04-25T20:00:00-03:00" in updated
    assert "- note: task done" in updated


def test_mark_request_completed_with_line_number_preserves_other_tasks():
    text = """# Inbox

- [ ] @hermes id:keep-me
  I stay pending.

- [ ] @hermes finish me.
"""

    updated = mark_request_completed(
        text,
        "20260425-2",
        "only second marked",
        timestamp="2026-04-25T20:00:00-03:00",
        line_number=6,  # second @hermes line
    )

    assert "- [ ] @hermes id:keep-me" in updated  # untouched
    assert "- [x] @hermes id:20260425-2" in updated  # marked + id injected


def test_mark_request_completed_split_line_with_line_number_injects_auto_id():
    text = """# Daily

@hermes
- [ ] do something.
"""

    updated = mark_request_completed(
        text,
        "20260425-1",
        "done via line",
        timestamp="2026-04-25T21:00:00-03:00",
        line_number=3,  # the @hermes line
    )

    assert "- [x] do something." in updated
    assert "@hermes id:20260425-1" in updated  # injected
    assert "- completed: 2026-04-25T21:00:00-03:00" in updated
    assert "- note: done via line" in updated


# ---------------------------------------------------------------------------
# Mark failed
# ---------------------------------------------------------------------------

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


def test_mark_request_failed_split_line_format():
    text = """# Daily

@hermes id:iterate-001
- [ ] cheque os templates no Obsidian.
"""

    updated = mark_request_failed(
        text,
        "iterate-001",
        "templates folder not found",
        timestamp="2026-04-25T21:00:00-03:00",
    )

    assert "- [x] cheque os templates no Obsidian." in updated
    assert "- status: failed" in updated
    assert "- failed: 2026-04-25T21:00:00-03:00" in updated
    assert "- error: templates folder not found" in updated
    assert "@hermes id:iterate-001" in updated  # preserved


def test_mark_request_failed_with_line_number_injects_auto_id():
    text = """# Inbox

- [ ] @hermes tricky task.
"""

    updated = mark_request_failed(
        text,
        "20260425-1",
        "something broke",
        timestamp="2026-04-25T20:00:00-03:00",
        line_number=3,
    )

    assert "- [x] @hermes id:20260425-1" in updated
    assert "- status: failed" in updated
    assert "- error: something broke" in updated


# ---------------------------------------------------------------------------
# Not found errors
# ---------------------------------------------------------------------------

def test_mark_request_raises_for_nonexistent_line_number():
    text = """# Inbox

- [ ] @hermes do stuff.
"""

    try:
        mark_request_completed(text, "any-id", "done", line_number=99)
    except ValueError as exc:
        assert "out of range" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_mark_request_raises_for_line_without_hermes():
    text = """# Inbox

- [ ] no hermes here.

- [ ] @hermes real task.
"""

    try:
        mark_request_completed(text, "any-id", "done", line_number=3)  # no @hermes on line 3
    except ValueError as exc:
        pass
    else:
        raise AssertionError("expected ValueError")


# ---------------------------------------------------------------------------
# Replace
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Log entries
# ---------------------------------------------------------------------------

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


def test_start_request_log_entry_creates_pending_section():
    updated = start_request_log_entry(
        "# ofício log\n",
        "task-1",
        "agent/oficio/inbox.md",
        "will summarize notes",
    )

    assert "## task-1" in updated
    assert "- status: pending" in updated
    assert "- source: agent/oficio/inbox.md" in updated
    assert "will summarize notes" in updated


def test_start_request_log_entry_is_idempotent():
    log = """# ofício log

## task-1

- status: pending
- at: 2026-04-25T20:00:00-03:00
- source: agent/oficio/inbox.md

will summarize notes
"""

    updated = start_request_log_entry(
        log, "task-1", "agent/oficio/inbox.md", "should not appear"
    )

    assert updated == log  # unchanged


def test_update_request_log_status_pending_to_completed():
    log = """# ofício log

## task-1

- status: pending
- at: 2026-04-25T20:00:00-03:00
- source: agent/oficio/inbox.md

will summarize notes
"""

    updated = update_request_log_status(
        log, "task-1", "completed", "summaries done",
        timestamp="2026-04-25T20:05:00-03:00",
    )

    assert "## task-1" in updated
    assert "- status: completed" in updated
    assert "summaries done" in updated
    assert "- status: pending" not in updated  # replaced


def test_update_request_log_status_pending_to_failed():
    log = """# ofício log

## task-1

- status: pending
- at: 2026-04-25T20:00:00-03:00
- source: agent/oficio/inbox.md

will summarize notes
"""

    updated = update_request_log_status(
        log, "task-1", "failed", "note not found",
        timestamp="2026-04-25T20:05:00-03:00",
    )

    assert "## task-1" in updated
    assert "- status: failed" in updated
    assert "note not found" in updated


def test_update_request_log_status_creates_entry_if_none_exists():
    log = "# ofício log\n"

    updated = update_request_log_status(
        log, "new-task", "completed", "direct complete",
        timestamp="2026-04-25T20:00:00-03:00",
    )

    assert "## new-task" in updated
    assert "- status: completed" in updated
    assert "direct complete" in updated


def test_update_request_log_status_preserves_other_sections():
    log = """# ofício log

## other-task

- status: completed
- at: 2026-04-25T19:00:00-03:00
- source: inbox.md

already done.

## task-1

- status: pending
- at: 2026-04-25T20:00:00-03:00
- source: inbox.md

working on it.
"""

    updated = update_request_log_status(
        log, "task-1", "completed", "finished",
        timestamp="2026-04-25T20:05:00-03:00",
    )

    assert "## other-task" in updated
    assert "already done" in updated
    assert "## task-1" in updated
    assert "- status: completed" in updated
    assert "finished" in updated
