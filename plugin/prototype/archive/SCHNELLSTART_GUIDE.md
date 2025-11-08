# SCHNELLSTART-GUIDE: CLAUDE CODE für QGIS Plugin

## 📋 CHECKLISTE VOR DEM START

### 1. Vorbereitungen
- [ ] QGIS LTR installiert und funktionsfähig
- [ ] Python 3 Environment mit QGIS-Zugriff
- [ ] Claude Code installiert und konfiguriert
- [ ] Deine Dateien bereit:
  - `WindTurbine_Earthwork_Calculator.py` (Prototyp)
  - `Kranstellfläche_Marsberg_V172-7_2-175m.dxf` (Test-DXF)
  - `CLAUDE_CODE_PROMPT.md` (Der erstellte Prompt)

### 2. Plugin-Verzeichnis
QGIS Plugin-Pfad (je nach System):
- **Windows:** `C:\Users\{user}\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\`
- **Linux:** `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
- **Mac:** `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`

---

## 🚀 CLAUDE CODE STARTEN

### Empfohlener Workflow:

**1. Projekt initialisieren:**
```bash
cd ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
mkdir windturbine_optimizer
cd windturbine_optimizer
```

**2. Claude Code starten:**
```bash
# In deinem Terminal (im Plugin-Verzeichnis)
claude-code
```

**3. Ersten Prompt an Claude Code:**
```
Ich möchte ein QGIS Processing Plugin entwickeln. 
Bitte lies die detaillierte Spezifikation in der Datei 
'CLAUDE_CODE_PROMPT.md' und erstelle zunächst die 
grundlegende Projekt-Struktur mit allen notwendigen Dateien.

Beginne mit Phase 1 (MVP):
1. Erstelle die Verzeichnisstruktur
2. Erstelle metadata.txt und __init__.py
3. Implementiere den DXF-Importer (core/dxf_importer.py)

Teste nach jedem Schritt mit der angehängten DXF-Datei.
```

---

## 💡 WICHTIGE TIPPS FÜR CLAUDE CODE

### Iteratives Arbeiten
Claude Code arbeitet am besten, wenn du **schrittweise vorgehst**:

✅ **Gut:**
- "Implementiere jetzt den DXF-Importer"
- "Teste den DXF-Import mit der Beispieldatei"
- "Füge jetzt Fehlerbehandlung hinzu"

❌ **Weniger gut:**
- "Implementiere das gesamte Plugin auf einmal"

### Konkrete Anweisungen
Je spezifischer deine Anfragen, desto besser:

✅ **Gut:**
- "Nutze ezdxf zum Einlesen der LWPOLYLINE-Entitäten aus Layer '0'"
- "Implementiere die Punkt-Verbindungs-Logik mit 0.01m Toleranz"

❌ **Weniger gut:**
- "Mach was mit dem DXF"

### Tests einfordern
Nach jeder Komponente testen lassen:

```
Erstelle jetzt ein Test-Script, das:
1. Die DXF-Datei einliest
2. Das Polygon validiert
3. Die Koordinaten ausgibt

Führe den Test aus und zeige mir das Ergebnis.
```

### Prototyp-Code nutzen
Explizit auf Prototyp verweisen:

```
Die Erdmassenberechnung ist bereits im Prototyp 
'WindTurbine_Earthwork_Calculator.py' implementiert.
Bitte übernimm die Logik aus den Zeilen 2500-3000
und passe sie für das modulare Design an.
```

---

## 🔧 DEBUGGING-STRATEGIE

### Wenn etwas nicht funktioniert:

**1. QGIS Python Console nutzen:**
```python
# In QGIS öffne: Plugins → Python Console
import sys
sys.path.append('/pfad/zum/plugin/ordner')

from core.dxf_importer import DXFImporter
importer = DXFImporter('test.dxf')
polygon = importer.to_qgs_polygon()
print(polygon.isGeosValid())
```

**2. Plugin Reloader installieren:**
- Plugins → Manage and Install Plugins → "Plugin Reloader"
- Ermöglicht Plugin-Reload ohne QGIS-Neustart

**3. Claude Code um Debug-Output bitten:**
```
Füge detailliertes Logging in den DXF-Importer ein.
Logge:
- Anzahl gefundener Polylinien
- Start/End-Punkte jeder Linie
- Verbindungs-Matches
- Finale Polygon-Vertex-Anzahl
```

### Log-Dateien prüfen:
```bash
# QGIS Log-Verzeichnis
~/.local/share/QGIS/QGIS3/profiles/default/processing/processing.log

# Plugin-spezifisches Log (wenn implementiert)
~/.qgis3/windturbine_plugin.log
```

---

## 📝 ENTWICKLUNGS-PHASEN IM DETAIL

### Phase 1: Grundgerüst (Tag 1)
**Ziel:** DXF einlesen, Polygon erzeugen

**Claude Code Prompts:**
1. "Erstelle die Projekt-Struktur gemäß Prompt"
2. "Implementiere DXFImporter mit ezdxf"
3. "Teste mit der Beispiel-DXF-Datei"
4. "Erstelle den Processing Algorithm Wrapper"
5. "Teste das Plugin in QGIS"

