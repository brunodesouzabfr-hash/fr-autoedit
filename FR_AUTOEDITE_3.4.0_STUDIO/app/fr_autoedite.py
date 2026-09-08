#!/usr/bin/env python3
"""FR AutoEdite — preparação, inteligência de edição e render local.

O programa não altera os arquivos originais. Ele trabalha em uma pasta de
projeto, cria proxies leves, manifesto cronológico, contatos visuais, plano
JSON editável e duas versões de vídeo: institucional e limpa.
"""

from __future__ import annotations

import argparse
import copy
import csv
import datetime as dt
import hashlib
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unicodedata
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


APP_VERSION = "3.4.0"
APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT / "app") not in sys.path:
    sys.path.insert(0, str(APP_ROOT / "app"))
from project_scope import isolated_render
from media_frames import source_signatures
TEMPLATES = APP_ROOT / "templates"
ASSETS = APP_ROOT / "assets"
FONTS = ASSETS / "fonts"
DEFAULT_WORKSPACE = Path("~/FR-AutoEdite/Studio").expanduser()
DEFAULT_ZIP = DEFAULT_WORKSPACE / "novo-projeto" / "_ENTRADA" / "FR_AUTOEDITE_ENTRADA.zip"
AI_BRIEF_JSON_BEGIN = "<!-- FR_AUTOEDITE_JSON_BEGIN -->"
AI_BRIEF_JSON_END = "<!-- FR_AUTOEDITE_JSON_END -->"

ORDER_MODES = {"automatico", "cronologico", "alfabetico", "aleatorio"}

TRANSITION_MAP = {
    "cut": "cut",
    "fade": "fade", "fade_black": "fadeblack", "fade_white": "fadewhite",
    "dissolve": "dissolve", "pixelize": "pixelize", "blur": "hblur",
    "zoom_in": "zoomin", "zoom_swipe": "zoomin",
    "slide_left": "slideleft", "slide_right": "slideright",
    "slide_up": "slideup", "slide_down": "slidedown",
    "smooth_left": "smoothleft", "smooth_right": "smoothright",
    "smooth_up": "smoothup", "smooth_down": "smoothdown",
    "wipe_left": "wipeleft", "wipe_right": "wiperight",
    "wipe_up": "wipeup", "wipe_down": "wipedown",
    "diagonal_tl": "diagtl", "diagonal_tr": "diagtr",
    "diagonal_bl": "diagbl", "diagonal_br": "diagbr",
    "circle_open": "circleopen", "circle_close": "circleclose",
    "radial": "radial", "squeeze_horizontal": "squeezeh",
    "squeeze_vertical": "squeezev",
}

CARD_PRESETS = {
    "site_fr_luxo": {
        "palette": {"background": "#061D18", "surface": "#0A2F26", "orange": "#FC7016", "gold": "#C8A034", "bone": "#E6D6B5", "border": "#1A6069"},
        "details": {"density": "high", "top_bar": True, "bottom_bar": True, "corner_brackets": True, "diagonal_band": True, "technical_ticks": True},
    },
    "forja_tecnica": {
        "palette": {"background": "#0A2F26", "surface": "#123F34", "orange": "#FC7016", "gold": "#C8A034", "bone": "#E6D6B5", "border": "#1A6069"},
        "details": {"density": "high", "top_bar": True, "bottom_bar": True, "corner_brackets": True, "diagonal_band": True, "technical_ticks": True},
    },
    "editorial_osso": {
        "palette": {"background": "#121318", "surface": "#0A2F26", "orange": "#FF6B00", "gold": "#C8986A", "bone": "#F0ECE4", "border": "#1A6069"},
        "details": {"density": "medium", "top_bar": True, "bottom_bar": False, "corner_brackets": False, "diagonal_band": False, "technical_ticks": True},
    },
    "cinema_petroleo": {
        "palette": {"background": "#031812", "surface": "#0B3D3E", "orange": "#FF7A00", "gold": "#C8A034", "bone": "#E6D6B5", "border": "#123F34"},
        "details": {"density": "low", "top_bar": True, "bottom_bar": True, "corner_brackets": False, "diagonal_band": True, "technical_ticks": False},
    },
    "blueprint_3d": {
        "palette": {"background": "#043451", "surface": "#0A2F26", "orange": "#FC7016", "gold": "#71E5F4", "bone": "#F0ECE4", "border": "#65B5FF"},
        "details": {"density": "high", "top_bar": True, "bottom_bar": False, "corner_brackets": True, "diagonal_band": False, "technical_ticks": True},
    },
}
ORDER_ALIASES = {
    "auto": "automatico", "automatic": "automatico", "automático": "automatico",
    "cronológica": "cronologico", "cronologica": "cronologico", "chronological": "cronologico",
    "alfabética": "alfabetico", "alfabetica": "alfabetico", "alphabetical": "alfabetico",
    "aleatória": "aleatorio", "aleatoria": "aleatorio", "random": "aleatorio",
    "shuffle": "aleatorio", "mashup": "aleatorio",
}

VIDEO_EXTENSIONS = {
    ".mp4", ".mov", ".mkv", ".m4v", ".avi", ".webm", ".3gp", ".mts", ".m2ts"
}
IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".tif", ".tiff", ".dng"
}
SIDECAR_SUFFIXES = (".json", ".supplemental-metadata.json")


class AutoEditeError(RuntimeError):
    pass


def info(message: str) -> None:
    print(f"[FR] {message}", flush=True)


def warning(message: str) -> None:
    print(f"[FR][ATENÇÃO] {message}", file=sys.stderr, flush=True)


def expand_path(value: str | Path) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(str(value)))).resolve()


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return normalized or "projeto-fr"


def normalize_search(value: str) -> str:
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AutoEditeError(f"Arquivo JSON não encontrado: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AutoEditeError(f"JSON inválido em {path}: linha {exc.lineno}, coluna {exc.colno}") from exc


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Mescla configurações preservando compatibilidade com questionários 1.x."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def normalize_order_mode(value: Any) -> str:
    normalized = normalize_search(str(value or "automatico")).strip()
    normalized = ORDER_ALIASES.get(normalized, normalized)
    if normalized not in ORDER_MODES:
        raise AutoEditeError(
            f"Modo de edição inválido: {value}. Use automatico, cronologico, alfabetico ou aleatorio."
        )
    return normalized


def normalize_answers(raw: dict[str, Any]) -> dict[str, Any]:
    def bounded(value: Any, default: float, minimum: float, maximum: float) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            parsed = default
        if not math.isfinite(parsed):
            parsed = default
        return min(maximum, max(minimum, parsed))

    base = read_json(TEMPLATES / "questionario_base.json")
    merged = deep_merge(base, raw)
    merged["schema_version"] = 3
    edition = merged.setdefault("edition", {})
    edition["order_mode"] = normalize_order_mode(
        edition.get("order_mode", "automatico")
    )
    edition["quality_preset"] = str(edition.get("quality_preset") or "custom").lower()
    if edition["quality_preset"] not in {"draft", "hd", "full_hd", "2k", "4k", "original", "custom"}:
        edition["quality_preset"] = "custom"
    edition["format"] = str(edition.get("format") or "vertical").lower()
    if edition["format"] not in {"vertical", "horizontal", "quadrado"}:
        edition["format"] = "vertical"
    edition["render_source"] = str(edition.get("render_source") or "originals").lower()
    if edition["render_source"] not in {"proxies", "originals"}:
        edition["render_source"] = "originals"
    edition["width"] = int(bounded(edition.get("width"), 720, 240, 7680))
    edition["height"] = int(bounded(edition.get("height"), 1280, 240, 7680))
    edition["width"] += edition["width"] % 2
    edition["height"] += edition["height"] % 2
    edition["fps"] = int(bounded(edition.get("fps"), 24, 12, 120))
    edition["target_duration_sec"] = bounded(edition.get("target_duration_sec"), 360, 5, 21600)
    edition["average_clip_duration_sec"] = bounded(edition.get("average_clip_duration_sec"), 6, 0.3, 120)
    edition["max_video_excerpt_sec"] = bounded(edition.get("max_video_excerpt_sec"), 14, 0.3, 600)
    edition["still_duration_sec"] = bounded(edition.get("still_duration_sec"), 4, 0.3, 120)
    edition["phase_card_duration_sec"] = bounded(edition.get("phase_card_duration_sec"), 4, 0.3, 120)
    edition["max_media_segments"] = int(bounded(edition.get("max_media_segments"), 80, 1, 10000))
    edition["music_volume"] = bounded(edition.get("music_volume"), 0.1, 0, 2)
    random_mode = merged.setdefault("random_mode", {})
    if random_mode.get("enabled"):
        merged["edition"]["order_mode"] = "aleatorio"
    handoff = merged.setdefault("handoff", {})
    try:
        requested_lot = float(handoff.get("chatgpt_lot_max_mb", 145))
    except (TypeError, ValueError):
        requested_lot = 145.0
    handoff["chatgpt_lot_max_mb"] = min(149.0, max(10.0, requested_lot))
    merged.setdefault("ai_copilot", {}).setdefault("enabled", False)
    service = merged.setdefault("service_intro", {})
    available_services = {item["key"] for item in load_service_catalog().values()}
    if str(service.get("service_key") or "") not in available_services:
        service["service_key"] = "projetos_3d"
    service["duration_sec"] = bounded(service.get("duration_sec"), 3.5, 0.8, 20)
    external = merged.setdefault("external_intro_outro", {})
    for role in ("intro", "outro"):
        external[f"{role}_duration_sec"] = bounded(external.get(f"{role}_duration_sec"), 4, 0.4, 120)
        external.setdefault(f"{role}_include_in_reels", True)
    social = merged.setdefault("social", {})
    durations: list[int] = []
    raw_durations = social.get("reel_durations_sec", [30, 60, 90])
    if not isinstance(raw_durations, (list, tuple, set)):
        raw_durations = [raw_durations]
    for value in raw_durations:
        try:
            target = int(float(value))
        except (TypeError, ValueError):
            continue
        if 5 <= target <= 600 and target not in durations:
            durations.append(target)
    social["reel_durations_sec"] = sorted(durations or [30, 60, 90])
    social["story_part_duration_sec"] = int(bounded(social.get("story_part_duration_sec"), 15, 5, 120))
    social["carousel_slides"] = int(bounded(social.get("carousel_slides"), 8, 1, 40))
    effects = merged.setdefault("visual_effects", {})
    raw_transitions = effects.get("transitions", ["fade"])
    if not isinstance(raw_transitions, (list, tuple, set)):
        raw_transitions = [raw_transitions]
    transitions = [
        str(value) for value in raw_transitions
        if str(value) in TRANSITION_MAP
    ]
    effects["transitions"] = list(dict.fromkeys(transitions)) or ["fade"]
    effects["transition_duration_sec"] = bounded(effects.get("transition_duration_sec"), 0.45, 0, 3)
    if str(effects.get("stabilization_mode")) not in {"auto", "all", "manual"}:
        effects["stabilization_mode"] = "auto"
    if str(effects.get("stabilization_strength")) not in {"light", "low", "medium", "strong", "high"}:
        effects["stabilization_strength"] = "medium"
    timelapse = effects.setdefault("editorial_timelapse", {})
    timelapse["enabled"] = bool(timelapse.get("enabled", False))
    timelapse["speed_factor"] = bounded(timelapse.get("speed_factor"), 6, 1.25, 30)
    timelapse["minimum_source_duration_sec"] = bounded(
        timelapse.get("minimum_source_duration_sec"), 18, 3, 3600,
    )
    timelapse["output_duration_sec"] = bounded(timelapse.get("output_duration_sec"), 4, 0.75, 30)
    timelapse["max_segments"] = int(bounded(timelapse.get("max_segments"), 4, 1, 30))
    timelapse["mute_original_audio"] = bool(timelapse.get("mute_original_audio", True))
    audio = merged.setdefault("audio_design", {})
    audio["sfx_volume"] = bounded(audio.get("sfx_volume"), 0.3, 0, 1)
    quality = merged.setdefault("export_quality", {})
    quality["parallel_workers"] = int(bounded(quality.get("parallel_workers"), 2, 1, 16))
    quality["video_crf"] = int(bounded(quality.get("video_crf"), 18, 0, 35))
    quality["audio_bitrate_kbps"] = int(bounded(quality.get("audio_bitrate_kbps"), 192, 64, 320))
    brief = merged.setdefault("editing_brief", {})
    brief.setdefault("overlay_title_font", "StardosStencil-Bold.ttf")
    brief.setdefault("overlay_body_font", "Rokkitt-Regular.ttf")
    brief.setdefault("overlay_technical_font", "ShareTechMono-Regular.ttf")
    return merged


def load_service_catalog() -> dict[str, dict[str, Any]]:
    """Carrega o catálogo fechado de cards de serviço da instalação."""
    source = read_json(TEMPLATES / "service_catalog.json")
    return {
        str(item.get("key")): item
        for item in source.get("services", [])
        if isinstance(item, dict) and item.get("key")
    }


def resolve_output_dimensions(
    edition: dict[str, Any], media_rows: list[dict[str, Any]] | None = None,
) -> tuple[int, int]:
    """Resolve a qualidade de saída sem trocar silenciosamente originais por proxies."""
    preset = str(edition.get("quality_preset") or "custom").lower()
    output_format = str(edition.get("format") or "vertical").lower()
    sizes = {
        "draft": (480, 854),
        "hd": (720, 1280),
        "full_hd": (1080, 1920),
        "2k": (1440, 2560),
        "4k": (2160, 3840),
    }
    if preset == "original":
        longest = max(
            [max(int(row.get("width") or 0), int(row.get("height") or 0)) for row in (media_rows or [])]
            or [max(int(edition.get("width", 720)), int(edition.get("height", 1280)))]
        )
        longest = max(720, min(7680, longest))
        short = max(2, int(round(longest * 9 / 16)))
    elif preset in sizes:
        short, longest = sizes[preset]
    else:
        return int(edition.get("width", 720)), int(edition.get("height", 1280))
    short += short % 2
    longest += longest % 2
    if output_format == "horizontal":
        return longest, short
    if output_format == "quadrado":
        return short, short
    return short, longest


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(content, encoding="utf-8")
    temp.replace(path)


def run(
    command: list[str], *, capture: bool = False, check: bool = True,
    timeout: float | None = None, operation: str = "",
) -> subprocess.CompletedProcess[str]:
    """Executa um comando externo sem permitir espera infinita.

    O limite global pode ser ajustado por ``FR_AUTOEDITE_COMMAND_TIMEOUT_SEC``.
    Chamadas curtas, como FFprobe e miniaturas, informam limites menores. O
    ``subprocess.run`` encerra o processo ao expirar e os arquivos ``.partial``
    continuam sendo removidos pelos chamadores.
    """
    if timeout is None:
        try:
            timeout = float(os.environ.get("FR_AUTOEDITE_COMMAND_TIMEOUT_SEC", "7200"))
        except ValueError:
            timeout = 7200.0
    timeout = None if timeout <= 0 else max(1.0, timeout)
    try:
        result = subprocess.run(
            command,
            text=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
            stderr=subprocess.PIPE if capture else subprocess.DEVNULL,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        label = operation.strip() or Path(command[0]).name
        raise AutoEditeError(
            f"Tempo limite excedido em {label} após {int(timeout or 0)} s. "
            "O item foi interrompido com segurança; execute novamente para retomar os demais."
        ) from exc
    if check and result.returncode != 0:
        tail = (result.stderr or "").strip()[-1800:]
        raise AutoEditeError(f"Falha ao executar {command[0]} (código {result.returncode}).\n{tail}")
    return result


def check_runtime(require_pillow: bool = True) -> None:
    missing = [name for name in ("ffmpeg", "ffprobe") if shutil.which(name) is None]
    if missing:
        raise AutoEditeError(
            "Dependências ausentes: " + ", ".join(missing) +
            ". No Parrot/Debian, execute: sudo apt update && sudo apt install -y ffmpeg unzip zip python3 python3-pil"
        )
    if require_pillow:
        try:
            import PIL  # noqa: F401
        except ImportError as exc:
            raise AutoEditeError(
                "Pillow não está instalado. Execute: sudo apt install -y python3-pil"
            ) from exc


def safe_extract(zip_path: Path, destination: Path) -> None:
    if not zip_path.is_file():
        raise AutoEditeError(f"ZIP não encontrado: {zip_path}")
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(zip_path) as archive:
        members = archive.infolist()
        if not members:
            raise AutoEditeError("O ZIP está vazio.")
        validated_targets: dict[str, Path] = {}
        for member in members:
            target = (destination / member.filename).resolve()
            try:
                target.relative_to(root)
            except ValueError as exc:
                raise AutoEditeError(f"Caminho inseguro dentro do ZIP: {member.filename}") from exc
            validated_targets[member.filename] = target
        unpacked_bytes = sum(member.file_size for member in members if not member.is_dir())
        remaining_bytes = sum(
            member.file_size for member in members
            if not member.is_dir()
            and not (validated_targets[member.filename].is_file()
                     and validated_targets[member.filename].stat().st_size == member.file_size)
        )
        free_bytes = shutil.disk_usage(destination).free
        reserve = max(2 * 1024**3, int(unpacked_bytes * 0.15))
        info(
            f"ZIP: {len(members)} itens, {unpacked_bytes / 1024**3:.2f} GiB descompactados; "
            f"livre no disco: {free_bytes / 1024**3:.2f} GiB"
        )
        if remaining_bytes + reserve > free_bytes:
            required = (remaining_bytes + reserve) / 1024**3
            raise AutoEditeError(
                f"Espaço insuficiente. São necessários cerca de {required:.2f} GiB livres "
                "para extrair e manter margem para proxies/render."
            )
        for index, member in enumerate(members, 1):
            target = validated_targets[member.filename]
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and target.stat().st_size == member.file_size:
                continue
            with archive.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            if index % 50 == 0:
                info(f"Extração: {index}/{len(members)} itens")


def takeout_sidecar_for(media_path: Path) -> tuple[Path | None, dict[str, Any] | None]:
    """Localiza o JSON correspondente sem depender de um único padrão de nome do Takeout."""
    exact = [
        Path(str(media_path) + ".json"),
        Path(str(media_path) + ".supplemental-metadata.json"),
        media_path.with_suffix(".json"),
        media_path.with_name(media_path.stem + ".supplemental-metadata.json"),
    ]
    prefix = media_path.name[:46]
    nearby = sorted(media_path.parent.glob(prefix + "*.json"))[:24]
    seen: set[Path] = set()
    fallback: tuple[Path, dict[str, Any]] | None = None
    for candidate in exact + nearby:
        if candidate in seen or not candidate.is_file():
            continue
        seen.add(candidate)
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        title = str(data.get("title") or "").strip()
        if candidate in exact or title == media_path.name:
            return candidate, data
        if title and normalize_search(title) == normalize_search(media_path.name):
            return candidate, data
        if fallback is None and any(isinstance(data.get(key), dict) for key in (
            "photoTakenTime", "creationTime", "modificationTime",
        )):
            fallback = (candidate, data)
    return fallback or (None, None)


def takeout_timestamp(data: dict[str, Any] | None) -> tuple[dt.datetime | None, str | None]:
    if not isinstance(data, dict):
        return None, None
    for key in ("photoTakenTime", "creationTime", "modificationTime"):
        block = data.get(key)
        if not isinstance(block, dict):
            continue
        raw = block.get("timestamp")
        try:
            numeric = float(raw)
            if numeric > 10_000_000_000:
                numeric /= 1000
            stamp = dt.datetime.fromtimestamp(numeric, tz=dt.timezone.utc)
            if 1970 <= stamp.year <= 2200:
                return stamp, key
        except (TypeError, ValueError, OverflowError, OSError):
            continue
    return None, None


def embed_takeout_timestamp(path: Path, stamp: dt.datetime) -> tuple[str, str]:
    """Grava metadados numa cópia; sempre mantém data de arquivo/ZIP como fallback."""
    exiftool = shutil.which("exiftool")
    if exiftool:
        base = stamp.astimezone(dt.timezone.utc).strftime("%Y:%m:%d %H:%M:%S")
        if path.suffix.lower() in VIDEO_EXTENSIONS:
            values = [
                f"-QuickTime:CreateDate={base}+00:00",
                f"-QuickTime:ModifyDate={base}+00:00",
                f"-TrackCreateDate={base}+00:00",
                f"-TrackModifyDate={base}+00:00",
                f"-MediaCreateDate={base}+00:00",
                f"-MediaModifyDate={base}+00:00",
            ]
        else:
            values = [
                f"-DateTimeOriginal={base}",
                f"-CreateDate={base}",
                f"-ModifyDate={base}",
            ]
        result = run(
            [exiftool, "-overwrite_original", "-api", "QuickTimeUTC=1", *values, str(path)],
            capture=True, check=False,
        )
        if result.returncode == 0:
            return "exiftool", "metadados internos + data do arquivo"
        detail = (result.stderr or result.stdout or "erro desconhecido").strip()[-300:]
        warning(f"ExifTool não gravou {path.name}; usando alternativa local: {detail}")

    # Vídeos comuns recebem creation_time por remux sem recodificação e sem
    # perda de qualidade. Formatos incompatíveis continuam com data de arquivo.
    if path.suffix.lower() in VIDEO_EXTENSIONS and shutil.which("ffmpeg"):
        temporary = path.with_name(path.stem + ".fr-data" + path.suffix)
        result = run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(path),
            "-map", "0", "-c", "copy", "-metadata",
            f"creation_time={stamp.astimezone(dt.timezone.utc).isoformat().replace('+00:00', 'Z')}",
            str(temporary),
        ], capture=True, check=False)
        if result.returncode == 0 and temporary.is_file() and temporary.stat().st_size > 0:
            temporary.replace(path)
            return "ffmpeg-remux", "creation_time interno + data do arquivo"
        temporary.unlink(missing_ok=True)

    return "filesystem-zip", "data do arquivo e da entrada ZIP; metadado interno não gravado"


def create_takeout_dated_zip(
    takeout_source: Path, project_dir: Path, *, embed_metadata: bool = True,
) -> dict[str, Any]:
    """Converte um Takeout em ZIP normalizado sem modificar o arquivo recebido."""
    takeout_source = takeout_source.resolve()
    project_dir = project_dir.resolve()
    if not takeout_source.exists():
        raise AutoEditeError(f"Google Takeout não encontrado: {takeout_source}")
    if takeout_source.is_file() and not zipfile.is_zipfile(takeout_source):
        raise AutoEditeError("O arquivo do Google Takeout precisa ser um ZIP íntegro.")

    takeout_root = project_dir / "_TAKEOUT"
    takeout_root.mkdir(parents=True, exist_ok=True)
    process_root = Path(tempfile.mkdtemp(prefix="processando-", dir=takeout_root))
    extracted = process_root / "extraido"
    dated = process_root / "midias_com_datas"
    dated.mkdir(parents=True, exist_ok=True)
    report_rows: list[dict[str, Any]] = []
    try:
        if takeout_source.is_dir():
            extracted = takeout_source
        else:
            info("Extraindo o Google Takeout com segurança")
            safe_extract(takeout_source, extracted)
        media = media_files(extracted)
        if not media:
            raise AutoEditeError("Nenhuma foto ou vídeo foi encontrado no Google Takeout.")
        matched = 0
        embedded = 0
        methods: dict[str, int] = {}
        for index, source in enumerate(media, 1):
            relative = source.relative_to(extracted)
            target = dated / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            sidecar, data = takeout_sidecar_for(source)
            stamp, field = takeout_timestamp(data)
            method = "sem-json"
            detail = "arquivo preservado; confirme a data manualmente"
            if stamp is not None:
                matched += 1
                epoch = stamp.timestamp()
                os.utime(target, (epoch, epoch))
                if embed_metadata:
                    method, detail = embed_takeout_timestamp(target, stamp)
                    os.utime(target, (epoch, epoch))
                    if method in {"exiftool", "ffmpeg-remux"}:
                        embedded += 1
                else:
                    method, detail = "filesystem-zip", "data do arquivo e da entrada ZIP"
                if sidecar is not None:
                    sidecar_target = target.parent / sidecar.name
                    if sidecar_target != target:
                        shutil.copy2(sidecar, sidecar_target)
            methods[method] = methods.get(method, 0) + 1
            report_rows.append({
                "media": str(relative),
                "sidecar_json": str(sidecar.relative_to(extracted)) if sidecar else None,
                "timestamp_utc": stamp.isoformat() if stamp else None,
                "timestamp_field": field,
                "method": method,
                "detail": detail,
            })
            if index % 50 == 0:
                info(f"Google Takeout: {index}/{len(media)} mídias processadas")

        report = {
            "schema_version": 1,
            "application": f"FR AutoEdite {APP_VERSION}",
            "generated_at": now_iso(),
            "source": str(takeout_source),
            "output": str(project_dir / "_ENTRADA" / "FR_AUTOEDITE_ENTRADA.zip"),
            "summary": {
                "media_total": len(media),
                "dates_restored_from_json": matched,
                "without_matching_date": len(media) - matched,
                "internal_metadata_written": embedded,
                "methods": methods,
            },
            "files": report_rows,
        }
        write_json(dated / "RELATORIO_GOOGLE_TAKEOUT.json", report)
        guide = [
            "# Relatório Google Takeout — FR AutoEdite", "",
            f"- Mídias encontradas: **{len(media)}**",
            f"- Datas recuperadas dos JSONs: **{matched}**",
            f"- Sem data correspondente: **{len(media) - matched}**",
            f"- Metadados internos gravados: **{embedded}**", "",
            "O ZIP original foi preservado. O novo `FR_AUTOEDITE_ENTRADA.zip` contém as mídias,",
            "os JSONs correspondentes e datas de entrada ZIP restauradas. O FR AutoEdite usa",
            "primeiro `photoTakenTime`, depois `creationTime` e por fim `modificationTime`.", "",
            "Se o ExifTool não estiver instalado, vídeos comuns recebem `creation_time` por remux",
            "FFmpeg sem recodificação; os demais arquivos mantêm a data no sistema/ZIP e o JSON",
            "ao lado da mídia para a leitura cronológica do próprio FR AutoEdite.",
        ]
        write_text(dated / "LEIA_O_RELATORIO_TAKEOUT.md", "\n".join(guide) + "\n")

        input_dir = project_dir / "_ENTRADA"
        history = project_dir / "_HISTORICO"
        input_dir.mkdir(parents=True, exist_ok=True)
        history.mkdir(parents=True, exist_ok=True)
        target = input_dir / "FR_AUTOEDITE_ENTRADA.zip"
        temporary_zip = input_dir / "FR_AUTOEDITE_ENTRADA.takeout.tmp"
        temporary_zip.unlink(missing_ok=True)
        with zipfile.ZipFile(
            temporary_zip, "w", compression=zipfile.ZIP_STORED,
            allowZip64=True, strict_timestamps=False,
        ) as archive:
            for path in sorted(item for item in dated.rglob("*") if item.is_file()):
                archive.write(path, str(path.relative_to(dated)))
        with zipfile.ZipFile(temporary_zip) as archive:
            bad = archive.testzip()
            if bad:
                raise AutoEditeError(f"ZIP normalizado do Takeout falhou no CRC: {bad}")
        if target.exists() or target.is_symlink():
            stamp_name = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            target.replace(history / f"FR_AUTOEDITE_ENTRADA_ANTES_TAKEOUT_{stamp_name}.zip")
        temporary_zip.replace(target)
        report["output"] = str(target)
        report["output_size_bytes"] = target.stat().st_size
        write_json(takeout_root / "01_RELATORIO_GOOGLE_TAKEOUT.json", report)
        write_text(takeout_root / "01_RELATORIO_GOOGLE_TAKEOUT.md", "\n".join(guide) + "\n")
        # Compatibilidade com projetos e integrações anteriores à 3.3.
        write_json(project_dir / "RELATORIO_GOOGLE_TAKEOUT.json", report)
        write_text(project_dir / "RELATORIO_GOOGLE_TAKEOUT.md", "\n".join(guide) + "\n")
        info(
            f"Google Takeout concluído: {matched}/{len(media)} datas recuperadas; "
            f"ZIP pronto em {target}"
        )
        return report
    finally:
        if process_root.exists():
            shutil.rmtree(process_root, ignore_errors=True)


def media_files(root: Path) -> list[Path]:
    found = []
    for path in root.rglob("*"):
        if not path.is_file() or path.name.startswith("."):
            continue
        if path.suffix.lower() in VIDEO_EXTENSIONS | IMAGE_EXTENSIONS:
            found.append(path)
    return sorted(found, key=lambda p: normalize_search(str(p.relative_to(root))))


def parse_ratio(value: str | None) -> float:
    if not value or value in {"0/0", "N/A"}:
        return 0.0
    try:
        if "/" in value:
            a, b = value.split("/", 1)
            return float(a) / float(b) if float(b) else 0.0
        return float(value)
    except (ValueError, ZeroDivisionError):
        return 0.0


def ffprobe(path: Path) -> dict[str, Any]:
    try:
        result = run([
            "ffprobe", "-v", "error", "-print_format", "json",
            "-show_format", "-show_streams", str(path)
        ], capture=True, check=False, timeout=60, operation=f"análise de {path.name}")
    except AutoEditeError as exc:
        return {"error": str(exc)}
    if result.returncode != 0:
        return {"error": (result.stderr or "ffprobe falhou").strip()[-500:]}
    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return {"error": "Saída inválida do ffprobe"}


def sidecar_capture_time(path: Path) -> tuple[str | None, str | None]:
    candidates = [Path(str(path) + suffix) for suffix in SIDECAR_SUFFIXES]
    candidates += [path.with_suffix(suffix) for suffix in SIDECAR_SUFFIXES]
    candidates += list(path.parent.glob(path.name[:40] + "*.json"))[:5]
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen or not candidate.is_file():
            continue
        seen.add(candidate)
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        for key in ("photoTakenTime", "creationTime", "modificationTime"):
            block = data.get(key)
            if not isinstance(block, dict):
                continue
            raw = block.get("timestamp")
            try:
                stamp = dt.datetime.fromtimestamp(int(raw), tz=dt.timezone.utc)
                return stamp.isoformat(), f"google_photos:{candidate.name}:{key}"
            except (TypeError, ValueError, OSError):
                formatted = block.get("formatted")
                if formatted:
                    return str(formatted), f"google_photos:{candidate.name}:{key}"
    return None, None


def filename_capture_time(path: Path) -> tuple[str | None, str | None]:
    name = path.name
    patterns = [
        r"(?:IMG|VID|PXL)[-_]?(20\d{2})(\d{2})(\d{2})[_-]?(\d{2})?(\d{2})?(\d{2})?",
        r"(?:IMG|VID)[-_](20\d{2})(\d{2})(\d{2})",
        r"(?<!\d)(20\d{2})[-_]?([01]\d)[-_]?([0-3]\d)(?!\d)",
    ]
    for pattern in patterns:
        match = re.search(pattern, name, flags=re.IGNORECASE)
        if not match:
            continue
        values = [int(v) if v else 0 for v in match.groups()]
        year, month, day = values[:3]
        hour, minute, second = (values + [0, 0, 0])[3:6]
        try:
            parsed = dt.datetime(year, month, day, hour, minute, second, tzinfo=dt.timezone.utc)
            return parsed.isoformat(), "filename"
        except ValueError:
            pass
    return None, None


def exif_capture_time(path: Path) -> tuple[str | None, str | None]:
    if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}:
        return None, None
    try:
        from PIL import Image, ExifTags
        with Image.open(path) as image:
            exif = image.getexif()
            tags = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
        raw = tags.get("DateTimeOriginal") or tags.get("DateTimeDigitized") or tags.get("DateTime")
        if raw:
            parsed = dt.datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S").replace(tzinfo=dt.timezone.utc)
            return parsed.isoformat(), "exif"
    except Exception:
        pass
    return None, None


def capture_time(path: Path, probe: dict[str, Any]) -> tuple[str, str]:
    for resolver in (sidecar_capture_time, filename_capture_time, exif_capture_time):
        value, source = resolver(path) if resolver is not exif_capture_time else resolver(path)
        if value:
            return value, source or "unknown"
    tags: dict[str, Any] = (probe.get("format") or {}).get("tags") or {}
    for key in ("creation_time", "com.apple.quicktime.creationdate", "date"):
        if tags.get(key):
            return str(tags[key]), f"ffprobe:{key}"
    stamp = dt.datetime.fromtimestamp(path.stat().st_mtime, tz=dt.timezone.utc)
    return stamp.isoformat(), "filesystem_mtime"


def parse_probe(path: Path, data: dict[str, Any]) -> dict[str, Any]:
    streams = data.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    fmt = data.get("format") or {}
    duration_raw = fmt.get("duration") or video.get("duration") or 0
    try:
        duration = round(float(duration_raw), 3)
    except (TypeError, ValueError):
        duration = 0.0
    rotation = 0
    for side in video.get("side_data_list") or []:
        if "rotation" in side:
            rotation = int(side.get("rotation") or 0)
    return {
        "duration_sec": duration,
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
        "fps": round(parse_ratio(video.get("avg_frame_rate") or video.get("r_frame_rate")), 3),
        "video_codec": video.get("codec_name") or "",
        "pixel_format": video.get("pix_fmt") or "",
        "has_audio": audio is not None,
        "audio_codec": (audio or {}).get("codec_name") or "",
        "rotation": rotation,
        "probe_error": data.get("error", ""),
    }


def media_quality_score(row: dict[str, Any], answers: dict[str, Any]) -> float:
    """Heurística local e explicável; não tenta substituir curadoria visual."""
    score = 50.0
    width, height = int(row.get("width") or 0), int(row.get("height") or 0)
    pixels = width * height
    if pixels >= 3840 * 2160:
        score += 14
    elif pixels >= 1920 * 1080:
        score += 10
    elif pixels >= 1280 * 720:
        score += 6
    elif pixels > 0:
        score += 2
    if row.get("probe_error"):
        score -= 35
    if row.get("media_type") == "video":
        duration = float(row.get("duration_sec") or 0)
        if 3 <= duration <= 180:
            score += 10
        elif duration > 180:
            score += 6
        elif 0 < duration < 1:
            score -= 8
        if row.get("has_audio"):
            score += 3
    else:
        score += 5
    edition = answers.get("edition", {})
    output_vertical = int(edition.get("height", 1280)) >= int(edition.get("width", 720))
    source_vertical = height >= width if width and height else output_vertical
    if source_vertical == output_vertical:
        score += 5
    return round(max(0.0, min(100.0, score)), 1)


