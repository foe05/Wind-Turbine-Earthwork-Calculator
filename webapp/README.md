# Geo-Engineering Platform

Microservices-based web application for Wind Turbine (WKA) Earthwork Calculations. This platform complements the existing QGIS Plugin and provides a modern web-based interface for calculating earthwork volumes, costs, and generating reports.

## 🎯 Overview

The platform consists of 6 microservices orchestrated with Docker Compose:

1. **Auth Service** (Port 8001) - Magic Link authentication ✅
2. **DEM Service** (Port 8002) - Digital Elevation Model data management ✅
3. **Calculation Service** (Port 8003) - Earthwork calculations ✅
4. **Cost Service** (Port 8004) - Cost analysis ✅
5. **Report Service** (Port 8005) - HTML/PDF report generation ✅
6. **API Gateway** (Port 8000) - Central routing and authentication ✅

Plus:
- **Frontend** (Port 3000) - React + Leaflet web interface ✅
- **PostgreSQL + PostGIS** - Spatial database
- **Redis** - Caching layer

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                        │
│          Leaflet Maps + proj4 UTM Conversion                │
│                      Port 3000                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway (Port 8000)                  │
│           Routing, Auth Middleware, Rate Limiting           │
└───┬────────┬──────────┬──────────┬──────────┬──────────────┘
    │        │          │          │          │
    ▼        ▼          ▼          ▼          ▼
┌──────┐ ┌──────┐ ┌─────────┐ ┌──────┐ ┌────────┐
│ Auth │ │ DEM  │ │  Calc   │ │ Cost │ │ Report │
│ 8001 │ │ 8002 │ │  8003   │ │ 8004 │ │  8005  │
└──────┘ └──┬───┘ └─────────┘ └──────┘ └────────┘
           │
           ▼
    ┌──────────────┐
    │ hoehendaten  │
    │     API      │
    └──────────────┘
```

## ✨ Key Features

### Phase 1 (✅ COMPLETED)
- ✅ Magic Link authentication (passwordless)
- ✅ Interactive Leaflet map with WKA site placement
- ✅ Automatic Lat/Lng to UTM coordinate conversion (proj4)
- ✅ DEM data fetching from hoehendaten.de API
- ✅ Foundation calculations (circular, polygon)
- ✅ Platform calculations with 3 optimization methods
- ✅ Material balance with swell/compaction factors
- ✅ Cost calculations with preset rate options
- ✅ PDF report generation with Jinja2 templates
- ✅ Redis caching (6-month TTL for DEM tiles)
- ✅ Docker Compose orchestration

### Phase 2 (🔜 Planned)
- 🔜 Road earthwork calculations
- 🔜 Solar park earthwork calculations
- 🔜 General terrain modeling
- 🔜 Multi-user project collaboration
- 🔜 Real-time progress tracking (WebSocket)
- 🔜 Historical project archives

## ⚠️ Critical Requirements

### Coordinate System
**MANDATORY**: All calculations use **UTM coordinates (EPSG:25832-25836)** for Germany
- Frontend automatically converts Lat/Lng to UTM using proj4
- hoehendaten.de API requires UTM coordinates
- Germany is primarily in UTM zones 32 and 33

### DEM Buffer
**MANDATORY**: **250m buffer** around WKA sites (NOT 100m)
- Ensures sufficient terrain data for slope calculations
- Buffer is applied in DEM fetch requests

### hoehendaten.de API
- German elevation data API
- Returns Base64-encoded GeoTIFF tiles
- 1km × 1km tile size
- Cached in Redis for 6 months

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Git
- (Optional) Node.js 18+ for local frontend development
- (Optional) Python 3.11+ for local service development

### 1. Clone Repository
```bash
git clone https://github.com/foe05/Wind-Turbine-Earthwork-Calculator.git
cd Wind-Turbine-Earthwork-Calculator/webapp
```

### 2. Configure Environment
```bash
# Copy example env files
cp .env.example .env

# Edit .env with your settings
# IMPORTANT: Set SMTP credentials for Magic Link authentication
nano .env
```

Required environment variables:
```env
# SMTP for Magic Link
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@geo-engineering.example.com

# JWT Secret
JWT_SECRET=change-this-to-a-secure-random-string

# Database
POSTGRES_PASSWORD=change-this-in-production
```

### 3. Start All Services
```bash
docker-compose up -d

# View logs
docker-compose logs -f

