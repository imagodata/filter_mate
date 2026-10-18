# -*- coding: utf-8 -*-
"""Map preview of a terrain derivative or a raster calculator expression selection.

The transparency preview of :func:`raster_adapter.apply_selection_preview` works on
the pixel values of one band, which a slope, an aspect or a colour (several bands:
the pipette on an orthophoto) is not. Here the pixels the selection drops are
covered by a white veil drawn by a canvas item: no layer is added to the project
(FilterMate refreshes everything when a layer is added) and the layer style is
left alone.
"""
import math
from typing import Iterable, Optional, Tuple

from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsPointXY, QgsProject, QgsRectangle
from qgis.gui import QgsMapCanvasItem
from qgis.PyQt.QtCore import QRectF
from qgis.PyQt.QtGui import QImage

from ....core.domain.raster_filter_criteria import RasterDerivative, RasterSelection
from .raster_adapter import (_grid_for, crs_kind, derived_array, expression_mask, raster_reference, read_band_array,
                             referenced_bands, selection_mask, selection_virtual_layer)

# RGBA of the pixels the selection drops.
VEIL = (255, 255, 255, 190)
# The preview is redrawn while a handle is dragged: a coarse grid keeps it light.
PREVIEW_MAX_PIXELS = 500000
# An expression is read again only when it changes (a pipette click). Its grid is
# finer: a pool of 125 m2 on a 25 cm orthophoto keeps 112 m2 at 1 M cells, 74 m2 at
# 500 000 (the overviews blur its edges out of the colour tolerance).
EXPRESSION_PREVIEW_MAX_PIXELS = 1000000


def _veil(mask):
    """RGBA array (height, width, 4): the veil where ``mask`` is False, clear elsewhere."""
    import numpy as np
    rgba = np.zeros(mask.shape + (4,), dtype='uint8')
    rgba[~mask] = VEIL  # NoData is dropped too
    return rgba


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
        self.crs = QgsCoordinateReferenceSystem(layer.crs())
        self.crs_authid = layer.crs().authid()
        self.cell_size = max(extent.width() / width, extent.height() / height)

    def veil(self, selection: RasterSelection):
        """RGBA array (height, width, 4): the veil where ``selection`` drops the pixel, clear elsewhere."""
        return _veil(selection_mask(self.values, selection))


class ExpressionSurface:
    """Pixels kept by a raster calculator expression (colour pipette, spectral preset), read once.

    The raster calculator evaluates it through the virtual raster the filter
    uses (:func:`raster_adapter.selection_virtual_layer`): the preview keeps
    what the filter keeps, on a coarser grid. The pixels with NoData in a band
    the expression reads are neither kept nor counted
    (:func:`raster_adapter.expression_mask`).

    Attributes:
        key: ``(source, expression)`` it was read for.
        extent: Extent of the grid, layer CRS.
        crs_authid: Authority id of the layer CRS ('' for a custom one).
        kept_ratio: Share (0-1) of the pixels with a value that the expression keeps; None when unreadable.
    """

    def __init__(self, layer, selection: RasterSelection, max_pixels: int = EXPRESSION_PREVIEW_MAX_PIXELS) -> None:
        extent = layer.extent()
        width, height = _grid_for(extent, layer.width(), layer.height(), max_pixels)
        self.key = (layer.source(), selection.expression)
        self.extent = QgsRectangle(extent)
        self.crs = QgsCoordinateReferenceSystem(layer.crs())
        self.crs_authid = layer.crs().authid()
        self.cell_size = max(extent.width() / width, extent.height() / height)
        self.mask = None
        self.kept_ratio = None
        virtual = selection_virtual_layer(layer, selection)
        if virtual is None:
            return  # the raster calculator refused the expression
        bands = [band for band in referenced_bands(selection.expression, raster_reference(layer))
                 if band <= layer.bandCount()]
        self.mask, valid = expression_mask(virtual.dataProvider(), layer.dataProvider(), bands, extent, width, height)
        count = int(valid.sum())
        self.kept_ratio = float(self.mask.sum()) / count if count else None

    def veil(self, _selection: Optional[RasterSelection] = None):
        """RGBA array (height, width, 4): the veil where the expression drops the pixel; None when unreadable."""
        return None if self.mask is None else _veil(self.mask)


