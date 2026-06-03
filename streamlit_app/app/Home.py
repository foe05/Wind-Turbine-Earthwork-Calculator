"""Streamlit-Haupt-App: Wind Turbine Earthwork Calculator."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

import streamlit as st

from app.services.pipeline import (
    PipelineInputs,
    bundle_artifacts_zip,
    run_pipeline,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

st.set_page_config(page_title="WTEC", layout="wide")

st.title("Wind Turbine Earthwork Calculator")
st.caption(
    "Streamlit-Migration des QGIS-Plugins · DXF-Upload → DEM von hoehendaten.de "
    "→ Multi-Surface Cut/Fill → Profile + PDF/HTML-Report."
)

# ---------------------------------------------------------------- Defaults
DEFAULT_FOK = 318.37
DEFAULT_DEPTH = 3.1
DEFAULT_GRAVEL = 0.60
DEFAULT_DEM_BUFFER = 250.0
DEFAULT_CRS = 25832

DEM_CACHE_DIR = os.environ.get("DEM_CACHE_DIR", str(Path.home() / ".wtec" / "dem_cache"))
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", str(Path(tempfile.gettempdir()) / "wtec_uploads"))
EXPORT_DIR = os.environ.get("EXPORT_DIR", str(Path(tempfile.gettempdir()) / "wtec_exports"))
Path(DEM_CACHE_DIR).mkdir(parents=True, exist_ok=True)
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(EXPORT_DIR).mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- Sidebar
with st.sidebar:
    st.header("Konfiguration")

    project_name = st.text_input("Projektname", value="WKA Standort 1")

    st.subheader("Plateau / Fundament")
    fok = st.number_input("FOK [m ü.NN]", value=DEFAULT_FOK, format="%.2f")
    depth = st.number_input("Fundamenttiefe [m]", value=DEFAULT_DEPTH, format="%.2f", min_value=0.0)
    gravel = st.number_input(
        "Schotterdicke Kranstellfläche [m]", value=DEFAULT_GRAVEL, format="%.2f", min_value=0.0
    )

    st.subheader("Höhen-Optimierung")
    optimize = st.checkbox("Kranhöhe automatisch optimieren", value=True)
    objective = st.selectbox(
        "Ziel",
        ["min_total", "min_net", "min_cut"],
        format_func=lambda x: {
            "min_total": "Min. bewegte Masse (Cut+Fill)",
            "min_net": "Massenausgleich (|Cut-Fill| min)",
            "min_cut": "Min. Abtrag",
        }[x],
    )
    col_a, col_b = st.columns(2)
    with col_a:
        range_below = st.number_input("Bereich unter FOK [m]", value=0.5, min_value=0.0, format="%.2f")
        coarse_step = st.number_input("Grob-Schritt [m]", value=0.1, min_value=0.01, format="%.2f")
    with col_b:
        range_above = st.number_input("Bereich über FOK [m]", value=0.5, min_value=0.0, format="%.2f")
        fine_step = st.number_input("Fein-Schritt [m]", value=0.01, min_value=0.001, format="%.3f")

    st.subheader("Geländeschnitte")
    profile_type = st.selectbox("Schnittart", ["cross", "long", "both"], format_func=lambda x: {
        "cross": "Querschnitte",
        "long": "Längsprofile",
        "both": "beide",
    }[x])
    profile_spacing = st.number_input("Abstand [m]", value=10.0, min_value=1.0, format="%.1f")

    st.subheader("DEM-Quelle")
    dem_source = st.radio(
        "DEM-Akquise",
        ["hoehendaten.de (automatisch)", "Eigene GeoTIFF hochladen"],
        index=0,
    )

# ---------------------------------------------------------------- Eingaben
st.header("1) Eingabe-Geometrien")
col1, col2 = st.columns(2)
with col1:
    crane_dxf = st.file_uploader(
        "Kranstellfläche (DXF, Polygon-Outline)",
        type=["dxf"],
        key="crane_dxf",
    )
with col2:
    foundation_dxf = st.file_uploader(
        "Fundamentfläche (DXF, Polygon-Outline)",
        type=["dxf"],
        key="foundation_dxf",
    )

uploaded_dem = None
if dem_source.startswith("Eigene"):
    uploaded_dem = st.file_uploader(
        "DEM (GeoTIFF, EPSG:25832/25833/25834/25835/25836)",
        type=["tif", "tiff"],
        key="dem_tif",
    )

# ---------------------------------------------------------------- Berechnung
st.header("2) Berechnung starten")
run = st.button(
    "Berechnung starten",
    type="primary",
    disabled=not (crane_dxf and foundation_dxf and (uploaded_dem or dem_source.startswith("hoehendaten"))),
)

if run:
    session_id = tempfile.mkdtemp(prefix="wtec_run_", dir=EXPORT_DIR)
    session_dir = Path(session_id)

    crane_path = session_dir / "crane.dxf"
    crane_path.write_bytes(crane_dxf.getbuffer())
    foundation_path = session_dir / "foundation.dxf"
    foundation_path.write_bytes(foundation_dxf.getbuffer())

    dem_local: str | None = None
    if uploaded_dem:
        dem_local = str(session_dir / "user_dem.tif")
        Path(dem_local).write_bytes(uploaded_dem.getbuffer())

    inputs = PipelineInputs(
        project_name=project_name,
        crane_pad_dxf=str(crane_path),
        foundation_dxf=str(foundation_path),
        fok=fok,
        foundation_depth=depth,
        gravel_thickness=gravel,
        output_dir=str(session_dir / "out"),
        crs_epsg=DEFAULT_CRS,
        dem_path=dem_local,
        dem_cache_dir=DEM_CACHE_DIR,
        dem_buffer_m=DEFAULT_DEM_BUFFER,
        optimize_crane_height=optimize,
        search_range_below_fok=range_below,
        search_range_above_fok=range_above,
        coarse_step=coarse_step,
        fine_step=fine_step,
        optimize_objective=objective,
        generate_profiles=True,
        profile_spacing=profile_spacing,
        profile_type=profile_type,
    )

    status = st.status("Berechnung läuft…", expanded=True)
    msgs: list[str] = []

    def progress(m: str):
        msgs.append(m)
        status.write(f"• {m}")

    try:
        out = run_pipeline(inputs, progress=progress)
        status.update(label="Fertig", state="complete")
        st.session_state["last_result"] = out
    except Exception as e:
        status.update(label=f"Fehler: {e}", state="error")
        st.exception(e)

# ---------------------------------------------------------------- Ergebnis
if "last_result" in st.session_state:
    out = st.session_state["last_result"]
    res = out.result
    st.header("3) Ergebnis")

    metric_a, metric_b, metric_c, metric_d = st.columns(4)
    metric_a.metric("Kran-Optimum [m ü.NN]", f"{res.crane_optimum_height:.2f}")
    metric_b.metric("Abtrag gesamt [m³]", f"{res.total_cut_m3:.0f}")
    metric_c.metric("Auftrag gesamt [m³]", f"{res.total_fill_m3:.0f}")
    metric_d.metric("Netto [m³]", f"{res.net_m3:.0f}")

    st.subheader("Pro Surface")
    rows = []
    for stype, r in res.surface_results.items():
        rows.append(
            {
                "Surface": stype.display_name,
                "Plateau [m]": round(r.plateau_height, 2),
                "Fläche [m²]": round(r.platform_area_m2, 0),
                "Abtrag [m³]": round(r.cut_m3, 0),
                "Auftrag [m³]": round(r.fill_m3, 0),
                "Netto [m³]": round(r.net_m3, 0),
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)

    col_map, col_dl = st.columns([2, 1])
    with col_map:
        if Path(out.map_image_path).exists():
            st.image(out.map_image_path, caption="Übersichtskarte")
    with col_dl:
        st.subheader("Downloads")
        with open(out.html_report_path, "rb") as f:
            st.download_button("HTML-Report", f, file_name="report.html", mime="text/html")
        with open(out.json_report_path, "rb") as f:
            st.download_button("JSON-Ergebnis", f, file_name="result.json", mime="application/json")
        # ZIP alles
        zip_path = bundle_artifacts_zip(out.output_dir, Path(out.output_dir).parent / "result_bundle.zip")
        with open(zip_path, "rb") as f:
            st.download_button(
                "Alle Artefakte (ZIP)", f, file_name="result_bundle.zip", mime="application/zip"
            )

    if out.profile_paths:
        st.subheader("Geländeschnitte")
        cols = st.columns(2)
        for i, p in enumerate(out.profile_paths):
            with cols[i % 2]:
                st.image(p["path"], caption=f"{p.get('type', 'Profil')} {p.get('index', i+1):02d}")
