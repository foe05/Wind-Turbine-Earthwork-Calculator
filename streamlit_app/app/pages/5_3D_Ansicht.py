"""Streamlit-Page: 3D-Viewer für die letzte Berechnung (Three.js iframe)."""

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="3D-Ansicht", layout="wide")
st.title("3D-Ansicht")

if "last_result" not in st.session_state:
    st.info(
        "Keine Berechnung gefunden — bitte erst auf der Startseite einen Lauf durchführen "
        "und sicherstellen, dass das 3D-Viewer-Output aktiviert ist."
    )
else:
    out = st.session_state["last_result"]
    if not out.three_viewer_path:
        st.warning("Diese Berechnung enthält keinen 3D-Viewer. Lauf erneut mit 'generate_3d_viewer=True'.")
    else:
        viewer_html = open(out.three_viewer_path, "r", encoding="utf-8").read()
        # Embed direkt
        components.html(viewer_html, height=800, scrolling=False)
        st.caption(f"Quelle: {out.three_viewer_path}")
