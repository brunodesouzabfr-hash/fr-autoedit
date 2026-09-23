"""Validação read-only contra cabeçalho gerado pela aplicação; não aplicar nem renderizar."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'app'))
from fr_v4.contracts.markdown import parse, ContractError
from fr_v4.contracts.validation import validate
from fr_v4.style_packs.registry import load


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('resposta', type=Path)
    parser.add_argument('--base-gerada', type=Path, required=True)
    parser.add_argument('--manifesto', type=Path, required=True)
    args = parser.parse_args()
    try:
        base = parse(args.base_gerada.read_text(encoding='utf-8'))
        document = parse(args.resposta.read_text(encoding='utf-8'))
        result = validate(document, expected_header=base.header,
            manifest=json.loads(args.manifesto.read_text(encoding='utf-8')),
            schema=json.loads((ROOT/'schemas/roteiro_mestre_v4.schema.json').read_text(encoding='utf-8')),
            assets=load(ROOT)['assets'])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        print(json.dumps({'valid': False, 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__': raise SystemExit(main())
