# Windows 11 Quickstart — `v3-foundation` testen

So bringst du den Stand des Feature-Branches in dein QGIS auf Windows 11.

## 0. Voraussetzungen

- **QGIS 3.34 LTR oder neuer** — Installer von <https://qgis.org/de/site/forusers/download.html>.
  Empfohlen: das **OSGeo4W**-Setup (Standalone-Installer geht auch, OSGeo4W
  liefert aber die OSGeo4W Shell mit, die wir für `pip` brauchen).
- **Git for Windows** — <https://git-scm.com/download/win>.
- Optional: ein DXF-Testdatensatz (Kranstellfläche + Fundament). Ohne DXF
  kannst du den Plugin-Tab und die Restriktions-Analyse testen, aber keinen
  echten Lauf starten.

## 1. Repository klonen

In `PowerShell` (oder `Git Bash`):

```powershell
cd $env:USERPROFILE\Documents
git clone https://github.com/foe05/Wind-Turbine-Earthwork-Calculator.git
cd Wind-Turbine-Earthwork-Calculator
git checkout v3-foundation
git pull
```

## 2. Plugin in den QGIS-Profilordner kopieren

QGIS liest installierte Plugins aus
`%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\` (dein Default-Profil).

Anstatt zu kopieren, lege einen **Symlink** an — dann ziehen `git pull`-Updates
sofort durch, ohne dass du neu kopierst:

```powershell
# PowerShell als Administrator öffnen (Symlinks brauchen das auf Windows)
$src  = "$env:USERPROFILE\Documents\Wind-Turbine-Earthwork-Calculator\windturbine_earthwork_calculator_v2"
$dest = "$env:APPDATA\QGIS\QGIS3\profiles\default\python\plugins\windturbine_earthwork_calculator_v2"
New-Item -ItemType SymbolicLink -Path $dest -Target $src
```

Wenn du keinen Admin-Rechte-Symlink willst, einfach rüberkopieren:

```powershell
Copy-Item -Recurse -Force `
  "$env:USERPROFILE\Documents\Wind-Turbine-Earthwork-Calculator\windturbine_earthwork_calculator_v2" `
  "$env:APPDATA\QGIS\QGIS3\profiles\default\python\plugins\"
