import logging
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from app.config import settings

logger = logging.getLogger(__name__)

_client: QdrantClient | None = None

VECTOR_SIZE = 1024


def get_qdrant_client(url: str | None = None) -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=url or settings.QDRANT_URL, timeout=10)
    return _client


def init_collection(client: QdrantClient | None = None, collection: str | None = None):
    client = client or get_qdrant_client()
    name = collection or settings.QDRANT_COLLECTION

    collections = [c.name for c in client.get_collections().collections]
    if name not in collections:
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        logger.info("Created Qdrant collection '%s' (%d dims, cosine)", name, VECTOR_SIZE)
    else:
        logger.info("Qdrant collection '%s' already exists", name)
