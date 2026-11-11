# -*- coding: utf-8 -*-
"""Images of the map for the MCP server of the plugin: the map as the user sees it, and contact sheets of objects.

Main thread only. They go to the application that asked, through the MCP server of the plugin, and never to the
provider of the chat (decided with the user, 2026-11-11). Nothing in the project changes.
"""
from __future__ import annotations

import base64
import logging
import math
from typing import Any, Dict, List, Sequence, Tuple

from ...core.domain.layer_kind import LayerKind
from .operations import layer_kind

logger = logging.getLogger('FilterMate.MapImages')

JPEG_QUALITY = 85
MAX_TILES = 30
SHEET_COLUMNS = 6
# Around an object, a tile shows this many times its larger side, and at least this many metres-or-units.
TILE_ZOOM = 1.6
TILE_MIN_SIDE = 12.0
OUTLINE = (232, 30, 30)


def _main_thread_wait(loop) -> None:
    """Run ``loop``; on the main thread without user input (a click must not start a tool meanwhile)."""
    from qgis.PyQt.QtCore import QCoreApplication, QEventLoop, QThread
    application = QCoreApplication.instance()
    if application is not None and QThread.currentThread() is application.thread():
        loop.exec(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
    else:
        loop.exec()


def render(settings) -> Any:
    """The map of ``settings`` as a QImage, rendered and waited for."""
    from qgis.core import QgsMapRendererSequentialJob
    from qgis.PyQt.QtCore import QEventLoop
    job = QgsMapRendererSequentialJob(settings)
    loop = QEventLoop()
    job.finished.connect(loop.quit)
    job.start()
    if job.isActive():
        _main_thread_wait(loop)
    job.waitForFinished()
    return job.renderedImage()


def jpeg_base64(image) -> str:
    """``image`` (QImage) as JPEG, base64."""
    from qgis.PyQt.QtCore import QBuffer, QByteArray, QIODevice
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, "JPEG", JPEG_QUALITY):
        raise RuntimeError("the image could not be encoded")
    buffer.close()
    return base64.b64encode(bytes(data)).decode("ascii")


def _extent_in(crs, extent_wkt: str, extent_crs: str):
    """The bounding box of ``extent_wkt`` (in ``extent_crs``, or ``crs``) in ``crs``."""
    from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsGeometry, QgsProject
    geometry = QgsGeometry.fromWkt(extent_wkt)
    if geometry is None or geometry.isNull() or geometry.isEmpty():
        raise ValueError("the extent could not be read")
    source = QgsCoordinateReferenceSystem(extent_crs) if extent_crs else crs
    if not source.isValid():
        raise ValueError(f"unknown CRS {extent_crs!r}")
    rectangle = geometry.boundingBox()
    if source != crs:
        rectangle = QgsCoordinateTransform(source, crs, QgsProject.instance()).transformBoundingBox(rectangle)
    if rectangle.isEmpty() or not all(math.isfinite(v) for v in (rectangle.xMinimum(), rectangle.yMaximum())):
        raise ValueError("the extent is empty")
    return rectangle


def map_image(extent_wkt: str = '', crs: str = '', width: int = 1024) -> Tuple[str, Dict[str, Any]]:
    """The map as the user sees it (or the layers checked in the layer tree without a map window), JPEG base64.

    Returns:
        ``(image, info)``: ``info`` holds width, height, extent_wkt, crs and scale.
    """
    from qgis.core import QgsMapSettings, QgsProject
    from qgis.PyQt.QtCore import QSize
    from qgis.PyQt.QtGui import QColor
    try:
        from qgis.utils import iface
        canvas = iface.mapCanvas() if iface is not None else None
    except ImportError:
        canvas = None
    project = QgsProject.instance()
    if canvas is not None:
        settings = QgsMapSettings(canvas.mapSettings())
        extent = canvas.extent()
    else:
        settings = QgsMapSettings()
        layers = project.layerTreeRoot().checkedLayers()
        destination = project.crs()
        if not destination.isValid():  # a project without a CRS: the one of the extent, or of the first layer
            from qgis.core import QgsCoordinateReferenceSystem
            destination = QgsCoordinateReferenceSystem(crs) if crs else (layers[0].crs() if layers else destination)
        settings.setDestinationCrs(destination)
        settings.setLayers(layers)
        settings.setTransformContext(project.transformContext())
        settings.setBackgroundColor(QColor(255, 255, 255))
        extent = None
    if extent_wkt:
        extent = _extent_in(settings.destinationCrs(), extent_wkt, crs)
    if extent is None or extent.isEmpty():
        raise ValueError("no extent to draw: give extent_wkt (there is no map window)")
    width = max(128, min(int(width), 1600))
    height = max(64, min(1600, int(round(width * extent.height() / extent.width())))) if extent.width() > 0 else width
    settings.setOutputSize(QSize(width, height))
    settings.setExtent(extent)
    image = render(settings)
    shown = settings.visibleExtent()
    info = {'width': image.width(), 'height': image.height(), 'extent_wkt': shown.asWktPolygon(),
            'crs': settings.destinationCrs().authid(), 'scale': round(settings.scale())}
    return jpeg_base64(image), info


