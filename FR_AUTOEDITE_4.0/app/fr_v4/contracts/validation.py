"""Validação read-only. Publicação transacional continua responsabilidade da integração."""
from __future__ import annotations
import math
from pathlib import Path
import json
from .markdown import Document, ContractError, canonical, fingerprint
from ..core.config import SERVICE_BY_KEY
from ..quiet_luxury.validators import check_silencio, check_veracidade, validate_text


def validate_schema(value, schema, *, root=None, path='$'):
    """Subconjunto explícito do schema distribuído; não anuncia suporte universal a JSON Schema."""
    root = root or schema
    if '$ref' in schema:
        ref = schema['$ref']
        if not ref.startswith('#/$defs/'): raise ContractError('Referência externa de schema proibida.')
        return validate_schema(value, root['$defs'][ref.split('/')[-1]], root=root, path=path)
    kind = schema.get('type')
    types = kind if isinstance(kind, list) else [kind]
    checks = {'object': lambda x: isinstance(x, dict), 'array': lambda x: isinstance(x, list),
        'string': lambda x: isinstance(x, str), 'boolean': lambda x: type(x) is bool,
        'number': lambda x: type(x) in (float, int) and math.isfinite(x),
        'integer': lambda x: type(x) is int, 'null': lambda x: x is None,
        None: lambda x: True}
    if not any(checks[t](value) for t in types): raise ContractError(f'{path}: tipo inválido; esperado {kind}.')
    if 'const' in schema and value != schema['const']: raise ContractError(f'{path}: valor fixo incompatível.')
    if 'enum' in schema and value not in schema['enum']: raise ContractError(f'{path}: use {schema["enum"]}.')
    if value is None: return
    if isinstance(value, dict):
        for required in schema.get('required', []):
            if required not in value: raise ContractError(f'{path}.{required}: obrigatório.')
        fields = schema.get('properties', {})
        if schema.get('additionalProperties') is False:
            extra = set(value)-set(fields)
            if extra: raise ContractError(f'{path}: campos desconhecidos: {sorted(extra)}.')
        for key, item in value.items():
            if key in fields: validate_schema(item, fields[key], root=root, path=f'{path}.{key}')
    elif isinstance(value, list):
        if len(value) > schema.get('maxItems', 10000): raise ContractError(f'{path}: lista longa demais.')
        if len(value) < schema.get('minItems', 0): raise ContractError(f'{path}: lista incompleta.')
        if schema.get('uniqueItems') and len({canonical(x) for x in value}) != len(value):
            raise ContractError(f'{path}: itens duplicados.')
        for i, item in enumerate(value): validate_schema(item, schema.get('items', {}), root=root, path=f'{path}[{i}]')
    elif isinstance(value, str):
        if len(value) < schema.get('minLength', 0) or len(value) > schema.get('maxLength', 100000):
            raise ContractError(f'{path}: comprimento inválido.')
    elif type(value) in (int, float):
        if value < schema.get('minimum', -math.inf) or value > schema.get('maximum', math.inf):
            raise ContractError(f'{path}: número fora dos limites.')


