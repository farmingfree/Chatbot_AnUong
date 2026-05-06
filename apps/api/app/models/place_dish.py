import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class PlaceDish(Base):
    __tablename__ = "place_dishes"

    place_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("places.id"), primary_key=True)
    dish_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dishes.id"), primary_key=True)
    price: Mapped[int | None] = mapped_column(Integer)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=datetime.utcnow)
