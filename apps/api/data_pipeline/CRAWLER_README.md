# Google Maps Playwright Crawler

Production-grade Google Maps crawler using Playwright browser automation. **No API key required.**

## Features

✅ **No API costs** — scrapes directly from google.com/maps
✅ **Stealth mode** — anti-bot evasion with randomized behavior
✅ **Retry logic** — exponential backoff on failures
✅ **Checkpoint system** — resume interrupted crawls
✅ **Review extraction** — captures user reviews with ratings
✅ **Structured data** — extracts embedded JSON from page state
✅ **Human-like behavior** — random delays, mouse movements, scrolling

## Installation

```bash
cd apps/api

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run database migration
alembic upgrade head
```

## Usage

### Basic crawl

```bash
python -m data_pipeline google_playwright --query "pho district 1 hcm"
```

### With options

```bash
python -m data_pipeline google_playwright \
  --query "coffee shop thao dien" \
  --max-results 50 \
  --no-resume
```

### Resume from checkpoint

```bash
# Crawl will automatically resume if interrupted
python -m data_pipeline google_playwright --query "bun bo quan 3"

# Force fresh start
python -m data_pipeline google_playwright --query "bun bo quan 3" --no-resume
```

## Query Examples

```bash
# By dish + district
python -m data_pipeline google_playwright --query "pho district 1 hcm"
python -m data_pipeline google_playwright --query "bun bo quan 3"
python -m data_pipeline google_playwright --query "banh mi thao dien"

# By category + area
python -m data_pipeline google_playwright --query "coffee shop district 2"
python -m data_pipeline google_playwright --query "vegetarian restaurant binh thanh"
python -m data_pipeline google_playwright --query "seafood restaurant vung tau"

# By cuisine
python -m data_pipeline google_playwright --query "japanese restaurant ho chi minh"
python -m data_pipeline google_playwright --query "italian pizza saigon"
```

## Architecture

### Data Flow

```
User Query
  ↓
Google Maps Search
  ↓
Scroll & Collect URLs (with stealth)
  ↓
Visit Each Place Page
  ↓
Extract Structured Data (from embedded JSON)
  ↓
Parse Reviews
  ↓
Geocode (if needed)
  ↓
Deduplicate
  ↓
Write to Database
```

### Key Components

| Component | Purpose |
|-----------|---------|
| `StealthBrowser` | Playwright wrapper with anti-bot evasion |
| `Checkpoint` | Save/resume crawl state |
| `retry_async` | Exponential backoff decorator |
| `GoogleMapsPlaywrightSource` | Main crawler implementation |
| `ReviewWriter` | Separate review storage |

### Anti-Bot Features

1. **Stealth scripts** — override `navigator.webdriver`, plugins, languages
2. **Random viewport** — 4 different screen sizes
3. **Random user agent** — rotates between Chrome/Firefox/Safari
4. **Human-like delays** — 500-2000ms random waits
5. **Smooth scrolling** — multi-step scroll with micro-delays
6. **Vietnamese locale** — timezone, language, geolocation set to HCM
7. **Mouse movements** — random cursor position on page load

## Data Extracted

### Place Fields

- `name` — restaurant name
- `address` — full address
- `lat`, `lng` — coordinates
- `district` — extracted from address
- `rating` — Google rating (0-5)
- `review_count` — number of reviews
- `price_level` — 1-4 scale
- `categories` — place types (e.g., "Vietnamese restaurant")
- `phone` — contact number
- `website` — official website
- `hours` — opening hours by day
- `image_urls` — photo URLs
- `source_id` — Google place ID for deduplication

### Review Fields

- `author_name` — reviewer name
- `rating` — 1-5 stars
- `content` — review text
- `published_at` — review date

## Checkpoint System

Checkpoints are saved every 10 places to `.checkpoints/` directory.

```json
{
  "query": "pho district 1 hcm",
  "seen_place_ids": ["ChIJ...", "ChIJ..."],
  "last_index": 20,
  "_saved_at": "2026-05-09T10:30:00"
}
```

