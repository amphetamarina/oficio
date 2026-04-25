from __future__ import annotations

import os
import shutil
from datetime import datetime
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
        "inbox_daily_dir": "agent/oficio/inbox/daily",
        "use_daily_inbox": False,
        "log_path": "agent/oficio/log.md",
        "log_daily_dir": "agent/oficio/log/daily",
        "use_daily_log": True,
        "timezone": "local",
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


def load_config(*, ensure: bool = True) -> Dict[str, Any]:
    cfg = default_config()
    config_dir = Path(cfg["config_dir"]).expanduser()
    config_file = config_dir / "config.yaml"
    cfg["config_file"] = str(config_file)

    if not config_file.exists():
        if ensure:
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file.write_text(_render_simple_yaml(cfg))
            _ensure_workspace_files(cfg)
        return cfg

    loaded = _load_yaml(config_file)
    cfg.update({k: v for k, v in loaded.items() if v is not None})
    # Keep config_dir/config_file coherent when OFICIO_CONFIG_DIR overrides.
    cfg["config_dir"] = str(config_dir)
    cfg["config_file"] = str(config_file)
    if ensure:
        config_dir.mkdir(parents=True, exist_ok=True)
        _ensure_workspace_files(cfg)
    return cfg


def vault_abspath(cfg: Dict[str, Any], vault_relative_path: str) -> Path:
    raw = str(vault_relative_path or "").strip()
    if not raw:
        raise ValueError("vault-relative path is required")
    path = Path(raw).expanduser()
    if path.is_absolute():
        raise ValueError("path must be vault-relative")
    vault = Path(str(cfg["vault_path"])).expanduser().resolve()
    target = (vault / path).resolve()
    try:
        target.relative_to(vault)
    except ValueError as exc:
        raise ValueError("path must stay inside the vault") from exc
    return target


def today_string(now: datetime | None = None) -> str:
    current = now or datetime.now().astimezone()
    return current.date().isoformat()


def resolve_log_path(cfg: Dict[str, Any], date: str | None = None) -> str:
    if not cfg.get("use_daily_log", True):
        return str(cfg["log_path"])
    day = date or today_string()
    daily_dir = str(cfg.get("log_daily_dir") or "agent/oficio/log/daily").rstrip("/")
    return f"{daily_dir}/{day}.md"


def resolve_inbox_path(cfg: Dict[str, Any], date: str | None = None) -> str:
    if not cfg.get("use_daily_inbox", False):
        return str(cfg["inbox_path"])
    day = date or today_string()
    daily_dir = str(cfg.get("inbox_daily_dir") or "agent/oficio/inbox/daily").rstrip("/")
    return f"{daily_dir}/{day}.md"


def _ensure_workspace_files(cfg: Dict[str, Any]) -> None:
    workspace_files = [
        ("inbox", str(cfg["inbox_path"])),
        ("inbox", resolve_inbox_path(cfg)),
        ("legacy_log", str(cfg["log_path"])),
        ("log", resolve_log_path(cfg)),
        ("plain", str(cfg["memory_file"])),
        ("plain", str(cfg["user_file"])),
        ("plain", str(cfg["soul_file"])),
    ]
    seen = set()
    for kind, rel_path in workspace_files:
        if rel_path in seen:
            continue
        seen.add(rel_path)
        path = vault_abspath(cfg, rel_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            if kind == "inbox":
                content = "# ofício inbox\n\n- [ ] @hermes id:example\n  Replace this example with a request, or delete it.\n"
            elif kind == "log":
                content = f"# ofício log · {Path(rel_path).stem}\n"
            elif kind == "legacy_log":
                content = "# ofício log\n"
            else:
                content = ""
            path.write_text(content)
