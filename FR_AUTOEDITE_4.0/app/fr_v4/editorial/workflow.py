"""Máquina de estados mínima para evitar publicação acidental."""
from __future__ import annotations

TRANSITIONS = {
    "draft": {"validated"},
    "validated": {"previewed", "draft"},
    "previewed": {"approved", "draft"},
    "approved": {"rendered"},
    "rendered": {"qa_passed", "draft"},
    "qa_passed": {"published"},
    "published": set(),
}


def transition(current: str, target: str) -> str:
    if current not in TRANSITIONS or target not in TRANSITIONS[current]:
        raise ValueError(f"Transição de workflow não permitida: {current} → {target}")
    return target


def build_workflow() -> dict:
    return {"state": "draft", "history": [], "publication_blocked": True}

