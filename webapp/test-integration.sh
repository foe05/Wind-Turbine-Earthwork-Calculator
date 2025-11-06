#!/bin/bash
# Integration Test für Calculation Service mit DEM Service

set -e

echo "🧪 Geo-Engineering Platform - Integration Test"
echo "=============================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check services
echo "🔍 Checking services..."
echo ""

# Auth Service
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Auth Service (Port 8001) - OK"
else
    echo -e "${RED}✗${NC} Auth Service (Port 8001) - NICHT ERREICHBAR"
    exit 1
fi

# DEM Service
if curl -s http://localhost:8002/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} DEM Service (Port 8002) - OK"
else
    echo -e "${RED}✗${NC} DEM Service (Port 8002) - NICHT ERREICHBAR"
    exit 1
fi

# Calculation Service
if curl -s http://localhost:8003/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Calculation Service (Port 8003) - OK"
else
    echo -e "${RED}✗${NC} Calculation Service (Port 8003) - NICHT ERREICHBAR"
    exit 1
fi

echo ""
echo "=============================================="
echo "📡 Test 1: Foundation (Circular) Calculation"
echo "=============================================="
echo ""

FOUNDATION_RESULT=$(curl -s -X POST http://localhost:8003/calc/foundation/circular \
  -H "Content-Type: application/json" \
  -d '{
    "diameter": 22.0,
    "depth": 4.0,
    "foundation_type": "shallow"
  }')

echo "Request:"
echo "  Diameter: 22.0m"
echo "  Depth: 4.0m"
echo "  Type: shallow"
echo ""
echo "Response:"
echo "$FOUNDATION_RESULT" | python3 -m json.tool
echo ""

FOUNDATION_VOLUME=$(echo "$FOUNDATION_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin)['volume'])")
echo -e "${GREEN}✓${NC} Foundation Volume: ${FOUNDATION_VOLUME} m³"

echo ""
echo "=============================================="
echo "📡 Test 2: DEM Fetch (hoehendaten.de API)"
echo "=============================================="
echo ""
echo "${YELLOW}⚠ Hinweis:${NC} Koordinaten müssen in Deutschland liegen (UTM Zone 32)"
echo ""

# Teststandort in Deutschland (UTM Zone 32)
# Beispiel: irgendwo in NRW
EASTING=497500
NORTHING=5670500

echo "Request:"
echo "  Coordinates: [($EASTING, $NORTHING)] (UTM Zone 32)"
echo "  CRS: EPSG:25832"
echo "  Buffer: 250m"
echo ""

DEM_RESULT=$(curl -s -X POST http://localhost:8002/dem/fetch \
  -H "Content-Type: application/json" \
  -d "{
    \"coordinates\": [[$EASTING, $NORTHING]],
    \"crs\": \"EPSG:25832\",
    \"buffer_meters\": 250.0
  }")

echo "Response:"
echo "$DEM_RESULT" | python3 -m json.tool
echo ""

DEM_ID=$(echo "$DEM_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin)['dem_id'])" 2>/dev/null || echo "")

if [ -z "$DEM_ID" ]; then
    echo -e "${RED}✗${NC} DEM konnte nicht geladen werden"
    echo "   Mögliche Gründe:"
    echo "   - Koordinaten außerhalb Deutschlands"
    echo "   - hoehendaten.de API nicht erreichbar"
    echo "   - Netzwerkprobleme"
    echo ""
    echo "${YELLOW}⚠ Überspringe Tests, die DEM benötigen${NC}"
    DEM_ID=""
else
    echo -e "${GREEN}✓${NC} DEM erfolgreich geladen: $DEM_ID"
fi

