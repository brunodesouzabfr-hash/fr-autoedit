# M4 — Balloon / Callout Engine

**PRE-AUDIT ASSUMPTION:** renderer atual em `app/fr_v4/overlays.py` produz box opaco de dimensão proporcional fixa, e há fallback em `ready_video.py`. M0 confirma também preview HTML. Pode desenvolver após M0 com integração temporal confirmada por M2. Não redesenhar cards nesta milestone.

Entregar contrato de balloon/callout com texto, role, timing, safe areas, priority, padding, limite de linhas, posição, motion e Brand/Style tokens. Medir texto real com fontes distribuídas e ajustar caixa ao conteúdo; grid e traços finos com opacidade baixa, final gradiente para transparência, fundo leve/sem painel opaco pesado, easing configurável. Resolver colisões com outros balões e legendas e preferir evitar sujeito se houver máscara confiável. Se não houver região livre, expor aviso e revisão, nunca cortar texto ou cobrir silenciosamente. Diferenciar 9:16/1:1/16:9 quando suportados; preservar fallback visual para projetos antigos e comparar preview HTML com render final.

Casos: texto curto/longo/acentos, duas caixas simultâneas, legenda na região inferior, sujeito central, margens e redução de movimento; verificar bbox e composição visual em fixture. Registrar falhas de font fallback, limite de evitar sujeito e testes reais. Ver M4 na matriz. Design final fino permanece decisão de QA visual posterior.
