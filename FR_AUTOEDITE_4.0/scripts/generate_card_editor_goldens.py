#!/usr/bin/env python3
"""Gera e verifica golden masters locais do FR Card Editor v1.1.0.

Os PNGs, estados extraídos e fontes baixadas são deliberadamente locais e não
podem ser incluídos no Git ou em releases enquanto a licença do componente
externo estiver pendente. O script não implementa CardDefinition/CardInstance
v2 nem valida escrita de projeto; ele congela somente a referência visual M9.0.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ROOT = ROOT / "contracts" / "m9"
ARCHITECTURE_PATH = CONTRACT_ROOT / "architecture_v1.json"
EDITOR_CONTRACT_PATH = CONTRACT_ROOT / "fr_card_editor_1_1.json"
FONT_SOURCES_PATH = CONTRACT_ROOT / "font_sources_v1.json"
SCENARIOS_PATH = CONTRACT_ROOT / "golden_scenarios_v1.json"
SERVICE_MANIFEST = ROOT / "assets" / "style_packs" / "fr_quiet_engineering_atelier_v2" / "manifest.json"
SERVICE_CATALOG = ROOT / "templates" / "service_catalog.json"
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")


class GoldenMasterError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GoldenMasterError(f"JSON inválido ou ausente: {path}") from exc
    if not isinstance(value, dict):
        raise GoldenMasterError(f"Contrato deve ser objeto JSON: {path}")
    return value


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return sha256_bytes(payload)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=".m9-json-", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _unique_ids(rows: Any, label: str) -> list[str]:
    if not isinstance(rows, list):
        raise GoldenMasterError(f"{label}: esperado array.")
    result: list[str] = []
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise GoldenMasterError(f"{label}[{index}]: esperado objeto.")
        item_id = row.get("id")
        if not isinstance(item_id, str) or not _ID.fullmatch(item_id):
            raise GoldenMasterError(f"{label}[{index}].id inválido.")
        if item_id in result:
            raise GoldenMasterError(f"{label}: ID duplicado: {item_id}.")
        result.append(item_id)
    return result


def validate_editor_state(state: Any, contract: dict[str, Any]) -> None:
    """Validação de referência M9.0; não substitui o validator produtivo M9.1."""
    if not isinstance(state, dict):
        raise GoldenMasterError("Estado do editor deve ser objeto.")
    required = set(contract["state"]["top_level_fields"])
    missing = sorted(required - set(state))
    if missing:
        raise GoldenMasterError("Estado do editor sem campos: " + ", ".join(missing))
    if state.get("version") != contract["state"]["version"]:
        raise GoldenMasterError("Versão do estado do editor divergente.")
    canvas = state.get("canvas")
    expected_canvas = contract["canvas"]
    if not isinstance(canvas, dict) or (
        canvas.get("width"), canvas.get("height"), canvas.get("ratio")
    ) != (expected_canvas["width"], expected_canvas["height"], expected_canvas["ratio"]):
        raise GoldenMasterError("Canvas do editor divergente do contrato congelado.")
    field_ids = _unique_ids(state.get("fields"), "fields")
    expected_fields = contract["fields"]["fixed_ids"] + contract["fields"]["variable_ids"]
    if set(field_ids) != set(expected_fields) or len(field_ids) != 21:
        raise GoldenMasterError("DEFAULT precisa conter exatamente os 21 campos conhecidos.")
    roles = {row["id"]: row.get("role") for row in state["fields"]}
    if any(roles[item] != "fixed" for item in contract["fields"]["fixed_ids"]):
        raise GoldenMasterError("Role fixed divergente no DEFAULT.")
    if any(roles[item] != "variable" for item in contract["fields"]["variable_ids"]):
        raise GoldenMasterError("Role variable divergente no DEFAULT.")
    line_ids = _unique_ids(state.get("lines"), "lines")
    if line_ids != contract["lines"]["ids"] or len(line_ids) != 29:
        raise GoldenMasterError("DEFAULT precisa conter as 29 linhas na ordem congelada.")
    if not isinstance(state.get("assets"), dict) or not isinstance(state.get("layers"), dict):
        raise GoldenMasterError("Assets e layers precisam ser objetos.")


def validate_contracts(
    architecture: dict[str, Any], contract: dict[str, Any], fonts: dict[str, Any],
    scenarios: dict[str, Any], service_keys: set[str],
) -> None:
    if architecture.get("decision_id") != "ACR-M9-001" or architecture.get("decision_status") != "approved":
        raise GoldenMasterError("ACR-M9-001 não está aprovada no contrato executável.")
    routing = architecture.get("renderer_routing", {})
    if set(routing) != {"fr-v4-f1-f6", "fr-universal-card"}:
        raise GoldenMasterError("Roteamento de renderer incompleto.")
    if routing["fr-v4-f1-f6"].get("behavior_change_in_m9_0") is not False:
        raise GoldenMasterError("M9.0 não pode alterar o renderer legado.")
    if routing["fr-universal-card"].get("formats") != ["9:16"]:
        raise GoldenMasterError("M9.0 deve congelar somente 9:16.")
    if contract.get("contract_id") != "fr-card-editor/1.1":
        raise GoldenMasterError("Contrato do editor incorreto.")
    if len(contract["fields"]["fixed_ids"] + contract["fields"]["variable_ids"]) != 21:
        raise GoldenMasterError("Contrato deve declarar 21 campos.")
    if len(contract["lines"]["ids"]) != 29:
        raise GoldenMasterError("Contrato deve declarar 29 linhas.")
    if contract["component"].get("excluded") != ["FR_CARD_EDITOR_STANDALONE.html"]:
        raise GoldenMasterError("Standalone precisa permanecer excluído.")
    if fonts.get("purpose") != "local_golden_generation_only" or fonts.get("redistribution_in_fr_autoedite") is not False:
        raise GoldenMasterError("Fontes de golden não podem virar dependência ou redistribuição.")
    font_names: set[str] = set()
    for row in fonts.get("fonts", []):
        if not isinstance(row, dict) or not re.fullmatch(r"[0-9a-f]{64}", str(row.get("sha256") or "")):
            raise GoldenMasterError("Fonte sem hash congelado.")
        if row.get("license_id") != "OFL-1.1":
            raise GoldenMasterError("Fonte de golden sem licença OFL-1.1 registrada.")
        if row.get("file") in font_names:
            raise GoldenMasterError("Arquivo de fonte duplicado.")
        font_names.add(str(row.get("file")))
    rows = scenarios.get("scenarios")
    if not isinstance(rows, list) or not rows:
        raise GoldenMasterError("Suite de golden vazia.")
    scenario_ids: set[str] = set()
    found_services: set[str] = set()
    found_shapes: set[str] = set()
    allowed_resolutions = {tuple(item) for item in contract["canvas"]["export_resolutions"]}
    for row in rows:
        if not isinstance(row, dict) or not _ID.fullmatch(str(row.get("id") or "")):
            raise GoldenMasterError("Cenário com ID inválido.")
        if row["id"] in scenario_ids:
            raise GoldenMasterError(f"Cenário duplicado: {row['id']}.")
        scenario_ids.add(row["id"])
        resolutions = row.get("resolutions")
        if not isinstance(resolutions, list) or not resolutions:
            raise GoldenMasterError(f"{row['id']}: sem resolução.")
        if any(tuple(value) not in allowed_resolutions for value in resolutions):
            raise GoldenMasterError(f"{row['id']}: resolução fora do contrato.")
        visual = row.get("visual")
        if isinstance(visual, dict):
            shape = str(visual.get("shape") or "")
            if shape not in contract["state"]["visual_shapes"]:
                raise GoldenMasterError(f"{row['id']}: shape desconhecido.")
            found_shapes.add(shape)
            if visual.get("kind") == "service_catalog":
                key = str(visual.get("service_key") or "")
                if key not in service_keys:
                    raise GoldenMasterError(f"{row['id']}: service_key desconhecido: {key}.")
                found_services.add(key)
            elif visual.get("kind") != "synthetic_test_pattern":
                raise GoldenMasterError(f"{row['id']}: origem visual desconhecida.")
        for operation in row.get("operations", []):
            if operation.get("op") not in {"set_field", "set_line", "set_grid_style", "set_layers"}:
                raise GoldenMasterError(f"{row['id']}: operação desconhecida.")
    if found_services != service_keys:
        raise GoldenMasterError("Suite precisa cobrir exatamente os 13 serviços.")
    if found_shapes != set(contract["state"]["visual_shapes"]):
        raise GoldenMasterError("Suite precisa cobrir circle, square, rounded e full.")
    baseline = next((row for row in rows if row["id"] == "baseline"), None)
    if baseline is None or {tuple(item) for item in baseline["resolutions"]} != allowed_resolutions:
        raise GoldenMasterError("Baseline precisa cobrir as três resoluções 9:16.")


def validate_component(source: Path, contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    source = source.expanduser().resolve()
    if not source.is_dir():
        raise GoldenMasterError(f"Componente não encontrado: {source}")
    checked: dict[str, dict[str, Any]] = {}
    for relative, specification in contract["component"]["files"].items():
        target = (source / relative).resolve()
        try:
            target.relative_to(source)
        except ValueError as exc:
            raise GoldenMasterError(f"Arquivo fora do componente: {relative}") from exc
        if not target.is_file() or target.is_symlink():
            raise GoldenMasterError(f"Arquivo modular ausente ou inseguro: {relative}")
        digest = sha256_file(target)
        if digest != specification["sha256"]:
            raise GoldenMasterError(f"Hash divergente no componente: {relative}")
        checked[relative] = {"sha256": digest, "size_bytes": target.stat().st_size}
        if target.suffix.lower() == ".png":
            from PIL import Image
            with Image.open(target) as image:
                actual = (image.width, image.height, image.mode)
            expected = (specification["width"], specification["height"], specification["mode"])
            if actual != expected:
                raise GoldenMasterError(f"Dimensões/modo divergentes: {relative}")
    return checked


def prepare_fonts(font_contract: dict[str, Any], target: Path, *, download: bool) -> list[dict[str, Any]]:
    target.mkdir(parents=True, exist_ok=True)
    repository = str(font_contract["repository"]).rstrip("/")
    commit = str(font_contract["commit"])
    result: list[dict[str, Any]] = []
    for row in font_contract["fonts"]:
        path = target / row["file"]
        source_url = f"{repository}/raw/{commit}/{urllib.parse.quote(row['source_path'], safe='/')}"
        if not path.is_file():
            if not download:
                raise GoldenMasterError(
                    f"Fonte local ausente: {path}. Execute novamente com --download-fonts."
                )
            handle, name = tempfile.mkstemp(prefix=".m9-font-", dir=target)
            os.close(handle)
            try:
                request = urllib.request.Request(source_url, headers={"User-Agent": "FR-AutoEdite-M9.0"})
                with urllib.request.urlopen(request, timeout=60) as response, open(name, "wb") as output:
                    shutil.copyfileobj(response, output)
                os.replace(name, path)
            finally:
                if os.path.exists(name):
                    os.unlink(name)
        digest = sha256_file(path)
        if digest != row["sha256"]:
            raise GoldenMasterError(f"Hash divergente na fonte local: {row['file']}")
        result.append({
            "file": row["file"], "family": row["family"], "weight": row["weight"],
            "sha256": digest, "size_bytes": path.stat().st_size,
            "source_url": source_url, "license_id": row["license_id"],
        })
    return result


def _font_css() -> str:
    return """<style id=\"m9-golden-fonts\">
