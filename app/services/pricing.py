import json

POST_TYPES = ["Story", "Post", "Carousel", "Reel", "UGC"]


def get_client_rates(client) -> dict[str, float]:
    return {
        "Story": client.rate_story,
        "Post": client.rate_post,
        "Carousel": client.rate_carousel,
        "Reel": client.rate_reel,
        "UGC": client.rate_ugc,
    }


def calculate_item_cost(item, client) -> float:
    if item.is_on_demand:
        return client.rate_on_demand
    rates = get_client_rates(client)
    platforms = json.loads(item.platforms or "[]")
    rate = rates.get(item.post_type, 0.0)
    return rate * max(len(platforms), 1)


def calculate_calendar_cost(content_items, client) -> dict:
    """Returns a cost summary split into the regular monthly package vs on-demand add-ons."""
    rates = get_client_rates(client)

    regular_total = 0.0
    on_demand_total = 0.0
    on_demand_count = 0
    by_type = {}
    counts_by_type = {}

    for item in content_items:
        if item.is_on_demand:
            on_demand_total += client.rate_on_demand
            on_demand_count += 1
            continue

        platforms = json.loads(item.platforms or "[]")
        cost = rates.get(item.post_type, 0.0) * max(len(platforms), 1)
        regular_total += cost
        by_type[item.post_type] = by_type.get(item.post_type, 0.0) + cost
        counts_by_type[item.post_type] = counts_by_type.get(item.post_type, 0) + 1

    return {
        "regular_total": regular_total,
        "on_demand_total": on_demand_total,
        "on_demand_count": on_demand_count,
        "grand_total": regular_total + on_demand_total,
        "by_type": by_type,
        "counts_by_type": counts_by_type,
        "regular_posts": sum(counts_by_type.values()),
    }
