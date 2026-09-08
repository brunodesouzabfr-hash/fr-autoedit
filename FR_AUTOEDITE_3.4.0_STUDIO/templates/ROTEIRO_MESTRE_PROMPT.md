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
iluminacao (detalhe/atmosfera). Use imagens reais do inventário nos campos visual e comparison.
Linhas decorativas de uma prancha não representam cotas ou um wireframe verdadeiro.

### Como o motor executa cada escolha

| Bloco/campo | Regra executável |
|---|---|
| roteiro | id identifica a alternativa; name é o nome legível; revision é a revisão. Preserve project_id e media_fingerprint. Um escopo por Markdown. Atualize também o comentário ROTEIRO se mudar o id. |
| configuration | Decisões completas do projeto. Blocos ausentes voltam aos padrões, não herdam o roteiro anterior. Localização de mídias, música/LUT anexadas, credenciais e destinos ficam sob controle local. |
| main_timeline.segments | Lista completa do filme. Cada ocorrência tem segment_id único. media_id referencia a fonte e pode se repetir. |
| include_in | ["branded"], ["clean"] ou ["branded","clean"]. Cards normalmente pertencem só a branded. |
| start_sec | Primeiro instante selecionado. start_time_basis = absolute_parent_media usa o relógio do vídeo-pai; scene_local usa deslocamento a partir da cena. Seja explícito. |
| duration_sec | Tempo exibido antes das sobreposições, em segundos. Tempo-fonte consumido = duration_sec × playback_speed. Não ultrapasse scene_end_sec nem a duração do vídeo. |
| playback_speed | 0.25–30. 1 é normal, menor que 1 é câmera lenta, maior que 1 acelera. Câmera lenta repete quadros; não há fluxo óptico. Divida em vários recortes para uma progressão de velocidade. |
| freeze_frame | Em um segmento media: {"time_sec":2.5,"time_basis":"absolute_parent_media"}. O media_id do segmento indica o vídeo. duration_sec controla quanto a foto permanece. Sem áudio desse vídeo. |
| transition | Transição de entrada do segmento. cut é corte seco; fade/dissolve/etc. estão em allowed_values. O primeiro segmento não tem transição de entrada. |
| transition_duration_sec | Pode ser definido por segmento; senão usa configuration.visual_effects.transition_duration_sec. Sobreposição limitada a 25% de cada clipe vizinho. cut ou duração zero não sobrepõem. |
| stabilization | off, auto ou on por segmento. on executa deshake; pode gerar bordas espelhadas. Confira linhas/medidas e não estabilize mídia já suave sem necessidade. |
| image_animation | none, zoom_in ou zoom_out para fotos/frames fixos. |
| type=card | card_kind, service_key opcional, title, body, duration_sec, card_animation; visual opcional ou comparison para comparação. Pode entrar em qualquer posição. |
| visual | {"media_id":"ID_EXISTENTE","time_sec":0,"time_basis":"absolute_parent_media","label":"Descrição factual"}. Para foto, time_sec=0. Para vídeo, escolha um quadro realmente visível. |
| comparison | {"before":{referência visual},"after":{referência visual}}. Os dois campos seguem visual. Labels podem ser ANTES/DEPOIS ou PROJETO/EXECUÇÃO, conforme a evidência. |
| reels | Objeto com chaves de duração, como "30" e "60". Cada um tem segments completo; escolha quantos desejar entre 5 e 600 s. {} desativa Reels. Não basta selecionar cortes do filme ao acaso. |
| carousel | enabled e slides completos em ordem. kind = cover, outro, card, media ou before_after; visual/comparison e service_key conforme necessidade. Quantidade exata = tamanho da lista. |
| stories | enabled, source_reel_sec (Reel existente), part_duration_sec. Opcional timeline com segments próprios, permitindo Stories sem Reels. |
| card_style | Paleta, fontes, respiro, contatos, logo persistente, overlay e layout. Se informado, é a autoridade visual do roteiro; não descreva uma fonte que o motor não possui. |
| publication | video_title, caption, hashtags, complementary_information e overlay_typography. É texto para publicação manual. |
| strategy | Racional breve, evidências, incertezas, CTA e teste. Não executa comandos nem publica automaticamente. |
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

O motor é local. Publicação em redes, aquisição de trilha, geração de cenas por IA, análise
financeira de resultados e medição real de retenção não acontecem por este Markdown.
