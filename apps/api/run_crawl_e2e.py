import asyncio
import json
import re
import time
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
from sqlalchemy import text
from app.database import AsyncSessionLocal, engine

OUT = Path(r"C:\Users\admin\Documents\chatbot_anuong\apps\api\crawl_proof_e2e")
OUT.mkdir(exist_ok=True)
QUERY = "pho district 1 hcm"
SEARCH_URL = "https://www.google.com/maps/search/" + QUERY.replace(" ", "+")

MOJIBAKE_FIX = [
    ("Nguyá»…n", "Nguyễn"), ("TrÃ£i", "Trãi"), ("Cáº§u", "Cầu"), ("Ã”ng", "Ông"), ("LÃ£nh", "Lãnh"),
    ("Há»“ ChÃ­ Minh", "Hồ Chí Minh"), ("Phá»Ÿ", "Phở"), ("Viá»‡t Nam", "Việt Nam"), ("PhÃº", "Phú"),
    ("VÆ°Æ¡ng", "Vương"), ("ThÃ¡i", "Thái"), ("BÃ¬nh", "Bình"), ("PhÆ°á»£ng", "Phượng"),
    ("Dáº­u", "Dậu"), ("Khá»Ÿi", "Khởi"), ("NghÄ©a", "Nghĩa"), ("Sá»‘", "Số"), ("HÃ  Ná»™i", "Hà Nội"),
    ("LÃª", "Lê"), ("Máº¡c", "Mạc"), ("Thá»‹", "Thị"), ("BÆ°á»Ÿi", "Bưởi"), ("An ÄÃ´ng", "An Đông"),
]

def clean(s):
    if not s: return s
    for a,b in MOJIBAKE_FIX: s=s.replace(a,b)
    return s

def parse_rating_count(body):
    # Google body typically has restaurant name then rating on separate line, e.g. "Pho Hung\n4.3\nPho restaurant"
    m = re.search(r"\n([1-5]\.\d)\n", body)
    rating = float(m.group(1)) if m else None
    count = None
    # Find count near "reviews" or fallback from full body
    cm = re.search(r"([0-9][0-9,]{1,})\s+reviews", body, re.I)
    if cm: count = int(cm.group(1).replace(',', ''))
    return rating, count

async def ensure_schema(db):
    await db.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    await db.execute(text("ALTER TABLE places ADD COLUMN IF NOT EXISTS name_normalized VARCHAR(255)"))
    await db.execute(text("ALTER TABLE places ADD COLUMN IF NOT EXISTS source_data JSONB"))
    await db.commit()

async def insert_place(db, p):
    pid = str(uuid.uuid4())
    await db.execute(text("""
        INSERT INTO places (
          id, name, name_normalized, address, lat, lng, geom, phone,
          rating_google, review_count, image_urls, district, is_closed, source_data, created_at
        ) VALUES (
          :id, :name, lower(:name), :address, :lat, :lng,
          ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), :phone,
          :rating, :review_count, :image_urls, :district, false, CAST(:source_data AS jsonb), now()
        )
    """), {
        "id": pid,
        "name": p["name"],
        "address": p.get("address"),
        "lat": p.get("lat"),
        "lng": p.get("lng"),
        "phone": p.get("phone"),
        "rating": p.get("rating"),
        "review_count": p.get("review_count") or 0,
        "image_urls": json.dumps(p.get("image_urls") or []),
        "district": p.get("district"),
        "source_data": json.dumps({"source":"google_maps_playwright_e2e", "source_id": p.get("source_id"), "url": p.get("url")}, ensure_ascii=False),
    })
    return pid

async def insert_reviews(db, place_id, reviews):
    for r in reviews:
        await db.execute(text("""
            INSERT INTO reviews (id, place_id, source, author_name, rating, content, published_at, crawled_at)
            VALUES (:id, :place_id, 'google_maps_playwright_e2e', :author, :rating, :content, NULL, now())
        """), {
            "id": str(uuid.uuid4()), "place_id": place_id,
            "author": r.get("author_name"), "rating": r.get("rating"), "content": r.get("review_text")
        })

