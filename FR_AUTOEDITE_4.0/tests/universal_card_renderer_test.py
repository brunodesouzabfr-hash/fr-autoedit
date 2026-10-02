#!/usr/bin/env python3
"""M9.3: renderer universal determinístico e comparação visual explícita."""
from __future__ import annotations

import copy
import hashlib
from io import BytesIO
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "tests"))

import card_state_v2 as cards  # noqa: E402
import card_state_v2_test as m91_fixture  # noqa: E402
import service_catalog_v2 as services  # noqa: E402
import universal_card_renderer as renderer  # noqa: E402


LOCAL_COMPONENT = ROOT / "FR_CARD_EDITOR_UNIVERSAL_v1.1.0"
LOCAL_GOLDENS = LOCAL_COMPONENT / ".m9-goldens"
FONT_ROOT = LOCAL_GOLDENS / "font-cache"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def local_suite_available() -> bool:
    required = [
        LOCAL_GOLDENS / "GOLDEN_MANIFEST.json",
        LOCAL_GOLDENS / "states" / "baseline.editor.json",
        LOCAL_GOLDENS / "images" / "baseline-941x1672.png",
        LOCAL_COMPONENT / "assets" / "background-fr-hd.png",
        LOCAL_COMPONENT / "assets" / "logo-fr.png",
        FONT_ROOT / "CormorantGaramond.ttf",
        FONT_ROOT / "Rokkitt.ttf",
        FONT_ROOT / "ShareTechMono-Regular.ttf",
        FONT_ROOT / "StardosStencil-Regular.ttf",
        FONT_ROOT / "StardosStencil-Bold.ttf",
    ]
    return all(path.is_file() for path in required)


