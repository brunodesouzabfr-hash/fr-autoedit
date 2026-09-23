#!/usr/bin/env python3
"""Cria distribuição de código determinística e audita caminhos proibidos."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT.parent / "final"
PREFIX = Path("FR_AUTOEDITE_4.0.0_CANDIDATO")
EXCLUDED_PARTS = {
    ".git", ".pytest_cache", ".venv", "__pycache__", "Studio", "entrega",
    "originais", "proxies", "renders", "_ENTRADA", "_RENDERIZACOES",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log", ".zip", ".gz", ".mp4", ".mov", ".mkv"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def allowed(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if any(part in EXCLUDED_PARTS or part.startswith(".env") for part in rel.parts):
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if path.name.startswith("test-"):
        return False
    return path.is_file() and not path.name.startswith(".")


def zip_bytes(archive: zipfile.ZipFile, name: Path, data: bytes, mode: int = 0o644) -> None:
    info = zipfile.ZipInfo(name.as_posix(), date_time=(2026, 9, 22, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (mode & 0xFFFF) << 16
    archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)


def main() -> int:
    FINAL.mkdir(parents=True, exist_ok=True)
    target = FINAL / "FR_AUTOEDITE_4.0.0_CANDIDATO.zip"
    partial = target.with_name("." + target.name + ".partial")
    partial.unlink(missing_ok=True)
    files = sorted(path for path in ROOT.rglob("*") if allowed(path))
    records = [{"path": path.relative_to(ROOT).as_posix(), "sha256": digest(path),
                "bytes": path.stat().st_size} for path in files]
    manifest = {"schema_version": 1, "version": "4.0.0-candidate",
                "source_base": "3.4.0", "generated_at": None,
                "files": records, "count": len(records)}
    with zipfile.ZipFile(partial, "w") as archive:
        for path in files:
            rel = path.relative_to(ROOT)
            executable = path.name in {"fr-autoedite", "install.sh", "INSTALAR_FR_AUTOEDITE_4.sh"} or path.suffix == ".sh"
            zip_bytes(archive, PREFIX / rel, path.read_bytes(), 0o755 if executable else 0o644)
        zip_bytes(archive, PREFIX / "RELEASE_MANIFEST.json",
                  (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    with zipfile.ZipFile(partial) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("CRC inválido na distribuição de código.")
        forbidden = [name for name in archive.namelist() if any(
            part in EXCLUDED_PARTS or part.startswith(".env")
            for part in Path(name).parts
        )]
        if forbidden:
            raise RuntimeError("Caminhos proibidos no ZIP: " + ", ".join(forbidden[:5]))
    partial.replace(target)

    artifacts = [target]
    for source_name in ("FR_CARDS_v2.0.0_CONSOLIDADO.zip", "FR_CARDS_v2.0.0_SEPARADOS.zip"):
        source = ROOT / "entrega" / source_name
        destination = FINAL / source_name
        shutil.copy2(source, destination)
        artifacts.append(destination)
    for source in (
        ROOT / "entrega/FR_CARDS_v2.0.0/qa/PREVIEW_F3_9X16.jpg",
        ROOT / "entrega/FR_CARDS_v2.0.0/qa/PREVIEW_TODAS_1X1.jpg",
        ROOT / "docs/RELATORIO_MIGRACAO.md",
        ROOT / "docs/RELATORIO_VALIDACAO_4_0.md",
    ):
        destination = FINAL / source.name
        shutil.copy2(source, destination)
        artifacts.append(destination)
    checksums = "".join(f"{digest(path)}  {path.name}\n" for path in artifacts)
    (FINAL / "SHA256SUMS.txt").write_text(checksums, encoding="utf-8")
    print(json.dumps({"zip": str(target), "sha256": digest(target),
                      "files": len(records), "final": str(FINAL)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
