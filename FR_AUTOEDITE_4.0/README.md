# FR AutoEdite Studio 4.0 beta-next

Esta distribuição **FR AutoEdite 4.0 beta-next** implementa o **FR Quiet
Engineering Atelier** sobre a base 3.4.0, preservando o pipeline FFmpeg, a CLI
e o fluxo de projetos. O identificador técnico em `VERSION` permanece
`4.0.0-candidate`; `beta-next` identifica esta distribuição de homologação,
sem alterar contratos persistidos. A aprovação visual e a instalação na
máquina do usuário continuam sendo etapas explícitas.

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

Para um filme que já chega editado, o Studio oferece um fluxo separado e não
destrutivo:

```text
Vídeo já editado
→ cópia íntegra + SHA-256
→ proxy e referências para análise
→ Roteiro Mestre com timeline bloqueada
→ overlays temporizados
→ prévia curta
→ render final separado, sem remontar o vídeo-base
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
- entrada alternativa de vídeo já editado, com duração, resolução, FPS, áudio,
  ordem e velocidade bloqueados;
- overlays temporizados de card, balão, callout, lower third, legenda e logo;
- Style Pack de vídeo pronto `fr_chiaroscuro_vintage_v1` preservado e novo
  sistema de cards `fr_quiet_engineering_atelier_v2`, com famílias F1–F6,
  13 diagramas e cache invalidado quando estilo, serviço ou asset muda;
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

## Instalação/atualização pelo GitHub

Requisitos: Linux da família Debian, Ubuntu ou Parrot OS, Git e permissão para
instalar dependências do sistema.

```bash
git clone https://github.com/brunodesouzabfr-hash/fr-autoedit.git
cd fr-autoedit/FR_AUTOEDITE_4.0
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
fr-autoedite --version
```

Saída esperada:

```text
FR AutoEdite 4.0.0-candidate
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
cd FR_AUTOEDITE_4.0
./install.sh
fr-autoedite --version
```

O `install.sh` guarda a instalação anterior em um diretório de backup. Ele não
move nem apaga os projetos de `~/FR-AutoEdite/Studio/`.

Para compatibilidade com instalações anteriores, o alias legado
`ATUALIZAR_FR_AUTOEDITE_3.4.0.sh` detecta a versão pelo arquivo `VERSION` e
também reconhece a estrutura 4.0. Consulte
`LEIA_PRIMEIRO_OUTRO_COMPUTADOR.md` antes de usar outro método.

## Uso básico

### Mídias brutas

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

### Vídeo já editado

1. Crie um projeto e escolha **Vídeo já editado** em Importar.
2. Envie o vídeo-base e deixe **Permitir intro/outro estender a entrega**
   desligado, salvo quando a extensão for realmente desejada.
3. Em Montagem, clique em **Preparar vídeo e referências**. Os controles de
   corte, ordem, velocidade e qualidade do filme-base permanecem ocultos.
4. Gere o Roteiro Mestre para a IA ou vá a Revisar filme e crie os overlays
   manualmente.
5. Salve as camadas, gere a prévia e confira seus intervalos no relógio do
   vídeo-base.
6. Renderize o vídeo pronto. A saída é criada em `entrega/`; o original em
   `_ENTRADA/` não é alterado.

Os mesmos passos podem ser executados por terminal:

```bash
fr-autoedite preparar-video-pronto --arquivo VIDEO.mp4 --respostas QUESTIONARIO_RESPONDIDO.json --projeto /CAMINHO/DO/PROJETO
fr-autoedite preview-video-pronto --projeto /CAMINHO/DO/PROJETO
fr-autoedite render-video-pronto --projeto /CAMINHO/DO/PROJETO
fr-autoedite reindexar-assets --projeto /CAMINHO/DO/PROJETO
```

### AutoEdit determinístico (somente mídias brutas)

O comando abaixo valida e mostra uma proposta sem alterar o projeto:

```bash
fr-autoedite autoeditar --projeto /CAMINHO/DO/PROJETO
```

Escolha explicitamente a ordenação quando necessário:

```bash
fr-autoedite autoeditar --projeto /CAMINHO/DO/PROJETO --modo automatico
fr-autoedite autoeditar --projeto /CAMINHO/DO/PROJETO --modo cronologico
fr-autoedite autoeditar --projeto /CAMINHO/DO/PROJETO --modo alfabetico
fr-autoedite autoeditar --projeto /CAMINHO/DO/PROJETO --modo aleatorio --seed 731
```

`--aplicar` publica a proposta somente depois da validação e cria um snapshot
recuperável. `--draft` exige `--aplicar` e renderiza uma prova pelos proxies;
`--somente branded|clean|both` escolhe as versões dessa prova:

```bash
fr-autoedite autoeditar --projeto /CAMINHO/DO/PROJETO --modo automatico --aplicar
fr-autoedite autoeditar --projeto /CAMINHO/DO/PROJETO --modo aleatorio --seed 731 --aplicar --draft --somente both
```

O JSON devolvido por `--aplicar` informa `rollback_version`. Para listar e
restaurar snapshots:

```bash
fr-autoedite listar-roteiros --projeto /CAMINHO/DO/PROJETO
fr-autoedite restaurar-roteiro --projeto /CAMINHO/DO/PROJETO --versao NOME_DO_SNAPSHOT
```

O AutoEdit determinístico é bloqueado em projetos `ready_video`, pois a
timeline do vídeo-base é imutável. Em `raw_media`, a master continua apontando
para os originais; proxies verificados são usados somente no `--draft`. O
processo é local, offline e continua exigindo revisão visual humana.

Os nomes e dimensões dos slots de arte estão em
`assets/style_packs/fr_chiaroscuro_vintage_v1/ASSET_REQUIREMENTS.md`. Slots
ausentes usam composição procedural; um `asset_id` explícito só é aceito se o
arquivo existir e tiver conteúdo.

Consulte [GUIA_RAPIDO_3_4.md](GUIA_RAPIDO_3_4.md) para o passo a passo e
[UPGRADE_3.4.0.md](UPGRADE_3.4.0.md) para as mudanças da Fase 2.

Para instalação lado a lado a partir do pacote 4.0, use:

```bash
chmod +x INSTALAR_FR_AUTOEDITE_4.sh
./INSTALAR_FR_AUTOEDITE_4.sh --destino ~/FR-AutoEdite/FR_AUTOEDITE_4.0
~/FR-AutoEdite/FR_AUTOEDITE_4.0/fr-autoedite --version
```

O guia completo está em
[`docs/GUIA_INSTALACAO_ATUALIZACAO_4_0.md`](docs/GUIA_INSTALACAO_ATUALIZACAO_4_0.md).

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
python3 -m pip install -r requirements-dev.txt
python -m pytest tests
bash tests/smoke_test.sh
bash tests/smoke_v4_visual.sh
```

O smoke test cria apenas mídias sintéticas temporárias. Ele verifica pacote IA,
contrato, cards, HTTP local, preparação retomável, renders e saídas sociais.
O relatório da execução deste candidato está em
[`docs/RELATORIO_VALIDACAO_4_0.md`](docs/RELATORIO_VALIDACAO_4_0.md).

## Limitações honestas

- IA e heurísticas locais não substituem revisão visual;
- no fluxo de mídias brutas, locução sobre vídeo, keyframes arbitrários,
  múltiplos balões temporizados e algumas transições avançadas ainda podem ser
  preservados apenas como metadados;
- a aplicação não publica automaticamente em redes sociais;
- métricas de retenção e conversão dependem dos dados reais da plataforma;
- música, imagem, marca e depoimentos só podem ser usados com autorização e
  evidência.
