#!/usr/bin/env python3
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from fr_v4.editorial.audio import plan
from fr_v4.editorial.captions import to_srt
from fr_v4.editorial.chapters import validate
from fr_v4.editorial.presets import preset
from fr_v4.editorial.search import search
from fr_v4.editorial.versioning import content_id, next_version
from fr_v4.editorial.workflow import transition


class EditorialTest(unittest.TestCase):
    def test_caption_is_clean_and_timestamped(self):
        result = to_srt([{"start_sec": 0.2, "end_sec": 1.5, "text": "Execução controlada"}])
        self.assertIn("00:00:00,200 --> 00:00:01,500", result)
        self.assertNotIn("comentário", result.casefold())

    def test_presets_are_copies(self):
        first = preset("instagram_reels"); first["aspect"] = "x"
        self.assertEqual(preset("instagram_reels")["aspect"], "9:16")

    def test_chapters_audio_search_version_and_workflow(self):
        self.assertEqual(len(validate([{"id":"a","titulo":"A","start_sec":0,"end_sec":2}], 2)), 1)
        self.assertTrue(plan(normalize_lufs=-14)["preserve_original"])
        self.assertEqual(search([{"id":"1","name":"Projeto elétrico"}], "elétrico")[0]["id"], "1")
        self.assertEqual(content_id({"b": 1, "a": 2}), content_id({"a": 2, "b": 1}))
        self.assertEqual(next_version(["filme-v001"], "filme"), "filme-v002")
        self.assertEqual(transition("draft", "validated"), "validated")
        with self.assertRaises(ValueError): transition("draft", "published")


if __name__ == "__main__": unittest.main()

