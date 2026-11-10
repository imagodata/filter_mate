# -*- coding: utf-8 -*-
"""Print layouts for the agent: a map page with its title, legend, scale bar and north arrow, and its export.

Main thread only, plain dicts out. A layout is added to the project, so the user opens it in the layout designer
and finishes it there; undoing the turn of the chat removes it (``adapters/agent/turn_effects.py`` keeps its XML,
redoing the turn reads it again). An export writes a PDF or a PNG into a folder the caller has resolved under the
export root: never a path from the model.
"""
from __future__ import annotations

import logging
import math
import os
from typing import Any, Dict, List, Optional

from .operations import resolve_layer

logger = logging.getLogger('FilterMate.Layouts')

PAGES = ('A4', 'A3', 'A5', 'Letter')
MARGIN = 10.0
TITLE_HEIGHT = 14.0
NORTH_ARROW = ':/images/north_arrows/layout_default_north_arrow.svg'
MAX_DPI = 600
MAX_NAME_CHARS = 100
MAX_LISTED = 50


def _mm():
    from qgis.core import QgsUnitTypes
    return getattr(QgsUnitTypes, 'LayoutMillimeters', None) or QgsUnitTypes.LayoutUnit.LayoutMillimeters


def _layout(name: str):
    from qgis.core import QgsProject
    layout = QgsProject.instance().layoutManager().layoutByName(str(name or ''))
    if layout is None:
        names = layout_names()
        raise ValueError(f"no layout {name!r} in the project" + (f": {', '.join(names)}" if names else ""))
    return layout


def layout_names() -> List[str]:
    from qgis.core import QgsProject
    return [item.name() for item in QgsProject.instance().layoutManager().printLayouts()][:MAX_LISTED]


def _extent(extent: Optional[List[float]], extent_layer: str, layers: List[Any], target_crs):
    """The rectangle to show, in ``target_crs``: given, a layer's, the map view, or the layers shown."""
    from qgis.core import QgsCoordinateTransform, QgsProject, QgsRectangle
    if extent:
        if len(extent) != 4 or not all(isinstance(item, (int, float)) and math.isfinite(item) for item in extent):
            raise ValueError('extent is [xmin, ymin, xmax, ymax]')
        rectangle = QgsRectangle(*extent)
        if rectangle.isEmpty():
            raise ValueError('extent has no area')
        return rectangle, 'given'
    project = QgsProject.instance()
    if extent_layer:
        layer = resolve_layer(extent_layer)
        if layer is None:
            raise ValueError(f"layer {extent_layer!r} not found")
        sources, origin = [layer], 'layer'
    else:
        try:
            from qgis.utils import iface
            canvas = iface.mapCanvas() if iface is not None else None
        except (ImportError, AttributeError):
            canvas = None
        if canvas is not None and not canvas.extent().isEmpty():
            transform = QgsCoordinateTransform(canvas.mapSettings().destinationCrs(), target_crs, project)
            return transform.transformBoundingBox(canvas.extent()), 'view'
        sources, origin = layers, 'layers'
    union = None
    for layer in sources:
        rectangle = layer.extent()
        if rectangle.isNull():
            continue
        transform = QgsCoordinateTransform(layer.crs(), target_crs, project)
        try:
            rectangle = transform.transformBoundingBox(rectangle)
        except Exception:  # QgsCsException: out of the domain of the map CRS, the layer is left out of the extent
            logger.debug("Layout extent: %s left out", layer.name(), exc_info=True)
            continue
        if union is None:
            union = QgsRectangle(rectangle)
        else:
            union.combineExtentWith(rectangle)
    if union is None:
        raise ValueError('no extent to show: give extent or extent_layer')
    if union.isEmpty():
        union.grow(max(abs(union.xMinimum()), abs(union.yMinimum()), 1.0) * 0.001)
    else:
        union.scale(1.05)
    return union, origin


