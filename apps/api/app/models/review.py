import uuid
from datetime import datetime
from sqlalchemy import String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    place_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("places.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(50))
    author_name: Mapped[str | None] = mapped_column(String(100))
    rating: Mapped[float | None] = mapped_column(Float)
    content: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    crawled_at: Mapped[datetime | None] = mapped_column(DateTime)
