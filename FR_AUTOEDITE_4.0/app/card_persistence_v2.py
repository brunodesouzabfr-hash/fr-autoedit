"""Persistência transacional de CardDefinition/CardInstance v2 por projeto.

O sidecar mantém o estado universal separado dos planos legados. ``EDIT_PLAN``
e ``READY_VIDEO_PLAN`` são lidos para validar placement e revisão, mas nunca são
reescritos por este módulo. AssetRefs persistidos não contêm paths: assets de
projeto vêm de ``MANIFESTO_MEDIA.json`` e medalhões SERVICE continuam sob a
autoridade manifest-driven de :mod:`service_catalog_v2`.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

import card_state_v2 as card_v2
import project_scope
import service_catalog_v2


APP_ROOT = Path(__file__).resolve().parents[1]
STORE_PATH = "_CONTROLE/CARD_STATE_V2.json"
STORE_SCHEMA_VERSION = 1
STORE_ID = "fr-card-state-project/1"
MANIFEST_PATH = "MANIFESTO_MEDIA.json"
RAW_PLAN_PATH = "EDIT_PLAN.json"
READY_PLAN_PATH = "READY_VIDEO_PLAN.json"
MIGRATION_REPORT_PATH = "_CONTROLE/CARD_MIGRATION_V99.json"
INPUT_MODES = frozenset({"raw_media", "ready_video"})
READY_CARD_KINDS = frozenset({"common_card", "service_card"})
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_STORE_FIELDS = frozenset({
    "schema_version", "store_id", "project_id", "source", "definitions",
    "instances", "snapshots", "revision",
})
_SOURCE_FIELDS = frozenset({
    "input_mode", "plan_path", "plan_revision", "manifest_path",
    "manifest_revision", "base_video_id", "timeline_locked",
})


class CardPersistenceV2Error(ValueError):
    """Falha fechada antes de publicar estado universal no projeto."""


def _error(label: str, message: str) -> None:
    raise CardPersistenceV2Error(f"{label}: {message}")


def _object(
    value: Any, *, label: str, allowed: frozenset[str], required: frozenset[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        _error(label, "esperado objeto.")
    unknown = sorted(set(value) - allowed)
    if unknown:
        _error(label, "campos desconhecidos: " + ", ".join(unknown) + ".")
    missing = sorted((required or allowed) - set(value))
    if missing:
        _error(label, "campos obrigatórios ausentes: " + ", ".join(missing) + ".")
    return value


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        _error(label, "esperado SHA-256 hexadecimal minúsculo.")
    return value


def _canonical_bytes(value: Any, label: str) -> bytes:
    try:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise CardPersistenceV2Error(f"{label}: JSON canônico inválido.") from exc


def _digest(value: Any, label: str) -> str:
    return hashlib.sha256(_canonical_bytes(value, label)).hexdigest()


def _read_json(path: Path, label: str) -> dict[str, Any]:
    duplicates: list[str] = []

    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                duplicates.append(key)
            result[key] = value
        return result

    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs_hook)
    except (OSError, json.JSONDecodeError) as exc:
        raise CardPersistenceV2Error(f"{label}: arquivo ausente ou JSON inválido: {path.name}.") from exc
    if duplicates:
        _error(label, "chaves JSON duplicadas: " + ", ".join(sorted(set(duplicates))) + ".")
    if not isinstance(value, dict):
        _error(label, "esperado objeto JSON.")
    return value


def _sha256_file(path: Path, label: str) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise CardPersistenceV2Error(f"{label}: asset ausente ou ilegível.") from exc
    return digest.hexdigest()


def _project(project: str | Path) -> Path:
    root = Path(project).expanduser().resolve()
    if not root.is_dir():
        _error("project", "diretório do projeto inexistente.")
    return root


def _project_file(project: Path, relative: str, label: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        _error(label, "path relativo inválido.")
    target = (project / relative).resolve()
    try:
        target.relative_to(project)
    except ValueError as exc:
        raise CardPersistenceV2Error(f"{label}: path escapa do projeto.") from exc
    return target


def _source_context(project: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest = _read_json(project / MANIFEST_PATH, "manifest")
    raw_mode = manifest.get("input_mode")
    if raw_mode is None:
        ready_candidate = project / READY_PLAN_PATH
        if ready_candidate.is_file():
            candidate = _read_json(ready_candidate, "ready_plan")
            raw_mode = candidate.get("input_mode")
        else:
            raw_mode = "raw_media"
    if raw_mode not in INPUT_MODES:
        _error("manifest.input_mode", "use raw_media ou ready_video.")
    mode = str(raw_mode)
    plan_path = READY_PLAN_PATH if mode == "ready_video" else RAW_PLAN_PATH
    plan = _read_json(project / plan_path, "source_plan")
    base_video_id = ""
    timeline_locked = False
    if mode == "ready_video":
        if plan.get("input_mode") != "ready_video":
            _error("source_plan.input_mode", "plano ready deve declarar ready_video.")
        if plan.get("timeline_locked") is not True:
            _error("source_plan.timeline_locked", "ready_video exige true.")
        base_video_id = plan.get("base_video_id")
        if not isinstance(base_video_id, str) or not base_video_id:
            _error("source_plan.base_video_id", "vídeo-base ausente.")
        timeline_locked = True
    source = {
        "input_mode": mode,
        "plan_path": plan_path,
        "plan_revision": _digest(plan, "source_plan"),
        "manifest_path": MANIFEST_PATH,
        "manifest_revision": _digest(manifest, "manifest"),
        "base_video_id": base_video_id,
        "timeline_locked": timeline_locked,
    }
    return source, plan, manifest


def _current_project_id(project: Path, manifest: Mapping[str, Any], *, create: bool) -> str:
    identity_path = project / "_CONTROLE" / "MEDIA_LIBRARY.json"
    identity = project_scope.read(identity_path, {})
    if not isinstance(identity, dict):
        _error("project_identity", "metadado de projeto inválido.")
    if not identity.get("project_id") and create:
        identity = project_scope.identity(project, dict(manifest))
    project_id = identity.get("project_id")
    if not isinstance(project_id, str) or not project_id or len(project_id) > 128:
        _error("project_identity.project_id", "identidade estável ausente.")
    return project_id


def project_context(project: str | Path) -> dict[str, Any]:
    """Devolve os tokens necessários a uma escrita sem depender do navegador."""

    root = _project(project)
    with project_scope.project_lock(root):
        source, _plan, manifest = _source_context(root)
        project_id = _current_project_id(root, manifest, create=True)
        store_path = root / STORE_PATH
        store_revision = None
        if store_path.is_file():
            raw = _read_json(store_path, "card_store")
            store_revision = raw.get("revision")
            _sha256(store_revision, "card_store.revision")
        return {
            "project_id": project_id,
            "input_mode": source["input_mode"],
            "plan_revision": source["plan_revision"],
            "manifest_revision": source["manifest_revision"],
            "store_revision": store_revision,
        }


def _state_asset_refs(state: Any) -> Iterable[dict[str, Any]]:
    if not isinstance(state, Mapping):
        return ()
    assets = state.get("assets")
    if not isinstance(assets, Mapping):
        return ()
    return tuple(
        value for name in ("background", "logo", "visual")
        if isinstance((value := assets.get(name)), dict)
    )


def _all_asset_refs(
    definitions: Iterable[Any], instances: Iterable[Any], snapshots: Iterable[Any],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for definition in definitions:
        if isinstance(definition, Mapping):
            result.extend(_state_asset_refs(definition.get("default_state")))
    for instance in instances:
        if isinstance(instance, Mapping):
            result.extend(_state_asset_refs(instance.get("state")))
    for snapshot in snapshots:
        if not isinstance(snapshot, Mapping):
            continue
        definition = snapshot.get("definition")
        instance = snapshot.get("instance")
        if isinstance(definition, Mapping):
            result.extend(_state_asset_refs(definition.get("default_state")))
        if isinstance(instance, Mapping):
            result.extend(_state_asset_refs(instance.get("state")))
    return result


def _manifest_media(manifest: Mapping[str, Any], asset_id: str) -> Mapping[str, Any]:
    rows = manifest.get("media")
    if not isinstance(rows, list):
        _error("manifest.media", "esperada lista para resolver asset de projeto.")
    matches = [row for row in rows if isinstance(row, Mapping) and row.get("id") == asset_id]
    if len(matches) != 1:
        _error("manifest.media", f"asset_id deve existir uma vez no manifesto: {asset_id}.")
    row = matches[0]
    if row.get("status", "ok") != "ok":
        _error("manifest.media." + asset_id, "asset não está disponível.")
    return row


def _manifest_hash(row: Mapping[str, Any], label: str) -> str:
    value = row.get("sha256") or row.get("file_hash")
    return _sha256(value, label + ".sha256")


def _manifest_source(project: Path, row: Mapping[str, Any], label: str) -> Path:
    value = row.get("source_path")
    if not isinstance(value, str) or not value:
        _error(label + ".source_path", "path ausente no manifesto.")
    source = Path(value).expanduser()
    if not source.is_absolute():
        source = _project_file(project, value, label + ".source_path")
    else:
        source = source.resolve()
    if not source.is_file():
        _error(label + ".source_path", "asset do manifesto está ausente.")
    return source


def _merge_catalog_entry(
    catalog: dict[str, Mapping[str, Any]], sources: dict[str, str | Path],
    *, asset_id: str, entry: Mapping[str, Any], source: Path | None,
) -> None:
    existing = catalog.get(asset_id)
    if existing is not None and (
        not isinstance(existing, Mapping)
        or existing.get("scope") != entry.get("scope")
        or existing.get("sha256") != entry.get("sha256")
    ):
        _error("asset_catalog." + asset_id, "binding confiável divergente.")
    catalog[asset_id] = copy.deepcopy(entry)
    if source is not None:
        existing_source = sources.get(asset_id)
        if existing_source is not None and Path(existing_source).resolve() != source.resolve():
            _error("asset_sources." + asset_id, "path confiável divergente.")
        sources[asset_id] = source


def _prepare_assets(
    project: Path,
    definitions: Iterable[Any],
    instances: Iterable[Any],
    snapshots: Iterable[Any],
    asset_catalog: Mapping[str, Mapping[str, Any]],
    asset_sources: Mapping[str, str | Path] | None,
    manifest: Mapping[str, Any],
    usage_context: str,
) -> tuple[dict[str, Mapping[str, Any]], dict[str, str | Path]]:
    if not isinstance(asset_catalog, Mapping):
        _error("asset_catalog", "catálogo confiável obrigatório.")
    if asset_sources is not None and not isinstance(asset_sources, Mapping):
        _error("asset_sources", "bindings confiáveis devem ser objeto.")
    catalog: dict[str, Mapping[str, Any]] = copy.deepcopy(dict(asset_catalog))
    sources: dict[str, str | Path] = dict(asset_sources or {})
    refs = _all_asset_refs(definitions, instances, snapshots)
    service_keys = {
        instance.get("service_key") for instance in instances
        if isinstance(instance, Mapping) and isinstance(instance.get("service_key"), str)
    }
    service_keys.update(
        snapshot.get("instance", {}).get("service_key")
        for snapshot in snapshots
        if isinstance(snapshot, Mapping)
        and isinstance(snapshot.get("instance"), Mapping)
        and isinstance(snapshot["instance"].get("service_key"), str)
    )
    try:
        resolved_services = {
            key: service_catalog_v2.resolve_service_asset(
                key, usage_context, app_root=APP_ROOT,
            )
            for key in service_keys
        }
    except service_catalog_v2.ServiceCatalogV2Error as exc:
        raise CardPersistenceV2Error(str(exc)) from exc
    for resolved in resolved_services.values():
        _merge_catalog_entry(
            catalog, sources, asset_id=resolved.asset_id,
            entry=resolved.asset_catalog_entry, source=resolved.source_path,
        )
    for index, ref in enumerate(refs):
        scope = ref.get("scope")
        asset_id = ref.get("asset_id")
        expected = ref.get("sha256")
        label = f"asset_refs[{index}]"
        if not isinstance(asset_id, str):
            _error(label + ".asset_id", "ID inválido.")
        if scope == "service_catalog":
            key = asset_id.removeprefix("medallion_")
            resolved = resolved_services.get(key)
            if resolved is None or resolved.asset_ref != ref:
                _error(label, "AssetRef SERVICE diverge do manifesto produtivo.")
            continue
        if scope not in {"project_media", "project_asset"}:
            continue
        row = _manifest_media(manifest, asset_id)
        received_hash = _manifest_hash(row, "manifest.media." + asset_id)
        if expected != received_hash:
            _error(label + ".sha256", "hash diverge do MANIFESTO_MEDIA.json.")
        source = _manifest_source(project, row, "manifest.media." + asset_id)
        if _sha256_file(source, label) != received_hash:
            _error(label + ".sha256", "bytes divergem do MANIFESTO_MEDIA.json.")
        entry = {"asset_id": asset_id, "scope": scope, "sha256": received_hash}
        _merge_catalog_entry(
            catalog, sources, asset_id=asset_id, entry=entry, source=source,
        )
    return catalog, sources


def _validate_source(value: Any, current: Mapping[str, Any]) -> dict[str, Any]:
    row = _object(value, label="card_store.source", allowed=_SOURCE_FIELDS)
    if row.get("input_mode") not in INPUT_MODES:
        _error("card_store.source.input_mode", "modo inválido.")
    _sha256(row.get("plan_revision"), "card_store.source.plan_revision")
    _sha256(row.get("manifest_revision"), "card_store.source.manifest_revision")
    if row != current:
        changed = sorted(key for key in _SOURCE_FIELDS if row.get(key) != current.get(key))
        _error(
            "card_store.source",
            "origem/revisão mudou desde a escrita: " + ", ".join(changed) + ".",
        )
    return copy.deepcopy(row)


def _validate_binding(instance: Mapping[str, Any], source: Mapping[str, Any], plan: Mapping[str, Any]) -> None:
    instance_id = instance["instance_id"]
    placement = instance["placement"]
    if source["input_mode"] == "raw_media":
        if placement.get("timebase") != "raw_sequence":
            _error("card_instance.placement.timebase", "projeto raw exige raw_sequence.")
        segments = plan.get("segments")
        if not isinstance(segments, list):
            _error("source_plan.segments", "timeline raw inválida.")
        matches = [
            (index, row) for index, row in enumerate(segments)
            if isinstance(row, Mapping) and row.get("segment_id") == instance_id
        ]
        if len(matches) != 1 or matches[0][1].get("type") != "card":
            _error("card_instance.instance_id", "card raw não existe uma vez no plano atual.")
        index, target = matches[0]
        duration = target.get("duration_sec")
        if (
            placement.get("sequence_index") != index
            or isinstance(duration, bool)
            or not isinstance(duration, (int, float))
            or not math.isfinite(float(duration))
            or abs(float(placement.get("duration_sec")) - float(duration)) > 0.000001
        ):
            _error("card_instance.placement", "ordem/duração divergem da timeline raw.")
    else:
        if source.get("timeline_locked") is not True or placement.get("timebase") != "ready_video_base":
            _error("card_instance.placement.timebase", "ready_video exige base bloqueada.")
        overlays = plan.get("overlays")
        if not isinstance(overlays, list):
            _error("source_plan.overlays", "lista de overlays inválida.")
        matches = [
            row for row in overlays
            if isinstance(row, Mapping) and row.get("overlay_id") == instance_id
        ]
        if len(matches) != 1 or matches[0].get("kind") not in READY_CARD_KINDS:
            _error("card_instance.instance_id", "card ready não existe uma vez no plano atual.")
        target = matches[0]
        if (
            abs(float(placement.get("start_sec")) - float(target.get("start_sec"))) > 0.000001
            or abs(float(placement.get("end_sec")) - float(target.get("end_sec"))) > 0.000001
        ):
            _error("card_instance.placement", "janela diverge do overlay ready atual.")
    expected_service = str(target.get("service_key") or "")
    received_service = str(instance.get("service_key") or "")
    if expected_service != received_service:
        _error("card_instance.service_key", "diverge do card físico atual.")


def _definition_key(definition: Mapping[str, Any]) -> tuple[str, int]:
    return str(definition["definition_id"]), int(definition["definition_version"])


def _store_basis(store: Mapping[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(value) for key, value in store.items() if key != "revision"}


def _with_revision(store: Mapping[str, Any]) -> dict[str, Any]:
    basis = _store_basis(store)
    return basis | {"revision": _digest(basis, "card_store")}


def _empty_store(project_id: str, source: Mapping[str, Any]) -> dict[str, Any]:
    return _with_revision({
        "schema_version": STORE_SCHEMA_VERSION,
        "store_id": STORE_ID,
        "project_id": project_id,
        "source": copy.deepcopy(source),
        "definitions": [],
        "instances": [],
        "snapshots": [],
    })


def _validate_store(
    value: Any,
    *,
    project: Path,
    project_id: str,
    current_source: Mapping[str, Any],
    plan: Mapping[str, Any],
    manifest: Mapping[str, Any],
    asset_catalog: Mapping[str, Mapping[str, Any]],
    usage_context: str,
) -> tuple[dict[str, Any], dict[str, Mapping[str, Any]]]:
    row = _object(value, label="card_store", allowed=_STORE_FIELDS)
    if row["schema_version"] != STORE_SCHEMA_VERSION:
        _error("card_store.schema_version", f"esperado {STORE_SCHEMA_VERSION}.")
    if row["store_id"] != STORE_ID:
        _error("card_store.store_id", f"esperado {STORE_ID}.")
    if row["project_id"] != project_id:
        _error("card_store.project_id", "estado pertence a outro projeto.")
    source = _validate_source(row["source"], current_source)
    for name in ("definitions", "instances", "snapshots"):
        if not isinstance(row[name], list):
            _error("card_store." + name, "esperada lista.")
    trusted_catalog, _sources = _prepare_assets(
        project, row["definitions"], row["instances"], row["snapshots"],
        asset_catalog, None, manifest, usage_context,
    )
    definitions: list[dict[str, Any]] = []
    definition_map: dict[tuple[str, int], dict[str, Any]] = {}
    for index, raw in enumerate(row["definitions"]):
        try:
            definition = card_v2.validate_card_definition_v2(
                raw, trusted_catalog, label=f"card_store.definitions[{index}]",
            )
        except card_v2.CardStateV2Error as exc:
            raise CardPersistenceV2Error(str(exc)) from exc
        key = _definition_key(definition)
        if key in definition_map:
            _error("card_store.definitions", "definition_id/version duplicado.")
        definition_map[key] = definition
        definitions.append(definition)
    instances: list[dict[str, Any]] = []
    instance_ids: set[str] = set()
    for index, raw in enumerate(row["instances"]):
        if not isinstance(raw, Mapping):
            _error(f"card_store.instances[{index}]", "esperado objeto.")
        ref = raw.get("definition_ref")
        key = (
            str(ref.get("definition_id")), int(ref.get("definition_version"))
        ) if isinstance(ref, Mapping) and isinstance(ref.get("definition_version"), int) else None
        definition = definition_map.get(key) if key is not None else None
        if definition is None:
            _error(f"card_store.instances[{index}].definition_ref", "definição não encontrada.")
        try:
            instance = card_v2.validate_card_instance_v2(
                raw, definition, trusted_catalog, label=f"card_store.instances[{index}]",
            )
        except card_v2.CardStateV2Error as exc:
            raise CardPersistenceV2Error(str(exc)) from exc
        if instance["instance_id"] in instance_ids:
            _error("card_store.instances", "instance_id duplicado.")
        instance_ids.add(instance["instance_id"])
        _validate_binding(instance, source, plan)
        instances.append(instance)
    snapshots: list[dict[str, Any]] = []
    snapshot_ids: set[str] = set()
    for index, raw in enumerate(row["snapshots"]):
        try:
            snapshot = card_v2.validate_card_snapshot(raw, trusted_catalog)
        except card_v2.CardStateV2Error as exc:
            raise CardPersistenceV2Error(
                f"card_store.snapshots[{index}]: {exc}"
            ) from exc
        if snapshot["snapshot_digest"] in snapshot_ids:
            _error("card_store.snapshots", "snapshot_digest duplicado.")
        snapshot_ids.add(snapshot["snapshot_digest"])
        _validate_binding(snapshot["instance"], source, plan)
        snapshots.append(snapshot)
    normalized = {
        "schema_version": STORE_SCHEMA_VERSION,
        "store_id": STORE_ID,
        "project_id": project_id,
        "source": source,
        "definitions": definitions,
        "instances": instances,
        "snapshots": snapshots,
    }
    revision = _sha256(row["revision"], "card_store.revision")
    if revision != _digest(normalized, "card_store"):
        _error("card_store.revision", "digest diverge do conteúdo persistido.")
    return normalized | {"revision": revision}, trusted_catalog


def _assert_expected(value: Any, expected: str, label: str) -> None:
    if value != expected:
        _error(label, "revisão obsoleta; recarregue o projeto atual.")


def _publish_store(project: Path, store: Mapping[str, Any], name: str) -> Path:
    rollback = project_scope.snapshot_decisions(project, name)
    project_scope.publish_files(project, {STORE_PATH: copy.deepcopy(store)})
    return rollback


def publish_card_migration(
    project: str | Path,
    definitions: Any,
    instances: Any,
    asset_catalog: Mapping[str, Mapping[str, Any]],
    *,
    expected_project_id: str,
    expected_plan_revision: str,
    expected_manifest_revision: str,
    migration_report: Mapping[str, Any],
    preview_files: Mapping[str, bytes],
    preview_registry: Mapping[str, Any],
    delete_paths: Iterable[str] = (),
    usage_context: str = "local_authorized",
) -> dict[str, Any]:
    """Publica ativação universal completa em uma única transação recuperável.

    O plano e o manifesto são apenas lidos. O snapshot é criado antes da
    escrita do store, relatório e previews; por isso o rollback também restaura
    a ausência de um sidecar em projetos realmente legados.
    """

    root = _project(project)
    if not isinstance(definitions, list) or not isinstance(instances, list):
        _error("migration", "definitions e instances devem ser listas.")
    if not isinstance(migration_report, Mapping):
        _error("migration_report", "relatório obrigatório.")
    if not isinstance(preview_files, Mapping) or not isinstance(preview_registry, Mapping):
        _error("migration_previews", "artefatos de preview inválidos.")
    with project_scope.project_lock(root):
        source, plan, manifest = _source_context(root)
        project_id = _current_project_id(root, manifest, create=True)
        if expected_project_id != project_id:
            _error("expected_project_id", "a migração pertence a outro projeto.")
        _assert_expected(expected_plan_revision, source["plan_revision"], "expected_plan_revision")
        _assert_expected(
            expected_manifest_revision, source["manifest_revision"],
            "expected_manifest_revision",
        )
        trusted_catalog, _sources = _prepare_assets(
            root, definitions, instances, [], asset_catalog, None, manifest, usage_context,
        )
        normalized_definitions: list[dict[str, Any]] = []
        definition_map: dict[tuple[str, int], dict[str, Any]] = {}
        try:
            for definition in definitions:
                normalized = card_v2.validate_card_definition_v2(definition, trusted_catalog)
                key = _definition_key(normalized)
                if key in definition_map:
                    _error("migration.definitions", "definition_id/version duplicado.")
                definition_map[key] = normalized
                normalized_definitions.append(normalized)
            normalized_instances: list[dict[str, Any]] = []
            instance_ids: set[str] = set()
            for raw in instances:
                ref = raw.get("definition_ref", {}) if isinstance(raw, Mapping) else {}
                key = (
                    ref.get("definition_id"), ref.get("definition_version"),
                ) if isinstance(ref, Mapping) else (None, None)
                definition = definition_map.get(key)
                if definition is None:
                    _error("migration.instances", "CardInstance referencia definição ausente.")
                instance = card_v2.validate_card_instance_v2(raw, definition, trusted_catalog)
                if instance["instance_id"] in instance_ids:
                    _error("migration.instances", "instance_id duplicado.")
                instance_ids.add(instance["instance_id"])
                _validate_binding(instance, source, plan)
                normalized_instances.append(instance)
        except card_v2.CardStateV2Error as exc:
            raise CardPersistenceV2Error(str(exc)) from exc
        snapshots = [
            card_v2.create_card_snapshot(
                definition_map[(
                    instance["definition_ref"]["definition_id"],
                    instance["definition_ref"]["definition_version"],
                )],
                instance,
                trusted_catalog,
            )
            for instance in normalized_instances
        ]
        candidate = _with_revision({
            "schema_version": STORE_SCHEMA_VERSION,
            "store_id": STORE_ID,
            "project_id": project_id,
            "source": copy.deepcopy(source),
            "definitions": normalized_definitions,
            "instances": normalized_instances,
            "snapshots": snapshots,
        })
        validated, _catalog = _validate_store(
            candidate, project=root, project_id=project_id, current_source=source,
            plan=plan, manifest=manifest, asset_catalog=asset_catalog,
            usage_context=usage_context,
        )
        rollback = project_scope.snapshot_decisions(root, "antes-migracao-card-universal-m99")
        report = copy.deepcopy(dict(migration_report))
        report["rollback_version"] = rollback.name
        report["store_revision"] = validated["revision"]
        # O chamador sela novamente o relatório depois de receber o nome do
        # snapshot seria tarde demais; fazemos aqui o mesmo digest canônico.
        report.pop("revision", None)
        report["revision"] = _digest(report, "migration_report")
        files: dict[str, Any] = {
            STORE_PATH: validated,
            MIGRATION_REPORT_PATH: report,
            "_CONTROLE/CARD_PREVIEWS.json": copy.deepcopy(dict(preview_registry)),
        }
        for relative, content in preview_files.items():
            if not isinstance(relative, str) or not isinstance(content, bytes):
                _error("migration_previews", "preview deve usar path relativo e bytes.")
            _project_file(root, relative, "migration_preview")
            files[relative] = content
        deletes = [relative for relative in dict.fromkeys(delete_paths) if relative not in files]
        for relative in deletes:
            _project_file(root, relative, "migration_delete")
        project_scope.publish_files(root, files, delete=deletes)
        return {
            "project_id": project_id,
            "store_revision": validated["revision"],
            "rollback_version": rollback.name,
            "report": report,
            "instances": copy.deepcopy(normalized_instances),
        }


def save_card_state(
    project: str | Path,
    definition: Any,
    instance: Any,
    asset_catalog: Mapping[str, Mapping[str, Any]],
    *,
    expected_project_id: str,
    expected_plan_revision: str,
    expected_store_revision: str | None,
    base_revision: str | None,
    usage_context: str = "local_authorized",
) -> dict[str, Any]:
    """Valida tudo, cria snapshot e publica somente o sidecar v2."""

    root = _project(project)
    with project_scope.project_lock(root):
        source, plan, manifest = _source_context(root)
        project_id = _current_project_id(root, manifest, create=True)
        if expected_project_id != project_id:
            _error("expected_project_id", "o editor está vinculado a outro projeto.")
        _assert_expected(expected_plan_revision, source["plan_revision"], "expected_plan_revision")
        trusted_catalog, _sources = _prepare_assets(
            root, [definition], [instance], [], asset_catalog, None, manifest, usage_context,
        )
        try:
            normalized_definition = card_v2.validate_card_definition_v2(
                definition, trusted_catalog,
            )
            normalized_instance = card_v2.validate_card_instance_v2(
                instance, normalized_definition, trusted_catalog,
            )
        except card_v2.CardStateV2Error as exc:
            raise CardPersistenceV2Error(str(exc)) from exc
        _validate_binding(normalized_instance, source, plan)
        store_path = root / STORE_PATH
        if store_path.is_file():
            store, _existing_catalog = _validate_store(
                _read_json(store_path, "card_store"), project=root,
                project_id=project_id, current_source=source, plan=plan,
                manifest=manifest, asset_catalog=asset_catalog,
                usage_context=usage_context,
            )
            _assert_expected(expected_store_revision, store["revision"], "expected_store_revision")
        else:
            if expected_store_revision is not None:
                _error("expected_store_revision", "store ainda não existe.")
            store = _empty_store(project_id, source)
        definitions = copy.deepcopy(store["definitions"])
        definition_key = _definition_key(normalized_definition)
        existing_definitions = {
            _definition_key(row): row for row in definitions
        }
        existing_definition = existing_definitions.get(definition_key)
        if existing_definition is not None and existing_definition != normalized_definition:
            _error("card_definition", "definition_id/version já existe com conteúdo diferente.")
        if existing_definition is None:
            definitions.append(normalized_definition)
        instances = copy.deepcopy(store["instances"])
        matches = [
            (index, row) for index, row in enumerate(instances)
            if row["instance_id"] == normalized_instance["instance_id"]
        ]
        if matches:
            index, current = matches[0]
            if base_revision is None:
                _error("base_revision", "obrigatória ao atualizar instância existente.")
            try:
                card_v2.require_current_revision(base_revision, current)
            except card_v2.CardStateV2Error as exc:
                raise CardPersistenceV2Error(str(exc)) from exc
            instances[index] = normalized_instance
        else:
            if base_revision is not None:
                _error("base_revision", "deve ser null na primeira gravação.")
            instances.append(normalized_instance)
        snapshot = card_v2.create_card_snapshot(
            normalized_definition, normalized_instance, trusted_catalog,
        )
        snapshots = copy.deepcopy(store["snapshots"])
        if not any(row["snapshot_digest"] == snapshot["snapshot_digest"] for row in snapshots):
            snapshots.append(snapshot)
        candidate = _with_revision({
            "schema_version": STORE_SCHEMA_VERSION,
            "store_id": STORE_ID,
            "project_id": project_id,
            "source": copy.deepcopy(source),
            "definitions": definitions,
            "instances": instances,
            "snapshots": snapshots,
        })
        validated, _catalog = _validate_store(
            candidate, project=root, project_id=project_id, current_source=source,
            plan=plan, manifest=manifest, asset_catalog=asset_catalog,
            usage_context=usage_context,
        )
        rollback = _publish_store(
            root, validated, "antes-card-state-v2-" + normalized_instance["instance_id"],
        )
        return {
            "project_id": project_id,
            "store_revision": validated["revision"],
            "instance_revision": card_v2.instance_revision(normalized_instance),
            "snapshot_digest": snapshot["snapshot_digest"],
            "rollback_version": rollback.name,
            "instance": copy.deepcopy(normalized_instance),
        }


def _load_validated(
    project: Path,
    asset_catalog: Mapping[str, Mapping[str, Any]],
    *,
    expected_project_id: str,
    usage_context: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Mapping[str, Any]]]:
    source, plan, manifest = _source_context(project)
    project_id = _current_project_id(project, manifest, create=False)
    if expected_project_id != project_id:
        _error("expected_project_id", "o estado aberto pertence a outro projeto.")
    path = project / STORE_PATH
    if not path.is_file():
        _error("card_store", "estado v2 ainda não foi salvo neste projeto.")
    store, catalog = _validate_store(
        _read_json(path, "card_store"), project=project, project_id=project_id,
        current_source=source, plan=plan, manifest=manifest,
        asset_catalog=asset_catalog, usage_context=usage_context,
    )
    return store, source, manifest, catalog


def load_card_state(
    project: str | Path,
    instance_id: str,
    asset_catalog: Mapping[str, Mapping[str, Any]],
    *,
    expected_project_id: str,
    usage_context: str = "local_authorized",
) -> dict[str, Any]:
    """Reabre o estado canônico e rejeita projeto/origem/revisão divergentes."""

    root = _project(project)
    with project_scope.project_lock(root):
        store, source, _manifest, catalog = _load_validated(
            root, asset_catalog, expected_project_id=expected_project_id,
            usage_context=usage_context,
        )
        matches = [row for row in store["instances"] if row["instance_id"] == instance_id]
        if len(matches) != 1:
            _error("instance_id", "instância não encontrada uma vez no projeto.")
        instance = matches[0]
        key = (
            instance["definition_ref"]["definition_id"],
            instance["definition_ref"]["definition_version"],
        )
        definition = next(
            row for row in store["definitions"] if _definition_key(row) == key
        )
        snapshot = card_v2.create_card_snapshot(definition, instance, catalog)
        return {
            "project_id": store["project_id"],
            "store_revision": store["revision"],
            "source": copy.deepcopy(source),
            "definition": copy.deepcopy(definition),
            "instance": copy.deepcopy(instance),
            "instance_revision": card_v2.instance_revision(instance),
            "snapshot": snapshot,
        }


def restore_card_snapshot(
    project: str | Path,
    instance_id: str,
    snapshot_digest: str,
    asset_catalog: Mapping[str, Mapping[str, Any]],
    *,
    expected_project_id: str,
    expected_store_revision: str,
    expected_current_revision: str,
    usage_context: str = "local_authorized",
) -> dict[str, Any]:
    """Restaura snapshot validado e cria rollback do próprio restore."""

    root = _project(project)
    with project_scope.project_lock(root):
        store, source, manifest, catalog = _load_validated(
            root, asset_catalog, expected_project_id=expected_project_id,
            usage_context=usage_context,
        )
        _assert_expected(expected_store_revision, store["revision"], "expected_store_revision")
        snapshots = [
            row for row in store["snapshots"]
            if row["snapshot_digest"] == snapshot_digest
            and row["instance"]["instance_id"] == instance_id
        ]
        if len(snapshots) != 1:
            _error("snapshot_digest", "snapshot não encontrado para a instância.")
        current_matches = [
            (index, row) for index, row in enumerate(store["instances"])
            if row["instance_id"] == instance_id
        ]
        if len(current_matches) != 1:
            _error("instance_id", "instância atual não encontrada uma vez.")
        index, current = current_matches[0]
        try:
            restored = card_v2.rollback_card_instance(
                current, snapshots[0], expected_current_revision=expected_current_revision,
                asset_catalog=catalog,
            )
        except card_v2.CardStateV2Error as exc:
            raise CardPersistenceV2Error(str(exc)) from exc
        _validate_binding(restored, source, _read_json(root / source["plan_path"], "source_plan"))
        instances = copy.deepcopy(store["instances"])
        instances[index] = restored
        candidate = _with_revision({
            "schema_version": STORE_SCHEMA_VERSION,
            "store_id": STORE_ID,
            "project_id": store["project_id"],
            "source": copy.deepcopy(source),
            "definitions": copy.deepcopy(store["definitions"]),
            "instances": instances,
            "snapshots": copy.deepcopy(store["snapshots"]),
        })
        plan = _read_json(root / source["plan_path"], "source_plan")
        validated, _catalog = _validate_store(
            candidate, project=root, project_id=store["project_id"],
            current_source=source, plan=plan, manifest=manifest,
            asset_catalog=asset_catalog, usage_context=usage_context,
        )
        rollback = _publish_store(
            root, validated, "antes-restore-card-state-v2-" + instance_id,
        )
        return {
            "project_id": store["project_id"],
            "store_revision": validated["revision"],
            "instance_revision": card_v2.instance_revision(restored),
            "restored_snapshot_digest": snapshot_digest,
            "rollback_version": rollback.name,
            "instance": copy.deepcopy(restored),
        }


def rollback_card_state(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Nome explícito de rollback para o mesmo restore transacional."""

    return restore_card_snapshot(*args, **kwargs)


