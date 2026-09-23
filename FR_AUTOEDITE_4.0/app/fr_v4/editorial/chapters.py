"""Capítulos e key moments derivados do roteiro, não de métricas inventadas."""
from __future__ import annotations


def validate(chapters: list[dict], duration: float) -> list[dict]:
    result = []
    previous = 0.
    for index, chapter in enumerate(chapters):
        start, end = float(chapter["start_sec"]), float(chapter["end_sec"])
        if not 0 <= start < end <= duration or start < previous:
            raise ValueError(f"Capítulo {index} fora de ordem ou da duração.")
        previous = end
        result.append(dict(chapter))
    return result


def youtube_description(chapters: list[dict]) -> str:
    def stamp(sec):
        sec = int(sec); return f"{sec//60:02d}:{sec%60:02d}"
    return "\n".join(f"{stamp(row['start_sec'])} {row['titulo']}" for row in chapters)

