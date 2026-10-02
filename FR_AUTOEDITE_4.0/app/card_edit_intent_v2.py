"""CARD_EDIT_INTENT v2 declarativo para o Card Editor Universal.

O provider recebe somente um snapshot de dados. Ele não recebe paths, objetos
graváveis ou callbacks. A intenção é validada contra o mesmo CardState v2 usado
pela edição manual; revisar nunca grava e aplicar exige confirmação e revisões
atuais antes de delegar a escrita transacional à persistência M9.5.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Callable, Mapping

import card_persistence_v2 as persistence
import card_state_v2 as card_v2


SCHEMA_VERSION = 2
INTENT_KIND = "CARD_EDIT_INTENT"
ORIGIN = "ai_assisted"
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}")
_SHA_RE = re.compile(r"[0-9a-f]{64}")
_TOP_FIELDS = frozenset({
    "schema_version", "kind", "intent_id", "origin", "project_id",
    "target_id", "input_mode", "base_plan_revision", "base_store_revision",
    "base_instance_revision", "operations", "provenance",
})
_OP_FIELDS = frozenset({"operation_id", "op", "target_id", "changes"})
_PROVENANCE_FIELDS = frozenset({"provider", "model", "request_id"})
_FIELD_CHANGES = frozenset({
    "text", "x", "y", "w", "h", "font", "size", "weight", "lineHeight",
    "spacing", "align", "color", "effect", "visible", "noWrap",
    "shadowEnabled", "shadowX", "shadowY", "shadowBlur", "shadowOpacity",
})
_LINE_CHANGES = frozenset({
    "x1", "y1", "x2", "y2", "width", "color", "visible", "opacity", "fade",
})
_ASSET_CHANGES = frozenset({
    "background", "logo", "visual", "visualOpacity", "visualShape",
    "visualSize", "visualZoom", "visualFocalX", "visualFocalY",
})
_LAYER_CHANGES = frozenset({"background", "grid", "text", "logo"})
_GRID_CHANGES = frozenset({"opacity"})
_OP_ALLOWED = {
    "set_field": _FIELD_CHANGES,
    "set_line": _LINE_CHANGES,
    "set_assets": _ASSET_CHANGES,
    "set_layers": _LAYER_CHANGES,
    "set_grid_style": _GRID_CHANGES,
}
_TARGETED_OPS = frozenset({"set_field", "set_line"})


class CardEditIntentV2Error(ValueError):
    """Intenção inválida, obsoleta ou não confirmada."""

    def __init__(self, code: str, message: str, *, field: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.field = field

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "field": self.field, "message": str(self)}


def _error(code: str, message: str, field: str = "") -> None:
    raise CardEditIntentV2Error(code, message, field=field)


def _object(
    value: Any, *, label: str, allowed: frozenset[str], required: frozenset[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        _error("invalid_type", f"{label}: esperado objeto.", label)
    unknown = sorted(set(value) - allowed)
    if unknown:
        _error("unknown_field", f"{label}: campos desconhecidos: {', '.join(unknown)}.", label)
    missing = sorted((required or allowed) - set(value))
    if missing:
        _error("required", f"{label}: campos obrigatórios ausentes: {', '.join(missing)}.", label)
    return value


def _stable_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value) or ".." in value or "//" in value:
        _error("invalid_id", f"{label}: ID estável inválido.", label)
    return value


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        _error("invalid_revision", f"{label}: esperado SHA-256 hexadecimal minúsculo.", label)
    return value


def _text(value: Any, label: str, *, maximum: int = 300) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum or "\x00" in value:
        _error("invalid_text", f"{label}: texto obrigatório de até {maximum} caracteres.", label)
    return value


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CardEditIntentV2Error("invalid_json", "CARD_EDIT_INTENT não é JSON canônico.") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _font_families() -> list[str]:
    path = Path(__file__).resolve().parents[1] / "contracts" / "m9" / "font_sources_v1.json"
    try:
        contract = json.loads(path.read_text(encoding="utf-8"))
        result = sorted({row["family"] for row in contract["fonts"]})
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise CardEditIntentV2Error("contract_unavailable", "Contrato de fontes M9.0 indisponível.") from exc
    return result


def _public_asset_catalog(catalog: Mapping[str, Mapping[str, Any]]) -> list[dict[str, str]]:
    if not isinstance(catalog, Mapping):
        _error("invalid_asset_catalog", "asset_catalog: esperado mapa confiável.", "asset_catalog")
    result: list[dict[str, str]] = []
    for asset_id in sorted(catalog):
        row = catalog[asset_id]
        if not isinstance(row, Mapping):
            _error("invalid_asset_catalog", f"asset_catalog.{asset_id}: esperado objeto.", "asset_catalog")
        scope = row.get("scope")
        sha256 = row.get("sha256")
        if row.get("asset_id") != asset_id or not isinstance(scope, str) or not _SHA_RE.fullmatch(str(sha256)):
            _error("invalid_asset_catalog", f"asset_catalog.{asset_id}: identidade inválida.", "asset_catalog")
        result.append({"asset_id": asset_id, "scope": scope, "sha256": str(sha256)})
    return result


def build_provider_request(
    project: str | Path,
    instance_id: str,
    asset_catalog: Mapping[str, Mapping[str, Any]],
    *,
    expected_project_id: str,
    task: str,
    usage_context: str = "local_authorized",
) -> dict[str, Any]:
    """Monta snapshot somente-leitura, sem qualquer path ou callback."""

    loaded = persistence.load_card_state(
        project, instance_id, asset_catalog,
        expected_project_id=expected_project_id, usage_context=usage_context,
    )
    source = loaded["source"]
    return {
        "request_version": 2,
        "required_output": "CARD_EDIT_INTENT_V2",
        "task": _text(task, "task", maximum=1200),
        "project_id": loaded["project_id"],
        "target_id": loaded["instance"]["instance_id"],
        "input_mode": source["input_mode"],
        "base_plan_revision": source["plan_revision"],
        "base_store_revision": loaded["store_revision"],
        "base_instance_revision": loaded["instance_revision"],
        "read_only_snapshot": copy.deepcopy(loaded["snapshot"]),
        "asset_catalog": _public_asset_catalog(asset_catalog),
        "capabilities": {
            "operations": {
                name: sorted(properties) for name, properties in _OP_ALLOWED.items()
            },
            "field_ids": list(card_v2.FIELD_IDS),
            "line_ids": list(card_v2.LINE_IDS),
            "fonts_renderable": _font_families(),
            "formats": ["9:16"],
            "unsupported": [
                "timeline", "placement", "duration", "animation", "service_key",
                "filesystem", "paths", "data_urls", "callbacks", "html",
            ],
        },
    }


def request_provider_intent(
    provider: Callable[[dict[str, Any]], Any], request: Mapping[str, Any],
) -> dict[str, Any]:
    """Invoca provider somente com cópia isolada do snapshot de dados."""

    if not callable(provider):
        _error("invalid_provider", "Provider precisa devolver CARD_EDIT_INTENT_V2.", "provider")
    result = provider(copy.deepcopy(dict(request)))
    if not isinstance(result, dict):
        _error("invalid_provider_response", "Provider não devolveu objeto JSON.", "provider")
    return copy.deepcopy(result)


def _validate_provenance(value: Any) -> dict[str, str]:
    row = _object(
        value, label="provenance", allowed=_PROVENANCE_FIELDS, required=_PROVENANCE_FIELDS,
    )
    return {name: _text(row[name], "provenance." + name) for name in sorted(_PROVENANCE_FIELDS)}


def _validate_operations(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value or len(value) > 100:
        _error("invalid_operations", "operations: use lista com 1 a 100 operações.", "operations")
    normalized: list[dict[str, Any]] = []
    operation_ids: set[str] = set()
    touched: set[tuple[str, str, str]] = set()
    renderable_fonts = set(_font_families())
    for index, raw in enumerate(value):
        label = f"operations[{index}]"
        row = _object(raw, label=label, allowed=_OP_FIELDS, required=frozenset({"operation_id", "op", "changes"}))
        operation_id = _stable_id(row["operation_id"], label + ".operation_id")
        if operation_id in operation_ids:
            _error("duplicate_id", f"{label}.operation_id: ID duplicado.", label + ".operation_id")
        operation_ids.add(operation_id)
        op = row["op"]
        if op not in _OP_ALLOWED:
            _error("unsupported_operation", f"{label}.op: operação não suportada.", label + ".op")
        target_id = row.get("target_id")
        if op in _TARGETED_OPS:
            target_id = _stable_id(target_id, label + ".target_id")
            allowed_targets = card_v2.FIELD_IDS if op == "set_field" else card_v2.LINE_IDS
            if target_id not in allowed_targets:
                _error("unknown_target", f"{label}.target_id: ID desconhecido.", label + ".target_id")
        elif "target_id" in row:
            _error("unknown_field", f"{label}.target_id: não se aplica a {op}.", label + ".target_id")
        changes = row["changes"]
        if not isinstance(changes, dict) or not changes:
            _error("empty_changes", f"{label}.changes: informe ao menos uma propriedade.", label + ".changes")
        unknown = sorted(set(changes) - _OP_ALLOWED[op])
        if unknown:
            _error(
                "unsupported_field",
                f"{label}.changes: propriedades não suportadas: {', '.join(unknown)}.",
                label + ".changes",
            )
        if op == "set_field" and "font" in changes and changes["font"] not in renderable_fonts:
            _error(
                "unrenderable_font",
                f"{label}.changes.font: fonte não registrada no renderer universal.",
                label + ".changes.font",
            )
        scope = target_id or op
        for property_name in changes:
            key = (op, scope, property_name)
            if key in touched:
                _error("conflicting_change", f"{label}: propriedade alterada mais de uma vez.", label)
            touched.add(key)
        normalized.append({
            "operation_id": operation_id,
            "op": op,
            **({"target_id": target_id} if target_id is not None else {}),
            "changes": copy.deepcopy(changes),
        })
    return normalized


def _validate_intent(value: Any, loaded: Mapping[str, Any]) -> dict[str, Any]:
    row = _object(value, label="CARD_EDIT_INTENT_V2", allowed=_TOP_FIELDS, required=_TOP_FIELDS)
    if row["schema_version"] != SCHEMA_VERSION or isinstance(row["schema_version"], bool):
        _error("unsupported_version", "schema_version: versão suportada é 2.", "schema_version")
    if row["kind"] != INTENT_KIND:
        _error("invalid_kind", f"kind: esperado {INTENT_KIND}.", "kind")
    if row["origin"] != ORIGIN:
        _error("invalid_origin", f"origin: esperado {ORIGIN}.", "origin")
    intent_id = _stable_id(row["intent_id"], "intent_id")
    project_id = _stable_id(row["project_id"], "project_id")
    target_id = _stable_id(row["target_id"], "target_id")
    source = loaded["source"]
    expected = {
        "project_id": loaded["project_id"],
        "target_id": loaded["instance"]["instance_id"],
        "input_mode": source["input_mode"],
        "base_plan_revision": source["plan_revision"],
        "base_store_revision": loaded["store_revision"],
        "base_instance_revision": loaded["instance_revision"],
    }
    received = {
        "project_id": project_id,
        "target_id": target_id,
        "input_mode": row["input_mode"],
        "base_plan_revision": _sha(row["base_plan_revision"], "base_plan_revision"),
        "base_store_revision": _sha(row["base_store_revision"], "base_store_revision"),
        "base_instance_revision": _sha(row["base_instance_revision"], "base_instance_revision"),
    }
    for name, expected_value in expected.items():
        if received[name] != expected_value:
            _error("stale_revision", f"{name}: estado atual diverge; gere nova intenção.", name)
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": INTENT_KIND,
        "intent_id": intent_id,
        "origin": ORIGIN,
        **received,
        "operations": _validate_operations(row["operations"]),
        "provenance": _validate_provenance(row["provenance"]),
    }


def _apply_operations(instance: Mapping[str, Any], operations: list[dict[str, Any]]) -> dict[str, Any]:
    candidate = copy.deepcopy(instance)
    state = candidate["state"]
    fields = {row["id"]: row for row in state["fields"]}
    lines = {row["id"]: row for row in state["lines"]}
    for operation in operations:
        op = operation["op"]
        changes = copy.deepcopy(operation["changes"])
        if op == "set_field":
            fields[operation["target_id"]].update(changes)
        elif op == "set_line":
            lines[operation["target_id"]].update(changes)
        elif op == "set_assets":
            state["assets"].update(changes)
        elif op == "set_layers":
            state["layers"].update(changes)
        elif op == "set_grid_style":
            state["gridStyle"].update(changes)
    candidate["edit_origin"] = ORIGIN
    return candidate


def _diff(before: Any, after: Any, path: str = "") -> list[dict[str, Any]]:
    if before == after:
        return []
    if isinstance(before, dict) and isinstance(after, dict):
        result: list[dict[str, Any]] = []
        for key in sorted(set(before) | set(after)):
            child = f"{path}.{key}" if path else key
            result.extend(_diff(before.get(key), after.get(key), child))
        return result
    if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        result = []
        for index, (old, new) in enumerate(zip(before, after)):
            result.extend(_diff(old, new, f"{path}[{index}]"))
        return result
    return [{"path": path, "before": copy.deepcopy(before), "after": copy.deepcopy(after)}]


def review_card_edit_intent(
    project: str | Path,
    intent: Any,
    asset_catalog: Mapping[str, Mapping[str, Any]],
    *,
    expected_project_id: str,
    usage_context: str = "local_authorized",
) -> dict[str, Any]:
    """Valida, calcula candidato/diff e não grava nenhum arquivo."""

    target_id = intent.get("target_id") if isinstance(intent, dict) else ""
    loaded = persistence.load_card_state(
        project, str(target_id), asset_catalog,
        expected_project_id=expected_project_id, usage_context=usage_context,
    )
    normalized = _validate_intent(intent, loaded)
    candidate = _apply_operations(loaded["instance"], normalized["operations"])
    service_key = candidate.get("service_key")
    if service_key is not None:
        assets = candidate["state"]["assets"]
        visual = assets.get("visual")
        if (
            not isinstance(visual, dict)
            or visual.get("scope") != "service_catalog"
            or visual.get("asset_id") != f"medallion_{service_key}"
            or assets.get("visualShape") != "circle"
        ):
            _error(
                "service_contract_rejected",
                "SERVICE exige o medalhão da service_key e círculo perfeito; não há fallback.",
                "operations",
            )
    try:
        candidate["state"] = card_v2.validate_card_state_v2(
            candidate["state"], asset_catalog, label="card_instance.state",
        )
        candidate["state_digest"] = card_v2.renderable_state_digest(
            candidate["definition_ref"], candidate["state"], candidate.get("service_key"),
        )
        validated = card_v2.validate_card_instance_v2(
            candidate, loaded["definition"], asset_catalog,
        )
        candidate_snapshot = card_v2.create_card_snapshot(
            loaded["definition"], validated, asset_catalog,
        )
    except card_v2.CardStateV2Error as exc:
        raise CardEditIntentV2Error("contract_rejected", str(exc), field="operations") from exc
    changes = _diff(loaded["instance"], validated)
    if not changes:
        _error("no_effect", "A intenção validada não produz mudança.", "operations")
    basis = {
        "intent": normalized,
        "before_revision": loaded["instance_revision"],
        "after_revision": card_v2.instance_revision(validated),
        "diff": changes,
    }
    return {
        "valid": True,
        "requires_confirmation": True,
        "confirmation_token": _digest(basis),
        "intent": normalized,
        "before_snapshot": copy.deepcopy(loaded["snapshot"]),
        "candidate_snapshot": candidate_snapshot,
        "candidate_instance": validated,
        "diff": changes,
        "before_revision": loaded["instance_revision"],
        "after_revision": basis["after_revision"],
        "store_revision": loaded["store_revision"],
        "plan_revision": loaded["source"]["plan_revision"],
    }


def apply_confirmed_card_edit(
    project: str | Path,
    intent: Any,
    asset_catalog: Mapping[str, Mapping[str, Any]],
    *,
    expected_project_id: str,
    confirmation_token: str,
    confirmed: bool,
    usage_context: str = "local_authorized",
) -> dict[str, Any]:
    """Revalida estado atual e persiste somente após confirmação explícita."""

    if confirmed is not True:
        _error("confirmation_required", "A edição exige confirmação explícita.", "confirmed")
    review = review_card_edit_intent(
        project, intent, asset_catalog,
        expected_project_id=expected_project_id, usage_context=usage_context,
    )
    if confirmation_token != review["confirmation_token"]:
        _error("invalid_confirmation", "Token não corresponde ao diff validado atual.", "confirmation_token")
    result = persistence.save_card_state(
        project,
        review["candidate_snapshot"]["definition"],
        review["candidate_instance"],
        asset_catalog,
        expected_project_id=expected_project_id,
        expected_plan_revision=review["plan_revision"],
        expected_store_revision=review["store_revision"],
        base_revision=review["before_revision"],
        usage_context=usage_context,
    )
    return {
        **result,
        "intent_id": review["intent"]["intent_id"],
        "applied": True,
        "diff": copy.deepcopy(review["diff"]),
        "confirmation_token": review["confirmation_token"],
        "before_snapshot_digest": review["before_snapshot"]["snapshot_digest"],
    }
