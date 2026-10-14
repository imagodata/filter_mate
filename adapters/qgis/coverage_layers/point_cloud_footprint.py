# -*- coding: utf-8 -*-
"""
Footprint of the points kept by a point cloud selection.

The layer's subset string (the EXPLORING selection, once applied) is honored
by ``QgsPointCloudDataProvider.identify``, which reads the COPC / EPT octree
at the level of detail matching ``resolution``: a coarse resolution reads few
points even on a 25 million point tile. The points are binned on a grid and
the occupied cells are polygonized.

Measured on a LiDAR HD tile (25.1 M points, Classification = 6): 25 780
points read in 1.8 s at 2 m.
"""
import logging
import math
from dataclasses import dataclass
from typing import Optional

from qgis.core import QgsDoubleRange, QgsGeometry, QgsRectangle

logger = logging.getLogger(__name__)

DEFAULT_RESOLUTION = 2.0
DEFAULT_POINTS_LIMIT = 3000000


@dataclass
class FootprintResult:
    geometry: QgsGeometry
    points_read: int
    cell_size: float


def footprint_geometry(layer, resolution: float = DEFAULT_RESOLUTION, extent: Optional[QgsRectangle] = None,
                       points_limit: int = DEFAULT_POINTS_LIMIT, dilate_cells: int = 1) -> FootprintResult:
    """Polygon covering the points of ``layer`` that pass its subset string.

    Args:
        layer: QgsPointCloudLayer (its current subset is the selection).
        resolution: Grid cell size in layer CRS units; also the level of detail read.
        extent: Area to scan (layer extent by default).
        points_limit: Maximum number of points read.
        dilate_cells: Grow the occupied cells by this many cells to close gaps.

    Returns:
        :class:`FootprintResult`, with an empty geometry when no point passes.
    """
    import numpy as np
    from .geometry_tools import mask_to_geometry

    resolution = float(resolution or DEFAULT_RESOLUTION)
    area = extent if extent is not None and not extent.isEmpty() else layer.extent()
    provider = layer.dataProvider()
    points = provider.identify(resolution, QgsGeometry.fromRect(area), QgsDoubleRange(), int(points_limit))
    if not points:
        return FootprintResult(QgsGeometry(), 0, resolution)
    xs = np.fromiter((p.get('X', 0.0) for p in points), dtype='float64', count=len(points))
    ys = np.fromiter((p.get('Y', 0.0) for p in points), dtype='float64', count=len(points))
    cols = max(1, int(math.ceil(area.width() / resolution)))
    rows = max(1, int(math.ceil(area.height() / resolution)))
    ci = np.clip(((xs - area.xMinimum()) / resolution).astype('int64'), 0, cols - 1)
    ri = np.clip(((area.yMaximum() - ys) / resolution).astype('int64'), 0, rows - 1)
    grid = np.zeros((rows, cols), dtype='uint8')
    grid[ri, ci] = 1
    for _ in range(max(0, int(dilate_cells))):
        grown = grid.copy()
        grown[1:, :] |= grid[:-1, :]
        grown[:-1, :] |= grid[1:, :]
        grown[:, 1:] |= grid[:, :-1]
        grown[:, :-1] |= grid[:, 1:]
        grid = grown
    geotransform = (area.xMinimum(), resolution, 0.0, area.yMaximum(), 0.0, -resolution)
    geometry = mask_to_geometry(grid, geotransform, layer.crs().toWkt(), sieve_pixels=0, simplify_tolerance=resolution * 0.5)
    return FootprintResult(geometry, len(points), resolution)
