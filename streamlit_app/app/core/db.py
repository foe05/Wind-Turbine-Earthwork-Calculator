"""
Datenbank-Anbindung: Engine, Session und Geometrie-Konvertierung.

Die Anwendung läuft bewusst weiter, wenn `DATABASE_URL` fehlt — die
Persistenz ist additiv, der Rechenkern hängt nicht an ihr. Aufrufer prüfen
mit `is_configured()`, bevor sie eine Session öffnen.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator, Optional

from geoalchemy2.shape import from_shape
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shapely_transform
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import STORAGE_SRID


def database_url() -> Optional[str]:
    """URL aus der Umgebung, oder None wenn keine Datenbank konfiguriert ist."""
    return os.environ.get("DATABASE_URL") or None


def is_configured() -> bool:
    return database_url() is not None


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Engine für die konfigurierte Datenbank (einmalig pro Prozess).

    `pool_pre_ping` ist gesetzt, weil Streamlit-Sessions lange leben und
    ein Neustart des DB-Containers sonst abgestandene Verbindungen
    hinterlässt.
    """
    url = database_url()
    if url is None:
        raise RuntimeError(
            "DATABASE_URL ist nicht gesetzt — vor get_engine() mit is_configured() prüfen."
        )
    return create_engine(url, pool_pre_ping=True, future=True)


@lru_cache(maxsize=1)
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Session mit Commit bei Erfolg und Rollback im Fehlerfall."""
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def to_storage_geometry(geom: BaseGeometry, crs_epsg: int):
    """Shapely-Geometrie aus dem Arbeits-CRS in die Speicherform überführen.

    Ergebnis ist immer ein MultiPolygon in EPSG:4326 (siehe `models`):
    ein gemeinsamer SRID hält Läufe aus verschiedenen UTM-Zonen räumlich
    vergleichbar. Die gerechneten Volumen und Flächen bleiben davon
    unberührt — die sind im nativen CRS entstanden und werden als Zahlen
    gespeichert.
    """
    if geom is None or geom.is_empty:
        return None

    if int(crs_epsg) != STORAGE_SRID:
        # Import lokal: pyproj wird nur gebraucht, wenn wirklich transformiert
        # werden muss, und der Rechenkern soll ohne DB-Modul importierbar bleiben.
        from pyproj import Transformer

        transformer = Transformer.from_crs(
            f"EPSG:{int(crs_epsg)}", f"EPSG:{STORAGE_SRID}", always_xy=True
        )
        geom = shapely_transform(transformer.transform, geom)

    if isinstance(geom, Polygon):
        geom = MultiPolygon([geom])

    return from_shape(geom, srid=STORAGE_SRID)


def multipolygon_from(geoms, crs_epsg: int):
    """Mehrere Polygone (z. B. die Holme) als ein MultiPolygon ablegen."""
    parts: list[Polygon] = []
    for g in geoms or []:
        if g is None or g.is_empty:
            continue
        if isinstance(g, MultiPolygon):
            parts.extend(g.geoms)
        else:
            parts.append(g)
    if not parts:
        return None
    return to_storage_geometry(MultiPolygon(parts), crs_epsg)


__all__ = [
    "database_url",
    "get_engine",
    "get_sessionmaker",
    "is_configured",
    "multipolygon_from",
    "session_scope",
    "to_storage_geometry",
]
