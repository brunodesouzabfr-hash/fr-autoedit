"""The Roteiro Mestre v2 is a declarative contract, never executable code."""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import re
from types import SimpleNamespace

import project_scope as scope

CARD_KINDS = {"intro", "service", "phase", "outro", "detail", "comparison"}
ANIMATIONS = {"none", "soft_zoom", "forge_reveal", "zoom_out", "fade"}
PROTECTED = {"ai_copilot", "cloud_export", "handoff", "local_analysis"}
CARD_MODES = {"none", "common", "service"}
SERVICE_ALIASES = {
    "projeto_3d": "projetos_3d", "project_3d": "projetos_3d",
    "mobilia": "moveis", "marcenaria": "moveis", "mobilia_marcenaria": "moveis",
    "producoes_eventos": "producoes", "eventos": "producoes",
}
SUPPORTED_SEGMENT_FIELDS = {
    "segment_id", "type", "enabled", "include_in", "duration_sec", "transition",
    "transition_duration_sec", "image_animation", "card_animation", "stabilization",
    "force_stabilization", "editorial_timelapse", "external_asset", "lower_third",
    "title", "body", "on_screen_text", "technical_note", "phase_title",
    "decision_reason", "card_kind", "card_mode", "service_key", "service_asset",
    "service_layout", "service_family", "associated_card_id", "media_id", "media_type",
    "source_path", "proxy_path", "thumbnail_path", "has_audio", "start_sec", "end_sec",
    "start_time_basis", "source_window_start_sec", "source_window_end_sec",
    "source_duration_sec", "playback_speed", "freeze_frame", "visual", "comparison",
    "coverage_role", "phase_order", "quality_score", "external_role", "include_in_reels",
    "narration", "narration_text", "subtitles", "cta", "cut_style", "keyframes", "unsupported_requests",
    "service_id", "service_name", "service_confidence", "service_card_enabled",
    "card_type", "card_family", "balloon_family", "visual_motif", "overlay_text",
    "voiceover_text", "caption_text", "transition_in", "transition_out", "balloon_texts",
}
AI_FILLER_PREFIXES = (
    "aqui está", "aqui esta", "claro!", "certamente!", "como solicitado",
    "observação:", "observacao:", "nota técnica:", "nota tecnica:",
)


def fail(c, message):
    raise c.AutoEditeError(message)


def number(c, value, label, low=0, high=21600):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        fail(c, f"{label}: informe um número finito, sem aspas.")
    if not low <= value <= high:
        fail(c, f"{label}: use um valor entre {low} e {high}.")
    return float(value)


def check_booleans(c, value, reference, prefix="configuration"):
    if not isinstance(value, dict):
        fail(c, f"{prefix}: esperado objeto JSON.")
    for key, item in value.items():
        original = reference.get(key)
        if isinstance(original, bool) and not isinstance(item, bool):
            fail(c, f"{prefix}.{key}: use true ou false, sem aspas.")
        if isinstance(original, dict):
            check_booleans(c, item, original, prefix + "." + key)
        if isinstance(item, float) and not math.isfinite(item):
            fail(c, f"{prefix}.{key}: número não finito.")


def clean_editorial_text(c, value, label, *, allow_empty=True):
    if not isinstance(value, str):
        fail(c, f"{label}: esperado texto.")
    text = " ".join(value.replace("\r", "\n").split())
    if not text and not allow_empty:
        fail(c, f"{label}: escreva um texto específico sustentado pelo projeto.")
    lowered = text.casefold()
    if any(lowered.startswith(prefix) for prefix in AI_FILLER_PREFIXES):
        fail(c, f"{label}: remova comentários da IA como ‘aqui está’, explicações ou notas fora do conteúdo final.")
    if len(text) > 4000:
        fail(c, f"{label}: limite o texto a 4000 caracteres.")
    return text


def validate_script_block(c, value, label):
    if value in (None, ""):
        return {"enabled": False, "text": ""}
    if isinstance(value, str):
        value = {"enabled": bool(value.strip()), "text": value}
    if not isinstance(value, dict):
        fail(c, f"{label}: use um objeto com enabled e text.")
    result = copy.deepcopy(value)
    enabled = result.get("enabled", bool(result.get("text")))
    if not isinstance(enabled, bool):
        fail(c, f"{label}.enabled: use true ou false.")
    result["enabled"] = enabled
    result["text"] = clean_editorial_text(c, result.get("text", ""), label + ".text")
    if enabled and not result["text"]:
        fail(c, f"{label}.text: texto obrigatório quando enabled=true.")
    return result


