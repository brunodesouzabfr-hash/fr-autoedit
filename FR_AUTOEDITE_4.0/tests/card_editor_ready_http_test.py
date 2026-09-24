#!/usr/bin/env python3
"""Round-trip HTTP do adapter content-only sobre um projeto ready_video sintético."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
import tempfile
import threading
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]


def load_studio():
    spec = importlib.util.spec_from_file_location("fr_studio_ready_http", ROOT / "app" / "studio.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Não foi possível carregar o Studio.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def request(url: str, token: str, payload: dict | None = None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    call = Request(
        url, data=body, method="GET" if body is None else "POST",
        headers={"X-FR-Token": token, "Content-Type": "application/json"},
    )
    with urlopen(call, timeout=20) as response:
        return json.loads(response.read())


def wait_for_job(state, project: Path, timeout: float = 90) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with state.lock:
            job = dict(state.jobs.get(project.name, {}))
        if job and not job.get("running"):
            return job
        time.sleep(0.08)
    raise AssertionError("A prévia ready_video não terminou dentro do limite.")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    studio = load_studio()
    import fr_autoedite as fr
    import project_scope

    with tempfile.TemporaryDirectory(prefix="fr-card-editor-ready-http-") as temporary:
        temporary_root = Path(temporary)
        source = temporary_root / "ready-source.mp4"
        fr.run([
            "ffmpeg", "-y", "-nostdin", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=c=0x284870:s=320x240:r=24:d=2",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=2",
            "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "96k", "-shortest", "-threads", "1", str(source),
        ])
        source_hash = sha256(source)
        state = studio.StudioState(ROOT, temporary_root / "Studio")
        project_a = Path(state.create_project("Ready HTTP A")["path"])
        config = state.load_config(project_a)
        config["input"].update({
            "mode": "ready_video", "timeline_locked": True,
            "allow_duration_extension": False,
            "style_pack_id": "fr_chiaroscuro_vintage_v1",
        })
        config["social"].update({
            "enabled": False, "reels_enabled": False,
            "stories_enabled": False, "carousel_enabled": False,
        })
        config["cards"]["generate_previews"] = False
        fr.prepare_ready_video(source, project_a, config, package=False)
        plan_a = fr.read_json(project_a / "READY_VIDEO_PLAN.json")
        plan_a["overlays"] = [{
            "overlay_id": "OV0001", "kind": "common_card",
            "start_sec": 0.25, "end_sec": 1.75,
            "text": "READY A", "body": "Corpo A explícito",
            "service_key": "", "asset_id": "", "presentation": "overlay",
            "position": "center", "safe_area": "title_safe", "opacity": 1,
            "animation_in": "fade", "animation_out": "fade",
            "audio_policy": "preserve", "rationale": "Fixture HTTP",
        }]
        state.save_ready_video_plan(project_a, plan_a)

        project_b = Path(state.create_project("Ready HTTP B")["path"])
        plan_b = json.loads(json.dumps(plan_a))
        plan_b["overlays"][0]["text"] = "READY B"
        plan_b["overlays"][0]["body"] = "Corpo B explícito"
        project_scope.write(project_b / "READY_VIDEO_PLAN.json", plan_b)

        server = ThreadingHTTPServer(("127.0.0.1", 0), studio.StudioHandler)
        server.state = state
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            def card_url(project: Path) -> str:
                return base + "/api/card-content?" + urlencode({
                    "token": state.token, "project": project.name,
                    "segment_id": "OV0001", "input_mode": "ready_video",
                })

            card_a = request(card_url(project_a), state.token)["card"]
            card_b = request(card_url(project_b), state.token)["card"]
            self_check = (card_a["fields"]["title"], card_b["fields"]["title"])
            assert self_check == ("READY A", "READY B"), self_check

            before_invalid = (project_a / "READY_VIDEO_PLAN.json").read_bytes()
            invalid = {
                "adapter_version": card_a["adapter_version"],
                "base_revision": card_a["base_revision"],
                "segment_id": "OV0001",
                "fields": {"title": "Inválido", "body": "data:image/png;base64,AAAA"},
            }
            try:
                request(card_url(project_a), state.token, invalid)
            except HTTPError as exc:
                assert exc.code == 400
            else:
                raise AssertionError("Data URL deveria ser rejeitada.")
            assert (project_a / "READY_VIDEO_PLAN.json").read_bytes() == before_invalid

            base_video = project_a / fr.read_json(project_a / "MANIFESTO_MEDIA.json")["media"][0]["source_path"]
            base_hash = sha256(base_video)
            edited_payload = {
                "adapter_version": card_a["adapter_version"],
                "base_revision": card_a["base_revision"],
                "segment_id": "OV0001",
                "fields": {"title": "READY A EDITADO", "body": "Corpo A revisado"},
            }
            edited = request(card_url(project_a), state.token, edited_payload)
            assert edited["preview_action"] == "ready-preview"
            job = wait_for_job(state, project_a)
            assert job["returncode"] == 0, "\n".join(job.get("log", []))

            persisted = fr.read_json(project_a / "READY_VIDEO_PLAN.json")
            assert persisted["timeline_locked"] is True
            assert persisted["base_video_id"] == "READY_VIDEO_BASE"
            assert persisted["overlays"][0]["overlay_id"] == "OV0001"
            assert persisted["overlays"][0]["text"] == "READY A EDITADO"
            assert persisted["overlays"][0]["body"] == "Corpo A revisado"
            assert request(card_url(project_b), state.token)["card"]["fields"]["title"] == "READY B"
            preview = fr.read_json(project_a / "_CONTROLE" / "READY_VIDEO_PREVIEW.json")
            assert (project_a / preview["output_path"]).is_file()
            assert preview["signature"]
            assert sha256(base_video) == base_hash
            assert sha256(source) == source_hash

            try:
                request(card_url(project_a), state.token, edited_payload)
            except HTTPError as exc:
                assert exc.code == 400
                assert "mudou desde" in json.loads(exc.read())["error"]
            else:
                raise AssertionError("Revisão obsoleta deveria ser rejeitada.")
        finally:
            server.shutdown()
            server.server_close()
    print("CARD EDITOR READY HTTP TEST OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
