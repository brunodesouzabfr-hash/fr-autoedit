# Instalar e atualizar o FR AutoEdite 4.0 beta-next

`FR AutoEdite 4.0 beta-next` é o nome da distribuição de homologação. O
identificador técnico permanece `4.0.0-candidate` no arquivo `VERSION` e na
saída de `fr-autoedite --version`.

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
cd FR_AUTOEDITE_4.0
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

## AutoEdit determinístico

O AutoEdit trabalha somente com projetos `raw_media`. Sem `--aplicar`, o
comando apenas valida e imprime uma proposta, sem gravar a timeline:

```bash
fr-autoedite autoeditar --projeto /CAMINHO/DO/PROJETO
fr-autoedite autoeditar --projeto /CAMINHO/DO/PROJETO --modo automatico
fr-autoedite autoeditar --projeto /CAMINHO/DO/PROJETO --modo cronologico
fr-autoedite autoeditar --projeto /CAMINHO/DO/PROJETO --modo alfabetico
fr-autoedite autoeditar --projeto /CAMINHO/DO/PROJETO --modo aleatorio --seed 731
```

Para publicar o plano validado, use `--aplicar`. Para também produzir uma
prova pelos proxies, combine `--aplicar --draft`; `--somente
branded|clean|both` limita as versões da prova:

```bash
fr-autoedite autoeditar --projeto /CAMINHO/DO/PROJETO --modo automatico --aplicar
fr-autoedite autoeditar --projeto /CAMINHO/DO/PROJETO --modo aleatorio --seed 731 --aplicar --draft --somente both
```

Ao aplicar, o programa cria um snapshot e devolve seu nome no campo
`rollback_version`. A reversão usa os comandos existentes:

```bash
fr-autoedite listar-roteiros --projeto /CAMINHO/DO/PROJETO
fr-autoedite restaurar-roteiro --projeto /CAMINHO/DO/PROJETO --versao NOME_DO_SNAPSHOT
```

Projetos `ready_video` são recusados para preservar a timeline bloqueada e o
vídeo-base. No fluxo `raw_media`, o plano de master aponta para os originais;
somente o draft usa proxies, depois da validação de integridade.

## Reversão

O `install.sh` informa o caminho `fr-autoedite.backup.DATA`. Para reverter,
feche o Studio, mova a instalação atual para outro nome e restaure o backup
para `~/.local/share/fr-autoedite`. Nunca substitua a pasta de projetos.
