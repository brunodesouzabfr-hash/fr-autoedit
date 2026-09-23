#!/usr/bin/env python3
"""Regressão: uma preparação interrompida deve reutilizar trabalho concluído."""

from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
from pathlib import Path


def main() -> int:
    app_root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("fr_resume_test", app_root / "app" / "fr_autoedite.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Não foi possível carregar o FR AutoEdite.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    with tempfile.TemporaryDirectory(prefix="fr-resume-") as temporary:
        project = Path(temporary) / "projeto"
        originals = project / "originais"
        originals.mkdir(parents=True)
        shutil.copy2(app_root / "assets" / "services" / "iluminacao.png", originals / "imagem.png")
        answers = module.normalize_answers(json.loads(
            (app_root / "templates" / "questionario_base.json").read_text(encoding="utf-8")
        ))
        answers["project"].update({"name": "Teste de retomada", "slug": "teste-retomada"})
        answers["local_analysis"]["enabled"] = False

        first = module.build_manifest(project, answers)
        row = first["media"][0]
        proxy = project / row["proxy_path"]
        thumbnail = project / row["thumbnail_path"]
        assert proxy.is_file() and thumbnail.is_file()
        proxy_stamp = proxy.stat().st_mtime_ns
        thumbnail_stamp = thumbnail.stat().st_mtime_ns

        original_proxy = module.create_image_proxy
        original_thumbnail = module.create_thumbnail

        def forbidden_proxy(*_args, **_kwargs):
            raise AssertionError("O proxy concluído foi recriado em vez de reutilizado.")

        def forbidden_thumbnail(*_args, **_kwargs):
            raise AssertionError("A miniatura concluída foi recriada em vez de reutilizada.")

        module.create_image_proxy = forbidden_proxy
        module.create_thumbnail = forbidden_thumbnail
        second = module.build_manifest(project, answers)
        assert second["summary"]["source_total"] == 1
        assert proxy.stat().st_mtime_ns == proxy_stamp
        assert thumbnail.stat().st_mtime_ns == thumbnail_stamp

        # Se apenas a miniatura estiver ausente, o proxy pronto continua
        # preservado e somente o arquivo faltante é reconstruído.
        thumbnail.unlink()
        calls = {"thumbnail": 0}

        def counted_thumbnail(*args, **kwargs):
            calls["thumbnail"] += 1
            return original_thumbnail(*args, **kwargs)

        module.create_image_proxy = forbidden_proxy
        module.create_thumbnail = counted_thumbnail
        third = module.build_manifest(project, answers)
        assert third["summary"]["source_total"] == 1
        assert calls["thumbnail"] == 1
        assert proxy.stat().st_mtime_ns == proxy_stamp
        checkpoint = json.loads(
            (project / "_CONTROLE" / "PREPARACAO_CHECKPOINT.json").read_text(encoding="utf-8")
        )
        assert checkpoint["status"] == "complete"
        assert checkpoint["completed"] == checkpoint["total"] == 1

        module.create_image_proxy = original_proxy
        module.create_thumbnail = original_thumbnail
    print("PREPARATION RESUME TEST OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

