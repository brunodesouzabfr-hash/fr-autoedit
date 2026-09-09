# Upgrade 3.4.0 — Fase 2: Roteiro Mestre Estratégico

Este documento resume a evolução do FR AutoEdite 3.4.0 nas Fases 2 e 2.1. A
mudança central é transformar o Roteiro Mestre na fonte principal das decisões
editoriais importadas pela aplicação.

## O que mudou

O fluxo assistido agora segue um contrato único:

```text
ZIP → proxies → manifesto → PACOTE_PARA_IA → Roteiro Mestre
→ resposta da IA → validação → plano → render
```

A aplicação gera o pacote automaticamente. Não é necessário montar arquivos
manualmente nem pedir que a IA invente caminhos, IDs ou configurações.

## PACOTE_PARA_IA

Cada projeto preparado pode gerar:

```text
PACOTE_PARA_IA/
├── 00_NAO_EDITAR_CONTEXTO_PROJETO.md
├── 01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE.md
├── 02_NAO_EDITAR_MANIFESTO_MEDIA.json
├── 03_NAO_EDITAR_LOTES_DE_PROXIES/
├── 04_NAO_EDITAR_INSTRUCOES_PARA_IA.md
└── 05_RESPOSTA_DA_IA_IMPORTAR_AQUI.md
```

- **00** informa o contexto confirmado pelo usuário;
- **01** é o único arquivo que a IA deve editar e devolver;
- **02** contém IDs, caminhos internos e dados técnicos das mídias;
- **03** reúne lotes independentes de proxies abaixo de 150 MB;
- **04** é o prompt operacional para copiar no chat da IA;
- **05** é o destino local da resposta que será importada.

## Roteiro Mestre estratégico

O contrato permite orientar:

- objetivo do vídeo, público, plataforma e etapa do funil;
- intenção editorial e arco de hook, desenvolvimento, processo/prova, clímax e
  CTA;
- primeira imagem forte, pergunta implícita, quebras de padrão, revelações,
  melhores momentos e recompensa visual;
- aceleração, time-lapse, câmera lenta, capítulos, fade e ritmo;
- CTA principal, secundário e por etapa do funil;
- chamadas para salvar, comentar, solicitar orçamento ou visitar um canal
  confirmado;
- hipóteses A/B de hook e CTA;
- legenda social e objetivo de lead;
- IHC, hierarquia, figura-fundo, proximidade, similaridade e atenção por
  movimento;
- branding Franco Romeu, com verdade material, método, autoria, precisão e luxo
  conceitual.

Essas escolhas ajudam a estruturar a edição. Elas não representam promessa de
retenção, viralização, lead, crescimento ou resultado comercial.

## Campos por trecho

Cada cena ou recorte pode registrar:

- `service_id`, `service_name` e `service_confidence`;
- `service_card_enabled`, `card_type` e `card_family`;
- `balloon_family`, `balloon_texts` e `visual_motif`;
- `overlay_text`, `voiceover_text` e `caption_text`;
- `transition_in` e `transition_out`;
- `start_sec`, `end_sec`, `duration_sec` e `playback_speed`;
- cortes, keyframes e demais decisões técnicas suportadas.

Uma mesma mídia pode ser dividida em vários segmentos. Assim, o plano pode
trocar de projeto 3D para elétrica, hidráulica, marcenaria ou acabamento no
instante correto.

Os nomes novos são normalizados para os campos já usados pelo render, como
`service_key`, `card_mode`, `narration`, `subtitles` e `transition`.
Isso mantém compatibilidade com roteiros anteriores.

## Cards e balões por família

O catálogo oferece estrutura configurável e composição procedural leve para:

- pintura;
- textura;
- elétrica;
- hidráulica;
- projeto 3D;
- revestimentos;
- iluminação;
- mobília e marcenaria;
- alvenaria;
- produções e eventos;
- instalação;
- manutenção.

Cada serviço possui família visual, família de balão e motivo material. A base
mantém verde-petróleo predominante, laranja como acento, ouro/osso como apoio,
tipografia FR e logo sem deformação.

## Marketing e neuromarketing éticos

O prompt proíbe inventar:

- métricas ou números;
- prova social;
- urgência ou escassez;
- preço ou desconto;
- cliente ou depoimento;
- resultado comercial ou técnico.

Quando faltar um fato indispensável, a IA deve usar `[DADO A CONFIRMAR]`
somente no metadado estratégico e deixar vazio o texto executável que não possa
ser comprovado.

## Anti-empilhamento

A aplicação detecta ou prepara avisos para:

- ZIP repetido;
- proxy ou lote repetido;
- card duplicado;
- Markdown antigo;
- resposta da IA já importada;
- render anterior;
- anexo temporário de tarefa interrompida.

As políticas disponíveis são substituir, criar nova versão/preservar histórico
ou cancelar. Nada é apagado automaticamente sem uma escolha explícita.

## Validação e tolerância

Antes de aplicar a resposta, o importador confere:

- um único bloco JSON e escopo de roteiro;
- identidade do projeto e fingerprint das mídias;
- IDs e janelas de tempo;
- duração, velocidade e `end_sec`;
- booleanos, números finitos, fontes e transições;
- texto de locução, legenda, card, balão e CTA;
- serviço e família disponíveis.

Campos desconhecidos ou ainda não renderizáveis são preservados em metadados
com aviso claro sempre que isso for seguro. O restante válido do plano continua
utilizável.

## Limitações atuais

- locução sobre mídia ainda não é sintetizada pelo motor local;
- keyframes arbitrários são preservados, mas não executados;
- `transition_out` exige repetir a decisão em `transition_in` do trecho
  seguinte para execução;
- legenda separada do overlay e múltiplos balões temporizados permanecem como
  metadados;
- algumas famílias ainda usam formas procedurais ou símbolos existentes em vez
  de assets exclusivos;
- publicação e medição de resultados continuam externas e manuais.

## Próximos passos

- executar locução e legendas independentes em trechos de mídia;
- adicionar balões temporizados e keyframes avançados;
- ampliar assets próprios por serviço;
- permitir edição completa da estratégia diretamente na interface;
- adicionar testes visuais automatizados das famílias e da timeline.

## Testes da Fase 2

O conjunto inclui regressões para pacote canônico, seis itens obrigatórios,
limite dos lotes, campos estratégicos, ética, troca de serviço, aliases,
fallbacks, respostas duplicadas e histórico não destrutivo.

```bash
python -m pytest tests
bash tests/smoke_test.sh
```

Consulte também [GUIA_RAPIDO_3_4.md](GUIA_RAPIDO_3_4.md).
