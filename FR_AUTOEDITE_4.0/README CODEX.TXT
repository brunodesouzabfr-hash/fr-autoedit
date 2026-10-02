

O principal refinamento que fiz no seu conceito é este: a IA não deve “melhorar a versão 4.0”. Ela deve primeiro descobrir qual seria a arquitetura ideal para resolver o problema da Franco Romeu em 2026 e só depois verificar quais funções antigas merecem sobreviver. O resultado deve ser um dossiê técnico/PRD para o Codex, não uma implementação.

Prompt Mestre — Reconcepção FR AutoEdite Next Generation
PROMPT MESTRE — FR AUTOEDITE NEXT GENERATION
Reconcepção completa, arquitetura, IA, automação de edição e plano executável pelo Codex

Você deve atuar simultaneamente como:

Principal Software Architect;
Staff/Principal Engineer de sistemas multimídia;
engenheiro de IA aplicada a vídeo, áudio e visão computacional;
arquiteto de aplicações desktop/web híbridas;
especialista em FFmpeg e pipelines audiovisuais;
especialista em visão computacional;
especialista em processamento de áudio;
especialista em LLMs multimodais;
especialista em UX de softwares profissionais de edição;
editor de vídeo e diretor de montagem;
estrategista de conteúdo para redes sociais;
engenheiro de automação;
engenheiro DevOps;
especialista em performance CPU/GPU;
especialista em sistemas locais/offline-first;
arquiteto de dados;
product designer;
product manager técnico;
especialista em branding e conteúdo da Franco Romeu.
1. MISSÃO

Sua missão NÃO é modificar a aplicação atual.

Sua missão NÃO é escrever imediatamente uma nova aplicação.

Sua missão NÃO é simplesmente sugerir algumas funcionalidades adicionais.

Sua missão é reconceber intelectualmente a FR AutoEdite do zero e produzir a especificação técnica, funcional, arquitetural e estratégica mais completa possível para que, posteriormente, o Codex implemente essa nova geração da aplicação.

Quero que você responda à seguinte questão:

Se hoje tivéssemos de criar, do zero, a melhor aplicação possível para automatizar a transformação de grandes volumes de vídeos, fotos, áudio e informações de projetos da Franco Romeu em conteúdos profissionais para redes sociais, como ela deveria funcionar?

Considere a FR AutoEdite 4.0 existente somente como uma fonte de requisitos e aprendizados.

REGRA FUNDAMENTAL

Não preserve a arquitetura atual por compatibilidade emocional ou histórica.

A versão existente deve ser tratada como:

fonte de requisitos → não como fonte de arquitetura

Você pode:

substituir tecnologias;
abandonar módulos;
dividir módulos;
fundir módulos;
reconstruir interfaces;
alterar linguagens;
alterar frameworks;
transformar scripts em serviços;
substituir o sistema de timeline;
substituir o sistema de render;
substituir o modelo de projeto;
adicionar banco de dados;
adicionar indexação vetorial;
criar arquitetura de plugins;
usar IA local;
usar IA externa;
criar modos híbridos;
introduzir workers;
introduzir filas;
criar um novo formato interno de projeto.

Desde que consiga justificar tecnicamente a decisão.

2. NÃO EXECUTE A IMPLEMENTAÇÃO

Nesta resposta:

NÃO modifique repositórios;
NÃO gere commits;
NÃO altere arquivos;
NÃO faça deploy;
NÃO tente criar a aplicação completa;
NÃO trate a primeira solução imaginada como definitiva.

Você deverá entregar uma análise de engenharia e especificação mestre para o Codex executar posteriormente.

Código é permitido apenas quando necessário para demonstrar:

arquitetura;
interfaces;
contratos;
estruturas;
schemas;
pseudocódigo;
modelos de dados;
exemplos de API.

O objetivo desta etapa é PENSAR ANTES DE PROGRAMAR.

3. PRINCÍPIO DE PROJETO

A aplicação não deve ser simplesmente um:

“script que junta vídeos usando FFmpeg”.

Ela deve ser concebida como um:

MEDIA INTELLIGENCE + EDITING AUTOMATION SYSTEM

ou seja, um sistema composto por diferentes motores especializados.

Mentalmente, considere algo semelhante a:

MÍDIAS
   ↓
INGESTÃO
   ↓
ANÁLISE
   ↓
MEDIA INTELLIGENCE INDEX
   ↓
ENTENDIMENTO DO PROJETO
   ↓
SELEÇÃO DE MOMENTOS
   ↓
PLANEJAMENTO NARRATIVO
   ↓
PLANO DE EDIÇÃO
   ↓
TIMELINE
   ↓
GRAPHICS / CARDS / TEXTOS
   ↓
ÁUDIO
   ↓
RENDER
   ↓
VERSÕES SOCIAIS
   ↓
CONTROLE DE QUALIDADE
   ↓
EXPORTAÇÃO

Mas não aceite essa divisão automaticamente.

Questione-a e proponha arquitetura melhor se existir.

4. CONTEXTO PRINCIPAL DE USO

A aplicação é destinada principalmente à produção de conteúdo audiovisual da Franco Romeu.

Utilize todo o contexto disponível sobre:

Franco Romeu;
posicionamento da marca;
serviços;
obras;
reformas;
arquitetura;
interiores;
projetos 3D;
mobiliário;
elétrica;
hidráulica;
revestimentos;
iluminação;
pintura;
construção;
produção;
manutenção;
processos técnicos;
demonstrações;
antes/depois;
bastidores;
materiais;
soluções técnicas;
redes sociais;
identidade visual;
branding;
linguagem;
conteúdo educacional;
conteúdo comercial;
conteúdo institucional.

Entretanto:

não transforme o software em algo incapaz de editar outros assuntos.

A Franco Romeu deve ser implementada como:

CORE UNIVERSAL DE EDIÇÃO
          +
FR DOMAIN PACK
          +
FR BRAND PACK
          +
FR CONTENT STRATEGY

Isso permitirá futuramente adicionar outros:

Brand Packs;
Domain Packs;
Style Packs;
Content Packs.
5. PRIMEIRA FASE — PROBLEMA ANTES DA SOLUÇÃO

Antes de propor arquitetura, faça uma decomposição completa do problema.

Identifique:

Entrada

Que tipos de dados o sistema poderá receber?

Exemplos:

vídeos;
fotos;
imagens renderizadas;
áudio;
voice-over;
música;
documentos;
roteiro;
briefing;
manifesto de mídia;
informações do projeto;
identidade visual;
legendas;
metadados;
comentários humanos;
marcações manuais.
Processamento

O que realmente precisa ser descoberto?

Decisão

Quais decisões hoje exigem um editor humano?

Automação

Quais delas podem ser:

determinísticas;
heurísticas;
estatísticas;
feitas por visão computacional;
feitas por modelos multimodais;
feitas por LLM;
feitas manualmente;
feitas em sistema híbrido.
Saída

Quais produtos audiovisuais devem ser possíveis?

6. TRÊS MODOS FUNDAMENTAIS

A aplicação deverá considerar seriamente três paradigmas.

MODO 1 — MANUAL ASSISTIDO

O usuário controla tudo, mas o software elimina tarefas repetitivas.

Exemplos:

detectar cenas;
eliminar silêncio;
marcar problemas;
gerar proxies;
sugerir crop;
encontrar takes semelhantes;
gerar legenda;
adaptar formato;
gerar cards.
MODO 2 — IA ASSISTIDA

A IA sugere decisões.

Exemplo:

Este trecho parece mostrar instalação elétrica.

Confiança: 91%

Ação detectada:
instalação de luminária

Sugestão:
usar entre 00:43 e 00:51

Motivo:
ação completa + enquadramento estável + boa iluminação

O humano pode:

aceitar;
editar;
rejeitar.
MODO 3 — AUTOPILOT

O sistema recebe:

/pasta-do-projeto

e devolve automaticamente:

vídeo principal;
Reel;
Shorts;
Stories;
teaser;
antes/depois;
versões sem texto;
versões com cards;
versões técnicas;
versões comerciais.

Analise profundamente como esses três modos poderiam compartilhar o mesmo core.

7. PRINCÍPIO CRÍTICO — EDIÇÃO NÃO DESTRUTIVA

Investigue uma arquitetura em que nenhuma decisão destrua o material original.

Considere um sistema baseado em:

SOURCE MEDIA
+
MEDIA INDEX
+
EDIT DECISIONS
+
TIMELINE
+
RENDER GRAPH

A timeline deve representar decisões, não arquivos renderizados intermediários sempre que possível.

Analise conceitos como:

EDL;
OTIO/OpenTimelineIO;
timeline intermediária própria;
composition graph;
render graph;
DAG;
nodes;
clips;
tracks;
overlays;
effects;
keyframes.

Determine a melhor abordagem.

8. MEDIA INTELLIGENCE ENGINE

Projete conceitualmente um motor capaz de analisar cada mídia uma única vez e reutilizar posteriormente os resultados.

Exemplo conceitual:

VIDEO
 ├── technical metadata
 ├── scenes
 ├── shots
 ├── speech
 ├── silence
 ├── motion
 ├── objects
 ├── people
 ├── tools
 ├── materials
 ├── actions
 ├── quality
 ├── embeddings
 ├── semantic description
 └── recommended segments

Pesquise e determine como detectar:

cenas;
mudanças de câmera;
cortes;
silêncio;
fala;
música;
ruído;
black frames;
frames congelados;
exposição ruim;
imagens desfocadas;
câmera excessivamente instável;
takes duplicados;
vídeos praticamente iguais;
regiões sem informação;
momentos mortos;
períodos sem ação;
enquadramentos ruins;
melhores takes;
início e fim de uma ação;
mãos;
pessoas;
ferramentas;
materiais;
ambientes;
objetos;
movimento;
transformação física;
antes/depois;
execução de serviço.
9. O CONCEITO DE “ÁREA MORTA”

Não trate “área morta” apenas como silêncio.

Defina uma taxonomia.

Exemplos:

Dead Audio

silêncio ou áudio inútil.

Dead Motion

imagem praticamente parada sem função narrativa.

Dead Action

pessoa se preparando para realizar uma ação, mas nada relevante acontece.

Dead Camera

reposicionamento de câmera.

Dead Narrative

trecho tecnicamente aceitável que não acrescenta informação.

Dead Duplicate

informação já exibida anteriormente.

Dead Transition

tempo excessivo entre dois acontecimentos.

Dead Visual

imagem desfocada, obstruída ou sem informação útil.

Crie métricas para detectar cada categoria.

10. SISTEMA DE SCORING

Não quero somente “IA escolhe o melhor trecho”.

Quero que você determine se é adequado criar um modelo explicável.

Exemplo:

segment_score =
    visual_quality
  + action_score
  + semantic_value
  + novelty
  + narrative_relevance
  + technical_relevance
  + branding_value
  - duplicate_penalty
  - blur_penalty
  - dead_time_penalty

Cada trecho poderia possuir algo semelhante a:

{
  "segment": "00:42.100-00:48.700",
  "visual_quality": 0.93,
  "action_score": 0.88,
  "semantic_value": 0.91,
  "novelty": 0.84,
  "duplicate_penalty": 0.12,
  "confidence": 0.89
}

Analise se esse conceito é adequado ou proponha sistema superior.

11. ENTENDIMENTO SEMÂNTICO

A aplicação deve ser capaz de entender, quando possível, não apenas:

“homem segurando uma ferramenta”

mas:

“profissional realizando acabamento de massa em parede antes da pintura”

ou:

“instalação do sistema hidráulico da cuba”

ou:

“montagem do mobiliário planejado”

ou:

“teste do sistema de iluminação LED”.

Projete a arquitetura necessária.

Considere combinação de:

visão computacional;
modelos de detecção;
modelos multimodais;
embeddings;
LLM;
ontologia da Franco Romeu;
contexto fornecido pelo projeto.
12. MEDIA MEMORY

Analise a criação de uma memória persistente das mídias.

Por exemplo:

Media Library
   ↓
Semantic Index
   ↓
Vector Search

Permitindo buscas como:

“mostre todos os vídeos onde aparece instalação da ilha da cozinha”

ou:

“encontre as melhores imagens da bancada antes da instalação”

ou:

“localize cenas de iluminação LED”

ou:

“quais vídeos mostram a transformação mais evidente?”

Analise:

banco relacional;
documentos JSON;
SQLite;
DuckDB;
PostgreSQL;
vector database;
FAISS;
Qdrant;
LanceDB;
alternativas atuais.

Escolha tecnicamente.

13. ENTENDIMENTO DE PROJETO

A aplicação deve conseguir separar:

MÍDIA

de:

SIGNIFICADO DA MÍDIA DENTRO DO PROJETO

Exemplo:

arquivo:
VID_4732.mp4

fase:
instalação do mobiliário

ação:
montagem de portas

ambiente:
cozinha

prioridade narrativa:
alta

Projete um Project Knowledge Graph, Project Manifest ou alternativa melhor.

14. EDITOR NARRATIVO

Investigue a possibilidade de um módulo acima da timeline denominado conceitualmente:

STORY ENGINE

Ele recebe:

objetivo;
plataforma;
duração;
público;
mídia disponível;
etapas do projeto;
estratégia;
identidade visual.

E produz algo semelhante a:

HOOK
↓
CONTEXTO
↓
PROBLEMA
↓
PROCESSO
↓
DETALHES TÉCNICOS
↓
TRANSFORMAÇÃO
↓
RESULTADO
↓
CTA

Mas não force essa fórmula em todos os vídeos.

O Story Engine deve escolher a estrutura adequada.

Exemplos:

transformação;
tutorial;
processo;
before/after;
showcase;
institucional;
técnico;
educativo;
comercial;
storytelling;
bastidores.
15. CARDS, BALÕES E GRAPHICS ENGINE

Este deve ser um sistema profissional, não imagens estáticas jogadas sobre o vídeo.

Projete um:

MOTION GRAPHICS / INFORMATION OVERLAY ENGINE

Cards e balões devem poder ser:

parametrizados;
editáveis;
animados;
vinculados a dados;
responsivos;
reutilizáveis;
adaptáveis por proporção.

Precisam considerar:

9:16;
16:9;
1:1;
4:5;
safe areas;
legendas;
rostos;
objeto principal;
composição;
movimento;
colisão visual.

Analise:

auto placement;
anchor tracking;
face avoidance;
subject avoidance;
subtitle avoidance;
collision detection;
responsive layout;
animation presets;
templates;
design tokens;
Brand Packs.
16. TEXTO AUTOMÁTICO SEM ALUCINAÇÃO

Se a IA gerar um card como:

“Tubulação PEX instalada”

ela deve possuir evidência suficiente de que isso realmente ocorreu.

Projete mecanismos de:

grounding;
confidence;
provenance;
revisão;
bloqueio de afirmações técnicas sem evidência.

Exemplo:

Card:
"Aplicação de impermeabilização"

Source:
clip_018

Evidence:
frames 320-518

Confidence:
0.94

Isso é particularmente importante para informações técnicas.

17. LEGENDAS

Projete um sistema profissional para:

speech-to-text;
word timestamps;
diarização quando necessária;
correção contextual;
pontuação;
remoção de vícios;
destaque de palavras;
karaoke;
estilos da marca;
quebra semântica de linhas;
limite de caracteres;
safe area;
geração multilíngue.
18. ÁUDIO

Projete um pipeline para:

normalização;
loudness;
remoção de ruído;
speech enhancement;
ducking;
trilha;
efeitos;
detecção de beat;
edição sincronizada à música;
crossfades;
sound design.

