"""Base classes for data sources"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import AsyncIterator


@dataclass
class RawPlace:
    """Unified raw format — mọi nguồn đều phải trả về format này"""
    name: str
    address: str | None
    lat: float | None
    lng: float | None
    district: str | None
    phone: str | None
    price_min: int | None
    price_max: int | None
    price_level: int | None  # 1-4
    rating: float | None
    review_count: int | None
    hours: dict | None  # {"mon": "07:00-22:00", ...}
    features: dict | None  # {"ac": bool, "wifi": bool, "vegetarian": bool, "halal": bool, "parking": bool}
    dishes: list[str]  # Tên các món
    image_urls: list[str]
    source: str  # "google_maps" | "foody" | "shopee_food" | "manual"
    source_id: str | None  # ID bên nguồn để dedup
    raw_data: dict | None  # Lưu raw để debug

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def _price_to_level(price_min: int | None, price_max: int | None) -> int | None:
        """Convert price range to level 1-4"""
        if not price_min and not price_max:
            return None
        avg = ((price_min or 0) + (price_max or 0)) / 2
        if avg < 50000:
            return 1
        elif avg < 150000:
            return 2
        elif avg < 350000:
            return 3
        else:
            return 4


class BaseSource(ABC):
    """Abstract base class for all data sources"""
    source_name: str

    @abstractmethod
    async def fetch(self, **kwargs) -> AsyncIterator[RawPlace]:
        """Yield từng quán một để có thể stream vào DB ngay"""
        pass

    @abstractmethod
    def estimate_count(self, **kwargs) -> int:
        """Ước tính số quán sẽ fetch để hiện progress bar"""
        pass
