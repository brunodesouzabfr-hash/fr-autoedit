# FR AutoEdite 4.0 — leia primeiro

**Esta entrega é preparação para o Codex; nenhum software foi alterado.** Repositório: `https://github.com/brunodesouzabfr-hash/fr-autoedit`. Caminho operacional informado: `/home/romeu/FR-AutoEdite/FR_AUTOEDITE_4.0`. O Git root remoto está **acima** desse diretório; descubra o Git root local em M0. O remoto `main` apontava para `915c13c625a26115da27027c3cbfa80cae814517` na consulta read-only de 23/09/2026. O usuário informou `main local == origin/main` e working tree clean, ainda não verificáveis neste Work.

## Instrução executável inicial

Execute **somente `M0_CODEX_AUDIT.md`**, em modo leitura, e entregue seu relatório. Não prossiga automaticamente para M1. Na sessão de M0, leia nesta ordem: `01_CANONICAL_STATE.md`, `02_SYSTEM_INVARIANTS.md`, `03_ARCHITECTURAL_DECISIONS.md`, `04_CODEX_RULES.md`, `05_DEPENDENCY_MAP.md`, `06_ACCEPTANCE_MATRIX.md`, `M0_CODEX_AUDIT.md`. Leia `NEXT/` apenas para identificar limites entre tracks.

Após M0, corrija suposições dos prompts M1–M8 com evidência e execute uma milestone por sessão/entrega. Uma branch dedicada à primeira alteração é recomendada, sujeita ao estado real: `codex/fr-autoedite-4-card-editor`. M0 não cria branch, não instala dependências e não modifica arquivos do projeto.

## Autoridade e conflitos

1. Pedido mais recente do usuário e invariantes deste pacote.
2. Fatos verificados no checkout local durante M0, inclusive `AGENTS.md` aplicáveis.
3. Decisões normativas deste pacote; suposições marcadas `TO VERIFY IN M0` não são fatos.
4. `promptcodexpart3.txt`: fonte de requisitos da **4.0**, dividida em M1–M8; não é comando de execução integral.
5. `promptcodexpart1.txt` e `promptcodexpart2.txt`: fontes da **Next**; não são milestones da 4.0.
6. `README CODEX.TXT`: histórico/decisões em ordem temporal; correção posterior prevalece sobre proposta antiga. `README.md` descreve candidato e pode estar defasado.

Se o código contradisser um fato remoto, registre evidência; se contradisser uma decisão estrutural, produza `ARCHITECTURE_CHANGE_REQUEST` com `07_ARCHITECTURE_CHANGE_REQUEST_TEMPLATE.md` antes de implementar. Não leia milhares de linhas históricas por padrão: consulte apenas trechos pertinentes a conflito real.

## Limites de operação

M0: leitura e relatório. M1–M8: somente escopo da milestone aprovada, código e testes relevantes, com diff e relatório. Nunca versionar mídia pessoal, tocar nos originais ou interpretar `Studio/` de projetos do usuário como código-fonte. `app/studio.py` e `assets/studio/index.html` são código de interface confirmado no remoto, mas verifique checkout. Não fazer push, merge ou deploy sem instrução específica. A track Next depende de pesquisa, Red Team e Architecture Freeze próprios; seu vertical slice não acompanha M1.

> Nomes `CODEX_M*_...md` neste pacote são atalhos de encaminhamento; `M*_...md` são os prompts normativos.