Determine o que deve ser:

automático;
configurável;
opcional.
19. REFRAMING INTELIGENTE

Um vídeo horizontal poderá gerar automaticamente:

16:9
9:16
4:5
1:1

Mas o sistema deve tentar preservar:

pessoa;
ferramenta;
objeto;
ação;
bancada;
detalhe técnico;
elemento principal.

Investigue:

tracking;
saliency;
object detection;
face detection;
dynamic crop;
keyframe crop.
20. SISTEMA ANTES/DEPOIS

Crie um subsistema específico para transformação visual.

Ele deverá ser capaz de sugerir pares de imagens ou vídeos com:

ambiente semelhante;
ângulo semelhante;
enquadramento compatível;
elementos reconhecíveis;
maior diferença visual;
maior impacto.

Considere alinhamento aproximado de câmera e composição.

21. FOTOS

A aplicação não pode tratar foto como vídeo congelado.

Analise mecanismos próprios:

Ken Burns;
pan;
zoom;
depth/parallax;
smart crop;
saliency;
transições;
agrupamento semântico;
foto antes/depois.
22. TIMELINE PROFISSIONAL

Determine qual nível de edição manual deve existir.

Analise recursos como:

múltiplas tracks;
trim;
ripple edit;
slip;
split;
magnet timeline;
snapping;
markers;
layers;
overlays;
audio tracks;
keyframes;
undo/redo;
history;
preview;
proxy/original switching.

Não copie Premiere ou DaVinci indiscriminadamente.

Projete apenas o necessário para a missão da aplicação.

23. EDIÇÃO POR LINGUAGEM NATURAL

Investigue profundamente este paradigma.

Exemplos:

“remova os trechos parados”

“deixe apenas a montagem da ilha”

“crie um Reel de 45 segundos”

“mostre primeiro o antes e depois explique o processo”

“reduza essa parte para cinco segundos”

“troque este card por informação sobre a iluminação”

A IA deverá transformar linguagem natural em operações estruturadas.

Exemplo conceitual:

USER
↓
LLM
↓
EDIT COMMAND
↓
VALIDATOR
↓
TIMELINE OPERATION

Nunca permita que o LLM altere arquivos diretamente sem uma camada estruturada de validação.

24. AGENTIC EDITING

Investigue se faz sentido criar agentes especializados.

Exemplo:

Media Analyst
Story Editor
Technical Reviewer
Social Strategist
Graphics Director
Audio Engineer
Quality Reviewer

Mas evite “multiagentes” apenas por moda.

Determine se:

agentes separados;
serviços;
pipelines determinísticos;
LLM único com ferramentas;

seria a melhor solução.

25. ARQUITETURA DE IA

Determine quais tarefas realmente precisam de IA.

Não utilize um LLM onde:

if duration > X

resolve melhor.

Classifique todas as operações entre:

DETERMINISTIC
HEURISTIC
CLASSICAL CV
ML MODEL
MULTIMODAL MODEL
LLM
HUMAN

Essa tabela é obrigatória.

26. IA LOCAL, CLOUD E HÍBRIDA

Projete três capacidades.

Local

Para privacidade e baixo custo.

Cloud

Para modelos extremamente poderosos quando necessário.

Hybrid

Local executa análise inicial e cloud apenas tarefas que justificam custo.

O software não deve deixar de funcionar completamente quando uma API externa estiver indisponível.

27. HARDWARE ADAPTATIVO

O sistema deverá detectar hardware.

Exemplos:

CPU only
NVIDIA CUDA
AMD
Intel
Apple Silicon

E alterar automaticamente:

modelo utilizado;
resolução de proxy;
batch size;
encoder;
análise;
render;
precisão.
28. PESQUISE O ECOSSISTEMA ATUAL

Antes de recomendar tecnologias, faça pesquisa atual.

Não se limite ao seu conhecimento interno.

Quando possuir acesso à web/GitHub/documentação:

pesquise.

Investigue projetos e categorias relacionadas a:

FFmpeg;
libav;
PyAV;
GStreamer;
MLT;
OpenTimelineIO;
Remotion;
OpenCV;
PySceneDetect;
Whisper;
faster-whisper;
whisper.cpp;
ONNX Runtime;
modelos multimodais;
object detection;
tracking;
segmentation;
embeddings;
vector search;
audio analysis;
speech enhancement;
smart cropping;
video understanding;
captioning;
subtitle rendering;
motion graphics.

Esses nomes são apenas sementes.

Não os adote automaticamente.

Encontre também alternativas melhores ou mais atuais.

29. PARA CADA TECNOLOGIA/REPOSITÓRIO

Avalie:

Critério	Avaliação
finalidade	

maturidade	

atividade do projeto	

licença	

qualidade da documentação	

performance	

GPU	

CPU	

cross-platform	

Python	

JS/TS	

integração	

complexidade	

riscos	

manutenção futura	

razão para usar	

razão para não usar	


Não faça uma lista gigantesca de bibliotecas sem decisão.

Escolha uma stack coerente.

30. STACK DA APLICAÇÃO

Não assuma que a stack atual é correta.

Compare seriamente abordagens como:

Desktop native
Desktop web-tech
Browser
Local web app
Hybrid desktop
Client/server local

E tecnologias possíveis.

A decisão deve considerar:

Linux;
Windows;
eventualmente macOS;
acesso ao filesystem;
FFmpeg;
GPU;
processamento em background;
preview;
timeline;
estabilidade;
instalador;
atualização;
uso offline.
31. ARQUITETURA EM CAMADAS

Avalie uma arquitetura semelhante a:

UI
↓
APPLICATION CORE
↓
PROJECT ENGINE
↓
STORY ENGINE
↓
EDIT ENGINE
↓
MEDIA INTELLIGENCE
↓
AI SERVICES
↓
RENDER ENGINE
↓
SYSTEM SERVICES

Ou proponha solução superior.

Não crie um monólito impossível de manter.

32. JOB SYSTEM

Análises pesadas não devem congelar a aplicação.

Projete:

task queue;
workers;
prioridades;
cancelamento;
pause/resume;
retry;
progress;
cache;
recovery.

Exemplo:

GenerateProxy
Transcribe
DetectScenes
AnalyzeFrames
CreateEmbeddings
RenderPreview
RenderFinal
33. CACHE

Uma mídia analisada não deve ser analisada novamente sem necessidade.

Defina uma estratégia baseada em:

hash;
fingerprint;
parâmetros;
versão do modelo;
versão do pipeline.
34. OBSERVABILIDADE

O software deve explicar:

o que está fazendo
por que está fazendo
quanto concluiu
qual etapa falhou
como recuperar

Projete:

logs;
jobs;
events;
error reporting;
debug mode;
audit trail.
35. PROJECT FORMAT

Projete um formato de projeto robusto.

Algo conceitualmente parecido com:

project.frproj

contendo ou referenciando:

metadata
sources
analysis
timeline
graphics
audio
strategy
exports
history

Determine se deverá ser:

pasta;
JSON;
SQLite;
archive;
combinação.
36. REPRODUTIBILIDADE

Dado:

mesmo projeto
+
mesmas mídias
+
mesmas configurações
+
mesma seed

o sistema deverá, quando desejado, conseguir reproduzir a mesma edição.

IA não deve tornar tudo aleatoriamente irreproduzível.

37. VERSÕES E EXPERIMENTAÇÃO

Projete:

Version A
Version B
Version C

por exemplo:

técnico;
emocional;
comercial.

O sistema deve reutilizar análises, não começar tudo novamente.

38. SOCIAL CONTENT ENGINE

Não trate todas as plataformas igualmente.

Projete presets estratégicos para:

Instagram Reels;
Instagram Feed;
Stories;
YouTube Shorts;
YouTube;
TikTok;
Facebook.

Considere:

duração;
proporção;
ritmo;
texto;
hook;
CTA;
safe zones.

Não invente “algoritmos secretos”.

Baseie decisões em princípios verificáveis de comunicação e edição.

39. MULTI-OUTPUT

Um projeto longo deverá poder produzir automaticamente:

FILME PRINCIPAL

├── Reel 15s
├── Reel 30s
├── Reel 60s
├── Reel 90s
├── Shorts
├── Stories
├── Teaser
├── Before/After
├── Technical Cut
├── Clean Cut
└── Thumbnail Candidates

Sem repetir toda a análise das mídias.

40. BRAND SYSTEM

Separe:

CONTENT

de:

BRAND PRESENTATION

Um Brand Pack deverá poder controlar:

logo;
tipografia;
cores;
grids;
cards;
motion;
transições;
captions;
CTA;
lower thirds;
intro;
outro.
41. PLUGIN SYSTEM

Avalie se a aplicação deve possuir arquitetura de plugins para:

IA;
modelos;
exportadores;
efeitos;
cards;
Brand Packs;
Domain Packs;
análise;
serviços externos.

Proponha contratos claros.

42. SEGURANÇA

Analise:

execução de FFmpeg;
paths;
shell injection;
APIs;
tokens;
downloads;
modelos;
plugins;
arquivos malformados;
permissões.
43. RECUPERAÇÃO DE FALHAS

Se o programa fechar durante:

42% da análise

não quero reiniciar tudo.

Projete checkpoints e retomada.

44. PREVIEW VS FINAL

Separe claramente:

FAST PREVIEW

de:

MASTER RENDER

O usuário não deve esperar um render 4K para avaliar um card.

45. TESTES

Projete uma estratégia incluindo:

unit tests;
integration tests;
golden tests;
visual regression;
render tests;
fixture projects;
corrupted media tests;
benchmark tests;
deterministic pipeline tests.
46. GOLDEN PROJECTS

Proponha manter projetos de referência como:

golden/kitchen-renovation
golden/before-after
golden/manual-edit
golden/ai-autopilot

Toda atualização relevante será comparada contra esses projetos.

47. BENCHMARKS

Defina benchmarks mensuráveis.

Exemplos:

tempo de ingestão;
geração de proxy;
velocidade de análise;
RAM;
VRAM;
render fps;
qualidade de transcrição;
precisão da detecção;
cache hit;
tempo de abertura.
48. UX

A aplicação deve ser poderosa sem virar cockpit incompreensível.

Pense em níveis.

SIMPLE
Importar
→
Escolher objetivo
→
Gerar
ASSISTED

Permite revisar sugestões.

PRO

Expõe:

timeline;
parâmetros;
modelos;
análise;
debugging.
49. COMMAND CENTER

Avalie uma interface em que o usuário veja:

PROJECT
MEDIA
STORY
TIMELINE
GRAPHICS
AUDIO
EXPORT
AI

Não use isso obrigatoriamente.

Projete a melhor IA de navegação.

50. NÃO CONFUNDA AUTOMAÇÃO COM FALTA DE CONTROLE

Cada decisão automática importante deveria, quando aplicável, oferecer:

resultado
confiança
motivo
fonte
editar
aceitar
rejeitar
51. COMPARE COM A FR AUTOEDITE 4.0

Somente depois de conceber a solução ideal, analise a versão existente.

Crie uma matriz:

Área	4.0	Nova arquitetura	Preservar	Recriar	Remover

Não permita que a estrutura da versão 4.0 contamine prematuramente o novo desenho.

52. MIGRAÇÃO

Depois disso, responda:

vale mais evoluir o código existente ou criar um novo core e migrar gradualmente?

Não escolha por intuição.

Considere:

dívida técnica;
cobertura de testes;
acoplamento;
capacidade de reaproveitamento;
custo;
risco;
migração dos projetos.
53. NÃO QUERO UM “BIG BANG REWRITE” IRRESPONSÁVEL

Mesmo se recomendar reconstrução, elabore uma migração incremental.

Exemplo conceitual:

NOVO MEDIA CORE
↓
NOVO PROJECT MODEL
↓
NOVO ANALYZER
↓
NOVO STORY ENGINE
↓
NOVO TIMELINE ENGINE
↓
NOVO GRAPHICS ENGINE
↓
NOVO UI

Podendo coexistir temporariamente com partes antigas.

54. ARQUITETURA DE REFERÊNCIA

No final, entregue um diagrama completo.

Exemplo apenas conceitual:

┌───────────────────────────────┐
│              UI               │
├───────────────────────────────┤
│        Application Core       │
├──────────────┬────────────────┤
│ Story Engine │ Timeline Engine│
├──────────────┴────────────────┤
│     Media Intelligence        │
├───────────┬───────────────────┤
│ AI Layer  │ Media Engine      │
├───────────┴───────────────────┤
│          Job System           │
├───────────────────────────────┤
│ Storage / Cache / Database    │
├───────────────────────────────┤
│ FFmpeg / GPU / OS / Filesystem│
└───────────────────────────────┘

Mas crie o seu próprio desenho depois da análise.

55. ENTREGÁVEIS OBRIGATÓRIOS

Sua resposta deverá ser suficientemente detalhada para posteriormente ser convertida nos seguintes documentos:

00_EXECUTIVE_SUMMARY.md
01_PRODUCT_VISION.md
02_REQUIREMENTS.md
03_ARCHITECTURE.md
04_MEDIA_PIPELINE.md
05_AI_ARCHITECTURE.md
06_STORY_ENGINE.md
07_TIMELINE_ENGINE.md
08_GRAPHICS_ENGINE.md
09_AUDIO_ENGINE.md
10_SOCIAL_ENGINE.md
11_DATA_MODEL.md
12_PLUGIN_SYSTEM.md
13_UX_ARCHITECTURE.md
14_TECHNOLOGY_RESEARCH.md
15_SECURITY.md
16_TEST_STRATEGY.md
17_BENCHMARKS.md
18_MIGRATION_PLAN.md
19_CODEX_EXECUTION_PLAN.md
20_ADR_INDEX.md
56. CODEX EXECUTION PLAN

Esta é uma das partes mais importantes.

Depois da arquitetura, transforme o projeto em unidades de implementação que o Codex possa executar.

Cada etapa deverá conter:

OBJETIVO

DEPENDÊNCIAS

ARQUIVOS/MÓDULOS PROVÁVEIS

IMPLEMENTAÇÃO

TESTES

CRITÉRIOS DE ACEITE

RISCO

ROLLBACK
57. ORGANIZE EM EPICS

Exemplo:

EPIC 01 — Foundation
EPIC 02 — Media Ingestion
EPIC 03 — Project Database
EPIC 04 — Proxy Engine
EPIC 05 — Media Intelligence
EPIC 06 — Speech Intelligence
EPIC 07 — Visual Intelligence
EPIC 08 — Timeline Core
EPIC 09 — Story Engine
EPIC 10 — Graphics Engine
EPIC 11 — Audio Engine
EPIC 12 — AI Assistant
EPIC 13 — Social Outputs
EPIC 14 — Render Engine
EPIC 15 — Desktop UI
EPIC 16 — Plugin Architecture
EPIC 17 — Tests
EPIC 18 — Migration

Mas altere esta lista se encontrar estrutura melhor.

58. QUEBRE EM PRs PEQUENOS

Não diga:

“Codex: recrie toda aplicação”.

Produza algo como:

PR-001 Project skeleton
PR-002 Media database
PR-003 FFprobe ingestion
PR-004 Proxy jobs
PR-005 Scene detection
PR-006 Audio transcription
...

Cada PR deve ser testável e reversível.

59. DEPENDENCY GRAPH

Informe quais implementações dependem de quais.

Exemplo:

