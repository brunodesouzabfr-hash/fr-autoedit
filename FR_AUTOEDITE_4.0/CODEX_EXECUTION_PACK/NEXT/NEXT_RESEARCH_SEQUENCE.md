# Sequência de pesquisa da Next

1. Reconstruir problema com dados de projetos reais autorizados/anonimizados e limites de hardware; usar 4.0 como baseline mensurável.
2. Part 1: alternativas de formato projeto, timeline, renderer, trabalho em segundo plano, modelos e UI; pesquisa de manutenção/licenças na documentação primária atual. Entregar ADRs candidatas e performance budgets mensuráveis.
3. Part 2: assumption register, conflitos, Red Team, pre-mortem, casos de falha, invariantes/provenance/privacidade, custo de migrar projetos 4.0.
4. Spikes focados quando duas alternativas não puderem ser decididas com evidência documental: teste em fixtures para seek, serialização, visual/paridade, recuperação e instalação Linux/CPU. Critério de escolha antes do teste.
5. Architecture Freeze v1 sob `ARCHITECTURE_FREEZE_REQUIREMENTS.md`. Registrar decisões abertas com prazo/owner e superfície de plugin.
6. Só depois: Codex Execution Plan por vertical slices, PRs pequenos e gates com rollback. Separar intenção narrativa de timeline física e provar `import → proxy → plan → validate → card → preview → render → reopen`, depois inteligência.

Não pesquisar toda a stack Next apenas para liberar M0/M1 da track 4.0.
