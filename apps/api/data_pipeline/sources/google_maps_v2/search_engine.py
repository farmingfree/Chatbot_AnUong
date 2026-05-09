"""
Google Maps search engine with intelligent result selection.
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import asyncio
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout


@dataclass
class SearchResult:
    """A single search result from Google Maps."""
    name: str
    url: str
    snippet: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    index: int = 0


class SearchEngine:
    """
    Handles Google Maps search and intelligent result selection.

    Does NOT blindly click first result - validates relevance first.
    """

    def __init__(self, page: Page):
        self.page = page

    async def search(self, query: str, location: str = "Ho Chi Minh City") -> List[SearchResult]:
        """
        Perform Google Maps search and extract result list.

        Args:
            query: Search query (e.g., "pho district 1")
            location: Location context

        Returns:
            List of SearchResult objects
        """
        full_query = f"{query} {location}" if location else query
        search_url = f"https://www.google.com/maps/search/{full_query.replace(' ', '+')}"

        await self.page.goto(search_url, wait_until='networkidle', timeout=30000)

        # Wait for results to load
        try:
            await self.page.wait_for_selector('div[role="feed"]', timeout=15000)
            await asyncio.sleep(2)  # Let results stabilize
        except PlaywrightTimeout:
            return []

        # Extract all visible results
        results = []
        result_elements = await self.page.locator('div[role="feed"] > div > div > a').all()

        for idx, element in enumerate(result_elements[:20]):  # Limit to first 20
            try:
                # Extract URL
                url = await element.get_attribute('href')
                if not url or 'google.com/maps/place' not in url:
                    continue

                # Extract name from aria-label
                aria_label = await element.get_attribute('aria-label')
                if not aria_label:
                    continue

                # Parse aria-label (format: "Name · Rating · Review count · ...")
                parts = aria_label.split('·')
                name = parts[0].strip() if parts else aria_label

                # Try to extract rating and review count
                rating = None
                review_count = None

                if len(parts) >= 2:
                    rating_text = parts[1].strip()
                    try:
                        rating = float(rating_text.split()[0])
                    except:
                        pass

                if len(parts) >= 3:
                    review_text = parts[2].strip()
                    try:
                        # Extract number from "(1,234)" or "1,234 reviews"
                        import re
                        match = re.search(r'([\d,]+)', review_text)
                        if match:
                            review_count = int(match.group(1).replace(',', ''))
                    except:
                        pass

                results.append(SearchResult(
                    name=name,
                    url=url,
                    snippet=aria_label,
                    rating=rating,
                    review_count=review_count,
                    index=idx
                ))

            except Exception as e:
                continue

        return results

    async def select_best_result(
        self,
        results: List[SearchResult],
        query: str,
        min_similarity: float = 0.6
    ) -> Optional[SearchResult]:
        """
        Select the most relevant result based on query similarity.

        Does NOT just pick first result - validates relevance.

        Args:
            results: List of search results
            query: Original search query
            min_similarity: Minimum name similarity threshold

        Returns:
            Best matching SearchResult or None if no good match
        """
        if not results:
            return None

        from difflib import SequenceMatcher

        def similarity(a: str, b: str) -> float:
            return SequenceMatcher(None, a.lower(), b.lower()).ratio()

        # Score each result
        scored_results = []
        for result in results:
            # Calculate name similarity to query
            name_sim = similarity(result.name, query)

            # Bonus for higher ratings
            rating_bonus = (result.rating or 0) / 10.0

            # Bonus for more reviews (indicates established place)
            review_bonus = min((result.review_count or 0) / 1000.0, 0.5)

            # Penalty for being further down the list
            position_penalty = result.index * 0.05

            total_score = name_sim + rating_bonus + review_bonus - position_penalty

            scored_results.append((total_score, name_sim, result))

        # Sort by total score
        scored_results.sort(reverse=True, key=lambda x: x[0])

        # Return best result if it meets minimum similarity
        best_score, best_name_sim, best_result = scored_results[0]

        if best_name_sim >= min_similarity:
            return best_result

        # If no result meets threshold, return None (don't blindly pick first)
        return None

    async def navigate_to_result(self, result: SearchResult) -> bool:
        """
        Navigate to a specific search result.

        Returns True if navigation successful.
        """
        try:
            await self.page.goto(result.url, wait_until='networkidle', timeout=30000)
            await self.page.wait_for_selector('h1', timeout=10000)
            return True
        except:
            return False
