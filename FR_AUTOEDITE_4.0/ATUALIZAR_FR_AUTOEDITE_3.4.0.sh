#!/usr/bin/env bash
set -euo pipefail

# Alias com nome explícito da versão atual. A lógica de atualização permanece
# em um único arquivo para evitar divergência entre instaladores.
fr_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec "$fr_root/ATUALIZAR_FR_AUTOEDITE_3.3.1.sh" "$@"
