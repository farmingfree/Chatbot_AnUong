import asyncio, json
from sqlalchemy import text
from app.database import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as db:
        # Get real crawled places
        places = (await db.execute(text("""
            SELECT id::text, name, address, lat, lng, rating_google, review_count,
                   source_data->>'source' AS source
            FROM places
            WHERE source_data->>'source' = 'google_maps_playwright_e2e'
            LIMIT 10
        """))).mappings().all()

        # Get reviews for first place
        reviews = []
        if places:
            reviews = (await db.execute(text("""
                SELECT author_name, rating, content
                FROM reviews
                WHERE place_id = :pid
                LIMIT 5
            """), {'pid': places[0]['id']})).mappings().all()

        # Get counts
        counts = (await db.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE source_data->>'source' = 'google_maps_playwright_e2e') AS real_crawl,
                COUNT(*) FILTER (WHERE google_place_id LIKE 'ChIJstatic%' OR name LIKE '%#%') AS fake_like,
                COUNT(*) AS total
            FROM places
        """))).mappings().first()

        result = {
            'places': [dict(p) for p in places],
            'reviews': [dict(r) for r in reviews],
            'counts': dict(counts)
        }

        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

asyncio.run(main())
