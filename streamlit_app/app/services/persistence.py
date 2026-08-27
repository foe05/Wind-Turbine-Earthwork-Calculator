"""
Mitschrift eines Berechnungslaufs in die Datenbank.

Additiv gedacht: ohne `DATABASE_URL` ist der Recorder ein No-op, und ein
Datenbankfehler darf einen erfolgreichen Lauf nicht kaputtmachen — die
Aufgabe der Pipeline ist das Rechnen, die Mitschrift ist Beiwerk. Jeder
Schreibvorgang ist deshalb gekapselt: er loggt eine Warnung und schaltet
den Recorder still, statt die Exception nach oben zu geben.

Die einzige Ausnahme ist die Reihenfolge — schlägt `start()` fehl, wird
auch nicht mehr versucht, Ergebnisse zu schreiben.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from ..core import db
from ..core.models import Project, Run, RunArtifact, RunSurface
from ..core.multi_surface import SurfaceType

if TYPE_CHECKING:  # pragma: no cover - nur für Typprüfung
    from .pipeline import PipelineInputs, PipelineOutputs

log = logging.getLogger(__name__)


#: Attribut auf PipelineOutputs -> Artefaktart in run_artifacts.
_ARTIFACT_ATTRS = (
    ("html_report_path", "html_report"),
    ("json_report_path", "json_report"),
    ("map_image_path", "map_image"),
    ("geopackage_path", "geopackage"),
    ("landxml_path", "landxml"),
    ("gltf_path", "gltf"),
    ("three_viewer_path", "three_viewer"),
    ("dem_path", "dem"),
)


def _surface_geometries(outputs: "PipelineOutputs") -> dict[SurfaceType, object]:
    """Flächentyp -> Geometrie, so wie die Pipeline sie zurückgibt."""
    return {
        SurfaceType.CRANE_PAD: outputs.crane_polygon,
        SurfaceType.FOUNDATION: outputs.foundation_polygon,
        SurfaceType.BOOM: outputs.boom_polygon,
        SurfaceType.ROTOR_STORAGE: outputs.rotor_polygon,
        SurfaceType.ROAD_ACCESS: outputs.road_polygon,
        SurfaceType.HOLMS: outputs.holm_polygons,
    }


def _get_or_create_project(session, name: str, crs_epsg: int) -> Project:
    """Projekt zum Namen holen, sonst anlegen.

    `projects.name` ist UNIQUE — zwei Läufe mit gleichem `project_name`
    bilden die Historie desselben Projekts.
    """
    project = session.execute(select(Project).where(Project.name == name)).scalar_one_or_none()
    if project is not None:
        return project
    project = Project(name=name, crs_epsg=crs_epsg)
    session.add(project)
    session.flush()
    return project


class RunRecorder:
    """Schreibt einen Lauf mit: `start()` vor, `finish()`/`fail()` nach der Rechnung."""

    def __init__(self, inputs: "PipelineInputs") -> None:
        self._inputs = inputs
        self.run_id: Optional[UUID] = None
        self.enabled: bool = db.is_configured()
        if not self.enabled:
            log.debug("Keine DATABASE_URL gesetzt — Lauf wird nicht persistiert.")

    # -- intern ---------------------------------------------------------

    def _disable(self, what: str, exc: Exception) -> None:
        log.warning("Lauf konnte nicht persistiert werden (%s): %s", what, exc)
        self.enabled = False

    # -- API ------------------------------------------------------------

    def start(self) -> None:
        """Lauf mit Status 'running' anlegen."""
        if not self.enabled:
            return
        try:
            with db.session_scope() as session:
                project = _get_or_create_project(
                    session, self._inputs.project_name, self._inputs.crs_epsg
                )
                run = Run(
                    project_id=project.id,
                    status="running",
                    inputs=asdict(self._inputs),
                    crs_epsg=self._inputs.crs_epsg,
                    output_dir=str(self._inputs.output_dir),
                    dem_path=str(self._inputs.dem_path) if self._inputs.dem_path else None,
                    fok=self._inputs.fok,
                    foundation_depth=self._inputs.foundation_depth,
                    gravel_thickness=self._inputs.gravel_thickness,
                )
                session.add(run)
                session.flush()
                self.run_id = run.id
        except (SQLAlchemyError, OSError) as exc:
            self._disable("start", exc)

    def finish(self, outputs: "PipelineOutputs") -> None:
        """Ergebnisse, Flächen und Artefakte nachtragen, Status auf 'succeeded'."""
        if not self.enabled or self.run_id is None:
            return
        try:
            with db.session_scope() as session:
                run = session.get(Run, self.run_id)
                if run is None:  # von außen gelöscht — nichts zu tun
                    return
                self._fill_run(run, outputs)
                self._add_surfaces(session, outputs)
                self._add_artifacts(session, outputs)
        except (SQLAlchemyError, OSError, ValueError) as exc:
            self._disable("finish", exc)

    def fail(self, exc: BaseException) -> None:
        """Lauf als gescheitert markieren; die Fehlermeldung wird mitgeschrieben."""
        if not self.enabled or self.run_id is None:
            return
        try:
            with db.session_scope() as session:
                run = session.get(Run, self.run_id)
                if run is None:
                    return
                run.status = "failed"
                run.error = f"{type(exc).__name__}: {exc}"[:4000]
                run.finished_at = func.now()
        except (SQLAlchemyError, OSError) as db_exc:
            self._disable("fail", db_exc)

    # -- Bausteine ------------------------------------------------------

    def _fill_run(self, run: Run, outputs: "PipelineOutputs") -> None:
        result = outputs.result
        run.status = "succeeded"
        run.dem_path = outputs.dem_path
        run.output_dir = outputs.output_dir
        run.crane_optimum_height = result.crane_optimum_height
        run.fok = result.fok
        run.foundation_depth = result.foundation_depth
        run.gravel_thickness = result.gravel_thickness
        run.boom_slope_percent = result.boom_slope_percent
        run.rotor_offset_m = result.rotor_offset_m
        run.road_slope_percent = result.road_slope_percent
        # Properties des Rechenkerns; net_m3 ist in der DB GENERATED.
        run.total_cut_m3 = result.total_cut_m3
        run.total_fill_m3 = result.total_fill_m3
        run.co2_breakdown = outputs.co2_breakdown
        run.phase_plan = outputs.phase_plan
        run.strata_breakdown = outputs.strata_breakdown
        run.finished_at = func.now()

    def _add_surfaces(self, session, outputs: "PipelineOutputs") -> None:
        result = outputs.result
        geoms = _surface_geometries(outputs)
        crs = self._inputs.crs_epsg

        for surface_type, cutfill in result.surface_results.items():
            geom = geoms.get(surface_type)
            if surface_type is SurfaceType.HOLMS:
                stored = db.multipolygon_from(geom, crs)
            else:
                stored = db.to_storage_geometry(geom, crs) if geom is not None else None

            slope = result.slope_results.get(surface_type)
            session.add(
                RunSurface(
                    run_id=self.run_id,
                    surface_type=surface_type.value,
                    geom=stored,
                    plateau_height=cutfill.plateau_height,
                    cut_m3=cutfill.cut_m3,
                    fill_m3=cutfill.fill_m3,
                    platform_area_m2=cutfill.platform_area_m2,
                    terrain_min=cutfill.terrain_min,
                    terrain_max=cutfill.terrain_max,
                    terrain_mean=cutfill.terrain_mean,
                    num_pixels=cutfill.num_pixels,
                    slope_cut_m3=slope.cut_m3 if slope else None,
                    slope_fill_m3=slope.fill_m3 if slope else None,
                    slope_area_m2=slope.slope_area_m2 if slope else None,
                    avg_slope_width_m=slope.avg_slope_width_m if slope else None,
                    slope_samples=slope.samples if slope else None,
                )
            )

    def _add_artifacts(self, session, outputs: "PipelineOutputs") -> None:
        for attr, kind in _ARTIFACT_ATTRS:
            path = getattr(outputs, attr, None)
            if path:
                session.add(RunArtifact(run_id=self.run_id, kind=kind, path=str(path)))

        for entry in outputs.profile_paths or []:
            path = entry.get("path") if isinstance(entry, dict) else None
            if not path:
                continue
            meta = {k: v for k, v in entry.items() if k != "path"} if isinstance(entry, dict) else None
            session.add(
                RunArtifact(run_id=self.run_id, kind="profile", path=str(path), meta=meta or None)
            )


__all__ = ["RunRecorder"]
