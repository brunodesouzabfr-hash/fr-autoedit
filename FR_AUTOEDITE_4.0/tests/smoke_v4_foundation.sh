#!/usr/bin/env bash
set -euo pipefail
fr_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$fr_root"
python3 -m pytest -q tests/test_v4_foundation.py
python3 scripts/diagnosticar_v4.py --check
python3 -c 'import sys; sys.path.insert(0,"app"); from fr_v4.adapters.registry import build_registry; rows=build_registry().diagnose(check=True); assert all(r.get("smoke_passed") for r in rows if r["name"] in {"ffmpeg","ffprobe","pillow"}), rows'
printf '%s\n' 'SMOKE V4 FOUNDATION OK — NÃO CERTIFICA RENDER/INTEGRAÇÃO V4'
