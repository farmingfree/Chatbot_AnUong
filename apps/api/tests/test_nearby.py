"""
Test script for nearby places endpoint

Usage:
    python test_nearby.py

Prerequisites:
    1. docker-compose up -d (postgres + redis running)
    2. python create_tables.py (tables created)
    3. python seed_static.py (data seeded)
    4. uvicorn app.main:app --reload (API running on port 8000)
"""

import httpx
import asyncio
import json


async def test_nearby_places():
    """Test the /api/places/nearby endpoint"""
    
    base_url = "http://localhost:8000"
    
    # Test 1: Basic search near Ben Thanh Market
    print("=" * 60)
    print("Test 1: Basic search near Ben Thanh Market")
    print("=" * 60)
    
    payload = {
        "lat": 10.7769,
        "lng": 106.7009,
        "radius_m": 500,
        "limit": 5
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/api/places/nearby",
            json=payload,
            timeout=10.0
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['total']} places")
            print(f"   Center: ({data['center_lat']}, {data['center_lng']})")
            print(f"   Radius: {data['radius_m']}m\n")
            
            for i, place in enumerate(data['places'], 1):
                print(f"{i}. {place['name']}")
                print(f"   📍 {place['address']} ({place['district']})")
                print(f"   📏 {place['distance_m']}m away")
                print(f"   ⭐ {place['rating']}/5 ({place['review_count']} reviews)")
                print(f"   💰 {place['price_range']}")
                print(f"   🍽️  {', '.join(place['top_dishes'][:3])}")
                print(f"   {'🟢 Open' if place['is_open_now'] else '🔴 Closed'}")
                print()
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
    
    # Test 2: Search with price filter
    print("=" * 60)
    print("Test 2: Budget search (max 50k per person, 2 people)")
    print("=" * 60)
    
    payload = {
        "lat": 10.7769,
        "lng": 106.7009,
        "radius_m": 1000,
        "price_max_per_person": 50000,
        "people_count": 2,
        "limit": 5
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/api/places/nearby",
            json=payload,
            timeout=10.0
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['total']} affordable places\n")
            
            for i, place in enumerate(data['places'], 1):
                print(f"{i}. {place['name']} - {place['price_range']}")
        else:
            print(f"❌ Error: {response.status_code}")
    
    # Test 3: Search for vegetarian places
    print("\n" + "=" * 60)
    print("Test 3: Vegetarian places")
    print("=" * 60)
    
    payload = {
        "lat": 10.7769,
        "lng": 106.7009,
        "radius_m": 2000,
        "vegetarian": True,
        "limit": 10
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/api/places/nearby",
            json=payload,
            timeout=10.0
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['total']} vegetarian places\n")
            
            for i, place in enumerate(data['places'], 1):
                print(f"{i}. {place['name']} ({place['district']}) - {place['distance_m']}m")
        else:
            print(f"❌ Error: {response.status_code}")
    
    # Test 4: Search by dish name
    print("\n" + "=" * 60)
    print("Test 4: Search for 'phở'")
    print("=" * 60)
    
    payload = {
        "lat": 10.7769,
        "lng": 106.7009,
        "radius_m": 3000,
        "dish_name": "phở",
        "limit": 5
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/api/places/nearby",
            json=payload,
            timeout=10.0
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['total']} places serving phở\n")
            
            for i, place in enumerate(data['places'], 1):
                print(f"{i}. {place['name']}")
                print(f"   🍜 {', '.join(place['top_dishes'])}")
                print(f"   📏 {place['distance_m']}m away")
                print()
        else:
            print(f"❌ Error: {response.status_code}")
    
    # Test 5: Get place detail
    print("=" * 60)
    print("Test 5: Get place detail (first place from Test 1)")
    print("=" * 60)
    
    # Re-fetch first place to get ID
    payload = {
        "lat": 10.7769,
        "lng": 106.7009,
        "radius_m": 500,
        "limit": 1
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/api/places/nearby",
            json=payload,
            timeout=10.0
        )
        
        if response.status_code == 200:
            data = response.json()
            if data['places']:
                place_id = data['places'][0]['id']
                
                # Get detail
                detail_response = await client.get(
                    f"{base_url}/api/places/{place_id}",
                    timeout=10.0
                )
                
                if detail_response.status_code == 200:
                    detail = detail_response.json()
                    print(f"✅ Place: {detail['name']}")
                    print(f"   📍 {detail['address']}")
                    print(f"   📞 {detail['phone']}")
                    print(f"   ⭐ {detail['rating_google']}/5")
                    print(f"   💰 {detail['price_min']:,}đ - {detail['price_max']:,}đ")
                    print(f"   🍽️  Dishes: {', '.join(detail['dishes'][:5])}")
                    print(f"   {'🟢 Open now' if detail['is_open_now'] else '🔴 Closed'}")
                    print(f"   🖼️  Images: {len(detail['image_urls'])}")
                    print(f"   💬 Reviews: {len(detail['reviews'])}")
                    
                    if detail['hours']:
                        print(f"\n   ⏰ Hours:")
                        for day, hours in detail['hours'].items():
                            print(f"      {day}: {hours}")
                else:
                    print(f"❌ Error getting detail: {detail_response.status_code}")


if __name__ == "__main__":
    print("\n🧪 Testing Food Advisor API - Nearby Places Endpoint\n")
    asyncio.run(test_nearby_places())
    print("\n✅ All tests completed!\n")
