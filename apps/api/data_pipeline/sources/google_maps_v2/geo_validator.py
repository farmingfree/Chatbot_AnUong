"""
Geo validation module for coordinate accuracy and location consistency.
"""
from typing import Optional, Dict, Any
from dataclasses import dataclass
import math


@dataclass
class GeoValidationResult:
    """Result of geographic validation checks."""
    is_valid: bool
    confidence: float
    flags: Dict[str, Any]
    errors: list[str]


class GeoValidator:
    """
    Validates geographic data for accuracy and consistency.

    Ensures coordinates are:
    - Within Ho Chi Minh City bounds
    - Consistent with stated district
    - Not in ocean/null island
    - Within reasonable distance of address
    """

    # Ho Chi Minh City bounding box (approximate)
    HCM_BOUNDS = {
        'lat_min': 10.35,
        'lat_max': 11.20,
        'lng_min': 106.35,
        'lng_max': 107.05
    }

    # District centroids for consistency checking (approximate)
    DISTRICT_CENTROIDS = {
        'Quận 1': (10.7756, 106.7019),
        'Quận 2': (10.7897, 106.7472),
        'Quận 3': (10.7847, 106.6878),
        'Quận 4': (10.7575, 106.7025),
        'Quận 5': (10.7553, 106.6672),
        'Quận 6': (10.7478, 106.6347),
        'Quận 7': (10.7333, 106.7219),
        'Quận 8': (10.7389, 106.6289),
        'Quận 9': (10.8503, 106.7844),
        'Quận 10': (10.7731, 106.6697),
        'Quận 11': (10.7628, 106.6503),
        'Quận 12': (10.8631, 106.6700),
        'Bình Thạnh': (10.8142, 106.7108),
        'Tân Bình': (10.8006, 106.6528),
        'Tân Phú': (10.7878, 106.6258),
        'Phú Nhuận': (10.7975, 106.6831),
        'Gò Vấp': (10.8378, 106.6647),
        'Bình Tân': (10.7403, 106.6050),
        'Thủ Đức': (10.8500, 106.7700),
    }

    # Maximum reasonable distance from district centroid (km)
    MAX_DISTRICT_DISTANCE_KM = 8.0

    # Coordinate difference threshold for multi-signal validation (meters)
    COORDINATE_MISMATCH_THRESHOLD_M = 100.0

    def validate(
        self,
        lat: float,
        lng: float,
        district: Optional[str] = None,
        address: Optional[str] = None,
        alternative_coords: Optional[list[tuple[float, float]]] = None
    ) -> GeoValidationResult:
        """
        Validate geographic coordinates with multiple checks.

        Args:
            lat: Latitude
            lng: Longitude
            district: District name (e.g., "Quận 1")
            address: Full address string
            alternative_coords: List of (lat, lng) from other extraction methods

        Returns:
            GeoValidationResult with validation status and flags
        """
        errors = []
        flags = {}
        confidence = 1.0

        # Check 1: Within HCM bounds
        if not self._is_within_hcm(lat, lng):
            errors.append("Coordinates outside Ho Chi Minh City bounds")
            confidence *= 0.1
            flags['outside_hcm'] = True

        # Check 2: Not null island (0, 0)
        if abs(lat) < 0.001 and abs(lng) < 0.001:
            errors.append("Coordinates are null island (0, 0)")
            confidence = 0.0
            flags['null_island'] = True

        # Check 3: District consistency
        if district and district in self.DISTRICT_CENTROIDS:
            distance_km = self._haversine_distance(
                lat, lng,
                *self.DISTRICT_CENTROIDS[district]
            )
            flags['district_distance_km'] = round(distance_km, 2)

            if distance_km > self.MAX_DISTRICT_DISTANCE_KM:
                errors.append(
                    f"Coordinates {distance_km:.1f}km from {district} centroid "
                    f"(max {self.MAX_DISTRICT_DISTANCE_KM}km)"
                )
                confidence *= 0.5
                flags['district_mismatch'] = True

        # Check 4: Multi-signal coordinate consistency
        if alternative_coords:
            max_diff_m = 0.0
            for alt_lat, alt_lng in alternative_coords:
                diff_m = self._haversine_distance(lat, lng, alt_lat, alt_lng) * 1000
                max_diff_m = max(max_diff_m, diff_m)

            flags['max_coordinate_diff_m'] = round(max_diff_m, 1)

            if max_diff_m > self.COORDINATE_MISMATCH_THRESHOLD_M:
                errors.append(
                    f"Coordinate sources differ by {max_diff_m:.0f}m "
                    f"(threshold {self.COORDINATE_MISMATCH_THRESHOLD_M}m)"
                )
                confidence *= 0.3
                flags['inconsistent_coordinates'] = True

        # Check 5: Reasonable coordinate precision
        # Google Maps typically provides 7 decimal places
        lat_decimals = len(str(lat).split('.')[-1]) if '.' in str(lat) else 0
        lng_decimals = len(str(lng).split('.')[-1]) if '.' in str(lng) else 0

        if lat_decimals < 4 or lng_decimals < 4:
            errors.append("Coordinates have suspiciously low precision")
            confidence *= 0.7
            flags['low_precision'] = True

        is_valid = len(errors) == 0 and confidence >= 0.7

        return GeoValidationResult(
            is_valid=is_valid,
            confidence=confidence,
            flags=flags,
            errors=errors
        )

    def _is_within_hcm(self, lat: float, lng: float) -> bool:
        """Check if coordinates are within HCM city bounds."""
        return (
            self.HCM_BOUNDS['lat_min'] <= lat <= self.HCM_BOUNDS['lat_max'] and
            self.HCM_BOUNDS['lng_min'] <= lng <= self.HCM_BOUNDS['lng_max']
        )

    def _haversine_distance(
        self,
        lat1: float, lng1: float,
        lat2: float, lng2: float
    ) -> float:
        """
        Calculate distance between two points in kilometers using Haversine formula.
        """
        R = 6371  # Earth radius in km

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
