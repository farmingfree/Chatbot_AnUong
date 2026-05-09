"""
Fetch real restaurant data from Google Places API with caching.

Usage:
    python -m scripts.fetch_google_places --api-key=YOUR_KEY
    python -m scripts.fetch_google_places --api-key=YOUR_KEY --areas=q1,q3,binh_thanh
    python -m scripts.fetch_google_places --api-key=YOUR_KEY --lat=10.78 --lng=106.70 --radius=1000
"""
import argparse
import asyncio
import hashlib
import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path

import httpx
from sqlalchemy import text, select

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import AsyncSessionLocal
from app.models import Place, Dish, PlaceDish
from app.services.geo import normalize_text

NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
DETAIL_URL = "https://maps.googleapis.com/maps/api/place/details/json"

CACHE_MAX_AGE_DAYS = 7

AREAS = {
    "q1":         {"lat": 10.7769, "lng": 106.7009, "name": "Quận 1"},
    "q2":         {"lat": 10.7870, "lng": 106.7480, "name": "Quận 2"},
    "q3":         {"lat": 10.7843, "lng": 106.6867, "name": "Quận 3"},
    "q4":         {"lat": 10.7578, "lng": 106.7064, "name": "Quận 4"},
    "q5":         {"lat": 10.7540, "lng": 106.6633, "name": "Quận 5"},
    "q7":         {"lat": 10.7340, "lng": 106.7220, "name": "Quận 7"},
    "q10":        {"lat": 10.7726, "lng": 106.6691, "name": "Quận 10"},
    "binh_thanh": {"lat": 10.8014, "lng": 106.7100, "name": "Bình Thạnh"},
    "phu_nhuan":  {"lat": 10.7990, "lng": 106.6802, "name": "Phú Nhuận"},
    "tan_binh":   {"lat": 10.8018, "lng": 106.6528, "name": "Tân Bình"},
    "go_vap":     {"lat": 10.8386, "lng": 106.6652, "name": "Gò Vấp"},
    "thu_duc":    {"lat": 10.8494, "lng": 106.7534, "name": "Thủ Đức"},
}

DISH_KEYWORDS = {
    "pho": "Phở", "phở": "Phở", "bun": "Bún", "bún": "Bún",
    "com tam": "Cơm tấm", "cơm tấm": "Cơm tấm",
    "banh mi": "Bánh mì", "bánh mì": "Bánh mì",
    "hu tieu": "Hủ tiếu", "hủ tiếu": "Hủ tiếu",
    "lau": "Lẩu", "lẩu": "Lẩu",
    "cafe": "Cà phê", "coffee": "Cà phê",
    "tra sua": "Trà sữa", "trà sữa": "Trà sữa",
    "pizza": "Pizza", "burger": "Burger",
    "nuong": "Nướng", "nướng": "Nướng",
}

DAY_MAP = {0: "sun", 1: "mon", 2: "tue", 3: "wed", 4: "thu", 5: "fri", 6: "sat"}

PRICE_RANGES = {
    1: (15000, 50000),
    2: (50000, 200000),
    3: (200000, 500000),
    4: (500000, 1000000),
}


def detect_dishes(name: str) -> list[str]:
    name_lower = name.lower()
    found = []
    for keyword, dish_name in DISH_KEYWORDS.items():
        if keyword in name_lower and dish_name not in found:
            found.append(dish_name)
    return found


def parse_hours(periods: list[dict] | None) -> dict | None:
    if not periods:
        return None
    hours = {}
    for period in periods:
        open_info = period.get("open", {})
        close_info = period.get("close", {})
        day = DAY_MAP.get(open_info.get("day"))
        if not day:
            continue
        open_time = open_info.get("time", "0000")
        close_time = close_info.get("time", "2359") if close_info else "23:59"
        hours[day] = f"{open_time[:2]}:{open_time[2:]}-{close_time[:2]}:{close_time[2:]}"
    return hours or None


