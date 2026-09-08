# FR AutoEdite Studio 3.4.0

Miniestúdio local de pós-produção da Franco Romeu para Linux/Parrot OS. A
aplicação recebe um ZIP com fotos e vídeos, contexto e escolhas editoriais;
organiza o material, cria proxies, propõe uma timeline, prepara lotes para
revisão por IA e renderiza versões longas e sociais.

O fluxo principal é gratuito e funciona offline. O Copiloto por API é
opcional, fica desligado por padrão e nunca bloqueia o modo local.

## O que mudou na 3.4.0 — Central da IA e roteiros isolados

- contrato **ROTEIRO MESTRE v2**: a IA pode decidir cortes exatos, reutilizar
  o mesmo vídeo em posições diferentes, criar cards/fotos e congelar frames;
- validação estrutural antes da aplicação, revisão contextual no Studio e
  bloqueio de caminhos não confiáveis, JSON duplicado ou referências de mídia
  inexistentes;
- botão **Apagar definições**: remove escolhas, planos, textos e cards
  regeneráveis, preservando `_ENTRADA`, proxies e o inventário original;
- cada aplicação é uma versão independente em `_ROTEIROS/` e cada render é
  congelado em `_RENDERIZACOES/`, permitindo comparar roteiros sem sobrescrita;
- cards adaptativos por serviço (3D, pintura, textura, revestimentos, móveis,
  produção, criação, alvenaria e iluminação), com explicação de uso e alerta
  de confiança visual;
- sprites/frames reais do vídeo podem ser usados como foto, em antes/depois ou
  em carrossel; transições e áudio são aplicados nos pontos de junção reais;
- prompt operacional em `templates/ROTEIRO_MESTRE_PROMPT.md` e guia de uso em
  `UPGRADE_3.4.0.md`.

## Histórico — o que mudou na 3.3.1

- corrige a importação de cenas `M####C###` com tempo local ou absoluto e
  elimina o erro de início fora da janela;
- retoma preparação interrompida reutilizando proxies e miniaturas concluídos;
- mostra progresso, arquivo atual, heartbeat, cancelamento e nova tentativa no
  log lateral persistente;
- inclui player de vídeo em **Revisar filme**, galeria e gerenciamento seguro
  com lixeira restaurável;
- transmite vídeos grandes por HTTP Range, sem carregar a master 4K inteira na
  memória do navegador;
- gera masters de cards em 4K com logo oficial remasterizada, mármore
  verde-petróleo/esmeralda, dourado acetinado e laranja neon;
- adiciona o encerramento “ARTE & ENGENHARIA — PROJETOS & REFORMAS”.

Recursos consolidados da linha 3.3 (mantidos na 3.4.0):

- Studio reorganizado em oito tarefas guiadas, com uma página exclusiva para
  a ida e a volta de arquivos de qualquer IA;
- arquivos da IA reunidos em `_ENVIAR_IA/`, com nomes que dizem exatamente
  **EDITE E DEVOLVA**, **NÃO EDITE** ou **ENVIE COMO MÍDIA**;
- correção geométrica dos símbolos de serviço: fotos quadradas, verticais ou
  horizontais agora recebem corte central e máscara circular perfeita, sem
  deformação oval;
- estilo **Site FR · Luxo forjado 60/20**, com 60% de verde-petróleo, 20% de
  detalhes laranja e 20% de osso/dourado para contraste;
- time-lapse editorial opcional: escolhe vídeos longos relevantes, acelera o
  conteúdo principal e mantém a seleção editável por cena;
- importador de Google Takeout: lê os JSONs laterais, restaura datas nas
  mídias quando possível e cria um ZIP normalizado sem modificar o original;
- card de serviço opcional com nove categorias visuais: Projetos 3D,
  Revestimentos, Alvenaria, Produções, Pintura, Móveis, Textura, Criações e
  Iluminação;
- símbolos dos anexos integrados como medalhões do próprio card, sem fundo
  quadrado ou aparência de imagem colada;
- upload de intro e outro personalizados em foto ou vídeo, com opção de som,
  duração, inclusão em Reels e composição antes/depois dos cards FR;
