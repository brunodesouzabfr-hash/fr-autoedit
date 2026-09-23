#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw


def run(command: list[str]) -> None:
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> int:
    root = Path(sys.argv[1]).resolve()
    app_root = Path(sys.argv[2]).resolve()
    media = root / "album" / "Google Fotos" / "Cozinha Teste"
    media.mkdir(parents=True, exist_ok=True)

    for index, date in enumerate(("2025-07-15", "2025-08-22"), 1):
        image = Image.new("RGB", (900, 1200), "#0A2F26" if index == 1 else "#E6D6B5")
        draw = ImageDraw.Draw(image)
        draw.rectangle((80, 250, 820, 950), outline="#FC7016", width=24)
        draw.text((120, 110), f"IMAGEM TESTE {index}", fill="#FC7016")
        path = media / f"IMG_{date.replace('-', '')}_120000.jpg"
        image.save(path, quality=92)
        sidecar = {"photoTakenTime": {"timestamp": str(1752577200 + index * 86400)}}
        Path(str(path) + ".json").write_text(json.dumps(sidecar), encoding="utf-8")
        if index == 2:
            burst = media / f"IMG_{date.replace('-', '')}_120000_BURST.jpg"
            image.save(burst, quality=88)
            Path(str(burst) + ".json").write_text(json.dumps(sidecar), encoding="utf-8")

    run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=24",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000", "-t", "2.4",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
        str(media / "VID_20250923_120000.mp4")
    ])
    run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=#123F34:size=360x640:rate=24",
        "-t", "2.2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(media / "VID_20251004_120000.mp4")
    ])
    run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc2=size=240x160:rate=8",
        "-t", "31.2", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "31",
        "-pix_fmt", "yuv420p", str(media / "VID_20251110_LONGO.mp4")
    ])

    zip_path = root / "fr autoedite.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((root / "album").rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(root / "album"))

    answers = json.loads((app_root / "examples" / "cozinha_carreira.questionario.json").read_text(encoding="utf-8"))
    answers["project"]["name"] = "Teste Automatizado"
    answers["project"]["slug"] = "teste-automatizado"
    answers["project"]["zip_path"] = str(zip_path)
    answers["project"]["workspace_root"] = str(root / "workspace")
    answers["edition"].update({
        "width": 360,
        "height": 640,
        "quality_preset": "custom",
        "fps": 24,
        "target_duration_sec": 18,
        "max_video_excerpt_sec": 1.4,
        "still_duration_sec": 1.1,
        "phase_card_duration_sec": 0.8,
        "render_source": "proxies",
    })
    answers["handoff"].update({"chatgpt_lot_max_mb": 25, "proxy_long_side": 360})
    answers["local_analysis"] = {
        "enabled": True,
        "deduplicate_bursts": True,
        "scene_detection": True,
        "detect_stability": True,
        "organize_by_phase": True,
        "create_selects": True,
        "minimum_quality_score": 0,
        "scene_threshold": 0.34,
        "minimum_scene_sec": 3,
        "maximum_scene_sec": 8,
        "max_scene_scan_sec": 40,
        "max_scene_clips_per_video": 4
    }
    answers["export_quality"] = {"draft_mode": True, "parallel_workers": 2, "max_lot_mb": 25}
    answers.setdefault("visual_effects", {})["editorial_timelapse"] = {
        "enabled": True,
        "speed_factor": 4.0,
        "minimum_source_duration_sec": 18.0,
        "output_duration_sec": 1.0,
        "max_segments": 1,
        "mute_original_audio": True,
    }
    custom_intro = root / "intro-personalizada.png"
    intro_image = Image.new("RGB", (720, 1280), "#031812")
    intro_draw = ImageDraw.Draw(intro_image)
    intro_draw.rectangle((80, 80, 640, 1200), outline="#F6A700", width=18)
    intro_draw.text((150, 600), "INTRO TESTE FR", fill="#FC7016")
    intro_image.save(custom_intro)
    answers["service_intro"] = {
        "enabled": True,
        "service_key": "iluminacao",
        "duration_sec": 0.8,
        "position": "after_intro",
        "include_in_reels": True,
        "custom_title": "ILUMINAÇÃO",
        "custom_body": "Luz técnica integrada ao projeto."
    }
    answers["external_intro_outro"] = {
        "intro_enabled": True,
        "intro_path": str(custom_intro),
        "intro_duration_sec": 0.8,
        "intro_mode": "before_card",
        "intro_preserve_audio": False,
        "intro_include_in_reels": True,
        "outro_enabled": False,
        "outro_path": "",
        "outro_duration_sec": 0.8,
        "outro_mode": "after_card",
        "outro_preserve_audio": True,
        "outro_include_in_reels": True,
        "include_in_clean_version": False
    }
    answers["social"].update({
        "reel_durations_sec": [6, 8, 10],
        "story_source_duration_sec": 8,
        "story_part_duration_sec": 5,
        "carousel_slides": 5,
        "carousel_width": 540,
        "carousel_height": 675,
    })
    questionnaire = root / "questionario-teste.json"
    questionnaire.write_text(json.dumps(answers, ensure_ascii=False, indent=2), encoding="utf-8")
    print(questionnaire)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
