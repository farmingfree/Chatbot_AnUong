# Food Advisor API

FastAPI backend for HCM food recommendation system with PostGIS spatial queries.

## Features

- 🗺️ **Geospatial Search**: Find nearby restaurants using PostGIS ST_DWithin
- 🍜 **Dish-based Search**: Search by Vietnamese dish names (phở, cơm tấm, etc.)
- 💰 **Budget Filtering**: Filter by price per person and group size
- 🥗 **Dietary Filters**: Vegetarian and Halal options
- ⏰ **Real-time Status**: Check if places are open now (Vietnam timezone)
- 📊 **Rich Data**: Ratings, reviews, hours, features, images

## Tech Stack

- **FastAPI** - Modern async Python web framework
- **PostgreSQL + PostGIS** - Spatial database for geo queries
- **SQLAlchemy 2.0** - Async ORM
- **Pydantic** - Data validation
- **Redis** - Caching (future)

## Setup

### 1. Start Database

```bash
cd food-advisor
docker-compose up -d
```

This starts:
- PostgreSQL 16 with PostGIS 3.4 (port 5432)
- Redis 7 (port 6379)

### 2. Install Dependencies

```bash
cd apps/api
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 4. Create Tables

```bash
python create_tables.py
```

This creates all tables with PostGIS geometry columns and indexes.

### 5. Seed Data

**Option A: Static Data (50 curated places)**
```bash
python seed_static.py
```

**Option B: Google Places API (requires API key)**
```bash
# Set GOOGLE_MAPS_API_KEY in .env
python seed_data.py
```

### 6. Run API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## API Endpoints

### POST /api/places/nearby

Find nearby places with filters.

**Request:**
```json
{
  "lat": 10.7769,
  "lng": 106.7009,
  "radius_m": 1000,
  "limit": 20,
  "price_max_per_person": 150000,
  "people_count": 2,
  "vegetarian": false,
  "halal": false,
  "dish_name": "phở"
}
```

**Response:**
```json
{
  "places": [
    {
      "id": "uuid",
      "name": "Phở Hòa Pasteur",
      "address": "260C Pasteur, Q.3",
      "district": "Quận 3",
      "distance_m": 450,
      "rating": 4.4,
      "review_count": 2847,
      "price_level": 2,
      "price_range": "80,000đ - 150,000đ",
      "image_url": "https://...",
      "is_open_now": true,
      "top_dishes": ["Phở bò", "Phở gà", "Phở đặc biệt"]
    }
  ],
  "total": 15,
  "center_lat": 10.7769,
  "center_lng": 106.7009,
  "radius_m": 1000
}
```

### GET /api/places/{place_id}

Get detailed place information.

**Response:**
```json
{
  "id": "uuid",
  "name": "Phở Hòa Pasteur",
  "address": "260C Pasteur, Q.3",
  "lat": 10.7791,
  "lng": 106.6923,
  "district": "Quận 3",
  "phone": "028 3829 7943",
  "google_place_id": "ChIJ...",
  "price_min": 80000,
  "price_max": 150000,
  "price_level": 2,
  "rating_google": 4.4,
  "review_count": 2847,
  "hours": {
    "mon": "06:00-22:00",
    "tue": "06:00-22:00",
    ...
  },
  "features": {
    "ac": true,
    "wifi": false,
    "parking": false,
    "vegetarian": false,
    "halal": false
  },
  "is_closed": false,
  "is_open_now": true,
  "image_urls": ["https://..."],
  "dishes": ["Phở bò", "Phở gà", "Phở đặc biệt"],
  "reviews": [
    {
      "id": "uuid",
      "user_name": "John Doe",
      "rating": 5,
      "comment": "Great phở!",
      "created_at": "2024-01-15T10:30:00"
    }
  ],
  "last_crawled_at": "2024-01-20T08:00:00",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-20T08:00:00"
}
```

## Testing

Run the test script:

```bash
python test_nearby.py
```

This tests:
1. Basic nearby search
2. Budget filtering
3. Vegetarian filtering
4. Dish name search
5. Place detail retrieval

## Database Schema

### Tables

- **places** - Restaurant/cafe locations with PostGIS geometry
- **dishes** - Vietnamese dishes (phở, cơm tấm, etc.)
- **place_dishes** - Many-to-many relationship
- **reviews** - User reviews
- **users** - User accounts (future)
- **favorites** - User favorites (future)

### Key Indexes

- `idx_places_geom_gist` - GiST index on geometry for spatial queries
- `idx_places_district` - B-tree index on district
- `idx_dishes_name_normalized` - B-tree index for dish search

## Query Performance

The nearby search uses PostGIS `ST_DWithin` with a GiST index for optimal performance:

```sql
WHERE ST_DWithin(
  p.geom::geography,
  ST_MakePoint(:lng, :lat)::geography,
  :radius_m
)
```

This efficiently finds all places within radius without scanning the entire table.

## Data Sources

### Static Data (50 places)
- `data/places_hcm.json` - Curated list of popular HCM restaurants
- Covers Quận 1, 3, 5, 7, Bình Thạnh, Tân Bình, Gò Vấp, Thủ Đức
- Includes phở, cơm tấm, bánh mì, bún bò, vegetarian, cafes, etc.

### Google Places API (optional)
- `seed_data.py` - Crawl real data from Google Places
- Requires `GOOGLE_MAPS_API_KEY` in .env
- Supports multiple districts and dish types

## Development

### Project Structure

```
apps/api/
├── app/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings
│   ├── database.py          # DB connection
│   ├── models/              # SQLAlchemy models
│   │   ├── place.py
│   │   ├── dish.py
│   │   ├── place_dish.py
│   │   ├── review.py
│   │   ├── user.py
│   │   └── favorite.py
│   ├── schemas/             # Pydantic schemas
│   │   ├── place.py
│   │   ├── dish.py
│   │   └── chat.py
│   ├── routers/             # API routes
│   │   └── places.py
│   └── services/            # Business logic (future)
├── data/
│   └── places_hcm.json      # Static seed data
├── create_tables.py         # DB initialization
├── seed_static.py           # Seed from JSON
├── seed_data.py             # Seed from Google API
├── test_nearby.py           # API tests
├── requirements.txt
├── Dockerfile
└── .env
```

### Adding New Endpoints

1. Create schema in `app/schemas/`
2. Create router in `app/routers/`
3. Register router in `app/main.py`

### Database Migrations

Currently using direct SQLAlchemy table creation. For production, consider:
- Alembic for migrations
- Separate migration scripts

## Deployment

### Docker

```bash
# Build image
docker build -t food-advisor-api .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://... \
  food-advisor-api
```

### Environment Variables

Required:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string

Optional:
- `OPENAI_API_KEY` - For AI chat features
- `GOOGLE_MAPS_API_KEY` - For Google Places crawling
- `NEXTAUTH_SECRET` - For authentication (future)

## License

MIT
