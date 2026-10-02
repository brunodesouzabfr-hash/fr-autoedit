"""Runtime M9.9 para Studio, timeline e renderer universal.

Todo projeto preparado ativa primeiro suas CardInstances v2. F1--F6 só pode
ser alcançado por uma rejeição nominal registrada no relatório M9.9; ausência
de rota é erro fechado. Paths vêm apenas de contratos/manifestos locais.
"""
from __future__ import annotations

from io import BytesIO
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import threading
from typing import Any, Callable, Mapping

from PIL import Image

import card_editor_adapter_v2 as adapter
import card_migration_v99 as migration_v99
import card_persistence_v2 as persistence
import card_state_v2 as card_v2
import project_scope
import service_catalog_v2
from universal_card_renderer import render_universal_card


APP_ROOT = Path(__file__).resolve().parents[1]
COMPONENT_RELATIVE = Path("local_components/fr-card-editor/1.1.0")
SOURCE_RELATIVE = Path("FR_CARD_EDITOR_UNIVERSAL_v1.1.0")
PREVIEW_ROOT = Path("cards_editaveis/fr-universal-card")
PREVIEW_REGISTRY = Path("_CONTROLE/CARD_PREVIEWS.json")
_COMPONENT_FILES = {
    "component/background-fr-hd": "assets/background-fr-hd.png",
    "component/background-fr-source": "assets/background-fr-source.png",
    "component/background-fr": "assets/background-fr.png",
    "component/logo-fr": "assets/logo-fr.png",
}
_SHA_RE = re.compile(r"[0-9a-f]{64}")
_RUNTIME_LOCKS_GUARD = threading.Lock()
_RUNTIME_LOCKS: dict[str, Any] = {}


class UniversalCardRuntimeError(ValueError):
    """Falha fechada de integração sem fallback para F1--F6."""


def _error(message: str) -> None:
    raise UniversalCardRuntimeError(message)


def _runtime_lock(project: str | Path):
    """Serializa ativação/leitura/render por projeto dentro deste processo."""

    key = str(Path(project).resolve())
    with _RUNTIME_LOCKS_GUARD:
        return _RUNTIME_LOCKS.setdefault(key, threading.RLock())


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UniversalCardRuntimeError(f"{label}: JSON ausente ou inválido.") from exc
    if not isinstance(value, dict):
        _error(f"{label}: esperado objeto JSON.")
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise UniversalCardRuntimeError(f"Asset local ausente ou ilegível: {path.name}.") from exc
    return digest.hexdigest()


def _confined(root: Path, relative: str, label: str) -> Path:
    value = Path(relative)
    if value.is_absolute() or ".." in value.parts:
        _error(f"{label}: path deve ser relativo ao projeto.")
    target = (root / value).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise UniversalCardRuntimeError(f"{label}: path escapa do projeto.") from exc
    return target


def discover_component(app_root: str | Path = APP_ROOT) -> Path:
    root = Path(app_root).resolve()
    configured = os.environ.get("FR_CARD_EDITOR_HOME", "").strip()
    candidates = [Path(configured).expanduser()] if configured else []
    candidates.extend([root / COMPONENT_RELATIVE, root / SOURCE_RELATIVE])
    for candidate in candidates:
        resolved = candidate.resolve()
        required = [resolved / "index.html", *(
            resolved / relative for relative in _COMPONENT_FILES.values()
        )]
        if all(path.is_file() and not path.is_symlink() for path in required):
            return resolved
    _error("FR Card Editor Universal modular não está instalado localmente.")


def discover_font_root(
    app_root: str | Path = APP_ROOT, editor_root: str | Path | None = None,
) -> Path:
    root = Path(app_root).resolve()
    configured = os.environ.get("FR_CARD_EDITOR_FONT_HOME", "").strip()
    candidates = [Path(configured).expanduser()] if configured else []
    if editor_root is not None:
        candidates.append(Path(editor_root) / "font-cache")
    candidates.append(root / SOURCE_RELATIVE / ".m9-goldens" / "font-cache")
    contract = _read_json(root / "contracts/m9/font_sources_v1.json", "font_sources_v1")
    names = [row.get("file") for row in contract.get("fonts", []) if isinstance(row, dict)]
    for candidate in candidates:
        resolved = candidate.resolve()
        if names and all(isinstance(name, str) and (resolved / name).is_file() for name in names):
            return resolved
    _error(
        "Fontes fixadas M9.0 ausentes. Gere o cache local ou configure "
        "FR_CARD_EDITOR_FONT_HOME; nenhuma fonte de fallback será usada."
    )


