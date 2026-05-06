"""
LLM Tools - OpenAI Function Calling Schema
Định nghĩa các tool mà LLM có thể gọi để tìm kiếm quán ăn
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_nearby_places",
            "description": "Tìm quán ăn gần vị trí người dùng dựa trên các tiêu chí. Dùng khi người dùng muốn tìm quán ăn cụ thể hoặc đã biết muốn ăn món gì.",
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

SYSTEM_PROMPT = """Bạn là trợ lý AI giúp tìm quán ăn tại TP.HCM. Bạn thân thiện, ngắn gọn, dùng ngôn ngữ tự nhiên như người bạn.

Khi người dùng hỏi:
- Luôn suy nghĩ (reasoning) 1-2 câu trước khi gọi tool
- Gọi đúng tool phù hợp với intent
- Sau khi có kết quả, giải thích ngắn gọn tại sao recommend các quán này
- Nếu thiếu location, hỏi lại lịch sự

Format khi trả kết quả:
- Đừng list dài, chọn top 3-5 phù hợp nhất
- Thêm 1 câu lý do cụ thể cho mỗi quán (giá phù hợp, gần nhất, rating cao, etc.)
- Kết thúc bằng gợi ý hành động: "Bạn muốn xem menu của quán nào?"

Ngôn ngữ: Tiếng Việt, informal, GenZ-friendly. Dùng "bạn" thay vì "quý khách"."""
