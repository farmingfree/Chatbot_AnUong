"""ShopeeFood API scraper - FREE internal API"""
import asyncio
import httpx
from typing import AsyncIterator
from .base import BaseSource, RawPlace


class ShopeeFoodSource(BaseSource):
    source_name = "shopee_food"

    # ShopeeFood internal API (from browser network inspection)
    API_URL = "https://gappapi.deliverynow.vn/api/delivery/get_detail_restaurant_list"

    # HCM city_id = 217
    DISTRICT_IDS = {
        "Quận 1": 1452, "Quận 3": 1454, "Quận 5": 1456,
        "Bình Thạnh": 1472, "Tân Bình": 1480, "Quận 7": 1458,
        "Quận 10": 1461, "Phú Nhuận": 1477, "Gò Vấp": 1469,
        "Thủ Đức": 1483
    }

    HEADERS = {
        "User-Agent": "Mozilla/5.0",
        "x-foody-client-id": "",
        "x-foody-client-language": "vi",
        "x-foody-client-type": "1",
        "x-foody-client-version": "3",
        "Referer": "https://shopeefood.vn/"
    }

    async def fetch(self, max_per_district: int = 200, **kwargs) -> AsyncIterator[RawPlace]:
        """Fetch places from ShopeeFood API"""
        async with httpx.AsyncClient(headers=self.HEADERS, timeout=15.0) as client:
            for district_name, district_id in self.DISTRICT_IDS.items():
                page = 0
                fetched = 0

                while fetched < max_per_district:
                    params = {
                        "category_id": 1,
                        "district_id": district_id,
                        "city_id": 217,
                        "start": page * 20,
                        "count": 20,
                        "sort_type": 0
                    }

                    try:
                        resp = await client.get(self.API_URL, params=params)
                        data = resp.json()

                        restaurants = data.get("reply", {}).get("delivery_detail_list", [])
                        if not restaurants:
                            break

                        for r in restaurants:
                            yield self._normalize(r, district_name)
                            fetched += 1

                        page += 1
                        await asyncio.sleep(1)

                    except Exception as e:
                        print(f"⚠️  ShopeeFood error district {district_name}: {e}")
                        await asyncio.sleep(3)
                        break

    def _normalize(self, r: dict, district: str) -> RawPlace:
        """Convert ShopeeFood data to RawPlace"""
        # Photos
        photos = [p.get("value", "") for p in r.get("photos", [])[:3]]

        # Price range (ShopeeFood uses 1000đ units)
        price_min_raw = r.get("price_range", {}).get("min_price", 0)
        price_max_raw = r.get("price_range", {}).get("max_price", 0)
        price_min = price_min_raw * 1000 if price_min_raw else None
        price_max = price_max_raw * 1000 if price_max_raw else None

        # Dishes from categories
        dishes = [cat.get("name", "") for cat in r.get("categories", [])[:5]]

        return RawPlace(
            name=r.get("name", ""),
            address=r.get("address", ""),
            lat=r.get("lat"),
            lng=r.get("lng"),
            district=district,
            phone=None,
            price_min=price_min,
            price_max=price_max,
            price_level=RawPlace._price_to_level(price_min, price_max),
            rating=r.get("rating", {}).get("avg"),
            review_count=r.get("rating", {}).get("count"),
            hours=None,
            features={
                "vegetarian": any("chay" in c.get("name", "").lower() for c in r.get("categories", [])),
                "delivery": True
            },
            dishes=[d for d in dishes if d],
            image_urls=photos,
            source="shopee_food",
            source_id=str(r.get("delivery_id")),
            raw_data=r
        )

    def estimate_count(self, max_per_district=200, **kwargs) -> int:
        return len(self.DISTRICT_IDS) * max_per_district
