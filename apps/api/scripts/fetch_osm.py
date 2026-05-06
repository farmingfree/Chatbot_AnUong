"""
Standalone OSM fetcher - save to JSON, no DB needed.
Usage: python fetch_osm.py --max=5000 --output=data/osm_places.json
"""
import asyncio
import httpx
import json
import argparse
import sys
import os
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')


OVERPASS_QUERY = """
[out:json][timeout:120];
(
  node["amenity"="restaurant"](10.35,106.35,11.15,107.05);
  node["amenity"="cafe"](10.35,106.35,11.15,107.05);
  node["amenity"="fast_food"](10.35,106.35,11.15,107.05);
  node["amenity"="food_court"](10.35,106.35,11.15,107.05);
  node["amenity"="bar"](10.35,106.35,11.15,107.05);
);
out center meta;
"""

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def parse_tags(tags: dict) -> dict:
    """Extract useful fields from OSM tags"""
    amenity_map = {
        "restaurant": "restaurant",
        "cafe": "cafe",
        "fast_food": "fast_food",
        "food_court": "food_court",
        "bar": "bar",
    }
    
    cuisine_raw = tags.get("cuisine", "")
    cuisines = [c.strip() for c in cuisine_raw.replace(";", ",").split(",") if c.strip()]
    
    opening_hours = tags.get("opening_hours", "")
    
    price_level = None
    if "price_range" in tags:
        pr = tags["price_range"]
        if "$$$" in pr or "expensive" in pr.lower():
            price_level = 3
        elif "$$" in pr or "moderate" in pr.lower():
            price_level = 2
        else:
            price_level = 1
    
    return {
        "place_type": amenity_map.get(tags.get("amenity", ""), "restaurant"),
        "name": tags.get("name") or tags.get("name:vi") or tags.get("name:en", ""),
        "name_en": tags.get("name:en", ""),
        "name_vi": tags.get("name:vi", ""),
        "phone": tags.get("phone") or tags.get("contact:phone", ""),
        "website": tags.get("website") or tags.get("contact:website", ""),
        "cuisine": cuisines,
        "opening_hours": opening_hours,
        "price_level": price_level,
        "wheelchair": tags.get("wheelchair", ""),
        "outdoor_seating": tags.get("outdoor_seating", ""),
        "takeaway": tags.get("takeaway", ""),
        "delivery": tags.get("delivery", ""),
        "wifi": tags.get("internet_access", ""),
        "addr_street": tags.get("addr:street", ""),
        "addr_housenumber": tags.get("addr:housenumber", ""),
        "addr_district": tags.get("addr:suburb") or tags.get("addr:quarter", ""),
        "addr_city": tags.get("addr:city", "Ho Chi Minh City"),
        "osm_id": None,
    }


def build_address(element: dict) -> str:
    tags = element.get("tags", {})
    parts = []
    if tags.get("addr:housenumber"):
        parts.append(tags["addr:housenumber"])
    if tags.get("addr:street"):
        parts.append(tags["addr:street"])
    if tags.get("addr:suburb"):
        parts.append(tags["addr:suburb"])
    elif tags.get("addr:quarter"):
        parts.append(tags["addr:quarter"])
    if not parts:
        return ""
    return ", ".join(parts) + ", TP. Hồ Chí Minh"


def detect_district(lat: float, lng: float, tags: dict) -> str:
    """Detect district from tags or coordinates"""
    # Try from tags first
    district = tags.get("addr:suburb") or tags.get("addr:quarter") or tags.get("addr:district", "")
    if district:
        return district
    
    # Simple grid-based detection for HCM
    if lat >= 10.78 and lng <= 106.68:
        return "Tân Bình"
    elif lat >= 10.80 and lng >= 106.72:
        return "Thủ Đức"
    elif lat >= 10.75 and lng >= 106.70:
        return "Bình Thạnh"
    elif lat <= 10.73 and lng >= 106.70:
        return "Quận 4"
    elif lat <= 10.72 and lng >= 106.72:
        return "Quận 7"
    elif lat >= 10.75 and lng <= 106.67:
        return "Quận 12"
    elif lat >= 10.76 and lng >= 106.69:
        return "Quận 3"
    else:
        return "Quận 1"


