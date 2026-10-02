# Achados preliminares para orientar M0

Snapshot: blobs remotos de `main@915c13c` e ZIP anexado; nenhuma execução local da aplicação, teste ou browser foi feita. Estes achados **não substituem M0**.

| Área | Evidência preliminar | Risco/pergunta para M0 |
|---|---|---|
| Git | Raiz remota tem duas distribuições, `FR_AUTOEDITE_3.4.0_STUDIO/` e `FR_AUTOEDITE_4.0/`; HEAD `main@915c13c`. | Confirmar o Git root local e qual distribuição é instalada. |
| Entrada | `FR_AUTOEDITE_4.0/fr-autoedite` exec `app/fr_autoedite.py`; `app/studio.py` serve HTML em `assets/studio/index.html`. | Conferir token, origin/CSP e método seguro de incorporar editor. |
| Dados vs fonte | `.gitignore` ignora `Studio/`; UI não mora em `Studio/`. | Proteger dados pessoais sem proibir alterações em fonte. |
| Cards | `fr_v4/bridge.py` traduz segmentos legados para `CardSpec`; `card_renderer.py` compõe F1–F6; `templates/card_style.json` `schema_version=4`. | Adapter para editor 1.1, fallback, diff visual, v2 e legacy; não substituir `CARD_STYLE.json` diretamente. |
| Timeline | `StudioState.save_plan()` persiste `EDIT_PLAN.json` com segmentos tipo media/card; `save_ready_video_plan()` valida `READY_VIDEO_PLAN.json`; `ready_video.py` aceita overlays e base bloqueada. | Semânticas temporais diferentes para M2; evitar remount em ready. |
| Balões | `fr_v4/overlays.py` dimensiona balloon/callout com width=.72 frame, height≥.22 frame, caixa opaca. | M4 precisa measure por texto e paridade com CSS do preview. |
| Roteiro IA | `master_contract.py:generate()` usa plano atual, incrementa `revision`, constrói Markdown+JSON e chama `refresh_ai_package_documents()`; `create_chatgpt_package()` inclui planos, roteiro e proxies. | Geração atual pode carregar decisões antigas; M6 distingue novo roteiro de revisão. Metadados voláteis impedem equivalência byte a byte sem normalização. |
| Proxies | `build_manifest()` reaproveita por ID/source path/size/status e existência não vazia; `create_video_proxy()` troca partial por MP4; lote varre `proxies/`. | Não há prova suficiente de cobertura/duração no critério de reutilização; M7 mede e fecha. |
| Auto | `build_auto_plan()`, `build_random_plan()`, `apply_local_analysis()` já existem. | M8 é melhoria do baseline, não módulo inaugural. |
| Editor anexo | `window.FRCardEditor` exporta objeto `version=1.1.0`; Map declara `schema=fr-card-editor/1.1`. Boot aplica `localStorage`; `applyConfig` só testa `fields[]/lines[]`; PNG é download. | Versionar contrato adapter, validar payload, controlar inicialização e provar caminho backend preview/render. |
| Assets editor | Fundo/logo locais, fontes Google externas com fallback; Data URLs no JSON e standalone grande. | Fonte e output podem variar offline; limitar tamanho/asset, não expor material em rota pública. |
| Testes | Suíte no remoto inclui `tests/ready_video_test.py`, `phase2_ai_package_test.py`, `card_circle_test.py`, `card_preview_refresh_test.py`, `smoke_test.sh`, `smoke_v4_visual.sh`. | Existência não prova que passam; M0 descobre env e comando, M1 executa testes relevantes. |

## Riscos prioritários

1. **Paridade visual/editorial:** o editor anexo é um único template vertical de 941×1672; o renderer atual tem seis famílias e 1:1. Gateway de capacidade e fallback explícito em M1.
2. **Contaminação entre projetos:** `localStorage` do editor carrega estado anterior no boot e projeto pode conter Data URL; o Studio deve impor estado corrente e isolar acessos.
3. **Falsa garantia dos proxies/IA:** arquivo não vazio e plano anterior não equivalem a proxy completo ou roteiro zerado. M6/M7 deverão demonstrar os casos negativos.

## Critério de pesquisa externa nesta track

Decisões do pack usam código e artefatos concretos, sem adotar biblioteca nova. Investigar licenças das fontes/imagens e bibliotecas somente se a distribuição do editor ou dependência nova exigir. Pesquisa comparativa de stack pertence à Next; nenhuma ferramenta citada em Part 1/2 está congelada para a 4.0.
