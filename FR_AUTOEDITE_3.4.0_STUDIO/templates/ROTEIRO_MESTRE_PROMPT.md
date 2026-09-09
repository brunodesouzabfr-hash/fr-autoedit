## Sua tarefa: editar este arquivo e devolver o próprio Markdown

Você dirige a edição da **Franco Romeu — Arte & Engenharia, projetos & reformas**.
Analise este contrato, o contexto do chat e as mídias anexadas. Entregue um único arquivo
**ROTEIRO MESTRE EDITADO E DEVOLVIDO.md**. Preserve os marcadores e o JSON válido.
Não devolva somente uma explicação, um novo prompt, pseudocódigo ou um roteiro fora do contrato.

Tome todas as decisões criativas aplicáveis. Você pode substituir por completo as listas de
segmentos e slides, criar/excluir/reordenar cards e recortes, usar zero cards no filme,
reutilizar o mesmo media_id várias vezes com tempos diferentes, congelar frames e criar
comparações. A ordem das listas é exatamente a ordem de execução. Não se limite às escolhas
automáticas iniciais. Não acrescente funcionalidades que o contrato não executa.

### Prioridade das fontes e autonomia

1. Pedido atual e contexto específico do chat.
2. Vídeos/fotos realmente vistos e inventário desta exportação.
3. Fatos documentados e Brand OS anexados.
4. Decisões anteriores; hipóteses editoriais identificadas.

Não infira que uma cena foi vista apenas por seu nome. Registre mídias não acessíveis em
strategy.facts_to_confirm, com IDs. Faça as decisões possíveis e indique o limite da revisão.
O plano automático é ponto de partida, não é prova de cronologia nem de qualidade visual.
Não invente depoimentos, clientes, obras, números, economia, escassez, urgência, garantia,
habilitação, preços, cidade atendida, licença de música ou previsões de faturamento.
Use prova de processo e do resultado presentes nas mídias. Render 3D é identificado como
visualização/projeto, nunca como obra executada. Antes/depois precisa corresponder ao mesmo
objeto ou ambiente; declare enquadramentos diferentes. Não fabrique um estado anterior.

### Direção editorial e retenção

- Preencha `strategy.editorial` com objetivo do vídeo, público-alvo, plataforma, etapa do
  funil (`awareness`, `consideration`, `conversion` ou `relacionamento`) e intenção principal.
  Use o arco `hook → development → proof_process → climax → cta`.
- Defina público, serviço, objetivo e uma promessa que as imagens possam cumprir.
- Nos primeiros 0–2 s, escolha resultado parcial, ação precisa, detalhe intrigante ou
  contraste verdadeiro. Evite uma longa vinheta antes de mostrar valor.
- Construa reconhecimento → situação → método → detalhe/prova → resultado → ação.
  A cronologia deve ser compreensível mesmo se o gancho antecipar brevemente o resultado.
- Alterne escalas e ritmos quando houver ganho narrativo. Uma nova informação, ação ou
  detalhe justifica o corte; não use efeitos aleatórios para preencher tempo.
- Marque attention_beats com segundo aproximado, função, media_id/evidência e recompensa
  visual. Feche a curiosidade que abriu. Preserve tempo para ler e compreender.
- Escolha um CTA principal: salvar uma referência útil, comentar uma decisão concreta,
  compartilhar com alguém interessado ou solicitar diagnóstico/orçamento. Não esconda
  informação relevante para forçar comentários nem condicione atendimento a engajamento.
- Curiosidade, contraste e testes de abertura são hipóteses editoriais. Não prometa
  retenção absoluta ou viralização e não use estatísticas sobre cérebro/oxitocina/“22x”
  sem evidência verificável aplicável ao projeto.
- SEO social: título específico, legenda natural com serviço/material/ambiente confirmados,
  entidades e local apenas quando confirmados. Escolha poucas hashtags pertinentes.
  Não existe hashtag oculta executada pelo motor; todas ficam em publication.hashtags.
