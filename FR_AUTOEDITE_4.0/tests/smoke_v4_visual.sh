#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
./fr-autoedite --version | grep -F '4.0.0-candidate'
python tests/test_v4_editorial.py
python tests/test_v4_contract_service.py
python tests/test_v4_visual.py
python scripts/diagnosticar_v4.py --check >/dev/null
python -m compileall -q app scripts tests
echo 'SMOKE V4 VISUAL OK'

