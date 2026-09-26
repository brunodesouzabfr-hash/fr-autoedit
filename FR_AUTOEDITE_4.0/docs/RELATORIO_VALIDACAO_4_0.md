# Relatório de validação — FR AutoEdite 4.0 beta-next

Data: 2026-09-26. Identificador técnico: `4.0.0-candidate`. Distribuição:
**FR AutoEdite 4.0 beta-next**. Ambiente: checkout Git local, projetos e mídias
sintéticos, sem uso de projetos pessoais.

## Resultado executivo

| Verificação | Resultado |
|---|---|
| Milestones M1–M8 | aprovadas nos commits registrados abaixo |
| Pytest completo | 128/128 aprovados em 182,15 s |
| Suíte Python completa `*_test.py` | 93/93 aprovados em 159,8 s |
| Studio HTTP | `STUDIO HTTP TEST OK` |
| Card Editor ready-video HTTP | `CARD EDITOR READY HTTP TEST OK` |
| Estado da UI do Studio | `STUDIO UI STATE TEST OK` |
| Smoke fundação v4 | 27 aprovados; smoke concluído |
| Smoke visual v4 | 8 aprovados; `SMOKE V4 VISUAL OK` |
| Smoke integral raw/ready | `SMOKE TEST OK` na repetição limpa |
| Testes de release hardening | 4/4 aprovados |
| Empacotamento | allowlist `git ls-files`, CRC íntegro, nomes únicos |
| Caminhos proibidos no ZIP | nenhum |
| Compilação Python e sintaxe shell | aprovadas |
| `git diff --check` | aprovado |
| Aprovação visual para publicação | pendente de revisão humana |

## Milestones M1–M8

| Milestone | Commit | Escopo validado |
|---|---|---|
| M1 | `56a5ed5` | bridge content-only e instalação modular local do Card Editor |
| M2 | `e40246d` | placement de cards nos relógios raw/ready |
| M3 | `3cee83a` | mídia de cards de serviço, crop, zoom, focal point e fallback |
| M4 | `15a665e` | balões medidos, safe areas e conflitos explícitos |
| M5 | `fcf2d92` | intent declarativa, validator, diff e confirmação |
| M6 | `63ae9c7` | pacote IA V2 derivado do snapshot atual |
| M7 | `4a00895` | lineage, hashes e cobertura decodificada dos proxies |
| M8 | `44965df` | AutoEdit determinístico, offline e reversível |

## Comandos executados no hardening

```bash
python3 -m pytest -q tests
python3 -m unittest discover -s tests -p '*_test.py' -v
python3 -m unittest tests.release_hardening_test -v
python3 tests/studio_http_test.py
python3 tests/card_editor_ready_http_test.py
node tests/studio_ui_state_test.cjs
bash tests/smoke_v4_foundation.sh
bash tests/smoke_v4_visual.sh
bash tests/smoke_test.sh
python3 scripts/empacotar_release_v4.py
python3 -m compileall -q app scripts tests
bash -n install.sh INSTALAR_FR_AUTOEDITE_4.sh \
  INSTALAR_EM_OUTRO_COMPUTADOR.sh ATUALIZAR_CORRECAO_CARDS.sh \
  ATUALIZAR_FR_AUTOEDITE_3.3.1.sh ATUALIZAR_FR_AUTOEDITE_3.4.0.sh
git diff --check
```

O primeiro smoke integral, executado imediatamente depois das demais suítes,
teve uma falha transitória do FFmpeg ao abrir o encoder AAC em uma junção social
curta. Não houve alteração de código para mascará-la. Recursos e processos
residuais foram conferidos, e uma repetição completa e isolada terminou com
`SMOKE TEST OK`. O evento permanece registrado como risco operacional.

## Hardening do pacote

O empacotador seleciona nomes exclusivamente pela allowlist do Git e aplica uma
segunda política de exclusão. Arquivos untracked, symlinks, caches, temporários,
ZIPs, vídeos, diretórios de projeto e os seguintes materiais não podem entrar:

- `CODEX_EXECUTION_PACK/`;
- `README CODEX.TXT` e `promptcodexpart1.txt` a `promptcodexpart3.txt`;
- `FR_CARD_EDITOR_UNIVERSAL_v1.1.0/` e `FR_CARD_EDITOR_STANDALONE.html`;
- `Studio/`, `originais/`, `proxies/`, renders e mídias pessoais;
- o manifesto histórico da raiz, substituído por um único manifesto gerado.

O ZIP é reaberto antes da publicação, passa por CRC, comparação exata com a
allowlist e verificação de nomes duplicados. `SHA256SUMS.txt` referencia somente
o ZIP de código produzido; artefatos locais de `entrega/` não são copiados.

## AutoEdit documentado e operacional

```bash
fr-autoedite autoeditar --projeto /CAMINHO/DO/PROJETO
fr-autoedite autoeditar --projeto /CAMINHO/DO/PROJETO --modo automatico
fr-autoedite autoeditar --projeto /CAMINHO/DO/PROJETO --modo cronologico
fr-autoedite autoeditar --projeto /CAMINHO/DO/PROJETO --modo alfabetico
fr-autoedite autoeditar --projeto /CAMINHO/DO/PROJETO --modo aleatorio --seed 731
fr-autoedite autoeditar --projeto /CAMINHO/DO/PROJETO --modo automatico --aplicar --draft --somente both
```

Sem `--aplicar`, a operação apenas propõe e valida. Ao aplicar, cria snapshot e
informa `rollback_version`; a recuperação usa `listar-roteiros` e
`restaurar-roteiro --versao`. `ready_video` é bloqueado. A master de
`raw_media` aponta para originais e somente o draft usa proxies validados.

## Limitações e gates externos

- revisão visual humana permanece obrigatória antes de publicação final;
- assets modulares do Card Editor não integram o Git nem o ZIP; sua licença e
  procedência continuam pendentes antes de publicação ou redistribuição externa;
- controles do editor externo não suportados fielmente pelo renderer continuam
  indisponíveis ou apenas como referência visual;
- ferramentas opcionais marcadas como `discovery_only` ou `metadata_only` não
  constituem pipelines implementados;
- o AutoEdit determinístico não remonta `ready_video`, não classifica serviços
  sem evidência e não depende de IA ou nuvem;
- a falha transitória de inicialização AAC descrita acima merece observação em
  máquinas com recursos limitados, embora a repetição integral tenha passado.

## Critério de promoção

O código e o pacote estão aptos para revisão da distribuição beta-next quando
todos os checks deste relatório forem reproduzidos. Redistribuição dos assets
externos do Card Editor exige verificação de licença separada; promoção para
release visual final exige aprovação humana das saídas renderizadas.