def _component_authority(editor_root: Path) -> dict[str, dict[str, Any]]:
    installed = editor_root / "LOCAL_COMPONENT_MANIFEST.json"
    if installed.is_file():
        manifest = _read_json(installed, "LOCAL_COMPONENT_MANIFEST")
        if manifest.get("component_id") != "fr-card-editor" or manifest.get("component_version") != "1.1.0":
            _error("Manifesto do componente instalado possui identidade divergente.")
        provenance = manifest.get("provenance")
        if not isinstance(provenance, dict) or provenance.get("license_status") != (
            "pending_before_external_publication_or_redistribution"
        ):
            _error("Manifesto local não preserva a pendência de licença/proveniência.")
        rows = manifest.get("included_files")
        if not isinstance(rows, dict):
            _error("Manifesto local não contém included_files.")
        return rows
    contract = _read_json(APP_ROOT / "contracts/m9/fr_card_editor_1_1.json", "fr_card_editor_1_1")
    rows = contract.get("component", {}).get("files")
    if not isinstance(rows, dict):
        _error("Contrato M9.0 do componente está incompleto.")
    return rows


def component_asset_context(editor_root: str | Path) -> tuple[dict[str, dict[str, Any]], dict[str, Path]]:
    root = Path(editor_root).resolve()
    authority = _component_authority(root)
    catalog: dict[str, dict[str, Any]] = {}
    sources: dict[str, Path] = {}
    for asset_id, relative in _COMPONENT_FILES.items():
        row = authority.get(relative)
        expected = row.get("sha256") if isinstance(row, dict) else None
        if not isinstance(expected, str) or not _SHA_RE.fullmatch(expected):
            _error(f"Hash autorizado ausente para {relative}.")
        path = root / relative
        if not path.is_file() or path.is_symlink() or _sha256_file(path) != expected:
            _error(f"Asset modular ausente ou hash divergente: {relative}.")
        catalog[asset_id] = {
            "asset_id": asset_id, "scope": "component", "sha256": expected,
        }
        sources[asset_id] = path
    return catalog, sources


def _project_media_assets(
    project: Path, manifest: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, Path]]:
    catalog: dict[str, dict[str, Any]] = {}
    sources: dict[str, Path] = {}
    rows = manifest.get("media", [])
    if not isinstance(rows, list):
        _error("MANIFESTO_MEDIA.media deve ser lista.")
    for row in rows:
        if (
            not isinstance(row, dict)
            or row.get("status", "ok") != "ok"
            or row.get("media_type") not in {"image", "photo", "graphic"}
        ):
            continue
        asset_id = row.get("id")
        digest = row.get("sha256") or row.get("file_hash")
        relative = row.get("source_path")
        if not isinstance(asset_id, str) or not isinstance(digest, str) or not _SHA_RE.fullmatch(digest):
            continue
        if not isinstance(relative, str) or not relative:
            continue
        source = Path(relative).expanduser()
        if source.is_absolute():
            source = source.resolve()
        else:
            source = _confined(project, relative, "MANIFESTO_MEDIA.source_path")
        if not source.is_file() or _sha256_file(source) != digest:
            _error(f"Asset de projeto ausente ou hash divergente: {asset_id}.")
        catalog[asset_id] = {
            "asset_id": asset_id, "scope": "project_media", "sha256": digest,
        }
        sources[asset_id] = source
    return catalog, sources


def build_asset_context(
    project: str | Path,
    editor_root: str | Path,
    *,
    usage_context: str = "local_authorized",
    require_manifest: bool = True,
) -> tuple[dict[str, dict[str, Any]], dict[str, Path], list[dict[str, Any]]]:
    root = Path(project).resolve()
    catalog, sources = component_asset_context(editor_root)
    manifest_path = root / persistence.MANIFEST_PATH
    if require_manifest:
        manifest = _read_json(manifest_path, "MANIFESTO_MEDIA")
    else:
        # CARD_PREVIEW_PLAN é deliberadamente utilizável antes da preparação
        # completa do projeto. Nessa fronteira visual, a ausência do manifesto
        # significa apenas que ainda não há assets de mídia do projeto; os
        # assets do componente e do catálogo SERVICE continuam validados.
        if manifest_path.is_file():
            try:
                manifest = _read_json(manifest_path, "MANIFESTO_MEDIA")
            except UniversalCardRuntimeError:
                manifest = {"media": []}
        else:
            manifest = {"media": []}
    project_catalog, project_sources = _project_media_assets(root, manifest)
    for asset_id, row in project_catalog.items():
        if asset_id in catalog:
            _error(f"asset_id duplicado entre componente e projeto: {asset_id}.")
        catalog[asset_id] = row
        sources[asset_id] = project_sources[asset_id]
    reviews: list[dict[str, Any]] = []
    for service_key in sorted(card_v2.SERVICE_KEYS):
        try:
            resolved = service_catalog_v2.resolve_service_asset(
                service_key, usage_context, app_root=APP_ROOT,
            )
        except service_catalog_v2.ServiceCatalogV2Error as exc:
            raise UniversalCardRuntimeError(str(exc)) from exc
        catalog[resolved.asset_id] = copy.deepcopy(resolved.asset_catalog_entry)
        sources[resolved.asset_id] = resolved.source_path
        reviews.append(copy.deepcopy(resolved.review))
    return catalog, sources, reviews


