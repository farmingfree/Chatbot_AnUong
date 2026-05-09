"""
Seed realistic restaurant data for development.
No API keys required.

Usage:
    python -m scripts.seed_realistic              # 500 places (default)
    python -m scripts.seed_realistic --count=300  # custom count
    python -m scripts.seed_realistic --force      # reseed even if data exists
"""
import argparse
import asyncio
import random
import uuid
from datetime import datetime

from sqlalchemy import text

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import AsyncSessionLocal, engine
from app.models import Place, Dish, PlaceDish
from app.services.geo import normalize_text

SEED = 42

DISTRICTS = [
    {"name": "Quận 1", "lat": 10.7769, "lng": 106.7009},
    {"name": "Quận 2", "lat": 10.7870, "lng": 106.7480},
    {"name": "Quận 3", "lat": 10.7843, "lng": 106.6867},
    {"name": "Quận 4", "lat": 10.7578, "lng": 106.7064},
    {"name": "Quận 5", "lat": 10.7540, "lng": 106.6633},
    {"name": "Quận 6", "lat": 10.7460, "lng": 106.6352},
    {"name": "Quận 7", "lat": 10.7340, "lng": 106.7220},
    {"name": "Quận 10", "lat": 10.7726, "lng": 106.6691},
    {"name": "Bình Thạnh", "lat": 10.8014, "lng": 106.7100},
    {"name": "Phú Nhuận", "lat": 10.7990, "lng": 106.6802},
    {"name": "Tân Bình", "lat": 10.8018, "lng": 106.6528},
    {"name": "Tân Phú", "lat": 10.7920, "lng": 106.6280},
    {"name": "Bình Tân", "lat": 10.7652, "lng": 106.6040},
    {"name": "Gò Vấp", "lat": 10.8386, "lng": 106.6652},
    {"name": "Thủ Đức", "lat": 10.8494, "lng": 106.7534},
]

DISHES = [
    ("Phở bò", "Món nước", 45000),
    ("Phở gà", "Món nước", 40000),
    ("Cơm tấm sườn", "Cơm", 35000),
    ("Cơm tấm bì chả", "Cơm", 40000),
    ("Bún bò Huế", "Món nước", 45000),
    ("Bún thịt nướng", "Món nước", 40000),
    ("Bánh mì thịt", "Ăn vặt", 25000),
    ("Bánh mì ốp la", "Ăn vặt", 30000),
    ("Hủ tiếu Nam Vang", "Món nước", 40000),
    ("Mì Quảng", "Món nước", 45000),
    ("Gỏi cuốn", "Ăn vặt", 30000),
    ("Bánh xèo", "Ăn vặt", 35000),
    ("Lẩu thái", "Lẩu", 150000),
    ("Lẩu bò", "Lẩu", 180000),
    ("Trà sữa trân châu", "Đồ uống", 35000),
    ("Cà phê sữa đá", "Đồ uống", 25000),
    ("Bò kho", "Món nước", 45000),
    ("Cháo lòng", "Món nước", 30000),
    ("Pizza", "Món Âu", 120000),
    ("Bún riêu", "Món nước", 40000),
    ("Chả giò", "Ăn vặt", 30000),
    ("Xôi mặn", "Ăn sáng", 20000),
    ("Bánh cuốn", "Ăn sáng", 30000),
    ("Bò lá lốt", "Nướng", 55000),
    ("Cá kho tộ", "Cơm", 50000),
    ("Canh chua cá", "Cơm", 45000),
    ("Gà nướng", "Nướng", 80000),
    ("Sushi", "Món Nhật", 100000),
    ("Ramen", "Món Nhật", 85000),
    ("Kem bơ", "Đồ uống", 30000),
]

NAME_PREFIXES = [
    "Quán", "Tiệm", "Nhà hàng", "Bếp", "Chợ", "Góc",
    "Xe", "Gánh", "Hẻm", "Phố", "Lò", "Cửa hàng",
]

NAME_FOODS = [
    "Phở", "Cơm Tấm", "Bún Bò", "Bánh Mì", "Hủ Tiếu",
    "Lẩu", "Nướng", "Chay", "Hải Sản", "Gà",
    "Vịt", "Dê", "Bò", "Ốc", "Chè",
    "Bánh Xèo", "Cháo", "Bún Riêu", "Mì", "Xôi",
    "Cá", "Trà Sữa", "Cà Phê", "Kem", "Bánh Cuốn",
]

NAME_SUFFIXES = [
    "Sài Gòn", "Ngon", "Xưa", "Mới", "Gia Truyền",
    "Cô Ba", "Anh Hai", "Chị Năm", "Bà Tư", "Ông Già",
    "24h", "Đêm", "Hẻm", "Phố", "Xóm",
    "Số 1", "Tư Beo", "Năm Sanh", "Út Nhỏ", "Hai Lúa",
    "Ngã Tư", "Đầu Hẻm", "Cuối Đường", "Gốc Cây", "Bên Sông",
]

STREETS = [
    "Nguyễn Huệ", "Lê Lợi", "Trần Hưng Đạo", "Hai Bà Trưng",
    "Pasteur", "Võ Văn Tần", "Nguyễn Đình Chiểu", "Cách Mạng Tháng 8",
    "Lý Tự Trọng", "Phạm Ngũ Lão", "Nguyễn Trãi", "Lê Văn Sỹ",
    "Phan Xích Long", "Hoàng Sa", "Trường Sa", "Điện Biên Phủ",
    "Nguyễn Thị Minh Khai", "Võ Thị Sáu", "Nam Kỳ Khởi Nghĩa",
    "Bùi Viện", "Đề Thám", "Nguyễn Cư Trinh", "Tôn Đức Thắng",
]

