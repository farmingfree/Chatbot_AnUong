"""Build text documents from structured place data for embedding."""

FEATURE_VI = {
    "ac": "máy lạnh",
    "wifi": "wifi",
    "parking": "chỗ đậu xe",
    "delivery": "giao hàng",
    "takeaway": "mang về",
    "outdoor": "ngoài trời",
    "vegetarian": "chay",
    "halal": "halal",
    "private_room": "phòng riêng",
    "card_payment": "thanh toán thẻ",
}


def build_place_document(
    name: str,
    district: str | None,
    dish_names: list[str],
    price_min: int | None,
    price_max: int | None,
    features: dict | None,
    rating: float | None,
    review_count: int | None,
) -> str:
    parts = [name]

    if district:
        parts.append(f"khu vực {district}")

    if dish_names:
        parts.append(f"món ăn: {', '.join(dish_names[:8])}")

    if price_min is not None and price_max is not None:
        parts.append(f"giá {price_min // 1000}k-{price_max // 1000}k/người")
    elif price_max is not None:
        parts.append(f"giá khoảng {price_max // 1000}k/người")

    if features:
        active = [FEATURE_VI.get(k, k) for k, v in features.items() if v]
        if active:
            parts.append(f"tiện ích: {', '.join(active)}")

    if rating is not None:
        parts.append(f"đánh giá {rating:.1f}/5")
        if review_count:
            parts.append(f"{review_count} lượt đánh giá")

    return ". ".join(parts)


def build_place_summary(
    name: str,
    district: str | None,
    dish_names: list[str],
    price_min: int | None,
    price_max: int | None,
    rating: float | None,
    is_open: bool = True,
) -> str:
    parts = [name]

    if district:
        parts.append(district)

    if dish_names:
        parts.append(", ".join(dish_names[:4]))

    if price_min is not None and price_max is not None:
        parts.append(f"{price_min // 1000}k-{price_max // 1000}k")

    if rating is not None:
        parts.append(f"⭐{rating:.1f}")

    if not is_open:
        parts.append("(đóng cửa)")

    return " | ".join(parts)
