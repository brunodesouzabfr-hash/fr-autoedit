# Quiet luxury — contrato operacional

Validadores retornam `path`, `rule`, `severity`, `message`. O Studio deve
mostrar a mesma mensagem e apontar o campo; erro bloqueia aplicação,
warning exige revisão. Código em `fr_v4/quiet_luxury/validators.py`.

| Regra | Passa | Falha | Severidade |
|---|---|---|---|
| Contenção | Encaixe e acabamento | Resultado incrível | error |
| Tom | Execução por etapas | Corpo acima de 220 caracteres | error |
| Veracidade | Afirmação acompanhada de fonte | Medida sem evidência | error |
| Permanência | Processo de montagem | Bora para essa trend | error |
| Precisão | Status projeto_3d | Status foto atribuído a um conceito | revisão semântica humana |
| Ritmo | Corte 2,4s | Corte 0,2s | error |
| Overlay | Camada por 2s | Camada por 0,5s | error |
| Assinatura | Tokens canônicos | Ouro substituído por cor aleatória | error |
| Exclusividade | Uso literal com fonte | Exclusivo sem comprovação | warning |

Regex não verifica a verdade do mundo: declarar fonte não prova sua validade.
Antes/depois, prazos, medidas, qualificações e depoimentos precisam ser
comparados com evidência real. Não certificar isso automaticamente.

As proporções de cor do manual não são preenchidas com pixels artificiais:
medir fora da máscara do medalhão e avaliar na QA. Também não há nota estética
automática ≥90. Miniatura, grayscale, leitura em 2s, 1:1 real e sequência de
13 continuam sendo verificações visuais, com registro por imagem.

Silêncio significa contenção. Preservar áudio de ready_video prevalece sobre
inserir pausas arbitrárias. Detecção de loudness não é detecção de voz.
