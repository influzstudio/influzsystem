"""
Creative generation service.
Generates client-branded 1080x1080 images using Pillow + Unsplash photos.

Branding rule: every creative uses the CLIENT's brand colors and CLIENT's logo.
Influz Studio appears only as a small "Powered by Influz" watermark in the footer.
"""
import os, io, base64, colorsys
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

CREATIVES_DIR = Path("/tmp/creatives")
CREATIVES_DIR.mkdir(parents=True, exist_ok=True)

UNSPLASH_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")
PEXELS_KEY = os.getenv("PEXELS_API_KEY", "")
W, H = 1080, 1080

# Fallback palette — only used if a client has no brand_colors saved yet.
DEFAULT_PRIMARY = "#2DD4BF"
DEFAULT_SECONDARY = "#0E1822"
WHITE = (255, 255, 255)
BLACK = (18, 18, 20)

FONTS = {
    "bold":    "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf",
    "medium":  "/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf",
    "regular": "/usr/share/fonts/truetype/google-fonts/Poppins-Regular.ttf",
    "light":   "/usr/share/fonts/truetype/google-fonts/Poppins-Light.ttf",
}
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


# ── Color helpers ────────────────────────────────────────────────────────────
def _hex_to_rgb(hex_str, fallback=(45, 212, 191)):
    try:
        h = (hex_str or "").lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) != 6:
            return fallback
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return fallback


def _luminance(rgb):
    r, g, b = [c / 255.0 for c in rgb]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _readable_ink(bg_rgb):
    """Return near-white or near-black text color for readability against bg_rgb."""
    return WHITE if _luminance(bg_rgb) < 0.5 else BLACK


def _shade(rgb, factor):
    """factor > 1 lightens, < 1 darkens."""
    h, l, s = colorsys.rgb_to_hls(*[c / 255.0 for c in rgb])
    l = max(0.0, min(1.0, l * factor))
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return (int(r * 255), int(g * 255), int(b * 255))


class Palette:
    """Resolved brand palette for a single creative render."""
    def __init__(self, brand_colors: dict | None):
        brand_colors = brand_colors or {}
        self.primary = _hex_to_rgb(brand_colors.get("primary"), _hex_to_rgb(DEFAULT_PRIMARY))
        self.secondary = _hex_to_rgb(brand_colors.get("secondary"), _hex_to_rgb(DEFAULT_SECONDARY))
        self.bg_dark = self.secondary if _luminance(self.secondary) < 0.55 else _shade(self.secondary, 0.35)
        self.ink = _readable_ink(self.bg_dark)
        self.accent = self.primary
        self.accent_ink = _readable_ink(self.accent)
        self.muted = tuple(int(c * 0.75 + self.bg_dark[i] * 0.25) for i, c in enumerate(self.ink))


def _f(style, size):
    p = FONTS.get(style, FONTS["regular"])
    for path in [p, FB]:
        if Path(path).exists():
            try: return ImageFont.truetype(path, size)
            except Exception: continue
    return ImageFont.load_default()


def _client_logo(logo_path: str, size=72):
    """Load the CLIENT's uploaded logo. Returns None if not set/found."""
    if not logo_path:
        return None
    for base in [Path(logo_path), Path("app") / logo_path if not logo_path.startswith("app/") else None]:
        if base and base.exists():
            try:
                img = Image.open(base).convert("RGBA")
                ratio = size / max(img.height, 1)
                return img.resize((max(1, int(img.width * ratio)), size), Image.LANCZOS)
            except Exception:
                continue
    return None


