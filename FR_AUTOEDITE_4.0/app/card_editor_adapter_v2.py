"""Adapter bidirecional puro entre CardInstance v2 e fr-card-editor/1.1.

O projeto validado é sempre a fonte de verdade. O adapter não lê localStorage,
não resolve paths, não grava uploads e não toca timeline ou renderer. URLs do
editor são bindings efêmeros fornecidos pelo backend; o estado persistível usa
somente AssetRef validado por ID e SHA-256.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

import card_state_v2 as card_v2


APP_ROOT = Path(__file__).resolve().parents[1]
ADAPTER_VERSION = "fr-autoedite-card/2"
EDITOR_VERSION = "1.1.0"
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_DATA_IMAGE_RE = re.compile(r"^data:image/(?:png|jpeg|webp);base64,", re.IGNORECASE)
_FORBIDDEN_BINDING_SCHEMES = ("data:", "file:", "blob:", "javascript:")
_PAYLOAD_FIELDS = frozenset({
    "adapter_version", "base_revision", "definition_digest", "instance_id",
    "definition_ref", "asset_refs", "editor_state",
})
_ASSET_REF_NAMES = frozenset({"background", "logo", "visual"})
_EDITOR_FIELD_DEFAULTS = {
    "visible": True,
    "noWrap": False,
    "shadowEnabled": False,
    "shadowX": 2,
    "shadowY": 3,
    "shadowBlur": 2,
    "shadowOpacity": 0.3,
}
_EDITOR_LINE_DEFAULTS = {"opacity": 1, "fade": True}


def _load_editor_contract() -> dict[str, Any]:
    path = APP_ROOT / "contracts" / "m9" / "fr_card_editor_1_1.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Contrato fr-card-editor/1.1 indisponível.") from exc
    if not isinstance(value, dict) or value.get("contract_id") != "fr-card-editor/1.1":
        raise RuntimeError("Contrato fr-card-editor/1.1 inválido.")
    return value


_EDITOR_CONTRACT = _load_editor_contract()
_EDITOR_TOP_FIELDS = frozenset(_EDITOR_CONTRACT["state"]["top_level_fields"])
_EDITOR_ASSET_FIELDS = frozenset(_EDITOR_CONTRACT["state"]["asset_fields"])


class CardEditorAdapterV2Error(ValueError):
    """Payload do editor não pode ser convertido sem perda ou sem confiança."""


def _error(label: str, message: str) -> None:
    raise CardEditorAdapterV2Error(f"{label}: {message}")


def _canonical_digest(value: Any, label: str) -> str:
    try:
        payload = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise CardEditorAdapterV2Error(f"{label}: conteúdo não é JSON canônico válido.") from exc
    return hashlib.sha256(payload).hexdigest()


def definition_digest(definition: Mapping[str, Any]) -> str:
    return _canonical_digest(definition, "card_definition")


def _object(
    value: Any, *, label: str, allowed: frozenset[str], required: frozenset[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        _error(label, "esperado objeto.")
    required = allowed if required is None else required
    unknown = sorted(set(value) - allowed)
    missing = sorted(required - set(value))
    if unknown or missing:
        details = []
        if unknown:
            details.append("desconhecidos: " + ", ".join(unknown))
        if missing:
            details.append("ausentes: " + ", ".join(missing))
        _error(label, "; ".join(details) + ".")
    return value


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        _error(label, "esperado SHA-256 hexadecimal minúsculo.")
    return value


def _binding_value(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 2048:
        _error(label, "binding deve ser uma URL/referência efêmera não vazia.")
    lowered = value.lower()
    if lowered.startswith(_FORBIDDEN_BINDING_SCHEMES):
        _error(label, "binding persistível não pode usar data, file, blob ou javascript.")
    if "\x00" in value or any(ord(char) < 0x20 for char in value):
        _error(label, "binding contém caractere de controle.")
    return value


def _bindings(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        _error("asset_bindings", "esperado mapa confiável asset_id -> URL efêmera.")
    result: dict[str, str] = {}
    for asset_id, binding in value.items():
        if not isinstance(asset_id, str):
            _error("asset_bindings", "asset_id deve ser texto.")
        result[asset_id] = _binding_value(binding, f"asset_bindings.{asset_id}")
    duplicates = sorted({item for item in result.values() if list(result.values()).count(item) > 1})
    if duplicates:
        _error("asset_bindings", "bindings duplicados não são permitidos.")
    return result


def _editor_canvas(definition: Mapping[str, Any]) -> dict[str, Any]:
    canvas = definition["canvas"]
    export_width, export_height = canvas["export_resolutions"][-1]
    return {
        "width": canvas["width"],
        "height": canvas["height"],
        "ratio": canvas["ratio"],
        "exportWidth": export_width,
        "exportHeight": export_height,
    }


def _asset_refs_from_state(state: Mapping[str, Any]) -> dict[str, Any]:
    assets = state["assets"]
    return {
        "background": copy.deepcopy(assets["background"]),
        "logo": copy.deepcopy(assets["logo"]),
        "visual": copy.deepcopy(assets["visual"]),
    }


def _binding_for_ref(ref: Mapping[str, Any], bindings: Mapping[str, str], label: str) -> str:
    asset_id = ref["asset_id"]
    if asset_id not in bindings:
        _error(label, f"asset_id sem binding efêmero: {asset_id}.")
    return bindings[asset_id]


def _normalized_editor_fields(fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = copy.deepcopy(fields)
    for row in result:
        row.setdefault("noWrap", False)
        row.setdefault("shadowEnabled", False)
        row.setdefault("visible", True)
    return result


def _normalized_editor_lines(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = copy.deepcopy(lines)
    for row in result:
        row.setdefault("opacity", 1)
        row.setdefault("fade", True)
    return result


def _to_editor_state(
    definition: Mapping[str, Any], instance: Mapping[str, Any], bindings: Mapping[str, str],
) -> dict[str, Any]:
    state = instance["state"]
    assets = copy.deepcopy(state["assets"])
    assets["background"] = _binding_for_ref(state["assets"]["background"], bindings, "assets.background")
    assets["logo"] = _binding_for_ref(state["assets"]["logo"], bindings, "assets.logo")
    visual = state["assets"]["visual"]
    assets["visual"] = "" if visual is None else _binding_for_ref(visual, bindings, "assets.visual")
    return {
        "version": EDITOR_VERSION,
        "canvas": _editor_canvas(definition),
        "assets": assets,
        "gridStyle": copy.deepcopy(state["gridStyle"]),
        "layers": copy.deepcopy(state["layers"]),
        "fields": _normalized_editor_fields(state["fields"]),
        "lines": _normalized_editor_lines(state["lines"]),
    }


def export_card_state(
    definition: Any, instance: Any, asset_catalog: Mapping[str, Mapping[str, Any]],
    asset_bindings: Mapping[str, str],
) -> dict[str, Any]:
    """Gera sessão completa para ``applyConfig`` a partir do snapshot atual."""
    if isinstance(instance, dict) and instance.get("schema_version") == 1:
        _error(
            "card_instance.schema_version",
            "CardInstance v1 permanece no adapter legado; conversão silenciosa para v2 é proibida.",
        )
    try:
        normalized_definition = card_v2.validate_card_definition_v2(definition, asset_catalog)
        normalized_instance = card_v2.validate_card_instance_v2(
            instance, normalized_definition, asset_catalog,
        )
    except card_v2.CardStateV2Error as exc:
        raise CardEditorAdapterV2Error(str(exc)) from exc
    bindings = _bindings(asset_bindings)
    editor_state = _to_editor_state(normalized_definition, normalized_instance, bindings)
    return {
        "adapter_version": ADAPTER_VERSION,
        "base_revision": card_v2.instance_revision(normalized_instance),
        "definition_digest": definition_digest(normalized_definition),
        "instance_id": normalized_instance["instance_id"],
        "definition_ref": copy.deepcopy(normalized_instance["definition_ref"]),
        "asset_refs": _asset_refs_from_state(normalized_instance["state"]),
        "editor_state": editor_state,
    }


def _validate_asset_refs(
    value: Any, asset_catalog: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    row = _object(value, label="asset_refs", allowed=_ASSET_REF_NAMES)
    result: dict[str, Any] = {}
    for name in ("background", "logo"):
        try:
            result[name] = card_v2.validate_asset_ref(
                row[name], asset_catalog, label=f"asset_refs.{name}",
            )
        except card_v2.CardStateV2Error as exc:
            raise CardEditorAdapterV2Error(str(exc)) from exc
    if row["visual"] is None:
        result["visual"] = None
    else:
        try:
            result["visual"] = card_v2.validate_asset_ref(
                row["visual"], asset_catalog, label="asset_refs.visual",
            )
        except card_v2.CardStateV2Error as exc:
            raise CardEditorAdapterV2Error(str(exc)) from exc
    return result


def _transient_hashes(value: Any) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        _error("transient_uploads", "esperado mapa asset_id -> hash da Data URL transitória.")
    result = {}
    for asset_id, digest in value.items():
        if not isinstance(asset_id, str):
            _error("transient_uploads", "asset_id deve ser texto.")
        result[asset_id] = _sha256(digest, f"transient_uploads.{asset_id}")
    return result


def _check_editor_asset(
    editor_value: Any, ref: Mapping[str, Any] | None, bindings: Mapping[str, str],
    transient_hashes: Mapping[str, str], label: str,
) -> None:
    if ref is None:
        if editor_value != "":
            _error(label, "visual vazio exige asset_refs.visual=null.")
        return
    if not isinstance(editor_value, str):
        _error(label, "editor deve devolver referência textual.")
    asset_id = ref["asset_id"]
    if editor_value.lower().startswith("data:"):
        if not _DATA_IMAGE_RE.match(editor_value):
            _error(label, "Data URL transitória não é uma imagem suportada.")
        expected = transient_hashes.get(asset_id)
        received = hashlib.sha256(editor_value.encode("utf-8")).hexdigest()
        if expected is None or expected != received:
            _error(label, "upload transitório não foi registrado pelo backend.")
        if asset_id not in bindings:
            _error(label, "upload registrado ainda não possui binding efêmero.")
        return
    expected_binding = bindings.get(asset_id)
    if expected_binding is None:
        _error(label, f"asset_id sem binding efêmero: {asset_id}.")
    if editor_value != expected_binding:
        _error(label, "referência devolvida não corresponde ao AssetRef validado.")


def _validate_editor_shell(editor_state: Any, definition: Mapping[str, Any]) -> dict[str, Any]:
    row = _object(editor_state, label="editor_state", allowed=_EDITOR_TOP_FIELDS)
    if row["version"] != EDITOR_VERSION:
        _error("editor_state.version", f"esperado {EDITOR_VERSION}.")
    if row["canvas"] != _editor_canvas(definition):
        _error("editor_state.canvas", "dimensões divergem do contrato 9:16 congelado.")
    _object(
        row["assets"], label="editor_state.assets",
        allowed=_EDITOR_ASSET_FIELDS, required=_EDITOR_ASSET_FIELDS,
    )
    return row


def _restore_semantic_presence(
    state: dict[str, Any], current_state: Mapping[str, Any],
) -> dict[str, Any]:
    current_fields = {row["id"]: row for row in current_state["fields"]}
    for row in state["fields"]:
        previous = current_fields[row["id"]]
        for name, default in _EDITOR_FIELD_DEFAULTS.items():
            if name not in previous and row.get(name) == default:
                row.pop(name, None)
    current_lines = {row["id"]: row for row in current_state["lines"]}
    for row in state["lines"]:
        previous = current_lines[row["id"]]
        for name, default in _EDITOR_LINE_DEFAULTS.items():
            if name not in previous and row.get(name) == default:
                row.pop(name, None)
    return state


def _require_no_property_loss(
    current_state: Mapping[str, Any], returned_state: Mapping[str, Any],
) -> None:
    for section in ("fields", "lines"):
        current_ids = [row["id"] for row in current_state[section]]
        returned_ids = [row["id"] for row in returned_state[section]]
        if returned_ids != current_ids:
            _error(
                f"editor_state.{section}",
                "ordem dos IDs diverge do estado aberto; reordenação silenciosa é proibida.",
            )
        current_rows = {row["id"]: row for row in current_state[section]}
        returned_rows = {row["id"]: row for row in returned_state[section]}
        for item_id, previous in current_rows.items():
            missing = sorted(set(previous) - set(returned_rows[item_id]))
            if missing:
                _error(
                    f"editor_state.{section}[{item_id}]",
                    "propriedades existentes removidas: " + ", ".join(missing) + ".",
                )


def _from_editor_state(
    editor_state: Any, definition: Mapping[str, Any], current_instance: Mapping[str, Any],
    asset_refs: Mapping[str, Any], asset_catalog: Mapping[str, Mapping[str, Any]],
    bindings: Mapping[str, str], transient_hashes: Mapping[str, str],
) -> dict[str, Any]:
    row = _validate_editor_shell(editor_state, definition)
    for name in ("background", "logo", "visual"):
        _check_editor_asset(
            row["assets"][name], asset_refs[name], bindings, transient_hashes,
            f"editor_state.assets.{name}",
        )
    assets = copy.deepcopy(row["assets"])
    assets["background"] = copy.deepcopy(asset_refs["background"])
    assets["logo"] = copy.deepcopy(asset_refs["logo"])
    assets["visual"] = copy.deepcopy(asset_refs["visual"])
    candidate = {
        "assets": assets,
        "layers": copy.deepcopy(row["layers"]),
        "gridStyle": copy.deepcopy(row["gridStyle"]),
        "fields": copy.deepcopy(row["fields"]),
        "lines": copy.deepcopy(row["lines"]),
    }
    try:
        normalized = card_v2.validate_card_state_v2(
            candidate, asset_catalog, label="editor_state",
        )
    except card_v2.CardStateV2Error as exc:
        raise CardEditorAdapterV2Error(str(exc)) from exc
    normalized = _restore_semantic_presence(normalized, current_instance["state"])
    _require_no_property_loss(current_instance["state"], normalized)
    try:
        return card_v2.validate_card_state_v2(
            normalized, asset_catalog, label="editor_state",
        )
    except card_v2.CardStateV2Error as exc:
        raise CardEditorAdapterV2Error(str(exc)) from exc


def apply_card_state(
    definition: Any, current_instance: Any, payload: Any,
    asset_catalog: Mapping[str, Mapping[str, Any]], asset_bindings: Mapping[str, str],
    *, transient_uploads: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Valida o retorno de ``getConfig`` e devolve nova CardInstance v2."""
    if isinstance(current_instance, dict) and current_instance.get("schema_version") == 1:
        _error(
            "card_instance.schema_version",
            "CardInstance v1 permanece no adapter legado; conversão silenciosa para v2 é proibida.",
        )
    try:
        normalized_definition = card_v2.validate_card_definition_v2(definition, asset_catalog)
        current = card_v2.validate_card_instance_v2(
            current_instance, normalized_definition, asset_catalog,
        )
    except card_v2.CardStateV2Error as exc:
        raise CardEditorAdapterV2Error(str(exc)) from exc
    row = _object(payload, label="payload", allowed=_PAYLOAD_FIELDS)
    if row["adapter_version"] != ADAPTER_VERSION:
        _error("payload.adapter_version", f"esperado {ADAPTER_VERSION}.")
    try:
        card_v2.require_current_revision(row["base_revision"], current)
    except card_v2.CardStateV2Error as exc:
        raise CardEditorAdapterV2Error(str(exc)) from exc
    received_definition_digest = _sha256(
        row["definition_digest"], "payload.definition_digest",
    )
    if received_definition_digest != definition_digest(normalized_definition):
        _error("payload.definition_digest", "CardDefinition mudou desde a abertura.")
    if row["instance_id"] != current["instance_id"]:
        _error("payload.instance_id", "não corresponde à instância atual.")
    if row["definition_ref"] != current["definition_ref"]:
        _error("payload.definition_ref", "não corresponde à definição da instância atual.")
    refs = _validate_asset_refs(row["asset_refs"], asset_catalog)
    bindings = _bindings(asset_bindings)
    transient = _transient_hashes(transient_uploads)
    state = _from_editor_state(
        row["editor_state"], normalized_definition, current, refs,
        asset_catalog, bindings, transient,
    )
    result = copy.deepcopy(current)
    result["state"] = state
    result["state_digest"] = card_v2.renderable_state_digest(
        result["definition_ref"], state, result.get("service_key"),
    )
    try:
        return card_v2.validate_card_instance_v2(
            result, normalized_definition, asset_catalog,
        )
    except card_v2.CardStateV2Error as exc:
        raise CardEditorAdapterV2Error(str(exc)) from exc


def title_body_projection(instance: Mapping[str, Any]) -> dict[str, str]:
    """Projeção somente-leitura; não cria uma segunda fonte de verdade."""
    fields = instance.get("state", {}).get("fields", [])
    if not isinstance(fields, list):
        _error("card_instance.state.fields", "esperada lista.")
    matches = [
        row for row in fields
        if isinstance(row, dict) and row.get("id") in {"title", "subtitle"}
    ]
    if (
        len(matches) != 2
        or {row.get("id") for row in matches} != {"title", "subtitle"}
        or not all(isinstance(row.get("text"), str) for row in matches)
    ):
        _error("card_instance.state.fields", "title/subtitle não estão disponíveis para projeção.")
    by_id = {row["id"]: row["text"] for row in matches}
    return {"title": by_id["title"], "body": by_id["subtitle"]}
