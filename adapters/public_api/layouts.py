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
from typing import Any, Dict, List, Optional, Tuple

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
    if type(layout).__name__ == 'QgsReport':  # a report: no page of its own, no atlas
        raise ValueError(f"{name!r} is a report, not a print layout: these tools read and change print layouts")
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
                  legend: bool = True, scale_bar: bool = True, north_arrow: bool = True,
                  template: str = '') -> Dict[str, Any]:
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
    if template:
        return _create_from_template(name, template, chosen, shown, extent, extent_layer)

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
        _check_text(str(title))
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


def _create_from_template(name: str, template: str, chosen: List[Any], shown: List[Any],
                          extent: Optional[List[float]], extent_layer: str) -> Dict[str, Any]:
    """create_layout from a template: its pages and items as it has them, its largest map framed as asked."""
    from qgis.core import QgsLayoutItemMap, QgsProject
    project = QgsProject.instance()
    layout = _from_template(name, template)
    maps = [item for item in layout_items(layout) if isinstance(item, QgsLayoutItemMap)]
    origin = ''
    scale = None
    if maps:
        main = max(maps, key=lambda item: item.rect().width() * item.rect().height())
        if chosen:
            main.setLayers(chosen)
            main.setKeepLayerSet(True)
        crs = main.crs() if main.crs().isValid() else project.crs()
        rectangle, origin = _extent(extent, extent_layer, shown, crs)
        main.zoomToExtent(rectangle)
        scale = main.scale()
    if not project.layoutManager().addLayout(layout):
        raise ValueError(f"the layout {name!r} could not be added to the project")
    return {'name': name, 'page': '', 'orientation': '', 'items': sorted({_kind(item) for item in layout_items(layout)}),
            'extent_from': origin, 'scale': round(scale) if scale is not None and math.isfinite(scale) else None,
            'layers': [layer.name() for layer in chosen] or 'shown in the layer tree',
            'note': f"Made from the template {template!r}: its texts are as it has them (set_text in edit_layout)."}


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
    # The name of each file, made of the expression of the atlas, never a path: QGIS joins it to the folder, and a
    # name with a / or a .. wrote anywhere on the disk (2026-11-22, review). Put back as it was afterwards: an export
    # changes nothing of the layout.
    original = atlas.filenameExpression()
    named = original or f"'{safe.replace(chr(39), '_')}_' || lpad(@atlas_featurenumber, 3, '0')"
    atlas.setFilenameExpression(
        f"replace(replace(replace(to_string({named}), '/', '_'), '\\\\', '_'), ':', '_')")
    try:
        return _write_atlas(atlas, target, safe, file_format, settings, single_file, count)
    finally:
        atlas.setFilenameExpression(original)


def _write_atlas(atlas, target: str, safe: str, file_format: str, settings, single_file: bool,
                 count: int) -> Dict[str, Any]:
    from qgis.core import QgsLayoutExporter
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
    answer = {'name': atlas.layout().name(), 'format': file_format, 'dpi': int(settings.dpi), 'path': target,
              'bytes': sum(os.path.getsize(item) for item in files), 'files': len(files), 'pages': count,
              'atlas': True}
    if not (file_format == 'pdf' and single_file) and len(files) < count:
        answer['note'] = 'pages of the same file name replaced each other: a file_name that differs per feature'
    return answer


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
    # Where the designer of QGIS looks: the profile, the folders set in the options, then those QGIS ships.
    folders = [os.path.join(QgsApplication.qgisSettingsDirPath(), 'composer_templates')]
    try:
        folders += list(QgsApplication.layoutTemplatePaths())
    except Exception:  # nosec B110 - no folder set in the options
        pass
    folders.append(os.path.join(QgsApplication.pkgDataPath(), 'composer_templates'))
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
    from ...core.agent.sql_guard import layout_expression_problem
    # 2026-11-22 (review): an atlas filter can read the environment (env()) and give it back as a count of pages.
    problem = layout_expression_problem(text)
    if problem:
        raise ValueError(f"{what}: {problem}")
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
    if isinstance(maps, str):
        maps = [maps]
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


# --- editing a layout -------------------------------------------------------------------------------------------

EDITS = ('add_text', 'add_map', 'add_legend', 'add_scale_bar', 'add_north_arrow', 'add_table', 'add_shape',
         'add_page', 'move', 'remove', 'set_text', 'set_map')
MAX_EDITS = 20
MAX_TEXT = 2000
MAX_TABLE_ROWS = 500


