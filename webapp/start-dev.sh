#!/bin/bash
# Quick Start Script für Geo-Engineering Platform Development

set -e

echo "🚀 Geo-Engineering Platform - Development Setup"
echo "================================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker ist nicht gestartet. Bitte starte Docker Desktop."
    exit 1
fi

echo "✅ Docker läuft"
echo ""

# Start infrastructure
echo "📦 Starte PostgreSQL + Redis..."
docker-compose up -d postgres redis

echo "⏳ Warte auf PostgreSQL..."
sleep 5

# Check if database is ready
until docker-compose exec -T postgres pg_isready -U admin -d geo_engineering > /dev/null 2>&1; do
    echo "   Warte auf Datenbank..."
    sleep 2
done

echo "✅ PostgreSQL bereit"
echo ""

# Check if database is initialized
echo "🔍 Prüfe Datenbank-Schema..."
TABLE_COUNT=$(docker-compose exec -T postgres psql -U admin -d geo_engineering -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")

if [ "$TABLE_COUNT" -lt 5 ]; then
    echo "📝 Initialisiere Datenbank-Schema..."
    docker-compose exec -T postgres psql -U admin -d geo_engineering < init-db/01-init.sql
    echo "✅ Schema erstellt"
else
    echo "✅ Schema bereits vorhanden ($TABLE_COUNT Tabellen)"
fi

echo ""

# Start services
echo "🚀 Starte Microservices..."
echo ""

# Auth Service
if docker-compose ps | grep -q "geo_auth.*Up"; then
    echo "✅ Auth Service läuft bereits (Port 8001)"
else
    echo "🔧 Starte Auth Service..."
    docker-compose up -d auth_service
    sleep 3
fi

# DEM Service
if docker-compose ps | grep -q "geo_dem.*Up"; then
    echo "✅ DEM Service läuft bereits (Port 8002)"
else
    echo "🔧 Starte DEM Service..."
    docker-compose up -d dem_service
    sleep 3
fi

echo ""
echo "================================================"
echo "✨ Services gestartet!"
echo "================================================"
echo ""
echo "📚 API-Dokumentation:"
echo "   Auth Service:  http://localhost:8001/docs"
echo "   DEM Service:   http://localhost:8002/docs"
echo ""
echo "🔍 Health Checks:"
echo "   curl http://localhost:8001/health"
echo "   curl http://localhost:8002/health"
echo ""
echo "💾 Datenbank:"
echo "   Host: localhost:5432"
echo "   DB:   geo_engineering"
echo "   User: admin"
echo ""
echo "📊 Redis:"
echo "   Host: localhost:6379"
echo ""
echo "🛑 Stoppen:"
echo "   docker-compose down"
echo ""
echo "📝 Logs anzeigen:"
echo "   docker-compose logs -f auth_service"
echo "   docker-compose logs -f dem_service"
echo ""
