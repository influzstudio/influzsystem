"""
Creative generation service.
Renders branded HTML templates to 1080x1080 PNG using Playwright.
"""
import os
import asyncio
from pathlib import Path
from datetime import date

CREATIVES_DIR = Path("app/static/creatives")
CREATIVES_DIR.mkdir(parents=True, exist_ok=True)

# ── Brand tokens ──────────────────────────────────────────────────────────────
BG      = "#0E1822"
BG_SOFT = "#13202E"
TEAL    = "#2DD4BF"
MINT    = "#A7E8DC"
MUTED   = "#7E8FA0"
INK     = "#F4F7F6"
LINE    = "rgba(45,212,191,0.16)"

TYPE_COLORS = {
    "Reel":     "#A78BFA",
    "Static":   "#60A5FA",
    "Carousel": "#34D399",
    "Story":    "#F9A8D4",
    "UGC":      "#FCD34D",
}


def _base_style() -> str:
    return f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700;800&family=Inter:wght@400;500&display=swap');
      * {{ margin:0; padding:0; box-sizing:border-box; }}
      body {{
        width:1080px; height:1080px; overflow:hidden;
        background:{BG};
        font-family:'Poppins', sans-serif;
        color:{INK};
      }}
      .wrap {{
        width:1080px; height:1080px;
        position:relative;
        display:flex; flex-direction:column;
        padding:72px;
      }}
      /* circuit corner accents */
      .corner {{ position:absolute; width:120px; height:120px; }}
      .corner.tl {{ top:24px; left:24px; border-top:2px solid {TEAL}; border-left:2px solid {TEAL}; border-radius:4px 0 0 0; opacity:0.5; }}
      .corner.tr {{ top:24px; right:24px; border-top:2px solid {TEAL}; border-right:2px solid {TEAL}; border-radius:0 4px 0 0; opacity:0.5; }}
      .corner.bl {{ bottom:24px; left:24px; border-bottom:2px solid {TEAL}; border-left:2px solid {TEAL}; border-radius:0 0 0 4px; opacity:0.5; }}
      .corner.br {{ bottom:24px; right:24px; border-bottom:2px solid {TEAL}; border-right:2px solid {TEAL}; border-radius:0 0 4px 0; opacity:0.5; }}
      /* grid dots */
      .grid {{
        position:absolute; inset:0; opacity:0.04;
        background-image: radial-gradient({TEAL} 1px, transparent 1px);
        background-size:48px 48px;
      }}
      .badge {{
        display:inline-block;
        padding:6px 18px; border-radius:4px;
        font-size:13px; font-weight:600; letter-spacing:2px;
        text-transform:uppercase;
        border:1px solid currentColor;
        margin-bottom:32px;
      }}
      .eyebrow {{
        font-size:13px; letter-spacing:3px; text-transform:uppercase;
        color:{TEAL}; font-weight:500; margin-bottom:20px;
        display:flex; align-items:center; gap:12px;
      }}
      .eyebrow::before {{
        content:''; width:32px; height:1px; background:{TEAL};
      }}
      .headline {{
        font-size:64px; font-weight:800; line-height:1.05;
        letter-spacing:-1px; margin-bottom:24px;
        max-width:860px;
      }}
      .subtext {{
        font-size:22px; font-weight:400; color:{MINT};
        line-height:1.5; max-width:760px; margin-bottom:auto;
      }}
      .footer {{
        display:flex; align-items:center; justify-content:space-between;
        padding-top:32px;
        border-top:1px solid {LINE};
        margin-top:auto;
      }}
      .brand {{ font-size:16px; font-weight:600; color:{TEAL}; letter-spacing:1px; }}
      .tagline {{ font-size:13px; color:{MUTED}; letter-spacing:1px; }}
    </style>
    """


def static_template(cover_text: str, image_text: str, post_type: str, topic: str) -> str:
    type_color = TYPE_COLORS.get(post_type, TEAL)
    words = cover_text.split()
    mid = max(1, len(words) // 2)
    line1 = " ".join(words[:mid])
    line2 = " ".join(words[mid:])

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">{_base_style()}</head>
<body>
<div class="wrap" style="justify-content:center;">
  <div class="grid"></div>
  <div class="corner tl"></div>
  <div class="corner tr"></div>
  <div class="corner bl"></div>
  <div class="corner br"></div>

  <div style="margin-bottom:auto;padding-top:32px;">
    <div class="eyebrow">Influz Studio</div>
    <div class="badge" style="color:{type_color};">{post_type}</div>
  </div>

  <div style="flex:1;display:flex;flex-direction:column;justify-content:center;padding:40px 0;">
    <div class="headline">
      {line1}<br>
      <span style="color:{TEAL};">{line2}</span>
    </div>
    <div class="subtext" style="margin-top:32px;">{image_text}</div>
  </div>

  <div class="footer">
    <div>
      <div class="brand">IS · Influz Studio</div>
      <div class="tagline">Crafting Digital Influence</div>
    </div>
    <div class="tagline">influzstudio.netlify.app</div>
  </div>
</div>
</body></html>"""


