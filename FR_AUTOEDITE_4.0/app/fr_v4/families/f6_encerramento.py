"""F6 — encerramento e contato; nunca inventa canais ausentes."""
from ..core.card_renderer import CardSpec


def spec(title: str, body: str = "", *, contacts: tuple[str, ...] = ()) -> CardSpec:
    return CardSpec("F6", title, body, contacts=contacts)

