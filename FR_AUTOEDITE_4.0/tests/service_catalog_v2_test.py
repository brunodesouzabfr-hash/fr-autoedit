#!/usr/bin/env python3
"""M9.4: catálogo produtivo e gate local dos 13 cards SERVICE."""
from __future__ import annotations

import copy
from io import BytesIO
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

import card_state_v2 as cards  # noqa: E402
import service_catalog_v2 as services  # noqa: E402
import universal_card_renderer as renderer  # noqa: E402
import universal_card_renderer_test as m93_fixture  # noqa: E402


CATALOG_PATH = ROOT / "contracts" / "m9" / "service_catalog_v1.json"
MANIFEST_PATH = (
    ROOT / "assets" / "style_packs" / "fr_quiet_engineering_atelier_v2" / "manifest.json"
)
OPAQUE_KEYS = {
    "eletrica", "hidraulica", "iluminacao", "instalacao", "manutencao", "projetos_3d",
}


class ServiceCatalogV2ContractTest(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        self.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_product_catalog_has_exact_thirteen_real_services_and_verified_bytes(self):
        validated = services.validate_service_catalog(
            self.catalog, self.manifest, app_root=ROOT, verify_files=True,
        )
        rows = validated["services"]
        self.assertEqual(len(rows), 13)
        self.assertEqual({row["service_key"] for row in rows}, set(cards.SERVICE_KEYS))
        self.assertEqual(
            {row["asset_id"] for row in rows},
            {f"medallion_{key}" for key in cards.SERVICE_KEYS},
        )
        self.assertTrue(all(row["scope"] == "service_catalog" for row in rows))
        self.assertTrue(all(row["publicavel"] is False for row in rows))
        self.assertTrue(all(row["status"] == "installed_requires_review" for row in rows))
        self.assertTrue(all(row["visual_review_required"] is True for row in rows))
        self.assertFalse(validated["usage_policy"]["external_distribution_allowed"])
        self.assertFalse(validated["usage_policy"]["fallback_allowed"])
        self.assertEqual(validated["usage_policy"]["license_status"], "pending")
        self.assertEqual(validated["usage_policy"]["provenance_status"], "pending")
        self.assertEqual(validated["visual_policy"]["shape"], "circle")
        self.assertEqual(validated["visual_policy"]["crop"], "1:1")

    def test_all_thirteen_resolve_only_to_existing_pinned_assets_locally(self):
        for service_key in sorted(cards.SERVICE_KEYS):
            with self.subTest(service_key=service_key):
                resolved = services.resolve_service_asset(
                    service_key, "local_authorized", app_root=ROOT,
                    catalog=self.catalog, manifest=self.manifest,
                )
                row = next(
                    item for item in self.catalog["services"]
                    if item["service_key"] == service_key
                )
                source = self.manifest["assets"][f"medallion_{service_key}"]
                self.assertEqual(resolved.asset_id, f"medallion_{service_key}")
                self.assertEqual(resolved.asset_ref, {
                    "scope": "service_catalog",
                    "asset_id": f"medallion_{service_key}",
                    "sha256": source["normalized"]["sha256"],
                })
                self.assertEqual(resolved.source_path, ROOT / source["normalized_path"])
                self.assertEqual(resolved.original_path, ROOT / source["path"])
                self.assertEqual(
                    resolved.asset_catalog_entry["resolution_authority"],
                    "source_manifest",
                )
                self.assertEqual(
                    resolved.review["source_manifest"], self.catalog["source_manifest"],
                )
                self.assertEqual(resolved.review["resolution_authority"], "source_manifest")
                self.assertNotIn("fallback", resolved.asset_catalog_entry)
                self.assertFalse(resolved.review["publicavel"])
                self.assertTrue(resolved.review["visual_review_required"])
                self.assertFalse(resolved.review["external_distribution_allowed"])
                self.assertIn("revisão visual obrigatória", resolved.warnings[0])

        internal = services.resolve_service_asset(
            "alvenaria", "internal_production", app_root=ROOT,
            catalog=self.catalog, manifest=self.manifest,
        )
        self.assertEqual(internal.review["usage_context"], "internal_production")

    def test_six_opaque_assets_remain_explicit_and_warned(self):
        rows = {row["service_key"]: row for row in self.catalog["services"]}
        actual = {
            key for key, row in rows.items() if row["opaque_background_preserved"]
        }
        self.assertEqual(actual, OPAQUE_KEYS)
        for service_key in sorted(actual):
            resolved = services.resolve_service_asset(
                service_key, "local_authorized", app_root=ROOT,
                catalog=self.catalog, manifest=self.manifest,
            )
            self.assertTrue(resolved.review["opaque_background_preserved"])
            self.assertIn("opaque_background_preserved", resolved.review["warning_codes"])
            self.assertTrue(any("fundo opaco preservado" in item for item in resolved.warnings))

    def test_unknown_service_invalid_id_wrong_scope_and_changed_editorial_state_are_rejected(self):
        with self.assertRaisesRegex(services.ServiceCatalogV2Error, "serviço desconhecido"):
            services.resolve_service_asset(
                "servico_inventado", "local_authorized", app_root=ROOT,
                catalog=self.catalog, manifest=self.manifest,
            )
        with self.assertRaisesRegex(services.ServiceCatalogV2Error, "serviço desconhecido"):
            services.resolve_service_asset(
                {"key": "alvenaria"}, "local_authorized", app_root=ROOT,
                catalog=self.catalog, manifest=self.manifest,
            )

        cases = []
        invalid_id = copy.deepcopy(self.catalog)
        invalid_id["services"][0]["asset_id"] = "asset-inventado"
        cases.append(("asset_id", invalid_id))
        wrong_scope = copy.deepcopy(self.catalog)
        wrong_scope["services"][0]["scope"] = "project_asset"
        cases.append(("scope", wrong_scope))
        publishable = copy.deepcopy(self.catalog)
        publishable["services"][0]["publicavel"] = True
        cases.append(("publicavel", publishable))
        changed_status = copy.deepcopy(self.catalog)
        changed_status["services"][0]["status"] = "approved"
        cases.append(("status", changed_status))
        review_removed = copy.deepcopy(self.catalog)
        review_removed["services"][0]["visual_review_required"] = False
        cases.append(("visual_review_required", review_removed))
        for message, candidate in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(services.ServiceCatalogV2Error, message):
                    services.validate_service_catalog(
                        candidate, self.manifest, app_root=ROOT,
                    )

    def test_external_contexts_are_blocked_and_cannot_borrow_local_authorization(self):
        for context in ("external_publication", "external_distribution", "web", ""):
            with self.subTest(context=context):
                with self.assertRaisesRegex(
                    services.ServiceCatalogV2Error,
                    "bloqueado fora de local_authorized/internal_production",
                ):
                    services.resolve_service_asset(
                        "pintura", context, app_root=ROOT,
                        catalog=self.catalog, manifest=self.manifest,
                    )

    def _temporary_root(self):
        temporary = tempfile.TemporaryDirectory(prefix="fr-m9-service-catalog-")
        root = Path(temporary.name)
        (root / "templates").mkdir(parents=True)
        shutil.copy2(ROOT / "templates" / "service_catalog.json", root / "templates")
        return temporary, root

    def test_missing_and_hash_divergent_assets_fail_without_manifest_fallback(self):
        service_key = "alvenaria"
        index = next(
            index for index, row in enumerate(self.catalog["services"])
            if row["service_key"] == service_key
        )

        temporary, root = self._temporary_root()
        self.addCleanup(temporary.cleanup)
        with self.assertRaisesRegex(services.ServiceCatalogV2Error, "asset ausente"):
            services.resolve_service_asset(
                service_key, "local_authorized", app_root=root,
                catalog=self.catalog, manifest=self.manifest,
            )

        row = self.catalog["services"][index]
        for relative in (row["normalized_path"], row["original_path"]):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        with (root / row["normalized_path"]).open("ab") as handle:
            handle.write(b"m9-hash-divergente")
        with self.assertRaisesRegex(services.ServiceCatalogV2Error, "hash divergente"):
            services.resolve_service_asset(
                service_key, "local_authorized", app_root=root,
                catalog=self.catalog, manifest=self.manifest,
            )
        self.assertEqual(
            self.manifest["assets"][row["asset_id"]]["fallback"],
            "medallion_placeholder_tecnico",
        )


class ServiceCatalogV2RendererTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not m93_fixture.local_suite_available():
            raise unittest.SkipTest(
                "goldens/assets/fontes M9.0 locais não estão disponíveis neste checkout"
            )
        m93_fixture.UniversalCardRendererGoldenTest.setUpClass()
        cls.fixture = m93_fixture.UniversalCardRendererGoldenTest
        cls.results = {}

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "fixture"):
            cls.fixture.tearDownClass()

    @classmethod
    def render(cls, service_key: str, instance: dict | None = None):
        if instance is None and service_key in cls.results:
            return cls.results[service_key]
        current = instance or cls.fixture.instance("service_" + service_key)
        result = services.render_service_card(
            cls.fixture.definition,
            current,
            cls.fixture.catalog,
            cls.fixture.sources,
            m93_fixture.FONT_ROOT,
            usage_context="local_authorized",
            output_size=(941, 1672),
            app_root=ROOT,
        )
        if instance is None:
            cls.results[service_key] = result
        return result

    def test_all_thirteen_render_through_product_resolver_with_review_result(self):
        hashes = set()
        opaque = set()
        for service_key in sorted(cards.SERVICE_KEYS):
            with self.subTest(service_key=service_key):
                result = self.render(service_key)
                self.assertEqual(result.renderer_id, "fr-universal-card")
                self.assertTrue(result.report["visual_review_required"])
                self.assertEqual(len(result.report["asset_reviews"]), 1)
                review = result.report["asset_reviews"][0]
                self.assertEqual(review["service_key"], service_key)
                self.assertFalse(review["publicavel"])
                self.assertEqual(review["status"], "installed_requires_review")
                self.assertFalse(review["external_distribution_allowed"])
                self.assertEqual(review["license_status"], "pending")
                self.assertEqual(review["provenance_status"], "pending")
                self.assertTrue(any("revisão visual obrigatória" in item for item in result.report["warnings"]))
                if review["opaque_background_preserved"]:
                    opaque.add(service_key)
                    self.assertTrue(any("fundo opaco preservado" in item for item in result.report["warnings"]))
                hashes.add(result.sha256)
        self.assertEqual(opaque, OPAQUE_KEYS)
        self.assertEqual(len(hashes), 13)

    def test_circle_crop_zoom_focal_point_and_determinism_are_preserved(self):
        instance = self.fixture.instance("service_alvenaria")
        assets = instance["state"]["assets"]
        assets["visualShape"] = "circle"
        assets["visualSize"] = 389
        assets["visualZoom"] = 1.73
        assets["visualFocalX"] = 23
        assets["visualFocalY"] = 77
        first = self.render("alvenaria", instance)
        second = self.render("alvenaria", copy.deepcopy(instance))
        self.assertEqual(first.png_bytes, second.png_bytes)
        self.assertEqual(first.sha256, second.sha256)
        visual = first.report["visual"]
        self.assertEqual(visual["shape"], "circle")
        self.assertEqual(visual["crop"], "1:1")
        self.assertTrue(visual["perfect_circle"])
        self.assertEqual(visual["logical_box"][2:], [389.0, 389.0])
        self.assertEqual(visual["zoom"], 1.73)
        self.assertEqual(visual["focal_point"], [23, 77])

        mask = renderer._shape_mask((389, 389), "circle", 1.0, 1.0)
        self.assertEqual(mask.size, (389, 389))
        self.assertEqual(mask.getpixel((0, 0)), 0)
        self.assertEqual(mask.getpixel((194, 194)), 255)
        with Image.open(BytesIO(first.png_bytes)) as image:
            self.assertEqual(image.size, (941, 1672))

    def test_non_circle_service_and_direct_renderer_bypass_are_rejected(self):
        instance = self.fixture.instance("service_pintura")
        instance["state"]["assets"]["visualShape"] = "square"
        resolved = services.resolve_service_asset(
            "pintura", "local_authorized", app_root=ROOT,
        )
        with self.assertRaisesRegex(services.ServiceCatalogV2Error, "círculo perfeito"):
            services.bind_service_instance(instance, resolved)

        valid = self.fixture.instance("service_pintura")
        with self.assertRaisesRegex(renderer.UniversalCardRenderError, "asset SERVICE bloqueado"):
            renderer.render_universal_preview(
                self.fixture.definition,
                valid,
                self.fixture.catalog,
                self.fixture.sources,
                m93_fixture.FONT_ROOT,
            )

        untrusted_catalog = copy.deepcopy(self.fixture.catalog)
        untrusted_catalog["medallion_pintura"].pop("resolution_authority")
        with self.assertRaisesRegex(renderer.UniversalCardRenderError, "manifest-driven"):
            renderer.render_universal_preview(
                self.fixture.definition,
                valid,
                untrusted_catalog,
                self.fixture.sources,
                m93_fixture.FONT_ROOT,
                usage_context="local_authorized",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