def _number(change: Dict[str, Any], key: str, low: float, high: float) -> Optional[float]:
    value = change.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{key} is a number")
    if not low <= value <= high:
        raise ValueError(f"{key} goes from {low:g} to {high:g}")
    return float(value)


def _item_by_ref(layout, ref: str):
    ref = str(ref or '')
    for item in layout_items(layout):
        if ref and (item.id() == ref or item_ref(item) == ref):
            return item
    raise ValueError(f"no item {ref!r} in the layout: describe_layout names them (ref)")


def _map_of(layout, ref: str = ''):
    from qgis.core import QgsLayoutItemMap
    if ref:
        item = _item_by_ref(layout, ref)
        if not isinstance(item, QgsLayoutItemMap):
            raise ValueError(f"{ref!r} is not a map")
        return item
    maps = [item for item in layout_items(layout) if isinstance(item, QgsLayoutItemMap)]
    if not maps:
        raise ValueError('the layout has no map: add_map first')
    return max(maps, key=lambda item: item.rect().width() * item.rect().height())


def _place(layout, item, change: Dict[str, Any], default: Tuple[float, float, float, float]) -> None:
    """Put ``item`` where ``change`` says (mm from the top left of its page), ``default`` for what it leaves out."""
    from qgis.core import QgsLayoutPoint, QgsLayoutSize
    pages = layout.pageCollection().pageCount()
    page = int(_number(change, 'page', 1, max(1, pages)) or 1)
    x = _number(change, 'x', 0, 5000)
    y = _number(change, 'y', 0, 5000)
    width = _number(change, 'width', 1, 5000)
    height = _number(change, 'height', 1, 5000)
    left, top, wide, high = default
    item.attemptResize(QgsLayoutSize(width if width is not None else wide, height if height is not None else high, _mm()))
    item.attemptMove(QgsLayoutPoint(x if x is not None else left, y if y is not None else top, _mm()), page=page - 1)


def _font(label, size: Optional[float]) -> None:
    if size is None:
        return
    if hasattr(label, 'setTextFormat'):
        text_format = label.textFormat()
        text_format.setSize(size)
        label.setTextFormat(text_format)
    else:
        font = label.font()
        font.setPointSizeF(size)
        label.setFont(font)


def _text_of(change: Dict[str, Any]) -> str:
    text = change.get('text')
    if not isinstance(text, str) or not text.strip():
        raise ValueError('text is needed')
    if len(text) > MAX_TEXT:
        raise ValueError(f"text is {MAX_TEXT} characters at most")
    _check_text(text)
    return text


def _check_text(text: str) -> None:
    """A text of a layout evaluates its [% ... %] at each drawing: the same expressions as an atlas, no more."""
    from ...core.agent.sql_guard import text_expressions_problem
    problem = text_expressions_problem(text)
    if problem:
        raise ValueError(f"text: {problem}")


def _layers_of(change: Dict[str, Any]) -> List[Any]:
    chosen = []
    for reference in change.get('layers') or []:
        layer = resolve_layer(reference)
        if layer is None:
            raise ValueError(f"layer {reference!r} not found")
        chosen.append(layer)
    return chosen


def _set_map(layout, item, change: Dict[str, Any]) -> None:
    layers = _layers_of(change)
    if layers:
        item.setLayers(layers)
        item.setKeepLayerSet(True)
    if change.get('extent_layer'):
        layer = resolve_layer(change['extent_layer'])
        if layer is None:
            raise ValueError(f"layer {change['extent_layer']!r} not found")
        rectangle, _ = _extent(None, change['extent_layer'], [layer], item.crs())
        item.zoomToExtent(rectangle)
    scale = _number(change, 'scale', 1, 1e9)
    if scale is not None:
        item.setScale(scale)


def _sheet_size(layout) -> Tuple[float, float]:
    """The size of the first page, in the units of the layout (millimetres by default)."""
    size = layout.convertToLayoutUnits(layout.pageCollection().page(0).pageSize())
    return size.width(), size.height()


