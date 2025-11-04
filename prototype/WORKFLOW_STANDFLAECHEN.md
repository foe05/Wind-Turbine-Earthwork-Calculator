# Workflow: Standflächen-basierte WKA-Planung

**Hinweis**: Dieser Workflow gilt unverändert für v6.0. Die neuen Features (API-Integration, Caching, GeoPackage-Output) ergänzen diesen Workflow, ändern ihn aber nicht.

## Übersicht

Der Wind Turbine Earthwork Calculator unterstützt einen **2-Schritt-Workflow** für die präzise Platzierung von Windkraftanlagen-Standflächen:

1. **Schritt 1**: Automatische Generierung von Standflächen-Polygonen basierend auf Punkt-Koordinaten
2. **Schritt 2**: Manuelle Anpassung der Polygone und Neuberechnung (geplant für v4.0)

---

## Schritt 1: Standflächen generieren

### Vorbereitung

1. **Input-Daten**:
   - Punktlayer mit WKA-Standorten (z.B. `wka_standorte.shp`)
   - Digitales Geländemodell (DEM)

2. **Tool-Parameter einstellen**:
   - Plattformlänge (z.B. 45m)
   - Plattformbreite (z.B. 40m)
   - Fundament-Parameter
   - Kosten-Parameter

3. **Outputs konfigurieren**:
   ```
   ✓ Volumendaten → wka_volumendaten.gpkg
   ✓ Standflächen (Polygone) → wka_standflaechen.gpkg  ← WICHTIG!
   ✓ HTML-Report → report.html
   ```

### Ergebnis

Nach dem ersten Lauf erhalten Sie:

- **Punkt-Layer** (`wka_volumendaten.gpkg`): Enthält alle Berechnungsergebnisse (Volumen, Kosten)
- **Polygon-Layer** (`wka_standflaechen.gpkg`): Rechtecke, Nord-Süd ausgerichtet, zentriert auf WKA-Punkte
- **HTML-Report**: Detaillierte Zusammenfassung

---

## Schritt 2: Standflächen anpassen (Manuell in QGIS)

### Geometrie bearbeiten

1. **Layer laden**: `wka_standflaechen.gpkg` in QGIS öffnen

2. **Bearbeitungsmodus aktivieren**:
   - Rechtsklick auf Layer → Toggle Editing (Bleistift-Icon)

3. **Polygone anpassen**:
   
   **a) Rotation (wichtigste Anpassung)**:
   - Werkzeug: `Vertex Tool` oder `Rotate Feature(s)`
   - Rechteck um den WKA-Punkt rotieren
   - An Geländegegebenheiten anpassen (z.B. Höhenlinien folgen)
   
   **b) Verschiebung**:
   - Werkzeug: `Move Feature(s)`
   - Polygon verschieben (falls Optimierung nötig)
   
   **c) Größe ändern** (optional):
   - Werkzeug: `Vertex Tool`
   - Einzelne Eckpunkte verschieben
   - **Achtung**: Attribut `area` wird NICHT automatisch aktualisiert!

4. **Speichern**: Toggle Editing → Save

### Attribute aktualisieren (bei Größenänderung)

Falls Sie die Polygon-Größe manuell geändert haben:

```sql
-- In QGIS Field Calculator:
-- Neues Feld oder bestehendes Feld 'area' aktualisieren
$area
```

Oder in Python-Konsole:

```python
layer = iface.activeLayer()
layer.startEditing()
for feature in layer.getFeatures():
    feature['area'] = feature.geometry().area()
    layer.updateFeature(feature)
layer.commitChanges()
```

---

## Schritt 3: Neuberechnung mit angepassten Polygonen (v4.0)

> ⚠️ **Hinweis**: Diese Funktion ist für Version 4.0 geplant und noch nicht implementiert.

### Geplante Funktionalität (v4.0)

In zukünftigen Versionen wird das Tool einen **Polygon-Input-Modus** unterstützen:

```
NEUER PARAMETER (v4.0):
[ ] Modus: Punkte verwenden
[✓] Modus: Polygone verwenden
    └─ Input-Polygone: [wka_standflaechen_angepasst.gpkg]
```

**Workflow**:
1. Angepasste Polygone als Input
2. Tool extrahiert:
   - Zentroid → WKA-Standort
   - Bounding Box → Plattformmaße
   - Rotation → Ausrichtung für DEM-Sampling
3. Neuberechnung der Volumen und Kosten

---

## Best Practices

### ✅ Empfohlene Vorgehensweise

1. **Erste Iteration**:
   - Standard-Parameter verwenden
   - Polygone automatisch generieren
   - Report prüfen

2. **Optimierung**:
   - Polygone in QGIS rotieren/verschieben
   - An Topographie anpassen
   - Konflikte mit anderen Features vermeiden (Gebäude, Straßen, etc.)

3. **Finale Berechnung**:
   - Mit v4.0: Neuberechnung mit angepassten Polygonen
   - Bis dahin: Manuelle Geometrie-Anpassung dokumentieren

