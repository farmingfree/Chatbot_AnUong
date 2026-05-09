"""
Production-grade Google Maps crawler orchestrator.
Version 2.0 - Correctness over speed.
"""
from typing import Optional, List, Dict, Any
from pathlib import Path
import asyncio
from dataclasses import asdict

from playwright.async_api import async_playwright, Page

from .search_engine import SearchEngine, SearchResult
from .extractor import PlaceExtractor, ExtractedPlace
from .coordinate_extractor import CoordinateExtractor, CoordinateSource
from .entity_validator import EntityValidator, EntityValidationResult
from .geo_validator import GeoValidator, GeoValidationResult
from .debug_artifacts import DebugArtifacts
from .metrics import MetricsCollector, CrawlMetrics
from data_pipeline.utils.stealth import StealthBrowser


class GoogleMapsCrawlerV2:
    """
    Production-grade Google Maps crawler with comprehensive validation.

    Key improvements over v1:
    - Multi-signal coordinate extraction with cross-validation
    - Entity disambiguation and fuzzy matching
    - Geographic validation (HCM bounds, district consistency)
    - Debug artifacts for every place
    - Quality metrics and reporting
    - Human review mode
    - Modular architecture
    """

    VERSION = "2.0.0"

    def __init__(
        self,
        debug_dir: Optional[Path] = None,
        review_mode: bool = False,
        min_confidence: float = 0.7
    ):
        """
        Initialize crawler.

        Args:
            debug_dir: Directory for debug artifacts
            review_mode: Enable human review for each place
            min_confidence: Minimum confidence score to accept a place
        """
        self.debug_dir = debug_dir or Path("data/debug/google_maps")
        self.review_mode = review_mode
        self.min_confidence = min_confidence

        self.debug_artifacts = DebugArtifacts(self.debug_dir)
        self.metrics = MetricsCollector()

        # Validators
        self.entity_validator = EntityValidator()
        self.geo_validator = GeoValidator()

    async def crawl_query(
        self,
        query: str,
        limit: int = 10,
        location: str = "Ho Chi Minh City"
    ) -> List[Dict[str, Any]]:
        """
        Crawl places for a search query with full validation.

        Args:
            query: Search query (e.g., "pho district 1")
            limit: Maximum number of places to crawl
            location: Location context

        Returns:
            List of validated place dictionaries
        """
        validated_places = []

        async with async_playwright() as p:
            browser = await StealthBrowser.launch(p)
            page = await browser.new_page()

            try:
                # Step 1: Search
                print(f"\n🔍 Searching: {query}")
                search_engine = SearchEngine(page)
                results = await search_engine.search(query, location)
                self.metrics.record_search()

                print(f"   Found {len(results)} results")

                # Step 2: Process each result
                for idx, result in enumerate(results[:limit]):
                    print(f"\n📍 [{idx+1}/{min(limit, len(results))}] Processing: {result.name}")

                    try:
                        place_data = await self._process_place(
                            page, result, query
                        )

                        if place_data:
                            validated_places.append(place_data)
                            self.metrics.record_save()
                            print(f"   ✅ Validated and saved")
                        else:
                            print(f"   ❌ Rejected (failed validation)")

                    except Exception as e:
                        print(f"   ⚠️  Error: {e}")
                        self.metrics.record_error(str(e), {'place': result.name})

                    # Rate limiting
                    await asyncio.sleep(2)

            finally:
                await browser.close()

        # Finalize metrics
        self.metrics.finalize()
        self.metrics.print_summary()

        return validated_places

    async def _process_place(
        self,
        page: Page,
        result: SearchResult,
        original_query: str
    ) -> Optional[Dict[str, Any]]:
        """
        Process a single place with full validation pipeline.

        Returns validated place dict or None if rejected.
        """
        # Navigate to place
        success = await SearchEngine(page).navigate_to_result(result)
        if not success:
            self.metrics.record_rejection(
                result.name,
                "Navigation failed",
                {'url': result.url}
            )
            return None

        # Extract all data
        extractor = PlaceExtractor(page)
        place = await extractor.extract(result.url, save_artifacts=True)
        self.metrics.record_extraction()

        # Extract coordinates from multiple sources
        coord_extractor = CoordinateExtractor(page)
        coord_sources = await coord_extractor.extract_all_sources(result.url)

        if not coord_sources:
            self.metrics.record_rejection(
                place.name,
                "No coordinates found",
                {}
            )
            return None

        # Select best coordinates
        best_coords = coord_extractor.select_best_coordinates(coord_sources)
        place.lat = best_coords.lat
        place.lng = best_coords.lng

        # Validate entity
        entity_result = self.entity_validator.validate(
            extracted_name=place.name,
            search_query=original_query,
            extracted_address=place.address,
            expected_district=place.district,
            google_place_id=place.google_place_id,
            google_cid=place.google_cid
        )

        # Validate geography
        alternative_coords = [(c.lat, c.lng) for c in coord_sources if c != best_coords]
        geo_result = self.geo_validator.validate(
            lat=place.lat,
            lng=place.lng,
            district=place.district,
            address=place.address,
            alternative_coords=alternative_coords
        )

        # Calculate overall confidence
        overall_confidence = (entity_result.confidence + geo_result.confidence) / 2.0

        # Record validation
        self.metrics.record_validation(
            confidence=overall_confidence,
            is_valid=entity_result.is_valid and geo_result.is_valid,
            flags={**entity_result.flags, **geo_result.flags}
        )

        # Prepare validation results
        validation_results = {
            'entity': {
                'is_valid': entity_result.is_valid,
                'confidence': entity_result.confidence,
                'flags': entity_result.flags,
                'warnings': entity_result.warnings
            },
            'geo': {
                'is_valid': geo_result.is_valid,
                'confidence': geo_result.confidence,
                'flags': geo_result.flags,
                'errors': geo_result.errors
            },
            'coordinates': {
                'sources': [asdict(c) for c in coord_sources],
                'selected': asdict(best_coords)
            },
            'overall_confidence': overall_confidence
        }

        # Save debug artifacts
        place_id = place.google_place_id or place.google_cid or f"unknown_{hash(place.name)}"
        await self.debug_artifacts.save_all(
            page=page,
            place_id=place_id,
            extracted_data=place.to_dict(),
            validation_results=validation_results
        )

        # Check if place meets quality threshold
        if not entity_result.is_valid or not geo_result.is_valid:
            self.metrics.record_rejection(
                place.name,
                "Validation failed",
                validation_results
            )
            return None

        if overall_confidence < self.min_confidence:
            self.metrics.record_low_confidence(
                place.name,
                overall_confidence,
                entity_result.warnings + geo_result.errors
            )
            self.metrics.record_rejection(
                place.name,
                f"Low confidence ({overall_confidence:.2f} < {self.min_confidence})",
                validation_results
            )
            return None

        # Human review mode
        if self.review_mode:
            if not await self._human_review(place, validation_results):
                self.metrics.record_rejection(
                    place.name,
                    "Rejected by human reviewer",
                    {}
                )
                return None

        # Build final validated place data
        place_data = place.to_dict()
        place_data['confidence_score'] = overall_confidence
        place_data['validation_status'] = 'validated'
        place_data['validation_flags'] = {**entity_result.flags, **geo_result.flags}
        place_data['extraction_version'] = self.VERSION

        return place_data

    async def _human_review(
        self,
        place: ExtractedPlace,
        validation: Dict[str, Any]
    ) -> bool:
        """
        Present place to human for review.

        Returns True to accept, False to reject.
        """
        print("\n" + "="*60)
        print("HUMAN REVIEW")
        print("="*60)
        print(f"Name:       {place.name}")
        print(f"Address:    {place.address}")
        print(f"District:   {place.district}")
        print(f"Coordinates: ({place.lat}, {place.lng})")
        print(f"Rating:     {place.rating} ({place.review_count} reviews)")
        print(f"Confidence: {validation['overall_confidence']:.3f}")

        if validation['entity']['warnings']:
            print("\nEntity Warnings:")
            for w in validation['entity']['warnings']:
                print(f"  - {w}")

        if validation['geo']['errors']:
            print("\nGeo Errors:")
            for e in validation['geo']['errors']:
                print(f"  - {e}")

        print("\nScreenshot saved to:", self.debug_dir / (place.google_place_id or "unknown"))
        print("\n[y] Accept  [n] Reject  [e] Edit")

        while True:
            choice = input("Your choice: ").lower().strip()
            if choice == 'y':
                return True
            elif choice == 'n':
                return False
            elif choice == 'e':
                print("Edit mode not yet implemented. Accept or reject?")
            else:
                print("Invalid choice. Please enter y, n, or e.")

    def get_metrics(self) -> CrawlMetrics:
        """Get current crawl metrics."""
        return self.metrics.metrics

    def save_metrics(self, path: str):
        """Save metrics to JSON file."""
        self.metrics.save(path)
