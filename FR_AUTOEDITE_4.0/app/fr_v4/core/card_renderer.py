"""Compositor F1–F6 com camadas reutilizáveis para PNG e motion.

Os desenhos técnicos não são plantas executivas e não inventam medidas.
O renderer produz rascunhos; aprovação de publicação é uma operação distinta.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from .config import SERVICES, SERVICE_BY_KEY, TOKENS, TEXTURE_SEED, MEDIA_STATUS, palette_rgba
from .grid import Grid, Box
from .typography import draw_text
from ..diagrams import render as diagram
from ..style_packs.registry import resolve, AssetError
from ..quiet_luxury.validators import validate_text


@dataclass(frozen=True)
class CardSpec:
    family: str
    title: str
    body: str = ''
    service_key: str = ''
    subtype: str = ''
    media_status: str | None = None
    image: Path | None = None
    comparison_image: Path | None = None
    contacts: tuple[str, ...] = ()
    evidence: tuple[dict, ...] = ()
    stage_number: str = ''


@dataclass
class Composition:
    layers: dict
    bounds: dict[str, Box]
    pending_assets: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def flatten(self):
        from PIL import Image
        first = next(iter(self.layers.values()))
        canvas = Image.new('RGBA', first.size)
        for layer in self.layers.values(): canvas.alpha_composite(layer)
        return canvas


def background(size):
    from PIL import Image
    import random
    width,height=size
    ramp=Image.new('RGB',(1,height))
    colors=[palette_rgba(k)[:3] for k in ('ink','deep','petrol')]
    for y in range(height):
        position=y/max(1,height-1)*2; index=min(1,int(position)); weight=position-index
        ramp.putpixel((0,y),tuple(round(a+(b-a)*weight) for a,b in zip(colors[index],colors[index+1])))
    result=ramp.resize(size).convert('RGBA')
    # Seed local: não altera o gerador aleatório global ou a seleção de mídias.
    rng=random.Random(TEXTURE_SEED)
    tile=Image.frombytes('L',(128,128),bytes(rng.randrange(256) for _ in range(128*128)))
    noise=Image.new('L',size)
    for y in range(0,height,128):
        for x in range(0,width,128): noise.paste(tile,(x,y))
    grain=Image.new('RGBA',size,palette_rgba('bone',0));grain.putalpha(noise.point(lambda v:round(v*.025)))
    result.alpha_composite(grain)
    return result


def placeholder(size, code, fonts):
    from PIL import Image, ImageDraw
    from .typography import load_font
    image=Image.new('RGBA',(size,size));draw=ImageDraw.Draw(image)
    m=round(size*.04);stroke=max(1,round(size/250))
    draw.ellipse((m,m,size-m-1,size-m-1),outline=TOKENS['gold'],width=stroke)
    draw.ellipse((m*2,m*2,size-m*2-1,size-m*2-1),outline=TOKENS['gold'],width=stroke)
    for sx,sy in ((1,1),(-1,1),(-1,-1),(1,-1)):
        cx=size/2+sx*size*.30;cy=size/2+sy*size*.30;length=size*.07
        draw.line((cx-sx*length,cy,cx,cy,cx,cy-sy*length),fill=TOKENS['orange'],width=stroke)
    # Outline técnico específico, sem imitar o medalhão oficial.
    key=next(s.key for s in SERVICES if s.code==code)
    symbol=diagram(key,(round(size*.32),round(size*.18)),.75)
    image.alpha_composite(symbol,(round(size*.34),round(size*.28)))
    draw_text(draw,code,Box(size*.2,size*.50,size*.6,size*.15),fonts,'technical','F3',TOKENS['bone'],
              max(12,round(size*.075)),max(10,round(size*.045)),1,'center')
    draw_text(draw,'ASSET PENDENTE',Box(size*.15,size*.67,size*.7,size*.10),fonts,'technical','F3',TOKENS['orange'],
              max(10,round(size*.036)),max(8,round(size*.025)),1,'center')
    return image


def compose(spec: CardSpec, size: tuple[int,int], app_root: Path) -> Composition:
    """F1 título+diagrama; F2 capítulo; F3 kernel+medalhão; F4 dado;
    F5 comparação/nota/CTA; F6 assinatura. Formatos remontados pelo grid.
    """
    from PIL import Image,ImageDraw,ImageOps
    if spec.family not in {'F1','F2','F3','F4','F5','F6'}: raise ValueError('Família desconhecida.')
    if spec.service_key and spec.service_key not in SERVICE_BY_KEY: raise ValueError('Serviço desconhecido.')
    if spec.family=='F3' and not spec.service_key: raise ValueError('F3 exige service_key.')
    if spec.image and spec.media_status not in MEDIA_STATUS: raise ValueError('Imagem exige etiqueta de status.')
    if len(spec.contacts)>3: raise ValueError('F6 permite até três canais principais.')
    for text in (spec.title,spec.body):
        errors=[v.message for v in validate_text(text,claims=list(spec.evidence)) if v.severity=='error']
        if errors: raise ValueError('; '.join(errors))
    grid=Grid(*size);unit=grid.scale;safe=grid.editorial;fonts=app_root/'assets/fonts'
    layers={'background':background(size)}
    for name in ('diagram','tag','title','medallion','data','footer'):
        layers[name]=Image.new('RGBA',size)
    result=Composition(layers,{})
    def box(name,x,y,w,h):
        value=Box(x,y,w,h)
        if not grid.safe.contains(value): raise ValueError('Layout invade safe area: '+name)
        result.bounds[name]=value;return value
    def text(name,content,b,role='body',maximum=42,lines=3,align='left',layer='data',color='bone'):
        if not content: return
        draw_text(ImageDraw.Draw(layers[layer]),content,b,fonts,role,spec.family,TOKENS[color],
                  round(maximum*unit),max(10,round(20*unit)),lines,align)
    def logo(b):
        path,_entry=resolve(app_root,'logo_primary')
        if path is None: result.pending_assets.append('logo_primary');return
        with Image.open(path) as opened: asset=ImageOps.contain(opened.convert('RGBA'),(round(b.width),round(b.height)),Image.Resampling.LANCZOS)
        layers['footer'].alpha_composite(asset,(round(b.x+(b.width-asset.width)/2),round(b.y+(b.height-asset.height)/2)))
    service=SERVICE_BY_KEY.get(spec.service_key)
    if service:
        drawing=diagram(service.key,(round(safe.width),round(safe.height)),.075 if spec.family=='F2' else .15)
        layers['diagram'].alpha_composite(drawing,(round(safe.x),round(safe.y)))
    draw=ImageDraw.Draw(layers['tag']);line_y=safe.y+48*unit
    draw.line((safe.x,line_y,safe.right,line_y),fill=palette_rgba('gold',110),width=max(1,round(unit)))
    draw.line((safe.x,line_y,safe.x+96*unit,line_y),fill=TOKENS['orange'],width=max(2,round(3*unit)))
    labels={'F1':'ABERTURA','F2':'PROCESSO','F3':'SERVIÇOS','F4':'EVIDÊNCIA','F5':'NOTA EDITORIAL','F6':'ASSINATURA'}
    tag='FR / '+labels[spec.family]+(' · '+spec.stage_number if spec.stage_number else '')
    if spec.family=='F3' and service: tag+=' · '+service.category
    text('tag',tag,box('tag',safe.x,safe.y,safe.width,40*unit),'technical',24,1,layer='tag',color='gold')
    if spec.family=='F3':
        # Kernel recebe nome, categoria, ativo, descrição curta e marca.
        k=grid.kernel
        if size[1]/size[0]>=1.6: k=Box(k.x,grid.snap(size[1]*.18),k.width,k.height)
        if not grid.safe.contains(k): raise ValueError('Kernel fora da área segura.')
        if k.y>safe.y+64*unit:
            text('category',service.category,box('category',k.x,k.y,k.width,32*unit),'technical',22,1,layer='tag',color='gold')
        text('title',spec.title or service.label,box('title',k.x,k.y+40*unit,k.width,100*unit),'title',64,1,layer='title')
        diameter=round(min(size)*.58)
        b=box('medallion',(size[0]-diameter)/2,k.y+176*unit,diameter,diameter)
        asset_id='medallion_'+service.key
        path,entry=resolve(app_root,asset_id)
        if path is None:
            asset=placeholder(diameter,service.code,fonts);result.pending_assets.append(asset_id)
        else:
            with Image.open(path) as opened:
                raw=opened.convert('RGBA');bbox=raw.getchannel('A').getbbox()
                asset=ImageOps.contain(raw.crop(bbox),(diameter,diameter),Image.Resampling.LANCZOS)
            if entry.get('normalized',{}).get('opaque_background_preserved'):
                result.warnings.append(asset_id+': fundo opaco preservado; conferir diâmetro aparente.')
        layers['medallion'].alpha_composite(asset,(round(b.x+(b.width-asset.width)/2),round(b.y+(b.height-asset.height)/2)))
        text('body',spec.body,box('body',k.x,k.bottom-116*unit,k.width-96*unit,48*unit),'body',27,1)
        index=next(i for i,s in enumerate(SERVICES,1) if s.key==service.key)
        text('code',f'{service.code} · SERVIÇO {index:02d}/13',box('code',k.x,k.bottom-56*unit,k.width-88*unit,40*unit),'technical',23,1,layer='footer',color='gold')
        logo(box('logo',k.right-80*unit,k.bottom-80*unit,80*unit,80*unit))
    else:
        y=safe.y+112*unit
        title_h=176*unit if spec.family in {'F1','F6'} else 120*unit
        text('title',spec.title,box('title',safe.x,y,safe.width,title_h),'title',72 if spec.family=='F1' else 60,2,layer='title')
        body_y=y+title_h+32*unit
        if spec.family=='F2': body_y+=safe.height*.10
        if spec.image:
            panel_h=min(safe.height*.38,440*unit)
            panel=box('media',safe.x,body_y,safe.width,panel_h)
            def place(path,target):
                with Image.open(path) as opened: asset=ImageOps.contain(opened.convert('RGBA'),(round(target.width),round(target.height)),Image.Resampling.LANCZOS)
                layers['medallion'].alpha_composite(asset,(round(target.x+(target.width-asset.width)/2),round(target.y+(target.height-asset.height)/2)))
            if spec.comparison_image:
                place(spec.image,Box(panel.x,panel.y,panel.width/2-4*unit,panel.height))
                place(spec.comparison_image,Box(panel.x+panel.width/2+4*unit,panel.y,panel.width/2-4*unit,panel.height))
                d=ImageDraw.Draw(layers['medallion']);d.line((panel.x+panel.width/2,panel.y,panel.x+panel.width/2,panel.bottom),fill=TOKENS['orange'],width=max(1,round(3*unit)))
            else: place(spec.image,panel)
            text('status',spec.media_status.upper(),box('status',safe.x,panel.bottom+8*unit,safe.width,36*unit),'technical',22,1,color='gold')
            body_y=panel.bottom+52*unit
        remaining=safe.bottom-body_y-148*unit
        if spec.family=='F6' and spec.contacts: remaining-=128*unit
        if remaining<40*unit and spec.body: raise ValueError('Texto/imagem excede layout desta família.')
        text('body',spec.body,box('body',safe.x,body_y,safe.width,max(40*unit,remaining)),
             'technical' if spec.family=='F4' else 'body',40,4)
        footer_y=safe.bottom-96*unit
        if spec.family=='F6' and spec.contacts:
            text('contacts','\n'.join(spec.contacts),box('contacts',safe.x,footer_y-120*unit,safe.width-128*unit,120*unit),'technical',24,3,layer='footer')
        text('footer','FRANCO ROMEU\nARTE & ENGENHARIA',box('footer',safe.x,footer_y,safe.width-128*unit,88*unit),'technical',23,2,layer='footer',color='gold')
        logo(box('logo',safe.right-96*unit,footer_y,96*unit,96*unit))
    return result
