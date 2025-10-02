# 🚀 SCHRITT-FÜR-SCHRITT ANLEITUNG
## Wind Turbine Earthwork Calculator - Prototyp Installation

---

## ✅ VORAUSSETZUNGEN

Was Sie brauchen:
- ✓ QGIS installiert (Version 3.x)
- ✓ Internet-Verbindung
- ✓ Etwa 30 Minuten Zeit

---

## 📁 SCHRITT 1: ORDNERSTRUKTUR ERSTELLEN

### 1.1 Erstellen Sie folgende Ordner auf Ihrem Computer:

**Windows:**
```
C:\GIS_Daten\Windkraft\
  ├── DEM\
  ├── Standorte\
  ├── Scripts\
  └── Ergebnisse\
```

**So geht's:**
1. Windows Explorer öffnen
2. Zu `C:\` navigieren (oder einen anderen Ort Ihrer Wahl)
3. Rechtsklick → "Neu" → "Ordner"
4. Namen eingeben: `GIS_Daten`
5. Darin weitere Unterordner wie oben erstellen

---

## 📥 SCHRITT 2: TESTDATEN HERUNTERLADEN

### Option A: Künstliche Testdaten (SCHNELLSTART - EMPFOHLEN)

Ich erstelle Ihnen gleich ein Python-Skript, das Test-DEM-Daten für Sie generiert!

### Option B: Echte DGM1-Daten (für Ihre Region)

#### Für Hessen (Zierenberg):

**2.1** Browser öffnen → https://gds.hessen.de/

**2.2** Navigation:
- Klicken Sie auf **"Downloadcenter"**
- Dann: **"3D-Geobasisdaten"** → **"DGM1"**

**2.3** Gebiet auswählen:
- Suchen Sie nach "Zierenberg" oder Ihrer gewünschten Region
- Wählen Sie die Kacheln aus (ca. 2km x 2km pro Kachel)
- Format: **GeoTIFF (*.tif)** auswählen

**2.4** Download:
- Datei herunterladen (kann einige Minuten dauern)
- Speichern unter: `C:\GIS_Daten\Windkraft\DEM\dgm1_hessen.tif`

#### Alternative Quellen:

**NRW:** https://www.opengeodata.nrw.de/produkte/geobasis/hm/dgm1_xyz/
**Niedersachsen:** https://www.lgln.niedersachsen.de/
**Bayern:** https://geodatenonline.bayern.de/

---

## 💾 SCHRITT 3: SCRIPT SPEICHERN

**3.1** Den Python-Code kopieren:
- Öffnen Sie das Artifact "Wind Turbine Earthwork Calculator - QGIS Processing Script" (oben)
- Markieren Sie den **gesamten Code** (Strg+A)
- Kopieren Sie ihn (Strg+C)

**3.2** Code in Datei speichern:
1. Öffnen Sie einen Texteditor (Notepad, Notepad++, oder ähnlich)
2. Fügen Sie den Code ein (Strg+V)
3. Speichern unter:
   - Speicherort: `C:\GIS_Daten\Windkraft\Scripts\`
   - Dateiname: `wind_earthwork_calculator.py`
   - **WICHTIG:** Dateityp: "Alle Dateien (*.*)" auswählen
   - **NICHT** als .txt speichern!

**3.3** Überprüfung:
- Die Datei muss heißen: `wind_earthwork_calculator.py`
- Dateigröße sollte ca. 20-25 KB sein

---

## 🔧 SCHRITT 4: TEST-DEM ERSTELLEN (OPTIONAL, ABER EMPFOHLEN)

Wenn Sie noch keine echten DEM-Daten haben, erstellen wir jetzt welche:

**4.1** QGIS öffnen

**4.2** Python Console öffnen:
- Menü: `Plugins` → `Python-Konsole`
- Oder Tastenkombination: `Strg+Alt+P`

**4.3** Folgenden Code in die Console eingeben und ausführen:

```python
import numpy as np
from osgeo import gdal, osr
import os

# Pfad anpassen!
output_path = r'C:\GIS_Daten\Windkraft\DEM\test_dem.tif'

# Test-DEM erstellen (500m x 500m, 1m Auflösung)
width = 500
height = 500
xmin, ymin = 500000, 5700000  # UTM32N Koordinaten

