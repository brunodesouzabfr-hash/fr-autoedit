from dataclasses import asdict, dataclass
import math
import re
import unicodedata
from ..core.config import MEDIA_STATUS, TOKENS


@dataclass(frozen=True)
class Violation:
    path: str
    rule: str
    severity: str
    message: str

    def as_dict(self): return asdict(self)


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.casefold()) if not unicodedata.combining(c))


def issue(path, rule, message, severity='error'):
    return Violation(path, rule, severity, message)


def check_veracidade(claims: list, path='claims') -> list[Violation]:
    result = []
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict) or not (claim.get('fonte') or claim.get('confirmado_por')):
            result.append(issue(f'{path}[{index}]', 'veracidade', 'Afirmação requer fonte ou confirmado_por.'))
    return result


def check_contencao(text: str, path='text') -> list[Violation]:
    words = ('incrivel', 'revolucionario', 'imperdivel', 'melhor do mercado',
             'transformador', 'surpreendente', 'espetacular', 'perfeito')
    value = normalized(text)
    found = [word for word in words if re.search(r'(?<!\w)'+re.escape(word)+r'(?!\w)', value)]
    result = [issue(path, 'contencao', 'Hipérbole não permitida: '+word) for word in found]
    if re.search(r'\b(unico|exclusivo)\b', value):
        result.append(issue(path, 'contencao_literal', 'Exclusividade/unicidade requer uso literal comprovado.', 'warning'))
    for pattern in (r'ultimas? vagas?', r'so hoje', r'viraliza[cç][aã]o garantida', r'\d+\s*%.*garantid'):
        if re.search(pattern, value): result.append(issue(path, 'promessa', 'Urgência ou promessa exige reescrita factual.'))
    if value.startswith(('aqui esta', 'como solicitado', 'certamente', 'claro!', 'observacao:')):
        result.append(issue(path, 'comentario_ia', 'Remova comentário da IA do texto renderizável.'))
    return result


def check_silencio(cuts: list, overlays: list, *, preserve_audio=True) -> list[Violation]:
    result = []
    for group, items, minimum in (('cuts', cuts, .4), ('overlays', overlays, 1.2)):
        for index, item in enumerate(items):
            start, end = item.get('start_sec'), item.get('end_sec')
            if not all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in (start, end)):
                result.append(issue(f'{group}[{index}]', 'tempo', 'Tempos devem ser números finitos.'))
            elif end-start < minimum:
                result.append(issue(f'{group}[{index}]', 'silencio', f'Duração mínima: {minimum}s.'))
    cards = sorted((o for o in overlays if o.get('kind') in {'service_card', 'common_card'}
                    and isinstance(o.get('start_sec'), (int, float)) and isinstance(o.get('end_sec'), (int, float))),
                   key=lambda o: o['start_sec'])
    for first, second in zip(cards, cards[1:]):
        gap = second['start_sec']-first['end_sec']
        if gap < .3:
            result.append(issue('overlays', 'respiro', 'Cards consecutivos/sobrepostos precisam de 0,3s de respiro.'))
    # Não impor silêncio artificial no áudio original de ready_video.
    return result


def check_precisao(text: str, media_status=None, claims=None, path='text') -> list[Violation]:
    result = []
    if media_status is not None and media_status not in MEDIA_STATUS:
        result.append(issue(path+'.media_status', 'precisao', 'Status de mídia não reconhecido.'))
    if re.search(r'\d+(?:[.,]\d+)?\s*(?:mm|cm|m²|m2|m|kg|dias?|horas?|K|V|W|%)\b', text) and not claims:
        result.append(issue(path, 'evidencia_numerica', 'Dado técnico requer declaração de evidência.'))
    return result


def check_permanencia(text: str, path='text') -> list[Violation]:
    result = []
    if any(0x1F300 <= ord(c) <= 0x1FAFF for c in text):
        result.append(issue(path, 'permanencia', 'Remova emoji decorativo.'))
    if re.search(r'\b(bora|topzera|partiu|viralizou|trend)\b', normalized(text)):
        result.append(issue(path, 'permanencia', 'Gíria ou tendência não pertence ao texto institucional.'))
    return result


def check_assinatura(palette: dict, font_roles: dict | None = None) -> list[Violation]:
    result = []
    for key, value in palette.items():
        if key not in TOKENS or value.upper() != TOKENS[key]:
            result.append(issue('palette.'+key, 'assinatura', 'Use o token canônico sem recolorir.'))
    return result


def check_tom_de_voz(text: str, path='text', maximum=220) -> list[Violation]:
    return ([issue(path, 'tom_de_voz', f'Máximo {maximum} caracteres; divida o card.')]
            if len(text) > maximum else [])


def validate_text(text: str, *, path='text', claims=None, media_status=None) -> list[Violation]:
    if not isinstance(text, str): return [issue(path, 'tipo', 'Texto deve ser string.')]
    return (check_contencao(text, path)+check_precisao(text, media_status, claims, path)
            +check_permanencia(text, path)+check_tom_de_voz(text, path))
