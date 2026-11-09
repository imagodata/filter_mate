# -*- coding: utf-8 -*-
"""Interactive segmentation of a raster: prompts on the map, polygons out.

FilterMate holds no model: the optional plugin :data:`PROVIDER_PLUGIN` provides a
:class:`~core.ports.segmentation_port.SegmentationProvider`. The model only helps
to draw the objects; the validated polygons are what a filter reads and replays
(``RasterSelection.segments``).

The window is the rendering of the layer (any raster the map can draw, a web
service too) around the first click. Encoding it takes a second or so and goes
to a task; the prompts that follow reuse it on the main thread (tens of ms).
"""
import logging
import math
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

from qgis.core import QgsMapRendererSequentialJob, QgsMapSettings, QgsRasterLayer, QgsRectangle, QgsTask
from qgis.PyQt.QtCore import QCoreApplication, QEventLoop, QSize, QTimer
from qgis.PyQt.QtGui import QColor, QImage

logger = logging.getLogger(__name__)

PROVIDER_PLUGIN = 'filter_mate_segmentation'
# Connected specks of the mask under this many pixels are dropped (the sieve never empties a mask).
SIEVE_PIXELS = 16


def find_provider() -> Optional[Any]:
    """The provider of the optional plugin; None when it is absent or not ready."""
    try:
        from qgis.utils import plugins
        getter = getattr(plugins.get(PROVIDER_PLUGIN), 'segmentation_provider', None)
        return getter() if getter is not None else None
    except Exception as exc:  # a third party plugin must not break the panel
        logger.warning(f"[FM5] segmentation provider unavailable: {exc}")
        return None


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
        self.settings = QgsMapSettings()
        self.settings.setDestinationCrs(crs)
        if context is not None:
            self.settings.setTransformContext(context)
        self.settings.setOutputSize(QSize(window.size, window.size))
        self.settings.setExtent(window.rectangle())
        self.settings.setBackgroundColor(QColor(0, 0, 0, 255))

    def _render(self, layer: Any) -> QImage:
        """The layer alone in the window. Worker thread only (it waits for the job)."""
        self.settings.setLayers([layer])
        job = QgsMapRendererSequentialJob(self.settings)
        loop = QEventLoop()
        timer = QTimer()
        timer.setInterval(100)
        timer.timeout.connect(lambda: job.cancelWithoutBlocking() if self.isCanceled() else None)
        job.finished.connect(loop.quit)
        job.start()
        timer.start()
        if job.isActive():
            loop.exec()
        timer.stop()
        job.waitForFinished()
        if not self.isCanceled() and job.errors():
            raise RuntimeError('the layer could not be drawn')
        return job.renderedImage()

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
            self.error = str(exc)
            logger.warning(f"[FM5] segmentation window not encoded: {exc}", exc_info=True)
            return False
        finally:
            self.settings.setLayers([])
            layer = None

    def finished(self, result: bool) -> None:
        callback, self.callback = self.callback, None
        if callback is not None:
            callback(self, bool(result))