async def main():
    started = time.time()
    result = {"query": QUERY, "search_url": SEARCH_URL, "places": [], "reviews": [], "failures": []}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = await browser.new_context(locale="en-US", timezone_id="Asia/Ho_Chi_Minh", viewport={"width":1366,"height":900}, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36")
        page = await ctx.new_page()
        page.set_default_timeout(25000)
        try:
            await page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(5000)
            await page.screenshot(path=str(OUT/"01_search_page.png"), full_page=True)
            for _ in range(18):
                await page.evaluate("""() => { const f=document.querySelector('[role="feed"]'); if(f) f.scrollTop=f.scrollHeight; else window.scrollBy(0,1000); }""")
                await page.mouse.wheel(0, 1000)
                await page.wait_for_timeout(700)
            urls = await page.evaluate("""() => Array.from(new Set(Array.from(document.querySelectorAll('a[href*="/maps/place/"]')).map(a=>a.href))).slice(0,55)""")
            result["place_urls"] = urls
            (OUT/"place_urls.json").write_text(json.dumps(urls, ensure_ascii=False, indent=2), encoding="utf-8")
            for i,url in enumerate(urls[:50],1):
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    await page.wait_for_timeout(3500)
                    if i==1: await page.screenshot(path=str(OUT/"02_place_detail_page.png"), full_page=True)
                    data = await page.evaluate("""() => {
                        const body=document.body.innerText;
                        const name=document.querySelector('h1')?.textContent?.trim() || null;
                        const addressBtn=Array.from(document.querySelectorAll('button,[role="button"]')).find(e=>(e.getAttribute('data-item-id')||'').includes('address') || (e.getAttribute('aria-label')||'').startsWith('Address:'));
                        const phoneBtn=Array.from(document.querySelectorAll('button,[role="button"]')).find(e=>(e.getAttribute('data-item-id')||'').includes('phone') || (e.getAttribute('aria-label')||'').startsWith('Phone:'));
                        const web=Array.from(document.querySelectorAll('a')).find(e=>(e.getAttribute('data-item-id')||'').includes('authority') || (e.getAttribute('aria-label')||'').includes('Website'));
                        const imgs=Array.from(new Set(Array.from(document.querySelectorAll('img[src*="googleusercontent"]')).map(i=>i.src))).slice(0,5);
                        return {name, body, address: addressBtn?((addressBtn.getAttribute('aria-label')||addressBtn.textContent||'').replace(/^Address:\\s*/,'').trim()):null, phone: phoneBtn?((phoneBtn.getAttribute('aria-label')||phoneBtn.textContent||'').replace(/^Phone:\\s*/,'').trim()):null, website:web?web.href:null, image_urls:imgs, url:location.href};
                    }""")
                    coord = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", page.url)
                    rating,count = parse_rating_count(data.get("body") or "")
                    item={"source_id": re.sub(r'[^A-Za-z0-9_:-]','_',url)[:180], "name": clean(data.get("name")), "address": clean(data.get("address")), "lat": float(coord.group(1)) if coord else None, "lng": float(coord.group(2)) if coord else None, "rating": rating, "review_count": count, "phone": data.get("phone"), "website": data.get("website"), "image_urls": data.get("image_urls"), "url": url, "district":"Quận 1"}
                    result["places"].append(item)
                    (OUT/f"place_{i:02d}.json").write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
                    if i==1:
                        try:
                            # click reviews tab/button
                            btns=await page.locator('button').all()
                            for b in btns:
                                label=(await b.get_attribute('aria-label')) or ''
                                txt=''
                                try: txt=await b.inner_text(timeout=500)
                                except Exception: pass
                                if 'review' in (label+txt).lower():
                                    await b.click(timeout=4000); await page.wait_for_timeout(4000); break
                            await page.screenshot(path=str(OUT/"03_review_modal.png"), full_page=True)
                            for _ in range(8):
                                await page.mouse.wheel(0, 1000); await page.wait_for_timeout(500)
                            reviews=await page.evaluate("""() => Array.from(document.querySelectorAll('[data-review-id]')).slice(0,80).map(el=>{
                                const ratingText=el.querySelector('[role="img"][aria-label*="star"]')?.getAttribute('aria-label')||'';
                                const rm=ratingText.match(/([1-5])/);
                                return {author_name: el.querySelector('.d4r55')?.textContent?.trim() || null, rating: rm?parseFloat(rm[1]):null, review_text: el.querySelector('.wiI7pd')?.textContent?.trim() || null, published_time: el.querySelector('.rsqaWe')?.textContent?.trim() || null};
                            }).filter(r=>r.author_name||r.review_text)""")
                            result["reviews"]=reviews
                            (OUT/"reviews_first_place.json").write_text(json.dumps(reviews, ensure_ascii=False, indent=2), encoding="utf-8")
                        except Exception as e:
                            result["failures"].append({"stage":"reviews", "error":str(e), "trace":traceback.format_exc()})
                except Exception as e:
                    result["failures"].append({"stage":"place", "url":url, "error":str(e), "trace":traceback.format_exc()})
        except Exception as e:
            result["failures"].append({"stage":"search", "error":str(e), "trace":traceback.format_exc()})
        finally:
            await browser.close()
    inserted=[]
    try:
        async with AsyncSessionLocal() as db:
            await ensure_schema(db)
            for idx,p in enumerate(result["places"][:50]):
                pid=await insert_place(db,p)
                p["db_id"]=pid
                inserted.append(pid)
                if idx==0 and result["reviews"]:
                    await insert_reviews(db,pid,result["reviews"][:500])
            await db.commit()
            dbrows=(await db.execute(text("""
                SELECT id::text,name,address,lat,lng,rating_google,review_count,source_data->>'source' AS source
                FROM places WHERE id = ANY(:ids::uuid[]) ORDER BY created_at DESC LIMIT 50
            """), {"ids": inserted})).mappings().all()
            revrows=(await db.execute(text("""
                SELECT author_name,rating,content FROM reviews WHERE place_id=:pid LIMIT 20
            """), {"pid": inserted[0] if inserted else None})).mappings().all()
            fake_count=(await db.execute(text("SELECT COUNT(*) FROM places WHERE source_data->>'source'='google_maps_playwright_e2e'"))).scalar()
            result["inserted_db_rows"]=[dict(r) for r in dbrows]
            result["inserted_review_rows"]=[dict(r) for r in revrows]
            result["google_maps_playwright_e2e_rows_total"]=fake_count
    except Exception as e:
        result["failures"].append({"stage":"db_insert", "error":str(e), "trace":traceback.format_exc()})
    result["duration_sec"]=round(time.time()-started,2)
    result["failure_count"]=len(result["failures"])
    result["place_count"]=len(result["places"])
    result["review_count_extracted"]=len(result["reviews"])
    (OUT/"run_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

asyncio.run(main())
