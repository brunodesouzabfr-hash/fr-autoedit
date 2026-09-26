"""Contrato e layout determinístico de balões/callouts versionados.

O motor não altera a timeline. Ele valida intenção visual, mede texto com as
fontes distribuídas e deriva posições de render sem persistir coordenadas
transientes no plano do projeto.
"""
from __future__ import annotations

import copy
import math
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
KINDS = frozenset({"balloon", "callout", "lower_third", "caption"})
ROLES = frozenset({"note", "technical", "warning", "caption"})
EASINGS = frozenset({"linear", "ease_out", "ease_in_out"})
POSITIONS = (
    "top_left", "top_right", "bottom_left", "bottom_right",
    "top_center", "bottom_center", "center",
)
_FIELDS = frozenset({
    "schema_version", "role", "priority", "padding", "max_lines",
    "easing", "reduced_motion", "avoid_subtitles", "avoid_subject",
})


class BalloonError(ValueError):
    pass


def _number(value: Any, label: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise BalloonError(f"{label}: informe um número finito, sem aspas.")
    result = float(value)
    if not low <= result <= high:
        raise BalloonError(f"{label}: use um valor entre {low:g} e {high:g}.")
    return result


def validate_balloon(value: Any, kind: str, *, label: str = "balloon") -> tuple[dict[str, Any], list[dict[str, str]]]:
    if kind not in KINDS:
        raise BalloonError(f"{label}: disponível apenas para balloon, callout, lower_third e caption.")
    if not isinstance(value, dict):
        raise BalloonError(f"{label}: esperado objeto.")
    unknown = sorted(set(value) - _FIELDS)
    if unknown:
        raise BalloonError(f"{label}: campos desconhecidos: {', '.join(unknown)}.")
    if isinstance(value.get("schema_version"), bool) or value.get("schema_version") != SCHEMA_VERSION:
        raise BalloonError(f"{label}.schema_version: versão suportada é {SCHEMA_VERSION}.")
    default_role = "caption" if kind == "caption" else "technical" if kind in {"callout", "lower_third"} else "note"
    role = str(value.get("role") or default_role)
    if role not in ROLES:
        raise BalloonError(f"{label}.role: use note, technical, warning ou caption.")
    priority_value = value.get("priority", 80 if kind == "caption" else 50)
    if isinstance(priority_value, bool) or not isinstance(priority_value, int) or not 0 <= priority_value <= 100:
        raise BalloonError(f"{label}.priority: use inteiro entre 0 e 100.")
    padding = _number(value.get("padding", 0.032), label + ".padding", 0.012, 0.08)
    max_lines_value = value.get("max_lines", 2 if kind == "caption" else 4)
    if isinstance(max_lines_value, bool) or not isinstance(max_lines_value, int) or not 1 <= max_lines_value <= 6:
        raise BalloonError(f"{label}.max_lines: use inteiro entre 1 e 6.")
    easing = str(value.get("easing") or "ease_out")
    if easing not in EASINGS:
        raise BalloonError(f"{label}.easing: use linear, ease_out ou ease_in_out.")
    result = {
        "schema_version": SCHEMA_VERSION,
        "role": role,
        "priority": priority_value,
        "padding": round(padding, 6),
        "max_lines": max_lines_value,
        "easing": easing,
    }
    for field, default in (
        ("reduced_motion", False), ("avoid_subtitles", True), ("avoid_subject", False),
    ):
        item = value.get(field, default)
        if not isinstance(item, bool):
            raise BalloonError(f"{label}.{field}: use true ou false.")
        result[field] = item
    notices: list[dict[str, str]] = []
    if result["avoid_subject"]:
        notices.append({
            "level": "warning", "block": label + ".avoid_subject",
            "message": "Não há máscara de sujeito confiável neste projeto.",
            "effect": "O motor evita o centro por heurística e exige revisão visual; não promete detecção de sujeito.",
        })
    return result, notices


def measure_balloon(overlay: dict[str, Any], size: tuple[int, int], app_root: Path) -> dict[str, Any]:
    """Mede a menor caixa legível dentro do limite do formato."""
    from PIL import Image, ImageDraw
    from fr_v4.core.grid import Box
    from fr_v4.core.typography import load_font, measure

    width, height = map(int, size)
    if min(width, height) < 240:
        raise BalloonError("Balão exige canvas de ao menos 240 px.")
    kind = str(overlay.get("kind") or "")
    spec, _ = validate_balloon(overlay.get("balloon"), kind)
    scale = min(width, height) / 1080
    portrait = height / width >= 1.25
    landscape = width / height >= 1.25
    width_ratio = 0.80 if portrait else 0.56 if landscape else 0.72
    if kind in {"caption", "lower_third"}:
        width_ratio = 0.86 if not landscape else 0.70
    maximum_width = max(180, round(width * width_ratio))
    padding = max(8, round(min(width, height) * spec["padding"]))
    tag_height = 0 if kind == "caption" else max(16, round(38 * scale))
    maximum = max(12, round((34 if kind == "caption" else 42) * scale))
    minimum = max(9, round((21 if kind == "caption" else 23) * scale))
    role = "technical" if kind == "caption" else "body"
    scratch = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(scratch, "RGBA")
    available_height = max(40, round(height * (0.24 if kind == "caption" else 0.34)) - 2 * padding - tag_height)
    layout = measure(
        draw, str(overlay.get("text") or ""),
        Box(0, 0, maximum_width - 2 * padding, available_height),
        app_root / "assets/fonts", role, "F5", maximum, minimum, spec["max_lines"],
    )
    font = load_font(str(app_root / "assets/fonts"), role, layout.size, "F5")
    line_widths = [round(draw.textlength(line, font=font)) for line in layout.lines]
    text_width = max(line_widths, default=0)
    layer_width = min(maximum_width, max(round(width * 0.28), text_width + 2 * padding))
    layer_height = max(
        round(min(width, height) * 0.10),
        2 * padding + tag_height + layout.line_height * len(layout.lines),
    )
    scratch.close()
    return {
        "width": layer_width, "height": layer_height, "padding": padding,
        "tag_height": tag_height, "lines": layout.lines, "font_size": layout.size,
        "line_height": layout.line_height, "font_role": role,
    }


def _safe_margin(overlay: dict[str, Any], width: int, height: int) -> int:
    safe = overlay.get("safe_area", "auto")
    if isinstance(safe, dict):
        values = [float(safe.get(side, 0)) for side in ("top", "right", "bottom", "left")]
        return max(0, round(max(values) * min(width, height)))
    return {
        "none": 0, "action_safe": round(min(width, height) * 0.05),
        "title_safe": round(min(width, height) * 0.10),
        "auto": round(min(width, height) * 0.07),
    }.get(str(safe), round(min(width, height) * 0.07))


def _legacy_size(overlay: dict[str, Any], size: tuple[int, int]) -> tuple[int, int]:
    width, height = size
    kind = str(overlay.get("kind") or "")
    scale = min(width, height) / 1080
    if kind in {"caption", "lower_third"}:
        return round(width * .86), max(round(height * .16), round(108 * scale))
    return round(width * .72), max(round(height * .22), round(160 * scale))


def _box(position: str, layer: tuple[int, int], canvas: tuple[int, int], margin: int) -> tuple[int, int, int, int]:
    width, height = canvas
    layer_w, layer_h = layer
    points = {
        "top_left": (margin, margin),
        "top_center": ((width - layer_w) // 2, margin),
        "top_right": (width - layer_w - margin, margin),
        "center": ((width - layer_w) // 2, (height - layer_h) // 2),
        "bottom_left": (margin, height - layer_h - margin),
        "bottom_center": ((width - layer_w) // 2, height - layer_h - margin),
        "bottom_right": (width - layer_w - margin, height - layer_h - margin),
    }
    x, y = points.get(position, points["bottom_left"])
    return x, y, x + layer_w, y + layer_h


def _intersects(first: tuple[int, int, int, int], second: tuple[int, int, int, int]) -> bool:
    return first[0] < second[2] and first[2] > second[0] and first[1] < second[3] and first[3] > second[1]


def _time_overlap(first: dict[str, Any], second: dict[str, Any]) -> bool:
    return float(first["start_sec"]) < float(second["end_sec"]) and float(first["end_sec"]) > float(second["start_sec"])


def resolve_collisions(
    overlays: list[dict[str, Any]], size: tuple[int, int], app_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Deriva posições sem gravá-las no plano e torna conflitos auditáveis."""
    resolved = copy.deepcopy(overlays)
    width, height = size
    notices: list[dict[str, str]] = []
    reservations: list[tuple[dict[str, Any], tuple[int, int, int, int]]] = []

    # Legendas e overlays legados são âncoras fixas: preservar seu renderer e
    # sua posição tem precedência sobre mover um balão versionado.
    for item in resolved:
        kind = str(item.get("kind") or "")
        if kind not in KINDS or ("balloon" in item and kind not in {"caption", "lower_third"}):
            continue
        layer_size = (
            (measure_balloon(item, size, app_root)["width"], measure_balloon(item, size, app_root)["height"])
            if "balloon" in item else _legacy_size(item, size)
        )
        position = str(item.get("position") or ("bottom_center" if kind in {"caption", "lower_third"} else "bottom_left"))
        reservations.append((item, _box(position, layer_size, size, _safe_margin(item, width, height))))

    movable = [
        item for item in resolved
        if item.get("kind") in {"balloon", "callout"} and isinstance(item.get("balloon"), dict)
    ]
    movable.sort(key=lambda item: (-int(item["balloon"]["priority"]), str(item.get("overlay_id") or "")))
    for item in movable:
        metrics = measure_balloon(item, size, app_root)
        layer_size = (metrics["width"], metrics["height"])
        requested = str(item.get("position") or "bottom_left")
        candidates = [requested] + [position for position in POSITIONS if position != requested]
        if item["balloon"].get("avoid_subject"):
            candidates = [position for position in candidates if position != "center"] + ["center"]
        margin = _safe_margin(item, width, height)
        chosen = ""
        chosen_box = None
        for position in candidates:
            candidate_box = _box(position, layer_size, size, margin)
            if all(
                not (_time_overlap(item, other) and _intersects(candidate_box, occupied))
                for other, occupied in reservations
            ):
                chosen, chosen_box = position, candidate_box
                break
        if not chosen:
            chosen, chosen_box = requested, _box(requested, layer_size, size, margin)
            item["_layout_review_required"] = True
            notices.append({
                "level": "warning", "block": f"overlays.{item.get('overlay_id')}.layout",
                "message": "Nenhuma região livre comporta o balão durante toda a janela.",
                "effect": "Prévia sinaliza revisão; o master é bloqueado para não cobrir conteúdo silenciosamente.",
            })
        elif chosen != requested:
            notices.append({
                "level": "info", "block": f"overlays.{item.get('overlay_id')}.layout",
                "message": f"Posição resolvida de {requested} para {chosen} por colisão temporal.",
                "effect": "Texto, timing e prioridade foram preservados; somente a posição derivada mudou.",
            })
        item["_resolved_position"] = chosen
        item["_layout_bbox"] = list(chosen_box)
        reservations.append((item, chosen_box))
    return resolved, notices
