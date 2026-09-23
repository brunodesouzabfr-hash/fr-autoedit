"""Presets editoriais como limites, não promessa algorítmica."""
from __future__ import annotations
import copy

PRESETS = {
    "instagram_reels": {"aspect": "9:16", "max_duration_sec": 180, "caption_safe": True, "pace": "adaptive"},
    "youtube_shorts": {"aspect": "9:16", "max_duration_sec": 180, "caption_safe": True, "pace": "adaptive"},
    "stories": {"aspect": "9:16", "part_duration_sec": 15, "caption_safe": True, "pace": "adaptive"},
    "feed_4x5": {"aspect": "4:5", "max_duration_sec": 90, "caption_safe": True, "pace": "contemplative"},
    "youtube_long": {"aspect": "16:9", "chapters": True, "pace": "editorial"},
}


def preset(name: str) -> dict:
    if name not in PRESETS:
        raise ValueError("Preset social desconhecido.")
    return copy.deepcopy(PRESETS[name])

