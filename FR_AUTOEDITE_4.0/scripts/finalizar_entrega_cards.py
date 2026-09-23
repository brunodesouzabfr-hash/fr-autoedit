#!/usr/bin/env python3
"""Produz manifesto integral e ZIP sem temporários ou arquivos ocultos."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origem", type=Path, default=ROOT / "entrega/FR_CARDS_v2.0.0")
    parser.add_argument("--zip", dest="zip_path", type=Path,
                        default=ROOT / "entrega/FR_CARDS_v2.0.0_CONSOLIDADO.zip")
    args = parser.parse_args()
    source, target = args.origem.resolve(), args.zip_path.resolve()
    if not source.is_dir(): raise SystemExit("Gere os cards antes de finalizar.")
    files = [p for p in source.rglob("*") if p.is_file() and p.name != "manifest.json"
             and not any(part.startswith(".") for part in p.relative_to(source).parts)]
    records = [{"path": p.relative_to(source).as_posix(), "sha256": sha(p), "bytes": p.stat().st_size}
               for p in sorted(files)]
    manifest = {"schema_version": 2, "package": "FR_CARDS_v2.0.0_CONSOLIDADO",
                "generated_at": None, "files": records,
                "counts": {"png": sum(p.suffix.lower()==".png" for p in files),
                           "mp4": sum(p.suffix.lower()==".mp4" for p in files),
                           "total": len(files)}}
    manifest_path = source / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name("."+target.name+".partial")
    temporary.unlink(missing_ok=True)
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted([*files, manifest_path]):
            archive.write(path, Path("FR_CARDS_v2.0.0") / path.relative_to(source))
    with zipfile.ZipFile(temporary) as archive:
        broken = archive.testzip()
        if broken: raise RuntimeError("CRC inválido: "+broken)
    temporary.replace(target)
    print(json.dumps({"zip": str(target), "sha256": sha(target), **manifest["counts"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__": raise SystemExit(main())

