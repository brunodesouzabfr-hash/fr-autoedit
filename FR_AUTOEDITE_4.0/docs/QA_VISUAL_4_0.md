# QA visual — FR Quiet Engineering Atelier v2

## Inventário avaliado

- 28 composições em 1080×1920;
- 28 remontagens reais em 1080×1080;
- 13 diagramas técnicos distintos;
- três provas motion de 3 segundos;
- pranchas `PREVIEW_F3_9X16.jpg` e `PREVIEW_TODAS_1X1.jpg`.

## Score automático

Todos os 56 cards receberam 100/100 nos critérios verificáveis pelo código:

| Critério | Peso | Evidência |
|---|---:|---|
| Grid e safe area | 20 | bounds do compositor |
| Tipografia medida | 20 | fitting sem truncamento silencioso |
| Paleta canônica | 15 | tokens do sistema |
| Integridade de asset | 15 | manifesto e hash |
| Formato exato | 15 | dimensão lida do PNG |
| Nomenclatura | 5 | padrão FR obrigatório |
| Determinismo | 10 | renderer e seed fixos |

O score não mede beleza, verdade semântica, contraste em toda tela, leitura em
um aparelho real nem adequação final ao projeto. Por isso o estado permanece
`REVIEW_REQUIRED` e não “publicável aprovado”.

## Observações da inspeção visual

- a sequência F3 é coerente, distinta por serviço e mantém hierarquia estável;
- os diagramas permanecem discretos e não competem com os medalhões;
- a versão 1:1 é recomposta pelo kernel e não é crop do 9:16;
- F1, F2, F4, F5 e F6 usam espaço negativo deliberado; conteúdo definitivo do
  projeto pode ocupar áreas reservadas sem romper o sistema;
- seis medalhões de origem possuem fundo opaco: elétrica, hidráulica,
  iluminação, instalação, manutenção e projetos 3D. O normalizador preservou
  esse fundo para não inventar transparência. Revisar diâmetro aparente antes
  de autorizar publicação.

## Checklist humano restante

1. abrir ambas as pranchas em 100% e em miniatura;
2. conferir legibilidade em grayscale;
3. executar o teste de leitura de 2 segundos;
4. conferir os 13 F3 em sequência, sem saltos de escala;
5. assistir aos três MP4s com e sem áudio;
6. aprovar ou substituir os seis PNGs opacos;
7. registrar aprovação editorial por nome de arquivo.
