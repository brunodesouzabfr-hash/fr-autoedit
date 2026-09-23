# FR AutoEdite — migração 4.0, candidato de integração

## Estado e evidências

Esta entrega é um candidato de homologação, não uma publicação automática em
produção. O código foi preparado em cópia isolada; não houve alteração na
instalação do usuário, em projetos reais, push, merge ou deploy. Os testes
sintéticos e de regressão descritos neste relatório foram executados. A
aprovação visual humana e o teste na máquina de destino continuam obrigatórios.

Base selecionada: `FR_AUTOEDITE_3.4.0_STUDIO.zip`, SHA-256
`a673324b832536e2adfb24b1b66df3955e387867897131060283ed77e7ab3e9b`.
O `VERSION` recebido contém 3.4.0. O TAR anterior também contém 3.4.0,
mas não é equivalente: o ZIP contém ready_video.py, style_engine.py e os
13 assets de serviço. A base é o ZIP mais recente, não uma reconstrução
a partir do manual 3.0. Sem metadados Git no pacote, branch/HEAD/estado
do repositório do usuário não são verificáveis a partir destes anexos.

## Fase 0 — auditoria estática antes da refatoração

| Arquivo / função na base | Evidência e consequência | Destino |
|---|---|---|
| templates/card_style.json | material_backgrounds e material_treatment ativam mármore; título vazado e contatos em todos os cards | sistema v2 separado, legado preservado |
| fr_autoedite.card_image | delega service_cards e usa desenho monolítico; não possui kernel quadrado explícito | motor por famílias e grid |
| fr_autoedite._material_card_background | ImageOps.fit + ajuste de saturação da base material | somente caminho legado |
| fr_autoedite.paste_service_symbol | ImageOps.fit, máscara circular e arcos decorativos sobre identidade | normalização sem recorte destrutivo |
| fr_autoedite.draw_hollow_centered | outline é gramática estrutural antiga | títulos sólidos no v2 |
| fr_autoedite.draw_contact_chips | WhatsApp verde fora da paleta e repetição de contatos | F6 e ícones funcionais |
| fr_autoedite.branded_overlay_image | top 3,5%; margem inferior sem grid Reels; motif genérico | etiquetas de prancheta |
| fr_autoedite.render_card_segment | zoom até 1,055, movimento por incremento linear; raster único não permite entrada por camada | composição de camadas dedicada |
| fr_autoedite.generate_card_previews | já possui staging e assinatura; não reimplementar como se inexistente | ampliar dependências, preservar contrato de galeria |
| fr_autoedite.render_reel_cover | usa card_image, portanto herda sistema da família | integração pelo mesmo ponto de entrada |
| social_contract.render_carousel | cover/outro mapeados; demais slides caem em phase | respeitar mídia/comparação e não confundir enums |
| service_cards.draw_service_motif | blueprint/pagination/foundation compartilham desenho; layers/material_macro também | 13 diagramas com geometria distinta |
| service_cards.render_service_card | não tem numeração da coleção nem kernel; painéis por orientação não são famílias F1–F6 | catálogo e renderer novo |
| service_cards.text_fit | encolhe até 9 px e quebra palavras longas | limite legível e erro explícito |
| ready_video.overlay_image | wrap_pixel(... )[:4] trunca texto; etiqueta arredondada genérica | ajuste medido, nunca truncamento silencioso |
| ready_video._safe_margin | converte margens assimétricas em escalar único | área retangular separada por orientação |
| ready_video._ffmpeg_compose | fps forçado e setpts; investigar VFR e sincronismo antes de certificar preservação | testes de duração, FPS e áudio exigidos |
| style_engine.asset_index | instalado significa arquivo não vazio; falta aprovação de identidade e publicação | manifesto de integridade + estado editorial |
| local_analysis | análise técnica já existe; não constitui compreensão semântica da obra | preservar, integrar por adapter |
| master_contract | contrato v2, revisão/transação já existem | v4 deve reaproveitar transação e validar migração |
| studio | jobs, versões, assets, preview e ready_video já existem | expandir sem substituir acervo por seleção |
| create_thumbnail/create_thumbnail_at | miniaturas técnicas, não peças publicitárias; não devem receber decoração | preservar |
| create_contact_sheets/create_master_contact_sheet | pranchas de análise, não transformar referências em peças falsas | preservar e documentar exceção funcional |
| media_frames.extract_reference | extração real de frames, sem redesenho | preservar |
| render_joins.concat_segments | união de mídia, não gerador de arte; depende de base de tempo uniforme | preservar e testar |

