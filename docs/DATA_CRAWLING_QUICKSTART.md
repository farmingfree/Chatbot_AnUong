# 🚀 Data Crawling Quick Start

**Last updated:** 2026-05-06

---

## ✅ Current Status

### OpenStreetMap - DONE ✅
- **3,902 places** đã fetch thành công
- **File:** `apps/api/data/osm_places.json`
- **Coverage:** Toàn HCM (Quận 1, 3, Bình Thạnh, Tân Bình, Thủ Đức...)
- **Breakdown:** 1,946 restaurants, 1,396 cafes, 303 fast food, 152 bars, 105 food courts

```bash
# Data đã sẵn sàng sử dụng!
cat apps/api/data/osm_places.json | jq '.places | length'
# → 3902
```

---

## 🚀 Quick Start

### Option 1: Dùng OSM data có sẵn (RECOMMENDED cho MVP)
```bash
# Data đã có, không cần fetch lại!
cd apps/api
ls -lh data/osm_places.json

# Import vào DB (khi DB ready)
docker-compose up -d postgres
python import_osm_to_db.py --file=data/osm_places.json
```

### Option 2: Fetch thêm từ Google Maps (RECOMMENDED cho Production)
```bash
# Cần API key (free $200/month)
cd apps/api
python fetch_google.py --api-key=YOUR_KEY --max=2000

# Hoặc enrich OSM data
python fetch_google.py \
  --api-key=YOUR_KEY \
  --enrich-from=data/osm_places.json
```

### Option 3: Capture Foody/ShopeeFood (Optional)
```bash
# Cần capture từ browser (10 phút/nguồn)
# Xem hướng dẫn bên dưới
```

---

## 📊 So sánh nguồn data

| Source | Places | Quality | Effort | Cost | Status |
|--------|--------|---------|--------|------|--------|
| **OSM** | 3,902 | ⭐⭐⭐ | ✅ Done | Free | ✅ |
| **Google Maps** | ~5,000 | ⭐⭐⭐⭐⭐ | Easy | Free* | 📝 |
| **Foody** | ~3,000 | ⭐⭐⭐⭐ | Medium | Free | ⏳ |
| **ShopeeFood** | ~2,000 | ⭐⭐⭐⭐ | Medium | Free | ⏳ |

*Free tier: $200/month credit

---

## 🎯 Khuyến nghị

### Cho MVP/Testing (hiện tại):
```
✅ OSM: 3,902 places
✅ Đủ để test chatbot
✅ Coverage tốt toàn HCM
```

### Cho Production:
```
1. ✅ OSM (base) - Done
2. 🎯 Google Maps (enrich) - Recommended next
3. 📝 Foody (optional) - Vietnamese reviews
4. 📝 ShopeeFood (optional) - Delivery data
```

---

## 📖 Chi tiết từng nguồn

### 1. OpenStreetMap (OSM) - ✅ DONE

**Data có sẵn:** `apps/api/data/osm_places.json`

**Breakdown:**
```
Restaurants:  1,946 (50%)
Cafes:        1,396 (36%)
Fast food:      303 (8%)
Bars:           152 (4%)
Food courts:    105 (3%)
```

**Top districts:**
```
Quận 1:       879 places
Bình Thạnh:   757 places
Quận 3:       733 places
Tân Bình:     515 places
Thủ Đức:      361 places
```

**Data quality:**
- ✅ Name (100%)
- ✅ Lat/Lng (100%)
- ✅ District (100%)
- ⚠️ Address (70%)
- ⚠️ Phone (20%)
- ❌ Photos (0%)
- ❌ Reviews (0%)

**Fetch lại (nếu cần):**
```bash
cd apps/api
python fetch_osm.py --max=5000 --output=data/osm_places.json
```

---

### 2. Google Maps - 📝 TODO (Recommended)

**Why Google Maps?**
- ✅ Best data quality (photos, reviews, ratings)
- ✅ Official API (stable, reliable)
- ✅ Easy to implement
- ✅ Can enrich OSM data
- ✅ Free tier sufficient

