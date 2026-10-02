# M0 — CODEX AUDIT — somente leitura

**Objetivo:** auditar o checkout operacional real antes de escrever código. Leia `00_READ_FIRST.md` e os documentos 01–07. Termine com relatório `M0_AUDIT_REPORT.md` **fora do projeto produtivo**, ou entregue integralmente no chat. Não execute M1 na mesma sessão.

## Sequência de inspeção

1. `pwd`; localizar `.git` nos diretórios pais; `git rev-parse --show-toplevel`, `git status --short --branch`, `git rev-parse HEAD`, `git branch -vv`, `git remote -v` **sem expor credenciais**. Comparar com `origin/main` por operação read-only; se acesso remoto falhar, registrar. Não mudar branch/ref. Ler `AGENTS.md` aplicáveis.
2. Localizar `FR_AUTOEDITE_4.0/`, pasta `FR_CARD_EDITOR_UNIVERSAL_v1.1.0/`, Parts 1–3; para cada item, `git ls-files`, `git status --short --untracked-files=all`, `git check-ignore -v` e `stat` apropriados. Provar se está no Git root, tracked, untracked, ignored, fora do root ou ausente. O remoto do commit não contém os quatro itens; não supor erro local. Não executar `git add`, commit, push ou cleanup.
3. Inventariar árvore principal: launcher, instaladores, docs, knowledge, app, templates, schema, scripts, tests, assets e diretórios de projeto. Apontar entrypoint CLI, servidor e frontend e caminho de instalação/serving. Não abrir mídia pessoal.
4. Mapear código com caminho/função: Studio/API/token/origin; estado e persistência de projeto; cards F1–F6, renderer, `CARD_STYLE.json`; timeline `raw_media` e overlays `ready_video` com validator e diferenças de base temporal; balões; preview/master/cache; geração de IA/roteiro/importação; manifesto/proxy/lotes; AutoEdit existente; testes de regressão. Para cada fluxo, entradas/saídas e pontos de escrita em projeto.
5. Ler integralmente no diretório local do editor `README.md`, `AUTOEDITE_MAP.json`, `index.html` e arquivos estruturais. Verificar contrato exportado **versus** map: `getConfig()`, `applyConfig`, `setField`, `setLine`, `exportPNG`, `reset`, formatos, campos, layers, imagens Data URL, localStorage, fonts, PNG, inexistência ou presença de ponte `postMessage`, política de segurança e licença. Não presumir que o Map valida o objeto ou que exportPNG retorna bytes.
6. Analisar diff de contratos e compatibilidade para M1. Confirmar se o novo editor suporta uma família, seis famílias ou variantes; qual fluxo pode ter primeiro round-trip real sem reescrever render. Recomendação principal de UI/bridge com alternativa e custo. Identificar arquivos que M1 deve tocar e testes reais para raw/ready. Não impor schema final de CardDefinition/Instance.
7. Reconciliar código e prompt: o remoto já contém `build_auto_plan`, F1–F6, ready overlays e suíte; verificar checkout. Identificar riscos concretos: documento IA gerado a partir do plano atual, `revision` incremental, reaproveitamento de proxy por tamanho e cache, boot localStorage, falta de API de PNG, discrepância visual/1:1. Marcar `VERIFIED LOCAL`, `VERIFIED REMOTE`, `PRE-AUDIT ASSUMPTION`, `CONFLICT`, `RESEARCH REQUIRED`.

## Entrega obrigatória

Tabela de Git/local; mapa de módulos/funções; dois fluxos de timeline; inventário dos contratos atuais e diferenças com `fr-card-editor/1.1`; sequência de integração M1; risco/fallback/rollback; matriz de testes e fixtures sintéticas; arquivo/endpoint candidato ou `TO VERIFY`; correções pontuais nos prompts M1–M8 sem executá-los; bloqueios objetivos. Relatar quaisquer diffs anteriores do usuário sem tocá-los.

**Critério de aceite:** matriz M0 em `06_ACCEPTANCE_MATRIX.md`; nenhum código, dependência, migração, fixture em projeto real, branch/ref, commit ou artefato gerado no repositório. Execute somente verificações de leitura e `git status` final para provar que nada mudou.
