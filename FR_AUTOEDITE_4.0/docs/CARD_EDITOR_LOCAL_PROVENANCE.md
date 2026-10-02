# Procedência local — FR Card Editor Universal v1.1.0

- Fonte recebida: diretório `FR_CARD_EDITOR_UNIVERSAL_v1.1.0/`, fornecido pelo proprietário deste projeto para integração local em 2026-09-23.
- Uso local até M9.8: o Studio carrega o `index.html` modular e os quatro PNGs
  por rota autenticada; o estado completo atravessa o adapter
  `fr-autoedite-card/2`, é validado e persistido como CardDefinition/CardInstance
  v2 e é renderizado offline pelo renderer universal. O arquivo standalone não
  integra a aplicação.
- Estado de licença: o pacote recebido não contém um arquivo `LICENSE` nem metadados suficientes para confirmar direitos de publicação ou redistribuição.
- Regra de distribuição: a ausência desses metadados não bloqueia o trabalho local autorizado, mas o pacote e seus assets não devem ser publicados, redistribuídos, enviados a um remoto ou incluídos em uma entrega externa até a procedência/licença ser documentada.
- Limite técnico atual: `fr-autoedite-card-content/1` permanece apenas como
  compatibilidade legada; o contrato v2 cobre geometria, linhas, crop, zoom,
  focal point, assets referenciados e o estado renderizável completo. Data URLs,
  paths graváveis, HTML/PNG como fonte de verdade e `localStorage` persistente
  continuam proibidos. A comparação com os 21 golden masters está medida, mas
  ainda diverge do Canvas de referência e exige revisão visual humana.

## Instalação local reproduzível

O pacote-fonte e `local_components/fr-card-editor/` ficam ignorados pelo Git para evitar publicação acidental. Em um clone limpo, mantenha o ZIP ou diretório fornecido fora do repositório e execute:

```bash
FR_CARD_EDITOR_SOURCE=/caminho/FR_CARD_EDITOR_UNIVERSAL_v1.1.0 ./install.sh
```

O instalador valida a versão e os PNGs, copia somente `index.html` e os quatro arquivos modulares de `assets/` para `local_components/fr-card-editor/1.1.0` dentro da instalação e grava `LOCAL_COMPONENT_MANIFEST.json` com hashes e a pendência de licença. `FR_CARD_EDITOR_STANDALONE.html`, documentação e imagens de referência não são copiados. Para desenvolvimento sem executar a instalação completa, o mesmo resultado pode ser criado com `scripts/install_card_editor_local.py --source ... --destination local_components/fr-card-editor/1.1.0`.

O empacotador de código exclui tanto o diretório-fonte quanto
`local_components/` e confronta o SHA-256 de todo arquivo selecionado com a
denylist congelada em `contracts/m9/fr_card_editor_1_1.json`. O status
`local_only_pending_license` permanece um gate: nenhuma distribuição externa
do componente ou de seus assets está autorizada por esta integração.
