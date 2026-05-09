"""
Quick test of Google Maps Crawler v2 with "pho district 1" query.
Tests the full validation pipeline.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from data_pipeline.sources.google_maps_v2.crawler import GoogleMapsCrawlerV2


async def main():
    print("\n" + "="*60)
    print("Google Maps Crawler v2 - Quick Test")
    print("="*60 + "\n")

    # Initialize crawler with test settings
    crawler = GoogleMapsCrawlerV2(
        debug_dir=Path("data/debug/google_maps_test"),
        review_mode=False,
        min_confidence=0.7
    )

    # Test query
    query = "pho district 1 hcm"
    limit = 3  # Just test 3 places

    print(f"Query: {query}")
    print(f"Limit: {limit}")
    print(f"Min Confidence: 0.7\n")

    try:
        results = await crawler.crawl_query(
            query=query,
            limit=limit,
            location="Ho Chi Minh City"
        )

        print(f"\n{'='*60}")
        print(f"RESULTS: {len(results)} places validated")
        print(f"{'='*60}\n")

        for idx, place in enumerate(results, 1):
            print(f"{idx}. {place['name']}")
            print(f"   Coordinates: ({place['lat']}, {place['lng']})")
            print(f"   Address: {place.get('address', 'N/A')}")
            print(f"   Confidence: {place.get('confidence_score', 0):.3f}")
            print(f"   Validation: {place.get('validation_status', 'unknown')}")
            if place.get('validation_flags'):
                flags = place['validation_flags']
                if 'coordinate_sources' in flags:
                    print(f"   Coord sources: {flags['coordinate_sources']}")
                if 'max_coordinate_diff_m' in flags:
                    print(f"   Max coord diff: {flags['max_coordinate_diff_m']:.1f}m")
            print()

        # Save results
        output_file = Path("data/debug/google_maps_test/test_results.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)

        import json
        output_file.write_text(
            json.dumps(results, ensure_ascii=False, indent=2, default=str),
            encoding='utf-8'
        )
        print(f"Results saved to: {output_file}")

        return len(results) > 0

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
