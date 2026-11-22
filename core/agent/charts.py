# -*- coding: utf-8 -*-
"""Charts of the agent drawn with d3: what a request asks, its data shaped for a template, and the page that draws it.

Plain Python. ``show_chart`` asks for a chart in data (a kind, a layer and its fields, or rows the agent gives); the
templates of ``resources/charts/fm_charts.js`` draw it in a page of QtWebEngine FilterMate keeps hidden
(``adapters/agent/chart_renderer.py``), which hands back an SVG: shown in the chat, written as PNG, JPG or SVG, put in a
print layout and drawn again there when the filter of its layer changes (``adapters/public_api/charts.py``).

In the expert mode alone, the agent may write the d3 code itself: it runs in the same page, which reaches no network
and no file (a Content-Security-Policy, and the renderer refuses every request that is not the page itself).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .widgets import histogram_bars

CHARTS_DIR = Path(__file__).resolve().parents[2] / "resources" / "charts"
D3_FILE = "d3.v7.min.js"
TEMPLATES_FILE = "fm_charts.js"

BAR, HISTOGRAM, PIE, LINE, SCATTER = "bar", "histogram", "pie", "line", "scatter"
KINDS = (BAR, HISTOGRAM, PIE, LINE, SCATTER)
AGGREGATES = ("count", "sum", "mean", "min", "max")
SORTS = ("value", "label")
X_TYPES = ("number", "time")
FORMATS = ("png", "jpg", "svg")

DEFAULT_SIZE = (640, 400)
MIN_SIZE, MAX_SIZE = (280, 200), (1600, 1200)
DEFAULT_LIMIT = {BAR: 10, PIE: 6}
MAX_LIMIT = 30
DEFAULT_BINS, MAX_BINS = 12, 50
MAX_ROWS = 500  # rows the agent gives
MAX_SERIES = {LINE: 8, SCATTER: 3}  # the categorical hues that stay apart (all pairs for a scatter): past, "others"
MAX_POINTS = 5000  # dots of a scatter; a layer of more is sampled, evenly
MAX_LINE_POINTS = 2000
MAX_CODE = 20000
MAX_TITLE, MAX_LABEL = 80, 60
MAX_PAGE_DATA = 1_000_000  # characters of data in the page: QtWebEngine loads 2 MB of HTML at most
MAX_KEPT = 30  # charts of a conversation the agent may export or put in a layout by their id

# The reference palette (8 hues in a fixed order, validated for colour vision deficiencies in both modes), text in ink,
# never in a series colour; the bar of the others in grey.
PALETTES = {
    "light": {"background": "#ffffff", "text": "#0b0b0b", "muted": "#52514e", "grid": "#e8e7e3", "axis": "#b9b8b2",
              "other": "#a7a6a0",
              "series": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]},
    "dark": {"background": "#1a1a19", "text": "#f0efec", "muted": "#c3c2b7", "grid": "#33332f", "axis": "#5c5b56",
             "other": "#6f6e69",
             "series": ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#0ca30c", "#9085e9", "#e66767"]},
}

CSP = ("default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; font-src data:; "
       "connect-src 'none'; frame-src 'none'; worker-src 'none'; form-action 'none'")


class ChartError(ValueError):
    """A chart that cannot be drawn as asked: the words are for the model."""


@dataclass(frozen=True)
class ChartRequest:
    """What show_chart asks, checked. ``rows`` (given by the agent) or ``layer`` (read by FilterMate), never both."""

    kind: str
    title: str = ""
    layer: str = ""
    field: str = ""
    value_field: str = ""
    series_field: str = ""
    aggregate: str = "count"
    limit: int = 0
    bins: int = DEFAULT_BINS
    sort: str = "value"
    horizontal: Optional[bool] = None
    donut: bool = True
    x_type: str = ""
    x_label: str = ""
    y_label: str = ""
    rows: Tuple[Dict[str, Any], ...] = ()
    code: str = ""
    width: int = DEFAULT_SIZE[0]
    height: int = DEFAULT_SIZE[1]

    def as_arguments(self) -> Dict[str, Any]:
        """The request as arguments of show_chart again: kept on a layout item, to draw it again from its layer."""
        answer = {"kind": self.kind, "title": self.title, "width": self.width, "height": self.height}
        for key in ("layer", "field", "value_field", "series_field", "x_type", "x_label", "y_label", "code"):
            if getattr(self, key):
                answer[key] = getattr(self, key)
        if self.kind in (BAR, PIE, LINE):
            answer["aggregate"] = self.aggregate
        if self.kind in (BAR, PIE):
            answer["limit"] = self.limit
        if self.kind == BAR:
            answer["sort"] = self.sort
            if self.horizontal is not None:
                answer["horizontal"] = self.horizontal
        if self.kind == PIE:
            answer["donut"] = self.donut
        if self.kind == HISTOGRAM:
            answer["bins"] = self.bins
        if self.rows:
            answer["rows"] = [dict(row) for row in self.rows]
        return answer


def _text(arguments: Dict[str, Any], key: str, size: int) -> str:
    value = arguments.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ChartError(f"{key} is text")
    return " ".join(value.split())[:size]


def _whole(arguments: Dict[str, Any], key: str, default: int, low: int, high: int) -> int:
    value = arguments.get(key)
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != int(value):
        raise ChartError(f"{key} is a whole number")
    if not low <= value <= high:
        raise ChartError(f"{key} is from {low} to {high}")
    return int(value)


def _finite(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def parse_request(arguments: Dict[str, Any], expert: bool = False) -> ChartRequest:
    """``arguments`` of show_chart checked into a request; ChartError says what is wrong."""
    if not isinstance(arguments, dict):
        raise ChartError("the arguments are an object")
    kind = arguments.get("kind") or ""
    code = arguments.get("code") or ""
    if not isinstance(code, str):
        raise ChartError("code is text")
    if code:
        if not expert:
            raise ChartError("code (d3 written by you) is only run in the expert mode, which the user did not turn "
                             "on: use a kind and its fields instead")
        if len(code) > MAX_CODE:
            raise ChartError(f"code is {MAX_CODE} characters at most")
        kind = kind or BAR  # what the data is shaped as
    if kind not in KINDS:
        raise ChartError(f"kind is one of {', '.join(KINDS)}")
    rows = arguments.get("rows") or []
    layer = _text(arguments, "layer", 1000)
    if not isinstance(rows, list):
        raise ChartError("rows is a list of objects")
    if rows and layer:
        raise ChartError("give rows or a layer, not both")
    if not rows and not layer:
        raise ChartError("a chart needs a layer (read by FilterMate as filtered now) or rows")
    if len(rows) > MAX_ROWS:
        raise ChartError(f"rows holds {MAX_ROWS} objects at most: draw from the layer instead")
    aggregate = arguments.get("aggregate") or "count"
    if aggregate not in AGGREGATES:
        raise ChartError(f"aggregate is one of {', '.join(AGGREGATES)}")
    sort = arguments.get("sort") or "value"
    if sort not in SORTS:
        raise ChartError(f"sort is one of {', '.join(SORTS)}")
    x_type = arguments.get("x_type") or ""
    if x_type and x_type not in X_TYPES:
        raise ChartError(f"x_type is one of {', '.join(X_TYPES)}")
    horizontal = arguments.get("horizontal")
    if horizontal is not None and not isinstance(horizontal, bool):
        raise ChartError("horizontal is true or false")
    request = ChartRequest(
        kind=kind, title=_text(arguments, "title", MAX_TITLE), layer=layer,
        field=_text(arguments, "field", 200), value_field=_text(arguments, "value_field", 200),
        series_field=_text(arguments, "series_field", 200), aggregate=aggregate,
        limit=_whole(arguments, "limit", DEFAULT_LIMIT.get(kind, 10), 1, MAX_LIMIT),
        bins=_whole(arguments, "bins", DEFAULT_BINS, 2, MAX_BINS), sort=sort, horizontal=horizontal,
        donut=arguments.get("donut") is not False, x_type=x_type,
        x_label=_text(arguments, "x_label", MAX_LABEL), y_label=_text(arguments, "y_label", MAX_LABEL),
        rows=tuple(_row(row) for row in rows), code=code,
        width=_whole(arguments, "width", DEFAULT_SIZE[0], MIN_SIZE[0], MAX_SIZE[0]),
        height=_whole(arguments, "height", DEFAULT_SIZE[1], MIN_SIZE[1], MAX_SIZE[1]))
    if layer:
        _check_layer_fields(request)
    return request


def _row(row: Any) -> Dict[str, Any]:
    if not isinstance(row, dict):
        raise ChartError("each row is an object")
    kept = {}
    for key, value in row.items():
        if key not in ("label", "value", "x", "y", "series"):
            raise ChartError("a row holds label and value (bar, pie, histogram), or x, y and series (line, scatter)")
        if isinstance(value, str):
            value = value[:200]
        elif value is not None and not isinstance(value, (int, float)):
            raise ChartError(f"{key} of a row is a number or text")
        kept[key] = value
    return kept


def _check_layer_fields(request: ChartRequest) -> None:
    kind = request.kind
    if not request.field:
        raise ChartError({BAR: "field: the categories of the bars", PIE: "field: the categories of the slices",
                          HISTOGRAM: "field: the numbers to count by class", LINE: "field: the x of the line",
                          SCATTER: "field: the x of the dots"}[kind] + " is needed")
    if kind in (BAR, PIE, LINE) and request.aggregate != "count" and not request.value_field:
        raise ChartError(f"value_field: the numbers to {request.aggregate} is needed (or aggregate count)")
    if kind == SCATTER and not request.value_field:
        raise ChartError("value_field: the y of the dots is needed")
    if kind == LINE and not request.value_field and request.aggregate != "count":
        raise ChartError("value_field: the y of the line is needed")


# --- data ---------------------------------------------------------------------------------------------------------

def _reduce(values: List[float], aggregate: str) -> Optional[float]:
    if aggregate == "count":
        return float(len(values))
    numbers = [value for value in values if value is not None]
    if not numbers:
        return None
    if aggregate == "sum":
        return math.fsum(numbers)
    if aggregate == "mean":
        return math.fsum(numbers) / len(numbers)
    return min(numbers) if aggregate == "min" else max(numbers)


def label_of(value: Any, empty: str) -> str:
    """A value of a field as the label of a bar: dates in ISO, NULL as ``empty``."""
    if value is None:
        return empty
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def category_values(pairs: Iterable[Tuple[Any, Any]], aggregate: str, limit: int, sort: str,
                    others: str, empty: str) -> List[Dict[str, Any]]:
    """``(category, number)`` pairs as bars ``{label, value, others}``: the ``limit`` largest, then one for the rest.

    The rest is the same aggregate over the features of the other categories (a count or a sum adds up; a mean, a min
    or a max of the rest is that of their features, never of the bars)."""
    groups: Dict[str, List[Optional[float]]] = {}
    for category, value in pairs:
        groups.setdefault(label_of(category, empty), []).append(_finite(value))
    reduced = [(label, _reduce(values, aggregate), values) for label, values in groups.items()]
    reduced = [item for item in reduced if item[1] is not None]
    reduced.sort(key=lambda item: (-item[1], item[0]))
    kept, rest = reduced[:limit], reduced[limit:]
    if sort == "label":
        kept.sort(key=lambda item: item[0])
    bars = [{"label": label, "value": value, "others": False} for label, value, _ in kept]
    if rest:
        value = _reduce([number for _, _, values in rest for number in values], aggregate)
        if value is not None:
            bars.append({"label": others, "value": value, "others": True})
    return bars


def histogram_values(values: Iterable[Any], bins: int) -> List[Dict[str, Any]]:
    return [{"low": bar["low"], "high": bar["high"], "count": bar["count"]} for bar in histogram_bars(values, bins)]


def _series_kept(names: Sequence[str], limit: int) -> Tuple[List[str], bool]:
    """The ``limit`` series with the most points; whether others were folded."""
    counts: Dict[str, int] = {}
    for name in names:
        counts[name] = counts.get(name, 0) + 1
    ranked = sorted(counts, key=lambda name: (-counts[name], name))
    return ranked[:limit], len(ranked) > limit


def line_values(triples: Iterable[Tuple[Any, Any, Any]], aggregate: str, x_type: str, empty: str,
                others: str) -> Tuple[List[Dict[str, Any]], bool]:
    """``(x, y, series)`` as the points of lines: the y of one x of a series aggregated; the 8 largest series, the
    others dropped (a line of "others" mixes things that do not add up). Returns the points and whether some were
    dropped."""
    groups: Dict[Tuple[str, Any], List[Optional[float]]] = {}
    for x, y, series in triples:
        x_value = _x(x, x_type)
        if x_value is None:
            continue
        # No series: one line. A series field whose value is NULL gives the caller's ``empty`` before it comes here.
        groups.setdefault(("" if series is None else label_of(series, empty), x_value), []).append(_finite(y))
    names = [series for series, _ in groups]
    kept, folded = _series_kept(names, MAX_SERIES[LINE])
    points = []
    for (series, x_value), values in groups.items():
        if series not in kept:
            continue
        value = _reduce(values, aggregate)
        if value is not None:
            points.append({"x": x_value, "y": value, "series": series})
    points.sort(key=lambda point: (point["series"], point["x"]))
    dropped = folded or len(points) > MAX_LINE_POINTS
    return points[:MAX_LINE_POINTS], dropped


def _x(value: Any, x_type: str) -> Any:
    if x_type == "time":
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return value if isinstance(value, str) and value else None
    return _finite(value)


def scatter_values(triples: Sequence[Tuple[Any, Any, Any]], others: str,
                   empty: str) -> Tuple[List[Dict[str, Any]], int]:
    """``(x, y, series)`` as dots: three series at most, the rest as ``others``; ``MAX_POINTS`` dots, taken evenly.
    Returns the dots and how many points with numbers there were."""
    points = [(_finite(x), _finite(y), series) for x, y, series in triples]
    points = [point for point in points if point[0] is not None and point[1] is not None]
    total = len(points)
    if total > MAX_POINTS:
        step = total / MAX_POINTS
        points = [points[int(index * step)] for index in range(MAX_POINTS)]
    names = [label_of(series, empty) if series is not None else "" for _, _, series in points]
    kept, _ = _series_kept(names, MAX_SERIES[SCATTER])
    dots = [{"x": x, "y": y, "series": name if name in kept else others}
            for (x, y, _), name in zip(points, names)]
    return dots, total


def rows_data(request: ChartRequest, others: str, empty: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """The data of a chart from the rows the agent gave, as the templates take it; and what to say of it."""
    rows = request.rows
    kind = request.kind
    if kind in (BAR, PIE):
        pairs = []
        for row in rows:
            value = _finite(row.get("value"))
            if value is None or "label" not in row:
                raise ChartError("each row of a bar or pie chart holds label and a number value")
            pairs.append((row["label"], value))
        aggregate = "sum"  # one row per label: its value; two rows of a label add up
        data = category_values(pairs, aggregate, request.limit, request.sort, others, empty)
        return data, {"points": len(data)}
    if kind == HISTOGRAM:
        values = [row.get("value") for row in rows]
        if not any(_finite(value) is not None for value in values):
            raise ChartError("each row of a histogram holds a number value")
        data = histogram_values(values, request.bins)
        return data, {"points": len(values)}
    x_type = request.x_type or ("time" if any(isinstance(row.get("x"), str) for row in rows) else "number")
    triples = [(row.get("x"), row.get("y"), row.get("series")) for row in rows]
    if kind == LINE:
        data, dropped = line_values(triples, "sum", x_type, empty, others)
        if not data:
            raise ChartError("each row of a line holds x and a number y")
        return data, {"points": len(data), "x_type": x_type, "dropped": dropped}
    data, total = scatter_values(triples, others, empty)
    if not data:
        raise ChartError("each row of a scatter holds a number x and a number y")
    return data, {"points": total}


# --- the page ----------------------------------------------------------------------------------------------------

def script_json(value: Any) -> str:
    """``value`` as JSON that stays inside a <script>: no ``</script>``, no comment of HTML, no line separator of JS."""
    text = json.dumps(value, ensure_ascii=False, allow_nan=False)
    return (text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def chart_spec(request: ChartRequest, data: List[Dict[str, Any]], theme: str, x_type: str = "",
               subtitle: str = "", others: str = "", count_label: str = "") -> Dict[str, Any]:
    """What a template draws."""
    return {"kind": request.kind, "title": request.title, "subtitle": subtitle, "width": request.width,
            "height": request.height, "data": data, "palette": PALETTES["dark" if theme == "dark" else "light"],
            "x_label": request.x_label, "y_label": request.y_label, "x_type": x_type or request.x_type,
            "horizontal": request.horizontal, "donut": request.donut, "others_label": others,
            "count_label": count_label}


def _read(name: str) -> str:
    return (CHARTS_DIR / name).read_text(encoding="utf-8")


def page_html(spec: Dict[str, Any], code: str = "", d3_source: Optional[str] = None,
              templates: Optional[str] = None) -> str:
    """The page that draws ``spec``: with a template, or with ``code`` (d3 written by the agent, expert mode)."""
    data = script_json(spec)
    if len(data) > MAX_PAGE_DATA:
        raise ChartError("too much data for one chart: fewer categories, classes or points")
    d3_source = _read(D3_FILE) if d3_source is None else d3_source
    templates = _read(TEMPLATES_FILE) if templates is None else templates
    if code:
        # The body of a function: what it declares stays in it. "</" cannot end the script early.
        body = code.replace("</", "<\\/")
        draw = ("var SPEC = " + data + ";\n(function () { var svg = FMCharts.prepare(SPEC);\n"
                "(function (d3, svg, data, width, height, palette) {\n" + body + "\n})(d3, svg, SPEC.data, SPEC.width, "
                "SPEC.height, SPEC.palette); })();")
    else:
        draw = "var SPEC = " + data + ";\nFMCharts.draw(SPEC);"
    return ("<!doctype html><html><head><meta charset=\"utf-8\">"
            f"<meta http-equiv=\"Content-Security-Policy\" content=\"{CSP}\">"
            "<style>html,body{margin:0;padding:0;background:transparent}</style>"
            f"<script>{d3_source}</script><script>{templates}</script></head>"
            f"<body><div id=\"chart\"></div><script>{draw}</script></body></html>")


# --- what the model is told ----------------------------------------------------------------------------------------

@dataclass
class Chart:
    """A chart of the conversation: what was asked, and the SVG drawn for the chat (``theme``)."""

    chart_id: str
    request: ChartRequest
    svg: str
    theme: str = "light"
    meta: Dict[str, Any] = field(default_factory=dict)


def summary(chart: Chart, data: List[Dict[str, Any]], share_values: bool) -> Dict[str, Any]:
    """What show_chart answers: the id, what was drawn; the values only when the user shares them with the model."""
    request = chart.request
    answer: Dict[str, Any] = {"chart_id": chart.chart_id, "kind": request.kind, "title": request.title,
                              "source": "layer" if request.layer else "rows", "points": chart.meta.get("points", 0)}
    if request.layer:
        answer["layer"] = chart.meta.get("layer_name", request.layer)
        answer["features"] = chart.meta.get("features", 0)
    if request.code:
        answer["code"] = True
    if chart.meta.get("dropped"):
        answer["note"] = "some series or points were left out: the chart shows the largest ones"
    if share_values and request.layer:
        answer["data"] = data[:40]
    return answer
