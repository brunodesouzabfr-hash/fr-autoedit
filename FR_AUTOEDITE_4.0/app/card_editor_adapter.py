"""Versioned, content-only bridge for existing raw and ready-video cards.

The bridge intentionally maps only ``title`` and ``body``. Geometry, lines,
crop data and embedded assets stay outside the project contract until the
renderer can reproduce them faithfully. In ready-video mode only explicit
``common_card`` and ``service_card`` overlays have a lossless two-field map.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any


ADAPTER_VERSION = "fr-autoedite-card-content/1"
SUPPORTED_FIELDS = ("title", "body")
UNSUPPORTED_FIELDS = ("geometry", "lines", "crop", "assets", "data_url")
MAX_TEXT_LENGTH = 220
_SEGMENT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_OVERLAY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_DATA_URL = re.compile(r"data:[^,\s]{1,200};base64,", re.IGNORECASE)
READY_CARD_KINDS = ("common_card", "service_card")


class CardEditorAdapterError(ValueError):
    """Raised before any project mutation when the bridge payload is invalid."""


def plan_revision(plan: dict[str, Any]) -> str:
    """Return a deterministic revision used to reject stale browser edits."""
    if not isinstance(plan, dict):
        raise CardEditorAdapterError("Plano de edição inválido.")
    try:
        serialized = json.dumps(
            plan, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CardEditorAdapterError("Plano de edição não pode ser versionado.") from exc
    return hashlib.sha256(serialized).hexdigest()


def _segment_id(value: Any) -> str:
    if not isinstance(value, str) or not _SEGMENT_ID.fullmatch(value):
        raise CardEditorAdapterError("segment_id inválido.")
    return value


def _card(plan: dict[str, Any], segment_id: str) -> dict[str, Any]:
    segments = plan.get("segments")
    if not isinstance(segments, list):
        raise CardEditorAdapterError("O projeto não possui uma timeline raw válida.")
    matches = [
        item for item in segments
        if isinstance(item, dict) and item.get("segment_id") == segment_id
    ]
    if not matches:
        raise CardEditorAdapterError("Card não encontrado na timeline atual.")
    if len(matches) != 1:
        raise CardEditorAdapterError("segment_id duplicado na timeline; corrija o plano antes de editar.")
    if matches[0].get("type") != "card":
        raise CardEditorAdapterError("O segmento selecionado não é um card raw.")
    return matches[0]


def _overlay_id(value: Any) -> str:
    if not isinstance(value, str) or not _OVERLAY_ID.fullmatch(value):
        raise CardEditorAdapterError("overlay_id inválido.")
    return value


def _ready_overlay(plan: dict[str, Any], overlay_id: str) -> dict[str, Any]:
    if plan.get("input_mode") != "ready_video" or plan.get("timeline_locked") is not True:
        raise CardEditorAdapterError("O projeto ready_video não possui timeline_locked=true.")
    overlays = plan.get("overlays")
    if not isinstance(overlays, list):
        raise CardEditorAdapterError("O projeto não possui overlays ready_video válidos.")
    matches = [
        item for item in overlays
        if isinstance(item, dict) and item.get("overlay_id") == overlay_id
    ]
    if not matches:
        raise CardEditorAdapterError("Overlay não encontrado no plano ready_video atual.")
    if len(matches) != 1:
        raise CardEditorAdapterError("overlay_id duplicado; corrija o plano antes de editar.")
    return matches[0]


def ready_overlay_editability(overlay: Any) -> dict[str, Any]:
    if not isinstance(overlay, dict):
        return {"available": False, "reason": "Overlay inválido."}
    kind = str(overlay.get("kind") or "")
    if kind not in READY_CARD_KINDS:
        return {
            "available": False,
            "reason": (
                f"{kind or 'overlay'} não possui title/body de card; "
                "o renderer usa outro contrato visual."
            ),
        }
    if not isinstance(overlay.get("text"), str) or not overlay["text"].strip():
        return {
            "available": False,
            "reason": "O card usa título de fallback; informe e salve um título explícito primeiro.",
        }
    if not isinstance(overlay.get("body"), str) or not overlay["body"].strip():
        return {
            "available": False,
            "reason": "O card usa corpo de fallback; informe e salve um corpo explícito primeiro.",
        }
    return {"available": True, "reason": "title/body têm round-trip fiel no renderer ready_video."}


def _text(value: Any, field: str, *, required: bool) -> str:
    if not isinstance(value, str):
        raise CardEditorAdapterError(f"fields.{field}: esperado texto.")
    value = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if required and not value:
        raise CardEditorAdapterError(f"fields.{field}: o título não pode ficar vazio.")
    if len(value) > MAX_TEXT_LENGTH:
        raise CardEditorAdapterError(
            f"fields.{field}: limite de {MAX_TEXT_LENGTH} caracteres para o renderer atual."
        )
    if any(ord(character) < 32 and character not in "\n\t" for character in value):
        raise CardEditorAdapterError(f"fields.{field}: contém caractere de controle inválido.")
    if _DATA_URL.search(value):
        raise CardEditorAdapterError(
            f"fields.{field}: Data URL não é aceita pelo adapter de conteúdo."
        )
    return value


def export_card_content(plan: dict[str, Any], segment_id: str) -> dict[str, Any]:
    """Map an existing raw card into the public, versioned editing contract."""
    segment_id = _segment_id(segment_id)
    segment = _card(plan, segment_id)
    return {
        "adapter_version": ADAPTER_VERSION,
        "base_revision": plan_revision(plan),
        "segment_id": segment_id,
        "source": {
            "input_mode": "raw_media",
            "card_kind": str(segment.get("card_kind") or ""),
            "card_family": str(segment.get("card_family") or ""),
        },
        "fields": {
            "title": str(segment.get("title") or ""),
            "body": str(segment.get("body") or ""),
        },
        "capabilities": {
            "supported_fields": list(SUPPORTED_FIELDS),
            "unsupported_fields": list(UNSUPPORTED_FIELDS),
            "preserves_renderer_families": ["F1", "F2", "F3", "F4", "F5", "F6"],
            "embedded_assets": False,
        },
    }


def export_ready_card_content(plan: dict[str, Any], overlay_id: str) -> dict[str, Any]:
    """Map a ready-video card overlay only when both rendered fields are explicit."""
    overlay_id = _overlay_id(overlay_id)
    overlay = _ready_overlay(plan, overlay_id)
    capability = ready_overlay_editability(overlay)
    if not capability["available"]:
        raise CardEditorAdapterError(str(capability["reason"]))
    return {
        "adapter_version": ADAPTER_VERSION,
        "base_revision": plan_revision(plan),
        "segment_id": overlay_id,
        "source": {
            "input_mode": "ready_video",
            "overlay_kind": str(overlay.get("kind") or ""),
            "timeline_locked": True,
            "base_video_id": str(plan.get("base_video_id") or ""),
        },
        "fields": {
            "title": str(overlay["text"]),
            "body": str(overlay["body"]),
        },
        "capabilities": {
            "supported_fields": list(SUPPORTED_FIELDS),
            "unsupported_fields": list(UNSUPPORTED_FIELDS),
            "ready_card_kinds": list(READY_CARD_KINDS),
            "embedded_assets": False,
        },
    }


def _validated_payload(plan: dict[str, Any], payload: Any) -> tuple[str, str, str]:
    if not isinstance(payload, dict):
        raise CardEditorAdapterError("Payload do adapter deve ser um objeto JSON.")
    required = {"adapter_version", "base_revision", "segment_id", "fields"}
    received = set(payload)
    if received != required:
        unknown = sorted(received - required)
        missing = sorted(required - received)
        details = []
        if unknown:
            details.append("não suportado: " + ", ".join(unknown))
        if missing:
            details.append("ausente: " + ", ".join(missing))
        raise CardEditorAdapterError("Payload fora do contrato (" + "; ".join(details) + ").")
    if payload["adapter_version"] != ADAPTER_VERSION:
        raise CardEditorAdapterError(
            f"adapter_version incompatível; esperado {ADAPTER_VERSION}."
        )
    revision = payload["base_revision"]
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{64}", revision):
        raise CardEditorAdapterError("base_revision inválida.")
    if revision != plan_revision(plan):
        raise CardEditorAdapterError(
            "A timeline mudou desde que o card foi aberto. Recarregue antes de salvar."
        )
    fields = payload["fields"]
    if not isinstance(fields, dict) or set(fields) != set(SUPPORTED_FIELDS):
        raise CardEditorAdapterError("fields aceita somente title e body, ambos presentes.")
    title = _text(fields["title"], "title", required=True)
    body = _text(fields["body"], "body", required=False)
    return str(payload["segment_id"]), title, body


def apply_card_content(plan: dict[str, Any], payload: Any) -> dict[str, Any]:
    """Validate a bridge payload and return a new plan with only text changed."""
    item_id, title, body = _validated_payload(plan, payload)
    segment_id = _segment_id(item_id)

    updated = copy.deepcopy(plan)
    card = _card(updated, segment_id)
    card["title"] = title
    card["body"] = body
    return updated


def apply_ready_card_content(plan: dict[str, Any], payload: Any) -> dict[str, Any]:
    """Update only explicit text/body on an existing ready-video card overlay."""
    item_id, title, body = _validated_payload(plan, payload)
    if not body:
        raise CardEditorAdapterError(
            "fields.body: o corpo não pode ficar vazio em cards ready_video porque acionaria fallback visual."
        )
    overlay_id = _overlay_id(item_id)
    current = _ready_overlay(plan, overlay_id)
    capability = ready_overlay_editability(current)
    if not capability["available"]:
        raise CardEditorAdapterError(str(capability["reason"]))
    updated = copy.deepcopy(plan)
    overlay = _ready_overlay(updated, overlay_id)
    overlay["text"] = title
    overlay["body"] = body
    return updated
