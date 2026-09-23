"""Planejamento de color sem alterar mídia durante a análise."""
from __future__ import annotations

ALLOWED = frozenset({"neutral", "quiet_chiaroscuro", "technical_clean"})


def ffmpeg_filters(profile: str = "quiet_chiaroscuro", strength: float = .35) -> list[str]:
    if profile not in ALLOWED:
        raise ValueError("Perfil de cor desconhecido.")
    strength = max(0., min(1., float(strength)))
    if profile == "neutral" or strength == 0:
        return []
    if profile == "technical_clean":
        return [f"eq=contrast={1+.06*strength:.4f}:saturation={1-.04*strength:.4f}"]
    return [
        f"eq=contrast={1+.10*strength:.4f}:brightness={-.015*strength:.4f}:saturation={1-.12*strength:.4f}",
        "curves=all='0/0 0.18/0.14 0.72/0.76 1/1'",
    ]


def validate_lut(path: str) -> None:
    if path and not path.lower().endswith(".cube"):
        raise ValueError("LUT deve ser arquivo .cube local.")