PROJECT CORE
 ├── MEDIA INGEST
 │    ├── PROXY
 │    ├── ANALYSIS
 │    └── TRANSCRIPTION
 │
 ├── TIMELINE
 │    ├── STORY ENGINE
 │    └── GRAPHICS
 │
 └── RENDER
60. MVP ≠ PRODUTO FINAL

Divida claramente:

FOUNDATION

infraestrutura fundamental.

MVP

primeiro fluxo realmente utilizável.

V1

produto estável.

V2 INTELLIGENCE

IA avançada.

PRO

recursos profissionais.

Evite tentar construir tudo no primeiro commit.

61. PRIORIZAÇÃO

Para cada funcionalidade relevante classifique:

Impacto
Complexidade
Risco
Dependências
Prioridade

Não use somente MoSCoW de maneira superficial.

62. CRITÉRIOS PARA A ARQUITETURA FINAL

A solução recomendada deverá maximizar:

qualidade da edição;
controle do usuário;
automação;
inteligência semântica;
velocidade;
estabilidade;
capacidade offline;
baixo retrabalho;
extensibilidade;
manutenibilidade;
observabilidade;
reprodutibilidade;
evolução futura.
63. ANTI-PADRÕES

Evite explicitamente:

script monolítico;
milhares de linhas em um arquivo;
chamadas FFmpeg espalhadas pela UI;
LLM alterando timeline diretamente;
regras de negócio dentro de componentes visuais;
JSON gigantesco usado como banco;
renderização bloqueando UI;
reanálise constante de mídia;
dependência obrigatória de internet;
templates hardcoded;
caminhos absolutos;
efeitos inseparáveis do render;
IA sem confidence;
IA sem provenance;
respostas genéricas;
tecnologia escolhida apenas por popularidade.
64. QUESTIONE MINHAS PREMISSAS

Você possui autorização explícita para dizer:

essa abordagem não é ideal.

Se encontrar alternativa melhor.

Quero engenharia, não concordância.

65. NÃO PRODUZA UMA LISTA DE DESEJOS

Cada funcionalidade proposta deve responder:

Qual problema resolve?

Por que ela deve existir?

Como funcionaria?

De que depende?

Quanto custa em complexidade?

Pertence ao core?

É plugin?

É IA?

É determinística?

É MVP?

É futura?
66. PESQUISA DE MERCADO TÉCNICA

Analise conceitos utilizados em categorias de software como:

NLEs profissionais;
editores automáticos;
plataformas de clipping;
sistemas de transcript editing;
ferramentas de social video;
motion graphics;
media asset management;
DAM;
AI video editing.

Não copie produtos.

Extraia conceitos arquiteturais úteis.

67. DIFERENCIAL DA FR AUTOEDITE

Procure descobrir qual poderia ser o verdadeiro diferencial.

Não quero apenas:

“editor com IA”.

Investigue conceitos como:

PROJECT-AWARE EDITING
DOMAIN-AWARE EDITING
SEMANTIC MEDIA MEMORY
EXPLAINABLE AUTOEDIT
MULTI-OUTPUT STORY ENGINE
BRAND-AWARE GRAPHICS

E diga quais deles possuem maior valor real para este produto.

68. RESULTADO ESPERADO

Ao terminar sua análise, eu devo conseguir entregar sua resposta para outro engenheiro ou para o Codex e ele entender:

o que construir;
por que construir;
como estruturar;
tecnologias indicadas;
tecnologias rejeitadas;
quais módulos criar;
como eles conversam;
quais dados persistir;
como a IA funciona;
como a timeline funciona;
como a renderização funciona;
como testar;
como migrar;
em qual ordem implementar.
69. FORMATO OBRIGATÓRIO DA RESPOSTA

Entregue na seguinte sequência:

PARTE A — Diagnóstico do problema
PARTE B — Visão da nova FR AutoEdite
PARTE C — Princípios arquiteturais
PARTE D — Arquitetura geral
PARTE E — Media Intelligence Engine
PARTE F — Story Engine
PARTE G — Timeline/Edit Engine
PARTE H — AI Architecture
PARTE I — Graphics/Card/Bubble Engine
PARTE J — Audio Engine
PARTE K — Social Content Engine
PARTE L — Data Architecture
PARTE M — UX
PARTE N — Tecnologias e repositórios pesquisados
PARTE O — Stack recomendada
PARTE P — Alternativas rejeitadas e justificativa
PARTE Q — Comparação com a FR AutoEdite 4.0
PARTE R — Estratégia de migração
PARTE S — Roadmap
PARTE T — Epics
PARTE U — Sequência de PRs para Codex
PARTE V — Testes e benchmarks
PARTE W — Riscos técnicos
PARTE X — Arquitetura final recomendada
PARTE Y — Estrutura de diretórios sugerida
PARTE Z — Prompt operacional final para o Codex
70. PROMPT DO CODEX

A última seção é obrigatória.

Depois de terminar toda a análise, transforme suas conclusões em um segundo prompt chamado:

PROMPT OPERACIONAL — CODEX — FR AUTOEDITE NEXT

Esse segundo prompt deverá permitir que o Codex comece a implementação de forma segura e incremental.

Ele deverá conter:

arquitetura escolhida;
stack;
regras;
estrutura;
primeira milestone;
arquivos iniciais;
testes;
critérios de aceite;
sequência de execução;
proibições;
checkpoints.

Não mande o Codex reconstruir tudo de uma vez.

Faça o Codex trabalhar fase a fase.

71. PROFUNDIDADE DO RACIOCÍNIO

Antes de responder:

decomponha o problema;
identifique restrições;
pesquise tecnologias atuais;
compare alternativas;
encontre conflitos arquiteturais;
analise custo e complexidade;
estabeleça requisitos;
escolha uma arquitetura;
tente encontrar falhas na própria arquitetura;
refine;
só então produza a recomendação final.

Não mostre raciocínio interno privado.

Mostre:

conclusões;
trade-offs;
evidências;
comparações;
justificativas técnicas.
72. REGRA FINAL

Não pergunte:

“qual abordagem você prefere?”

Sua função aqui é fazer a investigação técnica e chegar a uma arquitetura principal coerente.

Você poderá mostrar alternativas quando houver trade-offs reais, mas deverá terminar com uma recomendação arquitetural concreta e internamente consistente.

O resultado deve ser suficientemente detalhado para servir de blueprint da próxima geração da FR AutoEdite e posteriormente ser executado incrementalmente pelo Codex.

Esse prompt muda a tarefa de “me dê ideias para melhorar meu editor” para “projete um sistema profissional de inteligência e automação audiovisual e depois converta a arquitetura em trabalho executável pelo Codex”.

O ponto mais importante é a separação entre Media Intelligence → Story Engine → Timeline/Edit Engine → Render Engine. Isso impede que a próxima versão volte a se tornar apenas uma coleção crescente de scripts FFmpeg, prompts e condições acopladas. A IA passa a entender e recomendar, enquanto um núcleo determinístico continua responsável por executar as decisões.

Texto colado.txt
Documento
irei te entregar uma resposta de outra ia e vc ira decidir criteriosamente se é eficaz utilizar junto  a resposta gerada de agora, implemente uma parte dois retirando as redundancias se achar aplicavel, vc esta sob total autonomia de decisoes e modificações te dou o controle absoluto de escolha, analise a sua resposta e a que irei anexar  e conjunte para ser como uma aprte dois se achar necessario

Decisão

Sim, vale usar a segunda resposta junto com o prompt anterior — mas como uma Parte II, não como fusão literal. O primeiro prompt é mais forte na arquitetura sistêmica: Media Intelligence, Story Engine, Timeline, Graphics, Audio, dados, jobs, plugins, migração e plano incremental para o Codex. O texto anexado acrescenta uma camada que faltava: realidade operacional da Franco Romeu, ingestão de Takeout/ZIP, procedência, distinção entre render 3D e obra executada, regras de evidência, retenção compatível com quiet luxury, privacidade local e revisão adversarial da própria arquitetura.

Também preservei a excelente ideia de que a IA não pode inventar janelas temporais ou mídias, devendo operar apenas sobre IDs existentes no manifesto, com edição reversível, snapshots e possibilidade de reprocessamento. Isso deve virar uma propriedade estrutural do sistema, não apenas uma recomendação.

Por outro lado, não manteria literalmente algumas imposições do texto anexado. “Sem Whisper nesta fase”, “mínimo de dependências pesadas” e uma lista predeterminada de bibliotecas não devem ser decisões anteriores à pesquisa arquitetural. Também não usaria “um único Markdown com JSON entre marcadores” como banco ou modelo central; isso pode existir como formato humano de intercâmbio/auditoria, enquanto o core utiliza contratos tipados e armazenamento apropriado. A própria resposta anexada pede decisões específicas e defensáveis, portanto congelar tecnologia antes da análise contradiz esse objetivo.

Há ainda uma correção conceitual importante: a nova aplicação deve ser FR-first, mas não FR-hardcoded. O anexo define como propósito único transformar mídia da Franco Romeu, o que é coerente como produto inicial, mas eu manteria a arquitetura anterior de Universal Core + FR Domain Pack + FR Brand Pack + FR Content Strategy. Isso preserva especialização profunda sem transformar cada regra da empresa em dívida técnica do core.

A Parte II abaixo foi escrita justamente para ser colada imediatamente após o prompt anterior. Ela não repete a arquitetura já exigida; sua função é pressionar, validar, especializar e transformar a arquitetura concebida na Parte I em algo suficientemente rigoroso para depois entregar ao Codex.

Prompt Mestre FR AutoEdite Next — Parte II: Stress Test, Especialização FR e Contratos de Execução
PARTE II — FR AUTOEDITE NEXT
Stress Test Arquitetural, Inteligência Editorial FR, Provenance, Contratos e Preparação para Codex

Esta Parte II complementa integralmente a Parte I.

NÃO reinicie o projeto.

NÃO repita todas as seções da Parte I.

NÃO produza outra arquitetura independente.

Considere que a Parte I já lhe obrigou a conceber a melhor arquitetura possível para a próxima geração da FR AutoEdite.

Sua tarefa agora é:

tentar quebrar essa arquitetura;
encontrar premissas frágeis;
especializá-la para o uso real da Franco Romeu;
acrescentar requisitos operacionais ausentes;
transformar decisões conceituais em contratos verificáveis;
separar claramente hipótese, requisito, decisão e implementação;
preparar a arquitetura para posterior execução incremental pelo Codex.
1. PRINCÍPIO CENTRAL DESTA PARTE

A Parte I responde:

“Qual sistema deveríamos construir?”

A Parte II deve responder:

“Essa arquitetura realmente sobreviverá ao mundo real, aos arquivos reais, ao uso real da Franco Romeu, às decisões probabilísticas de IA, a falhas, a projetos antigos e à evolução futura?”

Sua função aqui é agir como:

Architecture Review Board;
Staff Engineer adversarial;
Technical Product Architect;
AI Safety/Validation Engineer;
Media Pipeline Engineer;
Director of Editing;
especialista em workflows audiovisuais reais;
especialista no domínio Franco Romeu.

Não proteja suas decisões anteriores.

Se uma arquitetura proposta na Parte I for frágil, corrija-a.

2. REGISTRO FORMAL DE PREMISSAS

Antes de continuar, extraia da arquitetura da Parte I todas as premissas relevantes.

Classifique cada uma como:

FACT;
REQUIREMENT;
ASSUMPTION;
HYPOTHESIS;
ARCHITECTURAL DECISION;
DEFERRED DECISION.

Exemplo:

ASSUMPTION
A maioria dos projetos possui informação temporal utilizável.

RISK
Arquivos de WhatsApp e exports podem destruir metadados.

MITIGATION
Combinar EXIF, filename, filesystem timestamps,
sidecars, análise visual e confirmação humana.

Não permita que uma suposição seja tratada como fato.

Crie um:

ASSUMPTION REGISTER

Ele deverá permanecer associado ao projeto técnico.

3. FR-FIRST, MAS NÃO FR-HARDCODED

A aplicação deve ser concebida prioritariamente para a Franco Romeu.

Entretanto, separe rigorosamente:

UNIVERSAL MEDIA CORE
        +
DOMAIN PACK
        +
BRAND PACK
        +
CONTENT STRATEGY PACK

A Franco Romeu deverá ser a primeira implementação completa desses sistemas.

UNIVERSAL MEDIA CORE

Não deve conhecer conceitos como:

pintura;
hidráulica;
móveis;
Franco Romeu;
quiet luxury.

Deve conhecer:

mídia;
tempo;
cenas;
objetos;
ações;
metadados;
timeline;
render;
áudio;
texto;
análise;
jobs.
FR DOMAIN PACK

Pode conhecer:

serviços;
processos;
materiais;
fases;
ambientes;
técnicas;
terminologia;
relações entre serviços.
FR BRAND PACK

Pode conhecer:

identidade;
grids;
logo;
tipografia;
movimento;
cards;
cores;
linguagem visual.
FR CONTENT STRATEGY

Pode conhecer:

formatos editoriais;
narrativa;
conteúdo técnico;
conteúdo comercial;
portfólio;
redes sociais.

Nenhuma regra puramente Franco Romeu deverá ser acoplada ao Media Core sem necessidade técnica.

4. REALIDADE DA INGESTÃO

Não imagine que os projetos chegam perfeitamente organizados.

Projete explicitamente para:

diretórios locais;
ZIP;
Google Takeout;
exports de celular;
cartão SD;
fotos;
vídeos;
timelapses;
screen recordings;
renders;
vídeos longos;
arquivos parcialmente duplicados;
arquivos renomeados;
arquivos sem data confiável;
mídia editada misturada com originais;
sidecars;
EXIF;
XMP;
GPS quando disponível;
timestamps inconsistentes.

A ingestão deve produzir:

MEDIA PROVENANCE

Para cada asset determine, quando possível:

source
original_path
import_batch
hash
perceptual_hash
creation_time
filesystem_time
device
codec
resolution
duration
exif
gps
sidecars
derived_from
suspected_duplicate_of
media_generation
5. GERAÇÕES DE MÍDIA

Um problema importante é impedir que versões exportadas sejam tratadas como matéria-prima original.

Projete classificação semelhante a:

G0 = original bruto
G1 = proxy
G2 = derivado técnico
G3 = edição intermediária
G4 = master/export
G5 = social derivative

Não adote obrigatoriamente esses nomes.

Mas resolva estruturalmente o problema.

Exemplo:

O sistema não deve selecionar automaticamente um Reel já exportado como se fosse gravação original da obra.

6. CLASSES SEMÂNTICAS QUE NÃO PODEM SER CONFUNDIDAS

A arquitetura deverá distinguir explicitamente:

referência visual;
moodboard;
render 3D;
projeto 3D;
planta/desenho técnico;
estado anterior da obra;
processo real;
resultado executado;
produto/material isolado;
conteúdo externo;
conteúdo promocional previamente produzido.

Isto é crítico.

Um render 3D NÃO constitui evidência de que determinada solução foi executada.

Uma referência do Pinterest NÃO constitui evidência de autoria.

Uma imagem de projeto NÃO pode ser automaticamente rotulada como “resultado final”.

Projete mecanismos para prevenir essas confusões.

7. PROVENANCE SEMÂNTICA

Cada afirmação produzida pelo sistema deverá possuir origem rastreável.

Exemplo conceitual:

CLAIM
"Instalação da iluminação LED"

EVIDENCE
asset_042
segment_07
00:13.400–00:21.800

SOURCE TYPE
real_process

MODEL CONFIDENCE
0.92

