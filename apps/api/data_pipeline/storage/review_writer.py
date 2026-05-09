"""Review writer for storing reviews separately"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
from app.models.review import Review

logger = logging.getLogger(__name__)


class ReviewWriter:
    """Write reviews to database"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def write_reviews(self, place_id: str, reviews: list[dict]):
        """
        Write reviews for a place.

        Args:
            place_id: UUID of the place
            reviews: List of review dicts with keys:
                - author_name
                - rating
                - content
                - published_at (optional)
        """
        if not reviews:
            return

        for review_data in reviews:
            # Check if review already exists (by place + author + content hash)
            content_hash = hash(review_data.get("content", ""))

            result = await self.db.execute(
                select(Review.id).where(
                    Review.place_id == place_id,
                    Review.author_name == review_data.get("author_name"),
                )
            )

            if result.first():
                continue  # Skip duplicate

            review = Review(
                place_id=place_id,
                source="google_maps",
                author_name=review_data.get("author_name"),
                rating=review_data.get("rating"),
                content=review_data.get("content"),
                published_at=review_data.get("published_at"),
            )

            self.db.add(review)

        await self.db.commit()
        logger.info(f"Wrote {len(reviews)} reviews for place {place_id}")
