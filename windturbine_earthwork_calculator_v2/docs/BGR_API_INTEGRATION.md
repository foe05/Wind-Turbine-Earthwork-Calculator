# BGR WFS-API Integration

Dokumentation der Integration mit der Bundesanstalt für Geowissenschaften und Rohstoffe (BGR) WFS-Service.

## Übersicht

Die BGR stellt Bodendaten für Deutschland über Web Feature Services (WFS) zur Verfügung. Diese Integration ermöglicht die automatische Abfrage von Bodenarten basierend auf Standortkoordinaten.

## Verfügbare Dienste

### BÜK200 (Hauptquelle)
**Bodenübersichtskarte 1:200.000**
- **URL**: `https://services.bgr.de/wfs/boden/buek200`
- **Maßstab**: 1:200.000
- **Genauigkeit**: Übersichtskarte (nicht standortgenau!)
- **Abdeckung**: Gesamtes Deutschland
- **Aktualisierung**: Regelmäßig

### BÜK1000 (Alternative)
**Bodenübersichtskarte 1:1.000.000**
- **URL**: `https://services.bgr.de/wfs/boden/buek1000`
- **Maßstab**: 1:1.000.000
- **Genauigkeit**: Grobe Übersicht
- **Verwendung**: Großräumige Analysen

### HÜK200 (Ergänzend)
**Hydrogeologische Übersichtskarte 1:200.000**
- **URL**: `https://services.bgr.de/wfs/grundwasser/huek200`
- **Inhalt**: Grundwasserdaten, geologische Einheiten
- **Verwendung**: Zusatzinformationen

## Verwendung

### In Python

```python
from qgis.core import QgsPointXY, QgsCoordinateReferenceSystem
from core.bgr_soil_api import get_soil_data_from_bgr

# Koordinaten (z.B. UTM Zone 32N)
point = QgsPointXY(500000, 5800000)
crs = QgsCoordinateReferenceSystem("EPSG:25832")

# Abfrage
result = get_soil_data_from_bgr(point, crs, buffer_m=100.0)

if result['success']:
    print(f"Bodenart: {result['soil_type']}")
    print(f"BGR-Code: {result['soil_code']}")
    print(f"Beschreibung: {result['description']}")
```

### In QGIS Plugin GUI

1. DXF-Datei im Tab "Eingabe" auswählen
2. Wechsel zum Tab "Bodenstabilisierung"
3. Button "Bodendaten von BGR abrufen" klicken
4. Bodenart wird automatisch gesetzt

## BGR-Bodenart-Codes

### Mapping zu Standardkategorien

| BGR-Code | Bedeutung | Kategorie |
|----------|-----------|-----------|
| TT, LT, TL, Tu | Tone | **Ton** |
| UU, UT, UL, Us | Schluffe | **Schluff** |
| LL, LU, Lu, Ls | Lehme | **Lehm** |
| SS, SU, SL, St, Su | Sande | **Sand** |
| GG, GS, Gu | Kiese | **Kies** |
| HH, HN | Moore | **Torf** |

### Code-Struktur

BGR verwendet **2-stellige Codes**:
- **1. Buchstabe**: Hauptkomponente (T=Ton, U=Schluff, L=Lehm, S=Sand, G=Kies)
- **2. Buchstabe**: Nebenkomponente oder Konsistenz

**Beispiele:**
- `LU` = Lehm mit Schluff
- `Su` = Sand mit Schluff
- `TL` = Ton mit Lehm

## Technische Details

### WFS-Request-Beispiel

```http
GET https://services.bgr.de/wfs/boden/buek200?
    SERVICE=WFS&
    VERSION=2.0.0&
    REQUEST=GetFeature&
    TYPENAME=boden:buek200&
    BBOX=13.3,52.4,13.5,52.6,EPSG:4326&
    OUTPUTFORMAT=application/json&
    SRSNAME=EPSG:4326
```

