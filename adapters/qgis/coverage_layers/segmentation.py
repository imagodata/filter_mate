# -*- coding: utf-8 -*-
"""Interactive segmentation of a raster: prompts on the map, polygons out.

The model (``sam_model``: SAM 2.1 tiny run by onnxruntime) is a
:class:`~core.ports.segmentation_port.SegmentationProvider`. FilterMate ships
neither the model nor the runtime: the user installs onnxruntime in the Python
of QGIS and asks for the download of the model files. The model only helps to
draw the objects; the validated polygons are what a filter reads and replays
(``RasterSelection.segments``).

The window is the rendering of the layer (any raster the map can draw, a web
service too) around the first click. Encoding it takes a second or so and goes
to a task; the prompts that follow reuse it on the main thread (tens of ms).
"""
import logging
import math
import os
import sys
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

from qgis.core import QgsMapRendererSequentialJob, QgsMapSettings, QgsRasterLayer, QgsRectangle, QgsTask
from qgis.PyQt.QtCore import QCoreApplication, QEventLoop, QSize, QThread, QTimer
from qgis.PyQt.QtGui import QColor, QImage

logger = logging.getLogger(__name__)

# Connected specks of the mask under this many pixels are dropped (the sieve never empties a mask).
SIEVE_PIXELS = 16
# Similar objects with SAM: the colour patches proposed as candidates, nearest to the click first.
SIMILAR_CANDIDATES = 120
# A candidate whose object overlaps one already kept (or the clicked one) by this much is the same object.
SAME_OBJECT_IOU = 0.5
# Least cosine between the encoder features of SAM under an object and under the clicked one. Chosen on 10 buildings
# of the 25 cm Cerdagne orthophoto, judged on 10 others by a rule set before the run (2026-11-10): median precision
# 0.24 -> 0.35, recall 0.31 -> 0.26 (scripts/sam_similar_appearance.py).
SIMILAR_APPEARANCE_MIN = 0.68
# Area ratios of the colour patches proposed to SAM, wide: the model redraws them, the panel's ratios judge them.
CANDIDATE_RATIO = (0.05, 20.0)
# A patch smaller than this share of the object drawn by SAM is a speck of the image, not a candidate:
# on a textured image they were most of the candidates (105 for 1 object, 20 s, 2026-11-10).
CANDIDATE_MIN_SHARE = 0.05
# After the colour patches, the places whose encoder features point most like the clicked object's: the best local
# maxima of their cosine over the coarsest feature map of the clicked window. Chosen on 10 buildings of the 25 cm
# Cerdagne orthophoto, judged on 10 others by a rule set before the run (2026-11-11,
# scripts/sam_similar_candidates.py): median recall 0.20 -> 0.32 for a precision of 0.37 -> 0.36.
SIMILAR_FEATURE_CANDIDATES = 10
SIMILAR_FEATURE_MIN = 0.3
# Once the user kept or rejected this many proposals of a search, those left whose features are closer to the rejected
# ones than to the kept ones and the clicked object are taken away. Same bench and rule: median precision of the
# proposals left 0.21 -> 0.33, none of the buildings they held lost.
SORT_AFTER_DECISIONS = 3

_provider: Any = None


@dataclass(frozen=True)
class ModelState:
    """What the Segment target has at hand."""

    runtime: bool  #: onnxruntime can be imported
    installed: bool  #: the model files are in :func:`model_directory`
    installing_runtime: bool = False  #: pip is installing onnxruntime in the background
    runtime_failed: bool = False  #: the last install of onnxruntime did not succeed

    @property
    def ready(self) -> bool:
        return self.runtime and self.installed


def model_directory() -> str:
    """Where the model files live: in the QGIS profile, with the other data of FilterMate."""
    from qgis.core import QgsApplication
    from . import sam_model
    return os.path.join(QgsApplication.qgisSettingsDirPath(), 'filtermate', 'models', sam_model.MODEL_FOLDER)  # next to filtermate/cache


def model_state() -> ModelState:
    from . import sam_model
    try:
        installed = sam_model.is_installed(model_directory())
    except Exception as exc:  # no profile folder (a bare qgis_process, the tests)
        logger.debug(f"[FM5] segmentation model folder unknown: {exc}")
        installed = False
    from .. import python_dependencies
    runtime = sam_model.runtime_available()
    return ModelState(runtime, installed, not runtime and python_dependencies.installing(), not runtime and python_dependencies.install_failed())


def find_provider() -> Optional[Any]:
    """The model, made once its files and onnxruntime are there (opened at its first use); None until then."""
    global _provider
    try:
        if not model_state().ready:
            _provider = None  # the files may have been removed since it was made
        elif _provider is None:
            from . import sam_model
            _provider = sam_model.SamOnnxProvider(model_directory())
    except Exception as exc:  # the panel must not break for the model
        logger.warning(f"[FM5] segmentation model unavailable: {exc}")
        return None
    return _provider


def qgis_proxy_url() -> Optional[str]:
    """The HTTP proxy set in the options of QGIS, as a URL; None for any other setting. Main thread."""
    from urllib.parse import quote
    try:
        from qgis.core import QgsNetworkAccessManager
        from qgis.PyQt.QtNetwork import QNetworkProxy
        proxy = QgsNetworkAccessManager.instance().fallbackProxy()
        if proxy.type() != QNetworkProxy.ProxyType.HttpProxy or not proxy.hostName():
            return None
        credentials = f"{quote(proxy.user(), safe='')}:{quote(proxy.password(), safe='')}@" if proxy.user() else ''
        return f'http://{credentials}{proxy.hostName()}:{proxy.port()}'
    except Exception as exc:  # the system proxy still applies
        logger.debug(f"[FM5] QGIS proxy not read: {exc}")
        return None


