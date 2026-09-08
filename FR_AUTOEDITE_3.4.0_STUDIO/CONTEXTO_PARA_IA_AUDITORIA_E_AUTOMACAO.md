# CONTEXTO MESTRE PARA IA — AUDITORIA, CORREÇÃO E AUTOMAÇÃO

## 0. Instrução de uso

Este documento acompanha o código-fonte completo do **FR AutoEdite Studio
3.4.0**. A IA que receber este arquivo deve agir como engenheira de software,
testes, UX e pós-produção. Ela deve primeiro compreender e auditar a aplicação;
depois corrigir erros reproduzidos; por fim automatizar tarefas seguras que
reduzam trabalho manual sem retirar a possibilidade de revisão humana.

Não presuma que uma alteração está correta apenas porque o código compila.
Toda correção deve ser reproduzida, testada e documentada.

---

## 1. O que é o FR AutoEdite

O FR AutoEdite é um miniestúdio local de pós-produção da **Franco Romeu — Arte
& Engenharia**. Ele transforma um ZIP com fotos e vídeos de obras, projetos,
serviços e processos em:

- filme institucional com identidade Franco Romeu;
- filme limpo, sem cards institucionais;
- Reels configuráveis, normalmente de 30, 60 e 90 segundos;
- Stories, capas e carrossel;
- cards de intro, etapas, serviços e encerramento;
- proxies leves para revisão;
- timeline JSON editável;
- lotes independentes para revisão por IA, sempre abaixo de 150 MB;
- relatórios de auditoria e mapas claros de arquivos.

O fluxo principal funciona gratuitamente e offline. Integrações com OpenAI,
Anthropic, Ollama ou Google Drive são opcionais e nunca podem bloquear o modo
local.

Fluxo profissional esperado:

```text
ZIP + contexto
→ extração segura
→ manifesto e análise local
→ proxies, miniaturas e prancha
→ plano automático
→ prévia de cards e timeline
→ revisão humana ou por IA
→ rascunho por proxies
→ ajustes
→ master pelos originais
→ auditoria
→ publicação ou envio

### Novidades da Central da IA 3.4.0

O único arquivo que a IA altera é o Markdown em `_ENVIAR_IA/` marcado
**EDITAR E DEVOLVER**. Ele contém o prompt operacional e o contrato v2. A IA
deve retornar o arquivo completo, preservando o comentário de escopo e usando
somente `media_id` do manifesto. O Studio valida antes de aplicar e mostra
contagens de cortes, cards, frames, slides, duração e avisos de legibilidade.

As decisões podem ser guardadas em `_ROTEIROS/` e cada render congela sua cópia
em `_RENDERIZACOES/`; `entrega/` é somente a versão corrente. O botão **Zerar
definições e manter mídias** arquiva as escolhas e limpa contexto/planos sem
apagar ZIP, Takeout, originais, proxies ou manifesto.
```

---

## 2. Usuário e princípio de usabilidade

O operador pode não conhecer programação, terminal, JSON, FFmpeg ou edição de
vídeo. Portanto:

- mensagens de erro devem explicar **o que ocorreu, onde e como resolver**;
- caminhos de arquivos devem ser visíveis e copiáveis;
- opções relacionadas devem ficar na mesma página do projeto;
- tarefas automáticas devem ter valores seguros por padrão;
- tarefas não automatizáveis devem ter passo a passo curto e verificável;
- nunca exija que o usuário edite JSON para uma operação comum;
- recursos avançados podem existir, mas não devem poluir o fluxo básico.

---

## 3. Identidade Franco Romeu que deve ser preservada

### Paleta consolidada

- Verde Petróleo Profundo: `#0A2F26`, `#123F34`, `#031812`
- Laranja: `#FF6B00`, `#FF7A00`, `#FC7016`
- Ouro: `#F6A700`
- Osso: `#E6D6B5`
- Borda Petróleo: `#1A6069`
- Preto: `#0A0A0A`

### Tipografia

