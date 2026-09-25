"""Lineage e cobertura verificáveis para proxies locais (M7)."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from typing import Any, Callable


INTEGRITY_VERSION = "fr-proxy-integrity/1"
VERIFIED_STATES = {"verified", "verified_legacy"}


class ProxyIntegrityError(ValueError):
    pass


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _project_file(project: Path, relative: Any, asset_id: str, role: str) -> tuple[str, Path]:
    if not isinstance(relative, str) or not relative.strip():
        raise ProxyIntegrityError(
            f"{asset_id}: {role} ausente; regenere os proxies sem alterar o original."
        )
    path = (project / relative).resolve()
    try:
        normalized = path.relative_to(project.resolve()).as_posix()
    except ValueError as exc:
        raise ProxyIntegrityError(f"{asset_id}: {role} aponta para fora do projeto.") from exc
    if not path.is_file() or path.stat().st_size <= 0:
        raise ProxyIntegrityError(
            f"{asset_id}: {role} ausente ou vazio ({normalized}); regenere o proxy."
        )
    return normalized, path


def _duration_tolerance(source: dict[str, Any], proxy: dict[str, Any]) -> float:
    fps_values = [
        float(value) for value in (source.get("fps"), proxy.get("fps"))
        if isinstance(value, (int, float)) and float(value) > 0
    ]
    fps = min(fps_values) if fps_values else 24.0
    # Três frames cobrem arredondamento CFR/VFR e delay de encoder; piso medido
    # para containers que arredondam timestamps em centésimos de segundo.
    return round(max(0.125, 3.0 / fps), 6)


def _image_is_decodable(path: Path, asset_id: str, role: str) -> None:
    try:
        from PIL import Image
        with Image.open(path) as image:
            image.verify()
    except Exception as exc:
        raise ProxyIntegrityError(
            f"{asset_id}: {role} de imagem ilegível; regenere o proxy: {exc}"
        ) from exc


def validate_decoded_coverage(
    metadata: dict[str, Any], decoded: dict[str, Any], *,
    asset_id: str, expected_duration: float | None = None,
    tolerance: float | None = None,
) -> dict[str, Any]:
    duration = float(metadata.get("video_duration_sec") or metadata.get("duration_sec") or 0)
    expected_duration = float(expected_duration or duration)
    tolerance = float(tolerance if tolerance is not None else _duration_tolerance(metadata, metadata))
    decoded_frames = int(decoded.get("decoded_frame_count") or 0)
    decoded_end = float(decoded.get("decoded_coverage_end") or 0)
    declared_frames = int(metadata.get("declared_frame_count") or 0)
    fps = float(metadata.get("fps") or 0)
    estimated_frames = max(1, round(duration * fps)) if duration > 0 and fps > 0 else 0
    expected_frames = declared_frames or estimated_frames
    frame_tolerance = max(2, round(tolerance * (fps or 24)))
    if expected_frames and decoded_frames + frame_tolerance < expected_frames:
        raise ProxyIntegrityError(
            f"{asset_id}: decodificação entregou {decoded_frames} de {expected_frames} frames "
            f"esperados (tolerância {frame_tolerance}); proxy truncado, regenere-o."
        )
    if decoded_end + tolerance < duration or decoded_end + tolerance < expected_duration:
        raise ProxyIntegrityError(
            f"{asset_id}: decodificação termina em {decoded_end:.3f}s, antes dos "
            f"{expected_duration:.3f}s esperados (tolerância {tolerance:.3f}s); "
            "proxy truncado, regenere-o."
        )
    return {
        "declared_frame_count": declared_frames,
        "expected_frame_count": expected_frames,
        "decoded_frame_count": decoded_frames,
        "decoded_coverage_end": round(decoded_end, 6),
        "frame_tolerance": frame_tolerance,
    }


def verify_asset(
    project: Path,
    row: dict[str, Any],
    *,
    generation_parameters: dict[str, Any],
    probe: Callable[[Path], dict[str, Any]],
    decode_video: Callable[[Path], dict[str, Any]],
    expected: dict[str, Any] | None = None,
    legacy: bool = False,
) -> dict[str, Any]:
    project = Path(project).resolve()
    asset_id = str(row.get("id") or "item-sem-id")
    source_relative, source = _project_file(project, row.get("source_path"), asset_id, "original")
    proxy_relative, proxy = _project_file(project, row.get("proxy_path"), asset_id, "proxy")
    if source == proxy:
        raise ProxyIntegrityError(
            f"{asset_id}: original e proxy são o mesmo arquivo; regenere um proxy separado."
        )
    source_hash = file_sha256(source)
    proxy_hash = file_sha256(proxy)
    if expected:
        if expected.get("source_hash") != source_hash:
            raise ProxyIntegrityError(
                f"{asset_id}: o original mudou desde a geração do proxy; regenere o proxy."
            )
        if expected.get("proxy_hash") != proxy_hash:
            raise ProxyIntegrityError(
                f"{asset_id}: o proxy mudou ou foi truncado; regenere o proxy."
            )
        if expected.get("generation_parameters") != generation_parameters:
            raise ProxyIntegrityError(
                f"{asset_id}: os parâmetros de proxy mudaram; regenere o proxy."
            )
    media_type = str(row.get("media_type") or "")
    source_duration = proxy_duration = 0.0
    tolerance = 0.0
    if media_type == "image":
        _image_is_decodable(source, asset_id, "original")
        _image_is_decodable(proxy, asset_id, "proxy")
        coverage_start = coverage_end = None
    elif media_type == "video":
        try:
            source_probe = probe(source)
            proxy_probe = probe(proxy)
        except Exception as exc:
            raise ProxyIntegrityError(f"{asset_id}: FFprobe falhou; regenere o proxy: {exc}") from exc
        source_duration = float(source_probe.get("video_duration_sec") or source_probe.get("duration_sec") or 0)
        proxy_duration = float(proxy_probe.get("video_duration_sec") or proxy_probe.get("duration_sec") or 0)
        if (
            source_probe.get("probe_error") or proxy_probe.get("probe_error")
            or source_duration <= 0 or proxy_duration <= 0
            or not proxy_probe.get("width") or not proxy_probe.get("height")
        ):
            raise ProxyIntegrityError(
                f"{asset_id}: proxy de vídeo ilegível ou sem duração; regenere o proxy."
            )
        tolerance = _duration_tolerance(source_probe, proxy_probe)
        if abs(proxy_duration - source_duration) > tolerance:
            raise ProxyIntegrityError(
                f"{asset_id}: proxy incompleto ({proxy_duration:.3f}s de {source_duration:.3f}s; "
                f"tolerância {tolerance:.3f}s); regenere o proxy."
            )
        try:
            decoded = decode_video(proxy)
        except Exception as exc:
            raise ProxyIntegrityError(
                f"{asset_id}: a decodificação do proxy falhou; regenere o proxy: {exc}"
            ) from exc
        decoded_coverage = validate_decoded_coverage(
            proxy_probe, decoded, asset_id=asset_id,
            expected_duration=source_duration, tolerance=tolerance,
        )
        coverage_start = float(row.get("scene_start_sec") or 0)
        coverage_end = float(row.get("scene_end_sec") or source_duration)
        if coverage_start < 0 or coverage_end <= coverage_start or coverage_end > source_duration + tolerance:
            raise ProxyIntegrityError(
                f"{asset_id}: cobertura {coverage_start:.3f}–{coverage_end:.3f}s inválida; "
                "regenere o manifesto sem tocar no original."
            )
    else:
        raise ProxyIntegrityError(f"{asset_id}: media_type sem suporte para integridade: {media_type!r}.")
    record = {
        "version": INTEGRITY_VERSION,
        "status": "verified_legacy" if legacy else "verified",
        "source_asset_id": str(row.get("parent_video") or asset_id),
        "source_path": source_relative,
        "proxy_path": proxy_relative,
        "source_hash": source_hash,
        "proxy_hash": proxy_hash,
        "source_duration": round(source_duration, 6),
        "proxy_duration": round(proxy_duration, 6),
        "coverage_start": None if coverage_start is None else round(coverage_start, 6),
        "coverage_end": None if coverage_end is None else round(coverage_end, 6),
        "duration_tolerance_sec": tolerance,
        "generation_parameters": copy.deepcopy(generation_parameters),
    }
    if media_type == "video":
        record.update(decoded_coverage)
    if legacy:
        record["notice"] = "Proxy legado verificado; parâmetros históricos exatos não estavam registrados."
    return record


def ensure_manifest_integrity(
    project: Path,
    manifest: dict[str, Any],
    *,
    parameters_for: Callable[[dict[str, Any]], dict[str, Any]],
    probe: Callable[[Path], dict[str, Any]],
    decode_video: Callable[[Path], dict[str, Any]],
) -> dict[str, Any]:
    result = copy.deepcopy(manifest)
    for row in result.get("media", []):
        if (
            not isinstance(row, dict) or row.get("status", "ok") != "ok"
            or row.get("excluded_from_auto_edit")
            or row.get("media_type") not in {"image", "video"}
        ):
            continue
        expected = row.get("proxy_integrity") if isinstance(row.get("proxy_integrity"), dict) else None
        legacy = expected is None
        parameters = (
            copy.deepcopy(expected.get("generation_parameters")) if expected
            else {"pipeline_version": "legacy-unknown", "verification": "m7-migrated"}
        )
        if expected and expected.get("generation_parameters") != parameters_for(row):
            raise ProxyIntegrityError(
                f"{row.get('id')}: parâmetros atuais diferem do proxy registrado; "
                "execute novamente a preparação para regenerá-lo."
            )
        row["proxy_integrity"] = verify_asset(
            project, row, generation_parameters=parameters, probe=probe,
            decode_video=decode_video, expected=expected, legacy=legacy,
        )
    return result
