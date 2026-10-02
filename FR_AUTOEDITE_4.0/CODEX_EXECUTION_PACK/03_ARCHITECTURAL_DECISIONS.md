# Decisões arquiteturais e contratos conceituais

Decisões deste handoff não impõem alteração imediata no projeto. O M0 confronta cada decisão com o código real; desvios estruturais usam `07_ARCHITECTURE_CHANGE_REQUEST_TEMPLATE.md`.

## AD-01 — Fronteira do Card Editor

Recomendação: `AutoEdite CardDefinition/CardInstance ↔ CardEditorAdapter ↔ fr-card-editor/1.1 ↔ Card Editor`. O `AUTOEDITE_MAP.json` é inventário; não contém o estado exportado nem garante validação. O adapter define versão explícita, mapeamento bidirecional, whitelist de IDs/propriedades, limites numéricos, assets permitidos, persistência transacional, invalidação de preview e reconciliação com renderer. Não mutar o `CARD_STYLE.json` para fingir que o contrato visual e o contrato do projeto são idênticos. Para M1, preservar renderer antigo como fallback e começar por round-trip de edição **manual de um card existente**. Integração por rota/painel isolado ou iframe same-origin é preferível a copiar JS do editor; escolher após M0 conforme token/origin/segurança do Studio. Evitar `FR_CARD_EDITOR_STANDALONE.html` como caminho principal pelo custo ~28 MB e duplicação. Não depender da leitura de `localStorage` do editor como source of truth: estado do projeto deve prevalecer; salvar via bridge explícita. `exportPNG()` baixa arquivo no browser; M1 precisa provar estratégia de preview/renderer, não presumir retorno PNG via API.

**Risco comprovado:** o editor anexado é uma única composição 9:16 altamente específica, enquanto AutoEdite renderiza seis famílias F1–F6 e também 1:1. A compatibilidade visual universal é `RESEARCH REQUIRED`. M1 deve preservar as famílias não mapeadas com fallback, sem prometer substituição integral. Fontes externas Google no HTML podem divergir das fontes locais do render; validar equivalência.

## AD-02 — Modelo de card (conceitual, não schema produtivo)

- `CardDefinition`: identificador/versão de família (`F1`–`F6` ou `SERVICE`), template/versão, campos variáveis/fixos, regras de layout/safe area, Brand Pack/style tokens, slots/fallbacks, dimensões aceitas, export/renderer capability. Deixar contrato antigo legível enquanto migra.
- `CardInstance`: ID estável, referência de definição e projeto, texto, serviço, `central_asset_id` ou fallback verificável, crop 1:1, zoom, focal point, posição, animação, fonte/origin, claims/evidence/provenance e revision; inclui **placement** temporal para modo específico. Em `raw_media`, segmento card entre trechos usa `duration_sec` e/ou `start/end` conforme timeline validada; em `ready_video`, overlay com `start_sec/end_sec` sobre base bloqueada. Não supor que os dois modos compartilham representação física.
- Na família `SERVICE`/F3, máscara circular matematicamente exata e imagem interna preserva proporção. `shape=circle` deve ser reimposta na validação/aplicação, mesmo se UI permitir square. Zoom, focal point, substituição e fallback visual rastreável. Não impor círculo às demais famílias. Verificar se saída JS em navegador e composição Pillow/FFmpeg conferem.

## AD-03 — Planejamento único com validação

`MANUAL`, `DETERMINISTIC_AUTO`, `AI_ASSISTED` produzem uma intenção/plano declarativo na fronteira do **EDIT_PLAN** existente ou uma versão migrável: `PLAN → VALIDATOR → DIFF/REVIEW → TIMELINE/OVERLAYS → PREVIEW → RENDER`. Ninguém altera arquivos originais. IA não executa shell/FFmpeg nem grava diretamente no projeto. Validar existência de IDs, janelas, overlap e regras de `ready_video`, estilos, assets e provenance. Aplicação transacional e reversível. M0 deve mapear validators atuais (`master_contract.py`, `StudioState.save_plan`, `save_ready_video_plan`) antes de refatorar; plano comum não significa unificar à força os modos de render.

## AD-04 — Documento de IA derivado

Source of truth são respostas, manifesto, planos/estado do projeto e regras de versão confirmados no checkout, não um Markdown previamente editado. `CONTEXT + MEDIA_MANIFEST + EDIT_TASK + EDIT_SCHEMA → IA → EDIT_PLAN → VALIDATOR → timeline`. Markdown permanece para interchange/review/handoff. Geração usa snapshot imutável do estado corrente, serialização determinística de conteúdo (metadados de auditoria voláteis fora do payload ou normalizados), escrita em staging e substituição atômica. Não incorpora `EDIT_PLAN` anterior como sugestão se a ação pedir novo roteiro zerado; se a UI oferecer revisão de edição existente, é fluxo distinto rotulado. Inventário completo inclui proxies elegíveis ou retorna erro específico por item; preserva resposta já importada e histórico em armazenamento distinto. Pesquisa M6 verifica migração da atual revisão `roteiro.revision` e compatibilidade de importação.

## AD-05 — Integridade de proxy

Registro por asset: `source_asset_id`, `source_hash`, `proxy_hash`, `source_duration`, `proxy_duration`, `coverage_start`, `coverage_end`, `generation_parameters`, estado/versão do pipeline. Hashes distintos. Validar proveniência, arquivos existentes/decodificáveis e cobertura temporal dentro de tolerância justificada por FPS, timebase, VFR, encoder delay e containers. M7 mede casos reais/sintéticos e define política para áudio que difere de vídeo e mídia estática. Ao truncar, bloquear pacote da IA e informar item/proposta de regeneração; proteger origem. A API atual já faz encode via FFmpeg, mas somente tamanho não vazio/identidade de arquivo não comprova completude.

## AD-06 — Balões e prioridades

M4 adiciona tamanho medido por texto e limites, padding, gradiente do traço para transparência, grid discreto, fundo leve, safe area, prioridade em relação a legenda e outros overlays; avoidance de sujeito quando detecção confiável. Se região livre não existe, reduzir/adiar/sinalizar revisão, não ocultar texto. Usar Brand/Style Pack e distinguir preview HTML de render PIL/FFmpeg. Não congelar design final agora.

## Decisões abertas

| Item | Estado e prova necessária |
|---|---|
| Canal Studio↔Card Editor (same-origin iframe, rota, painel) | PRE-AUDIT ASSUMPTION; M0 examina token, CSP, assets, segurança de URL; M1 testa round-trip. |
| Persistência de `CardInstance` e schema/versionamento exatos | TO VERIFY IN M0; evitar mudança de schema produtivo em M1 sem necessidade. |
| Paridade visual, 1:1 e todas as famílias | RESEARCH REQUIRED, documentar diferenças; usar fallback. |
| Limite por ZIP | Compatibilidade atual <150 MiB verificada no código; projetar limite por exporter/provider sem quebrar saída atual. |
| Render de cards editados por browser | `exportPNG()` não retorna Blob; demonstrar solução mínima real antes de marcar M1 aceita. |