**Erfolgs-Kriterium:** 
Plugin erscheint in Processing Toolbox und kann DXF einlesen.

---

### Phase 2: DEM-Handling (Tag 2-3)
**Ziel:** Höhendaten downloaden und verarbeiten

**Claude Code Prompts:**
1. "Implementiere DEMDownloader mit hoehendaten.de API"
2. "Teste API-Call mit Beispiel-Koordinaten"
3. "Implementiere Caching-Logik"
4. "Implementiere Mosaik-Erzeugung mit GDAL"
5. "Teste mit echten Koordinaten (EPSG:25832)"

**Erfolgs-Kriterium:**
Plugin lädt DEM und speichert Mosaik im GeoPackage.

---

### Phase 3: Optimierung (Tag 4-5)
**Ziel:** Höhenoptimierung implementieren

**Claude Code Prompts:**
1. "Implementiere EarthworkCalculator basierend auf Prototyp"
2. "Übernimm Cut/Fill-Berechnung aus Prototyp Zeile X-Y"
3. "Implementiere Optimierungs-Loop"
4. "Teste mit min=300, max=310, step=0.1"
5. "Validiere Ergebnisse gegen Prototyp"

**Erfolgs-Kriterium:**
Plugin findet optimale Höhe und gibt Volumen aus.

---

### Phase 4: Visualisierung (Tag 6-7)
**Ziel:** Geländeschnitte und Report

**Claude Code Prompts:**
1. "Implementiere ProfileGenerator"
2. "Teste Schnittlinien-Generierung"
3. "Implementiere Matplotlib-Plotting"
4. "Übernimm HTML-Report aus Prototyp"
5. "Teste vollständigen Workflow"

**Erfolgs-Kriterium:**
Vollständiger Report mit Karten und Profilen.

---

## ⚠️ HÄUFIGE STOLPERSTEINE

### Problem 1: QGIS findet Plugin nicht
**Lösung:**
- Prüfe Plugin-Verzeichnis-Name (keine Leerzeichen!)
- `metadata.txt` muss vorhanden sein
- `__init__.py` muss `classFactory()` enthalten
- QGIS neu starten

### Problem 2: Import-Fehler
**Lösung:**
```python
# In __init__.py richtig importieren:
def classFactory(iface):
    from .processing_provider.provider import Provider
    from .plugin_main import WindTurbineOptimizerPlugin
    return WindTurbineOptimizerPlugin(iface)
```

### Problem 3: Processing Algorithm erscheint nicht
**Lösung:**
- Provider muss registriert werden in `initProcessing()`
- Algorithm muss von `QgsProcessingAlgorithm` erben
- `createInstance()` muss implementiert sein

### Problem 4: ezdxf nicht gefunden
**Lösung:**
```bash
# In QGIS Python Console:
import pip
pip.main(['install', 'ezdxf', '--user'])
```

### Problem 5: API-Timeout
**Lösung:**
- Timeout auf 60s erhöhen
- Retry-Logik implementieren
- User über langsame Verbindung informieren

---

## 🎯 QUALITÄTS-CHECKS

Vor Abschluss jeder Phase, Claude Code bitten:

```
Bitte führe folgende Checks durch:
1. PEP8 Linting (pycodestyle)
2. Type Hints überprüfen (mypy)
3. Docstrings vollständig?
4. Error Handling an allen kritischen Stellen?
5. Test-Script funktioniert?
```

---

## 📚 NÜTZLICHE RESSOURCEN

### QGIS PyQGIS
- API-Doku: https://qgis.org/pyqgis/3.34/
- Cookbook: https://docs.qgis.org/3.34/en/docs/pyqgis_developer_cookbook/

### Python-Bibliotheken
- ezdxf: https://ezdxf.mozman.at/
- NumPy: https://numpy.org/doc/
- Matplotlib: https://matplotlib.org/stable/

### QGIS Processing
- Processing Guide: https://docs.qgis.org/3.34/en/docs/user_manual/processing/
- Algorithm Template: https://docs.qgis.org/3.34/en/docs/pyqgis_developer_cookbook/processing.html

---

## 🏁 FINALE SCHRITTE

Nach Fertigstellung:

### 1. Plugin testen
- [ ] Verschiedene DXF-Dateien
- [ ] Verschiedene Höhenbereiche
- [ ] Edge Cases (leere DXF, keine Internet-Verbindung, etc.)

### 2. Dokumentation erstellen
```
Claude, erstelle bitte:
1. README.md mit Anleitung
2. Beispiel-Screenshots
3. Troubleshooting-Guide
```

### 3. Plugin verpacken
```bash
cd ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
zip -r windturbine_optimizer.zip windturbine_optimizer/
```

### 4. Installation testen
- In QGIS: Plugins → Install from ZIP
- Auf anderem Rechner testen

---

## 💬 SUPPORT

Bei Problemen:
- QGIS User Mailing List: https://lists.osgeo.org/mailman/listinfo/qgis-user
- Stack Exchange GIS: https://gis.stackexchange.com/
- QGIS Plugin Development Forum

---

**Viel Erfolg mit deinem Plugin! 🚀**

Bei Fragen zur Prompt-Verwendung oder technischen Details, 
frag einfach nach - ich helfe gerne weiter!
