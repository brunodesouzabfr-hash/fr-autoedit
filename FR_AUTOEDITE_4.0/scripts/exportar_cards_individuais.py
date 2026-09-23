#!/usr/bin/env python3
"""Exporta PNGs soltos a partir da árvore consolidada, preservando nomes."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origem", type=Path, default=ROOT / "entrega/FR_CARDS_v2.0.0")
    parser.add_argument("--saida", type=Path, default=ROOT / "entrega/separados")
    parser.add_argument("--zip", dest="zip_path", type=Path,
                        default=ROOT / "entrega/FR_CARDS_v2.0.0_SEPARADOS.zip")
    args = parser.parse_args()
    source, target = args.origem.resolve(), args.saida.resolve()
    target.mkdir(parents=True, exist_ok=True)
    for stale in target.iterdir():
        if stale.is_file() and stale.suffix.lower() == ".png":
            stale.unlink(missing_ok=True)
    count = 0
    for path in sorted(source.glob("cards_*/*/*.png")):
        if path.name.startswith("."):
            continue
        destination = target / path.name
        shutil.copy2(path, destination); count += 1
    if count != 56:
        raise RuntimeError(f"A exportação individual exige 56 cards; recebeu {count}.")
    zip_path = args.zip_path.resolve()
    partial = zip_path.with_name("." + zip_path.name + ".partial")
    partial.unlink(missing_ok=True)
    with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(target.glob("FR_*.png")):
            archive.write(path, Path("FR_CARDS_v2.0.0_SEPARADOS") / path.name)
    with zipfile.ZipFile(partial) as archive:
        if len(archive.namelist()) != 56 or archive.testzip() is not None:
            raise RuntimeError("ZIP de cards separados inválido.")
    partial.replace(zip_path)
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    print(f"{count} cards exportados para {target}; zip={zip_path}; sha256={digest}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
