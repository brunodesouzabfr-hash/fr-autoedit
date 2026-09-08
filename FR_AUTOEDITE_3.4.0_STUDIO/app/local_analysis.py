#!/usr/bin/env python3
"""Análise local, explicável e opcional para o FR AutoEdite.

Este módulo não tenta reconhecer semanticamente uma obra. Ele mede sinais
técnicos (nitidez, repetição e variação entre quadros) e devolve indicadores
que sempre podem ser revisados pelo usuário.
"""

from __future__ import annotations

import math
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _laplacian_variance(pixels: bytes, width: int, height: int) -> float:
    """Variância de um Laplaciano simples, sem NumPy/OpenCV."""
    if len(pixels) < width * height or width < 3 or height < 3:
        return 0.0
    values: list[float] = []
    for y in range(1, height - 1):
        row = y * width
        for x in range(1, width - 1):
            index = row + x
            center = pixels[index] * 4
            lap = center - pixels[index - 1] - pixels[index + 1]
            lap -= pixels[index - width] + pixels[index + width]
            values.append(float(lap))
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values) / len(values)


def _gray_frame(path: Path, seek: float, width: int = 160, height: int = 90) -> bytes:
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-nostdin", "-v", "error", "-ss", f"{max(0.0, seek):.3f}",
                "-i", str(path), "-vf", f"scale={width}:{height},format=gray",
                "-frames:v", "1", "-f", "rawvideo", "-",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=45,
        )
    except subprocess.TimeoutExpired:
        return b""
    return result.stdout if result.returncode == 0 else b""


def _gray_sequence(
    path: Path, seek: float, seconds: float = 2.0, fps: int = 4,
    width: int = 160, height: int = 90,
) -> list[bytes]:
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-nostdin", "-v", "error", "-ss", f"{max(0.0, seek):.3f}",
                "-t", f"{max(0.5, seconds):.3f}", "-i", str(path),
                "-vf", f"fps={fps},scale={width}:{height},format=gray",
                "-frames:v", str(max(2, round(seconds * fps))), "-f", "rawvideo", "-",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=45,
        )
    except subprocess.TimeoutExpired:
        return []
    if result.returncode != 0:
        return []
    frame_size = width * height
    data = result.stdout
    return [data[index:index + frame_size] for index in range(0, len(data), frame_size) if len(data[index:index + frame_size]) == frame_size]


def _frame_change(frames: list[bytes]) -> float:
    if len(frames) < 2:
        return 0.0
    scores: list[float] = []
    for previous, current in zip(frames, frames[1:]):
        if len(previous) != len(current) or not previous:
            continue
        # Amostragem reduz o custo em máquinas antigas.
        delta = sum(abs(previous[index] - current[index]) for index in range(0, len(current), 4))
        scores.append(delta / (math.ceil(len(current) / 4) * 255.0))
    return sum(scores) / len(scores) if scores else 0.0


def _crop_border_ratio(path: Path, seek: float) -> float:
    """Amostra bordas persistentes; valor baixo pode indicar recorte/estabilização prévia."""
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "info",
                "-ss", f"{max(0.0, seek):.3f}", "-t", "2", "-i", str(path),
                "-vf", "scale=160:90,cropdetect=limit=20:round=2:reset=12",
                "-an", "-f", "null", "-",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=45,
        )
    except subprocess.TimeoutExpired:
        return 1.0
    matches = re.findall(r"crop=(\d+):(\d+):\d+:\d+", result.stderr or "")
    if not matches:
        return 1.0
    ratios = [int(width) * int(height) / (160 * 90) for width, height in matches]
    return max(0.0, min(1.0, sum(ratios) / len(ratios)))


