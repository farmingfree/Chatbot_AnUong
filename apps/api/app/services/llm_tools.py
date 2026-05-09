"""
LLM Tools - OpenAI Function Calling Schema
Định nghĩa các tool mà LLM có thể gọi để tìm kiếm quán ăn
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_nearby_places",
            "description": "Tìm quán ăn gần vị trí người dùng dựa trên các tiêu chí cụ thể (tên món, giá, chay/halal). Dùng khi người dùng chỉ rõ muốn ăn món gì.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {
                        "type": "number",
                        "description": "Vĩ độ vị trí người dùng"
                    },
                    "lng": {
                        "type": "number",
                        "description": "Kinh độ vị trí người dùng"
                    },
                    "radius_m": {
                        "type": "integer",
                        "description": "Bán kính tìm kiếm tính bằng mét (100-5000)",
                        "default": 500
                    },
                    "dish_name": {
                        "type": "string",
                        "description": "Tên món ăn muốn tìm, ví dụ: 'bún đậu', 'phở'. Để trống nếu không specify"
                    },
                    "vegetarian": {
                        "type": "boolean",
                        "default": False
                    },
                    "halal": {
                        "type": "boolean",
                        "default": False
                    },
                    "price_max_per_person": {
                        "type": "integer",
                        "description": "Ngân sách tối đa mỗi người, đơn vị VNĐ"
                    },
                    "people_count": {
                        "type": "integer",
                        "description": "Số người ăn",
                        "default": 1
                    },
                    "limit": {
                        "type": "integer",
                        "default": 5
                    }
                },
                "required": ["lat", "lng"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_places_semantic",
            "description": "Tìm quán ăn theo mô tả tự nhiên (mood, không khí, dịp đặc biệt, yêu cầu phức tạp). Dùng khi người dùng KHÔNG chỉ rõ tên món cụ thể mà mô tả nhu cầu chung.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Mô tả tự nhiên nhu cầu ăn uống, ví dụ: 'quán lẩu view đẹp cho nhóm bạn', 'quán ăn sáng bình dân quận 1'"
                    },
                    "lat": {
                        "type": "number",
                        "description": "Vĩ độ vị trí người dùng"
                    },
                    "lng": {
                        "type": "number",
                        "description": "Kinh độ vị trí người dùng"
                    },
                    "radius_m": {
                        "type": "integer",
                        "description": "Bán kính tìm kiếm (mét)",
                        "default": 2000
                    },
                    "budget_per_person": {
                        "type": "integer",
                        "description": "Ngân sách tối đa mỗi người (VNĐ)"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 5
                    }
                },
                "required": ["query", "lat", "lng"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_nearby_dishes",
            "description": "Tìm các MÓN ĂN có sẵn gần vị trí người dùng. Dùng khi người dùng chưa biết muốn ăn gì và muốn xem các lựa chọn.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {
                        "type": "number",
                        "description": "Vĩ độ vị trí người dùng"
                    },
                    "lng": {
                        "type": "number",
                        "description": "Kinh độ vị trí người dùng"
                    },
                    "radius_m": {
                        "type": "integer",
                        "description": "Bán kính tìm kiếm tính bằng mét",
                        "default": 500
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Số lượng món ăn tối đa trả về",
                        "default": 12
                    }
                },
                "required": ["lat", "lng"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_place_detail",
            "description": "Lấy thông tin chi tiết của một quán ăn: menu đầy đủ, reviews, giờ mở cửa, chỉ đường.",
            "parameters": {
                "type": "object",
                "properties": {
                    "place_id": {
                        "type": "string",
                        "description": "UUID của quán ăn"
                    },
                    "lat": {
                        "type": "number",
                        "description": "Vĩ độ vị trí người dùng (để tính khoảng cách)"
                    },
                    "lng": {
                        "type": "number",
                        "description": "Kinh độ vị trí người dùng (để tính khoảng cách)"
                    }
                },
                "required": ["place_id"]
            }
        }
    }
]

SYSTEM_PROMPT = """Bạn là trợ lý AI giúp tìm quán ăn tại TP.HCM. Bạn thân thiện, ngắn gọn, dùng ngôn ngữ tự nhiên.

