# FR AutoEdite 4.5.2 — UI version + zero-preview fix

## Corrigido
- O cabeçalho do Studio não contém mais `STUDIO 4.0` fixo. O HTML recebe a versão de `VERSION` no servidor.
- O comando `cards` não aceita mais um `EDIT_PLAN.json` existente porém sem segmentos de card como fonte suficiente para prévias.
- Quando não há cards no plano produtivo e o questionário existe, é criado `CARD_PREVIEW_PLAN.json` para revisão visual sem modificar a timeline produtiva.
- Cards desse plano de prévia são renderizados pelo `fr-universal-card`; não caem silenciosamente em F1--F6.
- Versão: `4.5.2-candidate`.

## Ready video
Em `ready_video`, o plano de prévia é deliberadamente separado do `READY_VIDEO_PLAN.json`. Ele permite conferir intro, serviço, fases e outro antes de definir janelas temporais de overlay, preservando o vídeo-base.
