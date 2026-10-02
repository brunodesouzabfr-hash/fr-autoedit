#!/usr/bin/env python3
"""M9.2: round-trip integral fr-card-editor/1.1 ↔ CardInstance v2."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "tests"))

import card_editor_adapter as legacy_adapter  # noqa: E402
import card_editor_adapter_v2 as adapter  # noqa: E402
import card_state_v2 as cards  # noqa: E402
import card_state_v2_test as m91_fixture  # noqa: E402


class CardEditorAdapterV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        m91_fixture.CardStateV2Test.setUpClass()
        cls.editor_contract = json.loads(
            (ROOT / "contracts" / "m9" / "fr_card_editor_1_1.json").read_text(encoding="utf-8")
        )

    def setUp(self):
        fixture = m91_fixture.CardStateV2Test(
            methodName="test_valid_definition_and_instance_preserve_all_fields_lines_unicode_and_newlines"
        )
        fixture.setUp()
        self.catalog = copy.deepcopy(fixture.catalog)
        self.catalog.update({
            "synthetic_service": {
                "asset_id": "synthetic_service",
                "scope": "service_catalog",
                "sha256": "d" * 64,
            },
            "synthetic_upload": {
                "asset_id": "synthetic_upload",
                "scope": "project_asset",
                "sha256": "e" * 64,
            },
        })
        self.bindings = {
            "synthetic_background": "/m9/assets/background",
            "synthetic_logo": "/m9/assets/logo",
            "synthetic_visual": "/m9/assets/visual",
            "synthetic_service": "/m9/assets/service",
            "synthetic_upload": "/m9/assets/upload",
        }
        self.definition = copy.deepcopy(fixture.definition)
        self.instance = copy.deepcopy(fixture.instance)
        # Exercita a normalização real de applyConfig(): essas propriedades são
        # opcionais em v2, mas o editor as materializa em getConfig().
        self.instance["state"]["fields"][0].pop("visible")
        self.instance["state"]["lines"][0].pop("opacity")
        self.instance["state"]["lines"][0].pop("fade")
        self.redigest(self.instance)

    @staticmethod
    def redigest(instance: dict) -> None:
        instance["state_digest"] = cards.renderable_state_digest(
            instance["definition_ref"], instance["state"], instance.get("service_key"),
        )

    def asset_ref(self, asset_id: str, *, frame_time_sec: float | None = None) -> dict:
        row = self.catalog[asset_id]
        result = {
            "scope": row["scope"], "asset_id": row["asset_id"], "sha256": row["sha256"],
        }
        if frame_time_sec is not None:
            result["frame_time_sec"] = frame_time_sec
        return result

    def session(self) -> dict:
        return adapter.export_card_state(
            self.definition, self.instance, self.catalog, self.bindings,
        )

    def test_export_matches_real_editor_contract_without_persisting_asset_paths(self):
        session = self.session()
        state = session["editor_state"]
        self.assertEqual(session["adapter_version"], "fr-autoedite-card/2")
        self.assertEqual(set(state), set(self.editor_contract["state"]["top_level_fields"]))
        self.assertEqual(state["version"], "1.1.0")
        self.assertEqual(state["canvas"], {
            "width": 941, "height": 1672, "ratio": "9:16",
            "exportWidth": 2160, "exportHeight": 3840,
        })
        self.assertEqual(len(state["fields"]), 21)
        self.assertEqual(len(state["lines"]), 29)
        self.assertEqual(state["assets"]["background"], self.bindings["synthetic_background"])
        self.assertEqual(state["assets"]["logo"], self.bindings["synthetic_logo"])
        self.assertEqual(state["assets"]["visual"], self.bindings["synthetic_visual"])
        self.assertIsInstance(session["asset_refs"]["background"], dict)
        self.assertNotIn("data:", json.dumps(session, ensure_ascii=False).lower())
        self.assertEqual(
            session["base_revision"], cards.instance_revision(self.instance),
        )

    def test_noop_round_trip_is_exact_despite_editor_default_materialization(self):
        original = copy.deepcopy(self.instance)
        session = self.session()
        self.assertTrue(session["editor_state"]["fields"][0]["visible"])
        self.assertFalse(session["editor_state"]["fields"][0]["noWrap"])
        self.assertFalse(session["editor_state"]["fields"][0]["shadowEnabled"])
        self.assertEqual(session["editor_state"]["lines"][0]["opacity"], 1)
        self.assertTrue(session["editor_state"]["lines"][0]["fade"])
        result = adapter.apply_card_state(
            self.definition, self.instance, session, self.catalog, self.bindings,
        )
        self.assertEqual(result, original)
        self.assertEqual(self.instance, original)

    def test_full_edit_round_trip_preserves_structure_and_updates_renderable_state(self):
        before = copy.deepcopy(self.instance)
        session = self.session()
        fields = {row["id"]: row for row in session["editor_state"]["fields"]}
        lines = {row["id"]: row for row in session["editor_state"]["lines"]}
        fields["title"].update({
            "text": "CASA — MEMÓRIA\nE MATÉRIA",
            "x": 101,
            "y": 207,
            "font": "Stardos Stencil",
            "size": 58,
            "weight": 700,
            "lineHeight": 1.05,
            "spacing": 0.03,
            "align": "center",
            "color": "#F6A700",
            "effect": "metallic",
            "noWrap": True,
            "shadowEnabled": True,
            "shadowX": 3,
            "shadowY": 4,
            "shadowBlur": 2.5,
            "shadowOpacity": 0.4,
        })
        fields["subtitle"]["text"] = "Unicode preservado: São Paulo · ação · 施工"
        lines["title-underline"].update({
            "x1": 290, "y1": 336, "x2": 651, "y2": 336,
            "width": 2.4, "opacity": 0.72, "fade": False,
        })
        session["editor_state"]["gridStyle"]["opacity"] = 0.55
        session["editor_state"]["layers"]["logo"] = False
        session["editor_state"]["assets"].update({
            "visual": self.bindings["synthetic_service"],
            "visualShape": "rounded",
            "visualSize": 420,
            "visualZoom": 2.1,
            "visualFocalX": 81,
            "visualFocalY": 19,
            "visualOpacity": 0.74,
        })
        session["asset_refs"]["visual"] = self.asset_ref("synthetic_service")

        result = adapter.apply_card_state(
            self.definition, self.instance, session, self.catalog, self.bindings,
        )
        self.assertEqual(self.instance, before)
        self.assertEqual(result["instance_id"], before["instance_id"])
        self.assertEqual(result["definition_ref"], before["definition_ref"])
        self.assertEqual(result["placement"], before["placement"])
        self.assertEqual(result["edit_origin"], before["edit_origin"])
        self.assertEqual(len(result["state"]["fields"]), 21)
        self.assertEqual(len(result["state"]["lines"]), 29)
        title = next(row for row in result["state"]["fields"] if row["id"] == "title")
        self.assertEqual(title["text"], "CASA — MEMÓRIA\nE MATÉRIA")
        self.assertTrue(title["shadowEnabled"])
        self.assertEqual(result["state"]["assets"]["visual"], self.asset_ref("synthetic_service"))
        self.assertFalse(result["state"]["layers"]["logo"])
        self.assertEqual(
            result["state_digest"],
            cards.renderable_state_digest(result["definition_ref"], result["state"]),
        )
        self.assertEqual(adapter.title_body_projection(result), {
            "title": "CASA — MEMÓRIA\nE MATÉRIA",
            "body": "Unicode preservado: São Paulo · ação · 施工",
        })

    def test_registered_transient_upload_becomes_asset_ref_and_data_url_is_not_persisted(self):
        session = self.session()
        data_url = "data:image/png;base64,U1lOVEhFVElDX01BR0U="
        session["editor_state"]["assets"]["visual"] = data_url
        session["asset_refs"]["visual"] = self.asset_ref("synthetic_upload")
        transient = {
            "synthetic_upload": hashlib.sha256(data_url.encode("utf-8")).hexdigest(),
        }
        result = adapter.apply_card_state(
            self.definition,
            self.instance,
            session,
            self.catalog,
            self.bindings,
            transient_uploads=transient,
        )
        self.assertEqual(
            result["state"]["assets"]["visual"], self.asset_ref("synthetic_upload"),
        )
        self.assertNotIn("data:image", json.dumps(result).lower())

        with self.assertRaisesRegex(adapter.CardEditorAdapterV2Error, "não foi registrado"):
            adapter.apply_card_state(
                self.definition,
                self.instance,
                session,
                self.catalog,
                self.bindings,
                transient_uploads={"synthetic_upload": "0" * 64},
            )

    def test_invalid_payloads_are_rejected_without_mutating_current_instance(self):
        cases: list[tuple[str, dict]] = []

        unknown_payload = self.session()
        unknown_payload["timeline"] = []
        cases.append(("desconhecidos", unknown_payload))

        stale = self.session()
        stale["base_revision"] = "0" * 64
        cases.append(("revisão obsoleta", stale))

        changed_definition = self.session()
        changed_definition["definition_digest"] = "0" * 64
        cases.append(("CardDefinition mudou", changed_definition))

        changed_canvas = self.session()
        changed_canvas["editor_state"]["canvas"]["width"] = 1080
        cases.append(("dimensões divergem", changed_canvas))

        unknown_editor_property = self.session()
        unknown_editor_property["editor_state"]["html"] = "<div>solto</div>"
        cases.append(("desconhecidos", unknown_editor_property))

        duplicate_field = self.session()
        duplicate_field["editor_state"]["fields"][-1]["id"] = "promise"
        duplicate_field["editor_state"]["fields"][-1]["role"] = "fixed"
        cases.append(("IDs duplicados", duplicate_field))

        unknown_line = self.session()
        unknown_line["editor_state"]["lines"][-1]["id"] = "linha-inventada"
        cases.append(("linha desconhecida", unknown_line))

        duplicate_line = self.session()
        duplicate_line["editor_state"]["lines"][-1]["id"] = "v-left"
        cases.append(("IDs duplicados", duplicate_line))

        unknown_field_property = self.session()
        unknown_field_property["editor_state"]["fields"][0]["css"] = "position:fixed"
        cases.append(("campos desconhecidos", unknown_field_property))

        reordered_lines = self.session()
        reordered_lines["editor_state"]["lines"][0], reordered_lines["editor_state"]["lines"][1] = (
            reordered_lines["editor_state"]["lines"][1],
            reordered_lines["editor_state"]["lines"][0],
        )
        cases.append(("ordem dos IDs diverge", reordered_lines))

        divergent_asset = self.session()
        divergent_asset["asset_refs"]["logo"]["sha256"] = "f" * 64
        cases.append(("hash diverge", divergent_asset))

        mismatched_binding = self.session()
        mismatched_binding["editor_state"]["assets"]["logo"] = "/client/path/logo.png"
        cases.append(("não corresponde", mismatched_binding))

        unregistered_data = self.session()
        unregistered_data["editor_state"]["assets"]["visual"] = "data:image/png;base64,AAAA"
        cases.append(("não foi registrado", unregistered_data))

        property_loss = self.session()
        property_loss["editor_state"]["fields"][1].pop("visible")
        cases.append(("propriedades existentes removidas", property_loss))

        for message, payload in cases:
            with self.subTest(message=message):
                before = copy.deepcopy(self.instance)
                with self.assertRaisesRegex(adapter.CardEditorAdapterV2Error, message):
                    adapter.apply_card_state(
                        self.definition, self.instance, payload, self.catalog, self.bindings,
                    )
                self.assertEqual(self.instance, before)

    def test_asset_id_unknown_duplicate_binding_and_data_url_binding_are_rejected(self):
        unknown_asset = self.session()
        unknown_asset["asset_refs"]["visual"] = {
            "scope": "project_asset", "asset_id": "invented", "sha256": "1" * 64,
        }
        with self.assertRaisesRegex(adapter.CardEditorAdapterV2Error, "asset inexistente"):
            adapter.apply_card_state(
                self.definition, self.instance, unknown_asset, self.catalog, self.bindings,
            )

        duplicate_bindings = copy.deepcopy(self.bindings)
        duplicate_bindings["synthetic_logo"] = duplicate_bindings["synthetic_background"]
        with self.assertRaisesRegex(adapter.CardEditorAdapterV2Error, "bindings duplicados"):
            adapter.export_card_state(
                self.definition, self.instance, self.catalog, duplicate_bindings,
            )

        data_binding = copy.deepcopy(self.bindings)
        data_binding["synthetic_logo"] = "data:image/png;base64,AAAA"
        with self.assertRaisesRegex(adapter.CardEditorAdapterV2Error, "não pode usar data"):
            adapter.export_card_state(
                self.definition, self.instance, self.catalog, data_binding,
            )

    def test_projects_are_isolated_and_browser_storage_is_not_an_input(self):
        project_a = copy.deepcopy(self.instance)
        project_b = copy.deepcopy(self.instance)
        title_b = next(row for row in project_b["state"]["fields"] if row["id"] == "title")
        title_b["text"] = "PROJETO B — ESTADO ATUAL"
        self.redigest(project_b)
        session_a = adapter.export_card_state(
            self.definition, project_a, self.catalog, self.bindings,
        )
        session_b = adapter.export_card_state(
            self.definition, project_b, self.catalog, self.bindings,
        )
        self.assertNotEqual(session_a["base_revision"], session_b["base_revision"])
        self.assertNotEqual(
            adapter.title_body_projection(project_a), adapter.title_body_projection(project_b),
        )
        with self.assertRaisesRegex(adapter.CardEditorAdapterV2Error, "revisão obsoleta"):
            adapter.apply_card_state(
                self.definition, project_b, session_a, self.catalog, self.bindings,
            )

    def test_card_instance_v1_remains_on_legacy_adapter_without_silent_conversion(self):
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
        self.assertEqual(cards.validate_card_instance(legacy), legacy)
        self.assertEqual(legacy_adapter.ADAPTER_VERSION, "fr-autoedite-card-content/1")
        with self.assertRaisesRegex(adapter.CardEditorAdapterV2Error, "adapter legado"):
            adapter.export_card_state(
                self.definition, legacy, self.catalog, self.bindings,
            )
        with self.assertRaisesRegex(adapter.CardEditorAdapterV2Error, "adapter legado"):
            adapter.apply_card_state(
                self.definition, legacy, {}, self.catalog, self.bindings,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