- Reels de 30/60/90 segundos com arco obrigatório de começo, meio distribuído
  e resultado final;
- plano separado para cada Reel, permitindo escolher mídias, tempos, textos,
  estabilização, transições e ordem sem alterar o filme principal;
- Roteiro Mestre Markdown exportável e importável para Claude, ChatGPT ou
  qualquer IA capaz de editar JSON;
- logo persistente centralizada no balão e mantida sozinha quando o balão é
  desativado;
- fontes dos textos sobre a mídia independentes das fontes protegidas dos
  cards;
- configuração de qualidade entre rascunho, HD, Full HD, 2K, 4K e dimensão
  máxima dos arquivos originais.

## Atualização segura no computador atual

Descompacte o pacote 3.4.0, abra um terminal dentro da pasta e execute:

```bash
chmod +x ATUALIZAR_FR_AUTOEDITE_3.4.0.sh
./ATUALIZAR_FR_AUTOEDITE_3.4.0.sh
```

O atualizador testa o pacote antes da troca, cria backup da instalação anterior
e preserva os projetos em `~/FR-AutoEdite/Studio`.

## Instalação portátil no Parrot OS, Debian ou Ubuntu

No outro computador, descompacte o pacote, abra um terminal dentro da pasta
`FR-AutoEdite-3.3` e execute:

```bash
chmod +x INSTALAR_EM_OUTRO_COMPUTADOR.sh
./INSTALAR_EM_OUTRO_COMPUTADOR.sh
```

Esse instalador verifica dependências, preserva uma instalação anterior,
instala a aplicação, executa o teste rápido e abre o Studio. Consulte
`LEIA_PRIMEIRO_OUTRO_COMPUTADOR.md` para opções como instalação sem abrir o
painel, recursos opcionais e teste integral.

## Instalação manual

```bash
tar -xzf FR_AUTOEDITE_3.4.0_STUDIO_FINAL.tar.gz
cd FR_AUTOEDITE_3.4.0_STUDIO
chmod +x install.sh fr-autoedite
./install.sh
```

Dependências obrigatórias:

```bash
sudo apt update
sudo apt install -y python3 python3-pil ffmpeg unzip zip xdg-utils
```

Recursos opcionais:

```bash
sudo apt install -y qrencode espeak-ng libsecret-tools rclone libimage-exiftool-perl
```

- `qrencode`: QR Code no encerramento;
- `espeak-ng`: narração local dos cards;
- `libsecret-tools`: cofre do sistema para chave opcional de API;
- `rclone`: autorização e envio ao Google Drive sem senha no projeto.
- `libimage-exiftool-perl`: grava nas mídias as datas encontradas nos JSONs do
  Google Takeout; sem ele, o Studio usa FFmpeg e datas do ZIP como fallback.

Confirme com `fr-autoedite --versao`. O resultado deve ser
`FR AutoEdite 3.4.0`.

## Uso recomendado: Studio visual

```bash
fr-autoedite studio
```

O Studio abre somente em `127.0.0.1`, no próprio computador, e reúne todo o
projeto em uma página. As dez etapas são:

1. **Importar** — criar o projeto, anexar ZIP, contexto e intro/outro;
2. **Montagem** — escolher modo, duração, formato, qualidade e saídas;
3. **Cards e marca** — serviço, estilo, balões, logo, contatos e fontes;
4. **Efeitos e áudio** — transições, estabilização, time-lapse e trilha;
5. **Enviar à IA** — gerar, localizar, baixar e reaplicar o Roteiro Mestre;
6. **Revisar filme** — assistir no player, reordenar e editar a timeline longa;
7. **Editar Reels** — revisar separadamente cada versão social;
8. **Entregar** — renderizar, auditar, localizar arquivos e enviar ao Drive.
9. **Galeria** — visualizar originais, cards, entregas e vídeos sociais;
10. **Gerenciar** — acompanhar armazenamento e limpar somente arquivos
    regeneráveis por uma lixeira restaurável.

Fluxo seguro recomendado:

```text
ZIP + contexto → preparar → revisar cards/timeline → rascunho por proxies
→ ajustar filme e Reels → master pelos originais → auditoria → entrega
```

