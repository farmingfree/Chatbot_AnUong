from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class DishCard(BaseModel):
    id: UUID
    name: str
    category: str | None = None
    place_count: int = 0  # số quán có món này
    price_range: str | None = None  # "50,000đ - 150,000đ"
    avg_price: int | None = None
    image_url: str | None = None
    sample_places: list[str] = []  # tên 3 quán mẫu có món này
    model_config = ConfigDict(from_attributes=True)


class NearbyDishesRequest(BaseModel):
    lat: float
    lng: float
    radius_m: int = Field(default=1000, ge=100, le=5000)
    limit: int = Field(default=20, ge=1, le=50)
    category: str | None = None  # filter by category
    min_place_count: int = Field(default=1, ge=1)  # minimum places serving this dish


class NearbyDishesResponse(BaseModel):
    dishes: list[DishCard]
    total: int
    center_lat: float
    center_lng: float
    radius_m: int