### ⚠️ Bekannte Einschränkungen (v3.0)

- **Nur Nord-Süd-Ausrichtung**: Erstmalig generierte Polygone sind immer NS/EW ausgerichtet
- **Keine Rückberechnung**: Angepasste Polygone können noch nicht als Input verwendet werden
- **Area-Attribut**: Wird bei manueller Größenänderung nicht automatisch aktualisiert

---

## Tipps für manuelle Anpassung

### 1. Rotation basierend auf Höhenlinien

```
Ziel: Plattform so ausrichten, dass minimaler Cut/Fill entsteht
→ Längsachse parallel zu Höhenlinien = weniger Aushub
```

**Workflow**:
1. Höhenlinien-Layer einblenden
2. Standfläche parallel zu Höhenlinie drehen
3. Visual check: Plattform sollte "flach" im Gelände liegen

### 2. Rotation basierend auf Slope-Raster

```
Verwendung: QGIS Raster → Analysis → Slope
```

**Workflow**:
1. Slope-Raster aus DEM erstellen
2. Plattform so ausrichten, dass sie über Bereiche mit minimaler Neigung liegt
3. Visual check mit Transparenz-Overlay

### 3. Konflikte vermeiden

**Checkliste**:
- [ ] Mindestabstand zu Gebäuden: ___ m
- [ ] Mindestabstand zu Straßen: ___ m
- [ ] Mindestabstand zu Grundstücksgrenzen: ___ m
- [ ] Keine Überschneidung mit Schutzgebieten
- [ ] Zufahrt gewährleistet

---

## Technische Details

### Polygon-Struktur

**Koordinaten-Reihenfolge** (gegen Uhrzeigersinn):
```
    NW ----------- NE
    |               |
    |      WKA      |   ← Zentrum = WKA-Punkt
    |               |
    SW ----------- SE

X-Achse = Ost-West (Breite)
Y-Achse = Nord-Süd (Länge)
```

**Attribut-Schema**:
```
id           : Integer    - WKA-Nummer
length       : Double     - Plattformlänge (m)
width        : Double     - Plattformbreite (m)
area         : Double     - Fläche (m²)
cost_total   : Double     - Gesamtkosten (€)
found_vol    : Double     - Fundament-Volumen (m³)
total_cut    : Double     - Gesamt-Aushub (m³)
total_fill   : Double     - Gesamt-Auftrag (m³)
```

### QGIS-Python-Snippet: Rotation um WKA-Punkt

```python
from qgis.core import QgsGeometry, QgsPointXY
import math

def rotate_platform(feature, angle_degrees):
    """
    Rotiert Polygon um sein Zentroid
    
    Args:
        feature: QgsFeature mit Polygon-Geometrie
        angle_degrees: Rotationswinkel in Grad (positiv = gegen Uhrzeigersinn)
    """
    geom = feature.geometry()
    centroid = geom.centroid().asPoint()
    
    # Rotation in QGIS (in Radiant)
    angle_rad = math.radians(angle_degrees)
    
    # Geometrie rotieren
    rotated = geom.rotate(angle_degrees, centroid)
    
    return rotated

# Anwendung:
layer = iface.activeLayer()
layer.startEditing()
for feature in layer.getFeatures():
    # 45° gegen Uhrzeigersinn rotieren
    rotated_geom = rotate_platform(feature, 45)
    feature.setGeometry(rotated_geom)
    layer.updateFeature(feature)
layer.commitChanges()
```

---

## Roadmap v4.0

### Geplante Features

1. **Polygon-Input-Modus**:
   ```python
   self.addParameter(QgsProcessingParameterFeatureSource(
       'INPUT_POLYGONS', 'WKA-Standflächen (Polygone)',
       [QgsProcessing.TypeVectorPolygon], optional=True))
   ```

2. **Auto-Rotation-Optimierung**:
   - Algorithmus testet verschiedene Rotationswinkel (0°, 15°, 30°, ..., 345°)
   - Wählt Rotation mit minimalem Cut/Fill-Volume
   - User kann manuell überschreiben

3. **Constraint-basierte Platzierung**:
   - Buffer um Gebäude/Straßen
   - Automatische Vermeidung von Konflikten
   - Snap to grid/slope-optimierte Platzierung

4. **Batch-Optimierung**:
   - Mehrere Standorte gleichzeitig optimieren
   - Minimierung von Material-Transport zwischen Standorten
   - Kostenfunktion über gesamten Windpark

---

## Support & Weiterentwicklung

**Feedback & Feature Requests**: Bitte Issues auf GitHub erstellen

**Aktuelle Version**: v3.0  
**Nächste Version**: v4.0 (Q2 2025) - mit Polygon-Input-Support

---

**Autor**: Windkraft-Standortplanung  
**Lizenz**: Siehe LICENSE  
**Datum**: Oktober 2025
