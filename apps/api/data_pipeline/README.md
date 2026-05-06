# 🍜 Food Advisor Data Pipeline

Pipeline tự động crawl và import dữ liệu quán ăn từ nhiều nguồn vào database.

## 📦 Cấu trúc

```
data_pipeline/
├── sources/          # Data sources (Google Maps, Foody, ShopeeFood, Manual)
├── processors/       # Data processing (Geocoder, Deduplicator, Normalizer)
├── storage/          # Database writer
└── __main__.py       # CLI entry point
```

## 🚀 Sử dụng

### 1. Google Maps (Cần API key - FREE $200/tháng)

```bash
cd apps/api
python -m data_pipeline google --api-key YOUR_API_KEY
```

**Ước tính:** ~3000+ quán từ 15 điểm grid covering HCM

### 2. Foody.vn (Web scraping - FREE)

```bash
python -m data_pipeline foody --max-pages 50
```

**Ước tính:** ~6000 quán (8 categories × 50 pages × 15 quán/page)

### 3. ShopeeFood (Internal API - FREE)

```bash
python -m data_pipeline shopee --max-per-district 200
```

**Ước tính:** ~2000 quán (10 quận × 200 quán/quận)

### 4. Manual Entry (Interactive hoặc JSON import)

**Interactive mode:**
```bash
python -m data_pipeline manual
```

**Import từ JSON:**
```bash
python -m data_pipeline manual --from-file data/my_places.json
```

JSON format:
```json
[
  {
    "name": "Phở Hòa Pasteur",
    "address": "260C Pasteur, Quận 3",
    "district": "Quận 3",
    "lat": 10.7836,
    "lng": 106.6885,
    "phone": "028 3829 7943",
    "price_min": 40000,
    "price_max": 80000,
    "rating": 4.5,
    "dishes": ["Phở", "Bún bò Huế"],
    "features": {"ac": true, "wifi": false}
  }
]
```

## 🔧 Features

### ✅ Deduplication
- Check source_id để tránh duplicate từ cùng nguồn
- Name + district similarity > 90%
- Geo proximity < 50m

### 🌍 Geocoding
- Tự động geocode địa chỉ thiếu tọa độ
- Sử dụng Nominatim (OpenStreetMap) - 100% FREE
- Rate limit: 1 request/giây

### 📊 Progress Tracking
- Real-time console output
- Summary report: new/updated/skipped

## 🎯 Workflow

```
Source → Fetch → Dedup Check → Geocode (if needed) → Write to DB
```

## 📝 Dependencies

Đã có trong `requirements.txt`:
- `httpx` - HTTP client
- `beautifulsoup4` - HTML parsing (Foody)
- `tqdm` - Progress bars

## 💡 Tips

1. **Chạy Google Maps trước** - có tọa độ chính xác nhất
2. **Sau đó Foody** - bổ sung menu chi tiết
3. **Cuối cùng ShopeeFood** - thêm delivery info
4. **Manual** - điền gaps hoặc quán đặc biệt

## ⚠️ Rate Limits

- **Google Maps:** $200 credit/tháng (~28,000 requests)
- **Nominatim:** 1 request/giây
- **Foody:** 1.5s delay giữa các requests
- **ShopeeFood:** 1s delay giữa các requests

## 🔍 Troubleshooting

**Lỗi import:**
```bash
# Chạy từ apps/api directory
cd apps/api
python -m data_pipeline google --api-key XXX
```

**Database connection:**
```bash
# Check .env có DATABASE_URL
cat .env | grep DATABASE_URL
```

**Geocoding fails:**
- Nominatim có thể block nếu quá nhiều requests
- Thêm delay hoặc dùng Google Geocoding API
