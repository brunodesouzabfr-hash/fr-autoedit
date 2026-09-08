# FR AutoEdite 3.4.0 — guia de operação da Central da IA

## Instalar

```bash
tar -xzf FR_AUTOEDITE_3.4.0_STUDIO_FINAL.tar.gz
cd FR_AUTOEDITE_3.4.0_STUDIO
chmod +x install.sh fr-autoedite ATUALIZAR_FR_AUTOEDITE_3.4.0.sh
./install.sh
fr-autoedite studio
```

O instalador cria backup da instalação anterior e não toca nos projetos em
`~/FR-AutoEdite/Studio`.

## Fluxo da IA

1. Crie ou abra um projeto e execute a preparação com proxies ou originais.
2. Em **Enviar à IA**, informe no campo de contexto o assunto do material e
   clique **Gerar Roteiro Mestre Markdown**.
3. Baixe o arquivo `01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE_IA.md` e envie-o à IA
   junto com o contexto. O prompt já informa que a IA é responsável por todas
   as decisões: duração, cortes, ordem, recortes repetidos, cards, fotos,
   frames, antes/depois, tipografia, transições, áudio, retenção e CTA.
4. Anexe de volta exatamente um arquivo `.md`. O Studio valida primeiro e
   mostra uma auditoria por bloco. Erros aparecem com correção sugerida; o
   botão **Aplicar** só é liberado quando o contrato está íntegro.
5. Revise o rascunho com proxies. A aplicação grava uma cópia de segurança e
   nunca substitui os originais.

## Roteiros independentes e reset

- **Salvar como roteiro** congela a definição atual em `_ROTEIROS/`.
- **Restaurar** troca a definição ativa sem alterar outras versões.
- **Apagar definições** move as decisões para `_HISTORICO/RESET_*` e mantém
  mídias, inventário, proxies, metadados e assinaturas de origem.
- Uma renderização usa sua própria fotografia de decisões em
  `_RENDERIZACOES/`; renderizar o roteiro B não reescreve o roteiro A.

## Compatibilidade de cards

Escolha o serviço no painel **Cards e marca**. O catálogo seleciona a estrutura
visual adequada: wireframe/evolução para 3D, camadas para pintura, macro de
material para textura, paginação para revestimentos, encaixes para móveis,
sequência de obra para produção/criação, fundação para alvenaria e linhas de
luz para iluminação. É possível revisar ou substituir a decisão no Markdown.

## Limites e revisão humana

O motor não publica automaticamente nem promete viralização. A IA recebe apenas
as mídias e metadados fornecidos; não deve inventar resultados, clientes,
medidas ou depoimentos. Antes da entrega, confira o player, a legibilidade em
9:16, os direitos de uso e o CTA.
