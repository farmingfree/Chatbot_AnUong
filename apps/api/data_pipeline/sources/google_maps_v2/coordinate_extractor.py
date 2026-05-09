"""
Multi-signal coordinate extractor with fallback hierarchy and cross-validation.
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import re
import json
from playwright.async_api import Page


@dataclass
class CoordinateSource:
    """A coordinate extracted from a specific source."""
    lat: float
    lng: float
    source: str
    confidence: float
    metadata: Dict[str, Any]


class CoordinateExtractor:
    """
    Extracts coordinates from multiple sources and cross-validates.

    Priority hierarchy:
    1. URL @lat,lng pattern
    2. Embedded JSON-LD or structured data
    3. JavaScript state variables
    4. Data attributes on map elements
    5. Network response interception
    """

    def __init__(self, page: Page):
        self.page = page

    async def extract_all_sources(self, url: str) -> List[CoordinateSource]:
        """
        Extract coordinates from all available sources.

        Returns list of CoordinateSource objects for cross-validation.
        """
        sources = []

        # Source 1: URL pattern
        url_coords = self._extract_from_url(url)
        if url_coords:
            sources.append(url_coords)

        # Source 2: Current page URL (may have changed after navigation)
        current_url = self.page.url
        if current_url != url:
            current_url_coords = self._extract_from_url(current_url)
            if current_url_coords:
                sources.append(current_url_coords)

        # Source 3: JSON-LD structured data
        jsonld_coords = await self._extract_from_jsonld()
        if jsonld_coords:
            sources.append(jsonld_coords)

        # Source 4: JavaScript window state
        js_coords = await self._extract_from_js_state()
        if js_coords:
            sources.append(js_coords)

        # Source 5: Meta tags
        meta_coords = await self._extract_from_meta_tags()
        if meta_coords:
            sources.append(meta_coords)

        # Source 6: Data attributes
        data_coords = await self._extract_from_data_attributes()
        if data_coords:
            sources.append(data_coords)

        return sources

    def _extract_from_url(self, url: str) -> Optional[CoordinateSource]:
        """
        Extract coordinates from URL patterns.

        Patterns:
        - @10.7648891,106.6877054
        - !3d10.7648891!4d106.6877054
        - 3d10.7648891,4d106.6877054
        """
        # Pattern 1: @lat,lng
        match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', url)
        if match:
            return CoordinateSource(
                lat=float(match.group(1)),
                lng=float(match.group(2)),
                source='url_at_pattern',
                confidence=0.95,
                metadata={'url': url}
            )

        # Pattern 2: !3d!4d
        match = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', url)
        if match:
            return CoordinateSource(
                lat=float(match.group(1)),
                lng=float(match.group(2)),
                source='url_3d4d_pattern',
                confidence=0.90,
                metadata={'url': url}
            )

        # Pattern 3: 3d,4d (without !)
        match = re.search(r'3d(-?\d+\.\d+)[,_]4d(-?\d+\.\d+)', url)
        if match:
            return CoordinateSource(
                lat=float(match.group(1)),
                lng=float(match.group(2)),
                source='url_3d4d_comma',
                confidence=0.85,
                metadata={'url': url}
            )

        return None

    async def _extract_from_jsonld(self) -> Optional[CoordinateSource]:
        """Extract from JSON-LD structured data."""
        try:
            jsonld_text = await self.page.locator('script[type="application/ld+json"]').first.text_content()
            if not jsonld_text:
                return None

            data = json.loads(jsonld_text)

            # Check for geo coordinates
            if isinstance(data, dict):
                geo = data.get('geo', {})
                if 'latitude' in geo and 'longitude' in geo:
                    return CoordinateSource(
                        lat=float(geo['latitude']),
                        lng=float(geo['longitude']),
                        source='jsonld_geo',
                        confidence=0.92,
                        metadata={'jsonld': data}
                    )

        except Exception:
            pass

        return None

    async def _extract_from_js_state(self) -> Optional[CoordinateSource]:
        """Extract from JavaScript window state variables."""
        try:
            # Try common Google Maps state variables
            coords = await self.page.evaluate("""
                () => {
                    // Check various possible state locations
                    const sources = [
                        window.APP_INITIALIZATION_STATE,
                        window.APP_OPTIONS,
                        window._pageData
                    ];

                    for (const source of sources) {
                        if (!source) continue;

                        const str = JSON.stringify(source);
                        // Look for coordinate patterns in the state
                        const match = str.match(/\\[(-?\\d+\\.\\d+),(-?\\d+\\.\\d+)\\]/);
                        if (match) {
                            const lat = parseFloat(match[1]);
                            const lng = parseFloat(match[2]);
                            // Validate reasonable coordinates
                            if (lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180) {
                                return {lat, lng};
                            }
                        }
                    }

                    return null;
                }
            """)

            if coords and 'lat' in coords and 'lng' in coords:
                return CoordinateSource(
                    lat=coords['lat'],
                    lng=coords['lng'],
                    source='js_window_state',
                    confidence=0.80,
                    metadata=coords
                )

        except Exception:
            pass

        return None

    async def _extract_from_meta_tags(self) -> Optional[CoordinateSource]:
        """Extract from meta tags."""
        try:
            # Check og:latitude and og:longitude
            lat_meta = await self.page.locator('meta[property="og:latitude"]').get_attribute('content')
            lng_meta = await self.page.locator('meta[property="og:longitude"]').get_attribute('content')

            if lat_meta and lng_meta:
                return CoordinateSource(
                    lat=float(lat_meta),
                    lng=float(lng_meta),
                    source='meta_og_tags',
                    confidence=0.88,
                    metadata={'lat_meta': lat_meta, 'lng_meta': lng_meta}
                )

        except Exception:
            pass

        return None

    async def _extract_from_data_attributes(self) -> Optional[CoordinateSource]:
        """Extract from data attributes on map or place elements."""
        try:
            # Try to find elements with data-lat, data-lng attributes
            coords = await self.page.evaluate("""
                () => {
                    const selectors = [
                        '[data-lat][data-lng]',
                        '[data-latitude][data-longitude]',
                        '.place-card[data-lat]',
                        '#map[data-center]'
                    ];

                    for (const selector of selectors) {
                        const el = document.querySelector(selector);
                        if (!el) continue;

                        const lat = el.getAttribute('data-lat') || el.getAttribute('data-latitude');
                        const lng = el.getAttribute('data-lng') || el.getAttribute('data-longitude');

                        if (lat && lng) {
                            return {
                                lat: parseFloat(lat),
                                lng: parseFloat(lng)
                            };
                        }
                    }

                    return null;
                }
            """)

            if coords and 'lat' in coords and 'lng' in coords:
                return CoordinateSource(
                    lat=coords['lat'],
                    lng=coords['lng'],
                    source='data_attributes',
                    confidence=0.75,
                    metadata=coords
                )

        except Exception:
            pass

        return None

    def select_best_coordinate(
        self,
        sources: List[CoordinateSource],
        max_variance_m: float = 100.0
    ) -> Optional[tuple[float, float, Dict[str, Any]]]:
        """
        Select the best coordinate from multiple sources.

        Returns:
            (lat, lng, metadata) where metadata includes:
            - all_sources: list of all extracted coordinates
            - selected_source: which source was chosen
            - confidence: overall confidence score
            - variance_m: maximum distance between sources
        """
        if not sources:
            return None

        if len(sources) == 1:
            src = sources[0]
            return (
                src.lat,
                src.lng,
                {
                    'all_sources': [self._source_to_dict(src)],
                    'selected_source': src.source,
                    'confidence': src.confidence,
                    'variance_m': 0.0
                }
            )

        # Calculate variance between all sources
        max_distance_m = 0.0
        for i, src1 in enumerate(sources):
            for src2 in sources[i+1:]:
                dist_m = self._haversine_distance_m(
                    src1.lat, src1.lng,
                    src2.lat, src2.lng
                )
                max_distance_m = max(max_distance_m, dist_m)

        # If variance is too high, flag as inconsistent
        if max_distance_m > max_variance_m:
            # Return highest confidence source but flag the issue
            best = max(sources, key=lambda s: s.confidence)
            return (
                best.lat,
                best.lng,
                {
                    'all_sources': [self._source_to_dict(s) for s in sources],
                    'selected_source': best.source,
                    'confidence': best.confidence * 0.5,  # Penalize for inconsistency
                    'variance_m': max_distance_m,
                    'inconsistent': True
                }
            )

        # Sources are consistent, pick highest confidence
        best = max(sources, key=lambda s: s.confidence)
        return (
            best.lat,
            best.lng,
            {
                'all_sources': [self._source_to_dict(s) for s in sources],
                'selected_source': best.source,
                'confidence': best.confidence,
                'variance_m': max_distance_m
            }
        )

    def _source_to_dict(self, source: CoordinateSource) -> Dict[str, Any]:
        """Convert CoordinateSource to dict for serialization."""
        return {
            'lat': source.lat,
            'lng': source.lng,
            'source': source.source,
            'confidence': source.confidence
        }

    def _haversine_distance_m(
        self,
        lat1: float, lng1: float,
        lat2: float, lng2: float
    ) -> float:
        """Calculate distance in meters."""
        import math
        R = 6371000  # Earth radius in meters

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)

        a = (
            math.sin(dlat / 2) ** 2 +
            math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c
