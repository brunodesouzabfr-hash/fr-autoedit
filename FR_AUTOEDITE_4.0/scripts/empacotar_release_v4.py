#!/usr/bin/env python3
"""Cria distribuição de código determinística e audita caminhos proibidos."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT.parent / "final"
PREFIX = Path("FR_AUTOEDITE_4.0.0_CANDIDATO")
EXCLUDED_PARTS = {
    ".git", ".pytest_cache", ".venv", "__pycache__", "CODEX_EXECUTION_PACK",
    "FR_CARD_EDITOR_UNIVERSAL_v1.1.0", "Studio", "entrega", "originais",
    "proxies", "renders", "_ENTRADA", "_EDITAR", "_ENVIAR_CHATGPT",
    "_ENVIAR_IA", "_HISTORICO", "_RENDERIZACOES",
}
EXCLUDED_NAMES = {
    "README CODEX.TXT",
    "promptcodexpart1.txt",
    "promptcodexpart2.txt",
    "promptcodexpart3.txt",
    "FR_CARD_EDITOR_STANDALONE.html",
    "RELEASE_MANIFEST.json",
}
EXCLUDED_SUFFIXES = {
    ".pyc", ".pyo", ".log", ".zip", ".gz", ".tar", ".tgz",
    ".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".mts", ".m2ts",
    ".3gp", ".heic", ".heif", ".dng", ".cr2", ".nef", ".arw",
}
BINARY_ASSET_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".wav", ".mp3",
    ".m4a", ".aac", ".flac", ".ttf", ".otf", ".woff", ".woff2",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def allowed(root: Path, path: Path) -> bool:
    """Aceita apenas payload versionado que pertença à distribuição de código."""
    rel = path.relative_to(root)
    if any(part in EXCLUDED_PARTS or part.startswith(".env") for part in rel.parts):
        return False
    if path.name in EXCLUDED_NAMES:
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if path.suffix.lower() in BINARY_ASSET_SUFFIXES and rel.parts[0] != "assets":
        return False
    if path.name.startswith("test-"):
        return False
    return path.is_file() and not path.is_symlink() and not path.name.startswith(".")


def tracked_files(root: Path) -> list[Path]:
    """Retorna a allowlist do Git relativa a ``root``; falha fechado sem Git."""
    root = root.resolve()
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--", "."],
            check=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(
            "Empacotamento exige um checkout Git para construir a allowlist versionada."
        ) from exc
    files: list[Path] = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        relative = Path(os.fsdecode(raw))
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError(f"Caminho Git inseguro: {relative}")
        candidate = root / relative
        if allowed(root, candidate):
            files.append(candidate)
    return sorted(files, key=lambda item: item.relative_to(root).as_posix())


def zip_bytes(archive: zipfile.ZipFile, name: Path, data: bytes, mode: int = 0o644) -> None:
    info = zipfile.ZipInfo(name.as_posix(), date_time=(2026, 9, 22, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (mode & 0xFFFF) << 16
    archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)


def create_code_archive(root: Path, target: Path, prefix: Path = PREFIX) -> dict:
    """Cria o ZIP somente com a allowlist rastreada e valida o payload final."""
    root = root.resolve()
    target = target.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name("." + target.name + ".partial")
    partial.unlink(missing_ok=True)
    files = tracked_files(root)
    records = [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": digest(path),
            "bytes": path.stat().st_size,
        }
        for path in files
    ]
    manifest = {
        "schema_version": 1,
        "version": "4.0.0-candidate",
        "distribution": "FR AutoEdite 4.0 beta-next",
        "source_base": "3.4.0",
        "generated_at": None,
        "selection": "git-ls-files-allowlist",
        "files": records,
        "count": len(records),
    }
    with zipfile.ZipFile(partial, "w") as archive:
        for path in files:
            rel = path.relative_to(root)
            executable = (
                path.name in {"fr-autoedite", "install.sh", "INSTALAR_FR_AUTOEDITE_4.sh"}
                or path.suffix == ".sh"
            )
            zip_bytes(archive, prefix / rel, path.read_bytes(), 0o755 if executable else 0o644)
        zip_bytes(
            archive,
            prefix / "RELEASE_MANIFEST.json",
            (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        )
    expected = {str(prefix / record["path"]) for record in records}
    expected.add(str(prefix / "RELEASE_MANIFEST.json"))
    with zipfile.ZipFile(partial) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("CRC inválido na distribuição de código.")
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise RuntimeError("O ZIP contém nomes de arquivo duplicados.")
        archived = set(archive.namelist())
        if archived != expected:
            unexpected = sorted(archived - expected)
            missing = sorted(expected - archived)
            raise RuntimeError(
                f"Payload do ZIP diverge da allowlist; extras={unexpected[:5]}, ausentes={missing[:5]}"
            )
        forbidden = [
            name for name in archived
            if not allowed(root, root / Path(name).relative_to(prefix))
            and name != str(prefix / "RELEASE_MANIFEST.json")
        ]
        if forbidden:
            raise RuntimeError("Caminhos proibidos no ZIP: " + ", ".join(forbidden[:5]))
    partial.replace(target)
    return manifest


def main() -> int:
    FINAL.mkdir(parents=True, exist_ok=True)
    target = FINAL / "FR_AUTOEDITE_4.0.0_CANDIDATO.zip"
    manifest = create_code_archive(ROOT, target)
    checksums = f"{digest(target)}  {target.name}\n"
    (FINAL / "SHA256SUMS.txt").write_text(checksums, encoding="utf-8")
    print(json.dumps({"zip": str(target), "sha256": digest(target),
                      "files": manifest["count"], "final": str(FINAL)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
