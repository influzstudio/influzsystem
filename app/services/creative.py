"""
Creative generation service.
Generates branded 1080x1080 SVG templates and converts to PNG using cairosvg.
No browser or Playwright needed — installs cleanly on Render free tier.
"""
import os
import json
import textwrap
from pathlib import Path
import cairosvg

CREATIVES_DIR = Path("app/static/creatives")
CREATIVES_DIR.mkdir(parents=True, exist_ok=True)

# ── Brand tokens ──────────────────────────────────────────────────────────────
BG      = "#0E1822"
BG_SOFT = "#13202E"
TEAL    = "#2DD4BF"
MINT    = "#A7E8DC"
MUTED   = "#7E8FA0"
INK     = "#F4F7F6"
LINE    = "rgba(45,212,191,0.2)"

TYPE_COLORS = {
    "Reel":     "#A78BFA",
    "Static":   "#60A5FA",
    "Carousel": "#34D399",
    "Story":    "#F9A8D4",
    "UGC":      "#FCD34D",
}

W, H = 1080, 1080


def _wrap_text(text: str, max_chars: int) -> list[str]:
    """Wrap text into lines of max_chars."""
    words = text.split()
    lines, current = [], ""
    for word in words:
        if len(current) + len(word) + 1 <= max_chars:
            current = f"{current} {word}".strip()
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _corner_accents() -> str:
    """SVG corner bracket decorations."""
    s = 90  # size
    p = 28  # padding
    op = "0.45"
    return f"""
    <!-- corners -->
    <path d="M{p},{p+s} L{p},{p} L{p+s},{p}" stroke="{TEAL}" stroke-width="2" fill="none" opacity="{op}"/>
    <path d="M{W-p-s},{p} L{W-p},{p} L{W-p},{p+s}" stroke="{TEAL}" stroke-width="2" fill="none" opacity="{op}"/>
    <path d="M{p},{H-p-s} L{p},{H-p} L{p+s},{H-p}" stroke="{TEAL}" stroke-width="2" fill="none" opacity="{op}"/>
    <path d="M{W-p-s},{H-p} L{W-p},{H-p} L{W-p},{H-p-s}" stroke="{TEAL}" stroke-width="2" fill="none" opacity="{op}"/>
    """


def _dot_grid() -> str:
    """Subtle dot grid background."""
    dots = []
    for x in range(48, W, 72):
        for y in range(48, H, 72):
            dots.append(f'<circle cx="{x}" cy="{y}" r="1.2" fill="{TEAL}" opacity="0.06"/>')
    return "\n".join(dots)


def _eyebrow(y: int) -> str:
    return f"""
    <line x1="72" y1="{y}" x2="108" y2="{y}" stroke="{TEAL}" stroke-width="1.5"/>
    <text x="120" y="{y+5}" font-family="Arial, sans-serif" font-size="13"
          fill="{TEAL}" letter-spacing="3" font-weight="bold">INFLUZ STUDIO</text>
    """


def _badge(post_type: str, y: int) -> str:
    color = TYPE_COLORS.get(post_type, TEAL)
    return f"""
    <rect x="72" y="{y}" width="110" height="34" rx="4"
          fill="none" stroke="{color}" stroke-width="1.5"/>
    <text x="127" y="{y+22}" font-family="Arial, sans-serif" font-size="12"
          fill="{color}" letter-spacing="2" font-weight="bold"
          text-anchor="middle">{post_type.upper()}</text>
    """


def _headline_lines(lines: list[str], start_y: int, teal_from: int = 1) -> str:
    """Render headline lines — second half in teal."""
    out = []
    y = start_y
    for i, line in enumerate(lines):
        color = TEAL if i >= teal_from else INK
        out.append(
            f'<text x="72" y="{y}" font-family="Arial Black, Arial, sans-serif" '
            f'font-size="68" font-weight="900" fill="{color}" '
            f'font-style="normal">{line}</text>'
        )
        y += 80
    return "\n".join(out), y


def _subtext_lines(lines: list[str], start_y: int) -> str:
    out = []
    y = start_y
    for line in lines:
        out.append(
            f'<text x="72" y="{y}" font-family="Arial, sans-serif" '
            f'font-size="24" fill="{MINT}" font-weight="400">{line}</text>'
        )
        y += 34
    return "\n".join(out)


