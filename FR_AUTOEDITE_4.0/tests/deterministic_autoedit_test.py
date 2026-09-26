#!/usr/bin/env python3
"""M8: AutoEdit determinístico, offline, validado e reversível."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import deterministic_autoedit as deterministic  # noqa: E402
import fr_autoedite as fr  # noqa: E402
import project_scope as scope  # noqa: E402
import proxy_integrity  # noqa: E402


class DeterministicAutoEditTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="fr-autoedit-m8-")
        self.project = Path(self.temporary.name) / "projeto"
        originals = self.project / "originais"
        proxies = self.project / "proxies"
        originals.mkdir(parents=True)
        proxies.mkdir(parents=True)
        rows = []
        for index, color in enumerate(("#d84b30", "#2868b2"), 1):
            source = originals / f"fase-{index}.png"
            proxy = proxies / f"fase-{index}.png"
            Image.new("RGB", (320, 568), color).save(source)
            Image.new("RGB", (160, 284), color).save(proxy)
            rows.append({
                "id": f"M{index:04d}", "status": "ok", "media_type": "image",
                "source_path": source.relative_to(self.project).as_posix(),
                "proxy_path": proxy.relative_to(self.project).as_posix(),
                "thumbnail_path": proxy.relative_to(self.project).as_posix(),
                "width": 320, "height": 568, "quality_score": 70 + index,
                "chronological_index": index, "alphabetical_index": index,
                "has_audio": False,
            })
        self.manifest = {"schema_version": 3, "input_mode": "raw_media", "media": rows}
        answers = fr.normalize_answers(fr.read_json(ROOT / "templates" / "questionario_base.json"))
        answers["project"].update(name="Fixture M8", slug="fixture-m8")
        answers["context"].update(
            summary="Registro sintético sem classificação de serviço.",
            facts_confirmed=[], facts_to_confirm=[], cta="Revisar o rascunho.",
        )
        answers["story"]["chronology"] = [{
            "order": 1, "title": "FASE SINTÉTICA",
            "description": "Duas imagens geradas pelo teste.", "keywords": ["fase"],
        }]
        answers["edition"].update({
            "order_mode": "automatico", "format": "vertical", "width": 320,
            "height": 568, "quality_preset": "custom", "fps": 24,
            "target_duration_sec": 5, "average_clip_duration_sec": 1,
            "still_duration_sec": 0.4, "phase_card_duration_sec": 0.3,
            "max_media_segments": 2, "create_clean_version": False,
            "preserve_original_audio": False, "render_source": "originals",
        })
        answers["visual_effects"].update({
            "transitions": ["cut"], "transition_duration_sec": 0,
            "speed_ramping": False, "enable_stabilization": False, "color_lut": "",
        })
        answers["audio_design"].update(enable_sfx=False, tts_voiceover=False)
        answers["export_quality"].update(video_crf=30, parallel_workers=1)
        answers["social"].update(
            enabled=False, reels_enabled=False, carousel_enabled=False, stories_enabled=False,
        )
        answers["service_intro"]["enabled"] = False
        self.answers = fr.normalize_answers(answers)
        scope.write(self.project / "QUESTIONARIO_RESPONDIDO.json", self.answers)
        scope.write(self.project / "MANIFESTO_MEDIA.json", self.manifest)
        scope.write(self.project / "EDIT_PLAN.json", {"sentinel": "manual-before-m8"})

    def tearDown(self):
        self.temporary.cleanup()

    def original_hashes(self):
        return {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((self.project / "originais").iterdir())
        }

    def test_fixed_seed_reuses_baseline_and_is_offline_and_stable(self):
        before_plan = (self.project / "EDIT_PLAN.json").read_bytes()
        before_originals = self.original_hashes()
        real_socket = socket.socket

        def block_network(*args, **kwargs):
            family = args[0] if args else kwargs.get("family", socket.AF_INET)
            if family in {socket.AF_INET, socket.AF_INET6}:
                raise AssertionError("M8 tentou abrir rede")
            return real_socket(*args, **kwargs)

        with patch("socket.socket", side_effect=block_network):
            first, report = deterministic.generate_plan(vars(fr), self.project, mode="aleatorio", seed=731)
            second, _ = deterministic.generate_plan(vars(fr), self.project, mode="aleatorio", seed=731)
        self.assertEqual(deterministic.normalized_plan(first), deterministic.normalized_plan(second))
        self.assertEqual(report["seed"], 731)
        self.assertEqual(report["status"], "proposal_validated")
        self.assertTrue(report["requires_explicit_apply"])
        self.assertEqual(before_plan, (self.project / "EDIT_PLAN.json").read_bytes())
        self.assertEqual(before_originals, self.original_hashes())

        verified = proxy_integrity.ensure_manifest_integrity(
            self.project, self.manifest,
            parameters_for=lambda row: fr.proxy_generation_parameters(row, self.answers),
            probe=fr.proxy_probe_metadata, decode_video=fr.decode_video_proxy,
        )
        baseline_answers = copy.deepcopy(self.answers)
        baseline_answers["edition"]["order_mode"] = "aleatorio"
        baseline = fr.build_auto_plan(
            self.project, baseline_answers, verified, publish=False, seed_override=731,
        )
        fields = ("type", "media_id", "start_sec", "duration_sec", "transition", "card_kind")
        baseline_signature = [tuple(row.get(key) for key in fields) for row in baseline["segments"]]
        m8_signature = [tuple(row.get(key) for key in fields) for row in first["segments"]]
        self.assertEqual(baseline_signature, m8_signature)
        self.assertEqual(first["automation"]["origin"], "deterministic_auto")
        self.assertEqual(first["automation"]["engine_version"], deterministic.ENGINE_VERSION)
        self.assertEqual(first["output"]["render_source"], "originals")
        self.assertTrue(all(row.get("decision_reason") for row in first["segments"]))
        cards = [row for row in first["segments"] if row["type"] == "card"]
        self.assertTrue(all(row["card_instance"]["edit_origin"] == "deterministic_auto" for row in cards))
        self.assertFalse(any(row.get("card_kind") == "service" for row in cards))
        self.assertFalse(any("balloon" in row for row in first["segments"]))
        validated = fr.validate_imported_plan(copy.deepcopy(first), verified, "filme principal")
        self.assertEqual(len(validated["segments"]), len(first["segments"]))

    def test_derived_seed_apply_snapshot_and_rollback(self):
        old_plan = (self.project / "EDIT_PLAN.json").read_bytes()
        before_originals = self.original_hashes()
        first, _ = deterministic.generate_plan(vars(fr), self.project, mode="aleatorio")
        second, _ = deterministic.generate_plan(vars(fr), self.project, mode="aleatorio")
        self.assertEqual(first["automation"]["seed"], second["automation"]["seed"])
        self.assertEqual(deterministic.normalized_plan(first), deterministic.normalized_plan(second))

        result = deterministic.apply_plan(vars(fr), self.project, mode="automatico")
        self.assertEqual(result["status"], "applied")
        self.assertEqual(fr.read_json(self.project / "EDIT_PLAN.json")["automation"]["origin"], "deterministic_auto")
        self.assertEqual(
            fr.read_json(self.project / "EDIT_PLAN.json"),
            fr.read_json(self.project / "EDIT_PLAN_AUTO.json"),
        )
        rollback = result["rollback_version"]
        self.assertTrue((self.project / "_ROTEIROS" / rollback / "VERSION.json").is_file())
        scope.restore_version(self.project, rollback)
        self.assertEqual(old_plan, (self.project / "EDIT_PLAN.json").read_bytes())
        self.assertFalse((self.project / "EDIT_PLAN_AUTO.json").exists())
        self.assertFalse((self.project / deterministic.CONTROL_PATH).exists())
        self.assertEqual(before_originals, self.original_hashes())

    def test_ready_video_and_corrupt_proxy_are_blocked_before_writes(self):
        config = copy.deepcopy(self.answers)
        config["input"].update(mode="ready_video", timeline_locked=True, base_video_id="READY_VIDEO_BASE")
        scope.write(self.project / "QUESTIONARIO_RESPONDIDO.json", config)
        scope.write(self.project / "READY_VIDEO_PLAN.json", {
            "input_mode": "ready_video", "base_video_id": "READY_VIDEO_BASE",
            "timeline_locked": True, "overlays": [],
        })
        before_plan = (self.project / "EDIT_PLAN.json").read_bytes()
        before_ready = (self.project / "READY_VIDEO_PLAN.json").read_bytes()
        with self.assertRaisesRegex(deterministic.DeterministicAutoEditError, "ready_video"):
            deterministic.apply_plan(vars(fr), self.project)
        self.assertEqual(before_plan, (self.project / "EDIT_PLAN.json").read_bytes())
        self.assertEqual(before_ready, (self.project / "READY_VIDEO_PLAN.json").read_bytes())

        config["input"].update(mode="raw_media", timeline_locked=False, base_video_id="")
        scope.write(self.project / "QUESTIONARIO_RESPONDIDO.json", config)
        (self.project / self.manifest["media"][0]["proxy_path"]).write_bytes(b"proxy-corrompido")
        with self.assertRaisesRegex(proxy_integrity.ProxyIntegrityError, "imagem ilegível"):
            deterministic.generate_plan(vars(fr), self.project)
        self.assertEqual(before_plan, (self.project / "EDIT_PLAN.json").read_bytes())

    def test_limited_draft_renders_from_verified_proxies_and_ffprobe_passes(self):
        original_manifest = copy.deepcopy(self.manifest)
        original_manifest["media"] = original_manifest["media"][:1]
        scope.write(self.project / "MANIFESTO_MEDIA.json", original_manifest)
        before_originals = self.original_hashes()
        result = deterministic.apply_plan(vars(fr), self.project, mode="automatico")
        plan = result["plan"]
        self.assertEqual(plan["review_status"], "DETERMINISTIC_LIMITED_DRAFT_REQUIRES_VISUAL_REVIEW")
        self.assertTrue(any("Material limitado" in item for item in plan["automation"]["limitations"]))
        outputs = fr.render_draft(self.project, only="branded")
        self.assertEqual(len(outputs), 1)
        metadata = fr.parse_probe(outputs[0], fr.ffprobe(outputs[0]))
        self.assertGreater(metadata["duration_sec"], 0)
        self.assertEqual(metadata["video_codec"], "h264")
        self.assertEqual((metadata["width"], metadata["height"]), (480, 854))
        render_workspace = outputs[0].parent.parent
        draft_plan = fr.read_json(render_workspace / "EDIT_PLAN_DRAFT.json")
        self.assertEqual(draft_plan["output"]["render_source"], "proxies")
        self.assertEqual(fr.read_json(self.project / "EDIT_PLAN.json")["output"]["render_source"], "originals")
        self.assertEqual(before_originals, self.original_hashes())


if __name__ == "__main__":
    unittest.main(verbosity=2)
