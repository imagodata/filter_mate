# -*- coding: utf-8 -*-
"""Map tool of SAM for the object targets of the raster pipette.

Left click: a new object. Shift+left click: extend the last object. Right click:
trim it. Left drag: a box around a new object. Escape: remove the last object.
Moving the mouse without a button asks for a preview of the object under it.
"""
from qgis.core import QgsPointXY, QgsRectangle
from qgis.gui import QgsMapTool, QgsRubberBand, QgsVertexMarker
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QColor

POSITIVE_COLOR = '#d9ffe6'
NEGATIVE_COLOR = '#b4001e'
MARKER_SIZE = 14
MARKER_PEN_WIDTH = 3
# Below this many screen pixels a press and release are a click, not a box.
DRAG_THRESHOLD = 5


def _marker_icon(name: str):
    scoped = getattr(QgsVertexMarker, 'IconType', None)
    return getattr(scoped, name, None) if scoped is not None and hasattr(scoped, name) else getattr(QgsVertexMarker, name)


def _polygon_type():
    """Polygon geometry type of a rubber band: ``Qgis.GeometryType`` (3.30+), ``QgsWkbTypes`` before."""
    from qgis.core import Qgis
    geometry_type = getattr(Qgis, 'GeometryType', None)
    if geometry_type is not None and hasattr(geometry_type, 'Polygon'):
        return geometry_type.Polygon
    from qgis.core import QgsWkbTypes
    return QgsWkbTypes.GeometryType.PolygonGeometry


class SegmentationTool(QgsMapTool):
    """Emit the prompts of the object being drawn, in the map CRS."""

    pointPicked = pyqtSignal(object, bool, bool)  # QgsPointXY, on the object, Shift held (extend the last object)
    boxDrawn = pyqtSignal(object)  # QgsRectangle
    hovered = pyqtSignal(object)  # QgsPointXY under the mouse, no button pressed
    validateRequested = pyqtSignal()
    clearRequested = pyqtSignal()

    def __init__(self, canvas) -> None:
        super().__init__(canvas)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._press = None
        self._dragging = False
        self._band = None
        self._markers = []
        self._shown = 0  # the first ones of the markers are in use

    def canvasPressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.LeftButton:
            self._press = event.pos()
            self._dragging = False

    def canvasMoveEvent(self, event) -> None:  # noqa: N802 - Qt override
        if self._press is None:
            self.hovered.emit(QgsPointXY(self.toMapCoordinates(event.pos())))
            return
        offset = event.pos() - self._press
        self._dragging = self._dragging or max(abs(offset.x()), abs(offset.y())) >= DRAG_THRESHOLD
        if self._dragging:
            self._draw_box(self._rectangle(event.pos()))

    def canvasReleaseEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.RightButton:
            self.pointPicked.emit(QgsPointXY(self.toMapCoordinates(event.pos())), False, False)
            return
        if event.button() != Qt.MouseButton.LeftButton or self._press is None:
            return
        dragging, self._dragging = self._dragging, False
        rectangle = self._rectangle(event.pos())
        self._press = None
        self._hide_box()
        if dragging:
            self.boxDrawn.emit(rectangle)
        else:
            extend = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            self.pointPicked.emit(QgsPointXY(self.toMapCoordinates(event.pos())), True, extend)

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.validateRequested.emit()
        elif event.key() == Qt.Key.Key_Escape:
            self.clearRequested.emit()

    def deactivate(self) -> None:
        self._press = None
        self._dragging = False
        self._hide_box()
        self.clear_markers()
        super().deactivate()

    def _rectangle(self, position) -> QgsRectangle:
        corner = self.toMapCoordinates(self._press)
        other = self.toMapCoordinates(position)
        return QgsRectangle(QgsPointXY(corner), QgsPointXY(other))

    def _draw_box(self, rectangle: QgsRectangle) -> None:
        from qgis.core import QgsGeometry
        if self._band is None:
            self._band = QgsRubberBand(self.canvas(), _polygon_type())
            self._band.setStrokeColor(QColor(NEGATIVE_COLOR))
            self._band.setFillColor(QColor(0, 0, 0, 0))
            self._band.setWidth(2)
        self._band.setToGeometry(QgsGeometry.fromRect(rectangle), None)
        self._band.show()

    def _hide_box(self) -> None:
        if self._band is not None:
            try:
                self._band.reset(_polygon_type())
                self._band.hide()
            except RuntimeError:  # the canvas is gone (plugin unloaded)
                self._band = None

    def add_marker(self, point, positive: bool) -> None:
        """Mark a prompt: a pale cross on the object, a dark X off it (they differ by shape and lightness).

        The markers are reused: the scene does not delete an item it removes, one per click would pile up.
        """
        if self._shown == len(self._markers):
            marker = QgsVertexMarker(self.canvas())
            marker.setIconSize(MARKER_SIZE)
            marker.setPenWidth(MARKER_PEN_WIDTH)
            self._markers.append(marker)
        marker = self._markers[self._shown]
        self._shown += 1
        marker.setIconType(_marker_icon('ICON_CROSS' if positive else 'ICON_X'))
        marker.setColor(QColor(POSITIVE_COLOR if positive else NEGATIVE_COLOR))
        marker.setCenter(QgsPointXY(point))
        marker.show()

    def clear_markers(self) -> None:
        self._shown = 0
        for marker in self._markers:
            try:
                marker.hide()
            except RuntimeError:  # the canvas is gone (plugin unloaded)
                self._markers = []
                return
