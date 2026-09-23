#!/usr/bin/env python3
"""Gera amostras motion F3 com a coreografia quiet luxury."""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from fr_v4.core.card_renderer import CardSpec, compose
from fr_v4.core.config import SERVICE_BY_KEY, DESIGN_VERSION
from fr_v4.motion.renderer import render


def valid(path: Path) -> bool:
    if not path.is_file(): return False
    result = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                             "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=False)
    return result.returncode == 0 and "1080,1920" in result.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--servicos", default="alvenaria,criacoes,eletrica")
    parser.add_argument("--saida", type=Path, default=ROOT / "entrega/FR_CARDS_v2.0.0/motion")
    args = parser.parse_args()
    services = [item.strip() for item in args.servicos.split(",") if item.strip()]
    for key in services:
        if key not in SERVICE_BY_KEY: raise SystemExit(f"Serviço inválido: {key}")
        service = SERVICE_BY_KEY[key]
        target = args.saida / f"FR_F3_{key.upper()}_9X16_MOTION_v{DESIGN_VERSION}.mp4"
        if valid(target):
            print(f"mantido: {target}"); continue
        target.unlink(missing_ok=True)
        composition = compose(CardSpec("F3", service.label, "Técnica aplicada com precisão.", service_key=key),
                              (1080, 1920), ROOT)
        try:
            render(composition, target, duration=3., fps=24)
        finally:
            for layer in composition.layers.values(): layer.close()
        print(f"gerado: {target}")
    return 0


if __name__ == "__main__": raise SystemExit(main())

