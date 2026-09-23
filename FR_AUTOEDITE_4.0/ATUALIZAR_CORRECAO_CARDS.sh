#!/usr/bin/env bash
set -euo pipefail

fr_update_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
fr_user_id="$(id -u)"
fr_data_base="${XDG_DATA_HOME:-$HOME/.local/share}"
fr_bin_dir="${XDG_BIN_HOME:-$HOME/.local/bin}"
fr_bin_path="$fr_bin_dir/fr-autoedite"
fr_log_dir="${XDG_STATE_HOME:-$HOME/.local/state}/fr-autoedite"
fr_log_path="$fr_log_dir/studio-3.4.0.log"
fr_open_studio=true

for fr_argument in "$@"; do
  case "$fr_argument" in
    --sem-abrir) fr_open_studio=false ;;
    --ajuda|-h)
      echo "Uso: ./ATUALIZAR_CORRECAO_CARDS.sh [--sem-abrir]"
      exit 0
      ;;
    *)
      echo "Opção desconhecida: $fr_argument" >&2
      exit 2
      ;;
  esac
done

echo "FR AutoEdite 3.4.0 — atualização segura"
echo "Esta rotina fecha somente painéis FR AutoEdite antigos; os projetos são preservados."

mapfile -t fr_studio_pids < <(
  pgrep -u "$fr_user_id" -f 'app/fr_autoedite[.]py (studio|wizard)' 2>/dev/null || true
)

if ((${#fr_studio_pids[@]})); then
  echo "Encerrando painel antigo para impedir que ele continue exibindo a interface anterior..."
  for fr_pid in "${fr_studio_pids[@]}"; do
    fr_command="$(ps -p "$fr_pid" -o args= 2>/dev/null || true)"
    if [[ "$fr_command" == *"/app/fr_autoedite.py studio"* || "$fr_command" == *"/app/fr_autoedite.py wizard"* ]]; then
      kill -TERM "$fr_pid" 2>/dev/null || true
    fi
  done
  for fr_pid in "${fr_studio_pids[@]}"; do
    for _fr_attempt in {1..50}; do
      kill -0 "$fr_pid" 2>/dev/null || break
      sleep 0.1
    done
    if kill -0 "$fr_pid" 2>/dev/null; then
      echo "O painel antigo não encerrou. Feche o terminal antigo e execute este atualizador novamente." >&2
      exit 3
    fi
  done
fi

"$fr_update_root/install.sh"

fr_installed_version="$($fr_bin_path --versao 2>&1 || true)"
if [[ "$fr_installed_version" != "FR AutoEdite 3.4.0" ]]; then
  echo "A instalação não confirmou a versão 3.4.0: $fr_installed_version" >&2
  exit 4
fi

echo
echo "ATUALIZAÇÃO CONCLUÍDA: FR AutoEdite 3.4.0"
if [[ "$fr_open_studio" == true ]]; then
  mkdir -p "$fr_log_dir"
  nohup "$fr_bin_path" studio >"$fr_log_path" 2>&1 </dev/null &
  fr_new_pid=$!
  sleep 1.5
  if ! kill -0 "$fr_new_pid" 2>/dev/null; then
    echo "O painel novo não iniciou. Últimas mensagens:" >&2
    tail -n 20 "$fr_log_path" >&2 || true
    exit 5
  fi
  echo "Confirme na lateral do navegador: STUDIO 3.4.0 · ROTEIRO ISOLADO"
  echo "O painel novo foi aberto. Log técnico: $fr_log_path"
else
  echo "Instalação concluída sem abrir o painel. Para abrir: fr-autoedite studio"
fi
