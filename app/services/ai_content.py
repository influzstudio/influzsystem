import os, json, re
from datetime import date, timedelta


def _build_prompt(business_name, niche, brand_voice, goals, city, usp, services,
                   products, target_audience, price_range, content_pillars,
                   competitors, start_date, num_posts):
    services_txt = ", ".join(services) if services else "(not specified — infer typical services for this niche)"
    products_txt = ", ".join(products) if products else "(not specified — infer from services/niche)"
    pillars_txt = ", ".join(content_pillars) if content_pillars else "(pick pillars that fit the services and audience below)"

    return f"""You are the social media strategist for {business_name}, a {niche} business{f" in {city}" if city else ""}.
Write a {num_posts}-post content calendar that could ONLY belong to this exact business — not a generic {niche} template.

BUSINESS PROFILE
- Business: {business_name}
- Industry / niche: {niche}
- Brand voice: {brand_voice}
- USP (what makes them different): {usp or "not specified"}
- Services offered: {services_txt}
- Key products / packages to feature: {products_txt}
- Price range / market positioning: {price_range or "not specified"}
- Target audience: {target_audience or "not specified — infer a realistic ideal customer for this niche and price point"}
- Competitors / differentiation context: {competitors or "not specified"}
- Marketing goals: {goals or "general growth"}
- Content pillars to rotate through: {pillars_txt}
- Location: {city or "not specified"}

RULES
1. Every post must reference something concrete from the profile above — a specific service, product/package name, price point, audience pain point, or local detail. Do not write posts that could apply to any random business in this niche.
2. Rotate through the services/products and content pillars across the calendar so no single offering is repeated too often; spread promotional posts, educational posts, social proof, and engagement posts across the period.
3. Match tone strictly to the brand voice given.
4. Captions should speak directly to the target audience's motivations and price sensitivity described above.
5. No placeholder text like "[insert product]" or "your business" — always use real specifics from the profile.
6. When post_type is "Carousel", also fill carousel_slides with 4-6 slide objects that tell a real structured sequence: slide 1 is the hook (matches cover_text), the middle slides each cover ONE distinct concrete point (a specific inclusion, a price detail, a benefit, a testimonial-style line — never restate the same idea twice), and the final slide is a clear call-to-action naming how to act (DM, link in bio, call, visit website). Each slide needs slide_headline (max 6 words) and slide_subtext (max 12 words). For any other post_type, set carousel_slides to [].

Start date: {start_date} | Period: 60 days

Return ONLY a JSON array with {num_posts} objects, each having:
post_date (YYYY-MM-DD), post_type (Static/Reel/Carousel/Story/UGC), platforms (list),
topic (specific, max 10 words, must name a real service/product/pillar from above),
cover_text (headline, max 8 words), image_text (supporting copy, max 12 words),
caption (full with emojis+hashtags, speaks to the target audience directly),
reference_note (visual direction — what should be photographed/shown), content_angle (the hook/pillar this post uses),
carousel_slides (see rule 6 — [] unless post_type is Carousel)

Output raw JSON only. No markdown fences, no preamble."""


def generate_social_calendar(business_name, niche, brand_voice, goals, city, start_date, num_posts=16,
                              usp="", services=None, products=None, target_audience="",
                              price_range="", content_pillars=None, competitors=""):
    prompt = _build_prompt(
        business_name=business_name, niche=niche, brand_voice=brand_voice, goals=goals, city=city,
        usp=usp, services=services or [], products=products or [], target_audience=target_audience,
        price_range=price_range, content_pillars=content_pillars or [], competitors=competitors,
        start_date=start_date, num_posts=num_posts,
    )

    # Try Anthropic first
    ak = os.getenv("ANTHROPIC_API_KEY")
    if ak:
        try:
            import anthropic
            c = anthropic.Anthropic(api_key=ak)
            r = c.messages.create(model="claude-sonnet-4-6", max_tokens=12000,
                messages=[{"role": "user", "content": prompt}])
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", r.content[0].text.strip())
            items = json.loads(raw)
            if isinstance(items, list) and items: return items[:num_posts]
        except Exception as e:
            if "credit" not in str(e).lower(): print(f"Anthropic error: {e}")

    # Try Groq (free) — primary path for this deployment
    if os.getenv("GROQ_API_KEY"):
        try:
            from app.services.ai_base import call_ai_groq
            raw = call_ai_groq(prompt, max_tokens=8000)
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
            items = json.loads(raw)
            if isinstance(items, list) and items: return items[:num_posts]
        except Exception as e:
            print(f"Groq error: {e}")

    return _fallback(start_date, num_posts, business_name)


def _fallback(start_date, num, name):
    types = ["Static","Reel","Carousel","Story","UGC"]
    return [{"post_date": (start_date+timedelta(days=i*2)).isoformat(),
             "post_type": types[i%5], "platforms": ["instagram"],
             "topic": f"Content idea {i+1}", "cover_text": f"Post {i+1}",
             "image_text": "", "caption": f"Sample caption for {name}. #socialmedia",
             "reference_note": "", "content_angle": ""} for i in range(num)]
