# Auditoria de configurações — FR AutoEdite 3.3

O Studio visual é o questionário principal. Abra com:

```bash
fr-autoedite studio
```

As escolhas são salvas em `QUESTIONARIO_RESPONDIDO.json`. O contexto e os
fatos declarados são a fonte de verdade; nomes, datas e pontuação técnica são
apenas evidências auxiliares.

## Entrada mínima

1. ZIP com fotos e vídeos.
2. Contexto do projeto.

No Studio, ambos ficam em `_ENTRADA/`. Pelo terminal:

```bash
fr-autoedite novo --zip ARQUIVO.zip --contexto CONTEXTO.md
```

Uma sequência clara pode ser escrita assim:

```text
1. CONCEPÇÃO | o que precisa aparecer e o que é fato confirmado
2. EXECUÇÃO | decisão, material ou serviço visível
3. RESULTADO | como a entrega deve ser mostrada
```

## Montagem e qualidade

```json
"edition": {
  "order_mode": "automatico",
  "target_duration_sec": 360,
  "average_clip_duration_sec": 6,
  "max_video_excerpt_sec": 14,
  "still_duration_sec": 4,
  "phase_card_duration_sec": 4,
  "max_media_segments": 80,
  "format": "vertical",
  "quality_preset": "full_hd",
  "render_source": "originals",
  "fps": 24
}
```

`order_mode`: `automatico`, `cronologico`, `alfabetico` ou `aleatorio`.
`quality_preset`: `draft`, `hd`, `full_hd`, `2k`, `4k`, `original` ou
`custom`. `render_source`: `proxies` para revisão ou `originals` para master.

## Reels com arco completo

```json
"social": {
  "enabled": true,
  "reels_enabled": true,
  "reel_durations_sec": [30, 60, 90],
  "reel_sampling_mode": "beginning_middle_end",
  "always_include_beginning": true,
  "always_include_ending": true,
  "minimum_source_coverage": 0.85,
  "manual_plans_preserved": true,
  "stories_enabled": true,
  "story_part_duration_sec": 15,
  "carousel_enabled": true,
  "carousel_slides": 8,
  "create_reel_covers": true
}
```

Cada plano social é salvo separadamente em `social/EDIT_PLAN_REEL_30.json`,
`social/EDIT_PLAN_REEL_60.json` etc. O editor visual permite incluir/excluir,
reordenar e alterar corte, duração, texto, transição e estabilização de cada
cena. Esses ajustes não modificam `EDIT_PLAN.json`.

## Card de serviço opcional

```json
"service_intro": {
  "enabled": true,
  "service_key": "iluminacao",
  "duration_sec": 3.5,
  "position": "after_intro",
  "include_in_reels": true,
  "custom_title": "",
  "custom_body": ""
}
```

`service_key` aceita `projetos_3d`, `revestimentos`, `alvenaria`, `producoes`,
`pintura`, `moveis`, `textura`, `criacoes` ou `iluminacao`. Título e corpo em
branco usam o texto do catálogo.

## Intro e outro personalizados

```json
"external_intro_outro": {
  "intro_enabled": true,
  "intro_path": "_ENTRADA/INTRO_PERSONALIZADA.mp4",
  "intro_duration_sec": 4,
  "intro_mode": "before_card",
  "intro_preserve_audio": true,
  "intro_include_in_reels": true,
  "outro_enabled": true,
  "outro_path": "_ENTRADA/OUTRO_PERSONALIZADO.png",
  "outro_duration_sec": 4,
  "outro_mode": "after_card",
  "outro_preserve_audio": true,
  "outro_include_in_reels": true,
  "include_in_clean_version": false
}
```

Os modos de intro são `before_card`, `after_card` e `replace_card`; os de outro
são `before_card`, `after_card` e `replace_card`. O Studio preenche os caminhos
ao receber o upload.

## Cards, balões e marca

```json
"cards": {
  "persistent_logo": true,
  "persistent_bubble": true,
  "show_contacts": true,
  "show_contact_icons": true,
  "show_pinterest": true,
  "show_site": true,
  "style_preset": "site_fr_luxo",
  "layout": "site_editorial",
  "bubble_style": "glass",
  "intro_animation": "forge_reveal",
  "service_animation": "forge_reveal",
  "animation": "soft_zoom",
  "outro_animation": "soft_zoom",
  "qr_code_on_outro": false,
  "qr_code_target": "https://wa.me/5511990021603"
}
```

Presets: `site_fr_luxo` (padrão), `forja_tecnica`, `editorial_osso`,
`cinema_petroleo` e `blueprint_3d`. Balões: `glass`, `solid`, `outline` e
`minimal`. A logo é independente do balão e permanece fixa quando
`persistent_bubble` é falso.

`site_fr_luxo` usa a regra visual 60/20/20: 60% verde-petróleo para estrutura,
20% laranja para ações e pontos focais e 20% osso/dourado para contraste. Os
símbolos de serviço são centralizados sem esticar e recebem máscara circular
perfeita, inclusive quando a imagem-fonte não é quadrada.

## Fontes e publicação