### Response-Struktur (GeoJSON)

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { ... },
      "properties": {
        "BOART": "LU",
        "LEGENDE": "Lehm über Schluff",
        "BESCHREIB": "Braune Böden aus Geschiebelehm..."
      }
    }
  ]
}
```

### Koordinaten-Transformation

Das System unterstützt automatische Transformation zwischen verschiedenen CRS:
- **Input**: Beliebiges CRS (z.B. EPSG:25832 - UTM Zone 32N)
- **WFS-Abfrage**: Transformation nach EPSG:4326 (WGS84)
- **Puffer**: In Metern (wird in Grad umgerechnet)

## Einschränkungen

### Räumliche Abdeckung
- ✅ Deutschland (flächendeckend)
- ❌ Außerhalb Deutschlands (keine Daten)

### Genauigkeit
- **Maßstab**: 1:200.000 (Übersichtskarte!)
- **Nicht geeignet für**: Exakte Standortbestimmung
- **Verwendung**: Vordimensionierung, erste Einschätzung
- **Erforderlich**: Standortspezifische Eignungsprüfung vor Ort

### Service-Verfügbarkeit
- **Uptime**: Normalerweise hoch, aber keine Garantie
- **Timeout**: 10 Sekunden
- **Fallback**: Manuelle Eingabe bei Ausfall

### Datenqualität
- **Quelle**: Offiziell (BGR)
- **Verlässlichkeit**: Hoch für Übersichtszwecke
- **Aktualisierung**: Nicht in Echtzeit
- **Variabilität**: Lokale Bodenverhältnisse können abweichen

## Fehlerbehandlung

### Typische Fehler und Lösungen

| Fehler | Ursache | Lösung |
|--------|---------|--------|
| `Keine Internet-Verbindung` | Offline | Internet-Verbindung prüfen |
| `Koordinaten außerhalb BGR-Bereich` | Ausland | Manuelle Eingabe verwenden |
| `WFS-Service nicht erreichbar` | BGR-Server down | Später erneut versuchen |
| `Keine Geometrie in DXF` | Leere/fehlerhafte DXF | DXF-Datei prüfen |
| `Parse-Fehler` | Unerwartete Response | BGR-Service-Status prüfen |

### Logging

Alle API-Aufrufe werden geloggt:
```python
from ..utils.logging_utils import get_plugin_logger

logger = get_plugin_logger()
# Log-Einträge in QGIS Message Log verfügbar
```

## Best Practices

### 1. Vorbereitung
- ✅ DXF-Datei vorher validieren
- ✅ Koordinaten im richtigen CRS
- ✅ Internet-Verbindung testen

### 2. Verwendung
- ✅ Puffer anpassen (Standard: 100m)
- ✅ Ergebnis visuell prüfen
- ✅ Mit Vor-Ort-Erkenntnissen vergleichen

### 3. Interpretation
- ⚠️ BGR-Daten sind Richtwerte
- ⚠️ Lokale Variabilität beachten
- ⚠️ Bodengutachten nicht ersetzen
- ✅ Für erste Kostenschätzung verwenden

## API-Limits

Die BGR-WFS-Services haben keine dokumentierten Rate-Limits, aber:
- **Fair Use**: Keine exzessiven Anfragen
- **Batch-Abfragen**: Vermeiden (manuell throtteln)
- **Caching**: Sinnvoll bei wiederholten Abfragen

## Weiterführende Ressourcen

### BGR-Dokumentation
- **Produktkatalog**: https://www.bgr.bund.de/DE/Themen/Boden/Produkte/produkte_node.html
- **WFS-Services**: https://services.bgr.de/wfs/
- **Metadaten**: https://www.bgr.bund.de/DE/Themen/Boden/Informationsgrundlagen/Bodenkundliche_Karten_Datenbanken/BUEK200/buek200_node.html

### Standards
- **OGC WFS 2.0**: https://www.ogc.org/standards/wfs
- **GeoJSON**: https://geojson.org/

### Support
- **BGR-Kontakt**: geoportal@bgr.de
- **Plugin-Issues**: GitHub Repository

## Lizenz

BGR-Daten unterliegen der **Datenlizenz Deutschland – Namensnennung – Version 2.0**

**Namensnennung erforderlich:**
> "Datenquelle: © Bundesanstalt für Geowissenschaften und Rohstoffe (BGR), Hannover, [Jahr]"

**Nutzungsbedingungen**: https://www.govdata.de/dl-de/by-2-0

## Changelog

### Version 2.0 (2025-11)
- ✨ Initiale BGR WFS-API Integration
- ✨ BÜK200 Hauptdatenquelle
- ✨ Automatische Koordinatentransformation
- ✨ GUI-Integration mit Auto-Fill
- ✨ Umfassende Fehlerbehandlung
- ✨ Test-Suite mit 5 Testfällen

### Geplante Erweiterungen
- 🔄 BÜK1000 als Fallback
- 🔄 Caching von Abfrageergebnissen
- 🔄 Batch-Abfragen für mehrere Standorte
- 🔄 HÜK200 Integration (Grundwasserdaten)
- 🔄 Visualisierung der BGR-Geometrien auf Karte
