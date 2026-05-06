"""
Users router - favorites and preferences management
"""
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User
from app.models.favorite import Favorite
from app.models.place import Place
from app.schemas.user import (
    UserMeResponse,
    PreferencesUpdate,
    FavoriteRequest,
    FavoriteResponse,
    FavoritesListResponse
)
from app.schemas.place import PlaceCard

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserMeResponse)
async def get_current_user_info(
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user info and preferences"""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update last_active_at
    user.last_active_at = datetime.utcnow()
    await db.commit()
    
    return user


@router.patch("/preferences", response_model=dict)
async def update_preferences(
    preferences: PreferencesUpdate,
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user preferences (partial update - merge with existing)
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Merge new preferences with existing ones
    current_prefs = user.preferences or {}
    update_data = preferences.model_dump(exclude_unset=True)
    
    # Merge the updates
    for key, value in update_data.items():
        if value is not None:
            current_prefs[key] = value
    
    user.preferences = current_prefs
    await db.commit()
    await db.refresh(user)

    return user.preferences


@router.post("/favorites", response_model=FavoriteResponse)
async def add_favorite(
    request: FavoriteRequest,
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a place to user's favorites (upsert)"""
    # Check if place exists
    place_result = await db.execute(
        select(Place).where(Place.id == request.place_id)
    )
    place = place_result.scalar_one_or_none()
    
    if not place:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Place not found"
        )
    
    # Upsert favorite using PostgreSQL INSERT ... ON CONFLICT DO NOTHING
    stmt = insert(Favorite).values(
        user_id=user_id,
        place_id=request.place_id,
        created_at=datetime.utcnow()
    ).on_conflict_do_nothing(
        constraint='uq_user_place'
    )
    
    await db.execute(stmt)
    await db.commit()
    
    return FavoriteResponse(favorited=True, place_id=request.place_id)


@router.delete("/favorites/{place_id}", response_model=FavoriteResponse)
async def remove_favorite(
    place_id: UUID,
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a place from user's favorites"""
    stmt = delete(Favorite).where(
        Favorite.user_id == user_id,
        Favorite.place_id == place_id
    )
    
    result = await db.execute(stmt)
    await db.commit()
    
    return FavoriteResponse(favorited=False, place_id=place_id)


@router.get("/favorites", response_model=FavoritesListResponse)
async def get_favorites(
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all user's favorite places"""
    # Query favorites with place details, ordered by created_at DESC
    stmt = (
        select(Place, Favorite.created_at)
        .join(Favorite, Place.id == Favorite.place_id)
        .where(Favorite.user_id == user_id)
        .order_by(Favorite.created_at.desc())
    )
    
    result = await db.execute(stmt)
    rows = result.all()
    
    # Convert to PlaceCard format
    places = []
    for place, fav_created_at in rows:
        # Build PlaceCard
        place_card = PlaceCard(
            id=place.id,
            name=place.name,
            address=place.address,
            district=place.district,
            distance_m=None,  # No distance calculation for favorites list
            rating=place.rating_google,
            review_count=place.review_count or 0,
            price_level=place.price_level,
            price_range=f"{place.price_min:,}đ - {place.price_max:,}đ" if place.price_min and place.price_max else None,
            image_url=place.image_urls[0] if place.image_urls else None,
            is_open_now=False,  # Could calculate this if needed
            top_dishes=place.dishes[:3] if place.dishes else []
        )
        places.append(place_card)
    
    return FavoritesListResponse(
        favorites=places,
        total=len(places)
    )
