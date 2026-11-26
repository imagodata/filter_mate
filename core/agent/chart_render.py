# -*- coding: utf-8 -*-
"""The charts of show_chart drawn in Python: an SVG that QtSvg reads, and the marks it holds.

Plain Python, no QGIS and no Qt, so on every QGIS. ``render`` draws the spec ``charts.chart_spec`` builds (bar,
histogram, pie, line, scatter, kpi, treemap, area) with the conventions of ``resources/charts/fm_charts.js``: margins,
axes and nice ticks (d3's algorithm), their number format, their palette. What QtSvg reads only: the look written as
attributes on each element, no style sheet, no "em", no dominant-baseline. Every text is escaped: what a layer holds is
never read as markup.

Besides the SVG, the marks: each bar, class, slice, dot or line with its box in pixels of the chart and the datum it
stands for, for what will point at a mark (a tooltip, a click that filters).
"""
from __future__ import annotations

import math
import re
import unicodedata
from bisect import bisect_right
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

FONT = "'Segoe UI', 'Noto Sans', 'DejaVu Sans', Arial, sans-serif"
MIN_SIDE, MAX_SIDE = 120, 4000  # pixels a chart is drawn at (a card of a narrow dock, the largest export)
MINUS = "−"  # d3 writes a minus sign, not a hyphen
ELLIPSIS = "…"


@dataclass
class Mark:
    """A mark of a chart: ``shape`` (bar, slice, dot, line), its box ``(x, y, width, height)`` in pixels of the chart,
    and what it stands for (``datum``: the index of its datum in the data of the spec, and its values)."""

    shape: str
    box: Tuple[float, float, float, float]
    datum: Dict[str, Any] = field(default_factory=dict)


# --- text ---------------------------------------------------------------------------------------------------------

# Widths of the printable ASCII characters in thousandths of the font size (Helvetica), from space to tilde; the
# fonts of the stack are wider (DejaVu Sans by about a tenth): WIDE. A label is cut a little early, never clipped.
_ASCII = (278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556,
          556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556, 1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500,
          667, 556, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556, 333,
          556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333, 500, 278, 556, 500,
          722, 500, 500, 500, 334, 260, 334, 584)
WIDE = 1.1
BOLD = 1.06
_INVALID = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff￾￿]")  # no place in XML


def _char_width(char: str) -> int:
    code = ord(char)
    if 32 <= code <= 126:
        return _ASCII[code - 32]
    if char in (ELLIPSIS, "—"):
        return 1000
    if char == MINUS:
        return 584
    if unicodedata.east_asian_width(char) in ("W", "F"):
        return 1000
    if unicodedata.combining(char):
        return 0
    base = unicodedata.normalize("NFD", char)[0]  # é as e
    if base != char and 32 <= ord(base) <= 126:
        return _ASCII[ord(base) - 32]
    return 600


def text_width(text: str, size: float, bold: bool = False) -> float:
    """The width of ``text`` in pixels at ``size``, roughly (a little more than most fonts of the stack)."""
    return sum(_char_width(char) for char in text) * size / 1000 * WIDE * (BOLD if bold else 1)


def fit(text: str, width: float, size: float, bold: bool = False) -> str:
    """``text`` cut with an ellipsis so that it holds in ``width`` pixels; "" when not even the ellipsis does."""
    if text_width(text, size, bold) <= width:
        return text
    room = width - text_width(ELLIPSIS, size, bold)
    if room < 0:
        return ""
    scale = size / 1000 * WIDE * (BOLD if bold else 1)
    used, kept = 0.0, []
    for char in text:
        used += _char_width(char) * scale
        if used > room:
            break
        kept.append(char)
    return "".join(kept).rstrip() + ELLIPSIS


def clean(value: Any) -> str:
    """A value as one line of text XML can hold."""
    return _INVALID.sub("", " ".join(str(value).split()))


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# --- numbers ------------------------------------------------------------------------------------------------------

_PREFIXES = "yzafpnµm\u0000kMGTPEZY"  # 10^-24 ... 10^24 by thousands; the middle one is none


def _trim(text: str) -> str:
    return text.rstrip("0").rstrip(".") if "." in text else text