def _tile_extent(geometry, tile_min_side: float):
    """A square around ``geometry``, :data:`TILE_ZOOM` times its larger side."""
    from qgis.core import QgsRectangle
    box = geometry.boundingBox()
    side = max(box.width(), box.height()) * TILE_ZOOM
    side = max(side, tile_min_side)
    centre = box.center()
    return QgsRectangle(centre.x() - side / 2, centre.y() - side / 2, centre.x() + side / 2, centre.y() + side / 2)


def _outline(painter, geometry, extent, size: int) -> None:
    """``geometry`` drawn in red on a tile of ``extent`` and ``size`` pixels: its rings, or a circle for a point."""
    from qgis.PyQt.QtCore import QPointF
    from qgis.PyQt.QtGui import QPolygonF
    from ..qgis.coverage_layers.segmentation import _geometry_kinds

    def pixel(x: float, y: float):
        return QPointF((x - extent.xMinimum()) / extent.width() * size, (extent.yMaximum() - y) / extent.height() * size)
    if geometry.type() == _geometry_kinds()[0]:
        point = geometry.centroid().asPoint()
        painter.drawEllipse(pixel(point.x(), point.y()), 6.0, 6.0)
        return
    polygons = geometry.asMultiPolygon() if geometry.isMultipart() else [geometry.asPolygon()]
    for polygon in polygons:
        for ring in polygon:
            painter.drawPolygon(QPolygonF([pixel(point.x(), point.y()) for point in ring]))


