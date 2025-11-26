# Implementierungsanweisung: Geländeschnittkanten & Differenz-Raster

**Projekt:** Wind Turbine Earthwork Calculator V2
**Feature:** Terrain Intersection Lines & Cut/Fill Difference Rasters
**Version:** 1.0
**Datum:** 2025-11-26

---

## Inhaltsverzeichnis

1. [Projektziel](#projektziel)
2. [Architektur-Übersicht](#architektur-übersicht)
3. [Implementierungsplan](#implementierungsplan)
4. [Detaillierte Implementierung](#detaillierte-implementierung)
5. [Integration in Workflow](#integration-in-workflow)
6. [Testing & Validierung](#testing--validierung)
7. [Erwartete Outputs](#erwartete-outputs)

---

## Projektziel

### Was wird implementiert?

Für jede konstruierte Fläche (Fundament, Kranstellfläche, Auslegerfläche, Rotorfläche, Zufahrt) sollen zwei neue Features erstellt werden:

1. **Geländeschnittkanten-Linien (2D + 3D)**
   - Linien, die zeigen, wo die konstruierte Fläche die ursprüngliche Geländeoberfläche schneidet
   - 2D-Version: LineString für Kartenansicht
   - 3D-Version: LineStringZ für QGIS 3D-Viewer
   - Farbcodiert nach Flächentyp

2. **Differenz-Raster (Cut/Fill)**
   - Raster-Dateien (GeoTIFF) die zeigen: `Differenz = DEM - Soll-Oberfläche`
   - Positive Werte (rot): Abtrag nötig (Cut)
   - Negative Werte (grün): Auftrag nötig (Fill)
   - Null-Werte (weiß): Schnittkante (keine Erdarbeiten)

### Benötigte Outputs

**Schnittkanten-Layer (14 Layer im GeoPackage):**

| Fläche | Layer-Name 2D | Layer-Name 3D | Höhe | Farbe |
|--------|--------------|--------------|------|-------|
| Fundamentsohle | `gelaendeschnittkante_fundamentsohle` | `gelaendeschnittkante_fundamentsohle_3d` | FOK - foundation_depth | Braun (#8B4513) |
| Kranstellfläche Sohle | `gelaendeschnittkante_kranstellflaeche_sohle` | `gelaendeschnittkante_kranstellflaeche_sohle_3d` | crane_height | Rot (#FF0000) |
| Kranstellfläche Oberfläche | `gelaendeschnittkante_kranstellflaeche_oberflaeche` | `gelaendeschnittkante_kranstellflaeche_oberflaeche_3d` | crane_height + gravel_thickness | Orange (#FF8C00) |
| Auslegerfläche | `gelaendeschnittkante_auslegerflaeche` | `gelaendeschnittkante_auslegerflaeche_3d` | variabel (slope) | Grün (#00AA00) |
| Rotorfläche | `gelaendeschnittkante_rotorflaeche` | `gelaendeschnittkante_rotorflaeche_3d` | crane_height + rotor_offset + 0.3m | Violett (#AA00AA) |
| Zufahrt Sohle | `gelaendeschnittkante_zufahrt_sohle` | `gelaendeschnittkante_zufahrt_sohle_3d` | variabel (slope) | Blau (#0000FF) |
| Zufahrt Oberfläche | `gelaendeschnittkante_zufahrt_oberflaeche` | `gelaendeschnittkante_zufahrt_oberflaeche_3d` | variabel (slope) + gravel | Cyan (#00FFFF) |

**Differenz-Raster (7 GeoTIFF-Dateien):**

- `differenz_fundamentsohle.tif`
- `differenz_kranstellflaeche_sohle.tif`
- `differenz_kranstellflaeche_oberflaeche.tif`
- `differenz_auslegerflaeche.tif`
- `differenz_rotorflaeche.tif`
- `differenz_zufahrt_sohle.tif`
- `differenz_zufahrt_oberflaeche.tif`

---

## Architektur-Übersicht

### Neue Dateien

```
windturbine_earthwork_calculator_v2/
├── utils/
│   └── terrain_intersection.py          # NEU: Haupt-Implementierung
├── core/
│   ├── surface_types.py                 # ERWEITERN: Neue Felder
│   ├── multi_surface_calculator.py      # ERWEITERN: Berechnungs-Methode
│   └── workflow_runner.py               # ERWEITERN: Integration + QGIS-Styling
```

### Datenfluss

```
1. Berechnung der optimalen Höhe (bestehendes System)
                    ↓
2. calculate_terrain_intersection_lines()
                    ↓
   ┌────────────────┴────────────────┐
   │                                 │
   ↓                                 ↓
Horizontale Flächen            Geneigte Flächen
   │                                 │
   ↓                                 ↓
create_difference_raster_      create_target_surface_raster()
horizontal()                          ↓
   │                           create_difference_raster_
   │                           from_surfaces()
   └────────────────┬────────────────┘
                    ↓
         Differenz-Raster (GeoTIFF)
                    ↓
         extract_contour_at_height(0.0)
                    ↓
         Schnittkanten-Linien (2D + 3D)
                    ↓
         Speichern in GeoPackage + Output-Ordner
                    ↓
         Laden in QGIS mit Styling
```

---

## Implementierungsplan

### Phase 1: Grundstruktur ✅
- **Task 1.1:** Erstelle neue Datei `utils/terrain_intersection.py`
- **Task 1.2:** Erweitere `surface_types.py` um neue Felder
- **Task 1.3:** Erstelle Helper-Funktionen

### Phase 2: Differenz-Raster (Horizontal) ✅
- **Task 2.1:** Implementiere `create_polygon_mask()`
- **Task 2.2:** Implementiere `create_difference_raster_horizontal()`
- **Task 2.3:** Teste mit Kranstellfläche

### Phase 3: Konturlinien-Extraktion ✅
- **Task 3.1:** Implementiere `extract_contour_at_height()`
- **Task 3.2:** Implementiere `line_to_linestringz_constant()`
- **Task 3.3:** Implementiere `extract_terrain_intersection_horizontal()` komplett
- **Task 3.4:** Teste Ende-zu-Ende

### Phase 4: Geneigte Flächen ✅
- **Task 4.1:** Implementiere `create_target_surface_raster()`
- **Task 4.2:** Implementiere `create_difference_raster_from_surfaces()`
- **Task 4.3:** Implementiere `extract_terrain_intersection_sloped()`
- **Task 4.4:** Teste mit Auslegerfläche

### Phase 5: Integration in Workflow ✅
- **Task 5.1:** Implementiere `calculate_terrain_intersection_lines()` in `multi_surface_calculator.py`
- **Task 5.2:** Integriere in `workflow_runner.run_workflow()`
- **Task 5.3:** Erweitere `_save_to_geopackage()`
- **Task 5.4:** Erweitere `_add_to_qgis()`

### Phase 6: Styling & Validierung ✅
- **Task 6.1:** Implementiere `apply_cutfill_styling()`
- **Task 6.2:** Teste alle 7 Flächentypen
- **Task 6.3:** Validiere 3D-Darstellung
- **Task 6.4:** Prüfe Raster-Werte

---

## Detaillierte Implementierung

### Task 1.1: Neue Datei `utils/terrain_intersection.py`

**Erstelle:** `windturbine_earthwork_calculator_v2/utils/terrain_intersection.py`

```python
"""
Terrain Intersection Line Extraction

Extrahiert Schnittkanten zwischen konstruierten Flächen und ursprünglichem Gelände.

Author: Wind Energy Site Planning
Version: 2.0.0 - Terrain Intersection Extension
"""

import numpy as np
import os
import tempfile
from typing import Tuple, Optional
from osgeo import gdal, ogr, osr

from qgis.core import (
    QgsGeometry,
    QgsPoint,
    QgsLineString,
    QgsMultiLineString,
    QgsPointXY,
    QgsVectorLayer,
    QgsFeature,
    QgsFields,
    QgsField,
    QgsWkbTypes
)
from qgis.PyQt.QtCore import QVariant

from ..utils.logging_utils import get_plugin_logger


logger = get_plugin_logger()


def extract_terrain_intersection_horizontal(
    polygon: QgsGeometry,
    target_height: float,
    dem_path: str,
    output_raster_path: str,
    tolerance: float = 0.1
) -> Tuple[QgsGeometry, QgsGeometry, str]:
    """
    Extrahiert Schnittkante für horizontale Fläche.

    Algorithmus:
    1. Erstelle Differenz-Raster: DEM - target_height
    2. Extrahiere Konturlinie bei Wert = 0
    3. Erstelle 3D-Version mit Z = target_height

    Args:
        polygon: 2D-Polygon der Fläche
        target_height: Zielhöhe der konstruierten Fläche (m)
        dem_path: Pfad zum DEM
        output_raster_path: Pfad zum Speichern des Differenz-Rasters
        tolerance: Toleranz für Konturlinien-Extraktion (m)

    Returns:
        (line_2d, line_3d, raster_path): Tuple von 2D LineString,
                                          3D LineStringZ und
                                          Pfad zum Differenz-Raster
    """
    logger.info(f"Extracting terrain intersection for horizontal surface at {target_height}m")

    # 1. Erstelle Differenz-Raster
    diff_raster = create_difference_raster_horizontal(
        dem_path,
        polygon,
        target_height,
        output_raster_path
    )

    # 2. Extrahiere Konturlinie bei Wert = 0
    line_2d = extract_contour_at_height(diff_raster, polygon, height=0.0, tolerance=tolerance)

    # 3. Erstelle 3D-Version mit konstantem Z
    line_3d = line_to_linestringz_constant(line_2d, target_height)

    logger.info(f"Terrain intersection extracted: {line_2d.length():.1f}m length")

    return (line_2d, line_3d, output_raster_path)


def extract_terrain_intersection_sloped(
    polygon: QgsGeometry,
    base_height: float,
    slope_percent: float,
    slope_direction_deg: float,
    dem_path: str,
    output_raster_path: str,
    resolution: float = 1.0
) -> Tuple[QgsGeometry, QgsGeometry, str]:
    """
    Extrahiert Schnittkante für geneigte Fläche.

    Algorithmus:
    1. Erstelle Ziel-Oberflächen-Raster (Target Surface) mit Neigung
    2. Berechne Differenz-Raster: DEM - Target Surface
    3. Extrahiere Konturlinie bei Wert = 0
    4. Erstelle 3D-Version mit Z-Werten aus DEM

    Args:
        polygon: 2D-Polygon der Fläche
        base_height: Höhe am Referenzpunkt (m)
        slope_percent: Neigung in Prozent
        slope_direction_deg: Richtung der Neigung in Grad (0° = Ost)
        dem_path: Pfad zum DEM
        output_raster_path: Pfad zum Speichern des Differenz-Rasters
        resolution: Auflösung des Ziel-Rasters in Metern

    Returns:
        (line_2d, line_3d, raster_path): Tuple von 2D LineString,
                                          3D LineStringZ und
                                          Pfad zum Differenz-Raster
    """
    logger.info(f"Extracting terrain intersection for sloped surface: "
                f"base={base_height}m, slope={slope_percent}%, dir={slope_direction_deg}°")

    # 1. Erstelle Ziel-Oberflächen-Raster
    target_surface_raster = create_target_surface_raster(
        polygon, base_height, slope_percent, slope_direction_deg,
        dem_path, resolution
    )

    # 2. Erstelle Differenz-Raster: DEM - Target Surface
    diff_raster = create_difference_raster_from_surfaces(
        dem_path,
        target_surface_raster,
        output_raster_path
    )

    # 3. Extrahiere Konturlinie bei Wert = 0
    line_2d = extract_contour_at_height(diff_raster, polygon, height=0.0)

    # 4. Erstelle 3D-Version mit Z-Werten aus DEM
    from ..utils.geometry_3d import line_to_linestringz
    line_3d = line_to_linestringz(line_2d, dem_path, z_offset=0.0)

    # Cleanup temporäres Target Surface Raster
    if os.path.exists(target_surface_raster):
        try:
            os.remove(target_surface_raster)
        except:
            pass

    logger.info(f"Terrain intersection extracted: {line_2d.length():.1f}m length")

    return (line_2d, line_3d, output_raster_path)


def create_difference_raster_horizontal(
    dem_path: str,
    polygon: QgsGeometry,
    target_height: float,
    output_path: str
) -> str:
    """
    Erstellt Differenz-Raster für horizontale Fläche.

    Raster-Wert = DEM - target_height
    - Positiv: Abtrag nötig (Cut)
    - Negativ: Auftrag nötig (Fill)
    - Null: Schnittkante

    Nur innerhalb des Polygons, außerhalb = NoData

    Args:
        dem_path: Pfad zum DEM
        polygon: Polygon der Fläche (Maske)
        target_height: Konstante Zielhöhe (m)
        output_path: Pfad für Output-Raster (GeoTIFF)

    Returns:
        Pfad zum erstellten Raster
    """
    logger.info(f"Creating horizontal difference raster at {target_height}m")

    # 1. Öffne DEM
    dem_ds = gdal.Open(dem_path, gdal.GA_ReadOnly)
    if dem_ds is None:
        raise ValueError(f"Could not open DEM: {dem_path}")

    dem_band = dem_ds.GetRasterBand(1)
    dem_data = dem_band.ReadAsArray().astype(float)
    geotransform = dem_ds.GetGeoTransform()
    projection = dem_ds.GetProjection()
    nodata = dem_band.GetNoDataValue()

    # 2. Erstelle Maske aus Polygon
    mask = create_polygon_mask(polygon, dem_ds)

    # 3. Berechne Differenz: DEM - target_height
    # Nur innerhalb der Maske, außerhalb = NoData
    diff_data = np.where(
        mask == 1,
        dem_data - target_height,
        -9999.0
    )

    # Handle original NoData values
    if nodata is not None:
        diff_data = np.where(dem_data == nodata, -9999.0, diff_data)

    # 4. Speichere als GeoTIFF
    driver = gdal.GetDriverByName('GTiff')
    out_ds = driver.Create(
        output_path,
        dem_ds.RasterXSize,
        dem_ds.RasterYSize,
        1,
        gdal.GDT_Float32,
        options=['COMPRESS=LZW', 'TILED=YES']
    )

    out_ds.SetGeoTransform(geotransform)
    out_ds.SetProjection(projection)

    out_band = out_ds.GetRasterBand(1)
    out_band.WriteArray(diff_data)
    out_band.SetNoDataValue(-9999.0)

    # Berechne Statistiken (wichtig für QGIS Min/Max)
    out_band.ComputeStatistics(False)

    # Cleanup
    out_band.FlushCache()
    out_ds.FlushCache()
    out_ds = None
    dem_ds = None

    logger.info(f"Difference raster created: {output_path}")

    return output_path


def create_difference_raster_from_surfaces(
    dem_path: str,
    target_surface_path: str,
    output_path: str
) -> str:
    """
    Erstellt Differenz-Raster aus zwei Oberflächen.

    Raster-Wert = DEM - Target_Surface
    - Positiv: Abtrag nötig (Cut)
    - Negativ: Auftrag nötig (Fill)
    - Null: Schnittkante

    Args:
        dem_path: Pfad zum DEM
        target_surface_path: Pfad zum Ziel-Oberflächen-Raster
        output_path: Pfad für Output-Raster (GeoTIFF)

    Returns:
        Pfad zum erstellten Raster
    """
    logger.info("Creating difference raster from two surfaces")

    # Öffne beide Raster
    dem_ds = gdal.Open(dem_path, gdal.GA_ReadOnly)
    target_ds = gdal.Open(target_surface_path, gdal.GA_ReadOnly)

    if dem_ds is None:
        raise ValueError(f"Could not open DEM: {dem_path}")
    if target_ds is None:
        raise ValueError(f"Could not open target surface: {target_surface_path}")

    # Lese Daten
    dem_data = dem_ds.GetRasterBand(1).ReadAsArray().astype(float)
    target_data = target_ds.GetRasterBand(1).ReadAsArray().astype(float)
    target_nodata = target_ds.GetRasterBand(1).GetNoDataValue()

    # Berechne Differenz
    diff_data = dem_data - target_data

    # Handle NoData: Wo Target NoData ist, soll auch Differenz NoData sein
    if target_nodata is not None:
        diff_data = np.where(target_data == target_nodata, -9999.0, diff_data)

    # Speichere als GeoTIFF
    driver = gdal.GetDriverByName('GTiff')
    out_ds = driver.Create(
        output_path,
        dem_ds.RasterXSize,
        dem_ds.RasterYSize,
        1,
        gdal.GDT_Float32,
        options=['COMPRESS=LZW', 'TILED=YES']
    )

    out_ds.SetGeoTransform(dem_ds.GetGeoTransform())
    out_ds.SetProjection(dem_ds.GetProjection())

    out_band = out_ds.GetRasterBand(1)
    out_band.WriteArray(diff_data)
    out_band.SetNoDataValue(-9999.0)
    out_band.ComputeStatistics(False)

    # Cleanup
    out_band.FlushCache()
    out_ds.FlushCache()
    out_ds = None
    dem_ds = None
    target_ds = None

    logger.info(f"Difference raster created: {output_path}")

    return output_path


def create_target_surface_raster(
    polygon: QgsGeometry,
    base_height: float,
    slope_percent: float,
    slope_direction_deg: float,
    dem_path: str,
    resolution: float = 1.0
) -> str:
    """
    Erstellt Raster der Soll-Oberfläche mit Neigung.

    Die Höhe variiert basierend auf der Position relativ zum Polygon-Zentrum:
    height(x,y) = base_height - distance_along_slope * (slope_percent / 100)

    Args:
        polygon: Polygon der Fläche
        base_height: Höhe am Referenzpunkt (Polygon-Zentrum) in m
        slope_percent: Neigung in Prozent
        slope_direction_deg: Richtung des Gefälles in Grad (0° = Ost)
        dem_path: Pfad zum DEM (für Georeferenzierung)
        resolution: Pixel-Größe in Metern

    Returns:
        Pfad zum temporären Target Surface Raster
    """
    logger.info(f"Creating target surface raster: slope={slope_percent}%, dir={slope_direction_deg}°")

    import math

    # Öffne DEM für Georeferenzierung
    dem_ds = gdal.Open(dem_path, gdal.GA_ReadOnly)
    dem_geotransform = dem_ds.GetGeoTransform()
    dem_projection = dem_ds.GetProjection()

    # Berechne Bounding Box des Polygons
    bbox = polygon.boundingBox()

    # Berechne Raster-Dimensionen
    width = int((bbox.width() / resolution) + 1)
    height = int((bbox.height() / resolution) + 1)

    # Neuer Geotransform für Target Surface
    target_geotransform = (
        bbox.xMinimum(),      # Origin X
        resolution,           # Pixel width
        0,                    # Rotation (0)
        bbox.yMaximum(),      # Origin Y
        0,                    # Rotation (0)
        -resolution           # Pixel height (negative!)
    )

    # Erstelle Output-Raster (temporär)
    temp_path = tempfile.mktemp(suffix='_target_surface.tif')

    driver = gdal.GetDriverByName('GTiff')
    target_ds = driver.Create(temp_path, width, height, 1, gdal.GDT_Float32)
    target_ds.SetGeoTransform(target_geotransform)
    target_ds.SetProjection(dem_projection)

    # Berechne Polygon-Zentrum als Referenzpunkt
    centroid = polygon.centroid().asPoint()

    # Berechne Richtungsvektor
    slope_rad = math.radians(slope_direction_deg)
    slope_dir_x = math.cos(slope_rad)
    slope_dir_y = math.sin(slope_rad)

    # Erstelle Polygon-Maske
    mask = create_polygon_mask(polygon, target_ds)

    # Erstelle Höhen-Array
    target_data = np.zeros((height, width), dtype=np.float32)

    for row in range(height):
        for col in range(width):
            # Geo-Koordinaten des Pixels
            x = target_geotransform[0] + col * target_geotransform[1]
            y = target_geotransform[3] + row * target_geotransform[5]

            # Vektor vom Zentrum zum Punkt
            dx = x - centroid.x()
            dy = y - centroid.y()

            # Distanz entlang der Gefälle-Richtung
            dist_along_slope = dx * slope_dir_x + dy * slope_dir_y

            # Höhenänderung (positives Gefälle = abfallend)
            height_change = dist_along_slope * (slope_percent / 100.0)

            # Zielhöhe
            target_height = base_height - height_change

            target_data[row, col] = target_height

    # Setze Werte außerhalb des Polygons auf NoData
    target_data = np.where(mask == 1, target_data, -9999.0)

    # Schreibe Raster
    target_band = target_ds.GetRasterBand(1)
    target_band.WriteArray(target_data)
    target_band.SetNoDataValue(-9999.0)
    target_band.ComputeStatistics(False)

    # Cleanup
    target_band.FlushCache()
    target_ds.FlushCache()
    target_ds = None
    dem_ds = None

    logger.info(f"Target surface raster created: {temp_path}")

    return temp_path


def create_polygon_mask(polygon: QgsGeometry, reference_ds: gdal.Dataset) -> np.ndarray:
    """
    Erstellt Binär-Maske aus Polygon.

    Args:
        polygon: QGIS Polygon-Geometrie
        reference_ds: GDAL Dataset für Georeferenzierung

    Returns:
        np.ndarray: 1 innerhalb Polygon, 0 außerhalb
    """
    # Erstelle Memory-Layer mit Polygon
    mem_driver = ogr.GetDriverByName('Memory')
    mem_ds = mem_driver.CreateDataSource('memData')

    # Erstelle Layer
    srs = osr.SpatialReference()
    srs.ImportFromWkt(reference_ds.GetProjection())
    mem_layer = mem_ds.CreateLayer('polygon', srs=srs, geom_type=ogr.wkbPolygon)

    # Füge Polygon hinzu
    wkt = polygon.asWkt()
    ogr_geom = ogr.CreateGeometryFromWkt(wkt)
    feature = ogr.Feature(mem_layer.GetLayerDefn())
    feature.SetGeometry(ogr_geom)
    mem_layer.CreateFeature(feature)

    # Erstelle Raster-Maske
    mask_driver = gdal.GetDriverByName('MEM')
    mask_ds = mask_driver.Create(
        '',
        reference_ds.RasterXSize,
        reference_ds.RasterYSize,
        1,
        gdal.GDT_Byte
    )
    mask_ds.SetGeoTransform(reference_ds.GetGeoTransform())
    mask_ds.SetProjection(reference_ds.GetProjection())

    # Rasterize Polygon
    gdal.RasterizeLayer(mask_ds, [1], mem_layer, burn_values=[1])

    # Lese Maske
    mask_array = mask_ds.GetRasterBand(1).ReadAsArray()

    # Cleanup
    mask_ds = None
    mem_ds = None

    return mask_array


def extract_contour_at_height(
    raster_path: str,
    polygon: QgsGeometry,
    height: float = 0.0,
    tolerance: float = 0.05
) -> QgsGeometry:
    """
    Extrahiert Konturlinie auf bestimmter Höhe innerhalb eines Polygons.

    Nutzt GDAL ContourGenerate für Konturlinien-Extraktion.

    Args:
        raster_path: Pfad zum Raster (z.B. Differenz-Raster)
        polygon: Polygon zum Clippen der Kontur
        height: Höhenwert der Konturlinie (default: 0.0 für Schnittkante)
        tolerance: Toleranz für Konturlinien-Extraktion

    Returns:
        QgsGeometry: LineString oder MultiLineString der Kontur
    """
    logger.info(f"Extracting contour at height {height}m")

    # Öffne Raster
    raster_ds = gdal.Open(raster_path, gdal.GA_ReadOnly)
    if raster_ds is None:
        logger.warning(f"Could not open raster: {raster_path}")
        return QgsGeometry()

    raster_band = raster_ds.GetRasterBand(1)

    # Erstelle temporären Vektor-Layer für Konturen
    temp_contour_path = tempfile.mktemp(suffix='_contours.shp')

    # Erstelle Shapefile für Konturen
    driver = ogr.GetDriverByName('ESRI Shapefile')
    contour_ds = driver.CreateDataSource(temp_contour_path)

    srs = osr.SpatialReference()
    srs.ImportFromWkt(raster_ds.GetProjection())

    contour_layer = contour_ds.CreateLayer('contour', srs=srs, geom_type=ogr.wkbLineString)

    # Feld für Höhenwert
    field_defn = ogr.FieldDefn('ELEV', ogr.OFTReal)
    contour_layer.CreateField(field_defn)

    # Extrahiere Konturlinie bei spezifischer Höhe
    # fixedLevelCount = 1, fixedLevels = [height]
    try:
        gdal.ContourGenerateEx(
            raster_band,
            contour_layer,
            options={
                'FIXED_LEVELS': [height],
                'ELEV_FIELD': 'ELEV'
            }
        )
    except Exception as e:
        logger.error(f"Contour generation failed: {e}")
        contour_ds = None
        raster_ds = None
        return QgsGeometry()

    # Cleanup GDAL
    contour_ds = None
    raster_ds = None

    # Lade Konturen als QGIS Layer
    contour_layer_qgis = QgsVectorLayer(temp_contour_path, 'contours', 'ogr')

    if not contour_layer_qgis.isValid() or contour_layer_qgis.featureCount() == 0:
        logger.warning("No contours found")
        return QgsGeometry()

    # Sammle alle Geometrien
    all_geoms = []
    for feature in contour_layer_qgis.getFeatures():
        geom = feature.geometry()
        if not geom.isEmpty():
            all_geoms.append(geom)

    if not all_geoms:
        return QgsGeometry()

    # Vereinige alle Linien
    if len(all_geoms) == 1:
        result = all_geoms[0]
    else:
        result = QgsGeometry.unaryUnion(all_geoms)

    # Clip mit Polygon
    if not polygon.isEmpty():
        result = result.intersection(polygon)

    # Cleanup temporäre Dateien
    try:
        import shutil
        import glob
        for f in glob.glob(temp_contour_path.replace('.shp', '.*')):
            os.remove(f)
    except:
        pass

    logger.info(f"Contour extracted: {result.length():.1f}m length")

    return result


def line_to_linestringz_constant(line_2d: QgsGeometry, z_value: float) -> QgsGeometry:
    """
    Konvertiert 2D-Linie zu 3D LineStringZ mit konstantem Z-Wert.

    Args:
        line_2d: 2D LineString oder MultiLineString
        z_value: Z-Wert für alle Punkte (m)

    Returns:
        LineStringZ oder MultiLineStringZ
    """
    if line_2d.isEmpty():
        return QgsGeometry()

    if line_2d.isMultipart():
        # MultiLineString
        lines_2d = line_2d.asMultiPolyline()
        lines_3d = []

        for line in lines_2d:
            points_3d = [QgsPoint(pt.x(), pt.y(), z_value) for pt in line]
            lines_3d.append(QgsLineString(points_3d))

        from qgis.core import QgsMultiLineString
        multi_line = QgsMultiLineString()
        for line in lines_3d:
            multi_line.addGeometry(line)

        return QgsGeometry(multi_line)
    else:
        # Single LineString
        vertices = line_2d.asPolyline()
        points_3d = [QgsPoint(pt.x(), pt.y(), z_value) for pt in vertices]

        return QgsGeometry(QgsLineString(points_3d))
```

---

### Task 1.2: Erweitere `core/surface_types.py`

**Füge folgende Felder zu den Dataclasses hinzu:**

```python
# In der Datei: windturbine_earthwork_calculator_v2/core/surface_types.py

# Finde die Klasse SurfaceCalculationResult und füge hinzu:

@dataclass
class SurfaceCalculationResult:
    # ... bestehende Felder ...

    # Geländeschnittkanten (NEU)
    terrain_intersection_2d: Optional[QgsGeometry] = None
    terrain_intersection_3d: Optional[QgsGeometry] = None
    terrain_intersection_raster_path: Optional[str] = None


# Finde die Klasse MultiSurfaceCalculationResult und füge hinzu:

@dataclass
class MultiSurfaceCalculationResult:
    # ... bestehende Felder ...

    # Kranstellfläche Schnittkanten (NEU)
    crane_terrain_intersection_base_2d: Optional[QgsGeometry] = None
    crane_terrain_intersection_base_3d: Optional[QgsGeometry] = None
    crane_terrain_intersection_base_raster_path: Optional[str] = None

    crane_terrain_intersection_surface_2d: Optional[QgsGeometry] = None
    crane_terrain_intersection_surface_3d: Optional[QgsGeometry] = None
    crane_terrain_intersection_surface_raster_path: Optional[str] = None

    # Zufahrt Schnittkanten (NEU)
    road_terrain_intersection_base_2d: Optional[QgsGeometry] = None
    road_terrain_intersection_base_3d: Optional[QgsGeometry] = None
    road_terrain_intersection_base_raster_path: Optional[str] = None

    road_terrain_intersection_surface_2d: Optional[QgsGeometry] = None
    road_terrain_intersection_surface_3d: Optional[QgsGeometry] = None
    road_terrain_intersection_surface_raster_path: Optional[str] = None
```

---

### Task 5.1: Erweitere `core/multi_surface_calculator.py`

**Füge folgende Methode zur Klasse `MultiSurfaceCalculator` hinzu:**

```python
# In der Datei: windturbine_earthwork_calculator_v2/core/multi_surface_calculator.py

# Füge Import hinzu (am Anfang der Datei):
import os

# Füge Methode zur Klasse MultiSurfaceCalculator hinzu:

def calculate_terrain_intersection_lines(
    self,
    results: 'MultiSurfaceCalculationResult',
    output_dir: str
) -> None:
    """
    Berechnet alle Geländeschnittkanten und Differenz-Raster.

    Für jede konstruierte Fläche wird berechnet:
    - 2D Schnittkante (LineString)
    - 3D Schnittkante (LineStringZ)
    - Differenz-Raster (GeoTIFF): DEM - Soll-Oberfläche

    Die Ergebnisse werden direkt im results-Objekt gespeichert.

    Args:
        results: MultiSurfaceCalculationResult (wird in-place modifiziert)
        output_dir: Verzeichnis zum Speichern der Differenz-Raster
    """
    from ..utils.terrain_intersection import (
        extract_terrain_intersection_horizontal,
        extract_terrain_intersection_sloped
    )

    dem_path = self.dem_layer.source()

    self.logger.info("Calculating terrain intersection lines for all surfaces...")

    # 1. Fundamentsohle (horizontal)
    if SurfaceType.FOUNDATION in results.surface_results:
        self.logger.info("Processing foundation terrain intersection...")
        foundation = results.surface_results[SurfaceType.FOUNDATION]
        fund_height = self.project.fok - self.project.foundation_depth

        raster_path = os.path.join(output_dir, 'differenz_fundamentsohle.tif')

        try:
            line_2d, line_3d, raster = extract_terrain_intersection_horizontal(
                self.project.foundation.geometry,
                fund_height,
                dem_path,
                raster_path
            )
            foundation.terrain_intersection_2d = line_2d
            foundation.terrain_intersection_3d = line_3d
            foundation.terrain_intersection_raster_path = raster
        except Exception as e:
            self.logger.error(f"Failed to create foundation intersection: {e}")

    # 2. Kranstellfläche Sohle (horizontal, ohne Schotter)
    if SurfaceType.CRANE_PAD in results.surface_results:
        self.logger.info("Processing crane pad base terrain intersection...")
        crane = results.surface_results[SurfaceType.CRANE_PAD]

        raster_path = os.path.join(output_dir, 'differenz_kranstellflaeche_sohle.tif')

        try:
            line_2d, line_3d, raster = extract_terrain_intersection_horizontal(
                self.project.crane_pad.geometry,
                crane.target_height,
                dem_path,
                raster_path
            )
            results.crane_terrain_intersection_base_2d = line_2d
            results.crane_terrain_intersection_base_3d = line_3d
            results.crane_terrain_intersection_base_raster_path = raster
        except Exception as e:
            self.logger.error(f"Failed to create crane base intersection: {e}")

    # 3. Kranstellfläche Oberfläche (horizontal, mit Schotter)
    if SurfaceType.CRANE_PAD in results.surface_results:
        self.logger.info("Processing crane pad surface terrain intersection...")
        crane = results.surface_results[SurfaceType.CRANE_PAD]
        surface_height = crane.target_height + self.project.gravel_thickness

        raster_path = os.path.join(output_dir, 'differenz_kranstellflaeche_oberflaeche.tif')

        try:
            line_2d, line_3d, raster = extract_terrain_intersection_horizontal(
                self.project.crane_pad.geometry,
                surface_height,
                dem_path,
                raster_path
            )
            results.crane_terrain_intersection_surface_2d = line_2d
            results.crane_terrain_intersection_surface_3d = line_3d
            results.crane_terrain_intersection_surface_raster_path = raster
        except Exception as e:
            self.logger.error(f"Failed to create crane surface intersection: {e}")

    # 4. Auslegerfläche (geneigt)
    if self.project.boom and SurfaceType.BOOM in results.surface_results:
        self.logger.info("Processing boom terrain intersection...")
        boom = results.surface_results[SurfaceType.BOOM]

        raster_path = os.path.join(output_dir, 'differenz_auslegerflaeche.tif')

        try:
            line_2d, line_3d, raster = extract_terrain_intersection_sloped(
                self.project.boom.geometry,
                boom.target_height,
                results.boom_slope_percent,
                self.boom_slope_direction,
                dem_path,
                raster_path
            )
            boom.terrain_intersection_2d = line_2d
            boom.terrain_intersection_3d = line_3d
            boom.terrain_intersection_raster_path = raster
        except Exception as e:
            self.logger.error(f"Failed to create boom intersection: {e}")

    # 5. Rotorfläche (horizontal, mit 30cm Holmen)
    if self.project.rotor_storage and SurfaceType.ROTOR_STORAGE in results.surface_results:
        self.logger.info("Processing rotor storage terrain intersection...")
        rotor = results.surface_results[SurfaceType.ROTOR_STORAGE]
        rotor_height = rotor.target_height + 0.3  # 30cm Holme

        raster_path = os.path.join(output_dir, 'differenz_rotorflaeche.tif')

        try:
            line_2d, line_3d, raster = extract_terrain_intersection_horizontal(
                self.project.rotor_storage.geometry,
                rotor_height,
                dem_path,
                raster_path
            )
            rotor.terrain_intersection_2d = line_2d
            rotor.terrain_intersection_3d = line_3d
            rotor.terrain_intersection_raster_path = raster
        except Exception as e:
            self.logger.error(f"Failed to create rotor intersection: {e}")

    # 6. Zufahrt Sohle (geneigt, ohne Schotter)
    if self.project.road_access and SurfaceType.ROAD_ACCESS in results.surface_results:
        self.logger.info("Processing road base terrain intersection...")
        road = results.surface_results[SurfaceType.ROAD_ACCESS]

        raster_path = os.path.join(output_dir, 'differenz_zufahrt_sohle.tif')

        try:
            line_2d, line_3d, raster = extract_terrain_intersection_sloped(
                self.project.road_access.geometry,
                road.target_height,
                results.road_slope_percent,
                self.road_slope_direction,
                dem_path,
                raster_path
            )
            results.road_terrain_intersection_base_2d = line_2d
            results.road_terrain_intersection_base_3d = line_3d
            results.road_terrain_intersection_base_raster_path = raster
        except Exception as e:
            self.logger.error(f"Failed to create road base intersection: {e}")

    # 7. Zufahrt Oberfläche (geneigt, mit Schotter)
    if self.project.road_access and SurfaceType.ROAD_ACCESS in results.surface_results:
        self.logger.info("Processing road surface terrain intersection...")
        road = results.surface_results[SurfaceType.ROAD_ACCESS]
        gravel = self.project.road_gravel_thickness if self.project.road_gravel_enabled else 0.0

        raster_path = os.path.join(output_dir, 'differenz_zufahrt_oberflaeche.tif')

        try:
            line_2d, line_3d, raster = extract_terrain_intersection_sloped(
                self.project.road_access.geometry,
                road.target_height + gravel,
                results.road_slope_percent,
                self.road_slope_direction,
                dem_path,
                raster_path
            )
            results.road_terrain_intersection_surface_2d = line_2d
            results.road_terrain_intersection_surface_3d = line_3d
            results.road_terrain_intersection_surface_raster_path = raster
        except Exception as e:
            self.logger.error(f"Failed to create road surface intersection: {e}")

    self.logger.info("Terrain intersection lines calculation complete")
```

---

### Task 5.2 & 5.3: Erweitere `core/workflow_runner.py`

**Ändere in der Methode `run_workflow()`:**

```python
# Finde die Stelle nach calculator.find_optimum() oder calculator.calculate_scenario()
# und füge VOR dem Aufruf von _save_to_geopackage() hinzu:

# Berechne Geländeschnittkanten
output_dir = os.path.dirname(gpkg_path)
calculator.calculate_terrain_intersection_lines(results, output_dir)
```

**Erweitere die Methode `_save_to_geopackage()`:**

Füge am Ende der Methode, nach dem Speichern der Böschungen-Layer, folgenden Code hinzu:

```python
# === GELÄNDESCHNITTKANTEN (2D und 3D) ===
# Helper-Funktion zum Speichern einer Schnittkante
def save_intersection_line(layer_name: str, geometry_2d: QgsGeometry,
                           geometry_3d: QgsGeometry, color: str,
                           description: str):
    """Speichert 2D und 3D Schnittkanten-Layer."""
    if geometry_2d is None or geometry_2d.isEmpty():
        return

    # 2D Layer
    fields_2d = QgsFields()
    fields_2d.append(QgsField('id', QVariant.Int))
    fields_2d.append(QgsField('length_m', QVariant.Double))
    fields_2d.append(QgsField('description', QVariant.String))
    fields_2d.append(QgsField('color', QVariant.String))

    feat_2d = QgsFeature(fields_2d)
    feat_2d.setGeometry(geometry_2d)
    feat_2d.setAttribute('id', 1)
    feat_2d.setAttribute('length_m', round(geometry_2d.length(), 2))
    feat_2d.setAttribute('description', description)
    feat_2d.setAttribute('color', color)

    options.layerName = layer_name
    writer = QgsVectorFileWriter.create(
        gpkg_path, fields_2d, QgsWkbTypes.LineString, crs,
        QgsCoordinateTransformContext(), options
    )
    writer.addFeature(feat_2d)
    del writer

    # 3D Layer
    if geometry_3d is not None and not geometry_3d.isEmpty():
        fields_3d = QgsFields()
        fields_3d.append(QgsField('id', QVariant.Int))
        fields_3d.append(QgsField('length_m', QVariant.Double))
        fields_3d.append(QgsField('description', QVariant.String))
        fields_3d.append(QgsField('color', QVariant.String))

        feat_3d = QgsFeature(fields_3d)
        feat_3d.setGeometry(geometry_3d)
        feat_3d.setAttribute('id', 1)
        feat_3d.setAttribute('length_m', round(geometry_3d.length(), 2))
        feat_3d.setAttribute('description', description)
        feat_3d.setAttribute('color', color)

        options.layerName = f"{layer_name}_3d"
        writer = QgsVectorFileWriter.create(
            gpkg_path, fields_3d, QgsWkbTypes.LineStringZ, crs,
            QgsCoordinateTransformContext(), options
        )
        writer.addFeature(feat_3d)
        del writer

# Speichere alle Schnittkanten
if SurfaceType.FOUNDATION in results.surface_results:
    foundation = results.surface_results[SurfaceType.FOUNDATION]
    save_intersection_line(
        'gelaendeschnittkante_fundamentsohle',
        foundation.terrain_intersection_2d,
        foundation.terrain_intersection_3d,
        '#8B4513',
        'Schnittkante Fundamentsohle mit ursprünglichem Gelände'
    )

save_intersection_line(
    'gelaendeschnittkante_kranstellflaeche_sohle',
    results.crane_terrain_intersection_base_2d,
    results.crane_terrain_intersection_base_3d,
    '#FF0000',
    'Schnittkante Kranstellfläche Sohle (ohne Schotter)'
)

save_intersection_line(
    'gelaendeschnittkante_kranstellflaeche_oberflaeche',
    results.crane_terrain_intersection_surface_2d,
    results.crane_terrain_intersection_surface_3d,
    '#FF8C00',
    'Schnittkante Kranstellfläche Oberfläche (mit Schotter)'
)

if project.boom and SurfaceType.BOOM in results.surface_results:
    boom = results.surface_results[SurfaceType.BOOM]
    save_intersection_line(
        'gelaendeschnittkante_auslegerflaeche',
        boom.terrain_intersection_2d,
        boom.terrain_intersection_3d,
        '#00AA00',
        'Schnittkante Auslegerfläche'
    )

if project.rotor_storage and SurfaceType.ROTOR_STORAGE in results.surface_results:
    rotor = results.surface_results[SurfaceType.ROTOR_STORAGE]
    save_intersection_line(
        'gelaendeschnittkante_rotorflaeche',
        rotor.terrain_intersection_2d,
        rotor.terrain_intersection_3d,
        '#AA00AA',
        'Schnittkante Rotorfläche'
    )

if project.road_access and SurfaceType.ROAD_ACCESS in results.surface_results:
    save_intersection_line(
        'gelaendeschnittkante_zufahrt_sohle',
        results.road_terrain_intersection_base_2d,
        results.road_terrain_intersection_base_3d,
        '#0000FF',
        'Schnittkante Zufahrt Sohle (ohne Schotter)'
    )

    save_intersection_line(
        'gelaendeschnittkante_zufahrt_oberflaeche',
        results.road_terrain_intersection_surface_2d,
        results.road_terrain_intersection_surface_3d,
        '#00FFFF',
        'Schnittkante Zufahrt Oberfläche (mit Schotter)'
    )

self.logger.info("Terrain intersection lines saved to GeoPackage")
```

---

### Task 5.4 & 6.1: Erweitere `_add_to_qgis()` in `workflow_runner.py`

**Füge am Ende der Methode `_add_to_qgis()` hinzu:**

```python
# === GELÄNDESCHNITTKANTEN ===
from qgis.core import QgsLineSymbol

subgroup_intersections = QgsLayerTreeGroup('Geländeschnittkanten')
group.addChildNode(subgroup_intersections)

intersection_layers = [
    ('gelaendeschnittkante_fundamentsohle', '#8B4513', 0.4),
    ('gelaendeschnittkante_kranstellflaeche_sohle', '#FF0000', 0.5),
    ('gelaendeschnittkante_kranstellflaeche_oberflaeche', '#FF8C00', 0.5),
    ('gelaendeschnittkante_auslegerflaeche', '#00AA00', 0.5),
    ('gelaendeschnittkante_rotorflaeche', '#AA00AA', 0.5),
    ('gelaendeschnittkante_zufahrt_sohle', '#0000FF', 0.5),
    ('gelaendeschnittkante_zufahrt_oberflaeche', '#00FFFF', 0.5),
]

for layer_name, color, width in intersection_layers:
    # 2D Layer
    layer_2d = QgsVectorLayer(f"{gpkg_path}|layername={layer_name}",
                              layer_name, "ogr")
    if layer_2d.isValid():
        # Style: Gestrichelte Linie
        symbol = QgsLineSymbol.createSimple({
            'line_color': color,
            'line_width': str(width),
            'line_style': 'dash',
            'capstyle': 'round'
        })
        layer_2d.renderer().setSymbol(symbol)
        QgsProject.instance().addMapLayer(layer_2d, False)
        subgroup_intersections.addLayer(layer_2d)

    # 3D Layer
    layer_3d = QgsVectorLayer(f"{gpkg_path}|layername={layer_name}_3d",
                              f"{layer_name}_3d", "ogr")
    if layer_3d.isValid():
        # Style: Gleiche Farbe für 3D
        symbol = QgsLineSymbol.createSimple({
            'line_color': color,
            'line_width': str(width),
            'line_style': 'solid',
            'capstyle': 'round'
        })
        layer_3d.renderer().setSymbol(symbol)
        QgsProject.instance().addMapLayer(layer_3d, False)
        subgroup_intersections.addLayer(layer_3d)


# === DIFFERENZ-RASTER (Cut/Fill) ===
from qgis.core import (
    QgsSingleBandPseudoColorRenderer,
    QgsColorRampShader,
    QgsRasterShader
)
from qgis.PyQt.QtGui import QColor

def apply_cutfill_styling(raster_layer: QgsRasterLayer):
    """
    Wendet Cut/Fill-Farbschema auf Differenz-Raster an.

    Farbskala:
    - Dunkelrot: Starker Abtrag (Cut > 5m)
    - Rot: Mittlerer Abtrag (0 < Cut < 5m)
    - Weiß: Schnittkante (≈ 0m)
    - Grün: Mittlerer Auftrag (0 < Fill < 5m)
    - Dunkelgrün: Starker Auftrag (Fill > 5m)
    """
    # Hole Min/Max-Werte aus Raster
    provider = raster_layer.dataProvider()
    stats = provider.bandStatistics(1)
    min_val = stats.minimumValue
    max_val = stats.maximumValue

    # Symmetrisch um 0 für bessere Visualisierung
    abs_max = max(abs(min_val), abs(max_val))

    # Erstelle Farbrampe
    shader = QgsRasterShader()
    color_ramp = QgsColorRampShader()
    color_ramp.setColorRampType(QgsColorRampShader.Interpolated)

    # Farbpunkte definieren
    items = [
        # Fill (negativ) = Grün-Töne
        QgsColorRampShader.ColorRampItem(-abs_max, QColor(0, 100, 0), f'Fill {abs_max:.1f}m'),
        QgsColorRampShader.ColorRampItem(-2.0, QColor(34, 139, 34), 'Fill 2m'),
        QgsColorRampShader.ColorRampItem(-0.5, QColor(144, 238, 144), 'Fill 0.5m'),
        QgsColorRampShader.ColorRampItem(-0.1, QColor(240, 255, 240), 'Fill 0.1m'),

        # Schnittkante = Weiß
        QgsColorRampShader.ColorRampItem(0.0, QColor(255, 255, 255), '0m (Schnittkante)'),

        # Cut (positiv) = Rot-Töne
        QgsColorRampShader.ColorRampItem(0.1, QColor(255, 240, 240), 'Cut 0.1m'),
        QgsColorRampShader.ColorRampItem(0.5, QColor(255, 200, 200), 'Cut 0.5m'),
        QgsColorRampShader.ColorRampItem(2.0, QColor(255, 100, 100), 'Cut 2m'),
        QgsColorRampShader.ColorRampItem(abs_max, QColor(139, 0, 0), f'Cut {abs_max:.1f}m'),
    ]

    color_ramp.setColorRampItemList(items)
    shader.setRasterShaderFunction(color_ramp)

    # Erstelle Renderer
    renderer = QgsSingleBandPseudoColorRenderer(provider, 1, shader)
    raster_layer.setRenderer(renderer)

    # Transparenz für NoData
    raster_layer.renderer().setNodataColor(QColor(0, 0, 0, 0))

    # Layer-Transparenz für bessere Überlagerung
    raster_layer.renderer().setOpacity(0.7)  # 70% Deckkraft

    raster_layer.triggerRepaint()


subgroup_diff_rasters = QgsLayerTreeGroup('Differenz-Raster (Cut/Fill)')
group.addChildNode(subgroup_diff_rasters)

diff_raster_configs = [
    ('differenz_fundamentsohle.tif', 'Differenz Fundamentsohle'),
    ('differenz_kranstellflaeche_sohle.tif', 'Differenz Kranstellfläche Sohle'),
    ('differenz_kranstellflaeche_oberflaeche.tif', 'Differenz Kranstellfläche Oberfläche'),
    ('differenz_auslegerflaeche.tif', 'Differenz Auslegerfläche'),
    ('differenz_rotorflaeche.tif', 'Differenz Rotorfläche'),
    ('differenz_zufahrt_sohle.tif', 'Differenz Zufahrt Sohle'),
    ('differenz_zufahrt_oberflaeche.tif', 'Differenz Zufahrt Oberfläche'),
]

output_dir = os.path.dirname(gpkg_path)

for raster_file, layer_name in diff_raster_configs:
    raster_path = os.path.join(output_dir, raster_file)

    if os.path.exists(raster_path):
        diff_layer = QgsRasterLayer(raster_path, layer_name)

        if diff_layer.isValid():
            # Styling: Cut/Fill-Farbschema
            apply_cutfill_styling(diff_layer)

            QgsProject.instance().addMapLayer(diff_layer, False)
            subgroup_diff_rasters.addLayer(diff_layer)

self.logger.info("Terrain intersection lines and difference rasters added to QGIS")
```

---

## Integration in Workflow

### Ablauf im `workflow_runner.py`:

```
1. run_workflow() wird aufgerufen
        ↓
2. DEM laden, Geometrien validieren
        ↓
3. calculator.find_optimum() oder calculate_scenario()
        ↓
4. calculator.calculate_terrain_intersection_lines(results, output_dir)  ← NEU
        ↓
5. _save_to_geopackage() - speichert alle Layer inkl. Schnittkanten
        ↓
6. _save_report() - PDF-Report
        ↓
7. _add_to_qgis() - lädt Layer + Raster mit Styling
```

---

## Testing & Validierung

### Test-Checkliste:

**Phase 1: Einzelne Funktionen**

✅ **Test 1.1:** `create_polygon_mask()`
- Erstelle einfaches Test-Polygon
- Prüfe ob Maske korrekt (1 innen, 0 außen)

✅ **Test 1.2:** `create_difference_raster_horizontal()`
- Teste mit Kranstellfläche
- Prüfe ob Raster erstellt wird
- Öffne in QGIS und prüfe Werte (positiv = Cut, negativ = Fill)

✅ **Test 1.3:** `extract_contour_at_height()`
- Teste mit Differenz-Raster aus 1.2
- Prüfe ob Linie extrahiert wird
- Prüfe ob Linie innerhalb Polygon liegt

**Phase 2: Horizontale Flächen**

✅ **Test 2.1:** Kranstellfläche Sohle
- Führe Workflow komplett aus
- Prüfe ob Layer im GeoPackage vorhanden
- Prüfe ob Raster erstellt wurde
- Prüfe 3D-Linie im 3D-Viewer

✅ **Test 2.2:** Fundamentsohle
- Analog zu 2.1

**Phase 3: Geneigte Flächen**

✅ **Test 3.1:** `create_target_surface_raster()`
- Teste mit Auslegerfläche
- Prüfe ob Gefälle korrekt (höher am einen Ende, niedriger am anderen)

✅ **Test 3.2:** Auslegerfläche komplett
- Führe Workflow aus
- Prüfe Schnittkante visuell
- Validiere 3D-Darstellung

**Phase 4: Integration**

✅ **Test 4.1:** Alle Flächen zusammen
- Workflow mit allen 7 Flächentypen
- Prüfe GeoPackage: 14 Linien-Layer vorhanden?
- Prüfe Output-Ordner: 7 Raster-Dateien vorhanden?

✅ **Test 4.2:** QGIS-Darstellung
- Öffne QGIS-Projekt
- Layer-Gruppe "Geländeschnittkanten" vorhanden?
- Farben korrekt?
- Layer-Gruppe "Differenz-Raster" vorhanden?
- Cut/Fill-Styling korrekt (Rot/Grün)?

✅ **Test 4.3:** 3D-Viewer
- Öffne QGIS 3D Map View
- Prüfe ob 3D-Linien korrekt dargestellt werden
- Prüfe Höhen-Korrektheit

**Phase 5: Validierung**

✅ **Test 5.1:** Höhen-Validierung
- Nimm Stichproben entlang Schnittkante
- Prüfe: DEM-Höhe ≈ Soll-Höhe (±Toleranz)

✅ **Test 5.2:** Differenz-Raster Werte
- Prüfe: Auf Schnittkante sollte Wert ≈ 0 sein
- Prüfe: Cut-Bereiche (rot) haben positive Werte
- Prüfe: Fill-Bereiche (grün) haben negative Werte

---

## Erwartete Outputs

### Nach erfolgreicher Implementierung:

**1. GeoPackage (`wea01_results.gpkg`):**

Neue Layer:
- `gelaendeschnittkante_fundamentsohle` (LineString)
- `gelaendeschnittkante_fundamentsohle_3d` (LineStringZ)
- `gelaendeschnittkante_kranstellflaeche_sohle` (LineString)
- `gelaendeschnittkante_kranstellflaeche_sohle_3d` (LineStringZ)
- `gelaendeschnittkante_kranstellflaeche_oberflaeche` (LineString)
- `gelaendeschnittkante_kranstellflaeche_oberflaeche_3d` (LineStringZ)
- `gelaendeschnittkante_auslegerflaeche` (LineString)
- `gelaendeschnittkante_auslegerflaeche_3d` (LineStringZ)
- `gelaendeschnittkante_rotorflaeche` (LineString)
- `gelaendeschnittkante_rotorflaeche_3d` (LineStringZ)
- `gelaendeschnittkante_zufahrt_sohle` (LineString)
- `gelaendeschnittkante_zufahrt_sohle_3d` (LineStringZ)
- `gelaendeschnittkante_zufahrt_oberflaeche` (LineString)
- `gelaendeschnittkante_zufahrt_oberflaeche_3d` (LineStringZ)

**2. Differenz-Raster (Output-Ordner):**

- `differenz_fundamentsohle.tif` (GeoTIFF, Float32, komprimiert)
- `differenz_kranstellflaeche_sohle.tif`
- `differenz_kranstellflaeche_oberflaeche.tif`
- `differenz_auslegerflaeche.tif`
- `differenz_rotorflaeche.tif`
- `differenz_zufahrt_sohle.tif`
- `differenz_zufahrt_oberflaeche.tif`

**3. QGIS-Projekt:**

Layer-Gruppen:
- **Geländeschnittkanten**
  - Farbcodierte gestrichelte Linien (2D)
  - Farbcodierte durchgezogene Linien (3D)

- **Differenz-Raster (Cut/Fill)**
  - 7 Raster mit Cut/Fill-Styling
  - Rot = Abtrag (Cut)
  - Grün = Auftrag (Fill)
  - Weiß = Schnittkante
  - 70% Transparenz

**4. 3D-Viewer:**

- Alle 3D-Linien korrekt auf Geländehöhe
- Farbcodiert nach Flächentyp
- Interaktiv navigierbar

---

## Troubleshooting

### Häufige Probleme:

**Problem 1: Keine Konturlinien gefunden**
- **Ursache:** Polygon liegt nicht im DEM-Bereich ODER Soll-Höhe außerhalb DEM-Wertebereich
- **Lösung:** Prüfe DEM-Statistiken und Polygon-Position

**Problem 2: Leeres Differenz-Raster**
- **Ursache:** Polygon-Maske fehlerhaft
- **Lösung:** Prüfe `create_polygon_mask()`, validiere Geometrie

**Problem 3: 3D-Linien falsch dargestellt**
- **Ursache:** Z-Werte nicht korrekt aus DEM gelesen
- **Lösung:** Prüfe DEM-Pfad und Koordinatensystem

**Problem 4: GDAL ContourGenerate Error**
- **Ursache:** GDAL-Version zu alt oder falsche Parameter
- **Lösung:** Prüfe GDAL-Version (>= 3.0 empfohlen)

---

## Zusammenfassung

Nach erfolgreicher Implementierung bietet das Plugin:

✅ **Visualisierung der Schnittkanten** zwischen konstruierten Flächen und Gelände
✅ **Cut/Fill-Analyse** durch Differenz-Raster
✅ **2D- und 3D-Darstellung** für QGIS Map und 3D-Viewer
✅ **Farbcodierte Layer** für intuitive Interpretation
✅ **Permanente Raster-Dateien** für weitere Analysen

**Erfolg!** 🎉
