import asyncio
import json
from pathlib import Path
from datetime import datetime
from uuid import uuid4
from sqlalchemy import text, select
from app.database import AsyncSessionLocal
from app.models import Place, Dish, PlaceDish


async def load_static_data():
    """Load places from JSON file"""
    json_path = Path(__file__).parent / "data" / "places_hcm.json"
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


async def seed_static_places():
    """Seed database with static place data"""
    print("🌱 Loading static data from JSON...")
    places_data = await load_static_data()
    print(f"   Found {len(places_data)} places in JSON")
    
    async with AsyncSessionLocal() as session:
        # Collect all unique dishes
        all_dishes = set()
        for place_data in places_data:
            all_dishes.update(place_data.get("dishes", []))
        
        print(f"\n📝 Creating {len(all_dishes)} unique dishes...")
        dish_map = {}  # dish_name -> dish_id
        
        for dish_name in all_dishes:
            # Check if dish already exists
            result = await session.execute(
                select(Dish).where(Dish.name == dish_name)
            )
            existing_dish = result.scalar_one_or_none()
            
            if existing_dish:
                dish_map[dish_name] = existing_dish.id
            else:
                dish = Dish(
                    id=uuid4(),
                    name=dish_name,
                    name_normalized=dish_name.lower(),
                    category="Món Việt" if any(k in dish_name.lower() for k in ["phở", "bún", "cơm", "bánh", "cháo", "xôi", "hủ tiếu"]) else "Khác",
                    created_at=datetime.utcnow(),
                )
                session.add(dish)
                dish_map[dish_name] = dish.id
        
        await session.commit()
        print(f"   ✅ Created/found {len(dish_map)} dishes")
        
        # Insert places
        print(f"\n🏪 Inserting {len(places_data)} places...")
        place_count = 0
        relationship_count = 0
        
        for place_data in places_data:
            # Check if place already exists
            google_place_id = place_data.get("google_place_id")
            result = await session.execute(
                select(Place).where(Place.google_place_id == google_place_id)
            )
            existing_place = result.scalar_one_or_none()
            
            if existing_place:
                print(f"   ⏭️  Skipping existing place: {place_data['name']}")
                continue
            
            # Extract dishes before creating place
            dishes = place_data.pop("dishes", [])
            
            # Create place
            place = Place(
                id=uuid4(),
                name=place_data["name"],
                address=place_data["address"],
                lat=place_data["lat"],
                lng=place_data["lng"],
                phone=place_data.get("phone"),
                google_place_id=google_place_id,
                price_min=place_data.get("price_min"),
                price_max=place_data.get("price_max"),
                price_level=place_data.get("price_level"),
                rating_google=place_data.get("rating_google"),
                review_count=place_data.get("review_count", 0),
                hours=place_data.get("hours"),
                features=place_data.get("features"),
                is_closed=False,
                image_urls=place_data.get("image_urls", []),
                district=place_data["district"],
                last_crawled_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            
            session.add(place)
            await session.flush()
            
            # Set geom using PostGIS
            await session.execute(
                text("UPDATE places SET geom = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326) WHERE id = :id"),
                {"lng": place.lng, "lat": place.lat, "id": str(place.id)}
            )
            
            # Link dishes
            for dish_name in dishes:
                if dish_name in dish_map:
                    # Check if relationship exists
                    result = await session.execute(
                        select(PlaceDish).where(
                            PlaceDish.place_id == place.id,
                            PlaceDish.dish_id == dish_map[dish_name]
                        )
                    )
                    if not result.scalar_one_or_none():
                        place_dish = PlaceDish(
                            place_id=place.id,
                            dish_id=dish_map[dish_name],
                            is_available=True,
                            updated_at=datetime.utcnow(),
                        )
                        session.add(place_dish)
                        relationship_count += 1
            
            place_count += 1
            
            if place_count % 10 == 0:
                await session.commit()
                print(f"   Inserted {place_count}/{len(places_data)} places...")
        
        await session.commit()
        
        print(f"\n✅ Seeding complete!")
        print(f"   📊 Summary:")
        print(f"      - Places: {place_count}")
        print(f"      - Dishes: {len(dish_map)}")
        print(f"      - Relationships: {relationship_count}")


if __name__ == "__main__":
    asyncio.run(seed_static_places())