def sheet_image(raster, example, geometries: Sequence[Any], tile: int = 160):
    """A contact sheet as a QImage: tile E for ``example`` (or none), then one tile per geometry, numbered from 1.

    Geometries are in the CRS of ``raster``; each tile is cut out of it around the object, outlined in red.
    """
    from qgis.core import QgsMapSettings, QgsProject
    from qgis.PyQt.QtCore import QRectF, QSize, Qt
    from qgis.PyQt.QtGui import QColor, QFont, QImage, QPainter, QPen
    tiles: List[Tuple[str, Any]] = ([('E', example)] if example is not None else []) + \
        [(str(index), geometry) for index, geometry in enumerate(geometries, start=1)]
    if not tiles:
        raise ValueError("nothing to show")
    columns = min(SHEET_COLUMNS, len(tiles))
    rows = math.ceil(len(tiles) / columns)
    sheet = QImage(columns * tile, rows * tile, QImage.Format.Format_RGB32)
    sheet.fill(QColor(255, 255, 255))
    settings = QgsMapSettings()
    settings.setDestinationCrs(raster.crs())
    settings.setTransformContext(QgsProject.instance().transformContext())
    settings.setLayers([raster])
    settings.setBackgroundColor(QColor(0, 0, 0))
    settings.setOutputSize(QSize(tile, tile))
    cell = raster.rasterUnitsPerPixelX() if raster.rasterUnitsPerPixelX() > 0 else 1.0
    painter = QPainter(sheet)
    try:
        font = QFont()
        font.setBold(True)
        font.setPixelSize(max(12, tile // 9))
        painter.setFont(font)
        for position, (label, geometry) in enumerate(tiles):
            extent = _tile_extent(geometry, max(TILE_MIN_SIDE, cell * 24))
            settings.setExtent(extent)
            image = render(settings)
            x, y = (position % columns) * tile, (position // columns) * tile
            painter.drawImage(x, y, image)
            painter.save()
            painter.translate(x, y)
            painter.setClipRect(QRectF(0, 0, tile, tile))
            painter.setPen(QPen(QColor(*OUTLINE), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            _outline(painter, geometry, settings.visibleExtent(), tile)
            box = QRectF(2, 2, painter.fontMetrics().horizontalAdvance(label) + 8, painter.fontMetrics().height() + 2)
            painter.fillRect(box, QColor(0, 0, 0, 200))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(box, int(Qt.AlignmentFlag.AlignCenter), label)
            painter.restore()
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawRect(x, y, tile - 1, tile - 1)
    finally:
        painter.end()
    return sheet


def contact_sheet(raster: str, layer: str, example_layer: str = '', tile: int = 160) -> Tuple[str, Dict[str, Any]]:
    """A contact sheet of the objects of ``layer`` cut out of ``raster``, JPEG base64, and which feature each tile is.

    The objects are the selected features of ``layer``, or all it shows; at most :data:`MAX_TILES`.
    """
    from qgis.core import QgsCoordinateTransform, QgsFeatureRequest, QgsGeometry, QgsProject
    from .drawn_objects import _layer_of_kind
    image = _layer_of_kind(raster, LayerKind.RASTER)
    if image is None or layer_kind(image) is not LayerKind.RASTER or not image.isValid():
        raise ValueError(f"raster layer {raster!r} not found")
    objects = _layer_of_kind(layer, LayerKind.VECTOR)
    if objects is None or layer_kind(objects) is not LayerKind.VECTOR:
        raise ValueError(f"layer {layer!r} not found among the vector layers")
    project = QgsProject.instance()

    def to_raster(source_layer, geometry):
        geometry = QgsGeometry(geometry)
        if source_layer.crs() != image.crs():
            geometry.transform(QgsCoordinateTransform(source_layer.crs(), image.crs(), project))
        return geometry
    example, example_fid = None, None
    if example_layer:
        source = _layer_of_kind(example_layer, LayerKind.VECTOR)
        if source is None or layer_kind(source) is not LayerKind.VECTOR:
            raise ValueError(f"example layer {example_layer!r} not found among the vector layers")
        selected = list(source.selectedFeatures())
        if len(selected) != 1:
            raise ValueError(f"'{source.name()}' has {len(selected)} features selected: select the one example")
        example, example_fid = to_raster(source, selected[0].geometry()), selected[0].id()
    request = QgsFeatureRequest().setLimit(MAX_TILES + 1)
    features = list(objects.getSelectedFeatures(request) if objects.selectedFeatureCount() else objects.getFeatures(request))
    features = [feature for feature in features if feature.hasGeometry() and not feature.geometry().isEmpty()]
    if not features:
        raise ValueError(f"'{objects.name()}' has no object to show")
    shown = features[:MAX_TILES]
    sheet = sheet_image(image, example, [to_raster(objects, feature.geometry()) for feature in shown],
                        max(96, min(int(tile), 256)))
    info = {'width': sheet.width(), 'height': sheet.height(), 'example_fid': example_fid,
            'tiles': [{'tile': index, 'fid': feature.id()} for index, feature in enumerate(shown, start=1)]}
    if len(features) > MAX_TILES:
        info['note'] = f"only the first {MAX_TILES} objects are shown: select the ones to look at"
    return jpeg_base64(sheet), info


def handlers() -> Dict[str, Any]:
    """The handlers of the tools of :data:`core.agent.tool_catalog.MCP_ONLY`, for the MCP server of the plugin."""
    from ...core.agent.tool_catalog import CONTACT_SHEET, MAP_IMAGE
    from ...core.agent.tool_executor import ToolFailure, WithImages

    def answer(make, *args, **kwargs):
        try:
            data, info = make(*args, **kwargs)
        except ValueError as exc:
            raise ToolFailure(str(exc)) from None
        return WithImages(info, (("image/jpeg", data),))

    return {
        MAP_IMAGE: lambda args: answer(map_image, args.get("extent_wkt", ""), args.get("crs", ""), args.get("width", 1024)),
        CONTACT_SHEET: lambda args: answer(contact_sheet, args["raster"], args["layer"], args.get("example_layer", ""),
                                           args.get("tile", 160)),
    }
