"""Streamlit-Page: Multi-Site Vergleich + optionale Park-Optimierung."""

import tempfile
from pathlib import Path

import streamlit as st
from shapely.geometry import Point

from app.core.earthwork import CutFillResult
from app.core.multi_site_report import export_multisite_xlsx, render_multisite_html
from app.core.multi_surface import MultiSurfaceResult, SurfaceType
from app.core.park_optimizer import (
    ParkOptimizer,
    SiteCandidate,
    SiteEarthwork,
    SiteWithCandidates,
    TransportConfig,
)
from app.core.site_data import MultiSiteProject, SiteData

st.set_page_config(page_title="Multi-Site Vergleich", layout="wide")
st.title("Multi-Site Vergleich & Park-Optimierung")

if "ms_project" not in st.session_state:
    st.session_state["ms_project"] = MultiSiteProject(project_name="Park")

project: MultiSiteProject = st.session_state["ms_project"]

project_name = st.text_input("Park-Name", value=project.project_name)
project.project_name = project_name

with st.expander("Standort hinzufügen", expanded=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        site_id = st.text_input("Site-ID", value=f"WEA{len(project.sites) + 1:02d}")
        site_name = st.text_input("Name", value=f"Standort {len(project.sites) + 1}")
        x = st.number_input("X (UTM 32N, m)", value=492000.0)
        y = st.number_input("Y (UTM 32N, m)", value=5702000.0)
    with c2:
        fok = st.number_input("FOK [m ü.NN]", value=318.0)
        crane_h = st.number_input("Kranhöhe Optimum [m ü.NN]", value=319.87)
        cut = st.number_input("Gesamt-Cut [m³]", value=6500.0, min_value=0.0)
        fill = st.number_input("Gesamt-Fill [m³]", value=2400.0, min_value=0.0)
    with c3:
        cost = st.number_input("Kosten [€]", value=50000.0, min_value=0.0)
        area_crane = st.number_input("Kran-Fläche [m²]", value=2500.0, min_value=1.0)
        area_found = st.number_input("Fundament-Fläche [m²]", value=200.0, min_value=1.0)
    if st.button("Standort hinzufügen", type="primary"):
        res = MultiSurfaceResult(
            crane_optimum_height=crane_h,
            fok=fok,
            foundation_depth=3.1,
            gravel_thickness=0.6,
            surface_results={
                SurfaceType.CRANE_PAD: CutFillResult(crane_h - 0.6, cut * 0.85, fill * 0.85, area_crane, 0, 0, 0, 0),
                SurfaceType.FOUNDATION: CutFillResult(fok - 3.1, cut * 0.15, fill * 0.15, area_found, 0, 0, 0, 0),
            },
        )
        sd = SiteData(
            site_id=site_id,
            site_name=site_name,
            location=Point(x, y),
            result=res,
            costs={"cost_total": cost},
        )
        try:
            project.add_site(sd)
            st.success(f"{site_name} hinzugefügt.")
            st.rerun()
        except ValueError as e:
            st.error(str(e))

if project.sites:
    st.subheader(f"Park-Übersicht ({project.site_count} Standorte)")
    summary = project.summary()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Standorte", summary["site_count"])
    c2.metric("Gesamt-Cut [m³]", f"{summary['total_cut_m3']:,.0f}")
    c3.metric("Gesamt-Fill [m³]", f"{summary['total_fill_m3']:,.0f}")
    c4.metric("Gesamt-Kosten [€]", f"{summary['total_cost_eur']:,.0f}")

    rows = []
    for s in project.sites:
        rows.append(
            {
                "ID": s.site_id,
                "Name": s.site_name,
                "X": round(s.location.x, 0),
                "Y": round(s.location.y, 0),
                "Kran [m ü.NN]": round(s.crane_height, 2),
                "Cut [m³]": round(s.total_cut, 0),
                "Fill [m³]": round(s.total_fill, 0),
                "Netto [m³]": round(s.net_volume, 0),
                "Kosten [€]": round(s.total_cost, 0),
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.subheader("Park-Optimierung (Material-Transport)")
    if st.checkbox("Optimierung aktivieren", value=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            cost_km = st.number_input("Transport [€/m³·km]", value=0.20, format="%.2f")
        with col2:
            dump_cost = st.number_input("Deponie [€/m³]", value=8.0, format="%.2f")
        with col3:
            gravel_cost = st.number_input("Schotter-Import [€/m³]", value=15.0, format="%.2f")
        max_dist = st.number_input("Max. Transportdistanz [km]", value=5.0, min_value=0.0, format="%.1f")

        cfg = TransportConfig(
            cost_per_m3_km=cost_km,
            dump_cost_per_m3=dump_cost,
            external_gravel_cost_per_m3=gravel_cost,
            max_distance_km=max_dist if max_dist > 0 else None,
        )
        if st.button("LP-Optimierung starten"):
            sites_e = [
                SiteEarthwork(
                    s.site_id,
                    s.location.x,
                    s.location.y,
                    cut_excess_m3=max(0.0, s.net_volume),
                    fill_need_m3=max(0.0, -s.net_volume),
                )
                for s in project.sites
            ]
            sol = ParkOptimizer(cfg).solve(sites_e)
            st.write(f"Solver: {sol.solver_status}")
            st.metric("Transport-Kosten [€]", f"{sol.total_transport_eur:,.0f}")
            st.metric("Deponie Rest [€]", f"{sol.total_dump_eur:,.0f}")
            st.metric("Schotter-Import Rest [€]", f"{sol.total_gravel_eur:,.0f}")
            st.metric("Baseline [€]", f"{sol.baseline_cost_eur:,.0f}")
            st.metric("Ersparnis [€]", f"{sol.savings_eur:,.0f}")
            if sol.flows:
                st.write("Materialflüsse:")
                st.dataframe(
                    [
                        {
                            "Von": f.from_site,
                            "Nach": f.to_site,
                            "Volumen [m³]": round(f.volume_m3, 0),
                            "Distanz [km]": round(f.distance_km, 2),
                            "Kosten [€]": round(f.transport_cost_eur, 0),
                        }
                        for f in sol.flows
                    ],
                    hide_index=True,
                )
            st.session_state["last_park_solution"] = sol

    # Downloads
    st.subheader("Downloads")
    tmpdir = tempfile.mkdtemp(prefix="multisite_")
    html_path = Path(tmpdir) / "multisite.html"
    xlsx_path = Path(tmpdir) / "multisite.xlsx"
    render_multisite_html(project, str(html_path), park_solution=st.session_state.get("last_park_solution"))
    export_multisite_xlsx(project, str(xlsx_path))
    with open(html_path, "rb") as f:
        st.download_button("HTML-Report", f, file_name=f"{project.project_name}_multisite.html")
    with open(xlsx_path, "rb") as f:
        st.download_button("XLSX-Export", f, file_name=f"{project.project_name}_multisite.xlsx")

    if st.button("Alle Standorte löschen", type="secondary"):
        st.session_state["ms_project"] = MultiSiteProject(project_name=project_name)
        st.rerun()
else:
    st.info("Noch keine Standorte — einen oben anlegen.")
