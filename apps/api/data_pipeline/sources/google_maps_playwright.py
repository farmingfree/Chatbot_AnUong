"""Google Maps crawler using Playwright (no API key required)"""
import asyncio
import json
import logging
import re
from typing import AsyncIterator
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from ..sources.base import BaseSource, RawPlace
from ..utils.retry import retry_async, RetryConfig
from ..utils.stealth import StealthBrowser, random_delay, human_scroll
from ..utils.checkpoint import Checkpoint

logger = logging.getLogger(__name__)


class GoogleMapsPlaywrightSource(BaseSource):
    """Scrape Google Maps directly via browser automation"""

    source_name = "google_maps_playwright"

    def __init__(self):
        self.checkpoint = Checkpoint()
        self.seen_place_ids = set()

    async def fetch(self, query: str, max_results: int = 100, resume: bool = True, **kwargs) -> AsyncIterator[RawPlace]:
        """
        Fetch places from Google Maps search.

        Args:
            query: Search query (e.g., "pho district 1 hcm", "coffee shop thao dien")
            max_results: Maximum number of places to fetch
            resume: Whether to resume from checkpoint
        """
        checkpoint_key = f"gmaps_{query.replace(' ', '_')}"

        # Load checkpoint
        state = None
        if resume:
            state = self.checkpoint.load(checkpoint_key)
            if state:
                self.seen_place_ids = set(state.get("seen_place_ids", []))
                logger.info(f"Resuming from checkpoint: {len(self.seen_place_ids)} places already crawled")

        async with StealthBrowser(headless=True) as browser:
            page = await browser.new_page()

            try:
                # Step 1: Search and collect place URLs
                place_urls = await self._search_and_collect_urls(page, query, max_results)
                logger.info(f"Collected {len(place_urls)} place URLs")

                # Step 2: Visit each place and extract data
                for idx, url in enumerate(place_urls, 1):
                    place_id = self._extract_place_id(url)

                    if place_id in self.seen_place_ids:
                        logger.debug(f"[{idx}/{len(place_urls)}] Skipping already crawled: {place_id}")
                        continue

                    try:
                        logger.info(f"[{idx}/{len(place_urls)}] Crawling: {url}")
                        raw_place = await self._extract_place_data(page, url, place_id)

                        if raw_place:
                            self.seen_place_ids.add(place_id)
                            yield raw_place

                            # Save checkpoint every 10 places
                            if idx % 10 == 0:
                                self.checkpoint.save(checkpoint_key, {
                                    "query": query,
                                    "seen_place_ids": list(self.seen_place_ids),
                                    "last_index": idx,
                                })

                    except Exception as e:
                        logger.error(f"Failed to extract place {url}: {e}")
                        continue

                # Clear checkpoint on successful completion
                self.checkpoint.clear(checkpoint_key)

            finally:
                await page.close()

    async def _search_and_collect_urls(self, page: Page, query: str, max_results: int) -> list[str]:
        """Search Google Maps and collect all place URLs"""
        search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"

        await page.goto(search_url, wait_until="networkidle", timeout=30000)
        await random_delay(2000, 4000)

        # Wait for results panel
        try:
            await page.wait_for_selector('[role="feed"]', timeout=10000)
        except PlaywrightTimeout:
            logger.warning("No results found for query")
            return []

        place_urls = []
        last_count = 0
        no_new_results_count = 0

        while len(place_urls) < max_results:
            # Scroll the results panel
            await self._scroll_results_panel(page)
            await random_delay(1000, 2000)

            # Extract place URLs from current view
            new_urls = await page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a[href*="/maps/place/"]'));
                    return links.map(a => a.href).filter(href => href.includes('/maps/place/'));
                }
            """)

            # Deduplicate
            for url in new_urls:
                if url not in place_urls:
                    place_urls.append(url)

            # Check if we're getting new results
            if len(place_urls) == last_count:
                no_new_results_count += 1
                if no_new_results_count >= 3:
                    logger.info("No more results found, stopping scroll")
                    break
            else:
                no_new_results_count = 0

            last_count = len(place_urls)

            logger.debug(f"Collected {len(place_urls)} URLs so far...")

            # Check if we've reached the end
            end_marker = await page.query_selector('text="You\'ve reached the end of the list."')
            if end_marker:
                logger.info("Reached end of results")
                break

        return place_urls[:max_results]

    async def _scroll_results_panel(self, page: Page):
        """Scroll the left results panel to load more places"""
        await page.evaluate("""
            () => {
                const feed = document.querySelector('[role="feed"]');
                if (feed) {
                    feed.scrollTop = feed.scrollHeight;
                }
            }
        """)
        await asyncio.sleep(0.5)

    @retry_async(RetryConfig(max_attempts=3, base_delay=2.0))
    async def _extract_place_data(self, page: Page, url: str, place_id: str) -> RawPlace | None:
        """Extract structured data from a place page"""
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await random_delay(1500, 3000)

        # Wait for place info to load
        try:
            await page.wait_for_selector('h1', timeout=10000)
        except PlaywrightTimeout:
            logger.warning(f"Place page did not load: {url}")
            return None

        # Extract data from embedded JSON (more reliable than HTML parsing)
        place_data = await self._extract_from_page_data(page)

        if not place_data:
            # Fallback to HTML parsing
            place_data = await self._extract_from_html(page)

        if not place_data or not place_data.get("name"):
            logger.warning(f"Could not extract place data from {url}")
            return None

        # Extract reviews
        reviews = await self._extract_reviews(page)

        return RawPlace(
            name=place_data.get("name", ""),
            address=place_data.get("address"),
            lat=place_data.get("lat"),
            lng=place_data.get("lng"),
            district=self._extract_district(place_data.get("address", "")),
            phone=place_data.get("phone"),
            price_min=None,
            price_max=None,
            price_level=self._parse_price_level(place_data.get("price_level")),
            rating=place_data.get("rating"),
            review_count=place_data.get("review_count"),
            hours=place_data.get("hours"),
            features=self._extract_features(place_data),
            dishes=[],  # Google Maps doesn't have dish-level data
            image_urls=place_data.get("image_urls", []),
            source="google_maps_playwright",
            source_id=place_id,
            raw_data={"url": url, "reviews": reviews, **place_data},
        )

    async def _extract_from_page_data(self, page: Page) -> dict | None:
        """Extract data from embedded JSON in page source"""
        try:
            # Google Maps embeds data in window.APP_INITIALIZATION_STATE or similar
            page_data = await page.evaluate("""
                () => {
                    // Try to find embedded JSON data
                    const scripts = Array.from(document.querySelectorAll('script'));
                    for (const script of scripts) {
                        const text = script.textContent;
                        if (text && text.includes('window.APP_INITIALIZATION_STATE')) {
                            // Extract JSON
                            const match = text.match(/window\\.APP_INITIALIZATION_STATE\\s*=\\s*(\\[.*?\\]);/s);
                            if (match) {
                                try {
                                    return JSON.parse(match[1]);
                                } catch (e) {
                                    return null;
                                }
                            }
                        }
                    }
                    return null;
                }
            """)

            if page_data:
                # Parse the nested structure (Google's format is complex)
                return self._parse_app_state(page_data)

        except Exception as e:
            logger.debug(f"Could not extract from page data: {e}")

        return None

    def _parse_app_state(self, app_state: list) -> dict:
        """Parse Google Maps APP_INITIALIZATION_STATE structure"""
        # This is a simplified parser - Google's structure is deeply nested
        # In production, you'd need to reverse-engineer the exact indices
        result = {}

        try:
            # Navigate the nested array structure
            # Format: [[[null, null, [null, null, "Place Name", ...], ...], ...], ...]
            # This is highly fragile and may break with Google updates

            # For now, return empty dict - HTML fallback will be used
            pass

        except Exception as e:
            logger.debug(f"Failed to parse app state: {e}")

        return result

    async def _extract_from_html(self, page: Page) -> dict:
        """Fallback: extract data from HTML elements"""
        data = {}

        try:
            # Name
            name_el = await page.query_selector('h1')
            if name_el:
                data["name"] = await name_el.inner_text()

            # Rating and review count
            rating_text = await page.evaluate("""
                () => {
                    const ratingEl = document.querySelector('[role="img"][aria-label*="stars"]');
                    return ratingEl ? ratingEl.getAttribute('aria-label') : null;
                }
            """)
            if rating_text:
                rating_match = re.search(r'(\\d+\\.\\d+)\\s*stars', rating_text)
                review_match = re.search(r'(\\d+(?:,\\d+)*)\\s*reviews', rating_text)
                if rating_match:
                    data["rating"] = float(rating_match.group(1))
                if review_match:
                    data["review_count"] = int(review_match.group(1).replace(',', ''))

            # Address
            address_el = await page.query_selector('button[data-item-id="address"]')
            if address_el:
                data["address"] = await address_el.get_attribute('aria-label')

            # Phone
            phone_el = await page.query_selector('button[data-item-id*="phone"]')
            if phone_el:
                phone_text = await phone_el.get_attribute('aria-label')
                if phone_text:
                    data["phone"] = phone_text.replace('Phone: ', '').strip()

            # Website
            website_el = await page.query_selector('a[data-item-id="authority"]')
            if website_el:
                data["website"] = await website_el.get_attribute('href')

            # Price level
            price_el = await page.query_selector('[aria-label*="Price:"]')
            if price_el:
                price_text = await price_el.get_attribute('aria-label')
                data["price_level"] = price_text

            # Coordinates from URL
            url = page.url
            coords_match = re.search(r'@(-?\\d+\\.\\d+),(-?\\d+\\.\\d+)', url)
            if coords_match:
                data["lat"] = float(coords_match.group(1))
                data["lng"] = float(coords_match.group(2))

            # Images
            image_urls = await page.evaluate("""
                () => {
                    const imgs = Array.from(document.querySelectorAll('img[src*="googleusercontent"]'));
                    return imgs.map(img => img.src).slice(0, 5);
                }
            """)
            data["image_urls"] = image_urls

            # Opening hours
            hours = await self._extract_hours(page)
            if hours:
                data["hours"] = hours

        except Exception as e:
            logger.error(f"Error extracting from HTML: {e}")

        return data

    async def _extract_hours(self, page: Page) -> dict | None:
        """Extract opening hours"""
        try:
            # Click hours button if present
            hours_button = await page.query_selector('button[data-item-id="oh"]')
            if hours_button:
                await hours_button.click()
                await asyncio.sleep(1)

                # Extract hours table
                hours_data = await page.evaluate("""
                    () => {
                        const rows = Array.from(document.querySelectorAll('table tr'));
                        const hours = {};
                        const dayMap = {
                            'Monday': 'mon', 'Tuesday': 'tue', 'Wednesday': 'wed',
                            'Thursday': 'thu', 'Friday': 'fri', 'Saturday': 'sat', 'Sunday': 'sun'
                        };

                        rows.forEach(row => {
                            const cells = row.querySelectorAll('td');
                            if (cells.length >= 2) {
                                const day = cells[0].textContent.trim();
                                const time = cells[1].textContent.trim();
                                const dayKey = dayMap[day];
                                if (dayKey) {
                                    hours[dayKey] = time === 'Closed' ? 'closed' : time;
                                }
                            }
                        });

                        return Object.keys(hours).length > 0 ? hours : null;
                    }
                """)

                # Close hours dialog
                await page.keyboard.press('Escape')
                await asyncio.sleep(0.5)

                return hours_data

        except Exception as e:
            logger.debug(f"Could not extract hours: {e}")

        return None

    async def _extract_reviews(self, page: Page, max_reviews: int = 10) -> list[dict]:
        """Extract reviews from place page"""
        reviews = []

        try:
            # Click reviews tab
            reviews_button = await page.query_selector('button[aria-label*="Reviews"]')
            if not reviews_button:
                return reviews

            await reviews_button.click()
            await random_delay(1500, 2500)

            # Scroll to load reviews
            for _ in range(3):
                await page.evaluate("""
                    () => {
                        const scrollable = document.querySelector('[role="main"]');
                        if (scrollable) {
                            scrollable.scrollTop = scrollable.scrollHeight;
                        }
                    }
                """)
                await asyncio.sleep(1)

            # Extract review data
            review_elements = await page.query_selector_all('[data-review-id]')

            for el in review_elements[:max_reviews]:
                try:
                    review_data = await el.evaluate("""
                        (element) => {
                            const author = element.querySelector('[class*="author"]')?.textContent || '';
                            const ratingEl = element.querySelector('[role="img"][aria-label*="stars"]');
                            const rating = ratingEl ? parseFloat(ratingEl.getAttribute('aria-label')) : null;
                            const text = element.querySelector('[class*="review-text"]')?.textContent || '';
                            const time = element.querySelector('[class*="review-date"]')?.textContent || '';

                            return { author, rating, text, time };
                        }
                    """)

                    if review_data.get("author"):
                        reviews.append(review_data)

                except Exception as e:
                    logger.debug(f"Failed to extract review: {e}")
                    continue

        except Exception as e:
            logger.debug(f"Could not extract reviews: {e}")

        return reviews

    def _extract_place_id(self, url: str) -> str:
        """Extract place ID from Google Maps URL"""
        # Format: /maps/place/.../@lat,lng,zoom/data=!4m...!1s0x...
        match = re.search(r'/place/([^/]+)/', url)
        if match:
            return match.group(1)

        # Fallback: use full URL as ID
        return url.split('/')[-1]

    def _extract_district(self, address: str) -> str | None:
        """Extract district from Vietnamese address"""
        if not address:
            return None

        # Common patterns
        patterns = [
            r'Quận\\s+(\\d+|[A-Za-z\\s]+)',
            r'Q\\.?\\s*(\\d+)',
            r'District\\s+(\\d+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, address, re.IGNORECASE)
            if match:
                district_num = match.group(1).strip()
                if district_num.isdigit():
                    return f"Quận {district_num}"
                return district_num

        return None

    def _parse_price_level(self, price_text: str | None) -> int | None:
        """Parse price level from text like '$$' or 'Moderate'"""
        if not price_text:
            return None

        if '$' in price_text:
            return min(price_text.count('$'), 4)

        price_map = {
            'inexpensive': 1,
            'moderate': 2,
            'expensive': 3,
            'very expensive': 4,
        }

        return price_map.get(price_text.lower())

    def _extract_features(self, place_data: dict) -> dict:
        """Extract features from place data"""
        features = {}

        # Check for common features in various fields
        text_to_check = ' '.join([
            str(place_data.get('name', '')),
            str(place_data.get('address', '')),
        ]).lower()

        feature_keywords = {
            'wifi': ['wifi', 'wi-fi'],
            'ac': ['air conditioning', 'a/c', 'ac'],
            'parking': ['parking', 'bãi đỗ xe'],
            'delivery': ['delivery', 'giao hàng'],
            'takeaway': ['takeaway', 'take away', 'mang về'],
            'outdoor': ['outdoor', 'ngoài trời'],
            'vegetarian': ['vegetarian', 'chay'],
            'halal': ['halal'],
        }

        for feature, keywords in feature_keywords.items():
            features[feature] = any(kw in text_to_check for kw in keywords)

        return features

    def estimate_count(self, query: str = "", max_results: int = 100, **kwargs) -> int:
        """Estimate number of places to be fetched"""
        return min(max_results, 100)
