"""
Database migration: Add v2 crawler validation fields.

Adds:
- google_cid (unique index)
- confidence_score
- extraction_method
- validation_status
- validation_flags (JSONB)
- extraction_version
- raw_payload (JSONB)
"""
import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal


async def migrate():
    """Add new columns for crawler v2."""
    async with AsyncSessionLocal() as db:
        print("Adding new columns for Google Maps Crawler v2...")

        # Add google_cid
        await db.execute(text("""
            ALTER TABLE places
            ADD COLUMN IF NOT EXISTS google_cid VARCHAR(100)
        """))
        print("+ Added google_cid")

        # Add confidence_score
        await db.execute(text("""
            ALTER TABLE places
            ADD COLUMN IF NOT EXISTS confidence_score FLOAT
        """))
        print("+ Added confidence_score")

        # Add extraction_method
        await db.execute(text("""
            ALTER TABLE places
            ADD COLUMN IF NOT EXISTS extraction_method VARCHAR(50)
        """))
        print("+ Added extraction_method")

        # Add validation_status
        await db.execute(text("""
            ALTER TABLE places
            ADD COLUMN IF NOT EXISTS validation_status VARCHAR(20) DEFAULT 'pending'
        """))
        print("+ Added validation_status")

        # Add validation_flags
        await db.execute(text("""
            ALTER TABLE places
            ADD COLUMN IF NOT EXISTS validation_flags JSONB
        """))
        print("+ Added validation_flags")

        # Add extraction_version
        await db.execute(text("""
            ALTER TABLE places
            ADD COLUMN IF NOT EXISTS extraction_version VARCHAR(20)
        """))
        print("+ Added extraction_version")

        # Add raw_payload
        await db.execute(text("""
            ALTER TABLE places
            ADD COLUMN IF NOT EXISTS raw_payload JSONB
        """))
        print("+ Added raw_payload")

        # Create unique index on google_cid
        await db.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_places_google_cid
            ON places(google_cid)
            WHERE google_cid IS NOT NULL
        """))
        print("+ Created unique index on google_cid")

        # Create index on google_place_id if not exists
        await db.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_places_google_place_id
            ON places(google_place_id)
            WHERE google_place_id IS NOT NULL
        """))
        print("+ Created unique index on google_place_id")

        # Create index on validation_status
        await db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_places_validation_status
            ON places(validation_status)
        """))
        print("+ Created index on validation_status")

        await db.commit()
        print("\n[OK] Migration complete!")


if __name__ == "__main__":
    asyncio.run(migrate())
