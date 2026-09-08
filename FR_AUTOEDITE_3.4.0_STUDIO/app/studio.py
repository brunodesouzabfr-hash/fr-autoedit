#!/usr/bin/env python3
"""Studio visual local do FR AutoEdite 3.4.0.

Servidor restrito a 127.0.0.1. O navegador funciona como uma única central do
projeto: entrada, auditoria, ações, timeline e arquivos para entrega.
"""

from __future__ import annotations

import copy
import datetime as dt
import errno
import json
import mimetypes
import os
import queue
import re
import secrets
import signal
import shutil
import subprocess
import threading
import time
import webbrowser
import zipfile
import functools
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

# O Studio também é carregado diretamente pelos testes e por integrações que
# usam ``spec_from_file_location``.  Nesse caso o diretório ``app`` não fica
# automaticamente no ``sys.path``; explicitar o caminho torna o carregamento
# determinístico sem alterar a forma normal de execução.
import sys
_APP_DIR = str(Path(__file__).resolve().parent)
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

import project_scope


def serialized_mutation(fn):
    @functools.wraps(fn)
    def wrapped(self):
        with self.state.mutation_lock:
            return fn(self)
    return wrapped


class StudioError(RuntimeError):
    pass


def _slugify(value: str) -> str:
    import re
    import unicodedata

    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return normalized or "projeto-fr"


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


