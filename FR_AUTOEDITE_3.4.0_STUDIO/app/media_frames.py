"""Extract actual video frames; references are resolved against the manifest."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import uuid


def extract_reference(env, project, reference, use_proxies=False):
    c = SimpleNamespace(**env)
    project = Path(project)
    row = next((r for r in c.read_json(project / "MANIFESTO_MEDIA.json").get("media", [])
                if r.get("id") == reference.get("media_id")), None)
    if not row:
        raise c.AutoEditeError("Referência visual não encontrada: " + str(reference.get("media_id")))
    source = project / str(row.get("proxy_path" if use_proxies else "source_path") or "")
    if not source.is_file():
        source = project / str(row.get("source_path" if use_proxies else "proxy_path") or "")
    if not source.is_file():
        raise c.AutoEditeError("Fonte da imagem indisponível: " + str(source))
    if row.get("media_type") == "image":
        return source
    second = float(reference.get("time_sec", 0))
    if reference.get("time_basis") == "scene_local":
        second += float(row.get("scene_start_sec") or 0)
    stat = source.stat()
    key = hashlib.sha256(json.dumps([str(source.resolve()), stat.st_size, stat.st_mtime_ns,
                                     second, c.APP_VERSION]).encode()).hexdigest()[:24]
    target = project / "frames_extraidos" / (key + ".png")
    if target.is_file():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(key + "." + uuid.uuid4().hex + ".png")
    try:
        c.run(["ffmpeg", "-y", "-nostdin", "-hide_banner", "-loglevel", "error", "-ss", f"{second:.6f}",
               "-i", str(source), "-frames:v", "1", "-threads", "1", str(temp)])
        if not temp.is_file() or temp.stat().st_size == 0:
            raise c.AutoEditeError(f"Não foi possível extrair o quadro em {second:.3f}s de {row['id']}.")
        temp.replace(target)
    finally:
        temp.unlink(missing_ok=True)
    return target


def source_signatures(project, segment, plan, style):
    paths = set()
    def collect(data):
        if isinstance(data, dict):
            for k, v in data.items():
                if k in {"source_path", "proxy_path", "thumbnail_path", "music_path", "color_lut"} and isinstance(v, str) and v:
                    paths.add(v)
                else:
                    collect(v)
        elif isinstance(data, list):
            for v in data:
                collect(v)
    collect(segment)
    collect(plan.get("audio", {}))
    collect(plan.get("visual_effects", {}))
    collect(style)
    result = {}
    for v in sorted(paths):
        p = Path(v).expanduser()
        if not p.is_absolute():
            p = Path(project) / p
        if p.is_file():
            st = p.stat()
            result[str(p.resolve())] = [st.st_size, st.st_mtime_ns]
        else:
            result[str(p)] = "missing"
    return result