def _page_size(layout, page: str, orientation: str):
    from qgis.core import QgsLayoutItemPage
    if page not in PAGES:
        raise ValueError(f"page is one of {', '.join(PAGES)}")
    if orientation not in ('landscape', 'portrait'):
        raise ValueError('orientation is landscape or portrait')
    orientations = getattr(QgsLayoutItemPage, 'Orientation', QgsLayoutItemPage)
    first = layout.pageCollection().page(0)
    if not first.setPageSize(page, orientations.Landscape if orientation == 'landscape' else orientations.Portrait):
        raise ValueError(f"page {page} is not known to this QGIS")
    size = first.pageSize()
    return size.width(), size.height()


def create_layout(name: str, title: str = '', page: str = 'A4', orientation: str = 'landscape',
                  layers: Optional[List[str]] = None, extent: Optional[List[float]] = None, extent_layer: str = '',
                  legend: bool = True, scale_bar: bool = True, north_arrow: bool = True) -> Dict[str, Any]:
    """A print layout added to the project: a map of the layers shown, and its title, legend, scale and north.

    Args:
        layers: The layers of the map; the layers checked in the layer tree, as the map shows, by default.
        extent: ``[xmin, ymin, xmax, ymax]`` in the project CRS; by default ``extent_layer``, then the map view,
            then the layers shown.

    Raises:
        ValueError: A name already taken or empty, an unknown layer or page, nothing to show.
    """
    from qgis.core import (QgsLayoutItemLabel, QgsLayoutItemLegend, QgsLayoutItemMap, QgsLayoutItemPicture,
                           QgsLayoutItemScaleBar, QgsLayoutPoint, QgsLayoutSize, QgsPrintLayout, QgsProject)
    from qgis.PyQt.QtGui import QFont
    project = QgsProject.instance()
    name = ' '.join(str(name or '').split())[:MAX_NAME_CHARS]
    if not name:
        raise ValueError('a layout needs a name')
    if project.layoutManager().layoutByName(name) is not None:
        raise ValueError(f"the project has a layout named {name!r} already: choose another name")
    chosen = []
    for reference in layers or []:
        layer = resolve_layer(reference)
        if layer is None:
            raise ValueError(f"layer {reference!r} not found")
        chosen.append(layer)
    shown = chosen or [node.layer() for node in project.layerTreeRoot().findLayers()
                       if node.isVisible() and node.layer() is not None]
    if not shown:
        raise ValueError('no layer is shown: check one in the layer tree, or give layers')

    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName(name)
    width, height = _page_size(layout, page, orientation)
    mm = _mm()
    top = MARGIN + (TITLE_HEIGHT if title else 0.0)
    map_item = QgsLayoutItemMap(layout)
    map_item.attemptMove(QgsLayoutPoint(MARGIN, top, mm))
    map_item.attemptResize(QgsLayoutSize(width - 2 * MARGIN, height - top - MARGIN, mm))
    crs = project.crs() if project.crs().isValid() else shown[0].crs()  # a new project may have none yet
    map_item.setCrs(crs)
    if chosen:
        map_item.setLayers(chosen)
        map_item.setKeepLayerSet(True)
    map_item.setFrameEnabled(True)
    layout.addLayoutItem(map_item)
    rectangle, origin = _extent(extent, extent_layer, shown, crs)
    map_item.zoomToExtent(rectangle)
    items = ['map']
    if title:
        label = QgsLayoutItemLabel(layout)
        label.setText(' '.join(str(title).split())[:200])
        font = QFont()
        font.setPointSize(20)
        font.setBold(True)
        if hasattr(label, 'setFont'):
            label.setFont(font)
        label.attemptMove(QgsLayoutPoint(MARGIN, MARGIN - 2, mm))
        label.attemptResize(QgsLayoutSize(width - 2 * MARGIN, TITLE_HEIGHT, mm))
        layout.addLayoutItem(label)
        items.append('title')
    if legend:
        item = QgsLayoutItemLegend(layout)
        item.setLinkedMap(map_item)
        item.setTitle('')
        if chosen and hasattr(item, 'setLegendFilterByMapEnabled'):
            item.setLegendFilterByMapEnabled(True)
        item.setBackgroundEnabled(True)
        item.setFrameEnabled(True)
        layout.addLayoutItem(item)
        item.adjustBoxSize()
        size = item.sizeWithUnits()
        item.attemptMove(QgsLayoutPoint(width - MARGIN - size.width() - 3, top + 3, mm))
        items.append('legend')
    if scale_bar:
        bar = QgsLayoutItemScaleBar(layout)
        bar.setLinkedMap(map_item)
        bar.applyDefaultSize()
        bar.setBackgroundEnabled(True)
        layout.addLayoutItem(bar)
        bar.attemptMove(QgsLayoutPoint(MARGIN + 3, height - MARGIN - 18, mm))
        items.append('scale_bar')
    if north_arrow:
        arrow = QgsLayoutItemPicture(layout)
        arrow.setPicturePath(NORTH_ARROW)
        arrow.setLinkedMap(map_item)
        arrow.attemptResize(QgsLayoutSize(12, 12, mm))
        arrow.attemptMove(QgsLayoutPoint(MARGIN + 3, top + 3, mm))
        layout.addLayoutItem(arrow)
        items.append('north_arrow')
    if not project.layoutManager().addLayout(layout):
        raise ValueError(f"the layout {name!r} could not be added to the project")
    scale = map_item.scale()
    return {'name': name, 'page': page, 'orientation': orientation, 'items': items, 'extent_from': origin,
            'scale': round(scale) if math.isfinite(scale) else None, 'layers': [layer.name() for layer in chosen] or 'shown in the layer tree',
            'note': 'Added to the project: the user can open it in the layout designer and change anything.'}


