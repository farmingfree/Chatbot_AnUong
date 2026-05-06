"""Google Maps Places API source - FREE $200/month credit"""
import asyncio
import httpx
from typing import AsyncIterator
from .base import BaseSource, RawPlace


class GoogleMapsSource(BaseSource):
    source_name = "google_maps"

    # 15 điểm grid covering HCM — đủ để crawl ~3000+ quán unique
    SEARCH_POINTS = [
        {"lat": 10.7769, "lng": 106.7009, "district": "Quận 1"},
        {"lat": 10.7731, "lng": 106.6946, "district": "Quận 1"},
        {"lat": 10.7836, "lng": 106.6885, "district": "Quận 3"},
        {"lat": 10.8037, "lng": 106.7131, "district": "Bình Thạnh"},
        {"lat": 10.7392, "lng": 106.7216, "district": "Quận 7"},
        {"lat": 10.8017, "lng": 106.6587, "district": "Tân Bình"},
        {"lat": 10.8381, "lng": 106.6818, "district": "Gò Vấp"},
        {"lat": 10.7745, "lng": 106.6668, "district": "Quận 10"},
        {"lat": 10.7998, "lng": 106.6847, "district": "Phú Nhuận"},
        {"lat": 10.8533, "lng": 106.7553, "district": "Thủ Đức"},
        {"lat": 10.7550, "lng": 106.6825, "district": "Quận 5"},
        {"lat": 10.7628, "lng": 106.6601, "district": "Quận 6"},
        {"lat": 10.7326, "lng": 106.6996, "district": "Quận 4"},
        {"lat": 10.7589, "lng": 106.7399, "district": "Quận 2"},
        {"lat": 10.8251, "lng": 106.6298, "district": "Tân Phú"},
    ]

    TYPES = ["restaurant", "cafe", "food", "bakery"]

    async def fetch(self, api_key: str, radius: int = 500, **kwargs) -> AsyncIterator[RawPlace]:
        """Fetch places from Google Maps API"""
        seen_ids = set()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for point in self.SEARCH_POINTS:
                for place_type in self.TYPES:
                    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
                    params = {
                        "location": f"{point['lat']},{point['lng']}",
                        "radius": radius,
                        "type": place_type,
                        "language": "vi",
                        "key": api_key
                    }

                    while True:
                        try:
                            resp = await client.get(url, params=params)
                            data = resp.json()

                            if data.get("status") == "OVER_QUERY_LIMIT":
                                print(f"⚠️  API quota exceeded")
                                return

                            for place in data.get("results", []):
                                place_id = place.get("place_id")
                                if place_id in seen_ids:
                                    continue
                                seen_ids.add(place_id)

                                # Fetch details để lấy phone + hours
                                detail = await self._fetch_detail(client, place_id, api_key)
                                yield self._normalize(place, detail, point["district"])
                                await asyncio.sleep(0.3)

                            # Pagination
                            next_token = data.get("next_page_token")
                            if not next_token:
                                break
                            await asyncio.sleep(2)  # Google requires delay
                            params = {"pagetoken": next_token, "key": api_key}

                        except Exception as e:
                            print(f"⚠️  Error fetching {place_type} at {point['district']}: {e}")
                            break

    async def _fetch_detail(self, client: httpx.AsyncClient, place_id: str, api_key: str) -> dict:
        """Fetch place details"""
        fields = "formatted_phone_number,opening_hours,photos,price_level,website"
        try:
            resp = await client.get(
                "https://maps.googleapis.com/maps/api/place/details/json",
                params={"place_id": place_id, "fields": fields, "language": "vi", "key": api_key}
            )
            return resp.json().get("result", {})
        except:
            return {}

    def _normalize(self, place: dict, detail: dict, district: str) -> RawPlace:
        """Convert Google Maps data to RawPlace"""
        # Parse hours
        hours = {}
        if "opening_hours" in detail:
            day_names = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]
            for period in detail["opening_hours"].get("periods", []):
                if "open" not in period:
                    continue
                day = day_names[period["open"]["day"]]
                open_t = period["open"]["time"]
                close_t = period.get("close", {}).get("time", "2359")
                hours[day] = f"{open_t[:2]}:{open_t[2:]}-{close_t[:2]}:{close_t[2:]}"

        # Image URLs
        image_urls = []
        for photo in detail.get("photos", [])[:3]:
            ref = photo.get("photo_reference")
            if ref:
                image_urls.append(
                    f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={ref}&key=PLACEHOLDER"
                )

        # Price level to range
        price_level = detail.get("price_level") or place.get("price_level")
        price_ranges = {
            1: (15000, 50000),
            2: (50000, 150000),
            3: (150000, 350000),
            4: (350000, 999000)
        }
        price_min, price_max = price_ranges.get(price_level, (None, None))

        return RawPlace(
            name=place.get("name", ""),
            address=place.get("vicinity", ""),
            lat=place["geometry"]["location"]["lat"],
            lng=place["geometry"]["location"]["lng"],
            district=district,
            phone=detail.get("formatted_phone_number"),
            price_min=price_min,
            price_max=price_max,
            price_level=price_level,
            rating=place.get("rating"),
            review_count=place.get("user_ratings_total"),
            hours=hours if hours else None,
            features={
                "vegetarian": "vegetarian_restaurant" in place.get("types", []),
                "ac": None,
                "wifi": None,
                "parking": None,
                "halal": False
            },
            dishes=self._detect_dishes(place.get("name", "")),
            image_urls=image_urls,
            source="google_maps",
            source_id=place.get("place_id"),
            raw_data=place
        )

    def _detect_dishes(self, name: str) -> list[str]:
        """Detect dishes from place name"""
        DISH_MAP = {
            "phở": "Phở", "pho": "Phở", "bún bò": "Bún bò Huế",
            "cơm tấm": "Cơm tấm", "bánh mì": "Bánh mì",
            "bún đậu": "Bún đậu mắm tôm", "hủ tiếu": "Hủ tiếu",
            "cháo": "Cháo", "xôi": "Xôi", "bún riêu": "Bún riêu",
            "bún thịt nướng": "Bún thịt nướng", "lẩu": "Lẩu",
            "nướng": "Đồ nướng", "chay": "Đồ chay",
            "bánh cuốn": "Bánh cuốn", "pizza": "Pizza",
            "burger": "Burger", "sushi": "Sushi", "ramen": "Ramen",
            "kem": "Kem", "chè": "Chè"
        }
        name_lower = name.lower()
        return list({v for k, v in DISH_MAP.items() if k in name_lower})

    def estimate_count(self, **kwargs) -> int:
        return len(self.SEARCH_POINTS) * len(self.TYPES) * 20
