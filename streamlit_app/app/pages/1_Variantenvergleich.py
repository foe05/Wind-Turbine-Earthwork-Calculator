"""Streamlit-Page: Side-by-side Variantenvergleich."""

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from app.core.variants import Variant, VariantComparisonReport
from app.services import history

st.set_page_config(page_title="Variantenvergleich", layout="wide")
st.title("Variantenvergleich")
st.caption("Mehrere Planungsvarianten gegenüberstellen (Höhe, Massen, Kosten, CO₂).")

if "variants" not in st.session_state:
    st.session_state["variants"] = []


def _variant_from_run(run: dict) -> Variant:
    """Gespeicherten Lauf in eine Variante übersetzen.

    Kosten und CO₂ stammen aus den Zusatzmodulen und fehlen, wenn der Lauf
    ohne sie gerechnet wurde — dann bleibt es bei 0 und kann von Hand
    nachgetragen werden. Externer Schotter wird von der Pipeline nicht
    ermittelt und bleibt deshalb ebenfalls offen.
    """
    fehlend = [
        name
        for name, wert in (("Kosten", run["total_cost_eur"]), ("CO₂", run["total_co2_kg"]))
        if wert is None
    ]
    return Variant(
        label=f"{run['project_name']} — {run['started_at']:%d.%m. %H:%M}",
        crane_height_m=run["crane_optimum_height"],
        total_cut_m3=run["total_cut_m3"],
        total_fill_m3=run["total_fill_m3"],
        gravel_m3=0.0,
        total_cost_eur=run["total_cost_eur"] or 0.0,
        total_co2_kg=run["total_co2_kg"] or 0.0,
        notes=("ohne " + "/".join(fehlend)) if fehlend else "",
    )


# --- Aus gespeicherten Laeufen uebernehmen -------------------------------

if history.is_available():
    try:
        gespeicherte = history.list_runs_for_comparison()
    except SQLAlchemyError as exc:
        gespeicherte = []
        st.warning(f"Gespeicherte Läufe nicht abrufbar: {exc}")

    if gespeicherte:
        with st.expander("Aus gespeicherten Läufen übernehmen", expanded=True):
            st.caption(
                "Massen und Kranhöhe kommen direkt aus der Berechnung — kein Abtippen "
                "aus dem Report."
            )
            auswahl = st.multiselect(
                "Läufe",
                options=[r["id"] for r in gespeicherte],
                format_func=lambda rid: next(
                    f"{r['project_name']} — {r['started_at']:%d.%m.%Y %H:%M} "
                    f"({r['total_cut_m3']:.0f} / {r['total_fill_m3']:.0f} m³)"
                    for r in gespeicherte
                    if r["id"] == rid
                ),
            )
            if st.button("Übernehmen", type="primary", disabled=not auswahl):
                nach_id = {r["id"]: r for r in gespeicherte}
                for rid in auswahl:
                    st.session_state["variants"].append(_variant_from_run(nach_id[rid]))
                st.success(f"{len(auswahl)} Lauf/Läufe übernommen.")
                st.rerun()
    else:
        st.info(
            "Noch keine erfolgreichen Läufe gespeichert — Varianten lassen sich unten "
            "von Hand anlegen."
        )

with st.expander("Variante von Hand anlegen", expanded=not st.session_state["variants"]):
    col1, col2 = st.columns(2)
    with col1:
        label = st.text_input("Bezeichnung", value=f"Variante {len(st.session_state['variants']) + 1}")
        crane_h = st.number_input("Kranhöhe [m ü.NN]", value=319.87, format="%.2f")
        cut = st.number_input("Gesamt-Cut [m³]", value=5280.0, min_value=0.0)
        fill = st.number_input("Gesamt-Fill [m³]", value=1763.0, min_value=0.0)
    with col2:
        gravel = st.number_input("Externer Schotter [m³]", value=0.0, min_value=0.0)
        cost = st.number_input("Kosten [€]", value=50000.0, min_value=0.0)
        co2 = st.number_input("CO₂e [kg]", value=15000.0, min_value=0.0)
        notes = st.text_input("Notizen", value="")
    if st.button("Hinzufügen", type="primary"):
        st.session_state["variants"].append(
            Variant(
                label=label,
                crane_height_m=crane_h,
                total_cut_m3=cut,
                total_fill_m3=fill,
                gravel_m3=gravel,
                total_cost_eur=cost,
                total_co2_kg=co2,
                notes=notes,
            )
        )
        st.success(f"{label} hinzugefügt.")
        st.rerun()

if st.session_state["variants"]:
    st.subheader(f"Vergleich ({len(st.session_state['variants'])} Varianten)")
    rows = []
    for v in st.session_state["variants"]:
        rows.append(
            {
                "Label": v.label,
                "Kran [m ü.NN]": round(v.crane_height_m, 2),
                "Cut [m³]": round(v.total_cut_m3, 0),
                "Fill [m³]": round(v.total_fill_m3, 0),
                "Erdbewegung [m³]": round(v.total_volume_moved_m3, 0),
                "Netto [m³]": round(v.net_volume_m3, 0),
                "Schotter [m³]": round(v.gravel_m3, 0),
                "Kosten [€]": round(v.total_cost_eur, 0),
                "CO₂ [kg]": round(v.total_co2_kg, 0),
                "Hinweis": v.notes,
            }
        )
    st.dataframe(rows, width="stretch", hide_index=True)

    rep = VariantComparisonReport(st.session_state["variants"])
    best_vol = rep.best_variant("total_volume_moved_m3")
    best_cost = rep.best_variant("total_cost_eur")
    best_co2 = rep.best_variant("total_co2_kg")

    c1, c2, c3 = st.columns(3)
    c1.metric("Min. Erdbewegung", best_vol.label, f"{best_vol.total_volume_moved_m3:.0f} m³")
    c2.metric("Min. Kosten", best_cost.label, f"{best_cost.total_cost_eur:,.0f} €")
    c3.metric("Min. CO₂", best_co2.label, f"{best_co2.total_co2_kg:,.0f} kg")

    html = rep.to_html("Variantenvergleich")
    st.download_button("Als HTML downloaden", html, "varianten.html", "text/html")

    if st.button("Alle löschen"):
        st.session_state["variants"] = []
        st.rerun()
else:
    st.info("Noch keine Varianten — eine oben anlegen.")
