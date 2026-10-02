"""Lineage e cobertura verificáveis para proxies locais (M7)."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from typing import Any, Callable

from runtime_control import SkipCurrentItem


INTEGRITY_VERSION = "fr-proxy-integrity/1"
VERIFIED_STATES = {"verified", "verified_legacy"}


class ProxyIntegrityError(ValueError):
    pass


class SceneCoverageUnavailable(ProxyIntegrityError):
    """Cena virtual sem nenhum intervalo útil dentro da mídia realmente decodificável."""



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
        if row.get("parent_video"):
            available_candidates = [
                value for value in (source_duration, proxy_duration, float(decoded_coverage.get("decoded_coverage_end") or 0))
                if value > 0
            ]
            available_end = min(available_candidates) if available_candidates else source_duration
            requested = (coverage_start, coverage_end)
            coverage_start = max(0.0, coverage_start)
            coverage_end = min(coverage_end, available_end)
            minimum_viable = max(0.10, 2.0 / max(float(proxy_probe.get("fps") or 24.0), 1.0))
            if coverage_end - coverage_start < minimum_viable:
                raise SceneCoverageUnavailable(
                    f"{asset_id}: cena sem cobertura decodificável útil "
                    f"({requested[0]:.3f}–{requested[1]:.3f}s; disponível até {available_end:.3f}s)."
                )
            if coverage_end + 0.0005 < requested[1] or coverage_start > requested[0] + 0.0005:
                decoded_coverage["coverage_adjusted"] = True
                decoded_coverage["coverage_requested_start"] = round(requested[0], 6)
                decoded_coverage["coverage_requested_end"] = round(requested[1], 6)
        elif coverage_start < 0 or coverage_end <= coverage_start or coverage_end > source_duration + tolerance:
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
    continue_on_error: bool = False,
    progress: Callable[[int, int, dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Valida proxies sem repetir a decodificação para cada cena virtual.

    Cenas que compartilham o mesmo proxy pai reutilizam uma verificação-base.
    Janelas que ultrapassam a cobertura real são recortadas; cenas sem nenhum
    intervalo útil são marcadas como ``skipped``. Em modo tolerante, uma mídia
    defeituosa é isolada e o restante do pacote continua.
    """
    result = copy.deepcopy(manifest)
    verification_cache: dict[tuple[str, str, str], dict[str, Any]] = {}
    failure_cache: dict[tuple[str, str, str], str] = {}
    report = {"verified": 0, "clamped_scenes": 0, "skipped_scenes": 0, "errors": 0}
    candidates = [
        row for row in result.get("media", [])
        if isinstance(row, dict) and row.get("status", "ok") == "ok"
        and not row.get("excluded_from_auto_edit")
        and row.get("media_type") in {"image", "video"}
    ]

    for current_index, row in enumerate(candidates, 1):
        asset_id = str(row.get("id") or "item-sem-id")
        if progress is not None:
            progress(current_index, len(candidates), row)
        expected = row.get("proxy_integrity") if isinstance(row.get("proxy_integrity"), dict) else None
        legacy = expected is None
        parameters = (
            copy.deepcopy(expected.get("generation_parameters")) if expected
            else {"pipeline_version": "legacy-unknown", "verification": "m7-migrated"}
        )
        try:
            if expected and expected.get("generation_parameters") != parameters_for(row):
                raise ProxyIntegrityError(
                    f"{asset_id}: parâmetros atuais diferem do proxy registrado; "
                    "execute novamente a preparação para regenerá-lo."
                )
            source_key = str(row.get("source_path") or "")
            proxy_key = str(row.get("proxy_path") or "")
            cache_key = (source_key, proxy_key, repr(sorted(parameters.items())))
            if cache_key in failure_cache:
                raise ProxyIntegrityError(failure_cache[cache_key])

            if row.get("media_type") == "video" and row.get("parent_video"):
                if cache_key not in verification_cache:
                    base_row = copy.deepcopy(row)
                    base_row.pop("scene_start_sec", None)
                    base_row.pop("scene_end_sec", None)
                    base_row.pop("parent_video", None)
                    base_row["id"] = str(row.get("parent_video") or asset_id)
                    try:
                        verification_cache[cache_key] = verify_asset(
                            project, base_row, generation_parameters=parameters, probe=probe,
                            decode_video=decode_video, expected=expected, legacy=legacy,
                        )
                    except SkipCurrentItem:
                        raise
                    except ProxyIntegrityError as exc:
                        failure_cache[cache_key] = str(exc)
                        raise
                record = copy.deepcopy(verification_cache[cache_key])
                record["source_asset_id"] = str(row.get("parent_video") or asset_id)
                start = max(0.0, float(row.get("scene_start_sec") or 0))
                requested_end = float(row.get("scene_end_sec") or record.get("source_duration") or 0)
                available_values = [
                    float(v) for v in (
                        record.get("source_duration"), record.get("proxy_duration"), record.get("decoded_coverage_end")
                    ) if isinstance(v, (int, float)) and float(v) > 0
                ]
                available_end = min(available_values) if available_values else 0.0
                end = min(requested_end, available_end)
                fps = 24.0
                tolerance = float(record.get("duration_tolerance_sec") or 0.125)
                minimum_viable = max(0.10, tolerance)
                if end - start < minimum_viable:
                    raise SceneCoverageUnavailable(
                        f"{asset_id}: cena sem cobertura útil ({start:.3f}–{requested_end:.3f}s; "
                        f"disponível até {available_end:.3f}s)."
                    )
                record["coverage_start"] = round(start, 6)
                record["coverage_end"] = round(end, 6)
                if end + 0.0005 < requested_end:
                    record["coverage_adjusted"] = True
                    record["coverage_requested_end"] = round(requested_end, 6)
                    row["scene_end_sec"] = round(end, 6)
                    row["duration_sec"] = round(end - start, 6)
                    row["integrity_notice"] = (
                        f"cena recortada automaticamente até {end:.3f}s, limite realmente decodificável"
                    )
                    report["clamped_scenes"] += 1
                row["proxy_integrity"] = record
            else:
                record = verify_asset(
                    project, row, generation_parameters=parameters, probe=probe,
                    decode_video=decode_video, expected=expected, legacy=legacy,
                )
                verification_cache[cache_key] = copy.deepcopy(record)
                row["proxy_integrity"] = record
            report["verified"] += 1
        except SkipCurrentItem as exc:
            row["status"] = "skipped"
            row["excluded_from_auto_edit"] = True
            row["exclusion_reason"] = "pulado manualmente pelo usuário"
            row["error"] = str(exc)
            report["errors"] += 1
            if not continue_on_error:
                raise
        except SceneCoverageUnavailable as exc:
            row["status"] = "skipped"
            row["excluded_from_auto_edit"] = True
            row["exclusion_reason"] = "cena vazia/fora da cobertura real; descartada automaticamente"
            row["error"] = str(exc)
            report["skipped_scenes"] += 1
        except ProxyIntegrityError as exc:
            if not continue_on_error:
                raise
            row["status"] = "error"
            row["excluded_from_auto_edit"] = True
            row["exclusion_reason"] = "falha técnica isolada de integridade; demais itens continuam"
            row["error"] = str(exc)
            report["errors"] += 1

    result["integrity_report"] = report
    summary = result.setdefault("summary", {})
    if isinstance(summary, dict):
        summary["integrity_errors"] = report["errors"]
        summary["scene_clips_clamped"] = report["clamped_scenes"]
        summary["scene_clips_discarded_integrity"] = report["skipped_scenes"]
        summary["errors"] = sum(
            isinstance(row, dict) and row.get("status", "ok") not in {"ok"}
            for row in result.get("media", [])
        )
    return result

