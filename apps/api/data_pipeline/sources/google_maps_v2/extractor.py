"""
Place data extractor with comprehensive field extraction and validation.
"""
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
import re
import json
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout


@dataclass
class ExtractedPlace:
    """Comprehensive place data with all extracted fields."""
    # Core identity
    name: str
    google_place_id: Optional[str] = None
    google_cid: Optional[str] = None
    url: str = ""

    # Location
    lat: Optional[float] = None
    lng: Optional[float] = None
    address: Optional[str] = None
    district: Optional[str] = None

    # Contact
    phone: Optional[str] = None
    website: Optional[str] = None

    # Ratings
    rating: Optional[float] = None
    review_count: Optional[int] = None

    # Media
    image_urls: List[str] = None

    # Metadata
    extraction_method: str = "google_maps_v2"
    raw_html: Optional[str] = None
    raw_json: Optional[Dict] = None

    def __post_init__(self):
        if self.image_urls is None:
            self.image_urls = []
        if self.raw_json is None:
            self.raw_json = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class PlaceExtractor:
    """
    Extracts comprehensive place data from Google Maps detail page.

    Handles multiple extraction strategies with fallbacks.
    """

    def __init__(self, page: Page):
        self.page = page

    async def extract(self, url: str, save_artifacts: bool = True) -> ExtractedPlace:
        """
        Extract all available data from a place detail page.

        Args:
            url: Google Maps place URL
            save_artifacts: Whether to save raw HTML/JSON for debugging

        Returns:
            ExtractedPlace with all extracted fields
        """
        place = ExtractedPlace(name="", url=url)

        # Wait for page to be ready
        try:
            await self.page.wait_for_selector('h1', timeout=10000)
        except PlaywrightTimeout:
            place.name = "ERROR: Page load timeout"
            return place

        # Extract name (required)
        place.name = await self._extract_name()

        # Extract Google identifiers
        place.google_place_id = self._extract_place_id_from_url(url)
        place.google_cid = self._extract_cid_from_url(url)

        # Extract address
        place.address = await self._extract_address()

        # Extract district from address
        if place.address:
            place.district = self._extract_district_from_address(place.address)

        # Extract contact info
        place.phone = await self._extract_phone()
        place.website = await self._extract_website()

        # Extract ratings
        place.rating = await self._extract_rating()
        place.review_count = await self._extract_review_count()

        # Extract images
        place.image_urls = await self._extract_images()

        # Save artifacts if requested
        if save_artifacts:
            place.raw_html = await self.page.content()
            place.raw_json = await self._extract_structured_data()

        return place

    async def _extract_name(self) -> str:
        """Extract place name from h1 or title."""
        try:
            # Try h1 first
            name = await self.page.locator('h1').first.text_content(timeout=5000)
            if name:
                return name.strip()
        except:
            pass

        try:
            # Fallback to title
            title = await self.page.title()
            # Remove " - Google Maps" suffix
            name = re.sub(r'\s*-\s*Google Maps.*$', '', title)
            return name.strip()
        except:
            pass

        return "UNKNOWN"

    async def _extract_address(self) -> Optional[str]:
        """Extract full address."""
        try:
            # Try button with address
            address_button = self.page.locator('button[data-item-id="address"]')
            address = await address_button.locator('div.fontBodyMedium').first.text_content(timeout=5000)
            if address:
                return address.strip()
        except:
            pass

        try:
            # Fallback: look for address-like text
            address_candidates = await self.page.locator('div.fontBodyMedium').all_text_contents()
            for candidate in address_candidates:
                # Vietnamese address pattern: contains district and numbers
                if re.search(r'(Quận|Huyện|Phường|District)\s+\d+', candidate, re.IGNORECASE):
                    if re.search(r'\d+', candidate):  # Has street number
                        return candidate.strip()
        except:
            pass

        return None

    def _extract_district_from_address(self, address: str) -> Optional[str]:
        """Extract district name from address string."""
        # Pattern: Quận 1, District 1, Q.1, etc.
        patterns = [
            r'(Quận\s+\d+)',
            r'(District\s+\d+)',
            r'Q\.\s*(\d+)',
            r'(Bình Thạnh|Tân Bình|Tân Phú|Phú Nhuận|Gò Vấp|Bình Tân|Thủ Đức)',
        ]

        for pattern in patterns:
            match = re.search(pattern, address, re.IGNORECASE)
            if match:
                district = match.group(1)
                # Normalize to "Quận X" format
                if re.match(r'^\d+$', district):
                    return f"Quận {district}"
                if district.lower().startswith('district'):
                    num = re.search(r'\d+', district)
                    if num:
                        return f"Quận {num.group()}"
                return district

        return None

    def _extract_place_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract Google Place ID from URL.

        Format: ChIJ... (base64-like string)
        """
        match = re.search(r'(ChIJ[\w-]+)', url)
        return match.group(1) if match else None

    def _extract_cid_from_url(self, url: str) -> Optional[str]:
        """
        Extract Google CID (Customer ID) from URL.

        Format: 0x...:0x... (hex pairs)
        """
        match = re.search(r'(0x[0-9a-f]+:0x[0-9a-f]+)', url, re.IGNORECASE)
        return match.group(1) if match else None

    async def _extract_phone(self) -> Optional[str]:
        """Extract phone number."""
        try:
            phone_button = self.page.locator('button[data-item-id*="phone"]')
            phone_text = await phone_button.locator('div.fontBodyMedium').first.text_content(timeout=5000)
            if phone_text:
                # Clean phone number
                phone = re.sub(r'[^\d+\s()-]', '', phone_text.strip())
                return phone if phone else None
        except:
            pass

        return None

    async def _extract_website(self) -> Optional[str]:
        """Extract website URL."""
        try:
            website_link = self.page.locator('a[data-item-id="authority"]')
            href = await website_link.get_attribute('href', timeout=5000)
            if href and href.startswith('http'):
                return href
        except:
            pass

        return None

    async def _extract_rating(self) -> Optional[float]:
        """Extract rating score."""
        try:
            # Look for rating in format "4.3" or "4,3"
            rating_text = await self.page.locator('div.fontDisplayLarge').first.text_content(timeout=5000)
            if rating_text:
                # Replace comma with dot for float parsing
                rating_str = rating_text.strip().replace(',', '.')
                match = re.search(r'(\d+\.?\d*)', rating_str)
                if match:
                    rating = float(match.group(1))
                    if 0 <= rating <= 5:
                        return rating
        except:
            pass

        return None

    async def _extract_review_count(self) -> Optional[int]:
        """Extract number of reviews."""
        try:
            # Look for review count like "(4,255)" or "(4.255)"
            review_text = await self.page.locator('button[aria-label*="reviews"]').first.text_content(timeout=5000)
            if review_text:
                # Extract number, handling both comma and dot as thousands separator
                match = re.search(r'([\d,.]+)', review_text)
                if match:
                    count_str = match.group(1).replace(',', '').replace('.', '')
                    return int(count_str)
        except:
            pass

        return None

    async def _extract_images(self, limit: int = 5) -> List[str]:
        """Extract image URLs."""
        try:
            # Find image elements
            images = await self.page.locator('button[aria-label*="Photo"] img, div[role="img"] img').all()
            urls = []

            for img in images[:limit]:
                src = await img.get_attribute('src')
                if src and src.startswith('http'):
                    # Get higher resolution version
                    # Google Maps uses =w{width}-h{height} pattern
                    src = re.sub(r'=w\d+-h\d+', '=w800-h600', src)
                    urls.append(src)

            return urls
        except:
            pass

        return []

    async def _extract_structured_data(self) -> Dict[str, Any]:
        """Extract any structured JSON data from page."""
        try:
            # Try to find JSON-LD
            jsonld = await self.page.locator('script[type="application/ld+json"]').first.text_content()
            if jsonld:
                return json.loads(jsonld)
        except:
            pass

        return {}
