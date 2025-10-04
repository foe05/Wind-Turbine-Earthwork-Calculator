# Installation in QGIS

## 📋 Voraussetzungen

- **QGIS 3.22+** (Python 3.9+)
- **NumPy** (in QGIS enthalten)
- **Matplotlib** (optional, für Geländeschnitte)

---

## 🚀 Installationsschritte

### 1. Script-Dateien kopieren

Kopiere **beide Dateien** in den QGIS Processing Scripts Ordner:

```bash
# Linux/Mac
cp prototype/prototype.py ~/.local/share/QGIS/QGIS3/profiles/default/processing/scripts/
cp prototype/html_report_generator.py ~/.local/share/QGIS/QGIS3/profiles/default/processing/scripts/

# Windows (PowerShell)
Copy-Item prototype\prototype.py -Destination "$env:APPDATA\QGIS\QGIS3\profiles\default\processing\scripts\"
Copy-Item prototype\html_report_generator.py -Destination "$env:APPDATA\QGIS\QGIS3\profiles\default\processing\scripts\"
```

**Wichtig:** `html_report_generator.py` MUSS im gleichen Ordner wie `prototype.py` liegen!

---

### 2. QGIS-Scripts neu laden

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

### 3. Tool finden

Das Tool erscheint in der **Processing Toolbox** unter:

```
Processing Toolbox
└── Scripts
    └── Windkraft
        └── Wind Turbine Earthwork Calculator v5.5
```

---

## 🧪 Funktionstest

### Minimaler Test (ohne Geländeschnitte)

1. **Input vorbereiten:**
   - DEM (Raster, projiziert, z.B. UTM)
   - WKA-Standorte (Punkt-Layer, mindestens 1 Punkt)

2. **Tool öffnen:**
   - Processing Toolbox → Windkraft → "Wind Turbine Earthwork Calculator v5.5"

3. **Parameter einstellen:**
   - INPUT DEM: Dein Raster
   - INPUT Points: Dein Punkt-Layer
   - OUTPUT Report: Pfad zur HTML-Datei (z.B. `~/test_report.html`)
   - Alle anderen Parameter: Default-Werte OK

4. **Ausführen:**
   - "Run" klicken
   - Warten bis "✅ Fertig!" erscheint

5. **Report öffnen:**
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

### Import-Fehler: "html_report_generator could not be resolved"

**Ursache:** Modul nicht im gleichen Ordner wie `prototype.py`

**Lösung:**
```bash
# Prüfen ob beide Dateien vorhanden sind:
ls ~/.local/share/QGIS/QGIS3/profiles/default/processing/scripts/

# Sollte zeigen:
# prototype.py
# html_report_generator.py
```

Falls `html_report_generator.py` fehlt → nochmal kopieren (siehe Schritt 1)

---

### Report zeigt alten Stil (kein White Template)

**Ursache:** Fallback auf Legacy-Methode (Import fehlgeschlagen)

**Debug in Python-Console:**
```python
import sys
sys.path.append('/pfad/zu/processing/scripts')

try:
    from html_report_generator import HTMLReportGenerator
    print("✅ Modul geladen")
except Exception as e:
    print(f"❌ Fehler: {e}")
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

**Version:** 5.5 (Polygon-based Sampling + Professional Report)  
**Autor:** Windkraft-Standortplanung  
**Datum:** Oktober 2025
