#!/usr/bin/env python3
"""Instalador local conservador: backup de código e preservação de Studio/."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE = {"Studio", "entrega", ".git", ".env", "__pycache__", ".pytest_cache"}


def ignored(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in EXCLUDE or name.endswith((".zip", ".tar.gz"))}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destino", type=Path, default=Path("~/FR-AutoEdite/FR_AUTOEDITE_4.0").expanduser())
    args = parser.parse_args()
    target = args.destino.expanduser().resolve()
    if target == Path.home() or target == Path("/"):
        raise SystemExit("Destino amplo/proibido.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if target.exists():
        backup = target.parent / f"{target.name}.backup-{stamp}"
        shutil.copytree(target, backup, ignore=ignored)
        print(f"backup: {backup}")
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT, target, dirs_exist_ok=True, ignore=ignored)
    for name in ("fr-autoedite", "install.sh"):
        path = target / name
        if path.is_file(): path.chmod(path.stat().st_mode | 0o111)
    print(f"instalado: {target}")
    print(f"execute: {target / 'fr-autoedite'} --version")
    return 0


if __name__ == "__main__": raise SystemExit(main())

