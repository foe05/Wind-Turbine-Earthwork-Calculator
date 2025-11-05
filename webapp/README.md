# Geo-Engineering Platform - Web Application

Microservices-basierte Web-Plattform für Geo-Engineering-Berechnungen.

## 🏗️ Architektur

```
┌─────────────────────────────────────────────┐
│ FRONTEND (React + Leaflet)                  │
│ Port: 3000                                  │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│ API GATEWAY (FastAPI)                       │
│ Port: 8000                                  │
│ - Routing, Auth Middleware, Job Queue      │
└──┬───┬───┬───┬───┬──────────────────────────┘
   │   │   │   │   │
   ▼   ▼   ▼   ▼   ▼
  Auth DEM Calc Cost Report
  8001 8002 8003 8004 8005
```

## 📦 Services

### 1. Auth Service (Port 8001) ✅ IMPLEMENTIERT
**Status:** Komplett
**Features:**
- Magic Link Authentifizierung (passwordless)
- JWT Token Management
- Email-Versand mit Templates
- Session-Tracking

**Endpoints:**
- `POST /auth/request-login` - Magic Link anfordern
- `GET /auth/verify/{token}` - Token verifizieren → JWT
- `GET /auth/me` - Current user
- `POST /auth/logout` - Logout

**Tech Stack:**
- FastAPI, SQLAlchemy, PostgreSQL
- python-jose (JWT)
- itsdangerous (Magic Links)
- aiosmtplib (Email)

---

### 2. DEM Service (Port 8002) ✅ IMPLEMENTIERT
**Status:** Komplett mit hoehendaten.de API Integration
**Features:**
- **hoehendaten.de API Integration** (1:1 aus QGIS Plugin übernommen)
- UTM-Koordinaten-Validierung (EPSG:25832-25836)
- 250m Buffer um jeden WKA-Standort
- 1km Kachel-Management
- Redis-Cache (6 Monate TTL)
- Automatisches Mosaik-Building

**Endpoints:**
- `POST /dem/fetch` - DEM von API holen
- `GET /dem/{dem_id}` - GeoTIFF download
- `GET /dem/{dem_id}/info` - Metadaten
- `GET /dem/cache/stats` - Cache-Statistiken

**WICHTIG - UTM-Koordinaten:**
```python
# Koordinaten MÜSSEN in UTM sein!
request = {
    "coordinates": [
        (497500, 5670500),  # UTM Easting, Northing
        (498000, 5671000)
    ],
    "crs": "EPSG:25832",  # UTM Zone 32
    "buffer_meters": 250.0  # Mind. 250m!
}
```

**Implementation Details:**
- `app/core/hoehendaten_api.py` - API-Integration (aus QGIS übernommen)
- `app/core/cache.py` - Redis-Cache-Manager
- `app/api/dem.py` - REST-Endpoints

---

### 3. Calculation Service (Port 8003) ✅ IMPLEMENTIERT
**Status:** Komplett
**Abhängigkeiten:** `shared/core/*`, DEM Service

**Module:**
```
app/modules/
├── optimization.py    # 3 Optimierungsmethoden (mean, min_cut, balanced)
├── platform.py        # Kranflächen Cut/Fill (polygon & rectangle)
└── profiles.py        # Schnittlinien (TODO)

app/core/
└── dem_sampling.py    # DEM-Sampling mit rasterio

Erweitert:
├── road.py           # Straßenbau-Modul (TODO)
└── solar.py          # Solar-Park-Modul (TODO)
```

**Endpoints:**
- `POST /calc/foundation/circular` - Kreisförmiges Fundament ✅
- `POST /calc/foundation/polygon` - Polygon-Fundament ✅
- `POST /calc/platform/rectangle` - Rechteckige Plattform ✅
- `POST /calc/platform/polygon` - Polygon-Plattform ✅
- `POST /calc/wka/site` - Komplette WKA-Berechnung ✅

