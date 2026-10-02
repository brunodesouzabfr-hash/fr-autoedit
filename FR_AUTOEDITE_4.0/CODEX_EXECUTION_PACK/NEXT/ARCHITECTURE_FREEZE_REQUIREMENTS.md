# Requisitos para Architecture Freeze v1 da Next

**Estado atual:** ainda **não produzido**. Part 1/2 são prompts, não uma arquitetura aceita. Para congelar v1 é preciso escolher com ADR, evidência, alternativas rejeitadas, risco, trigger de revisão e estratégia de migração:

| Decisão estrutural | Evidência mínima |
|---|---|
| Linguagem/runtime/core e primeiro SO suportado | Benchmark/instalação, manutenção, offline, portabilidade |
| Arquitetura UI e isolamento do filesystem | Threat model e spike de preview/timeline |
| Formato de projeto, banco e versão de schema | Migração/relocação, queda abrupta, reabertura |
| Identidade/lineage de mídia e storage de análise | Duplicatas, Takeout, VFR, cache invalidation |
| Representação timeline/story vs render graph | Round-trip, seek, múltiplos outputs, teste ponta a ponta |
| Render backend e model jobs | Performance CPU/GPU, cancelamento/retry/checkpoint |
| Limite IA/core e provedores | Schema validado, provenance, recusa sem mutação |
| Brand/Domain/Content Pack e plugins | Versão, trust/capabilities, FR sem hardcode no core |
| Segurança/licenças/distribuição | Fontes, modelos, codecs, dependências, segredo, logs |
| Migração 4.0 e rollback | Fixture antiga, dois fluxos raw/ready, incompatibilidade explícita |

Um backend opcional STT/visão/embedding pode permanecer `PLUGGABLE`; marketplace, event sourcing e nuvem obrigatória não são pressupostos. Freeze inclui invariantes, aceitação do vertical slice e backlog de research spikes; não declara conclusões fictícias para tecnologias ainda não pesquisadas.