def carousel_slide(cover_text: str, image_text: str, slide_num: int,
                   total_slides: int, post_type: str) -> str:
    type_color = TYPE_COLORS.get(post_type, TEAL)
    progress = int((slide_num / total_slides) * 100)

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">{_base_style()}
<style>
  .slide-num {{ font-size:13px; color:{MUTED}; letter-spacing:2px; margin-bottom:24px; }}
  .progress-bar {{
    height:3px; background:{LINE}; border-radius:2px; margin-bottom:40px;
  }}
  .progress-fill {{
    height:3px; background:{TEAL}; border-radius:2px;
    width:{progress}%;
  }}
  .big-num {{
    font-size:140px; font-weight:800; color:{type_color};
    opacity:0.12; position:absolute; right:72px; top:50%;
    transform:translateY(-50%); line-height:1;
  }}
</style>
</head>
<body>
<div class="wrap">
  <div class="grid"></div>
  <div class="corner tl"></div>
  <div class="corner tr"></div>
  <div class="corner bl"></div>
  <div class="corner br"></div>
  <div class="big-num">{slide_num}</div>

  <div class="progress-bar"><div class="progress-fill"></div></div>
  <div class="slide-num">SLIDE {slide_num} OF {total_slides}</div>

  <div class="eyebrow">Influz Studio</div>

  <div class="headline" style="font-size:56px;">
    {cover_text}
  </div>

  <div class="subtext">{image_text}</div>

  <div class="footer">
    <div>
      <div class="brand">IS · Influz Studio</div>
      <div class="tagline">Crafting Digital Influence</div>
    </div>
    <div class="tagline">{slide_num}/{total_slides}</div>
  </div>
</div>
</body></html>"""


async def _render_html_to_png(html: str, output_path: Path) -> None:
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1080, "height": 1080})
        await page.set_content(html, wait_until="networkidle")
        await page.screenshot(path=str(output_path), type="png")
        await browser.close()


def generate_static_creative(item_id: int, cover_text: str, image_text: str,
                               post_type: str, topic: str) -> str:
    """Generate a static 1080x1080 PNG. Returns relative path."""
    html = static_template(cover_text, image_text, post_type, topic)
    output = CREATIVES_DIR / f"item_{item_id}_static.png"
    asyncio.run(_render_html_to_png(html, output))
    return f"creatives/item_{item_id}_static.png"


def generate_carousel_creatives(item_id: int, cover_text: str, image_text: str,
                                  post_type: str, total_slides: int = 5) -> list[str]:
    """Generate carousel slides. Returns list of relative paths."""
    paths = []
    # Parse image_text for slide-specific content
    slide_items = [s.strip() for s in image_text.split("|") if s.strip()]
    if len(slide_items) < total_slides:
        slide_items += [image_text] * (total_slides - len(slide_items))

    for i in range(1, total_slides + 1):
        slide_cover = cover_text if i == 1 else slide_items[i - 1]
        slide_body = slide_items[i - 1] if i > 1 else image_text
        html = carousel_slide(slide_cover, slide_body, i, total_slides, post_type)
        output = CREATIVES_DIR / f"item_{item_id}_slide_{i}.png"
        asyncio.run(_render_html_to_png(html, output))
        paths.append(f"creatives/item_{item_id}_slide_{i}.png")
    return paths
