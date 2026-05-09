"""
Quick test of improved crawler - single query to verify fixes.
"""
import asyncio, json, uuid
from pathlib import Path
from playwright.async_api import async_playwright
from app.database import AsyncSessionLocal
from sqlalchemy import text
import re

OUT = Path(r"C:\Users\admin\Documents\chatbot_anuong\apps\api\data\validation_reports")

def safe_json(v):
    return json.dumps(v, ensure_ascii=False) if v is not None else None

def extract_coords_from_url(url: str):
    m = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', url)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', url)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None, None

def extract_place_id(url: str):
    # Pattern 1: ChIJ format in URL path
    m = re.search(r'place/[^/]+/(ChIJ[\w-]+)', url)
    if m:
        return m.group(1)
    # Pattern 2: ChIJ anywhere in URL
    m = re.search(r'(ChIJ[\w-]+)', url)
    if m:
        return m.group(1)
    # Pattern 3: ftid parameter
    m = re.search(r'ftid=(0x[0-9a-f]+:0x[0-9a-f]+)', url, re.IGNORECASE)
    if m:
        return m.group(1)
    return None

def extract_cid(url: str):
    m = re.search(r'(0x[0-9a-f]+:0x[0-9a-f]+)', url, re.IGNORECASE)
    return m.group(1) if m else None

async def test_single_place():
    """Test crawler improvements on a single place."""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # visible for debugging
        page = await browser.new_page()

        try:
            # Search
            query = "pho hung district 1 ho chi minh"
            search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
            print(f"Searching: {query}")

            await page.goto(search_url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(3)

            # Get first result
            place_links = await page.locator('div[role="feed"] a[href*="google.com/maps/place"]').all()
            if not place_links:
                print("No results found")
                return None

            url = await place_links[0].get_attribute('href')
            print(f"Opening: {url[:80]}...")

            await page.goto(url, wait_until='networkidle', timeout=20000)
            await asyncio.sleep(2)

            # Extract name
            name = None
            try:
                name = (await page.locator('h1').first.text_content(timeout=5000) or '').strip()
                print(f"Name: {name}")
            except:
                print("Could not extract name")
                return None

            # Extract coordinates
            current_url = page.url
            lat, lng = extract_coords_from_url(current_url)
            print(f"Coords: ({lat}, {lng})")

            # Extract place_id
            google_place_id = extract_place_id(current_url)
            google_cid = extract_cid(current_url)
            print(f"Place ID: {google_place_id}")
            print(f"CID: {google_cid}")

            # Extract reviews with improved logic
            reviews = []
            try:
                print("\nExtracting reviews...")
                await page.locator('button[aria-label*="review"]').first.click(timeout=3000)
                await asyncio.sleep(2)

                # Scroll reviews panel
                reviews_panel = page.locator('div[role="main"]').first
                for i in range(2):
                    try:
                        await reviews_panel.evaluate('el => el.scrollBy(0, 500)')
                        await asyncio.sleep(0.5)
                    except:
                        pass

                review_elements = await page.locator('div[data-review-id]').all()
                print(f"Found {len(review_elements)} review elements")

                for idx, el in enumerate(review_elements[:10]):
                    try:
                        # Extract author
                        author = None
                        try:
                            author = (await el.locator('div.d4r55').text_content(timeout=2000) or '').strip()
                        except:
                            pass

                        # Try "More" button
                        try:
                            more_btn = el.locator('button[aria-label*="More"]')
                            if await more_btn.count() > 0:
                                await more_btn.first.click(timeout=1000)
                                await asyncio.sleep(0.3)
                        except:
                            pass

                        # Extract content with multiple selectors
                        content = None
                        content_selectors = [
                            'span.wiI7pd',
                            'div.MyEned span',
                            'div.MyEned',
                            'span[jsaction*="review"]',
                        ]
                        for selector in content_selectors:
                            try:
                                content_el = el.locator(selector).first
                                if await content_el.count() > 0:
                                    content = (await content_el.text_content(timeout=2000) or '').strip()
                                    if content and len(content) > 5:
                                        break
                            except:
                                continue

                        # Extract rating
                        r_val = None
                        try:
                            rating_span = el.locator('span[aria-label*="star"]')
                            r_label = await rating_span.get_attribute('aria-label', timeout=2000)
                            if r_label:
                                m = re.search(r'(\d+)', r_label)
                                if m:
                                    r_val = float(m.group(1))
                        except:
                            pass

                        if author:
                            review_data = {
                                'author_name': author,
                                'rating': r_val,
                                'review_text': content if content and len(content) > 5 else None,
                            }
                            reviews.append(review_data)

                            # Print review summary
                            content_preview = (content[:50] + '...') if content and len(content) > 50 else (content or 'NULL')
                            print(f"  Review {idx+1}: {author} | Rating: {r_val} | Content: {content_preview}")
                    except Exception as e:
                        print(f"  Review {idx+1}: Error - {e}")
                        pass
            except Exception as e:
                print(f"Reviews panel error: {e}")
                pass

            print(f"\nExtracted {len(reviews)} reviews")
            print(f"  - With content: {sum(1 for r in reviews if r['review_text'])}/{len(reviews)}")
            print(f"  - Null content: {sum(1 for r in reviews if not r['review_text'])}/{len(reviews)}")

            await asyncio.sleep(5)  # Keep browser open for inspection

        finally:
            await browser.close()

asyncio.run(test_single_place())
