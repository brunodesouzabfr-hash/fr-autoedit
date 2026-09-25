#!/usr/bin/env python3
"""Regressões do modo vídeo pronto e do Style Pack V1."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import fr_autoedite as fr
import card_timeline
import local_analysis
import master_contract
import project_scope
import ready_video
import style_engine
from studio import StudioError, StudioState


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReadyVideoFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="fr-ready-video-")
        cls.root = Path(cls.temp.name)
        cls.source = cls.root / "fonte-fora-do-projeto.mp4"
        fr.run([
            "ffmpeg", "-y", "-nostdin", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=c=0x284870:s=320x240:r=24:d=3",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=3",
            "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "96k", "-shortest", "-threads", "1", str(cls.source),
        ])
        cls.source_hash = sha256(cls.source)
        state = StudioState(ROOT, cls.root / "workspace")
        cls.base_project = Path(state.create_project("Vídeo pronto teste")["path"])
        answers = state.load_config(cls.base_project)
        answers["input"].update({
            "mode": "ready_video", "timeline_locked": True,
            "allow_duration_extension": False,
            "style_pack_id": "fr_chiaroscuro_vintage_v1",
        })
        answers["social"].update({"enabled": False, "reels_enabled": False, "stories_enabled": False, "carousel_enabled": False})
        answers["cards"]["generate_previews"] = False
        fr.prepare_ready_video(cls.source, cls.base_project, answers, package=False)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.case_root = Path(tempfile.mkdtemp(prefix="case-", dir=self.root))
        self.project = self.case_root / "project"
        shutil.copytree(self.base_project, self.project)
        self.manifest = fr.read_json(self.project / "MANIFESTO_MEDIA.json")
        self.plan = fr.read_json(self.project / "READY_VIDEO_PLAN.json")
        self.c = SimpleNamespace(**vars(fr))

    def tearDown(self):
        shutil.rmtree(self.case_root)

    def overlay(self, **overrides):
        item = {
            "overlay_id": "OV0001", "kind": "lower_third",
            "start_sec": 0.6, "end_sec": 1.8,
            "text": "Execução controlada", "service_key": "eletrica",
            "asset_id": "", "presentation": "overlay", "position": "bottom_center",
            "safe_area": "title_safe", "opacity": 1.0,
            "animation_in": "fade", "animation_out": "fade",
            "audio_policy": "preserve", "rationale": "Identifica o processo para revisão.",
        }
        item.update(overrides)
        return item

    def test_prepare_generates_locked_contract_proxy_and_references_without_changing_source(self):
        self.assertEqual(sha256(self.source), self.source_hash)
        row = self.manifest["media"][0]
        base = self.project / row["source_path"]
        self.assertEqual(self.manifest["input_mode"], "ready_video")
        self.assertEqual(row["id"], "READY_VIDEO_BASE")
        self.assertEqual(sha256(base), self.source_hash)
        self.assertTrue((self.project / row["proxy_path"]).is_file())
        self.assertTrue((self.project / row["thumbnail_path"]).is_file())
        self.assertGreaterEqual(len(self.manifest["visual_references"]), 3)
        self.assertTrue(all((self.project / item["thumbnail_path"]).is_file() for item in self.manifest["visual_references"]))
        self.assertTrue(self.plan["timeline_locked"])
        locked_timeline = fr.read_json(self.project / "EDIT_PLAN.json")
        self.assertEqual(locked_timeline["segments"][0]["duration_sec"], row["duration_sec"])
        self.assertEqual(locked_timeline["segments"][0]["playback_speed"], 1.0)
        self.assertEqual(len(locked_timeline["segments"]), 1)

    def test_master_markdown_exposes_ready_video_contract_and_imports_valid_overlay(self):
        markdown = self.project / "PACOTE_PARA_IA" / "01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE.md"
        payload = fr.parse_ai_editing_brief(markdown)
        for key in (
            "input_mode", "base_video_id", "timeline_locked", "allow_duration_extension",
            "style_pack_id", "audio_policy", "overlays",
        ):
            self.assertIn(key, payload)
        for key in (
            "overlay_id", "kind", "start_sec", "end_sec", "text", "body", "service_key", "asset_id",
            "presentation", "position", "safe_area", "opacity", "animation_in", "animation_out",
            "audio_policy", "rationale",
        ):
            self.assertIn(key, payload["allowed_values"]["overlay_item_fields"])
        payload["overlays"] = [self.overlay()]
        bundle = master_contract.prepare_bundle(vars(fr), self.project, payload)
        self.assertEqual(bundle["input_mode"], "ready_video")
        self.assertEqual(bundle["overlays"][0]["service_key"], "eletrica")
        rationale_notice = [item for item in bundle["review"]["notices"] if item["block"].endswith("rationale")]
        self.assertTrue(rationale_notice)

    def test_validation_rejects_unknown_kind_bad_time_missing_asset_and_unlocked_timeline(self):
        cases = [
            (self.overlay(kind="zoom_magic"), "tipo desconhecido"),
            (self.overlay(end_sec=99), "use um valor entre"),
            (self.overlay(asset_id="asset_inexistente"), "asset_id desconhecido"),
        ]
        for overlay, message in cases:
            with self.subTest(message=message):
                invalid = copy.deepcopy(self.plan)
                invalid["overlays"] = [overlay]
                with self.assertRaisesRegex(fr.AutoEditeError, message):
                    master_contract.validate_ready_video_contract(self.c, invalid, self.manifest)
        invalid = copy.deepcopy(self.plan)
        invalid["timeline_locked"] = False
        with self.assertRaisesRegex(fr.AutoEditeError, "exige true"):
            master_contract.validate_ready_video_contract(self.c, invalid, self.manifest)

    def test_card_instance_ready_round_trip_legacy_fallback_and_invalid_placement(self):
        legacy = copy.deepcopy(self.plan)
        legacy["overlays"] = [self.overlay(kind="common_card", body="Corpo explícito")]
        validated_legacy, _ = master_contract.validate_ready_video_contract(self.c, legacy, self.manifest)
        self.assertNotIn("card_instance", validated_legacy["overlays"][0])

        versioned = copy.deepcopy(legacy)
        versioned["overlays"][0]["card_instance"] = card_timeline.build_ready_card_instance(
            versioned["overlays"][0]
        )
        validated, _ = master_contract.validate_ready_video_contract(self.c, versioned, self.manifest)
        self.assertEqual(validated["overlays"][0]["card_instance"]["placement"], {
            "timebase": "ready_video_base", "start_sec": 0.6, "end_sec": 1.8,
        })
        self.assertTrue(validated["timeline_locked"])

        invalid = copy.deepcopy(versioned)
        invalid["overlays"][0]["card_instance"]["placement"]["end_sec"] = 2.0
        with self.assertRaisesRegex(fr.AutoEditeError, "janela física"):
            master_contract.validate_ready_video_contract(self.c, invalid, self.manifest)

    def test_master_import_rejects_hidden_cut_or_speed_change(self):
        payload = fr.parse_ai_editing_brief(
            self.project / "PACOTE_PARA_IA" / "01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE.md"
        )
        payload["main_timeline"]["segments"][0]["start_sec"] = 0.2
        payload["main_timeline"]["segments"][0]["duration_sec"] -= 0.2
        payload["main_timeline"]["segments"][0]["playback_speed"] = 1.1
        with self.assertRaisesRegex(fr.AutoEditeError, "vídeo pronto está bloqueado"):
            master_contract.prepare_bundle(vars(fr), self.project, payload)

    def test_ffmpeg_render_preserves_base_hash_duration_audio_and_overlay_window(self):
        self.plan["overlays"] = [self.overlay()]
        project_scope.write(self.project / "READY_VIDEO_PLAN.json", self.plan)
        base = self.project / self.manifest["media"][0]["source_path"]
        before = sha256(base)
        with patch("ready_video.choose_preview_backend", return_value="ffmpeg"):
            record = ready_video.render(vars(fr), self.project, self.plan, preview=False)
        output = self.project / record["output_path"]
        parsed = fr.parse_probe(output, fr.ffprobe(output))
        source_parsed = fr.parse_probe(base, fr.ffprobe(base))
        tolerance = 1 / source_parsed["fps"] + 0.01
        self.assertLessEqual(abs(parsed["duration_sec"] - source_parsed["duration_sec"]), tolerance)
        self.assertEqual((parsed["width"], parsed["height"]), (source_parsed["width"], source_parsed["height"]))
        self.assertAlmostEqual(parsed["fps"], source_parsed["fps"], places=3)
        self.assertTrue(parsed["has_audio"])
        self.assertEqual(sha256(base), before)
        self.assertEqual(sha256(self.source), self.source_hash)

        def audio_timing(path):
            result = fr.run([
                "ffprobe", "-v", "error", "-select_streams", "a:0",
                "-show_entries", "stream=start_time,duration", "-of", "json", str(path),
            ], capture=True)
            stream = json.loads(result.stdout)["streams"][0]
            return float(stream.get("start_time") or 0), float(stream.get("duration") or 0)

        source_audio = audio_timing(base)
        output_audio = audio_timing(output)
        self.assertLessEqual(abs(output_audio[0] - source_audio[0]), tolerance)
        self.assertLessEqual(abs(output_audio[1] - source_audio[1]), tolerance)

        before_frame = self.case_root / "before.png"
        active_frame = self.case_root / "active.png"
        after_frame = self.case_root / "after.png"
        for seek, target in ((0.2, before_frame), (1.1, active_frame), (2.4, after_frame)):
            fr.run(["ffmpeg", "-y", "-nostdin", "-loglevel", "error", "-ss", str(seek), "-i", str(output), "-frames:v", "1", str(target)])
        from PIL import Image, ImageChops, ImageStat
        with Image.open(before_frame) as before, Image.open(active_frame) as active, Image.open(after_frame) as after:
            active_difference = ImageChops.difference(before.convert("RGB"), active.convert("RGB"))
            inactive_difference = ImageChops.difference(before.convert("RGB"), after.convert("RGB"))
            self.assertGreater(sum(ImageStat.Stat(active_difference).mean), 12.0)
            self.assertLess(sum(ImageStat.Stat(inactive_difference).mean), 5.0)

    def test_preview_signature_changes_when_card_style_changes_and_uses_cache_busting_record(self):
        self.plan["overlays"] = [self.overlay(kind="service_card", text="ELÉTRICA", position="bottom_left")]
        with patch("ready_video.choose_preview_backend", return_value="ffmpeg"):
            first = ready_video.render(vars(fr), self.project, self.plan, preview=True)
            style = fr.load_card_style(self.project)
            style["palette"]["orange"] = "#FF7A00" if style["palette"]["orange"].upper() != "#FF7A00" else "#F6A700"
            project_scope.write(self.project / "CARD_STYLE.json", style)
            second = ready_video.render(vars(fr), self.project, self.plan, preview=True)
        self.assertNotEqual(first["signature"], second["signature"])
        registry = project_scope.read(self.project / "_CONTROLE" / "READY_VIDEO_PREVIEW.json")
        self.assertEqual(registry["signature"], second["signature"])
        html = (ROOT / "assets" / "studio" / "index.html").read_text(encoding="utf-8")
        self.assertIn("d.ready_video_preview.signature", html)
        self.assertIn("&v=", html)

    def test_ready_layer_cache_reuses_timing_only_change_and_removes_deleted_card(self):
        overlay = self.overlay(
            kind="common_card", text="CARD CACHE", body="Corpo explícito", position="center",
        )
        overlay["card_instance"] = card_timeline.build_ready_card_instance(overlay)
        self.plan["overlays"] = [overlay]
        with patch("ready_video.choose_preview_backend", return_value="ffmpeg"):
            ready_video.render(vars(fr), self.project, self.plan, preview=True)
        layer = self.project / "_CACHE_RENDER" / "ready_video_overlays" / "OV0001.png"
        self.assertTrue(layer.is_file())

        moved = copy.deepcopy(self.plan)
        moved["overlays"][0].update(start_sec=0.8, end_sec=2.0)
        moved["overlays"][0]["card_instance"] = card_timeline.build_ready_card_instance(moved["overlays"][0])
        with (
            patch("ready_video.choose_preview_backend", return_value="ffmpeg"),
            patch("ready_video._ffmpeg_compose"),
            patch("ready_video.overlay_image", wraps=ready_video.overlay_image) as render_layer,
        ):
            ready_video.render(vars(fr), self.project, moved, preview=True)
        self.assertEqual(render_layer.call_count, 0)

        removed = copy.deepcopy(moved)
        removed["overlays"] = []
        with (
            patch("ready_video.choose_preview_backend", return_value="ffmpeg"),
            patch("ready_video._ffmpeg_compose"),
        ):
            ready_video.render(vars(fr), self.project, removed, preview=True)
        self.assertFalse(layer.exists())
        cache = project_scope.read(
            self.project / "_CACHE_RENDER" / "ready_video_overlays" / "LAYER_CACHE.json"
        )
        self.assertEqual(cache["layers"], {})

    def test_saving_unchanged_overlay_plan_does_not_stack_hidden_history(self):
        state = StudioState(ROOT, self.root / "workspace")
        state.save_ready_video_plan(self.project, self.plan)
        after_first = len(list((self.project / "_HISTORICO").glob("READY_VIDEO_PLAN_*.json")))
        normalized = fr.read_json(self.project / "READY_VIDEO_PLAN.json")
        state.save_ready_video_plan(self.project, normalized)
        after_second = len(list((self.project / "_HISTORICO").glob("READY_VIDEO_PLAN_*.json")))
        self.assertEqual(after_second, after_first)

    def test_card_editor_ready_round_trip_preview_and_original_preservation(self):
        state = StudioState(ROOT, self.root / "workspace-card-editor")
        self.plan["overlays"] = [self.overlay(
            kind="common_card", text="CARD READY", body="Corpo original explícito",
            service_key="", asset_id="", position="center",
        )]
        project_scope.write(self.project / "READY_VIDEO_PLAN.json", self.plan)
        before_plan = copy.deepcopy(self.plan)
        base = self.project / self.manifest["media"][0]["source_path"]
        base_hash = sha256(base)
        with patch("ready_video.choose_preview_backend", return_value="ffmpeg"):
            initial_preview = ready_video.render(vars(fr), self.project, self.plan, preview=True)

        exported = state.card_content(self.project, "OV0001", "ready_video")
        payload = {
            "adapter_version": exported["adapter_version"],
            "base_revision": exported["base_revision"],
            "segment_id": exported["segment_id"],
            "fields": {"title": "CARD READY REVISADO", "body": "Corpo revisado explícito"},
        }
        saved = state.save_card_content(self.project, payload, "ready_video")
        persisted = fr.read_json(self.project / "READY_VIDEO_PLAN.json")

        self.assertEqual(saved["fields"], payload["fields"])
        self.assertTrue(persisted["timeline_locked"])
        self.assertEqual(persisted["base_video_id"], "READY_VIDEO_BASE")
        self.assertEqual(persisted["overlays"][0]["overlay_id"], "OV0001")
        self.assertEqual(persisted["overlays"][0]["text"], "CARD READY REVISADO")
        self.assertEqual(persisted["overlays"][0]["body"], "Corpo revisado explícito")
        for key, value in before_plan.items():
            if key != "overlays":
                self.assertEqual(persisted[key], value, key)
        expected_overlay = copy.deepcopy(before_plan["overlays"][0])
        actual_overlay = copy.deepcopy(persisted["overlays"][0])
        for item in (expected_overlay, actual_overlay):
            item.pop("text")
            item.pop("body")
        self.assertEqual(actual_overlay, expected_overlay)

        with self.assertRaisesRegex(StudioError, "timeline mudou"):
            state.save_card_content(self.project, payload, "ready_video")
        with self.assertRaisesRegex(StudioError, "outro contrato visual"):
            unsupported = copy.deepcopy(persisted)
            unsupported["overlays"].append(self.overlay(overlay_id="OV0002"))
            project_scope.write(self.project / "READY_VIDEO_PLAN.json", unsupported)
            state.card_content(self.project, "OV0002", "ready_video")
        project_scope.write(self.project / "READY_VIDEO_PLAN.json", persisted)

        with patch("ready_video.choose_preview_backend", return_value="ffmpeg"):
            record = ready_video.render(vars(fr), self.project, persisted, preview=True)
        self.assertTrue((self.project / record["output_path"]).is_file())
        self.assertTrue(record["signature"])
        self.assertNotEqual(record["signature"], initial_preview["signature"])
        self.assertEqual(sha256(base), base_hash)
        self.assertEqual(sha256(self.source), self.source_hash)

    def test_duration_extension_is_blocked_until_explicitly_allowed(self):
        config = fr.read_json(self.project / "QUESTIONARIO_RESPONDIDO.json")
        config["external_intro_outro"].update({
            "intro_enabled": True, "intro_path": str(self.source), "intro_duration_sec": 1.0,
        })
        project_scope.write(self.project / "QUESTIONARIO_RESPONDIDO.json", config)
        with self.assertRaisesRegex(fr.AutoEditeError, "allow_duration_extension"):
            ready_video.render(vars(fr), self.project, self.plan, preview=False)

    def test_duration_extension_runs_only_after_explicit_permission(self):
        config = fr.read_json(self.project / "QUESTIONARIO_RESPONDIDO.json")
        config["external_intro_outro"].update({
            "intro_enabled": True, "intro_path": str(self.source), "intro_duration_sec": 0.5,
            "intro_preserve_audio": True,
        })
        project_scope.write(self.project / "QUESTIONARIO_RESPONDIDO.json", config)
        allowed = copy.deepcopy(self.plan)
        allowed["allow_duration_extension"] = True
        record = ready_video.render(vars(fr), self.project, allowed, preview=False)
        output = self.project / record["output_path"]
        parsed = fr.parse_probe(output, fr.ffprobe(output))
        fps = float(self.manifest["media"][0]["fps"])
        self.assertLessEqual(abs(parsed["duration_sec"] - 3.5), 1 / fps + 0.01)
        self.assertTrue(parsed["has_audio"])
        self.assertEqual(sha256(self.source), self.source_hash)


class StylePackAndCapabilities(unittest.TestCase):
    def test_style_pack_has_exact_services_slots_and_directories(self):
        manifest = style_engine.load_style_pack(ROOT, "fr_chiaroscuro_vintage_v1")
        expected = {
            "projetos_3d", "pintura", "textura", "revestimentos", "moveis", "alvenaria",
            "producoes", "criacoes", "iluminacao", "eletrica", "hidraulica", "instalacao", "manutencao",
        }
        self.assertTrue(expected.issubset(manifest["services"]))
        for service in expected:
            definition = manifest["services"][service]
            self.assertTrue(definition.get("motif"), service)
            self.assertIn(definition.get("asset_id"), manifest["assets"])
        self.assertIn("background_chiaroscuro_vertical", manifest["assets"])
        self.assertIn("background_chiaroscuro_horizontal", manifest["assets"])
        root = ROOT / "assets" / "style_packs" / "fr_chiaroscuro_vintage_v1"
        for folder in (
            "cards_common", "cards_service", "balloons", "frames", "textures",
            "background_motifs", "logo", "typography",
        ):
            self.assertTrue((root / folder).is_dir(), folder)
        index = style_engine.asset_index(ROOT, "fr_chiaroscuro_vintage_v1")
        self.assertTrue(index["ready"])
        self.assertTrue(index["missing_optional"])

    def test_style_pack_signature_tracks_asset_bytes_and_mtime(self):
        with tempfile.TemporaryDirectory(prefix="fr-style-signature-") as temp:
            app = Path(temp)
            pack = app / "assets" / "style_packs" / "test_pack"
            (pack / "cards").mkdir(parents=True)
            (pack / "manifest.json").write_text(json.dumps({
                "schema_version": 1, "style_pack_id": "test_pack",
                "assets": {"card": {"path": "cards/card.png", "required": True}},
            }), encoding="utf-8")
            asset = pack / "cards" / "card.png"
            asset.write_bytes(b"primeira-versao")
            first = style_engine.style_pack_signature(app, "test_pack")
            asset.write_bytes(b"segunda-versao")
            second = style_engine.style_pack_signature(app, "test_pack")
            self.assertNotEqual(first, second)

    def test_moviepy_absence_uses_ffmpeg_fallback_without_importing_it(self):
        with patch("local_analysis.importlib.util.find_spec", return_value=None), patch(
            "local_analysis.shutil.which", return_value="/usr/bin/ffmpeg"
        ):
            self.assertEqual(local_analysis.choose_preview_backend(True), "ffmpeg")
            capabilities = local_analysis.compositor_capabilities()
        self.assertFalse(capabilities["moviepy"])
        self.assertEqual(capabilities["final_render_backend"], "ffmpeg")

    def test_raw_media_remains_default_and_studio_exposes_both_modes(self):
        answers = fr.normalize_answers({})
        self.assertEqual(answers["input"]["mode"], "raw_media")
        html = (ROOT / "assets" / "studio" / "index.html").read_text(encoding="utf-8")
        self.assertIn('value="raw_media"', html)
        self.assertIn('value="ready_video"', html)
        self.assertIn("readyOverlayList", html)
        self.assertIn("style-reindex", html)
        self.assertIn('id="rawMontageControls"', html)
        self.assertIn('id="readyMontageControls"', html)
        self.assertIn("Revise o vídeo-base e suas camadas", html)
        self.assertIn('.overlay-row{grid-template-columns:repeat(2,minmax(0,1fr))}', html)


if __name__ == "__main__":
    unittest.main()
