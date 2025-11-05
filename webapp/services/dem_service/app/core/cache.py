"""
DEM Cache Management mit Redis

Cache-Strategie:
- Redis: Kachel-Daten (Base64) mit 6 Monaten TTL
- PostgreSQL: Metadaten über DEM-Anfragen
- Dateisystem: GeoTIFF-Dateien
"""
import json
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta
import redis
from pathlib import Path

logger = logging.getLogger(__name__)

# Cache TTL: 6 Monate
CACHE_TTL_SECONDS = 15552000  # 6 * 30 * 24 * 60 * 60


class DEMCache:
    """DEM Cache Manager mit Redis"""

    def __init__(self, redis_url: str, cache_dir: Path):
        """
        Initialize cache

        Args:
            redis_url: Redis connection URL
            cache_dir: Directory for file cache
        """
        self.redis_client = redis.from_url(redis_url, decode_responses=False)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"DEM Cache initialisiert: Redis={redis_url}, Dir={cache_dir}")

    def _get_tile_key(self, zone: int, easting: float, northing: float) -> str:
        """
        Generate Redis key for tile

        Format: dem:tile:{zone}_{easting}_{northing}
        """
        # Runde auf 1km-Raster
        tile_easting = int(easting / 1000) * 1000 + 500
        tile_northing = int(northing / 1000) * 1000 + 500

        return f"dem:tile:{zone}_{int(tile_easting)}_{int(tile_northing)}"

    def get_tile(
        self,
        zone: int,
        easting: float,
        northing: float
    ) -> Optional[Dict]:
        """
        Get tile from cache

        Args:
            zone: UTM zone
            easting: Easting coordinate
            northing: Northing coordinate

        Returns:
            Dict with tile data or None if not cached
        """
        key = self._get_tile_key(zone, easting, northing)

        try:
            cached_data = self.redis_client.get(key)

            if cached_data:
                tile_data = json.loads(cached_data)

                logger.info(
                    f"  💾 Cache-Hit: Zone {zone}, "
                    f"E={int(easting)}, N={int(northing)}"
                )

                return tile_data

            return None

        except Exception as e:
            logger.error(f"Cache-Read-Fehler: {e}")
            return None

    def set_tile(
        self,
        zone: int,
        easting: float,
        northing: float,
        tile_data: Dict,
        ttl_seconds: int = CACHE_TTL_SECONDS
    ) -> bool:
        """
        Store tile in cache

        Args:
            zone: UTM zone
            easting: Easting coordinate
            northing: Northing coordinate
            tile_data: Tile data dict (with 'data', 'attribution', etc.)
            ttl_seconds: Time to live in seconds

        Returns:
            True if successful
        """
        key = self._get_tile_key(zone, easting, northing)

        try:
            # Add cache metadata
            tile_data['cached_at'] = datetime.utcnow().isoformat()
            tile_data['expires_at'] = (
                datetime.utcnow() + timedelta(seconds=ttl_seconds)
            ).isoformat()

            # Store in Redis with TTL
            self.redis_client.setex(
                key,
                ttl_seconds,
                json.dumps(tile_data)
            )

            logger.info(
                f"  💾 Cache gespeichert: Zone {zone}, "
                f"E={int(easting)}, N={int(northing)}"
            )

            return True

        except Exception as e:
            logger.error(f"Cache-Write-Fehler: {e}")
            return False

    def get_tile_file_path(
        self,
        zone: int,
        easting: float,
        northing: float
    ) -> Path:
        """
        Get file path for tile GeoTIFF

        Args:
            zone: UTM zone
            easting: Easting coordinate
            northing: Northing coordinate

        Returns:
            Path to GeoTIFF file
        """
        tile_easting = int(easting / 1000) * 1000 + 500
        tile_northing = int(northing / 1000) * 1000 + 500

        filename = f"dem_z{zone}_e{tile_easting}_n{tile_northing}.tif"

        return self.cache_dir / filename

    def tile_file_exists(
        self,
        zone: int,
        easting: float,
        northing: float
    ) -> bool:
        """Check if tile file exists on disk"""
        file_path = self.get_tile_file_path(zone, easting, northing)
        return file_path.exists()

    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics

        Returns:
            Dict with cache stats
        """
        try:
            info = self.redis_client.info()

            # Count DEM tiles in cache
            tile_keys = self.redis_client.keys("dem:tile:*")
            tile_count = len(tile_keys) if tile_keys else 0

            # File cache
            file_count = len(list(self.cache_dir.glob("*.tif")))
            total_size = sum(
                f.stat().st_size for f in self.cache_dir.glob("*.tif")
            )

            return {
                "redis": {
                    "connected": True,
                    "used_memory_human": info.get("used_memory_human", "N/A"),
                    "tile_keys": tile_count
                },
                "file_cache": {
                    "directory": str(self.cache_dir),
                    "tile_count": file_count,
                    "total_size_mb": round(total_size / (1024 * 1024), 2)
                }
            }

        except Exception as e:
            logger.error(f"Cache-Stats-Fehler: {e}")
            return {
                "error": str(e)
            }

    def clear_expired(self) -> int:
        """
        Clear expired tiles from file cache

        Redis handles TTL automatically.
        This clears old files based on modification time.

        Returns:
            Number of files deleted
        """
        deleted = 0
        cutoff = datetime.utcnow() - timedelta(seconds=CACHE_TTL_SECONDS)

        try:
            for file_path in self.cache_dir.glob("*.tif"):
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

                if mtime < cutoff:
                    file_path.unlink()
                    deleted += 1
                    logger.debug(f"Gelöscht: {file_path.name}")

            if deleted > 0:
                logger.info(f"Cache-Cleanup: {deleted} Dateien gelöscht")

            return deleted

        except Exception as e:
            logger.error(f"Cache-Cleanup-Fehler: {e}")
            return 0
