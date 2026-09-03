# Weitermachen

Stand: 2026-09-03. Betrifft `streamlit_app/`.

Diese Datei ist für den kalten Wiedereinstieg gedacht: was zuletzt passiert ist,
was offen liegt und warum, plus das Betriebswissen, das man sonst jedes Mal neu
zusammensuchen muss.

---

## 1) Was zuletzt passiert ist (2026-08-27)

Sieben Commits auf `v3-foundation`, alle gepusht:

| Commit | Inhalt |
|---|---|
| `a6f9e7b` | PostGIS-Image `16-3.4` → `16-3.5` (PostGIS 3.4.3 → 3.5.2, PG 16.4 → 16.9) |
| `47a483a` | Abhängigkeiten über `requirements.lock` gepinnt, `.dockerignore` ergänzt |
| `257092e` | Persistenz-Schema: `projects` → `runs` → `run_surfaces` / `run_artifacts` |
| `5bbe518` | `run_pipeline()` schreibt jeden Lauf mit |
| `a94194b` | Seite 6 „Laufhistorie" |
| `e5aa225` | Vorabprüfung vor DXF-Import, DEM-Download und Sweep |
| `50eb29f` | Variantenvergleich übernimmt gespeicherte Läufe |

Ausgangslage war, dass `CLAUDE.md` seit jeher „PostgreSQL + PostGIS (Projekte,
Jobs, Ergebnisse)" als Persistenz führte, es die aber nie gab: Der Container
lief, `DATABASE_URL` war gesetzt, und kein Modul hat die Variable je gelesen.
Ebenso war `core/validation.py` portiert, getestet und wurde nirgends aufgerufen.
Beides ist jetzt verdrahtet.

Testsuite: **170 passed** (vorher 135 passed / 5 skipped).

### Entscheidungen, die man kennen sollte

**Geometrien liegen in EPSG:4326, nicht im Arbeits-CRS.** Ein fester SRID hält
Läufe aus verschiedenen UTM-Zonen über einen gemeinsamen GiST-Index abfragbar;
mit gemischten SRIDs in einer Spalte scheitert schon jedes `ST_Intersects`. Das
Arbeits-CRS steht je Lauf in `runs.crs_epsg`, die Transformation macht
`db.to_storage_geometry()`. An der 4326-Kopie hängt keine Maßzahl — alle Volumen
und Flächen sind im nativen CRS vorberechnet und als Zahlen gespeichert.

**Kein `organization_id`.** Solange Single-Tenant gilt, wäre die Spalte tote
Fracht. Für Multi-Tenancy ist `projects` der eine Anker, an dem der FK hängt.

**`text` + `CHECK` statt nativer PG-Enums**, damit neue Flächentypen eine
gewöhnliche Constraint-Migration bleiben. Die Werte kommen aus dem
`SurfaceType`-Enum des Rechenkerns, damit Schema und Kern nicht abdriften.

**Die Mitschrift ist Beiwerk, nicht Voraussetzung.** Ohne `DATABASE_URL` ist der
`RunRecorder` ein No-op, ein DB-Ausfall loggt eine Warnung und legt ihn still.
Die Pipeline ist zum Rechnen da; eine fertige Rechnung darf nicht an der
Datenbank verloren gehen.

---

## 2) Git-Situation — bitte vor dem nächsten Push lesen

