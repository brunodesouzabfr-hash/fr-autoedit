"""Fronteira segura para sugestões assistidas de cards.

Providers recebem somente dados e devolvem intenção declarativa. Este módulo
não entrega callbacks de escrita, paths do projeto ou execução ao provider.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
from types import SimpleNamespace
from typing import Any, Callable

import card_timeline
import project_scope


SCHEMA_VERSION = 1
ORIGIN = "ai_assisted"
_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
_TOP_FIELDS = frozenset({
    "schema_version", "intent_id", "base_revision", "input_mode", "target_id",
    "origin", "changes", "claims", "evidence", "provenance",
})
_RAW_CHANGES = frozenset({
    "title", "body", "card_kind", "service_key", "duration_sec", "central_media",
})
_READY_CHANGES = frozenset({
    "text", "body", "kind", "service_key", "start_sec", "end_sec", "central_media",
})
_FACTUAL = re.compile(
    r"(?:\b\d+(?:[.,]\d+)?\s*(?:%|mm|cm|m|m²|kg|bar|w|kw|v|a)\b|"
    r"\b(?:norma|garantia|resistência|pressão|carga|potência|economia|redução|certificad[oa])\b)",
    re.IGNORECASE,
)
_CONFIRM_MARKER = re.compile(r"\[\s*dado\s+a\s+confirmar\s*\]", re.IGNORECASE)


class AiCardIntentError(ValueError):
    def __init__(self, code: str, message: str, *, field: str = ""):
        super().__init__(message)
        self.code = code
        self.field = field

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "field": self.field, "message": str(self)}


def _error(code: str, message: str, field: str = "") -> None:
    raise AiCardIntentError(code, message, field=field)


def _text(value: Any, field: str, *, required: bool = False, maximum: int = 2000) -> str:
    if not isinstance(value, str):
        _error("invalid_type", f"{field}: esperado texto.", field)
    result = " ".join(value.replace("\r", "\n").split())
    if required and not result:
        _error("required", f"{field}: texto obrigatório.", field)
    if len(result) > maximum:
        _error("too_long", f"{field}: limite de {maximum} caracteres.", field)
    if _CONFIRM_MARKER.search(result):
        _error(
            "unconfirmed_content",
            f"{field}: [DADO A CONFIRMAR] nunca pode virar texto publicável.", field,
        )
    return result


def _number(value: Any, field: str, low: float, high: float) -> float:
    import math
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        _error("invalid_number", f"{field}: informe número finito, sem aspas.", field)
    result = float(value)
    if not low <= result <= high:
        _error("out_of_range", f"{field}: use valor entre {low:g} e {high:g}.", field)
    return result


def _load(project: Path) -> tuple[str, Path, dict[str, Any], dict[str, Any]]:
    manifest = project_scope.read(project / "MANIFESTO_MEDIA.json", {})
    mode = str(manifest.get("input_mode") or "raw_media")
    target = project / ("READY_VIDEO_PLAN.json" if mode == "ready_video" else "EDIT_PLAN.json")
    plan = project_scope.read(target, {})
    if not manifest.get("media") or not plan:
        _error("project_not_ready", "Prepare o projeto e a timeline antes de revisar uma intenção.")
    return mode, target, plan, manifest


def current_revision(project: Path) -> str:
    _mode, _target, plan, _manifest = _load(Path(project))
    return project_scope.digest(plan)


def _find_target(plan: dict[str, Any], mode: str, target_id: str) -> tuple[int, dict[str, Any]]:
    key, rows = (
        ("overlay_id", plan.get("overlays", []))
        if mode == "ready_video" else ("segment_id", plan.get("segments", []))
    )
    matches = [(index, row) for index, row in enumerate(rows) if row.get(key) == target_id]
    if len(matches) != 1:
        _error("unknown_target", f"target_id: card único não encontrado: `{target_id}`.", "target_id")
    index, row = matches[0]
    if mode == "ready_video":
        if row.get("kind") not in {"common_card", "service_card"}:
            _error("unsupported_target", "target_id: somente cards ready_video são editáveis.", "target_id")
    elif row.get("type") != "card":
        _error("unsupported_target", "target_id: somente segmentos card são editáveis.", "target_id")
    return index, row


def _capabilities(mode: str, row: dict[str, Any]) -> dict[str, Any]:
    fields = sorted(_READY_CHANGES if mode == "ready_video" else _RAW_CHANGES)
    return {
        "schema_version": SCHEMA_VERSION,
        "input_mode": mode,
        "target_id": str(row.get("overlay_id") or row.get("segment_id") or ""),
        "supported_change_fields": fields,
        "card_kinds": ["intro", "service", "phase", "outro", "detail", "comparison"],
        "ready_kinds": ["common_card", "service_card"],
        "central_media": {
            "service_only": True, "shape": "circle", "crop": "1:1",
            "zoom": [1.0, 4.0], "focal_x": [0.0, 1.0], "focal_y": [0.0, 1.0],
        },
        "unsupported": ["paths", "data_urls", "free_geometry", "filesystem", "shell", "render"],
    }


def build_provider_request(project: Path, target_id: str, task: str) -> dict[str, Any]:
    project = Path(project)
    mode, _target, plan, manifest = _load(project)
    _index, row = _find_target(plan, mode, target_id)
    media = [
        {
            key: copy.deepcopy(item.get(key))
            for key in ("id", "media_type", "duration_sec", "status", "parent_video")
            if key in item
        }
        for item in manifest.get("media", []) if isinstance(item, dict)
    ]
    return {
        "request_version": 1,
        "task": _text(task, "task", required=True, maximum=1200),
        "base_revision": project_scope.digest(plan),
        "current_card": copy.deepcopy(row),
        "manifest_media": media,
        "capabilities": _capabilities(mode, row),
        "required_output": "AI_CARD_INTENT",
    }


def request_provider_intent(provider: Callable[[dict[str, Any]], Any], request: dict[str, Any]) -> dict[str, Any]:
    if not callable(provider):
        _error("invalid_provider", "Provider precisa ser uma função que devolve AI_CARD_INTENT.")
    # Cópia profunda impede o provider de alterar o snapshot mantido pelo app.
    result = provider(copy.deepcopy(request))
    if not isinstance(result, dict):
        _error("invalid_provider_response", "Provider não devolveu um objeto AI_CARD_INTENT.")
    return copy.deepcopy(result)


def _validate_evidence(intent: dict[str, Any], manifest: dict[str, Any], public_texts: list[str]) -> tuple[list[dict], list[dict]]:
    evidence = intent.get("evidence", [])
    claims = intent.get("claims", [])
    if not isinstance(evidence, list) or len(evidence) > 100:
        _error("invalid_evidence", "evidence: use lista com até 100 itens.", "evidence")
    if not isinstance(claims, list) or len(claims) > 100:
        _error("invalid_claims", "claims: use lista com até 100 itens.", "claims")
    media_ids = {str(item.get("id")) for item in manifest.get("media", []) if item.get("status", "ok") == "ok"}
    by_id: dict[str, dict] = {}
    normalized_evidence = []
    allowed_kinds = {"project_media", "user_provided", "documented_fact", "render_3d", "reference"}
    for index, raw in enumerate(evidence, 1):
        field = f"evidence[{index}]"
        if not isinstance(raw, dict):
            _error("invalid_evidence", f"{field}: esperado objeto.", field)
        unknown = sorted(set(raw) - {"evidence_id", "kind", "media_id", "source", "description"})
        if unknown:
            _error("unknown_field", f"{field}: campos desconhecidos: {', '.join(unknown)}.", field)
        evidence_id = str(raw.get("evidence_id") or "")
        if not _ID.fullmatch(evidence_id) or evidence_id in by_id:
            _error("invalid_evidence_id", f"{field}.evidence_id: ID único inválido.", field + ".evidence_id")
        kind = str(raw.get("kind") or "")
        if kind not in allowed_kinds:
            _error("invalid_evidence_kind", f"{field}.kind: tipo de evidência desconhecido.", field + ".kind")
        media_id = str(raw.get("media_id") or "")
        if media_id and media_id not in media_ids:
            _error("unknown_media_id", f"{field}.media_id: `{media_id}` não pertence ao manifesto.", field + ".media_id")
        if kind == "project_media" and not media_id:
            _error("required", f"{field}.media_id: obrigatório para project_media.", field + ".media_id")
        item = {
            "evidence_id": evidence_id, "kind": kind, "media_id": media_id,
            "source": _text(raw.get("source", ""), field + ".source", required=True, maximum=300),
            "description": _text(raw.get("description", ""), field + ".description", required=True, maximum=1000),
        }
        by_id[evidence_id] = item
        normalized_evidence.append(item)
    normalized_claims = []
    for index, raw in enumerate(claims, 1):
        field = f"claims[{index}]"
        if not isinstance(raw, dict) or set(raw) - {"claim_id", "text", "evidence_ids"}:
            _error("invalid_claim", f"{field}: use claim_id, text e evidence_ids.", field)
        claim_id = str(raw.get("claim_id") or "")
        if not _ID.fullmatch(claim_id):
            _error("invalid_claim_id", f"{field}.claim_id: ID inválido.", field + ".claim_id")
        text = _text(raw.get("text", ""), field + ".text", required=True, maximum=1000)
        evidence_ids = raw.get("evidence_ids", [])
        if (
            not isinstance(evidence_ids, list) or not evidence_ids
            or any(not isinstance(item, str) or item not in by_id for item in evidence_ids)
        ):
            _error("missing_evidence", f"{field}.evidence_ids: referencie evidência existente.", field + ".evidence_ids")
        usable = [by_id[item] for item in evidence_ids if by_id[item]["kind"] not in {"render_3d", "reference"}]
        if not usable:
            _error(
                "insufficient_evidence",
                f"{field}: render 3D ou referência visual isolada não comprova execução real.", field,
            )
        if not any(text.casefold() in public.casefold() for public in public_texts):
            _error("claim_not_public", f"{field}.text: claim não aparece no texto proposto.", field + ".text")
        normalized_claims.append({"claim_id": claim_id, "text": text, "evidence_ids": list(evidence_ids)})
    for public in public_texts:
        if _FACTUAL.search(public) and not any(claim["text"].casefold() in public.casefold() for claim in normalized_claims):
            _error(
                "unsubstantiated_claim",
                "Texto técnico/factual requer claim explícito e evidência com proveniência.", "changes",
            )
    return normalized_claims, normalized_evidence


def _validate_intent(intent: Any, mode: str, plan: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(intent, dict):
        _error("invalid_intent", "AI_CARD_INTENT: esperado objeto JSON.")
    unknown = sorted(set(intent) - _TOP_FIELDS)
    if unknown:
        _error("unknown_field", f"AI_CARD_INTENT: campos desconhecidos: {', '.join(unknown)}.")
    if intent.get("schema_version") != SCHEMA_VERSION or isinstance(intent.get("schema_version"), bool):
        _error("unsupported_version", "schema_version: versão suportada é 1.", "schema_version")
    intent_id = str(intent.get("intent_id") or "")
    if not _ID.fullmatch(intent_id):
        _error("invalid_intent_id", "intent_id: ID inválido.", "intent_id")
    if intent.get("origin") != ORIGIN:
        _error("invalid_origin", "origin: AI_CARD_INTENT exige ai_assisted.", "origin")
    if intent.get("input_mode") != mode:
        _error("wrong_input_mode", f"input_mode: projeto atual usa {mode}.", "input_mode")
    revision = project_scope.digest(plan)
    if intent.get("base_revision") != revision:
        _error("stale_revision", "base_revision: a timeline mudou; gere nova intenção.", "base_revision")
    target_id = str(intent.get("target_id") or "")
    if not _ID.fullmatch(target_id):
        _error("invalid_target_id", "target_id: ID inválido.", "target_id")
    _index, current = _find_target(plan, mode, target_id)
    changes = intent.get("changes")
    if not isinstance(changes, dict) or not changes:
        _error("empty_changes", "changes: informe ao menos uma alteração suportada.", "changes")
    allowed = _READY_CHANGES if mode == "ready_video" else _RAW_CHANGES
    unsupported = sorted(set(changes) - allowed)
    if unsupported:
        _error("unsupported_field", f"changes: campos não suportados: {', '.join(unsupported)}.", "changes")
    normalized_changes: dict[str, Any] = {}
    for field, value in changes.items():
        if field in {"title", "text", "body"}:
            normalized_changes[field] = _text(value, "changes." + field, maximum=2000)
        elif field == "duration_sec":
            normalized_changes[field] = _number(value, "changes.duration_sec", 0.04, 600)
        elif field in {"start_sec", "end_sec"}:
            normalized_changes[field] = _number(value, "changes." + field, 0, 21600)
        elif field == "card_kind":
            value = str(value)
            if value not in {"intro", "service", "phase", "outro", "detail", "comparison"}:
                _error("unsupported_value", "changes.card_kind: família não suportada.", "changes.card_kind")
            normalized_changes[field] = value
        elif field == "kind":
            value = str(value)
            if value not in {"common_card", "service_card"}:
                _error("unsupported_value", "changes.kind: use common_card ou service_card.", "changes.kind")
            normalized_changes[field] = value
        elif field == "service_key":
            value = str(value)
            normalized_changes[field] = value
        elif field == "central_media":
            if value is not None and not isinstance(value, dict):
                _error("invalid_type", "changes.central_media: use objeto ou null.", "changes.central_media")
            normalized_changes[field] = copy.deepcopy(value)
    public_texts = [
        value for key, value in normalized_changes.items()
        if key in {"title", "text", "body"} and value
    ]
    claims, evidence = _validate_evidence(intent, manifest, public_texts)
    provenance = intent.get("provenance")
    if not isinstance(provenance, dict) or set(provenance) - {"provider", "model", "request_id"}:
        _error("invalid_provenance", "provenance: use provider, model e request_id.", "provenance")
    normalized_provenance = {
        key: _text(provenance.get(key, ""), "provenance." + key, required=True, maximum=200)
        for key in ("provider", "model", "request_id")
    }
    return {
        "schema_version": SCHEMA_VERSION, "intent_id": intent_id,
        "base_revision": revision, "input_mode": mode, "target_id": target_id,
        "origin": ORIGIN, "changes": normalized_changes, "claims": claims,
        "evidence": evidence, "provenance": normalized_provenance,
        "current": copy.deepcopy(current),
    }


def _candidate(env: dict[str, Any], plan: dict[str, Any], manifest: dict[str, Any], normalized: dict[str, Any]) -> dict[str, Any]:
    import fr_autoedite as fr
    from master_contract import validate_ready_video_contract

    mode = normalized["input_mode"]
    candidate = copy.deepcopy(plan)
    index, row = _find_target(candidate, mode, normalized["target_id"])
    changes = normalized["changes"]
    row.update({key: copy.deepcopy(value) for key, value in changes.items() if key != "central_media"})
    services = fr.load_service_catalog()
    service_key = str(row.get("service_key") or "")
    if service_key and service_key not in services:
        _error("unknown_service", f"changes.service_key: serviço desconhecido `{service_key}`.", "changes.service_key")
    if mode == "ready_video":
        if row.get("kind") == "service_card" and not service_key:
            _error("missing_service", "service_card exige service_key.", "changes.service_key")
        if row.get("kind") != "service_card" and changes.get("central_media") is not None:
            _error("unsupported_media", "Mídia central só é reproduzível em service_card.", "changes.central_media")
        row["card_instance"] = card_timeline.build_ready_card_instance(row, edit_origin=ORIGIN)
        if "central_media" in changes and changes["central_media"] is not None:
            row["card_instance"]["central_media"] = copy.deepcopy(changes["central_media"])
        elif changes.get("central_media") is None and "central_media" in changes:
            row["card_instance"].pop("central_media", None)
        candidate["overlays"][index] = row
        try:
            validated, _notices = validate_ready_video_contract(SimpleNamespace(**env), candidate, manifest)
        except fr.AutoEditeError as exc:
            _error("contract_rejected", str(exc), "changes")
        return validated
    if row.get("card_kind") == "service" and not service_key:
        _error("missing_service", "card_kind service exige service_key.", "changes.service_key")
    if row.get("card_kind") != "service" and changes.get("central_media") is not None:
        _error("unsupported_media", "Mídia central só é reproduzível em F3/SERVICE.", "changes.central_media")
    row["card_instance"] = card_timeline.build_raw_card_instance(row, index, edit_origin=ORIGIN)
    if "central_media" in changes and changes["central_media"] is not None:
        row["card_instance"]["central_media"] = copy.deepcopy(changes["central_media"])
    elif changes.get("central_media") is None and "central_media" in changes:
        row["card_instance"].pop("central_media", None)
    candidate["segments"][index] = row
    try:
        trusted = {
            item["media_id"]: item for item in plan.get("segments", []) if item.get("external_asset")
        }
        return fr.validate_imported_plan(candidate, manifest, "AI_CARD_INTENT", trusted)
    except fr.AutoEditeError as exc:
        _error("contract_rejected", str(exc), "changes")


def _diff(before: Any, after: Any, path: str = "") -> list[dict[str, Any]]:
    if before == after:
        return []
    if isinstance(before, dict) and isinstance(after, dict):
        result = []
        for key in sorted(set(before) | set(after)):
            child = f"{path}.{key}" if path else key
            result.extend(_diff(before.get(key), after.get(key), child))
        return result
    return [{"path": path, "before": copy.deepcopy(before), "after": copy.deepcopy(after)}]


def review_intent(env: dict[str, Any], project: Path, intent: Any) -> dict[str, Any]:
    project = Path(project).resolve()
    mode, target, plan, manifest = _load(project)
    normalized = _validate_intent(intent, mode, plan, manifest)
    candidate = _candidate(env, plan, manifest, normalized)
    changes = _diff(plan, candidate)
    if not changes:
        _error("no_effect", "A intenção validada não produz mudança.", "changes")
    payload = {
        "intent": {key: value for key, value in normalized.items() if key != "current"},
        "before_revision": project_scope.digest(plan),
        "after_revision": project_scope.digest(candidate),
        "diff": changes,
    }
    token = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "valid": True, "requires_confirmation": True, "confirmation_token": token,
        "target_file": target.name, "candidate_plan": candidate, **payload,
    }
