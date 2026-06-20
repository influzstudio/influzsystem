"""
Photo-based creative generation service.
Fetches a relevant photo from Unsplash (or uses client-uploaded photo),
then overlays text + logo using Pillow to produce a 1080x1080 PNG.
"""
import os
import io
import json
import textwrap
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

CREATIVES_DIR = Path("app/static/creatives")
CREATIVES_DIR.mkdir(parents=True, exist_ok=True)

UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")
UNSPLASH_URL = "https://api.unsplash.com/search/photos"

W, H = 1080, 1080

# Brand colors
TEAL    = (45, 212, 191)
TEAL_A  = (45, 212, 191, 200)
INK     = (244, 247, 246)
BG_DARK = (14, 24, 34, 200)
MINT    = (167, 232, 220)


def _load_logo() -> Image.Image | None:
    """Load the IS logo icon."""
    logo_path = Path("app/static/logo_b64.txt")
    if logo_path.exists():
        import base64
        b64 = logo_path.read_text().strip()
        img_bytes = base64.b64decode(b64)
        logo = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        return logo.resize((80, 80), Image.LANCZOS)
    return None


def _fetch_unsplash_photo(query: str, niche: str) -> Image.Image | None:
    """Fetch a relevant photo from Unsplash based on topic + niche."""
    if not UNSPLASH_ACCESS_KEY:
        return None
    search_query = f"{query} {niche}".strip()[:60]
    try:
        resp = requests.get(
            UNSPLASH_URL,
            params={
                "query": search_query,
                "per_page": 5,
                "orientation": "squarish",
                "content_filter": "high",
            },
            headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
            timeout=10,
        )
        results = resp.json().get("results", [])
        if not results:
            # Try niche only
            resp2 = requests.get(
                UNSPLASH_URL,
                params={"query": niche, "per_page": 3, "orientation": "squarish"},
                headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
                timeout=10,
            )
            results = resp2.json().get("results", [])

        if results:
            photo_url = results[0]["urls"]["regular"]
            img_resp = requests.get(photo_url, timeout=15)
            img = Image.open(io.BytesIO(img_resp.content)).convert("RGBA")
            # Crop to square 1080x1080
            img = _crop_center(img, W, H)
            return img
    except Exception:
        return None
    return None


def _crop_center(img: Image.Image, w: int, h: int) -> Image.Image:
    """Crop image to exact size from center."""
    img = img.resize((max(w, int(img.width * h / img.height)),
                       max(h, int(img.height * w / img.width))), Image.LANCZOS)
    left = (img.width - w) // 2
    top = (img.height - h) // 2
    return img.crop((left, top, left + w, top + h))


def _dark_overlay(base: Image.Image, opacity: int = 140) -> Image.Image:
    """Add a dark gradient overlay for text readability."""
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    # Bottom-heavy gradient: dark at bottom, lighter at top
    for y in range(H):
        alpha = int(opacity * (y / H) ** 0.6)
        draw.line([(0, y), (W, y)], fill=(14, 24, 34, alpha))
    return Image.alpha_composite(base, overlay)


def _teal_accent_overlay(base: Image.Image) -> Image.Image:
    """Add subtle teal corner accents."""
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    s, p = 90, 28
    c = (*TEAL, 140)
    # Corners
    draw.line([(p, p+s), (p, p), (p+s, p)], fill=c, width=3)
    draw.line([(W-p-s, p), (W-p, p), (W-p, p+s)], fill=c, width=3)
    draw.line([(p, H-p-s), (p, H-p), (p+s, H-p)], fill=c, width=3)
    draw.line([(W-p-s, H-p), (W-p, H-p), (W-p, H-p-s)], fill=c, width=3)
    return Image.alpha_composite(base, overlay)


def _get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Try to load a system font, fallback to default."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for path in font_paths:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _draw_text_with_shadow(draw: ImageDraw.Draw, pos: tuple, text: str,
                            font, color: tuple, shadow_color=(0,0,0,180)):
    """Draw text with drop shadow for readability on photos."""
    x, y = pos
    # Shadow
    draw.text((x+3, y+3), text, font=font, fill=shadow_color)
    # Main text
    draw.text((x, y), text, font=font, fill=color)


