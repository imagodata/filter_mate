# -*- coding: utf-8 -*-
"""
Object detection on a point cloud: the cluster of points of one class under a click.

A building, a tree: the points around the click are read with
``QgsPointCloudDataProvider.identify`` at :data:`OBJECT_RESOLUTION` (the octree
level of 1 m, on the layer of the project and the main thread, as the class
pipette), those of the clicked class are binned on a grid of cells of that size,
the gaps between the points are closed by one cell (as the footprint of a source,
:func:`point_cloud_footprint.footprint_geometry`), the 4-connected patch of
cells under the click is followed (:func:`raster_adapter.flood_fill`), shrunk
back by one cell (:data:`OBJECT_ERODE_CELLS`, :func:`geometry_tools.shrink_back`:
the object is not grown, a neck of two grown cells between two objects is cut, a
gap of one cell in a row of points stays closed), the patch under the click taken
again and its holes filled (a courtyard). The window read starts at 64 m a side
around the click and grows four times while the patch touches its side, up to
128 m: a larger patch (a forest) is cut there (``truncated``). A point two cells
away from its object (the sparse edge of a crown) is left out of it, and is a
part of one cell of the footprint.

Similar objects: the footprint of the whole class (a private copy of the layer
filtered on the class, :func:`point_cloud_footprint.footprint_geometry`, with the
same gap closing and shrinking, cell by cell: the clicked object is the part of the
footprint under the click, holes filled), whose parts of an area like the clicked objects'
are kept (:func:`raster_adapter.similar_area_bounds`), and of a shape like theirs
with *same shape* (compactness, as on a raster). It is read in cells of 2 m first
and, for a class of :data:`FINE_CLASS_POINTS` points at most there, again in cells
of 1 m, a read stopped at :data:`FINE_POINTS_LIMIT` points; a denser class (the high
vegetation of a tile), or one whose read in cells of 1 m was stopped, keeps its cells
of 2 m and the clicked objects are measured again in them (:func:`class_footprint`). The
clicked objects and the parts are measured alike: same cells, same closing, holes filled.

Measured 2026-11-11 on the LiDAR HD tile of the test project (Cerdagne), against
the BD TOPO buildings merged into blocks (``scripts/pc_object_closing.py``, rule
set before the run, 2 sets of 20): cells of 2 m grown by the closing, as before,
gave a clicked object overlapping its block at a median IoU of 0.18 and 0.20 (a
village merged into one object), similar objects of precision 0.46 and 0.25 for a
recall of 0.02 and 0.01; cells of 1 m shrunk back give 0.54 and 0.79, precision
0.84 and 0.84, recall 0.44 and 0.51. Cost (``scripts/pc_object_cost.py``, Docker
qgis/qgis:latest): a click at 1 m 1.1 to 2.3 s (median per class, 5 s at most), the
footprint of buildings at 1 m 5 s, of the high vegetation 62 s (8 s at 2 m), of the
ground 97 s (22 s at 2 m). Tried and not adopted: cutting the object where the roof
height jumps by more than 1.25 m between two cells (``scripts/pc_object_height.py``):
better on the set it was chosen on (IoU 0.54 to 0.73), worse on the other (0.79 to 0.63).

The grid and window logic is plain numpy (:func:`object_window`,
:func:`bin_points`, :func:`seed_cell`, :func:`grow_object`), testable without QGIS.
"""
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Sequence, Tuple

from qgis.core import QgsDoubleRange, QgsGeometry, QgsRectangle

logger = logging.getLogger(__name__)

