import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(100))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    provider: Mapped[str | None] = mapped_column(String(20))  # "google"
    provider_id: Mapped[str | None] = mapped_column(String(100), unique=True)  # Google sub ID
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    # preferences structure:
    # {
    #   "budget_per_person": 100000,
    #   "vegetarian": false,
    #   "favorite_districts": ["Quận 1", "Bình Thạnh"],
    #   "disliked_dishes": [],
    #   "dietary_notes": "không ăn cay"
    # }
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
