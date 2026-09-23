#!/usr/bin/env python3
"""Regressões do pacote canônico da Fase 2."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import fr_autoedite as fr  # noqa: E402
import project_scope as scope  # noqa: E402
from studio import StudioState  # noqa: E402


class Phase2AiPackage(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="fr-phase2-package-")
        root = Path(self.temporary.name)
        self.state = StudioState(ROOT, root / "Studio")
        self.project = Path(self.state.create_project("Pacote Fase Dois")["path"])
        source = self.project / "originais" / "imagem.png"
        proxy = self.project / "proxies" / "M0001_imagem_PROXY.png"
        source.parent.mkdir(parents=True, exist_ok=True)
        proxy.parent.mkdir(parents=True, exist_ok=True)
        image = (ROOT / "assets" / "services" / "pintura.png").read_bytes()
        source.write_bytes(image);proxy.write_bytes(image)
        self.manifest = {"schema_version":3,"summary":{"total":1},"media":[{
            "id":"M0001","status":"ok","media_type":"image","filename":"imagem.png",
            "source_path":"originais/imagem.png","proxy_path":"proxies/M0001_imagem_PROXY.png",
            "thumbnail_path":"proxies/M0001_imagem_PROXY.png","duration_sec":0,"width":512,"height":512,"has_audio":False,
        }]}
        scope.write(self.project / "MANIFESTO_MEDIA.json", self.manifest)
        config = self.state.load_config(self.project)
        config["social"].update(enabled=False,reels_enabled=False,carousel_enabled=False,stories_enabled=False)
        config["cards"]["generate_previews"] = False
        scope.write(self.project / "QUESTIONARIO_RESPONDIDO.json", config)
        scope.write(self.project / "EDIT_PLAN.json", {"segments":[{
            "segment_id":"S0001","type":"media","media_id":"M0001","media_type":"image",
            "start_sec":0,"duration_sec":3,"transition":"cut","include_in":["branded","clean"],"enabled":True,
        }]})
        (self.project / "_ENTRADA" / "CONTEXTO_PROJETO.md").write_text(
            "Mostrar projeto 3D, execução elétrica e entrega final.", encoding="utf-8",
        )

    def tearDown(self):
        self.temporary.cleanup()

    def test_complete_package_and_contract(self):
        config = fr.read_json(self.project / "QUESTIONARIO_RESPONDIDO.json")
        outputs = fr.create_chatgpt_package(self.project, config)
        package = self.project / "PACOTE_PARA_IA"
        required = (
            "00_NAO_EDITAR_CONTEXTO_PROJETO.md",
            "01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE.md",
            "02_NAO_EDITAR_MANIFESTO_MEDIA.json",
            "03_NAO_EDITAR_LOTES_DE_PROXIES",
            "04_NAO_EDITAR_INSTRUCOES_PARA_IA.md",
            "05_RESPOSTA_DA_IA_IMPORTAR_AQUI.md",
        )
        self.assertTrue(all((package / name).exists() for name in required))
        self.assertTrue(outputs)
        self.assertTrue(all(path.stat().st_size < 150 * 1024 * 1024 for path in outputs))
        self.assertTrue(all(zipfile.ZipFile(path).testzip() is None for path in outputs))
        markdown = (package / required[1]).read_text(encoding="utf-8")
        payload = fr.parse_ai_editing_brief(package / required[1])
        for expected in ("start_sec","duration_sec","end_sec","playback_speed","keyframes",
                         "narration","subtitles","card_mode","service_key","stories","reels",
                         "service_id","service_name","service_confidence","service_card_enabled",
                         "card_type","card_family","balloon_family","visual_motif","overlay_text",
                         "voiceover_text","caption_text","transition_in","transition_out"):
            self.assertIn(expected, markdown)
        strategy = payload["strategy"]
        self.assertEqual(
            set(strategy) & {"editorial","retention","ethical_marketing_growth",
                             "ethical_neuromarketing","brand_franco_romeu","final_copy"},
            {"editorial","retention","ethical_marketing_growth",
             "ethical_neuromarketing","brand_franco_romeu","final_copy"},
        )
        self.assertEqual(
            set(strategy["editorial"]["narrative_arc"]),
            {"hook","development","proof_process","climax","cta"},
        )
        for field in ("hook_0_3_sec","first_strong_image","visual_promise","implicit_question",
                      "pattern_breaks","partial_reveals","best_moments","acceleration_timelapse",
                      "selective_slow_motion","fade_to_black","chapter_transitions","visual_climax","final_cta"):
            self.assertIn(field, strategy["retention"])
        self.assertGreaterEqual(len(payload["allowed_values"]["service_profiles"]),13)
        self.assertTrue({"pintura","textura","eletrica","hidraulica","projetos_3d",
                         "revestimentos","iluminacao","moveis","alvenaria","producoes",
                         "instalacao","manutencao"}.issubset(payload["allowed_values"]["service_profiles"]))
        for profile in payload["allowed_values"]["service_profiles"].values():
            self.assertTrue(profile["visual_family"])
            self.assertTrue(profile["balloon_family"])
            self.assertTrue(profile["visual_motif"])
        instruction = (package / required[4]).read_text(encoding="utf-8").casefold()
        self.assertIn("somente o markdown",instruction)
        self.assertIn("neuromarketing",instruction)
        for forbidden in ("não invente métricas", "prova social", "urgência", "escassez",
                          "preço", "desconto", "cliente", "depoimento", "resultado"):
            self.assertIn(forbidden, instruction)
        self.assertIn("[dado a confirmar]", instruction)
        registry = fr.read_json(self.project / "_CONTROLE" / "PACOTE_IA.json")
        self.assertTrue(registry["all_below_150_mb"])

    def test_replace_does_not_create_history_and_cancel_preserves_current(self):
        config = fr.read_json(self.project / "QUESTIONARIO_RESPONDIDO.json")
        first = fr.create_chatgpt_package(self.project, config, conflict_policy="replace")
        fingerprints = [(path.name, path.stat().st_size, fr._file_digest(path)) for path in first]
        second = fr.create_chatgpt_package(self.project, config, conflict_policy="replace")
        self.assertEqual(fingerprints,[(path.name,path.stat().st_size,fr._file_digest(path)) for path in second])
        history = self.project / "_HISTORICO"
        self.assertFalse(any(history.glob("pacote-chatgpt_*")))
        with self.assertRaises(fr.AutoEditeError):
            fr.create_chatgpt_package(self.project, config, conflict_policy="cancel")
        current = sorted((self.project / "PACOTE_PARA_IA" / "03_NAO_EDITAR_LOTES_DE_PROXIES").glob("*.zip"))
        self.assertEqual(fingerprints,[(path.name,path.stat().st_size,fr._file_digest(path)) for path in current])

    def test_history_policy_preserves_previous_lots(self):
        config = fr.read_json(self.project / "QUESTIONARIO_RESPONDIDO.json")
        first = fr.create_chatgpt_package(self.project, config, conflict_policy="replace")
        old_hashes = {fr._file_digest(path) for path in first}
        proxy = self.project / "proxies" / "M0001_imagem_PROXY.png"
        proxy.write_bytes(proxy.read_bytes() + b"phase-2.1")
        current = fr.create_chatgpt_package(self.project, config, conflict_policy="history")
        self.assertNotEqual(old_hashes, {fr._file_digest(path) for path in current})
        history = self.project / "_HISTORICO"
        archived = list(history.rglob("FR_AUTOEDITE_LOTE_*.zip"))
        self.assertTrue(archived)
        self.assertTrue(old_hashes & {fr._file_digest(path) for path in archived})


if __name__ == "__main__":
    unittest.main(verbosity=2)
