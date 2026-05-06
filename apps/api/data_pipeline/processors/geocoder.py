"""Geocoder using Nominatim (OpenStreetMap) - 100% FREE"""
import asyncio
import httpx


class Geocoder:
    """Free geocoding using Nominatim (OSM)"""
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

    def __init__(self):
        self.cache: dict[str, tuple[float, float]] = {}

    async def geocode(self, address: str, district: str | None = None) -> tuple[float, float] | None:
        """Convert địa chỉ → lat/lng using Nominatim (OSM), completely free"""
        
        # Build query
        query = address
        if district and district not in address:
            query = f"{address}, {district}, Thành phố Hồ Chí Minh, Vietnam"
        elif "HCM" not in address and "Hồ Chí Minh" not in address:
            query = f"{address}, Thành phố Hồ Chí Minh, Vietnam"

        # Check cache
        if query in self.cache:
            return self.cache[query]

        # Query Nominatim
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(
                    self.NOMINATIM_URL,
                    params={
                        "q": query,
                        "format": "json",
                        "limit": 1,
                        "countrycodes": "vn"
                    },
                    headers={"User-Agent": "FoodAdvisorApp/1.0 (contact@foodadvisor.vn)"}
                )
                results = resp.json()

                if results:
                    lat = float(results[0]["lat"])
                    lng = float(results[0]["lon"])
                    self.cache[query] = (lat, lng)
                    await asyncio.sleep(1.1)  # Nominatim rate limit: 1 req/s
                    return (lat, lng)

            except Exception as e:
                print(f"⚠️  Geocode error for '{query}': {e}")

        return None

    async def geocode_batch(self, addresses: list[tuple[str, str | None]]) -> list[tuple[float, float] | None]:
        """Geocode multiple addresses with rate limiting"""
        results = []
        for address, district in addresses:
            result = await self.geocode(address, district)
            results.append(result)
        return results
