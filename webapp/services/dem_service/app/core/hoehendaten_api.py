"""
hoehendaten.de API Integration

WICHTIG: Dieser Code ist basierend auf der funktionierenden QGIS-Plugin-Implementation
in plugin/prototype/WindTurbine_Earthwork_Calculator.py

Die API erwartet:
- UTM-Koordinaten (Zone, Easting, Northing)
- Koordinaten als Floats
- Kacheln sind 1x1km groß
"""
import base64
import io
import json
import logging
from typing import List, Tuple, Optional, Dict
from pathlib import Path
import requests
import rasterio
from rasterio.merge import merge
from rasterio.io import MemoryFile
import numpy as np

logger = logging.getLogger(__name__)

# API Configuration
HOEHENDATEN_API_URL = "https://api.hoehendaten.de:14444/v1/rawtif"
TILE_SIZE = 1000  # 1km tiles


def extract_utm_zone_from_epsg(epsg_code: int) -> int:
    """
    Extrahiert UTM Zone aus EPSG Code

    Args:
        epsg_code: EPSG Code (z.B. 25832, 32632)

    Returns:
        UTM Zone (z.B. 32)

    Raises:
        ValueError: Wenn kein UTM-System
    """
    # EPSG:32601-32660 (WGS84 UTM Nord)
    if 32601 <= epsg_code <= 32660:
        return epsg_code - 32600

    # EPSG:32701-32760 (WGS84 UTM Süd)
    elif 32701 <= epsg_code <= 32760:
        return epsg_code - 32700

    # EPSG:25832-25836 (ETRS89 UTM für Deutschland)
    elif 25832 <= epsg_code <= 25836:
        return epsg_code - 25800

    else:
        raise ValueError(
            f"EPSG:{epsg_code} ist kein UTM-System. "
            f"Erwarte EPSG:25832-25836 oder EPSG:32632-32636"
        )


def validate_utm_crs(crs_string: str) -> Tuple[int, int]:
    """
    Validiert CRS und extrahiert UTM Zone

    Args:
        crs_string: CRS String (z.B. "EPSG:25832")

    Returns:
        Tuple (epsg_code, utm_zone)

    Raises:
        ValueError: Wenn ungültiges Format oder kein UTM
    """
    if not crs_string.startswith("EPSG:"):
        raise ValueError(f"CRS muss Format 'EPSG:XXXXX' haben, bekam: {crs_string}")

    try:
        epsg_code = int(crs_string.split(":")[1])
    except (IndexError, ValueError):
        raise ValueError(f"Ungültiges CRS Format: {crs_string}")

    utm_zone = extract_utm_zone_from_epsg(epsg_code)

    logger.info(f"CRS validiert: {crs_string} → UTM Zone {utm_zone}")

    return epsg_code, utm_zone


def calculate_tiles_for_points(
    coordinates: List[Tuple[float, float]],
    radius_m: float = 250.0
) -> List[Tuple[float, float]]:
    """
    Berechnet benötigte 1x1km Kacheln für Punkte mit Radius

    WICHTIG: 250m Buffer um jeden Standort (nicht 100m!)

    Args:
        coordinates: Liste von (easting, northing) Tupeln in UTM
        radius_m: Radius um jeden Punkt (Standard: 250m)

    Returns:
        Liste von (center_easting, center_northing) für Kachel-Zentren
    """
    tiles = set()

    logger.info(f"Berechne Kacheln für {len(coordinates)} Standorte mit {radius_m}m Radius")

    for i, (easting, northing) in enumerate(coordinates):
        # Bounding Box mit Radius um diesen Standort
        min_x = easting - radius_m
        max_x = easting + radius_m
        min_y = northing - radius_m
        max_y = northing + radius_m

        # Kacheln für diesen Standort berechnen
        tile_x_start = int(min_x / TILE_SIZE) * TILE_SIZE
        tile_x_end = int(max_x / TILE_SIZE) * TILE_SIZE
        tile_y_start = int(min_y / TILE_SIZE) * TILE_SIZE
        tile_y_end = int(max_y / TILE_SIZE) * TILE_SIZE

        standort_tiles = []
        for x in range(tile_x_start, tile_x_end + TILE_SIZE, TILE_SIZE):
            for y in range(tile_y_start, tile_y_end + TILE_SIZE, TILE_SIZE):
                # Kachel-Zentrum (wie in QGIS Plugin)
                center_x = x + TILE_SIZE / 2
                center_y = y + TILE_SIZE / 2
                tile_tuple = (center_x, center_y)
                tiles.add(tile_tuple)
                standort_tiles.append(tile_tuple)

        logger.debug(
            f"  Standort {i+1} @ ({easting:.0f}, {northing:.0f}): "
            f"{len(standort_tiles)} Kachel(n)"
        )

    logger.info(f"→ Gesamt: {len(tiles)} eindeutige Kachel(n) benötigt")

    return list(tiles)