def _initials_badge(name, size, pal: Palette):
    """Fallback client mark when no logo is uploaded: a colored initials badge."""
    initials = "".join([w[0] for w in (name or "?").split()[:2]]).upper() or "?"
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([(0, 0), (size, size)], fill=(*pal.accent, 255))
    f = _f("bold", int(size * 0.42))
    bb = draw.textbbox((0, 0), initials, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    draw.text(((size - tw) / 2 - bb[0], (size - th) / 2 - bb[1]), initials, font=f, fill=(*pal.accent_ink, 255))
    return img


def _influz_watermark(img, pal: Palette):
    """Tiny 'Powered by Influz' watermark — bottom-right corner, unobtrusive."""
    d = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(d)
    text = "Powered by Influz"
    f = _f("regular", 13)
    bb = draw.textbbox((0, 0), text, font=f)
    tw = bb[2] - bb[0]
    x, y = W - 24 - tw, H - 26
    draw.text((x + 1, y + 1), text, font=f, fill=(0, 0, 0, 110))
    draw.text((x, y), text, font=f, fill=(*pal.muted, 160))
    return Image.alpha_composite(img, d)


_BRAND_BLOCKLIST = {
    "delta", "emirates", "lufthansa", "boeing", "airbus", "american airlines",
    "united airlines", "southwest", "qantas", "singapore airlines", "logo",
    "nike", "adidas", "coca-cola", "pepsi", "apple", "samsung", "mercedes",
    "bmw", "toyota", "starbucks", "mcdonald", "nasa", "tesla",
}
_STOPWORDS = {"a","an","the","of","in","on","at","for","with","and","to","is","-","near","by"}


def _keyword_score(alt_text, query):
    alt = (alt_text or "").lower()
    if any(brand in alt for brand in _BRAND_BLOCKLIST):
        return -100
    q_words = {w for w in query.lower().split() if w not in _STOPWORDS}
    if not q_words:
        return 0
    return sum(1 for w in q_words if w in alt)


def _fetch_from_pexels(query):
    if not PEXELS_KEY:
        return None
    try:
        r = requests.get("https://api.pexels.com/v1/search",
            params={"query": query, "per_page": 12, "orientation": "square"},
            headers={"Authorization": PEXELS_KEY}, timeout=10)
        if r.status_code != 200:
            print(f"[creative_service] Pexels HTTP {r.status_code} for '{query}': {r.text[:200]}")
            return None
        results = r.json().get("photos", [])
        if not results:
            return None
        scored = sorted(results, key=lambda p: _keyword_score(p.get("alt", ""), query), reverse=True)
        best = scored[0]
        if _keyword_score(best.get("alt", ""), query) < 0:
            return None  # all candidates were brand/logo matches — let it fall through to next query
        url = best["src"]["large"]
        img = Image.open(io.BytesIO(requests.get(url, timeout=30).content)).convert("RGBA")
        return img
    except Exception as e:
        print(f"[creative_service] Pexels error for '{query}': {e}")
        return None


def _fetch_from_unsplash(query):
    if not UNSPLASH_KEY:
        return None
    try:
        r = requests.get("https://api.unsplash.com/search/photos",
            params={"query": query, "per_page": 12, "orientation": "squarish"},
            headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"}, timeout=10)
        if r.status_code != 200:
            print(f"[creative_service] Unsplash HTTP {r.status_code} for '{query}': {r.text[:200]}")
            return None
        results = r.json().get("results", [])
        if not results:
            return None
        def alt(p): return p.get("alt_description") or p.get("description") or ""
        scored = sorted(results, key=lambda p: _keyword_score(alt(p), query), reverse=True)
        best = scored[0]
        if _keyword_score(alt(best), query) < 0:
            return None
        url = best["urls"].get("regular")
        img = Image.open(io.BytesIO(requests.get(url, timeout=30).content)).convert("RGBA")
        return img
    except Exception as e:
        print(f"[creative_service] Unsplash error for '{query}': {e}")
        return None


def _glow_background(pal: Palette):
    """Soft brand-colored radial glows on a solid dark background — no grid/checker pattern."""
    img = Image.new("RGBA", (W, H), (*pal.bg_dark, 255))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for (cx, cy, r, col, alpha) in [
        (W * 0.15, H * 0.1, 520, pal.accent, 70),
        (W * 0.9, H * 0.85, 620, pal.accent, 55),
        (W * 0.5, H * 0.95, 480, _shade(pal.accent, 1.3), 40),
    ]:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*col, alpha))
        layer = layer.filter(ImageFilter.GaussianBlur(140))
        glow = Image.alpha_composite(glow, layer)
    img = Image.alpha_composite(img, glow)
    # subtle fine grain/vignette instead of a hard grid, for texture
    vign = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vign)
    vd.rectangle([(0, 0), (W, H)], outline=(0, 0, 0, 0))
    for i in range(6):
        a = int(10 * (i + 1))
        vd.rectangle([i * 14, i * 14, W - i * 14, H - i * 14], outline=(0, 0, 0, a))
    return Image.alpha_composite(img, vign)


