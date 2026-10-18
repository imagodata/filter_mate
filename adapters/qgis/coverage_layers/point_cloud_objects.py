# -*- coding: utf-8 -*-
"""
Object detection on a point cloud: the cluster of points of one class under a click.

A building, a tree: the points around the click are read with
``QgsPointCloudDataProvider.identify`` at :data:`OBJECT_RESOLUTION` (the octree
level of 2 m, on the layer of the project and the main thread, as the class
pipette), those of the clicked class are binned on a grid of cells of that size,
the gaps between the points are closed by one cell (as the footprint of a source,
:func:`point_cloud_footprint.footprint_geometry`) and the 4-connected patch of
cells under the click is followed (:func:`raster_adapter.flood_fill`), its holes
filled (a courtyard). The window read starts at 64 m a side around the click and
grows four times while the patch touches its side, up to 128 m: a larger patch
(a forest) is cut there (``truncated``).

Measured on a LiDAR HD tile (25 M points, QGIS 4.2): ``identify`` turns every
point read into a dict of its attributes, about 30 000 points a second, and
reads every class: a click in a forest read at 1 m over 256 m took 11 s, the
footprint of the vegetation class of the whole tile at 1 m 49 s. Cells of 2 m
(the resolution of the footprint of a source) and a window of 128 m keep a
click under a few seconds; a car is then two cells long.

Similar objects: the footprint of the whole class (a private copy of the layer
filtered on the class, :func:`point_cloud_footprint.footprint_geometry` at the
same resolution, with the same gap closing), whose parts of an area like the
clicked objects' are kept (:func:`raster_adapter.similar_area_bounds`). The
clicked objects and the parts are measured alike: same cells, same closing,
holes filled.

The grid and window logic is plain numpy (:func:`object_window`,
:func:`bin_points`, :func:`seed_cell`, :func:`grow_object`), testable without QGIS.
"""
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Sequence, Tuple

from qgis.core import QgsGeometry, QgsRectangle

logger = logging.getLogger(__name__)

# Cell size in metres (degrees for a cloud in a geographic CRS, see point_cloud_footprint.layer_resolution):
# also the level of detail read, the clicked objects and the similar ones alike (see the module docstring).
OBJECT_RESOLUTION = 2.0
# Half side in metres of the first window read around a click: 64 m, a house, a tree, a block of flats.
OBJECT_WINDOW_START = 32.0
# Largest half side: 128 m. Read on the main thread at each click (every class: identify cannot filter);
# a patch still larger (a forest, a hedge) is cut and the panel says so.
OBJECT_WINDOW_MAX = 64.0
# The window grows four times at each step: 64 m, then 128 m (the limit); two reads at most.
OBJECT_WINDOW_GROWTH = 4
# Points read (every class) for one object at most: about 0.1 M in a window of 128 m at 2 m.
OBJECT_POINTS_LIMIT = 500000
# Points read for the footprint of a class (the similar objects, whole layer): about 30 s at most;
# beyond, the footprint is truncated and the panel says some objects may be missing.
CLASS_POINTS_LIMIT = 1000000
# Gaps between the points closed by this many cells, as the footprint of a source does.
OBJECT_DILATE_CELLS = 1
# A click between two points of the object: the nearest cell of the class within this many cells
# (at least; the controller asks for the identify search radius of the map, at most OBJECT_SEED_MAX_CELLS).
OBJECT_SEED_CELLS = 2
OBJECT_SEED_MAX_CELLS = 8
DEFAULT_SIMILAR_RATIO = (0.5, 2.0)


# --- grid (numpy only) ------------------------------------------------------

def object_window(x: float, y: float, half: float, cell: float) -> Tuple[float, float, int]:
    """Square window of cells around ``(x, y)``: ``(left, top, size)``, the clicked cell at row and column ``size // 2``.

    The cells are aligned on multiples of ``cell``: the clicked cell keeps its place
    (and the cells around it their bounds) when the window grows.
    """
    cell = float(cell)
    n = max(1, int(math.ceil(float(half) / cell - 1e-9)))
    col, row = math.floor(x / cell), math.floor(y / cell)
    return (col - n) * cell, (row + n + 1) * cell, 2 * n + 1


