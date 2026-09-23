# FR AutoEdite 3.3.1 — guia direto

## Atualizar sem perder projetos

Os projetos permanecem em `~/FR-AutoEdite/Studio`. O atualizador substitui
somente o programa instalado e cria um backup da versão anterior.

No terminal, entre na pasta extraída e execute:

```bash
chmod +x ATUALIZAR_FR_AUTOEDITE_3.3.1.sh
./ATUALIZAR_FR_AUTOEDITE_3.3.1.sh
```

Ao terminar, confirme e abra:

```bash
fr-autoedite --versao
fr-autoedite studio
```

O resultado correto da primeira linha é `FR AutoEdite 3.3.1`.

## O que mudou no Studio

- **Revisar filme:** player integrado para entregas, vídeos sociais e cenas da
  timeline, com avanço de 5 segundos e de um quadro.
- **Log lateral:** mostra porcentagem, mídia atual, tempo, cancelamento e nova
  tentativa. O estado também fica salvo em `_CONTROLE/STUDIO_JOB_STATUS.json`.
- **Retomada:** proxies, miniaturas e segmentos concluídos são reutilizados.
- **Galeria:** reúne originais, cards, entregas e vídeos sociais.
- **Gerenciar:** limpa apenas caches regeneráveis, usando lixeira restaurável.
  Originais, entradas, Takeout, histórico, planos e configurações ficam
  protegidos.
- **Cards:** masters 4K com mármore verde-petróleo/esmeralda, dourado acetinado,
  laranja térmico e logotipo oficial remasterizado.

## Corrigir o projeto que falhava em M0036C003

Depois de atualizar, abra o mesmo projeto e use novamente **Validar e aplicar**.
O 3.3.1 aceita o tempo local da cena e o tempo absoluto do vídeo-pai, converte
internamente para o formato correto e registra o reparo automático.

Se uma preparação anterior parou em `63/64`, clique novamente em **Preparar**.
Os 63 itens concluídos são reutilizados; o log lateral identifica exatamente o
item atual. Não apague proxies antes dessa retomada.

## Limpeza segura

Em **Gerenciar**, selecione somente os itens oferecidos em **Limpeza
recomendada**. A primeira ação apenas os move para a lixeira interna. Use
**Restaurar última limpeza** se necessário.

Esvaziar a lixeira é permanente e exige digitar exatamente
`APAGAR DEFINITIVAMENTE`.

