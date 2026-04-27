import importlib.util
import json
import re
from pathlib import Path

import pytest

from oficio_config import default_config, resolve_daily_path, vault_abspath
from oficio_protocol import (
    find_pending_requests,
    mark_request_completed,
    replace_once,
    session_log_path,
    upsert_agent_response,
)

PLUGIN_PATH = Path(__file__).resolve().parents[1] / "__init__.py"


class HermesContext:
    def __init__(self):
        self.tools = []
        self.commands = []

    def register_tool(self, *args, **kwargs):
        self.tools.append(args)

    def register_command(self, *args, **kwargs):
        self.commands.append(args)


def load_plugin_module():
    spec = importlib.util.spec_from_file_location("oficio_plugin_under_test", PLUGIN_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def given_vault(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / "Documents" / "my-vault" / "agent" / "oficio"
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(config_dir))

    plugin = load_plugin_module()
    cfg = plugin.load_config()
    config_file = Path(cfg["config_file"])
    config_file.write_text(config_file.read_text().replace("use_obsidian_cli: true", "use_obsidian_cli: false"))
    return plugin, plugin.load_config()


def given_daily_note(cfg, text):
    daily_path = resolve_daily_path(cfg)
    daily = vault_abspath(cfg, daily_path)
    daily.parent.mkdir(parents=True, exist_ok=True)
    daily.write_text(text)
    return daily_path, daily


def payload(raw):
    return json.loads(raw)


def test_scenario_fresh_install_exposes_only_the_supported_command_surface(tmp_path, monkeypatch):
    plugin, cfg = given_vault(tmp_path, monkeypatch)
    context = HermesContext()

    plugin.register(context)

    config_text = Path(cfg["config_file"]).read_text()
    assert "vault_path:" in config_text
    assert 'pending_marker: "@hermes"' in config_text
    assert len(context.tools) == 8
    assert len(context.commands) == 1
    assert not hasattr(plugin, "_session_start_context")


def test_scenario_daily_note_request_moves_from_pending_to_completed(tmp_path, monkeypatch):
    plugin, cfg = given_vault(tmp_path, monkeypatch)
    daily_path, daily = given_daily_note(
        cfg,
        "# Daily\n\n- [ ] @hermes id:summary\n  Summarize [[Meeting]].\n",
    )

    scanned = payload(plugin._handle_scan({"path": daily_path}))
    started = payload(plugin._handle_start({"id": "summary", "path": daily_path, "session_id": "sid-1"}))
    completed = payload(plugin._handle_complete({
        "id": "summary",
        "path": daily_path,
        "note": "summary written",
        "response": "## Result\n\n- Final answer.",
        "session_id": "sid-1",
    }))

    content = daily.read_text()
    assert scanned["count"] == 1
    assert started["log_path"].endswith("session_sid-1.json")
    assert completed["success"] is True
    assert "- [x] @hermes id:summary" in content
    assert "Status: completed - summary written | Session: sid-1" in content
    assert "Agent response:" in content
    assert "```markdown" not in content
    assert "  ## Result" in content
    assert "  - Final answer." in content


def test_scenario_auto_ids_and_split_line_requests_target_the_right_checkbox():
    text = """# Daily

- [ ] @hermes first.

@hermes id:split
- [ ] Do the split-line thing.

- [ ] @hermes second.
"""

    pending = find_pending_requests("Daily/2026-04-27.md", text)
    completed = mark_request_completed(text, "20260427-2", "second done", line_number=8)
    split_done = mark_request_completed(text, "split", "done")

    assert [item["has_explicit_id"] for item in pending] == [False, True, False]
    assert re.match(r"\d{8}-1", str(pending[0]["id"]))
    assert pending[1]["lines"] == [5, 6]
    assert "- [ ] @hermes first." in completed
    assert "- [x] @hermes id:20260427-2 second." in completed
    assert "@hermes id:split" in split_done
    assert "- [x] Do the split-line thing." in split_done


def test_scenario_existing_agent_response_is_replaced_not_duplicated():
    text = """# Daily

- [x] @hermes id:task
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


def test_scenario_existing_plain_agent_response_is_replaced_not_duplicated():
    text = """# Daily

- [x] @hermes id:task
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


def test_scenario_boundaries_reject_unsafe_or_ambiguous_edits(monkeypatch):
    monkeypatch.setenv("HOME", "/home/marina")
    cfg = default_config()

    for unsafe in ("/tmp/outside.md", "../outside.md", "agent/../../outside.md"):
        with pytest.raises(ValueError, match="path must"):
            vault_abspath(cfg, unsafe)

    with pytest.raises(ValueError, match="multiple"):
        replace_once("same same", "same", "x")
    with pytest.raises(ValueError, match="required"):
        replace_once("abc", "", "x")

    assert session_log_path("abc") == "/home/marina/.hermes/sessions/session_abc.json"
