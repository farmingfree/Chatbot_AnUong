"""
Geo and utility helper functions
"""
import unicodedata
import math
from datetime import datetime, timedelta, timezone
from typing import Optional


def normalize_text(text: str) -> str:
    """
    Normalize Vietnamese text for search
    - Convert to lowercase
    - Remove Vietnamese diacritics
    
    Example:
        "Phở Bò" -> "pho bo"
        "Cơm Tấm" -> "com tam"
    """
    if not text:
        return ""
    
    # Normalize to NFD (decomposed form)
    nfd = unicodedata.normalize('NFD', text)
    
    # Remove combining characters (diacritics)
    without_accents = ''.join(
        char for char in nfd 
        if unicodedata.category(char) != 'Mn'
    )
    
    return without_accents.lower().strip()


def calc_distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate distance between two coordinates using Haversine formula
    
    Args:
        lat1, lng1: First coordinate
        lat2, lng2: Second coordinate
    
    Returns:
        Distance in meters
    """
    # Earth radius in meters
    R = 6371000
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    # Haversine formula
    a = (
        math.sin(delta_lat / 2) ** 2 +
        math.cos(lat1_rad) * math.cos(lat2_rad) *
        math.sin(delta_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance


def is_open_now(hours: Optional[dict]) -> bool:
    """
    Check if place is open now based on Vietnam timezone (UTC+7)
    
    Args:
        hours: Dict with keys like "mon", "tue", etc. and values like "06:00-22:00" or "closed"
    
    Returns:
        True if open now, False if closed
    """
    if not hours:
        return True  # Assume open if no hours specified
    
    # Vietnam timezone UTC+7
    now_vn = datetime.now(timezone(timedelta(hours=7)))
    day_keys = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    day_key = day_keys[now_vn.weekday()]
    
    schedule = hours.get(day_key, "closed")
    if schedule == "closed" or not schedule:
        return False
    
    try:
        # Parse schedule like "06:00-22:00"
        open_str, close_str = schedule.split("-")
        
        # Parse times
        open_time = datetime.strptime(open_str.strip(), "%H:%M").time()
        close_time = datetime.strptime(close_str.strip(), "%H:%M").time()
        
        current_time = now_vn.time()
        
        # Handle overnight hours (e.g., "22:00-02:00")
        if close_time < open_time:
            # Open past midnight
            return current_time >= open_time or current_time <= close_time
        else:
            # Normal hours
            return open_time <= current_time <= close_time
    except Exception:
        # If parsing fails, assume open
        return True


def price_level_to_range(level: int) -> tuple[int, int]:
    """
    Map price level (1-4) to VND price range
    
    Price levels:
        1: Budget (< 50k)
        2: Moderate (50k - 200k)
        3: Expensive (200k - 500k)
        4: Very Expensive (> 500k)
    
    Args:
        level: Price level (1-4)
    
    Returns:
        Tuple of (min_price, max_price) in VND
    """
    price_map = {
        1: (10000, 50000),
        2: (50000, 200000),
        3: (200000, 500000),
        4: (500000, 2000000)
    }
    
    return price_map.get(level, (50000, 200000))


def format_price_vnd(price: int) -> str:
    """
    Format price in VND with thousand separators
    
    Example:
        150000 -> "150,000đ"
    """
    return f"{price:,}đ"


def format_distance(distance_m: float) -> str:
    """
    Format distance in human-readable form
    
    Example:
        450 -> "450m"
        1200 -> "1.2km"
    """
    if distance_m < 1000:
        return f"{int(distance_m)}m"
    else:
        return f"{distance_m / 1000:.1f}km"


def get_google_maps_url(google_place_id: Optional[str] = None, lat: Optional[float] = None, lng: Optional[float] = None) -> Optional[str]:
    """
    Generate Google Maps URL for a place
    
    Args:
        google_place_id: Google Place ID (preferred)
        lat, lng: Coordinates (fallback)
    
    Returns:
        Google Maps URL or None
    """
    if google_place_id:
        return f"https://www.google.com/maps/place/?q=place_id:{google_place_id}"
    elif lat and lng:
        return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
    return None


def get_day_name_vi(day_key: str) -> str:
    """
    Convert day key to Vietnamese day name
    
    Example:
        "mon" -> "Thứ 2"
        "sun" -> "Chủ nhật"
    """
    day_map = {
        "mon": "Thứ 2",
        "tue": "Thứ 3",
        "wed": "Thứ 4",
        "thu": "Thứ 5",
        "fri": "Thứ 6",
        "sat": "Thứ 7",
        "sun": "Chủ nhật"
    }
    return day_map.get(day_key, day_key)