`v3-foundation` wird per **Squash-Merge** nach `main` gebracht. Das ist jetzt
zweimal passiert (`96b0a02` = PR #52, `e53d89d` = PR #53). Folge:

- `origin/main` enthält den Branch-Inhalt **vollständig und byte-identisch**
  (`git diff origin/main v3-foundation` ist leer), aber als jeweils einen Commit.
- Ein normales `git rebase origin/main` würde alle Branch-Commits auf ein `main`
  replayen, das ihren Inhalt schon hat. Patch-ID-Erkennung greift bei
  Squash-Merges nicht → Konflikte am Fließband.

**Richtig ist `--onto`**, das nur die noch nicht gemergten Commits übernimmt:

```bash
git branch backup/v3-foundation-$(date +%Y%m%d) v3-foundation   # erst sichern
git rebase --onto origin/main <letzter-gemergter-commit> v3-foundation
git push --force-with-lease=v3-foundation:<alter-remote-sha> origin v3-foundation
```

Das verwirft die alten Einzelcommits **auf der Branch** — ihr Inhalt steckt im
Squash-Commit auf `main`. Nur machen, wenn die Branch niemand anderem gehört.

Alternative, die das Muster beendet: nach dem Merge `v3-foundation` löschen und
für den nächsten Arbeitsblock frisch von `main` abzweigen.

---

## 3) Offen — nach Hebelwirkung

### 3.1 Background-Jobs *(der große Brocken)*

`run_pipeline()` läuft inline im Streamlit-Skript. Schließt jemand den Tab oder
greift ein Reverse-Proxy-Timeout, ist die Rechnung weg.

Seit der Mitschrift hat das ein **sichtbares Symptom**: verwaiste Zeilen mit
`status='running'`, die nie fertig werden. Die Historien-Seite warnt bereits
explizit davor (`pages/6_Laufhistorie.py`, Zweig `status == "running"`). Damit
ist das Problem messbar, statt nur behauptet.

`streamlit_app/CLAUDE.md` nennt `dramatiq` oder `rq` als Option „bei Bedarf" —
der Bedarf gilt als belegt. Zu klären:

- Worker im selben Compose-Stack oder separater Container?
- Redis kommt dazu (im dockeradmin-Stack läuft schon einer, aber Single-Tenant
  heißt eigener).
- `RunRecorder` passt schon: Der Job schreibt `running` → `succeeded`/`failed`,
  die Seite pollt auf den Status statt auf ein Funktionsergebnis zu warten.
- Aufräumjob für Läufe, die länger als X Stunden auf `running` stehen.

**Nicht nebenbei bauen** — das will geplant werden.

### 3.2 Exakte Böschungsgeometrie

`core/slope_volume.py` ist eine Näherung: randdiskretisiertes Δh/tan(α)-Band,
laut Repo-Doku 5–10 % typische Abweichung. Die geometrisch exakte
Böschungspolygon-Konstruktion existiert nur im QGIS-Plugin
(`windturbine_earthwork_calculator_v2/`).

Das ist der einzige offene Punkt, bei dem es um **Richtigkeit** geht und nicht um
Komfort: Bei Ausschreibungsmassen sind 5–10 % auf den Böschungsanteil bares Geld.
Wenn das Tool Angebotsmassen liefern soll, gehört das vorgezogen.

Portierung heißt: QGIS-API ersetzen (shapely statt `QgsGeometry`), und die
wea45-Regression muss grün bleiben — die Erwartungswerte ändern sich dadurch
allerdings, das ist Teil der Aufgabe und braucht eine bewusste Neufestlegung.

### 3.3 Was die Datenbank fast geschenkt hergibt

- **Doppelte Läufe erkennen.** `runs.inputs` ist ein JSONB mit allen Parametern.
  Ein Hash darüber erkennt, ob exakt dieselbe Rechnung schon lief — statt sie zu
  wiederholen, könnte die App den alten Lauf anbieten.
- **Betriebsübersicht.** Aus `started_at`/`finished_at`/`status` fällt eine
  Auswertung heraus (Dauer, Fehlerquote, welche Eingaben oft scheitern), ohne
  dass irgendwo Instrumentierung nachgerüstet werden muss.

### 3.4 Aufbewahrung

Artefakte und DEM-Cache wachsen unbegrenzt. Die DB hält nur Pfade — die Historie
zeigt fehlende Dateien bereits als `🚫` an, aber niemand räumt auf. `dem_cache`
lag zuletzt bei ~10 MB, das ist noch kein Druck, wächst aber monoton. Der
SaaS-Plan (§7) nennt 12 Monate Aufbewahrung.

### 3.5 Kleinkram

- `use_container_width` ist in Streamlit 1.62 abgekündigt (Entfernung war für
  Ende 2025 angesetzt). Offen in `app/Home.py:253` und
  `app/pages/2_Multi_Site.py:97` → `width="stretch"`. Zwei Zeilen.
- Externer Schotter im Variantenvergleich bleibt manuell. Die Pipeline ermittelt
  ihn nicht; ihn aus Schotterdicke × Fläche zu schätzen wäre eine erfundene Zahl
  in einer Tabelle, aus der Angebotsmassen abgelesen werden. Wenn er automatisch
  kommen soll, muss ihn der Rechenkern liefern, nicht die Anzeige.

### 3.6 Ausdrücklich nicht jetzt

**Multi-Tenancy / Row-Level-Security** aus `PLAN_SAAS_INTEGRATION.md` §7 und
Etappe 3. Solange Läufe an einer Browser-Session hängen, ist RLS das Lösen des
falschen Problems. Zur Warnung: Der Plan baute auf „zusätzlich zur heutigen
PostGIS-Welt" auf — diese Welt gab es beim Schreiben des Plans nicht, seine
Aufwandsschätzung für Etappe 3 ist entsprechend zu optimistisch.

---

## 4) Betriebswissen

### Tests

```bash
cd streamlit_app
docker compose -f docker-compose.yml -f docker-compose.prod.yml build app

# Volle Suite. Der Mount ist Pflicht, sonst werden 5 Tests still uebersprungen:
# tests/test_e2e_pipeline.py sucht wea45mit3d.zip unter
# /windturbine_earthwork_calculator_v2 (Path(__file__).parent.parent.parent).
docker run --rm -e PYTHONPATH=/app \
  -v "$PWD/tests:/app/tests:ro" \
  -v "$PWD/../windturbine_earthwork_calculator_v2:/windturbine_earthwork_calculator_v2:ro" \
  streamlit_app-app:latest \
  sh -c "pip install -q pytest && cd /app && python -m pytest -q"
```

**Falle:** Wer nur `tests/` mountet, testet die App-Version *aus dem Image*, nicht
die editierten Dateien. Nach Änderungen an `app/` also neu bauen — oder `app/`
zusätzlich mounten.

### Migrationen

```bash
docker run --rm --network streamlit_app_default \
  -e DATABASE_URL='postgresql+psycopg://wtec:wtec@db:5432/wtec' -w /app \
  streamlit_app-app:latest alembic upgrade head

# Trockenlauf ohne DB-Zugriff:  alembic upgrade head --sql
# Modelle vs. Migrationen:      alembic check
```

`migrations/env.py` setzt `search_path` auf `public` und filtert reflektierte
Fremdtabellen. Ohne das schlägt `--autogenerate` vor, die rund vierzig
tiger-Tabellen von `postgis_tiger_geocoder` zu löschen — die liegen über den
`search_path` scheinbar in `public`. Preis des Filters: eine wirklich entfernte
eigene Tabelle wird nicht automatisch erkannt, deren `drop_table` schreibt man
von Hand.

### Läufe zum Ausprobieren erzeugen

Die E2E-Tests mit gesetzter `DATABASE_URL` laufen lassen — sie schreiben zwei
echte Läufe in die DB. Danach aufräumen, sonst stehen Zeilen mit Pfaden nach
`/tmp/pytest-*` in der Produktionsdatenbank:

```bash
docker exec wtec-db psql -U wtec -d wtec -c "delete from projects where name like 'wea45 E2E%';"
```

### Was die Zahlen sein müssen

Autoritative Regression aus `wea45mit3d.zip`: Fundament-Cut **693 m³ ±1**,
Kranstellfläche Cut **5280 ±2** / Fill **1763 ±2**. Beim Schreibtest der
Persistenz kam Fundament-Cut mit 693,2 m³ in der DB an — daran erkennt man, dass
die gespeicherten Werte die echten sind und nicht irgendwo unterwegs verfälscht
wurden.

### Lokal geprüfte Umgebung

`wtec-db` läuft auf `postgis/postgis:16-3.5` (PostGIS 3.5.2, PG 16.9), `wtec-app`
auf dem lokal gebauten `streamlit_app-app`. Beide im Compose-Projekt
`streamlit_app`, Netz `streamlit_app_default`, Public-Traffic über den Nginx
Proxy Manager auf `v1.kubatur.app` (dort greift eine Access List, ein 401 ist
also normal und kein App-Fehler).

**PG 16.9, nicht 16.15:** Das PostGIS-Image basiert auf `postgres:16-bullseye`,
und der Bullseye-Zweig wird nicht mehr gepflegt. Die Lücke schließt nur ein
Wechsel auf ein Bookworm/Trixie-basiertes Image (PG 17/18 + PostGIS 3.6) — und
das ist dann ein echtes Major-Upgrade mit Dump/Restore.
