# FR AutoEdite — fundação da atualização 4.0

Este pacote é uma etapa de desenvolvimento. **Não substitui uma instalação
3.4.0 por uma release4.0 completa.** Adiciona módulos para as próximas fases
e conserva a CLI e o Studio atuais.

## 1. Extrair em uma pasta separada

Extraia `FR_AUTOEDITE_4_0_FASES_0_2_FUNDACAO.zip` pelo gerenciador de arquivos.
Entre na pasta extraída pelo terminal. Ela contém `aplicar_fundacao_v4.py`,
`PATCH_MANIFEST.json`, o diff e `source/` com arquivos novos.

## 2. Conferir o destino sem alterar nada

O destino é a pasta do código que contém `VERSION`, `app/` e `fr-autoedite`.
No caminho mencionado na conversa:

```bash
python3 aplicar_fundacao_v4.py --destino "$HOME/FR-AutoEdite/FR_AUTOEDITE_3.4.0_STUDIO"
```

Se o seu código estiver em outra pasta, ajuste apenas `--destino`.
Se a base divergir do ZIP recebido, o script para sem sobrescrever.
Não use opções de força nem substitua uma main mais nova pela base antiga.

## 3. Aplicar somente as adições verificadas

```bash
python3 aplicar_fundacao_v4.py --destino "$HOME/FR-AutoEdite/FR_AUTOEDITE_3.4.0_STUDIO" --aplicar
```

Essa operação não troca VERSION, não instala dependências e não inicia Studio.

## 4. Rodar verificações no diretório de código

```bash
cd "$HOME/FR-AutoEdite/FR_AUTOEDITE_3.4.0_STUDIO"
python3 -m pytest -q tests/test_v4_foundation.py
bash tests/smoke_v4_foundation.sh
python3 -m pytest tests
bash tests/smoke_test.sh
git diff --check
```

Se a pasta não for checkout Git, `git diff --check` não é aplicável. Em um
checkout, arquivos novos não rastreados podem não aparecer em `git diff`;
inspecione a lista do manifesto e valide o patch antes de qualquer commit.
Nenhum comando acima autoriza envio ao GitHub.

## 5. Indexar os assets preservados, quando for revisar a camada visual

```bash
python3 scripts/indexar_assets_v2.py
```

Cria cópias de identidade e normalizados separados; não redesenha imagens.
Os quatro serviços antes ausentes estão no ZIP3.4.0 mais recente. Arquivo
ausente no seu checkout fica `pending_asset`, bloqueado para publicação.

## 6. Saídas úteis para a continuidade

Cole a saída completa dos dois comandos pytest, dos dois smoke tests e
qualquer erro de hash do aplicador. Não envie mídias pessoais, credenciais
ou logs que contenham dados privados. Nenhum teste foi marcado como aprovado
sem essa execução.

## Reverter

Como nenhum arquivo da base é alterado, a CLI3.4.0 permanece funcionando
com seu caminho anterior. Para remover a fundação, use a lista de arquivos
novos do `PATCH_MANIFEST.json` e confira o hash antes de remover cada arquivo.
Não apagar pastas de projeto, assets originais ou arquivos modificados
posteriormente. Não usar `git clean` nem `reset --hard`.
