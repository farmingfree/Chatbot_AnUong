# Google Maps Crawler v2.0 - Production Quality

**Version:** 2.0.0  
**Status:** Production-ready  
**Priority:** Correctness over speed

## Overview

Complete refactor of the Google Maps crawler with production-grade validation, quality controls, and comprehensive error handling. Addresses critical data quality issues discovered in v1 (incorrect coordinates, entity mismatches).

## Key Improvements

### 1. Multi-Signal Coordinate Extraction
- **6 extraction methods** with fallback hierarchy:
  1. URL `@lat,lng` pattern (95% confidence)
  2. URL `!3d!4d` pattern (90% confidence)
  3. JSON-LD structured data (92% confidence)
  4. JavaScript window state (85% confidence)
  5. Meta tags (80% confidence)
  6. Data attributes (75% confidence)

- **Cross-validation**: Compares all sources, rejects outliers >100m apart
- **Consensus selection**: Picks highest confidence with spatial agreement

### 2. Entity Validation
- **Fuzzy name matching** with configurable similarity threshold (default 0.6)
- **Chain detection**: Identifies franchise restaurants
- **District consistency**: Validates address matches expected district
- **Stable identifiers**: Requires Google Place ID or CID
- **Quality checks**: Rejects suspicious patterns (short names, number spam)

### 3. Geographic Validation
- **HCM bounds checking**: Rejects coordinates outside city limits
- **Null island detection**: Catches (0, 0) errors
- **District distance validation**: Max 8km from district centroid
- **Coordinate precision**: Validates decimal places (min 4)

### 4. Debug Artifacts
Every crawled place saves:
- `screenshot.png` - Visual proof
- `raw.html` - Full page HTML
- `extracted.json` - Parsed data
- `validation.json` - Validation results
- `metadata.json` - Crawl metadata

Stored in: `data/debug/google_maps/{place_id}/`

### 5. Quality Metrics
Comprehensive reporting:
- Success/rejection rates
- Average confidence scores
- Coordinate mismatches
- Entity mismatches
- Geo validation failures
- Duplicate detection
- Per-place timing

### 6. Human Review Mode
Optional interactive validation:
```bash
python -m data_pipeline.sources.google_maps_v2.cli "pho district 1" --review-mode
```

Shows screenshot + extracted data, prompts:
- `[y]` accept
- `[n]` reject
- `[e]` edit fields

### 7. Modular Architecture
```
google_maps_v2/
├── __init__.py
├── crawler.py           # Main orchestrator
├── search_engine.py     # Search + result selection
├── extractor.py         # Data extraction
├── coordinate_extractor.py  # Multi-signal coords
├── entity_validator.py  # Name/address validation
├── geo_validator.py     # Geographic checks
├── debug_artifacts.py   # Artifact management
├── metrics.py           # Quality reporting
└── cli.py               # Command-line interface
```

### 8. Enhanced Database Schema
New fields:
- `google_cid` - Google CID (unique index)
- `confidence_score` - Overall confidence (0-1)
- `extraction_method` - Source method used
- `validation_status` - pending/validated/rejected
- `validation_flags` - JSONB with validation details
- `extraction_version` - Crawler version (2.0.0)
- `raw_payload` - JSONB with full extracted data

### 9. Integration Tests
Comprehensive test suite:
- Coordinate extraction accuracy
- Entity validation logic
- Geo validation boundaries
- Duplicate handling
- Parser regression detection

Run: `pytest tests/test_google_maps_v2.py`

### 10. Production Safeguards
- **Minimum confidence threshold**: Default 0.7 (configurable)
- **Automatic rejection**: Low confidence, validation failures
- **Rate limiting**: 2s delay between places
- **Error recovery**: Continues on individual failures
- **Duplicate prevention**: Unique indexes on place_id/CID

## Usage

### Basic Crawl
```bash
python -m data_pipeline.sources.google_maps_v2.cli "pho district 1 hcm" --limit 10
```

### High-Confidence Only
```bash
python -m data_pipeline.sources.google_maps_v2.cli "pho district 1" --min-confidence 0.85
```

### With Human Review
```bash
python -m data_pipeline.sources.google_maps_v2.cli "pho district 1" --review-mode
```

### Save Results
```bash
python -m data_pipeline.sources.google_maps_v2.cli "pho district 1" \
    --output results.json \
    --debug-dir data/debug/my_crawl
```

