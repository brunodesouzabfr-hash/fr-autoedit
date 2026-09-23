"""F5 — citação, nota, CTA e comparação remontada por formato."""
from pathlib import Path
from ..core.card_renderer import CardSpec


def spec(title: str, body: str = "", *, subtype: str = "note", image: Path | None = None,
         comparison_image: Path | None = None, media_status: str | None = None) -> CardSpec:
    return CardSpec("F5", title, body, subtype=subtype, image=image,
                    comparison_image=comparison_image, media_status=media_status)

