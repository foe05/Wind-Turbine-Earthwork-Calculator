# Project Structure - Geo-Engineering Platform

**Last Updated**: 2025 (Phase 3 Complete)

## 📁 Repository-Struktur

```
Wind-Turbine-Earthwork-Calculator/
│
├── plugin/                                    # 🔧 QGIS Plugin
│   └── prototype/
│       ├── WindTurbine_Earthwork_Calculator.py    ✅ QGIS Plugin v6.0
│       ├── INSTALLATION_QGIS.md                   ✅ Installation Guide
│       ├── WORKFLOW_STANDFLAECHEN.md              ✅ Workflow Documentation
│       └── installationsanleitung.md              ✅ DE Installation
│
├── webapp/                                    # 🌐 Web-Plattform (Phase 1-3 Complete)
│   ├── services/
│   │   ├── api_gateway/                           ✅ API Gateway (Phase 1-3)
│   │   │   ├── app/
│   │   │   │   ├── api/
│   │   │   │   │   ├── proxy.py                   ✅ Service proxying
│   │   │   │   │   ├── websocket.py               ✅ WebSocket support (Phase 2)
│   │   │   │   │   ├── jobs.py                    ✅ Jobs management (Phase 2)
│   │   │   │   │   ├── projects.py                ✅ Project CRUD (Phase 3)
│   │   │   │   │   ├── batch.py                   ✅ Batch upload (Phase 3)
│   │   │   │   │   └── exports.py                 ✅ GeoPackage export (Phase 3)
│   │   │   │   ├── core/
│   │   │   │   │   ├── config.py                  ✅ Configuration
│   │   │   │   │   ├── auth.py                    ✅ JWT authentication (Phase 3)
│   │   │   │   │   └── database.py                ✅ Database utils (Phase 3)
│   │   │   │   └── main.py                        ✅ FastAPI app
│   │   │   ├── requirements.txt                   ✅ Dependencies
│   │   │   └── Dockerfile                         ✅ Container config
│   │   │
│   │   ├── auth_service/                          ✅ Authentication Service
│   │   │   ├── app/
│   │   │   │   ├── api/
│   │   │   │   │   └── auth.py                    ✅ Magic link auth
│   │   │   │   ├── core/
│   │   │   │   │   ├── config.py
│   │   │   │   │   ├── email.py                   ✅ Email sender
│   │   │   │   │   └── tokens.py                  ✅ JWT tokens
│   │   │   │   └── main.py
│   │   │   ├── requirements.txt
│   │   │   └── Dockerfile
│   │   │
│   │   ├── dem_service/                           ✅ DEM Service (Phase 1-2)
│   │   │   ├── app/
│   │   │   │   ├── api/
│   │   │   │   │   └── dem.py                     ✅ DEM fetching & caching
│   │   │   │   ├── core/
│   │   │   │   │   ├── cache.py                   ✅ Intelligent caching (Phase 2)
│   │   │   │   │   └── hoehendaten.py             ✅ API integration
│   │   │   │   └── main.py
│   │   │   ├── requirements.txt
│   │   │   └── Dockerfile
│   │   │
│   │   ├── calculation_service/                   ✅ Calculation Service (Phase 1-2)
│   │   │   ├── app/
│   │   │   │   ├── api/
│   │   │   │   │   └── calculation.py             ✅ Multi-use-case calc
│   │   │   │   ├── modules/
│   │   │   │   │   ├── wka.py                     ✅ WKA calculations (Phase 1)
│   │   │   │   │   ├── road.py                    ✅ Road calculations (Phase 2)
│   │   │   │   │   ├── solar.py                   ✅ Solar calculations (Phase 2)
│   │   │   │   │   └── terrain.py                 ✅ Terrain analysis (Phase 2)
│   │   │   │   └── main.py
│   │   │   ├── requirements.txt
│   │   │   └── Dockerfile
│   │   │
│   │   ├── cost_service/                          ✅ Cost Service
│   │   │   ├── app/
│   │   │   │   ├── api/
│   │   │   │   │   └── costs.py                   ✅ Cost calculation
│   │   │   │   └── main.py
│   │   │   ├── requirements.txt
│   │   │   └── Dockerfile
│   │   │
│   │   ├── report_service/                        ✅ Report Service (Phase 2)
│   │   │   ├── app/
│   │   │   │   ├── api/
│   │   │   │   │   └── report.py                  ✅ PDF generation
│   │   │   │   ├── templates/                     ✅ Report templates (Phase 2)
│   │   │   │   │   ├── wka_report.html
│   │   │   │   │   ├── road_report.html
│   │   │   │   │   ├── solar_report.html
│   │   │   │   │   └── terrain_report.html
│   │   │   │   └── main.py
│   │   │   ├── requirements.txt
│   │   │   └── Dockerfile
│   │   │
│   │   └── celery_worker/                         ✅ Background Jobs (Phase 2)
│   │       ├── app/
│   │       │   ├── tasks.py                       ✅ Celery tasks
│   │       │   └── worker.py                      ✅ Worker config
│   │       ├── requirements.txt
│   │       └── Dockerfile
│   │
│   ├── frontend/                                  ✅ React Frontend (Phase 1-3)
│   │   ├── public/
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   ├── Map.tsx                        ✅ Leaflet map
│   │   │   │   ├── MapWithDrawing.tsx             ✅ Drawing tools
│   │   │   │   ├── WKAForm.tsx                    ✅ WKA calculator (Phase 1)
│   │   │   │   ├── RoadForm.tsx                   ✅ Road calculator (Phase 2)
│   │   │   │   ├── SolarForm.tsx                  ✅ Solar calculator (Phase 2)
│   │   │   │   ├── TerrainForm.tsx                ✅ Terrain calculator (Phase 2)
│   │   │   │   ├── BatchUpload.tsx                ✅ Batch upload (Phase 3)
│   │   │   │   └── ErrorBoundary.tsx              ✅ Error boundary (Phase 3)
│   │   │   ├── pages/
│   │   │   │   ├── Login.tsx                      ✅ Login page
│   │   │   │   ├── Dashboard.tsx                  ✅ Main dashboard (Phase 1)
│   │   │   │   ├── MultiTabDashboard.tsx          ✅ Multi-use dashboard (Phase 2)
│   │   │   │   ├── ProjectsOverview.tsx           ✅ Projects page (Phase 3)
│   │   │   │   ├── JobsHistory.tsx                ✅ Jobs page (Phase 3)
│   │   │   │   └── NotFound.tsx                   ✅ 404 page (Phase 3)
│   │   │   ├── services/
│   │   │   │   └── api.ts                         ✅ API client (all phases)
│   │   │   ├── types/
│   │   │   │   └── index.ts                       ✅ TypeScript types
│   │   │   ├── App.tsx                            ✅ Main app (lazy loading)
│   │   │   ├── main.tsx                           ✅ Entry point
│   │   │   └── index.css                          ✅ Global styles
│   │   ├── package.json                           ✅ Dependencies
│   │   ├── vite.config.ts                         ✅ Build config
│   │   ├── tsconfig.json                          ✅ TypeScript config
│   │   ├── Dockerfile                             ✅ Container config
│   │   └── README.md                              ✅ Frontend docs
│   │
│   ├── init-db/                                   ✅ Database initialization
│   │   ├── 01-init.sql                            ✅ Schema setup
│   │   ├── 02-demo-data.sql                       ✅ Demo data (Phase 2)
│   │   └── 03-test-data.sql                       ✅ Test data (Phase 2)
│   │
│   ├── docker-compose.yml                         ✅ Multi-service orchestration
│   ├── .env.example                               ✅ Environment template
│   ├── nginx.conf                                 ✅ Reverse proxy config
│   └── README.md                                  ✅ Webapp documentation
│
├── docs/                                          # 📚 Documentation
│   ├── PHASE2_DESIGN.md                           ✅ Phase 2 design
│   ├── PHASE2_COMPLETE.md                         ✅ Phase 2 completion
│   └── PHASE3_COMPLETE.md                         ✅ Phase 3 completion (NEW)
│
├── tests/                                         # 🧪 Tests
│   ├── integration/                               ✅ Integration tests (Phase 2)
│   │   ├── test_wka_workflow.py
│   │   ├── test_road_workflow.py
│   │   ├── test_solar_workflow.py
│   │   └── test_terrain_workflow.py
│   └── unit/                                      ⚠️ TODO
│
├── .github/
│   └── workflows/                                 ⚠️ TODO
│       ├── plugin-tests.yml
│       └── webapp-deploy.yml
│
├── README.md                                      ✅ Main README (updated)
├── PROJECT_STRUCTURE.md                           ✅ This file (updated)
├── AGENTS.md                                      ✅ AI agents info
├── CHANGELOG.md                                   ✅ Version history
├── CONTRIBUTING.md                                ✅ Contribution guide
└── LICENSE                                        ✅ MIT License
```

