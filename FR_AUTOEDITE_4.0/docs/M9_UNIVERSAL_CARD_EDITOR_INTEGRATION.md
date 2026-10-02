# M9 — Universal Card Editor Integration

## Objetivo

Integrar o estado estruturado do FR Card Editor Universal v1.1.0 ao Studio,
timeline e pipeline determinístico, sem alterar o compositor legado F1–F6.

O contrato executável da arquitetura está em
`contracts/m9/architecture_v1.json`. Os schemas produtivos de
CardDefinition/CardInstance v2 começam na M9.1; os arquivos da M9.0 são
contratos de referência e gates, não validators de escrita.

O limite conceitual aprovado para CardDefinition, CardInstance, AssetRef,
placement e projeção `title/body` está congelado em
`contracts/m9/card_state_v2_concept.json`. A M9.1 deverá transformá-lo em
schema/validator produtivo sem ampliar silenciosamente esse escopo.

## Submilestones e gates

### M9.0 — arquitetura executável e golden masters

Entregas:

- ACR aprovada e versionada;
- contrato real `fr-card-editor/1.1` em formato legível por máquina;
- fontes de referência fixadas por commit e SHA-256;
- 19 cenários locais, totalizando 21 PNGs;
- duas renderizações obrigatórias por artefato;
- estados completos junto aos PNGs;
- nenhum binário do componente ou fonte adicionado ao Git.

Gate: o manifesto local precisa validar todos os hashes, dimensões, 21 campos,
29 linhas, quatro shapes e os 13 `service_key`.

### M9.1 — CardDefinition/CardInstance v2

- schemas estritos e validators produtivos;
- leitura aditiva e compatível com CardInstance v1;
- referências de assets por ID e hash;
- projeção explícita de `title/body`;
- nenhuma persistência ainda ligada ao Studio até os testes unitários passarem.

### M9.2 — adapter bidirecional

- `fr-autoedite-card/2`;
- editor config ↔ estado v2 sem perda;
- upload transitório convertido em AssetRef;
- revisão obsoleta e campos desconhecidos rejeitados.

### M9.3 — renderer universal determinístico

- Python/Pillow, offline;
- fundo, logo, grid, textos, linhas, geometria, crop, zoom, focal point,
  auto-fit, sombras, metálico, layers e ícones;
- comparação com os golden masters da M9.0;
- F1–F6 sem alteração.

### M9.4 — catálogo SERVICE

- `service_key` validado resolve somente `medallion_<service_key>`;
- hash, origem e estado publicável conferidos;
- os seis medalhões opacos continuam sinalizados para revisão.

### M9.5 — persistência e round-trip raw/ready

- snapshot, escrita transacional e rollback;
- raw preserva sequência e duração;
- ready preserva vídeo-base, `timeline_locked`, início e fim;
- reabertura reproduz o mesmo estado canônico.

### M9.6 — CARD_EDIT_INTENT v2

- operações declarativas allowlisted;
- mesmo validator da edição manual;
- diff e confirmação obrigatórios;
- provider sem paths graváveis, callbacks ou filesystem.

### M9.7 — Studio, timeline, preview e render

- editor interativo carregando sempre o projeto atual;
- `localStorage` permanentemente fora da fonte de verdade;
- preview e master vindos do mesmo snapshot e renderer;
- cache invalidado somente por estado renderizável.

### M9.8 — testes, documentação e release hardening

- regressão integral M1–M8;
- raw/ready, HTTP/UI, smoke, instalação limpa e pacote;
- auditoria de ausência dos assets externos;
- revisão humana dos golden masters e licença antes de qualquer distribuição.

## Golden masters locais

Pré-requisitos de desenvolvimento:

```bash
python3 -m pip install -r requirements-dev.txt
```

Geração autorizada somente no diretório ignorado do componente local:

```bash
python3 scripts/generate_card_editor_goldens.py \
  --source FR_CARD_EDITOR_UNIVERSAL_v1.1.0 \
  --output FR_CARD_EDITOR_UNIVERSAL_v1.1.0/.m9-goldens \
  --download-fonts
```

Verificação posterior, sem rede:

```bash
python3 scripts/generate_card_editor_goldens.py \
  --output FR_CARD_EDITOR_UNIVERSAL_v1.1.0/.m9-goldens \
  --verify-only
```

O download explícito busca fontes OFL em commit fixado do repositório oficial
Google Fonts. Elas ficam no cache local ignorado e não fazem parte da aplicação
nem do release. O pacote modular, estados completos, imagens golden e fontes
continuam marcados como `local_only_non_redistributable`.

## Fidelity profile M9.0

- Autoridade: `exportPNG()`/Canvas do editor v1.1.0.
- Browser de referência registrado no manifesto de cada geração.
- Fontes: binários locais com SHA-256 fixado.
- Resolução lógica: 941×1672.
- Saídas: 941×1672, 1080×1920 e 2160×3840.
- Formato: 9:16 apenas.
- Comparação M9.3: hash idêntico para repetições do backend e golden visual
  medido. O limiar de diferença backend/browser só poderá ser fixado depois do
  primeiro renderer M9.3; não será ajustado para esconder divergências.

## Itens deliberadamente fora da M9.0

- schema produtivo v2;
- alterações em `app/card_timeline.py`;
- endpoints Studio;
- persistência de CardDefinition/CardInstance;
- render Python/Pillow;
- CARD_EDIT_INTENT v2;
- suporte 1:1;
- publicação ou redistribuição dos assets externos.
