import importlib.util
import json
from pathlib import Path

from oficio_config import default_config, resolve_daily_path, resolve_inbox_path, vault_abspath


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
                "use_obsidian_cli: false",
            ]
        )
        + "\n"
    )
    # Write pending requests to the daily note (new default scan target)
    daily_path = resolve_daily_path(cfg)
    daily = vault_abspath(cfg, daily_path)
    daily.parent.mkdir(parents=True, exist_ok=True)
    original = """# Daily

- [ ] @hermes id:first
  do one thing.

- [ ] @hermes id:second
  do another thing.
"""
    daily.write_text(original)
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
    assert daily_path in rendered
    assert "first" in rendered
    assert "second" in rendered
    assert daily.read_text() == original


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


def test_complete_handler_writes_source_and_session_log(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / "Documents" / "amphetamarina" / "agent" / "oficio"
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(config_dir))
    plugin = load_plugin_module()
    cfg = plugin.load_config()
    Path(cfg["config_file"]).write_text(Path(cfg["config_file"]).read_text().replace("use_obsidian_cli: true", "use_obsidian_cli: false"))
    cfg = plugin.load_config()
    # Write request to daily note (new default)
    daily_path = plugin.resolve_daily_path(cfg)
    daily = vault_abspath(cfg, daily_path)
    daily.parent.mkdir(parents=True, exist_ok=True)
    daily.write_text("# Daily\n\n- [ ] @hermes id:finish-me\n  do it.\n")

    raw = plugin._handle_complete({"id": "finish-me", "note": "done in test"})
    payload = json.loads(raw)

    assert payload["success"] is True
    assert payload["session_log"].startswith("agent/oficio/sessions/")
    assert "- [x] @hermes id:finish-me" in daily.read_text()
    assert "Status: completed - done in test" in daily.read_text()
    session_log = vault_abspath(cfg, payload["session_log"])
    assert session_log.exists()
    assert "finish-me" in session_log.read_text()
    assert "done in test" in session_log.read_text()


def test_complete_with_line_number_injects_auto_id(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / "Documents" / "amphetamarina" / "agent" / "oficio"
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(config_dir))
    plugin = load_plugin_module()
    cfg = plugin.load_config()
    Path(cfg["config_file"]).write_text(Path(cfg["config_file"]).read_text().replace("use_obsidian_cli: true", "use_obsidian_cli: false"))
    cfg = plugin.load_config()
    daily_path = plugin.resolve_daily_path(cfg)
    daily = vault_abspath(cfg, daily_path)
    daily.parent.mkdir(parents=True, exist_ok=True)
    daily.write_text("# Daily\n\n- [ ] @hermes do something without explicit id.\n")

    raw = plugin._handle_complete({
        "id": "20260425-1",
        "note": "auto-id task done",
        "line": 3,
    })
    payload = json.loads(raw)

    assert payload["success"] is True
    assert "- [x] @hermes id:20260425-1" in daily.read_text()
    assert "Status: completed - auto-id task done" in daily.read_text()


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
        "- [x] @hermes id:other\n  first task.\n  Status: completed - done\n",
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
    assert "Status: completed - completed despite stale line" in content


def test_start_handler_writes_status_line_to_daily(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / "Documents" / "amphetamarina" / "agent" / "oficio"
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(config_dir))
    plugin = load_plugin_module()
    cfg = plugin.load_config()
    Path(cfg["config_file"]).write_text(Path(cfg["config_file"]).read_text().replace("use_obsidian_cli: true", "use_obsidian_cli: false"))
    cfg = plugin.load_config()
    # Write pending request to daily note
    daily_path = plugin.resolve_daily_path(cfg)
    daily = vault_abspath(cfg, daily_path)
    daily.parent.mkdir(parents=True, exist_ok=True)
    daily.write_text("# Daily\n\n- [ ] @hermes id:20260425-1\n  do stuff.\n")

    raw = plugin._handle_start({"id": "20260425-1", "summary": "summarizing daily notes"})
    payload = json.loads(raw)

    assert payload["success"] is True
    assert payload["id"] == "20260425-1"
    assert payload["status"] == "in-progress"
    content = daily.read_text()
    assert "Status: in-progress - summarizing daily notes" in content


