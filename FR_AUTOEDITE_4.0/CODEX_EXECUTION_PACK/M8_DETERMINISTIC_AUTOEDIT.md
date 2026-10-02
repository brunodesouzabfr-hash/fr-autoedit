# M8 — Deterministic AutoEdit

**PRE-AUDIT ASSUMPTION:** `build_auto_plan` e `build_random_plan` já existem no remoto; M0 deve mapear seleção, qualidade, fases, cards, balões, validação e render reais. Após M2/M6/M7, melhorar lacunas comprovadas do baseline. Não criar segundo motor paralelo sem justificativa.

Modo CPU/offline, sem IA obrigatória; manifesto íntegro, contexto e Style Pack alimentam regras determinísticas (seed explícita se aleatoriedade). Emitir o mesmo `EDIT_PLAN` validado pelo fluxo manual/IA, com reasons, provenance, snapshots e opções editáveis. Seleção por fases, cortes úteis e limites válidos, cards por catálogo existente, balões do pack se M4 concluída, transições com suporte real; social somente onde pipeline já dá suporte. Não inferir serviço técnico sem evidência de contexto/classificação; se material insuficiente, produzir draft limitado/aviso, não claim falso. Preview usa proxies íntegros, master originals; ready_video continua sem remontagem da base.

Teste golden sintético com seed fixa e comparação baseline vs novo, execução sem rede/modelos, validação do plano, `ffprobe` no draft, rollback e regressão raw/ready. Documentar nível de automação e capacidades não suportadas sem afirmar “edição completa” quando ausentes. Matriz M8.
