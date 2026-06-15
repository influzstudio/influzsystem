import os
import json
import re
from datetime import date, timedelta, datetime
import anthropic

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are a social media content strategist working for Influz Studio, \
an AI-powered social media management studio. Generate a content calendar for a client \
business covering a {num_days}-day period starting from {start_date} (inclusive), but \
containing only {num_posts} posts total - the client's monthly package covers a limited \
number of posts, so posts should be spaced out across the period rather than one per day.

Return ONLY valid JSON - an array of exactly {num_posts} objects, ordered chronologically, \
with this exact structure:

[
  {{
    "post_date": "YYYY-MM-DD (a date within the {num_days}-day period starting {start_date}, \
spaced out roughly evenly with natural variation - avoid clustering all posts together)",
    "post_type": "Story | Post | Carousel | Reel | UGC",
    "platforms": ["instagram"] or ["facebook"] or ["instagram", "facebook"],
    "theme": "short theme name (3-6 words)",
    "caption": "a ready-to-use caption, 1-4 sentences, matching the brand voice. For Story \
entries, keep this short (1 sentence or a prompt like a poll/question). For UGC entries, \
write it as a repost/feature caption (e.g. thanking a customer, featuring their content).",
    "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"]
  }}
]

Do not include any text before or after the JSON array. Do not use markdown code fences.

Guidelines:
- Vary post types: roughly 35% Post, 20% Story, 20% Carousel, 15% Reel, 10% UGC
- Most posts should target Instagram only; occasionally include Facebook too (alongside \
Instagram or alone), reflecting realistic cross-posting cadence
- Captions must be specific to the business and niche, not generic filler
- Build thematic variety across all {num_posts} posts - avoid repeating the same theme/idea
- Hashtags should be relevant to the business niche and location where applicable
- UGC posts should feel like genuine customer-content reposts, not promotional copy"""


def _build_user_prompt(business_name: str, niche: str, brand_voice: str, goals: str) -> str:
    return (
        f"Business name: {business_name}\n"
        f"Industry/niche: {niche}\n"
        f"Brand voice: {brand_voice}\n"
        f"Goals: {goals}\n\n"
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
    """Used if the API call fails, so the UI never breaks."""
    type_cycle = ["Post", "Story", "Carousel", "Reel", "UGC", "Post", "Story", "Carousel"]
    platform_cycle = [["instagram"], ["instagram"], ["instagram", "facebook"], ["instagram"]]
    items = []
    for i in range(num_posts):
        items.append({
            "post_date": _spaced_date(start_date, num_days, num_posts, i).isoformat(),
            "post_type": type_cycle[i % len(type_cycle)],
            "platforms": platform_cycle[i % len(platform_cycle)],
            "theme": f"{niche.title()} content idea {i + 1}",
            "caption": f"Sample caption for {business_name} (post {i + 1}) - edit before approving.",
            "hashtags": ["#socialmedia", f"#{niche.replace(' ', '')}", "#influzstudio"],
        })
    return items


def _validate_dates(items: list[dict], start_date: date, num_days: int) -> list[dict]:
    """Ensure every item has a valid post_date within range; fix or reassign if not."""
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
            d = _spaced_date(start_date, num_days, len(items), i)
        item["post_date"] = d.isoformat()
    return items


def generate_content_calendar(
    business_name: str,
    niche: str,
    brand_voice: str,
    goals: str,
    start_date: date,
    num_days: int = 60,
    num_posts: int = 32,
) -> list[dict]:
    """Generate num_posts content entries spread across num_days starting from start_date."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        items = _fallback_calendar(business_name, niche, start_date, num_days, num_posts)
    else:
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=8000,
                system=SYSTEM_PROMPT.format(
                    num_days=num_days, num_posts=num_posts, start_date=start_date.isoformat()
                ),
                messages=[
                    {
                        "role": "user",
                        "content": _build_user_prompt(business_name, niche, brand_voice, goals),
                    }
                ],
            )
            raw_text = "".join(
                block.text for block in response.content if block.type == "text"
            ).strip()

            raw_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text.strip())

            items = json.loads(raw_text)
            if not (isinstance(items, list) and len(items) > 0):
                items = _fallback_calendar(business_name, niche, start_date, num_days, num_posts)
            elif len(items) < num_posts:
                extra = _fallback_calendar(business_name, niche, start_date, num_days, num_posts - len(items))
                items += extra
            elif len(items) > num_posts:
                items = items[:num_posts]

        except Exception:
            items = _fallback_calendar(business_name, niche, start_date, num_days, num_posts)

    items = _validate_dates(items, start_date, num_days)
    items.sort(key=lambda x: x["post_date"])
    return items
