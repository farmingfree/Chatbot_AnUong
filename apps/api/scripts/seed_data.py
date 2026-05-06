import asyncio
import argparse
import time
from datetime import datetime
from uuid import uuid4
import httpx
from sqlalchemy import select, text
from geoalchemy2.functions import ST_SetSRID, ST_MakePoint
from app.database import engine, AsyncSessionLocal
from app.models import Place, Dish, PlaceDish


# 15 điểm tìm kiếm tại HCM
SEARCH_POINTS = [
    (10.7769, 106.7009, "Quận 1"),
    (10.7731, 106.6946, "Quận 1"),
    (10.7758, 106.7054, "Quận 1"),
    (10.7836, 106.6885, "Quận 3"),
    (10.7802, 106.6921, "Quận 3"),
    (10.8037, 106.7131, "Bình Thạnh"),
    (10.8124, 106.7089, "Bình Thạnh"),
    (10.7392, 106.7216, "Quận 7"),
    (10.7361, 106.7273, "Quận 7"),
    (10.8017, 106.6587, "Tân Bình"),
    (10.7989, 106.6632, "Tân Bình"),
    (10.8381, 106.6818, "Gò Vấp"),
    (10.8533, 106.7553, "Thủ Đức"),
    (10.7745, 106.6668, "Quận 10"),
    (10.7998, 106.6847, "Phú Nhuận"),
]

DISH_KEYWORDS = {
    "bún bò": "Bún bò Huế",
    "phở": "Phở",
    "cơm tấm": "Cơm tấm",
    "bánh mì": "Bánh mì",
    "bún đậu": "Bún đậu mắm tôm",
    "hủ tiếu": "Hủ tiếu",
    "cháo": "Cháo",
    "bánh cuốn": "Bánh cuốn",
    "xôi": "Xôi",
    "bún riêu": "Bún riêu",
    "lẩu": "Lẩu",
    "nướng": "Đồ nướng",
    "chay": "Đồ chay",
    "pizza": "Pizza",
    "burger": "Burger",
    "sushi": "Sushi",
}

PRICE_RANGES = {
    1: (15000, 50000),
    2: (50000, 150000),
    3: (150000, 350000),
    4: (350000, 999000),
}