def number(value: Any, percent: bool = False) -> str:
    """A number as the templates write it (``number()`` of fm_charts.js): 4 significant digits with thousands
    separators, SI prefixes from a million and below a thousandth (``1.5M``, ``500µ``), a minus sign; ``percent``: 2
    decimals at most. One change: from 10,000 the whole number (d3 wrote 12345 as ``1.235e+4``)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return ""
    sign, size = (MINUS if value < 0 else ""), abs(float(value))
    if percent:
        return sign + _trim(f"{size:.2f}") if round(size, 2) else "0"
    if size == 0:
        return "0"
    if size >= 1e6 or size < 1e-3:
        mantissa, exponent = f"{size:.2e}".split("e")
        exponent_value = int(exponent)
        thousands = max(-8, min(8, exponent_value // 3))
        digits = mantissa.replace(".", "")
        whole = exponent_value - 3 * thousands + 1
        if whole >= len(digits):
            text = digits + "0" * (whole - len(digits))
        elif whole > 0:
            text = digits[:whole] + "." + digits[whole:]
        else:
            text = "0." + "0" * -whole + digits
        return sign + _trim(text) + _PREFIXES[thousands + 8].replace("\u0000", "")
    rounded = float(f"{size:.3e}")
    if rounded >= 1e4:
        return sign + f"{round(size):,}"
    exponent_value = int(f"{rounded:e}".split("e")[1])
    return sign + _trim(f"{rounded:,.{max(0, 3 - exponent_value)}f}")


def _n(value: float) -> str:
    """A coordinate in the SVG: 2 decimals at most."""
    if not math.isfinite(value):
        return "0"
    rounded = round(value, 2)
    if rounded == int(rounded):
        return str(int(rounded))
    return _trim(f"{rounded:.2f}")


# --- scales and ticks (d3-array ticks, d3-scale nice) -------------------------------------------------------------

_E10, _E5, _E2 = math.sqrt(50), math.sqrt(10), math.sqrt(2)
MAX_TICKS = 200


def _js_round(value: float) -> int:
    return math.floor(value + 0.5)


def _tick_spec(start: float, stop: float, count: float) -> Tuple[int, int, float]:
    step = (stop - start) / max(0.0, count) if count > 0 else math.inf
    if not math.isfinite(step) or step <= 0:
        return 0, -1, 0.0
    power = math.floor(math.log10(step))
    error = step / math.pow(10, power)
    factor = 10 if error >= _E10 else 5 if error >= _E5 else 2 if error >= _E2 else 1
    if power < 0:
        inc = math.pow(10, -power) / factor
        if not math.isfinite(start * inc) or not math.isfinite(stop * inc):
            return 0, -1, 0.0
        i1, i2 = _js_round(start * inc), _js_round(stop * inc)
        if i1 / inc < start:
            i1 += 1
        if i2 / inc > stop:
            i2 -= 1
        inc = -inc
    else:
        inc = math.pow(10, power) * factor
        if not math.isfinite(inc):
            return 0, -1, 0.0
        i1, i2 = _js_round(start / inc), _js_round(stop / inc)
        if i1 * inc < start:
            i1 += 1
        if i2 * inc > stop:
            i2 -= 1
    if i2 < i1 and 0.5 <= count < 2:
        return _tick_spec(start, stop, count * 2)
    return i1, i2, inc


def ticks(start: float, stop: float, count: float) -> List[float]:
    """The ticks d3 puts between ``start`` and ``stop`` for about ``count`` of them."""
    if not count > 0 or not math.isfinite(start) or not math.isfinite(stop):
        return []
    if start == stop:
        return [start]
    reverse = stop < start
    i1, i2, inc = _tick_spec(stop, start, count) if reverse else _tick_spec(start, stop, count)
    if not i2 >= i1 or inc == 0:
        return []
    found = [(i1 + index) / -inc if inc < 0 else (i1 + index) * inc for index in range(min(i2 - i1 + 1, MAX_TICKS))]
    return found[::-1] if reverse else found


def _tick_increment(start: float, stop: float, count: float) -> float:
    return _tick_spec(start, stop, count)[2]


def _tick_step(start: float, stop: float, count: float) -> float:
    reverse = stop < start
    inc = _tick_increment(stop, start, count) if reverse else _tick_increment(start, stop, count)
    if inc == 0:
        return 0.0
    return (-1 if reverse else 1) * (1 / -inc if inc < 0 else inc)


def nice(low: float, high: float, count: int = 10) -> Tuple[float, float]:
    """``(low, high)`` widened to round numbers as d3's ``scale.nice()``; unchanged when that does not settle."""
    start, stop = (high, low) if high < low else (low, high)
    previous = None
    for _ in range(10):
        step = _tick_increment(start, stop, count)
        if step == previous:
            if not (math.isfinite(start) and math.isfinite(stop)):
                break
            return (stop, start) if high < low else (start, stop)
        if step > 0:
            start, stop = math.floor(start / step) * step, math.ceil(stop / step) * step
        elif step < 0:
            start, stop = math.ceil(start * step) / step, math.floor(stop * step) / step
        else:
            break
        previous = step
    return low, high


class Linear:
    """A linear scale from ``domain`` to ``extent`` (pixels); a domain of one value maps to the middle."""

    def __init__(self, domain: Tuple[float, float], extent: Tuple[float, float]) -> None:
        self.domain, self.extent = domain, extent

    def __call__(self, value: float) -> float:
        (d0, d1), (r0, r1) = self.domain, self.extent
        if d1 == d0:
            return (r0 + r1) / 2
        span = d1 - d0
        if math.isfinite(span):
            share = (value - d0) / span
        else:  # from -1.7e308 to 1.7e308: in halves, which fit
            share = (value / 2 - d0 / 2) / (d1 / 2 - d0 / 2)
        return r0 + share * (r1 - r0)


def _band(count: int, start: float, stop: float, inner: float, outer: float = 0.0) -> Tuple[List[float], float]:
    """d3.scaleBand: the start of each of ``count`` bands, and their width."""
    step = (stop - start) / max(1.0, count - inner + outer * 2)
    first = start + (stop - start - step * (count - inner)) * 0.5
    return [first + step * index for index in range(count)], step * (1 - inner)


def _extent(values: Sequence[float]) -> Tuple[float, float]:
    low, high = min(values), max(values)
    if low == high:  # one value: an axis around it (d3 drew every point in the middle, with one tick)
        pad = abs(low) / 10 or 1.0
        return low - pad, high + pad
    return low, high


# --- time (d3-time, UTC) ------------------------------------------------------------------------------------------

_SECOND, _MINUTE, _HOUR, _DAY = 1000.0, 60000.0, 3600000.0, 86400000.0
_WEEK, _MONTH, _YEAR = 7 * _DAY, 30 * _DAY, 365 * _DAY
_INTERVALS = (("second", 1, _SECOND), ("second", 5, 5 * _SECOND), ("second", 15, 15 * _SECOND),
              ("second", 30, 30 * _SECOND), ("minute", 1, _MINUTE), ("minute", 5, 5 * _MINUTE),
              ("minute", 15, 15 * _MINUTE), ("minute", 30, 30 * _MINUTE), ("hour", 1, _HOUR), ("hour", 3, 3 * _HOUR),
              ("hour", 6, 6 * _HOUR), ("hour", 12, 12 * _HOUR), ("day", 1, _DAY), ("day", 2, 2 * _DAY),
              ("week", 1, _WEEK), ("month", 1, _MONTH), ("month", 3, 3 * _MONTH), ("year", 1, _YEAR))
_DURATIONS = [interval[2] for interval in _INTERVALS]
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.(\d+))?)?)?(Z|[+-]\d{2}:?\d{2})?$")
_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December")
_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MAX_TIME_STEPS = 5000


def parse_time(text: Any) -> Optional[float]:
    """An ISO date, with a time or not, as milliseconds since 1970 in UTC (a time without a zone is UTC, as the
    templates read it); None when it is none."""
    match = _DATE.match(text) if isinstance(text, str) else None
    if match is None:
        return None
    year, month, day, hour, minute, second, fraction, zone = match.groups()
    try:
        moment = datetime(int(year), int(month), int(day), int(hour or 0), int(minute or 0), int(second or 0),
                          int((fraction or "0")[:3].ljust(3, "0")) * 1000, tzinfo=timezone.utc)  # in ms, as JS
    except ValueError:
        return None
    if zone and zone != "Z":
        digits = zone.replace(":", "")
        offset = timedelta(hours=int(digits[1:3]), minutes=int(digits[3:5]))
        moment = moment - offset if digits[0] == "+" else moment + offset
    return (moment - _EPOCH).total_seconds() * 1000


