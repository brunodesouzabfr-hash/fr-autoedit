"""Versioned editing decisions, recoverable reset and immutable render inputs.

Media bytes stay in the source project. Every render gets a private workspace;
no active configuration or output is overwritten by a different render.
"""
from __future__ import annotations

import contextlib
import contextvars
import copy
import datetime as dt
import fcntl
import functools
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import uuid

APP_ROOT = Path(__file__).resolve().parents[1]
DECISIONS = (
    "QUESTIONARIO_RESPONDIDO.json", "EDIT_PLAN.json", "EDIT_PLAN_DRAFT.json",
    "CARD_STYLE.json", "SOCIAL_PLAN.json", "PUBLICACAO_SOCIAL.json",
    "PUBLICACAO_SOCIAL.md", "RESUMO_EXECUTIVO_IA.md", "ESTRATEGIA_IA.json",
    "ROTEIRO_MESTRE_PARA_IA.md", "RELATORIO_APLICACAO_ROTEIRO_IA.json",
    "_EDITAR", "social/planos", "_ENVIAR_IA",
    "PACOTE_PARA_IA/01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE.md",
    "PACOTE_PARA_IA/05_RESPOSTA_DA_IA_IMPORTAR_AQUI.md",
    "_ENVIAR_CHATGPT/03_ROTEIRO_MESTRE_PARA_IA.md", "_CONTROLE/REVISAO_ROTEIRO.json",
)
SOURCE_KEYS = {"source_path", "proxy_path", "thumbnail_path", "music_path", "color_lut",
               "intro_path", "outro_path"}
_held = contextvars.ContextVar("fr_project_locks", default=())
_render = contextvars.ContextVar("fr_render_snapshot", default=None)


def read(path, default=None):
    return json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).is_file() else copy.deepcopy(default)


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode()).hexdigest()


def timestamp():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


@contextlib.contextmanager
def project_lock(project):
    """One writer per project, including CLI vs Studio; nested calls are safe."""
    project = Path(project).resolve()
    key = str(project)
    if key in _held.get():
        yield
        return
    lockfile = project / "_CONTROLE" / "EDICAO.lock"
    lockfile.parent.mkdir(parents=True, exist_ok=True)
    with lockfile.open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("Este projeto está ocupado. Aguarde a tarefa terminar para alterar suas definições.") from exc
        token = _held.set((*_held.get(), key))
        try:
            recover_transaction(project)
            yield
        finally:
            _held.reset(token)
            fcntl.flock(stream, fcntl.LOCK_UN)


def identity(project, manifest):
    path = Path(project) / "_CONTROLE" / "MEDIA_LIBRARY.json"
    data = read(path, {})
    if not data.get("project_id"):
        data = {"project_id": str(uuid.uuid4()), "created_at": timestamp()}
        write(path, data)
    keys = ("id", "media_type", "source_path", "duration_sec", "parent_video",
            "scene_start_sec", "scene_end_sec", "sha256", "sha256_short", "file_hash", "size_bytes")
    rows = [{k: row.get(k) for k in keys if k in row} for row in manifest.get("media", [])]
    return {"project_id": data["project_id"], "media_fingerprint": digest(sorted(rows, key=lambda r: r.get("id", "")))}


def copy_decisions(source, target):
    source, target = Path(source), Path(target)
    target.mkdir(parents=True, exist_ok=True)
    for relative in DECISIONS:
        src, dst = source / relative, target / relative
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        elif src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def snapshot_decisions(project, name="manual", *, roteiro=None):
    project = Path(project)
    name = re.sub(r"[^a-zA-Z0-9_-]", "-", name)[:72] or "manual"
    target = project / "_ROTEIROS" / (timestamp() + "_" + name)
    copy_decisions(project, target)
    for relative in ("_ENTRADA/CONTEXTO_PROJETO.md", "_ENTRADA/ROTEIRO_MESTRE_RESPONDIDO.md"):
        src = project / relative
        if src.is_file():
            (target / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target / relative)
    active = read(project / "_CONTROLE" / "ROTEIRO_ATIVO.json", {})
    metadata = {"name": name, "saved_at": timestamp(), "roteiro": roteiro or active,
                "files": {p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in target.rglob("*") if p.is_file()}}
    write(target / "VERSION.json", metadata)
    return target


def recover_transaction(project):
    journal = Path(project) / "_CONTROLE" / "TRANSACTION.json"
    data = read(journal, {})
    if not data:
        return
    root = Path(project) / data["directory"]
    if data.get("status") == "committed":
        journal.unlink(missing_ok=True)
        return
    for relative in data["paths"]:
        path, backup = Path(project) / relative, root / "before" / relative
        if backup.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, path)
        elif not data["existed"].get(relative):
            path.unlink(missing_ok=True)
    journal.unlink(missing_ok=True)


