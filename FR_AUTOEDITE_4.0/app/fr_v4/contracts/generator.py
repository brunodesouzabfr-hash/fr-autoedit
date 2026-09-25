"""Geração determinística do Roteiro Mestre v4 para uma IA externa."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .markdown import Document, fingerprint, serialize
from ..core.config import STYLE_PACK_ID

BODY = """# ROTEIRO MESTRE — EDITAR E DEVOLVER

Edite somente o apêndice JSON. Preserve integralmente o cabeçalho YAML.
Use exclusivamente IDs presentes no manifesto. Não invente clientes, preços,
métricas, prova social, urgência, escassez, resultados ou características não
visíveis/confirmadas. `rationale` e `notas_editoriais` são metadados e nunca
devem aparecer no vídeo.

## Objetivo editorial

Construa uma narrativa clara, tecnicamente verdadeira e adequada à plataforma.
O ritmo deve responder ao material: quiet luxury não significa lentidão fixa e
retenção não significa cortes frenéticos. Textos de locução, legenda e overlay
devem conter apenas conteúdo publicável, sem comentários da IA.
"""


def generate(*, manifest: dict[str, Any], project_id: str, input_mode: str = "raw_media",
             base_video_id: str | None = None, duration: float | None = None,
             platforms: list[str] | None = None, context: str = "") -> tuple[str, dict]:
    if input_mode not in {"raw_media", "ready_video"}:
        raise ValueError("input_mode inválido.")
    media = manifest.get("media", [])
    if duration is None:
        if input_mode == "ready_video" and base_video_id:
            duration = next((float(row.get("duration_sec") or 0) for row in media if row.get("id") == base_video_id), 0.)
        else:
            duration = sum(float(row.get("duration_sec") or 0) for row in media)
    duration = max(.4, float(duration or 0))
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    header = {"contrato_versao": "4.0.0", "projeto_id": project_id, "gerado_em": generated,
              "hash_manifesto_media": fingerprint(manifest), "duracao_total_estimada_sec": duration,
              "input_mode": input_mode, "timeline_locked": input_mode == "ready_video",
              "allow_duration_extension": False, "style_pack_id": STYLE_PACK_ID,
              "plataformas_alvo": list(platforms or []), "regras_quiet_luxury_ativo": True}
    cuts = []
    if input_mode == "ready_video" and base_video_id:
        cuts = [{"media_id": base_video_id, "start_sec": 0, "end_sec": duration,
                 "transicao_in": "cut", "transicao_out": "cut"}]
    payload = {"contrato_versao": "4.0.0", "project_id": project_id, "input_mode": input_mode,
               "base_video_id": base_video_id, "timeline_locked": input_mode == "ready_video",
               "allow_duration_extension": False, "duracao_final_estimada_sec": duration,
               "chapters": [], "cuts": cuts, "overlays": [],
               "audio": {"preserve_original": True, "music_asset_id": None, "music_volume": 0,
                         "ducking": False, "normalize_lufs": None},
               "captions": {"gerar_srt": False, "queimar": False, "estilo": "quiet_luxury_minimal"},
               "social": {"reels_sec": [], "stories_partes_sec": 15, "carrossel_slides": []},
               "style_pack_id": STYLE_PACK_ID,
               "notas_editoriais": context[:8000], "legacy_payload": None,
               "main_timeline": {"segments": []}, "audio_policy": "preserve",
               "allowed_values": allowed_values()}
    document = Document(header, BODY, payload)
    content = serialize(Document(document.header, BODY, document.payload))
    return content, header


def allowed_values() -> dict:
    return {
        "overlay_kinds": ["service_card", "common_card", "balloon", "callout", "lower_third", "caption", "logo"],
        "overlay_presentations": ["overlay", "full_frame"],
        "overlay_positions": ["top_left", "top_center", "top_right", "center", "bottom_left", "bottom_center", "bottom_right"],
        "overlay_safe_areas": ["auto", "title_safe", "action_safe", "none"],
        "overlay_animations": ["none", "fade", "slide_up", "slide_down", "soft_scale"],
        "audio_policies": ["preserve", "mix"],
        "overlay_item_fields": ["overlay_id", "kind", "start_sec", "end_sec", "text", "service_key",
                                "asset_id", "presentation", "position", "safe_area", "opacity",
                                "animation_in", "animation_out", "audio_policy", "rationale", "balloon"],
    }