```

## 3. Python-Dependencies installieren

Das Plugin braucht: `ezdxf`, `requests`, `shapely`, `weasyprint`, `openpyxl`.
QGIS bringt `numpy`, `scipy`, `PyQt5` und `GDAL` schon mit.

Die saubere Variante ist die **OSGeo4W Shell** (kommt mit QGIS):

1. Start-Menü → *OSGeo4W Shell*
2. In der Shell:

```cmd
python -m pip install --upgrade pip
python -m pip install ezdxf>=1.1.0 requests>=2.28.0 shapely>=2.0.0 openpyxl>=3.0.0
python -m pip install weasyprint
```

> **WeasyPrint-Hinweis (Windows):** WeasyPrint hängt von GTK3 ab. Wenn der
> Import-Test (`python -c "import weasyprint"`) mit
> `OSError: cannot load library 'libgobject-2.0-0'` fehlschlägt, installiere
> das **GTK3-Runtime-Bundle** von <https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases>
> (einmaliges MSI-Setup). Danach QGIS neu starten.

Alternativ kannst du im Plugin selbst das mitgelieferte Hilfsskript ausführen:

```cmd
cd "%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\windturbine_earthwork_calculator_v2"
python install_dependencies.py
```

## 4. Plugin in QGIS aktivieren

1. QGIS starten.
2. *Erweiterungen → Erweiterungen verwalten und installieren* (Strg+M).
3. Reiter **Installiert** → Haken bei **Wind Turbine Earthwork Calculator V2**.
4. Es erscheint ein neuer Eintrag in der Werkzeugleiste und ein Algorithmus
   *Wind Turbine Earthwork Calculator V2 → Optimize Platform Height* in der
   Verarbeitungs-Werkzeugkiste.

Falls der Haken nicht hält / das Plugin nicht startet:

- *Hilfe → Über → Protokoll* öffnen
- Im Panel *Protokollmeldungen* (Strg+5) den Reiter *Plugins* prüfen — meist
  fehlt eine Dependency aus Schritt 3.

## 5. Erstes Smoke-Through

### a) Plugin-Dialog öffnen

Klick auf das Plugin-Icon → tab-basierter Dialog erscheint. Reiter:

- 📂 **Eingabe** — DXF-Pfade, Foundation-Parameter
- ⚙️ **Optimierung** — Höhenbereich, Böschung, **„Erweiterte Analysen"**
  (Rotations-Analyse, Mass-Haul) — neue Checkboxen aus `v3-foundation`
- 🚧 **Restriktionen** — neu in `v3-foundation`
- 📊 **Geländeschnitte**
- 🏗️ **Bodenstabilisierung**
- 💾 **Ausgabe** — Workspace + jetzt **lokales DEM (Drohne)** + Slope-Stability-Export
- 📈 **Standortvergleich**

### b) Mini-Lauf

1. **Eingabe-Tab:** mindestens DXF für Kranstellfläche und Fundament setzen.
2. **Ausgabe-Tab:** Workspace wählen (leerer Ordner, z. B.
   `C:\Users\<du>\Documents\WEA-Test`).
3. **Optimierung-Tab:** Höhenbereich anpassen (für einen schnellen Test 5 m
   Range, 0.1 m Schritt).
4. **Optional:** *„Optimale Plattform-Ausrichtung analysieren"* + *„Massenmassenkurve
   berechnen"* ankreuzen, dann beides im Bericht sehen.
5. **Optional:** im Ausgabe-Tab *„Slope-Stability-XML exportieren"* ankreuzen.
6. **Restriktionen-Tab (optional):** eine Vektor-Ebene aus dem QGIS-Projekt
   (z. B. ein Wohnbau-Polygon) auswählen, Distanz 600 m → Position prüfen.
7. **Start.**

Falls du **kein DXF** zur Hand hast: nur den Restriktions-Tab benutzen,
Koordinate eingeben (UTM 32N, EPSG:25832), *Position prüfen* / *Nächste gültige
Position* → das funktioniert ohne Lauf.

### c) Output-Verzeichnis (nach erfolgreichem Lauf)

Im Workspace landen:

```
WEA-Test\
├─ ergebnisse\
│  ├─ WKA_<x>_<y>_DEM.tif
│  ├─ WKA_<x>_<y>_MultiSurface.gpkg
│  ├─ WKA_<x>_<y>_Bericht_MultiSurface.html  ← Bericht mit allen neuen Sektionen
│  ├─ WKA_<x>_<y>_meshes\
│  │  ├─ kranstellflaeche.obj, fundamentsohle.obj, …
│  │  ├─ terrain.obj
│  │  ├─ scene.gltf            ← kombinierte 3D-Szene
│  │  ├─ viewer.html           ← Three.js-Viewer (Doppelklick öffnet im Browser)
│  │  └─ surfaces.xml          ← LandXML für Trimble/Topcon/Leica
│  └─ slope_stability.xml      ← nur wenn opt-in aktiviert
├─ gelaendeschnitte\           ← Profil-PNGs
└─ cache\dem_tiles\
```

Im **Bericht** (HTML, öffnet sich automatisch im Standardbrowser) sind die
neuen Sektionen sichtbar:

- 🧭 **Ausrichtungs-Analyse Kranstellfläche** (wenn opt-in)
- 📈 **Massenmassenkurve** (wenn opt-in)
- 🪨 **Bodenschichten (Strata-Quantities)** — automatisch
- 📅 **Bauphasen-Verteilung** — automatisch
- 🌍 **CO₂-Bilanz** — automatisch

Die `viewer.html` braucht beim ersten Öffnen **kurz Internet** (lädt Three.js
einmal von jsDelivr), funktioniert danach offline solange der Browser-Cache
hält.

## 6. Drohnen-DEM testen (optional)

Wenn du ein eigenes Drohnen-DEM (GeoTIFF) hast:

1. Ausgabe-Tab → Gruppe **„Lokales DEM (z. B. Drohnenbefliegung)"** → Durchsuchen
2. Lauf starten — STEP 4 überspringt dann die hoehendaten.de-Abfrage komplett.

Anforderung: das Raster muss in EPSG:25832–25836 (UTM Zone 32–36N) vorliegen
und die DXF-Geometrien geometrisch abdecken.

## 7. Headless / Python-Konsole testen

In der QGIS Python-Konsole (Strg+Alt+P) kannst du die Module direkt importieren:

```python
from windturbine_earthwork_calculator_v2.core import park_optimizer, mesh_exporter

