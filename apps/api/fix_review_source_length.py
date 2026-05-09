import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as db:
        await db.execute(text("ALTER TABLE reviews ALTER COLUMN source TYPE VARCHAR(50)"))
        await db.commit()
        print("✓ reviews.source column extended to VARCHAR(50)")

asyncio.run(main())
