import importlib.util
import json
from pathlib import Path

from oficio_config import default_config, resolve_inbox_path, vault_abspath


PLUGIN_PATH = Path(__file__).resolve().parents[1] / "__init__.py"


def load_plugin_module():
    spec = importlib.util.spec_from_file_location("oficio_plugin_under_test", PLUGIN_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def tree_snapshot(root: Path) -> set[str]:
    if not root.exists():
        return set()
    return {str(path.relative_to(root)) for path in root.rglob("*")}


def test_session_start_context_reports_pending_requests_without_mutating(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / "Documents" / "amphetamarina" / "agent" / "oficio"
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(config_dir))
    cfg = default_config()
    cfg["use_obsidian_cli"] = False
    config_dir.mkdir(parents=True)
    Path(cfg["config_file"]).write_text(
        "\n".join(
            [
                f"vault_path: {cfg['vault_path']}",
                f"config_dir: {cfg['config_dir']}",
                "inbox_path: agent/oficio/inbox.md",
                "use_obsidian_cli: false",
            ]
        )
        + "\n"
    )
    inbox_path = resolve_inbox_path(cfg)
    inbox = vault_abspath(cfg, inbox_path)
    inbox.parent.mkdir(parents=True, exist_ok=True)
    original = """# ofício inbox

- [ ] @hermes id:first
  do one thing.

- [ ] @hermes id:second
  do another thing.
"""
    inbox.write_text(original)
    vault_root = Path(cfg["vault_path"])
    before = tree_snapshot(vault_root)

    plugin = load_plugin_module()
    context = plugin._session_start_context()

    after = tree_snapshot(vault_root)
    assert after == before
    assert context is not None
    if isinstance(context, dict):
        rendered = json.dumps(context, ensure_ascii=False)
    else:
        rendered = str(context)
    assert "ofício" in rendered
    assert "2" in rendered
    assert inbox_path in rendered
    assert "first" in rendered
    assert "second" in rendered
    assert "Proactively inform" in rendered or "inform" in rendered.lower()
    assert inbox.read_text() == original


def test_session_start_context_missing_config_and_inbox_creates_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / "Documents" / "amphetamarina" / "agent" / "oficio"
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(config_dir))
    cfg = default_config()
    vault_root = Path(cfg["vault_path"])

    plugin = load_plugin_module()
    context = plugin._session_start_context()

    assert context is None
    assert not config_dir.exists()
    assert tree_snapshot(vault_root) == set()


def test_complete_handler_writes_source_and_daily_log(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / "Documents" / "amphetamarina" / "agent" / "oficio"
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(config_dir))
    plugin = load_plugin_module()
    cfg = plugin.load_config()
    Path(cfg["config_file"]).write_text(Path(cfg["config_file"]).read_text().replace("use_obsidian_cli: true", "use_obsidian_cli: false"))
    cfg = plugin.load_config()
    inbox_path = plugin.resolve_inbox_path(cfg)
    inbox = vault_abspath(cfg, inbox_path)
    inbox.write_text("# ofício inbox\n\n- [ ] @hermes id:finish-me\n  do it.\n")

    raw = plugin._handle_complete({"id": "finish-me", "note": "done in test"})
    payload = json.loads(raw)

    assert payload["success"] is True
    assert payload["log_path"].startswith("agent/oficio/log/daily/")
    assert "- [x] @hermes id:finish-me" in inbox.read_text()
    assert "- note: done in test" in inbox.read_text()
    log = vault_abspath(cfg, payload["log_path"])
    assert "## finish-me" in log.read_text()
    assert "- status: completed" in log.read_text()
    assert "done in test" in log.read_text()


def test_complete_with_line_number_injects_auto_id(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / "Documents" / "amphetamarina" / "agent" / "oficio"
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(config_dir))
    plugin = load_plugin_module()
    cfg = plugin.load_config()
    Path(cfg["config_file"]).write_text(Path(cfg["config_file"]).read_text().replace("use_obsidian_cli: true", "use_obsidian_cli: false"))
    cfg = plugin.load_config()
    inbox_path = plugin.resolve_inbox_path(cfg)
    inbox = vault_abspath(cfg, inbox_path)
    inbox.write_text("# ofício inbox\n\n- [ ] @hermes do something without explicit id.\n")

    raw = plugin._handle_complete({
        "id": "20260425-1",
        "note": "auto-id task done",
        "line": 3,
    })
    payload = json.loads(raw)

    assert payload["success"] is True
    assert "- [x] @hermes id:20260425-1" in inbox.read_text()
    assert "- note: auto-id task done" in inbox.read_text()
    log = vault_abspath(cfg, payload["log_path"])
    assert "## 20260425-1" in log.read_text()
    assert "- status: completed" in log.read_text()


