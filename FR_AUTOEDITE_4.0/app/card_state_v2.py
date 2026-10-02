"""Schemas produtivos e validação pura de CardDefinition/CardInstance v2.

Este módulo é deliberadamente independente de Studio, timeline e renderers. Os
contratos congelados em M9.0 são a autoridade; nenhuma validação resolve paths
fornecidos pelo cliente ou lê bytes de assets. O chamador fornece um catálogo
confiável de ``asset_id``/scope/hash e só recebe cópias validadas.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Mapping

from card_media import CardMediaError, validate_central_media


APP_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ROOT = APP_ROOT / "contracts" / "m9"
SCHEMA_VERSION = 2
SNAPSHOT_VERSION = 1
EDITOR_SCHEMA = "fr-card-editor/1.1"
RENDERER_ID = "fr-universal-card"
EDIT_ORIGINS = frozenset({"manual", "ai_assisted", "deterministic_auto"})
ASSET_SCOPES = frozenset({"component", "service_catalog", "project_media", "project_asset"})
STATE_SECTIONS = ("assets", "layers", "gridStyle", "fields", "lines")

_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}")
_LEGACY_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")
_VERSION_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_COLOR_RE = re.compile(r"#[0-9A-Fa-f]{6}")


class CardStateV2Error(ValueError):
    """Falha de contrato antes de qualquer escrita ou renderização."""


def _load_contract(name: str) -> dict[str, Any]:
    try:
        value = json.loads((CONTRACT_ROOT / name).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Contrato M9 indisponível ou inválido: {name}.") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"Contrato M9 deve ser objeto JSON: {name}.")
    return value


_EDITOR_CONTRACT = _load_contract("fr_card_editor_1_1.json")
_CONCEPT_CONTRACT = _load_contract("card_state_v2_concept.json")
_GOLDEN_CONTRACT = _load_contract("golden_scenarios_v1.json")

FIXED_FIELD_IDS = tuple(_EDITOR_CONTRACT["fields"]["fixed_ids"])
VARIABLE_FIELD_IDS = tuple(_EDITOR_CONTRACT["fields"]["variable_ids"])
FIELD_IDS = FIXED_FIELD_IDS + VARIABLE_FIELD_IDS
LINE_IDS = tuple(_EDITOR_CONTRACT["lines"]["ids"])
FONTS = frozenset(_EDITOR_CONTRACT["fields"]["fonts"])
WEIGHTS = frozenset(_EDITOR_CONTRACT["fields"]["weights"])
ALIGNMENTS = frozenset(_EDITOR_CONTRACT["fields"]["alignments"])
EFFECTS = frozenset(_EDITOR_CONTRACT["fields"]["effects"])
VISUAL_SHAPES = frozenset(_EDITOR_CONTRACT["state"]["visual_shapes"])
SERVICE_KEYS = frozenset(
    row["visual"]["service_key"]
    for row in _GOLDEN_CONTRACT["scenarios"]
    if row.get("visual", {}).get("kind") == "service_catalog"
)

_STATE_FIELDS = frozenset(STATE_SECTIONS)
_ASSET_FIELDS = frozenset(_EDITOR_CONTRACT["state"]["asset_fields"])
_LAYER_FIELDS = frozenset(_EDITOR_CONTRACT["state"]["layers"])
_GRID_FIELDS = frozenset(_EDITOR_CONTRACT["state"]["grid_style_fields"])
_FIELD_PROPERTIES = frozenset(_EDITOR_CONTRACT["fields"]["properties"])
_LINE_PROPERTIES = frozenset(_EDITOR_CONTRACT["lines"]["properties"])
_FIELD_REQUIRED = frozenset({
    "id", "role", "text", "x", "y", "w", "h", "font", "size", "weight",
    "lineHeight", "spacing", "align", "color", "effect",
})
_LINE_REQUIRED = frozenset({"id", "x1", "y1", "x2", "y2", "width", "color", "visible"})
_ASSET_REF_FIELDS = frozenset({"scope", "asset_id", "sha256", "frame_time_sec"})
_ASSET_REF_REQUIRED = frozenset(_CONCEPT_CONTRACT["asset_ref"]["required"])
_DEFINITION_FIELDS = frozenset(_CONCEPT_CONTRACT["card_definition"]["required"])
_INSTANCE_REQUIRED = frozenset(_CONCEPT_CONTRACT["card_instance"]["required"])
_INSTANCE_FIELDS = _INSTANCE_REQUIRED | frozenset(_CONCEPT_CONTRACT["card_instance"]["optional"])
_LEGACY_FIELDS = frozenset({
    "schema_version", "instance_id", "definition_id", "definition_version",
    "edit_origin", "placement", "central_media",
})


def _error(label: str, message: str) -> None:
    raise CardStateV2Error(f"{label}: {message}")


def _object(
    value: Any, *, label: str, allowed: frozenset[str], required: frozenset[str],
) -> dict[str, Any]:
    if not isinstance(value, dict):
        _error(label, "esperado objeto.")
    unknown = sorted(set(value) - allowed)
    if unknown:
        _error(label, "campos desconhecidos: " + ", ".join(unknown) + ".")
    missing = sorted(required - set(value))
    if missing:
        _error(label, "campos obrigatórios ausentes: " + ", ".join(missing) + ".")
    return value


def _stable_id(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not _ID_RE.fullmatch(value)
        or ".." in value
        or "//" in value
    ):
        _error(label, "ID estável inválido.")
    return value


def _version(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _VERSION_RE.fullmatch(value):
        _error(label, "versão inválida.")
    return value


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        _error(label, f"esperado inteiro maior ou igual a {minimum}.")
    return value


def _number(
    value: Any, label: str, *, minimum: float | None = None,
    maximum: float | None = None, exclusive_minimum: bool = False,
) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        _error(label, "esperado número finito.")
    number = float(value)
    if minimum is not None and (
        number < minimum or (exclusive_minimum and number == minimum)
    ):
        qualifier = "maior que" if exclusive_minimum else "maior ou igual a"
        _error(label, f"esperado valor {qualifier} {minimum:g}.")
    if maximum is not None and number > maximum:
        _error(label, f"esperado valor menor ou igual a {maximum:g}.")
    return value


def _boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        _error(label, "esperado booleano.")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str):
        _error(label, "esperado texto Unicode.")
    for char in value:
        codepoint = ord(char)
        if 0xD800 <= codepoint <= 0xDFFF:
            _error(label, "Unicode contém surrogate isolado.")
        if codepoint < 0x20 and char != "\n":
            _error(label, "somente quebra de linha LF é permitida entre os controles.")
    return value


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        _error(label, "esperado SHA-256 hexadecimal minúsculo.")
    return value


def _canonical_bytes(value: Any, label: str) -> bytes:
    try:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise CardStateV2Error(f"{label}: estado não é JSON canônico válido.") from exc


def _digest(value: Any, label: str) -> str:
    return hashlib.sha256(_canonical_bytes(value, label)).hexdigest()


def _catalog_entry(
    catalog: Mapping[str, Mapping[str, Any]], asset_id: str, label: str,
) -> Mapping[str, Any]:
    if not isinstance(catalog, Mapping):
        _error(label, "catálogo confiável de assets não foi informado.")
    entry = catalog.get(asset_id)
    if not isinstance(entry, Mapping):
        _error(label + ".asset_id", f"asset inexistente no catálogo: {asset_id}.")
    if "asset_id" in entry and entry["asset_id"] != asset_id:
        _error(label + ".asset_id", "ID diverge da chave do catálogo.")
    return entry


def validate_asset_ref(
    value: Any, asset_catalog: Mapping[str, Mapping[str, Any]], *, label: str = "asset_ref",
) -> dict[str, Any]:
    row = _object(
        value, label=label, allowed=_ASSET_REF_FIELDS, required=_ASSET_REF_REQUIRED,
    )
    scope = row["scope"]
    if not isinstance(scope, str) or scope not in ASSET_SCOPES:
        _error(label + ".scope", "scope inválido.")
    asset_id = _stable_id(row["asset_id"], label + ".asset_id")
    sha256 = _sha256(row["sha256"], label + ".sha256")
    entry = _catalog_entry(asset_catalog, asset_id, label)
    if entry.get("scope") != scope:
        _error(label + ".scope", "scope diverge do catálogo.")
    if entry.get("sha256") != sha256:
        _error(label + ".sha256", "hash diverge do catálogo.")
    if "frame_time_sec" in row:
        _number(row["frame_time_sec"], label + ".frame_time_sec", minimum=0)
    return copy.deepcopy(row)


def _validate_assets(
    value: Any, asset_catalog: Mapping[str, Mapping[str, Any]], label: str,
) -> dict[str, Any]:
    row = _object(value, label=label, allowed=_ASSET_FIELDS, required=_ASSET_FIELDS)
    result = copy.deepcopy(row)
    for name in ("background", "logo"):
        result[name] = validate_asset_ref(row[name], asset_catalog, label=f"{label}.{name}")
    if row["visual"] is not None:
        result["visual"] = validate_asset_ref(
            row["visual"], asset_catalog, label=label + ".visual",
        )
    opacity_min, opacity_max = _EDITOR_CONTRACT["state"]["visual_ranges"]["visualOpacity"]
    size_min, size_max = _EDITOR_CONTRACT["state"]["visual_ranges"]["visualSize"]
    zoom_min, zoom_max = _EDITOR_CONTRACT["state"]["visual_ranges"]["visualZoom"]
    focal_x_min, focal_x_max = _EDITOR_CONTRACT["state"]["visual_ranges"]["visualFocalX"]
    focal_y_min, focal_y_max = _EDITOR_CONTRACT["state"]["visual_ranges"]["visualFocalY"]
    _number(row["visualOpacity"], label + ".visualOpacity", minimum=opacity_min, maximum=opacity_max)
    if not isinstance(row["visualShape"], str) or row["visualShape"] not in VISUAL_SHAPES:
        _error(label + ".visualShape", "forma visual inválida.")
    _number(row["visualSize"], label + ".visualSize", minimum=size_min, maximum=size_max)
    _number(row["visualZoom"], label + ".visualZoom", minimum=zoom_min, maximum=zoom_max)
    _number(row["visualFocalX"], label + ".visualFocalX", minimum=focal_x_min, maximum=focal_x_max)
    _number(row["visualFocalY"], label + ".visualFocalY", minimum=focal_y_min, maximum=focal_y_max)
    return result


def _validate_layers(value: Any, label: str) -> dict[str, bool]:
    row = _object(value, label=label, allowed=_LAYER_FIELDS, required=_LAYER_FIELDS)
    for key in _LAYER_FIELDS:
        _boolean(row[key], f"{label}.{key}")
    return copy.deepcopy(row)


def _validate_grid(value: Any, label: str) -> dict[str, Any]:
    row = _object(value, label=label, allowed=_GRID_FIELDS, required=_GRID_FIELDS)
    low, high = _EDITOR_CONTRACT["state"]["grid_opacity_range"]
    _number(row["opacity"], label + ".opacity", minimum=low, maximum=high)
    return copy.deepcopy(row)


def _validate_field(value: Any, index: int, label: str) -> dict[str, Any]:
    row = _object(value, label=label, allowed=_FIELD_PROPERTIES, required=_FIELD_REQUIRED)
    field_id = row["id"]
    if field_id not in FIELD_IDS:
        _error(label + ".id", f"campo desconhecido: {field_id!r}.")
    expected_role = "fixed" if field_id in FIXED_FIELD_IDS else "variable"
    if row["role"] != expected_role:
        _error(label + ".role", f"esperado {expected_role} para {field_id}.")
    _text(row["text"], label + ".text")
    for name in ("x", "y", "spacing"):
        _number(row[name], f"{label}.{name}")
    for name in ("w", "h", "size", "lineHeight"):
        _number(row[name], f"{label}.{name}", minimum=0, exclusive_minimum=True)
    if not isinstance(row["font"], str) or row["font"] not in FONTS:
        _error(label + ".font", "fonte não suportada pelo contrato congelado.")
    if (
        isinstance(row["weight"], bool)
        or not isinstance(row["weight"], int)
        or row["weight"] not in WEIGHTS
    ):
        _error(label + ".weight", "peso tipográfico inválido.")
    if not isinstance(row["align"], str) or row["align"] not in ALIGNMENTS:
        _error(label + ".align", "alinhamento inválido.")
    if not isinstance(row["effect"], str) or row["effect"] not in EFFECTS:
        _error(label + ".effect", "efeito inválido.")
    if not isinstance(row["color"], str) or not _COLOR_RE.fullmatch(row["color"]):
        _error(label + ".color", "cor deve usar #RRGGBB.")
    for name in ("visible", "noWrap", "shadowEnabled"):
        if name in row:
            _boolean(row[name], f"{label}.{name}")
    for name in ("shadowX", "shadowY"):
        if name in row:
            _number(row[name], f"{label}.{name}")
    if "shadowBlur" in row:
        _number(row["shadowBlur"], label + ".shadowBlur", minimum=0)
    if "shadowOpacity" in row:
        _number(row["shadowOpacity"], label + ".shadowOpacity", minimum=0, maximum=1)
    return copy.deepcopy(row)


def _validate_fields(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        _error(label, "esperada lista.")
    if len(value) != len(FIELD_IDS):
        _error(label, f"esperados exatamente {len(FIELD_IDS)} campos.")
    result = [_validate_field(row, index, f"{label}[{index}]") for index, row in enumerate(value)]
    ids = [row["id"] for row in result]
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        _error(label, "IDs duplicados: " + ", ".join(duplicates) + ".")
    missing = sorted(set(FIELD_IDS) - set(ids))
    if missing:
        _error(label, "campos obrigatórios ausentes: " + ", ".join(missing) + ".")
    return result


def _validate_line(value: Any, index: int, label: str) -> dict[str, Any]:
    row = _object(value, label=label, allowed=_LINE_PROPERTIES, required=_LINE_REQUIRED)
    if row["id"] not in LINE_IDS:
        _error(label + ".id", f"linha desconhecida: {row['id']!r}.")
    for name in ("x1", "y1", "x2", "y2"):
        _number(row[name], f"{label}.{name}")
    width_min, width_max = _EDITOR_CONTRACT["lines"]["width_range"]
    _number(row["width"], label + ".width", minimum=width_min, maximum=width_max)
    if not isinstance(row["color"], str) or not _COLOR_RE.fullmatch(row["color"]):
        _error(label + ".color", "cor deve usar #RRGGBB.")
    _boolean(row["visible"], label + ".visible")
    if "opacity" in row:
        low, high = _EDITOR_CONTRACT["lines"]["opacity_range"]
        _number(row["opacity"], label + ".opacity", minimum=low, maximum=high)
    if "fade" in row:
        _boolean(row["fade"], label + ".fade")
    return copy.deepcopy(row)


def _validate_lines(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        _error(label, "esperada lista.")
    if len(value) != len(LINE_IDS):
        _error(label, f"esperadas exatamente {len(LINE_IDS)} linhas.")
    result = [_validate_line(row, index, f"{label}[{index}]") for index, row in enumerate(value)]
    ids = [row["id"] for row in result]
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        _error(label, "IDs duplicados: " + ", ".join(duplicates) + ".")
    missing = sorted(set(LINE_IDS) - set(ids))
    if missing:
        _error(label, "linhas obrigatórias ausentes: " + ", ".join(missing) + ".")
    return result


def validate_card_state_v2(
    value: Any, asset_catalog: Mapping[str, Mapping[str, Any]], *, label: str = "state",
) -> dict[str, Any]:
    row = _object(value, label=label, allowed=_STATE_FIELDS, required=_STATE_FIELDS)
    result = {
        "assets": _validate_assets(row["assets"], asset_catalog, label + ".assets"),
        "layers": _validate_layers(row["layers"], label + ".layers"),
        "gridStyle": _validate_grid(row["gridStyle"], label + ".gridStyle"),
        "fields": _validate_fields(row["fields"], label + ".fields"),
        "lines": _validate_lines(row["lines"], label + ".lines"),
    }
    _canonical_bytes(result, label)
    return result


def _expected_capabilities() -> dict[str, Any]:
    return {
        "formats": list(_CONCEPT_CONTRACT["card_definition"]["formats"]),
        "state_sections": list(_CONCEPT_CONTRACT["card_definition"]["state_sections"]),
    }


def validate_card_definition_v2(
    value: Any, asset_catalog: Mapping[str, Mapping[str, Any]], *, label: str = "card_definition",
) -> dict[str, Any]:
    row = _object(value, label=label, allowed=_DEFINITION_FIELDS, required=_DEFINITION_FIELDS)
    if not isinstance(row["schema_version"], int) or isinstance(row["schema_version"], bool) or row["schema_version"] != SCHEMA_VERSION:
        _error(label + ".schema_version", f"versão suportada é {SCHEMA_VERSION}.")
    _stable_id(row["definition_id"], label + ".definition_id")
    _integer(row["definition_version"], label + ".definition_version", minimum=1)
    if row["editor_schema"] != EDITOR_SCHEMA:
        _error(label + ".editor_schema", f"esperado {EDITOR_SCHEMA}.")
    if row["renderer_id"] != RENDERER_ID:
        _error(label + ".renderer_id", f"esperado {RENDERER_ID}.")
    _version(row["renderer_version"], label + ".renderer_version")
    if row["canvas"] != _EDITOR_CONTRACT["canvas"]:
        _error(label + ".canvas", "deve coincidir com o canvas 9:16 congelado em M9.0.")
    if row["component"] != _EDITOR_CONTRACT["component"]:
        _error(label + ".component", "deve coincidir com o componente congelado em M9.0.")
    if row["capabilities"] != _expected_capabilities():
        _error(label + ".capabilities", "capabilities divergem do contrato conceitual M9.0.")
    result = copy.deepcopy(row)
    result["default_state"] = validate_card_state_v2(
        row["default_state"], asset_catalog, label=label + ".default_state",
    )
    _canonical_bytes(result, label)
    return result


def _validate_definition_ref(
    value: Any, definition: Mapping[str, Any], label: str,
) -> dict[str, Any]:
    allowed = frozenset({"definition_id", "definition_version"})
    row = _object(value, label=label, allowed=allowed, required=allowed)
    _stable_id(row["definition_id"], label + ".definition_id")
    _integer(row["definition_version"], label + ".definition_version", minimum=1)
    if row["definition_id"] != definition["definition_id"]:
        _error(label + ".definition_id", "não corresponde à CardDefinition validada.")
    if row["definition_version"] != definition["definition_version"]:
        _error(label + ".definition_version", "não corresponde à CardDefinition validada.")
    return copy.deepcopy(row)


def _validate_placement(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _error(label, "esperado objeto.")
    timebase = value.get("timebase")
    if timebase == "raw_sequence":
        fields = frozenset({"timebase", "sequence_index", "duration_sec"})
        row = _object(value, label=label, allowed=fields, required=fields)
        _integer(row["sequence_index"], label + ".sequence_index")
        _number(row["duration_sec"], label + ".duration_sec", minimum=0, exclusive_minimum=True)
    elif timebase == "ready_video_base":
        fields = frozenset({"timebase", "start_sec", "end_sec"})
        row = _object(value, label=label, allowed=fields, required=fields)
        start = _number(row["start_sec"], label + ".start_sec", minimum=0)
        end = _number(row["end_sec"], label + ".end_sec", minimum=0)
        if float(end) <= float(start):
            _error(label + ".end_sec", "deve ser maior que start_sec.")
    else:
        _error(label + ".timebase", "use raw_sequence ou ready_video_base.")
    return copy.deepcopy(row)


def renderable_state_digest(
    definition_ref: Mapping[str, Any], state: Mapping[str, Any], service_key: str | None = None,
) -> str:
    payload: dict[str, Any] = {
        "definition_ref": copy.deepcopy(definition_ref),
        "state": copy.deepcopy(state),
    }
    if service_key is not None:
        payload["service_key"] = service_key
    return _digest(payload, "estado renderizável")


def validate_card_instance_v2(
    value: Any, definition: Any, asset_catalog: Mapping[str, Mapping[str, Any]],
    *, label: str = "card_instance",
) -> dict[str, Any]:
    normalized_definition = validate_card_definition_v2(
        definition, asset_catalog, label="card_definition",
    )
    row = _object(value, label=label, allowed=_INSTANCE_FIELDS, required=_INSTANCE_REQUIRED)
    if not isinstance(row["schema_version"], int) or isinstance(row["schema_version"], bool) or row["schema_version"] != SCHEMA_VERSION:
        _error(label + ".schema_version", f"versão suportada é {SCHEMA_VERSION}.")
    _stable_id(row["instance_id"], label + ".instance_id")
    definition_ref = _validate_definition_ref(
        row["definition_ref"], normalized_definition, label + ".definition_ref",
    )
    if not isinstance(row["edit_origin"], str) or row["edit_origin"] not in EDIT_ORIGINS:
        _error(label + ".edit_origin", "origem de edição inválida.")
    placement = _validate_placement(row["placement"], label + ".placement")
    state = validate_card_state_v2(row["state"], asset_catalog, label=label + ".state")
    service_key = row.get("service_key")
    if service_key is not None and (
        not isinstance(service_key, str) or service_key not in SERVICE_KEYS
    ):
        _error(label + ".service_key", "serviço não pertence ao catálogo congelado.")
    expected_digest = renderable_state_digest(definition_ref, state, service_key)
    received_digest = _sha256(row["state_digest"], label + ".state_digest")
    if received_digest != expected_digest:
        _error(label + ".state_digest", "digest diverge do estado renderizável.")
    result = copy.deepcopy(row)
    result["definition_ref"] = definition_ref
    result["placement"] = placement
    result["state"] = state
    _canonical_bytes(result, label)
    return result


def _validate_legacy_v1(value: Any, label: str) -> dict[str, Any]:
    required = _LEGACY_FIELDS - {"central_media"}
    row = _object(value, label=label, allowed=_LEGACY_FIELDS, required=required)
    if not isinstance(row["schema_version"], int) or isinstance(row["schema_version"], bool) or row["schema_version"] != 1:
        _error(label + ".schema_version", "versão legada suportada é 1.")
    if not isinstance(row["instance_id"], str) or not _LEGACY_ID_RE.fullmatch(row["instance_id"]):
        _error(label + ".instance_id", "ID legado inválido.")
    _stable_id(row["definition_id"], label + ".definition_id")
    if isinstance(row["definition_version"], bool) or row["definition_version"] != 1:
        _error(label + ".definition_version", "versão legada suportada é 1.")
    if not isinstance(row["edit_origin"], str) or row["edit_origin"] not in EDIT_ORIGINS:
        _error(label + ".edit_origin", "origem de edição inválida.")
    result = copy.deepcopy(row)
    result["placement"] = _validate_placement(row["placement"], label + ".placement")
    if "central_media" in row:
        try:
            result["central_media"] = validate_central_media(
                row["central_media"], label=label + ".central_media",
            )
        except CardMediaError as exc:
            raise CardStateV2Error(str(exc)) from exc
    return result


def validate_card_instance(
    value: Any, *, definition: Any | None = None,
    asset_catalog: Mapping[str, Mapping[str, Any]] | None = None,
    label: str = "card_instance",
) -> dict[str, Any] | None:
    """Dispatch explícito; ausência mantém plano legado e v1 nunca vira v2."""
    if value is None:
        return None
    if not isinstance(value, dict):
        _error(label, "esperado objeto.")
    version = value.get("schema_version")
    if isinstance(version, bool):
        _error(label + ".schema_version", "versão inválida.")
    if version == 1:
        return _validate_legacy_v1(value, label)
    if version == SCHEMA_VERSION:
        if definition is None or asset_catalog is None:
            _error(label, "CardDefinition e catálogo são obrigatórios para v2.")
        return validate_card_instance_v2(value, definition, asset_catalog, label=label)
    _error(label + ".schema_version", "versão não suportada.")


def instance_revision(instance: Mapping[str, Any]) -> str:
    return _digest(instance, "card_instance")


def require_current_revision(base_revision: Any, current_instance: Mapping[str, Any]) -> str:
    received = _sha256(base_revision, "base_revision")
    current = instance_revision(current_instance)
    if received != current:
        _error("base_revision", "revisão obsoleta; recarregue o estado atual.")
    return current


def create_card_snapshot(
    definition: Any, instance: Any, asset_catalog: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    normalized_definition = validate_card_definition_v2(definition, asset_catalog)
    normalized_instance = validate_card_instance_v2(
        instance, normalized_definition, asset_catalog,
    )
    revision = instance_revision(normalized_instance)
    basis = {
        "snapshot_version": SNAPSHOT_VERSION,
        "definition": normalized_definition,
        "instance": normalized_instance,
        "revision": revision,
    }
    return basis | {"snapshot_digest": _digest(basis, "snapshot")}


def validate_card_snapshot(
    snapshot: Any, asset_catalog: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    fields = frozenset({
        "snapshot_version", "definition", "instance", "revision", "snapshot_digest",
    })
    row = _object(snapshot, label="snapshot", allowed=fields, required=fields)
    if not isinstance(row["snapshot_version"], int) or isinstance(row["snapshot_version"], bool) or row["snapshot_version"] != SNAPSHOT_VERSION:
        _error("snapshot.snapshot_version", f"versão suportada é {SNAPSHOT_VERSION}.")
    definition = validate_card_definition_v2(row["definition"], asset_catalog)
    instance = validate_card_instance_v2(row["instance"], definition, asset_catalog)
    revision = _sha256(row["revision"], "snapshot.revision")
    if revision != instance_revision(instance):
        _error("snapshot.revision", "revisão diverge da instância salva.")
    basis = {
        "snapshot_version": SNAPSHOT_VERSION,
        "definition": definition,
        "instance": instance,
        "revision": revision,
    }
    received_digest = _sha256(row["snapshot_digest"], "snapshot.snapshot_digest")
    if received_digest != _digest(basis, "snapshot"):
        _error("snapshot.snapshot_digest", "snapshot foi alterado.")
    return basis | {"snapshot_digest": received_digest}


def rollback_card_instance(
    current_instance: Any, snapshot: Any, *, expected_current_revision: Any,
    asset_catalog: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Restaura uma cópia validada sem publicar ou tocar no filesystem."""
    normalized_snapshot = validate_card_snapshot(snapshot, asset_catalog)
    current = validate_card_instance_v2(
        current_instance, normalized_snapshot["definition"], asset_catalog,
    )
    require_current_revision(expected_current_revision, current)
    return copy.deepcopy(normalized_snapshot["instance"])
