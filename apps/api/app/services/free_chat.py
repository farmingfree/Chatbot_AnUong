"""
Free Chat Service - Context-aware rule-based chatbot (no API key needed)
Phân tích intent từ tin nhắn, sử dụng session context, và trả lời thông minh
"""
import re
from typing import Optional


# Greeting patterns
GREETINGS = ["chào", "hello", "hi", "xin chào", "hey", "ê", "alo"]

# Food-related keywords
FOOD_KEYWORDS = [
    "ăn", "món", "quán", "nhà hàng", "đói", "gợi ý", "recommend",
    "tìm", "gần", "ngon", "rẻ", "bữa", "trưa", "tối", "sáng",
    "ăn gì", "ăn ở đâu", "đi ăn", "order", "đặt"
]

# Specific dish keywords for search
DISH_NAMES = [
    "phở", "bún bò", "cơm tấm", "bánh mì", "hủ tiếu", "bún đậu",
    "bún chả", "cơm gà", "lẩu", "nướng", "sushi", "pizza", "burger",
    "trà sữa", "cà phê", "bánh xèo", "gỏi cuốn", "chả giò",
    "bún riêu", "mì quảng", "cao lầu", "bánh cuốn", "xôi",
    "cháo", "bò kho", "hải sản", "ốc", "chè", "kem",
    "bún mắm", "cơm niêu", "cơm văn phòng", "buffet", "dimsum",
    "mì cay", "tokbokki", "ramen", "pasta", "steak"
]

# District mapping for HCM
DISTRICT_PATTERNS = {
    r'qu?ận\s*1\b|q1\b|district\s*1': 'Quận 1',
    r'qu?ận\s*2\b|q2\b|district\s*2|thảo điền': 'Quận 2',
    r'qu?ận\s*3\b|q3\b|district\s*3': 'Quận 3',
    r'qu?ận\s*4\b|q4\b|district\s*4': 'Quận 4',
    r'qu?ận\s*5\b|q5\b|district\s*5': 'Quận 5',
    r'qu?ận\s*6\b|q6\b|district\s*6': 'Quận 6',
    r'qu?ận\s*7\b|q7\b|district\s*7|phú mỹ hưng': 'Quận 7',
    r'qu?ận\s*8\b|q8\b|district\s*8': 'Quận 8',
    r'qu?ận\s*9\b|q9\b|district\s*9': 'Quận 9',
    r'qu?ận\s*10\b|q10\b|district\s*10': 'Quận 10',
    r'qu?ận\s*11\b|q11\b|district\s*11': 'Quận 11',
    r'qu?ận\s*12\b|q12\b|district\s*12': 'Quận 12',
    r'bình thạnh|binh thanh': 'Bình Thạnh',
    r'tân bình|tan binh': 'Tân Bình',
    r'tân phú|tan phu': 'Tân Phú',
    r'phú nhuận|phu nhuan': 'Phú Nhuận',
    r'gò vấp|go vap': 'Gò Vấp',
    r'thủ đức|thu duc': 'Thủ Đức',
}


def detect_intent(message: str, session_context: dict = None) -> dict:
    """
    Detect user intent from message with session context awareness
    Returns: {
        "intent": str,
        "dish_name": str|None,
        "budget": int|None,
        "people": int|None,
        "district": str|None,
        "vegetarian": bool,
        "halal": bool,
        "meal_time": str|None,
        "purpose": str|None
    }
    """
    msg = message.lower().strip()
    session_context = session_context or {}

    result = {
        "intent": "unknown",
        "dish_name": None,
        "budget": session_context.get("budget_per_person"),
        "people": session_context.get("people_count", 1),
        "district": None,
        "vegetarian": session_context.get("vegetarian", False),
        "halal": session_context.get("halal", False),
        "meal_time": None,
        "purpose": None,
    }

    # Check greeting
    if any(msg.startswith(g) or msg == g for g in GREETINGS):
        if len(msg) < 20 and not any(k in msg for k in FOOD_KEYWORDS):
            result["intent"] = "greeting"
            return result

    # Extract district
    for pattern, district_name in DISTRICT_PATTERNS.items():
        if re.search(pattern, msg):
            result["district"] = district_name
            break

    # Extract budget (only if not already in session or explicitly mentioned)
    budget_patterns = [
        r'(?:dưới|under|max|tối đa|ít hơn)\s*(\d+)\s*(?:k|nghìn|ngàn)',
        r'(?:khoảng|tầm|around|~)\s*(\d+)\s*(?:k|nghìn|ngàn)',
        r'(\d+)\s*(?:k|nghìn|ngàn)(?:/người)?',
        r'(\d{2,3})\.?(\d{3})',
    ]
    for pattern in budget_patterns:
        match = re.search(pattern, msg)
        if match:
            if len(match.groups()) == 2:
                result["budget"] = int(match.group(1)) * 1000 + int(match.group(2))
            else:
                val = int(match.group(1))
                if val < 1000:
                    val *= 1000
                result["budget"] = val
            break

    # Extract people count
    people_match = re.search(r'(\d+)\s*người|nhóm\s*(\d+)|đi\s*(\d+)', msg)
    if people_match:
        result["people"] = int(people_match.group(1) or people_match.group(2) or people_match.group(3))

    # Check vegetarian/halal
    if any(k in msg for k in ["ăn chay", "đồ chay", "món chay", "vegetarian", "chay"]):
        result["vegetarian"] = True
    if "halal" in msg:
        result["halal"] = True

    # Extract meal time
    if any(k in msg for k in ["sáng", "breakfast", "morning"]):
        result["meal_time"] = "sáng"
    elif any(k in msg for k in ["trưa", "lunch", "noon"]):
        result["meal_time"] = "trưa"
    elif any(k in msg for k in ["tối", "dinner", "evening", "chiều"]):
        result["meal_time"] = "tối"

    # Extract purpose/context
    if any(k in msg for k in ["hẹn hò", "date", "romantic"]):
        result["purpose"] = "hẹn hò"
    elif any(k in msg for k in ["nhóm", "team", "đông người", "bạn bè"]):
        result["purpose"] = "nhóm"
    elif any(k in msg for k in ["gia đình", "family"]):
        result["purpose"] = "gia đình"

    # Check for specific dish
    for dish in DISH_NAMES:
        if dish in msg:
            result["dish_name"] = dish
            result["intent"] = "search_dish"
            return result

    # Check food intent with location/budget
    if any(k in msg for k in FOOD_KEYWORDS):
        # If has district or budget, likely wants to search
        if result["district"] or result["budget"]:
            result["intent"] = "search_food"
        else:
            result["intent"] = "suggest_food"
        return result

    # Check if asking for nearby
    if any(k in msg for k in ["gần", "gần đây", "quanh đây", "nearby"]):
        result["intent"] = "search_nearby"
        return result

    return result


