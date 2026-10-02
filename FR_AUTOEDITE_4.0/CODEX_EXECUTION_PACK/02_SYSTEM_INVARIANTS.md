# Invariantes do sistema

Válidos em 4.0; Next deverá submetê-los a seu próprio Architecture Freeze. Toda milestone relata como preservou os invariantes afetados. `M0` identifica verificadores existentes e lacunas.

| ID | Invariante e verificação requerida |
|---|---|
| I01 | Original é imutável: sem escrita, rename, overwrite ou render em caminho de origem; teste com hash antes/depois em fixture. |
| I02 | IA só referencia `asset_id`/`media_id` existentes no manifesto corrente; rejeitar ID externo/desconhecido. |
| I03 | IA só referencia intervalo finito válido, `start < end`, dentro da duração efetiva, com base temporal declarada; cenas locais/absolutas não podem ser confundidas. |
| I04 | Toda decisão externa/IA passa por schema, validação semântica e diff/revisão aplicável antes da mutação; recusa é erro estruturado. |
| I05 | Claims técnicos/factuais usam evidência ou dado fornecido com proveniência; sem prova, omitir texto publicável e pedir revisão. |
| I06 | `render_3d` e referência visual não provam execução real; classificações e texto não os equiparam. |
| I07 | Interrupção não destrói estado: staging e persistência recuperáveis, sem gravação parcial tratada como válida. |
| I08 | Análise/cache ainda válido pode ser reutilizado por dependências/assinaturas; mudança de estilo não exige reanálise de mídia. |
| I09 | Fluxos básicos funcionam sem nuvem/IA externa; recursos opcionais degradam explicitamente. |
| I10 | Decisões automáticas relevantes são reversíveis por snapshot/operation log ou mecanismo comprovado; alterações manuais permanecem editáveis. |
| I11 | Regras FR de marca/domínio permanecem em packs/adapters, não no núcleo universal de mídia. |
| I12 | Mídia pessoal, `Studio/` de projetos, proxies, renders, segredos e logs pessoais nunca são incluídos no Git; fixtures são sintéticas. |
| I13 | Markdown/ZIP enviado à IA é representação derivada e regenerável, não source of truth; resposta anterior não contamina novo pedido. |
| I14 | Editor de cards e AutoEdite comunicam-se via fronteira versionada e validação explícita, inclusive persistência e render. |
| I15 | `raw_media` e `ready_video` continuam funcionais; `ready_video` mantém timeline do vídeo-base bloqueada e edita apenas overlays permitidos. |
| I16 | Preview e master de um mesmo estado não divergem silenciosamente em conteúdo/posição; diferença visual mensurável ou limitação documentada. |
| I17 | O estado aplicado conhece origem (`manual`, `deterministic_auto`, `ai_assisted`), versão/seed quando aplicável, ID estável e rollback. |

Se uma milestone não conseguir demonstrar um invariante afetado, encerre como **bloqueada/pendente**, com evidência da limitação; não declare conclusão funcional.
