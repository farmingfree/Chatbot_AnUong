import asyncio, json, traceback
from pathlib import Path
from sqlalchemy import text
from app.database import engine
from app.models import Base
OUT=Path(r"C:\Users\admin\Documents\chatbot_anuong\apps\api\crawl_proof_e2e\db_fix.json")
async def main():
    res={}
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        async with engine.begin() as conn:
            await conn.execute(text("DROP INDEX IF EXISTS idx_places_geom"))
            await conn.execute(text("DROP INDEX IF EXISTS idx_places_district"))
        # avoid SQLAlchemy recreating duplicate orphan index during proof setup
        if 'places' in Base.metadata.tables:
            Base.metadata.tables['places'].indexes.clear()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        res["ok"]=True
    except Exception as e:
        res["ok"]=False; res["error"]=str(e); res["trace"]=traceback.format_exc()
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
asyncio.run(main())
