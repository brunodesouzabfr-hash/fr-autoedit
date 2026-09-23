"""F3 — kernel 1:1, medalhão preservado, diagrama e código de coleção."""
from ..core.card_renderer import CardSpec


def spec(service_key: str, title: str, body: str = "") -> CardSpec:
    return CardSpec("F3", title, body, service_key=service_key)

