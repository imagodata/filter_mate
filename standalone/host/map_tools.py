# -*- coding: utf-8 -*-
"""The map tools the QGIS application has and the libraries do not: select, select by polygon, identify.

Each acts on the current layer of the layer panel, as in QGIS. Shift adds to the selection,
Ctrl removes from it.
"""

from qgis.core import QgsFeatureRequest, QgsGeometry, QgsPointXY, QgsRectangle, QgsVectorLayer, QgsWkbTypes
from qgis.gui import QgsMapTool, QgsMapToolIdentify, QgsRubberBand
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor

from .compat import enum_member, select_behavior
from .qt import _tr

_FILL = QColor(254, 178, 76, 63)
_STROKE = QColor(254, 58, 29, 200)


def _polygon_type():
    scope = getattr(QgsWkbTypes, "GeometryType", None)
    if scope is not None and hasattr(scope, "PolygonGeometry"):
        return scope.PolygonGeometry
    from qgis.core import Qgis
    return Qgis.GeometryType.Polygon


def _behavior(event):
    modifiers = event.modifiers()
    if modifiers & Qt.KeyboardModifier.ShiftModifier:
        return select_behavior("AddToSelection")
    if modifiers & Qt.KeyboardModifier.ControlModifier:
        return select_behavior("RemoveFromSelection")
    return select_behavior("SetSelection")


class _LayerTool(QgsMapTool):
    """A tool that needs a vector layer: says so in the message bar when there is none."""

    def __init__(self, window):
        super().__init__(window.canvas)
        self._window = window
        self._band = None

    def _layer(self):
        layer = self._window.tree_view.currentLayer()
        if isinstance(layer, QgsVectorLayer) and layer.isValid():
            return layer
        self._window.message_bar.pushInfo("FilterMate", _tr("Choose a vector layer in the layer panel first."))
        return None

    def _new_band(self):
        band = QgsRubberBand(self.canvas(), _polygon_type())
        band.setFillColor(_FILL)
        band.setStrokeColor(_STROKE)
        band.setWidth(1)
        return band

    def _show_points(self, points):
        """Draw ``points`` (map coordinates) as the outline being drawn."""
        if self._band is None:
            self._band = self._new_band()
        self._band.reset(_polygon_type())
        for index, point in enumerate(points):
            self._band.addPoint(QgsPointXY(point), index == len(points) - 1)

    def _drop_band(self):
        if self._band is not None:
            self.canvas().scene().removeItem(self._band)
            self._band = None

    def deactivate(self):
        self._drop_band()
        super().deactivate()


class SelectTool(_LayerTool):
    """A click selects what is under the pointer, a drag what the rectangle touches."""

    def __init__(self, window):
        super().__init__(window)
        self._origin = None
        self._dragging = False
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def canvasPressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.pos()
            self._dragging = False

    def canvasMoveEvent(self, event):
        if self._origin is None:
            return
        if not self._dragging and (event.pos() - self._origin).manhattanLength() < 4:
            return
        self._dragging = True
        r = self._map_rectangle(self._origin, event.pos())
        self._show_points([QgsPointXY(r.xMinimum(), r.yMinimum()), QgsPointXY(r.xMaximum(), r.yMinimum()),
                           QgsPointXY(r.xMaximum(), r.yMaximum()), QgsPointXY(r.xMinimum(), r.yMaximum())])

    def canvasReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self._origin is None:
            return
        # A drag is told by the distance too: a fast one may bring no move event between press and release.
        origin = self._origin
        dragging = self._dragging or (event.pos() - origin).manhattanLength() >= 4
        self._origin, self._dragging = None, False
        self._drop_band()
        layer = self._layer()
        if layer is None:
            return
        if dragging:
            rectangle = self._map_rectangle(origin, event.pos())
        else:
            radius = QgsMapTool.searchRadiusMU(self.canvas())
            centre = self.toMapCoordinates(event.pos())
            rectangle = QgsRectangle(centre.x() - radius, centre.y() - radius, centre.x() + radius, centre.y() + radius)
        try:
            layer.selectByRect(self.toLayerCoordinates(layer, rectangle), _behavior(event))
        except Exception as error:  # a rectangle that does not project into the layer's CRS
            self._window.message_bar.pushWarning("FilterMate", str(error))

    def _map_rectangle(self, first, second):
        a, b = self.toMapCoordinates(first), self.toMapCoordinates(second)
        return QgsRectangle(QgsPointXY(a), QgsPointXY(b))


class PolygonSelectTool(_LayerTool):
    """Left clicks draw a polygon, a right click closes it and selects what it touches; Escape gives up."""

    def __init__(self, window):
        super().__init__(window)
        self._points = []
        self.setCursor(Qt.CursorShape.CrossCursor)

    def canvasPressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._points.append(self.toMapCoordinates(event.pos()))
            self._redraw(None)
        elif event.button() == Qt.MouseButton.RightButton:
            self._finish(event)

    def canvasMoveEvent(self, event):
        if self._points:
            self._redraw(self.toMapCoordinates(event.pos()))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._points = []
            self._drop_band()
            event.accept()

    def deactivate(self):
        self._points = []
        super().deactivate()

    def _redraw(self, moving):
        self._show_points(list(self._points) + ([moving] if moving is not None else []))

    def _finish(self, event):
        points, self._points = [QgsPointXY(p) for p in self._points], []
        self._drop_band()
        if len(points) < 3:
            return
        layer = self._layer()
        if layer is None:
            return
        try:
            polygon = QgsGeometry.fromPolygonXY([points])
            settings = self.canvas().mapSettings()
            if settings.destinationCrs() != layer.crs():
                from qgis.core import QgsCoordinateTransform, QgsProject
                polygon.transform(QgsCoordinateTransform(settings.destinationCrs(), layer.crs(), QgsProject.instance()))
            request = QgsFeatureRequest().setFilterRect(polygon.boundingBox()).setNoAttributes()
            engine = QgsGeometry.createGeometryEngine(polygon.constGet())
            engine.prepareGeometry()
            ids = [f.id() for f in layer.getFeatures(request)
                   if f.hasGeometry() and engine.intersects(f.geometry().constGet())]
            layer.selectByIds(ids, _behavior(event))
        except Exception as error:
            self._window.message_bar.pushWarning("FilterMate", str(error))


class IdentifyTool(QgsMapToolIdentify):
    """A click opens the form of the feature under the pointer (the current layer first, then the others)."""

    def __init__(self, window):
        super().__init__(window.canvas)
        self._window = window
        self.setCursor(Qt.CursorShape.WhatsThisCursor)

    def canvasReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        position = event.pos()
        results = []
        current = self._window.tree_view.currentLayer()
        try:
            if current is not None:
                results = self.identify(position.x(), position.y(), [current],
                                        enum_member(QgsMapToolIdentify, "IdentifyMode", "TopDownAll"))
            if not results:
                results = self.identify(position.x(), position.y(),
                                        enum_member(QgsMapToolIdentify, "IdentifyMode", "TopDownStopAtFirst"))
        except Exception as error:
            self._window.message_bar.pushWarning("FilterMate", str(error))
            return
        if not results:
            self._window.message_bar.pushInfo("FilterMate", _tr("Nothing here."))
            return
        result = results[0]
        layer = result.mLayer
        if isinstance(layer, QgsVectorLayer):
            self._window.open_feature_form(layer, result.mFeature, modal=False)
            return
        values = ", ".join(f"{key}: {value}" for key, value in list(result.mAttributes.items())[:8])
        self._window.message_bar.pushInfo(layer.name() if layer is not None else "FilterMate", values or result.mLabel)
