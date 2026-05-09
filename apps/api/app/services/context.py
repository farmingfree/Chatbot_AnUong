"""Context building: token-efficient prompt assembly for LLM calls."""

import math
from datetime import datetime, timezone


MAX_PLACES_IN_CONTEXT = 6
MAX_REVIEWS_PER_PLACE = 3
MAX_HISTORY_MESSAGES = 10


def compress_place_context(ranked_places: list[dict], max_places: int = MAX_PLACES_IN_CONTEXT) -> str:
    """Build compact place context for LLM tool results. ~50 tokens per place."""
    lines = []
    for i, p in enumerate(ranked_places[:max_places], 1):
        parts = [f"{i}. {p['name']}"]
        if p.get("district"):
            parts.append(p["district"])
        if p.get("distance_m"):
            d = p["distance_m"]
            parts.append(f"{d}m" if d < 1000 else f"{d/1000:.1f}km")
        if p.get("price_min") and p.get("price_max"):
            parts.append(f"{p['price_min']//1000}-{p['price_max']//1000}k")
        elif p.get("price_max"):
            parts.append(f"~{p['price_max']//1000}k")
        if p.get("rating"):
            parts.append(f"★{p['rating']:.1f}")
        if p.get("dish_names"):
            parts.append(", ".join(p["dish_names"][:3]))
        if p.get("review_summary"):
            parts.append(f"[{p['review_summary']}]")
        lines.append(" | ".join(parts))
    return "\n".join(lines)


def summarize_reviews(reviews: list[dict], max_reviews: int = MAX_REVIEWS_PER_PLACE) -> str | None:
    """Compress reviews into a single sentiment line. Returns None if no reviews."""
    if not reviews:
        return None

    ratings = [r.get("rating", 0) for r in reviews if r.get("rating")]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0

    # Extract key phrases from review content
    positive_keywords = []
    negative_keywords = []

    for r in reviews[:max_reviews]:
        content = (r.get("content") or "").lower()
        if not content:
            continue
        if r.get("rating", 3) >= 4:
            for kw in _extract_food_keywords(content):
                if kw not in positive_keywords:
                    positive_keywords.append(kw)
        elif r.get("rating", 3) <= 2:
            for kw in _extract_food_keywords(content):
                if kw not in negative_keywords:
                    negative_keywords.append(kw)

    parts = []
    if positive_keywords:
        parts.append(f"+{','.join(positive_keywords[:3])}")
    if negative_keywords:
        parts.append(f"-{','.join(negative_keywords[:2])}")
    if not parts and avg_rating > 0:
        if avg_rating >= 4:
            parts.append("đa số khen")
        elif avg_rating <= 2.5:
            parts.append("nhiều phàn nàn")

    return " ".join(parts) if parts else None


def compress_chat_history(messages: list[dict], max_messages: int = MAX_HISTORY_MESSAGES) -> list[dict]:
    """Compress chat history for token efficiency.

    Strategy:
    - Keep last max_messages
    - Truncate long assistant messages to 150 chars
    - Remove tool call/result messages (data already consumed)
    - Merge consecutive same-role messages
    """
    # Filter out tool messages and empty messages
    filtered = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "tool":
            continue
        if not content:
            continue
        if isinstance(content, dict) or isinstance(content, list):
            continue
        filtered.append(msg)

    # Keep only last N
    filtered = filtered[-max_messages:]

    # Compress long assistant messages
    compressed = []
    for msg in filtered:
        role = msg["role"]
        content = msg["content"]

        if role == "assistant" and len(content) > 150:
            content = content[:147] + "..."

        # Merge with previous if same role
        if compressed and compressed[-1]["role"] == role:
            compressed[-1]["content"] += "\n" + content
        else:
            compressed.append({"role": role, "content": content})

    return compressed


def build_context_message(session) -> str | None:
    """Build a compact context injection. Returns None if nothing to add."""
    parts = []
    if session.lat and session.lng:
        parts.append(f"loc:{session.lat:.4f},{session.lng:.4f}")
    if session.budget_per_person:
        parts.append(f"budget:{session.budget_per_person//1000}k")
    if session.people_count > 1:
        parts.append(f"{session.people_count}pax")
    if session.vegetarian:
        parts.append("veg")
    if session.halal:
        parts.append("halal")
    if session.recommended_place_ids:
        parts.append(f"seen:{len(session.recommended_place_ids)}")

    if not parts:
        return None
    return "[" + " ".join(parts) + "]"


def _extract_food_keywords(text: str) -> list[str]:
    """Extract meaningful food/service keywords from review text."""
    positive_map = {
        "ngon": "ngon", "tươi": "tươi", "nóng": "nóng hổi",
        "nhanh": "phục vụ nhanh", "sạch": "sạch sẽ", "đẹp": "không gian đẹp",
        "rẻ": "giá rẻ", "nhiều": "phần lớn", "thơm": "thơm",
        "view": "view đẹp", "mát": "mát mẻ",
    }
    negative_map = {
        "chậm": "phục vụ chậm", "bẩn": "bẩn", "đắt": "đắt",
        "ít": "phần ít", "lâu": "đợi lâu", "hôi": "hôi",
        "nguội": "nguội", "mặn": "mặn", "nhạt": "nhạt",
    }

    found = []
    for keyword, label in positive_map.items():
        if keyword in text:
            found.append(label)
    for keyword, label in negative_map.items():
        if keyword in text:
            found.append(label)
    return found[:3]


def estimate_tokens(text: str) -> int:
    """Rough token estimate for Vietnamese text (~1.5 chars per token)."""
    return math.ceil(len(text) / 1.5)
