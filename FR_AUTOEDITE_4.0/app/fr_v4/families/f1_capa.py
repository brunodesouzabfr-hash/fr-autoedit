"""F1 — tag superior, título editorial, respiro e assinatura inferior."""
from ..core.card_renderer import CardSpec


def spec(title: str, body: str = "", *, service_key: str = "") -> CardSpec:
    return CardSpec("F1", title, body, service_key=service_key)

