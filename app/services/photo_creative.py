"""
High-quality photo creative generation using Poppins fonts.
"""
import os, io, base64
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

CREATIVES_DIR = Path("/tmp/creatives")
CREATIVES_DIR.mkdir(parents=True, exist_ok=True)

UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")
W, H = 1080, 1080

# Brand colors
TEAL    = (45, 212, 191)
INK     = (244, 247, 246)
MINT    = (167, 232, 220)
DARK    = (14, 24, 34)
BLACK   = (0, 0, 0)

# Font paths
FONTS = {
    "black":   "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf",
    "bold":    "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf",
    "medium":  "/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf",
    "regular": "/usr/share/fonts/truetype/google-fonts/Poppins-Regular.ttf",
    "light":   "/usr/share/fonts/truetype/google-fonts/Poppins-Light.ttf",
}

def _f(style: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONTS.get(style, FONTS["regular"]), size)

def _load_logo(size=80) -> Image.Image | None:
    p = Path("app/static/logo_b64.txt")
    if not p.exists():
        p = Path("/tmp/logo_b64.txt")
    if p.exists():
        img = Image.open(io.BytesIO(base64.b64decode(p.read_text().strip()))).convert("RGBA")
        return img.resize((size, size), Image.LANCZOS)
    return None

def _fetch_photo(topic: str, niche: str) -> Image.Image | None:
    if not UNSPLASH_ACCESS_KEY:
        return None
    for q in [f"{topic} {niche}", niche, "business professional"]:
        try:
            r = requests.get("https://api.unsplash.com/search/photos",
                params={"query": q, "per_page": 3, "orientation": "squarish", "content_filter": "high"},
                headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}, timeout=10)
            results = r.json().get("results", [])
            if results:
                url = results[0]["urls"].get("full", results[0]["urls"]["regular"])
                img_r = requests.get(url, timeout=30)
                img = Image.open(io.BytesIO(img_r.content)).convert("RGBA")
                return _crop_square(img)
        except Exception:
            continue
    return None

def _crop_square(img: Image.Image) -> Image.Image:
    r = max(W / img.width, H / img.height)
    img = img.resize((int(img.width * r), int(img.height * r)), Image.LANCZOS)
    x = (img.width - W) // 2
    y = (img.height - H) // 2
    return img.crop((x, y, x + W, y + H))

