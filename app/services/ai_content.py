import os
import json
import re
import anthropic

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are a social media content strategist working for Influz Studio, \
an AI-powered social media management studio. Generate a one-week content calendar \
for a client business.

Return ONLY valid JSON - an array of exactly 7 objects, one per day (Monday through \
Sunday), with this exact structure:

[
  {
    "day": "Mon",
    "type": "Post | Reel | Story | Carousel",
    "theme": "short theme name (3-5 words)",
    "caption": "a ready-to-use caption, 2-4 sentences, matching the brand voice",
    "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"]
  }
]

Do not include any text before or after the JSON array. Do not use markdown code \
fences. Vary the post types across the week (mix of Post, Reel, Story, Carousel). \
Captions should be specific to the business, not generic."""


def _build_user_prompt(business_name: str, niche: str, brand_voice: str, goals: str) -> str:
    return (
        f"Business name: {business_name}\n"
        f"Industry/niche: {niche}\n"
        f"Brand voice: {brand_voice}\n"
        f"Goals: {goals}\n\n"
        f"Generate the one-week content calendar as specified."
    )


def _fallback_calendar(business_name: str, niche: str) -> list[dict]:
    """Used if the API call fails, so the UI never breaks."""
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    types = ["Post", "Reel", "Story", "Carousel", "Post", "Reel", "Story"]
    return [
        {
            "day": d,
            "type": t,
            "theme": f"{niche.title()} highlight",
            "caption": f"Sample caption for {business_name} - edit this before approving.",
            "hashtags": ["#socialmedia", f"#{niche.replace(' ', '')}", "#influzstudio"],
        }
        for d, t in zip(days, types)
    ]


def generate_content_calendar(
    business_name: str, niche: str, brand_voice: str, goals: str
) -> list[dict]:
    if not os.getenv("ANTHROPIC_API_KEY"):
        return _fallback_calendar(business_name, niche)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
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

        # Strip accidental markdown fences if present
        raw_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text.strip())

        items = json.loads(raw_text)
        if isinstance(items, list) and len(items) > 0:
            return items
        return _fallback_calendar(business_name, niche)

    except Exception:
        return _fallback_calendar(business_name, niche)