def _edit(layout, change: Dict[str, Any]) -> Dict[str, Any]:
    from qgis.core import (QgsLayoutFrame, QgsLayoutItemAttributeTable, QgsLayoutItemLabel, QgsLayoutItemLegend,
                           QgsLayoutItemMap, QgsLayoutItemMapOverview, QgsLayoutItemPage, QgsLayoutItemPicture,
                           QgsLayoutItemScaleBar, QgsLayoutItemShape, QgsLayoutSize, QgsVectorLayer)
    do = change.get('do')
    if do not in EDITS:
        raise ValueError(f"do is one of {', '.join(EDITS)}")
    width, height = _sheet_size(layout)
    if do in ('move', 'remove', 'set_text'):
        item = _item_by_ref(layout, change.get('ref'))
        ref = item_ref(item)
        if do == 'remove':
            if isinstance(item, QgsLayoutFrame) and item.multiFrame() is not None:
                # Its frames first: removeMultiFrame alone left the table drawn (2026-11-22, review).
                multi = item.multiFrame()
                for frame in list(multi.frames()):
                    layout.removeLayoutItem(frame)
                layout.removeMultiFrame(multi)
            else:
                layout.removeLayoutItem(item)
            return {'do': do, 'ref': ref}
        if do == 'set_text':
            if not isinstance(item, QgsLayoutItemLabel):
                raise ValueError(f"{ref!r} is not a text")
            item.setText(_text_of(change))
            _font(item, _number(change, 'font_size', 4, 200))
            item.refresh()
            return {'do': do, 'ref': ref}
        position = layout.convertToLayoutUnits(item.pagePositionWithUnits())
        size = layout.convertToLayoutUnits(item.sizeWithUnits())
        _place(layout, item, dict(change, page=change.get('page') or item.page() + 1),
               (position.x(), position.y(), size.width(), size.height()))
        return {'do': do, 'ref': ref}
    if do == 'set_map':
        item = _map_of(layout, change.get('ref') or '')
        _set_map(layout, item, change)
        return {'do': do, 'ref': item_ref(item), 'scale': round(item.scale()) if math.isfinite(item.scale()) else None}
    if do == 'add_page':
        page = QgsLayoutItemPage(layout)
        page.setPageSize(QgsLayoutSize(width, height, _mm()))
        layout.pageCollection().addPage(page)
        return {'do': do, 'page': layout.pageCollection().pageCount()}
    if do == 'add_text':
        item = QgsLayoutItemLabel(layout)
        item.setText(_text_of(change))
        _font(item, _number(change, 'font_size', 4, 200) or 12)
        layout.addLayoutItem(item)
        _place(layout, item, change, (MARGIN, MARGIN, width - 2 * MARGIN, 10))
    elif do == 'add_map':
        item = QgsLayoutItemMap(layout)
        project_crs = layout.project().crs()
        item.setCrs(project_crs)
        item.setFrameEnabled(True)
        layout.addLayoutItem(item)
        _place(layout, item, change, (width - MARGIN - 70, MARGIN + 20, 70, 50))
        overview_of = change.get('overview_of')
        if overview_of:
            target = _map_of(layout, overview_of)
            item.setLayers(target.layers())
            if change.get('layers') or change.get('extent_layer'):
                _set_map(layout, item, change)
            else:
                item.zoomToExtent(target.extent().buffered(max(target.extent().width(), target.extent().height())
                                                           * 2.0))
            overview = QgsLayoutItemMapOverview('FilterMate overview', item)
            overview.setLinkedMap(target)
            item.overviews().addOverview(overview)
        else:
            if not change.get('extent_layer'):
                raise ValueError('add_map needs extent_layer, or overview_of a map')
            _set_map(layout, item, change)
    elif do in ('add_legend', 'add_scale_bar', 'add_north_arrow'):
        target = _map_of(layout, change.get('map') or '')
        if do == 'add_legend':
            item = QgsLayoutItemLegend(layout)
            item.setTitle('')
            item.setBackgroundEnabled(True)
            item.setLinkedMap(target)
            default = (width - MARGIN - 50, MARGIN + 20, 50, 40)
        elif do == 'add_scale_bar':
            item = QgsLayoutItemScaleBar(layout)
            item.setLinkedMap(target)
            item.applyDefaultSize()
            item.setBackgroundEnabled(True)
            default = (MARGIN + 3, height - MARGIN - 18, 60, 12)
        else:
            item = QgsLayoutItemPicture(layout)
            item.setPicturePath(NORTH_ARROW)
            item.setLinkedMap(target)
            default = (MARGIN + 3, MARGIN + 20, 12, 12)
        layout.addLayoutItem(item)
        _place(layout, item, change, default)
        if do == 'add_legend':
            item.adjustBoxSize()
    elif do == 'add_shape':
        item = QgsLayoutItemShape(layout)
        shapes = getattr(QgsLayoutItemShape, 'Shape', QgsLayoutItemShape)
        item.setShapeType(shapes.Rectangle)
        layout.addLayoutItem(item)
        _place(layout, item, change, (MARGIN, MARGIN, 50, 30))
    else:  # add_table
        layer = resolve_layer(change.get('layer') or '')
        if not isinstance(layer, QgsVectorLayer):
            raise ValueError(f"layer {change.get('layer')!r} is not a vector layer of the project")
        table = QgsLayoutItemAttributeTable.create(layout) if hasattr(QgsLayoutItemAttributeTable, 'create') \
            else QgsLayoutItemAttributeTable(layout)
        table.setVectorLayer(layer)
        columns = change.get('columns') or []
        if isinstance(columns, str):  # one field given alone: never its letters
            columns = [columns]
        missing = [name for name in columns if layer.fields().lookupField(name) < 0]
        if missing:
            raise ValueError(f"no field {missing} in '{layer.name()}': see describe_layer")
        if columns:
            table.setDisplayedFields(list(columns))
        table.setMaximumNumberOfFeatures(int(_number(change, 'max_rows', 1, MAX_TABLE_ROWS) or 30))
        atlas = layout.atlas() if hasattr(layout, 'atlas') else None
        if atlas is not None and atlas.enabled() and atlas.coverageLayer() is not None \
                and atlas.coverageLayer().id() == layer.id():
            table.setFilterToAtlasFeature(True)  # the rows of the feature of each page
        layout.addMultiFrame(table)
        frame = QgsLayoutFrame(layout, table)
        table.addFrame(frame)
        _place(layout, frame, change, (MARGIN, height - MARGIN - 50, width / 2 - MARGIN, 50))
        table.refresh()
        return {'do': do, 'ref': item_ref(frame), 'layer': layer.name()}
    return {'do': do, 'ref': item_ref(item)}


