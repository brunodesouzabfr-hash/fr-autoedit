"""Controles cooperativos de jobs longos do FR AutoEdite.

O Studio pode solicitar que apenas o item lógico atual seja pulado sem cancelar
o job inteiro. O processo filho consome o marcador em checkpoints seguros e,
quando estiver aguardando ffmpeg/ffprobe, encerra somente aquele subprocesso.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from typing import Any

SKIP_FILE = "_CONTROLE/SKIP_CURRENT_ITEM.json"


class SkipCurrentItem(RuntimeError):
    """Solicitação explícita do usuário para abandonar apenas o item atual."""


def _project(project: str | Path | None = None) -> Path:
    if project:
        return Path(project).expanduser().resolve()
    configured = os.environ.get("FR_AUTOEDITE_PROJECT_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return Path.cwd().resolve()


def marker_path(project: str | Path | None = None) -> Path:
    return _project(project) / SKIP_FILE


def request_skip(project: str | Path, target_item: str = "") -> dict[str, Any]:
    path = marker_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "requested_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "target_item": str(target_item or "").strip(),
    }
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return payload


def clear_skip(project: str | Path | None = None) -> None:
    marker_path(project).unlink(missing_ok=True)


def _matches(target: str, item_id: str) -> bool:
    target = str(target or "").strip()
    item_id = str(item_id or "").strip()
    if not target:
        return True
    if not item_id:
        return False
    if target == item_id:
        return True
    # Uma cena M0036C017 pertence ao proxy M0036. Isso permite interromper a
    # decodificação integral do pai quando a UI mostra a cena como item atual.
    base_target = target.split("C", 1)[0] if target.startswith("M") and "C" in target else target
    base_item = item_id.split("C", 1)[0] if item_id.startswith("M") and "C" in item_id else item_id
    return base_target == base_item


def consume_skip(item_id: str = "", project: str | Path | None = None) -> dict[str, Any] | None:
    path = marker_path(project)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        payload = {"target_item": ""}
    if not _matches(str(payload.get("target_item") or ""), item_id):
        return None
    path.unlink(missing_ok=True)
    return payload


def checkpoint(item_id: str = "", project: str | Path | None = None) -> None:
    payload = consume_skip(item_id=item_id, project=project)
    if payload is not None:
        target = str(payload.get("target_item") or item_id or "item atual")
        raise SkipCurrentItem(f"{target}: item pulado manualmente pelo usuário.")
