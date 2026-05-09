import asyncio, json, uuid, traceback
from pathlib import Path
from sqlalchemy import text
from app.database import AsyncSessionLocal
OUT=Path(r"C:\Users\admin\Documents\chatbot_anuong\apps\api\crawl_proof_e2e")

def safe_json(v): return json.dumps(v, ensure_ascii=False) if v is not None else None

async def main():
    res=json.loads((OUT/'run_result.json').read_text(encoding='utf-8'))
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("ALTER TABLE places ADD COLUMN IF NOT EXISTS name_normalized VARCHAR(255)"))
            await db.execute(text("ALTER TABLE places ADD COLUMN IF NOT EXISTS source_data JSONB"))
            inserted=[]
            for p in res['places'][:10]:
                if p.get('lat') is None or p.get('lng') is None:
                    continue
                pid=str(uuid.uuid4())
                await db.execute(text("""
                    INSERT INTO places (id,name,name_normalized,address,lat,lng,geom,phone,rating_google,review_count,image_urls,district,is_closed,data_quality_score,source_data,created_at)
                    VALUES (:id,:name,:name_normalized,:address,:lat,:lng,ST_SetSRID(ST_MakePoint(:lng,:lat),4326),:phone,:rating,:review_count,CAST(:image_urls AS json),:district,false,0.9,CAST(:source_data AS jsonb),now())
                """), {
                    'id':pid,'name':p['name'],'name_normalized':p['name'].lower(),'address':p.get('address'),'lat':p['lat'],'lng':p['lng'],'phone':p.get('phone'),
                    'rating':p.get('rating'),'review_count':p.get('review_count') or 0,'image_urls':safe_json(p.get('image_urls') or []),'district':p.get('district') or 'Quận 1',
                    'source_data':safe_json({'source':'google_maps_playwright_e2e','source_id':p.get('source_id'),'url':p.get('url')})
                })
                inserted.append(pid)
            if inserted and res.get('reviews'):
                for r in res['reviews'][:24]:
                    await db.execute(text("""
                        INSERT INTO reviews (id,place_id,source,author_name,rating,content,published_at,crawled_at)
                        VALUES (:id,:place_id,'google_maps_playwright_e2e',:author,:rating,:content,NULL,now())
                    """), {'id':str(uuid.uuid4()), 'place_id':inserted[0], 'author':r.get('author_name'), 'rating':r.get('rating'), 'content':r.get('review_text')})
            await db.commit()
            rows=(await db.execute(text("SELECT id::text,name,address,lat,lng,rating_google,review_count,source_data->>'source' AS source FROM places WHERE id=ANY(:ids::uuid[])"), {'ids':inserted})).mappings().all()
            reviews=(await db.execute(text("SELECT author_name,rating,content FROM reviews WHERE place_id=:pid LIMIT 20"), {'pid': inserted[0] if inserted else None})).mappings().all()
            counts=(await db.execute(text("SELECT COUNT(*) FILTER (WHERE source_data->>'source'='google_maps_playwright_e2e') AS real_crawl, COUNT(*) FILTER (WHERE google_place_id LIKE 'ChIJstatic%' OR name LIKE '%#%') AS fake_like FROM places"))).mappings().first()
            res['inserted_db_rows']=[dict(x) for x in rows]
            res['inserted_review_rows']=[dict(x) for x in reviews]
            res['db_counts']=dict(counts)
            res['db_insert_failure']=None
    except Exception as e:
        res['db_insert_failure']={'error':str(e),'trace':traceback.format_exc()}
    (OUT/'run_result_db_inserted.json').write_text(json.dumps(res, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
asyncio.run(main())
