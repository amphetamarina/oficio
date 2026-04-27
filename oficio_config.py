from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

ConfigDict = dict[str, Any]

DEFAULT_VAULT_NAME = "my-vault"
WORKSPACE_FILES = ("memory_file", "user_file", "soul_file")


class OficioConfig:
    def __init__(self, home: Path | None = None) -> None:
        self.home = home or Path(os.environ.get("HOME", str(Path.home()))).expanduser()

    def defaults(self) -> ConfigDict:
        vault = self.home / "Documents" / DEFAULT_VAULT_NAME
        agent_dir = vault / "agent"
        config_dir = self._config_dir(agent_dir)

        return {
            "vault_path": str(vault),
            "agent_dir": str(agent_dir),
            "config_dir": str(config_dir),
            "config_file": str(config_dir / "config.yaml"),
            "daily_path": "Daily",
            "scan_daily": True,
            "timezone": "local",
            "memory_file": "agent/MEMORY.md",
            "user_file": "agent/USER.md",
            "soul_file": "agent/SOUL.md",
            "obsidian_cli": self._obsidian_cli(),
            "vault": "",
            "pending_marker": "@hermes",
            "use_obsidian_cli": True,
        }

    def load(self, *, ensure: bool = True) -> ConfigDict:
        cfg = self.defaults()
        config_dir = Path(cfg["config_dir"]).expanduser()
        config_file = config_dir / "config.yaml"
        cfg["config_file"] = str(config_file)

        if config_file.exists():
            cfg.update(self._present_values(self._load_yaml(config_file)))

        cfg["config_dir"] = str(config_dir)
        cfg["config_file"] = str(config_file)

        if ensure:
            config_dir.mkdir(parents=True, exist_ok=True)
            if not config_file.exists():
                config_file.write_text(self._render_yaml(cfg))
            self.ensure_workspace_files(cfg)

        return cfg

    def vault_path(self, cfg: ConfigDict, vault_relative_path: str) -> Path:
        raw_path = str(vault_relative_path or "").strip()
        if not raw_path:
            raise ValueError("vault-relative path is required")

        relative_path = Path(raw_path).expanduser()
        if relative_path.is_absolute():
            raise ValueError("path must be vault-relative")

        vault = Path(str(cfg["vault_path"])).expanduser().resolve()
        target = (vault / relative_path).resolve()
        try:
            target.relative_to(vault)
        except ValueError as exc:
            raise ValueError("path must stay inside the vault") from exc
        return target

    def daily_path(self, cfg: ConfigDict, date: str | None = None) -> str:
        daily_dir = str(cfg.get("daily_path") or "Daily").rstrip("/")
        return f"{daily_dir}/{date or today_string()}.md"

    def ensure_workspace_files(self, cfg: ConfigDict) -> None:
        for key in WORKSPACE_FILES:
            path = self.vault_path(cfg, str(cfg[key]))
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text("")

    def _config_dir(self, agent_dir: Path) -> Path:
        configured = os.environ.get("OFICIO_CONFIG_DIR")
        return Path(configured).expanduser() if configured else agent_dir / "oficio"

    def _obsidian_cli(self) -> str:
        return os.environ.get("OBSIDIAN_CLI") or shutil.which("obsidian-cli") or "obsidian-cli"

    def _present_values(self, data: ConfigDict) -> ConfigDict:
        return {key: value for key, value in data.items() if value is not None}

    def _render_yaml(self, data: ConfigDict) -> str:
        lines = [
            "# ofício Hermes plugin config",
            "# Lives in the Obsidian vault so it is visible and editable as text.",
        ]
        lines.extend(f"{key}: {self._yaml_value(value)}" for key, value in data.items())
        return "\n".join(lines) + "\n"

    def _yaml_value(self, value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"

        text = str(value)
        if self._needs_quotes(text):
            return '"' + text.replace('"', '\\"') + '"'
        return text

    def _needs_quotes(self, text: str) -> bool:
        return (
            text == ""
            or text.startswith(("@", "&", "*", "!", "%"))
            or any(char in text for char in [": ", "#", "\n", "'", '"'])
        )

    def _load_yaml(self, path: Path) -> ConfigDict:
        text = path.read_text()
        if yaml is not None:
            loaded = yaml.safe_load(text) or {}
            return loaded if isinstance(loaded, dict) else {}
        return self._load_simple_yaml(text)

    def _load_simple_yaml(self, text: str) -> ConfigDict:
        data: ConfigDict = {}
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            key, value = line.split(":", 1)
            data[key.strip()] = self._parse_simple_value(value.strip())
        return data

    def _parse_simple_value(self, value: str) -> Any:
        unquoted = value.strip('"')
        if unquoted.lower() == "true":
            return True
        if unquoted.lower() == "false":
            return False
        return unquoted


CONFIG = OficioConfig()


def default_config() -> ConfigDict:
    return CONFIG.defaults()


def load_config(*, ensure: bool = True) -> ConfigDict:
    return CONFIG.load(ensure=ensure)


def vault_abspath(cfg: ConfigDict, vault_relative_path: str) -> Path:
    return CONFIG.vault_path(cfg, vault_relative_path)


def today_string(now: datetime | None = None) -> str:
    return (now or datetime.now().astimezone()).date().isoformat()


def resolve_daily_path(cfg: ConfigDict, date: str | None = None) -> str:
    return CONFIG.daily_path(cfg, date=date)