def _compose_photo_creative(
    photo: Image.Image,
    cover_text: str,
    image_text: str,
    post_type: str,
    business_name: str = "Influz Studio",
    website: str = "influzstudio.netlify.app",
) -> Image.Image:
    """Compose the final creative: photo + overlays + text + logo."""
    # Enhance photo
    photo = photo.convert("RGBA")
    enhancer = ImageEnhance.Brightness(photo)
    photo = enhancer.enhance(0.75)  # Slightly darken for text contrast

    # Dark gradient overlay
    photo = _dark_overlay(photo, opacity=200)
    # Teal corner accents
    photo = _teal_accent_overlay(photo)

    draw = ImageDraw.Draw(photo)

    # ── Eyebrow ────────────────────────────────────────────────────────────
    eyebrow_font = _get_font(22, bold=True)
    draw.line([(72, 96), (108, 96)], fill=(*TEAL, 255), width=2)
    _draw_text_with_shadow(draw, (120, 84), "INFLUZ STUDIO", eyebrow_font, (*TEAL, 255))

    # ── Main headline ──────────────────────────────────────────────────────
    # Split cover text into lines
    words = cover_text.split()
    mid = max(1, len(words) // 2)
    line1 = " ".join(words[:mid])
    line2 = " ".join(words[mid:])

    headline_font = _get_font(72, bold=True)
    y = H - 420
    _draw_text_with_shadow(draw, (72, y), line1, headline_font, (*INK, 255))
    _draw_text_with_shadow(draw, (72, y + 88), line2, headline_font, (*TEAL, 255))

    # ── Subtext / image_text ───────────────────────────────────────────────
    subtext_font = _get_font(28)
    sub_lines = textwrap.wrap(image_text, width=42)[:2]
    sub_y = y + 88 + 90
    for line in sub_lines:
        _draw_text_with_shadow(draw, (72, sub_y), line, subtext_font, (*MINT, 220))
        sub_y += 38

    # ── Footer line ────────────────────────────────────────────────────────
    footer_y = H - 110
    draw.line([(72, footer_y), (W - 72, footer_y)], fill=(*TEAL, 100), width=1)

    # ── Logo ───────────────────────────────────────────────────────────────
    logo = _load_logo()
    logo_x, logo_y = 72, footer_y + 12
    if logo:
        photo.paste(logo, (logo_x, logo_y), logo)
        text_x = logo_x + 90
    else:
        text_x = logo_x

    brand_font = _get_font(20, bold=True)
    small_font = _get_font(16)
    _draw_text_with_shadow(draw, (text_x, footer_y + 16), business_name, brand_font, (*TEAL, 255))
    _draw_text_with_shadow(draw, (text_x, footer_y + 42), "Crafting Digital Influence", small_font, (*MINT, 200))

    # Website right side
    web_font = _get_font(16)
    _draw_text_with_shadow(draw, (W - 72 - 320, footer_y + 28), website, web_font, (180, 180, 180, 200))

    return photo


def generate_photo_creative(
    item_id: int,
    cover_text: str,
    image_text: str,
    post_type: str,
    topic: str,
    niche: str = "",
    client_photo_path: str | None = None,
    business_name: str = "Influz Studio",
    website: str = "influzstudio.netlify.app",
) -> str:
    """Generate a photo-based 1080x1080 creative. Returns relative path."""
    # Get base photo
    photo = None

    if client_photo_path and Path(client_photo_path).exists():
        # Use client-uploaded photo
        photo = Image.open(client_photo_path).convert("RGBA")
        photo = _crop_center(photo, W, H)
    else:
        # Fetch from Unsplash
        photo = _fetch_unsplash_photo(topic, niche)

    if photo is None:
        # No photo available — fall back to SVG-based creative
        from app.services.creative import generate_static_creative
        return generate_static_creative(item_id, cover_text, image_text, post_type, topic)

    # Compose
    final = _compose_photo_creative(photo, cover_text or topic, image_text or "", 
                                     post_type, business_name, website)
    output = CREATIVES_DIR / f"item_{item_id}_photo.png"
    final.convert("RGB").save(str(output), "PNG", quality=95)
    return f"creatives/item_{item_id}_photo.png"
