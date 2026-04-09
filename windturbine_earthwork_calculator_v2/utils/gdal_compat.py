"""
GDAL compatibility helpers.

Some QGIS installations ship a Python environment where GDAL's `_gdal_array`
extension cannot import numpy (typical error:
``numpy.core.multiarray failed to import``). As a consequence the standard
``band.ReadAsArray()`` / ``band.WriteArray()`` helpers raise on every call
and all DEM sampling and terrain-intersection rasters silently fail.

This module provides drop-in replacements that go through the plain SWIG
``ReadRaster`` / ``WriteRaster`` API. That path returns raw Python bytes
and never touches ``_gdal_array`` at all, so it works in environments where
numpy is installed for plain Python code but GDAL's numpy binding is broken.

Author: Wind Energy Site Planning
"""

from typing import Optional

import numpy as np

try:
    from osgeo import gdal
    GDAL_AVAILABLE = True
except ImportError:
    GDAL_AVAILABLE = False
    gdal = None  # type: ignore


# Mapping GDAL data type codes -> numpy dtype. Covers the types we actually
# use (DEM rasters: Float32/Float64, masks: Byte).
_GDAL_TO_NUMPY = {}
if GDAL_AVAILABLE:
    _GDAL_TO_NUMPY = {
        gdal.GDT_Byte: np.uint8,
        gdal.GDT_UInt16: np.uint16,
        gdal.GDT_Int16: np.int16,
        gdal.GDT_UInt32: np.uint32,
        gdal.GDT_Int32: np.int32,
        gdal.GDT_Float32: np.float32,
        gdal.GDT_Float64: np.float64,
    }


def read_band_as_array(
    band,
    xoff: int = 0,
    yoff: int = 0,
    win_xsize: Optional[int] = None,
    win_ysize: Optional[int] = None,
) -> np.ndarray:
    """
    Drop-in replacement for ``band.ReadAsArray(xoff, yoff, xsize, ysize)``.

    Uses ``band.ReadRaster()`` under the hood and reconstructs the numpy
    array via ``np.frombuffer``. This avoids GDAL's ``_gdal_array`` numpy
    extension, which is broken on some QGIS Linux builds.

    Args:
        band: An ``osgeo.gdal.Band`` instance.
        xoff, yoff: Pixel offset of the window (default 0).
        win_xsize, win_ysize: Window size in pixels. If ``None``, the full
            band is read.

    Returns:
        A 2D numpy array of shape ``(win_ysize, win_xsize)`` with the
        band's native dtype.

    Raises:
        RuntimeError: If GDAL is not available or ``ReadRaster`` returns
            ``None``.
    """
    if not GDAL_AVAILABLE:
        raise RuntimeError("GDAL is not available")

    if win_xsize is None:
        win_xsize = band.XSize
    if win_ysize is None:
        win_ysize = band.YSize

    buf = band.ReadRaster(xoff, yoff, win_xsize, win_ysize)
    if buf is None:
        raise RuntimeError(
            f"ReadRaster returned None for band at "
            f"({xoff},{yoff}) {win_xsize}x{win_ysize}"
        )

    np_dtype = _GDAL_TO_NUMPY.get(band.DataType)
    if np_dtype is None:
        raise RuntimeError(
            f"Unsupported GDAL data type code: {band.DataType}"
        )

    # np.frombuffer creates a read-only view; copy so callers can modify.
    arr = np.frombuffer(buf, dtype=np_dtype).reshape(win_ysize, win_xsize)
    return arr.copy()


def write_array_to_band(band, array: np.ndarray, xoff: int = 0, yoff: int = 0) -> None:
    """
    Drop-in replacement for ``band.WriteArray(array, xoff, yoff)``.

    Uses ``band.WriteRaster()`` with raw bytes so it does not depend on
    GDAL's ``_gdal_array`` extension.

    Args:
        band: An ``osgeo.gdal.Band`` instance.
        array: 2D numpy array whose dtype must match the band's data type.
        xoff, yoff: Pixel offset for the write (default 0).
    """
    if not GDAL_AVAILABLE:
        raise RuntimeError("GDAL is not available")

    np_dtype = _GDAL_TO_NUMPY.get(band.DataType)
    if np_dtype is None:
        raise RuntimeError(
            f"Unsupported GDAL data type code: {band.DataType}"
        )

    # Ensure contiguous buffer with the right dtype.
    if array.dtype != np_dtype:
        array = array.astype(np_dtype, copy=False)
    if not array.flags['C_CONTIGUOUS']:
        array = np.ascontiguousarray(array)

    win_ysize, win_xsize = array.shape
    band.WriteRaster(xoff, yoff, win_xsize, win_ysize, array.tobytes())