def edit_layout(layout_name: str, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Change a layout item by item: add a text, a map (``overview_of`` another one: a map of situation), a legend,
    a scale bar, a north arrow, an attribute table, a frame or a page; move, remove; set a text or a map. In
    millimetres from the top left of a page. All or nothing: a change refused puts the layout back as it was.

    Raises:
        ValueError: An unknown layout, change, item or layer, a value out of range.
    """
    from qgis.core import QgsProject
    layout = _layout(layout_name)
    if not isinstance(changes, list) or not changes:
        raise ValueError('changes is a list of 1 to 20 changes')
    if len(changes) > MAX_EDITS:
        raise ValueError(f"{MAX_EDITS} changes at most in one call")
    before = layout_xml(layout)
    done = []
    try:
        for index, change in enumerate(changes, 1):
            if not isinstance(change, dict):
                raise ValueError('each change is an object')
            try:
                done.append(_edit(layout, change))
            except ValueError as exc:
                raise ValueError(f"change {index} ({change.get('do')}): {exc}") from None
    except Exception:
        # Put back only when something changed: a change refused before any other left the layout as it was, and
        # its designer stays open.
        if layout_xml(layout) != before:
            manager = QgsProject.instance().layoutManager()
            manager.removeLayout(layout)
            if not layout_from_xml(before):
                raise ValueError(f"the layout {layout_name!r} could not be put back as it was: undo the turn") from None
        raise
    layout.refresh()
    return {'layout': layout.name(), 'done': done, 'items': len(layout_items(layout)),
            'pages': layout.pageCollection().pageCount()}


def _from_template(name: str, template: str):
    """A layout of the project made from the template ``template`` of the profile (``template_names``)."""
    from qgis.core import QgsPrintLayout, QgsProject, QgsReadWriteContext
    from qgis.PyQt.QtXml import QDomDocument
    paths = [path for path, _ in _templates() if os.path.splitext(os.path.basename(path))[0] == template]
    if not paths:
        names = template_names()
        raise ValueError(f"no template {template!r}" + (f": {', '.join(names)}" if names else
                                                        ": the profile has none"))
    with open(paths[0], encoding='utf-8') as handle:
        text = handle.read()
    document = QDomDocument()
    if not document.setContent(text):
        raise ValueError(f"the template {template!r} could not be read")
    layout = QgsPrintLayout(QgsProject.instance())
    _, ok = layout.loadFromTemplate(document, QgsReadWriteContext())
    if not ok:
        raise ValueError(f"the template {template!r} could not be loaded")
    layout.setName(name)
    return layout


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
