# -*- coding: utf-8 -*-
"""The data of a chart read from its layer as filtered now, and the charts of the print layouts.

Main thread only, plain values out. A chart put in a print layout is a picture item holding the SVG itself (embedded,
``base64:``: the project carries it, no file beside it), and the request that drew it as a custom property: FilterMate
draws it again from its layer when the filter of that layer changes (``ChartLayoutSync`` in
``ui/controllers/agent_charts.py``). Opened without FilterMate, the layout shows the last drawing.
"""
from __future__ import annotations

import base64
import json
import logging
from typing import Any, Dict, Iterator, List, Optional, Tuple

from ...core.agent.charts import (
    BAR, HISTOGRAM, LINE, PIE, ChartError, ChartRequest, category_values, histogram_values, line_values,
    scatter_values,
)

logger = logging.getLogger("FilterMate.agent")

PROPERTY = "filtermate/chart"  # on a picture item of a layout: the arguments of show_chart that drew it
ITEM_PREFIX = "FilterMate chart"
DEFAULT_WIDTH_MM = 110.0
MARGIN_MM = 10.0
MAX_ITEM_MM = 2000.0


def _value(value: Any) -> Any:
    """A value of QGIS as plain Python: None for NULL, dates as ISO text."""
    if value is None:
        return None
    is_null = getattr(value, "isNull", None)
    if callable(is_null) and is_null():
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    for name in ("toPyDateTime", "toPyDate"):
        convert = getattr(value, name, None)
        if callable(convert):
            try:
                return convert().isoformat()
            except (TypeError, ValueError):
                return None
    return str(value)


def _layer(reference: str):
    from .introspection import _refuse_web_service, _vector_layer
    try:
        layer = _vector_layer(reference)
    except ValueError as exc:
        raise ChartError(str(exc)) from None
    if layer is None:
        raise ChartError(f"no vector layer {reference!r} in the project: see list_layers")
    try:
        _refuse_web_service(layer)
    except ValueError as exc:
        raise ChartError(str(exc)) from None
    return layer


def _index(layer, name: str, numeric: bool = False) -> int:
    if not name:
        return -1
    index = layer.fields().lookupField(name)
    if index < 0:
        raise ChartError(f"no field {name!r} in '{layer.name()}': see describe_layer")
    if numeric and not layer.fields().at(index).isNumeric():
        raise ChartError(f"'{name}' of '{layer.name()}' is not numeric")
    return index


def _is_time(layer, index: int) -> bool:
    if index < 0:
        return False
    try:
        field = layer.fields().at(index)
        return field.isDateOrTime()
    except AttributeError:
        return field.typeName().lower().startswith(("date", "time"))


def _rows(layer, indexes: List[int]) -> Iterator[Tuple[Any, ...]]:
    from qgis.core import QgsFeatureRequest
    from .introspection import MAX_STAT_FEATURES
    from ..qgis.feature_count import features_to_read
    count = features_to_read(layer)
    if isinstance(count, int) and count > MAX_STAT_FEATURES:
        raise ChartError(f"'{layer.name()}' shows {count} features: filter it below {MAX_STAT_FEATURES} first")
    wanted = sorted({index for index in indexes if index >= 0})
    request = QgsFeatureRequest().setFlags(QgsFeatureRequest.Flag.NoGeometry).setSubsetOfAttributes(wanted) \
        .setLimit(MAX_STAT_FEATURES + 1)
    read = 0
    for feature in layer.getFeatures(request):
        read += 1
        if read > MAX_STAT_FEATURES:
            raise ChartError(f"'{layer.name()}' shows too many features: filter it first")
        yield tuple(_value(feature.attribute(index)) if index >= 0 else None for index in indexes)