---

## 🎯 Project Overview

This repository contains **two parallel projects**:

### 1. QGIS Plugin (`plugin/`)
- **Status:** Production (v6.0)
- **Target Audience:** QGIS users, desktop application
- **Features:**
  - hoehendaten.de API integration
  - DEM cache with LRU strategy
  - GeoPackage output
  - Site-based tile calculation (250m radius)
- **Documentation:** `plugin/prototype/INSTALLATION_QGIS.md`

### 2. Web Platform (`webapp/`)
- **Status:** Production Ready (Phase 1-3 Complete)
- **Target Audience:** Web users, multi-user cloud platform
- **Architecture:** Microservices with FastAPI + React
- **Features:**
  - **Phase 1**: WKA calculations, passwordless auth, interactive maps
  - **Phase 2**: Road/Solar/Terrain calculations, PDF reports, Celery jobs, WebSockets
  - **Phase 3**: Projects dashboard, batch upload, GeoPackage export, error handling
- **Documentation:** `webapp/README.md`

---

## 🏗️ Architecture Overview

### Microservices Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Users (Web Browser)                      │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│              Frontend (React + TypeScript)                  │
│  • Projects Dashboard      • Jobs History                   │
│  • Multi-Tab Calculator    • Batch Upload                   │
│  • Interactive Maps        • Error Boundaries               │
└────────────────┬────────────────────────────────────────────┘
                 │ HTTP/REST + WebSocket
