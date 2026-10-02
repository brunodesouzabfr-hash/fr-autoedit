from __future__ import annotations

import json
import os
import sys
import time

import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))

import proxy_integrity
import runtime_control
import fr_autoedite
from studio import StudioState


def _write(path: Path, data: bytes = b"x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def test_scene_windows_clamp_discard_and_decode_once(tmp_path: Path) -> None:
    source = tmp_path / "originais" / "source.mp4"
    proxy = tmp_path / "proxies" / "M0036_source_PROXY.mp4"
    _write(source, b"source")
    _write(proxy, b"proxy")

    manifest = {
        "media": [
            {
                "id": "M0036C017",
                "media_type": "video",
                "source_path": "originais/source.mp4",
                "proxy_path": "proxies/M0036_source_PROXY.mp4",
                "parent_video": "M0036",
                "scene_start_sec": 8.0,
                "scene_end_sec": 10.0,
                "duration_sec": 2.0,
                "status": "ok",
            },
            {
                "id": "M0036C018",
                "media_type": "video",
                "source_path": "originais/source.mp4",
                "proxy_path": "proxies/M0036_source_PROXY.mp4",
                "parent_video": "M0036",
                "scene_start_sec": 9.95,
                "scene_end_sec": 10.5,
                "duration_sec": 0.55,
                "status": "ok",
            },
        ]
    }
    calls = {"decode": 0}

    def probe(_path: Path) -> dict:
        return {
            "video_duration_sec": 10.0,
            "duration_sec": 10.0,
            "fps": 25.0,
            "width": 720,
            "height": 1280,
            "declared_frame_count": 250,
        }

    def decode(_path: Path) -> dict:
        calls["decode"] += 1
        return {"decoded_frame_count": 248, "decoded_coverage_end": 9.9}

    result = proxy_integrity.ensure_manifest_integrity(
        tmp_path,
        manifest,
        parameters_for=lambda _row: {"pipeline_version": "test"},
        probe=probe,
        decode_video=decode,
        continue_on_error=True,
    )

    first, second = result["media"]
    assert first["status"] == "ok"
    assert first["scene_end_sec"] == 9.9
    assert round(first["duration_sec"], 3) == 1.9
    assert first["proxy_integrity"]["coverage_adjusted"] is True
    assert second["status"] == "skipped"
    assert second["excluded_from_auto_edit"] is True
    assert result["integrity_report"]["clamped_scenes"] == 1
    assert result["integrity_report"]["skipped_scenes"] == 1
    # As duas cenas compartilham o mesmo proxy: ele só deve ser decodificado uma vez.
    assert calls["decode"] == 1


def test_integrity_error_isolated_when_tolerant(tmp_path: Path) -> None:
    source = tmp_path / "originais" / "bad.mp4"
    _write(source, b"source")
    manifest = {
        "media": [{
            "id": "M0046",
            "media_type": "video",
            "source_path": "originais/bad.mp4",
            "proxy_path": "proxies/missing.mp4",
            "duration_sec": 3.0,
            "status": "ok",
        }]
    }
    result = proxy_integrity.ensure_manifest_integrity(
        tmp_path,
        manifest,
        parameters_for=lambda _row: {"pipeline_version": "test"},
        probe=lambda _path: {},
        decode_video=lambda _path: {},
        continue_on_error=True,
    )
    row = result["media"][0]
    assert row["status"] == "error"
    assert row["excluded_from_auto_edit"] is True
    assert result["integrity_report"]["errors"] == 1


def test_skip_marker_matches_scene_to_parent(tmp_path: Path) -> None:
    (tmp_path / "_CONTROLE").mkdir()
    runtime_control.request_skip(tmp_path, "M0036C017")
    assert runtime_control.consume_skip("M0036", tmp_path)["target_item"] == "M0036C017"
    assert not runtime_control.marker_path(tmp_path).exists()


def test_skip_marker_does_not_hit_unrelated_item(tmp_path: Path) -> None:
    (tmp_path / "_CONTROLE").mkdir()
    runtime_control.request_skip(tmp_path, "M0046")
    assert runtime_control.consume_skip("M0045", tmp_path) is None
    assert runtime_control.marker_path(tmp_path).exists()
    runtime_control.clear_skip(tmp_path)


def test_studio_exposes_skip_current_button_and_route() -> None:
    html = (ROOT / "assets" / "studio" / "index.html").read_text(encoding="utf-8")
    studio = (ROOT / "app" / "studio.py").read_text(encoding="utf-8")
    assert 'id="skipCurrentJob"' in html
    assert "/api/skip-current" in html
    assert 'parsed.path == "/api/skip-current"' in studio
    assert "def skip_current_item" in studio


def test_long_subprocess_can_be_skipped_without_cancelling_job(tmp_path: Path) -> None:
    (tmp_path / "_CONTROLE").mkdir()
    runtime_control.request_skip(tmp_path, "M0046")
    previous = Path.cwd()
    os.chdir(tmp_path)
    started = time.monotonic()
    try:
        with pytest.raises(runtime_control.SkipCurrentItem):
            fr_autoedite.run(
                [sys.executable, "-c", "import time; time.sleep(10)"],
                timeout=20, allow_skip=True, item_id="M0046", operation="teste skip",
            )
    finally:
        os.chdir(previous)
    assert time.monotonic() - started < 4


def test_brief_retry_resumes_missing_package_lots(tmp_path: Path) -> None:
    app_root = ROOT
    state = StudioState(app_root, tmp_path / "Studio")
    created = state.create_project("Retry IA")
    project = Path(created["path"])
    (project / "MANIFESTO_MEDIA.json").write_text('{"media": []}\n', encoding="utf-8")
    command = state._command_for(project, "brief-generate")
    assert "pacote-chatgpt" in command
    assert "--conflito" in command
    assert "replace" in command