def cache_key(lat: float, lng: float, radius: int) -> str:
    raw = f"{lat:.4f}_{lng:.4f}_{radius}"
    return hashlib.md5(raw.encode()).hexdigest()


def load_cache(cache_dir: Path, key: str) -> list[dict] | None:
    path = cache_dir / f"{key}.json"
    if not path.exists():
        return None
    age_days = (time.time() - path.stat().st_mtime) / 86400
    if age_days > CACHE_MAX_AGE_DAYS:
        return None
    with open(path) as f:
        return json.load(f)


def save_cache(cache_dir: Path, key: str, data: list[dict]):
    cache_dir.mkdir(parents=True, exist_ok=True)
    with open(cache_dir / f"{key}.json", "w") as f:
        json.dump(data, f, ensure_ascii=False)


async def fetch_nearby(client: httpx.AsyncClient, api_key: str,
                       lat: float, lng: float, radius: int,
                       cache_dir: Path | None = None) -> list[dict]:
    if cache_dir:
        key = cache_key(lat, lng, radius)
        cached = load_cache(cache_dir, key)
        if cached is not None:
            print(f"  [CACHE HIT] {len(cached)} places from cache")
            return cached

    all_results = []
    params = {
        "location": f"{lat},{lng}",
        "radius": radius,
        "type": "restaurant",
        "language": "vi",
        "key": api_key,
    }

    while True:
        resp = await client.get(NEARBY_URL, params=params)
        data = resp.json()
        status = data.get("status")

        if status == "ZERO_RESULTS":
            break
        if status not in ("OK", "ZERO_RESULTS"):
            print(f"  [API ERROR] {status}: {data.get('error_message', '')}")
            break

        all_results.extend(data.get("results", []))
        print(f"  Fetched {len(data.get('results', []))} (total: {len(all_results)})")

        next_token = data.get("next_page_token")
        if not next_token:
            break
        params = {"pagetoken": next_token, "key": api_key}
        await asyncio.sleep(2)

    if cache_dir and all_results:
        save_cache(cache_dir, cache_key(lat, lng, radius), all_results)

    return all_results


async def fetch_detail(client: httpx.AsyncClient, api_key: str,
                       place_id: str) -> dict | None:
    params = {
        "place_id": place_id,
        "fields": "formatted_phone_number,opening_hours,photos,price_level",
        "language": "vi",
        "key": api_key,
    }
    resp = await client.get(DETAIL_URL, params=params)
    data = resp.json()
    if data.get("status") != "OK":
        return None
    return data.get("result", {})