Os projetos ficam em `~/FR-AutoEdite/Studio/NOME-DO-PROJETO/`. O ZIP
original fica preservado em `_ENTRADA/FR_AUTOEDITE_ENTRADA.zip`.

## Card de serviço

Em **Cards e marca**, ative **Adicionar card após a intro** e escolha uma das
nove categorias. Título, texto, duração, animação e uso nos Reels podem ser
alterados. O símbolo do serviço é recortado e incorporado ao sistema gráfico
FR com máscara fluida, grid, anéis e detalhes técnicos.

O card é opcional. Desativá-lo não remove a arte nem modifica os originais.

## Intro e outro personalizados

Em **Importar**, envie uma imagem ou vídeo para a abertura e/ou encerramento.
Cada arquivo pode:

- entrar antes/depois do card FR ou substituí-lo;
- ter duração própria;
- preservar o áudio original;
- participar ou não dos Reels;
- ficar fora da versão limpa.

Os arquivos são copiados para `_ENTRADA/INTRO_PERSONALIZADA.ext` e
`_ENTRADA/OUTRO_PERSONALIZADO.ext`. Uma nova versão preserva a anterior em
`_HISTORICO/`.

## Reels com começo, meio e fim

Os planos de 30, 60 e 90 segundos não usam apenas o começo da timeline. O
motor distribui as cenas por toda a duração da obra:

- a primeira mídia começa no início do arquivo-fonte;
- cenas intermediárias são amostradas ao longo do projeto;
- a última mídia usa o trecho final e representa o resultado;
- intro, serviço e outro entram apenas quando marcados para Reels.

Na etapa **Editar Reels**, cada versão possui timeline própria. É possível
marcar/desmarcar uma cena, mudar início e duração, editar texto, escolher
transição, estabilizar, reordenar e remover. O filme principal não é alterado.
Planos manuais são preservados; use `--recriar-planos` somente quando quiser
descartá-los.

## Roteiro Mestre para qualquer IA

Depois de preparar o projeto:

1. em **Enviar à IA**, clique em **Gerar Markdown**;
2. baixe e envie somente o arquivo marcado como **EDITE E DEVOLVA**:
   `_ENVIAR_IA/01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE_IA.md`;
3. envie também os lotes de proxies marcados como **ENVIE COMO MÍDIA**, sem
   editar nem descompactar;
4. peça que ela devolva o mesmo Markdown, alterando apenas o JSON entre os
   marcadores `FR_AUTOEDITE_JSON_BEGIN` e `FR_AUTOEDITE_JSON_END`;
5. anexe a resposta em **Markdown respondido**;
6. clique em **Enviar resposta** e depois em **Validar e aplicar**;
7. revise o rascunho antes da master.

O arquivo contém contexto, inventário das mídias, timeline longa, planos de
Reels, cards, tempos, textos sobre o vídeo, legendas, publicação, fontes,
transições e opções permitidas. A importação valida IDs, limites, fontes e
valores antes de modificar o projeto, cria backup e gera
`RELATORIO_APLICACAO_ROTEIRO_IA.json`.

Os mesmos passos funcionam no terminal:

```bash
fr-autoedite gerar-roteiro-ia --projeto CAMINHO_DO_PROJETO
fr-autoedite aplicar-roteiro-ia \
  --projeto CAMINHO_DO_PROJETO \
  --arquivo ROTEIRO_MESTRE_RESPONDIDO.md
```

## Qualidade, efeitos, time-lapse e estabilização

O Studio permite combinar:

- origem por proxies para revisão ou originais para a master;
- qualidade 480p, HD, Full HD, 2K, 4K ou dimensão máxima/original;
- 29 transições, com seleção global e escolha individual por cena;
- Ken Burns para fotos, LUT `.cube`, speed ramp e time-lapse editorial;
- estabilização automática, total ou cena a cena, em três intensidades;
- áudio original, trilha licenciada, ducking, SFX e TTS local opcional.

“Máxima/original” preserva o maior enquadramento detectado, limitado a 8K por
segurança. Não aumenta artificialmente a qualidade de um arquivo pequeno.
Estabilização reduz tremor, mas pode recortar bordas; confira o rascunho.