def universal_state_digest(project: str | Path, instance_id: str) -> str | None:
    """Digest renderizável para cache; não valida nem altera o store."""

    path = Path(project).resolve() / persistence.STORE_PATH
    if not path.is_file():
        return None
    store = _read_json(path, "CARD_STATE_V2")
    instances = store.get("instances")
    if not isinstance(instances, list):
        _error("CARD_STATE_V2.instances deve ser lista.")
    matches = [row for row in instances if isinstance(row, dict) and row.get("instance_id") == instance_id]
    if not matches:
        return None
    if len(matches) != 1:
        _error(f"CardInstance universal duplicada: {instance_id}.")
    digest = matches[0].get("state_digest")
    if not isinstance(digest, str) or not _SHA_RE.fullmatch(digest):
        _error(f"CardInstance universal possui digest inválido: {instance_id}.")
    return digest


def list_universal_cards(project: str | Path) -> list[dict[str, Any]]:
    path = Path(project).resolve() / persistence.STORE_PATH
    if not path.is_file():
        return []
    store = _read_json(path, "CARD_STATE_V2")
    rows = store.get("instances")
    if not isinstance(rows, list):
        _error("CARD_STATE_V2.instances deve ser lista.")
    result = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            _error("CARD_STATE_V2.instances contém entrada inválida.")
        instance_id = row.get("instance_id")
        digest = row.get("state_digest")
        if not isinstance(instance_id, str) or instance_id in seen:
            _error("CARD_STATE_V2 contém instance_id inválido ou duplicado.")
        if not isinstance(digest, str) or not _SHA_RE.fullmatch(digest):
            _error(f"CARD_STATE_V2 possui digest inválido para {instance_id}.")
        seen.add(instance_id)
        result.append({
            "instance_id": instance_id,
            "state_digest": digest,
            "renderer_id": card_v2.RENDERER_ID,
            "timebase": row.get("placement", {}).get("timebase"),
            "service_key": row.get("service_key"),
        })
    return result


def migration_report(project: str | Path) -> dict[str, Any]:
    value = project_scope.read(Path(project).resolve() / migration_v99.REPORT_PATH, {})
    return copy.deepcopy(value) if isinstance(value, dict) else {}


def _migration_is_complete(project: Path, context: Mapping[str, Any]) -> dict[str, Any] | None:
    report = migration_v99.current_report(project, context)
    if report is None:
        return None
    store = project_scope.read(project / persistence.STORE_PATH, {})
    if not isinstance(store, dict) or store.get("revision") != report.get("store_revision"):
        return None
    migrated = {
        row.get("instance_id"): row.get("state_digest")
        for row in report.get("cards", [])
        if isinstance(row, dict) and row.get("outcome") == "migrated"
    }
    active = {row["instance_id"]: row["state_digest"] for row in list_universal_cards(project)}
    if migrated != active:
        return None
    previews = report.get("previews", {}).get("regenerated", [])
    preview_ids: set[str] = set()
    for row in previews:
        if not isinstance(row, dict):
            return None
        relative = row.get("relative")
        expected = row.get("sha256")
        if not isinstance(relative, str) or not isinstance(expected, str):
            return None
        target = _confined(project, relative, "migration.preview.relative")
        if not target.is_file() or _sha256_file(target) != expected:
            return None
        preview_ids.add(str(row.get("segment_id") or ""))
    if preview_ids != set(migrated):
        return None
    return report


