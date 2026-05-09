"""Index places into Qdrant for semantic search."""

import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from app.config import settings
from app.rag.embedder import Embedder
from app.rag.document import build_place_document, build_place_summary
from app.services.geo import is_open_now

logger = logging.getLogger(__name__)

BATCH_SIZE = 32

PLACES_WITH_DISHES_SQL = text("""
    SELECT
        p.id, p.name, p.district, p.lat, p.lng,
        p.price_min, p.price_max, p.price_level,
        p.rating_google, p.review_count,
        p.hours, p.features, p.is_closed,
        array_agg(DISTINCT d.name) FILTER (WHERE d.name IS NOT NULL) as dish_names
    FROM places p
    LEFT JOIN place_dishes pd ON pd.place_id = p.id
    LEFT JOIN dishes d ON d.id = pd.dish_id
    WHERE p.is_closed = false
    GROUP BY p.id
    ORDER BY p.id
""")

SINGLE_PLACE_SQL = text("""
    SELECT
        p.id, p.name, p.district, p.lat, p.lng,
        p.price_min, p.price_max, p.price_level,
        p.rating_google, p.review_count,
        p.hours, p.features, p.is_closed,
        array_agg(DISTINCT d.name) FILTER (WHERE d.name IS NOT NULL) as dish_names
    FROM places p
    LEFT JOIN place_dishes pd ON pd.place_id = p.id
    LEFT JOIN dishes d ON d.id = pd.dish_id
    WHERE p.id = :place_id
    GROUP BY p.id
""")


def _row_to_doc(row) -> tuple[str, str, dict]:
    dish_names = row.dish_names or []
    is_open = is_open_now(row.hours)

    doc_text = build_place_document(
        name=row.name,
        district=row.district,
        dish_names=dish_names,
        price_min=row.price_min,
        price_max=row.price_max,
        features=row.features,
        rating=row.rating_google,
        review_count=row.review_count,
    )

    summary = build_place_summary(
        name=row.name,
        district=row.district,
        dish_names=dish_names,
        price_min=row.price_min,
        price_max=row.price_max,
        rating=row.rating_google,
        is_open=is_open,
    )

    payload = {
        "place_id": str(row.id),
        "name": row.name,
        "district": row.district or "",
        "lat": row.lat,
        "lng": row.lng,
        "summary": summary,
        "dish_names": dish_names,
        "price_min": row.price_min,
        "price_max": row.price_max,
        "rating": row.rating_google,
        "review_count": row.review_count or 0,
    }

    return doc_text, summary, payload


async def index_all_places(
    db: AsyncSession,
    embedder: Embedder,
    qdrant: QdrantClient,
    collection: str | None = None,
):
    col = collection or settings.QDRANT_COLLECTION
    result = await db.execute(PLACES_WITH_DISHES_SQL)
    rows = result.fetchall()

    if not rows:
        logger.warning("No places found to index")
        return 0

    logger.info("Indexing %d places into Qdrant collection '%s'", len(rows), col)

    total = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        docs = []
        payloads = []
        ids = []

        for row in batch:
            doc_text, _, payload = _row_to_doc(row)
            docs.append(doc_text)
            payloads.append(payload)
            ids.append(str(row.id))

        vectors = embedder.encode(docs)

        points = [
            PointStruct(id=pid, vector=vec, payload=pay)
            for pid, vec, pay in zip(ids, vectors, payloads)
        ]

        qdrant.upsert(collection_name=col, points=points)
        total += len(points)
        logger.info("  Indexed batch %d-%d (%d/%d)", i, i + len(batch), total, len(rows))

    logger.info("Indexing complete: %d places", total)
    return total


async def index_place(
    place_id: str | UUID,
    db: AsyncSession,
    embedder: Embedder,
    qdrant: QdrantClient,
    collection: str | None = None,
):
    col = collection or settings.QDRANT_COLLECTION
    result = await db.execute(SINGLE_PLACE_SQL, {"place_id": str(place_id)})
    row = result.fetchone()

    if not row:
        logger.warning("Place %s not found for indexing", place_id)
        return False

    doc_text, _, payload = _row_to_doc(row)
    vector = embedder.encode([doc_text])[0]

    qdrant.upsert(
        collection_name=col,
        points=[PointStruct(id=str(row.id), vector=vector, payload=payload)],
    )
    logger.info("Indexed place: %s (%s)", row.name, place_id)
    return True


def delete_place_from_index(
    place_id: str | UUID,
    qdrant: QdrantClient,
    collection: str | None = None,
):
    col = collection or settings.QDRANT_COLLECTION
    qdrant.delete(collection_name=col, points_selector=[str(place_id)])
    logger.info("Deleted place from index: %s", place_id)