def _footer() -> str:
    y_line = H - 80
    return f"""
    <line x1="72" y1="{y_line}" x2="{W-72}" y2="{y_line}"
          stroke="{TEAL}" stroke-width="0.8" opacity="0.3"/>
    <text x="72" y="{y_line+28}" font-family="Arial, sans-serif" font-size="16"
          fill="{TEAL}" font-weight="bold" letter-spacing="1">IS · Influz Studio</text>
    <text x="72" y="{y_line+46}" font-family="Arial, sans-serif" font-size="13"
          fill="{MUTED}" letter-spacing="1">Crafting Digital Influence</text>
    <text x="{W-72}" y="{y_line+36}" font-family="Arial, sans-serif" font-size="13"
          fill="{MUTED}" text-anchor="end">influzstudio.netlify.app</text>
    """


def build_static_svg(cover_text: str, image_text: str, post_type: str) -> str:
    headline_lines = _wrap_text(cover_text, 18)
    subtext_lines = _wrap_text(image_text, 52)[:3]

    headline_svg, headline_end_y = _headline_lines(headline_lines, 380)
    subtext_svg = _subtext_lines(subtext_lines, min(headline_end_y + 36, 820))

    return f"""<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}"
     xmlns="http://www.w3.org/2000/svg">
  <!-- background -->
  <rect width="{W}" height="{H}" fill="{BG}"/>
  <rect x="0" y="0" width="{W}" height="{H}" fill="{BG_SOFT}" opacity="0.4"/>

  {_dot_grid()}
  {_corner_accents()}
  {_eyebrow(100)}
  {_badge(post_type, 128)}

  <!-- headline -->
  {headline_svg}

  <!-- subtext -->
  {subtext_svg}

  {_footer()}
</svg>"""


def build_carousel_svg(cover_text: str, image_text: str, post_type: str,
                       slide_num: int, total_slides: int) -> str:
    headline_lines = _wrap_text(cover_text, 20)
    subtext_lines = _wrap_text(image_text, 52)[:3]
    headline_svg, headline_end_y = _headline_lines(headline_lines, 360, teal_from=0)
    subtext_svg = _subtext_lines(subtext_lines, min(headline_end_y + 36, 800))
    type_color = TYPE_COLORS.get(post_type, TEAL)

    # Progress bar
    bar_w = W - 144
    filled = int(bar_w * slide_num / total_slides)

    return f"""<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}"
     xmlns="http://www.w3.org/2000/svg">
  <rect width="{W}" height="{H}" fill="{BG}"/>
  <rect x="0" y="0" width="{W}" height="{H}" fill="{BG_SOFT}" opacity="0.4"/>

  {_dot_grid()}
  {_corner_accents()}

  <!-- progress bar -->
  <rect x="72" y="60" width="{bar_w}" height="3" rx="2" fill="{LINE}"/>
  <rect x="72" y="60" width="{filled}" height="3" rx="2" fill="{TEAL}"/>

  <!-- slide number -->
  <text x="72" y="108" font-family="Arial, sans-serif" font-size="13"
        fill="{MUTED}" letter-spacing="2">SLIDE {slide_num} OF {total_slides}</text>

  {_eyebrow(140)}

  <!-- big faded slide number -->
  <text x="{W-72}" y="{H//2+60}" font-family="Arial Black, Arial, sans-serif"
        font-size="280" font-weight="900" fill="{type_color}" opacity="0.07"
        text-anchor="end">{slide_num}</text>

  <!-- headline -->
  {headline_svg}

  <!-- subtext -->
  {subtext_svg}

  {_footer()}
  <!-- slide counter -->
  <text x="{W-72}" y="{H-52}" font-family="Arial, sans-serif" font-size="13"
        fill="{MUTED}" text-anchor="end">{slide_num}/{total_slides}</text>
</svg>"""


def _svg_to_png(svg: str, output_path: Path) -> None:
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=str(output_path), scale=1.0)


def generate_static_creative(item_id: int, cover_text: str, image_text: str,
                               post_type: str, topic: str) -> str:
    svg = build_static_svg(cover_text or topic, image_text or topic, post_type)
    output = CREATIVES_DIR / f"item_{item_id}_static.png"
    _svg_to_png(svg, output)
    return f"creatives/item_{item_id}_static.png"


def generate_carousel_creatives(item_id: int, cover_text: str, image_text: str,
                                  post_type: str, total_slides: int = 5) -> list[str]:
    slide_items = [s.strip() for s in image_text.split("|") if s.strip()]
    while len(slide_items) < total_slides:
        slide_items.append(image_text)

    paths = []
    for i in range(1, total_slides + 1):
        slide_cover = cover_text if i == 1 else slide_items[i - 1]
        slide_body = slide_items[i - 1]
        svg = build_carousel_svg(slide_cover, slide_body, post_type, i, total_slides)
        output = CREATIVES_DIR / f"item_{item_id}_slide_{i}.png"
        _svg_to_png(svg, output)
        paths.append(f"creatives/item_{item_id}_slide_{i}.png")
    return paths
