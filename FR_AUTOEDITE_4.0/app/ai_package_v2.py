"""Snapshot V2 limpo e determinístico para edição externa assistida."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Callable

import project_scope


PACKAGE_VERSION = 2
DETERMINISTIC_FILES = (
    "CONTEXT.json", "MEDIA_MANIFEST.json", "EDIT_TASK.json", "EDIT_SCHEMA.json",
    "PACKAGE_DESCRIPTOR.json",
)


class AiPackageV2Error(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return (json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ) + "\n").encode("utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _project_file(project: Path, relative: Any, label: str) -> tuple[str, Path]:
    if not isinstance(relative, str) or not relative.strip():
        raise AiPackageV2Error(f"{label}: proxy ausente.")
    candidate = (project / relative).resolve()
    try:
        normalized = candidate.relative_to(project.resolve()).as_posix()
    except ValueError as exc:
        raise AiPackageV2Error(f"{label}: proxy precisa permanecer dentro do projeto.") from exc
    if not candidate.is_file() or candidate.stat().st_size <= 0:
        raise AiPackageV2Error(f"{label}: proxy ausente ou vazio: {normalized}.")
    return normalized, candidate


def _structural_probe(path: Path, media_type: str, probe: Callable[[Path], dict] | None) -> dict[str, Any]:
    if media_type == "image":
        try:
            from PIL import Image
            with Image.open(path) as image:
                image.verify()
        except Exception as exc:
            raise AiPackageV2Error(f"Proxy de imagem corrompido: {path.name}: {exc}") from exc
        return {"decodable": True, "duration_sec": 0.0}
    if probe is None:
        raise AiPackageV2Error(f"Proxy de vídeo exige verificação local: {path.name}.")
    try:
        parsed = probe(path)
    except Exception as exc:
        raise AiPackageV2Error(f"Proxy de vídeo corrompido: {path.name}: {exc}") from exc
    duration = float(parsed.get("duration_sec") or 0)
    if parsed.get("probe_error") or duration <= 0 or not parsed.get("width") or not parsed.get("height"):
        raise AiPackageV2Error(f"Proxy de vídeo corrompido ou sem duração: {path.name}.")
    return {
        "decodable": True, "duration_sec": round(duration, 6),
        "width": int(parsed["width"]), "height": int(parsed["height"]),
        "has_audio": bool(parsed.get("has_audio")),
    }


def _media_inventory(
    project: Path, manifest: dict[str, Any], probe: Callable[[Path], dict] | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    proxy_paths: set[str] = set()
    seen: set[str] = set()
    source_durations = {
        str(row.get("id")): float(row.get("source_duration_sec") or row.get("duration_sec") or 0)
        for row in manifest.get("media", []) if isinstance(row, dict) and row.get("id")
    }
    for index, raw in enumerate(manifest.get("media", []), 1):
        if not isinstance(raw, dict):
            raise AiPackageV2Error(f"MANIFESTO_MEDIA.media[{index}]: esperado objeto.")
        asset_id = str(raw.get("id") or "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", asset_id) or asset_id in seen:
            raise AiPackageV2Error(f"MANIFESTO_MEDIA.media[{index}].id: ID ausente, inválido ou duplicado.")
        seen.add(asset_id)
        if raw.get("status", "ok") != "ok":
            rows.append({
                "asset_id": asset_id, "eligible": False,
                "exclusion_reason": str(raw.get("error") or "status diferente de ok"),
            })
            continue
        if raw.get("excluded_from_auto_edit"):
            rows.append({
                "asset_id": asset_id, "eligible": False,
                "exclusion_reason": "marcado como excluded_from_auto_edit",
            })
            continue
        media_type = str(raw.get("media_type") or "")
        if media_type not in {"image", "video"}:
            rows.append({
                "asset_id": asset_id, "eligible": False,
                "exclusion_reason": f"media_type não suportado: {media_type or 'ausente'}",
            })
            continue
        relative, proxy_path = _project_file(project, raw.get("proxy_path"), f"media[{asset_id}].proxy_path")
        structural = _structural_probe(proxy_path, media_type, probe)
        proxy_paths.add(relative)
        duration = float(raw.get("duration_sec") or 0)
        if media_type == "video" and duration <= 0:
            raise AiPackageV2Error(f"media[{asset_id}].duration_sec: duração inválida.")
        start = float(raw.get("scene_start_sec") or raw.get("source_window_start_sec") or 0)
        end = float(
            raw.get("scene_end_sec") or raw.get("source_window_end_sec")
            or raw.get("source_duration_sec") or duration
        )
        parent_id = str(raw.get("parent_video") or "")
        available_duration = float(
            raw.get("source_duration_sec") or source_durations.get(parent_id) or duration
        )
        if media_type == "video" and (
            start < 0 or end <= start or available_duration <= 0
            or end > available_duration + 0.001
            or (parent_id and end - start > duration + 0.001)
        ):
            raise AiPackageV2Error(
                f"media[{asset_id}]: janela {start:.3f}–{end:.3f}s inválida para "
                f"fonte de {available_duration:.3f}s e item de {duration:.3f}s."
            )
        rows.append({
            "asset_id": asset_id, "eligible": True, "media_type": media_type,
            "duration_sec": round(duration, 6),
            "window": None if media_type == "image" else {
                "time_basis": "absolute_parent_media", "start_sec": round(start, 6),
                "end_sec": round(end, 6),
            },
            "parent_asset_id": parent_id,
            "proxy": {
                "relative_path": relative, "size_bytes": proxy_path.stat().st_size,
                "sha256": _sha256(proxy_path), **structural,
            },
        })
    eligible = [row for row in rows if row.get("eligible")]
    if not eligible:
        raise AiPackageV2Error("Nenhum proxy elegível foi encontrado para o pacote V2.")
    return rows, sorted(proxy_paths)


def build_snapshot(
    project: Path, answers: dict[str, Any], manifest: dict[str, Any], *,
    mode: str = "new_script", base_plan: dict[str, Any] | None = None,
    probe: Callable[[Path], dict] | None = None,
) -> dict[str, Any]:
    project = Path(project).resolve()
    if mode not in {"new_script", "revise_edit"}:
        raise AiPackageV2Error("EDIT_TASK.mode: use new_script ou revise_edit.")
    if mode == "revise_edit" and not isinstance(base_plan, dict):
        raise AiPackageV2Error("revise_edit exige base_plan explícito.")
    rows, proxy_paths = _media_inventory(project, manifest, probe)
    context_paths = (
        project / "_ENTRADA" / "CONTEXTO_PROJETO.md",
        project / "CONTEXTO_PROJETO.md",
    )
    context_text = next(
        (path.read_text(encoding="utf-8", errors="strict") for path in context_paths if path.is_file()),
        "",
    )
    project_data = answers.get("project", {}) if isinstance(answers.get("project"), dict) else {}
    input_data = answers.get("input", {}) if isinstance(answers.get("input"), dict) else {}
    edition = answers.get("edition", {}) if isinstance(answers.get("edition"), dict) else {}
    context = {
        "schema_version": PACKAGE_VERSION,
        "project": {
            key: str(project_data.get(key) or "") for key in ("name", "client", "location")
        },
        "factual_context": context_text.strip(),
        "input_mode": str(input_data.get("mode") or manifest.get("input_mode") or "raw_media"),
        "base_video_id": str(input_data.get("base_video_id") or manifest.get("base_video_id") or ""),
        "timeline_locked": bool(
            str(input_data.get("mode") or manifest.get("input_mode") or "raw_media") == "ready_video"
        ),
        "renderer_configuration": {
            key: edition.get(key) for key in ("format", "width", "height", "fps") if key in edition
        },
    }
    media_manifest = {
        "schema_version": PACKAGE_VERSION,
        "integrity_level": "structural_m6_pending_lineage_m7",
        "assets": rows,
        "eligible_asset_ids": [row["asset_id"] for row in rows if row.get("eligible")],
        "proxy_files": proxy_paths,
    }
    task = {
        "schema_version": PACKAGE_VERSION, "mode": mode,
        "objective": "Criar um novo plano a partir do snapshot atual" if mode == "new_script"
        else "Revisar a edição-base explicitamente selecionada",
        "rules": [
            "referenciar somente asset_id existente", "usar janelas absolute_parent_media",
            "não escrever paths, comandos ou Data URL", "não inventar claims sem evidência",
            "preservar timeline_locked quando ready_video",
        ],
        "base": None if mode == "new_script" else {
            "revision": project_scope.digest(base_plan), "edit_plan": copy.deepcopy(base_plan),
        },
    }
    edit_schema = {
        "schema_version": PACKAGE_VERSION,
        "response": {
            "schema_version": 2, "package_snapshot_id": "snapshot_id publicado no PACKAGE_DESCRIPTOR",
            "edit_plan": "Roteiro Mestre schema 1 ou 2 aceito pelo validator local",
        },
        "essential_segment_fields": [
            "segment_id", "type", "enabled", "duration_sec", "transition",
            "media_id|card_kind", "start_sec para mídia", "title/body para card",
        ],
        "optional_supported_fields": [
            "service_key", "card_instance", "central_media", "playback_speed",
            "narration", "subtitles", "visual", "comparison",
        ],
        "ready_overlay_fields": [
            "overlay_id", "kind", "start_sec", "end_sec", "text", "body",
            "service_key", "position", "safe_area", "animation_in", "animation_out",
            "card_instance", "balloon",
        ],
        "forbidden": ["source_path inventado", "shell", "filesystem", "URL de download", "NaN"],
    }
    core = {
        "CONTEXT.json": context, "MEDIA_MANIFEST.json": media_manifest,
        "EDIT_TASK.json": task, "EDIT_SCHEMA.json": edit_schema,
    }
    snapshot_id = hashlib.sha256(b"".join(
        name.encode("utf-8") + b"\0" + _canonical(core[name])
        for name in sorted(core)
    )).hexdigest()
    descriptor = {
        "schema_version": PACKAGE_VERSION, "snapshot_id": snapshot_id,
        "deterministic_files": sorted(core), "proxy_files": proxy_paths,
        "integrity_status": "m6_structural_only_m7_required",
    }
    return {**core, "PACKAGE_DESCRIPTOR.json": descriptor}


def publish_snapshot(project: Path, documents: dict[str, Any]) -> Path:
    project = Path(project).resolve()
    root = Path("PACOTE_PARA_IA/V2")
    files = {str(root / name): value for name, value in documents.items()}
    descriptor = documents["PACKAGE_DESCRIPTOR.json"]
    files[str(root / "PACKAGE_AUDIT.json")] = {
        "schema_version": PACKAGE_VERSION, "generated_at": project_scope.timestamp(),
        "snapshot_id": descriptor["snapshot_id"],
        "note": "Metadado volátil fora do payload determinístico.",
    }
    project_scope.publish_files(project, files)
    return project / root


def generate_snapshot(
    project: Path, answers: dict[str, Any], manifest: dict[str, Any], *,
    mode: str = "new_script", base_plan: dict[str, Any] | None = None,
    probe: Callable[[Path], dict] | None = None,
) -> Path:
    documents = build_snapshot(
        project, answers, manifest, mode=mode, base_plan=base_plan, probe=probe,
    )
    return publish_snapshot(project, documents)


def load_v2_response(project: Path, path: Path) -> dict[str, Any]:
    try:
        response = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AiPackageV2Error(f"Resposta V2 inválida: {exc}") from exc
    if not isinstance(response, dict) or response.get("schema_version") != PACKAGE_VERSION:
        raise AiPackageV2Error("Resposta V2 exige schema_version=2.")
    descriptor = project_scope.read(Path(project) / "PACOTE_PARA_IA/V2/PACKAGE_DESCRIPTOR.json", {})
    if not descriptor or response.get("package_snapshot_id") != descriptor.get("snapshot_id"):
        raise AiPackageV2Error("package_snapshot_id não corresponde ao snapshot atual.")
    plan = response.get("edit_plan")
    if not isinstance(plan, dict):
        raise AiPackageV2Error("edit_plan: esperado objeto.")
    return copy.deepcopy(plan)
