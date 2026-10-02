#!/usr/bin/env python3
"""M9.9: ativação, migração, edição, fallback, rollback e render universal."""
from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import card_migration_v99 as migration  # noqa: E402
import card_persistence_v2 as persistence  # noqa: E402
import fr_autoedite as fr  # noqa: E402
import project_scope  # noqa: E402
from studio import StudioState  # noqa: E402
import universal_card_runtime as runtime  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class UniversalCardActivationMigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.editor_root = runtime.discover_component(ROOT)
        cls.font_root = runtime.discover_font_root(ROOT, cls.editor_root)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="fr-m99-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.studio = StudioState(ROOT, self.root / "Studio")
        self.project = Path(self.studio.create_project("M9.9 sintético")["path"])
        source = self.project / "originais" / "central.png"
        source.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (640, 480), "#7a351c").save(source)
        self.source = source
        self.manifest = {
            "schema_version": 2,
            "input_mode": "raw_media",
            "media": [{
                "id": "M0001", "status": "ok", "media_type": "image",
                "source_path": "originais/central.png", "sha256": sha256(source),
                "duration_sec": 0, "width": 640, "height": 480,
                "has_audio": False,
            }],
        }
        self.plan = {
            "schema_version": 3,
            "project": {"slug": self.project.name, "name": "M9.9 sintético"},
            "output": {"width": 480, "height": 854, "fps": 24},
            "segments": [
                {
                    "segment_id": "S0001", "type": "card", "enabled": True,
                    "card_kind": "intro", "title": "ABERTURA ANTIGA",
                    "body": "Texto preservado integralmente.", "duration_sec": 2.5,
                    "phase_order": 0, "transition": "fade",
                },
                {
                    "segment_id": "S0002", "type": "card", "enabled": True,
                    "card_kind": "service", "service_key": "pintura",
                    "title": "PINTURA", "body": "Acabamento existente.",
                    "duration_sec": 3.25, "phase_order": 1, "transition": "cut",
                    "card_instance": {
                        "schema_version": 1, "instance_id": "S0002",
                        "definition_id": "raw/service", "definition_version": 1,
                        "edit_origin": "manual",
                        "placement": {
                            "timebase": "raw_sequence", "sequence_index": 1,
                            "duration_sec": 3.25,
                        },
                        "central_media": {
                            "schema_version": 1, "central_asset_id": "M0001",
                            "shape": "circle", "crop": "1:1", "zoom": 1.5,
                            "focal_x": 0.25, "focal_y": 0.75,
                        },
                    },
                },
            ],
        }
        project_scope.write(self.project / "MANIFESTO_MEDIA.json", self.manifest)
        project_scope.write(self.project / "EDIT_PLAN.json", self.plan)

    def test_first_studio_open_migrates_every_raw_card_idempotently_and_rolls_back(self):
        plan_before = (self.project / "EDIT_PLAN.json").read_bytes()
        media_before = self.source.read_bytes()
        state = self.studio.project_state(self.project)
        report = state["card_migration"]
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["counts"], {"discovered": 2, "migrated": 2, "fallback": 0})
        self.assertEqual(
            {row["instance_id"] for row in state["universal_cards"]},
            {"S0001", "S0002"},
        )
        self.assertTrue(all(row["renderer_id"] == "fr-universal-card" for row in report["cards"]))
        self.assertEqual((self.project / "EDIT_PLAN.json").read_bytes(), plan_before)
        self.assertEqual(self.source.read_bytes(), media_before)
        store_before = (self.project / persistence.STORE_PATH).read_bytes()
        previews_before = {
            row["relative"]: (self.project / row["relative"]).read_bytes()
            for row in report["previews"]["regenerated"]
        }

        again = runtime.activate_project_cards(self.project, app_root=ROOT)
        self.assertTrue(again["idempotent"])
        self.assertEqual(again["rollback_version"], report["rollback_version"])
        self.assertEqual((self.project / persistence.STORE_PATH).read_bytes(), store_before)
        self.assertEqual(
            {name: (self.project / name).read_bytes() for name in previews_before},
            previews_before,
        )

        loaded = persistence.load_card_state(
            self.project, "S0002", runtime.build_asset_context(
                self.project, self.editor_root,
            )[0], expected_project_id=report["project_id"],
        )
        self.assertEqual(loaded["instance"]["placement"]["duration_sec"], 3.25)
        self.assertEqual(loaded["instance"]["state"]["assets"]["visual"]["asset_id"], "M0001")
        self.assertEqual(loaded["instance"]["state"]["assets"]["visualZoom"], 1.5)
        title = next(row for row in loaded["instance"]["state"]["fields"] if row["id"] == "title")
        self.assertEqual(title["text"], "PINTURA")

        rendered = self.project / "m99-master-route.png"
        self.assertTrue(runtime.render_timeline_card(
            self.project, "S0001", rendered, (480, 854), app_root=ROOT,
        ))
        self.assertTrue(rendered.is_file())

        parallel_targets = [
            self.project / "m99-parallel-S0001.png",
            self.project / "m99-parallel-S0002.png",
        ]
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(
                    runtime.render_timeline_card,
                    self.project,
                    instance_id,
                    target,
                    (480, 854),
                    app_root=ROOT,
                )
                for instance_id, target in zip(
                    ("S0001", "S0002"), parallel_targets, strict=True,
                )
            ]
            self.assertEqual([future.result() for future in futures], [True, True])
        self.assertTrue(all(target.is_file() for target in parallel_targets))

        derived = {
            "segments": [{
                "segment_id": "S9001", "type": "card", "card_kind": "intro",
                "title": "REEL DERIVADO", "body": "Fallback nominal.",
                "duration_sec": 1.5,
            }],
        }
        registered = runtime.register_derived_plan_fallbacks(
            self.project, derived, plan_label="social/planos/REEL_8S.json",
        )
        route = next(
            row for row in registered["cards"] if row["instance_id"] == "S9001"
        )
        self.assertEqual(route["renderer_id"], "fr-v4-f1-f6")
        self.assertTrue(route["fallback"]["registered"])
        self.assertIn("REEL_8S.json", route["fallback"]["reason"])
        self.assertFalse(runtime.render_timeline_card(
            self.project, "S9001", self.project / "derived-fallback.png",
            (480, 854), app_root=ROOT,
        ))

        style = fr.load_card_style(self.project)
        style["cards"]["always_generate_4k_masters"] = False
        project_scope.write(self.project / "CARD_STYLE.json", style)
        with (
            patch("fr_autoedite.card_image", side_effect=AssertionError(
                "preview de card migrado tentou usar o renderer legado",
            )),
            patch("universal_card_runtime.persistence.render_persisted_card", side_effect=AssertionError(
                "preview universal já validado foi renderizado uma segunda vez",
            )),
        ):
            previews = fr.generate_card_previews(
                self.project, self.project / "EDIT_PLAN.json",
            )
        self.assertEqual(len(previews), 2)
        self.assertTrue(all(path.is_file() for path in previews))

        rollback = runtime.rollback_project_card_activation(
            self.project, report["rollback_version"],
        )
        self.assertTrue(rollback["card_activation_rolled_back"])
        self.assertFalse((self.project / persistence.STORE_PATH).exists())
        self.assertFalse((self.project / migration.REPORT_PATH).exists())
        self.assertEqual((self.project / "EDIT_PLAN.json").read_bytes(), plan_before)
        self.assertEqual(self.source.read_bytes(), media_before)

    def test_editor_persists_text_background_central_crop_and_reopens_same_state(self):
        report = runtime.activate_project_cards(self.project, app_root=ROOT)
        binding = lambda asset_id: "/asset/" + asset_id
        opened = runtime.open_editor_session(
            self.project, "S0002", expected_project_id=report["project_id"],
            editor_root=self.editor_root, binding_builder=binding,
        )
        session = copy.deepcopy(opened["session"])
        source_background = next(
            row for row in opened["asset_options"]
            if row["asset_id"] == "component/background-fr-source"
        )
        session["asset_refs"]["background"] = {
            key: source_background[key] for key in ("scope", "asset_id", "sha256")
        }
        session["editor_state"]["assets"]["background"] = source_background["binding"]
        session["editor_state"]["assets"].update({
            "visualShape": "rounded", "visualZoom": 2.25,
            "visualFocalX": 63, "visualFocalY": 31,
        })
        next(row for row in session["editor_state"]["fields"] if row["id"] == "title")["text"] = "PINTURA EDITADA"
        before_preview = next(
            row for row in report["previews"]["regenerated"] if row["segment_id"] == "S0002"
        )["sha256"]
        saved = runtime.save_editor_session(
            self.project, session, expected_project_id=report["project_id"],
            editor_root=self.editor_root, binding_builder=binding, font_root=self.font_root,
        )
        self.assertNotEqual(saved["renderer_sha256"], before_preview)
        reopened = runtime.open_editor_session(
            self.project, "S0002", expected_project_id=report["project_id"],
            editor_root=self.editor_root, binding_builder=binding,
        )
        state = reopened["session"]["editor_state"]
        self.assertEqual(state["assets"]["background"], source_background["binding"])
        self.assertEqual(state["assets"]["visual"], "/asset/M0001")
        self.assertEqual(state["assets"]["visualShape"], "rounded")
        self.assertEqual(state["assets"]["visualZoom"], 2.25)
        self.assertEqual(state["assets"]["visualFocalX"], 63)
        self.assertEqual(state["assets"]["visualFocalY"], 31)
        self.assertEqual(
            next(row for row in state["fields"] if row["id"] == "title")["text"],
            "PINTURA EDITADA",
        )
        current_report = runtime.migration_report(self.project)
        migrated = next(row for row in current_report["cards"] if row["instance_id"] == "S0002")
        self.assertEqual(migrated["state_digest"], saved["instance"]["state_digest"])

    def test_ready_video_is_preserved_and_unconvertible_card_gets_only_explicit_fallback(self):
        base = self.project / "originais" / "ready.mp4"
        base.write_bytes(b"synthetic-ready-video-bytes")
        base_hash = sha256(base)
        manifest = {
            "schema_version": 2, "input_mode": "ready_video",
            "media": [{
                "id": "READY_VIDEO_BASE", "status": "ok", "media_type": "video",
                "source_path": "originais/ready.mp4", "sha256": base_hash,
                "duration_sec": 10, "width": 1080, "height": 1920,
                "fps": 24, "has_audio": True,
            }],
        }
        plan = {
            "input_mode": "ready_video", "base_video_id": "READY_VIDEO_BASE",
            "timeline_locked": True, "allow_duration_extension": False,
            "overlays": [
                {
                    "overlay_id": "OV0001", "kind": "common_card",
                    "start_sec": 1.25, "end_sec": 4.75,
                    "text": "READY ANTIGO", "body": "Janela preservada.",
                    "asset_id": "", "position": "bottom_left",
                    "animation_in": "fade", "animation_out": "soft_scale",
                },
                {
                    "overlay_id": "OV0002", "kind": "common_card",
                    "start_sec": 5, "end_sec": 7, "text": "INCONVERSÍVEL",
                    "body": "Asset fora do manifesto.", "asset_id": "slot-nao-instalado",
                },
            ],
        }
        project_scope.write(self.project / "MANIFESTO_MEDIA.json", manifest)
        project_scope.write(self.project / "READY_VIDEO_PLAN.json", plan)
        (self.project / "EDIT_PLAN.json").unlink(missing_ok=True)
        plan_before = (self.project / "READY_VIDEO_PLAN.json").read_bytes()

        report = runtime.activate_project_cards(self.project, app_root=ROOT)
        self.assertEqual(report["counts"], {"discovered": 2, "migrated": 1, "fallback": 1})
        fallback = next(row for row in report["cards"] if row["instance_id"] == "OV0002")
        self.assertEqual(fallback["renderer_id"], "fr-v4-f1-f6")
        self.assertTrue(fallback["fallback"]["registered"])
        self.assertIn("asset_id não existe", fallback["fallback"]["reason"])
        self.assertFalse(runtime.render_timeline_card(
            self.project, "OV0002", self.project / "fallback.png", (480, 854), app_root=ROOT,
        ))
        with self.assertRaisesRegex(runtime.UniversalCardRuntimeError, "fallback silencioso"):
            runtime.render_timeline_card(
                self.project, "NAO-REGISTRADO", self.project / "forbidden.png",
                (480, 854), app_root=ROOT,
            )
        loaded = persistence.load_card_state(
            self.project, "OV0001", runtime.build_asset_context(
                self.project, self.editor_root,
            )[0], expected_project_id=report["project_id"],
        )
        self.assertEqual(loaded["instance"]["placement"], {
            "timebase": "ready_video_base", "start_sec": 1.25, "end_sec": 4.75,
        })
        self.assertEqual((self.project / "READY_VIDEO_PLAN.json").read_bytes(), plan_before)
        self.assertEqual(sha256(base), base_hash)


if __name__ == "__main__":
    unittest.main(verbosity=2)