DOMAIN CONFIDENCE
0.86

Isso deve valer para:

cards;
balões;
legendas técnicas;
títulos;
descrições;
Story Engine;
classificação de etapas;
resumo do projeto.
8. PROIBIÇÃO DE AFIRMAÇÃO NÃO PROVADA

Projete níveis de afirmação.

Exemplo:

OBSERVED

Diretamente visível ou audível.

INFERRED

Inferência razoável da mídia.

PROVIDED

Informação fornecida pelo usuário ou projeto.

EXTERNAL

Informação oriunda de fonte externa.

UNKNOWN

Não comprovada.

O Graphics Engine e Story Engine devem conhecer essa distinção.

Exemplo:

Se a mídia mostra aplicação de revestimento, o sistema pode descrever o processo observado.

Se não existe informação suficiente para determinar o material específico, não deve inventá-lo.

9. CONTRATO ENTRE IA E CORE

Defina uma fronteira absoluta.

A IA NÃO deverá:

manipular arquivos diretamente;
inventar IDs;
criar timestamps inexistentes;
chamar FFmpeg arbitrariamente;
alterar banco de dados livremente;
executar shell;
modificar timeline diretamente.

A IA deverá produzir:

DECLARATIVE EDIT INTENT

Esse contrato pode conter conceitos como:

selected_segments
segment_order
editorial_role
crop_intent
overlay_intent
caption_intent
transition_intent
audio_intent
reason
confidence
evidence

O formato definitivo deverá ser definido tecnicamente na arquitetura.

10. VALIDATION GATE

Todo plano criado por IA deverá passar por validação determinística antes de ser aplicado.

O Validator deverá verificar pelo menos:

media_id existe;
segment_id existe;
timestamps pertencem ao arquivo;
início < fim;
duração válida;
asset não está corrompido;
claim possui evidência quando necessária;
style token existe;
template existe;
track suporta aquela operação;
formato é compatível;
recursos não colidem;
arquivo original não será modificado.

Se qualquer condição falhar:

PLAN != EXECUTABLE

O sistema retorna erro estruturado.

11. PLAN → VALIDATE → APPLY

Todas as operações relevantes deverão seguir algo conceitualmente equivalente a:

REQUEST
   ↓
INTENT
   ↓
PLAN
   ↓
VALIDATE
   ↓
DIFF
   ↓
SNAPSHOT
   ↓
APPLY
   ↓
AUDIT EVENT

O usuário deverá poder visualizar mudanças importantes antes de aplicá-las.

12. SNAPSHOTS TRANSACIONAIS

Antes de qualquer alteração significativa:

registrar estado;
registrar operação;
registrar origem;
registrar usuário/agente;
registrar versão do modelo;
registrar parâmetros relevantes.

Permitir:

undo
redo
restore
branch
duplicate version
regenerate

Investigue se event sourcing completo é justificável ou se snapshots + operation log são suficientes.

Não introduza complexidade sem benefício real.

13. EDITABILIDADE APÓS IA

Uma edição gerada por IA NÃO pode virar objeto opaco.

Depois da geração automática, o usuário deverá poder:

cortar;
alongar;
trocar take;
mover card;
editar texto;
remover card;
trocar estilo;
substituir música;
alterar ordem;
modificar crop;
alterar duração.

O projeto continua estruturalmente válido.

14. REPROCESSAMENTO RETROATIVO

Projete pensando no seguinte cenário:

Hoje existem 200 projetos.

A Franco Romeu altera o sistema de cards.

Não devemos reeditar manualmente 200 projetos.

O sistema deverá distinguir:

CONTENT DECISIONS
STYLE DECISIONS
RENDER DECISIONS

Assim poderá, quando tecnicamente possível:

mesma edição
+
novo Brand Pack
=
novo render

sem refazer a análise semântica inteira.

15. INVALIDAÇÃO DE CACHE

Defina uma estratégia formal.

Um artefato derivado precisa saber de quais inputs depende.

Exemplo conceitual:

preview_signature =
timeline_version
+ brand_pack_version
+ template_version
+ asset_hash
+ render_parameters

Se somente o template mudar:

não reexecutar visão computacional;
não retranscrever áudio;
não recalcular embeddings;
invalidar apenas resultados dependentes.

Projete um dependency graph de cache.

16. MEDIA INTELLIGENCE — VALOR EDITORIAL

Não se limite à qualidade técnica.

Para conteúdo Franco Romeu, investigue atributos editoriais como:

transformação;
ação;
materialidade;
detalhe técnico;
textura;
precisão;
uso de ferramenta;
revelação;
contraste antes/depois;
progressão;
dificuldade visível;
acabamento;
resultado;
composição;
novidade.

Um trecho tecnicamente perfeito pode ser editorialmente inútil.

Um trecho tecnicamente imperfeito pode documentar uma etapa essencial.

Crie separação entre:

TECHNICAL QUALITY
EDITORIAL VALUE
SEMANTIC VALUE
NARRATIVE VALUE
17. SCORE NÃO É VERDADE

Se utilizar scoring, ele deverá ser explicável e modular.

Evite:

magic_score = 0.87

Prefira dimensões independentes.

Exemplo:

sharpness       0.91
stability       0.75
action          0.93
novelty         0.88
technical_value 0.95
transformation  0.76

Diferentes Story Engines poderão aplicar pesos diferentes.

18. CONTEXTUAL SCORING

O “melhor take” depende da finalidade.

Um mesmo segmento pode receber:

technical_tutorial = 0.94
luxury_showcase    = 0.61
before_after       = 0.72
behind_the_scenes  = 0.89

Evite criar um ranking universal permanente.

19. ONTOLOGIA FR

Projete um modelo formal do domínio Franco Romeu.

Por exemplo:

SERVICE
PROCESS
PHASE
ACTION
MATERIAL
TOOL
ENVIRONMENT
COMPONENT
RESULT
DEFECT
SOLUTION

Exemplos de relações:

ACTION
uses TOOL

ACTION
acts_on MATERIAL

PROCESS
contains ACTION

SERVICE
contains PROCESS

PROJECT_PHASE
contains PROCESS

Não transforme isso necessariamente em um knowledge graph complexo se um modelo relacional resolver.

Escolha pela necessidade.

20. VOCABULÁRIO CONTROLADO + LINGUAGEM LIVRE

A aplicação deverá combinar:

VOCABULÁRIO CONTROLADO

Para classificação interna consistente.

NATURAL LANGUAGE

Para descrição rica.

Exemplo:

Internamente:

service = hydraulic
action = fixture_installation
component = kitchen_sink

Externamente:

“Instalação e ajuste da cuba na bancada.”

Isso reduz inconsistência sem empobrecer a comunicação.

21. RENDER 3D × OBRA REAL

Crie uma regra arquitetural explícita:

DESIGN INTENT != EXECUTED RESULT

O Story Engine pode mostrar:

Projeto 3D
→
Execução
→
Resultado

Mas jamais poderá fundi-los semanticamente.

22. BEFORE / PROCESS / AFTER COMO ENTIDADES

Não trate before/after como simples tags.

Projete relações como:

same_space
same_component
same_project
different_phase

Isso ajudará:

matching;
transformação;
carrossel;
comparação;
storytelling;
geração automática de pares.
23. RETENÇÃO × QUIET LUXURY

A aplicação não deverá otimizar retenção simplesmente aumentando:

número de cortes;
zoom;
texto;
efeitos;
velocidade.

Defina:

EDITORIAL PACING MODEL

Ele deve considerar:

plataforma;
conteúdo;
informação;
movimento existente;
complexidade visual;
etapa narrativa;
posicionamento da marca.

O objetivo é:

MAXIMIZAR DENSIDADE DE VALOR
≠
MAXIMIZAR QUANTIDADE DE CORTES
24. HOLD TIME

Investigue hold time adaptativo.

Por exemplo:

Um macro de textura pode justificar mais permanência.

Um deslocamento de câmera sem ação pode justificar corte rápido.

Um detalhe técnico pode precisar de tempo suficiente para compreensão.

Portanto:

hold_time =
function(
  semantic_complexity,
  motion,
  narrative_role,
  platform,
  visual_density
)

Não trate isso como fórmula fixa sem validação.

25. HOOKS VERIFICÁVEIS

O Hook Engine não poderá inventar:

números;
preço;
prazo;
depoimento;
dificuldade;
economia;
urgência;
escassez;
resultado.

Prefira hooks extraídos de informação verdadeira.

Exemplos de estruturas:

TRANSFORMATION
DETAIL
PROBLEM
CONTRAST
QUESTION
REVEAL
PROCESS

O hook deve possuir provenance.

26. BRAND FIDELITY COMO SISTEMA

Não basta armazenar:

orange = #...

O Brand Pack deve poder controlar:

typography;
logo;
spacing;
grid;
hierarchy;
corner treatment;
opacity;
motion timing;
transitions;
lower thirds;
card families;
safe areas;
caption style;
CTA;
intro/outro;
compositional rules.
27. FONT PIPELINE

A fidelidade tipográfica deve ser validada.

Considere:

disponibilidade da fonte;
versão;
licença;
fallback;
rasterização;
shaping;
kerning;
line breaking;
renderização no preview;
renderização no master.

Preview e render final não devem produzir composições radicalmente diferentes.

28. STYLE PACK VERSIONING

Cada Style Pack deverá possuir versão.

Exemplo conceitual:

FR_STYLE
1.0
1.1
2.0

Um projeto antigo deverá saber qual versão utilizou.

O usuário poderá optar por:

KEEP ORIGINAL STYLE

ou:

MIGRATE TO CURRENT STYLE
29. DESIGN TOKENS

Separe:

DESIGN TOKENS

de:

TEMPLATE GEOMETRY

e:

MOTION PRESET

Isso permitirá alterar identidade sem reconstruir todo o sistema de composição.

30. GUIA DE COMPOSIÇÃO ADAPTATIVA

Cards e balões devem reagir a:

proporção;
objeto principal;
rosto;
ferramentas;
mãos;
subtitle area;
safe area;
movimento;
outros overlays.

Crie um:

OCCUPANCY MAP

ou mecanismo equivalente.

O Graphics Engine deverá saber quais regiões do frame estão “ocupadas semanticamente”.

31. PRIVACIDADE LOCAL-FIRST

A arquitetura deverá funcionar fundamentalmente com mídia local.

Nenhum fluxo básico deverá exigir upload de mídia pessoal.

Quando um recurso cloud for habilitado:

indicar claramente o que será enviado;
para qual finalidade;
para qual serviço;
permitir cancelar;
permitir substituir por alternativa local quando existente.
32. LOCAL APPLICATION BOUNDARY

Se utilizar servidor local:

bind local;
autenticação/controle quando necessário;
nunca expor automaticamente a LAN;
CORS restritivo;
paths validados;
tokens protegidos;
nenhuma credencial no repositório.

Não assuma que 127.0.0.1 sozinho resolve toda segurança.

Faça threat model.

33. ARQUIVOS PESSOAIS

Defina políticas de:

project/
cache/
proxies/
renders/
models/
logs/
secrets/

Mídia pessoal e projetos locais não devem entrar acidentalmente no Git.

34. JOB ENGINE — REALIDADE OPERACIONAL

Teste sua arquitetura contra:

vídeo de 3 minutos;
vídeo de 90 minutos;
lote de 500 fotos;
projeto de 50 GB;
interrupção elétrica;
falta de espaço;
processo morto;
GPU indisponível;
modelo inexistente;
arquivo corrompido.

Jobs deverão possuir:

queued
running
paused
completed
failed
cancelled
recoverable

ou máquina de estados melhor.

35. RESOURCE SCHEDULER

Não execute simultaneamente:

transcrição pesada;
análise visual pesada;
render 4K;

se o hardware não suporta.

Projete um scheduler considerando:

CPU;
GPU;
VRAM;
RAM;
storage throughput;
prioridade do usuário.
36. GRACEFUL DEGRADATION

Se não houver GPU:

não significa que o programa deixa de funcionar.

Se um modelo multimodal estiver indisponível:

não significa que a ingestão deixa de funcionar.

Se a internet cair:

não significa que a timeline deixa de abrir.

Defina funcionalidades por níveis de capacidade.

37. CAPABILITY MATRIX

Crie uma matriz semelhante a:

CORE
CPU
GPU
LOCAL_AI
CLOUD_AI

E indique quais funcionalidades existem em cada nível.

O usuário precisa saber:

AVAILABLE
LIMITED
OPTIONAL
UNAVAILABLE
38. NÃO CONGELE TECNOLOGIAS PREMATURAMENTE

Nomes como:

FFmpeg;
GStreamer;
OpenCV;
PySceneDetect;
PyAV;
MediaPipe;
Ollama;
Whisper;
faster-whisper;
whisper.cpp;
Remotion;
OpenTimelineIO;

são candidatos.

Não são mandamentos.

Para cada categoria:

identifique requisito;
pesquise alternativas atuais;
construa shortlist;
compare;
escolha.
39. TECHNOLOGY DECISION RECORD

Cada escolha estrutural importante deverá gerar ADR.

Exemplo:

ADR-007
Timeline representation

Candidates:
A
B
C

Decision:
B

Why:
...

Rejected:
A because...
C because...

Revisit if:
...

Não use ADR para trivialidades.

40. REPOSITORY HEALTH

Ao recomendar projeto open source, analise:

licença;
releases;
atividade;
issues;
manutenção;
documentação;
API stability;
comunidade;
dependências;
plataforma;
performance;
facilidade de substituição.

Não selecione biblioteca somente porque possui muitas estrelas.

41. ABSTRACTION BOUNDARY

Dependências importantes devem ser encapsuladas.

Exemplo:

TranscriptionProvider
VisionProvider
TimelineSerializer
RenderBackend
EmbeddingProvider

Isso permite trocar implementação sem reescrever o produto.

Não abstraia tudo indiscriminadamente.

Abstraia especialmente componentes com:

fornecedor externo;
modelo de IA;
backend de render;
alta volatilidade tecnológica.
42. SPEECH ENGINE

Não imponha antecipadamente Whisper ou qualquer modelo específico.

Defina primeiro uma interface capaz de fornecer:

segments
words
timestamps
confidence
speaker optional
language

Depois selecione backend.

Na primeira milestone, speech intelligence poderá ser:

incluída;
reduzida;
postergada;

de acordo com dependências reais do MVP.

43. VISUAL INTELLIGENCE EM CAMADAS

Evite enviar todos os frames para um modelo multimodal caro.

Considere pipeline:

CHEAP SIGNALS
↓
CANDIDATE WINDOWS
↓
CLASSICAL CV
↓
SPECIALIZED MODEL
↓
MULTIMODAL REASONING

Use inteligência cara onde ela produz valor.

44. FRAME SAMPLING INTELIGENTE

Não analise necessariamente 24 ou 60 frames por segundo semanticamente.

Projete estratégias baseadas em:

scene boundaries;
motion;
entropy;
keyframes;
temporal sampling;
detected actions.

Determine quais etapas precisam de frame-level precision.

45. HIERARQUIA DE ANÁLISE

Considere níveis:

ASSET
SHOT
SCENE
SEGMENT
FRAME
REGION

Uma classificação deve informar a granularidade.

Exemplo:

asset = kitchen_project
scene = island_installation
segment = cutting_countertop
region = hand/tool
46. RESULTADOS DE IA PRECISAM DE VERSIONAMENTO

Registre:

provider;
model;
model version;
prompt/template version;
parameters;
timestamp;
confidence;
source inputs.

