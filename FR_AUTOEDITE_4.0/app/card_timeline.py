"""Contrato aditivo de placement para instâncias de card.

O renderer continua usando os campos físicos históricos: ordem/duration_sec em
raw_media e start_sec/end_sec em ready_video.  ``card_instance`` registra a
mesma decisão de forma versionada e auditável, sem migrar planos legados.
"""
from __future__ import annotations

import math
import re
from typing import Any

from card_media import CardMediaError, validate_central_media


SCHEMA_VERSION = 1
EDIT_ORIGINS = frozenset({"manual", "deterministic_auto", "ai_assisted"})
READY_CARD_KINDS = frozenset({"common_card", "service_card"})
_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")
_COMMON_FIELDS = frozenset({
    "schema_version", "instance_id", "definition_id", "definition_version",
    "edit_origin", "placement", "central_media",
})


class CardTimelineError(ValueError):
    pass


def _finite(value: Any, label: str, *, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise CardTimelineError(f"{label}: informe um número finito, sem aspas.")
    number = float(value)
    if number < minimum:
        raise CardTimelineError(f"{label}: use valor maior ou igual a {minimum:g}.")
    return number


def _common(instance: Any, *, expected_id: str, expected_definition: str, label: str) -> dict[str, Any]:
    if not isinstance(instance, dict):
        raise CardTimelineError(f"{label}: esperado objeto.")
    unknown = sorted(set(instance) - _COMMON_FIELDS)
    if unknown:
        raise CardTimelineError(f"{label}: campos desconhecidos: {', '.join(unknown)}.")
    if isinstance(instance.get("schema_version"), bool) or instance.get("schema_version") != SCHEMA_VERSION:
        raise CardTimelineError(f"{label}.schema_version: versão suportada é {SCHEMA_VERSION}.")
    instance_id = str(instance.get("instance_id") or "")
    if not _ID_RE.fullmatch(instance_id) or instance_id != expected_id:
        raise CardTimelineError(f"{label}.instance_id: deve coincidir com o ID estável `{expected_id}`.")
    definition_id = str(instance.get("definition_id") or "")
    if definition_id != expected_definition:
        raise CardTimelineError(f"{label}.definition_id: esperado `{expected_definition}`.")
    if isinstance(instance.get("definition_version"), bool) or instance.get("definition_version") != 1:
        raise CardTimelineError(f"{label}.definition_version: versão suportada é 1.")
    origin = str(instance.get("edit_origin") or "")
    if origin not in EDIT_ORIGINS:
        raise CardTimelineError(
            f"{label}.edit_origin: use manual, deterministic_auto ou ai_assisted."
        )
    placement = instance.get("placement")
    if not isinstance(placement, dict):
        raise CardTimelineError(f"{label}.placement: esperado objeto.")
    result = {
        "schema_version": SCHEMA_VERSION,
        "instance_id": instance_id,
        "definition_id": definition_id,
        "definition_version": 1,
        "edit_origin": origin,
        "placement": placement,
    }
    if "central_media" in instance:
        try:
            result["central_media"] = validate_central_media(
                instance["central_media"], label=label + ".central_media",
            )
        except CardMediaError as exc:
            raise CardTimelineError(str(exc)) from exc
    return result


def build_raw_card_instance(
    segment: dict[str, Any], sequence_index: int, *, edit_origin: str = "manual",
) -> dict[str, Any]:
    result = {
        "schema_version": SCHEMA_VERSION,
        "instance_id": str(segment.get("segment_id") or ""),
        "definition_id": f"raw/{segment.get('card_kind') or 'phase'}",
        "definition_version": 1,
        "edit_origin": edit_origin,
        "placement": {
            "timebase": "raw_sequence",
            "sequence_index": sequence_index,
            "duration_sec": float(segment.get("duration_sec") or 0),
        },
    }
    existing = segment.get("card_instance")
    if isinstance(existing, dict) and "central_media" in existing:
        result["central_media"] = existing["central_media"]
    return result


def build_ready_card_instance(
    overlay: dict[str, Any], *, edit_origin: str = "manual",
) -> dict[str, Any]:
    result = {
        "schema_version": SCHEMA_VERSION,
        "instance_id": str(overlay.get("overlay_id") or ""),
        "definition_id": f"ready/{overlay.get('kind') or 'common_card'}",
        "definition_version": 1,
        "edit_origin": edit_origin,
        "placement": {
            "timebase": "ready_video_base",
            "start_sec": float(overlay.get("start_sec") or 0),
            "end_sec": float(overlay.get("end_sec") or 0),
        },
    }
    existing = overlay.get("card_instance")
    if isinstance(existing, dict) and "central_media" in existing:
        result["central_media"] = existing["central_media"]
    return result


def validate_raw_card_instance(
    segment: dict[str, Any], sequence_index: int, *, label: str = "card_instance",
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Valida metadado novo; ausência significa fallback legado sem escrita."""
    if "card_instance" not in segment:
        return None
    expected = build_raw_card_instance(segment, sequence_index)
    result = _common(
        segment["card_instance"], expected_id=expected["instance_id"],
        expected_definition=expected["definition_id"], label=label,
    )
    if "central_media" in result:
        if str(segment.get("card_kind") or "") != "service" or not segment.get("service_key"):
            raise CardTimelineError(f"{label}.central_media: disponível apenas para cards F3/SERVICE.")
        try:
            result["central_media"] = validate_central_media(
                result["central_media"], manifest, label=label + ".central_media",
            )
        except CardMediaError as exc:
            raise CardTimelineError(str(exc)) from exc
    placement = result["placement"]
    unknown = sorted(set(placement) - {"timebase", "sequence_index", "duration_sec"})
    if unknown:
        raise CardTimelineError(f"{label}.placement: campos desconhecidos: {', '.join(unknown)}.")
    if placement.get("timebase") != "raw_sequence":
        raise CardTimelineError(f"{label}.placement.timebase: esperado raw_sequence.")
    index = placement.get("sequence_index")
    if isinstance(index, bool) or not isinstance(index, int) or index != sequence_index:
        raise CardTimelineError(
            f"{label}.placement.sequence_index: deve coincidir com a ordem física {sequence_index}."
        )
    duration = _finite(placement.get("duration_sec"), label + ".placement.duration_sec")
    if duration <= 0 or abs(duration - float(segment.get("duration_sec") or 0)) > 0.000001:
        raise CardTimelineError(
            f"{label}.placement.duration_sec: deve coincidir com duration_sec positivo do segmento."
        )
    result["placement"] = {
        "timebase": "raw_sequence", "sequence_index": index,
        "duration_sec": round(duration, 6),
    }
    return result


def validate_ready_card_instance(
    overlay: dict[str, Any], *, label: str = "card_instance",
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Valida placement no relógio do vídeo-base; overlays legados ficam intactos."""
    if "card_instance" not in overlay:
        return None
    kind = str(overlay.get("kind") or "")
    if kind not in READY_CARD_KINDS:
        raise CardTimelineError(f"{label}: disponível apenas para common_card e service_card.")
    expected = build_ready_card_instance(overlay)
    result = _common(
        overlay["card_instance"], expected_id=expected["instance_id"],
        expected_definition=expected["definition_id"], label=label,
    )
    if "central_media" in result:
        if kind != "service_card" or not overlay.get("service_key"):
            raise CardTimelineError(f"{label}.central_media: disponível apenas para cards F3/SERVICE.")
        try:
            result["central_media"] = validate_central_media(
                result["central_media"], manifest, label=label + ".central_media",
            )
        except CardMediaError as exc:
            raise CardTimelineError(str(exc)) from exc
    placement = result["placement"]
    unknown = sorted(set(placement) - {"timebase", "start_sec", "end_sec"})
    if unknown:
        raise CardTimelineError(f"{label}.placement: campos desconhecidos: {', '.join(unknown)}.")
    if placement.get("timebase") != "ready_video_base":
        raise CardTimelineError(f"{label}.placement.timebase: esperado ready_video_base.")
    start = _finite(placement.get("start_sec"), label + ".placement.start_sec")
    end = _finite(placement.get("end_sec"), label + ".placement.end_sec")
    if end <= start:
        raise CardTimelineError(f"{label}.placement: end_sec deve ser maior que start_sec.")
    if (
        abs(start - float(overlay.get("start_sec") or 0)) > 0.000001
        or abs(end - float(overlay.get("end_sec") or 0)) > 0.000001
    ):
        raise CardTimelineError(
            f"{label}.placement: início/fim devem coincidir com a janela física do overlay."
        )
    result["placement"] = {
        "timebase": "ready_video_base", "start_sec": round(start, 6),
        "end_sec": round(end, 6),
    }
    return result