pad = mesh_exporter.polygon_to_mesh_at_height(
    [(0,0),(20,0),(20,10),(0,10)], 320.0, name="pad"
)
mesh_exporter.write_obj(r"C:\Users\<du>\Documents\WEA-Test\pad.obj", pad)
```

Mehr Beispiele: `windturbine_earthwork_calculator_v2/docs/PYTHON_API.md`.

## 8. Updates ziehen

Wenn du Schritt 2 als **Symlink** gelöst hast:

```powershell
cd $env:USERPROFILE\Documents\Wind-Turbine-Earthwork-Calculator
git pull
```

QGIS neu starten reicht (oder im Plugin-Manager kurz aus- und einschalten).

Wenn du **kopiert** hast: Schritt 2 wiederholen (Quelle und Ziel sind dann nicht
mehr verknüpft).

## 9. Typische Stolpersteine auf Windows

| Symptom | Ursache / Fix |
|---|---|
| Plugin erscheint nicht im Manager | falscher Profil-Ordner — prüfe `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\` |
| `ModuleNotFoundError: ezdxf` beim Start | Dependency-Schritt 3 vergessen oder im falschen Python ausgeführt — **immer in der OSGeo4W Shell** installieren, nicht in einem separaten Python |
| `OSError: libgobject-2.0-0` beim PDF-Export | WeasyPrint-GTK3-Runtime (siehe Hinweis in Schritt 3) |
| Lauf hängt bei „DEM herunterladen" | Firewall / Proxy → hoehendaten.de auf Port 14444 erlauben, oder lokales DEM nutzen |
| `multiprocessing` schlägt fehl | auf Windows ist der parallele Pfad bewusst deaktiviert (`platform.system() != 'Windows'`); der serielle Pfad ist langsamer aber sicher |
| Viewer.html zeigt nur graues Feld | Browser hat kein Internet → einmalig online öffnen, danach hält der Cache |
| `git pull` zieht nichts | Branch prüfen: `git status` muss `On branch v3-foundation` zeigen |

## 10. Tests selbst laufen lassen

Optional in der OSGeo4W Shell:

```cmd
cd /d "%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\windturbine_earthwork_calculator_v2"
python -m pip install pytest
python -m pytest tests\test_e2e_smoke.py -v
```

Der E2E-Smoke-Test läuft die ganze Park-Planungs-Pipeline durch alle
QGIS-freien Module — wenn der grün ist, sind die Kern-Algorithmen funktional.

---

Bei Problemen die Logs sammeln und ein Issue aufmachen:

- QGIS-Log: *Ansicht → Bedienfelder → Protokollmeldungen* (Strg+5), Reiter *Plugins*
- Plugin-Log: `%USERPROFILE%\.qgis3\windturbine_calculator_v2\*.log`
- Issue: <https://github.com/foe05/Wind-Turbine-Earthwork-Calculator/issues>