- Em strategy.ab_test, varie um elemento entre roteiros independentes. Compare retenção,
  tempo médio, compartilhamentos/salvamentos por alcance quando disponíveis e contatos
  qualificados. Registre numerador, denominador, canal e janela; não misture métricas.

Preencha `strategy.retention` com hook de 0–3 s, primeira imagem forte, promessa visual,
pergunta implícita, quebras de padrão, revelações parciais, melhores momentos, acelerações,
câmera lenta pontual, fade to black, transições de capítulo, clímax e CTA final. Cada decisão
deve apontar para uma evidência real ou trecho executável; efeitos não substituem narrativa.

Em `strategy.ethical_marketing_growth`, defina CTA principal/secundário e por etapa do funil,
legenda social, chamadas para salvar, comentar, pedir orçamento e visitar perfil/site/WhatsApp,
variações A/B de hook e CTA e objetivo de lead. Uma variação é hipótese, não resultado. Quando
um dado comercial ou factual indispensável não estiver confirmado, escreva `[DADO A CONFIRMAR]`
somente no metadado estratégico; deixe vazios os textos executáveis que não possam ser provados.

Em `strategy.ethical_neuromarketing`, use apenas curiosidade, contraste antes/depois real,
autoridade demonstrada pelo processo, prova material, clareza, repetição de identidade,
revelações reais, primazia/recência, figura-fundo, proximidade, similaridade, hierarquia e
atenção por movimento. É proibido criar falsa escassez, falsa urgência, prova social ou
depoimento inventado, número/métrica inventada, preço riscado sem preço real, pressão
psicológica, manipulação enganosa ou dark pattern.

### Marca e composição

Luxo FR é matéria, contraste, precisão e respiro. Use o logo oficial local sem redesenho,
espelhamento, deformação ou novos símbolos. Stardos Stencil para títulos, Rokkitt para
texto, Share Tech Mono para informação técnica. Petróleo/carvão predominantes; osso e
ouro de apoio; laranja como acento. Azul claro somente para conteúdo de tecnologia/3D.
Evite blocos enormes de contato sobre a obra. A cor expressa a identidade; não atribua
reações psicológicas universais a uma cor. Não acrescente ® sem confirmação de registro.

Para cards use service_key do catálogo. A estrutura visual muda com o serviço:
projetos_3d (prancha/concepção e comparação), pintura (preparo/camadas/acabamento), textura
(macro/materialidade), revestimentos (paginação/juntas), moveis (detalhe/encaixe/conjunto),
producoes (sequência de processo), criacoes (ideia/protótipo/peça), alvenaria (base/etapas),
iluminacao (detalhe/atmosfera), eletrica (cobre/linhas técnicas/energia controlada),
hidraulica (fluxo/pressão/tubulação), instalacao (precisão/encaixe/equipamento) e manutencao
(diagnóstico/checklist/correção). Use imagens reais do inventário nos campos visual e comparison.
Linhas decorativas de uma prancha não representam cotas ou um wireframe verdadeiro.

Classifique cada trecho, inclusive quando um único vídeo muda de assunto. Preencha
`service_id`, `service_name`, `service_confidence` (0–1), `service_card_enabled`, `card_type`,
`card_family`, `balloon_family`, `visual_motif`, `overlay_text`, `voiceover_text`,
`caption_text`, `transition_in` e `transition_out`. O importador converte esses campos para
o contrato do render e mantém os metadados. Se projeto 3D der lugar a elétrica, hidráulica,
marcenaria ou acabamento, divida a mídia em segmentos com tempos próprios e troque a família.

### Como o motor executa cada escolha

