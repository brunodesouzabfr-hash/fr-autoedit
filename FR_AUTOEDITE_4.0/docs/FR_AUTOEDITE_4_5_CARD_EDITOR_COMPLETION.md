# FR AutoEdite 4.5 — conclusão do FR Card Editor Universal v1.1.0

## Escopo

Correção da integração M9.x com foco em tornar `FR_CARD_EDITOR_UNIVERSAL_v1.1.0` a implementação visual efetiva dos cards universais, sem depender de um estado reduzido que apenas carregava título/subtítulo.

Versão do pacote: `4.5.0-candidate`.
Migração universal: `9.9.1`.
Definição universal migrada: versão `2`.

## Diagnóstico consolidado

### Implementado anteriormente e aproveitado

- `CardDefinition/CardInstance` v2.
- adapter `fr-autoedite-card/2` ↔ `fr-card-editor/1.1`.
- persistência transacional do estado v2.
- renderer `fr-universal-card` separado do F1–F6.
- rotas HTTP do Studio para abrir/salvar Card Editor Universal.
- ativação/migração M9.9 com snapshot, rollback e fallback legado explícito.
- preview universal e render universal na timeline quando a ativação está válida.
- catálogo SERVICE e mídia central circular com zoom/focal point.
- AI Card Intent validado antes de aplicar.

### Parcial/incorreto encontrado

1. **O baseline visual M9.9 não era o editor real.**
   `card_migration_v99._base_state()` fabricava geometria reduzida, deixava 19/21 campos vazios/invisíveis e as 29 linhas invisíveis. O contrato podia dizer `fr-universal-card`, porém o estado não representava o `DEFAULT` aprovado do editor v1.1.0.

2. **Projetos já migrados ficariam presos no baseline ruim.**
   A migração 9.9.0 é idempotente; apenas corrigir `_base_state()` não alteraria `CARD_STATE_V2` já publicado. Era necessária nova versão de migração/definição e upgrade controlado.

3. **Instalação declarava o editor instalado sem garantir as fontes exigidas pelo renderer.**
   `discover_font_root()` exige o font-cache fixado da M9.0. O `install.sh` instalava `index.html` + assets, mas não preparava esse cache. Resultado possível: UI do editor instalada e renderer universal indisponível.

4. **O renderer legado ainda existe por design.**
   Ele permanece apenas como compatibilidade explícita para cards que não podem ser convertidos. Não deve ser interpretado como renderer padrão.

## Correções aplicadas na 4.5

### 1. Template visual canônico congelado

Novo contrato:

`contracts/m9/card_editor_default_v1_1.json`

Ele é derivado do `const DEFAULT` real do `FR_CARD_EDITOR_UNIVERSAL_v1.1.0/index.html` e contém:

- 21 campos editoriais;
- 29 linhas do grid;
- geometria 941 × 1672;
- textos fixos/variáveis do template;
- tipografia, pesos, alinhamentos e efeitos;
- grid ativo;
- layers ativos;
- configuração de mídia central.

`card_migration_v99._base_state()` agora carrega esse contrato, substituindo somente paths do editor por `AssetRef` validado.

### 2. Upgrade automático M9.9.0 → M9.9.1

- `MIGRATION_VERSION`: `9.9.1`.
- `DEFINITION_VERSION`: `2`.
- projetos previamente migrados são reavaliados;
- título/subtítulo e assets são preservados;
- edição detectável em campos/linhas do estado reduzido é preservada;
- elementos que ainda estavam exatamente no baseline defeituoso 9.9.0 passam ao layout canônico do editor 1.1.0;
- IDs e placement continuam preservados;
- source plan/mídia continuam imutáveis.

### 3. Font-cache obrigatório e verificável

Novo instalador:

`scripts/install_card_editor_fonts.py`

O `install.sh` agora:

1. instala o componente modular do editor;
2. lê `contracts/m9/font_sources_v1.json`;
3. reutiliza fontes locais quando o SHA-256 confere;
4. quando ausentes, obtém as fontes OFL diretamente do commit fixado do repositório oficial `google/fonts`;
5. verifica SHA-256 antes de publicar no cache local;
6. instala em `local_components/fr-card-editor/1.1.0/font-cache`;
7. somente então declara `fr-universal-card` pronto.

As fontes não são embutidas nem redistribuídas neste pacote.

### 4. Instalação fail-closed

Na 4.5, ausência do `FR_CARD_EDITOR_UNIVERSAL_v1.1.0` não gera mais uma instalação aparentemente completa. O instalador encerra com erro claro, pois o editor universal é requisito da versão.

### 5. Identificação da versão

- `VERSION`: `4.5.0-candidate`;
- `APP_VERSION`: `4.5.0-candidate`;
- Studio/server: `4.5.0-candidate`;
- atalhos locais: Studio 4.5;
- release manifest/empacotador atualizados.

## Validação feita neste pacote

- `py_compile` dos módulos alterados: aprovado.
- `bash -n install.sh`: aprovado.
- extração do DEFAULT real do editor: 21 fields / 29 lines.
- teste direto de `_base_state()`: grid e campos do editor canônico ativos.
- teste direto de upgrade de instância reduzida v1 → definição v2: aprovado, preservando título/subtítulo e ativando o template real.
- suíte M9 parcial: testes iniciais passaram; um teste que consulta `git ls-files` falhou somente porque o ZIP fornecido não contém `.git`.
- a suíte `card_migration_v99_test.py` iniciou com sucesso, mas excedeu a janela de execução disponível neste ambiente; não é declarada como totalmente aprovada aqui.

## Critério operacional após instalação

Após instalar e abrir um projeto antigo, o esperado é:

- `CARD_MIGRATION_V99.json` com `migration_version=9.9.1`;
- definição `universal/migrated-legacy-9x16` versão `2`;
- card migrado com `renderer_id=fr-universal-card`;
- template com 21 campos e 29 linhas, não somente título/subtítulo;
- Card Editor abrindo o mesmo estado que será renderizado;
- save → preview → reabrir preservando estado;
- F1–F6 somente quando houver `compatibility_fallback` nominal no relatório.

## Instalação local recomendada

```bash
cd /home/romeu/FR-AutoEdite/FR_AUTOEDITE_4.0
chmod +x install.sh fr-autoedite
./install.sh
fr-autoedite --version
fr-autoedite studio
```

A primeira instalação 4.5 pode precisar de acesso à internet para preparar o font-cache pinado. Depois de validado, o cache local é reutilizado.

## Verificação rápida no projeto

```bash
cat _CONTROLE/CARD_MIGRATION_V99.json | grep -E 'migration_version|renderer_id|status'
cat _CONTROLE/CARD_STATE_V2.json | grep -E 'definition_version|renderer_id' | head
```

O valor decisivo é `fr-universal-card`; cards em fallback devem possuir causa explícita no relatório.
