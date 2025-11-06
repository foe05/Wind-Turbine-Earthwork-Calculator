"""
Foundation Volume Calculations

Extrahiert aus QGIS Plugin WindTurbine_Earthwork_Calculator.py
Konvertiert zu rasterio (statt QGIS QgsRasterLayer)
"""
import math
import numpy as np
from typing import Dict, Tuple, List, Optional


def calculate_foundation_circular(
    diameter: float,
    depth: float,
    foundation_type: int = 0
) -> Dict[str, float]:
    """
    Berechnet Fundament-Volumen für kreisförmiges Fundament

    Args:
        diameter: Fundament-Durchmesser in Metern
        depth: Fundamenttiefe in Metern
        foundation_type: 0=shallow (flach), 1=deep (tief mit Konus), 2=pile (Pfahlgründung)

    Returns:
        Dict mit 'volume', 'diameter', 'depth', 'type'
    """
    radius = diameter / 2

    if foundation_type == 0:
        # Flachgründung (Zylinder)
        volume = math.pi * radius**2 * depth

    elif foundation_type == 1:
        # Tiefgründung mit Konus
        cylinder_depth = depth * 0.6
        cone_depth = depth * 0.4
        volume_cylinder = math.pi * radius**2 * cylinder_depth
        volume_cone = (1/3) * math.pi * radius**2 * cone_depth
        volume = volume_cylinder + volume_cone

    else:
        # Pfahlgründung (80% des Volumens)
        volume = math.pi * radius**2 * depth * 0.8

    return {
        'volume': volume,
        'diameter': diameter,
        'depth': depth,
        'type': foundation_type
    }


def calculate_foundation_polygon(
    polygon_points: List[Tuple[float, float]],
    dem_data: np.ndarray,
    dem_transform,
    depth: float,
    foundation_type: int = 0,
    resolution: float = 0.5
) -> Dict[str, float]:
    """
    Berechnet Fundament-Aushub für beliebige Polygon-Form

    Args:
        polygon_points: Liste von (x, y) Koordinaten des Polygons
        dem_data: NumPy Array mit DEM-Daten
        dem_transform: Affine Transform des DEM
        depth: Fundamenttiefe in Metern
        foundation_type: 0=shallow, 1=deep, 2=pile
        resolution: Sample-Auflösung in Metern

    Returns:
        Dict mit 'volume', 'area', 'depth', 'type'
    """
    from shapely.geometry import Polygon
    import rasterio

    # Polygon erstellen
    polygon = Polygon(polygon_points)
    polygon_area = polygon.area

    # DEM innerhalb Polygon samplen
    elevations = []

    # Bounding Box
    minx, miny, maxx, maxy = polygon.bounds

    # Sample-Punkte erstellen
    x_range = np.arange(minx, maxx, resolution)
    y_range = np.arange(miny, maxy, resolution)

    for x in x_range:
        for y in y_range:
            from shapely.geometry import Point
            if polygon.contains(Point(x, y)):
                # Höhe aus DEM extrahieren
                row, col = rasterio.transform.rowcol(dem_transform, x, y)

                if 0 <= row < dem_data.shape[0] and 0 <= col < dem_data.shape[1]:
                    elevation = dem_data[row, col]
                    if not np.isnan(elevation):
                        elevations.append((x, y, elevation))

    if len(elevations) == 0:
        raise ValueError("Keine DEM-Daten in Fundament-Polygon!")

    # Mittlere Geländehöhe
    avg_existing_z = np.mean([z for (x, y, z) in elevations])

    # Fundament-Sohle
    foundation_bottom = avg_existing_z - depth

    # Cut-Volumen berechnen
    foundation_cut = 0.0
    cell_area = resolution * resolution

    for (x, y, existing_z) in elevations:
        if existing_z > foundation_bottom:
            cut_height = existing_z - foundation_bottom
            foundation_cut += cut_height * cell_area

    # Typ-basierte Anpassung
    if foundation_type == 1:  # Tiefgründung mit Konus
        foundation_cut *= 1.1
    elif foundation_type == 2:  # Pfahlgründung
        foundation_cut *= 0.8

    return {
        'volume': round(foundation_cut, 1),
        'area': round(polygon_area, 1),
        'depth': depth,
        'type': foundation_type
    }