# Künstliches Gelände mit Hügel
x = np.linspace(0, 1, width)
y = np.linspace(0, 1, height)
X, Y = np.meshgrid(x, y)

# Wellenförmiges Gelände mit Neigung
dem_data = (
    300 +  # Basis-Höhe
    20 * np.sin(X * 4 * np.pi) +  # Wellen in X
    15 * np.sin(Y * 3 * np.pi) +  # Wellen in Y
    10 * X +  # Leichte Neigung
    5 * np.random.random((height, width))  # Rauschen
)

# GeoTIFF schreiben
driver = gdal.GetDriverByName('GTiff')
dataset = driver.Create(output_path, width, height, 1, gdal.GDT_Float32)

# Geo-Transformation setzen (1m Pixel-Größe)
geotransform = (xmin, 1, 0, ymin + height, 0, -1)
dataset.SetGeoTransform(geotransform)

# Koordinatensystem (UTM32N)
srs = osr.SpatialReference()
srs.ImportFromEPSG(25832)
dataset.SetProjection(srs.ExportToWkt())

# Daten schreiben
band = dataset.GetRasterBand(1)
band.WriteArray(dem_data)
band.SetNoDataValue(-9999)

dataset = None
print(f"✓ Test-DEM erstellt: {output_path}")
```

**4.4** Code ausführen:
- Drücken Sie `Enter` nach jeder Zeile ODER
- Kopieren Sie den gesamten Block und drücken Sie `Enter`

**4.5** Ergebnis:
- Sie sollten sehen: `✓ Test-DEM erstellt: C:\GIS_Daten\Windkraft\DEM\test_dem.tif`

---

## 📍 SCHRITT 5: TEST-STANDORTE ERSTELLEN

**5.1** In QGIS: Menü → `Layer` → `Layer erstellen` → `Neuer Shapefile-Layer`

**5.2** Einstellungen im Dialog:
- **Dateiname:** `C:\GIS_Daten\Windkraft\Standorte\wka_test.shp`
- **Geometrie-Typ:** `Punkt`
- **KBS (CRS):** `EPSG:25832 - ETRS89 / UTM zone 32N`
- Klicken Sie `OK`

**5.3** Layer in Bearbeitungsmodus versetzen:
- Rechtsklick auf `wka_test` im Layer-Panel
- Wählen Sie `Bearbeitung umschalten` (oder Bleistift-Symbol)

**5.4** Punkte hinzufügen:
- Klicken Sie auf `Punkt-Objekt hinzufügen` (Toolbar)
- Klicken Sie **3-5 Mal** auf verschiedene Stellen in der Karte
- Jedes Mal erscheint ein Dialog → einfach `OK` klicken

**5.5** Speichern:
- Klicken Sie `Änderungen speichern` (Disketten-Symbol)
- Bearbeitungsmodus beenden (wieder Bleistift-Symbol)

**ODER: Schneller Weg über Python Console:**

```python
from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY

# Layer erstellen
layer = QgsVectorLayer('Point?crs=EPSG:25832', 'wka_test', 'memory')
provider = layer.dataProvider()

# Test-Punkte hinzufügen
test_points = [
    (500150, 5700150),
    (500250, 5700250),
    (500350, 5700200),
]

layer.startEditing()
for x, y in test_points:
    feature = QgsFeature()
    feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
    provider.addFeature(feature)
layer.commitChanges()

# Layer zum Projekt hinzufügen
QgsProject.instance().addMapLayer(layer)

# Als Shapefile speichern
output_path = r'C:\GIS_Daten\Windkraft\Standorte\wka_test.shp'
QgsVectorFileWriter.writeAsVectorFormat(layer, output_path, 'UTF-8', layer.crs(), 'ESRI Shapefile')

