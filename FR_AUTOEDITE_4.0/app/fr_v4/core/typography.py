"""Medição real em Pillow; sem corte de palavras, truncamento ou fallback de fonte silencioso."""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from .config import FONTS
from .grid import Box


class TypographyError(ValueError): pass


@lru_cache(maxsize=256)
def load_font(font_directory: str, role: str, size: int, family='F3'):
    from PIL import ImageFont
    if role not in FONTS: raise TypographyError('Papel tipográfico não autorizado.')
    if role == 'editorial' and family not in {'F1', 'F6'}:
        raise TypographyError('Cormorant é restrita a F1/F6.')
    path = Path(font_directory)/FONTS[role]
    if not path.is_file(): raise TypographyError(f'Fonte obrigatória ausente: {path.name}')
    return ImageFont.truetype(str(path), int(size))


@dataclass(frozen=True)
class TextLayout:
    lines: tuple[str, ...]
    size: int
    line_height: int
    role: str


def measure(draw, text: str, box: Box, font_directory: Path, role: str,
            family: str, maximum: int, minimum: int, max_lines: int) -> TextLayout:
    if not isinstance(text, str): raise TypographyError('Texto deve ser string.')
    if not text.strip(): return TextLayout((), maximum, maximum, role)
    for size in range(maximum, minimum-1, -1):
        font = load_font(str(font_directory), role, size, family)
        lines = []
        failed = False
        for paragraph in text.splitlines():
            current = ''
            for word in paragraph.split():
                if draw.textlength(word, font=font) > box.width:
                    failed = True
                    break
                candidate = f'{current} {word}'.strip()
                if current and draw.textlength(candidate, font=font) > box.width:
                    lines.append(current)
                    current = word
                else: current = candidate
            if failed: break
            lines.append(current)
        ascent, descent = font.getmetrics()
        line_height = ceil_height = round((ascent+descent)*1.12)
        if not failed and len(lines) <= max_lines and ceil_height*len(lines) <= box.height:
            return TextLayout(tuple(lines), size, line_height, role)
    raise TypographyError('Texto excede a caixa legível; reduza ou divida o conteúdo.')


def draw_text(draw, text: str, box: Box, font_directory: Path, role: str,
              family: str, color, maximum: int, minimum: int,
              max_lines=3, align='left') -> TextLayout:
    layout = measure(draw, text, box, font_directory, role, family, maximum, minimum, max_lines)
    font = load_font(str(font_directory), role, layout.size, family)
    for index, line in enumerate(layout.lines):
        x = box.x
        if align == 'center': x += (box.width-draw.textlength(line, font=font))/2
        draw.text((round(x), round(box.y+index*layout.line_height)), line,
                  font=font, fill=color, anchor='lt')
    return layout
