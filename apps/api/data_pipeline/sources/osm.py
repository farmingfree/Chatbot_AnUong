"""OpenStreetMap Overpass API source - Free, stable, no auth required"""
import asyncio
import logging
from typing import AsyncIterator, Optional, List
import httpx
from .base import BaseSource, RawPlace


class OSMSource(BaseSource):
    """Fetch restaurant data from OpenStreetMap via Overpass API"""

    # HCM bounding box: [south, west, north, east]
    HCM_BBOX = (10.35, 106.35, 11.15, 107.05)

    OVERPASS_URL = "https://overpass-api.de/api/interpreter"

    # Overpass requires 10s between requests
    RATE_LIMIT = 10.0

    def __init__(self):
        self.source_name = "osm"
        self.logger = logging.getLogger(__name__)

    def _build_query(self, amenity_types: List[str]) -> str:
        """Build Overpass QL query for HCM restaurants"""
        south, west, north, east = self.HCM_BBOX
        
        # Build node queries for each amenity type
        node_queries = []
        for amenity in amenity_types:
            node_queries.append(
                f'node["amenity"="{amenity}"]({south},{west},{north},{east});'
            )
        
        query = f"""
        [out:json][timeout:120];
        (
          {chr(10).join('  ' + q for q in node_queries)}
        );
        out body center meta;
        """
        
        return query.strip()
    
    def _parse_osm_element(self, element: dict) -> Optional[RawPlace]:
        """Parse OSM element to RawPlace"""
        tags = element.get("tags", {})
        
        # Must have name
        name = tags.get("name")
        if not name:
            return None
        
        # Get coordinates
        lat = element.get("lat")
        lon = element.get("lon")
        if not lat or not lon:
            return None
        
        # Build address from OSM tags
        address_parts = []
        if addr_num := tags.get("addr:housenumber"):
            address_parts.append(addr_num)
        if addr_street := tags.get("addr:street"):
            address_parts.append(addr_street)
        if addr_district := tags.get("addr:district"):
            address_parts.append(addr_district)
        
        address = ", ".join(address_parts) if address_parts else tags.get("addr:full", "")
        
        # Determine district from address or tags
        district = None
        if addr_district := tags.get("addr:district"):
            district = addr_district
        elif "Quận" in address or "Huyện" in address:
            # Try to extract from address
            for part in address.split(","):
                part = part.strip()
                if part.startswith("Quận") or part.startswith("Huyện"):
                    district = part
                    break
        
        # Get cuisine/dishes from tags
        dishes = []
        if cuisine := tags.get("cuisine"):
            # OSM cuisine can be comma-separated
            dishes = [c.strip() for c in cuisine.split(";")]
        
        # Phone
        phone = tags.get("phone") or tags.get("contact:phone")
        
        # Opening hours
        opening_hours = tags.get("opening_hours")
        
        # Website
        website = tags.get("website") or tags.get("contact:website")
        
        # Features
        features = {
            "wifi": tags.get("internet_access") in ["yes", "wlan", "wifi"],
            "ac": tags.get("air_conditioning") == "yes",
            "outdoor_seating": tags.get("outdoor_seating") == "yes",
            "takeaway": tags.get("takeaway") == "yes",
            "delivery": tags.get("delivery") == "yes",
            "wheelchair": tags.get("wheelchair") == "yes",
        }
        
        # Parse opening hours to dict format
        hours = None
        if opening_hours:
            hours = {"raw": opening_hours}  # Store raw format for now

        return RawPlace(
            name=name,
            address=address or "Địa chỉ chưa rõ",
            lat=float(lat),
            lng=float(lon),
            district=district,
            phone=phone,
            price_min=None,  # OSM doesn't have price info
            price_max=None,
            price_level=None,
            rating=None,  # OSM doesn't have ratings
            review_count=None,
            hours=hours,
            features=features,
            dishes=dishes,
            image_urls=[],  # OSM doesn't have images
            source=self.source_name,
            source_id=str(element.get("id")),
            raw_data={
                "osm_type": element.get("type"),
                "osm_id": element.get("id"),
                "amenity": tags.get("amenity"),
                "opening_hours": opening_hours,
                "website": website,
                "tags": tags,
            }
        )
    
    def estimate_count(self, **kwargs) -> int:
        """Estimate number of places - OSM typically has 5000-8000 in HCM"""
        return 6000

    async def fetch(self, **kwargs) -> AsyncIterator[RawPlace]:
        """Fetch restaurants from OSM Overpass API"""
        max_results = kwargs.get("max_results")

        # Query for restaurants, cafes, and fast food
        amenity_types = ["restaurant", "cafe", "fast_food"]
        query = self._build_query(amenity_types)

        self.logger.info(f"Querying OSM Overpass API for HCM restaurants...")
        self.logger.info(f"Bounding box: {self.HCM_BBOX}")
        self.logger.info(f"Amenity types: {', '.join(amenity_types)}")

        async with httpx.AsyncClient(timeout=180.0) as client:
            try:
                response = await client.post(
                    self.OVERPASS_URL,
                    data={"data": query},
                    headers={
                        "User-Agent": "FoodAdvisor/1.0 (Data Collection)",
                        "Accept": "application/json",
                    }
                )
                response.raise_for_status()

                data = response.json()
                elements = data.get("elements", [])

                self.logger.info(f"Received {len(elements)} elements from OSM")

                # Parse and yield elements one by one
                count = 0
                for element in elements:
                    if place := self._parse_osm_element(element):
                        yield place
                        count += 1

                        if max_results and count >= max_results:
                            break

                self.logger.info(f"Yielded {count} valid places")

                # Respect rate limit for next request
                await asyncio.sleep(self.RATE_LIMIT)

            except httpx.HTTPError as e:
                self.logger.error(f"HTTP error querying Overpass API: {e}")
            except Exception as e:
                self.logger.error(f"Error fetching from OSM: {e}")
                import traceback
                traceback.print_exc()
