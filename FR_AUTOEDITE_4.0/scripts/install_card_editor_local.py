#!/usr/bin/env python3
"""Instala somente o pacote modular autorizado do FR Card Editor.

O instalador aceita o diretório extraído ou o ZIP fornecido pelo proprietário
do projeto. O standalone e arquivos não listados nunca são copiados.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from typing import Callable
import zipfile


COMPONENT_ID = "fr-card-editor"
COMPONENT_VERSION = "1.1.0"
FILES = (
    "index.html",
    "assets/background-fr-hd.png",
    "assets/background-fr-source.png",
    "assets/background-fr.png",
    "assets/logo-fr.png",
)
MAX_BYTES = {
    "index.html": 2 * 1024 * 1024,
    "assets/background-fr-hd.png": 16 * 1024 * 1024,
    "assets/background-fr-source.png": 16 * 1024 * 1024,
    "assets/background-fr.png": 16 * 1024 * 1024,
    "assets/logo-fr.png": 16 * 1024 * 1024,
}


class ComponentInstallError(RuntimeError):
    pass


def _directory_reader(source: Path) -> Callable[[str], bytes]:
    root = source
    if not (root / "index.html").is_file():
        children = [item for item in root.iterdir() if item.is_dir()]
        matches = [item for item in children if (item / "index.html").is_file()]
        if len(matches) != 1:
            raise ComponentInstallError("O diretório não contém um pacote modular v1.1.0 identificável.")
        root = matches[0]

    def read(relative: str) -> bytes:
        target = (root / relative).resolve()
        try:
            target.relative_to(root.resolve())
        except ValueError as exc:
            raise ComponentInstallError(f"Arquivo fora do pacote: {relative}.") from exc
        if not target.is_file() or target.is_symlink():
            raise ComponentInstallError(f"Arquivo modular ausente ou inseguro: {relative}.")
        if target.stat().st_size > MAX_BYTES[relative]:
            raise ComponentInstallError(f"Arquivo modular grande demais: {relative}.")
        return target.read_bytes()

    return read


def _zip_reader(source: Path) -> tuple[Callable[[str], bytes], zipfile.ZipFile]:
    try:
        archive = zipfile.ZipFile(source)
    except (OSError, zipfile.BadZipFile) as exc:
        raise ComponentInstallError("ZIP do Card Editor inválido.") from exc
    names = [PurePosixPath(name) for name in archive.namelist() if not name.endswith("/")]
    index_matches = [name for name in names if name.name == "index.html"]
    roots = []
    for name in index_matches:
        root = name.parent
        if all(root.joinpath(*PurePosixPath(relative).parts) in names for relative in FILES):
            roots.append(root)
    if len(roots) != 1:
        archive.close()
        raise ComponentInstallError("O ZIP não contém exatamente um pacote modular v1.1.0 identificável.")
    root = roots[0]

    def read(relative: str) -> bytes:
        member = root.joinpath(*PurePosixPath(relative).parts)
        info = archive.getinfo(str(member))
        mode = (info.external_attr >> 16) & 0o170000
        if mode == 0o120000:
            raise ComponentInstallError(f"Link simbólico não permitido no ZIP: {relative}.")
        if info.file_size > MAX_BYTES[relative]:
            raise ComponentInstallError(f"Arquivo modular grande demais: {relative}.")
        return archive.read(info)

    return read, archive


def read_component(source: Path) -> dict[str, bytes]:
    source = source.expanduser().resolve()
    archive: zipfile.ZipFile | None = None
    if source.is_dir():
        read = _directory_reader(source)
    elif source.is_file() and source.suffix.lower() == ".zip":
        read, archive = _zip_reader(source)
    else:
        raise ComponentInstallError("Informe o diretório extraído ou o ZIP do FR Card Editor v1.1.0.")
    try:
        files = {relative: read(relative) for relative in FILES}
    finally:
        if archive is not None:
            archive.close()
    try:
        html = files["index.html"].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ComponentInstallError("index.html não está em UTF-8.") from exc
    if "FR Card Editor Universal v1.1.0" not in html or "window.FRCardEditor" not in html:
        raise ComponentInstallError("index.html não corresponde ao FR Card Editor Universal v1.1.0.")
    for relative in FILES[1:]:
        if not files[relative].startswith(b"\x89PNG\r\n\x1a\n"):
            raise ComponentInstallError(f"Asset não é PNG válido: {relative}.")
    return files


def manifest_for(files: dict[str, bytes]) -> dict:
    return {
        "schema_version": 1,
        "component_id": COMPONENT_ID,
        "component_version": COMPONENT_VERSION,
        "provenance": {
            "source": "provided_by_project_owner_for_local_integration",
            "license_status": "pending_before_external_publication_or_redistribution",
            "allowed_scope": "local_project_installation",
        },
        "included_files": {
            relative: {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}
            for relative, data in sorted(files.items())
        },
        "excluded_files": ["FR_CARD_EDITOR_STANDALONE.html"],
    }


def install_component(source: Path, destination: Path) -> Path:
    files = read_component(source)
    destination = destination.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".fr-card-editor-install-", dir=destination.parent))
    try:
        for relative, data in files.items():
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (staging / "LOCAL_COMPONENT_MANIFEST.json").write_text(
            json.dumps(manifest_for(files), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if destination.exists():
            backup = destination.with_name(destination.name + ".previous")
            if backup.exists():
                shutil.rmtree(backup)
            os.replace(destination, backup)
        os.replace(staging, destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="Diretório extraído ou ZIP fornecido localmente")
    parser.add_argument("--destination", required=True, type=Path, help="Diretório local do componente instalado")
    args = parser.parse_args()
    try:
        installed = install_component(args.source, args.destination)
    except ComponentInstallError as exc:
        parser.error(str(exc))
    print(f"FR Card Editor modular instalado localmente em: {installed}")
    print("Standalone não copiado. Publicação/redistribuição externa continua bloqueada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
