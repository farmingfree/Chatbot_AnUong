"""Deduplication logic"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..sources.base import RawPlace
from .normalizer import normalize_text, similarity_score
import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
from app.models.place import Place


class Deduplicator:
    """Check for duplicate places in database"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def is_duplicate(self, place: RawPlace) -> str | None:
        """
        Check if place already exists in DB.
        Returns place_id if duplicate found, None otherwise.
        
        Check priority:
        1. source_id match (most reliable)
        2. Name + district similarity > 90%
        3. Lat/lng within 50m
        """
        
        # Check 1: source_id match
        if place.source_id:
            result = await self.db.execute(
                select(Place.id).where(
                    Place.source_data['source_id'].astext == place.source_id,
                    Place.source_data['source'].astext == place.source
                )
            )
            row = result.first()
            if row:
                return str(row[0])

        # Check 2: Name + district similarity
        if place.name and place.district:
            name_norm = normalize_text(place.name)
            result = await self.db.execute(
                select(Place.id, Place.name).where(
                    Place.district == place.district
                )
            )
            for row in result:
                if similarity_score(place.name, row[1]) > 0.9:
                    return str(row[0])

        # Check 3: Geo proximity (if has coordinates)
        if place.lat and place.lng:
            # Use ST_DWithin to find places within 50m
            result = await self.db.execute(
                select(Place.id).where(
                    func.ST_DWithin(
                        Place.geom,
                        func.ST_SetSRID(func.ST_MakePoint(place.lng, place.lat), 4326),
                        0.0005  # ~50m in degrees
                    )
                )
            )
            row = result.first()
            if row:
                return str(row[0])

        return None

    async def find_all_duplicates(self) -> list[tuple[int, int, float]]:
        """
        Find all potential duplicates in database.
        Returns list of (place_id1, place_id2, similarity_score)
        """
        duplicates = []
        
        # Get all places
        result = await self.db.execute(
            select(Place.id, Place.name, Place.district, Place.lat, Place.lng)
        )
        places = result.all()
        
        # Compare each pair
        for i, p1 in enumerate(places):
            for p2 in places[i+1:]:
                # Same district + high name similarity
                if p1[2] == p2[2]:  # same district
                    sim = similarity_score(p1[1], p2[1])
                    if sim > 0.85:
                        duplicates.append((p1[0], p2[0], sim))
                        continue
                
                # Close geo proximity
                if p1[3] and p1[4] and p2[3] and p2[4]:
                    dist = self._haversine_distance(p1[3], p1[4], p2[3], p2[4])
                    if dist < 50:  # within 50m
                        duplicates.append((p1[0], p2[0], 1.0))
        
        return duplicates

    def _haversine_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance in meters between two coordinates"""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371000  # Earth radius in meters
        
        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
