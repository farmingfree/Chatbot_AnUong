import uuid
from datetime import datetime
from sqlalchemy import String, Text, Float, Integer, Boolean, DateTime, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geometry
from app.models.base import Base


class Place(Base):
    __tablename__ = "places"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    geom = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20))
    google_place_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    price_min: Mapped[int | None] = mapped_column(Integer)
    price_max: Mapped[int | None] = mapped_column(Integer)
    price_level: Mapped[int | None] = mapped_column(Integer)
    rating_google: Mapped[float | None] = mapped_column(Float)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    hours = mapped_column(JSON, nullable=True)
    features = mapped_column(JSON, nullable=True)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)
    data_quality_score: Mapped[float] = mapped_column(Float, default=0.5)
    image_urls = mapped_column(JSON, nullable=True)
    district: Mapped[str | None] = mapped_column(String(50))
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_places_geom", "geom", postgresql_using="gist"),
        Index("idx_places_district", "district", "is_closed"),
    )
