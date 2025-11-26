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
        # Combine all geometries using QgsGeometry.collectGeometry
        # Note: QgsGeometry.unaryUnion does NOT exist! That's a Shapely function.
        result = QgsGeometry.collectGeometry(all_geoms)

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
