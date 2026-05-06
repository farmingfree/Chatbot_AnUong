"""Test Foody.vn API thực tế"""
import asyncio
import httpx
import json
import sys
import os

# Fix Windows console encoding
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')


async def test_foody_api():
    """Test Foody API với các endpoints có thể"""
    
    # Thử các endpoints khác nhau
    endpoints = [
        # API v1 (có thể public)
        "https://gappapi.foody.vn/api/restaurant/list",
        
        # API v2
        "https://www.foody.vn/__get/Restaurant/GetList",
        
        # Search API
        "https://www.foody.vn/__get/Search/GetRestaurantList",
        
        # Mobile API
        "https://gappapi.deliverynow.vn/api/delivery/get_from_category",
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.foody.vn/ho-chi-minh/quan-an",
        "Origin": "https://www.foody.vn",
    }
    
    # Params thử nghiệm
    params_list = [
        {"lat": 10.7769, "lng": 106.7009, "page": 1, "limit": 20},
        {"cityId": 50, "districtId": 0, "page": 1},
        {"q": "quận 1", "page": 1},
    ]
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for i, url in enumerate(endpoints, 1):
            print(f"\n{'='*60}")
            print(f"Test #{i}: {url}")
            print('='*60)
            
            for params in params_list:
                try:
                    print(f"\n[*] Trying params: {params}")
                    
                    response = await client.get(
                        url,
                        headers=headers,
                        params=params
                    )
                    
                    print(f"Status: {response.status_code}")
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            print(f"[OK] Got JSON response!")
                            print(f"Keys: {list(data.keys()) if isinstance(data, dict) else 'array'}")

                            # Tìm restaurants trong response
                            if isinstance(data, dict):
                                for key in ["Items", "items", "data", "restaurants", "SearchItems", "result"]:
                                    if key in data:
                                        items = data[key]
                                        if isinstance(items, list) and items:
                                            print(f"\n[SUCCESS] FOUND {len(items)} restaurants in '{key}'!")
                                            print(f"\nFirst restaurant:")
                                            print(json.dumps(items[0], indent=2, ensure_ascii=False)[:500])
                                            return  # Success!

                        except json.JSONDecodeError:
                            print(f"[ERROR] Not JSON: {response.text[:200]}")
                    else:
                        print(f"[ERROR] Status {response.status_code}: {response.text[:200]}")

                except Exception as e:
                    print(f"[ERROR] Exception: {e}")
                    
                await asyncio.sleep(1)  # Rate limit
    
    print("\n" + "="*60)
    print("[FAIL] Khong tim thay API endpoint nao hoat dong")
    print("="*60)
    print("\n[INFO] Giai phap:")
    print("1. Mở Chrome → https://www.foody.vn/ho-chi-minh/quan-an")
    print("2. F12 → Network → XHR")
    print("3. Scroll trang để load restaurants")
    print("4. Tìm request có JSON response")
    print("5. Copy as cURL và chạy: python parse_foody_curl.py foody_curl.txt")


if __name__ == "__main__":
    asyncio.run(test_foody_api())
