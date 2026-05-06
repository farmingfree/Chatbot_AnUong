"""Manual entry source - Interactive CLI or JSON import"""
import json
from typing import AsyncIterator
from .base import BaseSource, RawPlace


class ManualSource(BaseSource):
    source_name = "manual"

    DISTRICTS = [
        "Quận 1", "Quận 2", "Quận 3", "Quận 4", "Quận 5",
        "Quận 6", "Quận 7", "Quận 8", "Quận 9", "Quận 10",
        "Quận 11", "Quận 12", "Bình Thạnh", "Tân Bình", "Tân Phú",
        "Gò Vấp", "Phú Nhuận", "Bình Tân", "Thủ Đức"
    ]

    ALL_DISHES = [
        "Phở", "Bún bò Huế", "Cơm tấm", "Bánh mì", "Bún đậu mắm tôm",
        "Hủ tiếu", "Cháo", "Xôi", "Bún riêu", "Lẩu", "Đồ nướng",
        "Đồ chay", "Bánh cuốn", "Pizza", "Burger", "Sushi", "Ramen",
        "Cơm chiên", "Mì xào", "Bún thịt nướng", "Gỏi cuốn", "Kem", "Chè"
    ]

    async def fetch(self, from_file: str | None = None, **kwargs) -> AsyncIterator[RawPlace]:
        """
        2 modes:
        - from_file=None: interactive mode
        - from_file="path.json": import from JSON
        """
        if from_file:
            # Import from JSON file
            with open(from_file, encoding="utf-8") as f:
                places = json.load(f)
            for p in places:
                yield RawPlace(**p, source="manual", source_id=None, raw_data=None)
            return

        # Interactive mode
        print("\n🍜 NHẬP TAY QUÁN ĂN — Gõ 'xong' để kết thúc\n")

        while True:
            print("─" * 50)
            name = input("Tên quán (hoặc 'xong' để thoát): ").strip()
            if name.lower() == "xong":
                break

            address = input("Địa chỉ đầy đủ: ").strip()

            # Select district
            print("\nChọn quận:")
            for i, d in enumerate(self.DISTRICTS, 1):
                print(f"  {i:2}. {d}")
            district_idx = int(input("Số quận: ")) - 1
            district = self.DISTRICTS[district_idx]

            phone = input("SĐT (Enter để bỏ qua): ").strip() or None

            price_input = input("Giá (VD: 30000-80000, hoặc 1/2/3/4 cho level, Enter để bỏ qua): ").strip()
            price_min, price_max, price_level = self._parse_price_input(price_input)

            rating_input = input("Rating (1.0-5.0, Enter để bỏ qua): ").strip()
            rating = float(rating_input) if rating_input else None

            # Multi-select dishes
            print("\nChọn món ăn (nhập số, cách nhau bằng dấu phẩy, VD: 1,3,7):")
            for i, d in enumerate(self.ALL_DISHES, 1):
                print(f"  {i:2}. {d}")
            dishes_input = input("Món: ").strip()
            dishes = []
            if dishes_input:
                for idx in dishes_input.split(","):
                    try:
                        dishes.append(self.ALL_DISHES[int(idx.strip()) - 1])
                    except:
                        pass

            hours_str = input("Giờ mở cửa (VD: 6:00-22:00, Enter để bỏ qua): ").strip()
            hours = None
            if hours_str:
                days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
                hours = {d: hours_str for d in days}

            features_input = input("Đặc điểm (AC/wifi/chay/halal/parking, cách nhau dấu phẩy): ").strip().lower()
            features = {
                "ac": "ac" in features_input,
                "wifi": "wifi" in features_input,
                "vegetarian": "chay" in features_input,
                "halal": "halal" in features_input,
                "parking": "parking" in features_input or "gửi xe" in features_input
            }

            print(f"\n✅ Đã nhập: {name} — {district}")
            confirm = input("Lưu? (Enter = có, 'n' = không): ").strip()
            if confirm.lower() != 'n':
                yield RawPlace(
                    name=name, address=address, lat=None, lng=None,
                    district=district, phone=phone,
                    price_min=price_min, price_max=price_max, price_level=price_level,
                    rating=rating, review_count=None,
                    hours=hours, features=features, dishes=dishes,
                    image_urls=[], source="manual",
                    source_id=None, raw_data=None
                )

    def _parse_price_input(self, text: str) -> tuple[int | None, int | None, int | None]:
        """Parse price input: '30000-80000' or '1/2/3/4' or empty"""
        if not text:
            return None, None, None

        # Level input
        if text in ["1", "2", "3", "4"]:
            level = int(text)
            ranges = {1: (15000, 50000), 2: (50000, 150000), 3: (150000, 350000), 4: (350000, 999000)}
            price_min, price_max = ranges[level]
            return price_min, price_max, level

        # Range input
        if "-" in text:
            parts = text.split("-")
            try:
                price_min = int(parts[0].strip())
                price_max = int(parts[1].strip())
                return price_min, price_max, RawPlace._price_to_level(price_min, price_max)
            except:
                return None, None, None

        # Single value
        try:
            val = int(text)
            return val, val, RawPlace._price_to_level(val, val)
        except:
            return None, None, None

    def estimate_count(self, **kwargs) -> int:
        return 0  # Unknown for manual entry