- Títulos e cards: Stardos Stencil
- Corpo editorial: Rokkitt
- Informação técnica: Share Tech Mono

### Linguagem

- técnica, clara, autoral e verificável;
- “luxo silencioso” e “engenharia inteligente”;
- verdade material, processo, execução e resultado;
- não inventar depoimentos, números, garantias, escassez ou fatos da obra.

### Marca

O logotipo oficial já está em `assets/franco-romeu-logo.png`. Não redesenhe,
deforme, espelhe, recorte de forma destrutiva ou substitua por uma imitação.

---

## 4. Arquitetura do pacote

| Caminho | Responsabilidade |
|---|---|
| `fr-autoedite` | Launcher Bash estável |
| `app/fr_autoedite.py` | CLI, preparação, plano, cards, render, social, auditoria e nuvem |
| `app/studio.py` | Servidor HTTP local e operações do Studio |
| `app/local_analysis.py` | Qualidade, cenas, duplicatas e estabilidade local |
| `app/copilot.py` | Copiloto opcional, credenciais e fallback |
| `assets/studio/index.html` | Interface única do projeto |
| `templates/questionario_base.json` | Configuração padrão e compatibilidade |
| `templates/EDIT_PLAN_SCHEMA.json` | Contrato estrutural do plano |
| `templates/card_style.json` | Design padrão dos cards |
| `templates/fr_brand_profile.json` | Identidade e contatos da marca |
| `templates/service_catalog.json` | Nove serviços e símbolos visuais |
| `tests/card_circle_test.py` | Regressão geométrica da máscara circular de serviço |
| `tests/studio_http_test.py` | Regressões HTTP, IA, Takeout, cards e mensagens de erro |
| `tests/smoke_test.sh` | Teste integral com mídias sintéticas |
| `install.sh` | Instalação local sem instalar pacotes do sistema |
| `INSTALAR_EM_OUTRO_COMPUTADOR.sh` | Instalação portátil guiada |
| `ATUALIZAR_CORRECAO_CARDS.sh` | Atualização com encerramento do painel antigo |

### Estrutura de um projeto criado pelo Studio

```text
NOME-DO-PROJETO/
├── _ENTRADA/                 ZIP, contexto, intro/outro e roteiro respondido
├── _EDITAR/                  compatibilidade e ajustes humanos locais
├── _ENVIAR_IA/               única central: o que editar, ler e enviar
├── _ENVIAR_CHATGPT/          compatibilidade com projetos anteriores
├── _TAKEOUT/                 exportação original e relatório de datas
├── _HISTORICO/               backups antes de substituições
├── originais/                extração preservada
├── originais_organizados/    referências organizadas por fase
├── proxies/                  mídias leves para revisão
├── miniaturas/               imagens de contato
├── selects/                  seleção técnica reversível
├── cards_editaveis/          PNGs de prévia
├── pacote_chatgpt/           lotes independentes abaixo de 150 MB
├── social/                   Reels, Stories, capas e carrossel
├── entrega/                  masters e relatórios
├── QUESTIONARIO_RESPONDIDO.json
├── MANIFESTO_MEDIA.json
├── EDIT_PLAN.json
├── CARD_STYLE.json
└── RELATORIO_AUDITORIA.md
```

---

## 5. Funcionalidades já implementadas

- modos automático, cronológico, alfabético e aleatório com seed;
- extração protegida contra caminhos maliciosos;
- proxies, miniaturas, prancha e manifesto;
- organização por fases sem alterar os originais;
- marcação reversível de duplicatas e qualidade;
- cenas virtuais para vídeos longos;
- cards de intro, fase, serviço e outro;
- nove categorias de serviço;
- símbolos de serviço recortados com proporção preservada e círculo alfa real;
- preset `site_fr_luxo`, layout `site_editorial` e regra cromática 60/20/20;
- logo fixa, balão, contatos e ícones;
- intro/outro externos em foto ou vídeo;
- 29 transições selecionáveis via FFmpeg;
- Ken Burns, LUT, estabilização, speed ramp, time-lapse editorial, ducking e SFX;
- qualidade de rascunho até 4K ou dimensão do original;
- Reels separados com cobertura de início, meio distribuído e fim;
- editor visual de timeline e editor próprio para cada Reel;
- Roteiro Mestre Markdown exportável/importável para qualquer IA;
- página única `_ENVIAR_IA/`, com o papel de cada arquivo explícito no nome;
- Google Takeout + JSON com recuperação de datas, ZIP normalizado e relatório;
- lotes ZIP independentes abaixo de 150 MB com CRC;
- auditoria técnica e relatórios;
- Google Drive opcional via `rclone`;
- Copiloto opcional com fallback para o modo local.