**Features:**
- ✅ DEM-Sampling mit rasterio (statt QGIS)
- ✅ 3 Optimierungsmethoden für Plattformhöhe
- ✅ Material-Balance-Integration
- ✅ Automatischer DEM-Download vom DEM Service

**Beispiel:**
```bash
# Komplette WKA-Berechnung
curl -X POST http://localhost:8003/calc/wka/site \
  -H "Content-Type: application/json" \
  -d '{
    "dem_id": "uuid-from-dem-service",
    "center_x": 497500,
    "center_y": 5670500,
    "foundation_diameter": 22.0,
    "foundation_depth": 4.0,
    "platform_length": 45.0,
    "platform_width": 40.0,
    "optimization_method": "balanced",
    "material_reuse": true
  }'
```

---

### 4. Cost Service (Port 8004) ⚠️ TODO
**Status:** Noch zu implementieren
**Abhängigkeiten:** `shared/core/costs.py`, `shared/core/material_balance.py`

**Features:**
- Material-Bilanz (Wiederverwendung)
- Kostenberechnung mit Swell/Compaction
- Einsparungs-Analyse

**Endpoints (geplant):**
- `POST /costs/calculate` - Kosten berechnen

**Implementation:**
```python
# Nutze shared modules
from shared.core.material_balance import calculate_material_balance
from shared.core.costs import calculate_costs

material_balance = calculate_material_balance(
    foundation_volume=1000,
    crane_cut=500,
    crane_fill=800,
    swell_factor=1.25,
    compaction_factor=0.85
)

costs = calculate_costs(
    foundation_volume=1000,
    crane_cut=500,
    crane_fill=800,
    platform_area=1800,
    material_balance=material_balance,
    material_reuse=True
)
```

---

### 5. Report Service (Port 8005) ⚠️ TODO
**Status:** Noch zu implementieren

**Features:**
- HTML Report-Generierung (Jinja2 Templates)
- PDF Export (weasyprint)
- GeoJSON/GeoPackage Export
- Mehrere Templates: WKA, Road, Solar, Terrain

**Endpoints (geplant):**
- `POST /report/generate` - Report erstellen
- `GET /report/download/{job_id}/{filename}` - Report download

**Templates:**
```
templates/
├── wka_report.html          # Aus QGIS Plugin übernehmen
├── road_report.html
├── solar_report.html
└── terrain_report.html
```

---

### 6. API Gateway (Port 8000) ⚠️ TODO
**Status:** Noch zu implementieren

**Features:**
- Service-Routing
- Auth-Middleware (JWT validation)
- Rate Limiting
- WebSocket für Job-Progress
- Celery Job Queue

**Job-Flow:**
```python
1. User startet Berechnung
   → Job in DB (status: "pending")

2. Celery Worker:
   → "fetching_dem" (20%)
   → DEM Service Call

   → "calculating" (40%)
   → Calculation Service Calls

   → "computing_costs" (70%)
   → Cost Service Call

   → "generating_report" (90%)
   → Report Service Call

   → "completed" (100%)
```

---

## 🔧 Setup & Deployment

### Lokale Entwicklung

1. **Environment-Variablen:**
```bash
cp .env.example .env
# Bearbeite .env mit deinen SMTP-Credentials
```

2. **Starte Services:**
```bash
cd webapp
docker-compose up -d postgres redis
```

3. **Datenbank initialisieren:**
```bash
docker-compose exec postgres psql -U admin -d geo_engineering -f /docker-entrypoint-initdb.d/01-init.sql
```

4. **Service einzeln starten (Development):**
```bash
# Auth Service
cd services/auth_service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001

# DEM Service
cd services/dem_service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002
```

5. **Alle Services starten:**
```bash
docker-compose up --build
```

6. **Integration testen:**
```bash
./test-integration.sh
```

### Zugriff

- **API Gateway:** http://localhost:8000/docs (TODO)
- **Auth Service:** http://localhost:8001/docs
- **DEM Service:** http://localhost:8002/docs
- **Calculation Service:** http://localhost:8003/docs
- **Frontend:** http://localhost:3000 (TODO)

