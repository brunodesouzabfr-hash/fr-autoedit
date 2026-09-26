#!/usr/bin/env python3
"""M6: snapshot limpo, determinístico, atômico e importável."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import ai_package_v2 as package_v2  # noqa: E402
import fr_autoedite as fr  # noqa: E402
import master_contract  # noqa: E402
import project_scope  # noqa: E402
from studio import StudioState  # noqa: E402


class AiPackageV2Test(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="fr-ai-package-v2-")
        root = Path(self.temporary.name)
        self.state = StudioState(ROOT, root / "Studio")
        self.project = Path(self.state.create_project("Pacote V2")['path'])
        image = (ROOT / "assets" / "services" / "pintura.png").read_bytes()
        media = []
        for index in range(1, 4):
            relative = f"proxies/M{index:04d}_PROXY.png"
            source_relative = f"originais/imagem-{index}.png"
            path = self.project / relative
            source = self.project / source_relative
            path.parent.mkdir(parents=True, exist_ok=True)
            source.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(image)
            source.write_bytes(image)
            media.append({
                "id": f"M{index:04d}", "status": "ok", "media_type": "image",
                "filename": f"imagem-{index}.png", "proxy_path": relative,
                "source_path": source_relative, "duration_sec": 0,
                "width": 512, "height": 512, "has_audio": False,
            })
        self.manifest = {"schema_version": 3, "input_mode": "raw_media", "media": media}
        project_scope.write(self.project / "MANIFESTO_MEDIA.json", self.manifest)
        self.answers = self.state.load_config(self.project)
        self.answers["project"].update(name="Pacote atual", client="Cliente atual", location="Local atual")
        self.answers["social"].update(enabled=False, reels_enabled=False, carousel_enabled=False, stories_enabled=False)
        self.answers["cards"]["generate_previews"] = False
        project_scope.write(self.project / "QUESTIONARIO_RESPONDIDO.json", self.answers)
        self.plan = {"segments": [{
            "segment_id": "S0001", "type": "media", "media_id": "M0001",
            "media_type": "image", "start_sec": 0, "duration_sec": 3,
            "transition": "cut", "include_in": ["branded", "clean"], "enabled": True,
        }]}
        project_scope.write(self.project / "EDIT_PLAN.json", self.plan)
        context = self.project / "_ENTRADA" / "CONTEXTO_PROJETO.md"
        context.parent.mkdir(parents=True, exist_ok=True)
        context.write_text("Contexto factual atual.", encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def hashes(root: Path) -> dict[str, str]:
        return {
            name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in package_v2.DETERMINISTIC_FILES
        }

    def test_clean_deterministic_snapshot_and_current_state(self):
        package_v2.generate_snapshot(self.project, self.answers, self.manifest)
        root = self.project / "PACOTE_PARA_IA" / "V2"
        first = self.hashes(root)
        response = self.project / "PACOTE_PARA_IA" / "05_RESPOSTA_DA_IA_IMPORTAR_AQUI.md"
        response.parent.mkdir(parents=True, exist_ok=True)
        response.write_text("DECISAO_ANTIGA_NAO_VAZAR", encoding="utf-8")
        stale = copy.deepcopy(self.plan)
        stale["segments"][0]["decision_reason"] = "DECISAO_ANTIGA_NAO_VAZAR"
        project_scope.write(self.project / "EDIT_PLAN.json", stale)
        package_v2.generate_snapshot(self.project, self.answers, self.manifest)
        self.assertEqual(first, self.hashes(root))
        combined = b"".join((root / name).read_bytes() for name in package_v2.DETERMINISTIC_FILES)
        self.assertNotIn(b"DECISAO_ANTIGA_NAO_VAZAR", combined)
        self.assertEqual(response.read_text(encoding="utf-8"), "DECISAO_ANTIGA_NAO_VAZAR")
        task = project_scope.read(root / "EDIT_TASK.json", {})
        self.assertEqual(task["mode"], "new_script")
        self.assertIsNone(task["base"])
        changed = copy.deepcopy(self.answers)
        changed["project"]["client"] = "Cliente novo"
        documents = package_v2.build_snapshot(self.project, changed, self.manifest)
        self.assertNotEqual(
            documents["PACKAGE_DESCRIPTOR.json"]["snapshot_id"],
            project_scope.read(root / "PACKAGE_DESCRIPTOR.json", {})["snapshot_id"],
        )

    def test_revise_has_explicit_base_and_inventory_is_complete(self):
        documents = package_v2.build_snapshot(
            self.project, self.answers, self.manifest,
            mode="revise_edit", base_plan=self.plan,
        )
        task = documents["EDIT_TASK.json"]
        self.assertEqual(task["base"]["edit_plan"], self.plan)
        self.assertEqual(task["base"]["revision"], project_scope.digest(self.plan))
        inventory = documents["MEDIA_MANIFEST.json"]
        self.assertEqual(inventory["eligible_asset_ids"], ["M0001", "M0002", "M0003"])
        self.assertEqual(len(inventory["proxy_files"]), 3)
        self.assertEqual(inventory["integrity_level"], "structural_m6_pending_lineage_m7")
        self.assertEqual(
            documents["PACKAGE_DESCRIPTOR.json"]["integrity_status"],
            "m6_structural_only_m7_required",
        )

    def test_missing_corrupt_and_invalid_window_fail_without_partial_publish(self):
        package_v2.generate_snapshot(self.project, self.answers, self.manifest)
        root = self.project / "PACOTE_PARA_IA" / "V2"
        before = self.hashes(root)
        missing = copy.deepcopy(self.manifest)
        missing["media"][0]["proxy_path"] = "proxies/ausente.png"
        with self.assertRaisesRegex(package_v2.AiPackageV2Error, "ausente"):
            package_v2.generate_snapshot(self.project, self.answers, missing)
        self.assertEqual(before, self.hashes(root))
        corrupt = copy.deepcopy(self.manifest)
        corrupt_path = self.project / corrupt["media"][1]["proxy_path"]
        corrupt_path.write_bytes(b"nao-e-imagem")
        with self.assertRaisesRegex(package_v2.AiPackageV2Error, "corrompido"):
            package_v2.generate_snapshot(self.project, self.answers, corrupt)
        self.assertEqual(before, self.hashes(root))
        corrupt_path.write_bytes((ROOT / "assets" / "services" / "pintura.png").read_bytes())
        invalid = copy.deepcopy(self.manifest)
        invalid["media"][2].update(
            media_type="video", duration_sec=2, scene_start_sec=1, scene_end_sec=4,
        )
        with self.assertRaisesRegex(package_v2.AiPackageV2Error, "janela"):
            package_v2.build_snapshot(
                self.project, self.answers, invalid,
                probe=lambda _path: {"duration_sec": 2, "width": 10, "height": 10},
            )

    def test_export_contains_only_v2_contract_and_all_proxies(self):
        outputs = fr.create_chatgpt_package(self.project, self.answers)
        self.assertTrue(outputs)
        with zipfile.ZipFile(outputs[0]) as archive:
            names = set(archive.namelist())
            for name in package_v2.DETERMINISTIC_FILES:
                self.assertIn(name, names)
            self.assertNotIn("EDIT_PLAN.json", names)
            self.assertFalse(any("RESPOSTA" in name for name in names))
            for index in range(1, 4):
                self.assertIn(f"proxies/M{index:04d}_PROXY.png", names)

    def test_import_v1_and_v2(self):
        legacy = fr.generate_ai_editing_brief(
            self.project, answers=self.answers, plan=self.plan, manifest=self.manifest,
        )
        legacy_bundle = master_contract.inspect_file(vars(fr), self.project, legacy)
        self.assertEqual(legacy_bundle["main_timeline"]["segments"][0]["media_id"], "M0001")
        package_v2.generate_snapshot(self.project, self.answers, self.manifest)
        descriptor = project_scope.read(
            self.project / "PACOTE_PARA_IA" / "V2" / "PACKAGE_DESCRIPTOR.json", {},
        )
        payload = fr.parse_ai_editing_brief(legacy)
        response = self.project / "resposta-v2.json"
        project_scope.write(response, {
            "schema_version": 2,
            "package_snapshot_id": descriptor["snapshot_id"],
            "edit_plan": payload,
        })
        v2_bundle = master_contract.inspect_file(vars(fr), self.project, response)
        self.assertEqual(v2_bundle["main_timeline"], legacy_bundle["main_timeline"])
        project_scope.write(self.project / "_CONTROLE" / "ROTEIRO_IMPORT_SOURCE.json", {
            "relative_path": response.relative_to(self.project).as_posix(),
            "sha256": hashlib.sha256(response.read_bytes()).hexdigest(),
            "format": "v2_json",
        })
        command = self.state._command_for(self.project, "brief-apply")
        self.assertEqual(Path(command[-1]), response)
        report = master_contract.apply_file(vars(fr), self.project, response)
        self.assertEqual(report["status"], "applied_requires_visual_review")
        self.assertEqual(
            (self.project / "PACOTE_PARA_IA" / "V2" / "EDIT_PLAN_RESPONSE.json").read_bytes(),
            response.read_bytes(),
        )
        wrong = project_scope.read(response, {})
        wrong["package_snapshot_id"] = "0" * 64
        project_scope.write(response, wrong)
        with self.assertRaisesRegex(package_v2.AiPackageV2Error, "snapshot atual"):
            master_contract.inspect_file(vars(fr), self.project, response)


if __name__ == "__main__":
    unittest.main(verbosity=2)
