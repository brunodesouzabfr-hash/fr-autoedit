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


def render_service_card(env, path, segment, plan, brand, style, project):
    c = SimpleNamespace(**env)
    from PIL import Image, ImageDraw, ImageOps
    from media_frames import extract_reference
    key = str(segment.get("service_key") or "")
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
    draw.rectangle((m, int(h*.085), m+max(3,w*.005), int(h*.16)), fill=orange)
    heading = service.get("label", "FR / PROCESSO")
    text_fit(c, draw, heading, (m*1.25, h*.085, w*.77, h*.14), mono, unit*.025, gold, 2)
    if style.get("logo", {}).get("persistent_on_cards", True):
        c.paste_logo_at(canvas, c.logo_path_for(project, style), int(unit*.10), int(unit*.10),
                        (w-m, int(h*.075)), anchor="ra", opacity=245)
    # Material motifs are editorial structure, never fabricated measurement data.
    line_color = c.hex_rgb(pal.get("surface", "#123F34")) + (180,)
    if layout in {"blueprint", "pagination", "foundation"}:
        step = max(24, unit//12)
        for x in range(m, w-m, step):
            draw.line((x, h*.18, x, h*.80), fill=line_color, width=1)
        for y in range(int(h*.18), int(h*.80), step):
            draw.line((m, y, w-m, y), fill=line_color, width=1)
    if vertical:
        title_box = (m, h*.18, w-m, h*.31)
        panel = (m, h*.345, w-m, h*.66)
        body_box = (m, h*.70, w-m, h*.84)
    else:
        title_box = (m, h*.25, w*.46, h*.53)
        body_box = (m, h*.57, w*.46, h*.80)
        panel = (w*.52, h*.23, w-m, h*.79)
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
        size = int(min(right-x,bottom-y)*.80)
        asset = c.ASSETS / service.get("asset", "")
        if asset.is_file():
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
    canvas.convert("RGB").save(path,quality=96)
    return True