Resume behavior:
- Automatically resumes if checkpoint exists
- Skips already-crawled places
- Clears checkpoint on successful completion
- Use `--no-resume` to force fresh start

## Error Handling

### Retry Logic

All network operations retry 3 times with exponential backoff:

```python
@retry_async(RetryConfig(max_attempts=3, base_delay=2.0))
async def _extract_place_data(self, page, url, place_id):
    ...
```

Delays: 2s → 4s → 8s

### Failure Modes

| Error | Behavior |
|-------|----------|
| Network timeout | Retry 3x, then skip place |
| CAPTCHA detected | Save screenshot, skip place, continue |
| No results found | Log warning, return empty |
| Parse error | Log error, skip place, continue |
| Database error | Propagate (stops crawl) |

### Logging

```python
import logging
logging.basicConfig(level=logging.INFO)
```

Logs include:
- Progress: `[15/100] Crawling: https://...`
- Checkpoints: `Checkpoint saved: .checkpoints/gmaps_pho_district_1.json`
- Errors: `Failed to extract place: TimeoutError`
- Summary: `✅ New places: 45, 🔄 Updated: 3, ⏭️ Skipped: 2`

## Performance

| Metric | Value |
|--------|-------|
| Speed | ~5-10 places/minute |
| Memory | ~200MB (Chromium browser) |
| Network | ~2-5 MB per place |
| Checkpoint interval | Every 10 places |

### Optimization Tips

1. **Headless mode** — faster, less resource usage (default)
2. **Max results** — limit with `--max-results 50`
3. **Parallel crawls** — run multiple queries in separate terminals
4. **Proxy rotation** — add proxy support for higher volume

## Troubleshooting

### Playwright not installed

```bash
playwright install chromium
```

### CAPTCHA blocking

- Reduce crawl speed (add longer delays)
- Use residential proxies
- Rotate user agents more frequently
- Run in non-headless mode to solve manually

### No results found

- Check query spelling
- Try broader query (e.g., "restaurant district 1" instead of specific dish)
- Verify Google Maps has results for that query in browser

### Database errors

```bash
# Run migration
alembic upgrade head

# Check Place model has required columns
psql -d food_advisor -c "\d places"
```

## Production Deployment

### Docker

```dockerfile
FROM python:3.11-slim

# Install Playwright dependencies
RUN apt-get update && apt-get install -y \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN playwright install chromium

COPY . .
CMD ["python", "-m", "data_pipeline", "google_playwright", "--query", "$QUERY"]
```

### Cron Job

```bash
# Crawl different queries daily
0 2 * * * cd /app && python -m data_pipeline google_playwright --query "pho district 1"
0 3 * * * cd /app && python -m data_pipeline google_playwright --query "coffee shop district 2"
0 4 * * * cd /app && python -m data_pipeline google_playwright --query "banh mi thao dien"
```

### Monitoring

```python
# Add to your monitoring system
from data_pipeline.sources.google_maps_playwright import GoogleMapsPlaywrightSource

source = GoogleMapsPlaywrightSource()
places_crawled = 0

async for place in source.fetch(query="pho district 1", max_results=100):
    places_crawled += 1
    # Send metric to Prometheus/Datadog
    metrics.increment("crawler.places_crawled")
```

## Comparison with API-based Crawler

| Feature | Playwright | Google Maps API |
|---------|-----------|-----------------|
| Cost | Free | $0.017/request |
| Rate limit | Soft (IP-based) | 100 req/day free |
| Data freshness | Real-time | Real-time |
| Reviews | ✅ Full text | ❌ Summary only |
| Setup | Playwright install | API key required |
| Reliability | Medium (anti-bot) | High |
| Speed | 5-10/min | 60/min |

## License

MIT

## Support

Issues: https://github.com/your-repo/issues
Docs: https://docs.your-domain.com/crawler
