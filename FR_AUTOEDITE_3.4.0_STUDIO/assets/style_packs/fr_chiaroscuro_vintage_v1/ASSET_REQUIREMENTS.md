# Requisitos de assets — FR Chiaroscuro Vintage Luxury V1

Este diretório é um contrato de indexação. Os arquivos listados abaixo serão
produzidos externamente; os fallbacks procedurais do FR AutoEdite continuam
ativos enquanto um slot opcional estiver vazio. Não coloque vídeos de projeto,
proxies, renders, credenciais ou materiais de cliente neste Style Pack.

## Regras gerais

- Cor: sRGB, perfil incorporado ou removido de forma consistente.
- PNG: RGBA, fundo transparente, sem margens externas invisíveis e sem texto
  rasterizado quando o texto precisar ser editável.
- Linhas: mínimo de 3 px no master vertical; brilho deve permanecer sutil.
- Área segura vertical: 160 px nas laterais, 240 px no topo e 320 px na base.
- Área segura horizontal: 240 px nas laterais, 160 px no topo e 220 px na base.
- Logo: preservar proporção, simetria e transparência; nunca deformar.
- Não usar glitch, flash, bloom plástico ou sombras esmagadas.
- A arte de serviço é uma camada sutil e precisa funcionar sobre qualquer card.

## Arquivos comuns obrigatoriamente nomeados

Todos os slots desta V1 são opcionais porque possuem fallback local. Para que
o indexador marque o slot como instalado, use exatamente estes nomes:

| Asset ID | Arquivo | Quadro | Formato |
|---|---|---:|---|
| `common_editorial_vertical` | `cards_common/common_editorial_vertical_2160x3840.png` | 2160 × 3840 | PNG RGBA |
| `common_editorial_horizontal` | `cards_common/common_editorial_horizontal_3840x2160.png` | 3840 × 2160 | PNG RGBA |
| `balloon_technical_vertical` | `balloons/balloon_technical_vertical_1600x480.png` | 1600 × 480 | PNG RGBA |
| `balloon_technical_horizontal` | `balloons/balloon_technical_horizontal_1920x360.png` | 1920 × 360 | PNG RGBA |
| `frame_vertical` | `frames/frame_chiaroscuro_vertical_2160x3840.png` | 2160 × 3840 | PNG RGBA |
| `frame_horizontal` | `frames/frame_chiaroscuro_horizontal_3840x2160.png` | 3840 × 2160 | PNG RGBA |
| `background_chiaroscuro_vertical` | `background_motifs/background_chiaroscuro_vertical_2160x3840.png` | 2160 × 3840 | PNG RGBA |
| `background_chiaroscuro_horizontal` | `background_motifs/background_chiaroscuro_horizontal_3840x2160.png` | 3840 × 2160 | PNG RGBA |
| `texture_gold_brushed` | `textures/texture_gold_brushed_2048.png` | 2048 × 2048 | PNG RGB, seamless |
| `texture_patina_petroleum` | `textures/texture_patina_petroleum_2048.png` | 2048 × 2048 | PNG RGB, seamless |
| `logo_primary` | `logo/fr_logo_primary_bone_gold_1600.png` | até 1600 × 1600 | PNG RGBA |

O balão deve ter o corpo visual dentro do próprio quadro, com pelo menos 96 px
de respiro para sombra. Não desenhar texto, ícones de contato ou logo no balão.

## Camadas de serviço

Cada arquivo abaixo é um overlay vertical 2160 × 3840 em PNG RGBA. Mantenha
60–85% do quadro transparente e evite informação importante na área central do
vídeo. A aplicação redimensiona proporcionalmente para horizontal/quadrado.

| Serviço | Arquivo exato | Motivo |
|---|---|---|
| Projetos 3D | `cards_service/service_projetos_3d_overlay_2160x3840.png` | grid, planta, perspectiva |
| Pintura | `cards_service/service_pintura_overlay_2160x3840.png` | pigmento e matéria |
| Textura | `cards_service/service_textura_overlay_2160x3840.png` | relevo e luz rasante |
| Revestimentos | `cards_service/service_revestimentos_overlay_2160x3840.png` | paginação, junta, corte |
| Móveis | `cards_service/service_moveis_overlay_2160x3840.png` | marcenaria, fibra, encaixe |
| Alvenaria | `cards_service/service_alvenaria_overlay_2160x3840.png` | módulos, bloco, prumo |
| Produções | `cards_service/service_producoes_overlay_2160x3840.png` | palco, luz, movimento |
| Criações | `cards_service/service_criacoes_overlay_2160x3840.png` | autoria e protótipo |
| Iluminação | `cards_service/service_iluminacao_overlay_2160x3840.png` | fachos e penumbra |
| Elétrica | `cards_service/service_eletrica_overlay_2160x3840.png` | cobre e trajetos luminosos |
| Hidráulica | `cards_service/service_hidraulica_overlay_2160x3840.png` | fluxo e tubulação |
| Instalação | `cards_service/service_instalacao_overlay_2160x3840.png` | encaixes e precisão |
| Manutenção | `cards_service/service_manutencao_overlay_2160x3840.png` | inspeção e checklist |

## Tipografia

Os arquivos de referência podem ser colocados em `typography/`, mas as fontes
executáveis pertencem a `assets/fonts/` e devem respeitar suas licenças.

- Títulos: Stardos Stencil.
- Corpo: Rokkitt.
- Informação técnica: Share Tech Mono.
- Acento editorial pontual: Cormorant Garamond.

## Animação futura

Esta V1 indexa imagens estáticas. Uma arte com movimento deverá ser entregue em
uma revisão do manifesto, com nome, codec, alfa e duração definidos antes de ser
aceita. Não renomeie GIF/WebM como PNG. O render atual anima opacidade; nesta
V1, a posição permanece fixa e entradas direcionais degradam para fade suave.
Ele não interpreta animação embutida nos slots.

## Como validar

No Studio, use **Reindexar assets**. Um `asset_id` informado explicitamente no
Roteiro Mestre só será aceito quando o arquivo correspondente existir e tiver
conteúdo. O editor de overlays lista somente os slots instalados. Cards de
serviço usam automaticamente o slot associado a `service_key`; cards comuns,
balões e logo podem selecionar o respectivo `asset_id`. O texto permanece uma
camada editável da aplicação. Se `asset_id` ficar vazio, o fallback procedural
sóbrio é usado.
