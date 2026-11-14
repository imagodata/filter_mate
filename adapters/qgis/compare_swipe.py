# -*- coding: utf-8 -*-
"""Compare mode: the map before a step (or as it was pinned) left of a swipe line, the map as it is on its right.

Measured first (docs/internal/plans/COMPARE_MODE_SPIKE_2026-11-12.md): a clone of a layer, never added to the
project, draws the state before (its former subset, the source a derived raster / point cloud replaced, its former
style); the canvas keeps drawing the layers as they are; a canvas item paints the "before" image clipped left of the
line. The before image draws the layers of the canvas, less those not on the map before (added since, or hidden
then), plus those hidden since, at their place in the layer tree (``core/domain/compare_states.BeforeMap``).
The before image costs a render of the canvas layers (two seconds for a dense layer at the scale of a city), so it is
rendered in the background, for the extent shown, again after each pan or zoom, the older render cancelled.

Lifetimes: a cancelled render keeps the clones it draws until it finishes (its threads still read them); a finished
render is deleted at the next one, never inside its own signal; the swipe tool and item live while the comparison
does. The comparison ends by itself when the map is given to another tool: the line would stay still otherwise.
"""
from __future__ import annotations

import logging
import time
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Tuple, Union

from qgis.core import QgsMapLayer, QgsMapRendererParallelJob, QgsMapSettings, QgsPointXY, QgsProject, QgsRectangle
from qgis.gui import QgsMapCanvasItem, QgsMapTool
from qgis.PyQt.QtCore import QObject, QPointF, QRectF, Qt, QTimer, pyqtSignal
from qgis.PyQt.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPen

from ...core.domain.compare_states import BeforeMap, BeforeState, LayerState, MapState, before_layer_order
from .coverage_layers.snapshots import DerivedSourceRegistry, registry, restore_snapshot, take_snapshot

logger = logging.getLogger("FilterMate.compare")

RENDER_DELAY_MS = 250  # a pan or a zoom in progress renders once it stops
LABEL_GAP = 8.0  # between the line and its labels
LABEL_PADDING = 5.0

# A clone of a web feature service asks the server again, on the main thread: left out of the before image.
WEB_FEATURE_PROVIDERS = frozenset({"wfs", "oapif", "arcgisfeatureserver"})


class _CloneRegistry(DerivedSourceRegistry):
    """Restores a snapshot on a clone: the alpha band of the original source is the one the shared registry knows,
    and nothing is recorded (the clone is not in the project; the shared registry is left alone)."""

    def __init__(self, alpha_band: Optional[int]) -> None:
        super().__init__()
        self._band = alpha_band

    def remember_alpha_band(self, layer) -> None:
        pass

    def original_alpha_band(self, layer_id: str) -> Optional[int]:
        return self._band

    def record(self, snapshot, layer=None) -> None:
        pass


def before_clone(layer: QgsMapLayer, state: BeforeState) -> Optional[QgsMapLayer]:
    """A clone of ``layer`` as it was, never added to the project; None when that state cannot be drawn."""
    try:
        if (layer.providerType() or "").lower() in WEB_FEATURE_PROVIDERS:
            return None
        clone = layer.clone()
    except RuntimeError:  # the layer was deleted meanwhile
        return None
    if clone is None:
        return None
    if state.snapshot is not None:  # a cross operation or a pin: restored the way Undo restores it
        try:
            restore_snapshot(clone, state.snapshot, _CloneRegistry(registry().original_alpha_band(layer.id())))
        except Exception:  # a former source removed since: that layer is left out of the before image
            logger.debug("Compare: %s not restored", layer.name(), exc_info=True)
            return None
        if hasattr(clone, "subsetString") and clone.subsetString() != (state.snapshot.subset or ""):
            return None  # the former subset refused
    else:
        if state.other_source:
            clone.setDataSource(state.source, layer.name(), state.provider or layer.providerType())
            if not clone.isValid():
                return None
        if state.subset is not None and hasattr(clone, "setSubsetString") and clone.subsetString() != state.subset:
            if not clone.setSubsetString(state.subset):
                return None
    if state.style is not None:  # after the source: a raster renderer follows its source
        from ..agent.turn_effects import _set_style
        try:
            if not _set_style(clone, state.style):
                return None
        except (RuntimeError, TypeError):
            logger.debug("Compare: style of %s not restored", layer.name(), exc_info=True)
            return None
    return clone


