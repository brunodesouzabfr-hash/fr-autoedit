"""Inventário read-only. Não importa nem executa o código auditado."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path


def audit(root: Path) -> dict:
    root = root.resolve()
    files = []
    for path in sorted(root.rglob('*.py')):
        rel = path.relative_to(root)
        if any(p in {'Studio', 'originais', '.venv', '__pycache__', '.git'} for p in rel.parts):
            continue
        data = path.read_bytes()
        tree = ast.parse(data, filename=str(rel))
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                calls = sorted({ast.unparse(call.func) for call in ast.walk(node) if isinstance(call, ast.Call)})
                functions.append({'name': node.name, 'line': node.lineno,
                                  'end_line': node.end_lineno, 'calls': calls})
        files.append({'path': str(rel), 'sha256': hashlib.sha256(data).hexdigest(),
                      'functions': sorted(functions, key=lambda f: f['line'])})
    return {'schema_version': 1, 'mode': 'static_only', 'files': files}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--output', type=Path,
                        help='Salva o inventário JSON além de imprimi-lo quando omitido.')
    args = parser.parse_args()
    content = json.dumps(audit(args.root), ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding='utf-8')
        print(args.output.resolve())
    else:
        print(content, end='')
