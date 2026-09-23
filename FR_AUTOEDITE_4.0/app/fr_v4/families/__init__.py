"""Fachadas tipadas das famílias F1–F6."""

from .f1_capa import spec as capa
from .f2_etapa import spec as etapa
from .f3_servico import spec as servico
from .f4_detalhe import spec as detalhe
from .f5_extra import spec as extra
from .f6_encerramento import spec as encerramento

__all__ = ["capa", "etapa", "servico", "detalhe", "extra", "encerramento"]

