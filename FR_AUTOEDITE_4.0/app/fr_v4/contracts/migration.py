"""Migração conservadora para revisão: preserva integralmente payload legado."""
from __future__ import annotations
import copy
from .markdown import Document, ContractError, fingerprint
from ..core.config import STYLE_PACK_ID


def from_legacy(payload: dict, *, manifest: dict, project_id: str,
                generated_at: str) -> tuple[Document, list[str]]:
    if payload.get('schema_version', 1) not in {1, 2}:
        raise ContractError('Migrador aceita somente schema_version 1 ou 2 da base recebida.')
    if not project_id or not generated_at: raise ContractError('Identidade e data explícitas são obrigatórias.')
    original = copy.deepcopy(payload)
    main = payload.get('main_timeline', payload if 'segments' in payload else {})
    segments = main.get('segments', [])
    mode = payload.get('input_mode', main.get('input_mode', manifest.get('input_mode', 'raw_media')))
    cuts, notes = [], []
    for i, segment in enumerate(segments):
        if segment.get('type') != 'media':
            notes.append(f'segments[{i}]: card mantido em legacy_payload; requer conversão explícita de família.')
            continue
        if segment.get('external_asset'):
            notes.append(f'segments[{i}]: asset externo preservado, não convertido automaticamente.')
            continue
        if segment.get('enabled', True) is False: continue
        speed = float(segment.get('playback_speed') or 1)
        if speed != 1:
            notes.append(f'segments[{i}]: velocidade {speed} preservada; v4 cuts ainda não executa speed ramp.')
        start = float(segment.get('start_sec') or 0)
        end = float(segment.get('end_sec', start+float(segment.get('duration_sec') or 0)*speed))
        if end <= start: raise ContractError(f'segments[{i}]: intervalo inválido; migração interrompida.')
        transition = segment.get('transition') or 'cut'
        if transition not in {'cut', 'fade', 'fade_black', 'dissolve'}:
            notes.append(f'segments[{i}]: transição {transition} preservada apenas no legado; revisão necessária.')
            transition = 'cut'
        cuts.append({'media_id': segment.get('media_id', ''), 'start_sec': start,
                     'end_sec': end, 'transicao_in': transition, 'transicao_out': 'cut'})
    if not cuts and mode == 'raw_media':
        raise ContractError('Nenhum recorte conversível; não gerar roteiro vazio fingindo migração.')
    duration = sum(float(s.get('duration_sec') or 0) for s in segments if s.get('enabled', True))
    if duration <= 0: raise ContractError('Duração não encontrada na base.')
    base_id = payload.get('base_video_id') or main.get('base_video_id') or manifest.get('base_video_id')
    header = {'contrato_versao': '4.0.0', 'projeto_id': project_id, 'gerado_em': generated_at,
        'hash_manifesto_media': fingerprint(manifest), 'duracao_total_estimada_sec': duration,
        'input_mode': mode, 'timeline_locked': mode == 'ready_video',
        'allow_duration_extension': bool(payload.get('allow_duration_extension', False)),
        'style_pack_id': STYLE_PACK_ID, 'plataformas_alvo': [], 'regras_quiet_luxury_ativo': True}
    result = {'contrato_versao': '4.0.0', 'project_id': project_id, 'input_mode': mode,
        'base_video_id': base_id, 'timeline_locked': header['timeline_locked'],
        'allow_duration_extension': header['allow_duration_extension'],
        'duracao_final_estimada_sec': duration, 'chapters': [], 'cuts': cuts, 'overlays': [],
        'audio': {'preserve_original': True, 'music_asset_id': None, 'music_volume': 0,
                  'ducking': False, 'normalize_lufs': None},
        'captions': {'gerar_srt': False, 'queimar': False, 'estilo': 'quiet_luxury_minimal'},
        'social': {'reels_sec': [], 'stories_partes_sec': 15, 'carrossel_slides': []},
        'style_pack_id': STYLE_PACK_ID, 'notas_editoriais': 'Candidato migrado; requer revisão e integração de execução.',
        'legacy_payload': original}
    # Ponte explícita para consumidores 3.4.0. Estes campos não substituem o
    # contrato v4; permitem que a aplicação explique e preserve opções ainda
    # não executáveis sem descartá-las silenciosamente.
    result['main_timeline'] = copy.deepcopy(main)
    result['audio_policy'] = str(main.get('audio_policy') or 'preserve')
    result['allowed_values'] = {
        'overlay_kinds': ['service_card', 'common_card', 'balloon', 'callout', 'lower_third', 'caption', 'logo'],
        'overlay_presentations': ['overlay', 'full_frame'],
        'overlay_positions': ['top_left', 'top_center', 'top_right', 'center', 'bottom_left', 'bottom_center', 'bottom_right'],
        'overlay_safe_areas': ['auto', 'title_safe', 'action_safe', 'none'],
        'overlay_animations': ['none', 'fade', 'slide_up', 'slide_down', 'soft_scale'],
        'audio_policies': ['preserve', 'mix'],
        'overlay_item_fields': ['overlay_id', 'kind', 'start_sec', 'end_sec', 'text', 'service_key',
                                'asset_id', 'presentation', 'position', 'safe_area', 'opacity',
                                'animation_in', 'animation_out', 'audio_policy', 'rationale'],
    }
    body = ('# Roteiro Mestre — migração para revisão\n\n'
            '## Decisões preservadas\n'
            'O payload anterior está integralmente em legacy_payload. Não é executado por esta fundação.\n\n'
            '## Revisão obrigatória\n'+'\n'.join('- '+note for note in notes))
    return Document(header, body, result), notes
