# Matriz de aceite — evidência exigida do Codex

Cada requisito é uma linha verificável. `TEST` indica tipo/caso, não afirma que o teste já passou. Use fixture sintética; reporte comando exato, resultado e artefato. M0 corrige paths e testes com a versão local.

## M0 — Auditoria

| REQUIREMENT | IMPLEMENTATION EXPECTATION | TEST | PASS CONDITION | REGRESSION GUARD | EVIDENCE REQUIRED FROM CODEX |
|---|---|---|---|---|---|
| Git e ambiente | Nenhuma modificação | `pwd`, `rev-parse`, `status`, `ls`, `check-ignore`, `ls-remote` read-only | Localização/status de todos os itens e divergências explícitas | Diff e status inalterados ao encerrar | Saídas resumidas com commit, branch e caminhos reais |
| Mapa de fluxos | Identificar entrypoint, contratos, rotas e testes | Inspeção com caminhos/linhas, leitura de schema | Separar raw/ready, renderer, IA, proxies e editor | Sem afirmar implementação inexistente | Tabela de fatos, suposições, riscos e M1 corrigida |

## M1 — Card Editor Bridge

| REQUIREMENT | IMPLEMENTATION EXPECTATION | TEST | PASS CONDITION | REGRESSION GUARD | EVIDENCE REQUIRED FROM CODEX |
|---|---|---|---|---|---|
| Abrir e carregar | UI aciona editor com estado do projeto atual | Fluxo Studio com projeto sintético e recarga | Editor correto, IDs e asset/fallback resolvidos, sem estado anterior de `localStorage` | Projetos separados não vazam dados | Vídeo/captura ou teste de integração reproduzível + payload redigido |
| Salvar/round-trip | Adapter valida e persiste uma edição manual | Editar título/estilo, salvar, reabrir, renderizar preview | Estado, preview e renderer mostram mesma mudança; rejeitar JSON malformado | `CARD_STYLE.json`/famílias não mapeadas preservados | Diff do estado, assinaturas preview e resultado visual |
| Fluxos existentes | Suporte manual raw e ready sem alterar mídia | Testes relevantes de ambos; hash originais | Ambos continuam abrindo, salvando e pré-visualizando | Base ready bloqueada | Logs/resultado dos testes, hashes quando pertinente |

## M2 — Card Timeline Integration

| REQUIREMENT | IMPLEMENTATION EXPECTATION | TEST | PASS CONDITION | REGRESSION GUARD | EVIDENCE REQUIRED FROM CODEX |
|---|---|---|---|---|---|
| Placement raw | Criar/editar/remover `CardInstance` sequencial com duração positiva | Plano sintético, preview/render, reload | Card surge no ponto e duração planejados, remoção não deixa cache | Trechos de mídia inalterados | Plano antes/depois, duração observada, teste |
| Placement ready | Overlay temporizado sobre vídeo-base | Start/end válidos; erro fora do vídeo; render | Apenas intervalo desejado recebe card; base não é cortada | `timeline_locked=true` | Contrato validado, medições de base e saída |
| Versão/fallback | Editar card e template sem perder projetos antigos | Fixture contrato anterior | Antigo abre/renderiza; novo round-trip | Sem conversão destrutiva | Teste de migração/fallback e relatório |

## M3 — Service Card Central Media

| REQUIREMENT | IMPLEMENTATION EXPECTATION | TEST | PASS CONDITION | REGRESSION GUARD | EVIDENCE REQUIRED FROM CODEX |
|---|---|---|---|---|---|
| Círculo F3 | Crop quadrado sem deformar e máscara circular | Fixtures paisagem/retrato e frames PNG | Diâmetro X=Y no output, aspecto interno preservado | Outras famílias mantêm formas próprias | Comparação visual/medida e screenshots 9:16/1:1 quando suportado |
| Asset/zoom/focal | Substituir, persistir e renderizar posição | Zoom min/max, focal extremos, reload | Sujeito visível ou aviso de revisão; asset ID existente | Fallback quando asset ausente, sem inventar imagem | Casos válidos/inválidos e prova de fallback |

## M4 — Balloon/Callout Engine