---

## 📚 Shared Modules

Die `shared/` Module enthalten die Berechnungslogik, die von mehreren Services genutzt wird:

### `shared/core/foundation.py` ✅
- `calculate_foundation_circular()` - Kreisförmiges Fundament
- `calculate_foundation_polygon()` - Polygon-Fundament

### `shared/core/material_balance.py` ✅
- `calculate_material_balance()` - Material-Bilanz mit Swell/Compaction

### `shared/core/costs.py` ✅
- `calculate_costs()` - Detaillierte Kostenberechnung

**Verwendung:**
```python
# In Calculation Service
import sys
sys.path.append('/shared')
from shared.core.foundation import calculate_foundation_circular
```

---

## 🧪 Testing

```bash
# Unit Tests
pytest tests/

# Einzelner Service
pytest tests/webapp/test_auth_service.py

# Integration Tests
pytest tests/webapp/test_integration.py
```

---

## 🚀 Production Deployment

### Fly.io
```bash
# Pro Service ein Deployment
fly launch --name geo-auth-service --region fra
fly launch --name geo-dem-service --region fra
...
```

### Railway
```bash
railway init
railway up
```

---

## 📋 Nächste Schritte

### Phase 1: Core-Services vervollständigen
1. ✅ Auth Service - **FERTIG**
2. ✅ DEM Service - **FERTIG**
3. ✅ Calculation Service - **FERTIG**
   - ✅ Foundation-Modul (circular & polygon)
   - ✅ Platform Cut/Fill-Modul (rectangle & polygon mit Rotation)
   - ✅ Optimization-Modul (3 Methoden)
   - ✅ DEM-Sampling mit rasterio
   - ✅ Integration mit DEM Service
4. ⚠️ Cost Service - **TODO**
   - API-Endpoints (nutze `shared/core/costs.py` und `material_balance.py`)
5. ⚠️ Report Service - **TODO**
   - HTML-Template aus QGIS Plugin übernehmen
   - PDF-Export mit weasyprint
6. ⚠️ API Gateway - **TODO**
   - Service-Routing
   - Celery Job Queue
   - WebSocket für Progress

### Phase 2: Frontend
1. React-App mit Leaflet-Karte
2. proj4js für UTM-Konvertierung (WICHTIG!)
3. Use-Case-spezifische Formulare
4. WebSocket-Integration für Live-Progress

### Phase 3: Erweiterte Use-Cases
1. Road-Modul (Straßenbau)
2. Solar-Modul (Solar-Park-Planung)
3. Terrain-Modul (Geländeanalyse)

---

## 🐛 Known Issues & Wichtige Hinweise

### ⚠️ KRITISCH: UTM-Koordinaten
- **hoehendaten.de API erwartet UTM-Koordinaten!**
- Frontend MUSS Lat/Lng → UTM konvertieren (proj4js)
- Mindestens 250m Buffer um WKA-Standorte
- Validierung: Deutschland EPSG:25832-25836

### ⚠️ QGIS Plugin vs Web-App
- Plugin bleibt unter `plugin/prototype/` erhalten
- Shared Module nutzen rasterio statt QGIS
- Keine Abhängigkeit von QGIS in Web-Services

### ⚠️ Cache-Management
- Redis-Cache: 6 Monate TTL
- File-Cache: `/app/cache` in DEM Service
- Regelmäßig `POST /dem/cache/clear-expired` aufrufen

---

## 📖 Dokumentation

- **API-Referenz:** http://localhost:8000/docs (Swagger)
- **QGIS Plugin:** `../plugin/prototype/WORKFLOW_STANDFLAECHEN.md`
- **hoehendaten.de Docs:** https://hoehendaten.de/api-rawtifrequest.html

---

## 🤝 Contributing

Siehe `../CONTRIBUTING.md`

---

## 📄 License

Siehe `../LICENSE`
