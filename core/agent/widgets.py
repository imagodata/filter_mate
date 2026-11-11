# -*- coding: utf-8 -*-
"""Small controls the agent makes for the user: a description, never code.

Plain Python. A widget is a dict, kept as JSON in the project, drawn by FilterMate with widgets it knows:

- ``range``: two bounds on a numeric field; moving them filters the layer;
- ``values``: the values of a field, each ticked or not; ticking filters the layer;
- ``stat``: a number computed on the layer as it is filtered now (count, sum, mean, minimum, maximum);
- ``chart``: bars of the layer as filtered now: the features of each value of a field (the most frequent ones), or
  a histogram of a numeric field.

A widget filters only its own layer. The conditions of the widgets of a layer are joined with AND, after the filter
the layer had when its first widget was made (``base``), so two widgets of one layer narrow it together and the filter
of the user is kept. What a widget writes is built here from the field and values it holds, quoted by the caller's
functions (QGIS's), never from text a model wrote: a model only chooses the kind, the layer, the field and the title.
"""
from __future__ import annotations

import json
import math
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

RANGE, VALUES, STAT, CHART = "range", "values", "stat", "chart"
KINDS = (RANGE, VALUES, STAT, CHART)
# Widgets that show the layer and filter nothing.
SHOWING = (STAT, CHART)
CATEGORIES, HISTOGRAM = "categories", "histogram"
CHART_MODES = (CATEGORIES, HISTOGRAM)
MAX_BARS = 8  # the most frequent values; the others are summed in one bar
HISTOGRAM_BINS = 10
AGGREGATES = ("count", "sum", "mean", "min", "max")
MAX_WIDGETS = 12
MAX_VALUES = 50
MAX_TITLE = 60
NOTHING = "1 = 0"  # every value unticked: the layer shows nothing, as the user asked

Quote = Callable[[Any], str]


class WidgetError(ValueError):
    """Why a widget cannot be made; the message is for the model."""


def _number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def _scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _clean(widget: Any) -> Optional[Dict[str, Any]]:
    """A stored widget as it may be drawn, or None when it cannot be (an older or damaged entry)."""
    if not isinstance(widget, dict):
        return None
    kind = widget.get("kind")
    if kind not in KINDS or not isinstance(widget.get("id"), str) or not isinstance(widget.get("layer_id"), str):
        return None
    out = {
        "id": widget["id"], "kind": kind, "layer_id": widget["layer_id"],
        "layer_name": str(widget.get("layer_name") or ""), "title": str(widget.get("title") or "")[:MAX_TITLE],
        "field": str(widget.get("field") or ""), "base": str(widget.get("base") or ""),
    }
    if kind == RANGE:
        low, high = _number(widget.get("minimum")), _number(widget.get("maximum"))
        if low is None or high is None or low > high or not out["field"]:
            return None
        start, end = _number(widget.get("low")), _number(widget.get("high"))
        start = low if start is None else min(max(start, low), high)
        end = high if end is None else min(max(end, start), high)
        out.update(minimum=low, maximum=high, low=start, high=end,
                   integer=bool(widget.get("integer")))
    elif kind == VALUES:
        values = widget.get("values")
        if not isinstance(values, list) or not values or not out["field"]:
            return None
        values = [value for value in values if _scalar(value)][:MAX_VALUES]
        chosen = widget.get("chosen")
        chosen = list(values) if not isinstance(chosen, list) else [value for value in chosen if value in values]
        out.update(values=values, chosen=chosen)
    elif kind == CHART:
        mode = widget.get("mode")
        if mode not in CHART_MODES or not out["field"]:
            return None
        out.update(mode=mode)
    else:
        aggregate = widget.get("aggregate") or "count"
        if aggregate not in AGGREGATES or (aggregate != "count" and not out["field"]):
            return None
        out.update(aggregate=aggregate)
    return out


def parse(stored: str) -> List[Dict[str, Any]]:
    """The widgets kept in a project; what cannot be read is left out."""
    try:
        value = json.loads(stored) if stored else []
    except (ValueError, RecursionError):
        return []
    if not isinstance(value, list):
        return []
    widgets = [widget for widget in (_clean(item) for item in value[:MAX_WIDGETS]) if widget is not None]
    seen, unique = set(), []
    for widget in widgets:
        if widget["id"] not in seen:
            seen.add(widget["id"])
            unique.append(widget)
    return unique


