# Regras de execução universais para Codex

1. Uma milestone por sessão/diff. M0 é estritamente read-only, termina com relatório e proposta de correções dos prompts. Não avançar para M1 no mesmo comando.
2. Antes de qualquer alteração de M1–M8: `pwd`, `git rev-parse --show-toplevel`, `git status`, branch/HEAD/upstream, descobrir `AGENTS.md`; identificar arquivos do escopo. Se branch for `main`, preparar branch dedicada conforme autorização da sessão de desenvolvimento. Nada disso é feito pelo Work.
3. Não presumir caminhos, APIs, classes, testes ou contratos. Confirmar por leitura do checkout, registrar arquivo/função/linha antes de editar; rotular demais como `TO VERIFY IN M0`.
4. Fazer diff pequeno e reversível, preservar caminho legado e dados; não reescrever a aplicação em big-bang. Mudança estrutural fora das decisões exige `ARCHITECTURE_CHANGE_REQUEST` antes do código.
5. Nunca `git add -f` de mídia pessoal, `Studio/` de projetos ou credenciais. Não usar dados do usuário como fixture. Não tocar nem limpar originais, proxies de projeto real ou `ready_video` de cliente. Fixtures sintéticas em diretórios temporários.
6. Não instalar dependências/migrations automaticamente. Dependência nova exige justificativa, licença/distribuição, impacto offline e escopo da milestone. Não acoplar nuvem/Whisper obrigatórios.
7. Descobrir testes existentes, executar os relevantes antes/depois, adicionar testes focados para riscos reais; `git diff --check`; reportar comandos e resultados verdadeiros, sem presumir pytest/smoke se não disponíveis.
8. Critério de entrega: arquivos alterados, diagrama/diff funcional breve, contratos migrados, testes executados, regressões, limitações, rollback e evidência da matriz de aceite. Não avançar com regressão aberta.
9. Validar `raw_media` e `ready_video` independentemente. Preserve timeline bloqueada do vídeo pronto e render por originals no fluxo bruto.
10. Sem commit, push, PR, merge ou deploy por padrão neste handoff. Se instrução posterior autorizar, seguir alcance específico; M0 continua sem alterações.

## Procedimento diante de conflito

Confirmar código → classificar requisito, suposição ou regressão → escolher correção local se não muda arquitetura → se muda, preencher `07_...TEMPLATE.md` com alternativas/testes/migração → aguardar decisão arquitetural necessária antes de introduzir desvio. Falha de teste existente requer investigação, não supressão.
