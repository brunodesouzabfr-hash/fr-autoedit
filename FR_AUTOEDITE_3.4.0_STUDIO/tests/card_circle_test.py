#!/usr/bin/env python3
"""Regressão visual geométrica: medalhões de serviço nunca podem virar ovais."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from PIL import Image


def main() -> int:
    app_root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("fr_autoedite_circle_test", app_root / "app" / "fr_autoedite.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Não foi possível carregar o FR AutoEdite.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    canvas = Image.new("RGBA", (600, 600), (0, 0, 0, 0))
    ok = module.paste_service_symbol(
        canvas,
        app_root / "assets" / "services" / "iluminacao.png",
        (300, 300),
        400,
        "#FC7016",
        "#F6A700",
        "#1A6069",
    )
    assert ok
    alpha = canvas.getchannel("A")
    bounds = alpha.getbbox()
    assert bounds is not None
    width, height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    assert abs(width - height) <= 1, bounds
    assert alpha.getpixel((100, 100)) == 0
    assert alpha.getpixel((300, 101)) > 0
    assert alpha.getpixel((101, 300)) > 0
    assert alpha.getpixel((499, 300)) > 0
    assert alpha.getpixel((300, 499)) > 0
    print("CARD CIRCLE TEST OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
