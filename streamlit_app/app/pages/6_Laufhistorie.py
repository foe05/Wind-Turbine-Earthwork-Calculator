"""Streamlit-Page: gespeicherte Berechnungsläufe durchsehen."""

import json
from pathlib import Path

import folium
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError
from streamlit_folium import st_folium

from app.services import history

st.set_page_config(page_title="Laufhistorie", layout="wide")
st.title("Laufhistorie")
st.caption("Gespeicherte Berechnungsläufe: Massen, Flächen und erzeugte Dateien.")

STATUS_ICON = {"succeeded": "✅", "failed": "❌", "running": "⏳"}

SURFACE_LABEL = {
    "kranstellflaeche": "Kranstellfläche",
    "fundamentflaeche": "Fundamentfläche",
    "auslegerflaeche": "Auslegerfläche",
    "rotorflaeche": "Blattlagerfläche",
    "zufahrt": "Zufahrtsstraße",
    "holme": "Holme",
}

SURFACE_COLOR = {
    "kranstellflaeche": "#1f77b4",
    "fundamentflaeche": "#d62728",
    "auslegerflaeche": "#2ca02c",
    "rotorflaeche": "#ff7f0e",
    "zufahrt": "#9467bd",
    "holme": "#8c564b",
}

if not history.is_available():
    st.info(
        "Keine Datenbank konfiguriert — es wird nichts mitgeschrieben. "
        "Setze `DATABASE_URL`, damit Läufe hier auftauchen."
    )
    st.stop()

try:
    projects = history.list_projects()
except SQLAlchemyError as exc:
    st.error(f"Datenbank nicht erreichbar: {exc}")
    st.stop()

if not projects:
    st.info("Noch keine Läufe gespeichert. Starte eine Berechnung auf der Startseite.")
    st.stop()

# ---------------------------------------------------------------- Projekt

labels = {
    p["id"]: f"{p['name']} — {p['run_count']} Lauf/Läufe"
    + (f", zuletzt {p['last_run']:%d.%m.%Y %H:%M}" if p["last_run"] else "")
    for p in projects
}
project_id = st.selectbox(
    "Projekt", options=list(labels), format_func=lambda pid: labels[pid]
)

runs = history.list_runs(project_id)
if not runs:
    st.info("Für dieses Projekt sind keine Läufe gespeichert.")
    st.stop()

st.subheader("Läufe")
st.dataframe(
    [
        {
            "": STATUS_ICON.get(r["status"], "•"),
            "Start": r["started_at"],
            "Dauer [s]": (
                round((r["finished_at"] - r["started_at"]).total_seconds(), 1)
                if r["finished_at"]
                else None
            ),
            "Kran-Optimum [m ü.NN]": r["crane_optimum_height"],
            "Abtrag [m³]": r["total_cut_m3"],
            "Auftrag [m³]": r["total_fill_m3"],
            "Netto [m³]": r["net_m3"],
            "EPSG": r["crs_epsg"],
            "Fehler": r["error"],
        }
        for r in runs
    ],
    width="stretch",
    hide_index=True,
)

# ---------------------------------------------------------------- Detail

def _run_label(run_id):
    r = next(x for x in runs if x["id"] == run_id)
    return f"{STATUS_ICON.get(r['status'], '•')} {r['started_at']:%d.%m.%Y %H:%M:%S}"


run_id = st.selectbox(
    "Lauf im Detail", options=[r["id"] for r in runs], format_func=_run_label
)

run = history.load_run(run_id)
if run is None:
    st.warning("Dieser Lauf existiert nicht mehr.")
    st.stop()

st.subheader("Ergebnis")

if run["status"] == "failed":
    st.error(run["error"] or "Der Lauf ist gescheitert.")
elif run["status"] == "running":
    st.warning(
        "Dieser Lauf steht noch auf 'running'. Entweder rechnet er gerade, "
        "oder der Prozess ist abgebrochen, bevor das Ergebnis geschrieben wurde."
    )

col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric(
    "Kran-Optimum [m ü.NN]",
    f"{run['crane_optimum_height']:.2f}" if run["crane_optimum_height"] is not None else "—",
)
col_b.metric(
    "Abtrag gesamt [m³]", f"{run['total_cut_m3']:.0f}" if run["total_cut_m3"] is not None else "—"
)
col_c.metric(
    "Auftrag gesamt [m³]", f"{run['total_fill_m3']:.0f}" if run["total_fill_m3"] is not None else "—"
)
col_d.metric("Netto [m³]", f"{run['net_m3']:.0f}" if run["net_m3"] is not None else "—")

