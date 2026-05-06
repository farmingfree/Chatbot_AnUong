"""Foody.vn scraper - FREE web scraping"""
import asyncio
import httpx
import re
from typing import AsyncIterator
from bs4 import BeautifulSoup
from .base import BaseSource, RawPlace


class FoodySource(BaseSource):
    source_name = "foody"
    BASE_URL = "https://www.foody.vn"

    # Các category slugs trên Foody HCM
    CATEGORIES = [
        "quan-an", "nha-hang", "cafe", "banh-mi",
        "bun-pho", "com-chien", "do-chay", "do-uong"
    ]

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept-Language": "vi-VN,vi;q=0.9",
        "Referer": "https://www.foody.vn/"
    }

    async def fetch(self, max_pages: int = 50, **kwargs) -> AsyncIterator[RawPlace]:
        """Scrape places from Foody.vn"""
        async with httpx.AsyncClient(headers=self.HEADERS, follow_redirects=True, timeout=15.0) as client:
            for category in self.CATEGORIES:
                for page in range(1, max_pages + 1):
                    url = f"{self.BASE_URL}/ho-chi-minh/{category}?page={page}"

                    try:
                        resp = await client.get(url)
                        if resp.status_code == 404:
                            break

                        soup = BeautifulSoup(resp.text, "html.parser")
                        place_cards = soup.select(".item-restaurant, .item-food")

                        if not place_cards:
                            break

                        for card in place_cards:
                            link = card.select_one("a")
                            if not link or not link.get("href"):
                                continue
                            
                            detail_url = self.BASE_URL + link["href"]
                            detail = await self._fetch_detail(client, detail_url)
                            if detail:
                                yield detail
                            await asyncio.sleep(1.5)

                    except Exception as e:
                        print(f"⚠️  Foody error {url}: {e}")
                        await asyncio.sleep(5)
                        continue

    async def _fetch_detail(self, client: httpx.AsyncClient, url: str) -> RawPlace | None:
        """Fetch and parse place detail page"""
        try:
            resp = await client.get(url, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")

            # Parse fields
            name_el = soup.select_one("h1.res-name, h1.restaurant-name")
            name = name_el.text.strip() if name_el else None
            if not name:
                return None

            address_el = soup.select_one(".address-item span, .res-address")
            address = address_el.text.strip() if address_el else None

            rating_el = soup.select_one(".point-number, .microsite-point")
            rating = float(rating_el.text) if rating_el and rating_el.text.strip() else None

            price_el = soup.select_one(".price-range, .res-price")
            price_min, price_max = self._parse_price(price_el.text if price_el else "")

            # Images
            images = []
            for img in soup.select(".restaurant-photo img, .microsite-top-image img")[:3]:
                src = img.get("src") or img.get("data-src")
                if src:
                    images.append(src)

            # Dishes from menu
            dishes = []
            for d in soup.select(".menu-item-name, .fd-name")[:10]:
                dish_name = d.text.strip()
                if dish_name:
                    dishes.append(dish_name)

            # District
            district = self._extract_district(address or "")

            # Phone
            phone_el = soup.select_one(".phone-number, .res-phone")
            phone = phone_el.text.strip() if phone_el else None

            return RawPlace(
                name=name,
                address=address,
                lat=None,  # Will geocode later
                lng=None,
                district=district,
                phone=phone,
                price_min=price_min,
                price_max=price_max,
                price_level=RawPlace._price_to_level(price_min, price_max),
                rating=rating,
                review_count=None,
                hours=None,
                features={"vegetarian": "chay" in name.lower()},
                dishes=dishes,
                image_urls=images,
                source="foody",
                source_id=url.split("/")[-1],
                raw_data={"url": url}
            )
        except Exception as e:
            print(f"⚠️  Parse error {url}: {e}")
            return None

    def _parse_price(self, text: str) -> tuple[int | None, int | None]:
        """Extract price range from text like '50.000đ - 150.000đ'"""
        nums = re.findall(r"[\d\.]+", text.replace(".", ""))
        if len(nums) >= 2:
            return int(nums[0]), int(nums[1])
        elif len(nums) == 1:
            val = int(nums[0])
            return val, val
        return None, None

    def _extract_district(self, address: str) -> str | None:
        """Extract district from address"""
        match = re.search(
            r"Quận\s+\d+|Quận\s+\w+|Bình Thạnh|Tân Bình|Gò Vấp|Phú Nhuận|Thủ Đức|Tân Phú|Bình Tân",
            address
        )
        return match.group(0) if match else None

    def estimate_count(self, max_pages=50, **kwargs) -> int:
        return len(self.CATEGORIES) * max_pages * 15
