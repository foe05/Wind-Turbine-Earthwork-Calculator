"""
Tests für die Laufhistorie.

Ohne Datenbank prüfbar ist der Pfad, der im Betrieb am ehesten wehtut: die
Seite darf nicht mit einem Traceback hochkommen, wenn keine `DATABASE_URL`
gesetzt ist — sie soll es sagen und aufhören. Der Rendertest fängt
nebenbei Importfehler und Tippfehler in den Streamlit-Aufrufen ab.

Die Wege mit echten Daten sind über `test_e2e_pipeline.py` mit gesetzter
`DATABASE_URL` abgedeckt.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.services import history

PAGE = Path(__file__).resolve().parent.parent / "app" / "pages" / "6_Laufhistorie.py"
VARIANTEN = Path(__file__).resolve().parent.parent / "app" / "pages" / "1_Variantenvergleich.py"


def test_ohne_database_url_nicht_verfuegbar(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert history.is_available() is False


def test_seite_rendert_ohne_datenbank(monkeypatch):
    """Kein Traceback, sondern ein Hinweis — und dann Schluss."""
    monkeypatch.delenv("DATABASE_URL", raising=False)

    at = AppTest.from_file(str(PAGE), default_timeout=60)
    at.run()

    assert not at.exception, [str(e.value) for e in at.exception]
    assert at.title[0].value == "Laufhistorie"
    assert any("DATABASE_URL" in i.value for i in at.info), "Hinweis auf fehlende DB fehlt"
    # st.stop() muss gegriffen haben: keine Auswahl, keine Kennzahlen.
    assert not at.selectbox
    assert not at.metric


def test_seite_meldet_unerreichbare_datenbank(monkeypatch):
    """DB konfiguriert, aber tot: Fehlermeldung statt Absturz."""
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://wtec:wtec@host.invalid:5432/wtec"
    )
    from app.core import db

    db.get_engine.cache_clear()
    db.get_sessionmaker.cache_clear()

    at = AppTest.from_file(str(PAGE), default_timeout=60)
    at.run()

    try:
        assert not at.exception, [str(e.value) for e in at.exception]
        assert at.error, "Fehlermeldung zur nicht erreichbaren Datenbank fehlt"
        assert not at.metric
    finally:
        db.get_engine.cache_clear()
        db.get_sessionmaker.cache_clear()


@pytest.mark.parametrize("fn", [history.list_projects, history.load_run, history.delete_run])
def test_lesefunktionen_sind_exportiert(fn):
    """Schützt die Seite davor, gegen umbenannte Funktionen zu laufen."""
    assert fn.__name__ in history.__all__


def test_variantenvergleich_ohne_datenbank(monkeypatch):
    """Die Seite gab es vor der Persistenz — sie muss ohne DB unveraendert laufen."""
    monkeypatch.delenv("DATABASE_URL", raising=False)

    at = AppTest.from_file(str(VARIANTEN), default_timeout=60)
    at.run()

    assert not at.exception, [str(e.value) for e in at.exception]
    assert at.title[0].value == "Variantenvergleich"
    # Kein Uebernehmen-Block, aber die manuelle Eingabe muss da sein.
    assert not at.multiselect
    assert any(b.label == "Hinzufügen" for b in at.button)


def test_variantenvergleich_meldet_tote_datenbank(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://wtec:wtec@host.invalid:5432/wtec")
    from app.core import db

    db.get_engine.cache_clear()
    db.get_sessionmaker.cache_clear()

    at = AppTest.from_file(str(VARIANTEN), default_timeout=60)
    at.run()

    try:
        assert not at.exception, [str(e.value) for e in at.exception]
        assert at.warning, "Hinweis auf nicht abrufbare Laeufe fehlt"
        # Manuelle Eingabe bleibt trotzdem benutzbar.
        assert any(b.label == "Hinzufügen" for b in at.button)
    finally:
        db.get_engine.cache_clear()
        db.get_sessionmaker.cache_clear()
