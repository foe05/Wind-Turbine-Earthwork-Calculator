"""
Tests für die Lauf-Mitschrift.

Bewusst ohne laufende Datenbank: geprüft wird das Verhalten, das die
Pipeline schützt — ohne `DATABASE_URL` passiert nichts, bei einer
unerreichbaren Datenbank fliegt nichts nach oben, und das Mapping deckt
jeden Flächentyp und jedes Artefaktfeld ab.

Der Weg mit echter Datenbank ist durch `test_e2e_pipeline.py` abgedeckt,
sobald `DATABASE_URL` gesetzt ist.
"""

from __future__ import annotations

import dataclasses

import pytest

from app.core.models import ARTIFACT_KINDS
from app.core.multi_surface import SurfaceType
from app.services.persistence import _ARTIFACT_ATTRS, _surface_geometries, RunRecorder
from app.services.pipeline import PipelineInputs, PipelineOutputs


@pytest.fixture
def inputs(tmp_path):
    return PipelineInputs(
        project_name="Persistenz-Test",
        crane_pad_dxf=str(tmp_path / "kran.dxf"),
        foundation_dxf=str(tmp_path / "fundament.dxf"),
        fok=100.0,
        foundation_depth=3.0,
        gravel_thickness=0.4,
        output_dir=str(tmp_path / "out"),
    )


def test_ohne_database_url_ist_recorder_stumm(inputs, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    recorder = RunRecorder(inputs)
    assert recorder.enabled is False

    # Alle drei Methoden müssen folgenlos durchlaufen — die Pipeline ruft sie
    # unbedingt auf.
    recorder.start()
    recorder.finish(None)
    recorder.fail(RuntimeError("egal"))
    assert recorder.run_id is None


def test_unerreichbare_datenbank_bricht_nicht_durch(inputs, monkeypatch):
    """Ein DB-Ausfall darf einen erfolgreichen Lauf nicht kaputtmachen."""
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://wtec:wtec@host.invalid:5432/wtec"
    )
    # Engine/Sessionmaker sind pro Prozess gecacht.
    from app.core import db

    db.get_engine.cache_clear()
    db.get_sessionmaker.cache_clear()

    recorder = RunRecorder(inputs)
    assert recorder.enabled is True

    recorder.start()  # darf nicht werfen
    assert recorder.enabled is False, "nach Fehlschlag muss der Recorder stillgelegt sein"
    assert recorder.run_id is None

    recorder.finish(None)
    recorder.fail(RuntimeError("egal"))

    db.get_engine.cache_clear()
    db.get_sessionmaker.cache_clear()


def test_jeder_flaechentyp_hat_eine_geometriequelle():
    """Sonst landet eine Fläche ohne Geometrie in der DB, ohne dass es auffällt."""
    outputs = PipelineOutputs(
        project_name="x",
        output_dir="/tmp/x",
        dem_path="/tmp/x.tif",
        crane_polygon=None,
        foundation_polygon=None,
        result=None,
        map_image_path="/tmp/map.png",
        profile_paths=[],
        html_report_path="/tmp/r.html",
        json_report_path="/tmp/r.json",
    )
    mapping = _surface_geometries(outputs)
    assert set(mapping) == set(SurfaceType), "Flächentyp ohne Geometrie-Zuordnung"


def test_artefakt_mapping_passt_zu_schema_und_outputs():
    """Attributnamen müssen existieren und die Arten im CHECK erlaubt sein."""
    felder = {f.name for f in dataclasses.fields(PipelineOutputs)}
    for attr, kind in _ARTIFACT_ATTRS:
        assert attr in felder, f"PipelineOutputs hat kein Feld {attr}"
        assert kind in ARTIFACT_KINDS, f"{kind} ist im CHECK-Constraint nicht erlaubt"
    # 'profile' wird separat aus profile_paths erzeugt.
    assert "profile" in ARTIFACT_KINDS
