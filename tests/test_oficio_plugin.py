import importlib.util
import json
from pathlib import Path

from oficio_config import resolve_daily_path, vault_abspath


PLUGIN_PATH = Path(__file__).resolve().parents[1] / "__init__.py"


def load_plugin_module():
    spec = importlib.util.spec_from_file_location("oficio_plugin_under_test", PLUGIN_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def configure_tmp_vault(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / "Documents" / "amphetamarina" / "agent" / "oficio"
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(config_dir))
    plugin = load_plugin_module()
    cfg = plugin.load_config()
    config_file = Path(cfg["config_file"])
    config_file.write_text(config_file.read_text().replace("use_obsidian_cli: true", "use_obsidian_cli: false"))
    return plugin, plugin.load_config()


def test_start_handler_writes_status_with_explicit_session(tmp_path, monkeypatch):
    plugin, cfg = configure_tmp_vault(tmp_path, monkeypatch)
    daily_path = resolve_daily_path(cfg)
    daily = vault_abspath(cfg, daily_path)
    daily.parent.mkdir(parents=True, exist_ok=True)
    daily.write_text("# Daily\n\n- [ ] @hermes id:start-me\n  do it.\n")

    payload = json.loads(plugin._handle_start({"id": "start-me", "session_id": "sid-1"}))

    assert payload["success"] is True
    assert payload["session_id"] == "sid-1"
    assert payload["log_path"].endswith("session_sid-1.json")
    assert "Status: in progress | Session: sid-1" in daily.read_text()


def test_complete_handler_can_write_response_block(tmp_path, monkeypatch):
    plugin, cfg = configure_tmp_vault(tmp_path, monkeypatch)
    daily_path = resolve_daily_path(cfg)
    daily = vault_abspath(cfg, daily_path)
    daily.parent.mkdir(parents=True, exist_ok=True)
    daily.write_text("# Daily\n\n- [ ] @hermes id:finish-me\n  do it.\n")

    payload = json.loads(plugin._handle_complete({
        "id": "finish-me",
        "note": "done",
        "response": "Final answer.",
        "session_id": "sid-2",
    }))

    content = daily.read_text()
    assert payload["success"] is True
    assert "- [x] @hermes id:finish-me" in content
    assert "Status: completed - done | Session: sid-2" in content
    assert "Agent response:" in content
    assert "  Final answer." in content


def test_auto_id_completion_requires_line_and_injects_id(tmp_path, monkeypatch):
    plugin, cfg = configure_tmp_vault(tmp_path, monkeypatch)
    daily_path = resolve_daily_path(cfg)
    daily = vault_abspath(cfg, daily_path)
    daily.parent.mkdir(parents=True, exist_ok=True)
    daily.write_text("# Daily\n\n- [ ] @hermes no explicit id.\n")

    payload = json.loads(plugin._handle_complete({"id": "20260427-1", "note": "done", "line": 3}))

    assert payload["success"] is True
    assert "- [x] @hermes id:20260427-1 no explicit id." in daily.read_text()


def test_replace_handler_rejects_absolute_path(tmp_path, monkeypatch):
    plugin, _cfg = configure_tmp_vault(tmp_path, monkeypatch)

    payload = json.loads(plugin._handle_replace({"path": "/tmp/outside.md", "old": "a", "new": "b"}))

    assert payload["success"] is False
    assert "path must" in payload["error"] or "vault-relative" in payload["error"]


class HooklessCtx:
    def __init__(self):
        self.tools = []
        self.commands = []

    def register_tool(self, *args, **kwargs):
        self.tools.append(args)

    def register_command(self, *args, **kwargs):
        self.commands.append(args)


def test_register_degrades_without_hook_support(tmp_path, monkeypatch):
    plugin, _cfg = configure_tmp_vault(tmp_path, monkeypatch)
    ctx = HooklessCtx()

    plugin.register(ctx)

    assert len(ctx.tools) == 8
    assert len(ctx.commands) == 1