def publish_files(project, files, *, delete=()):
    """Validate/build first; publish a recoverable multi-file transaction."""
    project = Path(project)
    root = project / "_HISTORICO" / ("TRANSACAO_" + timestamp())
    paths = list(dict.fromkeys([*files, *delete]))
    existed = {}
    for relative in paths:
        path = project / relative
        path.resolve().relative_to(project.resolve())
        existed[relative] = path.is_file()
        if path.is_file():
            backup = root / "before" / relative
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, backup)
        if relative in files:
            staged = root / "after" / relative
            staged.parent.mkdir(parents=True, exist_ok=True)
            value = files[relative]
            if isinstance(value, bytes):
                staged.write_bytes(value)
            elif isinstance(value, str):
                staged.write_text(value, encoding="utf-8")
            else:
                write(staged, value)
    journal = project / "_CONTROLE" / "TRANSACTION.json"
    record = {"directory": root.relative_to(project).as_posix(), "paths": paths,
              "existed": existed, "status": "publishing"}
    write(journal, record)
    try:
        for relative in paths:
            target = project / relative
            if relative in files:
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(root / "after" / relative, target)
            else:
                target.unlink(missing_ok=True)
        record["status"] = "committed"
        write(journal, record)
        journal.unlink(missing_ok=True)
    except BaseException:
        recover_transaction(project)
        raise
    return root


def reset_definitions(project):
    project = Path(project)
    with project_lock(project):
        archive = snapshot_decisions(project, "antes-do-reset")
        old = read(project / "QUESTIONARIO_RESPONDIDO.json", {})
        config = read(APP_ROOT / "templates/questionario_base.json")
        for key in ("name", "slug", "zip_path", "workspace_root", "context_file"):
            if key in old.get("project", {}):
                config["project"][key] = old["project"][key]
        for role in ("intro", "outro"):
            config["external_intro_outro"][role + "_path"] = old.get("external_intro_outro", {}).get(role + "_path", "")
            config["external_intro_outro"][role + "_enabled"] = False
        config["context"] = {"text": "", "cta": "", "desired_message": ""}
        config["story"]["chronology"] = []
        config["story"]["objective"] = ""
        config["ai_copilot"]["enabled"] = False
        config["cloud_export"]["enabled"] = False
        config["editing_brief"]["scenario_name"] = "novo-roteiro"
        files = {"QUESTIONARIO_RESPONDIDO.json": config,
                 "_EDITAR/01_CONFIGURACOES_DO_PROJETO.json": config,
                 "CARD_STYLE.json": read(APP_ROOT / "templates/card_style.json"),
                 "_ENTRADA/CONTEXTO_PROJETO.md": "",
                 "_CONTROLE/REVISAO_ROTEIRO.json": {},
                 "_CONTROLE/ROTEIRO_ATIVO.json": {"status": "reset", "reset_at": timestamp(), "backup": archive.name}}
        remove = []
        for relative in (*DECISIONS, "_ENTRADA/ROTEIRO_MESTRE_RESPONDIDO.md"):
            path = project / relative
            candidates = list(path.rglob("*")) if path.is_dir() else [path]
            remove.extend(p.relative_to(project).as_posix() for p in candidates if p.is_file() and p.relative_to(project).as_posix() not in files)
        publish_files(project, files, delete=remove)
        # Only regenerable previews; source files, historical outputs and proxies stay.
        if (project / "cards_editaveis").is_dir():
            shutil.move(str(project / "cards_editaveis"), str(archive / "cards_editaveis"))
        return {"backup": archive.name, "media_preserved": True, "status": "reset"}


def list_versions(project):
    result = []
    for path in sorted((Path(project) / "_ROTEIROS").glob("*/VERSION.json"), reverse=True):
        data = read(path, {})
        result.append({"id": path.parent.name, "name": data.get("name"), "saved_at": data.get("saved_at"),
                       "roteiro": data.get("roteiro", {})})
    return result[:150]


def restore_version(project, version):
    project = Path(project)
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", version):
        raise ValueError("Versão inválida.")
    source = project / "_ROTEIROS" / version
    meta = read(source / "VERSION.json", {})
    if not meta:
        raise ValueError("Versão não encontrada.")
    with project_lock(project):
        snapshot_decisions(project, "antes-de-restaurar")
        files = {}
        for relative, expected in meta.get("files", {}).items():
            p = source / relative
            p.resolve().relative_to(source.resolve())
            content = p.read_bytes()
            if hashlib.sha256(content).hexdigest() != expected:
                raise ValueError("A cópia salva foi modificada: " + relative)
            files[relative] = content
        deletes = []
        for relative in DECISIONS:
            p = project / relative
            for item in (p.rglob("*") if p.is_dir() else [p]):
                if item.is_file() and item.relative_to(project).as_posix() not in files:
                    deletes.append(item.relative_to(project).as_posix())
        files["_CONTROLE/ROTEIRO_ATIVO.json"] = meta.get("roteiro", {})
        publish_files(project, files, delete=deletes)
    return {"restored": version}


