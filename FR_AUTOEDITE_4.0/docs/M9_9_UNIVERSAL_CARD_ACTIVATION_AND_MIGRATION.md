# M9.9 — Universal Card Activation and Migration

## Resultado

Ao abrir um projeto que já possui `MANIFESTO_MEDIA.json` e um plano ativo, o
Studio faz o inventário de todos os cards raw (`EDIT_PLAN.json`) ou ready
(`READY_VIDEO_PLAN.json`) e cria o estado canônico em
`_CONTROLE/CARD_STATE_V2.json`. O plano e as mídias permanecem somente leitura.

Cada card convertido recebe o mesmo ID, textos e placement raw (índice e
duração) ou ready (início e fim). Assets são resolvidos exclusivamente por ID,
hash e manifesto. O relatório `_CONTROLE/CARD_MIGRATION_V99.json` registra a
versão, fingerprint do plano/manifesto, resultado por card, previews e snapshot
de rollback. Reexecutar com o mesmo fingerprint, store e previews não grava nem
duplica estado.

## Fallback explícito

F1–F6 não é mais uma ausência implícita de CardInstance v2. Um card só chega ao
renderer legado quando o relatório contém, para aquele ID, uma rota única
`compatibility_fallback`, `renderer_id=fr-v4-f1-f6`, `registered=true` e uma
causa. Sem esse registro o render falha fechado.

Casos rejeitados incluem ID ausente/duplicado, placement inválido, asset fora do
manifesto/catálogo, hash divergente, mídia central não renderizável e estado v2
preexistente adulterado. A migração não cria assets nem aceita paths fornecidos
pelo navegador.

Planos derivados de Reel/draft não pertencem ao `EDIT_PLAN.json` canônico e
podem renumerar ou encurtar cards. Neles, cada ID sem CardInstance canônica recebe
antes do render uma rota `compatibility_fallback` nominal, com o arquivo do plano
e a causa registrados no relatório; não há fallback por ausência silenciosa.

## Snapshot e rollback

Antes da publicação, `project_scope.snapshot_decisions()` salva o estado anterior.
Store, relatório e previews são publicados numa transação recuperável. A chamada
`universal_card_runtime.rollback_project_card_activation(project, version)`
restaura a versão anterior, inclusive a ausência do store em projetos legados.

## Editor e render

Todo card migrado abre o adapter `fr-autoedite-card/2` no FR Card Editor
Universal. Texto, fundo, logo, mídia central, shape/crop, zoom, focal point,
geometria, tipografia, layers, grid e linhas persistem e reabrem do projeto.
Posição e animações temporais ready continuam no plano do overlay e são aplicadas
pelo compositor quando suportadas. Duração e IDs não são mutados pelo editor.

SERVICE usa o medalhão manifest-driven como padrão. Uma mídia central explícita
do manifesto pode substituí-lo sem perder `service_key`; permissões e hashes
continuam validados. Assets SERVICE mantêm os gates de proveniência, publicação e
revisão visual.