async def fetch_places_from_google(lat: float, lng: float, radius: int, api_key: str):
    """Fetch places from Google Places API with pagination"""
    places = []
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    
    params = {
        "location": f"{lat},{lng}",
        "radius": radius,
        "type": "restaurant|food",
        "language": "vi",
        "key": api_key,
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            response = await client.get(url, params=params)
            data = response.json()
            
            if data.get("status") != "OK":
                break
                
            places.extend(data.get("results", []))
            
            next_page_token = data.get("next_page_token")
            if not next_page_token:
                break
                
            # Wait for token to become valid
            await asyncio.sleep(2)
            params = {"pagetoken": next_page_token, "key": api_key}
    
    return places


async def enrich_place_detail(place_id: str, api_key: str):
    """Fetch detailed place info from Google Places Details API"""
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "formatted_phone_number,opening_hours,website,photos",
        "language": "vi",
        "key": api_key,
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        data = response.json()
        
        if data.get("status") == "OK":
            return data.get("result", {})
    
    return {}


def detect_dishes_from_name(place_name: str) -> list[str]:
    """Detect dishes from place name using keyword matching"""
    dishes = []
    name_lower = place_name.lower()
    
    for keyword, dish_name in DISH_KEYWORDS.items():
        if keyword in name_lower:
            dishes.append(dish_name)
    
    return dishes


def normalize_place(raw_data: dict, district_name: str, details: dict = None) -> dict:
    """Map Google Place data to app schema"""
    geometry = raw_data.get("geometry", {})
    location = geometry.get("location", {})
    
    price_level = raw_data.get("price_level", 2)
    price_min, price_max = PRICE_RANGES.get(price_level, (50000, 150000))
    
    # Parse opening hours
    hours = None
    if details and "opening_hours" in details:
        periods = details["opening_hours"].get("periods", [])
        hours = {}
        day_map = {0: "sun", 1: "mon", 2: "tue", 3: "wed", 4: "thu", 5: "fri", 6: "sat"}
        for period in periods:
            day = period.get("open", {}).get("day")
            if day is not None:
                open_time = period.get("open", {}).get("time", "0000")
                close_time = period.get("close", {}).get("time", "2359")
                hours[day_map[day]] = f"{open_time[:2]}:{open_time[2:]}-{close_time[:2]}:{close_time[2:]}"
    
    # Detect features from types
    types = raw_data.get("types", [])
    features = {
        "ac": True,
        "wifi": False,
        "parking": "parking" in types,
        "vegetarian": "vegetarian_restaurant" in types,
        "halal": False,
    }
    
    # Build image URLs
    image_urls = []
    if details and "photos" in details:
        for photo in details["photos"][:3]:
            photo_ref = photo.get("photo_reference")
            if photo_ref:
                image_urls.append(
                    f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photo_reference={photo_ref}&key=YOUR_KEY"
                )
    
    return {
        "name": raw_data.get("name", ""),
        "address": raw_data.get("vicinity", ""),
        "lat": location.get("lat", 0),
        "lng": location.get("lng", 0),
        "phone": details.get("formatted_phone_number") if details else None,
        "google_place_id": raw_data.get("place_id"),
        "price_min": price_min,
        "price_max": price_max,
        "price_level": price_level,
        "rating_google": raw_data.get("rating"),
        "review_count": raw_data.get("user_ratings_total", 0),
        "hours": hours,
        "features": features,
        "is_closed": raw_data.get("business_status") == "CLOSED_PERMANENTLY",
        "image_urls": image_urls,
        "district": district_name,
        "last_crawled_at": datetime.utcnow(),
    }


async def main(api_key: str, limit: int = 200):
    """Main seeding function"""
    print(f"🌱 Starting seed process for {limit} places...")
    
    all_places = {}  # Dedup by google_place_id
    processed_count = 0
    
    # Fetch places from all search points
    for lat, lng, district in SEARCH_POINTS:
        if processed_count >= limit:
            break
            
        print(f"\n📍 Searching near {district} ({lat}, {lng})...")
        raw_places = await fetch_places_from_google(lat, lng, 500, api_key)
        
        for raw_place in raw_places:
            if processed_count >= limit:
                break
                
            place_id = raw_place.get("place_id")
            if not place_id or place_id in all_places:
                continue
            
            # Enrich with details (rate limited - be careful)
            details = await enrich_place_detail(place_id, api_key)
            await asyncio.sleep(0.5)  # Rate limit protection
            
            # Normalize place data
            normalized = normalize_place(raw_place, district, details)
            normalized["detected_dishes"] = detect_dishes_from_name(normalized["name"])
            
            all_places[place_id] = normalized
            processed_count += 1
            
            if processed_count % 10 == 0:
                print(f"   Processed {processed_count}/{limit} places...")
    
    print(f"\n✅ Fetched {len(all_places)} unique places")
    
    # Insert into database
    print("\n💾 Inserting into database...")
    async with AsyncSessionLocal() as session:
        # Create dishes first
        dish_map = {}  # dish_name -> dish_id
        all_dish_names = set()
        for place_data in all_places.values():
            all_dish_names.update(place_data.get("detected_dishes", []))
        
        for dish_name in all_dish_names:
            dish = Dish(
                id=uuid4(),
                name=dish_name,
                name_normalized=dish_name.lower(),
                category="Món Việt",
            )
            session.add(dish)
            dish_map[dish_name] = dish.id
        
        await session.commit()
        print(f"   Created {len(dish_map)} dishes")
        
        # Insert places
        place_count = 0
        for place_data in all_places.values():
            detected_dishes = place_data.pop("detected_dishes", [])
            
            place = Place(
                id=uuid4(),
                **place_data
            )
            
            # Set geom from lat/lng
            stmt = text(
                "UPDATE places SET geom = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326) WHERE id = :id"
            )
            
            session.add(place)
            await session.flush()
            
            await session.execute(
                stmt,
                {"lng": place.lng, "lat": place.lat, "id": str(place.id)}
            )
            
            # Link dishes
            for dish_name in detected_dishes:
                if dish_name in dish_map:
                    place_dish = PlaceDish(
                        place_id=place.id,
                        dish_id=dish_map[dish_name],
                        is_available=True,
                    )
                    session.add(place_dish)
            
            place_count += 1
            if place_count % 20 == 0:
                await session.commit()
                print(f"   Inserted {place_count}/{len(all_places)} places...")
        
        await session.commit()
        print(f"\n✅ Successfully seeded {place_count} places!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed database with HCM restaurants")
    parser.add_argument("--api-key", required=True, help="Google Maps API key")
    parser.add_argument("--limit", type=int, default=200, help="Max places to fetch")
    
    args = parser.parse_args()
    asyncio.run(main(args.api_key, args.limit))
