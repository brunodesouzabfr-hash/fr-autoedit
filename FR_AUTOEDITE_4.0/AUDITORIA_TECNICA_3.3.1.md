# Auditoria técnica — FR AutoEdite 3.3.1

Data: 6 de setembro de 2026  
Resultado: **APROVADO PARA ATUALIZAÇÃO LOCAL**

## Escopo auditado

- importação do Roteiro Mestre devolvido pela IA;
- preparação, proxies, miniaturas e recuperação de interrupções;
- renderização do filme longo, versão limpa, rascunho e pacote social;
- servidor e interface do Studio;
- reprodução de vídeos grandes no navegador;
- galeria, gestão de projetos, limpeza e restauração;
- identidade visual, logo e cards 4K;
- instalador, atualização, rollback e preservação de projetos.

## Falhas encontradas e correções

| Prioridade | Falha | Causa confirmada | Correção 3.3.1 |
|---|---|---|---|
| Crítica | `início fora da janela de M0036C003` | O roteiro podia devolver o início no relógio local da cena, enquanto o validador aceitava somente o relógio absoluto do vídeo-pai. | O importador aceita ambos, normaliza para o tempo absoluto, preserva o deslocamento relativo quando a janela mudou e registra cada reparo. |
| Alta | Aparente congelamento em `63/64` | Não havia checkpoint por mídia nem sinal visual durante etapas sem saída; repetir podia refazer trabalho concluído. | Checkpoint atômico, reutilização de proxy/miniatura, arquivo atual, progresso, heartbeat, log persistente, cancelar e tentar novamente. |
| Alta | Player pesado ou sem resposta com master 4K | A entrega podia ser tratada como um arquivo único, inadequado para busca por tempo no navegador. | Streaming em blocos com HTTP Range (`206`), `HEAD`, seek e descarte de conexão interrompida. |
| Alta | Limpeza com risco de remover material de origem | Não havia uma política central de arquivos elimináveis. | Somente caches e derivados regeneráveis aparecem como candidatos; originais, entrada, Takeout, histórico, planos, manifesto e configuração são protegidos. A remoção inicial usa lixeira restaurável. |
| Média | Logs no fim da revisão e sem contexto operacional | O log não permanecia visível durante a navegação. | Painel lateral fixo com ação, mídia/segmento atual, percentual, tempo, estado e botões operacionais. |
| Média | Ausência de visualização central das saídas | Era necessário localizar os arquivos fora da interface. | Player em Revisar filme e Galeria para originais, cards, entregas e mídias sociais. |
| Média | Cards e assinatura sem acabamento visual uniforme | Fundos e assinatura não compartilhavam uma master material 4K. | Três fundos 3840×2160, logo FR RGBA remasterizada, Stardos Stencil, Rokkitt, Share Tech Mono e Cormorant Garamond; verde-petróleo/esmeralda, mármore, dourado acetinado e laranja neon. |

## Garantias de segurança

- O Studio continua restrito a `127.0.0.1` e usa token de sessão.
- Caminhos enviados ao servidor são resolvidos dentro do projeto; caminhos
  absolutos, travessia por `..` e links simbólicos não são aceitos para mídia
  ou limpeza.
- Projetos ativos só vão para a lixeira após confirmação exata do identificador.
- Esvaziar a lixeira exige a frase exata `APAGAR DEFINITIVAMENTE`.
- O atualizador valida o pacote antes da troca, cria backup da instalação
  anterior e possui rollback se a versão instalada não for confirmada.
- A atualização não move nem substitui `~/FR-AutoEdite/Studio`.
- A varredura não encontrou chaves de API, tokens ou chaves privadas incluídas
  no pacote.

## Testes executados

| Teste | Resultado |
|---|---:|
| Compilação de todos os módulos Python | PASSOU |
| Sintaxe JavaScript do Studio | PASSOU |
| Sintaxe de todos os scripts Bash de instalação | PASSOU |
| Tempos local/absoluto e arredondamento de time-lapse | PASSOU |
| Interrupção e retomada sem refazer proxy concluído | PASSOU |
| Heartbeat, progresso `1/64`, cancelamento e recuperação de sessão | PASSOU |
| Cards circulares e geração de prévias | PASSOU |
| Rotas HTTP, token, streaming Range, galeria e lixeira | PASSOU |
| Proteção de originais e restauração de arquivos/projetos | PASSOU |
| Google Takeout e recuperação de datas | PASSOU |
| Filme institucional, versão limpa e rascunho | PASSOU |
| Reels 6/8/10 s, Stories, capas e carrossel | PASSOU |
| Replanejamento determinístico e auditoria de entrega | PASSOU |
| Fluxo universal em projeto novo | PASSOU |
| Atualizador 3.3.1 em instalação isolada | PASSOU |
| Bateria integral `tests/smoke_test.sh` | **SMOKE TEST OK** |

## Limites intencionais

- A limpeza automática não classifica arquivos pessoais arbitrários como
  descartáveis. Ela oferece apenas derivados regeneráveis e projetos inteiros
  escolhidos explicitamente; isso evita apagar material que apenas parece
  antigo.
- Falha física de disco, arquivo-fonte corrompido ou codec não instalado ainda
  pode interromper um job. O 3.3.1 identifica o item, preserva o que terminou e
  permite retomar após corrigir a causa.
- A aprovação final continua exigindo assistir à master e às versões sociais;
  testes mecânicos não substituem revisão editorial humana.