# Check service health
docker-compose ps
```

### 4. Access Application
- **Frontend**: http://localhost:3000
- **API Gateway**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### 5. First Login
1. Navigate to http://localhost:3000
2. Enter your email address
3. Check your email for the Magic Link
4. Click the link to log in

## 📦 Service Details

### 1. Auth Service (Port 8001) ✅
**Purpose**: User authentication with Magic Links (passwordless)

**Key Endpoints**:
- `POST /auth/request-login` - Request magic link
- `GET /auth/verify/{token}` - Verify token and get JWT
- `GET /auth/me` - Get current user info
- `POST /auth/logout` - Invalidate session

**Tech Stack**: FastAPI, PostgreSQL, SQLAlchemy, python-jose (JWT)

---

### 2. DEM Service (Port 8002) ✅
**Purpose**: Digital Elevation Model data management and caching

**Key Endpoints**:
- `POST /dem/fetch` - Fetch DEM tiles for coordinates
- `GET /dem/{dem_id}` - Get cached DEM data
- `GET /dem/cache/stats` - Cache statistics

**Tech Stack**: FastAPI, Redis, requests, rasterio

**Critical**:
- Requires UTM coordinates (EPSG:25832-25836)
- 250m buffer requirement
- Caches tiles for 6 months in Redis
- Integrates with hoehendaten.de API

**Implementation Details**:
- `app/core/hoehendaten_api.py` - API integration (copied 1:1 from QGIS Plugin)
- `app/core/cache.py` - Redis cache manager
- `app/api/dem.py` - REST endpoints

---

### 3. Calculation Service (Port 8003) ✅
**Purpose**: Earthwork volume calculations

**Key Endpoints**:
- `POST /calc/foundation/circular` - Circular foundation
- `POST /calc/foundation/polygon` - Polygon foundation
- `POST /calc/platform/rectangle` - Rectangular platform
- `POST /calc/platform/polygon` - Polygon platform
- `POST /calc/wka/site` - Complete WKA site calculation

**Tech Stack**: FastAPI, NumPy, rasterio, shapely

**Optimization Methods**:
1. **mean**: Average elevation of sample points
2. **min_cut**: 40th percentile (minimize cut)
3. **balanced**: Binary search for cut/fill balance

**Module Structure**:
```
app/modules/
├── optimization.py    # 3 optimization methods
├── platform.py        # Platform cut/fill (polygon & rectangle)
└── profiles.py        # Cross-section profiles (TODO Phase 2)

app/core/
└── dem_sampling.py    # DEM sampling with rasterio