# ---------------------------------------------------------------- Flächen

if run["surfaces"]:
    st.subheader("Flächen")
    st.dataframe(
        [
            {
                "Fläche": SURFACE_LABEL.get(s["surface_type"], s["surface_type"]),
                "Planum [m ü.NN]": s["plateau_height"],
                "Abtrag [m³]": s["cut_m3"],
                "Auftrag [m³]": s["fill_m3"],
                "Fläche [m²]": s["platform_area_m2"],
                "Gelände min/max [m]": f"{s['terrain_min']:.2f} / {s['terrain_max']:.2f}",
                "Böschung Ab-/Auftrag [m³]": (
                    f"{s['slope_cut_m3']:.0f} / {s['slope_fill_m3']:.0f}"
                    if s["slope_cut_m3"] is not None
                    else "—"
                ),
                "Pixel": s["num_pixels"],
            }
            for s in run["surfaces"]
        ],
        width="stretch",
        hide_index=True,
    )

    # Geometrien liegen in EPSG:4326 — direkt kartierbar, ohne Transformation.
    geo_surfaces = [s for s in run["surfaces"] if s["geojson"]]
    if geo_surfaces:
        fmap = folium.Map(tiles="OpenStreetMap")
        bounds = []
        for s in geo_surfaces:
            gj = json.loads(s["geojson"])
            color = SURFACE_COLOR.get(s["surface_type"], "#333333")
            folium.GeoJson(
                gj,
                name=SURFACE_LABEL.get(s["surface_type"], s["surface_type"]),
                style_function=lambda _f, c=color: {
                    "color": c,
                    "weight": 2,
                    "fillColor": c,
                    "fillOpacity": 0.25,
                },
                tooltip=SURFACE_LABEL.get(s["surface_type"], s["surface_type"]),
            ).add_to(fmap)
            for polygon in gj.get("coordinates", []):
                for ring in polygon:
                    bounds.extend([(lat, lon) for lon, lat in ring])
        if bounds:
            fmap.fit_bounds(
                [
                    [min(b[0] for b in bounds), min(b[1] for b in bounds)],
                    [max(b[0] for b in bounds), max(b[1] for b in bounds)],
                ]
            )
        folium.LayerControl().add_to(fmap)
        st_folium(fmap, height=420, use_container_width=True, returned_objects=[])

# ---------------------------------------------------------------- Artefakte

if run["artifacts"]:
    st.subheader("Erzeugte Dateien")
    st.caption(
        "Die Datenbank hält die Pfade, nicht die Dateien. Ältere Läufe können "
        "auf Dateien zeigen, die inzwischen aufgeräumt wurden."
    )
    rows = []
    for a in run["artifacts"]:
        exists = Path(a["path"]).exists()
        rows.append(
            {
                "": "📄" if exists else "🚫",
                "Art": a["kind"],
                "Pfad": a["path"],
                "Info": ", ".join(f"{k}={v}" for k, v in (a["meta"] or {}).items()) or "",
            }
        )
    st.dataframe(rows, width="stretch", hide_index=True)

    missing = sum(1 for a in run["artifacts"] if not Path(a["path"]).exists())
    if missing:
        st.warning(f"{missing} von {len(run['artifacts'])} Dateien sind nicht mehr vorhanden.")

# ---------------------------------------------------------------- Rest

with st.expander("Eingabeparameter"):
    st.json(run["inputs"])

for label, key in (
    ("CO₂-Bilanz", "co2_breakdown"),
    ("Bauphasen", "phase_plan"),
    ("Bodenschichten", "strata_breakdown"),
):
    if run.get(key):
        with st.expander(label):
            st.json(run[key])

with st.expander("Lauf löschen"):
    st.caption(
        "Entfernt den Lauf mit Flächen und Artefakt-Einträgen aus der Datenbank. "
        "Die Dateien im Ausgabeordner bleiben liegen."
    )
    if st.checkbox("Ja, diesen Lauf löschen", key=f"del_{run_id}"):
        if st.button("Endgültig löschen", type="primary"):
            if history.delete_run(run_id):
                st.success("Lauf gelöscht.")
                st.rerun()
            else:
                st.warning("Der Lauf war bereits weg.")
