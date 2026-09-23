"""Fundação dos tiers; apenas operações realmente implementadas são executáveis."""
from __future__ import annotations
import json
from pathlib import Path
import shutil
import subprocess
from .base import Adapter, AdapterError, AdapterUnavailable, Request, Result


def _run(binary: str, args: list[str], timeout=30):
    executable = shutil.which(binary)
    if not executable: raise AdapterUnavailable(binary+' ausente.')
    process = subprocess.run([executable, *args], stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)
    if process.returncode:
        raise AdapterError(binary+' falhou: '+process.stderr.decode('utf-8', 'replace')[-1000:])
    return process.stdout


def _file(request):
    if request.source is None or not request.source.is_file(): raise ValueError('source deve ser arquivo existente.')
    return request.source.resolve()


def _probe(request):
    source = _file(request)
    return json.loads(_run('ffprobe', ['-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(source)]))


def _ffmpeg_self(_):
    data = _run('ffmpeg', ['-nostdin', '-v', 'error', '-f', 'lavfi', '-i',
                         'color=c=black:s=16x16:r=1', '-frames:v', '1', '-f', 'rawvideo', '-'])
    return len(data) == 384


def _ffprobe_self(_):
    # Sem arquivo real, este teste verifica executabilidade; probe é testado com fixture.
    return bool(_run('ffprobe', ['-version']))


def _pillow_self(_):
    from PIL import Image
    from io import BytesIO
    stream = BytesIO()
    Image.new('RGBA', (8, 8), (3, 24, 18, 255)).save(stream, format='PNG')
    stream.seek(0)
    with Image.open(stream) as image: return image.getpixel((0, 0)) == (3, 24, 18, 255)


def _image_info(request):
    from PIL import Image
    with Image.open(_file(request)) as image:
        return {'width': image.width, 'height': image.height, 'mode': image.mode, 'format': image.format}


class Registry:
    def __init__(self, adapters=None):
        self._adapters = {}
        for adapter in adapters or []: self.register(adapter)

    def register(self, adapter):
        if adapter.name in self._adapters: raise ValueError('Adapter duplicado: '+adapter.name)
        self._adapters[adapter.name] = adapter

    def list_all(self): return list(self._adapters.values())

    def list_available(self):
        result = []
        for adapter in self.list_all():
            try:
                if adapter.is_available(): result.append(adapter)
            except Exception:  # Uma detecção opcional defeituosa não derruba o Studio.
                continue
        return result

    def get(self, name):
        if name not in self._adapters: raise AdapterError('Adapter desconhecido: '+name)
        return self._adapters[name]

    def run_with_fallback(self, name, request):
        adapter = self.get(name)
        try: return adapter.run(request)
        except AdapterError as exc:
            handler = adapter.fallback()
            if adapter.tier == 3 or handler is None: raise
            fallback = handler(request)
            return Result(fallback.backend, fallback.operation, fallback.data, True,
                          fallback.warnings+(f'{name} indisponível/falhou; fallback aplicado: {exc}',))

    def diagnose(self, *, check=False):
        rows = []
        for adapter in self.list_all():
            try:
                available = adapter.is_available()
                row = {'name': adapter.name, 'tier': adapter.tier, 'available': available,
                       'implementation_status': adapter.state, 'purpose': adapter.purpose,
                       'capabilities': sorted(adapter.capabilities()),
                       'version': adapter.version() if check else None,
                       'smoke_passed': adapter.smoke_test() if check else None,
                       'fallback': adapter.fallback() is not None}
            except Exception as exc:
                row = {'name': adapter.name, 'available': False, 'error': type(exc).__name__}
            rows.append(row)
        return rows


def build_registry():
    registry = Registry([
        Adapter('ffmpeg', 1, executable='ffmpeg', state='implemented', version_args=('-version',),
                purpose='motor base; autoteste sintético', operations={'self_test': _ffmpeg_self}),
        Adapter('ffprobe', 1, executable='ffprobe', state='implemented', version_args=('-version',),
                purpose='sondagem de mídia', operations={'probe': _probe, 'self_test': _ffprobe_self}),
        Adapter('pillow', 1, module='PIL', distribution='Pillow', state='implemented',
                purpose='raster local', operations={'image_info': _image_info, 'self_test': _pillow_self}),
    ])
    # Tier descreve prioridade de integração, NÃO maturidade do adapter.
    specifications = [
        ('opencv',1,None,'cv2','opencv-python','qualidade visual'),
        ('scenedetect',1,None,'scenedetect','scenedetect','mudanças de cena'),
        ('auto_editor',1,'auto-editor',None,None,'corte por atividade'),
        ('imagemagick',1,'magick',None,None,'conversão de imagem'),
        ('rsvg',1,'rsvg-convert',None,None,'raster SVG'),
        ('inkscape',1,'inkscape',None,None,'raster SVG'),
        ('exiftool',1,'exiftool',None,None,'metadados'),
        ('mediainfo',1,'mediainfo',None,None,'metadados'),
        ('jinja2',1,None,'jinja2','Jinja2','templates confinados'),
        ('pydantic',1,None,'pydantic','pydantic','validação v2'),
        ('pandoc',1,'pandoc',None,None,'documentos'),
        ('qrcode',1,None,'qrcode','qrcode','QR local'),
        ('reportlab',1,None,'reportlab','reportlab','PDF local'),
        ('moviepy',2,None,'moviepy','moviepy','prévia curta'),
        ('pyloudnorm',2,None,'pyloudnorm','pyloudnorm','medição LUFS'),
        ('librosa',2,None,'librosa','librosa','onsets e BPM'),
        ('aubio',2,None,'aubio','aubio','beat/pitch'),
        ('rubberband',2,'rubberband',None,None,'time stretch'),
        ('demucs',2,None,'demucs','demucs','separação de stems'),
        ('tesseract',2,'tesseract',None,None,'OCR'),
        ('weasyprint',2,None,'weasyprint','weasyprint','PDF'),
        ('style_dictionary',2,'style-dictionary',None,None,'tokens'),
        ('colour_science',2,None,'colour','colour-science','cor'),
        ('chroma_js',2,None,None,None,'cor via Node: requer integração futura'),
        ('mermaid',2,'mmdc',None,None,'diagramas de documentação'),
        ('whisper',3,None,'whisper','openai-whisper','transcrição futura'),
        ('whisperx',3,None,'whisperx','whisperx','alinhamento futuro'),
        ('ollama',3,'ollama',None,None,'copiloto futuro; sem chamada'),
        ('clip',3,None,'clip',None,'busca semântica futura'),
        ('blip',3,None,'transformers','transformers','presença do runtime não confirma modelo'),
        ('yolo',3,None,'ultralytics','ultralytics','detecção futura'),
        ('mediapipe',3,None,'mediapipe','mediapipe','pose futura'),
        ('rife',3,None,None,None,'interpolação futura'),
        ('realesrgan',3,None,'realesrgan','realesrgan','upscale futuro'),
        ('figma',3,None,None,None,'tokens remotos: bloqueado'),
        ('youtube',3,None,None,None,'publicação: bloqueada'),
        ('instagram',3,None,None,None,'publicação: bloqueada'),
        ('tiktok',3,None,None,None,'publicação: bloqueada'),
    ]
    for name,tier,binary,module,distribution,purpose in specifications:
        registry.register(Adapter(name,tier,binary,module,distribution,purpose,
                                  state='metadata_only' if tier == 3 else 'discovery_only'))
    return registry
