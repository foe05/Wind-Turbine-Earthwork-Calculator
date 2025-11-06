#!/bin/bash
# 🔄 Reset Database - Drop and recreate with fresh schema

set -e

echo "🗑️  Resetting Database..."
echo "======================================"
echo ""
echo "⚠️  WARNING: This will delete ALL data!"
echo ""
read -p "Continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cancelled"
    exit 1
fi

echo ""
echo "1️⃣  Stopping services..."
docker-compose stop api_gateway auth_service celery_worker

echo ""
echo "2️⃣  Dropping database..."
docker-compose exec -T postgres psql -U admin -d geo_engineering -c "DROP SCHEMA public CASCADE;"
docker-compose exec -T postgres psql -U admin -d geo_engineering -c "CREATE SCHEMA public;"
docker-compose exec -T postgres psql -U admin -d geo_engineering -c "GRANT ALL ON SCHEMA public TO admin;"
docker-compose exec -T postgres psql -U admin -d geo_engineering -c "GRANT ALL ON SCHEMA public TO public;"

echo ""
echo "3️⃣  Running init scripts..."
docker-compose exec -T postgres psql -U admin -d geo_engineering < init-db/01-init.sql

echo ""
echo "4️⃣  Loading demo data (optional)..."
read -p "Load demo data? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose exec -T postgres psql -U admin -d geo_engineering < init-db/02-demo-data.sql
    echo "✅ Demo data loaded"
else
    echo "⏭️  Skipped demo data"
fi

echo ""
echo "5️⃣  Restarting services..."
docker-compose start api_gateway auth_service celery_worker

echo ""
echo "⏳ Waiting for services to start (10 seconds)..."
sleep 10

echo ""
echo "✅ Database reset complete!"
echo ""
echo "📊 Verify with:"
echo "   docker-compose exec postgres psql -U admin -d geo_engineering -c '\d users'"
echo ""
echo "🔓 Try login:"
echo "   ./dev-login.sh test@example.com"
