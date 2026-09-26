#!/usr/bin/env python3
"""Synthetic contract tests for the first, content-only card bridge."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import card_editor_adapter as adapter  # noqa: E402


class CardContentAdapterTest(unittest.TestCase):
    def plan(self, *, title: str = "Título A", body: str = "Corpo A") -> dict:
        return {
            "schema_version": 3,
            "output": {"width": 1080, "height": 1920, "fps": 24},
            "segments": [
                {
                    "segment_id": "S-CARD", "type": "card", "enabled": True,
                    "card_kind": "phase", "card_family": "F2",
                    "duration_sec": 3, "title": title, "body": body,
                    "include_in": ["branded"],
                },
                {
                    "segment_id": "S-MEDIA", "type": "media", "enabled": True,
                    "media_id": "M0001", "duration_sec": 2,
                },
            ],
        }

    def payload(self, plan: dict, **overrides) -> dict:
        payload = {
            "adapter_version": adapter.ADAPTER_VERSION,
            "base_revision": adapter.plan_revision(plan),
            "segment_id": "S-CARD",
            "fields": {"title": "Título editado", "body": "Corpo editado"},
        }
        payload.update(overrides)
        return payload

    def ready_plan(self, *, title: str = "Título ready", body: str = "Corpo ready") -> dict:
        return {
            "schema_version": 1,
            "input_mode": "ready_video",
            "base_video_id": "READY_VIDEO_BASE",
            "timeline_locked": True,
            "allow_duration_extension": False,
            "style_pack_id": "fr_chiaroscuro_vintage_v1",
            "audio_policy": "preserve",
            "overlays": [
                {
                    "overlay_id": "OV0001", "kind": "common_card",
                    "start_sec": 0.4, "end_sec": 2.1,
                    "text": title, "body": body,
                    "position": "center", "asset_id": "cards_common/default",
                    "presentation": "overlay", "safe_area": "title_safe",
                    "opacity": 0.9, "animation_in": "fade",
                    "animation_out": "soft_scale", "audio_policy": "preserve",
                    "rationale": "Fixture sintética.",
                },
                {
                    "overlay_id": "OV0002", "kind": "lower_third",
                    "start_sec": 2.2, "end_sec": 2.8, "text": "Não editar",
                    "position": "bottom_center", "asset_id": "",
                    "presentation": "overlay", "safe_area": "auto",
                    "opacity": 1, "animation_in": "fade",
                    "animation_out": "fade", "audio_policy": "preserve",
                    "rationale": "Controle não-card.",
                },
            ],
        }

    def ready_payload(self, plan: dict, **overrides) -> dict:
        payload = {
            "adapter_version": adapter.ADAPTER_VERSION,
            "base_revision": adapter.plan_revision(plan),
            "segment_id": "OV0001",
            "fields": {"title": "Título ready editado", "body": "Corpo ready editado"},
        }
        payload.update(overrides)
        return payload

    def test_round_trip_changes_only_supported_content(self):
        original = self.plan()
        exported = adapter.export_card_content(original, "S-CARD")
        self.assertEqual(exported["adapter_version"], "fr-autoedite-card-content/1")
        self.assertEqual(exported["fields"], {"title": "Título A", "body": "Corpo A"})
        self.assertEqual(exported["capabilities"]["supported_fields"], ["title", "body"])
        self.assertFalse(exported["capabilities"]["embedded_assets"])

        updated = adapter.apply_card_content(original, self.payload(original))
        self.assertEqual(original["segments"][0]["title"], "Título A")
        self.assertEqual(updated["segments"][0]["title"], "Título editado")
        self.assertEqual(updated["segments"][0]["body"], "Corpo editado")
        for field in ("card_kind", "card_family", "duration_sec", "include_in"):
            self.assertEqual(updated["segments"][0][field], original["segments"][0][field])
        self.assertEqual(updated["segments"][1], original["segments"][1])

    def test_rejects_stale_revision_unknown_fields_and_embedded_data(self):
        plan = self.plan()
        cases = [
            self.payload(plan, base_revision="0" * 64),
            {key: value for key, value in self.payload(plan).items() if key != "segment_id"},
            {**self.payload(plan), "geometry": {"x": 1}},
            self.payload(plan, fields={"title": "Sem corpo"}),
            self.payload(plan, fields={"title": "Fixo", "body": "Corpo", "style": "F1"}),
            self.payload(plan, fields={"title": "Imagem", "body": "data:image/png;base64,AAAA"}),
            self.payload(plan, fields={"title": "X" * 221, "body": "Corpo"}),
            self.payload(plan, adapter_version="fr-card-editor/1.1"),
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                before = copy.deepcopy(plan)
                with self.assertRaises(adapter.CardEditorAdapterError):
                    adapter.apply_card_content(plan, payload)
                self.assertEqual(plan, before)

    def test_all_renderer_families_are_preserved(self):
        for family in ("F1", "F2", "F3", "F4", "F5", "F6"):
            with self.subTest(family=family):
                plan = self.plan()
                plan["segments"][0]["card_family"] = family
                updated = adapter.apply_card_content(plan, self.payload(plan))
                self.assertEqual(updated["segments"][0]["card_family"], family)
                self.assertEqual(updated["segments"][0]["card_kind"], "phase")

    def test_rejects_non_card_and_duplicate_id(self):
        plan = self.plan()
        with self.assertRaisesRegex(adapter.CardEditorAdapterError, "não é um card raw"):
            adapter.export_card_content(plan, "S-MEDIA")
        duplicate = self.plan()
        duplicate["segments"].append(copy.deepcopy(duplicate["segments"][0]))
        with self.assertRaisesRegex(adapter.CardEditorAdapterError, "duplicado"):
            adapter.export_card_content(duplicate, "S-CARD")

    def test_projects_remain_isolated_without_browser_storage(self):
        project_a = self.plan(title="Projeto A")
        project_b = self.plan(title="Projeto B")
        updated_a = adapter.apply_card_content(
            project_a,
            self.payload(project_a, fields={"title": "A revisado", "body": "Somente A"}),
        )
        self.assertEqual(updated_a["segments"][0]["title"], "A revisado")
        self.assertEqual(project_b["segments"][0]["title"], "Projeto B")
        self.assertNotEqual(adapter.plan_revision(updated_a), adapter.plan_revision(project_b))

    def test_ready_video_card_round_trip_changes_only_text_and_body(self):
        original = self.ready_plan()
        exported = adapter.export_ready_card_content(original, "OV0001")
        self.assertEqual(exported["fields"], {"title": "Título ready", "body": "Corpo ready"})
        self.assertEqual(exported["source"]["input_mode"], "ready_video")
        self.assertTrue(exported["source"]["timeline_locked"])

        updated = adapter.apply_ready_card_content(original, self.ready_payload(original))
        self.assertEqual(original["overlays"][0]["text"], "Título ready")
        self.assertEqual(updated["overlays"][0]["text"], "Título ready editado")
        self.assertEqual(updated["overlays"][0]["body"], "Corpo ready editado")
        original_without_content = copy.deepcopy(original)
        updated_without_content = copy.deepcopy(updated)
        for item in (original_without_content, updated_without_content):
            item["overlays"][0].pop("text")
            item["overlays"][0].pop("body")
        self.assertEqual(updated_without_content, original_without_content)

    def test_ready_video_rejects_non_cards_fallback_content_and_invalid_payloads(self):
        plan = self.ready_plan()
        with self.assertRaisesRegex(adapter.CardEditorAdapterError, "outro contrato visual"):
            adapter.export_ready_card_content(plan, "OV0002")
        missing_title = self.ready_plan(title="")
        with self.assertRaisesRegex(adapter.CardEditorAdapterError, "título de fallback"):
            adapter.export_ready_card_content(missing_title, "OV0001")
        missing_body = self.ready_plan(body="")
        with self.assertRaisesRegex(adapter.CardEditorAdapterError, "corpo de fallback"):
            adapter.export_ready_card_content(missing_body, "OV0001")

        cases = [
            self.ready_payload(plan, base_revision="0" * 64),
            {key: value for key, value in self.ready_payload(plan).items() if key != "segment_id"},
            {**self.ready_payload(plan), "crop": {"x": 0}},
            self.ready_payload(plan, fields={"title": "Sem corpo", "body": ""}),
            self.ready_payload(plan, fields={"title": "Imagem", "body": "data:image/png;base64,AAAA"}),
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                before = copy.deepcopy(plan)
                with self.assertRaises(adapter.CardEditorAdapterError):
                    adapter.apply_ready_card_content(plan, payload)
                self.assertEqual(plan, before)

    def test_ready_video_projects_remain_isolated(self):
        project_a = self.ready_plan(title="Ready A")
        project_b = self.ready_plan(title="Ready B")
        updated_a = adapter.apply_ready_card_content(
            project_a,
            self.ready_payload(
                project_a,
                fields={"title": "Ready A revisado", "body": "Somente ready A"},
            ),
        )
        self.assertEqual(updated_a["overlays"][0]["text"], "Ready A revisado")
        self.assertEqual(project_b["overlays"][0]["text"], "Ready B")
        self.assertNotEqual(adapter.plan_revision(updated_a), adapter.plan_revision(project_b))


if __name__ == "__main__":
    unittest.main(verbosity=2)
