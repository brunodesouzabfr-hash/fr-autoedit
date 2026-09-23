"""Overlays quiet luxury medidos, sem truncamento silencioso."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .core.config import TOKENS, palette_rgba
from .core.grid import Box
from .core.typography import draw_text
from .diagrams import render as render_diagram


KINDS = frozenset({"service_card", "common_card", "balloon", "callout", "lower_third", "caption", "logo"})


def render_overlay(overlay: dict[str, Any], size: tuple[int, int], app_root: Path):
    from PIL import Image, ImageDraw

    kind = str(overlay.get("kind") or "")
    if kind not in KINDS:
        raise ValueError(f"Overlay desconhecido: {kind}")
    width, height = size
    if min(width, height) < 240:
        raise ValueError("Overlay exige canvas de ao menos 240 px.")
    u = min(width, height) / 1080
    full = str(overlay.get("presentation") or "overlay") == "full_frame"
    if full:
        layer_w, layer_h = width, height
    elif kind in {"caption", "lower_third"}:
        layer_w, layer_h = round(width * .86), max(round(height * .16), round(108 * u))
    elif kind in {"balloon", "callout"}:
        layer_w, layer_h = round(width * .72), max(round(height * .22), round(160 * u))
    else:
        layer_w, layer_h = round(width * .78), max(round(height * .30), round(230 * u))
    image = Image.new("RGBA", (layer_w, layer_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    radius = max(8, round(22 * u))
    stroke = max(1, round(2 * u))
    draw.rounded_rectangle((1, 1, layer_w - 2, layer_h - 2), radius=radius,
                           fill=palette_rgba("ink", 222), outline=palette_rgba("gold", 156), width=stroke)
    draw.line((round(24*u), round(15*u), layer_w-round(24*u), round(15*u)),
              fill=palette_rgba("gold", 140), width=max(1, round(u)))
    draw.line((round(24*u), round(15*u), round(124*u), round(15*u)),
              fill=TOKENS["orange"], width=max(2, round(3*u)))
    service = str(overlay.get("service_key") or "")
    if service:
        motif = render_diagram(service, (layer_w, layer_h), .11)
        image.alpha_composite(motif)
        motif.close()
    fonts = app_root / "assets/fonts"
    tag = "LEGENDA" if kind == "caption" else ("FR / NOTA" if width < 640 else "FR / NOTA DE PROCESSO")
    if kind != "caption":
        tag_max = max(8, round(23*u)); tag_min = max(6, min(tag_max, round(18*u)))
        tag_x = round(24*u)
        tag_y = max(4, round(16*u)); tag_h = max(14, round(40*u))
        draw_text(draw, tag, Box(tag_x, tag_y, layer_w-tag_x-round(24*u), tag_h),
                  fonts, "technical", "F5", TOKENS["gold"], tag_max, tag_min, 1)
    else:
        tag_y = 0; tag_h = 0
    start_y = max(6, round(24*u)) if kind == "caption" else max(tag_y+tag_h+2, round(72*u))
    body_max = max(10, round(40*u)); body_min = max(7, min(body_max, round(24*u)))
    body_box = Box(round(24*u), start_y, layer_w-round(48*u), layer_h-start_y-round(20*u))
    draw_text(draw, str(overlay.get("text") or ""), body_box, fonts,
              "body" if kind != "caption" else "technical", "F5", TOKENS["bone"],
              body_max, body_min, 4 if kind != "caption" else 2, "center" if kind == "caption" else "left")
    return image

