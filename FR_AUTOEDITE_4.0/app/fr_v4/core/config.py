"""Fonte única dos tokens FR QUIET ENGINEERING ATELIER v2."""
from dataclasses import dataclass
from types import MappingProxyType

DESIGN_VERSION = '2.0.0'
STYLE_PACK_ID = 'fr_quiet_engineering_atelier_v2'
TEXTURE_SEED = 4072026
TOKENS = MappingProxyType({
    'ink': '#031812', 'deep': '#0A2F26', 'petrol': '#123F34',
    'tech': '#1A6069', 'orange': '#FF6B00', 'orange_2': '#FF7A00',
    'gold': '#F6A700', 'bone': '#E6D6B5', 'black': '#0A0A0A',
})
FONTS = MappingProxyType({
    'title': 'StardosStencil-Bold.ttf', 'body': 'Rokkitt-Regular.ttf',
    'technical': 'ShareTechMono-Regular.ttf',
    'editorial': 'CormorantGaramond-Italic.ttf',
})
FORMATS = MappingProxyType({'9X16': (1080, 1920), '1X1': (1080, 1080),
                           '4X5': (1080, 1350), '16X9': (1920, 1080)})
MEDIA_STATUS = frozenset({'obra_real', 'projeto_3d', 'conceito', 'referencia', 'estudo', 'processo'})


@dataclass(frozen=True)
class Service:
    key: str
    label: str
    code: str
    category: str


SERVICES = (
    Service('alvenaria', 'ALVENARIA', 'STR-WALL', 'ESTRUTURA'),
    Service('criacoes', 'CRIAÇÕES', 'AUT-MAKE', 'AUTORIA'),
    Service('eletrica', 'ELÉTRICA', 'MEP-ELE', 'SISTEMAS'),
    Service('hidraulica', 'HIDRÁULICA', 'MEP-HYD', 'SISTEMAS'),
    Service('iluminacao', 'ILUMINAÇÃO', 'MEP-LUX', 'LUZ'),
    Service('instalacao', 'INSTALAÇÃO', 'FIT-INST', 'MONTAGEM'),
    Service('manutencao', 'MANUTENÇÃO', 'OPS-MNT', 'OPERAÇÃO'),
    Service('moveis', 'MÓVEIS', 'MOB-JOIN', 'MARCENARIA'),
    Service('pintura', 'PINTURA', 'FIN-PNT', 'ACABAMENTO'),
    Service('producoes', 'PRODUÇÕES', 'EVT-PROD', 'CENOGRAFIA'),
    Service('projetos_3d', 'PROJETOS', 'ENG-3D', 'PROJETO'),
    Service('revestimentos', 'REVESTIMENTOS', 'FIN-REV', 'ACABAMENTO'),
    Service('textura', 'TEXTURA', 'FIN-TEX', 'MATERIALIDADE'),
)
SERVICE_BY_KEY = MappingProxyType({s.key: s for s in SERVICES})


def palette_rgba(token: str, alpha: int = 255) -> tuple[int, int, int, int]:
    if token not in TOKENS or not 0 <= alpha <= 255:
        raise ValueError('Token/alpha inválido.')
    color = TOKENS[token].lstrip('#')
    return tuple(int(color[i:i+2], 16) for i in (0, 2, 4)) + (alpha,)