---

## 6. Invariantes — regras que nenhuma correção pode quebrar

1. **Nunca apagar, mover destrutivamente ou regravar os originais.**
2. Toda substituição de plano, configuração ou estilo deve criar backup quando
   houver risco de perda de trabalho.
3. O modo local precisa continuar funcional sem internet, conta ou API.
4. Copiloto e serviços pagos permanecem desligados por padrão.
5. Nenhuma chave, token, senha ou credencial pode entrar no ZIP, log, Git ou
   projeto do cliente.
6. Cada lote destinado ao ChatGPT deve ficar abaixo de 150 MB após compactar.
7. Reels devem representar início, meio e resultado final, salvo escolha manual
   explícita e validada.
8. A master deve preferir originais; proxies servem para revisão e rascunho.
9. Não alterar assinatura dos comandos V2 existentes sem migração compatível.
10. Não enfraquecer, remover, ignorar ou modificar testes apenas para fazê-los
    passar.
11. Não inventar compreensão visual que a heurística local não possui.
12. Uma auditoria técnica não substitui assistir integralmente às entregas.
13. O Google Takeout original e seus sidecars JSON nunca podem ser
    sobrescritos; o resultado deve ser um novo ZIP auditável.
14. Fotos de serviço não podem ser esticadas para preencher o medalhão; o
    recorte deve preservar proporção e produzir círculo matematicamente exato.

---

## 7. Regressões históricas que precisam permanecer cobertas

### Geração de cards antes da preparação

O botão de prévia falhava quando `EDIT_PLAN.json` ainda não existia. Desde a
3.2.1, `CARD_PREVIEW_PLAN.json` é criado para prévias sem fingir ser a timeline
principal. Audite os dois estados:

- projeto recém-criado, sem ZIP preparado;
- projeto preparado, com `EDIT_PLAN.json` real.

### Painel antigo continuando aberto

Uma instalação anterior podia continuar ocupando a porta e servindo HTML
antigo. Desde a 3.2.2:

- o atualizador encerra somente processos reconhecidos do Studio;
- a interface mostra versão visível;
- o HTML usa cabeçalhos contra cache;
- uma porta livre é escolhida se a padrão estiver ocupada.

### `CARD_STYLE.json` incompatível

Um estilo antigo, fonte ausente ou cor inválida não deve impedir a prévia. O
arquivo incompatível deve ser movido para `_HISTORICO/` e reconstruído a partir
das escolhas atuais. A recuperação deve ser informada no log.

### Backups com nomes repetidos

Replanejamentos rápidos já colidiram por usarem precisão de apenas um segundo.
Backups devem continuar usando microssegundos ou identificador igualmente
único.

### Roteiro Mestre em projeto novo

O botão **Gerar Markdown** já falhou por abrir um caminho legado antes de o
backend terminar a preparação. Desde a 3.3.0, o frontend usa o caminho real
devolvido pelo estado do projeto e só habilita a abertura quando o arquivo
existe. Audite projeto vazio, projeto apenas com ZIP e projeto preparado.

### Símbolo de serviço oval

Imagens de tamanhos diferentes eram redimensionadas diretamente para o
medalhão e podiam ficar ovais. Desde a 3.3.0, o renderer usa corte central em
quadrado, preserva a proporção e multiplica o canal alfa por uma máscara
circular exata. Execute `python3 tests/card_circle_test.py` e também inspecione
uma prévia visual.