┌────────────────▼────────────────────────────────────────────┐
│          API Gateway (FastAPI Port 8000)                    │
│  • Request routing         • JWT authentication             │
│  • Rate limiting          • WebSocket hub                   │
│  • Project management     • Batch upload                    │
│  • GeoPackage export      • Jobs orchestration              │
└─────┬──────┬──────┬──────┬──────┬──────┬───────────────────┘
      │      │      │      │      │      │
┌─────▼──┐ ┌─▼────┐ ┌▼─────┐ ┌───▼──┐ ┌─▼────┐ ┌▼──────────┐
│ Auth   │ │ DEM  │ │ Calc │ │ Cost │ │Report│ │ Postgres  │
│Service │ │Service│ │Service│ │Service│ │Service│ │  +PostGIS │
│Port    │ │Port   │ │Port  │ │Port  │ │Port  │ │Port 5432  │
│8001    │ │8002   │ │8003  │ │8004  │ │8005  │ └───────────┘
└────────┘ └───────┘ └──────┘ └──────┘ └──────┘
                                                   ┌───────────┐
                                                   │  Redis    │
                                                   │Port 6379  │
                                                   └─────┬─────┘
                                                         │
                                                   ┌─────▼─────┐
                                                   │  Celery   │
                                                   │  Workers  │
                                                   └───────────┘
```

### Data Flow

#### 1. WKA Calculation Flow (Phase 1)
```
User → Frontend → API Gateway → Calculation Service
                                      ↓
                            DEM Service (fetch DEM)
                                      ↓
                            Cost Service (calculate costs)
                                      ↓
                            Report Service (generate PDF)
                                      ↓
                            Database (store results)
                                      ↓
                            Frontend (display results)
```

#### 2. Batch Upload Flow (Phase 3)
```
User → Upload CSV/GeoJSON → API Gateway
                                ↓
                       Validate & Parse
                                ↓
                       Auto-detect UTM zone
                                ↓
                       Convert coordinates (WGS84 → UTM)
                                ↓
                       Create sites in database
                                ↓
                       Create Celery jobs (background)
                                ↓
                       Return job IDs to frontend
                                ↓
                       WebSocket progress updates
```

#### 3. Export Flow (Phase 3)
```
User → Request Export → API Gateway
                            ↓
                    Query project data
                            ↓
                    Join sites + jobs + results
                            ↓
                    Create GeoDataFrame (geopandas)
                            ↓
                    Export to .gpkg
                            ↓
                    Return file to browser
                            ↓
                    Browser downloads file