def clean_metadata(c, value, label):
    """Valida texto editorial aninhado sem executar metadados estratégicos."""
    if isinstance(value, str):
        return clean_editorial_text(c, value, label)
    if isinstance(value, list):
        if len(value) > 500:
            fail(c, f"{label}: limite a lista a 500 itens.")
        return [clean_metadata(c, item, f"{label}[{index}]") for index, item in enumerate(value)]
    if isinstance(value, dict):
        return {str(key): clean_metadata(c, item, f"{label}.{key}") for key, item in value.items()}
    if value is None or isinstance(value, (bool, int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            fail(c, f"{label}: número não finito.")
        return value
    fail(c, f"{label}: tipo de metadado não suportado.")


def validate_strategy(c, value):
    if not isinstance(value, dict):
        fail(c, "strategy: esperado objeto.")
    result = clean_metadata(c, copy.deepcopy(value), "strategy")
    editorial = result.get("editorial", {})
    if editorial and not isinstance(editorial, dict):
        fail(c, "strategy.editorial: esperado objeto.")
    funnel = str(editorial.get("funnel_stage") or "")
    if funnel and funnel not in {"awareness", "consideration", "conversion", "relacionamento"}:
        fail(c, "strategy.editorial.funnel_stage: use awareness, consideration, conversion ou relacionamento.")
    intent = str(editorial.get("primary_intent") or "")
    allowed_intents = {"educar", "inspirar", "provar_tecnica", "vender", "gerar_lead",
                       "fortalecer_marca", "mostrar_bastidor", "mostrar_antes_depois"}
    if intent and intent not in allowed_intents:
        fail(c, "strategy.editorial.primary_intent: escolha um valor de allowed_values.primary_intents.")
    return result


def normalize_segment_contract(c, segment, label, warnings):
    """Converte nomes estratégicos da Fase 2.1 para o contrato usado pelo render."""
    services = c.load_service_catalog()
    raw_service = str(segment.get("service_id") or segment.get("service_key") or "")
    service_key = SERVICE_ALIASES.get(raw_service, raw_service)
    if raw_service and service_key != raw_service:
        warnings.append({"level":"info", "block":label + ".service_id",
            "message":f"Alias de serviço `{raw_service}` normalizado para `{service_key}`.",
            "effect":"A família visual canônica será usada sem perder o trecho."})
    if service_key:
        segment["service_key"] = service_key
        segment["service_id"] = service_key
    confidence = segment.get("service_confidence")
    if confidence not in (None, ""):
        segment["service_confidence"] = number(c, confidence, label + ".service_confidence", 0, 1)
    if "service_card_enabled" in segment and not isinstance(segment["service_card_enabled"], bool):
        fail(c, f"{label}.service_card_enabled: use true ou false.")
    if "service_card_enabled" in segment:
        segment["card_mode"] = (
            "service" if segment["service_card_enabled"]
            else "common" if segment.get("type") == "card" else "none"
        )
    card_type = str(segment.get("card_type") or "")
    if card_type:
        if card_type in CARD_MODES:
            segment["card_mode"] = card_type
        elif card_type in CARD_KINDS:
            segment["card_kind"] = card_type
        elif card_type not in CARD_MODES | CARD_KINDS:
            warnings.append({"level":"warning", "block":label + ".card_type",
                "message":f"Tipo de card `{card_type}` não reconhecido.",
                "effect":"O valor foi preservado como pedido não executável; o trecho continua válido."})
            segment.setdefault("unsupported_requests", {})["card_type"] = card_type
    for alias, target in (("overlay_text", "on_screen_text"),
                          ("voiceover_text", "narration"), ("caption_text", "subtitles")):
        if alias not in segment:
            continue
        value = clean_editorial_text(c, segment[alias], label + "." + alias)
        segment[alias] = value
        if target in {"narration", "subtitles"}:
            if value:
                segment[target] = {"enabled": bool(value), "text": value}
            elif target in segment and isinstance(segment[target], dict):
                segment[alias] = str(segment[target].get("text") or "")
        elif value:
            segment[target] = value
        elif target in segment:
            segment[alias] = str(segment[target] or "")
    if str(segment.get("transition_in") or ""):
        segment["transition"] = segment["transition_in"]
    else:
        segment["transition_in"] = str(segment.get("transition") or "cut")
    transition_out = str(segment.get("transition_out") or "")
    if transition_out:
        if transition_out not in c.TRANSITION_MAP:
            warnings.append({"level":"warning", "block":label + ".transition_out",
                "message":f"Transição de saída `{transition_out}` não reconhecida.",
                "effect":"Foi preservada como metadado; a entrada do próximo trecho continua válida."})
        else:
            warnings.append({"level":"info", "block":label + ".transition_out",
                "message":"transition_out é metadado nesta versão do renderizador.",
                "effect":"Defina também transition_in no trecho seguinte para executar a passagem."})
        segment.setdefault("unsupported_requests", {})["transition_out"] = transition_out
    for field in ("service_name", "card_family", "balloon_family", "visual_motif"):
        if field in segment:
            segment[field] = clean_editorial_text(c, segment[field], label + "." + field)
    if "balloon_texts" in segment:
        if not isinstance(segment["balloon_texts"], list):
            fail(c, label + ".balloon_texts: use uma lista de textos finais.")
        segment["balloon_texts"] = clean_metadata(c, segment["balloon_texts"], label + ".balloon_texts")
        if segment["balloon_texts"]:
            warnings.append({"level":"info", "block":label + ".balloon_texts",
                "message":"Textos de balão foram validados e preservados como metadados.",
                "effect":"O overlay persistente atual não alterna múltiplos balões por trecho; revise na Etapa 06."})
    if service_key in services:
        profile = services[service_key]
        segment["service_name"] = profile.get("label", service_key)
        segment["card_family"] = profile.get("visual_family", profile.get("layout", "editorial"))
        segment["balloon_family"] = profile.get("balloon_family", "fr_tecnico")
        segment["visual_motif"] = profile.get("visual_motif", profile.get("visual_family", ""))
    return service_key


def media_ref(c, ref, manifest, label):
    if not isinstance(ref, dict):
        fail(c, f"{label}: esperado objeto com media_id e time_sec.")
    row = next((x for x in manifest.get("media", []) if x.get("id") == ref.get("media_id")), None)
    if not row or row.get("status", "ok") != "ok":
        fail(c, f"{label}: media_id ausente, inválido ou indisponível.")
    out = {"media_id": row["id"], "media_type": row["media_type"]}
    for key in ("source_path", "proxy_path", "thumbnail_path"):
        out[key] = row.get(key, "")
    if row["media_type"] == "video":
        t = number(c, ref.get("time_sec", 0), label + ".time_sec")
        basis = ref.get("time_basis", "absolute_parent_media")
        if basis not in {"absolute_parent_media", "scene_local"}:
            fail(c, f"{label}.time_basis: use scene_local ou absolute_parent_media.")
        start = float(row.get("scene_start_sec") or 0)
        end = float(row.get("scene_end_sec") or row.get("duration_sec") or 0)
        if basis == "scene_local":
            t += start
        if not start <= t < end:
            fail(c, f"{label}: quadro em {t:.3f}s fora de {row['id']} ({start:.3f} ≤ tempo < {end:.3f}s).")
        out.update(time_sec=round(t, 6), time_basis="absolute_parent_media")
    else:
        out.update(time_sec=0, time_basis="absolute_parent_media")
    out["label"] = str(ref.get("label") or "")[:120]
    return out


def validate_plan(c, plan, manifest, label, trusted=None, *, legacy=False):
    if not isinstance(plan, dict) or not isinstance(plan.get("segments"), list):
        fail(c, f"{label}.segments: esperado uma lista de segmentos.")
    plan = copy.deepcopy(plan)
    segments = plan["segments"]
    if not 1 <= len(segments) <= 10000:
        fail(c, f"{label}.segments: use entre 1 e 10000 segmentos.")
    repairs = []
    warnings = []
    if legacy:
        # Preserve the R4 compatibility rules, then enforce the current contract.
        plan = c._validate_imported_plan_v1(plan, manifest, label, trusted_external=trusted)
        segments = plan["segments"]
        repairs = plan.get("import_repairs", [])
    rows = {r["id"]: r for r in manifest.get("media", []) if r.get("id")}
    trusted = trusted or {}
    services = c.load_service_catalog()
    seen = set()
    for index, s in enumerate(segments, 1):
        p = f"{label}.segments[{index}]"
        if not isinstance(s, dict) or s.get("type") not in {"media", "card"}:
            fail(c, p + ": type deve ser media ou card.")
        normalized_service_key = normalize_segment_contract(c, s, p, warnings)
        unknown = sorted(set(s) - SUPPORTED_SEGMENT_FIELDS)
        if unknown:
            preserved = s.setdefault("unsupported_requests", {})
            if not isinstance(preserved, dict):
                preserved = s["unsupported_requests"] = {"original_value": preserved}
            for key in unknown:
                preserved[key] = s.pop(key)
            warnings.append({
                "level": "warning", "block": p,
                "message": "Campos ainda não executados foram preservados: " + ", ".join(unknown) + ".",
                "effect": "O restante do segmento será aplicado; revise estes pedidos manualmente.",
            })
        s["duration_sec"] = duration = number(c, s.get("duration_sec"), p + ".duration_sec", 0.04, 3600)
        for field in ("enabled", "force_stabilization", "editorial_timelapse", "external_asset", "lower_third"):
            if field in s and not isinstance(s[field], bool):
                fail(c, f"{p}.{field}: use true ou false.")
        s.setdefault("enabled", True)
        s.setdefault("include_in", ["branded", "clean"] if s["type"] == "media" else ["branded"])
        if not isinstance(s["include_in"], list) or not s["include_in"] or any(v not in {"branded", "clean"} for v in s["include_in"]):
            fail(c, p + ".include_in: escolha branded, clean ou ambos.")
        s.setdefault("transition", "cut")
        if s["transition"] not in c.TRANSITION_MAP:
            warnings.append({"level":"warning","block":p+".transition",
                "message":f"Transição `{s['transition']}` ainda não é executada; foi substituída por corte seco.",
                "effect":"O segmento e seus tempos permanecem válidos."})
            s.setdefault("unsupported_requests", {})["transition"] = s["transition"]
            s["transition"] = "cut"
        if "transition_duration_sec" in s:
            number(c, s["transition_duration_sec"], p + ".transition_duration_sec", 0, 3)
        s["image_animation"] = "zoom_in" if s.get("image_animation") == "soft_zoom" else s.get("image_animation") or "none"
        if s["image_animation"] not in {"none", "zoom_in", "zoom_out"}:
            warnings.append({"level":"warning","block":p+".image_animation",
                "message":"Animação de imagem indisponível; foi desativada.","effect":"O restante do trecho será aplicado."})
            s.setdefault("unsupported_requests", {})["image_animation"] = s["image_animation"]
            s["image_animation"] = "none"
        if (s.get("card_animation") or "none") not in ANIMATIONS:
            warnings.append({"level":"warning","block":p+".card_animation",
                "message":"Animação de card indisponível; foi desativada.","effect":"O card continuará no plano."})
            s.setdefault("unsupported_requests", {})["card_animation"] = s.get("card_animation")
            s["card_animation"] = "none"
        if "stabilization" in s and s["stabilization"] not in {"off", "auto", "on"}:
            warnings.append({"level":"warning","block":p+".stabilization",
                "message":"Modo de estabilização indisponível; foi usado auto.","effect":"O recorte continuará válido."})
            s.setdefault("unsupported_requests", {})["stabilization"] = s["stabilization"]
            s["stabilization"] = "auto"
        for text_key in ("title", "body", "on_screen_text", "technical_note", "phase_title", "decision_reason", "cta"):
            if text_key in s and not isinstance(s[text_key], str):
                fail(c, p + "." + text_key + ": esperado texto.")
            if text_key in s:
                s[text_key] = clean_editorial_text(c, s[text_key], p + "." + text_key)
        if "narration" in s:
            s["narration"] = validate_script_block(c, s["narration"], p + ".narration")
        if "subtitles" in s:
            s["subtitles"] = validate_script_block(c, s["subtitles"], p + ".subtitles")
            if s["subtitles"]["enabled"]:
                if s.get("overlay_text"):
                    s["on_screen_text"] = s["overlay_text"]
                    warnings.append({
                        "level": "info", "block": p + ".caption_text",
                        "message": "Legenda e overlay distintos foram preservados.",
                        "effect": "Nesta versão, o render local exibe overlay_text; caption_text permanece como metadado para legendagem futura.",
                    })
                else:
                    s["on_screen_text"] = s["subtitles"]["text"]
        if "keyframes" in s:
            if not isinstance(s["keyframes"], list) or len(s["keyframes"]) > 100:
                fail(c, p + ".keyframes: use uma lista de até 100 instruções.")
            if s["keyframes"]:
                warnings.append({
                    "level": "warning", "block": p + ".keyframes",
                    "message": "Keyframes arbitrários ainda não são executados pelo renderizador.",
                    "effect": "As instruções foram preservadas; cortes, velocidade e animações suportadas continuam válidos.",
                })
        if "cut_style" in s and s["cut_style"] not in {"hard", "match", "jump", "j_cut", "l_cut"}:
            warnings.append({
                "level": "warning", "block": p + ".cut_style",
                "message": f"Estilo de corte `{s['cut_style']}` não reconhecido; será tratado como corte normal.",
                "effect": "A transição e os tempos válidos permanecem preservados.",
            })
            s["cut_style"] = "hard"
        sid = str(s.get("segment_id") or f"S{index:04d}")
        # IDs identify occurrences, not source videos. Duplicates get stable new IDs.
        if sid in seen or not re.fullmatch(r"[A-Za-z0-9_-]{1,48}", sid):
            sid = f"S{index:04d}"
        while sid in seen:
            sid += "x"
        s["segment_id"] = sid
        seen.add(sid)
        if s["type"] == "card":
            s.setdefault("card_kind", "phase")
            if s["card_kind"] not in CARD_KINDS:
                warnings.append({"level":"warning","block":p+".card_kind",
                    "message":f"Categoria `{s['card_kind']}` indisponível; o card foi preservado como phase.",
                    "effect":"Título, corpo e duração continuam válidos."})
                s.setdefault("unsupported_requests", {})["card_kind"] = s["card_kind"]
                s["card_kind"] = "phase"
            key = normalized_service_key
            if key and key not in services:
                warnings.append({"level":"warning","block":p+".service_key",
                    "message":f"Serviço `{key}` não cadastrado; o card foi mantido como comum.",
                    "effect":"Escolha uma família visual disponível na Etapa 06."})
                s.setdefault("unsupported_requests", {})["service_key"] = key
                key = ""
                s.pop("service_key", None)
            if key:
                s["service_asset"] = services[key]["asset"]
                s["service_layout"] = services[key].get("layout", "editorial")
                s["service_family"] = services[key].get("visual_family", s["service_layout"])
                s["card_mode"] = "service"
                s["service_card_enabled"] = True
            else:
                s.pop("service_asset", None)
                s.pop("service_family", None)
                s["card_mode"] = "common"
                s["service_card_enabled"] = False
            narration = s.get("narration", {})
            if narration.get("enabled"):
                s["narration_text"] = narration["text"]
            if s.get("visual"):
                s["visual"] = media_ref(c, s["visual"], manifest, p + ".visual")
            if s.get("comparison"):
                if not isinstance(s["comparison"], dict):
                    fail(c, p + ".comparison: use before e after.")
                s["comparison"] = {k: media_ref(c, s["comparison"].get(k), manifest, p + ".comparison." + k)
                                   for k in ("before", "after")}
            continue
        mid = str(s.get("media_id") or "")
        row = trusted.get(mid) if s.get("external_asset") else rows.get(mid)
        if not row or row.get("status", "ok") != "ok":
            fail(c, p + f": media_id `{mid}` não pertence às mídias disponíveis.")
        for field in ("source_path", "proxy_path", "thumbnail_path", "media_type", "has_audio"):
            s[field] = copy.deepcopy(row.get(field, False if field == "has_audio" else ""))
        service_key = normalized_service_key
        if service_key and service_key not in services:
            warnings.append({
                "level": "warning", "block": p + ".service_key",
                "message": f"Serviço `{service_key}` não existe no catálogo e foi removido deste trecho.",
                "effect": "O recorte de mídia continuará válido e poderá ser reclassificado no Studio.",
            })
            service_key = ""
            s.setdefault("unsupported_requests", {})["service_key"] = str(s.get("service_key") or "")
            s.pop("service_key", None)
        if service_key:
            s["service_family"] = services[service_key].get("visual_family", services[service_key].get("layout", "editorial"))
        card_mode = str(s.get("card_mode") or ("service" if service_key else "none"))
        if card_mode not in CARD_MODES:
            warnings.append({
                "level": "warning", "block": p + ".card_mode",
                "message": f"Modo de card `{card_mode}` indisponível; nenhum card automático será presumido.",
                "effect": "O recorte permanece no plano.",
            })
            s.setdefault("unsupported_requests", {})["card_mode"] = card_mode
            card_mode = "none"
        if card_mode == "service" and not service_key:
            warnings.append({
                "level": "warning", "block": p + ".card_mode",
                "message": "Card de serviço solicitado sem service_key.",
                "effect": "O trecho foi mantido como card comum até a classificação no Studio.",
            })
            card_mode = "common"
        s["card_mode"] = card_mode
        s["service_card_enabled"] = card_mode == "service"
        narration = s.get("narration", {})
        if narration.get("enabled"):
            warnings.append({
                "level": "warning", "block": p + ".narration",
                "message": "Locução em trecho de mídia foi validada e preservada, mas o motor local ainda não sintetiza TTS sobre vídeo.",
                "effect": "O vídeo, a legenda e os demais campos serão aplicados normalmente.",
            })
        if s.get("freeze_frame") is not None:
            if s.get("external_asset"):
                fail(c, p + ": extraia frames somente das mídias do inventário.")
            ref = dict(s["freeze_frame"]) if isinstance(s["freeze_frame"], dict) else {}
            ref["media_id"] = mid
            s["freeze_frame"] = media_ref(c, ref, manifest, p + ".freeze_frame")
            s.update(start_sec=s["freeze_frame"]["time_sec"], playback_speed=1.0, editorial_timelapse=False, has_audio=False)
            continue
        if s["media_type"] == "image":
            s.update(start_sec=0.0, playback_speed=1.0, editorial_timelapse=False)
            continue
        speed = number(c, s.get("playback_speed", 1.0), p + ".playback_speed", 0.25, 30)
        raw_start = number(c, s.get("start_sec", 0), p + ".start_sec")
        basis = s.get("start_time_basis", "absolute_parent_media")
        if basis not in {"absolute_parent_media", "scene_local"}:
            fail(c, p + ".start_time_basis: use scene_local ou absolute_parent_media.")
        window_start = float(row.get("scene_start_sec") or row.get("source_window_start_sec") or 0)
        window_end = float(row.get("scene_end_sec") or row.get("source_window_end_sec") or row.get("duration_sec") or row.get("source_duration_sec") or 0)
        window_length = max(0.0, window_end - window_start)
        span = duration * speed
        if speed > 1 and span > window_length + 0.000001:
            maximum_speed = window_length / duration if duration > 0 else 0.0
            small_rounding_overflow = (
                maximum_speed >= 1.25
                and span <= window_length + max(0.25, window_length * 0.01)
            )
            if small_rounding_overflow:
                repaired_speed = math.floor(maximum_speed * 1000.0) / 1000.0
                repairs.append({
                    "label": label, "segment": index, "media_id": mid,
                    "field": "playback_speed", "before": speed,
                    "after": repaired_speed,
                    "reason": "ajuste de arredondamento ao limite real da cena",
                })
                speed = repaired_speed
                span = duration * speed
        start = raw_start
        if basis == "scene_local":
            start += window_start
        else:
            absolute_valid = (
                start >= window_start - 0.000001
                and start + span <= window_end + 0.001
            )
            local_valid = (
                raw_start >= -0.000001
                and raw_start + span <= window_length + 0.001
            )
            if not absolute_valid and local_valid:
                start = window_start + max(0.0, raw_start)
                repairs.append({
                    "label": label, "segment": index, "media_id": mid,
                    "field": "start_sec", "before": raw_start,
                    "after": round(start, 6),
                    "reason": "tempo local da cena convertido para o vídeo-pai",
                })
            elif not absolute_valid:
                try:
                    declared_window_start = float(s.get("source_window_start_sec"))
                except (TypeError, ValueError):
                    declared_window_start = window_start
                declared_relative = raw_start - declared_window_start
                stale_window_valid = (
                    declared_relative >= -0.000001
                    and declared_relative + span <= window_length + 0.001
                )
                if stale_window_valid:
                    start = window_start + max(0.0, declared_relative)
                    repairs.append({
                        "label": label, "segment": index, "media_id": mid,
                        "field": "start_sec", "before": raw_start,
                        "after": round(start, 6),
                        "reason": "deslocamento preservado após atualização da janela de cena",
                    })
        if start < window_start - 0.000001 or start + span > window_end + 0.001:
            fail(c, f"{p}: {mid} usa {start:.3f}–{start + span:.3f}s; janela disponível {window_start:.3f}–{window_end:.3f}s. Reduza duração/velocidade ou escolha outro recorte.")
        if "end_sec" in s and abs(number(c, s["end_sec"], p + ".end_sec") - (start + span)) > 0.002:
            fail(c, p + ".end_sec difere de start_sec + duration_sec × playback_speed.")
        s.update(start_sec=round(start, 6), playback_speed=speed, editorial_timelapse=speed > 1,
                 start_time_basis="absolute_parent_media", source_window_start_sec=window_start,
                 source_window_end_sec=window_end, source_duration_sec=window_end,
                 end_sec=round(start + span, 6))
    if not any(s.get("enabled", True) and s["type"] == "media" for s in segments):
        fail(c, label + ": mantenha pelo menos um trecho de mídia ativo.")
    plan.update(contract_version=2, segments=segments, import_repairs=repairs, import_warnings=warnings,
                review_status="AI_BRIEF_APPLIED_REQUIRES_VISUAL_REVIEW")
    return plan


def validate_style(c, incoming, current):
    if not isinstance(incoming, dict):
        fail(c, "card_style: esperado objeto JSON.")
    style = c.deep_merge(c.load_card_style(), incoming)
    for role, value in style.get("palette", {}).items():
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(value)):
            fail(c, f"card_style.palette.{role}: use #RRGGBB.")
    available = {p.name for p in c.FONTS.glob("*.ttf")}
    for role, value in style.get("fonts", {}).items():
        if value not in available:
            fail(c, f"card_style.fonts.{role}: fonte não instalada.")
    for field in ("title_font", "body_font", "technical_font"):
        if style.get("persistent_overlay", {}).get(field) not in available:
            fail(c, "card_style.persistent_overlay." + field + ": fonte não instalada.")
    # Logo, textures and LUT paths come from local configuration, never the AI.
    style.setdefault("logo", {})["file"] = current.get("logo", {}).get("file", "franco-romeu-logo.png")
    style["color_lut"] = ""  # The selected LUT is supplied by the protected local setting.
    style.setdefault("cards", {})["material_backgrounds"] = copy.deepcopy(current.get("cards", {}).get("material_backgrounds", {}))
    style["cards"]["service_adaptive_layout"] = True
    for group, key, low, high in (("logo", "width_percent", 1, 30), ("logo", "opacity_percent", 0, 100),
                                ("logo", "safe_margin_percent", 1, 20)):
        number(c, style[group][key], f"card_style.{group}.{key}", low, high)
    return style


def validate_carousel(c, carousel, manifest):
    if not isinstance(carousel, dict) or not isinstance(carousel.get("enabled", False), bool):
        fail(c, "carousel: esperado objeto com enabled booleano.")
    result = copy.deepcopy(carousel)
    if not result.get("enabled"):
        return {"enabled": False, "slides": []}
    slides = result.get("slides")
    if not isinstance(slides, list) or not 1 <= len(slides) <= 40:
        fail(c, "carousel.slides: escolha explicitamente entre 1 e 40 slides; confira o limite do canal de publicação.")
    output = result.setdefault("output", {"width": 1080, "height": 1350, "format": "jpg"})
    for key in ("width", "height"):
        output[key] = int(number(c, output.get(key), "carousel.output." + key, 240, 7680))
    for index, s in enumerate(slides, 1):
        p = f"carousel.slides[{index}]"
        if not isinstance(s, dict) or s.get("kind") not in {"cover", "outro", "card", "media", "before_after"}:
            fail(c, p + ".kind: use cover, outro, card, media ou before_after.")
        s["slide"] = index
        if s["kind"] == "media":
            ref = s.get("visual") or {"media_id": s.get("media_id"), "time_sec": s.get("time_sec", 0), "time_basis": s.get("time_basis", "absolute_parent_media")}
            s["visual"] = media_ref(c, ref, manifest, p + ".visual")
        if s["kind"] == "before_after":
            s["comparison"] = {key: media_ref(c, s.get("comparison", {}).get(key), manifest, p + "." + key)
                               for key in ("before", "after")}
        key = s.get("service_key", "")
        if key and key not in c.load_service_catalog():
            fail(c, p + ".service_key: serviço não cadastrado.")
        if s.get("visual"):
            s["visual"] = media_ref(c, s["visual"], manifest, p + ".visual")
    return result


def duration(plan, version="branded"):
    selected = [s for s in plan.get("segments", []) if s.get("enabled", True) and version in s.get("include_in", ["branded", "clean"])]
    value = 0
    default = float(plan.get("visual_effects", {}).get("transition_duration_sec", .32))
    for index, s in enumerate(selected):
        d = float(s["duration_sec"])
        if index and s.get("transition", "fade") != "cut":
            requested = float(s.get("transition_duration_sec", default))
            value -= min(max(0, requested), float(selected[index-1]["duration_sec"]) * .25, d * .25)
        value += d
    return round(value, 6)


def review(c, bundle):
    notices, totals = [], {}
    all_plans = {"filme": bundle["main_timeline"], **{"reel_" + str(k): v for k, v in bundle["reels"].items()}}
    if bundle.get("stories", {}).get("timeline"):
        all_plans["stories"] = bundle["stories"]["timeline"]
    for name, p in all_plans.items():
        notices.extend(copy.deepcopy(p.get("import_warnings", [])))
        selected = [s for s in p["segments"] if s.get("enabled", True) and "branded" in s.get("include_in", [])]
        media = [s for s in selected if s["type"] == "media"]
        refs = [s["media_id"] for s in media]
        totals[name] = {"duration_sec": duration(p), "segments": len(selected), "cuts": max(0, len(selected)-1),
                        "cards": len(selected)-len(media), "media_excerpts": len(media),
                        "reused_excerpts": len(refs)-len(set(refs)), "freeze_frames": sum(bool(s.get("freeze_frame")) for s in media)}
        if selected and selected[0]["type"] == "card" and selected[0]["duration_sec"] > 2:
            notices.append({"level": "suggestion", "block": name + ".segments[1]", "message": "A abertura dedica mais de 2 s ao card. Considere mostrar primeiro o resultado ou uma ação legível.", "effect": "Hipótese editorial de retenção; teste com sua audiência."})
        if name.startswith("reel_") and abs(duration(p)-p.get("social_target_sec", duration(p))) > max(.15, 1/p["output"]["fps"]):
            notices.append({"level": "warning", "block": name, "message": f"Duração real {duration(p):.2f}s; alvo {p['social_target_sec']}s. A aplicação respeitará os cortes escolhidos.", "effect": "Ajuste duration_sec incluindo as sobreposições se precisar de duração exata."})
        for i, s in enumerate(selected, 1):
            block = f"{name}.segments[{i}]"
            text = str(s.get("body") or s.get("on_screen_text") or "")
            if len(text.split()) > float(s["duration_sec"]) * 3.0:
                notices.append({"level": "warning", "block": block, "message": "Texto denso para o tempo de tela.", "effect": "Reduza o texto ou aumente a duração; 3 palavras/s é uma heurística de revisão."})
            if s.get("playback_speed", 1) < 1:
                notices.append({"level": "info", "block": block, "message": "Câmera lenta por repetição de quadros.", "effect": "Vídeos com poucos fps podem ficar entrecortados; não há interpolação óptica automática."})
            if s.get("stabilization") == "on" or s.get("force_stabilization"):
                notices.append({"level": "info", "block": block, "message": "Estabilização local com deshake.", "effect": "Pode criar bordas espelhadas; confira linhas retas e detalhes de acabamento."})
            if s.get("type") == "media" and s.get("card_mode") == "service" and not s.get("associated_card_id"):
                notices.append({"level": "suggestion", "block": block, "message": "Trecho classificado para card de serviço sem associated_card_id.", "effect": "Associe um card existente ou transforme/crie o card na Etapa 06."})
    return {"valid": True, "totals": totals, "carousel_slides": len(bundle.get("carousel", {}).get("slides", [])),
            "notices": notices, "strategy": bundle.get("strategy", {}), "executive_summary": bundle.get("executive_summary", [])}


def prepare_bundle(env, project, payload):
    c = SimpleNamespace(**env)
    project = Path(project)
    manifest = c.read_json(project / "MANIFESTO_MEDIA.json")
    version = payload.get("schema_version", 1)
    if version not in (1, 2):
        fail(c, "schema_version incompatível. Gere um novo Markdown nesta versão do Studio.")
    supported_top = {"schema_version","application","roteiro","configuration","main_timeline","reels",
                     "carousel","stories","card_style","publication","strategy","executive_summary",
                     "media_inventory","allowed_values"}
    top_warnings = [{"level":"warning","block":key,
        "message":"Bloco ainda não executado foi ignorado nesta versão.",
        "effect":"Filme, planos e configurações reconhecidos continuam válidos."}
        for key in sorted(set(payload)-supported_top)]
    current = c.normalize_answers(c.read_json(project / "QUESTIONARIO_RESPONDIDO.json"))
    incoming = payload.get("configuration", {})
    baseline = c.read_json(c.TEMPLATES / "questionario_base.json")
    check_booleans(c, incoming, baseline)
    # Replacement from installation defaults prevents A's omitted choices leaking into B.
    config = c.normalize_answers(c.deep_merge(baseline, incoming))
    for key in PROTECTED:
        config[key] = copy.deepcopy(current.get(key, {}))
    for key in ("slug", "zip_path", "workspace_root", "context_file"):
        config["project"][key] = current["project"].get(key, "")
    for group, keys in (("edition", ("music_path",)), ("visual_effects", ("color_lut",)),
                        ("external_intro_outro", ("intro_path", "outro_path"))):
        for key in keys:
            config[group][key] = current.get(group, {}).get(key, "")
    config["cards"]["style_file"] = "CARD_STYLE.json"
    provenance = scope.identity(project, manifest)
    meta = copy.deepcopy(payload.get("roteiro") or {"id": "roteiro-legado", "name": "Roteiro importado R4", "revision": 1, **provenance})
    if version == 2 and any(meta.get(k) != v for k, v in provenance.items()):
        fail(c, "roteiro: projeto ou inventário diferente do Markdown recebido. Gere outro Roteiro Mestre com as mídias atuais.")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", str(meta.get("id", ""))):
        fail(c, "roteiro.id: use 1–64 letras minúsculas, números, hífen ou sublinhado.")
    number(c, meta.get("revision", 1), "roteiro.revision", 1, 100000)
    style = validate_style(c, payload.get("card_style", c.load_card_style() if version == 2 else c.load_card_style(project)), c.load_card_style(project))
    style["color_lut"] = config["visual_effects"].get("color_lut", "")
    # Keep controls in sync with the authoritative imported visual choices.
    cards = config["cards"]
    cards["palette_overrides"] = copy.deepcopy(style["palette"])
    cards["persistent_logo"] = style["logo"].get("persistent_on_branded_video", True)
    cards["persistent_bubble"] = style["persistent_overlay"].get("enabled", True)
    cards["show_contacts"] = style["cards"].get("show_contacts_on_every_card", True)
    for field in ("layout", "animation", "intro_animation", "outro_animation", "service_animation",
                  "bubble_style", "show_site", "show_pinterest", "show_contact_icons", "qr_code_on_outro", "qr_code_target"):
        if field in style["cards"]:
            cards[field] = style["cards"][field]
    publication = copy.deepcopy(payload.get("publication", {}))
    if not isinstance(publication, dict) or not isinstance(publication.get("hashtags", []), list):
        fail(c, "publication: use objeto; hashtags deve ser uma lista de textos.")
    for key in ("video_title", "caption", "complementary_information", "social_caption_suggestion"):
        if key in publication:
            publication[key] = clean_editorial_text(c, publication[key], "publication." + key)
    if any(not isinstance(item, str) for item in publication.get("hashtags", [])):
        fail(c, "publication.hashtags: use somente textos.")
    typography = publication.get("overlay_typography", {})
    for key, target in (("title_font", "overlay_title_font"), ("body_font", "overlay_body_font"), ("technical_font", "overlay_technical_font")):
        chosen = typography.get(key, config.get("editing_brief", {}).get(target))
        if chosen not in {p.name for p in c.FONTS.glob("*.ttf")}:
            fail(c, "publication.overlay_typography." + key + ": fonte não instalada.")
        config["editing_brief"][target] = chosen
        style["persistent_overlay"][key] = chosen
    config["editing_brief"].update(publication_title=publication.get("video_title", ""),
        publication_caption=publication.get("caption", ""), hashtags=publication.get("hashtags", []),
        complementary_information=publication.get("complementary_information", ""),
        scenario_name=meta.get("name", meta["id"]))
    current_plan = scope.read(project / "EDIT_PLAN.json", {})
    trusted = {s["media_id"]: s for s in current_plan.get("segments", []) if s.get("external_asset")}
    width, height = c.resolve_output_dimensions(config["edition"], manifest.get("media", []))
    edition = config["edition"]
    common = {"project": config["project"], "context": config.get("context", {}),
        "audio": {"preserve_original": edition.get("preserve_original_audio", True),
                  "music_path": edition.get("music_path", ""), "music_volume": edition.get("music_volume", .1), **config["audio_design"]},
        "visual_effects": config["visual_effects"], "export_quality": config["export_quality"],
        "social": config["social"], "order_mode": edition["order_mode"], "roteiro": meta}
    # Global hidden speed ramps may consume source outside selected boundaries.
    common["visual_effects"]["speed_ramping"] = False
    def complete(plan, label, target=None):
        p = validate_plan(c, plan, manifest, label, trusted, legacy=version == 1)
        p.update(copy.deepcopy(common))
        p["output"] = {"width": width, "height": height, "fps": edition["fps"], "render_source": edition["render_source"]}
        p["versions"] = {"branded": edition.get("create_branded_version", True), "clean": edition.get("create_clean_version", True)}
        if target is not None:
            p["output"] = c.social_output_settings(p["output"], target)
            p["social_target_sec"] = target
            p["versions"] = {"branded": True, "clean": False}
        for name, on in p["versions"].items():
            if on and not any(s.get("enabled", True) and name in s["include_in"] for s in p["segments"]):
                fail(c, label + ": a versão " + name + " está ativa, mas não possui segmentos.")
        return p
    main = complete(payload.get("main_timeline"), "filme principal")
    reels = payload.get("reels", {})
    if not isinstance(reels, dict):
        fail(c, "reels: esperado objeto de planos indexados pela duração.")
    validated_reels = {}
    for key, p in reels.items():
        if not re.fullmatch(r"\d+", str(key)):
            fail(c, "reels: chaves devem ser durações inteiras em segundos.")
        target = int(number(c, int(key), "reels." + key, 5, 600))
        validated_reels[str(target)] = complete(p, "Reel " + key + "s", target)
    carousel = validate_carousel(c, payload.get("carousel", {"enabled": False, "slides": []}), manifest)
    stories = copy.deepcopy(payload.get("stories", {"enabled": False}))
    if not isinstance(stories, dict) or not isinstance(stories.get("enabled", False), bool):
        fail(c, "stories.enabled: esperado booleano.")
    if stories.get("enabled"):
        stories["part_duration_sec"] = int(number(c, stories.get("part_duration_sec", 15), "stories.part_duration_sec", 5, 120))
        if stories.get("timeline"):
            stories["timeline"] = complete(stories["timeline"], "Stories", 60)
            stories["timeline"]["output"]["delivery_label"] = "STORIES"
        elif str(stories.get("source_reel_sec")) not in validated_reels:
            fail(c, "stories.source_reel_sec: escolha um Reel presente no contrato ou forneça stories.timeline.")
    config["social"].update(enabled=bool(validated_reels or carousel["enabled"] or stories.get("enabled")),
        reels_enabled=bool(validated_reels), reel_durations_sec=[int(k) for k in validated_reels],
        carousel_enabled=carousel["enabled"], carousel_slides=len(carousel.get("slides", [])),
        stories_enabled=stories.get("enabled", False), story_part_duration_sec=stories.get("part_duration_sec", 15),
        story_source_duration_sec=stories.get("source_reel_sec", 60))
    strategy = validate_strategy(c, payload.get("strategy", {}))
    executive = payload.get("executive_summary", [])
    if not isinstance(executive, list):
        fail(c, "executive_summary deve ser lista de decisões.")
    result = {"schema_version": 2, "roteiro": meta, "configuration": config, "card_style": style,
              "main_timeline": main, "reels": validated_reels, "carousel": carousel,
              "stories": stories, "publication": publication, "strategy": strategy, "executive_summary": executive}
    result["review"] = review(c, result)
    result["review"]["notices"] = top_warnings + result["review"]["notices"]
    if any(strategy.get(key) for key in ("retention", "ethical_marketing_growth", "ethical_neuromarketing", "final_copy")):
        result["review"]["notices"].append({
            "level": "info", "block": "strategy",
            "message": "Estratégia, growth e neuromarketing ético foram aceitos como metadados editoriais.",
            "effect": "O render executa apenas os campos de timeline suportados; o restante permanece em ESTRATEGIA_IA.json para revisão humana.",
        })
    return result


def inspect_file(env, project, path):
    c = SimpleNamespace(**env)
    return prepare_bundle(env, project, c.parse_ai_editing_brief(Path(path)))


def apply_file(env, project, path):
    c = SimpleNamespace(**env)
    project, path = Path(project), Path(path)
    with scope.project_lock(project):
        bundle = inspect_file(env, project, path)
        report = bundle["review"]
        source_sha256 = __import__("hashlib").sha256(path.read_bytes()).hexdigest()
        active = scope.read(project / "_CONTROLE/ROTEIRO_ATIVO.json", {})
        if active.get("source_sha256") == source_sha256:
            report = copy.deepcopy(bundle["review"])
            report.update(status="already_applied_no_changes", roteiro=active)
            report.setdefault("notices", []).append({
                "level": "info", "block": "roteiro",
                "message": "Esta resposta da IA já foi aplicada anteriormente.",
                "effect": "Nenhum arquivo foi sobrescrito e nenhum anexo duplicado foi criado.",
            })
            return report
        before = scope.snapshot_decisions(project, "antes-da-ia")
        meta = bundle["roteiro"] | {"applied_at": scope.timestamp(), "source_sha256": source_sha256}
        config = bundle["configuration"]
        files = {"QUESTIONARIO_RESPONDIDO.json": config, "_EDITAR/01_CONFIGURACOES_DO_PROJETO.json": config,
                 "EDIT_PLAN.json": bundle["main_timeline"], "_EDITAR/02_PLANO_DA_EDICAO.json": bundle["main_timeline"],
                 "CARD_STYLE.json": bundle["card_style"], "PUBLICACAO_SOCIAL.json": bundle["publication"],
                 "ESTRATEGIA_IA.json": bundle["strategy"], "_CONTROLE/ROTEIRO_ATIVO.json": meta,
                 "social/planos/CARROSSEL_PLAN.json": bundle["carousel"], "social/planos/STORIES_PLAN.json": bundle["stories"],
                 "SOCIAL_PLAN.json": {"enabled": config["social"]["enabled"], "contract_version": 2,
                                     "reel_plans": [f"social/planos/REEL_{key}S.json" for key in bundle["reels"]]},
                 "_ENTRADA/ROTEIRO_MESTRE_RESPONDIDO.md": path.read_bytes(),
                 "PACOTE_PARA_IA/05_RESPOSTA_DA_IA_IMPORTAR_AQUI.md": path.read_bytes()}
        for key, plan in bundle["reels"].items():
            files[f"social/planos/REEL_{key}S.json"] = plan
        deletes = [p.relative_to(project).as_posix() for p in (project / "social/planos").glob("REEL_*S.json")
                   if p.relative_to(project).as_posix() not in files]
        # O roteiro-base continua imutável; a resposta recebida tem arquivo próprio.
        pub = bundle["publication"]
        files["PUBLICACAO_SOCIAL.md"] = "# Publicação sugerida\n\n" + str(pub.get("video_title", "")) + "\n\n" + str(pub.get("caption", "")) + "\n\n" + " ".join(map(str, pub.get("hashtags", []))) + "\n"
        summary = executive_markdown(bundle)
        files["RESUMO_EXECUTIVO_IA.md"] = summary
        report.update(application=f"FR AutoEdite {c.APP_VERSION}", backup=str(before), status="applied_requires_visual_review",
                      main_segments=len(bundle["main_timeline"]["segments"]), reels=[int(k) for k in bundle["reels"]],
                      automatic_repairs=bundle["main_timeline"].get("import_repairs", []), roteiro=meta)
        report["automatic_repairs_count"] = len(report["automatic_repairs"])
        files["RELATORIO_APLICACAO_ROTEIRO_IA.json"] = report
        files["_CONTROLE/REVISAO_ROTEIRO.json"] = report
        scope.publish_files(project, files, delete=deletes)
        saved = scope.snapshot_decisions(project, meta["id"], roteiro=meta)
        c.info(f"Roteiro validado e aplicado: {meta['id']} · cópia independente {saved.name}")
        return report


def executive_markdown(bundle):
    lines = ["# Resumo Executivo da IA", "", "Roteiro: " + bundle["roteiro"]["id"], "",
             "| Saída | Duração estimada | Cortes | Cards | Frames fixos |", "|---|---:|---:|---:|---:|"]
    for name, data in bundle["review"]["totals"].items():
        lines.append(f"| {name} | {data['duration_sec']:.3f}s | {data['cuts']} | {data['cards']} | {data['freeze_frames']} |")
    lines += ["", f"Carrossel: {bundle['review']['carousel_slides']} slides.", "", "## Decisões", ""]
    for item in bundle.get("executive_summary", []):
        lines.append("- " + (item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)))
    lines += ["", "## Revisão contextual", ""]
    for item in bundle["review"]["notices"]:
        lines.append(f"- **{item['block']}** — {item['message']} {item['effect']}")
    return "\n".join(lines) + "\n"


