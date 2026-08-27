"""Alembic-Umgebung für das WTEC-Schema."""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Projektwurzel in den Pfad, damit `app.core.models` importierbar ist —
# auch wenn Alembic aus einem anderen Arbeitsverzeichnis läuft.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.models import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Von PostGIS selbst verwaltete Objekte. Ohne Filter schlägt
# `alembic revision --autogenerate` vor, sie zu löschen, weil sie in
# target_metadata fehlen.
POSTGIS_TABLES = {
    "spatial_ref_sys",
    "geography_columns",
    "geometry_columns",
    "raster_columns",
    "raster_overviews",
}


def _get_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL ist nicht gesetzt — Alembic braucht dieselbe URL wie die Anwendung."
        )
    return url


def include_object(object_, name, type_, reflected, compare_to) -> bool:
    """Fremde Tabellen aus Autogenerate heraushalten.

    Die Datenbank teilt sich `public` mit PostGIS (`spatial_ref_sys`) und —
    über den `search_path` des postgis_tiger_geocoder — mit rund vierzig
    tiger-Tabellen. Reflektierte Tabellen, die nicht in unserem Metadata
    stehen, gehören uns nicht: Alembic soll sie weder anfassen noch zum
    Löschen vorschlagen.

    Der Preis ist, dass eine wirklich entfernte eigene Tabelle nicht mehr
    automatisch erkannt wird — deren `drop_table` schreibt man von Hand.
    """
    if type_ == "table":
        if name in POSTGIS_TABLES:
            return False
        if reflected and name not in target_metadata.tables:
            return False
    if type_ == "index" and getattr(object_, "table", None) is not None:
        if object_.table.name not in target_metadata.tables:
            return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        include_object=include_object,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _get_url()

    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)

    with connectable.connect() as connection:
        # tiger/topology aus dem search_path nehmen, damit ihre Tabellen gar
        # nicht erst reflektiert werden. Unser Schema liegt komplett in public,
        # die PostGIS-Funktionen ebenfalls.
        connection.exec_driver_sql("SET search_path TO public")

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