def _moment(milliseconds: float) -> datetime:
    return _EPOCH + timedelta(milliseconds=milliseconds)


def _ms(moment: datetime) -> float:
    return (moment - _EPOCH).total_seconds() * 1000


def _candidates(unit: str, start: datetime, stop: datetime) -> List[datetime]:
    """Every start of ``unit`` from ``start`` to ``stop`` (both kept), at most MAX_TIME_STEPS."""
    found: List[datetime] = []
    if unit == "year":
        for year in range(start.year, stop.year + 1):
            moment = datetime(year, 1, 1, tzinfo=timezone.utc)
            if moment >= start:
                found.append(moment)
        return found[:MAX_TIME_STEPS]
    if unit == "month":
        year, month = start.year, start.month
        while len(found) < MAX_TIME_STEPS:
            moment = datetime(year, month, 1, tzinfo=timezone.utc)
            if moment > stop:
                break
            if moment >= start:
                found.append(moment)
            year, month = (year + 1, 1) if month == 12 else (year, month + 1)
        return found
    floor = {"second": start.replace(microsecond=0), "minute": start.replace(second=0, microsecond=0),
             "hour": start.replace(minute=0, second=0, microsecond=0),
             "day": start.replace(hour=0, minute=0, second=0, microsecond=0)}.get(unit)
    step = {"second": timedelta(seconds=1), "minute": timedelta(minutes=1), "hour": timedelta(hours=1)}.get(
        unit, timedelta(days=1))
    if unit == "week":  # Sundays
        floor = start.replace(hour=0, minute=0, second=0, microsecond=0)
        floor -= timedelta(days=(floor.weekday() + 1) % 7)
        step = timedelta(days=7)
    moment = floor
    while moment <= stop and len(found) < MAX_TIME_STEPS:
        if moment >= start:
            found.append(moment)
        try:
            moment += step
        except OverflowError:
            break
    return found


def _field(unit: str, moment: datetime) -> int:
    if unit == "day":  # days since 1970 (d3-time 3: every other day goes on across months)
        return math.floor(_ms(moment) / _DAY)
    return {"second": moment.second, "minute": moment.minute, "hour": moment.hour, "month": moment.month - 1}.get(
        unit, 0)


def time_ticks(start: float, stop: float, count: float) -> List[float]:
    """The ticks of d3's UTC time scale between two moments (milliseconds), about ``count`` of them."""
    if not count > 0 or not math.isfinite(start) or not math.isfinite(stop) or stop < start:
        return []
    if start == stop:
        return [start]
    try:
        return _time_ticks(start, stop, count)
    except (OverflowError, ValueError):  # beyond the years datetime holds
        return []


def _time_ticks(start: float, stop: float, count: float) -> List[float]:
    target = (stop - start) / count
    index = bisect_right(_DURATIONS, target)
    if index == 0:  # milliseconds
        every = max(_tick_step(start, stop, count), 1)
        first = math.ceil(start / every) * every
        return [first + every * step for step in range(MAX_TICKS) if first + every * step <= stop]
    low, high = _moment(start), _moment(stop)
    if index == len(_INTERVALS):
        every = max(1, math.floor(_tick_step(start / _YEAR, stop / _YEAR, count)))
        first = -(-low.year // every) * every
        found = []
        for year in range(max(1, first), high.year + 1, every):
            moment = datetime(year, 1, 1, tzinfo=timezone.utc)
            if moment >= low and len(found) < MAX_TICKS:
                found.append(_ms(moment))
        return found
    if target / _DURATIONS[index - 1] < _DURATIONS[index] / target:
        index -= 1
    unit, every, _ = _INTERVALS[index]
    moments = _candidates(unit, low, high)
    return [_ms(moment) for moment in moments if every == 1 or _field(unit, moment) % every == 0][:MAX_TICKS]


def time_label(milliseconds: float) -> str:
    """A tick of a time axis as d3 writes it (its default multi-scale format, in English)."""
    moment = _moment(milliseconds)
    twelve = f"{moment.hour % 12 or 12:02d}"
    if moment.microsecond:
        return f".{moment.microsecond // 1000:03d}"
    if moment.second:
        return f":{moment.second:02d}"
    if moment.minute:
        return f"{twelve}:{moment.minute:02d}"
    if moment.hour:
        return f"{twelve} {'PM' if moment.hour >= 12 else 'AM'}"
    if moment.day != 1:
        if moment.weekday() != 6:
            return f"{_DAYS[moment.weekday()]} {moment.day:02d}"
        return f"{_MONTHS[moment.month - 1][:3]} {moment.day:02d}"
    if moment.month != 1:
        return _MONTHS[moment.month - 1]
    return f"{moment.year:04d}"


# --- the SVG ------------------------------------------------------------------------------------------------------

class _Svg:
    """Elements written as text, their look as attributes."""

    def __init__(self, width: int, height: int, palette: Dict[str, Any]) -> None:
        self.width, self.height, self.palette = width, height, palette
        self.parts: List[str] = []
        self.marks: List[Mark] = []

    def element(self, tag: str, attributes: Dict[str, Any], text: Optional[str] = None) -> None:
        written = "".join(f' {name}="{_escape(_n(value) if isinstance(value, float) else str(value))}"'
                          for name, value in attributes.items() if value is not None)
        if text is None:
            self.parts.append(f"<{tag}{written}/>")
        else:
            self.parts.append(f"<{tag}{written}>{_escape(text)}</{tag}>")

    def text(self, x: float, y: float, text: str, size: float = 10, fill: str = "", anchor: str = "",
             weight: Any = None, rotate: float = 0) -> None:
        if not text:
            return
        attributes: Dict[str, Any] = {"font-size": _n(size), "fill": fill or self.palette["text"]}
        if anchor:
            attributes["text-anchor"] = anchor
        if weight:
            attributes["font-weight"] = weight
        if rotate:  # QtSvg reads translate then rotate
            attributes = dict({"transform": f"translate({_n(x)},{_n(y)}) rotate({_n(rotate)})"}, **attributes)
        else:
            attributes = dict({"x": float(x), "y": float(y)}, **attributes)
        self.element("text", attributes, text)

    def line(self, x1: float, y1: float, x2: float, y2: float, stroke: str) -> None:
        self.element("line", {"x1": float(x1), "y1": float(y1), "x2": float(x2), "y2": float(y2), "stroke": stroke,
                              "stroke-width": "1"})

    def path(self, d: str, **attributes: Any) -> None:
        self.element("path", dict({"d": d}, **{name.replace("_", "-"): value for name, value in attributes.items()}))

    def mark(self, shape: str, x: float, y: float, width: float, height: float, datum: Dict[str, Any]) -> None:
        left, top = max(0.0, min(x, self.width)), max(0.0, min(y, self.height))
        right, bottom = max(0.0, min(x + width, self.width)), max(0.0, min(y + height, self.height))
        self.marks.append(Mark(shape, (round(left, 2), round(top, 2), round(right - left, 2), round(bottom - top, 2)),
                               datum))

    def write(self) -> str:
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" '
                f'viewBox="0 0 {self.width} {self.height}" font-family="{_escape(FONT)}" font-size="11" '
                f'fill="{_escape(str(self.palette["text"]))}">')
        return head + "".join(self.parts) + "</svg>"