def bin_points(xs, ys, left: float, top: float, cell: float, size: int, dilate_cells: int = OBJECT_DILATE_CELLS):
    """Cells of a ``size`` x ``size`` grid (top left corner ``(left, top)``) holding a point, grown by ``dilate_cells``.

    The points up to ``dilate_cells`` cells outside the grid are binned too, so the
    border cells grow as the inner ones do. Returns ``(mask, rows, cols)``: the grid,
    and the cell of each point, -1 for a point outside the grid.
    """
    import numpy as np
    from .geometry_tools import dilate_mask
    margin = max(0, int(dilate_cells))
    xs, ys = np.asarray(xs, dtype='float64'), np.asarray(ys, dtype='float64')
    cols = np.floor((xs - left) / cell).astype('int64')
    rows = np.floor((top - ys) / cell).astype('int64')
    near = (cols >= -margin) & (cols < size + margin) & (rows >= -margin) & (rows < size + margin)
    grid = np.zeros((size + 2 * margin, size + 2 * margin), dtype=bool)
    grid[rows[near] + margin, cols[near] + margin] = True
    mask = dilate_mask(grid, margin)[margin:margin + size, margin:margin + size]
    inside = (cols >= 0) & (cols < size) & (rows >= 0) & (rows < size)
    return mask, np.where(inside, rows, -1), np.where(inside, cols, -1)


def seed_cell(mask, row: int, col: int, radius: int) -> Optional[Tuple[int, int]]:
    """The set cell of ``mask`` nearest to ``(row, col)`` within ``radius`` cells (itself when set), None without one.

    On a tie the first cell in row order wins.
    """
    import numpy as np
    rows, cols = mask.shape
    if not (0 <= row < rows and 0 <= col < cols):
        return None
    if mask[row, col]:
        return int(row), int(col)
    radius = int(radius)
    if radius <= 0:
        return None
    row0, col0 = max(0, row - radius), max(0, col - radius)
    found = np.argwhere(mask[row0:row + radius + 1, col0:col + radius + 1])
    if not found.size:
        return None
    distances = (found[:, 0] + row0 - row) ** 2 + (found[:, 1] + col0 - col) ** 2
    best = int(np.argmin(distances))
    if distances[best] > radius * radius:
        return None
    return int(found[best, 0]) + row0, int(found[best, 1]) + col0


@dataclass
class ObjectGrid:
    """Cells of one object: ``region`` (holes filled), its GDAL ``geotransform``, the points in it."""
    region: Any
    geotransform: Tuple[float, float, float, float, float, float]
    points: int
    truncated: bool  # the patch still touched the side of the largest window: cut there
    half: float  # half side of the last window read


