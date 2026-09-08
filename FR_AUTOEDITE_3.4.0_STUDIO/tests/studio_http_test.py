#!/usr/bin/env python3
"""Teste HTTP das rotas do Studio 3.4.0, incluindo IA e Google Takeout."""

from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import threading
import time
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def load_studio(app_root: Path):
    spec = importlib.util.spec_from_file_location("fr_studio_test", app_root / "app" / "studio.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Não foi possível carregar o Studio.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def request(url: str, token: str = "", data: bytes | None = None, headers: dict[str, str] | None = None):
    request_headers = dict(headers or {})
    if token:
        request_headers["X-FR-Token"] = token
    call = Request(
        url,
        data=data,
        headers=request_headers,
        method="POST" if data is not None else "GET",
    )
    with urlopen(call, timeout=15) as response:
        body = response.read()
        if response.headers.get_content_type() == "application/json":
            return json.loads(body)
        return body


def wait_for_job(state, project: Path, timeout: float = 45.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with state.lock:
            job = dict(state.jobs.get(project.name, {}))
        if job and not job.get("running"):
            return job
        time.sleep(0.08)
    raise AssertionError("A tarefa do Studio não terminou dentro do limite.")


def main() -> int:
    app_root = Path(__file__).resolve().parents[1]
    studio = load_studio(app_root)
    with tempfile.TemporaryDirectory(prefix="fr-studio-http-") as temporary:
        state = studio.StudioState(app_root, Path(temporary) / "Studio")
        server = ThreadingHTTPServer(("127.0.0.1", 0), studio.StudioHandler)
        server.state = state
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            html = request(base + "/").decode("utf-8")
            assert "Editar Reels" in html and "Roteiro Mestre" in html
            assert "Enviar à IA" in html and "GOOGLE TAKEOUT + JSON" in html
            assert "Time-lapse" in html and "clip-path:circle" in html
            assert "Galeria" in html and "Gerenciar" in html
            assert 'id="reviewPlayer"' in html and 'class="log-rail"' in html

            created = request(
                base + "/api/project",
                state.token,
                json.dumps({"name": "Projeto HTTP 3.3"}).encode(),
                {"Content-Type": "application/json"},
            )
            slug = created["project"]["slug"]
            project_query = urlencode({"project": slug})
            project = state.project_dir(slug)

            # Regressão 3.2.3: cards pré-preparo e autorreparo de estilo antigo.
            (project / "CARD_STYLE.json").write_text(
                json.dumps({"palette": {"background": "cor-invalida"}}), encoding="utf-8"
            )
            state.start_job(project, "cards")
            card_job = wait_for_job(state, project)
            assert card_job["returncode"] == 0, "\n".join(card_job.get("log", []))
            assert (project / "CARD_PREVIEW_PLAN.json").is_file()
            assert not (project / "EDIT_PLAN.json").exists()
            assert len(list((project / "cards_editaveis").rglob("*.png"))) >= 3
            assert len(list((project / "_HISTORICO").glob("CARD_STYLE_INVALIDO_*.json"))) == 1

            image = (app_root / "assets" / "services" / "iluminacao.png").read_bytes()

            # Regressão 3.2.4: sem ZIP, orientar sem deixar a tarefa presa.
            try:
                state.start_job(project, "brief-generate")
            except studio.StudioError as exc:
                assert "envie o ZIP" in str(exc)
            else:
                raise AssertionError("Gerar Markdown sem ZIP deveria orientar o usuário.")
            assert not state.jobs.get(project.name, {}).get("running")

            # Google Takeout: o ZIP original é preservado e os JSONs restauram
            # a data no ZIP normalizado usado como entrada do projeto.
            takeout = io.BytesIO()
            with zipfile.ZipFile(takeout, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("Takeout/Google Fotos/Projeto/iluminacao.png", image)
                archive.writestr(
                    "Takeout/Google Fotos/Projeto/iluminacao.png.json",
                    json.dumps({
                        "title": "iluminacao.png",
                        "photoTakenTime": {"timestamp": "1714566896"},
                    }),
                )
            uploaded_takeout = request(
                base + "/api/takeout-upload?" + project_query,
                state.token,
                takeout.getvalue(),
                {"X-Filename": "takeout.zip", "Content-Type": "application/zip"},
            )
            assert uploaded_takeout["ok"] is True
            state.start_job(project, "takeout-normalize")
            takeout_job = wait_for_job(state, project, timeout=90.0)
            assert takeout_job["returncode"] == 0, "\n".join(takeout_job.get("log", []))
            takeout_report = json.loads((project / "RELATORIO_GOOGLE_TAKEOUT.json").read_text())
            assert takeout_report["summary"]["dates_restored_from_json"] == 1
            assert (project / "_TAKEOUT" / "00_NAO_EDITAR_GOOGLE_TAKEOUT_ORIGINAL.zip").is_file()
            assert (project / "_TAKEOUT" / "01_RELATORIO_GOOGLE_TAKEOUT.md").is_file()

            # Com ZIP, o botão prepara o projeto e gera um Markdown baixável.
            zipped = io.BytesIO()
            with zipfile.ZipFile(zipped, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("resultado/iluminacao.png", image)
            uploaded_zip = request(
                base + "/api/upload?" + project_query,
                state.token,
                zipped.getvalue(),
                {"Content-Type": "application/zip"},
            )
            assert uploaded_zip["ok"] is True
            state.start_job(project, "brief-generate")
            brief_job = wait_for_job(state, project, timeout=90.0)
            assert brief_job["returncode"] == 0, "\n".join(brief_job.get("log", []))
            generated_brief = project / "_ENVIAR_IA" / "01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE_IA.md"
            assert generated_brief.is_file()
            downloaded_brief = request(
                base + "/api/file?" + urlencode({
                    "token": state.token,
                    "project": slug,
                    "path": "_ENVIAR_IA/01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE_IA.md",
                })
            ).decode("utf-8")
            assert "FR_AUTOEDITE_JSON_BEGIN" in downloaded_brief
            range_call = Request(
                base + "/api/file?" + urlencode({
                    "token": state.token,
                    "project": slug,
                    "path": "_ENVIAR_IA/01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE_IA.md",
                }),
                headers={"Range": "bytes=0-31", "X-FR-Token": state.token},
            )
            with urlopen(range_call, timeout=15) as range_response:
                assert range_response.status == 206
                assert len(range_response.read()) == 32
                assert range_response.headers["Accept-Ranges"] == "bytes"
                assert range_response.headers["Content-Range"].startswith("bytes 0-31/")

            uploaded = request(
                base + "/api/asset-upload?" + project_query + "&kind=intro",
                state.token,
                image,
                {"X-Filename": "abertura.png", "Content-Type": "image/png"},
            )
            assert uploaded["config"]["external_intro_outro"]["intro_enabled"] is True

            # Reenvia o contrato gerado pela própria Central como uma resposta
            # válida da IA; um JSON vazio deve continuar sendo rejeitado pelo
            # validador antes de alterar o projeto.
            brief = generated_brief.read_bytes()
            response = request(
                base + "/api/editing-brief-upload?" + project_query,
                state.token,
                brief,
                {"Content-Type": "text/markdown"},
            )
            assert response["ok"] is True

            plan = {
                "segments": [{
                    "segment_id": "S0001", "type": "card", "card_kind": "intro",
                    "duration_sec": 2, "title": "Teste", "body": "HTTP",
                }]
            }
            payload = json.dumps({"plan": plan}).encode()
            for _ in range(2):
                response = request(
                    base + "/api/plan?" + project_query,
                    state.token,
                    payload,
                    {"Content-Type": "application/json"},
                )
            assert response["ok"] is True

            media_id = next(
                row["id"] for row in json.loads((project / "MANIFESTO_MEDIA.json").read_text())
                ["media"] if row.get("status", "ok") == "ok"
            )
            reel = {
                "social_target_sec": 30,
                "segments": [
                    {
                        "segment_id": "R0001", "type": "card", "card_kind": "intro",
                        "duration_sec": 2, "title": "Reel", "body": "Teste",
                    },
                    {
                        "segment_id": "R0002", "type": "media", "media_id": media_id,
                        "media_type": "image", "duration_sec": 3, "coverage_role": "inicio",
                    },
                    {
                        "segment_id": "R0003", "type": "media", "media_id": media_id,
                        "media_type": "image", "duration_sec": 3, "coverage_role": "fim",
                    },
                ],
            }
            response = request(
                base + "/api/reel-plan?" + project_query,
                state.token,
                json.dumps({"plan": reel}).encode(),
                {"Content-Type": "application/json"},
            )
            assert response["ok"] is True

            snapshot = request(
                base + "/api/state?" + urlencode({"token": state.token, "project": slug})
            )
            assert snapshot["application_version"] == "3.4.0"
            assert len(snapshot["service_catalog"]) == 9
            assert snapshot["config"]["cards"]["style_preset"] == "site_fr_luxo"
            assert any(item["role"] == "edit_return" and item["exists"] for item in snapshot["ai_files"])
            assert "30" in snapshot["reel_plans"]
            assert (project / "_ENTRADA" / "INTRO_PERSONALIZADA.png").is_file()
            assert (project / "_ENTRADA" / "ROTEIRO_MESTRE_RESPONDIDO.md").is_file()
            assert len(list((project / "_HISTORICO").glob("EDIT_PLAN_*.json"))) == 2

            # Galeria e limpeza segura: cards são regeneráveis, originais não.
            library = request(base + "/api/library?" + urlencode({"token": state.token, "project": slug}))
            assert library["ok"] is True
            assert any(item["category"] == "cards" for item in library["gallery"])
            assert any(item["relative"].startswith("originais/") for item in library["files"])
            assert all(not item["relative"].startswith("originais/") for item in library["cleanup_candidates"])
            cleanup = library["cleanup_candidates"]
            assert cleanup
            selected = cleanup[0]["relative"]
            cleaned = request(
                base + "/api/trash-files?" + project_query,
                state.token,
                json.dumps({"paths": [selected]}).encode(),
                {"Content-Type": "application/json"},
            )
            assert cleaned["result"]["files"] == 1
            assert not (project / selected).exists()
            restored = request(
                base + "/api/restore-trash?" + project_query,
                state.token,
                b"{}",
                {"Content-Type": "application/json"},
            )
            assert restored["result"]["restored"] == 1
            assert (project / selected).is_file()

            # Projetos são movidos a uma lixeira própria e podem ser restaurados.
            disposable = state.create_project("Projeto para restaurar")
            disposable_slug = disposable["slug"]
            moved = request(
                base + "/api/trash-project?" + urlencode({"project": disposable_slug}),
                state.token,
                json.dumps({"confirmation": disposable_slug}).encode(),
                {"Content-Type": "application/json"},
            )
            assert not state.project_dir(disposable_slug).exists()
            restored_project = request(
                base + "/api/restore-project",
                state.token,
                json.dumps({"trash_id": moved["result"]["id"]}).encode(),
                {"Content-Type": "application/json"},
            )
            assert restored_project["project"]["slug"] == disposable_slug
            assert state.project_dir(disposable_slug).is_dir()
            assert (project / "_CONTROLE" / "STUDIO_JOB_STATUS.json").is_file()
        finally:
            server.shutdown()
            server.server_close()
    print("STUDIO HTTP TEST OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
