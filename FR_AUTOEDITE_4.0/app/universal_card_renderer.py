"""Renderer determinístico do contrato ``fr-universal-card``.

O módulo reproduz, em Pillow e sem navegador, a ordem de composição do
``exportPNG()`` do FR Card Editor 1.1. Ele é deliberadamente independente do
renderer legado F1--F6, do Studio, da timeline e de persistência.

Paths nunca fazem parte de CardDefinition/CardInstance. O chamador fornece
bindings internos de ``asset_id`` para arquivos, e cada arquivo é conferido
contra o SHA-256 já validado no catálogo. Fontes seguem o mesmo princípio e
somente os binários congelados em M9.0 são aceitos.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from io import BytesIO
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from card_state_v2 import (
    RENDERER_ID,
    validate_card_definition_v2,
    validate_card_instance_v2,
)


APP_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ROOT = APP_ROOT / "contracts" / "m9"
FONT_CONTRACT_PATH = CONTRACT_ROOT / "font_sources_v1.json"
RENDERER_VERSION = "1.0.0"
LOGICAL_WIDTH = 941
LOGICAL_HEIGHT = 1672
BACKGROUND_FALLBACK = "#0a2f26"
VISUAL_BOX = (160.0, 508.0, 623.0, 863.0)
METALLIC_STOPS = (
    (0.0, "#5b3309"),
    (0.10, "#b97719"),
    (0.22, "#ffe09a"),
    (0.36, "#c78828"),
    (0.49, "#fff0b5"),
    (0.64, "#a76410"),
    (0.78, "#f5c568"),
    (1.0, "#70400a"),
)
_PNG_SAVE_OPTIONS = {"format": "PNG", "compress_level": 9, "optimize": False}


class UniversalCardRenderError(ValueError):
    """Falha fechada antes de produzir um frame universal."""


@dataclass(frozen=True)
class UniversalCardRenderResult:
    """PNG e relatório verificável produzidos pela mesma execução."""

    png_bytes: bytes
    sha256: str
    width: int
    height: int
    renderer_id: str
    renderer_version: str
    state_digest: str
    report: dict[str, Any]


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UniversalCardRenderError(f"{label} indisponível ou inválido: {path.name}.") from exc
    if not isinstance(value, dict):
        raise UniversalCardRenderError(f"{label} deve ser objeto JSON.")
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise UniversalCardRenderError(f"Não foi possível ler o arquivo validado: {path.name}.") from exc
    return digest.hexdigest()


def _positive_dimension(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise UniversalCardRenderError(f"{label} deve ser inteiro positivo.")
    return value


def _hex_color(value: str) -> tuple[int, int, int]:
    return tuple(int(value[index:index + 2], 16) for index in (1, 3, 5))


def _rgba(value: str, alpha: int = 255) -> tuple[int, int, int, int]:
    return _hex_color(value) + (max(0, min(255, int(alpha))),)


def _resampling() -> Image.Resampling:
    return Image.Resampling.LANCZOS


class _AssetResolver:
    def __init__(
        self,
        catalog: Mapping[str, Mapping[str, Any]],
        sources: Mapping[str, str | Path],
        usage_context: str | None,
    ) -> None:
        if not isinstance(catalog, Mapping):
            raise UniversalCardRenderError("Catálogo confiável de assets não informado.")
        if not isinstance(sources, Mapping):
            raise UniversalCardRenderError("Bindings internos de assets não informados.")
        self.catalog = catalog
        self.sources = sources
        self.usage_context = usage_context
        self._cache: dict[str, Image.Image] = {}
        self.used: list[str] = []
        self.reviews: list[dict[str, Any]] = []
        self.warnings: list[str] = []

    def resolve(self, reference: Mapping[str, Any], label: str) -> Image.Image:
        asset_id = str(reference["asset_id"])
        catalog_row = self.catalog.get(asset_id)
        if not isinstance(catalog_row, Mapping):
            raise UniversalCardRenderError(f"{label}: asset inexistente no catálogo: {asset_id}.")
        if catalog_row.get("scope") != reference.get("scope"):
            raise UniversalCardRenderError(f"{label}: scope diverge do catálogo para {asset_id}.")
        expected = reference.get("sha256")
        if catalog_row.get("sha256") != expected:
            raise UniversalCardRenderError(f"{label}: hash diverge do catálogo para {asset_id}.")
        if reference.get("scope") == "service_catalog":
            # Gate no próprio renderer: um chamador não pode contornar o
            # resolver M9.4 passando diretamente um path/AssetRef SERVICE.
            from service_catalog_v2 import validate_renderer_service_asset

            try:
                review = validate_renderer_service_asset(
                    catalog_row, asset_id, self.usage_context,
                )
            except ValueError as exc:
                raise UniversalCardRenderError(str(exc)) from exc
            if review not in self.reviews:
                self.reviews.append(review)
                service_key = review["service_key"]
                self.warnings.append(
                    f"SERVICE {service_key}: revisão visual obrigatória; "
                    f"publicavel=false; uso restrito a {review['usage_context']}."
                )
                if review["opaque_background_preserved"]:
                    self.warnings.append(
                        f"SERVICE {service_key}: fundo opaco preservado; "
                        "não remover nem mascarar sem nova revisão."
                    )
        raw_source = self.sources.get(asset_id)
        if not isinstance(raw_source, (str, Path)):
            raise UniversalCardRenderError(f"{label}: arquivo ausente para asset {asset_id}.")
        source = Path(raw_source).expanduser()
        if not source.is_file():
            raise UniversalCardRenderError(f"{label}: arquivo ausente para asset {asset_id}.")
        if _sha256_file(source) != expected:
            raise UniversalCardRenderError(f"{label}: SHA-256 do arquivo diverge para {asset_id}.")
        if asset_id not in self._cache:
            try:
                with Image.open(source) as opened:
                    opened.load()
                    image = opened.convert("RGBA")
            except (OSError, ValueError) as exc:
                raise UniversalCardRenderError(
                    f"{label}: asset não é imagem decodificável: {asset_id}."
                ) from exc
            self._cache[asset_id] = image
        if asset_id not in self.used:
            self.used.append(asset_id)
        return self._cache[asset_id].copy()


class _FontRegistry:
    _VARIABLE_NAMES = {
        400: "Regular",
        500: "Medium",
        600: "SemiBold",
        700: "Bold",
    }

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self.contract = _load_json(FONT_CONTRACT_PATH, "Contrato de fontes M9.0")
        self.rows: dict[str, list[dict[str, Any]]] = {}
        self.paths: dict[str, Path] = {}
        self._cache: dict[tuple[str, int, int], ImageFont.FreeTypeFont] = {}
        self.used: list[dict[str, Any]] = []
        if not self.root.is_dir():
            raise UniversalCardRenderError("Diretório das fontes fixadas M9.0 está ausente.")
        for raw in self.contract.get("fonts", []):
            if not isinstance(raw, dict):
                raise UniversalCardRenderError("Contrato de fontes M9.0 contém entrada inválida.")
            row = dict(raw)
            filename = row.get("file")
            family = row.get("family")
            expected = row.get("sha256")
            if not all(isinstance(item, str) and item for item in (filename, family, expected)):
                raise UniversalCardRenderError("Contrato de fontes M9.0 está incompleto.")
            path = (self.root / filename).resolve()
            try:
                path.relative_to(self.root)
            except ValueError as exc:
                raise UniversalCardRenderError("Fonte M9.0 tenta escapar do diretório autorizado.") from exc
            if not path.is_file():
                raise UniversalCardRenderError(f"Fonte fixada ausente: {filename}.")
            if _sha256_file(path) != expected:
                raise UniversalCardRenderError(f"SHA-256 divergente na fonte fixada: {filename}.")
            self.rows.setdefault(family, []).append(row)
            self.paths[filename] = path

    @staticmethod
    def _weight_range(value: Any) -> tuple[int, int]:
        if not isinstance(value, str):
            raise UniversalCardRenderError("Peso de fonte inválido no contrato M9.0.")
        parts = value.split()
        try:
            numbers = [int(item) for item in parts]
        except ValueError as exc:
            raise UniversalCardRenderError("Peso de fonte inválido no contrato M9.0.") from exc
        if len(numbers) == 1:
            return numbers[0], numbers[0]
        if len(numbers) == 2:
            return numbers[0], numbers[1]
        raise UniversalCardRenderError("Faixa de peso inválida no contrato M9.0.")

    def _select(self, family: str, weight: int) -> dict[str, Any]:
        rows = self.rows.get(family, [])
        candidates = [row for row in rows if self._weight_range(row["weight"])[0] <= weight <= self._weight_range(row["weight"])[1]]
        if not candidates:
            raise UniversalCardRenderError(
                f"Fonte/peso não registrado no conjunto fixado M9.0: {family} {weight}."
            )
        exact = [row for row in candidates if self._weight_range(row["weight"]) == (weight, weight)]
        return exact[0] if exact else candidates[0]

    def font(self, family: str, weight: int, pixel_size: float) -> ImageFont.FreeTypeFont:
        row = self._select(family, weight)
        size = max(1, int(round(pixel_size)))
        key = (str(row["file"]), weight, size)
        if key not in self._cache:
            try:
                font = ImageFont.truetype(str(self.paths[str(row["file"])]), size=size)
                low, high = self._weight_range(row["weight"])
                if low != high:
                    font.set_variation_by_name(self._VARIABLE_NAMES[weight])
            except (OSError, KeyError, ValueError) as exc:
                raise UniversalCardRenderError(
                    f"Não foi possível carregar a fonte fixada {family} {weight}."
                ) from exc
            self._cache[key] = font
        usage = {
            "family": family,
            "weight": weight,
            "file": row["file"],
            "sha256": row["sha256"],
        }
        if usage not in self.used:
            self.used.append(usage)
        return self._cache[key]


def _validate_output_size(definition: Mapping[str, Any], output_size: tuple[int, int] | None) -> tuple[int, int]:
    canvas = definition["canvas"]
    allowed = {tuple(item) for item in canvas["export_resolutions"]}
    if output_size is None:
        result = (int(canvas["width"]), int(canvas["height"]))
    else:
        if not isinstance(output_size, tuple) or len(output_size) != 2:
            raise UniversalCardRenderError("output_size deve ser uma tupla (largura, altura).")
        result = (
            _positive_dimension(output_size[0], "output_size.width"),
            _positive_dimension(output_size[1], "output_size.height"),
        )
    if result not in allowed:
        raise UniversalCardRenderError(
            f"Resolução {result[0]}x{result[1]} não pertence ao contrato 9:16 congelado."
        )
    return result


def _paste_rgba(base: Image.Image, overlay: Image.Image, position: tuple[int, int] = (0, 0)) -> None:
    base.alpha_composite(overlay, dest=position)


def _opacity(image: Image.Image, amount: float) -> Image.Image:
    result = image.copy()
    alpha = result.getchannel("A").point(lambda value: int(round(value * amount)))
    result.putalpha(alpha)
    return result


def _visual_geometry(assets: Mapping[str, Any]) -> tuple[float, float, float, float]:
    shape = assets["visualShape"]
    if shape == "full":
        return VISUAL_BOX
    size = float(assets["visualSize"])
    return ((LOGICAL_WIDTH - size) / 2.0, 508.0 + (863.0 - size) / 2.0, size, size)


def _shape_mask(size: tuple[int, int], shape: str, sx: float, sy: float) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    box = (0, 0, max(0, size[0] - 1), max(0, size[1] - 1))
    if shape == "circle":
        draw.ellipse(box, fill=255)
    elif shape == "rounded":
        radius = max(1, int(round(42.0 * min(sx, sy))))
        draw.rounded_rectangle(box, radius=radius, fill=255)
    else:
        draw.rectangle(box, fill=255)
    return mask


def _draw_visual(
    canvas: Image.Image,
    visual: Image.Image,
    assets: Mapping[str, Any],
    sx: float,
    sy: float,
) -> dict[str, Any]:
    fx, fy, fw, fh = _visual_geometry(assets)
    shape = str(assets["visualShape"])
    zoom = float(assets["visualZoom"])
    scale = max(fw / visual.width, fh / visual.height) * zoom
    dw = visual.width * scale
    dh = visual.height * scale
    dx = fx + (fw - dw) * float(assets["visualFocalX"]) / 100.0
    dy = fy + (fh - dh) * float(assets["visualFocalY"]) / 100.0

    target_box = (
        int(round(fx * sx)),
        int(round(fy * sy)),
        max(1, int(round(fw * sx))),
        max(1, int(round(fh * sy))),
    )
    resized_size = (
        max(1, int(round(dw * sx))),
        max(1, int(round(dh * sy))),
    )
    resized = visual.resize(resized_size, _resampling())
    local = Image.new("RGBA", (target_box[2], target_box[3]), (0, 0, 0, 0))
    local.alpha_composite(
        resized,
        dest=(int(round((dx - fx) * sx)), int(round((dy - fy) * sy))),
    )
    local.putalpha(ImageChops.multiply(local.getchannel("A"), _shape_mask(local.size, shape, sx, sy)))
    local = _opacity(local, float(assets["visualOpacity"]))
    _paste_rgba(canvas, local, (target_box[0], target_box[1]))

    if shape != "full":
        border = Image.new("RGBA", local.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(border)
        width = max(1, int(round(min(sx, sy))))
        box = (0, 0, local.width - 1, local.height - 1)
        color = (214, 166, 75, int(round(255 * 0.28)))
        if shape == "circle":
            draw.ellipse(box, outline=color, width=width)
        elif shape == "rounded":
            draw.rounded_rectangle(
                box,
                radius=max(1, int(round(42.0 * min(sx, sy)))),
                outline=color,
                width=width,
            )
        else:
            draw.rectangle(box, outline=color, width=width)
        _paste_rgba(canvas, border, (target_box[0], target_box[1]))

    return {
        "shape": shape,
        "logical_box": [fx, fy, fw, fh],
        "crop": "1:1" if shape != "full" else "623:863",
        "perfect_circle": shape == "circle" and fw == fh,
        "zoom": zoom,
        "focal_point": [assets["visualFocalX"], assets["visualFocalY"]],
        "opacity": assets["visualOpacity"],
    }


def _quadratic_points(
    x1: float, y1: float, cx: float, cy: float, x2: float, y2: float, count: int,
) -> list[tuple[float, float]]:
    result = []
    for index in range(count + 1):
        t = index / count
        inverse = 1.0 - t
        result.append((
            inverse * inverse * x1 + 2 * inverse * t * cx + t * t * x2,
            inverse * inverse * y1 + 2 * inverse * t * cy + t * t * y2,
        ))
    return result


def _fade_at(position: float) -> float:
    if position <= 0.13:
        return position / 0.13
    if position >= 0.87:
        return (1.0 - position) / 0.13
    return 1.0


def _draw_grid(
    canvas: Image.Image, state: Mapping[str, Any], sx: float, sy: float,
) -> tuple[list[str], list[str]]:
    visible = [line for line in state["lines"] if line["visible"]]
    rendered: list[str] = []
    hidden = [line["id"] for line in state["lines"] if not line["visible"]]
    grid_alpha = float(state["gridStyle"]["opacity"])
    for index, line in enumerate(visible):
        horizontal = abs(line["x2"] - line["x1"]) >= abs(line["y2"] - line["y1"])
        midpoint_x = (line["x1"] + line["x2"]) / 2.0
        midpoint_y = (line["y1"] + line["y2"]) / 2.0
        bend = ((index % 3) - 1) * 0.32
        control_x = midpoint_x if horizontal else midpoint_x + bend
        control_y = midpoint_y + bend if horizontal else midpoint_y
        span = math.hypot(line["x2"] - line["x1"], line["y2"] - line["y1"])
        samples = max(16, min(512, int(math.ceil(span * max(sx, sy) / 3.0))))
        logical = _quadratic_points(
            line["x1"], line["y1"], control_x, control_y,
            line["x2"], line["y2"], samples,
        )
        points = [(int(round(x * sx)), int(round(y * sy))) for x, y in logical]
        width = max(1, int(round(float(line["width"]) * (sx + sy) / 2.0)))
        base_alpha = grid_alpha * float(line.get("opacity", 1.0))
        color = _hex_color(line["color"])
        overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        fading = line.get("fade", True) is not False
        for segment in range(samples):
            factor = _fade_at((segment + 0.5) / samples) if fading else 1.0
            alpha = int(round(255 * base_alpha * max(0.0, min(1.0, factor))))
            draw.line((points[segment], points[segment + 1]), fill=color + (alpha,), width=width)
        if not fading and points:
            radius = width / 2.0
            for point in (points[0], points[-1]):
                draw.ellipse(
                    (point[0] - radius, point[1] - radius, point[0] + radius, point[1] + radius),
                    fill=color + (int(round(255 * base_alpha)),),
                )
        _paste_rgba(canvas, overlay)
        rendered.append(str(line["id"]))
    return rendered, hidden


def _logo_alpha(image: Image.Image) -> Image.Image:
    red, green, blue, alpha = image.convert("RGBA").split()
    luminance = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    factor = luminance.point(
        lambda value: max(0, min(255, int(round(max(0.0, (value - 5) / 80.0) * 255))))
    )
    result = image.convert("RGBA")
    result.putalpha(ImageChops.multiply(alpha, factor))
    return result


def _draw_logo(canvas: Image.Image, logo: Image.Image, sx: float, sy: float) -> None:
    processed = _logo_alpha(logo)
    size = (max(1, int(round(87 * sx))), max(1, int(round(87 * sy))))
    processed = processed.resize(size, _resampling())
    _paste_rgba(canvas, processed, (int(round(368 * sx)), int(round(72 * sy))))


def _wrap_lines(font: ImageFont.FreeTypeFont, text: str, maximum: float) -> list[str]:
    output: list[str] = []
    for paragraph in text.split("\n"):
        if paragraph == "":
            output.append("")
            continue
        words = paragraph.split()
        line = ""
        for word in words:
            candidate = f"{line} {word}" if line else word
            if font.getlength(candidate) > maximum and line:
                output.append(line)
                line = word
            else:
                line = candidate
        output.append(line)
    return output


def _fit_field(
    fonts: _FontRegistry, field: Mapping[str, Any], sx: float, sy: float,
) -> tuple[float, list[str], ImageFont.FreeTypeFont]:
    size = float(field["size"])
    minimum = max(8.0, min(13.0, size * 0.46))
    lines: list[str] = []
    font: ImageFont.FreeTypeFont | None = None
    for _index in range(80):
        font = fonts.font(str(field["font"]), int(field["weight"]), size * sy)
        if field.get("noWrap", False):
            lines = str(field["text"]).split("\n")
        else:
            lines = _wrap_lines(font, str(field["text"]), float(field["w"]) * sx)
        widest = max((font.getlength(line) for line in lines), default=0.0)
        height = len(lines) * size * float(field["lineHeight"])
        if (
            widest <= float(field["w"]) * sx + sx
            and height <= float(field["h"]) + 2.0
        ) or size <= minimum:
            break
        size -= 0.5
    assert font is not None
    return size, lines, font


def _metallic_row(width: int, start: float, span: float) -> Image.Image:
    row = Image.new("RGB", (width, 1))
    pixels = row.load()
    parsed = [(position, _hex_color(color)) for position, color in METALLIC_STOPS]
    for x in range(width):
        t = (x - start) / span if span else 0.0
        t = max(0.0, min(1.0, t))
        left = parsed[0]
        right = parsed[-1]
        for index in range(len(parsed) - 1):
            if parsed[index][0] <= t <= parsed[index + 1][0]:
                left, right = parsed[index], parsed[index + 1]
                break
        local = 0.0 if right[0] == left[0] else (t - left[0]) / (right[0] - left[0])
        pixels[x, 0] = tuple(
            int(round(left[1][channel] + (right[1][channel] - left[1][channel]) * local))
            for channel in range(3)
        )
    return row


def _shift_mask(mask: Image.Image, offset_x: int, offset_y: int) -> Image.Image:
    shifted = Image.new("L", mask.size, 0)
    source_left = max(0, -offset_x)
    source_top = max(0, -offset_y)
    source_right = min(mask.width, mask.width - offset_x)
    source_bottom = min(mask.height, mask.height - offset_y)
    if source_right <= source_left or source_bottom <= source_top:
        return shifted
    crop = mask.crop((source_left, source_top, source_right, source_bottom))
    shifted.paste(crop, (source_left + offset_x, source_top + offset_y))
    return shifted


def _draw_fields(
    canvas: Image.Image, state: Mapping[str, Any], fonts: _FontRegistry, sx: float, sy: float,
) -> tuple[list[str], list[str], dict[str, float]]:
    rendered: list[str] = []
    hidden: list[str] = []
    sizes: dict[str, float] = {}
    for field in state["fields"]:
        field_id = str(field["id"])
        if field.get("visible", True) is False:
            hidden.append(field_id)
            continue
        fitted_size, lines, font = _fit_field(fonts, field, sx, sy)
        sizes[field_id] = fitted_size
        mask = Image.new("L", canvas.size, 0)
        draw = ImageDraw.Draw(mask)
        alignment = str(field["align"])
        anchor = {"left": "lt", "center": "mt", "right": "rt"}[alignment]
        text_x = (
            float(field["x"])
            if alignment == "left"
            else float(field["x"]) + float(field["w"]) / 2.0
            if alignment == "center"
            else float(field["x"]) + float(field["w"])
        ) * sx
        line_height = fitted_size * float(field["lineHeight"]) * sy
        text_y = float(field["y"]) * sy
        for line in lines:
            draw.text((text_x, text_y), line, font=font, fill=255, anchor=anchor)
            text_y += line_height

        if field.get("shadowEnabled", False):
            blur = float(field.get("shadowBlur", 2.0)) * (sx + sy) / 2.0
            shadow = mask.filter(ImageFilter.GaussianBlur(radius=blur)) if blur > 0 else mask
            shadow = _shift_mask(
                shadow,
                int(round(float(field.get("shadowX", 2.0)) * sx)),
                int(round(float(field.get("shadowY", 3.0)) * sy)),
            )
            shadow_alpha = float(field.get("shadowOpacity", 0.3))
            shadow = shadow.point(lambda value: int(round(value * shadow_alpha)))
            shadow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            shadow_layer.putalpha(shadow)
            _paste_rgba(canvas, shadow_layer)

        if field["effect"] == "metallic":
            row = _metallic_row(
                canvas.width,
                float(field["x"]) * sx,
                float(field["w"]) * sx,
            )
            fill = row.resize(canvas.size, Image.Resampling.NEAREST).convert("RGBA")
        else:
            fill = Image.new("RGBA", canvas.size, _rgba(str(field["color"])))
        fill.putalpha(mask)
        _paste_rgba(canvas, fill)
        rendered.append(field_id)
    return rendered, hidden, sizes


def _sample_cubic(
    start: tuple[float, float], control1: tuple[float, float],
    control2: tuple[float, float], end: tuple[float, float], count: int = 32,
) -> list[tuple[float, float]]:
    points = []
    for index in range(count + 1):
        t = index / count
        inverse = 1.0 - t
        points.append((
            inverse ** 3 * start[0]
            + 3 * inverse * inverse * t * control1[0]
            + 3 * inverse * t * t * control2[0]
            + t ** 3 * end[0],
            inverse ** 3 * start[1]
            + 3 * inverse * inverse * t * control1[1]
            + 3 * inverse * t * t * control2[1]
            + t ** 3 * end[1],
        ))
    return points


def _draw_fixed_icons(canvas: Image.Image, sx: float, sy: float) -> None:
    mask = Image.new("L", canvas.size, 0)
    draw = ImageDraw.Draw(mask)
    width = max(1, int(round(2 * (sx + sy) / 2.0)))

    def point(value: tuple[float, float]) -> tuple[int, int]:
        return int(round(value[0] * sx)), int(round(value[1] * sy))

    def path(points: list[tuple[float, float]]) -> None:
        draw.line([point(item) for item in points], fill=255, width=width, joint="curve")

    draw.ellipse(
        (int(round(77 * sx)), int(round(1560 * sy)), int(round(107 * sx)), int(round(1590 * sy))),
        outline=255,
        width=width,
    )
    path([(82, 1587), (78, 1591), (80, 1583)])
    path(_quadratic_points(86, 1568, 90, 1580, 99, 1582, 16))
    path(_quadratic_points(99, 1582, 103, 1582, 103, 1578, 16))

    draw.ellipse(
        (int(round(512 * sx)), int(round(1560 * sy)), int(round(542 * sx)), int(round(1590 * sy))),
        outline=255,
        width=width,
    )
    path([(512, 1575), (542, 1575)])
    path([(527, 1560)] + _sample_cubic((527, 1560), (519, 1568), (519, 1582), (527, 1590))[1:])
    path([(527, 1560)] + _sample_cubic((527, 1560), (535, 1568), (535, 1582), (527, 1590))[1:])

    shadow = mask.filter(ImageFilter.GaussianBlur(radius=2 * (sx + sy) / 2.0))
    shadow = shadow.point(lambda value: int(round(value * 0.32)))
    shadow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow_layer.putalpha(shadow)
    _paste_rgba(canvas, shadow_layer)
    icon_layer = Image.new("RGBA", canvas.size, _rgba("#e7c96f"))
    icon_layer.putalpha(mask)
    _paste_rgba(canvas, icon_layer)


def _encode_png(image: Image.Image) -> bytes:
    output = BytesIO()
    image.convert("RGB").save(output, **_PNG_SAVE_OPTIONS)
    return output.getvalue()


def render_universal_card(
    definition: Any,
    instance: Any,
    asset_catalog: Mapping[str, Mapping[str, Any]],
    asset_sources: Mapping[str, str | Path],
    font_root: str | Path,
    *,
    output_size: tuple[int, int] | None = None,
    usage_context: str | None = None,
) -> UniversalCardRenderResult:
    """Valida e renderiza exclusivamente ``fr-universal-card``.

    Não existe fallback para F1--F6 nem conversão de CardInstance v1. Preview
    e master devem chamar esta mesma função, mudando apenas ``output_size``.
    """

    try:
        normalized_definition = validate_card_definition_v2(definition, asset_catalog)
        normalized_instance = validate_card_instance_v2(
            instance, normalized_definition, asset_catalog,
        )
    except ValueError as exc:
        raise UniversalCardRenderError(str(exc)) from exc
    if normalized_definition["renderer_id"] != RENDERER_ID:
        raise UniversalCardRenderError(f"Renderer incompatível; esperado {RENDERER_ID}.")
    if normalized_definition["renderer_version"] != RENDERER_VERSION:
        raise UniversalCardRenderError(
            f"Versão do renderer incompatível; esperado {RENDERER_VERSION}."
        )

    width, height = _validate_output_size(normalized_definition, output_size)
    sx = width / LOGICAL_WIDTH
    sy = height / LOGICAL_HEIGHT
    state = normalized_instance["state"]
    assets = state["assets"]
    resolver = _AssetResolver(asset_catalog, asset_sources, usage_context)
    # Todos os AssetRefs persistidos são resolvidos, mesmo se a layer estiver
    # oculta. Assim, estado incompleto nunca ganha um PNG aparentemente válido.
    background = resolver.resolve(assets["background"], "state.assets.background")
    logo = resolver.resolve(assets["logo"], "state.assets.logo")
    visual = (
        resolver.resolve(assets["visual"], "state.assets.visual")
        if assets["visual"] is not None
        else None
    )
    fonts = _FontRegistry(font_root)

    canvas = Image.new("RGBA", (width, height), _rgba(BACKGROUND_FALLBACK))
    if state["layers"]["background"]:
        _paste_rgba(canvas, background.resize((width, height), _resampling()))

    visual_report = None
    if visual is not None and float(assets["visualOpacity"]) > 0:
        visual_report = _draw_visual(canvas, visual, assets, sx, sy)

    rendered_lines: list[str] = []
    hidden_lines = [line["id"] for line in state["lines"]]
    if state["layers"]["grid"]:
        rendered_lines, hidden_lines = _draw_grid(canvas, state, sx, sy)

    if state["layers"]["logo"]:
        _draw_logo(canvas, logo, sx, sy)

    rendered_fields: list[str] = []
    hidden_fields = [field["id"] for field in state["fields"]]
    fitted_sizes: dict[str, float] = {}
    if state["layers"]["text"]:
        rendered_fields, hidden_fields, fitted_sizes = _draw_fields(
            canvas, state, fonts, sx, sy,
        )
        _draw_fixed_icons(canvas, sx, sy)

    png = _encode_png(canvas)
    digest = hashlib.sha256(png).hexdigest()
    report = {
        "renderer_id": RENDERER_ID,
        "renderer_version": RENDERER_VERSION,
        "output_size": [width, height],
        "state_digest": normalized_instance["state_digest"],
        "asset_ids": list(resolver.used),
        "asset_reviews": copy.deepcopy(resolver.reviews),
        "visual_review_required": bool(resolver.reviews),
        "warnings": list(resolver.warnings),
        "fonts": sorted(fonts.used, key=lambda row: (row["family"], row["weight"])),
        "field_ids": [field["id"] for field in state["fields"]],
        "rendered_field_ids": rendered_fields,
        "hidden_field_ids": hidden_fields,
        "fitted_sizes": fitted_sizes,
        "line_ids": [line["id"] for line in state["lines"]],
        "rendered_line_ids": rendered_lines,
        "hidden_line_ids": hidden_lines,
        "layers": dict(state["layers"]),
        "visual": visual_report,
    }
    return UniversalCardRenderResult(
        png_bytes=png,
        sha256=digest,
        width=width,
        height=height,
        renderer_id=RENDERER_ID,
        renderer_version=RENDERER_VERSION,
        state_digest=normalized_instance["state_digest"],
        report=report,
    )


def render_universal_preview(
    definition: Any,
    instance: Any,
    asset_catalog: Mapping[str, Mapping[str, Any]],
    asset_sources: Mapping[str, str | Path],
    font_root: str | Path,
    *,
    usage_context: str | None = None,
) -> UniversalCardRenderResult:
    """Preview nativo do mesmo pipeline, em 941x1672."""

    return render_universal_card(
        definition, instance, asset_catalog, asset_sources, font_root,
        output_size=(941, 1672),
        usage_context=usage_context,
    )


def render_universal_master(
    definition: Any,
    instance: Any,
    asset_catalog: Mapping[str, Mapping[str, Any]],
    asset_sources: Mapping[str, str | Path],
    font_root: str | Path,
    *,
    usage_context: str | None = None,
) -> UniversalCardRenderResult:
    """Master 2160x3840 do mesmo pipeline e snapshot renderizável."""

    return render_universal_card(
        definition, instance, asset_catalog, asset_sources, font_root,
        output_size=(2160, 3840),
        usage_context=usage_context,
    )


def compare_with_golden(
    result: UniversalCardRenderResult,
    golden_path: str | Path,
) -> dict[str, Any]:
    """Mede toda divergência sem aplicar tolerância implícita.

    ``status`` só é ``exact`` quando os bytes têm o mesmo SHA-256. Qualquer
    diferença permanece ``divergent`` e é acompanhada das métricas brutas; a
    função nunca normaliza, redimensiona ou esconde o golden.
    """

    path = Path(golden_path)
    if not path.is_file():
        raise UniversalCardRenderError(f"Golden ausente: {path.name}.")
    golden_bytes = path.read_bytes()
    golden_sha = hashlib.sha256(golden_bytes).hexdigest()
    try:
        with Image.open(BytesIO(result.png_bytes)) as current_opened:
            current_opened.load()
            current = current_opened.convert("RGB")
        with Image.open(BytesIO(golden_bytes)) as golden_opened:
            golden_opened.load()
            golden = golden_opened.convert("RGB")
    except (OSError, ValueError) as exc:
        raise UniversalCardRenderError("Resultado ou golden não é PNG decodificável.") from exc
    if current.size != golden.size:
        raise UniversalCardRenderError(
            f"Dimensão divergente: backend {current.size[0]}x{current.size[1]}, "
            f"golden {golden.size[0]}x{golden.size[1]}."
        )
    difference = ImageChops.difference(current, golden)
    histogram = difference.histogram()
    channel_samples = current.width * current.height * 3
    absolute_sum = sum((index % 256) * count for index, count in enumerate(histogram))
    squared_sum = sum((index % 256) ** 2 * count for index, count in enumerate(histogram))
    extrema = difference.getextrema()
    changed = difference.convert("RGB").point(lambda value: 255 if value else 0)
    changed_pixels = sum(1 for pixel in changed.getdata() if pixel != (0, 0, 0))
    return {
        "status": "exact" if result.sha256 == golden_sha else "divergent",
        "backend_sha256": result.sha256,
        "golden_sha256": golden_sha,
        "width": current.width,
        "height": current.height,
        "mean_absolute_error": absolute_sum / channel_samples,
        "root_mean_square_error": math.sqrt(squared_sum / channel_samples),
        "max_channel_error": max(maximum for _minimum, maximum in extrema),
        "changed_pixel_ratio": changed_pixels / (current.width * current.height),
    }
