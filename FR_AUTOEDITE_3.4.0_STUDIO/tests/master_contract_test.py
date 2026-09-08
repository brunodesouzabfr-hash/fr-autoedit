#!/usr/bin/env python3
"""Behavioural regression tests for the Markdown/Studio/render contract."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
import fr_autoedite as fr
import master_contract as contract
import project_scope as scope
from media_frames import extract_reference
from studio import StudioState


class MasterContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.TemporaryDirectory(prefix="fr-contract-")
        cls.work = Path(cls.root.name)
        cls.source = cls.work / "colors.mp4"
        fr.run(["ffmpeg","-y","-loglevel","error","-f","lavfi","-i","color=red:s=320x240:r=24:d=2",
                "-f","lavfi","-i","color=green:s=320x240:r=24:d=2","-f","lavfi","-i","color=blue:s=320x240:r=24:d=2",
                "-filter_complex","[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]","-map","[v]","-c:v","libx264",
                "-threads","1","-pix_fmt","yuv420p",str(cls.source)])

    @classmethod
    def tearDownClass(cls):
        cls.root.cleanup()

    def setUp(self):
        self.state=StudioState(ROOT,self.work/self.id().rsplit(".",1)[-1])
        self.project=Path(self.state.create_project("Teste do contrato")["path"])
        p=self.project
        (p/"originais").mkdir(exist_ok=True)
        (p/"originais/colors.mp4").write_bytes(self.source.read_bytes())
        self.manifest={"media":[{"id":"M0001","status":"ok","media_type":"video","duration_sec":6,
            "source_path":"originais/colors.mp4","proxy_path":"originais/colors.mp4","has_audio":False,"width":320,"height":240,"fps":24},
            {"id":"M0001C001","status":"ok","media_type":"video","parent_video":"M0001","scene_start_sec":1.0,"scene_end_sec":5.0,"duration_sec":4,
             "source_path":"originais/colors.mp4","proxy_path":"originais/colors.mp4","has_audio":False,"width":320,"height":240}]}
        scope.write(p/"MANIFESTO_MEDIA.json",self.manifest)
        cfg=self.state.load_config(p)
        cfg["edition"].update(width=320,height=568,format="vertical",quality_preset="custom",fps=24,create_clean_version=False)
        cfg["visual_effects"].update(transition_duration_sec=.25,speed_ramping=False)
        cfg["audio_design"].update(enable_sfx=False,tts_voiceover=False)
        cfg["export_quality"].update(video_crf=26,parallel_workers=1)
        cfg["social"].update(enabled=False,reels_enabled=False,carousel_enabled=False,stories_enabled=False)
        scope.write(p/"QUESTIONARIO_RESPONDIDO.json",cfg)
        style=fr.load_card_style()
        style["logo"].update(persistent_on_branded_video=False,persistent_on_cards=True)
        style["persistent_overlay"]["enabled"]=False
        style["cards"].update(always_generate_4k_masters=False,show_contacts_on_every_card=False)
        self.base={"schema_version":2,"roteiro":{"id":"teste-a","name":"Teste A","revision":1,**scope.identity(p,self.manifest)},
            "configuration":cfg,"card_style":style,"main_timeline":{"segments":[self.media("S01",0,1),
                {"segment_id":"S02","type":"card","card_kind":"service","service_key":"pintura","title":"PINTURA","body":"Preparo e acabamento.","duration_sec":1,"transition":"cut","card_animation":"none","include_in":["branded"],"visual":{"media_id":"M0001","time_sec":2.5}},
                {**self.media("S03",4,2),"freeze_frame":{"time_sec":4.5}},self.media("S04",4,1)]},
            "reels":{},"carousel":{"enabled":False,"slides":[]},"stories":{"enabled":False},
            "publication":{"video_title":"Teste de software","caption":"Mídia sintética para validação.","hashtags":[],
                "overlay_typography":{"title_font":"StardosStencil-Bold.ttf","body_font":"Rokkitt-Regular.ttf","technical_font":"ShareTechMono-Regular.ttf"}},
            "strategy":{"hook":"Teste","facts_to_confirm":[]},"executive_summary":["Reutilizar a fonte sem duplicar seus bytes."]}
        scope.write(p/"EDIT_PLAN.json",self.base["main_timeline"])

    def media(self,sid,start,duration):
        return {"segment_id":sid,"type":"media","media_id":"M0001","start_sec":start,"duration_sec":duration,
                "start_time_basis":"absolute_parent_media","transition":"cut","include_in":["branded","clean"],"enabled":True}

    def markdown(self,data=None,name="answer.md"):
        data=data or self.base
        path=self.project/name
        path.write_text("# ROTEIRO MESTRE EDITADO E DEVOLVIDO\n<!-- ROTEIRO: "+data["roteiro"]["id"]+" -->\n"+fr.AI_BRIEF_JSON_BEGIN+"\n```json\n"+json.dumps(data,ensure_ascii=False)+"\n```\n"+fr.AI_BRIEF_JSON_END+"\n",encoding="utf-8")
        return path

    def bundle(self,data=None):
        return contract.prepare_bundle(vars(fr),self.project,data or self.base)

    def test_repeated_source_and_exact_counts(self):
        b=self.bundle();counts=b["review"]["totals"]["filme"]
        self.assertEqual((counts["cards"],counts["cuts"],counts["freeze_frames"],counts["duration_sec"]),(1,3,1,5))
        self.assertEqual([x.get("media_id") for x in b["main_timeline"]["segments"]], ["M0001",None,"M0001","M0001"])

    def test_explicit_scene_clock_and_slow_motion(self):
        d=copy.deepcopy(self.base);s=self.media("A",1.2,2);s.update(media_id="M0001C001",start_time_basis="scene_local",playback_speed=.5)
        d["main_timeline"]["segments"]=[s]
        out=self.bundle(d)["main_timeline"]["segments"][0]
        self.assertAlmostEqual(out["start_sec"],2.2)
        self.assertAlmostEqual(out["end_sec"],3.2)

    def test_outside_window_is_rejected_without_writes(self):
        before=(self.project/"EDIT_PLAN.json").read_bytes()
        d=copy.deepcopy(self.base);d["main_timeline"]["segments"][0]["start_sec"]=99
        with self.assertRaises(fr.AutoEditeError):fr.apply_ai_editing_brief(self.project,self.markdown(d))
        self.assertEqual(before,(self.project/"EDIT_PLAN.json").read_bytes())

    def test_boolean_strings_and_nan_are_rejected(self):
        for value in ("false",0):
            d=copy.deepcopy(self.base);d["configuration"]["edition"]["create_clean_version"]=value
            with self.assertRaises(fr.AutoEditeError):self.bundle(d)
        d=copy.deepcopy(self.base);d["main_timeline"]["segments"][0]["start_sec"]=float("nan")
        with self.assertRaises(fr.AutoEditeError):fr.parse_ai_editing_brief(self.markdown(d))

    def test_duplicate_json_and_scope_are_rejected(self):
        path=self.markdown();text=path.read_text();path.write_text(text.replace('"schema_version": 2','"schema_version": 2, "schema_version": 1',1))
        with self.assertRaises(fr.AutoEditeError):fr.parse_ai_editing_brief(path)
        path=self.markdown();path.write_text(path.read_text().replace('<!-- ROTEIRO: teste-a -->','<!-- ROTEIRO: errado -->'))
        with self.assertRaises(fr.AutoEditeError):fr.parse_ai_editing_brief(path)

    def test_media_identity_and_untrusted_paths(self):
        d=copy.deepcopy(self.base);d["roteiro"]["project_id"]="outro"
        with self.assertRaises(fr.AutoEditeError):self.bundle(d)
        d=copy.deepcopy(self.base);d["main_timeline"]["segments"][0]["source_path"]="/etc/passwd"
        self.assertEqual(self.bundle(d)["main_timeline"]["segments"][0]["source_path"],"originais/colors.mp4")

    def test_before_after_uses_distinct_real_frames(self):
        d=copy.deepcopy(self.base);d["carousel"]={"enabled":True,"output":{"width":320,"height":400},"slides":[{"kind":"before_after","title":"COMPARAÇÃO DE TESTE","service_key":"projetos_3d","comparison":{"before":{"media_id":"M0001","time_sec":.5,"label":"ANTES"},"after":{"media_id":"M0001","time_sec":4.5,"label":"DEPOIS"}}}]}
        b=self.bundle(d);refs=b["carousel"]["slides"][0]["comparison"]
        from PIL import Image
        a=Image.open(extract_reference(vars(fr),self.project,refs["before"])).getpixel((120,100))
        z=Image.open(extract_reference(vars(fr),self.project,refs["after"])).getpixel((120,100))
        self.assertGreater(a[0],200);self.assertGreater(z[2],200)

    def test_replacing_plan_removes_stale_reels_and_style(self):
        scope.write(self.project/"social/planos/REEL_99S.json",{"old":True})
        fr.apply_ai_editing_brief(self.project,self.markdown())
        self.assertFalse((self.project/"social/planos/REEL_99S.json").exists())
        d=copy.deepcopy(self.base);d["roteiro"]["id"]="teste-b";d["configuration"].pop("visual_effects");d.pop("card_style")
        fr.apply_ai_editing_brief(self.project,self.markdown(d))
        self.assertEqual(fr.read_json(self.project/"CARD_STYLE.json")["palette"],fr.load_card_style()["palette"])
        self.assertFalse(fr.read_json(self.project/"EDIT_PLAN.json")["visual_effects"]["speed_ramping"])
        self.assertGreaterEqual(len(scope.list_versions(self.project)),4)

    def test_reset_preserves_media_and_restores_decisions(self):
        fr.apply_ai_editing_brief(self.project,self.markdown())
        media=(self.project/"originais/colors.mp4").read_bytes();manifest=(self.project/"MANIFESTO_MEDIA.json").read_bytes()
        result=scope.reset_definitions(self.project)
        self.assertFalse((self.project/"EDIT_PLAN.json").exists())
        self.assertEqual(media,(self.project/"originais/colors.mp4").read_bytes())
        self.assertEqual(manifest,(self.project/"MANIFESTO_MEDIA.json").read_bytes())
        self.assertEqual((self.project/"_ENTRADA/CONTEXTO_PROJETO.md").read_text(),"")
        scope.restore_version(self.project,result["backup"])
        self.assertEqual(fr.read_json(self.project/"EDIT_PLAN.json")["roteiro"]["id"],"teste-a")

    def test_recoverable_transaction_rolls_back(self):
        scope.write(self.project/"a.json",{"old":1});scope.write(self.project/"b.json",{"old":2})
        original=os.replace
        def broken(src,dst):
            if str(dst).endswith("/b.json"):raise OSError("simulated disk failure")
            return original(src,dst)
        with patch("project_scope.os.replace",side_effect=broken):
            with self.assertRaises(OSError):scope.publish_files(self.project,{"a.json":{"new":1},"b.json":{"new":2}})
        self.assertEqual(fr.read_json(self.project/"a.json"),{"old":1})
        self.assertEqual(fr.read_json(self.project/"b.json"),{"old":2})

    def test_generate_after_reset_does_not_need_zip(self):
        scope.reset_definitions(self.project)
        path=fr.generate_ai_editing_brief(self.project)
        data=fr.parse_ai_editing_brief(path)
        self.assertEqual(data["schema_version"],2)
        self.assertEqual(len(data["media_inventory"]),2)

    def test_render_snapshot_is_independent(self):
        calls=[]
        @scope.isolated_render
        def fake_render(project,plan_path):
            calls.append((project,fr.read_json(plan_path),fr.read_json(project/"CARD_STYLE.json")))
            result=project/"entrega/test.mp4";result.parent.mkdir();result.write_bytes(b"fixture")
            return [result]
        fr.apply_ai_editing_brief(self.project,self.markdown())
        a=fake_render(self.project,self.project/"EDIT_PLAN.json")[0]
        d=copy.deepcopy(self.base);d["roteiro"]["id"]="teste-b";d["card_style"]["palette"]["orange"]="#FF7A00"
        fr.apply_ai_editing_brief(self.project,self.markdown(d))
        b=fake_render(self.project,self.project/"EDIT_PLAN.json")[0]
        self.assertNotEqual(a,b);self.assertTrue(a.is_file())
        self.assertNotEqual(calls[0][2]["palette"]["orange"],calls[1][2]["palette"]["orange"])
        self.assertEqual(calls[0][1]["roteiro"]["id"],"teste-a")

    def test_render_and_frame_hold_are_executed(self):
        fr.apply_ai_editing_brief(self.project,self.markdown())
        result=fr.render_plan(self.project,self.project/"EDIT_PLAN.json",only="branded")
        self.assertEqual(len(result),1)
        info=fr.parse_probe(result[0],fr.ffprobe(result[0]))
        self.assertAlmostEqual(info["duration_sec"],5,delta=.12)
        self.assertEqual((info["width"],info["height"]),(320,568))
        # The hold spans seconds 2–4. Decode the actual final video at 3 seconds.
        raw=subprocess.run(["ffmpeg","-loglevel","error","-ss","3","-i",str(result[0]),"-frames:v","1","-f","rawvideo","-pix_fmt","rgb24","-"],capture_output=True,check=True).stdout
        pixel=raw[(284*320+160)*3:(284*320+160)*3+3]
        self.assertGreater(pixel[2],200)

    def test_service_layouts_create_different_images(self):
        from PIL import Image
        style=self.base["card_style"]
        hashes=[]
        for service in fr.load_service_catalog():
            path=self.project/(service+".png")
            fr.card_image(path,{"type":"card","card_kind":"service","service_key":service,"title":"SERVIÇO","body":"Demonstração do layout."},
                          {"output":{"width":540,"height":675}},fr.load_brand(),style,self.project)
            hashes.append(hashlib.sha256(Image.open(path).tobytes()).hexdigest())
        self.assertEqual(len(set(hashes)),9)


if __name__=="__main__":
    unittest.main(verbosity=2)
