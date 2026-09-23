# Guia rápido — FR AutoEdite Studio 3.4.0 (compatibilidade)

## Primeira execução

```bash
./install.sh
fr-autoedite studio
```

O navegador abre a Central FR. Siga as oito etapas da esquerda para a direita:

1. **Importar**
   - clique em **+ Novo**;
   - envie o ZIP comum de fotos e vídeos; ou use **Google Takeout + JSON** para
     recuperar datas ajustadas no Google Fotos;
   - preencha e salve o contexto dentro da própria página;
   - opcionalmente envie intro e/ou outro em foto ou vídeo.

2. **Montagem**
   - para começar sem dúvidas, use **Profissional FR**;
   - marque Filme institucional, Filme limpo e os Reels desejados;
   - use **Proxies** durante a revisão e **Originais** na entrega.

3. **Cards e marca**
   - mantenha **Site FR · Luxo forjado 60/20** para o padrão atual;
   - ative o card de serviço somente se fizer sentido na abertura;
   - escolha 3D, Revestimentos, Alvenaria, Produções, Pintura, Móveis,
     Textura, Criações ou Iluminação;
   - clique em **Gerar prévias agora**. Os símbolos devem aparecer em círculos
     perfeitos, sem deformação oval.

4. **Efeitos e áudio**
   - selecione as transições permitidas;
   - ative estabilização em **Automática** para a primeira prova;
   - se desejar, ative **Time-lapse editorial** e defina velocidade, duração e
     número máximo de vídeos acelerados.

5. **Enviar à IA**
   - clique em **Gerar Markdown**;
   - envie o arquivo `01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE_IA.md` para a IA;
   - não edite os arquivos marcados como **NÃO EDITAR**;
   - envie cada `FR_AUTOEDITE_LOTE_###.zip` como mídia, sem juntá-los;
   - receba o Markdown respondido, anexe-o e clique em **Validar e aplicar**.

   A versão 3.4.0 mostra a auditoria antes de aplicar, permite salvar
   alternativas em `_ROTEIROS/` e oferece **Zerar definições e manter mídias**.

6. **Revisar filme**
   - assista às entregas e cenas no player integrado;
   - arraste cenas, ajuste início/duração, transição, estabilização e
     time-lapse;
   - gere o **Rascunho rápido** e assista do início ao fim.

7. **Galeria e Gerenciar**
   - visualize originais, cards, entregas e vídeos sociais na galeria;
   - use somente a lista de limpeza recomendada; arquivos vão primeiro para
     uma lixeira restaurável;
   - acompanhe processos pelo log lateral, com arquivo atual, progresso,
     cancelamento e nova tentativa.

8. **Editar Reels**
   - selecione 30s, 60s ou 90s;
   - mantenha pelo menos uma cena de início e uma de resultado final;
   - altere cada Reel sem modificar o filme principal;
   - clique em **Salvar Reel**.

9. **Entregar**
   - troque a origem para **Originais** e escolha a qualidade final;
   - renderize master e pacote social;
   - execute **Auditar arquivos**;
   - assista tudo antes de publicar ou enviar ao Drive.

## O que editar e o que apenas enviar à IA

| Arquivo | Você edita? | O que fazer |
|---|---:|---|
| `_ENVIAR_IA/00_COMECE_AQUI_O_QUE_EDITAR_E_ENVIAR.md` | Não | Leia e anexe para orientar a IA. |
| `_ENVIAR_IA/01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE_IA.md` | Sim, pela IA | A IA altera somente o JSON marcado e devolve o mesmo Markdown. |
| `_ENVIAR_IA/02_NAO_EDITAR_APENAS_ENVIAR_PROMPT.md` | Não | Anexe como instrução fixa. |
| `_ENVIAR_IA/03_NAO_EDITAR_LISTA_DE_LOTES.txt` | Não | Use para conferir os lotes. |
| `pacote_chatgpt/FR_AUTOEDITE_LOTE_###.zip` | Não | Envie como mídia, um lote por anexo. |

## Google Takeout em quatro ações

1. No Google Takeout, exporte somente Google Fotos e o álbum desejado.
2. Em **Importar**, selecione o ZIP em **Google Takeout + JSON**.
3. Clique **Enviar Takeout** e **Restaurar datas e criar ZIP**.
4. Leia `_TAKEOUT/01_RELATORIO_GOOGLE_TAKEOUT.md`; depois prepare normalmente.

O Takeout original nunca é alterado. O Studio cria o novo
`_ENTRADA/FR_AUTOEDITE_ENTRADA.zip` com as datas recuperadas.

## Regra de segurança

O FR AutoEdite não apaga os originais. Planos substituídos ficam em
`_HISTORICO/`. Nenhuma automação ou IA substitui a conferência visual da
master e de cada Reel.
