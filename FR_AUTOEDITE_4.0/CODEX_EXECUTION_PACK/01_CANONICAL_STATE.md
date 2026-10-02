# Estado canônico e registro de fontes

Data da verificação remota: 23/09/2026. `VERIFIED REMOTE` indica consulta read-only de `git ls-remote` e árvore/blobs GitHub no commit indicado. `USER-CONFIRMED LOCAL` registra o estado relatado pelo usuário, sem atestar a máquina dele. `TO VERIFY DURING M0` exige checkout local.

## VERIFIED REMOTE

| Fato | Evidência e limite |
|---|---|
| HEAD simbólico = `main`; `main` = `915c13c625a26115da27027c3cbfa80cae814517` | `git ls-remote --symref` no URL do repositório; pode mudar após esta consulta. |
| Branches `codex/ready-video-chiaroscuro-v1` = `8975ddf…`, `codex/auditoria-fr-autoedite-3-4` = `d2e88d5…`, `master` = `803c573…` | Mesma consulta; não são alvo de desenvolvimento deste pack. |
| Raiz Git remota contém `FR_AUTOEDITE_4.0/` **e** `FR_AUTOEDITE_3.4.0_STUDIO/` | Árvore recursiva do commit, 340 entradas, `truncated=false`. Não confundir diretório operacional com root. |
| `FR_AUTOEDITE_4.0/fr-autoedite` chama `python3 app/fr_autoedite.py`; backend em `app/studio.py`; UI em `assets/studio/index.html` | Blobs lidos no commit. Local Studio é HTTP em loopback com API `/api/state`, `/api/plan`, `/api/ready-video-plan`, `/api/action`. |
| Contratos existentes: `EDIT_PLAN.json`, `READY_VIDEO_PLAN.json`, `CARD_STYLE.json`, `MANIFESTO_MEDIA.json`; `app/fr_v4` já possui bridge de cards F1–F6 e overlay renderer | Blobs e árvore; validar versão local antes de modificar. |
| Testes existem em `FR_AUTOEDITE_4.0/tests/`: `ready_video_test.py`, `phase2_ai_package_test.py`, `card_circle_test.py`, `card_preview_refresh_test.py`, smoke e testes v4 | Existência na árvore, **não execução nem aprovação**. |
| Pacote Card Editor e `promptcodexpart{1,2,3}.txt` não aparecem dentro de `FR_AUTOEDITE_4.0/` nesse commit | Ausência na árvore `915c13c`; não prova ausência na máquina do usuário. |
| `.gitignore` inclui `Studio/`, `*.zip`, mídias e credenciais | Não prova que nada sensível já está tracked; auditar localmente. |

## USER-CONFIRMED LOCAL

| Informação recebida | Status |
|---|---|
| Caminho `/home/romeu/FR-AutoEdite/FR_AUTOEDITE_4.0` operacional; branch `main`; HEAD local e `origin/main` em `915c13c`; working tree clean; push sincronizado | Relato do usuário. O caminho `/home/romeu/...` **não existe neste ambiente Work**. |
| Card Editor extraído na raiz operacional e Parts 1–3 presentes ou prestes a estar | Intenção/relato, não verificado no checkout local. |

## VERIFIED ATTACHMENT

O ZIP anexado contém `FR_CARD_EDITOR_UNIVERSAL_v1.1.0/README.md`, `AUTOEDITE_MAP.json`, `index.html`, `assets/`, um HTML standalone de ~28 MB. `AUTOEDITE_MAP.json` anuncia `schema: fr-card-editor/1.1`. O objeto real de `getConfig()` usa `version: 1.1.0`, `canvas`, `assets`, `gridStyle`, `layers`, `fields[]`, `lines[]`: **a string `schema` não está no estado exportado**. API em `window.FRCardEditor`: `getConfig`, `applyConfig`, `setField`, `setLine`, `exportPNG`, `reset`. `exportPNG()` faz download pelo navegador; não devolve buffer de imagem. `applyConfig()` verifica somente arrays `fields` e `lines`, não valida schema completo. `localStorage` reaplica estado anterior no boot. O editor não expõe API de `postMessage` nem uma ponte de persistência para Studio. Canvas-mestre 941×1672; exportações 941×1672, 1080×1920 e 2160×3840. Arquivos de imagem importados viram Data URLs no JSON. Trata-se de **um template visual concreto**, não contrato comprovado para seis famílias nem renderer headless.

