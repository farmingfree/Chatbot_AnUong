"""Test data pipeline components with small samples"""
import asyncio
import sys
import json
import os
from pprint import pprint

# Fix Windows console encoding
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    sys.stdout.reconfigure(encoding='utf-8')

from data_pipeline.sources import ShopeeFoodSource, FoodySource, ManualSource
from data_pipeline.processors import Geocoder, normalize_text


def print_section(title: str):
    """Print section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_place(raw_place, index: int):
    """Pretty print a RawPlace object"""
    print(f"\n[{index}] {raw_place.name}")
    print(f"    Address: {raw_place.address}")
    print(f"    District: {raw_place.district}")
    print(f"    Coords: ({raw_place.lat}, {raw_place.lng})")
    print(f"    Phone: {raw_place.phone or 'N/A'}")
    print(f"    Price: {raw_place.price_min:,}đ - {raw_place.price_max:,}đ" if raw_place.price_min else "    Price: N/A")
    print(f"    Rating: {raw_place.rating}⭐ ({raw_place.review_count} reviews)" if raw_place.rating else "    Rating: N/A")
    print(f"    Dishes: {', '.join(raw_place.dishes[:5])}" if raw_place.dishes else "    Dishes: N/A")
    print(f"    Features: {raw_place.features}" if raw_place.features else "    Features: N/A")
    print(f"    Source: {raw_place.source} (ID: {raw_place.source_id})")


async def test_shopee_food():
    """Test ShopeeFood source - 10 places from District 1"""
    print_section("TEST 1: ShopeeFood API (10 quán Quận 1)")
    
    source = ShopeeFoodSource()
    count = 0
    max_count = 10
    
    try:
        async for raw_place in source.fetch(max_per_district=10):
            if raw_place.district == "Quận 1":
                print_place(raw_place, count + 1)
                count += 1
                if count >= max_count:
                    break
        
        print(f"\n✅ Fetched {count} places from ShopeeFood")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_foody():
    """Test Foody source - page 1 of 'quan-an' category"""
    print_section("TEST 2: Foody.vn Scraper (Page 1 - Quán ăn)")
    
    source = FoodySource()
    count = 0
    
    try:
        async for raw_place in source.fetch(max_pages=1):
            print_place(raw_place, count + 1)
            count += 1
            if count >= 15:  # Foody returns ~15 per page
                break
        
        print(f"\n✅ Fetched {count} places from Foody")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_manual():
    """Test Manual source - import sample JSON"""
    print_section("TEST 3: Manual Import (sample_places.json)")

    source = ManualSource()
    count = 0

    # Use absolute path
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "data", "sample_places.json")

    try:
        async for raw_place in source.fetch(from_file=json_path):
            print_place(raw_place, count + 1)
            count += 1

        print(f"\n✅ Imported {count} places from JSON")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_geocoder():
    """Test Nominatim geocoder"""
    print_section("TEST 4: Nominatim Geocoder")
    
    geocoder = Geocoder()
    
    test_addresses = [
        ("260 Pasteur, Quận 3, HCM", "Quận 3"),
        ("26 Lê Thị Riêng, Quận 1, HCM", "Quận 1"),
        ("191 Bùi Viện, Quận 1, HCM", "Quận 1"),
    ]
    
    print("Testing geocoding for 3 addresses:\n")
    
    for address, district in test_addresses:
        try:
            coords = await geocoder.geocode(address, district)
            if coords:
                lat, lng = coords
                print(f"✅ {address}")
                print(f"   → ({lat:.6f}, {lng:.6f})")
                print(f"   → https://www.google.com/maps?q={lat},{lng}\n")
            else:
                print(f"❌ {address}")
                print(f"   → Could not geocode\n")
        except Exception as e:
            print(f"❌ {address}")
            print(f"   → Error: {e}\n")


def test_normalizer():
    """Test text normalizer"""
    print_section("TEST 5: Text Normalizer")
    
    test_texts = [
        "Phở Hòa Pasteur",
        "Bánh Mì Huỳnh Hoa",
        "Cơm Tấm Sườn Nướng",
        "Quán Ăn Ngon 123",
        "Cafe Sài Gòn - Chi nhánh 2",
    ]
    
    print("Testing text normalization:\n")
    
    for text in test_texts:
        normalized = normalize_text(text)
        print(f"Original:   {text}")
        print(f"Normalized: {normalized}")
        print()


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  DATA PIPELINE TEST SUITE")
    print("="*60)
    
    # Test 1: ShopeeFood
    await test_shopee_food()
    
    # Test 2: Foody
    await test_foody()
    
    # Test 3: Manual
    await test_manual()
    
    # Test 4: Geocoder
    await test_geocoder()
    
    # Test 5: Normalizer (sync)
    test_normalizer()
    
    # Summary
    print_section("✅ ALL TESTS COMPLETED")
    print("Next steps:")
    print("1. Review output to verify data format")
    print("2. Check coordinates on Google Maps")
    print("3. Run full pipeline: python -m data_pipeline <source>")
    print()


if __name__ == "__main__":
    asyncio.run(main())
