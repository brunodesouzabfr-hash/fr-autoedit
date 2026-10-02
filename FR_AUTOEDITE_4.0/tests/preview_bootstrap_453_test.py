from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

import universal_card_runtime as runtime


class PreviewBootstrap453Test(unittest.TestCase):
    def test_preview_without_manifest_accepts_720x1280(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fr-preview-453-") as tmp:
            project = Path(tmp)
            (project / "_CONTROLE").mkdir()
            target = project / "preview.png"
            result = runtime.render_preview_plan_card(
                project,
                {
                    "segment_id": "P0001",
                    "type": "card",
                    "card_kind": "phase",
                    "title": "TESTE UNIVERSAL",
                    "body": "Preview sem manifesto",
                    "duration_sec": 3.0,
                },
                target,
                (720, 1280),
                app_root=Path(__file__).resolve().parents[1],
            )
            self.assertEqual(result["renderer_id"], "fr-universal-card")
            self.assertEqual(result["definition_version"], 2)
            self.assertFalse((project / "MANIFESTO_MEDIA.json").exists())
            with Image.open(target) as image:
                self.assertEqual(image.size, (720, 1280))


if __name__ == "__main__":
    unittest.main()
