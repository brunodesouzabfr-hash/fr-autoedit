# Arquitetura de migração — FR AutoEdite 4.0

## Decisão

Manter `app/fr_autoedite.py` como fachada pública da CLI 3.4.0. A nova
implementação reside em `app/fr_v4/`, evitando colisão entre o módulo
`fr_autoedite.py` e um pacote homônimo. Não reconstruir ingestão, FFmpeg,
jobs, isolamento ou transação que já existem.

Dependências mínimas: Python compatível com a base, Pillow, FFmpeg e FFprobe.
Adaptações opcionais são carregadas sob demanda, jamais na inicialização
do Studio. Detecção de presença não significa teste de funcionamento.

## Contratos entre camadas

| Camada | Entrada | Saída | Responsabilidade |
|---|---|---|---|
| core | tokens, formato e textos | caixas e camadas RGBA | medidas, tipografia e identidade |
| style_packs | manifesto e diretório local | assets verificados | caminhos confinados, hash e estado |
| contracts | YAML restrito + corpo + JSON | dados validados | corpo humano não executável |
| quiet_luxury | campos renderizáveis + evidências | violações por caminho | bloqueios e avisos separados |
| adapters | requisições tipadas | resultado/capacidade | rede e downloads desativados |
| pipelines | plano validado | jobs/render | reusar 3.4.0, sem tocar originais |
| editorial | decisões explícitas | filtros e artefatos | nunca inventar áudio ou resultado |
| Studio | estado persistido | revisão e prévia | acervo independente de seleção |

## Compatibilidade da fachada existente

Os comandos `novo`, `express`, `questionario`, `preparar`, `render`, `draft`,
`social`, `cards`, `replanejar`, `gerar-roteiro-ia`, `validar-roteiro-ia`,
`aplicar-roteiro-ia`, `status`, `auditar`, `pacote-chatgpt` permanecem.
Também devem permanecer os demais comandos detectados no parser, incluindo
Studio/wizard, Takeout, reset/restauração, copiloto e exportação em nuvem.
`replay` não é assumido como comando existente só porque aparece no prompt.

## Plano por módulo

- `fr_autoedite.py`: delegar composição nova, manter chamadas públicas.
- `master_contract.py`: conservar transação, adicionar entrada v4 explicitamente.
- `ready_video.py`: composição nova deve preservar semântica do vídeo-base.
- `style_engine.py`: reaproveitar seleção e adicionar registro v2 auditável.
- `local_analysis.py`: reutilizar funções técnicas através dos adapters.
- `service_cards.py`: preservar disponível no modo legado.
- `social_contract.py`: mapear famílias sem alterar enum de carrossel.
- `studio.py` e `assets/studio/index.html`: evoluir endpoints existentes.
- `project_scope.py`: não substituir o mecanismo de isolamento por cópias ad hoc.
- `render_joins.py`, `media_frames.py`, `copilot.py`: preservar até necessidade
  comprovada por testes.

## Limites não negociáveis

Não remapear IDs de mídia; não executar instruções de Markdown como código;
não usar shell=True; não instalar bibliotecas ou baixar modelos em silêncio.
O arquivo de entrada e `originais/` nunca são alvos de saída.

Uma versão com código escrito, porém sem regressão e QA visual, é candidata,
não release de produção. O relatório de entrega distingue esses estados.
