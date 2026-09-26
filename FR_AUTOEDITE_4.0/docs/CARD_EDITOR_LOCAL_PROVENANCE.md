# Procedência local — FR Card Editor Universal v1.1.0

- Fonte recebida: diretório `FR_CARD_EDITOR_UNIVERSAL_v1.1.0/`, fornecido pelo proprietário deste projeto para integração local em 2026-09-23.
- Uso nesta M1: leitura do `index.html` modular e dos quatro PNGs em `assets/` por uma rota local autenticada do Studio. O arquivo standalone não é a implementação principal.
- Estado de licença: o pacote recebido não contém um arquivo `LICENSE` nem metadados suficientes para confirmar direitos de publicação ou redistribuição.
- Regra de distribuição: a ausência desses metadados não bloqueia o trabalho local autorizado, mas o pacote e seus assets não devem ser publicados, redistribuídos, enviados a um remoto ou incluídos em uma entrega externa até a procedência/licença ser documentada.
- Limite técnico desta integração: somente `title` e `body` atravessam o adapter `fr-autoedite-card-content/1`. Geometria, linhas, crop, imagens, Data URLs, exportação e armazenamento local permanecem fora do contrato enquanto o renderer F1–F6 não puder reproduzi-los com fidelidade.

## Instalação local reproduzível

O pacote-fonte e `local_components/fr-card-editor/` ficam ignorados pelo Git para evitar publicação acidental. Em um clone limpo, mantenha o ZIP ou diretório fornecido fora do repositório e execute:

```bash
FR_CARD_EDITOR_SOURCE=/caminho/FR_CARD_EDITOR_UNIVERSAL_v1.1.0 ./install.sh
```

O instalador valida a versão e os PNGs, copia somente `index.html` e os quatro arquivos modulares de `assets/` para `local_components/fr-card-editor/1.1.0` dentro da instalação e grava `LOCAL_COMPONENT_MANIFEST.json` com hashes e a pendência de licença. `FR_CARD_EDITOR_STANDALONE.html`, documentação e imagens de referência não são copiados. Para desenvolvimento sem executar a instalação completa, o mesmo resultado pode ser criado com `scripts/install_card_editor_local.py --source ... --destination local_components/fr-card-editor/1.1.0`.