PRICE_TIERS = [
    (1, 15000, 50000),
    (2, 50000, 150000),
    (3, 150000, 350000),
    (4, 350000, 800000),
]


def generate_name(used_names: set) -> str:
    for _ in range(200):
        prefix = random.choice(NAME_PREFIXES)
        food = random.choice(NAME_FOODS)
        suffix = random.choice(NAME_SUFFIXES)
        name = f"{prefix} {food} {suffix}"
        if name not in used_names:
            used_names.add(name)
            return name
    return f"Quán Ăn {uuid.uuid4().hex[:6]}"


def generate_hours() -> dict:
    open_hour = random.choice(["05:00", "06:00", "07:00", "08:00", "09:00", "10:00", "11:00"])
    close_hour = random.choice(["20:00", "21:00", "22:00", "23:00", "00:00", "01:00"])
    schedule = f"{open_hour}-{close_hour}"
    days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    hours = {}
    for day in days:
        if random.random() < 0.92:
            hours[day] = schedule
        else:
            hours[day] = "closed"
    return hours


def generate_place(district: dict, used_names: set) -> dict:
    lat = district["lat"] + random.uniform(-0.008, 0.008)
    lng = district["lng"] + random.uniform(-0.008, 0.008)
    tier = random.choices(PRICE_TIERS, weights=[35, 40, 15, 10])[0]
    price_level, price_min, price_max = tier
    rating = round(random.triangular(3.0, 5.0, 4.2), 1)
    review_count = int(random.lognormvariate(4.0, 1.3))
    review_count = max(3, min(review_count, 5000))

    return {
        "id": uuid.uuid4(),
        "name": generate_name(used_names),
        "address": f"{random.randint(1, 999)} {random.choice(STREETS)}, {district['name']}",
        "lat": round(lat, 6),
        "lng": round(lng, 6),
        "district": district["name"],
        "phone": f"028 {random.randint(1000, 9999)} {random.randint(1000, 9999)}",
        "price_min": price_min,
        "price_max": price_max,
        "price_level": price_level,
        "rating_google": rating,
        "review_count": review_count,
        "hours": generate_hours(),
        "features": {
            "ac": random.random() < 0.6,
            "wifi": random.random() < 0.7,
            "parking": random.random() < 0.5,
            "delivery": random.random() < 0.4,
            "vegetarian": random.random() < 0.12,
            "halal": random.random() < 0.03,
        },
        "is_closed": False,
        "image_urls": None,
        "data_quality_score": round(random.uniform(0.5, 0.95), 2),
        "created_at": datetime.utcnow(),
    }


async def seed(count: int = 500, force: bool = False):
    random.seed(SEED)
    print(f"[seed] Target: {count} places across {len(DISTRICTS)} districts")

    from app.models.base import Base
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.run_sync(Base.metadata.create_all)
    print("[OK] Tables ensured")

    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM places"))
        existing_count = result.scalar() or 0

    if existing_count >= count and not force:
        print(f"[SKIP] Already have {existing_count} places (target={count}). Use --force to reseed.")
        return

    if existing_count > 0:
        print(f"[CLEAR] Removing {existing_count} existing places...")
        async with AsyncSessionLocal() as session:
            await session.execute(text("DELETE FROM place_dishes"))
            await session.execute(text("DELETE FROM reviews"))
            await session.execute(text("DELETE FROM places"))
            await session.execute(text("DELETE FROM dishes"))
            await session.commit()

    async with AsyncSessionLocal() as session:
        dish_objects = []
        for name, category, avg_price in DISHES:
            dish = Dish(
                id=uuid.uuid4(),
                name=name,
                name_normalized=normalize_text(name),
                category=category,
                avg_price=avg_price,
            )
            session.add(dish)
            dish_objects.append(dish)
        await session.flush()
        print(f"[OK] Created {len(dish_objects)} dishes")

        used_names: set = set()
        places_per_district = count // len(DISTRICTS)
        remainder = count % len(DISTRICTS)
        place_count = 0

        for i, district in enumerate(DISTRICTS):
            n = places_per_district + (1 if i < remainder else 0)
            for _ in range(n):
                place_data = generate_place(district, used_names)
                place = Place(**place_data)
                session.add(place)
                await session.flush()

                await session.execute(text(
                    "UPDATE places SET geom = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326) WHERE id = :id"
                ), {"lng": place_data["lng"], "lat": place_data["lat"], "id": str(place_data["id"])})

                num_dishes = random.randint(3, 6)
                selected_dishes = random.sample(dish_objects, min(num_dishes, len(dish_objects)))
                for dish in selected_dishes:
                    pd = PlaceDish(
                        place_id=place_data["id"],
                        dish_id=dish.id,
                        price=max(5000, dish.avg_price + random.randint(-10000, 20000)),
                        is_available=random.random() < 0.95,
                    )
                    session.add(pd)

                place_count += 1

            await session.flush()
            print(f"  {district['name']}: {n} places")

        await session.commit()
        print(f"\n[DONE] Seeded {place_count} places, {len(dish_objects)} dishes, ~{place_count * 4} place_dishes")


def main():
    parser = argparse.ArgumentParser(description="Seed realistic restaurant data")
    parser.add_argument("--count", type=int, default=500, help="Number of places to create")
    parser.add_argument("--force", action="store_true", help="Reseed even if data exists")
    args = parser.parse_args()
    asyncio.run(seed(count=args.count, force=args.force))


if __name__ == "__main__":
    main()