def grow_object(read_points: Callable[[float, float, float, float], Tuple[Any, Any]], x: float, y: float, cell: float,
                start: float = OBJECT_WINDOW_START, limit: float = OBJECT_WINDOW_MAX,
                growth: int = OBJECT_WINDOW_GROWTH, dilate_cells: int = OBJECT_DILATE_CELLS,
                seed_radius: int = OBJECT_SEED_CELLS) -> Optional[ObjectGrid]:
    """The patch of cells holding points under ``(x, y)``, read in a window grown while the patch touches its side.

    Args:
        read_points: ``(xmin, ymin, xmax, ymax) -> (xs, ys)``: the points of the class in a rectangle.
        x, y: The click, in the units of the points.
        cell: Cell size.
        start, limit: Half side of the first and of the largest window (same units).
        growth: Factor of the half side at each step.
        dilate_cells: Gaps between the points closed by this many cells (see :func:`bin_points`).
        seed_radius: A click on an empty cell starts from the nearest cell of the patch within this many cells.

    Returns:
        :class:`ObjectGrid`, None when no point is near the click.
    """
    import numpy as np
    from .raster_adapter import fill_holes, flood_fill
    margin = max(0, int(dilate_cells))
    half = float(start)
    while True:
        left, top, size = object_window(x, y, half, cell)
        xs, ys = read_points(left - margin * cell, top - (size + margin) * cell,
                             left + (size + margin) * cell, top + margin * cell)
        mask, rows, cols = bin_points(xs, ys, left, top, cell, size, dilate_cells)
        seed = seed_cell(mask, size // 2, size // 2, seed_radius)
        if seed is None:
            return None
        region = flood_fill(mask, [seed])
        touches = bool(region[0].any() or region[-1].any() or region[:, 0].any() or region[:, -1].any())
        if touches and half < limit and growth > 1:
            half = min(float(limit), half * growth)
            continue
        region = fill_holes(region)
        inside = rows >= 0
        points = int(np.count_nonzero(region[rows[inside], cols[inside]]))
        return ObjectGrid(region, (left, float(cell), 0.0, top, 0.0, -float(cell)), points, touches, half)


# --- similar objects (duck-typed geometries) --------------------------------

def filled_part(part):
    """``part`` without its interior rings (a courtyard), as the clicked objects are measured; itself when it cannot tell."""
    remove = getattr(part, 'removeInteriorRings', None)
    if remove is None:
        return part
    try:
        filled = remove()
    except Exception:  # noqa: BLE001 - kept as it is
        return part
    return filled if filled is not None and not filled.isEmpty() else part


def similar_parts(geometry, reference_areas: Sequence[float], ratio) -> Tuple[list, int]:
    """``(kept, total)``: the parts of ``geometry`` (holes filled) whose area is like ``reference_areas``.

    The bounds are those of the raster similar objects (:func:`raster_adapter.similar_area_bounds`):
    ``ratio[0]`` times the smallest reference to ``ratio[1]`` times the largest one.
    """
    from .raster_adapter import geometry_parts, similar_area_bounds
    parts = [filled_part(part) for part in geometry_parts(geometry)]
    bounds = similar_area_bounds(reference_areas, ratio)
    if bounds is None:
        return [], len(parts)
    return [part for part in parts if bounds[0] <= part.area() <= bounds[1]], len(parts)


# --- QGIS ---------------------------------------------------------------------

@dataclass
class PointCloudObject:
    """The object under a click, in the CRS of the layer; an empty geometry without one (``message`` says why)."""
    geometry: QgsGeometry
    points: int = 0
    truncated: bool = False
    cell_size: float = 0.0
    message: str = ''


@dataclass
class SimilarObjects:
    """The objects of a class like the clicked ones: their union and the parts kept."""
    geometry: QgsGeometry
    parts: List[Any] = field(default_factory=list)
    total: int = 0  # objects of the class
    truncated: bool = False  # the footprint read its maximum of points: some objects may be missing
    coarse: bool = False  # cells larger than the resolution (grid limit): areas measured coarser


def _readable_reason(layer) -> str:
    """Why ``layer`` cannot be read point by point ('' when it can)."""
    from .point_cloud_footprint import index_ready
    if layer.providerType() == 'vpc':
        return "a virtual point cloud (VPC) is read tile by tile: open one of its tiles to detect objects"
    if not layer.isValid() or not index_ready(layer):
        return "the point cloud could not be read (not indexed yet?)"
    return ''


def object_footprint(layer, x: float, y: float, code: int, seed_radius: float = 0.0,
                     resolution: float = OBJECT_RESOLUTION, start: float = OBJECT_WINDOW_START,
                     limit: float = OBJECT_WINDOW_MAX, points_limit: int = OBJECT_POINTS_LIMIT) -> PointCloudObject:
    """The object of class ``code`` under ``(x, y)`` (layer CRS), read from ``layer`` itself (main thread).

    ``identify`` honours the subset string of the layer and reads every class: the points
    of ``code`` are kept in Python.

    Args:
        seed_radius: Search radius of the click, in layer units (a click between the points of a roof).
        resolution, start, limit: Cell size and half sides of the first and largest windows, in metres.
        points_limit: Points read at most for one window (``truncated`` beyond).
    """
    from ..point_cloud_layer_adapter import class_code
    from .geometry_tools import mask_to_geometry
    from .point_cloud_footprint import _read_xy, layer_resolution
    reason = _readable_reason(layer)
    if reason:
        return PointCloudObject(QgsGeometry(), message=reason)
    started = time.perf_counter()
    crs = layer.crs()
    cell = layer_resolution(resolution, crs)
    scale = cell / float(resolution)  # metres -> layer units
    provider = layer.dataProvider()
    code = int(code)
    read = {'truncated': False, 'points': 0}

    def keep(point: dict) -> bool:
        return class_code(point.get('Classification')) == code

    def read_points(xmin, ymin, xmax, ymax):
        area = QgsRectangle(xmin, ymin, xmax, ymax)
        area.grow(cell * 0.5)  # identify() leaves out the points on the edge of the area
        xs, ys, truncated = _read_xy(provider, cell, area, int(points_limit), None, None, keep=keep)
        read['truncated'] = read['truncated'] or truncated
        read['points'] += len(xs)
        return xs, ys

    radius = max(OBJECT_SEED_CELLS, min(OBJECT_SEED_MAX_CELLS, int(math.ceil(max(0.0, float(seed_radius)) / cell))))
    grid = grow_object(read_points, float(x), float(y), cell, start * scale, limit * scale, seed_radius=radius)
    elapsed = time.perf_counter() - started
    if grid is None:
        logger.info(f"⏱ [FM5] point cloud object: no point of class {code} under the click "
                    f"({read['points']} points of the class read{', at the limit' if read['truncated'] else ''}, "
                    f"{elapsed:.2f} s)")
        return PointCloudObject(QgsGeometry(), truncated=read['truncated'], cell_size=cell)
    geometry = mask_to_geometry(grid.region, grid.geotransform, crs.toWkt(), simplify_tolerance=cell * 0.5)
    truncated = grid.truncated or read['truncated']
    logger.info(f"⏱ [FM5] point cloud object: class {code}, {grid.points} points, window of "
                f"{2 * grid.half / scale:.0f} m{', cut' if truncated else ''}, {elapsed:.2f} s")
    return PointCloudObject(geometry, grid.points, truncated, cell)


def class_subset(code: int, base_subset: str = '') -> str:
    """Subset string of the class ``code``, ANDed with the filter the layer already has (``base_subset``).

    Spelled in parentheses (see PointCloudSourceJob): QGIS caches the decoded blocks under the
    subset text; the line break keeps a final "--" comment of the base out of the parenthesis.
    """
    clause = f"(Classification = {int(code)})"
    base = (base_subset or '').strip()
    return f"({base}\n) AND {clause}" if base else clause


def class_footprint(layer, code: int, base_subset: str = '', resolution: float = OBJECT_RESOLUTION,
                    points_limit: int = CLASS_POINTS_LIMIT):
    """Footprint (:class:`point_cloud_footprint.FootprintResult`) of the points of class ``code`` of ``layer``.

    Read from a private copy of the layer filtered on the class and ``base_subset`` (the
    project layer keeps its filter and its preview), at the cell size of the objects (main thread).

    Raises:
        RuntimeError: The cloud cannot be read, or refused the class (the reason).
    """
    from .point_cloud_footprint import footprint_geometry, layer_resolution, open_point_cloud, selection_check
    reason = _readable_reason(layer)
    if reason:
        raise RuntimeError(reason)
    started = time.perf_counter()
    copy = open_point_cloud(layer.source(), f"{layer.name()}_objects", layer.providerType())
    subset = class_subset(code, base_subset)
    reason = _readable_reason(copy)
    if reason:
        raise RuntimeError(reason)
    if not copy.setSubsetString(subset):
        raise RuntimeError(f"the class was rejected by the point cloud: {subset[:120]}")
    result = footprint_geometry(copy, layer_resolution(resolution, layer.crs()), points_limit=points_limit,
                                check=selection_check(subset))
    logger.info(f"⏱ [FM5] point cloud class {int(code)} footprint: {result.points_read} points read, cells of "
                f"{result.cell_size:.3g}{', truncated' if result.truncated else ''}, {time.perf_counter() - started:.2f} s")
    return result


def similar_objects_footprint(layer, code: int, reference_areas: Sequence[float], ratio=DEFAULT_SIMILAR_RATIO,
                              base_subset: str = '', footprint=None) -> SimilarObjects:
    """Every object of class ``code`` of ``layer`` whose area is like ``reference_areas`` (layer units²).

    Args:
        reference_areas: Areas of the clicked objects of that class (:func:`object_footprint`).
        ratio: ``(low, high)`` area ratios (:func:`similar_parts`).
        base_subset: The filter of the layer the objects are read through (not the live preview).
        footprint: The :func:`class_footprint` already read for the class (a ratio changed); read when None.

    Raises:
        RuntimeError: See :func:`class_footprint`.
    """
    from .geometry_tools import union_geometries
    started = time.perf_counter()
    if footprint is None:
        footprint = class_footprint(layer, code, base_subset)
    kept, total = similar_parts(footprint.geometry, reference_areas, ratio)
    geometry = union_geometries(kept) if kept else QgsGeometry()
    if footprint.coarse:
        logger.warning(f"[FM5] similar point cloud objects of class {int(code)} measured on cells of "
                       f"{footprint.cell_size:.3g} (grid limit): their areas are coarser than the clicked ones'")
    logger.info(f"⏱ [FM5] similar point cloud objects: class {int(code)}, {len(kept)} of {total} objects like "
                f"{len(reference_areas)} clicked one(s), {time.perf_counter() - started:.2f} s")
    return SimilarObjects(geometry, kept, total, footprint.truncated, footprint.coarse)