### Google Takeout e datas

Sidecars podem usar nomes diferentes e nem toda mídia aceita os mesmos campos
EXIF. A sequência obrigatória é: localizar JSON correspondente, ler
`photoTakenTime`/`creationTime`, tentar ExifTool, tentar remux de vídeo, ajustar
mtime/data do ZIP e registrar o método usado. Falha de uma mídia não deve
eliminar a mídia nem interromper todo o lote.

---

## 8. Protocolo obrigatório de auditoria

Execute na raiz do código:

```bash
./fr-autoedite --versao
bash -n install.sh ATUALIZAR_CORRECAO_CARDS.sh INSTALAR_EM_OUTRO_COMPUTADOR.sh
python3 -m py_compile app/fr_autoedite.py app/studio.py app/local_analysis.py app/copilot.py
python3 tests/card_circle_test.py
python3 tests/studio_http_test.py
bash tests/smoke_test.sh
```

Também verifique:

1. todos os JSONs de `templates/` carregam sem erro;
2. `EDIT_PLAN_SCHEMA.json` permanece compatível com planos existentes;
3. não existem credenciais ou padrões de chave no pacote;
4. o ZIP final passa em `unzip -t`;
5. os scripts executáveis preservam permissão de execução;
6. a interface e o backend anunciam a mesma versão;
7. o botão de cards funciona antes e depois da preparação;
8. um `CARD_STYLE.json` inválido é preservado e recuperado;
9. erro de tarefa chega à interface com causa legível;
10. porta ocupada abre uma nova instância em porta livre;
11. lotes passam no CRC e cada um fica abaixo de 150 MB;
12. início e fim permanecem presentes nos planos de Reels;
13. nenhum teste utiliza fotos, vídeos ou credenciais pessoais;
14. a instalação isolada não modifica a instalação real do auditor.
15. a central `_ENVIAR_IA/` aponta para um único Markdown editável existente;
16. o teste Takeout preserva o ZIP original e recupera a data sintética;
17. time-lapse só é aplicado a vídeo, respeita 1.25x–30x e não extrapola a
    duração-fonte;
18. o canal alfa dos símbolos de serviço tem largura e altura iguais.

Para testar a instalação em isolamento, defina diretórios XDG temporários em
vez de reutilizar a instalação pessoal. Não altere `HOME`.

---

## 9. Como corrigir um erro corretamente

1. Reproduza o erro com o menor caso possível.
2. Registre o comportamento observado e o esperado.
3. Identifique a causa raiz, não apenas a mensagem final.
4. Crie um teste que falhe antes da correção.
5. Faça a menor alteração segura capaz de resolver a causa.
6. Execute teste focal, teste HTTP e smoke test integral.
7. Inspecione visualmente cards ou vídeos quando a alteração for visual.
8. Atualize versão e changelog quando houver mudança entregue ao usuário.
9. Empacote sem `__pycache__`, `.pyc`, credenciais ou mídias pessoais.
10. Entregue um ZIP novo com instruções claras de migração e rollback.

Se o erro não puder ser reproduzido, melhore observabilidade e peça o log
completo. Não invente uma causa.

---

## 10. Automação permitida e desejável

Priorize automações reversíveis:

- diagnóstico automático de dependências e versão;
- mensagens de erro orientadas à solução;
- autorreparo com backup;
- validação automática de JSON, caminhos, mídias, codecs e fontes;
- retomada de tarefas interrompidas;
- criação automática de proxies e rascunhos;
- seleção local por qualidade, cronologia e cobertura narrativa;
- seleção explícita e reversível de trechos para time-lapse editorial;
- recuperação de datas do Google Takeout com relatório por arquivo;
- divisão real de lotes e proxies grandes;
- geração de relatórios e mapa de arquivos;
- presets seguros para leigos;
- testes sintéticos que não dependam de dados pessoais;
- exportação opcional após confirmação explícita.

