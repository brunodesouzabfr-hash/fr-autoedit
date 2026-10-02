# FR AutoEdite 4.5.1 — Universal Card Routing Fix

## Causa raiz confirmada

1. `card_image()` chamava `fr_v4.bridge.render_legacy_card()` antes de qualquer rota universal.
2. `generate_card_previews()` podia cair em `card_image()` quando `render_timeline_card()` não materializava um card universal.
3. Projetos ready_video sem overlays de card eram registrados como `status=completed` mesmo com `discovered=0`, `definitions=0` e `instances=0`.
4. `CARD_PREVIEWS.json` não registrava o renderer efetivamente usado em cada saída.

## Correções 4.5.1

- `card_image()` agora tenta `fr-universal-card` primeiro sempre que há `project_dir` + `segment_id/overlay_id`.
- Instâncias sem rota universal e sem fallback explicitamente registrado agora falham; não há downgrade silencioso para F1–F6.
- O renderer legado continua disponível apenas quando `render_timeline_card()` retorna `False`, condição reservada a fallback explícito registrado.
- Migração sem cards passa a registrar `status=no_cards_discovered` em vez de falso `completed`.
- `CARD_PREVIEWS.json` passa a registrar `renderer_id` e `definition_version` por preview.

## Evidência mínima

- `python3 -m py_compile app/fr_autoedite.py app/card_migration_v99.py`: OK.
- `UniversalCardActivationMigrationTest::test_first_studio_open_migrates_every_raw_card_idempotently_and_rolls_back`: PASS.
- Cenário ready_video sem overlays: `status=no_cards_discovered`, counts 0/0/0.

## Regra operacional

`fr-universal-card` é o caminho produtivo padrão. `fr-v4-f1-f6` somente pode executar quando o relatório de ativação contém fallback de compatibilidade explícito para a instância.
