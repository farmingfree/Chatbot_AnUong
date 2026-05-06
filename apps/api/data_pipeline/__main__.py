"""CLI entry point for data pipeline"""
import asyncio
import argparse
import sys
import os
from tqdm import tqdm

# Add parent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))

from app.database import get_db
from app.config import settings
from data_pipeline.sources import GoogleMapsSource, FoodySource, ShopeeFoodSource, ManualSource, OSMSource
from data_pipeline.processors import Geocoder, Deduplicator
from data_pipeline.storage import DBWriter


async def run_crawl(source_name: str, **kwargs):
    """Run crawl from specified source"""
    
    # Select source
    sources = {
        "google": GoogleMapsSource(),
        "foody": FoodySource(),
        "shopee": ShopeeFoodSource(),
        "manual": ManualSource(),
        "osm": OSMSource()
    }
    
    if source_name not in sources:
        print(f"❌ Unknown source: {source_name}")
        print(f"Available: {', '.join(sources.keys())}")
        return
    
    source = sources[source_name]
    print(f"\n🚀 Starting crawl from: {source.source_name}")
    print(f"Estimated count: ~{source.estimate_count(**kwargs)} places\n")
    
    # Initialize components
    geocoder = Geocoder()
    
    # Get DB session
    async for db in get_db():
        writer = DBWriter(db)
        deduplicator = Deduplicator(db)
        
        # Fetch and process
        new_count = 0
        updated_count = 0
        skipped_count = 0
        
        try:
            async for raw_place in source.fetch(**kwargs):
                # Check duplicate
                dup_id = await deduplicator.is_duplicate(raw_place)
                if dup_id:
                    skipped_count += 1
                    print(f"⏭️  Skipped duplicate: {raw_place.name}")
                    continue
                
                # Geocode if needed
                if not raw_place.lat or not raw_place.lng:
                    if raw_place.address:
                        coords = await geocoder.geocode(raw_place.address, raw_place.district)
                        if coords:
                            raw_place.lat, raw_place.lng = coords
                
                # Write to DB
                place_id, is_new = await writer.upsert_place(raw_place)
                
                if is_new:
                    new_count += 1
                    print(f"✅ Added: {raw_place.name} (ID: {place_id})")
                else:
                    updated_count += 1
                    print(f"🔄 Updated: {raw_place.name} (ID: {place_id})")
        
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
        except Exception as e:
            print(f"\n\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"\n{'='*50}")
        print(f"📊 SUMMARY")
        print(f"{'='*50}")
        print(f"✅ New places:     {new_count}")
        print(f"🔄 Updated places: {updated_count}")
        print(f"⏭️  Skipped (dup):  {skipped_count}")
        print(f"{'='*50}\n")
        
        break  # Exit after first session


def main():
    parser = argparse.ArgumentParser(description="Food Advisor Data Pipeline")
    parser.add_argument("source", choices=["google", "foody", "shopee", "manual", "osm"],
                       help="Data source to crawl from")
    parser.add_argument("--api-key", help="Google Maps API key (for google source)")
    parser.add_argument("--max-pages", type=int, default=50, help="Max pages (for foody)")
    parser.add_argument("--max-per-district", type=int, default=200, help="Max per district (for shopee)")
    parser.add_argument("--from-file", help="JSON file to import (for manual)")
    parser.add_argument("--max", type=int, help="Max results (for osm)")

    args = parser.parse_args()

    # Build kwargs
    kwargs = {}
    if args.source == "google":
        if not args.api_key:
            print("❌ --api-key required for Google Maps source")
            sys.exit(1)
        kwargs["api_key"] = args.api_key
    elif args.source == "foody":
        kwargs["max_pages"] = args.max_pages
    elif args.source == "shopee":
        kwargs["max_per_district"] = args.max_per_district
    elif args.source == "manual":
        kwargs["from_file"] = args.from_file
    elif args.source == "osm":
        if args.max:
            kwargs["max_results"] = args.max

    # Run
    asyncio.run(run_crawl(args.source, **kwargs))


if __name__ == "__main__":
    main()
