from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.schemas.place import (
    NearbyPlacesRequest,
    NearbyPlacesResponse,
    PlaceCard,
    PlaceDetail
)
from app.models import Place, Review
from app.services.geo import normalize_text, is_open_now, calc_distance_m, get_google_maps_url

router = APIRouter(prefix="/api/places", tags=["places"])


async def search_nearby_places(
    req: NearbyPlacesRequest,
    db: AsyncSession
) -> List[PlaceCard]:
    """Search for nearby places with filters"""
    
    # Build dynamic filters
    filters = []
    params = {
        "lat": req.lat,
        "lng": req.lng,
        "radius_m": req.radius_m,
        "limit": req.limit
    }
    
    if req.vegetarian:
        filters.append("(p.features->>'vegetarian')::boolean = true")
    
    if req.halal:
        filters.append("(p.features->>'halal')::boolean = true")
    
    if req.price_max_per_person:
        total_budget = req.price_max_per_person * req.people_count
        filters.append("p.price_min <= :price_max")
        params["price_max"] = total_budget
    
    if req.dish_name:
        filters.append("""
            p.id IN (
                SELECT pd2.place_id FROM place_dishes pd2
                JOIN dishes d2 ON d2.id = pd2.dish_id
                WHERE d2.name_normalized ILIKE :dish_pattern
            )
        """)
        params["dish_pattern"] = f"%{normalize_text(req.dish_name)}%"
    
    filter_clause = ""
    if filters:
        filter_clause = "AND " + " AND ".join(filters)
    
    # Build query with PostGIS
    query = f"""
    SELECT
        p.id,
        p.name,
        p.address,
        p.lat,
        p.lng,
        p.district,
        p.phone,
        p.price_min,
        p.price_max,
        p.price_level,
        p.rating_google,
        p.review_count,
        p.hours,
        p.features,
        p.image_urls,
        ST_Distance(p.geom::geography, ST_MakePoint(:lng, :lat)::geography) as distance_m,
        array_agg(DISTINCT d.name) FILTER (WHERE d.name IS NOT NULL) as dish_names
    FROM places p
    LEFT JOIN place_dishes pd ON pd.place_id = p.id AND pd.is_available = true
    LEFT JOIN dishes d ON d.id = pd.dish_id
    WHERE
        ST_DWithin(p.geom::geography, ST_MakePoint(:lng, :lat)::geography, :radius_m)
        AND p.is_closed = false
        {filter_clause}
    GROUP BY p.id
    ORDER BY distance_m ASC
    LIMIT :limit
    """
    
    result = await db.execute(text(query), params)
    rows = result.fetchall()
    
    # Map to PlaceCard schema
    places = []
    for row in rows:
        # Get first image or None
        image_url = row.image_urls[0] if row.image_urls else None
        
        # Get top 3 dishes
        dishes = (row.dish_names or [])[:3]
        
        # Calculate is_open_now
        is_open = is_open_now(row.hours)
        
        place_card = PlaceCard(
            id=row.id,
            name=row.name,
            address=row.address,
            district=row.district,
            distance_m=int(row.distance_m),
            rating=row.rating_google,
            review_count=row.review_count,
            price_level=row.price_level,
            price_range=f"{row.price_min:,}đ - {row.price_max:,}đ" if row.price_min and row.price_max else None,
            image_url=image_url,
            is_open_now=is_open,
            top_dishes=dishes
        )
        places.append(place_card)
    
    return places


@router.post("/nearby", response_model=NearbyPlacesResponse)
async def get_nearby_places(
    request: NearbyPlacesRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Find nearby places based on location and filters
    
    - **lat**: Latitude (e.g., 10.7769 for Ben Thanh Market)
    - **lng**: Longitude (e.g., 106.7009)
    - **radius_m**: Search radius in meters (default: 1000m)
    - **limit**: Max results (default: 20)
    - **price_max_per_person**: Max price per person in VND
    - **people_count**: Number of people (default: 1)
    - **vegetarian**: Filter vegetarian places
    - **halal**: Filter halal places
    - **dish_name**: Search by dish name (e.g., "phở", "cơm tấm")
    """
    places = await search_nearby_places(request, db)
    
    return NearbyPlacesResponse(
        places=places,
        total=len(places),
        center_lat=request.lat,
        center_lng=request.lng,
        radius_m=request.radius_m
    )


@router.get("/{place_id}", response_model=PlaceDetail)
async def get_place_detail(
    place_id: UUID,
    lat: Optional[float] = Query(None, description="User's latitude for distance calculation"),
    lng: Optional[float] = Query(None, description="User's longitude for distance calculation"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific place

    Includes:
    - Full place information
    - Top 10 recent reviews
    - All available dishes with prices
    - Opening hours
    - Features (AC, WiFi, Parking, etc.)
    - Distance from user (if lat/lng provided)
    - Google Maps URL
    """
    # Get place with dishes and menu items
    query = text("""
    SELECT
        p.*,
        array_agg(DISTINCT d.name) FILTER (WHERE d.name IS NOT NULL) as dish_names,
        array_agg(DISTINCT jsonb_build_object(
            'dish_name', d.name,
            'price', pd.price,
            'is_available', pd.is_available
        )) FILTER (WHERE d.name IS NOT NULL) as menu_items
    FROM places p
    LEFT JOIN place_dishes pd ON pd.place_id = p.id
    LEFT JOIN dishes d ON d.id = pd.dish_id
    WHERE p.id = :place_id
    GROUP BY p.id
    """)

    result = await db.execute(query, {"place_id": str(place_id)})
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Place not found")

    # Get recent reviews (limit 10)
    reviews_result = await db.execute(
        select(Review)
        .where(Review.place_id == place_id)
        .order_by(Review.created_at.desc())
        .limit(10)
    )
    reviews = reviews_result.scalars().all()

    # Calculate is_open_now
    is_open = is_open_now(row.hours)

    # Calculate distance if user location provided
    distance_m = None
    if lat is not None and lng is not None:
        distance_m = int(calc_distance_m(lat, lng, row.lat, row.lng))

    # Generate Google Maps URL
    google_maps_url = get_google_maps_url(
        google_place_id=row.google_place_id,
        lat=row.lat,
        lng=row.lng
    )

    # Build PlaceDetail
    place_detail = PlaceDetail(
        id=row.id,
        name=row.name,
        address=row.address,
        lat=row.lat,
        lng=row.lng,
        district=row.district,
        phone=row.phone,
        google_place_id=row.google_place_id,
        google_maps_url=google_maps_url,
        price_min=row.price_min,
        price_max=row.price_max,
        price_level=row.price_level,
        rating_google=row.rating_google,
        review_count=row.review_count,
        hours=row.hours,
        features=row.features,
        is_closed=row.is_closed,
        image_urls=row.image_urls or [],
        dishes=row.dish_names or [],
        menu_items=row.menu_items or [],
        is_open_now=is_open,
        distance_m=distance_m,
        reviews=[
            {
                "id": str(r.id),
                "user_name": r.user_name,
                "rating": r.rating,
                "comment": r.comment,
                "created_at": r.created_at.isoformat()
            }
            for r in reviews
        ],
        last_crawled_at=row.last_crawled_at,
        created_at=row.created_at,
        updated_at=row.updated_at
    )

    return place_detail
