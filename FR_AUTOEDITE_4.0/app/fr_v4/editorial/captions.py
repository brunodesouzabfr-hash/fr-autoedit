"""Exportação de legendas a partir de timestamps declarados, sem transcrição inventada."""
from __future__ import annotations


def _time(value: float) -> str:
    millis = round(float(value) * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    seconds, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def to_srt(items: list[dict]) -> str:
    blocks = []
    for index, item in enumerate(items, 1):
        start, end = float(item["start_sec"]), float(item["end_sec"])
        text = str(item.get("text") or "").strip()
        if not text or not 0 <= start < end:
            raise ValueError(f"Legenda {index} inválida.")
        blocks.append(f"{index}\n{_time(start)} --> {_time(end)}\n{text}")
    return "\n\n".join(blocks) + ("\n" if blocks else "")