def map_state(canvas=None) -> MapState:
    """Every layer of the project now, for a pin: its filter, its style, drawn or not (checked with its groups in
    the layer tree; on ``canvas`` for a layer the tree does not hold)."""
    from ..agent.turn_effects import _style
    from ..public_api.operations import layer_kind
    project = QgsProject.instance()
    root = project.layerTreeRoot()
    drawn = {layer.id() for layer in canvas.layers()} if canvas is not None else set()
    layers = list(root.layerOrder())
    seen = {layer.id() for layer in layers}
    layers += [layer for layer in project.mapLayers().values() if layer.id() not in seen]
    states = []
    for layer in layers:
        node = root.findLayer(layer.id())
        try:
            snapshot = take_snapshot(layer, layer_kind(layer))
        except (RuntimeError, ValueError, AttributeError):  # one odd layer must not lose the pin
            logger.debug("Compare: %s not read", layer.name(), exc_info=True)
            snapshot = None
        visible = node.isVisible() if node is not None else layer.id() in drawn
        states.append(LayerState(layer.id(), layer.name(), snapshot, _style(layer), bool(visible)))
    return MapState(tuple(states), time.time())


class SwipeItem(QgsMapCanvasItem):
    """The "before" image over its map extent, left of the swipe line; the line itself, a sign while it renders, and
    what each side shows, written at the top on both sides of the line."""

    def __init__(self, canvas) -> None:
        super().__init__(canvas)
        self._canvas = canvas  # QgsMapCanvasItem keeps it protected
        self._image: Optional[QImage] = None
        self._extent = QgsRectangle()
        self._size = QRectF()
        self.fraction = 0.5
        self.busy = True
        self.labels: Tuple[str, str] = ("", "")
        self._font = QFont(canvas.font())
        self.setZValue(5)

    def set_image(self, image: Optional[QImage], extent: QgsRectangle, busy: Optional[bool] = None) -> None:
        """``extent`` empty: the image covers the canvas as it is (a rotated map, drawn again after each move).
        No image and not ``busy``: the map before is the map now, the line alone is drawn."""
        self._image = QImage(image) if image is not None else None
        self._extent = QgsRectangle(extent)
        self.busy = image is None if busy is None else busy
        self.updatePosition()
        self.update()

    def set_fraction(self, fraction: float) -> None:
        self.fraction = min(max(float(fraction), 0.0), 1.0)
        self.update()

    def set_labels(self, before: str, now: str) -> None:
        self.labels = (before or "", now or "")
        self.update()

    def label_rects(self) -> Tuple[QRectF, QRectF]:
        """Where the labels are drawn, in the coordinates of the item: left of the line, right of it (empty rectangle:
        no label). At the top of the canvas, even when the item was moved with the map since its image."""
        metrics = QFontMetricsF(self._font)
        line = self._size.width() * self.fraction
        top = max(0.0, -self.pos().y()) + LABEL_GAP
        height = metrics.height() + LABEL_PADDING
        rects = []
        for text, left in ((self.labels[0], True), (self.labels[1], False)):
            if not text:
                rects.append(QRectF())
                continue
            width = metrics.horizontalAdvance(text) + 2 * LABEL_PADDING
            rects.append(QRectF(line - LABEL_GAP - width if left else line + LABEL_GAP, top, width, height))
        return rects[0], rects[1]

    def boundingRect(self):  # noqa: N802 - Qt override
        return self._size

    def updatePosition(self):  # noqa: N802 - Qt override
        if self._extent.isEmpty():
            self.prepareGeometryChange()
            width, height = self._canvas.width(), self._canvas.height()
            self._size = QRectF(0.0, 0.0, width, height)
            self.setPos(0.0, 0.0)
            return
        top_left = self.toCanvasCoordinates(QgsPointXY(self._extent.xMinimum(), self._extent.yMaximum()))
        bottom_right = self.toCanvasCoordinates(QgsPointXY(self._extent.xMaximum(), self._extent.yMinimum()))
        self.prepareGeometryChange()
        self._size = QRectF(0.0, 0.0, bottom_right.x() - top_left.x(), bottom_right.y() - top_left.y())
        self.setPos(top_left)

    def paint(self, painter, *_args):
        width, height = self._size.width(), self._size.height()
        line = width * self.fraction
        if self._image is not None and not self.busy:
            painter.save()
            painter.setClipRect(QRectF(0.0, 0.0, line, height))
            painter.drawImage(self._size, self._image)
            painter.restore()
        pen = QPen(QColor(255, 255, 255, 230), 3)
        painter.setPen(pen)
        painter.drawLine(QPointF(line, 0.0), QPointF(line, height))
        pen = QPen(QColor(40, 40, 40, 220), 1, Qt.PenStyle.DashLine if self.busy else Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.drawLine(QPointF(line, 0.0), QPointF(line, height))
        # Light text on a dark pill: readable on any map.
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(self._font)
        for text, rect in zip(self.labels, self.label_rects()):
            if not text:
                continue
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(20, 20, 20, 170))
            painter.drawRoundedRect(rect, 4.0, 4.0)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()