def fetch_dem_tile_from_api(
    easting: float,
    northing: float,
    zone: int = 32,
    timeout: int = 30
) -> Optional[Dict]:
    """
    Holt eine einzelne 1x1km DEM-Kachel von der hoehendaten.de API

    Diese Funktion ist 1:1 aus dem QGIS Plugin übernommen und an Python angepasst.

    Args:
        easting: UTM Easting-Koordinate (Zentrum der Kachel)
        northing: UTM Northing-Koordinate (Zentrum der Kachel)
        zone: UTM Zone (Standard: 32 für Deutschland)
        timeout: Request timeout in Sekunden

    Returns:
        Dict mit:
        - 'data': Base64-kodierter GeoTIFF String
        - 'attribution': Quellenangabe
        - 'easting': Kachel Easting
        - 'northing': Kachel Northing
        - 'zone': UTM Zone

        Oder None bei Fehler
    """
    # Kachel auf 1km-Raster ausrichten (wie im QGIS Plugin)
    tile_easting = int(easting / 1000) * 1000 + 500
    tile_northing = int(northing / 1000) * 1000 + 500

    # Request-Payload (exakt wie im QGIS Plugin)
    payload = {
        "Type": "RawTIFRequest",
        "ID": f"webapp_{zone}_{tile_easting}_{tile_northing}",
        "Attributes": {
            "Zone": int(zone),
            "Easting": float(tile_easting),
            "Northing": float(tile_northing)
        }
    }

    # Headers (wie im QGIS Plugin)
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip'
    }

    logger.info(
        f"→ API-Anfrage: Zone {zone}, E={tile_easting}, N={tile_northing}"
    )
    logger.debug(f"  Payload: {json.dumps(payload)}")

    try:
        # API Call (wie im QGIS Plugin)
        response = requests.post(
            HOEHENDATEN_API_URL,
            data=json.dumps(payload),
            headers=headers,
            timeout=timeout
        )

        # Debug bei Fehler
        if response.status_code != 200:
            logger.error(f"  Status: {response.status_code}")
            logger.error(f"  Response: {response.text[:500]}")

        response.raise_for_status()

        data = response.json()

        # Validierung (wie im QGIS Plugin)
        if 'Attributes' not in data or 'RawTIFs' not in data['Attributes']:
            logger.error(f"Ungültige API-Response: {data}")
            return None

        raw_tifs = data['Attributes']['RawTIFs']

        if not raw_tifs or len(raw_tifs) == 0:
            logger.error('Keine DEM-Daten verfügbar für diese Koordinaten')
            return None

        # Erste Kachel verwenden (wie im QGIS Plugin)
        tile_data = raw_tifs[0]

        result = {
            'data': tile_data.get('Data'),
            'attribution': data['Attributes'].get('Attribution', 'hoehendaten.de'),
            'easting': tile_easting,
            'northing': tile_northing,
            'zone': zone
        }

        logger.info(f"  ✓ Kachel erfolgreich geladen (Attribution: {result['attribution']})")

        return result

    except requests.exceptions.Timeout:
        logger.error(f"Timeout beim API-Call nach {timeout}s")
        return None

    except requests.exceptions.HTTPError as e:
        logger.error(f"API-HTTP-Fehler: {e}")
        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"API-Request-Fehler: {e}")
        return None

    except Exception as e:
        logger.error(f"Unerwarteter Fehler: {e}", exc_info=True)
        return None


def decode_dem_tile(base64_data: str, easting: float, northing: float, zone: int) -> Optional[tuple]:
    """
    Dekodiert Base64 GeoTIFF Daten zu rasterio Dataset

    Args:
        base64_data: Base64-kodierter GeoTIFF String
        easting: Kachel center easting
        northing: Kachel center northing
        zone: UTM Zone

    Returns:
        Tuple of (MemoryFile, DatasetReader) or None
        IMPORTANT: MemoryFile must be kept alive to prevent data corruption
    """
    try:
        # Base64 dekodieren
        tif_bytes = base64.b64decode(base64_data)

        # Als rasterio Dataset öffnen
        # IMPORTANT: Return both memfile and dataset to keep memfile alive
        memfile = MemoryFile(tif_bytes)
        dataset = memfile.open()

        logger.debug(
            f"  Tile dekodiert: {dataset.width}x{dataset.height} px, "
            f"CRS: {dataset.crs}"
        )

        return (memfile, dataset)

    except Exception as e:
        logger.error(f"Fehler beim Dekodieren: {e}", exc_info=True)
        return None


def create_mosaic_from_tiles(tile_datasets: List[rasterio.DatasetReader]) -> Optional[np.ndarray]:
    """
    Erstellt Mosaik aus mehreren DEM-Kacheln

    Args:
        tile_datasets: Liste von rasterio Datasets

    Returns:
        Merged dataset oder None
    """
    if not tile_datasets:
        logger.error("Keine Kacheln zum Mergen")
        return None

    try:
        logger.info(f"Erstelle Mosaik aus {len(tile_datasets)} Kachel(n)...")

        # Merge tiles (wie im QGIS Plugin mit rasterio)
        mosaic, out_trans = merge(tile_datasets)

        logger.info(f"  ✓ Mosaik erstellt: {mosaic.shape}")

        return mosaic, out_trans, tile_datasets[0].crs

    except Exception as e:
        logger.error(f"Fehler beim Mosaik-Erstellen: {e}", exc_info=True)
        return None


def save_mosaic_to_file(
    mosaic: np.ndarray,
    transform,
    crs,
    output_path: Path
) -> bool:
    """
    Speichert Mosaik als GeoTIFF

    Args:
        mosaic: Mosaic array
        transform: Affine transform
        crs: CRS
        output_path: Ausgabe-Pfad

    Returns:
        True wenn erfolgreich
    """
    try:
        with rasterio.open(
            output_path,
            'w',
            driver='GTiff',
            height=mosaic.shape[1],
            width=mosaic.shape[2],
            count=1,
            dtype=mosaic.dtype,
            crs=crs,
            transform=transform,
            compress='lzw'
        ) as dst:
            dst.write(mosaic[0], 1)

        logger.info(f"  ✓ Mosaik gespeichert: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Fehler beim Speichern: {e}", exc_info=True)
        return False