=== QUY TẮC TUYỆT ĐỐI — VI PHẠM LÀ LỖI NGHIÊM TRỌNG ===

1. KHÔNG BAO GIỜ bịa tên quán, địa chỉ, giá cả, rating, hoặc bất kỳ thông tin nào.
2. CHỈ đề cập quán ăn có trong kết quả tìm kiếm (tool results). Nếu tool chưa trả về dữ liệu, KHÔNG gợi ý quán.
3. Nếu không tìm thấy kết quả: nói rõ "Mình chưa tìm thấy quán phù hợp trong khu vực này" — KHÔNG tự nghĩ ra thay thế.
4. Nếu không chắc chắn thông tin (giờ mở cửa, giá hiện tại): nói "Mình không chắc lắm, bạn nên gọi trước để xác nhận nhé."
5. KHÔNG đưa gợi ý chung chung kiểu "bạn có thể thử phở ở quận 1" mà không có dữ liệu cụ thể.

=== CÁCH LÀM VIỆC ===

Khi người dùng hỏi:
- Nếu chỉ rõ tên món (phở, bún bò, lẩu...) → gọi search_nearby_places
- Nếu mô tả chung (mood, dịp, không khí) → gọi search_places_semantic
- Nếu chưa biết ăn gì → gọi search_nearby_dishes
- Nếu thiếu vị trí → hỏi lại: "Bạn đang ở khu vực nào để mình tìm quán gần nhé?"
- Nếu không có kết quả → thử mở rộng bán kính hoặc nói thẳng "Khu vực này mình chưa có dữ liệu"

=== FORMAT TRẢ LỜI ===

Khi CÓ kết quả từ tool:
- Liệt kê top 3-5 quán với thông tin CÓ TRONG dữ liệu (tên, giá, rating, khoảng cách)
- Mỗi quán kèm 1 lý do ngắn dựa trên DATA (không suy diễn)
- Kết thúc: "Bạn muốn xem chi tiết quán nào?"

Khi KHÔNG CÓ kết quả:
- "Mình chưa tìm thấy quán [yêu cầu] trong bán kính [X]m. Bạn muốn mình mở rộng khu vực tìm không?"

=== USER PROFILE ===

{user_profile}

Sử dụng profile để cá nhân hóa gợi ý:
- Ưu tiên quán phù hợp với sở thích đã biết
- Tránh gợi ý cuisine mà user không thích
- Áp dụng budget mặc định nếu user không nói rõ
- Nhưng KHÔNG bao giờ nói "vì bạn thích X" nếu user chưa nói trong cuộc hội thoại hiện tại

=== NGÔN NGỮ ===

Tiếng Việt, tự nhiên, thân thiện. Dùng "bạn", "mình". Ngắn gọn — tối đa 3-4 câu trước khi liệt kê quán."""


def build_system_prompt(user_profile: dict | None = None) -> str:
    if not user_profile:
        profile_text = "Chưa có thông tin về sở thích người dùng."
    else:
        parts = []
        if user_profile.get("favorite_cuisines"):
            parts.append(f"Món yêu thích: {', '.join(user_profile['favorite_cuisines'])}")
        if user_profile.get("disliked_cuisines"):
            parts.append(f"Không thích: {', '.join(user_profile['disliked_cuisines'])}")
        if user_profile.get("spicy_tolerance") is not None:
            levels = {0: "không ăn cay", 1: "cay ít", 2: "cay vừa", 3: "cay nhiều"}
            parts.append(f"Độ cay: {levels.get(user_profile['spicy_tolerance'], 'chưa rõ')}")
        if user_profile.get("budget_preference"):
            parts.append(f"Budget thường: {user_profile['budget_preference']:,}đ/người")
        if user_profile.get("favorite_districts"):
            parts.append(f"Khu vực hay ăn: {', '.join(user_profile['favorite_districts'])}")
        profile_text = "\n".join(parts) if parts else "Chưa có thông tin về sở thích người dùng."

    return SYSTEM_PROMPT.replace("{user_profile}", profile_text)