Se um modelo for trocado, o sistema deverá saber que análises antigas pertencem a outro pipeline.

47. REANÁLISE SELETIVA

Ao instalar um detector melhor de cenas:

não reexecute necessariamente toda inteligência semântica.

Projete lineage entre analyses.

48. HUMAN REVIEW QUE REALMENTE AJUDA

Não obrigue o usuário a revisar milhares de detecções.

Crie interfaces de revisão para decisões de alto impacto.

Exemplos:

LOW CONFIDENCE
CONFLICT
NO EVIDENCE
DUPLICATE
AMBIGUOUS PHASE

O humano deve revisar exceções, não atuar como operador do algoritmo.

49. ACTIVE LEARNING LOCAL

Avalie se correções humanas podem melhorar futuros projetos.

Exemplo:

Usuário corrige repetidamente:

"isto é iluminação, não elétrica"

A aplicação pode:

aprender preferência;
criar regra;
atualizar vocabulário;
sugerir correção futura.

Mas não crie treinamento complexo sem justificativa.

Considere primeiro:

preference memory;
rules;
exemplars;
embeddings;
few-shot context.
50. COMPETITIVE DECOMPOSITION

Compare conceitualmente a solução com categorias representadas por:

Premiere;
DaVinci Resolve;
CapCut;
Descript;
Opus Clip;
VEED;
Submagic;
Munch;
Auto-Editor;
ferramentas emergentes equivalentes.

Não produza propaganda.

Para cada uma, identifique:

WHAT THEY OPTIMIZE FOR
WHAT THEY DO WELL
WHAT FR AUTOEDITE SHOULD NOT COPY
WHAT CONCEPT IS WORTH ADOPTING

A comparação deverá utilizar informação atual quando pesquisa externa estiver disponível.

51. NÃO TENTE VENCER UM NLE EM TUDO

A FR AutoEdite não precisa possuir:

color grading equivalente ao DaVinci;
compositor equivalente ao After Effects;
timeline equivalente ao Premiere;
editor gráfico equivalente ao Canva.

Descubra seu produto específico.

Uma hipótese central a ser validada é:

A FR AutoEdite deve dominar a transformação de acervos brutos de obras e projetos em narrativas sociais estruturadas, tecnicamente contextualizadas, visualmente consistentes e multi-output.

Teste essa hipótese.

52. DIFERENCIAL DEFENSÁVEL

Investigue especialmente:

PROJECT-AWARE EDITING

A mídia pertence a um projeto e possui significado dentro dele.

DOMAIN-AWARE EDITING

A aplicação entende serviços, ações e etapas.

EVIDENCE-AWARE GENERATION

Texto e narrativa possuem provenance.

SEMANTIC MEDIA MEMORY

O acervo se torna pesquisável.

EXPLAINABLE AUTOEDIT

A IA informa por que tomou decisões relevantes.

BRAND-AWARE COMPOSITION

Branding faz parte do motor de composição.

MULTI-OUTPUT STORY GRAPH

Um entendimento editorial pode gerar diversas saídas sem reanalisar tudo.

Determine quais realmente constituem vantagem arquitetural.

53. STORY GRAPH

Investigue se uma única timeline master é suficiente.

Talvez seja melhor representar primeiro uma estrutura narrativa abstrata.

Exemplo:

PROJECT STORY
│
├── BEFORE
├── PROBLEM
├── PROCESS
│   ├── demolition
│   ├── infrastructure
│   ├── furniture
│   └── lighting
├── DETAILS
└── RESULT

Dessa estrutura poderiam nascer:

60s Reel
30s Reel
Technical Cut
Before/After
Stories
Long Film

Compare:

MASTER TIMELINE FIRST

versus:

STORY GRAPH FIRST

Escolha conscientemente.

54. CONTENT ATOMS

Avalie representar material editorial como átomos reutilizáveis:

atom:
service
phase
action
media windows
description
evidence
importance

Isso pode permitir novas edições sem reanalisar arquivos.

Não adote se duplicar desnecessariamente outras estruturas.

55. MULTI-OUTPUT NÃO DEVE SER "AUTO-CROP"

Gerar versão 30s a partir de 90s não deve significar simplesmente cortar duração.

Cada output pode possuir narrativa diferente.

Exemplo:

90s
process-focused

30s
transformation-focused

15s
result-focused

Compartilham conhecimento, não necessariamente a mesma montagem.

56. PUBLICAÇÃO NÃO É O CORE INICIAL

Diferencie:

CREATE CONTENT

de:

PUBLISH CONTENT

Integrações com:

Drive;
cloud;
redes sociais;
storage externo;

devem ser plugins/adapters quando possível.

Não transforme APIs de terceiros em dependência estrutural do editor.

57. EXPORT MANIFEST

Cada export deverá possuir registro.

Exemplo:

project
version
timeline/story
brand pack
output preset
resolution
fps
codec
audio
render date
source version

Isso permite reproduzir o conteúdo publicado.

58. CONTENT LINEAGE

Deve ser possível responder:

De qual projeto este Reel veio?

Qual timeline o produziu?

Quais mídias foram usadas?

Qual Style Pack estava ativo?

Qual modelo sugeriu os cortes?

Houve alterações humanas?

Projete essa rastreabilidade.

59. TESTE COM CASOS REAIS

Não valide somente componentes.

Crie cenários de produto.

CASE A — Projeto organizado

20 vídeos claros.

CASE B — Takeout

400 mídias misturadas.

CASE C — Vídeo longo

90 minutos.

CASE D — Projeto incompleto

Sem “before”.

CASE E — Mídia ambígua

Render + obra real.

CASE F — CPU ONLY

Sem GPU.

CASE G — Rebrand

Projeto antigo recebe Style Pack novo.

CASE H — Recuperação

Aplicação interrompida durante análise.

A arquitetura deve explicar o comportamento esperado em todos.

60. FAILURE INJECTION

Inclua testes deliberados:

apagar proxy;
mover original;
corromper arquivo;
matar worker;
lotar disco;
remover GPU;
invalidar API;
alterar versão de Style Pack;
interromper render.

Verifique se o sistema falha de maneira controlada.

61. PERFORMANCE BUDGET

Defina orçamento de performance para:

abertura de projeto;
scrubbing;
preview;
ingestão;
geração de proxy;
análise;
render;
busca semântica.

Não precisa definir números arbitrários agora.

Mas a arquitetura deve permitir medir.

62. STORAGE BUDGET

Grandes projetos geram:

originals;
proxies;
thumbnails;
waveforms;
embeddings;
analysis;
previews;
masters.

Projete:

limpeza;
cache eviction;
pinning;
armazenamento externo;
cálculo de espaço;
proteção de original.
63. RELOCATABLE PROJECTS

Um projeto não deve quebrar completamente se:

/home/user/videos

virar:

/mnt/storage/videos

Projete:

relative paths;
asset IDs;
relink;
hash matching;
media search.
64. OFFLINE ARCHIVE

Avalie capacidade de arquivar projeto preservando:

projeto;
decisões;
textos;
metadata;
manifests;
thumbnails;
eventualmente proxies;

sem necessariamente duplicar todos os originais.

65. HUMAN-EDITABLE INTERCHANGE

É útil possuir um artefato legível por humano/IA.

Por exemplo:

PROJECT_BRIEF.md
EDIT_REVIEW.md
AI_EDIT_REQUEST.md

com blocos estruturados.

Entretanto:

não use Markdown como banco de dados principal apenas por conveniência.

O formato humano deve funcionar como:

INTERCHANGE / REVIEW / AUDIT

e ser validado contra schemas internos.

66. SCHEMA VERSIONING

Contratos deverão possuir versões.

Exemplo:

edit_plan.schema.v1
edit_plan.schema.v2

Defina:

migration;
compatibility;
validation;
deprecation.
67. MIGRATION TESTS

Não basta escrever migração.

Mantenha fixtures de projetos antigos.

Toda versão deverá provar que consegue:

abrir;
migrar;
preservar;
ou rejeitar explicitamente um formato antigo.
68. PLUGIN TRUST MODEL

Se existir plugin system:

não permita execução arbitrária sem pensar em segurança.

Classifique plugins:

internal;
trusted;
external.

Defina capabilities.

Exemplo:

read project
read media
write analysis
register template
register exporter
network
69. MODEL DOWNLOAD SECURITY

Se modelos de IA forem baixados:

origem;
checksum;
versionamento;
cache;
licença;
tamanho;
integridade;

devem ser conhecidos.

70. LICENSING REVIEW

A escolha de tecnologias deverá considerar uso comercial.

Não basta o código funcionar.

Analise:

software license;
model license;
font license;
codec implications;
redistribuição.

Qualquer incerteza deve ser explicitada.

71. DEPENDENCY MINIMIZATION COMO CONSEQUÊNCIA

Não adote:

“menos dependências sempre é melhor”.

Adote:

“cada dependência precisa justificar seu custo operacional”.

Para cada dependência pesada responda:

qual problema resolve;
existe substituto;
pode ser opcional;
afeta instalador;
afeta atualização;
afeta segurança;
afeta performance;
afeta cross-platform.
72. DEBIAN/LINUX COMO PRIORIDADE DE ENTREGA

Considere Linux/Debian-like como alvo prioritário inicial caso isso corresponda ao ambiente operacional estabelecido.

Mas evite acoplar o domínio e o core de forma que Windows/macOS se tornem estruturalmente impossíveis.

Separe:

CORE PORTABILITY

de:

FIRST SUPPORTED PLATFORM
73. NO TERMINAL COMO UX PADRÃO

Ferramentas de diagnóstico podem possuir CLI.

Mas o fluxo normal deve existir no Studio.

O usuário não deve precisar decorar comandos para:

importar;
analisar;
editar;
gerar;
recuperar;
atualizar packs;
exportar.
74. UX DE EXPLICAÇÃO

O Studio deve diferenciar visualmente:

SOURCE FACT
AI INFERENCE
AI SUGGESTION
MANUAL DECISION
SYSTEM ACTION
WARNING
ERROR

Isso é particularmente importante em um editor assistido por IA.

75. CONFIDENCE NÃO DEVE POLUIR A INTERFACE

Não mostre centenas de números ao usuário comum.

Use confidence internamente.

Exponha-a quando:

decisão é ambígua;
confiança é baixa;
existe conflito;
usuário solicita detalhes;
afirmação possui implicação técnica.
76. REVIEW BY EXCEPTION

A interface ideal deverá dizer algo semelhante:

147 assets analisados
12 decisões precisam de revisão

e não:

revise 4.912 classificações
77. SIMPLE MODE

O usuário deveria conseguir:

NOVO PROJETO
→
IMPORTAR
→
OBJETIVO
→
ANALISAR
→
REVISAR EXCEÇÕES
→
GERAR
78. PRO MODE

Usuários avançados poderão acessar:

timeline;
analysis;
weights;
metadata;
diagnostics;
jobs;
model providers;
cache;
render graph.

Simple e Pro devem utilizar o mesmo core.

79. NÃO CRIE DOIS PRODUTOS

Evite:

simple app
+
pro app

Mantenha progressividade de complexidade.

80. ARCHITECTURAL RED TEAM

Depois de consolidar todas as decisões, ataque sua própria arquitetura.

Procure:

single point of failure;
overengineering;
abstração excessiva;
dependência excessiva de IA;
dependência de um fornecedor;
gargalo de storage;
gargalo de GPU;
gargalo de banco;
UX excessivamente complexa;
contratos difíceis de migrar;
plugin system prematuro;
Story Engine impossível de testar;
pipeline caro demais.
81. TRÊS FALHAS MAIS PROVÁVEIS

Identifique as três coisas com maior probabilidade de destruir o projeto.

Não escolha problemas superficiais.

Para cada uma:

FAILURE MODE
WHY IT IS DANGEROUS
EARLY SIGNAL
MITIGATION
FALLBACK
82. PRE-MORTEM

Imagine:

É 18 meses no futuro e o FR AutoEdite Next fracassou.

Explique as cinco causas técnicas ou de produto mais plausíveis.

Depois adapte o desenho para reduzi-las.

83. COMPLEXITY BUDGET

Cada grande sistema deverá justificar existir.

Classifique:

ESSENTIAL NOW
ESSENTIAL FOUNDATION
LATER
EXPERIMENTAL
REJECT

Especialmente para:

knowledge graph;
vector database;
agents;
plugin marketplace;
event sourcing;
cloud;
multi-user;
generative video;
model training.
84. BUILD VS BUY VS INTEGRATE

Para cada capacidade complexa, determine:

BUILD
ADAPT
INTEGRATE
OUTSOURCE

Exemplos:

timeline;
transcription;
scene detection;
rendering;
motion graphics;
embeddings;
object tracking.
85. ARCHITECTURE FREEZE

Depois da pesquisa e do Red Team, produza:

ARCHITECTURE FREEZE v1

Não significa que nunca mudará.

Significa que o Codex não deve começar a implementar enquanto questões estruturais fundamentais continuam abertas.

86. DECISIONS THAT MUST BE FROZEN

Antes da implementação determine pelo menos:

linguagem/core;
runtime;
UI architecture;
project format;
database;
timeline representation;
render backend;
job model;
media identity;
analysis storage;
AI provider boundary;
plugin boundary;
Brand Pack contract;
schema strategy.
87. DECISIONS THAT MAY REMAIN PLUGGABLE

Exemplos:

transcription model;
multimodal provider;
embedding model;
detector;
music source;
cloud integrations.

Não confunda arquitetura estável com tecnologias imutáveis.

88. CODEX IMPLEMENTATION CONTRACT

Depois do Architecture Freeze, gere regras para o Codex.

O Codex deverá receber:

ARCHITECTURE
ADR
SCHEMAS
DEPENDENCY RULES
TESTS
ACCEPTANCE CRITERIA
MILESTONE

E não apenas uma descrição em linguagem natural.

89. CODEX NÃO DEVE REDESENHAR A ARQUITETURA DURANTE CADA PR

O Codex poderá identificar problemas.

Mas mudanças estruturais deverão produzir:

ARCHITECTURE CHANGE REQUEST

antes de serem aplicadas.

Isso evita deriva arquitetural entre dezenas de PRs.

90. VERTICAL SLICE PRIMEIRO

Antes de implementar todos os subsistemas, construa um vertical slice mínimo que prove a arquitetura.

Exemplo conceitual:

IMPORT 1 VIDEO
↓
IDENTIFY
↓
GENERATE PROXY
↓
DETECT SCENES
↓
CREATE PROJECT
↓
CREATE SIMPLE TIMELINE
↓
ADD 1 GRAPHIC
↓
PREVIEW
↓
RENDER
↓
REOPEN PROJECT

Sem IA avançada inicialmente.

Esse slice deve provar:

project model;
jobs;
timeline;
render;
persistence;
recovery.
91. INTELLIGENCE SECOND SLICE

Depois:

ANALYZE
↓
SUGGEST SEGMENTS
↓
PLAN
↓
VALIDATE
↓
USER REVIEW
↓
APPLY

Isso prova a fronteira IA/core.

92. FR DOMAIN SLICE

Depois:

PROJECT CONTEXT
↓
FR CLASSIFICATION
↓
STORY STRUCTURE
↓
FR GRAPHICS
↓
SOCIAL OUTPUT

Isso prova a especialização de domínio sem contaminar o core.

93. NÃO FAÇA UI COMPLETA ANTES DO CORE FUNCIONAR

Evite construir dezenas de telas sobre contratos ainda instáveis.

