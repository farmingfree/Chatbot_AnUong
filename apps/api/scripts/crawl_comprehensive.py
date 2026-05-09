#!/usr/bin/env python3
"""
Example crawl strategies for Ho Chi Minh City restaurants

This script demonstrates different approaches to crawling Google Maps
for comprehensive restaurant coverage.
"""

import subprocess
import time

# Strategy 1: By popular dishes
DISH_QUERIES = [
    "pho district 1 hcm",
    "bun bo hue ho chi minh",
    "banh mi saigon",
    "com tam district 1",
    "bun dau mam tom hcm",
    "hu tieu nam vang saigon",
    "banh xeo ho chi minh",
    "cao lau hoi an hcm",
    "mi quang district 1",
    "bun rieu cua hcm",
]

# Strategy 2: By district + category
DISTRICT_QUERIES = [
    "restaurant district 1 hcm",
    "restaurant district 2 hcm",
    "restaurant district 3 hcm",
    "restaurant binh thanh hcm",
    "restaurant phu nhuan hcm",
    "restaurant tan binh hcm",
    "restaurant go vap hcm",
    "restaurant thu duc hcm",
]

# Strategy 3: By cuisine type
CUISINE_QUERIES = [
    "vietnamese restaurant ho chi minh",
    "japanese restaurant saigon",
    "korean restaurant hcm",
    "italian restaurant district 1",
    "french restaurant saigon",
    "chinese restaurant cho lon",
    "thai restaurant ho chi minh",
    "indian restaurant district 1",
]

# Strategy 4: By meal type
MEAL_QUERIES = [
    "breakfast restaurant hcm",
    "lunch restaurant district 1",
    "dinner restaurant saigon",
    "late night food ho chi minh",
    "street food hcm",
]

# Strategy 5: By special features
FEATURE_QUERIES = [
    "vegetarian restaurant hcm",
    "halal restaurant ho chi minh",
    "buffet restaurant saigon",
    "rooftop restaurant district 1",
    "view restaurant ho chi minh",
    "romantic restaurant saigon",
]


def run_crawl(query: str, max_results: int = 100):
    """Run a single crawl"""
    print(f"\n{'='*60}")
    print(f"🔍 Crawling: {query}")
    print(f"{'='*60}\n")

    cmd = [
        "python", "-m", "data_pipeline",
        "google_playwright",
        "--query", query,
        "--max-results", str(max_results)
    ]

    try:
        subprocess.run(cmd, check=True)
        print(f"\n✅ Completed: {query}\n")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Failed: {query} - {e}\n")
    except KeyboardInterrupt:
        print(f"\n⚠️  Interrupted: {query}\n")
        raise

    # Delay between crawls to avoid rate limiting
    time.sleep(30)


def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║  Google Maps Crawler - Comprehensive Coverage Strategy  ║
╚══════════════════════════════════════════════════════════╝

This script will crawl Google Maps using multiple strategies:
1. Popular Vietnamese dishes (10 queries)
2. Districts + category (8 queries)
3. Cuisine types (8 queries)
4. Meal types (5 queries)
5. Special features (6 queries)

Total: 37 queries × 100 results = ~3,700 places
Estimated time: 6-8 hours

Press Ctrl+C to stop at any time. Progress is checkpointed.
""")

    input("Press Enter to start...")

    strategies = [
        ("Popular Dishes", DISH_QUERIES),
        ("District Coverage", DISTRICT_QUERIES),
        ("Cuisine Types", CUISINE_QUERIES),
        ("Meal Types", MEAL_QUERIES),
        ("Special Features", FEATURE_QUERIES),
    ]

    try:
        for strategy_name, queries in strategies:
            print(f"\n\n{'#'*60}")
            print(f"# Strategy: {strategy_name}")
            print(f"# Queries: {len(queries)}")
            print(f"{'#'*60}\n")

            for query in queries:
                run_crawl(query)

        print("""
╔══════════════════════════════════════════════════════════╗
║                  ✅ ALL CRAWLS COMPLETE                  ║
╚══════════════════════════════════════════════════════════╝

Next steps:
1. Check database for new places
2. Run deduplication if needed
3. Index places in Qdrant for semantic search
4. Test the chatbot with real data

Commands:
  # Check place count
  psql -d food_advisor -c "SELECT COUNT(*) FROM places;"

  # Index in Qdrant
  python scripts/index_qdrant.py

  # Start API
  uvicorn app.main:app --reload
""")

    except KeyboardInterrupt:
        print("\n\n⚠️  Crawl interrupted by user")
        print("Progress has been saved. Run this script again to resume.")


if __name__ == "__main__":
    main()
