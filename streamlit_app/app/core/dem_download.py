"""
DEM-Download (portiert aus core/dem_downloader.py, QGIS-frei).

hoehendaten.de-Client mit Base64-TIFF-Response, Magic-Byte- und Size-Checks,
lokales Tile-Cache, Mosaik via rasterio.merge mit Nodata-Erhaltung und
Sanity-Check (Regressionsschutz gegen leere Mosaike, siehe Plugin-Commit 85f57f9).
"""

from __future__ import annotations

import base64
import json
import logging
import math
import re
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Iterable, Optional

import numpy as np
import rasterio
import requests
from rasterio.merge import merge as rio_merge

log = logging.getLogger(__name__)


def _safe_progress(progress: Optional[Callable[[str], None]], msg: str) -> None:
    """Ruft progress() defensiv auf. UI-Callbacks (z. B. Streamlit st.status.write)
    sind häufig nicht thread-safe — Exceptions aus dem Callback dürfen NICHT
    die Download-Logik abbrechen."""
    if not progress:
        return
    try:
        progress(msg)
    except Exception:
        # Bewusst stumm — Logging des Download-Status liegt ohnehin in `log`.
        log.debug("progress callback failed (ignored)", exc_info=True)


class DEMDownloader:
    """hoehendaten.de DGM1-Tiles laden + rasterio-Mosaik bauen."""

    API_BASE_URL = "https://api.hoehendaten.de:14444/v1/rawtif"
    TILE_SIZE = 1000  # 1 km × 1 km
    TILE_PREFIX = "dgm1_32"
    TILE_RESOLUTION = "1m"

    # ~50 MB pro 1 km² float-TIFF reicht generös; Magic-Bytes für TIFF/BigTIFF
    MAX_TIFF_SIZE_BYTES = 50 * 1024 * 1024
    _TIFF_MAGIC = (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+")
    _TILE_NAME_RE = re.compile(r"^dgm1_\d+_\d+_\d+_1m$")

    def __init__(self, cache_dir: str | Path, force_refresh: bool = False):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.force_refresh = force_refresh

    # ------------------------------------------------------- Tile-Berechnung

    def calculate_tiles(
        self, bbox: tuple[float, float, float, float], buffer_m: float = 250.0
    ) -> list[str]:
        """bbox=(minx, miny, maxx, maxy) in EPSG:25832 -> Tile-Namen."""
        minx, miny, maxx, maxy = bbox
        minx -= buffer_m
        miny -= buffer_m
        maxx += buffer_m
        maxy += buffer_m

        min_e_km = math.floor(minx / self.TILE_SIZE)
        max_e_km = math.floor(maxx / self.TILE_SIZE)
        min_n_km = math.floor(miny / self.TILE_SIZE)
        max_n_km = math.floor(maxy / self.TILE_SIZE)

        tiles = [
            f"{self.TILE_PREFIX}_{e_km}_{n_km}_{self.TILE_RESOLUTION}"
            for e_km in range(min_e_km, max_e_km + 1)
            for n_km in range(min_n_km, max_n_km + 1)
        ]
        if len(tiles) > 10:
            log.warning(
                "Große DEM-Fläche angefordert: %d km² (%d Tiles) — Sampling lädt das volle DEM in RAM.",
                len(tiles),
                len(tiles),
            )
        return tiles

    # ----------------------------------------------------- Single-Tile-Load

    def download_tile(
        self, tile_name: str, timeout: int = 30, progress: Optional[Callable[[str], None]] = None
    ) -> Optional[str]:
        """Lädt einen Tile von hoehendaten.de in den Cache. None bei Fehler."""
        if not self._TILE_NAME_RE.match(tile_name):
            log.error("Ungültiges Tile-Namen-Format: %r", tile_name)
            return None

        tile_path = self.cache_dir / f"{tile_name}.tif"
        if tile_path.exists() and not self.force_refresh:
            _safe_progress(progress, f"Cache-Hit: {tile_name}")
            return str(tile_path)

        parts = tile_name.split("_")
        zone = int(parts[1])
        easting = int(parts[2]) * 1000 + 500
        northing = int(parts[3]) * 1000 + 500
        payload = {
            "Type": "RawTIFRequest",
            "ID": tile_name,
            "Attributes": {"Zone": zone, "Easting": float(easting), "Northing": float(northing)},
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
        }

        log.info("Lade Tile %s (Zone=%s E=%s N=%s)", tile_name, zone, easting, northing)
        _safe_progress(progress, f"Lade Tile {tile_name}…")

        try:
            resp = requests.post(
                self.API_BASE_URL,
                data=json.dumps(payload),
                headers=headers,
                timeout=timeout,
                stream=True,
            )
            if resp.status_code != 200:
                log.warning("Tile %s nicht verfügbar (HTTP %d)", tile_name, resp.status_code)
                return None
            resp.raise_for_status()
            body = resp.json()
        except requests.RequestException as e:
            log.error("Fehler beim Laden %s: %s", tile_name, e)
            return None
        except ValueError as e:  # JSONDecodeError
            log.error("Antwort für %s ist kein gültiges JSON: %s", tile_name, e)
            return None

        if body.get("Type") != "RawTIFResponse":
            log.error("Unerwarteter Antwort-Typ: %s", body.get("Type"))
            return None
        raw = body.get("Attributes", {}).get("RawTIFs", [])
        if not raw:
            log.error("Keine RawTIFs in Antwort für %s", tile_name)
            return None
        b64 = raw[0].get("Data", "")
        if not b64:
            log.error("Leeres TIFF-Datenfeld für %s", tile_name)
            return None
        if len(b64) > self.MAX_TIFF_SIZE_BYTES * 2:
            log.error("TIFF-Payload für %s überschreitet Limit", tile_name)
            return None

        try:
            tiff = base64.b64decode(b64)
        except Exception as e:
            log.error("Base64-Decode für %s fehlgeschlagen: %s", tile_name, e)
            return None

        if len(tiff) > self.MAX_TIFF_SIZE_BYTES:
            log.error("Decoded TIFF für %s über Limit (%d > %d)", tile_name, len(tiff), self.MAX_TIFF_SIZE_BYTES)
            return None
        if not tiff.startswith(self._TIFF_MAGIC):
            log.error("Antwort für %s ist kein TIFF (first 4: %r)", tile_name, tiff[:4])
            return None

        tile_path.write_bytes(tiff)
        log.info("Tile geladen: %s (%.2f MB)", tile_name, len(tiff) / 1024 / 1024)
        _safe_progress(progress, f"OK {tile_name} ({len(tiff) / 1024 / 1024:.2f} MB)")
        return str(tile_path)

    # ----------------------------------------------------- Parallel-Loading

    def download_tiles(
        self,
        tile_names: Iterable[str],
        max_workers: int = 4,
        progress: Optional[Callable[[str], None]] = None,
    ) -> list[str]:
        tile_names = list(tile_names)
        paths: list[str] = []
        # progress wird absichtlich NICHT in die Worker-Threads gegeben — UI-Callbacks
        # (Streamlit st.status etc.) sind häufig nicht thread-safe und werfen aus
        # einem Worker eine schwer abzufangende Exception. Stattdessen rufen wir
        # progress vom Main-Thread auf, sobald ein Worker fertig ist.
        total = len(tile_names)
        done = 0
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            fut_map = {ex.submit(self.download_tile, t): t for t in tile_names}
            for fut in as_completed(fut_map):
                t = fut_map[fut]
                done += 1
                try:
                    p = fut.result()
                except Exception as e:
                    log.error("Download-Exception %s: %s", t, repr(e))
                    p = None
                if p:
                    paths.append(p)
                    _safe_progress(progress, f"[{done}/{total}] OK {t}")
                else:
                    _safe_progress(progress, f"[{done}/{total}] FAIL {t}")
        return paths

    # ----------------------------------------------------------- Mosaik-IO

    def create_mosaic(self, tile_paths: list[str], output_path: str) -> str:
        """Mosaik aus mehreren Tiles via rasterio.merge mit Sanity-Check."""
        if not tile_paths:
            raise ValueError("Keine Tiles zum Mosaiken")
        if len(tile_paths) == 1:
            shutil.copy(tile_paths[0], output_path)
            return output_path

        log.info("Erzeuge Mosaik aus %d Tiles -> %s", len(tile_paths), output_path)
        srcs = [rasterio.open(p) for p in tile_paths]
        try:
            # Nodata aus dem ersten Tile übernehmen (DGM1 nutzt einheitlich denselben Wert);
            # Fallback -9999 wie im Plugin.
            src_nodata = srcs[0].nodata if srcs[0].nodata is not None else -9999.0
            mosaic, transform = rio_merge(srcs, nodata=src_nodata)

            profile = srcs[0].profile.copy()
            profile.update(
                driver="GTiff",
                height=mosaic.shape[1],
                width=mosaic.shape[2],
                transform=transform,
                count=1,
                dtype="float32",
                nodata=src_nodata,
                compress="lzw",
                tiled=True,
            )

            mosaic_f32 = mosaic.astype(np.float32, copy=False)
            with rasterio.open(output_path, "w", **profile) as dst:
                dst.write(mosaic_f32)

            # Sanity-Check (Regressionsschutz gegen Nodata-only-Mosaike):
            self._sanity_check_mosaic(output_path, src_nodata)
        finally:
            for s in srcs:
                s.close()
        return output_path

    @staticmethod
    def _sanity_check_mosaic(path: str, nodata_value: float) -> None:
        with rasterio.open(path) as ds:
            width = ds.width
            height = ds.height
            win = min(64, width, height)
            if win <= 0:
                return
            cx = max(0, (width - win) // 2)
            cy = max(0, (height - win) // 2)
            window = rasterio.windows.Window(cx, cy, win, win)
            sample = ds.read(1, window=window).astype(np.float32, copy=False)
        valid = sample[sample != np.float32(nodata_value)]
        if valid.size == 0:
            log.error(
                "Mosaik-Sanity-Check FAILED: Zentralfenster (%dx%d @ %d,%d) komplett Nodata. "
                "Cut/Fill-Volumina werden 0 sein.",
                win,
                win,
                cx,
                cy,
            )
            raise RuntimeError(
                "DEM-Mosaik ist leer (nur Nodata). Pipeline ist gebrochen, Berechnung abgebrochen."
            )
        log.info(
            "Mosaik-Sanity OK: min=%.2f max=%.2f mean=%.2f valid=%d/%d",
            float(valid.min()),
            float(valid.max()),
            float(valid.mean()),
            valid.size,
            sample.size,
        )

    # --------------------------------------------------- High-Level-Wrapper

    def download_for_bbox(
        self,
        bbox: tuple[float, float, float, float],
        output_path: str,
        buffer_m: float = 250.0,
        progress: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Komplett-Workflow: Tile-Namen berechnen, laden, mosaiken."""
        tiles = self.calculate_tiles(bbox, buffer_m=buffer_m)
        if not tiles:
            raise ValueError("Keine Tiles für BBox berechnet")
        _safe_progress(progress, f"Benötige {len(tiles)} Tile(s)")
        paths = self.download_tiles(tiles, progress=progress)
        if not paths:
            raise RuntimeError("Keine DEM-Tiles konnten geladen werden")
        if len(paths) < len(tiles):
            log.warning("Nur %d/%d Tiles geladen — Coverage unvollständig", len(paths), len(tiles))
        return self.create_mosaic(paths, output_path)

    # ------------------------------------------------------------- Cache

    def get_cache_info(self) -> dict:
        files = list(self.cache_dir.glob("*.tif"))
        return {
            "num_tiles": len(files),
            "total_size_mb": sum(f.stat().st_size for f in files) / 1024 / 1024,
            "cache_dir": str(self.cache_dir),
        }

    def clear_cache(self) -> int:
        files = list(self.cache_dir.glob("*.tif"))
        for f in files:
            f.unlink()
        return len(files)