Use inicialmente interfaces mínimas suficientes para testar workflows.

Depois refine UX.

94. NÃO FAÇA IA AVANÇADA ANTES DA LINHA DE BASE

Primeiro crie baseline determinístico mensurável.

Depois meça quanto a IA melhora:

seleção;
classificação;
tempo manual;
qualidade percebida.

Sem baseline, “IA melhor” vira opinião.

95. MÉTRICAS DO PRODUTO

Além de performance técnica, considere:

TIME TO FIRST USABLE CUT
MANUAL INTERVENTIONS
REJECTED AI SUGGESTIONS
PROJECT RECOVERY SUCCESS
CACHE REUSE
RENDER FAILURE RATE
CLAIM VALIDATION FAILURE

Não trate essas métricas como metas arbitrárias inicialmente.

Use-as para comparação.

96. HUMAN EFFORT AS PRIMARY KPI

Uma das métricas centrais deverá ser:

Quanto trabalho humano é necessário para transformar mídia bruta em conteúdo publicável sem sacrificar qualidade?

Meça tarefas humanas evitadas.

97. QUALITY NÃO PODE SER UM ÚNICO NÚMERO

Avalie separadamente:

technical;
editorial;
factual;
brand;
narrative;
render.
98. BENCHMARK DATASET

Construa futuramente um conjunto interno de projetos anonimizados ou autorizados para avaliação.

Deve possuir exemplos de:

boa seleção;
má seleção;
before/after;
render/real;
serviços;
áreas mortas;
duplicatas;
baixa qualidade;
bons detalhes técnicos.

Isso será essencial para medir evolução da inteligência.

99. GOLDEN EDITS

Além de Golden Projects, mantenha edições aprovadas como referência.

O objetivo não é treinar automaticamente.

É permitir regressão:

nova versão
vs
edição de referência
100. ENTREGÁVEIS ADICIONAIS DA PARTE II

Além dos entregáveis da Parte I, produza:

A. ASSUMPTION_REGISTER.md

Premissas e riscos.

B. SYSTEM_INVARIANTS.md

Regras que nunca podem ser violadas.

Exemplos:

Original media is immutable.
AI cannot reference nonexistent media.
Technical claims require provenance.
C. MEDIA_PROVENANCE_SPEC.md

Identidade, geração e lineage dos assets.

D. AI_CORE_CONTRACT.md

Fronteira entre modelos e execução determinística.

E. FR_DOMAIN_MODEL.md

Ontologia/vocabulário operacional.

F. BRAND_PACK_SPEC.md

Contrato de identidade e motion.

G. CACHE_DEPENDENCY_GRAPH.md

Reprocessamento seletivo.

H. CAPABILITY_MATRIX.md

CPU/GPU/local/cloud.

I. FAILURE_MODEL.md

Falhas e recuperação.

J. ARCHITECTURE_RED_TEAM.md

Auto-crítica e pre-mortem.

K. ARCHITECTURE_FREEZE_V1.md

Decisões congeladas antes do Codex.

L. VERTICAL_SLICE_PLAN.md

Primeiro fluxo ponta a ponta.

101. SYSTEM INVARIANTS OBRIGATÓRIOS

Analise e refine pelo menos estes invariantes:

INVARIANT 01

Original nunca é modificado.

INVARIANT 02

Nenhuma operação de IA é aplicada sem validação estrutural.

INVARIANT 03

IA não pode referenciar mídia ou intervalo inexistente.

INVARIANT 04

Afirmação factual/técnica precisa possuir origem.

INVARIANT 05

Render 3D não equivale a obra executada.

INVARIANT 06

Projeto precisa ser recuperável após interrupção.

INVARIANT 07

Reprocessamento deve reutilizar trabalho anterior sempre que inputs dependentes não mudaram.

INVARIANT 08

Core deve funcionar sem cloud obrigatória.

INVARIANT 09

Decisões automáticas relevantes devem ser reversíveis.

INVARIANT 10

Branding não deve estar hardcoded no motor universal.

102. DECISION MATRIX FINAL

Antes do Prompt Operacional do Codex, produza uma matriz final contendo:

Decisão	Escolha	Evidência	Trade-off	Status
Core language	...	...	...	FROZEN
Timeline	...	...	...	FROZEN
STT backend	...	...	...	PLUGGABLE
Vision backend	...	...	...	PLUGGABLE

Use estados como:

FROZEN
PLUGGABLE
DEFERRED
EXPERIMENTAL
103. RESEARCH BACKLOG

Nem todas as decisões precisam ser fingidamente resolvidas.

Quando evidência for insuficiente:

RESEARCH ITEM
QUESTION
CANDIDATES
TEST
DECISION CRITERIA

Não transforme dúvida real em falsa certeza.

104. PROTOTYPE BEFORE COMMITMENT

Quando duas tecnologias permanecerem equivalentes, proponha spike técnico.

Exemplo:

SPIKE-003
Compare timeline backend A vs B.

Dataset:
3 reference projects.

Measure:
serialization
seek
edit operations
render integration
complexity

Depois decidir.

105. SAÍDA FINAL DA PARTE II

Sua resposta a esta Parte II deverá terminar com cinco blocos claramente separados:

1. CORREÇÕES À ARQUITETURA DA PARTE I

Tudo que você alteraria após este stress test.

2. ARQUITETURA CONSOLIDADA

Somente diferenças e decisões finais; não repita toda a Parte I inutilmente.

3. ARCHITECTURE FREEZE v1

Decisões necessárias para iniciar implementação.

4. RESEARCH/SPIKES PENDENTES

Somente questões cuja resolução depende de teste ou pesquisa adicional.

5. DELTA PARA O PROMPT OPERACIONAL DO CODEX

Liste exatamente o que precisa ser acrescentado ao Prompt Operacional produzido na Parte I.

106. REGRA DE NÃO REDUNDÂNCIA

Antes de escrever qualquer seção, pergunte internamente:

Isto já foi completamente especificado na Parte I?

Se SIM:

não repita.

Apenas:

refine;
corrija;
torne verificável;
acrescente requisito ausente;
registre conflito.

A Parte II existe para aumentar a qualidade da Parte I, não para duplicá-la.

107. REGRA DE CONFLITO

Se esta Parte II contradizer uma decisão da Parte I:

não escolha silenciosamente.

Produza:

CONFLICT

PART I
...

PART II REQUIREMENT
...

ANALYSIS
...

FINAL DECISION
...

WHY
...
108. REGRA DE TECNOLOGIA

Não mantenha uma tecnologia simplesmente porque foi citada neste prompt.

Toda tecnologia mencionada é:

CANDIDATE

até ser tecnicamente selecionada.

109. REGRA DE CONTEXTO

Use todo contexto confiável disponível sobre a Franco Romeu para compreender:

serviços;
estética;
produção de mídia;
operação;
conteúdo;
objetivos.

Entretanto:

não invente informação ausente.

Quando o projeto depender de uma informação não comprovada:

ASSUMPTION

ou:

RESEARCH REQUIRED
110. REGRA FINAL

Ao terminar Parte I + Parte II, o sistema proposto não deverá parecer:

“um editor de vídeo com alguns recursos de IA”.

Ele deverá possuir uma tese arquitetural clara.

Uma hipótese que merece forte consideração é:

FR AutoEdite Next é um sistema local-first de inteligência de mídia e edição não destrutiva, orientado a projeto e domínio, que transforma acervos brutos em narrativas verificáveis, editáveis, reutilizáveis e multi-output, mantendo a IA separada da execução determinística.

Você não é obrigado a aceitar essa definição.

Teste-a.

Melhore-a.

Rejeite-a se encontrar formulação arquitetural superior.

O objetivo final não é preservar minhas ideias.

É encontrar a melhor arquitetura tecnicamente defensável para que o Codex consiga construir a aplicação incrementalmente, sem dívida estrutural deliberada e sem transformar decisões probabilísticas de IA em comportamento não auditável.

O que esta Parte II melhora de verdade

Ela incorpora o que havia de mais forte na outra IA — ingestão real, procedência, classificação render/real, dual-mode, reversibilidade, branding e privacidade — sem repetir as dezenas de módulos já cobertos na Parte I. O anexo também tinha uma boa exigência de auto-crítica e identificação dos pontos frágeis da própria proposta, que transformei em Architectural Red Team + Pre-mortem + Architecture Freeze.

A alteração mais importante, porém, é outra: agora o futuro ChatGPT não poderá simplesmente produzir uma arquitetura bonita e então mandar o Codex construí-la. Ele terá de passar por Part I → Stress Test → conflitos → Red Team → Architecture Freeze → spikes pendentes → Codex. Isso reduz bastante a chance de a recriação começar cedo demais e depois exigir outra reescrita estrutural.

FR_CARD_EDITOR_UNIVERSAL_v1.1.0(1).zip
Arquivo zip
vamos implementar na aplicação uma aplicação de edição para os cards q deve conversar com a aplicação atual e dar a opção de editar manualmente ou inserir os cards nos trechos dos videos irei anexar a aplicação aqui e tambem na pasta do fr autoedite /home/romeu/FR-AutoEdite/FR_AUTOEDITE_4.0 q ja esta logada no github, colocarei na raiz para que o codex execute os doisprompts ais o prompt q vc vai gerar dizendo exatamente oq ele deve fazeer de forma mais resumida tambem irei colar na raiz da pasta os dois prompts em txt para o codex revisar quando for necessario nomeei elas de "promptcodexpart1" "promptcodexpart2" na raiz irei anexar a aplicação de edição de cards sera o novo modelo de cards atual deve implementar a funcionalidade de edição de acrds a arrea do fr autoedite de "enviar a ia" para que pelo contexto respondido do prompt mestre consiga fazer a edição de todas as areas das cards com informações referente ao projeto atual e video, e tambem quando selecionarmosr uma card de serviço ou a ia decidir colocar nesta aplicação tem a opção de adicionar imagem central e esta imagem central do card de serviço deve sempre estar no formato circular com a opção de zoom distante, a ia deve editar as cads pois são partes essenciais do fr edite e redesenhar os baloes do video para ficarem como grids e linhas com degradencia final no gradiante de transpatencia parecendo as linhas e grids das cards e o tamanho do balão deve condizer com o tamanho do texto para nao ficar algo vazio.
vamos realizar uma forma de otimizar o prompt mestre do markdown gerado para que nao fique algo extensivo para uma ia editar todos os detalhes, devemos otimizar da melhor maneira possivel para ser melhor que o atual e englobar todas as opções da aplicação fr autoedite pois na maioria dos testes a ia demora muito a depurar o reoteiro mestre e muitas vezes edita mal ou erra e da falha ou simplesmente coloca informações meramente institucionais ou que so coupam espaço, e nao consegue fazer otimização dos recortes
promptcodexpart1.txt
Documento
promptcodexpart2.txt
Documento
promptcodexpart3.txt
Documento
FR_CARD_EDITOR_UNIVERSAL_v1.1.0(2).zip
Arquivo zip
recebi a suintes  resposta vc tem total liberdade de decidir se esta correta ou nao, irei anexar os tres promps que iria enviar ao codex part 1 2 3 e ver se esta correto oq a outra ia eta alegando e qual a melhor opção atual q temos.# Como iniciar a atualização da FR AutoEdite com esses 3 prompts
minha pergunta para ia foi a seguinte:
(Vou usar o editor de cards anexado como referência concreta e transformar meu pedido em um prompt operacional curto que irei anexar junto ao promptpart 1 e 2 para o Codex, complementar aos promptcodexpart1 e promptcodexpart2. O foco será integração real com a FR AutoEdite 4.0, edição manual + IA, inserção temporal dos cards, vamos implementar na aplicação autoedite uma aplicação de edição para os cards q deve conversar com a aplicação atual e dar a opção de editar manualmente ou inserir os cards nos trechos dos videos irei anexar a aplicação aqui em zip e la ja extraida a pasta com os arquivos (FR_CARD_EDITOR_UNIVERSAL_v1.1.0) e tambem na pasta do fr autoedite /home/romeu/FR-AutoEdite/FR_AUTOEDITE_4.0 q ja esta logada no github, colocarei na raiz para que o codex execute os dois prompts  part1 e 2  tambem irei colar na raiz da pasta os dois prompts em txt para o codex revisar quando for necessario nomeei elas de "promptcodexpart1" "promptcodexpart2" na raiz irei anexar a aplicação de edição de cards sera o novo modelo de cards atual deve implementar a funcionalidade de edição de acrds a arrea do fr autoedite de "enviar a ia" para que pelo contexto respondido do prompt mestre consiga fazer a edição de todas as areas das cards com informações referente ao projeto atual e video, e tambem quando selecionarmosr uma card de serviço ou a ia decidir colocar nesta aplicação tem a opção de adicionar imagem central e esta imagem central do card de serviço deve sempre estar no formato circular com a opção de zoom distante, a ia deve editar as cads pois são partes essenciais do fr edite e redesenhar os baloes do video para ficarem como grids e linhas com degradencia final no gradiante de transpatencia parecendo as linhas e grids das cards e o tamanho do balão deve condizer com o tamanho do texto para nao ficar algo vazio. vamos realizar uma forma de otimizar o prompt mestre do markdown gerado para que nao fique algo extensivo para uma ia editar todos os detalhes, devemos otimizar da melhor maneira possivel para ser melhor que o atual e englobar todas as opções da aplicação fr autoedite pois na maioria dos testes a ia demora muito a depurar o reoteiro mestre e muitas vezes edita mal ou erra e da falha ou simplesmente coloca informações meramente institucionais ou que so coupam espaço, e nao consegue fazer otimização dos recortes, vamos melhorar e otimizar isso, e melhorar a função automatica tambem do fr autoedite para ele fazer edições autonomas com as ferramentas que iremos adicionar a edição autonoma nao deve usar ia obrigatoriamente. e garantir que quando usamos a opção de enviar markdown para ia para q ela edite o roteiro mestre o arquivo gerado deve conter somente informações zeradas e somente sobre o contexto e os videos/proxys devemos garatir q a ia vai receber um arquivo zerado toda vez q clicarmos em gerar e nao haja resquicios de edições anteriores ou falte algum dos proxys, e garantir que os proxys sejam os videos originais sem faltar partes.)

a resposta foi a part3 anexada, e ao anexar nela as tres partes a resposta foi:

Antes de qualquer comando, é importante entender o que cada prompt **realmente é** — porque existe uma armadilha comum aqui.

---

## 1. Natureza de cada prompt (não misture)

| Prompt | O que ele pede | O que ele produz | Quem deve rodar |
|---|---|---|---|
| **part1** | Reconcepção arquitetural completa | Um documento gigante de design (não código) | Modelo com raciocínio longo (GPT-5 thinking, Codex reasoning, Claude) |
| **part2** | Stress test da arquitetura + contratos + freeze | Correções, invariantes, freeze v1, delta para Codex | Mesmo modelo, com part1 + resposta da part1 no contexto |
| **part3** | Integração concreta do Card Editor + ajustes pontuais | Especificação operacional de integração | Codex ou modelo com foco em execução |

**Regra crítica:** parts 1 e 2 **proíbem implementação** explicitamente. Se você mandar o Codex "executar" os três de uma vez, ele vai produzir um tratado arquitetural e nunca tocar em código. Ou pior: vai tentar codar direto sem o freeze, e vai gerar dívida estrutural.

O fluxo correto é **em 3 etapas separadas**, cada uma com um artefato concreto.

---

## 2. Sequência recomendada (etapas separadas)

