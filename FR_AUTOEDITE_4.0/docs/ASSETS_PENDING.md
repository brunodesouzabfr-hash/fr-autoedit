# Identidade e estado dos ativos

Os quatro arquivos antes ausentes foram recebidos nesta rodada. O ZIP contém
os 13 serviços. Não produzir placeholders para substituir arquivos disponíveis.

Estado atual: 13/13 medalhões instalados, 0 `pending_asset`. O fallback continua
implementado para instalações futuras incompletas, mas não foi usado nos cards
entregues.

A indexação verifica presença e hashes; ausência futura gera `pending_asset`,
`sha256: null`, `dimensoes: null`, `publicavel: false` e fallback
`medallion_placeholder_tecnico`. Rascunhos podem usar o fallback identificado.
Publicação exige identidade instalada e revisão humana específica do output.

| Serviço | Original esperado | Código |
|---|---|---|
| Elétrica | assets/service-medallions/original/eletrica.png | MEP-ELE |
| Hidráulica | assets/service-medallions/original/hidraulica.png | MEP-HYD |
| Instalação | assets/service-medallions/original/instalacao.png | FIT-INST |
| Manutenção | assets/service-medallions/original/manutencao.png | OPS-MNT |

Formato ideal para substituição futura: PNG RGBA 2048×2048, centro alinhado, diâmetro visual
1740 px, sem recorte de aro ou texto. Fontes atualmente opacas continuam
opacas no interior; o normalizador acrescenta margens transparentes, mas
não inventa uma segmentação nem remove o fundo que faz parte da identidade.
Esse caso fica marcado `opaque_background_preserved` e exige QA visual.

Os arquivos com fundo opaco preservado são: Elétrica, Hidráulica, Iluminação,
Instalação, Manutenção e Projetos 3D. Isso gera 12 avisos no QA porque cada
medalhão aparece em 9:16 e 1:1.

Não ajustar exposição automaticamente. Arquivos normalizados são derivados;
os originais byte a byte ficam separados. Não colocar novas artes por cima
de cópias existentes sem revisar diferenças de hash.
