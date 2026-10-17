# -*- coding: utf-8 -*-
"""Terrain derivatives of an elevation grid (slope, aspect, hillshade, roughness).

Pure numpy, no QGIS: the arrays are the ones :func:`raster_adapter.read_band_array`
returns (float64, NaN for NoData). Slope, aspect and hillshade use the Horn
3 x 3 kernel, the one of ``gdaldem`` and of the QGIS slope / aspect algorithms;
roughness is the Terrain Ruggedness Index of Wilson (mean absolute difference
between a pixel and its eight neighbours).

A pixel whose 3 x 3 neighbourhood holds a NoData is NaN, a flat pixel has no
aspect (NaN). The border of the grid is computed on a linear extrapolation of
its edge (a plane keeps its slope up to the last pixel, as ``gdaldem -compute_edges``).
"""
import math
from typing import Tuple

from ....core.domain.raster_filter_criteria import RasterDerivative

# Metres per degree at the equator, WGS84 (mean values are enough for a filter threshold).
_METRES_PER_DEGREE_LAT = 110574.0
_METRES_PER_DEGREE_LON = 111320.0

HILLSHADE_AZIMUTH = 315.0
HILLSHADE_ALTITUDE = 45.0


def ground_cell_size(cell_x: float, cell_y: float, geographic: bool, latitude: float = 0.0,
                     mercator: bool = False) -> Tuple[float, float]:
    """Cell size in ground units: degrees are converted to metres at ``latitude``.

    Args:
        cell_x: Pixel width in CRS units.
        cell_y: Pixel height in CRS units (absolute value is used).
        geographic: True when the CRS units are degrees.
        latitude: Latitude of the raster centre, degrees.
        mercator: True for Web Mercator (EPSG:3857): its metres stretch by 1 / cos(latitude).

    Returns:
        ``(size_x, size_y)`` in the unit of the elevations (metres).
    """
    cell_x, cell_y = abs(float(cell_x)), abs(float(cell_y))
    if mercator:
        scale = max(math.cos(math.radians(latitude)), 1e-6)
        return cell_x * scale, cell_y * scale
    if not geographic:
        return cell_x, cell_y
    return (cell_x * _METRES_PER_DEGREE_LON * max(math.cos(math.radians(latitude)), 1e-6),
            cell_y * _METRES_PER_DEGREE_LAT)


def _neighbours(array):
    """The nine shifted views of ``array`` padded on its edge, named like a 3 x 3 window.

    ``a b c / d e f / g h i``, row 0 being the north row.
    """
    import numpy as np
    rows, cols = array.shape
    # Odd reflection: the pad value is 2 * edge - neighbour, a linear extrapolation (needs 2 pixels).
    padded = np.pad(array, 1, mode='reflect', reflect_type='odd') if min(rows, cols) > 1 else np.pad(array, 1, mode='edge')
    view = lambda dy, dx: padded[1 + dy:1 + dy + rows, 1 + dx:1 + dx + cols]  # noqa: E731
    return (view(-1, -1), view(-1, 0), view(-1, 1),
            view(0, -1), view(0, 0), view(0, 1),
            view(1, -1), view(1, 0), view(1, 1))


def _gradient(array, size_x: float, size_y: float):
    """Horn gradient ``(dz/dx towards east, dz/dy towards north)``."""
    a, b, c, d, _e, f, g, h, i = _neighbours(array)
    dzdx = ((c + 2 * f + i) - (a + 2 * d + g)) / (8.0 * size_x)
    dzdy = ((a + 2 * b + c) - (g + 2 * h + i)) / (8.0 * size_y)
    return dzdx, dzdy


def derive(array, derivative: RasterDerivative, size_x: float, size_y: float):
    """``derivative`` of the elevation grid ``array``.

    Args:
        array: 2D float array, row 0 to the north, NaN for NoData.
        derivative: What to compute; ``VALUE`` returns ``array`` itself.
        size_x: Ground pixel width, same unit as the elevations (see :func:`ground_cell_size`).
        size_y: Ground pixel height.

    Returns:
        Float array of the same shape, NaN where undefined. Slope in degrees or
        percent, aspect in degrees clockwise from north of the downhill direction
        ([0, 360[), hillshade 0-255 (sun at 315 deg, 45 deg high), roughness in
        elevation units.
    """
    import numpy as np
    if derivative is RasterDerivative.VALUE:
        return array
    if size_x <= 0 or size_y <= 0:
        raise ValueError(f"cell size must be positive, got {size_x} x {size_y}")
    if derivative is RasterDerivative.ROUGHNESS:
        neighbours = _neighbours(array)
        centre = neighbours[4]
        total = sum(np.abs(n - centre) for index, n in enumerate(neighbours) if index != 4)
        result = total / 8.0
    else:
        dzdx, dzdy = _gradient(array, size_x, size_y)
        steepness = np.hypot(dzdx, dzdy)
        if derivative is RasterDerivative.SLOPE_DEGREES:
            result = np.degrees(np.arctan(steepness))
        elif derivative is RasterDerivative.SLOPE_PERCENT:
            result = steepness * 100.0
        elif derivative is RasterDerivative.ASPECT:
            result = np.degrees(np.arctan2(-dzdx, -dzdy)) % 360.0
            result[steepness == 0] = np.nan
        elif derivative is RasterDerivative.HILLSHADE:
            azimuth, altitude = math.radians(HILLSHADE_AZIMUTH), math.radians(HILLSHADE_ALTITUDE)
            sun = (math.sin(azimuth) * math.cos(altitude), math.cos(azimuth) * math.cos(altitude), math.sin(altitude))
            # Unit normal of the surface z(x, y): (-dz/dx, -dz/dy, 1) / norm.
            lit = (-dzdx * sun[0] - dzdy * sun[1] + sun[2]) / np.sqrt(1.0 + steepness ** 2)
            result = 255.0 * np.clip(lit, 0.0, None)
        else:
            raise ValueError(f"unknown derivative {derivative!r}")
    # A NoData in the neighbourhood already made the sums NaN; the kernel ignores the centre
    # pixel, so a NoData pixel of valid surroundings is masked here.
    result = np.where(np.isnan(array), np.nan, result)
    return result