def video_quality_signals(path: Path, duration: float) -> dict[str, Any]:
    """Mede amostras curtas; nunca afirma que o vídeo está ruim sozinho."""
    if not path.is_file() or duration <= 0:
        return {
            "sample_sharpness": 0.0,
            "frame_change_score": 0.0,
            "detected_content_area_ratio": 1.0,
            "possible_pre_stabilized_borders": False,
            "needs_stabilization": False,
            "stabilization_confidence": "sem_dados",
        }
    seeks = [duration * 0.18, duration * 0.50, duration * 0.82]
    sharpness = []
    for seek in seeks:
        frame = _gray_frame(path, seek)
        if frame:
            sharpness.append(_laplacian_variance(frame, 160, 90))
    middle = max(0.0, duration * 0.50 - 1.0)
    change = _frame_change(_gray_sequence(path, middle))
    crop_ratio = _crop_border_ratio(path, middle)
    mean_sharpness = sum(sharpness) / len(sharpness) if sharpness else 0.0
    # É um alerta conservador: movimento alto + baixa definição. Pode ser ação
    # real da obra; por isso a confirmação visual continua obrigatória.
    flag = bool(change > 0.19 and mean_sharpness < 520.0)
    return {
        "sample_sharpness": round(mean_sharpness, 2),
        "frame_change_score": round(change, 4),
        "detected_content_area_ratio": round(crop_ratio, 4),
        "possible_pre_stabilized_borders": bool(crop_ratio < 0.94),
        "needs_stabilization": flag,
        "stabilization_confidence": "heuristica_confirmar_visual" if flag else "baixo_risco_tecnico",
    }


def image_signature(path: Path) -> tuple[int | None, float]:
    """Retorna dHash de 64 bits e nitidez da imagem proxy."""
    try:
        from PIL import Image, ImageOps

        with Image.open(path) as opened:
            image = ImageOps.exif_transpose(opened).convert("L")
            hash_image = image.resize((9, 8), Image.Resampling.LANCZOS)
            values = list(hash_image.getdata())
            signature = 0
            for y in range(8):
                for x in range(8):
                    signature <<= 1
                    signature |= int(values[y * 9 + x] > values[y * 9 + x + 1])
            focus = image.copy()
            focus.thumbnail((320, 320), Image.Resampling.LANCZOS)
            pixels = focus.tobytes()
            sharpness = _laplacian_variance(pixels, focus.width, focus.height)
            return signature, round(sharpness, 2)
    except Exception:
        return None, 0.0


