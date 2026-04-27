from datetime import datetime
from pathlib import Path

import pytest

from oficio_config import default_config, load_config, resolve_daily_path, today_string, vault_abspath


def test_default_config_and_daily_path(monkeypatch):
    monkeypatch.setenv("HOME", "/home/marinarosa")

    cfg = default_config()

    assert cfg["vault_path"] == "/home/marinarosa/Documents/amphetamarina"
    assert cfg["daily_path"] == "Daily"
    assert resolve_daily_path(cfg, date="2026-04-27") == "Daily/2026-04-27.md"
    assert today_string(datetime(2026, 4, 27, 23, 59)) == "2026-04-27"


def test_load_config_creates_visible_vault_config(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / "Documents" / "amphetamarina" / "agent" / "oficio"
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(config_dir))

    cfg = load_config()

    config_file = Path(cfg["config_file"])
    assert config_file.exists()
    text = config_file.read_text()
    assert "vault_path:" in text
    assert 'pending_marker: "@hermes"' in text
    assert load_config()["pending_marker"] == "@hermes"


def test_load_config_can_skip_writes(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / "Documents" / "amphetamarina" / "agent" / "oficio"
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(config_dir))

    cfg = load_config(ensure=False)

    assert cfg["config_dir"] == str(config_dir)
    assert not config_dir.exists()


def test_vault_abspath_rejects_paths_outside_vault(monkeypatch):
    monkeypatch.setenv("HOME", "/home/marinarosa")
    cfg = default_config()

    for unsafe in ("/tmp/outside.md", "../outside.md", "agent/../../outside.md"):
        with pytest.raises(ValueError, match="path must"):
            vault_abspath(cfg, unsafe)
