"""IDs estáveis para roteiros e saídas; não sobrescreve versões existentes."""
from __future__ import annotations
import hashlib
import json


def content_id(payload: dict, prefix: str = "v4") -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return f"{prefix}-{hashlib.sha256(raw.encode()).hexdigest()[:16]}"


def next_version(existing: list[str], scope: str) -> str:
    numbers = []
    prefix = scope + "-v"
    for value in existing:
        if value.startswith(prefix) and value[len(prefix):].isdigit():
            numbers.append(int(value[len(prefix):]))
    return f"{prefix}{max(numbers, default=0)+1:03d}"