def _fetch_photo(query_terms):
    """
    query_terms: list of search phrases tried in order of specificity.
    Tries Pexels first (no approval process, 20k free requests/month, rarely
    rate-limited) then Unsplash (50 req/hour on the free demo tier — easy to
    exhaust). Logs every failure so it's visible in Render logs instead of
    silently falling back to the plain background card.
    """
    if not UNSPLASH_KEY and not PEXELS_KEY:
        print("[creative_service] No PEXELS_API_KEY or UNSPLASH_ACCESS_KEY set — "
              "creatives will always use the no-photo background card.")
        return None

    for q in query_terms:
        if not q or not q.strip():
            continue
        img = _fetch_from_pexels(q) or _fetch_from_unsplash(q)
        if img:
            ratio = max(W / img.width, H / img.height)
            img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
            return img.crop(((img.width - W) // 2, (img.height - H) // 2, (img.width + W) // 2, (img.height + H) // 2))
    print(f"[creative_service] No photo found for any of: {query_terms}")
    return None


def _wrap(text, font, max_px, draw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = f"{cur} {w}".strip()
        if draw.textbbox((0, 0), t, font=font)[2] <= max_px: cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines


def _shadow(draw, xy, text, font, color):
    x, y = xy
    draw.text((x + 4, y + 4), text, font=font, fill=(0, 0, 0, 180))
    draw.text((x, y), text, font=font, fill=color)


def _brackets(img, pal: Palette):
    d = Image.new("RGBA", (W, H), (0, 0, 0, 0)); draw = ImageDraw.Draw(d)
    p, s, c = 32, 90, (*pal.accent, 160)
    for pts in [[(p, p + s), (p, p), (p + s, p)], [(W - p - s, p), (W - p, p), (W - p, p + s)],
                [(p, H - p - s), (p, H - p), (p + s, H - p)], [(W - p - s, H - p), (W - p, H - p), (W - p, H - p - s)]]:
        draw.line(pts, fill=c, width=3)
    return Image.alpha_composite(img, d)


def _brand_header(img, draw, x, y, business_name, logo_path, pal: Palette, mark_size=56):
    """Draws the CLIENT's logo (or initials badge) + business name at (x, y).
    Logos get a soft white chip behind them so logos with solid/white
    backgrounds (most uploaded PNGs/JPEGs) always look intentional instead
    of pasting a stray rectangle onto the photo."""
    logo = _client_logo(logo_path, size=mark_size)
    if logo:
        pad = 10
        chip_w, chip_h = logo.width + pad * 2, mark_size + pad * 2
        chip = Image.new("RGBA", (chip_w, chip_h), (0, 0, 0, 0))
        cd = ImageDraw.Draw(chip)
        cd.rounded_rectangle([(0, 0), (chip_w, chip_h)], radius=12, fill=(255, 255, 255, 235))
        img.paste(chip, (x, y - pad), chip)
        img.paste(logo, (x + pad, y), logo)
        text_x = x + chip_w + 14
    else:
        logo = _initials_badge(business_name, mark_size, pal)
        img.paste(logo, (x, y), logo)
        text_x = x + mark_size + 14
    name_f = _f("bold", 22)
    draw.text((text_x, y + mark_size // 2 - 13), business_name, font=name_f, fill=(*pal.ink, 255))
    return img


def _footer(img, name, website, pal: Palette):
    d = Image.new("RGBA", (W, H), (0, 0, 0, 0)); draw = ImageDraw.Draw(d)
    fy = H - 92
    draw.line([(72, fy), (W - 72, fy)], fill=(*pal.accent, 60), width=1)
    draw.text((88, fy + 16), website, font=_f("light", 15), fill=(*pal.muted, 200))
    img = Image.alpha_composite(img, d)
    return _influz_watermark(img, pal)


def _dark_card(cover, subtext, business_name, website, logo_path, pal: Palette):
    img = _glow_background(pal)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (W, 8)], fill=(*pal.accent,))
    img = _brackets(img, pal); draw = ImageDraw.Draw(img)
    img = _brand_header(img, draw, 88, 40, business_name, logo_path, pal)
    words = cover.split(); mid = max(1, len(words) // 2)
    p1, p2 = " ".join(words[:mid]), " ".join(words[mid:])
    l1 = l2 = []
    for fs in [82, 70, 60, 52, 44]:
        hf = _f("bold", fs)
        l1 = _wrap(p1, hf, W - 180, draw); l2 = _wrap(p2, hf, W - 180, draw)
        if (len(l1) + len(l2)) * (fs + 16) < 400: break
    total = (len(l1) + len(l2)) * (fs + 16); y = (H - total) // 2
    for line in l1:
        bb = draw.textbbox((0, 0), line, font=hf); x = (W - (bb[2] - bb[0])) // 2
        _shadow(draw, (x, y), line, hf, (*pal.ink, 255)); y += fs + 14
    y += 10
    for line in l2:
        bb = draw.textbbox((0, 0), line, font=hf); x = (W - (bb[2] - bb[0])) // 2
        _shadow(draw, (x, y), line, hf, (*pal.accent, 255)); y += fs + 14
    if subtext:
        sf = _f("regular", 26)
        for line in _wrap(subtext, sf, W - 200, draw)[:2]:
            bb = draw.textbbox((0, 0), line, font=sf); x = (W - (bb[2] - bb[0])) // 2
            draw.text((x, y + 16), line, font=sf, fill=(*pal.ink, 200)); y += 38
    return _footer(img, business_name, website, pal)


def _photo_card(photo, cover, subtext, business_name, website, logo_path, pal: Palette):
    img = ImageEnhance.Brightness(photo.convert("RGBA")).enhance(0.78)
    img = ImageEnhance.Color(img).enhance(0.9)
    # Overlay tint: mostly neutral black (keeps the photo readable/true-color)
    # with a light wash of the brand color, rather than a full-saturation
    # brand-color wash that can fight the photo's own colors.
    tint = tuple(int(c * 0.35) for c in pal.bg_dark)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for y in range(H):
        a = int(min(215, 225 * max(0, (y - H * 0.38) / (H * 0.62)) ** 1.3))
        d.line([(0, y), (W, y)], fill=(*tint, a))
    img = Image.alpha_composite(img, ov)
    img = _brackets(img, pal); draw = ImageDraw.Draw(img)
    img = _brand_header(img, draw, 88, 56, business_name, logo_path, pal, mark_size=48)
    words = cover.split(); mid = max(1, len(words) // 2)
    p1, p2 = " ".join(words[:mid]), " ".join(words[mid:])
    l1 = l2 = []
    for fs in [82, 70, 60, 52, 44]:
        hf = _f("bold", fs)
        l1 = _wrap(p1, hf, W - 176, draw); l2 = _wrap(p2, hf, W - 176, draw)
        if (len(l1) + len(l2)) * (fs + 14) < 320: break
    sub_lines = _wrap(subtext, _f("light", 24), W - 176, draw)[:2] if subtext else []
    sub_h = len(sub_lines) * 36 + (24 if sub_lines else 0)
    y = H - (len(l1) + len(l2)) * (fs + 14) - sub_h - 160
    draw.line([(88, y - 10), (88, y + (len(l1) + len(l2)) * (fs + 14) + sub_h + 20)], fill=(*pal.accent, 180), width=5)
    for line in l1: _shadow(draw, (100, y), line, hf, (*pal.ink, 255)); y += fs + 12
    y += 8
    for line in l2: _shadow(draw, (100, y), line, hf, (*pal.accent, 255)); y += fs + 12
    if sub_lines:
        y += 24
        sf = _f("light", 24)
        for line in sub_lines:
            _shadow(draw, (100, y), line, sf, (*pal.ink, 200)); y += 36
    return _footer(img, business_name, website, pal)


def _poll_card(cover, options_text, business_name, website, logo_path, pal: Palette):
    img = _glow_background(pal)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (W, 108)], fill=(*pal.bg_dark, 255))
    draw.line([(0, 108), (W, 108)], fill=(*pal.accent, 80), width=2)
    img = _brand_header(img, draw, 88, 26, business_name, logo_path, pal, mark_size=52)
    img = _brackets(img, pal); draw = ImageDraw.Draw(img)
    qf = _f("bold", 70); q_lines = _wrap(cover, qf, W - 160, draw)[:3]
    y = 160
    for line in q_lines: _shadow(draw, (88, y), line, qf, (*pal.ink, 255)); y += 82
    parts = [p.strip() for p in options_text.split("|")] if "|" in options_text else ["YES", "NO"]
    colors = [pal.accent, (248, 113, 113)]; btn_y = y + 60
    for i, (opt, col) in enumerate(zip(parts[:2], colors)):
        draw.rounded_rectangle([(88, btn_y), (W - 88, btn_y + 108)], radius=16, fill=(*col, 25), outline=(*col, 180), width=3)
        draw.ellipse([(110, btn_y + 22), (172, btn_y + 86)], fill=(*col, 220))
        ic = "+" if i == 0 else "x"; iff = _f("bold", 38)
        bb = draw.textbbox((0, 0), ic, font=iff)
        ic_ink = _readable_ink(col)
        draw.text((141 - (bb[2] - bb[0]) // 2, btn_y + 30), ic, font=iff, fill=(*ic_ink, 255))
        draw.text((192, btn_y + 28), opt, font=_f("bold", 40), fill=(*pal.ink, 255))
        btn_y += 126
    return _footer(img, business_name, website, pal)


def _slide_badge(img, idx, total, pal: Palette):
    """Small 'n/total' pill top-right — makes a multi-slide set read as a carousel."""
    d = Image.new("RGBA", (W, H), (0, 0, 0, 0)); draw = ImageDraw.Draw(d)
    text = f"{idx}/{total}"
    f = _f("bold", 18)
    bb = draw.textbbox((0, 0), text, font=f)
    tw = bb[2] - bb[0]
    pad = 14
    x0, y0 = W - 88 - tw - pad * 2, 40
    x1, y1 = W - 88, y0 + 40
    draw.rounded_rectangle([(x0, y0), (x1, y1)], radius=20, fill=(0, 0, 0, 130))
    draw.text((x0 + pad, y0 + 9), text, font=f, fill=(255, 255, 255, 230))
    return Image.alpha_composite(img, d)


def _render_card(post_type, cover, subtext, business_name, website, logo_path, pal: Palette, photo=None):
    """Renders one slide/card. Shared by single creatives and carousel slides."""
    pt = post_type.lower()
    if pt == "story":
        return _poll_card(cover, subtext, business_name, website, logo_path, pal)
    if photo is not None:
        return _photo_card(photo, cover, subtext, business_name, website, logo_path, pal)
    return _dark_card(cover, subtext, business_name, website, logo_path, pal)


def _auto_slides_from_caption(cover_text, image_text, caption, topic, website, n=4):
    """Fallback slide breakdown for Carousel posts generated before carousel_slides
    existed, or where the AI omitted it. Splits the caption into distinct points
    instead of repeating the same headline on every slide."""
    import re as _re
    slides = [{"slide_headline": cover_text or topic, "slide_subtext": image_text or ""}]
    if caption:
        # strip hashtags/emoji-heavy trailing line, split into sentences
        body = _re.sub(r"#\w+", "", caption).strip()
        sentences = [s.strip() for s in _re.split(r"(?<=[.!?])\s+", body) if len(s.strip()) > 8]
        for s in sentences[:max(0, n - 2)]:
            words = s.split()
            slides.append({"slide_headline": " ".join(words[:6]), "slide_subtext": " ".join(words[6:16])})
    slides.append({"slide_headline": "Ready to book?", "slide_subtext": f"Visit {website}" if website else "DM us to get started"})
    return slides[:n] if len(slides) > n else slides


def generate_carousel(post_id, slides, post_type, topic, niche="", business_name="Client",
                       website="", brand_colors=None, logo_path="", photo_keywords=None,
                       caption="") -> list:
    """
    Renders a full carousel (3-6 slides) instead of a single image.
    Returns an ordered list of file paths, one per slide.
    """
    pal = Palette(brand_colors)
    website = (website or "").strip() or "influz-platform.onrender.com"

    if not slides:
        slides = _auto_slides_from_caption("", "", caption, topic, website)
    slides = slides[:6] if len(slides) > 6 else slides
    total = len(slides)

    queries = photo_keywords or [f"{topic} {niche}", niche, "business professional"]
    hero_photo = _fetch_photo(queries)

    paths = []
    for i, slide in enumerate(slides):
        cover = slide.get("slide_headline") or topic
        subtext = slide.get("slide_subtext") or ""
        photo = hero_photo if i == 0 else None  # hero photo on slide 1, brand cards for the rest
        img = _render_card(post_type, cover, subtext, business_name, website, logo_path, pal, photo=photo)
        img = _slide_badge(img, i + 1, total, pal)
        out = CREATIVES_DIR / f"post_{post_id}_s{i + 1}.png"
        img.convert("RGB").save(str(out), "PNG", compress_level=1)
        paths.append(str(out))
    return paths


def generate_creative(post_id, cover_text, image_text, post_type, topic,
                       niche="", business_name="Client",
                       website="", brand_colors=None, logo_path="",
                       photo_keywords=None) -> str:
    """
    Renders a client-branded creative.
    brand_colors: {"primary": "#RRGGBB", "secondary": "#RRGGBB"} — the CLIENT's colors.
    logo_path: path to the CLIENT's uploaded logo (relative to repo root), e.g. "app/static/client_logos/acme.png".
    photo_keywords: ordered list of Unsplash search phrases, most specific first
                    (e.g. [f"{product} {niche}", f"{topic} {niche}", niche]).
    """
    pal = Palette(brand_colors)
    cover = cover_text or topic
    subtext = image_text or ""
    website = (website or "").strip() or "influz-platform.onrender.com"

    photo = None
    if post_type.lower() != "story":
        queries = photo_keywords or [f"{topic} {niche}", niche, "business professional"]
        photo = _fetch_photo(queries)
    final = _render_card(post_type, cover, subtext, business_name, website, logo_path, pal, photo=photo)

    output = CREATIVES_DIR / f"post_{post_id}.png"
    final.convert("RGB").save(str(output), "PNG", compress_level=1)
    return str(output)