def _activate_project_cards_unlocked(
    project: str | Path,
    *,
    app_root: str | Path = APP_ROOT,
    usage_context: str = "local_authorized",
    force: bool = False,
) -> dict[str, Any]:
    """Migra todos os cards do plano atual e regenera previews universais.

    A função é idempotente pelo fingerprint de plano/manifesto, store_revision e
    hashes dos previews. Qualquer card não convertível recebe fallback F1--F6
    nominal e justificativa no relatório; a ausência dessa rota é erro fechado.
    """

    root = Path(project).resolve()
    try:
        context = persistence.project_context(root)
    except (ValueError, persistence.CardPersistenceV2Error) as exc:
        raise UniversalCardRuntimeError(str(exc)) from exc
    current = None if force else _migration_is_complete(root, context)
    if current is not None:
        return copy.deepcopy(current) | {"idempotent": True}
    editor_root = discover_component(app_root)
    font_root = discover_font_root(app_root, editor_root)
    catalog, sources, reviews = build_asset_context(
        root, editor_root, usage_context=usage_context,
    )
    try:
        prepared = migration_v99.build_migration(root, context, catalog)
    except (migration_v99.CardMigrationV99Error, card_v2.CardStateV2Error) as exc:
        raise UniversalCardRuntimeError(str(exc)) from exc
    definitions = {
        (row["definition_id"], row["definition_version"]): row
        for row in prepared["definitions"]
    }
    preview_files: dict[str, bytes] = {}
    preview_records: list[dict[str, Any]] = []
    for instance in prepared["instances"]:
        ref = instance["definition_ref"]
        definition = definitions[(ref["definition_id"], ref["definition_version"])]
        rendered = render_universal_card(
            definition, instance, catalog, sources, font_root,
            output_size=(941, 1672), usage_context=usage_context,
        )
        relative = (PREVIEW_ROOT / _safe_filename(instance["instance_id"])).as_posix()
        preview_files[relative] = rendered.png_bytes
        preview_records.append({
            "segment_id": instance["instance_id"],
            "relative": relative,
            "version": rendered.state_digest[:24],
            "state_digest": rendered.state_digest,
            "sha256": rendered.sha256,
            "renderer_id": card_v2.RENDERER_ID,
            "input_mode": context["input_mode"],
        })
    inventory_ids = {
        str(row.get("instance_id") or "")
        for row in prepared["report"]["cards"]
        if isinstance(row, dict)
    }
    old_registry = project_scope.read(root / PREVIEW_REGISTRY, {})
    old_records = old_registry.get("previews", []) if isinstance(old_registry, dict) else []
    kept: list[dict[str, Any]] = []
    delete_paths: list[str] = []
    for row in old_records:
        if not isinstance(row, dict):
            continue
        if str(row.get("segment_id") or "") in inventory_ids:
            relative = row.get("relative")
            if isinstance(relative, str) and relative not in preview_files:
                delete_paths.append(relative)
        else:
            kept.append(copy.deepcopy(row))
    if context["input_mode"] == "ready_video":
        ready_preview = root / "_CONTROLE/READY_VIDEO_PREVIEW.json"
        if ready_preview.is_file():
            delete_paths.append("_CONTROLE/READY_VIDEO_PREVIEW.json")
        for instance_id in inventory_ids:
            cached = root / "_CACHE_RENDER/ready_video_overlays" / f"{instance_id}.png"
            if cached.is_file():
                delete_paths.append(cached.relative_to(root).as_posix())
    preview_registry = {
        "schema_version": 2,
        "generation_id": "card-migration-v99-" + migration_v99.source_fingerprint(context)[:16],
        "previews": kept + preview_records,
        "invalidated_card_ids": sorted(inventory_ids),
    }
    prepared["report"]["previews"] = {
        "invalidated": sorted(inventory_ids),
        "regenerated": copy.deepcopy(preview_records),
    }
    prepared["report"]["asset_provenance"] = {
        "manifest_revision": context["manifest_revision"],
        "component_hashes_validated": True,
        "visual_review_required": bool(reviews),
        "usage_context": usage_context,
    }
    try:
        published = persistence.publish_card_migration(
            root,
            prepared["definitions"],
            prepared["instances"],
            catalog,
            expected_project_id=context["project_id"],
            expected_plan_revision=context["plan_revision"],
            expected_manifest_revision=context["manifest_revision"],
            migration_report=prepared["report"],
            preview_files=preview_files,
            preview_registry=preview_registry,
            delete_paths=delete_paths,
            usage_context=usage_context,
        )
    except (ValueError, persistence.CardPersistenceV2Error) as exc:
        raise UniversalCardRuntimeError(str(exc)) from exc
    return copy.deepcopy(published["report"]) | {"idempotent": False}


