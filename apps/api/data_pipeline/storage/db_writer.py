"""Database writer for places"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from geoalchemy2.functions import ST_SetSRID, ST_MakePoint
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
from app.models.place import Place
from app.models.dish import Dish
from app.models.place_dish import PlaceDish
from ..sources.base import RawPlace
from ..processors.normalizer import normalize_text


class DBWriter:
    """Write places to database"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def upsert_place(self, raw: RawPlace) -> tuple[int, bool]:
        """
        Insert or update place in database.
        Returns (place_id, is_new)
        """
        # Check if exists by source_id
        existing_id = None
        if raw.source_id:
            from sqlalchemy import cast, String
            result = await self.db.execute(
                select(Place.id).where(
                    cast(Place.source_data['source_id'], String) == f'"{raw.source_id}"',
                    cast(Place.source_data['source'], String) == f'"{raw.source}"'
                )
            )
            row = result.first()
            if row:
                existing_id = row[0]

        # Prepare data
        geom = None
        if raw.lat and raw.lng:
            geom = ST_SetSRID(ST_MakePoint(raw.lng, raw.lat), 4326)

        place_data = {
            "name": raw.name,
            "name_normalized": normalize_text(raw.name),
            "address": raw.address,
            "district": raw.district,
            "lat": raw.lat,
            "lng": raw.lng,
            "geom": geom,
            "phone": raw.phone,
            "price_min": raw.price_min,
            "price_max": raw.price_max,
            "price_level": raw.price_level,
            "rating_google": raw.rating,
            "review_count": raw.review_count,
            "hours": raw.hours,
            "features": raw.features or {},
            "image_urls": raw.image_urls,
            "source_data": {
                "source": raw.source,
                "source_id": raw.source_id,
                "raw": raw.raw_data
            }
        }

        if existing_id:
            # Update existing
            await self.db.execute(
                Place.__table__.update().where(Place.id == existing_id).values(**place_data)
            )
            place_id = existing_id
            is_new = False
        else:
            # Insert new
            place = Place(**place_data)
            self.db.add(place)
            await self.db.flush()
            place_id = place.id
            is_new = True

        # Handle dishes
        if raw.dishes:
            await self._link_dishes(place_id, raw.dishes)

        await self.db.commit()
        return place_id, is_new

    async def _link_dishes(self, place_id: int, dish_names: list[str]):
        """Link dishes to place"""
        for dish_name in dish_names:
            # Get or create dish
            result = await self.db.execute(
                select(Dish.id).where(Dish.name == dish_name)
            )
            row = result.first()
            
            if row:
                dish_id = row[0]
            else:
                dish = Dish(name=dish_name, name_normalized=normalize_text(dish_name))
                self.db.add(dish)
                await self.db.flush()
                dish_id = dish.id

            # Link place-dish (if not exists)
            result = await self.db.execute(
                select(PlaceDish).where(
                    PlaceDish.place_id == place_id,
                    PlaceDish.dish_id == dish_id
                )
            )
            if not result.first():
                place_dish = PlaceDish(place_id=place_id, dish_id=dish_id)
                self.db.add(place_dish)
