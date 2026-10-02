# M3 — Service Card Central Media

**PRE-AUDIT ASSUMPTION:** `app/fr_v4/core/card_renderer.py` já possui máscara/símbolos de serviço; comparar com editor 1.1 e `service_cards.py` após M0. Depende de M2 para placement e M1 para edição. Escopo: slot central F3/SERVICE, seleção/substituição manual, zoom/focal, fallback e paridade entre preview/render. Não generalizar forma circular a outras famílias.

Contrato: `central_asset_id` aponta asset existente/autorizado, `shape=circle` sempre para F3, crop efetivo 1:1 e imagem interna sem distorção, zoom em faixa validada, `focal_x/y` finitos, opacidade/borda do Style Pack se suportado. Proporcionalidade a 9:16 e 1:1 requer composição própria ou fallback declarado; não esticar PNG vertical para quadrado. Quando asset ausente, fallback real do pack e aviso; IA futura apenas sugere ID existente. Persistir ajustes por instância, versão, preview invalidado.

Testar imagens horizontal/vertical, extremos de zoom/focal, asset removido e family não SERVICE; medir diâmetro, preservar razão dos objetos e comparar preview/master. Rodar testes do círculo existentes se checkout os contiver; reportar limites de QA visual. Matriz M3.