```json
"editing_brief": {
  "auto_generate": true,
  "overlay_title_font": "StardosStencil-Bold.ttf",
  "overlay_body_font": "Rokkitt-Regular.ttf",
  "overlay_technical_font": "ShareTechMono-Regular.ttf",
  "publication_title": "",
  "publication_caption": "",
  "hashtags": [],
  "complementary_information": ""
}
```

Essas fontes controlam somente textos sobre fotos/vídeos. As fontes dos cards
continuam protegidas no `CARD_STYLE.json`.

## Efeitos, estabilização e áudio

```json
"visual_effects": {
  "transitions": ["fade", "zoom_swipe", "smooth_left", "circle_open"],
  "transition_duration_sec": 0.45,
  "enable_stabilization": true,
  "stabilization_mode": "auto",
  "stabilization_strength": "medium",
  "color_lut": "",
  "ken_burns_on_images": true,
  "speed_ramping": false,
  "editorial_timelapse": {
    "enabled": false,
    "speed_factor": 6.0,
    "minimum_source_duration_sec": 18.0,
    "output_duration_sec": 4.0,
    "max_segments": 4,
    "mute_original_audio": true
  }
},
"audio_design": {
  "auto_ducking": true,
  "enable_sfx": true,
  "sfx_volume": 0.3,
  "tts_voiceover": false,
  "tts_language": "pt-BR"
}
```

`stabilization_mode`: `auto`, `all` ou `manual`. Intensidade: `light`,
`medium` ou `strong`. LUT exige arquivo `.cube`; TTS exige `espeak-ng`.

O time-lapse editorial seleciona no máximo `max_segments` vídeos longos,
consome `output_duration_sec × speed_factor` segundos do original e exibe o
resultado no tempo definido. Cada cena pode ser ligada/desligada e ter sua
velocidade alterada na timeline. A opção não se aplica a fotos.

## Roteiro Mestre Markdown

`_ENVIAR_IA/01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE_IA.md` é a configuração
completa e portável para qualquer IA. É o único arquivo dessa pasta que deve
ser editado e devolvido. O JSON entre os marcadores do documento pode
alterar filme, Reels, cards, tempos, texto sobre mídia, legenda, publicação,
fontes, transições, estabilização e time-lapse. A importação rejeita IDs
inexistentes, valores proibidos e cortes fora dos limites antes de escrever
qualquer plano.

```bash
fr-autoedite gerar-roteiro-ia --projeto PROJETO
fr-autoedite aplicar-roteiro-ia --projeto PROJETO --arquivo RESPOSTA.md
```

A etapa **Enviar à IA** mostra, em uma única página, quatro papéis:

| Rótulo | Ação correta |
|---|---|
| `COMECE AQUI` | ler e enviar sem editar |
| `EDITAR E DEVOLVER` | a IA altera e devolve este Markdown |
| `NÃO EDITAR · APENAS ENVIAR` | anexar como instrução fixa |
| `ENVIAR COMO MÍDIA` | anexar os lotes ZIP sem editar ou juntar |

## Google Takeout + JSON

Quando as datas ajustadas no Google Fotos não vierem nos metadados normais,
baixe um Takeout contendo as mídias e seus JSONs laterais. No Studio, use
**Importar → Google Takeout + JSON**. O original é guardado em `_TAKEOUT/` e o
ZIP normalizado é criado em `_ENTRADA/FR_AUTOEDITE_ENTRADA.zip`.

```bash
fr-autoedite importar-takeout --arquivo TAKEOUT.zip --projeto PROJETO
```

O ExifTool é preferido para gravar a data internamente. Sem ele, o programa
tenta remux com FFmpeg e sempre ajusta a data de modificação e a data interna
do novo ZIP. Mídias sem JSON não são descartadas; o resultado é detalhado em
`_TAKEOUT/01_RELATORIO_GOOGLE_TAKEOUT.md`.

## Filtro local

```json
"local_analysis": {
  "enabled": true,
  "deduplicate_bursts": true,
  "scene_detection": true,
  "detect_stability": true,
  "organize_by_phase": true,
  "create_selects": true,
  "minimum_quality_score": 30,
  "max_scene_scan_sec": 180,
  "max_scene_clips_per_video": 18
}
```

Duplicatas são apenas marcadas e ignoradas pela montagem automática. Cenas
são intervalos virtuais e mantêm `parent_video`. Nenhum original é apagado.

## Google Drive

```json
"cloud_export": {
  "enabled": false,
  "provider": "google_drive_rclone",
  "account_email": "blueprintsplam@gmail.com",
  "rclone_remote": "gdrive",
  "remote_folder": "FR-AutoEdite/Entregas",
  "include_master": true,
  "include_social": true,
  "include_project_files": false
}
```

O e-mail é um rótulo de auditoria. A autorização real é feita por
`rclone config`, permitindo escolher qualquer conta sem guardar senha.

## Precisão

Preencha `context.facts_confirmed` somente com fatos documentados. Use
`context.facts_to_confirm` para materiais, marcas, medidas, fornecedores ou
resultados incertos. A master e cada Reel precisam de revisão humana integral.