### Etapa A — Design arquitetural (parts 1 + 2)

**Onde rodar:** num chat de raciocínio longo (não no Codex dentro do repo).
**Por quê:** o output vai ser grande e você precisa poder reler, editar e versionar antes de virar contrato.

1. Cole **part1** sozinho.
2. Espere a resposta completa (vai ser longa — Partes A a Z).
3. Copie essa resposta inteira.
4. Abra **novo chat**, cole a resposta da part1 + **part2**.
5. Espere a resposta (blocos 1 a 5 do item 105).
6. Salve os dois outputs como arquivos no repo:


FR_AUTOEDITE_4.0/docs/design/
├── 00_PART1_ARCHITECTURE.md
├── 01_PART2_STRESS_TEST.md
├── ASSUMPTION_REGISTER.md
├── SYSTEM_INVARIANTS.md
├── AI_CORE_CONTRACT.md
├── ARCHITECTURE_FREEZE_V1.md
└── VERTICAL_SLICE_PLAN.md


Não avance sem esses arquivos existirem. Eles são o contrato que o Codex vai seguir.

---

### Etapa B — Preparar o terreno no repositório

Antes de chamar o Codex para codar:


bash
cd ~/FR-AutoEdite/FR_AUTOEDITE_4.0

# Confirme que está na main atualizada
git checkout main
git pull origin main
git status          # deve estar limpo

# Crie a branch de trabalho
git checkout -b codex/fr-autoedite-next-foundation

# Crie a pasta de design e coloque os arquivos da Etapa A
mkdir -p docs/design
# (copie os .md gerados pela part1 e part2 para cá)

git add docs/design/
git commit -m "docs: arquitetura e freeze v1 da próxima geração"
git push -u origin codex/fr-autoedite-next-foundation


Também confirme que a pasta do Card Editor está na raiz:


bash
ls -la FR_CARD_EDITOR_UNIVERSAL_v1.1.0/


E que os 3 prompts estão na raiz como referência:


bash
ls -la promptcodexpart1.txt promptcodexpart2.txt promptcodexpart3.txt


---

### Etapa C — Execução pelo Codex (part3 + vertical slice)

**Aqui sim o Codex entra.** Mas não mande os 3 prompts de uma vez. Mande **um pacote inicial curto**, referenciando os arquivos em disco.

**Mensagem inicial para o Codex (colar no chat do Codex dentro do repo):**


Você está no repositório /home/romeu/FR-AutoEdite/FR_AUTOEDITE_4.0,
branch codex/fr-autoedite-next-foundation.

Leia nesta ordem:
1. docs/design/ARCHITECTURE_FREEZE_V1.md
2. docs/design/SYSTEM_INVARIANTS.md
3. docs/design/AI_CORE_CONTRACT.md
4. docs/design/VERTICAL_SLICE_PLAN.md
5. promptcodexpart3.txt

Execute SOMENTE a Parte 3 (integração do Card Editor) e o
VERTICAL SLICE mínimo descrito em docs/design/VERTICAL_SLICE_PLAN.md.

Regras:
- Não redesinhe a arquitetura congelada.
- Se identificar problema estrutural, pare e produza um
  ARCHITECTURE_CHANGE_REQUEST.md antes de mudar código.
- Trabalhe em PRs pequenos. Um PR por unidade lógica.
- Não faça commit nem push. Eu reviso, testo e empurro.
- Não altere Studio/ nem mídias pessoais.
- Rode antes de cada entrega:
    git diff --check
    python -m pytest tests
    bash tests/smoke_test.sh

Comece pela menor unidade possível: identificar o ponto de entrada
do Card Editor, mapear o contrato atual de cards e propor o primeiro
PR que conecta o Card Editor ao Studio sem quebrar raw_media nem
ready_video. Me entregue o diff conceitual antes de codar.


Isso força o Codex a:
- trabalhar em pedaços;
- não inventar arquitetura;
- produzir PRs revisáveis;
- não commitar sozinho.

---

## 3. Ordem prática de milestones

Não tente tudo de uma vez. Sugestão de fatiamento:

| Ordem | Milestone | Referência nos prompts |
|---|---|---|
| M1 | Card Editor conectado ao Studio (só abrir, ler, salvar) | Part3 §2 |
| M2 | Card de serviço com círculo perfeito + zoom | Part3 §4 |
| M3 | Balões redesenhados em grid/linhas com fade-out | Part3 §5 |
| M4 | Roteiro mestre otimizado + arquivo zerado | Part3 §6–8 |
| M5 | Modo automático sem IA | Part3 §9 |
| M6 | Vertical slice do core novo (do design da part1/part2) | VERTICAL_SLICE_PLAN.md |
| M7 | Media Intelligence mínimo | Architecture Freeze |
| M8 | Story Engine mínimo | Architecture Freeze |

Cada milestone = 1 a 3 PRs. Nunca mais que isso.

---

## 4. Regras de ouro