Automação não autorizada:

- publicar, enviar, apagar ou sobrescrever arquivos externos sem confirmação;
- ativar API paga automaticamente;
- armazenar credenciais em texto puro;
- decidir fatos da obra sem evidência;
- renderizar master como aprovada sem revisão;
- apagar duplicatas em vez de apenas marcá-las;
- substituir o logo oficial por arte gerada.

---

## 11. Melhorias que a IA pode propor após a auditoria

- testes unitários adicionais para alocação de duração e transições;
- validação de capacidade real dos filtros FFmpeg antes do render;
- modo de diagnóstico exportável em um único ZIP sem dados sensíveis;
- preview em vídeo dos cards e transições antes da master;
- comparação automática do design dos cards com a proporção cromática 60/20/20;
- fila persistente de jobs com retomada após reinício do Studio;
- verificação visual local opcional por modelo aberto, sem tornar isso requisito;
- comparação lado a lado entre rascunho anterior e atual;
- acessibilidade do painel, navegação por teclado e textos de ajuda contextuais;
- instalador adicional para outras distribuições, desde que testado em ambiente
  correspondente;
- assinatura e checksum de releases.

Não implemente uma melhoria apenas porque parece sofisticada. Demonstre valor,
custo, risco, compatibilidade e teste de aceite.

---

## 12. Formato esperado da resposta da IA auditora

A IA deve devolver:

1. **Resumo executivo** — estado real, versão e resultado dos testes;
2. **Falhas reproduzidas** — evidência, causa raiz e gravidade;
3. **Correções aplicadas** — arquivos e comportamento alterado;
4. **Automações adicionadas** — benefício, limites e como desligar;
5. **Testes executados** — comando, resultado e duração aproximada;
6. **Riscos restantes** — sem esconder limitações;
7. **Arquivos entregues** — ZIP instalável, changelog e checksums;
8. **Passo a passo para leigo** — instalar, testar, usar e reverter;
9. **Itens não alterados** — para demonstrar preservação de escopo.

Use marcações `APROVADO`, `CORRIGIDO`, `PENDENTE` e `BLOQUEADO`, sempre com
uma justificativa factual.

---

## 13. Prompt pronto para enviar junto deste arquivo

```text
Você recebeu o código completo do FR AutoEdite Studio e o arquivo
CONTEXTO_PARA_IA_AUDITORIA_E_AUTOMACAO.md.

Leia primeiro o contexto integralmente. Depois audite a aplicação seguindo o
protocolo obrigatório, sem apagar originais, sem inserir credenciais, sem
ativar APIs pagas e sem enfraquecer testes. Reproduza cada erro antes de
corrigi-lo. Automatize apenas tarefas reversíveis e seguras, criando backups e
mensagens compreensíveis para usuários leigos.

Ao terminar, execute os testes focal, HTTP e smoke integral. Entregue um novo
ZIP instalável, changelog, resultado dos testes, riscos restantes e passo a
passo de instalação. Se algo não puder ser confirmado, marque como PENDENTE em
vez de inventar sucesso.
```

---

## 14. Critério final de aprovação

A aplicação só pode ser declarada pronta quando:

- instalação portátil foi validada em ambiente isolado compatível;
- versão da CLI, servidor e interface coincide;
- teste HTTP e smoke integral passam sem mascarar falhas;
- cards funcionam em projeto vazio e preparado;
- símbolos de serviço permanecem circulares em fontes quadradas e retangulares;
- Roteiro Mestre abre pelo caminho canônico `_ENVIAR_IA/`;
- importação Takeout preserva o original e documenta datas não recuperadas;
- time-lapse renderiza com duração e velocidade consistentes;
- mídias originais permanecem intactas;
- lotes respeitam o limite;
- nenhum segredo ou mídia pessoal entrou no pacote;
- o usuário recebe instruções suficientes para instalar e reverter;
- limitações reais são declaradas.

Se qualquer item falhar, a entrega deve ser marcada como **PENDENTE**.
