import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Dish(Base):
    __tablename__ = "dishes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_normalized: Mapped[str | None] = mapped_column(String(100))
    category: Mapped[str | None] = mapped_column(String(50))
    avg_price: Mapped[int | None] = mapped_column(Integer)
    image_url: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
