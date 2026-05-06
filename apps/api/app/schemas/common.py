from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ReviewCard(BaseModel):
    id: UUID
    source: str
    author_name: str | None
    rating: float | None
    content: str | None
    published_at: str | None
    model_config = ConfigDict(from_attributes=True)


class MenuItemCard(BaseModel):
    dish_id: UUID
    dish_name: str
    price: int | None
    is_available: bool
    model_config = ConfigDict(from_attributes=True)