def forget_provider() -> None:
    """Drop the model made by :func:`find_provider` (its files changed, or a test)."""
    global _provider
    _provider = None


@dataclass(frozen=True)
class SegmentationWindow:
    """Square of map units the model sees, north up, in the layer CRS."""

    x_min: float
    y_max: float
    cell: float
    size: int

    @property
    def side(self) -> float:
        return self.cell * self.size

    def contains(self, x: float, y: float) -> bool:
        return self.x_min <= x <= self.x_min + self.side and self.y_max - self.side <= y <= self.y_max

    def to_pixel(self, x: float, y: float) -> Tuple[float, float]:
        """``(column, row)`` of a map point, in fractions of pixels."""
        return (x - self.x_min) / self.cell, (self.y_max - y) / self.cell

    def to_map(self, column: float, row: float) -> Tuple[float, float]:
        """Map point of ``(column, row)``: the inverse of :meth:`to_pixel`."""
        return self.x_min + column * self.cell, self.y_max - row * self.cell

    def rectangle_of(self, column0: float, row0: float, column1: float, row1: float) -> QgsRectangle:
        """Map rectangle of a box of pixels (a box prompt)."""
        x0, y0 = self.to_map(column0, row0)
        x1, y1 = self.to_map(column1, row1)
        return QgsRectangle(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))

    def geotransform(self) -> Tuple[float, float, float, float, float, float]:
        return (self.x_min, self.cell, 0.0, self.y_max, 0.0, -self.cell)

    def rectangle(self) -> QgsRectangle:
        return QgsRectangle(self.x_min, self.y_max - self.side, self.x_min + self.side, self.y_max)


def plan_window(x: float, y: float, raster: Tuple[float, float, float, float], native_cell: float,
                visible_side: float, size: int) -> SegmentationWindow:
    """Window around a click: the native pixels, or coarser when the map shows more than they cover.

    Args:
        raster: ``(x_min, y_min, x_max, y_max)`` of the layer.
        native_cell: Pixel size of the layer; 0 for a rendered service, which has none.
        visible_side: Shortest side of the visible extent, in layer units: the object
            the user sees must fit in the window.
        size: Side of the window in pixels.

    Raises:
        ValueError: When no positive cell size can be derived.
    """
    cell = max(float(native_cell), float(visible_side) / size)
    if not (math.isfinite(cell) and cell > 0):
        raise ValueError('segmentation window without a cell size')
    side = cell * size

    def start(click: float, low: float, high: float) -> float:
        if high - low <= side:  # a raster smaller than the window sits in its middle
            return low + (high - low - side) / 2.0
        return min(max(click - side / 2.0, low), high - side)

    x_min = start(x, raster[0], raster[2])
    y_min = start(y, raster[1], raster[3])
    return SegmentationWindow(x_min, y_min + side, cell, size)


@dataclass
class SegmentationSession:
    """Prompts of the object being drawn, on one encoded window. Main thread."""

    provider: Any
    window: SegmentationWindow
    embedding: Any
    points: List[Tuple[float, float]] = field(default_factory=list)
    labels: List[int] = field(default_factory=list)
    box: Optional[Tuple[float, float, float, float]] = None
    mask: Any = None
    masks: List[Any] = field(default_factory=list)  # every mask of the last prediction (SAM: three granularities)
    scores: List[float] = field(default_factory=list)
    choice: int = 0  # the mask in use among ``masks``

    @property
    def has_prompts(self) -> bool:
        return bool(self.points) or self.box is not None

    def add_point(self, x: float, y: float, positive: bool) -> bool:
        """Add a point of the map; False when it is off the window."""
        if not self.window.contains(x, y):
            return False
        self.points.append(self.window.to_pixel(x, y))
        self.labels.append(1 if positive else 0)
        return True

    def set_box(self, x0: float, y0: float, x1: float, y1: float) -> bool:
        """Frame the object with two opposite corners of the map, clipped to the window.

        Returns:
            False, the box unchanged, when less than a pixel of it is left in the window.
        """
        size = float(self.window.size)
        (c0, r0), (c1, r1) = self.window.to_pixel(x0, y0), self.window.to_pixel(x1, y1)
        box = (max(0.0, min(c0, c1)), max(0.0, min(r0, r1)), min(size, max(c0, c1)), min(size, max(r0, r1)))
        if box[2] - box[0] < 1.0 or box[3] - box[1] < 1.0:
            return False
        self.box = box
        return True

    def clear(self) -> None:
        """Forget the prompts, keep the encoded window."""
        self.points, self.labels, self.box, self.mask = [], [], None, None
        self.masks, self.scores, self.choice = [], [], 0

    def predict(self) -> Any:
        """Ask the model for the mask of the current prompts: its best one; the others wait for :meth:`cycle`."""
        several = getattr(self.provider, 'predict_masks', None)
        if several is None:
            self.mask, _score = self.provider.predict(self.embedding, self.points, self.labels, self.box)
            self.masks, self.scores, self.choice = [self.mask], [_score], 0
            return self.mask
        self.masks, self.scores = several(self.embedding, self.points, self.labels, self.box)
        self.choice = max(range(len(self.scores)), key=lambda index: self.scores[index])
        self.mask = self.masks[self.choice]
        return self.mask

    def cycle(self) -> bool:
        """Use the next mask of the last prediction, by growing area (a part, the object, a group); False without another."""
        if len(self.masks) < 2:
            return False
        order = sorted(range(len(self.masks)), key=lambda index: int(self.masks[index].sum()))
        self.choice = order[(order.index(self.choice) + 1) % len(order)]
        self.mask = self.masks[self.choice]
        return True

    def granularity(self) -> Tuple[int, int]:
        """``(rank, count)`` of the mask in use, ranked by area from 1 (the smallest)."""
        if not self.masks:
            return 0, 0
        order = sorted(range(len(self.masks)), key=lambda index: int(self.masks[index].sum()))
        return order.index(self.choice) + 1, len(order)

    def geometry(self, crs_wkt: str = '') -> Any:
        """Polygons of the current mask, simplified by half a pixel; None without a mask."""
        if self.mask is None:
            return None
        from .geometry_tools import mask_to_geometry
        return mask_to_geometry(self.mask, self.window.geotransform(), crs_wkt, sieve_pixels=SIEVE_PIXELS,
                                simplify_tolerance=self.window.cell * 0.5)


