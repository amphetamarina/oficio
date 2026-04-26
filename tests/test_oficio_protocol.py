from oficio_protocol import (
    find_pending_requests,
    mark_request_completed,
    mark_request_failed,
    mark_request_in_progress,
    replace_once,
    upsert_status_line,
)


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

def test_find_pending_requests_detects_marked_checkbox():
    text = """# Daily

- [ ] @hermes id:test-1
  Please summarize [[Note]].

- [x] @hermes id:done
  Already done.
"""

    pending = find_pending_requests("Daily/2026-04-26.md", text)

    assert len(pending) == 1
    assert pending[0]["id"] == "test-1"
    assert pending[0]["path"] == "Daily/2026-04-26.md"
    assert "Please summarize" in pending[0]["text"]
    assert pending[0]["has_explicit_id"] is True


def test_find_pending_requests_without_explicit_id_generates_auto_id():
    text = """# Daily

- [ ] @hermes do something simple.
"""

    pending = find_pending_requests("Daily/2026-04-26.md", text)

    assert len(pending) == 1
    assert pending[0]["path"] == "Daily/2026-04-26.md"
    assert pending[0]["has_explicit_id"] is False
    # Auto-ID should be date-based: YYYYMMDD-N
    assert len(pending[0]["id"]) >= 9  # at least YYYYMMDD-1
    assert "do something simple" in pending[0]["text"]


def test_find_pending_requests_multiple_auto_ids_increment():
    text = """# Daily

- [ ] @hermes first task.

- [ ] @hermes second task.
"""

    pending = find_pending_requests("Daily/2026-04-26.md", text)

    assert len(pending) == 2
    assert pending[0]["has_explicit_id"] is False
    assert pending[1]["has_explicit_id"] is False
    assert pending[0]["id"] != pending[1]["id"]
    # Both should be date-based
    assert pending[0]["id"].endswith("-1")
    assert pending[1]["id"].endswith("-2")


def test_find_pending_requests_mixed_explicit_and_auto_ids():
    text = """# Daily

- [ ] @hermes id:explicit-one
  I have an id.

- [ ] @hermes I am auto-generated.
"""

    pending = find_pending_requests("Daily/2026-04-26.md", text)

    assert len(pending) == 2
    assert pending[0]["id"] == "explicit-one"
    assert pending[0]["has_explicit_id"] is True
    assert pending[1]["has_explicit_id"] is False
    # Explicit IDs don't consume auto-index slots; second is first auto
    assert pending[1]["id"].endswith("-1")


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
# Mark completed (Status-line architecture)
# ---------------------------------------------------------------------------

def test_mark_request_completed_writes_status_line():
    text = """# Daily

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
    assert "Status: completed - summary written" in updated


def test_mark_request_completed_uses_exact_id_not_prefix_match():
    text = """# Daily

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

    assert "- [ ] @hermes id:test-10" in updated
    assert "- [x] @hermes id:test-1" in updated
    assert "Status: completed - exact one done" in updated


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
    assert "Status: completed - templates configurados" in updated
    assert "@hermes id:iterate-001" in updated  # preserved


# ---------------------------------------------------------------------------
# Mark completed (with line_number — auto-generated IDs)
# ---------------------------------------------------------------------------

def test_mark_request_completed_with_line_number_injects_auto_id():
    text = """# Daily

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
    assert "Status: completed - task done" in updated


def test_mark_request_completed_with_line_number_preserves_other_tasks():
    text = """# Daily

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
    assert "Status: completed - only second marked" in updated


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
    assert "Status: completed - done via line" in updated


# ---------------------------------------------------------------------------
# Mark failed (Status-line architecture)
# ---------------------------------------------------------------------------

def test_mark_request_failed_writes_status_line():
    text = """# Daily

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
    assert "Status: failed - note not found" in updated


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
    assert "Status: failed - templates folder not found" in updated
    assert "@hermes id:iterate-001" in updated  # preserved


def test_mark_request_failed_with_line_number_injects_auto_id():
    text = """# Daily

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
    assert "Status: failed - something broke" in updated


# ---------------------------------------------------------------------------
# Not found errors
# ---------------------------------------------------------------------------

def test_mark_request_raises_for_nonexistent_line_number():
    text = """# Daily

- [ ] @hermes do stuff.
"""

    try:
        mark_request_completed(text, "any-id", "done", line_number=99)
    except ValueError as exc:
        assert "out of range" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_mark_request_raises_for_line_without_hermes():
    text = """# Daily

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
# Status line
# ---------------------------------------------------------------------------

def test_upsert_status_line_adds_to_standard_format():
    text = """# Daily

- [ ] @hermes id:test-1
  Please summarize [[Note]].
"""

    updated = upsert_status_line(text, "test-1", "in-progress - working")

    assert "Status: in-progress - working" in updated
    assert "- [ ] @hermes id:test-1" in updated  # checkbox unchanged


def test_upsert_status_line_updates_existing():
    text = """# Daily

- [ ] @hermes id:test-1
  Status: pending - waiting
  Please summarize [[Note]].
