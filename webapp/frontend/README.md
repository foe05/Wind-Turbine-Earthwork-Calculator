# Geo-Engineering Platform - Frontend

React + TypeScript frontend for Wind Turbine Earthwork Calculations.

## Features

- **Interactive Leaflet Map**: Click to place WKA sites
- **Coordinate Conversion**: Automatic Lat/Lng to UTM conversion using proj4
- **Real-time Calculations**: DEM fetching, earthwork calculations, and cost analysis
- **Magic Link Authentication**: Passwordless login
- **PDF Report Generation**: Download comprehensive project reports
- **Responsive Design**: Modern UI with Tailwind-inspired styling

## Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development and building
- **Leaflet** for interactive mapping
- **proj4** for coordinate transformations (WGS84 ↔ UTM)
- **Axios** for API communication
- **React Router** for navigation

## Critical Requirements

- **UTM Coordinates**: All calculations use EPSG:25832-25836 (UTM zones 32-36 for Germany)
- **250m Buffer**: DEM data is fetched with 250m buffer around each WKA site
- **hoehendaten.de API**: German elevation data API integration via backend services

## Development

```bash
# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build
```

The development server runs on port 3000 and proxies API requests to the API Gateway on port 8000.

## Environment Variables

Create a `.env` file:

```
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```

## Project Structure

```
src/
├── components/
│   ├── Map.tsx           # Leaflet map component
│   └── WKAForm.tsx       # WKA calculation form
├── pages/
│   ├── Login.tsx         # Magic link login
│   └── Dashboard.tsx     # Main application
├── services/
│   └── api.ts            # API client
├── types/
│   └── index.ts          # TypeScript definitions
├── utils/
│   └── coordinates.ts    # Coordinate conversion utilities
├── App.tsx               # Main app with routing
├── main.tsx              # Entry point
└── index.css             # Global styles
```

## Docker

```bash
# Build image
docker build -t geo-frontend .

# Run container
docker run -p 3000:3000 geo-frontend
```

## API Integration

The frontend communicates with the API Gateway (port 8000), which routes requests to:

- **Auth Service** (8001): Magic link authentication
- **DEM Service** (8002): Elevation data fetching
- **Calculation Service** (8003): Earthwork calculations
- **Cost Service** (8004): Cost analysis
- **Report Service** (8005): PDF generation

## Usage

1. **Login**: Enter your email to receive a magic link
2. **Create Project**: Click on the map to add WKA sites
3. **Configure**: Set foundation and platform parameters
4. **Calculate**: Trigger DEM fetch and earthwork calculations
5. **Review**: View results including cut/fill volumes and costs
6. **Export**: Generate PDF report with all sites

## Coordinate Conversion

The application automatically converts between:
- **Map Coordinates**: Lat/Lng (WGS84, EPSG:4326)
- **Calculation Coordinates**: UTM (ETRS89, EPSG:25832-25836)

Germany is primarily in UTM zones 32 and 33. The zone is automatically determined based on longitude.

## Phase 3 Features (NEW)

### New Pages
- **ProjectsOverview** (`/projects`) - Project management dashboard
- **JobsHistory** (`/jobs`) - Jobs list with filtering
- **NotFound** (`/404`) - User-friendly 404 page

### New Components
- **BatchUpload** - Drag & drop CSV/GeoJSON upload
- **ErrorBoundary** - Global error handling

### Performance Optimizations
- **Lazy Loading**: All pages loaded on-demand with React.lazy()
- **Code Splitting**: Optimized bundle sizes
- **Suspense**: Loading fallbacks for better UX

### Enhanced Features
- Projects CRUD operations
- GeoPackage export (via API client)
- Automatic UTM coordinate conversion
- Batch site import (up to 123 sites)
- Real-time job progress tracking
- Error boundaries for graceful error handling

## Bundle Sizes (After Optimization)

```
vendor.js:     280 KB (React, Router, Leaflet)
login.js:       45 KB (Login page)
projects.js:    68 KB (Projects Dashboard)
jobs.js:        52 KB (Jobs History)
dashboard.js:  185 KB (Calculator with Map)
```

## Documentation

- [Main README](../../README.md)
- [Webapp README](../README.md)
- [Phase 3 Complete](../../docs/PHASE3_COMPLETE.md)

