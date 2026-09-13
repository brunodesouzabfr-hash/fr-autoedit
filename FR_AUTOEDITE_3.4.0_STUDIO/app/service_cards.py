"""Service-aware layouts with real media panels and bounded typography."""
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace


def text_fit(c, draw, text, box, font_name, max_size, color, max_lines=6):
    x, y, right, bottom = box
    text = str(text or "")
    if not text:
        return y
    for size in range(max(9, int(max_size)), 8, -1):
        f = c.font(font_name, size)
        # Long unbroken words are split by available pixel width.
        words = []
        for word in text.split():
            part = ""
            for char in word:
                if part and draw.textlength(part + char, font=f) > right-x:
                    words.append(part)
                    part = ""
                part += char
            words.append(part)
        lines, line = [], ""
        for word in words:
            new = (line + " " + word).strip()
            if line and draw.textlength(new, font=f) > right-x:
                lines.append(line)
                line = word
            else:
                line = new
        if line:
            lines.append(line)
        line_h = size * 1.25
        if len(lines) <= max_lines and len(lines)*line_h <= bottom-y:
            for line in lines:
                draw.text((x, y), line, font=f, fill=color, anchor="lt")
                y += line_h
            return y
    raise c.AutoEditeError("O texto não cabe no card sem perder leitura. Reduza title/body ou divida em dois cards.")


