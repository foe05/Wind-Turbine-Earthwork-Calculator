#!/bin/bash
# 🔄 Migration: Add user_metadata column to users table

set -e

echo "🔄 Database Migration: Add user_metadata column"
echo "=============================================="
echo ""

# Check if column already exists
COLUMN_EXISTS=$(docker-compose exec -T postgres psql -U admin -d geo_engineering -tAc \
    "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='users' AND column_name='user_metadata';")

if [ "$COLUMN_EXISTS" -eq "1" ]; then
    echo "✅ Column 'user_metadata' already exists - no migration needed"
    exit 0
fi

echo "➕ Adding user_metadata column..."
docker-compose exec -T postgres psql -U admin -d geo_engineering -c \
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS user_metadata JSONB DEFAULT '{}'::jsonb;"

echo ""
echo "✅ Migration complete!"
echo ""
echo "🔍 Verify:"
docker-compose exec -T postgres psql -U admin -d geo_engineering -c "\d users"

echo ""
echo "🔓 Now try login:"
echo "   ./dev-login.sh test@example.com"
