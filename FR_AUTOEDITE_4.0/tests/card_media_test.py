#!/usr/bin/env python3
"""M3: mídia central F3/SERVICE, crop circular e validação de assets."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import card_media
import card_timeline
import fr_autoedite as fr
import master_contract
import project_scope
from studio import StudioState


class CardMediaContractTest(unittest.TestCase):
    def setUp(self):
        self.manifest = {
            "media": [
                {"id": "M0001", "status": "ok", "media_type": "image", "duration_sec": 0},
                {"id": "M0002", "status": "ok", "media_type": "video", "duration_sec": 3.0},
            ]
        }

    def test_asset_zoom_focal_and_service_only_validation(self):
        media = card_media.build_central_media("M0001", zoom=2, focal_x=0, focal_y=1)
        normalized = card_media.validate_central_media(media, self.manifest)
        self.assertEqual(normalized["shape"], "circle")
        self.assertEqual(normalized["crop"], "1:1")
        self.assertEqual(normalized["zoom"], 2.0)

        for changed, message in (
            ({**media, "central_asset_id": "M9999"}, "manifesto corrente"),
            ({**media, "shape": "square"}, "exigem circle"),
            ({**media, "zoom": 4.1}, "entre 1 e 4"),
            (card_media.build_central_media("M0002", frame_time_sec=3.5), "excede a mídia"),
        ):
            with self.assertRaisesRegex(card_media.CardMediaError, message):
                card_media.validate_central_media(changed, self.manifest)

        raw = {
            "segment_id": "S0001", "type": "card", "card_kind": "phase",
            "duration_sec": 1.0,
        }
        raw["card_instance"] = card_timeline.build_raw_card_instance(raw, 0)
        raw["card_instance"]["central_media"] = media
        with self.assertRaisesRegex(card_timeline.CardTimelineError, "F3/SERVICE"):
            card_timeline.validate_raw_card_instance(raw, 0, manifest=self.manifest)

    def test_horizontal_and_vertical_crop_preserve_square_circle_and_focal_point(self):
        landscape = Image.new("RGB", (400, 200), "#d51f1f")
        ImageDraw.Draw(landscape).rectangle((200, 0, 399, 199), fill="#1f36d5")
        left = card_media.circle_crop(landscape, 200, zoom=2, focal_x=0, focal_y=.5)
        right = card_media.circle_crop(landscape, 200, zoom=2, focal_x=1, focal_y=.5)
        self.assertEqual(left.size, (200, 200))
        self.assertEqual(left.getchannel("A").getbbox()[2:], right.getchannel("A").getbbox()[2:])
        self.assertGreater(left.getpixel((100, 100))[0], left.getpixel((100, 100))[2])
        self.assertGreater(right.getpixel((100, 100))[2], right.getpixel((100, 100))[0])
        self.assertEqual(left.getchannel("A").getpixel((0, 0)), 0)

        portrait = Image.new("RGB", (200, 400), "#20b05a")
        ImageDraw.Draw(portrait).rectangle((0, 200, 199, 399), fill="#e5ca28")
        top = card_media.circle_crop(portrait, 200, zoom=2, focal_x=.5, focal_y=0)
        bottom = card_media.circle_crop(portrait, 200, zoom=2, focal_x=.5, focal_y=1)
        self.assertGreater(top.getpixel((100, 100))[1], top.getpixel((100, 100))[0])
        self.assertGreater(bottom.getpixel((100, 100))[0], bottom.getpixel((100, 100))[2])


class CardMediaRendererTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="fr-card-media-")
        self.root = Path(self.temporary.name)
        self.state = StudioState(ROOT, self.root / "Studio")
        self.project = Path(self.state.create_project("M3 sintética")["path"])
        source = self.project / "originais" / "central.png"
        source.parent.mkdir(exist_ok=True)
        Image.new("RGB", (640, 320), "#c52f2f").save(source)
        self.manifest = {
            "schema_version": 3, "input_mode": "raw_media",
            "media": [{
                "id": "M0001", "status": "ok", "media_type": "image", "duration_sec": 0,
                "source_path": "originais/central.png", "proxy_path": "originais/central.png",
                "thumbnail_path": "", "width": 640, "height": 320, "has_audio": False,
            }],
        }
        project_scope.write(self.project / "MANIFESTO_MEDIA.json", self.manifest)
        self.segment = {
            "segment_id": "S0001", "type": "card", "enabled": True,
            "include_in": ["branded"], "card_kind": "service", "card_mode": "service",
            "service_key": "eletrica", "duration_sec": 1.0, "transition": "cut",
            "title": "ELÉTRICA", "body": "Instalação controlada.",
        }
        self.segment["card_instance"] = card_timeline.build_raw_card_instance(self.segment, 1)
        self.segment["card_instance"]["central_media"] = card_media.build_central_media(
            "M0001", zoom=1.4, focal_x=.25, focal_y=.5,
        )

    def tearDown(self):
        self.temporary.cleanup()

    def plan(self, width: int, height: int) -> dict:
        return {
            "contract_version": 2, "project": {"slug": self.project.name},
            "segments": [{
                "segment_id": "S0000", "type": "media", "enabled": True,
                "include_in": ["branded", "clean"], "media_id": "M0001",
                "start_sec": 0.0, "duration_sec": 0.5,
                "playback_speed": 1.0, "transition": "cut",
            }, copy.deepcopy(self.segment)],
            "output": {"width": width, "height": height, "fps": 24, "render_source": "originals"},
            "versions": {"branded": True, "clean": False},
            "audio": {"preserve_original": False},
            "visual_effects": {"transition_duration_sec": 0},
        }

    def test_round_trip_preview_invalidation_and_render_9_16_and_1_1(self):
        validated = master_contract.validate_plan(
            SimpleNamespace(**vars(fr)), self.plan(480, 854), self.manifest, "M3",
        )
        central = validated["segments"][1]["card_instance"]["central_media"]
        self.assertEqual(central["central_asset_id"], "M0001")

        style = fr.load_card_style()
        outputs = []
        for width, height in ((480, 854), (480, 480)):
            target = self.root / f"service-{width}x{height}.png"
            fr.card_image(target, validated["segments"][1], self.plan(width, height), fr.load_brand(), style, self.project)
            with Image.open(target) as rendered:
                self.assertEqual(rendered.size, (width, height))
                self.assertIsNotNone(rendered.getbbox())
            outputs.append(target.read_bytes())
        self.assertNotEqual(outputs[0], outputs[1])

        before = self.state._card_preview_state(validated["segments"][1])
        changed = copy.deepcopy(validated["segments"][1])
        changed["card_instance"]["central_media"]["focal_x"] = .9
        self.assertNotEqual(before, self.state._card_preview_state(changed))

        # Remoção posterior do arquivo não inventa mídia nem interrompe o
        # render: o fallback oficial do serviço permanece disponível.
        (self.project / "originais" / "central.png").unlink()
        fallback = self.root / "fallback.png"
        fr.card_image(fallback, validated["segments"][1], self.plan(480, 480), fr.load_brand(), style, self.project)
        self.assertTrue(fallback.is_file())

    def test_ready_video_keeps_locked_base_and_validates_same_asset_contract(self):
        ready_manifest = copy.deepcopy(self.manifest)
        ready_manifest["input_mode"] = "ready_video"
        ready_manifest["base_video_id"] = "READY_VIDEO_BASE"
        ready_manifest["media"].append({
            "id": "READY_VIDEO_BASE", "status": "ok", "media_type": "video",
            "duration_sec": 4.0,
        })
        overlay = {
            "overlay_id": "OV0001", "kind": "service_card", "start_sec": .5, "end_sec": 2.0,
            "text": "ELÉTRICA", "body": "Instalação controlada.", "service_key": "eletrica",
            "asset_id": "", "presentation": "overlay", "position": "center", "safe_area": "auto",
            "opacity": 1.0, "animation_in": "fade", "animation_out": "fade",
            "audio_policy": "preserve", "rationale": "",
        }
        overlay["card_instance"] = card_timeline.build_ready_card_instance(overlay)
        overlay["card_instance"]["central_media"] = card_media.build_central_media("M0001")
        plan = {
            "input_mode": "ready_video", "base_video_id": "READY_VIDEO_BASE",
            "timeline_locked": True, "allow_duration_extension": False,
            "style_pack_id": "fr_chiaroscuro_vintage_v1", "audio_policy": "preserve",
            "overlays": [overlay],
        }
        normalized, _ = master_contract.validate_ready_video_contract(
            SimpleNamespace(**vars(fr)), plan, ready_manifest,
        )
        self.assertTrue(normalized["timeline_locked"])
        self.assertEqual(normalized["overlays"][0]["card_instance"]["central_media"]["shape"], "circle")


if __name__ == "__main__":
    unittest.main(verbosity=2)