# Cell size in metres (in degrees or feet for a cloud in such a CRS, see point_cloud_footprint.layer_resolution):
# also the level of detail read, the clicked objects and the similar ones alike (see the module docstring).
OBJECT_RESOLUTION = 1.0
# The footprint of a class is read in these cells first, and kept in them for a class denser than
# FINE_CLASS_POINTS points there (about four times as many at 1 m: 200 000 points, some 10 to 15 s).
COARSE_RESOLUTION = 2.0
FINE_CLASS_POINTS = 50000
# The read again in cells of 1 m stops at this many points, and the cells of 2 m are kept: the 10 to 15 s above, on the
# main thread, at most. The four times was an estimate; a class whose points thin out more at 2 m (the low vegetation
# of the tile of scripts/pc_object_cost.py: 13 047 points at 2 m, 9.6 s at 1 m) read up to CLASS_POINTS_LIMIT points.
FINE_POINTS_LIMIT = 4 * FINE_CLASS_POINTS
# Half side in metres of the first window read around a click: 64 m, a house, a tree, a block of flats.
OBJECT_WINDOW_START = 32.0
# Largest half side: 128 m. Read on the main thread at each click (every class: identify cannot filter);
# a patch still larger (a forest, a hedge) is cut and the panel says so.
OBJECT_WINDOW_MAX = 64.0
# The window grows four times at each step: 64 m, then 128 m (the limit); two reads at most.
OBJECT_WINDOW_GROWTH = 4
# Points read (every class) for one object at most: some 0.1 to 0.4 M in a window of 128 m at 1 m.
OBJECT_POINTS_LIMIT = 500000
# Points read for the footprint of a class (the similar objects, whole layer): about 30 s at most;
# beyond, the footprint is truncated and the panel says some objects may be missing.
CLASS_POINTS_LIMIT = 1000000
# Gaps between the points closed by this many cells, as the footprint of a source does.
OBJECT_DILATE_CELLS = 1
# Cells taken back off the edge once the gaps are closed and the holes filled (at most OBJECT_DILATE_CELLS,
# no cell of a point is shrunk away): 0 keeps the objects grown by one cell.
OBJECT_ERODE_CELLS = 1
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
                seed_radius: int = OBJECT_SEED_CELLS, erode_cells: int = OBJECT_ERODE_CELLS) -> Optional[ObjectGrid]:
    """The patch of cells holding points under ``(x, y)``, read in a window grown while the patch touches its side.

    Args:
        read_points: ``(xmin, ymin, xmax, ymax) -> (xs, ys)``: the points of the class in a rectangle.
        x, y: The click, in the units of the points.
        cell: Cell size.
        start, limit: Half side of the first and of the largest window (same units).
        growth: Factor of the half side at each step.
        dilate_cells: Gaps between the points closed by this many cells (see :func:`bin_points`).
        seed_radius: A click on an empty cell starts from the nearest cell of the patch within this many cells.
        erode_cells: Cells taken back off the edges once the gaps are closed
            (:func:`geometry_tools.shrink_back`, at most ``dilate_cells``).

    Returns:
        :class:`ObjectGrid`, None when no point is near the click.
    """
    import numpy as np
    from .geometry_tools import shrink_back
    from .raster_adapter import fill_holes, flood_fill
    margin = max(0, int(dilate_cells))
    erode_cells = min(max(0, int(erode_cells)), margin)  # never past the dilation: every cell of a point stays
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
        inside = rows >= 0
        if int(erode_cells) > 0:
            # Shrunk back as the footprint of the class is (geometry_tools.shrink_back, cell by cell), then the patch
            # under the click again: the patches the grown cells had joined by a neck are apart, as in the footprint.
            occupied = np.zeros(region.shape, dtype=bool)
            occupied[rows[inside], cols[inside]] = True
            shrunk = shrink_back(region, occupied, int(erode_cells))
            again = seed_cell(shrunk, seed[0], seed[1], seed_radius + int(erode_cells))
            if again is not None:
                region = flood_fill(shrunk, [again])
            # cut: the object itself still reaches the side of the largest window
            touches = bool(region[0].any() or region[-1].any() or region[:, 0].any() or region[:, -1].any())
        region = fill_holes(region)
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


