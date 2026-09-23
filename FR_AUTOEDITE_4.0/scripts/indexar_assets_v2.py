"""Cria derivados sem substituir o conjunto original recebido."""
import argparse
import json
from pathlib import Path
import sys
APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT/'app'))
from fr_v4.style_packs.registry import index_assets

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raiz', type=Path, default=APP_ROOT)
    args = parser.parse_args()
    print(json.dumps(index_assets(args.raiz), ensure_ascii=False, indent=2))
