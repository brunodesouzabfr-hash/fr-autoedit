#!/usr/bin/env python3
"""M9.6: CARD_EDIT_INTENT v2 declarativo, confirmado e reversível."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "tests"))

import card_edit_intent_v2 as intents  # noqa: E402
import card_persistence_v2 as persistence  # noqa: E402
import card_persistence_v2_test as persistence_fixture  # noqa: E402
import card_state_v2 as cards  # noqa: E402
import project_scope  # noqa: E402


class CardEditIntentV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        persistence_fixture.CardPersistenceV2Test.setUpClass()

    def setUp(self):
        fixture = persistence_fixture.CardPersistenceV2Test(
            methodName="test_raw_save_reopen_is_canonical_and_never_mutates_plan_or_media"
        )
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        for name in (
            "project", "catalog", "definition", "instance", "context", "visual",
            "raw_plan", "manifest",
        ):
            setattr(self, name, getattr(fixture, name))
        self.saved = fixture._save_first()

    def request(self, task: str = "Ajuste o texto e a composição sem inventar fatos") -> dict:
        return intents.build_provider_request(
            self.project,
            self.instance["instance_id"],
            self.catalog,
            expected_project_id=self.context["project_id"],
            task=task,
        )

    def intent(self, operations: list[dict] | None = None) -> dict:
        request = self.request()
        return {
            "schema_version": 2,
            "kind": "CARD_EDIT_INTENT",
            "intent_id": "INTENT-M9-6-001",
            "origin": "ai_assisted",
            "project_id": request["project_id"],
            "target_id": request["target_id"],
            "input_mode": request["input_mode"],
            "base_plan_revision": request["base_plan_revision"],
            "base_store_revision": request["base_store_revision"],
            "base_instance_revision": request["base_instance_revision"],
            "operations": operations or [
                {
                    "operation_id": "OP-TITLE",
                    "op": "set_field",
                    "target_id": "title",
                    "changes": {
                        "text": "TÍTULO IA — VALIDADO\nSEM PERDA",
                        "x": 104,
                        "font": "Stardos Stencil",
                        "shadowEnabled": True,
                    },
                },
                {
                    "operation_id": "OP-LINE",
                    "op": "set_line",
                    "target_id": "title-underline",
                    "changes": {"width": 2.2, "opacity": 0.72, "fade": False},
                },
                {
                    "operation_id": "OP-ASSET",
                    "op": "set_assets",
                    "changes": {
                        "visualZoom": 2.2,
                        "visualFocalX": 72,
                        "visualFocalY": 28,
                        "visualShape": "rounded",
                    },
                },
                {
                    "operation_id": "OP-LAYERS",
                    "op": "set_layers",
                    "changes": {"logo": False},
                },
                {
                    "operation_id": "OP-GRID",
                    "op": "set_grid_style",
                    "changes": {"opacity": 0.45},
                },
            ],
            "provenance": {
                "provider": "fixture-local",
                "model": "synthetic-no-network",
                "request_id": "REQ-M9-6-001",
            },
        }

    def review(self, intent: dict | None = None) -> dict:
        return intents.review_card_edit_intent(
            self.project,
            intent or self.intent(),
            self.catalog,
            expected_project_id=self.context["project_id"],
        )

    def test_provider_request_is_read_only_path_free_and_capability_bounded(self):
        request = self.request()
        serialized = json.dumps(request, ensure_ascii=False)
        self.assertNotIn(str(self.project), serialized)
        self.assertNotIn("source_path", serialized)
        self.assertNotIn("data:image", serialized.lower())
        self.assertNotIn("callback", serialized.lower().replace('"callbacks"', ""))
        self.assertEqual(request["required_output"], "CARD_EDIT_INTENT_V2")
        self.assertEqual(request["capabilities"]["formats"], ["9:16"])
        self.assertIn("duration", request["capabilities"]["unsupported"])
        self.assertNotIn("Georgia", request["capabilities"]["fonts_renderable"])

        before = copy.deepcopy(request)

        def provider(snapshot):
            snapshot["read_only_snapshot"]["instance"]["state"]["fields"][0]["text"] = "MUTADO"
            return self.intent()

        returned = intents.request_provider_intent(provider, request)
        self.assertEqual(request, before)
        self.assertEqual(returned["kind"], "CARD_EDIT_INTENT")

    def test_review_uses_manual_validator_builds_diff_and_never_writes(self):
        store_path = self.project / persistence.STORE_PATH
        store_before = store_path.read_bytes()
        plan_before = (self.project / "EDIT_PLAN.json").read_bytes()
        media_before = self.visual.read_bytes()
        review = self.review()
        self.assertTrue(review["valid"])
        self.assertTrue(review["requires_confirmation"])
        self.assertEqual(review["candidate_instance"]["edit_origin"], "ai_assisted")
        self.assertEqual(len(review["candidate_instance"]["state"]["fields"]), 21)
        self.assertEqual(len(review["candidate_instance"]["state"]["lines"]), 29)
        self.assertEqual(
            review["candidate_snapshot"]["revision"], review["after_revision"],
        )
        paths = {row["path"] for row in review["diff"]}
        self.assertIn("state.fields[10].text", paths)
        self.assertIn("state.assets.visualZoom", paths)
        self.assertEqual(store_path.read_bytes(), store_before)
        self.assertEqual((self.project / "EDIT_PLAN.json").read_bytes(), plan_before)
        self.assertEqual(self.visual.read_bytes(), media_before)

    def test_apply_requires_confirmation_then_snapshot_and_rollback_restore_exact_state(self):
        intent = self.intent()
        review = self.review(intent)
        with self.assertRaisesRegex(intents.CardEditIntentV2Error, "confirmação explícita"):
            intents.apply_confirmed_card_edit(
                self.project, intent, self.catalog,
                expected_project_id=self.context["project_id"],
                confirmation_token=review["confirmation_token"], confirmed=False,
            )
        with self.assertRaisesRegex(intents.CardEditIntentV2Error, "Token"):
            intents.apply_confirmed_card_edit(
                self.project, intent, self.catalog,
                expected_project_id=self.context["project_id"],
                confirmation_token="0" * 64, confirmed=True,
            )

        plan_before = (self.project / "EDIT_PLAN.json").read_bytes()
        media_before = self.visual.read_bytes()
        applied = intents.apply_confirmed_card_edit(
            self.project, intent, self.catalog,
            expected_project_id=self.context["project_id"],
            confirmation_token=review["confirmation_token"], confirmed=True,
        )
        self.assertTrue(applied["applied"])
        self.assertEqual(applied["instance"]["state_digest"], review["candidate_instance"]["state_digest"])
        self.assertTrue(
            (self.project / "_ROTEIROS" / applied["rollback_version"] / persistence.STORE_PATH).is_file()
        )
        restored = persistence.rollback_card_state(
            self.project,
            self.instance["instance_id"],
            applied["before_snapshot_digest"],
            self.catalog,
            expected_project_id=self.context["project_id"],
            expected_store_revision=applied["store_revision"],
            expected_current_revision=applied["instance_revision"],
        )
        self.assertEqual(restored["instance"], self.instance)
        self.assertEqual((self.project / "EDIT_PLAN.json").read_bytes(), plan_before)
        self.assertEqual(self.visual.read_bytes(), media_before)

    def test_forbidden_unknown_conflicting_and_unrenderable_changes_are_rejected(self):
        cases = []
        forbidden = self.intent([{
            "operation_id": "OP-BAD", "op": "set_field", "target_id": "title",
            "changes": {"duration_sec": 9},
        }])
        cases.append(("não suportadas", forbidden))
        unknown_op = self.intent([{
            "operation_id": "OP-BAD", "op": "write_timeline", "changes": {"x": 1},
        }])
        cases.append(("operação não suportada", unknown_op))
        unknown_target = self.intent([{
            "operation_id": "OP-BAD", "op": "set_line", "target_id": "invented",
            "changes": {"width": 1},
        }])
        cases.append(("ID desconhecido", unknown_target))
        unrenderable_font = self.intent([{
            "operation_id": "OP-BAD", "op": "set_field", "target_id": "title",
            "changes": {"font": "Georgia"},
        }])
        cases.append(("não registrada", unrenderable_font))
        bad_asset = self.intent([{
            "operation_id": "OP-BAD", "op": "set_assets",
            "changes": {"visual": {
                "scope": "project_asset", "asset_id": "invented", "sha256": "0" * 64,
            }},
        }])
        cases.append(("asset inexistente", bad_asset))
        duplicate = self.intent([
            {"operation_id": "OP-A", "op": "set_grid_style", "changes": {"opacity": 0.4}},
            {"operation_id": "OP-B", "op": "set_grid_style", "changes": {"opacity": 0.5}},
        ])
        cases.append(("mais de uma vez", duplicate))
        for message, value in cases:
            with self.subTest(message=message):
                before = (self.project / persistence.STORE_PATH).read_bytes()
                with self.assertRaisesRegex((intents.CardEditIntentV2Error, persistence.CardPersistenceV2Error), message):
                    self.review(value)
                self.assertEqual((self.project / persistence.STORE_PATH).read_bytes(), before)

    def test_stale_revision_project_isolation_and_invalid_state_fail_closed(self):
        stale = self.intent()
        stale["base_instance_revision"] = "0" * 64
        with self.assertRaisesRegex(intents.CardEditIntentV2Error, "estado atual diverge"):
            self.review(stale)

        invalid = self.intent([{
            "operation_id": "OP-NAN", "op": "set_assets", "changes": {"visualZoom": float("nan")},
        }])
        with self.assertRaisesRegex(intents.CardEditIntentV2Error, "número finito"):
            self.review(invalid)

        with self.assertRaisesRegex(persistence.CardPersistenceV2Error, "outro projeto"):
            intents.build_provider_request(
                self.project, self.instance["instance_id"], self.catalog,
                expected_project_id="PROJECT-INVENTED", task="Editar",
            )

    def test_ready_video_intent_preserves_locked_clock_and_base(self):
        fixture = self.fixture
        video = self.project / "_ORIGINAIS" / "base.mp4"
        video.parent.mkdir(exist_ok=True)
        video.write_bytes(b"synthetic-ready-base")
        ready_instance = copy.deepcopy(self.instance)
        ready_instance["instance_id"] = "OV-UNIVERSAL-INTENT"
        ready_instance["placement"] = {
            "timebase": "ready_video_base", "start_sec": 1.0, "end_sec": 4.5,
        }
        ready_instance["state_digest"] = cards.renderable_state_digest(
            ready_instance["definition_ref"], ready_instance["state"],
        )
        ready_plan = {
            "input_mode": "ready_video", "base_video_id": "READY-BASE",
            "timeline_locked": True,
            "overlays": [{
                "overlay_id": ready_instance["instance_id"], "kind": "common_card",
                "start_sec": 1.0, "end_sec": 4.5, "text": "Card", "body": "Ready",
            }],
        }
        ready_manifest = copy.deepcopy(self.manifest)
        ready_manifest["input_mode"] = "ready_video"
        ready_manifest["base_video_id"] = "READY-BASE"
        ready_manifest["media"].append({
            "id": "READY-BASE", "media_type": "video", "status": "ok",
            "source_path": "_ORIGINAIS/base.mp4",
            "sha256": __import__("hashlib").sha256(video.read_bytes()).hexdigest(),
            "duration_sec": 6.0,
        })
        # O store raw anterior não pode sobreviver à troca de modo da fixture.
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
        request = intents.build_provider_request(
            self.project, ready_instance["instance_id"], self.catalog,
            expected_project_id=context["project_id"], task="Editar somente o título",
        )
        value = {
            "schema_version": 2, "kind": "CARD_EDIT_INTENT", "intent_id": "READY-INTENT",
            "origin": "ai_assisted", "project_id": request["project_id"],
            "target_id": request["target_id"], "input_mode": "ready_video",
            "base_plan_revision": request["base_plan_revision"],
            "base_store_revision": request["base_store_revision"],
            "base_instance_revision": request["base_instance_revision"],
            "operations": [{
                "operation_id": "OP-READY-TITLE", "op": "set_field", "target_id": "title",
                "changes": {"text": "READY SEM MOVER O RELÓGIO"},
            }],
            "provenance": {"provider": "fixture", "model": "offline", "request_id": "ready-1"},
        }
        review = intents.review_card_edit_intent(
            self.project, value, self.catalog,
            expected_project_id=context["project_id"],
        )
        self.assertEqual(review["candidate_instance"]["placement"], ready_instance["placement"])
        self.assertTrue(project_scope.read(self.project / "READY_VIDEO_PLAN.json")["timeline_locked"])
        self.assertEqual(project_scope.read(self.project / "READY_VIDEO_PLAN.json")["base_video_id"], "READY-BASE")

    def test_schema_is_strict_and_versioned(self):
        schema = json.loads(
            (ROOT / "contracts" / "m9" / "card_edit_intent_v2.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["schema_version"]["const"], 2)
        self.assertEqual(schema["properties"]["kind"]["const"], "CARD_EDIT_INTENT")


if __name__ == "__main__":
    unittest.main(verbosity=2)
