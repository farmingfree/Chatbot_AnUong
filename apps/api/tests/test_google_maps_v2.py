"""
Integration tests for Google Maps Crawler v2.

Tests:
- Coordinate extraction accuracy
- Entity validation
- Geo validation
- Duplicate handling
- Parser regression
"""
import pytest
from data_pipeline.sources.google_maps_v2.coordinate_extractor import CoordinateExtractor, CoordinateSource
from data_pipeline.sources.google_maps_v2.entity_validator import EntityValidator
from data_pipeline.sources.google_maps_v2.geo_validator import GeoValidator


class TestCoordinateExtraction:
    """Test coordinate extraction from various sources."""

    def test_url_at_pattern(self):
        """Test @lat,lng pattern extraction."""
        extractor = CoordinateExtractor(None)
        url = "https://www.google.com/maps/place/Pho+Hung/@10.7648891,106.6877054,17z"

        result = extractor._extract_from_url(url)

        assert result is not None
        assert result.lat == 10.7648891
        assert result.lng == 106.6877054
        assert result.source == 'url_at_pattern'

    def test_url_3d4d_pattern(self):
        """Test !3d!4d pattern extraction."""
        extractor = CoordinateExtractor(None)
        url = "https://www.google.com/maps/place/!3d10.771386!4d106.6961339"

        result = extractor._extract_from_url(url)

        assert result is not None
        assert result.lat == 10.771386
        assert result.lng == 106.6961339

    def test_coordinate_selection_consensus(self):
        """Test coordinate selection with consensus."""
        extractor = CoordinateExtractor(None)

        sources = [
            CoordinateSource(10.7648891, 106.6877054, 'url', 0.95, {}),
            CoordinateSource(10.7648900, 106.6877060, 'jsonld', 0.92, {}),
            CoordinateSource(10.7648885, 106.6877050, 'js_state', 0.88, {}),
        ]

        best = extractor.select_best_coordinates(sources)

        # Should select highest confidence with consensus
        assert best.source == 'url'
        assert best.lat == 10.7648891

    def test_coordinate_selection_outlier_rejection(self):
        """Test that outliers are rejected."""
        extractor = CoordinateExtractor(None)

        sources = [
            CoordinateSource(10.7648891, 106.6877054, 'url', 0.95, {}),
            CoordinateSource(10.7648900, 106.6877060, 'jsonld', 0.92, {}),
            CoordinateSource(11.5000000, 107.0000000, 'outlier', 0.50, {}),  # Far away
        ]

        best = extractor.select_best_coordinates(sources)

        # Should not select the outlier
        assert best.source != 'outlier'


class TestEntityValidation:
    """Test entity validation and disambiguation."""

    def test_exact_name_match(self):
        """Test exact name matching."""
        validator = EntityValidator()

        result = validator.validate(
            extracted_name="Phở Hùng",
            search_query="pho hung"
        )

        assert result.is_valid
        assert result.confidence >= 0.9

    def test_fuzzy_name_match(self):
        """Test fuzzy name matching."""
        validator = EntityValidator()

        result = validator.validate(
            extracted_name="Quán Phở Hùng",
            search_query="pho hung"
        )

        assert result.is_valid
        assert result.confidence >= 0.7

    def test_name_mismatch_rejection(self):
        """Test rejection of mismatched names."""
        validator = EntityValidator()

        result = validator.validate(
            extracted_name="Bún Bò Huế",
            search_query="pho hung"
        )

        assert not result.is_valid
        assert result.confidence < 0.6

    def test_chain_detection(self):
        """Test chain restaurant detection."""
        validator = EntityValidator()

        result = validator.validate(
            extracted_name="Phở 24 - Chi nhánh Quận 1",
            address="123 Nguyễn Huệ, Quận 1"
        )

        assert result.flags.get('is_chain') is True

    def test_district_consistency(self):
        """Test district consistency checking."""
        validator = EntityValidator()

        result = validator.validate(
            extracted_name="Phở Hùng",
            extracted_address="241 Nguyễn Trãi, Quận 1, Hồ Chí Minh",
            expected_district="Quận 1"
        )

        assert 'district_mismatch' not in result.flags

    def test_district_mismatch(self):
        """Test district mismatch detection."""
        validator = EntityValidator()

        result = validator.validate(
            extracted_name="Phở Hùng",
            extracted_address="123 Street, Quận 3, Hồ Chí Minh",
            expected_district="Quận 1"
        )

        assert result.flags.get('district_mismatch') is True


class TestGeoValidation:
    """Test geographic validation."""

    def test_valid_hcm_coordinates(self):
        """Test valid HCM coordinates."""
        validator = GeoValidator()

        result = validator.validate(
            lat=10.7648891,
            lng=106.6877054,
            district="Quận 1"
        )

        assert result.is_valid
        assert result.confidence >= 0.9

    def test_outside_hcm_rejection(self):
        """Test rejection of coordinates outside HCM."""
        validator = GeoValidator()

        result = validator.validate(
            lat=21.0285,  # Hanoi
            lng=105.8542,
            district="Quận 1"
        )

        assert not result.is_valid
        assert 'outside_hcm' in result.flags

    def test_null_island_rejection(self):
        """Test rejection of null island coordinates."""
        validator = GeoValidator()

        result = validator.validate(
            lat=0.0,
            lng=0.0,
            district="Quận 1"
        )

        assert not result.is_valid
        assert 'null_island' in result.flags

    def test_district_distance_check(self):
        """Test district distance consistency."""
        validator = GeoValidator()

        # Coordinates in Quận 1
        result = validator.validate(
            lat=10.7756,
            lng=106.7019,
            district="Quận 1"
        )

        assert result.is_valid
        assert result.flags['district_distance_km'] < 3.0

    def test_coordinate_mismatch_detection(self):
        """Test detection of inconsistent coordinates from multiple sources."""
        validator = GeoValidator()

        # Two sources with 200m difference
        result = validator.validate(
            lat=10.7648891,
            lng=106.6877054,
            alternative_coords=[
                (10.7668891, 106.6877054)  # ~2.2km north
            ]
        )

        assert 'inconsistent_coordinates' in result.flags
        assert result.confidence < 0.5


class TestDuplicateHandling:
    """Test duplicate place detection."""

    def test_same_place_id_duplicate(self):
        """Test detection of same Google Place ID."""
        # This would be tested with actual database queries
        # Placeholder for integration test
        pass

    def test_same_cid_duplicate(self):
        """Test detection of same Google CID."""
        pass

    def test_similar_name_and_address(self):
        """Test detection of similar name + address."""
        pass


class TestParserRegression:
    """Test for Google Maps UI changes."""

    @pytest.mark.asyncio
    async def test_name_extraction(self):
        """Test that name extraction still works."""
        # Would require actual page load
        # Placeholder for integration test
        pass

    @pytest.mark.asyncio
    async def test_address_extraction(self):
        """Test that address extraction still works."""
        pass

    @pytest.mark.asyncio
    async def test_rating_extraction(self):
        """Test that rating extraction still works."""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
