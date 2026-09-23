# FR AutoEdite 4.0 — 18 entregas obrigatórias

## Estado geral

Versão: `4.0.0-candidate`. Base: ZIP 3.4.0 auditado. Integração realizada em
cópia isolada. Nenhum commit, push, merge ou deploy foi feito. O candidato
passou pelos testes locais descritos no relatório de validação, mas ainda
requer homologação visual e instalação controlada na máquina de destino.

1. **Auditoria do código 3.4.0** — mapa das funções visuais, violações,
   conflitos e decisões no `RELATORIO_MIGRACAO.md`; inventário AST reproduzível
   por `scripts/auditar_base.py`.
2. **Arquitetura 4.0** — pacote modular `app/fr_v4/`, mantendo
   `app/fr_autoedite.py` como fachada compatível.
3. **Sistema visual operacional** — tokens, grid 12 colunas, baseline 8 px,
   safe areas, kernel 1:1, tipografia medida e fundos sem mármore institucional.
4. **Famílias F1–F6** — capa, etapa, serviço, detalhe, extras e encerramento,
   com wrappers documentados e motor compartilhado.
5. **Treze serviços** — diagramas distintos, microcódigos, numeração 01/13 a
   13/13 e medalhões preservados.
6. **Assets e Style Pack** — manifesto com hashes, original/normalizado,
   status editorial, fallback técnico e documentação de assets.
7. **Motion quiet luxury** — easing contido, fade, line wipe, microparallax e
   três MP4s de prova; FFmpeg continua sendo o motor obrigatório.
8. **Contrato Markdown↔IA v4** — YAML imutável + corpo + JSON, schema,
   validador, Pydantic opcional, migração conservadora e publicação atômica.
9. **Ready video** — timeline bloqueada, original intocado, overlays medidos,
   FFprobe antes da publicação e fallback FFmpeg sem MoviePy.
10. **Sistema editorial** — módulos para cor, áudio, captions, capítulos,
    presets, metadados, versões, workflow e busca estrutural.
11. **Adapters Tier 1/2/3** — operações reais somente para FFmpeg/FFprobe/
    Pillow; extras detectáveis sem importação obrigatória; Tier 3 bloqueado.
12. **CLI preservada e ampliada** — comandos legados mantidos; novos comandos
    de diagnóstico e contrato; `--version` e `--versao` aceitos.
13. **Studio expandido** — identificação 4.0, integração pelo backend existente,
    preview/assinatura v2 e compatibilidade com jobs e projetos 3.4.0.
14. **Cards consolidados** — 56 PNGs, 13 diagramas, três MP4s, manifesto e ZIP
    `FR_CARDS_v2.0.0_CONSOLIDADO.zip`.
15. **Cards separados** — os 56 PNGs também em `entrega/separados/`, seguindo
    `FR_[FAMILIA]_[TEMA]_[FORMATO]_[VARIANTE]_v2.0.0.png`.
16. **QA e regressão** — score técnico automático, pranchas de inspeção,
    testes visuais, contrato, ready_video, cache, HTTP, jobs e smoke integral.
17. **Instalação, atualização e rollback** — instalador normal, instalador lado
    a lado, backup, guia de atualização pela `main` e reversão sem tocar projetos.
18. **Segurança da distribuição** — exclusão de Studio, mídia pessoal, proxies,
    renders, ZIPs de usuário, `.env`, tokens, logs e caches; hashes SHA-256 dos
    pacotes finais.

## Limites explícitos

- aprovação estética final e autorização de publicação são humanas;
- MoviePy, OpenCV, PySceneDetect, Whisper/WhisperX e modelos locais não são
  requisitos nem pipelines declarados prontos;
- locução complexa, keyframes arbitrários e múltiplos balões independentes do
  fluxo bruto podem continuar como metadados;
- não existe promessa de viralização, retenção, leads, ROI ou resultado;
- `git diff --check` depende de uma cópia Git real; o ZIP recebido não contém
  `.git`.
