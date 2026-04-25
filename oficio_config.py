from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore


def _home() -> Path:
    return Path(os.environ.get("HOME", str(Path.home()))).expanduser()


def default_config() -> Dict[str, Any]:
    home = _home()
    vault = home / "Documents" / "amphetamarina"
    agent_dir = vault / "agent"
    config_dir = Path(os.environ.get("OFICIO_CONFIG_DIR", str(agent_dir / "oficio"))).expanduser()
    obsidian_cli = os.environ.get("OBSIDIAN_CLI") or shutil.which("obsidian-cli") or "obsidian-cli"
    return {
        "vault_path": str(vault),
        "agent_dir": str(agent_dir),
        "config_dir": str(config_dir),
        "config_file": str(config_dir / "config.yaml"),
        "inbox_path": "agent/oficio/inbox.md",
        "log_path": "agent/oficio/log.md",
        "memory_file": "agent/MEMORY.md",
        "user_file": "agent/USER.md",
        "soul_file": "agent/SOUL.md",
        "obsidian_cli": obsidian_cli,
        "vault": "",
        "pending_marker": "@hermes",
        "use_obsidian_cli": True,
    }


def _render_simple_yaml(data: Dict[str, Any]) -> str:
    lines = ["# ofício Hermes plugin config", "# Lives in the Obsidian vault so it is visible and editable as text."]
    for key, value in data.items():
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        else:
            rendered = str(value)
            if rendered == "" or rendered.startswith(("@", "&", "*", "!", "%")) or any(ch in rendered for ch in [": ", "#", "\n", "'", '"']):
                rendered = '"' + rendered.replace('"', '\\"') + '"'
        lines.append(f"{key}: {rendered}")
    return "\n".join(lines) + "\n"


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text()
    if yaml is not None:
        loaded = yaml.safe_load(text) or {}
        return loaded if isinstance(loaded, dict) else {}
    # Tiny fallback for the simple key: value config we write.
    data: Dict[str, Any] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip().strip('"')
        if value.lower() == "true":
            data[key.strip()] = True
        elif value.lower() == "false":
            data[key.strip()] = False
        else:
            data[key.strip()] = value
    return data


def load_config() -> Dict[str, Any]:
    cfg = default_config()
    config_dir = Path(cfg["config_dir"]).expanduser()
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.yaml"
    cfg["config_file"] = str(config_file)

    if not config_file.exists():
        config_file.write_text(_render_simple_yaml(cfg))
        _ensure_workspace_files(cfg)
        return cfg

    loaded = _load_yaml(config_file)
    cfg.update({k: v for k, v in loaded.items() if v is not None})
    # Keep config_dir/config_file coherent when OFICIO_CONFIG_DIR overrides.
    cfg["config_dir"] = str(config_dir)
    cfg["config_file"] = str(config_file)
    _ensure_workspace_files(cfg)
    return cfg


def vault_abspath(cfg: Dict[str, Any], vault_relative_path: str) -> Path:
    path = Path(vault_relative_path).expanduser()
    if path.is_absolute():
        return path
    return Path(str(cfg["vault_path"])).expanduser() / path


def _ensure_workspace_files(cfg: Dict[str, Any]) -> None:
    for key in ("inbox_path", "log_path", "memory_file", "user_file", "soul_file"):
        path = vault_abspath(cfg, str(cfg[key]))
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            if key == "inbox_path":
                content = "# ofício inbox\n\n- [ ] @hermes id:example\n  Replace this example with a request, or delete it.\n"
            elif key == "log_path":
                content = "# ofício log\n"
            else:
                content = ""
            path.write_text(content)
