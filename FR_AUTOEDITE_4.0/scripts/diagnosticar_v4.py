"""Diagnóstico isolado: não instala, não baixa modelos, não altera projetos."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'app'))
from fr_v4.adapters.registry import build_registry

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='autotestes apenas dos adapters implementados')
    args = parser.parse_args()
    print(json.dumps(build_registry().diagnose(check=args.check), ensure_ascii=False, indent=2))
