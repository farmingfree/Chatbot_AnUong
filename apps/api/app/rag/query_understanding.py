"""Query understanding: parse natural language into structured search parameters."""

import re
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class ParsedQuery:
    raw_query: str
    cuisine: Optional[str] = None
    district: Optional[str] = None
    mood: Optional[str] = None
    budget: Optional[int] = None
    group_size: Optional[int] = None
    dining_intent: Optional[str] = None
    time_of_day: Optional[str] = None
    special_constraints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


CUISINE_MAP: list[tuple[str, list[str]]] = [
    ("phở", ["phở", "pho"]),
    ("bún bò", ["bún bò", "bun bo"]),
    ("cơm tấm", ["cơm tấm", "com tam"]),
    ("bánh mì", ["bánh mì", "banh mi"]),
    ("hủ tiếu", ["hủ tiếu", "hu tieu"]),
    ("bún đậu", ["bún đậu", "bun dau"]),
    ("bún chả", ["bún chả", "bun cha"]),
    ("lẩu", ["lẩu", "lau", "hotpot"]),
    ("nướng", ["nướng", "nuong", "bbq", "barbecue"]),
    ("sushi", ["sushi", "sashimi"]),
    ("pizza", ["pizza"]),
    ("burger", ["burger", "hamburger"]),
    ("bánh xèo", ["bánh xèo", "banh xeo"]),
    ("bún riêu", ["bún riêu", "bun rieu"]),
    ("mì quảng", ["mì quảng", "mi quang"]),
    ("bánh cuốn", ["bánh cuốn", "banh cuon"]),
    ("cháo", ["cháo", "chao"]),
    ("hải sản", ["hải sản", "hai san", "seafood"]),
    ("ốc", ["ốc"]),
    ("dimsum", ["dimsum", "dim sum"]),
    ("ramen", ["ramen"]),
    ("steak", ["steak", "bò bít tết", "beefsteak"]),
    ("buffet", ["buffet"]),
    ("cơm gà", ["cơm gà", "com ga"]),
    ("bò kho", ["bò kho", "bo kho"]),
    ("xôi", ["xôi"]),
    ("trà sữa", ["trà sữa", "tra sua", "milk tea"]),
    ("cà phê", ["cà phê", "ca phe", "coffee", "cafe"]),
    ("chè", ["chè"]),
    ("kem", ["kem", "ice cream"]),
]

DISTRICT_PATTERNS: list[tuple[str, str]] = [
    (r'qu?ận\s*1\b|q\.?1\b|district\s*1', 'Quận 1'),
    (r'qu?ận\s*2\b|q\.?2\b|thảo điền|thao dien', 'Quận 2'),
    (r'qu?ận\s*3\b|q\.?3\b', 'Quận 3'),
    (r'qu?ận\s*4\b|q\.?4\b', 'Quận 4'),
    (r'qu?ận\s*5\b|q\.?5\b', 'Quận 5'),
    (r'qu?ận\s*6\b|q\.?6\b', 'Quận 6'),
    (r'qu?ận\s*7\b|q\.?7\b|phú mỹ hưng|phu my hung', 'Quận 7'),
    (r'qu?ận\s*8\b|q\.?8\b', 'Quận 8'),
    (r'qu?ận\s*9\b|q\.?9\b', 'Quận 9'),
    (r'qu?ận\s*10\b|q\.?10\b', 'Quận 10'),
    (r'qu?ận\s*11\b|q\.?11\b', 'Quận 11'),
    (r'qu?ận\s*12\b|q\.?12\b', 'Quận 12'),
    (r'bình thạnh|binh thanh', 'Bình Thạnh'),
    (r'tân bình|tan binh', 'Tân Bình'),
    (r'tân phú|tan phu', 'Tân Phú'),
    (r'phú nhuận|phu nhuan', 'Phú Nhuận'),
    (r'gò vấp|go vap', 'Gò Vấp'),
    (r'thủ đức|thu duc', 'Thủ Đức'),
]

