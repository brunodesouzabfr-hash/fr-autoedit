# FR AutoEdite Studio 3.4.0

O FR AutoEdite é um estúdio local de preparação e edição assistida de conteúdo
da Franco Romeu — Arte & Engenharia. Ele organiza fotos e vídeos de obras,
reformas, projetos 3D, instalações, manutenção e bastidores, cria materiais
leves para análise por IA e transforma um roteiro validado em planos de edição
e vídeos renderizados.

A aplicação ajuda a estruturar narrativa, retenção, clareza visual, identidade
Franco Romeu e chamadas para ação. Ela não promete viralização, leads, ROI ou
crescimento. Toda master deve ser revisada por uma pessoa antes da publicação.

## Fluxo principal

```text
ZIP de mídias
→ proxies
→ manifesto
→ PACOTE_PARA_IA
→ Markdown mestre editável
→ resposta da IA externa
→ validação e avisos
→ plano de edição
→ rascunho
→ render final, Reels e Stories
```

O `PACOTE_PARA_IA/` é gerado pela aplicação dentro de cada projeto:

```text
PACOTE_PARA_IA/
├── 00_NAO_EDITAR_CONTEXTO_PROJETO.md
├── 01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE.md
├── 02_NAO_EDITAR_MANIFESTO_MEDIA.json
├── 03_NAO_EDITAR_LOTES_DE_PROXIES/
├── 04_NAO_EDITAR_INSTRUCOES_PARA_IA.md
└── 05_RESPOSTA_DA_IA_IMPORTAR_AQUI.md
```

A IA externa recebe contexto, inventário e proxies, edita o Roteiro Mestre e
devolve somente o Markdown importável. O aplicativo confere IDs, tempos,
janelas de cena, tipos, valores e recursos disponíveis antes de aplicar o plano.

## Recursos atuais

- Studio visual local em `127.0.0.1`;
- importação segura de ZIP e Google Takeout;
- geração retomável de proxies, miniaturas e manifesto;
- lotes independentes de proxies com menos de 150 MB;
- Roteiro Mestre estratégico com filme principal, Reels, Stories e carrossel;
- definição de objetivo, público, plataforma, funil, arco narrativo, hook,
  ritmo, CTA, estratégia de retenção e growth ético;
- seleção de cenas, `start_sec`, `end_sec`, duração, velocidade, cortes,
  transições, frames congelados, cards, balões, locução e legenda;
- classificação e troca de serviço por trecho;
- famílias visuais para 3D, pintura, textura, elétrica, hidráulica,
  revestimentos, iluminação, marcenaria, alvenaria, eventos, instalação e
  manutenção;
- validação com avisos para metadados ainda não executados pelo render;
- proteção contra respostas, anexos, lotes, cards e artefatos duplicados;
- versões recuperáveis de roteiros e renders;
- rascunho por proxies e master pelos originais.

## Instalação pelo GitHub

Requisitos: Linux da família Debian, Ubuntu ou Parrot OS, Git e permissão para
instalar dependências do sistema.

```bash
git clone https://github.com/brunodesouzabfr-hash/fr-autoedit.git
cd fr-autoedit/FR_AUTOEDITE_3.4.0_STUDIO
chmod +x install.sh fr-autoedite
./install.sh
```

Se alguma dependência estiver ausente:

```bash
sudo apt update
sudo apt install -y python3 python3-pil ffmpeg unzip zip xdg-utils
```

Recursos opcionais:

```bash
sudo apt install -y qrencode espeak-ng libsecret-tools rclone libimage-exiftool-perl
```

O instalador preserva a instalação anterior, copia o programa para
`~/.local/share/fr-autoedite/` e cria o comando
`~/.local/bin/fr-autoedite`.

Confirme a instalação:

```bash
fr-autoedite --versao
```

Saída esperada:

```text
FR AutoEdite 3.4.0
```

## Abrir o Studio

```bash
fr-autoedite studio
```

Se o comando ainda não estiver no `PATH`:

```bash
~/.local/bin/fr-autoedite studio
```

O Studio abre no navegador e permanece acessível somente no computador local.
Os projetos ficam, por padrão, em `~/FR-AutoEdite/Studio/`.

## Atualização segura

Antes de atualizar, confirme que não há projeto sendo processado. Na cópia
local do repositório:

```bash
cd /CAMINHO/PARA/fr-autoedit
git switch main
git pull --ff-only origin main
cd FR_AUTOEDITE_3.4.0_STUDIO
./install.sh
fr-autoedite --versao
```

O `install.sh` guarda a instalação anterior em um diretório de backup. Ele não
move nem apaga os projetos de `~/FR-AutoEdite/Studio/`.

Para uma atualização distribuída em arquivo, também existe
`ATUALIZAR_FR_AUTOEDITE_3.4.0.sh`. Consulte
`LEIA_PRIMEIRO_OUTRO_COMPUTADOR.md` antes de usar outro método.

## Uso básico

1. Abra `fr-autoedite studio`.
2. Crie um projeto e escreva o contexto confirmado.
3. Envie o ZIP de fotos e vídeos.
4. Prepare o projeto para gerar proxies e manifesto.
5. Gere o `PACOTE_PARA_IA`.
6. Envie à IA os arquivos indicados e todos os lotes de proxies.
7. Salve a resposta completa em
   `05_RESPOSTA_DA_IA_IMPORTAR_AQUI.md`.
8. Importe e leia os erros, avisos e metadados preservados.
9. Gere e assista ao rascunho.
10. Só então renderize a master pelos originais.

Consulte [GUIA_RAPIDO_3_4.md](GUIA_RAPIDO_3_4.md) para o passo a passo e
[UPGRADE_3.4.0.md](UPGRADE_3.4.0.md) para as mudanças da Fase 2.

## Segurança do repositório

Nunca envie ao GitHub:

- `Studio/`;
- vídeos ou fotos pessoais;
- proxies;
- arquivos ZIP;
- originais;
- renders reais;
- arquivos `.env`;
- tokens;
- chaves;
- credenciais;
- logs pessoais.

O diretório `Studio/` está ignorado pelo Git, mas isso não substitui a
conferência com `git status --short` antes de cada commit. Nunca use
`git add -f` para contornar essa proteção.

## Branches

- `main`: versão estável destinada a instalação e atualização;
- `codex/auditoria-fr-autoedite-3-4`: branch de desenvolvimento e auditoria da
  versão 3.4.0/Fase 2.

Antes de instalar em produção, confirme no GitHub se as mudanças da branch de
desenvolvimento já foram revisadas e integradas à `main`.

## Testes

```bash
python -m pytest tests
bash tests/smoke_test.sh
```

O smoke test cria apenas mídias sintéticas temporárias. Ele verifica pacote IA,
contrato, cards, HTTP local, preparação retomável, renders e saídas sociais.

## Limitações honestas

- IA e heurísticas locais não substituem revisão visual;
- locução sobre vídeo, keyframes arbitrários, múltiplos balões temporizados e
  algumas transições avançadas ainda podem ser preservados apenas como
  metadados;
- a aplicação não publica automaticamente em redes sociais;
- métricas de retenção e conversão dependem dos dados reais da plataforma;
- música, imagem, marca e depoimentos só podem ser usados com autorização e
  evidência.
