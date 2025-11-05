# Installation in QGIS

## 📋 Voraussetzungen

- **QGIS 3.22+** (Python 3.9+)
- **NumPy** (in QGIS enthalten)
- **Requests** (für hoehendaten.de API, siehe Installation)
- **Matplotlib** (optional, für Geländeschnitte)

---

## 🚀 Installationsschritte

### 1. Python-Paket installieren (NEU v6.0)

Installiere die `requests` Bibliothek in QGIS Python:

```python
# In QGIS Python-Console (Plugins → Python-Konsole)
import subprocess
import sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
```

### 2. Script-Datei kopieren

Kopiere **eine Datei** in den QGIS Processing Scripts Ordner:

```bash
# Linux/Mac
cp prototype/WindTurbine_Earthwork_Calculator.py ~/.local/share/QGIS/QGIS3/profiles/default/processing/scripts/

# Windows (PowerShell)
Copy-Item prototype\WindTurbine_Earthwork_Calculator.py -Destination "$env:APPDATA\QGIS\QGIS3\profiles\default\processing\scripts\"
```

**Hinweis:** Ab v6.0 mit integrierter API, Caching und GeoPackage-Output!

---

### 3. QGIS-Scripts neu laden

#### Option A: Über Menü
1. QGIS öffnen
2. Menü: **Processing → Toolbox**
3. Im Toolbox-Panel: **Rechtsklick → Scripts → Reload Scripts**

#### Option B: Über Python-Console
1. QGIS öffnen
2. Menü: **Plugins → Python-Console** (Strg+Alt+P)
3. Eingeben:
   ```python
   import processing
   processing.core.Processing.Processing.updateAlgsList()
   ```

---

### 4. Tool finden

Das Tool erscheint in der **Processing Toolbox** unter:

```
Processing Toolbox
└── Scripts
    └── Windkraft
        └── Wind Turbine Earthwork Calculator v6.0
```

---

## 🧪 Funktionstest

### Minimaler Test mit API (NEU v6.0)

1. **Input vorbereiten:**
   - WKA-Standorte (Punkt-Layer, mindestens 1 Punkt, UTM32N empfohlen)
   - DEM wird automatisch von hoehendaten.de API geladen
   - Optional: Eigenes DEM (Raster, projiziert, z.B. UTM)

2. **Tool öffnen:**
   - Processing Toolbox → Windkraft → "Wind Turbine Earthwork Calculator v6.0"

3. **Parameter einstellen:**
   - ✓ DEM von hoehendaten.de API beziehen: Aktiviert (NEU!)
   - INPUT Points: Dein Punkt-Layer (UTM32N)
   - INPUT DEM: Leer lassen (API lädt automatisch)
   - Alle anderen Parameter: Default-Werte OK

4. **Ausführen:**
   - "Run" klicken
   - Beobachten Sie die API-Downloads im Log
   - Cache wird in ~/.qgis3/hoehendaten_cache/ gespeichert
   - Warten bis "✅ Fertig!" erscheint

5. **Ergebnisse:**
   - GeoPackage im aktuellen Verzeichnis: `WKA_{X}_{Y}.gpkg`
   - HTML-Report: `WKA_{X}_{Y}.html`
   - GeoPackage enthält DEM + alle Vektorlayer

6. **Report öffnen:**
   - HTML-Datei im Browser öffnen
   - "📄 Als PDF exportieren" Button testen (oben rechts)

---

## 🎨 HTML-Report Features

### Professional White Template

- **Cover Page:** Gradient-Hintergrund, Logo, Projekt-Info
- **Summary:** Key-Metrics (Gesamt-Aushub, Auftrag, Saldo)
- **Standort-Details:** Fundament, Kranfläche, Material-Bilanz
- **Geländeschnitte:** Thumbnails mit Modal (wenn vorhanden)

### PDF-Export

