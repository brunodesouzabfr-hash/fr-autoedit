# Instalar e atualizar o FR AutoEdite 4.0

## Opção recomendada: instalação normal do usuário

Dentro da pasta distribuída:

```bash
chmod +x install.sh fr-autoedite
./install.sh
fr-autoedite --version
fr-autoedite studio
```

O instalador valida Python, Pillow, FFmpeg e FFprobe; move a instalação de
código anterior para um backup datado e recria o comando em
`~/.local/bin/fr-autoedite`. A pasta de projetos
`~/FR-AutoEdite/Studio/` não é movida nem apagada.

Se você recebeu `FR_AUTOEDITE_4.0.0_CANDIDATO.zip`, primeiro confira o hash
publicado em `SHA256SUMS.txt`, extraia em uma pasta nova e só então execute o
instalador. Não extraia por cima da pasta antiga.

## Instalação lado a lado para homologação

```bash
chmod +x INSTALAR_FR_AUTOEDITE_4.sh
./INSTALAR_FR_AUTOEDITE_4.sh --destino ~/FR-AutoEdite/FR_AUTOEDITE_4.0
~/FR-AutoEdite/FR_AUTOEDITE_4.0/fr-autoedite --version
```

Essa opção cria backup do diretório de destino, ignora `Studio/`, `.env`,
pacotes compactados e resultados locais. Use-a antes de substituir a versão
principal.

## Atualizar a partir da `main`

```bash
cd /CAMINHO/DO/fr-autoedit
git switch main
git pull --ff-only origin main
cd FR_AUTOEDITE_3.4.0_STUDIO
./install.sh
fr-autoedite --version
```

Não use `git reset --hard` nem apague branches para atualizar. Se houver
alterações locais, preserve-as antes de `git pull`.

## Diagnóstico

```bash
fr-autoedite diagnosticar-v4 --check
fr-autoedite --version
ffmpeg -version
ffprobe -version
```

MoviePy, OpenCV, PySceneDetect e demais extras são opcionais. A ausência de um
extra não deve impedir o Studio de abrir. FFmpeg continua sendo o motor final.

Para validar o candidato com pytest:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest tests
bash tests/smoke_test.sh
bash tests/smoke_v4_visual.sh
```

## Reversão

O `install.sh` informa o caminho `fr-autoedite.backup.DATA`. Para reverter,
feche o Studio, mova a instalação atual para outro nome e restaure o backup
para `~/.local/share/fr-autoedite`. Nunca substitua a pasta de projetos.