@dataclass
class _Frame:
    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height


def _top(svg: _Svg, spec: Dict[str, Any]) -> float:
    """The title and the subtitle; where the plot may start."""
    top = 8.0
    title = fit(clean(spec.get("title") or ""), svg.width - 24, 14, bold=True)
    if title:
        svg.text(12, 22, title, 14, weight="600")
        top = 36.0
    subtitle = fit(clean(spec.get("subtitle") or ""), svg.width - 24, 11)
    if subtitle:
        svg.text(12, top + 6, subtitle, 11, fill=svg.palette["muted"])
        top += 18
    return top


def _frame(svg: _Svg, top: float, left: float = 48, right: float = 16, bottom: float = 34) -> _Frame:
    return _Frame(left, top + 8, max(40.0, svg.width - left - right), max(40.0, svg.height - top - 8 - bottom))


def _axis_title(svg: _Svg, text: str, x: float, y: float, rotate: bool = False, room: float = 0) -> None:
    text = fit(clean(text or ""), room or svg.width - 16, 10)
    svg.text(x, y, text, 10, fill=svg.palette["muted"], anchor="middle", rotate=-90 if rotate else 0)


def _value_ticks(low: float, high: float, length: float, per: float) -> Tuple[Tuple[float, float], List[float]]:
    """A nice domain over ``low`` to ``high`` and its ticks, one every ``per`` pixels of ``length`` about."""
    domain = nice(low, high)
    return domain, ticks(domain[0], domain[1], max(2, math.floor(length / per)))


def _ticks_width(values: Sequence[float]) -> float:
    return max((text_width(number(value), 10) for value in values), default=0.0)


def _left_margin(values: Sequence[float], y_label: str, least: float = 52) -> float:
    """Room at the left for the labels of a vertical value axis (3 px from it) and the title of the axis."""
    return max(least, 3 + _ticks_width(values) + (22 if y_label else 8))


def _grid_left(svg: _Svg, frame: _Frame, scale: Linear, values: Sequence[float]) -> None:
    """A vertical value axis: a light line across the plot at each tick, its label at the left; no domain line."""
    for value in values:
        y = scale(value)
        svg.line(frame.x, y + 0.5, frame.right, y + 0.5, svg.palette["grid"])
        svg.text(frame.x - 3, y + 3.2, number(value), 10, fill=svg.palette["muted"], anchor="end")


def _axis_bottom(svg: _Svg, frame: _Frame, scale: Callable[[float], float], values: Sequence[float],
                 label: Callable[[float], str]) -> None:
    """A horizontal axis at the bottom of the plot: its line with an end tick at each side, a tick of 6 px and a
    label at each value; labels that would overlap the one before are left out."""
    y = frame.bottom + 0.5
    svg.path(f"M{_n(frame.x + 0.5)},{_n(y + 6)}V{_n(y)}H{_n(frame.right + 0.5)}V{_n(y + 6)}", fill="none",
             stroke=svg.palette["axis"], stroke_width="1")
    last_end = -math.inf
    for value in values:
        x = scale(value)
        svg.line(x + 0.5, y, x + 0.5, y + 6, svg.palette["axis"])
        text = label(value)
        half = text_width(text, 10) / 2
        if x - half < last_end + 4:
            continue
        last_end = x + half
        svg.text(x + 0.5, y + 16.1, text, 10, fill=svg.palette["muted"], anchor="middle")


def _bar_path(x: float, y: float, width: float, height: float, end: str) -> str:
    """A bar with its data end (``top``, ``bottom``, ``right``, ``left``) rounded (4 px), its base square."""
    r = max(0.0, min(4.0, width / 2, height / 2))
    if end == "top":
        return (f"M{_n(x)},{_n(y + height)}V{_n(y + r)}A{_n(r)},{_n(r)} 0 0 1 {_n(x + r)},{_n(y)}"
                f"H{_n(x + width - r)}A{_n(r)},{_n(r)} 0 0 1 {_n(x + width)},{_n(y + r)}V{_n(y + height)}Z")
    if end == "bottom":
        return (f"M{_n(x)},{_n(y)}V{_n(y + height - r)}A{_n(r)},{_n(r)} 0 0 0 {_n(x + r)},{_n(y + height)}"
                f"H{_n(x + width - r)}A{_n(r)},{_n(r)} 0 0 0 {_n(x + width)},{_n(y + height - r)}V{_n(y)}Z")
    if end == "right":
        return (f"M{_n(x)},{_n(y)}H{_n(x + width - r)}A{_n(r)},{_n(r)} 0 0 1 {_n(x + width)},{_n(y + r)}"
                f"V{_n(y + height - r)}A{_n(r)},{_n(r)} 0 0 1 {_n(x + width - r)},{_n(y + height)}H{_n(x)}Z")
    return (f"M{_n(x + width)},{_n(y)}H{_n(x + r)}A{_n(r)},{_n(r)} 0 0 0 {_n(x)},{_n(y + r)}"
            f"V{_n(y + height - r)}A{_n(r)},{_n(r)} 0 0 0 {_n(x + r)},{_n(y + height)}H{_n(x + width)}Z")


