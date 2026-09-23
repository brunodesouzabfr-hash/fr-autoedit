#!/usr/bin/env python3
"""Regressão: roteiros de IA aceitam relógio local ou absoluto de cenas."""

from __future__ import annotations

import copy
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT / "app"))

import fr_autoedite as fr  # noqa: E402


def manifest() -> dict:
    return {
        "media": [
            {
                "id": "M0036", "media_type": "video", "duration_sec": 48.0,
                "source_path": "originais/video.mp4", "proxy_path": "proxies/video.mp4",
                "thumbnail_path": "miniaturas/M0036.jpg", "has_audio": True,
            },
            {
                "id": "M0036C003", "media_type": "video", "duration_sec": 8.0,
                "parent_video": "M0036", "scene_start_sec": 13.1, "scene_end_sec": 21.1,
                "source_path": "originais/video.mp4", "proxy_path": "proxies/video.mp4",
                "thumbnail_path": "miniaturas/cenas/M0036C003.jpg", "has_audio": True,
            },
        ]
    }


def plan(start: float, duration: float = 3.5, speed: float = 1.0) -> dict:
    return {
        "segments": [{
            "segment_id": "S0030", "type": "media", "media_id": "M0036C003",
            "start_sec": start, "duration_sec": duration, "transition": "dissolve",
            "editorial_timelapse": speed > 1.0, "playback_speed": speed,
            "include_in": ["branded", "clean"],
        }]
    }


def main() -> int:
    absolute = fr.validate_imported_plan(plan(13.1), manifest(), "filme principal")
    assert absolute["segments"][0]["start_sec"] == 13.1
    assert absolute["import_repairs"] == []

    local = fr.validate_imported_plan(plan(0.0), manifest(), "filme principal")
    assert local["segments"][0]["start_sec"] == 13.1
    assert local["import_repairs"][0]["reason"].startswith("tempo local")

    stale = plan(10.0)
    stale["segments"][0]["source_window_start_sec"] = 9.0
    normalized = fr.validate_imported_plan(stale, manifest(), "filme principal")
    assert normalized["segments"][0]["start_sec"] == 14.1
    assert "atualização" in normalized["import_repairs"][0]["reason"]

    rounded = fr.validate_imported_plan(plan(0.0, duration=1.2, speed=6.667), manifest(), "filme principal")
    assert rounded["segments"][0]["start_sec"] == 13.1
    assert rounded["segments"][0]["playback_speed"] == 6.666
    assert {item["field"] for item in rounded["import_repairs"]} == {"start_sec", "playback_speed"}

    invalid = copy.deepcopy(plan(99.0))
    try:
        fr.validate_imported_plan(invalid, manifest(), "filme principal")
    except fr.AutoEditeError as exc:
        message = str(exc)
        assert "M0036C003" in message and "tempo local" in message
    else:
        raise AssertionError("Um corte realmente externo à cena deveria ser recusado.")

    print("AI BRIEF WINDOW TEST OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
