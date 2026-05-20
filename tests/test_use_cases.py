import asyncio
import json
import re
from pathlib import Path

import pytest

from oficio import (
    OficioTools,
    default_config,
    find_pending_requests,
    load_config,
    mark_request_completed,
    replace_once,
    resolve_daily_path,
    upsert_agent_response,
    vault_abspath,
)
from oficio.mcp import build_server


@pytest.fixture
def vault(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(tmp_path / "Documents" / "my-vault" / "agent" / "oficio"))
    monkeypatch.delenv("OFICIO_SESSION_ID", raising=False)
    monkeypatch.delenv("OFICIO_AGENT_MARKER", raising=False)

    cfg = load_config()
    config_file = Path(cfg["config_file"])
    config_file.write_text(config_file.read_text().replace("use_obsidian_cli: true", "use_obsidian_cli: false"))
    return load_config()


def write_daily(cfg, text):
    daily_path = resolve_daily_path(cfg)
    file = vault_abspath(cfg, daily_path)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text)
    return daily_path, file


def payload(raw):
    return json.loads(raw)


def test_mcp_server_exposes_eight_tools(vault):
    server = build_server()
    tools = asyncio.run(server.list_tools())
    names = {tool.name for tool in tools}

    assert names == {
        "oficio_config_show",
        "oficio_scan",
        "oficio_read",
        "oficio_today",
        "oficio_start",
        "oficio_complete",
        "oficio_fail",
        "oficio_replace",
    }


def test_request_moves_from_pending_to_completed(vault):
    daily_path, file = write_daily(
        vault,
        "# Daily\n\n- [ ] @agent id:summary\n  Summarize [[Meeting]].\n",
    )
    tools = OficioTools()

    scanned = payload(tools.scan({"path": daily_path}))
    started = payload(tools.start({"id": "summary", "path": daily_path, "session_id": "sid-1"}))
    completed = payload(
        tools.complete(
            {
                "id": "summary",
                "path": daily_path,
                "note": "summary written",
                "response": "## Result\n\n- Final answer.",
                "session_id": "sid-1",
            }
        )
    )

    content = file.read_text()
    assert scanned["count"] == 1
    assert started["session_id"] == "sid-1"
    assert completed["success"] is True
    assert "- [x] @agent id:summary" in content
    assert "Status: completed - summary written | Session: sid-1" in content
    assert "Agent response:" in content
    assert "```markdown" not in content
    assert "  ## Result" in content
    assert "  - Final answer." in content


def test_session_id_falls_back_to_env(vault, monkeypatch):
    monkeypatch.setenv("OFICIO_SESSION_ID", "env-sid")
    daily_path, file = write_daily(vault, "# Daily\n\n- [ ] @agent id:task\n  Do thing.\n")

    started = payload(OficioTools().start({"id": "task", "path": daily_path}))

    assert started["session_id"] == "env-sid"
    assert "Session: env-sid" in file.read_text()


def test_custom_marker_via_env(vault, monkeypatch):
    monkeypatch.setenv("OFICIO_AGENT_MARKER", "@claude")
    daily_path, _ = write_daily(vault, "# Daily\n\n- [ ] @claude finish the report.\n")

    pending = payload(OficioTools().scan({"path": daily_path}))["pending"]

    assert len(pending) == 1
    assert "@claude" in pending[0]["text"]


def test_auto_ids_and_split_line_requests_target_the_right_checkbox():
    text = """# Daily

- [ ] @agent first.

@agent id:split
- [ ] Do the split-line thing.

- [ ] @agent second.
"""

    pending = find_pending_requests("Daily/2026-04-27.md", text)
    completed = mark_request_completed(text, "20260427-2", "second done", line_number=8)
    split_done = mark_request_completed(text, "split", "done")

    assert [item["has_explicit_id"] for item in pending] == [False, True, False]
    assert re.match(r"\d{8}-1", str(pending[0]["id"]))
    assert pending[1]["lines"] == [5, 6]
    assert "- [ ] @agent first." in completed
    assert "- [x] @agent id:20260427-2 second." in completed
    assert "@agent id:split" in split_done
    assert "- [x] Do the split-line thing." in split_done


def test_existing_agent_response_is_replaced_not_duplicated():
    text = """# Daily

- [x] @agent id:task
  Status: completed - old
  Agent response:
  ```markdown
  old
  ```
"""

    updated = upsert_agent_response(text, "task", "new")

    assert updated.count("Agent response:") == 1
    assert "  old\n" not in updated
    assert "  new\n" in updated


def test_existing_plain_agent_response_is_replaced_not_duplicated():
    text = """# Daily

- [x] @agent id:task
  Status: completed - old
  Agent response:
  old
  - stale
"""

    updated = upsert_agent_response(text, "task", "## New\n\n- fresh")

    assert updated.count("Agent response:") == 1
    assert "  old\n" not in updated
    assert "  - stale\n" not in updated
    assert "  ## New\n" in updated
    assert "  - fresh\n" in updated


def test_boundaries_reject_unsafe_or_ambiguous_edits(monkeypatch):
    monkeypatch.setenv("HOME", "/home/marina")
    cfg = default_config()

    for unsafe in ("/tmp/outside.md", "../outside.md", "agent/../../outside.md"):
        with pytest.raises(ValueError, match="path must"):
            vault_abspath(cfg, unsafe)

    with pytest.raises(ValueError, match="multiple"):
        replace_once("same same", "same", "x")
    with pytest.raises(ValueError, match="required"):
        replace_once("abc", "", "x")
