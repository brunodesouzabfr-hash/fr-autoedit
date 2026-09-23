"""F2 — capítulo técnico; hierarquia fixa e diagrama contextual opcional."""
from ..core.card_renderer import CardSpec


def spec(title: str, body: str = "", *, number: str = "", service_key: str = "") -> CardSpec:
    return CardSpec("F2", title, body, service_key=service_key, stage_number=number)

