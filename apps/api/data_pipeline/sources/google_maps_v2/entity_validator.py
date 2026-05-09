"""
Entity validation and disambiguation for place matching.
"""
from typing import Optional, Dict, Any
from dataclasses import dataclass
import re
from difflib import SequenceMatcher


@dataclass
class EntityValidationResult:
    """Result of entity validation checks."""
    is_valid: bool
    confidence: float
    flags: Dict[str, Any]
    warnings: list[str]


class EntityValidator:
    """
    Validates extracted place entities against search intent.

    Handles:
    - Name matching with fuzzy logic
    - Duplicate detection
    - Chain disambiguation
    - Address consistency
    """

    # Minimum similarity score for name matching
    MIN_NAME_SIMILARITY = 0.6

    # Common Vietnamese restaurant prefixes/suffixes to normalize
    NORMALIZE_PATTERNS = [
        (r'\s+', ' '),  # Multiple spaces
        (r'^(quán|nhà hàng|cửa hàng|tiệm)\s+', '', re.IGNORECASE),  # Prefixes
        (r'\s+(chi nhánh|branch|cơ sở)\s+\d+$', '', re.IGNORECASE),  # Branch numbers
    ]

    def __init__(self):
        pass

    def validate(
        self,
        extracted_name: str,
        search_query: Optional[str] = None,
        extracted_address: Optional[str] = None,
        expected_district: Optional[str] = None,
        google_place_id: Optional[str] = None,
        google_cid: Optional[str] = None
    ) -> EntityValidationResult:
        """
        Validate extracted entity against search intent and consistency checks.

        Args:
            extracted_name: Name extracted from Google Maps
            search_query: Original search query
            extracted_address: Address extracted from Google Maps
            expected_district: Expected district from search
            google_place_id: Google Place ID
            google_cid: Google CID from URL

        Returns:
            EntityValidationResult with validation status
        """
        warnings = []
        flags = {}
        confidence = 1.0

        # Normalize names for comparison
        normalized_extracted = self._normalize_name(extracted_name)
        flags['normalized_name'] = normalized_extracted

        # Check 1: Name similarity to search query
        if search_query:
            normalized_query = self._normalize_name(search_query)
            similarity = self._calculate_similarity(normalized_extracted, normalized_query)
            flags['name_similarity'] = round(similarity, 3)

            if similarity < self.MIN_NAME_SIMILARITY:
                warnings.append(
                    f"Extracted name '{extracted_name}' has low similarity "
                    f"({similarity:.2f}) to query '{search_query}'"
                )
                confidence *= 0.6

        # Check 2: District consistency
        if expected_district and extracted_address:
            if not self._district_in_address(expected_district, extracted_address):
                warnings.append(
                    f"Expected district '{expected_district}' not found in address"
                )
                confidence *= 0.8
                flags['district_mismatch'] = True

        # Check 3: Chain detection
        chain_indicators = self._detect_chain_indicators(extracted_name, extracted_address)
        if chain_indicators:
            flags['is_chain'] = True
            flags['chain_indicators'] = chain_indicators
            warnings.append(f"Detected chain restaurant: {', '.join(chain_indicators)}")

        # Check 4: Stable identifiers
        if not google_place_id and not google_cid:
            warnings.append("Missing stable identifiers (place_id and CID)")
            confidence *= 0.7
            flags['missing_identifiers'] = True

        # Check 5: Name quality checks
        if len(extracted_name) < 3:
            warnings.append("Name suspiciously short")
            confidence *= 0.5
            flags['short_name'] = True

        if re.search(r'[#\d]{3,}', extracted_name):
            warnings.append("Name contains suspicious number patterns")
            confidence *= 0.7
            flags['suspicious_numbers'] = True

        # Check 6: Address quality
        if extracted_address:
            if len(extracted_address) < 10:
                warnings.append("Address suspiciously short")
                confidence *= 0.8
                flags['short_address'] = True

            if not re.search(r'\d', extracted_address):
                warnings.append("Address missing street numbers")
                confidence *= 0.9
                flags['no_street_number'] = True

        is_valid = confidence >= 0.7 and len([w for w in warnings if 'suspicious' in w.lower()]) == 0

        return EntityValidationResult(
            is_valid=is_valid,
            confidence=confidence,
            flags=flags,
            warnings=warnings
        )

    def _normalize_name(self, name: str) -> str:
        """Normalize restaurant name for comparison."""
        normalized = name.lower().strip()

        for pattern, replacement, *flags in self.NORMALIZE_PATTERNS:
            flag = flags[0] if flags else 0
            normalized = re.sub(pattern, replacement, normalized, flags=flag)

        # Remove diacritics for fuzzy matching (optional)
        # For now, keep Vietnamese diacritics for accuracy

        return normalized.strip()

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity between two strings.

        Uses SequenceMatcher for fuzzy matching.
        """
        return SequenceMatcher(None, str1, str2).ratio()

    def _district_in_address(self, district: str, address: str) -> bool:
        """Check if district name appears in address."""
        normalized_district = district.lower()
        normalized_address = address.lower()

        # Direct match
        if normalized_district in normalized_address:
            return True

        # Try without "Quận" prefix
        district_number = re.search(r'\d+', district)
        if district_number:
            # Look for "Q1", "Q.1", "Quan 1", etc.
            patterns = [
                f"q{district_number.group()}",
                f"q.{district_number.group()}",
                f"q {district_number.group()}",
                f"quan {district_number.group()}",
            ]
            for pattern in patterns:
                if pattern in normalized_address:
                    return True

        return False

    def _detect_chain_indicators(
        self,
        name: str,
        address: Optional[str]
    ) -> list[str]:
        """
        Detect if this is a chain restaurant.

        Returns list of indicators found.
        """
        indicators = []

        # Branch numbers in name
        if re.search(r'(chi nhánh|branch|cơ sở)\s+\d+', name, re.IGNORECASE):
            indicators.append('branch_number_in_name')

        # Multiple locations pattern
        if re.search(r'\d+\s+(locations?|chi nhánh)', name, re.IGNORECASE):
            indicators.append('multiple_locations_mentioned')

        # Common chain patterns
        chain_patterns = [
            r'(highland|starbucks|kfc|lotteria|jollibee)',
            r'(phở 24|phở 2000|cơm tấm)',
        ]
        for pattern in chain_patterns:
            if re.search(pattern, name, re.IGNORECASE):
                indicators.append('known_chain_name')
                break

        return indicators

    def fuzzy_match_names(self, name1: str, name2: str, threshold: float = 0.8) -> bool:
        """
        Check if two names are fuzzy matches.

        Useful for duplicate detection.
        """
        norm1 = self._normalize_name(name1)
        norm2 = self._normalize_name(name2)

        similarity = self._calculate_similarity(norm1, norm2)
        return similarity >= threshold
