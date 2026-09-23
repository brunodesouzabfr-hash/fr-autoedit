#!/usr/bin/env bash
set -euo pipefail

fr_portable_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
fr_data_base="${XDG_DATA_HOME:-$HOME/.local/share}"
fr_bin_dir="${XDG_BIN_HOME:-$HOME/.local/bin}"
fr_bin_path="$fr_bin_dir/fr-autoedite"
fr_installed_root="$fr_data_base/fr-autoedite"
fr_state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/fr-autoedite"
fr_portable_log="$fr_state_dir/studio-3.4.0.log"
fr_open_studio=true
fr_install_optionals=false
fr_full_test=false

for fr_argument in "$@"; do
  case "$fr_argument" in
    --sem-abrir) fr_open_studio=false ;;
    --com-opcionais) fr_install_optionals=true ;;
    --teste-completo) fr_full_test=true ;;
    --ajuda|-h)
      echo "Uso: ./INSTALAR_EM_OUTRO_COMPUTADOR.sh [--sem-abrir] [--com-opcionais] [--teste-completo]"
      exit 0
      ;;
    *)
      echo "Opção desconhecida: $fr_argument" >&2
      exit 2
      ;;
  esac
done

echo "============================================================"
echo " FR AUTOEDITE 3.4.0 — INSTALAÇÃO PORTÁTIL GUIADA"
echo "============================================================"
echo "O instalador não apaga projetos nem originais. Uma instalação anterior"
echo "é preservada como backup antes de ser substituída."
echo

fr_linux_family=""
if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  fr_linux_family="${ID:-} ${ID_LIKE:-}"
fi
if [[ "$fr_linux_family" != *debian* && "$fr_linux_family" != *ubuntu* && "$fr_linux_family" != *parrot* ]]; then
  echo "Sistema não reconhecido como Parrot/Debian/Ubuntu." >&2
  echo "A instalação automática de dependências foi interrompida para evitar alterações incorretas." >&2
  echo "Consulte LEIA_PRIMEIRO_OUTRO_COMPUTADOR.md para instalação manual." >&2
  exit 3
fi

fr_missing=false
for fr_command in python3 ffmpeg ffprobe unzip zip xdg-open; do
  if ! command -v "$fr_command" >/dev/null 2>&1; then
    echo "Dependência ausente: $fr_command"
    fr_missing=true
  fi
done
if ! python3 -c 'import PIL' >/dev/null 2>&1; then
  echo "Dependência ausente: python3-pil"
  fr_missing=true
fi

if [[ "$fr_missing" == true ]]; then
  if [[ "$(id -u)" -eq 0 ]]; then
    fr_privilege=()
  elif command -v sudo >/dev/null 2>&1; then
    fr_privilege=(sudo)
  else
    echo "É necessário instalar dependências, mas sudo não foi encontrado." >&2
    exit 4
  fi
  echo
  echo "Instalando dependências obrigatórias pelo gerenciador do sistema..."
  "${fr_privilege[@]}" apt-get update
  "${fr_privilege[@]}" apt-get install -y python3 python3-pil ffmpeg unzip zip xdg-utils
fi

if [[ "$fr_install_optionals" == true ]]; then
  if [[ "$(id -u)" -eq 0 ]]; then
    fr_optional_privilege=()
  elif command -v sudo >/dev/null 2>&1; then
    fr_optional_privilege=(sudo)
  else
    echo "Os opcionais exigem sudo; continuando sem eles." >&2
    fr_optional_privilege=()
  fi
  if [[ "$(id -u)" -eq 0 || ${#fr_optional_privilege[@]} -gt 0 ]]; then
    "${fr_optional_privilege[@]}" apt-get install -y qrencode espeak-ng libsecret-tools rclone libimage-exiftool-perl
  fi
fi

echo
echo "Instalando o FR AutoEdite e preservando versões anteriores..."
"$fr_portable_root/ATUALIZAR_CORRECAO_CARDS.sh" --sem-abrir

fr_version_result="$($fr_bin_path --versao 2>&1 || true)"
if [[ "$fr_version_result" != "FR AutoEdite 3.4.0" ]]; then
  echo "Falha na verificação de versão: $fr_version_result" >&2
  exit 5
fi

echo
echo "Executando teste rápido do Studio e da geração de cards..."
python3 "$fr_installed_root/tests/studio_http_test.py"

if [[ "$fr_full_test" == true ]]; then
  echo
  echo "Executando teste completo com mídias sintéticas e renderizações..."
  bash "$fr_installed_root/tests/smoke_test.sh"
fi

echo
echo "INSTALAÇÃO APROVADA"
echo "Versão: $fr_version_result"
echo "Programa: $fr_installed_root"
echo "Projetos: $HOME/FR-AutoEdite/Studio"
echo "Contexto para IA: $fr_installed_root/CONTEXTO_PARA_IA_AUDITORIA_E_AUTOMACAO.md"

if [[ "$fr_open_studio" == true ]]; then
  mkdir -p "$fr_state_dir"
  nohup "$fr_bin_path" studio >"$fr_portable_log" 2>&1 </dev/null &
  fr_portable_pid=$!
  sleep 1.5
  if ! kill -0 "$fr_portable_pid" 2>/dev/null; then
    echo "A instalação passou, mas o painel não abriu. Últimas mensagens:" >&2
    tail -n 20 "$fr_portable_log" >&2 || true
    echo "Abra manualmente com: $fr_bin_path studio" >&2
    exit 6
  fi
  echo "O Studio foi aberto no navegador. Confira: STUDIO 3.4.0 · ROTEIRO ISOLADO"
  echo "Log do painel: $fr_portable_log"
else
  echo "Para abrir depois: $fr_bin_path studio"
fi