Future (Phase 2):
├── road.py           # Road construction module
└── solar.py          # Solar park module
```

---

### 4. Cost Service (Port 8004) ✅
**Purpose**: Cost calculations and material balance

**Key Endpoints**:
- `POST /costs/calculate` - Calculate project costs
- `POST /costs/material-balance` - Material reuse calculation
- `GET /costs/presets` - Get cost rate presets

**Tech Stack**: FastAPI, shared/core modules

**Cost Factors**:
- Excavation cost (€/m³)
- Transport cost (€/m³)
- Disposal cost (€/m³)
- Fill material cost (€/m³)
- Platform preparation cost (€/m²)
- Swell factor: 1.25
- Compaction factor: 0.85

**Presets**: standard, low, high, premium

---

### 5. Report Service (Port 8005) ✅
**Purpose**: HTML and PDF report generation

**Key Endpoints**:
- `POST /report/generate` - Generate report (HTML/PDF)
- `GET /report/download/{report_id}/{filename}` - Download report

**Tech Stack**: FastAPI, Jinja2, WeasyPrint

**Features**:
- WKA site reports with material balance
- Print-friendly CSS
- Auto-cleanup after 30 days
- Multiple template support (WKA ready, Road/Solar/Terrain planned)

**Templates**:
- `wka_report.html` - Modern responsive design based on QGIS Plugin template

---

### 6. API Gateway (Port 8000) ✅
**Purpose**: Central routing, authentication, and rate limiting

**Key Features**:
- Service proxying to all microservices
- JWT authentication middleware
- Rate limiting with slowapi
- CORS support
- Service discovery endpoint

**Tech Stack**: FastAPI, httpx (async client), slowapi

**Proxy Routes**:
- `/auth/*` → Auth Service (8001)
- `/dem/*` → DEM Service (8002)
- `/calc/*` → Calculation Service (8003)
- `/costs/*` → Cost Service (8004)
- `/report/*` → Report Service (8005)

---

### 7. Frontend (Port 3000) ✅
**Purpose**: React-based web interface

**Key Features**:
- Interactive Leaflet map
- Click-to-place WKA sites
- Automatic coordinate conversion (proj4)
- Real-time calculation parameters
- Material balance visualization
- PDF report download
- Responsive design

**Tech Stack**: React 18, TypeScript, Vite, Leaflet, proj4, axios

**Components**:
- `Map.tsx` - Leaflet map with marker management
- `WKAForm.tsx` - Comprehensive calculation form
- `Dashboard.tsx` - Main application interface
- `Login.tsx` - Magic link authentication

**Critical Feature**: Automatic Lat/Lng → UTM conversion using proj4
```typescript
// Germany UTM zones 32-36 (EPSG:25832-25836)
const utmCoords = latLngToUTM({ lat: 51.5, lng: 10.5 });
// Result: { easting: 597500, northing: 5705000, zone: 32, epsg: "EPSG:25832" }
```

## 📁 Project Structure

```
Wind-Turbine-Earthwork-Calculator/
├── plugin/                     # Original QGIS Plugin (preserved)
│   └── prototype/
├── webapp/                     # NEW: Web Application
│   ├── docker-compose.yml     # Orchestration
│   ├── init-db/               # Database initialization
│   ├── services/
│   │   ├── auth_service/      # Port 8001
│   │   ├── dem_service/       # Port 8002
│   │   ├── calculation_service/ # Port 8003
│   │   ├── cost_service/      # Port 8004
│   │   ├── report_service/    # Port 8005
│   │   └── api_gateway/       # Port 8000
│   ├── frontend/              # React app (Port 3000)
│   └── test-integration.sh    # Integration tests
├── shared/                    # Shared calculation modules
│   ├── core/
│   │   ├── foundation.py      # Foundation calculations
│   │   ├── platform.py        # Platform calculations
│   │   ├── material_balance.py # Material reuse
│   │   └── costs.py           # Cost calculations
│   └── utils/
│       └── geometry.py        # Geometry utilities
├── tests/                     # Test suites
└── docs/                      # Additional documentation
```

## 🗄️ Database Schema

PostgreSQL with PostGIS extension:

**Tables**:
- `users` - User accounts
- `magic_links` - Authentication tokens
- `sessions` - Active sessions
- `projects` - User projects
- `jobs` - Background calculation jobs
- `dem_cache` - Metadata for cached DEM tiles
- `dem_tiles` - Individual DEM tile metadata
- `calculation_results` - Calculation outputs
- `reports` - Generated reports

See `init-db/01-init.sql` for complete schema.

## 🧪 Testing

### Integration Tests
```bash
cd webapp
./test-integration.sh
```

Tests:
1. Foundation calculation
2. DEM fetch with UTM coordinates
3. Platform calculation
4. Complete WKA site calculation

### Manual Testing
```bash
# Test Auth Service
curl -X POST http://localhost:8001/auth/request-login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# Test DEM Service
curl -X POST http://localhost:8002/dem/fetch \
  -H "Content-Type: application/json" \
  -d '{
    "crs": "EPSG:25832",
    "center_x": 497500,
    "center_y": 5670500,
    "buffer_meters": 250
  }'

# Test Calculation Service
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
    "optimization_method": "balanced"
  }'
```

## 🔧 Development

### Running Services Locally

Each service can be run independently:

```bash
# Example: Run Calculation Service locally
cd services/calculation_service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

### Running Frontend Locally

```bash
cd frontend
npm install
npm start
```

### Adding New Services

1. Create service directory in `services/`
2. Follow the FastAPI service template
3. Add to `docker-compose.yml`
4. Add proxy route in API Gateway
5. Update frontend API client if needed

## 🚢 Deployment

### Production Considerations

1. **Security**:
   - Change default passwords
   - Use strong JWT secret
   - Restrict CORS origins
   - Use HTTPS (add nginx reverse proxy)
   - Enable firewall rules

2. **Performance**:
   - Increase Redis memory limit
   - Add more Celery workers (Phase 2)
   - Use PostgreSQL connection pooling
   - Enable HTTP/2

3. **Monitoring**:
   - Add logging aggregation
   - Set up health check endpoints
   - Monitor Redis cache hit rates
   - Track DEM API response times

4. **Backup**:
   - Regular PostgreSQL backups
   - Redis persistence configuration
   - Report file backups

## 🐛 Troubleshooting

### Services won't start
```bash
# Check Docker logs
docker-compose logs <service-name>

# Restart specific service
docker-compose restart <service-name>

# Rebuild if code changed
docker-compose up -d --build
```

### Frontend can't connect to API
- Check that API Gateway is running: `curl http://localhost:8000/health`
- Verify CORS settings in API Gateway
- Check browser console for CORS errors

### DEM fetch fails
- Verify UTM coordinates are being used (EPSG:25832-25836)
- Check hoehendaten.de API availability
- Verify Redis is running: `docker-compose logs redis`

### Magic Link not received
- Check SMTP credentials in `.env`
- Check email spam folder
- Verify SMTP service is not blocking emails
- Check Auth Service logs: `docker-compose logs auth_service`

## 📋 Next Steps

### Phase 2: Extended Use Cases
1. Road construction earthwork module
2. Solar park planning module
3. General terrain analysis module
4. WebSocket integration for real-time progress
5. Multi-user collaboration features

### Phase 3: Advanced Features
1. 3D visualization of earthwork
2. Drone survey integration
3. Machine learning for cost estimation
4. Mobile app (React Native)

## 📖 Documentation

- **API Reference**: http://localhost:8000/docs (Swagger)
- **QGIS Plugin**: `../plugin/prototype/WORKFLOW_STANDFLAECHEN.md`
- **hoehendaten.de API**: https://hoehendaten.de/api-rawtifrequest.html

## 🤝 Contributing

1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes
3. Test locally with Docker Compose
4. Run integration tests: `./test-integration.sh`
5. Commit with descriptive message
6. Push and create Pull Request

## 📄 License

See LICENSE file for details.

## 📞 Contact

For issues, questions, or feature requests, please create an issue on GitHub.

## 🙏 Acknowledgments

- **hoehendaten.de** - German elevation data API
- **OpenStreetMap** - Map tiles
- **Leaflet** - Mapping library
- **FastAPI** - Python web framework
- **proj4** - Coordinate transformation library
