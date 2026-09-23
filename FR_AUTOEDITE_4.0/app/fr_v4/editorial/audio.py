"""Políticas de áudio transparentes e reversíveis."""
from __future__ import annotations


def plan(*, preserve_original: bool = True, normalize_lufs: float | None = None,
         music_asset_id: str | None = None, music_volume: float = 0., ducking: bool = False) -> dict:
    if normalize_lufs is not None and not -24 <= float(normalize_lufs) <= -9:
        raise ValueError("normalize_lufs deve ficar entre -24 e -9.")
    if not 0 <= float(music_volume) <= 1:
        raise ValueError("music_volume deve ficar entre 0 e 1.")
    return {"preserve_original": bool(preserve_original), "normalize_lufs": normalize_lufs,
            "music_asset_id": music_asset_id, "music_volume": float(music_volume),
            "ducking": bool(ducking)}


def ffmpeg_filter(normalize_lufs: float | None) -> str | None:
    return None if normalize_lufs is None else f"loudnorm=I={float(normalize_lufs):.1f}:TP=-1.5:LRA=11"

