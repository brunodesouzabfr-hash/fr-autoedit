"""M9.9: ativação versionada de cards legados no contrato universal.

Este módulo só constrói estado: não altera ``EDIT_PLAN.json``,
``READY_VIDEO_PLAN.json`` nem bytes de mídia. A publicação transacional, o
snapshot e a regeneração dos previews são coordenados pelo runtime universal.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

import card_state_v2 as card_v2
import project_scope


APP_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = "_CONTROLE/CARD_MIGRATION_V99.json"
MIGRATION_ID = "fr-universal-card-activation/1"
MIGRATION_VERSION = "9.9.1"
DEFINITION_ID = "universal/migrated-legacy-9x16"
DEFINITION_VERSION = 2
LEGACY_RENDERER_ID = "fr-v4-f1-f6"


class CardMigrationV99Error(ValueError):
    """Um card não pode ser convertido sem perda ou a ativação é inválida."""


def _canonical_digest(value: Any) -> str:
    try:
        payload = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise CardMigrationV99Error("Dados legados não formam JSON canônico válido.") from exc
    return hashlib.sha256(payload).hexdigest()


def _contract() -> dict[str, Any]:
    try:
        value = json.loads(
            (APP_ROOT / "contracts/m9/fr_card_editor_1_1.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise CardMigrationV99Error("Contrato fr-card-editor/1.1 indisponível.") from exc
    if value.get("contract_id") != "fr-card-editor/1.1":
        raise CardMigrationV99Error("Contrato fr-card-editor/1.1 inválido.")
    return value


def _asset_ref(catalog: Mapping[str, Mapping[str, Any]], asset_id: str) -> dict[str, Any]:
    row = catalog.get(asset_id)
    if not isinstance(row, Mapping):
        raise CardMigrationV99Error(f"asset_id não existe no catálogo autorizado: {asset_id}.")
    return {
        "scope": str(row.get("scope") or ""),
        "asset_id": asset_id,
        "sha256": str(row.get("sha256") or ""),
    }


def _field(field_id: str, index: int) -> dict[str, Any]:
    fixed = field_id in card_v2.FIXED_FIELD_IDS
    # Layout conservador e integralmente editável. Campos sem dado legado ficam
    # vazios e invisíveis; nenhum texto de marketing é inventado pela migração.
    return {
        "id": field_id,
        "role": "fixed" if fixed else "variable",
        "text": "",
        "x": 80 + (index % 4) * 205,
        "y": 520 + (index // 4) * 150,
        "w": 170,
        "h": 110,
        "font": "Cormorant Garamond",
        "size": 24,
        "weight": 500,
        "lineHeight": 1.15,
        "spacing": 0,
        "align": "left",
        "color": "#e6d6b5",
        "effect": "plain",
        "visible": False,
        "noWrap": False,
        "shadowEnabled": False,
    }


def _base_state(catalog: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Carrega o estado visual canônico do FR Card Editor Universal v1.1.0.

    A M9.9 anterior reconstruía apenas título/subtítulo e desligava o grid,
    criando um contrato universal que não reproduzia o template aprovado.
    A 4.5 congela o DEFAULT real do editor em contracts/m9 e troca apenas
    referências de arquivo por AssetRefs validados.
    """
    default_path = APP_ROOT / "contracts/m9/card_editor_default_v1_1.json"
    try:
        default = json.loads(default_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CardMigrationV99Error(
            "Contrato visual canônico do Card Editor v1.1.0 está ausente ou inválido."
        ) from exc
    if default.get("version") != "1.1.0":
        raise CardMigrationV99Error("Versão do template canônico do Card Editor divergente.")
    fields = copy.deepcopy(default.get("fields"))
    lines = copy.deepcopy(default.get("lines"))
    if not isinstance(fields, list) or not isinstance(lines, list):
        raise CardMigrationV99Error("Template canônico não contém fields/lines válidos.")
    # O editor omite esses defaults no JSON-base; o renderer/adapter aceitam a
    # ausência, mas explicitá-los estabiliza round-trip e diffs de persistência.
    for row in fields:
        if isinstance(row, dict):
            row.setdefault("visible", True)
            row.setdefault("noWrap", False)
            row.setdefault("shadowEnabled", False)
    for row in lines:
        if isinstance(row, dict):
            row.setdefault("opacity", 1)
            row.setdefault("fade", True)
    assets = copy.deepcopy(default.get("assets") or {})
    return {
        "assets": {
            "background": _asset_ref(catalog, "component/background-fr-hd"),
            "logo": _asset_ref(catalog, "component/logo-fr"),
            "visual": None,
            "visualOpacity": assets.get("visualOpacity", 1),
            "visualShape": assets.get("visualShape", "circle"),
            "visualSize": assets.get("visualSize", 389),
            "visualZoom": assets.get("visualZoom", 1),
            "visualFocalX": assets.get("visualFocalX", 50),
            "visualFocalY": assets.get("visualFocalY", 50),
        },
        "layers": copy.deepcopy(default.get("layers") or {"background": True, "grid": True, "text": True, "logo": True}),
        "gridStyle": copy.deepcopy(default.get("gridStyle") or {"opacity": 0.36}),
        "fields": fields,
        "lines": lines,
    }


def build_definition(catalog: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    contract = _contract()
    value = {
        "schema_version": 2,
        "definition_id": DEFINITION_ID,
        "definition_version": DEFINITION_VERSION,
        "editor_schema": "fr-card-editor/1.1",
        "renderer_id": card_v2.RENDERER_ID,
        "renderer_version": "1.0.0",
        "canvas": copy.deepcopy(contract["canvas"]),
        "component": copy.deepcopy(contract["component"]),
        "default_state": _base_state(catalog),
        "capabilities": {
            "formats": ["9:16"],
            "state_sections": ["assets", "layers", "gridStyle", "fields", "lines"],
        },
    }
    return card_v2.validate_card_definition_v2(value, catalog)


def _text(value: Any, label: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise CardMigrationV99Error(f"{label}: texto legado não é string.")
    if any(ord(char) < 0x20 and char != "\n" for char in value):
        raise CardMigrationV99Error(f"{label}: texto legado contém controle inválido.")
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _finite(value: Any, label: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise CardMigrationV99Error(f"{label}: esperado número finito.")
    number = float(value)
    if number < low or number > high:
        raise CardMigrationV99Error(f"{label}: esperado valor entre {low:g} e {high:g}.")
    return number


def _explicit_asset_id(card: Mapping[str, Any], role: str) -> str:
    names = {
        "background": ("background_asset_id", "background_media_id"),
        "logo": ("logo_asset_id", "logo_media_id"),
    }[role]
    for name in names:
        if name not in card or card.get(name) in (None, ""):
            continue
        value = card[name]
        if not isinstance(value, str):
            raise CardMigrationV99Error(f"{name}: referência de asset inválida.")
        return value
    return ""


def _central_media(
    card: Mapping[str, Any], catalog: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    legacy_instance = card.get("card_instance")
    central = legacy_instance.get("central_media") if isinstance(legacy_instance, Mapping) else None
    if central is None:
        central = card.get("central_media")
    if central is None:
        return None, {}
    if not isinstance(central, Mapping):
        raise CardMigrationV99Error("central_media: esperado objeto.")
    asset_id = central.get("central_asset_id")
    if not isinstance(asset_id, str) or not asset_id:
        raise CardMigrationV99Error("central_media.central_asset_id: asset ausente.")
    ref = _asset_ref(catalog, asset_id)
    if ref["scope"] not in {"project_media", "project_asset", "service_catalog", "component"}:
        raise CardMigrationV99Error("central_media: escopo do asset não é renderizável.")
    shape = str(central.get("shape") or "circle")
    if shape not in card_v2.VISUAL_SHAPES:
        raise CardMigrationV99Error(f"central_media.shape: formato não suportado: {shape}.")
    zoom = _finite(central.get("zoom", 1), "central_media.zoom", 1, 3)
    focal_x = _finite(central.get("focal_x", 0.5), "central_media.focal_x", 0, 1)
    focal_y = _finite(central.get("focal_y", 0.5), "central_media.focal_y", 0, 1)
    if "frame_time_sec" in central:
        frame_time = _finite(central["frame_time_sec"], "central_media.frame_time_sec", 0, 10**9)
        if frame_time:
            ref["frame_time_sec"] = frame_time
    return ref, {
        "visualShape": shape,
        "visualZoom": zoom,
        "visualFocalX": focal_x * 100,
        "visualFocalY": focal_y * 100,
    }


def _placement(card: Mapping[str, Any], index: int, input_mode: str) -> dict[str, Any]:
    if input_mode == "raw_media":
        duration = _finite(card.get("duration_sec"), "duration_sec", 0.000001, 10**9)
        return {"timebase": "raw_sequence", "sequence_index": index, "duration_sec": duration}
    start = _finite(card.get("start_sec"), "start_sec", 0, 10**9)
    end = _finite(card.get("end_sec"), "end_sec", 0.000001, 10**9)
    if end <= start:
        raise CardMigrationV99Error("end_sec deve ser maior que start_sec.")
    return {"timebase": "ready_video_base", "start_sec": start, "end_sec": end}


def card_inventory(project: str | Path) -> tuple[str, dict[str, Any], list[tuple[int, dict[str, Any]]]]:
    root = Path(project).resolve()
    manifest = project_scope.read(root / "MANIFESTO_MEDIA.json", {})
    input_mode = str(manifest.get("input_mode") or "")
    if not input_mode:
        ready = project_scope.read(root / "READY_VIDEO_PLAN.json", {})
        input_mode = "ready_video" if ready.get("input_mode") == "ready_video" else "raw_media"
    if input_mode == "ready_video":
        plan = project_scope.read(root / "READY_VIDEO_PLAN.json", {})
        rows = [
            (index, row) for index, row in enumerate(plan.get("overlays", []))
            if isinstance(row, dict) and row.get("kind") in {"common_card", "service_card"}
        ]
    elif input_mode == "raw_media":
        plan = project_scope.read(root / "EDIT_PLAN.json", {})
        rows = [
            (index, row) for index, row in enumerate(plan.get("segments", []))
            if isinstance(row, dict) and row.get("type") == "card"
        ]
    else:
        raise CardMigrationV99Error("Projeto deve declarar raw_media ou ready_video.")
    return input_mode, plan, rows


def source_fingerprint(context: Mapping[str, Any]) -> str:
    return _canonical_digest({
        "migration_id": MIGRATION_ID,
        "migration_version": MIGRATION_VERSION,
        "input_mode": context.get("input_mode"),
        "plan_revision": context.get("plan_revision"),
        "manifest_revision": context.get("manifest_revision"),
    })


def current_report(project: str | Path, context: Mapping[str, Any]) -> dict[str, Any] | None:
    report = project_scope.read(Path(project) / REPORT_PATH, None)
    if not isinstance(report, dict):
        return None
    if (
        report.get("migration_id") != MIGRATION_ID
        or report.get("migration_version") != MIGRATION_VERSION
        or report.get("source_fingerprint") != source_fingerprint(context)
    ):
        return None
    basis = {key: copy.deepcopy(value) for key, value in report.items() if key != "revision"}
    if report.get("revision") != _canonical_digest(basis):
        return None
    return report


def _load_reusable_instances(
    project: Path, catalog: Mapping[str, Mapping[str, Any]],
) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    store = project_scope.read(project / "_CONTROLE/CARD_STATE_V2.json", {})
    if not isinstance(store, dict) or not store:
        return {}
    basis = {key: copy.deepcopy(value) for key, value in store.items() if key != "revision"}
    if store.get("revision") != _canonical_digest(basis):
        raise CardMigrationV99Error("CARD_STATE_V2 existente possui revisão divergente.")
    definitions: dict[tuple[str, int], dict[str, Any]] = {}
    for raw in store.get("definitions", []):
        definition = card_v2.validate_card_definition_v2(raw, catalog)
        definitions[(definition["definition_id"], definition["definition_version"])] = definition
    reusable: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for raw in store.get("instances", []):
        ref = raw.get("definition_ref", {}) if isinstance(raw, Mapping) else {}
        definition = definitions.get((ref.get("definition_id"), ref.get("definition_version")))
        if definition is None:
            raise CardMigrationV99Error("CARD_STATE_V2 existente referencia definição ausente.")
        instance = card_v2.validate_card_instance_v2(raw, definition, catalog)
        if instance["instance_id"] in reusable:
            raise CardMigrationV99Error("CARD_STATE_V2 existente contém instance_id duplicado.")
        reusable[instance["instance_id"]] = (definition, instance)
    return reusable


def _legacy_reduced_state_v1(catalog: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Baseline produzido pela M9.9.0, usado somente para detectar edições reais."""
    fields = [_field(field_id, index) for index, field_id in enumerate(card_v2.FIELD_IDS)]
    by_id = {row["id"]: row for row in fields}
    by_id["title"].update({
        "x": 78, "y": 205, "w": 785, "h": 118,
        "font": "Stardos Stencil", "size": 55, "weight": 700,
        "lineHeight": 1, "align": "center", "color": "#f6a700",
        "effect": "metallic", "visible": True, "noWrap": False,
        "shadowEnabled": True, "shadowX": 2, "shadowY": 3,
        "shadowBlur": 2.5, "shadowOpacity": 0.34,
    })
    by_id["subtitle"].update({
        "x": 120, "y": 340, "w": 701, "h": 150,
        "size": 29, "weight": 500, "lineHeight": 1.08,
        "align": "center", "visible": True,
    })
    lines = [{
        "id": line_id, "x1": 0, "y1": 0, "x2": 1, "y2": 1,
        "width": 1.4, "color": "#d6a64b", "visible": False,
        "opacity": 1, "fade": True,
    } for line_id in card_v2.LINE_IDS]
    return {
        "assets": {
            "background": _asset_ref(catalog, "component/background-fr-hd"),
            "logo": _asset_ref(catalog, "component/logo-fr"),
            "visual": None, "visualOpacity": 1, "visualShape": "circle",
            "visualSize": 389, "visualZoom": 1, "visualFocalX": 50, "visualFocalY": 50,
        },
        "layers": {"background": True, "grid": True, "text": True, "logo": True},
        "gridStyle": {"opacity": 0.36},
        "fields": fields,
        "lines": lines,
    }


def _upgrade_reduced_v1_instance(
    instance: Mapping[str, Any], old_definition: Mapping[str, Any],
    new_definition: Mapping[str, Any], catalog: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Atualiza M9.9.0 reduzida para o template visual canônico sem apagar edições."""
    current = copy.deepcopy(instance["state"])
    legacy = _legacy_reduced_state_v1(catalog)
    upgraded = copy.deepcopy(new_definition["default_state"])

    # Assets são escolhas do projeto/usuário e sempre prevalecem.
    upgraded["assets"] = copy.deepcopy(current["assets"])
    upgraded["layers"] = copy.deepcopy(current.get("layers", upgraded["layers"]))
    upgraded["gridStyle"] = copy.deepcopy(current.get("gridStyle", upgraded["gridStyle"]))

    current_fields = {row["id"]: row for row in current["fields"]}
    legacy_fields = {row["id"]: row for row in legacy["fields"]}
    upgraded_fields = {row["id"]: row for row in upgraded["fields"]}
    for field_id, row in current_fields.items():
        target = upgraded_fields[field_id]
        baseline = legacy_fields[field_id]
        # Título/subtítulo sempre preservam conteúdo legado. Estilo só prevalece
        # quando divergiu do baseline M9.9.0, indicando edição manual/IA.
        if field_id in {"title", "subtitle"}:
            target["text"] = row.get("text", "")
            changed_style = any(
                row.get(key) != baseline.get(key)
                for key in set(row) | set(baseline)
                if key not in {"text", "id", "role"}
            )
            if changed_style:
                for key, value in row.items():
                    if key not in {"id", "role", "text"}:
                        target[key] = copy.deepcopy(value)
        elif row != baseline:
            # Campo que era vazio/invisível e agora diverge foi de fato editado.
            upgraded_fields[field_id] = copy.deepcopy(row)
    upgraded["fields"] = [upgraded_fields[field_id] for field_id in card_v2.FIELD_IDS]

    current_lines = {row["id"]: row for row in current["lines"]}
    legacy_lines = {row["id"]: row for row in legacy["lines"]}
    upgraded_lines = {row["id"]: row for row in upgraded["lines"]}
    for line_id, row in current_lines.items():
        if row != legacy_lines[line_id]:
            upgraded_lines[line_id] = copy.deepcopy(row)
    upgraded["lines"] = [upgraded_lines[line_id] for line_id in card_v2.LINE_IDS]

    result = copy.deepcopy(instance)
    result["definition_ref"] = {
        "definition_id": new_definition["definition_id"],
        "definition_version": new_definition["definition_version"],
    }
    result["state"] = upgraded
    service_key = str(result.get("service_key") or "")
    result["state_digest"] = card_v2.renderable_state_digest(
        result["definition_ref"], upgraded, service_key or None,
    )
    return card_v2.validate_card_instance_v2(result, new_definition, catalog)


def _new_instance(
    card: Mapping[str, Any], index: int, input_mode: str,
    definition: Mapping[str, Any], catalog: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    instance_id = card.get("overlay_id") if input_mode == "ready_video" else card.get("segment_id")
    if not isinstance(instance_id, str) or not instance_id:
        raise CardMigrationV99Error("Card legado não possui ID estável.")
    state = copy.deepcopy(definition["default_state"])
    title = card.get("text") if input_mode == "ready_video" else card.get("title")
    body = card.get("body")
    for row in state["fields"]:
        if row["id"] == "title":
            row["text"] = _text(title, "title")
        elif row["id"] == "subtitle":
            row["text"] = _text(body, "body")
    for role in ("background", "logo"):
        asset_id = _explicit_asset_id(card, role)
        if asset_id:
            state["assets"][role] = _asset_ref(catalog, asset_id)
    visual, visual_properties = _central_media(card, catalog)
    legacy_asset_id = card.get("asset_id") if input_mode == "ready_video" else None
    if legacy_asset_id not in (None, ""):
        if visual is not None:
            raise CardMigrationV99Error("asset_id legado e central_media concorrem pela mídia visual.")
        if not isinstance(legacy_asset_id, str):
            raise CardMigrationV99Error("asset_id legado inválido.")
        visual = _asset_ref(catalog, legacy_asset_id)
    service_key = str(card.get("service_key") or "")
    if not visual and service_key:
        visual = _asset_ref(catalog, "medallion_" + service_key)
        visual_properties["visualShape"] = "circle"
    if visual:
        state["assets"]["visual"] = visual
        state["assets"].update(visual_properties)
    origin = "manual"
    legacy_instance = card.get("card_instance")
    if isinstance(legacy_instance, Mapping) and legacy_instance.get("edit_origin") in card_v2.EDIT_ORIGINS:
        origin = str(legacy_instance["edit_origin"])
    ref = {
        "definition_id": definition["definition_id"],
        "definition_version": definition["definition_version"],
    }
    instance: dict[str, Any] = {
        "schema_version": 2,
        "instance_id": instance_id,
        "definition_ref": ref,
        "edit_origin": origin,
        "placement": _placement(card, index, input_mode),
        "state": state,
        "state_digest": card_v2.renderable_state_digest(ref, state, service_key or None),
    }
    if service_key:
        instance["service_key"] = service_key
    return card_v2.validate_card_instance_v2(instance, definition, catalog)


def build_migration(
    project: str | Path, context: Mapping[str, Any],
    catalog: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    root = Path(project).resolve()
    input_mode, _plan, rows = card_inventory(root)
    definition = build_definition(catalog)
    reusable = _load_reusable_instances(root, catalog)
    definitions: dict[tuple[str, int], dict[str, Any]] = {}
    instances: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    labels = [
        str((card.get("overlay_id") if input_mode == "ready_video" else card.get("segment_id"))
            or f"card-sem-id-{index}")
        for index, card in rows
    ]
    duplicates = {label for label in labels if labels.count(label) > 1}
    for index, card in rows:
        instance_id = card.get("overlay_id") if input_mode == "ready_video" else card.get("segment_id")
        label = str(instance_id or f"card-sem-id-{index}")
        source_digest = _canonical_digest(card)
        if label in duplicates:
            reason = "ID duplicado no plano; conversão ambígua."
            records.append({
                "instance_id": label, "source_index": index, "source_digest": source_digest,
                "outcome": "compatibility_fallback", "renderer_id": LEGACY_RENDERER_ID,
                "fallback": {"registered": True, "reason": reason},
            })
            continue
        try:
            if label in reusable:
                current_definition, instance = copy.deepcopy(reusable[label])
                if (
                    current_definition.get("definition_id") == DEFINITION_ID
                    and int(current_definition.get("definition_version") or 0) < DEFINITION_VERSION
                ):
                    instance = _upgrade_reduced_v1_instance(
                        instance, current_definition, definition, catalog,
                    )
                    current_definition = definition
                    source = "existing_v2_upgraded_4_5"
                else:
                    source = "existing_v2"
                instance["placement"] = _placement(card, index, input_mode)
                expected_service = str(card.get("service_key") or "")
                if expected_service:
                    instance["service_key"] = expected_service
                else:
                    instance.pop("service_key", None)
                instance["state_digest"] = card_v2.renderable_state_digest(
                    instance["definition_ref"], instance["state"], expected_service or None,
                )
                instance = card_v2.validate_card_instance_v2(instance, current_definition, catalog)
            else:
                current_definition = definition
                instance = _new_instance(card, index, input_mode, definition, catalog)
                source = "legacy_conversion"
            key = (current_definition["definition_id"], current_definition["definition_version"])
            definitions[key] = current_definition
            instances.append(instance)
            records.append({
                "instance_id": label,
                "source_index": index,
                "source_digest": source_digest,
                "outcome": "migrated",
                "renderer_id": card_v2.RENDERER_ID,
                "conversion_source": source,
                "state_digest": instance["state_digest"],
                "preserved": {
                    "id": True,
                    "text": True,
                    "placement": True,
                    "duration_or_window": True,
                    "source_plan_unchanged": True,
                    "assets_by_manifest_reference": True,
                },
            })
        except (CardMigrationV99Error, card_v2.CardStateV2Error) as exc:
            records.append({
                "instance_id": label,
                "source_index": index,
                "source_digest": source_digest,
                "outcome": "compatibility_fallback",
                "renderer_id": LEGACY_RENDERER_ID,
                "fallback": {"registered": True, "reason": str(exc)},
            })
    migrated = sum(row["outcome"] == "migrated" for row in records)
    fallback = len(records) - migrated
    report = {
        "schema_version": 1,
        "migration_id": MIGRATION_ID,
        "migration_version": MIGRATION_VERSION,
        "project_id": context["project_id"],
        "input_mode": input_mode,
        "source_fingerprint": source_fingerprint(context),
        "source": {
            "plan_revision": context["plan_revision"],
            "manifest_revision": context["manifest_revision"],
        },
        "status": (
            "no_cards_discovered" if not records
            else "completed" if fallback == 0
            else "completed_with_explicit_fallback"
        ),
        "counts": {"discovered": len(records), "migrated": migrated, "fallback": fallback},
        "cards": records,
        "raw_media_and_ready_video_unchanged": True,
        "previews": {"invalidated": [], "regenerated": []},
        "rollback_version": "",
    }
    return {
        "definitions": list(definitions.values()),
        "instances": instances,
        "report": report,
    }


def seal_report(report: Mapping[str, Any]) -> dict[str, Any]:
    basis = copy.deepcopy(dict(report))
    basis.pop("revision", None)
    return basis | {"revision": _canonical_digest(basis)}


def route(project: str | Path, instance_id: str) -> dict[str, Any]:
    report = project_scope.read(Path(project) / REPORT_PATH, {})
    cards = report.get("cards", []) if isinstance(report, dict) else []
    matches = [row for row in cards if isinstance(row, dict) and row.get("instance_id") == instance_id]
    if len(matches) != 1:
        raise CardMigrationV99Error(
            f"Card {instance_id!r} não possui rota M9.9 única; fallback silencioso é proibido."
        )
    return copy.deepcopy(matches[0])