def test_complete_ignores_stale_line_when_id_still_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / "Documents" / "amphetamarina" / "agent" / "oficio"
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(config_dir))
    plugin = load_plugin_module()
    cfg = plugin.load_config()
    Path(cfg["config_file"]).write_text(Path(cfg["config_file"]).read_text().replace("use_obsidian_cli: true", "use_obsidian_cli: false"))
    cfg = plugin.load_config()
    daily_path = "Daily/2026-04-25.md"
    daily = vault_abspath(cfg, daily_path)
    daily.parent.mkdir(parents=True, exist_ok=True)
    daily.write_text(
        "# Daily\n\n"
        "- [ ] @hermes id:other\n"
        "  first task.\n"
        "\n"
        "- [ ] @hermes id:task-2\n"
        "  second task.\n"
    )

    # Simulate line shift after first completion metadata was added elsewhere.
    shifted = daily.read_text().replace(
        "- [ ] @hermes id:other\n  first task.\n",
        "- [x] @hermes id:other\n  first task.\n  - completed: 2026-04-25T20:00:00-03:00\n  - note: done\n",
    )
    daily.write_text(shifted)

    raw = plugin._handle_complete({
        "id": "task-2",
        "path": daily_path,
        "line": 6,
        "note": "completed despite stale line",
    })
    payload = json.loads(raw)

    assert payload["success"] is True
    content = daily.read_text()
    assert "- [x] @hermes id:task-2" in content
    assert "- note: completed despite stale line" in content


def test_start_handler_creates_pending_log_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / "Documents" / "amphetamarina" / "agent" / "oficio"
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(config_dir))
    plugin = load_plugin_module()
    cfg = plugin.load_config()
    Path(cfg["config_file"]).write_text(Path(cfg["config_file"]).read_text().replace("use_obsidian_cli: true", "use_obsidian_cli: false"))
    cfg = plugin.load_config()

    raw = plugin._handle_start({"id": "20260425-1", "summary": "summarizing daily notes"})
    payload = json.loads(raw)

    assert payload["success"] is True
    assert payload["id"] == "20260425-1"
    assert payload["status"] == "pending"
    log = vault_abspath(cfg, payload["log_path"])
    log_content = log.read_text()
    assert "## 20260425-1" in log_content
    assert "- status: pending" in log_content
    assert "summarizing daily notes" in log_content


def test_start_then_complete_updates_pending_to_completed(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / "Documents" / "amphetamarina" / "agent" / "oficio"
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(config_dir))
    plugin = load_plugin_module()
    cfg = plugin.load_config()
    Path(cfg["config_file"]).write_text(Path(cfg["config_file"]).read_text().replace("use_obsidian_cli: true", "use_obsidian_cli: false"))
    cfg = plugin.load_config()
    inbox_path = plugin.resolve_inbox_path(cfg)
    inbox = vault_abspath(cfg, inbox_path)
    inbox.write_text("# ofício inbox\n\n- [ ] @hermes id:task-xyz\n  do things.\n")

    # 1. Start
    raw_start = plugin._handle_start({"id": "task-xyz", "summary": "starting task xyz"})
    assert json.loads(raw_start)["success"] is True

    # 2. Complete
    raw_complete = plugin._handle_complete({"id": "task-xyz", "note": "task xyz finished"})
    assert json.loads(raw_complete)["success"] is True

    # Verify log shows completed (updated from pending)
    log = vault_abspath(cfg, json.loads(raw_complete)["log_path"])
    log_content = log.read_text()
    assert "## task-xyz" in log_content
    assert "- status: completed" in log_content
    assert "task xyz finished" in log_content
    # Pending summary should still be there (it's part of the section body)
    assert "starting task xyz" in log_content


