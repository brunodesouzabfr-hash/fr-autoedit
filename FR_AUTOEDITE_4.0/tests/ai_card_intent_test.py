#!/usr/bin/env python3
"""M5: intenção assistida validada, confirmada e reversível."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import ai_card_intent
import card_media
import card_timeline
import project_scope
from studio import StudioError, StudioState


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def provenance():
    return {"provider": "fake-local", "model": "fixture-v1", "request_id": "REQ0001"}


class AiCardIntentRawTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="fr-ai-card-m5-")
        self.root = Path(self.temporary.name)
        self.state = StudioState(ROOT, self.root / "Studio")
        self.project = Path(self.state.create_project("M5 raw sintético")["path"])
        source = self.project / "originais" / "m5.png"
        source.parent.mkdir(exist_ok=True)
        Image.new("RGB", (640, 480), "#315a55").save(source)
        self.source = source
        self.source_hash = sha256(source)
        self.manifest = {
            "schema_version": 3, "input_mode": "raw_media",
            "media": [{
                "id": "M0001", "status": "ok", "media_type": "image", "duration_sec": 0,
                "source_path": "originais/m5.png", "proxy_path": "originais/m5.png",
                "thumbnail_path": "", "width": 640, "height": 480, "has_audio": False,
            }],
        }
        card = {
            "segment_id": "S0001", "type": "card", "enabled": True,
            "include_in": ["branded"], "card_kind": "service", "card_mode": "service",
            "service_key": "eletrica", "duration_sec": 1.0, "transition": "cut",
            "title": "ELÉTRICA", "body": "Execução controlada.",
        }
        card["card_instance"] = card_timeline.build_raw_card_instance(card, 1)
        self.plan = {
            "contract_version": 2, "project": {"slug": self.project.name},
            "segments": [{
                "segment_id": "S0000", "type": "media", "enabled": True,
                "include_in": ["branded", "clean"], "media_id": "M0001",
                "start_sec": 0.0, "duration_sec": .5, "playback_speed": 1.0,
                "transition": "cut",
            }, card],
            "output": {"width": 480, "height": 854, "fps": 24, "render_source": "originals"},
            "versions": {"branded": True, "clean": False},
            "audio": {"preserve_original": False}, "visual_effects": {"transition_duration_sec": 0},
        }
        project_scope.write(self.project / "MANIFESTO_MEDIA.json", self.manifest)
        project_scope.write(self.project / "EDIT_PLAN.json", self.plan)
        project_scope.write(self.project / "_EDITAR" / "02_PLANO_DA_EDICAO.json", self.plan)

    def tearDown(self):
        self.temporary.cleanup()

    def intent(self, **changes):
        body = changes.pop("body", "Pressão verificada em 3 bar")
        payload = {
            "schema_version": 1, "intent_id": "INTENT0001",
            "base_revision": ai_card_intent.current_revision(self.project),
            "input_mode": "raw_media", "target_id": "S0001", "origin": "ai_assisted",
            "changes": {
                "title": "ELÉTRICA REVISADA", "body": body, "duration_sec": 1.2,
                "card_kind": "service", "service_key": "eletrica",
                "central_media": card_media.build_central_media(
                    "M0001", zoom=1.2, focal_x=.4, focal_y=.6,
                ),
                **changes,
            },
            "claims": [{
                "claim_id": "CLM0001", "text": "Pressão verificada em 3 bar",
                "evidence_ids": ["EVD0001"],
            }] if "3 bar" in body else [],
            "evidence": [{
                "evidence_id": "EVD0001", "kind": "user_provided", "media_id": "",
                "source": "Ficha técnica fornecida pelo usuário",
                "description": "Medição declarada de 3 bar.",
            }] if "3 bar" in body else [],
            "provenance": provenance(),
        }
        return payload

    def test_review_has_no_writes_apply_requires_confirmation_and_revert_restores(self):
        before = project_scope.read(self.project / "EDIT_PLAN.json")
        review = self.state.review_ai_card_intent(self.project, self.intent())
        self.assertTrue(review["valid"])
        self.assertTrue(review["requires_confirmation"])
        self.assertTrue(review["diff"])
        self.assertEqual(project_scope.read(self.project / "EDIT_PLAN.json"), before)
        self.assertEqual(sha256(self.source), self.source_hash)

        with self.assertRaisesRegex(StudioError, "confirmação explícita"):
            self.state.apply_ai_card_intent(
                self.project, self.intent(), confirmed=False,
                confirmation_token=review["confirmation_token"],
            )
        self.assertEqual(project_scope.read(self.project / "EDIT_PLAN.json"), before)

        applied = self.state.apply_ai_card_intent(
            self.project, self.intent(), confirmed=True,
            confirmation_token=review["confirmation_token"],
        )
        saved = project_scope.read(self.project / "EDIT_PLAN.json")
        card = saved["segments"][1]
        self.assertEqual(card["title"], "ELÉTRICA REVISADA")
        self.assertEqual(card["card_instance"]["edit_origin"], "ai_assisted")
        self.assertEqual(card["card_instance"]["central_media"]["central_asset_id"], "M0001")
        self.assertEqual(sha256(self.source), self.source_hash)
        self.assertTrue((self.project / "_ROTEIROS" / applied["operation"]["rollback_version"]).is_dir())

        self.state.revert_ai_card_intent(self.project, applied["operation"]["operation_id"])
        self.assertEqual(project_scope.read(self.project / "EDIT_PLAN.json"), before)
        self.assertEqual(sha256(self.source), self.source_hash)

    def test_invalid_asset_time_marker_stale_and_render3d_only_never_mutate(self):
        before = project_scope.read(self.project / "EDIT_PLAN.json")
        invalid_cases = []
        bad_asset = self.intent()
        bad_asset["changes"]["central_media"]["central_asset_id"] = "M9999"
        invalid_cases.append((bad_asset, "contract_rejected"))
        bad_duration = self.intent(duration_sec=-1)
        invalid_cases.append((bad_duration, "out_of_range"))
        marker = self.intent(body="[DADO A CONFIRMAR] pressão")
        invalid_cases.append((marker, "unconfirmed_content"))
        stale = self.intent()
        stale["base_revision"] = "0" * 64
        invalid_cases.append((stale, "stale_revision"))
        unsupported = self.intent()
        unsupported["changes"]["geometry"] = {"x": 1}
        invalid_cases.append((unsupported, "unsupported_field"))
        render_only = self.intent()
        render_only["evidence"] = [{
            "evidence_id": "EVD0001", "kind": "render_3d", "media_id": "M0001",
            "source": "Imagem 3D", "description": "Referência visual de projeto.",
        }]
        invalid_cases.append((render_only, "insufficient_evidence"))
        for payload, code in invalid_cases:
            with self.subTest(code=code), self.assertRaises(ai_card_intent.AiCardIntentError) as captured:
                ai_card_intent.review_intent(__import__("fr_autoedite").__dict__, self.project, payload)
            self.assertEqual(captured.exception.code, code)
            self.assertEqual(project_scope.read(self.project / "EDIT_PLAN.json"), before)
            self.assertEqual(sha256(self.source), self.source_hash)

    def test_fake_provider_receives_no_paths_or_write_capability(self):
        request = ai_card_intent.build_provider_request(self.project, "S0001", "Revisar conteúdo")
        serialized = repr(request)
        self.assertNotIn(str(self.project), serialized)
        self.assertNotIn("source_path", serialized)
        self.assertIn("filesystem", request["capabilities"]["unsupported"])

        def provider(snapshot):
            self.assertEqual(snapshot["required_output"], "AI_CARD_INTENT")
            result = self.intent(body="Execução revisada")
            result["base_revision"] = snapshot["base_revision"]
            return result

        proposed = ai_card_intent.request_provider_intent(provider, request)
        review = self.state.review_ai_card_intent(self.project, proposed)
        self.assertTrue(review["valid"])


class AiCardIntentReadyTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="fr-ai-ready-m5-")
        self.root = Path(self.temporary.name)
        self.state = StudioState(ROOT, self.root / "Studio")
        self.project = Path(self.state.create_project("M5 ready sintético")["path"])
        base = self.project / "_ENTRADA" / "VIDEO_PRONTO_ORIGINAL.mp4"
        base.parent.mkdir(exist_ok=True)
        base.write_bytes(b"synthetic-ready-base-do-not-edit")
        image = self.project / "originais" / "central.png"
        image.parent.mkdir(exist_ok=True)
        Image.new("RGB", (320, 240), "#854321").save(image)
        self.base = base
        self.base_hash = sha256(base)
        self.manifest = {
            "input_mode": "ready_video", "base_video_id": "READY_VIDEO_BASE",
            "media": [
                {"id": "READY_VIDEO_BASE", "status": "ok", "media_type": "video", "duration_sec": 3.0,
                 "source_path": "_ENTRADA/VIDEO_PRONTO_ORIGINAL.mp4"},
                {"id": "M0001", "status": "ok", "media_type": "image", "duration_sec": 0,
                 "source_path": "originais/central.png"},
            ],
        }
        card = {
            "overlay_id": "OV0001", "kind": "service_card", "start_sec": .4, "end_sec": 1.8,
            "text": "ELÉTRICA", "body": "Execução controlada", "service_key": "eletrica",
            "asset_id": "", "presentation": "overlay", "position": "center", "safe_area": "auto",
            "opacity": 1.0, "animation_in": "fade", "animation_out": "fade",
            "audio_policy": "preserve", "rationale": "",
        }
        card["card_instance"] = card_timeline.build_ready_card_instance(card)
        self.plan = {
            "input_mode": "ready_video", "base_video_id": "READY_VIDEO_BASE", "timeline_locked": True,
            "allow_duration_extension": False, "style_pack_id": "fr_chiaroscuro_vintage_v1",
            "audio_policy": "preserve", "overlays": [card],
        }
        project_scope.write(self.project / "MANIFESTO_MEDIA.json", self.manifest)
        project_scope.write(self.project / "READY_VIDEO_PLAN.json", self.plan)

    def tearDown(self):
        self.temporary.cleanup()

    def intent(self, **changes):
        return {
            "schema_version": 1, "intent_id": "READYINTENT1",
            "base_revision": ai_card_intent.current_revision(self.project),
            "input_mode": "ready_video", "target_id": "OV0001", "origin": "ai_assisted",
            "changes": {
                "text": "ELÉTRICA READY", "body": "Execução revisada",
                "kind": "service_card", "service_key": "eletrica",
                "start_sec": .6, "end_sec": 2.0,
                "central_media": card_media.build_central_media("M0001"), **changes,
            },
            "claims": [], "evidence": [], "provenance": provenance(),
        }

    def test_ready_applies_overlay_only_and_rejects_invalid_base_clock(self):
        before = project_scope.read(self.project / "READY_VIDEO_PLAN.json")
        invalid = self.intent(end_sec=4.0)
        with self.assertRaises(ai_card_intent.AiCardIntentError) as captured:
            ai_card_intent.review_intent(__import__("fr_autoedite").__dict__, self.project, invalid)
        self.assertEqual(captured.exception.code, "contract_rejected")
        self.assertEqual(project_scope.read(self.project / "READY_VIDEO_PLAN.json"), before)
        self.assertEqual(sha256(self.base), self.base_hash)

        intent = self.intent()
        review = self.state.review_ai_card_intent(self.project, intent)
        applied = self.state.apply_ai_card_intent(
            self.project, intent, confirmed=True,
            confirmation_token=review["confirmation_token"],
        )
        saved = project_scope.read(self.project / "READY_VIDEO_PLAN.json")
        self.assertTrue(saved["timeline_locked"])
        self.assertEqual(saved["base_video_id"], "READY_VIDEO_BASE")
        self.assertEqual(saved["overlays"][0]["start_sec"], .6)
        self.assertEqual(saved["overlays"][0]["card_instance"]["edit_origin"], "ai_assisted")
        self.assertEqual(sha256(self.base), self.base_hash)
        self.state.revert_ai_card_intent(self.project, applied["operation"]["operation_id"])
        self.assertEqual(project_scope.read(self.project / "READY_VIDEO_PLAN.json"), before)
        self.assertEqual(sha256(self.base), self.base_hash)


if __name__ == "__main__":
    unittest.main(verbosity=2)
