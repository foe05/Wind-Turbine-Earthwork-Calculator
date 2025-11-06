#!/bin/bash
# 🔄 Migration: Add created_at column to magic_links table

set -e

echo "🔄 Database Migration: Add magic_links.created_at column"
echo "=========================================================="
echo ""

# Check if column already exists
COLUMN_EXISTS=$(docker-compose exec -T postgres psql -U admin -d geo_engineering -tAc \
    "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='magic_links' AND column_name='created_at';")

if [ "$COLUMN_EXISTS" -eq "1" ]; then
    echo "✅ Column 'created_at' already exists - no migration needed"
    exit 0
fi

echo "➕ Adding created_at column to magic_links table..."
docker-compose exec -T postgres psql -U admin -d geo_engineering -c \
    "ALTER TABLE magic_links ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();"

echo ""
echo "📊 Creating index on created_at..."
docker-compose exec -T postgres psql -U admin -d geo_engineering -c \
    "CREATE INDEX IF NOT EXISTS idx_magic_links_created_at ON magic_links(created_at);"

echo ""
echo "✅ Migration complete!"
echo ""
echo "🔍 Verify:"
docker-compose exec -T postgres psql -U admin -d geo_engineering -c "\d magic_links"

echo ""
echo "🔄 Restarting auth service to pick up changes..."
docker-compose restart auth_service

echo ""
echo "⏳ Waiting for service to start (5 seconds)..."
sleep 5

echo ""
echo "✅ Ready to test!"
echo ""
echo "🔓 Now try login:"
echo "   ./dev-login.sh test@example.com"
