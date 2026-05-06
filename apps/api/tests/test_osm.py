"""Test OSM source"""
import asyncio
import sys
import os

# Fix Windows console encoding
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    sys.stdout.reconfigure(encoding='utf-8')

from data_pipeline.sources.osm import OSMSource


async def test_osm():
    """Test OSM source with small sample"""
    print("="*60)
    print("  TESTING OSM SOURCE")
    print("="*60)
    print()
    
    source = OSMSource()

    print("Fetching first 20 places from OpenStreetMap...")
    print("(This may take 10-15 seconds)")
    print()

    # Collect places from async iterator
    places = []
    async for place in source.fetch(max_results=20):
        places.append(place)

    print(f"\n✅ Fetched {len(places)} places from OSM\n")
    
    if not places:
        print("❌ No places found!")
        return
    
    # Show first 10
    for i, place in enumerate(places[:10], 1):
        print(f"[{i}] {place.name}")
        print(f"    Address: {place.address}")
        if place.district:
            print(f"    District: {place.district}")
        print(f"    Coords: ({place.lat:.6f}, {place.lng:.6f})")
        if place.phone:
            print(f"    Phone: {place.phone}")
        if place.dishes:
            print(f"    Cuisine: {', '.join(place.dishes[:3])}")
        
        # Show some features
        if place.features:
            active_features = [k for k, v in place.features.items() if v]
            if active_features:
                print(f"    Features: {', '.join(active_features)}")
        
        print(f"    Source: {place.source} (ID: {place.source_id})")
        print()
    
    # Statistics
    print("="*60)
    print("  STATISTICS")
    print("="*60)
    print()
    
    with_coords = sum(1 for p in places if p.lat and p.lng)
    with_phone = sum(1 for p in places if p.phone)
    with_district = sum(1 for p in places if p.district)
    with_cuisine = sum(1 for p in places if p.dishes)
    
    print(f"Total places: {len(places)}")
    print(f"With coordinates: {with_coords} ({with_coords/len(places)*100:.1f}%)")
    print(f"With phone: {with_phone} ({with_phone/len(places)*100:.1f}%)")
    print(f"With district: {with_district} ({with_district/len(places)*100:.1f}%)")
    print(f"With cuisine: {with_cuisine} ({with_cuisine/len(places)*100:.1f}%)")
    print()
    
    # Amenity type breakdown
    amenity_counts = {}
    for place in places:
        amenity = place.raw_data.get("amenity", "unknown")
        amenity_counts[amenity] = amenity_counts.get(amenity, 0) + 1
    
    print("Amenity types:")
    for amenity, count in sorted(amenity_counts.items(), key=lambda x: -x[1]):
        print(f"  {amenity}: {count}")
    print()
    
    print("✅ OSM source test completed!")
    print()
    print("To import all HCM restaurants:")
    print("  python -m data_pipeline osm --max=5000")


if __name__ == "__main__":
    asyncio.run(test_osm())