def activate_project_cards(
    project: str | Path,
    *,
    app_root: str | Path = APP_ROOT,
    usage_context: str = "local_authorized",
    force: bool = False,
) -> dict[str, Any]:
    """Ativa os cards uma vez por projeto sem corrida entre workers locais."""

    root = Path(project).resolve()
    with _runtime_lock(root):
        return _activate_project_cards_unlocked(
            root,
            app_root=app_root,
            usage_context=usage_context,
            force=force,
        )



def render_preview_plan_card(
    project: str | Path,
    segment: Mapping[str, Any],
    output_path: str | Path,
    output_size: tuple[int, int],
    *,
    app_root: str | Path = APP_ROOT,
    usage_context: str = "local_authorized",
    source_index: int = 0,
) -> dict[str, Any]:
    """Renderiza um card de CARD_PREVIEW_PLAN pelo fr-universal-card.

    Este caminho existe para prévia de design antes de haver card temporizado no
    plano produtivo (especialmente ready_video). Não altera READY_VIDEO_PLAN nem
    EDIT_PLAN e nunca usa F1--F6 silenciosamente.
    """
    root = Path(project).resolve()
    editor_root = discover_component(app_root)
    font_root = discover_font_root(app_root, editor_root)
    catalog, sources, _reviews = build_asset_context(
        root, editor_root, usage_context=usage_context, require_manifest=False,
    )
    try:
        definition = migration_v99.build_definition(catalog)
        instance = migration_v99._new_instance(
            dict(segment), int(source_index), "raw_media", definition, catalog,
        )
        requested_size = (int(output_size[0]), int(output_size[1]))
        if requested_size[0] <= 0 or requested_size[1] <= 0:
            raise UniversalCardRuntimeError("CARD_PREVIEW_PLAN: resolução de preview inválida.")
        # O renderer universal permanece estrito e só aceita resoluções
        # congeladas. Para a UI de preview, renderizamos em uma resolução
        # contratada e só então redimensionamos para o quadro solicitado.
        # Isso permite 720x1280 e outros 9:16 sem alterar o contrato do master.
        ratio_error = abs((requested_size[0] / requested_size[1]) - (9 / 16))
        if ratio_error > 0.003:
            raise UniversalCardRuntimeError(
                f"CARD_PREVIEW_PLAN: resolução {requested_size[0]}x{requested_size[1]} não é 9:16."
            )
        contracted = [tuple(item) for item in definition["canvas"]["export_resolutions"]]
        render_size = requested_size if requested_size in contracted else (941, 1672)
        rendered = render_universal_card(
            definition, instance, catalog, sources, font_root,
            output_size=render_size, usage_context=usage_context,
        )
    except (migration_v99.CardMigrationV99Error, card_v2.CardStateV2Error) as exc:
        raise UniversalCardRuntimeError(str(exc)) from exc
    image_bytes = rendered.png_bytes
    if render_size != requested_size:
        with Image.open(BytesIO(image_bytes)) as opened:
            resized = opened.convert("RGB").resize(requested_size, Image.Resampling.LANCZOS)
        output = BytesIO()
        resized.save(output, format="PNG", compress_level=9, optimize=False)
        image_bytes = output.getvalue()
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(image_bytes)
    return {
        "renderer_id": card_v2.RENDERER_ID,
        "definition_version": definition["definition_version"],
        "state_digest": rendered.state_digest,
        "sha256": rendered.sha256,
        "preview_only": True,
    }

def rollback_project_card_activation(project: str | Path, rollback_version: str) -> dict[str, Any]:
    """Restaura o snapshot anterior, inclusive store/relatório/previews ausentes."""

    root = Path(project).resolve()
    report = migration_report(root)
    if report.get("rollback_version") != rollback_version:
        _error("rollback_version não corresponde à ativação M9.9 atual.")
    try:
        result = project_scope.restore_version(root, rollback_version)
    except ValueError as exc:
        raise UniversalCardRuntimeError(str(exc)) from exc
    return result | {"card_activation_rolled_back": True}


def explicit_legacy_fallback(project: str | Path, instance_id: str) -> dict[str, Any]:
    try:
        route = migration_v99.route(project, instance_id)
    except migration_v99.CardMigrationV99Error as exc:
        raise UniversalCardRuntimeError(str(exc)) from exc
    fallback = route.get("fallback")
    if (
        route.get("outcome") != "compatibility_fallback"
        or route.get("renderer_id") != migration_v99.LEGACY_RENDERER_ID
        or not isinstance(fallback, dict)
        or fallback.get("registered") is not True
        or not fallback.get("reason")
    ):
        _error(f"Card {instance_id!r} não possui fallback legado explícito válido.")
    return route


