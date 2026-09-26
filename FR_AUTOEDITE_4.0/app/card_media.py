"""Contrato e composição da mídia central de cards F3/SERVICE.

O contrato referencia somente IDs do manifesto do projeto.  A geometria é
deliberadamente pequena: crop quadrado, máscara circular, zoom e ponto focal.
Não há Data URL nem caminho fornecido pelo cliente do Studio.
"""
from __future__ import annotations

import math
import re
from typing import Any


SCHEMA_VERSION = 1
SHAPE = "circle"
CROP = "1:1"
MIN_ZOOM = 1.0
MAX_ZOOM = 4.0
_ASSET_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
_FIELDS = frozenset({
    "schema_version", "central_asset_id", "shape", "crop", "zoom",
    "focal_x", "focal_y", "frame_time_sec",
})


class CardMediaError(ValueError):
    pass


def _finite(value: Any, label: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise CardMediaError(f"{label}: informe um número finito, sem aspas.")
    number = float(value)
    if not low <= number <= high:
        raise CardMediaError(f"{label}: use um valor entre {low:g} e {high:g}.")
    return number


def build_central_media(
    central_asset_id: str, *, zoom: float = 1.0, focal_x: float = 0.5,
    focal_y: float = 0.5, frame_time_sec: float = 0.0,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "central_asset_id": central_asset_id,
        "shape": SHAPE,
        "crop": CROP,
        "zoom": zoom,
        "focal_x": focal_x,
        "focal_y": focal_y,
        "frame_time_sec": frame_time_sec,
    }


def validate_central_media(
    value: Any, manifest: dict[str, Any] | None = None, *, label: str = "central_media",
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CardMediaError(f"{label}: esperado objeto.")
    unknown = sorted(set(value) - _FIELDS)
    if unknown:
        raise CardMediaError(f"{label}: campos desconhecidos: {', '.join(unknown)}.")
    if isinstance(value.get("schema_version"), bool) or value.get("schema_version") != SCHEMA_VERSION:
        raise CardMediaError(f"{label}.schema_version: versão suportada é {SCHEMA_VERSION}.")
    asset_id = value.get("central_asset_id")
    if not isinstance(asset_id, str) or not _ASSET_ID.fullmatch(asset_id):
        raise CardMediaError(f"{label}.central_asset_id: ID inválido.")
    if value.get("shape") != SHAPE:
        raise CardMediaError(f"{label}.shape: cards F3/SERVICE exigem circle.")
    if value.get("crop") != CROP:
        raise CardMediaError(f"{label}.crop: cards F3/SERVICE exigem crop 1:1.")
    zoom = _finite(value.get("zoom"), label + ".zoom", MIN_ZOOM, MAX_ZOOM)
    focal_x = _finite(value.get("focal_x"), label + ".focal_x", 0.0, 1.0)
    focal_y = _finite(value.get("focal_y"), label + ".focal_y", 0.0, 1.0)
    frame_time = _finite(value.get("frame_time_sec", 0.0), label + ".frame_time_sec", 0.0, 21600.0)
    if manifest is not None:
        row = next(
            (
                item for item in manifest.get("media", [])
                if isinstance(item, dict) and item.get("id") == asset_id
                and item.get("status", "ok") == "ok"
            ),
            None,
        )
        if row is None:
            raise CardMediaError(
                f"{label}.central_asset_id: `{asset_id}` não pertence ao manifesto corrente."
            )
        if row.get("media_type") not in {"image", "video"}:
            raise CardMediaError(f"{label}.central_asset_id: mídia deve ser image ou video.")
        duration = float(row.get("duration_sec") or 0)
        if row.get("media_type") == "video" and (duration <= 0 or frame_time > duration + 0.0005):
            raise CardMediaError(
                f"{label}.frame_time_sec: {frame_time:.3f}s excede a mídia de {duration:.3f}s."
            )
    return build_central_media(
        asset_id, zoom=round(zoom, 6), focal_x=round(focal_x, 6),
        focal_y=round(focal_y, 6), frame_time_sec=round(frame_time, 6),
    )


def circle_crop(source, size: int, *, zoom: float, focal_x: float, focal_y: float):
    """Retorna RGBA quadrado/circular sem redimensionamento anisotrópico."""
    from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

    if size < 8:
        raise CardMediaError("circle_crop: diâmetro mínimo é 8 px.")
    zoom = _finite(zoom, "central_media.zoom", MIN_ZOOM, MAX_ZOOM)
    focal_x = _finite(focal_x, "central_media.focal_x", 0.0, 1.0)
    focal_y = _finite(focal_y, "central_media.focal_y", 0.0, 1.0)
    image = ImageOps.exif_transpose(source).convert("RGBA")
    width, height = image.size
    crop_side = max(1.0, min(width, height) / zoom)
    center_x = crop_side / 2 + focal_x * max(0.0, width - crop_side)
    center_y = crop_side / 2 + focal_y * max(0.0, height - crop_side)
    left = max(0.0, min(width - crop_side, center_x - crop_side / 2))
    top = max(0.0, min(height - crop_side, center_y - crop_side / 2))
    square = image.crop((left, top, left + crop_side, top + crop_side))
    square = square.resize((size, size), Image.Resampling.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    inset = max(1, size // 160)
    ImageDraw.Draw(mask).ellipse((inset, inset, size - inset - 1, size - inset - 1), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(max(0.6, size / 420)))
    square.putalpha(ImageChops.multiply(square.getchannel("A"), mask))
    return square
