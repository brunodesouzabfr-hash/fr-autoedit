# M2 — Card Timeline Integration

**PRE-AUDIT ASSUMPTION:** no remoto `raw_media` usa `EDIT_PLAN.json` com segmentos card sequenciais; `ready_video` usa `READY_VIDEO_PLAN.json` com overlays `start_sec/end_sec` sobre base bloqueada. Validar no relatório M0. Depende de M1 aceita. Trabalhe somente placement temporal; não introduzir IA/novo renderer não necessário.

Representar `CardInstance` com ID estável/definição/instância/edit-origin e placement normalizado, **sem unificar de forma destrutiva** modelos físicos raw/ready. Permitir criar, mover, ajustar duração, trocar template compatível e remover no Studio. Intervalos finitos, start < end no relógio correto, duração >0, sem ultrapassar base no ready. Cache/preview invalidam apenas artefatos afetados. Ao salvar, snapshot, validator, reload e comparação com render. Manter fallback para instâncias legadas; não alterar duração, ordem ou velocidade do vídeo-base ready.

Teste com fixture sintética de dois segmentos raw e um vídeo-base ready; medir frame inicial/final do card, remoção, tempo inválido e reload; rodar suíte real relevante. Entregar planos antes/depois, resultados visuais e hashes de originais. Ver matriz M2. Se o modelo atual exigir migration, documentar compatibilidade e rollback antes de executar.
