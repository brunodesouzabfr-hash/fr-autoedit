"""Busca textual local simples sobre manifesto e decisões editoriais."""
from __future__ import annotations
import re


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", value.casefold()))


def search(records: list[dict], query: str, fields: tuple[str, ...] = ("name", "description", "tags")) -> list[dict]:
    wanted = _tokens(query)
    if not wanted:
        return []
    scored = []
    for record in records:
        haystack = " ".join(str(record.get(field, "")) for field in fields)
        score = len(wanted & _tokens(haystack))
        if score:
            scored.append((score, str(record.get("id", "")), record))
    return [row[2] for row in sorted(scored, key=lambda row: (-row[0], row[1]))]

