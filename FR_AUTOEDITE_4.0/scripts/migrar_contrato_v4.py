"""Produz arquivo novo para revisão; nunca sobrescreve o roteiro de entrada."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'app'))
import fr_autoedite
from fr_v4.contracts.markdown import serialize
from fr_v4.contracts.migration import from_legacy


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('entrada', type=Path)
    parser.add_argument('--manifesto', type=Path, required=True)
    parser.add_argument('--projeto-id', required=True)
    parser.add_argument('--gerado-em', required=True, help='ISO8601 explícito para reprodutibilidade')
    parser.add_argument('--saida', type=Path, required=True)
    args = parser.parse_args()
    if args.saida.exists() or args.saida.resolve() == args.entrada.resolve():
        parser.error('Saída deve ser arquivo novo, separado da entrada.')
    payload = fr_autoedite.parse_ai_editing_brief(args.entrada)
    document, notes = from_legacy(payload,
        manifest=json.loads(args.manifesto.read_text(encoding='utf-8')),
        project_id=args.projeto_id, generated_at=args.gerado_em)
    with args.saida.open('x', encoding='utf-8') as stream: stream.write(serialize(document))
    print(json.dumps({'output': str(args.saida), 'requires_review': True, 'notices': notes}, ensure_ascii=False, indent=2))
