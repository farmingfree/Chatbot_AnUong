import logging
from sentence_transformers import SentenceTransformer

from app.config import settings

logger = logging.getLogger(__name__)


class Embedder:
    def __init__(self, model_name: str | None = None):
        name = model_name or settings.EMBEDDING_MODEL
        logger.info("Loading embedding model: %s", name)
        self.model = SentenceTransformer(name)
        logger.info("Embedding model loaded (dim=%d)", self.model.get_sentence_embedding_dimension())

    def encode(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return embeddings.tolist()

    def encode_query(self, query: str) -> list[float]:
        embedding = self.model.encode([query], normalize_embeddings=True, show_progress_bar=False)
        return embedding[0].tolist()
