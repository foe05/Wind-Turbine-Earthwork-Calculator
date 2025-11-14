# Wind Turbine Earthwork Calculator V2 - Multi-Surface Edition

## Benutzerhandbuch

**Version:** 2.0 - Multi-Surface Extension
**Autor:** Wind Energy Site Planning
**Datum:** November 2025

---

## Inhaltsverzeichnis

1. [Überblick](#überblick)
2. [Voraussetzungen](#voraussetzungen)
3. [Konzept der 4 Flächentypen](#konzept-der-4-flächentypen)
4. [Installation](#installation)
5. [Workflow](#workflow)
6. [Parameter-Referenz](#parameter-referenz)
7. [Berechnungsformeln](#berechnungsformeln)
8. [Ausgabedaten](#ausgabedaten)
9. [Beispiel-Projekt](#beispiel-projekt)
10. [Troubleshooting](#troubleshooting)

---

## Überblick

Das **Wind Turbine Earthwork Calculator Plugin V2** ist eine QGIS-Erweiterung zur automatischen Berechnung und Optimierung von Erdmassen für Windenergieanlagen-Baustellen. Im Gegensatz zur V1-Version, die nur eine einzelne Fläche (Kranstellfläche) betrachtete, unterstützt V2 die **simultane Optimierung von 4 verschiedenen Flächentypen** mit komplexen räumlichen und höhenmäßigen Beziehungen zueinander.

### Hauptfunktionen

- ✅ **4-Flächen-Optimierung:** Kranstellfläche, Fundament, Auslegerfläche, Blattlagerfläche
- ✅ **FOK-basierte Höhensteuerung:** Fundamentoberkante als behördlich vorgegebener Anker
- ✅ **Intelligente Gefälle-Berechnung:** Auslegerfläche mit konstanter Längsneigung (2-8%)
- ✅ **Auto-Slope Feature:** Automatische Anpassung an Geländeneigung
- ✅ **Integrierte Validierung:** Prüfung räumlicher Beziehungen zwischen Flächen
- ✅ **Vollständige Erdmassenberechnung:** Cut/Fill für alle Flächen inkl. Böschungen
- ✅ **DEM-Integration:** Automatischer Download von Höhendaten
- ✅ **Profil-Generierung:** Quer- und Längsprofile durch alle Flächen
- ✅ **HTML-Report:** Professionelle Dokumentation mit Karten und Grafiken
- ✅ **GeoPackage-Export:** 5 Layer für alle Flächen und Profile

---

## Voraussetzungen

### Software

- **QGIS:** Version 3.22 oder höher
- **Python:** Version 3.8 oder höher (in QGIS enthalten)
- **Python-Pakete:**
  - `ezdxf` (für DXF-Import)
  - `numpy` (für numerische Berechnungen)
  - `matplotlib` (für Profil-Grafiken)
  - `shapely` (für Geometrie-Operationen)

### DXF-Dateien

Sie benötigen **4 separate DXF-Dateien** mit den Umrissen der jeweiligen Flächen:

1. **Kranstellfläche** (`Kranstellflaeche.dxf`)
   - Rechteckig oder polygonal
   - Typische Größe: 30×40m bis 40×50m
   - Enthält: LWPOLYLINE oder POLYLINE Entitäten

2. **Fundamentfläche** (`Fundamentflaeche.dxf`)
   - Meist kreisförmig
   - Typischer Durchmesser: Ø 20-25m
   - Muss **innerhalb** der Kranstellfläche liegen

3. **Auslegerfläche** (`Auslegerflaeche.dxf`)
   - Rechteckig oder polygonal
   - Typische Größe: 30×15m bis 40×20m
   - Muss die Kranstellfläche **berühren** (gemeinsame Kante)

4. **Blattlagerfläche** (`Rotorflaeche.dxf`)
   - Rechteckig
   - Typische Größe: 20×10m bis 30×15m
   - Muss die Kranstellfläche **berühren** (gemeinsame Kante)

### Behördliche Vorgaben

- **Fundamentoberkante (FOK):** Wird von Behörden vorgeschrieben (z.B. 305.50 m ü.NN)
- **Fundamenttiefe:** Konstruktionsabhängig (typisch 3-4m)

---

## Konzept der 4 Flächentypen

### 1. Fundamentfläche

**Zweck:** Trägt das Fundament der Windenergieanlage.

**Eigenschaften:**
- Lage: Innerhalb/unterhalb der Kranstellfläche
- Höhe: Oberkante Fundament (FOK) ist behördlich vorgegeben
- Tiefe: Fundamentsohle liegt `Fundamenttiefe` Meter unter FOK
- Form: Meist kreisförmig (Ø 20-25m)

**Besonderheit bei Erdmassen:**
- **Aushub:** Komplett auszuheben von Gelände bis Fundamentsohle
- **Auffüllung:** Minimal (Fundament wird mit Beton gefüllt, nicht mit Erde)
- Das Aushubvolumen wird zu den Gesamt-Erdmassen hinzugefügt

### 2. Kranstellfläche (Optimierungsvariable)

**Zweck:** Ebene Fläche für Kranaufstellung und Montagevorgänge.

**Eigenschaften:**
- Lage: Zentrale Referenzfläche
- Höhe: **Wird optimiert** im Bereich FOK ± Δh
- Form: Rechteckig oder polygonal (30×40m bis 40×50m)
- Schichtaufbau: Oberste Schicht ist Schotter (typisch 0.5m dick)

**Höhenberechnung:**
```
Planumshöhe = Kranstellflächenhöhe - Schotterschichtdicke
```

**Optimierungsziel:**
Die Kranstellflächenhöhe wird so gewählt, dass die **Gesamterdmasse** über alle 4 Flächen **minimiert** wird.

### 3. Auslegerfläche (mit Längsneigung)

**Zweck:** Ablagefläche für Rotorblätter während der Montage.

**Eigenschaften:**
- Lage: Schließt direkt an Kranstellfläche an (gemeinsame Kante)
- Höhe: Anschlusskante auf Kranstellflächenhöhe, dann abfallend
- Form: Rechteckig (30×15m bis 40×20m)
- Neigung: **Konstantes Längsge Gefälle** 2-8% (typisch 5%)
- Querneigung: 0% (planar quer zur Hauptachse)

**Besonderheit:**
- **Auto-Slope Feature:** Plugin kann Neigung automatisch an Gelände anpassen
- Neigung wird innerhalb des zulässigen Bereichs (2-8%) gewählt
- Längere Transportwege für große Komponenten

### 4. Blattlagerfläche

**Zweck:** Lagerfläche für Rotornabe und weitere Komponenten.

**Eigenschaften:**
- Lage: Schließt an Kranstellfläche an (gemeinsame Kante)
- Höhe: Kranstellflächenhöhe + konfigurierbare Differenz
- Form: Rechteckig (20×10m bis 30×15m)
- Neigung: 0% (planar)

**Höhenberechnung:**
```
Blattflächenhöhe = Kranstellflächenhöhe + Höhendifferenz
```

Die Höhendifferenz kann positiv (Blattfläche höher) oder negativ (Blattfläche tiefer) sein.

### Räumliche Beziehungen

```
        ┌─────────────────────┐
        │   Auslegerfläche    │
        │   (Längsneigung)    │
        └───────┬─────────────┘
                │ berührt
    ┌───────────┴───────────┐
    │   Kranstellfläche     │◄─── Optimierungsvariable
    │       (planar)        │
    │  ┌─────────────────┐  │
    │  │  Fundament      │  │◄─── FOK (behördlich)
    │  │  (darunter)     │  │
    │  └─────────────────┘  │
    └───────────┬───────────┘
                │ berührt
        ┌───────┴─────────┐
        │ Blattlagerfläche│
        │    (planar)     │
        └─────────────────┘
```

---

## Installation

### 1. Plugin-Dateien kopieren

Kopieren Sie den Ordner `windturbine_earthwork_calculator_v2` in das QGIS-Plugin-Verzeichnis:

**Linux:**
```bash
~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
```

**Windows:**
```
C:\Users\<Username>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\
```

**macOS:**
```
~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/
```

### 2. Python-Abhängigkeiten installieren

Öffnen Sie die **Python-Konsole** in QGIS und führen Sie aus:

```python
import pip
pip.main(['install', 'ezdxf', 'shapely'])
```

Alternativ über die Kommandozeile (mit QGIS-Python):

**Linux/macOS:**
```bash
pip3 install ezdxf shapely
```

**Windows:**
```cmd
python -m pip install ezdxf shapely
```

### 3. Plugin aktivieren

1. QGIS öffnen
2. Menü: **Erweiterungen → Erweiterungen verwalten und installieren**
3. Tab **Installiert**
4. Häkchen bei **Wind Turbine Earthwork Calculator V2** setzen

---

## Workflow

### Schritt 1: Plugin starten

**Menü:** Erweiterungen → Wind Turbine Earthwork Calculator → Multi-Surface Calculation

Es öffnet sich der Dialog mit 4 Tabs.

### Schritt 2: Tab "Eingabe" - DXF-Dateien laden

#### DXF-Dateien

Laden Sie alle 4 DXF-Dateien:

1. **Kranstellfläche:** Umriss der Kranstellfläche
2. **Fundamentfläche:** Umriss des Fundaments
3. **Auslegerfläche:** Umriss der Auslegerfläche
4. **Blattlagerfläche:** Umriss der Blattlagerfläche

**Punkt-Toleranz:** (Standard: 0.01m)
- Toleranz für das Verbinden von Punkten im DXF
- Bei gut gezeichneten DXFs kann dieser Wert niedrig bleiben

#### Fundamentparameter

**Fundamentoberkante (FOK):**
- Behördlich vorgegebene Höhe in m ü.NN
- Beispiel: 305.50 m ü.NN
- Dies ist der zentrale Höhenankerpunkt!

**Fundamenttiefe:**
- Tiefe unter FOK bis zur Fundamentsohle
- Standard: 3.5m
- Bestimmt das Aushubvolumen des Fundaments

**Fundamentdurchmesser:**
- Optional, falls nicht aus DXF ersichtlich
- Wird für Volumenabschätzungen verwendet

#### Kranstellflächen-Parameter

**Suchbereich unter FOK:**
- Wie weit darf die Kranstellfläche **unter** FOK liegen?
- Standard: 0.5m
- Beispiel: Bei FOK=305.50m und 0.5m ergibt sich Minimum 305.00m

**Suchbereich über FOK:**
- Wie weit darf die Kranstellfläche **über** FOK liegen?
- Standard: 0.5m
- Beispiel: Bei FOK=305.50m und 0.5m ergibt sich Maximum 306.00m

**Live-Anzeige:**
Der absolute Suchbereich wird automatisch angezeigt, z.B.:
```
→ Suchbereich: 305.00 - 306.00 m ü.NN
```

**Schotterschichtdicke:**
- Dicke der Schotterschicht auf der Kranstellfläche
- Standard: 0.5m
- Wird von der Kranstellflächenhöhe abgezogen für das Planum

#### Auslegerflächen-Parameter

**Längsneigung:**
- Konstante Neigung der Auslegerfläche in %
- Zulässiger Bereich: 2.0 - 8.0%
- Standard: 5.0%

**☑ Neigung automatisch an Gelände anpassen:**
- Wenn aktiviert (Standard), passt das Plugin die Neigung automatisch an
- Die Geländeneigung wird via linearer Regression berechnet
- Das Ergebnis wird auf den zulässigen Bereich (2-8%) begrenzt
- Empfohlen für optimale Erdmassenbalance!

#### Blattlagerflächen-Parameter

**Höhendifferenz zu Kranstellfläche:**
- Relativer Höhenunterschied zur Kranstellfläche
- Positiv: Blattfläche liegt höher
- Negativ: Blattfläche liegt tiefer
- Standard: 0.0m (gleiche Höhe)

### Schritt 3: Tab "Optimierung" - Feineinstellungen

**Höhen-Schritt:**
- Schrittweite für die Höhensuche
- Standard: 0.1m
- Kleinere Werte = genauere Optimierung, aber langsamer
- Beispiel: Bei Suchbereich 305.00-306.00m und Schritt 0.1m werden 11 Höhen getestet

**Böschungswinkel:**
- Winkel der Erdböschungen in Grad
- Standard: 45° (entspricht 1:1)
- Üblich: 30°-60°

### Schritt 4: Tab "Geländeschnitte" - Profil-Optionen

**Querprofile:**
- ☑ Querprofile generieren
- Schnitt-Abstand: 10m (Abstand zwischen Profilen)
- Überhang: 10% (Extension über Flächen hinaus)

**Längsprofile:**
- ☑ Längsprofile generieren
- Schnitt-Abstand: 10m
- Überhang: 10%

**Visualisierung:**
- Vert. Überhöhung: 2.0x (für bessere Sichtbarkeit in Grafiken)

### Schritt 5: Tab "Ausgabe" - Workspace wählen

**Workspace-Ordner:**
- Wählen Sie einen leeren Ordner für alle Ausgaben
- Das Plugin erstellt automatisch die Struktur:
  ```
  Workspace/
  ├── ergebnisse/
  │   ├── WKA_XXXXX_YYYYY_MultiSurface.gpkg
  │   └── WKA_XXXXX_YYYYY_Bericht_MultiSurface.html
  ├── gelaendeschnitte/
  │   ├── Querschnitt_01.png
  │   ├── Querschnitt_02.png
  │   ├── Laengsprofil_01.png
  │   └── ...
  └── cache/
      └── dem_tiles/
  ```

**Optionen:**
- ☐ DEM-Cache ignorieren: Erzwingt erneuten Download der Höhendaten

### Schritt 6: Berechnung starten

Klicken Sie auf **"Berechnung starten"**.

Das Plugin führt folgende Schritte aus:

1. ✅ **Import:** Alle 4 DXF-Dateien werden importiert
2. ✅ **Validierung:** Räumliche Beziehungen werden geprüft
3. ✅ **DEM Download:** Höhendaten werden heruntergeladen
4. ✅ **Optimierung:** Beste Kranstellflächenhöhe wird gefunden
5. ✅ **Profile:** Quer- und Längsprofile werden generiert
6. ✅ **Report:** HTML-Bericht wird erstellt
7. ✅ **Export:** GeoPackage mit allen Layern wird gespeichert
8. ✅ **QGIS:** Layer werden zum Projekt hinzugefügt

**Fortschrittsanzeige:** Zeigt den aktuellen Schritt und Fortschritt (0-100%)

**Dauer:** Je nach Flächengröße und Suchbereich ca. 2-10 Minuten

---

## Parameter-Referenz

### DXF-Import-Parameter

| Parameter | Einheit | Standard | Beschreibung |
|-----------|---------|----------|--------------|
| `dxf_crane` | Pfad | - | DXF-Datei für Kranstellfläche |
| `dxf_foundation` | Pfad | - | DXF-Datei für Fundamentfläche |
| `dxf_boom` | Pfad | - | DXF-Datei für Auslegerfläche |
| `dxf_rotor` | Pfad | - | DXF-Datei für Blattlagerfläche |
| `dxf_tolerance` | m | 0.01 | Toleranz für Punktverbindung |

### Fundament-Parameter

| Parameter | Einheit | Beispiel | Beschreibung |
|-----------|---------|----------|--------------|
| `fok` | m ü.NN | 305.50 | Fundamentoberkante (behördlich) |
| `foundation_depth` | m | 3.5 | Tiefe unter FOK |
| `foundation_diameter` | m | 20.0 | Durchmesser (optional) |

### Kranstellflächen-Parameter

| Parameter | Einheit | Standard | Beschreibung |
|-----------|---------|----------|--------------|
| `search_range_below_fok` | m | 0.5 | Suchbereich unter FOK |
| `search_range_above_fok` | m | 0.5 | Suchbereich über FOK |
| `gravel_thickness` | m | 0.5 | Schotterschichtdicke |

### Auslegerflächen-Parameter

| Parameter | Einheit | Standard | Beschreibung |
|-----------|---------|----------|--------------|
| `boom_slope` | % | 5.0 | Längsneigung (2-8%) |
| `boom_auto_slope` | bool | true | Auto-Anpassung an Gelände |

### Rotor-Parameter

| Parameter | Einheit | Standard | Beschreibung |
|-----------|---------|----------|--------------|
| `rotor_height_offset` | m | 0.0 | Höhendifferenz zu Kran |

### Optimierungs-Parameter

| Parameter | Einheit | Standard | Beschreibung |
|-----------|---------|----------|--------------|
| `height_step` | m | 0.1 | Schrittweite für Suche |
| `slope_angle` | ° | 45.0 | Böschungswinkel |

---

## Berechnungsformeln

### 1. Fundamentfläche

#### Fundamentsohle-Höhe
```
H_sohle = FOK - Fundamenttiefe
```

#### Aushubvolumen
Das Aushubvolumen wird **pixelweise** über der Fundamentfläche berechnet:

```
V_aushub = Σ (H_gelände,i - H_sohle) × A_pixel
```

Wobei:
- `H_gelände,i` = Geländehöhe am Pixel i
- `H_sohle` = Fundamentsohlenhöhe
- `A_pixel` = Pixelfläche des DEM (typisch 1m²)
- Summe über alle Pixel innerhalb der Fundamentfläche

**Auffüllung:** Minimal (nur für Statistik, da Fundament mit Beton gefüllt wird)

---

### 2. Kranstellfläche

#### Planumshöhe
```
H_planum = H_kran - d_schotter
```

Wobei:
- `H_kran` = Kranstellflächenhöhe (Optimierungsvariable)
- `d_schotter` = Schotterschichtdicke (typisch 0.5m)

#### Cut/Fill Volumina

**Auf der Plattform:**
```
V_cut = Σ max(0, H_gelände,i - H_planum) × A_pixel
V_fill = Σ max(0, H_planum - H_gelände,i) × A_pixel
```

**Böschungsberechnung:**

Die Böschungsbreite hängt vom maximalen Höhenunterschied ab:

```
w_böschung = Δh_max / tan(α_böschung)
```

Wobei:
- `Δh_max` = max(|H_gelände - H_planum|)
- `α_böschung` = Böschungswinkel (typisch 45°)

Die Böschungsfläche wird durch Buffern der Plattformfläche erzeugt:
```
A_böschung = Buffer(A_plattform, w_böschung) \ A_plattform
```

**Vereinfachte Böschungsvolumen-Berechnung:**
```
V_cut_böschung = Σ max(0, H_gelände,i - H_mittel,i) × A_pixel
V_fill_böschung = Σ max(0, H_mittel,i - H_gelände,i) × A_pixel
```

Wobei `H_mittel,i ≈ (H_planum + H_gelände,i) / 2`

**Gesamtvolumen Kranstellfläche:**
```
V_cut_gesamt = V_cut + V_cut_böschung
V_fill_gesamt = V_fill + V_fill_böschung
```

---

### 3. Auslegerfläche (mit Gefälle)

#### Anschlusskante identifizieren

Die Anschlusskante ist die gemeinsame Grenze zwischen Kranstellfläche und Auslegerfläche:

```
Edge_anschluss = Boundary(Kran) ∩ Boundary(Ausleger)
```

#### Gefällerichtung

Die Gefällerichtung ist **perpendikular** zur Anschlusskante, zeigend in die Auslegerfläche:

```
θ_gefälle = θ_kante + 90°
```

#### Höhenberechnung für jeden Pixel

Für jeden Pixel in der Auslegerfläche:

1. **Berechne Distanz zur Anschlusskante** (entlang Gefällerichtung):
```
d_i = (P_i - P_kante) · (cos θ_gefälle, sin θ_gefälle)
```

Wobei:
- `P_i` = Position des Pixels
- `P_kante` = nächster Punkt auf Anschlusskante
- `·` = Skalarprodukt (Projektion)

2. **Berechne Zielhöhe mit Gefälle:**
```
H_ziel,i = H_kran - (d_i × s_längs / 100)
```

Wobei:
- `H_kran` = Kranstellflächenhöhe
- `d_i` = Distanz von Anschlusskante
- `s_längs` = Längsneigung in Prozent (z.B. 5.0 für 5%)

3. **Berechne Cut/Fill:**
```
Δh_i = H_gelände,i - H_ziel,i

V_cut = Σ max(0, Δh_i) × A_pixel
V_fill = Σ max(0, -Δh_i) × A_pixel
```

#### Auto-Slope Feature

Wenn Auto-Slope aktiviert ist, wird die Geländeneigung via **linearer Regression** berechnet:

**Sammle Datenpunkte:**
- Für alle Pixel in Auslegerfläche: (d_i, H_gelände,i)
- Nur Pixel mit d_i > 0 (in Gefällerichtung)

**Lineare Regression:**
```
n = Anzahl Datenpunkte
Σx = Σ d_i
Σy = Σ H_gelände,i
Σxy = Σ (d_i × H_gelände,i)
Σx² = Σ d_i²

m = (n × Σxy - Σx × Σy) / (n × Σx² - (Σx)²)
```

**Konvertierung zu Prozent:**
```
s_terrain = m × 100
```

**Clamping auf zulässigen Bereich:**
```
s_längs = clamp(|s_terrain|, s_min, s_max)
        = max(s_min, min(s_max, |s_terrain|))
```

Mit s_min = 2.0% und s_max = 8.0%

---

### 4. Blattlagerfläche

#### Höhenberechnung
```
H_rotor = H_kran + Δh_rotor
```

Wobei:
- `H_kran` = Kranstellflächenhöhe
- `Δh_rotor` = Konfigurierter Höhenoffset (kann ± sein)

#### Cut/Fill Volumina

Analog zur Kranstellfläche, aber mit H_rotor:

```
V_cut = Σ max(0, H_gelände,i - H_rotor) × A_pixel
V_fill = Σ max(0, H_rotor - H_gelände,i) × A_pixel
```

Plus Böschungsvolumen (analog zur Kranstellfläche).

---

### 5. Optimierung

#### Zielfunktion

Das Plugin minimiert das **Gesamtvolumen der Erdbewegungen**:

```
Minimize: V_gesamt = V_cut_gesamt + V_fill_gesamt
```

Wobei:
```
V_cut_gesamt = V_cut_fundament + V_cut_kran + V_cut_ausleger + V_cut_rotor
V_fill_gesamt = V_fill_fundament + V_fill_kran + V_fill_ausleger + V_fill_rotor
```

#### Suchraum

Die Kranstellflächenhöhe H_kran wird im folgenden Bereich gesucht:

```
H_min = FOK - Δh_unten
H_max = FOK + Δh_oben
H_kran ∈ [H_min, H_max] mit Schritt Δh_step
```

Beispiel:
- FOK = 305.50 m ü.NN
- Δh_unten = 0.50 m
- Δh_oben = 0.50 m
- Δh_step = 0.10 m

→ Suchraum: [305.00, 305.10, 305.20, ..., 305.90, 306.00] m ü.NN (11 Höhen)

#### Tie-Breaker

Bei mehreren Höhen mit gleichem Gesamtvolumen wird die Höhe mit dem **kleinsten Netto-Volumen** (|V_cut - V_fill|) bevorzugt, da dies eine bessere Balance zwischen Abtrag und Auftrag bedeutet.

```
Wenn V_gesamt,A = V_gesamt,B:
    Wähle min(|V_cut,A - V_fill,A|, |V_cut,B - V_fill,B|)
```

---

## Ausgabedaten

### GeoPackage (.gpkg)

Das GeoPackage enthält **5 Layer:**

#### 1. `kranstellflaechen` (Polygon)

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | Integer | ID (immer 1) |
| `optimal_height` | Double | Optimale Kranstellflächenhöhe (m ü.NN) |
| `fok` | Double | Fundamentoberkante (m ü.NN) |
| `area_m2` | Double | Fläche (m²) |
| `total_cut` | Double | Gesamtabtrag (m³) |
| `total_fill` | Double | Gesamtauftrag (m³) |

#### 2. `fundamentflaechen` (Polygon)

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | Integer | ID (immer 1) |
| `fok` | Double | Fundamentoberkante (m ü.NN) |
| `depth` | Double | Fundamenttiefe (m) |
| `area_m2` | Double | Fläche (m²) |

#### 3. `auslegerflaechen` (Polygon)

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | Integer | ID (immer 1) |
| `slope_percent` | Double | Verwendete Längsneigung (%) |
| `area_m2` | Double | Fläche (m²) |

#### 4. `rotorflaechen` (Polygon)

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | Integer | ID (immer 1) |
| `height_offset` | Double | Höhendifferenz zu Kran (m) |
| `area_m2` | Double | Fläche (m²) |

#### 5. `schnitte` (LineString)

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | Integer | Fortlaufende ID |
| `type` | String | "Querschnitt XX" oder "Längsprofil XX" |
| `length_m` | Double | Länge des Schnitts (m) |

### HTML-Report

Der HTML-Report enthält:

- **Projektzusammenfassung:** Koordinaten, Datum, Flächen
- **Optimierungsergebnisse:** Optimale Höhe, Volumina
- **Parameter-Übersicht:** Alle verwendeten Eingabeparameter
- **Volumenbilanz-Tabelle:** Cut/Fill für jede Fläche
- **Übersichtskarte:** Wenn verfügbar
- **Geländeschnitte:** Alle generierten Profilbilder

### Profil-Bilder (.png)

Für jedes Profil wird ein PNG-Bild generiert mit:

- **X-Achse:** Distanz entlang Profil (m)
- **Y-Achse:** Höhe (m ü.NN)
- **Linien:**
  - Schwarz: Gelände (DEM)
  - Rot: Kranstellfläche
  - Orange: Auslegerfläche (wenn durchquert)
  - Grün: Blattlagerfläche (wenn durchquert)
  - Grau: Böschungen
- **Legende und Volumeninfo**

---

## Beispiel-Projekt

### Szenario

WEA-Standort bei Koordinaten: **ETRS89 / UTM Zone 32N**
- X: 500000
- Y: 5500000

### Behördliche Vorgaben

- **FOK:** 305.50 m ü.NN (behördlich vorgegeben)
- **Fundamenttiefe:** 3.5m

### Flächengrößen

- **Kranstellfläche:** 35m × 45m = 1575 m²
- **Fundamentfläche:** Ø 22m = 380 m²
- **Auslegerfläche:** 35m × 18m = 630 m²
- **Blattlagerfläche:** 25m × 12m = 300 m²

### Parameter-Einstellungen

```yaml
# Suchbereich
Search Range Below FOK: 0.5 m
Search Range Above FOK: 0.5 m
→ Absoluter Suchbereich: 305.00 - 306.00 m ü.NN

# Kranstellfläche
Gravel Thickness: 0.5 m

# Auslegerfläche
Boom Slope: 5.0 %
Auto-Slope: ✓ aktiviert

# Blattlagerfläche
Height Offset: -0.2 m (etwas tiefer als Kran)

# Optimierung
Height Step: 0.1 m
Slope Angle: 45°
```

### Ergebnis

Nach der Optimierung:

```
✅ Optimale Kranstellflächenhöhe: 305.35 m ü.NN

Offset von FOK: +0.35 m (15 cm über FOK)

Volumenbilanz:
┌────────────────────┬──────────────┬──────────────┬──────────────┐
│ Fläche             │ Cut (m³)     │ Fill (m³)    │ Gesamt (m³)  │
├────────────────────┼──────────────┼──────────────┼──────────────┤
│ Fundament          │ 1,450        │ 38           │ 1,488        │
│ Kranstellfläche    │ 2,850        │ 3,120        │ 5,970        │
│ Auslegerfläche     │ 920          │ 680          │ 1,600        │
│ Blattlagerfläche   │ 540          │ 620          │ 1,160        │
├────────────────────┼──────────────┼──────────────┼──────────────┤
│ GESAMT             │ 5,760        │ 4,458        │ 10,218       │
└────────────────────┴──────────────┴──────────────┴──────────────┘

Netto: +1,302 m³ (mehr Abtrag als Auftrag)

Auslegerfläche:
- Verwendete Neigung: 5.2% (auto-angepasst von 5.0%)
- Geländeneigung: 5.3%
```

**Interpretation:**
- Die optimale Höhe liegt 35cm über FOK
- Es müssen netto 1,302 m³ mehr abgetragen als aufgefüllt werden
- Die Auto-Slope-Funktion hat die Neigung leicht auf 5.2% angepasst
- Die Gesamterdbewegung beträgt 10,218 m³

---

## Troubleshooting

### Problem: "DXF-Import fehlgeschlagen"

**Mögliche Ursachen:**
- DXF-Datei enthält keine LWPOLYLINE oder POLYLINE Entitäten
- DXF ist in einem unbekannten Format
- Koordinatensystem stimmt nicht

**Lösung:**
1. Öffnen Sie DXF in CAD-Software (z.B. AutoCAD, LibreCAD)
2. Prüfen Sie, ob Entitäten vorhanden sind
3. Exportieren Sie als DXF R2010 oder R2013
4. Prüfen Sie Koordinatensystem (sollte metrisch sein)

### Problem: "Validierungsfehler: Fundament nicht innerhalb Kranstellfläche"

**Ursache:**
Das Fundament liegt außerhalb oder berührt nur den Rand der Kranstellfläche.

**Lösung:**
1. Öffnen Sie beide DXF in CAD-Software
2. Prüfen Sie, ob Fundament wirklich innerhalb Kran liegt
3. Erhöhen Sie ggf. die Größe der Kranstellfläche
4. Falls Fundament nur knapp außerhalb: Erhöhen Sie `dxf_tolerance` auf 0.5m

### Problem: "Validierungsfehler: Auslegerfläche berührt Kranstellfläche nicht"

**Ursache:**
Auslegerfläche und Kranstellfläche haben keine gemeinsame Kante (Gap).

**Lösung:**
1. Überprüfen Sie DXFs in CAD-Software
2. Stellen Sie sicher, dass die Flächen sich **berühren** (gemeinsame Kante)
3. Gap sollte < 0.1m sein
4. Falls kleiner Gap: Erhöhen Sie `dxf_tolerance`

### Problem: "Optimierung findet keine Lösung"

**Ursache:**
- Suchbereich zu klein
- DEM-Daten fehlen oder sind fehlerhaft
- Flächen zu groß für Gelände

**Lösung:**
1. Vergrößern Sie Suchbereich (z.B. ±1.0m statt ±0.5m)
2. Prüfen Sie, ob DEM-Download funktioniert hat
3. Prüfen Sie Geländeneigung (sehr steiles Gelände kann problematisch sein)

### Problem: "Auto-Slope weicht stark von manueller Eingabe ab"

**Ursache:**
Das Gelände in der Auslegerfläche hat eine deutlich andere Neigung als die manuelle Eingabe.

**Interpretation:**
- Das ist normal und erwünscht!
- Auto-Slope versucht, sich an Gelände anzupassen
- Wird auf 2-8% begrenzt

**Falls nicht erwünscht:**
- Deaktivieren Sie "Neigung automatisch an Gelände anpassen"
- Manuelle Neigung wird dann verwendet

### Problem: "Profile werden nicht generiert"

**Ursache:**
- Fläche zu klein
- Spacing zu groß
- Fehler in ProfileGenerator

**Lösung:**
1. Reduzieren Sie `cross_profile_spacing` auf 5m
2. Prüfen Sie Logs in QGIS-Konsole
3. Prüfen Sie, ob Ordner `gelaendeschnitte/` erstellt wurde

### Problem: "GeoPackage kann nicht geöffnet werden"

**Ursache:**
- Schreibrechte fehlen
- Antivirensoftware blockiert
- Datei ist korrupt

**Lösung:**
1. Prüfen Sie Schreibrechte im Workspace-Ordner
2. Deaktivieren Sie temporär Antivirensoftware
3. Führen Sie Plugin erneut aus
4. Öffnen Sie GeoPackage manuell: `Layer → Layer hinzufügen → Vektorlayer hinzufügen`

---

## Anhang A: Berechnungsbeispiel

### Gegeben

- **FOK:** 305.50 m ü.NN
- **Fundamenttiefe:** 3.5 m
- **Schotterschicht:** 0.5 m
- **Optimale Kranstellflächenhöhe:** 305.35 m ü.NN
- **Auslegerflächen-Neigung:** 5.0%
- **Rotor-Offset:** -0.2 m

### Höhenberechnung

#### Fundament
```
Fundamentsohle = 305.50 - 3.5 = 302.00 m ü.NN
```

#### Kranstellfläche
```
Planumshöhe = 305.35 - 0.5 = 304.85 m ü.NN
```

#### Auslegerfläche (Beispiel-Pixel bei 10m Distanz)
```
Distanz von Anschlusskante: d = 10.0 m
Zielhöhe = 305.35 - (10.0 × 5.0/100) = 305.35 - 0.5 = 304.85 m ü.NN
```

#### Blattlagerfläche
```
Zielhöhe = 305.35 + (-0.2) = 305.15 m ü.NN
```

### Volumenberechnung (vereinfachtes Beispiel)

Angenommen, Geländehöhe in Kranstellfläche variiert zwischen 304.0 und 306.0 m ü.NN:

**Pixel 1:** Gelände = 306.0 m, Planum = 304.85 m
```
Δh = 306.0 - 304.85 = +1.15 m → Cut
V_cut += 1.15 × 1.0 m² = 1.15 m³
```

**Pixel 2:** Gelände = 304.0 m, Planum = 304.85 m
```
Δh = 304.0 - 304.85 = -0.85 m → Fill
V_fill += 0.85 × 1.0 m² = 0.85 m³
```

Dies wird für alle Pixel in allen Flächen wiederholt und aufsummiert.

---

## Anhang B: DXF-Vorbereitung

### Empfohlene CAD-Software

- **AutoCAD / AutoCAD LT**
- **LibreCAD** (Open Source)
- **QCAD** (Open Source)
- **DraftSight**

### DXF-Erstellungs-Checkliste

**Für jede Fläche:**

1. ☑ Koordinatensystem: ETRS89 / UTM Zone 32N (EPSG:25832)
2. ☑ Einheiten: Meter
3. ☑ Geometrie-Typ: LWPOLYLINE oder POLYLINE
4. ☑ Geschlossene Polylinien (erster = letzter Punkt)
5. ☑ Keine selbstschneidenden Polygone
6. ☑ Keine Löcher oder Inseln
7. ☑ Keine Multi-Part Geometrien
8. ☑ Export-Format: DXF R2010 oder höher

### Räumliche Anordnung prüfen

**In CAD-Software:**
1. Laden Sie alle 4 DXFs in ein Projekt
2. Prüfen Sie visuell:
   - Fundament **innerhalb** Kran
   - Ausleger **berührt** Kran (gemeinsame Kante sichtbar)
   - Rotor **berührt** Kran (gemeinsame Kante sichtbar)
   - Ausleger und Rotor **überlappen nicht**

**Hilfsmittel:**
```
MEASURE DISTANCE (Abstand messen)
- Kran zu Ausleger: sollte 0.0m sein (oder < 0.1m)
- Kran zu Rotor: sollte 0.0m sein (oder < 0.1m)
- Ausleger zu Rotor: sollte > 0.0m sein
```

---

## Anhang C: Glossar

| Begriff | Beschreibung |
|---------|--------------|
| **FOK** | Fundamentoberkante - behördlich vorgegebene Höhe des Fundaments |
| **Planum** | Ebene Oberfläche nach Erdbewegung, vor Schotterauftrag |
| **Cut** | Abtrag - Erdmasse die weggebaggert werden muss |
| **Fill** | Auftrag - Erdmasse die aufgeschüttet werden muss |
| **Böschung** | Geneigte Erdwände um Flächen herum |
| **DEM** | Digital Elevation Model - digitales Höhenmodell |
| **m ü.NN** | Meter über Normalnull |
| **EPSG:25832** | Koordinatenreferenzsystem ETRS89 / UTM Zone 32N |
| **Auto-Slope** | Automatische Anpassung der Neigung an Geländeverlauf |
| **Längsneigung** | Gefälle in Hauptrichtung der Auslegerfläche |
| **Querneigung** | Gefälle quer zur Hauptrichtung (bei Ausleger: 0%) |

---

## Support & Feedback

**GitHub Repository:**
https://github.com/foe05/Wind-Turbine-Earthwork-Calculator

**Issues/Bugs:**
https://github.com/foe05/Wind-Turbine-Earthwork-Calculator/issues

**Dokumentation:**
https://github.com/foe05/Wind-Turbine-Earthwork-Calculator/tree/main/docs

---

**Version:** 2.0
**Letzte Aktualisierung:** November 2025
**Lizenz:** MIT

---

*Dieses Plugin wurde entwickelt für die effiziente Planung von Windenergieanlagen-Baustellen mit Berücksichtigung aller relevanten Flächentypen und Höhenvorgaben.*
