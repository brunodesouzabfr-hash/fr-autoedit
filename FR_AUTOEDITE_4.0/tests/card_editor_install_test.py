#!/usr/bin/env python3
"""Instalação reproduzível do Card Editor com fixture independente do checkout."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "scripts"))

from install_card_editor_local import FILES, install_component  # noqa: E402
from studio import StudioState  # noqa: E402


HTML = """<!doctype html>
<html><body><div>FR Card Editor Universal v1.1.0</div>
<img src="assets/logo-fr.png"><img src="assets/background-fr-hd.png">
<img src="assets/background-fr-source.png"><img src="assets/background-fr.png"><script>
const $=()=>({});let state={};const DEFAULT={};
window.FRCardEditor={reset(){},getConfig(){return {assets:{},fields:[]}},applyConfig(){}};
$("#saveLocal").onclick=()=>{try{localStorage.setItem("fr-card-editor-v1.1",JSON.stringify(state));toast("Estado salvo neste navegador")}catch{toast("Estado grande demais; exporte JSON")}};
try{let saved=localStorage.getItem("fr-card-editor-v1.1");if(saved)state=normalizeConfig(JSON.parse(saved))}catch{}render();resizeStage();
</script></body></html>
"""
PNG = b"\x89PNG\r\n\x1a\nsynthetic-fixture"


class CardEditorInstallTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fr-card-editor-install-")
        self.root = Path(self.temp.name)
        self.source = self.root / "source" / "FR_CARD_EDITOR_UNIVERSAL_v1.1.0"
        (self.source / "assets").mkdir(parents=True)
        (self.source / "index.html").write_text(HTML, encoding="utf-8")
        for relative in FILES[1:]:
            (self.source / relative).write_bytes(PNG)
        (self.source / "FR_CARD_EDITOR_STANDALONE.html").write_bytes(b"standalone-excluded")

    def tearDown(self):
        self.temp.cleanup()

    def assert_installed_subset(self, destination: Path) -> None:
        relative_files = {
            str(path.relative_to(destination))
            for path in destination.rglob("*")
            if path.is_file()
        }
        self.assertEqual(relative_files, {*FILES, "LOCAL_COMPONENT_MANIFEST.json"})
        manifest = json.loads((destination / "LOCAL_COMPONENT_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["component_version"], "1.1.0")
        self.assertEqual(manifest["provenance"]["source"], "provided_by_project_owner_for_local_integration")
        self.assertEqual(
            manifest["provenance"]["license_status"],
            "pending_before_external_publication_or_redistribution",
        )
        self.assertEqual(manifest["excluded_files"], ["FR_CARD_EDITOR_STANDALONE.html"])

    def test_directory_source_installs_only_modular_subset_and_studio_loads_it(self):
        clean_app = self.root / "clean-app"
        destination = clean_app / "local_components" / "fr-card-editor" / "1.1.0"
        with patch.dict(os.environ, {"FR_CARD_EDITOR_HOME": ""}):
            state = StudioState(clean_app, self.root / "workspace-before")
            self.assertFalse(state.card_editor_capabilities()["available"])
            install_component(self.source, destination)
            state = StudioState(clean_app, self.root / "workspace-after")
            capability = state.card_editor_capabilities()
            self.assertTrue(capability["available"])
            self.assertEqual(capability["component_source"], "installed_component")
            document = state.card_editor_document().decode("utf-8")

        self.assert_installed_subset(destination)
        self.assertNotIn("localStorage.getItem", document)
        self.assertNotIn("localStorage.setItem", document)
        self.assertIn('id="fr-autoedite-bridge"', document)
        self.assertIn("fr-autoedite-card-content/1", document)
        self.assertIn("/card-editor/assets/logo-fr.png?token=", document)

    def test_zip_source_with_outer_directory_is_reproducible(self):
        archive = self.root / "FR_CARD_EDITOR_UNIVERSAL_v1.1.0.zip"
        with zipfile.ZipFile(archive, "w") as output:
            for path in self.source.rglob("*"):
                if path.is_file():
                    output.write(path, Path(self.source.name) / path.relative_to(self.source))
        destination = self.root / "installed-from-zip"
        install_component(archive, destination)
        self.assert_installed_subset(destination)

    def test_application_installer_uses_explicit_external_source_without_standalone(self):
        xdg_data = self.root / "xdg-data"
        xdg_bin = self.root / "xdg-bin"
        environment = os.environ.copy()
        environment.update({
            "HOME": str(self.root / "home"),
            "XDG_DATA_HOME": str(xdg_data),
            "XDG_BIN_HOME": str(xdg_bin),
            "FR_CARD_EDITOR_SOURCE": str(self.source),
        })
        result = subprocess.run(
            [str(ROOT / "install.sh")], cwd=ROOT, env=environment,
            check=True, capture_output=True, text=True, timeout=90,
        )
        installed_app = xdg_data / "fr-autoedite"
        destination = installed_app / "local_components" / "fr-card-editor" / "1.1.0"
        self.assert_installed_subset(destination)
        self.assertFalse((installed_app / "FR_CARD_EDITOR_UNIVERSAL_v1.1.0").exists())
        self.assertFalse(any(installed_app.rglob("FR_CARD_EDITOR_STANDALONE.html")))
        self.assertTrue((xdg_bin / "fr-autoedite").is_symlink())
        self.assertIn("Standalone não copiado", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