def read_data(request: ChartRequest, others: str, empty: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """The data of ``request`` from its layer as filtered now, shaped for its template; and what to say of it."""
    layer = _layer(request.layer)
    kind = request.kind
    meta: Dict[str, Any] = {"layer_id": layer.id(), "layer_name": layer.name()}
    if kind in (BAR, PIE):
        category = _index(layer, request.field)
        value = _index(layer, request.value_field, numeric=True) if request.aggregate != "count" else -1
        rows = list(_rows(layer, [category, value]))
        data = category_values(rows, request.aggregate, request.limit, request.sort, others, empty)
        meta.update(features=len(rows), points=len(data))
    elif kind == HISTOGRAM:
        number = _index(layer, request.field, numeric=True)
        values = [row[0] for row in _rows(layer, [number])]
        data = histogram_values(values, request.bins)
        meta.update(features=len(values), points=len(data))
    elif kind == LINE:
        x_index = _index(layer, request.field)
        x_type = request.x_type or ("time" if _is_time(layer, x_index) else "number")
        if x_type == "number" and not layer.fields().at(x_index).isNumeric():
            raise ChartError(f"'{request.field}' is neither a number nor a date: a bar chart for categories")
        y_index = _index(layer, request.value_field, numeric=True)
        series = _index(layer, request.series_field)
        rows = list(_rows(layer, [x_index, y_index, series]))
        triples = [(x, y, (empty if s is None else s) if series >= 0 else None) for x, y, s in rows]
        aggregate = request.aggregate if request.value_field or request.aggregate == "count" else "count"
        data, dropped = line_values(triples, aggregate, x_type, empty, others)
        meta.update(features=len(rows), points=len(data), x_type=x_type, dropped=dropped)
    else:
        x_index = _index(layer, request.field, numeric=True)
        y_index = _index(layer, request.value_field, numeric=True)
        series = _index(layer, request.series_field)
        rows = list(_rows(layer, [x_index, y_index, series]))
        triples = [(x, y, (empty if s is None else s) if series >= 0 else None) for x, y, s in rows]
        data, total = scatter_values(triples, others, empty)
        meta.update(features=len(rows), points=total, dropped=total > len(data))
    if not data:
        raise ChartError(f"'{layer.name()}' as filtered now gives nothing to draw for this chart")
    return data, meta


# --- print layouts ----------------------------------------------------------------------------------------------

def _layout(name: str):
    from qgis.core import QgsProject
    layout = QgsProject.instance().layoutManager().layoutByName(str(name or ""))
    if layout is None:
        from .layouts import layout_names
        names = layout_names()
        raise ChartError(f"no print layout {name!r} in the project"
                         + (f": {', '.join(names)}" if names else ": create_layout makes one"))
    return layout


def _embedded(svg: str) -> str:
    return "base64:" + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def _svg_format():
    from qgis.core import QgsLayoutItemPicture
    return getattr(QgsLayoutItemPicture, "FormatSVG", None) or QgsLayoutItemPicture.Format.FormatSVG


def _mm():
    from qgis.core import QgsUnitTypes
    return getattr(QgsUnitTypes, "LayoutMillimeters", None) or QgsUnitTypes.LayoutUnit.LayoutMillimeters


def add_to_layout(layout_name: str, svg: str, arguments: Dict[str, Any], aspect: float,
                  x: Optional[float] = None, y: Optional[float] = None,
                  width: Optional[float] = None) -> Dict[str, Any]:
    """Put the chart ``svg`` in the layout ``layout_name`` as a picture, in millimetres from the top left of its first
    page (default: at its bottom right). ``aspect`` is height / width of the chart."""
    from qgis.core import QgsLayoutItemPicture, QgsLayoutPoint, QgsLayoutSize
    layout = _layout(layout_name)
    page = layout.pageCollection().page(0)
    if page is None:
        raise ChartError(f"the layout {layout_name!r} has no page")
    page_size = page.pageSize()
    page_width, page_height = page_size.width(), page_size.height()
    for key, value in (("x", x), ("y", y), ("width", width)):
        if value is not None and not 0 <= value <= MAX_ITEM_MM:
            raise ChartError(f"{key} is from 0 to {MAX_ITEM_MM:g} mm")
    item_width = width or min(DEFAULT_WIDTH_MM, page_width - 2 * MARGIN_MM)
    item_height = item_width * aspect
    if item_height > page_height - 2 * MARGIN_MM and width is None:
        item_height = page_height - 2 * MARGIN_MM
        item_width = item_height / aspect
    left = x if x is not None else max(0.0, page_width - MARGIN_MM - item_width)
    top = y if y is not None else max(0.0, page_height - MARGIN_MM - item_height)
    item = QgsLayoutItemPicture(layout)
    title = arguments.get("title") or arguments.get("kind", "")
    item.setId(f"{ITEM_PREFIX}: {title}"[:100])
    item.setPicturePath(_embedded(svg), _svg_format())
    item.setResizeMode(QgsLayoutItemPicture.ResizeMode.Zoom if hasattr(QgsLayoutItemPicture, "ResizeMode")
                       else QgsLayoutItemPicture.Zoom)
    item.setCustomProperty(PROPERTY, json.dumps(arguments, ensure_ascii=False))
    layout.addLayoutItem(item)
    item.attemptMove(QgsLayoutPoint(left, top, _mm()))
    item.attemptResize(QgsLayoutSize(item_width, item_height, _mm()))
    return {"layout": layout.name(), "item": item.id(), "uuid": item.uuid(),
            "x_mm": round(left, 1), "y_mm": round(top, 1), "width_mm": round(item_width, 1),
            "height_mm": round(item_height, 1)}


def chart_items(layer_id: str = "") -> Iterator[Tuple[Any, Dict[str, Any]]]:
    """``(item, arguments)`` of the charts of every print layout of the project; of one layer when ``layer_id``."""
    from qgis.core import QgsLayoutItemPicture, QgsProject
    project = QgsProject.instance()
    for layout in project.layoutManager().printLayouts():
        for item in layout.items():
            if not isinstance(item, QgsLayoutItemPicture):
                continue
            text = item.customProperty(PROPERTY)
            if not text:
                continue
            try:
                arguments = json.loads(str(text))
            except ValueError:
                continue
            if not isinstance(arguments, dict):
                continue
            if layer_id:
                layer = project.mapLayer(layer_id)
                reference = arguments.get("layer") or ""
                if layer is None or reference not in (layer.id(), layer.name()):
                    continue
            yield item, arguments


def set_chart_svg(item, svg: str) -> None:
    """Show a new drawing of the chart in its item."""
    item.setPicturePath(_embedded(svg), _svg_format())
    item.refresh()


def item_xml(item) -> str:
    """The item as XML, to bring it back after an undo of the turn is redone."""
    from qgis.core import QgsReadWriteContext
    from qgis.PyQt.QtXml import QDomDocument
    document = QDomDocument()
    holder = document.createElement("Holder")
    document.appendChild(holder)
    item.writeXml(holder, document, QgsReadWriteContext())
    return document.toString()


def remove_item(layout_name: str, uuid: str) -> bool:
    from qgis.core import QgsProject
    layout = QgsProject.instance().layoutManager().layoutByName(layout_name)
    item = layout.itemByUuid(uuid) if layout is not None else None
    if item is None:
        return False
    layout.removeLayoutItem(item)
    return True


def restore_item(layout_name: str, xml: str) -> bool:
    """Add back an item ``item_xml`` kept; False when its layout is gone or the XML cannot be read."""
    from qgis.core import QgsLayoutItemPicture, QgsProject, QgsReadWriteContext
    from qgis.PyQt.QtXml import QDomDocument
    layout = QgsProject.instance().layoutManager().layoutByName(layout_name)
    document = QDomDocument()
    if layout is None or not document.setContent(xml):
        return False
    element = document.documentElement().firstChildElement("LayoutItem")
    if element.isNull():
        return False
    item = QgsLayoutItemPicture(layout)
    if not item.readXml(element, document, QgsReadWriteContext()):
        return False
    layout.addLayoutItem(item)
    item.finalizeRestoreFromXml()
    return True


def layout_chart_uuids() -> Dict[str, set]:
    """``{layout name: uuids of its chart items}``: what the turn had before a chart was put in a layout."""
    found: Dict[str, set] = {}
    for item, _ in chart_items():
        found.setdefault(item.layout().name(), set()).add(item.uuid())
    return found


def find_item(layout_name: str, uuid: str):
    from qgis.core import QgsProject
    layout = QgsProject.instance().layoutManager().layoutByName(layout_name)
    return layout.itemByUuid(uuid) if layout is not None else None


def layer_ids_of_charts() -> List[str]:
    """The layers whose charts are in layouts, by id (a reference by name resolved now)."""
    from qgis.core import QgsProject
    project = QgsProject.instance()
    ids = []
    for _, arguments in chart_items():
        reference = arguments.get("layer") or ""
        if not reference:
            continue
        layer = project.mapLayer(reference)
        if layer is None:
            named = project.mapLayersByName(reference)
            layer = named[0] if named else None
        if layer is not None and layer.id() not in ids:
            ids.append(layer.id())
    return ids
