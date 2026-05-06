from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List

from app.database import get_db
from app.schemas.dish import NearbyDishesRequest, NearbyDishesResponse, DishCard

router = APIRouter(prefix="/api/dishes", tags=["dishes"])


@router.post("/nearby", response_model=NearbyDishesResponse)
async def get_nearby_dishes(
    request: NearbyDishesRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Find dishes available at nearby places
    
    Different from /api/places/nearby - this returns DISHES with place_count,
    showing how many nearby places serve each dish.
    
    - **lat**: Latitude
    - **lng**: Longitude
    - **radius_m**: Search radius in meters (default: 1000m)
    - **limit**: Max results (default: 20)
    - **category**: Filter by dish category (optional)
    - **min_place_count**: Minimum number of places serving the dish (default: 1)
    """
    
    # Build query to find dishes at nearby places
    params = {
        "lat": request.lat,
        "lng": request.lng,
        "radius_m": request.radius_m,
        "limit": request.limit,
        "min_place_count": request.min_place_count
    }
    
    # Add category filter if provided
    category_filter = ""
    if request.category:
        category_filter = "AND d.category = :category"
        params["category"] = request.category
    
    query = f"""
    SELECT
        d.id,
        d.name,
        d.name_normalized,
        d.category,
        d.avg_price,
        d.image_url,
        COUNT(DISTINCT pd.place_id) as place_count,
        MIN(pd.price) as min_price_at_nearby,
        MAX(pd.price) as max_price_at_nearby,
        array_agg(DISTINCT p.name) FILTER (WHERE p.name IS NOT NULL) as place_names
    FROM dishes d
    JOIN place_dishes pd ON pd.dish_id = d.id AND pd.is_available = true
    JOIN places p ON p.id = pd.place_id
    WHERE
        ST_DWithin(p.geom::geography, ST_MakePoint(:lng, :lat)::geography, :radius_m)
        AND p.is_closed = false
        {category_filter}
    GROUP BY d.id
    HAVING COUNT(DISTINCT pd.place_id) >= :min_place_count
    ORDER BY place_count DESC, d.name ASC
    LIMIT :limit
    """
    
    result = await db.execute(text(query), params)
    rows = result.fetchall()
    
    # Map to DishCard schema
    dishes = []
    for row in rows:
        # Format price range
        if row.min_price_at_nearby and row.max_price_at_nearby:
            if row.min_price_at_nearby == row.max_price_at_nearby:
                price_range = f"{row.min_price_at_nearby:,}đ"
            else:
                price_range = f"{row.min_price_at_nearby:,}đ - {row.max_price_at_nearby:,}đ"
        else:
            price_range = None
        
        # Get sample places (max 3)
        sample_places = (row.place_names or [])[:3]
        
        dish_card = DishCard(
            id=row.id,
            name=row.name,
            category=row.category,
            place_count=row.place_count,
            price_range=price_range,
            avg_price=row.avg_price,
            image_url=row.image_url,
            sample_places=sample_places
        )
        dishes.append(dish_card)
    
    return NearbyDishesResponse(
        dishes=dishes,
        total=len(dishes),
        center_lat=request.lat,
        center_lng=request.lng,
        radius_m=request.radius_m
    )
