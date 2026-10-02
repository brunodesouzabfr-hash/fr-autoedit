#!/usr/bin/env python3
"""M9.1: schemas e validators produtivos de CardDefinition/CardInstance v2."""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import card_state_v2 as cards  # noqa: E402


class CardStateV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.editor_contract = json.loads(
            (ROOT / "contracts" / "m9" / "fr_card_editor_1_1.json").read_text(encoding="utf-8")
        )

    def setUp(self):
        self.catalog = {
            "synthetic_background": {
                "asset_id": "synthetic_background", "scope": "component", "sha256": "a" * 64,
            },
            "synthetic_logo": {
                "asset_id": "synthetic_logo", "scope": "component", "sha256": "b" * 64,
            },
            "synthetic_visual": {
                "asset_id": "synthetic_visual", "scope": "project_media", "sha256": "c" * 64,
            },
        }
        self.definition = self.build_definition()
        self.instance = self.build_instance()

    def asset_ref(self, asset_id: str) -> dict:
        row = self.catalog[asset_id]
        return {
            "scope": row["scope"], "asset_id": row["asset_id"], "sha256": row["sha256"],
        }

    def build_state(self) -> dict:
        fields = []
        for index, field_id in enumerate(cards.FIELD_IDS):
            fields.append({
                "id": field_id,
                "role": "fixed" if field_id in cards.FIXED_FIELD_IDS else "variable",
                "text": "Reforma — São Paulo\nEtapa válida" if field_id == "title" else f"Texto {field_id}",
                "x": 20 + index,
                "y": 30 + index,
                "w": 180,
                "h": 64,
                "font": "Cormorant Garamond",
                "size": 24,
                "weight": 500,
                "lineHeight": 1.2,
                "spacing": 0.02,
                "align": "left",
                "color": "#E6D6B5",
                "effect": "plain",
                "visible": True,
            })
        lines = [
            {
                "id": line_id,
                "x1": index,
                "y1": index + 1,
                "x2": index + 20,
                "y2": index + 1,
                "width": 1.4,
                "color": "#D6A64B",
                "visible": True,
                "opacity": 0.8,
                "fade": False,
            }
            for index, line_id in enumerate(cards.LINE_IDS)
        ]
        return {
            "assets": {
                "background": self.asset_ref("synthetic_background"),
                "logo": self.asset_ref("synthetic_logo"),
                "visual": self.asset_ref("synthetic_visual") | {"frame_time_sec": 1.25},
                "visualOpacity": 0.86,
                "visualShape": "circle",
                "visualSize": 389,
                "visualZoom": 1.73,
                "visualFocalX": 23,
                "visualFocalY": 77,
            },
            "layers": {"background": True, "grid": True, "text": True, "logo": True},
            "gridStyle": {"opacity": 0.36},
            "fields": fields,
            "lines": lines,
        }

    def build_definition(self) -> dict:
        return {
            "schema_version": 2,
            "definition_id": "universal/default-9x16",
            "definition_version": 1,
            "editor_schema": "fr-card-editor/1.1",
            "renderer_id": "fr-universal-card",
            "renderer_version": "1.0.0",
            "canvas": copy.deepcopy(self.editor_contract["canvas"]),
            "component": copy.deepcopy(self.editor_contract["component"]),
            "default_state": self.build_state(),
            "capabilities": {
                "formats": ["9:16"],
                "state_sections": ["assets", "layers", "gridStyle", "fields", "lines"],
            },
        }

    def build_instance(self, *, placement: dict | None = None) -> dict:
        state = self.build_state()
        definition_ref = {
            "definition_id": self.definition["definition_id"],
            "definition_version": self.definition["definition_version"],
        }
        return {
            "schema_version": 2,
            "instance_id": "CARD-UNIVERSAL-001",
            "definition_ref": definition_ref,
            "edit_origin": "manual",
            "placement": placement or {
                "timebase": "raw_sequence", "sequence_index": 2, "duration_sec": 3.5,
            },
            "state": state,
            "state_digest": cards.renderable_state_digest(definition_ref, state),
        }

    @staticmethod
    def redigest(instance: dict) -> None:
        instance["state_digest"] = cards.renderable_state_digest(
            instance["definition_ref"], instance["state"], instance.get("service_key"),
        )

    def test_valid_definition_and_instance_preserve_all_fields_lines_unicode_and_newlines(self):
        definition_before = copy.deepcopy(self.definition)
        instance_before = copy.deepcopy(self.instance)
        definition = cards.validate_card_definition_v2(self.definition, self.catalog)
        instance = cards.validate_card_instance_v2(self.instance, definition, self.catalog)
        self.assertEqual(len(instance["state"]["fields"]), 21)
        self.assertEqual(len(instance["state"]["lines"]), 29)
        self.assertEqual(
            next(row for row in instance["state"]["fields"] if row["id"] == "title")["text"],
            "Reforma — São Paulo\nEtapa válida",
        )
        self.assertEqual(self.definition, definition_before)
        self.assertEqual(self.instance, instance_before)

    def test_ready_video_placement_is_validated_without_mixing_clocks(self):
        ready = self.build_instance(placement={
            "timebase": "ready_video_base", "start_sec": 1.25, "end_sec": 4.75,
        })
        normalized = cards.validate_card_instance_v2(ready, self.definition, self.catalog)
        self.assertEqual(normalized["placement"], ready["placement"])
        mixed = copy.deepcopy(ready)
        mixed["placement"]["duration_sec"] = 3.5
        with self.assertRaisesRegex(cards.CardStateV2Error, "campos desconhecidos"):
            cards.validate_card_instance_v2(mixed, self.definition, self.catalog)

    def test_invalid_payload_unknown_properties_nan_and_bad_unicode_are_rejected(self):
        cases = []
        unknown = copy.deepcopy(self.instance)
        unknown["html"] = "<div>não pertence ao contrato</div>"
        cases.append(unknown)
        nan_value = copy.deepcopy(self.instance)
        nan_value["state"]["fields"][0]["x"] = math.nan
        cases.append(nan_value)
        bad_unicode = copy.deepcopy(self.instance)
        bad_unicode["state"]["fields"][0]["text"] = "surrogate:\ud800"
        bad_unicode["state_digest"] = "0" * 64
        cases.append(bad_unicode)
        bad_break = copy.deepcopy(self.instance)
        bad_break["state"]["fields"][0]["text"] = "linha 1\r\nlinha 2"
        self.redigest(bad_break)
        cases.append(bad_break)
        for payload in cases:
            with self.subTest(payload=list(payload)):
                with self.assertRaises(cards.CardStateV2Error):
                    cards.validate_card_instance_v2(payload, self.definition, self.catalog)

    def test_invalid_enum_types_and_fractional_schema_version_raise_contract_error(self):
        cases = []
        bad_version = copy.deepcopy(self.instance)
        bad_version["schema_version"] = 2.0
        cases.append(bad_version)
        bad_origin = copy.deepcopy(self.instance)
        bad_origin["edit_origin"] = ["manual"]
        cases.append(bad_origin)
        bad_service = copy.deepcopy(self.instance)
        bad_service["service_key"] = {"key": "alvenaria"}
        cases.append(bad_service)
        bad_font = copy.deepcopy(self.instance)
        bad_font["state"]["fields"][0]["font"] = ["Arial"]
        cases.append(bad_font)
        for payload in cases:
            with self.subTest(payload=payload.get("instance_id")):
                with self.assertRaises(cards.CardStateV2Error):
                    cards.validate_card_instance_v2(payload, self.definition, self.catalog)

    def test_unknown_field_and_line_ids_are_rejected(self):
        unknown_field = copy.deepcopy(self.instance)
        unknown_field["state"]["fields"][-1]["id"] = "inventedField"
        self.redigest(unknown_field)
        with self.assertRaisesRegex(cards.CardStateV2Error, "campo desconhecido"):
            cards.validate_card_instance_v2(unknown_field, self.definition, self.catalog)

        unknown_line = copy.deepcopy(self.instance)
        unknown_line["state"]["lines"][-1]["id"] = "invented-line"
        self.redigest(unknown_line)
        with self.assertRaisesRegex(cards.CardStateV2Error, "linha desconhecida"):
            cards.validate_card_instance_v2(unknown_line, self.definition, self.catalog)

    def test_duplicate_field_and_line_ids_are_rejected(self):
        duplicate_field = copy.deepcopy(self.instance)
        duplicate_field["state"]["fields"][-1]["id"] = duplicate_field["state"]["fields"][0]["id"]
        duplicate_field["state"]["fields"][-1]["role"] = "fixed"
        self.redigest(duplicate_field)
        with self.assertRaisesRegex(cards.CardStateV2Error, "IDs duplicados"):
            cards.validate_card_instance_v2(duplicate_field, self.definition, self.catalog)

        duplicate_line = copy.deepcopy(self.instance)
        duplicate_line["state"]["lines"][-1]["id"] = duplicate_line["state"]["lines"][0]["id"]
        self.redigest(duplicate_line)
        with self.assertRaisesRegex(cards.CardStateV2Error, "IDs duplicados"):
            cards.validate_card_instance_v2(duplicate_line, self.definition, self.catalog)

    def test_missing_asset_and_divergent_hash_are_rejected(self):
        missing = copy.deepcopy(self.instance)
        missing["state"]["assets"]["visual"]["asset_id"] = "asset_inexistente"
        self.redigest(missing)
        with self.assertRaisesRegex(cards.CardStateV2Error, "asset inexistente"):
            cards.validate_card_instance_v2(missing, self.definition, self.catalog)

        divergent = copy.deepcopy(self.instance)
        divergent["state"]["assets"]["logo"]["sha256"] = "d" * 64
        self.redigest(divergent)
        with self.assertRaisesRegex(cards.CardStateV2Error, "hash diverge"):
            cards.validate_card_instance_v2(divergent, self.definition, self.catalog)

        client_path = copy.deepcopy(self.instance)
        client_path["state"]["assets"]["logo"]["absolute_path"] = "/tmp/logo.png"
        self.redigest(client_path)
        with self.assertRaisesRegex(cards.CardStateV2Error, "campos desconhecidos"):
            cards.validate_card_instance_v2(client_path, self.definition, self.catalog)

    def test_stale_revision_is_rejected(self):
        revision = cards.instance_revision(self.instance)
        self.assertEqual(cards.require_current_revision(revision, self.instance), revision)
        with self.assertRaisesRegex(cards.CardStateV2Error, "revisão obsoleta"):
            cards.require_current_revision("0" * 64, self.instance)

    def test_legacy_v1_and_missing_card_instance_remain_compatible_without_migration(self):
        legacy = {
            "schema_version": 1,
            "instance_id": "S0003",
            "definition_id": "raw/phase",
            "definition_version": 1,
            "edit_origin": "manual",
            "placement": {
                "timebase": "raw_sequence", "sequence_index": 1, "duration_sec": 2.0,
            },
        }
        before = copy.deepcopy(legacy)
        self.assertEqual(cards.validate_card_instance(legacy), legacy)
        self.assertEqual(legacy, before)
        self.assertIsNone(cards.validate_card_instance(None))
        self.assertEqual(cards.validate_card_instance(legacy)["schema_version"], 1)

    def test_snapshot_is_immutable_and_rollback_requires_current_revision(self):
        snapshot = cards.create_card_snapshot(self.definition, self.instance, self.catalog)
        snapshot_before = copy.deepcopy(snapshot)
        current = copy.deepcopy(self.instance)
        current["state"]["fields"][10]["text"] = "Estado alterado após snapshot"
        self.redigest(current)
        current_revision = cards.instance_revision(current)
        restored = cards.rollback_card_instance(
            current,
            snapshot,
            expected_current_revision=current_revision,
            asset_catalog=self.catalog,
        )
        self.assertEqual(restored, self.instance)
        self.assertEqual(snapshot, snapshot_before)
        restored["state"]["fields"][0]["text"] = "cópia independente"
        self.assertEqual(snapshot, snapshot_before)
        with self.assertRaisesRegex(cards.CardStateV2Error, "revisão obsoleta"):
            cards.rollback_card_instance(
                current,
                snapshot,
                expected_current_revision="0" * 64,
                asset_catalog=self.catalog,
            )

    def test_snapshot_tampering_is_rejected(self):
        snapshot = cards.create_card_snapshot(self.definition, self.instance, self.catalog)
        snapshot["instance"]["state"]["fields"][0]["text"] = "alteração não autenticada"
        with self.assertRaises(cards.CardStateV2Error):
            cards.validate_card_snapshot(snapshot, self.catalog)

    def test_renderable_digest_is_deterministic_and_sensitive_to_state(self):
        first = cards.renderable_state_digest(
            self.instance["definition_ref"], self.instance["state"],
        )
        reordered_state = {
            key: copy.deepcopy(self.instance["state"][key])
            for key in reversed(list(self.instance["state"]))
        }
        second = cards.renderable_state_digest(self.instance["definition_ref"], reordered_state)
        self.assertEqual(first, second)
        changed = copy.deepcopy(self.instance["state"])
        changed["fields"][0]["text"] += "!"
        self.assertNotEqual(
            first, cards.renderable_state_digest(self.instance["definition_ref"], changed),
        )

    def test_productive_json_schemas_are_versioned_and_closed(self):
        expected = {
            "card_state_v2.schema.json": {"assets", "layers", "gridStyle", "fields", "lines"},
            "card_definition_v2.schema.json": {
                "schema_version", "definition_id", "definition_version", "editor_schema",
                "renderer_id", "renderer_version", "canvas", "component", "default_state",
                "capabilities",
            },
            "card_instance_v2.schema.json": {
                "schema_version", "instance_id", "definition_ref", "edit_origin", "placement",
                "state", "state_digest",
            },
        }
        for name, required in expected.items():
            with self.subTest(schema=name):
                schema = json.loads((ROOT / "contracts" / "m9" / name).read_text(encoding="utf-8"))
                self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
                self.assertFalse(schema["additionalProperties"])
                self.assertEqual(set(schema["required"]), required)
        state_schema = json.loads(
            (ROOT / "contracts" / "m9" / "card_state_v2.schema.json").read_text(encoding="utf-8")
        )
        definition_schema = json.loads(
            (ROOT / "contracts" / "m9" / "card_definition_v2.schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            set(state_schema["$defs"]["field"]["properties"]["id"]["enum"]),
            set(cards.FIELD_IDS),
        )
        self.assertEqual(
            set(state_schema["$defs"]["line"]["properties"]["id"]["enum"]),
            set(cards.LINE_IDS),
        )
        self.assertEqual(
            definition_schema["properties"]["component"]["const"],
            self.editor_contract["component"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
