#!/usr/bin/env bash
set -euo pipefail

fr_source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
fr_data_base="${XDG_DATA_HOME:-$HOME/.local/share}"
fr_bin_dir="${XDG_BIN_HOME:-$HOME/.local/bin}"
fr_install_dir="$fr_data_base/fr-autoedite"
fr_stage_dir="$fr_data_base/fr-autoedite.installing.$$"
fr_backup_dir=""
fr_applications_dir="$fr_data_base/applications"

cleanup_stage() {
  if [[ -d "$fr_stage_dir" && "$fr_stage_dir" == "$fr_data_base"/fr-autoedite.installing.* ]]; then
    rm -rf -- "$fr_stage_dir"
  fi
}
trap cleanup_stage EXIT

echo "FR AutoEdite 3.4.0 — atualização segura"
echo "Projetos em ~/FR-AutoEdite/Studio serão preservados."

for fr_command in python3 ffmpeg ffprobe; do
  if ! command -v "$fr_command" >/dev/null 2>&1; then
    echo "Dependência ausente: $fr_command" >&2
    echo "No Parrot/Debian: sudo apt update && sudo apt install -y python3 python3-pil ffmpeg unzip zip" >&2
    exit 2
  fi
done
if ! python3 -c 'import PIL' >/dev/null 2>&1; then
  echo "Dependência ausente: python3-pil (Pillow)." >&2
  echo "Instale com: sudo apt install -y python3-pil" >&2
  exit 2
fi

echo "[1/5] Validando o pacote antes de alterar a instalação..."
python3 -m py_compile "$fr_source_dir"/app/*.py
python3 "$fr_source_dir/tests/ai_brief_window_test.py"
python3 "$fr_source_dir/tests/card_circle_test.py"
python3 "$fr_source_dir/tests/preparation_resume_test.py"
python3 "$fr_source_dir/tests/studio_job_recovery_test.py"
python3 "$fr_source_dir/tests/studio_http_test.py"

echo "[2/5] Encerrando somente o painel antigo, se estiver aberto..."
pkill -TERM -f "$fr_install_dir/app/fr_autoedite.py studio" 2>/dev/null || true
sleep 1

echo "[3/5] Preparando a nova instalação..."
mkdir -p -- "$fr_data_base" "$fr_bin_dir" "$fr_applications_dir"
mkdir -p -- "$fr_stage_dir"
cp -a -- "$fr_source_dir/." "$fr_stage_dir/"
chmod +x -- "$fr_stage_dir/fr-autoedite" "$fr_stage_dir/install.sh" "$fr_stage_dir/ATUALIZAR_FR_AUTOEDITE_3.3.1.sh" "$fr_stage_dir/ATUALIZAR_FR_AUTOEDITE_3.4.0.sh"

if [[ -e "$fr_install_dir" ]]; then
  fr_backup_dir="$fr_data_base/fr-autoedite.backup.$(date +%Y%m%d-%H%M%S)"
  mv -- "$fr_install_dir" "$fr_backup_dir"
  echo "Backup criado em: $fr_backup_dir"
fi

rollback() {
  echo "A validação final falhou; restaurando a instalação anterior." >&2
  if [[ -d "$fr_install_dir" && "$fr_install_dir" == "$fr_data_base/fr-autoedite" ]]; then
    mv -- "$fr_install_dir" "$fr_data_base/fr-autoedite.failed.$(date +%Y%m%d-%H%M%S)"
  fi
  if [[ -n "$fr_backup_dir" && -d "$fr_backup_dir" ]]; then
    mv -- "$fr_backup_dir" "$fr_install_dir"
  fi
  exit 3
}

mv -- "$fr_stage_dir" "$fr_install_dir"
ln -sfn -- "$fr_install_dir/fr-autoedite" "$fr_bin_dir/fr-autoedite"

echo "[4/5] Criando o atalho do Studio..."
fr_desktop_file="$fr_applications_dir/fr-autoedite-studio.desktop"
{
  echo '[Desktop Entry]'
  echo 'Type=Application'
  echo 'Name=FR AutoEdite Studio 3.4.0'
  echo 'Comment=Central local de preparação e edição Franco Romeu'
  echo "Exec=$fr_bin_dir/fr-autoedite studio"
  echo 'Terminal=true'
  echo 'Categories=AudioVideo;Video;'
  echo "Icon=$fr_install_dir/assets/franco-romeu-logo.png"
} > "$fr_desktop_file"
chmod 644 -- "$fr_desktop_file"

echo "[5/5] Confirmando a versão instalada..."
fr_version="$($fr_bin_dir/fr-autoedite --versao 2>&1)" || rollback
if [[ "$fr_version" != "FR AutoEdite 3.4.0" ]]; then
  echo "Versão inesperada: $fr_version" >&2
  rollback
fi

trap - EXIT
echo
echo "ATUALIZAÇÃO CONCLUÍDA: $fr_version"
echo "Abra agora com: fr-autoedite studio"
echo "Se o comando não for encontrado, use: $fr_bin_dir/fr-autoedite studio"
echo "A versão anterior permanece no backup informado acima."
