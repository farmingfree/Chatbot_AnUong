"""
Quality metrics and reporting for crawl runs.
"""
from typing import List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class CrawlMetrics:
    """Metrics for a crawl run."""
    # Counts
    total_searched: int = 0
    total_extracted: int = 0
    total_validated: int = 0
    total_rejected: int = 0
    total_saved: int = 0

    # Quality metrics
    avg_confidence: float = 0.0
    coordinate_mismatches: int = 0
    entity_mismatches: int = 0
    geo_validation_failures: int = 0
    duplicate_entities: int = 0

    # Timing
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0

    # Errors
    errors: List[Dict[str, Any]] = field(default_factory=list)

    # Details
    rejected_places: List[Dict[str, Any]] = field(default_factory=list)
    low_confidence_places: List[Dict[str, Any]] = field(default_factory=list)

    def finalize(self):
        """Calculate final metrics."""
        self.end_time = datetime.utcnow()
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'counts': {
                'total_searched': self.total_searched,
                'total_extracted': self.total_extracted,
                'total_validated': self.total_validated,
                'total_rejected': self.total_rejected,
                'total_saved': self.total_saved,
            },
            'quality': {
                'avg_confidence': round(self.avg_confidence, 3),
                'coordinate_mismatches': self.coordinate_mismatches,
                'entity_mismatches': self.entity_mismatches,
                'geo_validation_failures': self.geo_validation_failures,
                'duplicate_entities': self.duplicate_entities,
            },
            'timing': {
                'start_time': self.start_time.isoformat(),
                'end_time': self.end_time.isoformat() if self.end_time else None,
                'duration_seconds': round(self.duration_seconds, 2),
            },
            'errors': self.errors,
            'rejected_places': self.rejected_places,
            'low_confidence_places': self.low_confidence_places,
        }

    def to_json(self, path: str):
        """Save metrics to JSON file."""
        from pathlib import Path
        Path(path).write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding='utf-8'
        )

    def print_summary(self):
        """Print human-readable summary."""
        print("\n" + "="*60)
        print("CRAWL QUALITY REPORT")
        print("="*60)
        print(f"\nCounts:")
        print(f"  Searched:   {self.total_searched}")
        print(f"  Extracted:  {self.total_extracted}")
        print(f"  Validated:  {self.total_validated}")
        print(f"  Rejected:   {self.total_rejected}")
        print(f"  Saved:      {self.total_saved}")

        if self.total_validated > 0:
            success_rate = (self.total_validated / self.total_extracted) * 100
            print(f"\nSuccess Rate: {success_rate:.1f}%")

        print(f"\nQuality Metrics:")
        print(f"  Avg Confidence:         {self.avg_confidence:.3f}")
        print(f"  Coordinate Mismatches:  {self.coordinate_mismatches}")
        print(f"  Entity Mismatches:      {self.entity_mismatches}")
        print(f"  Geo Validation Failures: {self.geo_validation_failures}")
        print(f"  Duplicate Entities:     {self.duplicate_entities}")

        print(f"\nTiming:")
        print(f"  Duration: {self.duration_seconds:.1f}s")
        if self.total_extracted > 0:
            avg_time = self.duration_seconds / self.total_extracted
            print(f"  Avg per place: {avg_time:.1f}s")

        if self.errors:
            print(f"\nErrors: {len(self.errors)}")
            for error in self.errors[:5]:
                print(f"  - {error.get('message', 'Unknown error')}")

        if self.rejected_places:
            print(f"\nRejected Places: {len(self.rejected_places)}")
            for place in self.rejected_places[:5]:
                print(f"  - {place.get('name', 'Unknown')}: {place.get('reason', 'Unknown reason')}")

        print("\n" + "="*60 + "\n")


class MetricsCollector:
    """Collects metrics during crawl run."""

    def __init__(self):
        self.metrics = CrawlMetrics()
        self._confidence_scores = []

    def record_search(self):
        """Record a search attempt."""
        self.metrics.total_searched += 1

    def record_extraction(self):
        """Record a successful extraction."""
        self.metrics.total_extracted += 1

    def record_validation(self, confidence: float, is_valid: bool, flags: Dict[str, Any]):
        """Record validation result."""
        self._confidence_scores.append(confidence)

        if is_valid:
            self.metrics.total_validated += 1
        else:
            self.metrics.total_rejected += 1

        # Track specific issues
        if flags.get('inconsistent_coordinates'):
            self.metrics.coordinate_mismatches += 1

        if flags.get('district_mismatch') or flags.get('name_mismatch'):
            self.metrics.entity_mismatches += 1

        if flags.get('outside_hcm') or flags.get('null_island'):
            self.metrics.geo_validation_failures += 1

    def record_save(self):
        """Record a successful database save."""
        self.metrics.total_saved += 1

    def record_rejection(self, name: str, reason: str, details: Dict[str, Any]):
        """Record a rejected place."""
        self.metrics.rejected_places.append({
            'name': name,
            'reason': reason,
            'details': details
        })

    def record_low_confidence(self, name: str, confidence: float, warnings: List[str]):
        """Record a low confidence place."""
        self.metrics.low_confidence_places.append({
            'name': name,
            'confidence': confidence,
            'warnings': warnings
        })

    def record_error(self, stage: str, message: str, details: Optional[Dict] = None):
        """Record an error."""
        self.metrics.errors.append({
            'stage': stage,
            'message': message,
            'details': details or {},
            'timestamp': datetime.utcnow().isoformat()
        })

    def finalize(self) -> CrawlMetrics:
        """Finalize and return metrics."""
        if self._confidence_scores:
            self.metrics.avg_confidence = sum(self._confidence_scores) / len(self._confidence_scores)

        self.metrics.finalize()
        return self.metrics