def render_persisted_card(
    project: str | Path,
    instance_id: str,
    asset_catalog: Mapping[str, Mapping[str, Any]],
    asset_sources: Mapping[str, str | Path],
    font_root: str | Path,
    *,
    expected_project_id: str,
    usage_context: str,
    output_size: tuple[int, int] | None = None,
):
    """Renderiza diretamente o snapshot canônico reaberto do projeto."""

    root = _project(project)
    with project_scope.project_lock(root):
        loaded = load_card_state(
            root, instance_id, asset_catalog,
            expected_project_id=expected_project_id, usage_context=usage_context,
        )
        _source, _plan, manifest = _source_context(root)
        catalog, sources = _prepare_assets(
            root, [loaded["definition"]], [loaded["instance"]], [],
            asset_catalog, asset_sources, manifest, usage_context,
        )
        instance = loaded["instance"]
        visual = instance.get("state", {}).get("assets", {}).get("visual")
        if (
            instance.get("service_key")
            and isinstance(visual, Mapping)
            and visual.get("scope") == "service_catalog"
            and visual.get("asset_id") == "medallion_" + instance["service_key"]
        ):
            return service_catalog_v2.render_service_card(
                loaded["definition"], instance, catalog, sources, font_root,
                usage_context=usage_context, output_size=output_size, app_root=APP_ROOT,
            )
        from universal_card_renderer import render_universal_card

        return render_universal_card(
            loaded["definition"], instance, catalog, sources, font_root,
            output_size=output_size, usage_context=usage_context,
        )