print(f"✓ Test-Standorte erstellt: {output_path}")
```

---

## 🎯 SCHRITT 6: SCRIPT IN QGIS LADEN

**6.1** Processing Toolbox öffnen:
- Menü: `Verarbeitung` → `Werkzeugkiste`
- Oder: `Strg+Alt+T`

**6.2** Script hinzufügen:
1. In der Werkzeugkiste: Klicken Sie auf das **Python-Symbol** (oben)
2. Wählen Sie `Skript zu Werkzeugkiste hinzufügen...`
3. Navigieren Sie zu: `C:\GIS_Daten\Windkraft\Scripts\wind_earthwork_calculator.py`
4. Klicken Sie `Öffnen`

**6.3** Überprüfung:
- Das Script sollte nun unter `Scripts` → `Windkraft` erscheinen
- Name: **"Wind Turbine Earthwork Calculator"**

❗ **Falls Fehler auftreten:**
- Überprüfen Sie, ob die Datei korrekt als `.py` gespeichert wurde
- Öffnen Sie die Datei erneut und prüfen Sie, ob der Code vollständig ist

---

## ▶️ SCHRITT 7: SCRIPT AUSFÜHREN

**7.1** Daten laden (falls noch nicht geschehen):

In Python Console:
```python
# DEM laden
dem_path = r'C:\GIS_Daten\Windkraft\DEM\test_dem.tif'
dem_layer = iface.addRasterLayer(dem_path, 'Test DEM')

# Standorte laden
points_path = r'C:\GIS_Daten\Windkraft\Standorte\wka_test.shp'
points_layer = iface.addVectorLayer(points_path, 'WKA Standorte', 'ogr')

