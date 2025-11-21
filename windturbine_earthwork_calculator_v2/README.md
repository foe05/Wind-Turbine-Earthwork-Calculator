# Wind Turbine Earthwork Calculator V2

**A QGIS Processing Plugin for Optimizing Wind Turbine Crane Pad Heights**

Version: 2.0.0
Author: Wind Energy Site Planning
Date: November 2025

---

## 📋 Overview

This QGIS plugin optimizes the platform height for wind turbine crane pads by calculating and minimizing earthwork volumes (cut and fill). It processes DXF files containing crane pad outlines, downloads high-resolution elevation data, and generates comprehensive reports with terrain profiles.

### Key Features

✅ **DXF Import** - Automatically converts DXF polylines to platform polygons
✅ **DEM Download** - Fetches 1m-resolution elevation data from hoehendaten.de API
✅ **Height Optimization** - Tests multiple heights to find minimal earthwork
✅ **Volume Calculations** - Accurate cut/fill calculations for platform and slopes
✅ **Terrain Profiles** - Generates cross-section visualizations
✅ **HTML Reports** - Professional reports with maps and statistics
✅ **GeoPackage Output** - All data stored in standard GIS format

---

## 🚀 Installation

### Prerequisites

- **QGIS LTR 3.34+** (Long Term Release)
- **Python 3.9+** (included with QGIS)
- **Internet connection** (for DEM download)

### Step 1: Copy Plugin to QGIS Directory

Copy the entire `windturbine_earthwork_calculator_v2` folder to your QGIS plugins directory:

**Linux:**
```bash
cp -r windturbine_earthwork_calculator_v2 ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
```

**Windows:**
```
C:\Users\{YourUsername}\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\
```

**macOS:**
```
~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/
```

### Step 2: Install Python Dependencies

The plugin requires two additional Python packages:

```bash
# Run this in your terminal/command prompt
pip install --user ezdxf requests
```

Alternatively, run the included installation script:

```bash
cd ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/windturbine_earthwork_calculator_v2
python install_dependencies.py
```

### Step 3: Enable Plugin in QGIS

1. Start QGIS
2. Go to **Plugins → Manage and Install Plugins**
3. Click **Installed**
4. Find **Wind Turbine Earthwork Calculator V2**
5. Check the checkbox to enable it

---

## 📖 Usage

### Quick Start

1. **Open Processing Toolbox**
   - View → Panels → Processing Toolbox
   - Or press `Ctrl+Alt+T`

2. **Find the Algorithm**
   - Expand **Wind Turbine Earthwork Calculator V2**
   - Double-click **Optimize Platform Height**

3. **Configure Parameters**
   - **Input DXF File**: Select your crane pad DXF file
   - **Min/Max Height**: Set height range (e.g., 300-310m ü.NN)
   - **Output GeoPackage**: Choose output file path

4. **Run**
   - Click **Run**
   - Wait for processing (typically 2-5 minutes)

### Input Requirements

#### DXF File Format

- **Entities**: LWPOLYLINE or POLYLINE
- **CRS**: EPSG:25832 (UTM Zone 32N)
- **Closure**: Lines will be automatically connected
- **Layer**: Any layer (default: Layer '0')

Example DXF structure:
```
- LWPOLYLINE entities (42 lines forming crane pad outline)
- Coordinates in meters (UTM 32N)
- Not necessarily closed (plugin connects them automatically)
```

#### Height Range

- **Min Height**: Minimum platform height to test (m ü.NN)
- **Max Height**: Maximum platform height to test (m ü.NN)
- **Step**: Height increment for optimization (default: 0.1m)

**Example**: Min=300, Max=310, Step=0.1 → Tests 101 scenarios

### Advanced Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| Height Step | 0.1 m | 0.01-10 m | Optimization granularity |
| DXF Tolerance | 0.01 m | 0.001-10 m | Point connection tolerance |
| Slope Angle | 45° | 15-60° | Embankment slope angle |
| Num Profiles | 8 | 4-16 | Number of terrain cross-sections |
| Vertical Exag. | 2.0x | 1.0-5.0x | Profile visualization scaling |
| Force DEM Refresh | False | - | Ignore cache, re-download DEM |

### Output Files

After successful execution, you'll get:

```
output_directory/
├── project.gpkg                  # GeoPackage with all vector data
│   ├── platform_polygon          # Optimized crane pad polygon
│   └── profile_lines             # Terrain cross-section lines
├── project.dem.tif               # DEM mosaic (GeoTIFF)
├── project.html                  # HTML report
└── profiles/                     # Terrain profile images
    ├── profile_001.png
    ├── profile_002.png
    ├── ...
    └── profile_008.png
```

---

## 🔧 Workflow Details

### Step 1: DXF Import

