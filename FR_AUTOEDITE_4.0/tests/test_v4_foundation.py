"""Fixtures sintéticas em tmp_path. Não usa Studio nem mídias reais."""
from pathlib import Path
import copy
import json
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
from fr_v4.core.grid import Grid,Box
from fr_v4.core.config import SERVICES,TOKENS,STYLE_PACK_ID
from fr_v4.contracts.markdown import Document,ContractError,parse,serialize,fingerprint
from fr_v4.contracts.validation import validate
from fr_v4.contracts.migration import from_legacy
from fr_v4.style_packs.registry import confined,normalize,digest,index_assets,resolve,AssetError,signature
from fr_v4.adapters.base import Adapter,AdapterError,AdapterDeferred,Request,Result
from fr_v4.adapters.registry import Registry,build_registry
from fr_v4.quiet_luxury.validators import validate_text,check_silencio,check_assinatura


def fixture():
    manifest={'media':[{'id':'V1','media_type':'video','status':'ok','duration_sec':8,'fps':24}]}
    header={'contrato_versao':'4.0.0','projeto_id':'fixture','gerado_em':'2026-09-16T00:00:00Z',
        'hash_manifesto_media':fingerprint(manifest),'duracao_total_estimada_sec':8,
        'input_mode':'ready_video','timeline_locked':True,'allow_duration_extension':False,
        'style_pack_id':STYLE_PACK_ID,'plataformas_alvo':[],'regras_quiet_luxury_ativo':True}
    payload={'contrato_versao':'4.0.0','project_id':'fixture','input_mode':'ready_video',
        'base_video_id':'V1','timeline_locked':True,'allow_duration_extension':False,
        'duracao_final_estimada_sec':8,'chapters':[],
        'cuts':[{'media_id':'V1','start_sec':0,'end_sec':8,'transicao_in':'cut','transicao_out':'cut'}],
        'overlays':[],'audio':{'preserve_original':True,'music_asset_id':None,'music_volume':0,'ducking':False,'normalize_lufs':None},
        'captions':{'gerar_srt':False,'queimar':False,'estilo':'quiet_luxury_minimal'},
        'social':{'reels_sec':[],'stories_partes_sec':15,'carrossel_slides':[]},
        'style_pack_id':STYLE_PACK_ID,'notas_editoriais':''}
    return Document(header,'# Revisão humana',payload),manifest


def check(document,manifest,header=None):
    schema=json.loads((ROOT/'schemas/roteiro_mestre_v4.schema.json').read_text())
    return validate(document,expected_header=header or document.header,manifest=manifest,schema=schema,assets={})


def test_grid_reference_and_kernel():
    grid=Grid(1080,1920)
    assert grid.safe==Box(72,140,936,1530)
    assert grid.column==56 and grid.gutter==24 and grid.unit==8
    assert grid.safe.contains(grid.kernel)
    assert grid.editorial.y%8==0 and grid.editorial.bottom%8==0
    assert grid.validate({'unsafe':Box(0,0,100,100)})==['unsafe']


@pytest.mark.parametrize('size',[(1080,1080),(1080,1350),(1920,1080),(2160,3840)])
def test_grid_responsive(size):
    grid=Grid(*size)
    assert grid.safe.contains(grid.kernel)
    assert grid.span(0,12,grid.editorial.y,grid.unit).width==pytest.approx(grid.editorial.width)


def test_13_services_have_distinct_codes():
    assert len(SERVICES)==len({s.key for s in SERVICES})==len({s.code for s in SERVICES})==13


def test_header_body_json_roundtrip():
    document,manifest=fixture()
    assert parse(serialize(document))==document
    result=check(document,manifest)
    assert result['valid'] and not result['applied'] and not result['render_executed']


def test_modified_header_and_wrong_manifest_rejected():
    document,manifest=fixture();expected=copy.deepcopy(document.header)
    document.header['projeto_id']='outro'
    with pytest.raises(ContractError):check(document,manifest,expected)
    document,manifest=fixture();manifest['media'][0]['duration_sec']=9
    with pytest.raises(ContractError):check(document,manifest)


def test_duplicate_keys_and_nan_rejected():
    document,_=fixture();text=serialize(document)
    with pytest.raises(ContractError):parse(text.replace('"project_id": "fixture",','"project_id": "fixture", "project_id": "outro",'))
    with pytest.raises(ContractError):parse(text.replace('"duracao_final_estimada_sec": 8','"duracao_final_estimada_sec": NaN'))


def test_yaml_tags_and_extra_json_rejected():
    document,_=fixture();text=serialize(document)
    with pytest.raises(ContractError):parse(text.replace('projeto_id: "fixture"','projeto_id: !!python/object:object {}'))
    with pytest.raises(ContractError):parse(text.replace('# Revisão humana','# Revisão humana\n```json\n{}\n```'))


def test_carousel_enum_rejected():
    document,manifest=fixture()
    document.payload['social']['carrossel_slides']=[{'kind':'service_card','media_id':None,'texto':'Serviço'}]
    with pytest.raises(ContractError,match='kind'):check(document,manifest)


