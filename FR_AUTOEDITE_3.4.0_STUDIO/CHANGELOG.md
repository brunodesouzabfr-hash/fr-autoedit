# Alterações

## 3.4.0 Fase 2 — Roteiro Mestre Estratégico e Pacote IA

### Correções de auditoria — commit `8571235`

- torna a concatenação do rascunho leve para qualquer draft explícito, reduzindo
  risco de congelamento em timelines longas;
- normaliza `start_sec` e janelas de cenas antes de validar recortes;
- mantém timebase consistente nas junções, completa áudio quando necessário e
  repete uma junção após falha transitória;
- melhora cache, progresso e tempo de geração dos cards;
- amplia regressões do contrato, draft e Studio HTTP.

### Pacote IA e roteiro estratégico — commit `7b7694c`

- gera automaticamente os seis componentes canônicos de
  `PACOTE_PARA_IA/`;
- transforma o Roteiro Mestre em contrato para estratégia editorial, retenção,
  funil, growth ético, CTA, locução, legenda, cards, balões e decisões técnicas;
- permite classificar e trocar serviço por trecho, com famílias visuais e
  aliases compatíveis com o render existente;
- preserva metadados ainda não executáveis e registra avisos sem descartar o
  restante válido;
- adiciona políticas seguras contra ZIP, lote, resposta, card, anexo e render
  duplicados;
- atualiza a ETAPA 06 e a prévia em modal com timeline clicável;
- proíbe instruções de falsa urgência, escassez, prova social, preço, cliente,
  depoimento, métrica ou resultado inventado.

### Validação

- `python -m pytest tests`: 24 testes aprovados;
- `bash tests/smoke_test.sh`: aprovado com mídias sintéticas;
- inclui testes de pacote, limite inferior a 150 MB, contrato estratégico,
  famílias por serviço, histórico não destrutivo e importação tolerante.

### Limitações

- locução sobre vídeo, keyframes arbitrários, múltiplos balões temporizados,
  legenda independente do overlay e parte das transições avançadas ainda são
  preservados como metadados;
- publicação e medição de retenção/conversão permanecem externas;
- algumas famílias visuais ainda usam composição procedural ou símbolos
  existentes em vez de assets exclusivos.

## 3.4.0 — 2026-09-08

- substitui o briefing v1 por contrato **ROTEIRO MESTRE v2**, com autonomia
  explícita para cortes, reutilização de mídias, cards, carrossel, Stories,
  frames congelados, antes/depois, copy, tipografia e CTA;
- valida exatamente um bloco JSON, IDs e janelas do inventário, fontes
  instaladas, comentários de escopo e números finitos antes de qualquer escrita;
- adiciona revisão contextual no Studio e `Resumo Executivo da IA` com totais
  de duração, cortes, cards, recortes repetidos, frames e alertas por bloco;
- adiciona reset recuperável que mantém ZIP, originais, proxies, manifesto e
  histórico, além de salvar/restaurar alternativas em `_ROTEIROS/`;
- isola cada render em `_RENDERIZACOES/`, verifica assinaturas das mídias e
  publica somente uma cópia operacional na pasta `entrega/`;
- adapta cards ao serviço escolhido (3D, pintura, textura, revestimentos,
  móveis, produção, criação, alvenaria e iluminação) com referências reais ou
  símbolos de categoria claramente tratados como ilustração;
- corrige junções para aplicar transições nos pontos reais entre segmentos e
  amplia a cobertura de testes para contrato, frames, reset e independência.

## 3.3.1 — 2026-09-06

- aceita `start_sec` absoluto ou local em cenas `M####C###` e normaliza para o
  relógio do vídeo-pai, corrigindo o erro “início fora da janela”;
- ajusta automaticamente pequenas diferenças de arredondamento em time-lapse
  sem deslocar o quadro escolhido;
- adiciona checkpoint por mídia, reutilização de proxies/miniaturas e
  persistência do trabalho já concluído após interrupção;
- adiciona timeout por operação, heartbeat, arquivo atual, progresso, botão de
  cancelamento e nova tentativa no painel lateral;
- transmite vídeos por HTTP Range, evitando carregar arquivos 4K inteiros na
  memória do navegador;
- adiciona player integrado em Revisar filme, Galeria e gerenciamento seguro de
  arquivos/projetos com lixeira e restauração;
- integra logo FR remasterizada e fundos 4K de mármore verde-esmeralda, moldura
  dourada acetinada e feixe laranja neon;
