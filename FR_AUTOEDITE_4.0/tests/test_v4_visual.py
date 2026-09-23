#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from fr_v4.core.card_renderer import CardSpec, compose
from fr_v4.core.config import SERVICES
from fr_v4.diagrams import render as diagram
from fr_v4.overlays import render_overlay


class VisualTest(unittest.TestCase):
    def test_diagrams_are_distinct(self):
        hashes = set()
        for service in SERVICES:
            image = diagram(service.key, (540, 540), .18)
            hashes.add(hashlib.sha256(image.tobytes()).hexdigest()); image.close()
        self.assertEqual(len(hashes), 13)

    def test_every_service_composes_in_both_formats(self):
        for service in SERVICES:
            for size in ((1080, 1920), (1080, 1080)):
                with self.subTest(service=service.key, size=size):
                    result = compose(CardSpec("F3", service.label, "Técnica aplicada com precisão.",
                                              service_key=service.key), size, ROOT)
                    image = result.flatten()
                    self.assertEqual(image.size, size)
                    self.assertFalse(result.pending_assets)
                    image.close()
                    for layer in result.layers.values(): layer.close()

    def test_small_overlay_is_measured(self):
        overlay = render_overlay({"kind":"lower_third", "text":"Execução controlada",
                                  "service_key":"eletrica"}, (320, 240), ROOT)
        self.assertGreater(overlay.getbbox()[2], 0); overlay.close()


if __name__ == "__main__": unittest.main()

