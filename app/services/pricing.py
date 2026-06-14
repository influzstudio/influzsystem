import json
from sqlalchemy.orm import Session

from app.models.client import PricingRate, ContentItem

DEFAULT_RATES = {
    "Story": 150.0,
    "Post": 300.0,
    "Carousel": 500.0,
    "Reel": 800.0,
}


def ensure_default_rates(db: Session):
    """Create default pricing rate rows if they don't exist yet."""
    existing = {r.post_type for r in db.query(PricingRate).all()}
    for post_type, rate in DEFAULT_RATES.items():
        if post_type not in existing:
            db.add(PricingRate(post_type=post_type, rate_per_platform=rate))
    db.commit()


def get_rates_map(db: Session) -> dict[str, float]:
    ensure_default_rates(db)
    rates = db.query(PricingRate).all()
    return {r.post_type: r.rate_per_platform for r in rates}


def calculate_item_cost(post_type: str, platforms: list[str], rates: dict[str, float]) -> float:
    rate = rates.get(post_type, 0.0)
    return rate * max(len(platforms), 1)


def calculate_calendar_cost(content_items: list[ContentItem], rates: dict[str, float]) -> dict:
    """Returns total cost plus a breakdown by post type and by platform-count."""
    total = 0.0
    by_type = {}
    counts_by_type = {}

    for item in content_items:
        platforms = json.loads(item.platforms or "[]")
        cost = calculate_item_cost(item.post_type, platforms, rates)
        total += cost
        by_type[item.post_type] = by_type.get(item.post_type, 0.0) + cost
        counts_by_type[item.post_type] = counts_by_type.get(item.post_type, 0) + 1

    return {
        "total": total,
        "by_type": by_type,
        "counts_by_type": counts_by_type,
        "total_posts": len(content_items),
    }
