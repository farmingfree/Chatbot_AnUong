from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db, engine
from app.routers import places, dishes, users, chat
from app.routers import admin
from sqlalchemy import text

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    # Load RAG components (graceful — app works without them)
    try:
        from app.rag.embedder import Embedder
        from app.rag.client import get_qdrant_client, init_collection

        app.state.embedder = Embedder(settings.EMBEDDING_MODEL)
        app.state.qdrant = get_qdrant_client(settings.QDRANT_URL)
        init_collection(app.state.qdrant, settings.QDRANT_COLLECTION)
        logger.info("[OK] RAG components loaded (embedder + Qdrant)")
    except Exception as e:
        app.state.embedder = None
        app.state.qdrant = None
        logger.warning("[WARN] RAG not available: %s — falling back to keyword search", e)

    yield


app = FastAPI(title="Food Advisor API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(places.router)
app.include_router(dishes.router)
app.include_router(users.router)
app.include_router(chat.router)
app.include_router(admin.router)


@app.get("/health")
async def health_check():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    llm_providers = []
    if settings.OLLAMA_URL:
        llm_providers.append("ollama")
    if settings.GEMINI_API_KEY:
        llm_providers.append("gemini")
    if settings.OPENAI_API_KEY:
        llm_providers.append("openai")

    return {
        "status": "ok",
        "db": db_status,
        "llm_providers": llm_providers or ["rule-based"],
    }