class StudioState:
    def __init__(self, app_root: Path, studio_root: Path) -> None:
        self.app_root = app_root.resolve()
        version_file = self.app_root / "VERSION"
        self.app_version = version_file.read_text(encoding="utf-8").strip() if version_file.is_file() else "3.4.0"
        self.studio_root = studio_root.expanduser().resolve()
        self.studio_root.mkdir(parents=True, exist_ok=True)
        self.launcher = self.app_root / "fr-autoedite"
        self.token = secrets.token_urlsafe(24)
        self.lock = threading.Lock()
        self.mutation_lock = threading.RLock()
        self.jobs: dict[str, dict[str, Any]] = {}
        self.processes: dict[str, subprocess.Popen[str]] = {}

    def project_dir(self, slug: str) -> Path:
        safe = _slugify(slug)
        path = (self.studio_root / safe).resolve()
        path.relative_to(self.studio_root)
        return path

    def list_projects(self) -> list[dict[str, Any]]:
        result = []
        for path in sorted(self.studio_root.iterdir(), key=lambda item: item.name):
            if not path.is_dir() or path.name.startswith("."):
                continue
            if not (path / "QUESTIONARIO_RESPONDIDO.json").is_file() and not (path / "MANIFESTO_MEDIA.json").is_file():
                continue
            questionnaire = path / "QUESTIONARIO_RESPONDIDO.json"
            name = path.name
            if questionnaire.is_file():
                try:
                    name = json.loads(questionnaire.read_text(encoding="utf-8")).get("project", {}).get("name") or name
                except Exception:
                    pass
            result.append({"slug": path.name, "name": name, "path": str(path)})
        return result

    def create_project(self, name: str) -> dict[str, Any]:
        slug = _slugify(name)
        project = self.project_dir(slug)
        project.mkdir(parents=True, exist_ok=True)
        for folder in ("_ENTRADA", "_EDITAR", "_ENVIAR_IA", "_ENVIAR_CHATGPT", "_TAKEOUT", "_HISTORICO"):
            (project / folder).mkdir(parents=True, exist_ok=True)
        template = json.loads((self.app_root / "templates" / "questionario_base.json").read_text(encoding="utf-8"))
        template["project"].update({
            "name": name.strip() or "Novo projeto Franco Romeu",
            "slug": slug,
            "zip_path": str(project / "_ENTRADA" / "FR_AUTOEDITE_ENTRADA.zip"),
            "workspace_root": str(self.studio_root),
            "context_file": str(project / "_ENTRADA" / "CONTEXTO_PROJETO.md"),
        })
        questionnaire = project / "QUESTIONARIO_RESPONDIDO.json"
        if not questionnaire.is_file():
            questionnaire.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        context = project / "_ENTRADA" / "CONTEXTO_PROJETO.md"
        if not context.is_file():
            context.write_text(
                f"# {template['project']['name']}\n\n"
                "Descreva aqui o objetivo, os fatos confirmados e a ordem real das etapas.\n\n"
                "1. CONCEPÇÃO | projeto, referências e medidas\n"
                "2. EXECUÇÃO | preparação, montagem e instalações\n"
                "3. RESULTADO | detalhes, testes e ambiente concluído\n",
                encoding="utf-8",
            )
        guide = project / "GUIA_INICIAL.md"
        if not guide.is_file():
            guide.write_text(
                "# Central do projeto FR AutoEdite\n\n"
                "1. IMPORTE o ZIP, o contexto e, se desejar, intro/outro personalizados.\n"
                "2. Em MONTAGEM, escolha formato, qualidade, duração e saídas.\n"
                "3. Em CARDS E MARCA, escolha o serviço e confira a prévia visual.\n"
                "4. Execute PREPARAR e revise o filme em REVISAR FILME.\n"
                "5. Revise separadamente os planos em EDITAR REELS.\n"
                "6. Opcional: abra ENVIAR À IA e gere `01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE_IA.md`.\n"
                "7. Gere o RASCUNHO por proxies e assista integralmente.\n"
                "8. Em ENTREGAR, renderize a master pelos originais e execute a auditoria.\n",
                encoding="utf-8",
            )
        return {"slug": slug, "name": template["project"]["name"], "path": str(project)}

    @staticmethod
    def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)

    @staticmethod
    def _job_status_path(project: Path) -> Path:
        return project / "_CONTROLE" / "STUDIO_JOB_STATUS.json"

    def _persist_job_locked(self, project: Path) -> None:
        job = copy.deepcopy(self.jobs.get(project.name, {}))
        if not job:
            return
        self._write_json_atomic(self._job_status_path(project), job)

    def _load_persisted_job(self, project: Path) -> dict[str, Any]:
        path = self._job_status_path(project)
        if not path.is_file():
            return {"running": False, "log": [], "returncode": None}
        try:
            job = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"running": False, "log": [], "returncode": None}
        if job.get("running"):
            job.update({
                "running": False,
                "returncode": 130,
                "interrupted": True,
                "finished_at": time.time(),
                "error_message": (
                    "A sessão anterior foi interrompida. Execute novamente: proxies e segmentos "
                    "já concluídos serão reutilizados."
                ),
            })
            job.setdefault("log", []).append("[STUDIO] Sessão interrompida; retomada disponível.")
            self._write_json_atomic(path, job)
        return job

    def _append_job_line_locked(self, project: Path, line: str) -> None:
        job = self.jobs[project.name]
        clean = line.rstrip()
        if clean:
            job["log"].append(clean)
            if len(job["log"]) > 1200:
                del job["log"][:300]
            job["last_line"] = clean
            job["last_output_at"] = time.time()
            progress = list(re.finditer(r"(?<!\d)(\d{1,5})\s*/\s*(\d{1,5})(?!\d)", clean))
            if progress:
                current = int(progress[-1].group(1))
                total = max(1, int(progress[-1].group(2)))
                job["progress"] = {
                    "current": current,
                    "total": total,
                    "percent": round(min(100.0, current * 100.0 / total), 1),
                    "label": clean[:240],
                }
            item = re.search(r"\b(?:M\d{4}(?:C\d{3})?|[PSR]\d{4})\b", clean)
            if item:
                job["current_item"] = item.group(0)
        job["heartbeat_at"] = time.time()
        self._persist_job_locked(project)

    def load_config(self, project: Path) -> dict[str, Any]:
        template = json.loads((self.app_root / "templates" / "questionario_base.json").read_text(encoding="utf-8"))
        path = project / "QUESTIONARIO_RESPONDIDO.json"
        if path.is_file():
            try:
                template = _merge(template, json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                pass
        template["project"]["zip_path"] = str(project / "_ENTRADA" / "FR_AUTOEDITE_ENTRADA.zip")
        template["project"]["workspace_root"] = str(self.studio_root)
        template["project"]["context_file"] = str(project / "_ENTRADA" / "CONTEXTO_PROJETO.md")
        return template

    def save_config(self, project: Path, config: dict[str, Any]) -> dict[str, Any]:
        base = self.load_config(project)
        merged = _merge(base, config)
        import fr_autoedite as fr
        try:
            from master_contract import check_booleans
            from types import SimpleNamespace
            check_booleans(SimpleNamespace(**vars(fr)), config, base)
            merged = fr.normalize_answers(merged)
        except fr.AutoEditeError as exc:
            raise StudioError(str(exc)) from exc
        merged["schema_version"] = 3
        merged["project"]["slug"] = project.name
        merged["project"]["zip_path"] = str(project / "_ENTRADA" / "FR_AUTOEDITE_ENTRADA.zip")
        merged["project"]["workspace_root"] = str(self.studio_root)
        merged["project"]["context_file"] = str(project / "_ENTRADA" / "CONTEXTO_PROJETO.md")
        maximum = float(merged.setdefault("handoff", {}).get("chatgpt_lot_max_mb", 145))
        merged["handoff"]["chatgpt_lot_max_mb"] = min(149.0, max(10.0, maximum))
        path = project / "QUESTIONARIO_RESPONDIDO.json"
        plan = project_scope.read(project / "EDIT_PLAN.json", {})
        if plan.get("contract_version") == 2:
            with project_scope.project_lock(project):
                files = {"QUESTIONARIO_RESPONDIDO.json": merged, "_EDITAR/01_CONFIGURACOES_DO_PROJETO.json": merged}
                # Update rendering choices while keeping the AI's explicit lists intact.
                width, height = fr.resolve_output_dimensions(merged["edition"], project_scope.read(project / "MANIFESTO_MEDIA.json", {}).get("media", []))
                plans = [("EDIT_PLAN.json", plan), *[(p.relative_to(project).as_posix(), project_scope.read(p)) for p in (project / "social/planos").glob("REEL_*S.json")]]
                for relative, item in plans:
                    item["audio"] = {"preserve_original": merged["edition"].get("preserve_original_audio", True), "music_path": merged["edition"].get("music_path", ""), "music_volume": merged["edition"].get("music_volume", .1), **merged["audio_design"]}
                    item["visual_effects"] = copy.deepcopy(merged["visual_effects"])
                    item["visual_effects"]["speed_ramping"] = False
                    item["export_quality"] = copy.deepcopy(merged["export_quality"])
                    item["output"].update(fps=merged["edition"]["fps"], render_source=merged["edition"]["render_source"])
                    if relative == "EDIT_PLAN.json":
                        item["output"].update(width=width, height=height)
                        item["versions"] = {"branded": merged["edition"].get("create_branded_version", True), "clean": merged["edition"].get("create_clean_version", True)}
                    else:
                        item["output"] = fr.social_output_settings({"width": width, "height": height, **item["output"]}, item["social_target_sec"])
                    if merged.get("service_intro", {}).get("service_key") != base.get("service_intro", {}).get("service_key"):
                        key = merged["service_intro"]["service_key"]
                        service = fr.load_service_catalog()[key]
                        for segment in item.get("segments", []):
                            if segment.get("card_kind") == "service" or segment.get("service_key") == base.get("service_intro", {}).get("service_key"):
                                segment.update(service_key=key, service_asset=service["asset"], service_layout=service.get("layout"))
                                if segment.get("card_kind") == "service":
                                    segment["title"] = merged["service_intro"].get("custom_title") or service["label"]
                                    segment["body"] = merged["service_intro"].get("custom_body") or service["body"]
                    files[relative] = item
                files["_EDITAR/02_PLANO_DA_EDICAO.json"] = files["EDIT_PLAN.json"]
                if any(merged.get(k) != base.get(k) for k in ("cards", "editing_brief", "visual_effects")):
                    files["CARD_STYLE.json"] = fr.sync_card_style_from_answers(project, merged, persist=False)
                project_scope.publish_files(project, files)
                return merged
        if path.is_file():
            stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            shutil.copy2(path, project / "_HISTORICO" / f"QUESTIONARIO_{stamp}.json")
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
        shutil.copy2(path, project / "_EDITAR" / "01_CONFIGURACOES_DO_PROJETO.json")
        return merged

    def important_files(self, project: Path) -> list[dict[str, Any]]:
        rows = [
            ("VOCÊ ENVIA · ZIP", "_ENTRADA/FR_AUTOEDITE_ENTRADA.zip", "Entrada principal; não editar internamente"),
            ("TAKEOUT ORIGINAL · NÃO EDITAR", "_TAKEOUT/00_NAO_EDITAR_GOOGLE_TAKEOUT_ORIGINAL.zip", "Preservado; o Studio cria outro ZIP com datas"),
            ("TAKEOUT · RELATÓRIO", "_TAKEOUT/01_RELATORIO_GOOGLE_TAKEOUT.md", "Datas recuperadas, pendências e método usado"),
            ("VOCÊ EDITA · contexto", "_ENTRADA/CONTEXTO_PROJETO.md", "Preencha no painel Importar"),
            ("STUDIO EDITA · configurações", "QUESTIONARIO_RESPONDIDO.json", "Prefira editar pelos controles do Studio"),
            ("STUDIO EDITA · plano", "EDIT_PLAN.json", "Prefira editar pela timeline"),
            ("STUDIO EDITA · design", "CARD_STYLE.json", "Prefira editar em Cards e marca"),
            ("IA EDITA E DEVOLVE · roteiro", "_ENVIAR_IA/01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE_IA.md", "Único Markdown que a IA deve alterar"),
            ("Intro personalizada", "_ENTRADA/INTRO_PERSONALIZADA", "Foto ou vídeo opcional"),
            ("Outro personalizado", "_ENTRADA/OUTRO_PERSONALIZADO", "Foto ou vídeo opcional"),
            ("Manifesto das mídias", "MANIFESTO_MEDIA.json", "Gerado automaticamente"),
            ("Prancha geral", "CONTATO_GERAL_CODEX.jpg", "Gerada automaticamente"),
            ("Lista de envios", "UPLOAD_LIST.txt", "Siga exatamente esta lista"),
            ("Prompt para ChatGPT", "PROMPT_PRONTO_PARA_CHATGPT.md", "Envie após os lotes"),
            ("Lotes ChatGPT", "pacote_chatgpt", "Cada ZIP fica abaixo de 150 MB"),
            ("Vídeos finais", "entrega", "Assista antes de publicar"),
        ]
        result = []
        for label, relative, purpose in rows:
            path = project / relative
            if path.name in {"INTRO_PERSONALIZADA", "OUTRO_PERSONALIZADO"}:
                matches = sorted(path.parent.glob(path.name + ".*"))
                if matches:
                    path = matches[-1]
                    relative = str(path.relative_to(project))
            result.append({
                "label": label, "relative": relative, "path": str(path), "purpose": purpose,
                "exists": path.exists(), "is_dir": path.is_dir(),
            })
        return result

    def ai_files(self, project: Path) -> list[dict[str, Any]]:
        """Uma única lista, com ação inequívoca, para o fluxo manual com IA."""
        canonical = project / "_ENVIAR_IA" / "01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE_IA.md"
        legacy = project / "_EDITAR" / "04_ROTEIRO_MESTRE_PARA_IA.md"
        editable_relative = (
            str(canonical.relative_to(project)) if canonical.is_file()
            else str(legacy.relative_to(project)) if legacy.is_file()
            else str(canonical.relative_to(project))
        )
        rows: list[tuple[str, str, str]] = [
            ("COMECE AQUI", "_ENVIAR_IA/00_COMECE_AQUI_O_QUE_EDITAR_E_ENVIAR.md", "read_only"),
            ("EDITAR E DEVOLVER", editable_relative, "edit_return"),
            ("NÃO EDITAR · APENAS ENVIAR", "_ENVIAR_IA/02_NAO_EDITAR_APENAS_ENVIAR_PROMPT.md", "read_only"),
            ("NÃO EDITAR · LISTA DOS LOTES", "_ENVIAR_IA/03_NAO_EDITAR_LISTA_DE_LOTES.txt", "read_only"),
        ]
        package = project / "pacote_chatgpt"
        if package.is_dir():
            for path in sorted(package.glob("FR_AUTOEDITE_LOTE_*.zip")):
                rows.append(("NÃO EDITAR · ANEXAR À IA", str(path.relative_to(project)), "media_lot"))
        result = []
        for label, relative, role in rows:
            path = project / relative
            result.append({
                "label": label, "role": role, "relative": relative, "path": str(path),
                "exists": path.is_file(), "is_dir": False,
                "size_bytes": path.stat().st_size if path.is_file() else 0,
            })
        return result

    def project_state(self, project: Path) -> dict[str, Any]:
        config = self.load_config(project)
        context_path = project / "_ENTRADA" / "CONTEXTO_PROJETO.md"
        context = context_path.read_text(encoding="utf-8", errors="replace") if context_path.is_file() else ""
        plan = None
        if (project / "EDIT_PLAN.json").is_file():
            try:
                plan = json.loads((project / "EDIT_PLAN.json").read_text(encoding="utf-8"))
            except Exception:
                pass
        manifest = None
        if (project / "MANIFESTO_MEDIA.json").is_file():
            try:
                manifest = json.loads((project / "MANIFESTO_MEDIA.json").read_text(encoding="utf-8"))
            except Exception:
                pass
        reel_plans: dict[str, dict[str, Any]] = {}
        reel_root = project / "social" / "planos"
        if reel_root.is_dir():
            for reel_path in sorted(reel_root.glob("REEL_*S.json")):
                try:
                    reel = json.loads(reel_path.read_text(encoding="utf-8"))
                    reel_plans[str(int(reel.get("social_target_sec") or 0))] = reel
                except Exception:
                    pass
        try:
            service_catalog = json.loads(
                (self.app_root / "templates" / "service_catalog.json").read_text(encoding="utf-8")
            ).get("services", [])
        except Exception:
            service_catalog = []
        with self.lock:
            if project.name not in self.jobs:
                self.jobs[project.name] = self._load_persisted_job(project)
            job = copy.deepcopy(self.jobs[project.name])
        if job.get("started_at"):
            ended = float(job.get("finished_at") or time.time())
            job["elapsed_sec"] = max(0, round(ended - float(job["started_at"]), 1))
        card_previews = []
        preview_root = project / "cards_editaveis"
        if preview_root.is_dir():
            card_previews = [str(path.relative_to(project)) for path in sorted(preview_root.rglob("*.png"))[-24:]]
        return {
            "application_version": self.app_version,
            "roteiro_versions": project_scope.list_versions(project),
            "active_roteiro": project_scope.read(project / "_CONTROLE/ROTEIRO_ATIVO.json", {}),
            "brief_review": project_scope.read(project / "_CONTROLE/REVISAO_ROTEIRO.json", {}),
            "last_render": project_scope.read(project / "_CONTROLE/ULTIMA_RENDERIZACAO.json", {}),
            "project": {"slug": project.name, "path": str(project)},
            "config": config,
            "context": context,
            "plan": plan,
            "manifest": manifest,
            "reel_plans": reel_plans,
            "service_catalog": service_catalog,
            "files": self.important_files(project),
            "ai_files": self.ai_files(project),
            "card_previews": card_previews,
            "capabilities": {
                "rclone": bool(shutil.which("rclone")),
                "ffmpeg": bool(shutil.which("ffmpeg")),
                "exiftool": bool(shutil.which("exiftool")),
            },
            "job": job,
        }

    @staticmethod
    def _safe_project_target(project: Path, relative: str) -> Path:
        value = Path(str(relative))
        if value.is_absolute() or not str(value) or str(value) == ".":
            raise StudioError("Caminho de arquivo inválido.")
        target = (project / value).resolve()
        target.relative_to(project.resolve())
        return target

    @staticmethod
    def _kind_for(path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in {".mp4", ".mov", ".mkv", ".m4v", ".avi", ".webm", ".3gp", ".mts", ".m2ts"}:
            return "video"
        if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff"}:
            return "image"
        return "document"

    def gallery_items(self, project: Path) -> list[dict[str, Any]]:
        """Catálogo visual sem duplicar cenas virtuais do mesmo vídeo."""
        items: dict[str, dict[str, Any]] = {}

        def add(
            relative: str, category: str, *, preview: str | None = None,
            thumbnail: str | None = None, label: str | None = None,
        ) -> None:
            try:
                source = self._safe_project_target(project, relative)
            except (StudioError, ValueError):
                return
            if not source.is_file() or source.is_symlink():
                return
            preview_relative = preview or relative
            try:
                preview_path = self._safe_project_target(project, preview_relative)
                if not preview_path.is_file():
                    preview_relative = relative
            except (StudioError, ValueError):
                preview_relative = relative
            stat = source.stat()
            items[relative] = {
                "relative": relative,
                "preview_relative": preview_relative,
                "thumbnail_relative": thumbnail or "",
                "name": label or source.name,
                "category": category,
                "kind": self._kind_for(source),
                "size_bytes": stat.st_size,
                "modified_at": stat.st_mtime,
            }

        manifest_path = project / "MANIFESTO_MEDIA.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                manifest = {}
            seen_sources: set[str] = set()
            for row in manifest.get("media", []):
                if not isinstance(row, dict):
                    continue
                source = str(row.get("source_path") or "")
                if not source or source in seen_sources:
                    continue
                seen_sources.add(source)
                proxy = str(row.get("proxy_path") or source)
                thumbnail = str(row.get("thumbnail_path") or "")
                add(source, "originais", preview=proxy, thumbnail=thumbnail, label=str(row.get("filename") or ""))

        roots = (
            ("entrega", "entregas"), ("social", "social"),
            ("cards_editaveis", "cards"), ("_ENTRADA", "entradas"),
        )
        for relative_root, category in roots:
            root = project / relative_root
            if not root.is_dir():
                continue
            for path in root.rglob("*"):
                if path.is_file() and not path.is_symlink() and self._kind_for(path) in {"video", "image"}:
                    relative = path.relative_to(project).as_posix()
                    add(relative, category)
        for record in (project / "_RENDERIZACOES").glob("*/RENDER_RUN.json"):
            data = project_scope.read(record, {})
            if data.get("status") != "completed":
                continue
            for value in data.get("outputs", []):
                path = Path(value)
                try:
                    relative = path.relative_to(project).as_posix()
                except ValueError:
                    continue
                label = f"{data.get('roteiro', {}).get('id', 'manual')} · {record.parent.name[:16]} · {path.name}"
                add(relative, "social" if "/social/" in relative else "entregas", label=label)
        return sorted(items.values(), key=lambda item: (-float(item["modified_at"]), item["name"].lower()))[:2000]

    @staticmethod
    def _is_protected_relative(relative: str) -> bool:
        protected_prefixes = ("originais/", "_ENTRADA/", "_TAKEOUT/", "_HISTORICO/")
        protected_names = {
            "QUESTIONARIO_RESPONDIDO.json", "FR_AUTOEDITE_PROJECT.json", "MANIFESTO_MEDIA.json",
            "MANIFESTO_MEDIA.csv", "EDIT_PLAN.json", "CARD_STYLE.json", "SOCIAL_PLAN.json",
            "PUBLICACAO_SOCIAL.json", "PUBLICACAO_SOCIAL.md", "ROTEIRO_MESTRE_PARA_IA.md",
        }
        return relative.startswith(protected_prefixes) or Path(relative).name in protected_names

    def cleanup_candidates(self, project: Path) -> list[dict[str, Any]]:
        """Somente arquivos regeneráveis ou interrompidos entram nesta lista."""
        candidates: dict[str, dict[str, Any]] = {}

        def add(path: Path, group: str, reason: str) -> None:
            if not path.is_file() or path.is_symlink():
                return
            try:
                relative = path.resolve().relative_to(project.resolve()).as_posix()
            except ValueError:
                return
            if relative.startswith(".FR_AUTOEDITE_LIXEIRA/") or self._is_protected_relative(relative):
                return
            candidates[relative] = {
                "relative": relative, "name": path.name, "group": group,
                "reason": reason, "size_bytes": path.stat().st_size,
            }

        for path in project.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            name = path.name.lower()
            if name.endswith((".partial.mp4", ".partial.jpg", ".upload.tmp", ".tmp", ".tts.wav")):
                add(path, "temporarios", "arquivo parcial/interrompido")

        for relative_root, group, reason in (
            ("render/segmentos", "cache_render", "segmento intermediário regenerável"),
            ("cards_editaveis", "previas_cards", "prévia de card regenerável"),
            ("pacote_chatgpt", "lotes_ia", "lote de envio regenerável"),
            ("_ENVIAR_CHATGPT", "lotes_ia", "cópia de envio regenerável"),
            ("contatos_visuais", "previas_midias", "prancha visual regenerável"),
        ):
            root = project / relative_root
            if root.is_dir():
                for path in root.rglob("*"):
                    add(path, group, reason)

        referenced_proxies: set[str] = set()
        referenced_thumbnails: set[str] = set()
        manifest_path = project / "MANIFESTO_MEDIA.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                manifest = {}
            for row in manifest.get("media", []):
                if isinstance(row, dict):
                    if row.get("proxy_path"):
                        referenced_proxies.add(str(row["proxy_path"]))
                    if row.get("thumbnail_path"):
                        referenced_thumbnails.add(str(row["thumbnail_path"]))
        for root_name, referenced, group in (
            ("proxies", referenced_proxies, "proxies_orfaos"),
            ("miniaturas", referenced_thumbnails, "miniaturas_orfas"),
        ):
            root = project / root_name
            if not root.is_dir():
                continue
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                relative = path.relative_to(project).as_posix()
                if relative not in referenced:
                    add(path, group, "arquivo sem referência no manifesto atual")
        return sorted(candidates.values(), key=lambda item: (item["group"], item["relative"]))

    def project_files(self, project: Path, deletable: set[str] | None = None) -> list[dict[str, Any]]:
        deletable = deletable if deletable is not None else {
            item["relative"] for item in self.cleanup_candidates(project)
        }
        rows: list[dict[str, Any]] = []
        for path in project.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(project).as_posix()
            if relative.startswith(".FR_AUTOEDITE_LIXEIRA/"):
                continue
            stat = path.stat()
            rows.append({
                "relative": relative, "name": path.name, "kind": self._kind_for(path),
                "size_bytes": stat.st_size, "modified_at": stat.st_mtime,
                "protected": self._is_protected_relative(relative),
                "cleanup_candidate": relative in deletable,
            })
        return sorted(rows, key=lambda item: item["relative"].lower())[:5000]

    def storage_summary(self, project: Path) -> dict[str, Any]:
        groups = {"originais": 0, "proxies": 0, "render": 0, "entregas": 0, "outros": 0, "lixeira": 0}
        count = 0
        for path in project.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(project).as_posix()
            size = path.stat().st_size
            count += 1
            if relative.startswith("originais/"):
                group = "originais"
            elif relative.startswith("proxies/"):
                group = "proxies"
            elif relative.startswith("render/"):
                group = "render"
            elif relative.startswith(("entrega/", "social/")):
                group = "entregas"
            elif relative.startswith(".FR_AUTOEDITE_LIXEIRA/"):
                group = "lixeira"
            else:
                group = "outros"
            groups[group] += size
        return {"total_bytes": sum(groups.values()), "file_count": count, "groups": groups}

    def trash_batches(self, project: Path) -> list[dict[str, Any]]:
        root = project / ".FR_AUTOEDITE_LIXEIRA"
        batches: list[dict[str, Any]] = []
        if not root.is_dir():
            return batches
        for batch in sorted(root.iterdir(), reverse=True):
            manifest = batch / "manifest.json"
            if not batch.is_dir() or not manifest.is_file():
                continue
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            batches.append({
                "id": batch.name, "created_at": data.get("created_at"),
                "restored_at": data.get("restored_at"),
                "files": len(data.get("moves") or []),
                "size_bytes": sum(int(item.get("size_bytes") or 0) for item in data.get("moves") or []),
            })
        return batches

    def trash_files(self, project: Path, requested: list[str]) -> dict[str, Any]:
        allowed = {item["relative"]: item for item in self.cleanup_candidates(project)}
        selected = list(dict.fromkeys(str(item) for item in requested if str(item) in allowed))
        if not selected:
            raise StudioError("Selecione ao menos um arquivo regenerável para mover à lixeira.")
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        batch = project / ".FR_AUTOEDITE_LIXEIRA" / stamp
        moves: list[dict[str, Any]] = []
        for relative in selected:
            source = self._safe_project_target(project, relative)
            if not source.is_file() or source.is_symlink():
                continue
            destination = batch / "files" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            size = source.stat().st_size
            source.replace(destination)
            moves.append({"relative": relative, "size_bytes": size})
        if not moves:
            raise StudioError("Os arquivos selecionados já não existem.")
        payload = {"created_at": dt.datetime.now(dt.timezone.utc).isoformat(), "moves": moves}
        self._write_json_atomic(batch / "manifest.json", payload)
        return {"batch": batch.name, "files": len(moves), "size_bytes": sum(item["size_bytes"] for item in moves)}

    def restore_latest_trash(self, project: Path) -> dict[str, Any]:
        root = project / ".FR_AUTOEDITE_LIXEIRA"
        batches = [path for path in sorted(root.iterdir(), reverse=True) if (path / "manifest.json").is_file()] if root.is_dir() else []
        batch: Path | None = None
        payload: dict[str, Any] = {}
        for candidate in batches:
            try:
                candidate_payload = json.loads((candidate / "manifest.json").read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not candidate_payload.get("restored_at"):
                batch = candidate
                payload = candidate_payload
                break
        if batch is None:
            raise StudioError("Não existe lote de limpeza pendente para restaurar.")
        manifest_path = batch / "manifest.json"
        restored = 0
        skipped: list[str] = []
        for item in payload.get("moves") or []:
            relative = str(item.get("relative") or "")
            source = batch / "files" / relative
            destination = self._safe_project_target(project, relative)
            if not source.is_file():
                continue
            if destination.exists():
                skipped.append(relative)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            source.replace(destination)
            restored += 1
        payload["restored_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        payload["restore_skipped"] = skipped
        self._write_json_atomic(manifest_path, payload)
        return {"batch": batch.name, "restored": restored, "skipped": skipped}

    def empty_project_trash(self, project: Path, confirmation: str) -> dict[str, Any]:
        if confirmation != "APAGAR DEFINITIVAMENTE":
            raise StudioError("Confirmação incorreta; a lixeira não foi apagada.")
        root = project / ".FR_AUTOEDITE_LIXEIRA"
        size = self.storage_summary(project)["groups"]["lixeira"]
        batches = len(self.trash_batches(project))
        if root.is_dir():
            shutil.rmtree(root)
        return {"batches": batches, "size_bytes": size}

    def project_trash(self) -> list[dict[str, Any]]:
        root = self.studio_root / ".FR_AUTOEDITE_LIXEIRA_PROJETOS"
        rows: list[dict[str, Any]] = []
        if not root.is_dir():
            return rows
        for path in sorted(root.iterdir(), reverse=True):
            metadata = path / ".FR_PROJECT_TRASH.json"
            if not path.is_dir() or not metadata.is_file():
                continue
            try:
                data = json.loads(metadata.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            rows.append({"id": path.name, "slug": data.get("slug"), "deleted_at": data.get("deleted_at")})
        return rows

    def trash_project(self, project: Path, confirmation: str) -> dict[str, Any]:
        if confirmation != project.name:
            raise StudioError(f"Para mover o projeto à lixeira, digite exatamente: {project.name}")
        with self.lock:
            if self.jobs.get(project.name, {}).get("running"):
                raise StudioError("Cancele a tarefa ativa antes de mover o projeto.")
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        root = self.studio_root / ".FR_AUTOEDITE_LIXEIRA_PROJETOS"
        root.mkdir(parents=True, exist_ok=True)
        metadata = {"slug": project.name, "deleted_at": dt.datetime.now(dt.timezone.utc).isoformat()}
        self._write_json_atomic(project / ".FR_PROJECT_TRASH.json", metadata)
        destination = root / f"{stamp}__{project.name}"
        project.replace(destination)
        with self.lock:
            self.jobs.pop(project.name, None)
            self.processes.pop(project.name, None)
        return {"id": destination.name, "slug": metadata["slug"]}

    def restore_project(self, trash_id: str) -> dict[str, Any]:
        root = (self.studio_root / ".FR_AUTOEDITE_LIXEIRA_PROJETOS").resolve()
        source = (root / Path(trash_id).name).resolve()
        source.relative_to(root)
        metadata_path = source / ".FR_PROJECT_TRASH.json"
        if not source.is_dir() or not metadata_path.is_file():
            raise StudioError("Projeto não encontrado na lixeira.")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        destination = self.project_dir(str(metadata.get("slug") or "projeto-restaurado"))
        if destination.exists():
            raise StudioError("Já existe um projeto ativo com esse nome.")
        metadata_path.unlink(missing_ok=True)
        source.replace(destination)
        return {"slug": destination.name, "path": str(destination)}

    def library_state(self, project: Path) -> dict[str, Any]:
        cleanup = self.cleanup_candidates(project)
        deletable = {item["relative"] for item in cleanup}
        return {
            "ok": True,
            "gallery": self.gallery_items(project),
            "files": self.project_files(project, deletable),
            "cleanup_candidates": cleanup,
            "trash_batches": self.trash_batches(project),
            "project_trash": self.project_trash(),
            "storage": self.storage_summary(project),
        }

    def _command_for(self, project: Path, action: str) -> list[str]:
        questionnaire = project / "QUESTIONARIO_RESPONDIDO.json"
        zip_path = project / "_ENTRADA" / "FR_AUTOEDITE_ENTRADA.zip"
        config: dict[str, Any] = {}
        if questionnaire.is_file():
            try:
                config = json.loads(questionnaire.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                config = {}
        use_proxies = config.get("edition", {}).get("render_source") == "proxies"
        if action == "prepare":
            return [str(self.launcher), "preparar", "--respostas", str(questionnaire), "--zip", str(zip_path), "--projeto", str(project)]
        if action == "draft":
            return [str(self.launcher), "draft", "--projeto", str(project)]
        if action == "render":
            command = [str(self.launcher), "render", "--projeto", str(project)]
            if use_proxies:
                command.append("--usar-proxies")
            return command
        if action == "social":
            command = [str(self.launcher), "social", "--projeto", str(project)]
            if use_proxies:
                command.append("--usar-proxies")
            return command
        if action == "package":
            return [str(self.launcher), "pacote-chatgpt", "--projeto", str(project)]
        if action == "cards":
            return [str(self.launcher), "cards", "--projeto", str(project)]
        if action == "audit":
            return [str(self.launcher), "auditar", "--projeto", str(project)]
        if action == "cloud-test":
            return [str(self.launcher), "exportar-nuvem", "--projeto", str(project), "--testar"]
        if action == "cloud":
            return [str(self.launcher), "exportar-nuvem", "--projeto", str(project)]
        if action == "brief-generate":
            if not (project / "MANIFESTO_MEDIA.json").is_file():
                if not zip_path.is_file():
                    raise StudioError(
                        "Antes de gerar o Markdown, envie o ZIP de fotos e vídeos. "
                        "Depois clique novamente em Gerar Markdown; o Studio preparará as mídias automaticamente."
                    )
                return [
                str(self.launcher), "preparar", "--respostas", str(questionnaire),
                    "--zip", str(zip_path), "--projeto", str(project),
                ]
            return [str(self.launcher), "gerar-roteiro-ia", "--projeto", str(project)]
        if action == "brief-apply":
            return [
                str(self.launcher), "aplicar-roteiro-ia", "--projeto", str(project),
                "--arquivo", str(project / "_ENTRADA" / "ROTEIRO_MESTRE_RESPONDIDO.md"),
            ]
        if action == "takeout-normalize":
            source = project / "_TAKEOUT" / "00_NAO_EDITAR_GOOGLE_TAKEOUT_ORIGINAL.zip"
            legacy_source = project / "_ENTRADA" / "GOOGLE_TAKEOUT_ORIGINAL.zip"
            if not source.is_file() and legacy_source.is_file():
                source = legacy_source
            if not source.is_file():
                raise StudioError("Envie primeiro o ZIP original do Google Takeout.")
            return [
                str(self.launcher), "importar-takeout", "--arquivo", str(source),
                "--projeto", str(project),
            ]
        raise StudioError(f"Ação desconhecida: {action}")

    def start_job(self, project: Path, action: str) -> None:
        # Valide pré-condições antes de marcar a tarefa como ativa. Uma falha
        # imediata não pode deixar o projeto preso em "PROCESSANDO".
        command = self._command_for(project, action)
        with self.lock:
            current = self.jobs.get(project.name)
            if current and current.get("running"):
                raise StudioError("Já existe uma tarefa em execução neste projeto.")
            stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
            log_path = project / "_CONTROLE" / "logs" / f"{stamp}_{_slugify(action)}.log"
            self.jobs[project.name] = {
                "running": True, "action": action, "started_at": time.time(),
                "last_output_at": time.time(), "heartbeat_at": time.time(),
                "returncode": None, "pid": None, "cancel_requested": False,
                "progress": {"current": 0, "total": 0, "percent": 0.0, "label": "Preparando tarefa"},
                "current_item": "", "log_path": str(log_path),
                "log": [f"[STUDIO] Iniciando: {action}"],
            }
            self._persist_job_locked(project)

        def worker() -> None:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                process = subprocess.Popen(
                    command,
                    cwd=str(project),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    start_new_session=True,
                )
            except OSError as exc:
                with self.lock:
                    job = self.jobs[project.name]
                    job.update({
                        "running": False, "returncode": 127, "finished_at": time.time(),
                        "error_message": f"Não foi possível iniciar a tarefa: {exc}",
                    })
                    self._append_job_line_locked(project, f"[STUDIO] Falha ao iniciar: {exc}")
                return

            with self.lock:
                self.processes[project.name] = process
                self.jobs[project.name]["pid"] = process.pid
                self._persist_job_locked(project)

            output: queue.Queue[str | None] = queue.Queue()

            def read_output() -> None:
                assert process.stdout is not None
                try:
                    for line in process.stdout:
                        output.put(line)
                finally:
                    output.put(None)

            threading.Thread(target=read_output, daemon=True).start()
            reader_finished = False
            with log_path.open("a", encoding="utf-8") as log_stream:
                log_stream.write(f"[STUDIO] Iniciando: {action}\n")
                log_stream.flush()
                while process.poll() is None or not reader_finished or not output.empty():
                    try:
                        line = output.get(timeout=0.75)
                    except queue.Empty:
                        line = ""
                    if line is None:
                        reader_finished = True
                    elif line:
                        log_stream.write(line)
                        log_stream.flush()
                        with self.lock:
                            self._append_job_line_locked(project, line)
                    else:
                        with self.lock:
                            job = self.jobs[project.name]
                            job["heartbeat_at"] = time.time()
                            self._persist_job_locked(project)
            code = process.wait()
            with self.lock:
                self.processes.pop(project.name, None)
                job = self.jobs[project.name]
                job["running"] = False
                job["returncode"] = code
                job["finished_at"] = time.time()
                if code != 0:
                    meaningful = [
                        line.strip() for line in job["log"]
                        if line.strip() and not line.startswith("[STUDIO]")
                    ]
                    last = meaningful[-1] if meaningful else f"A tarefa terminou com o código {code}."
                    last = last.removeprefix("[FR][ATENÇÃO]").removeprefix("[FR]").strip()
                    job["error_message"] = last[:700]
                final_line = (
                    "[STUDIO] Cancelado; resultados concluídos foram preservados."
                    if job.get("cancel_requested") else
                    "[STUDIO] Concluído com sucesso." if code == 0 else
                    f"[STUDIO] Encerrado com erro {code}."
                )
                job["log"].append(final_line)
                if code == 0:
                    job["progress"] = {
                        "current": job.get("progress", {}).get("total", 1) or 1,
                        "total": job.get("progress", {}).get("total", 1) or 1,
                        "percent": 100.0,
                        "label": "Concluído",
                    }
                self._persist_job_locked(project)
            with log_path.open("a", encoding="utf-8") as log_stream:
                log_stream.write(final_line + "\n")

        threading.Thread(target=worker, daemon=True).start()

    def cancel_job(self, project: Path) -> None:
        with self.lock:
            job = self.jobs.get(project.name)
            process = self.processes.get(project.name)
            if not job or not job.get("running") or process is None:
                raise StudioError("Não há tarefa ativa para cancelar.")
            job["cancel_requested"] = True
            job["error_message"] = "Cancelamento solicitado; aguardando o processo encerrar."
            self._append_job_line_locked(project, "[STUDIO] Cancelamento solicitado pelo usuário.")
            pid = process.pid
        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except OSError as exc:
            raise StudioError(f"Não foi possível cancelar a tarefa: {exc}") from exc

    @staticmethod
    def _validate_segment_controls(segment: dict[str, Any], index: int, label: str) -> None:
        if segment.get("type") != "media" or not segment.get("editorial_timelapse"):
            return
        if segment.get("media_type") != "video":
            raise StudioError(f"{label}, segmento {index}: time-lapse só pode ser usado em vídeo.")
        try:
            speed = float(segment.get("playback_speed") or 0)
        except (TypeError, ValueError) as exc:
            raise StudioError(f"{label}, segmento {index}: velocidade de time-lapse inválida.") from exc
        if not 1.25 <= speed <= 30:
            raise StudioError(f"{label}, segmento {index}: use velocidade entre 1.25x e 30x.")

    def save_plan(self, project: Path, plan: dict[str, Any]) -> None:
        if (project / "MANIFESTO_MEDIA.json").is_file():
            import fr_autoedite as fr
            try:
                plan = fr.validate_imported_plan(plan, fr.read_json(project / "MANIFESTO_MEDIA.json"), "filme principal",
                    {s["media_id"]: s for s in project_scope.read(project / "EDIT_PLAN.json", {}).get("segments", []) if s.get("external_asset")})
            except fr.AutoEditeError as exc:
                raise StudioError(str(exc)) from exc
        if not isinstance(plan.get("segments"), list) or not plan["segments"]:
            raise StudioError("O plano precisa conter ao menos um segmento.")
        for index, segment in enumerate(plan["segments"], 1):
            if segment.get("type") not in {"card", "media"}:
                raise StudioError(f"Segmento {index}: tipo inválido.")
            try:
                if float(segment.get("duration_sec") or 0) <= 0:
                    raise ValueError
            except (TypeError, ValueError) as exc:
                raise StudioError(f"Segmento {index}: duração inválida.") from exc
            self._validate_segment_controls(segment, index, "Filme")
        target = project / "EDIT_PLAN.json"
        if target.is_file():
            stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            shutil.copy2(target, project / "_HISTORICO" / f"EDIT_PLAN_{stamp}.json")
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(target)
        shutil.copy2(target, project / "_EDITAR" / "02_PLANO_DA_EDICAO.json")

    def save_reel_plan(self, project: Path, plan: dict[str, Any]) -> Path:
        if (project / "MANIFESTO_MEDIA.json").is_file():
            import fr_autoedite as fr
            try:
                plan = fr.validate_imported_plan(plan, fr.read_json(project / "MANIFESTO_MEDIA.json"), "Reel editado",
                    {s["media_id"]: s for s in project_scope.read(project / "EDIT_PLAN.json", {}).get("segments", []) if s.get("external_asset")})
            except fr.AutoEditeError as exc:
                raise StudioError(str(exc)) from exc
        try:
            target_sec = int(float(plan.get("social_target_sec") or 0))
        except (TypeError, ValueError) as exc:
            raise StudioError("O plano do Reel não informa uma duração válida.") from exc
        if target_sec < 5 or target_sec > 600:
            raise StudioError("A duração do Reel deve ficar entre 5 e 600 segundos.")
        if not isinstance(plan.get("segments"), list) or not plan["segments"]:
            raise StudioError("O Reel precisa conter ao menos um segmento.")
        for index, segment in enumerate(plan["segments"], 1):
            if segment.get("type") not in {"card", "media"}:
                raise StudioError(f"Reel {target_sec}s, segmento {index}: tipo inválido.")
            try:
                if float(segment.get("duration_sec") or 0) <= 0:
                    raise ValueError
            except (TypeError, ValueError) as exc:
                raise StudioError(f"Reel {target_sec}s, segmento {index}: duração inválida.") from exc
            self._validate_segment_controls(segment, index, f"Reel {target_sec}s")
            segment.setdefault("enabled", True)
        enabled_media = [
            segment for segment in plan["segments"]
            if segment.get("type") == "media"
            and not segment.get("external_asset")
            and segment.get("enabled", True)
        ]
        roles = {str(segment.get("coverage_role") or "") for segment in enabled_media}
        if plan.get("contract_version") != 2 and (not enabled_media or "inicio" not in roles or "fim" not in roles):
            raise StudioError(
                "O Reel precisa manter ao menos uma mídia de início e uma de fim. "
                "Desmarque outras cenas, mas preserve as faixas azul e laranja."
            )
        target = project / "social" / "planos" / f"REEL_{target_sec}S.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_file():
            stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            shutil.copy2(target, project / "_HISTORICO" / f"REEL_{target_sec}S_{stamp}.json")
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(target)
        return target


class StudioHandler(BaseHTTPRequestHandler):
    server_version = "FR-AutoEdite-Studio/3.4.0"

    @property
    def state(self) -> StudioState:
        return self.server.state  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, message: str, status: int = 400) -> None:
        self._json({"ok": False, "error": message}, status)

    def _authorized(self) -> bool:
        supplied = self.headers.get("X-FR-Token", "")
        if not supplied:
            supplied = parse_qs(urlparse(self.path).query).get("token", [""])[0]
        return secrets.compare_digest(supplied, self.state.token)

    def _project(self, query: dict[str, list[str]] | None = None) -> Path:
        query = query or parse_qs(urlparse(self.path).query)
        slug = query.get("project", [""])[0]
        if not slug:
            raise StudioError("Selecione um projeto.")
        project = self.state.project_dir(slug)
        if not project.is_dir():
            raise StudioError("Projeto não encontrado.")
        return project

    def _read_json(self, limit: int = 8 * 1024 * 1024) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0 or length > limit:
            raise StudioError("Requisição vazia ou grande demais.")
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception as exc:
            raise StudioError("JSON inválido.") from exc

    def _receive_file(self, target: Path, limit: int) -> int:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0 or length > limit:
            raise StudioError("Arquivo vazio ou maior que o limite permitido.")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".upload.tmp")
        remaining = length
        with temporary.open("wb") as stream:
            while remaining > 0:
                chunk = self.rfile.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                stream.write(chunk)
                remaining -= len(chunk)
        if remaining:
            temporary.unlink(missing_ok=True)
            raise StudioError("O envio foi interrompido antes do fim.")
        temporary.replace(target)
        return length

    def _send_file(self, target: Path, *, head_only: bool = False) -> None:
        """Transmite arquivos grandes com HTTP Range, sem carregá-los na RAM."""
        if not target.is_file() or target.is_symlink():
            self._error("Arquivo não encontrado.", 404)
            return
        size = target.stat().st_size
        start = 0
        end = max(0, size - 1)
        status = HTTPStatus.OK
        range_header = self.headers.get("Range", "").strip()
        if range_header:
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header)
            if not match or (not match.group(1) and not match.group(2)):
                self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if match.group(1):
                start = int(match.group(1))
                end = int(match.group(2)) if match.group(2) else end
            else:
                suffix = int(match.group(2))
                start = max(0, size - suffix)
            if start >= size or start < 0 or end < start:
                self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            end = min(end, size - 1)
            status = HTTPStatus.PARTIAL_CONTENT
        length = 0 if size == 0 else end - start + 1
        self.send_response(status)
        self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        download_name = re.sub(r"[^A-Za-z0-9._ -]", "_", target.name).strip() or "arquivo"
        self.send_header("Content-Disposition", f'inline; filename="{download_name}"')
        self.send_header("Cache-Control", "no-store")
        if status == HTTPStatus.PARTIAL_CONTENT:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        if head_only or length <= 0:
            return
        remaining = length
        with target.open("rb") as stream:
            stream.seek(start)
            while remaining > 0:
                chunk = stream.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    break
                remaining -= len(chunk)

    def do_HEAD(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        try:
            if not self._authorized():
                self._error("Sessão inválida.", 403)
                return
            if parsed.path in {"/api/file", "/api/media"}:
                project = self._project(query)
                relative = unquote(query.get("path", [""])[0])
                target = self.state._safe_project_target(project, relative)
                self._send_file(target, head_only=True)
                return
            self._error("Rota não encontrada.", 404)
        except (StudioError, ValueError, OSError) as exc:
            self._error(str(exc))

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        try:
            if parsed.path == "/":
                template = (self.state.app_root / "assets" / "studio" / "index.html").read_text(encoding="utf-8")
                body = template.replace("__FR_TOKEN__", self.state.token).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
                self.end_headers()
                self.wfile.write(body)
                return
            public_assets = {
                "/asset/logo.png": ("assets/franco-romeu-logo.png", "image/png"),
                "/asset/font-title.ttf": ("assets/fonts/StardosStencil-Bold.ttf", "font/ttf"),
                "/asset/font-body.ttf": ("assets/fonts/Rokkitt-Regular.ttf", "font/ttf"),
                "/asset/font-mono.ttf": ("assets/fonts/ShareTechMono-Regular.ttf", "font/ttf"),
            }
            if parsed.path.startswith("/asset/service/"):
                import re
                key = re.sub(r"[^a-z0-9_]", "", parsed.path.rsplit("/", 1)[-1].lower())
                path = self.state.app_root / "assets" / "services" / f"{key}.png"
                if not path.is_file():
                    self._error("Serviço não encontrado.", 404)
                    return
                body = path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "public, max-age=3600")
                self.end_headers()
                self.wfile.write(body)
                return
            if parsed.path in public_assets:
                relative, mime = public_assets[parsed.path]
                path = self.state.app_root / relative
                body = path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if not self._authorized():
                self._error("Sessão inválida.", 403)
                return
            if parsed.path == "/api/state":
                projects = self.state.list_projects()
                slug = query.get("project", [projects[0]["slug"] if projects else ""])[0]
                payload: dict[str, Any] = {"ok": True, "projects": projects, "studio_root": str(self.state.studio_root)}
                if slug:
                    payload.update(self.state.project_state(self.state.project_dir(slug)))
                self._json(payload)
                return
            if parsed.path == "/api/library":
                project = self._project(query)
                self._json(self.state.library_state(project))
                return
            if parsed.path in {"/api/file", "/api/media"}:
                project = self._project(query)
                relative = unquote(query.get("path", [""])[0])
                target = self.state._safe_project_target(project, relative)
                self._send_file(target)
                return
            self._error("Rota não encontrada.", 404)
        except (StudioError, ValueError, OSError) as exc:
            self._error(str(exc))

    @serialized_mutation
    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if not self._authorized():
            self._error("Sessão inválida.", 403)
            return
        try:
            if parsed.path == "/api/project":
                data = self._read_json()
                project = self.state.create_project(str(data.get("name") or "Novo projeto Franco Romeu"))
                self._json({"ok": True, "project": project})
                return
            if parsed.path == "/api/restore-project":
                data = self._read_json()
                restored = self.state.restore_project(str(data.get("trash_id") or ""))
                self._json({"ok": True, "project": restored})
                return
            project = self._project(query)
            if parsed.path not in {"/api/cancel", "/api/open-folder"}:
                with self.state.lock:
                    busy = self.state.jobs.get(project.name, {}).get("running")
                if busy:
                    raise StudioError("Aguarde a tarefa atual terminar antes de alterar este projeto.")
            if parsed.path == "/api/upload":
                length = int(self.headers.get("Content-Length", "0") or 0)
                if length < 4:
                    raise StudioError("Selecione um ZIP válido.")
                target = project / "_ENTRADA" / "FR_AUTOEDITE_ENTRADA.zip"
                temporary = target.with_suffix(".upload.tmp")
                remaining = length
                with temporary.open("wb") as stream:
                    while remaining > 0:
                        chunk = self.rfile.read(min(1024 * 1024, remaining))
                        if not chunk:
                            break
                        stream.write(chunk)
                        remaining -= len(chunk)
                if remaining or not zipfile.is_zipfile(temporary):
                    temporary.unlink(missing_ok=True)
                    raise StudioError("O arquivo enviado não é um ZIP íntegro.")
                if target.is_file():
                    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                    target.replace(project / "_HISTORICO" / f"FR_AUTOEDITE_ENTRADA_{stamp}.zip")
                temporary.replace(target)
                self._json({"ok": True, "path": str(target), "size_bytes": target.stat().st_size})
                return
            if parsed.path == "/api/takeout-upload":
                filename = Path(unquote(self.headers.get("X-Filename", "takeout.zip"))).name
                if Path(filename).suffix.lower() != ".zip":
                    raise StudioError("O Google Takeout deve ser enviado como arquivo .zip.")
                stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                takeout_dir = project / "_TAKEOUT"
                takeout_dir.mkdir(parents=True, exist_ok=True)
                incoming = takeout_dir / f"TAKEOUT_RECEBENDO_{stamp}.zip"
                size = self._receive_file(incoming, 80 * 1024 * 1024 * 1024)
                if not zipfile.is_zipfile(incoming):
                    incoming.unlink(missing_ok=True)
                    raise StudioError("O arquivo enviado não é um ZIP íntegro do Google Takeout.")
                target = takeout_dir / "00_NAO_EDITAR_GOOGLE_TAKEOUT_ORIGINAL.zip"
                if target.is_file():
                    target.replace(project / "_HISTORICO" / f"GOOGLE_TAKEOUT_ORIGINAL_{stamp}.zip")
                incoming.replace(target)
                self._json({"ok": True, "path": str(target), "size_bytes": size})
                return
            if parsed.path == "/api/asset-upload":
                role = query.get("kind", [""])[0]
                if role not in {"intro", "outro"}:
                    raise StudioError("Tipo de abertura/encerramento inválido.")
                filename = Path(unquote(self.headers.get("X-Filename", "arquivo"))).name
                suffix = Path(filename).suffix.lower()
                allowed = {
                    ".mp4", ".mov", ".mkv", ".m4v", ".avi", ".webm", ".3gp", ".mts", ".m2ts",
                    ".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".tif", ".tiff",
                }
                if suffix not in allowed:
                    raise StudioError("Use uma foto ou vídeo compatível para intro/outro.")
                stem = "INTRO_PERSONALIZADA" if role == "intro" else "OUTRO_PERSONALIZADO"
                stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                incoming = project / "_ENTRADA" / f"UPLOAD_{role.upper()}_{stamp}{suffix}"
                size = self._receive_file(incoming, 12 * 1024 * 1024 * 1024)
                try:
                    probe = subprocess.run(
                        ["ffprobe", "-v", "error", "-show_entries", "format=format_name,duration", "-of", "json", str(incoming)],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=45,
                    )
                except subprocess.TimeoutExpired as exc:
                    incoming.unlink(missing_ok=True)
                    raise StudioError("A validação da intro/outro excedeu 45 segundos.") from exc
                if probe.returncode != 0:
                    incoming.unlink(missing_ok=True)
                    raise StudioError("O arquivo enviado não pôde ser reconhecido como foto ou vídeo íntegro.")
                for old in (project / "_ENTRADA").glob(f"{stem}.*"):
                    old.replace(project / "_HISTORICO" / f"{stem}_{stamp}{old.suffix.lower()}")
                target = project / "_ENTRADA" / f"{stem}{suffix}"
                incoming.replace(target)
                config = self.state.load_config(project)
                block = config.setdefault("external_intro_outro", {})
                block[f"{role}_enabled"] = True
                block[f"{role}_path"] = str(target)
                config = self.state.save_config(project, config)
                self._json({"ok": True, "path": str(target), "size_bytes": size, "config": config})
                return
            if parsed.path == "/api/editing-brief-upload":
                target = project / "_ENTRADA" / "ROTEIRO_MESTRE_RESPONDIDO.md"
                stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                incoming = project / "_ENTRADA" / f"ROTEIRO_MESTRE_RECEBENDO_{stamp}.md"
                size = self._receive_file(incoming, 64 * 1024 * 1024)
                try:
                    content = incoming.read_text(encoding="utf-8")
                except UnicodeDecodeError as exc:
                    incoming.unlink(missing_ok=True)
                    raise StudioError("O roteiro precisa ser um Markdown UTF-8.") from exc
                if "FR_AUTOEDITE_JSON_BEGIN" not in content or "FR_AUTOEDITE_JSON_END" not in content:
                    incoming.unlink(missing_ok=True)
                    raise StudioError("O Markdown não contém os marcadores do Roteiro Mestre.")
                import fr_autoedite as fr
                from master_contract import inspect_file
                try:
                    with project_scope.project_lock(project):
                        bundle = inspect_file(vars(fr), project, incoming)
                    review = bundle["review"]
                except (fr.AutoEditeError, ValueError, TypeError, KeyError) as exc:
                    incoming.unlink(missing_ok=True)
                    project_scope.write(project / "_CONTROLE/REVISAO_ROTEIRO.json", {"valid": False, "error": str(exc)})
                    raise StudioError(str(exc)) from exc
                if target.is_file():
                    shutil.copy2(target, project / "_HISTORICO" / f"ROTEIRO_MESTRE_RESPONDIDO_{stamp}.md")
                incoming.replace(target)
                project_scope.write(project / "_CONTROLE/REVISAO_ROTEIRO.json", review)
                self._json({"ok": True, "path": str(target), "size_bytes": size, "review": review})
                return
            data = self._read_json()
            if parsed.path == "/api/reset-definitions":
                result = project_scope.reset_definitions(project)
                self._json({"ok": True, "result": result})
                return
            if parsed.path == "/api/roteiro-save":
                with project_scope.project_lock(project):
                    path = project_scope.snapshot_decisions(project, str(data.get("name") or "manual"))
                self._json({"ok": True, "version": path.name})
                return
            if parsed.path == "/api/roteiro-restore":
                result = project_scope.restore_version(project, str(data.get("version") or ""))
                self._json({"ok": True, "result": result})
                return
            if parsed.path == "/api/context":
                target = project / "_ENTRADA" / "CONTEXTO_PROJETO.md"
                if target.is_file():
                    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                    shutil.copy2(target, project / "_HISTORICO" / f"CONTEXTO_PROJETO_{stamp}.md")
                target.write_text(str(data.get("context") or ""), encoding="utf-8")
                self._json({"ok": True, "path": str(target)})
                return
            if parsed.path == "/api/config":
                config = self.state.save_config(project, data.get("config") or {})
                self._json({"ok": True, "config": config})
                return
            if parsed.path == "/api/action":
                self.state.start_job(project, str(data.get("action") or ""))
                self._json({"ok": True})
                return
            if parsed.path == "/api/cancel":
                self.state.cancel_job(project)
                self._json({"ok": True})
                return
            if parsed.path == "/api/trash-files":
                result = self.state.trash_files(project, data.get("paths") or [])
                self._json({"ok": True, "result": result})
                return
            if parsed.path == "/api/restore-trash":
                result = self.state.restore_latest_trash(project)
                self._json({"ok": True, "result": result})
                return
            if parsed.path == "/api/empty-trash":
                result = self.state.empty_project_trash(project, str(data.get("confirmation") or ""))
                self._json({"ok": True, "result": result})
                return
            if parsed.path == "/api/trash-project":
                result = self.state.trash_project(project, str(data.get("confirmation") or ""))
                self._json({"ok": True, "result": result})
                return
            if parsed.path == "/api/plan":
                self.state.save_plan(project, data.get("plan") or {})
                self._json({"ok": True})
                return
            if parsed.path == "/api/reel-plan":
                target = self.state.save_reel_plan(project, data.get("plan") or {})
                self._json({"ok": True, "path": str(target)})
                return
            if parsed.path == "/api/open-folder":
                if shutil.which("xdg-open"):
                    subprocess.Popen(["xdg-open", str(project)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self._json({"ok": True, "path": str(project)})
                return
            self._error("Rota não encontrada.", 404)
        except (StudioError, ValueError, OSError) as exc:
            self._error(str(exc))


def launch_studio(
    app_root: Path, studio_root: Path, host: str = "127.0.0.1", port: int = 8765,
    open_browser: bool = True,
) -> int:
    state = StudioState(app_root, studio_root)
    try:
        server = ThreadingHTTPServer((host, port), StudioHandler)
    except OSError as exc:
        if port == 0 or exc.errno != errno.EADDRINUSE:
            raise
        print(
            f"[FR][ATENÇÃO] A porta {port} está ocupada por outro painel. "
            "Abrindo esta versão corrigida em uma porta livre.",
            flush=True,
        )
        server = ThreadingHTTPServer((host, 0), StudioHandler)
    server.state = state  # type: ignore[attr-defined]
    address, assigned_port = server.server_address
    url = f"http://{address}:{assigned_port}/?v={state.app_version}"
    print(f"[FR] Studio {state.app_version} · TAKEOUT + IA + CARDS CIRCULARES: {url}", flush=True)
    print(f"[FR] Projetos: {state.studio_root}", flush=True)
    print("[FR] Pressione Ctrl+C para encerrar o painel. Renderizações iniciadas continuam registradas no log.", flush=True)
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever(poll_interval=0.4)
    except KeyboardInterrupt:
        print("\n[FR] Studio encerrado.", flush=True)
    finally:
        server.server_close()
    return 0
