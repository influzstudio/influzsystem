"""
Photo-based creative generation service.
"""
import os, io, json, textwrap
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

CREATIVES_DIR = Path("app/static/creatives")
CREATIVES_DIR.mkdir(parents=True, exist_ok=True)

UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")
UNSPLASH_URL = "https://api.unsplash.com/search/photos"

W, H = 1080, 1080

TEAL  = (45, 212, 191)
INK   = (244, 247, 246)
MINT  = (167, 232, 220)
DARK  = (14, 24, 34)


def _load_logo() -> Image.Image | None:
    logo_path = Path("app/static/logo_b64.txt")
    if logo_path.exists():
        import base64
        b64 = logo_path.read_text().strip()
        img_bytes = base64.b64decode(b64)
        logo = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        return logo.resize((72, 72), Image.LANCZOS)
    return None


def _fetch_unsplash(query: str, niche: str) -> Image.Image | None:
    if not UNSPLASH_ACCESS_KEY:
        return None
    for q in [f"{query} {niche}", niche, "social media marketing"]:
        try:
            resp = requests.get(UNSPLASH_URL,
                params={"query": q, "per_page": 3, "orientation": "squarish",
                        "content_filter": "high"},
                headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
                timeout=10)
            results = resp.json().get("results", [])
            if results:
                img_resp = requests.get(results[0]["urls"]["regular"], timeout=15)
                img = Image.open(io.BytesIO(img_resp.content)).convert("RGBA")
                return _crop_center(img, W, H)
        except Exception:
            continue
    return None


def _crop_center(img: Image.Image, w: int, h: int) -> Image.Image:
    ratio = max(w / img.width, h / img.height)
    img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
    left = (img.width - w) // 2
    top  = (img.height - h) // 2
    return img.crop((left, top, left + w, top + h))


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    paths_bold = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    paths_reg = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for p in (paths_bold if bold else paths_reg):
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _shadow_text(draw, xy, text, font, color, shadow=(0,0,0,200)):
    x, y = xy
    draw.text((x+3, y+3), text, font=font, fill=shadow)
    draw.text((x, y), text, font=font, fill=color)


def _fit_text(text: str, font, max_width: int, draw) -> list[str]:
    """Wrap text to fit within max_width pixels."""
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _compose(photo: Image.Image, cover_text: str, image_text: str,
             business_name: str, website: str) -> Image.Image:
    # Darken photo
    photo = photo.convert("RGBA")
    photo = ImageEnhance.Brightness(photo).enhance(0.65)

    # Gradient overlay — strong at bottom for text
    overlay = Image.new("RGBA", (W, H), (0,0,0,0))
    ov_draw = ImageDraw.Draw(overlay)
    for y in range(H):
        alpha = min(220, int(180 * (y / H) ** 0.5))
        ov_draw.line([(0,y),(W,y)], fill=(*DARK, alpha))
    photo = Image.alpha_composite(photo, overlay)

    # Teal corner brackets
    brk = Image.new("RGBA", (W,H), (0,0,0,0))
    bd = ImageDraw.Draw(brk)
    s, p = 80, 32
    c = (*TEAL, 160)
    bd.line([(p,p+s),(p,p),(p+s,p)], fill=c, width=3)
    bd.line([(W-p-s,p),(W-p,p),(W-p,p+s)], fill=c, width=3)
    bd.line([(p,H-p-s),(p,H-p),(p+s,H-p)], fill=c, width=3)
    bd.line([(W-p-s,H-p),(W-p,H-p),(W-p,H-p-s)], fill=c, width=3)
    photo = Image.alpha_composite(photo, brk)

    draw = ImageDraw.Draw(photo)
    max_w = W - 144  # text max width

    # ── Eyebrow ────────────────────────────────────────────────────────
    eyebrow_f = _font(18, bold=True)
    draw.line([(72, 88),(108, 88)], fill=(*TEAL,255), width=2)
    _shadow_text(draw, (120, 76), "INFLUZ STUDIO", eyebrow_f, (*TEAL,255))

    # ── Headline — split into two parts, first white second teal ───────
    words = cover_text.split()
    mid = max(1, len(words)//2)
    part1 = " ".join(words[:mid])
    part2 = " ".join(words[mid:])

    # Dynamically size headline font to fit
    for fsize in [72, 60, 52, 44, 36]:
        hf = _font(fsize, bold=True)
        lines1 = _fit_text(part1, hf, max_w, draw)
        lines2 = _fit_text(part2, hf, max_w, draw)
        total_h = (len(lines1) + len(lines2)) * (fsize + 12)
        if total_h < 280:
            break

    y = H - 400
    for line in lines1:
        _shadow_text(draw, (72, y), line, hf, (*INK,255))
        y += fsize + 10

    y += 8  # small gap between parts
    for line in lines2:
        _shadow_text(draw, (72, y), line, hf, (*TEAL,255))
        y += fsize + 10

    # ── Subtext ────────────────────────────────────────────────────────
    if image_text:
        sf = _font(24)
        sub_lines = _fit_text(image_text, sf, max_w, draw)[:2]
        y += 8
        for line in sub_lines:
            _shadow_text(draw, (72, y), line, sf, (*MINT, 210))
            y += 32

    # ── Footer ─────────────────────────────────────────────────────────
    footer_y = H - 108
    draw.line([(72, footer_y),(W-72, footer_y)], fill=(*TEAL,80), width=1)

    logo = _load_logo()
    lx, ly = 72, footer_y + 10
    if logo:
        photo.paste(logo, (lx, ly), logo)
        tx = lx + 84
    else:
        tx = lx

    bf = _font(18, bold=True)
    rf = _font(15)
    _shadow_text(draw, (tx, footer_y + 14), business_name, bf, (*TEAL,255))
    _shadow_text(draw, (tx, footer_y + 40), "Crafting Digital Influence", rf, (*MINT,200))

    # Website right-aligned
    wb = draw.textbbox((0,0), website, font=rf)
    wx = W - 72 - (wb[2]-wb[0])
    _shadow_text(draw, (wx, footer_y + 26), website, rf, (180,180,180,200))

    return photo


def generate_photo_creative(item_id, cover_text, image_text, post_type,
                             topic, niche="", client_photo_path=None,
                             business_name="Influz Studio",
                             website="influzstudio.netlify.app") -> str:
    photo = None
    if client_photo_path and Path(client_photo_path).exists():
        photo = Image.open(client_photo_path).convert("RGBA")
        photo = _crop_center(photo, W, H)
    else:
        photo = _fetch_unsplash(topic, niche)

    if photo is None:
        from app.services.creative import generate_static_creative
        return generate_static_creative(item_id, cover_text, image_text, post_type, topic)

    final = _compose(photo, cover_text or topic, image_text or "", business_name, website)
    output = CREATIVES_DIR / f"item_{item_id}_photo.png"
    final.convert("RGB").save(str(output), "PNG", quality=95)
    return f"creatives/item_{item_id}_photo.png"
