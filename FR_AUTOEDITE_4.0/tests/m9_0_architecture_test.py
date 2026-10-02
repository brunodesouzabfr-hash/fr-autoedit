#!/usr/bin/env python3
"""M9.0: decisão executável e golden masters locais, sem iniciar M9.1."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_card_editor_goldens as golden  # noqa: E402


class M90ArchitectureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.architecture = golden.load_json(golden.ARCHITECTURE_PATH)
        cls.contract = golden.load_json(golden.EDITOR_CONTRACT_PATH)
        cls.fonts = golden.load_json(golden.FONT_SOURCES_PATH)
        cls.scenarios = golden.load_json(golden.SCENARIOS_PATH)
        cls.card_state = golden.load_json(ROOT / "contracts" / "m9" / "card_state_v2_concept.json")
        catalog = json.loads((ROOT / "templates" / "service_catalog.json").read_text(encoding="utf-8"))
        cls.service_keys = {str(row["key"]) for row in catalog["services"]}

    def test_approved_architecture_keeps_legacy_renderer_unchanged(self):
        golden.validate_contracts(
            self.architecture, self.contract, self.fonts, self.scenarios, self.service_keys,
        )
        routing = self.architecture["renderer_routing"]
        self.assertFalse(routing["fr-v4-f1-f6"]["behavior_change_in_m9_0"])
        self.assertFalse(routing["fr-v4-f1-f6"]["automatic_conversion"])
        self.assertEqual(routing["fr-universal-card"]["formats"], ["9:16"])
        self.assertEqual(routing["fr-universal-card"]["implementation_starts_in"], "M9.1")

    def test_editor_contract_freezes_21_fields_29_lines_and_no_standalone(self):
        field_ids = self.contract["fields"]["fixed_ids"] + self.contract["fields"]["variable_ids"]
        self.assertEqual(len(field_ids), 21)
        self.assertEqual(len(set(field_ids)), 21)
        self.assertEqual(len(self.contract["lines"]["ids"]), 29)
        self.assertEqual(len(set(self.contract["lines"]["ids"])), 29)
        self.assertEqual(self.contract["component"]["excluded"], ["FR_CARD_EDITOR_STANDALONE.html"])
        self.assertNotIn("FR_CARD_EDITOR_STANDALONE.html", self.contract["component"]["files"])
        self.assertFalse(self.contract["integrated_policy"]["local_storage_source_of_truth"])
        self.assertFalse(self.contract["integrated_policy"]["persistent_data_urls"])

    def test_card_state_v2_boundary_is_reference_only_until_m9_1(self):
        self.assertEqual(self.card_state["status"], "reference_only_until_m9_1")
        self.assertEqual(self.card_state["card_definition"]["renderer_id"], "fr-universal-card")
        self.assertEqual(self.card_state["card_definition"]["formats"], ["9:16"])
        self.assertTrue(self.card_state["placement"]["ready_video"]["timeline_locked"])
        self.assertEqual(self.card_state["placement"]["raw_media"]["timebase"], "raw_sequence")
        self.assertEqual(self.card_state["placement"]["ready_video"]["timebase"], "ready_video_base")
        self.assertIn("data_url", self.card_state["asset_ref"]["forbidden"])
        self.assertTrue(self.card_state["compatibility_projection"]["projection_must_match"])

    def test_reference_state_requires_exact_default_ids_and_roles(self):
        fixed = [
            {"id": item, "role": "fixed", "text": item}
            for item in self.contract["fields"]["fixed_ids"]
        ]
        variable = [
            {"id": item, "role": "variable", "text": item}
            for item in self.contract["fields"]["variable_ids"]
        ]
        state = {
            "version": "1.1.0",
            "canvas": {"width": 941, "height": 1672, "ratio": "9:16"},
            "assets": {},
            "gridStyle": {"opacity": 0.36},
            "layers": {"background": True, "grid": True, "text": True, "logo": True},
            "fields": fixed + variable,
            "lines": [{"id": item} for item in self.contract["lines"]["ids"]],
        }
        golden.validate_editor_state(state, self.contract)
        duplicate = copy.deepcopy(state)
        duplicate["lines"][-1]["id"] = duplicate["lines"][0]["id"]
        with self.assertRaisesRegex(golden.GoldenMasterError, "duplicado"):
            golden.validate_editor_state(duplicate, self.contract)
        missing = copy.deepcopy(state)
        missing["fields"].pop()
        with self.assertRaisesRegex(golden.GoldenMasterError, "21 campos"):
            golden.validate_editor_state(missing, self.contract)

    def test_scenarios_cover_three_resolutions_four_shapes_and_thirteen_services(self):
        rows = self.scenarios["scenarios"]
        self.assertEqual(len(rows), 19)
        self.assertEqual(sum(len(row["resolutions"]) for row in rows), 21)
        baseline = next(row for row in rows if row["id"] == "baseline")
        self.assertEqual(
            baseline["resolutions"], [[941, 1672], [1080, 1920], [2160, 3840]],
        )
        shapes = {row["visual"]["shape"] for row in rows if "visual" in row}
        services = {
            row["visual"]["service_key"] for row in rows
            if row.get("visual", {}).get("kind") == "service_catalog"
        }
        self.assertEqual(shapes, {"circle", "square", "rounded", "full"})
        self.assertEqual(services, self.service_keys)
        self.assertGreaterEqual(self.scenarios["repeat_each_render"], 2)

    def test_font_inputs_are_pinned_and_not_runtime_or_release_dependencies(self):
        self.assertFalse(self.fonts["redistribution_in_fr_autoedite"])
        self.assertFalse(self.fonts["runtime_dependency"])
        self.assertRegex(self.fonts["commit"], r"^[0-9a-f]{40}$")
        for row in self.fonts["fonts"]:
            with self.subTest(font=row["file"]):
                self.assertRegex(row["sha256"], r"^[0-9a-f]{64}$")
                self.assertEqual(row["license_id"], "OFL-1.1")
                self.assertFalse(Path(row["source_path"]).is_absolute())

    def test_real_local_component_matches_frozen_hashes_when_available(self):
        source = ROOT / "FR_CARD_EDITOR_UNIVERSAL_v1.1.0"
        if not source.is_dir():
            return
        checked = golden.validate_component(source, self.contract)
        self.assertEqual(set(checked), set(self.contract["component"]["files"]))

    def test_local_golden_manifest_verifies_when_generated(self):
        output = ROOT / "FR_CARD_EDITOR_UNIVERSAL_v1.1.0" / ".m9-goldens"
        if not (output / "GOLDEN_MANIFEST.json").is_file():
            return
        manifest = golden.verify_existing(output)
        self.assertEqual(len(manifest["scenarios"]), 19)
        self.assertEqual(
            sum(len(row["artifacts"]) for row in manifest["scenarios"]), 21,
        )

    def test_m9_tracked_changes_contain_no_external_editor_binary(self):
        result = subprocess.run(
            ["git", "ls-files", "--", "FR_CARD_EDITOR_UNIVERSAL_v1.1.0", "local_components/fr-card-editor"],
            cwd=ROOT, check=True, capture_output=True, text=True,
        )
        self.assertEqual(result.stdout.strip(), "")
        for path in (ROOT / "contracts" / "m9").rglob("*"):
            if path.is_file():
                self.assertLess(path.stat().st_size, 256 * 1024)
                self.assertNotIn("data:image/", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
