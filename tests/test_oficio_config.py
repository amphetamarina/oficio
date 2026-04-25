from pathlib import Path

from oficio_config import default_config, load_config


def test_default_config_points_at_amphetamarina_agent_dir(monkeypatch):
    monkeypatch.setenv("HOME", "/home/marinarosa")

    cfg = default_config()

    assert cfg["vault_path"] == "/home/marinarosa/Documents/amphetamarina"
    assert cfg["agent_dir"] == "/home/marinarosa/Documents/amphetamarina/agent"
    assert cfg["config_dir"] == "/home/marinarosa/Documents/amphetamarina/agent/oficio"
    assert cfg["inbox_path"] == "agent/oficio/inbox.md"
    assert cfg["log_path"] == "agent/oficio/log.md"
    assert cfg["obsidian_cli"].endswith("obsidian-cli")


def test_load_config_creates_file_with_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    config_dir = tmp_path / "vault" / "agent" / "oficio"
    monkeypatch.setenv("OFICIO_CONFIG_DIR", str(config_dir))

    cfg = load_config()

    assert cfg["config_dir"] == str(config_dir)
    assert Path(cfg["config_file"]).exists()
    text = Path(cfg["config_file"]).read_text()
    assert "vault_path:" in text
    assert 'pending_marker: "@hermes"' in text

    reloaded = load_config()
    assert reloaded["pending_marker"] == "@hermes"
