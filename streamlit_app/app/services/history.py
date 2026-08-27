"""
Lesezugriff auf die gespeicherten Berechnungsläufe.

Gegenstück zu `persistence.py`: dort wird geschrieben, hier gelesen. Die
Funktionen geben einfache Dicts zurück, keine ORM-Objekte — die Session ist
beim Rendern der Seite längst geschlossen, und detachte Instanzen wären eine
Fehlerquelle ohne Gegenwert.

Geometrien kommen als GeoJSON heraus. Sie liegen in EPSG:4326, lassen sich
also ohne weitere Transformation auf eine Karte legen.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select

from ..core import db
from ..core.models import Project, Run, RunArtifact, RunSurface

log = logging.getLogger(__name__)


def is_available() -> bool:
    """Ist überhaupt eine Datenbank konfiguriert?"""
    return db.is_configured()


def list_projects() -> list[dict]:
    """Projekte mit Anzahl und Zeitpunkt ihrer Läufe, neueste zuerst."""
    with db.session_scope() as session:
        rows = session.execute(
            select(
                Project.id,
                Project.name,
                Project.crs_epsg,
                func.count(Run.id).label("run_count"),
                func.max(Run.started_at).label("last_run"),
            )
            .outerjoin(Run, Run.project_id == Project.id)
            .group_by(Project.id, Project.name, Project.crs_epsg)
            .order_by(func.max(Run.started_at).desc().nullslast())
        ).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "crs_epsg": r.crs_epsg,
            "run_count": r.run_count,
            "last_run": r.last_run,
        }
        for r in rows
    ]


def list_runs(project_id: int, limit: int = 50) -> list[dict]:
    """Läufe eines Projekts, neueste zuerst."""
    with db.session_scope() as session:
        rows = session.execute(
            select(
                Run.id,
                Run.status,
                Run.started_at,
                Run.finished_at,
                Run.crane_optimum_height,
                Run.total_cut_m3,
                Run.total_fill_m3,
                Run.net_m3,
                Run.crs_epsg,
                Run.error,
            )
            .where(Run.project_id == project_id)
            .order_by(Run.started_at.desc())
            .limit(limit)
        ).all()
    return [dict(r._mapping) for r in rows]


def load_run(run_id: UUID) -> Optional[dict]:
    """Ein Lauf mit Flächen (inkl. GeoJSON) und Artefakten."""
    with db.session_scope() as session:
        run = session.get(Run, run_id)
        if run is None:
            return None

        surfaces = session.execute(
            select(
                RunSurface.surface_type,
                RunSurface.plateau_height,
                RunSurface.cut_m3,
                RunSurface.fill_m3,
                RunSurface.platform_area_m2,
                RunSurface.terrain_min,
                RunSurface.terrain_max,
                RunSurface.terrain_mean,
                RunSurface.num_pixels,
                RunSurface.slope_cut_m3,
                RunSurface.slope_fill_m3,
                RunSurface.slope_area_m2,
                func.ST_AsGeoJSON(RunSurface.geom).label("geojson"),
            )
            .where(RunSurface.run_id == run_id)
            .order_by(RunSurface.surface_type)
        ).all()

        artifacts = session.execute(
            select(RunArtifact.kind, RunArtifact.path, RunArtifact.meta)
            .where(RunArtifact.run_id == run_id)
            .order_by(RunArtifact.kind, RunArtifact.id)
        ).all()

        project_name = session.get(Project, run.project_id).name

        return {
            "id": run.id,
            "project_name": project_name,
            "status": run.status,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "error": run.error,
            "crs_epsg": run.crs_epsg,
            "output_dir": run.output_dir,
            "dem_path": run.dem_path,
            "fok": run.fok,
            "foundation_depth": run.foundation_depth,
            "gravel_thickness": run.gravel_thickness,
            "crane_optimum_height": run.crane_optimum_height,
            "boom_slope_percent": run.boom_slope_percent,
            "rotor_offset_m": run.rotor_offset_m,
            "road_slope_percent": run.road_slope_percent,
            "total_cut_m3": run.total_cut_m3,
            "total_fill_m3": run.total_fill_m3,
            "net_m3": run.net_m3,
            "inputs": run.inputs,
            "co2_breakdown": run.co2_breakdown,
            "phase_plan": run.phase_plan,
            "strata_breakdown": run.strata_breakdown,
            "surfaces": [dict(s._mapping) for s in surfaces],
            "artifacts": [dict(a._mapping) for a in artifacts],
        }


def list_runs_for_comparison(limit: int = 100) -> list[dict]:
    """Erfolgreiche Laeufe aller Projekte, aufbereitet fuer den Variantenvergleich.

    Kosten und CO2 stehen nicht als eigene Spalten in `runs`, sondern in den
    JSONB-Feldern der jeweiligen Zusatzmodule — sie fehlen, wenn der Lauf
    ohne `compute_phases` bzw. `compute_co2` gerechnet wurde.
    """
    with db.session_scope() as session:
        rows = session.execute(
            select(
                Run.id,
                Project.name.label("project_name"),
                Run.started_at,
                Run.crane_optimum_height,
                Run.total_cut_m3,
                Run.total_fill_m3,
                Run.crs_epsg,
                Run.co2_breakdown,
                Run.phase_plan,
            )
            .join(Project, Project.id == Run.project_id)
            .where(Run.status == "succeeded")
            .order_by(Run.started_at.desc())
            .limit(limit)
        ).all()

    ergebnis = []
    for r in rows:
        co2 = (r.co2_breakdown or {}).get("total_kg")
        kosten = (r.phase_plan or {}).get("total_cost_eur")
        ergebnis.append(
            {
                "id": r.id,
                "project_name": r.project_name,
                "started_at": r.started_at,
                "crane_optimum_height": r.crane_optimum_height or 0.0,
                "total_cut_m3": r.total_cut_m3 or 0.0,
                "total_fill_m3": r.total_fill_m3 or 0.0,
                "crs_epsg": r.crs_epsg,
                "total_co2_kg": float(co2) if co2 is not None else None,
                "total_cost_eur": float(kosten) if kosten is not None else None,
            }
        )
    return ergebnis


def delete_run(run_id: UUID) -> bool:
    """Einen Lauf samt Flächen und Artefakten entfernen (DB-seitig CASCADE).

    Die erzeugten Dateien im Ausgabeordner bleiben liegen — die gehören dem
    Dateisystem, nicht der Datenbank.
    """
    with db.session_scope() as session:
        run = session.get(Run, run_id)
        if run is None:
            return False
        session.delete(run)
    return True


__all__ = [
    "delete_run",
    "is_available",
    "list_projects",
    "list_runs",
    "list_runs_for_comparison",
    "load_run",
]
