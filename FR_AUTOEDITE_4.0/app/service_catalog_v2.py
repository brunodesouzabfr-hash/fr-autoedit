"""Catálogo produtivo M9.4 dos 13 medalhões SERVICE.

Os PNGs continuam ``publicavel=false`` e ``installed_requires_review``. A
aprovação M9.4 autoriza somente render local ou produção interna, sempre com
aviso de revisão visual. Publicação/distribuição externa permanece bloqueada.

O módulo não cria fallback, não altera o manifesto legado e nunca aceita path
fornecido por CardInstance ou pelo navegador. O contrato versionado fixa a
política e o mapeamento; paths, hashes e estado editorial usados em runtime vêm
do manifesto versionado, depois da validação cruzada entre as duas fontes.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Mapping

from PIL import Image

import card_state_v2 as card_v2


APP_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = APP_ROOT / "contracts" / "m9" / "service_catalog_v1.json"
CATALOG_ID = "fr-service-medallions/1"
SCHEMA_VERSION = 1
ASSET_SCOPE = "service_catalog"
ALLOWED_CONTEXTS = ("local_authorized", "internal_production")
STATUS = "installed_requires_review"
VISUAL_POLICY = {
    "shape": "circle",
    "crop": "1:1",
    "default_size": 389,
    "zoom_range": [1, 3],
    "focal_range": [0, 100],
}
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_TOP_FIELDS = frozenset({
    "schema_version", "catalog_id", "source_manifest", "source_service_catalog",
    "asset_scope", "usage_policy", "visual_policy", "services",
})
_POLICY_FIELDS = frozenset({
    "allowed_contexts", "external_distribution_allowed", "license_status",
    "provenance_status", "fallback_allowed", "publicavel_must_remain_false",
    "status_must_remain", "visual_review_required",
})
_SERVICE_FIELDS = frozenset({
    "service_key", "asset_id", "scope", "original_path", "original_sha256",
    "normalized_path", "sha256", "dimensions", "status", "publicavel",
    "visual_review_required", "opaque_background_preserved",
})


class ServiceCatalogV2Error(ValueError):
    """Falha fechada de identidade, integridade ou contexto SERVICE."""


@dataclass(frozen=True)
class ResolvedServiceAsset:
    service_key: str
    asset_id: str
    asset_ref: dict[str, str]
    asset_catalog_entry: dict[str, Any]
    source_path: Path
    original_path: Path
    review: dict[str, Any]
    warnings: tuple[str, ...]


def _error(label: str, message: str) -> None:
    raise ServiceCatalogV2Error(f"{label}: {message}")


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


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ServiceCatalogV2Error(f"{label}: arquivo ausente ou inválido: {path}.") from exc
    if not isinstance(value, dict):
        _error(label, "esperado objeto JSON.")
    return value


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        _error(label, "esperado SHA-256 hexadecimal minúsculo.")
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise ServiceCatalogV2Error(f"asset ausente ou ilegível: {path}.") from exc
    return digest.hexdigest()


def _confined(app_root: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value:
        _error(label, "path relativo obrigatório.")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        _error(label, "path deve permanecer dentro da instalação.")
    root = app_root.resolve()
    target = (root / relative).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ServiceCatalogV2Error(f"{label}: path escapa da instalação.") from exc
    return target


def _manifest_entry(manifest: Mapping[str, Any], asset_id: str, label: str) -> Mapping[str, Any]:
    assets = manifest.get("assets")
    if not isinstance(assets, Mapping):
        _error("source_manifest.assets", "esperado objeto.")
    row = assets.get(asset_id)
    if not isinstance(row, Mapping):
        _error(label, f"asset inexistente no manifesto: {asset_id}.")
    return row


def _verify_source(
    app_root: Path, relative: str, expected_hash: str, label: str,
    dimensions: tuple[int, int] | None = None,
) -> Path:
    source = _confined(app_root, relative, label + ".path")
    if not source.is_file():
        _error(label, f"asset ausente: {relative}.")
    received = _sha256_file(source)
    if received != expected_hash:
        _error(label, f"hash divergente para {relative}.")
    if dimensions is not None:
        try:
            with Image.open(source) as opened:
                opened.load()
                received_dimensions = opened.size
        except OSError as exc:
            raise ServiceCatalogV2Error(f"{label}: imagem inválida: {relative}.") from exc
        if received_dimensions != dimensions:
            _error(
                label,
                f"dimensões divergentes: esperado {dimensions[0]}x{dimensions[1]}.",
            )
    return source


def _validate_usage_policy(value: Any) -> dict[str, Any]:
    row = _object(value, label="service_catalog.usage_policy", allowed=_POLICY_FIELDS)
    if row["allowed_contexts"] != list(ALLOWED_CONTEXTS):
        _error("service_catalog.usage_policy.allowed_contexts", "contextos autorizados divergentes.")
    required_values = {
        "external_distribution_allowed": False,
        "license_status": "pending",
        "provenance_status": "pending",
        "fallback_allowed": False,
        "publicavel_must_remain_false": True,
        "status_must_remain": STATUS,
        "visual_review_required": True,
    }
    for name, expected in required_values.items():
        if row[name] != expected:
            _error(f"service_catalog.usage_policy.{name}", f"esperado {expected!r}.")
    return copy.deepcopy(row)


def _validate_service_row(
    value: Any, index: int, manifest: Mapping[str, Any], app_root: Path,
    *, verify_files: bool,
) -> dict[str, Any]:
    label = f"service_catalog.services[{index}]"
    row = _object(value, label=label, allowed=_SERVICE_FIELDS)
    service_key = row["service_key"]
    if not isinstance(service_key, str) or service_key not in card_v2.SERVICE_KEYS:
        _error(label + ".service_key", "service_key desconhecida.")
    expected_asset_id = f"medallion_{service_key}"
    if row["asset_id"] != expected_asset_id:
        _error(label + ".asset_id", f"esperado {expected_asset_id}.")
    if row["scope"] != ASSET_SCOPE:
        _error(label + ".scope", f"esperado {ASSET_SCOPE}.")
    if row["status"] != STATUS:
        _error(label + ".status", f"esperado {STATUS}.")
    if row["publicavel"] is not False:
        _error(label + ".publicavel", "deve permanecer false.")
    if row["visual_review_required"] is not True:
        _error(label + ".visual_review_required", "deve permanecer true.")
    if not isinstance(row["opaque_background_preserved"], bool):
        _error(label + ".opaque_background_preserved", "esperado booleano.")
    if row["dimensions"] != [2048, 2048]:
        _error(label + ".dimensions", "medalhão normalizado deve medir 2048x2048.")
    original_hash = _sha256(row["original_sha256"], label + ".original_sha256")
    normalized_hash = _sha256(row["sha256"], label + ".sha256")
    original_path = _confined(app_root, row["original_path"], label + ".original_path")
    normalized_path = _confined(app_root, row["normalized_path"], label + ".normalized_path")
    source = _manifest_entry(manifest, expected_asset_id, label + ".asset_id")
    normalized = source.get("normalized")
    if not isinstance(normalized, Mapping):
        _error("source_manifest.assets." + expected_asset_id + ".normalized", "esperado objeto.")
    comparisons = {
        "asset_id": source.get("asset_id"),
        "service_key": source.get("servico"),
        "original_path": source.get("path"),
        "original_sha256": source.get("sha256"),
        "normalized_path": source.get("normalized_path"),
        "sha256": normalized.get("sha256"),
        "dimensions": normalized.get("dimensions"),
        "status": source.get("status"),
        "publicavel": source.get("publicavel"),
        "visual_review_required": normalized.get("visual_review_required"),
        "opaque_background_preserved": normalized.get("opaque_background_preserved"),
    }
    expected = {
        "asset_id": expected_asset_id,
        "service_key": service_key,
        "original_path": row["original_path"],
        "original_sha256": original_hash,
        "normalized_path": row["normalized_path"],
        "sha256": normalized_hash,
        "dimensions": row["dimensions"],
        "status": STATUS,
        "publicavel": False,
        "visual_review_required": True,
        "opaque_background_preserved": row["opaque_background_preserved"],
    }
    for name, expected_value in expected.items():
        if comparisons[name] != expected_value:
            _error(label + "." + name, "diverge do manifesto de origem.")
    if source.get("caminho") != row["original_path"]:
        _error(label + ".original_path", "diverge de caminho no manifesto de origem.")
    if normalized.get("original_sha256") != original_hash:
        _error(label + ".original_sha256", "diverge do hash de linhagem normalizada.")
    if verify_files:
        _verify_source(app_root, row["original_path"], original_hash, label + ".original")
        _verify_source(
            app_root, row["normalized_path"], normalized_hash, label + ".normalized",
            dimensions=(2048, 2048),
        )
    if original_path == normalized_path:
        _error(label + ".normalized_path", "derivado não pode substituir o original.")
    result = copy.deepcopy(row)
    return result


def validate_service_catalog(
    value: Any,
    manifest: Mapping[str, Any],
    *,
    app_root: str | Path = APP_ROOT,
    verify_files: bool = False,
) -> dict[str, Any]:
    """Valida o registro contra contrato, manifesto e, opcionalmente, bytes."""

    root = Path(app_root)
    row = _object(value, label="service_catalog", allowed=_TOP_FIELDS)
    if row["schema_version"] != SCHEMA_VERSION:
        _error("service_catalog.schema_version", f"esperado {SCHEMA_VERSION}.")
    if row["catalog_id"] != CATALOG_ID:
        _error("service_catalog.catalog_id", f"esperado {CATALOG_ID}.")
    if row["source_manifest"] != "assets/style_packs/fr_quiet_engineering_atelier_v2/manifest.json":
        _error("service_catalog.source_manifest", "manifesto de origem divergente.")
    if row["source_service_catalog"] != "templates/service_catalog.json":
        _error("service_catalog.source_service_catalog", "catálogo semântico divergente.")
    if row["asset_scope"] != ASSET_SCOPE:
        _error("service_catalog.asset_scope", f"esperado {ASSET_SCOPE}.")
    policy = _validate_usage_policy(row["usage_policy"])
    if row["visual_policy"] != VISUAL_POLICY:
        _error("service_catalog.visual_policy", "política circle/crop 1:1 divergente.")
    services = row["services"]
    if not isinstance(services, list) or len(services) != len(card_v2.SERVICE_KEYS):
        _error("service_catalog.services", "esperados exatamente 13 serviços.")
    normalized = [
        _validate_service_row(item, index, manifest, root, verify_files=verify_files)
        for index, item in enumerate(services)
    ]
    keys = [item["service_key"] for item in normalized]
    asset_ids = [item["asset_id"] for item in normalized]
    if len(set(keys)) != len(keys):
        _error("service_catalog.services", "service_key duplicada.")
    if len(set(asset_ids)) != len(asset_ids):
        _error("service_catalog.services", "asset_id duplicado.")
    if set(keys) != set(card_v2.SERVICE_KEYS):
        _error("service_catalog.services", "conjunto de service_key diverge do contrato M9.0.")
    semantic_path = _confined(root, row["source_service_catalog"], "source_service_catalog")
    semantic = _load_json(semantic_path, "source_service_catalog")
    semantic_rows = semantic.get("services")
    if not isinstance(semantic_rows, list):
        _error("source_service_catalog.services", "esperada lista.")
    semantic_keys = {
        item.get("key") for item in semantic_rows if isinstance(item, Mapping)
    }
    if semantic_keys != set(keys):
        _error("service_catalog.services", "diverge do catálogo semântico versionado.")
    result = copy.deepcopy(row)
    result["usage_policy"] = policy
    result["services"] = normalized
    return result


def load_service_catalog(
    *, app_root: str | Path = APP_ROOT, verify_files: bool = False,
) -> dict[str, Any]:
    root = Path(app_root)
    contract = _load_json(
        _confined(root, "contracts/m9/service_catalog_v1.json", "service_catalog.contract"),
        "service_catalog.contract",
    )
    manifest = _load_json(
        _confined(root, contract.get("source_manifest"), "service_catalog.source_manifest"),
        "service_catalog.source_manifest",
    )
    return validate_service_catalog(
        contract, manifest, app_root=root, verify_files=verify_files,
    )


def _renderer_entry(
    row: Mapping[str, Any], source: Mapping[str, Any], policy: Mapping[str, Any],
    source_manifest: str,
) -> dict[str, Any]:
    normalized = source["normalized"]
    return {
        # Identidade, status, path selecionado e hash vêm do manifesto depois
        # de ele ter sido confrontado com o registro versionado M9.4.
        "asset_id": source["asset_id"],
        "scope": row["scope"],
        "sha256": normalized["sha256"],
        "service_key": source["servico"],
        "status": source["status"],
        "publicavel": source["publicavel"],
        "visual_review_required": normalized["visual_review_required"],
        "opaque_background_preserved": normalized["opaque_background_preserved"],
        "resolution_authority": "source_manifest",
        "source_manifest": source_manifest,
        "usage_policy": copy.deepcopy(policy),
    }


def validate_renderer_service_asset(
    entry: Mapping[str, Any], asset_id: str, usage_context: Any,
) -> dict[str, Any]:
    """Gate chamado pelo próprio renderer para impedir bypass do resolver."""

    if not isinstance(entry, Mapping):
        _error("renderer.service_asset", "entrada de catálogo ausente.")
    if entry.get("asset_id") != asset_id:
        _error("renderer.service_asset.asset_id", "ID diverge da chave do catálogo.")
    if entry.get("scope") != ASSET_SCOPE:
        _error("renderer.service_asset.scope", f"esperado {ASSET_SCOPE}.")
    if entry.get("resolution_authority") != "source_manifest":
        _error(
            "renderer.service_asset.resolution_authority",
            "asset SERVICE exige resolução manifest-driven.",
        )
    if entry.get("source_manifest") != (
        "assets/style_packs/fr_quiet_engineering_atelier_v2/manifest.json"
    ):
        _error("renderer.service_asset.source_manifest", "manifesto de origem divergente.")
    service_key = entry.get("service_key")
    if not isinstance(service_key, str) or service_key not in card_v2.SERVICE_KEYS:
        _error("renderer.service_asset.service_key", "service_key desconhecida.")
    if asset_id != f"medallion_{service_key}":
        _error("renderer.service_asset.asset_id", "não corresponde à service_key.")
    _sha256(entry.get("sha256"), "renderer.service_asset.sha256")
    if entry.get("status") != STATUS:
        _error("renderer.service_asset.status", f"esperado {STATUS}.")
    if entry.get("publicavel") is not False:
        _error("renderer.service_asset.publicavel", "deve permanecer false.")
    if entry.get("visual_review_required") is not True:
        _error("renderer.service_asset.visual_review_required", "deve permanecer true.")
    if not isinstance(entry.get("opaque_background_preserved"), bool):
        _error("renderer.service_asset.opaque_background_preserved", "esperado booleano.")
    policy = _validate_usage_policy(entry.get("usage_policy"))
    if not isinstance(usage_context, str) or usage_context not in policy["allowed_contexts"]:
        _error(
            "renderer.usage_context",
            "asset SERVICE bloqueado fora de local_authorized/internal_production.",
        )
    warning_codes = ["visual_review_required", "external_distribution_blocked"]
    if entry["opaque_background_preserved"]:
        warning_codes.append("opaque_background_preserved")
    return {
        "service_key": service_key,
        "asset_id": asset_id,
        "scope": ASSET_SCOPE,
        "sha256": entry["sha256"],
        "usage_context": usage_context,
        "status": STATUS,
        "publicavel": False,
        "visual_review_required": True,
        "opaque_background_preserved": entry["opaque_background_preserved"],
        "external_distribution_allowed": False,
        "license_status": policy["license_status"],
        "provenance_status": policy["provenance_status"],
        "resolution_authority": "source_manifest",
        "source_manifest": entry["source_manifest"],
        "warning_codes": warning_codes,
    }


def resolve_service_asset(
    service_key: Any,
    usage_context: Any,
    *,
    app_root: str | Path = APP_ROOT,
    catalog: Mapping[str, Any] | None = None,
    manifest: Mapping[str, Any] | None = None,
) -> ResolvedServiceAsset:
    """Resolve um medalhão real, sem fallback e somente em contexto autorizado."""

    root = Path(app_root)
    if not isinstance(service_key, str) or service_key not in card_v2.SERVICE_KEYS:
        _error("service_key", "serviço desconhecido.")
    if catalog is None:
        catalog = _load_json(
            _confined(root, "contracts/m9/service_catalog_v1.json", "service_catalog.contract"),
            "service_catalog.contract",
        )
    if manifest is None:
        source_manifest = catalog.get("source_manifest") if isinstance(catalog, Mapping) else None
        manifest = _load_json(
            _confined(root, source_manifest, "service_catalog.source_manifest"),
            "service_catalog.source_manifest",
        )
    validated = validate_service_catalog(catalog, manifest, app_root=root, verify_files=False)
    rows = {row["service_key"]: row for row in validated["services"]}
    row = rows[service_key]
    manifest_row = _manifest_entry(manifest, row["asset_id"], "service." + service_key)
    normalized = manifest_row["normalized"]
    entry = _renderer_entry(
        row, manifest_row, validated["usage_policy"], validated["source_manifest"],
    )
    # Contexto externo falha antes de qualquer leitura dos bytes locais.
    review = validate_renderer_service_asset(entry, manifest_row["asset_id"], usage_context)
    source = _verify_source(
        root,
        manifest_row["normalized_path"],
        normalized["sha256"],
        f"service.{service_key}.normalized",
        dimensions=tuple(normalized["dimensions"]),
    )
    original = _verify_source(
        root,
        manifest_row["path"],
        manifest_row["sha256"],
        f"service.{service_key}.original",
    )
    warnings = [
        f"SERVICE {service_key}: revisão visual obrigatória; publicavel=false; "
        f"uso restrito a {usage_context}.",
    ]
    if normalized["opaque_background_preserved"]:
        warnings.append(
            f"SERVICE {service_key}: fundo opaco preservado; não remover nem mascarar sem nova revisão."
        )
    return ResolvedServiceAsset(
        service_key=service_key,
        asset_id=manifest_row["asset_id"],
        asset_ref={
            "scope": ASSET_SCOPE,
            "asset_id": manifest_row["asset_id"],
            "sha256": normalized["sha256"],
        },
        asset_catalog_entry=entry,
        source_path=source,
        original_path=original,
        review=review,
        warnings=tuple(warnings),
    )


def bind_service_instance(
    instance: Any, resolved: ResolvedServiceAsset,
) -> dict[str, Any]:
    """Aplica somente o AssetRef SERVICE e recalcula o digest, sem persistir."""

    if not isinstance(instance, dict):
        _error("card_instance", "esperado objeto.")
    if instance.get("schema_version") != 2:
        _error("card_instance.schema_version", "CardInstance SERVICE deve usar v2.")
    if instance.get("service_key") != resolved.service_key:
        _error("card_instance.service_key", "não corresponde ao serviço resolvido.")
    state = instance.get("state")
    assets = state.get("assets") if isinstance(state, dict) else None
    if not isinstance(assets, dict):
        _error("card_instance.state.assets", "esperado objeto.")
    if assets.get("visualShape") != VISUAL_POLICY["shape"]:
        _error("card_instance.state.assets.visualShape", "SERVICE exige círculo perfeito.")
    for name in ("visualZoom", "visualFocalX", "visualFocalY", "visualSize"):
        value = assets.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            _error("card_instance.state.assets." + name, "esperado número finito.")
    if not VISUAL_POLICY["zoom_range"][0] <= float(assets["visualZoom"]) <= VISUAL_POLICY["zoom_range"][1]:
        _error("card_instance.state.assets.visualZoom", "zoom fora do contrato SERVICE.")
    for name in ("visualFocalX", "visualFocalY"):
        if not VISUAL_POLICY["focal_range"][0] <= float(assets[name]) <= VISUAL_POLICY["focal_range"][1]:
            _error("card_instance.state.assets." + name, "focal point fora do contrato SERVICE.")
    result = copy.deepcopy(instance)
    result["state"]["assets"]["visual"] = copy.deepcopy(resolved.asset_ref)
    result["state_digest"] = card_v2.renderable_state_digest(
        result["definition_ref"], result["state"], result["service_key"],
    )
    return result


def render_service_card(
    definition: Any,
    instance: Any,
    asset_catalog: Mapping[str, Mapping[str, Any]],
    asset_sources: Mapping[str, str | Path],
    font_root: str | Path,
    *,
    usage_context: str,
    output_size: tuple[int, int] | None = None,
    app_root: str | Path = APP_ROOT,
    catalog: Mapping[str, Any] | None = None,
    manifest: Mapping[str, Any] | None = None,
):
    """Resolve, vincula e renderiza SERVICE pelo ``fr-universal-card``."""

    service_key = instance.get("service_key") if isinstance(instance, dict) else None
    resolved = resolve_service_asset(
        service_key, usage_context, app_root=app_root, catalog=catalog, manifest=manifest,
    )
    prepared = bind_service_instance(instance, resolved)
    merged_catalog = dict(asset_catalog)
    existing = merged_catalog.get(resolved.asset_id)
    if existing is not None:
        if not isinstance(existing, Mapping) or (
            existing.get("scope") != resolved.asset_catalog_entry["scope"]
            or existing.get("sha256") != resolved.asset_catalog_entry["sha256"]
        ):
            _error(
                "asset_catalog." + resolved.asset_id,
                "binding existente diverge do catálogo SERVICE.",
            )
    merged_catalog[resolved.asset_id] = resolved.asset_catalog_entry
    merged_sources = dict(asset_sources)
    existing_source = merged_sources.get(resolved.asset_id)
    if existing_source is not None:
        if not isinstance(existing_source, (str, Path)) or (
            Path(existing_source).resolve() != resolved.source_path.resolve()
        ):
            _error(
                "asset_sources." + resolved.asset_id,
                "path existente diverge do catálogo SERVICE.",
            )
    merged_sources[resolved.asset_id] = resolved.source_path
    # Import local evita ciclo: o renderer chama o gate de política deste módulo.
    from universal_card_renderer import render_universal_card

    return render_universal_card(
        definition,
        prepared,
        merged_catalog,
        merged_sources,
        font_root,
        output_size=output_size,
        usage_context=usage_context,
    )
