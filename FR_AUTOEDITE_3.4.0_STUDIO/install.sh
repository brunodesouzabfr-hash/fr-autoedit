#!/usr/bin/env bash
set -euo pipefail

fr_source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
fr_data_base="${XDG_DATA_HOME:-$HOME/.local/share}"
fr_install_dir="$fr_data_base/fr-autoedite"
fr_bin_dir="${XDG_BIN_HOME:-$HOME/.local/bin}"
fr_bin_path="$fr_bin_dir/fr-autoedite"
fr_applications_dir="${XDG_DATA_HOME:-$HOME/.local/share}/applications"

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

mkdir -p "$fr_data_base" "$fr_bin_dir"

if [[ -e "$fr_install_dir" ]]; then
  fr_backup="$fr_data_base/fr-autoedite.backup.$(date +%Y%m%d-%H%M%S)"
  mv -- "$fr_install_dir" "$fr_backup"
  echo "Versão anterior preservada em: $fr_backup"
fi

mkdir -p "$fr_install_dir"
cp -a -- "$fr_source_dir/." "$fr_install_dir/"
chmod +x "$fr_install_dir/fr-autoedite" "$fr_install_dir/install.sh" \
  "$fr_install_dir/ATUALIZAR_FR_AUTOEDITE_3.4.0.sh" \
  "$fr_install_dir/ATUALIZAR_FR_AUTOEDITE_3.3.1.sh" \
  "$fr_install_dir/ATUALIZAR_CORRECAO_CARDS.sh" \
  "$fr_install_dir/INSTALAR_EM_OUTRO_COMPUTADOR.sh"
ln -sfn -- "$fr_install_dir/fr-autoedite" "$fr_bin_path"

mkdir -p "$fr_applications_dir"
fr_desktop_file="$fr_applications_dir/fr-autoedite-studio.desktop"
{
  echo '[Desktop Entry]'
  echo 'Type=Application'
  echo 'Name=FR AutoEdite Studio 3.4.0'
  echo 'Comment=Central local de preparação e edição Franco Romeu'
  echo "Exec=$fr_bin_path studio"
  echo 'Terminal=true'
  echo 'Categories=AudioVideo;Video;'
  echo "Icon=$fr_install_dir/assets/franco-romeu-logo.png"
} > "$fr_desktop_file"
chmod 644 "$fr_desktop_file"

echo "FR AutoEdite instalado em: $fr_install_dir"
echo "Comando criado em: $fr_bin_path"
if [[ ":$PATH:" != *":$fr_bin_dir:"* ]]; then
  echo "Adicione ao seu shell: export PATH=\"$fr_bin_dir:\$PATH\""
fi
echo "Teste agora: fr-autoedite --versao"
echo "Abra a central visual: fr-autoedite studio"
echo "Atalho de aplicativos: FR AutoEdite Studio 3.4.0"
echo "Opcionais: sudo apt install -y qrencode espeak-ng libsecret-tools rclone libimage-exiftool-perl"
