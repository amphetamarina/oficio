from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List

try:
    from .oficio_config import load_config, vault_abspath
except Exception:  # pragma: no cover - direct test/import mode
    from oficio_config import load_config, vault_abspath


def _cli_base(cfg: Dict[str, Any]) -> List[str]:
    cmd = [str(cfg.get("obsidian_cli") or "obsidian-cli")]
    vault = str(cfg.get("vault") or "").strip()
    if vault:
        cmd.append(f"vault={vault}")
    return cmd


def run_obsidian(command: str, **kwargs: Any) -> str:
    cfg = load_config()
    args = _cli_base(cfg) + [command]
    for key, value in kwargs.items():
        if value is None:
            continue
        if value is True:
            args.append(str(key))
        elif value is False:
            continue
        else:
            args.append(f"{key}={value}")
    proc = subprocess.run(args, text=True, capture_output=True, timeout=30)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "obsidian-cli failed").strip())
    return proc.stdout


def read_note(path: str) -> str:
    cfg = load_config()
    if cfg.get("use_obsidian_cli", True):
        return run_obsidian("read", path=path)
    return vault_abspath(cfg, path).read_text()


def append_note(path: str, content: str) -> str:
    cfg = load_config()
    if cfg.get("use_obsidian_cli", True):
        return run_obsidian("append", path=path, content=content)
    target = vault_abspath(cfg, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a") as fh:
        fh.write("\n" + content)
    return str(target)


def write_note(path: str, content: str) -> str:
    cfg = load_config()
    if cfg.get("use_obsidian_cli", True):
        return run_obsidian("create", path=path, content=content, overwrite=True)
    target = vault_abspath(cfg, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return str(target)
