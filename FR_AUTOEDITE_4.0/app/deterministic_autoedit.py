"""Orquestração M8 sobre o AutoEdit local existente.

Este módulo não seleciona mídia por conta própria. Ele verifica as entradas,
chama ``build_auto_plan``/``build_random_plan``, passa pelo validador comum e
só então oferece publicação transacional com snapshot recuperável.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import project_scope as scope
from card_timeline import build_raw_card_instance, validate_raw_card_instance
from proxy_integrity import ensure_manifest_integrity
from style_engine import asset_index, style_pack_signature


ENGINE_VERSION = "fr-deterministic-autoedit/1"
CONTROL_PATH = "_CONTROLE/DETERMINISTIC_AUTOEDIT.json"


class DeterministicAutoEditError(ValueError):
    pass


def _digest(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _manifest_basis(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    fields = (
        "id", "status", "media_type", "source_path", "proxy_path", "duration_sec",
        "parent_video", "scene_start_sec", "scene_end_sec", "quality_score",
        "chronological_index", "alphabetical_index", "excluded_from_auto_edit",
    )
    return [
        {key: row.get(key) for key in fields if key in row}
        for row in sorted(
            (item for item in manifest.get("media", []) if isinstance(item, dict)),
            key=lambda item: str(item.get("id") or ""),
        )
    ]


def derive_seed(answers: dict[str, Any], manifest: dict[str, Any]) -> int:
    """Deriva seed estável dos dados editoriais, nunca do relógio do sistema."""
    basis = {
        "context": answers.get("context", {}),
        "story": answers.get("story", {}),
        "edition": answers.get("edition", {}),
        "visual_effects": answers.get("visual_effects", {}),
        "style_pack_id": answers.get("input", {}).get("style_pack_id"),
        "media": _manifest_basis(manifest),
    }
    return int(_digest(basis)[:15], 16) % 1_000_000_000


def normalized_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Representação estável usada por golden tests e IDs, sem auditoria volátil."""
    result = copy.deepcopy(plan)
    for key in ("generated_at", "application"):
        result.pop(key, None)
    automation = result.get("automation")
    if isinstance(automation, dict):
        automation.pop("rollback_version", None)
        automation.pop("plan_id", None)
    return result


def _trusted_external(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(segment.get("media_id")): copy.deepcopy(segment)
        for segment in plan.get("segments", [])
        if isinstance(segment, dict)
        and segment.get("type") == "media"
        and segment.get("external_asset")
        and segment.get("media_id")
    }


def _limitations(usable: list[dict[str, Any]], phase_count: int) -> list[str]:
    limitations = [
        "O resultado é um rascunho determinístico e continua exigindo revisão humana do conteúdo visual.",
        "Balões M4 não são inferidos em raw_media: só são criados onde o contrato de overlay já os representa fielmente.",
        "Nenhum serviço técnico é classificado automaticamente sem configuração ou evidência fornecida pelo usuário.",
    ]
    if len(usable) < max(3, phase_count):
        limitations.append(
            "Material limitado para todas as fases; o plano preserva o que existe sem inventar cenas ou claims."
        )
    return limitations


def _attach_audit_metadata(
    plan: dict[str, Any], *, answers: dict[str, Any], manifest: dict[str, Any],
    style_signature: str, mode: str, seed: int | None,
) -> dict[str, Any]:
    result = copy.deepcopy(plan)
    usable = [
        row for row in manifest.get("media", [])
        if isinstance(row, dict)
        and row.get("status", "ok") == "ok"
        and row.get("proxy_path")
        and not row.get("excluded_from_auto_edit")
    ]
    phases = answers.get("story", {}).get("chronology", [])
    limitations = _limitations(usable, len(phases))
    for index, segment in enumerate(result.get("segments", [])):
        if segment.get("type") == "media":
            segment["decision_reason"] = str(
                segment.get("selection_basis")
                or "Mídia elegível distribuída pelas fases e limites do AutoEdit local."
            )
        else:
            kind = str(segment.get("card_kind") or "phase")
            if kind == "service":
                reason = "Card de serviço solicitado explicitamente na configuração local e resolvido pelo catálogo existente."
            elif kind == "phase":
                reason = "Card derivado da cronologia fornecida no contexto do projeto."
            else:
                reason = "Card estrutural do AutoEdit existente; texto permanece editável no Studio."
            segment["decision_reason"] = reason
            segment["card_instance"] = build_raw_card_instance(
                segment, index, edit_origin="deterministic_auto",
            )
            validate_raw_card_instance(
                segment, index, label=f"segments[{index}].card_instance", manifest=manifest,
            )
    result.setdefault("output", {})["render_source"] = "originals"
    result["manual_editing"] = {
        "preserve_on_regeneration": True,
        "editable_fields": [
            "enabled", "start_sec", "duration_sec", "transition", "title", "body",
            "phase_title", "on_screen_text", "editorial_timelapse", "playback_speed",
        ],
        "instruction": "Revise e edite a timeline no Studio antes de renderizar o master.",
    }
    integrity_states = sorted({
        str((row.get("proxy_integrity") or {}).get("status") or "unverified")
        for row in usable
    })
    result["automation"] = {
        "origin": "deterministic_auto",
        "engine_version": ENGINE_VERSION,
        "mode": mode,
        "seed": seed,
        "offline": True,
        "source_state": {
            "manifest_digest": _digest(_manifest_basis(manifest)),
            "context_digest": _digest({
                "context": answers.get("context", {}),
                "story": answers.get("story", {}),
            }),
            "style_pack_id": answers.get("input", {}).get("style_pack_id"),
            "style_pack_signature": style_signature,
            "proxy_integrity_states": integrity_states,
        },
        "limitations": limitations,
    }
    result["automation"]["plan_id"] = "DA-" + _digest(normalized_plan(result))[:20]
    result["review_status"] = (
        "DETERMINISTIC_LIMITED_DRAFT_REQUIRES_VISUAL_REVIEW"
        if any("Material limitado" in item for item in limitations)
        else "DETERMINISTIC_DRAFT_REQUIRES_VISUAL_REVIEW"
    )
    return result


