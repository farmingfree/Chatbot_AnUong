import asyncio
from sqlalchemy import text
from app.database import engine
from app.models import Base


async def create_tables():
    async with engine.begin() as conn:
        # Create PostGIS extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        # Create indexes (handled by model __table_args__ but explicit for clarity)
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_places_geom ON places USING GIST(geom)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_places_district ON places(district, is_closed)"
        ))
    print("✅ All tables and indexes created successfully!")


if __name__ == "__main__":
    asyncio.run(create_tables())
