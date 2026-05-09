import asyncio, json, traceback
from pathlib import Path
from app.database import engine
from app.models import Base
from sqlalchemy import text
OUT=Path(r"C:\Users\admin\Documents\chatbot_anuong\apps\api\crawl_proof_e2e\create_all_debug.json")
async def main():
    res={}
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            await conn.run_sync(Base.metadata.create_all)
        res["ok"]=True
        res["tables"]=list(Base.metadata.tables.keys())
    except Exception as e:
        res["ok"]=False
        res["error"]=str(e)
        res["trace"]=traceback.format_exc()
        res["tables"]=list(Base.metadata.tables.keys())
    OUT.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
asyncio.run(main())
