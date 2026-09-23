# Leia primeiro — instalar em outro computador

O FR AutoEdite Studio 3.4.0 foi preparado para Linux da família Parrot OS,
Debian ou Ubuntu. A instalação principal é local; projetos reais não devem ser
versionados nem enviados ao GitHub.

## Opção recomendada: clonar o GitHub

No computador novo, abra o terminal e execute:

```bash
sudo apt update
sudo apt install -y git python3 python3-pil ffmpeg unzip zip xdg-utils
git clone https://github.com/brunodesouzabfr-hash/fr-autoedit.git
cd fr-autoedit
git switch main
cd FR_AUTOEDITE_3.4.0_STUDIO
chmod +x install.sh fr-autoedite
./install.sh
```

Confira:

```bash
fr-autoedite --versao
fr-autoedite studio
```

Se `fr-autoedite` ainda não estiver no `PATH`:

```bash
~/.local/bin/fr-autoedite studio
```

O instalador:

- verifica `python3`, Pillow, FFmpeg e FFprobe;
- preserva uma instalação anterior como backup;
- instala em `~/.local/share/fr-autoedite/`;
- cria `~/.local/bin/fr-autoedite`;
- não apaga projetos em `~/FR-AutoEdite/Studio/`.

## Instalação guiada do pacote portátil

Se você recebeu a pasta completa por um meio autorizado:

```bash
cd FR_AUTOEDITE_3.4.0_STUDIO
chmod +x INSTALAR_EM_OUTRO_COMPUTADOR.sh
./INSTALAR_EM_OUTRO_COMPUTADOR.sh
```

Opções disponíveis:

```bash
./INSTALAR_EM_OUTRO_COMPUTADOR.sh --sem-abrir
./INSTALAR_EM_OUTRO_COMPUTADOR.sh --com-opcionais
./INSTALAR_EM_OUTRO_COMPUTADOR.sh --teste-completo
```

- `--sem-abrir`: instala sem abrir o navegador;
- `--com-opcionais`: instala QR Code, TTS, cofre, rclone e ExifTool;
- `--teste-completo`: executa o smoke test com mídias sintéticas.

## Atualizar posteriormente

Na cópia clonada:

```bash
cd /CAMINHO/PARA/fr-autoedit
git status --short
git switch main
git pull --ff-only origin main
cd FR_AUTOEDITE_3.4.0_STUDIO
./install.sh
fr-autoedite --versao
```

Se `git status --short` mostrar alterações pessoais, não continue até entender
e preservar essas mudanças. O `git pull --ff-only` evita criar um merge
acidental durante uma atualização comum.

## Onde ficam os arquivos

- instalação: `~/.local/share/fr-autoedite/`;
- comando: `~/.local/bin/fr-autoedite`;
- projetos: `~/FR-AutoEdite/Studio/`;
- backups da instalação:
  `~/.local/share/fr-autoedite.backup.DATA-HORA/`;
- log local do instalador guiado:
  `~/.local/state/fr-autoedite/studio-3.4.0.log`.

O log é local e não deve ser enviado ao GitHub. Caso precise pedir suporte,
revise o conteúdo e compartilhe somente o trecho necessário, sem dados pessoais
ou credenciais.

## Projetos reais e GitHub

Nunca envie ao GitHub:

- `Studio/`;
- vídeos ou fotos;
- proxies;
- ZIPs;
- originais;
- renders reais;
- `.env`;
- tokens;
- chaves;
- credenciais;
- logs pessoais.

O diretório `Studio/` é ignorado pelo repositório, mas confira sempre:

```bash
git status --short
```

Não use `git add -f` para forçar a inclusão desses arquivos. Se possível,
mantenha projetos reais apenas no diretório padrão da instalação, sem copiar
seu conteúdo para outras pastas do repositório.

## Fluxo após instalar

1. Execute `fr-autoedite studio`.
2. Crie o projeto e envie o ZIP de mídias.
3. Gere proxies e manifesto.
4. Gere o `PACOTE_PARA_IA`.
5. Envie o Roteiro Mestre e os lotes para a IA escolhida.
6. Salve e importe a resposta.
7. Leia a validação.
8. Revise o rascunho.
9. Renderize a master pelos originais.

Consulte [GUIA_RAPIDO_3_4.md](GUIA_RAPIDO_3_4.md) para instruções detalhadas.