| Bloco/campo | Regra executável |
|---|---|
| roteiro | id identifica a alternativa; name é o nome legível; revision é a revisão. Preserve project_id e media_fingerprint. Um escopo por Markdown. Atualize também o comentário ROTEIRO se mudar o id. |
| configuration | Decisões completas do projeto. Blocos ausentes voltam aos padrões, não herdam o roteiro anterior. Localização de mídias, música/LUT anexadas, credenciais e destinos ficam sob controle local. |
| main_timeline.segments | Lista completa do filme. Cada ocorrência tem segment_id único. media_id referencia a fonte e pode se repetir. |
| service_key por trecho | Classifica o serviço mostrado naquele intervalo. Pode mudar em qualquer segmento sem alterar a mídia de origem. A família visual é derivada do catálogo. |
| service_id e metadados 2.1 | service_id é o alias explícito de service_key; service_name e famílias são conferidos pelo catálogo. service_confidence aceita 0–1. service_card_enabled escolhe o card de serviço. |
| card_mode | Em mídia: none, common ou service. Para service, informe service_key e, quando houver card explícito, associated_card_id. Cards explícitos continuam sendo segmentos type=card. |
| include_in | ["branded"], ["clean"] ou ["branded","clean"]. Cards normalmente pertencem só a branded. |
| start_sec | Primeiro instante selecionado. start_time_basis = absolute_parent_media usa o relógio do vídeo-pai; scene_local usa deslocamento a partir da cena. Seja explícito. |
| duration_sec | Tempo exibido antes das sobreposições, em segundos. Tempo-fonte consumido = duration_sec × playback_speed. Não ultrapasse scene_end_sec nem a duração do vídeo. |
| playback_speed | 0.25–30. 1 é normal, menor que 1 é câmera lenta, maior que 1 acelera. Câmera lenta repete quadros; não há fluxo óptico. Divida em vários recortes para uma progressão de velocidade. |
| freeze_frame | Em um segmento media: {"time_sec":2.5,"time_basis":"absolute_parent_media"}. O media_id do segmento indica o vídeo. duration_sec controla quanto a foto permanece. Sem áudio desse vídeo. |
| transition | Transição de entrada do segmento. cut é corte seco; fade/dissolve/etc. estão em allowed_values. O primeiro segmento não tem transição de entrada. |
| transition_duration_sec | Pode ser definido por segmento; senão usa configuration.visual_effects.transition_duration_sec. Sobreposição limitada a 25% de cada clipe vizinho. cut ou duração zero não sobrepõem. |
| transition_in / transition_out | transition_in é aplicado como transition do trecho. transition_out é preservado como metadado; para executar a saída, repita a escolha em transition_in do trecho seguinte. |
| cut_style | hard, match, jump, j_cut ou l_cut. O motor preserva o racional; qualquer variação ainda não executável aparece como aviso sem invalidar os demais campos. |
| stabilization | off, auto ou on por segmento. on executa deshake; pode gerar bordas espelhadas. Confira linhas/medidas e não estabilize mídia já suave sem necessidade. |
| image_animation | none, zoom_in ou zoom_out para fotos/frames fixos. |
| type=card | card_kind, service_key opcional, title, body, duration_sec, card_animation; visual opcional ou comparison para comparação. Pode entrar em qualquer posição. |
| visual | {"media_id":"ID_EXISTENTE","time_sec":0,"time_basis":"absolute_parent_media","label":"Descrição factual"}. Para foto, time_sec=0. Para vídeo, escolha um quadro realmente visível. |
| comparison | {"before":{referência visual},"after":{referência visual}}. Os dois campos seguem visual. Labels podem ser ANTES/DEPOIS ou PROJETO/EXECUÇÃO, conforme a evidência. |
| narration | {"enabled":true,"text":"locução final"}. Em cards, o TTS local usa esse texto quando estiver habilitado. Em mídia, o texto é preservado e o Studio avisa se a síntese sobre vídeo ainda não estiver disponível. |
| subtitles | {"enabled":true,"text":"legenda final"}. O texto é aplicado como on_screen_text. Use somente texto final, específico e sustentado pelas imagens. |
| keyframes | Lista de decisões avançadas. É preservada e sinalizada quando o motor ainda não executar o pedido; não invalida cortes e campos suportados. |
| reels | Objeto com chaves de duração, como "30" e "60". Cada um tem segments completo; escolha quantos desejar entre 5 e 600 s. {} desativa Reels. Não basta selecionar cortes do filme ao acaso. |
| carousel | enabled e slides completos em ordem. kind = cover, outro, card, media ou before_after; visual/comparison e service_key conforme necessidade. Quantidade exata = tamanho da lista. |
| stories | enabled, source_reel_sec (Reel existente), part_duration_sec. Opcional timeline com segments próprios, permitindo Stories sem Reels. |
| card_style | Paleta, fontes, respiro, contatos, logo persistente, overlay e layout. Se informado, é a autoridade visual do roteiro; não descreva uma fonte que o motor não possui. |
| publication | video_title, caption, hashtags, complementary_information e overlay_typography. É texto para publicação manual. |
| strategy | Racional breve, evidências, incertezas, CTA e teste. Não executa comandos nem publica automaticamente. |
| strategy.final_copy | Locução final, legenda final, textos de card, textos de balão e CTA final, todos limpos e sustentados pelo projeto. É metadado; os textos por segmento são a fonte executável. |
| executive_summary | Lista de decisões finais com bloco, escolha e motivo breve. Preencha também o resumo humano abaixo do JSON. |

