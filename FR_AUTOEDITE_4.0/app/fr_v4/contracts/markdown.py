"""YAML restrito + corpo humano + único apêndice JSON. Sem eval e sem YAML tags."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
import re

BEGIN = '<!-- FR_AUTOEDITE_JSON_BEGIN -->'
END = '<!-- FR_AUTOEDITE_JSON_END -->'
HEADER_KEYS = frozenset({'contrato_versao', 'projeto_id', 'gerado_em',
    'hash_manifesto_media', 'duracao_total_estimada_sec', 'input_mode',
    'timeline_locked', 'allow_duration_extension', 'style_pack_id',
    'plataformas_alvo', 'regras_quiet_luxury_ativo'})


class ContractError(ValueError): pass


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def fingerprint(manifest: dict) -> str:
    return 'sha256:'+hashlib.sha256(canonical(manifest).encode('utf-8')).hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ContractError('Chave duplicada: '+key)
        result[key] = value
    return result


def _constant(value): raise ContractError('Constante não JSON: '+value)


def strict_json(value: str):
    try: return json.loads(value, object_pairs_hook=_pairs, parse_constant=_constant)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ContractError('JSON inválido: '+str(exc)) from exc


@dataclass(frozen=True)
class Document:
    header: dict
    body: str
    payload: dict


def parse(text: str) -> Document:
    if len(text.encode('utf-8')) > 8*1024*1024: raise ContractError('Markdown excede 8 MiB.')
    text = text.removeprefix('\ufeff').replace('\r\n', '\n')
    if not text.startswith('---\n'): raise ContractError('Cabeçalho YAML obrigatório.')
    boundary = text.find('\n---\n', 4)
    if boundary < 0: raise ContractError('Cabeçalho YAML não encerrado.')
    header = {}
    for line in text[4:boundary].splitlines():
        match = re.fullmatch(r'([a-z_]+):[ \t]*(.+)', line)
        if not match: raise ContractError('Use YAML plano com valores JSON; sem tags, âncoras ou multiline.')
        key, raw = match.groups()
        if key in header: raise ContractError('Campo YAML duplicado: '+key)
        # JSON é subconjunto seguro de YAML; evita loaders opcionais e ambiguidades.
        header[key] = strict_json(raw)
    if set(header) != HEADER_KEYS: raise ContractError('Campos YAML incompatíveis com contrato v4.')
    if text.count(BEGIN) != 1 or text.count(END) != 1: raise ContractError('Exatamente um apêndice JSON é permitido.')
    left, right = text.index(BEGIN), text.index(END)
    if left <= boundary or right <= left: raise ContractError('Ordem dos marcadores inválida.')
    if text[right+len(END):].strip(): raise ContractError('Não coloque conteúdo após o apêndice.')
    raw = text[left+len(BEGIN):right].strip()
    if not raw.startswith('```json\n') or not raw.endswith('\n```'):
        raise ContractError('Apêndice deve conter uma única cerca json.')
    payload = strict_json(raw[len('```json\n'):-len('\n```')])
    if not isinstance(payload, dict): raise ContractError('Apêndice deve ser objeto JSON.')
    body = text[boundary+5:left].strip()
    if re.search(r'^```json\s*$', body, re.MULTILINE): raise ContractError('JSON adicional no corpo não permitido.')
    return Document(header, body, payload)


def serialize(document: Document) -> str:
    if set(document.header) != HEADER_KEYS: raise ContractError('Header incompleto.')
    header = '\n'.join(f'{key}: {canonical(document.header[key])}' for key in sorted(HEADER_KEYS))
    result = f'---\n{header}\n---\n\n{document.body.strip()}\n\n{BEGIN}\n```json\n'
    result += json.dumps(document.payload, ensure_ascii=False, indent=2, allow_nan=False)
    return result+f'\n```\n{END}\n'
