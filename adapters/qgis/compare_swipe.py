# -*- coding: utf-8 -*-
"""Compare mode: the map before a filter operation left of a swipe line, the map as it is on its right.

Measured first (docs/internal/plans/COMPARE_MODE_SPIKE_2026-11-12.md): a clone of a layer, never added to the
project, draws the state before (its former subset, or the source a derived raster / point cloud replaced); the
canvas keeps drawing the layers as they are; a canvas item paints the "before" image clipped left of the line.
The before image costs a render of the canvas layers (two seconds for a dense layer at the scale of a city), so it is
rendered in the background, for the extent shown, again after each pan or zoom, the older render cancelled.
"""
from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Optional

from qgis.core import QgsMapLayer, QgsMapRendererParallelJob, QgsMapSettings, QgsPointXY, QgsRectangle
from qgis.gui import QgsMapCanvasItem, QgsMapTool
from qgis.PyQt.QtCore import QObject, QPointF, QRectF, Qt, QTimer
from qgis.PyQt.QtGui import QColor, QImage, QPen

from ...core.domain.compare_states import BeforeState

logger = logging.getLogger("FilterMate.compare")

RENDER_DELAY_MS = 250  # a pan or a zoom in progress renders once it stops


def before_clone(layer: QgsMapLayer, state: BeforeState) -> Optional[QgsMapLayer]:
    """A clone of ``layer`` as it was, never added to the project; None when that state cannot be drawn."""
    try:
        clone = layer.clone()
    except RuntimeError:  # the layer was deleted meanwhile
        return None
    if clone is None:
        return None
    if state.other_source:
        clone.setDataSource(state.source, layer.name(), state.provider or layer.providerType())
        if not clone.isValid():  # a derived file removed since: that layer is left out of the before image
            return None
    if hasattr(clone, "setSubsetString"):
        clone.setSubsetString(state.subset)
    return clone


class SwipeItem(QgsMapCanvasItem):
    """The "before" image over its map extent, left of the swipe line; the line itself, and a sign while it renders."""

    def __init__(self, canvas) -> None:
        super().__init__(canvas)
        self._canvas = canvas  # QgsMapCanvasItem keeps it protected
        self._image: Optional[QImage] = None
        self._extent = QgsRectangle()
        self._size = QRectF()
        self.fraction = 0.5
        self.busy = True
        self.setZValue(5)

    def set_image(self, image: Optional[QImage], extent: QgsRectangle) -> None:
        self._image = QImage(image) if image is not None else None
        self._extent = QgsRectangle(extent)
        self.busy = image is None
        self.updatePosition()
        self.update()

    def set_fraction(self, fraction: float) -> None:
        self.fraction = min(max(float(fraction), 0.0), 1.0)
        self.update()

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


class SwipeTool(QgsMapTool):
    """The swipe line follows the mouse over the map; nothing else is done with the clicks."""

    def __init__(self, canvas, item: SwipeItem) -> None:
        super().__init__(canvas)
        self._item = item

    def canvasMoveEvent(self, event):  # noqa: N802 - Qt override
        width = self.canvas().width()
        if width > 0:
            self._item.set_fraction(event.pos().x() / width)


class CompareSession(QObject):
    """One comparison on a canvas: the clones, the before image, the swipe item and its tool."""

    def __init__(self, canvas, parent=None) -> None:
        super().__init__(parent)
        self.canvas = canvas
        self.clones: Dict[str, QgsMapLayer] = {}
        self.item: Optional[SwipeItem] = None
        self.tool: Optional[SwipeTool] = None
        self._previous_tool = None
        self._job: Optional[QgsMapRendererParallelJob] = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(RENDER_DELAY_MS)
        self._timer.timeout.connect(self.render)
        self.renders = 0  # before images done, for the checks

    @property
    def active(self) -> bool:
        return self.item is not None

    def start(self, states: Iterable[BeforeState], layers: Dict[str, QgsMapLayer]) -> int:
        """Begin comparing; the number of layers drawn as they were (0: nothing to compare, nothing shown)."""
        self.stop()
        for state in states:
            layer = layers.get(state.layer_id)
            clone = before_clone(layer, state) if layer is not None else None
            if clone is not None:
                self.clones[state.layer_id] = clone
        if not self.clones:
            return 0
        self.item = SwipeItem(self.canvas)
        self.tool = SwipeTool(self.canvas, self.item)
        self._previous_tool = self.canvas.mapTool()
        self.canvas.setMapTool(self.tool)
        self.canvas.extentsChanged.connect(self._timer.start)
        self.render()
        return len(self.clones)

    def render(self) -> None:
        """Render the before image of the extent shown, in the background; a render under way is dropped."""
        if self.item is None:
            return
        self._cancel_job()
        self.item.set_image(None, QgsRectangle())
        settings = QgsMapSettings(self.canvas.mapSettings())
        settings.setLayers([self.clones.get(layer.id(), layer) for layer in self.canvas.layers()])
        job = QgsMapRendererParallelJob(settings)
        job.finished.connect(lambda done=job, extent=settings.visibleExtent(): self._on_rendered(done, extent))
        self._job = job
        job.start()

    def _on_rendered(self, job, extent) -> None:
        if job is not self._job or self.item is None:
            return
        self._job = None
        self.renders += 1
        self.item.set_image(job.renderedImage(), extent)

    def _cancel_job(self) -> None:
        job, self._job = self._job, None
        if job is not None:
            try:
                job.cancelWithoutBlocking()
            except RuntimeError:
                pass

    def stop(self) -> None:
        """End the comparison: no image, the map tool there before, no clone left."""
        self._timer.stop()
        self._cancel_job()
        try:
            self.canvas.extentsChanged.disconnect(self._timer.start)
        except (TypeError, RuntimeError):  # not connected
            pass
        if self.tool is not None:
            try:
                if self.canvas.mapTool() is self.tool:
                    if self._previous_tool is not None:
                        self.canvas.setMapTool(self._previous_tool)
                    else:
                        self.canvas.unsetMapTool(self.tool)
            except RuntimeError:  # the previous tool was deleted
                self.canvas.unsetMapTool(self.tool)
        if self.item is not None:
            try:
                self.canvas.scene().removeItem(self.item)
            except RuntimeError:
                pass
            self.canvas.update()
        self.item, self.tool, self._previous_tool = None, None, None
        self.clones = {}

    def compared_layer_ids(self) -> List[str]:
        return list(self.clones)
