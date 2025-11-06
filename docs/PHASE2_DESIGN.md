# Phase 2: Extended Use Cases - Design Document

## Overview

Phase 2 extends the Geo-Engineering Platform from WKA-only to a comprehensive earthwork calculation system supporting:
1. **Road Construction** - Highway, access roads, forest roads
2. **Solar Parks** - Ground-mounted PV systems with foundations
3. **Terrain Modeling** - General cut/fill analysis for any polygon

## Architecture Changes

### 1. Calculation Service Extension

```
calculation_service/app/modules/
├── wka.py              # Phase 1: WKA calculations (existing)
├── road.py             # NEW: Road earthwork module
├── solar.py            # NEW: Solar park module
└── terrain.py          # NEW: General terrain module
```

### 2. Frontend Multi-Use-Case Support

```
frontend/src/
├── pages/
│   ├── Dashboard.tsx           # Multi-tab interface
│   ├── WKACalculator.tsx       # Phase 1 (existing)
│   ├── RoadCalculator.tsx      # NEW
│   ├── SolarCalculator.tsx     # NEW
│   └── TerrainCalculator.tsx   # NEW
└── components/
    ├── Map.tsx                 # Extended with drawing tools
    ├── WKAForm.tsx            # Phase 1 (existing)
    ├── RoadForm.tsx           # NEW
    ├── SolarForm.tsx          # NEW
    └── TerrainForm.tsx        # NEW
```

### 3. WebSocket for Real-Time Progress

```
API Gateway (Port 8000)
├── WebSocket endpoint: /ws/{job_id}
├── Celery worker integration
└── Progress broadcasting
```

### 4. Background Job Queue (Celery)

```
Job States:
1. pending (0%)
2. fetching_dem (20%)
3. calculating (40-70%)
4. computing_costs (80%)
5. generating_report (90%)
6. completed (100%)
7. failed
```

## Use Case Designs

### 1. Road Earthwork Module

**Input Parameters**:
- Road centerline (LineString geometry)
- Road width (m)
- Cross-section profile type:
  - Flat (0% crown)
  - Crowned (2% crown)
  - Super-elevated (3-8% banking)
- Design grade/slope (%)
- Cut slope angle (e.g., 1:1.5)
- Fill slope angle (e.g., 1:2)
- Ditch dimensions (optional)

**Calculation Method**:
1. Sample DEM along centerline at intervals (e.g., every 10m)
2. For each station:
   - Get existing ground elevation
   - Calculate design elevation (start + grade * distance)
   - Determine cut or fill depth
   - Calculate cross-section area
   - Apply slope angles for cut/fill
3. Compute volumes between stations using average-end-area method
4. Sum total cut and fill volumes

**Output**:
- Total cut volume (m³)
- Total fill volume (m³)
- Road length (m)
- Average cut depth (m)
- Average fill depth (m)
- Volume per station (profile data)

**API Endpoint**:
```
POST /calc/road
{
  "dem_id": "uuid",
  "centerline": [[x1,y1], [x2,y2], ...],
  "road_width": 6.0,
  "profile_type": "crowned",
  "design_grade": 2.5,
  "cut_slope": 1.5,
  "fill_slope": 2.0,
  "station_interval": 10.0
}
```

---

### 2. Solar Park Module

**Input Parameters**:
- Solar park boundary (Polygon)
- Array layout:
  - Panel dimensions (L x W)
  - Row spacing (m)
  - Panel tilt angle (°)
  - Orientation (azimuth)
- Foundation type:
  - Driven piles
  - Concrete footings
  - Screw anchors
- Access road specifications
- Grading strategy:
  - Minimal grading (follow terrain)
  - Terraced grading
  - Full site grading

**Calculation Method**:
1. Generate array layout within boundary
2. For each foundation location:
   - Sample DEM elevation
   - Calculate footing/pile requirements
3. For access roads:
   - Apply road calculation method
4. For grading:
   - **Minimal**: Only level under inverters/transformers
   - **Terraced**: Create level terraces every N rows
   - **Full**: Level entire site to optimal elevation

**Output**:
- Number of panels
- Total foundation volume (m³)
- Access road cut/fill (m³)
- Grading cut/fill (m³)
- Total cut volume (m³)
- Total fill volume (m³)
- Site area (m²)

