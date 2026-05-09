"""
Live crawl runner - crawls multiple queries to build a real test dataset.
Targets 20+ places across different categories for validation.
"""
import asyncio, json, uuid, traceback, time
from pathlib import Path
from playwright.async_api import async_playwright
from app.database import AsyncSessionLocal
from data_pipeline.utils.stealth import StealthBrowser
from sqlalchemy import text

OUT = Path(r"C:\Users\admin\Documents\chatbot_anuong\apps\api\data\validation_reports")
OUT.mkdir(parents=True, exist_ok=True)

QUERIES = [
    "pho district 1 ho chi minh",
    "bun bo hue district 3 saigon",
    "banh mi quan 1 hcm",
    "com tam saigon district 1",
]

def safe_json(v):
    return json.dumps(v, ensure_ascii=False) if v is not None else None

def extract_coords_from_url(url: str):
    import re
    # @lat,lng pattern
    m = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', url)
    if m:
        return float(m.group(1)), float(m.group(2))
    # !3d!4d pattern
    m = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', url)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None, None

def extract_place_id(url: str):
    import re
    # Try multiple patterns for place_id extraction
    # Pattern 1: !19s segment (most common in current Google Maps URLs)
    m = re.search(r'!19s(ChIJ[\w-]+)', url)
    if m:
        return m.group(1)
    # Pattern 2: ChIJ format in URL path
    m = re.search(r'place/[^/]+/(ChIJ[\w-]+)', url)
    if m:
        return m.group(1)
    # Pattern 3: ChIJ anywhere in URL
    m = re.search(r'(ChIJ[\w-]+)', url)
    if m:
        return m.group(1)
    # Pattern 4: ftid parameter
    m = re.search(r'ftid=(0x[0-9a-f]+:0x[0-9a-f]+)', url, re.IGNORECASE)
    if m:
        return m.group(1)
    return None

def extract_cid(url: str):
    import re
    m = re.search(r'(0x[0-9a-f]+:0x[0-9a-f]+)', url, re.IGNORECASE)
    return m.group(1) if m else None

def extract_district(address: str):
    import re
    if not address:
        return 'Quận 1'
    m = re.search(r'(Qu[aậ]n\s+\d+)', address, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r'(B[iì]nh Th[aạ]nh|T[aâ]n B[iì]nh|T[aâ]n Ph[uú]|Ph[uú] Nhu[aậ]n|G[oò] V[aấ]p|B[iì]nh T[aâ]n|Th[uủ] D[uứ]c)', address, re.IGNORECASE)
    if m:
        return m.group(1)
    return 'Quận 1'

