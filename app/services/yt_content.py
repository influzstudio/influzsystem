"""
AI-powered YouTube content generation for ZenTraders channel.
Generates video ideas, titles, descriptions, tags, thumbnail text, scripts.
"""
import os
import json
import re
from datetime import date, timedelta
import anthropic

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are a YouTube growth strategist specializing in trading and finance channels.
Generate a YouTube content calendar for a FACELESS trading channel.

Channel details:
- Niche: AI Trading Bots — Gold (XAU/USD), BTC, Quotex OTC pairs
- Style: Faceless (screen recordings, charts, bot signals, text overlays)
- Goal: Grow from 51 subscribers to 500+ in 3 months
- Platform mix: YouTube Shorts (60s max) + Long-form videos (8-15 mins)

Return ONLY valid JSON — an array of exactly {num_videos} objects:
[
  {{
    "publish_date": "YYYY-MM-DD",
    "video_type": "Short | Long | Live",
    "title": "SEO-optimized title with high-CTR hook. Max 60 chars. Include numbers/power words.",
    "description": "Full YouTube description. 3-4 paragraphs. Include: hook, what viewers learn, timestamps (for long-form), CTA to subscribe. End with 5-7 relevant hashtags.",
    "tags": ["tag1", "tag2", ...],
    "thumbnail_text": "Bold text for thumbnail overlay. Max 5 words. High contrast.",
    "script_outline": "Key points to cover in order. 5-8 bullet points for long-form, 3-4 for Shorts.",
    "content_angle": "The specific hook/angle (e.g. 'Bot made 3x in 1 week on Gold', 'Quotex secret strategy nobody talks about')"
  }}
]

Guidelines:
- 40% Shorts (quick tips, bot signals, trade results — drives discoverability)
- 50% Long-form (tutorials, strategy guides, bot setups — drives watch time)
- 10% Lives (only after base audience grows)
- Titles must be specific and curiosity-driven: NOT "Gold Trading Tips" but "This Gold Bot Made ₹12,000 in 3 Days (Full Setup)"
- Tags: mix of exact match (quotex strategy), broad (trading bots), long-tail (quotex otc pairs strategy 2026)
- Each video must have a UNIQUE angle — no generic content
- Include festival/market event hooks where relevant
- Thumbnail text must create curiosity or show results

Do not include any text before or after the JSON array."""


def generate_youtube_calendar(
    channel_name: str,
    niche: str,
    goals: str,
    start_date: date,
    num_days: int = 30,
    num_videos: int = 12,
) -> list[dict]:
    """Generate AI YouTube content calendar."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return _fallback_calendar(start_date, num_videos)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8000,
            system=SYSTEM_PROMPT.format(num_videos=num_videos),
            messages=[{
                "role": "user",
                "content": f"""Channel: {channel_name}
Niche: {niche}
Goals: {goals}
Start date: {start_date.isoformat()}
Period: {num_days} days
Number of videos: {num_videos}

Generate the content calendar. Space videos naturally — 3-4 per week for Shorts, 1-2 per week for Long-form."""
            }]
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
        items = json.loads(raw)
        if isinstance(items, list) and len(items) > 0:
            return items[:num_videos]
    except Exception:
        pass
    return _fallback_calendar(start_date, num_videos)


def _fallback_calendar(start_date: date, num_videos: int) -> list[dict]:
    templates = [
        {"video_type": "Short", "title": "This Quotex OTC Signal Works 80% of the Time",
         "thumbnail_text": "80% WIN RATE", "content_angle": "High win rate OTC signal demo"},
        {"video_type": "Long", "title": "How I Built a Gold Trading Bot That Made ₹15,000 in a Week",
         "thumbnail_text": "₹15K IN 1 WEEK", "content_angle": "Full bot setup tutorial"},
        {"video_type": "Short", "title": "Gold is Moving — My Bot Caught This Signal Live",
         "thumbnail_text": "LIVE GOLD SIGNAL", "content_angle": "Real-time bot signal"},
        {"video_type": "Long", "title": "Quotex OTC Pairs: Complete Strategy Guide 2026",
         "thumbnail_text": "FULL STRATEGY", "content_angle": "Comprehensive OTC guide"},
    ]
    items = []
    for i in range(num_videos):
        t = templates[i % len(templates)]
        pub_date = start_date + timedelta(days=i * 2)
        items.append({
            "publish_date": pub_date.isoformat(),
            "video_type": t["video_type"],
            "title": t["title"],
            "description": f"Full video about {t['content_angle']}. Subscribe for daily trading signals and bot updates.\n\n#trading #quotex #goldtrading #tradingbot #forexbot",
            "tags": ["quotex", "gold trading", "trading bot", "forex bot", "quotex strategy", "AI trading"],
            "thumbnail_text": t["thumbnail_text"],
            "script_outline": f"1. Introduction\n2. {t['content_angle']}\n3. Live demo\n4. Results\n5. CTA",
            "content_angle": t["content_angle"],
        })
    return items
