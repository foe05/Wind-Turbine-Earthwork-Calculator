"""Streamlit-Page: Kalkdosierung + Schottertragschicht + BGR-Lookup."""

import streamlit as st

from app.core.bgr_api import BGRSoilAPI
from app.core.soil_stabilization import (
    DIN_SOIL_CLASSIFICATION,
    OPTIMUM_WATER_CONTENT,
    SoilStabilizationCalculator,
)

st.set_page_config(page_title="Bodenstabilisierung", layout="wide")
st.title("Bodenstabilisierung")

calc = SoilStabilizationCalculator()

st.subheader("BGR-Bodendaten")
c1, c2 = st.columns(2)
with c1:
    x = st.number_input("X (UTM 32N)", value=492000.0)
    y = st.number_input("Y (UTM 32N)", value=5702000.0)
    if st.button("BGR-Lookup"):
        with st.spinner("Frage BGR ab…"):
            r = BGRSoilAPI(timeout=8).query_soil_at_point(x, y, source_epsg=25832)
        if r["success"]:
            st.success(f"Bodenart: {r['soil_type']} ({r['soil_code']})")
            st.write(r.get("description", ""))
            st.session_state["bgr_soil"] = r["soil_type"]
        else:
            st.error(r["error"])
            if r.get("endpoint_unavailable"):
                st.info("BGR-Service eventuell nicht erreichbar.")

with c2:
    st.markdown("**DIN-18196-Klassifikation**")
    din_code = st.text_input("DIN-Code (z. B. TM, SU, ST)", value="TM")
    if din_code:
        soil = calc.soil_type_from_din18196(din_code)
        if soil:
            st.info(f"{din_code} → {soil}")

st.markdown("---")
st.subheader("Kalk-Dosierung")
c1, c2, c3 = st.columns(3)
with c1:
    soil_type = st.selectbox("Bodenart", ["Ton", "Schluff", "Lehm", "Sand", "Kies"],
                              index=0 if "bgr_soil" not in st.session_state else
                              ["Ton", "Schluff", "Lehm", "Sand", "Kies"].index(
                                  st.session_state["bgr_soil"]
                              ) if st.session_state["bgr_soil"] in ["Ton", "Schluff", "Lehm", "Sand", "Kies"] else 0)
with c2:
    water = st.number_input("Aktueller Wassergehalt [%]", value=22.0, min_value=0.0)
    optimum = OPTIMUM_WATER_CONTENT.get(soil_type, 16.0)
    st.write(f"DIN-Optimum: {optimum} %")
with c3:
    current_ev2 = st.number_input("Aktueller Ev2 [MN/m²]", value=20.0, min_value=1.0)
    target_ev2 = st.number_input("Ziel-Ev2 [MN/m²]", value=60.0, min_value=1.0)

if soil_type in ("Sand", "Kies"):
    st.warning("Kalkstabilisierung für Sand/Kies normalerweise nicht empfohlen.")

r = calc.estimate_lime_dosage(soil_type, water, optimum, current_ev2, target_ev2)
c1, c2, c3 = st.columns(3)
c1.metric("Dosierung [% Masse]", f"{r['percentage']:.1f}")
c2.metric("kg/m²", f"{r['kg_per_m2']:.0f}")
c3.metric("Erwarteter Ev2 [MN/m²]", f"{r['expected_ev2_after']:.0f}")
if r.get("note"):
    st.info(r["note"])

st.markdown("---")
st.subheader("Schotter-Tragschicht (RStO 12)")
c1, c2, c3 = st.columns(3)
with c1:
    subgrade_ev2 = st.number_input("Planum-Ev2 [MN/m²]", value=60.0, min_value=1.0)
with c2:
    area_m2 = st.number_input("Fläche [m²]", value=2500.0, min_value=1.0)
with c3:
    target_g = st.number_input("Ziel-Ev2 oben [MN/m²]", value=120.0, min_value=1.0)

gravel = calc.calculate_gravel_layer(subgrade_ev2, target_g, area_m2)
c1, c2, c3 = st.columns(3)
c1.metric("Schotterdicke [m]", f"{gravel['thickness_m']:.2f}")
c2.metric("Volumen [m³]", f"{gravel['volume_m3']:,.0f}")
c3.metric("Masse [t]", f"{gravel['mass_t']:,.0f}")
