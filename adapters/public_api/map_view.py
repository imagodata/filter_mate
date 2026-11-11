# -*- coding: utf-8 -*-
"""The map as an image, for a model that reads images: what the user sees, or a given extent or layer.

Main thread only. Rendered by ``QgsMapRendererSequentialJob`` from the settings of the map canvas (its layers, its
styles, its CRS), or, without a canvas, from the layers checked in the layer tree; a ``canvas.grab()`` would hand
back whatever the screen last painted. JPEG, a few hundred kilobytes at most: the chat sends it with the request it
was taken in only.
"""
from __future__ import annotations

import base64
import math
from typing import Any, Dict, List, Optional, Tuple

from .operations import resolve_layer

MAX_SIDE = 1568  # what the providers of images take before scaling down themselves
MIN_SIDE = 256
JPEG_QUALITY = 80


def _canvas():
    try:
        from qgis.utils import iface
        return iface.mapCanvas() if iface is not None else None
    except (ImportError, AttributeError):
        return None


def _settings_without_canvas():
    """Map settings of the layers checked in the tree, top first, over their union."""
    from qgis.core import QgsCoordinateTransform, QgsMapSettings, QgsProject, QgsRectangle
    project = QgsProject.instance()
    layers = [node.layer() for node in project.layerTreeRoot().findLayers()
              if node.isVisible() and node.layer() is not None and node.layer().isValid()]
    if not layers:
        raise ValueError('no layer is shown: check one in the layer tree')
    crs = project.crs() if project.crs().isValid() else layers[0].crs()
    union = None
    for layer in layers:
        try:
            box = QgsCoordinateTransform(layer.crs(), crs, project).transformBoundingBox(layer.extent())
        except Exception:  # QgsCsException: out of the domain of the map CRS, left out of the extent
            box = None
        if box is None or box.isNull():
            continue
        if union is None:
            union = QgsRectangle(box)
        else:
            union.combineExtentWith(box)
    settings = QgsMapSettings()
    settings.setLayers(layers)
    settings.setDestinationCrs(crs)
    settings.setTransformContext(project.transformContext())
    if union is not None:
        if union.isEmpty():
            union.grow(max(abs(union.xMinimum()), abs(union.yMinimum()), 1.0) * 0.001)
        else:
            union.scale(1.05)
        settings.setExtent(union)
    return settings


def _extent_of(layer_reference: str, crs):
    from qgis.core import QgsCoordinateTransform, QgsProject
    layer = resolve_layer(layer_reference)
    if layer is None:
        raise ValueError(f"layer {layer_reference!r} not found")
    box = QgsCoordinateTransform(layer.crs(), crs, QgsProject.instance()).transformBoundingBox(layer.extent())
    if box.isNull():
        raise ValueError(f"'{layer.name()}' has no extent to show")
    if box.isEmpty():
        box.grow(max(abs(box.xMinimum()), abs(box.yMinimum()), 1.0) * 0.001)
    else:
        box.scale(1.05)
    return box


def _size(extent, width: int) -> Tuple[int, int]:
    width = max(MIN_SIDE, min(int(width), MAX_SIDE))
    ratio = extent.height() / extent.width() if extent.width() > 0 else 1.0
    height = int(round(width * ratio))
    if height > MAX_SIDE:
        width, height = int(round(MAX_SIDE / ratio)), MAX_SIDE
    return max(width, MIN_SIDE // 4), max(height, MIN_SIDE // 4)


def render_map(extent: Optional[List[float]] = None, layer: str = '', width: int = 1024) -> Tuple[Dict[str, Any], bytes]:
    """``(what was rendered, JPEG bytes)``.

    Args:
        extent: ``[xmin, ymin, xmax, ymax]`` in the CRS of the map; the view of the map by default.
        layer: Show the whole of this layer instead.

    Raises:
        ValueError: An extent with no area, an unknown layer, nothing shown, a render that failed.
    """
    from qgis.core import QgsMapRendererSequentialJob, QgsMapSettings, QgsRectangle
    from qgis.PyQt.QtCore import QBuffer, QByteArray, QIODevice
    canvas = _canvas()
    settings = QgsMapSettings(canvas.mapSettings()) if canvas is not None else _settings_without_canvas()
    origin = 'view'
    if extent:
        if len(extent) != 4 or not all(isinstance(item, (int, float)) and math.isfinite(item) for item in extent):
            raise ValueError('extent is [xmin, ymin, xmax, ymax]')
        rectangle = QgsRectangle(*extent)
        if rectangle.isEmpty():
            raise ValueError('extent has no area')
        settings.setExtent(rectangle)
        origin = 'given'
    elif layer:
        settings.setExtent(_extent_of(layer, settings.destinationCrs()))
        origin = 'layer'
    elif canvas is None:
        origin = 'layers'
    shown = settings.extent()
    if shown.isEmpty():
        raise ValueError('nothing to show: give extent or layer')
    from qgis.PyQt.QtCore import QSize
    width_px, height_px = _size(shown, width)
    settings.setOutputSize(QSize(width_px, height_px))
    settings.setOutputDpi(96)
    job = QgsMapRendererSequentialJob(settings)
    job.start()
    job.waitForFinished()
    image = job.renderedImage()
    if image.isNull():
        raise ValueError('the map could not be rendered')
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, 'JPG', JPEG_QUALITY)
    buffer.close()
    visible = settings.visibleExtent()
    meta = {
        'width': image.width(), 'height': image.height(), 'crs': settings.destinationCrs().authid(),
        'extent': [visible.xMinimum(), visible.yMinimum(), visible.xMaximum(), visible.yMaximum()],
        'scale': round(settings.scale()) if math.isfinite(settings.scale()) else None, 'extent_from': origin,
        'layers': [item.name() for item in settings.layers()][:50],
        'errors': [str(error.message)[:200] for error in job.errors()][:5],
    }
    return meta, bytes(data)


def render_map_base64(extent: Optional[List[float]] = None, layer: str = '', width: int = 1024) -> Tuple[Dict[str, Any], str]:
    meta, jpeg = render_map(extent, layer, width)
    return meta, base64.b64encode(jpeg).decode('ascii')
