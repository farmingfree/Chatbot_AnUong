import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint('user_id', 'place_id', name='uq_user_place'),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    place_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("places.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