def window_at(x: float, y: float, raster: Tuple[float, float, float, float], cell: float, size: int) -> SegmentationWindow:
    """A window of ``cell`` around ``(x, y)``, kept inside the raster like :func:`plan_window`."""
    return plan_window(x, y, raster, cell, 0.0, size)


def assign_windows(points: List[Tuple[float, float]], raster: Tuple[float, float, float, float], cell: float, size: int,
                   margin_pixels: int = 128) -> List[Tuple[SegmentationWindow, List[int]]]:
    """Group points into as few windows as greedily found: each point lies ``margin_pixels`` inside its window.

    Returns:
        ``(window, indexes of its points)``, in the order the windows were opened.
    """
    margin = margin_pixels * cell
    windows: List[Tuple[SegmentationWindow, List[int]]] = []
    for index, (x, y) in enumerate(points):
        for window, members in windows:
            if (window.x_min + margin <= x <= window.x_min + window.side - margin
                    and window.y_max - window.side + margin <= y <= window.y_max - margin):
                members.append(index)
                break
        else:
            window = window_at(x, y, raster, cell, size)
            same = [members for other, members in windows if (other.x_min, other.y_max) == (window.x_min, window.y_max)]
            if same:  # a window kept in the raster near its edge: the point is as far inside as it can be
                same[0].append(index)
            else:
                windows.append((window, [index]))
    return windows


def point_geometry(provider: Any, embedding: Any, window: SegmentationWindow, x: float, y: float, crs_wkt: str = '') -> Any:
    """The object SAM sees under one point of the map, its part nearest the point; None without one."""
    return point_object(provider, embedding, window, x, y, crs_wkt)[0]


def point_object(provider: Any, embedding: Any, window: SegmentationWindow, x: float, y: float,
                 crs_wkt: str = '') -> Tuple[Any, Any]:
    """``(geometry, mask)`` of the object SAM sees under one point: its part nearest the point, and the whole mask."""
    from qgis.core import QgsGeometry, QgsPointXY
    from .geometry_tools import mask_to_geometry
    from .raster_adapter import geometry_parts
    if not window.contains(x, y):
        return None, None
    mask, _score = provider.predict(embedding, [window.to_pixel(x, y)], [1], None)
    geometry = mask_to_geometry(mask, window.geotransform(), crs_wkt, sieve_pixels=SIEVE_PIXELS,
                                simplify_tolerance=window.cell * 0.5)
    parts = geometry_parts(geometry)
    if not parts:
        return None, mask
    where = QgsGeometry.fromPointXY(QgsPointXY(x, y))
    near = [part for part in parts if part.distance(where) <= window.cell * 2.0]  # a simplified edge may pass by the point
    return (min(near, key=lambda part: part.distance(where)) if near else None), mask


@dataclass(frozen=True)
class Prompt:
    """What SAM is given for one feature of a guide layer, in the CRS of the raster."""

    x: float  #: a point inside the object: the feature's point, or the pole of inaccessibility of its polygon
    y: float
    box: Optional[Tuple[float, float, float, float]] = None  #: ``(x_min, y_min, x_max, y_max)`` of a polygon, None for a point
    others: Tuple[Tuple[float, float], ...] = ()  #: the other points of a multipoint, positive too

    def side(self) -> float:
        """Longest side of the box; 0 for a point."""
        return max(self.box[2] - self.box[0], self.box[3] - self.box[1]) if self.box else 0.0


def _geometry_kinds() -> Tuple[Any, Any]:
    """Point and polygon geometry types: ``Qgis.GeometryType`` (3.30+), ``QgsWkbTypes`` before."""
    from qgis.core import Qgis
    kinds = getattr(Qgis, 'GeometryType', None)
    if kinds is not None and hasattr(kinds, 'Polygon'):
        return kinds.Point, kinds.Polygon
    from qgis.core import QgsWkbTypes
    return QgsWkbTypes.GeometryType.PointGeometry, QgsWkbTypes.GeometryType.PolygonGeometry


