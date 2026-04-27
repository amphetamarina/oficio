from __future__ import annotations

import subprocess
from typing import Any

try:
    from .oficio_config import ConfigDict, load_config, vault_abspath
except Exception:  # pragma: no cover - direct test/import mode
    from oficio_config import ConfigDict, load_config, vault_abspath


class ObsidianVault:
    def run(self, command: str, **kwargs: Any) -> str:
        cfg = load_config()
        proc = subprocess.run(
            self._args(cfg, command, kwargs),
            text=True,
            capture_output=True,
            timeout=30,
        )
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or proc.stdout or "obsidian-cli failed").strip())
        return proc.stdout

    def read(self, path: str) -> str:
        cfg = load_config()
        if self._use_cli(cfg):
            return self.run("read", path=path)
        return vault_abspath(cfg, path).read_text()

    def append(self, path: str, content: str) -> str:
        cfg = load_config()
        if self._use_cli(cfg):
            return self.run("append", path=path, content=content)

        target = vault_abspath(cfg, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a") as file:
            file.write("\n" + content)
        return str(target)

    def write(self, path: str, content: str) -> str:
        cfg = load_config()
        if self._use_cli(cfg):
            return self.run("create", path=path, content=content, overwrite=True)

        target = vault_abspath(cfg, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return str(target)

    def _args(self, cfg: ConfigDict, command: str, kwargs: dict[str, Any]) -> list[str]:
        args = self._base_args(cfg) + [command]
        args.extend(self._format_arg(key, value) for key, value in kwargs.items() if self._include_arg(value))
        return args

    def _base_args(self, cfg: ConfigDict) -> list[str]:
        args = [str(cfg.get("obsidian_cli") or "obsidian-cli")]
        vault = str(cfg.get("vault") or "").strip()
        if vault:
            args.append(f"vault={vault}")
        return args

    def _use_cli(self, cfg: ConfigDict) -> bool:
        return bool(cfg.get("use_obsidian_cli", True))

    def _include_arg(self, value: Any) -> bool:
        return value is not None and value is not False

    def _format_arg(self, key: str, value: Any) -> str:
        return str(key) if value is True else f"{key}={value}"


VAULT = ObsidianVault()


def run_obsidian(command: str, **kwargs: Any) -> str:
    return VAULT.run(command, **kwargs)


def read_note(path: str) -> str:
    return VAULT.read(path)


def append_note(path: str, content: str) -> str:
    return VAULT.append(path, content)


def write_note(path: str, content: str) -> str:
    return VAULT.write(path, content)
