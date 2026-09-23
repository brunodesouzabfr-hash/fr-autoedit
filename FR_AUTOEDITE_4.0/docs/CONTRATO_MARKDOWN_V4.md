# Contrato Markdown ↔ IA v4 — integração candidata

Três zonas: YAML imutável, corpo de revisão humana e único apêndice JSON
entre FR_AUTOEDITE_JSON_BEGIN/END. Valores YAML são serializados como JSON
em linha: isso é YAML válido, com subconjunto deliberadamente restrito,
sem tags, âncoras, duplicatas ou carregamento de objetos Python.

`schemas/roteiro_mestre_v4.schema.json` usa Draft 2020-12. O validador
stdlib implementa somente os keywords usados por esse arquivo; não é um
substituto universal de `jsonschema`. Quando Pydantic v2 está presente, o
payload também passa pelo modelo opcional em `models/roteiro_mestre.py`.

Validações: cabeçalho contra base gerada, fingerprint canônico do manifesto,
tipos estritos, IDs, tempos, catálogo, kinds, dados editoriais e preservação
do vídeo pronto. O corpo humano não é interpretado como comando. Extensão
de duração em ready_video é rejeitada até haver implementação explícita de
intro/outro sem alteração da base.

`contracts/service.py` publica Markdown e JSON somente após revisão válida,
por gravação temporária, `fsync` e substituição atômica em `_ROTEIROS/v4/`.
Os comandos da CLI são `gerar-roteiro-v4`, `validar-roteiro-v4` e
`aplicar-roteiro-v4`.

Migração conserva payload legado integral. Cards, social, velocidade,
transições incompatíveis e outras decisões não são descartados para fazer
o JSON parecer compatível. O resultado é um candidato de revisão, sem
aplicação automática. Seu relatório lista campos que precisam de integração.

O contrato v2 anterior continua disponível para projetos existentes. O v4 é
entrada explícita dos novos comandos e não é aplicado silenciosamente pelo
importador legado.

Limites atuais: `cuts` ainda não descreve toda edição de fotos/speed ramps;
before_after precisa de dois referenciais na integração seguinte; captions
é intenção, não transcrição; normalize_lufs não é normalização executada;
source/fonte não comprova semanticamente uma alegação. Nenhum deles será
rotulado como render pronto por este validador.