def synthetic_pattern(path: Path) -> None:
    width, height = 1200, 900
    image = Image.new("RGB", (width, height), "#071d18")
    draw = ImageDraw.Draw(image)
    colors = ("#f6a700", "#1a6069", "#e6d6b5", "#ff6b00")
    draw.rectangle((0, 0, width // 2, height // 2), fill=colors[0])
    draw.rectangle((width // 2, 0, width, height // 2), fill=colors[1])
    draw.rectangle((0, height // 2, width // 2, height), fill=colors[2])
    draw.rectangle((width // 2, height // 2, width, height), fill=colors[3])
    for offset in range(0, min(width, height), 60):
        draw.line((0, offset, offset, 0), fill="#121318", width=8)
        draw.line((width - offset, height, width, height - offset), fill="#0a2f26", width=8)
    draw.ellipse((360, 210, 840, 690), outline="#ffffff", width=18)
    image.save(path, format="PNG", compress_level=6)


class UniversalCardRendererContractTest(unittest.TestCase):
    """Gates fechados que não dependem do pacote externo local."""

    @classmethod
    def setUpClass(cls):
        m91_fixture.CardStateV2Test.setUpClass()

    def setUp(self):
        fixture = m91_fixture.CardStateV2Test(
            methodName="test_valid_definition_and_instance_preserve_all_fields_lines_unicode_and_newlines"
        )
        fixture.setUp()
        self.catalog = fixture.catalog
        self.definition = fixture.definition
        self.instance = fixture.instance

    def test_missing_asset_is_rejected_before_any_apparent_render(self):
        with self.assertRaisesRegex(renderer.UniversalCardRenderError, "arquivo ausente"):
            renderer.render_universal_card(
                self.definition,
                self.instance,
                self.catalog,
                {},
                ROOT / "diretorio-de-fontes-inexistente",
            )

    def test_renderer_never_falls_back_to_legacy(self):
        changed = copy.deepcopy(self.definition)
        changed["renderer_id"] = "fr-v4-f1-f6"
        with self.assertRaisesRegex(renderer.UniversalCardRenderError, "fr-universal-card"):
            renderer.render_universal_card(
                changed,
                self.instance,
                self.catalog,
                {},
                ROOT / "diretorio-de-fontes-inexistente",
            )

    def test_uncontracted_resolution_is_rejected(self):
        with self.assertRaisesRegex(renderer.UniversalCardRenderError, "não pertence"):
            renderer._validate_output_size(self.definition, (1000, 1000))


class UniversalCardRendererGoldenTest(unittest.TestCase):
    """Exercita os assets locais não redistribuíveis quando eles existem."""

    @classmethod
    def setUpClass(cls):
        if not local_suite_available():
            raise unittest.SkipTest(
                "goldens/assets/fontes M9.0 locais não estão disponíveis neste checkout"
            )
        cls.temporary = tempfile.TemporaryDirectory(prefix="fr-m9-renderer-test-")
        cls.temp_root = Path(cls.temporary.name)
        cls.synthetic = cls.temp_root / "m9-synthetic-pattern.png"
        synthetic_pattern(cls.synthetic)
        cls.manifest = json.loads(
            (LOCAL_GOLDENS / "GOLDEN_MANIFEST.json").read_text(encoding="utf-8")
        )
        cls.editor_contract = json.loads(
            (ROOT / "contracts" / "m9" / "fr_card_editor_1_1.json").read_text(encoding="utf-8")
        )
        cls.background = LOCAL_COMPONENT / "assets" / "background-fr-hd.png"
        cls.logo = LOCAL_COMPONENT / "assets" / "logo-fr.png"
        cls.catalog = {
            "component/background-fr-hd": {
                "asset_id": "component/background-fr-hd",
                "scope": "component",
                "sha256": sha256_file(cls.background),
            },
            "component/logo-fr": {
                "asset_id": "component/logo-fr",
                "scope": "component",
                "sha256": sha256_file(cls.logo),
            },
            "fixture/m9-synthetic-pattern": {
                "asset_id": "fixture/m9-synthetic-pattern",
                "scope": "project_asset",
                "sha256": sha256_file(cls.synthetic),
            },
        }
        cls.sources = {
            "component/background-fr-hd": cls.background,
            "component/logo-fr": cls.logo,
            "fixture/m9-synthetic-pattern": cls.synthetic,
        }
        for service_key in sorted(cards.SERVICE_KEYS):
            resolved = services.resolve_service_asset(
                service_key, "local_authorized", app_root=ROOT,
            )
            cls.catalog[resolved.asset_id] = resolved.asset_catalog_entry
            cls.sources[resolved.asset_id] = resolved.source_path
        baseline = cls.v2_state("baseline")
        cls.definition = {
            "schema_version": 2,
            "definition_id": "universal/golden-9x16",
            "definition_version": 1,
            "editor_schema": "fr-card-editor/1.1",
            "renderer_id": "fr-universal-card",
            "renderer_version": "1.0.0",
            "canvas": copy.deepcopy(cls.editor_contract["canvas"]),
            "component": copy.deepcopy(cls.editor_contract["component"]),
            "default_state": baseline,
            "capabilities": {
                "formats": ["9:16"],
                "state_sections": ["assets", "layers", "gridStyle", "fields", "lines"],
            },
        }
        cls._render_cache: dict[tuple[str, tuple[int, int]], renderer.UniversalCardRenderResult] = {}

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "temporary"):
            cls.temporary.cleanup()

    @classmethod
    def v2_state(cls, scenario: str) -> dict:
        state = json.loads(
            (LOCAL_GOLDENS / "states" / f"{scenario}.editor.json").read_text(encoding="utf-8")
        )
        state.pop("version")
        state.pop("canvas")
        visual = state["assets"]["visual"]
        state["assets"]["background"] = {
            "scope": "component",
            "asset_id": "component/background-fr-hd",
            "sha256": cls.catalog["component/background-fr-hd"]["sha256"],
        }
        state["assets"]["logo"] = {
            "scope": "component",
            "asset_id": "component/logo-fr",
            "sha256": cls.catalog["component/logo-fr"]["sha256"],
        }
        if scenario.startswith("service_"):
            asset_id = "medallion_" + scenario.removeprefix("service_")
            state["assets"]["visual"] = {
                "scope": "service_catalog",
                "asset_id": asset_id,
                "sha256": cls.catalog[asset_id]["sha256"],
            }
        elif visual:
            state["assets"]["visual"] = {
                "scope": "project_asset",
                "asset_id": "fixture/m9-synthetic-pattern",
                "sha256": cls.catalog["fixture/m9-synthetic-pattern"]["sha256"],
            }
        else:
            state["assets"]["visual"] = None
        return state

    @classmethod
    def instance(cls, scenario: str) -> dict:
        state = cls.v2_state(scenario)
        definition_ref = {
            "definition_id": cls.definition["definition_id"],
            "definition_version": cls.definition["definition_version"],
        }
        instance = {
            "schema_version": 2,
            "instance_id": f"GOLDEN-{scenario.replace('_', '-').upper()}",
            "definition_ref": definition_ref,
            "edit_origin": "manual",
            "placement": {
                "timebase": "raw_sequence",
                "sequence_index": 0,
                "duration_sec": 3.0,
            },
            "state": state,
            "state_digest": "",
        }
        if scenario.startswith("service_"):
            instance["service_key"] = scenario.removeprefix("service_")
        instance["state_digest"] = cards.renderable_state_digest(
            definition_ref, state, instance.get("service_key"),
        )
        return instance

    @classmethod
    def render(cls, scenario: str, size: tuple[int, int] = (941, 1672)):
        key = (scenario, size)
        if key not in cls._render_cache:
            cls._render_cache[key] = renderer.render_universal_card(
                cls.definition,
                cls.instance(scenario),
                cls.catalog,
                cls.sources,
                FONT_ROOT,
                output_size=size,
                usage_context="local_authorized",
            )
        return cls._render_cache[key]

    def test_same_state_is_byte_deterministic_and_no_field_or_line_is_discarded(self):
        instance = self.instance("baseline")
        first = renderer.render_universal_preview(
            self.definition, instance, self.catalog, self.sources, FONT_ROOT,
        )
        second = renderer.render_universal_preview(
            self.definition, instance, self.catalog, self.sources, FONT_ROOT,
        )
        expected_fields = [row["id"] for row in instance["state"]["fields"]]
        expected_lines = [row["id"] for row in instance["state"]["lines"]]
        self.assertEqual(first.png_bytes, second.png_bytes)
        self.assertEqual(first.sha256, second.sha256)
        self.assertEqual(first.report["field_ids"], expected_fields)
        self.assertEqual(first.report["rendered_field_ids"], expected_fields)
        self.assertEqual(first.report["line_ids"], expected_lines)
        self.assertEqual(first.report["rendered_line_ids"], expected_lines)
        self.assertEqual(
            {row["family"] for row in first.report["fonts"]},
            {"Cormorant Garamond", "Stardos Stencil"},
        )
        with Image.open(BytesIO(first.png_bytes)) as image:
            self.assertEqual(image.size, (941, 1672))
            self.assertEqual(image.mode, "RGB")

    def test_four_visual_shapes_preserve_crop_zoom_focal_point_and_opacity(self):
        expectations = {
            "visual_circle": ("circle", 1.73, [23, 77], 0.86),
            "visual_square": ("square", 2.1, [81, 19], 1),
            "visual_rounded": ("rounded", 1.35, [50, 50], 0.74),
            "visual_full": ("full", 1.18, [34, 62], 0.91),
        }
        hashes = set()
        for scenario, expected in expectations.items():
            with self.subTest(scenario=scenario):
                result = self.render(scenario)
                visual = result.report["visual"]
                self.assertEqual(visual["shape"], expected[0])
                self.assertEqual(visual["zoom"], expected[1])
                self.assertEqual(visual["focal_point"], expected[2])
                self.assertEqual(visual["opacity"], expected[3])
                hashes.add(result.sha256)
        self.assertEqual(len(hashes), 4)

    def test_preview_and_master_share_state_and_pipeline_with_contracted_dimensions(self):
        instance = self.instance("baseline")
        preview = self.render("baseline")
        master = renderer.render_universal_master(
            self.definition, instance, self.catalog, self.sources, FONT_ROOT,
        )
        type(self)._render_cache[("baseline", (2160, 3840))] = master
        middle = self.render("baseline", (1080, 1920))
        self.assertEqual(preview.state_digest, master.state_digest)
        self.assertEqual(preview.state_digest, middle.state_digest)
        self.assertEqual((preview.width, preview.height), (941, 1672))
        self.assertEqual((middle.width, middle.height), (1080, 1920))
        self.assertEqual((master.width, master.height), (2160, 3840))
        self.assertEqual(master.report["renderer_id"], "fr-universal-card")

    def test_layers_are_honored_without_discarding_the_structured_state(self):
        instance = self.instance("baseline")
        instance["state"]["layers"] = {
            "background": False,
            "grid": False,
            "text": False,
            "logo": False,
        }
        instance["state_digest"] = cards.renderable_state_digest(
            instance["definition_ref"], instance["state"],
        )
        result = renderer.render_universal_preview(
            self.definition, instance, self.catalog, self.sources, FONT_ROOT,
        )
        with Image.open(BytesIO(result.png_bytes)) as image:
            self.assertEqual(image.getpixel((0, 0)), (10, 47, 38))
            self.assertEqual(image.getpixel((470, 836)), (10, 47, 38))
        self.assertEqual(result.report["rendered_field_ids"], [])
        self.assertEqual(result.report["rendered_line_ids"], [])
        self.assertEqual(len(result.report["field_ids"]), 21)
        self.assertEqual(len(result.report["line_ids"]), 29)

    def test_missing_asset_bad_hash_and_unregistered_font_are_rejected(self):
        instance = self.instance("baseline")
        sources = dict(self.sources)
        sources.pop("component/logo-fr")
        with self.assertRaisesRegex(renderer.UniversalCardRenderError, "arquivo ausente"):
            renderer.render_universal_preview(
                self.definition, instance, self.catalog, sources, FONT_ROOT,
            )

        altered = self.temp_root / "altered-background.png"
        Image.new("RGB", (8, 8), "red").save(altered)
        sources = dict(self.sources)
        sources["component/background-fr-hd"] = altered
        with self.assertRaisesRegex(renderer.UniversalCardRenderError, "SHA-256"):
            renderer.render_universal_preview(
                self.definition, instance, self.catalog, sources, FONT_ROOT,
            )

        unknown = self.instance("baseline")
        unknown["state"]["fields"][0]["font"] = "Arial"
        unknown["state_digest"] = cards.renderable_state_digest(
            unknown["definition_ref"], unknown["state"],
        )
        with self.assertRaisesRegex(renderer.UniversalCardRenderError, "não registrado"):
            renderer.render_universal_preview(
                self.definition, unknown, self.catalog, self.sources, FONT_ROOT,
            )

        altered_fonts = self.temp_root / "altered-fonts"
        if altered_fonts.exists():
            shutil.rmtree(altered_fonts)
        shutil.copytree(FONT_ROOT, altered_fonts)
        with (altered_fonts / "CormorantGaramond.ttf").open("ab") as handle:
            handle.write(b"m9-hash-divergente")
        with self.assertRaisesRegex(renderer.UniversalCardRenderError, "SHA-256 divergente"):
            renderer.render_universal_preview(
                self.definition, instance, self.catalog, self.sources, altered_fonts,
            )

        wrong_version = copy.deepcopy(self.definition)
        wrong_version["renderer_version"] = "9.9.9"
        with self.assertRaisesRegex(renderer.UniversalCardRenderError, "Versão do renderer"):
            renderer.render_universal_preview(
                wrong_version, instance, self.catalog, self.sources, FONT_ROOT,
            )

    def test_golden_differences_are_measured_and_never_hidden(self):
        fidelity = json.loads(
            (ROOT / "contracts" / "m9" / "renderer_fidelity_v1.json").read_text(
                encoding="utf-8"
            )
        )
        scenarios = fidelity["scenarios"]
        acceptance = fidelity["acceptance"]
        manifest_rows = {row["id"]: row for row in self.manifest["scenarios"]}
        reports = {}
        for scenario in scenarios:
            for artifact in manifest_rows[scenario]["artifacts"]:
                size = (artifact["width"], artifact["height"])
                result = self.render(scenario, size)
                golden = LOCAL_GOLDENS / artifact["file"]
                report = renderer.compare_with_golden(result, golden)
                key = f"{scenario}-{size[0]}x{size[1]}"
                reports[key] = report
                self.assertEqual(report["golden_sha256"], artifact["sha256"])
                self.assertIn(report["status"], {"exact", "divergent"})
                self.assertGreaterEqual(report["mean_absolute_error"], 0)
                self.assertLessEqual(report["mean_absolute_error"], 255)
                self.assertGreaterEqual(report["changed_pixel_ratio"], 0)
                self.assertLessEqual(report["changed_pixel_ratio"], 1)
        print("M9.3 GOLDEN METRICS " + json.dumps(reports, sort_keys=True))
        for key, report in reports.items():
            with self.subTest(artifact=key):
                self.assertLessEqual(
                    report["mean_absolute_error"],
                    acceptance["maximum_mean_absolute_error"],
                )
                self.assertLessEqual(
                    report["root_mean_square_error"],
                    acceptance[
                        "maximum_root_mean_square_error_941x1672"
                        if (report["width"], report["height"]) == (941, 1672)
                        else "maximum_root_mean_square_error_scaled"
                    ],
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