@pytest.mark.parametrize('change',[{'start_sec':1},{'end_sec':10},{'media_id':'INEXISTENTE'},{'start_sec':True}])
def test_invalid_cuts_rejected(change):
    document,manifest=fixture();document.payload['cuts'][0].update(change)
    with pytest.raises(ContractError):check(document,manifest)


def test_duration_extension_does_not_unlock_base():
    document,manifest=fixture()
    document.header['allow_duration_extension']=True;document.payload['allow_duration_extension']=True
    document.payload['cuts'][0]['start_sec']=1
    with pytest.raises(ContractError):check(document,manifest)


def test_ready_video_transition_and_audio_rejected():
    document,manifest=fixture();document.payload['cuts'][0]['transicao_in']='fade'
    with pytest.raises(ContractError):check(document,manifest)
    document,manifest=fixture();document.payload['audio']['preserve_original']=False
    with pytest.raises(ContractError):check(document,manifest)


def test_migration_keeps_legacy_bytes_semantics():
    _doc,manifest=fixture()
    payload={'schema_version':2,'main_timeline':{'segments':[
        {'type':'card','title':'Abertura','duration_sec':2},
        {'type':'media','media_id':'V1','start_sec':0,'duration_sec':4,'playback_speed':1}]},
        'strategy':{'custom_metadata':'Preservar'}}
    before=copy.deepcopy(payload)
    document,notes=from_legacy(payload,manifest=manifest,project_id='fixture',generated_at='2026-09-16T00:00:00Z')
    assert payload==before and document.payload['legacy_payload']==before
    assert notes and 'card' in notes[0]


def test_assets_reject_escape(tmp_path):
    with pytest.raises(AssetError):confined(tmp_path,'../outside.png')
    with pytest.raises(AssetError):confined(tmp_path,'/etc/passwd')


def test_normalizer_preserves_original_and_is_repeatable(tmp_path):
    from PIL import Image
    source=tmp_path/'source.png';target=tmp_path/'normalized.png'
    Image.new('RGBA',(31,27),(10,40,30,255)).save(source)
    before=digest(source)
    one=normalize(source,target);two=normalize(source,target)
    assert digest(source)==before and one['sha256']==two['sha256']
    with Image.open(target) as image:
        assert image.size==(2048,2048) and image.mode=='RGBA' and image.getpixel((0,0))[3]==0


def test_pending_assets_are_not_publishable(tmp_path):
    manifest=index_assets(tmp_path)
    assert len(manifest['assets'])==14
    assert all(row['status']=='pending_asset' and row['publicavel'] is False for row in manifest['assets'].values())
    path,row=resolve(tmp_path,'medallion_eletrica')
    assert path is None and row['sha256'] is None


def test_signature_changes_with_plan_and_style(tmp_path):
    index_assets(tmp_path)
    a=signature(tmp_path,{'service':'eletrica'},{'variant':'a'})
    b=signature(tmp_path,{'service':'hidraulica'},{'variant':'a'})
    c=signature(tmp_path,{'service':'eletrica'},{'variant':'b'})
    assert len({a,b,c})==3


def test_missing_binary_is_safe(monkeypatch):
    monkeypatch.setattr('shutil.which',lambda _name:None)
    adapter=Adapter('not_installed',1,executable='nonexistent')
    assert adapter.is_available() is False and adapter.version() is None


def test_fallback_records_backend(monkeypatch):
    def fail(_):raise AdapterError('fixture')
    adapter=Adapter('broken',1,state='implemented',operations={'probe':fail},
        fallback_handler=lambda request:Result('fallback',request.operation,{'ok':True}))
    monkeypatch.setattr(adapter,'is_available',lambda:True)
    result=Registry([adapter]).run_with_fallback('broken',Request('probe'))
    assert result.backend=='fallback' and result.fallback_used and result.warnings


def test_bad_detection_does_not_break_registry(monkeypatch):
    adapter=Adapter('bad',1)
    def broken():raise RuntimeError('fixture')
    monkeypatch.setattr(adapter,'is_available',broken)
    registry=Registry([adapter]);assert registry.list_available()==[]
    assert registry.diagnose()[0]['available'] is False


def test_tier_three_never_runs(monkeypatch):
    adapter=build_registry().get('ollama')
    monkeypatch.setattr(adapter,'is_available',lambda:True)
    monkeypatch.setattr('subprocess.run',lambda *a,**k:pytest.fail('Tier3 iniciou subprocesso'))
    assert adapter.version() is None and adapter.capabilities()==set()
    with pytest.raises(AdapterDeferred):adapter.run(Request('generate'))


def test_quiet_luxury_pass_fail():
    assert not validate_text('Encaixe e acabamento.')
    assert any(v.severity=='error' for v in validate_text('Resultado incrível.'))
    assert check_silencio([{'start_sec':0,'end_sec':.2}],[])
    assert check_assinatura({'gold':'#FFFFFF'})
    assert check_assinatura(dict(TOKENS))==[]
