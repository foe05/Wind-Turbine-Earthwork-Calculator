# Landingpage-Prompt für „Kubatur"

Wiederverwendbarer Prompt für ein Frontend-Bau-Tool (v0.dev, Lovable, Bolt,
Claude/Cursor) zur Generierung einer Single-Page-Landingpage für das Produkt
**Kubatur** (https://kubatur.app).

Vor dem Loslassen prüfen:

- **Brand-Name:** „Kubatur" basiert auf der Domain. Falls anders gewollt
  (z. B. „WTEC"), unten Find/Replace.
- **Pilot-Adresse:** `pilot@kubatur.app` ist Platzhalter. Durch echte
  ersetzen.
- **Akzentfarbe:** Petrol/Teal als Default. Falls Corporate-Color
  existiert, austauschen.

---

## Prompt (alles unterhalb dieser Zeile kopierbar)

````markdown
# Landingpage für „Kubatur" — Erdmassenberechnung für Windenergiestandorte

Baue eine moderne, deutschsprachige Single-Page-Landingpage für ein
B2B-SaaS-Produkt namens **Kubatur**. Domain: kubatur.app. Stilvorbild:
Linear, Vercel, Stripe — viel Whitespace, klare Typographie, dezente
Akzentfarbe, keine Stock-Hero-Bilder.

## Stack & Constraints

- **Next.js 14 App Router + Tailwind CSS + shadcn/ui** (oder gleichwertig).
  Falls das Tool nur statisches HTML kann: pure HTML + Tailwind via CDN.
- Mobile first, responsiver Breakpoint bei `md:` und `lg:`.
- Lighthouse-Ziel ≥ 95 in allen Kategorien.
- Keine externen Tracker. Datenschutz-Schein als Footer-Link genügt.
- Sprache: Deutsch. Domänenbegriffe NICHT übersetzen (Kranstellfläche, FOK,
  Böschung, Auslegerfläche, Mass-Haul, etc.).
- Schriften: System-UI-Stack oder Inter über @next/font.
- Dark Mode Pflicht (Toggle in der Nav).

## Marke

- Name: **Kubatur**
- Tagline: „Erdmassen für Windenergie. In Minuten statt Tagen."
- Sub-Tagline: „Browserbasiert. Plugin-Genauigkeit. Lieferfertige Reports."
- Akzentfarbe: tiefes Petrol/Teal (#0E7C7B oder ähnlich). Sekundär:
  warmes Anthrazit (#1f2937), Akzent für Cut: Sand-Orange (#f4a259),
  Akzent für Fill: Wasserblau (#4a90d9).
- Logo-Idee: Schichtende Linien (Geländeprofil) — wenn das Tool das nicht
  kann, reicht Wordmark in Bold.

## Zielgruppe

Planungsbüros für Windenergie, Vermessungsbüros, Tiefbauunternehmen,
Forstdienstleister, technische Projektentwickler. Diese Leute kennen
QGIS und CAD, wollen aber nicht jedes Mal das Plugin installieren,
DEM-Tiles ziehen und Skripte debuggen.

## Seitenstruktur

### 1. Hero
- H1: „Erdmassen für Windenergie. In Minuten statt Tagen."
- Subhead (max. 2 Zeilen): „DXF hoch, FOK rein, Bericht raus. Multi-Surface
  Cut/Fill, Geländeschnitte, 3D-Ansicht und CAD-Export — pixelgenau
  identisch zur QGIS-Plugin-Berechnung."
- Primärer CTA: „Pilot anfragen" → Mailto/Formular
- Sekundärer CTA: „Live ansehen" → https://v1.kubatur.app
- Visuell: Mockup-Slot für einen Screenshot der App (Platzhalter mit
  Polygon-/Karten-Outline genügt). Darunter Trust-Bar: „DGM1 von
  hoehendaten.de · DSGVO-konform · Hosted in Deutschland · Single-Tenant
  pro Kunde".

### 2. „Warum Kubatur" — drei Säulen mit Icons
1. **Browser statt Plugin** — Kein QGIS, keine OSGeo4W-Shell, keine
   Python-Abhängigkeiten. Funktioniert auf jedem Rechner.
2. **Plugin-Parität verifiziert** — Pixel-weise identisch zur etablierten
   QGIS-Plugin-Berechnung (Foundation Cut ±1 m³, Crane Cut/Fill ±2 m³
   gegen Referenz-Fixture).
3. **End-to-End in einem Lauf** — Vom DXF bis zum PDF-Bericht inklusive
   Profilen, 3D-Ansicht, GeoPackage, LandXML und CO₂-Bilanz.

### 3. Feature-Grid „Was Kubatur kann" — 4-Spalten-Grid mit Icons
Gruppen-Header und je 2–3 Bullets pro Karte:

**Eingabe & DEM**
- DXF-Upload für bis zu 6 Surfaces: Kranstellfläche, Fundamentfläche,
  Auslegerfläche, Blattlagerfläche, Holme, Zufahrtsstraße
- Automatischer DEM-Download von hoehendaten.de (DGM1, 1 m Auflösung,
  deutschlandweit)
- CRS-Auto-Erkennung (UTM 32N/33N, Gauss-Krüger als Legacy)

**Berechnung & Optimierung**
- Pixel-genaue Cut/Fill-Bilanz inkl. Slope-/Böschungsanteil
- Höhen-Sweep (coarse → fine) mit drei Zielen: minimale bewegte Masse,
  Massenausgleich, minimaler Abtrag
- Boom-Slope-Sweep, Rotor-Offset-Sweep, Road-Slope-Sweep
- Rotation-Optimierung — beste Plattform-Ausrichtung gegen Höhenlinien
- Placement-Constraints — Mindestabstände zu Wohnen, Straßen,
  Schutzgebieten
- Monte-Carlo-Unsicherheitsanalyse mit Latin Hypercube Sampling und
  Sensitivitäts-Ranking

**Berichte & Visualisierung**
- HTML- und PDF-Bericht mit Tabellen, Übersichtskarte und eingebetteten
  Geländeschnitten
- Quer- und Längsprofile als hochauflösende PNGs
- Interaktive 3D-Ansicht im Browser (Three.js, DEM-Hillshade + farbcodierte
  Surface-Meshes)
- Mass-Haul-Diagramm mit Massenausgleichspunkten und Free-Haul/Overhaul-Split
- Side-by-Side-Vergleich mehrerer Planungsvarianten

**Multi-Site & Park**
- Vergleich mehrerer Standorte im selben Park
- Park-weite Material-Transport-Optimierung (LP/MILP über
  scipy.optimize)
- Excel-Export (XLSX) und HTML-Park-Report

**Geotechnik & Nachhaltigkeit**
- Bauphasen-Verteilung — Massen, Kosten und CO₂ je Phase
  (Wegebau → Kranstellfläche → Fundament → Restarbeiten)
- Bodenschichten-Aufteilung — Mutterboden, Frostschutz, Schottertragschicht
  (DIN 18196 / RStO 12)
- Bodenstabilisierung — Kalkdosierung je Bodenart, Schotterdicke nach
  Ev2-Lookup
- BGR-Bodendaten-Lookup (BÜK200) per Klick auf die Karte
- CO₂-Bilanz (Aushub, Transport, Beton, Stahl) mit konfigurierbaren
  Emissionsfaktoren

**Exporte für CAD, BIM und Maschinensteuerung**
- GeoPackage (alle Surfaces + Attribute) für QGIS und Civil 3D
- LandXML 1.2 TIN-Surfaces für Trimble, Topcon, Leica
- Slope-Stability-XML für Slide2, GeoStudio SLOPE/W, Plaxis-LE
- 3D-Mesh als OBJ, STL und glTF — direkt in Blender, Cesium oder
  Sketchfab nutzbar

### 4. Workflow-Sektion „So läuft eine Berechnung"
Horizontaler Step-Indikator mit fünf Schritten, jeder mit kurzem Text und
ggf. kleinem Mockup-Slot:

1. **DXF hochladen** — Pflicht: Kranstellfläche + Fundamentfläche.
   Optional: Ausleger, Blattlager, Holme, Zufahrt.
2. **Parameter setzen** — FOK, Fundamenttiefe, Schotterdicke,
   Optimierungs-Ziel, Sweep-Bereiche.
3. **Berechnen** — DEM wird automatisch gezogen, Cut/Fill und alle
   Sweeps laufen pixelweise auf dem Mosaik.
4. **Live ansehen** — Karte, Tabellen je Surface, Profile, 3D-Modell.
5. **Bericht downloaden** — HTML, PDF, GeoPackage, LandXML, glTF, ZIP.

### 5. Vergleichstabelle (optional, aber stark) — „Kubatur vs. heutiger Workflow"
| Schritt | Heute | Mit Kubatur |
|---|---|---|
| DXF einlesen | QGIS + ezdxf-Workarounds | Drag & Drop im Browser |
| DEM ziehen | hoehendaten.de-API manuell, Tile-Mosaik | Automatisch im Hintergrund |
| Cut/Fill rechnen | Excel-Tabellen, Plugin-Tabs | Ein Klick, pixelgenau |
| Profile rendern | matplotlib-Script, Output sortieren | Querschnitte und Längsprofile inklusive |
| Bericht zusammenbauen | manuell in Word/PowerPoint | PDF und GeoPackage in ein ZIP |
| **Zeit** | **1–2 Personentage** | **5–15 Minuten** |

### 6. Use-Cases (3 Karten)
- **Einzelner WEA-Standort** — Optimale Kranstellflächen-Höhe finden,
  Massenausgleich erreichen, Geländeschnitte für den Bauantrag.
- **Park-Optimierung** — Mehrere Standorte vergleichen, Material zwischen
  Cut- und Fill-Sites verschieben, Park-weite Kosten minimieren.
- **Bauphasen & Reporting** — Massen, Kosten und CO₂ je Phase
  visualisieren, Reports inkl. LandXML an die Bauleitung übergeben.

### 7. Trust & Compliance
- **Single-Tenant pro Kunde** — eigene Instanz, keine geteilte
  Datenbank.
- **Hosting in Deutschland** (Hetzner) — TLS via Let's Encrypt,
  Authentifizierung über Reverse Proxy.
- **DSGVO-konform** — keine PII in Telemetrie, keine externen Tracker.
- **Offen für Audit** — Berechnungslogik ist als QGIS-Plugin
  open-source dokumentiert (Link zu GitHub-Repo).

### 8. FAQ — 5–7 Items im Accordion
- „Welche DEM-Quellen werden unterstützt?" — DGM1 von hoehendaten.de
  deutschlandweit, plus Upload eigener GeoTIFFs in EPSG:25832–25836.
- „Wie genau ist die Berechnung?" — Pixel-weise identisch zum
  QGIS-Plugin-Algorithmus (±2 m³ gegen Referenz-Fixture).
- „Welche CAD-Formate kommen raus?" — GeoPackage, LandXML 1.2,
  glTF, OBJ, STL, PDF, HTML, XLSX.
- „Funktioniert es ohne QGIS?" — Ja, komplett browserbasiert.
- „Wie steht es um Datenschutz?" — Single-Tenant, Hosting in
  Deutschland, keine Tracker.
- „Kann ich mehrere Standorte parallel rechnen?" — Ja, plus
  park-weite Material-Transport-Optimierung.
- „Was kostet es?" — Pilot-Phase laufend; Preise auf Anfrage.

### 9. Final CTA
- H2: „Pilot starten."
- Body: „Du schickst zwei DXFs, wir rechnen den ersten Standort
  gemeinsam. Kein Kreditkartenzwang, kein Account nötig."
- Button: „Pilot anfragen" → Mailto an `pilot@kubatur.app` mit
  vorausgefülltem Betreff.

### 10. Footer
- Spalten: Produkt (Features, Live-Demo, Pricing-Anfrage), Ressourcen
  (GitHub, Dokumentation, Changelog), Rechtliches (Impressum,
  Datenschutz, AGB), Kontakt (E-Mail, optional XING/LinkedIn).
- Copyright: „© 2026 Kubatur — gebaut auf Basis des QGIS-Plugins
  Wind Turbine Earthwork Calculator."

## Tone of Voice

- Faktisch, zahlenlastig, ohne Marketing-Geblubber.
- „Wir sparen Tage Arbeit" steht NICHT in Konjunktiv, sondern: „1–2
  Personentage werden 5–15 Minuten".
- Domänenwortschatz bewusst deutsch lassen — die Zielgruppe will das so.
- Keine Buzzwords („KI-gestützt", „revolutionär", „intelligent"). Stattdessen:
  „pixelweise", „verifiziert", „identisch zum Plugin".

## Output

- `app/` mit Next.js-Routing (Single Page auf `/`)
- `components/` für Hero, FeatureGrid, Workflow, ComparisonTable,
  UseCases, Trust, FAQ, CTA, Footer, ThemeToggle
- `tailwind.config.ts` mit der oben definierten Farbpalette
- `README.md` mit `npm run dev` / `npm run build`
- Alle Texte fest verdrahtet (keine CMS-Integration nötig)
- Mockup-Bilder als `<div>`-Platzhalter mit Beschriftung „Screenshot
  folgt — Polygonansicht / 3D-Modell / Bericht"

Wenn ein Schritt unklar ist: lieber konservativ entscheiden und unten
in einem `NOTES.md` festhalten, statt sich Inhalte auszudenken.
````
