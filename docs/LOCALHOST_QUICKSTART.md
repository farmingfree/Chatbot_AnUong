# 🚀 Localhost Quick Start Guide

## ⚠️ Vấn đề hiện tại

Bạn **chưa cài Docker Desktop**, nên không thể chạy PostgreSQL + Redis qua `docker-compose`.

## ✅ Giải pháp: Chạy frontend standalone

Frontend Next.js có thể chạy độc lập mà không cần backend. Chatbot sẽ báo lỗi khi gọi API, nhưng bạn vẫn xem được UI.

### Bước 1: Đợi npm install hoàn tất

npm install đang chạy background (có thể mất 2-5 phút). Kiểm tra xem đã xong chưa:

```bash
dir c:\Users\admin\Documents\chatbot_anuong\food-advisor\apps\web\node_modules
```

Nếu thấy thư mục `node_modules` có nhiều file → đã xong.

### Bước 2: Chạy Next.js dev server

```bash
cd c:\Users\admin\Documents\chatbot_anuong\food-advisor\apps\web
npm run dev
```

### Bước 3: Mở trình duyệt

```
http://localhost:3000
```

Bạn sẽ thấy giao diện chat, nhưng khi gửi tin nhắn sẽ báo lỗi vì không có backend.

---

## 🐳 Để chạy FULL STACK (cần Docker)

### Option 1: Cài Docker Desktop (Khuyến nghị)

1. Download: https://www.docker.com/products/docker-desktop/
2. Cài đặt và khởi động Docker Desktop
3. Chạy lại:

```bash
cd c:\Users\admin\Documents\chatbot_anuong\food-advisor
docker compose up -d
```

4. Chạy frontend:

```bash
cd apps\web
npm run dev
```

5. Mở: http://localhost:3000

---

### Option 2: Cài PostgreSQL + Redis thủ công (Phức tạp)

**PostgreSQL:**
1. Download: https://www.postgresql.org/download/windows/
2. Cài với PostGIS extension
3. Tạo database: `food_advisor`
4. Update `.env`:
   ```
   DATABASE_URL=postgresql://postgres:password@localhost:5432/food_advisor
   ```

**Redis:**
1. Download: https://github.com/microsoftarchive/redis/releases
2. Chạy: `redis-server`
3. Update `.env`:
   ```
   REDIS_URL=redis://localhost:6379
   ```

**Chạy API:**
```bash
cd c:\Users\admin\Documents\chatbot_anuong\food-advisor\apps\api
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

**Chạy Frontend:**
```bash
cd c:\Users\admin\Documents\chatbot_anuong\food-advisor\apps\web
npm run dev
```

---

## 📊 Kiểm tra trạng thái

### Frontend đã chạy chưa?
```bash
curl http://localhost:3000
```

### API đã chạy chưa? (cần Docker hoặc manual setup)
```bash
curl http://localhost:8000/health
```

### Docker services đang chạy?
```bash
docker ps
```

---

## 🎯 Khuyến nghị

**Cách nhanh nhất:** Cài Docker Desktop (5 phút), sau đó:

```bash
cd c:\Users\admin\Documents\chatbot_anuong\food-advisor
docker compose up -d
cd apps\web
npm run dev
```

Xong! Mở http://localhost:3000

---

## 🐛 Troubleshooting

### npm install bị lỗi peer dependency
```bash
npm --prefix c:\Users\admin\Documents\chatbot_anuong\food-advisor\apps\web install --legacy-peer-deps
```

### Port 3000 đã bị chiếm
```bash
# Tìm process đang dùng port 3000
netstat -ano | findstr :3000

# Kill process (thay PID)
taskkill /PID <PID> /F
```

### Port 8000 đã bị chiếm
```bash
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Docker không khởi động
- Mở Docker Desktop
- Đợi whale icon màu xanh
- Retry: `docker compose up -d`

---

## 📝 Environment Variables

File `.env` ở root đã có sẵn. Các biến quan trọng:

```env
# Database (cần Docker hoặc PostgreSQL local)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/food_advisor

# Redis (cần Docker hoặc Redis local)
REDIS_URL=redis://localhost:6379

# OpenAI (optional - có free mode)
OPENAI_API_KEY=

# Google Maps (optional)
GOOGLE_MAPS_API_KEY=

# NextAuth
NEXTAUTH_SECRET=your-secret-key-here
NEXTAUTH_URL=http://localhost:3000

# API URL
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## ✅ Checklist

- [ ] npm install xong (check `node_modules` folder)
- [ ] Docker Desktop cài và chạy (hoặc PostgreSQL + Redis manual)
- [ ] `docker compose up -d` thành công
- [ ] Frontend chạy: `npm run dev` → http://localhost:3000
- [ ] API health check: http://localhost:8000/health
- [ ] API docs: http://localhost:8000/docs

---

**Last updated:** 2026-05-06 17:09 ICT