class SwipeTool(QgsMapTool):
    """The swipe line follows the mouse over the map; nothing else is done with the clicks."""

    def __init__(self, canvas, item: SwipeItem) -> None:
        super().__init__(canvas)
        self._item = item

    def canvasMoveEvent(self, event):  # noqa: N802 - Qt override
        width = self.canvas().width()
        if width > 0 and self._item is not None:
            self._item.set_fraction(event.pos().x() / width)


class CompareSession(QObject):
    """One comparison on a canvas: the clones, the before image, the swipe item and its tool."""

    ended = pyqtSignal()  # the map was given to another tool, or every compared layer removed: stopped by itself

    def __init__(self, canvas, parent=None) -> None:
        super().__init__(parent)
        self.canvas = canvas
        self.clones: Dict[str, QgsMapLayer] = {}
        self.item: Optional[SwipeItem] = None
        self.tool: Optional[SwipeTool] = None
        self._previous_tool = None
        self._job: Optional[QgsMapRendererParallelJob] = None
        self._job_extent = QgsRectangle()
        self._retired: List[Tuple[QgsMapRendererParallelJob, Dict[str, QgsMapLayer]]] = []
        self._done: List[QgsMapRendererParallelJob] = []
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(RENDER_DELAY_MS)
        self._timer.timeout.connect(self.render)
        self.absent: FrozenSet[str] = frozenset()  # layers of the canvas not on the map before
        self.present: Tuple[str, ...] = ()  # layers hidden now, on the map before
        self.refused: List[str] = []  # names of the layers whose state before could not be drawn
        self._keep = False  # a pin: the comparison waits for a change instead of stopping
        self.renders = 0  # before images done, for the checks

    @property
    def active(self) -> bool:
        return self.item is not None

    def start(self, before: Union[BeforeMap, Iterable[BeforeState]], layers: Dict[str, QgsMapLayer],
              keep: bool = False, labels: Sequence[str] = ("", "")) -> int:
        """Compare against the map ``before`` (again, while on: the tool and the line stay); the number of layers drawn
        otherwise than now (0: nothing to compare, the comparison stops, unless ``keep``: a pin waits for a change).

        ``layers``: the layers of the project by id. The layers whose state before cannot be drawn are named in
        ``refused`` and drawn as they are now.
        """
        if not isinstance(before, BeforeMap):
            before = BeforeMap(tuple(before))
        clones, refused = {}, []
        for state in before.states:
            layer = layers.get(state.layer_id)
            clone = before_clone(layer, state) if layer is not None else None
            if clone is not None:
                clones[state.layer_id] = clone
            elif layer is not None:
                refused.append(layer.name())
        absent = frozenset(layer_id for layer_id in before.absent if layer_id in layers)
        present = tuple(layer_id for layer_id in before.present if layer_id in layers)
        count = len(set(clones) | absent | set(present))
        if not count and not keep:
            self.stop()
            self.refused = refused
            return 0
        self._retire_job()
        self.clones, self.absent, self.present, self.refused, self._keep = clones, absent, present, refused, keep
        if self.item is None:
            self.item = SwipeItem(self.canvas)
            self.tool = SwipeTool(self.canvas, self.item)
            self._previous_tool = self.canvas.mapTool()
            self.canvas.setMapTool(self.tool)
            self.canvas.extentsChanged.connect(self._on_extents_changed)
            self.canvas.mapToolSet.connect(self._on_tool_set)
            QgsProject.instance().layersWillBeRemoved.connect(self._on_layers_removed)
        self.item.set_labels(*labels)
        self.render()
        return count

    def _differs(self) -> bool:
        return bool(self.clones or self.absent or self.present)

    def _before_layers(self) -> List[QgsMapLayer]:
        """The layers of the map before, top first: clones for the layers drawn as they were."""
        drawn = {layer.id(): layer for layer in self.canvas.layers()}
        root = QgsProject.instance().layerTreeRoot()
        order = [layer.id() for layer in root.layerOrder()]
        layers = []
        for layer_id in before_layer_order(list(drawn), order, self.absent, self.present):
            # Not ``or``: a layer may be false (a vector layer of no feature has a length of 0).
            layer = self.clones.get(layer_id)
            if layer is None:
                layer = drawn.get(layer_id)
            if layer is None:
                layer = QgsProject.instance().mapLayer(layer_id)
            if layer is not None:  # a layer hidden now and removed since
                layers.append(layer)
        return layers

    # --- the before image ----------------------------------------------------------

    def render(self) -> None:
        """Render the before image of the extent shown, in the background; a render under way is dropped."""
        if self.item is None:
            return
        self._timer.stop()
        self._retire_job()
        self._done = []  # finished renders: deleted here, not inside their own signal
        if not self._differs():  # a pin with nothing changed since: the map before is the map now
            self.item.set_image(None, QgsRectangle(), busy=False)
            return
        self.item.set_image(None, QgsRectangle())
        settings = QgsMapSettings(self.canvas.mapSettings())
        settings.setLayers(self._before_layers())
        job = QgsMapRendererParallelJob(settings)
        job.finished.connect(self._on_finished)
        self._job = job
        # A rotated map: the image covers the canvas as it is (the visible extent is the bounding box of the view).
        self._job_extent = QgsRectangle() if settings.rotation() else settings.visibleExtent()
        job.start()

    def _on_finished(self) -> None:
        job = self.sender()
        if job is not None and job is self._job:
            self._job = None
            self._done.append(job)
            if self.item is not None:
                self.renders += 1
                self.item.set_image(job.renderedImage(), self._job_extent)
            return
        for index, (retired, _clones) in enumerate(self._retired):
            if retired is job:
                del self._retired[index]  # its clones go with it
                self._done.append(job)
                return

    def _retire_job(self) -> None:
        """Cancel the render under way without waiting; it keeps its clones until it finishes."""
        job, self._job = self._job, None
        if job is None:
            return
        self._retired.append((job, self.clones))
        try:
            job.cancelWithoutBlocking()
        except RuntimeError:
            pass

    def _cancel_all(self) -> None:
        """Wait for every render: a layer is about to go, or the comparison is torn down."""
        # Forgotten first: a cancelled render signals that it finished, and is not a before image then.
        jobs = ([self._job] if self._job is not None else []) + [job for job, _ in self._retired]
        kept = [clones for _, clones in self._retired]  # alive until the renders that read them are over
        self._job, self._retired = None, []
        for job in jobs:
            try:
                if job.isActive():
                    job.cancel()
            except RuntimeError:
                pass
        del kept

    # --- what ends or moves the comparison --------------------------------------------

    def _on_extents_changed(self) -> None:
        if self.item is not None and self.canvas.rotation():
            self.item.set_image(None, QgsRectangle())  # placed on the canvas: wrong as soon as the map moves
        self._timer.start()

    def _on_tool_set(self, new_tool=None, *_args) -> None:
        if self.tool is not None and new_tool is not self.tool:
            self._previous_tool = None  # the map is the user's tool now
            self.stop()
            self.ended.emit()

    def _on_layers_removed(self, layer_ids) -> None:
        if self.item is None:
            return
        self._cancel_all()  # the renders read the layers going
        going = set(layer_ids)
        gone = going & (set(self.clones) | self.absent | set(self.present))
        for layer_id in gone:
            self.clones.pop(layer_id, None)
        self.absent = self.absent - going
        self.present = tuple(layer_id for layer_id in self.present if layer_id not in going)
        if gone and not self._differs() and not self._keep:
            self.stop()
            self.ended.emit()
            return
        self._timer.start()

    def stop(self) -> None:
        """End the comparison: no image, the map tool there before, no clone left."""
        self._timer.stop()
        self._retire_job()
        for signal, slot in ((self.canvas.extentsChanged, self._on_extents_changed),
                             (self.canvas.mapToolSet, self._on_tool_set),
                             (QgsProject.instance().layersWillBeRemoved, self._on_layers_removed)):
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):  # not connected
                pass
        tool, item, previous = self.tool, self.item, self._previous_tool
        self.item, self.tool, self._previous_tool = None, None, None
        self.clones, self.absent, self.present, self._keep = {}, frozenset(), (), False
        if tool is not None:
            try:
                if self.canvas.mapTool() is tool:
                    try:
                        if previous is None:
                            raise RuntimeError("no tool before")
                        self.canvas.setMapTool(previous)
                    except RuntimeError:  # the previous tool was deleted
                        self.canvas.unsetMapTool(tool)
                tool.deleteLater()
            except RuntimeError:  # the canvas is gone (QGIS closing)
                pass
        if item is not None:
            try:
                self.canvas.scene().removeItem(item)
                self.canvas.update()
            except RuntimeError:
                pass

    def close(self) -> None:
        """Stop and wait for the renders (the plugin is unloaded: nothing may run on its clones afterwards)."""
        self.stop()
        self._cancel_all()
        self._done = []

    def compared_layer_ids(self) -> List[str]:
        return list(self.clones)