def generate_plan(
    env: dict[str, Any], project: Path, *, mode: str | None = None,
    seed: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Gera e valida uma proposta sem alterar o projeto."""
    c = SimpleNamespace(**env)
    project = Path(project).resolve()
    answers = c.normalize_answers(c.read_json(project / "QUESTIONARIO_RESPONDIDO.json"))
    input_config = answers.get("input", {})
    input_mode = str(input_config.get("mode") or "raw_media")
    if input_mode != "raw_media" or input_config.get("timeline_locked"):
        raise DeterministicAutoEditError(
            "AutoEdit determinístico remonta somente raw_media. Em ready_video, a timeline do vídeo-base permanece bloqueada."
        )
    manifest = c.read_json(project / "MANIFESTO_MEDIA.json")
    selected_mode = c.normalize_order_mode(mode or answers.get("edition", {}).get("order_mode", "automatico"))
    effective_seed = None
    if selected_mode == "aleatorio":
        if isinstance(seed, bool):
            raise DeterministicAutoEditError("Seed inválida; use um número inteiro.")
        effective_seed = derive_seed(answers, manifest) if seed is None else int(seed)
    answers.setdefault("edition", {})["order_mode"] = selected_mode
    answers["edition"]["render_source"] = "originals"
    verified_manifest = ensure_manifest_integrity(
        project, manifest,
        parameters_for=lambda row: c.proxy_generation_parameters(row, answers),
        probe=c.proxy_probe_metadata, decode_video=c.decode_video_proxy,
    )
    style_pack_id = str(answers.get("input", {}).get("style_pack_id") or "")
    style = asset_index(c.APP_ROOT, style_pack_id)
    if not style.get("ready"):
        raise DeterministicAutoEditError(
            "Style Pack incompleto; assets obrigatórios ausentes: "
            + ", ".join(style.get("missing_required", []))
        )
    baseline = c.build_auto_plan(
        project, answers, verified_manifest, publish=False, seed_override=effective_seed,
    )
    validated = c.validate_imported_plan(
        copy.deepcopy(baseline), verified_manifest, "filme principal",
        trusted_external=_trusted_external(baseline),
    )
    plan = _attach_audit_metadata(
        validated, answers=answers, manifest=verified_manifest,
        style_signature=style_pack_signature(c.APP_ROOT, style_pack_id),
        mode=selected_mode, seed=effective_seed,
    )
    current = scope.read(project / "EDIT_PLAN.json", {})
    report = {
        "schema_version": 1,
        "engine_version": ENGINE_VERSION,
        "status": "proposal_validated",
        "requires_explicit_apply": True,
        "input_mode": input_mode,
        "mode": selected_mode,
        "seed": effective_seed,
        "plan_id": plan["automation"]["plan_id"],
        "changed": normalized_plan(current) != normalized_plan(plan),
        "current_plan_digest": _digest(normalized_plan(current)),
        "proposed_plan_digest": _digest(normalized_plan(plan)),
        "segments": len(plan.get("segments", [])),
        "media_segments": sum(s.get("type") == "media" for s in plan.get("segments", [])),
        "card_segments": sum(s.get("type") == "card" for s in plan.get("segments", [])),
        "limitations": copy.deepcopy(plan["automation"]["limitations"]),
    }
    return plan, report


def apply_plan(
    env: dict[str, Any], project: Path, *, mode: str | None = None,
    seed: int | None = None,
) -> dict[str, Any]:
    """Valida primeiro e publica plano/controle em uma transação recuperável."""
    project = Path(project).resolve()
    with scope.project_lock(project):
        plan, report = generate_plan(env, project, mode=mode, seed=seed)
        rollback = scope.snapshot_decisions(project, "antes-autoedit-deterministico")
        plan["automation"]["rollback_version"] = rollback.name
        control = {
            **report,
            "status": "applied",
            "rollback_version": rollback.name,
            "files": ["EDIT_PLAN.json", "EDIT_PLAN_AUTO.json", CONTROL_PATH],
        }
        scope.publish_files(project, {
            "EDIT_PLAN.json": plan,
            "EDIT_PLAN_AUTO.json": plan,
            CONTROL_PATH: control,
        })
    return {**control, "plan": plan}