## Configuration

### Confidence Thresholds
- **Entity validation**: 0.6 minimum name similarity
- **Coordinate consensus**: 100m maximum difference
- **District distance**: 8km maximum from centroid
- **Overall acceptance**: 0.7 minimum confidence

### HCM City Bounds
```python
lat: 10.35 - 11.20
lng: 106.35 - 107.05
```

### District Centroids
Defined for all 19 districts + Thủ Đức for distance validation.

## Output Format

### Validated Place
```json
{
  "name": "Phở Hùng",
  "google_place_id": "ChIJgTpe0RkvdTERiArZU41y19w",
  "google_cid": "0xdcd7728d53d90a88",
  "lat": 10.7648891,
  "lng": 106.6877054,
  "address": "241 - 243 Nguyễn Trãi, Quận 1",
  "district": "Quận 1",
  "rating": 4.3,
  "review_count": 4255,
  "confidence_score": 0.92,
  "validation_status": "validated",
  "validation_flags": {
    "coordinate_sources": 3,
    "max_coordinate_diff_m": 15.2,
    "district_distance_km": 1.8,
    "name_similarity": 0.95
  },
  "extraction_version": "2.0.0"
}
```

### Quality Report
```
CRAWL QUALITY REPORT
============================================================

Counts:
  Searched:   10
  Extracted:  10
  Validated:  8
  Rejected:   2
  Saved:      8

Success Rate: 80.0%

Quality Metrics:
  Avg Confidence:         0.876
  Coordinate Mismatches:  1
  Entity Mismatches:      0
  Geo Validation Failures: 1
  Duplicate Entities:     0

Timing:
  Duration: 127.3s
  Avg per place: 12.7s

Rejected Places: 2
  - Phở ABC: Coordinate mismatch (sources differ by 250m)
  - Restaurant XYZ: Outside HCM bounds
```

## Migration

Run database migration to add v2 fields:
```bash
python migrate_crawler_v2.py
```

## Comparison: v1 vs v2

| Feature | v1 | v2 |
|---------|----|----|
| Coordinate extraction | Single source | 6 sources + cross-validation |
| Entity validation | None | Fuzzy matching + disambiguation |
| Geo validation | None | HCM bounds + district checks |
| Debug artifacts | None | HTML + JSON + screenshots |
| Quality metrics | None | Comprehensive reporting |
| Human review | No | Optional interactive mode |
| Duplicate handling | Basic | Unique indexes + detection |
| Confidence scoring | No | Per-place + overall |
| Test coverage | None | Integration tests |
| Architecture | Monolithic | Modular (9 files) |

## Known Limitations

1. **Speed**: ~12s per place (vs ~5s in v1) due to validation overhead
2. **Google Maps UI changes**: May require extractor updates
3. **Vietnamese text**: Requires UTF-8 encoding throughout
4. **Rate limiting**: Google may block aggressive crawling

## Troubleshooting

### "No coordinates found"
- Check if place detail page loaded
- Verify URL contains coordinate patterns
- Review debug artifacts in `data/debug/google_maps/{place_id}/`

### "Coordinate mismatch"
- Multiple sources disagree by >100m
- Indicates unstable/incorrect data
- Review `validation.json` for details

### "Entity mismatch"
- Extracted name doesn't match search query
- May indicate wrong place selected
- Check `screenshot.png` to verify

### "Outside HCM bounds"
- Coordinates not in Ho Chi Minh City
- Verify search query includes location
- Check if place actually exists in HCM

## Future Enhancements

- [ ] Review extraction from detail pages
- [ ] Opening hours parsing
- [ ] Price range extraction
- [ ] Category/cuisine classification
- [ ] Network response interception for coordinates
- [ ] Automatic retry with different extraction methods
- [ ] Batch processing with checkpoint/resume
- [ ] API integration for persistence

## Version History

### 2.0.0 (2026-05-09)
- Complete refactor for production quality
- Multi-signal coordinate extraction
- Comprehensive validation pipeline
- Debug artifacts and quality metrics
- Modular architecture
- Integration tests

### 1.0.0 (2026-05-08)
- Initial working crawler
- Basic extraction
- Known issues: incorrect coordinates, no validation

## License

Internal use only - chatbot_anuong project
