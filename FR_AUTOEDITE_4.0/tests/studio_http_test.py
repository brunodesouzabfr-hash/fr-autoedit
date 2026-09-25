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
from urllib.error import HTTPError
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
            assert 'id="reviewModal"' in html and 'id="reviewTimeline"' in html
            assert "Gerar/atualizar PACOTE_PARA_IA" in html
            assert "Transformar em serviço" in html
            assert "Editar conteúdo" in html
            assert "fr-autoedite-card-content/1" in html
            assert 'id="cardContentModal"' in html
            assert 'id="cardEditorFrame"' in html
            assert "FR CARD EDITOR UNIVERSAL v1.1.0" in html
            assert "applyPolledMainPlan" in html
            assert "applyPolledReadyPlan" in html
            assert "Alterações não salvas da timeline foram preservadas" in html
            assert "Alterações não salvas dos overlays foram preservadas" in html
            assert "Editar conteúdo no Card Editor" in html
            assert "readyCardEditorCapability" in html
            assert "else{plan=d.plan;mainPlanDirty=false" not in html
            assert "persistMainPlan(true)" in html
            assert "&v=" in html
            assert "NÃO USADA" in html

            try:
                request(base + "/card-editor/")
            except HTTPError as exc:
                assert exc.code == 403
            else:
                raise AssertionError("O Card Editor integrado deveria exigir o token local.")
            editor_html = request(base + "/card-editor/", state.token).decode("utf-8")
            editor_call = Request(
                base + "/card-editor/", headers={"X-FR-Token": state.token},
            )
            with urlopen(editor_call, timeout=15) as editor_response:
                editor_csp = editor_response.headers["Content-Security-Policy"]
                assert "frame-ancestors 'self'" in editor_csp
                assert "connect-src 'none'" in editor_csp
            assert "FR Card Editor Universal v1.1.0" in editor_html
            assert 'id="fr-autoedite-bridge"' in editor_html
            assert "fr-autoedite:load-card" in editor_html
            assert "editor modular abaixo é uma referência visual" not in editor_html
            assert "Prévia visual de referência" in editor_html
            assert "localStorage.getItem" not in editor_html
            assert "localStorage.setItem" not in editor_html
            assert "fonts.googleapis.com" not in editor_html
            assert "/card-editor/assets/background-fr-hd.png?token=" in editor_html
            editor_asset = request(
                base + "/card-editor/assets/logo-fr.png", state.token,
            )
            assert editor_asset.startswith(b"\x89PNG\r\n\x1a\n")
            try:
                request(base + "/card-editor/assets/nao-permitido.png", state.token)
            except HTTPError as exc:
                assert exc.code == 404
            else:
                raise AssertionError("O allowlist de assets do Card Editor deveria rejeitar nomes desconhecidos.")

            created = request(
                base + "/api/project",
                state.token,
                json.dumps({"name": "Projeto HTTP 3.3"}).encode(),
                {"Content-Type": "application/json"},
            )
            slug = created["project"]["slug"]
            project_query = urlencode({"project": slug})
            project = state.project_dir(slug)
            initial_state = request(base + "/api/state?" + project_query, state.token)
            editor_capability = initial_state["capabilities"]["card_editor"]
            assert editor_capability["available"] is True
            assert editor_capability["integration_mode"] == "same_origin_iframe_content_only"
            assert editor_capability["supported_fields"] == ["title", "body"]
            assert editor_capability["provenance"] == "user_supplied_local_publication_pending"

            # Regressão 3.2.3: cards pré-preparo e autorreparo de estilo antigo.
            (project / "CARD_STYLE.json").write_text(
                json.dumps({"palette": {"background": "cor-invalida"}}), encoding="utf-8"
            )
            state.start_job(project, "cards")
            card_job = wait_for_job(state, project, timeout=90.0)
            assert card_job["returncode"] == 0, "\n".join(card_job.get("log", []))
            assert any("Cards 1/" in line for line in card_job.get("log", []))
            assert (project / "CARD_PREVIEW_PLAN.json").is_file()
            assert not (project / "EDIT_PLAN.json").exists()
            assert len(list((project / "cards_editaveis").rglob("*.png"))) >= 3
            assert len(list((project / "_HISTORICO").glob("CARD_STYLE_INVALIDO_*.json"))) == 1
            preview_state = state.project_state(project)
            assert preview_state["card_previews"]
            assert all(item.get("version") for item in preview_state["card_previews"])
            assert len({item.get("generation_id") for item in preview_state["card_previews"]}) == 1

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
            repeated_zip = request(
                base + "/api/upload?" + project_query,
                state.token,
                zipped.getvalue(),
                {"Content-Type": "application/zip"},
            )
            assert repeated_zip["duplicate"] is True
            state.start_job(project, "brief-generate")
            brief_job = wait_for_job(state, project, timeout=90.0)
            assert brief_job["returncode"] == 0, "\n".join(brief_job.get("log", []))
            generated_brief = project / "_ENVIAR_IA" / "01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE_IA.md"
            assert generated_brief.is_file()
            canonical_package = project / "PACOTE_PARA_IA"
            assert (canonical_package / "01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE.md").is_file()
            assert (canonical_package / "03_NAO_EDITAR_LOTES_DE_PROXIES").is_dir()
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
            repeated_response = request(
                base + "/api/editing-brief-upload?" + project_query,
                state.token,
                brief,
                {"Content-Type": "text/markdown"},
            )
            assert repeated_response["duplicate"] is True

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

            card = request(
                base + "/api/card-content?" + urlencode({
                    "token": state.token, "project": slug, "segment_id": "S0001",
                })
            )["card"]
            assert card["adapter_version"] == "fr-autoedite-card-content/1"
            assert card["fields"] == {"title": "Teste", "body": "HTTP"}
            assert card["source"]["card_kind"] == "intro"
            assert card["capabilities"]["supported_fields"] == ["title", "body"]
            before_invalid = (project / "EDIT_PLAN.json").read_bytes()
            invalid = {
                "adapter_version": card["adapter_version"],
                "base_revision": card["base_revision"],
                "segment_id": "S0001",
                "fields": {"title": "Não aplicar", "body": "Não aplicar"},
                "geometry": {"x": 10},
            }
            try:
                request(
                    base + "/api/card-content?" + project_query,
                    state.token,
                    json.dumps(invalid).encode(),
                    {"Content-Type": "application/json"},
                )
            except HTTPError as exc:
                assert exc.code == 400
                error = json.loads(exc.read())
                assert "não suportado: geometry" in error["error"]
            else:
                raise AssertionError("Geometria fora do adapter deveria ser rejeitada.")
            assert (project / "EDIT_PLAN.json").read_bytes() == before_invalid

            edited = request(
                base + "/api/card-content?" + project_query,
                state.token,
                json.dumps({
                    "adapter_version": card["adapter_version"],
                    "base_revision": card["base_revision"],
                    "segment_id": "S0001",
                    "fields": {"title": "Título manual", "body": "Corpo manual"},
                }).encode(),
                {"Content-Type": "application/json"},
            )
            assert edited["ok"] is True and edited["preview_job_started"] is True
            preview_job = wait_for_job(state, project, timeout=90.0)
            assert preview_job["returncode"] == 0, "\n".join(preview_job.get("log", []))
            persisted = json.loads((project / "EDIT_PLAN.json").read_text())
            persisted_card = next(item for item in persisted["segments"] if item["segment_id"] == "S0001")
            assert persisted_card["title"] == "Título manual"
            assert persisted_card["body"] == "Corpo manual"
            assert persisted_card["card_kind"] == "intro"
            reloaded = request(
                base + "/api/card-content?" + urlencode({
                    "token": state.token, "project": slug, "segment_id": "S0001",
                })
            )["card"]
            assert reloaded["fields"] == {"title": "Título manual", "body": "Corpo manual"}
            preview_registry = json.loads(
                (project / "_CONTROLE" / "CARD_PREVIEWS.json").read_text()
            )
            preview = next(item for item in preview_registry["previews"] if item["segment_id"] == "S0001")
            assert (project / preview["relative"]).is_file()

            try:
                request(
                    base + "/api/card-content?" + project_query,
                    state.token,
                    json.dumps({
                        "adapter_version": card["adapter_version"],
                        "base_revision": card["base_revision"],
                        "segment_id": "S0001",
                        "fields": {"title": "Stale", "body": "Stale"},
                    }).encode(),
                    {"Content-Type": "application/json"},
                )
            except HTTPError as exc:
                assert exc.code == 400
                assert "mudou desde" in json.loads(exc.read())["error"]
            else:
                raise AssertionError("Uma revisão antiga deveria ser rejeitada.")
            assert json.loads((project / "EDIT_PLAN.json").read_text())["segments"][0]["title"] == "Título manual"

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
            assert snapshot["application_version"] == (app_root / "VERSION").read_text(encoding="utf-8").strip()
            assert len(snapshot["service_catalog"]) >= 13
            assert snapshot["config"]["cards"]["style_preset"] == "site_fr_luxo"
            assert any(item["role"] == "edit_return" and item["exists"] for item in snapshot["ai_files"])
            assert "artifact_conflicts" in snapshot
            assert "30" in snapshot["reel_plans"]
            assert (project / "_ENTRADA" / "INTRO_PERSONALIZADA.png").is_file()
            assert (project / "_ENTRADA" / "ROTEIRO_MESTRE_RESPONDIDO.md").is_file()
            # Duas gravações da timeline + a edição content-only, todas pelo
            # mesmo mecanismo de backup de save_plan().
            assert len(list((project / "_HISTORICO").glob("EDIT_PLAN_*.json"))) == 3

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
