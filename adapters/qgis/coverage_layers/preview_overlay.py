# -*- coding: utf-8 -*-
"""Map preview of a terrain derivative selection.

The transparency preview of :func:`raster_adapter.apply_selection_preview` works on
pixel values, which a slope or an aspect is not. Here the pixels the selection
drops are covered by a white veil drawn by a canvas item: no layer is added to
the project (FilterMate refreshes everything when a layer is added) and the
layer style is left alone.
"""
from typing import Optional

from qgis.core import QgsPointXY, QgsRectangle
from qgis.gui import QgsMapCanvasItem
from qgis.PyQt.QtCore import QRectF
from qgis.PyQt.QtGui import QImage

from ....core.domain.raster_filter_criteria import RasterDerivative, RasterSelection
from .raster_adapter import _grid_for, crs_kind, derived_array, read_band_array, selection_mask

# RGBA of the pixels the selection drops.
VEIL = (255, 255, 255, 190)
# The preview is redrawn while a handle is dragged: a coarse grid keeps it light.
PREVIEW_MAX_PIXELS = 500000


class DerivativeSurface:
    """A terrain derivative of a raster band, computed once and compared with each new range.

    Attributes:
        key: ``(source, band, derivative)`` it was computed for.
        extent: Extent of the grid, layer CRS.
        crs_authid: CRS of ``extent``.
    """

    def __init__(self, layer, band: int, derivative: RasterDerivative, max_pixels: int = PREVIEW_MAX_PIXELS) -> None:
        extent = layer.extent()
        width, height = _grid_for(extent, layer.width(), layer.height(), max_pixels)
        array = read_band_array(layer.dataProvider(), band, extent, width, height)
        self.values = derived_array(array, derivative, extent, crs_kind(layer.crs())).astype('float32')
        self.key = (layer.source(), int(band), derivative)
        self.extent = QgsRectangle(extent)
        self.crs_authid = layer.crs().authid()

    def veil(self, selection: RasterSelection):
        """RGBA array (height, width, 4): the veil where ``selection`` drops the pixel, clear elsewhere."""
        import numpy as np
        mask = selection_mask(self.values, selection)
        rgba = np.zeros(self.values.shape + (4,), dtype='uint8')
        rgba[~mask] = VEIL  # NoData is dropped too
        return rgba


class _MaskItem(QgsMapCanvasItem):
    """Canvas item drawing an image over a map rectangle (kept in place while the canvas pans / zooms)."""

    def __init__(self, canvas, image: QImage, extent: QgsRectangle) -> None:
        super().__init__(canvas)
        self._image = image
        self._extent = QgsRectangle(extent)
        self._size = QRectF(0.0, 0.0, 0.0, 0.0)
        self.setZValue(5)
        self.updatePosition()

    def boundingRect(self):  # noqa: N802 - Qt override
        return self._size

    def updatePosition(self):  # noqa: N802 - Qt override
        top_left = self.toCanvasCoordinates(QgsPointXY(self._extent.xMinimum(), self._extent.yMaximum()))
        bottom_right = self.toCanvasCoordinates(QgsPointXY(self._extent.xMaximum(), self._extent.yMinimum()))
        self.prepareGeometryChange()
        self._size = QRectF(0.0, 0.0, bottom_right.x() - top_left.x(), bottom_right.y() - top_left.y())
        self.setPos(top_left)

    def paint(self, painter, *_args):
        painter.drawImage(self._size, self._image)


class MaskOverlay:
    """The veil of a derivative selection on a map canvas (one at a time)."""

    def __init__(self, canvas) -> None:
        self._canvas = canvas
        self._item: Optional[_MaskItem] = None

    @property
    def visible(self) -> bool:
        return self._item is not None

    def show(self, rgba, extent: QgsRectangle) -> None:
        """Draw ``rgba`` (height, width, 4 uint8) over ``extent`` (canvas CRS), replacing the previous veil."""
        height, width = rgba.shape[:2]
        data = rgba.tobytes()
        image = QImage(data, width, height, width * 4, QImage.Format.Format_RGBA8888).copy()  # copy: owns its pixels
        self.hide()
        self._item = _MaskItem(self._canvas, image, extent)
        self._canvas.update()

    def hide(self) -> None:
        item, self._item = self._item, None
        if item is not None:
            try:
                self._canvas.scene().removeItem(item)
            except RuntimeError:  # the canvas is gone (plugin unloaded)
                pass