def dumps(widgets: Sequence[Dict[str, Any]]) -> str:
    return json.dumps(list(widgets), ensure_ascii=False, sort_keys=True)


def new_id(widgets: Sequence[Dict[str, Any]]) -> str:
    taken = {widget["id"] for widget in widgets}
    number = 1
    while f"w{number}" in taken:
        number += 1
    return f"w{number}"


def make(widgets: Sequence[Dict[str, Any]], kind: str, layer_id: str, layer_name: str, base: str, title: str = "",
         field: str = "", aggregate: str = "", minimum: Any = None, maximum: Any = None, integer: bool = False,
         values: Optional[Iterable[Any]] = None, numeric: bool = False) -> Dict[str, Any]:
    """A new widget, checked; the caller read ``minimum``/``maximum`` or ``values`` from the layer.

    Raises:
        WidgetError: With what the model should do instead.
    """
    if len(widgets) >= MAX_WIDGETS:
        raise WidgetError(f"There are already {MAX_WIDGETS} widgets: remove one first (remove_widget).")
    if kind not in KINDS:
        raise WidgetError(f"kind must be one of {', '.join(KINDS)}.")
    same_layer = [widget for widget in widgets if widget["layer_id"] == layer_id and widget["kind"] not in SHOWING]
    if kind not in SHOWING and same_layer:
        base = same_layer[0]["base"]  # the filter the layer had before its first widget
    if kind not in SHOWING and any(widget["field"] == field for widget in same_layer):
        raise WidgetError(f"A widget already filters {field!r} of this layer.")
    entry = {"id": new_id(widgets), "kind": kind, "layer_id": layer_id, "layer_name": layer_name,
             "title": (title or "").strip()[:MAX_TITLE], "field": field, "base": base}
    if kind == RANGE:
        low, high = _number(minimum), _number(maximum)
        if low is None or high is None:
            raise WidgetError(f"{field!r} has no numeric values among the features shown: a range needs numbers.")
        if low == high:
            raise WidgetError(f"Every feature shown has the same value of {field!r} ({low:g}): nothing to choose.")
        entry.update(minimum=low, maximum=high, low=low, high=high, integer=bool(integer))
    elif kind == VALUES:
        found = [value for value in (values or ()) if _scalar(value)]
        if not found:
            raise WidgetError(f"{field!r} has no values among the features shown.")
        if len(found) > MAX_VALUES:
            raise WidgetError(f"{field!r} takes more than {MAX_VALUES} values: use a range widget, or filter first.")
        ordered = sorted(found, key=lambda value: (value is None, type(value).__name__, value if value is not None else 0))
        entry.update(values=ordered, chosen=list(ordered))
    elif kind == CHART:
        if not field:
            raise WidgetError("A chart needs a field: the values it counts, or the numbers of a histogram.")
        entry.update(mode=HISTOGRAM if numeric else CATEGORIES)
    else:
        aggregate = aggregate or "count"
        if aggregate not in AGGREGATES:
            raise WidgetError(f"aggregate must be one of {', '.join(AGGREGATES)}.")
        if aggregate != "count" and not field:
            raise WidgetError(f"{aggregate} needs a numeric field.")
        entry.update(aggregate=aggregate)
    cleaned = _clean(entry)
    if cleaned is None:  # make and _clean say the same thing; a difference is a bug here, not a model mistake
        raise WidgetError("This widget could not be made.")
    return cleaned


def _format_number(value: float, integer: bool) -> str:
    return str(int(round(value))) if integer else repr(float(value))


