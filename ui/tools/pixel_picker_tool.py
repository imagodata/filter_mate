# -*- coding: utf-8 -*-
"""
Pixel picker map tool of the raster EXPLORING panel.

A click emits the map point (canvas CRS); Ctrl+click asks the panel to
extend the value range to the picked value. The last picked point is marked
on the map (raster amber cross) until the tool is put away.
"""
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QColor
from qgis.gui import QgsMapToolEmitPoint

MARKER_COLOR = '#f0b35a'  # raster kind color of the FilterMate 5 design
MARKER_SIZE = 14
MARKER_PEN_WIDTH = 2


def _marker_icon(name: str):
    from qgis.gui import QgsVertexMarker
    scoped = getattr(QgsVertexMarker, 'IconType', None)
    return getattr(scoped, name, None) if scoped is not None and hasattr(scoped, name) else getattr(QgsVertexMarker, name)


class PixelPickerTool(QgsMapToolEmitPoint):
    """Emit ``picked(point, extend)`` on every left click and mark the point on the map."""

    picked = pyqtSignal(object, bool)

    def __init__(self, canvas) -> None:
        super().__init__(canvas)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._marker = None

    def canvasReleaseEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.button() != Qt.MouseButton.LeftButton:
            return
        point = self.toMapCoordinates(event.pos())
        extend = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        self.show_marker(point)
        self.picked.emit(point, extend)

    def show_marker(self, point) -> None:
        """Mark ``point`` (canvas CRS) as the last picked pixel."""
        try:
            from qgis.gui import QgsVertexMarker
            if self._marker is None:
                marker = QgsVertexMarker(self.canvas())
                marker.setIconType(_marker_icon('ICON_CROSS'))
                marker.setColor(QColor(MARKER_COLOR))
                marker.setIconSize(MARKER_SIZE)
                marker.setPenWidth(MARKER_PEN_WIDTH)
                self._marker = marker
            self._marker.setCenter(point)
            self._marker.show()
        except (ImportError, AttributeError, RuntimeError):
            self._marker = None

    def clear_marker(self) -> None:
        marker, self._marker = self._marker, None
        if marker is None:
            return
        try:
            marker.hide()
            scene = self.canvas().scene()
            if scene is not None:
                scene.removeItem(marker)
        except RuntimeError:
            pass

    def deactivate(self) -> None:  # noqa: D401 - Qt override
        """The tool is put away: the marker goes with it."""
        self.clear_marker()
        super().deactivate()