def generate(env, project, answers=None, plan=None, manifest=None):
    c = SimpleNamespace(**env)
    project = Path(project)
    with scope.project_lock(project):
        answers = c.normalize_answers(answers or c.read_json(project / "QUESTIONARIO_RESPONDIDO.json"))
        manifest = manifest or c.read_json(project / "MANIFESTO_MEDIA.json")
        plan = copy.deepcopy(plan or scope.read(project / "EDIT_PLAN.json"))
        if not plan:
            if not answers.get("story", {}).get("chronology"):
                answers.setdefault("story", {})["chronology"] = [{"order": 1, "title": "MÍDIAS DO PROJETO",
                    "description": "Registros disponíveis para curadoria da IA.", "keywords": []}]
            plan = c.build_auto_plan(project, answers, manifest)
            scope.write(project / "EDIT_PLAN.json", plan)
        active = scope.read(project / "_CONTROLE/ROTEIRO_ATIVO.json", {})
        name = str(answers.get("editing_brief", {}).get("scenario_name") or active.get("name") or "roteiro-principal")
        meta = {"id": c.slugify(name)[:64], "name": name, "revision": int(active.get("revision", 0)) + 1,
                **scope.identity(project, manifest)}
        plans = project / "social/planos"
        reels = {str(int(c.read_json(p).get("social_target_sec", 0))): c.read_json(p) for p in sorted(plans.glob("REEL_*S.json"))}
        social = answers.get("social", {})
        if not reels and social.get("reels_enabled"):
            reels = {str(t): c.build_reel_plan(plan, int(t)) for t in social.get("reel_durations_sec", [30, 60, 90])}
        carousel = scope.read(plans / "CARROSSEL_PLAN.json") or c.build_carousel_plan(project, answers, plan, manifest)
        carousel["enabled"] = social.get("carousel_enabled", True)
        for slide in carousel.get("slides", []):
            if slide.get("kind") == "media" and not slide.get("visual"):
                row = next((x for x in manifest.get("media", []) if x.get("id") == slide.get("media_id")), {})
                slide["visual"] = {"media_id": row.get("id"), "time_sec": float(row.get("scene_start_sec") or 0), "time_basis": "absolute_parent_media"}
        for p in [plan, *reels.values()]:
            p["contract_version"] = 2
            for s in p.get("segments", []):
                s["start_time_basis"] = "absolute_parent_media"
                s.setdefault("stabilization", "auto")
                s.setdefault("decision_reason", "")
                s.setdefault("cut_style", "hard")
                s.setdefault("keyframes", [])
                s.setdefault("narration", {"enabled": False, "text": ""})
                s.setdefault("subtitles", {"enabled": False, "text": ""})
                s.setdefault("cta", "")
                service_id = str(s.get("service_key") or "")
                profile = c.load_service_catalog().get(service_id, {})
                s.setdefault("service_id", service_id)
                s.setdefault("service_name", profile.get("label", ""))
                s.setdefault("service_confidence", 0.0)
                s.setdefault("card_family", profile.get("visual_family", ""))
                s.setdefault("balloon_family", profile.get("balloon_family", ""))
                s.setdefault("visual_motif", profile.get("visual_motif", ""))
                s.setdefault("overlay_text", str(s.get("on_screen_text") or ""))
                s.setdefault("voiceover_text", str(s.get("narration", {}).get("text") or ""))
                s.setdefault("caption_text", str(s.get("subtitles", {}).get("text") or ""))
                s.setdefault("transition_in", str(s.get("transition") or "cut"))
                s.setdefault("transition_out", "")
                s.setdefault("balloon_texts", [])
                if s.get("type") == "card":
                    s.setdefault("card_mode", "service" if s.get("service_key") else "common")
                    s.setdefault("card_type", str(s.get("card_kind") or "phase"))
                    s.setdefault("service_card_enabled", s.get("card_mode") == "service")
                else:
                    s.setdefault("service_key", "")
                    s.setdefault("service_family", "")
                    s.setdefault("card_mode", "none")
                    s.setdefault("card_type", s.get("card_mode"))
                    s.setdefault("service_card_enabled", s.get("card_mode") == "service")
                    s.setdefault("associated_card_id", "")
                    s.setdefault("playback_speed", 1.0)
                    s["end_sec"] = round(
                        float(s.get("start_sec") or 0)
                        + float(s.get("duration_sec") or 0) * float(s.get("playback_speed") or 1), 6,
                    )
        safe_config = copy.deepcopy(answers)
        for field in ("ai_copilot", "cloud_export"):
            safe_config.pop(field, None)
        style = c.load_card_style(project)
        default_story = str(social.get("story_source_duration_sec", 60))
        if default_story not in reels:
            default_story = next(iter(reels), "60")
        publication = scope.read(project / "PUBLICACAO_SOCIAL.json", {})
        publication.setdefault("video_title", "")
        publication.setdefault("caption", "")
        publication.setdefault("hashtags", [])
        publication.setdefault("overlay_typography", {"title_font": "StardosStencil-Bold.ttf", "body_font": "Rokkitt-Regular.ttf", "technical_font": "ShareTechMono-Regular.ttf"})
        payload = {"schema_version": 2, "application": f"FR AutoEdite {c.APP_VERSION}", "roteiro": meta,
            "configuration": safe_config, "main_timeline": plan, "reels": reels,
            "carousel": carousel, "stories": scope.read(plans / "STORIES_PLAN.json", {"enabled": bool(social.get("stories_enabled") and reels), "source_reel_sec": int(default_story), "part_duration_sec": social.get("story_part_duration_sec", 15)}),
            "card_style": style, "publication": publication,
            "strategy": {
                "service_key": answers.get("service_intro", {}).get("service_key", ""),
                "editorial": {
                    "video_objective": "", "target_audience": "", "platform": "",
                    "funnel_stage": "", "primary_intent": "",
                    "narrative_arc": {"hook": "", "development": "", "proof_process": "", "climax": "", "cta": ""},
                },
                "retention": {
                    "hook_0_3_sec": "", "first_strong_image": "", "visual_promise": "",
                    "implicit_question": "", "pattern_breaks": [], "partial_reveals": [],
                    "best_moments": [], "acceleration_timelapse": [], "selective_slow_motion": [],
                    "fade_to_black": [], "chapter_transitions": [], "visual_climax": "", "final_cta": "",
                },
                "ethical_marketing_growth": {
                    "primary_cta": "", "secondary_cta": "",
                    "funnel_cta": {"awareness": "", "consideration": "", "conversion": "", "relacionamento": ""},
                    "social_caption_suggestion": "", "save_prompt": "", "comment_prompt": "",
                    "quote_request_prompt": "", "profile_site_whatsapp_prompt": "",
                    "hook_ab_variations": [], "cta_ab_variations": [], "lead_objective": "",
                },
                "ethical_neuromarketing": {
                    "curiosity": "", "before_after_contrast": "", "process_based_authority": "",
                    "material_proof": "", "visual_clarity": "", "identity_repetition": "",
                    "real_revelation_reward": "", "primacy_recency": "", "figure_ground": "",
                    "proximity": "", "similarity": "", "visual_hierarchy": "", "motion_attention": "",
                },
                "brand_franco_romeu": {
                    "brand": "Franco Romeu", "signature": "Arte & Engenharia", "scope": "projetos e reformas",
                    "principles": ["verdade material", "método", "autoria", "resistência", "execução controlada"],
                    "positioning": "luxo conceitual e alto padrão sem exagero artificial",
                    "palette": {"predominant": "verde-petróleo", "accent": "laranja", "support": ["ouro", "osso"]},
                    "logo_rule": "fixa, simétrica e sem deformação", "typography_rule": "tipografia FR quando aplicável",
                },
                "final_copy": {"voiceover_final": "", "caption_final": "", "card_texts": [], "balloon_texts": [], "cta_final": ""},
                "evidence": [], "facts_to_confirm": [], "attention_beats": [], "narrative_order": [],
                "rhythm": "", "aesthetic": "", "ihc_notes": [], "growth_hypothesis": "",
                "keywords": [], "ab_test": {"variable": "", "hypothesis": "", "primary_metric": "", "guardrail": ""},
            },
            "executive_summary": [], "media_inventory": c._brief_media_inventory(manifest),
            "allowed_values": {"transitions": sorted(c.TRANSITION_MAP), "card_kinds": sorted(CARD_KINDS), "card_modes": sorted(CARD_MODES), "card_animations": sorted(ANIMATIONS),
                "service_profiles": c.load_service_catalog(), "fonts": sorted(p.name for p in c.FONTS.glob("*.ttf")),
                "playback_speed": [0.25, 30], "time_basis": ["absolute_parent_media", "scene_local"],
                "cut_styles": ["hard", "match", "jump", "j_cut", "l_cut"],
                "funnel_stages": ["awareness", "consideration", "conversion", "relacionamento"],
                "primary_intents": ["educar", "inspirar", "provar_tecnica", "vender", "gerar_lead",
                    "fortalecer_marca", "mostrar_bastidor", "mostrar_antes_depois"],
                "service_aliases": SERVICE_ALIASES,
                "unknown_fact_placeholder": "[DADO A CONFIRMAR]",
                "script_block": {"enabled": True, "text": "Texto final limpo, sem comentários da IA"}}}
        context_path = project / "_ENTRADA/CONTEXTO_PROJETO.md"
        context = context_path.read_text(encoding="utf-8") if context_path.is_file() else ""
        prompt = (c.TEMPLATES / "ROTEIRO_MESTRE_PROMPT.md").read_text(encoding="utf-8")
        document = "# ROTEIRO MESTRE 1 — " + str(answers["project"]["name"]) + "\n\n" + prompt
        document += "\n\n## Contexto informado pelo usuário\n\n" + context
        document += "\n\n## Contrato editável\n\n<!-- ROTEIRO: " + meta["id"] + " -->\n" + c.AI_BRIEF_JSON_BEGIN + "\n```json\n"
        document += json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n```\n" + c.AI_BRIEF_JSON_END + "\n"
        document += "\n## Resumo Executivo da IA\n\nA IA deve preencher executive_summary no JSON e resumir aqui as decisões finais. O JSON é a fonte executável.\n"
        for p in c.editing_brief_paths(project):
            c.write_text(p, document)
        c.refresh_ai_package_documents(project, answers, manifest, document)
        c.info("Markdown completo gerado: " + str(c.editing_brief_paths(project)[1]))
        return c.editing_brief_paths(project)[1]