def similar_parts(geometry, reference_areas: Sequence[float], ratio,
                  reference_shapes: Optional[Sequence[float]] = None) -> Tuple[list, int]:
    """``(kept, total)``: the parts of ``geometry`` (holes filled) whose area is like ``reference_areas``.

    The bounds are those of the raster similar objects (:func:`raster_adapter.similar_area_bounds`):
    ``ratio[0]`` times the smallest reference to ``ratio[1]`` times the largest one. With
    ``reference_shapes`` (compactness of the clicked objects, holes filled), the compactness of a part
    must be within the same ratios too (:func:`raster_adapter.similar_shape_bounds`), as on a raster.
    """
    from .geometry_tools import compactness
    from .raster_adapter import geometry_parts, similar_area_bounds, similar_shape_bounds
    parts = [filled_part(part) for part in geometry_parts(geometry)]
    bounds = similar_area_bounds(reference_areas, ratio)
    if bounds is None:
        return [], len(parts)
    kept = [part for part in parts if bounds[0] <= part.area() <= bounds[1]]
    shapes = similar_shape_bounds(reference_shapes, ratio) if reference_shapes else None
    if shapes is not None:
        kept = [part for part in kept if shapes[0] <= compactness(part) <= shapes[1]]
    return kept, len(parts)


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
                     limit: float = OBJECT_WINDOW_MAX, points_limit: int = OBJECT_POINTS_LIMIT,
                     erode_cells: int = OBJECT_ERODE_CELLS) -> PointCloudObject:
    """The object of class ``code`` under ``(x, y)`` (layer CRS), read from ``layer`` (main thread).

    ``identify`` honours the subset string of the layer and reads every class: the points
    of ``code`` are kept in Python. ``layer`` is the project layer, or its :func:`base_copy`
    while a preview is applied to it.

    Args:
        seed_radius: Search radius of the click, in layer units (a click between the points of a roof).
        resolution, start, limit: Cell size and half sides of the first and largest windows, in metres.
        points_limit: Points read at most for one window (``truncated`` beyond).
        erode_cells: Cells taken back off the edges once the gaps are closed (see :func:`bin_points`).
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
        read['truncated'] = truncated  # the last read is the final window: a smaller one saturated does not count
        read['points'] += len(xs)
        return xs, ys

    radius = max(OBJECT_SEED_CELLS, min(OBJECT_SEED_MAX_CELLS, int(math.ceil(max(0.0, float(seed_radius)) / cell))))
    grid = grow_object(read_points, float(x), float(y), cell, start * scale, limit * scale, seed_radius=radius,
                       erode_cells=erode_cells)
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


# Points read around a click to tell its class on a private copy (the preview hides the others from the map).
CLASS_UNDER_POINTS = 20000


def base_copy(layer, base_subset: str = ''):
    """A private copy of ``layer`` filtered on ``base_subset`` only (main thread): its filter, not its live preview.

    The object under a click is read through it while the preview (or the subset of the objects)
    is applied to the project layer: ``identify`` honours the subset, a click on another building
    read nothing there, or an object cut to the box of the first one.

    Opening it reads the header and the root of the octree (COPC: the LAS header, the COPC info
    record and the first hierarchy page; EPT: ``ept.json``), no statistics nor index (see
    :func:`point_cloud_footprint.open_point_cloud`).

    Raises:
        RuntimeError: The copy cannot be read, or refused the filter (the reason).
    """
    from .point_cloud_footprint import open_point_cloud
    reason = _readable_reason(layer)
    if reason:
        raise RuntimeError(reason)
    copy = open_point_cloud(layer.source(), f"{layer.name()}_objects", layer.providerType())
    reason = _readable_reason(copy)
    if reason:
        raise RuntimeError(reason)
    base = (base_subset or '').strip()
    # Spelled in parentheses, as class_subset: not the cache key of the project layer's own text.
    if base and not copy.setSubsetString(f"({base}\n)"):
        raise RuntimeError(f"the filter was rejected by the point cloud: {base[:120]}")
    return copy


def class_under(layer, x: float, y: float, radius: float = 0.0, resolution: float = OBJECT_RESOLUTION) -> Optional[int]:
    """Most frequent class of the points of ``layer`` within ``radius`` (layer units, a cell at least) of ``(x, y)``.

    What the class pipette reads on the map, read from the points instead (a private copy is not drawn).
    """
    from ..point_cloud_layer_adapter import dominant_class
    from .point_cloud_footprint import layer_resolution
    cell = layer_resolution(resolution, layer.crs())
    half = max(float(radius or 0.0), cell)
    area = QgsRectangle(x - half, y - half, x + half, y + half)
    points = layer.dataProvider().identify(cell, QgsGeometry.fromRect(area), QgsDoubleRange(), CLASS_UNDER_POINTS)
    return dominant_class(points)


def class_subset(code: int, base_subset: str = '') -> str:
    """Subset string of the class ``code``, ANDed with the filter the layer already has (``base_subset``).

    Spelled in parentheses (see PointCloudSourceJob): QGIS caches the decoded blocks under the
    subset text; the line break keeps a final "--" comment of the base out of the parenthesis.
    """
    clause = f"(Classification = {int(code)})"
    base = (base_subset or '').strip()
    return f"({base}\n) AND {clause}" if base else clause


def footprint_resolution(coarse_points: int, coarse_truncated: bool = False) -> float:
    """Cells (metres) of the footprint of a class read with ``coarse_points`` points in cells of :data:`COARSE_RESOLUTION`.

    Those of the clicked objects (:data:`OBJECT_RESOLUTION`) unless the class is too dense to be read
    again in them within some seconds: then the coarse cells, and the clicked objects are measured in them.
    """
    if coarse_truncated or int(coarse_points) > FINE_CLASS_POINTS:
        return COARSE_RESOLUTION
    return OBJECT_RESOLUTION


def class_footprint(layer, code: int, base_subset: str = '', resolution: Optional[float] = None,
                    points_limit: int = CLASS_POINTS_LIMIT, erode_cells: int = OBJECT_ERODE_CELLS):
    """Footprint (:class:`point_cloud_footprint.FootprintResult`) of the points of class ``code`` of ``layer``.

    Read from a private copy of the layer filtered on the class and ``base_subset`` (the
    project layer keeps its filter and its preview) on the main thread, its gaps closed as the
    clicked objects' (``erode_cells``, see :func:`grow_object`). Without ``resolution`` (metres),
    in cells of :data:`COARSE_RESOLUTION` first, then again in those of the clicked objects when
    the class is light enough (:func:`footprint_resolution`) and that read stays under
    :data:`FINE_POINTS_LIMIT` points; ``resolution`` of the result says which.

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

    def read(metres: float, limit: int = points_limit):
        result = footprint_geometry(copy, layer_resolution(metres, layer.crs()), points_limit=limit,
                                    dilate_cells=OBJECT_DILATE_CELLS, erode_cells=erode_cells,
                                    check=selection_check(subset))
        result.resolution = float(metres)
        return result

    if resolution is not None:
        result = read(float(resolution))
    else:
        result = read(COARSE_RESOLUTION)
        fine = footprint_resolution(result.points_read, result.truncated)
        if fine != COARSE_RESOLUTION and not result.coarse:
            again = read(fine, min(int(points_limit), FINE_POINTS_LIMIT))
            # Cut at the points limit (FINE_POINTS_LIMIT: a few seconds at most), or in cells widened by the grid limit
            # (a cloud of several km): the complete read in the coarse cells, the clicked objects measured again in them.
            if not again.truncated and not again.coarse:
                result = again
    logger.info(f"⏱ [FM5] point cloud class {int(code)} footprint: {result.points_read} points read, cells of "
                f"{result.cell_size:.3g}{', truncated' if result.truncated else ''}, {time.perf_counter() - started:.2f} s")
    return result