def _finite(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number_value = float(value)
    return number_value if math.isfinite(number_value) else None


# --- bar ----------------------------------------------------------------------------------------------------------

BAR_LABEL_ANGLE = -35  # degrees of the labels of narrow vertical bars


def _bar(svg: _Svg, spec: Dict[str, Any]) -> None:
    """[{label, value, others}]: one hue, the bar of the others in grey, the values written at the ends."""
    palette = svg.palette
    data = [(index, row) for index, row in enumerate(spec.get("data") or [])
            if _finite(row.get("value")) is not None]
    top = _top(svg, spec)
    if not data:
        return
    labels = [clean(row.get("label", "")) for _, row in data]
    values = [float(row["value"]) for _, row in data]
    longest = max(len(label) for label in labels)
    horizontal = spec.get("horizontal") is True or (spec.get("horizontal") is not False and
                                                    (longest > 10 or len(data) > 12))
    low, high = min(0.0, min(values)), max(0.0, max(values))  # 0 always inside: the bars grow from it
    if low == high:
        high = 1.0
    written = len(data) <= 16
    color = [palette["other"] if row.get("others") else palette["series"][0] for _, row in data]
    if horizontal:
        widest = max(text_width(label, 10) for label in labels)
        left = min(svg.width * 0.4, 14 + widest)
        right = 16.0
        if written:
            right = max(right, 10 + max(text_width(number(value), 10) for value in values))
        frame = _frame(svg, top, left, right, 34 if spec.get("y_label") else 22)
        domain, values_ticks = _value_ticks(low, high, frame.width, 80)
        x = Linear(domain, (frame.x, frame.right))
        starts, band = _band(len(data), frame.y, frame.bottom, 0.18)
        for value in values_ticks:
            svg.line(x(value) + 0.5, frame.y, x(value) + 0.5, frame.bottom, palette["grid"])
        last_end = -math.inf
        for value in values_ticks:
            text = number(value)
            half = text_width(text, 10) / 2
            if x(value) - half >= last_end + 4:
                svg.text(x(value) + 0.5, frame.bottom + 10.1, text, 10, fill=palette["muted"], anchor="middle")
                last_end = x(value) + half
        zero = x(0)
        for (index, row), label, value, fill, start in zip(data, labels, values, color, starts):
            x0, width = x(min(0.0, value)), max(abs(x(value) - zero), 0.5)
            svg.path(_bar_path(x0, start, width, band, "left" if value < 0 else "right"), fill=fill)
            svg.mark("bar", x0, start, width, band, {"index": index, "label": label, "value": value,
                                                     "others": bool(row.get("others"))})
            svg.text(frame.x - 6, start + band / 2 + 3.2, fit(label, frame.x - 12, 10), 10, anchor="end")
            if written:
                svg.text(x(max(0.0, value)) + 4, start + band / 2 + 4, number(value), 10)
        svg.path(f"M{_n(zero + 0.5)},{_n(frame.y)}V{_n(frame.bottom)}", fill="none", stroke=palette["axis"],
                 stroke_width="1")
        _axis_title(svg, spec.get("y_label") or "", frame.x + frame.width / 2, svg.height - 6)
        return
    x_label = spec.get("x_label") or ""
    y_label = spec.get("y_label") or ""
    # The bands come from the plot's width, the plot's height from the room the labels under the bars take: their
    # angle is chosen on a first guess of the left margin, then the margin is set from the ticks.
    widest = max(text_width(label, 10) for label in labels)
    guess_starts, guess_band = _band(len(data), 52, svg.width - 16, 0.18, 0.1)
    step = guess_band / 0.82
    slanted = widest > step - 4 and len(data) > 1
    sine = math.sin(math.radians(-BAR_LABEL_ANGLE))
    longest_slanted = min(widest, 120.0, max(30.0, (0.3 * svg.height - 8) / sine))
    bottom = (12 + longest_slanted * sine + 8 if slanted else 22) + (12 if x_label else 0)
    frame = _frame(svg, top, 52, 16, bottom)
    domain, values_ticks = _value_ticks(low, high, frame.height, 50)
    left = _left_margin(values_ticks, y_label)
    frame = _frame(svg, top, left, 16, bottom)
    y = Linear(domain, (frame.bottom, frame.y))
    _grid_left(svg, frame, y, values_ticks)
    starts, band = _band(len(data), frame.x, frame.right, 0.18, 0.1)
    zero = y(0)
    for (index, row), label, value, fill, start in zip(data, labels, values, color, starts):
        y0, height = y(max(0.0, value)), max(abs(y(value) - zero), 0.5)
        svg.path(_bar_path(start, y0, band, height, "bottom" if value < 0 else "top"), fill=fill)
        svg.mark("bar", start, y0, band, height, {"index": index, "label": label, "value": value,
                                                  "others": bool(row.get("others"))})
        middle = start + band / 2
        if slanted:
            svg.text(middle + 3, frame.bottom + 12, fit(label, longest_slanted, 10), 10, anchor="end",
                     rotate=BAR_LABEL_ANGLE)
        else:
            svg.text(middle, frame.bottom + 13.1, fit(label, band / 0.82 - 2, 10), 10, anchor="middle")
        if written:
            if value < 0:
                svg.text(middle, y(value) + 12, number(value), 10, anchor="middle")
            else:
                svg.text(middle, y(value) - 4, number(value), 10, anchor="middle")
    svg.path(f"M{_n(frame.x)},{_n(zero + 6.5)}V{_n(zero + 0.5)}H{_n(frame.right)}V{_n(zero + 6.5)}", fill="none",
             stroke=palette["axis"], stroke_width="1")
    _axis_title(svg, x_label, frame.x + frame.width / 2, svg.height - 8)
    _axis_title(svg, y_label, 12, frame.y + frame.height / 2, rotate=True, room=frame.height)


# --- histogram ----------------------------------------------------------------------------------------------------

def _histogram(svg: _Svg, spec: Dict[str, Any]) -> None:
    """[{low, high, count}]: adjacent bars 2 px apart."""
    palette = svg.palette
    data = [(index, row) for index, row in enumerate(spec.get("data") or [])
            if None not in (_finite(row.get("low")), _finite(row.get("high")), _finite(row.get("count")))]
    top = _top(svg, spec)
    if not data:
        return
    x_label = spec.get("x_label") or ""
    y_label = spec.get("y_label") or spec.get("count_label") or ""
    low, high = min(row["low"] for _, row in data), max(row["high"] for _, row in data)
    if low == high:
        low, high = low - 0.5, high + 0.5
    bottom = 46 if x_label else 34
    frame = _frame(svg, top, 52, 16, bottom)
    domain, values_ticks = _value_ticks(0, max(row["count"] for _, row in data) or 1, frame.height, 50)
    frame = _frame(svg, top, _left_margin(values_ticks, y_label), 16, bottom)
    y = Linear(domain, (frame.bottom, frame.y))
    x = Linear((low, high), (frame.x, frame.right))
    _grid_left(svg, frame, y, values_ticks)
    _axis_bottom(svg, frame, x, ticks(low, high, max(2, math.floor(frame.width / 80))), number)
    for index, row in data:
        if len(data) == 1:
            x0, x1 = frame.x, frame.right
        else:
            x0, x1 = x(row["low"]) + 1, x(row["high"]) - 1
        count = row["count"]
        datum = {"index": index, "low": row["low"], "high": row["high"], "count": count}
        width = max(x1 - x0, 0.5)
        if count > 0:
            height = max(y(0) - y(count), 0.5)
            svg.path(_bar_path(x0, y(count), width, height, "top"), fill=palette["series"][0])
            svg.mark("bar", x0, y(count), width, height, datum)
        else:  # a class of none: its place still points at it
            svg.mark("bar", x0, frame.bottom, width, 0, datum)
    _axis_title(svg, x_label, frame.x + frame.width / 2, svg.height - 8)
    _axis_title(svg, y_label, 12, frame.y + frame.height / 2, rotate=True, room=frame.height)


# --- pie ----------------------------------------------------------------------------------------------------------

def _point(cx: float, cy: float, radius: float, angle: float) -> Tuple[float, float]:
    """A point at ``angle`` (radians from 12 o'clock, clockwise), as d3.arc places it."""
    return cx + radius * math.sin(angle), cy - radius * math.cos(angle)


def _arc_path(cx: float, cy: float, inner: float, outer: float, start: float, end: float) -> str:
    if end - start >= 2 * math.pi - 1e-9:  # a whole ring: two halves (an arc to its own start draws nothing)
        middle = start + math.pi
        return _arc_path(cx, cy, inner, outer, start, middle) + _arc_path(cx, cy, inner, outer, middle, end)
    large = 1 if end - start > math.pi else 0
    x0, y0 = _point(cx, cy, outer, start)
    x1, y1 = _point(cx, cy, outer, end)
    d = f"M{_n(x0)},{_n(y0)}A{_n(outer)},{_n(outer)} 0 {large} 1 {_n(x1)},{_n(y1)}"
    if inner > 0:
        x2, y2 = _point(cx, cy, inner, end)
        x3, y3 = _point(cx, cy, inner, start)
        d += f"L{_n(x2)},{_n(y2)}A{_n(inner)},{_n(inner)} 0 {large} 0 {_n(x3)},{_n(y3)}Z"
    else:
        d += f"L{_n(cx)},{_n(cy)}Z"
    return d


def _arc_box(cx: float, cy: float, inner: float, outer: float, start: float,
             end: float) -> Tuple[float, float, float, float]:
    """The box of a slice: its four corners, and the points of its outer edge at 12, 3, 6 and 9 o'clock it passes."""
    points = [_point(cx, cy, radius, angle) for radius in (inner, outer) for angle in (start, end)]
    quarter = math.ceil(start / (math.pi / 2))
    while quarter * math.pi / 2 <= end:
        points.append(_point(cx, cy, outer, quarter * math.pi / 2))
        quarter += 1
    xs, ys = [point[0] for point in points], [point[1] for point in points]
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def _pie(svg: _Svg, spec: Dict[str, Any]) -> None:
    """[{label, value, others}]: a ring (donut) by default, the slices 2 px apart, a legend at the right."""
    palette = svg.palette
    data = [(index, row) for index, row in enumerate(spec.get("data") or [])
            if (_finite(row.get("value")) or 0) > 0]
    top = _top(svg, spec)
    if not data:
        return
    frame = _frame(svg, top, 12, 12, 12)
    legend_width = min(220.0, frame.width * 0.45)
    radius = max(20.0, min((frame.width - legend_width) / 2, frame.height / 2) - 4)
    cx, cy = frame.x + radius + 4, frame.y + frame.height / 2
    largest = max(float(row["value"]) for _, row in data)
    scaled = math.fsum(float(row["value"]) / largest for _, row in data)  # a sum of 1e308s stays finite
    shares = [float(row["value"]) / largest / scaled for _, row in data]
    donut = spec.get("donut") is not False
    inner = radius * 0.58 if donut else 0.0
    colors = [palette["other"] if row.get("others") else palette["series"][index % len(palette["series"])]
              for index, (_, row) in enumerate(data)]
    angle = 0.0
    for (index, row), share, fill in zip(data, shares, colors):
        end = angle + share * 2 * math.pi
        # The slices are 2 px apart: a stroke of the background over their edges.
        svg.path(_arc_path(cx, cy, inner, radius, angle, end), fill=fill, stroke=palette["background"],
                 stroke_width="2", stroke_linejoin="round")
        svg.mark("slice", *_arc_box(cx, cy, inner, radius, angle, end),
                 {"index": index, "label": clean(row.get("label", "")), "value": float(row["value"]),
                  "share": share, "others": bool(row.get("others"))})
        angle = end
    if donut:
        total = number(largest * scaled)
        size = 16.0
        while size > 9 and text_width(total, size, bold=True) > inner * 1.7:
            size -= 1
        if text_width(total, size, bold=True) <= inner * 1.7:
            svg.text(cx, cy + size * 0.375, total, size, anchor="middle", weight="600")
    lx = cx + radius + 18
    row_height = min(20.0, frame.height / len(data))
    size = 11.0 if row_height >= 14 else max(7.0, row_height - 2)
    swatch = min(10.0, max(4.0, row_height - 3))
    ly = cy - row_height * len(data) / 2 + row_height / 2
    room = svg.width - (lx + 16) - 8
    for position, ((_, row), share, fill) in enumerate(zip(data, shares, colors)):
        y = ly + position * row_height
        svg.element("rect", {"x": float(lx), "y": float(y - swatch / 2), "width": float(swatch),
                             "height": float(swatch), "rx": "2", "fill": fill})
        tail = "  " + number(100 * share, percent=True) + " %"
        label = fit(clean(row.get("label", "")), room - text_width(tail, size), size)
        svg.text(lx + 16, y + size * 0.36, label + tail if label else tail.strip(), size)


# --- line and scatter ---------------------------------------------------------------------------------------------

def _series_names(rows: Sequence[Dict[str, Any]]) -> List[str]:
    return list(dict.fromkeys(clean(row.get("series") or "") for row in rows))


def _spread(positions: List[Tuple[float, int]], gap: float, low: float, high: float) -> Dict[int, float]:
    """Labels at the end of their lines, moved apart so that none overlaps the next, within low and high."""
    placed: List[Tuple[float, int]] = []
    for y, key in sorted(positions):
        if placed and y < placed[-1][0] + gap:
            y = placed[-1][0] + gap
        placed.append((y, key))
    overflow = placed[-1][0] - high if placed else 0
    if overflow > 0:
        placed = [(max(low, y - overflow), key) for y, key in placed]
    return {key: y for y, key in placed}


def _line(svg: _Svg, spec: Dict[str, Any]) -> None:
    """[{x, y, series}], x a number or a date (ISO text when x_type is "time"); one line per series, 2 px."""
    palette = svg.palette
    time = spec.get("x_type") == "time"
    points = []
    for index, row in enumerate(spec.get("data") or []):
        x_value = parse_time(row.get("x")) if time else _finite(row.get("x"))
        y_value = _finite(row.get("y"))
        if x_value is not None and y_value is not None:
            points.append((index, x_value, y_value, clean(row.get("series") or "")))
    top = _top(svg, spec)
    if not points:
        return
    names = list(dict.fromkeys(point[3] for point in points))
    several = len(names) > 1
    x_label, y_label = spec.get("x_label") or "", spec.get("y_label") or ""
    right, bottom = (110 if several else 20), (46 if x_label else 34)
    frame = _frame(svg, top, 52, right, bottom)
    lo, hi = min(point[2] for point in points), max(point[2] for point in points)
    filled = spec.get("kind") == "area"
    low, high = min(0.0, lo), max(0.0, hi) if filled else hi
    if low == high:
        high = low + 1
    domain, values_ticks = _value_ticks(low, high, frame.height, 50)
    frame = _frame(svg, top, _left_margin(values_ticks, y_label), right, bottom)
    y = Linear(domain, (frame.bottom, frame.y))
    x_low, x_high = min(point[1] for point in points), max(point[1] for point in points)
    if x_low == x_high:
        x_low, x_high = (x_low - _DAY, x_high + _DAY) if time else _extent([x_low])
    x = Linear((x_low, x_high), (frame.x, frame.right))
    _grid_left(svg, frame, y, values_ticks)
    count = max(2, math.floor(frame.width / 90))
    if time:
        _axis_bottom(svg, frame, x, time_ticks(x_low, x_high, count), time_label)
    else:
        _axis_bottom(svg, frame, x, ticks(x_low, x_high, count), number)
    ends = []
    for number_of, name in enumerate(names):
        series = sorted((point for point in points if point[3] == name), key=lambda point: point[1])
        color = palette["series"][number_of % len(palette["series"])]
        d = "".join(("M" if position == 0 else "L") + f"{_n(x(point[1]))},{_n(y(point[2]))}"
                    for position, point in enumerate(series))
        if filled:
            ground = y(0)
            area = (f"M{_n(x(series[0][1]))},{_n(ground)}L" + d[1:]
                    + f"L{_n(x(series[-1][1]))},{_n(ground)}Z")
            svg.path(area, fill=color, fill_opacity="0.22")
        svg.path(d, fill="none", stroke=color, stroke_width="2", stroke_linejoin="round", stroke_linecap="round")
        xs, ys = [x(point[1]) for point in series], [y(point[2]) for point in series]
        svg.mark("line", min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys), {"series": name})
        for (index, x_value, y_value, _), px, py in zip(series, xs, ys):
            if len(series) <= 40:
                svg.element("circle", {"cx": float(px), "cy": float(py), "r": "3", "fill": color,
                                       "stroke": palette["background"], "stroke-width": "1.5"})
            raw = (spec.get("data") or [])[index].get("x")
            svg.mark("dot", px - 3, py - 3, 6, 6, {"index": index, "series": name, "x": raw, "y": y_value})
        ends.append((ys[-1], number_of))
    if several:  # the name at the end of its line: identity is never the colour alone
        places = _spread(ends, 12, frame.y + 4, frame.bottom + 4)
        for number_of, name in enumerate(names):
            svg.text(frame.right + 6, places[number_of] + 4, fit(name or "-", right - 10, 10), 10)
    _axis_title(svg, x_label, frame.x + frame.width / 2, svg.height - 8)
    _axis_title(svg, y_label, 12, frame.y + frame.height / 2, rotate=True, room=frame.height)