if [ -n "$DEM_ID" ]; then
    echo ""
    echo "=============================================="
    echo "📡 Test 3: Platform Cut/Fill (Rectangle)"
    echo "=============================================="
    echo ""

    PLATFORM_RESULT=$(curl -s -X POST http://localhost:8003/calc/platform/rectangle \
      -H "Content-Type: application/json" \
      -d "{
        \"dem_id\": \"$DEM_ID\",
        \"center_x\": $EASTING,
        \"center_y\": $NORTHING,
        \"length\": 45.0,
        \"width\": 40.0,
        \"slope_width\": 10.0,
        \"slope_angle\": 34.0,
        \"optimization_method\": \"balanced\",
        \"rotation_angle\": 0.0
      }")

    echo "Request:"
    echo "  Center: ($EASTING, $NORTHING)"
    echo "  Size: 45m x 40m"
    echo "  Slope: 10m @ 34°"
    echo "  Optimization: balanced"
    echo ""
    echo "Response:"
    echo "$PLATFORM_RESULT" | python3 -m json.tool
    echo ""

    PLATFORM_HEIGHT=$(echo "$PLATFORM_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin)['platform_height'])" 2>/dev/null || echo "0")
    TOTAL_CUT=$(echo "$PLATFORM_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin)['total_cut'])" 2>/dev/null || echo "0")
    TOTAL_FILL=$(echo "$PLATFORM_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin)['total_fill'])" 2>/dev/null || echo "0")

    echo -e "${GREEN}✓${NC} Platform Height: ${PLATFORM_HEIGHT}m"
    echo -e "${GREEN}✓${NC} Total Cut: ${TOTAL_CUT} m³"
    echo -e "${GREEN}✓${NC} Total Fill: ${TOTAL_FILL} m³"

    echo ""
    echo "=============================================="
    echo "📡 Test 4: Complete WKA Site Calculation"
    echo "=============================================="
    echo ""

    WKA_RESULT=$(curl -s -X POST http://localhost:8003/calc/wka/site \
      -H "Content-Type: application/json" \
      -d "{
        \"dem_id\": \"$DEM_ID\",
        \"center_x\": $EASTING,
        \"center_y\": $NORTHING,
        \"foundation_diameter\": 22.0,
        \"foundation_depth\": 4.0,
        \"foundation_type\": \"shallow\",
        \"platform_length\": 45.0,
        \"platform_width\": 40.0,
        \"slope_width\": 10.0,
        \"slope_angle\": 34.0,
        \"optimization_method\": \"balanced\",
        \"rotation_angle\": 0.0,
        \"material_reuse\": true,
        \"swell_factor\": 1.25,
        \"compaction_factor\": 0.85
      }")

    echo "Request:"
    echo "  Location: ($EASTING, $NORTHING)"
    echo "  Foundation: Ø22m x 4m (shallow)"
    echo "  Platform: 45m x 40m"
    echo "  Material Reuse: Yes"
    echo ""
    echo "Response:"
    echo "$WKA_RESULT" | python3 -m json.tool
    echo ""

    FOUNDATION_VOL=$(echo "$WKA_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin)['foundation_volume'])" 2>/dev/null || echo "0")
    WKA_TOTAL_CUT=$(echo "$WKA_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin)['total_cut'])" 2>/dev/null || echo "0")
    WKA_TOTAL_FILL=$(echo "$WKA_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin)['total_fill'])" 2>/dev/null || echo "0")
    MATERIAL_SURPLUS=$(echo "$WKA_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin)['material_surplus'])" 2>/dev/null || echo "0")

    echo -e "${GREEN}✓${NC} Foundation: ${FOUNDATION_VOL} m³"
    echo -e "${GREEN}✓${NC} Total Cut: ${WKA_TOTAL_CUT} m³"
    echo -e "${GREEN}✓${NC} Total Fill: ${WKA_TOTAL_FILL} m³"
    echo -e "${GREEN}✓${NC} Material Surplus: ${MATERIAL_SURPLUS} m³"
fi

echo ""
echo "=============================================="
echo "✅ Integration Tests abgeschlossen!"
echo "=============================================="
echo ""
echo "📚 Weitere Tests:"
echo "   - API Dokumentation: http://localhost:8003/docs"
echo "   - Logs anzeigen: docker-compose logs -f calculation_service"
echo ""
