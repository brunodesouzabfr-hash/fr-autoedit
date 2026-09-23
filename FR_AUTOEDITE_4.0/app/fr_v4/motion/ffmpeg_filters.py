"""Construtores de filtros FFmpeg autorizados pelo sistema visual v2."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Transition:
    name: str
    duration: float
    filter_name: str


TRANSITIONS = {
    "dissolve": Transition("dissolve", .4, "fade"),
    "fade": Transition("fade", .4, "fade"),
    "fade_black": Transition("fade_black", .25, "fadeblack"),
}


def overlay_chain(index: int, start: float, end: float, animation_in: str = "fade",
                  animation_out: str = "fade", fade_sec: float = .25) -> str:
    if not 0 <= start < end:
        raise ValueError("Janela de overlay inválida.")
    if animation_in not in {"none", "fade", "slide_up", "slide_down", "soft_scale"}:
        raise ValueError("animation_in não autorizada.")
    if animation_out not in {"none", "fade", "slide_up", "slide_down", "soft_scale"}:
        raise ValueError("animation_out não autorizada.")
    filters = ["format=rgba"]
    if animation_in != "none":
        filters.append(f"fade=t=in:st={start:.6f}:d={min(fade_sec, (end-start)/2):.6f}:alpha=1")
    if animation_out != "none":
        out_start = max(start, end-min(fade_sec, (end-start)/2))
        filters.append(f"fade=t=out:st={out_start:.6f}:d={end-out_start:.6f}:alpha=1")
    return f"[{index}:v]{','.join(filters)}[ov{index}]"


def xfade(name: str, duration: float, offset: float) -> str:
    if name not in TRANSITIONS:
        raise ValueError("Transição quiet luxury desconhecida.")
    duration = max(.2, min(float(duration), 1.2))
    if offset < 0:
        raise ValueError("Offset negativo.")
    return f"xfade=transition={TRANSITIONS[name].filter_name}:duration={duration:.6f}:offset={offset:.6f}"

