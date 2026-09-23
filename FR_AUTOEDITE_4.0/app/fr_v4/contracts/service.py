"""Serviço transacional do contrato Markdown↔IA v4."""
from __future__ import annotations
import json
import os
from pathlib import Path
import tempfile

from .markdown import parse
from .validation import validate
from ..style_packs.registry import load as load_assets


def inspect(path: Path, *, expected_header: dict, manifest: dict, schema: dict, app_root: Path) -> dict:
    document = parse(Path(path).read_text(encoding="utf-8"))
    assets = load_assets(app_root).get("assets", {})
    review = validate(document, expected_header=expected_header, manifest=manifest, schema=schema, assets=assets)
    return {"document": document, "review": review}


def publish(path: Path, project: Path, *, expected_header: dict, manifest: dict,
            schema: dict, app_root: Path) -> dict:
    result = inspect(path, expected_header=expected_header, manifest=manifest, schema=schema, app_root=app_root)
    project = Path(project).resolve()
    target_dir = project / "_ROTEIROS" / "v4"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "ROTEIRO_MESTRE_EDITADO_E_DEVOLVIDO.md"
    payload_target = target_dir / "ROTEIRO_MESTRE_VALIDADO.json"
    for destination, content in ((target, Path(path).read_text(encoding="utf-8")),
                                 (payload_target, json.dumps(result["document"].payload, ensure_ascii=False, indent=2)+"\n")):
        fd, name = tempfile.mkstemp(prefix=".fr-contract-", dir=target_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(content); stream.flush(); os.fsync(stream.fileno())
            os.replace(name, destination)
        finally:
            if os.path.exists(name): os.unlink(name)
    return {**result["review"], "applied": True, "markdown": str(target), "payload": str(payload_target)}