async def fetch_osm(max_results: int, output_file: str):
    """Fetch places from OpenStreetMap via Overpass API"""
    print(f"\nFetching from OpenStreetMap Overpass API...")
    print(f"BBox: HCM area (10.35-11.15N, 106.35-107.05E)")
    print(f"Max results: {max_results}")
    print(f"Output: {output_file}\n")
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            print("Sending query to Overpass API...")
            response = await client.post(
                OVERPASS_URL,
                content=OVERPASS_QUERY,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "FoodAdvisor/1.0"
                }
            )
            
            if response.status_code != 200:
                print(f"[ERROR] HTTP {response.status_code}: {response.text[:200]}")
                return
            
            print("Parsing response...")
            data = response.json()
            elements = data.get("elements", [])
            print(f"Total elements from OSM: {len(elements)}")
            
        except Exception as e:
            print(f"[ERROR] {e}")
            import traceback
            traceback.print_exc()
            return
    
    # Process elements
    places = []
    skipped = 0
    
    for el in elements[:max_results]:
        tags = el.get("tags", {})
        
        # Skip if no name
        name = tags.get("name") or tags.get("name:vi") or tags.get("name:en", "")
        if not name:
            skipped += 1
            continue
        
        # Get coordinates
        lat = el.get("lat") or (el.get("center", {}) or {}).get("lat")
        lng = el.get("lon") or (el.get("center", {}) or {}).get("lon")
        
        if not lat or not lng:
            skipped += 1
            continue
        
        parsed = parse_tags(tags)
        parsed["osm_id"] = el.get("id")
        
        address = build_address(el)
        district = detect_district(lat, lng, tags)
        
        place = {
            "name": name,
            "name_en": parsed["name_en"],
            "name_vi": parsed["name_vi"] or name,
            "place_type": parsed["place_type"],
            "lat": lat,
            "lng": lng,
            "address": address or f"{district}, TP. Hồ Chí Minh",
            "district": district,
            "city": "Ho Chi Minh City",
            "phone": parsed["phone"],
            "website": parsed["website"],
            "cuisine_tags": parsed["cuisine"],
            "opening_hours": parsed["opening_hours"],
            "price_level": parsed["price_level"],
            "source": "osm",
            "source_id": f"osm_{el.get('id')}",
            "raw_tags": {
                "wheelchair": parsed["wheelchair"],
                "outdoor_seating": parsed["outdoor_seating"],
                "takeaway": parsed["takeaway"],
                "delivery": parsed["delivery"],
                "wifi": parsed["wifi"],
            },
            "fetched_at": datetime.utcnow().isoformat()
        }
        places.append(place)
        
        if len(places) % 500 == 0:
            print(f"  Processed {len(places)} places...")
    
    print(f"\nTotal valid places: {len(places)}")
    print(f"Skipped (no name/coords): {skipped}")
    
    # Save to file
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "meta": {
                "source": "openstreetmap",
                "fetched_at": datetime.utcnow().isoformat(),
                "total": len(places),
                "query_bbox": "HCM 10.35-11.15N, 106.35-107.05E"
            },
            "places": places
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n[OK] Saved {len(places)} places to {output_file}")
    
    # Show summary by type
    types = {}
    districts = {}
    for p in places:
        t = p["place_type"]
        types[t] = types.get(t, 0) + 1
        d = p["district"]
        districts[d] = districts.get(d, 0) + 1
    
    print("\n--- By Type ---")
    for t, cnt in sorted(types.items(), key=lambda x: -x[1]):
        print(f"  {t}: {cnt}")
    
    print("\n--- Top Districts ---")
    for d, cnt in sorted(districts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {d}: {cnt}")
    
    print(f"\nDone! Next step: python import_osm_to_db.py --file={output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch places from OpenStreetMap")
    parser.add_argument("--max", type=int, default=5000, help="Max places to fetch")
    parser.add_argument("--output", default="data/osm_places.json", help="Output JSON file")
    args = parser.parse_args()
    
    asyncio.run(fetch_osm(args.max, args.output))