def test_fail_handler_with_line_number(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / "Documents" / "amphetamarina" / "agent" / "oficio"
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(config_dir))
    plugin = load_plugin_module()
    cfg = plugin.load_config()
    Path(cfg["config_file"]).write_text(Path(cfg["config_file"]).read_text().replace("use_obsidian_cli: true", "use_obsidian_cli: false"))
    cfg = plugin.load_config()
    inbox_path = plugin.resolve_inbox_path(cfg)
    inbox = vault_abspath(cfg, inbox_path)
    inbox.write_text("# ofício inbox\n\n- [ ] @hermes will fail.\n")

    raw = plugin._handle_fail({
        "id": "20260425-1",
        "error": "something went wrong",
        "line": 3,
    })
    payload = json.loads(raw)

    assert payload["success"] is True
    assert "- [x] @hermes id:20260425-1" in inbox.read_text()
    assert "- error: something went wrong" in inbox.read_text()


def test_summary_handler_aggregates_daily_logs(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / "Documents" / "amphetamarina" / "agent" / "oficio"
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(config_dir))
    plugin = load_plugin_module()
    cfg = plugin.load_config()
    Path(cfg["config_file"]).write_text(Path(cfg["config_file"]).read_text().replace("use_obsidian_cli: true", "use_obsidian_cli: false"))
    cfg = plugin.load_config()
    log_dir = vault_abspath(cfg, "agent/oficio/log/daily")
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "2026-04-24.md").write_text(
        "# ofício log · 2026-04-24\n\n"
        "## req-1\n\n"
        "- status: completed\n"
        "- at: 2026-04-24T10:00:00-03:00\n"
        "- source: inbox.md\n\n"
        "first summary\n"
    )
    (log_dir / "2026-04-25.md").write_text(
        "# ofício log · 2026-04-25\n\n"
        "## req-2\n\n"
        "- status: failed\n"
        "- at: 2026-04-25T11:00:00-03:00\n"
        "- source: Daily/2026-04-25.md\n\n"
        "boom\n"
    )

    raw = plugin._handle_summary({"days": 7, "format": "markdown"})
    payload = json.loads(raw)

    assert payload["success"] is True
    assert payload["count"] == 2
    assert "| Date | ID | Status | Note |" in payload["summary"]
    assert "req-1" in payload["summary"]
    assert "req-2" in payload["summary"]


def test_request_handler_appends_follow_up_to_inbox(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / "Documents" / "amphetamarina" / "agent" / "oficio"
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(config_dir))
    plugin = load_plugin_module()
    cfg = plugin.load_config()
    Path(cfg["config_file"]).write_text(Path(cfg["config_file"]).read_text().replace("use_obsidian_cli: true", "use_obsidian_cli: false"))
    cfg = plugin.load_config()
    inbox_path = plugin.resolve_inbox_path(cfg)
    inbox = vault_abspath(cfg, inbox_path)
    inbox.write_text("# ofício inbox\n")

    raw = plugin._handle_request({"id": "follow-up-1", "description": "investigue o erro"})
    payload = json.loads(raw)

    assert payload["success"] is True
    assert payload["id"] == "follow-up-1"
    content = inbox.read_text()
    assert "- [ ] @hermes id:follow-up-1 investigue o erro" in content


def test_replace_handler_rejects_absolute_path(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(tmp_path / "Documents" / "amphetamarina" / "agent" / "oficio"))
    plugin = load_plugin_module()

    raw = plugin._handle_replace({"path": "/tmp/outside.md", "old": "a", "new": "b"})
    payload = json.loads(raw)

    assert payload["success"] is False
    assert "vault-relative" in payload["error"] or "path must" in payload["error"]


class HooklessCtx:
    def __init__(self):
        self.tools = []
        self.commands = []

    def register_tool(self, name, toolset, schema, handler, **kwargs):
        self.tools.append(name)

    def register_command(self, name, handler, **kwargs):
        self.commands.append(name)


def test_register_degrades_when_ctx_has_no_hook_support(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(tmp_path / "Documents" / "amphetamarina" / "agent" / "oficio"))
    plugin = load_plugin_module()
    ctx = HooklessCtx()

    plugin.register(ctx)

    assert "oficio_complete" in ctx.tools
    assert "oficio_start" in ctx.tools
    assert "oficio_summary" in ctx.tools
    assert "oficio_request" in ctx.tools
    assert "oficio" in ctx.commands
