# M5 — AI Card Editing

**PRE-AUDIT ASSUMPTION:** após M1–M3 há adapter, instâncias e validator de intervalos; M0 identifica rota de IA real. Não chamar IA obrigatoriamente, não incluir M6 pacote completo neste escopo.

Rota: `current project + manifest + editing task → AI_CARD_INTENT (declarativo) → deterministic validator → diff/review → apply/snapshot`. Permitir sugestão de família, texto, serviço, asset ID existente, crop/zoom, estilo permitido e intervalo válido; metadados `origin=ai_assisted`, evidence/provenance e versionamento. Claims técnicos sem evidência geram bloqueio/revisão; `[DADO A CONFIRMAR]` nunca vira texto do card publicável. No modo assistido, confirmação do usuário antes de aplicar. Permitir editar/reverter após aceitar. Não permitir API da IA escrever arquivos, chamar FFmpeg nem modificar a timeline diretamente. Ready mantém base intacta.

Testes com provider falso: intent válida/ID inventado/intervalo inválido/render 3D como única prova/asset inexistente/confirmação recusada; estado intacto nos casos inválidos e snapshot revertível no positivo. Reportar payloads de fixture, decisões, logs dos testes e limites. Matriz M5.
