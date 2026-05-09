import asyncio, json, traceback
from sqlalchemy import text
from app.database import AsyncSessionLocal, init_db
from pathlib import Path
OUT=Path(r"C:\Users\admin\Documents\chatbot_anuong\apps\api\crawl_proof_e2e\db_status.json")
async def main():
    res={}
    try:
        await init_db()
        async with AsyncSessionLocal() as db:
            res['tables']=(await db.execute(text("SELECT array_agg(tablename) FROM pg_tables WHERE schemaname='public'"))).scalar()
            res['places']=(await db.execute(text('SELECT COUNT(*) FROM places'))).scalar()
            res['reviews']=(await db.execute(text('SELECT COUNT(*) FROM reviews'))).scalar()
    except Exception as e:
        res={'error':str(e),'trace':traceback.format_exc()}
    OUT.write_text(json.dumps(res, indent=2, default=str), encoding='utf-8')
asyncio.run(main())