def validate(document: Document, *, expected_header: dict, manifest: dict,
             schema: dict, assets: dict) -> dict:
    """Header esperado deve vir do pacote gerado no projeto, nunca da resposta da IA."""
    if not isinstance(expected_header, dict) or expected_header.get('contrato_versao') != '4.0.0':
        raise ContractError('Cabeçalho gerado deve ser versão 4.0.0.')
    if canonical(document.header) != canonical(expected_header):
        raise ContractError('Cabeçalho imutável alterado ou pertencente a outro pacote.')
    if expected_header.get('hash_manifesto_media') != fingerprint(manifest):
        raise ContractError('Manifesto mudou desde a geração do pacote; gere outro roteiro.')
    payload = document.payload
    validate_schema(payload, schema)
    matches = {'contrato_versao': 'contrato_versao', 'project_id': 'projeto_id',
        'input_mode': 'input_mode', 'timeline_locked': 'timeline_locked',
        'allow_duration_extension': 'allow_duration_extension', 'style_pack_id': 'style_pack_id'}
    for key, header_key in matches.items():
        if payload.get(key) != expected_header.get(header_key):
            raise ContractError(f'{key}: diverge do cabeçalho imutável.')
    media = {str(row['id']): row for row in manifest.get('media', [])}
    if len(media) != len(manifest.get('media', [])): raise ContractError('Manifesto contém IDs duplicados.')
    duration = payload['duracao_final_estimada_sec']
    if not expected_header.get('regras_quiet_luxury_ativo') is True:
        raise ContractError('Regras quiet luxury devem estar ativas nesta versão.')
    violations = []
    seen = set()
    for i, cut in enumerate(payload['cuts']):
        row = media.get(cut['media_id'])
        if not row or row.get('status', 'ok') != 'ok': raise ContractError(f'cuts[{i}]: mídia indisponível.')
        if row.get('media_type') != 'video':
            raise ContractError(f'cuts[{i}]: cortes v4 nesta fundação exigem vídeo; fotos permanecem no legado.')
        if not 0 <= cut['start_sec'] < cut['end_sec'] <= float(row.get('duration_sec', 0)):
            raise ContractError(f'cuts[{i}]: janela fora da mídia.')
        window_start = float(row.get('scene_start_sec') or 0)
        window_end = float(row.get('scene_end_sec') or row.get('duration_sec') or 0)
        if cut['start_sec'] < window_start or cut['end_sec'] > window_end:
            raise ContractError(f'cuts[{i}]: janela fora da cena identificada.')
    for group in ('overlays', 'chapters'):
        for i, item in enumerate(payload[group]):
            if not 0 <= item['start_sec'] < item['end_sec'] <= duration:
                raise ContractError(f'{group}[{i}]: tempo fora da duração final.')
            id_key = 'overlay_id' if group == 'overlays' else 'id'
            identity = group+':'+item[id_key]
            if identity in seen: raise ContractError(f'{group}[{i}]: ID duplicado.')
            seen.add(identity)
    for i, overlay in enumerate(payload['overlays']):
        key = overlay.get('service_key')
        if key and key not in SERVICE_BY_KEY: raise ContractError(f'overlays[{i}].service_key: inválido.')
        if overlay['kind'] == 'service_card' and not key: raise ContractError(f'overlays[{i}]: serviço obrigatório.')
        asset_id = overlay.get('asset_id')
        if asset_id and (asset_id not in assets or assets[asset_id].get('status') == 'pending_asset'):
            raise ContractError(f'overlays[{i}].asset_id: inexistente ou pendente.')
        violations += validate_text(overlay.get('text', ''), path=f'overlays[{i}].text',
                                    claims=overlay.get('claims'), media_status=overlay.get('media_status'))
        violations += check_veracidade(overlay.get('claims', []), f'overlays[{i}].claims')
    for i, slide in enumerate(payload['social']['carrossel_slides']):
        if slide.get('media_id') and slide['media_id'] not in media:
            raise ContractError(f'social.carrossel_slides[{i}].media_id: inexistente.')
        violations += validate_text(slide.get('texto', ''), path=f'social.carrossel_slides[{i}].texto', claims=slide.get('claims'))
    music = payload['audio'].get('music_asset_id')
    if music and (music not in assets or assets[music].get('status') == 'pending_asset'):
        raise ContractError('audio.music_asset_id: asset indisponível.')
    violations += check_silencio(payload['cuts'], payload['overlays'])
    if payload['input_mode'] == 'ready_video':
        if payload['timeline_locked'] is not True: raise ContractError('ready_video exige timeline_locked=true.')
        base_id = payload.get('base_video_id')
        base = media.get(base_id)
        if not base or base.get('media_type') != 'video': raise ContractError('base_video_id inválido.')
        total = float(base['duration_sec'])
        fps = max(float(base.get('fps') or 24), 1)
        if abs(duration-total) > 1/fps:
            raise ContractError('Nesta fundação, extensão de duração requer integração explícita de intro/outro.')
        cuts = payload['cuts']
        if cuts and (len(cuts) != 1 or cuts[0]['media_id'] != base_id or cuts[0]['start_sec'] != 0
                     or abs(cuts[0]['end_sec']-total) > 1/fps):
            raise ContractError('ready_video não permite recorte ou reordenação do vídeo-base.')
        if any(c['transicao_in'] != 'cut' or c['transicao_out'] != 'cut' for c in cuts):
            raise ContractError('ready_video não permite transições sobre os quadros do vídeo-base.')
        if payload['audio']['preserve_original'] is not True:
            raise ContractError('ready_video exige áudio original preservado.')
    errors = [v.as_dict() for v in violations if v.severity == 'error']
    warnings = [v.as_dict() for v in violations if v.severity != 'error']
    if errors: raise ContractError(json.dumps({'errors': errors}, ensure_ascii=False))
    return {'valid': True, 'contract_version': '4.0.0', 'warnings': warnings,
            'applied': False, 'render_executed': False,
            'note': 'Validação estrutural não certifica verdade semântica nem suporte integral do render.'}