def condition(widget: Dict[str, Any], quote_field: Quote, quote_value: Quote) -> str:
    """What this widget asks of its layer now; "" when it lets everything through."""
    field = quote_field(widget["field"]) if widget.get("field") else ""
    if widget["kind"] == RANGE:
        parts = []
        if widget["low"] > widget["minimum"]:
            parts.append(f"{field} >= {_format_number(widget['low'], widget.get('integer', False))}")
        if widget["high"] < widget["maximum"]:
            parts.append(f"{field} <= {_format_number(widget['high'], widget.get('integer', False))}")
        return " AND ".join(parts)
    if widget["kind"] == VALUES:
        chosen, values = widget["chosen"], widget["values"]
        if len(chosen) == len(values):
            return ""
        if not chosen:
            return NOTHING
        listed = [value for value in chosen if value is not None]
        parts = [f"{field} IN ({', '.join(quote_value(value) for value in listed)})"] if listed else []
        if None in chosen:
            parts.append(f"{field} IS NULL")
        return parts[0] if len(parts) == 1 else "(" + " OR ".join(parts) + ")"
    return ""


def layer_filter(widgets: Sequence[Dict[str, Any]], layer_id: str, quote_field: Quote, quote_value: Quote) -> str:
    """The filter of a layer from its widgets: its filter from before, AND each condition."""
    mine = [widget for widget in widgets if widget["layer_id"] == layer_id and widget["kind"] not in SHOWING]
    if not mine:
        return ""
    parts = [mine[0]["base"]] if mine[0]["base"] else []
    parts += [part for part in (condition(widget, quote_field, quote_value) for widget in mine) if part]
    if len(parts) <= 1:
        return parts[0] if parts else ""
    return " AND ".join(f"({part})" for part in parts)


def summary(widgets: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The widgets as the model sees them: what they are, not every value they hold."""
    rows = []
    for widget in widgets:
        row = {"widget_id": widget["id"], "kind": widget["kind"], "layer": widget["layer_name"],
               "title": widget["title"]}
        if widget["field"]:
            row["field"] = widget["field"]
        if widget["kind"] == RANGE:
            row.update(low=widget["low"], high=widget["high"])
        elif widget["kind"] == VALUES:
            row.update(values=len(widget["values"]), ticked=len(widget["chosen"]))
        elif widget["kind"] == CHART:
            row["mode"] = widget["mode"]
        else:
            row["aggregate"] = widget["aggregate"]
        rows.append(row)
    return rows


def category_bars(counts: Iterable[Any], total: int, limit: int = MAX_BARS) -> List[Dict[str, Any]]:
    """The bars of a chart of categories: the ``limit`` most frequent values, then one bar for all the others.

    ``counts`` holds ``(value, count)``; ``total`` is the number of features of the layer. Each bar is
    ``{"value", "count", "others"}``; ``others`` is True for the bar of the rest.
    """
    ranked = sorted(((value, count) for value, count in counts), key=lambda item: (-item[1], str(item[0])))
    bars = [{"value": value, "count": count, "others": False} for value, count in ranked[:limit]]
    rest = total - sum(bar["count"] for bar in bars)
    if rest > 0:
        bars.append({"value": None, "count": rest, "others": True})
    return bars


def histogram_bars(values: Iterable[Any], bins: int = HISTOGRAM_BINS) -> List[Dict[str, Any]]:
    """The bars of a histogram: ``bins`` equal intervals of the finite numbers of ``values``, as
    ``{"low", "high", "count"}``."""
    numbers = [float(value) for value in values if _number(value) is not None]
    if not numbers:
        return []
    low, high = min(numbers), max(numbers)
    if low == high:
        return [{"low": low, "high": high, "count": len(numbers)}]
    width = (high - low) / bins
    counts = [0] * bins
    for number in numbers:
        counts[min(int((number - low) / width), bins - 1)] += 1
    return [{"low": low + index * width, "high": low + (index + 1) * width, "count": count}
            for index, count in enumerate(counts)]


def without(widgets: Sequence[Dict[str, Any]], widget_id: str) -> List[Dict[str, Any]]:
    """The widgets less one.

    Raises:
        WidgetError: No widget has this id.
    """
    if not any(widget["id"] == widget_id for widget in widgets):
        known = ", ".join(widget["id"] for widget in widgets) or "none"
        raise WidgetError(f"No widget {widget_id!r} (widgets: {known}).")
    return [widget for widget in widgets if widget["id"] != widget_id]


def replaced(widgets: Sequence[Dict[str, Any]], widget: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The widgets with ``widget`` in place of the one of the same id (its new state)."""
    cleaned = _clean(widget)
    if cleaned is None:
        return list(widgets)
    return [cleaned if item["id"] == cleaned["id"] else item for item in widgets]