async def crawl_one_query(page, query: str, limit=6):
    """Crawl one query and return place data."""
    import re
    results = []
    search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"

    print(f"  Searching: {query}")
    try:
        await page.goto(search_url, wait_until='networkidle', timeout=30000)
        await asyncio.sleep(2)
    except Exception as e:
        print(f"  Navigation failed: {e}")
        return results

    # Get URLs from result list
    place_links = await page.locator('div[role="feed"] a[href*="google.com/maps/place"]').all()
    urls = []
    for link in place_links[:limit*2]:
        href = await link.get_attribute('href')
        if href and href not in urls:
            urls.append(href)

    print(f"  Found {len(urls)} URLs, crawling {min(limit, len(urls))}")

    for url in urls[:limit]:
        try:
            await page.goto(url, wait_until='networkidle', timeout=20000)
            await asyncio.sleep(1.5)

            # Extract name
            name = None
            try:
                name = (await page.locator('h1').first.text_content(timeout=5000) or '').strip()
            except:
                pass
            if not name:
                continue

            # Extract address
            address = None
            try:
                btn = page.locator('button[data-item-id="address"]')
                address = (await btn.locator('div.fontBodyMedium').first.text_content(timeout=3000) or '').strip()
            except:
                pass

            # Extract coordinates from current URL
            current_url = page.url
            lat, lng = extract_coords_from_url(current_url)

            # Extract rating
            rating = None
            try:
                r_text = (await page.locator('div.fontDisplayLarge').first.text_content(timeout=3000) or '').strip()
                m = re.search(r'(\d+[.,]\d+)', r_text)
                if m:
                    rating = float(m.group(1).replace(',', '.'))
                    if not (0 <= rating <= 5):
                        rating = None
            except:
                pass

            # Extract review count
            review_count = 0
            try:
                rc_btn = page.locator('button[aria-label*="review"]').first
                rc_text = await rc_btn.text_content(timeout=3000)
                m = re.search(r'([\d,\.]+)', rc_text or '')
                if m:
                    review_count = int(m.group(1).replace(',','').replace('.',''))
            except:
                pass

            # Extract phone
            phone = None
            try:
                ph_btn = page.locator('button[data-item-id*="phone"]')
                ph_text = await ph_btn.locator('div.fontBodyMedium').first.text_content(timeout=3000)
                if ph_text:
                    phone = re.sub(r'[^\d+\-\s()]', '', ph_text.strip())[:20]
            except:
                pass

            # Extract images
            image_urls = []
            try:
                imgs = await page.locator('button img[src*="googleusercontent"]').all()
                for img in imgs[:5]:
                    src = await img.get_attribute('src')
                    if src and 'lh3.googleusercontent' in src:
                        image_urls.append(src)
            except:
                pass

            # Extract reviews with improved content extraction
            reviews = []
            try:
                # Click reviews tab
                await page.locator('button[aria-label*="review"]').first.click(timeout=3000)
                await asyncio.sleep(2)

                # Scroll reviews panel to load more
                reviews_panel = page.locator('div[role="main"]').first
                for _ in range(2):
                    try:
                        await reviews_panel.evaluate('el => el.scrollBy(0, 500)')
                        await asyncio.sleep(0.5)
                    except:
                        pass

                review_elements = await page.locator('div[data-review-id]').all()
                for el in review_elements[:10]:
                    try:
                        # Extract author
                        author = None
                        try:
                            author = (await el.locator('div.d4r55').text_content(timeout=2000) or '').strip()
                        except:
                            pass

                        # Extract content with multiple fallback selectors
                        content = None
                        try:
                            # Try "More" button first to expand truncated reviews
                            more_btn = el.locator('button[aria-label*="More"]')
                            if await more_btn.count() > 0:
                                await more_btn.first.click(timeout=1000)
                                await asyncio.sleep(0.3)
                        except:
                            pass

                        # Try multiple content selectors
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
                        rating_span = el.locator('span[aria-label*="star"]')
                        r_val = None
                        try:
                            r_label = await rating_span.get_attribute('aria-label', timeout=2000)
                            if r_label:
                                m = re.search(r'(\d+)', r_label)
                                if m:
                                    r_val = float(m.group(1))
                        except:
                            pass

                        # Only add review if we have author (content can be null for rating-only reviews)
                        if author:
                            reviews.append({
                                'author_name': author,
                                'rating': r_val,
                                'review_text': content if content and len(content) > 5 else None,
                            })
                    except Exception as e:
                        print(f"    ! Review extraction error: {e}")
                        pass
            except Exception as e:
                print(f"    ! Reviews panel error: {e}")
                pass

            google_place_id = extract_place_id(url)  # Use original URL, not current_url
            google_cid = extract_cid(current_url)

            place_data = {
                'name': name,
                'address': address,
                'lat': lat,
                'lng': lng,
                'rating': rating,
                'review_count': review_count,
                'phone': phone,
                'image_urls': image_urls,
                'url': current_url,
                'google_place_id': google_place_id,
                'google_cid': google_cid,
                'district': extract_district(address),
                'reviews': reviews,
                'query': query,
            }
            results.append(place_data)
            print(f"  + {name} ({lat}, {lng}) rating={rating} reviews={review_count}")
            await asyncio.sleep(1.5)

        except Exception as e:
            print(f"  ! Error on place: {e}")
            continue

    return results

