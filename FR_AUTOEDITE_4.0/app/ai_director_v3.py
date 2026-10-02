"""Contrato V3 da Direção Autônoma por IA.

O pacote V3 é editorialmente virgem: ele publica fatos, proxies elegíveis,
capacidades fechadas e um template de resposta; não publica EDIT_PLAN,
CARD_STATE, previews ou escolhas editoriais anteriores. A única decisão humana
pré-IA preservada é a elegibilidade da mídia (ex.: excluded_from_auto_edit).
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping

import project_scope
from ai_package_v2 import _media_inventory


PACKAGE_VERSION = 3
MODE = "autonomous_new_edit"
DETERMINISTIC_FILES = (
    "PROMPT_MESTRE_AUTONOMO.md",
    "FACTS.json",
    "MEDIA_MANIFEST.json",
    "CAPABILITIES.json",
    "DIRECTOR_TASK.json",
    "DIRECTOR_TEMPLATE.json",
    "RESPONSE_SCHEMA.json",
    "PACKAGE_DESCRIPTOR.json",
)


class AiDirectorV3Error(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def _compact_media_row(row: Mapping[str, Any]) -> dict[str, Any]:
    if not row.get("eligible"):
        return {
            "asset_id": str(row.get("asset_id") or ""),
            "eligible": False,
            "exclusion_reason": str(row.get("exclusion_reason") or "inelegível"),
        }
    proxy = row.get("proxy") if isinstance(row.get("proxy"), Mapping) else {}
    return {
        "asset_id": str(row.get("asset_id") or ""),
        "eligible": True,
        "media_type": str(row.get("media_type") or ""),
        "duration_sec": row.get("duration_sec"),
        "window": copy.deepcopy(row.get("window")),
        "parent_asset_id": str(row.get("parent_asset_id") or ""),
        "proxy": {
            "relative_path": str(proxy.get("relative_path") or ""),
            "size_bytes": int(proxy.get("size_bytes") or 0),
            "sha256": str(proxy.get("sha256") or ""),
            "width": proxy.get("width"),
            "height": proxy.get("height"),
            "duration_sec": proxy.get("duration_sec"),
            "has_audio": bool(proxy.get("has_audio")),
        },
    }


def _prompt(app_version: str) -> str:
    return f"""# PROMPT MESTRE AUTÔNOMO — FR AUTOEDITE {app_version}

Você é a direção editorial/técnica do FR AutoEdite. Analise visualmente TODOS os proxies elegíveis dos lotes e devolva UMA resposta JSON V3 executável. Você tem liberdade editorial dentro das capacidades publicadas, mas não tem liberdade factual nem liberdade para inventar recursos.

## Ordem de leitura
1. `FACTS.json` — fatos do projeto e contexto escrito pelo usuário.
2. `MEDIA_MANIFEST.json` — universo fechado de mídias. `eligible=false` significa: não use e não solicite esse proxy.
3. `CAPABILITIES.json` — universo fechado do que o aplicativo sabe executar.
4. `DIRECTOR_TASK.json` — missão e regras.
5. `DIRECTOR_TEMPLATE.json` e `RESPONSE_SCHEMA.json` — formato exato da resposta.
6. Assista aos proxies de TODOS os lotes antes de concluir a edição.

## Liberdade editorial permitida
Você decide seleção/descarte, ordem, cortes, tempos, ritmo, velocidades, estabilização, transições, fade, time-lapse, cards, quantidade de cards, card comum ou de serviço, textos, serviço por trecho, overlays, balões, narrativa, filme principal, Reels/Stories/carrossel, CTA, publicação e estratégia — apenas quando o contrato publicar capacidade para isso.

## Barreiras antialucinação
- Nunca invente `asset_id`, `media_id`, arquivo, caminho, URL, fonte, serviço, transição, efeito, card_kind, card_mode ou capability.
- Nunca crie uma foto/vídeo inexistente. Um card pode ser procedural; mídia central só pode usar um `asset_id` elegível publicado.
- `service_key` só pode vir de `CAPABILITIES.json`. Se o serviço não puder ser identificado com segurança, use card comum ou `needs_human_confirmation=true`; não force uma classificação.
- Não invente material, marca, medida, método, cliente, preço, prazo, resultado, depoimento ou qualquer fato não visível/confirmado. Use `facts_to_confirm` quando necessário.
- Não interprete nomes de arquivo como prova visual. O proxy é a evidência principal.
- Não recrie decisões antigas: este pacote é editorialmente virgem e não contém `EDIT_PLAN`, `CARD_STATE`, previews ou escolhas anteriores.
- Respeite `timeline_locked=true`: em `ready_video`, preserve integralmente o vídeo-base e decida apenas overlays/camadas permitidas.
- `DIRECTOR_TEMPLATE.json` contém somente defaults válidos para manter o contrato executável. Eles NÃO são decisões do usuário nem recomendações. Revise deliberadamente cada grupo editorial e não mantenha um valor apenas porque já veio preenchido.