- gera automaticamente uma cópia 4K de cada card editável, incluindo o card
  final “ARTE & ENGENHARIA — PROJETOS & REFORMAS”;
- amplia os testes de regressão para janela de cena, Range HTTP, galeria,
  proteção de originais, lixeira e restauração de projetos.

## 3.3.0 — 2026-09-05

- corrige os símbolos de serviço ovais com corte central sem deformação e
  máscara alfa circular testada pixel a pixel;
- adiciona o preset `site_fr_luxo` e o layout `site_editorial`, com proporção
  visual 60% verde-petróleo, 20% laranja e 20% osso/dourado;
- separa **Enviar à IA** como uma etapa própria e reúne todos os arquivos em
  `_ENVIAR_IA/`, identificando claramente o único Markdown editável;
- corrige o download do Roteiro Mestre em projetos novos usando o caminho real
  devolvido pelo backend;
- adiciona time-lapse editorial configurável e editável por cena, com
  velocidade, duração, limite de trechos e controle de áudio;
- promove o vídeo-fonte longo quando uma cena virtual é escolhida para
  time-lapse, preservando conteúdo relevante em vez de acelerar só 3–8 s;
- adiciona importação de Google Takeout com JSON lateral, ExifTool preferencial,
  fallback FFmpeg/data do ZIP, relatório e preservação integral do original;
- amplia a auditoria e os testes sintéticos para círculo, Takeout, time-lapse,
  página da IA e instalação portátil 3.3.0.

## 3.2.4 — 2026-09-04

- corrige “Arquivo não encontrado” ao gerar o Roteiro Mestre em projeto novo;
- prepara automaticamente o projeto quando existe ZIP, mas ainda não há manifesto/plano;
- orienta a anexar o ZIP quando ele estiver ausente, sem deixar a tarefa travada;
- bloqueia “Abrir/baixar” até o Markdown existir e libera o botão ao concluir;
- adiciona teste de regressão do fluxo completo: projeto novo → ZIP → Markdown → download.

## 3.2.3 — 2026-09-02

- adiciona instalador portátil guiado para Parrot OS, Debian e Ubuntu;
- verifica dependências, versão instalada e teste HTTP antes de aprovar a instalação;
- inclui contexto mestre para uma IA auditar, corrigir e automatizar o projeto;
- documenta arquitetura, invariantes, regressões conhecidas e critérios de aceite;
- mantém atualização segura com backup e opção de instalar sem abrir o painel.

## 3.2.2 — 2026-09-02

- inclui atualizador que encerra o painel antigo antes de reinstalar e reabrir o Studio;
- identifica claramente a interface como `3.2.2 · CARDS FIX`;
- abre em outra porta quando uma instância antiga ainda ocupa a porta padrão;
- impede reutilização da página antiga pelo cache do navegador;
- recupera `CARD_STYLE.json` incompatível, preservando a versão anterior no histórico.

## 3.2.1 — 2026-09-02

- Corrige **Gerar prévias/cards** em projetos ainda não preparados.
- Cria `CARD_PREVIEW_PLAN.json` sem substituir a timeline principal.
- Mostra no Studio a causa real da falha, em vez do aviso genérico “Confira o log”.
- Diferencia claramente os estados PRONTO, PROCESSANDO, CONCLUÍDO e ERRO.

## 3.2.0 — 2026-09-02

- card de serviço opcional com nove categorias derivadas dos anexos fornecidos;
- símbolos de serviço compostos organicamente em medalhão, grid e anéis do card FR;
- upload de intro e outro personalizados em imagem ou vídeo, com modos de composição, áudio e uso social;
- Reels de 30/60/90 segundos reconstruídos para cobrir começo, meio distribuído e resultado final;
- editor independente por Reel para mídias, tempos, texto, transição, estabilização e ordem;
- Roteiro Mestre Markdown exportável/importável para Claude, ChatGPT ou qualquer IA capaz de editar JSON;
- validação e backup atômico antes de aplicar o roteiro devolvido pela IA;
- logo persistente alinhada ao centro do balão e mantida quando o balão está desativado;
- fontes de overlays independentes das fontes protegidas dos cards;
- Studio ampliado para sete tarefas e mapa de arquivos atualizado;
- testes integrais para serviço, intro externa, arco social e ida/volta do Roteiro Mestre.

## 3.1.0 — 2026-09-01