**API Endpoint**:
```
POST /calc/solar
{
  "dem_id": "uuid",
  "boundary": [[x1,y1], [x2,y2], ...],
  "panel_width": 2.0,
  "panel_length": 1.0,
  "row_spacing": 5.0,
  "panel_tilt": 20,
  "foundation_type": "driven_piles",
  "grading_strategy": "minimal"
}
```

---

### 3. Terrain Modeling Module

**Input Parameters**:
- Analysis polygon (Polygon)
- Analysis type:
  - **Cut/Fill Balance**: Find optimal grade elevation
  - **Volume Calculation**: Calculate volumes at specified grade
  - **Slope Analysis**: Analyze slope percentages
  - **Contour Generation**: Generate contour lines
- Target elevation (for volume calculation)
- Optimization method (mean, min_cut, balanced)

**Calculation Method**:
1. Sample DEM within polygon at resolution
2. Depending on analysis type:
   - **Cut/Fill Balance**: Use optimization to find grade
   - **Volume**: Calculate cut/fill at target elevation
   - **Slope Analysis**: Calculate slope between adjacent points
   - **Contour**: Use marching squares algorithm

**Output**:
- Analysis type results
- Cut volume (m³)
- Fill volume (m³)
- Average elevation (m)
- Min/max elevation (m)
- Slope statistics (%, min/max/avg)
- Contour data (GeoJSON)

**API Endpoint**:
```
POST /calc/terrain
{
  "dem_id": "uuid",
  "polygon": [[x1,y1], [x2,y2], ...],
  "analysis_type": "cut_fill_balance",
  "optimization_method": "balanced",
  "resolution": 1.0
}
```

## Database Schema Extensions

### New Tables

```sql
-- Job tracking for async operations
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    project_id UUID REFERENCES projects(id),
    job_type VARCHAR(50) NOT NULL,  -- 'wka', 'road', 'solar', 'terrain'
    status VARCHAR(50) NOT NULL,     -- 'pending', 'running', 'completed', 'failed'
    progress INTEGER DEFAULT 0,      -- 0-100
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Project collaboration
CREATE TABLE project_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id),
    user_id UUID REFERENCES users(id),
    role VARCHAR(50) NOT NULL,  -- 'owner', 'editor', 'viewer'
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(project_id, user_id)
);

-- Road calculations
CREATE TABLE road_calculations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES jobs(id),
    centerline GEOMETRY(LINESTRING),
    road_width FLOAT,
    profile_type VARCHAR(50),
    design_grade FLOAT,
    total_cut FLOAT,
    total_fill FLOAT,
    road_length FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Solar calculations
CREATE TABLE solar_calculations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES jobs(id),
    boundary GEOMETRY(POLYGON),
    panel_count INTEGER,
    foundation_volume FLOAT,
    grading_cut FLOAT,
    grading_fill FLOAT,
    site_area FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Terrain calculations
CREATE TABLE terrain_calculations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES jobs(id),
    polygon GEOMETRY(POLYGON),
    analysis_type VARCHAR(50),
    cut_volume FLOAT,
    fill_volume FLOAT,
    avg_elevation FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## WebSocket Protocol

### Connection
```
ws://localhost:8000/ws/{job_id}?token={jwt_token}
```

### Message Format
```json
{
  "type": "progress",
  "job_id": "uuid",
  "status": "calculating",
  "progress": 45,
  "message": "Calculating road profiles...",
  "timestamp": "2025-11-05T10:30:00Z"
}
```

### Progress Events
1. `fetching_dem` (20%) - "Fetching elevation data..."
2. `calculating` (40-70%) - "Calculating earthwork volumes..."
3. `computing_costs` (80%) - "Computing costs..."
4. `generating_report` (90%) - "Generating report..."
5. `completed` (100%) - "Calculation complete!"
6. `failed` - "Error: {error_message}"

## Celery Task Structure

```python
@celery_app.task(bind=True)
def calculate_road_async(self, job_id: str, params: dict):
    # Update progress: fetching_dem (20%)
    update_job_progress(job_id, 20, "Fetching DEM data...")
    dem_data = fetch_dem(params)

    # Update progress: calculating (40%)
    update_job_progress(job_id, 40, "Calculating road profiles...")
    calculation_result = calculate_road(dem_data, params)

    # Update progress: computing_costs (80%)
    update_job_progress(job_id, 80, "Computing costs...")
    cost_result = calculate_costs(calculation_result, params)

    # Update progress: generating_report (90%)
    update_job_progress(job_id, 90, "Generating report...")
    report = generate_report(calculation_result, cost_result)

    # Update progress: completed (100%)
    update_job_progress(job_id, 100, "Calculation complete!")
    return {"calculation": calculation_result, "cost": cost_result, "report": report}
