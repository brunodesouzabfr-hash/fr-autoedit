"""Validação Pydantic opcional para o payload v4.

O JSON Schema distribuído continua sendo a autoridade portável. Este módulo
somente acrescenta mensagens de desenvolvimento quando Pydantic v2 existe.
"""
from __future__ import annotations
from typing import Any


def validate(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        from pydantic import BaseModel, ConfigDict, Field
    except ImportError as exc:
        raise RuntimeError("Pydantic opcional não instalado; use o validador stdlib.") from exc

    class Payload(BaseModel):
        model_config = ConfigDict(extra="forbid")
        contrato_versao: str = Field(pattern=r"^4\.0\.0$")
        project_id: str
        input_mode: str
        base_video_id: str | None = None
        timeline_locked: bool
        allow_duration_extension: bool
        duracao_final_estimada_sec: float
        chapters: list[dict]
        cuts: list[dict]
        overlays: list[dict]
        audio: dict
        captions: dict
        social: dict
        style_pack_id: str
        notas_editoriais: str
        legacy_payload: dict | None = None
        main_timeline: dict | None = None
        audio_policy: str | None = None
        allowed_values: dict | None = None

    return Payload.model_validate(payload).model_dump(mode="json")
