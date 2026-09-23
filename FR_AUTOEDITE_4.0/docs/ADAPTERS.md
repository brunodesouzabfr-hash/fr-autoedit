# Adapters — estado real no candidato 4.0

O registro é carregado sob demanda e não instala pacotes, baixa modelos nem
faz chamadas externas. Ele separa capacidade executável de simples detecção.

- `implemented`: operação local realmente presente no código.
- `discovery_only`: presença detectável, execução bloqueada.
- `metadata_only`: Tier 3; nenhuma execução autorizada nesta versão.
- `available`: runtime encontrado; não afirma que modelos/codecs funcionam.
- `smoke_passed`: nulo antes de `--check`; não confundir com aprovação.

FFprobe executa `probe`; Pillow inspeciona imagens; FFmpeg possui autoteste
sintético. O pipeline pesado continua sendo o FFmpeg da base 3.4.0. OpenCV,
PySceneDetect, Auto-Editor, MoviePy e demais nomes do catálogo têm propósito,
tier e disponibilidade detectável, mas permanecem `discovery_only` enquanto
não houver operação e testes próprios. Whisper/WhisperX e publicação em redes
permanecem `metadata_only`.

O fallback só é usado se registrado e retorna `backend`, `fallback_used` e
avisos. Não converter erro de contrato do usuário em render aparentemente
bem-sucedido. Tier 3 nunca chama fallback ou rede.

Uso:

```python
from pathlib import Path
from fr_v4.adapters.registry import build_registry
from fr_v4.adapters.base import Request
result = build_registry().run_with_fallback('ffprobe', Request('probe', Path('amostra.mp4')))
```

```bash
python3 scripts/diagnosticar_v4.py
python3 scripts/diagnosticar_v4.py --check
```

Nenhum `pip install`, apt, download de pesos, upload, API ou publicação é
disparado. Instalação de dependências opcionais é uma ação separada.

Resultado verificado neste ambiente: FFmpeg, FFprobe e Pillow disponíveis e
aprovados no autoteste. Pydantic, Inkscape, Pandoc, ReportLab e Tesseract foram
detectados, mas sua detecção não os promove a pipelines executáveis.
