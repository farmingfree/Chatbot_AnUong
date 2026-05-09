import asyncio
import json
import re
import time
import traceback
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path(r"C:\Users\admin\Documents\chatbot_anuong\apps\api\crawl_proof")
OUT.mkdir(exist_ok=True)

QUERY = "pho district 1 hcm"
SEARCH_URL = "https://www.google.com/maps/search/" + QUERY.replace(" ", "+")

async def main():
    start = time.time()
    result = {"query": QUERY, "search_url": SEARCH_URL, "places": [], "reviews": [], "failures": []}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        ctx = await browser.new_context(locale="en-US", timezone_id="Asia/Ho_Chi_Minh", viewport={"width": 1366, "height": 900})
        page = await ctx.new_page()
        page.set_default_timeout(20000)
        try:
            await page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(6000)
            await page.screenshot(path=str(OUT / "01_search_page.png"), full_page=True)
            # try consent
            for txt in ["Accept all", "I agree", "Reject all"]:
                try:
                    btn = page.get_by_text(txt, exact=False).first
                    if await btn.count():
                        await btn.click(timeout=3000)
                        await page.wait_for_timeout(2000)
                        break
                except Exception:
                    pass

            # Scroll results panel / page to load cards
            for _ in range(12):
                await page.mouse.wheel(0, 1200)
                await page.wait_for_timeout(900)
                await page.evaluate("""() => { const feed = document.querySelector('[role="feed"]'); if (feed) feed.scrollTop = feed.scrollHeight; }""")
                await page.wait_for_timeout(900)

            urls = await page.evaluate("""() => Array.from(new Set(Array.from(document.querySelectorAll('a[href*="/maps/place/"]')).map(a => a.href))).slice(0, 12)""")
            result["place_urls"] = urls
            (OUT / "place_urls.json").write_text(json.dumps(urls, ensure_ascii=False, indent=2), encoding="utf-8")

            for i, url in enumerate(urls[:10], 1):
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    await page.wait_for_timeout(5000)
                    if i == 1:
                        await page.screenshot(path=str(OUT / "02_place_detail_page.png"), full_page=True)
                    data = await page.evaluate("""() => {
                        const text = (sel) => document.querySelector(sel)?.textContent?.trim() || null;
                        const attr = (sel, name) => document.querySelector(sel)?.getAttribute(name) || null;
                        const name = text('h1');
                        const body = document.body.innerText;
                        const ratingMatch = body.match(/\b([0-9]\.[0-9])\s*\(?([0-9,]+)?\)?/);
                        const addressBtn = Array.from(document.querySelectorAll('button, [role="button"]')).find(e => (e.getAttribute('data-item-id')||'').includes('address') || (e.getAttribute('aria-label')||'').includes('Address'));
                        const phoneBtn = Array.from(document.querySelectorAll('button, [role="button"]')).find(e => (e.getAttribute('data-item-id')||'').includes('phone') || (e.getAttribute('aria-label')||'').includes('Phone'));
                        const websiteA = Array.from(document.querySelectorAll('a')).find(e => (e.getAttribute('data-item-id')||'').includes('authority') || (e.getAttribute('aria-label')||'').includes('Website'));
                        const imgs = Array.from(new Set(Array.from(document.querySelectorAll('img[src*="googleusercontent"]')).map(i => i.src))).slice(0,5);
                        return {
                          name,
                          bodyPreview: body.slice(0, 2000),
                          ratingText: ratingMatch ? ratingMatch[0] : null,
                          address: addressBtn ? ((addressBtn.getAttribute('aria-label')||addressBtn.textContent||'').replace(/^Address:\s*/,'').trim()) : null,
                          phone: phoneBtn ? ((phoneBtn.getAttribute('aria-label')||phoneBtn.textContent||'').replace(/^Phone:\s*/,'').trim()) : null,
                          website: websiteA ? websiteA.href : null,
                          image_urls: imgs,
                          url: location.href
                        };
                    }""")
                    coord = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", page.url)
                    if coord:
                        data["lat"] = float(coord.group(1)); data["lng"] = float(coord.group(2))
                    rating = re.search(r"(\d\.\d)", data.get("ratingText") or "")
                    reviews = re.search(r"\(?([0-9,]{2,})\)?", data.get("ratingText") or "")
                    data["rating"] = float(rating.group(1)) if rating else None
                    data["review_count"] = int(reviews.group(1).replace(',', '')) if reviews else None
                    result["places"].append(data)
                    (OUT / f"place_{i:02d}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

                    # open reviews for first place
                    if i == 1:
                        try:
                            candidates = await page.locator('button').all()
                            for b in candidates:
                                label = (await b.get_attribute('aria-label')) or ''
                                txt = ''
                                try: txt = await b.inner_text(timeout=1000)
                                except Exception: pass
                                if 'review' in label.lower() or 'review' in txt.lower():
                                    await b.click(timeout=5000)
                                    await page.wait_for_timeout(4000)
                                    await page.screenshot(path=str(OUT / "03_review_modal.png"), full_page=True)
                                    break
                            review_data = await page.evaluate("""() => Array.from(document.querySelectorAll('[data-review-id]')).slice(0,10).map(el => ({
                                author_name: el.querySelector('.d4r55')?.textContent?.trim() || el.querySelector('[class*="fontHeadlineSmall"]')?.textContent?.trim() || null,
                                rating_text: el.querySelector('[role="img"][aria-label*="star"]')?.getAttribute('aria-label') || null,
                                review_text: el.querySelector('.wiI7pd')?.textContent?.trim() || null,
                                published_time: el.querySelector('.rsqaWe')?.textContent?.trim() || null
                            }))""")
                            result["reviews"] = review_data
                            (OUT / "reviews_first_place.json").write_text(json.dumps(review_data, ensure_ascii=False, indent=2), encoding="utf-8")
                        except Exception as e:
                            result["failures"].append({"stage":"reviews", "error":str(e), "trace":traceback.format_exc()})
                except Exception as e:
                    result["failures"].append({"stage":"place", "url":url, "error":str(e), "trace":traceback.format_exc()})
        except Exception as e:
            result["failures"].append({"stage":"search", "error":str(e), "trace":traceback.format_exc()})
        finally:
            result["duration_sec"] = round(time.time()-start, 2)
            (OUT / "run_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            await browser.close()

asyncio.run(main())