The plugin:
1. Reads all LWPOLYLINE entities from the DXF file
2. Connects polylines by matching endpoints (within tolerance)
3. Creates a closed polygon
4. Validates topology (no self-intersections, valid area)

**Output**: QGIS polygon geometry in EPSG:25832

### Step 2: DEM Download

The plugin:
1. Calculates required 1km×1km DEM tiles (with 250m buffer)
2. Downloads tiles from hoehendaten.de API
3. Caches tiles locally (~/.qgis3/windturbine_calculator_v2/dem_cache/)
4. Mosaics tiles into single raster

**Note**: First run downloads tiles (~10-40 MB), subsequent runs use cache.

### Step 3: Height Optimization

For each height h in range (min → max, step):
1. Sample DEM elevations within platform polygon
2. Calculate cut volume (where terrain > platform)
3. Calculate fill volume (where terrain < platform)
4. Calculate slope/embankment volumes
5. Sum total volume moved

**Optimal height** = height with minimum total volume

### Step 4: Terrain Profiles

The plugin generates radial cross-sections:
- 8 equally-spaced lines from platform center
- Samples DEM along each line (0.5m intervals)
- Creates matplotlib plots showing:
  - Existing terrain (black line)
  - Planned platform (blue line)
  - Cut areas (red fill)
  - Fill areas (green fill)

### Step 5: HTML Report

Generates a professional report with:
- Executive summary (optimal height, volumes)
- Project parameters (location, area, slope angle)
- Detailed results (terrain statistics, volume breakdown)
- Embedded terrain profile images
- Print-friendly styling

---

## 🛠️ Troubleshooting

### Plugin doesn't appear in QGIS

**Solution:**
1. Check plugin directory location
2. Ensure `__init__.py` and `metadata.txt` exist
3. Restart QGIS
4. Check **Plugins → Manage and Install Plugins → Installed**

### ImportError: No module named 'ezdxf'

**Solution:**
```bash
pip install --user ezdxf
```
Or run `install_dependencies.py`

### DEM Download Fails (HTTP 404)

**Reason**: Tile not available on hoehendaten.de

**Solution**:
- Check if your area is covered by German DEM data
- Verify DXF coordinates are in EPSG:25832
- Try with a different location

### Processing takes very long

**Reasons**:
- Height range too large
- Height step too small
- Too many scenarios

**Solution**:
- Reduce height range (e.g., 300-305 instead of 300-400)
- Increase step size (e.g., 0.2m instead of 0.1m)
- Aim for < 1000 scenarios

### Polygon is invalid (self-intersection)

**Reason**: DXF polylines create invalid geometry

**Solution**:
- Check DXF file in CAD software
- Ensure polylines form a valid closed shape
- Fix overlapping segments
- Adjust DXF tolerance parameter

---

## 📊 Example

### Input

- **DXF File**: `Kranstellfläche_Marsberg_V172-7.2-175m.dxf`
- **Location**: Marsberg, Germany (EPSG:25832)
- **Min Height**: 300.0 m ü.NN
- **Max Height**: 310.0 m ü.NN
- **Step**: 0.1 m

### Output

```
Optimal Platform Height: 305.3 m ü.NN
Total Cut Volume: 3,421 m³
Total Fill Volume: 2,987 m³
Total Earthwork: 6,408 m³
Net Balance: +434 m³ (surplus cut)

Platform Area: 1,850 m²
Terrain Range: 8.5 m (min: 301.2, max: 309.7)
```

---

## 🐛 Known Issues

1. **GeoPackage Raster Support**: QGIS sometimes has issues with rasters in GeoPackage. DEM is saved as separate GeoTIFF.
2. **Large DXF Files**: Very complex DXF files (>1000 polylines) may be slow to import.
3. **Memory Usage**: Processing large DEMs (>10km²) may require significant RAM.

---

## 🔄 Changelog

### Version 2.0.0 (November 2025)

- Complete refactoring as QGIS Processing Plugin
- Modular architecture (separation of concerns)
- DXF import with automatic polygon generation
- hoehendaten.de API integration with caching
- Automated terrain profile generation
- Professional HTML reports
- Comprehensive error handling and validation
- Full logging support

### Version 1.0 (Previous)

- Initial standalone script version
- Manual workflow
- Single-file implementation

---

## 📝 License

This plugin is provided "as-is" for wind energy site planning purposes.

---

## 👥 Support

For issues, questions, or feature requests:

1. Check this README and troubleshooting section
2. Review QGIS logs: View → Panels → Log Messages
3. Check plugin logs: `~/.qgis3/windturbine_calculator_v2/*.log`

---

## 🙏 Acknowledgments

- **QGIS Project** - For the excellent GIS platform
- **hoehendaten.de** - For providing free high-resolution DEM data
- **ezdxf** - For DXF file parsing capabilities

---

**Happy Optimizing! 🌬️💨**
