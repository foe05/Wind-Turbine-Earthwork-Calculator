"""
BGR Bodendaten WFS-Client (Port aus core/bgr_soil_api.py).

QGIS-frei: pyproj statt QgsCoordinateTransform, requests statt urllib.
"""

from __future__ import annotations

import logging
from typing import Optional

import requests
from pyproj import Transformer

log = logging.getLogger(__name__)


class BGREndpointUnavailable(Exception):
    """BGR-Endpoint ist nicht verfügbar (z. B. HTTP 404)."""


# Bodenart-Mapping BGR-Codes → vereinfachte Kategorien
BGR_SOIL_TYPE_MAPPING = {
    "TT": "Ton", "LT": "Ton", "TL": "Ton", "Tu": "Ton",
    "UU": "Schluff", "UT": "Schluff", "UL": "Schluff", "Us": "Schluff",
    "LL": "Lehm", "LU": "Lehm", "Lu": "Lehm", "Ls": "Lehm",
    "SS": "Sand", "SU": "Sand", "SL": "Sand", "St": "Sand", "Su": "Sand",
    "GG": "Kies", "GS": "Kies", "Gu": "Kies",
    "HH": "Torf", "HN": "Torf",
}


class BGRSoilAPI:
    """Client für BGR WFS-Services (BÜK200, BÜK1000)."""

    BGR_WFS_BUEK200 = "https://services.bgr.de/wfs/boden/buek200"
    BGR_WFS_BUEK1000 = "https://services.bgr.de/wfs/boden/buek1000"
    WFS_VERSION = "2.0.0"

    def __init__(self, timeout: int = 10, endpoint: Optional[str] = None):
        self.timeout = timeout
        self.endpoint = endpoint or self.BGR_WFS_BUEK200

    def query_soil_at_point(
        self, x: float, y: float, source_epsg: int = 25832, buffer_m: float = 100.0
    ) -> dict:
        """Liefert Bodendaten für UTM/WGS-Punkt.

        Returns dict {success, soil_type, soil_code, description, source, error?}.
        """
        try:
            lon, lat = self._to_wgs84(x, y, source_epsg)
        except Exception as e:
            return {"success": False, "error": f"Koordinatentransformation fehlgeschlagen: {e}"}

        try:
            features = self._wfs_get_feature(lon, lat, buffer_m)
        except BGREndpointUnavailable as e:
            return {"success": False, "error": str(e), "endpoint_unavailable": True}
        except Exception as e:
            return {"success": False, "error": f"BGR-API-Fehler: {e}"}

        if not features:
            return {"success": False, "error": "Keine Bodendaten an diesem Standort verfügbar"}

        feat = features[0]
        return self._parse_feature(feat) | {"success": True}

    @staticmethod
    def _to_wgs84(x: float, y: float, source_epsg: int) -> tuple[float, float]:
        if source_epsg == 4326:
            return x, y
        t = Transformer.from_crs(f"EPSG:{source_epsg}", "EPSG:4326", always_xy=True)
        return t.transform(x, y)

    def _wfs_get_feature(self, lon: float, lat: float, buffer_m: float) -> list[dict]:
        buffer_deg = buffer_m / 111000.0
        bbox = (lon - buffer_deg, lat - buffer_deg, lon + buffer_deg, lat + buffer_deg)
        params = {
            "SERVICE": "WFS",
            "VERSION": self.WFS_VERSION,
            "REQUEST": "GetFeature",
            "TYPENAMES": "boden_buek200_v_geom",
            "OUTPUTFORMAT": "application/json",
            "BBOX": ",".join(f"{v}" for v in bbox) + ",urn:ogc:def:crs:EPSG::4326",
            "COUNT": "5",
        }
        resp = requests.get(self.endpoint, params=params, timeout=self.timeout)
        if resp.status_code == 404:
            raise BGREndpointUnavailable(
                f"BGR-WFS-Endpoint nicht erreichbar (HTTP 404) — Service ggf. eingestellt: {self.endpoint}"
            )
        resp.raise_for_status()
        data = resp.json()
        return data.get("features", [])

    @staticmethod
    def _parse_feature(feature: dict) -> dict:
        props = feature.get("properties", {})
        # Heuristisches Auslesen der Bodenart-Felder
        soil_code = (
            props.get("LEG_NR")
            or props.get("BODENART")
            or props.get("legend_code")
            or ""
        )
        description = (
            props.get("LEG_TXT")
            or props.get("BESCHREIBUNG")
            or props.get("description")
            or ""
        )
        soil_type = BGR_SOIL_TYPE_MAPPING.get(str(soil_code)[:2], "Unbekannt")
        return {
            "soil_type": soil_type,
            "soil_code": str(soil_code),
            "description": str(description),
            "source": "BGR BÜK200",
            "raw_data": props,
        }
