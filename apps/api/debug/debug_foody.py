"""Debug Foody.vn scraper"""
import asyncio
import sys
import os
import httpx
from bs4 import BeautifulSoup

# Fix Windows console encoding
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    sys.stdout.reconfigure(encoding='utf-8')


async def debug_foody():
    """Fetch Foody page and analyze HTML structure"""
    url = "https://www.foody.vn/ho-chi-minh/quan-an"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.foody.vn/",
    }
    
    print("🔍 Fetching Foody.vn page...")
    print(f"URL: {url}\n")
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        try:
            response = await client.get(url, headers=headers)
            print(f"✅ Status: {response.status_code}")
            print(f"✅ Content-Type: {response.headers.get('content-type')}")
            print(f"✅ Content-Length: {len(response.text)} bytes\n")
            
            # Save raw HTML
            with open("foody_debug.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            print("✅ Saved raw HTML to foody_debug.html\n")
            
            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Try different selectors
            selectors = [
                ".item-food",
                ".row-item",
                ".item-restaurant",
                "[class*='item']",
                ".microsite-item",
                ".fd-item",
            ]
            
            print("🔍 Testing CSS selectors:\n")
            for selector in selectors:
                items = soup.select(selector)
                print(f"  {selector:30s} → {len(items)} items")
            
            print("\n" + "="*60)
            print("🔍 Analyzing page structure...")
            print("="*60 + "\n")
            
            # Find all divs with 'item' in class name
            all_items = soup.find_all("div", class_=lambda x: x and "item" in x.lower())
            print(f"Found {len(all_items)} divs with 'item' in class name\n")
            
            if all_items:
                print("First 3 items class names:")
                for i, item in enumerate(all_items[:3], 1):
                    print(f"  [{i}] {item.get('class')}")
                
                print("\n" + "="*60)
                print("🔍 First item HTML structure:")
                print("="*60 + "\n")
                print(all_items[0].prettify()[:1000])
                print("\n... (truncated)")
            
            # Try to find restaurant names
            print("\n" + "="*60)
            print("🔍 Looking for restaurant names...")
            print("="*60 + "\n")
            
            name_selectors = [
                "h3",
                ".title",
                ".name",
                "[class*='title']",
                "[class*='name']",
                "a[title]",
            ]
            
            for selector in name_selectors:
                elements = soup.select(selector)[:5]
                if elements:
                    print(f"\n{selector}:")
                    for elem in elements:
                        text = elem.get_text(strip=True)
                        if text and len(text) > 3:
                            print(f"  - {text[:80]}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_foody())