async def ingest_area(client: httpx.AsyncClient, api_key: str,
                      lat: float, lng: float, radius: int,
                      district_name: str | None,
                      cache_dir: Path | None):
    print(f"\n--- {district_name or f'({lat}, {lng})'} ---")
    raw_places = await fetch_nearby(client, api_key, lat, lng, radius, cache_dir)
    if not raw_places:
        print("  No places found.")
        return 0

    async with AsyncSessionLocal() as session:
        existing = await session.execute(
            text("SELECT google_place_id FROM places WHERE google_place_id IS NOT NULL")
        )
        known_ids = {row[0] for row in existing.fetchall()}

    new_places = [p for p in raw_places if p.get("place_id") not in known_ids]
    print(f"  {len(raw_places)} total, {len(new_places)} new")

    if not new_places:
        return 0

    async with AsyncSessionLocal() as session:
        dish_cache: dict[str, uuid.UUID] = {}
        existing_dishes = await session.execute(text("SELECT name, id FROM dishes"))
        for row in existing_dishes.fetchall():
            dish_cache[row[0]] = row[1]

        inserted = 0
        for raw in new_places:
            detail = await fetch_detail(client, api_key, raw["place_id"])
            await asyncio.sleep(0.3)

            location = raw.get("geometry", {}).get("location", {})
            p_lat = location.get("lat")
            p_lng = location.get("lng")
            if not p_lat or not p_lng:
                continue

            price_level = (detail or {}).get("price_level") or raw.get("price_level")
            price_min, price_max = PRICE_RANGES.get(price_level or 2, (50000, 200000))

            hours = None
            if detail and "opening_hours" in detail:
                hours = parse_hours(detail["opening_hours"].get("periods"))

            phone = (detail or {}).get("formatted_phone_number")

            place_id = uuid.uuid4()
            place = Place(
                id=place_id,
                name=raw.get("name", "Unknown"),
                address=raw.get("vicinity", ""),
                lat=p_lat,
                lng=p_lng,
                google_place_id=raw["place_id"],
                phone=phone,
                price_min=price_min,
                price_max=price_max,
                price_level=price_level,
                rating_google=raw.get("rating"),
                review_count=raw.get("user_ratings_total", 0),
                hours=hours,
                features={"vegetarian": "vegetarian_restaurant" in raw.get("types", [])},
                is_closed=raw.get("business_status") == "CLOSED_PERMANENTLY",
                district=district_name,
                image_urls=None,
                data_quality_score=0.7,
                created_at=datetime.utcnow(),
            )
            session.add(place)
            await session.flush()

            await session.execute(text(
                "UPDATE places SET geom = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326) WHERE id = :id"
            ), {"lng": p_lng, "lat": p_lat, "id": str(place_id)})

            dishes = detect_dishes(raw.get("name", ""))
            for dish_name in dishes:
                if dish_name not in dish_cache:
                    dish_id = uuid.uuid4()
                    dish = Dish(
                        id=dish_id,
                        name=dish_name,
                        name_normalized=normalize_text(dish_name),
                        category="Món Việt",
                    )
                    session.add(dish)
                    await session.flush()
                    dish_cache[dish_name] = dish_id

                pd = PlaceDish(
                    place_id=place_id,
                    dish_id=dish_cache[dish_name],
                    price=None,
                    is_available=True,
                )
                session.add(pd)

            inserted += 1
            if inserted % 10 == 0:
                await session.flush()

        await session.commit()
        print(f"  Inserted {inserted} new places")
        return inserted


async def run(api_key: str, areas: list[str] | None,
              lat: float | None, lng: float | None, radius: int,
              cache_dir: Path | None):

    total = 0
    async with httpx.AsyncClient(timeout=15) as client:
        if areas:
            for area_key in areas:
                area = AREAS.get(area_key)
                if not area:
                    print(f"[WARN] Unknown area '{area_key}'. Available: {', '.join(AREAS.keys())}")
                    continue
                n = await ingest_area(client, api_key, area["lat"], area["lng"],
                                      radius, area["name"], cache_dir)
                total += n
        else:
            district = None
            if lat and lng:
                for a in AREAS.values():
                    if abs(a["lat"] - lat) < 0.02 and abs(a["lng"] - lng) < 0.02:
                        district = a["name"]
                        break
            n = await ingest_area(client, api_key,
                                  lat or 10.7769, lng or 106.7009,
                                  radius, district, cache_dir)
            total += n

    print(f"\n[DONE] Total inserted: {total}")


def main():
    parser = argparse.ArgumentParser(description="Fetch Google Places into DB")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--areas", type=str, default=None,
                        help=f"Comma-separated areas: {','.join(AREAS.keys())}")
    parser.add_argument("--lat", type=float, default=None)
    parser.add_argument("--lng", type=float, default=None)
    parser.add_argument("--radius", type=int, default=1000)
    parser.add_argument("--cache-dir", type=str, default="data/google_cache")
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()

    area_list = args.areas.split(",") if args.areas else None
    cd = None if args.no_cache else Path(args.cache_dir)

    asyncio.run(run(args.api_key, area_list, args.lat, args.lng, args.radius, cd))


if __name__ == "__main__":
    main()
