from oficio_protocol import find_pending_requests, mark_request_completed


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


def test_mark_request_completed_replaces_checkbox_and_appends_result():
    text = """# Inbox

- [ ] @hermes id:test-1
  Please summarize [[Note]].
"""

    updated = mark_request_completed(text, "test-1", "Done.")

    assert "- [x] @hermes id:test-1" in updated
    assert "Result:" in updated
    assert "Done." in updated
