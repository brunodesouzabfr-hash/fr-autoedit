"""Overlays quiet luxury medidos, sem truncamento silencioso."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .core.config import TOKENS, palette_rgba
from .core.grid import Box
from .core.typography import draw_text
from .diagrams import render as render_diagram


KINDS = frozenset({"service_card", "common_card", "balloon", "callout", "lower_third", "caption", "logo"})


def _render_versioned_balloon(overlay: dict[str, Any], size: tuple[int, int], app_root: Path):
    """Render responsivo; o caminho sem `balloon` abaixo permanece legado."""
    from PIL import Image, ImageDraw

    from balloon_engine import measure_balloon, validate_balloon
    from .core.typography import load_font

    kind = str(overlay.get("kind") or "")
    spec, _ = validate_balloon(overlay.get("balloon"), kind)
    metrics = measure_balloon(overlay, size, app_root)
    width, height = metrics["width"], metrics["height"]
    padding = metrics["padding"]
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    radius = max(8, round(min(width, height) * .10))

    # Fundo leve e grid discreto: estrutura sem painel opaco pesado.
    draw.rounded_rectangle(
        (1, 1, width - 2, height - 2), radius=radius,
        fill=palette_rgba("ink", 174), outline=palette_rgba("gold", 112), width=max(1, round(min(size) / 720)),
    )
    for index in range(1, 6):
        x = round(width * index / 6)
        draw.line((x, padding, x, height - padding), fill=palette_rgba("tech", 22), width=1)

    # Traço superior perde opacidade até desaparecer, evitando uma moldura pesada.
    line_y = max(2, round(min(size) / 180))
    start_x, end_x = padding, width - padding
    span = max(1, end_x - start_x)
    for x in range(start_x, end_x):
        progress = (x - start_x) / span
        alpha = round(170 * (1 - progress) ** 1.7)
        color = TOKENS["orange"] if progress < .18 else TOKENS["gold"]
        rgb = tuple(int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        draw.point((x, line_y), fill=(*rgb, alpha))

    labels = {
        "note": "FR / NOTA", "technical": "FR / NOTA TÉCNICA",
        "warning": "FR / REVISÃO", "caption": "LEGENDA",
    }
    if metrics["tag_height"]:
        tag_font = load_font(
            str(app_root / "assets/fonts"), "technical",
            max(8, round(metrics["font_size"] * .58)), "F5",
        )
        draw.text((padding, padding), labels[spec["role"]], font=tag_font, fill=TOKENS["gold"], anchor="lt")
    font = load_font(
        str(app_root / "assets/fonts"), metrics["font_role"], metrics["font_size"], "F5",
    )
    y = padding + metrics["tag_height"]
    for line in metrics["lines"]:
        x = padding
        if kind == "caption":
            x += round((width - 2 * padding - draw.textlength(line, font=font)) / 2)
        draw.text((x, y), line, font=font, fill=TOKENS["bone"], anchor="lt")
        y += metrics["line_height"]
    return image


def render_overlay(overlay: dict[str, Any], size: tuple[int, int], app_root: Path):
    from PIL import Image, ImageDraw

    kind = str(overlay.get("kind") or "")
    if kind not in KINDS:
        raise ValueError(f"Overlay desconhecido: {kind}")
    width, height = size
    if min(width, height) < 240:
        raise ValueError("Overlay exige canvas de ao menos 240 px.")
    if kind in {"balloon", "callout", "lower_third", "caption"} and "balloon" in overlay:
        return _render_versioned_balloon(overlay, size, app_root)
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
