"""Metadados de entrega reproduzíveis e sem dados pessoais implícitos."""
from __future__ import annotations
import hashlib
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def delivery_record(path: Path, *, project_id: str, version_id: str, profile: str) -> dict:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    return {"file": path.name, "sha256": sha256(path), "bytes": path.stat().st_size,
            "project_id": project_id, "version_id": version_id, "profile": profile}

