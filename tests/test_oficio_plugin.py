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
    assert "2" in rendered
    assert inbox_path in rendered
    assert "first" in rendered
    assert "second" in rendered
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
    assert "oficio" in ctx.commands
