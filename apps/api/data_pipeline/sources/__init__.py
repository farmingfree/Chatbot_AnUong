"""Data sources for food places"""
from .base import BaseSource, RawPlace
from .google_maps import GoogleMapsSource
from .google_maps_playwright import GoogleMapsPlaywrightSource
from .foody import FoodySource
from .shopee_food import ShopeeFoodSource
from .manual import ManualSource
from .osm import OSMSource

__all__ = [
    "BaseSource",
    "RawPlace",
    "GoogleMapsSource",
    "GoogleMapsPlaywrightSource",
    "FoodySource",
    "ShopeeFoodSource",
    "ManualSource",
    "OSMSource",
]
