"""Treze diagramas distintos, sem medidas fictícias. Cada traço pertence a uma forma ou conexão."""
from math import cos, sin, pi
from ..core.config import SERVICE_BY_KEY, palette_rgba


def render(service_key: str, size: tuple[int, int], opacity=.15):
    from PIL import Image, ImageDraw
    if service_key not in SERVICE_BY_KEY: raise ValueError('Serviço não catalogado.')
    width, height = size
    image = Image.new('RGBA', size)
    draw = ImageDraw.Draw(image)
    color = palette_rgba('tech', round(255*opacity))
    gold = palette_rgba('gold', round(255*opacity))
    stroke = max(1, round(min(size)/540))
    def p(x,y): return (round(width*x),round(height*y))
    def line(points, fill=color): draw.line([p(*v) for v in points], fill=fill, width=stroke)
    def box(x,y,w,h,fill=color):
        draw.rectangle((*p(x,y),*p(x+w,y+h)), outline=fill, width=stroke)
    def node(x,y,r=.008):
        draw.ellipse((*p(x-r,y-r),*p(x+r,y+r)),outline=gold,width=stroke)
    def arrow(a,b):
        line([a,b],gold)
        dx,dy=b[0]-a[0],b[1]-a[1]
        norm=max((dx*dx+dy*dy)**.5,.0001)
        ux,uy=dx/norm*.016,dy/norm*.016
        line([(b[0]-ux-uy*.5,b[1]-uy+ux*.5),b,
              (b[0]-ux+uy*.5,b[1]-uy-ux*.5)],gold)
    if service_key == 'alvenaria':
        box(.06,.12,.88,.70)
        for row in range(7):
            y=.12+row*.10
            line([(.06,y),(.94,y)])
            for col in range(5):
                x=.06+col*.176+(row%2)*.088
                if x < .94: line([(x,y),(x,min(.82,y+.10))])
        line([(.97,.12),(.97,.82)],gold); node(.97,.12);node(.97,.82)
    elif service_key == 'criacoes':
        for i in range(3):
            x=.08+i*.31
            line([(x,.55),(x+.04,.28),(x+.21,.35),(x+.23,.61),(x,.55)])
            line([(x,.55),(x+.21,.35),(x+.04,.28)])
            if i < 2: arrow((x+.23,.47),(x+.30,.47))
        line([(.08,.76),(.92,.76)],gold);node(.08,.76);node(.92,.76)
    elif service_key == 'eletrica':
        box(.06,.34,.13,.32);line([(.19,.5),(.31,.5),(.31,.23),(.90,.23)])
        line([(.31,.5),(.31,.78),(.90,.78)])
        for x in (.45,.65,.85):
            line([(x,.23),(x,.43)]);node(x,.43,.02)
            line([(x,.78),(x,.58)]);node(x,.58,.02)
            line([(x-.012,.42),(x+.012,.44)],gold)
    elif service_key == 'hidraulica':
        route=[(.06,.64),(.29,.42),(.52,.65),(.74,.43),(.92,.43)]
        line(route);line([(x,y+.025) for x,y in route])
        for x,y in route[1:-1]: node(x,y,.014)
        arrow((.33,.48),(.43,.58));arrow((.77,.43),(.88,.43))
        line([(.52,.65),(.52,.30)],gold)
        line([(.49,.28),(.55,.32),(.49,.32),(.55,.28),(.49,.28)],gold)
    elif service_key == 'iluminacao':
        box(.08,.12,.84,.74)
        for x in (.22,.50,.78):
            node(x,.24,.016)
            line([(x,.24),(x-.12,.73),(x+.12,.73),(x,.24)])
            for spread in (.06,.09):
                points=[(x+cos(a)*spread,.55+sin(a)*spread) for a in [pi*j/24 for j in range(25)]]
                line(points,gold)
    elif service_key == 'instalacao':
        for i in range(3):
            x=.09+i*.28;y=.48-i*.07
            line([(x,y),(x+.14,y-.14),(x+.24,y-.08),(x+.10,y+.06),(x,y)])
            line([(x+.10,y+.06),(x+.10,y+.19),(x+.24,y+.05),(x+.24,y-.08)])
            if i < 2: arrow((x+.22,y+.16),(x+.30,y+.09))
        line([(.08,.81),(.88,.33)],gold);node(.08,.81);node(.88,.33)
    elif service_key == 'manutencao':
        points=[(.15,.22),(.75,.22),(.75,.70),(.15,.70)]
        for i,(x,y) in enumerate(points):
            box(x,y,.10,.10)
            line([(x+.025,y+.05),(x+.045,y+.075),(x+.08,y+.025)],gold)
            other=points[(i+1)%4]
            arrow((x+.05,y+.05),(other[0]+.05,other[1]+.05))
        node(.5,.5,.10)
    elif service_key == 'moveis':
        box(.08,.20,.84,.56)
        for x in (.29,.5,.71): line([(x,.20),(x,.76)])
        for y in (.39,.57):line([(.50,y),(.92,y)])
        for x in (.24,.45,.60,.81):node(x,.47,.006)
        line([(.08,.85),(.92,.85)],gold)
        for x in (.08,.29,.50,.71,.92):line([(x,.80),(x,.88)],gold)
    elif service_key == 'pintura':
        for i in range(4):
            y=.22+i*.12
            line([(.08,y),(.85,y),(.92,y-.05),(.15,y-.05),(.08,y)])
            line([(.08,y),(.08,y+.07),(.85,y+.07),(.85,y)])
        box(.78,.76,.13,.05,gold);line([(.78,.785),(.71,.785),(.71,.91)],gold)
    elif service_key == 'producoes':
        box(.16,.12,.68,.27);box(.08,.10,.08,.14);box(.84,.10,.08,.14)
        for r in range(4):
            for c in range(6):box(.12+c*.13,.46+r*.09,.065,.038)
        arrow((.06,.91),(.06,.30));arrow((.94,.91),(.94,.30))
        line([(.13,.90),(.86,.90)],gold)
        for x in (.13,.38,.62,.86):node(x,.90)
    elif service_key == 'projetos_3d':
        box(.08,.12,.36,.32);line([(.08,.27),(.26,.27),(.26,.44)])
        box(.55,.12,.36,.32);line([(.55,.32),(.91,.32)]);box(.64,.18,.09,.14)
        line([(.08,.83),(.08,.61),(.42,.61),(.42,.83),(.08,.83)])
        line([(.57,.68),(.72,.54),(.91,.65),(.76,.81),(.57,.68)])
        line([(.57,.68),(.57,.84),(.76,.95),(.91,.79),(.91,.65)])
        line([(.76,.81),(.76,.95)])
    elif service_key == 'revestimentos':
        for r in range(4):
            for c in range(5):box(.10+c*.16,.13+r*.14,.148,.128)
        line([(.10,.78),(.90,.78),(.90,.83),(.10,.83),(.10,.78)],gold)
        line([(.50,.08),(.50,.72)],gold);node(.50,.08);node(.50,.72)
    elif service_key == 'textura':
        for i in range(5):
            points=[(.08+j*.008,.24+i*.12+sin(j*.32+i)*.016) for j in range(106)]
            line(points, gold if i==0 else color)
        line([(.65,.20),(.75,.10),(.91,.23),(.80,.34),(.65,.20)],gold)
        arrow((.69,.38),(.47,.57))
    return image