def prompt_of(geometry: Any, margin: float = 0.0) -> Optional[Prompt]:
    """The prompt of a feature (raster CRS): a point, or the bounding box of a polygon grown by ``margin`` of its size.

    A multipoint gives all its points, the one nearest their centre first. A multipolygon is
    prompted by its largest part (its pieces are far apart, a box over all of them frames none).
    A polygon smaller than nothing, a point in fact, is prompted by its point. None for an empty
    geometry or a line: a line frames no object.
    """
    if geometry is None or geometry.isNull() or geometry.isEmpty():
        return None
    kind = geometry.type()
    point_kind, polygon_kind = _geometry_kinds()
    if kind == point_kind:
        points = [(point.x(), point.y()) for point in (geometry.asMultiPoint() if geometry.isMultipart() else [geometry.asPoint()])]
        cx, cy = sum(x for x, _y in points) / len(points), sum(y for _x, y in points) / len(points)
        points.sort(key=lambda point: (point[0] - cx) ** 2 + (point[1] - cy) ** 2)
        return Prompt(points[0][0], points[0][1], others=tuple(points[1:]))
    if kind != polygon_kind:
        return None
    if not geometry.isGeosValid():
        geometry = geometry.makeValid()
    from .raster_adapter import geometry_parts
    parts = [part for part in geometry_parts(geometry) if part.type() == polygon_kind and part.area() > 0]
    if not parts:
        centre = geometry.boundingBox().center()
        return Prompt(centre.x(), centre.y())
    geometry = max(parts, key=lambda part: part.area())
    rectangle = geometry.boundingBox()
    grow_x, grow_y = rectangle.width() * margin, rectangle.height() * margin
    inside = geometry.poleOfInaccessibility(max(rectangle.width(), rectangle.height()) / 100.0)[0]
    point = inside.asPoint() if inside is not None and not inside.isEmpty() else rectangle.center()
    return Prompt(point.x(), point.y(), (rectangle.xMinimum() - grow_x, rectangle.yMinimum() - grow_y,
                                         rectangle.xMaximum() + grow_x, rectangle.yMaximum() + grow_y))


# A box fills at most this share of its window: SAM sees the object with some ground around it.
PROMPT_BOX_FILL = 2.0 / 3.0
# A point prompt sees at least this many metres of ground, as a click in a view of the town.
PROMPT_POINT_VIEW_METRES = 150.0
# Without a native cell (a service), no window is finer than this share of a point's view: a speck of a polygon
# would otherwise make a window of a few centimetres.
SERVICE_FINEST_SHARE = 1.0 / 8.0