O inventário AST completo de arquivos/funções é gerado por
`scripts/auditar_base.py`. Ele distingue inventário mecânico de julgamento
visual; não atribui automaticamente uma infração a toda função Python.
Não houve auditoria dinâmica nem comprovação de qualidade final nesta etapa.

## Entradas lidas

- Manual mestre v2: autoridade visual.
- Manual de criação v1: diagnóstico e contexto.
- Consolidação generativa: contexto subordinado ao v2.
- Textos de execução (2)(6) e (2)(7): arquitetura e 18 entregáveis.
- Manual operacional DOCX 3.0: histórico; código 3.4.0 prevalece.
- Guia rápido 3.4: fluxo de operação.
- ZIP 3.4.0: código e assets de execução.
- TAR anterior: comparação de inventário, não base aplicada.
- Elétrica, Hidráulica, Instalação e Manutenção: imagens agora disponíveis,
  sem redesenho. Não assumir ausência por erro antigo de upload.

## Conflitos resolvidos

1. Mármore e outline do v1 cedem ao petróleo fosco e hierarquia do v2.
2. Contatos e Cormorant não se espalham por todas as famílias; Cormorant
   é restrita a F1/F6. Não inventar informações de contato.
3. Rodapé 88–94% do wireframe invade a margem inferior de 250 px. A área
   segura prevalece; o rodapé é reposicionado dentro dela.
4. 6%+4% não substitui margens verticais explícitas 72/140/250 em 1080x1920.
5. Originais permanecem byte a byte; normalizados ficam em diretório separado.
   Adicionar canvas transparente não autoriza remover fundo ou cortar aro.
6. Ready_video não ganha permissão de corte por permitir extensão de duração.
7. A regra de silêncio não autoriza mutilar áudio original preservado.
8. Corpo humano e rationale não são texto de locução ou overlay.
9. Carousel kind permanece cover/outro/card/media/before_after; não recebe
   service_card nem tipos de famílias F1–F6.
10. Veracidade semântica não é demonstrada por regex. Fonte/confirmado_por
    permite rastrear a afirmação; revisão humana continua necessária.
11. A regra original de pedir aprovação por fase foi substituída pela
    autorização mais recente de prosseguir sem confirmação intermediária.

## Preservação e rollback

Nenhum arquivo original de entrada foi alterado. Os caminhos da CLI e as
pastas de projeto da base continuam sendo a referência. O sistema antigo
não será apagado para simular refatoração; os pontos de extensão retornam
ao legado quando v2 não está ativo. A cópia de distribuição deve ser
instalada lado a lado até passar pelos testes. Não executar reset --hard,
git clean, limpeza de Studio ou migração destrutiva.

Uma reversão deve trocar somente a instalação de código pela cópia 3.4.0
preservada. Nunca restaurar código por cima de originais de projeto.
Roteiros v4 não são silenciosamente aceitos pelo motor v2.

## Fases 1–2 — arquitetura e fundação

- `app/fr_v4/` concentra grid, tipografia, renderer, famílias, diagramas,
  motion, contrato, validadores, adapters e módulos editoriais.
- `app/fr_autoedite.py` permanece fachada pública para preservar os comandos
  e delega ao sistema v2 quando ativo.
- `templates/card_style.json` ganhou schema 4 e defaults v2 sem remover os
  campos legados.
- o formato 9:16 usa 72 px laterais, 140 px superiores, 250 px inferiores,
  12 colunas, gutter 24 px e baseline 8 px; 1:1 é remontagem por kernel.

## Fase 3 — famílias e 13 serviços