def similar_objects_footprint(layer, code: int, reference_areas: Sequence[float], ratio=DEFAULT_SIMILAR_RATIO,
                              base_subset: str = '', footprint=None,
                              reference_shapes: Optional[Sequence[float]] = None) -> SimilarObjects:
    """Every object of class ``code`` of ``layer`` whose area (and shape) is like the clicked objects'.

    Args:
        reference_areas: Areas of the clicked objects of that class (:func:`object_footprint`), layer units².
        ratio: ``(low, high)`` area ratios (:func:`similar_parts`).
        reference_shapes: Their compactness, holes filled; None: the area alone.
        base_subset: The filter of the layer the objects are read through (not the live preview).
        footprint: The :func:`class_footprint` already read for the class (a ratio changed), the reference
            areas measured in its cells; read in those of :data:`OBJECT_RESOLUTION` when None.

    Raises:
        RuntimeError: See :func:`class_footprint`.
    """
    from .geometry_tools import union_geometries
    started = time.perf_counter()
    if footprint is None:  # in the cells of the clicked objects, whose areas are given
        footprint = class_footprint(layer, code, base_subset, resolution=OBJECT_RESOLUTION)
    kept, total = similar_parts(footprint.geometry, reference_areas, ratio, reference_shapes)
    geometry = union_geometries(kept) if kept else QgsGeometry()
    if footprint.coarse:
        logger.warning(f"[FM5] similar point cloud objects of class {int(code)} measured on cells of "
                       f"{footprint.cell_size:.3g} (grid limit): their areas are coarser than the clicked ones'")
    logger.info(f"⏱ [FM5] similar point cloud objects: class {int(code)}, {len(kept)} of {total} objects like "
                f"{len(reference_areas)} clicked one(s), {time.perf_counter() - started:.2f} s")
    return SimilarObjects(geometry, kept, total, footprint.truncated, footprint.coarse)
