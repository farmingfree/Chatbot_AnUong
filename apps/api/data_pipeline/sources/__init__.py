"""Data sources for food places"""
from .base import BaseSource, RawPlace
from .google_maps import GoogleMapsSource
from .foody import FoodySource
from .shopee_food import ShopeeFoodSource
from .manual import ManualSource
from .osm import OSMSource

__all__ = [
    "BaseSource",
    "RawPlace",
    "GoogleMapsSource",
    "FoodySource",
    "ShopeeFoodSource",
    "ManualSource",
    "OSMSource",
]
