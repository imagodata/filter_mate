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
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

from qgis.core import QgsMapRendererSequentialJob, QgsMapSettings, QgsRasterLayer, QgsRectangle, QgsTask
from qgis.PyQt.QtCore import QCoreApplication, QEventLoop, QSize, QTimer
from qgis.PyQt.QtGui import QColor, QImage

logger = logging.getLogger(__name__)

# Connected specks of the mask under this many pixels are dropped (the sieve never empties a mask).
SIEVE_PIXELS = 16
# Similar objects with SAM: the colour patches proposed as candidates, nearest to the click first.
SIMILAR_CANDIDATES = 120
# A candidate whose object overlaps one already kept (or the clicked one) by this much is the same object.
SAME_OBJECT_IOU = 0.5
# Area ratios of the colour patches proposed to SAM, wide: the model redraws them, the panel's ratios judge them.
CANDIDATE_RATIO = (0.05, 20.0)
# A patch smaller than this share of the object drawn by SAM is a speck of the image, not a candidate:
# on a textured image they were most of the candidates (105 for 1 object, 20 s, 2026-11-10).
CANDIDATE_MIN_SHARE = 0.05

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

    def predict(self) -> Any:
        """Ask the model for the mask of the current prompts."""
        self.mask, _score = self.provider.predict(self.embedding, self.points, self.labels, self.box)
        return self.mask

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
    """The object SAM sees under one point of the map, its part holding the point (or its largest); None without one."""
    from qgis.core import QgsGeometry, QgsPointXY
    from .geometry_tools import mask_to_geometry
    from .raster_adapter import geometry_parts
    if not window.contains(x, y):
        return None
    mask, _score = provider.predict(embedding, [window.to_pixel(x, y)], [1], None)
    geometry = mask_to_geometry(mask, window.geotransform(), crs_wkt, sieve_pixels=SIEVE_PIXELS,
                                simplify_tolerance=window.cell * 0.5)
    parts = geometry_parts(geometry)
    if not parts:
        return None
    where = QgsGeometry.fromPointXY(QgsPointXY(x, y))
    near = [part for part in parts if part.distance(where) <= window.cell * 2.0]  # a simplified edge may pass by the point
    return min(near, key=lambda part: part.distance(where)) if near else None


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
                                 max_pixels=SIMILAR_LIVE_MAX_PIXELS, opening=criterion.object_opening).geometry
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


def render_window(settings: Any, layer: Any, window: SegmentationWindow, is_canceled: Any) -> QImage:
    """``layer`` alone, drawn in ``window``. Worker thread only (it waits for the job)."""
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

    The candidates are points inside colour patches near the click; each window holding some of
    them is drawn and encoded once, then each point is one prompt.

    Args:
        callback: ``callback(task, success)`` on the main thread; ``task.wkts`` holds the objects kept
            (WKT, layer CRS), ``task.examined`` the candidates prompted and ``task.error`` a failure.
    """

    def __init__(self, source: str, provider_key: str, renderer: Any, crs: Any, model: Any,
                 raster: Tuple[float, float, float, float], cell: float, points: List[Tuple[float, float]],
                 reference_wkt: str, ratio: Tuple[float, float], shape: bool, callback: Any, context: Any = None,
                 existing: Optional[List[str]] = None) -> None:
        super().__init__(QCoreApplication.translate('SimilarObjectsTask', 'FilterMate: drawing the similar objects'),
                         QgsTask.Flag.CanCancel)
        self.source, self.provider_key, self.renderer = source, provider_key, renderer
        self.model, self.raster, self.cell, self.points = model, raster, cell, list(points)
        self.reference_wkt, self.ratio, self.shape = reference_wkt, tuple(ratio), bool(shape)
        self.existing = list(existing or ())  # objects already in the panel: not drawn twice
        self.callback = callback
        self.crs_wkt = crs.toWkt()
        self.wkts: List[str] = []
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
                    found = point_geometry(self.model, embedding, window, x, y, self.crs_wkt)
                    if found is not None and not found.isEmpty():
                        found = found.intersection(bounds)  # past the raster the window is black: nothing was drawn
                    if found is None or found.isEmpty() or any(overlap(found, other) >= SAME_OBJECT_IOU for other in kept):
                        continue
                    if is_similar(found, reference_area, reference_shape, self.ratio, self.shape):
                        kept.append(found)
                        self.wkts.append(found.asWkt())
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