def sha256_short(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()[:16]


def create_video_proxy(
    source: Path, target: Path, long_side: int, fps: int,
    source_duration: float = 0.0,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.stem + ".partial.mp4")
    vf = f"scale='if(gt(iw,ih),{long_side},-2)':'if(gt(iw,ih),-2,{long_side})',fps={fps},setsar=1"
    command = [
        "ffmpeg", "-y", "-nostdin", "-hide_banner", "-loglevel", "error", "-i", str(source),
        "-map", "0:v:0", "-map", "0:a?", "-vf", vf,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "31",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-ac", "1", "-b:a", "64k",
        "-movflags", "+faststart", "-threads", "2", str(temp)
    ]
    timeout = max(600.0, min(7200.0, float(source_duration or 0) * 6.0 + 180.0))
    try:
        run(command, timeout=timeout, operation=f"proxy de {source.name}")
        if not temp.is_file() or temp.stat().st_size == 0:
            raise AutoEditeError(f"Proxy vazio para {source.name}")
        temp.replace(target)
    finally:
        temp.unlink(missing_ok=True)


def create_image_proxy(source: Path, target: Path, long_side: int = 1600) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.stem + ".partial.jpg")
    try:
        try:
            from PIL import Image, ImageOps
            with Image.open(source) as image:
                image = ImageOps.exif_transpose(image).convert("RGB")
                image.thumbnail((long_side, long_side), Image.Resampling.LANCZOS)
                image.save(temp, "JPEG", quality=86, optimize=True)
        except Exception:
            vf = f"scale='if(gt(iw,ih),{long_side},-2)':'if(gt(iw,ih),-2,{long_side})',setsar=1"
            run([
                "ffmpeg", "-y", "-nostdin", "-hide_banner", "-loglevel", "error", "-i", str(source),
                "-vf", vf, "-frames:v", "1", "-q:v", "3", str(temp)
            ], timeout=180, operation=f"proxy de imagem {source.name}")
        if not temp.is_file() or temp.stat().st_size == 0:
            raise AutoEditeError(f"Proxy de imagem vazio para {source.name}")
        temp.replace(target)
    finally:
        temp.unlink(missing_ok=True)


def create_thumbnail(source: Path, target: Path, media_type: str, duration: float) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.stem + ".partial.jpg")
    seek = max(0.0, duration * 0.35)
    command = ["ffmpeg", "-y", "-nostdin", "-hide_banner", "-loglevel", "error"]
    if media_type == "video":
        command += ["-ss", f"{seek:.3f}", "-i", str(source)]
    else:
        command += ["-i", str(source)]
    command += [
        "-vf", "scale=360:240:force_original_aspect_ratio=decrease,pad=360:240:(ow-iw)/2:(oh-ih)/2:color=101713",
        "-frames:v", "1", "-q:v", "3", str(temp)
    ]
    try:
        run(command, timeout=180, operation=f"miniatura de {source.name}")
        if not temp.is_file() or temp.stat().st_size == 0:
            raise AutoEditeError(f"Miniatura vazia para {source.name}")
        temp.replace(target)
    finally:
        temp.unlink(missing_ok=True)


def create_thumbnail_at(source: Path, target: Path, seek: float) -> None:
    """Miniatura de um instante exato, usada pelos clipes virtuais de cena."""
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.stem + ".partial.jpg")
    try:
        run([
            "ffmpeg", "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
            "-ss", f"{max(0.0, seek):.3f}", "-i", str(source),
            "-vf", "scale=360:240:force_original_aspect_ratio=decrease,pad=360:240:(ow-iw)/2:(oh-ih)/2:color=101713",
            "-frames:v", "1", "-q:v", "3", str(temp),
        ], timeout=180, operation=f"miniatura de cena {target.name}")
        if not temp.is_file() or temp.stat().st_size == 0:
            raise AutoEditeError(f"Miniatura de cena vazia: {target.name}")
        temp.replace(target)
    finally:
        temp.unlink(missing_ok=True)


def _local_analysis_module() -> Any:
    try:
        from local_analysis import mark_burst_duplicates, scene_ranges, video_quality_signals
    except ImportError as exc:
        raise AutoEditeError("Módulo de análise local não foi encontrado na instalação.") from exc
    return mark_burst_duplicates, scene_ranges, video_quality_signals


def apply_local_analysis(
    project_dir: Path, rows: list[dict[str, Any]], answers: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    config = answers.get("local_analysis", {})
    if not config.get("enabled", True):
        return rows, {"enabled": False}
    mark_burst_duplicates, scene_ranges, video_quality_signals = _local_analysis_module()
    report: dict[str, Any] = {"enabled": True, "videos_analyzed": 0, "scene_clips": 0}
    if config.get("deduplicate_bursts", True):
        report.update(mark_burst_duplicates(rows, project_dir))
    if config.get("detect_stability", True):
        videos = [row for row in rows if row.get("media_type") == "video" and row.get("status") == "ok"]
        for index, row in enumerate(videos, 1):
            proxy = project_dir / str(row.get("proxy_path") or "")
            info(f"Análise técnica {index}/{len(videos)}: processando {row['id']} · {row.get('filename', '')}")
            try:
                signals = video_quality_signals(proxy, float(row.get("duration_sec") or 0))
                row.update(signals)
                if signals.get("needs_stabilization"):
                    row["quality_score"] = max(0.0, round(float(row.get("quality_score") or 0) - 5.0, 1))
                report["videos_analyzed"] += 1
                info(f"Análise técnica {index}/{len(videos)}: {row['id']} concluído")
            except Exception as exc:
                row["analysis_error"] = str(exc)[:500]
                warning(f"Análise técnica ignorada em {row['id']}: {exc}")
    expanded = list(rows)
    if config.get("scene_detection", True):
        max_scan = float(config.get("max_scene_scan_sec", 180))
        max_clips = int(config.get("max_scene_clips_per_video", 18))
        threshold = float(config.get("scene_threshold", 0.34))
        videos = [
            row for row in rows
            if row.get("media_type") == "video" and row.get("status") == "ok"
            and float(row.get("duration_sec") or 0) > 30
        ]
        for row in videos:
            proxy = project_dir / str(row.get("proxy_path") or "")
            ranges = scene_ranges(
                proxy, float(row.get("duration_sec") or 0),
                minimum=float(config.get("minimum_scene_sec", 3.0)),
                maximum=float(config.get("maximum_scene_sec", 8.0)),
                threshold=threshold, max_scan_seconds=max_scan, max_clips=max_clips,
            )
            if not ranges:
                continue
            row["scene_split_parent"] = True
            row["excluded_from_auto_edit"] = True
            row["exclusion_reason"] = "substituído por clipes virtuais detectados localmente"
            for scene_index, (start, duration) in enumerate(ranges, 1):
                child = copy.deepcopy(row)
                child_id = f"{row['id']}C{scene_index:03d}"
                thumb = project_dir / "miniaturas" / "cenas" / f"{child_id}.jpg"
                try:
                    if not thumb.is_file():
                        create_thumbnail_at(proxy, thumb, start + duration * 0.5)
                except Exception as exc:
                    warning(f"Miniatura da cena {child_id}: {exc}")
                child.update({
                    "id": child_id,
                    "filename": f"{row['filename']} [cena {scene_index:03d}]",
                    "duration_sec": round(duration, 3),
                    "parent_video": row["id"],
                    "scene_start_sec": round(start, 3),
                    "scene_end_sec": round(start + duration, 3),
                    "thumbnail_path": rel(thumb, project_dir) if thumb.is_file() else row.get("thumbnail_path", ""),
                    "scene_split_parent": False,
                    "excluded_from_auto_edit": False,
                    "exclusion_reason": "",
                    "selection_basis": "mudança de cena local + janela de 3–8 segundos",
                })
                expanded.append(child)
                report["scene_clips"] += 1
    write_json(project_dir / "RELATORIO_ANALISE_LOCAL.json", report)
    return expanded, report


def rel(path: Path, base: Path) -> str:
    return path.resolve().relative_to(base.resolve()).as_posix()


def build_manifest(project_dir: Path, answers: dict[str, Any]) -> dict[str, Any]:
    originals = project_dir / "originais"
    proxy_dir = project_dir / "proxies"
    thumb_dir = project_dir / "miniaturas"
    long_side = int(answers.get("handoff", {}).get("proxy_long_side", 720))
    proxy_fps = int(answers.get("handoff", {}).get("proxy_fps", 24))
    sources = media_files(originals)
    if not sources:
        raise AutoEditeError("Nenhuma foto ou vídeo compatível foi encontrado após extrair o ZIP.")
    checkpoint_path = project_dir / "_CONTROLE" / "PREPARACAO_CHECKPOINT.json"
    cached_rows: dict[str, dict[str, Any]] = {}
    for cache_path in (project_dir / "MANIFESTO_MEDIA.json", checkpoint_path):
        if not cache_path.is_file():
            continue
        try:
            cached = read_json(cache_path)
        except AutoEditeError:
            continue
        for cached_row in cached.get("media", []):
            if not isinstance(cached_row, dict) or cached_row.get("parent_video"):
                continue
            source_key = str(cached_row.get("source_path") or "")
            if source_key:
                cached_rows[source_key] = cached_row

    rows: list[dict[str, Any]] = []
    for index, source in enumerate(sources, 1):
        media_id = f"M{index:04d}"
        kind = "video" if source.suffix.lower() in VIDEO_EXTENSIONS else "image"
        source_relative = rel(source, project_dir)
        proxy = proxy_dir / (f"{media_id}_{slugify(source.stem)[:60]}_PROXY.mp4" if kind == "video" else f"{media_id}_{slugify(source.stem)[:60]}_PROXY.jpg")
        thumb = thumb_dir / f"{media_id}.jpg"
        cached = cached_rows.get(source_relative)
        if (
            cached
            and cached.get("id") == media_id
            and cached.get("media_type") == kind
            and int(cached.get("size_bytes") or -1) == source.stat().st_size
            and cached.get("status") == "ok"
            and proxy.is_file() and proxy.stat().st_size > 0
            and thumb.is_file() and thumb.stat().st_size > 0
        ):
            row = copy.deepcopy(cached)
            row.update({
                "id": media_id,
                "filename": source.name,
                "source_path": source_relative,
                "proxy_path": rel(proxy, project_dir),
                "thumbnail_path": rel(thumb, project_dir),
                "size_bytes": source.stat().st_size,
                "status": "ok",
                "error": "",
            })
            rows.append(row)
            info(f"Preparação {index}/{len(sources)}: {media_id} reutilizado · {source.name}")
            write_json(checkpoint_path, {
                "schema_version": 1, "status": "running", "updated_at": now_iso(),
                "completed": index, "total": len(sources), "last_media_id": media_id,
                "media": rows,
            })
            continue

        info(f"Preparação {index}/{len(sources)}: processando {media_id} · {source.name}")
        probe_data = ffprobe(source)
        metadata = parse_probe(source, probe_data)
        taken_at, date_source = capture_time(source, probe_data)
        status = "ok"
        error = ""
        try:
            if not proxy.is_file() or proxy.stat().st_size == 0:
                if kind == "video":
                    create_video_proxy(
                        source, proxy, long_side, proxy_fps,
                        source_duration=float(metadata.get("duration_sec") or 0),
                    )
                else:
                    create_image_proxy(source, proxy)
            if not thumb.is_file() or thumb.stat().st_size == 0:
                create_thumbnail(proxy, thumb, kind, metadata["duration_sec"])
        except Exception as exc:
            status = "error"
            error = str(exc)
            warning(f"{media_id} {source.name}: {exc}")
        try:
            digest = sha256_short(source)
        except OSError as exc:
            digest = ""
            status = "error"
            error = (error + "; " if error else "") + f"leitura do original: {exc}"
        row = {
            "id": media_id,
            "media_type": kind,
            "filename": source.name,
            "source_path": source_relative,
            "relative_album_path": rel(source.parent, originals),
            "extension": source.suffix.lower(),
            "size_bytes": source.stat().st_size,
            "sha256_16": digest,
            "capture_time": taken_at,
            "capture_time_source": date_source,
            **metadata,
            "proxy_path": rel(proxy, project_dir) if proxy.exists() else "",
            "thumbnail_path": rel(thumb, project_dir) if thumb.exists() else "",
            "status": status,
            "error": error,
        }
        row["quality_score"] = media_quality_score(row, answers)
        rows.append(row)
        write_json(checkpoint_path, {
            "schema_version": 1, "status": "running", "updated_at": now_iso(),
            "completed": index, "total": len(sources), "last_media_id": media_id,
            "errors": sum(item.get("status") != "ok" for item in rows),
            "media": rows,
        })
        outcome = "concluído" if status == "ok" else "ignorado com erro"
        info(f"Preparação {index}/{len(sources)}: {media_id} {outcome} · {source.name}")
    source_rows = list(rows)
    rows, local_report = apply_local_analysis(project_dir, rows, answers)
    rows.sort(key=lambda item: (str(item.get("capture_time", "")), normalize_search(item["filename"])))
    for index, row in enumerate(rows, 1):
        row["chronological_index"] = index
    for index, row in enumerate(sorted(rows, key=lambda item: normalize_search(item["filename"])), 1):
        row["alphabetical_index"] = index
    manifest = {
        "schema_version": 3,
        "generated_at": now_iso(),
        "application": f"FR AutoEdite {APP_VERSION}",
        "project": answers["project"],
        "chronology_policy": answers.get("story", {}).get("priority", "Cronologia informada prevalece."),
        "order_mode": answers.get("edition", {}).get("order_mode", "automatico"),
        "summary": {
            "total": len(rows),
            "source_total": len(source_rows),
            "videos": sum(r["media_type"] == "video" for r in rows),
            "images": sum(r["media_type"] == "image" for r in rows),
            "scene_clips": sum(bool(r.get("parent_video")) for r in rows),
            "duplicates_marked": sum(bool(r.get("duplicate")) for r in rows),
            "excluded_from_auto_edit": sum(bool(r.get("excluded_from_auto_edit")) for r in rows),
            "errors": sum(r["status"] != "ok" for r in rows),
            "source_bytes": sum(r["size_bytes"] for r in source_rows),
        },
        "local_analysis": local_report,
        "media": rows,
    }
    write_json(project_dir / "MANIFESTO_MEDIA.json", manifest)
    write_manifest_csv(project_dir / "MANIFESTO_MEDIA.csv", rows)
    create_contact_sheets(project_dir, rows)
    create_master_contact_sheet(project_dir, rows)
    assign_manifest_phases_and_organize(project_dir, rows, answers)
    write_json(project_dir / "MANIFESTO_MEDIA.json", manifest)
    write_manifest_csv(project_dir / "MANIFESTO_MEDIA.csv", rows)
    write_json(checkpoint_path, {
        "schema_version": 1, "status": "complete", "updated_at": now_iso(),
        "completed": len(source_rows), "total": len(source_rows),
        "errors": sum(item.get("status") != "ok" for item in source_rows),
        "media": source_rows,
    })
    return manifest


def write_manifest_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "chronological_index", "alphabetical_index", "quality_score", "sharpness_score", "id", "media_type", "capture_time", "capture_time_source",
        "filename", "relative_album_path", "duration_sec", "width", "height", "fps",
        "has_audio", "source_path", "proxy_path", "thumbnail_path", "parent_video", "scene_start_sec",
        "duplicate", "duplicate_of", "needs_stabilization", "excluded_from_auto_edit", "phase_title", "status", "error"
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".csv.tmp")
    with temp.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(path)


def fit_image(image: Any, size: tuple[int, int]) -> Any:
    from PIL import Image
    canvas = Image.new("RGB", size, "#101713")
    image = image.convert("RGB")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    x = (size[0] - image.width) // 2
    y = (size[1] - image.height) // 2
    canvas.paste(image, (x, y))
    return canvas


