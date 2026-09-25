#!/usr/bin/env python3
"""M2: placement de cards nos dois relógios sem migrar planos legados."""
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

import card_timeline
import fr_autoedite as fr
import project_scope
from studio import StudioError, StudioState


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RawCardTimelineTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="fr-card-timeline-")
        self.root = Path(self.temporary.name)
        self.state = StudioState(ROOT, self.root / "Studio")
        self.project = Path(self.state.create_project("Timeline M2 sintética")["path"])
        originals = self.project / "originais"
        originals.mkdir(exist_ok=True)
        self.sources = []
        for name, color in (("m1.png", (190, 25, 25)), ("m2.png", (25, 55, 190))):
            path = originals / name
            Image.new("RGB", (320, 240), color).save(path)
            self.sources.append(path)
        self.source_hashes = [sha256(path) for path in self.sources]
        self.manifest = {
            "schema_version": 2,
            "input_mode": "raw_media",
            "media": [
                {
                    "id": f"M000{index}", "status": "ok", "media_type": "image",
                    "duration_sec": 1.0, "source_path": f"originais/m{index}.png",
                    "proxy_path": f"originais/m{index}.png", "thumbnail_path": "",
                    "width": 320, "height": 240, "fps": 0, "has_audio": False,
                }
                for index in (1, 2)
            ],
        }
        project_scope.write(self.project / "MANIFESTO_MEDIA.json", self.manifest)
        config = self.state.load_config(self.project)
        config["edition"].update(
            width=320, height=240, format="horizontal", quality_preset="custom",
            fps=24, create_branded_version=True, create_clean_version=False,
            preserve_original_audio=False,
        )
        config["audio_design"].update(enable_sfx=False, tts_voiceover=False)
        config["export_quality"].update(video_crf=28, parallel_workers=1)
        project_scope.write(self.project / "QUESTIONARIO_RESPONDIDO.json", config)
        style = fr.load_card_style()
        style["logo"]["persistent_on_branded_video"] = False
        style["persistent_overlay"]["enabled"] = False
        style["cards"].update(always_generate_4k_masters=False, show_contacts_on_every_card=False)
        project_scope.write(self.project / "CARD_STYLE.json", style)

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def media(segment_id: str, media_id: str) -> dict:
        return {
            "segment_id": segment_id, "type": "media", "enabled": True,
            "include_in": ["branded", "clean"], "media_id": media_id,
            "start_sec": 0.0, "duration_sec": 0.5, "playback_speed": 1.0,
            "transition": "cut",
        }

    def base_plan(self) -> dict:
        return {
            "contract_version": 2,
            "project": {"slug": self.project.name, "name": "Timeline M2 sintética"},
            "segments": [self.media("S0001", "M0001"), self.media("S0002", "M0002")],
            "output": {"width": 320, "height": 240, "fps": 24, "render_source": "originals"},
            "versions": {"branded": True, "clean": False},
            "audio": {"preserve_original": False, "music_path": "", "music_volume": 0},
            "visual_effects": {"transition_duration_sec": 0, "speed_ramping": False},
        }

    def card(self, *, segment_id: str = "S0003", duration: float = 1.0, index: int = 1) -> dict:
        item = {
            "segment_id": segment_id, "type": "card", "enabled": True,
            "include_in": ["branded"], "card_kind": "phase",
            "duration_sec": duration, "transition": "cut",
            "title": "CARD M2", "body": "Placement sequencial verificável.",
        }
        item["card_instance"] = card_timeline.build_raw_card_instance(item, index)
        return item

    def test_raw_create_move_duration_template_remove_reload_and_original_hashes(self):
        baseline = self.state.save_plan(self.project, self.base_plan())["plan"]
        baseline_media = copy.deepcopy(baseline["segments"])
        edited = copy.deepcopy(baseline)
        edited["segments"].insert(1, self.card())
        saved = self.state.save_plan(self.project, edited)
        reloaded = fr.read_json(self.project / "EDIT_PLAN.json")
        self.assertEqual(saved["plan"], reloaded)
        self.assertEqual(reloaded["segments"][1]["card_instance"]["placement"], {
            "timebase": "raw_sequence", "sequence_index": 1, "duration_sec": 1.0,
        })
        self.assertEqual(
            [item for item in reloaded["segments"] if item["type"] == "media"],
            baseline_media,
        )

        moved = copy.deepcopy(reloaded)
        card = moved["segments"].pop(1)
        card["duration_sec"] = 0.75
        card["card_kind"] = "detail"
        moved["segments"].append(card)
        card["card_instance"] = card_timeline.build_raw_card_instance(card, 2)
        moved_result = self.state.save_plan(self.project, moved)
        self.assertEqual(moved_result["plan"]["segments"][2]["segment_id"], "S0003")
        self.assertEqual(moved_result["plan"]["segments"][2]["card_kind"], "detail")
        self.assertEqual(moved_result["plan"]["segments"][2]["duration_sec"], 0.75)

        invalid = copy.deepcopy(moved_result["plan"])
        invalid["segments"][2]["card_instance"]["placement"]["sequence_index"] = 1
        before_invalid = (self.project / "EDIT_PLAN.json").read_bytes()
        with self.assertRaisesRegex(StudioError, "ordem física"):
            self.state.save_plan(self.project, invalid)
        self.assertEqual((self.project / "EDIT_PLAN.json").read_bytes(), before_invalid)

        removed = copy.deepcopy(moved_result["plan"])
        removed["segments"] = [item for item in removed["segments"] if item["type"] == "media"]
        removed_result = self.state.save_plan(self.project, removed)
        self.assertEqual(removed_result["plan"]["segments"], baseline_media)
        self.assertEqual([sha256(path) for path in self.sources], self.source_hashes)
        self.assertGreaterEqual(len(list((self.project / "_HISTORICO").glob("EDIT_PLAN_*.json"))), 3)

    def test_legacy_fallback_and_affected_preview_invalidation(self):
        legacy = self.base_plan()
        legacy["segments"].insert(1, {key: value for key, value in self.card().items() if key != "card_instance"})
        saved = self.state.save_plan(self.project, legacy)["plan"]
        self.assertNotIn("card_instance", saved["segments"][1])

        namespace = self.project / "cards_editaveis" / self.project.name
        master = namespace / "4K_MASTERS"
        master.mkdir(parents=True)
        preview = namespace / "S0003.png"
        preview_4k = master / "S0003_4K.png"
        preview.write_bytes(b"synthetic-preview")
        preview_4k.write_bytes(b"synthetic-preview-4k")
        project_scope.write(self.project / "_CONTROLE" / "CARD_PREVIEWS.json", {
            "schema_version": 1,
            "previews": [
                {"relative": preview.relative_to(self.project).as_posix(), "segment_id": "S0003"},
                {"relative": preview_4k.relative_to(self.project).as_posix(), "segment_id": "S0003"},
            ],
        })

        duration_only = copy.deepcopy(saved)
        duration_only["segments"][1]["duration_sec"] = 1.25
        duration_only["segments"][1]["card_instance"] = card_timeline.build_raw_card_instance(
            duration_only["segments"][1], 1,
        )
        duration_result = self.state.save_plan(self.project, duration_only)
        self.assertEqual(duration_result["invalidated_card_ids"], [])
        self.assertTrue(preview.is_file())

        visual_change = copy.deepcopy(duration_result["plan"])
        visual_change["segments"][1]["card_kind"] = "detail"
        visual_change["segments"][1]["card_instance"] = card_timeline.build_raw_card_instance(
            visual_change["segments"][1], 1,
        )
        changed = self.state.save_plan(self.project, visual_change)
        self.assertEqual(changed["invalidated_card_ids"], ["S0003"])
        self.assertFalse(preview.exists())
        self.assertFalse(preview_4k.exists())

    def test_raw_render_observes_card_duration_and_sequence(self):
        plan = self.base_plan()
        plan["segments"].insert(1, self.card(duration=1.0))
        self.state.save_plan(self.project, plan)
        output = fr.render_plan(self.project, self.project / "EDIT_PLAN.json", only="branded")[0]
        parsed = fr.parse_probe(output, fr.ffprobe(output))
        self.assertAlmostEqual(parsed["duration_sec"], 2.0, delta=0.12)
        frames = []
        for seek in (0.25, 1.0, 1.75):
            target = self.root / f"frame-{seek}.png"
            fr.run([
                "ffmpeg", "-y", "-nostdin", "-loglevel", "error", "-ss", str(seek),
                "-i", str(output), "-frames:v", "1", str(target),
            ])
            with Image.open(target) as image:
                frames.append(image.convert("RGB").getpixel((160, 120)))
        self.assertGreater(frames[0][0], frames[0][2])
        self.assertNotEqual(frames[1], frames[0])
        self.assertGreater(frames[2][2], frames[2][0])
        self.assertEqual([sha256(path) for path in self.sources], self.source_hashes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