O time-lapse editorial é diferente de apenas acelerar todo o vídeo. O motor
prioriza vídeos longos selecionados na montagem, usa um trecho-fonte maior e o
comprime no tempo configurado. Velocidade, duração, quantidade máxima e áudio
podem ser definidos globalmente ou ajustados em cada cena na timeline.

## Cards, balões e DNA Franco Romeu

O padrão é **Site FR · Luxo forjado 60/20**. Ele usa o verde-petróleo em fundos
e superfícies dominantes, o laranja em ações, linhas e pontos focais e o
osso/dourado para legibilidade e luxo silencioso. Permanecem disponíveis as
famílias **Forja Técnica**, **Editorial Osso**, **Cinema Petróleo** e
**Blueprint 3D**, com balões em vidro fluente, sólido, contorno ou minimalista.

Símbolos de Projetos 3D, Revestimentos, Alvenaria, Produções, Pintura, Móveis,
Textura, Criações e Iluminação são encaixados por corte central em um círculo
real. O arquivo original não é esticado e o desenho não fica oval.

A logo persistente é alinhada ao centro óptico do balão. Se o balão for
desativado, a logo continua fixa e simétrica. Os cards podem mostrar ícones e
dados de:

- Instagram `@francoromeu.fr`;
- WhatsApp `(11) 99002-1603`;
- Pinterest `@FrancoRomeu.FR`;
- site `https://francoromeu-app.vercel.app/`.

## Google Takeout, Drive e Google Fotos

### Recuperar datas com Google Takeout + JSON

1. abra `takeout.google.com`, desmarque tudo e selecione apenas Google Fotos;
2. nas opções, mantenha somente o álbum desejado e baixe o ZIP;
3. no Studio, em **Importar**, escolha o ZIP em **Google Takeout + JSON**;
4. clique em **Enviar Takeout** e depois em **Restaurar datas e criar ZIP**;
5. confira o relatório em `_TAKEOUT/01_RELATORIO_GOOGLE_TAKEOUT.md`.

O Studio preserva o Takeout recebido em
`_TAKEOUT/00_NAO_EDITAR_GOOGLE_TAKEOUT_ORIGINAL.zip`,
procura `foto.jpg.json` e variantes de nome, recupera `photoTakenTime` ou
`creationTime` e cria `_ENTRADA/FR_AUTOEDITE_ENTRADA.zip`. Com ExifTool, a data
é gravada nos metadados compatíveis; o FFmpeg e a data interna do novo ZIP são
fallbacks. Arquivos sem JSON continuam no pacote e aparecem no relatório.

O Google exige que o próprio usuário solicite e baixe a exportação no Takeout;
o FR AutoEdite processa esse arquivo localmente e não acessa a conta nem guarda
senha.

### Enviar entregas ao Google Drive

O envio ao Drive é opcional e usa a autorização local do `rclone`; nenhuma
senha é salva no projeto.

```bash
rclone config
```

Crie um destino Google Drive, por exemplo `gdrive`, e autorize
`blueprintsplam@gmail.com` ou a conta escolhida no navegador. Em **Entregar**,
informe o mesmo nome, teste a conexão e escolha Master, Social e/ou Editáveis.
O botão Google Fotos abre o fluxo oficial para envio manual; Drive é o destino
automatizado e auditável.

## Análise local e Copiloto

Sem API, a aplicação mede nitidez, marca rajadas semelhantes, sinaliza
possíveis tremores, divide virtualmente vídeos longos em cenas e cria
`originais_organizados/` e `selects/`. Nada é apagado.

O Copiloto visual é opcional e pode usar OpenAI, Anthropic ou Ollama. Sem
credencial, internet ou resposta válida, o plano local permanece intacto. Uma
API pode ter custo separado; Ollama e o fluxo Markdown permitem operação sem
dependência de API paga.

## Lotes para ChatGPT, Claude ou outra IA

Depois de preparar, abra **Enviar à IA**. A pasta principal é:

```text
_ENVIAR_IA/00_COMECE_AQUI_O_QUE_EDITAR_E_ENVIAR.md        NÃO EDITAR
_ENVIAR_IA/01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE_IA.md      EDITAR E DEVOLVER
_ENVIAR_IA/02_NAO_EDITAR_APENAS_ENVIAR_PROMPT.md          NÃO EDITAR
_ENVIAR_IA/03_NAO_EDITAR_LISTA_DE_LOTES.txt               NÃO EDITAR
pacote_chatgpt/FR_AUTOEDITE_LOTE_###.zip                   ENVIAR COMO MÍDIA
```

Cada `FR_AUTOEDITE_LOTE_###.zip` é independente, validado por CRC e menor que
150 MB. Um proxy grande é convertido em MP4s autônomos; não são criadas partes
binárias confusas.

## Arquivos editáveis e caminhos

```text
projeto/
├── _ENTRADA/                  ZIP, contexto, intro/outro e roteiro respondido
├── _EDITAR/                   arquivos claramente nomeados para edição
├── _ENVIAR_IA/                página única: editar, não editar e mídias
├── _ENVIAR_CHATGPT/           compatibilidade com projetos antigos
├── _TAKEOUT/                  original NÃO EDITÁVEL e relatório de datas
├── _HISTORICO/                backups recuperáveis
├── originais/                 extração imutável
├── originais_organizados/     referências por fase
├── selects/                   proxies aprovados
├── proxies/                   mídias leves
├── miniaturas/                quadros de referência
├── contatos_visuais/          pranchas
├── cards_editaveis/           PNGs de prévia
├── pacote_chatgpt/            ZIPs abaixo de 150 MB
├── social/                    planos, capas, Stories e carrossel
├── render/segmentos/          cache retomável
├── entrega/                   rascunhos e masters
├── EDIT_PLAN.json             timeline do filme
├── CARD_STYLE.json            aparência e fontes
├── PUBLICACAO_SOCIAL.md       legenda e publicação
├── ROTEIRO_MESTRE_PARA_IA.md configuração universal
└── 00_MAPA_RAPIDO.md          mapa de caminhos
```

## Comandos principais

```bash
fr-autoedite studio
fr-autoedite novo --zip MATERIAL.zip --contexto CONTEXTO.md
fr-autoedite express --zip MATERIAL.zip --contexto CONTEXTO.md
fr-autoedite preparar --respostas QUESTIONARIO.json
fr-autoedite replanejar --projeto PROJETO --modo cronologico
fr-autoedite draft --projeto PROJETO
fr-autoedite render --projeto PROJETO
fr-autoedite social --projeto PROJETO --usar-proxies
fr-autoedite social --projeto PROJETO --recriar-planos
fr-autoedite cards --projeto PROJETO
fr-autoedite importar-takeout --arquivo TAKEOUT.zip --projeto PROJETO
fr-autoedite gerar-roteiro-ia --projeto PROJETO
fr-autoedite aplicar-roteiro-ia --projeto PROJETO --arquivo RESPOSTA.md
fr-autoedite pacote-chatgpt --projeto PROJETO
fr-autoedite auditar --projeto PROJETO
fr-autoedite exportar-nuvem --projeto PROJETO --testar
fr-autoedite exportar-nuvem --projeto PROJETO
fr-autoedite status --projeto PROJETO
```

Os comandos das versões 2.0 e 3.0 foram preservados.

## Limites honestos

- heurísticas locais não substituem revisão visual do conteúdo;
- uma IA pode escolher cenas inadequadas, mesmo quando o Markdown é válido;
- speed ramp segue regras temporais e não reconhece sozinho o gesto perfeito;
- LUT, TTS, QR e Copiloto dependem do recurso correspondente estar disponível;
- a aplicação não baixa música nem publica automaticamente em redes sociais;
- a master deve usar originais e ser assistida integralmente antes de publicar.

## Teste

```bash
bash tests/smoke_test.sh
```

O teste cria mídia sintética e valida análise local, círculo perfeito dos
serviços, Google Takeout, time-lapse, intro externa, seed, renderização, Reels
com início/meio/fim, Roteiro Mestre, rascunho, auditoria e integridade/tamanho
dos lotes.
