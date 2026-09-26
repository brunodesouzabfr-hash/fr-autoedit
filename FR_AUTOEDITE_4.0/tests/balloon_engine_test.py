#!/usr/bin/env python3
"""M4: contrato, medida, safe area e colisões de balões/callouts."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import balloon_engine
import fr_autoedite as fr
from fr_v4.core.typography import TypographyError
from fr_v4.overlays import render_overlay
import master_contract
import ready_video


def contract(**changes):
    result = {
        "schema_version": 1, "role": "technical", "priority": 50,
        "padding": 0.032, "max_lines": 4, "easing": "ease_out",
        "reduced_motion": False, "avoid_subtitles": True, "avoid_subject": False,
    }
    result.update(changes)
    return result


def overlay(overlay_id="OV0001", **changes):
    result = {
        "overlay_id": overlay_id, "kind": "callout", "start_sec": 0.2, "end_sec": 2.2,
        "text": "Execução controlada com precisão", "body": "", "service_key": "eletrica",
        "asset_id": "", "presentation": "overlay", "position": "bottom_left",
        "safe_area": "title_safe", "opacity": 1.0,
        "animation_in": "fade", "animation_out": "fade",
        "audio_policy": "preserve", "rationale": "", "balloon": contract(),
    }
    result.update(changes)
    return result


class BalloonContractTest(unittest.TestCase):
    def setUp(self):
        self.manifest = {
            "input_mode": "ready_video", "base_video_id": "READY_VIDEO_BASE",
            "media": [{
                "id": "READY_VIDEO_BASE", "status": "ok", "media_type": "video",
                "duration_sec": 3.0, "width": 1080, "height": 1920,
            }],
        }
        self.plan = {
            "input_mode": "ready_video", "base_video_id": "READY_VIDEO_BASE",
            "timeline_locked": True, "allow_duration_extension": False,
            "style_pack_id": "fr_chiaroscuro_vintage_v1", "audio_policy": "preserve",
            "overlays": [overlay()],
        }

    def test_versioned_contract_is_strict_and_legacy_remains_legacy(self):
        normalized, notices = master_contract.validate_ready_video_contract(
            SimpleNamespace(**vars(fr)), self.plan, self.manifest,
        )
        item = normalized["overlays"][0]
        self.assertEqual(item["balloon"]["schema_version"], 1)
        self.assertEqual(item["balloon"]["priority"], 50)
        self.assertTrue(any(entry["block"].endswith("easing") for entry in notices))

        legacy = copy.deepcopy(self.plan)
        legacy["overlays"][0].pop("balloon")
        legacy_item, _ = master_contract.validate_ready_video_contract(
            SimpleNamespace(**vars(fr)), legacy, self.manifest,
        )
        self.assertNotIn("balloon", legacy_item["overlays"][0])
        legacy_image = render_overlay(legacy["overlays"][0], (1080, 1920), ROOT)
        self.assertEqual(legacy_image.size, (round(1080 * .72), round(1920 * .22)))
        legacy_image.close()

        for changed, message in (
            ({**contract(), "priority": True}, "inteiro"),
            ({**contract(), "padding": .2}, "entre"),
            ({**contract(), "unknown": 1}, "campos desconhecidos"),
        ):
            invalid = copy.deepcopy(self.plan)
            invalid["overlays"][0]["balloon"] = changed
            with self.assertRaisesRegex(fr.AutoEditeError, message):
                master_contract.validate_ready_video_contract(
                    SimpleNamespace(**vars(fr)), invalid, self.manifest,
                )

    def test_reduced_motion_and_subject_limit_are_explicit(self):
        changed = copy.deepcopy(self.plan)
        changed["overlays"][0]["balloon"] = contract(
            reduced_motion=True, avoid_subject=True,
        )
        normalized, notices = master_contract.validate_ready_video_contract(
            SimpleNamespace(**vars(fr)), changed, self.manifest,
        )
        item = normalized["overlays"][0]
        self.assertEqual(item["animation_in"], "none")
        self.assertEqual(item["animation_out"], "none")
        self.assertTrue(any("máscara de sujeito" in entry["message"] for entry in notices))


class BalloonLayoutTest(unittest.TestCase):
    def test_measured_text_accents_formats_and_no_silent_truncation(self):
        short = overlay(text="Prumo e nível")
        long = overlay(text="Instalação hidráulica revisada com pressão, vedação e alinhamento verificados.")
        for size in ((1080, 1920), (1080, 1080), (1920, 1080)):
            with self.subTest(size=size):
                short_metrics = balloon_engine.measure_balloon(short, size, ROOT)
                long_metrics = balloon_engine.measure_balloon(long, size, ROOT)
                self.assertGreaterEqual(long_metrics["height"], short_metrics["height"])
                self.assertLessEqual(long_metrics["width"], round(size[0] * (.80 if size[1] / size[0] >= 1.25 else .56 if size[0] / size[1] >= 1.25 else .72)))
                rendered = render_overlay(long, size, ROOT)
                self.assertEqual(rendered.size, (long_metrics["width"], long_metrics["height"]))
                self.assertIsNotNone(rendered.getbbox())
                rendered.close()

        too_long = overlay(text=" ".join(["conteúdo"] * 160), balloon=contract(max_lines=2))
        with self.assertRaises(TypographyError):
            balloon_engine.measure_balloon(too_long, (1080, 1920), ROOT)

    def test_caption_and_two_simultaneous_callouts_are_resolved_without_overlap(self):
        caption = overlay(
            "CAP0001", kind="caption", text="Legenda na região inferior", position="bottom_center",
            balloon=contract(role="caption", priority=100, max_lines=2),
        )
        first = overlay("OV0001", balloon=contract(priority=70))
        second = overlay("OV0002", text="Segunda nota técnica", balloon=contract(priority=60))
        resolved, notices = balloon_engine.resolve_collisions(
            [caption, first, second], (1080, 1920), ROOT,
        )
        callouts = [item for item in resolved if item["kind"] == "callout"]
        self.assertTrue(all(item.get("_resolved_position") for item in callouts))
        first_box, second_box = callouts[0]["_layout_bbox"], callouts[1]["_layout_bbox"]
        self.assertFalse(balloon_engine._intersects(tuple(first_box), tuple(second_box)))
        self.assertTrue(any("Posição resolvida" in item["message"] for item in notices))

    def test_unresolvable_layout_is_marked_for_review(self):
        rows = [
            overlay(
                f"OV{index:04d}", text="Nota técnica larga para ocupar a região disponível",
                balloon=contract(priority=100 - index),
            )
            for index in range(1, 10)
        ]
        resolved, notices = balloon_engine.resolve_collisions(rows, (480, 480), ROOT)
        self.assertTrue(any(item.get("_layout_review_required") for item in resolved))
        self.assertTrue(any("Nenhuma região livre" in item["message"] for item in notices))

    def test_safe_area_and_preview_master_layer_are_identical(self):
        with tempfile.TemporaryDirectory(prefix="fr-balloon-m4-") as folder:
            root = Path(folder)
            item = overlay(position="bottom_left")
            preview = root / "preview.png"
            master = root / "master.png"
            style = fr.load_card_style()
            for target in (preview, master):
                ready_video.overlay_image(
                    vars(fr), root, item, 1080, 1920, style,
                    "fr_chiaroscuro_vintage_v1", target,
                )
            self.assertEqual(hashlib.sha256(preview.read_bytes()).hexdigest(), hashlib.sha256(master.read_bytes()).hexdigest())
            with Image.open(preview) as image:
                bbox = image.getchannel("A").getbbox()
                margin = round(1080 * .10)
                self.assertGreaterEqual(bbox[0], margin)
                self.assertLessEqual(bbox[2], 1080 - margin)
                self.assertLessEqual(bbox[3], 1920 - margin)


if __name__ == "__main__":
    unittest.main(verbosity=2)
