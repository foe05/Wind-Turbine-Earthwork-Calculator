# Project Structure - Geo-Engineering Platform

## 📁 Repository-Struktur (NEU ab v6.1)

```
Wind-Turbine-Earthwork-Calculator/
│
├── plugin/                          # 🔧 QGIS Plugin (bestehend)
│   └── prototype/
│       ├── WindTurbine_Earthwork_Calculator.py  ← QGIS Plugin v6.0
│       ├── INSTALLATION_QGIS.md
│       └── WORKFLOW_STANDFLAECHEN.md
│
├── webapp/                          # 🌐 Web-Plattform (NEU)
│   ├── services/
│   │   ├── api_gateway/            ⚠️ TODO
│   │   ├── auth_service/           ✅ FERTIG
│   │   ├── dem_service/            ✅ FERTIG
│   │   ├── calculation_service/    ⚠️ TODO
│   │   ├── cost_service/           ⚠️ TODO
│   │   └── report_service/         ⚠️ TODO
│   ├── frontend/                   ⚠️ TODO
│   ├── docker-compose.yml          ✅ FERTIG
│   ├── .env.example                ✅ FERTIG
│   ├── init-db/                    ✅ FERTIG
│   │   └── 01-init.sql
│   └── README.md                   ✅ FERTIG
│
├── shared/                          # 📦 Geteilte Berechnungslogik
│   ├── core/
│   │   ├── foundation.py           ✅ FERTIG
│   │   ├── material_balance.py     ✅ FERTIG
│   │   ├── costs.py                ✅ FERTIG
│   │   ├── platform.py             ⚠️ TODO
│   │   ├── volume.py               ⚠️ TODO
│   │   └── optimization.py         ⚠️ TODO
│   └── utils/
│       ├── dem_processing.py       ⚠️ TODO
│       └── geometry.py             ⚠️ TODO
│
├── tests/                           # 🧪 Tests
│   ├── plugin/                     ⚠️ TODO
│   ├── webapp/                     ⚠️ TODO
│   └── shared/                     ⚠️ TODO
│
├── docs/                            # 📚 Dokumentation
│   ├── plugin/                     ⚠️ TODO
│   ├── webapp/                     ⚠️ TODO
│   └── api/                        ⚠️ TODO
│
├── .github/
│   └── workflows/
│       ├── plugin-tests.yml        ⚠️ TODO
│       └── webapp-deploy.yml       ⚠️ TODO
│
├── README.md                        ← Haupt-README
├── PROJECT_STRUCTURE.md             ← Diese Datei
├── CHANGELOG.md
├── CONTRIBUTING.md
└── LICENSE
```

---

## 🎯 Projekt-Übersicht

Dieses Repository enthält **zwei parallele Projekte**:

### 1. QGIS Plugin (`plugin/`)
- **Status:** Produktiv (v6.0)
- **Zielgruppe:** QGIS-Nutzer, Desktop-Anwendung
- **Features:**
  - hoehendaten.de API Integration
  - DEM-Cache mit LRU-Strategie
  - GeoPackage Output
  - Standort-basierte Kachel-Berechnung (250m Radius)
- **Dokumentation:** `plugin/prototype/INSTALLATION_QGIS.md`

### 2. Web-Plattform (`webapp/`)
- **Status:** In Entwicklung (v1.0 alpha)
- **Zielgruppe:** Öffentlich zugängliche Web-App
- **Features (geplant):**
  - 4 Use-Cases: WKA, Straßenbau, Solar-Park, Geländeanalyse
  - Microservices-Architektur
  - Magic Link Authentifizierung
  - Interaktive Leaflet-Karte
  - Background Job Processing
- **Dokumentation:** `webapp/README.md`

---

## 🚀 Quick Start

### QGIS Plugin verwenden

```bash
# 1. Plugin-Datei kopieren
cp plugin/prototype/WindTurbine_Earthwork_Calculator.py ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/

# 2. QGIS neu starten

# 3. Plugin in QGIS aktivieren
# Menü: Plugins → Manage and Install Plugins → "Wind Turbine Earthwork Calculator"
```

Siehe: `plugin/prototype/INSTALLATION_QGIS.md`

### Web-Plattform entwickeln

```bash
# 1. Services starten
cd webapp
docker-compose up -d postgres redis

# 2. Services testen
curl http://localhost:8001/health  # Auth Service
curl http://localhost:8002/health  # DEM Service

# 3. Dokumentation öffnen
open http://localhost:8001/docs
open http://localhost:8002/docs
```

