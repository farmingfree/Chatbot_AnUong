from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import Place, Dish, PlaceDish
from app.services.geo import normalize_text

router = APIRouter(prefix="/api/admin", tags=["admin"])


class PlaceCreate(BaseModel):
    name: str
    address: str
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    district: str
    phone: Optional[str] = None
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    price_level: Optional[int] = Field(default=None, ge=1, le=4)
    rating_google: Optional[float] = Field(default=None, ge=0, le=5)
    review_count: int = 0
    hours: Optional[dict] = None
    features: Optional[dict] = None
    dishes: list[str] = []


class PlaceUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lng: Optional[float] = Field(default=None, ge=-180, le=180)
    district: Optional[str] = None
    phone: Optional[str] = None
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    price_level: Optional[int] = Field(default=None, ge=1, le=4)
    rating_google: Optional[float] = Field(default=None, ge=0, le=5)
    review_count: Optional[int] = None
    hours: Optional[dict] = None
    features: Optional[dict] = None
    is_closed: Optional[bool] = None


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    places = (await db.execute(text("SELECT COUNT(*) FROM places"))).scalar() or 0
    dishes = (await db.execute(text("SELECT COUNT(*) FROM dishes"))).scalar() or 0
    place_dishes = (await db.execute(text("SELECT COUNT(*) FROM place_dishes"))).scalar() or 0
    reviews = (await db.execute(text("SELECT COUNT(*) FROM reviews"))).scalar() or 0
    open_places = (await db.execute(text("SELECT COUNT(*) FROM places WHERE is_closed = false"))).scalar() or 0
    return {
        "places": places,
        "open_places": open_places,
        "dishes": dishes,
        "place_dishes": place_dishes,
        "reviews": reviews,
    }


@router.post("/places", status_code=201)
async def create_place(body: PlaceCreate, db: AsyncSession = Depends(get_db)):
    import uuid
    place_id = uuid.uuid4()
    place = Place(
        id=place_id,
        name=body.name,
        address=body.address,
        lat=body.lat,
        lng=body.lng,
        district=body.district,
        phone=body.phone,
        price_min=body.price_min,
        price_max=body.price_max,
        price_level=body.price_level,
        rating_google=body.rating_google,
        review_count=body.review_count,
        hours=body.hours,
        features=body.features,
        is_closed=False,
    )
    db.add(place)
    await db.flush()

    await db.execute(text(
        "UPDATE places SET geom = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326) WHERE id = :id"
    ), {"lng": body.lng, "lat": body.lat, "id": str(place_id)})

    for dish_name in body.dishes:
        result = await db.execute(
            select(Dish).where(Dish.name == dish_name)
        )
        dish = result.scalar_one_or_none()
        if not dish:
            dish = Dish(
                id=uuid.uuid4(),
                name=dish_name,
                name_normalized=normalize_text(dish_name),
                category="Khác",
            )
            db.add(dish)
            await db.flush()

        pd = PlaceDish(place_id=place_id, dish_id=dish.id, is_available=True)
        db.add(pd)

    await db.commit()
    return {"id": str(place_id), "name": body.name}


@router.put("/places/{place_id}")
async def update_place(place_id: UUID, body: PlaceUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Place).where(Place.id == place_id))
    place = result.scalar_one_or_none()
    if not place:
        raise HTTPException(status_code=404, detail="Place not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(place, field, value)

    if "lat" in update_data or "lng" in update_data:
        await db.execute(text(
            "UPDATE places SET geom = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326) WHERE id = :id"
        ), {"lng": place.lng, "lat": place.lat, "id": str(place_id)})

    await db.commit()
    return {"id": str(place_id), "updated": list(update_data.keys())}


@router.delete("/places/{place_id}")
async def delete_place(place_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Place).where(Place.id == place_id))
    place = result.scalar_one_or_none()
    if not place:
        raise HTTPException(status_code=404, detail="Place not found")

    place.is_closed = True
    await db.commit()
    return {"id": str(place_id), "status": "closed"}


@router.post("/places/import", status_code=201)
async def import_places(places: list[PlaceCreate], db: AsyncSession = Depends(get_db)):
    import uuid
    created = []
    for body in places:
        place_id = uuid.uuid4()
        place = Place(
            id=place_id,
            name=body.name,
            address=body.address,
            lat=body.lat,
            lng=body.lng,
            district=body.district,
            phone=body.phone,
            price_min=body.price_min,
            price_max=body.price_max,
            price_level=body.price_level,
            rating_google=body.rating_google,
            review_count=body.review_count,
            hours=body.hours,
            features=body.features,
            is_closed=False,
        )
        db.add(place)
        await db.flush()

        await db.execute(text(
            "UPDATE places SET geom = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326) WHERE id = :id"
        ), {"lng": body.lng, "lat": body.lat, "id": str(place_id)})

        for dish_name in body.dishes:
            result = await db.execute(select(Dish).where(Dish.name == dish_name))
            dish = result.scalar_one_or_none()
            if not dish:
                dish = Dish(
                    id=uuid.uuid4(),
                    name=dish_name,
                    name_normalized=normalize_text(dish_name),
                    category="Khác",
                )
                db.add(dish)
                await db.flush()
            pd = PlaceDish(place_id=place_id, dish_id=dish.id, is_available=True)
            db.add(pd)

        created.append({"id": str(place_id), "name": body.name})

    await db.commit()
    return {"imported": len(created), "places": created}


@router.post("/reindex")
async def reindex_places(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Reindex all places into Qdrant for semantic search."""
    embedder = getattr(request.app.state, "embedder", None)
    qdrant = getattr(request.app.state, "qdrant", None)

    if not embedder or not qdrant:
        raise HTTPException(status_code=503, detail="RAG components not loaded")

    from app.rag.indexer import index_all_places
    count = await index_all_places(db, embedder, qdrant)
    return {"indexed": count}
