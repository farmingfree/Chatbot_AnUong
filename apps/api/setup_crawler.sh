#!/bin/bash
# Quick start script for Google Maps Playwright crawler

set -e

echo "🚀 Setting up Google Maps Playwright Crawler..."

# Check if in correct directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: Run this script from apps/api directory"
    exit 1
fi

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install Playwright browsers
echo "🌐 Installing Playwright browsers..."
playwright install chromium

# Run database migration
echo "🗄️  Running database migration..."
alembic upgrade head

echo ""
echo "✅ Setup complete!"
echo ""
echo "📖 Usage examples:"
echo ""
echo "  # Crawl pho restaurants in District 1"
echo "  python -m data_pipeline google_playwright --query 'pho district 1 hcm'"
echo ""
echo "  # Crawl coffee shops in Thao Dien"
echo "  python -m data_pipeline google_playwright --query 'coffee shop thao dien' --max-results 50"
echo ""
echo "  # Resume interrupted crawl"
echo "  python -m data_pipeline google_playwright --query 'bun bo quan 3'"
echo ""
echo "📚 Full documentation: data_pipeline/CRAWLER_README.md"
