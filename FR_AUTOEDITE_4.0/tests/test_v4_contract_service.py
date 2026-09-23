#!/usr/bin/env python3
from pathlib import Path
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from fr_v4.contracts.generator import generate
from fr_v4.contracts.markdown import parse
from fr_v4.contracts.service import inspect, publish
from fr_v4.models.roteiro_mestre import validate as validate_pydantic


class ContractServiceTest(unittest.TestCase):
    def setUp(self):
        self.manifest = {"schema_version": 1, "media": []}
        self.content, self.header = generate(manifest=self.manifest, project_id="teste", duration=4)
        self.schema = json.loads((ROOT / "schemas/roteiro_mestre_v4.schema.json").read_text(encoding="utf-8"))

    def test_round_trip_and_validation(self):
        document = parse(self.content)
        self.assertEqual(document.payload["allowed_values"]["audio_policies"], ["preserve", "mix"])
        self.assertEqual(validate_pydantic(document.payload)["project_id"], "teste")
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "roteiro.md"; source.write_text(self.content, encoding="utf-8")
            result = inspect(source, expected_header=self.header, manifest=self.manifest,
                             schema=self.schema, app_root=ROOT)
            self.assertTrue(result["review"]["valid"])

    def test_publish_is_transactional(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / "roteiro.md"; source.write_text(self.content, encoding="utf-8")
            result = publish(source, root / "projeto", expected_header=self.header,
                             manifest=self.manifest, schema=self.schema, app_root=ROOT)
            self.assertTrue(result["applied"])
            self.assertTrue(Path(result["payload"]).is_file())


if __name__ == "__main__": unittest.main()
