import math
from dataclasses import dataclass

from app.services.geo import normalize_text


@dataclass(frozen=True)
class RankingWeights:
    distance: float = 0.35
    rating: float = 0.25
    popularity: float = 0.15
    dish_match: float = 0.15
    price_fit: float = 0.10


DEFAULT_WEIGHTS = RankingWeights()


def score_place(
    distance_m: float | None,
    radius_m: int,
    rating: float | None,
    review_count: int | None,
    dish_names: list[str] | None,
    requested_dish: str | None,
    price_min: int | None,
    price_max: int | None,
    budget_per_person: int | None,
    is_open: bool,
    weights: RankingWeights = DEFAULT_WEIGHTS,
) -> float:
    s_dist = _score_distance(distance_m, radius_m)
    s_rating = _score_rating(rating)
    s_pop = _score_popularity(review_count)
    s_dish = _score_dish_match(dish_names, requested_dish)
    s_price = _score_price_fit(price_min, price_max, budget_per_person)

    raw = (
        weights.distance * s_dist
        + weights.rating * s_rating
        + weights.popularity * s_pop
        + weights.dish_match * s_dish
        + weights.price_fit * s_price
    )

    if is_open:
        raw *= 1.1

    return round(raw, 4)


def _score_distance(distance_m: float | None, radius_m: int) -> float:
    if distance_m is None or radius_m <= 0:
        return 0.0
    ratio = distance_m / radius_m
    return max(0.0, 1.0 - ratio)


def _score_rating(rating: float | None) -> float:
    if rating is None or rating <= 0:
        return 0.3
    return min(rating / 5.0, 1.0)


def _score_popularity(review_count: int | None) -> float:
    count = review_count or 0
    if count <= 0:
        return 0.1
    return min(math.log10(count + 1) / 3.0, 1.0)


def _score_dish_match(
    dish_names: list[str] | None,
    requested_dish: str | None,
) -> float:
    if not requested_dish:
        return 0.5
    if not dish_names:
        return 0.0
    needle = normalize_text(requested_dish)
    for name in dish_names:
        normalized = normalize_text(name)
        if needle in normalized or normalized in needle:
            return 1.0
    return 0.0


def _score_price_fit(
    price_min: int | None,
    price_max: int | None,
    budget: int | None,
) -> float:
    if budget is None:
        return 0.5
    if price_min is None and price_max is None:
        return 0.3

    avg_price = _avg_price(price_min, price_max)
    if avg_price is None:
        return 0.3
    if avg_price <= budget:
        return 1.0
    overshoot = avg_price / budget
    if overshoot <= 1.5:
        return 0.5
    return 0.1


def _avg_price(price_min: int | None, price_max: int | None) -> int | None:
    if price_min is not None and price_max is not None:
        return (price_min + price_max) // 2
    return price_min or price_max
