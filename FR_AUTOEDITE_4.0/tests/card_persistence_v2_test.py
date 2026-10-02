#!/usr/bin/env python3
"""M9.5: persistência transacional e round-trip universal raw/ready."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "tests"))

import card_persistence_v2 as persistence  # noqa: E402
import card_state_v2 as cards  # noqa: E402
import card_state_v2_test as m91_fixture  # noqa: E402
import project_scope  # noqa: E402
import universal_card_renderer as renderer  # noqa: E402
import universal_card_renderer_test as m93_fixture  # noqa: E402


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class CardPersistenceV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        m91_fixture.CardStateV2Test.setUpClass()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="fr-m9-card-persistence-")
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name) / "project-a"
        self.project.mkdir()
        fixture = m91_fixture.CardStateV2Test(
            methodName="test_valid_definition_and_instance_preserve_all_fields_lines_unicode_and_newlines"
        )
        fixture.setUp()
        self.catalog = copy.deepcopy(fixture.catalog)
        self.definition = copy.deepcopy(fixture.definition)
        self.instance = copy.deepcopy(fixture.instance)
        self.instance["instance_id"] = "CARD-UNIVERSAL-001"
        self.instance["placement"] = {
            "timebase": "raw_sequence", "sequence_index": 1, "duration_sec": 3.5,
        }
        self.assets = self.project / "_ASSETS"
        self.assets.mkdir()
        self.background = self.assets / "background.png"
        self.logo = self.assets / "logo.png"
        self.visual = self.assets / "visual.png"
        Image.new("RGB", (941, 1672), "#0a2f26").save(self.background)
        Image.new("RGBA", (128, 128), (255, 210, 100, 220)).save(self.logo)
        Image.new("RGB", (640, 480), "#315a55").save(self.visual)
        self._bind_asset("synthetic_background", "component", self.background)
        self._bind_asset("synthetic_logo", "component", self.logo)
        self._bind_asset("synthetic_visual", "project_media", self.visual)
        self._redigest()
        self.raw_plan = {
            "contract_version": 2,
            "segments": [
                {
                    "segment_id": "S0000", "type": "media", "enabled": True,
                    "media_id": "M0001", "duration_sec": 1.0,
                },
                {
                    "segment_id": self.instance["instance_id"], "type": "card",
                    "enabled": True, "card_kind": "phase", "duration_sec": 3.5,
                    "title": "Card universal", "body": "Estado estruturado",
                },
            ],
        }
        self.manifest = {
            "input_mode": "raw_media",
            "media": [
                {
                    "id": "synthetic_visual", "media_type": "image", "status": "ok",
                    "source_path": self.visual.relative_to(self.project).as_posix(),
                    "sha256": sha256_file(self.visual),
                }
            ],
        }
        project_scope.write(self.project / "EDIT_PLAN.json", self.raw_plan)
        project_scope.write(self.project / "MANIFESTO_MEDIA.json", self.manifest)
        self.context = persistence.project_context(self.project)

    def _bind_asset(self, asset_id: str, scope: str, path: Path) -> None:
        digest = sha256_file(path)
        self.catalog[asset_id] = {
            "asset_id": asset_id, "scope": scope, "sha256": digest,
        }
        for state in (self.definition["default_state"], self.instance["state"]):
            for name in ("background", "logo", "visual"):
                ref = state["assets"].get(name)
                if isinstance(ref, dict) and ref.get("asset_id") == asset_id:
                    ref["scope"] = scope
                    ref["sha256"] = digest

    def _redigest(self) -> None:
        self.instance["state_digest"] = cards.renderable_state_digest(
            self.instance["definition_ref"], self.instance["state"],
            self.instance.get("service_key"),
        )

    def _save_first(self) -> dict:
        return persistence.save_card_state(
            self.project, self.definition, self.instance, self.catalog,
            expected_project_id=self.context["project_id"],
            expected_plan_revision=self.context["plan_revision"],
            expected_store_revision=None,
            base_revision=None,
        )

    def test_raw_save_reopen_is_canonical_and_never_mutates_plan_or_media(self):
        plan_before = (self.project / "EDIT_PLAN.json").read_bytes()
        media_before = self.visual.read_bytes()
        saved = self._save_first()
        store_path = self.project / persistence.STORE_PATH
        self.assertTrue(store_path.is_file())
        serialized = store_path.read_text(encoding="utf-8")
        self.assertNotIn(str(self.project), serialized)
        self.assertNotIn("source_path", serialized)
        self.assertNotIn("data:image", serialized.lower())
        self.assertTrue((self.project / "_ROTEIROS" / saved["rollback_version"]).is_dir())

        loaded = persistence.load_card_state(
            self.project, self.instance["instance_id"], self.catalog,
            expected_project_id=self.context["project_id"],
        )
        self.assertEqual(loaded["definition"], self.definition)
        self.assertEqual(loaded["instance"], self.instance)
        self.assertEqual(loaded["instance_revision"], saved["instance_revision"])
        self.assertEqual(len(loaded["instance"]["state"]["fields"]), 21)
        self.assertEqual(len(loaded["instance"]["state"]["lines"]), 29)
        self.assertEqual((self.project / "EDIT_PLAN.json").read_bytes(), plan_before)
        self.assertEqual(self.visual.read_bytes(), media_before)

    def test_update_creates_snapshots_and_rollback_restores_exact_state(self):
        first = self._save_first()
        first_store = (self.project / persistence.STORE_PATH).read_bytes()
        edited = copy.deepcopy(self.instance)
        title = next(row for row in edited["state"]["fields"] if row["id"] == "title")
        title["text"] = "ESTADO EDITADO — M9.5\nSEM PERDA"
        edited["state"]["assets"]["visualZoom"] = 2.2
        edited["state_digest"] = cards.renderable_state_digest(
            edited["definition_ref"], edited["state"], edited.get("service_key"),
        )
        second = persistence.save_card_state(
            self.project, self.definition, edited, self.catalog,
            expected_project_id=self.context["project_id"],
            expected_plan_revision=self.context["plan_revision"],
            expected_store_revision=first["store_revision"],
            base_revision=first["instance_revision"],
        )
        backup = self.project / "_ROTEIROS" / second["rollback_version"] / persistence.STORE_PATH
        self.assertEqual(backup.read_bytes(), first_store)
        store = project_scope.read(self.project / persistence.STORE_PATH)
        self.assertEqual(len(store["snapshots"]), 2)

        restored = persistence.rollback_card_state(
            self.project,
            self.instance["instance_id"],
            first["snapshot_digest"],
            self.catalog,
            expected_project_id=self.context["project_id"],
            expected_store_revision=second["store_revision"],
            expected_current_revision=second["instance_revision"],
        )
        self.assertEqual(restored["instance"], self.instance)
        reopened = persistence.load_card_state(
            self.project, self.instance["instance_id"], self.catalog,
            expected_project_id=self.context["project_id"],
        )
        self.assertEqual(reopened["instance"], self.instance)
        self.assertTrue(
            (self.project / "_ROTEIROS" / restored["rollback_version"] / persistence.STORE_PATH).is_file()
        )

    def test_stale_store_instance_and_plan_revisions_are_rejected_without_writes(self):
        first = self._save_first()
        store_path = self.project / persistence.STORE_PATH
        before = store_path.read_bytes()
        edited = copy.deepcopy(self.instance)
        edited["state"]["gridStyle"]["opacity"] = 0.4
        edited["state_digest"] = cards.renderable_state_digest(
            edited["definition_ref"], edited["state"], edited.get("service_key"),
        )
        cases = (
            {"expected_store_revision": "0" * 64, "base_revision": first["instance_revision"]},
            {"expected_store_revision": first["store_revision"], "base_revision": "0" * 64},
        )
        for arguments in cases:
            with self.subTest(arguments=arguments):
                with self.assertRaisesRegex(persistence.CardPersistenceV2Error, "revisão obsoleta"):
                    persistence.save_card_state(
                        self.project, self.definition, edited, self.catalog,
                        expected_project_id=self.context["project_id"],
                        expected_plan_revision=self.context["plan_revision"],
                        **arguments,
                    )
                self.assertEqual(store_path.read_bytes(), before)

        changed_plan = copy.deepcopy(self.raw_plan)
        changed_plan["segments"][0]["duration_sec"] = 1.1
        project_scope.write(self.project / "EDIT_PLAN.json", changed_plan)
        with self.assertRaisesRegex(persistence.CardPersistenceV2Error, "origem/revisão mudou"):
            persistence.load_card_state(
                self.project, self.instance["instance_id"], self.catalog,
                expected_project_id=self.context["project_id"],
            )
        self.assertEqual(store_path.read_bytes(), before)

    def test_project_switch_and_corrupt_store_are_rejected(self):
        self._save_first()
        project_b = Path(self.temporary.name) / "project-b"
        project_b.mkdir()
        shutil.copy2(self.project / "EDIT_PLAN.json", project_b / "EDIT_PLAN.json")
        shutil.copy2(self.project / "MANIFESTO_MEDIA.json", project_b / "MANIFESTO_MEDIA.json")
        (project_b / "_ASSETS").mkdir()
        shutil.copy2(self.visual, project_b / "_ASSETS" / "visual.png")
        context_b = persistence.project_context(project_b)
        self.assertNotEqual(context_b["project_id"], self.context["project_id"])
        with self.assertRaisesRegex(persistence.CardPersistenceV2Error, "outro projeto"):
            persistence.save_card_state(
                project_b, self.definition, self.instance, self.catalog,
                expected_project_id=self.context["project_id"],
                expected_plan_revision=context_b["plan_revision"],
                expected_store_revision=None, base_revision=None,
            )
        self.assertFalse((project_b / persistence.STORE_PATH).exists())

        store_path = self.project / persistence.STORE_PATH
        valid = project_scope.read(store_path)
        invalid = copy.deepcopy(valid)
        invalid["schema_version"] = 2
        project_scope.write(store_path, invalid)
        with self.assertRaisesRegex(persistence.CardPersistenceV2Error, "schema_version"):
            persistence.load_card_state(
                self.project, self.instance["instance_id"], self.catalog,
                expected_project_id=self.context["project_id"],
            )
        project_scope.write(store_path, valid)
        tampered = copy.deepcopy(valid)
        tampered["instances"][0]["state"]["fields"][0]["text"] = "alterado sem digest"
        project_scope.write(store_path, tampered)
        with self.assertRaisesRegex(persistence.CardPersistenceV2Error, "digest diverge"):
            persistence.load_card_state(
                self.project, self.instance["instance_id"], self.catalog,
                expected_project_id=self.context["project_id"],
            )

    def test_project_asset_origin_hash_and_bytes_are_manifest_driven(self):
        wrong_manifest = copy.deepcopy(self.manifest)
        wrong_manifest["media"][0]["sha256"] = "0" * 64
        project_scope.write(self.project / "MANIFESTO_MEDIA.json", wrong_manifest)
        context = persistence.project_context(self.project)
        with self.assertRaisesRegex(persistence.CardPersistenceV2Error, "MANIFESTO_MEDIA"):
            persistence.save_card_state(
                self.project, self.definition, self.instance, self.catalog,
                expected_project_id=context["project_id"],
                expected_plan_revision=context["plan_revision"],
                expected_store_revision=None, base_revision=None,
            )
        self.assertFalse((self.project / persistence.STORE_PATH).exists())

        project_scope.write(self.project / "MANIFESTO_MEDIA.json", self.manifest)
        with self.visual.open("ab") as handle:
            handle.write(b"m9-bytes-divergentes")
        context = persistence.project_context(self.project)
        with self.assertRaisesRegex(persistence.CardPersistenceV2Error, "bytes divergem"):
            persistence.save_card_state(
                self.project, self.definition, self.instance, self.catalog,
                expected_project_id=context["project_id"],
                expected_plan_revision=context["plan_revision"],
                expected_store_revision=None, base_revision=None,
            )

    def test_ready_video_round_trip_preserves_locked_base_and_overlay_clock(self):
        video = self.project / "_ORIGINAIS" / "base.mp4"
        video.parent.mkdir()
        video.write_bytes(b"synthetic-ready-video-base")
        ready_instance = copy.deepcopy(self.instance)
        ready_instance["instance_id"] = "OV-UNIVERSAL-001"
        ready_instance["placement"] = {
            "timebase": "ready_video_base", "start_sec": 1.25, "end_sec": 4.75,
        }
        ready_instance["state_digest"] = cards.renderable_state_digest(
            ready_instance["definition_ref"], ready_instance["state"],
        )
        ready_plan = {
            "input_mode": "ready_video",
            "base_video_id": "READY_VIDEO_BASE",
            "timeline_locked": True,
            "overlays": [
                {
                    "overlay_id": ready_instance["instance_id"], "kind": "common_card",
                    "start_sec": 1.25, "end_sec": 4.75,
                    "text": "Card", "body": "Ready",
                }
            ],
        }
        ready_manifest = copy.deepcopy(self.manifest)
        ready_manifest["input_mode"] = "ready_video"
        ready_manifest["base_video_id"] = "READY_VIDEO_BASE"
        ready_manifest["media"].append({
            "id": "READY_VIDEO_BASE", "media_type": "video", "status": "ok",
            "source_path": video.relative_to(self.project).as_posix(),
            "sha256": sha256_file(video), "duration_sec": 6.0,
        })
        project_scope.write(self.project / "READY_VIDEO_PLAN.json", ready_plan)
        project_scope.write(self.project / "MANIFESTO_MEDIA.json", ready_manifest)
        context = persistence.project_context(self.project)
        plan_before = (self.project / "READY_VIDEO_PLAN.json").read_bytes()
        video_before = video.read_bytes()
        result = persistence.save_card_state(
            self.project, self.definition, ready_instance, self.catalog,
            expected_project_id=context["project_id"],
            expected_plan_revision=context["plan_revision"],
            expected_store_revision=None, base_revision=None,
        )
        loaded = persistence.load_card_state(
            self.project, ready_instance["instance_id"], self.catalog,
            expected_project_id=context["project_id"],
        )
        self.assertEqual(loaded["instance"]["placement"], ready_instance["placement"])
        self.assertEqual(loaded["source"]["base_video_id"], "READY_VIDEO_BASE")
        self.assertTrue(loaded["source"]["timeline_locked"])
        self.assertEqual((self.project / "READY_VIDEO_PLAN.json").read_bytes(), plan_before)
        self.assertEqual(video.read_bytes(), video_before)
        self.assertIsNotNone(result["snapshot_digest"])

    @unittest.skipUnless(m93_fixture.local_suite_available(), "fontes M9.0 locais ausentes")
    def test_persisted_project_asset_renders_from_the_same_canonical_state(self):
        saved = self._save_first()
        sources = {
            "synthetic_background": self.background,
            "synthetic_logo": self.logo,
            "synthetic_visual": self.visual,
        }
        direct = renderer.render_universal_card(
            self.definition, self.instance, self.catalog, sources,
            m93_fixture.FONT_ROOT, output_size=(941, 1672),
        )
        reopened = persistence.render_persisted_card(
            self.project, self.instance["instance_id"], self.catalog, sources,
            m93_fixture.FONT_ROOT,
            expected_project_id=self.context["project_id"],
            usage_context="local_authorized", output_size=(941, 1672),
        )
        self.assertEqual(reopened.sha256, direct.sha256)
        self.assertEqual(reopened.state_digest, self.instance["state_digest"])
        self.assertEqual(saved["instance_revision"], cards.instance_revision(self.instance))


class CardPersistenceServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not m93_fixture.local_suite_available():
            raise unittest.SkipTest("assets/fontes M9.0 locais ausentes")
        m93_fixture.UniversalCardRendererGoldenTest.setUpClass()
        cls.fixture = m93_fixture.UniversalCardRendererGoldenTest

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "fixture"):
            cls.fixture.tearDownClass()

    def test_service_round_trip_uses_manifest_and_blocks_external_render(self):
        temporary = tempfile.TemporaryDirectory(prefix="fr-m9-service-persistence-")
        self.addCleanup(temporary.cleanup)
        project = Path(temporary.name)
        instance = self.fixture.instance("service_alvenaria")
        plan = {
            "segments": [{
                "segment_id": instance["instance_id"], "type": "card",
                "card_kind": "service", "service_key": "alvenaria",
                "duration_sec": instance["placement"]["duration_sec"],
            }]
        }
        manifest = {"input_mode": "raw_media", "media": []}
        project_scope.write(project / "EDIT_PLAN.json", plan)
        project_scope.write(project / "MANIFESTO_MEDIA.json", manifest)
        context = persistence.project_context(project)
        saved = persistence.save_card_state(
            project, self.fixture.definition, instance, self.fixture.catalog,
            expected_project_id=context["project_id"],
            expected_plan_revision=context["plan_revision"],
            expected_store_revision=None, base_revision=None,
            usage_context="local_authorized",
        )
        serialized = (project / persistence.STORE_PATH).read_text(encoding="utf-8")
        self.assertIn('"asset_id": "medallion_alvenaria"', serialized)
        self.assertNotIn("assets/service-medallions", serialized)
        result = persistence.render_persisted_card(
            project, instance["instance_id"], self.fixture.catalog, self.fixture.sources,
            m93_fixture.FONT_ROOT,
            expected_project_id=context["project_id"],
            usage_context="local_authorized", output_size=(941, 1672),
        )
        self.assertTrue(result.report["visual_review_required"])
        self.assertEqual(result.report["asset_reviews"][0]["service_key"], "alvenaria")
        self.assertEqual(saved["instance_revision"], cards.instance_revision(instance))
        with self.assertRaisesRegex(persistence.CardPersistenceV2Error, "bloqueado"):
            persistence.load_card_state(
                project, instance["instance_id"], self.fixture.catalog,
                expected_project_id=context["project_id"],
                usage_context="external_distribution",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
