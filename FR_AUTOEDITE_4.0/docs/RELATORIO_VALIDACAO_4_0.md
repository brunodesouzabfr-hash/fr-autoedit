# Relatório de validação — FR AutoEdite 4.0.0-candidate

Data: 2026-09-22. Ambiente: cópia isolada do ZIP 3.4.0, sem projetos reais.

## Resultado executivo

| Verificação | Resultado |
|---|---|
| CLI `--version` e `--versao` | aprovado |
| Compilação `app/`, `scripts/`, `tests/` | aprovada |
| Testes legados executáveis individualmente | aprovados |
| Testes v4 via `unittest` | 8 aprovados |
| Smoke visual v4 | aprovado |
| Smoke integral 3.4.0 + v4 | `SMOKE TEST OK` |
| Ready video | 13 aprovados |
| Contrato mestre legado | 21 aprovados |
| Preview/cache/seleção de mídia | 6 aprovados |
| Pacote IA | 3 aprovados |
| Studio HTTP e recuperação de job | aprovados |
| QA técnico de cards | 56/56 com 100/100 |
| CRC do ZIP de cards | obrigatório na finalização |
| ZIP de código extraído e executado isoladamente | aprovado |
| Instalador lado a lado em diretório temporário | aprovado |
| Empacotamento determinístico | aprovado |
| Varredura por padrões comuns de segredo | nenhum encontrado |
| Aprovação visual para publicação | pendente de revisão humana |

## Comandos executados

```bash
./fr-autoedite --version
./fr-autoedite --versao
bash tests/smoke_v4_visual.sh
bash tests/smoke_test.sh
python3 tests/ready_video_test.py
python3 tests/master_contract_test.py
python3 tests/card_preview_refresh_test.py
python3 tests/phase2_ai_package_test.py
python3 tests/ai_brief_window_test.py
python3 tests/card_circle_test.py
python3 tests/draft_concat_route_test.py
python3 tests/preparation_resume_test.py
python3 tests/studio_http_test.py
python3 tests/studio_job_recovery_test.py
python3 -m unittest tests.test_v4_contract_service tests.test_v4_editorial tests.test_v4_visual -v
python3 -m compileall -q app scripts tests
python3 scripts/empacotar_release_v4.py
```

## Incidentes encontrados e corrigidos durante QA

1. A assinatura v2 de prévia incluía o plano inteiro e mudava sem alteração
   visual. A assinatura passou a usar apenas dependências visuais, mantendo
   invalidação por card, estilo, serviço, style pack e asset.
2. `studio_http_test.py` esperava literalmente 3.4.0. O teste passou a conferir
   o arquivo `VERSION`, sem enfraquecer o requisito de versão.
3. O modelo Pydantic rejeitava `base_video_id`, embora o gerador v4 produzisse
   esse campo. O campo opcional foi adicionado e ganhou regressão no round-trip.
4. A publicação motion poderia aceitar arquivo temporário incompleto. Agora
   usa retries determinísticos e FFprobe antes de `replace` atômico.
5. Temporários de PNG interrompidos podiam permanecer no diretório gerado e
   contaminar uma exportação avulsa. Gerador, normalizador, exportador e ZIP
   agora limpam/ignoram temporários e exigem exatamente 56 cards separados.

## Comandos que não puderam ser certificados neste ambiente

`python -m pytest tests` retornou `No module named pytest`. A suíte funcional
foi executada por `unittest`, scripts individuais e dois smoke tests, mas o
comando pytest não é marcado como aprovado. Para reproduzi-lo:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest tests
```

`git diff --check` é não aplicável porque o ZIP recebido não contém `.git`.
Na cópia real do repositório, execute:

```bash
git diff --check
git status --short
```

## Critério de promoção

Promover de candidato para release somente após: pytest na máquina de destino,
`git diff --check` no repositório real, inspeção das duas pranchas QA, execução
de um projeto sintético instalado lado a lado e aprovação humana dos seis
medalhões com fundo opaco preservado.