def _wrap(text: str, font, max_px: int, draw: ImageDraw.Draw) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if draw.textbbox((0,0), test, font=font)[2] <= max_px:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def _shadow(draw, xy, text, font, color, offset=4, shadow_alpha=180):
    x, y = xy
    # Multiple shadow layers for depth
    for ox, oy in [(offset, offset), (offset//2, offset//2)]:
        draw.text((x+ox, y+oy), text, font=font, fill=(0,0,0,shadow_alpha))
    draw.text((x, y), text, font=font, fill=color)

def compose(photo: Image.Image, cover_text: str, image_text: str,
            business_name: str, website: str) -> Image.Image:
    
    # Step 1: Enhance photo
    photo = photo.convert("RGBA")
    photo = ImageEnhance.Contrast(photo).enhance(1.1)
    photo = ImageEnhance.Brightness(photo).enhance(0.6)
    photo = ImageEnhance.Color(photo).enhance(0.85)
    
    # Step 2: Multi-layer gradient overlay
    overlay = Image.new("RGBA", (W, H), (0,0,0,0))
    ov = ImageDraw.Draw(overlay)
    
    # Bottom 60% — dark gradient for text
    for y in range(H):
        t = max(0, (y - H*0.25) / (H * 0.75))
        alpha = int(min(235, 240 * t**1.2))
        ov.line([(0,y),(W,y)], fill=(*DARK, alpha))
    
    # Top bar for eyebrow
    for y in range(120):
        alpha = int(80 * (1 - y/120))
        ov.line([(0,y),(W,y)], fill=(0,0,0,alpha))
    
    photo = Image.alpha_composite(photo, overlay)
    
    # Step 3: Teal decorative elements
    deco = Image.new("RGBA", (W, H), (0,0,0,0))
    dd = ImageDraw.Draw(deco)
    
    # Corner brackets
    p, s = 32, 88
    c = (*TEAL, 180)
    for pts in [
        [(p,p+s),(p,p),(p+s,p)],
        [(W-p-s,p),(W-p,p),(W-p,p+s)],
        [(p,H-p-s),(p,H-p),(p+s,H-p)],
        [(W-p-s,H-p),(W-p,H-p),(W-p,H-p-s)],
    ]:
        dd.line(pts, fill=c, width=3)
    
    # Teal accent bar under eyebrow
    dd.rectangle([(72, 108), (W-72, 111)], fill=(*TEAL, 40))
    
    # Teal left accent line
    dd.rectangle([(72, H-320), (78, H-120)], fill=(*TEAL, 200))
    
    photo = Image.alpha_composite(photo, deco)
    draw = ImageDraw.Draw(photo)
    
    # Step 4: Eyebrow text
    ef = _f("medium", 20)
    draw.text((88, 72), "INFLUZ STUDIO", font=ef, fill=(*TEAL, 230))
    
    # Step 5: Main headline — dynamic sizing
    words = cover_text.split()
    mid = max(1, len(words) // 2)
    p1 = " ".join(words[:mid])
    p2 = " ".join(words[mid:])
    
    max_w = W - 160  # 80px margin each side
    
    for fsize in [90, 78, 68, 58, 50, 44]:
        hf = _f("black", fsize)
        l1 = _wrap(p1, hf, max_w, draw)
        l2 = _wrap(p2, hf, max_w, draw)
        total = (len(l1) + len(l2)) * (fsize + 16)
        if total < 300:
            break
    
    # Position text in lower third
    text_block_h = (len(l1) + len(l2)) * (fsize + 16)
    start_y = H - text_block_h - 160
    
    y = start_y
    for line in l1:
        _shadow(draw, (88, y), line, hf, (*INK, 255))
        y += fsize + 14
    
    y += 6
    for line in l2:
        _shadow(draw, (88, y), line, hf, (*TEAL, 255))
        y += fsize + 14
    
    # Step 6: Subtext
    if image_text:
        sf = _f("light", 26)
        sub = _wrap(image_text, sf, max_w, draw)[:2]
        y += 10
        for line in sub:
            _shadow(draw, (88, y), line, sf, (*MINT, 220), offset=2, shadow_alpha=140)
            y += 36
    
    # Step 7: Footer
    footer_y = H - 108
    draw.line([(72, footer_y), (W-72, footer_y)], fill=(*TEAL, 80), width=1)
    
    logo = _load_logo(70)
    lx, ly = 88, footer_y + 10
    if logo:
        photo.paste(logo, (lx, ly), logo)
        tx = lx + 82
    else:
        tx = lx
    
    draw.text((tx, footer_y + 14), business_name, font=_f("bold", 20), fill=(*TEAL, 255))
    draw.text((tx, footer_y + 42), "Crafting Digital Influence", font=_f("light", 15), fill=(*MINT, 180))
    
    # Website right aligned
    wf = _f("light", 15)
    wb = draw.textbbox((0,0), website, font=wf)
    draw.text((W - 88 - (wb[2]-wb[0]), footer_y + 28), website, font=wf, fill=(190,190,190,180))
    
    return photo


def generate_photo_creative(item_id, cover_text, image_text, post_type,
                             topic, niche="", client_photo_path=None,
                             business_name="Influz Studio",
                             website="influzstudio.netlify.app") -> str:
    photo = None
    if client_photo_path and Path(client_photo_path).exists():
        photo = Image.open(client_photo_path).convert("RGBA")
        photo = _crop_square(photo)
    else:
        photo = _fetch_photo(topic, niche)

    if photo is None:
        from app.services.creative import generate_static_creative
        return generate_static_creative(item_id, cover_text, image_text, post_type, topic)

    final = compose(photo, cover_text or topic, image_text or "", business_name, website)
    output = CREATIVES_DIR / f"item_{item_id}_photo.png"
    final.convert("RGB").save(str(output), "PNG", compress_level=1)
    return f"creatives/item_{item_id}_photo.png"
