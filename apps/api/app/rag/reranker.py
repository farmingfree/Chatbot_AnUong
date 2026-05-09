"""Rerank candidates with 7 ranking factors + user preference boost."""

import math
from dataclasses import dataclass

from app.rag.retriever import SearchCandidate
from app.rag.query_understanding import ParsedQuery
from app.services.geo import normalize_text, is_open_now


@dataclass(frozen=True)
class RankWeights:
    semantic: float = 0.15
    review_sentiment: float = 0.10
    rating: float = 0.10
    popularity: float = 0.08
    recency: float = 0.05
    user_pref: float = 0.12
    distance: float = 0.15
    district: float = 0.15
    cuisine: float = 0.10


DEFAULT_WEIGHTS = RankWeights()


def rerank(
    candidates: list[SearchCandidate],
    radius_m: int,
    parsed: ParsedQuery | None = None,
    budget_per_person: int | None = None,
    user_profile: dict | None = None,
    limit: int = 5,
    weights: RankWeights = DEFAULT_WEIGHTS,
) -> list[dict]:
    if parsed is None:
        parsed = ParsedQuery(raw_query="")
    user_profile = user_profile or {}

    budget = budget_per_person or parsed.budget
    scored = []

    for c in candidates:
        scores = {
            "semantic": max(c.semantic_score, c.keyword_score),
            "review_sentiment": _score_review_sentiment(c),
            "rating": _score_rating(c.rating),
            "popularity": _score_popularity(c.review_count),
            "recency": _score_recency(c),
            "user_pref": _score_user_preference(c, user_profile),
            "distance": _score_distance(c.distance_m, radius_m),
            "district": _score_district(c.district, parsed.district),
            "cuisine": _score_cuisine(c.dish_names, parsed.cuisine),
        }

        final = (
            weights.semantic * scores["semantic"]
            + weights.review_sentiment * scores["review_sentiment"]
            + weights.rating * scores["rating"]
            + weights.popularity * scores["popularity"]
            + weights.recency * scores["recency"]
            + weights.user_pref * scores["user_pref"]
            + weights.distance * scores["distance"]
            + weights.district * scores["district"]
            + weights.cuisine * scores["cuisine"]
        )

        # Bonuses
        if is_open_now(c.hours):
            final *= 1.1
        if budget and _price_fits(c.price_min, c.price_max, budget):
            final *= 1.05

        scored.append({
            "place_id": c.place_id,
            "name": c.name,
            "district": c.district,
            "summary": c.summary,
            "distance_m": c.distance_m,
            "final_score": round(final, 4),
            "scores": {k: round(v, 3) for k, v in scores.items()},
            "dish_names": c.dish_names,
            "price_min": c.price_min,
            "price_max": c.price_max,
            "rating": c.rating,
            "review_count": c.review_count,
            "review_summary": getattr(c, "review_summary", None),
        })

    scored.sort(key=lambda x: x["final_score"], reverse=True)
    return scored[:limit]


# ── Individual scoring functions ──

def _score_district(place_district: str, requested: str | None) -> float:
    if not requested:
        return 0.5
    if not place_district:
        return 0.0
    return 1.0 if normalize_text(place_district) == normalize_text(requested) else 0.0


def _score_cuisine(dish_names: list[str], requested: str | None) -> float:
    if not requested:
        return 0.5
    if not dish_names:
        return 0.0
    needle = normalize_text(requested)
    for d in dish_names:
        if needle in normalize_text(d):
            return 1.0
    return 0.0


def _score_distance(distance_m: float | None, radius_m: int) -> float:
    if distance_m is None or radius_m <= 0:
        return 0.0
    return max(0.0, 1.0 - distance_m / radius_m)


def _score_rating(rating: float | None) -> float:
    if rating is None:
        return 0.3
    return min(rating / 5.0, 1.0)


def _score_popularity(review_count: int) -> float:
    if review_count <= 0:
        return 0.1
    return min(math.log10(review_count + 1) / 3.0, 1.0)


def _score_review_sentiment(c: SearchCandidate) -> float:
    """Score based on review sentiment. Uses review_sentiment field if available on candidate,
    otherwise falls back to rating+count heuristic."""
    sentiment = getattr(c, "review_sentiment", None)
    if sentiment is not None:
        return max(0.0, min(1.0, sentiment))
    # Fallback: high rating + many reviews = positive sentiment
    if c.rating is None:
        return 0.3
    rating_factor = c.rating / 5.0
    count_factor = min(math.log10(max(c.review_count, 1) + 1) / 2.5, 1.0)
    return 0.6 * rating_factor + 0.4 * count_factor


def _score_recency(c: SearchCandidate) -> float:
    """Score based on data freshness. Uses last_updated field if available."""
    last_updated = getattr(c, "last_updated", None)
    if last_updated is None:
        return 0.5
    try:
        from datetime import datetime, timezone
        if isinstance(last_updated, str):
            dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
        else:
            dt = last_updated
        age_days = (datetime.now(timezone.utc) - dt).days
        if age_days <= 7:
            return 1.0
        if age_days <= 30:
            return 0.8
        if age_days <= 90:
            return 0.5
        return 0.2
    except Exception:
        return 0.5


def _score_user_preference(c: SearchCandidate, profile: dict) -> float:
    """Score based on match with user's long-term preferences."""
    if not profile:
        return 0.5

    score = 0.5
    boosts = 0

    # Boost for favorite cuisines
    fav_cuisines = profile.get("favorite_cuisines", [])
    if fav_cuisines and c.dish_names:
        for dish in c.dish_names:
            dish_norm = normalize_text(dish)
            for fav in fav_cuisines:
                if normalize_text(fav) in dish_norm:
                    score += 0.3
                    boosts += 1
                    break
            if boosts:
                break

    # Penalize disliked cuisines
    disliked = profile.get("disliked_cuisines", [])
    if disliked and c.dish_names:
        for dish in c.dish_names:
            dish_norm = normalize_text(dish)
            for d in disliked:
                if normalize_text(d) in dish_norm:
                    score -= 0.4
                    break

    # Boost for favorite districts
    fav_districts = profile.get("favorite_districts", [])
    if fav_districts and c.district:
        if normalize_text(c.district) in [normalize_text(d) for d in fav_districts]:
            score += 0.15

    # Budget alignment
    budget_pref = profile.get("budget_preference")
    if budget_pref and (c.price_min or c.price_max):
        if _price_fits(c.price_min, c.price_max, budget_pref):
            score += 0.1

    return max(0.0, min(1.0, score))


def _price_fits(price_min: int | None, price_max: int | None, budget: int) -> bool:
    avg = price_min or price_max
    if price_min and price_max:
        avg = (price_min + price_max) // 2
    if avg is None:
        return True
    return avg <= budget