def plan_prompts(prompts: List[Prompt], raster: Tuple[float, float, float, float], native_cell: float, size: int,
                 point_view: float = PROMPT_POINT_VIEW_METRES) -> List[Tuple[SegmentationWindow, List[int]]]:
    """Windows to encode for ``prompts``, each with the indexes of the prompts it holds.

    A prompt needs a cell where its box fills at most :data:`PROMPT_BOX_FILL` of the window (a point:
    ``point_view`` of ground). Cells are the native one doubled as often as needed, so that nearby
    objects of one size share a window; a prompt lies inside its window with its box and some ground.

    Args:
        native_cell: Pixel size of the raster; 0 for a service: the finest cell a prompt needs is then
            used, no finer than :data:`SERVICE_FINEST_SHARE` of a point's view.
        point_view: Ground seen around a point prompt, in raster units.
    """
    if not prompts:
        return []

    def needed(prompt: Prompt) -> float:
        side = prompt.side() / PROMPT_BOX_FILL if prompt.box else point_view
        return max(native_cell, side / size)

    if native_cell > 0:
        base = native_cell
    else:
        base = max(min(needed(prompt) for prompt in prompts), point_view * SERVICE_FINEST_SHARE / size)
    if not (math.isfinite(base) and base > 0):
        raise ValueError('segmentation window without a cell size')
    levels: dict = {}
    for index, prompt in enumerate(prompts):
        level = max(0, math.ceil(math.log2(max(needed(prompt), base) / base) - 1e-9))
        levels.setdefault(level, []).append(index)
    planned: List[Tuple[SegmentationWindow, List[int]]] = []
    for level in sorted(levels):
        cell = base * (2 ** level)
        members = levels[level]
        half_box = max((prompts[i].side() / cell / 2.0 for i in members), default=0.0)
        margin = int(min(size // 2 - 1, math.ceil(half_box) + 32))
        centres = [((prompts[i].box[0] + prompts[i].box[2]) / 2.0, (prompts[i].box[1] + prompts[i].box[3]) / 2.0)
                   if prompts[i].box else (prompts[i].x, prompts[i].y) for i in members]
        for window, inner in assign_windows(centres, raster, cell, size, margin_pixels=margin):
            planned.append((window, [members[i] for i in inner]))
    return planned


def prompt_object(provider: Any, embedding: Any, window: SegmentationWindow, prompt: Prompt, crs_wkt: str = '',
                  with_point: bool = True) -> Tuple[Any, float]:
    """``(geometry, score)`` of the object SAM draws for ``prompt``; ``(None, 0.0)`` when nothing is drawn.

    With a box, the point inside the polygon is given too when ``with_point``; a box under a pixel
    is replaced by its point. Only the parts of the mask that touch the box (or a point) are kept:
    SAM may return detached specks.
    """
    from qgis.core import QgsGeometry, QgsPointXY
    from .geometry_tools import mask_to_geometry
    from .raster_adapter import geometry_parts
    session = SegmentationSession(provider, window, embedding)
    boxed = prompt.box is not None and session.set_box(*prompt.box)
    anchors = []
    if boxed:
        c0, r0, c1, r1 = session.box
        anchors.append(QgsGeometry.fromRect(window.rectangle_of(c0, r0, c1, r1)))
    if not boxed or with_point:
        for x, y in ((prompt.x, prompt.y),) + tuple(prompt.others):
            if session.add_point(x, y, True) and not boxed:
                anchors.append(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
    if not session.has_prompts or not anchors:
        return None, 0.0
    session.predict()
    score = float(session.scores[session.choice]) if session.scores else 0.0
    geometry = mask_to_geometry(session.mask, window.geotransform(), crs_wkt, sieve_pixels=SIEVE_PIXELS,
                                simplify_tolerance=window.cell * 0.5)
    parts = geometry_parts(geometry)
    if not boxed:  # points: the parts under them, as clicks
        held = []
        for anchor in anchors:
            near = [part for part in parts if part.distance(anchor) <= window.cell * 2.0]
            if near:
                nearest = min(near, key=lambda part: part.distance(anchor))
                if not any(nearest.equals(other) for other in held):
                    held.append(nearest)
    else:
        held = [part for part in parts if part.intersects(anchors[0])]
    if not held:
        return None, score
    return (QgsGeometry.unaryUnion(held) if len(held) < len(parts) else geometry), score


def coarse_features(embedding: Any) -> Any:
    """The coarsest feature map of SAM's encoder, ``channels x height x width``; None for an embedding that is not SAM's."""
    import numpy as np
    if not isinstance(embedding, dict):
        return None
    maps = [np.asarray(value) for value in embedding.values() if np.ndim(value) == 4]
    if not maps:
        return None
    return min(maps, key=lambda value: value.shape[-1] * value.shape[-2])[0]


def pooled_features(embedding: Any, mask: Any) -> Any:
    """Encoder features of SAM averaged under a mask, on the coarsest feature map, unit length; None without them.

    The appearance of an object for the similar objects: two roofs of one kind point the same way,
    a road or a lawn of the same colour less so. None for an embedding that is not SAM's (a stub).
    """
    import numpy as np
    coarse = coarse_features(embedding) if mask is not None else None
    if coarse is None:
        return None
    _channels, height, width = coarse.shape
    size = np.asarray(mask).shape[0]
    if size % height or size % width:
        return None
    cells = np.asarray(mask).reshape(height, size // height, width, size // width).mean(axis=(1, 3)) >= 0.5
    if not cells.any():
        return None
    vector = coarse[:, cells].mean(axis=1)
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm else None


def similarity_peaks(coarse: Any, reference_features: Any, minimum: float) -> List[Tuple[float, int, int]]:
    """``(cosine, row, column)`` of the cells of ``coarse`` whose cosine with ``reference_features`` peaks, best first.

    A peak is at least each of its 8 neighbours and at least ``minimum``. ``coarse`` is
    ``channels x height x width`` (:func:`coarse_features`), ``reference_features`` a unit vector.
    """
    import numpy as np
    channels, height, width = coarse.shape
    cells = np.asarray(coarse, dtype=np.float64).reshape(channels, -1)
    norms = np.linalg.norm(cells, axis=0)
    norms[norms == 0] = 1.0
    cosine = (np.asarray(reference_features, dtype=np.float64) @ (cells / norms)).reshape(height, width)
    padded = np.pad(cosine, 1, constant_values=-np.inf)
    neighbours = np.stack([padded[1 + dy:1 + dy + height, 1 + dx:1 + dx + width]
                           for dy in (-1, 0, 1) for dx in (-1, 0, 1)])
    peaks = (cosine >= neighbours.max(axis=0)) & (cosine >= minimum)
    found = [(float(cosine[row, column]), int(row), int(column)) for row, column in zip(*np.nonzero(peaks))]
    found.sort(key=lambda item: (-item[0], item[1], item[2]))
    return found


def feature_candidate_points(embedding: Any, window: SegmentationWindow, reference_features: Any, visible: Any,
                             reference: Any, limit: int = SIMILAR_FEATURE_CANDIDATES,
                             minimum: float = SIMILAR_FEATURE_MIN) -> List[Tuple[float, float]]:
    """Points where the encoder features of the clicked window look most like the clicked object, best first.

    The centres of the cells of :func:`similarity_peaks`, inside ``visible`` (layer CRS) and outside
    the clicked object ``reference``, at most ``limit``. Nothing for an embedding that is not SAM's.
    """
    from qgis.core import QgsGeometry, QgsPointXY
    coarse = coarse_features(embedding)
    if coarse is None or reference_features is None or limit <= 0:
        return []
    step = window.size / coarse.shape[1]
    points: List[Tuple[float, float]] = []
    for _cosine, row, column in similarity_peaks(coarse, reference_features, minimum):
        x, y = window.to_map((column + 0.5) * step, (row + 0.5) * step)
        point = QgsPointXY(x, y)
        if not visible.contains(point) or reference.contains(QgsGeometry.fromPointXY(point)):
            continue
        points.append((x, y))
        if len(points) >= limit:
            break
    return points


def closer_to_rejected(features: Any, kept: List[Any], rejected: List[Any]) -> bool:
    """Whether ``features`` point more like the mean of the ``rejected`` ones than like the mean of the ``kept`` ones.

    False without features, without anything rejected or without anything kept: a proposal is only
    taken away on evidence.
    """
    import numpy as np
    if features is None or not rejected or not kept:
        return False

    def unit_mean(vectors: List[Any]) -> Any:
        mean = np.mean(np.asarray(vectors, dtype=np.float64), axis=0)
        norm = float(np.linalg.norm(mean))
        return mean / norm if norm else mean
    vector = np.asarray(features, dtype=np.float64)
    return float(vector @ unit_mean(rejected)) > float(vector @ unit_mean(kept))


def similar_candidate_points(layer: Any, criterion: Any, reference: Any, visible: Any,
                             limit: int = SIMILAR_CANDIDATES) -> List[Tuple[float, float]]:
    """One point inside each patch of ``criterion`` in the visible map, of an area near the object, nearest first.

    Main thread, as the live similar objects of the colour engine, but on the visible map only:
    a far zoom-out of a large raster reads it coarser. The patches are judged on the area of
    the object drawn by SAM (``CANDIDATE_RATIO``, wide), not on the colour patch under it: a
    textured roof is many small patches. SAM then redraws each candidate and the ratios of
    the panel judge the objects it draws.

    Args:
        layer: The raster whose values are read (the base raster, not a filtered or sampled view).
        criterion: Pixels like the one under the object (``RasterExploringPanel.criterion_at``).
        reference: The object drawn by SAM (layer CRS).
        visible: The visible map (layer CRS): the search stays where the user looks.
    """
    import math
    from dataclasses import replace
    from qgis.core import QgsRectangle
    from ....core.domain.raster_filter_criteria import RasterSelectionMode
    from .raster_adapter import SIMILAR_LIVE_MAX_PIXELS, geometry_parts, selection_geometry, selection_virtual_layer
    extent = layer.extent()
    if layer.width() <= 0 or layer.height() <= 0:
        return []
    cell_x, cell_y = extent.width() / layer.width(), extent.height() / layer.height()
    clip = extent.intersect(visible)
    if clip.isEmpty():
        return []
    columns = (math.floor((clip.xMinimum() - extent.xMinimum()) / cell_x), math.ceil((clip.xMaximum() - extent.xMinimum()) / cell_x))
    rows = (math.floor((extent.yMaximum() - clip.yMaximum()) / cell_y), math.ceil((extent.yMaximum() - clip.yMinimum()) / cell_y))
    window = QgsRectangle(extent.xMinimum() + columns[0] * cell_x, extent.yMaximum() - rows[1] * cell_y,
                          extent.xMinimum() + columns[1] * cell_x, extent.yMaximum() - rows[0] * cell_y)
    plain = replace(criterion, seeds=(), objects=(), similar=(), shape=False)
    virtual = selection_virtual_layer(layer, plain) if plain.mode is RasterSelectionMode.EXPRESSION else None
    if plain.mode is RasterSelectionMode.EXPRESSION and virtual is None:
        return []
    provider = virtual.dataProvider() if virtual is not None else layer.dataProvider()
    patches = selection_geometry(provider, plain, window, columns[1] - columns[0], rows[1] - rows[0], layer.crs().toWkt(),
                                 max_pixels=SIMILAR_LIVE_MAX_PIXELS, opening=criterion.object_opening,
                                 max_vertices=sys.maxsize).geometry  # only measured: no simplification
    inside = reference.pointOnSurface().asPoint()
    points = []
    low, high = reference.area() * max(CANDIDATE_RATIO[0], CANDIDATE_MIN_SHARE), reference.area() * CANDIDATE_RATIO[1]
    for part in geometry_parts(patches):
        if not low <= part.area() <= high or part.intersects(reference):
            continue
        point = part.pointOnSurface().asPoint()
        points.append(((point.x() - inside.x()) ** 2 + (point.y() - inside.y()) ** 2, (point.x(), point.y())))
    points.sort()
    return [point for _distance, point in points[:limit]]


def overlap(first: Any, second: Any) -> float:
    """Intersection over union of two polygons; 0 when either is empty."""
    try:
        union = first.combine(second).area()
        return first.intersection(second).area() / union if union > 0 else 0.0
    except Exception:  # an invalid geometry: not the same object
        return 0.0


def is_similar(geometry: Any, reference_area: float, reference_compactness: float, ratio: Tuple[float, float], shape: bool) -> bool:
    """Whether an object drawn by SAM is like the clicked one: its area, and its compactness with ``shape``, within the ratios."""
    from .geometry_tools import compactness
    from .raster_adapter import similar_area_bounds, similar_shape_bounds
    bounds = similar_area_bounds([reference_area], ratio)
    if bounds is None or not bounds[0] <= geometry.area() <= bounds[1]:
        return False
    if not shape:
        return True
    shapes = similar_shape_bounds([reference_compactness], ratio)
    return shapes is None or shapes[0] <= compactness(geometry) <= shapes[1]


def area_measure(crs: Any) -> Any:
    """A function giving the area of a geometry in ``crs`` in square metres (None when unknown), set up once.

    On the ellipsoid of the project; with none set and a geographic CRS, on the ellipsoid of the CRS:
    a planar area in square degrees would be wrong by tens of percent away from the equator.
    """
    from qgis.core import Qgis, QgsDistanceArea, QgsProject, QgsUnitTypes
    measure = QgsDistanceArea()
    project = QgsProject.instance()
    measure.setSourceCrs(crs, project.transformContext())
    ellipsoid = project.ellipsoid() or 'NONE'
    if ellipsoid == 'NONE' and crs is not None and crs.isGeographic():
        ellipsoid = crs.ellipsoidAcronym() or 'EPSG:7030'
    measure.setEllipsoid(ellipsoid)
    area_unit = getattr(Qgis, 'AreaUnit', None)
    square_metres = area_unit.SquareMeters if area_unit is not None else QgsUnitTypes.AreaUnit.AreaSquareMeters

    def area(geometry: Any) -> Optional[float]:
        try:
            return float(measure.convertAreaMeasurement(measure.measureArea(geometry), square_metres))
        except Exception as exc:  # noqa: BLE001 - an area is a convenience: the objects are still told
            logger.debug(f"[FM5] area of an object unknown: {exc}")
            return None
    return area


def ground_area(geometry: Any, crs: Any) -> Optional[float]:
    """Area of ``geometry`` (in ``crs``) in square metres, on the project ellipsoid; None when unknown."""
    try:
        return area_measure(crs)(geometry)
    except Exception as exc:  # noqa: BLE001 - an area is a convenience: the objects are still told
        logger.debug(f"[FM5] area of the objects unknown: {exc}")
        return None


def objects_layer(wkts: List[str], crs: Any, name: str, area: Optional[Any] = None) -> Tuple[Any, int]:
    """A memory layer of the objects (WKT, ``crs``): one multipolygon each, numbered from 1, with its area.

    ``area`` gives the area of a geometry in square metres (None when unknown); without it the
    column stays empty. Returns the layer and the number of objects that could not be read.
    """
    from qgis.core import QgsFeature, QgsGeometry, QgsVectorLayer
    authid = crs.authid() if crs is not None else ''
    uri = 'MultiPolygon?field=object:integer&field=area_m2:double(20,2)'
    if authid:
        uri += f'&crs={authid}'
    layer = QgsVectorLayer(uri, name, 'memory')
    if crs is not None and crs.isValid():
        layer.setCrs(crs)  # a CRS without authid (a custom one) too
    features, skipped = [], 0
    for wkt in wkts:
        geometry = QgsGeometry.fromWkt(wkt)
        if geometry is None or geometry.isNull() or geometry.isEmpty():
            skipped += 1
            continue
        geometry.convertToMultiType()
        feature = QgsFeature(layer.fields())
        measured = area(geometry) if area is not None else None
        feature.setAttributes([len(features) + 1, round(measured, 2) if measured is not None else None])
        feature.setGeometry(geometry)
        features.append(feature)
    if features:
        layer.dataProvider().addFeatures(features)
        layer.updateExtents()
    return layer, skipped


def render_window(settings: Any, layer: Any, window: SegmentationWindow, is_canceled: Any) -> QImage:
    """``layer`` alone, drawn in ``window``; it waits for the job.

    Made for a worker thread. On the main thread (a script, a tool of the agent) the wait takes no
    user input: a click must not start something else in the middle of the run.
    """
    settings.setOutputSize(QSize(window.size, window.size))
    settings.setExtent(window.rectangle())
    settings.setLayers([layer])
    job = QgsMapRendererSequentialJob(settings)
    loop = QEventLoop()
    timer = QTimer()
    timer.setInterval(100)
    timer.timeout.connect(lambda: job.cancelWithoutBlocking() if is_canceled() else None)
    job.finished.connect(loop.quit)
    job.start()
    timer.start()
    if job.isActive():
        application = QCoreApplication.instance()
        if application is not None and QThread.currentThread() is application.thread():
            loop.exec(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
        else:
            loop.exec()
    timer.stop()
    job.waitForFinished()
    if not is_canceled() and job.errors():
        raise RuntimeError('the layer could not be drawn')
    return job.renderedImage()


def image_to_rgb(image: QImage) -> Any:
    """Copy of the RGB bytes of ``image`` as a height x width x 3 uint8 array."""
    import numpy as np
    image = image.convertToFormat(QImage.Format.Format_RGBA8888)
    width, height = image.width(), image.height()
    pointer = image.constBits()
    pointer.setsize(image.bytesPerLine() * height)
    pixels = np.frombuffer(pointer, dtype=np.uint8).reshape(height, image.bytesPerLine())
    return pixels[:, :width * 4].reshape(height, width, 4)[:, :, :3].copy()


class SegmentationEmbedTask(QgsTask):
    """Render the window of a layer and encode it, off the main thread.

    Built on the main thread with a detached ``layer.renderer().clone()``.

    Args:
        callback: ``callback(task, success)`` on the main thread; ``task.embedding``
            holds the result and ``task.error`` the reason of a failure.
    """

    def __init__(self, source: str, provider_key: str, renderer: Any, crs: Any, window: SegmentationWindow,
                 model: Any, callback: Any, context: Any = None) -> None:
        super().__init__(QCoreApplication.translate('SegmentationEmbedTask', 'FilterMate: preparing the segmentation'),
                         QgsTask.Flag.CanCancel)
        self.source, self.provider_key = source, provider_key
        self.renderer = renderer
        self.window = window
        self.model = model
        self.callback = callback
        self.embedding = None
        self.error = ''
        self.model_damaged = False  # the files of the model were refused: downloading them again can repair them
        self.settings = QgsMapSettings()
        self.settings.setDestinationCrs(crs)
        if context is not None:
            self.settings.setTransformContext(context)
        self.settings.setOutputSize(QSize(window.size, window.size))
        self.settings.setExtent(window.rectangle())
        self.settings.setBackgroundColor(QColor(0, 0, 0, 255))

    def _render(self, layer: Any) -> QImage:
        """The layer alone in the window. Worker thread only (it waits for the job)."""
        return render_window(self.settings, layer, self.window, self.isCanceled)

    def run(self) -> bool:
        layer = None
        try:
            if self.isCanceled():
                return False
            layer = QgsRasterLayer(self.source, 'FilterMate segmentation', self.provider_key)
            if not layer.isValid():
                raise RuntimeError('the layer could not be opened')
            if self.renderer is not None:
                layer.setRenderer(self.renderer)
                self.renderer = None
            image = self._render(layer)
            if self.isCanceled():
                return False
            self.embedding = self.model.embed(image_to_rgb(image))
            return not self.isCanceled()
        except Exception as exc:  # the model is third party code: its failure is told, not raised in a task
            from . import sam_model
            self.error = str(exc)
            self.model_damaged = isinstance(exc, sam_model.ModelLoadError)
            logger.warning(f"[FM5] segmentation window not encoded: {exc}", exc_info=True)
            return False
        finally:
            self.settings.setLayers([])
            layer = None

    def finished(self, result: bool) -> None:
        callback, self.callback = self.callback, None
        if callback is not None:
            callback(self, bool(result))


class SimilarObjectsTask(QgsTask):
    """Redraw with SAM the candidates of a similar objects search and keep those like the clicked object. Worker thread.

    The candidates are points inside colour patches near the click, then the places whose features
    look like the clicked object's (:func:`feature_candidate_points`); each window holding some of
    them is drawn and encoded once, then each point is one prompt.

    Args:
        callback: ``callback(task, success)`` on the main thread; ``task.wkts`` holds the objects kept
            (WKT, layer CRS), ``task.examined`` the candidates prompted and ``task.error`` a failure.
    """

    def __init__(self, source: str, provider_key: str, renderer: Any, crs: Any, model: Any,
                 raster: Tuple[float, float, float, float], cell: float, points: List[Tuple[float, float]],
                 reference_wkt: str, ratio: Tuple[float, float], shape: bool, callback: Any, context: Any = None,
                 existing: Optional[List[str]] = None, reference_features: Any = None) -> None:
        super().__init__(QCoreApplication.translate('SimilarObjectsTask', 'FilterMate: drawing the similar objects'),
                         QgsTask.Flag.CanCancel)
        self.source, self.provider_key, self.renderer = source, provider_key, renderer
        self.model, self.raster, self.cell, self.points = model, raster, cell, list(points)
        self.reference_wkt, self.ratio, self.shape = reference_wkt, tuple(ratio), bool(shape)
        self.existing = list(existing or ())  # objects already in the panel: not drawn twice
        self.reference_features = reference_features  # the appearance of the clicked object; None: not compared
        self.callback = callback
        self.crs_wkt = crs.toWkt()
        self.wkts: List[str] = []
        self.features: dict = {}  # WKT of an object kept -> its encoder features (None when unknown): keep / reject sorts by them
        self.examined = 0
        self.error = ''
        self.model_damaged = False
        self.settings = QgsMapSettings()
        self.settings.setDestinationCrs(crs)
        if context is not None:
            self.settings.setTransformContext(context)
        self.settings.setBackgroundColor(QColor(0, 0, 0, 255))

    def run(self) -> bool:
        from qgis.core import QgsGeometry, QgsPointXY
        from .geometry_tools import compactness
        layer = None
        try:
            if self.isCanceled():
                return False
            layer = QgsRasterLayer(self.source, 'FilterMate segmentation', self.provider_key)
            if not layer.isValid():
                raise RuntimeError('the layer could not be opened')
            if self.renderer is not None:
                layer.setRenderer(self.renderer)
                self.renderer = None
            reference = QgsGeometry.fromWkt(self.reference_wkt)
            reference_area, reference_shape = reference.area(), compactness(reference)
            kept: List[Any] = [reference] + [geometry for geometry in (QgsGeometry.fromWkt(wkt) for wkt in self.existing)
                                             if not geometry.isEmpty()]
            bounds = QgsGeometry.fromRect(QgsRectangle(*self.raster))
            windows = assign_windows(self.points, self.raster, self.cell, int(self.model.input_size))
            done = 0
            for window, members in windows:
                if self.isCanceled():
                    return False
                image = render_window(self.settings, layer, window, self.isCanceled)
                if self.isCanceled():
                    return False
                embedding = self.model.embed(image_to_rgb(image))
                for index in members:
                    if self.isCanceled():
                        return False
                    done += 1
                    self.setProgress(100.0 * done / max(1, len(self.points)))
                    x, y = self.points[index]
                    where = QgsGeometry.fromPointXY(QgsPointXY(x, y))
                    if any(found.contains(where) for found in kept):
                        continue  # a patch of an object already drawn
                    self.examined += 1
                    found, mask = point_object(self.model, embedding, window, x, y, self.crs_wkt)
                    if found is not None and not found.isEmpty():
                        found = found.intersection(bounds)  # past the raster the window is black: nothing was drawn
                    if found is None or found.isEmpty() or any(overlap(found, other) >= SAME_OBJECT_IOU for other in kept):
                        continue
                    if is_similar(found, reference_area, reference_shape, self.ratio, self.shape):
                        kept.append(found)  # drawn: its patches are not prompted again, whatever its appearance
                        features = pooled_features(embedding, mask)
                        if self._looks_alike(embedding, mask, features):
                            wkt = found.asWkt()
                            self.wkts.append(wkt)
                            self.features[wkt] = features
            return not self.isCanceled()
        except Exception as exc:  # the model is third party code: its failure is told, not raised in a task
            from . import sam_model
            self.error = str(exc) or type(exc).__name__
            self.model_damaged = isinstance(exc, sam_model.ModelLoadError)
            logger.warning(f"[FM5] similar objects not drawn: {exc}", exc_info=True)
            return False
        finally:
            self.settings.setLayers([])
            layer = None

    def _looks_alike(self, embedding: Any, mask: Any, features: Any = None) -> bool:
        """Its SAM features point like the clicked object's (``SIMILAR_APPEARANCE_MIN``); True when either is unknown.

        ``features``: those of the object when already pooled; read from ``embedding`` and ``mask`` otherwise.
        """
        import numpy as np
        if self.reference_features is None:
            return True
        if features is None:
            features = pooled_features(embedding, mask)
        return features is None or float(np.dot(features, self.reference_features)) >= SIMILAR_APPEARANCE_MIN

    def finished(self, result: bool) -> None:
        callback, self.callback = self.callback, None
        if callback is not None:
            callback(self, bool(result))


class ModelDownloadTask(QgsTask):
    """Fetch the files of the model into a folder, off the main thread, once the user asked for it.

    Args:
        callback: ``callback(task, success)`` on the main thread; ``task.error`` says why it
            failed, and stays empty when it was canceled.
    """

    def __init__(self, directory: str, callback: Any) -> None:
        super().__init__(QCoreApplication.translate('ModelDownloadTask', 'FilterMate: downloading the segmentation model'),
                         QgsTask.Flag.CanCancel)
        self.directory, self.callback, self.error = directory, callback, ''
        self.proxy = qgis_proxy_url()  # read here, on the main thread

    def run(self) -> bool:
        from . import sam_model
        try:
            sam_model.download(self.directory, self.isCanceled, self.setProgress, self.proxy)
            return True
        except sam_model.Canceled:
            return False
        except Exception as exc:  # network or disk: told to the user
            self.error = str(exc) or type(exc).__name__
            return False

    def finished(self, result: bool) -> None:
        forget_provider()
        callback, self.callback = self.callback, None
        if callback is not None:
            callback(self, bool(result))
