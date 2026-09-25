"""Fluxo não destrutivo para vídeos já editados.

O vídeo-base nunca é remontado: o render final preserva sua timeline e aplica
somente camadas temporizadas. FFmpeg é obrigatório; MoviePy é um compositor
opcional para prévias curtas e nunca é importado durante o boot do Studio.
"""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
from typing import Any

import project_scope
from local_analysis import choose_preview_backend, ready_video_reference_times
from style_engine import DEFAULT_STYLE_PACK_ID, resolve_asset, style_pack_signature


BASE_VIDEO_ID = "READY_VIDEO_BASE"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path, project: Path) -> str:
    return path.resolve().relative_to(project.resolve()).as_posix()


def prepare(env: dict[str, Any], source: Path, project: Path, answers: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Copia, cataloga e cria referências sem escrever no vídeo recebido."""
    c = SimpleNamespace(**env)
    source = Path(source).expanduser().resolve()
    project = Path(project).expanduser().resolve()
    if not source.is_file() or source.suffix.lower() not in c.VIDEO_EXTENSIONS:
        raise c.AutoEditeError("Vídeo pronto ausente ou em formato não suportado.")
    c.check_runtime()
    before_hash = _sha256(source)
    answers = c.normalize_answers(answers)
    input_config = answers.setdefault("input", {})
    input_config.update({
        "mode": "ready_video",
        "base_video_id": BASE_VIDEO_ID,
        "timeline_locked": True,
        "style_pack_id": str(input_config.get("style_pack_id") or DEFAULT_STYLE_PACK_ID),
    })
    project.mkdir(parents=True, exist_ok=True)
    for folder in ("_ENTRADA", "_EDITAR", "_ENVIAR_IA", "_ENVIAR_CHATGPT", "_HISTORICO", "proxies", "miniaturas/ready_video"):
        (project / folder).mkdir(parents=True, exist_ok=True)

    with project_scope.project_lock(project):
        target = project / "_ENTRADA" / f"VIDEO_PRONTO_ORIGINAL{source.suffix.lower()}"
        existing = sorted((project / "_ENTRADA").glob("VIDEO_PRONTO_ORIGINAL.*"))
        same_target = source == target
        if same_target:
            if _sha256(target) != before_hash:
                raise c.AutoEditeError("O vídeo-base mudou durante a preparação.")
        elif target.is_file() and _sha256(target) == before_hash:
            pass
        else:
            stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            for old in existing:
                if old.is_file() and _sha256(old) != before_hash:
                    old.replace(project / "_HISTORICO" / f"VIDEO_PRONTO_ORIGINAL_{stamp}{old.suffix.lower()}")
            temporary = target.with_name(f".{target.name}.recebendo")
            temporary.unlink(missing_ok=True)
            try:
                shutil.copy2(source, temporary)
                if _sha256(temporary) != before_hash:
                    raise c.AutoEditeError("A cópia do vídeo pronto não passou na conferência SHA-256.")
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)

        if _sha256(source) != before_hash:
            raise c.AutoEditeError("O arquivo original mudou durante a preparação; operação interrompida.")
        probe_data = c.ffprobe(target)
        parsed = c.parse_probe(target, probe_data)
        if parsed.get("probe_error") or not parsed.get("width") or float(parsed.get("duration_sec") or 0) <= 0:
            raise c.AutoEditeError("FFprobe não reconheceu um vídeo-base íntegro.")
        duration = float(parsed["duration_sec"])
        taken_at, date_source = c.capture_time(target, probe_data)
        proxy = project / "proxies" / "READY_VIDEO_BASE_PROXY.mp4"
        c.create_video_proxy(
            target, proxy,
            int(answers.get("handoff", {}).get("proxy_long_side", 720)),
            int(answers.get("handoff", {}).get("proxy_fps", 24)),
            source_duration=duration,
        )
        main_thumb = project / "miniaturas" / "READY_VIDEO_BASE.jpg"
        c.create_thumbnail(proxy, main_thumb, "video", duration)
        reference_times = ready_video_reference_times(proxy, duration)
        references: list[dict[str, Any]] = []
        for index, seek in enumerate(reference_times, 1):
            thumb = project / "miniaturas" / "ready_video" / f"REF_{index:03d}_{int(seek * 1000):09d}.jpg"
            c.create_thumbnail_at(proxy, thumb, seek)
            references.append({"id": f"READY_REF_{index:03d}", "time_sec": seek, "thumbnail_path": _relative(thumb, project)})
        row = {
            "id": BASE_VIDEO_ID,
            "chronological_index": 1,
            "alphabetical_index": 1,
            "status": "ok",
            "error": "",
            "media_type": "video",
            "filename": target.name,
            "source_path": _relative(target, project),
            "relative_album_path": "_ENTRADA",
            "extension": target.suffix.lower(),
            "proxy_path": _relative(proxy, project),
            "thumbnail_path": _relative(main_thumb, project),
            "capture_time": taken_at,
            "capture_time_source": date_source,
            "duration_sec": duration,
            "width": int(parsed["width"]),
            "height": int(parsed["height"]),
            "fps": float(parsed.get("fps") or 0),
            "has_audio": bool(parsed.get("has_audio")),
            "audio_codec": str(parsed.get("audio_codec") or ""),
            "video_codec": str(parsed.get("video_codec") or ""),
            "sha256": before_hash,
            "size_bytes": target.stat().st_size,
            "input_mode": "ready_video",
            "timeline_locked": True,
            "visual_references": references,
        }
        manifest = {
            "schema_version": 2,
            "generated_at": c.now_iso(),
            "input_mode": "ready_video",
            "base_video_id": BASE_VIDEO_ID,
            "media": [row],
            "visual_references": references,
        }
        output = {"width": int(parsed["width"]), "height": int(parsed["height"]), "fps": float(parsed.get("fps") or 24)}
        plan = {
            "contract_version": 2,
            "input_mode": "ready_video",
            "base_video_id": BASE_VIDEO_ID,
            "timeline_locked": True,
            "allow_duration_extension": bool(input_config.get("allow_duration_extension", False)),
            "style_pack_id": input_config["style_pack_id"],
            "audio_policy": "preserve",
            "overlays": [],
            "segments": [{
                "segment_id": "RV0001", "type": "media", "enabled": True,
                "include_in": ["branded", "clean"], "media_id": BASE_VIDEO_ID,
                "media_type": "video", "source_path": row["source_path"], "proxy_path": row["proxy_path"],
                "thumbnail_path": row["thumbnail_path"], "has_audio": row["has_audio"],
                "start_sec": 0.0, "end_sec": duration, "duration_sec": duration,
                "source_duration_sec": duration, "playback_speed": 1.0,
                "transition": "cut", "start_time_basis": "absolute_parent_media",
            }],
            "output": output,
            "versions": {"branded": True, "clean": False},
            "project": copy.deepcopy(answers.get("project", {})),
        }
        c.write_json(project / "QUESTIONARIO_RESPONDIDO.json", answers)
        c.write_json(project / "MANIFESTO_MEDIA.json", manifest)
        c.write_json(project / "EDIT_PLAN.json", plan)
        c.write_json(project / "READY_VIDEO_PLAN.json", {
            key: copy.deepcopy(plan[key]) for key in (
                "input_mode", "base_video_id", "timeline_locked", "allow_duration_extension",
                "style_pack_id", "audio_policy", "overlays",
            )
        })
        c.write_json(project / "FR_AUTOEDITE_PROJECT.json", {
            "application_version": c.APP_VERSION, "created_or_updated_at": c.now_iso(),
            "input_mode": "ready_video", "base_video_sha256": before_hash,
            "project_dir": str(project),
        })
        return manifest, plan


def _apply_opacity(image: Any, opacity: float) -> Any:
    alpha = image.getchannel("A")
    alpha = alpha.point(lambda value: round(value * max(0.0, min(1.0, opacity))))
    image.putalpha(alpha)
    return image


def _place_layer(canvas: Any, layer: Any, position: str, margin: int) -> None:
    positions = {
        "top_left": (margin, margin),
        "top_center": ((canvas.width - layer.width) // 2, margin),
        "top_right": (canvas.width - layer.width - margin, margin),
        "center": ((canvas.width - layer.width) // 2, (canvas.height - layer.height) // 2),
        "bottom_left": (margin, canvas.height - layer.height - margin),
        "bottom_center": ((canvas.width - layer.width) // 2, canvas.height - layer.height - margin),
        "bottom_right": (canvas.width - layer.width - margin, canvas.height - layer.height - margin),
    }
    canvas.alpha_composite(layer, positions.get(position, positions["bottom_left"]))


def _safe_margin(overlay: dict[str, Any], width: int, height: int) -> int:
    safe = overlay.get("safe_area", "auto")
    if isinstance(safe, dict):
        horizontal = max(float(safe.get("left", 0)), float(safe.get("right", 0))) * width
        vertical = max(float(safe.get("top", 0)), float(safe.get("bottom", 0))) * height
        return max(0, round(max(horizontal, vertical)))
    return {
        "none": 0,
        "action_safe": round(min(width, height) * 0.05),
        "title_safe": round(min(width, height) * 0.10),
        "auto": round(min(width, height) * 0.07),
    }.get(str(safe), round(min(width, height) * 0.07))


def overlay_image(
    env: dict[str, Any], project: Path, overlay: dict[str, Any], width: int, height: int,
    style: dict[str, Any], style_pack_id: str, target: Path,
) -> Path:
    """Rasteriza uma camada executável transparente no quadro do vídeo-base."""
    c = SimpleNamespace(**env)
    from PIL import Image, ImageDraw

    target.parent.mkdir(parents=True, exist_ok=True)
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    opacity = float(overlay.get("opacity", 1.0))
    safe_margin = _safe_margin(overlay, width, height)
    asset_id = str(overlay.get("asset_id") or "")
    external_layer = None
    if asset_id:
        asset_path = resolve_asset(c.APP_ROOT, style_pack_id, asset_id)
        with Image.open(asset_path) as opened:
            external_layer = opened.convert("RGBA")

    kind = str(overlay.get("kind") or "")
    if kind in {"service_card", "common_card"}:
        service_key = str(overlay.get("service_key") or "")
        service = c.load_service_catalog().get(service_key, {})
        card_segment = {
            "segment_id": str(overlay.get("overlay_id") or "READY_CARD"),
            "type": "card", "card_kind": "service" if kind == "service_card" else "phase",
            "title": str(overlay.get("text") or service.get("label") or "FRANCO ROMEU"),
            "body": str(overlay.get("body") or service.get("body") or "ARTE & ENGENHARIA"),
            "service_key": service_key, "service_id": service_key,
            "service_name": service.get("label", ""), "service_asset": service.get("asset", ""),
            "service_layout": service.get("layout", ""), "card_family": service.get("visual_family", ""),
            "balloon_family": service.get("balloon_family", ""),
        }
        full = target.with_name(target.stem + ".card.png")
        c.card_image(
            full, card_segment,
            {"output": {"width": width, "height": height}, "style_pack_id": style_pack_id},
            c.load_brand(), style, project,
        )
        with Image.open(full) as opened:
            layer = opened.convert("RGBA")
        full.unlink(missing_ok=True)
        if external_layer is not None:
            from style_engine import load_style_pack
            automatic_service_slot = str(
                load_style_pack(c.APP_ROOT, style_pack_id).get("services", {}).get(service_key, {}).get("asset_id") or ""
            )
            if kind != "service_card" or asset_id != automatic_service_slot:
                decoration = external_layer.copy()
                decoration.thumbnail((width, height), Image.Resampling.LANCZOS)
                layer.alpha_composite(decoration, ((width - decoration.width) // 2, (height - decoration.height) // 2))
        if overlay.get("presentation") == "full_frame":
            canvas = _apply_opacity(layer, opacity)
        else:
            layer.thumbnail((int(width * 0.58), int(height * 0.54)), Image.Resampling.LANCZOS)
            _place_layer(canvas, _apply_opacity(layer, opacity), str(overlay.get("position") or "bottom_left"), safe_margin)
        canvas.save(target)
        return target
    if kind == "logo":
        logo_width = max(64, int(width * 0.14))
        layer = external_layer
        if layer is None:
            try:
                installed_logo = resolve_asset(c.APP_ROOT, style_pack_id, "logo_primary")
                with Image.open(installed_logo) as opened:
                    layer = opened.convert("RGBA")
            except (OSError, RuntimeError):
                logo_path = c.logo_path_for(project, style)
                if not logo_path.is_file():
                    raise c.AutoEditeError("Logo configurada não foi encontrada.")
                with Image.open(logo_path) as opened:
                    layer = opened.convert("RGBA")
        layer.thumbnail((logo_width, logo_width), Image.Resampling.LANCZOS)
        _place_layer(canvas, _apply_opacity(layer, opacity), str(overlay.get("position") or "top_right"), safe_margin)
        canvas.save(target)
        return target

    # O sistema v2 mede o texto integralmente e falha de forma explícita se a
    # caixa não comportar o conteúdo. O caminho antigo fica disponível apenas
    # para assets externos, cuja geometria pertence ao próprio arquivo.
    if external_layer is None and kind in {"balloon", "callout", "lower_third", "caption"}:
        from fr_v4.overlays import render_overlay
        layer = render_overlay(overlay, (width, height), c.APP_ROOT)
        default_position = "bottom_center" if kind in {"caption", "lower_third"} else "bottom_left"
        _place_layer(canvas, _apply_opacity(layer, opacity),
                     str(overlay.get("position") or default_position), safe_margin)
        canvas.save(target)
        layer.close()
        canvas.close()
        return target

    palette = style.get("palette", {})
    bone = c.hex_rgb(str(palette.get("bone") or "#E6D6B5"))
    petroleum = c.hex_rgb(str(palette.get("background") or "#031812"))
    gold = c.hex_rgb(str(palette.get("gold") or "#C8A034"))
    orange = c.hex_rgb(str(palette.get("orange") or "#FF6B00"))
    text = str(overlay.get("text") or "")
    fonts = style.get("fonts", {})
    is_caption = kind == "caption"
    selected_font = c.font(
        fonts.get("body", "Rokkitt-Regular.ttf"),
        max(22, int(width * (0.034 if is_caption else 0.040))),
    )
    scratch = ImageDraw.Draw(canvas, "RGBA")
    max_text_width = int(width * (0.78 if is_caption else 0.62))
    lines = c.wrap_pixel(scratch, text, selected_font, max_text_width)[:4]
    line_height = int(selected_font.size * 1.22)
    measured = [scratch.textbbox((0, 0), line, font=selected_font) for line in lines]
    text_width = max((box[2] - box[0] for box in measured), default=max_text_width // 2)
    pad_x, pad_y = max(24, width // 34), max(14, height // 90)
    if external_layer is not None:
        external_layer.thumbnail(
            (width if overlay.get("presentation") == "full_frame" else int(width * 0.78),
             height if overlay.get("presentation") == "full_frame" else int(height * 0.32)),
            Image.Resampling.LANCZOS,
        )
        layer = external_layer
        layer_w, layer_h = layer.size
        pad_x, pad_y = max(pad_x, int(layer_w * 0.08)), max(pad_y, int(layer_h * 0.12))
    else:
        layer_w = min(width - 2 * pad_x, text_width + 2 * pad_x)
        layer_h = len(lines) * line_height + 2 * pad_y
        layer = Image.new("RGBA", (layer_w, layer_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    if external_layer is not None:
        fitted = False
        for candidate_size in range(selected_font.size, 15, -2):
            candidate_font = c.font(fonts.get("body", "Rokkitt-Regular.ttf"), candidate_size)
            candidate_lines = c.wrap_pixel(
                draw, text, candidate_font, max(24, layer_w - 2 * pad_x),
            )
            candidate_height = int(candidate_font.size * 1.22)
            if len(candidate_lines) <= 4 and len(candidate_lines) * candidate_height <= layer_h - 2 * pad_y:
                selected_font, lines, line_height = candidate_font, candidate_lines, candidate_height
                fitted = True
                break
        if not fitted:
            raise c.AutoEditeError(
                f"{overlay.get('overlay_id', 'overlay')}: o texto não cabe no asset sem perder legibilidade."
            )
    radius = max(12, min(layer_w, layer_h) // 10)
    if external_layer is None:
        draw.rounded_rectangle((3, 5, layer_w - 1, layer_h - 1), radius=radius, fill=(0, 0, 0, 86))
        draw.rounded_rectangle((0, 0, layer_w - 4, layer_h - 6), radius=radius, fill=(*petroleum, 226), outline=(*gold, 178), width=max(1, width // 500))
        draw.rounded_rectangle((0, 0, max(7, width // 120), layer_h - 6), radius=max(3, radius // 2), fill=(*orange, 245))
    y = pad_y - 2
    for line in lines:
        draw.text((pad_x, y), line, font=selected_font, fill=(*bone, 255))
        y += line_height
    default_position = "bottom_center" if kind in {"caption", "lower_third"} else "bottom_left"
    _place_layer(canvas, _apply_opacity(layer, opacity), str(overlay.get("position") or default_position), safe_margin)
    canvas.save(target)
    return target


def _ffmpeg_compose(
    c: SimpleNamespace, base: Path, layers: list[tuple[dict[str, Any], Path]], target: Path,
    *, duration: float, fps: float, preview_duration: float | None = None,
) -> None:
    command = ["ffmpeg", "-y", "-nostdin", "-hide_banner", "-loglevel", "error", "-i", str(base)]
    for _overlay, image in layers:
        command += ["-loop", "1", "-i", str(image)]
    filters: list[str] = [f"[0:v]fps={fps:.6f},setpts=PTS-STARTPTS[rv0]"]
    current = "rv0"
    for index, (overlay, _image) in enumerate(layers, 1):
        start, end = float(overlay["start_sec"]), float(overlay["end_sec"])
        fade = min(0.28, max(0.0, (end - start) / 4.0))
        source = f"layer{index}"
        layer_filters = ["format=rgba"]
        if overlay.get("animation_in") != "none":
            layer_filters.append(f"fade=t=in:st={start:.6f}:d={fade:.6f}:alpha=1")
        if overlay.get("animation_out") != "none":
            layer_filters.append(f"fade=t=out:st={max(start, end-fade):.6f}:d={fade:.6f}:alpha=1")
        filters.append(f"[{index}:v]{','.join(layer_filters)}[{source}]")
        output = f"rv{index}"
        filters.append(
            f"[{current}][{source}]overlay=0:0:format=auto:enable='between(t,{start:.6f},{end:.6f})'[{output}]"
        )
        current = output
    filters.append(f"[{current}]format=yuv420p[rvout]")
    temporary = target.with_name(target.stem + ".partial.mp4")
    temporary.unlink(missing_ok=True)
    command += [
        "-filter_complex", ";".join(filters), "-map", "[rvout]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-r", f"{fps:.6f}", "-fps_mode", "cfr",
    ]
    output_duration = min(duration, preview_duration) if preview_duration else duration
    # As imagens de overlay usam loop intencionalmente. Sem um limite explícito,
    # esses streams podem manter o muxer aberto depois do EOF do vídeo-base.
    command += ["-t", f"{output_duration:.6f}"]
    command += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", "-threads", "2", str(temporary)]
    try:
        result = c.run(command, capture=True, check=False)
        if result.returncode != 0:
            raise c.AutoEditeError(f"Falha ao compor vídeo pronto: {(result.stderr or '')[-1200:]}")
        c.validate_rendered_media(temporary, output_duration)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def _extension_source(project: Path, configured: str) -> Path:
    value = Path(str(configured or "")).expanduser()
    return value.resolve() if value.is_absolute() else (project / value).resolve()


def _normalize_extension(
    c: SimpleNamespace, source: Path, target: Path, *, width: int, height: int,
    fps: float, duration: float, preserve_audio: bool, audio_channels: int = 2,
) -> None:
    if not source.is_file():
        raise c.AutoEditeError(f"Intro/outro configurado não encontrado: {source}")
    is_video = source.suffix.lower() in c.VIDEO_EXTENSIONS
    command = ["ffmpeg", "-y", "-nostdin", "-hide_banner", "-loglevel", "error"]
    if is_video:
        command += ["-i", str(source)]
    else:
        command += ["-loop", "1", "-i", str(source)]
    probe = c.parse_probe(source, c.ffprobe(source)) if is_video else {"has_audio": False}
    has_audio = bool(is_video and preserve_audio and probe.get("has_audio"))
    if not has_audio:
        layout = "mono" if audio_channels == 1 else "stereo"
        command += ["-f", "lavfi", "-t", f"{duration:.6f}", "-i", f"anullsrc=r=48000:cl={layout}"]
    vf = (
        f"split=2[bg][fg];[bg]scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},gblur=sigma=18[bg2];[fg]scale={width}:{height}:"
        f"force_original_aspect_ratio=decrease[fg2];[bg2][fg2]overlay=(W-w)/2:(H-h)/2,"
        f"setsar=1,fps={fps:.6f},format=yuv420p"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.stem + ".partial.mp4")
    temporary.unlink(missing_ok=True)
    command += ["-vf", vf, "-map", "0:v:0", "-map", "0:a:0" if has_audio else "1:a:0",
                "-t", f"{duration:.6f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", str(audio_channels),
                "-movflags", "+faststart", "-threads", "2", str(temporary)]
    try:
        c.run(command)
        c.validate_rendered_media(temporary, duration)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def _moviepy_preview(
    base: Path, layers: list[tuple[dict[str, Any], Path]], target: Path,
    *, duration: float, fps: float,
) -> None:
    """Compositor curto compatível com MoviePy 1.x e 2.x."""
    try:
        from moviepy import VideoFileClip, ImageClip, CompositeVideoClip  # type: ignore
    except ImportError:
        from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip  # type: ignore
    preview_duration = min(12.0, duration)
    base_clip = VideoFileClip(str(base))
    if hasattr(base_clip, "subclipped"):
        base_clip = base_clip.subclipped(0, preview_duration)
    else:
        base_clip = base_clip.subclip(0, preview_duration)
    clips: list[Any] = [base_clip]
    for overlay, path in layers:
        start = float(overlay["start_sec"])
        if start >= preview_duration:
            continue
        clip = ImageClip(str(path))
        length = max(0.04, min(float(overlay["end_sec"]), preview_duration) - start)
        if hasattr(clip, "with_start"):
            clip = clip.with_start(start).with_duration(length)
        else:
            clip = clip.set_start(start).set_duration(length)
        clips.append(clip)
    composite = CompositeVideoClip(clips, size=base_clip.size)
    try:
        composite.write_videofile(
            str(target), codec="libx264", audio_codec="aac", fps=fps or None,
            logger=None, preset="veryfast", threads=2,
        )
    finally:
        composite.close()
        base_clip.close()


def render(
    env: dict[str, Any], project: Path, ready_plan: dict[str, Any], *, preview: bool = False,
) -> dict[str, Any]:
    c = SimpleNamespace(**env)
    project = Path(project).resolve()
    manifest = c.read_json(project / "MANIFESTO_MEDIA.json")
    from master_contract import validate_ready_video_contract
    validated, notices = validate_ready_video_contract(c, ready_plan, manifest)
    row = next(item for item in manifest.get("media", []) if item.get("id") == validated["base_video_id"])
    base = project / str(row["source_path"])
    if not base.is_file():
        raise c.AutoEditeError("Vídeo-base não encontrado no projeto.")
    before_hash = _sha256(base)
    parsed = c.parse_probe(base, c.ffprobe(base))
    width, height = int(parsed["width"]), int(parsed["height"])
    duration, fps = float(parsed["duration_sec"]), float(parsed.get("fps") or 24)
    style = c.load_card_style(project)
    pack_id = validated["style_pack_id"]
    work = project / "_CACHE_RENDER" / "ready_video_overlays"
    work.mkdir(parents=True, exist_ok=True)
    cache_path = work / "LAYER_CACHE.json"
    layer_cache = project_scope.read(cache_path, {})
    cached_layers = layer_cache.get("layers", {}) if isinstance(layer_cache.get("layers", {}), dict) else {}
    shared_layer_state = {
        "width": width, "height": height, "card_style": style,
        "style_pack_signature": style_pack_signature(c.APP_ROOT, pack_id),
        "application": c.APP_VERSION,
    }
    expected_layers = {f"{overlay['overlay_id']}.png" for overlay in validated["overlays"]}
    for stale in work.glob("*.png"):
        if stale.name not in expected_layers:
            stale.unlink(missing_ok=True)
    layers: list[tuple[dict[str, Any], Path]] = []
    next_layer_cache: dict[str, dict[str, str]] = {}
    for overlay in validated["overlays"]:
        target = work / f"{overlay['overlay_id']}.png"
        visual_overlay = {
            key: copy.deepcopy(value) for key, value in overlay.items()
            if key not in {"start_sec", "end_sec", "card_instance", "rationale", "audio_policy"}
        }
        layer_signature = hashlib.sha256(json.dumps(
            {"shared": shared_layer_state, "overlay": visual_overlay},
            ensure_ascii=False, sort_keys=True, allow_nan=False,
        ).encode("utf-8")).hexdigest()
        cached = cached_layers.get(overlay["overlay_id"], {})
        if not target.is_file() or cached.get("signature") != layer_signature:
            overlay_image(env, project, overlay, width, height, style, pack_id, target)
        next_layer_cache[overlay["overlay_id"]] = {
            "signature": layer_signature, "relative": _relative(target, project),
        }
        layers.append((overlay, target))
    project_scope.write(cache_path, {"schema_version": 1, "layers": next_layer_cache})
    signature_payload = {
        "plan": validated,
        "card_style": style,
        "base_sha256": before_hash,
        "style_pack_signature": style_pack_signature(c.APP_ROOT, pack_id),
        "layer_sha256": {overlay["overlay_id"]: _sha256(path) for overlay, path in layers},
        "application": c.APP_VERSION,
    }
    signature = hashlib.sha256(json.dumps(signature_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:24]
    slug = c.slugify(validated.get("project", {}).get("slug") or project.name).upper().replace("-", "_")
    if preview:
        target = project / "previews" / "READY_VIDEO_PREVIEW.mp4"
    else:
        target = project / "entrega" / f"FR_{slug}_READY_VIDEO_OVERLAYS.mp4"
    target.parent.mkdir(parents=True, exist_ok=True)
    config = c.normalize_answers(c.read_json(project / "QUESTIONARIO_RESPONDIDO.json"))
    external = config.get("external_intro_outro", {})
    extension_specs: list[tuple[str, Path, float, bool]] = []
    for role in ("intro", "outro"):
        if not external.get(f"{role}_enabled", False):
            continue
        if not validated.get("allow_duration_extension", False):
            raise c.AutoEditeError(
                f"{role}: a extensão de duração está bloqueada. Ative allow_duration_extension para usar intro/outro."
            )
        extension_specs.append((
            role,
            _extension_source(project, str(external.get(f"{role}_path") or "")),
            float(external.get(f"{role}_duration_sec") or 4),
            bool(external.get(f"{role}_preserve_audio", True)),
        ))
    compose_target = target if not extension_specs else work / (
        "READY_VIDEO_BASE_PREVIEW.mp4" if preview else "READY_VIDEO_BASE_OVERLAYS.mp4"
    )
    backend = choose_preview_backend(True) if preview and not extension_specs else "ffmpeg"
    if backend == "moviepy" and any(
        overlay.get("animation_in") != "none" or overlay.get("animation_out") != "none"
        for overlay, _path in layers
    ):
        # O fallback FFmpeg é a referência executável desta V1 e implementa os
        # fades validados. MoviePy fica restrito a composições estáticas para a
        # prévia nunca divergir visualmente do render final.
        backend = "ffmpeg"
    if preview and backend == "moviepy":
        temporary = compose_target.with_name(compose_target.stem + ".partial.mp4")
        temporary.unlink(missing_ok=True)
        try:
            _moviepy_preview(base, layers, temporary, duration=duration, fps=fps)
            c.validate_rendered_media(temporary, min(12.0, duration))
            temporary.replace(compose_target)
        except Exception as exc:
            temporary.unlink(missing_ok=True)
            c.warning(f"MoviePy não compôs a prévia ({exc}); usando fallback FFmpeg equivalente.")
            backend = "ffmpeg"
            _ffmpeg_compose(c, base, layers, compose_target, duration=duration, fps=fps, preview_duration=12.0)
    else:
        _ffmpeg_compose(
            c, base, layers, compose_target, duration=duration, fps=fps,
            preview_duration=12.0 if preview else None,
        )
    extension_duration = 0.0
    if extension_specs:
        compose_probe = c.ffprobe(compose_target)
        audio_stream = next((stream for stream in compose_probe.get("streams", [])
                             if stream.get("codec_type") == "audio"), {})
        audio_channels = max(1, min(2, int(audio_stream.get("channels") or 2)))
        normalized: dict[str, Path] = {}
        for role, source, requested_duration, preserve_audio in extension_specs:
            extension_target = work / f"READY_{role.upper()}_NORMALIZED.mp4"
            _normalize_extension(
                c, source, extension_target, width=width, height=height, fps=fps,
                duration=requested_duration, preserve_audio=preserve_audio,
                audio_channels=audio_channels,
            )
            normalized[role] = extension_target
            extension_duration += requested_duration
        pieces = []
        if "intro" in normalized:
            pieces.append(normalized["intro"])
        pieces.append(compose_target)
        if "outro" in normalized:
            pieces.append(normalized["outro"])
        c._concat_copy_segments(pieces, target)
    if _sha256(base) != before_hash:
        raise c.AutoEditeError("Proteção de integridade: o vídeo-base foi alterado durante o render.")
    output_probe = c.parse_probe(target, c.ffprobe(target))
    if not preview:
        tolerance = 1.0 / max(1.0, fps) + 0.01
        expected_duration = duration + extension_duration
        delta = abs(float(output_probe.get("duration_sec") or 0) - expected_duration)
        if delta > tolerance:
            raise c.AutoEditeError(
                f"Duração do vídeo pronto divergiu {delta:.4f}s; limite de um frame é {tolerance:.4f}s."
            )
    record = {
        "schema_version": 1, "generated_at": c.now_iso(), "signature": signature,
        "input_mode": "ready_video", "backend": backend, "preview": preview,
        "source_path": row["source_path"], "source_sha256": before_hash,
        "output_path": _relative(target, project), "output_duration_sec": output_probe.get("duration_sec", 0),
        "style_pack_id": pack_id, "duration_extension_sec": extension_duration, "notices": notices,
    }
    c.write_json(project / "_CONTROLE" / ("READY_VIDEO_PREVIEW.json" if preview else "READY_VIDEO_RENDER.json"), record)
    return record
