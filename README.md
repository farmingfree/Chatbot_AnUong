# Food Advisor - Gợi ý ăn uống HCM

Web app gợi ý quán ăn, món ăn tại TP.HCM sử dụng AI.

## Tech Stack

- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS
- **Backend**: FastAPI, SQLAlchemy, PostgreSQL + PostGIS
- **Cache**: Redis
- **AI**: OpenAI API
- **Maps**: Google Maps API

## Quick Start

```bash
# 1. Clone repo
git clone <repo-url>
cd food-advisor

# 2. Tạo file .env
cp .env.example .env
# Điền các API keys cần thiết

# 3. Khởi động services (Postgres, Redis, API)
docker-compose up -d

# 4. Import dữ liệu nhà hàng (QUAN TRỌNG)
cd apps/api
python -m data_pipeline google --api-key YOUR_GOOGLE_API_KEY
# Hoặc xem: DATA_CRAWLING_QUICKSTART.md

# 5. Cài đặt frontend
cd ../web
npm install

# 6. Chạy frontend dev server
npm run dev
```

Truy cập:
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 📊 Data Crawling

Xem hướng dẫn chi tiết:
- **[DATA_CRAWLING_QUICKSTART.md](./DATA_CRAWLING_QUICKSTART.md)** - Quick start
- **[DATA_SOURCES_GUIDE.md](./DATA_SOURCES_GUIDE.md)** - Hướng dẫn đầy đủ

**TL;DR:**
```bash
# Recommended: Google Maps (data sạch nhất)
cd apps/api
python -m data_pipeline google --api-key YOUR_KEY

# Alternative: OSM (free, không cần API key)
python -m data_pipeline osm --max=5000

# Advanced: Foody + ShopeeFood (cần capture từ browser)
# Xem DATA_SOURCES_GUIDE.md
```

## 📚 Documentation

- [USER_AUTH_SETUP.md](./USER_AUTH_SETUP.md) - User authentication
- [CHAT_STREAMING_SETUP.md](./CHAT_STREAMING_SETUP.md) - Chat streaming
- [CHAT_SESSION_MANAGEMENT.md](./CHAT_SESSION_MANAGEMENT.md) - Session management
- [CHATBOT_IMPROVEMENTS.md](./CHATBOT_IMPROVEMENTS.md) - Chatbot features
