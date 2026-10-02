# FR AutoEdite 4.6.1 — Resiliência por item

## Objetivo

A 4.6.1 torna jobs longos tolerantes a falhas locais sem enfraquecer a integridade do pacote V3.
Um item defeituoso deixa de encerrar toda a execução.

## Política de cenas virtuais

- A cobertura física realmente decodificável do proxy é a autoridade.
- Se uma cena ultrapassar apenas o final disponível, `scene_end_sec` e `duration_sec` são recortados.
- Se não restar intervalo útil, a cena recebe `status=skipped`, `excluded_from_auto_edit=true` e não entra no pacote da IA.
- Miniatura vazia de cena descarta apenas aquela cena.
- O original e o proxy pai nunca são recortados ou reescritos por essa correção.

## Resiliência por mídia

Na preparação, análise, verificação de integridade e handoff:

- erro técnico isolado -> item marcado `error` e inelegível;
- skip manual -> item marcado `skipped` e inelegível;
- demais itens continuam;
- se um proxy falhar depois do snapshot, o manifesto é atualizado e o snapshot V3 é regenerado sem aquele proxy antes de criar os ZIPs.

Isso evita um pacote inconsistente no qual `MEDIA_MANIFEST.json` anuncie uma mídia que não está presente nos lotes.

## Pular item atual

O Studio expõe `Pular item atual` durante jobs com `current_item` conhecido.
A solicitação é cooperativa e por item. Processos FFmpeg longos associados à mídia atual são encerrados com segurança; o processo principal continua no próximo item.

Rota local: `POST /api/skip-current`.
Marcador transitório: `_CONTROLE/SKIP_CURRENT_ITEM.json`.

## Otimização de cenas

Cenas virtuais do mesmo vídeo pai não repetem a decodificação integral do proxy.
A verificação-base é cacheada por `source_path + proxy_path + generation_parameters`, e cada cena valida apenas sua janela sobre essa prova.

Exemplo: `M0036C001...M0036C018` usam uma única prova de decodificação de `M0036`, salvo quando a prova é invalidada.

## Auditoria

`MANIFESTO_MEDIA.json` recebe `integrity_report` com:

- `verified`
- `clamped_scenes`
- `skipped_scenes`
- `errors`

O relatório de análise local também registra cenas recortadas/descartadas e skips manuais.