def register_derived_plan_fallbacks(
    project: str | Path,
    plan: Mapping[str, Any],
    *,
    plan_label: str,
) -> dict[str, Any]:
    """Registra cards de timelines derivadas fora do store canônico do projeto.

    Reels e drafts podem renumerar cards e alterar sua duração sem fazer parte
    do ``EDIT_PLAN.json`` que ancora CardInstance v2. Esses cards continuam no
    renderer legado apenas por uma rota nominal no relatório M9.9; nunca por
    ausência implícita de estado universal.
    """

    root = Path(project).resolve()
    if not isinstance(plan, Mapping):
        _error("Plano derivado inválido para registro de fallback M9.9.")
    rows = [
        (index, row)
        for index, row in enumerate(plan.get("segments", []))
        if isinstance(row, Mapping) and row.get("type") == "card"
    ]
    labels = [str(row.get("segment_id") or "") for _index, row in rows]
    if any(not label for label in labels) or len(labels) != len(set(labels)):
        _error("Plano derivado possui IDs de card ausentes ou duplicados.")
    with _runtime_lock(root):
        report = migration_report(root)
        if report.get("migration_id") != migration_v99.MIGRATION_ID:
            _error("Ativação M9.9 ausente antes do plano derivado.")
        cards = report.get("cards")
        if not isinstance(cards, list):
            _error("Relatório M9.9 não contém inventário de cards válido.")
        existing = {
            str(row.get("instance_id"))
            for row in cards
            if isinstance(row, Mapping) and row.get("instance_id")
        }
        reason = (
            f"Plano derivado {plan_label!r} não pertence ao EDIT_PLAN.json canônico; "
            "compatibilidade F1–F6 registrada sem persistir estado fora da timeline principal."
        )
        for index, row in rows:
            instance_id = str(row["segment_id"])
            if instance_id in existing:
                continue
            cards.append({
                "instance_id": instance_id,
                "source_index": index,
                "source_digest": project_scope.digest(row),
                "outcome": "compatibility_fallback",
                "renderer_id": migration_v99.LEGACY_RENDERER_ID,
                "fallback": {"registered": True, "reason": reason},
            })
            existing.add(instance_id)
        migrated = sum(
            isinstance(row, Mapping) and row.get("outcome") == "migrated"
            for row in cards
        )
        fallback = len(cards) - migrated
        report["counts"] = {
            "discovered": len(cards),
            "migrated": migrated,
            "fallback": fallback,
        }
        report["status"] = (
            "completed" if fallback == 0 else "completed_with_explicit_fallback"
        )
        sealed = migration_v99.seal_report(report)
        project_scope.write(root / migration_v99.REPORT_PATH, sealed)
        return copy.deepcopy(sealed)


def _asset_options(
    catalog: Mapping[str, Mapping[str, Any]],
    binding_builder: Callable[[str], str],
) -> list[dict[str, Any]]:
    result = []
    for asset_id in sorted(catalog):
        row = catalog[asset_id]
        result.append({
            "asset_id": asset_id,
            "scope": row["scope"],
            "sha256": row["sha256"],
            "binding": binding_builder(asset_id),
            "visual_review_required": bool(row.get("visual_review_required")),
            "opaque_background_preserved": bool(row.get("opaque_background_preserved")),
            "publicavel": row.get("publicavel"),
        })
    return result


def open_editor_session(
    project: str | Path,
    instance_id: str,
    *,
    expected_project_id: str,
    editor_root: str | Path,
    binding_builder: Callable[[str], str],
    usage_context: str = "local_authorized",
) -> dict[str, Any]:
    catalog, sources, reviews = build_asset_context(
        project, editor_root, usage_context=usage_context,
    )
    loaded = persistence.load_card_state(
        project, instance_id, catalog,
        expected_project_id=expected_project_id, usage_context=usage_context,
    )
    bindings = {asset_id: binding_builder(asset_id) for asset_id in sources}
    try:
        session = adapter.export_card_state(
            loaded["definition"], loaded["instance"], catalog, bindings,
        )
    except adapter.CardEditorAdapterV2Error as exc:
        raise UniversalCardRuntimeError(str(exc)) from exc
    return {
        "project_id": loaded["project_id"],
        "input_mode": loaded["source"]["input_mode"],
        "renderer_id": loaded["definition"]["renderer_id"],
        "session": session,
        "asset_options": _asset_options(catalog, binding_builder),
        "instance_revision": loaded["instance_revision"],
        "store_revision": loaded["store_revision"],
        "visual_review_required": bool(reviews),
        "license_status": "pending_before_external_publication_or_redistribution",
        "external_distribution_allowed": False,
    }


