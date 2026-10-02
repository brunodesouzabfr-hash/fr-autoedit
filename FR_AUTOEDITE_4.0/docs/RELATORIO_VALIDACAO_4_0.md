# Relatório de validação — FR AutoEdite 4.0 beta-next

Data: 2026-09-27. Identificador técnico: `4.0.0-candidate`. Distribuição:
**FR AutoEdite 4.0 beta-next**. Ambiente: checkout Git local, projetos e mídias
sintéticos, sem uso de projetos pessoais.

## Resultado executivo

| Verificação | Resultado |
|---|---|
| Milestones M1–M8 | aprovadas nos commits registrados abaixo |
| Milestones M9.0–M9.7 | contratos e implementação aprovados nos commits registrados abaixo |
| Suíte Python completa `*_test.py` pós-patch M9.8 | 163/163 aprovados em 738,308 s |
| Studio HTTP | `STUDIO HTTP TEST OK` |
| Card Editor ready-video HTTP | `CARD EDITOR READY HTTP TEST OK` |
| Estado da UI do Studio | `STUDIO UI STATE TEST OK` |
| Smoke fundação v4 | 27 aprovados; smoke concluído |
| Smoke visual v4 | 8 aprovados; `SMOKE V4 VISUAL OK` |
| Smoke integral raw/ready | `SMOKE TEST OK` na repetição limpa |
| Testes de release hardening | 6/6 aprovados; instalação limpa 3/3 aprovada |
| Empacotamento | allowlist `git ls-files`, CRC íntegro, nomes únicos e auditoria SHA-256 externa |
| Caminhos proibidos no ZIP | nenhum |
| Compilação Python e sintaxe shell | aprovadas |
| `git diff --check` | aprovado |
| Golden masters M9 | 21/21 medidos e divergentes; revisão humana pendente |
| Licença/procedência do componente | pendente; redistribuição bloqueada |

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

## Milestones M9.0–M9.8

| Milestone | Commit | Escopo validado |
|---|---|---|
| M9.0 | `589e910` | arquitetura, contratos e golden masters locais |
| M9.1 | `32b0259` | schemas e validators CardDefinition/CardInstance v2 |
| M9.2 | `fc70a45` | adapter bidirecional `fr-autoedite-card/2` |
| M9.3 | `40bdc7a` | renderer universal determinístico Python/Pillow |
| M9.4 | `a53cb6d` | catálogo produtivo dos 13 serviços |
| M9.5 | `e22c485` | persistência, snapshot, rollback e round-trip raw/ready |
| M9.6 | `3d21b8c` | `CARD_EDIT_INTENT` v2 validado e confirmado |
| M9.7 | `9e9e631` | integração Studio, timeline, preview e render |
| M9.8 | estado atual | regressão integral, documentação e hardening de distribuição |

## Comandos executados no hardening

```bash
python3 -m pytest -q tests
python3 -m unittest discover -s tests -p '*_test.py' -v
python3 -m unittest tests.release_hardening_test -v
python3 -m unittest tests.card_editor_install_test -v
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

O primeiro smoke integral da validação M1–M8, executado imediatamente depois das demais suítes,
teve uma falha transitória do FFmpeg ao abrir o encoder AAC em uma junção social
curta. Não houve alteração de código para mascará-la. Recursos e processos
residuais foram conferidos, e uma repetição completa e isolada terminou com
`SMOKE TEST OK`. O evento permanece registrado como risco operacional.

## Hardening do pacote

O empacotador seleciona nomes exclusivamente pela allowlist do Git, aplica uma
segunda política de exclusão e confronta o SHA-256 dos arquivos selecionados
com o contrato do componente externo. O manifesto registra
`passed-by-path-and-sha256`. Arquivos untracked, symlinks, caches, temporários,
ZIPs, vídeos, diretórios de projeto e os seguintes materiais não podem entrar:

- `CODEX_EXECUTION_PACK/`;
- `README CODEX.TXT` e `promptcodexpart1.txt` a `promptcodexpart3.txt`;
- `FR_CARD_EDITOR_UNIVERSAL_v1.1.0/`, `local_components/` e
  `FR_CARD_EDITOR_STANDALONE.html`;
- `Studio/`, `originais/`, `proxies/`, renders e mídias pessoais;
- o manifesto histórico da raiz, substituído por um único manifesto gerado.

O ZIP é reaberto antes da publicação, passa por CRC, comparação exata com a
allowlist e verificação de nomes duplicados. `SHA256SUMS.txt` referencia somente
o ZIP de código produzido; artefatos locais de `entrega/` não são copiados.
Um arquivo rastreado que repita os bytes de qualquer asset externo congelado é
recusado mesmo que tenha sido renomeado ou movido para `assets/`.

## Fidelidade visual M9

O renderer Pillow repetiu bytes de forma determinística, preservou o estado
estruturado e comparou os 21 artefatos com o Canvas de referência. Todos foram
classificados como `divergent`: a razão de pixels diferentes variou de cerca de
5,73% a 92,67%, e o erro absoluto médio de cerca de 3,11 a 4,87 por canal. O
teste passa porque mede e expõe a divergência; ele não constitui aprovação
visual. A revisão humana dos PNGs e a decisão sobre fidelidade continuam
obrigatórias antes de promoção.

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
