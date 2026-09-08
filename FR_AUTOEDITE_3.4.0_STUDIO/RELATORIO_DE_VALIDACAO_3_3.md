# Relatório de validação — FR AutoEdite Studio 3.3.0

Data da validação: **2026-09-05**

## Resultado

**APROVADO para empacotamento portátil em Parrot OS, Debian e Ubuntu.**

## Verificações executadas

| Verificação | Resultado |
|---|---|
| Compilação dos módulos Python | APROVADO |
| Sintaxe dos instaladores Bash | APROVADO |
| Leitura de todos os templates JSON | APROVADO |
| Sintaxe JavaScript do Studio | APROVADO |
| Teste HTTP do Studio | APROVADO |
| Geração de cards antes/depois da preparação | APROVADO |
| Máscara circular dos nove serviços | APROVADO |
| Google Takeout + JSON e preservação do original | APROVADO |
| Time-lapse editorial com velocidade reproduzível | APROVADO |
| Roteiro Mestre na central `_ENVIAR_IA/` | APROVADO |
| Filme institucional e filme limpo | APROVADO |
| Reels com começo, meio distribuído e fim | APROVADO |
| Stories, capas e carrossel | APROVADO |
| Lotes ZIP com CRC e menos de 150 MB | APROVADO |
| Auditoria mecânica final | APROVADO |

## Comandos de reprodução

```bash
./fr-autoedite --versao
bash -n install.sh ATUALIZAR_CORRECAO_CARDS.sh INSTALAR_EM_OUTRO_COMPUTADOR.sh
python3 -m py_compile app/fr_autoedite.py app/studio.py app/local_analysis.py app/copilot.py
python3 tests/card_circle_test.py
python3 tests/studio_http_test.py
bash tests/smoke_test.sh
```

Os testes usam somente mídias sintéticas temporárias. Nenhuma mídia pessoal,
senha, token ou chave de API é necessária.

## Limites que permanecem

- A recuperação interna de datas funciona melhor com ExifTool instalado; sem
  ele, FFmpeg, data do arquivo e data do ZIP servem como fallback auditável.
- Estabilização e time-lapse alteram movimento e podem exigir ajuste visual.
- Heurísticas e IA não substituem assistir à master e a cada Reel integralmente.
- O usuário precisa solicitar e baixar o Google Takeout na própria conta; o
  Studio processa localmente o ZIP recebido.