@font-face{font-family:\"Cormorant Garamond\";src:url(\"fonts/CormorantGaramond.ttf\") format(\"truetype\");font-style:normal;font-weight:300 700;font-display:block}
@font-face{font-family:Rokkitt;src:url(\"fonts/Rokkitt.ttf\") format(\"truetype\");font-style:normal;font-weight:100 900;font-display:block}
@font-face{font-family:\"Share Tech Mono\";src:url(\"fonts/ShareTechMono-Regular.ttf\") format(\"truetype\");font-style:normal;font-weight:400;font-display:block}
@font-face{font-family:\"Stardos Stencil\";src:url(\"fonts/StardosStencil-Regular.ttf\") format(\"truetype\");font-style:normal;font-weight:400;font-display:block}
@font-face{font-family:\"Stardos Stencil\";src:url(\"fonts/StardosStencil-Bold.ttf\") format(\"truetype\");font-style:normal;font-weight:700;font-display:block}
</style>"""


def prepare_harness(source: Path, font_cache: Path, work: Path, contract: dict[str, Any]) -> None:
    for relative in contract["component"]["files"]:
        src = source / relative
        dst = work / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    fonts = work / "fonts"
    fonts.mkdir(parents=True)
    for font in font_cache.glob("*.ttf"):
        shutil.copy2(font, fonts / font.name)
    index = work / "index.html"
    html = index.read_text(encoding="utf-8")
    html = re.sub(
        r"\s*<link[^>]+(?:fonts\.googleapis\.com|fonts\.gstatic\.com)[^>]*>", "", html,
    )
    actual_save = '$("#saveLocal").onclick=()=>{try{localStorage.setItem("fr-card-editor-v1.1",JSON.stringify(state));toast("Estado salvo neste navegador")}catch{toast("Estado grande demais; exporte JSON")}};'
    if actual_save not in html:
        raise GoldenMasterError("Não foi possível neutralizar a escrita localStorage do componente.")
    html = html.replace(actual_save, '$("#saveLocal").onclick=()=>toast("localStorage desativado no golden M9.0");')
    load_local = 'try{let saved=localStorage.getItem("fr-card-editor-v1.1");if(saved)state=normalizeConfig(JSON.parse(saved))}catch{}render();resizeStage();'
    if load_local not in html:
        raise GoldenMasterError("Não foi possível neutralizar a leitura localStorage do componente.")
    html = html.replace(load_local, 'state=clone(DEFAULT);render();resizeStage();')
    if "localStorage." in html:
        raise GoldenMasterError("Harness ainda contém acesso a localStorage.")
    html = html.replace("</head>", _font_css() + "\n</head>")
    index.write_text(html, encoding="utf-8")


def synthetic_pattern(path: Path) -> dict[str, Any]:
    from PIL import Image, ImageDraw
    width, height = 1200, 900
    image = Image.new("RGB", (width, height), "#071d18")
    draw = ImageDraw.Draw(image)
    colors = ("#f6a700", "#1a6069", "#e6d6b5", "#ff6b00")
    draw.rectangle((0, 0, width // 2, height // 2), fill=colors[0])
    draw.rectangle((width // 2, 0, width, height // 2), fill=colors[1])
    draw.rectangle((0, height // 2, width // 2, height), fill=colors[2])
    draw.rectangle((width // 2, height // 2, width, height), fill=colors[3])
    for offset in range(0, min(width, height), 60):
        draw.line((0, offset, offset, 0), fill="#121318", width=8)
        draw.line((width - offset, height, width, height - offset), fill="#0a2f26", width=8)
    draw.ellipse((360, 210, 840, 690), outline="#ffffff", width=18)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", compress_level=6)
    image.close()
    return {"asset_id": "m9-synthetic-pattern", "sha256": sha256_file(path), "width": width, "height": height}


def _service_index(app_root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    manifest = load_json(app_root / SERVICE_MANIFEST.relative_to(ROOT))
    catalog_source = load_json(app_root / SERVICE_CATALOG.relative_to(ROOT))
    catalog = {
        str(row["key"]): row for row in catalog_source.get("services", [])
        if isinstance(row, dict) and row.get("key")
    }
    assets = manifest.get("assets")
    if not isinstance(assets, dict):
        raise GoldenMasterError("Manifesto SERVICE sem assets.")
    return catalog, assets


def prepare_service_assets(app_root: Path, work: Path, service_keys: set[str]) -> dict[str, dict[str, Any]]:
    catalog, assets = _service_index(app_root)
    result: dict[str, dict[str, Any]] = {}
    if set(catalog) != service_keys:
        raise GoldenMasterError("Catálogo SERVICE diverge dos 13 cenários congelados.")
    app_root = app_root.resolve()
    for key in sorted(service_keys):
        asset_id = "medallion_" + key
        entry = assets.get(asset_id)
        if not isinstance(entry, dict) or entry.get("servico") != key:
            raise GoldenMasterError(f"Asset SERVICE ausente ou divergente: {asset_id}")
        relative = str(entry.get("normalized_path") or "")
        target = (app_root / relative).resolve()
        try:
            target.relative_to(app_root)
        except ValueError as exc:
            raise GoldenMasterError(f"Asset SERVICE fora da raiz: {asset_id}") from exc
        expected = str((entry.get("normalized") or {}).get("sha256") or "")
        if not target.is_file() or not expected or sha256_file(target) != expected:
            raise GoldenMasterError(f"Asset SERVICE ausente ou com hash divergente: {asset_id}")
        harness_name = f"m9-service-{key}.png"
        shutil.copy2(target, work / "assets" / harness_name)
        result[key] = {
            "service_key": key,
            "label": str(catalog[key].get("label") or key),
            "asset_id": asset_id,
            "sha256": expected,
            "runtime_path": f"assets/{harness_name}",
            "scope": "service_catalog",
            "opaque_background_preserved": bool((entry.get("normalized") or {}).get("opaque_background_preserved")),
        }
    return result


def apply_operations(state: dict[str, Any], scenario: dict[str, Any]) -> None:
    for operation in scenario.get("operations", []):
        kind = operation["op"]
        if kind == "set_field":
            row = next((item for item in state["fields"] if item["id"] == operation["id"]), None)
            if row is None:
                raise GoldenMasterError(f"Campo inexistente no cenário: {operation['id']}")
            row.update(copy.deepcopy(operation["values"]))
        elif kind == "set_line":
            row = next((item for item in state["lines"] if item["id"] == operation["id"]), None)
            if row is None:
                raise GoldenMasterError(f"Linha inexistente no cenário: {operation['id']}")
            row.update(copy.deepcopy(operation["values"]))
        elif kind == "set_grid_style":
            state["gridStyle"].update(copy.deepcopy(operation["values"]))
        elif kind == "set_layers":
            state["layers"].update(copy.deepcopy(operation["values"]))


def apply_visual(
    logical: dict[str, Any], runtime: dict[str, Any], visual: dict[str, Any],
    synthetic: dict[str, Any], services: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if visual["kind"] == "synthetic_test_pattern":
        asset = {
            "asset_id": synthetic["asset_id"], "sha256": synthetic["sha256"],
            "runtime_path": "assets/m9-synthetic-pattern.png",
            "scope": "synthetic_fixture",
        }
    else:
        asset = services[str(visual["service_key"])]
        label = asset["label"]
        for state in (logical, runtime):
            next(row for row in state["fields"] if row["id"] == "title")["text"] = label
            next(row for row in state["fields"] if row["id"] == "subtitle")["text"] = (
                "GOLDEN SERVICE · " + str(visual["service_key"]).upper()
            )
    # O caminho é real e existe somente no harness temporário. O escopo/ID/hash
    # ficam no manifesto; nenhum esquema de URI ou path produtivo é inventado.
    for state in (logical, runtime):
        state["assets"].update({
            "visual": asset["runtime_path"],
            "visualOpacity": visual["opacity"],
            "visualShape": visual["shape"],
            "visualSize": visual["size"],
            "visualZoom": visual["zoom"],
            "visualFocalX": visual["focal_x"],
            "visualFocalY": visual["focal_y"],
        })
        for field_id in ("visualTitle", "visualBody"):
            next(row for row in state["fields"] if row["id"] == field_id)["visible"] = False
    return {key: value for key, value in asset.items() if key != "runtime_path"}


def _browser_versions(chromium: str, chromedriver: str) -> dict[str, str]:
    def version(command: str) -> str:
        result = subprocess.run(
            [command, "--version"], check=True, capture_output=True, text=True, timeout=15,
        )
        return result.stdout.strip() or result.stderr.strip()
    return {"chromium": version(chromium), "chromedriver": version(chromedriver)}


def _driver(chromium: str, chromedriver: str):
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
    except ImportError as exc:
        raise GoldenMasterError("Instale requirements-dev.txt para gerar os goldens com Selenium.") from exc
    options = Options()
    options.binary_location = chromium
    for argument in (
        "--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
        "--allow-file-access-from-files", "--force-device-scale-factor=1",
        "--hide-scrollbars", "--disable-background-networking",
    ):
        options.add_argument(argument)
    return webdriver.Chrome(service=Service(chromedriver), options=options)


def _load_fonts(driver) -> dict[str, int]:
    requests = [
        ('400 24px "Cormorant Garamond"', "M9 Cormorant"),
        ('500 24px "Cormorant Garamond"', "M9 Cormorant"),
        ('600 24px "Cormorant Garamond"', "M9 Cormorant"),
        ('400 24px Rokkitt', "M9 Rokkitt"),
        ('500 24px Rokkitt', "M9 Rokkitt"),
        ('600 24px Rokkitt', "M9 Rokkitt"),
        ('400 24px "Share Tech Mono"', "M9 Share Tech"),
        ('400 24px "Stardos Stencil"', "M9 Stardos"),
        ('700 24px "Stardos Stencil"', "M9 Stardos"),
    ]
    result = driver.execute_async_script(
        """
        const items=arguments[0],done=arguments[arguments.length-1];
        Promise.all(items.map(([font,text])=>document.fonts.load(font,text)))
          .then(rows=>document.fonts.ready.then(()=>done(rows.map(row=>row.length))))
          .catch(error=>done({error:String(error)}));
        """,
        requests,
    )
    if not isinstance(result, list) or len(result) != len(requests) or any(int(item) < 1 for item in result):
        raise GoldenMasterError(f"Conjunto tipográfico exato não carregou: {result}")
    return {font: int(count) for (font, _text), count in zip(requests, result)}


def _download_png(driver, directory: Path, width: int, height: int) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    driver.execute_cdp_cmd("Page.setDownloadBehavior", {"behavior": "allow", "downloadPath": str(directory)})
    driver.execute_script(
        "document.getElementById('exportResolution').value=arguments[0]; FRCardEditor.exportPNG();",
        f"{width}x{height}",
    )
    expected = directory / f"FR_CARD_{width}x{height}.png"
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if expected.is_file() and not list(directory.glob("*.crdownload")):
            return expected
        time.sleep(0.1)
    raise GoldenMasterError(f"Timeout ao exportar {width}x{height}.")


def generate(
    source: Path, app_root: Path, output: Path, *, download_fonts: bool,
    chromium: str, chromedriver: str,
) -> dict[str, Any]:
    architecture = load_json(ARCHITECTURE_PATH)
    contract = load_json(EDITOR_CONTRACT_PATH)
    font_contract = load_json(FONT_SOURCES_PATH)
    scenarios = load_json(SCENARIOS_PATH)
    catalog, _assets = _service_index(app_root)
    service_keys = set(catalog)
    validate_contracts(architecture, contract, font_contract, scenarios, service_keys)
    component_files = validate_component(source, contract)
    output = output.expanduser().resolve()
    app_root = app_root.expanduser().resolve()
    try:
        relative_output = output.relative_to(app_root)
    except ValueError:
        relative_output = None
    if relative_output is not None and relative_output.parts[:1] not in {
        ("FR_CARD_EDITOR_UNIVERSAL_v1.1.0",), ("local_components",),
    }:
        raise GoldenMasterError(
            "Dentro do checkout, use somente diretório ignorado do componente local para os goldens."
        )
    output.mkdir(parents=True, exist_ok=True)
    font_cache = output / "font-cache"
    fonts = prepare_fonts(font_contract, font_cache, download=download_fonts)
    versions = _browser_versions(chromium, chromedriver)
    repeat = int(scenarios.get("repeat_each_render") or 2)
    if repeat < 2:
        raise GoldenMasterError("Golden M9.0 exige pelo menos duas renderizações idênticas.")
    records: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="fr-m9-golden-harness-") as temporary:
        work = Path(temporary)
        prepare_harness(source.resolve(), font_cache, work, contract)
        synthetic = synthetic_pattern(work / "assets" / "m9-synthetic-pattern.png")
        service_assets = prepare_service_assets(app_root, work, service_keys)
        driver = _driver(chromium, chromedriver)
        try:
            driver.set_script_timeout(45)
            driver.get((work / "index.html").as_uri())
            font_loads = _load_fonts(driver)
            default_state = driver.execute_script("return FRCardEditor.getConfig();")
            validate_editor_state(default_state, contract)
            for scenario in scenarios["scenarios"]:
                logical = copy.deepcopy(default_state)
                runtime = copy.deepcopy(default_state)
                apply_operations(logical, scenario)
                apply_operations(runtime, scenario)
                asset_record = None
                if isinstance(scenario.get("visual"), dict):
                    asset_record = apply_visual(
                        logical, runtime, scenario["visual"], synthetic, service_assets,
                    )
                validate_editor_state(logical, contract)
                state_path = output / "states" / f"{scenario['id']}.editor.json"
                write_json(state_path, logical)
                driver.execute_script("FRCardEditor.applyConfig(arguments[0]);", runtime)
                artifacts = []
                for width, height in scenario["resolutions"]:
                    digests: list[str] = []
                    first: Path | None = None
                    for iteration in range(repeat):
                        download = work / "downloads" / scenario["id"] / f"{width}x{height}" / str(iteration)
                        captured = _download_png(driver, download, width, height)
                        digests.append(sha256_file(captured))
                        if first is None:
                            first = captured
                    if len(set(digests)) != 1:
                        raise GoldenMasterError(
                            f"Render não determinístico: {scenario['id']} {width}x{height}: {digests}"
                        )
                    assert first is not None
                    target = output / "images" / f"{scenario['id']}-{width}x{height}.png"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(first, target)
                    from PIL import Image
                    with Image.open(target) as image:
                        actual_size = list(image.size)
                        image.verify()
                    if actual_size != [width, height]:
                        raise GoldenMasterError(f"Dimensão PNG divergente: {target.name}")
                    artifacts.append({
                        "file": target.relative_to(output).as_posix(),
                        "width": width,
                        "height": height,
                        "sha256": digests[0],
                        "size_bytes": target.stat().st_size,
                        "repeat_count": repeat,
                    })
                records.append({
                    "id": scenario["id"],
                    "description": scenario["description"],
                    "state_file": state_path.relative_to(output).as_posix(),
                    "state_sha256": sha256_file(state_path),
                    "canonical_state_digest": canonical_digest(logical),
                    "asset": asset_record,
                    "artifacts": artifacts,
                })
        finally:
            driver.quit()
    manifest = {
        "schema_version": 1,
        "suite_id": scenarios["suite_id"],
        "milestone": "M9.0",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "distribution": "local_only_non_redistributable",
        "license_status": "card_editor_pending_before_external_publication_or_redistribution",
        "reference_renderer": scenarios["reference_renderer"],
        "environment": versions,
        "font_loads": font_loads,
        "component_files": component_files,
        "fonts": fonts,
        "synthetic_asset": synthetic,
        "service_assets": [
            {key: value for key, value in service_assets[item].items() if key != "runtime_path"}
            for item in sorted(service_assets)
        ],
        "scenarios": records,
    }
    write_json(output / "GOLDEN_MANIFEST.json", manifest)
    verify_existing(output, architecture, contract, scenarios)
    return manifest


def verify_existing(
    output: Path, architecture: dict[str, Any] | None = None,
    contract: dict[str, Any] | None = None, scenarios: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output = output.expanduser().resolve()
    architecture = architecture or load_json(ARCHITECTURE_PATH)
    contract = contract or load_json(EDITOR_CONTRACT_PATH)
    scenarios = scenarios or load_json(SCENARIOS_PATH)
    manifest = load_json(output / "GOLDEN_MANIFEST.json")
    if manifest.get("milestone") != "M9.0" or manifest.get("distribution") != "local_only_non_redistributable":
        raise GoldenMasterError("Manifesto golden fora do contrato M9.0.")
    if manifest.get("reference_renderer") != architecture.get("render_authority"):
        raise GoldenMasterError("Autoridade de render divergente no manifesto golden.")
    expected_ids = [row["id"] for row in scenarios["scenarios"]]
    records = manifest.get("scenarios")
    if not isinstance(records, list) or [row.get("id") for row in records] != expected_ids:
        raise GoldenMasterError("Cenários do manifesto golden divergentes.")
    artifact_count = 0
    for row in records:
        state_path = (output / str(row["state_file"])).resolve()
        try:
            state_path.relative_to(output)
        except ValueError as exc:
            raise GoldenMasterError("Estado golden fora do diretório autorizado.") from exc
        if not state_path.is_file() or sha256_file(state_path) != row["state_sha256"]:
            raise GoldenMasterError(f"Estado golden ausente ou alterado: {row['id']}")
        state = load_json(state_path)
        validate_editor_state(state, contract)
        if canonical_digest(state) != row["canonical_state_digest"]:
            raise GoldenMasterError(f"Digest canônico divergente: {row['id']}")
        for artifact in row.get("artifacts", []):
            path = (output / str(artifact["file"])).resolve()
            try:
                path.relative_to(output)
            except ValueError as exc:
                raise GoldenMasterError("Imagem golden fora do diretório autorizado.") from exc
            if not path.is_file() or sha256_file(path) != artifact["sha256"]:
                raise GoldenMasterError(f"Imagem golden ausente ou alterada: {artifact['file']}")
            from PIL import Image
            with Image.open(path) as image:
                dimensions = [image.width, image.height]
                image.verify()
            if dimensions != [artifact["width"], artifact["height"]]:
                raise GoldenMasterError(f"Dimensão golden divergente: {artifact['file']}")
            if int(artifact.get("repeat_count") or 0) < 2:
                raise GoldenMasterError(f"Prova de determinismo ausente: {artifact['file']}")
            artifact_count += 1
    expected_artifacts = sum(len(row["resolutions"]) for row in scenarios["scenarios"])
    if artifact_count != expected_artifacts:
        raise GoldenMasterError(
            f"Quantidade de imagens golden divergente: {artifact_count}, esperado {expected_artifacts}."
        )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="Diretório local fornecido do Card Editor v1.1.0")
    parser.add_argument("--app-root", type=Path, default=ROOT, help="Raiz desta instalação FR AutoEdite")
    parser.add_argument("--output", required=True, type=Path, help="Diretório local e ignorado para os goldens")
    parser.add_argument("--download-fonts", action="store_true", help="Baixa fontes OFL fixadas apenas no cache local")
    parser.add_argument("--verify-only", action="store_true", help="Somente verifica um conjunto já gerado")
    parser.add_argument("--chromium", default=shutil.which("chromium") or "chromium")
    parser.add_argument("--chromedriver", default=shutil.which("chromedriver") or "chromedriver")
    args = parser.parse_args()
    try:
        if args.verify_only:
            manifest = verify_existing(args.output)
        else:
            if args.source is None:
                raise GoldenMasterError("--source é obrigatório para gerar golden masters.")
            manifest = generate(
                args.source, args.app_root, args.output,
                download_fonts=args.download_fonts,
                chromium=args.chromium, chromedriver=args.chromedriver,
            )
    except GoldenMasterError as exc:
        parser.error(str(exc))
    artifacts = sum(len(row.get("artifacts", [])) for row in manifest.get("scenarios", []))
    print(f"M9.0 GOLDEN OK: {len(manifest.get('scenarios', []))} cenários, {artifacts} PNGs.")
    print(f"Manifesto local: {(args.output / 'GOLDEN_MANIFEST.json').resolve()}")
    print("Distribuição: local_only_non_redistributable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
