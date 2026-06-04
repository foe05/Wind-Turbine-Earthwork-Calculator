"""Streamlit-Page: Monte-Carlo-Unsicherheit auf einem Cut/Fill-Modell."""

import numpy as np
import streamlit as st

from app.core.uncertainty import (
    TerrainType,
    UncertaintyConfig,
    run_uncertainty_analysis,
)

st.set_page_config(page_title="Unsicherheit", layout="wide")
st.title("Monte-Carlo-Unsicherheits-Analyse")
st.caption(
    "Propagiert Eingabeparameter-Unsicherheiten (DEM, FOK, Tiefen, Slope) "
    "auf das berechnete Volumen. Latin Hypercube Sampling."
)

col1, col2 = st.columns(2)
with col1:
    st.subheader("Konfiguration")
    terrain = st.selectbox(
        "Geländetyp",
        list(TerrainType),
        format_func=lambda t: {"flat": "Flach (±15 cm @ 2σ)", "moderate": "Mittel (±20 cm)", "steep": "Steil (±30 cm @ 2σ)"}[t.value],
    )
    n = st.slider("Sample-Anzahl", 100, 5000, 500, step=100)
    seed = st.number_input("Random Seed (Reproduzierbarkeit)", value=42)
    fok_std = st.number_input("σ FOK [m]", value=0.0, format="%.3f")
    depth_std = st.number_input("σ Fundamenttiefe [m]", value=0.1, format="%.3f")
    gravel_std = st.number_input("σ Schotterdicke [m]", value=0.05, format="%.3f")
    slope_std = st.number_input("σ Böschungswinkel [°]", value=3.0, format="%.1f")

with col2:
    st.subheader("Nominalwerte")
    base_fok = st.number_input("FOK [m ü.NN]", value=318.37)
    base_depth = st.number_input("Fundamenttiefe [m]", value=3.1)
    base_gravel = st.number_input("Schotterdicke [m]", value=0.6)
    base_slope = st.number_input("Böschungswinkel [°]", value=45.0)
    base_cut_per_m_dem = st.number_input(
        "Sensitivität: Δ Cut [m³] pro Δ DEM [m]",
        value=2500.0,
        help="Empirischer Wert: wie stark ändert sich der Cut bei systemt. DEM-Verschiebung um 1 m.",
    )
    base_cut_per_m_depth = st.number_input("Δ Cut pro Δ Fundamenttiefe", value=200.0)
    base_cut_per_m_gravel = st.number_input("Δ Cut pro Δ Schotter", value=1800.0)

if st.button("Analyse starten", type="primary"):
    cfg = UncertaintyConfig.for_terrain(
        terrain,
        num_samples=n,
        random_seed=int(seed),
        fok_std=fok_std,
        foundation_depth_std=depth_std,
        gravel_thickness_std=gravel_std,
        slope_angle_std=3.0,
    )

    def evaluate(params: dict) -> dict:
        dem = params.get("dem_bias", 0.0)
        fok = params.get("fok", base_fok)
        depth = params.get("foundation_depth", base_depth)
        gravel = params.get("gravel_thickness", base_gravel)
        # Linearisiertes Modell: Cut hängt linear von DEM, Tiefe, Schotter ab
        cut = 6546 + base_cut_per_m_dem * dem + base_cut_per_m_depth * (depth - base_depth) + base_cut_per_m_gravel * (gravel - base_gravel)
        # Fill folgt anti-linear (Plattform-Verschiebung)
        fill = 2411 - 0.8 * (cut - 6546)
        return {
            "cut_m3": cut,
            "fill_m3": fill,
            "net_m3": cut - fill,
            "total_moved_m3": cut + fill,
        }

    with st.spinner("Latin-Hypercube-Sampling läuft…"):
        result = run_uncertainty_analysis(
            cfg, {"fok": base_fok, "foundation_depth": base_depth, "gravel_thickness": base_gravel}, evaluate
        )

    st.subheader("Ergebnis-Verteilungen")
    cols = st.columns(2)
    for i, (name, r) in enumerate(result.outputs.items()):
        with cols[i % 2]:
            st.markdown(f"**{name}**")
            st.write(f"μ = {r.mean:.0f}, σ = {r.std:.0f}, CV = {r.coefficient_of_variation*100:.1f}%")
            st.write(f"90% CI: [{r.percentile_5:.0f}, {r.percentile_95:.0f}]")
            # Histogramm
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(5, 2.5))
            ax.hist(r.samples, bins=30, color="#4a90d9", alpha=0.8)
            ax.axvline(r.mean, color="red", lw=1.5, label=f"Mittel {r.mean:.0f}")
            ax.axvline(r.percentile_5, color="orange", lw=1, ls="--", label="5 %")
            ax.axvline(r.percentile_95, color="orange", lw=1, ls="--", label="95 %")
            ax.set_xlabel(name)
            ax.legend(fontsize=8)
            ax.grid(alpha=0.3)
            st.pyplot(fig)
            plt.close(fig)

    st.subheader("Sensitivitäts-Ranking")
    target = st.selectbox("Output", list(result.outputs.keys()))
    ranking = result.get_sensitivity_ranking(target)
    if ranking:
        st.dataframe(
            [{"Parameter": p, "|Korrelation|": round(c, 4)} for p, c in ranking],
            hide_index=True,
        )