"""

    updated = upsert_status_line(text, "test-1", "in-progress - doing it")

    assert "Status: in-progress - doing it" in updated
    assert "Status: pending - waiting" not in updated


def test_upsert_status_line_adds_to_split_line_format():
    text = """# Daily

@hermes id:iterate-001
- [ ] cheque os templates.
"""

    updated = upsert_status_line(text, "iterate-001", "in-progress - checking")

    assert "- [ ] cheque os templates." in updated
    assert "Status: in-progress - checking" in updated


def test_upsert_status_line_updates_split_line_existing():
    text = """# Daily

@hermes id:iterate-001
- [ ] cheque os templates.
  Status: pending - start
"""

    updated = upsert_status_line(text, "iterate-001", "completed - done")

    assert "Status: completed - done" in updated
    assert "Status: pending - start" not in updated


def test_upsert_status_line_handles_post_marked_split_line():
    """After _mark_request, a split-line has @hermes id:xxx + - [x] below."""
    text = """# Daily

@hermes id:iterate-001
- [x] cheque os templates.
"""

    updated = upsert_status_line(text, "iterate-001", "completed - templates ok")

    assert "Status: completed - templates ok" in updated
    assert "- [x] cheque os templates." in updated


def test_upsert_status_line_raises_for_missing_id():
    text = """# Daily

- [ ] @hermes id:other
  stuff.
"""

    try:
        upsert_status_line(text, "missing", "done")
    except ValueError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("expected ValueError")


# ---------------------------------------------------------------------------
# Mark in progress
# ---------------------------------------------------------------------------


def test_mark_request_in_progress_adds_status_line_without_changing_checkbox():
    text = """# Daily

- [ ] @hermes id:test-1
  Please summarize [[Note]].
"""

    updated = mark_request_in_progress(text, "test-1")

    assert "- [ ] @hermes id:test-1" in updated  # checkbox unchanged
    assert "Status: in progress" in updated


def test_mark_request_in_progress_includes_session_id():
    text = """# Daily

- [ ] @hermes id:test-1
  Please summarize [[Note]].
"""

    updated = mark_request_in_progress(text, "test-1", session_id="20260426_164315_8da571")

    assert "- [ ] @hermes id:test-1" in updated
    assert "Status: in progress | Session: 20260426_164315_8da571" in updated


def test_mark_request_in_progress_with_line_number_injects_auto_id():
    text = """# Daily

- [ ] @hermes do something without id.
"""

    updated = mark_request_in_progress(
        text, "20260426-1", session_id="sess-123", line_number=3
    )

    assert "- [ ] @hermes id:20260426-1" in updated  # id injected
    assert "Status: in progress | Session: sess-123" in updated
    assert "[x]" not in updated.split("@hermes")[0]  # checkbox still [ ]


def test_mark_request_in_progress_raises_for_missing_id_without_line():
    text = """# Daily

- [ ] @hermes id:other
  stuff.
"""

    try:
        mark_request_in_progress(text, "missing")
    except ValueError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_mark_request_in_progress_updates_existing_status():
    text = """# Daily

- [ ] @hermes id:test-1
  Status: pending
  Please do work.
"""

    updated = mark_request_in_progress(text, "test-1", session_id="sess-456")

    assert "Status: in progress | Session: sess-456" in updated
    assert "Status: pending" not in updated


# ---------------------------------------------------------------------------
# Mark completed / failed with session_id
# ---------------------------------------------------------------------------


def test_mark_request_completed_includes_session_id():
    text = """# Daily

- [ ] @hermes id:test-1
  Please summarize [[Note]].
"""

    updated = mark_request_completed(
        text,
        "test-1",
        "summary written",
        session_id="20260426_xyz",
        timestamp="2026-04-25T20:00:00-03:00",
    )

    assert "Status: completed - summary written | Session: 20260426_xyz" in updated


def test_mark_request_failed_includes_session_id():
    text = """# Daily

- [ ] @hermes id:test-1
  Please summarize [[Note]].
"""

    updated = mark_request_failed(
        text,
        "test-1",
        "note not found",
        session_id="20260426_xyz",
        timestamp="2026-04-25T20:00:00-03:00",
    )

    assert "Status: failed - note not found | Session: 20260426_xyz" in updated


# ---------------------------------------------------------------------------
# Session ID discovery
# ---------------------------------------------------------------------------


def test_get_current_session_id(tmp_path, monkeypatch):
    from oficio_protocol import _get_current_session_id

    # Create a fake sessions directory inside tmp_path
    sessions_dir = tmp_path / ".hermes" / "sessions"
    sessions_dir.mkdir(parents=True)

    # Write a session file with a known session_id
    session_file = sessions_dir / "session_20260426_164315_8da571.json"
    session_file.write_text('{"session_id": "20260426_164315_8da571", "model": "test"}')

    # Patch Path.home at the module level where it's used
    import oficio_protocol
    monkeypatch.setattr(oficio_protocol.Path, "home", staticmethod(lambda: tmp_path))

    sid = _get_current_session_id()
    assert sid == "20260426_164315_8da571"
