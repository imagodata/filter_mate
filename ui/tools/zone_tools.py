# -*- coding: utf-8 -*-
"""
Zone map tool: the shapes of the QGIS selection tools (rectangle, polygon, freehand, radius)
drawn on the map, given back as one polygon geometry in the canvas CRS.

Used by the Zone button of the point cloud rail (ATTRIBUTES): the bounding box of the
shape becomes X / Y conditions, the shape itself the source geometry of the cross filter.
"""
import math

try:
    from qgis.PyQt.QtCore import Qt, pyqtSignal
    from qgis.PyQt.QtGui import QColor
    from qgis.core import QgsGeometry, QgsPointXY, QgsRectangle, QgsWkbTypes
    from qgis.gui import QgsMapTool, QgsRubberBand
    QT_AVAILABLE = True
except ImportError:  # pragma: no cover - unit tests without QGIS
    QT_AVAILABLE = False
    QgsMapTool = object

    def pyqtSignal(*_args):
        return None

SHAPE_RECTANGLE = 'rectangle'
SHAPE_POLYGON = 'polygon'
SHAPE_FREEHAND = 'freehand'
SHAPE_RADIUS = 'radius'
SHAPES = (SHAPE_RECTANGLE, SHAPE_POLYGON, SHAPE_FREEHAND, SHAPE_RADIUS)
RADIUS_SEGMENTS = 36
FILL_COLOR = '#4fd1b0'  # the point cloud colour of the mockup


def circle_points(center_x: float, center_y: float, radius: float, segments: int = RADIUS_SEGMENTS):
    """``(x, y)`` vertices of a circle, the first one repeated last (pure, testable)."""
    points = []
    for index in range(max(3, int(segments))):
        angle = 2 * math.pi * index / max(3, int(segments))
        points.append((center_x + radius * math.cos(angle), center_y + radius * math.sin(angle)))
    points.append(points[0])
    return points


def polygon_wkt(points) -> str:
    """WKT polygon of ``(x, y)`` vertices (closed if needed); ``""`` below three distinct vertices."""
    distinct = []
    for x, y in points:
        if not distinct or distinct[-1] != (x, y):
            distinct.append((float(x), float(y)))
    if distinct and distinct[0] == distinct[-1]:
        distinct.pop()
    if len(distinct) < 3:
        return ""
    ring = ", ".join(f"{x!r} {y!r}" for x, y in [*distinct, distinct[0]])
    return f"POLYGON(({ring}))"


def _polygon_type():
    geometry_type = getattr(QgsWkbTypes, 'GeometryType', None)
    if geometry_type is not None and hasattr(geometry_type, 'PolygonGeometry'):
        return geometry_type.PolygonGeometry
    return QgsWkbTypes.PolygonGeometry


class ShapeZoneTool(QgsMapTool):
    """Draw a zone as the QGIS selection tools do; ``zoneDrawn(geometry)`` when the shape is done.

    Rectangle and radius: press, drag, release. Freehand: press, move, release. Polygon:
    a left click per vertex, a right click (or a double click) closes it; Escape cancels.
    """

    zoneDrawn = pyqtSignal(object)

    def __init__(self, canvas, shape: str = SHAPE_RECTANGLE) -> None:
        super().__init__(canvas)
        self._canvas = canvas
        self._shape = shape if shape in SHAPES else SHAPE_RECTANGLE
        self._points = []
        self._anchor = None
        self._dragging = False
        self._band = None
        self.setCursor(Qt.CursorShape.CrossCursor)

    @property
    def shape(self) -> str:
        return self._shape

    def set_shape(self, shape: str) -> None:
        self._shape = shape if shape in SHAPES else SHAPE_RECTANGLE
        self._reset()

    # --- rubber band ---

    def _rubber_band(self):
        if self._band is None:
            self._band = QgsRubberBand(self._canvas, _polygon_type())
            colour = QColor(FILL_COLOR)
            self._band.setStrokeColor(colour)
            fill = QColor(colour)
            fill.setAlpha(60)
            self._band.setFillColor(fill)
            self._band.setWidth(2)
        return self._band

    def _show(self, points) -> None:
        band = self._rubber_band()
        band.reset(_polygon_type())
        for x, y in points:
            band.addPoint(QgsPointXY(x, y), False)
        band.closePoints()
        band.show()

    def _reset(self) -> None:
        self._points = []
        self._anchor = None
        self._dragging = False
        if self._band is not None:
            self._band.reset(_polygon_type())

    def deactivate(self) -> None:  # noqa: N802 - Qt override
        self._reset()
        super().deactivate()

    # --- events ---

    def canvasPressEvent(self, event) -> None:  # noqa: N802 - Qt override
        point = event.mapPoint()
        if event.button() == Qt.MouseButton.RightButton:
            if self._shape == SHAPE_POLYGON:
                self._finish_polygon()
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._shape == SHAPE_POLYGON:
            self._points.append((point.x(), point.y()))
            self._show(self._points)
            return
        self._anchor = (point.x(), point.y())
        self._dragging = True
        self._points = [self._anchor]

    def canvasMoveEvent(self, event) -> None:  # noqa: N802 - Qt override
        point = event.mapPoint()
        if self._shape == SHAPE_POLYGON:
            if self._points:
                self._show([*self._points, (point.x(), point.y())])
            return
        if not self._dragging or self._anchor is None:
            return
        if self._shape == SHAPE_FREEHAND:
            self._points.append((point.x(), point.y()))
            self._show(self._points)
        else:
            self._show(self._shape_points(point.x(), point.y()))

    def canvasReleaseEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.button() != Qt.MouseButton.LeftButton or self._shape == SHAPE_POLYGON:
            return
        point = event.mapPoint()
        if not self._dragging or self._anchor is None:
            return
        if self._shape == SHAPE_FREEHAND:
            self._points.append((point.x(), point.y()))
            points = self._points
        else:
            points = self._shape_points(point.x(), point.y())
        self._emit(points)

    def canvasDoubleClickEvent(self, event) -> None:  # noqa: N802 - Qt override
        if self._shape == SHAPE_POLYGON and event.button() == Qt.MouseButton.LeftButton:
            self._finish_polygon()

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.key() == Qt.Key.Key_Escape:
            self._reset()
            return
        super().keyPressEvent(event)

    # --- shapes ---

    def _shape_points(self, x: float, y: float):
        ax, ay = self._anchor
        if self._shape == SHAPE_RADIUS:
            return circle_points(ax, ay, math.hypot(x - ax, y - ay))
        rect = QgsRectangle(QgsPointXY(ax, ay), QgsPointXY(x, y))
        return [(rect.xMinimum(), rect.yMinimum()), (rect.xMaximum(), rect.yMinimum()),
                (rect.xMaximum(), rect.yMaximum()), (rect.xMinimum(), rect.yMaximum()), (rect.xMinimum(), rect.yMinimum())]

    def _finish_polygon(self) -> None:
        points = list(self._points)
        self._emit(points)

    def _emit(self, points) -> None:
        wkt = polygon_wkt(points)
        self._reset()
        if not wkt:
            return
        geometry = QgsGeometry.fromWkt(wkt)
        if geometry is None or geometry.isEmpty() or geometry.area() <= 0:
            return
        self.zoneDrawn.emit(geometry)
