"""
CLI for production-grade Google Maps crawler v2.

Usage:
    python -m data_pipeline.sources.google_maps_v2.cli "pho district 1" --limit 10
    python -m data_pipeline.sources.google_maps_v2.cli "pho district 1" --review-mode
    python -m data_pipeline.sources.google_maps_v2.cli "pho district 1" --min-confidence 0.8
"""
import asyncio
import argparse
import json
from pathlib import Path

from .crawler import GoogleMapsCrawlerV2


def main():
    parser = argparse.ArgumentParser(
        description="Google Maps Crawler v2 - Production Quality"
    )
    parser.add_argument(
        "query",
        help="Search query (e.g., 'pho district 1 hcm')"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of places to crawl (default: 10)"
    )
    parser.add_argument(
        "--location",
        default="Ho Chi Minh City",
        help="Location context (default: Ho Chi Minh City)"
    )
    parser.add_argument(
        "--review-mode",
        action="store_true",
        help="Enable human review for each place"
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.7,
        help="Minimum confidence score to accept (default: 0.7)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output JSON file path"
    )
    parser.add_argument(
        "--debug-dir",
        type=str,
        default="data/debug/google_maps",
        help="Directory for debug artifacts"
    )

    args = parser.parse_args()

    # Initialize crawler
    crawler = GoogleMapsCrawlerV2(
        debug_dir=Path(args.debug_dir),
        review_mode=args.review_mode,
        min_confidence=args.min_confidence
    )

    # Run crawl
    print(f"\n{'='*60}")
    print(f"Google Maps Crawler v{GoogleMapsCrawlerV2.VERSION}")
    print(f"{'='*60}")
    print(f"Query: {args.query}")
    print(f"Limit: {args.limit}")
    print(f"Min Confidence: {args.min_confidence}")
    print(f"Review Mode: {args.review_mode}")
    print(f"Debug Dir: {args.debug_dir}")
    print(f"{'='*60}\n")

    results = asyncio.run(crawler.crawl_query(
        query=args.query,
        limit=args.limit,
        location=args.location
    ))

    # Save results
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(results, ensure_ascii=False, indent=2, default=str),
            encoding='utf-8'
        )
        print(f"\n💾 Results saved to: {output_path}")

    # Save metrics
    metrics_path = Path(args.debug_dir) / "latest_metrics.json"
    crawler.metrics.to_json(str(metrics_path))
    print(f"📊 Metrics saved to: {metrics_path}")

    print(f"\n✅ Crawl complete. {len(results)} places validated and saved.")


if __name__ == "__main__":
    main()
