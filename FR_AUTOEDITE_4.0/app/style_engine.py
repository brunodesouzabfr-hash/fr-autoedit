"""Indexação segura dos Style Packs do FR AutoEdite.

O módulo não desenha artes finais. Ele resolve contratos declarados em
``manifest.json``, informa slots ausentes e produz uma assinatura de conteúdo
usada pelos caches de prévia e render.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any


DEFAULT_STYLE_PACK_ID = "fr_chiaroscuro_vintage_v1"
STYLE_PACK_ID_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")


class StylePackError(RuntimeError):
    pass


def style_pack_root(app_root: Path, style_pack_id: str) -> Path:
    value = str(style_pack_id or DEFAULT_STYLE_PACK_ID)
    if not STYLE_PACK_ID_RE.fullmatch(value):
        raise StylePackError("style_pack_id inválido; use letras minúsculas, números, hífen ou sublinhado.")
    root = (Path(app_root) / "assets" / "style_packs" / value).resolve()
    packs = (Path(app_root) / "assets" / "style_packs").resolve()
    try:
        root.relative_to(packs)
    except ValueError as exc:
        raise StylePackError("Style Pack fora da instalação.") from exc
    return root


def load_style_pack(app_root: Path, style_pack_id: str = DEFAULT_STYLE_PACK_ID) -> dict[str, Any]:
    root = style_pack_root(app_root, style_pack_id)
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise StylePackError(f"Style Pack não instalado: {style_pack_id}.")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StylePackError(f"manifest.json inválido no Style Pack {style_pack_id}.") from exc
    if not isinstance(manifest, dict) or manifest.get("style_pack_id") != style_pack_id:
        raise StylePackError("manifest.json não coincide com style_pack_id.")
    if not isinstance(manifest.get("assets", {}), dict):
        raise StylePackError("manifest.json: assets deve ser um objeto indexado por asset_id.")
    return manifest


def _safe_pack_asset(root: Path, relative: str) -> Path:
    value = Path(str(relative or ""))
    if value.is_absolute() or not relative or ".." in value.parts:
        raise StylePackError(f"Caminho de asset inválido: {relative!r}.")
    target = (root / value).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise StylePackError(f"Asset fora do Style Pack: {relative!r}.") from exc
    return target


def asset_index(app_root: Path, style_pack_id: str = DEFAULT_STYLE_PACK_ID) -> dict[str, Any]:
    manifest = load_style_pack(app_root, style_pack_id)
    root = style_pack_root(app_root, style_pack_id)
    rows: list[dict[str, Any]] = []
    for asset_id, definition in sorted(manifest.get("assets", {}).items()):
        if not isinstance(definition, dict):
            raise StylePackError(f"Asset {asset_id}: definição deve ser um objeto.")
        relative = str(definition.get("path") or "")
        target = _safe_pack_asset(root, relative)
        installed = target.is_file() and target.stat().st_size > 0
        rows.append({
            "asset_id": str(asset_id),
            "path": relative,
            "kind": str(definition.get("kind") or "image"),
            "required": bool(definition.get("required", False)),
            "installed": installed,
            "fallback": str(definition.get("fallback") or ""),
            "size_bytes": target.stat().st_size if installed else 0,
            "modified_ns": target.stat().st_mtime_ns if installed else 0,
        })
    missing_required = [row["asset_id"] for row in rows if row["required"] and not row["installed"]]
    missing_optional = [row["asset_id"] for row in rows if not row["required"] and not row["installed"]]
    return {
        "style_pack_id": style_pack_id,
        "label": manifest.get("label", style_pack_id),
        "manifest_version": manifest.get("schema_version", 1),
        "ready": not missing_required,
        "assets": rows,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "procedural_fallbacks": bool(manifest.get("procedural_fallbacks", True)),
    }


def resolve_asset(app_root: Path, style_pack_id: str, asset_id: str) -> Path:
    """Resolve um asset explicitamente pedido; ausente é erro, não fallback silencioso."""
    manifest = load_style_pack(app_root, style_pack_id)
    definition = manifest.get("assets", {}).get(str(asset_id))
    if not isinstance(definition, dict):
        raise StylePackError(f"asset_id desconhecido no Style Pack {style_pack_id}: {asset_id}.")
    target = _safe_pack_asset(style_pack_root(app_root, style_pack_id), str(definition.get("path") or ""))
    if not target.is_file() or target.stat().st_size <= 0:
        raise StylePackError(
            f"Asset declarado, mas ainda não instalado: {asset_id} ({definition.get('path', '')})."
        )
    return target


def _hash_file(digest: "hashlib._Hash", path: Path, relative: str) -> None:
    stat = path.stat()
    digest.update(relative.encode("utf-8"))
    digest.update(f"\0{stat.st_size}\0{stat.st_mtime_ns}\0".encode("ascii"))
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)


def style_pack_signature(
    app_root: Path,
    style_pack_id: str = DEFAULT_STYLE_PACK_ID,
    *,
    extra_assets: list[Path] | None = None,
) -> str:
    """Assina manifesto, mtime, tamanho e bytes de todos os assets instalados."""
    root = style_pack_root(app_root, style_pack_id)
    manifest = load_style_pack(app_root, style_pack_id)
    digest = hashlib.sha256()
    digest.update(json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    for definition in manifest.get("assets", {}).values():
        if not isinstance(definition, dict):
            continue
        relative = str(definition.get("path") or "")
        path = _safe_pack_asset(root, relative)
        if path.is_file():
            _hash_file(digest, path, relative)
        else:
            digest.update(("missing\0" + relative).encode("utf-8"))
    for path in sorted({Path(item).resolve() for item in (extra_assets or [])}, key=str):
        if path.is_file():
            _hash_file(digest, path, "external:" + str(path))
        else:
            digest.update(("missing-external\0" + str(path)).encode("utf-8"))
    return digest.hexdigest()[:24]
