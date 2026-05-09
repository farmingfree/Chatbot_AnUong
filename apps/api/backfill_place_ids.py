"""
Backfill google_place_id for existing places using the original URL.
"""
import asyncio
from app.database import AsyncSessionLocal
from sqlalchemy import text
import re

def extract_place_id(url: str):
    if not url:
        return None
    # Pattern 1: !19s segment (most common)
    m = re.search(r'!19s(ChIJ[\w-]+)', url)
    if m:
        return m.group(1)
    # Pattern 2: ChIJ in path
    m = re.search(r'place/[^/]+/(ChIJ[\w-]+)', url)
    if m:
        return m.group(1)
    # Pattern 3: ChIJ anywhere
    m = re.search(r'(ChIJ[\w-]+)', url)
    if m:
        return m.group(1)
    return None

async def main():
    async with AsyncSessionLocal() as db:
        # Get all places with URLs but no place_id
        rows = (await db.execute(text("""
            SELECT id::text, name, source_data->>'url' as url
            FROM places
            WHERE google_place_id IS NULL
              AND source_data->>'url' IS NOT NULL
        """))).fetchall()

        print(f"Found {len(rows)} places without place_id")

        updated = 0
        for row in rows:
            url = row.url
            place_id = extract_place_id(url)

            if place_id:
                try:
                    await db.execute(text("""
                        UPDATE places
                        SET google_place_id = :place_id
                        WHERE id = :id
                    """), {'place_id': place_id, 'id': row.id})
                    updated += 1
                    print(f"  OK: {place_id}")
                except Exception as e:
                    print(f"  ERR: {e}")
            else:
                print(f"  SKIP: No place_id in URL")

        await db.commit()
        print(f"\nUpdated {updated}/{len(rows)} places")

asyncio.run(main())
