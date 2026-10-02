# M1 — Card Editor Bridge — executar somente após M0

**PRE-AUDIT ASSUMPTION:** arquivos e rotas citados abaixo correspondem ao remoto `915c13c`; M0 deve confirmar o checkout. Leia 00–07 e relatório M0; ajuste este prompt com achados documentados. Escopo M1: abrir o editor pelo Studio, carregar estado atual de um card, editar manualmente, salvar no projeto, recarregar e atualizar preview. Sem IA, sem novo placement de timeline, sem redesign de balões, sem pacote novo/proxies/AutoEdit.

## Design mínimo

1. Defina uma fronteira versionada `AutoEdite card ↔ CardEditorAdapter ↔ fr-card-editor/1.1`. Escreva mapeamento de ida/volta com campos suportados, desconhecidos, fixos/variáveis e propriedades que ficam no `CARD_STYLE.json`. Valide ao receber: tamanho/forma de payload, IDs, texto, tipos e números finitos, cores, Data URLs/assets contra política local. Não usar `applyConfig` como validator único.
2. Integre UI do editor via rota/painel same-origin ou iframe controlado se a auditoria provar segurança/compatibilidade. Estado do projeto se sobrepõe ao `localStorage` prévio; carregar explicitamente e impedir contaminação entre projetos. Tratar tokens/origin/paths de assets corretamente. Preservar arquivos modulares `index.html`+`assets`, sem trocar por standalone volumoso apenas por conveniência.
3. Persistir apenas no formato do projeto escolhido pela auditoria, com versão/snapshot/rollback. Preservar famílias F1–F6 e renderer legado como fallback para propriedade/família não representada. Salvar altera assinatura de preview e render coerente. **Atenção:** `FRCardEditor.exportPNG()` dispara download no browser e não fornece arquivo ao backend; demonstrar um caminho concreto de preview/render da edição salva. Se não couber em M1 sem novo renderer, restringir o primeiro round-trip a campos cujo compositor atual represente com fidelidade e registrar demais como não suportados; não declarar “todos os campos editáveis” sem renderização correspondente.
4. Suportar cartão acessível no modo `raw_media` e overlay card existente em `ready_video` quando há card aplicável; manter base ready bloqueada. M1 não adiciona temporalidade nova.

## Casos de teste e aceite

- Projeto sintético A/B: abrir, alterar `title` e um atributo suportado, salvar, reabrir no mesmo projeto, trocar projeto, voltar; sem fuga por localStorage.
- JSON inválido, ID removido, Data URL malformada/grande, campo fixed inesperado: rejeitar sem mutação ou exigir regra explícita da UI; conteúdo antigo persiste.
- Comparar preview antes/depois e export relevante, incluindo fontes e logo; se só uma parte dos campos estiver mapeada, interface declara essa capacidade. `CARD_STYLE.json` de projetos antigos e fallback v2/legacy continuam funcionais.
- Rodar testes existentes aplicáveis para Studio, cards e ready_video, com fixtures novas focalizadas; não testar mídia pessoal. `git diff --check`; status/diff final. Critérios detalhados em `06_ACCEPTANCE_MATRIX.md`.

## Relatório

Arquivos alterados, contrato e versionamento, escolhas UI/segurança, payload de exemplo sem mídia, resultados dos casos, capacidades mapeadas e pendentes, rollback, riscos residuais. Não iniciar M2 se houver divergência visual/regressão; emitir `ARCHITECTURE_CHANGE_REQUEST` se a fronteira exigir mudança estrutural.
