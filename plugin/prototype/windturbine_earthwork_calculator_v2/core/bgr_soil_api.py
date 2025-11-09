"""
BGR Soil Data API Integration

Fragt Bodendaten von der Bundesanstalt für Geowissenschaften und Rohstoffe (BGR) ab.

Verfügbare WFS-Services:
- Bodenübersichtskarte 1:1.000.000 (BÜK1000)
- Bodenübersichtskarte 1:200.000 (BÜK200)
- Hydrogeologische Übersichtskarte 1:200.000 (HÜK200)

Author: Wind Energy Site Planning
Version: 2.0
"""

from typing import Dict, Optional, List, Tuple
import json
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from qgis.core import (
    QgsPointXY,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject
)

from ..utils.logging_utils import get_plugin_logger


class BGRSoilAPI:
    """
    API-Client für BGR WFS-Services.

    Ermöglicht Abfrage von Bodendaten basierend auf Koordinaten.
    """

    # BGR WFS Base URL
    BGR_WFS_BASE = "https://services.bgr.de/wfs/boden/buek200"

    # Alternative Services
    BGR_WFS_BUEK1000 = "https://services.bgr.de/wfs/boden/buek1000"
    BGR_WFS_HUEK200 = "https://services.bgr.de/wfs/grundwasser/huek200"

    # Standard-Parameter für WFS GetFeature Request
    WFS_VERSION = "2.0.0"

    # Bodenarten-Mapping von BGR-Codes zu unseren Kategorien
    BGR_SOIL_TYPE_MAPPING = {
        # Tone
        'TT': 'Ton',
        'LT': 'Ton',
        'TL': 'Ton',
        'Tu': 'Ton',

        # Schluffe
        'UU': 'Schluff',
        'UT': 'Schluff',
        'UL': 'Schluff',
        'Us': 'Schluff',

        # Lehme
        'LL': 'Lehm',
        'LU': 'Lehm',
        'Lu': 'Lehm',
        'Ls': 'Lehm',

        # Sande
        'SS': 'Sand',
        'SU': 'Sand',
        'SL': 'Sand',
        'St': 'Sand',
        'Su': 'Sand',

        # Kiese
        'GG': 'Kies',
        'GS': 'Kies',
        'Gu': 'Kies',

        # Sonderfälle
        'HH': 'Torf',  # Hochmoor
        'HN': 'Torf',  # Niedermoor
    }

    def __init__(self, timeout: int = 10):
        """
        Initialisiert BGR API Client.

        Args:
            timeout: Timeout für HTTP-Requests in Sekunden
        """
        self.logger = get_plugin_logger()
        self.timeout = timeout
        self.logger.info("BGR Soil API Client initialisiert")

    def query_soil_at_point(
        self,
        point: QgsPointXY,
        crs: QgsCoordinateReferenceSystem,
        buffer_m: float = 100.0
    ) -> Dict:
        """
        Fragt Bodendaten für einen Punkt ab.

        Args:
            point: Koordinaten des Abfragepunkts
            crs: Koordinatenreferenzsystem des Punktes
            buffer_m: Puffer-Radius um den Punkt in Metern

        Returns:
            Dict mit:
                - success: Bool ob Abfrage erfolgreich
                - soil_type: Bodenart (vereinfacht)
                - soil_code: BGR Bodenart-Code
                - description: Bodenbeschreibung
                - source: Datenquelle
                - legend: Legendenbezeichnung
                - raw_data: Vollständige Rohdaten
                - error: Fehlermeldung (falls success=False)
        """
        try:
            self.logger.info(f"BGR-Abfrage für Punkt: {point.x():.2f}, {point.y():.2f}")

            # Transformiere zu EPSG:4326 (WGS84) für WFS-Abfrage
            point_wgs84 = self._transform_to_wgs84(point, crs)

            if not point_wgs84:
                return {
                    'success': False,
                    'error': 'Koordinatentransformation fehlgeschlagen'
                }

            # Erstelle WFS GetFeature Request
            features = self._wfs_get_feature_at_point(
                point_wgs84,
                buffer_m=buffer_m
            )

            if not features:
                self.logger.warning("Keine Bodendaten von BGR gefunden")
                return {
                    'success': False,
                    'error': 'Keine Bodendaten an diesem Standort verfügbar'
                }

            # Parse erste Feature (nächstes zum Punkt)
            feature = features[0]
            result = self._parse_soil_feature(feature)
            result['success'] = True

            self.logger.info(
                f"BGR-Daten erfolgreich abgerufen: {result.get('soil_type', 'Unbekannt')}"
            )

            return result

        except Exception as e:
            self.logger.error(f"BGR-Abfrage fehlgeschlagen: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'API-Fehler: {str(e)}'
            }

    def _transform_to_wgs84(
        self,
        point: QgsPointXY,
        source_crs: QgsCoordinateReferenceSystem
    ) -> Optional[QgsPointXY]:
        """
        Transformiert Punkt zu WGS84 (EPSG:4326).

        Args:
            point: Punkt in Quell-CRS
            source_crs: Quell-Koordinatenreferenzsystem

        Returns:
            Punkt in WGS84 oder None bei Fehler
        """
        try:
            target_crs = QgsCoordinateReferenceSystem("EPSG:4326")

            # Wenn bereits WGS84, direkt zurückgeben
            if source_crs.authid() == "EPSG:4326":
                return point

            # Transformation
            transform = QgsCoordinateTransform(
                source_crs,
                target_crs,
                QgsProject.instance()
            )

            transformed_point = transform.transform(point)

            self.logger.debug(
                f"Koordinaten transformiert: "
                f"{source_crs.authid()} → WGS84: "
                f"{transformed_point.x():.6f}, {transformed_point.y():.6f}"
            )

            return transformed_point

        except Exception as e:
            self.logger.error(f"Koordinatentransformation fehlgeschlagen: {e}")
            return None

    def _wfs_get_feature_at_point(
        self,
        point: QgsPointXY,
        buffer_m: float = 100.0
    ) -> List[Dict]:
        """
        Führt WFS GetFeature Request für Punkt aus.

        Args:
            point: Punkt in WGS84
            buffer_m: Puffer in Metern

        Returns:
            Liste von Features als Dictionaries
        """
        try:
            # Konvertiere Buffer von Meter zu Grad (grobe Approximation)
            # 1 Grad ≈ 111 km am Äquator
            buffer_deg = buffer_m / 111000.0

            # Bounding Box um Punkt
            bbox = (
                point.x() - buffer_deg,
                point.y() - buffer_deg,
                point.x() + buffer_deg,
                point.y() + buffer_deg
            )

            # WFS GetFeature Parameter
            params = {
                'SERVICE': 'WFS',
                'VERSION': self.WFS_VERSION,
                'REQUEST': 'GetFeature',
                'TYPENAME': 'boden:buek200',  # Layer-Name
                'BBOX': f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]},EPSG:4326",
                'OUTPUTFORMAT': 'application/json',
                'SRSNAME': 'EPSG:4326'
            }

            # Erstelle URL
            url = f"{self.BGR_WFS_BASE}?{urlencode(params)}"

            self.logger.debug(f"WFS Request URL: {url}")

            # HTTP Request
            request = Request(url)
            request.add_header('User-Agent', 'QGIS Wind Turbine Calculator/2.0')

            with urlopen(request, timeout=self.timeout) as response:
                data = response.read()
                content = json.loads(data.decode('utf-8'))

            # Parse GeoJSON Response
            if 'features' not in content:
                self.logger.warning("Keine Features in WFS-Response")
                return []

            features = content['features']
            self.logger.info(f"WFS-Response: {len(features)} Features gefunden")

            return features

        except HTTPError as e:
            self.logger.error(f"HTTP Error bei WFS-Request: {e.code} - {e.reason}")
            return []
        except URLError as e:
            self.logger.error(f"URL Error bei WFS-Request: {e.reason}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON Parse Error: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unerwarteter Fehler bei WFS-Request: {e}", exc_info=True)
            return []

    def _parse_soil_feature(self, feature: Dict) -> Dict:
        """
        Parsed ein GeoJSON Feature zu Bodendaten.

        Args:
            feature: GeoJSON Feature Dictionary

        Returns:
            Dict mit extrahierten Bodendaten
        """
        try:
            properties = feature.get('properties', {})

            # Extrahiere relevante Felder (abhängig von BÜK200 Schema)
            # HINWEIS: Feldnamen müssen ggf. an tatsächliches Schema angepasst werden
            soil_code = properties.get('BOART', properties.get('Bodenart', ''))
            legend = properties.get('LEGENDE', properties.get('Legend', ''))
            description = properties.get('BESCHREIB', properties.get('Description', ''))

            # Mappe BGR-Code zu unserer Kategorie
            soil_type = self._map_soil_code(soil_code)

            result = {
                'soil_type': soil_type,
                'soil_code': soil_code,
                'description': description or 'Keine Beschreibung verfügbar',
                'legend': legend,
                'source': 'BGR BÜK200 (WFS)',
                'raw_data': properties
            }

            self.logger.debug(f"Feature geparst: {soil_code} → {soil_type}")

            return result

        except Exception as e:
            self.logger.error(f"Fehler beim Parsen des Features: {e}")
            return {
                'soil_type': None,
                'soil_code': None,
                'description': 'Parse-Fehler',
                'legend': '',
                'source': 'BGR BÜK200 (Fehler)',
                'raw_data': {}
            }

    def _map_soil_code(self, soil_code: str) -> Optional[str]:
        """
        Mappt BGR Bodenart-Code zu vereinfachter Kategorie.

        Args:
            soil_code: BGR Bodenart-Code (z.B. 'LU', 'SS')

        Returns:
            Vereinfachte Bodenart oder None
        """
        if not soil_code:
            return None

        # Exakte Übereinstimmung
        if soil_code in self.BGR_SOIL_TYPE_MAPPING:
            return self.BGR_SOIL_TYPE_MAPPING[soil_code]

        # Versuche partielle Übereinstimmung (erste 2 Zeichen)
        code_prefix = soil_code[:2].upper()
        if code_prefix in self.BGR_SOIL_TYPE_MAPPING:
            return self.BGR_SOIL_TYPE_MAPPING[code_prefix]

        # Fallback: Analysiere nach Hauptkomponente
        if 'T' in soil_code.upper():
            return 'Ton'
        elif 'U' in soil_code.upper():
            return 'Schluff'
        elif 'L' in soil_code.upper():
            return 'Lehm'
        elif 'S' in soil_code.upper():
            return 'Sand'
        elif 'G' in soil_code.upper():
            return 'Kies'

        self.logger.warning(f"Unbekannter BGR Bodenart-Code: {soil_code}")
        return None

    def test_connection(self) -> Dict:
        """
        Testet Verbindung zum BGR WFS-Service.

        Returns:
            Dict mit Test-Ergebnis
        """
        try:
            # GetCapabilities Request
            params = {
                'SERVICE': 'WFS',
                'REQUEST': 'GetCapabilities',
                'VERSION': self.WFS_VERSION
            }

            url = f"{self.BGR_WFS_BASE}?{urlencode(params)}"

            request = Request(url)
            request.add_header('User-Agent', 'QGIS Wind Turbine Calculator/2.0')

            with urlopen(request, timeout=self.timeout) as response:
                status_code = response.getcode()

            return {
                'success': status_code == 200,
                'status_code': status_code,
                'message': 'BGR WFS-Service erreichbar' if status_code == 200 else f'HTTP {status_code}'
            }

        except Exception as e:
            return {
                'success': False,
                'status_code': None,
                'message': f'Verbindung fehlgeschlagen: {str(e)}'
            }


def get_soil_data_from_bgr(
    coordinates: QgsPointXY,
    crs: QgsCoordinateReferenceSystem,
    buffer_m: float = 100.0
) -> Dict:
    """
    Convenience-Funktion für BGR-Bodendaten-Abfrage.

    Args:
        coordinates: Koordinaten des Standorts
        crs: Koordinatenreferenzsystem
        buffer_m: Puffer-Radius in Metern

    Returns:
        Dict mit Bodendaten (siehe BGRSoilAPI.query_soil_at_point)

    Example:
        >>> from qgis.core import QgsPointXY, QgsCoordinateReferenceSystem
        >>> point = QgsPointXY(32500000, 5900000)
        >>> crs = QgsCoordinateReferenceSystem("EPSG:25832")
        >>> result = get_soil_data_from_bgr(point, crs)
        >>> if result['success']:
        ...     print(f"Bodenart: {result['soil_type']}")
    """
    api = BGRSoilAPI()
    return api.query_soil_at_point(coordinates, crs, buffer_m)
