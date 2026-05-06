"""
Test script for new endpoints
Run with: python test_endpoints.py
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("Testing imports...")

try:
    from app.services.geo import (
        normalize_text,
        calc_distance_m,
        is_open_now,
        price_level_to_range,
        get_google_maps_url
    )
    print("✓ geo service imported successfully")
    
    # Test normalize_text
    result = normalize_text("Phở Bò")
    assert result == "pho bo", f"Expected 'pho bo', got '{result}'"
    print(f"✓ normalize_text('Phở Bò') = '{result}'")
    
    # Test calc_distance_m
    # Ben Thanh Market to Notre Dame Cathedral (~500m)
    distance = calc_distance_m(10.7729, 106.6980, 10.7797, 106.6991)
    print(f"✓ calc_distance_m() = {distance:.0f}m")
    
    # Test is_open_now
    hours = {"mon": "08:00-22:00", "tue": "08:00-22:00"}
    result = is_open_now(hours)
    print(f"✓ is_open_now() = {result}")
    
    # Test price_level_to_range
    result = price_level_to_range(2)
    assert result == (50000, 200000)
    print(f"✓ price_level_to_range(2) = {result}")
    
    # Test get_google_maps_url
    url = get_google_maps_url(google_place_id="ChIJabcdef123")
    assert "place_id:ChIJabcdef123" in url
    print(f"✓ get_google_maps_url() = {url}")
    
except Exception as e:
    print(f"✗ Error importing geo service: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    from app.routers import dishes, places
    print("✓ routers imported successfully")
except Exception as e:
    print(f"✗ Error importing routers: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    from app.schemas.dish import DishCard, NearbyDishesRequest, NearbyDishesResponse
    from app.schemas.place import PlaceCard, PlaceDetail
    print("✓ schemas imported successfully")
except Exception as e:
    print(f"✗ Error importing schemas: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*50)
print("All imports successful! ✓")
print("="*50)
print("\nEndpoints available:")
print("  POST /api/dishes/nearby - Find dishes at nearby places")
print("  GET  /api/places/{id}?lat=X&lng=Y - Get place detail with distance")
print("\nTo test with real data:")
print("  1. Start API: docker-compose up -d")
print("  2. Seed data: python seed_static.py && python seed_data.py")
print("  3. Test: curl -X POST http://localhost:8000/api/dishes/nearby \\")
print("           -H 'Content-Type: application/json' \\")
print("           -d '{\"lat\":10.7769,\"lng\":106.7009,\"radius_m\":1000}'")
