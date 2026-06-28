"""
Professional template-based creative generation with Poppins fonts.
"""
import os, io, base64
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

CREATIVES_DIR = Path("/tmp/creatives")
CREATIVES_DIR.mkdir(parents=True, exist_ok=True)

UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")
W, H = 1080, 1080

TEAL  = (45,212,191); INK   = (244,247,246); MINT  = (167,232,220)
DARK  = (14,24,34);   DARK2 = (19,32,46);    MUTED = (126,143,160)
WHITE = (255,255,255)

FONT_PATHS = {
    "bold":    "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf",
    "medium":  "/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf",
    "regular": "/usr/share/fonts/truetype/google-fonts/Poppins-Regular.ttf",
    "light":   "/usr/share/fonts/truetype/google-fonts/Poppins-Light.ttf",
}
FALLBACK_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FALLBACK_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def _f(style, size):
    primary = FONT_PATHS.get(style, FONT_PATHS["regular"])
    fallback = FALLBACK_BOLD if "bold" in style else FALLBACK_REG
    for p in [primary, fallback]:
        if Path(p).exists():
            try: return ImageFont.truetype(p, size)
            except: continue
    return ImageFont.load_default()

def _logo(size=70):
    for p in ["app/static/logo_b64.txt", "/tmp/logo_b64.txt"]:
        if Path(p).exists():
            try:
                img = Image.open(io.BytesIO(base64.b64decode(Path(p).read_text().strip()))).convert("RGBA")
                return img.resize((size, size), Image.LANCZOS)
            except: pass
    return None

def _fetch_photo(topic, niche):
    if not UNSPLASH_ACCESS_KEY: return None
    for q in [f"{topic} {niche}", niche, "professional business"]:
        try:
            r = requests.get("https://api.unsplash.com/search/photos",
                params={"query": q, "per_page": 3, "orientation": "squarish"},
                headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}, timeout=10)
            results = r.json().get("results", [])
            if results:
                url = results[0]["urls"].get("regular")
                img = Image.open(io.BytesIO(requests.get(url, timeout=30).content)).convert("RGBA")
                return _crop(img)
        except: continue
    return None

