"""
SQLAlchemy-Modelle für die Persistenz von Projekten und Berechnungsläufen.

Der Schnitt folgt dem Rechenkern: ein `Run` hält die Kopfdaten eines
`run_pipeline()`-Aufrufs, `RunSurface` je einen Eintrag aus
`MultiSurfaceResult.surface_results` (plus dem passenden `slope_results`-
Eintrag), `RunArtifact` die erzeugten Dateien.

Geometrien liegen kanonisch in EPSG:4326. Das Arbeits-CRS steht in
`Run.crs_epsg` — dort wird gerechnet, dort liegen auch GeoPackage und DXF.
Die 4326-Kopie existiert, damit Läufe aus verschiedenen UTM-Zonen räumlich
vergleichbar und über einen gemeinsamen GiST-Index abfragbar bleiben. Es
hängt keine Maßzahl daran: sämtliche Volumen und Flächen sind im nativen
CRS vorberechnet und werden als Zahlen gespeichert.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Computed,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .multi_surface import SurfaceType

#: SRID, in dem Geometrien abgelegt werden. Bewusst nicht das Arbeits-CRS.
STORAGE_SRID = 4326


def _enum_check(column: str, values) -> CheckConstraint:
    """CHECK-Constraint aus einer Wertemenge bauen.

    Bewusst `text` + CHECK statt eines nativen PG-Enums: neue Flächentypen
    oder Artefaktarten sind damit eine gewöhnliche Constraint-Migration
    statt eines ALTER TYPE mit Transaktions-Fallstricken.
    """
    literals = ", ".join(f"'{v}'" for v in values)
    return CheckConstraint(f"{column} IN ({literals})", name=f"ck_{column}")


RUN_STATUSES = ("running", "succeeded", "failed")

ARTIFACT_KINDS = (
    "html_report",
    "json_report",
    "map_image",
    "geopackage",
    "landxml",
    "gltf",
    "three_viewer",
    "profile",
    "dem",
)


class Base(DeclarativeBase):
    pass


class Project(Base):
    """Ein benanntes Projekt; bündelt alle Läufe unter demselben Namen.

    `name` ist identitätsstiftend (UNIQUE) — zwei Läufe mit gleichem
    `PipelineInputs.project_name` hängen am selben Projekt und bilden dessen
    Historie.
    """

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    #: Vorgabe-CRS für neue Läufe; einzelne Läufe dürfen davon abweichen.
    crs_epsg: Mapped[int] = mapped_column(Integer, nullable=False, default=25832)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    runs: Mapped[list["Run"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:  # pragma: no cover - Debug-Hilfe
        return f"<Project {self.id} {self.name!r}>"


class Run(Base):
    """Ein Aufruf von `run_pipeline()`.

    `inputs` hält `_serialize_inputs()` unverändert: die rund 50 Felder aus
    `PipelineInputs` sind überwiegend Tuning-Parameter, nach denen nicht
    gefiltert wird. Nur die Werte, die im Listing oder in Auswertungen
    gebraucht werden, bekommen eigene Spalten.

    Die UUID ist bewusst extern verwendbar — der SaaS-Plan adressiert
    Artefakte später über `run/{run_id}/...`.
    """

    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error: Mapped[Optional[str]] = mapped_column(Text)

    inputs: Mapped[dict] = mapped_column(JSONB, nullable=False)
    #: CRS, in dem gerechnet wurde (PipelineInputs.crs_epsg).
    crs_epsg: Mapped[int] = mapped_column(Integer, nullable=False)
    output_dir: Mapped[str] = mapped_column(Text, nullable=False)
    dem_path: Mapped[Optional[str]] = mapped_column(Text)

    # --- Kopfwerte aus MultiSurfaceResult ---
    fok: Mapped[Optional[float]] = mapped_column(Float)
    foundation_depth: Mapped[Optional[float]] = mapped_column(Float)
    gravel_thickness: Mapped[Optional[float]] = mapped_column(Float)
    crane_optimum_height: Mapped[Optional[float]] = mapped_column(Float)
    boom_slope_percent: Mapped[Optional[float]] = mapped_column(Float)
    rotor_offset_m: Mapped[Optional[float]] = mapped_column(Float)
    road_slope_percent: Mapped[Optional[float]] = mapped_column(Float)

    # --- Summen ---
    # Im Rechenkern sind das @property-Werte über alle Flächen. Hier
    # denormalisiert, damit ein Listing ohne Aggregation über run_surfaces
    # auskommt (und damit der Volumen-Regressionstest per SQL prüfbar ist).
    total_cut_m3: Mapped[Optional[float]] = mapped_column(Float)
    total_fill_m3: Mapped[Optional[float]] = mapped_column(Float)
    #: Spiegelt MultiSurfaceResult.net_m3 — kann per Definition nicht abdriften.
    net_m3: Mapped[Optional[float]] = mapped_column(
        Float, Computed("total_cut_m3 - total_fill_m3", persisted=True)
    )

    # --- Optionale Zusatzmodule (Wave 7-9), heterogene Dicts ---
    co2_breakdown: Mapped[Optional[dict]] = mapped_column(JSONB)
    phase_plan: Mapped[Optional[dict]] = mapped_column(JSONB)
    strata_breakdown: Mapped[Optional[dict]] = mapped_column(JSONB)

    project: Mapped[Project] = relationship(back_populates="runs")
    surfaces: Mapped[list["RunSurface"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", passive_deletes=True
    )
    artifacts: Mapped[list["RunArtifact"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        _enum_check("status", RUN_STATUSES),
        Index("ix_runs_project_started", "project_id", started_at.desc()),
    )

    def __repr__(self) -> str:  # pragma: no cover - Debug-Hilfe
        return f"<Run {self.id} {self.status}>"


class RunSurface(Base):
    """Ergebnis einer einzelnen Fläche innerhalb eines Laufs.

    Fasst `CutFillResult` und den zugehörigen `SlopeVolumeResult` in einer
    Zeile zusammen — beide sind im Rechenkern über denselben `SurfaceType`
    verschlüsselt, getrennte Tabellen erzwängen nur einen Join. Die
    `slope_*`-Spalten sind nullable, weil `slope_results` leer bleiben darf.

    Holme kommen als Liste von Polygonen aus der Pipeline und werden als ein
    MultiPolygon abgelegt; so bleibt es eine Zeile je Flächentyp.
    """

    __tablename__ = "run_surfaces"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), primary_key=True
    )
    surface_type: Mapped[str] = mapped_column(String(32), primary_key=True)

    geom: Mapped[Optional[object]] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=STORAGE_SRID, spatial_index=False)
    )

    # --- CutFillResult ---
    plateau_height: Mapped[float] = mapped_column(Float, nullable=False)
    cut_m3: Mapped[float] = mapped_column(Float, nullable=False)
    fill_m3: Mapped[float] = mapped_column(Float, nullable=False)
    platform_area_m2: Mapped[float] = mapped_column(Float, nullable=False)
    terrain_min: Mapped[float] = mapped_column(Float, nullable=False)
    terrain_max: Mapped[float] = mapped_column(Float, nullable=False)
    terrain_mean: Mapped[float] = mapped_column(Float, nullable=False)
    num_pixels: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- SlopeVolumeResult (optional) ---
    slope_cut_m3: Mapped[Optional[float]] = mapped_column(Float)
    slope_fill_m3: Mapped[Optional[float]] = mapped_column(Float)
    slope_area_m2: Mapped[Optional[float]] = mapped_column(Float)
    avg_slope_width_m: Mapped[Optional[float]] = mapped_column(Float)
    slope_samples: Mapped[Optional[int]] = mapped_column(Integer)

    run: Mapped[Run] = relationship(back_populates="surfaces")

    __table_args__ = (
        _enum_check("surface_type", tuple(s.value for s in SurfaceType)),
        Index("ix_run_surfaces_geom", "geom", postgresql_using="gist"),
    )

    def __repr__(self) -> str:  # pragma: no cover - Debug-Hilfe
        return f"<RunSurface {self.surface_type} of {self.run_id}>"


class RunArtifact(Base):
    """Eine vom Lauf erzeugte Datei.

    Als Zeilen statt als Spaltensatz, weil `profile_paths` eine Liste
    variabler Länge ist und der SaaS-Plan die Artefakte später nach
    S3/MinIO verschieben will — dann kommt hier eine `storage_key`-Spalte
    dazu und sonst nichts.
    """

    __tablename__ = "run_artifacts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    #: Zusatzinfo je Artefakt — bei 'profile' die Dicts aus profile_paths.
    meta: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    run: Mapped[Run] = relationship(back_populates="artifacts")

    __table_args__ = (
        _enum_check("kind", ARTIFACT_KINDS),
        Index("ix_run_artifacts_run_kind", "run_id", "kind"),
    )

    def __repr__(self) -> str:  # pragma: no cover - Debug-Hilfe
        return f"<RunArtifact {self.kind} of {self.run_id}>"


__all__ = [
    "ARTIFACT_KINDS",
    "RUN_STATUSES",
    "STORAGE_SRID",
    "Base",
    "Project",
    "Run",
    "RunArtifact",
    "RunSurface",
]
