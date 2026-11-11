# -*- coding: utf-8 -*-
"""The widgets of the agent in QGIS: kept in the project file, read from the layers, applied as filters."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

from qgis.core import QgsExpression, QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import QCoreApplication

from ...core.agent.widgets import (
    CATEGORIES, CHART, MAX_VALUES, RANGE, SHOWING, STAT, VALUES, WidgetError, category_bars, dumps, histogram_bars,
    layer_filter, make, parse,
)

logger = logging.getLogger("FilterMate.agent")

SCOPE = "FilterMateAgent"
KEY = "widgets"
SOURCE = "FilterMate widget"


def _tr(text: str) -> str:
    return QCoreApplication.translate("AgentWidgets", text)


def read_widgets(project=None) -> List[Dict[str, Any]]:
    project = project or QgsProject.instance()
    stored, _found = project.readEntry(SCOPE, KEY, "")
    return parse(stored)


def write_widgets(widgets: Sequence[Dict[str, Any]], project=None) -> None:
    """Keep ``widgets`` in the project, saved with it."""
    project = project or QgsProject.instance()
    if list(widgets) == read_widgets(project):
        return
    if widgets:
        project.writeEntry(SCOPE, KEY, dumps(widgets))
    else:
        project.removeEntry(SCOPE, KEY)


def quote_field(name: str) -> str:
    return QgsExpression.quotedColumnRef(name)


def quote_value(value: Any) -> str:
    return QgsExpression.quotedValue(value)


def widget_layer(widget: Dict[str, Any]) -> Optional[QgsVectorLayer]:
    layer = QgsProject.instance().mapLayer(widget.get("layer_id", ""))
    return layer if isinstance(layer, QgsVectorLayer) and layer.isValid() else None


def _plain(value: Any) -> Any:
    """A QGIS value as plain JSON; None for NULL."""
    if value is None:
        return None
    is_null = getattr(value, "isNull", None)
    if callable(is_null) and is_null():
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def _vector(reference: str) -> QgsVectorLayer:
    from ..public_api.introspection import _vector_layer, _refuse_web_service
    try:
        layer = _vector_layer(reference)
    except ValueError as exc:
        raise WidgetError(str(exc)) from None
    if layer is None:
        raise WidgetError(f"No vector layer {reference!r} in the project: see list_layers.")
    try:
        _refuse_web_service(layer)
    except ValueError as exc:
        raise WidgetError(str(exc)) from None
    return layer


def create(kind: str, layer: str, field: str = "", title: str = "", aggregate: str = "") -> Dict[str, Any]:
    """A widget read from the layer as it shows now, added to the project; what the model is told of it.

    Raises:
        WidgetError: With what the model should do instead.
    """
    target = _vector(layer)
    index = target.fields().lookupField(field) if field else -1
    if field and index < 0:
        raise WidgetError(f"No field {field!r} in {target.name()!r}: see describe_layer.")
    if kind in (RANGE, VALUES) and index < 0:
        raise WidgetError(f"A {kind} widget needs a field.")
    definition = target.fields().at(index) if index >= 0 else None
    if definition is not None and kind in (RANGE, STAT) and (kind == RANGE or aggregate not in ("", "count")) \
            and not definition.isNumeric():
        raise WidgetError(f"{field!r} is not numeric: use a values widget, or count.")
    widgets = read_widgets()
    options: Dict[str, Any] = {}
    if kind == RANGE:
        low, high = _plain(target.minimumValue(index)), _plain(target.maximumValue(index))
        # Whole numbers come back as int from an integer field, whatever the provider calls its type.
        options = dict(minimum=low, maximum=high, integer=isinstance(low, int) and isinstance(high, int))
    elif kind == VALUES:
        options = dict(values=[_plain(value) for value in target.uniqueValues(index, MAX_VALUES + 1)])
    elif kind == CHART:
        options = dict(numeric=definition is not None and definition.isNumeric())
    widget = make(widgets, kind, target.id(), target.name(), target.subsetString() or "", title=title,
                  field=definition.name() if definition is not None else "", aggregate=aggregate, **options)
    write_widgets(widgets + [widget])
    return widget


def apply_layer(widgets: Sequence[Dict[str, Any]], layer_id: str, public_api=None) -> str:
    """Filter a layer as its widgets say; "" when done, else why not (for the user)."""
    layer = QgsProject.instance().mapLayer(layer_id)
    if not isinstance(layer, QgsVectorLayer):
        return _tr("The layer of this widget is no longer in the project.")
    expression = layer_filter(widgets, layer_id, quote_field, quote_value)
    if not any(widget["layer_id"] == layer_id and widget["kind"] not in SHOWING for widget in widgets):
        return ""
    if expression == (layer.subsetString() or ""):
        return ""
    if layer.isEditable():
        return _tr("The layer is being edited: save or discard its edits to filter it.")
    named = QgsProject.instance().mapLayersByName(layer.name())
    try:
        if public_api is not None and len(named) == 1:
            done = public_api.apply_filter(layer.name(), expression, SOURCE)
        else:
            done = layer.setSubsetString(expression)
    except Exception:  # the widget says it failed; the details go to the log
        logger.exception("Widget filter failed on %s", layer.name())
        done = False
    return "" if done else _tr("The filter of this widget was refused by the layer.")


def stat_value(widget: Dict[str, Any]) -> Optional[float]:
    """The number of a stat widget on its layer as filtered now; None when it cannot be computed."""
    layer = widget_layer(widget)
    if layer is None:
        return None
    if widget.get("aggregate") == "count":
        count = layer.featureCount()
        return float(count) if isinstance(count, int) and count >= 0 else None
    from ..public_api.introspection import layer_statistics
    try:
        answer = layer_statistics(layer.id(), widget["field"])
    except (ValueError, RuntimeError):
        return None
    statistics = (answer or {}).get("statistics") or {}
    value = statistics.get({"min": "minimum", "max": "maximum"}.get(widget["aggregate"], widget["aggregate"]))
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def chart_bars(widget: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """The bars of a chart widget on its layer as filtered now; None when they cannot be read (layer gone, field
    gone, a web service, too many features)."""
    from qgis.core import QgsFeatureRequest
    from ..public_api.introspection import MAX_STAT_FEATURES, _refuse_web_service
    layer = widget_layer(widget)
    if layer is None:
        return None
    index = layer.fields().lookupField(widget.get("field", ""))
    if index < 0:
        return None
    try:
        _refuse_web_service(layer)
    except ValueError:
        return None
    count = layer.featureCount()
    if not isinstance(count, int) or count > MAX_STAT_FEATURES:
        return None
    request = QgsFeatureRequest().setFlags(QgsFeatureRequest.Flag.NoGeometry).setSubsetOfAttributes([index])
    values = [_plain(feature.attribute(index)) for feature in layer.getFeatures(request)]
    if widget["mode"] == CATEGORIES:
        counts: Dict[Any, int] = {}
        for value in values:
            key = value if isinstance(value, (str, int, float, bool)) or value is None else str(value)
            counts[key] = counts.get(key, 0) + 1
        return category_bars(counts.items(), total=len(values))
    return histogram_bars(values)