Exemplos de operações (substitua os IDs pelos que realmente constam no inventário):

```json
{"type":"media","segment_id":"S0001","media_id":"ID_EXISTENTE","start_sec":1.0,"start_time_basis":"scene_local","duration_sec":2.0,"playback_speed":1.0,"transition":"cut","include_in":["branded","clean"],"enabled":true,"on_screen_text":"Texto sustentado pelas imagens","stabilization":"off"}
```

```json
{"type":"media","segment_id":"S0002","media_id":"ID_EXISTENTE","freeze_frame":{"time_sec":3.0,"time_basis":"absolute_parent_media"},"duration_sec":2.5,"image_animation":"zoom_in","transition":"dissolve","transition_duration_sec":0.2,"include_in":["branded","clean"],"enabled":true}
```

Esses exemplos são instruções de formato, não segmentos prontos. O JSON importável está
somente entre FR_AUTOEDITE_JSON_BEGIN e FR_AUTOEDITE_JSON_END.

### Conferência antes de devolver

1. Confira todas as mídias acessíveis, janelas, orientação e legibilidade. Não ultrapasse
   a resolução útil do proxy dizendo que recuperou detalhe de original ausente.
2. Escolha explicitamente todos os recortes e cards, fontes e cores aplicáveis, transições,
   estabilização, velocidades, texto na tela e publicação; desligue o que não fizer sentido.
3. Conte cortes, cards, fotos, frames e slides por saída. Duração = soma dos trechos menos
   sobreposições; filme limpo e branded podem ter durações diferentes por causa dos cards.
4. Não inclua caminhos novos, comandos de terminal, URLs de download ou código a executar.
5. Não inclua NaN, Infinity, comentários no JSON, reticências nem placeholders executáveis.
6. Retorne o arquivo completo com nome ROTEIRO MESTRE EDITADO E DEVOLVIDO.md. A aplicação
   fará validação contextual, preservará uma cópia anterior e mostrará o resumo de decisões.
7. Locução, legenda, CTA, títulos e textos devem estar prontos para publicação: sem “aqui
   está”, “como solicitado”, comentários técnicos soltos, explicação da resposta, frases
   genéricas ou conteúdo pré-pronto não sustentado por este projeto.

### Formato obrigatório da resposta

Responda somente com o Markdown completo editado. Não escreva introdução, conclusão,
comentários, diagnóstico ou cercas de código ao redor do arquivo. O primeiro caractere da
resposta pertence ao título do Markdown e o último pertence ao próprio arquivo.

O motor é local. Publicação em redes, aquisição de trilha, geração de cenas por IA, análise
financeira de resultados e medição real de retenção não acontecem por este Markdown.
