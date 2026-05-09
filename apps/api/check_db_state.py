import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as db:
        counts = (await db.execute(text("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE source_data->>'source' IN ('google_maps_playwright_e2e', 'google_maps_v2')) as real
            FROM places
        """))).mappings().first()

        reviews = (await db.execute(text("SELECT COUNT(*) as total FROM reviews"))).scalar()

        print(f"Places: {counts['total']} total, {counts['real']} real crawled")
        print(f"Reviews: {reviews}")

asyncio.run(check())
