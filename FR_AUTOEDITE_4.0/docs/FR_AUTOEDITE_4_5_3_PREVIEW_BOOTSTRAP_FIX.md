# FR AutoEdite 4.5.3 — Preview bootstrap fix

Correções:

- CARD_PREVIEW_PLAN pode renderizar antes de existir MANIFESTO_MEDIA.json; nessa fase usa apenas assets validados do componente/catálogo SERVICE.
- Preview temporário aceita qualquer resolução 9:16 (por exemplo 720x1280): renderiza internamente em resolução congelada do contrato e redimensiona somente a saída de preview.
- O contrato de master permanece estrito e inalterado.
