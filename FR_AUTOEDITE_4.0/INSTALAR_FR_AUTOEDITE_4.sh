#!/usr/bin/env bash
set -euo pipefail
fr_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$fr_root/scripts/aplicar_atualizacao_v4.py" "$@"