def create_contact_sheets(project_dir: Path, rows: list[dict[str, Any]], per_sheet: int = 20) -> None:
    from PIL import Image, ImageDraw, ImageFont
    sheet_dir = project_dir / "contatos_visuais"
    sheet_dir.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype(str(FONTS / "ShareTechMono-Regular.ttf"), 20)
    tile_w, tile_h = 380, 290
    columns = 4
    for sheet_number, start in enumerate(range(0, len(rows), per_sheet), 1):
        batch = rows[start:start + per_sheet]
        lines = math.ceil(len(batch) / columns)
        sheet = Image.new("RGB", (columns * tile_w, lines * tile_h + 70), "#0A2F26")
        draw = ImageDraw.Draw(sheet)
        draw.text((24, 18), f"FR AUTOEDITE  |  CONTATO {sheet_number:02d}", font=font, fill="#E6D6B5")
        for offset, row in enumerate(batch):
            x = (offset % columns) * tile_w
            y = 70 + (offset // columns) * tile_h
            thumb_path = project_dir / row.get("thumbnail_path", "")
            try:
                with Image.open(thumb_path) as opened:
                    tile = fit_image(opened, (360, 240))
            except Exception:
                tile = Image.new("RGB", (360, 240), "#121318")
            sheet.paste(tile, (x + 10, y))
            label = f"{row['id']}  {row['capture_time'][:10]}  {row['media_type'].upper()}"
            draw.text((x + 10, y + 246), label, font=font, fill="#FC7016")
            draw.rectangle((x + 9, y - 1, x + 371, y + 241), outline="#1A6069", width=2)
        sheet.save(sheet_dir / f"CONTATO_{sheet_number:02d}.jpg", quality=90)


def create_master_contact_sheet(project_dir: Path, rows: list[dict[str, Any]]) -> Path:
    """Prancha única compacta para revisão humana ou Copiloto opcional."""
    from PIL import Image, ImageDraw, ImageFont

    approved = [
        row for row in rows
        if row.get("status") == "ok" and row.get("thumbnail_path")
        and not row.get("excluded_from_auto_edit")
    ]
    target = project_dir / "CONTATO_GERAL_CODEX.jpg"
    if not approved:
        return target
    columns = 8
    tile_w, tile_h = 200, 150
    header_h = 66
    lines = math.ceil(len(approved) / columns)
    sheet = Image.new("RGB", (columns * tile_w, header_h + lines * tile_h), "#0A2F26")
    draw = ImageDraw.Draw(sheet)
    title_font = ImageFont.truetype(str(FONTS / "ShareTechMono-Regular.ttf"), 20)
    label_font = ImageFont.truetype(str(FONTS / "ShareTechMono-Regular.ttf"), 13)
    draw.text((20, 18), f"FR AUTOEDITE {APP_VERSION}  |  CONTATO GERAL  |  {len(approved)} MÍDIAS", font=title_font, fill="#E6D6B5")
    for offset, row in enumerate(approved):
        x = (offset % columns) * tile_w
        y = header_h + (offset // columns) * tile_h
        thumb = project_dir / str(row.get("thumbnail_path") or "")
        try:
            with Image.open(thumb) as opened:
                tile = fit_image(opened, (190, 116))
        except Exception:
            tile = Image.new("RGB", (190, 116), "#121318")
        sheet.paste(tile, (x + 5, y + 4))
        marker = "!" if row.get("needs_stabilization") else ""
        parent = "·CENA" if row.get("parent_video") else ""
        draw.text((x + 7, y + 124), f"{row['id']}{parent}{marker}", font=label_font, fill="#FC7016")
        draw.rectangle((x + 4, y + 3, x + 196, y + 121), outline="#1A6069", width=1)
    sheet.save(target, quality=88, optimize=True)
    return target


def phase_score(row: dict[str, Any], phase: dict[str, Any]) -> int:
    haystack = normalize_search(" ".join([
        row.get("filename", ""), row.get("relative_album_path", ""), row.get("source_path", "")
    ]))
    score = 0
    for keyword in phase.get("keywords", []):
        normalized = normalize_search(str(keyword)).strip()
        if normalized and normalized in haystack:
            score += max(2, len(normalized) // 3)
    return score


def media_order_key(row: dict[str, Any], mode: str) -> tuple[Any, ...]:
    if mode == "alfabetico":
        return (int(row.get("alphabetical_index") or 0), normalize_search(row.get("filename", "")))
    return (int(row.get("chronological_index") or 0), normalize_search(row.get("filename", "")))


def ordered_media(rows: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    mode = normalize_order_mode(mode)
    return sorted(rows, key=lambda row: media_order_key(row, mode))


def assign_phases(
    rows: list[dict[str, Any]], phases: list[dict[str, Any]], mode: str = "automatico"
) -> dict[int, list[dict[str, Any]]]:
    """Agrupa sem quebrar a política de ordem escolhida pelo usuário."""
    mode = normalize_order_mode(mode)
    assigned = {index: [] for index in range(len(phases))}
    if mode in {"cronologico", "alfabetico"}:
        sequence = ordered_media(rows, mode)
        total = max(1, len(sequence))
        for index, row in enumerate(sequence):
            phase_index = min(len(phases) - 1, int(index * len(phases) / total))
            assigned[phase_index].append(row)
        return assigned

    unresolved = []
    for row in rows:
        scores = [phase_score(row, phase) for phase in phases]
        best = max(scores) if scores else 0
        if best > 0:
            assigned[scores.index(best)].append(row)
        else:
            unresolved.append(row)
    total = max(1, len(unresolved))
    for index, row in enumerate(ordered_media(unresolved, "cronologico")):
        phase_index = min(len(phases) - 1, int(index * len(phases) / total))
        assigned[phase_index].append(row)
    for batch in assigned.values():
        batch.sort(key=lambda r: media_order_key(r, "cronologico"))
    return assigned


def _safe_media_link(source: Path, destination: Path) -> str:
    """Cria atalho relativo; nunca move, regrava ou apaga a origem."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() or destination.is_symlink():
        return "existing"
    try:
        destination.symlink_to(os.path.relpath(source, destination.parent))
        return "symlink"
    except OSError:
        pointer = destination.with_suffix(destination.suffix + ".FR_LINK.txt")
        write_text(pointer, str(source.resolve()) + "\n")
        return "pointer"


def assign_manifest_phases_and_organize(
    project_dir: Path, rows: list[dict[str, Any]], answers: dict[str, Any]
) -> None:
    phases = sorted(answers.get("story", {}).get("chronology", []), key=lambda item: item.get("order", 0))
    if not phases:
        return
    mode = normalize_order_mode(answers.get("edition", {}).get("order_mode", "automatico"))
    phase_mode = "chronologico" if mode == "aleatorio" else mode
    eligible = [
        row for row in rows
        if row.get("status") == "ok"
        and (not row.get("excluded_from_auto_edit") or row.get("scene_split_parent"))
    ]
    assigned = assign_phases(eligible, phases, phase_mode)
    for phase_index, batch in assigned.items():
        phase = phases[phase_index]
        for row in batch:
            row["phase_order"] = int(phase.get("order", phase_index + 1))
            row["phase_title"] = str(phase.get("title") or f"ETAPA {phase_index + 1}")
            row["phase_assignment"] = (
                "palavras-chave do contexto" if phase_score(row, phase) else f"distribuição {phase_mode}"
            )
    config = answers.get("local_analysis", {})
    if not config.get("organize_by_phase", True) and not config.get("create_selects", True):
        return
    organized = project_dir / "originais_organizados"
    selects = project_dir / "selects"
    minimum_quality = float(config.get("minimum_quality_score", 30))
    link_methods: dict[str, int] = {}
    if config.get("organize_by_phase", True):
        for row in rows:
            if row.get("parent_video"):
                continue
            if row.get("excluded_from_auto_edit") and not row.get("scene_split_parent"):
                phase_folder = "99_IGNORADOS_OU_DUPLICADOS"
            else:
                order = int(row.get("phase_order") or 98)
                title = slugify(str(row.get("phase_title") or "NAO_CLASSIFICADO")).upper().replace("-", "_")
                phase_folder = f"{order:02d}_{title[:54]}"
            media_folder = "VIDEOS" if row.get("media_type") == "video" else "FOTOS"
            source = project_dir / str(row.get("source_path") or "")
            if not source.is_file():
                continue
            destination = organized / phase_folder / media_folder / f"{row['id']}_{source.name}"
            method = _safe_media_link(source, destination)
            link_methods[method] = link_methods.get(method, 0) + 1
    if config.get("create_selects", True):
        for row in rows:
            if row.get("status") != "ok" or row.get("excluded_from_auto_edit"):
                continue
            if float(row.get("quality_score") or 0) < minimum_quality:
                continue
            source = project_dir / str(row.get("proxy_path") or "")
            if not source.is_file():
                continue
            title = slugify(str(row.get("phase_title") or "SELECAO")).upper().replace("-", "_")
            start_label = f"_{float(row.get('scene_start_sec') or 0):07.2f}s" if row.get("parent_video") else ""
            destination = selects / f"{int(row.get('phase_order') or 98):02d}_{title[:38]}" / f"{row['id']}{start_label}_{source.name}"
            method = _safe_media_link(source, destination)
            link_methods[method] = link_methods.get(method, 0) + 1
    guide = """# Originais organizados e selects

- `originais/` é a cópia integral extraída do ZIP e nunca é alterada.
- `originais_organizados/` contém atalhos por etapa; não edite o arquivo pelo atalho.
- `selects/` contém atalhos para proxies aprovados pela análise técnica.
- Duplicatas e alertas são marcações reversíveis no `MANIFESTO_MEDIA.json`; nada é apagado.
- A classificação automática deve ser confirmada visualmente antes da entrega.
"""
    write_text(project_dir / "originais_organizados" / "00_SOMENTE_LEITURA.md", guide)
    write_json(project_dir / "RELATORIO_ORGANIZACAO.json", {"generated_at": now_iso(), "link_methods": link_methods})


def spread_select(rows: list[Any], count: int) -> list[Any]:
    if count <= 0 or not rows:
        return []
    if count >= len(rows):
        return list(rows)
    if count == 1:
        return [rows[len(rows) // 2]]
    indices = []
    for index in range(count):
        position = round(index * (len(rows) - 1) / (count - 1))
        if position not in indices:
            indices.append(position)
    return [rows[index] for index in indices]


def allocate_counts(batches: dict[int, list[dict[str, Any]]], desired: int) -> dict[int, int]:
    non_empty = [index for index, rows in batches.items() if rows]
    allocation = {index: 0 for index in batches}
    if not non_empty or desired <= 0:
        return allocation
    desired = min(desired, sum(len(batches[index]) for index in non_empty))
    for index in spread_select(non_empty, min(desired, len(non_empty))):
        allocation[index] = 1
    remaining = desired - sum(allocation.values())
    while remaining > 0:
        candidates = [
            index for index in non_empty if allocation[index] < len(batches[index])
        ]
        if not candidates:
            break
        selected = max(candidates, key=lambda index: len(batches[index]) - allocation[index])
        allocation[selected] += 1
        remaining -= 1
    return allocation


def project_relative_or_absolute(path: Path, project_dir: Path) -> str:
    try:
        return rel(path, project_dir)
    except ValueError:
        return str(path.resolve())


def configured_external_segment(
    project_dir: Path, answers: dict[str, Any], role: str, phase_order: int,
) -> dict[str, Any] | None:
    """Transforma uma intro/outro enviada em segmento comum, sem tocar no original."""
    config = answers.get("external_intro_outro", {})
    if not config.get(f"{role}_enabled"):
        return None
    raw_path = str(config.get(f"{role}_path") or "").strip()
    if not raw_path:
        warning(f"{role.title()} personalizada ativada, mas nenhum arquivo foi informado.")
        return None
    candidate = expand_path(raw_path) if Path(raw_path).expanduser().is_absolute() else (project_dir / raw_path).resolve()
    suffix = candidate.suffix.lower()
    if not candidate.is_file() or suffix not in VIDEO_EXTENSIONS | IMAGE_EXTENSIONS:
        warning(f"{role.title()} personalizada não encontrada ou incompatível: {candidate}")
        return None
    media_type = "video" if suffix in VIDEO_EXTENSIONS else "image"
    requested_duration = float(config.get(f"{role}_duration_sec") or 4.0)
    source_duration = requested_duration
    source_has_audio = False
    if media_type == "video":
        metadata = parse_probe(candidate, ffprobe(candidate))
        measured = float(metadata.get("duration_sec") or 0)
        if measured > 0:
            source_duration = measured
            requested_duration = min(requested_duration, measured)
        source_has_audio = bool(metadata.get("has_audio"))
    include_in = ["branded"]
    if config.get("include_in_clean_version"):
        include_in.append("clean")
    return {
        "segment_id": "TEMP",
        "type": "media",
        "enabled": True,
        "include_in": include_in,
        "media_id": f"EXTERNAL_{role.upper()}",
        "external_asset": True,
        "external_role": role,
        "include_in_reels": bool(config.get(f"{role}_include_in_reels", True)),
        "source_path": project_relative_or_absolute(candidate, project_dir),
        "proxy_path": project_relative_or_absolute(candidate, project_dir),
        "media_type": media_type,
        "has_audio": source_has_audio and bool(config.get(f"{role}_preserve_audio", True)),
        "start_sec": 0.0,
        "duration_sec": round(max(0.4, requested_duration), 3),
        "source_duration_sec": round(max(requested_duration, source_duration), 3),
        "source_window_start_sec": 0.0,
        "source_window_end_sec": round(max(requested_duration, source_duration), 3),
        "phase_order": phase_order,
        "phase_title": "ABERTURA PERSONALIZADA" if role == "intro" else "ENCERRAMENTO PERSONALIZADO",
        "technical_note": "Arquivo fornecido pelo usuário; conteúdo preservado.",
        "lower_third": False,
        "quality_score": 100,
        "transition": "fade" if role == "intro" else "dissolve",
        "image_animation": "zoom_in" if media_type == "image" else "none",
        "needs_stabilization": False,
        "selection_basis": "intro/outro personalizado",
        "review": "Confirmar duração, áudio e enquadramento no rascunho.",
    }


def renumber_segments(segments: list[dict[str, Any]], start: int = 1) -> list[dict[str, Any]]:
    for index, segment in enumerate(segments, start):
        segment["segment_id"] = f"S{index:04d}"
        segment.setdefault("enabled", True)
    return segments


def apply_opening_closing_features(
    project_dir: Path, answers: dict[str, Any], plan: dict[str, Any],
) -> dict[str, Any]:
    """Insere card de serviço e mídias externas sem alterar a montagem-base."""
    segments = copy.deepcopy(plan.get("segments", []))
    external = answers.get("external_intro_outro", {})
    intro_external = configured_external_segment(project_dir, answers, "intro", -1)
    outro_external = configured_external_segment(project_dir, answers, "outro", 10_000)

    if intro_external:
        if str(external.get("intro_mode") or "before_card") == "replace_card":
            segments = [
                segment for segment in segments
                if not (segment.get("type") == "card" and segment.get("card_kind") == "intro")
            ]
        segments.insert(0, intro_external)

    service_config = answers.get("service_intro", {})
    catalog = load_service_catalog()
    service = catalog.get(str(service_config.get("service_key") or ""))
    if service_config.get("enabled") and service:
        service_card = {
            "segment_id": "TEMP",
            "type": "card",
            "enabled": True,
            "card_kind": "service",
            "service_key": service["key"],
            "service_asset": service.get("asset", ""),
            "include_in": ["branded"],
            "include_in_reels": bool(service_config.get("include_in_reels", True)),
            "duration_sec": round(float(service_config.get("duration_sec") or 3.5), 3),
            "title": str(service_config.get("custom_title") or service.get("label") or "SERVIÇO"),
            "body": str(service_config.get("custom_body") or service.get("body") or ""),
            "phase_order": 0,
            "transition": "dissolve",
            "card_animation": "forge_reveal",
        }
        position = str(service_config.get("position") or "after_intro")
        if position == "before_intro":
            insertion = 0
        else:
            insertion = 0
            for index, segment in enumerate(segments):
                leading = (
                    (segment.get("type") == "card" and segment.get("card_kind") == "intro")
                    or (segment.get("external_asset") and segment.get("external_role") == "intro")
                )
                if leading:
                    insertion = index + 1
                elif insertion:
                    break
        segments.insert(insertion, service_card)

    if outro_external:
        if str(external.get("outro_mode") or "after_card") == "replace_card":
            segments = [
                segment for segment in segments
                if not (segment.get("type") == "card" and segment.get("card_kind") == "outro")
            ]
        segments.append(outro_external)

    plan = copy.deepcopy(plan)
    plan["segments"] = renumber_segments(segments)
    plan["service_intro"] = copy.deepcopy(service_config)
    plan["external_intro_outro"] = copy.deepcopy(external)
    return plan


def editorial_timelapse_ids(
    grouped_media: dict[int, list[dict[str, Any]]], effects: dict[str, Any],
) -> set[str]:
    """Escolhe poucos vídeos longos e fortes, distribuídos entre as etapas."""
    config = effects.get("editorial_timelapse", {})
    if not isinstance(config, dict) or not config.get("enabled"):
        return set()
    minimum = float(config.get("minimum_source_duration_sec") or 18)
    maximum = max(1, int(config.get("max_segments") or 4))

    def eligible(row: dict[str, Any]) -> bool:
        return (
            row.get("media_type") == "video"
            and not row.get("parent_video")
            and float(row.get("duration_sec") or 0) >= minimum
            and bool(row.get("id"))
        )

    def rank(row: dict[str, Any]) -> tuple[float, float, str]:
        return (
            float(row.get("quality_score") or 0),
            min(600.0, float(row.get("duration_sec") or 0)),
            str(row.get("id") or ""),
        )

    selected: list[str] = []
    all_candidates: list[dict[str, Any]] = []
    for phase_index in sorted(grouped_media):
        candidates = sorted(
            (row for row in grouped_media[phase_index] if eligible(row)),
            key=rank, reverse=True,
        )
        all_candidates.extend(candidates)
        if candidates and len(selected) < maximum:
            selected.append(str(candidates[0]["id"]))
    for row in sorted(all_candidates, key=rank, reverse=True):
        media_id = str(row["id"])
        if media_id not in selected:
            selected.append(media_id)
        if len(selected) >= maximum:
            break
    return set(selected[:maximum])


def promote_timelapse_parents(
    grouped_media: dict[int, list[dict[str, Any]]], manifest: dict[str, Any],
    effects: dict[str, Any],
) -> None:
    """Troca alguns clipes virtuais pelo vídeo longo pai para acelerar o processo completo.

    A detecção de cenas normalmente exclui o vídeo longo da montagem e mantém só
    clipes de 3–8 s. Para um time-lapse editorial isso seria contraproducente.
    A promoção é limitada e só acontece quando um clipe daquele mesmo vídeo já
    havia sido selecionado, preservando a pertinência narrativa.
    """
    config = effects.get("editorial_timelapse", {})
    if not isinstance(config, dict) or not config.get("enabled"):
        return
    minimum = float(config.get("minimum_source_duration_sec") or 18)
    maximum = max(1, int(config.get("max_segments") or 4))
    rows = {
        str(row.get("id")): row for row in manifest.get("media", [])
        if isinstance(row, dict) and row.get("id")
    }
    promoted: set[str] = set()
    for phase_index in sorted(grouped_media):
        batch = grouped_media[phase_index]
        for position, row in enumerate(batch):
            parent_id = str(row.get("parent_video") or "")
            parent = rows.get(parent_id)
            if (
                not parent or parent_id in promoted
                or parent.get("media_type") != "video"
                or float(parent.get("duration_sec") or 0) < minimum
                or not parent.get("proxy_path") or not parent.get("source_path")
            ):
                continue
            replacement = copy.deepcopy(parent)
            replacement["promoted_for_editorial_timelapse"] = True
            batch[position] = replacement
            promoted.add(parent_id)
            if len(promoted) >= maximum:
                return


def build_random_plan(
    project_dir: Path, answers: dict[str, Any], manifest: dict[str, Any],
    usable: list[dict[str, Any]], seed_override: int | None = None,
) -> dict[str, Any]:
    edition = answers.get("edition", {})
    config = answers.get("random_mode", {})
    configured_seed = config.get("seed") if seed_override is None else seed_override
    try:
        seed = int(configured_seed) if configured_seed not in (None, "") else int(time.time_ns() % 1_000_000_000)
    except (TypeError, ValueError) as exc:
        raise AutoEditeError("Seed inválida; use um número inteiro ou deixe vazio.") from exc
    rng = random.Random(seed)
    manifest_rows = {str(row.get("id")): row for row in manifest.get("media", [])}
    phases = [
        {"order": 1, "title": "CONCEPÇÃO / DESENVOLVIMENTO", "description": "Ideação, planejamento e base"},
        {"order": 2, "title": "EXECUÇÃO", "description": "Montagem, aplicação e construção"},
        {"order": 3, "title": "DETALHES E ACABAMENTOS", "description": "Precisão, ajustes e finalização"},
    ]
    target = max(10.0, float(edition.get("target_duration_sec", 360)))
    card_duration = max(1.0, float(edition.get("phase_card_duration_sec", 4)))
    minimum = max(1.0, float(config.get("min_clip_duration", 1.5)))
    maximum = max(minimum, float(config.get("max_clip_duration", 8.0)))
    average = max(minimum, min(maximum, float(edition.get("average_clip_duration_sec", 4.5))))
    media_budget = max(3.0, target - card_duration * 5)
    max_segments = max(3, int(edition.get("max_media_segments", 80)))
    desired = min(len(usable), max_segments, max(3, round(media_budget / average)))
    prefer_video = min(1.0, max(0.0, float(config.get("prefer_video_over_image", 0.7))))
    videos = [row for row in usable if row.get("media_type") == "video"]
    images = [row for row in usable if row.get("media_type") == "image"]
    rng.shuffle(videos)
    rng.shuffle(images)
    desired_videos = min(len(videos), round(desired * prefer_video))
    selected = videos[:desired_videos] + images[:max(0, desired - desired_videos)]
    if len(selected) < desired:
        remaining = [row for row in usable if row not in selected]
        rng.shuffle(remaining)
        selected += remaining[:desired - len(selected)]
    if config.get("shuffle_media", True):
        rng.shuffle(selected)
    assigned: dict[int, list[dict[str, Any]]] = {0: [], 1: [], 2: []}
    if len(selected) >= 3:
        for phase_index, row in enumerate(selected[:3]):
            assigned[phase_index].append(row)
        selected = selected[3:]
    weights = [rng.uniform(0.65, 1.45) for _ in phases]
    for row in selected:
        assigned[rng.choices(range(3), weights=weights, k=1)[0]].append(row)
    effects = answers.get("visual_effects", {})
    timelapse_config = effects.get("editorial_timelapse", {})
    promote_timelapse_parents(assigned, manifest, effects)
    timelapse_media = editorial_timelapse_ids(assigned, effects)
    timelapse_speed = float(timelapse_config.get("speed_factor") or 6)
    timelapse_output = float(timelapse_config.get("output_duration_sec") or 4)
    transitions = [
        value for value in effects.get("transitions", [])
        if value in TRANSITION_MAP
    ] or [str(edition.get("transition") or "fade")]
    context = answers.get("context", {})
    segments: list[dict[str, Any]] = [{
        "segment_id": "S0001", "type": "card", "card_kind": "intro",
        "include_in": ["branded"], "duration_sec": card_duration + 1,
        "title": answers["project"]["name"].upper(), "body": "Registro visual do processo",
        "phase_order": 0, "transition": "fade",
    }]
    next_id = 2
    for phase_index, phase in enumerate(phases):
        segments.append({
            "segment_id": f"S{next_id:04d}", "type": "card", "card_kind": "phase",
            "include_in": ["branded"], "duration_sec": card_duration,
            "title": phase["title"], "body": phase["description"],
            "phase_order": phase["order"], "transition": "fade",
        })
        next_id += 1
        batch = list(assigned[phase_index])
        if config.get("shuffle_media", True):
            rng.shuffle(batch)
        for media_index, row in enumerate(batch):
            if row.get("media_type") == "image":
                start = 0.0
                duration = 3.0
                animation = rng.choice(["zoom_in", "zoom_out"]) if rng.random() < 0.5 else "none"
            else:
                source_duration = max(0.0, float(row.get("duration_sec") or 0))
                is_timelapse = str(row.get("id")) in timelapse_media
                if is_timelapse:
                    duration = min(timelapse_output, source_duration / timelapse_speed)
                    duration = max(0.2, duration)
                    source_span = duration * timelapse_speed
                else:
                    duration = min(source_duration or maximum, rng.uniform(minimum, maximum))
                    duration = max(minimum if source_duration >= minimum else source_duration, duration)
                    source_span = duration
                base_start = max(0.0, float(row.get("scene_start_sec") or 0))
                available = max(0.0, source_duration - source_span)
                region = rng.choice(("inicio", "meio", "fim"))
                if region == "inicio":
                    relative = rng.uniform(0, available * 0.30) if available else 0.0
                elif region == "meio":
                    relative = rng.uniform(available * 0.25, available * 0.75) if available else 0.0
                else:
                    relative = rng.uniform(available * 0.70, available) if available else 0.0
                start = base_start + relative
                animation = "none"
            transition = rng.choice(transitions)
            segments.append({
                "segment_id": f"S{next_id:04d}", "type": "media",
                "include_in": ["branded", "clean"], "media_id": row["id"],
                "source_path": row["source_path"], "proxy_path": row["proxy_path"],
                "media_type": row["media_type"], "has_audio": row.get("has_audio", False),
                "start_sec": round(start, 3), "duration_sec": round(max(0.2, duration), 3),
                "source_duration_sec": round(float(
                    manifest_rows.get(str(row.get("parent_video")), row).get("duration_sec") or duration
                ), 3),
                "source_window_start_sec": round(float(row.get("scene_start_sec") or 0), 3),
                "source_window_end_sec": round(float(
                    row.get("scene_end_sec") or row.get("duration_sec") or duration
                ), 3),
                "phase_order": phase["order"], "phase_title": phase["title"],
                "technical_note": phase["description"], "lower_third": media_index == 0,
                "quality_score": row.get("quality_score", 0), "transition": transition,
                "image_animation": animation, "needs_stabilization": row.get("needs_stabilization", False),
                "editorial_timelapse": bool(row.get("media_type") == "video" and str(row.get("id")) in timelapse_media),
                "playback_speed": round(timelapse_speed, 3) if str(row.get("id")) in timelapse_media else 1.0,
                "selection_basis": f"modo aleatório reproduzível; seed {seed}",
                "review": "Confirmar conteúdo visual; o modo aleatório ignora a narrativa do contexto.",
            })
            next_id += 1
    segments.append({
        "segment_id": f"S{next_id:04d}", "type": "card", "card_kind": "outro",
        "include_in": ["branded"], "duration_sec": card_duration + 1,
        "title": "ENTREGA", "body": context.get("cta") or "Projeto concluído — por Franco Romeu",
        "phase_order": 4, "transition": "fade",
    })
    plan = {
        "schema_version": 3, "generated_at": now_iso(),
        "application": f"FR AutoEdite {APP_VERSION}", "project": answers["project"],
        "context": context, "order_mode": "aleatorio", "random_seed": seed,
        "narrative_priority": "Modo aleatório: contexto semântico ignorado; cards universais.",
        "output": {
            "width": resolve_output_dimensions(edition, usable)[0],
            "height": resolve_output_dimensions(edition, usable)[1],
            "fps": int(edition.get("fps", 24)), "video_codec": "libx264", "audio_codec": "aac",
            "pixel_format": "yuv420p", "render_source": edition.get("render_source", "originals"),
            "quality_preset": edition.get("quality_preset", "custom"),
        },
        "versions": {
            "branded": bool(edition.get("create_branded_version", True)),
            "clean": bool(edition.get("create_clean_version", True)),
        },
        "audio": {
            "preserve_original": bool(edition.get("preserve_original_audio", True)),
            "music_path": edition.get("music_path", ""), "music_volume": float(edition.get("music_volume", 0.1)),
            **answers.get("audio_design", {}),
        },
        "visual_effects": answers.get("visual_effects", {}),
        "export_quality": answers.get("export_quality", {}),
        "review_status": "RANDOM_DRAFT_REQUIRES_VISUAL_REVIEW",
        "card_style_path": "CARD_STYLE.json", "social": answers.get("social", {}), "segments": segments,
    }
    plan = apply_opening_closing_features(project_dir, answers, plan)
    write_json(project_dir / "EDIT_PLAN_AUTO.json", plan)
    write_json(project_dir / "EDIT_PLAN.json", plan)
    info(f"Modo aleatório: seed {seed}. Use esta seed para reproduzir a montagem.")
    return plan


def build_auto_plan(project_dir: Path, answers: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    answers = normalize_answers(answers)
    edition = answers.get("edition", {})
    order_mode = normalize_order_mode(edition.get("order_mode", "automatico"))
    usable = [
        r for r in manifest["media"]
        if r.get("status") == "ok" and r.get("proxy_path") and not r.get("excluded_from_auto_edit")
    ]
    if not usable:
        raise AutoEditeError("Nenhuma mídia válida para montar o plano.")
    if order_mode == "aleatorio":
        return build_random_plan(project_dir, answers, manifest, usable)
    manifest_rows = {str(row.get("id")): row for row in manifest.get("media", [])}
    phases = sorted(answers.get("story", {}).get("chronology", []), key=lambda p: p.get("order", 0))
    if not phases:
        raise AutoEditeError("O questionário precisa ter pelo menos uma etapa de cronologia.")
    assigned = assign_phases(usable, phases, order_mode)
    target = float(edition.get("target_duration_sec", 360))
    card_duration = float(edition.get("phase_card_duration_sec", 4))
    media_budget = max(float(len(phases)), target - card_duration * (len(phases) + 2))
    average_clip = max(1.0, float(edition.get("average_clip_duration_sec", 6)))
    max_segments = max(1, int(edition.get("max_media_segments", 80)))
    desired_count = min(len(usable), max_segments, max(len(phases), round(media_budget / average_clip)))
    allocation = allocate_counts(assigned, desired_count)
    selected_by_phase: dict[int, list[dict[str, Any]]] = {}
    for phase_index, batch in assigned.items():
        count = allocation.get(phase_index, 0)
        if order_mode == "automatico":
            ranked = sorted(
                batch,
                key=lambda row: (
                    phase_score(row, phases[phase_index]),
                    float(row.get("quality_score") or 0),
                    row.get("media_type") == "video",
                ),
                reverse=True,
            )[:count]
            selected_by_phase[phase_index] = sorted(ranked, key=lambda row: media_order_key(row, "cronologico"))
        else:
            selected_by_phase[phase_index] = spread_select(batch, count)
    effects = answers.get("visual_effects", {})
    timelapse_config = effects.get("editorial_timelapse", {})
    promote_timelapse_parents(selected_by_phase, manifest, effects)
    timelapse_media = editorial_timelapse_ids(selected_by_phase, effects)
    timelapse_speed = float(timelapse_config.get("speed_factor") or 6)
    timelapse_output = float(timelapse_config.get("output_duration_sec") or 4)
    selected_total = sum(len(rows) for rows in selected_by_phase.values())
    unit = media_budget / max(1, selected_total)
    max_video = float(edition.get("max_video_excerpt_sec", 14))
    still_duration = float(edition.get("still_duration_sec", 4))
    transition_options = [
        value for value in effects.get("transitions", [])
        if value in TRANSITION_MAP
    ] or [str(edition.get("transition") or "fade")]
    context = answers.get("context", {})
    segments: list[dict[str, Any]] = []
    segments.append({
        "segment_id": "S0001", "type": "card", "card_kind": "intro",
        "include_in": ["branded"], "duration_sec": card_duration + 1,
        "title": answers["project"]["name"].upper(),
        "body": context.get("summary") or answers.get("story", {}).get("objective", "Transformação completa."),
        "phase_order": 0,
    })
    next_id = 2
    for phase_index, phase in enumerate(phases):
        segments.append({
            "segment_id": f"S{next_id:04d}", "type": "card", "card_kind": "phase",
            "include_in": ["branded"], "duration_sec": card_duration,
            "title": phase.get("title", f"ETAPA {phase_index + 1}"),
            "body": phase.get("description", ""), "phase_order": phase.get("order", phase_index + 1),
        })
        next_id += 1
        batch = selected_by_phase.get(phase_index, [])
        for media_index, row in enumerate(batch):
            if row["media_type"] == "image":
                duration = min(still_duration, max(1.5, unit * 0.90))
                start = 0.0
            else:
                source_duration = max(0.0, float(row.get("duration_sec") or 0))
                is_timelapse = str(row.get("id")) in timelapse_media
                if is_timelapse:
                    duration = max(0.2, min(timelapse_output, source_duration / timelapse_speed))
                    source_span = duration * timelapse_speed
                else:
                    duration = min(max_video, max(1.8, unit * 1.05))
                    if source_duration:
                        duration = min(duration, source_duration)
                    source_span = duration
                final_phase = phase_index == len(phases) - 1
                if final_phase and source_duration > source_span + 1:
                    start = max(0.0, source_duration - source_span - 0.75)
                elif source_duration > source_span + 1:
                    position = 0.08 + 0.16 * ((media_index % 4) / 3)
                    start = min(source_duration - source_span, source_duration * position)
                else:
                    start = 0.0
                start += max(0.0, float(row.get("scene_start_sec") or 0))
            segments.append({
                "segment_id": f"S{next_id:04d}", "type": "media",
                "include_in": ["branded", "clean"], "media_id": row["id"],
                "source_path": row["source_path"], "proxy_path": row["proxy_path"],
                "media_type": row["media_type"], "has_audio": row.get("has_audio", False),
                "start_sec": round(start, 3), "duration_sec": round(duration, 3),
                "source_duration_sec": round(float(
                    manifest_rows.get(str(row.get("parent_video")), row).get("duration_sec") or duration
                ), 3),
                "source_window_start_sec": round(float(row.get("scene_start_sec") or 0), 3),
                "source_window_end_sec": round(float(
                    row.get("scene_end_sec") or row.get("duration_sec") or duration
                ), 3),
                "phase_order": phase.get("order", phase_index + 1),
                "phase_title": phase.get("title", ""),
                "technical_note": phase.get("description", ""),
                "lower_third": media_index == 0,
                "quality_score": row.get("quality_score", 0),
                "transition": transition_options[media_index % len(transition_options)],
                "image_animation": (
                    "zoom_in" if row["media_type"] == "image" and effects.get("ken_burns_on_images")
                    else "none"
                ),
                "needs_stabilization": row.get("needs_stabilization", False),
                "editorial_timelapse": bool(row.get("media_type") == "video" and str(row.get("id")) in timelapse_media),
                "playback_speed": round(timelapse_speed, 3) if str(row.get("id")) in timelapse_media else 1.0,
                "selection_basis": (
                    "palavras-chave + qualidade técnica" if order_mode == "automatico" and phase_score(row, phase)
                    else f"ordem {order_mode} + amostragem distribuída"
                ),
                "review": "Confirmar conteúdo visual e ajustar start_sec/duration_sec no EDIT_PLAN.json.",
            })
            next_id += 1
    segments.append({
        "segment_id": f"S{next_id:04d}", "type": "card", "card_kind": "outro",
        "include_in": ["branded"], "duration_sec": card_duration + 1,
        "title": "PROJETO · EXECUÇÃO · RESULTADO",
        "body": context.get("cta") or "Franco Romeu — arte + engenharia.",
        "phase_order": len(phases) + 1,
    })
    plan = {
        "schema_version": 3,
        "generated_at": now_iso(),
        "application": f"FR AutoEdite {APP_VERSION}",
        "project": answers["project"],
        "context": context,
        "order_mode": order_mode,
        "narrative_priority": answers.get("story", {}).get("priority"),
        "output": {
            "width": resolve_output_dimensions(edition, usable)[0],
            "height": resolve_output_dimensions(edition, usable)[1],
            "fps": int(edition.get("fps", 24)),
            "video_codec": "libx264",
            "audio_codec": "aac",
            "pixel_format": "yuv420p",
            "render_source": edition.get("render_source", "originals"),
            "quality_preset": edition.get("quality_preset", "custom"),
        },
        "versions": {
            "branded": bool(edition.get("create_branded_version", True)),
            "clean": bool(edition.get("create_clean_version", True)),
        },
        "audio": {
            "preserve_original": bool(edition.get("preserve_original_audio", True)),
            "music_path": edition.get("music_path", ""),
            "music_volume": float(edition.get("music_volume", 0.1)),
            **answers.get("audio_design", {}),
        },
        "visual_effects": answers.get("visual_effects", {}),
        "export_quality": answers.get("export_quality", {}),
        "review_status": "AUTO_DRAFT_REQUIRES_VISUAL_REVIEW",
        "card_style_path": "CARD_STYLE.json",
        "social": answers.get("social", {}),
        "segments": segments,
    }
    plan = apply_opening_closing_features(project_dir, answers, plan)
    write_json(project_dir / "EDIT_PLAN_AUTO.json", plan)
    write_json(project_dir / "EDIT_PLAN.json", plan)
    return plan


def apply_copilot_selection(
    project_dir: Path, answers: dict[str, Any], manifest: dict[str, Any],
    base_plan: dict[str, Any], curation: dict[str, Any], *, apply_now: bool,
) -> dict[str, Any]:
    rows = {row.get("id"): row for row in manifest.get("media", [])}
    cards = [segment for segment in base_plan.get("segments", []) if segment.get("type") == "card"]
    intro = [segment for segment in cards if segment.get("card_kind") == "intro"]
    outro = [segment for segment in cards if segment.get("card_kind") == "outro"]
    phase_cards = {int(segment.get("phase_order") or 0): segment for segment in cards if segment.get("card_kind") == "phase"}
    transitions = answers.get("visual_effects", {}).get("transitions", []) or ["fade"]
    segments: list[dict[str, Any]] = copy.deepcopy(intro)
    next_id = len(segments) + 1
    grouped: dict[int, list[dict[str, Any]]] = {}
    for selected in curation.get("selections", []):
        grouped.setdefault(int(selected.get("phase_order") or 1), []).append(selected)
    for phase_order in sorted(grouped):
        card = copy.deepcopy(phase_cards.get(phase_order))
        if card:
            card["segment_id"] = f"S{next_id:04d}"
            segments.append(card)
            next_id += 1
        for media_index, selected in enumerate(grouped[phase_order]):
            row = rows.get(selected.get("media_id"))
            if not row:
                continue
            start = float(selected.get("start_sec") or 0)
            if row.get("parent_video"):
                start += float(row.get("scene_start_sec") or 0)
            segments.append({
                "segment_id": f"S{next_id:04d}", "type": "media",
                "include_in": ["branded", "clean"], "media_id": row["id"],
                "source_path": row["source_path"], "proxy_path": row["proxy_path"],
                "media_type": row["media_type"], "has_audio": row.get("has_audio", False),
                "start_sec": round(start, 3),
                "duration_sec": round(float(selected.get("duration_sec") or 3), 3),
                "source_duration_sec": round(float(
                    rows.get(str(row.get("parent_video")), row).get("duration_sec")
                    or selected.get("duration_sec") or 3
                ), 3),
                "source_window_start_sec": round(float(row.get("scene_start_sec") or 0), 3),
                "source_window_end_sec": round(float(
                    row.get("scene_end_sec") or row.get("duration_sec") or selected.get("duration_sec") or 3
                ), 3),
                "phase_order": phase_order,
                "phase_title": row.get("phase_title") or f"ETAPA {phase_order}",
                "technical_note": str(selected.get("reason") or "Curadoria visual opcional"),
                "lower_third": media_index == 0, "quality_score": row.get("quality_score", 0),
                "transition": transitions[media_index % len(transitions)],
                "image_animation": "zoom_in" if row.get("media_type") == "image" else "none",
                "needs_stabilization": row.get("needs_stabilization", False),
                "selection_basis": f"Copiloto {curation.get('provider', 'IA')} + validação local",
                "review": "A seleção da IA precisa de aprovação humana antes da master.",
            })
            next_id += 1
    for card in outro:
        copied = copy.deepcopy(card)
        copied["segment_id"] = f"S{next_id:04d}"
        segments.append(copied)
        next_id += 1
    suggested = copy.deepcopy(base_plan)
    suggested["segments"] = segments
    suggested["copilot_curation"] = {
        "provider": curation.get("provider"), "summary": curation.get("summary"),
        "warnings": curation.get("warnings", []), "auto_applied": bool(apply_now),
    }
    suggested["review_status"] = "COPILOT_SUGGESTION_REQUIRES_HUMAN_APPROVAL"
    suggested = apply_opening_closing_features(project_dir, answers, suggested)
    write_json(project_dir / "EDIT_PLAN_COPILOT_SUGERIDO.json", suggested)
    if apply_now:
        write_json(project_dir / "EDIT_PLAN.json", suggested)
        info("Curadoria do Copiloto aplicada; confirme a timeline antes de renderizar.")
    else:
        info("Curadoria do Copiloto salva como sugestão; o plano local foi preservado.")
    return suggested


def run_optional_copilot(
    project_dir: Path, answers: dict[str, Any], manifest: dict[str, Any],
    base_plan: dict[str, Any], *, force_apply: bool | None = None,
) -> dict[str, Any]:
    config = answers.get("ai_copilot", {})
    if not config.get("enabled"):
        return base_plan
    report = {"enabled": True, "provider": config.get("provider", "openai"), "status": "fallback_local"}
    try:
        from copilot import CopilotError, CopilotManager

        board = project_dir / "CONTATO_GERAL_CODEX.jpg"
        if not board.is_file():
            raise CopilotError("Prancha geral não encontrada.")
        source_text, _ = context_source_text(answers)
        context = source_text or json.dumps(answers.get("context", {}), ensure_ascii=False)
        strategy_path = APP_ROOT / "knowledge" / "FRANCO_ROMEU_MENTE_ESTRATEGICA_LLM_MASTER_v1.1.md"
        strategy = strategy_path.read_text(encoding="utf-8", errors="replace") if strategy_path.is_file() else "Verdade factual, método, técnica e identidade Franco Romeu."
        manager = CopilotManager(project_dir, config)
        curation = manager.curate(
            board, context, manifest, strategy,
            use_cache=bool(config.get("use_cache", True)),
        )
        apply_now = bool(config.get("auto_apply", False)) if force_apply is None else force_apply
        result = apply_copilot_selection(project_dir, answers, manifest, base_plan, curation, apply_now=apply_now)
        report.update({"status": "succeeded", "selected": len(curation.get("selections", [])), "applied": apply_now})
        write_json(project_dir / "RELATORIO_COPILOTO.json", report)
        return result if apply_now else base_plan
    except Exception as exc:
        report["error"] = str(exc)
        write_json(project_dir / "RELATORIO_COPILOTO.json", report)
        warning(f"Copiloto indisponível. Usando modo local avançado: {exc}")
        return base_plan


def load_brand() -> dict[str, Any]:
    return read_json(TEMPLATES / "fr_brand_profile.json")


def load_card_style(project_dir: Path | None = None) -> dict[str, Any]:
    default = read_json(TEMPLATES / "card_style.json")
    result = default
    if project_dir:
        custom = project_dir / "CARD_STYLE.json"
        if custom.is_file():
            result = deep_merge(default, read_json(custom))
    for name, value in result.get("palette", {}).items():
        if not re.fullmatch(r"#?[0-9A-Fa-f]{6}", str(value)):
            raise AutoEditeError(f"Cor inválida em CARD_STYLE.json: palette.{name} = {value}")
    for role, filename in result.get("fonts", {}).items():
        if not (FONTS / str(filename)).is_file():
            raise AutoEditeError(f"Fonte não encontrada para cards ({role}): {filename}")
    return result


def sync_card_style_from_answers(
    project_dir: Path, answers: dict[str, Any], *, repair_invalid: bool = False, persist: bool = True,
) -> dict[str, Any]:
    """Aplica no arquivo editável somente as escolhas feitas na auditoria."""
    try:
        style = load_card_style(project_dir)
    except AutoEditeError as exc:
        custom = project_dir / "CARD_STYLE.json"
        if not repair_invalid or not custom.is_file():
            raise
        history = project_dir / "_HISTORICO"
        history.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup = history / f"CARD_STYLE_INVALIDO_{stamp}.json"
        custom.replace(backup)
        warning(
            f"O design anterior era incompatível ({exc}). Ele foi preservado em {backup.name}; "
            "o Studio reconstruiu o CARD_STYLE.json pelas opções atuais."
        )
        style = load_card_style()
    cards = answers.get("cards", {})
    effects = answers.get("visual_effects", {})
    preset_name = str(cards.get("style_preset") or style.get("preset") or "site_fr_luxo")
    preset = CARD_PRESETS.get(preset_name, CARD_PRESETS["site_fr_luxo"])
    style["preset"] = preset_name if preset_name in CARD_PRESETS else "site_fr_luxo"
    style.setdefault("palette", {}).update(preset["palette"])
    style.setdefault("orange_details", {}).update(preset["details"])
    palette_overrides = cards.get("palette_overrides", {})
    if isinstance(palette_overrides, dict):
        style["palette"].update({key: value for key, value in palette_overrides.items() if value})
    style.setdefault("logo", {}).update({
        "persistent_on_branded_video": bool(cards.get("persistent_logo", True)),
        "persistent_on_cards": bool(cards.get("persistent_logo", True)),
    })
    show_contacts = bool(cards.get("show_contacts", True))
    overlay = style.setdefault("persistent_overlay", {})
    overlay["show_instagram"] = show_contacts
    overlay["enabled"] = bool(cards.get("persistent_bubble", True))
    brief = answers.get("editing_brief", {})
    overlay.update({
        "title_font": str(brief.get("overlay_title_font") or "StardosStencil-Bold.ttf"),
        "body_font": str(brief.get("overlay_body_font") or "Rokkitt-Regular.ttf"),
        "technical_font": str(brief.get("overlay_technical_font") or "ShareTechMono-Regular.ttf"),
        "logo_alignment": "bubble_center",
        "logo_without_bubble": True,
    })
    style.setdefault("cards", {}).update({
        "layout": str(cards.get("layout") or "editorial"),
        "bubble_style": str(cards.get("bubble_style") or "glass"),
        "animation": str(cards.get("animation") or "soft_zoom"),
        "intro_animation": str(cards.get("intro_animation") or "forge_reveal"),
        "outro_animation": str(cards.get("outro_animation") or "soft_zoom"),
        "service_animation": str(cards.get("service_animation") or "forge_reveal"),
        "show_contact_icons": bool(cards.get("show_contact_icons", True)),
        "show_site": bool(cards.get("show_site", True)),
        "show_pinterest": bool(cards.get("show_pinterest", True)),
        "show_contacts_on_every_card": show_contacts,
        "show_full_contacts_on_outro": show_contacts,
        "qr_code_on_outro": bool(cards.get("qr_code_on_outro", False)),
        "qr_code_target": str(cards.get("qr_code_target") or "https://wa.me/5511990021603"),
    })
    style["color_lut"] = str(effects.get("color_lut") or "").strip()
    if persist:
        write_json(project_dir / "CARD_STYLE.json", style)
    return style


def style_signature(brand: dict[str, Any], style: dict[str, Any], project_dir: Path) -> str:
    logo = logo_path_for(project_dir, style)
    payload = json.dumps({"brand": brand, "style": style}, ensure_ascii=False, sort_keys=True).encode("utf-8")
    digest = hashlib.sha256(payload)
    if logo.is_file():
        digest.update(sha256_short(logo).encode("ascii"))
    return digest.hexdigest()[:12]


def color_hex(value: str) -> str:
    return value if value.startswith("#") else "#" + value


def font(name: str, size: int) -> Any:
    from PIL import ImageFont
    return ImageFont.truetype(str(FONTS / name), max(8, size))


def wrap_pixel(draw: Any, text: str, selected_font: Any, width: int) -> list[str]:
    words = str(text).split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        box = draw.textbbox((0, 0), candidate, font=selected_font)
        if current and box[2] - box[0] > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


def paste_logo_at(
    canvas: Any, logo_path: Path, max_width: int, max_height: int,
    xy: tuple[int, int], anchor: str = "mm", opacity: int = 255
) -> None:
    from PIL import Image
    if not logo_path.is_file():
        return
    with Image.open(logo_path) as opened:
        logo = opened.convert("RGBA")
    logo.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
    if opacity < 255:
        alpha = logo.getchannel("A").point(lambda value: int(value * opacity / 255))
        logo.putalpha(alpha)
    x, y = xy
    if anchor == "mm":
        x -= logo.width // 2
        y -= logo.height // 2
    elif anchor == "ra":
        x -= logo.width
    elif anchor == "rm":
        x -= logo.width
        y -= logo.height // 2
    elif anchor == "ma":
        x -= logo.width // 2
    canvas.alpha_composite(logo, (int(x), int(y)))


def paste_optional_qr(canvas: Any, target: str, size: int, xy: tuple[int, int]) -> bool:
    """Gera QR local se qrencode ou o módulo qrcode estiver disponível."""
    from PIL import Image

    if not target.strip():
        return False
    temporary_dir = Path(tempfile.mkdtemp(prefix="fr-qr-"))
    png = temporary_dir / "qr.png"
    try:
        if shutil.which("qrencode"):
            result = run(
                ["qrencode", "-o", str(png), "-s", "8", "-m", "2", target],
                capture=True,
                check=False,
            )
            if result.returncode != 0:
                png.unlink(missing_ok=True)
        if not png.is_file():
            try:
                import qrcode  # type: ignore

                qrcode.make(target).save(png)
            except ImportError:
                return False
        with Image.open(png) as opened:
            qr = opened.convert("RGB").resize((size, size), Image.Resampling.NEAREST).convert("RGBA")
        x, y = xy
        canvas.alpha_composite(qr, (int(x), int(y)))
        return True
    finally:
        shutil.rmtree(temporary_dir, ignore_errors=True)


def logo_path_for(project_dir: Path | None = None, style: dict[str, Any] | None = None) -> Path:
    configured = str((style or {}).get("logo", {}).get("file") or "franco-romeu-logo.png")
    candidate = Path(os.path.expanduser(configured))
    if candidate.is_absolute() and candidate.is_file():
        return candidate
    if project_dir and (project_dir / configured).is_file():
        return project_dir / configured
    if (ASSETS / configured).is_file():
        return ASSETS / configured
    if project_dir and (project_dir / "franco-romeu-logo.png").is_file():
        return project_dir / "franco-romeu-logo.png"
    return ASSETS / "franco-romeu-logo.png"


def draw_hollow_centered(
    draw: Any, text: str, y: int, max_width: int, canvas_width: int,
    base_color: str, stroke_color: str, font_name: str = "StardosStencil-Bold.ttf"
) -> int:
    size = max(30, canvas_width // 12)
    while size > 20:
        selected = font(font_name, size)
        lines = wrap_pixel(draw, text, selected, max_width)
        widest = max(draw.textbbox((0, 0), line, font=selected)[2] for line in lines)
        if widest <= max_width and len(lines) <= 4:
            break
        size -= 2
    line_height = int(size * 1.15)
    for line in lines:
        box = draw.textbbox((0, 0), line, font=selected, stroke_width=max(1, size // 18))
        width = box[2] - box[0]
        draw.text(
            ((canvas_width - width) // 2, y), line, font=selected,
            fill=base_color, stroke_width=max(1, size // 18), stroke_fill=stroke_color
        )
        y += line_height
    return y


def draw_contact_icon(draw: Any, kind: str, box: tuple[int, int, int, int], color: str) -> None:
    """Ícones vetoriais simples, legíveis e independentes de fonte externa."""
    x0, y0, x1, y1 = box
    size = min(x1 - x0, y1 - y0)
    weight = max(1, size // 10)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    if kind == "instagram":
        inset = max(1, size // 8)
        draw.rounded_rectangle((x0 + inset, y0 + inset, x1 - inset, y1 - inset), radius=size // 4, outline=color, width=weight)
        r = size // 5
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color, width=weight)
        dot = max(1, size // 13)
        draw.ellipse((x1 - size // 3, y0 + size // 4, x1 - size // 3 + dot * 2, y0 + size // 4 + dot * 2), fill=color)
    elif kind == "whatsapp":
        inset = max(1, size // 10)
        draw.ellipse((x0 + inset, y0 + inset, x1 - inset, y1 - inset), outline=color, width=weight)
        draw.polygon(((x0 + size // 4, y1 - size // 4), (x0 + size // 6, y1), (x0 + size // 2, y1 - size // 7)), fill=color)
        draw.arc((x0 + size // 3, y0 + size // 4, x1 - size // 5, y1 - size // 4), 115, 255, fill=color, width=weight)
    elif kind == "pinterest":
        pfont = font("Rokkitt-Bold.ttf", max(12, int(size * 0.82)))
        bbox = draw.textbbox((0, 0), "P", font=pfont)
        draw.text((cx - (bbox[2] - bbox[0]) // 2, cy - (bbox[3] - bbox[1]) // 2 - bbox[1]), "P", font=pfont, fill=color)
    else:
        inset = max(1, size // 10)
        draw.ellipse((x0 + inset, y0 + inset, x1 - inset, y1 - inset), outline=color, width=weight)
        draw.arc((cx - size // 6, y0 + inset, cx + size // 6, y1 - inset), 90, 270, fill=color, width=weight)
        draw.arc((cx - size // 6, y0 + inset, cx + size // 6, y1 - inset), 270, 90, fill=color, width=weight)
        draw.line((x0 + inset, cy, x1 - inset, cy), fill=color, width=weight)


def draw_contact_chips(
    draw: Any, items: list[tuple[str, str]], y: int, canvas_width: int, margin: int,
    chip_font: Any, surface: str, bone: str, orange: str, gold: str, bubble_style: str,
) -> int:
    # Em rascunhos 360 px, quatro contatos ainda precisam caber acima da
    # assinatura. Em Full HD os mesmos cálculos crescem de forma proporcional.
    gap = max(5, canvas_width // 120)
    icon_size = max(16, canvas_width // 36)
    chip_h = max(icon_size + gap, int(chip_font.size * 1.75))
    widths = []
    for _, label in items:
        bbox = draw.textbbox((0, 0), label, font=chip_font)
        widths.append(icon_size + (bbox[2] - bbox[0]) + gap * 3)
    rows: list[list[tuple[int, tuple[str, str]]]] = [[]]
    used = 0
    max_width = canvas_width - margin * 2
    for item, width in zip(items, widths):
        if rows[-1] and used + gap + width > max_width:
            rows.append([])
            used = 0
        rows[-1].append((width, item))
        used += width + (gap if rows[-1][:-1] else 0)
    for row in rows:
        row_width = sum(width for width, _ in row) + gap * max(0, len(row) - 1)
        x = (canvas_width - row_width) // 2
        for width, (kind, label) in row:
            box = (x, y, x + width, y + chip_h)
            if bubble_style == "solid":
                fill, outline = (*hex_rgb(surface), 255), None
            elif bubble_style == "outline":
                fill, outline = None, (*hex_rgb(orange), 230)
            elif bubble_style == "minimal":
                fill, outline = None, None
            else:
                fill, outline = (*hex_rgb(surface), 188), (*hex_rgb(gold), 145)
            if fill or outline:
                draw.rounded_rectangle(box, radius=chip_h // 2, fill=fill, outline=outline, width=max(1, canvas_width // 420))
            icon_box = (x + gap, y + (chip_h - icon_size) // 2, x + gap + icon_size, y + (chip_h + icon_size) // 2)
            draw_contact_icon(draw, kind, icon_box, orange if kind != "whatsapp" else "#25D366")
            draw.text((x + icon_size + gap * 2, y + (chip_h - chip_font.size) // 2 - 1), label, font=chip_font, fill=bone)
            x += width + gap
        y += chip_h + gap
    return y


def paste_service_symbol(
    canvas: Any, asset_path: Path, center: tuple[int, int], size: int,
    orange: str, gold: str, border: str,
) -> bool:
    """Integra o medalhão de serviço num círculo matematicamente perfeito.

    Os anexos são quadrados. A versão anterior os recortava para um retângulo
    antes da máscara circular, deformando visualmente o medalhão em uma oval.
    Aqui a imagem é ajustada primeiro a um quadrado e só depois recebe a máscara.
    """
    from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

    if not asset_path.is_file():
        return False
    try:
        with Image.open(asset_path) as opened:
            source = ImageOps.exif_transpose(opened).convert("RGBA")
        plate = ImageOps.fit(
            source, (size, size), method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )
        mask = Image.new("L", (size, size), 0)
        mask_draw = ImageDraw.Draw(mask)
        inset = max(1, size // 160)
        mask_draw.ellipse((inset, inset, size - inset - 1, size - inset - 1), fill=255)
        # Antialias discreto apenas na borda; não altera a geometria circular.
        mask = mask.filter(ImageFilter.GaussianBlur(max(0.6, size / 420)))
        plate.putalpha(ImageChops.multiply(plate.getchannel("A"), mask))
        cx, cy = center
        canvas.alpha_composite(plate, (cx - size // 2, cy - size // 2))
        draw = ImageDraw.Draw(canvas, "RGBA")
        ring = max(2, size // 95)
        draw.ellipse(
            (cx - size // 2, cy - size // 2, cx + size // 2, cy + size // 2),
            outline=(*hex_rgb(gold), 190), width=ring,
        )
        inner = int(size * 0.43)
        draw.arc((cx - inner, cy - inner, cx + inner, cy + inner), 205, 335, fill=orange, width=ring)
        draw.arc((cx - inner, cy - inner, cx + inner, cy + inner), 25, 155, fill=border, width=ring)
        tick = max(5, size // 25)
        for angle in (0, 90, 180, 270):
            radians = math.radians(angle)
            x0 = cx + int(math.cos(radians) * size * 0.48)
            y0 = cy + int(math.sin(radians) * size * 0.48)
            x1 = cx + int(math.cos(radians) * (size * 0.48 + tick))
            y1 = cy + int(math.sin(radians) * (size * 0.48 + tick))
            draw.line((x0, y0, x1, y1), fill=orange, width=ring)
        return True
    except Exception as exc:
        warning(f"Símbolo de serviço não pôde ser composto: {exc}")
        return False


def card_image(
    path: Path, segment: dict[str, Any], plan: dict[str, Any], brand: dict[str, Any],
    style: dict[str, Any], project_dir: Path | None = None
) -> None:
    from service_cards import render_service_card
    if render_service_card(globals(), path, segment, plan, brand, style, project_dir):
        return
    from PIL import Image, ImageDraw, ImageEnhance, ImageOps
    width, height = int(plan["output"]["width"]), int(plan["output"]["height"])
    palette = style.get("palette", {})
    bg = color_hex(palette.get("background", brand["colors"]["deep_green"]))
    surface = color_hex(palette.get("surface", brand["colors"]["petrol_green"]))
    bone = color_hex(palette.get("bone", brand["colors"]["bone"]))
    orange = color_hex(palette.get("orange", brand["colors"]["orange"]))
    orange_neon = color_hex(palette.get("orange_neon", brand["colors"].get("orange_alt", "#FF6B00")))
    gold = color_hex(palette.get("gold", brand["colors"]["gold"]))
    border = color_hex(palette.get("border", brand["colors"]["border"]))
    fonts = style.get("fonts", {})
    title_font_name = fonts.get("title", "StardosStencil-Bold.ttf")
    body_font_name = fonts.get("body", "Rokkitt-Regular.ttf")
    technical_font_name = fonts.get("technical", "ShareTechMono-Regular.ttf")
    orange_details = style.get("orange_details", {})
    cards_cfg = style.get("cards", {})
    layout = str(cards_cfg.get("layout") or "site_editorial")
    card_kind = str(segment.get("card_kind") or "phase")
    material_relative = str((cards_cfg.get("material_backgrounds") or {}).get(card_kind) or "")
    material_path = Path(material_relative).expanduser() if material_relative else Path()
    if material_relative and not material_path.is_absolute():
        project_material = (project_dir / material_relative) if project_dir else Path()
        material_path = project_material if project_dir and project_material.is_file() else ASSETS / material_relative
    material_enabled = bool(material_relative and material_path.is_file())
    if material_enabled:
        with Image.open(material_path) as opened:
            material = ImageOps.exif_transpose(opened).convert("RGB")
        material = ImageOps.fit(
            material, (width, height), method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )
        # Mantém o mármore e o metal visíveis, com saturação controlada para
        # preservar legibilidade e o chiaroscuro de luxo da identidade FR.
        material = ImageEnhance.Color(material).enhance(0.94)
        canvas = material
    else:
        canvas = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(canvas, "RGBA")
    margin = max(24, width // 18)

    # Estrutura material: planos, faixa diagonal e uma densidade maior de laranja.
    if material_enabled:
        draw.rectangle((0, 0, width, height), fill=(*hex_rgb(bg), 32))
    else:
        draw.polygon(
            ((int(width * 0.60), 0), (width, 0), (width, int(height * 0.40))),
            fill=(*hex_rgb(surface), 115),
        )
    if not material_enabled and orange_details.get("diagonal_band", True):
        draw.polygon(
            ((-int(width * 0.18), int(height * 0.73)), (int(width * 0.08), int(height * 0.64)),
             (int(width * 0.34), height), (int(width * 0.08), height)),
            fill=(*hex_rgb(orange), 26),
        )
    if not material_enabled:
        draw.rectangle(
            (margin, margin, width - margin, height - margin),
            outline=border, width=max(2, width // 240),
        )
    grid_step = max(50, width // 8)
    if not material_enabled:
        for x in range(margin + grid_step, width - margin, grid_step):
            draw.line((x, margin, x, height - margin), fill=(*hex_rgb(border), 35), width=1)
        for y in range(margin + grid_step, height - margin, grid_step):
            draw.line((margin, y, width - margin, y), fill=(*hex_rgb(border), 35), width=1)

    # Linguagem do site: grande massa verde-petróleo, moldura editorial e
    # laranja reservado aos pontos de direção. O conteúdo continua legível
    # nos três formatos porque tudo deriva das dimensões do plano.
    if layout == "site_editorial" and not material_enabled:
        panel_box = (
            int(margin * 1.20), int(height * 0.095),
            width - int(margin * 1.20), int(height * 0.805),
        )
        draw.rounded_rectangle(
            panel_box, radius=max(16, width // 34),
            fill=(*hex_rgb(surface), 78 if material_enabled else 132),
            outline=(*hex_rgb(border), 175), width=max(1, width // 360),
        )
        rail_x = int(margin * 1.20)
        draw.rounded_rectangle(
            (rail_x, int(height * 0.18), rail_x + max(7, width // 82), int(height * 0.62)),
            radius=max(3, width // 180), fill=(*hex_rgb(orange), 230),
        )
        phase_mark = str(int(segment.get("phase_order") or 0)).zfill(2) if segment.get("phase_order") else "FR"
        mark_font = font(title_font_name, max(72, int(width * 0.28)))
        mark_box = draw.textbbox((0, 0), phase_mark, font=mark_font)
        draw.text(
            (width - margin * 1.35 - (mark_box[2] - mark_box[0]), int(height * 0.58)),
            phase_mark, font=mark_font, fill=(*hex_rgb(border), 42),
        )

    accent_width = max(4, int(width * float(orange_details.get("accent_width_percent", 0.9)) / 100))
    if not material_enabled and orange_details.get("top_bar", True):
        draw.rectangle((0, 0, width, max(7, height // 170)), fill=orange)
        draw.rectangle((0, max(7, height // 170), int(width * 0.34), max(10, height // 125)), fill=gold)
    if not material_enabled and orange_details.get("bottom_bar", True):
        draw.rectangle((0, height - max(6, height // 190), width, height), fill=gold)
        draw.rectangle((int(width * 0.62), height - max(10, height // 125), width, height), fill=orange_neon)
    if not material_enabled and orange_details.get("corner_brackets", True):
        bracket = int(width * 0.08)
        weight = max(2, width // 250)
        for x, y, sx, sy in (
            (margin, margin, 1, 1), (width - margin, margin, -1, 1),
            (margin, height - margin, 1, -1), (width - margin, height - margin, -1, -1),
        ):
            draw.line((x, y, x + sx * bracket, y), fill=orange, width=weight)
            draw.line((x, y, x, y + sy * bracket), fill=orange, width=weight)
    if not material_enabled and orange_details.get("technical_ticks", True):
        for y in range(margin + grid_step, height - margin, grid_step):
            draw.rectangle((margin - accent_width, y, margin + accent_width * 2, y + 3), fill=orange)

    # Os planos translúcidos acima são mesclados em RGB. Daqui em diante o
    # canvas vira RGBA para receber a transparência real do monograma oficial.
    canvas = canvas.convert("RGBA")
    draw = ImageDraw.Draw(canvas, "RGBA")
    logo_cfg = style.get("logo", {})
    hero_logo = bool(logo_cfg.get("hero_on_intro_and_outro", True) and card_kind in {"intro", "outro"})
    if logo_cfg.get("persistent_on_cards", True) and not hero_logo:
        safe = int(width * float(logo_cfg.get("safe_margin_percent", 5)) / 100)
        logo_width = int(width * float(logo_cfg.get("width_percent", 9)) / 100)
        opacity = int(255 * float(logo_cfg.get("opacity_percent", 94)) / 100)
        paste_logo_at(
            canvas, logo_path_for(project_dir, style), logo_width, logo_width,
            (width - safe, safe), anchor="ra", opacity=opacity,
        )
    if hero_logo:
        paste_logo_at(
            canvas, logo_path_for(project_dir, style), int(width * 0.21), int(height * 0.18),
            (width // 2, int(height * 0.15)), anchor="mm", opacity=245,
        )

    mono = font(technical_font_name, max(14, width // 38))
    phase = int(segment.get("phase_order", 0))
    if card_kind == "outro":
        meta = "FR / CONTATO"
    elif card_kind == "service":
        meta = "FR / SERVIÇO"
    else:
        meta = "FR / PROCESSO"
    if phase:
        meta += f"  ·  ETAPA {phase:02d}"
    meta_y = int(height * (0.24 if card_kind in {"intro", "outro"} else 0.13 if card_kind == "service" else 0.15))
    bubble_style = str(style.get("cards", {}).get("bubble_style") or "glass")
    pill_box = draw.textbbox((0, 0), meta, font=mono)
    pill_w = pill_box[2] - pill_box[0] + margin
    pill_fill = None if bubble_style in {"outline", "minimal"} else (*hex_rgb(surface), 255 if bubble_style == "solid" else 205)
    pill_outline = None if bubble_style == "minimal" else (*hex_rgb(orange), 220)
    if pill_fill or pill_outline:
        draw.rounded_rectangle(
            (int(margin * 1.30), meta_y - 8, int(margin * 1.30) + pill_w, meta_y + mono.size + 8),
            radius=max(8, width // 90), fill=pill_fill, outline=pill_outline, width=1,
        )
    draw.rectangle((int(margin * 1.30), meta_y - 8, int(margin * 1.30) + accent_width, meta_y + mono.size + 8), fill=orange)
    draw.text((margin * 1.55, meta_y), meta, font=mono, fill=gold)
    if card_kind == "service":
        service_asset = str(segment.get("service_asset") or "")
        service_path = ASSETS / service_asset
        symbol_size = min(int(width * 0.46), int(height * 0.30))
        pasted = paste_service_symbol(
            canvas, service_path, (width // 2, int(height * 0.36)), symbol_size,
            orange, gold, border,
        )
        if not pasted:
            draw.ellipse(
                (width // 2 - symbol_size // 2, int(height * 0.36) - symbol_size // 2,
                 width // 2 + symbol_size // 2, int(height * 0.36) + symbol_size // 2),
                outline=orange, width=max(2, width // 250),
            )
        y = int(height * 0.53)
    else:
        y = int(height * (0.32 if card_kind in {"intro", "outro"} else 0.27))
    y = draw_hollow_centered(
        draw, str(segment.get("title", "FRANCO ROMEU")), y,
        width - margin * 3, width, bg, orange if card_kind in {"intro", "outro"} else bone,
        title_font_name,
    )
    beam_y = y + 18
    if card_kind == "outro":
        # Feixe térmico vivo: halo controlado + núcleo nítido, sem estourar o
        # dourado acetinado do logotipo.
        draw.line((width * 0.15, beam_y, width * 0.85, beam_y), fill=(*hex_rgb(orange_neon), 42), width=max(18, width // 70))
        draw.line((width * 0.15, beam_y, width * 0.85, beam_y), fill=(*hex_rgb(orange), 115), width=max(8, width // 150))
        draw.line((width * 0.15, beam_y, width * 0.85, beam_y), fill=orange_neon, width=max(3, width // 380))
    else:
        draw.line((width * 0.15, beam_y, width * 0.85, beam_y), fill=orange, width=max(3, width // 180))
        draw.line((width * 0.15, y + 27, width * 0.38, y + 27), fill=gold, width=max(1, width // 300))
    body_font = font(body_font_name, max(24, width // 23))
    emotion_font_name = fonts.get("emotion", body_font_name)
    if card_kind == "outro":
        body_font = font(emotion_font_name, max(24, width // 27))
        body_text = str(segment.get("body") or cards_cfg.get("final_tagline") or "ARTE & ENGENHARIA — PROJETOS & REFORMAS")
    else:
        body_text = str(segment.get("body", ""))
    body_lines = wrap_pixel(draw, body_text, body_font, width - margin * 4)
    body_y = y + 55
    max_body = 3 if card_kind == "service" else int(style.get("cards", {}).get("max_body_lines", 7))
    for line in body_lines[:max_body]:
        box = draw.textbbox((0, 0), line, font=body_font)
        draw.text(((width - (box[2] - box[0])) // 2, body_y), line, font=body_font, fill=bone)
        body_y += int(body_font.size * 1.25)

    contacts = brand["contacts"]
    footer_font = font(technical_font_name, max(10, width // 60))
    show_contacts = bool(style.get("cards", {}).get("show_contacts_on_every_card", True))
    contact_items: list[tuple[str, str]] = []
    if show_contacts:
        contact_items.extend([("instagram", contacts["instagram"]), ("whatsapp", contacts["whatsapp"])])
        if card_kind == "outro" and cards_cfg.get("show_pinterest", True):
            contact_items.append(("pinterest", contacts.get("pinterest", "@FrancoRomeu.FR")))
        if card_kind == "outro" and cards_cfg.get("show_site", True):
            contact_items.append(("site", contacts.get("site", "francoromeu-app.vercel.app")))
    footer_y = int(height * (0.80 if len(contact_items) > 2 else 0.84))
    if contact_items:
        draw.line((margin * 1.4, footer_y - 18, width - margin * 1.4, footer_y - 18), fill=gold, width=1)
        if cards_cfg.get("show_contact_icons", True):
            footer_y = draw_contact_chips(
                draw, contact_items, footer_y, width, int(margin * 1.4), footer_font,
                surface, bone, orange, gold, bubble_style,
            )
        else:
            footer = "  //  ".join(label for _, label in contact_items)
            for line in wrap_pixel(draw, footer, footer_font, width - margin * 3):
                box = draw.textbbox((0, 0), line, font=footer_font)
                draw.text(((width - (box[2] - box[0])) // 2, footer_y), line, font=footer_font, fill=bone)
                footer_y += int(footer_font.size * 1.25)
    if card_kind == "outro" and cards_cfg.get("qr_code_on_outro", False):
        qr_size = max(72, int(width * 0.13))
        if not paste_optional_qr(
            canvas,
            str(cards_cfg.get("qr_code_target") or ""),
            qr_size,
            (int(margin * 1.35), int(height * 0.78)),
        ):
            warning("QR Code solicitado, mas qrencode/python-qrcode não está disponível; card mantido sem QR.")
    if not material_enabled and not contact_items:
        signature = "FRANCO ROMEU  ·  ARTE & ENGENHARIA"
        sig_box = draw.textbbox((0, 0), signature, font=footer_font)
        signature_y = min(height - margin - footer_font.size, footer_y + 8)
        draw.text(((width - (sig_box[2] - sig_box[0])) // 2, signature_y), signature, font=footer_font, fill=orange)
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(path, quality=96)


def hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def branded_overlay_image(
    path: Path, segment: dict[str, Any], plan: dict[str, Any], brand: dict[str, Any],
    style: dict[str, Any], project_dir: Path, show_lower_third: bool
) -> None:
    from PIL import Image, ImageDraw
    width, height = int(plan["output"]["width"]), int(plan["output"]["height"])
    palette = style.get("palette", {})
    colors = {
        "deep_green": palette.get("background", brand["colors"]["deep_green"]),
        "surface": palette.get("surface", brand["colors"]["petrol_green"]),
        "orange": palette.get("orange", brand["colors"]["orange"]),
        "gold": palette.get("gold", brand["colors"]["gold"]),
        "bone": palette.get("bone", brand["colors"]["bone"]),
        "border": palette.get("border", brand["colors"]["border"]),
    }
    fonts = style.get("fonts", {})
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas, "RGBA")
    margin = max(24, width // 18)

    overlay_cfg = style.get("persistent_overlay", {})
    logo_cfg = style.get("logo", {})
    header_top = int(height * 0.035)
    header_height = max(70, int(height * 0.085))
    if overlay_cfg.get("enabled", True):
        opacity = int(255 * float(overlay_cfg.get("background_opacity_percent", 72)) / 100)
        draw.rounded_rectangle(
            (margin, header_top, width - margin, header_top + header_height),
            radius=max(10, width // 50), fill=(*hex_rgb(colors["deep_green"]), opacity),
            outline=(*hex_rgb(colors["border"]), 205), width=max(1, width // 360),
        )
        accent = max(5, width // 110)
        draw.rectangle((margin, header_top, margin + accent, header_top + header_height), fill=color_hex(colors["orange"]))
        if overlay_cfg.get("show_top_orange_line", True):
            draw.rectangle((margin, header_top, width - margin, header_top + max(3, height // 320)), fill=color_hex(colors["orange"]))

        technical = font(
            overlay_cfg.get("technical_font") or fonts.get("technical", "ShareTechMono-Regular.ttf"),
            max(13, width // 44),
        )
        stage_font = font(
            overlay_cfg.get("title_font") or fonts.get("title", "StardosStencil-Bold.ttf"),
            max(18, width // 30),
        )
        brand_line = "FRANCO ROMEU"
        if overlay_cfg.get("show_instagram", True):
            brand_line += f"  //  {brand['contacts']['instagram']}"
        text_x = int(margin * 1.45)
        draw.text((text_x, header_top + int(header_height * 0.16)), brand_line, font=technical, fill=color_hex(colors["gold"]))
        if overlay_cfg.get("show_stage", True):
            stage = str(segment.get("phase_title") or "PROCESSO FR")
            draw.text((text_x, header_top + int(header_height * 0.46)), stage, font=stage_font, fill=color_hex(colors["bone"]))

    if logo_cfg.get("persistent_on_branded_video", True):
        safe = int(width * float(logo_cfg.get("safe_margin_percent", 5)) / 100)
        logo_width = int(width * float(logo_cfg.get("width_percent", 9)) / 100)
        logo_opacity = int(255 * float(logo_cfg.get("opacity_percent", 94)) / 100)
        if overlay_cfg.get("enabled", True) and overlay_cfg.get("logo_alignment") == "bubble_center":
            paste_logo_at(
                canvas, logo_path_for(project_dir, style),
                min(logo_width, int(header_height * 0.82)), int(header_height * 0.82),
                (width - margin - max(10, width // 80), header_top + header_height // 2),
                anchor="rm", opacity=logo_opacity,
            )
        elif overlay_cfg.get("logo_without_bubble", True):
            paste_logo_at(
                canvas, logo_path_for(project_dir, style), logo_width, logo_width,
                (width - safe, header_top), anchor="ra", opacity=logo_opacity,
            )

    if show_lower_third:
        from service_cards import text_fit
        from types import SimpleNamespace
        top, bottom = int(height * 0.64), int(height * 0.82)
        draw.rounded_rectangle((margin, top, width-margin, bottom), radius=max(8,width//50), fill=(*hex_rgb(colors["deep_green"]),230))
        draw.rectangle((margin,top,margin+max(3,width//160),bottom),fill=color_hex(colors["orange"]))
        body = str(segment.get("on_screen_text") or segment.get("technical_note", ""))
        text_fit(SimpleNamespace(**globals()), draw, body,
                 (margin*1.4, top+height*.018, width-margin*1.4, bottom-height*.018),
                 overlay_cfg.get("body_font") or fonts.get("body","Rokkitt-Regular.ttf"),
                 max(16,width*.037),color_hex(colors["bone"]),6)
    canvas.save(path)


def _ffmpeg_filter_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def visual_filter(
    width: int, height: int, duration: float, overlay: bool, *, fps: int = 24,
    input_label: str = "0:v", image_animation: str = "none", lut_path: Path | None = None,
    stabilize: bool = False, stabilization_strength: str = "medium",
) -> str:
    fade_out = max(0.0, duration - 0.28)
    prefilters = []
    if stabilize:
        radius = {
            "light": 8, "low": 8, "medium": 16, "strong": 32, "high": 32,
        }.get(stabilization_strength, 16)
        prefilters.append(f"deshake=rx={radius}:ry={radius}:edge=mirror")
    prefilter_text = (",".join(prefilters) + ",") if prefilters else ""
    chain = (
        f"[{input_label}]{prefilter_text}split=2[bg][fg];"
        f"[bg]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},gblur=sigma=18[bg2];"
        f"[fg]scale={width}:{height}:force_original_aspect_ratio=decrease[fg2];"
        f"[bg2][fg2]overlay=(W-w)/2:(H-h)/2,setsar=1,fps={fps}[base0]"
    )
    current = "base0"
    if image_animation in {"zoom_in", "zoom_out"}:
        if image_animation == "zoom_in":
            zoom = "min(zoom+0.0012,1.10)"
        else:
            zoom = "if(lte(on,1),1.10,max(1.0,zoom-0.0012))"
        chain += f";[{current}]zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={width}x{height}:fps={fps}[animated]"
        current = "animated"
    if lut_path is not None:
        chain += f";[{current}]lut3d=file='{_ffmpeg_filter_path(lut_path)}'[graded]"
        current = "graded"
    # Transitions belong to the joins. Fading every clip creates black flashes.
    chain += f";[{current}]null[base]"
    if overlay:
        chain += ";[base][1:v]overlay=0:0:format=auto,format=yuv420p[v]"
    else:
        chain += ";[base]format=yuv420p[v]"
    return chain


def segment_playback_speed(segment: dict[str, Any]) -> float:
    if segment.get("media_type") != "video" or segment.get("freeze_frame"):
        return 1.0
    try:
        value = float(segment.get("playback_speed") or 1)
    except (TypeError, ValueError):
        value = 1.0
    if not math.isfinite(value):
        value = 1.0
    return min(30.0, max(0.25, value))


def atempo_chain(speed: float) -> str:
    """Decompõe fatores altos no intervalo 0.5–2 aceito por versões antigas do FFmpeg."""
    factors: list[float] = []
    remaining = max(0.5, float(speed))
    while remaining > 2.0 + 1e-6:
        factors.append(2.0)
        remaining /= 2.0
    while remaining < 0.5 - 1e-6:
        factors.append(0.5)
        remaining /= 0.5
    factors.append(remaining)
    return ",".join(f"atempo={factor:.6f}" for factor in factors)


def validate_rendered_media(path: Path, expected_duration: float | None = None) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise AutoEditeError(f"Render incompleto ou vazio: {path}")
    parsed = parse_probe(path, ffprobe(path))
    duration = float(parsed.get("duration_sec") or 0)
    if parsed.get("probe_error") or duration <= 0:
        raise AutoEditeError(f"FFprobe não validou o arquivo: {path}")
    if expected_duration and duration + 0.12 < expected_duration:
        raise AutoEditeError(
            f"Render encerrou antes do previsto: {path.name} ({duration:.2f}s de {expected_duration:.2f}s)."
        )


def render_media_segment(
    project_dir: Path, segment: dict[str, Any], plan: dict[str, Any], brand: dict[str, Any],
    style: dict[str, Any], target: Path, version: str, use_proxies: bool
) -> None:
    width, height = int(plan["output"]["width"]), int(plan["output"]["height"])
    fps = int(plan["output"].get("fps", 24))
    duration = float(segment["duration_sec"])
    media_type = segment["media_type"]
    source_key = "proxy_path" if use_proxies else "source_path"
    source = project_dir / segment.get(source_key, "")
    if not source.is_file():
        source = project_dir / segment.get("proxy_path", "")
    if not source.is_file():
        raise AutoEditeError(f"Fonte ausente para {segment['segment_id']}: {source}")
    if segment.get("freeze_frame"):
        from media_frames import extract_reference
        source = extract_reference(globals(), project_dir, segment["freeze_frame"], use_proxies)
        media_type = "image"
    target.parent.mkdir(parents=True, exist_ok=True)
    persistent = bool(style.get("persistent_overlay", {}).get("enabled", True))
    persistent_logo = bool(style.get("logo", {}).get("persistent_on_branded_video", True))
    overlay = version == "branded" and (
        persistent or persistent_logo or bool(segment.get("lower_third")) or bool(segment.get("on_screen_text")) or bool(segment.get("technical_note"))
    )
    overlay_path = target.with_suffix(".overlay.png")
    temporary = target.with_name(target.stem + ".partial.mp4")
    temporary.unlink(missing_ok=True)
    command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    if media_type == "video":
        command += ["-ss", f"{float(segment.get('start_sec', 0)):.3f}", "-i", str(source)]
    else:
        command += ["-loop", "1", "-i", str(source)]
    if overlay:
        branded_overlay_image(
            overlay_path, segment, plan, brand, style, project_dir,
            show_lower_third=bool(segment.get("lower_third") or segment.get("on_screen_text") or segment.get("technical_note")),
        )
        command += ["-loop", "1", "-i", str(overlay_path)]
    effects = plan.get("visual_effects", {})
    timelapse_config = effects.get("editorial_timelapse", {})
    timelapse_speed = segment_playback_speed(segment)
    timelapse_active = timelapse_speed != 1.0
    timelapse_mute = bool(timelapse_config.get("mute_original_audio", True))
    audio_input_index: int | None = None
    has_audio = (
        media_type == "video"
        and bool(segment.get("has_audio"))
        and bool(plan.get("audio", {}).get("preserve_original", True))
        and not (timelapse_speed > 1.0 and timelapse_mute)
    )
    if not has_audio:
        audio_input_index = 2 if overlay else 1
        command += ["-f", "lavfi", "-t", f"{duration:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
    lut_value = str(effects.get("color_lut") or style.get("color_lut") or "").strip()
    lut_path: Path | None = None
    if lut_value:
        candidate = expand_path(lut_value) if Path(lut_value).is_absolute() else project_dir / lut_value
        if candidate.is_file():
            lut_path = candidate
        else:
            warning(f"LUT não encontrada; render continua sem grade: {candidate}")
    stabilization_mode = str(effects.get("stabilization_mode") or "auto")
    stabilize = bool(effects.get("enable_stabilization")) and (
        stabilization_mode == "all" or
        (stabilization_mode == "auto" and bool(segment.get("needs_stabilization"))) or
        bool(segment.get("force_stabilization"))
    )
    if segment.get("stabilization") == "on" or segment.get("force_stabilization"):
        stabilize = True
    elif segment.get("stabilization") == "off":
        stabilize = False
    stabilize = stabilize and media_type == "video"
    stabilization_strength = str(effects.get("stabilization_strength") or "medium")
    image_animation = str(segment.get("image_animation") or "none") if media_type == "image" else "none"
    speed_enabled = (
        bool(effects.get("speed_ramping")) and media_type == "video"
        and duration > 10 and not timelapse_active and plan.get("contract_version") != 2
    )
    speed_prefix = ""
    audio_label: str | None = None
    video_input_label = "0:v"
    if timelapse_active:
        speed_prefix = f"[0:v]setpts=(PTS-STARTPTS)/{timelapse_speed:.6f}[timelapsev];"
        video_input_label = "timelapsev"
        if has_audio:
            speed_prefix += (
                f"[0:a]asetpts=PTS-STARTPTS,{atempo_chain(timelapse_speed)},"
                f"aresample=48000:async=1:first_pts=0,apad,atrim=duration={duration:.3f}[timelapsea];"
            )
            audio_label = "timelapsea"
    elif speed_enabled:
        parsed_source = parse_probe(source, ffprobe(source))
        total_source = float(parsed_source.get("duration_sec") or 0)
        start_value = float(segment.get("start_sec", 0))
        source_window = 2 * duration - 3
        if total_source - start_value >= source_window and source_window > 1:
            fast_end = source_window - 1
            speed_prefix = (
                f"[0:v]split=2[speed_fast][speed_slow];"
                f"[speed_fast]trim=start=0:end={fast_end:.3f},setpts=0.5*(PTS-STARTPTS)[speed_fast_out];"
                f"[speed_slow]trim=start={fast_end:.3f}:end={source_window:.3f},setpts=2.0*(PTS-STARTPTS)[speed_slow_out];"
                f"[speed_fast_out][speed_slow_out]concat=n=2:v=1:a=0[speedv];"
            )
            video_input_label = "speedv"
            if has_audio:
                speed_prefix += (
                    f"[0:a]asplit=2[a_fast][a_slow];"
                    f"[a_fast]atrim=start=0:end={fast_end:.3f},asetpts=PTS-STARTPTS,atempo=2.0[a_fast_out];"
                    f"[a_slow]atrim=start={fast_end:.3f}:end={source_window:.3f},asetpts=PTS-STARTPTS,atempo=0.5[a_slow_out];"
                    f"[a_fast_out][a_slow_out]concat=n=2:v=0:a=1[speeda];"
                    f"[speeda]aresample=48000:async=1:first_pts=0,apad,atrim=duration={duration:.3f}[speedaout];"
                )
                audio_label = "speedaout"
        else:
            warning(f"Speed ramp ignorado em {segment['segment_id']}: trecho-fonte curto demais.")
    vf = speed_prefix + visual_filter(
        width, height, duration, overlay, fps=fps, input_label=video_input_label,
        image_animation=image_animation, lut_path=lut_path, stabilize=stabilize,
        stabilization_strength=stabilization_strength,
    )
    command += ["-filter_complex", vf, "-map", "[v]"]
    if has_audio:
        if audio_label:
            command += ["-map", f"[{audio_label}]"]
        else:
            command += ["-map", "0:a:0", "-af", f"aresample=48000:async=1:first_pts=0,apad,atrim=duration={duration:.3f}"]
    else:
        command += ["-map", f"{audio_input_index}:a:0"]
    quality = plan.get("export_quality", {})
    crf = max(0, min(35, int(quality.get("video_crf", 18))))
    audio_rate = max(64, min(320, int(quality.get("audio_bitrate_kbps", 192))))
    command += [
        "-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
        "-pix_fmt", "yuv420p", "-r", str(fps), "-c:a", "aac", "-b:a", f"{audio_rate}k",
        "-ac", "2", "-ar", "48000", "-movflags", "+faststart", "-threads", "2", str(temporary)
    ]
    try:
        run(command)
        validate_rendered_media(temporary, duration)
        temporary.replace(target)
    finally:
        overlay_path.unlink(missing_ok=True)
        temporary.unlink(missing_ok=True)


def render_card_segment(
    project_dir: Path, segment: dict[str, Any], plan: dict[str, Any], brand: dict[str, Any],
    style: dict[str, Any], target: Path
) -> None:
    duration = float(segment["duration_sec"])
    fps = int(plan["output"].get("fps", 24))
    target.parent.mkdir(parents=True, exist_ok=True)
    namespace = slugify(plan.get("project", {}).get("slug") or plan.get("project", {}).get("name", "projeto"))
    card_path = project_dir / "cards_editaveis" / namespace / f"{segment['segment_id']}.png"
    card_image(card_path, segment, plan, brand, style, project_dir)
    temporary = target.with_name(target.stem + ".partial.mp4")
    temporary.unlink(missing_ok=True)
    sfx_enabled = bool(plan.get("audio", {}).get("enable_sfx"))
    sfx_name = "ding.wav" if segment.get("card_kind") == "outro" else "whoosh.wav"
    sfx_path = ASSETS / "sfx" / sfx_name
    tts_path = target.with_suffix(".tts.wav")
    tts_path.unlink(missing_ok=True)
    tts_enabled = bool(plan.get("audio", {}).get("tts_voiceover"))
    tts_binary = shutil.which("espeak-ng") or shutil.which("espeak")
    if tts_enabled and tts_binary:
        tts_text = f"{segment.get('title', '')}. {segment.get('body', '')}".strip()
        voice = "pt-br" if Path(tts_binary).name == "espeak-ng" else "pt"
        result = run(
            [tts_binary, "-v", voice, "-s", "150", "-w", str(tts_path), tts_text],
            capture=True,
            check=False,
        )
        if result.returncode != 0:
            tts_path.unlink(missing_ok=True)
            warning("Narração local falhou neste card; render continua sem TTS.")
    elif tts_enabled:
        warning("TTS solicitado, mas espeak-ng/espeak não está instalado; render continua sem narração.")
    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-loop", "1", "-i", str(card_path), "-f", "lavfi", "-t", f"{duration:.3f}",
        "-i", "anullsrc=r=48000:cl=stereo",
    ]
    audio_inputs: list[tuple[int, str, float]] = []
    next_input = 2
    if sfx_enabled and sfx_path.is_file():
        sfx_volume = max(0.0, min(1.0, float(plan.get("audio", {}).get("sfx_volume", 0.3))))
        command += ["-i", str(sfx_path)]
        audio_inputs.append((next_input, "sfx", sfx_volume))
        next_input += 1
    if tts_path.is_file():
        command += ["-i", str(tts_path)]
        audio_inputs.append((next_input, "tts", 0.95))
        next_input += 1
    if audio_inputs:
        filters = [f"[{index}:a]volume={volume:.3f}[{label}]" for index, label, volume in audio_inputs]
        labels = "[1:a]" + "".join(f"[{label}]" for _, label, _ in audio_inputs)
        filters.append(f"{labels}amix=inputs={1 + len(audio_inputs)}:duration=first:dropout_transition=0[a]")
        command += ["-filter_complex", ";".join(filters), "-map", "0:v:0", "-map", "[a]"]
    else:
        command += ["-map", "0:v:0", "-map", "1:a:0"]
    card_cfg = style.get("cards", {})
    animation = str(segment.get("card_animation") or (
        card_cfg.get("intro_animation") if segment.get("card_kind") == "intro" else
        card_cfg.get("outro_animation") if segment.get("card_kind") == "outro" else
        card_cfg.get("service_animation") if segment.get("card_kind") == "service" else
        card_cfg.get("animation") or "soft_zoom"
    ))
    width, height = int(plan["output"]["width"]), int(plan["output"]["height"])
    fade_out = max(0, duration - 0.42)
    if animation in {"soft_zoom", "forge_reveal"}:
        motion = (
            f"zoompan=z='min(zoom+0.0008,1.055)':x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':d=1:s={width}x{height}:fps={fps},"
        )
    elif animation == "zoom_out":
        motion = (
            f"zoompan=z='if(lte(on,1),1.055,max(1.0,zoom-0.0008))':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={width}x{height}:fps={fps},"
        )
    else:
        motion = f"scale={width}:{height},fps={fps},"
    quality = plan.get("export_quality", {})
    crf = max(0, min(35, int(quality.get("video_crf", 18))))
    audio_rate = max(64, min(320, int(quality.get("audio_bitrate_kbps", 192))))
    command += [
        "-vf", f"{motion}" + (f"fade=t=in:st=0:d=0.42,fade=t=out:st={fade_out:.3f}:d=0.42," if animation == "fade" else "") + "format=yuv420p",
        "-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
        "-pix_fmt", "yuv420p", "-r", str(fps), "-c:a", "aac", "-b:a", f"{audio_rate}k",
        "-ac", "2", "-ar", "48000", "-shortest", "-threads", "2", str(temporary)
    ]
    try:
        run(command)
        validate_rendered_media(temporary, duration)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
        tts_path.unlink(missing_ok=True)


def _concat_copy_segments(segments: list[Path], target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    list_path = target.with_suffix(".concat.txt")
    lines = []
    for path in segments:
        escaped = str(path.resolve()).replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
    write_text(list_path, "\n".join(lines) + "\n")
    temp = target.with_name(target.stem + ".partial.mp4")
    try:
        run([
            "ffmpeg", "-nostdin", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
            "-i", str(list_path), "-c", "copy", "-movflags", "+faststart", str(temp)
        ])
        probe = ffprobe(temp)
        parsed = parse_probe(temp, probe)
        if parsed.get("probe_error") or float(parsed.get("duration_sec") or 0) <= 0:
            raise AutoEditeError(f"Validação final falhou para {target.name}")
        temp.replace(target)
    finally:
        list_path.unlink(missing_ok=True)
        temp.unlink(missing_ok=True)


def _concat_copy_segments_with_progress(segments: list[Path], target: Path) -> None:
    """Concatena o rascunho sem abrir uma cadeia xfade gigante."""
    info(f"Montando arquivo final leve: {len(segments)} segmentos")
    _concat_copy_segments(segments, target)
    info(f"Montagem final concluída: {target.name}")


def concat_segments(segments, target, definitions=None, transition_duration=0.32, *, quality=None, draft=None):
    from render_joins import join_segments
    return join_segments(globals(), segments, target, definitions, transition_duration, quality, draft)


def _concat_segments_v1(
    segments: list[Path], target: Path, definitions: list[dict[str, Any]] | None = None,
    transition_duration: float = 0.32,
) -> None:
    """Une segmentos com xfade/acrossfade e cai para concat seguro se necessário."""
    # Uma prévia com dezenas de segmentos não precisa recomprimir uma cadeia
    # xfade completa. Essa cadeia pode consumir memória/CPU por muitos minutos
    # depois de todos os itens já aparecerem como concluídos. A master continua
    # usando as transições; somente o draft usa esta rota leve.
    if len(segments) > 24 and transition_duration <= 0.20:
        _concat_copy_segments_with_progress(segments, target)
        return
    if len(segments) < 2 or not definitions or len(definitions) != len(segments):
        _concat_copy_segments(segments, target)
        return
    durations = [float(parse_probe(path, ffprobe(path)).get("duration_sec") or 0) for path in segments]
    if any(value <= 0.2 for value in durations):
        _concat_copy_segments(segments, target)
        return
    inputs: list[str] = []
    for path in segments:
        inputs += ["-i", str(path)]
    filters: list[str] = []
    cumulative = durations[0]
    video_label = "0:v"
    audio_label = "0:a"
    for index in range(1, len(segments)):
        incoming = definitions[index]
        requested = str(incoming.get("transition") or "fade")
        transition = TRANSITION_MAP.get(requested, "fade")
        overlap = min(max(0.08, transition_duration), durations[index - 1] * 0.25, durations[index] * 0.25)
        offset = max(0.0, cumulative - overlap)
        next_video = f"vx{index}"
        next_audio = f"ax{index}"
        filters.append(
            f"[{video_label}][{index}:v]xfade=transition={transition}:duration={overlap:.3f}:offset={offset:.3f}[{next_video}]"
        )
        filters.append(f"[{audio_label}][{index}:a]acrossfade=d={overlap:.3f}:c1=tri:c2=tri[{next_audio}]")
        video_label, audio_label = next_video, next_audio
        cumulative += durations[index] - overlap
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.stem + ".xfade.partial.mp4")
    temporary.unlink(missing_ok=True)
    command = ["ffmpeg", "-y", "-nostdin", "-hide_banner", "-loglevel", "error", *inputs]
    command += [
        "-filter_complex", ";".join(filters), "-map", f"[{video_label}]", "-map", f"[{audio_label}]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-ac", "2", "-ar", "48000", "-movflags", "+faststart",
        "-threads", "2", str(temporary),
    ]
    try:
        result = run(command, capture=True, check=False)
        if result.returncode != 0:
            warning("Transição xfade indisponível neste conjunto; usando concatenação compatível.")
            _concat_copy_segments(segments, target)
            return
        validate_rendered_media(temporary)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def add_music(source: Path, music: Path, volume: float, target: Path, *, ducking: bool = False) -> None:
    temp = target.with_name(target.stem + ".music.partial.mp4")
    if ducking:
        audio_filter = (
            f"[1:a]volume={volume:.4f}[music];"
            "[music][0:a]sidechaincompress=threshold=0.018:ratio=8:attack=20:release=420[ducked];"
            "[0:a][ducked]amix=inputs=2:duration=first:dropout_transition=2[a]"
        )
    else:
        audio_filter = f"[1:a]volume={volume:.4f}[music];[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[a]"
    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(source),
        "-stream_loop", "-1", "-i", str(music),
        "-filter_complex", audio_filter,
        "-map", "0:v:0", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart", "-shortest", str(temp)
    ]
    result = run(command, capture=True, check=False)
    if result.returncode != 0 and ducking:
        warning("Ducking não foi suportado pelo FFmpeg atual; usando mixagem simples.")
        return add_music(source, music, volume, target, ducking=False)
    if result.returncode != 0:
        raise AutoEditeError(f"Falha ao adicionar trilha: {(result.stderr or '')[-1200:]}")
    temp.replace(target)


@isolated_render
def render_plan(project_dir: Path, plan_path: Path, use_proxies: bool = False, only: str = "both") -> list[Path]:
    check_runtime()
    plan = read_json(plan_path)
    use_proxies = bool(use_proxies or plan.get("output", {}).get("render_source") == "proxies")
    brand = load_brand()
    style = load_card_style(project_dir)
    visual_signature = style_signature(brand, style, project_dir)
    render_root = project_dir / "render"
    from project_scope import read as scope_read
    run_record = scope_read(project_dir / "RENDER_RUN.json", {})
    segment_root = (Path(run_record["source_project"]) / "_CACHE_RENDER" if run_record.get("source_project") else render_root / "segmentos")
    output_root = project_dir / "entrega"
    output_root.mkdir(parents=True, exist_ok=True)
    versions = []
    if only in {"both", "branded"} and plan.get("versions", {}).get("branded", True):
        versions.append("branded")
    if only in {"both", "clean"} and plan.get("versions", {}).get("clean", True):
        versions.append("clean")
    results: list[Path] = []
    for version in versions:
        selected = [
            s for s in plan["segments"]
            if s.get("enabled", True) and version in s.get("include_in", ["branded", "clean"] if s.get("type") == "media" else ["branded"])
        ]
        if not selected:
            raise AutoEditeError(f"A versão {version} não contém segmentos ativos.")
        rendered: list[Path | None] = [None] * len(selected)
        requested_workers = int(plan.get("export_quality", {}).get("parallel_workers", 1) or 1)
        workers = max(1, min(4, requested_workers, len(selected) or 1))
        info(f"Renderizando versão {version}: {len(selected)} segmentos; {workers} processo(s) em paralelo")

        def render_one(index: int, segment: dict[str, Any]) -> tuple[int, Path, bool]:
            item_label = str(
                segment.get("media_id") or segment.get("card_kind")
                or segment.get("segment_id") or f"item-{index}"
            )
            info(
                f"{version} item {index}/{len(selected)}: iniciando "
                f"{segment.get('segment_id', '')} · {item_label}"
            )
            signature_payload = json.dumps(
                {
                    "segment": segment, "output": plan.get("output"), "version": version,
                    "proxies": use_proxies, "visual_signature": visual_signature,
                    "audio": plan.get("audio"), "visual_effects": plan.get("visual_effects"),
                    "export_quality": plan.get("export_quality"), "application": APP_VERSION,
                    "source_files": source_signatures(project_dir, segment, plan, style),
                },
                ensure_ascii=False, sort_keys=True
            ).encode("utf-8")
            signature = hashlib.sha256(signature_payload).hexdigest()[:24]
            target = segment_root / version / f"{index:04d}_{segment['segment_id']}_{signature}.mp4"
            if target.is_file() and target.stat().st_size > 0:
                return index - 1, target, True
            partial = target.with_name(target.stem + ".partial.mp4")
            partial.unlink(missing_ok=True)
            if segment["type"] == "card":
                render_card_segment(project_dir, segment, plan, brand, style, target)
            else:
                render_media_segment(project_dir, segment, plan, brand, style, target, version, use_proxies)
            return index - 1, target, False

        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="fr-render") as executor:
            futures = {
                executor.submit(render_one, index, segment): (index, segment)
                for index, segment in enumerate(selected, 1)
            }
            completed = 0
            for future in as_completed(futures):
                index, segment = futures[future]
                try:
                    position, target, cached = future.result()
                except Exception as exc:
                    for pending in futures:
                        if pending is not future:
                            pending.cancel()
                    item_label = str(segment.get("media_id") or segment.get("card_kind") or "item")
                    raise AutoEditeError(
                        f"Falha no item {index}/{len(selected)} ({segment.get('segment_id', '')} · {item_label}). "
                        f"Os {completed} segmentos já concluídos foram preservados para a retomada. Motivo: {exc}"
                    ) from exc
                rendered[position] = target
                completed += 1
                info(f"{version} {completed}/{len(selected)} {'reutilizado' if cached else 'concluído'}")
        finalized = [path for path in rendered if path is not None]
        if len(finalized) != len(selected):
            raise AutoEditeError(f"Render incompleto: {len(finalized)} de {len(selected)} segmentos.")
        slug = slugify(plan.get("project", {}).get("slug") or plan.get("project", {}).get("name", "projeto"))
        suffix = "INSTITUCIONAL_FR" if version == "branded" else "LIMPO"
        delivery_label = str(plan.get("output", {}).get("delivery_label") or "").strip()
        label = f"_{slugify(delivery_label).upper().replace('-', '_')}" if delivery_label else ""
        final = output_root / f"FR_{slug.upper().replace('-', '_')}{label}_{suffix}.mp4"
        transition_duration = float(plan.get("visual_effects", {}).get("transition_duration_sec", 0.32))
        info(f"{version}: segmentos concluídos; montando entrega final")
        concat_segments(finalized, final, selected, transition_duration, quality=plan.get("export_quality"),
                        draft=plan.get("review_status") == "DRAFT_REQUIRES_FULL_VISUAL_REVIEW")
        music_value = str(plan.get("audio", {}).get("music_path") or "").strip()
        if music_value:
            music = expand_path(music_value)
            if music.is_file():
                mixed = final.with_name(final.stem + "_COM_TRILHA.mp4")
                add_music(
                    final, music, float(plan.get("audio", {}).get("music_volume", 0.1)), mixed,
                    ducking=bool(plan.get("audio", {}).get("auto_ducking", False)),
                )
                final = mixed
            else:
                warning(f"Trilha não encontrada; versão mantida sem trilha: {music}")
        results.append(final)
        info(f"Entrega concluída: {final}")
    write_delivery_report(project_dir, results)
    return results


def write_delivery_report(project_dir: Path, outputs: list[Path]) -> None:
    lines = ["# Relatório de entrega — FR AutoEdite", "", f"Gerado em: {now_iso()}", ""]
    for output in outputs:
        parsed = parse_probe(output, ffprobe(output))
        lines += [
            f"- `{output.name}`",
            f"  - duração: {parsed.get('duration_sec', 0):.2f} s",
            f"  - quadro: {parsed.get('width')} × {parsed.get('height')}",
            f"  - tamanho: {output.stat().st_size} bytes",
        ]
    write_text(project_dir / "entrega" / "RELATORIO_ENTREGA.md", "\n".join(lines) + "\n")


def generate_card_previews(project_dir: Path, plan_path: Path) -> list[Path]:
    plan = read_json(plan_path)
    brand = load_brand()
    style = load_card_style(project_dir)
    namespace = slugify(plan.get("project", {}).get("slug") or plan.get("project", {}).get("name", "projeto"))
    output_dir = project_dir / "cards_editaveis" / namespace
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for segment in plan.get("segments", []):
        if segment.get("type") != "card":
            continue
        target = output_dir / f"{segment['segment_id']}.png"
        card_image(target, segment, plan, brand, style, project_dir)
        outputs.append(target)
    if style.get("cards", {}).get("always_generate_4k_masters", True):
        source_width = int(plan.get("output", {}).get("width") or 1920)
        source_height = int(plan.get("output", {}).get("height") or 1080)
        if source_width > source_height * 1.05:
            master_width, master_height = 3840, 2160
        elif source_height > source_width * 1.05:
            master_width, master_height = 2160, 3840
        else:
            master_width, master_height = 2160, 2160
        master_plan = copy.deepcopy(plan)
        master_plan.setdefault("output", {}).update({
            "width": master_width, "height": master_height,
            "quality_preset": "4k_card_master",
        })
        master_dir = output_dir / "4K_MASTERS"
        master_dir.mkdir(parents=True, exist_ok=True)
        for segment in plan.get("segments", []):
            if segment.get("type") != "card":
                continue
            target = master_dir / f"{segment['segment_id']}_4K.png"
            card_image(target, segment, master_plan, brand, style, project_dir)
            outputs.append(target)
    guide = f"""# Cards editáveis — FR AutoEdite {APP_VERSION}

- Conteúdo: altere `title` e `body` nos segmentos `type: card` do plano JSON.
- Aparência: altere `CARD_STYLE.json` na raiz do projeto.
- Prévia: execute `fr-autoedite cards --projeto CAMINHO_DO_PROJETO`.
- Render final: execute novamente `fr-autoedite render` ou `fr-autoedite social`.
- O logotipo oficial é apenas aplicado proporcionalmente; não é redesenhado ou recolorido.
- Todo card também recebe um master 4K em `4K_MASTERS/`.
"""
    write_text(project_dir / "cards_editaveis" / "COMO_EDITAR.md", guide)
    info(f"Cards editáveis: {len(outputs)} prévia(s) em {output_dir}")
    return outputs


def build_card_preview_plan(project_dir: Path, answers: dict[str, Any]) -> Path:
    """Cria um plano leve de cards quando a preparação das mídias ainda não ocorreu.

    O arquivo é separado do EDIT_PLAN.json: serve para conferir o design e
    nunca se passa por uma timeline final de edição.
    """
    answers = normalize_answers(answers)
    edition = answers.get("edition", {})
    width, height = resolve_output_dimensions(edition, [])
    longest = max(width, height)
    if longest > 1280:
        scale = 1280 / longest
        width = max(240, int(round(width * scale)))
        height = max(240, int(round(height * scale)))
        width += width % 2
        height += height % 2

    context = answers.get("context", {})
    story = answers.get("story", {})
    project = answers.get("project", {})
    card_duration = float(edition.get("phase_card_duration_sec") or 4)
    transitions = [
        value for value in answers.get("visual_effects", {}).get("transitions", [])
        if value in TRANSITION_MAP
    ] or ["fade"]
    segments: list[dict[str, Any]] = [{
        "segment_id": "P0001", "type": "card", "enabled": True,
        "card_kind": "intro", "include_in": ["branded"],
        "duration_sec": round(card_duration + 1, 3),
        "title": str(project.get("name") or "PROJETO FRANCO ROMEU").upper(),
        "body": str(context.get("summary") or story.get("objective") or "Projeto, técnica e execução com identidade."),
        "phase_order": 0, "transition": transitions[0],
    }]

    service_config = answers.get("service_intro", {})
    service = load_service_catalog().get(str(service_config.get("service_key") or ""))
    if service_config.get("enabled") and service:
        segments.append({
            "segment_id": f"P{len(segments) + 1:04d}", "type": "card", "enabled": True,
            "card_kind": "service", "service_key": service["key"],
            "service_asset": service.get("asset", ""), "include_in": ["branded"],
            "duration_sec": round(float(service_config.get("duration_sec") or 3.5), 3),
            "title": str(service_config.get("custom_title") or service.get("label") or "SERVIÇO"),
            "body": str(service_config.get("custom_body") or service.get("body") or ""),
            "phase_order": 0, "transition": transitions[len(segments) % len(transitions)],
            "card_animation": str(service_config.get("animation") or "forge_reveal"),
        })

    phases = sorted(story.get("chronology", []), key=lambda item: item.get("order", 0))
    if not phases:
        phases = [
            {"order": 1, "title": "CONCEPÇÃO", "description": "Ideia, levantamento e planejamento."},
            {"order": 2, "title": "EXECUÇÃO", "description": "Preparação, montagem e aplicação."},
            {"order": 3, "title": "RESULTADO", "description": "Detalhes, acabamento e entrega."},
        ]
    for phase_index, phase in enumerate(phases, 1):
        segments.append({
            "segment_id": f"P{len(segments) + 1:04d}", "type": "card", "enabled": True,
            "card_kind": "phase", "include_in": ["branded"],
            "duration_sec": round(card_duration, 3),
            "title": str(phase.get("title") or f"ETAPA {phase_index}"),
            "body": str(phase.get("description") or ""),
            "phase_order": int(phase.get("order") or phase_index),
            "transition": transitions[len(segments) % len(transitions)],
        })

    segments.append({
        "segment_id": f"P{len(segments) + 1:04d}", "type": "card", "enabled": True,
        "card_kind": "outro", "include_in": ["branded"],
        "duration_sec": round(card_duration + 1, 3), "title": "FRANCO ROMEU",
        "body": str(context.get("cta") or "Projeto · execução · resultado."),
        "phase_order": len(phases) + 1,
        "transition": transitions[len(segments) % len(transitions)],
    })
    plan = {
        "schema_version": 3, "generated_at": now_iso(),
        "application": f"FR AutoEdite {APP_VERSION}", "preview_only": True,
        "project": project, "context": context,
        "output": {
            "width": width, "height": height, "fps": int(edition.get("fps", 24)),
            "quality_preset": "studio_preview", "render_source": "cards_only",
        },
        "visual_effects": answers.get("visual_effects", {}),
        "card_style_path": "CARD_STYLE.json", "segments": segments,
    }
    target = project_dir / "CARD_PREVIEW_PLAN.json"
    write_json(target, plan)
    info("Projeto ainda não preparado: usando plano visual temporário somente para os cards.")
    return target


def social_media_segments(base_plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        copy.deepcopy(segment) for segment in base_plan.get("segments", [])
        if segment.get("type") == "media"
        and segment.get("enabled", True)
        and not segment.get("external_asset")
        and "branded" in segment.get("include_in", [])
    ]


def allocate_social_durations(
    selected: list[dict[str, Any]], budget: float, minimum: float = 1.0
) -> list[float]:
    if not selected or budget <= 0:
        return []
    maximums = [max(0.2, float(segment.get("duration_sec") or minimum)) for segment in selected]
    durations = [min(minimum, maximum) for maximum in maximums]
    if sum(durations) > budget:
        scale = budget / sum(durations)
        return [round(max(0.2, value * scale), 3) for value in durations]
    remaining = budget - sum(durations)
    while remaining > 0.001:
        candidates = [index for index, value in enumerate(durations) if value + 0.001 < maximums[index]]
        if not candidates:
            break
        share = remaining / len(candidates)
        consumed = 0.0
        for index in candidates:
            add = min(share, maximums[index] - durations[index])
            durations[index] += add
            consumed += add
        if consumed <= 0.0001:
            break
        remaining -= consumed
    return [round(value, 3) for value in durations]


def social_output_settings(base_output: dict[str, Any], target_sec: int) -> dict[str, Any]:
    """Mantém a qualidade geral escolhida, sempre no enquadramento vertical 9:16."""
    preset = str(base_output.get("quality_preset") or "custom").lower()
    preset_sizes = {
        "draft": (480, 854),
        "hd": (720, 1280),
        "full_hd": (1080, 1920),
        "2k": (1440, 2560),
        "4k": (2160, 3840),
    }
    if preset in preset_sizes:
        width, height = preset_sizes[preset]
    else:
        try:
            base_width = int(base_output.get("width", 720))
            base_height = int(base_output.get("height", 1280))
        except (TypeError, ValueError):
            base_width, base_height = 720, 1280
        longest = max(
            480,
            min(7680, max(base_width, base_height)),
        )
        width = max(2, int(round(longest * 9 / 16)))
        width += width % 2
        height = longest + longest % 2
    output = copy.deepcopy(base_output)
    output.update({
        "width": width,
        "height": height,
        "fps": int(base_output.get("fps", 24)),
        "quality_preset": preset,
        "delivery_label": f"REEL_{target_sec}S",
    })
    return output


def build_reel_plan(base_plan: dict[str, Any], target_sec: int) -> dict[str, Any]:
    if target_sec < 5:
        raise AutoEditeError("Um Reel precisa ter ao menos 5 segundos.")
    all_media = social_media_segments(base_plan)
    if not all_media:
        raise AutoEditeError("O plano não contém mídias para criar cortes sociais.")
    context = base_plan.get("context", {})
    base_segments = [segment for segment in base_plan.get("segments", []) if segment.get("enabled", True)]
    normal_indices = [
        index for index, segment in enumerate(base_segments)
        if segment.get("type") == "media" and not segment.get("external_asset")
    ]
    first_normal, last_normal = normal_indices[0], normal_indices[-1]

    def reel_special(segment: dict[str, Any]) -> bool:
        if segment.get("external_asset"):
            return bool(segment.get("include_in_reels", True))
        return segment.get("type") == "card" and segment.get("card_kind") in {"intro", "service", "outro"} and bool(
            segment.get("include_in_reels", True)
        )

    opening = [copy.deepcopy(segment) for segment in base_segments[:first_normal] if reel_special(segment)]
    closing = [copy.deepcopy(segment) for segment in base_segments[last_normal + 1:] if reel_special(segment)]
    if not any(segment.get("card_kind") == "intro" or segment.get("external_role") == "intro" for segment in opening):
        opening.append({
            "type": "card", "card_kind": "intro", "enabled": True,
            "title": base_plan.get("project", {}).get("name", "FRANCO ROMEU"),
            "body": context.get("summary", "PROCESSO · EXECUÇÃO · RESULTADO"),
            "phase_order": 0, "include_in": ["branded"], "transition": "fade",
        })
    if not any(segment.get("card_kind") == "outro" or segment.get("external_role") == "outro" for segment in closing):
        closing.append({
            "type": "card", "card_kind": "outro", "enabled": True,
            "title": "FRANCO ROMEU", "body": context.get("cta", "Vamos dimensionar sua obra."),
            "phase_order": 999, "include_in": ["branded"], "transition": "dissolve",
        })

    for segment in opening + closing:
        original = float(segment.get("duration_sec") or 2.0)
        if segment.get("external_asset"):
            maximum = 3.2 if target_sec >= 60 else 2.4
        elif segment.get("card_kind") == "service":
            maximum = 2.4 if target_sec >= 60 else 1.8
        elif segment.get("card_kind") == "outro":
            maximum = 3.0 if target_sec >= 60 else 2.1
        else:
            maximum = 2.2 if target_sec >= 60 else 1.6
        segment["duration_sec"] = round(max(0.65, min(original, maximum)), 3)
        segment["include_in"] = ["branded"]
        segment["enabled"] = True

    fixed_duration = sum(float(segment.get("duration_sec") or 0) for segment in opening + closing)
    fixed_limit = max(2.0, target_sec * 0.34)
    if fixed_duration > fixed_limit:
        scale = fixed_limit / fixed_duration
        for segment in opening + closing:
            segment["duration_sec"] = round(max(0.5, float(segment["duration_sec"]) * scale), 3)
        fixed_duration = sum(float(segment["duration_sec"]) for segment in opening + closing)
    media_budget = max(1.5, target_sec - fixed_duration)

    desired = min(
        len(all_media),
        max(3 if len(all_media) >= 3 else len(all_media), round(media_budget / 2.7)),
    )
    selected = spread_select(all_media, desired)
    if len(selected) == 1:
        selected = [copy.deepcopy(selected[0]), copy.deepcopy(selected[0])]
    prepared: list[dict[str, Any]] = []
    for segment in selected:
        copied = copy.deepcopy(segment)
        if copied.get("media_type") == "image":
            copied["duration_sec"] = min(4.0, max(1.0, float(copied.get("duration_sec") or 3.0)))
        else:
            window_start = float(copied.get("source_window_start_sec") or 0)
            window_end = float(
                copied.get("source_window_end_sec")
                or copied.get("source_duration_sec")
                or (float(copied.get("start_sec") or 0) + float(copied.get("duration_sec") or 0))
            )
            speed = segment_playback_speed(copied)
            available = max(0.2, (window_end - window_start) / speed)
            copied["duration_sec"] = min(8.0, max(0.2, available))
        prepared.append(copied)
    durations = allocate_social_durations(prepared, media_budget, minimum=0.75)

    media_segments: list[dict[str, Any]] = []
    for index, (segment, duration) in enumerate(zip(prepared, durations)):
        fraction = index / max(1, len(prepared) - 1)
        if index == 0:
            role = "inicio"
        elif index == len(prepared) - 1:
            role = "fim"
        else:
            role = "meio"
        if segment.get("media_type") == "video":
            window_start = float(segment.get("source_window_start_sec") or 0)
            window_end = float(
                segment.get("source_window_end_sec")
                or segment.get("source_duration_sec")
                or (float(segment.get("start_sec") or 0) + float(segment.get("duration_sec") or 0))
            )
            source_span = duration * segment_playback_speed(segment)
            available_start = max(0.0, window_end - window_start - source_span)
            segment["start_sec"] = round(window_start + available_start * fraction, 3)
        else:
            segment["start_sec"] = 0.0
        segment.update({
            "enabled": True,
            "include_in": ["branded"],
            "duration_sec": round(duration, 3),
            "coverage_role": role,
            "source_timeline_fraction": round(fraction, 3),
            "reel_manual": False,
            "lower_third": bool(index == 0 or (
                index and prepared[index - 1].get("phase_order") != segment.get("phase_order")
            )),
        })
        media_segments.append(segment)

    segments = opening + media_segments + closing
    transition_duration = max(
        0.0,
        float(base_plan.get("visual_effects", {}).get("transition_duration_sec", 0.32)),
    )
    # O xfade sobrepõe segmentos. O ajuste final fica no encerramento, sem
    # alongar os clipes de mídia escolhidos pelo usuário.
    desired_raw_total = target_sec + transition_duration * max(0, len(segments) - 1)
    current_raw_total = sum(float(segment.get("duration_sec") or 0) for segment in segments)
    correction = desired_raw_total - current_raw_total
    if segments:
        target_segment = next(
            (segment for segment in reversed(segments) if segment.get("type") == "card"),
            segments[-1],
        )
        target_segment["duration_sec"] = round(max(0.5, float(target_segment.get("duration_sec") or 0.5) + correction), 3)
    renumber_segments(segments, start=9001)
    output = social_output_settings(base_plan.get("output", {}), target_sec)
    result = {
        "schema_version": 3,
        "generated_at": now_iso(),
        "application": f"FR AutoEdite {APP_VERSION}",
        "project": copy.deepcopy(base_plan.get("project", {})),
        "context": copy.deepcopy(context),
        "order_mode": base_plan.get("order_mode", "automatico"),
        "output": output,
        "versions": {"branded": True, "clean": False},
        "audio": copy.deepcopy(base_plan.get("audio", {})),
        "visual_effects": copy.deepcopy(base_plan.get("visual_effects", {})),
        "export_quality": copy.deepcopy(base_plan.get("export_quality", {})),
        "review_status": "SOCIAL_AUTO_DRAFT_REQUIRES_VISUAL_REVIEW",
        "social_target_sec": target_sec,
        "reel_sampling_mode": "beginning_middle_end",
        "manual_editing": {
            "preserve_on_regeneration": True,
            "editable_fields": [
                "enabled", "start_sec", "duration_sec", "transition", "phase_title",
                "on_screen_text", "force_stabilization", "editorial_timelapse", "playback_speed",
            ],
            "instruction": "Use o editor de Reels do Studio; salvar este plano não altera o filme principal.",
        },
        "card_style_path": "CARD_STYLE.json",
        "segments": segments,
    }
    return result


def build_carousel_plan(
    project_dir: Path, answers: dict[str, Any], base_plan: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    social = answers.get("social", {})
    slide_count = max(4, min(20, int(social.get("carousel_slides", 8))))
    media_rows = [row for row in manifest.get("media", []) if row.get("status") == "ok" and row.get("thumbnail_path")]
    selected_rows = spread_select(ordered_media(media_rows, base_plan.get("order_mode", "automatico")), max(1, slide_count - 2))
    phases = sorted(answers.get("story", {}).get("chronology", []), key=lambda item: item.get("order", 0))
    context = answers.get("context", {})
    slides: list[dict[str, Any]] = [{
        "slide": 1,
        "kind": "cover",
        "title": answers["project"]["name"].upper(),
        "body": context.get("desired_message") or answers.get("story", {}).get("objective", ""),
    }]
    for index, row in enumerate(selected_rows, 2):
        phase_index = min(len(phases) - 1, int((index - 2) * len(phases) / max(1, len(selected_rows)))) if phases else 0
        phase = phases[phase_index] if phases else {}
        slides.append({
            "slide": index,
            "kind": "media",
            "media_id": row.get("id"),
            "thumbnail_path": row.get("thumbnail_path"),
            "title": phase.get("title") or row.get("filename", "PROCESSO"),
            "body": phase.get("description") or "Registro do processo.",
            "source_filename": row.get("filename"),
        })
    slides.append({
        "slide": slide_count,
        "kind": "outro",
        "title": "FRANCO ROMEU",
        "body": context.get("cta") or "Vamos dimensionar sua obra.",
    })
    return {
        "schema_version": 3,
        "generated_at": now_iso(),
        "project": answers["project"],
        "output": {
            "width": int(social.get("carousel_width", 1080)),
            "height": int(social.get("carousel_height", 1350)),
            "format": "jpg",
        },
        "slides": slides[:slide_count],
        "editing_note": "Edite title/body e execute fr-autoedite social novamente. Não altere media_id sem conferir MANIFESTO_MEDIA.json.",
    }


def build_social_plans(
    project_dir: Path, answers: dict[str, Any], base_plan: dict[str, Any], manifest: dict[str, Any],
    recreate: bool = False
) -> list[Path]:
    social = answers.get("social", {})
    plan_dir = project_dir / "social" / "planos"
    plan_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    if social.get("reels_enabled", True):
        durations = social.get("reel_durations_sec", [30, 60, 90])
        for value in durations:
            target_sec = max(5, int(float(value)))
            path = plan_dir / f"REEL_{target_sec}S.json"
            if recreate or not path.is_file():
                write_json(path, build_reel_plan(base_plan, target_sec))
            outputs.append(path)
    carousel_path = plan_dir / "CARROSSEL_PLAN.json"
    if social.get("carousel_enabled", True):
        if recreate or not carousel_path.is_file():
            write_json(carousel_path, build_carousel_plan(project_dir, answers, base_plan, manifest))
        outputs.append(carousel_path)
    summary = {
        "schema_version": 3,
        "generated_at": now_iso(),
        "enabled": bool(social.get("enabled", True)),
        "reel_plans": [rel(path, project_dir) for path in outputs if path.name.startswith("REEL_")],
        "carousel_plan": rel(carousel_path, project_dir) if carousel_path.is_file() else "",
        "stories": {
            "enabled": bool(social.get("stories_enabled", True)),
            "source_duration_sec": int(social.get("story_source_duration_sec", 60)),
            "part_duration_sec": int(social.get("story_part_duration_sec", 15)),
        },
    }
    write_json(project_dir / "SOCIAL_PLAN.json", summary)
    return outputs


def editing_brief_paths(project_dir: Path) -> tuple[Path, ...]:
    return (
        project_dir / "ROTEIRO_MESTRE_PARA_IA.md",
        project_dir / "_ENVIAR_IA" / "01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE_IA.md",
        project_dir / "_EDITAR" / "04_ROTEIRO_MESTRE_PARA_IA.md",
        project_dir / "_ENVIAR_CHATGPT" / "03_ROTEIRO_MESTRE_PARA_IA.md",
    )


def _brief_media_inventory(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    fields = (
        "id", "media_type", "filename", "source_path", "proxy_path", "thumbnail_path",
        "duration_sec", "capture_time", "width", "height", "has_audio", "quality_score",
        "phase_title", "parent_video", "scene_start_sec", "scene_end_sec",
        "needs_stabilization", "duplicate", "excluded_from_auto_edit",
    )
    return [
        {field: row.get(field) for field in fields if field in row}
        for row in manifest.get("media", [])
        if row.get("status") == "ok"
    ]


def generate_ai_editing_brief(project_dir, answers=None, plan=None, manifest=None):
    from master_contract import generate
    return generate(globals(), project_dir, answers, plan, manifest)


def _generate_ai_editing_brief_v1(
    project_dir: Path, answers: dict[str, Any] | None = None,
    plan: dict[str, Any] | None = None, manifest: dict[str, Any] | None = None,
) -> Path:
    """Gera um único Markdown que uma IA pode preencher e o programa reaplica."""
    answers = normalize_answers(answers or read_json(project_dir / "QUESTIONARIO_RESPONDIDO.json"))
    plan = copy.deepcopy(plan or read_json(project_dir / "EDIT_PLAN.json"))
    manifest = manifest or read_json(project_dir / "MANIFESTO_MEDIA.json")
    reel_plans: dict[str, dict[str, Any]] = {}
    plan_dir = project_dir / "social" / "planos"
    for path in sorted(plan_dir.glob("REEL_*S.json")) if plan_dir.is_dir() else []:
        reel_plans[str(int(read_json(path).get("social_target_sec") or 0))] = read_json(path)
    brief = answers.get("editing_brief", {})
    payload = {
        "schema_version": 1,
        "application": f"FR AutoEdite {APP_VERSION}",
        "project_path_label": str(project_dir),
        "response_contract": {
            "edit_only_this_json_object": True,
            "keep_schema_and_media_ids": True,
            "use_only_confirmed_facts": True,
            "never_include_secrets_or_api_keys": True,
            "empty_string_means_no_suggestion": True,
            "scene_start_sec_policy": (
                "Para media_id M####C###, start_sec pode permanecer absoluto no vídeo-pai "
                "ou ser informado como deslocamento local 0..duration_sec da cena; "
                "o importador valida e normaliza sem mudar o quadro escolhido."
            ),
            "protected_fields": [
                "project.slug", "project.zip_path", "project.workspace_root", "project.context_file",
                "external_intro_outro.intro_path", "external_intro_outro.outro_path",
                "edition.music_path", "visual_effects.color_lut", "cards.style_file",
                "ai_copilot", "cloud_export",
            ],
        },
        "configuration": answers,
        "main_timeline": plan,
        "reels": reel_plans,
        "publication": {
            "video_title": str(brief.get("publication_title") or ""),
            "caption": str(brief.get("publication_caption") or ""),
            "hashtags": list(brief.get("hashtags") or []),
            "complementary_information": str(brief.get("complementary_information") or ""),
            "overlay_typography": {
                "title_font": str(brief.get("overlay_title_font") or "StardosStencil-Bold.ttf"),
                "body_font": str(brief.get("overlay_body_font") or "Rokkitt-Regular.ttf"),
                "technical_font": str(brief.get("overlay_technical_font") or "ShareTechMono-Regular.ttf"),
                "available_fonts": sorted(path.name for path in FONTS.glob("*.ttf")),
                "note": "Estas fontes alteram textos sobre o vídeo; as fontes internas dos cards permanecem no CARD_STYLE.json.",
            },
        },
        "allowed_values": {
            "transitions": sorted(TRANSITION_MAP),
            "service_keys": sorted(load_service_catalog()),
            "card_kinds": ["intro", "service", "phase", "outro"],
            "image_animations": ["none", "zoom_in", "zoom_out"],
            "coverage_roles": ["inicio", "meio", "fim"],
            "editorial_timelapse": {
                "enabled": [True, False],
                "playback_speed_range": [1.25, 30.0],
                "rule": "Use somente em vídeos; duration_sec é o tempo exibido e o recorte consome duration_sec × playback_speed da fonte.",
            },
        },
        "media_inventory": _brief_media_inventory(manifest),
    }
    project_name = answers.get("project", {}).get("name", "Projeto Franco Romeu")
    instructions = f"""# Roteiro Mestre de Edição por IA — {project_name}

Este arquivo é simultaneamente um briefing humano e uma configuração importável pelo **FR AutoEdite {APP_VERSION}**.

## Como usar

1. Gere este arquivo no Studio ou com `fr-autoedite gerar-roteiro-ia --projeto CAMINHO`.
2. Envie à IA este Markdown, os lotes/proxies indicados pelo projeto e o contexto visual disponível.
3. Peça que a IA analise todo o material e altere **somente o objeto JSON entre os dois marcadores**.
4. Salve a resposta como `.md` sem remover os marcadores.
5. Importe no Studio. A aplicação valida, cria backup e aplica as escolhas ao filme e a cada Reel.

## Missão da IA

- compreender a transformação do início ao resultado sem inventar fatos;
- escolher ou excluir mídias com `enabled`;
- ajustar `start_sec` e `duration_sec` respeitando `media_inventory`;
- editar títulos, textos de cards, textos sobre o vídeo e informações complementares;
- selecionar transições, estabilização e animações disponíveis;
- revisar separadamente os Reels, preservando início, meio e fim;
- escrever título, legenda e hashtags de publicação;
- manter `media_id`, caminhos, estrutura JSON e todos os campos que não exigem mudança.

## Campos essenciais por segmento

- `enabled`: `true` usa; `false` ignora sem apagar.
- `start_sec` / `duration_sec`: início e duração do recorte. Em `M####C###`, prefira `start_sec` local à cena (0 até a duração disponível); o importador também aceita o valor absoluto legado e normaliza sem mudar o quadro escolhido.
- `transition`: transição que entra naquele segmento.
- `phase_title`: título do balão superior.
- `on_screen_text`: texto fluente sobre a mídia.
- `technical_note`: informação de apoio.
- `force_stabilization`: força estabilização naquele vídeo.
- `editorial_timelapse`: ativa um trecho acelerado editorial naquele vídeo.
- `playback_speed`: velocidade entre `1.25` e `30`; o programa valida o trecho real consumido.
- cards: `title`, `body`, `duration_sec`, `card_animation`.

## Regras de segurança e verdade

Não crie medidas, marcas, técnicas, datas, preços, resultados ou depoimentos que não estejam confirmados. Não inclua chaves, senhas ou tokens. Se não houver evidência, mantenha vazio ou registre a dúvida em `facts_to_confirm`.

{AI_BRIEF_JSON_BEGIN}
{json.dumps(payload, ensure_ascii=False, indent=2)}
{AI_BRIEF_JSON_END}
"""
    paths = editing_brief_paths(project_dir)
    for path in paths:
        write_text(path, instructions)
    info(f"Roteiro Mestre para IA: {paths[1]}")
    return paths[1]


def parse_ai_editing_brief(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise AutoEditeError(f"Roteiro Markdown não encontrado: {path}")
    text = path.read_text(encoding="utf-8", errors="strict")
    if text.count(AI_BRIEF_JSON_BEGIN) != 1 or text.count(AI_BRIEF_JSON_END) != 1:
        raise AutoEditeError("Use exatamente um bloco JSON e um roteiro por Markdown.")
    start = text.find(AI_BRIEF_JSON_BEGIN)
    end = text.find(AI_BRIEF_JSON_END)
    if start < 0 or end < 0 or end <= start:
        raise AutoEditeError("O Markdown não contém os marcadores JSON do FR AutoEdite.")
    raw = text[start + len(AI_BRIEF_JSON_BEGIN):end].strip()
    if raw.startswith("```json"):
        raw = raw[7:].strip()
    if raw.endswith("```"):
        raw = raw[:-3].strip()
    try:
        def unique_keys(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise AutoEditeError("Campo JSON duplicado: " + key)
                result[key] = value
            return result
        def invalid_constant(value):
            raise AutoEditeError("Número JSON inválido: " + value)
        payload = json.loads(raw, object_pairs_hook=unique_keys, parse_constant=invalid_constant)
    except json.JSONDecodeError as exc:
        raise AutoEditeError(
            f"JSON do roteiro inválido: linha {exc.lineno}, coluna {exc.colno}."
        ) from exc
    if not isinstance(payload, dict):
        raise AutoEditeError("O bloco do roteiro precisa conter um objeto JSON.")
    scopes = re.findall(r"<!--\s*ROTEIRO:\s*([a-zA-Z0-9_-]+)\s*-->", text)
    if payload.get("schema_version") == 2 and (len(scopes) != 1 or scopes[0] != payload.get("roteiro", {}).get("id")):
        raise AutoEditeError("O comentário ROTEIRO deve aparecer uma vez e coincidir com roteiro.id.")
    return payload


def validate_imported_plan(plan, manifest, label, trusted_external=None):
    if plan.get("contract_version") == 2:
        from master_contract import validate_plan
        from types import SimpleNamespace
        return validate_plan(SimpleNamespace(**globals()), plan, manifest, label, trusted_external)
    return _validate_imported_plan_v1(plan, manifest, label, trusted_external)


def _validate_imported_plan_v1(
    plan: dict[str, Any], manifest: dict[str, Any], label: str,
    trusted_external: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    segments = plan.get("segments")
    if not isinstance(segments, list) or not segments:
        raise AutoEditeError(f"{label}: a lista `segments` está vazia ou ausente.")
    rows = {
        str(row.get("id")): row
        for row in manifest.get("media", [])
        if isinstance(row, dict) and row.get("id")
    }
    trusted_external = trusted_external or {}
    repairs: list[dict[str, Any]] = []
    for index, segment in enumerate(segments, 1):
        if not isinstance(segment, dict) or segment.get("type") not in {"card", "media"}:
            raise AutoEditeError(f"{label}: segmento {index} possui tipo inválido.")
        try:
            duration = float(segment.get("duration_sec") or 0)
        except (TypeError, ValueError) as exc:
            raise AutoEditeError(f"{label}: duração inválida no segmento {index}.") from exc
        if duration <= 0 or duration > 3600:
            raise AutoEditeError(f"{label}: duração fora do limite no segmento {index}.")
        transition = str(segment.get("transition") or "fade")
        if transition not in TRANSITION_MAP:
            raise AutoEditeError(f"{label}: transição desconhecida `{transition}` no segmento {index}.")
        if segment.get("type") == "media":
            requested_timelapse = bool(segment.get("editorial_timelapse", False))
            try:
                requested_speed = float(segment.get("playback_speed") or 1.0)
            except (TypeError, ValueError) as exc:
                raise AutoEditeError(
                    f"{label}: velocidade de time-lapse inválida no segmento {index}."
                ) from exc
            if requested_timelapse and not 1.25 <= requested_speed <= 30.0:
                raise AutoEditeError(
                    f"{label}: time-lapse do segmento {index} deve ficar entre 1.25x e 30x."
                )
            media_id = str(segment.get("media_id") or "")
            if segment.get("external_asset"):
                trusted = trusted_external.get(media_id)
                if not trusted:
                    raise AutoEditeError(
                        f"{label}: mídia externa `{media_id}` não corresponde à intro/outro anexada."
                    )
                for field in (
                    "source_path", "proxy_path", "media_type", "has_audio", "source_duration_sec",
                    "source_window_start_sec", "source_window_end_sec", "external_role",
                    "include_in_reels", "include_in",
                ):
                    if field in trusted:
                        segment[field] = copy.deepcopy(trusted[field])
                if segment.get("media_type") == "video":
                    speed = requested_speed if requested_timelapse else 1.0
                    segment["editorial_timelapse"] = speed > 1.0
                    segment["playback_speed"] = round(speed, 3)
                    source_span = duration * speed
                    try:
                        start_sec = float(segment.get("start_sec") or 0)
                        source_duration = float(segment.get("source_duration_sec") or 0)
                    except (TypeError, ValueError) as exc:
                        raise AutoEditeError(f"{label}: corte externo inválido no segmento {index}.") from exc
                    if start_sec < 0 or (source_duration > 0 and start_sec + source_span > source_duration + 0.15):
                        raise AutoEditeError(f"{label}: corte externo ultrapassa a mídia no segmento {index}.")
                    segment["start_sec"] = round(start_sec, 3)
                else:
                    segment["start_sec"] = 0.0
                    segment["editorial_timelapse"] = False
                    segment["playback_speed"] = 1.0
            else:
                media = rows.get(media_id)
                if not media:
                    raise AutoEditeError(f"{label}: media_id desconhecido `{media_id}`.")
                media_type = str(media.get("media_type") or "")
                for field in ("source_path", "proxy_path", "thumbnail_path", "media_type", "has_audio"):
                    if field in media:
                        segment[field] = copy.deepcopy(media[field])
                try:
                    start_sec = float(segment.get("start_sec") or 0)
                except (TypeError, ValueError) as exc:
                    raise AutoEditeError(f"{label}: início inválido no segmento {index}.") from exc
                if start_sec < 0:
                    raise AutoEditeError(f"{label}: início negativo no segmento {index}.")
                if media_type == "image":
                    segment["start_sec"] = 0.0
                    segment["editorial_timelapse"] = False
                    segment["playback_speed"] = 1.0
                    segment["source_window_start_sec"] = 0.0
                    segment["source_window_end_sec"] = 0.0
                    segment["source_duration_sec"] = float(media.get("duration_sec") or 0)
                else:
                    speed = requested_speed if requested_timelapse else 1.0
                    segment["editorial_timelapse"] = speed > 1.0
                    window_start = float(media.get("scene_start_sec") or 0)
                    window_end = float(media.get("scene_end_sec") or media.get("duration_sec") or 0)
                    parent = rows.get(str(media.get("parent_video") or ""), {})
                    source_duration = float(parent.get("duration_sec") or media.get("duration_sec") or window_end)
                    window_length = max(0.0, window_end - window_start)

                    # O motor local usa o relógio absoluto do vídeo-pai, mas
                    # algumas IAs devolvem o deslocamento local de M####C###.
                    # Aceitamos os dois formatos e normalizamos para o valor
                    # absoluto exigido pelo ``ffmpeg -ss``.
                    source_span = duration * speed
                    if requested_timelapse and source_span > window_length + 0.000001:
                        maximum_speed = window_length / duration if duration > 0 else 0.0
                        small_rounding_overflow = (
                            maximum_speed >= 1.25
                            and source_span <= window_length + max(0.25, window_length * 0.01)
                        )
                        if small_rounding_overflow:
                            repaired_speed = math.floor(maximum_speed * 1000.0) / 1000.0
                            repairs.append({
                                "label": label, "segment": index, "media_id": media_id,
                                "field": "playback_speed", "before": speed,
                                "after": repaired_speed,
                                "reason": "ajuste de arredondamento ao limite real da cena",
                            })
                            speed = repaired_speed
                            source_span = duration * speed
                        else:
                            raise AutoEditeError(
                                f"{label}: recorte acelerado ultrapassa `{media_id}` no segmento {index} "
                                f"({source_span:.3f}s solicitados; {window_length:.3f}s disponíveis)."
                            )
                    segment["playback_speed"] = round(speed, 3)

                    absolute_valid = (
                        start_sec + 0.05 >= window_start
                        and start_sec <= window_end + 0.05
                        and start_sec + source_span <= window_end + 0.15
                    )
                    local_valid = (
                        start_sec >= -0.05
                        and start_sec <= window_length + 0.05
                        and start_sec + source_span <= window_length + 0.15
                    )
                    normalized_start = start_sec
                    if not absolute_valid and local_valid:
                        normalized_start = window_start + max(0.0, start_sec)
                        repairs.append({
                            "label": label, "segment": index, "media_id": media_id,
                            "field": "start_sec", "before": start_sec,
                            "after": round(normalized_start, 3),
                            "reason": "tempo local da cena convertido para o vídeo-pai",
                        })
                    elif not absolute_valid:
                        try:
                            declared_window_start = float(segment.get("source_window_start_sec"))
                        except (TypeError, ValueError):
                            declared_window_start = window_start
                        declared_relative = start_sec - declared_window_start
                        stale_window_valid = (
                            declared_relative >= -0.05
                            and declared_relative + source_span <= window_length + 0.15
                        )
                        if stale_window_valid:
                            normalized_start = window_start + max(0.0, declared_relative)
                            repairs.append({
                                "label": label, "segment": index, "media_id": media_id,
                                "field": "start_sec", "before": start_sec,
                                "after": round(normalized_start, 3),
                                "reason": "deslocamento preservado após atualização da janela de cena",
                            })
                        else:
                            raise AutoEditeError(
                                f"{label}: início {start_sec:.3f}s fora da janela de `{media_id}` no segmento {index}. "
                                f"Use tempo absoluto entre {window_start:.3f}s e {window_end:.3f}s, "
                                f"ou tempo local entre 0.000s e {window_length:.3f}s."
                            )
                    if normalized_start + source_span > window_end + 0.15:
                        raise AutoEditeError(
                            f"{label}: recorte ultrapassa a janela de `{media_id}` no segmento {index}."
                        )
                    segment["start_sec"] = round(normalized_start, 3)
                    segment["start_time_basis"] = "absolute_parent_media"
                    segment["source_window_start_sec"] = round(window_start, 3)
                    segment["source_window_end_sec"] = round(window_end, 3)
                    segment["source_duration_sec"] = round(source_duration, 3)
        segment.setdefault("enabled", True)
        segment["transition"] = transition
    if label.startswith("Reel"):
        enabled_media = [
            segment for segment in segments
            if segment.get("type") == "media"
            and not segment.get("external_asset")
            and segment.get("enabled", True)
        ]
        roles = {str(segment.get("coverage_role") or "") for segment in enabled_media}
        if not enabled_media or "inicio" not in roles or "fim" not in roles:
            raise AutoEditeError(
                f"{label}: mantenha ao menos uma mídia de início e uma de fim."
            )
    plan = copy.deepcopy(plan)
    plan["segments"] = renumber_segments(segments, start=1 if label == "filme principal" else 9001)
    plan["generated_at"] = now_iso()
    plan["application"] = f"FR AutoEdite {APP_VERSION} · roteiro IA aplicado"
    plan["review_status"] = "AI_BRIEF_APPLIED_REQUIRES_VISUAL_REVIEW"
    plan["import_repairs"] = repairs
    return plan


def apply_ai_editing_brief(project_dir: Path, markdown_path: Path) -> dict[str, Any]:
    from master_contract import apply_file
    return apply_file(globals(), project_dir, markdown_path)


def _apply_ai_editing_brief_v1(project_dir: Path, markdown_path: Path) -> dict[str, Any]:
    payload = parse_ai_editing_brief(markdown_path)
    manifest = read_json(project_dir / "MANIFESTO_MEDIA.json")
    current_answers = normalize_answers(read_json(project_dir / "QUESTIONARIO_RESPONDIDO.json"))
    incoming_configuration = payload.get("configuration") or {}
    if not isinstance(incoming_configuration, dict):
        raise AutoEditeError("`configuration` precisa ser um objeto JSON.")
    answers = normalize_answers(deep_merge(current_answers, incoming_configuration))
    # O roteiro controla a edição, não a localização de arquivos, credenciais
    # ou destinos externos. Esses campos permanecem sob controle do usuário.
    for field in ("slug", "zip_path", "workspace_root", "context_file"):
        answers.setdefault("project", {})[field] = current_answers.get("project", {}).get(field, "")
    for field in ("intro_path", "outro_path"):
        answers.setdefault("external_intro_outro", {})[field] = current_answers.get(
            "external_intro_outro", {}
        ).get(field, "")
    answers.setdefault("edition", {})["music_path"] = current_answers.get("edition", {}).get("music_path", "")
    answers.setdefault("visual_effects", {})["color_lut"] = current_answers.get("visual_effects", {}).get("color_lut", "")
    answers.setdefault("cards", {})["style_file"] = current_answers.get("cards", {}).get("style_file", "CARD_STYLE.json")
    answers["ai_copilot"] = copy.deepcopy(current_answers.get("ai_copilot", {}))
    answers["cloud_export"] = copy.deepcopy(current_answers.get("cloud_export", {}))
    publication = payload.get("publication") or {}
    if not isinstance(publication, dict):
        raise AutoEditeError("`publication` precisa ser um objeto JSON.")
    typography = publication.get("overlay_typography") or {}
    available_fonts = {path.name for path in FONTS.glob("*.ttf")}
    for role, target_key in (
        ("title_font", "overlay_title_font"),
        ("body_font", "overlay_body_font"),
        ("technical_font", "overlay_technical_font"),
    ):
        selected = str(typography.get(role) or answers.get("editing_brief", {}).get(target_key) or "")
        if selected and selected not in available_fonts:
            raise AutoEditeError(f"Fonte não disponível na instalação: {selected}")
        if selected:
            answers.setdefault("editing_brief", {})[target_key] = selected
    answers.setdefault("editing_brief", {}).update({
        "publication_title": str(publication.get("video_title") or ""),
        "publication_caption": str(publication.get("caption") or ""),
        "hashtags": list(publication.get("hashtags") or []),
        "complementary_information": str(publication.get("complementary_information") or ""),
    })
    main_plan = payload.get("main_timeline")
    if not isinstance(main_plan, dict):
        raise AutoEditeError("`main_timeline` está ausente ou inválido.")
    current_plan = read_json(project_dir / "EDIT_PLAN.json")
    trusted_external = {
        str(segment.get("media_id")): copy.deepcopy(segment)
        for segment in current_plan.get("segments", [])
        if segment.get("type") == "media" and segment.get("external_asset") and segment.get("media_id")
    }
    main_plan = validate_imported_plan(
        main_plan, manifest, "filme principal", trusted_external=trusted_external,
    )
    edition = answers.get("edition", {})
    output_width, output_height = resolve_output_dimensions(edition, manifest.get("media", []))
    edition["width"], edition["height"] = output_width, output_height
    main_plan.update({
        "project": copy.deepcopy(answers.get("project", {})),
        "context": copy.deepcopy(answers.get("context", {})),
        "order_mode": normalize_order_mode(edition.get("order_mode", "automatico")),
        "narrative_priority": answers.get("story", {}).get("priority"),
        "output": {
            "width": output_width,
            "height": output_height,
            "fps": int(edition.get("fps", 24)),
            "video_codec": "libx264",
            "audio_codec": "aac",
            "pixel_format": "yuv420p",
            "render_source": edition.get("render_source", "originals"),
            "quality_preset": edition.get("quality_preset", "custom"),
        },
        "versions": {
            "branded": bool(edition.get("create_branded_version", True)),
            "clean": bool(edition.get("create_clean_version", True)),
        },
        "audio": {
            "preserve_original": bool(edition.get("preserve_original_audio", True)),
            "music_path": edition.get("music_path", ""),
            "music_volume": float(edition.get("music_volume", 0.1)),
            **copy.deepcopy(answers.get("audio_design", {})),
        },
        "visual_effects": copy.deepcopy(answers.get("visual_effects", {})),
        "export_quality": copy.deepcopy(answers.get("export_quality", {})),
        "social": copy.deepcopy(answers.get("social", {})),
        "card_style_path": "CARD_STYLE.json",
    })
    reels = payload.get("reels") or {}
    if not isinstance(reels, dict):
        raise AutoEditeError("`reels` precisa ser um objeto JSON.")
    validated_reels: dict[int, dict[str, Any]] = {}
    for key, reel_plan in reels.items():
        if not isinstance(reel_plan, dict):
            raise AutoEditeError(f"Reel {key}: plano inválido.")
        target = int(float(reel_plan.get("social_target_sec") or key))
        if target < 5 or target > 600:
            raise AutoEditeError(f"Reel {key}: duração-alvo fora de 5–600 segundos.")
        reel_plan["social_target_sec"] = target
        validated = validate_imported_plan(
            reel_plan, manifest, f"Reel {target}s", trusted_external=trusted_external,
        )
        validated.update({
            "project": copy.deepcopy(main_plan["project"]),
            "context": copy.deepcopy(main_plan["context"]),
            "order_mode": main_plan["order_mode"],
            "output": social_output_settings(main_plan["output"], target),
            "versions": {"branded": True, "clean": False},
            "audio": copy.deepcopy(main_plan["audio"]),
            "visual_effects": copy.deepcopy(main_plan["visual_effects"]),
            "export_quality": copy.deepcopy(main_plan["export_quality"]),
            "social_target_sec": target,
            "reel_sampling_mode": "beginning_middle_end",
        })
        validated_reels[target] = validated

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    history = project_dir / "_HISTORICO" / f"ANTES_ROTEIRO_IA_{stamp}"
    history.mkdir(parents=True, exist_ok=True)
    for source in (
        project_dir / "QUESTIONARIO_RESPONDIDO.json",
        project_dir / "EDIT_PLAN.json",
        *sorted((project_dir / "social" / "planos").glob("REEL_*S.json")),
    ):
        if source.is_file():
            shutil.copy2(source, history / source.name)
    write_json(project_dir / "QUESTIONARIO_RESPONDIDO.json", answers)
    shutil.copy2(
        project_dir / "QUESTIONARIO_RESPONDIDO.json",
        project_dir / "_EDITAR" / "01_CONFIGURACOES_DO_PROJETO.json",
    )
    write_json(project_dir / "EDIT_PLAN.json", main_plan)
    shutil.copy2(project_dir / "EDIT_PLAN.json", project_dir / "_EDITAR" / "02_PLANO_DA_EDICAO.json")
    for target, reel_plan in validated_reels.items():
        write_json(project_dir / "social" / "planos" / f"REEL_{target}S.json", reel_plan)
    write_json(project_dir / "PUBLICACAO_SOCIAL.json", publication)
    publication_md = "# Publicação sugerida\n\n"
    publication_md += f"## Título\n\n{publication.get('video_title', '')}\n\n"
    publication_md += f"## Legenda\n\n{publication.get('caption', '')}\n\n"
    publication_md += "## Hashtags\n\n" + " ".join(str(item) for item in publication.get("hashtags", [])) + "\n\n"
    publication_md += f"## Informações complementares\n\n{publication.get('complementary_information', '')}\n"
    write_text(project_dir / "PUBLICACAO_SOCIAL.md", publication_md)
    sync_card_style_from_answers(project_dir, answers)
    generate_card_previews(project_dir, project_dir / "EDIT_PLAN.json")
    for target in editing_brief_paths(project_dir):
        target.parent.mkdir(parents=True, exist_ok=True)
        if markdown_path.resolve() != target.resolve():
            shutil.copy2(markdown_path, target)
    import_repairs = list(main_plan.get("import_repairs") or [])
    for reel_plan in validated_reels.values():
        import_repairs.extend(reel_plan.get("import_repairs") or [])
    report = {
        "schema_version": 1,
        "application": f"FR AutoEdite {APP_VERSION}",
        "applied_at": now_iso(),
        "source": str(markdown_path),
        "backup": str(history),
        "main_segments": len(main_plan.get("segments", [])),
        "reels": sorted(validated_reels),
        "automatic_repairs": import_repairs,
        "automatic_repairs_count": len(import_repairs),
        "status": "applied_requires_visual_review",
    }
    write_json(project_dir / "RELATORIO_APLICACAO_ROTEIRO_IA.json", report)
    info("Roteiro da IA aplicado com backup. Gere e assista ao rascunho antes da master.")
    return report


def render_reel_cover(project_dir: Path, reel_plan: dict[str, Any], target: Path) -> None:
    cover_plan = copy.deepcopy(reel_plan)
    cover_plan["output"] = {"width": 1080, "height": 1920, "fps": 24}
    intro = next((copy.deepcopy(s) for s in reel_plan.get("segments", []) if s.get("type") == "card"), {})
    intro.update({
        "card_kind": "intro",
        "title": reel_plan.get("project", {}).get("name", "FRANCO ROMEU"),
        "body": f"DO PROJETO À ENTREGA  //  {int(reel_plan.get('social_target_sec', 0))} SEGUNDOS",
        "phase_order": 0,
    })
    card_image(target, intro, cover_plan, load_brand(), load_card_style(project_dir), project_dir)


def split_story_video(source: Path, target_dir: Path, part_duration: int, prefix: str) -> list[Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    total = float(parse_probe(source, ffprobe(source)).get("duration_sec") or 0)
    outputs: list[Path] = []
    start = 0.0
    index = 1
    while start + 0.05 < total:
        duration = min(float(part_duration), total - start)
        target = target_dir / f"{prefix}_STORY_{index:02d}.mp4"
        temporary = target.with_name(target.stem + ".partial.mp4")
        temporary.unlink(missing_ok=True)
        run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{start:.3f}",
            "-i", str(source), "-t", f"{duration:.3f}", "-map", "0:v:0", "-map", "0:a?",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", str(temporary),
        ])
        validate_rendered_media(temporary, duration)
        temporary.replace(target)
        outputs.append(target)
        start += duration
        index += 1
    return outputs


def render_carousel(project_dir, carousel_plan_path):
    from social_contract import render_carousel as render_carousel_v2
    return render_carousel_v2(globals(), project_dir, carousel_plan_path)


def social_copy(answers: dict[str, Any]) -> str:
    context = answers.get("context", {})
    contacts = load_brand()["contacts"]
    must_include = "\n".join(f"- {item}" for item in answers.get("story", {}).get("must_include", [])) or "- Confirmar no contexto e nas imagens."
    return f"""# Pacote editorial social — {answers['project']['name']}

## Mensagem central

{context.get('desired_message') or answers.get('story', {}).get('objective', '')}

## Estrutura recomendada

- Gancho verdadeiro: detalhe, contraste ou pergunta sustentada pelas imagens.
- Contexto: o que estava sendo decidido ou transformado.
- Processo: decisões, materiais e execução visíveis.
- Evidência: teste, encaixe, evolução ou resultado final.
- CTA único: {context.get('cta') or 'Vamos dimensionar sua obra.'}

## Elementos obrigatórios

{must_include}

## Contatos oficiais

- Instagram: {contacts['instagram']}
- WhatsApp: {contacts['whatsapp']}
- E-mail: {contacts['email']}
- Região: {contacts['region']}

## Regra de publicação

Revisar os cortes e completar a legenda apenas com fatos confirmados. Não inventar medidas, materiais, marcas, prazos, preços, resultados ou prova social.
"""


@isolated_render
def render_social_outputs(
    project_dir: Path, answers: dict[str, Any], use_proxies: bool = False,
    only: str = "all", recreate_plans: bool = False
) -> list[Path]:
    base_plan = read_json(project_dir / "EDIT_PLAN.json")
    if base_plan.get("contract_version") == 2 and not recreate_plans:
        from social_contract import render as render_social_contract
        return render_social_contract(globals(), project_dir, answers, use_proxies, only)
    manifest = read_json(project_dir / "MANIFESTO_MEDIA.json")
    plans = build_social_plans(project_dir, answers, base_plan, manifest, recreate=recreate_plans)
    outputs: list[Path] = []
    reel_outputs: dict[int, Path] = {}
    if only in {"all", "reels", "stories"}:
        reel_plans = [path for path in plans if path.name.startswith("REEL_")]
        if only == "stories" and reel_plans:
            desired_story = int(answers.get("social", {}).get("story_source_duration_sec", 60))
            reel_plans = [min(
                reel_plans,
                key=lambda path: abs(int(read_json(path).get("social_target_sec", 0)) - desired_story),
            )]
        for plan_path in reel_plans:
            reel_plan = read_json(plan_path)
            target_sec = int(reel_plan.get("social_target_sec", 0))
            rendered = render_plan(project_dir, plan_path, use_proxies=use_proxies, only="branded")
            if rendered:
                reel_outputs[target_sec] = rendered[0]
                outputs.extend(rendered)
                if answers.get("social", {}).get("create_reel_covers", True):
                    cover = project_dir / "social" / "capas" / f"CAPA_REEL_{target_sec}S.jpg"
                    cover.parent.mkdir(parents=True, exist_ok=True)
                    render_reel_cover(project_dir, reel_plan, cover)
                    outputs.append(cover)
    if only in {"all", "stories"} and answers.get("social", {}).get("stories_enabled", True):
        desired = int(answers.get("social", {}).get("story_source_duration_sec", 60))
        if reel_outputs:
            source_duration = min(reel_outputs, key=lambda value: abs(value - desired))
            source = reel_outputs[source_duration]
            prefix = f"FR_{slugify(answers['project']['slug']).upper().replace('-', '_')}"
            stories = split_story_video(
                source, project_dir / "social" / "stories",
                max(5, int(answers.get("social", {}).get("story_part_duration_sec", 15))), prefix,
            )
            outputs.extend(stories)
    if only in {"all", "carrossel"} and answers.get("social", {}).get("carousel_enabled", True):
        carousel_path = next((path for path in plans if path.name == "CARROSSEL_PLAN.json"), None)
        if carousel_path:
            outputs.extend(render_carousel(project_dir, carousel_path))
    write_text(project_dir / "social" / "PACOTE_EDITORIAL.md", social_copy(answers))
    report_lines = [
        "# Relatório do pacote social — FR AutoEdite", "", f"Gerado em: {now_iso()}", "",
    ]
    for output in outputs:
        if output.suffix.lower() == ".mp4":
            parsed = parse_probe(output, ffprobe(output))
            report_lines.append(
                f"- `{rel(output, project_dir)}` — {float(parsed.get('duration_sec') or 0):.2f}s, "
                f"{parsed.get('width')}×{parsed.get('height')}"
            )
        else:
            report_lines.append(f"- `{rel(output, project_dir)}`")
    write_text(project_dir / "social" / "RELATORIO_SOCIAL.md", "\n".join(report_lines) + "\n")
    info(f"Pacote social concluído: {len(outputs)} arquivo(s)")
    return outputs


def context_source_text(answers: dict[str, Any]) -> tuple[str, Path | None]:
    value = str(answers.get("project", {}).get("context_file") or "").strip()
    if not value:
        return "", None
    path = expand_path(value)
    if not path.is_file():
        warning(f"Arquivo de contexto não encontrado; mantendo apenas o questionário: {path}")
        return "", None
    if path.suffix.lower() not in {".md", ".txt", ".json", ".yaml", ".yml", ".csv"}:
        return "", path
    try:
        return path.read_text(encoding="utf-8"), path
    except UnicodeDecodeError:
        return "", path


def write_project_context(project_dir: Path, answers: dict[str, Any]) -> list[Path]:
    context = answers.get("context", {})
    story = answers.get("story", {})
    phases = sorted(story.get("chronology", []), key=lambda item: item.get("order", 0))
    lines = [
        f"# Contexto do projeto — {answers['project']['name']}", "",
        "## Resumo", "", str(context.get("summary") or story.get("objective") or ""), "",
        "## Objetivo", "", str(story.get("objective") or ""), "",
        "## Público", "", str(story.get("audience") or ""), "",
        "## Mensagem central", "", str(context.get("desired_message") or ""), "",
        "## Ordem e etapas", "",
    ]
    for index, phase in enumerate(phases, 1):
        lines.append(f"{phase.get('order', index)}. **{phase.get('title', f'ETAPA {index}')}** — {phase.get('description', '')}")
    lines += ["", "## Elementos obrigatórios", ""]
    must_include = story.get("must_include", [])
    lines.extend(f"- {item}" for item in must_include)
    if not must_include:
        lines.append("- Nenhum elemento adicional informado.")
    lines += ["", "## Evitar", ""]
    must_avoid = story.get("must_avoid", [])
    lines.extend(f"- {item}" for item in must_avoid)
    if not must_avoid:
        lines.append("- Não inventar fatos, medidas, materiais ou resultados.")
    lines += ["", "## Fatos confirmados", ""]
    facts = context.get("facts_confirmed", [])
    lines.extend(f"- {item}" for item in facts)
    if not facts:
        lines.append("- Confirmar visualmente e no arquivo de contexto.")
    lines += ["", "## Fatos a confirmar", ""]
    facts_pending = context.get("facts_to_confirm", [])
    lines.extend(f"- {item}" for item in facts_pending)
    if not facts_pending:
        lines.append("- Nenhum informado.")
    lines += ["", "## Chamada para ação", "", str(context.get("cta") or "Vamos dimensionar sua obra."), ""]

    source_text, source_path = context_source_text(answers)
    copied: list[Path] = []
    if source_path:
        destination = project_dir / "fontes_contexto" / source_path.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source_path.resolve() != destination.resolve():
            shutil.copy2(source_path, destination)
        copied.append(destination)
        lines += ["", "## Arquivo de contexto fornecido", "", f"Arquivo preservado: `fontes_contexto/{source_path.name}`", ""]
    if source_text:
        lines += ["## Conteúdo integral fornecido", "", source_text.rstrip(), ""]
    elif context.get("notes"):
        lines += ["## Notas adicionais", "", str(context.get("notes")).rstrip(), ""]
    write_text(project_dir / "CONTEXTO_PROJETO.md", "\n".join(lines).rstrip() + "\n")
    return copied


def chatgpt_prompt(answers: dict[str, Any], manifest: dict[str, Any]) -> str:
    phases = sorted(answers.get("story", {}).get("chronology", []), key=lambda p: p.get("order", 0))
    chronology = "\n".join(
        f"{phase.get('order', i + 1)}. {phase.get('title')}: {phase.get('description')}"
        for i, phase in enumerate(phases)
    )
    contacts = load_brand()["contacts"]
    order_mode = answers.get("edition", {}).get("order_mode", "automatico")
    social = answers.get("social", {})
    return f"""# PROMPT MESTRE — FR AUTOEDITE {APP_VERSION} STUDIO

Você é o editor técnico e diretor de montagem da Franco Romeu. Os arquivos anexados formam um único projeto preparado pelo FR AutoEdite. Trabalhe diretamente sobre eles; não peça que eu reconte informações já presentes no questionário, manifesto, contatos visuais ou plano.

## Missão

1. Leia primeiro `00_LEIA_PRIMEIRO.md`, `CONTEXTO_PROJETO.md`, `QUESTIONARIO_RESPONDIDO.json`, `MANIFESTO_MEDIA.json`, todos os contatos visuais, `EDIT_PLAN.json`, `CARD_STYLE.json`, `SOCIAL_PLAN.json` e `FR_CONTENT_STRATEGY.json`.
2. Analise visualmente os proxies de todos os lotes. O nome/data ajuda, mas a cronologia editorial informada abaixo prevalece.
3. Selecione os melhores trechos técnicos: enquadramento legível, ação útil, evolução real, detalhe construtivo e resultado. Remova tremores severos, repetições, espera, câmera no chão, tela preta e momentos sem informação.
4. Atualize `EDIT_PLAN.json`, conservando seu schema. Ajuste `start_sec`, `duration_sec`, ordem, etapa, lower third e notas. Nunca indique um trecho fora da duração registrada no manifesto.
5. Produza uma versão institucional longa, com cards Franco Romeu e logo persistente, e uma versão limpa completa, sem cards, logo ou comentários. Preserve a história e dê tempo suficiente para compreender cada serviço.
6. Se o ambiente permitir FFmpeg/Python, execute a renderização e valide os vídeos. Caso não permita, devolva o `EDIT_PLAN.json` final completo e pronto para o comando `fr-autoedite render`.
7. Revise também os planos sociais: Reels de {', '.join(str(v) + 's' for v in social.get('reel_durations_sec', [30, 60, 90]))}, Stories e carrossel. Recompile a narrativa para cada canal; não apenas acelere o filme longo.

## Política de ordenação selecionada

Modo: **{order_mode}**.

- `automatico`: contexto, palavras-chave, qualidade técnica e cronologia dentro de cada etapa.
- `cronologico`: data/hora de captura, sem reorganização temática que quebre a sequência.
- `alfabetico`: nome do arquivo, útil quando o responsável já numerou ou nomeou a ordem.
- `aleatorio`: mashup reproduzível por `random_seed`; ignora o significado do contexto e exige revisão visual.

Não altere o modo sem justificativa explícita no relatório.

## Ordem narrativa obrigatória

{chronology}

## Identidade visual obrigatória

- Títulos: Stardos Stencil em composição vazada/contornada.
- Corpo: Rokkitt. Metadados: Share Tech Mono.
- Paleta: verde profundo #0A2F26, verde petróleo #123F34, laranja #FC7016, osso #E6D6B5, carvão #121318 e borda #1A6069.
- Cards conceituais, arquitetônicos, tecnicamente informativos e editáveis por `EDIT_PLAN.json` + `CARD_STYLE.json`.
- A versão institucional mantém uma pequena aplicação do logo oficial durante toda a mídia. A versão limpa permanece realmente limpa.
- Logo oficial: `franco-romeu-logo.png`.
- Contatos oficiais, sem alterações: WhatsApp {contacts['whatsapp']}; Instagram {contacts['instagram']}; e-mail {contacts['email']}; região {contacts['region']}.

## Regras de precisão

- Não invente materiais, medidas, marcas, técnicas, fornecedores, datas ou resultados.
- Distingua o que é visível do que foi declarado no questionário.
- Quando um arquivo não puder ser identificado com segurança, marque `needs_human_confirmation: true` no segmento, sem forçar uma classificação.
- Preserve os caminhos relativos e os `media_id` do manifesto.
- IDs como `M0001C003` são cenas virtuais do vídeo-pai; use o `start_sec` absoluto já sugerido no plano.
- Respeite `duplicate`, `excluded_from_auto_edit`, `needs_stabilization` e os sinais técnicos do manifesto.
- Não use os arquivos originais se somente proxies estiverem anexados; o plano continuará apontando para os originais no computador do proprietário.
- Cada `FR_AUTOEDITE_LOTE_###.zip` é independente e fica abaixo de 150 MB. Proxies grandes podem aparecer como MP4s autônomos numerados; não concatene ZIPs binariamente.

## Entregáveis esperados

- `EDIT_PLAN_FINAL.json` válido e completo.
- `RELATORIO_CURADORIA.md` com mídia usada, descartada, motivo e alertas.
- Vídeo institucional e vídeo limpo, quando a renderização estiver disponível.
- Planos e, quando possível, renders para Reels, Stories, capas e carrossel 4:5.

Projeto: **{answers['project']['name']}**  
Objetivo: {answers.get('story', {}).get('objective', '')}  
Mídias catalogadas: {manifest.get('summary', {}).get('total', 0)}.
"""


def write_handoff_files(project_dir: Path, answers: dict[str, Any], manifest: dict[str, Any]) -> None:
    write_project_context(project_dir, answers)
    prompt = chatgpt_prompt(answers, manifest)
    write_text(project_dir / "PROMPT_PRONTO_PARA_CHATGPT.md", prompt)
    brand_target = project_dir / "fr_brand_profile.json"
    shutil.copy2(TEMPLATES / "fr_brand_profile.json", brand_target)
    shutil.copy2(TEMPLATES / "EDIT_PLAN_SCHEMA.json", project_dir / "EDIT_PLAN_SCHEMA.json")
    if not (project_dir / "CARD_STYLE.json").is_file():
        shutil.copy2(TEMPLATES / "card_style.json", project_dir / "CARD_STYLE.json")
    shutil.copy2(TEMPLATES / "fr_content_strategy.json", project_dir / "FR_CONTENT_STRATEGY.json")
    logo_target = project_dir / "franco-romeu-logo.png"
    shutil.copy2(ASSETS / "franco-romeu-logo.png", logo_target)
    guide = f"""# 00 — LEIA PRIMEIRO

Este pacote foi preparado pelo **FR AutoEdite {APP_VERSION} Universal** para o projeto **{answers['project']['name']}**.

## Para usar no ChatGPT

1. Anexe todos os arquivos listados em `UPLOAD_LIST.txt` na mesma conversa.
2. Copie e envie o conteúdo de `PROMPT_PRONTO_PARA_CHATGPT.md`.
3. O ChatGPT deve revisar visualmente os proxies e devolver um plano final, sem modificar os originais.
4. Salve o plano devolvido como `EDIT_PLAN.json` na pasta do projeto.
5. Execute `fr-autoedite render --projeto "{project_dir}" --plano "{project_dir / 'EDIT_PLAN.json'}"`.
6. Execute `fr-autoedite social --projeto "{project_dir}"` para Reels, Stories, carrossel e capas.

## Roteiro único para qualquer IA

- Gere: `fr-autoedite gerar-roteiro-ia --projeto "{project_dir}"`.
- Envie `_ENVIAR_IA/01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE_IA.md` junto dos vídeos/proxies.
- Aplique a resposta: `fr-autoedite aplicar-roteiro-ia --projeto "{project_dir}" --arquivo RESPOSTA.md`.
- O importador valida o JSON, cria backup e nunca exige que a IA execute o programa.

## Cards editáveis

- Conteúdo: `EDIT_PLAN.json` (`title` e `body`).
- Aparência: `CARD_STYLE.json`.
- Prévia: `fr-autoedite cards --projeto "{project_dir}"`.

## Segurança

- Os arquivos em `originais/` nunca são alterados.
- O plano automático é uma primeira montagem: confirme visualmente os trechos antes da entrega ao cliente.
- A cronologia respondida tem prioridade sobre a data do arquivo.
- O modo de ordem selecionado é `{answers.get('edition', {}).get('order_mode', 'automatico')}`.
"""
    write_text(project_dir / "00_LEIA_PRIMEIRO.md", guide)


def partition_by_size(paths: list[Path], max_bytes: int) -> list[list[Path]]:
    lots: list[list[Path]] = []
    current: list[Path] = []
    current_size = 0
    for path in paths:
        size = path.stat().st_size
        if current and current_size + size > max_bytes:
            lots.append(current)
            current = []
            current_size = 0
        current.append(path)
        current_size += size
    if current:
        lots.append(current)
    return lots


def split_large_proxy_for_handoff(
    project_dir: Path, source: Path, payload_budget: int
) -> list[Path]:
    """Divide um proxy grande em MP4s independentes e analisáveis."""
    cache = project_dir / "_CHATGPT_CACHE" / "proxies_divididos" / slugify(source.stem)
    cache.mkdir(parents=True, exist_ok=True)
    parsed = parse_probe(source, ffprobe(source))
    duration = float(parsed.get("duration_sec") or 0)
    if duration <= 0:
        raise AutoEditeError(f"Não foi possível dividir o proxy grande: {source.name}")
    ratio = payload_budget / max(1, source.stat().st_size)
    segment_time = max(5.0, min(90.0, duration * ratio * 0.72))
    for attempt in range(4):
        attempt_dir = cache / f"tentativa_{attempt + 1}"
        attempt_dir.mkdir(parents=True, exist_ok=True)
        pattern = attempt_dir / f"{slugify(source.stem)}_PARTE_%03d.mp4"
        run([
            "ffmpeg", "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
            "-i", str(source),
            "-map", "0:v:0", "-map", "0:a?",
            "-vf", "scale='if(gt(iw,ih),640,-2)':'if(gt(iw,ih),-2,640)',fps=20,setsar=1",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "34", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ac", "1", "-b:a", "48k",
            "-f", "segment", "-segment_time", f"{segment_time:.3f}",
            "-reset_timestamps", "1", "-movflags", "+faststart", str(pattern),
        ])
        parts = sorted(path for path in attempt_dir.glob("*.mp4") if path.stat().st_size > 0)
        if parts and all(path.stat().st_size <= payload_budget for path in parts):
            return parts
        segment_time = max(3.0, segment_time * 0.52)
    raise AutoEditeError(
        f"Mesmo após quatro tentativas, um trecho de {source.name} excedeu o limite do lote. "
        "Reduza proxy_long_side ou o tamanho máximo do lote."
    )


def handoff_proxy_items(project_dir: Path, proxies: list[Path], payload_budget: int) -> list[Path]:
    result: list[Path] = []
    for path in proxies:
        if path.stat().st_size <= payload_budget:
            result.append(path)
            continue
        if path.suffix.lower() in VIDEO_EXTENSIONS:
            warning(f"Proxy acima do orçamento do lote; dividindo: {path.name}")
            result.extend(split_large_proxy_for_handoff(project_dir, path, payload_budget))
            continue
        # Imagens anormalmente grandes são convertidas para uma prévia JPEG.
        try:
            from PIL import Image, ImageOps
            target = project_dir / "_CHATGPT_CACHE" / "imagens_reduzidas" / f"{path.stem}.jpg"
            target.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(path) as opened:
                image = ImageOps.exif_transpose(opened).convert("RGB")
                image.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
                image.save(target, "JPEG", quality=80, optimize=True)
            if target.stat().st_size > payload_budget:
                raise AutoEditeError(f"Imagem ainda grande demais: {path.name}")
            result.append(target)
        except Exception as exc:
            raise AutoEditeError(f"Não foi possível preparar {path.name} para o ChatGPT: {exc}") from exc
    return result


def _chatgpt_arcname(path: Path, project_dir: Path) -> str:
    if "contatos_visuais" in path.parts:
        return f"contatos_visuais/{path.name}"
    if "fontes_contexto" in path.parts:
        return f"fontes_contexto/{path.name}"
    if "social" in path.parts and "planos" in path.parts:
        return f"social/planos/{path.name}"
    if "proxies_divididos" in path.parts:
        return f"proxies_divididos/{path.name}"
    if path.parent == project_dir / "proxies":
        return f"proxies/{path.name}"
    return path.name


def _write_chatgpt_archive(
    target: Path, metadata: list[Path], fonts: list[Path], payloads: list[Path],
    project_dir: Path,
) -> None:
    temporary = target.with_suffix(".zip.tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=3, allowZip64=True) as archive:
        for path in metadata:
            archive.write(path, _chatgpt_arcname(path, project_dir))
        for path in fonts:
            archive.write(path, f"assets/fonts/{path.name}")
        for path in payloads:
            archive.write(path, _chatgpt_arcname(path, project_dir))
    with zipfile.ZipFile(temporary) as archive:
        bad = archive.testzip()
        if bad:
            raise AutoEditeError(f"Lote ZIP inválido; primeira entrada com erro: {bad}")
    temporary.replace(target)


def create_chatgpt_package(project_dir: Path, answers: dict[str, Any]) -> list[Path]:
    answers = normalize_answers(answers)
    configured_mb = float(answers.get("handoff", {}).get("chatgpt_lot_max_mb", 145))
    max_mb = min(149.0, max(10.0, configured_mb))
    max_bytes = int(max_mb * 1024 * 1024)
    staging_dir = project_dir / "_PACOTE_CHATGPT_NOVO"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)
    metadata_names = [
        "00_LEIA_PRIMEIRO.md", "PROMPT_PRONTO_PARA_CHATGPT.md", "QUESTIONARIO_RESPONDIDO.json",
        "MANIFESTO_MEDIA.json", "MANIFESTO_MEDIA.csv", "EDIT_PLAN.json", "EDIT_PLAN_AUTO.json",
        "fr_brand_profile.json", "franco-romeu-logo.png", "EDIT_PLAN_SCHEMA.json",
        "CONTEXTO_PROJETO.md", "CARD_STYLE.json", "FR_CONTENT_STRATEGY.json", "SOCIAL_PLAN.json",
        "ROTEIRO_MESTRE_PARA_IA.md", "PUBLICACAO_SOCIAL.md", "PUBLICACAO_SOCIAL.json",
        "RELATORIO_ANALISE_LOCAL.json", "RELATORIO_ORGANIZACAO.json", "CONTATO_GERAL_CODEX.jpg"
    ]
    metadata = [project_dir / name for name in metadata_names if (project_dir / name).is_file()]
    metadata += sorted((project_dir / "contatos_visuais").glob("*.jpg"))
    metadata += sorted((project_dir / "social" / "planos").glob("*.json"))
    metadata += sorted(path for path in (project_dir / "fontes_contexto").glob("*") if path.is_file())
    bundled_fonts = sorted(FONTS.glob("*.ttf"))
    base_size = sum(path.stat().st_size for path in metadata + bundled_fonts)
    safety = 3 * 1024 * 1024
    payload_budget = max_bytes - base_size - safety
    if payload_budget < 5 * 1024 * 1024:
        raise AutoEditeError(
            f"Os documentos fixos ocupam {base_size / 1024**2:.1f} MB e não cabem com segurança "
            f"num lote de {max_mb:.1f} MB. Remova anexos opcionais ou aumente o limite."
        )
    proxies = sorted(path for path in (project_dir / "proxies").glob("*") if path.is_file())
    payloads = handoff_proxy_items(project_dir, proxies, payload_budget)
    pending = partition_by_size(payloads, payload_budget) if payloads else [[]]
    staged: list[Path] = []
    index = 1
    while pending:
        payload_lot = pending.pop(0)
        target = staging_dir / f"FR_AUTOEDITE_LOTE_{index:03d}.zip"
        _write_chatgpt_archive(target, metadata, bundled_fonts, payload_lot, project_dir)
        if target.stat().st_size >= 150 * 1024 * 1024 or target.stat().st_size > max_bytes:
            if len(payload_lot) <= 1:
                raise AutoEditeError(
                    f"{target.name} ficou com {target.stat().st_size / 1024**2:.1f} MB mesmo isolado. "
                    "Reduza o proxy ou o limite configurado."
                )
            midpoint = max(1, len(payload_lot) // 2)
            pending.insert(0, payload_lot[midpoint:])
            pending.insert(0, payload_lot[:midpoint])
            target.unlink(missing_ok=True)
            continue
        staged.append(target)
        index += 1
    package_dir = project_dir / "pacote_chatgpt"
    if package_dir.exists():
        history = project_dir / "_HISTORICO" / f"pacote_chatgpt_{dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"
        history.parent.mkdir(parents=True, exist_ok=True)
        package_dir.replace(history)
    staging_dir.replace(package_dir)
    outputs = [package_dir / path.name for path in staged]
    upload_lines = [
        "# ANEXE TODOS OS LOTES ABAIXO NA MESMA CONVERSA DO CHATGPT",
        "# Cada arquivo foi validado e possui menos de 150 MB.",
        "",
        *(f"{path}  |  {path.stat().st_size / 1024**2:.1f} MB" for path in outputs),
        "",
        f"# Depois envie o conteúdo deste arquivo:",
        str(project_dir / "PROMPT_PRONTO_PARA_CHATGPT.md"),
    ]
    write_text(project_dir / "UPLOAD_LIST.txt", "\n".join(upload_lines) + "\n")
    shutil.copy2(project_dir / "UPLOAD_LIST.txt", package_dir / "UPLOAD_LIST.txt")
    send_dir = project_dir / "_ENVIAR_CHATGPT"
    send_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(project_dir / "UPLOAD_LIST.txt", send_dir / "01_LISTA_EXATA_DE_ARQUIVOS.txt")
    shutil.copy2(project_dir / "PROMPT_PRONTO_PARA_CHATGPT.md", send_dir / "02_PROMPT_PARA_ENVIAR.md")
    guide = [
        "# Envio ao ChatGPT — passo a passo", "",
        "1. Abra `01_LISTA_EXATA_DE_ARQUIVOS.txt`.",
        "2. Anexe TODOS os lotes indicados na mesma conversa, sem extrair os ZIPs.",
        "3. Aguarde os anexos terminarem de carregar.",
        "4. Envie o conteúdo de `02_PROMPT_PARA_ENVIAR.md`.",
        "5. Para edição integral por qualquer IA, envie também `03_ROTEIRO_MESTRE_PARA_IA.md` e peça a devolução do mesmo Markdown preenchido.",
        "6. Importe o Markdown respondido no Studio; ele atualiza filme, Reels e publicação com backup.", "",
        f"Pasta dos lotes: `{package_dir}`", "",
        "Os lotes são múltiplos arquivos ZIP independentes; não são pedaços binários que precisem ser reconstruídos.",
    ]
    write_text(send_dir / "00_COMO_ENVIAR.md", "\n".join(guide) + "\n")
    ai_dir = project_dir / "_ENVIAR_IA"
    ai_dir.mkdir(parents=True, exist_ok=True)
    ai_guide = [
        "# CENTRAL ÚNICA — ARQUIVOS PARA QUALQUER IA", "",
        "## EDITE E DEVOLVA", "",
        "- `01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE_IA.md` — este é o ÚNICO arquivo que a IA deve alterar.", "",
        "## APENAS ENVIE; NÃO EDITE", "",
        "- `02_NAO_EDITAR_APENAS_ENVIAR_PROMPT.md` — instrução inicial para a IA.",
        "- `03_NAO_EDITAR_LISTA_DE_LOTES.txt` — lista dos ZIPs de mídia que devem acompanhar o roteiro.",
        "- Os lotes `FR_AUTOEDITE_LOTE_*.zip` ficam em `../pacote_chatgpt/` e têm menos de 150 MB.", "",
        "## DEVOLUÇÃO", "",
        "Salve a resposta da IA como Markdown e importe-a no botão `Enviar resposta` do Studio.",
        "O FR AutoEdite valida IDs, tempos, transições e limites antes de aplicar qualquer mudança.",
    ]
    write_text(ai_dir / "00_COMECE_AQUI_O_QUE_EDITAR_E_ENVIAR.md", "\n".join(ai_guide) + "\n")
    shutil.copy2(project_dir / "PROMPT_PRONTO_PARA_CHATGPT.md", ai_dir / "02_NAO_EDITAR_APENAS_ENVIAR_PROMPT.md")
    shutil.copy2(project_dir / "UPLOAD_LIST.txt", ai_dir / "03_NAO_EDITAR_LISTA_DE_LOTES.txt")
    info(f"Pacote ChatGPT: {len(outputs)} lote(s), máximo real {max_mb:.1f} MB; todos abaixo de 150 MB")
    return outputs


def context_keywords(value: str) -> list[str]:
    stop = {
        "para", "com", "sem", "uma", "uns", "das", "dos", "que", "deve", "depois",
        "antes", "entre", "sobre", "como", "todo", "toda", "todos", "todas", "esta",
        "este", "essa", "esse", "pela", "pelo", "mais", "menos", "etapa",
    }
    words = re.findall(r"[A-Za-zÀ-ÿ0-9]+", normalize_search(value))
    result = []
    for word in words:
        if len(word) < 3 or word in stop or word in result:
            continue
        result.append(word)
    return result[:12]


def phases_from_context(text: str) -> list[dict[str, Any]]:
    phases: list[dict[str, Any]] = []
    pattern = re.compile(r"^\s*(\d{1,2})[.)-]\s+(.+?)\s*$")
    for raw in text.splitlines():
        match = pattern.match(raw)
        if not match:
            continue
        content = match.group(2).strip().strip("#*- ")
        if not content or len(content) > 500:
            continue
        if "|" in content:
            title, description = [part.strip() for part in content.split("|", 1)]
        elif ":" in content:
            title, description = [part.strip() for part in content.split(":", 1)]
        else:
            title, description = content, content
        phases.append({
            "order": len(phases) + 1,
            "title": title.upper()[:100],
            "description": description[:500],
            "keywords": context_keywords(f"{title} {description}"),
        })
        if len(phases) >= 20:
            break
    return phases if len(phases) >= 2 else []


def read_context_argument(value: str) -> tuple[str, Path | None]:
    if "\n" in value or len(value) > 240:
        return value.strip(), None
    possible = expand_path(value)
    if possible.is_file():
        if possible.suffix.lower() not in {".md", ".txt", ".json", ".yaml", ".yml", ".csv"}:
            return (
                f"Arquivo de contexto fornecido: {possible.name}. "
                "O conteúdo binário foi preservado para revisão no ChatGPT; descreva a ordem no questionário se necessário.",
                possible,
            )
        try:
            return possible.read_text(encoding="utf-8"), possible
        except UnicodeDecodeError as exc:
            raise AutoEditeError(
                "O arquivo de contexto precisa ser texto UTF-8 (.md, .txt, .json ou .yaml)."
            ) from exc
    return value.strip(), None


def first_context_paragraph(text: str) -> str:
    blocks = []
    for raw in re.split(r"\n\s*\n", text):
        if raw.lstrip().startswith("#") and "\n" not in raw.strip():
            continue
        block = re.sub(r"\s+", " ", raw.strip("#*- \n"))
        if block and not re.match(r"^\d{1,2}[.)-]\s+", block):
            blocks.append(block)
    return (blocks[0] if blocks else "Documentar o projeto Franco Romeu.")[:900]


def project_name_from_context(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            value = line.lstrip("# ").strip()
            if value:
                return value[:120]
    return fallback


def answers_from_context(
    zip_path: Path, context_value: str, name: str | None, mode: str,
    target_duration: float, average_clip: float, reel_durations: list[int],
    workspace_root: Path | None = None, random_seed: int | None = None,
) -> dict[str, Any]:
    answers = read_json(TEMPLATES / "questionario_base.json")
    text, context_path = read_context_argument(context_value)
    fallback = zip_path.stem.replace("_", " ").replace("-", " ").strip() or "Projeto Franco Romeu"
    project_name = name or project_name_from_context(text, fallback)
    answers["project"].update({
        "name": project_name,
        "slug": slugify(project_name),
        "zip_path": str(zip_path),
        "workspace_root": str(workspace_root or DEFAULT_WORKSPACE),
        "context_file": str(context_path) if context_path else "",
    })
    summary = first_context_paragraph(text)
    answers["context"].update({
        "summary": summary,
        "desired_message": summary,
        "notes": "" if context_path else text,
    })
    answers["story"]["objective"] = summary
    extracted_phases = phases_from_context(text)
    if extracted_phases:
        answers["story"]["chronology"] = extracted_phases
        answers["story"]["priority"] = "A sequência numerada no contexto fornecido prevalece."
    answers["edition"].update({
        "order_mode": normalize_order_mode(mode),
        "target_duration_sec": float(target_duration),
        "average_clip_duration_sec": float(average_clip),
    })
    if normalize_order_mode(mode) == "aleatorio":
        answers.setdefault("random_mode", {}).update({"enabled": True, "seed": random_seed})
    answers["social"]["reel_durations_sec"] = reel_durations or [30, 60, 90]
    return normalize_answers(answers)


def questionnaire_interactive(base: dict[str, Any]) -> dict[str, Any]:
    print("\nFR AUTOEDITE — QUESTIONÁRIO DO PROJETO\n")

    def ask(label: str, default: Any = "") -> str:
        suffix = f" [{default}]" if default not in (None, "") else ""
        value = input(f"{label}{suffix}: ").strip()
        return value or str(default)

    project = base["project"]
    project["name"] = ask("Nome do projeto", project["name"])
    project["slug"] = slugify(ask("Identificador curto", slugify(project["name"])))
    project["client"] = ask("Cliente (opcional)", project.get("client", ""))
    project["location"] = ask("Cidade/região", project.get("location", "São Paulo, SP"))
    project["zip_path"] = ask("Caminho do ZIP do Google Fotos", project.get("zip_path", str(DEFAULT_ZIP)))
    project["workspace_root"] = ask("Pasta para os projetos", project.get("workspace_root", str(DEFAULT_WORKSPACE)))
    project["context_file"] = ask("Arquivo de contexto opcional (.md/.txt/.json/.yaml)", project.get("context_file", ""))
    context = base.setdefault("context", {})
    context["summary"] = ask("Resumo do contexto", context.get("summary", ""))
    context["desired_message"] = ask("Mensagem central desejada", context.get("desired_message", ""))
    context["cta"] = ask("Chamada para ação", context.get("cta", "Vamos dimensionar sua obra."))
    story = base["story"]
    story["objective"] = ask("Objetivo do vídeo", story.get("objective", ""))
    story["audience"] = ask("Público principal", story.get("audience", ""))
    print("\nCronologia: escreva uma etapa por linha no formato TÍTULO | descrição | palavra1,palavra2")
    print("Pressione Enter numa linha vazia para terminar. Digite apenas Enter agora para manter o modelo padrão.")
    phases = []
    while True:
        raw = input(f"Etapa {len(phases) + 1}: ").strip()
        if not raw:
            break
        parts = [part.strip() for part in raw.split("|", 2)]
        title = parts[0]
        description = parts[1] if len(parts) > 1 else ""
        keywords = [k.strip() for k in parts[2].split(",")] if len(parts) > 2 else []
        phases.append({"order": len(phases) + 1, "title": title.upper(), "description": description, "keywords": keywords})
    if phases:
        story["chronology"] = phases
    edition = base["edition"]
    edition["order_mode"] = normalize_order_mode(
        ask(
            "Modo de edição: automatico, cronologico, alfabetico ou aleatorio",
            edition.get("order_mode", "automatico"),
        )
    )
    if edition["order_mode"] == "aleatorio":
        seed_value = ask(
            "Seed aleatória (vazio gera uma nova)",
            base.get("random_mode", {}).get("seed") or "",
        )
        base.setdefault("random_mode", {}).update({
            "enabled": True,
            "seed": int(seed_value) if seed_value.strip() else None,
        })
    edition["target_duration_sec"] = float(ask("Duração aproximada do filme longo (segundos)", edition.get("target_duration_sec", 360)))
    edition["average_clip_duration_sec"] = float(
        ask("Tempo médio de cada corte (segundos)", edition.get("average_clip_duration_sec", 6))
    )
    format_value = ask("Formato: vertical, horizontal ou quadrado", edition.get("format", "vertical")).lower()
    if format_value.startswith("h"):
        edition.update({"format": "horizontal", "width": 1280, "height": 720})
    elif format_value.startswith("q"):
        edition.update({"format": "quadrado", "width": 1080, "height": 1080})
    else:
        edition.update({"format": "vertical", "width": 720, "height": 1280})
    edition["music_path"] = ask("Trilha local (opcional; deixe vazio para manter somente áudio original)", "")
    social = base.setdefault("social", {})
    durations = ask(
        "Cortes para Reels, separados por vírgula",
        ",".join(str(value) for value in social.get("reel_durations_sec", [30, 60, 90])),
    )
    social["reel_durations_sec"] = [
        int(float(value.strip())) for value in durations.split(",") if value.strip()
    ]
    social["carousel_slides"] = int(float(ask("Quantidade de cards do carrossel", social.get("carousel_slides", 8))))
    lot = ask("Tamanho máximo de cada lote para ChatGPT em MB", base["handoff"].get("chatgpt_lot_max_mb", 145))
    base["handoff"]["chatgpt_lot_max_mb"] = int(float(lot))
    return base


def create_questionnaire(output: Path, example: bool = False, interactive: bool = True) -> dict[str, Any]:
    template = read_json(TEMPLATES / "questionario_base.json")
    if example:
        template = read_json(APP_ROOT / "examples" / "cozinha_carreira.questionario.json")
    answers = normalize_answers(questionnaire_interactive(template) if interactive else template)
    write_json(output, answers)
    info(f"Questionário salvo: {output}")
    return answers


def project_paths(answers: dict[str, Any], project_override: str | None = None) -> tuple[Path, Path]:
    zip_path = expand_path(answers["project"].get("zip_path") or DEFAULT_ZIP)
    if project_override:
        project_dir = expand_path(project_override)
    else:
        root = expand_path(answers["project"].get("workspace_root") or DEFAULT_WORKSPACE)
        project_dir = root / slugify(answers["project"].get("slug") or answers["project"]["name"])
    return zip_path, project_dir


def prepare(zip_path: Path, project_dir: Path, answers: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    check_runtime()
    answers = normalize_answers(answers)
    project_dir.mkdir(parents=True, exist_ok=True)
    for folder in ("_ENTRADA", "_EDITAR", "_ENVIAR_IA", "_ENVIAR_CHATGPT", "_HISTORICO"):
        (project_dir / folder).mkdir(parents=True, exist_ok=True)
    central_zip = project_dir / "_ENTRADA" / "FR_AUTOEDITE_ENTRADA.zip"
    if zip_path.resolve() != central_zip.resolve() and not central_zip.exists():
        _safe_media_link(zip_path, central_zip)
    write_json(project_dir / "QUESTIONARIO_RESPONDIDO.json", answers)
    write_json(project_dir / "FR_AUTOEDITE_PROJECT.json", {
        "application_version": APP_VERSION,
        "created_or_updated_at": now_iso(),
        "zip_path": str(zip_path),
        "project_dir": str(project_dir),
    })
    info(f"Extraindo com segurança: {zip_path}")
    safe_extract(zip_path, project_dir / "originais")
    info("Catalogando mídias e criando proxies")
    manifest = build_manifest(project_dir, answers)
    plan = build_auto_plan(project_dir, answers, manifest)
    plan = run_optional_copilot(project_dir, answers, manifest, plan)
    write_handoff_files(project_dir, answers, manifest)
    sync_card_style_from_answers(project_dir, answers)
    build_social_plans(project_dir, answers, plan, manifest)
    if answers.get("editing_brief", {}).get("auto_generate", True):
        generate_ai_editing_brief(project_dir, answers, plan, manifest)
    if answers.get("cards", {}).get("generate_previews", True):
        generate_card_previews(project_dir, project_dir / "EDIT_PLAN.json")
    create_chatgpt_package(project_dir, answers)
    editable_files = [
        (project_dir / "QUESTIONARIO_RESPONDIDO.json", project_dir / "_EDITAR" / "01_CONFIGURACOES_DO_PROJETO.json"),
        (project_dir / "EDIT_PLAN.json", project_dir / "_EDITAR" / "02_PLANO_DA_EDICAO.json"),
        (project_dir / "CARD_STYLE.json", project_dir / "_EDITAR" / "03_DESIGN_DOS_CARDS.json"),
    ]
    for source, target in editable_files:
        if source.is_file():
            shutil.copy2(source, target)
    navigation = f"""# MAPA RÁPIDO DO PROJETO

## Você coloca ou edita
- ZIP: `{project_dir / '_ENTRADA' / 'FR_AUTOEDITE_ENTRADA.zip'}`
- Contexto: `{project_dir / '_ENTRADA' / 'CONTEXTO_PROJETO.md'}`
- Configurações: `{project_dir / '_EDITAR' / '01_CONFIGURACOES_DO_PROJETO.json'}`
- Timeline/plano: `{project_dir / '_EDITAR' / '02_PLANO_DA_EDICAO.json'}`
- Design: `{project_dir / '_EDITAR' / '03_DESIGN_DOS_CARDS.json'}`
- Roteiro único para qualquer IA: `{project_dir / '_ENVIAR_IA' / '01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE_IA.md'}`
- Intro personalizada: `{project_dir / '_ENTRADA' / 'INTRO_PERSONALIZADA.*'}`
- Outro personalizado: `{project_dir / '_ENTRADA' / 'OUTRO_PERSONALIZADO.*'}`

## Você envia a qualquer IA — tudo centralizado
- Comece aqui: `{project_dir / '_ENVIAR_IA' / '00_COMECE_AQUI_O_QUE_EDITAR_E_ENVIAR.md'}`
- EDITE E DEVOLVA: `{project_dir / '_ENVIAR_IA' / '01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE_IA.md'}`
- NÃO EDITE, apenas envie: `{project_dir / '_ENVIAR_IA' / '02_NAO_EDITAR_APENAS_ENVIAR_PROMPT.md'}`
- NÃO EDITE, lista de lotes: `{project_dir / '_ENVIAR_IA' / '03_NAO_EDITAR_LISTA_DE_LOTES.txt'}`

## Você revisa e entrega
- Rascunhos e masters: `{project_dir / 'entrega'}`
- Relatórios: `{project_dir}`

Abra o painel com: `fr-autoedite studio`
"""
    write_text(project_dir / "00_MAPA_RAPIDO.md", navigation)
    info(f"Projeto pronto para revisão: {project_dir}")
    return manifest, plan


def status(project_dir: Path) -> None:
    print(f"Projeto: {project_dir}")
    for name in (
        "QUESTIONARIO_RESPONDIDO.json", "CONTEXTO_PROJETO.md", "MANIFESTO_MEDIA.json",
        "EDIT_PLAN.json", "CARD_STYLE.json", "SOCIAL_PLAN.json",
        "ROTEIRO_MESTRE_PARA_IA.md", "PUBLICACAO_SOCIAL.md",
        "PROMPT_PRONTO_PARA_CHATGPT.md", "UPLOAD_LIST.txt",
    ):
        path = project_dir / name
        print(f"  {'OK' if path.is_file() else '--'}  {name}")
    for folder in (
        "originais", "proxies", "miniaturas", "contatos_visuais", "cards_editaveis",
        "pacote_chatgpt", "social", "entrega",
    ):
        path = project_dir / folder
        count = sum(1 for p in path.rglob("*") if p.is_file()) if path.is_dir() else 0
        print(f"  {count:4d} arquivo(s)  {folder}/")


@isolated_render
def render_draft(project_dir: Path, only: str = "both") -> list[Path]:
    """Renderiza uma prova leve sem alterar o plano principal."""
    source = project_dir / "EDIT_PLAN.json"
    plan = copy.deepcopy(read_json(source))
    output = plan.setdefault("output", {})
    width = int(output.get("width", 720))
    height = int(output.get("height", 1280))
    if width == height:
        draft_width, draft_height = 480, 480
    elif width > height:
        draft_width, draft_height = 854, 480
    else:
        draft_width, draft_height = 480, 854
    output.update({
        "width": draft_width,
        "height": draft_height,
        "fps": 15,
        "delivery_label": "RASCUNHO_480P",
        "render_source": "proxies",
    })
    effects = plan.setdefault("visual_effects", {})
    effects.update({
        "speed_ramping": False,
        "enable_stabilization": False,
        "color_lut": "",
        "transition_duration_sec": min(0.18, float(effects.get("transition_duration_sec", 0.18))),
    })
    plan.setdefault("audio", {})["music_path"] = ""
    plan["review_status"] = "DRAFT_REQUIRES_FULL_VISUAL_REVIEW"
    draft_plan = project_dir / "EDIT_PLAN_DRAFT.json"
    write_json(draft_plan, plan)
    results = render_plan(project_dir, draft_plan, use_proxies=True, only=only)
    guide = [
        "# Revisão do rascunho", "",
        "Assista cada arquivo do início ao fim antes da master.",
        "Ajuste a ordem, os tempos e os textos na Timeline do Studio ou em `EDIT_PLAN.json`.",
        "Depois use `fr-autoedite auditar` e gere a master pelos originais.", "",
        *(f"- `{path}`" for path in results),
    ]
    write_text(project_dir / "entrega" / "00_COMO_REVISAR_O_RASCUNHO.md", "\n".join(guide) + "\n")
    return results


def audit_project(project_dir: Path) -> dict[str, Any]:
    """Auditoria legível e mecânica antes da renderização ou do envio."""
    project_dir = project_dir.resolve()
    checks: list[dict[str, Any]] = []

    def record(name: str, ok: bool, detail: str, severity: str = "erro") -> None:
        checks.append({"check": name, "ok": bool(ok), "severity": severity, "detail": detail})

    required = [
        "QUESTIONARIO_RESPONDIDO.json", "MANIFESTO_MEDIA.json", "EDIT_PLAN.json",
        "CARD_STYLE.json", "PROMPT_PRONTO_PARA_CHATGPT.md", "ROTEIRO_MESTRE_PARA_IA.md",
    ]
    for name in required:
        path = project_dir / name
        record(f"arquivo:{name}", path.is_file(), str(path))

    json_files = [
        "QUESTIONARIO_RESPONDIDO.json", "MANIFESTO_MEDIA.json", "EDIT_PLAN.json", "CARD_STYLE.json",
    ]
    parsed: dict[str, dict[str, Any]] = {}
    for name in json_files:
        path = project_dir / name
        if not path.is_file():
            continue
        try:
            parsed[name] = read_json(path)
            record(f"json:{name}", True, "JSON válido")
        except AutoEditeError as exc:
            record(f"json:{name}", False, str(exc))

    manifest = parsed.get("MANIFESTO_MEDIA.json", {})
    rows = {str(row.get("id")): row for row in manifest.get("media", [])}
    plan = parsed.get("EDIT_PLAN.json", {})
    unknown_ids: list[str] = []
    out_of_bounds: list[str] = []
    missing_sources: list[str] = []
    for segment in plan.get("segments", []):
        if segment.get("type") != "media" or not segment.get("enabled", True):
            continue
        if segment.get("external_asset"):
            relative = str(segment.get("source_path") or "")
            source = Path(relative) if Path(relative).is_absolute() else project_dir / relative
            if not source.is_file():
                missing_sources.append(relative or str(segment.get("segment_id")))
            start = float(segment.get("start_sec") or 0)
            duration = float(segment.get("duration_sec") or 0)
            source_span = duration * segment_playback_speed(segment)
            upper = float(segment.get("source_duration_sec") or 0)
            if duration <= 0 or start < 0 or (upper > 0 and start + source_span > upper + 0.20):
                out_of_bounds.append(
                    f"{segment.get('segment_id')}:mídia externa "
                    f"({start:.2f}+{source_span:.2f}s fonte; limite 0–{upper:.2f}s)"
                )
            continue
        media_id = str(segment.get("media_id") or "")
        row = rows.get(media_id)
        if not row:
            unknown_ids.append(media_id or str(segment.get("segment_id")))
            continue
        relative = str(segment.get("source_path") or row.get("source_path") or "")
        if relative and not (project_dir / relative).is_file():
            missing_sources.append(relative)
        start = float(segment.get("start_sec") or 0)
        duration = float(segment.get("duration_sec") or 0)
        source_span = duration * segment_playback_speed(segment)
        if row.get("parent_video"):
            lower = float(row.get("scene_start_sec") or 0)
            upper = lower + float(row.get("duration_sec") or 0)
        else:
            lower = 0.0
            upper = float(row.get("duration_sec") or 0)
        invalid_bounds = duration <= 0
        if row.get("media_type") == "video":
            invalid_bounds = invalid_bounds or start < lower - 0.05 or (
                upper > 0 and start + source_span > upper + 0.20
            )
        if invalid_bounds:
            out_of_bounds.append(
                f"{segment.get('segment_id')}:{media_id} "
                f"({start:.2f}+{source_span:.2f}s fonte; limite {lower:.2f}–{upper:.2f}s)"
            )
    record("timeline:ids", not unknown_ids, "OK" if not unknown_ids else ", ".join(unknown_ids[:20]))
    record("timeline:limites", not out_of_bounds, "OK" if not out_of_bounds else "; ".join(out_of_bounds[:12]))
    record("timeline:fontes", not missing_sources, "OK" if not missing_sources else "; ".join(missing_sources[:12]))

    reel_plans = sorted((project_dir / "social" / "planos").glob("REEL_*S.json"))
    record("reels:planos", bool(reel_plans), f"{len(reel_plans)} plano(s)", severity="aviso")
    for reel_path in reel_plans:
        try:
            reel = read_json(reel_path)
            enabled_media = [
                segment for segment in reel.get("segments", [])
                if segment.get("type") == "media" and not segment.get("external_asset") and segment.get("enabled", True)
            ]
            roles = {str(segment.get("coverage_role") or "") for segment in enabled_media}
            arc_ok = bool(enabled_media) and "inicio" in roles and "fim" in roles
            record(
                f"reels:arco:{reel_path.name}", arc_ok,
                "início–meio–fim preservado" if arc_ok else "revise: falta início ou fim no Reel",
            )
        except AutoEditeError as exc:
            record(f"reels:json:{reel_path.name}", False, str(exc))

    lot_dir = project_dir / "pacote_chatgpt"
    lots = sorted(lot_dir.glob("FR_AUTOEDITE_LOTE_*.zip")) if lot_dir.is_dir() else []
    record("chatgpt:lotes", bool(lots), f"{len(lots)} lote(s)")
    for lot in lots:
        size_mb = lot.stat().st_size / 1024**2
        size_ok = lot.stat().st_size < 150 * 1024 * 1024
        crc_ok = False
        detail = f"{size_mb:.1f} MB"
        try:
            with zipfile.ZipFile(lot) as archive:
                bad = archive.testzip()
            crc_ok = bad is None
            if bad:
                detail += f"; CRC inválido em {bad}"
        except (OSError, zipfile.BadZipFile) as exc:
            detail += f"; ZIP inválido: {exc}"
        record(f"chatgpt:{lot.name}", size_ok and crc_ok, detail)

    originals = project_dir / "originais"
    record(
        "originais:preservados", originals.is_dir() and any(path.is_file() for path in originals.rglob("*")),
        str(originals),
    )
    warnings_count = sum(1 for item in checks if not item["ok"] and item["severity"] == "aviso")
    errors_count = sum(1 for item in checks if not item["ok"] and item["severity"] == "erro")
    report = {
        "schema_version": 1,
        "application": f"FR AutoEdite {APP_VERSION}",
        "generated_at": now_iso(),
        "project_dir": str(project_dir),
        "passed": errors_count == 0,
        "errors": errors_count,
        "warnings": warnings_count,
        "checks": checks,
    }
    write_json(project_dir / "RELATORIO_AUDITORIA.json", report)
    lines = [
        "# Relatório de auditoria — FR AutoEdite", "",
        f"Resultado: **{'APROVADO' if report['passed'] else 'PENDÊNCIAS ENCONTRADAS'}**", "",
        f"Erros: {errors_count}  ", f"Avisos: {warnings_count}", "", "## Verificações", "",
    ]
    for item in checks:
        marker = "OK" if item["ok"] else "PENDÊNCIA"
        lines.append(f"- **{marker}** — `{item['check']}`: {item['detail']}")
    lines += ["", "A auditoria técnica não substitui assistir integralmente aos vídeos antes da publicação.", ""]
    write_text(project_dir / "RELATORIO_AUDITORIA.md", "\n".join(lines))
    info(f"Auditoria: {'aprovada' if report['passed'] else f'{errors_count} pendência(s)'} — {project_dir / 'RELATORIO_AUDITORIA.md'}")
    return report


def export_to_cloud(project_dir: Path, *, test_only: bool = False) -> dict[str, Any]:
    """Envia entregas pelo rclone; a autenticação permanece no cofre/configuração local dele."""
    questionnaire = project_dir / "QUESTIONARIO_RESPONDIDO.json"
    if not questionnaire.is_file():
        raise AutoEditeError("Configurações do projeto não encontradas para exportação.")
    answers = normalize_answers(read_json(questionnaire))
    config = answers.get("cloud_export", {})
    if not config.get("enabled") and not test_only:
        raise AutoEditeError("Ative a exportação em Nuvem no Studio antes de enviar.")
    rclone = shutil.which("rclone")
    if not rclone:
        raise AutoEditeError(
            "rclone não está instalado. No Parrot/Debian: sudo apt install -y rclone; "
            "depois execute rclone config e autorize a conta Google desejada."
        )
    remote = str(config.get("rclone_remote") or "gdrive").strip().rstrip(":")
    if not re.fullmatch(r"[A-Za-z0-9_. -]+", remote):
        raise AutoEditeError("Nome do destino rclone inválido.")
    listed = run([rclone, "listremotes"], capture=True, check=False)
    available = {line.strip().rstrip(":") for line in (listed.stdout or "").splitlines() if line.strip()}
    if remote not in available:
        raise AutoEditeError(
            f"O destino '{remote}' ainda não existe no rclone. Execute rclone config, "
            "crie um Google Drive e use exatamente o mesmo nome no Studio."
        )
    if test_only:
        probe = run([rclone, "lsd", f"{remote}:"], capture=True, check=False)
        if probe.returncode != 0:
            raise AutoEditeError(f"A autorização do Google Drive falhou: {(probe.stderr or '')[-900:]}")
        info(f"Google Drive acessível pelo destino rclone '{remote}'.")
        return {"status": "ok", "remote": remote, "test_only": True}
    folder = str(config.get("remote_folder") or "FR-AutoEdite/Entregas").strip().strip("/")
    if not folder or ".." in Path(folder).parts or ":" in folder:
        raise AutoEditeError("Pasta remota inválida.")
    destination = f"{remote}:{folder}/{slugify(project_dir.name)}"
    sources: list[tuple[str, Path]] = []
    if config.get("include_master", True) and (project_dir / "entrega").is_dir():
        sources.append(("master", project_dir / "entrega"))
    if config.get("include_social", True) and (project_dir / "social").is_dir():
        sources.append(("social", project_dir / "social"))
    if config.get("include_project_files", False):
        bundle = project_dir / "entrega" / f"FR_{slugify(project_dir.name).upper()}_ARQUIVOS_EDITAVEIS.zip"
        names = [
            "QUESTIONARIO_RESPONDIDO.json", "EDIT_PLAN.json", "CARD_STYLE.json",
            "MANIFESTO_MEDIA.json", "RELATORIO_AUDITORIA.md", "CONTEXTO_PROJETO.md",
            "ROTEIRO_MESTRE_PARA_IA.md", "PUBLICACAO_SOCIAL.md", "PUBLICACAO_SOCIAL.json",
        ]
        with zipfile.ZipFile(bundle.with_suffix(".zip.tmp"), "w", zipfile.ZIP_DEFLATED) as archive:
            for name in names:
                candidate = project_dir / name
                if candidate.is_file():
                    archive.write(candidate, name)
        bundle.with_suffix(".zip.tmp").replace(bundle)
        sources.append(("editaveis", bundle))
    if not sources:
        raise AutoEditeError("Nenhuma entrega foi encontrada para enviar. Renderize primeiro.")
    uploaded = []
    for label, source in sources:
        target = f"{destination}/{label}"
        command = [rclone, "copy", str(source), target, "--transfers", "2", "--checkers", "4", "--create-empty-src-dirs"]
        result = run(command, capture=True, check=False)
        if result.returncode != 0:
            raise AutoEditeError(f"Falha no envio de {label}: {(result.stderr or '')[-1200:]}")
        uploaded.append({"label": label, "source": str(source), "destination": target})
    report = {
        "schema_version": 1, "application": f"FR AutoEdite {APP_VERSION}",
        "generated_at": now_iso(), "account_email_label": config.get("account_email", ""),
        "remote": remote, "destination": destination, "uploaded": uploaded,
    }
    write_json(project_dir / "entrega" / "RELATORIO_ENVIO_NUVEM.json", report)
    if config.get("open_google_photos_after_export"):
        webbrowser.open("https://photos.google.com/")
    info(f"Envio ao Google Drive concluído: {destination}")
    return report


def configure_copilot(provider: str, model: str, key: str | None = None) -> None:
    try:
        from copilot import CopilotError, CredentialStore

        storage = CredentialStore().configure(provider, model, key)
    except Exception as exc:
        raise AutoEditeError(f"Não foi possível configurar o Copiloto: {exc}") from exc
    if storage == "system_keyring":
        info(f"Copiloto {provider} configurado no cofre do sistema; modelo {model}. A chave não foi exibida.")
    elif provider == "ollama":
        info(f"Copiloto local Ollama configurado; modelo {model}. Nenhuma chave é necessária.")
    else:
        warning(
            "O sistema não ofereceu um cofre de segredos. A chave foi apenas ofuscada em Base64 "
            "num arquivo com permissão 0600; Base64 não é criptografia. Prefira secret-tool ou variável de ambiente."
        )


def interactive_menu() -> int:
    print(textwrap.dedent(f"""
        FR AUTOEDITE {APP_VERSION}
        1. Abrir Studio visual (recomendado; auditoria multisselecionável)
        2. Novo projeto pelo terminal (ZIP + contexto)
        3. Criar/preencher questionário detalhado
        4. Preparar ZIP e gerar pacote ChatGPT
        5. Fazer tudo: preparar, filme longo e pacote social
        6. Renderizar um plano existente
        7. Renderizar Reels, Stories e carrossel
        8. Gerar prévias dos cards editáveis
        9. Auditar um projeto
        0. Sair
    """))
    choice = input("Escolha: ").strip()
    if choice == "0":
        return 0
    if choice == "1":
        from studio import launch_studio

        return launch_studio(APP_ROOT, DEFAULT_WORKSPACE)
    if choice == "2":
        zip_path = expand_path(input(f"Caminho do ZIP [{DEFAULT_ZIP}]: ").strip() or str(DEFAULT_ZIP))
        context_value = input("Arquivo de contexto ou resumo do projeto: ").strip()
        if not context_value:
            raise AutoEditeError("Informe um arquivo de contexto ou um resumo do projeto.")
        mode = input("Modo [automatico/cronologico/alfabetico/aleatorio] [automatico]: ").strip() or "automatico"
        answers = answers_from_context(zip_path, context_value, None, mode, 360, 6, [30, 60, 90])
        _, project_dir = project_paths(answers)
        prepare(zip_path, project_dir, answers)
        return 0
    if choice == "3":
        output = expand_path(input("Salvar questionário em [./questionario.json]: ").strip() or "./questionario.json")
        create_questionnaire(output)
        return 0
    if choice in {"4", "5"}:
        questionnaire = expand_path(input("Questionário existente (vazio para criar agora): ").strip() or "./questionario.json")
        if questionnaire.is_file():
            answers = read_json(questionnaire)
        else:
            answers = create_questionnaire(questionnaire)
        zip_path, project_dir = project_paths(answers)
        prepare(zip_path, project_dir, answers)
        if choice == "5":
            render_plan(project_dir, project_dir / "EDIT_PLAN.json")
            if answers.get("social", {}).get("enabled", True):
                render_social_outputs(project_dir, normalize_answers(answers))
        return 0
    project_dir = expand_path(input("Pasta do projeto: ").strip())
    if choice == "6":
        render_plan(project_dir, project_dir / "EDIT_PLAN.json")
    elif choice == "7":
        answers = normalize_answers(read_json(project_dir / "QUESTIONARIO_RESPONDIDO.json"))
        render_social_outputs(project_dir, answers)
    elif choice == "8":
        generate_card_previews(project_dir, project_dir / "EDIT_PLAN.json")
    elif choice == "9":
        audit_project(project_dir)
    else:
        raise AutoEditeError("Opção inválida.")
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="fr-autoedite",
        description="Automação gratuita Franco Romeu para ZIP do Google Fotos, curadoria e edição com FFmpeg."
    )
    root.add_argument("--versao", action="version", version=f"FR AutoEdite {APP_VERSION}")
    commands = root.add_subparsers(dest="command")
    studio = commands.add_parser(
        "studio", aliases=["wizard"],
        help="abrir a central visual local com auditoria e timeline",
    )
    studio.add_argument("--raiz", default=str(DEFAULT_WORKSPACE), help="pasta única dos projetos")
    studio.add_argument("--porta", type=int, default=8765, help="porta local; use 0 para escolher automaticamente")
    studio.add_argument("--sem-navegador", action="store_true")
    new = commands.add_parser("novo", help="fluxo universal: recebe apenas ZIP e contexto")
    new.add_argument("--zip", dest="zip_path", required=True, help="qualquer ZIP de fotos/vídeos")
    new.add_argument("--contexto", required=True, help="arquivo .md/.txt/.json/.yaml ou texto curto entre aspas")
    new.add_argument("--nome", help="nome do projeto; por padrão usa o título do contexto")
    new.add_argument("--modo", choices=tuple(sorted(ORDER_MODES)), default="automatico")
    new.add_argument("--seed", type=int, help="seed reproduzível para o modo aleatório")
    new.add_argument("--duracao-longa", type=float, default=360)
    new.add_argument("--duracao-media", type=float, default=6, help="tempo médio de cada corte")
    new.add_argument("--reels", default="30,60,90", help="durações separadas por vírgula")
    new.add_argument("--workspace-root", help="pasta que guardará os projetos")
    new.add_argument("--projeto", help="pasta exata do projeto")
    new.add_argument("--renderizar", action="store_true", help="renderiza filmes e pacote social após preparar")
    new.add_argument("--usar-proxies", action="store_true")
    new.add_argument("--sem-social", action="store_true")
    express = commands.add_parser("express", help="fluxo completo sem menu: preparar, renderizar e gerar social")
    express.add_argument("--zip", dest="zip_path", required=True)
    express.add_argument("--contexto", required=True)
    express.add_argument("--nome")
    express.add_argument("--modo", choices=tuple(sorted(ORDER_MODES)), default="automatico")
    express.add_argument("--seed", type=int)
    express.add_argument("--duracao-longa", type=float, default=360)
    express.add_argument("--duracao-media", type=float, default=6)
    express.add_argument("--reels", default="30,60,90")
    express.add_argument("--workspace-root")
    express.add_argument("--projeto")
    express.add_argument("--usar-proxies", action="store_true")
    express.add_argument("--sem-social", action="store_true")
    express.add_argument("--copiloto", dest="copiloto", action="store_true", default=None)
    express.add_argument("--sem-copiloto", dest="copiloto", action="store_false")
    q = commands.add_parser("questionario", help="criar um questionário interativo ou de exemplo")
    q.add_argument("--saida", default="./questionario.json")
    q.add_argument("--cozinha-carreira", action="store_true")
    q.add_argument("--sem-perguntas", action="store_true")
    prep = commands.add_parser("preparar", help="extrair, catalogar, criar proxies, plano e pacote ChatGPT")
    prep.add_argument("--respostas", required=True, help="questionário JSON respondido")
    prep.add_argument("--zip", dest="zip_path", help="substitui o caminho do ZIP do questionário")
    prep.add_argument("--projeto", help="substitui a pasta de projeto")
    takeout = commands.add_parser(
        "importar-takeout",
        help="restaurar datas dos JSONs do Google Takeout e criar o ZIP de entrada",
    )
    takeout.add_argument("--arquivo", required=True, help="ZIP ou pasta extraída do Google Takeout")
    takeout.add_argument("--projeto", required=True, help="pasta do projeto criada no Studio")
    takeout.add_argument(
        "--sem-metadados-internos", action="store_true",
        help="restaura apenas datas de arquivo/ZIP e preserva os JSONs ao lado das mídias",
    )
    all_cmd = commands.add_parser("tudo", help="preparar e renderizar as duas versões")
    all_cmd.add_argument("--respostas", required=True)
    all_cmd.add_argument("--zip", dest="zip_path")
    all_cmd.add_argument("--projeto")
    all_cmd.add_argument("--usar-proxies", action="store_true", help="render rápido; entrega final deve preferir originais")
    all_cmd.add_argument("--sem-social", action="store_true")
    render = commands.add_parser("render", help="renderizar EDIT_PLAN.json")
    render.add_argument("--projeto", required=True)
    render.add_argument("--plano")
    render.add_argument("--usar-proxies", action="store_true")
    render.add_argument("--somente", choices=("both", "branded", "clean"), default="both")
    draft = commands.add_parser("draft", help="renderizar prova rápida em 480p/15fps pelos proxies")
    draft.add_argument("--projeto", required=True)
    draft.add_argument("--somente", choices=("both", "branded", "clean"), default="both")
    social = commands.add_parser("social", help="renderizar Reels, Stories, capas e carrossel")
    social.add_argument("--projeto", required=True)
    social.add_argument("--usar-proxies", action="store_true")
    social.add_argument("--somente", choices=("all", "reels", "stories", "carrossel"), default="all")
    social.add_argument("--recriar-planos", action="store_true", help="descarta ajustes manuais dos planos sociais")
    cards = commands.add_parser("cards", help="gerar PNGs de prévia a partir dos cards editáveis")
    cards.add_argument("--projeto", required=True)
    cards.add_argument("--plano")
    replan = commands.add_parser("replanejar", help="trocar modo/duração sem extrair o ZIP novamente")
    replan.add_argument("--projeto", required=True)
    replan.add_argument("--modo", choices=tuple(sorted(ORDER_MODES)))
    replan.add_argument("--duracao-longa", type=float)
    replan.add_argument("--duracao-media", type=float)
    replan.add_argument("--seed", type=int, help="seed do modo aleatório")
    replan.add_argument("--recriar-social", action="store_true")
    pack = commands.add_parser("pacote-chatgpt", help="refazer apenas os lotes de upload")
    pack.add_argument("--projeto", required=True)
    stat = commands.add_parser("status", help="mostrar o estado do projeto")
    stat.add_argument("--projeto", required=True)
    audit = commands.add_parser("auditar", help="validar timeline, fontes, ZIPs e limites antes da entrega")
    audit.add_argument("--projeto", required=True)
    config = commands.add_parser("codex-config", help="configurar o Copiloto opcional sem exibir a chave")
    config.add_argument("--provider", choices=("openai", "anthropic", "ollama"), required=True)
    config.add_argument("--model", required=True)
    config.add_argument(
        "--key", help="opcional; prefira omitir para digitar oculto e não gravar a chave no histórico do shell",
    )
    curate = commands.add_parser("copilot-curate", help="pedir uma curadoria visual opcional e preservar fallback local")
    curate.add_argument("--projeto", required=True)
    curate.add_argument("--provider", choices=("openai", "anthropic", "ollama"))
    curate.add_argument("--model")
    curate.add_argument("--aplicar", action="store_true", help="aplicar a sugestão diretamente ao plano")
    curate.add_argument("--ignorar-cache", action="store_true")
    cloud = commands.add_parser("exportar-nuvem", help="testar ou enviar entregas ao Google Drive via rclone")
    cloud.add_argument("--projeto", required=True)
    cloud.add_argument("--testar", action="store_true", help="valida autorização sem enviar arquivos")
    brief = commands.add_parser(
        "gerar-roteiro-ia",
        help="gerar Markdown universal para uma IA editar filme, Reels, cards e publicação",
    )
    brief.add_argument("--projeto", required=True)
    apply_brief = commands.add_parser(
        "aplicar-roteiro-ia",
        help="validar e aplicar o Markdown respondido por qualquer IA",
    )
    apply_brief.add_argument("--projeto", required=True)
    apply_brief.add_argument("--arquivo", required=True, help="Markdown devolvido pela IA")
    for command_name, help_text in (("reset-definicoes", "zerar escolhas preservando mídias e cópia recuperável"),
                                     ("listar-roteiros", "listar cópias independentes de roteiro")):
        command = commands.add_parser(command_name, help=help_text)
        command.add_argument("--projeto", required=True)
    restore = commands.add_parser("restaurar-roteiro", help="restaurar uma cópia de roteiro")
    restore.add_argument("--projeto", required=True)
    restore.add_argument("--versao", required=True)
    inspect = commands.add_parser("validar-roteiro-ia", help="validar Markdown sem aplicar")
    inspect.add_argument("--projeto", required=True)
    inspect.add_argument("--arquivo", required=True)
    return root


def parse_duration_list(value: str) -> list[int]:
    try:
        result = sorted({int(float(item.strip())) for item in value.split(",") if item.strip()})
    except ValueError as exc:
        raise AutoEditeError("Durações de Reels inválidas. Use, por exemplo: 30,60,90") from exc
    if not result or any(item < 5 or item > 600 for item in result):
        raise AutoEditeError("Cada duração de Reel deve ficar entre 5 e 600 segundos.")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if not args.command:
            return interactive_menu()
        if args.command in {"studio", "wizard"}:
            from studio import launch_studio

            return launch_studio(
                APP_ROOT,
                expand_path(args.raiz),
                host="127.0.0.1",
                port=max(0, min(65535, int(args.porta))),
                open_browser=not args.sem_navegador,
            )
        if args.command == "novo":
            zip_path = expand_path(args.zip_path)
            workspace_root = expand_path(args.workspace_root) if args.workspace_root else None
            answers = answers_from_context(
                zip_path, args.contexto, args.nome, args.modo, args.duracao_longa,
                args.duracao_media, parse_duration_list(args.reels), workspace_root, args.seed,
            )
            if args.sem_social:
                answers["social"]["enabled"] = False
            _, project_dir = project_paths(answers, args.projeto)
            prepare(zip_path, project_dir, answers)
            if args.renderizar:
                render_plan(project_dir, project_dir / "EDIT_PLAN.json", use_proxies=args.usar_proxies)
                if answers.get("social", {}).get("enabled", True):
                    render_social_outputs(project_dir, answers, use_proxies=args.usar_proxies)
            return 0
        if args.command == "express":
            zip_path = expand_path(args.zip_path)
            workspace_root = expand_path(args.workspace_root) if args.workspace_root else None
            answers = answers_from_context(
                zip_path, args.contexto, args.nome, args.modo, args.duracao_longa,
                args.duracao_media, parse_duration_list(args.reels), workspace_root, args.seed,
            )
            if args.sem_social:
                answers["social"]["enabled"] = False
            if args.copiloto is not None:
                answers["ai_copilot"]["enabled"] = bool(args.copiloto)
            else:
                try:
                    from copilot import CredentialStore

                    credential_status = CredentialStore().status()
                    active = credential_status.get("active_provider")
                    configured = credential_status.get("providers", {}).get(active, {}).get("configured")
                    if active and configured:
                        answers["ai_copilot"].update({
                            "enabled": True,
                            "provider": active,
                            "model": credential_status["providers"][active].get("model") or "",
                        })
                except Exception:
                    pass
            _, project_dir = project_paths(answers, args.projeto)
            prepare(zip_path, project_dir, answers)
            render_plan(project_dir, project_dir / "EDIT_PLAN.json", use_proxies=args.usar_proxies)
            if answers.get("social", {}).get("enabled", True):
                render_social_outputs(project_dir, answers, use_proxies=args.usar_proxies)
            audit_project(project_dir)
            return 0
        if args.command == "questionario":
            create_questionnaire(
                expand_path(args.saida), example=args.cozinha_carreira,
                interactive=not args.sem_perguntas
            )
            return 0
        if args.command == "importar-takeout":
            create_takeout_dated_zip(
                expand_path(args.arquivo), expand_path(args.projeto),
                embed_metadata=not args.sem_metadados_internos,
            )
            return 0
        if args.command in {"preparar", "tudo"}:
            answers = normalize_answers(read_json(expand_path(args.respostas)))
            zip_path, project_dir = project_paths(answers, args.projeto)
            if args.zip_path:
                zip_path = expand_path(args.zip_path)
            prepare(zip_path, project_dir, answers)
            if args.command == "tudo":
                render_plan(project_dir, project_dir / "EDIT_PLAN.json", use_proxies=args.usar_proxies)
                if not args.sem_social and answers.get("social", {}).get("enabled", True):
                    render_social_outputs(project_dir, answers, use_proxies=args.usar_proxies)
            return 0
        if args.command == "render":
            project_dir = expand_path(args.projeto)
            questionnaire = project_dir / "QUESTIONARIO_RESPONDIDO.json"
            if questionnaire.is_file() and read_json(project_dir / "EDIT_PLAN.json").get("contract_version") != 2:
                sync_card_style_from_answers(project_dir, normalize_answers(read_json(questionnaire)))
            plan_path = expand_path(args.plano) if args.plano else project_dir / "EDIT_PLAN.json"
            render_plan(project_dir, plan_path, use_proxies=args.usar_proxies, only=args.somente)
            return 0
        if args.command == "draft":
            project_dir = expand_path(args.projeto)
            questionnaire = project_dir / "QUESTIONARIO_RESPONDIDO.json"
            if questionnaire.is_file() and read_json(project_dir / "EDIT_PLAN.json").get("contract_version") != 2:
                sync_card_style_from_answers(project_dir, normalize_answers(read_json(questionnaire)))
            render_draft(project_dir, only=args.somente)
            return 0
        if args.command == "social":
            project_dir = expand_path(args.projeto)
            answers = normalize_answers(read_json(project_dir / "QUESTIONARIO_RESPONDIDO.json"))
            if read_json(project_dir / "EDIT_PLAN.json").get("contract_version") != 2:
                sync_card_style_from_answers(project_dir, answers)
            render_social_outputs(
                project_dir, answers, use_proxies=args.usar_proxies,
                only=args.somente, recreate_plans=args.recriar_planos,
            )
            return 0
        if args.command == "cards":
            project_dir = expand_path(args.projeto)
            questionnaire = project_dir / "QUESTIONARIO_RESPONDIDO.json"
            answers = None
            if questionnaire.is_file():
                answers = normalize_answers(read_json(questionnaire))
                sync_card_style_from_answers(project_dir, answers, repair_invalid=True)
            if args.plano:
                plan_path = expand_path(args.plano)
            elif (project_dir / "EDIT_PLAN.json").is_file():
                plan_path = project_dir / "EDIT_PLAN.json"
            elif answers is not None:
                plan_path = build_card_preview_plan(project_dir, answers)
            else:
                raise AutoEditeError(
                    "O projeto ainda não possui configurações. Crie ou abra o projeto no Studio e tente novamente."
                )
            generate_card_previews(project_dir, plan_path)
            return 0
        if args.command == "replanejar":
            project_dir = expand_path(args.projeto)
            answers = normalize_answers(read_json(project_dir / "QUESTIONARIO_RESPONDIDO.json"))
            if args.modo:
                answers["edition"]["order_mode"] = args.modo
                answers.setdefault("random_mode", {})["enabled"] = args.modo == "aleatorio"
            if args.duracao_longa is not None:
                answers["edition"]["target_duration_sec"] = args.duracao_longa
            if args.duracao_media is not None:
                answers["edition"]["average_clip_duration_sec"] = args.duracao_media
            if args.seed is not None:
                answers.setdefault("random_mode", {}).update({"enabled": True, "seed": args.seed})
                answers["edition"]["order_mode"] = "aleatorio"
            manifest = read_json(project_dir / "MANIFESTO_MEDIA.json")
            plan = build_auto_plan(project_dir, answers, manifest)
            write_json(project_dir / "QUESTIONARIO_RESPONDIDO.json", answers)
            write_handoff_files(project_dir, answers, manifest)
            sync_card_style_from_answers(project_dir, answers)
            build_social_plans(project_dir, answers, plan, manifest, recreate=args.recriar_social)
            generate_ai_editing_brief(project_dir, answers, plan, manifest)
            generate_card_previews(project_dir, project_dir / "EDIT_PLAN.json")
            create_chatgpt_package(project_dir, answers)
            info(f"Projeto replanejado em modo {answers['edition']['order_mode']}: {project_dir}")
            return 0
        if args.command == "pacote-chatgpt":
            project_dir = expand_path(args.projeto)
            answers = normalize_answers(read_json(project_dir / "QUESTIONARIO_RESPONDIDO.json"))
            create_chatgpt_package(project_dir, answers)
            return 0
        if args.command == "status":
            status(expand_path(args.projeto))
            return 0
        if args.command == "auditar":
            report = audit_project(expand_path(args.projeto))
            return 0 if report["passed"] else 3
        if args.command == "codex-config":
            configure_copilot(args.provider, args.model, args.key)
            return 0
        if args.command == "copilot-curate":
            project_dir = expand_path(args.projeto)
            answers = normalize_answers(read_json(project_dir / "QUESTIONARIO_RESPONDIDO.json"))
            answers.setdefault("ai_copilot", {})["enabled"] = True
            if args.provider:
                answers["ai_copilot"]["provider"] = args.provider
            if args.model:
                answers["ai_copilot"]["model"] = args.model
            if args.ignorar_cache:
                answers["ai_copilot"]["use_cache"] = False
            manifest = read_json(project_dir / "MANIFESTO_MEDIA.json")
            plan = read_json(project_dir / "EDIT_PLAN.json")
            run_optional_copilot(
                project_dir, answers, manifest, plan,
                force_apply=bool(args.aplicar),
            )
            write_json(project_dir / "QUESTIONARIO_RESPONDIDO.json", answers)
            create_chatgpt_package(project_dir, answers)
            return 0
        if args.command == "exportar-nuvem":
            export_to_cloud(expand_path(args.projeto), test_only=bool(args.testar))
            return 0
        if args.command in {"reset-definicoes", "listar-roteiros", "restaurar-roteiro", "validar-roteiro-ia"}:
            import project_scope
            project_dir = expand_path(args.projeto)
            if args.command == "reset-definicoes":
                result = project_scope.reset_definitions(project_dir)
            elif args.command == "listar-roteiros":
                result = project_scope.list_versions(project_dir)
            elif args.command == "restaurar-roteiro":
                result = project_scope.restore_version(project_dir, args.versao)
            else:
                from master_contract import inspect_file
                result = inspect_file(globals(), project_dir, expand_path(args.arquivo))["review"]
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "gerar-roteiro-ia":
            project_dir = expand_path(args.projeto)
            generate_ai_editing_brief(project_dir)
            return 0
        if args.command == "aplicar-roteiro-ia":
            apply_ai_editing_brief(expand_path(args.projeto), expand_path(args.arquivo))
            return 0
        raise AutoEditeError("Comando desconhecido.")
    except KeyboardInterrupt:
        warning("Operação cancelada. Arquivos já concluídos foram preservados.")
        return 130
    except (AutoEditeError, ValueError, TypeError, KeyError, OSError) as exc:
        warning(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