def _crop(img):
    r = max(W/img.width, H/img.height)
    img = img.resize((int(img.width*r), int(img.height*r)), Image.LANCZOS)
    return img.crop(((img.width-W)//2, (img.height-H)//2, (img.width+W)//2, (img.height+H)//2))

def _wrap(text, font, max_px, draw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = f"{cur} {w}".strip()
        if draw.textbbox((0,0), t, font=font)[2] <= max_px: cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def _shadow(draw, xy, text, font, color):
    x, y = xy
    draw.text((x+4,y+4), text, font=font, fill=(0,0,0,180))
    draw.text((x,y), text, font=font, fill=color)

def _brackets(img, color=TEAL, a=160):
    d = Image.new("RGBA",(W,H),(0,0,0,0)); draw = ImageDraw.Draw(d)
    p,s,c = 32,90,(*color,a)
    for pts in [[(p,p+s),(p,p),(p+s,p)],[(W-p-s,p),(W-p,p),(W-p,p+s)],
                [(p,H-p-s),(p,H-p),(p+s,H-p)],[(W-p-s,H-p),(W-p,H-p),(W-p,H-p-s)]]:
        draw.line(pts, fill=c, width=3)
    return Image.alpha_composite(img, d)

def _footer(img, name, website):
    d = Image.new("RGBA",(W,H),(0,0,0,0)); draw = ImageDraw.Draw(d)
    fy = H-108
    draw.line([(72,fy),(W-72,fy)], fill=(*TEAL,60), width=1)
    lg = _logo(64)
    lx, ly = 88, fy+10
    if lg: img.paste(lg,(lx,ly),lg); tx=lx+78
    else: tx=lx
    draw.text((tx,fy+12), name, font=_f("bold",19), fill=(*TEAL,255))
    draw.text((tx,fy+40), "Crafting Digital Influence", font=_f("light",14), fill=(*MINT,180))
    wf = _f("light",14); wb = draw.textbbox((0,0),website,font=wf)
    draw.text((W-88-(wb[2]-wb[0]),fy+26), website, font=wf, fill=(180,180,180,180))
    return Image.alpha_composite(img, d)

def _tpl_dark(cover, subtext, name, website):
    img = Image.new("RGBA",(W,H),(*DARK,255))
    draw = ImageDraw.Draw(img)
    for x in range(0,W,64): draw.line([(x,0),(x,H)], fill=(*TEAL,8), width=1)
    for y in range(0,H,64): draw.line([(0,y),(W,y)], fill=(*TEAL,8), width=1)
    draw.rectangle([(0,0),(W,8)], fill=(*TEAL,255))
    img = _brackets(img); draw = ImageDraw.Draw(img)
    draw.text((88,32), "INFLUZ STUDIO", font=_f("medium",18), fill=(*TEAL,200))
    draw.line([(88,68),(W-88,68)], fill=(*TEAL,30), width=1)
    words = cover.split(); mid = max(1,len(words)//2)
    p1,p2 = " ".join(words[:mid])," ".join(words[mid:])
    for fs in [82,70,60,52,44]:
        hf = _f("bold",fs)
        l1=_wrap(p1,hf,W-180,draw); l2=_wrap(p2,hf,W-180,draw)
        if (len(l1)+len(l2))*(fs+16)<400: break
    total = (len(l1)+len(l2))*(fs+16)
    y = (H-total)//2 - 20
    for line in l1:
        bb=draw.textbbox((0,0),line,font=hf); x=(W-(bb[2]-bb[0]))//2
        _shadow(draw,(x,y),line,hf,(*INK,255)); y+=fs+14
    y+=10
    for line in l2:
        bb=draw.textbbox((0,0),line,font=hf); x=(W-(bb[2]-bb[0]))//2
        _shadow(draw,(x,y),line,hf,(*TEAL,255)); y+=fs+14
    if subtext:
        sf=_f("regular",26)
        for line in _wrap(subtext,sf,W-200,draw)[:2]:
            bb=draw.textbbox((0,0),line,font=sf); x=(W-(bb[2]-bb[0]))//2
            draw.text((x,y+16),line,font=sf,fill=(*MINT,200)); y+=38
    return _footer(img,name,website)

def _tpl_photo(photo, cover, subtext, name, website):
    img = ImageEnhance.Brightness(photo.convert("RGBA")).enhance(0.6)
    img = ImageEnhance.Color(img).enhance(0.8)
    ov = Image.new("RGBA",(W,H),(0,0,0,0)); d = ImageDraw.Draw(ov)
    for y in range(H):
        a = int(min(240, 250*max(0,(y-H*0.3)/(H*0.7))**1.1))
        d.line([(0,y),(W,y)], fill=(*DARK,a))
    img = Image.alpha_composite(img, ov)
    img = _brackets(img); draw = ImageDraw.Draw(img)
    draw.line([(88,80),(124,80)], fill=(*TEAL,220), width=2)
    draw.text((132,68), "INFLUZ STUDIO", font=_f("medium",18), fill=(*TEAL,220))
    words = cover.split(); mid = max(1,len(words)//2)
    p1,p2 = " ".join(words[:mid])," ".join(words[mid:])
    for fs in [82,70,60,52,44]:
        hf = _f("bold",fs)
        l1=_wrap(p1,hf,W-176,draw); l2=_wrap(p2,hf,W-176,draw)
        if (len(l1)+len(l2))*(fs+14)<320: break
    y = H-(len(l1)+len(l2))*(fs+14)-180
    draw.line([(88,y-10),(88,y+(len(l1)+len(l2))*(fs+14)+20)], fill=(*TEAL,180), width=5)
    for line in l1: _shadow(draw,(100,y),line,hf,(*INK,255)); y+=fs+12
    y+=8
    for line in l2: _shadow(draw,(100,y),line,hf,(*TEAL,255)); y+=fs+12
    if subtext:
        sf=_f("light",24)
        for line in _wrap(subtext,sf,W-176,draw)[:2]:
            _shadow(draw,(100,y),line,sf,(*MINT,200)); y+=34
    return _footer(img,name,website)

def _tpl_poll(cover, options_text, name, website):
    img = Image.new("RGBA",(W,H),(*DARK2,255))
    draw = ImageDraw.Draw(img)
    for x in range(0,W,80): draw.line([(x,0),(x,H)], fill=(*TEAL,5), width=1)
    for y in range(0,H,80): draw.line([(0,y),(W,y)], fill=(*TEAL,5), width=1)
    draw.rectangle([(0,0),(W,108)], fill=(*DARK,255))
    draw.line([(0,108),(W,108)], fill=(*TEAL,80), width=2)
    draw.text((88,36), "INFLUZ STUDIO", font=_f("medium",22), fill=(*TEAL,230))
    img = _brackets(img); draw = ImageDraw.Draw(img)
    qf = _f("bold",70); q_lines = _wrap(cover,qf,W-160,draw)[:3]
    y = 160
    for line in q_lines: _shadow(draw,(88,y),line,qf,(*INK,255)); y+=82
    parts = [p.strip() for p in options_text.split("|")] if "|" in options_text else ["YES","NO"]
    colors = [TEAL,(248,113,113)]
    btn_y = y+60
    for i,(opt,col) in enumerate(zip(parts[:2],colors)):
        draw.rounded_rectangle([(88,btn_y),(W-88,btn_y+108)], radius=16,
            fill=(*col,25), outline=(*col,180), width=3)
        draw.ellipse([(110,btn_y+22),(172,btn_y+86)], fill=(*col,220))
        ic = "+" if i==0 else "x"
        iff = _f("bold",38)
        bb = draw.textbbox((0,0),ic,font=iff)
        draw.text((141-(bb[2]-bb[0])//2, btn_y+30),ic,font=iff,fill=(*WHITE,255))
        draw.text((192,btn_y+28),opt,font=_f("bold",40),fill=(*INK,255))
        btn_y += 126
    return _footer(img,name,website)

def _tpl_carousel(cover, content, slide, total, name, website):
    img = Image.new("RGBA",(W,H),(*DARK,255))
    draw = ImageDraw.Draw(img)
    panel = Image.new("RGBA",(W,H),(0,0,0,0)); pd=ImageDraw.Draw(panel)
    for x in range(200): pd.line([(x,0),(x,H)], fill=(*TEAL,int(60*(1-x/200))))
    img = Image.alpha_composite(img, panel)
    img = _brackets(img); draw = ImageDraw.Draw(img)
    bw = W-144
    draw.rectangle([(72,50),(W-72,56)], fill=(*TEAL,25))
    draw.rectangle([(72,50),(72+int(bw*slide/total),56)], fill=(*TEAL,200))
    draw.text((88,66), f"{slide:02d} / {total:02d}", font=_f("medium",18), fill=(*MUTED,200))
    draw.text((W-260,H//2-150), str(slide), font=_f("bold",300), fill=(*TEAL,10))
    tf=_f("bold",68); t_lines=_wrap(cover,tf,W-180,draw)[:3]
    y=150
    for line in t_lines: _shadow(draw,(88,y),line,tf,(*INK,255)); y+=80
    y+=20; draw.line([(88,y),(W-88,y)], fill=(*TEAL,60), width=2); y+=30
    if content:
        sf=_f("regular",28)
        for line in _wrap(content,sf,W-180,draw)[:4]:
            draw.ellipse([(88,y+10),(102,y+24)], fill=(*TEAL,255))
            draw.text((118,y),line,font=sf,fill=(*MINT,220)); y+=46
    return _footer(img,name,website)


def generate_photo_creative(item_id, cover_text, image_text, post_type,
                             topic, niche="", client_photo_path=None,
                             business_name="Influz Studio",
                             website="influzstudio.netlify.app") -> str:
    photo = None
    pt = post_type.lower()

    if client_photo_path and Path(client_photo_path).exists():
        photo = Image.open(client_photo_path).convert("RGBA")
        photo = _crop(photo)
    elif pt not in ["story","carousel"]:
        photo = _fetch_photo(topic, niche)

    cover = cover_text or topic
    subtext = image_text or ""

    if pt == "story":
        final = _tpl_poll(cover, subtext, business_name, website)
    elif pt == "carousel":
        final = _tpl_carousel(cover, subtext, 1, 5, business_name, website)
    elif photo is not None:
        final = _tpl_photo(photo, cover, subtext, business_name, website)
    else:
        final = _tpl_dark(cover, subtext, business_name, website)

    output = CREATIVES_DIR / f"item_{item_id}_photo.png"
    final.convert("RGB").save(str(output), "PNG", compress_level=1)
    return f"creatives/item_{item_id}_photo.png"
