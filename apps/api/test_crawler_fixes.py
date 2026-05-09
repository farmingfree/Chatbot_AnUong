"""
Test script to verify crawler fixes for:
1. Place ID extraction
2. Review content extraction (null, duplicates, truncation)
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import re

# Test place_id extraction
def test_place_id_extraction():
    print("=== Testing Place ID Extraction ===\n")

    test_urls = [
        # Format 1: ChIJ in path
        "https://www.google.com/maps/place/Ph%E1%BB%9F+H%C3%B9ng/ChIJabcdef123456",
        # Format 2: ChIJ in query
        "https://www.google.com/maps/place/@10.764889,106.687705,17z/data=!3m1!4b1!4m6!3m5!1s0x31752f1c06785a4f:0x123456!8m2!3d10.764889!4d106.687705!16s%2Fg%2F11ChIJabcdef123456",
        # Format 3: ftid parameter
        "https://www.google.com/maps/place/Pho+Hung/@10.764889,106.687705?ftid=0x31752f1c06785a4f:0x123456",
        # Format 4: Real URL pattern
        "https://www.google.com/maps/place/Ph%E1%BB%9F+H%C3%B9ng/@10.764889,106.687705,17z",
    ]

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

    for url in test_urls:
        place_id = extract_place_id(url)
        print(f"URL: {url[:80]}...")
        print(f"Place ID: {place_id}")
        print()

async def test_review_extraction():
    print("\n=== Testing Review Extraction ===\n")
    print("Testing with real Google Maps page...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Test with a known place
            test_url = "https://www.google.com/maps/search/pho+district+1+ho+chi+minh"
            print(f"Navigating to: {test_url}")
            await page.goto(test_url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)

            # Get first result
            place_links = await page.locator('div[role="feed"] a[href*="google.com/maps/place"]').all()
            if not place_links:
                print("No results found")
                return

            first_link = await place_links[0].get_attribute('href')
            print(f"Testing first result: {first_link[:80]}...")

            await page.goto(first_link, wait_until='networkidle', timeout=20000)
            await asyncio.sleep(1.5)

            # Extract place name
            name = None
            try:
                name = (await page.locator('h1').first.text_content(timeout=5000) or '').strip()
                print(f"Place: {name}")
            except:
                print("Could not extract name")
                return

            # Extract reviews with improved logic
            reviews = []
            try:
                # Click reviews tab
                await page.locator('button[aria-label*="review"]').first.click(timeout=3000)
                await asyncio.sleep(2)
                print("Clicked reviews tab")

                # Scroll reviews panel
                reviews_panel = page.locator('div[role="main"]').first
                for i in range(2):
                    try:
                        await reviews_panel.evaluate('el => el.scrollBy(0, 500)')
                        await asyncio.sleep(0.5)
                        print(f"Scrolled reviews panel ({i+1}/2)")
                    except:
                        pass

                review_elements = await page.locator('div[data-review-id]').all()
                print(f"Found {len(review_elements)} review elements")

                for idx, el in enumerate(review_elements[:5]):
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
                                print(f"  Review {idx+1}: Clicked 'More' button")
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
                                        print(f"  Review {idx+1}: Found content with selector '{selector}'")
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
                            reviews.append({
                                'author_name': author,
                                'rating': r_val,
                                'review_text': content if content and len(content) > 5 else None,
                            })
                            print(f"  Review {idx+1}: author={author}, rating={r_val}, content_len={len(content) if content else 0}")
                    except Exception as e:
                        print(f"  Review {idx+1}: Error - {e}")
            except Exception as e:
                print(f"Reviews panel error: {e}")

            print(f"\nExtracted {len(reviews)} reviews")
            print("\nReview Quality:")
            null_content = sum(1 for r in reviews if r['review_text'] is None)
            has_content = sum(1 for r in reviews if r['review_text'] is not None)
            print(f"  With content: {has_content}/{len(reviews)}")
            print(f"  Null content: {null_content}/{len(reviews)}")

            # Check for duplicates
            contents = [r['review_text'] for r in reviews if r['review_text']]
            duplicates = len(contents) - len(set(contents))
            print(f"  Duplicates: {duplicates}")

            # Show sample reviews
            print("\nSample Reviews:")
            for i, r in enumerate(reviews[:3]):
                print(f"\n  Review {i+1}:")
                print(f"    Author: {r['author_name']}")
                print(f"    Rating: {r['rating']}")
                content_preview = r['review_text'][:100] if r['review_text'] else "NULL"
                print(f"    Content: {content_preview}...")

        finally:
            await browser.close()

if __name__ == '__main__':
    test_place_id_extraction()
    asyncio.run(test_review_extraction())