print("✓ Daten geladen!")
```

**7.2** Algorithm starten:
1. In der Processing Toolbox: Doppelklick auf **"Wind Turbine Earthwork Calculator"**
2. Es öffnet sich ein Dialog mit Parametern

**7.3** Parameter einstellen:

| Parameter | Wert | Bedeutung |
|-----------|------|-----------|
| **Digitales Geländemodell** | `Test DEM` | Ihr DEM auswählen |
| **WKA-Standorte** | `WKA Standorte` | Ihre Punkte auswählen |
| **Plattformlänge** | `45` | Meter (Standard für 3-4 MW WKA) |
| **Plattformbreite** | `40` | Meter |
| **Max. Neigung** | `2` | Prozent (2% = sehr eben) |
| **Böschungswinkel** | `34` | Grad (1:1.5 Verhältnis) |
| **Böschungsbreite** | `10` | Meter |
| **Ausgabe: Standorte...** | `[Temporäre Datei erstellen]` | Lassen Sie so |
| **Ausgabe: HTML-Report** | `C:\GIS_Daten\Windkraft\Ergebnisse\report.html` | Pfad wählen |

**7.4** Klicken Sie auf `Ausführen`

**7.5** Beobachten Sie den Fortschritt:
- Im unteren Bereich sehen Sie Log-Meldungen
- Fortschrittsbalken zeigt Verarbeitung
- Dauer: ca. 10-30 Sekunden (abhängig von Anzahl Standorte)

---

## 📊 SCHRITT 8: ERGEBNISSE ANSCHAUEN

### 8.1 Layer-Ausgabe in QGIS:

Nach der Verarbeitung erscheint ein neuer Layer: **"Ausgabe"**

**Attributtabelle öffnen:**
- Rechtsklick auf Layer → `Attributtabelle öffnen`

**Sie sehen folgende Spalten:**
- `id` - Standort-Nummer
- `platform_h` - Berechnete Plattform-Höhe (m)
- `terrain_min` - Minimale Geländehöhe (m)
- `terrain_max` - Maximale Geländehöhe (m)
- `terrain_mean` - Durchschnittliche Geländehöhe (m)
- `cut_volume` - Abtrag in m³ (Erdaushub)
- `fill_volume` - Auftrag in m³ (Auffüllung)
- `net_volume` - Netto-Volumen in m³
- `platform_area` - Plattformfläche in m²

### 8.2 HTML-Report:

**Report öffnen:**
1. Windows Explorer öffnen
2. Navigieren zu: `C:\GIS_Daten\Windkraft\Ergebnisse\`
3. Doppelklick auf `report.html`
4. Öffnet sich im Browser

**Im Report sehen Sie:**
- 📊 **Zusammenfassung** aller Standorte
- 📍 **Detailtabelle** mit allen Werten
- 🎨 Farbcodierung (Rot = Cut, Grün = Fill)

---

## 🎨 SCHRITT 9: VISUALISIERUNG (OPTIONAL)

### 9.1 Punkte einfärben nach Volumen:

**Rechtsklick auf Layer → `Eigenschaften` → `Symbologie`**

1. Oben: Dropdown von `Einzelsymbol` zu `Abgestuft` ändern
2. **Spalte:** `net_volume` auswählen
3. **Farbverlauf:** Wählen Sie einen (z.B. Rot → Grün)
4. **Klassen:** 5
5. Klicken Sie `Klassifizieren`
6. `OK`

Jetzt sehen Sie die Standorte farblich nach Netto-Volumen!

### 9.2 Beschriftungen hinzufügen:

**Im gleichen Dialog → Tab `Beschriftungen`**

1. Dropdown: `Einzelne Beschriftungen` wählen
2. **Beschriftung mit:** `cut_volume` auswählen
3. Optional: Schriftgröße anpassen
4. `OK`

---

## ✅ SCHRITT 10: FERTIG!

### Sie haben jetzt:
- ✓ Ein funktionierendes QGIS Processing Script
- ✓ Test-Daten zum Experimentieren
- ✓ Volumenberechnungen für WKA-Standorte
- ✓ Einen schönen HTML-Report

---

## 🔧 TROUBLESHOOTING - Häufige Probleme

### Problem 1: "Modul nicht gefunden"
**Lösung:** 
- QGIS neu starten
- Python Console öffnen und testen: `import numpy`
- Falls Fehler: QGIS neu installieren (inkl. alle Pakete)

### Problem 2: Script erscheint nicht in Toolbox
**Lösung:**
- Datei wirklich als `.py` gespeichert? (nicht `.py.txt`)
- Processing Toolbox: Klick auf Aktualisieren-Symbol
- QGIS neu starten

### Problem 3: "DEM Layer konnte nicht geladen werden"
**Lösung:**
- Überprüfen Sie CRS: DEM und Punkte müssen gleiches KBS haben
- DEM in QGIS laden und visuell prüfen

### Problem 4: "Keine gültigen Höhenwerte gefunden"
**Lösung:**
- Punkte liegen außerhalb des DEM-Bereichs
- Zoomen Sie auf das DEM und setzen Sie Punkte innerhalb
- CRS überprüfen (sollte EPSG:25832 sein)

### Problem 5: Volumina sind unrealistisch
**Lösung:**
- Überprüfen Sie DEM-Einheit (sollte Meter sein)
- Pixel-Größe prüfen (sollte 1m x 1m sein)
- Dies ist ein Prototyp - Werte sind Näherungen!

---

## 📚 NÄCHSTE SCHRITTE

### Phase 2: Mit echten Daten arbeiten

1. **Echte DGM1-Daten herunterladen** (siehe Schritt 2B)
2. **Eigene Standorte digitalisieren**
3. **Parameter anpassen** für Ihre Anforderungen

### Phase 3: Erweiterte Features

Wenn der Prototyp funktioniert, können wir erweitern:
- 🎯 Kostenberechnung (€/m³)
- 📏 Böschungsquerschnitte
- 🗺️ Optimierungsalgorithmus
- 📦 Vollständiges Plugin

---

## 💬 FRAGEN?

Bei Problemen oder Fragen:
1. Überprüfen Sie die Log-Meldungen in QGIS
2. Schauen Sie in die Python Console (Fehlermeldungen)
3. Fragen Sie mich - ich helfe gerne weiter!

---

## 📝 CHECKLISTE

Vor dem ersten Test:
- [ ] Ordnerstruktur erstellt
- [ ] Script-Datei gespeichert (`.py`)
- [ ] Test-DEM erstellt ODER echte Daten heruntergeladen
- [ ] Test-Standorte erstellt
- [ ] Script in Processing Toolbox geladen
- [ ] Alle Layer in QGIS geladen
- [ ] CRS überprüft (alle gleich: EPSG:25832)

Bereit zum Testen:
- [ ] Algorithm öffnen
- [ ] Parameter einstellen
- [ ] Ausführen klicken
- [ ] Ergebnisse prüfen
- [ ] Report öffnen

**Viel Erfolg! 🚀**