- F1 capa, F2 etapa, F3 serviço, F4 detalhe/dado, F5 extra e F6 encerramento
  compartilham uma gramática única, mas mantêm composição própria.
- os 13 serviços possuem código, numeração de coleção e diagrama técnico
  distinto: STR-WALL, AUT-MAKE, MEP-ELE, MEP-HYD, MEP-LUX, FIT-INST,
  OPS-MNT, MOB-JOIN, FIN-PNT, EVT-PROD, ENG-3D, FIN-REV e FIN-TEX.
- todos os 13 medalhões foram encontrados na base recebida. Os originais
  permanecem separados e os derivados normalizados ficam em
  `assets/service-medallions/normalized/`.
- seis medalhões de fonte opaca são preservados sem segmentação inventada e
  carregam aviso de revisão visual; nenhum está pendente.

## Fase 4 — contrato Markdown↔IA

- contrato 4.0.0 com YAML imutável, corpo humano e um único JSON delimitado;
- schema Draft 2020-12, validador stdlib restrito ao schema distribuído,
  Pydantic v2 opcional e fingerprint do manifesto;
- publicação transacional em `_ROTEIROS/v4/` após validação;
- migração conservadora mantém `legacy_payload` em vez de descartar decisões;
- enums de carrossel permanecem separados dos kinds de overlay.

## Fase 5 — sistema editorial profissional

Foram implementados módulos locais e determinísticos para cor, áudio, captions,
capítulos, presets, metadados, versionamento, workflow e busca estrutural.
Esses módulos não afirmam análise semântica automática, transcrição nem
previsão de viralização. Whisper, visão avançada e publicação permanecem fora
do caminho obrigatório.

## Fase 6 — adapters

FFmpeg, FFprobe e Pillow têm operações reais e autoteste. O catálogo Tier 1/2
detecta extras sem executá-los; Tier 3 é apenas metadado. A ausência de MoviePy
não impede o Studio: motion e vídeo pronto usam FFmpeg. Nenhum adapter instala
software, baixa pesos ou acessa rede.

## Fase 7 — integração CLI, ready_video e Studio

- `--version` e `--versao` retornam `4.0.0-candidate`;
- `cards` aceita `--sistema-v2` e `--legacy-v1`;
- a assinatura de prévia inclui plano, estilo, style pack, serviço e assets;
- vídeo pronto utiliza overlays v2 medidos e mantém original intocado;
- saídas temporárias motion são verificadas por FFprobe antes da publicação;
- Studio recebeu identificação 4.0, mantendo endpoints, jobs e compatibilidade
  da base.

## Fase 8 — geração e QA

- 56 cards: 28 em 9:16 e 28 em 1:1;
- 13 diagramas técnicos;
- três provas motion F3 em H.264, 1080×1920, 24 fps e 3 segundos;
- 56 cards com score automático 100/100 e nenhum asset pendente;
- 12 ocorrências de aviso de fundo opaco preservado, correspondentes a seis
  medalhões nos dois formatos;
- a aprovação visual permanece `REVIEW_REQUIRED`, mesmo com score técnico ≥90.

## Fase 9 — distribuição e rollback

- `INSTALAR_FR_AUTOEDITE_4.sh` instala lado a lado com backup do destino;
- `install.sh` continua sendo a instalação normal do usuário;
- scripts de geração, motion, exportação e finalização reproduzem a entrega;
- a distribuição exclui `Studio/`, projetos, mídia pessoal, proxies, renders,
  `.env`, credenciais, caches Python e artefatos temporários;
- rollback restaura apenas código; nunca substitui a pasta de projetos.

## Validação executada

Consulte `docs/RELATORIO_VALIDACAO_4_0.md`. Em resumo: smoke integral aprovado,
smoke visual aprovado, testes de ready_video/contrato/cache/Studio aprovados,
compilação Python aprovada e ZIPs submetidos a teste CRC. O comando exato
`python -m pytest tests` não pôde ser executado porque o runtime não contém
pytest; isso é registrado como dependência de desenvolvimento ausente, não
como teste aprovado. O pacote não contém metadados `.git`, portanto
`git diff --check` é não aplicável nesta cópia.
