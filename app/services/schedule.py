from datetime import date, timedelta

TYPE_CYCLE = ["Post", "Story", "Carousel", "Reel", "UGC", "Post", "Story", "Carousel"]
PLATFORM_CYCLE = [["instagram"], ["instagram"], ["instagram", "facebook"], ["instagram"]]


def spaced_date(start_date: date, num_days: int, num_posts: int, index: int) -> date:
    if num_posts <= 1:
        offset = 0
    else:
        offset = round(index * (num_days - 1) / (num_posts - 1))
    offset = max(0, min(offset, num_days - 1))
    return start_date + timedelta(days=offset)


def build_default_schedule(start_date: date, num_days: int, num_posts: int) -> list[dict]:
    """Build a blank schedule: dates spaced evenly across the period, with default
    post types and platforms cycling for variety. No content (caption/theme) yet."""
    slots = []
    for i in range(num_posts):
        slots.append({
            "post_date": spaced_date(start_date, num_days, num_posts, i),
            "post_type": TYPE_CYCLE[i % len(TYPE_CYCLE)],
            "platforms": PLATFORM_CYCLE[i % len(PLATFORM_CYCLE)],
        })
    return slots
