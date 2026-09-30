"""Ponte compatível entre os planos 3.4.0 e o compositor visual v2.

Este módulo não altera o contrato legado. Ele somente traduz um segmento de
card já validado para ``CardSpec``. O fallback legado é decisão da fachada.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from .core.card_renderer import CardSpec, compose
from .core.config import SERVICE_BY_KEY
from .style_packs.registry import AssetError, index_assets


FAMILY_BY_KIND = {
    "intro": "F1",
    "cover": "F1",
    "phase": "F2",
    "chapter": "F2",
    "service": "F3",
    "detail": "F4",
    "data": "F4",
    "comparison": "F5",
    "before_after": "F5",
    "quote": "F5",
    "cta": "F5",
    "outro": "F6",
    "contact": "F6",
}


def enabled(style: dict[str, Any]) -> bool:
    system = style.get("design_system", {})
    if style.get("legacy_v1") is True or system.get("legacy_v1") is True:
        return False
    return bool(system.get("enabled", False))


def _service_key(segment: dict[str, Any]) -> str:
    raw = str(segment.get("service_key") or segment.get("service_id") or "").strip().lower()
    aliases = {"projetos": "projetos_3d", "projeto_3d": "projetos_3d", "mobiliario": "moveis"}
    raw = aliases.get(raw, raw)
    return raw if raw in SERVICE_BY_KEY else ""


def _status(segment: dict[str, Any]) -> str | None:
    value = str(segment.get("media_status") or "").strip().lower()
    return value or None


def spec_from_legacy(segment: dict[str, Any], brand: dict[str, Any]) -> CardSpec:
    kind = str(segment.get("card_kind") or "phase").strip().lower()
    family = str(segment.get("card_family") or FAMILY_BY_KIND.get(kind, "F5")).upper()
    if family not in {"F1", "F2", "F3", "F4", "F5", "F6"}:
        family = FAMILY_BY_KIND.get(kind, "F5")
    service = _service_key(segment)
    if family == "F3" and not service:
        raise ValueError("Card F3 exige service_key/service_id válido.")
    contacts: tuple[str, ...] = ()
    if family == "F6":
        contact = brand.get("contact", {})
        values = [contact.get("instagram"), contact.get("whatsapp"), contact.get("website")]
        contacts = tuple(str(item).strip() for item in values if str(item or "").strip())
    evidence = segment.get("claims") if isinstance(segment.get("claims"), list) else []
    return CardSpec(
        family=family,
        title=str(segment.get("title") or segment.get("text") or "FRANCO ROMEU").strip(),
        body=str(segment.get("body") or segment.get("subtitle") or "").strip(),
        service_key=service,
        subtype=kind,
        media_status=_status(segment),
        contacts=contacts,
        evidence=tuple(item for item in evidence if isinstance(item, dict)),
        stage_number=str(segment.get("phase_order") or "").strip(),
    )


def render_legacy_card(
    path: Path, segment: dict[str, Any], plan: dict[str, Any],
    brand: dict[str, Any], style: dict[str, Any], app_root: Path,
    *, project_dir: Path | None = None, env: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Renderiza atomicamente e retorna metadados editoriais verificáveis.

    Cards F3 com central_media continuam no renderer visual v2. A mídia é
    resolvida pelo manifesto do projeto e transformada em input somente de
    leitura do compositor. Se ela desaparecer após a validação, o próprio v2
    usa o medalhão oficial do serviço e registra aviso; não há fallback
    silencioso para o renderer legado.
    """
    central_media = segment.get("card_instance", {}).get("central_media")
    if not enabled(style):
        return {"handled": False}
    output = plan.get("output", {})
    size = (int(output.get("width") or 1080), int(output.get("height") or 1920))
    if min(size) < 480:
        # Miniaturas técnicas muito pequenas continuam no compositor legado;
        # o v2 é validado em artboards editoriais e depois reduzido.
        return {"handled": False, "reason": "preview_below_v2_artboard"}
    manifest = app_root / "assets/style_packs/fr_quiet_engineering_atelier_v2/manifest.json"
    if not manifest.is_file():
        index_assets(app_root)
    spec = spec_from_legacy(segment, brand)
    bridge_warnings: list[str] = []
    if isinstance(central_media, dict):
        if spec.family != "F3":
            return {"handled": False, "reason": "central_media_non_service"}
        if project_dir is None or env is None:
            bridge_warnings.append(
                "central_media: contexto do projeto indisponível; usando medalhão v2 do serviço."
            )
        else:
            try:
                from media_frames import extract_reference
                source = extract_reference(
                    env, Path(project_dir),
                    {
                        "media_id": central_media["central_asset_id"],
                        "time_sec": central_media.get("frame_time_sec", 0.0),
                        "time_basis": "absolute_parent_media",
                    },
                    plan.get("output", {}).get("render_source") == "proxies",
                )
                spec = replace(
                    spec,
                    central_image=Path(source),
                    central_zoom=float(central_media.get("zoom", 1.0)),
                    central_focal_x=float(central_media.get("focal_x", 0.5)),
                    central_focal_y=float(central_media.get("focal_y", 0.5)),
                )
            except Exception as exc:
                bridge_warnings.append(
                    "central_media: mídia indisponível; usando medalhão v2 do serviço: " + str(exc)
                )
    composition = compose(spec, size, app_root)
    if bridge_warnings:
        composition.warnings[:0] = bridge_warnings
    image = composition.flatten()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.png")
    temporary.unlink(missing_ok=True)
    try:
        image.convert("RGB").save(temporary, format="PNG", compress_level=6)
        from PIL import Image
        with Image.open(temporary) as check:
            check.verify()
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
        image.close()
        for layer in composition.layers.values():
            layer.close()
    return {
        "handled": True,
        "family": spec.family,
        "pending_assets": composition.pending_assets,
        "warnings": composition.warnings,
        "publicable": not composition.pending_assets,
    }