DENSE = 800  # dots of a scatter from which they are smaller, lighter, without a ring


def _scatter(svg: _Svg, spec: Dict[str, Any]) -> None:
    """[{x, y, series}]: dots of 4 px with a ring of the surface, three series at most (then "others")."""
    palette = svg.palette
    points = []
    for index, row in enumerate(spec.get("data") or []):
        x_value, y_value = _finite(row.get("x")), _finite(row.get("y"))
        if x_value is not None and y_value is not None:
            points.append((index, x_value, y_value, clean(row.get("series") or "")))
    top = _top(svg, spec)
    if not points:
        return
    names = list(dict.fromkeys(point[3] for point in points))
    several = len(names) > 1
    others = clean(spec.get("others_label") or "")
    x_label, y_label = spec.get("x_label") or "", spec.get("y_label") or ""
    right, bottom = (110 if several else 20), (46 if x_label else 34)
    frame = _frame(svg, top, 52, right, bottom)
    domain, values_ticks = _value_ticks(*_extent([point[2] for point in points]), frame.height, 50)
    frame = _frame(svg, top, _left_margin(values_ticks, y_label), right, bottom)
    y = Linear(domain, (frame.bottom, frame.y))
    x_domain = nice(*_extent([point[1] for point in points]))
    x = Linear(x_domain, (frame.x, frame.right))
    _grid_left(svg, frame, y, values_ticks)
    _axis_bottom(svg, frame, x, ticks(x_domain[0], x_domain[1], max(2, math.floor(frame.width / 80))), number)

    def color(name: str) -> str:
        if others and name == others:
            return palette["other"]
        return palette["series"][names.index(name) % len(palette["series"])]

    dense = len(points) > DENSE
    radius = 2.5 if dense else 4.0
    for index, x_value, y_value, name in points:
        px, py = x(x_value), y(y_value)
        attributes = {"cx": float(px), "cy": float(py), "r": _n(radius), "fill": color(name),
                      "fill-opacity": "0.6" if dense else "0.9"}
        if not dense:
            attributes.update({"stroke": palette["background"], "stroke-width": "1"})
        svg.element("circle", attributes)
        svg.mark("dot", px - radius, py - radius, 2 * radius, 2 * radius,
                 {"index": index, "series": name, "x": x_value, "y": y_value})
    if several:
        for position, name in enumerate(names):
            lx, ly = frame.right + 10, frame.y + 8 + position * 18
            svg.element("circle", {"cx": float(lx), "cy": float(ly), "r": "4", "fill": color(name)})
            svg.text(lx + 9, ly + 4, fit(name or "-", right - 23, 10), 10)
    _axis_title(svg, x_label, frame.x + frame.width / 2, svg.height - 8)
    _axis_title(svg, y_label, 12, frame.y + frame.height / 2, rotate=True, room=frame.height)


