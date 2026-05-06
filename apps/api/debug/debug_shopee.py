"""Debug ShopeeFood API"""
import asyncio
import sys
import os
import httpx
import json

# Fix Windows console encoding
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    sys.stdout.reconfigure(encoding='utf-8')


async def debug_shopee():
    """Test ShopeeFood API endpoints"""
    
    # Try different possible endpoints
    endpoints = [
        "https://gappapi.deliverynow.vn/api/delivery/get_all_categories",
        "https://gappapi.deliverynow.vn/api/delivery/get_from_category",
        "https://gappapi.deliverynow.vn/api/delivery/search_merchants",
        "https://shopeefood.vn/api/v1/restaurants",
        "https://shopeefood.vn/api/v2/restaurants/search",
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "x-foody-client-id": "",
        "x-foody-client-type": "1",
        "x-foody-app-type": "1004",
        "x-foody-client-version": "",
        "x-foody-api-version": "1",
        "x-foody-client-language": "vi",
    }
    
    print("🔍 Testing ShopeeFood API endpoints...\n")
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for url in endpoints:
            print(f"Testing: {url}")
            try:
                response = await client.get(url, headers=headers)
                print(f"  Status: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"  ✅ JSON response ({len(str(data))} bytes)")
                        print(f"  Keys: {list(data.keys()) if isinstance(data, dict) else 'array'}")
                        
                        # Save response
                        filename = url.split("/")[-1] + ".json"
                        with open(f"shopee_{filename}", "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                        print(f"  Saved to shopee_{filename}")
                    except:
                        print(f"  ⚠️ Not JSON: {response.text[:200]}")
                else:
                    print(f"  ❌ Error: {response.text[:200]}")
                    
            except Exception as e:
                print(f"  ❌ Exception: {e}")
            
            print()
    
    print("\n" + "="*60)
    print("🔍 Trying to find actual API from website...")
    print("="*60 + "\n")
    
    # Load main page and look for API calls
    try:
        response = await client.get("https://shopeefood.vn/ho-chi-minh", headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        print(f"Main page status: {response.status_code}")
        print(f"Content length: {len(response.text)} bytes")
        
        # Look for API endpoints in HTML/JS
        text = response.text
        api_patterns = [
            "api/",
            "gappapi",
            "deliverynow",
            "shopeefood.vn/api",
        ]
        
        print("\nSearching for API patterns in HTML:")
        for pattern in api_patterns:
            if pattern in text:
                # Find context around pattern
                idx = text.find(pattern)
                context = text[max(0, idx-50):min(len(text), idx+100)]
                print(f"\n  Found '{pattern}':")
                print(f"  ...{context}...")
        
    except Exception as e:
        print(f"❌ Error loading main page: {e}")


if __name__ == "__main__":
    asyncio.run(debug_shopee())