def generate_text_response(intent: dict, session_context: dict = None) -> str:
    """Generate a context-aware text response based on detected intent and session"""
    session_context = session_context or {}
    
    if intent["intent"] == "greeting":
        return "Chào bạn! 👋 Mình là trợ lý tìm quán ăn ở Sài Gòn. Bạn muốn ăn gì hôm nay?"

    if intent["intent"] == "suggest_food":
        # Generic suggestion without specific location/budget
        return ("Hmm để mình gợi ý nha! 🤔 Sài Gòn có nhiều món ngon lắm:\n"
                "• Cơm tấm - chắc bụng, giá rẻ\n"
                "• Phở/Bún bò - món nước nhẹ nhàng\n"
                "• Bánh mì - nhanh gọn, đa dạng\n"
                "• Lẩu/Nướng - đi nhóm vui\n\n"
                "Bạn cho mình biết thêm khu vực hoặc budget để mình tìm quán cụ thể nhé!")

    # For search_dish, search_food, search_nearby - build context-aware response
    parts = []
    
    if intent["dish_name"]:
        parts.append(f"Ok, để mình tìm quán {intent['dish_name']}")
    elif intent["intent"] == "search_food":
        parts.append("Ok, để mình tìm quán ăn")
    elif intent["intent"] == "search_nearby":
        parts.append("Mình sẽ tìm quán gần bạn")
    
    # Add context details
    context_parts = []
    if intent["district"]:
        context_parts.append(f"ở {intent['district']}")
    if intent["budget"]:
        context_parts.append(f"dưới {intent['budget']//1000}k/người")
    if intent["people"] and intent["people"] > 1:
        context_parts.append(f"cho {intent['people']} người")
    if intent["meal_time"]:
        context_parts.append(f"bữa {intent['meal_time']}")
    if intent["vegetarian"]:
        context_parts.append("món chay")
    if intent["halal"]:
        context_parts.append("halal")
    if intent["purpose"]:
        context_parts.append(f"đi {intent['purpose']}")
    
    if context_parts:
        parts.append(" ".join(context_parts))
    
    response = " ".join(parts) + " nha! 🔍"
    
    return response


def should_search_places(intent: dict) -> bool:
    """Check if we should trigger a place search"""
    return intent["intent"] in ["search_dish", "search_nearby", "search_food"]


def should_search_dishes(intent: dict) -> bool:
    """Check if we should trigger a dish search (when user wants general suggestions)"""
    # Only suggest dishes if no specific dish mentioned and has some context
    return intent["intent"] == "suggest_food" and intent["dish_name"] is None


def build_search_args(intent: dict, lat: Optional[float], lng: Optional[float]) -> dict:
    """Build search arguments from intent"""
    args = {
        "lat": lat or 10.7769,
        "lng": lng or 106.7009,
        "radius_m": 2000,  # Increased to 2km for better results
        "limit": 5,
    }
    if intent.get("dish_name"):
        args["dish_name"] = intent["dish_name"]
    if intent.get("budget"):
        args["price_max_per_person"] = intent["budget"]
    if intent.get("people"):
        args["people_count"] = intent["people"]
    if intent.get("vegetarian"):
        args["vegetarian"] = True
    if intent.get("halal"):
        args["halal"] = True
    return args