async def main():
    all_places = []
    all_reviews = []
    start = time.time()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            for query in QUERIES:
                places = await crawl_one_query(page, query, limit=6)
                all_places.extend(places)
                await asyncio.sleep(3)  # inter-query delay
        finally:
            await browser.close()

    duration = time.time() - start
    print(f"\nCrawled {len(all_places)} places in {duration:.1f}s")

    # Insert into DB
    inserted_place_ids = []
    db_failures = []

    async with AsyncSessionLocal() as db:
        for p in all_places:
            if p['lat'] is None or p['lng'] is None:
                print(f"  SKIP (no coords): {p['name']}")
                continue

            # Dedup by google_place_id
            if p['google_place_id']:
                exists = (await db.execute(text(
                    "SELECT id::text FROM places WHERE google_place_id = :pid"
                ), {'pid': p['google_place_id']})).scalar()
                if exists:
                    print(f"  DEDUP: {p['name']}")
                    inserted_place_ids.append(exists)
                    continue

            pid = str(uuid.uuid4())
            try:
                await db.execute(text("""
                    INSERT INTO places (
                        id, name, name_normalized, address, lat, lng, geom,
                        phone, rating_google, review_count, image_urls, district,
                        is_closed, data_quality_score, source_data,
                        google_place_id, validation_status, extraction_version, created_at
                    ) VALUES (
                        :id, :name, :name_norm, :address, :lat, :lng,
                        ST_SetSRID(ST_MakePoint(:lng, :lat), 4326),
                        :phone, :rating, :review_count, CAST(:image_urls AS json), :district,
                        false, 0.9, CAST(:source_data AS jsonb),
                        :google_place_id, 'pending', '2.0-live', now()
                    )
                    ON CONFLICT (google_place_id) WHERE google_place_id IS NOT NULL
                    DO NOTHING
                """), {
                    'id': pid,
                    'name': p['name'],
                    'name_norm': p['name'].lower(),
                    'address': p['address'],
                    'lat': p['lat'],
                    'lng': p['lng'],
                    'phone': p['phone'],
                    'rating': p['rating'],
                    'review_count': p['review_count'] or 0,
                    'image_urls': safe_json(p['image_urls'] or []),
                    'district': p['district'],
                    'google_place_id': p['google_place_id'],
                    'source_data': safe_json({
                        'source': 'google_maps_v2',
                        'query': p['query'],
                        'url': p['url'],
                        'google_cid': p['google_cid'],
                    }),
                })
                inserted_place_ids.append(pid)
                all_reviews.extend([{**r, 'place_id': pid} for r in p.get('reviews', [])])
            except Exception as e:
                db_failures.append({'name': p['name'], 'error': str(e)})
                print(f"  DB ERR {p['name']}: {e}")

        # Insert reviews
        review_count = 0
        for r in all_reviews[:200]:
            try:
                await db.execute(text("""
                    INSERT INTO reviews (id, place_id, source, author_name, rating, content, crawled_at)
                    VALUES (:id, :pid, 'google_maps_v2', :author, :rating, :content, now())
                """), {
                    'id': str(uuid.uuid4()),
                    'pid': r['place_id'],
                    'author': r.get('author_name'),
                    'rating': r.get('rating'),
                    'content': r.get('review_text'),
                })
                review_count += 1
            except Exception as e:
                pass

        await db.commit()

    result = {
        'duration_sec': round(duration, 2),
        'places_crawled': len(all_places),
        'places_with_coords': sum(1 for p in all_places if p['lat']),
        'places_inserted': len(inserted_place_ids),
        'reviews_inserted': review_count,
        'db_failures': db_failures,
        'places': all_places,
    }

    out_file = OUT / "live_crawl_result.json"
    out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print(f"\nSaved to {out_file}")
    print(f"Inserted: {len(inserted_place_ids)} places, {review_count} reviews")
    if db_failures:
        print(f"DB failures: {len(db_failures)}")

asyncio.run(main())