def _absolute_references(value, project):
    if isinstance(value, list):
        return [_absolute_references(x, project) for x in value]
    if not isinstance(value, dict):
        return value
    out = {}
    for key, item in value.items():
        if key in SOURCE_KEYS and isinstance(item, str) and item.strip():
            candidate = Path(item).expanduser()
            out[key] = str(candidate.resolve() if candidate.is_absolute() else (project / candidate).resolve())
        else:
            out[key] = _absolute_references(item, project)
    return out


def isolated_render(fn):
    """Freeze all decisions at action start, also when called directly via Python."""
    @functools.wraps(fn)
    def wrapped(project, *args, **kwargs):
        project = Path(project).resolve()
        active = _render.get()
        if active and project == active:
            return fn(project, *args, **kwargs)
        with project_lock(project):
            active_meta = read(project / "_CONTROLE/ROTEIRO_ATIVO.json", {})
            name = re.sub(r"[^a-zA-Z0-9_-]", "-", str(active_meta.get("id", "manual")))[:64]
            snapshot = project / "_RENDERIZACOES" / (timestamp() + "_" + name + "_" + fn.__name__)
            copy_decisions(project, snapshot)
            for filename in ("MANIFESTO_MEDIA.json",):
                if (project / filename).is_file():
                    shutil.copy2(project / filename, snapshot / filename)
            for p in list(snapshot.rglob("*.json")):
                write(p, _absolute_references(read(p), project))
            # Freeze user-supplied LUT/music/intro/outro by content; bulk source
            # video remains a read-only reference and is fingerprinted below.
            config = read(snapshot / "QUESTIONARIO_RESPONDIDO.json", {})
            style = read(snapshot / "CARD_STYLE.json", read(APP_ROOT / "templates/card_style.json"))
            # Assets that the renderer resolves relative to the project.
            for block, key in ((style.get("logo", {}), "file"),):
                value = block.get(key)
                if value and (project / value).is_file():
                    dest = snapshot / "_ASSETS" / Path(value).name
                    dest.parent.mkdir(exist_ok=True)
                    shutil.copy2(project / value, dest)
                    block[key] = str(dest)
            write(snapshot / "CARD_STYLE.json", style)
            media = read(snapshot / "MANIFESTO_MEDIA.json", {}).get("media", [])
            fingerprints = {}
            for row in media:
                for key in ("source_path", "proxy_path"):
                    value = row.get(key)
                    if value and Path(value).is_file() and value not in fingerprints:
                        stat = Path(value).stat()
                        fingerprints[value] = {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
            record = {"status": "running", "started_at": timestamp(), "source_project": str(project),
                      "roteiro": active_meta, "action": fn.__name__, "media": fingerprints,
                      "decisions_hash": digest({p.relative_to(snapshot).as_posix(): read(p)
                                               for p in snapshot.rglob("*.json")})}
            write(snapshot / "RENDER_RUN.json", record)
            changed_args = []
            for arg in args:
                if isinstance(arg, Path):
                    dest = snapshot / arg.name
                    try:
                        dest = snapshot / arg.resolve().relative_to(project)
                    except ValueError:
                        pass
                    if arg.is_file() and not dest.is_file():
                        write(dest, _absolute_references(read(arg), project))
                    changed_args.append(dest)
                elif isinstance(arg, dict):
                    changed_args.append(_absolute_references(copy.deepcopy(arg), project))
                else:
                    changed_args.append(arg)
            token = _render.set(snapshot)
            try:
                result = fn(snapshot, *changed_args, **kwargs)
                changed = [p for p, stat in fingerprints.items() if not Path(p).is_file() or
                           {"size": Path(p).stat().st_size, "mtime_ns": Path(p).stat().st_mtime_ns} != stat]
                if changed:
                    raise ValueError("Uma mídia foi alterada durante o render. Repita após concluir a cópia: " + changed[0])
                # Mantém uma cópia operacional no caminho legado ``entrega``/
                # ``social`` para que integrações existentes continuem
                # encontrando a última versão. A fonte da verdade permanece o
                # snapshot imutável em ``_RENDERIZACOES``; uma renderização
                # posterior pode substituir apenas essa cópia corrente sem
                # tocar no histórico anterior.
                published = []
                for item in result:
                    output = Path(item)
                    try:
                        relative = output.resolve().relative_to(snapshot.resolve())
                    except ValueError:
                        continue
                    if not output.is_file():
                        continue
                    destination = project / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(output, destination)
                    published.append(str(destination))
                for relative in (
                    Path("entrega/RELATORIO_ENTREGA.md"),
                    Path("social/PACOTE_EDITORIAL.md"),
                    Path("social/RELATORIO_SOCIAL.md"),
                ):
                    source = snapshot / relative
                    if source.is_file():
                        destination = project / relative
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source, destination)
                record.update(status="completed", finished_at=timestamp(), outputs=[str(p) for p in result],
                              published_outputs=published)
                write(project / "_CONTROLE/ULTIMA_RENDERIZACAO.json", record | {"directory": str(snapshot)})
                return result
            except BaseException as exc:
                record.update(status="failed", finished_at=timestamp(), error=str(exc))
                raise
            finally:
                write(snapshot / "RENDER_RUN.json", record)
                _render.reset(token)
    return wrapped