```

---

## 📦 Key Technologies

### Backend
- **FastAPI** 0.104+ - Modern Python web framework
- **PostgreSQL** 15 + **PostGIS** - Spatial database
- **Celery** 5.3+ - Background task queue
- **Redis** 7 - Cache & message broker
- **WeasyPrint** - PDF generation
- **GeoPandas** - GIS data processing
- **pyproj** - Coordinate transformations

### Frontend
- **React** 18 - UI framework
- **TypeScript** 5 - Type safety
- **Vite** 5 - Build tool & dev server
- **React Router** 6 - Client-side routing
- **Leaflet** 1.9 - Interactive maps
- **Axios** - HTTP client

### Infrastructure
- **Docker** + **Docker Compose** - Containerization
- **Nginx** - Reverse proxy
- **Python** 3.11+ - Programming language
- **Node.js** 20+ - Frontend build tools

---

## 🗄️ Database Schema

### Core Tables

```sql
-- Users
users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
)

-- Projects (Phase 3)
projects (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    use_case VARCHAR(50) CHECK (use_case IN ('wka', 'road', 'solar', 'terrain')),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    crs VARCHAR(50) NOT NULL,
    utm_zone INTEGER,
    bounds GEOMETRY(POLYGON, 4326),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
)

-- Sites
sites (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255),
    location_wgs84 GEOMETRY(POINT, 4326),
    location_utm GEOMETRY(POINT),
    foundation_type VARCHAR(50),
    foundation_diameter FLOAT,
    foundation_depth FLOAT,
    soil_type VARCHAR(50),
    bulk_density FLOAT,
    platform_length FLOAT,
    platform_width FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
)

-- Jobs (Phase 2)
jobs (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    site_id UUID REFERENCES sites(id),
    status VARCHAR(50) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    results JSONB,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
)

