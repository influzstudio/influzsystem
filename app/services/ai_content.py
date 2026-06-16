import os
import json
import re
from datetime import date, timedelta, datetime
import anthropic

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are a senior social media content strategist working for Influz Studio, \
an AI-powered social media management studio. Generate a professional content calendar for a \
client business covering {num_posts} posts spread across a {num_days}-day period starting {start_date}.

Return ONLY valid JSON — an array of exactly {num_posts} objects, ordered chronologically, \
with this EXACT structure:

[
  {{
    "post_date": "YYYY-MM-DD (a specific date within the period, posts spaced naturally — \
not every day, spread with realistic variation)",
    "post_type": "Reel | Static | Carousel | Story | UGC",
    "topic": "The creative angle — a punchy, specific content idea (e.g. 'Before & After — \
Bedroom Transformation', 'Monsoon Mood — Warm Lighting for Grey Days'). Max 8 words.",
    "cover_text": "The main headline text shown on the post image. Short, punchy. Max 10 words.",
    "image_text": "Supporting visual copy shown inside the image (subtext, slide labels, or \
tagline). Max 15 words.",
    "caption": "Full ready-to-post caption with emojis, a CTA (e.g. DM us, link in bio, \
comment below), and 8-10 relevant hashtags at the end. 3-5 sentences.",
    "platforms": ["instagram"] or ["facebook"] or ["instagram", "facebook"],
    "reference_note": "A brief description of the type of reference visual to look for \
(e.g. 'Warm toned bedroom reel with COB lighting', 'Minimal white product flat lay'). \
Not a URL — just a visual direction note."
  }}
]

Do not include any text before or after the JSON array. Do not use markdown code fences.

Guidelines:
- Post type mix roughly: 35% Static, 25% Reel, 25% Carousel, 10% Story, 5% UGC
- Captions must be specific to the business, niche, and brand voice — NOT generic filler
- Each post should have a distinct topic — no two posts with the same angle
- Include at least 2 posts tied to upcoming festivals/events if the dates fall in the period
- Instagram is always included; Facebook added on roughly every 3rd post
- Hashtags must be relevant to the niche and include 1-2 location-specific tags if city is known
- CTAs should vary (DM a keyword, comment below, link in bio, share with someone)
- UGC posts should feel like genuine customer reposts with a warm, appreciative tone"""


def _build_user_prompt(business_name: str, niche: str, brand_voice: str, goals: str, city: str = "") -> str:
    location_line = f"City/location: {city}\n" if city else ""
    return (
        f"Business name: {business_name}\n"
        f"Industry/niche: {niche}\n"
        f"Brand voice: {brand_voice}\n"
        f"Goals: {goals}\n"
        f"{location_line}\n"
        f"Generate the content calendar as specified."
    )


def _spaced_date(start_date: date, num_days: int, num_posts: int, index: int) -> date:
    if num_posts <= 1:
        offset = 0
    else:
        offset = round(index * (num_days - 1) / (num_posts - 1))
    offset = max(0, min(offset, num_days - 1))
    return start_date + timedelta(days=offset)


def _fallback_calendar(business_name: str, niche: str, start_date: date, num_days: int, num_posts: int) -> list[dict]:
    type_cycle = ["Static", "Reel", "Carousel", "Story", "UGC", "Static", "Reel", "Carousel"]
    platform_cycle = [["instagram"], ["instagram"], ["instagram", "facebook"], ["instagram"]]
    items = []
    for i in range(num_posts):
        items.append({
            "post_date": _spaced_date(start_date, num_days, num_posts, i).isoformat(),
            "post_type": type_cycle[i % len(type_cycle)],
            "topic": f"{niche.title()} content idea {i + 1}",
            "cover_text": f"Sample cover text — edit before approving",
            "image_text": f"Sample image text",
            "caption": f"Sample caption for {business_name} (post {i + 1}). Edit before approving. #socialmedia #{niche.replace(' ', '')} #influzstudio",
            "platforms": platform_cycle[i % len(platform_cycle)],
            "reference_note": f"Look for a clean {niche} reference image on Pinterest or Instagram.",
        })
    return items


def _validate_and_sort(items: list[dict], start_date: date, num_days: int, num_posts: int) -> list[dict]:
    end_date_excl = start_date + timedelta(days=num_days)
    for i, item in enumerate(items):
        valid = False
        raw = item.get("post_date", "")
        try:
            d = datetime.strptime(raw, "%Y-%m-%d").date()
            if start_date <= d < end_date_excl:
                valid = True
        except (ValueError, TypeError):
            pass
        if not valid:
            item["post_date"] = _spaced_date(start_date, num_days, num_posts, i).isoformat()
    items.sort(key=lambda x: x["post_date"])
    return items


def generate_content_calendar(
    business_name: str,
    niche: str,
    brand_voice: str,
    goals: str,
    start_date: date,
    num_days: int = 60,
    num_posts: int = 32,
    city: str = "",
) -> list[dict]:
    if not os.getenv("ANTHROPIC_API_KEY"):
        items = _fallback_calendar(business_name, niche, start_date, num_days, num_posts)
    else:
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=12000,
                system=SYSTEM_PROMPT.format(
                    num_days=num_days, num_posts=num_posts, start_date=start_date.isoformat()
                ),
                messages=[{
                    "role": "user",
                    "content": _build_user_prompt(business_name, niche, brand_voice, goals, city),
                }],
            )
            raw_text = "".join(
                block.text for block in response.content if block.type == "text"
            ).strip()
            raw_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text.strip())
            items = json.loads(raw_text)
            if not (isinstance(items, list) and len(items) > 0):
                items = _fallback_calendar(business_name, niche, start_date, num_days, num_posts)
            elif len(items) < num_posts:
                items += _fallback_calendar(business_name, niche, start_date, num_days, num_posts - len(items))
            elif len(items) > num_posts:
                items = items[:num_posts]
        except Exception:
            items = _fallback_calendar(business_name, niche, start_date, num_days, num_posts)

    return _validate_and_sort(items, start_date, num_days, num_posts)
