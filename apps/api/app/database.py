from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from redis.asyncio import Redis
from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Redis connection
redis_client: Redis | None = None


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def get_redis() -> Redis | None:
    """Get Redis client, returns None if Redis is not available"""
    global redis_client
    if redis_client is None:
        try:
            redis_client = Redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            await redis_client.ping()
        except Exception:
            redis_client = None
    return redis_client


async def init_db():
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        print("[OK] Database connected")
    except Exception as e:
        print(f"[WARN] Database not available: {e}")
        print("   API will start but DB-dependent features won't work.")


async def close_redis():
    """Close Redis connection"""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