def test_start_then_complete_updates_status_line(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / "Documents" / "amphetamarina" / "agent" / "oficio"
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(config_dir))
    plugin = load_plugin_module()
    cfg = plugin.load_config()
    Path(cfg["config_file"]).write_text(Path(cfg["config_file"]).read_text().replace("use_obsidian_cli: true", "use_obsidian_cli: false"))
    cfg = plugin.load_config()
    daily_path = plugin.resolve_daily_path(cfg)
    daily = vault_abspath(cfg, daily_path)
    daily.parent.mkdir(parents=True, exist_ok=True)
    daily.write_text("# Daily\n\n- [ ] @hermes id:task-xyz\n  do things.\n")

    # 1. Start
    raw_start = plugin._handle_start({"id": "task-xyz", "summary": "starting task xyz"})
    assert json.loads(raw_start)["success"] is True
    assert "Status: in-progress - starting task xyz" in daily.read_text()

    # 2. Complete
    raw_complete = plugin._handle_complete({"id": "task-xyz", "note": "task xyz finished"})
    assert json.loads(raw_complete)["success"] is True

    # Verify daily note shows completed status
    content = daily.read_text()
    assert "- [x] @hermes id:task-xyz" in content
    assert "Status: completed - task xyz finished" in content


def test_fail_handler_with_line_number(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / "Documents" / "amphetamarina" / "agent" / "oficio"
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(config_dir))
    plugin = load_plugin_module()
    cfg = plugin.load_config()
    Path(cfg["config_file"]).write_text(Path(cfg["config_file"]).read_text().replace("use_obsidian_cli: true", "use_obsidian_cli: false"))
    cfg = plugin.load_config()
    daily_path = plugin.resolve_daily_path(cfg)
    daily = vault_abspath(cfg, daily_path)
    daily.parent.mkdir(parents=True, exist_ok=True)
    daily.write_text("# Daily\n\n- [ ] @hermes will fail.\n")

    raw = plugin._handle_fail({
        "id": "20260425-1",
        "error": "something went wrong",
        "line": 3,
    })
    payload = json.loads(raw)

    assert payload["success"] is True
    content = daily.read_text()
    assert "- [x] @hermes id:20260425-1" in content
    assert "Status: failed - something went wrong" in content


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


def test_request_handler_appends_follow_up_to_daily(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / "Documents" / "amphetamarina" / "agent" / "oficio"
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(config_dir))
    plugin = load_plugin_module()
    cfg = plugin.load_config()
    Path(cfg["config_file"]).write_text(Path(cfg["config_file"]).read_text().replace("use_obsidian_cli: true", "use_obsidian_cli: false"))
    cfg = plugin.load_config()
    daily_path = plugin.resolve_daily_path(cfg)
    daily = vault_abspath(cfg, daily_path)
    daily.parent.mkdir(parents=True, exist_ok=True)
    daily.write_text("# Daily\n")

    raw = plugin._handle_request({"id": "follow-up-1", "description": "investigue o erro"})
    payload = json.loads(raw)

    assert payload["success"] is True
    assert payload["id"] == "follow-up-1"
    content = daily.read_text()
    assert "- [ ] @hermes id:follow-up-1 investigue o erro" in content


def test_request_handler_generates_slug_id_from_description(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / "Documents" / "amphetamarina" / "agent" / "oficio"
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(config_dir))
    plugin = load_plugin_module()
    cfg = plugin.load_config()
    Path(cfg["config_file"]).write_text(Path(cfg["config_file"]).read_text().replace("use_obsidian_cli: true", "use_obsidian_cli: false"))
    cfg = plugin.load_config()
    daily_path = plugin.resolve_daily_path(cfg)
    daily = vault_abspath(cfg, daily_path)
    daily.parent.mkdir(parents=True, exist_ok=True)
    daily.write_text("# Daily\n")

    raw = plugin._handle_request({"description": "Algo relacionado ao título!!!"})
    payload = json.loads(raw)

    assert payload["success"] is True
    assert payload["id"] == "algo-relacionado-ao-titulo"
    assert "id:algo-relacionado-ao-titulo" in daily.read_text()


def test_request_handler_slug_avoids_collisions_with_inbox_and_log(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / "Documents" / "amphetamarina" / "agent" / "oficio"
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(config_dir))
    plugin = load_plugin_module()
    cfg = plugin.load_config()
    Path(cfg["config_file"]).write_text(Path(cfg["config_file"]).read_text().replace("use_obsidian_cli: true", "use_obsidian_cli: false"))
    cfg = plugin.load_config()
    daily_path = plugin.resolve_daily_path(cfg)
    daily = vault_abspath(cfg, daily_path)
    daily.parent.mkdir(parents=True, exist_ok=True)
    daily.write_text("# Daily\n\n- [ ] @hermes id:algo-relacionado-ao-titulo pedido antigo\n")
    log = vault_abspath(cfg, plugin.resolve_log_path(cfg))
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("# ofício log\n\n## algo-relacionado-ao-titulo-2\n\n- status: completed\n")

    raw = plugin._handle_request({"description": "Algo relacionado ao título"})
    payload = json.loads(raw)

    assert payload["success"] is True
    assert payload["id"] == "algo-relacionado-ao-titulo-3"
    assert "id:algo-relacionado-ao-titulo-3" in daily.read_text()


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
