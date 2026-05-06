from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.common import ReviewCard, MenuItemCard


class PlaceBase(BaseModel):
    name: str
    address: str
    lat: float
    lng: float
    district: str


class PlaceCard(BaseModel):
    """Schema cho card hiển thị trong chat — lightweight"""
    id: UUID
    name: str
    address: str
    district: str
    distance_m: int | None = None  # computed từ user location
    rating: float | None = None
    review_count: int = 0
    price_level: int | None = None  # 1-4
    price_range: str | None = None  # "50,000đ - 150,000đ"
    image_url: str | None = None  # first image từ image_urls
    is_open_now: bool = False  # computed từ hours + current time VN
    top_dishes: list[str] = []  # tên các món nổi bật, tối đa 3
    model_config = ConfigDict(from_attributes=True)


class PlaceDetail(BaseModel):
    """Schema cho detail page — đầy đủ"""
    id: UUID
    name: str
    address: str
    lat: float
    lng: float
    district: str
    phone: str | None = None
    google_place_id: str | None = None
    google_maps_url: str | None = None
    price_min: int | None = None
    price_max: int | None = None
    price_level: int | None = None
    rating_google: float | None = None
    review_count: int = 0
    hours: dict | None = None
    features: dict | None = None
    is_closed: bool = False
    image_urls: list[str] = []
    dishes: list[str] = []
    menu_items: list[dict] = []
    is_open_now: bool = False
    distance_m: int | None = None
    reviews: list[dict] = []
    last_crawled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class NearbyPlacesRequest(BaseModel):
    lat: float
    lng: float
    radius_m: int = Field(default=500, ge=100, le=5000)
    dish_name: str | None = None
    vegetarian: bool = False
    halal: bool = False
    price_max_per_person: int | None = None  # VNĐ
    people_count: int = Field(default=1, ge=1, le=20)
    limit: int = Field(default=10, ge=1, le=30)


class NearbyPlacesResponse(BaseModel):
    places: list[PlaceCard]
    total: int
    radius_m: int
    center: dict  # {lat, lng}
