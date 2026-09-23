# FR Quiet Engineering Atelier v2 — assets

- Medalhões: `assets/service-medallions/original/<servico>.png`.
- Derivados: canvas RGBA 2048×2048 em `normalized/`, sem alterar o original.
- Logo: `assets/franco-romeu-logo.png`, sem espelhamento/recolorização.
- Fontes: Stardos Stencil, Rokkitt, Share Tech Mono e Cormorant Garamond.
- Um medalhão ausente recebe `pending_asset` e bloqueia publicação; somente
  rascunho pode usar `medallion_placeholder_tecnico`.
- Fundos finais externos são opcionais; o fallback procedural usa apenas os
  tokens canônicos e seed 4072026.