1. **Parts 1 e 2 não viram código direto.** Viram documentos. Sem isso, o Codex alucina arquitetura.
2. **Part 3 é a única executável de imediato.** Ela é operacional e concreta.
3. **Nunca mande os 3 prompts juntos no Codex.** Ele vai misturar design com execução e travar.
4. **Sempre branch, nunca main direto.** codex/* existe exatamente para isso.
5. **Codex não faz push.** Você revisa, testa e empurra. Isso já está nas regras dos prompts — respeite.
6. **Se o Codex quiser mexer em Studio/, pare.** Isso é regra inviolável nos três prompts.
7. **Um PR = uma responsabilidade.** Se um PR toca em 10 arquivos de 5 módulos, quebre antes de commitar.
8. **Antes de cada merge, rode os testes.** pytest, smoke_test.sh, git diff --check. Sem isso, a dívida se acumula invisível.

---

## 5. Se você tem pouco tempo/contexto, comece só com isto

Se quiser reduzir escopo para não travar, este é o caminho mais curto e útil agora:


bash
cd ~/FR-AutoEdite/FR_AUTOEDITE_4.0
git checkout main
git pull origin main
git checkout -b codex/card-editor-integration

# Cole apenas promptcodexpart3.txt no Codex com a instrução:
# "Execute somente este prompt. Não leia os outros dois ainda.
#  Trabalhe em PRs pequenos. Não commite."


Depois que part3 estiver integrada, testada e mergeada em main, aí sim você investe tempo na part1+part2 (design arquitetural), roda num chat separado, salva os documentos, e só então volta ao Codex para o vertical slice.

**Por quê:** part3 gera valor visível rápido (Card Editor funcionando). part1+part2 geram valor estrutural de médio prazo, mas só fazem sentido quando você já tem algo tangível para ancorar a discussão.

---

## 6. O que NÃO fazer

- ❌ Colar os 3 prompts no Codex em uma única mensagem.
- ❌ Rodar part1 e esperar código.
- ❌ Deixar o Codex commitar direto em main.
- ❌ Ignorar o ARCHITECTURE_FREEZE_V1.md depois de gerado — se ele mudar a cada PR, o projeto perde coerência.
- ❌ Rodar os prompts em paralelo em chats diferentes e depois tentar mesclar — as premissas vão divergir.
- ❌ Esperar que part1+part2 produzam algo "curto". Eles foram escritos para produzir documentos densos. Reserve tempo para ler.

---

## 7. Resumo em uma linha

**Rode part1 e part2 num chat de raciocínio para gerar os documentos de arquitetura; salve-os em docs/design/; depois use o Codex apenas com part3 e o vertical slice, em PRs pequenos, na branch codex/*, sem push automático.**

Se quiser, eu monto agora:
- o **texto exato** do primeiro comando para o Codex (o pacote inicial curto), ou
- um **checklist de aceite** para você validar cada PR que o Codex entregar antes de mergear.

A outra IA está direcionalmente correta, mas eu não seguiria o fluxo dela exatamente. Depois de revisar os três prompts e o ZIP do Card Editor, há uma arquitetura de execução melhor e mais segura.

O problema central é que vocês estão tentando usar três documentos com funções diferentes como se fossem três partes sequenciais do mesmo comando. Não são.

O part1 explicitamente proíbe implementação durante a resposta e manda primeiro conceber a arquitetura. Ao mesmo tempo, ele foi desenhado para terminar produzindo um plano de execução e um Prompt Operacional para o Codex. Portanto, dizer que ele é “apenas um tratado arquitetural” é incompleto.

O part2 é ainda mais claro: ele existe para testar a arquitetura da Parte I, gerar um Architecture Freeze e só então definir o contrato que o Codex deve executar. Ele ainda determina que IA e core sejam separados por contrato declarativo, que decisões passem por validação e que mudanças sejam reversíveis.

Já o part3 não é uma continuação arquitetural: ele é uma feature/migração concreta na FR AutoEdite 4.0 existente.

Minha decisão

Eu não enviaria Part 1 + Part 2 + Part 3 juntos para o Codex.

Mas também não seguiria exatamente a recomendação da outra IA de executar “Part 3 + vertical slice do Next” na mesma etapa.

Isso mistura dois projetos diferentes:

Trilha	Objetivo
FR AutoEdite 4.0	melhorar a aplicação que já funciona agora
FR AutoEdite Next	descobrir/reconstruir a arquitetura futura

A melhor estratégia é manter ambas, mas separadas.

1. Part 1 + Part 2 pertencem à FR AutoEdite Next

Part 1 estabelece algo muito importante:

a 4.0 é fonte de requisitos, não fonte obrigatória de arquitetura.

Isso está correto.

Part 2 reforça ainda mais essa abordagem ao separar:

Universal Media Core;
Domain Pack;
Brand Pack;
Content Strategy Pack.

Então essas duas partes não deveriam instruir diretamente o Codex a modificar a FR AutoEdite 4.0.

Devem produzir primeiro:

ARCHITECTURE_FREEZE_V1
SYSTEM_INVARIANTS
AI_CORE_CONTRACT
MEDIA_PROVENANCE_SPEC
DATA_MODEL
TIMELINE_MODEL
GRAPHICS_ENGINE_SPEC
VERTICAL_SLICE_PLAN
CODEX_EXECUTION_PLAN

Depois disso nasce o prompt operacional do FR AutoEdite Next.

2. Part 3 pertence à FR AutoEdite 4.0 atual

Aqui está a principal coisa que eu mudaria na recomendação recebida.

Part 3 pode ser executada agora, sem esperar toda a reconstrução Next.

Mas ela deve ser tratada como:

FR AutoEdite 4.0 — Feature/Bridge Implementation

e não como:

primeira implementação da arquitetura Next.

Essa distinção é essencial.

O que vocês aprenderem integrando:

Card Editor;
novo contrato de cards;
overlays;
geração limpa do roteiro;
manifest de proxies;
edição automática;

depois será usado como evidência real para Part 1/2.

Isso inclusive melhora a arquitetura futura.

3. Existe um erro arquitetural importante na Part 3 atual

Esta frase:

“O Card Editor deve ler e escrever o mesmo CARD_STYLE.json e o mesmo contrato de cards usado pelo Studio.”

eu mudaria.

Inspecionei o ZIP do FR_CARD_EDITOR_UNIVERSAL_v1.1.0.

Ele já possui contrato próprio:

schema = fr-card-editor/1.1

e API JavaScript:

FRCardEditor.getConfig()
FRCardEditor.applyConfig()
FRCardEditor.setField()
FRCardEditor.setLine()
FRCardEditor.exportPNG()
FRCardEditor.reset()

Isso é muito bom.

Portanto não devemos destruir essa independência fazendo o editor conhecer internamente toda a estrutura da AutoEdite.

A arquitetura correta é:

FR AUTOEDITE
     │
     │ CardDefinition / CardInstance
     ▼
CARD ADAPTER
     │
     │ fr-card-editor/1.1
     ▼
FR CARD EDITOR

E no sentido contrário:

FR CARD EDITOR
     │
     │ getConfig()
     ▼
CARD ADAPTER
     │
     │ normalização + validação
     ▼
PROJECT / TIMELINE

Isso cria uma Anti-Corruption Layer entre os dois sistemas.

4. Portanto o Card Editor não deve virar dependência acoplada do core

Eu mudaria:

“passa a ser o motor oficial de edição de cards”

para:

“passa a ser a implementação visual oficial do Card Editing Engine através de um contrato/adaptador estável.”

Parece uma diferença pequena, mas arquiteturalmente é enorme.

Futuramente você poderá ter:

CardEditingEngine
    ├── FRCardEditorAdapter
    ├── BatchCardGenerator
    ├── AIAdapter
    └── HeadlessRenderer

A UI atual não vira o banco nem o domínio.

5. O ZIP já facilita muito a integração

Há outro detalhe que torna a implementação mais simples do que o Part 3 pressupõe.

O pacote possui:

index.html
AUTOEDITE_MAP.json
README.md
assets/
FR_CARD_EDITOR_STANDALONE.html

Eu não utilizaria o FR_CARD_EDITOR_STANDALONE.html de ~28 MB como implementação principal dentro do Studio.

Ele é ótimo para portabilidade.

Para integração, eu usaria:

index.html
+
assets/
+
AUTOEDITE_MAP.json

porque reduz duplicação e peso.

O Codex deve decidir após auditar o frontend atual se a integração será:

iframe controlado

ou:

componente incorporado

ou:

rota/painel isolado

Mas não deve reescrever o editor inicialmente.

6. Há outra pequena inconsistência no Part 3

O Card Editor Universal permite:

circle
square
rounded
full

Isso é correto para um editor universal.

A Part 3 determina círculo obrigatório para card de serviço.

Também está correto.

A implementação deve ser:

IF card.family == SERVICE:
    centralMedia.shape = circle

e não:

ALL CARDS:
    centralMedia.shape = circle

Ou seja:

regra da família, não limitação do editor.

7. Eu dividiria a Part 3

Esse é o maior problema atual do prompt.

Part 3 contém simultaneamente:

integração de aplicação;
contratos de cards;
editor manual;
integração de IA;
imagem circular;
redesign dos balões;
novo Master Prompt;
regeneração limpa do Markdown;
verificação de proxies;
hashing;
modo automático;
análise local;
entregas sociais;
testes de regressão.

Isso é escopo demais para uma única execução do Codex.

O próprio Part 1 diz para trabalhar em PRs pequenos e reversíveis.

Portanto eu dividiria Part 3 em:

PART 3A — CARD / GRAPHICS INTEGRATION

PART 3B — AI EDIT CONTRACT + MASTER ROUTE

PART 3C — PROXY / MANIFEST / CLEAN PACKAGE

PART 3D — DETERMINISTIC AUTOEDIT

Isso é consideravelmente mais seguro.

8. Existe um problema ainda mais importante no Master Prompt atual

Você identificou corretamente que a IA está recebendo informação demais.

Mas eu iria além de simplesmente “encurtar Markdown”.

O problema não é Markdown longo.

O problema é que hoje aparentemente estamos pedindo a um LLM para simultaneamente:

entender projeto
+
entender vídeos
+
decidir narrativa
+
decidir cortes
+
decidir velocidade
+
escrever textos
+
escolher cards
+
posicionar balões
+
decidir transições
+
produzir contrato técnico

Isso aumenta brutalmente a superfície de erro.

A arquitetura melhor é:

SOURCE OF TRUTH
      ↓
COMPACT MEDIA MANIFEST
      ↓
AI EDIT REQUEST
      ↓
AI EDIT PLAN
      ↓
DETERMINISTIC VALIDATOR
      ↓
NORMALIZED EDIT PLAN
      ↓
AUTOEDITE

Part 2 já antecipa exatamente essa separação ao proibir a IA de alterar diretamente arquivos/timeline e exigir um DECLARATIVE EDIT INTENT.

9. Eu substituiria o “Roteiro Mestre” monolítico

O nome pode continuar na interface.

Mas internamente eu criaria três blocos:

CONTEXT
MANIFEST
TASK

E a IA devolveria:

EDIT_PLAN
CONTEXT

Informação realmente necessária:

project
objective
platform
duration
brand
services
strategy
MANIFEST

Mídia estruturada:

M001
duration
scenes
available_windows
description
quality
phase
TASK

Só as decisões que queremos dela:

select
trim
order
speed
card
bubble
transition
EDIT_PLAN

Resposta estruturada.

Isso é muito mais eficiente do que enviar um “dossiê explicativo”.

10. O Markdown pode continuar existindo

Mas como representação humana.

O correto seria:

Project DB / Manifest
       │
       ├──> AI_PACKAGE.md
       │
       └──> AI_PACKAGE.json

Ou ainda:

AI_PACKAGE.md

contendo uma seção estruturada compacta.

O que não recomendo é:

Markdown = banco de dados.

Part 2 também já corrige esse risco ao defender contratos e validação.

11. A exigência “arquivo zerado” está muito boa

Essa parte da Part 3 eu manteria praticamente integralmente.

Mas tecnicamente o botão não deveria “limpar um arquivo antigo”.

Deveria fazer:

GenerateAIRequest()

criando o objeto do zero em memória a partir da source of truth:

CURRENT PROJECT
+
CURRENT MANIFEST
+
CURRENT PROXIES
+
CURRENT SETTINGS

e então:

serialize
→
temporary file
→
atomic replace

Ou seja:

não reciclar o documento anterior.

12. Proxies: concordo com a intenção, mudaria a implementação

A exigência de que os proxies cubram 100% do original é correta.

Mas não compararia apenas hash, porque:

original ≠ proxy

obviamente terão hashes diferentes.

Precisamos de:

source_asset_id
source_hash
proxy_hash
source_duration
proxy_duration
frame/time coverage
generation_parameters

Exemplo:

M001
source_duration: 634.723
proxy_duration: 634.723
coverage: 0.000 → 634.723
status: complete

Então verificamos tolerância temporal.

13. Eu retiraria o limite fixo de 150 MB do core

A regra:

“o lote final continua abaixo de 150 MB”

pode ser necessária hoje por alguma interface específica.

Mas não deveria ser arquitetura.

Transformaria em:

ai_package.max_bytes

configurável por provider/exporter.

Exemplo:

OpenAI Provider
Claude Provider
Manual ZIP Export
Local Model

Cada um pode possuir limites diferentes.

14. “Modo automático sem IA” é uma excelente decisão

Essa talvez seja uma das melhores partes da Part 3.

Ela determina que o sistema consiga montar conteúdo com:

regras determinísticas;
FFmpeg;
análise local;
manifesto;
style pack.

Eu manteria.

Mas o chamaria internamente de:

DETERMINISTIC AUTOEDIT

e depois teríamos:

AI ASSISTED AUTOEDIT

Os dois devem produzir o mesmo EditPlan.

Essa arquitetura fica:

MANUAL
     ┐
DETERMINISTIC AUTO
     ├──> EDIT PLAN → VALIDATOR → TIMELINE
AI ASSISTED AUTO
     ┘

Isso é muito mais forte.

15. Existe uma contradição que precisa ser corrigida antes do Codex

Part 3 diz:

integrar o Card Editor dentro do Studio.

e depois:

“Não altere a pasta Studio/”.

Isso pode ser interpretado de duas formas diferentes.

Se Studio/ contém dados gerados pelos projetos, não devemos alterar diretamente.

Se Studio/ contém source code da interface, a regra impossibilitaria a implementação.

Eu substituiria por:

Não modificar, apagar, versionar ou usar como fixture dados pessoais/projetos gerados dentro de Studio/. Alterações no código-fonte responsável pela interface Studio são permitidas quando necessárias e devem utilizar dados mockados nos testes.

Isso elimina a ambiguidade.

16. Também não fixaria comandos de teste sem verificar o repositório

Part 3 manda executar:

python -m pytest tests
bash tests/smoke_test.sh

Pode ser que ambos existam.

Mas o Codex deve primeiro auditar o repo.

Se smoke_test.sh não existir, não deve inventar que o projeto está quebrado.

A regra correta:

1. descobrir suíte existente;
2. rodar suíte existente;
3. adicionar testes necessários;
4. rodar testes novos;
5. git diff --check.
Melhor opção atual

Eu utilizaria duas trilhas paralelas, porém sem misturá-las:

                    FR AUTOEDITE
                         │
             ┌───────────┴───────────┐
             │                       │
          TRACK A                  TRACK B
        CURRENT 4.0                  NEXT
             │                       │
         Part 3A-D              Part 1 → Part 2
             │                       │
     melhorias concretas       Architecture Freeze
             │                       │
     aprendizado real          Codex Execution Plan
             │                       │
             └───────────┬───────────┘
                         │
                  MIGRATION PLAN
Track A — Agora

Implementar na 4.0:

Card Editor Bridge
Card Timeline Integration
Card IA Editing
New Bubbles
Compact AI Contract
Fresh AI Package
Proxy Integrity
Deterministic AutoEdit
Track B — Arquitetura futura

Rodar:

Part 1
   ↓
resposta Part 1
   ↓
Part 2
   ↓
Architecture Freeze
   ↓
Prompt Operacional Codex Next

Eu rodaria Part 1 e Part 2 no mesmo chat de raciocínio, não em chats separados, salvo se a resposta da Parte I for anexada integralmente ao segundo.

Part 2 foi explicitamente criada para revisar a arquitetura produzida pela Part 1.

Novo chat desnecessariamente perde estado e aumenta possibilidade de inconsistência.

O que eu NÃO faria

Não mandaria isto:

Codex leia:
promptcodexpart1
promptcodexpart2
promptcodexpart3

Execute tudo.

Porque existe conflito semântico:

Part 1:
NÃO IMPLEMENTE

Part 2:
CONGELE ANTES DE IMPLEMENTAR

Part 3:
EXECUTE A INTEGRAÇÃO

Um modelo competente pode resolver isso.

Mas estamos criando ambiguidade gratuitamente.

O prompt que eu realmente daria ao Codex agora

Eu substituiria o comando sugerido pela outra IA por este:

Prompt Operacional Inicial — FR AutoEdite 4.0 / Card Editor Integration

Você está trabalhando no repositório:

/home/romeu/FR-AutoEdite/FR_AUTOEDITE_4.0

OBJETIVO DESTA SESSÃO

Esta sessão NÃO implementará ainda a reconstrução completa FR AutoEdite Next.

Os arquivos:

promptcodexpart1.txt
promptcodexpart2.txt

são documentos de arquitetura e requisitos da futura geração. Leia-os apenas como contexto, invariantes e direção arquitetural. Não tente executar literalmente suas etapas de reconcepção nesta sessão.

O trabalho executável atual é a integração descrita em:

promptcodexpart3.txt

e no aplicativo:

FR_CARD_EDITOR_UNIVERSAL_v1.1.0/

Entretanto, antes de alterar código, audite o repositório atual e o Card Editor real.

FASE 0 — AUDITORIA OBRIGATÓRIA

Identifique:

stack atual da FR AutoEdite;
ponto de entrada do Studio;
representação atual de cards;
uso atual de CARD_STYLE.json;
representação atual da timeline/overlays;
geração atual do roteiro mestre para IA;
geração e validação atual dos proxies;
implementação dos modos raw_media e ready_video;
suíte real de testes existente;
estrutura e API do FR_CARD_EDITOR_UNIVERSAL_v1.1.0.

Leia obrigatoriamente:

FR_CARD_EDITOR_UNIVERSAL_v1.1.0/README.md
FR_CARD_EDITOR_UNIVERSAL_v1.1.0/AUTOEDITE_MAP.json
FR_CARD_EDITOR_UNIVERSAL_v1.1.0/index.html

Não use FR_CARD_EDITOR_STANDALONE.html como primeira opção de integração enquanto index.html + assets puderem ser utilizados de forma modular.

REGRA ARQUITETURAL PRINCIPAL

Não acople diretamente o FR Card Editor à estrutura interna da AutoEdite.

Implemente uma fronteira semelhante a:

AutoEdite Card Model ↔ CardEditorAdapter ↔ fr-card-editor/1.1

O Card Editor mantém seu contrato próprio.

O Adapter é responsável por:

mapear estado AutoEdite → Card Editor;
mapear Card Editor → AutoEdite;
validar IDs;
normalizar estilos;
persistir alterações;
invalidar previews;
atualizar timeline quando aplicável.

Não duplique dentro da AutoEdite a lógica visual que já existe no Card Editor.

CARD DE SERVIÇO

A obrigatoriedade de recorte circular é regra da família service, não limitação universal do editor.

Para cards de serviço:

central_media.shape = circle;
proporção 1:1 antes da máscara;
nunca deformar;
zoom e ponto focal editáveis;
IA pode sugerir asset;
usuário pode substituir;
asset deve existir;
nunca inventar imagem.

Outras famílias continuam podendo utilizar formatos suportados pelo Card Editor quando o Style/Brand Pack permitir.

EXECUÇÃO EM MILESTONES

Não implemente toda a Parte 3 em uma única alteração.

M1 — CARD EDITOR BRIDGE

Entregar:

abertura do Card Editor pelo Studio;
carregamento do projeto atual;
adapter entre contratos;
edição manual;
salvar estado;
atualizar preview;
persistência;
regressão de raw_media e ready_video.

Nenhuma IA é necessária nesta milestone.

M2 — CARD NA TIMELINE

Adicionar:

criação de CardInstance;
start_sec;
end_sec ou duration_sec;
edição temporal;
preview;
remoção;
troca de template;
renderização.
M3 — SERVICE CARD + CENTRAL MEDIA

Adicionar:

regra circular;
zoom;
focal point;
substituição de asset;
fallback do Brand Pack;
testes contra deformação.
M4 — BALLOON / CALLOUT ENGINE

Redesenhar os balões conforme a Parte 3:

grid e linhas minimalistas;
final das linhas em transparência;
fundo não opaco;
tamanho orientado pelo conteúdo;
padding consistente;
safe area;
collision avoidance;
integração com Brand Pack;
animação configurável.

Não hardcode geometry específica quando puder ser representada por tokens/templates.

M5 — AI CARD EDITING

A IA não altera diretamente arquivos nem timeline.

Fluxo obrigatório:

PROJECT CONTEXT
→ AI CARD INTENT
→ VALIDATOR
→ DIFF
→ APPLY

A IA pode propor:

texto;
família;
serviço;
card;
imagem central;
posicionamento;
animação;
intervalo temporal.

Porém só pode referenciar:

IDs existentes;
assets existentes;
intervalos válidos.
M6 — AI EDIT PACKAGE V2

Não apenas “encurte o Markdown atual”.

Reconstrua a geração como pacote novo produzido da source of truth atual.

Separar conceitualmente:

CONTEXT
MEDIA_MANIFEST
EDIT_TASK
EDIT_SCHEMA

A saída da IA deverá ser um EDIT_PLAN estruturado.

O Markdown é uma representação humana/intercambiável; não deve ser o banco principal.

Toda geração deve criar o pacote do zero em memória.

Não reaproveitar texto ou decisões de gerações anteriores.

Mesma source of truth + mesmas configurações devem produzir pacote equivalente/determinístico.

M7 — PROXY INTEGRITY

Para cada proxy registrar relação com o original:

source_asset_id;
source_hash;
proxy_hash;
source_duration;
proxy_duration;
coverage_start;
coverage_end;
parâmetros de geração.

Validar que a cobertura temporal representa integralmente o original dentro de tolerância técnica documentada.

Hash do proxy não deve ser comparado diretamente ao hash do original como critério de igualdade.

O limite de pacote para IA deve ser configurável por provider/exporter, não hardcoded no core.

M8 — DETERMINISTIC AUTOEDIT

Criar um caminho sem IA externa que produza o mesmo contrato EDIT_PLAN usado pelos outros modos.

Arquitetura desejada:

MANUAL
DETERMINISTIC_AUTO
AI_ASSISTED

↓ todos produzem ↓

EDIT_PLAN
→ VALIDATOR
→ TIMELINE
→ RENDER

Use regras determinísticas e análise local quando disponível.

SOURCE OF TRUTH

Nenhum documento gerado para IA deve tornar-se source of truth.

A source of truth deve continuar sendo o estado estruturado do projeto.

AI_PACKAGE.md é artefato derivado e regenerável.

STUDIO/

Não interpretar “não alterar Studio/” como proibição de implementar funcionalidades da interface.

A regra significa:

não versionar mídia pessoal;
não usar projetos pessoais como fixtures;
não apagar ou modificar manualmente dados produzidos pelo usuário;
não adicionar arquivos de projeto reais ao Git.

Código-fonte responsável pelo Studio pode e deve ser alterado quando necessário para implementar a funcionalidade.

Testes devem utilizar fixtures/mocks dedicados.

TESTES

Primeiro descubra a suíte existente do projeto.

Não presuma a existência de um comando ou script.

Execute:

testes existentes aplicáveis;
novos testes unitários;
testes de integração;
regressão dos fluxos atuais;
git diff --check.

Se existir pytest, utilize-o.

Se existir tests/smoke_test.sh, execute-o.

Não crie falha artificial porque um comando citado em prompt antigo não existe.

GIT

Antes de alterar:

registre branch;
registre HEAD;
registre git status.

Não modifique main silenciosamente.

Trabalhe na branch atual se ela já for dedicada a esta implementação; caso contrário crie uma branch de trabalho apropriada.

Não faça push, merge ou deploy nesta sessão.

Não faça commit automaticamente salvo se houver instrução explícita posterior.

REGRA DE ESCOPO

Implemente uma milestone por vez.

Ao finalizar uma milestone:

liste arquivos alterados;
explique as decisões;
apresente testes executados;
apresente resultados;
apresente limitações;
indique a próxima milestone.

Não comece automaticamente a milestone seguinte se a atual apresentar regressões.

PRIMEIRA AÇÃO

Faça agora apenas a auditoria da FASE 0.

Em seguida apresente:

mapa da arquitetura atual relevante;
pontos de integração encontrados;
contrato atual dos cards;
diferenças para fr-card-editor/1.1;
estratégia de Adapter recomendada;
arquivos que M1 precisará alterar;
riscos;
testes existentes que protegerão a integração.

Depois dessa auditoria, prossiga diretamente para M1 se não houver bloqueio estrutural real.

Minha recomendação final

Use esse prompt operacional para o trabalho imediato da 4.0.

Mantenha os três arquivos na raiz, mas mude a função deles:

promptcodexpart1.txt
= visão e arquitetura NEXT

promptcodexpart2.txt
= stress test / freeze NEXT

promptcodexpart3.txt
= requisitos funcionais da evolução 4.0

PROMPT OPERACIONAL acima
= instrução que o Codex realmente executa agora

Depois, em uma sessão de raciocínio separada:

Part 1
↓
resposta
↓
Part 2
↓
Architecture Freeze
↓
Prompt Operacional NEXT

E só então começamos a migração estrutural.

Isso preserva as melhorias que você quer agora sem obrigar a FR AutoEdite 4.0 a se tornar prematuramente a arquitetura definitiva da próxima geração.
