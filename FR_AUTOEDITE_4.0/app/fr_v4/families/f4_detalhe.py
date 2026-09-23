"""F4 — dado, evidência e materialidade com etiqueta de status quando há imagem."""
from pathlib import Path
from ..core.card_renderer import CardSpec


def spec(title: str, body: str, *, image: Path | None = None, media_status: str | None = None) -> CardSpec:
    return CardSpec("F4", title, body, image=image, media_status=media_status)

