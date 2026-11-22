# -*- coding: utf-8 -*-
"""Print layouts for the agent: a map page with its title, legend, scale bar and north arrow, its atlas, what it
holds, and its export (PDF, PNG, JPG, SVG, TIFF; one page per feature for an atlas).

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
    from qgis.core import (QgsLayoutItem, QgsLayoutItemLabel, QgsLayoutItemLegend, QgsLayoutItemMap, QgsLayoutItemPicture,
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
        if hasattr(label, 'setTextFormat'):  # 3.24 and later; setFont is deprecated since 3.40
            from qgis.core import QgsTextFormat
            text_format = QgsTextFormat.fromQFont(font)
            text_format.setSize(20)
            label.setTextFormat(text_format)
        else:
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
        # Held by its upper right corner: its size is only known once QGIS has drawn it, and it grows to the left.
        corner = getattr(QgsLayoutItem, 'ReferencePoint', QgsLayoutItem).UpperRight
        item.setReferencePoint(corner)
        layout.addLayoutItem(item)
        item.attemptMove(QgsLayoutPoint(width - MARGIN - 3, top + 3, mm))
        item.adjustBoxSize()
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


FORMATS = ('pdf', 'png', 'jpg', 'svg', 'tif')
IMAGE_FORMATS = ('png', 'jpg', 'tif')
MAX_ATLAS_PAGES = 200  # one export on the main thread: beyond, filter the coverage layer first
MAX_ITEMS_LISTED = 60


def _safe(text: str, fallback: str) -> str:
    return ''.join(char if char.isalnum() or char in '-_ ' else '_' for char in str(text)).strip() or fallback


def tiff_available() -> bool:
    """Whether Qt here writes TIFF (the Windows QGIS does; some Linux packages leave its plugin out)."""
    from qgis.PyQt.QtGui import QImageWriter
    return any(bytes(name).lower() in (b'tif', b'tiff') for name in QImageWriter.supportedImageFormats())


def _ok(result) -> bool:
    """Whether an ExportResult (or ``(ExportResult, error)`` of an atlas export) is Success."""
    if isinstance(result, tuple):
        result = result[0]
    return int(getattr(result, 'value', result)) == 0


def _settings(file_format: str, dpi: int, georeference: bool):
    from qgis.core import QgsLayoutExporter
    if file_format == 'pdf':
        settings = QgsLayoutExporter.PdfExportSettings()
        settings.appendGeoreference = bool(georeference)
    elif file_format == 'svg':
        settings = QgsLayoutExporter.SvgExportSettings()
    else:
        settings = QgsLayoutExporter.ImageExportSettings()
        settings.generateWorldFile = bool(georeference)  # a .pgw / .jgw / .tfw beside each image of a map page
    settings.dpi = int(dpi)
    return settings


def export_layout(name: str, folder: str, file_format: str = 'pdf', dpi: int = 150, georeference: bool = True,
                  atlas: bool = False, single_file: bool = True) -> Dict[str, Any]:
    """Write a layout of the project into ``folder`` (resolved by the caller under the export root).

    2026-11-12: ``folder`` is created when missing, as ``export_layers`` does (the export failed on a new
    sub-folder), and an existing file is never overwritten: ``<name>_2.pdf``, ``<name>_3.pdf``... instead,
    for every page an image or SVG export writes (``<name>_2.png`` is its second page).

    2026-11-22: PDF, PNG, JPG, SVG or TIFF; georeferenced where QGIS can (a PDF, a world file beside an image).
    ``atlas``: one page per feature of its coverage layer as filtered now (set_atlas), in a new sub-folder
    ``<name>_atlas`` (``_2``... when taken): one PDF of every page (``single_file``) or one file per feature, named
    by the atlas.

    Raises:
        ValueError: An unknown layout or format, a resolution out of range, a folder that cannot be made, an
            atlas not set or too large, a failed export.
    """
    from qgis.core import QgsLayoutExporter
    layout = _layout(name)
    if file_format not in FORMATS:
        raise ValueError(f"format is one of {', '.join(FORMATS)}")
    if not 72 <= int(dpi) <= MAX_DPI:
        raise ValueError(f"dpi goes from 72 to {MAX_DPI}")
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError as exc:
        raise ValueError(f"the export folder could not be created ({exc.strerror or exc})") from None
    if file_format == 'tif' and not tiff_available():
        raise ValueError('TIFF cannot be written by this QGIS (its Qt has no TIFF plugin): png or pdf instead')
    safe = _safe(layout.name(), 'layout')
    settings = _settings(file_format, dpi, georeference)
    if atlas:
        return _export_atlas(layout, folder, safe, file_format, settings, single_file)
    pages = 1
    if file_format != 'pdf':
        try:
            pages = max(1, int(layout.pageCollection().pageCount()))
        except Exception:  # nosec B110 - one page assumed
            pages = 1

    def written(stem):
        """The files the exporter writes for ``stem``: one image or SVG per page, ``<stem>_2.png`` from the
        second."""
        return [os.path.join(folder, f"{stem}.{file_format}")] + [
            os.path.join(folder, f"{stem}_{page}.{file_format}") for page in range(2, pages + 1)]

    stem, index = safe, 2
    while any(os.path.exists(candidate) for candidate in written(stem)):
        stem, index = f"{safe}_{index}", index + 1
    path = written(stem)[0]
    exporter = QgsLayoutExporter(layout)
    if file_format == 'pdf':
        result = exporter.exportToPdf(path, settings)
    elif file_format == 'svg':
        result = exporter.exportToSvg(path, settings)
    else:
        result = exporter.exportToImage(path, settings)
    if not _ok(result) or not os.path.isfile(path):
        raise ValueError(f"the layout could not be exported ({exporter.errorMessage() or result})")
    files = [candidate for candidate in written(stem) if os.path.isfile(candidate)]
    answer = {'name': layout.name(), 'format': file_format, 'dpi': int(dpi), 'path': path,
              'bytes': sum(os.path.getsize(item) for item in files)}
    if len(files) > 1:
        answer['files'] = len(files)
    return answer


def _export_atlas(layout, folder: str, safe: str, file_format: str, settings, single_file: bool) -> Dict[str, Any]:
    from qgis.core import QgsLayoutExporter
    atlas = layout.atlas() if hasattr(layout, 'atlas') else None
    if atlas is None or not atlas.enabled() or atlas.coverageLayer() is None:
        raise ValueError(f"the layout {layout.name()!r} has no atlas: set_atlas first")
    count = atlas.updateFeatures()
    if count <= 0:
        raise ValueError('the atlas has no page: its coverage layer, as filtered now, keeps no feature')
    if count > MAX_ATLAS_PAGES:
        raise ValueError(f"the atlas has {count} pages: filter its coverage layer below {MAX_ATLAS_PAGES} first")
    # A folder of its own, never one that exists: the atlas names its files, and none may be overwritten.
    target, index = os.path.join(folder, f"{safe}_atlas"), 2
    while os.path.exists(target):
        target, index = os.path.join(folder, f"{safe}_atlas_{index}"), index + 1
    os.makedirs(target)
    if not atlas.filenameExpression():
        atlas.setFilenameExpression(f"'{safe.replace(chr(39), '_')}_' || lpad(@atlas_featurenumber, 3, '0')")
    if file_format == 'pdf' and single_file:
        path = os.path.join(target, f"{safe}.pdf")
        result = QgsLayoutExporter.exportToPdf(atlas, path, settings)
    elif file_format == 'pdf':
        result = QgsLayoutExporter.exportToPdfs(atlas, os.path.join(target, safe), settings)
    elif file_format == 'svg':
        result = QgsLayoutExporter.exportToSvg(atlas, os.path.join(target, safe), settings)
    else:
        result = QgsLayoutExporter.exportToImage(atlas, os.path.join(target, safe), file_format, settings)
    files = sorted(os.path.join(target, item) for item in os.listdir(target)
                   if item.lower().endswith('.' + file_format))
    if not _ok(result) or not files:
        error = result[1] if isinstance(result, tuple) and len(result) > 1 else result
        raise ValueError(f"the atlas could not be exported ({error})")
    return {'name': layout.name(), 'format': file_format, 'dpi': int(settings.dpi), 'path': target,
            'bytes': sum(os.path.getsize(item) for item in files), 'files': len(files), 'pages': count,
            'atlas': True}


# --- reading a layout and its atlas ------------------------------------------------------------------------------

def _kind(item) -> str:
    from qgis.core import (QgsLayoutItemLabel, QgsLayoutItemLegend, QgsLayoutItemMap, QgsLayoutItemPicture,
                           QgsLayoutItemScaleBar, QgsLayoutItemShape)
    for cls, name in ((QgsLayoutItemMap, 'map'), (QgsLayoutItemLabel, 'text'), (QgsLayoutItemLegend, 'legend'),
                      (QgsLayoutItemScaleBar, 'scale_bar'), (QgsLayoutItemPicture, 'picture'),
                      (QgsLayoutItemShape, 'shape')):
        if isinstance(item, cls):
            return name
    try:
        from qgis.core import QgsLayoutFrame
        if isinstance(item, QgsLayoutFrame):
            multi = item.multiFrame()
            return 'table' if multi is not None and 'Table' in type(multi).__name__ else 'frame'
    except ImportError:
        pass
    return type(item).__name__.replace('QgsLayoutItem', '').lower() or 'item'


def item_ref(item) -> str:
    """How an item is named to the agent: its id, else the first 8 characters of its uuid."""
    return item.id() or item.uuid().strip('{}')[:8]


def layout_items(layout) -> List[Any]:
    """The items of a layout a user sees (not its pages), top to bottom."""
    from qgis.core import QgsLayoutItem, QgsLayoutItemPage
    items = [item for item in layout.items() if isinstance(item, QgsLayoutItem)
             and not isinstance(item, QgsLayoutItemPage)]
    return sorted(items, key=lambda item: (item.page(), item.positionWithUnits().y(), item.positionWithUnits().x()))


def _describe_item(layout, item) -> Dict[str, Any]:
    kind = _kind(item)
    # In millimetres from the top left of its page, as the designer shows them.
    point = layout.convertToLayoutUnits(item.pagePositionWithUnits())
    size = layout.convertToLayoutUnits(item.sizeWithUnits())
    row: Dict[str, Any] = {'ref': item_ref(item), 'type': kind, 'page': item.page() + 1,
                           'x_mm': round(point.x(), 1), 'y_mm': round(point.y(), 1),
                           'width_mm': round(size.width(), 1), 'height_mm': round(size.height(), 1)}
    if kind == 'map':
        scale = item.scale()
        row['scale'] = round(scale) if math.isfinite(scale) else None
        row['layers'] = [layer.name() for layer in item.layers()] if item.keepLayerSet() else 'shown in the tree'
        if item.atlasDriven():
            row['atlas_driven'] = True
    elif kind == 'text':
        row['text'] = ' '.join(str(item.text()).split())[:200]
    elif kind == 'picture':
        if item.customProperty('filtermate/chart'):
            row['chart'] = True
        elif str(item.picturePath()).endswith('north_arrow.svg'):
            row['north_arrow'] = True
    return row


def describe_layout(name: str = '') -> Dict[str, Any]:
    """A layout of the project: its pages, its items (``ref`` names them), its atlas. Without ``name``: the
    layouts of the project and the templates of the profile."""
    from qgis.core import QgsLayoutItemMap
    if not name:
        return {'layouts': layout_names(), 'templates': template_names()}
    layout = _layout(name)
    collection = layout.pageCollection()
    pages = []
    for index in range(collection.pageCount()):
        size = collection.page(index).pageSize()
        pages.append({'page': index + 1, 'width_mm': round(size.width(), 1), 'height_mm': round(size.height(), 1)})
    items = layout_items(layout)
    answer: Dict[str, Any] = {'name': layout.name(), 'pages': pages,
                              'items': [_describe_item(layout, item) for item in items[:MAX_ITEMS_LISTED]]}
    if len(items) > MAX_ITEMS_LISTED:
        answer['items_left_out'] = len(items) - MAX_ITEMS_LISTED
    atlas = layout.atlas() if hasattr(layout, 'atlas') else None
    if atlas is not None and atlas.enabled() and atlas.coverageLayer() is not None:
        driven = [item_ref(item) for item in items if isinstance(item, QgsLayoutItemMap) and item.atlasDriven()]
        answer['atlas'] = {'coverage_layer': atlas.coverageLayer().name(), 'pages': atlas.updateFeatures(),
                           'filter': atlas.filterExpression() if atlas.filterFeatures() else '',
                           'page_name': atlas.pageNameExpression(), 'sort_by': atlas.sortExpression()
                           if atlas.sortFeatures() else '', 'file_name': atlas.filenameExpression(),
                           'maps': driven}
    return answer


def template_names() -> List[str]:
    """The layout templates (.qpt) of the profile and of the folders set in QGIS, by name."""
    names = []
    for path, _ in _templates():
        stem = os.path.splitext(os.path.basename(path))[0]
        if stem not in names:
            names.append(stem)
    return names[:MAX_LISTED]


def _templates() -> List[Any]:
    from qgis.core import QgsApplication
    found = []
    try:
        folders = QgsApplication.layoutTemplatePaths()
    except Exception:  # nosec B110 - no template folder
        folders = []
    for folder in folders:
        try:
            for entry in sorted(os.listdir(folder)):
                if entry.lower().endswith('.qpt') and os.path.isfile(os.path.join(folder, entry)):
                    found.append((os.path.join(folder, entry), folder))
        except OSError:
            continue
    return found


# --- the atlas -----------------------------------------------------------------------------------------------------

def _expression(text: str, what: str) -> str:
    from qgis.core import QgsExpression
    text = str(text or '').strip()
    if not text:
        return ''
    if len(text) > 2000:
        raise ValueError(f"{what} is 2000 characters at most")
    expression = QgsExpression(text)
    if expression.hasParserError():
        raise ValueError(f"{what} is not a valid QGIS expression: {expression.parserErrorString()}")
    return text


def _scaling_mode(mode: str):
    from qgis.core import QgsLayoutItemMap
    modes = getattr(QgsLayoutItemMap, 'AtlasScalingMode', QgsLayoutItemMap)
    return {'auto': modes.Auto, 'fixed': modes.Fixed, 'predefined': modes.Predefined}[mode]


def set_atlas(layout_name: str, coverage_layer: str = '', enabled: bool = True, filter_expression: str = '',
              page_name: str = '', sort_by: str = '', descending: bool = False, hide_coverage: bool = False,
              map_mode: str = 'auto', margin: float = 10.0, file_name: str = '', maps: Optional[List[str]] = None
              ) -> Dict[str, Any]:
    """Turn the atlas of a layout on: one page per feature of ``coverage_layer`` as filtered now, its maps following
    each feature (``auto``: the feature plus ``margin`` %, ``fixed``: the scale they have, ``predefined``: the
    scales of the project). Off with ``enabled`` False.

    Raises:
        ValueError: An unknown layout, layer or map, a layer that is not vector, an expression that does not parse.
    """
    from qgis.core import QgsLayoutItemMap, QgsVectorLayer
    layout = _layout(layout_name)
    if not hasattr(layout, 'atlas'):
        raise ValueError(f"{layout.name()!r} is a report, not a print layout: it has no atlas")
    atlas = layout.atlas()
    all_maps = [item for item in layout_items(layout) if isinstance(item, QgsLayoutItemMap)]
    if not enabled:
        atlas.setEnabled(False)
        for item in all_maps:
            item.setAtlasDriven(False)
        return {'layout': layout.name(), 'atlas': False}
    if map_mode not in ('auto', 'fixed', 'predefined'):
        raise ValueError('map_mode is auto, fixed or predefined')
    if not 0 <= float(margin) <= 500:
        raise ValueError('margin goes from 0 to 500 (%)')
    layer = resolve_layer(coverage_layer) if coverage_layer else atlas.coverageLayer()
    if layer is None:
        raise ValueError(f"layer {coverage_layer!r} not found" if coverage_layer else 'coverage_layer is needed')
    if not isinstance(layer, QgsVectorLayer):
        raise ValueError(f"'{layer.name()}' is not a vector layer: an atlas pages through features")
    if not all_maps:
        raise ValueError(f"the layout {layout.name()!r} has no map")
    if maps:
        chosen = [item for item in all_maps if item_ref(item) in maps or item.id() in maps]
        unknown = set(maps) - {item_ref(item) for item in chosen} - {item.id() for item in chosen}
        if unknown:
            raise ValueError(f"no map {sorted(unknown)} in the layout: describe_layout names them (ref)")
    else:  # the largest map follows the features; a map of situation stays as it is
        chosen = [max(all_maps, key=lambda item: item.rect().width() * item.rect().height())]
    filter_expression = _expression(filter_expression, 'filter')
    page_name = _expression(page_name, 'page_name')
    sort_by = _expression(sort_by, 'sort_by')
    file_name = _expression(file_name, 'file_name')
    atlas.setCoverageLayer(layer)
    atlas.setEnabled(True)
    atlas.setFilterFeatures(bool(filter_expression))
    if filter_expression:
        ok, error = atlas.setFilterExpression(filter_expression)
        if not ok:
            raise ValueError(f"filter: {error}")
    atlas.setPageNameExpression(page_name)
    atlas.setSortFeatures(bool(sort_by))
    atlas.setSortExpression(sort_by)
    atlas.setSortAscending(not descending)
    atlas.setHideCoverage(bool(hide_coverage))
    if file_name:
        ok, error = atlas.setFilenameExpression(file_name)
        if not ok:
            raise ValueError(f"file_name: {error}")
    for item in all_maps:
        item.setAtlasDriven(item in chosen)
    for item in chosen:
        item.setAtlasScalingMode(_scaling_mode(map_mode))
        item.setAtlasMargin(float(margin) / 100.0)
    pages = atlas.updateFeatures()
    answer = {'layout': layout.name(), 'atlas': True, 'coverage_layer': layer.name(), 'pages': pages,
              'maps': [item_ref(item) for item in chosen], 'map_mode': map_mode}
    if layer.subsetString():
        answer['note'] = 'one page per feature the layer keeps as filtered now: a new filter changes the pages'
    if pages > MAX_ATLAS_PAGES:
        answer['note'] = f"{pages} pages: export_layout exports {MAX_ATLAS_PAGES} at most, filter the layer first"
    return answer


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
