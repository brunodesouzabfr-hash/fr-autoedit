# FR AutoEdite 4.6 — AI Director V3

## Objetivo

A etapa **05 · Enviar à IA** passa a ter como modo padrão uma direção autônoma editorialmente virgem. O usuário prepara/importa as mídias, pode excluir manualmente arquivos impróprios por `excluded_from_auto_edit`, escreve o contexto factual e gera o pacote. O pacote não usa `EDIT_PLAN`, `CARD_STATE_V2`, previews, ordem manual, efeitos ou respostas anteriores como decisão editorial.

A IA recebe o universo factual e executável, analisa os proxies elegíveis e devolve um JSON V3. A aplicação valida localmente a resposta antes de alterar o projeto.

## Princípio de estado zero

Entram no snapshot V3:

- contexto factual escrito pelo usuário;
- identidade factual do projeto;
- modo técnico de entrada (`raw_media` ou `ready_video`);
- todos os proxies elegíveis e seus IDs canônicos;
- lista das mídias excluídas pelo filtro humano, sem enviar seus proxies;
- catálogo fechado de serviços e capacidades suportadas;
- template estrutural executável, explicitamente marcado como fallback técnico e não como decisão anterior;
- schema e regras da resposta.

Não entram como fonte editorial:

- `EDIT_PLAN.json` e derivados;
- `CARD_STATE_V2.json` e previews;
- cards previamente escolhidos;
- ordem, cortes, efeitos, transições ou velocidades manuais anteriores;
- respostas anteriores da IA;
- planos sociais anteriores.

## Filtro humano preservado

`excluded_from_auto_edit=true` continua sendo uma decisão humana pré-IA. A mídia aparece no manifesto compacto como inelegível para auditoria, mas seu proxy não é incluído nos lotes. A IA não pode referenciá-la.

## Arquivos determinísticos do V3

Cada lote carrega metadados pequenos e determinísticos:

- `PROMPT_MESTRE_AUTONOMO.md`
- `FACTS.json`
- `MEDIA_MANIFEST.json`
- `CAPABILITIES.json`
- `DIRECTOR_TASK.json`
- `DIRECTOR_TEMPLATE.json`
- `RESPONSE_SCHEMA.json`
- `PACKAGE_DESCRIPTOR.json`

Os proxies elegíveis são adicionados aos lotes conforme o limite configurado. Arquivos grandes podem ser divididos tecnicamente para transporte sem decisão editorial de descarte. Fontes tipográficas binárias não são anexadas; somente seus nomes/capacidades são publicados.

## Liberdade da IA e universo fechado

A IA pode decidir, quando suportado pelo contrato:

- `use` ou `discard` para cada mídia elegível;
- ordem, janelas de corte e duração;
- velocidade, time-lapse, estabilização;
- transições e fades;
- narrativa e retenção;
- cards comuns, de serviço, abertura, etapa, detalhe e encerramento;
- quantidade e posicionamento dos cards;
- mídia central existente, zoom e ponto focal;
- overlays, balões, legendas e callouts;
- filme principal e saídas sociais;
- CTA, publicação e copy.

A IA não pode inventar:

- `asset_id`/`media_id`;
- arquivos, caminhos ou URLs;
- fotos ou vídeos inexistentes;
- `service_key` fora do catálogo;
- transições/efeitos/capabilities não publicados;
- materiais, marcas, medidas, preços, prazos ou resultados não confirmados.

Incerteza factual deve aparecer em `facts_to_confirm`/`needs_human_confirmation`, e não ser convertida em fato.

## Cobertura obrigatória de mídia

A resposta V3 contém `asset_decisions` com exatamente uma decisão para cada mídia elegível. A validação local rejeita:

- mídia elegível omitida;
- ID duplicado ou inexistente;
- `decision` diferente de `use`/`discard`;
- mídia marcada `discard` usada no plano;
- mídia marcada `use` que não aparece em nenhuma saída executável do `director_plan`.

Isso não prova cognitivamente que um modelo externo “assistiu” cada frame, mas torna omissão e inconsistência estrutural detectáveis e bloqueáveis.

## Cards

A IA não gera PNGs como resposta. Ela declara cards no Roteiro Mestre. Após a aplicação do JSON V3:

1. o Roteiro Mestre é validado;
2. `EDIT_PLAN.json` é publicado;
3. o runtime tenta ativar os cards pelo `fr-universal-card`;
4. `CARD_STATE_V2.json`, migração e previews são materializados quando houver cards;
5. falha de materialização é registrada como `applied_card_activation_failed` em vez de ser escondida.

Cards comuns e de serviço pertencem à mesma pipeline universal. Card de serviço exige `service_key` válido e evidência contextual/visual suficiente.

## `ready_video`

Quando `timeline_locked=true`, a IA não pode remontar o vídeo-base. Ela decide somente as camadas permitidas pelo contrato: cards, overlays, balões, legendas, logo, callouts e demais elementos suportados.

## Compatibilidade

- JSON V3: modo padrão — Direção Autônoma / nova edição.
- JSON V2: continua importável para compatibilidade/revisão.
- Markdown legado: continua importável.

O gerador padrão da aba 05 não precisa publicar um snapshot V2 antes do V3. O estado legado não contamina o pacote autônomo.

## Aplicação e auditoria

A resposta V3 é salva em:

- `_ENTRADA/AI_DIRECTOR_RESPONSE_V3.json`
- `PACOTE_PARA_IA/V3/AI_DIRECTOR_RESPONSE.json`

A aplicação mantém versionamento/backup das decisões do projeto e produz relatório de revisão. A resposta só passa ao projeto depois das validações de contrato, mídia, tempo, IDs e capabilities existentes.

## Projeto novo pela aba 05

Se ainda não existir `MANIFESTO_MEDIA.json`, o Studio usa `preparar-ia` em vez da preparação editorial completa. Esse caminho executa somente:

1. extração segura;
2. catálogo de mídia;
3. proxies e miniaturas;
4. integridade/manifesto;
5. snapshot e lotes V3.

Ele não cria `EDIT_PLAN.json`, `CARD_STATE_V2.json`, cards, plano social ou autoedição antes da IA.

## Orçamento de contexto

Os metadados determinísticos foram deliberadamente separados da mídia e mantidos compactos. Em uma fixture mínima da 4.6, os oito documentos V3 somam aproximadamente **20 KB** antes dos proxies. O aplicativo não depende de um tamanho específico de janela de contexto do modelo: os proxies são distribuídos em lotes configuráveis e vídeos que excedem o orçamento de transporte são divididos com mapa de cobertura temporal verificado, sem descarte editorial.
