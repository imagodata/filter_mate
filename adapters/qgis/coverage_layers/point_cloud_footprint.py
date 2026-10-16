# -*- coding: utf-8 -*-
"""
Footprint of the points kept by a point cloud selection.

The layer's subset string (the EXPLORING selection, once applied) is honored
by ``QgsPointCloudDataProvider.identify``, which reads the COPC / EPT octree
at the level of detail matching ``resolution``: a coarse resolution reads few
points even on a 25 million point tile. The points are binned on a grid and
the occupied cells are polygonized.

``identify`` returns a Python dict of every attribute for each point (about
2 KB): the area is read in tiles of at most :data:`POINTS_PER_CALL` points,
of which only X / Y are kept, and the grid covers the points read, not the
whole layer (an EPT of 100 km at 2 m would be 2.5e9 cells).

Measured on a LiDAR HD tile (25.1 M points, Classification = 6): 25 780
points read in 1.8 s at 2 m.
"""
import logging
import math
from dataclasses import dataclass
from typing import Callable, List, Optional

from qgis.core import QgsDoubleRange, QgsGeometry, QgsRectangle

logger = logging.getLogger(__name__)

DEFAULT_RESOLUTION = 2.0
DEFAULT_POINTS_LIMIT = 3000000
# Points returned by one identify() call: a saturated tile is read again in four.
POINTS_PER_CALL = 200000
# A tile is not split below this many cells a side (it is then truncated).
MIN_TILE_CELLS = 64
# Occupancy grid size limit: above it the cells grow.
MAX_GRID_CELLS = 16000000
# Points of each identify() call checked against the selection.
CHECK_SAMPLE = 200

CheckFn = Callable[[List[dict]], None]


@dataclass
class FootprintResult:
    geometry: QgsGeometry
    points_read: int
    cell_size: float
    truncated: bool = False


def open_point_cloud(source: str, name: str, provider: str):
    """A private point cloud layer for a task: no statistics, no index generation (main thread).

    QGIS (seen on 3.44 and 4.2) decodes a block for the statistics task of a
    new layer with the filter of that moment, and caches it under the filter
    the layer has when the block is stored: a copy filtered right after it was
    opened then served every point of the file to ``identify``. Without the
    statistics task the copy never caches a block under a filter it did not
    decode with; without index generation it never starts a second indexing
    of a LAS file the project layer is already indexing.
    """
    from qgis.core import QgsPointCloudLayer
    options = QgsPointCloudLayer.LayerOptions()
    for option in ('skipStatisticsCalculation', 'skipIndexGeneration', 'skipCrsValidation'):
        if hasattr(options, option):
            setattr(options, option, True)
    options.loadDefaultStyle = False
    return QgsPointCloudLayer(source, name, provider, options)


def index_ready(layer) -> bool:
    """False when the layer has no usable point index (VPC, LAS still being indexed)."""
    provider = layer.dataProvider()
    if hasattr(provider, 'hasValidIndex'):  # every QGIS with point clouds (index() is not in Python before 3.42)
        return bool(provider.hasValidIndex())
    index = provider.index()
    return index is not None and index.isValid()


