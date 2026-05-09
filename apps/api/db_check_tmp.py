import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal

async def main():
    try:
        async with AsyncSessionLocal() as db:
            places = (await db.execute(text('SELECT COUNT(*) FROM places'))).scalar()
            reviews = (await db.execute(text('SELECT COUNT(*) FROM reviews'))).scalar()
            fake = (await db.execute(text("SELECT COUNT(*) FROM places WHERE google_place_id LIKE 'ChIJstatic%' OR name LIKE '%#%'"))).scalar()
            print(f'DB_CONNECTED places={places} reviews={reviews} fake_like={fake}')
    except Exception as e:
        print('DB_ERROR', type(e).__name__, str(e))

asyncio.run(main())