## TO VERIFY DURING M0 — ENVIRONMENT VERIFICATION ITEMS

- `pwd`, diretório que contém `.git`, `git rev-parse --show-toplevel`, branch, HEAD, upstream, `git status --porcelain=v1`, refs atuais. Se a branch ou HEAD divergir, não resetar/checkout.
- Localização real e status tracked/untracked/ignored dos três prompts e pasta editor, inclusive diretórios pais; `git check-ignore -v` quando aplicável. Não executar `git add`.
- Diferenças entre local e commit remoto e eventuais instruções `AGENTS.md`.
- Qual diretório `Studio/` é dado de projeto; como `app/studio.py` e `assets/studio/index.html` são instalados e servidos; CSP/origin/token.
- Contratos, persistência, testes existentes e integrações efetivas além das leituras preliminares; status de licença/fontes do novo editor, conforme distribuição pretendida.

## Matriz de autoridade das fontes

| SOURCE | ROLE | CURRENT AUTHORITY | CONFLICTS | USE BY CODEX |
|---|---|---|---|---|
| Pedido atual do usuário | Escopo e limites | CANONICAL | Corrige comando antigo que mandava executar tudo | Primeiro |
| `README CODEX.TXT` | PROJECT/DECISION HISTORY | HISTORICAL; últimas correções consolidadas refletem a separação das tracks | Inclui recomendações antigas de integrar Next vertical slice e de proibir `Studio/` indiscriminadamente | Consultar só para rastrear decisão |
| Part 1 | Next vision | CURRENT REQUIREMENT para pesquisa Next | Proíbe implementação imediata | `NEXT/PART1_ROLE.md` |
| Part 2 | Next adversarial review | ARCHITECTURAL DECISION para validação Next; algumas hipóteses abertas | Requer Part 1 antes do freeze | `NEXT/PART2_ROLE.md` |
| Part 3 | Requisitos 4.0 | CURRENT REQUIREMENT após decompor M1–M8 | Acoplamento direto, `Studio/` proibido, comandos fixos de teste, executar 3 prompts juntos | M1–M8, nunca diretamente |
| ZIP Card Editor | API/artefato visual | VERIFIED ATTACHMENT, contrato mínimo parcial | Manifest `schema` vs estado exportado; não prova F1–F6/headless | M0 e adapter M1 |
| `README.md` anexado | Visão e guias candidatos | HISTORICAL/REMOTE quando confirmado em commit | Documenta candidato e várias rotas já existentes, sem atestar testes locais | Contexto, validar no código |
| Repositório remoto `main@915c13c` | Snapshot do código | VERIFIED REMOTE no instante | Pode diferir do checkout local | Evidência preliminar para M0 |
| Checkout local do usuário | Alvo real | TO VERIFY DURING M0 | Diretório ausente neste Work | Autoridade operacional após auditoria |

## Resolução temporal dos conflitos principais

| Item | Classificação | Resolução |
|---|---|---|
| Executar Parts 1+2+3 juntas ou Parte 3 inteira | SUPERSEDED | M0 read-only; depois M1–M8, um prompt por vez. Next separada. |
| Fazer o editor ler/gravar diretamente `CARD_STYLE.json` | CONFLICT | Adapter traduz contratos; `CARD_STYLE.json` permanece style do projeto. Não forçar schema do editor no core. |
| `Studio/` nunca pode ser alterado | SUPERSEDED | Proteger dados pessoais em `Studio/`; fonte `app/studio.py` e `assets/studio/index.html` pode ser modificada em M1. |
| Usar `pytest tests` e smoke sem descobrir sua presença | SUPERSEDED | Os arquivos existem no remoto, mas M0 verifica checkout/ambiente; em milestones rodar testes relevantes reais. |
| Todos os cards têm recorte circular | CONFLICT | Apenas família `SERVICE`/F3; editor universal preserva formas extras. |
| Limite 150 MB estrutural | HYPOTHESIS | O código atual de pacote aplica teto 150 MB por lote; preservar compatibilidade do destino atual e pesquisar parametrização por exporter em M6/M7. |
| Fazer AutoEdit do zero | SUPERSEDED | `build_auto_plan` e `build_random_plan` já existem; M8 mede lacunas e evolui baseline. |
| Proxy íntegro se arquivo não vazio ou hashes iguais | CONFLICT | Hashes distintos e duração/cobertura por fonte, sem garantia de identidade visual perfeita; M7 avalia casos VFR/stream. |
