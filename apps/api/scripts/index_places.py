"""
Index all places into Qdrant for semantic search.

Usage:
    python -m scripts.index_places              # Full reindex
    python -m scripts.index_places --place-id=UUID  # Single place
"""

import argparse
import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="Index places into Qdrant")
    parser.add_argument("--place-id", type=str, help="Index a single place by UUID")
    parser.add_argument("--qdrant-url", type=str, default=None, help="Qdrant URL override")
    args = parser.parse_args()

    from app.config import settings
    from app.database import AsyncSessionLocal
    from app.rag.embedder import Embedder
    from app.rag.client import get_qdrant_client, init_collection
    from app.rag.indexer import index_all_places, index_place

    qdrant_url = args.qdrant_url or settings.QDRANT_URL
    embedder = Embedder(settings.EMBEDDING_MODEL)
    qdrant = get_qdrant_client(qdrant_url)
    init_collection(qdrant, settings.QDRANT_COLLECTION)

    async with AsyncSessionLocal() as db:
        if args.place_id:
            logger.info("Indexing single place: %s", args.place_id)
            ok = await index_place(args.place_id, db, embedder, qdrant)
            if ok:
                logger.info("Done — indexed 1 place")
            else:
                logger.error("Place not found: %s", args.place_id)
                sys.exit(1)
        else:
            logger.info("Starting full reindex...")
            count = await index_all_places(db, embedder, qdrant)
            logger.info("Done — indexed %d places", count)


if __name__ == "__main__":
    asyncio.run(main())