**Setup:**
```bash
# 1. Get API key (free)
# https://console.cloud.google.com/
# Enable: Places API, Geocoding API

# 2. Fetch new places
python fetch_google.py --api-key=YOUR_KEY --max=2000

# 3. Or enrich OSM data (recommended)
python fetch_google.py \
  --api-key=YOUR_KEY \
  --enrich-from=data/osm_places.json \
  --output=data/places_enriched.json
```

**Benefits of enriching OSM:**
- Add photos (Google has best photos)
- Add reviews & ratings
- Verify/fix addresses
- Add phone numbers
- Add opening hours

---

### 3. Foody.vn - ⏳ NEEDS BROWSER CAPTURE

**Why manual capture?**
- ❌ No public API
- ❌ Requires browser cookies/tokens
- ❌ Anti-bot protection

**How to capture (10 minutes):**

1. **Mở trang Foody:**
   ```
   https://www.foody.vn/ho-chi-minh/dia-diem-an-uong
   ```

2. **Mở DevTools:**
   - Nhấn **F12**
   - Tab **Network** → Filter **XHR**

3. **Scroll trang:**
   - Scroll để load restaurants
   - Tìm request có URL chứa `foody.vn` hoặc `gappapi`
   - Response type: JSON với restaurant data

4. **Copy request:**
   - Click phải → **Copy** → **Copy as cURL**
   - Paste vào file: `foody_curl.txt`

5. **Parse và fetch:**
   ```bash
   cd apps/api
   python parse_foody_curl.py foody_curl.txt
   ```

**Expected output:** `data/foody_places.json` với ~2,000-5,000 places

---

### 4. ShopeeFood - ⏳ NEEDS BROWSER CAPTURE

**Setup tương tự Foody:**

1. **Mở:** https://shopeefood.vn/ho-chi-minh/food/delivery
2. **F12** → Network → XHR
3. **Search/scroll** → Tìm API request
4. **Copy as cURL** → Save to `shopee_curl.txt`
5. **Run:** `python parse_shopee_curl.py shopee_curl.txt`

**Expected output:** `data/shopee_places.json`

---

## 🔧 Tools Available

### Standalone Fetchers (no DB needed):
- ✅ `fetch_osm.py` - OpenStreetMap (done)
- 📝 `fetch_google.py` - Google Maps (TODO)
- ⏳ `parse_foody_curl.py` - Foody (needs capture)
- ⏳ `parse_shopee_curl.py` - ShopeeFood (needs capture)

### DB Pipeline:
```bash
# Import JSON to PostgreSQL
python import_osm_to_db.py --file=data/osm_places.json

# Or use pipeline (requires DB)
python -m data_pipeline osm --max=5000
python -m data_pipeline google --api-key=KEY
python -m data_pipeline manual --from-file=FILE
```

---

## 📝 Notes

1. **OSM data is sufficient for MVP** - 3,902 places covers most of HCM
2. **Google Maps recommended next** - Best ROI (quality vs effort)
3. **Foody/ShopeeFood optional** - Only if need Vietnamese-specific data
4. **All data saved as JSON** - Easy to import, merge, or analyze
5. **No DB required for fetching** - Can test/analyze immediately

---

## 🚀 Next Actions

**Start using data NOW:**
```bash
# Data is ready!
cat apps/api/data/osm_places.json | jq '.meta'

# Import to DB (when ready)
docker-compose up -d postgres
python import_osm_to_db.py --file=data/osm_places.json
```

**Enrich with Google Maps (Recommended):**
```bash
# Get free API key first, then:
python fetch_google.py \
  --api-key=YOUR_KEY \
  --enrich-from=data/osm_places.json
```

**Capture Foody/ShopeeFood (Optional):**
- Follow guide above
- Takes 10 minutes per source
- Adds Vietnamese-specific data

---

## 📚 Related Docs

- **[DATA_SOURCES_GUIDE.md](./DATA_SOURCES_GUIDE.md)** - Detailed comparison & troubleshooting
- **[DATA_PIPELINE_GUIDE.md](./DATA_PIPELINE_GUIDE.md)** - Pipeline architecture
- **[README.md](./README.md)** - Project setup & overview
