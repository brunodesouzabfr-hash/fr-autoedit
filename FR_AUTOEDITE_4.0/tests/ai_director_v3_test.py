#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import ai_director_v3 as director  # noqa: E402
import fr_autoedite as fr  # noqa: E402
import master_contract  # noqa: E402
import project_scope  # noqa: E402
from studio import StudioState  # noqa: E402


class AiDirectorV3Test(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="fr-ai-director-v3-")
        root = Path(self.tmp.name)
        self.state = StudioState(ROOT, root / "Studio")
        self.project = Path(self.state.create_project("Diretor V3")["path"])
        image = (ROOT / "assets" / "services" / "pintura.png").read_bytes()
        media = []
        for index in range(1, 4):
            proxy = f"proxies/M{index:04d}_PROXY.png"
            source = f"originais/M{index:04d}.png"
            (self.project / proxy).parent.mkdir(parents=True, exist_ok=True)
            (self.project / source).parent.mkdir(parents=True, exist_ok=True)
            (self.project / proxy).write_bytes(image)
            (self.project / source).write_bytes(image)
            media.append({
                "id": f"M{index:04d}", "status": "ok", "media_type": "image",
                "proxy_path": proxy, "source_path": source, "duration_sec": 0,
                "width": 512, "height": 512, "has_audio": False,
                "excluded_from_auto_edit": index == 3,
            })
        self.manifest = {"schema_version": 3, "input_mode": "raw_media", "media": media}
        project_scope.write(self.project / "MANIFESTO_MEDIA.json", self.manifest)
        self.answers = self.state.load_config(self.project)
        self.answers["project"].update(name="Diretor", client="Cliente", location="Local")
        project_scope.write(self.project / "QUESTIONARIO_RESPONDIDO.json", self.answers)
        context = self.project / "_ENTRADA" / "CONTEXTO_PROJETO.md"
        context.parent.mkdir(parents=True, exist_ok=True)
        context.write_text("Contexto factual fornecido pelo usuário.", encoding="utf-8")
        project_scope.write(self.project / "EDIT_PLAN.json", {"contaminacao": "NAO_VAZAR"})
        project_scope.write(self.project / "_CONTROLE" / "CARD_STATE_V2.json", {"contaminacao": "NAO_VAZAR"})

    def tearDown(self):
        self.tmp.cleanup()

    def build_docs(self):
        return director.build_snapshot(
            self.project, self.answers, self.manifest,
            capabilities=fr.autonomous_ai_capabilities(),
            director_template=fr.autonomous_director_template(self.project, self.answers, self.manifest),
            app_version=fr.APP_VERSION,
        )

    def test_snapshot_is_virgin_but_preserves_human_exclusion(self):
        docs = self.build_docs()
        media = docs["MEDIA_MANIFEST.json"]
        self.assertEqual(media["eligible_asset_ids"], ["M0001", "M0002"])
        self.assertEqual(media["excluded_asset_ids"], ["M0003"])
        self.assertEqual(docs["PACKAGE_DESCRIPTOR.json"]["proxy_files"], [
            "proxies/M0001_PROXY.png", "proxies/M0002_PROXY.png",
        ])
        combined = b"".join(
            value.encode() if isinstance(value, str) else json.dumps(value, ensure_ascii=False).encode()
            for name, value in docs.items() if name in director.DETERMINISTIC_FILES
        )
        self.assertNotIn(b"NAO_VAZAR", combined)
        self.assertNotIn(b"NAO_VAZAR", combined)
        self.assertNotIn("EDIT_PLAN.json", docs["PACKAGE_DESCRIPTOR.json"]["deterministic_files"])
        self.assertNotIn("CARD_STATE_V2.json", docs["PACKAGE_DESCRIPTOR.json"]["deterministic_files"])

    def test_response_requires_exact_media_coverage_and_rejects_discarded_reference(self):
        docs = self.build_docs()
        director.publish_snapshot(self.project, docs)
        payload = fr.autonomous_director_template(self.project, self.answers, self.manifest)
        payload["main_timeline"] = {
            "contract_version": 2, "project": {"slug": self.project.name},
            "segments": [{
                "segment_id": "S0001", "type": "media", "enabled": True,
                "include_in": ["branded", "clean"], "media_id": "M0001",
                "start_sec": 0, "duration_sec": 3, "transition": "cut",
            }],
        }
        response = {
            "schema_version": 3,
            "package_snapshot_id": docs["PACKAGE_DESCRIPTOR.json"]["snapshot_id"],
            "mode": "autonomous_new_edit",
            "asset_decisions": [
                {"asset_id": "M0001", "decision": "use", "reason": "principal", "confidence": .9},
                {"asset_id": "M0002", "decision": "discard", "reason": "repetição", "confidence": .8},
            ],
            "director_plan": payload,
            "facts_to_confirm": [], "executive_summary": ["Edição autônoma"],
        }
        path = self.project / "response-v3.json"
        project_scope.write(path, response)
        loaded = director.load_v3_response(self.project, path)
        self.assertEqual(loaded["main_timeline"]["segments"][0]["media_id"], "M0001")
        bad = copy.deepcopy(response)
        bad["director_plan"]["main_timeline"]["segments"][0]["media_id"] = "M0002"
        project_scope.write(path, bad)
        with self.assertRaisesRegex(director.AiDirectorV3Error, "discard"):
            director.load_v3_response(self.project, path)
        unreferenced = copy.deepcopy(response)
        unreferenced["asset_decisions"][1]["decision"] = "use"
        project_scope.write(path, unreferenced)
        with self.assertRaisesRegex(director.AiDirectorV3Error, "não referencia"):
            director.load_v3_response(self.project, path)

    def test_v3_apply_materializes_card_state_after_plan_publish(self):
        docs = self.build_docs()
        director.publish_snapshot(self.project, docs)
        payload = fr.autonomous_director_template(self.project, self.answers, self.manifest)
        payload["configuration"]["social"].update(
            enabled=False, reels_enabled=False, stories_enabled=False, carousel_enabled=False
        )
        payload["main_timeline"] = {
            "contract_version": 2, "project": {"slug": self.project.name},
            "segments": [{
                "segment_id": "S0001", "type": "media", "enabled": True,
                "include_in": ["branded", "clean"], "media_id": "M0001",
                "start_sec": 0, "duration_sec": 3, "transition": "cut",
            }],
        }
        response = {
            "schema_version": 3,
            "package_snapshot_id": docs["PACKAGE_DESCRIPTOR.json"]["snapshot_id"],
            "mode": "autonomous_new_edit",
            "asset_decisions": [
                {"asset_id": "M0001", "decision": "use", "reason": "principal", "confidence": .9},
                {"asset_id": "M0002", "decision": "discard", "reason": "repetição", "confidence": .8},
            ],
            "director_plan": payload,
            "facts_to_confirm": [], "executive_summary": ["Edição autônoma"],
        }
        path = self.project / "response-v3-apply.json"
        project_scope.write(path, response)
        activation = {
            "status": "no_cards_discovered", "migration_version": "9.9.1",
            "counts": {"discovered": 0, "migrated": 0, "fallback": 0},
        }
        with patch("master_contract.universal_card_runtime.activate_project_cards", return_value=activation) as mocked:
            report = master_contract.apply_file(vars(fr), self.project, path)
        self.assertEqual(mocked.call_count, 1)
        self.assertEqual(report["card_activation"]["renderer_id"], "fr-universal-card")
        self.assertTrue((self.project / "_ENTRADA/AI_DIRECTOR_RESPONSE_V3.json").is_file())
        self.assertTrue((self.project / "EDIT_PLAN.json").is_file())

    def test_export_uses_v3_contract_and_does_not_bundle_fonts(self):
        # O manifesto precisa estar com integridade M7 para create_chatgpt_package; o fluxo de
        # produção cuida disso. Aqui validamos o writer diretamente com um ZIP pequeno.
        docs = self.build_docs()
        root = director.publish_snapshot(self.project, docs)
        target = self.project / "lot.zip"
        fr._write_chatgpt_archive(
            target, [root / name for name in director.DETERMINISTIC_FILES], [],
            [self.project / "proxies/M0001_PROXY.png"], self.project,
        )
        with zipfile.ZipFile(target) as archive:
            names = set(archive.namelist())
        self.assertIn("PROMPT_MESTRE_AUTONOMO.md", names)
        self.assertIn("CAPABILITIES.json", names)
        self.assertFalse(any(name.startswith("assets/fonts/") for name in names))
        self.assertNotIn("EDIT_PLAN.json", names)


if __name__ == "__main__":
    unittest.main(verbosity=2)