| REQUIREMENT | IMPLEMENTATION EXPECTATION | TEST | PASS CONDITION | REGRESSION GUARD | EVIDENCE REQUIRED FROM CODEX |
|---|---|---|---|---|---|
| Layout responsivo | Medida de conteúdo, padding e safe areas por formato | Texto curto/longo e 9:16/1:1 com bbox | Sem corte nem excesso desproporcional de vazio | Legibilidade com fontes do pack | Medidas bbox e imagens preview/master |
| Conflitos e estilo | Grid/traços com fade, evitar legenda/outro balão | Sobreposição deliberada, bordas e subtitle | Resolve ou sinaliza conflito, não oculta informação | Estilo legado recuperável | Relatório por cenário e render |

## M5 — AI Card Editing

| REQUIREMENT | IMPLEMENTATION EXPECTATION | TEST | PASS CONDITION | REGRESSION GUARD | EVIDENCE REQUIRED FROM CODEX |
|---|---|---|---|---|---|
| Intent validada | IA sugere, validator mostra diff e aplica após revisão | Proposta válida/inválida: ID, asset, tempo, claim | Inválida recusada sem mutação; válida editável/reversível | Nenhuma escrita direta pelo LLM | Payloads de teste, erros estruturados, histórico |
| Factualidade | Card técnico exige evidência ou revisão | Render 3D como única evidência; dados fornecidos | Claim não comprovado não vai ao render final | Sem CTA institucional irrelevante automático | Caso negativo/positivo e trilha de proveniência |

## M6 — AI Edit Package V2

| REQUIREMENT | IMPLEMENTATION EXPECTATION | TEST | PASS CONDITION | REGRESSION GUARD | EVIDENCE REQUIRED FROM CODEX |
|---|---|---|---|---|---|
| Pacote do zero | Context/manifest/task/schema derivados do snapshot | Gerar, editar resposta/planos antigos, gerar de novo | Nada anterior vaza; entradas iguais geram bytes equivalentes na parte determinística | Resposta já importada preservada fora do pacote novo | Diff/hash dos dois pacotes e teste de contaminação |
| Inventário completo | Referências a cada proxy elegível com razão para exclusões | Manifest com 3 vídeos, proxy ausente/corrompido | Todos incluídos ou erro identificado; schema importável | Compatibilidade/versão de projetos antigos | IDs comparados, erro e teste de migração |

## M7 — Proxy Integrity

| REQUIREMENT | IMPLEMENTATION EXPECTATION | TEST | PASS CONDITION | REGRESSION GUARD | EVIDENCE REQUIRED FROM CODEX |
|---|---|---|---|---|---|
| Lineage/cobertura | Hashes separados, durations, coverage, parâmetros | Fixture VFR, áudio assimétrico e proxy truncado | Íntegro passa; truncado falha, sem comparar hashes entre arquivos distintos | Proxy válido reutilizado sem tocar original | Tolerância justificada, relatórios ffprobe/hash |
| Packaging | Bloqueio claro para proxy ausente/corrompido | Repetir geração com itens faltantes | Nada parcial é entregue como completo | Lotes históricos tratáveis por migração/aviso | Teste negativo e estado recuperável |

## M8 — Deterministic AutoEdit

| REQUIREMENT | IMPLEMENTATION EXPECTATION | TEST | PASS CONDITION | REGRESSION GUARD | EVIDENCE REQUIRED FROM CODEX |
|---|---|---|---|---|---|
| Baseline auditado | Evoluir `build_auto_plan`/`build_random_plan`, não recriar cegamente | Comparar saída anterior/novo com seed fixa | Plano validado, decisões justificáveis, reversível | Modo manual/IA permanece funcional | Comparativo e plano normalizado |
| Saída offline | Edição por fases com cards/overlays conforme capacidades | CPU only, sem rede/modelo, render draft sintético | `ffprobe` confirma draft; limitações explícitas | raw e ready protegidos, fonte imutável | Logs, duração, codecs, testes relevantes |

## Encerramento de cada milestone

Codex reporta: requisitos aceitos/não aceitos, arquivos alterados, testes antes/depois, status Git, regressões, limitações e rollback. Resultado visual aprovado por testes não equivale automaticamente a release: revisão humana do master continua necessária.
