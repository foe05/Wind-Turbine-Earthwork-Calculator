"""initial schema: projects, runs, run_surfaces, run_artifacts

Revision ID: 0001
Revises:
Create Date: 2026-08-27

Erste Fassung der Persistenz. Bis hierher lief die Anwendung ohne
Datenbank — der Postgres-Container stand, wurde aber von keinem Modul
benutzt.

Bewusste Entscheidungen, die später schwer zu ändern sind:

* Geometrien liegen in EPSG:4326, nicht im Arbeits-CRS. Ein fester SRID
  hält Läufe aus verschiedenen UTM-Zonen über einen gemeinsamen Index
  abfragbar; das Arbeits-CRS steht je Lauf in `runs.crs_epsg`.
* `text` + CHECK statt nativer PG-Enums, damit neue Flächentypen eine
  gewöhnliche Constraint-Migration bleiben.
* Kein `organization_id`. Solange Single-Tenant gilt, wäre die Spalte tote
  Fracht; für Multi-Tenancy ist `projects` der eine Anker, an dem der FK
  später hängt.
"""

from __future__ import annotations

from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SURFACE_TYPES = (
    "kranstellflaeche",
    "fundamentflaeche",
    "auslegerflaeche",
    "rotorflaeche",
    "zufahrt",
    "holme",
)

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

RUN_STATUSES = ("running", "succeeded", "failed")


def _in_list(column: str, values: Sequence[str]) -> str:
    return "{} IN ({})".format(column, ", ".join(f"'{v}'" for v in values))


def upgrade() -> None:
    # Auf dem bestehenden Container längst vorhanden; für frische
    # Installationen trotzdem hier, damit die Migration allein genügt.
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "projects",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("crs_epsg", sa.Integer(), nullable=False, server_default="25832"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("inputs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("crs_epsg", sa.Integer(), nullable=False),
        sa.Column("output_dir", sa.Text(), nullable=False),
        sa.Column("dem_path", sa.Text(), nullable=True),
        sa.Column("fok", sa.Float(), nullable=True),
        sa.Column("foundation_depth", sa.Float(), nullable=True),
        sa.Column("gravel_thickness", sa.Float(), nullable=True),
        sa.Column("crane_optimum_height", sa.Float(), nullable=True),
        sa.Column("boom_slope_percent", sa.Float(), nullable=True),
        sa.Column("rotor_offset_m", sa.Float(), nullable=True),
        sa.Column("road_slope_percent", sa.Float(), nullable=True),
        sa.Column("total_cut_m3", sa.Float(), nullable=True),
        sa.Column("total_fill_m3", sa.Float(), nullable=True),
        sa.Column(
            "net_m3",
            sa.Float(),
            sa.Computed("total_cut_m3 - total_fill_m3", persisted=True),
            nullable=True,
        ),
        sa.Column("co2_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("phase_plan", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("strata_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(_in_list("status", RUN_STATUSES), name="ck_status"),
    )
    op.create_index("ix_runs_project_started", "runs", ["project_id", sa.text("started_at DESC")])

    op.create_table(
        "run_surfaces",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("surface_type", sa.String(length=32), nullable=False),
        sa.Column(
            "geom",
            geoalchemy2.Geometry(
                geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False, from_text="ST_GeomFromEWKT", name="geometry"
            ),
            nullable=True,
        ),
        sa.Column("plateau_height", sa.Float(), nullable=False),
        sa.Column("cut_m3", sa.Float(), nullable=False),
        sa.Column("fill_m3", sa.Float(), nullable=False),
        sa.Column("platform_area_m2", sa.Float(), nullable=False),
        sa.Column("terrain_min", sa.Float(), nullable=False),
        sa.Column("terrain_max", sa.Float(), nullable=False),
        sa.Column("terrain_mean", sa.Float(), nullable=False),
        sa.Column("num_pixels", sa.Integer(), nullable=False),
        sa.Column("slope_cut_m3", sa.Float(), nullable=True),
        sa.Column("slope_fill_m3", sa.Float(), nullable=True),
        sa.Column("slope_area_m2", sa.Float(), nullable=True),
        sa.Column("avg_slope_width_m", sa.Float(), nullable=True),
        sa.Column("slope_samples", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("run_id", "surface_type"),
        sa.CheckConstraint(_in_list("surface_type", SURFACE_TYPES), name="ck_surface_type"),
    )
    op.create_index("ix_run_surfaces_geom", "run_surfaces", ["geom"], postgresql_using="gist")

    op.create_table(
        "run_artifacts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(_in_list("kind", ARTIFACT_KINDS), name="ck_kind"),
    )
    op.create_index("ix_run_artifacts_run_kind", "run_artifacts", ["run_id", "kind"])


def downgrade() -> None:
    op.drop_index("ix_run_artifacts_run_kind", table_name="run_artifacts")
    op.drop_table("run_artifacts")
    op.drop_index("ix_run_surfaces_geom", table_name="run_surfaces", postgresql_using="gist")
    op.drop_table("run_surfaces")
    op.drop_index("ix_runs_project_started", table_name="runs")
    op.drop_table("runs")
    op.drop_table("projects")
    # postgis wird bewusst nicht entfernt: die Extension kann älter sein als
    # dieses Schema und von anderen Objekten benutzt werden.
