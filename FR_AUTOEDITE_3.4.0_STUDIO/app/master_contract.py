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
            fail(c, p + ".transition: transição desconhecida.")
        if "transition_duration_sec" in s:
            number(c, s["transition_duration_sec"], p + ".transition_duration_sec", 0, 3)
        s["image_animation"] = "zoom_in" if s.get("image_animation") == "soft_zoom" else s.get("image_animation") or "none"
        if s["image_animation"] not in {"none", "zoom_in", "zoom_out"}:
            fail(c, p + ".image_animation: use none, zoom_in ou zoom_out.")
        if (s.get("card_animation") or "none") not in ANIMATIONS:
            fail(c, p + ".card_animation: animação indisponível.")
        if "stabilization" in s and s["stabilization"] not in {"off", "auto", "on"}:
            fail(c, p + ".stabilization: use off, auto ou on.")
        for text_key in ("title", "body", "on_screen_text", "technical_note", "phase_title", "decision_reason"):
            if text_key in s and not isinstance(s[text_key], str):
                fail(c, p + "." + text_key + ": esperado texto.")
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
                fail(c, p + ".card_kind: categoria de card desconhecida.")
            key = str(s.get("service_key") or "")
            if key and key not in services:
                fail(c, p + ".service_key: serviço não cadastrado.")
            if key:
                s["service_asset"] = services[key]["asset"]
                s["service_layout"] = services[key].get("layout", "editorial")
            else:
                s.pop("service_asset", None)
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
    plan.update(contract_version=2, segments=segments, import_repairs=repairs,
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
    return {"valid": True, "totals": totals, "carousel_slides": len(bundle.get("carousel", {}).get("slides", [])),
            "notices": notices, "strategy": bundle.get("strategy", {}), "executive_summary": bundle.get("executive_summary", [])}


def prepare_bundle(env, project, payload):
    c = SimpleNamespace(**env)
    project = Path(project)
    manifest = c.read_json(project / "MANIFESTO_MEDIA.json")
    version = payload.get("schema_version", 1)
    if version not in (1, 2):
        fail(c, "schema_version incompatível. Gere um novo Markdown nesta versão do Studio.")
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
    strategy = payload.get("strategy", {})
    executive = payload.get("executive_summary", [])
    if not isinstance(strategy, dict) or not isinstance(executive, list):
        fail(c, "strategy deve ser objeto; executive_summary deve ser lista de decisões.")
    result = {"schema_version": 2, "roteiro": meta, "configuration": config, "card_style": style,
              "main_timeline": main, "reels": validated_reels, "carousel": carousel,
              "stories": stories, "publication": publication, "strategy": strategy, "executive_summary": executive}
    result["review"] = review(c, result)
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
        before = scope.snapshot_decisions(project, "antes-da-ia")
        meta = bundle["roteiro"] | {"applied_at": scope.timestamp()}
        config = bundle["configuration"]
        files = {"QUESTIONARIO_RESPONDIDO.json": config, "_EDITAR/01_CONFIGURACOES_DO_PROJETO.json": config,
                 "EDIT_PLAN.json": bundle["main_timeline"], "_EDITAR/02_PLANO_DA_EDICAO.json": bundle["main_timeline"],
                 "CARD_STYLE.json": bundle["card_style"], "PUBLICACAO_SOCIAL.json": bundle["publication"],
                 "ESTRATEGIA_IA.json": bundle["strategy"], "_CONTROLE/ROTEIRO_ATIVO.json": meta,
                 "social/planos/CARROSSEL_PLAN.json": bundle["carousel"], "social/planos/STORIES_PLAN.json": bundle["stories"],
                 "SOCIAL_PLAN.json": {"enabled": config["social"]["enabled"], "contract_version": 2,
                                     "reel_plans": [f"social/planos/REEL_{key}S.json" for key in bundle["reels"]]},
                 "_ENTRADA/ROTEIRO_MESTRE_RESPONDIDO.md": path.read_bytes()}
        for key, plan in bundle["reels"].items():
            files[f"social/planos/REEL_{key}S.json"] = plan
        deletes = [p.relative_to(project).as_posix() for p in (project / "social/planos").glob("REEL_*S.json")
                   if p.relative_to(project).as_posix() not in files]
        for target in c.editing_brief_paths(project):
            files[target.relative_to(project).as_posix()] = path.read_bytes()
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
            "strategy": {"service_key": answers.get("service_intro", {}).get("service_key", ""), "audience": "",
                "objective": "", "hook": "", "promise_and_payoff": "", "evidence": [], "facts_to_confirm": [],
                "attention_beats": [], "cta": "", "keywords": [], "ab_test": {"variable": "gancho", "hypothesis": "", "primary_metric": "retenção inicial", "guardrail": "contatos qualificados"}},
            "executive_summary": [], "media_inventory": c._brief_media_inventory(manifest),
            "allowed_values": {"transitions": sorted(c.TRANSITION_MAP), "card_kinds": sorted(CARD_KINDS), "card_animations": sorted(ANIMATIONS),
                "service_profiles": c.load_service_catalog(), "fonts": sorted(p.name for p in c.FONTS.glob("*.ttf")),
                "playback_speed": [0.25, 30], "time_basis": ["absolute_parent_media", "scene_local"]}}
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
        c.info("Markdown completo gerado: " + str(c.editing_brief_paths(project)[1]))
        return c.editing_brief_paths(project)[1]