**Browser-Print verwenden:**
1. Button "📄 Als PDF exportieren" klicken
2. Im Druckdialog: "Als PDF speichern" wählen
3. Speicherort angeben → Fertig!

**Optimiert für:**
- ✅ A4-Format
- ✅ Page-breaks (Cover, Profile auf eigenen Seiten)
- ✅ Keine interaktiven Elemente im PDF
- ✅ Bilder in hoher Qualität

---

## 📁 Geländeschnitt-Integration

### Automatisch (wenn v5.0-Feature genutzt)

Wenn **"Geländeschnitte erstellen"** aktiviert ist:

1. Tool erstellt PNGs im gewählten Ordner:
   ```
   profile_output_folder/
   ├── Site_1_Foundation_NS.png
   ├── Site_1_Foundation_EW.png
   ├── Site_1_Crane_Longitudinal.png
   └── ...
   ```

2. HTML-Report **findet PNGs automatisch** und bindet sie ein

3. Im Report: **Thumbnails klicken** → Vollbild-Ansicht (Modal)

### Manuell (externe PNGs)

Falls PNGs extern erstellt wurden:

1. **Dateinamen-Konvention beachten:**
   ```
   Site_{site_id}_{type}.png
   ```
   Beispiel: `Site_1_Foundation_NS.png`

2. **Types:**
   - `Foundation_NS`, `Foundation_EW`
   - `Crane_Longitudinal`, `Crane_Cross`
   - `Crane_Edge_N`, `Crane_Edge_E`, `Crane_Edge_S`, `Crane_Edge_W`

3. **Ordner angeben:**
   - Im Tool-Dialog: "Ordner für Profilschnitt-PNGs" auswählen
   - Wenn leer: Gleicher Ordner wie HTML-Report

---

## 🐛 Troubleshooting

### Report zeigt alten Stil (sollte nicht mehr vorkommen ab v5.5)

**Hinweis:** Ab v5.5 ist der Professional HTML Report direkt integriert. Der alte Stil wird nicht mehr verwendet.

Falls doch der alte Stil erscheint, prüfen:
- QGIS-Log: Steht dort "✅ Professional Report erstellt!"?
- Falls nicht: Möglicherweise alte Script-Version im Cache

**Lösung:**
```bash
# Datei erneut kopieren (überschreibt alte Version)
cp prototype/prototype.py ~/.local/share/QGIS/QGIS3/profiles/default/processing/scripts/

# In QGIS: Scripts neu laden
# Processing → Toolbox → Rechtsklick → Reload Scripts
```

---

### Geländeschnitte werden nicht angezeigt

**Checkliste:**
1. ✅ PNGs existieren im angegebenen Ordner?
2. ✅ Dateinamen korrekt (siehe Konvention)?
3. ✅ "Geländeschnitte erstellen" war aktiviert?
4. ✅ Pfad relativ zum HTML-Report korrekt?

**Debug:**
- HTML-Report im Texteditor öffnen
- Nach `<img src=` suchen
- Pfad prüfen (sollte `./profile_folder/Site_1_....png` sein)

---

### PDF-Export funktioniert nicht

**Browser-Problem:**
- **Chrome/Edge:** Strg+P → "Als PDF speichern"
- **Firefox:** Strg+P → Druckdialog → "Microsoft Print to PDF" (Windows)
- **Safari:** Cmd+P → PDF-Button unten links

**Fallback:**
- Online-Tool: https://www.web2pdfconvert.com/
- HTML hochladen → PDF herunterladen

---

## 📞 Support

**GitHub Issues:** https://github.com/foe05/Wind-Turbine-Earthwork-Calculator/issues

**Logs prüfen:**
```python
# In QGIS Python-Console:
import processing
processing.algorithmHelp("script:windturbineearthworkv3")
```

---

**Version:** 6.0 (Hoehendaten.de API Integration & GeoPackage Output)
**Autor:** Windkraft-Standortplanung
**Datum:** November 2025