MOOD_PATTERNS: list[tuple[str, list[str]]] = [
    ("romantic", ["hẹn hò", "date", "romantic", "lãng mạn"]),
    ("chill", ["chill", "thư giãn", "nhẹ nhàng", "yên tĩnh", "quiet"]),
    ("lively", ["vui", "sôi động", "lively", "party", "nhậu"]),
    ("cozy", ["ấm cúng", "cozy", "xinh"]),
    ("view", ["view đẹp", "view", "rooftop", "tầng thượng"]),
    ("instagrammable", ["sống ảo", "instagram", "check-in", "đẹp"]),
    ("local", ["bình dân", "vỉa hè", "lề đường", "local", "dân dã"]),
    ("upscale", ["sang trọng", "fine dining", "cao cấp", "luxury"]),
]

TIME_KEYWORDS: list[tuple[str, list[str]]] = [
    ("sáng", ["sáng", "breakfast", "morning", "ăn sáng"]),
    ("trưa", ["trưa", "lunch", "noon", "ăn trưa"]),
    ("chiều", ["chiều", "afternoon", "xế"]),
    ("tối", ["tối", "dinner", "evening", "ăn tối"]),
    ("khuya", ["khuya", "đêm", "late night", "midnight", "supper"]),
]

INTENT_KEYWORDS: list[tuple[str, list[str]]] = [
    ("explore", ["khám phá", "thử", "explore", "mới"]),
    ("quick_meal", ["nhanh", "quick", "gấp", "vội"]),
    ("gathering", ["nhóm", "team", "đông người", "bạn bè", "họp mặt", "liên hoan"]),
    ("family", ["gia đình", "family", "con nhỏ", "trẻ em"]),
    ("business", ["đối tác", "business", "khách hàng", "tiếp khách"]),
    ("solo", ["một mình", "solo", "alone"]),
]


def parse_query(message: str) -> ParsedQuery:
    msg = message.lower().strip()
    result = ParsedQuery(raw_query=message)

    # Cuisine
    for canonical, variants in CUISINE_MAP:
        if any(v in msg for v in variants):
            result.cuisine = canonical
            break

    # District
    for pattern, name in DISTRICT_PATTERNS:
        if re.search(pattern, msg):
            result.district = name
            break

    # Mood
    for mood, keywords in MOOD_PATTERNS:
        if any(k in msg for k in keywords):
            result.mood = mood
            break

    # Budget
    budget_patterns = [
        (r'(?:dưới|under|max|tối đa|ít hơn)\s*(\d+)\s*(?:k|nghìn|ngàn)', 1000),
        (r'(?:khoảng|tầm|around|~)\s*(\d+)\s*(?:k|nghìn|ngàn)', 1000),
        (r'(\d+)\s*(?:k|nghìn|ngàn)(?:\s*/\s*người)?', 1000),
        (r'(\d{2,3})\.(\d{3})\b', None),
    ]
    for pattern, multiplier in budget_patterns:
        m = re.search(pattern, msg)
        if m:
            if multiplier is None:
                result.budget = int(m.group(1)) * 1000 + int(m.group(2))
            else:
                val = int(m.group(1))
                if val < 1000:
                    val *= multiplier
                result.budget = val
            break

    # Group size
    people_match = re.search(r'(\d+)\s*người|nhóm\s*(\d+)|đi\s*(\d+)', msg)
    if people_match:
        result.group_size = int(next(g for g in people_match.groups() if g))

    # Time of day
    for tod, keywords in TIME_KEYWORDS:
        if any(k in msg for k in keywords):
            result.time_of_day = tod
            break

    # Dining intent
    for intent, keywords in INTENT_KEYWORDS:
        if any(k in msg for k in keywords):
            result.dining_intent = intent
            break

    # Special constraints
    if any(k in msg for k in ["ăn chay", "đồ chay", "món chay", "vegetarian", "chay"]):
        result.special_constraints.append("vegetarian")
    if "halal" in msg:
        result.special_constraints.append("halal")
    if any(k in msg for k in ["máy lạnh", "air con", "ac", "điều hòa"]):
        result.special_constraints.append("air_con")
    if any(k in msg for k in ["wifi", "wi-fi"]):
        result.special_constraints.append("wifi")
    if any(k in msg for k in ["parking", "đậu xe", "bãi xe"]):
        result.special_constraints.append("parking")
    if any(k in msg for k in ["giao hàng", "delivery", "ship"]):
        result.special_constraints.append("delivery")

    return result