## Regra de cobertura
`asset_decisions` deve conter EXATAMENTE uma decisão para cada `eligible_asset_id`: `use` ou `discard`. Se descartar, explique brevemente por quê. Se usar, o ID deve aparecer em alguma saída executável (filme principal, Reel/Stories/carrossel ou mídia de card), exceto quando houver justificativa explícita.

## Cards
Cards são instruções de layout executadas pelo `fr-universal-card`; não são imagens para você fabricar. Decida quando um card melhora compreensão. Evite excesso. Um card de serviço exige `service_key` válido e evidência visual/contextual. Cards convencionais e de serviço usam a mesma pipeline universal. Mídia central é opcional e, quando usada, deve apontar para um asset elegível existente.

## Resposta
Devolva SOMENTE JSON UTF-8 válido, sem Markdown, sem cercas, sem comentários e sem texto antes/depois. Preserve `package_snapshot_id`. Preencha `director_plan` conforme o template; ele é a fonte executável. Não use placeholders como `...`, `TODO`, `exemplo` ou valores fictícios.
"""


def _response_schema() -> dict[str, Any]:
    return {
        "schema_version": PACKAGE_VERSION,
        "required_top_level": [
            "schema_version", "package_snapshot_id", "mode", "asset_decisions",
            "director_plan", "facts_to_confirm", "executive_summary",
        ],
        "asset_decisions": {
            "coverage": "exactly_once_for_each_eligible_asset_id",
            "item": {
                "asset_id": "existing eligible_asset_id",
                "decision": ["use", "discard"],
                "reason": "short factual/editorial reason",
                "confidence": "number 0..1",
            },
        },
        "director_plan": {
            "contract": "FR Roteiro Mestre schema_version=2 accepted by local validator",
            "required": [
                "schema_version", "roteiro", "configuration", "main_timeline", "reels",
                "carousel", "stories", "card_style", "publication", "strategy", "executive_summary",
            ],
            "note": "Use DIRECTOR_TEMPLATE.json as structural seed and replace all editorial choices deliberately.",
        },
    }


def _task(input_mode: str) -> dict[str, Any]:
    return {
        "schema_version": PACKAGE_VERSION,
        "mode": MODE,
        "objective": "Criar uma edição nova do zero a partir de fatos + proxies elegíveis + capacidades fechadas.",
        "human_pre_ai_filter": {
            "preserve_excluded_from_auto_edit": True,
            "meaning": "Mídia marcada inelegível pelo usuário não participa da decisão da IA.",
        },
        "template_semantics": {
            "values_are": "valid_executable_fallbacks_and_schema_seed",
            "values_are_not": "previous_user_decisions_or_recommendations",
            "instruction": "Review every editorial group deliberately; do not preserve a template value merely because it is present.",
        },
        "editorial_state_policy": {
            "ignore_previous_edit_plan": True,
            "ignore_previous_card_state": True,
            "ignore_previous_previews": True,
            "ignore_previous_effect_choices": True,
            "ignore_previous_manual_order": True,
            "ignore_previous_ai_answers": True,
        },
        "input_mode": input_mode,
        "rules": [
            "analisar todos os proxies elegíveis antes de concluir",
            "usar apenas IDs e capacidades publicadas",
            "não inventar fatos nem mídias",
            "cada mídia elegível recebe decisão use/discard",
            "todo card é declarativo e usa fr-universal-card",
            "incerteza factual vira needs_human_confirmation/facts_to_confirm",
            "ready_video preserva a timeline bloqueada e edita apenas overlays",
        ],
    }


def build_snapshot(
    project: Path,
    answers: dict[str, Any],
    manifest: dict[str, Any],
    *,
    capabilities: dict[str, Any],
    director_template: dict[str, Any],
    app_version: str,
    probe: Callable[[Path], dict] | None = None,
) -> dict[str, Any]:
    project = Path(project).resolve()
    rows, proxy_paths = _media_inventory(project, manifest, probe)
    compact_rows = [_compact_media_row(row) for row in rows]
    context_paths = (project / "_ENTRADA" / "CONTEXTO_PROJETO.md", project / "CONTEXTO_PROJETO.md")
    context_text = next((p.read_text(encoding="utf-8", errors="strict") for p in context_paths if p.is_file()), "")
    project_data = answers.get("project", {}) if isinstance(answers.get("project"), dict) else {}
    input_data = answers.get("input", {}) if isinstance(answers.get("input"), dict) else {}
    input_mode = str(input_data.get("mode") or manifest.get("input_mode") or "raw_media")
    facts = {
        "schema_version": PACKAGE_VERSION,
        "project": {key: str(project_data.get(key) or "") for key in ("name", "client", "location")},
        "factual_context": context_text.strip(),
        "input_mode": input_mode,
        "base_video_id": str(input_data.get("base_video_id") or manifest.get("base_video_id") or ""),
        "timeline_locked": bool(input_mode == "ready_video"),
        "note": "Campos editoriais escolhidos anteriormente no Studio foram intencionalmente excluídos deste snapshot.",
    }
    media = {
        "schema_version": PACKAGE_VERSION,
        "assets": compact_rows,
        "eligible_asset_ids": [row["asset_id"] for row in compact_rows if row.get("eligible")],
        "excluded_asset_ids": [row["asset_id"] for row in compact_rows if not row.get("eligible")],
        "proxy_files": proxy_paths,
    }
    core: dict[str, Any] = {
        "PROMPT_MESTRE_AUTONOMO.md": _prompt(app_version),
        "FACTS.json": facts,
        "MEDIA_MANIFEST.json": media,
        "CAPABILITIES.json": copy.deepcopy(capabilities),
        "DIRECTOR_TASK.json": _task(input_mode),
        "DIRECTOR_TEMPLATE.json": copy.deepcopy(director_template),
        "RESPONSE_SCHEMA.json": _response_schema(),
    }
    snapshot_id = hashlib.sha256(b"".join(
        name.encode("utf-8") + b"\0" + (
            value.encode("utf-8") if isinstance(value, str) else _canonical(value)
        )
        for name, value in sorted(core.items())
    )).hexdigest()
    descriptor = {
        "schema_version": PACKAGE_VERSION,
        "mode": MODE,
        "snapshot_id": snapshot_id,
        "deterministic_files": sorted(core),
        "proxy_files": proxy_paths,
        "eligible_asset_ids": media["eligible_asset_ids"],
        "editorial_state": "virgin",
        "human_exclusions_preserved": True,
    }
    return {**core, "PACKAGE_DESCRIPTOR.json": descriptor}


def publish_snapshot(project: Path, documents: dict[str, Any]) -> Path:
    project = Path(project).resolve()
    root = Path("PACOTE_PARA_IA/V3")
    files = {str(root / name): value for name, value in documents.items()}
    descriptor = documents["PACKAGE_DESCRIPTOR.json"]
    files[str(root / "PACKAGE_AUDIT.json")] = {
        "schema_version": PACKAGE_VERSION,
        "generated_at": project_scope.timestamp(),
        "snapshot_id": descriptor["snapshot_id"],
        "note": "Metadado volátil fora do payload determinístico.",
    }
    project_scope.publish_files(project, files)
    return project / root


def generate_snapshot(project: Path, answers: dict[str, Any], manifest: dict[str, Any], **kwargs: Any) -> Path:
    return publish_snapshot(project, build_snapshot(project, answers, manifest, **kwargs))


def _read_response(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AiDirectorV3Error(f"Resposta V3 inválida: {exc}") from exc
    if not isinstance(value, dict):
        raise AiDirectorV3Error("Resposta V3 precisa ser um objeto JSON.")
    return value


def _collect_media_refs(value: Any, *, parent_key: str = "") -> set[str]:
    refs: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in {"media_id", "asset_id"} and isinstance(item, str) and item:
                # asset_id vazio é permitido em overlays procedurais.
                refs.add(item)
            elif key == "central_media" and isinstance(item, Mapping):
                asset = item.get("asset_id")
                if isinstance(asset, str) and asset:
                    refs.add(asset)
            else:
                refs.update(_collect_media_refs(item, parent_key=key))
    elif isinstance(value, list):
        for item in value:
            refs.update(_collect_media_refs(item, parent_key=parent_key))
    return refs


def load_v3_response(project: Path, path: Path) -> dict[str, Any]:
    project = Path(project).resolve()
    response = _read_response(path)
    if response.get("schema_version") != PACKAGE_VERSION:
        raise AiDirectorV3Error("Resposta autônoma exige schema_version=3.")
    if response.get("mode") != MODE:
        raise AiDirectorV3Error(f"mode deve ser `{MODE}`.")
    descriptor = project_scope.read(project / "PACOTE_PARA_IA/V3/PACKAGE_DESCRIPTOR.json", {})
    if not descriptor or response.get("package_snapshot_id") != descriptor.get("snapshot_id"):
        raise AiDirectorV3Error("package_snapshot_id não corresponde ao snapshot V3 atual.")
    eligible = [str(x) for x in descriptor.get("eligible_asset_ids", [])]
    eligible_set = set(eligible)
    decisions = response.get("asset_decisions")
    if not isinstance(decisions, list):
        raise AiDirectorV3Error("asset_decisions: esperado lista.")
    decision_map: dict[str, str] = {}
    for index, row in enumerate(decisions, 1):
        if not isinstance(row, Mapping):
            raise AiDirectorV3Error(f"asset_decisions[{index}]: esperado objeto.")
        asset_id = str(row.get("asset_id") or "")
        decision = str(row.get("decision") or "")
        if asset_id not in eligible_set:
            raise AiDirectorV3Error(f"asset_decisions[{index}].asset_id não é elegível: {asset_id!r}.")
        if asset_id in decision_map:
            raise AiDirectorV3Error(f"asset_decisions: asset_id duplicado: {asset_id}.")
        if decision not in {"use", "discard"}:
            raise AiDirectorV3Error(f"asset_decisions[{index}].decision: use `use` ou `discard`.")
        confidence = row.get("confidence", 1)
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= float(confidence) <= 1:
            raise AiDirectorV3Error(f"asset_decisions[{index}].confidence deve ficar entre 0 e 1.")
        decision_map[asset_id] = decision
    if set(decision_map) != eligible_set:
        missing = sorted(eligible_set - set(decision_map))
        extra = sorted(set(decision_map) - eligible_set)
        raise AiDirectorV3Error(f"asset_decisions deve cobrir exatamente todas as mídias elegíveis. faltando={missing}, extras={extra}")
    plan = response.get("director_plan")
    if not isinstance(plan, dict) or plan.get("schema_version") != 2:
        raise AiDirectorV3Error("director_plan: esperado Roteiro Mestre schema_version=2.")
    required = {"roteiro", "configuration", "main_timeline", "reels", "carousel", "stories", "card_style", "publication", "strategy", "executive_summary"}
    missing_top = sorted(required - set(plan))
    if missing_top:
        raise AiDirectorV3Error("director_plan incompleto; faltam: " + ", ".join(missing_top))
    configuration = plan.get("configuration")
    if not isinstance(configuration, dict):
        raise AiDirectorV3Error("director_plan.configuration: esperado objeto.")
    for group in ("edition", "social", "visual_effects", "audio_design", "cards"):
        if not isinstance(configuration.get(group), dict):
            raise AiDirectorV3Error(f"director_plan.configuration.{group}: decisão explícita obrigatória.")
    refs = _collect_media_refs(plan)
    technical_ids = {str(descriptor.get("base_video_id") or ""), "READY_VIDEO_BASE", "EXTERNAL_INTRO", "EXTERNAL_OUTRO"}
    unknown = sorted(ref for ref in refs if ref not in eligible_set and ref not in technical_ids and not ref.startswith("EXTERNAL_"))
    if unknown:
        raise AiDirectorV3Error("director_plan referencia mídia/asset inexistente ou inelegível: " + ", ".join(unknown[:12]))
    discarded_used = sorted(ref for ref in refs if decision_map.get(ref) == "discard")
    if discarded_used:
        raise AiDirectorV3Error("director_plan usa mídia marcada `discard`: " + ", ".join(discarded_used[:12]))
    declared_used = {asset_id for asset_id, decision in decision_map.items() if decision == "use"}
    unreferenced_used = sorted(declared_used - refs)
    if unreferenced_used:
        raise AiDirectorV3Error(
            "asset_decisions marca `use`, mas director_plan não referencia a mídia em nenhuma saída executável: "
            + ", ".join(unreferenced_used[:12])
        )
    facts = response.get("facts_to_confirm", [])
    if not isinstance(facts, list) or any(not isinstance(x, str) for x in facts):
        raise AiDirectorV3Error("facts_to_confirm deve ser lista de textos.")
    executive = response.get("executive_summary", [])
    if not isinstance(executive, list):
        raise AiDirectorV3Error("executive_summary deve ser lista.")
    result = copy.deepcopy(plan)
    # Fonte única: o resumo/fatos externos do envelope entram no payload executável.
    result["executive_summary"] = copy.deepcopy(executive or result.get("executive_summary", []))
    strategy = result.setdefault("strategy", {})
    if isinstance(strategy, dict):
        strategy["facts_to_confirm"] = copy.deepcopy(facts)
    return result
