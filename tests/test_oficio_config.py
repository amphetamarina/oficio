from datetime import datetime
from pathlib import Path

from oficio_config import default_config, load_config, resolve_inbox_path, resolve_log_path, today_string, vault_abspath


def test_default_config_points_at_amphetamarina_agent_dir(monkeypatch):
    monkeypatch.setenv("HOME", "/home/marinarosa")

    cfg = default_config()

    assert cfg["vault_path"] == "/home/marinarosa/Documents/amphetamarina"
    assert cfg["agent_dir"] == "/home/marinarosa/Documents/amphetamarina/agent"
    assert cfg["config_dir"] == "/home/marinarosa/Documents/amphetamarina/agent/oficio"
    assert cfg["inbox_path"] == "agent/oficio/inbox.md"
    assert cfg["inbox_daily_dir"] == "agent/oficio/inbox/daily"
    assert cfg["use_daily_inbox"] is False
    assert cfg["log_path"] == "agent/oficio/log.md"
    assert cfg["log_daily_dir"] == "agent/oficio/log/daily"
    assert cfg["use_daily_log"] is True
    assert cfg["timezone"] == "local"
    assert cfg["obsidian_cli"].endswith("obsidian-cli")


def test_today_string_uses_supplied_datetime():
    assert today_string(datetime(2026, 4, 25, 23, 59, 0)) == "2026-04-25"


def test_resolve_log_path_defaults_to_daily_log(monkeypatch):
    monkeypatch.setenv("HOME", "/home/marinarosa")
    cfg = default_config()

    path = resolve_log_path(cfg, date="2026-04-25")

    assert path == "agent/oficio/log/daily/2026-04-25.md"


def test_resolve_log_path_can_use_legacy_log(monkeypatch):
    monkeypatch.setenv("HOME", "/home/marinarosa")
    cfg = default_config()
    cfg["use_daily_log"] = False

    path = resolve_log_path(cfg, date="2026-04-25")

    assert path == "agent/oficio/log.md"


def test_resolve_inbox_path_keeps_canonical_inbox_by_default(monkeypatch):
    monkeypatch.setenv("HOME", "/home/marinarosa")
    cfg = default_config()

    path = resolve_inbox_path(cfg, date="2026-04-25")

    assert path == "agent/oficio/inbox.md"


def test_resolve_inbox_path_can_use_daily_inbox(monkeypatch):
    monkeypatch.setenv("HOME", "/home/marinarosa")
    cfg = default_config()
    cfg["use_daily_inbox"] = True

    path = resolve_inbox_path(cfg, date="2026-04-25")

    assert path == "agent/oficio/inbox/daily/2026-04-25.md"


def test_load_config_creates_file_with_defaults_and_resolved_workspace_files(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / "Documents" / "amphetamarina" / "agent" / "oficio"
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(config_dir))

    cfg = load_config()

    assert cfg["config_dir"] == str(config_dir)
    assert Path(cfg["config_file"]).exists()
    text = Path(cfg["config_file"]).read_text()
    assert "vault_path:" in text
    assert 'pending_marker: "@hermes"' in text
    assert "log_daily_dir: agent/oficio/log/daily" in text
    assert "use_daily_log: true" in text

    inbox = vault_abspath(cfg, resolve_inbox_path(cfg))
    log = vault_abspath(cfg, resolve_log_path(cfg))
    assert inbox.exists()
    assert inbox.read_text().startswith("# ofício inbox")
    assert log.exists()
    assert log.read_text().startswith("# ofício log · ")

    reloaded = load_config()
    assert reloaded["pending_marker"] == "@hermes"


def test_load_config_can_skip_workspace_creation(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / "Documents" / "amphetamarina" / "agent" / "oficio"
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(config_dir))

    cfg = load_config(ensure=False)

    assert cfg["config_dir"] == str(config_dir)
    assert not config_dir.exists()


def test_vault_abspath_rejects_absolute_and_traversal_paths(monkeypatch):
    monkeypatch.setenv("HOME", "/home/marinarosa")
    cfg = default_config()

    for unsafe in ("/tmp/outside.md", "../outside.md", "agent/../../outside.md"):
        try:
            vault_abspath(cfg, unsafe)
        except ValueError as exc:
            assert "path must" in str(exc)
        else:
            raise AssertionError(f"expected ValueError for {unsafe}")