def asset_source(
    project: str | Path,
    instance_id: str,
    asset_id: str,
    *,
    expected_project_id: str,
    editor_root: str | Path,
    usage_context: str = "local_authorized",
) -> Path:
    catalog, sources, _reviews = build_asset_context(
        project, editor_root, usage_context=usage_context,
    )
    persistence.load_card_state(
        project, instance_id, catalog,
        expected_project_id=expected_project_id, usage_context=usage_context,
    )
    source = sources.get(asset_id)
    if source is None or asset_id not in catalog:
        _error("Asset não pertence ao catálogo validado desta sessão.")
    return Path(source)


def _safe_filename(instance_id: str) -> str:
    label = re.sub(r"[^A-Za-z0-9_-]", "-", instance_id).strip("-")[:64] or "card"
    return f"{label}-{hashlib.sha256(instance_id.encode('utf-8')).hexdigest()[:10]}.png"


def _write_preview(
    project: Path,
    instance_id: str,
    png_bytes: bytes,
    *,
    state_digest: str,
    renderer_sha256: str,
    input_mode: str,
) -> dict[str, Any]:
    relative = PREVIEW_ROOT / _safe_filename(instance_id)
    target = project / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".png.tmp")
    temporary.write_bytes(png_bytes)
    if _sha256_file(temporary) != renderer_sha256:
        temporary.unlink(missing_ok=True)
        _error("Preview universal divergiu do hash produzido pelo renderer.")
    temporary.replace(target)
    registry_path = project / PREVIEW_REGISTRY
    registry = project_scope.read(registry_path, {})
    records = [
        row for row in registry.get("previews", [])
        if isinstance(row, dict) and row.get("segment_id") != instance_id
    ]
    record = {
        "segment_id": instance_id,
        "relative": relative.as_posix(),
        "version": state_digest[:24],
        "state_digest": state_digest,
        "sha256": renderer_sha256,
        "renderer_id": card_v2.RENDERER_ID,
        "input_mode": input_mode,
    }
    records.append(record)
    project_scope.write(registry_path, {
        "schema_version": 2,
        "generation_id": "card-state-v2-" + state_digest[:16],
        "previews": records,
    })
    return record


def _record_saved_universal_state(
    project: Path, instance_id: str, *, store_revision: str,
    state_digest: str, preview: Mapping[str, Any],
) -> None:
    report = migration_report(project)
    if report.get("migration_id") != migration_v99.MIGRATION_ID:
        return
    cards = report.get("cards")
    if not isinstance(cards, list):
        _error("Relatório M9.9 não contém cards válidos.")
    matches = [row for row in cards if isinstance(row, dict) and row.get("instance_id") == instance_id]
    if len(matches) != 1 or matches[0].get("outcome") != "migrated":
        _error("Card salvo não possui registro universal único na migração M9.9.")
    matches[0]["state_digest"] = state_digest
    report["store_revision"] = store_revision
    previews = report.setdefault("previews", {})
    regenerated = [
        row for row in previews.get("regenerated", [])
        if isinstance(row, dict) and row.get("segment_id") != instance_id
    ]
    regenerated.append(copy.deepcopy(dict(preview)))
    previews["regenerated"] = regenerated
    project_scope.write(project / migration_v99.REPORT_PATH, migration_v99.seal_report(report))