def _kpi(svg: _Svg, spec: Dict[str, Any]) -> None:
    data = [(index, row) for index, row in enumerate(spec.get("data") or [])
            if _finite(row.get("value")) is not None]
    top = _top(svg, spec)
    if not data:
        return
    frame = _frame(svg, top, 12, 12, 12)
    gap = 12
    columns = min(4, len(data), max(2, int((frame.width + gap) / 140)))
    rows = math.ceil(len(data) / columns)
    card_width = (frame.width - gap * (columns - 1)) / columns
    card_height = min(96, (frame.height - gap * (rows - 1)) / rows)
    for position, (index, row) in enumerate(data):
        left = frame.x + position % columns * (card_width + gap)
        top = frame.y + position // columns * (card_height + gap)
        svg.element("rect", {"x": float(left), "y": float(top), "width": float(card_width),
                             "height": float(card_height), "rx": "6",
                             "fill": "#f4f3ef" if svg.palette["background"] == "#ffffff" else "#262625"})
        written = number(row["value"])
        size = min(26.0, max(9.0, card_height * 0.36))
        while size > 9 and text_width(written, size, bold=True) > card_width - 24:
            size -= 1
        svg.text(left + 12, top + card_height * 0.46, fit(written, card_width - 24, size, bold=True), size,
                 fill=svg.palette["muted"] if row.get("others") else svg.palette["text"], weight="700")
        label_size = min(11.0, max(8.0, card_height * 0.22))
        svg.text(left + 12, top + card_height * 0.78,
                 fit(clean(row.get("label", "")), card_width - 24, label_size), label_size,
                 fill=svg.palette["muted"])
        svg.mark("kpi", left, top, card_width, card_height, dict(row, index=index))


