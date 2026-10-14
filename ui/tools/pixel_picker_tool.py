# -*- coding: utf-8 -*-
"""
Pixel picker map tool of the raster EXPLORING panel.

A click emits the map point (canvas CRS); Ctrl+click asks the panel to
extend the value range to the picked value.
"""
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.gui import QgsMapToolEmitPoint


class PixelPickerTool(QgsMapToolEmitPoint):
    """Emit ``picked(point, extend)`` on every left click."""

    picked = pyqtSignal(object, bool)

    def __init__(self, canvas) -> None:
        super().__init__(canvas)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def canvasReleaseEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.button() != Qt.MouseButton.LeftButton:
            return
        point = self.toMapCoordinates(event.pos())
        extend = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        self.picked.emit(point, extend)