def draw_service_motif(c, draw, layout, box, palette, unit, *, subtle=False):
    """Desenha uma camada técnica sóbria e específica do serviço.

    A camada é deliberadamente estática. O render atual pode animar o card
    completo, mas ainda não possui composição temporal independente por
    elemento; `motion_hint` no catálogo prepara essa evolução sem prometer uma
    animação que o arquivo PNG não executa.
    """
    x0, y0, x1, y1 = map(int, box)
    if x1 <= x0 or y1 <= y0:
        return
    orange = c.hex_rgb(palette.get("orange", "#FC7016")) + ((42 if subtle else 125),)
    gold = c.hex_rgb(palette.get("gold", "#C8A034")) + ((36 if subtle else 105),)
    border = c.hex_rgb(palette.get("border", "#1A6069")) + ((45 if subtle else 145),)
    bone = c.hex_rgb(palette.get("bone", "#E6D6B5")) + ((28 if subtle else 90),)
    weight = max(1, int(unit / (520 if subtle else 360)))
    width, height = x1 - x0, y1 - y0

    if layout in {"blueprint", "pagination", "foundation"}:
        step = max(22, int(unit * .045))
        for x in range(x0, x1 + 1, step):
            draw.line((x, y0, x, y1), fill=border, width=weight)
        for y in range(y0, y1 + 1, step):
            draw.line((x0, y, x1, y), fill=border, width=weight)
        draw.arc((x0 + width*.14, y0 + height*.12, x0 + width*.72, y0 + height*.82), 205, 350, fill=gold, width=weight)
        draw.line((x0 + width*.18, y0 + height*.72, x0 + width*.78, y0 + height*.28), fill=orange, width=weight)
    elif layout == "electrical":
        points = [(x0, y0 + height*.28), (x0 + width*.27, y0 + height*.28),
                  (x0 + width*.39, y0 + height*.50), (x0 + width*.70, y0 + height*.50),
                  (x1, y0 + height*.72)]
        draw.line(points, fill=orange, width=max(weight, int(unit*.005)), joint="curve")
        radius = max(4, int(unit*.012))
        for index, (x, y) in enumerate(points):
            draw.ellipse((x-radius, y-radius, x+radius, y+radius), outline=gold,
                         fill=orange if index in {0, len(points)-1} else None, width=weight)
        for offset in (.12, .84):
            draw.arc((x0 + width*offset - unit*.06, y0 + height*.12,
                      x0 + width*offset + unit*.06, y0 + height*.88), 70, 290, fill=border, width=weight)
    elif layout == "hydraulic":
        pipe_w = max(weight * 2, int(unit*.007))
        pipe = [(x0, y0 + height*.30), (x0 + width*.34, y0 + height*.30),
                (x0 + width*.34, y0 + height*.65), (x0 + width*.72, y0 + height*.65),
                (x0 + width*.72, y0 + height*.40), (x1, y0 + height*.40)]
        draw.line(pipe, fill=border, width=pipe_w, joint="curve")
        for x, y in pipe[1:-1]:
            radius = pipe_w + 3
            draw.ellipse((x-radius, y-radius, x+radius, y+radius), outline=bone, width=weight)
        for index in range(4):
            x = x0 + width*(.44 + index*.08)
            y = y0 + height*(.57 - (index % 2)*.04)
            draw.ellipse((x-unit*.006, y-unit*.010, x+unit*.006, y+unit*.010), fill=gold)
    elif layout == "installation":
        cx, cy, radius = x0 + width*.67, y0 + height*.50, min(width, height)*.27
        draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), outline=gold, width=max(weight, 2))
        draw.ellipse((cx-radius*.55, cy-radius*.55, cx+radius*.55, cy+radius*.55), outline=border, width=weight)
        draw.line((cx-radius*1.30, cy, cx+radius*1.30, cy), fill=orange, width=weight)
        draw.line((cx, cy-radius*1.30, cx, cy+radius*1.30), fill=orange, width=weight)
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            draw.line((cx+dx*radius*.82, cy+dy*radius*.82,
                       cx+dx*radius*1.06, cy+dy*radius*.82), fill=bone, width=weight)
    elif layout == "maintenance":
        gap = height / 5
        size = max(8, int(unit*.020))
        for index in range(4):
            x, y = x0 + width*.52, y0 + gap*(index+1)
            draw.rounded_rectangle((x, y, x+size, y+size), radius=max(2, size//5), outline=gold, width=weight)
            if index < 3:
                draw.line((x+size*.18, y+size*.52, x+size*.43, y+size*.78,
                           x+size*1.08, y-size*.10), fill=orange, width=max(2, weight))
            draw.line((x+size*1.55, y+size*.50, x1, y+size*.50), fill=border, width=weight)
    elif layout in {"layers", "material_macro"}:
        for index, color in enumerate((border, gold, orange)):
            y = y0 + height*(.35 + index*.11)
            draw.line((x0 + width*.08, y, x1 - width*.08, y-height*.10),
                      fill=color, width=max(weight, int(unit*(.006 + index*.002))))
        for index in range(9):
            x = x0 + width*(.12 + (index % 5)*.17)
            y = y0 + height*(.16 + (index // 5)*.62)
            r = max(2, int(unit*(.004 + (index % 3)*.002)))
            draw.ellipse((x-r, y-r, x+r, y+r), fill=orange if index % 2 else gold)
    elif layout == "light":
        cx, cy = x0 + width*.68, y0 + height*.30
        for spread, alpha in ((.46, border), (.31, gold), (.17, orange)):
            draw.polygon(((cx, cy), (cx-width*spread, y1), (cx+width*spread, y1)), fill=alpha)
    elif layout in {"joinery", "sequence"}:
        for index in range(4):
            inset = index * min(width, height) * .055
            draw.rounded_rectangle((x0+inset, y0+inset, x1-inset, y1-inset),
                                   radius=max(3, int(unit*.009)), outline=gold if index == 1 else border, width=weight)


def render_service_card(env, path, segment, plan, brand, style, project):
    c = SimpleNamespace(**env)
    from PIL import Image, ImageDraw, ImageOps
    from media_frames import extract_reference
    key = str(segment.get("service_key") or segment.get("service_id") or "")
    visual = segment.get("visual")
    comparison = segment.get("comparison")
    if not (visual or comparison or key and style.get("cards", {}).get("service_adaptive_layout", True)):
        return False
    catalog = c.load_service_catalog()
    service = catalog.get(key, {})
    layout = service.get("layout", "editorial")
    w, h = int(plan["output"]["width"]), int(plan["output"]["height"])
    vertical = h > w * 1.1
    pal = style["palette"]
    bg, bone, orange, gold = (pal[k] for k in ("background", "bone", "orange", "gold"))
    canvas = Image.new("RGBA", (w, h), bg)
    draw = ImageDraw.Draw(canvas)
    m = max(12, int(w * .065))
    unit = min(w, h)
    fonts = style["fonts"]
    title_font, body_font, mono = fonts["title"], fonts["body"], fonts["technical"]
    heading = service.get("label", "FR / PROCESSO")
    bubble_style = str(style.get("cards", {}).get("bubble_style") or "glass")
    heading_box = (m, int(h*.075), int(w*.76), int(h*.155))
    bubble_fill = None
    bubble_outline = None
    if bubble_style == "solid":
        bubble_fill = c.hex_rgb(pal.get("surface", "#123F34")) + (248,)
    elif bubble_style == "glass":
        bubble_fill = c.hex_rgb(pal.get("surface", "#123F34")) + (176,)
        bubble_outline = c.hex_rgb(pal.get("border", "#1A6069")) + (175,)
    elif bubble_style == "outline":
        bubble_outline = c.hex_rgb(pal.get("gold", "#C8A034")) + (155,)
    if bubble_fill or bubble_outline:
        draw.rounded_rectangle(
            heading_box, radius=max(7, int(unit*.018)), fill=bubble_fill,
            outline=bubble_outline, width=max(1, int(unit*.002)),
        )
    draw.rounded_rectangle(
        (m, int(h*.075), m+max(4,int(w*.008)), int(h*.155)),
        radius=max(2, int(unit*.004)), fill=orange,
    )
    text_fit(c, draw, heading, (m*1.28, h*.092, w*.72, h*.145), mono, unit*.025, gold, 2)
    if style.get("logo", {}).get("persistent_on_cards", True):
        c.paste_logo_at(canvas, c.logo_path_for(project, style), int(unit*.10), int(unit*.10),
                        (w-m, int(h*.075)), anchor="ra", opacity=245)
    # Estrutura procedural específica por serviço, sem dados técnicos fictícios.
    draw_service_motif(c, draw, layout, (m, h*.17, w-m, h*.84), pal, unit, subtle=True)
    # Uma camada externa instalada ocupa o mesmo papel do motivo procedural e
    # permanece sob textos/fotos. Slot ausente é esperado e não gera ruído.
    try:
        from style_engine import load_style_pack, resolve_asset, StylePackError
        pack_id = str(plan.get("style_pack_id") or "fr_chiaroscuro_vintage_v1")
        pack = load_style_pack(c.APP_ROOT, pack_id)
        service_slot = pack.get("services", {}).get(key, {}).get("asset_id")
        if service_slot:
            asset_path = resolve_asset(c.APP_ROOT, pack_id, service_slot)
            with Image.open(asset_path) as opened:
                layer = ImageOps.contain(opened.convert("RGBA"), (w, h), Image.Resampling.LANCZOS)
            canvas.alpha_composite(layer, ((w - layer.width) // 2, (h - layer.height) // 2))
            draw = ImageDraw.Draw(canvas)
    except (StylePackError, OSError):
        pass
    if vertical:
        title_box = (m, h*.17, w-m, h*.285)
        panel = (m, h*.29, w-m, h*.70)
        body_box = (m, h*.725, w-m, h*.85)
    else:
        title_box = (m, h*.25, w*.46, h*.53)
        body_box = (m, h*.57, w*.46, h*.80)
        panel = (w*.52, h*.23, w-m, h*.79)
    if str(segment.get("body") or "").strip() and bubble_style != "minimal":
        bx0, by0, bx1, by1 = map(int, body_box)
        pad = max(5, int(unit*.012))
        body_fill = c.hex_rgb(pal.get("surface", "#123F34")) + ((225 if bubble_style == "solid" else 138),)
        body_outline = c.hex_rgb(pal.get("gold" if bubble_style == "outline" else "border", "#1A6069")) + (145,)
        draw.rounded_rectangle(
            (bx0-pad, by0-pad, bx1+pad, by1+pad), radius=max(8, int(unit*.018)),
            fill=None if bubble_style == "outline" else body_fill,
            outline=body_outline, width=max(1, int(unit*.002)),
        )
    text_fit(c, draw, segment.get("title") or service.get("label") or "FRANCO ROMEU", title_box,
             title_font, unit*.064, bone, 4)
    text_fit(c, draw, segment.get("body") or "", body_box, body_font, unit*.035, bone, 6)

    def place_reference(ref, box):
        x, y, right, bottom = map(int, box)
        label_h = int(unit * .043) if ref.get("label") else 0
        source = extract_reference(env, project, ref, plan.get("output", {}).get("render_source") == "proxies")
        with Image.open(source) as im:
            img = ImageOps.exif_transpose(im).convert("RGBA")
        # Contain preserves evidence and avoids cutting fixtures or dimensions.
        img.thumbnail((right-x, max(1,bottom-y-label_h)), Image.Resampling.LANCZOS)
        canvas.alpha_composite(img, (x+(right-x-img.width)//2, y+(bottom-y-label_h-img.height)//2))
        draw.rectangle((x, y, right, bottom-label_h), outline=gold, width=max(1,w//700))
        if label_h:
            text_fit(c, draw, ref["label"], (x, bottom-label_h+3, right, bottom), mono, unit*.024, gold, 1)

    if comparison:
        x, y, right, bottom = panel
        gap = unit*.02
        mid = (x+right)/2
        for ref, box in ((comparison["before"], (x, y, mid-gap/2, bottom)),
                         (comparison["after"], (mid+gap/2, y, right, bottom))):
            place_reference(ref, box)
    elif visual:
        place_reference(visual, panel)
    else:
        # Official service asset acts only as an illustration of the category.
        x,y,right,bottom = panel
        # O serviço é a âncora visual do card, com presença maior que os
        # elementos decorativos e sem invadir título, corpo ou rodapé.
        size = int(min(right-x,bottom-y)*.94)
        asset = c.ASSETS / service.get("asset", "")
        if asset.is_file():
            shadow = max(5, int(unit*.012))
            cx, cy = int((x+right)/2), int((y+bottom)/2)
            draw.ellipse((cx-size//2-shadow, cy-size//2-shadow,
                          cx+size//2+shadow, cy+size//2+shadow),
                         fill=(0, 0, 0, 72), outline=gold, width=max(1, int(unit*.003)))
            c.paste_service_symbol(canvas, asset, (int((x+right)/2), int((y+bottom)/2)), size,
                                   orange, gold, pal.get("border", "#123F34"))
        if layout == "layers":
            for i,color in enumerate((pal.get("surface", bg), bone, orange)):
                draw.rectangle((x+i*(right-x)/3, bottom+unit*.02, x+(i+1)*(right-x)/3-2, bottom+unit*.029), fill=color)
        elif layout == "sequence":
            for i in range(3):
                xx=x+i*(right-x)/3
                draw.rectangle((xx, bottom+unit*.02, xx+(right-x)/3-6, bottom+unit*.024), fill=gold)
        elif layout == "material_macro":
            draw.line((x, bottom+unit*.02, right, bottom+unit*.02), fill=orange, width=max(2,int(unit*.007)))
        elif layout == "joinery":
            for xx in (x,right):
                draw.line((xx, y, xx, bottom), fill=orange, width=max(2,w//350))
        elif layout == "light":
            draw.line((x, bottom+unit*.025, right, bottom+unit*.025), fill=gold, width=max(2,w//260))
    footer = "FRANCO ROMEU · ARTE & ENGENHARIA"
    if style.get("cards", {}).get("show_contacts_on_every_card"):
        footer = brand["contacts"].get("instagram", "") + " · " + brand["contacts"].get("whatsapp", "")
    draw.line((m,h*.885,w-m,h*.885),fill=orange,width=max(1,w//450))
    text_fit(c,draw,footer,(m,h*.90,w-m,h*.955),mono,unit*.021,gold,2)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    c.save_card_image(canvas, path)
    return True