- Studio reorganizado em seis tarefas guiadas: Importar, Montar, Estilizar, Áudio e IA, Revisar e Entregar;
- presets de uso Rápido, Profissional FR e Máxima Qualidade, mantendo cada opção editável;
- perfis de saída 480p, HD, Full HD, 2K, 4K e dimensão máxima/original;
- escolha real entre proxies e originais conectada ao motor de render;
- estabilização opcional automática, total ou marcada cena a cena, com três intensidades;
- 29 transições selecionáveis e transição individual na timeline;
- quatro estilos de cards, quatro estilos de balões, paleta editável e animações independentes para intro, fases e encerramento;
- contatos com ícones de Instagram, WhatsApp, Pinterest e site oficial;
- DNA Franco Romeu consolidado no perfil de marca: Forjada Resistência, verdade material, arte e engenharia;
- upload opcional ao Google Drive via `rclone`, sem armazenar senha no projeto, e atalho guiado para Google Fotos;
- galeria de cards, auditoria legível, caminhos copiáveis e controles responsivos para tela grande ou celular;
- qualidade de compressão, áudio, FPS e origem das mídias auditáveis antes da execução.

## 3.0.0 — 2026-08-30

- Studio visual local em uma única página, restrito ao computador e offline por padrão;
- auditoria multisselecionável de entrada, ordem, formatos, redes sociais, filtros, efeitos, áudio e branding;
- central de projetos em `~/FR-AutoEdite/Studio`, sem dependência da pasta Downloads;
- organização segura por fase, `selects/`, deduplicação perceptual e alertas locais de nitidez/estabilidade;
- detecção amostral de cenas e clipes virtuais de 3–8 segundos para vídeos longos;
- modo aleatório/Mashup reproduzível por seed;
- timeline visual arrastável com edição de tempos, textos, fases e transições;
- rascunho 480p/15 fps por proxies e render paralelo configurável;
- xfade contextual, LUT opcional, Ken Burns, speed ramp, ducking, SFX e TTS local opcional;
- Copiloto visual opcional para OpenAI, Anthropic ou Ollama, com cache, validação e fallback local;
- lotes ZIP independentes com validação CRC e limite real inferior a 150 MB;
- divisão de proxies grandes em MP4s independentes, sem partes binárias confusas;
- mapa de caminhos, pastas `_ENTRADA`, `_EDITAR`, `_ENVIAR_CHATGPT` e `_HISTORICO`;
- auditoria mecânica de timeline, fontes, caminhos, ZIPs e limites antes da entrega;
- comandos novos `studio`, `express`, `draft`, `auditar`, `codex-config` e `copilot-curate`;
- compatibilidade mantida com os comandos e questionários da 2.0.

## 2.0.0 — 2026-08-30

- fluxo universal com entrada mínima ZIP + contexto;
- modos automático, cronológico e alfabético;
- duração longa e tempo médio de corte configuráveis;
- logo FR pequeno e persistente na versão institucional;
- cards editáveis por `EDIT_PLAN.json` e `CARD_STYLE.json`;
- maior densidade de detalhes laranja e áreas seguras;
- planos e renders para Reels, Stories, capas e carrossel 4:5;
- estratégia de conteúdo FR compilada a partir das bases fornecidas para Manus;
- contexto integral e planos sociais incluídos nos lotes para ChatGPT;
- render atômico com validação de cada segmento;
- comando `replanejar` sem nova extração/conversão;
- compatibilidade automática com questionários 1.x.

## 1.0.0 — 2026-08-30

- fluxo completo do ZIP do Google Fotos à renderização;
- questionário genérico e cronologia pronta da Cozinha Carreira;
- proxies, miniaturas, contatos visuais, manifesto JSON/CSV e plano editável;
- lotes independentes para ChatGPT com prompt mestre e schema;
- filmes institucional Franco Romeu e limpo;
- cards em Stardos Stencil vazada, Rokkitt e Share Tech Mono;
- retomada por segmento, validação FFprobe e proteção na extração;
- teste integral para vídeos com áudio, sem áudio, fotos e formato 9:16.
## R4 — correção do congelamento no fim do draft

- O rascunho com mais de 24 segmentos não usa mais uma cadeia gigante de `xfade`/`acrossfade`.
- A montagem final do draft usa concatenação leve e mostra mensagens próprias de início e conclusão.
- O FFmpeg é executado com `-nostdin`, evitando espera silenciosa por entrada do terminal.
- A master continua preservando as transições configuradas; a simplificação vale apenas para a prévia draft.