def _tile_ink(color: str) -> str:
    channels = [int(color[offset:offset + 2], 16) / 255 for offset in (1, 3, 5)]
    linear = [channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4
              for channel in channels]
    luminance = sum(channel * weight for channel, weight in zip(linear, (0.2126, 0.7152, 0.0722)))
    return "#ffffff" if luminance < 0.179 else "#0b0b0b"


def _treemap(svg: _Svg, spec: Dict[str, Any]) -> None:
    data = [(index, row) for index, row in enumerate(spec.get("data") or [])
            if _finite(row.get("value")) is not None and row["value"] > 0]
    top = _top(svg, spec)
    if not data:
        return
    data.sort(key=lambda item: -item[1]["value"])
    largest = data[0][1]["value"]
    weights = [row["value"] / largest for _, row in data]
    total = sum(weights)
    frame = _frame(svg, top, 12, 12, 12)

    def tiles(start: int, stop: int, left: float, top: float, width: float, height: float) -> None:
        if stop - start > 1:
            weight = sum(weights[start:stop])
            if weight <= 0:
                return
            accumulated = weights[start]
            middle = start + 1
            while middle < stop - 1 and abs(accumulated + weights[middle] - weight / 2) < abs(accumulated - weight / 2):
                accumulated += weights[middle]
                middle += 1
            share = accumulated / weight
            if width >= height:
                first = width * share
                tiles(start, middle, left, top, first, height)
                tiles(middle, stop, left + first, top, width - first, height)
            else:
                first = height * share
                tiles(start, middle, left, top, width, first)
                tiles(middle, stop, left, top + first, width, height - first)
            return
        if width <= 3 or height <= 3:
            return
        index, row = data[start]
        left, top, width, height = left + 1.5, top + 1.5, width - 3, height - 3
        color = svg.palette["other"] if row.get("others") else svg.palette["series"][start % len(svg.palette["series"])]
        svg.element("rect", {"x": float(left), "y": float(top), "width": float(width), "height": float(height),
                             "rx": "3", "fill": color})
        ink = _tile_ink(color)
        if width > 44 and height > 18:
            svg.text(left + 7, top + 16, fit(clean(row.get("label", "")), width - 14, 11, bold=True),
                     11, fill=ink, weight="600")
        if width > 44 and height > 34:
            svg.text(left + 7, top + 31, fit(number(100 * (row["value"] / largest) / total, percent=True) + " %",
                                           width - 14, 10), 10, fill=ink)
        svg.mark("tile", left, top, width, height, dict(row, index=index))

    tiles(0, len(data), frame.x, frame.y, frame.width, frame.height)


KINDS = {"bar": _bar, "histogram": _histogram, "pie": _pie, "line": _line, "scatter": _scatter,
         "kpi": _kpi, "treemap": _treemap, "area": _line}


def _side(value: Any, default: int) -> int:
    number_value = _finite(value)
    return default if number_value is None else max(MIN_SIDE, min(MAX_SIDE, int(round(number_value))))


def render(spec: Dict[str, Any], width: Optional[int] = None, height: Optional[int] = None) -> Tuple[str, List[Mark]]:
    """``spec`` (``charts.chart_spec``) drawn: its SVG and its marks. ``width`` and ``height`` draw it at another size
    than the one asked (a card as wide as the dock); a chart of no data is its title alone."""
    width = _side(width if width is not None else spec.get("width"), 640)
    height = _side(height if height is not None else spec.get("height"), 400)
    svg = _Svg(width, height, spec["palette"])
    svg.element("rect", {"width": str(width), "height": str(height), "fill": spec["palette"]["background"]})
    draw = KINDS.get(spec.get("kind") or "")
    if draw is None:
        raise ValueError(f"no chart of kind {spec.get('kind')!r}")
    draw(svg, spec)
    return svg.write(), svg.marks
