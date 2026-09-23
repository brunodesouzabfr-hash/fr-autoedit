"""Pillow compõe camadas com easing; FFmpeg codifica frames em fluxo limitado.

Não mantém o vídeo inteiro em RAM. Previews devem usar 540×960 em máquinas
modestas. As durações da coreografia são segundos derivados de 24 fps,
independentes da taxa de saída; não duplicar 24 frames em um render 60 fps.
"""
from __future__ import annotations
from pathlib import Path
import math
import os
import shutil
import subprocess
import tempfile
from .easing import ease

# start, end, offset vertical em px @1080, escala inicial
STAGES={'background':(0,6/24,0,1),'diagram':(2/24,10/24,0,1),
        'tag':(6/24,14/24,-8,1),'title':(10/24,20/24,6,1),
        'medallion':(14/24,24/24,0,.98),'data':(20/24,28/24,0,1),
        'footer':(24/24,32/24,0,1)}


def frame(composition, time_sec: float, duration: float):
    from PIL import Image,ImageChops
    size=composition.layers['background'].size
    result=Image.new('RGBA',size,(3,24,18,255))
    scale=min(size)/1080
    for name,original in composition.layers.items():
        start,end,offset,initial_scale=STAGES[name]
        gain=ease((time_sec-start)/(end-start),'easeOutQuint')
        if gain<=0:continue
        layer=original.copy()
        if initial_scale!=1:
            factor=initial_scale+(1-initial_scale)*gain
            resized=layer.resize((max(1,round(size[0]*factor)),max(1,round(size[1]*factor))),Image.Resampling.LANCZOS)
            layer=Image.new('RGBA',size)
            layer.alpha_composite(resized,((size[0]-resized.width)//2,(size[1]-resized.height)//2))
        layer.putalpha(layer.getchannel('A').point(lambda x:round(x*gain)))
        dy=round(offset*scale*(1-gain))
        # Blueprint com deslocamento de um pixel, suavizado em ciclo de 6s.
        dx=round(scale*math.sin(2*math.pi*time_sec/6)) if name=='diagram' else 0
        result.alpha_composite(layer,(dx,dy))
    out=ease((time_sec-(duration-.4))/.4,'easeInOutSine')
    if out>0:
        veil=Image.new('RGBA',size,(3,24,18,round(out*255)));result.alpha_composite(veil)
    return result.convert('RGB')


def render(composition, target: Path, *, duration=3.0, fps=24):
    if not 1.6<=duration<=12 or not isinstance(fps,int) or not 12<=fps<=60:
        raise ValueError('Motion curto: 1,6–12s, fps inteiro 12–60.')
    binary=shutil.which('ffmpeg')
    if not binary: raise RuntimeError('FFmpeg obrigatório para MP4.')
    width,height=composition.layers['background'].size
    if width%2 or height%2: raise ValueError('H.264 yuv420p exige dimensões pares.')
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists(): raise FileExistsError('Saída motion já existe; use versão isolada.')
    count=round(duration*fps)
    last_error = ''
    for attempt in range(1, 4):
        fd,name=tempfile.mkstemp(prefix=f'.fr-motion-{attempt}-',suffix='.mp4',dir=target.parent);os.close(fd)
        with tempfile.TemporaryFile() as errors:
            command=[binary,'-y','-nostdin','-hide_banner','-loglevel','error','-f','rawvideo',
                     '-pix_fmt','rgb24','-s',f'{width}x{height}','-r',str(fps),'-i','pipe:0',
                     '-an','-frames:v',str(count),'-c:v','libx264','-preset','veryfast',
                     '-crf','18','-pix_fmt','yuv420p','-threads','1','-map_metadata','-1',
                     '-movflags','+faststart',name]
            process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=errors)
            try:
                for index in range(count):
                    current = frame(composition,index/fps,count/fps)
                    process.stdin.write(current.tobytes()); current.close()
                process.stdin.close()
                code=process.wait(timeout=max(60, round(duration*20)))
                if code:
                    errors.seek(0);raise RuntimeError(errors.read().decode('utf-8','replace')[-1500:])
                probe = shutil.which('ffprobe')
                if not probe:
                    raise RuntimeError('FFprobe obrigatório para validar motion.')
                checked = subprocess.run([probe,'-v','error','-select_streams','v:0',
                                          '-show_entries','stream=width,height,nb_frames',
                                          '-of','default=noprint_wrappers=1',name],
                                         stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,check=False)
                if checked.returncode or f'width={width}' not in checked.stdout or f'height={height}' not in checked.stdout:
                    raise RuntimeError('MP4 temporário inválido: '+checked.stderr[-500:])
                os.replace(name,target)
                return target
            except (BrokenPipeError, OSError, subprocess.SubprocessError, RuntimeError) as exc:
                last_error = f'tentativa {attempt}: {exc}'
            finally:
                if process.poll() is None: process.kill();process.wait()
                if process.stdin and not process.stdin.closed:process.stdin.close()
                if os.path.exists(name):os.unlink(name)
    raise RuntimeError('Falha determinística ao gerar motion após 3 tentativas: '+last_error)