def export_layout(name: str, folder: str, file_format: str = 'pdf', dpi: int = 150) -> Dict[str, Any]:
    """Write a layout of the project into ``folder`` (resolved by the caller under the export root).

    Raises:
        ValueError: An unknown layout or format, a resolution out of range, a failed export.
    """
    from qgis.core import QgsLayoutExporter
    layout = _layout(name)
    if file_format not in ('pdf', 'png'):
        raise ValueError('format is pdf or png')
    if not 72 <= int(dpi) <= MAX_DPI:
        raise ValueError(f"dpi goes from 72 to {MAX_DPI}")
    safe = ''.join(char if char.isalnum() or char in '-_ ' else '_' for char in layout.name()).strip() or 'layout'
    path = os.path.join(folder, f"{safe}.{file_format}")
    exporter = QgsLayoutExporter(layout)
    if file_format == 'pdf':
        settings = QgsLayoutExporter.PdfExportSettings()
        settings.dpi = int(dpi)
        result = exporter.exportToPdf(path, settings)
    else:
        settings = QgsLayoutExporter.ImageExportSettings()
        settings.dpi = int(dpi)
        result = exporter.exportToImage(path, settings)
    if int(getattr(result, 'value', result)) != 0 or not os.path.isfile(path):
        raise ValueError(f"the layout could not be exported ({exporter.errorMessage() or result})")
    return {'name': layout.name(), 'format': file_format, 'dpi': int(dpi), 'path': path,
            'bytes': os.path.getsize(path)}


def layout_xml(layout) -> str:
    """The layout as XML, to bring it back after an undo of the turn."""
    from qgis.core import QgsReadWriteContext
    from qgis.PyQt.QtXml import QDomDocument
    document = QDomDocument()
    document.appendChild(layout.writeXml(document, QgsReadWriteContext()))
    return document.toString()


def layout_from_xml(xml: str) -> bool:
    """Add the layout ``xml`` holds back to the project; False when it cannot come back."""
    from qgis.core import QgsPrintLayout, QgsProject, QgsReadWriteContext
    from qgis.PyQt.QtXml import QDomDocument
    document = QDomDocument()
    if not document.setContent(xml):
        return False
    layout = QgsPrintLayout(QgsProject.instance())
    if not layout.readXml(document.documentElement(), document, QgsReadWriteContext()):
        return False
    return bool(QgsProject.instance().layoutManager().addLayout(layout))
