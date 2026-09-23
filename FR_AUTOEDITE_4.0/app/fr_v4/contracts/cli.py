"""Funções pequenas para integração segura na CLI pública."""
from __future__ import annotations
import json
from pathlib import Path

from .generator import generate
from .service import inspect, publish


def load_json(path: Path) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} deve conter objeto JSON.")
    return value


def generate_file(project: Path, app_root: Path) -> Path:
    project = Path(project)
    manifest = load_json(project / "MANIFESTO_MEDIA.json")
    config = load_json(project / "QUESTIONARIO_RESPONDIDO.json") if (project / "QUESTIONARIO_RESPONDIDO.json").is_file() else {}
    input_mode = config.get("input", {}).get("mode", "raw_media")
    base = config.get("input", {}).get("base_video_id")
    content, header = generate(manifest=manifest, project_id=project.name, input_mode=input_mode, base_video_id=base,
                               context=str(config.get("context", {}).get("description") or ""))
    root = project / "PACOTE_PARA_IA"
    root.mkdir(parents=True, exist_ok=True)
    target = root / "01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE_v4.md"
    target.write_text(content, encoding="utf-8")
    (root / "00_CABECALHO_IMUTAVEL_v4.json").write_text(json.dumps(header, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return target


def validate_file(project: Path, source: Path, app_root: Path, *, apply: bool = False) -> dict:
    project = Path(project)
    manifest = load_json(project / "MANIFESTO_MEDIA.json")
    header = load_json(project / "PACOTE_PARA_IA/00_CABECALHO_IMUTAVEL_v4.json")
    schema = load_json(app_root / "schemas/roteiro_mestre_v4.schema.json")
    if apply:
        return publish(source, project, expected_header=header, manifest=manifest, schema=schema, app_root=app_root)
    return inspect(source, expected_header=header, manifest=manifest, schema=schema, app_root=app_root)["review"]