def save_editor_session(
    project: str | Path,
    payload: Any,
    *,
    expected_project_id: str,
    editor_root: str | Path,
    binding_builder: Callable[[str], str],
    usage_context: str = "local_authorized",
    font_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(project).resolve()
    if not isinstance(payload, dict):
        _error("Payload do editor deve ser objeto.")
    instance_id = str(payload.get("instance_id") or "")
    catalog, sources, _reviews = build_asset_context(
        root, editor_root, usage_context=usage_context,
    )
    loaded = persistence.load_card_state(
        root, instance_id, catalog,
        expected_project_id=expected_project_id, usage_context=usage_context,
    )
    bindings = {asset_id: binding_builder(asset_id) for asset_id in sources}
    try:
        candidate = adapter.apply_card_state(
            loaded["definition"], loaded["instance"], payload, catalog, bindings,
        )
    except adapter.CardEditorAdapterV2Error as exc:
        raise UniversalCardRuntimeError(str(exc)) from exc
    fonts = Path(font_root) if font_root is not None else discover_font_root(APP_ROOT, editor_root)
    # Render antes de qualquer escrita: preview e estado persistido são o mesmo candidato.
    rendered = render_universal_card(
        loaded["definition"], candidate, catalog, sources, fonts,
        output_size=(941, 1672), usage_context=usage_context,
    )
    saved = persistence.save_card_state(
        root, loaded["definition"], candidate, catalog,
        expected_project_id=expected_project_id,
        expected_plan_revision=loaded["source"]["plan_revision"],
        expected_store_revision=loaded["store_revision"],
        base_revision=loaded["instance_revision"],
        usage_context=usage_context,
    )
    preview = _write_preview(
        root, instance_id, rendered.png_bytes,
        state_digest=rendered.state_digest,
        renderer_sha256=rendered.sha256,
        input_mode=loaded["source"]["input_mode"],
    )
    _record_saved_universal_state(
        root,
        instance_id,
        store_revision=saved["store_revision"],
        state_digest=rendered.state_digest,
        preview=preview,
    )
    return {
        **saved,
        "preview": preview,
        "renderer_sha256": rendered.sha256,
        "renderer_report": copy.deepcopy(rendered.report),
    }


def _render_timeline_card_unlocked(
    project: str | Path,
    instance_id: str,
    target: str | Path,
    size: tuple[int, int],
    *,
    usage_context: str = "local_authorized",
    app_root: str | Path = APP_ROOT,
    allow_migration_preview_cache: bool = False,
) -> bool:
    """Renderiza v2; retorna False somente para fallback legado registrado.

    ``allow_migration_preview_cache`` serve apenas para materializar uma prévia
    já produzida e conferida na ativação. Masters deixam a opção desativada e
    continuam renderizando na resolução contratada.
    """

    root = Path(project).resolve()
    activate_project_cards(
        root, app_root=app_root, usage_context=usage_context,
    )
    state_digest = universal_state_digest(root, instance_id)
    if state_digest is None:
        explicit_legacy_fallback(root, instance_id)
        return False
    if allow_migration_preview_cache:
        report = migration_report(root)
        cached = next((
            row for row in report.get("previews", {}).get("regenerated", [])
            if isinstance(row, dict)
            and row.get("segment_id") == instance_id
            and row.get("state_digest") == state_digest
        ), None)
        if cached is not None:
            relative = cached.get("relative")
            expected = cached.get("sha256")
            if isinstance(relative, str) and isinstance(expected, str):
                source = _confined(root, relative, "migration.preview.relative")
                if source.is_file() and _sha256_file(source) == expected:
                    with Image.open(source) as opened:
                        image = opened.convert("RGB")
                        if image.size != size:
                            image = image.resize(size, Image.Resampling.LANCZOS)
                    path = Path(target)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    temporary = path.with_suffix(path.suffix + ".tmp")
                    image.save(temporary, format="PNG", compress_level=9, optimize=False)
                    temporary.replace(path)
                    return True
    editor_root = discover_component(app_root)
    font_root = discover_font_root(app_root, editor_root)
    catalog, sources, _reviews = build_asset_context(
        root, editor_root, usage_context=usage_context,
    )
    context = persistence.project_context(root)
    loaded = persistence.load_card_state(
        root, instance_id, catalog,
        expected_project_id=context["project_id"], usage_context=usage_context,
    )
    definition = loaded["definition"]
    contracted = {tuple(item) for item in definition["canvas"]["export_resolutions"]}
    render_size = size if size in contracted else (941, 1672)
    rendered = persistence.render_persisted_card(
        root, instance_id, catalog, sources, font_root,
        expected_project_id=context["project_id"], usage_context=usage_context,
        output_size=render_size,
    )
    image_bytes = rendered.png_bytes
    if render_size != size:
        with Image.open(BytesIO(image_bytes)) as opened:
            resized = opened.convert("RGB").resize(size, Image.Resampling.LANCZOS)
        output = BytesIO()
        resized.save(output, format="PNG", compress_level=9, optimize=False)
        image_bytes = output.getvalue()
    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(image_bytes)
    temporary.replace(path)
    return True


def render_timeline_card(
    project: str | Path,
    instance_id: str,
    target: str | Path,
    size: tuple[int, int],
    *,
    usage_context: str = "local_authorized",
    app_root: str | Path = APP_ROOT,
    allow_migration_preview_cache: bool = False,
) -> bool:
    """Renderiza um card sem disputar o lock de projeto entre workers locais."""

    root = Path(project).resolve()
    with _runtime_lock(root):
        return _render_timeline_card_unlocked(
            root,
            instance_id,
            target,
            size,
            usage_context=usage_context,
            app_root=app_root,
            allow_migration_preview_cache=allow_migration_preview_cache,
        )