-- Report Templates (Phase 2)
report_templates (
    id UUID PRIMARY KEY,
    use_case VARCHAR(50),
    name VARCHAR(255),
    html_template TEXT,
    css_styles TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
)
```

### Indexes
```sql
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_projects_use_case ON projects(use_case);
CREATE INDEX idx_sites_project_id ON sites(project_id);
CREATE INDEX idx_jobs_project_id ON jobs(project_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created_at ON jobs(created_at DESC);
CREATE INDEX idx_jobs_project_status ON jobs(project_id, status);
```

---

## 🔌 API Endpoints Summary

### Authentication
- `POST /auth/request-login` - Request magic link
- `GET /auth/verify/{token}` - Verify magic link
- `GET /auth/me` - Get current user

### Projects (Phase 3)
- `POST /projects` - Create project
- `GET /projects` - List projects
- `GET /projects/{id}` - Get project details
- `PUT /projects/{id}` - Update project
- `DELETE /projects/{id}` - Delete project

### Batch Upload (Phase 3)
- `POST /batch/upload-csv` - Upload CSV
- `POST /batch/upload-geojson` - Upload GeoJSON

### Export (Phase 3)
- `GET /exports/projects/{id}/geopackage` - Export project
- `GET /exports/jobs/{id}/geopackage` - Export job

### Jobs (Phase 2)
- `POST /jobs` - Create job
- `GET /jobs/history` - Get jobs history
- `GET /jobs/{id}/details` - Get job details
- `DELETE /jobs/{id}` - Delete job

### DEM Service
- `POST /dem/fetch` - Fetch DEM data
- `GET /dem/{id}` - Get cached DEM
- `GET /dem/cache/stats` - Cache statistics

### Calculation Service (Phase 2)
- `POST /calculation/wka/calculate` - WKA calculations
- `POST /calculation/road/calculate` - Road calculations
- `POST /calculation/solar/calculate` - Solar calculations
- `POST /calculation/terrain/analyze` - Terrain analysis

### Cost Service
- `POST /costs/calculate` - Calculate costs
- `GET /costs/presets` - Get cost presets

### Report Service (Phase 2)
- `POST /report/generate` - Generate PDF report
- `GET /report/download/{id}/{filename}` - Download report

### WebSocket
- `WS /ws/job/{id}` - Real-time job progress

---

## 📁 File Organization

### Backend Service Structure
```
service_name/
├── app/
│   ├── api/
│   │   └── routes.py       # API endpoints
│   ├── core/
│   │   ├── config.py       # Configuration
│   │   └── database.py     # DB connection
│   ├── models/
│   │   └── schemas.py      # Pydantic models
│   ├── services/
│   │   └── logic.py        # Business logic
│   └── main.py             # FastAPI app
├── tests/
│   └── test_api.py
├── requirements.txt
├── Dockerfile
└── README.md
```

### Frontend Structure
```
frontend/
├── src/
│   ├── components/         # Reusable UI components
│   ├── pages/              # Page components (routes)
│   ├── services/           # API clients
│   ├── types/              # TypeScript types
│   ├── utils/              # Helper functions
│   ├── App.tsx             # Main app component
│   └── main.tsx            # Entry point
├── public/
│   └── assets/             # Static assets
├── package.json
├── tsconfig.json
├── vite.config.ts
└── Dockerfile
```

---

## 🚀 Development Workflow

### Local Development

```bash
# 1. Start backend services
cd webapp
docker-compose up -d postgres redis

# 2. Run individual service
cd webapp/services/api_gateway
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. Run frontend
cd webapp/frontend
npm install
npm run dev
```

### Testing

```bash
# Backend unit tests
pytest webapp/services/api_gateway/tests/

# Integration tests (Phase 2)
pytest tests/integration/

# Frontend tests
cd webapp/frontend
npm test
```

### Building

```bash
# Backend
docker build -t geo-api-gateway webapp/services/api_gateway

# Frontend
cd webapp/frontend
npm run build
```

---

## 📝 Configuration Files

### Environment Variables
```bash
# .env
DATABASE_URL=postgresql://user:pass@localhost:5432/geo_engineering
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=your-secret-key-here
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
```

### Docker Compose
```yaml
version: '3.8'
services:
  api-gateway:
    build: ./services/api_gateway
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis

  frontend:
    build: ./frontend
    ports:
      - "3000:80"

  postgres:
    image: postgis/postgis:15-3.3
    environment:
      POSTGRES_DB: geo_engineering
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./init-db:/docker-entrypoint-initdb.d

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

---

## 🎯 Feature Status

### Phase 1 - Core Infrastructure ✅ COMPLETE
- ✅ Passwordless authentication (magic link)
- ✅ Interactive map with drawing tools
- ✅ WKA site calculations
- ✅ Real-time results display
- ✅ PostgreSQL/PostGIS database
- ✅ Microservices architecture

### Phase 2 - Multi-Use-Case Support ✅ COMPLETE
- ✅ Road construction calculations
- ✅ Solar park calculations
- ✅ Terrain analysis
- ✅ PDF report generation
- ✅ Celery background jobs
- ✅ WebSocket real-time updates
- ✅ DEM caching strategy
- ✅ Integration tests
- ✅ Demo data

### Phase 3 - User Experience ✅ COMPLETE
- ✅ Projects dashboard (CRUD)
- ✅ Jobs history with filtering
- ✅ Batch upload (CSV/GeoJSON)
- ✅ Automatic UTM conversion
- ✅ GeoPackage export
- ✅ Error pages (404, boundary)
- ✅ Frontend lazy loading
- ✅ Code splitting

### Phase 4 - Future Enhancements ⚠️ PLANNED
- ⚠️ Email notifications
- ⚠️ Advanced filtering
- ⚠️ Project collaboration
- ⚠️ Analytics dashboard
- ⚠️ Mobile app
- ⚠️ CI/CD pipeline
- ⚠️ Monitoring & logging
- ⚠️ Unit tests coverage

---

## 📚 Documentation Links

- [Main README](README.md) - Project overview
- [Webapp README](webapp/README.md) - Backend services
- [Frontend README](webapp/frontend/README.md) - Frontend app
- [Phase 2 Complete](docs/PHASE2_COMPLETE.md) - Phase 2 documentation
- [Phase 3 Complete](docs/PHASE3_COMPLETE.md) - Phase 3 documentation
- [AGENTS.md](AGENTS.md) - AI development agents
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines

---

## 🔗 Quick Links

**Development**:
- Frontend: http://localhost:3000
- API Gateway: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Database: localhost:5432

**Production** (when deployed):
- Frontend: https://geo-engineering.example.com
- API: https://api.geo-engineering.example.com

---

**Last Updated**: 2025 (Phase 3 Complete)
**Status**: Production Ready
**Next**: Phase 4 Planning or Production Deployment
