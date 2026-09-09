#!/usr/bin/env python3
"""Regressões de cards, atualização de prévias e seleção de mídias."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import fr_autoedite as fr  # noqa: E402
import project_scope as scope  # noqa: E402
from studio import StudioState  # noqa: E402


SERVICES = ("eletrica", "hidraulica", "instalacao", "manutencao")


class CardPreviewRefreshTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="fr-card-preview-")
        root = Path(self.temporary.name)
        self.state = StudioState(ROOT, root / "Studio")
        self.project = Path(self.state.create_project("Cards atualizáveis")["path"])

    def tearDown(self):
        self.temporary.cleanup()

    def _plan(self, service_key: str) -> dict:
        service = fr.load_service_catalog()[service_key]
        family = service["visual_family"]
        return {
            "schema_version": 3,
            "project": {"slug": self.project.name, "name": "Cards atualizáveis"},
            "output": {"width": 360, "height": 640, "fps": 24},
            "segments": [{
                "segment_id": "S-CARD", "type": "card", "enabled": True,
                "card_kind": "service", "card_type": "service", "card_mode": "service",
                "service_card_enabled": True, "service_key": service_key,
                "service_id": service_key, "service_name": service["label"],
                "service_asset": service["asset"], "service_layout": service["layout"],
                "service_family": family, "card_family": family,
                "balloon_family": service["balloon_family"],
                "visual_motif": service["visual_motif"],
                "motion_hint": service["motion_hint"],
                "overlay_text": service["label"],
                "duration_sec": 3, "title": service["label"], "body": service["body"],
                "include_in": ["branded"],
            }],
        }

    def test_catalog_uses_four_real_assets(self):
        catalog = fr.load_service_catalog()
        for key in SERVICES:
            service = catalog[key]
            self.assertEqual(service["asset"], f"services/{key}.png")
            asset = ROOT / "assets" / service["asset"]
            self.assertTrue(asset.is_file(), asset)
            with Image.open(asset) as image:
                self.assertEqual(image.size[0], image.size[1], key)
            self.assertTrue(service["visual_family"])
            self.assertTrue(service["balloon_family"])
            self.assertTrue(service["motion_hint"])

    def test_new_service_and_style_replace_preview_version(self):
        plan_path = self.project / "EDIT_PLAN.json"
        first_plan = self._plan("eletrica")
        scope.write(plan_path, first_plan)
        initial_style = fr.load_card_style(self.project)
        initial_style["cards"]["always_generate_4k_masters"] = False
        scope.write(self.project / "CARD_STYLE.json", initial_style)
        first_outputs = fr.generate_card_previews(self.project, plan_path)
        first_registry = scope.read(self.project / "_CONTROLE/CARD_PREVIEWS.json")
        first_normal = next(item for item in first_registry["previews"] if not item["is_4k_master"])
        first_hash = fr.sha256_short(self.project / first_normal["relative"])

        second_plan = self._plan("hidraulica")
        scope.write(plan_path, second_plan)
        style = fr.load_card_style(self.project)
        style["palette"]["orange"] = "#FF7A00"
        scope.write(self.project / "CARD_STYLE.json", style)
        second_outputs = fr.generate_card_previews(self.project, plan_path)
        second_registry = scope.read(self.project / "_CONTROLE/CARD_PREVIEWS.json")
        second_normal = next(item for item in second_registry["previews"] if not item["is_4k_master"])

        self.assertEqual([p.relative_to(self.project) for p in first_outputs],
                         [p.relative_to(self.project) for p in second_outputs])
        self.assertNotEqual(first_registry["generation_id"], second_registry["generation_id"])
        self.assertNotEqual(first_registry["plan_sha256"], second_registry["plan_sha256"])
        self.assertNotEqual(first_normal["version"], second_normal["version"])
        self.assertNotEqual(first_hash, fr.sha256_short(self.project / second_normal["relative"]))
        self.assertEqual(second_normal["service_key"], "hidraulica")
        self.assertEqual(second_normal["card_family"], second_plan["segments"][0]["card_family"])
        self.assertFalse(list((self.project / "cards_editaveis").rglob("*.partial.png")))

        state = self.state.project_state(self.project)
        self.assertEqual({item["generation_id"] for item in state["card_previews"]},
                         {second_registry["generation_id"]})
        self.assertTrue(all(item["version"] for item in state["card_previews"]))

    def test_balloon_style_changes_service_preview(self):
        plan_path = self.project / "EDIT_PLAN.json"
        scope.write(plan_path, self._plan("instalacao"))
        style = fr.load_card_style(self.project)
        style["cards"]["always_generate_4k_masters"] = False
        style["cards"]["bubble_style"] = "glass"
        scope.write(self.project / "CARD_STYLE.json", style)
        first = fr.generate_card_previews(self.project, plan_path)[0]
        first_hash = fr.sha256_short(first)

        style["cards"]["bubble_style"] = "outline"
        scope.write(self.project / "CARD_STYLE.json", style)
        second = fr.generate_card_previews(self.project, plan_path)[0]
        registry = scope.read(self.project / "_CONTROLE/CARD_PREVIEWS.json")

        self.assertEqual(first, second)
        self.assertNotEqual(first_hash, fr.sha256_short(second))
        self.assertEqual(registry["style_signature"], fr.style_signature(
            fr.load_brand(), fr.load_card_style(self.project), self.project,
        ))

    def test_generation_without_cards_does_not_resurface_old_previews(self):
        plan_path = self.project / "EDIT_PLAN.json"
        scope.write(plan_path, self._plan("manutencao"))
        style = fr.load_card_style(self.project)
        style["cards"]["always_generate_4k_masters"] = False
        scope.write(self.project / "CARD_STYLE.json", style)
        old_preview = fr.generate_card_previews(self.project, plan_path)[0]
        self.assertTrue(old_preview.is_file())

        scope.write(plan_path, {"project": {"slug": self.project.name},
                                "output": {"width": 360, "height": 640}, "segments": []})
        self.assertEqual(fr.generate_card_previews(self.project, plan_path), [])
        self.assertEqual(self.state.project_state(self.project)["card_previews"], [])

    def test_unselected_media_is_not_rendered_but_stays_in_library(self):
        originals = self.project / "originais"
        proxies = self.project / "proxies"
        originals.mkdir(parents=True, exist_ok=True)
        proxies.mkdir(parents=True, exist_ok=True)
        image = (ROOT / "assets/services/pintura.png").read_bytes()
        for index in (1, 2):
            (originals / f"midia-{index}.png").write_bytes(image)
            (proxies / f"M000{index}_PROXY.png").write_bytes(image)
        manifest = {"media": [
            {"id": "M0001", "status": "ok", "media_type": "image", "filename": "midia-1.png",
             "source_path": "originais/midia-1.png", "proxy_path": "proxies/M0001_PROXY.png"},
            {"id": "M0002", "status": "ok", "media_type": "image", "filename": "midia-2.png",
             "source_path": "originais/midia-2.png", "proxy_path": "proxies/M0002_PROXY.png"},
        ]}
        plan = {"segments": [
            {"segment_id": "M1", "type": "media", "media_id": "M0001", "enabled": True,
             "duration_sec": 2, "include_in": ["branded", "clean"]},
            {"segment_id": "M2", "type": "media", "media_id": "M0002", "enabled": False,
             "duration_sec": 2, "include_in": ["branded", "clean"]},
        ]}
        scope.write(self.project / "MANIFESTO_MEDIA.json", manifest)
        scope.write(self.project / "EDIT_PLAN.json", plan)

        rendered = fr.render_segments_for_version(plan, "branded")
        self.assertEqual([item["media_id"] for item in rendered], ["M0001"])

        originals_in_library = {
            item["media_id"]: item for item in self.state.gallery_items(self.project)
            if item["category"] == "originais"
        }
        self.assertEqual(set(originals_in_library), {"M0001", "M0002"})
        self.assertTrue(originals_in_library["M0001"]["selected_in_plan"])
        self.assertEqual(originals_in_library["M0001"]["selection_status"], "selected")
        self.assertFalse(originals_in_library["M0002"]["selected_in_plan"])
        self.assertFalse(originals_in_library["M0002"]["visible_in_review"])
        self.assertEqual(originals_in_library["M0002"]["selection_status"], "not_used")
        self.assertTrue((originals / "midia-2.png").is_file())

    def test_preview_plan_carries_complete_service_state(self):
        answers = self.state.load_config(self.project)
        answers["service_intro"].update(enabled=True, service_key="manutencao")
        path = fr.build_card_preview_plan(self.project, answers)
        service_card = next(
            item for item in scope.read(path)["segments"] if item.get("card_kind") == "service"
        )
        for field in (
            "service_id", "service_name", "service_confidence", "service_card_enabled",
            "service_asset", "service_layout", "card_type", "card_family",
            "balloon_family", "visual_motif", "motion_hint", "overlay_text",
        ):
            self.assertIn(field, service_card)
        self.assertEqual(service_card["service_id"], "manutencao")
        self.assertEqual(service_card["service_asset"], "services/manutencao.png")


if __name__ == "__main__":
    unittest.main(verbosity=2)
