#!/usr/bin/env python3
"""Regressões do empacotamento, documentação e instaladores beta-next."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import empacotar_release_v4 as packager  # noqa: E402


class ReleasePackagerTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="fr-release-hardening-")
        self.root = Path(self.temporary.name) / "FR_AUTOEDITE_4.0"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)

    def tearDown(self):
        self.temporary.cleanup()

    def write(self, relative: str, data: bytes = b"fixture") -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def test_archive_contains_only_tracked_permitted_files(self):
        external_contract = {
            "component": {
                "distribution": "local_only_pending_license",
                "files": {
                    "assets/original.png": {"sha256": hashlib.sha256(b"external").hexdigest()},
                },
            },
        }
        permitted = {
            "README.md": b"release",
            "app/main.py": b"print('ok')\n",
            "assets/logo.png": b"synthetic-product-asset",
            "contracts/m9/fr_card_editor_1_1.json": json.dumps(external_contract).encode("utf-8"),
        }
        forbidden = [
            "CODEX_EXECUTION_PACK/00_READ_FIRST.md",
            "README CODEX.TXT",
            "promptcodexpart1.txt",
            "promptcodexpart2.txt",
            "promptcodexpart3.txt",
            "FR_CARD_EDITOR_UNIVERSAL_v1.1.0/index.html",
            "local_components/fr-card-editor/1.1.0/index.html",
            "FR_CARD_EDITOR_STANDALONE.html",
            "RELEASE_MANIFEST.json",
            "Studio/projeto/QUESTIONARIO_RESPONDIDO.json",
            "originais/foto.png",
            "assets/video-pessoal.mp4",
            "tests/__pycache__/cache.pyc",
            "foto-pessoal.jpg",
        ]
        for relative, data in permitted.items():
            self.write(relative, data)
        for relative in forbidden:
            self.write(relative)
        subprocess.run(["git", "-C", str(self.root), "add", "-A"], check=True)
        self.write("nao-versionado.txt", b"private")

        target = Path(self.temporary.name) / "release.zip"
        manifest = packager.create_code_archive(self.root, target)
        prefix = packager.PREFIX.as_posix() + "/"
        with zipfile.ZipFile(target) as archive:
            name_list = archive.namelist()
            names = set(name_list)
            embedded = json.loads(archive.read(prefix + "RELEASE_MANIFEST.json"))

        self.assertEqual(manifest, embedded)
        self.assertEqual(manifest["selection"], "git-ls-files-allowlist")
        self.assertEqual(
            manifest["external_component_asset_audit"],
            "passed-by-path-and-sha256",
        )
        self.assertEqual(len(name_list), len(names))
        self.assertEqual({row["path"] for row in manifest["files"]}, set(permitted))
        self.assertEqual(
            names,
            {prefix + relative for relative in permitted} | {prefix + "RELEASE_MANIFEST.json"},
        )
        self.assertFalse(any("nao-versionado" in name for name in names))
        self.assertEqual(sum(name.endswith("/RELEASE_MANIFEST.json") for name in name_list), 1)
        for relative in (item for item in forbidden if item != "RELEASE_MANIFEST.json"):
            self.assertFalse(any(name.endswith(relative) for name in names), relative)

    def test_archive_rejects_external_component_bytes_even_if_renamed(self):
        external = b"synthetic-external-component-asset"
        self.write("README.md", b"release")
        subprocess.run(["git", "-C", str(self.root), "add", "-A"], check=True)
        target = Path(self.temporary.name) / "blocked.zip"
        with self.assertRaisesRegex(RuntimeError, "Contrato ausente do componente externo"):
            packager.create_code_archive(self.root, target)

        contract = {
            "component": {
                "distribution": "local_only_pending_license",
                "files": {
                    "assets/original.png": {
                        "sha256": hashlib.sha256(external).hexdigest(),
                    },
                },
            },
        }
        self.write(
            "contracts/m9/fr_card_editor_1_1.json",
            json.dumps(contract).encode("utf-8"),
        )
        self.write("assets/renamed-and-tracked.png", external)
        subprocess.run(["git", "-C", str(self.root), "add", "-A"], check=True)

        with self.assertRaisesRegex(RuntimeError, "Assets externos do Card Editor"):
            packager.create_code_archive(self.root, target)
        self.assertFalse(target.exists())


class ReleaseDocumentationTest(unittest.TestCase):
    DOCUMENTS = (
        ROOT / "README.md",
        ROOT / "docs/GUIA_INSTALACAO_ATUALIZACAO_4_0.md",
        ROOT / "CHANGELOG.md",
    )

    def test_autoedit_commands_and_beta_label_are_documented(self):
        required = (
            "FR AutoEdite 4.0 beta-next",
            "fr-autoedite autoeditar --projeto /CAMINHO/DO/PROJETO",
            "--modo automatico",
            "--modo cronologico",
            "--modo alfabetico",
            "--modo aleatorio --seed 731",
            "--aplicar",
            "--draft",
            "--somente",
            "branded|clean|both",
            "rollback_version",
            "ready_video",
            "originais",
            "proxies",
        )
        for document in self.DOCUMENTS:
            normalized = " ".join(document.read_text(encoding="utf-8").split())
            for item in required:
                with self.subTest(document=document.name, item=item):
                    self.assertIn(item, normalized)

    def test_documented_autoedit_flags_exist_in_cli(self):
        result = subprocess.run(
            [str(ROOT / "fr-autoedite"), "autoeditar", "--help"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        for item in ("--projeto", "--modo", "--seed", "--aplicar", "--draft", "--somente"):
            self.assertIn(item, result.stdout)
        for mode in ("automatico", "cronologico", "alfabetico", "aleatorio"):
            self.assertIn(mode, result.stdout)
        for output in ("branded", "clean", "both"):
            self.assertIn(output, result.stdout)

    def test_installers_derive_supported_version_from_version_file(self):
        self.assertEqual(ROOT.name, "FR_AUTOEDITE_4.0")
        self.assertRegex((ROOT / "VERSION").read_text(encoding="utf-8").strip(), r"^4\.\d+(?:\.\d+)?-candidate$")
        scripts = (
            ROOT / "INSTALAR_EM_OUTRO_COMPUTADOR.sh",
            ROOT / "ATUALIZAR_CORRECAO_CARDS.sh",
            ROOT / "ATUALIZAR_FR_AUTOEDITE_3.3.1.sh",
        )
        for script in scripts:
            content = script.read_text(encoding="utf-8")
            with self.subTest(script=script.name):
                self.assertIn("VERSION", content)
                self.assertIn("3.4.0|4.*-candidate", content)
                self.assertIn("fr_expected_banner", content)
                self.assertNotIn('!= "FR AutoEdite 3.4.0"', content)
        updater = (ROOT / "ATUALIZAR_FR_AUTOEDITE_3.4.0.sh").read_text(encoding="utf-8")
        self.assertIn("ATUALIZAR_FR_AUTOEDITE_3.3.1.sh", updater)
        v4_installer = (ROOT / "scripts/aplicar_atualizacao_v4.py").read_text(encoding="utf-8")
        self.assertIn("FR_AUTOEDITE_4.0", v4_installer)

    def test_m9_release_gates_are_explicit(self):
        report = (ROOT / "docs" / "RELATORIO_VALIDACAO_4_0.md").read_text(encoding="utf-8")
        provenance = (ROOT / "docs" / "CARD_EDITOR_LOCAL_PROVENANCE.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        for item in (
            "M9.8",
            "fr-autoedite-card/2",
            "revisão humana",
            "licença",
            "redistribuição",
        ):
            with self.subTest(item=item):
                self.assertIn(item, report + provenance + changelog)
        self.assertIn("passed-by-path-and-sha256", report)
        self.assertIn("local_only_pending_license", provenance)


if __name__ == "__main__":
    unittest.main(verbosity=2)
