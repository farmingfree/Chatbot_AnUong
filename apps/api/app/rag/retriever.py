"""Hybrid search: Qdrant semantic + PostgreSQL keyword/FTS + PostGIS geo filtering."""

import logging
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.config import settings
from app.rag.embedder import Embedder
from app.rag.query_understanding import ParsedQuery

logger = logging.getLogger(__name__)


@dataclass
class SearchCandidate:
    place_id: str
    semantic_score: float
    keyword_score: float
    distance_m: float | None
    name: str
    district: str
    summary: str
    dish_names: list[str]
    price_min: int | None
    price_max: int | None
    rating: float | None
    review_count: int
    hours: dict | None = None


GEO_FILTER_SQL = text("""
    SELECT
        id::text as place_id,
        ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography) as distance_m
    FROM places
    WHERE id = ANY(:ids::uuid[])
      AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, :radius_m)
      AND is_closed = false
""")


KEYWORD_SEARCH_SQL = text("""
    SELECT DISTINCT
        p.id::text as place_id,
        p.name,
        p.district,
        p.price_min,
        p.price_max,
        p.rating_google as rating,
        p.review_count,
        p.hours,
        ST_Distance(p.geom::geography, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography) as distance_m,
        CASE
            WHEN LOWER(p.name) ILIKE :query_like THEN 0.9
            WHEN LOWER(p.district) ILIKE :district_like THEN 0.7
            WHEN d.name ILIKE :dish_like THEN 0.8
            ELSE 0.3
        END as keyword_score
    FROM places p
    LEFT JOIN place_dishes pd ON pd.place_id = p.id
    LEFT JOIN dishes d ON d.id = pd.dish_id
    WHERE p.is_closed = false
      AND ST_DWithin(p.geom::geography, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, :radius_m)
      AND (
          LOWER(p.name) ILIKE :query_like
          OR LOWER(p.district) ILIKE :district_like
          OR d.name ILIKE :dish_like
          OR d.name_normalized ILIKE :dish_norm_like
      )
    ORDER BY keyword_score DESC, distance_m ASC
    LIMIT :limit
""")


async def keyword_search(
    query: str,
    parsed: ParsedQuery,
    lat: float,
    lng: float,
    radius_m: int,
    db: AsyncSession,
    limit: int = 20,
) -> list[SearchCandidate]:
    query_like = f"%{query}%"
    district_like = f"%{parsed.district}%" if parsed.district else "%__NOMATCH__%"
    dish_like = f"%{parsed.cuisine}%" if parsed.cuisine else query_like
    dish_norm_like = f"%{query.lower()}%"

    result = await db.execute(KEYWORD_SEARCH_SQL, {
        "lat": lat,
        "lng": lng,
        "radius_m": radius_m,
        "query_like": query_like,
        "district_like": district_like,
        "dish_like": dish_like,
        "dish_norm_like": dish_norm_like,
        "limit": limit,
    })
    rows = result.fetchall()

    candidates = []
    for row in rows:
        candidates.append(SearchCandidate(
            place_id=row.place_id,
            semantic_score=0.0,
            keyword_score=row.keyword_score,
            distance_m=row.distance_m,
            name=row.name,
            district=row.district or "",
            summary="",
            dish_names=[],
            price_min=row.price_min,
            price_max=row.price_max,
            rating=row.rating,
            review_count=row.review_count or 0,
            hours=row.hours,
        ))

    return candidates


async def semantic_search(
    query: str,
    lat: float,
    lng: float,
    radius_m: int,
    embedder: Embedder,
    qdrant: QdrantClient,
    db: AsyncSession,
    limit: int = 20,
    district: str | None = None,
    collection: str | None = None,
) -> list[SearchCandidate]:
    col = collection or settings.QDRANT_COLLECTION

    query_vector = embedder.encode_query(query)

    qdrant_filter = None
    if district:
        qdrant_filter = Filter(
            must=[FieldCondition(key="district", match=MatchValue(value=district))]
        )

    qdrant_results = qdrant.search(
        collection_name=col,
        query_vector=query_vector,
        limit=limit * 3,
        query_filter=qdrant_filter,
    )

    if not qdrant_results:
        return []

    score_map: dict[str, float] = {}
    payload_map: dict[str, dict] = {}
    candidate_ids = []

    for hit in qdrant_results:
        pid = hit.id if isinstance(hit.id, str) else str(hit.id)
        score_map[pid] = hit.score
        payload_map[pid] = hit.payload or {}
        candidate_ids.append(pid)

    result = await db.execute(
        GEO_FILTER_SQL,
        {"lat": lat, "lng": lng, "radius_m": radius_m, "ids": candidate_ids},
    )
    geo_rows = result.fetchall()

    candidates = []
    for row in geo_rows:
        pid = row.place_id
        payload = payload_map.get(pid, {})
        candidates.append(SearchCandidate(
            place_id=pid,
            semantic_score=score_map.get(pid, 0.0),
            keyword_score=0.0,
            distance_m=row.distance_m,
            name=payload.get("name", ""),
            district=payload.get("district", ""),
            summary=payload.get("summary", ""),
            dish_names=payload.get("dish_names", []),
            price_min=payload.get("price_min"),
            price_max=payload.get("price_max"),
            rating=payload.get("rating"),
            review_count=payload.get("review_count", 0),
        ))

    return candidates


async def hybrid_search(
    query: str,
    lat: float,
    lng: float,
    radius_m: int,
    embedder: Embedder | None,
    qdrant: QdrantClient | None,
    db: AsyncSession,
    limit: int = 20,
    district: str | None = None,
    collection: str | None = None,
    parsed: ParsedQuery | None = None,
) -> list[SearchCandidate]:
    if parsed is None:
        from app.rag.query_understanding import parse_query
        parsed = parse_query(query)

    effective_district = district or parsed.district

    # Run both searches
    semantic_candidates = []
    if embedder and qdrant:
        semantic_candidates = await semantic_search(
            query, lat, lng, radius_m, embedder, qdrant, db,
            limit=limit, district=effective_district, collection=collection,
        )

    keyword_candidates = await keyword_search(
        query, parsed, lat, lng, radius_m, db, limit=limit,
    )

    # Merge by place_id
    merged: dict[str, SearchCandidate] = {}

    for c in semantic_candidates:
        merged[c.place_id] = c

    for c in keyword_candidates:
        if c.place_id in merged:
            merged[c.place_id].keyword_score = c.keyword_score
            if c.hours:
                merged[c.place_id].hours = c.hours
        else:
            merged[c.place_id] = c

    candidates = list(merged.values())

    logger.info(
        "Hybrid search: query='%s', semantic=%d, keyword=%d, merged=%d",
        query[:50], len(semantic_candidates), len(keyword_candidates), len(candidates),
    )

    return candidates
