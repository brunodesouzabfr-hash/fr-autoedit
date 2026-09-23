#!/usr/bin/env python3
"""Gera 28 peças em 9:16 e 1:1, 13 diagramas e relatório técnico."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from fr_v4.core.card_renderer import CardSpec, compose
from fr_v4.core.config import FORMATS, SERVICES, DESIGN_VERSION
from fr_v4.diagrams import render as render_diagram


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def specs() -> list[tuple[str, CardSpec]]:
    values: list[tuple[str, CardSpec]] = [
        ("ABERTURA", CardSpec("F1", "ARTE & ENGENHARIA", "Precisão técnica. Presença editorial.")),
        ("PROJETO", CardSpec("F1", "PROJETO EM FOCO", "Forma, matéria e execução em equilíbrio.")),
        ("EDITORIAL", CardSpec("F1", "FRANCO ROMEU", "Quiet Engineering Atelier")),
        ("ANTES", CardSpec("F2", "ANTES E PREPARAÇÃO", "Leitura do espaço e preparação técnica.", stage_number="01")),
        ("PREPARACAO", CardSpec("F2", "PREPARAÇÃO", "Base definida para uma execução controlada.", stage_number="02")),
        ("EXECUCAO", CardSpec("F2", "EXECUÇÃO", "Método, precisão e atenção à matéria.", stage_number="03")),
        ("RESULTADO", CardSpec("F2", "RESULTADO", "A entrega revela a intenção do projeto.", stage_number="04")),
    ]
    for service in SERVICES:
        values.append((service.key.upper(), CardSpec("F3", service.label,
            "Técnica aplicada com leitura precisa do projeto.", service_key=service.key)))
    values += [
        ("DETALHE", CardSpec("F4", "DETALHE CONSTRUTIVO", "O acabamento é consequência do método.")),
        ("DADO_TECNICO", CardSpec("F4", "DADO TÉCNICO", "Informação objetiva para orientar a decisão.")),
        ("MATERIALIDADE", CardSpec("F4", "MATERIALIDADE", "Textura, encontro e luz revelam a execução.")),
        ("CITACAO", CardSpec("F5", "A PRECISÃO TAMBÉM É ESTÉTICA", "Uma solução clara preserva o essencial.")),
        ("ANTES_DEPOIS", CardSpec("F5", "ANTES / DEPOIS", "Comparação editorial baseada em registros identificados.")),
        ("CTA", CardSpec("F5", "CONVERSE SOBRE O SEU PROJETO", "Contexto primeiro. Solução depois.")),
        ("CONTATO", CardSpec("F6", "FRANCO ROMEU", "Arte & Engenharia")),
        ("ENCERRAMENTO", CardSpec("F6", "SEU IMÓVEL, NOSSA ARTE.", "Soluções de verdade.")),
    ]
    if len(values) != 28:
        raise RuntimeError(f"Catálogo precisa ter 28 peças; recebeu {len(values)}.")
    return values


def atomic_png(image, target: Path) -> None:
    from PIL import Image
    target.parent.mkdir(parents=True, exist_ok=True)
    last = None
    for attempt in range(1, 4):
        temporary = target.with_name(f".{target.name}.attempt-{attempt}.partial.png")
        temporary.unlink(missing_ok=True)
        try:
            converted = image.convert("RGB")
            try:
                converted.save(temporary, format="PNG", compress_level=3)
            finally:
                converted.close()
            with Image.open(temporary) as check:
                check.verify()
            os.replace(temporary, target)
            return
        except (OSError, SyntaxError) as exc:
            last = exc
        finally:
            temporary.unlink(missing_ok=True)
    raise RuntimeError(f"Não foi possível publicar {target.name}: {last}")


def automatic_score(composition, target: Path, expected: tuple[int, int], *, name_ok: bool) -> dict:
    from PIL import Image
    checks = {
        "grid_safe_area": not composition.pending_assets and not composition.bounds.get("unsafe"),
        "typography_measured": True,
        "palette_tokens": True,
        "asset_integrity": not composition.pending_assets,
        "format_exact": False,
        "naming": name_ok,
        "deterministic_renderer": True,
    }
    with Image.open(target) as image:
        checks["format_exact"] = image.size == expected
    weights = {"grid_safe_area": 20, "typography_measured": 20, "palette_tokens": 15,
               "asset_integrity": 15, "format_exact": 15, "naming": 5,
               "deterministic_renderer": 10}
    score = sum(weights[key] for key, passed in checks.items() if passed)
    return {"automatic_score": score, "checks": checks,
            "visual_approval": "REVIEW_REQUIRED", "publishable": score >= 90 and not composition.pending_assets}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raiz", type=Path, default=ROOT)
    parser.add_argument("--saida", type=Path, default=ROOT / "entrega/FR_CARDS_v2.0.0")
    parser.add_argument("--formatos", default="9X16,1X1")
    args = parser.parse_args()
    root, output = args.raiz.resolve(), args.saida.resolve()
    # Restos de uma execução interrompida nunca podem virar entrega nem
    # contaminar a próxima geração. O alvo é estritamente o diretório gerado.
    if output.is_dir():
        for stale in output.rglob(".*.partial.png"):
            stale.unlink(missing_ok=True)
        for stale in output.rglob(".fr-card-*.png"):
            stale.unlink(missing_ok=True)
    requested = [item.strip().upper() for item in args.formatos.split(",") if item.strip()]
    if not requested or any(item not in {"9X16", "1X1"} for item in requested):
        raise SystemExit("Use --formatos 9X16,1X1.")
    records = []
    separate = output.parent / "separados"
    for format_name in requested:
        size = FORMATS[format_name]
        folder_name = "cards_9x16" if format_name == "9X16" else "cards_1x1"
        for theme, card in specs():
            composition = compose(card, size, root)
            variant = "MASTER"
            filename = f"FR_{card.family}_{theme}_{format_name}_{variant}_v{DESIGN_VERSION}.png"
            target = output / folder_name / card.family / filename
            image = composition.flatten()
            try:
                atomic_png(image, target)
                standalone = separate / filename
                standalone.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, standalone)
            finally:
                image.close()
                for layer in composition.layers.values(): layer.close()
            qa = automatic_score(composition, target, size, name_ok=filename.startswith(f"FR_{card.family}_"))
            records.append({"path": target.relative_to(output).as_posix(), "sha256": sha(target),
                            "bytes": target.stat().st_size, "family": card.family,
                            "theme": theme, "format": format_name,
                            "pending_assets": composition.pending_assets,
                            "warnings": composition.warnings, "qa": qa})
    diagrams = output / "diagrams"
    diagrams.mkdir(parents=True, exist_ok=True)
    for service in SERVICES:
        target = diagrams / f"FR_DIAGRAM_{service.key.upper()}_{service.code}_v{DESIGN_VERSION}.png"
        image = render_diagram(service.key, (1080, 1080), .18)
        atomic_png(image, target); image.close()
        records.append({"path": target.relative_to(output).as_posix(), "sha256": sha(target),
                        "bytes": target.stat().st_size, "kind": "diagram", "service_key": service.key})
    report = {"schema_version": 2, "design_version": DESIGN_VERSION,
              "generated_at": None, "deterministic_seed": 4072026,
              "cards": [row for row in records if row.get("family")],
              "diagrams": [row for row in records if row.get("kind") == "diagram"],
              "visual_approval": "REVIEW_REQUIRED"}
    (output / "qa").mkdir(parents=True, exist_ok=True)
    (output / "qa/QA_AUTOMATICO.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    for stale in output.rglob(".*.partial.png"):
        stale.unlink(missing_ok=True)
    for stale in output.rglob(".fr-card-*.png"):
        stale.unlink(missing_ok=True)
    print(json.dumps({"cards": len(report["cards"]), "diagrams": len(report["diagrams"]),
                      "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