def _hamming(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def mark_burst_duplicates(
    rows: list[dict[str, Any]], project_dir: Path, threshold: int = 8,
) -> dict[str, int]:
    """Marca fotos muito parecidas no mesmo segundo; não remove arquivos."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("media_type") != "image" or row.get("status") != "ok":
            continue
        second = str(row.get("capture_time") or "")[:19]
        groups.setdefault(second, []).append(row)
    duplicate_count = 0
    analyzed = 0
    for group in groups.values():
        if len(group) < 2:
            continue
        measured: list[tuple[dict[str, Any], int | None, float]] = []
        for row in group:
            proxy = project_dir / str(row.get("proxy_path") or "")
            signature, sharpness = image_signature(proxy)
            row["sharpness_score"] = sharpness
            row["perceptual_hash"] = f"{signature:016x}" if signature is not None else ""
            measured.append((row, signature, sharpness))
            analyzed += 1
        clusters: list[list[tuple[dict[str, Any], int, float]]] = []
        for row, signature, sharpness in measured:
            if signature is None:
                continue
            destination = next(
                (cluster for cluster in clusters if _hamming(signature, cluster[0][1]) <= threshold),
                None,
            )
            if destination is None:
                destination = []
                clusters.append(destination)
            destination.append((row, signature, sharpness))
        for cluster in clusters:
            if len(cluster) < 2:
                continue
            winner = max(cluster, key=lambda item: item[2])[0]
            winner["duplicate"] = False
            for row, _, _ in cluster:
                if row is winner:
                    continue
                row["duplicate"] = True
                row["duplicate_of"] = winner["id"]
                row["excluded_from_auto_edit"] = True
                row["exclusion_reason"] = "rajada semelhante; mantida a imagem localmente mais nítida"
                duplicate_count += 1
    return {"images_analyzed": analyzed, "duplicates_marked": duplicate_count}


def scene_boundaries(
    path: Path, duration: float, threshold: float = 0.34,
    max_scan_seconds: float = 180.0,
) -> list[float]:
    """Localiza mudanças de cena com FFmpeg em janelas curtas."""
    if not path.is_file() or duration <= 0 or shutil.which("ffmpeg") is None:
        return []
    # Quando PySceneDetect estiver instalado e o vídeo couber no limite de
    # análise, aproveitamos seu detector de conteúdo. Qualquer incompatibilidade
    # volta silenciosamente ao FFmpeg amostral abaixo.
    if duration <= max_scan_seconds:
        try:
            from scenedetect import ContentDetector, detect  # type: ignore

            scenes = detect(
                str(path),
                ContentDetector(threshold=max(8.0, min(60.0, threshold * 80.0))),
                show_progress=False,
            )
            boundaries = sorted({round(start.get_seconds(), 3) for start, _ in scenes[1:]})
            if boundaries:
                return [value for value in boundaries if 0.5 < value < duration - 0.5]
        except Exception:
            pass
    if duration <= max_scan_seconds:
        windows = [(0.0, duration)]
    else:
        window = max(20.0, max_scan_seconds / 3.0)
        windows = [
            (0.0, window),
            (max(0.0, duration / 2.0 - window / 2.0), window),
            (max(0.0, duration - window), window),
        ]
    found: set[float] = set()
    pattern = re.compile(r"pts_time:([0-9.]+)")
    for offset, length in windows:
        try:
            result = subprocess.run(
                [
                    "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "info",
                    "-ss", f"{offset:.3f}", "-t", f"{length:.3f}", "-i", str(path),
                    "-vf", f"select='gt(scene,{threshold:.3f})',showinfo", "-an", "-f", "null", "-",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=max(60.0, min(900.0, length * 8.0)),
            )
        except subprocess.TimeoutExpired:
            continue
        for match in pattern.finditer(result.stderr or ""):
            value = offset + float(match.group(1))
            if 0.5 < value < duration - 0.5:
                found.add(round(value, 3))
    return sorted(found)


def scene_ranges(
    path: Path, duration: float, *, minimum: float = 3.0, maximum: float = 8.0,
    threshold: float = 0.34, max_scan_seconds: float = 180.0, max_clips: int = 18,
) -> list[tuple[float, float]]:
    """Converte mudanças de cena em trechos virtuais de 3–8 segundos."""
    if duration <= 30.0:
        return []
    cuts = [0.0, *scene_boundaries(path, duration, threshold, max_scan_seconds), duration]
    candidates: list[tuple[float, float]] = []
    for start, end in zip(cuts, cuts[1:]):
        length = end - start
        if length < 1.5:
            continue
        cursor = start
        while cursor < end - 1.0:
            clip = min(maximum, end - cursor)
            if clip < minimum and candidates:
                previous_start, previous_duration = candidates[-1]
                # Só amplia o trecho anterior quando ele termina exatamente no
                # começo deste resto; nunca atravessa um corte de cena.
                if abs((previous_start + previous_duration) - cursor) < 0.05:
                    candidates[-1] = (previous_start, min(maximum, previous_duration + clip))
                elif clip >= 1.5:
                    candidates.append((round(cursor, 3), round(clip, 3)))
                break
            candidates.append((round(cursor, 3), round(clip, 3)))
            cursor += max(minimum, clip)
    if len(candidates) <= max_clips:
        return candidates
    # Amostragem distribuída preserva começo, meio e fim.
    selected: list[tuple[float, float]] = []
    for index in range(max_clips):
        position = round(index * (len(candidates) - 1) / max(1, max_clips - 1))
        selected.append(candidates[position])
    return selected