def corners_stay(moves: Iterable[Tuple[float, float, float, float]], tolerance: float) -> bool:
    """Whether every ``(x, y, moved_x, moved_y)`` corner stays within ``tolerance`` (a non finite one does not)."""
    for x, y, moved_x, moved_y in moves:
        if not (math.isfinite(moved_x) and math.isfinite(moved_y)):
            return False
        if abs(moved_x - x) > tolerance or abs(moved_y - y) > tolerance:
            return False
    return True


def fits_canvas(surface, canvas_crs, context=None) -> bool:
    """Whether the veil of ``surface`` (a grid in the layer CRS) can be drawn as is on a map in ``canvas_crs``.

    Same valid CRS, or one whose transformation moves no corner of the grid by
    half a cell. 2026-10-18: a GeoTIFF in Lambert-93 whose datum GDAL does not
    name (the orthophotos of the test project) is a custom CRS without authority
    id, drawn by QGIS at the very place of the EPSG:2154 map: comparing the
    authority ids refused its preview.
    """
    if not surface.crs.isValid() or not canvas_crs.isValid():
        return False
    if surface.crs == canvas_crs:
        return True
    try:
        transform = QgsCoordinateTransform(surface.crs, canvas_crs, context or QgsProject.instance())
        extent = surface.extent
        moves = []
        for x in (extent.xMinimum(), extent.xMaximum()):
            for y in (extent.yMinimum(), extent.yMaximum()):
                moved = transform.transform(QgsPointXY(x, y))
                moves.append((x, y, moved.x(), moved.y()))
    except Exception:  # QgsCsException: no transformation between the two CRS
        return False
    return corners_stay(moves, surface.cell_size / 2.0)


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


def _polygon_type():
    """Polygon geometry type of a rubber band: ``Qgis.GeometryType`` (3.30+), ``QgsWkbTypes`` before."""
    from qgis.core import Qgis
    geometry_type = getattr(Qgis, 'GeometryType', None)
    if geometry_type is not None and hasattr(geometry_type, 'Polygon'):
        return geometry_type.Polygon
    from qgis.core import QgsWkbTypes
    return QgsWkbTypes.GeometryType.PolygonGeometry


class ObjectOutline:
    """Outline of the objects the pipette detected, in the map selection colour.

    One rubber band, created at the first outline and reset afterwards: the scene
    does not delete an item it removes, a band per click would pile up.
    """

    def __init__(self, canvas) -> None:
        self._canvas = canvas
        self._band = None
        self._shown = False

    @property
    def visible(self) -> bool:
        return self._shown

    def show(self, geometry, layer) -> None:
        """Draw ``geometry`` (in the CRS of ``layer``) on the map, replacing the previous outline."""
        if geometry is None or geometry.isEmpty():
            self.hide()
            return
        if self._band is None:
            from qgis.gui import QgsRubberBand
            from qgis.PyQt.QtGui import QColor
            band = QgsRubberBand(self._canvas, _polygon_type())
            colour = QColor(self._canvas.selectionColor())
            colour.setAlpha(255)
            fill = QColor(colour)
            fill.setAlpha(70)
            band.setStrokeColor(colour)
            band.setFillColor(fill)
            band.setWidth(2)
            self._band = band
        self._band.setToGeometry(geometry, layer.crs())  # reprojected to the map CRS (the layer overload is a vector one)
        self._band.show()
        self._shown = True

    def geometry(self):
        """The outline drawn (map CRS), None when hidden."""
        return self._band.asGeometry() if self._band is not None and self._shown else None

    def hide(self) -> None:
        self._shown = False
        if self._band is not None:
            try:
                self._band.reset(_polygon_type())
                self._band.hide()
            except RuntimeError:  # the canvas is gone (plugin unloaded)
                self._band = None