def selection_check(subset: str) -> Optional[CheckFn]:
    """Callable raising RuntimeError when sampled points fail ``subset``; None when there is nothing to check.

    The points returned by ``identify`` all pass the subset string, unless
    QGIS served a block cached without the filter: the footprint would then
    cover the whole cloud, so the run stops instead.
    """
    if not (subset or '').strip():
        return None
    from qgis.core import QgsExpression, QgsExpressionContext, QgsFeature, QgsField, QgsFields
    expression = QgsExpression(subset)
    if expression.hasParserError():
        return None
    state = {}

    def check(points: List[dict]) -> None:
        if not points or state.get('off'):
            return
        if 'names' not in state:
            names = list(points[0].keys())
            fields = QgsFields()
            for name in names:
                fields.append(QgsField(name))
            context = QgsExpressionContext()
            context.setFields(fields)
            expression.prepare(context)
            state.update(names=names, fields=fields, context=context)
        names, context = state['names'], state['context']
        feature = QgsFeature(state['fields'])
        step = max(1, len(points) // CHECK_SAMPLE)
        for point in points[::step][:CHECK_SAMPLE]:
            feature.setAttributes([point.get(name) for name in names])
            context.setFeature(feature)
            value = expression.evaluate(context)
            if expression.hasEvalError():
                state['off'] = True  # not a QGIS expression after all: no check
                return
            if not value:
                raise RuntimeError("QGIS returned points outside the selection (point cloud cache): "
                                   "the footprint was not computed")

    return check


def _quarters(tile: QgsRectangle, overlap: float) -> List[QgsRectangle]:
    """Four parts of ``tile``, overlapping by ``overlap``: identify() leaves out the points on an edge."""
    xm, ym = tile.center().x(), tile.center().y()
    parts = [QgsRectangle(tile.xMinimum(), tile.yMinimum(), xm, ym), QgsRectangle(xm, tile.yMinimum(), tile.xMaximum(), ym),
             QgsRectangle(tile.xMinimum(), ym, xm, tile.yMaximum()), QgsRectangle(xm, ym, tile.xMaximum(), tile.yMaximum())]
    for part in parts:
        part.grow(overlap)
    return parts


def _read_xy(provider, resolution: float, area: QgsRectangle, points_limit: int,
             is_canceled: Optional[Callable[[], bool]], check: Optional[CheckFn]):
    """X and Y of the points of ``area`` (numpy arrays) and whether some were left out."""
    import numpy as np
    xs, ys = [], []
    total, truncated = 0, False
    tiles = [area]
    while tiles:
        if is_canceled is not None and is_canceled():
            break
        tile = tiles.pop()
        budget = min(POINTS_PER_CALL, points_limit - total)
        if budget <= 0:
            truncated = True
            break
        points = provider.identify(resolution, QgsGeometry.fromRect(tile), QgsDoubleRange(), budget)
        if len(points) >= budget:
            if budget == POINTS_PER_CALL and min(tile.width(), tile.height()) > 2 * MIN_TILE_CELLS * resolution:
                points = None  # noqa: F841 - not kept while the parts are read
                tiles.extend(_quarters(tile, resolution * 1e-3))  # saturated: the cached blocks are read again
                continue
            truncated = True
        if check is not None:
            check(points)
        xs.append(np.fromiter((p.get('X', 0.0) for p in points), dtype='float64', count=len(points)))
        ys.append(np.fromiter((p.get('Y', 0.0) for p in points), dtype='float64', count=len(points)))
        total += len(points)
        points = None  # noqa: F841 - the dicts go before the next call
    if not xs:
        return np.zeros(0), np.zeros(0), truncated
    return np.concatenate(xs), np.concatenate(ys), truncated


def footprint_geometry(layer, resolution: float = DEFAULT_RESOLUTION, extent: Optional[QgsRectangle] = None,
                       points_limit: int = DEFAULT_POINTS_LIMIT, dilate_cells: int = 1,
                       is_canceled: Optional[Callable[[], bool]] = None,
                       check: Optional[CheckFn] = None) -> FootprintResult:
    """Polygon covering the points of ``layer`` that pass its subset string.

    Args:
        layer: QgsPointCloudLayer (its current subset is the selection).
        resolution: Grid cell size in layer CRS units; also the level of detail read.
        extent: Area to scan (layer extent by default).
        points_limit: Maximum number of points read.
        dilate_cells: Grow the occupied cells by this many cells to close gaps.
        is_canceled: Polled between two reads; True stops reading.
        check: Called with the points of each read (see :func:`selection_check`).

    Returns:
        :class:`FootprintResult`, with an empty geometry when no point passes;
        ``truncated`` when ``points_limit`` left points out.
    """
    import numpy as np
    from .geometry_tools import mask_to_geometry

    resolution = float(resolution or DEFAULT_RESOLUTION)
    area = QgsRectangle(extent if extent is not None and not extent.isEmpty() else layer.extent())
    area.grow(resolution * 0.5)  # identify() leaves out the points on the edge of the area
    xs, ys, truncated = _read_xy(layer.dataProvider(), resolution, area, int(points_limit), is_canceled, check)
    if not len(xs):
        return FootprintResult(QgsGeometry(), 0, resolution, truncated)
    margin = max(0, int(dilate_cells)) + 1
    span_x, span_y = float(xs.max() - xs.min()), float(ys.max() - ys.min())

    def cells(size):
        return (span_x / size + 2 * margin + 2) * (span_y / size + 2 * margin + 2)

    cell = resolution
    if cells(cell) > MAX_GRID_CELLS:
        cell *= math.sqrt(cells(cell) / MAX_GRID_CELLS)
        while cells(cell) > MAX_GRID_CELLS:  # the margins do not shrink with the cells
            cell *= 1.05
        logger.warning(f"[FM5] footprint of {len(xs)} points over {span_x:.0f} x {span_y:.0f}: cells of {cell:.2f} "
                       f"instead of {resolution:.2f} (grid limit)")
    # Cells aligned on the scanned area, the grid limited to the points read (+ margin).
    left = area.xMinimum() + (math.floor((float(xs.min()) - area.xMinimum()) / cell) - margin) * cell
    top = area.yMaximum() - (math.floor((area.yMaximum() - float(ys.max())) / cell) - margin) * cell
    cols = int(math.floor((float(xs.max()) - left) / cell)) + 1 + margin
    rows = int(math.floor((top - float(ys.min())) / cell)) + 1 + margin
    ci = np.clip(np.floor((xs - left) / cell).astype('int64'), 0, cols - 1)
    ri = np.clip(np.floor((top - ys) / cell).astype('int64'), 0, rows - 1)
    grid = np.zeros((rows, cols), dtype='uint8')
    grid[ri, ci] = 1
    for _ in range(max(0, int(dilate_cells))):
        grown = grid.copy()
        grown[1:, :] |= grid[:-1, :]
        grown[:-1, :] |= grid[1:, :]
        grown[:, 1:] |= grid[:, :-1]
        grown[:, :-1] |= grid[:, 1:]
        grid = grown
    geotransform = (left, cell, 0.0, top, 0.0, -cell)
    geometry = mask_to_geometry(grid, geotransform, layer.crs().toWkt(), sieve_pixels=0, simplify_tolerance=cell * 0.5)
    return FootprintResult(geometry, int(len(xs)), cell, truncated)
