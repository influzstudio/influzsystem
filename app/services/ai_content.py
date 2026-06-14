import os
import json
import re
from datetime import date, timedelta
import anthropic

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are a social media content strategist working for Influz Studio, \
an AI-powered social media management studio. Generate a content calendar for a client \
business covering exactly {num_days} consecutive days, starting from {start_date}.

Return ONLY valid JSON - an array of exactly {num_days} objects, one per calendar day \
(in order, starting from the start date), with this exact structure:

[
  {{
    "post_type": "Story | Post | Carousel | Reel",
    "platforms": ["instagram"] or ["facebook"] or ["instagram", "facebook"],
    "theme": "short theme name (3-6 words)",
    "caption": "a ready-to-use caption, 1-4 sentences, matching the brand voice. For Story \
entries, keep this short (1 sentence or a prompt like a poll/question).",
    "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"]
  }}
]

Do not include any text before or after the JSON array. Do not use markdown code fences.

Guidelines:
- Vary post types across the period - roughly: 40% Post, 25% Story, 20% Carousel, 15% Reel
- Most posts should target Instagram only; periodically (roughly every 3rd-4th day) include \
Facebook too (either alongside Instagram or alone), reflecting realistic cross-posting cadence
- Captions must be specific to the business and niche, not generic filler
- Build thematic variety across the {num_days} days - avoid repeating the same theme/idea
- Hashtags should be relevant to the business niche and location where applicable"""


def _build_user_prompt(business_name: str, niche: str, brand_voice: str, goals: str) -> str:
    return (
        f"Business name: {business_name}\n"
        f"Industry/niche: {niche}\n"
        f"Brand voice: {brand_voice}\n"
        f"Goals: {goals}\n\n"
        f"Generate the content calendar as specified."
    )


def _fallback_calendar(business_name: str, niche: str, num_days: int) -> list[dict]:
    """Used if the API call fails, so the UI never breaks."""
    type_cycle = ["Post", "Story", "Carousel", "Reel", "Post", "Story"]
    platform_cycle = [["instagram"], ["instagram"], ["instagram", "facebook"], ["instagram"]]
    items = []
    for i in range(num_days):
        items.append({
            "post_type": type_cycle[i % len(type_cycle)],
            "platforms": platform_cycle[i % len(platform_cycle)],
            "theme": f"{niche.title()} content idea {i + 1}",
            "caption": f"Sample caption for {business_name} (day {i + 1}) - edit before approving.",
            "hashtags": ["#socialmedia", f"#{niche.replace(' ', '')}", "#influzstudio"],
        })
    return items


def generate_content_calendar(
    business_name: str,
    niche: str,
    brand_voice: str,
    goals: str,
    start_date: date,
    num_days: int = 60,
) -> list[dict]:
    """Generate a content calendar covering num_days starting from start_date.

    Returns a list of dicts, each containing post_date plus the AI-generated fields.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        items = _fallback_calendar(business_name, niche, num_days)
    else:
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=16000,
                system=SYSTEM_PROMPT.format(num_days=num_days, start_date=start_date.isoformat()),
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
                items = _fallback_calendar(business_name, niche, num_days)
            elif len(items) < num_days:
                # Pad with fallback items if the model returned fewer than requested
                items += _fallback_calendar(business_name, niche, num_days - len(items))
            elif len(items) > num_days:
                items = items[:num_days]

        except Exception:
            items = _fallback_calendar(business_name, niche, num_days)

    # Attach actual calendar dates
    for i, item in enumerate(items):
        item["post_date"] = (start_date + timedelta(days=i)).isoformat()

    return items