```

## Frontend UI Design

### Multi-Tab Dashboard

```
┌─────────────────────────────────────────────────┐
│ Geo-Engineering Platform    [User] [Logout]    │
├─────────────────────────────────────────────────┤
│ [WKA] [Road] [Solar] [Terrain] [Projects]      │
├─────────────────────────────────────────────────┤
│                                          │      │
│         Map (Leaflet)                    │ Form │
│                                          │      │
│                                          │      │
└──────────────────────────────────────────┴──────┘
```

### Road Form

```
Road Construction Calculator
─────────────────────────────
Drawing Mode: [Line] ✓
- Click to start road centerline
- Click to add points
- Double-click to finish

Road Parameters:
├─ Width: [6.0] m
├─ Profile: [Crowned ▼]
├─ Design Grade: [2.5] %
├─ Cut Slope: [1:1.5]
├─ Fill Slope: [1:2.0]
└─ Station Interval: [10] m

[Calculate]

Results:
├─ Road Length: 1,234 m
├─ Total Cut: 5,678 m³
├─ Total Fill: 3,456 m³
└─ Cost: €123,456
```

### Solar Form

```
Solar Park Calculator
─────────────────────────────
Drawing Mode: [Polygon] ✓
- Click to define park boundary
- Close polygon to finish

Panel Configuration:
├─ Width: [2.0] m
├─ Length: [1.0] m
├─ Row Spacing: [5.0] m
└─ Tilt Angle: [20] °

Foundation:
└─ Type: [Driven Piles ▼]

Grading:
└─ Strategy: [Minimal ▼]

[Calculate]

Results:
├─ Panel Count: 10,000
├─ Foundation: 1,234 m³
├─ Grading Cut: 5,678 m³
├─ Grading Fill: 3,456 m³
└─ Total Cost: €567,890
```

## Implementation Order

### Week 1: Road Module
1. ✅ Road calculation algorithm (`road.py`)
2. ✅ Road API endpoints
3. ✅ Road form component (frontend)
4. ✅ Road report template

### Week 2: Solar Module
1. ✅ Solar array layout algorithm
2. ✅ Solar calculation endpoints
3. ✅ Solar form component
4. ✅ Solar report template

### Week 3: Terrain Module
1. ✅ Terrain analysis algorithms
2. ✅ Terrain API endpoints
3. ✅ Terrain form component
4. ✅ Terrain report template

### Week 4: WebSocket & Background Jobs
1. ✅ Celery integration
2. ✅ WebSocket endpoint
3. ✅ Progress tracking UI
4. ✅ Job management

### Week 5: Multi-User & Polish
1. ✅ Project collaboration
2. ✅ User permissions
3. ✅ Historical archives
4. ✅ End-to-end testing

## Technical Considerations

### Performance
- Road calculations can be expensive (long roads with small intervals)
- Use Celery for calculations > 30 seconds
- Cache DEM data aggressively
- Implement cancellation for long-running jobs

### Accuracy
- Road: Use 3D spline interpolation for smooth profiles
- Solar: Account for panel shading in array layout
- Terrain: Use adaptive sampling density based on slope

### Validation
- Road: Maximum grade 15%, minimum radius for curves
- Solar: Minimum row spacing for maintenance access
- Terrain: Polygon must be valid (no self-intersections)

## Success Metrics

- ✅ All 3 new use cases implemented
- ✅ WebSocket real-time updates working
- ✅ Background jobs processing correctly
- ✅ Reports generated for all use cases
- ✅ Multi-user collaboration functional
- ✅ End-to-end tests passing

## Risk Mitigation

1. **Complex Algorithms**: Start with simple implementations, iterate
2. **Performance Issues**: Profile early, optimize hot paths
3. **WebSocket Stability**: Implement reconnection logic
4. **User Experience**: Get feedback early from test users