Siehe: `webapp/README.md`

---

## 🔄 Code-Sharing-Strategie

Die Berechnungslogik ist in `shared/` extrahiert und wird von beiden Projekten genutzt:

```
QGIS Plugin          Web-Services
     │                    │
     ├────────┬───────────┤
              ▼
         shared/core/
         ├── foundation.py
         ├── costs.py
         └── material_balance.py
```

**WICHTIG:**
- QGIS Plugin nutzt weiterhin QGIS-APIs (QgsRasterLayer, etc.)
- Web-Services nutzen rasterio, shapely, geopandas
- Shared modules sind **framework-agnostisch** (nur NumPy, Python stdlib)

---

## 📊 Implementierungs-Status

| Component                    | Status      | Details                          |
|------------------------------|-------------|----------------------------------|
| **QGIS Plugin**             | ✅ Produktiv | v6.0 - Vollständig funktionsfähig |
| **DB Schema**               | ✅ Fertig    | PostgreSQL + PostGIS            |
| **Auth Service**            | ✅ Fertig    | Magic Link + JWT                |
| **DEM Service**             | ✅ Fertig    | hoehendaten.de API + Cache      |
| **Shared Core Modules**     | 🟨 Teilweise | foundation, costs, material     |
| **Calculation Service**     | ⚠️ TODO     | WKA-Modul                       |
| **Cost Service**            | ⚠️ TODO     | API-Wrapper um shared modules   |
| **Report Service**          | ⚠️ TODO     | HTML/PDF Templates              |
| **API Gateway**             | ⚠️ TODO     | Routing + Job Queue             |
| **Frontend**                | ⚠️ TODO     | React + Leaflet                 |
| **Tests**                   | ⚠️ TODO     | pytest                          |
| **CI/CD**                   | ⚠️ TODO     | GitHub Actions                  |

---

## 🎓 Architektur-Entscheidungen

### Warum Microservices?

1. **Skalierbarkeit:** DEM-Fetching kann CPU-intensiv sein → eigener Service
2. **Technologie-Auswahl:** Auth braucht Email, Calculation braucht rasterio
3. **Team-Parallelität:** Teams können unabhängig arbeiten
4. **Deployment:** Services können einzeln deployed werden

### Warum Magic Links?

1. **UX:** Keine Passwort-Verwaltung
2. **Sicherheit:** Kein Passwort-Leak-Risiko
3. **Einfachheit:** Kein "Forgot Password" Flow nötig

### Warum Redis für DEM-Cache?

1. **Performance:** In-Memory-Cache für häufige Zugriffe
2. **TTL:** Automatisches Ablaufen nach 6 Monaten
3. **Einfachheit:** Keine eigene Cache-Logik nötig

---

## 🔧 Entwicklungs-Workflow

### Neue Features im QGIS Plugin

1. Änderungen in `plugin/prototype/WindTurbine_Earthwork_Calculator.py`
2. Extrahiere shared logic nach `shared/core/` (falls wiederverwendbar)
3. Teste in QGIS
4. Commit mit Prefix `plugin: `

### Neue Features in der Web-App

1. Implementiere Service in `webapp/services/{service_name}/`
2. Nutze `shared/core/` Module
3. Schreibe Tests in `tests/webapp/`
4. Update `webapp/docker-compose.yml` falls nötig
5. Commit mit Prefix `webapp: `

### Shared Module ändern

1. Ändere Code in `shared/core/`
2. **TESTE BEIDE:** QGIS Plugin UND Web-Services!
3. Commit mit Prefix `shared: `

---

## 📚 Weitere Dokumentation

- **Web-App Setup:** `webapp/README.md`
- **QGIS Plugin Installation:** `plugin/prototype/INSTALLATION_QGIS.md`
- **Standflächenberechnung:** `plugin/prototype/WORKFLOW_STANDFLAECHEN.md`
- **API-Referenz:** http://localhost:8000/docs (nach Start)
- **Changelog:** `CHANGELOG.md`
- **Contributing:** `CONTRIBUTING.md`

---

## 🤝 Contributing

Siehe `CONTRIBUTING.md`

---

## 📄 License

MIT License - Siehe `LICENSE`

---

## 🐛 Issues & Support

- **QGIS Plugin:** Issues mit Tag `plugin`
- **Web-App:** Issues mit Tag `webapp`
- **Shared Modules:** Issues mit Tag `shared`

GitHub Issues: https://github.com/foe05/Wind-Turbine-Earthwork-Calculator/issues
