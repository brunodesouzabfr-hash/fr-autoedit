#!/usr/bin/env python3
"""M9.7: runtime universal, Studio HTTP e roteamento raw/ready explícito."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
import threading
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "tests"))

import card_persistence_v2 as persistence  # noqa: E402
import card_persistence_v2_test as persistence_fixture  # noqa: E402
import card_state_v2 as cards  # noqa: E402
import project_scope  # noqa: E402
import ready_video  # noqa: E402
import universal_card_runtime as runtime  # noqa: E402


def load_studio():
    spec = importlib.util.spec_from_file_location("fr_studio_m97", ROOT / "app" / "studio.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Não foi possível carregar o Studio.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def http_json(url: str, token: str, payload: dict | None = None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url, data=body, method="GET" if body is None else "POST",
        headers={"X-FR-Token": token, "Content-Type": "application/json"},
    )
    with urlopen(request, timeout=60) as response:
        data = response.read()
        return json.loads(data) if response.headers.get_content_type() == "application/json" else data


class UniversalCardRuntimeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        persistence_fixture.CardPersistenceV2Test.setUpClass()
        cls.editor_root = runtime.discover_component(ROOT)
        cls.font_root = runtime.discover_font_root(ROOT, cls.editor_root)

    def setUp(self):
        fixture = persistence_fixture.CardPersistenceV2Test(
            methodName="test_raw_save_reopen_is_canonical_and_never_mutates_plan_or_media"
        )
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.project = fixture.project
        self.definition = copy.deepcopy(fixture.definition)
        self.instance = copy.deepcopy(fixture.instance)
        component_catalog, _sources = runtime.component_asset_context(self.editor_root)
        background = component_catalog["component/background-fr-hd"]
        logo = component_catalog["component/logo-fr"]
        for state in (self.definition["default_state"], self.instance["state"]):
            state["assets"]["background"] = copy.deepcopy(background)
            state["assets"]["logo"] = copy.deepcopy(logo)
        self.instance["state_digest"] = cards.renderable_state_digest(
            self.instance["definition_ref"], self.instance["state"],
        )
        self.catalog = copy.deepcopy(component_catalog)
        self.catalog["synthetic_visual"] = copy.deepcopy(fixture.catalog["synthetic_visual"])
        self.context = persistence.project_context(self.project)
        self.saved = persistence.save_card_state(
            self.project, self.definition, self.instance, self.catalog,
            expected_project_id=self.context["project_id"],
            expected_plan_revision=self.context["plan_revision"],
            expected_store_revision=None, base_revision=None,
        )

    def binding(self, asset_id: str) -> str:
        return "/api/card-v2-asset?asset_id=" + asset_id

    def open(self) -> dict:
        return runtime.open_editor_session(
            self.project, self.instance["instance_id"],
            expected_project_id=self.context["project_id"],
            editor_root=self.editor_root, binding_builder=self.binding,
        )

    def test_open_save_preview_round_trip_and_rollback_preserve_plan_and_media(self):
        opened = self.open()
        self.assertEqual(opened["renderer_id"], "fr-universal-card")
        self.assertEqual(len(opened["session"]["editor_state"]["fields"]), 21)
        self.assertEqual(len(opened["session"]["editor_state"]["lines"]), 29)
        self.assertFalse(opened["external_distribution_allowed"])
        self.assertNotIn(str(self.project), json.dumps(opened))
        plan_before = (self.project / "EDIT_PLAN.json").read_bytes()
        media_before = self.fixture.visual.read_bytes()

        session = copy.deepcopy(opened["session"])
        title = next(row for row in session["editor_state"]["fields"] if row["id"] == "title")
        title.update({"text": "ROUND-TRIP STUDIO M9.7", "x": 111, "color": "#F6A700"})
        session["editor_state"]["assets"].update({
            "visualShape": "circle", "visualZoom": 2.25,
            "visualFocalX": 73, "visualFocalY": 27,
        })
        result = runtime.save_editor_session(
            self.project, session,
            expected_project_id=self.context["project_id"],
            editor_root=self.editor_root, binding_builder=self.binding,
            font_root=self.font_root,
        )
        preview = self.project / result["preview"]["relative"]
        self.assertTrue(preview.is_file())
        self.assertEqual(hashlib.sha256(preview.read_bytes()).hexdigest(), result["renderer_sha256"])
        self.assertEqual(result["preview"]["state_digest"], result["instance"]["state_digest"])
        self.assertEqual((self.project / "EDIT_PLAN.json").read_bytes(), plan_before)
        self.assertEqual(self.fixture.visual.read_bytes(), media_before)

        restored = persistence.rollback_card_state(
            self.project, self.instance["instance_id"], self.saved["snapshot_digest"], self.catalog,
            expected_project_id=self.context["project_id"],
            expected_store_revision=result["store_revision"],
            expected_current_revision=result["instance_revision"],
        )
        self.assertEqual(restored["instance"], self.instance)

    def test_timeline_router_is_deterministic_and_unregistered_legacy_is_rejected(self):
        first = self.project / "preview-a.png"
        second = self.project / "preview-b.png"
        self.assertTrue(runtime.render_timeline_card(
            self.project, self.instance["instance_id"], first, (480, 854), app_root=ROOT,
        ))
        self.assertTrue(runtime.render_timeline_card(
            self.project, self.instance["instance_id"], second, (480, 854), app_root=ROOT,
        ))
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(
            runtime.universal_state_digest(self.project, self.instance["instance_id"]),
            self.instance["state_digest"],
        )
        untouched = self.project / "legacy-untouched.png"
        with self.assertRaisesRegex(runtime.UniversalCardRuntimeError, "fallback silencioso"):
            runtime.render_timeline_card(
                self.project, "LEGACY-ONLY", untouched, (480, 854), app_root=ROOT,
            )
        self.assertFalse(untouched.exists())

    def test_legacy_plan_projection_does_not_invalidate_universal_preview(self):
        opened = self.open()
        saved = runtime.save_editor_session(
            self.project, opened["session"],
            expected_project_id=self.context["project_id"],
            editor_root=self.editor_root, binding_builder=self.binding,
            font_root=self.font_root,
        )
        preview = self.project / saved["preview"]["relative"]
        preview_hash = hashlib.sha256(preview.read_bytes()).hexdigest()
        previous = project_scope.read(self.project / "EDIT_PLAN.json")
        current = copy.deepcopy(previous)
        segment = next(
            row for row in current["segments"]
            if row.get("segment_id") == self.instance["instance_id"]
        )
        segment["title"] = "PROJEÇÃO LEGADA NÃO AUTORITATIVA"
        segment["body"] = "O state_digest universal não mudou."

        studio = load_studio()
        state = studio.StudioState(ROOT, self.project.parent)
        self.assertEqual(
            state._invalidate_card_previews(self.project, previous, current), []
        )
        self.assertTrue(preview.is_file())
        self.assertEqual(hashlib.sha256(preview.read_bytes()).hexdigest(), preview_hash)

    def test_http_open_assets_stale_save_and_project_isolation(self):
        studio = load_studio()
        state = studio.StudioState(ROOT, self.project.parent)
        server = ThreadingHTTPServer(("127.0.0.1", 0), studio.StudioHandler)
        server.state = state
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            query = urlencode({
                "token": state.token, "project": self.project.name,
                "instance_id": self.instance["instance_id"],
            })
            opened = http_json(base + "/api/card-v2?" + query, state.token)["card"]
            session = opened["session"]
            background_url = session["editor_state"]["assets"]["background"]
            asset = http_json(base + background_url, state.token)
            self.assertTrue(asset.startswith(b"\x89PNG\r\n\x1a\n"))
            title = next(row for row in session["editor_state"]["fields"] if row["id"] == "title")
            title["text"] = "HTTP UNIVERSAL M9.7"
            saved = http_json(
                base + "/api/card-v2?" + urlencode({"token": state.token, "project": self.project.name}),
                state.token, {"session": session},
            )
            self.assertFalse(saved["preview_job_started"])
            self.assertEqual(saved["result"]["instance"]["edit_origin"], "manual")
            self.assertTrue((self.project / saved["result"]["preview"]["relative"]).is_file())
            try:
                http_json(
                    base + "/api/card-v2?" + urlencode({"token": state.token, "project": self.project.name}),
                    state.token, {"session": session},
                )
            except HTTPError as exc:
                self.assertEqual(exc.code, 400)
                self.assertIn("revisão obsoleta", json.loads(exc.read())["error"])
            else:
                self.fail("Sessão obsoleta deveria ser rejeitada.")

            bad_asset = background_url.replace(
                "project_id=" + opened["project_id"], "project_id=PROJECT-INVENTED"
            )
            with self.assertRaises(HTTPError) as caught:
                http_json(base + bad_asset, state.token)
            self.assertEqual(caught.exception.code, 400)
        finally:
            server.shutdown()
            server.server_close()

    def test_ready_overlay_dispatches_universal_without_mutating_locked_base(self):
        video = self.project / "_ORIGINAIS" / "base.mp4"
        video.parent.mkdir(exist_ok=True)
        video.write_bytes(b"synthetic-ready-video-base-m9-7")
        video_hash = hashlib.sha256(video.read_bytes()).hexdigest()
        ready_instance = copy.deepcopy(self.instance)
        ready_instance["instance_id"] = "OV-UNIVERSAL"
        ready_instance["placement"] = {
            "timebase": "ready_video_base", "start_sec": 1.25, "end_sec": 4.75,
        }
        ready_instance["state_digest"] = cards.renderable_state_digest(
            ready_instance["definition_ref"], ready_instance["state"],
        )
        ready_plan = {
            "input_mode": "ready_video", "base_video_id": "READY_VIDEO_BASE",
            "timeline_locked": True,
            "overlays": [{
                "overlay_id": "OV-UNIVERSAL", "kind": "common_card",
                "start_sec": 1.25, "end_sec": 4.75, "text": "Ready", "body": "V2",
                "asset_id": "", "presentation": "full_frame", "position": "center",
                "safe_area": "auto", "opacity": 1,
            }],
        }
        ready_manifest = copy.deepcopy(self.fixture.manifest)
        ready_manifest["input_mode"] = "ready_video"
        ready_manifest["base_video_id"] = "READY_VIDEO_BASE"
        ready_manifest["media"].append({
            "id": "READY_VIDEO_BASE", "media_type": "video", "status": "ok",
            "source_path": "_ORIGINAIS/base.mp4", "sha256": video_hash,
            "duration_sec": 6.0,
        })
        (self.project / persistence.STORE_PATH).unlink()
        project_scope.write(self.project / "READY_VIDEO_PLAN.json", ready_plan)
        project_scope.write(self.project / "MANIFESTO_MEDIA.json", ready_manifest)
        context = persistence.project_context(self.project)
        persistence.save_card_state(
            self.project, self.definition, ready_instance, self.catalog,
            expected_project_id=context["project_id"],
            expected_plan_revision=context["plan_revision"],
            expected_store_revision=None, base_revision=None,
        )
        plan_before = (self.project / "READY_VIDEO_PLAN.json").read_bytes()
        target = self.project / "ready-universal-layer.png"
        import fr_autoedite as fr
        ready_video.overlay_image(
            vars(fr), self.project, ready_plan["overlays"][0], 480, 854,
            {}, "fr_chiaroscuro_vintage_v1", target,
        )
        self.assertTrue(target.is_file())
        self.assertEqual((self.project / "READY_VIDEO_PLAN.json").read_bytes(), plan_before)
        self.assertEqual(hashlib.sha256(video.read_bytes()).hexdigest(), video_hash)
        self.assertEqual(
            runtime.universal_state_digest(self.project, "OV-UNIVERSAL"),
            ready_instance["state_digest"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
