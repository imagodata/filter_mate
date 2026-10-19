# -*- coding: utf-8 -*-
"""
Point Cloud EXPLORING Panel.

Shown in place of the vector exploring groups when the current layer is a
point cloud. Like the vector and raster panels, exactly one checkable group
is active (FilterMate 5 design): the classes, the attribute conditions or the
free expression restrict the kept points. Checking EXPRESSION starts from the
criteria of the group that was active, so classes and conditions can still be
combined there. The resulting subset expression becomes the source of
FILTERING.

ATTRIBUTES is a list of chained conditions on the attributes of the layer
(``Z between 10 and 50 OR Intensity >= 300``; AND binds tighter than OR),
with a "Returns" row (any, first, last, single) that keeps one return
condition. HEIGHT / DTM is its own group, not exclusive: the height above a
DTM computed with PDAL is always ANDed with the rest, whatever the active
group, and the group says it is a PDAL computation.

CLASSES lists the classes present in the layer first, each with a weight bar
proportional to its points, and the classes absent from it in a folded list;
the class pipette of the rail (the Identify button) checks the class clicked
on the map. The point counts and the current filter go to the selection strip
under EXPLORING, not to the panel (2026-10-18 audit).

The object detector of the rail is a tool of CLASSES too: a click keeps the
object under it (the cluster of points of its class, a building, a tree), or
every object of the cloud like it (similar objects, within area ratios). Each
object keeps its class; the classes of the objects are checked, the subset
string keeps the X / Y box of each object with its class, and the objects
themselves cut the source geometry of the cross filter (:meth:`zone_wkt`).
Editing the class list by hand drops the objects.

The panel only reads a ``PointCloudLayerSummary`` (and the DTM layer combo);
the state handling - criteria and expression building, presets, migration of
older states, count formatting - is done by pure functions of this module and
of ``core.domain.point_cloud_attributes``, testable without Qt.
"""
import math
from contextlib import contextmanager
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from qgis.PyQt.QtCore import QRect, Qt, QTimer, pyqtSignal
    from qgis.PyQt.QtGui import QColor, QIcon, QPixmap
    from qgis.PyQt.QtWidgets import (
        QCheckBox, QComboBox, QDoubleSpinBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
        QListWidget, QListWidgetItem, QMenu, QPlainTextEdit, QPushButton, QSizePolicy, QStyledItemDelegate,
        QToolButton, QVBoxLayout, QWidget,
    )
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    QWidget = object
    QStyledItemDelegate = object

    def pyqtSignal(*_args):
        """Placeholder signal when Qt is unavailable."""
        return None

try:
    from qgis.gui import QgsCollapsibleGroupBox, QgsMapLayerComboBox
except ImportError:
    QgsCollapsibleGroupBox = None
    QgsMapLayerComboBox = None

from ....core.domain import point_cloud_attributes as pc_attributes
from ....core.domain.point_cloud_attributes import (
    JOIN_AND, JOIN_OR, OP_BETWEEN, OP_EQUAL, OP_GREATER_OR_EQUAL, OP_LESS, OP_LESS_OR_EQUAL,
    OPERATOR_SYMBOLS, OPERATORS, attribute_info, condition_attributes, conditions_criteria,
    conditions_have_or, parse_condition, parse_conditions,
)
from ....core.domain.point_cloud_filter_criteria import (
    PointCloudFilterCriteria, PointCloudLayerSummary, format_number,
)
from ....core.domain.point_cloud_support import (
    ASPRS_CLASS_NAMES, CLASS_PRESETS, NOISE_CLASSES, asprs_class_label,
)
from .histogram_widget import normalize_range, spin_bounds

try:
    from ...styles.mockup_design import SPACING as _SPACING
    GAP = int(_SPACING['fm_gap'])
except Exception:  # the design module is not importable (tests without the ui package)
    GAP = 6

Bound = Optional[float]

CLASSIFICATION_ATTRIBUTE = pc_attributes.CLASSIFICATION
X_ATTRIBUTE = pc_attributes.X
Y_ATTRIBUTE = pc_attributes.Y
ZONE_ATTRIBUTES = (X_ATTRIBUTE, Y_ATTRIBUTE)
Z_ATTRIBUTE = pc_attributes.Z
DEFAULT_PICK_TOLERANCE = 5.0  # value pipette: ± percent of the observed range of the attribute
INTENSITY_ATTRIBUTE = pc_attributes.INTENSITY
RETURN_NUMBER_ATTRIBUTE = pc_attributes.RETURN_NUMBER
NUMBER_OF_RETURNS_ATTRIBUTE = pc_attributes.NUMBER_OF_RETURNS
HAG_ATTRIBUTE = pc_attributes.HEIGHT_ABOVE_GROUND

WITHOUT_NOISE_PRESET = "Without noise"
RETURN_FIRST = "first"
RETURN_LAST = "last"
RETURN_SINGLE = "single"
# Return shortcuts: the condition each one inserts (``low`` is a number or another attribute).
RETURN_PRESETS: Dict[str, Dict[str, Any]] = {
    RETURN_FIRST: {"attribute": RETURN_NUMBER_ATTRIBUTE, "op": OP_EQUAL, "low": 1.0},
    RETURN_LAST: {"attribute": RETURN_NUMBER_ATTRIBUTE, "op": OP_EQUAL, "low": NUMBER_OF_RETURNS_ATTRIBUTE},
    RETURN_SINGLE: {"attribute": NUMBER_OF_RETURNS_ATTRIBUTE, "op": OP_EQUAL, "low": 1.0},
}
MAX_RETURN_NUMBERS = 15  # older states: ``return`` was a number 1-15 or a preset key
DEFAULT_HAG_MIN = 2.0
SPIN_MIN_WIDTH = 64
COMBO_MIN_WIDTH = 48
DEBOUNCE_MS = 250

# Fixed swatch per class: ground brown, vegetation greens, building red,
# water blue, noise magenta, wires and towers yellow / orange.
CLASS_COLORS: Dict[int, str] = {
    0: "#9e9e9e", 1: "#bdbdbd", 2: "#a0703c", 3: "#b5d96b", 4: "#6cbf3f", 5: "#2e7d32",
    6: "#d9443a", 7: "#c050c0", 8: "#757575", 9: "#2f7fd8", 10: "#5d4037", 11: "#616161",
    12: "#757575", 13: "#f2c200", 14: "#f2a900", 15: "#e88a1a", 16: "#f2c200", 17: "#8d6e63",
    18: "#c050c0", 64: "#b04040", 65: "#c050c0", 66: "#cfd8dc", 67: "#e07a5f",
}
DEFAULT_CLASS_COLOR = "#9e9e9e"
CLASS_COUNT_ROLE = 0x0101  # Qt.UserRole + 1: points of the class, -1 when unknown
RETURN_ANY = "any"  # the "Returns" row: no return condition

# Object detector of the rail (CLASSES): what a click selects.
OBJECT_TARGET = "object"  # the object under the click (the cluster of points of its class)
SIMILAR_OBJECTS_TARGET = "similar_objects"  # every object of the cloud like the clicked one
OBJECT_TARGETS = (OBJECT_TARGET, SIMILAR_OBJECTS_TARGET)
DEFAULT_SIMILAR_RATIO = (0.5, 2.0)  # area of a similar object: x 0.5 to x 2 the clicked one
# Above this many objects the subset string keeps one X / Y box per class (the source geometry of the
# cross filter stays exact: it is cut by the objects themselves; the panel and the strip say it). QGIS
# evaluates the subset for every point it decodes: the boxes are grouped by class, the class tested
# first, so a point of another class costs one comparison and a point of the class about two a box
# (X >= xmin fails for the boxes on one side, X <= xmax on the other), with the AND / OR of the
# point cloud expressions evaluated lazily (C++ && / ||). 64 boxes of buildings (10 % of a LiDAR HD
# tile) then cost about 14 comparisons a point, less than 24 boxes each testing its class (about 28).
MAX_OBJECT_BOXES = 64
# Decimals of the X / Y bounds of a box: 1e-9 degree is 0.1 mm (6 decimals were 0.1 m in a geographic CRS).
BOX_DECIMALS = 9


# ---------------------------------------------------------------------------
# Pure helpers (no Qt)
# ---------------------------------------------------------------------------

def class_color(code: int) -> str:
    """Swatch colour (hex) of an ASPRS / LiDAR HD class."""
    return CLASS_COLORS.get(int(code), DEFAULT_CLASS_COLOR)


def format_count(count: Optional[int]) -> str:
    """Point count with a k / M / G suffix (``14_100_000`` -> ``"14.1 M"``); ``""`` when unknown."""
    if count is None or count < 0:
        return ""
    count = int(count)
    if count < 1000:
        return str(count)
    for scale, suffix in ((1e3, "k"), (1e6, "M"), (1e9, "G")):
        value = round(count / scale, 1)
        if value < 1000 or suffix == "G":
            return f"{value:.1f} {suffix}"
    return str(count)


def format_point_counts(kept: Optional[int], total: Optional[int]) -> str:
    """``"9.8 M / 38.4 M (25.5 %)"``; only the kept count when the total is unknown, ``""`` without kept count."""
    if kept is None or kept < 0:
        return ""
    text = format_count(kept)
    if total is not None and total > 0:
        text += f" / {format_count(total)} ({kept / total * 100:.1f} %)"
    return text


def class_item_label(code: int, count: Optional[int]) -> str:
    """List entry of a class: ``"2 - Ground (14.1 M)"``, without count when unknown."""
    counted = format_count(count)
    label = asprs_class_label(int(code))
    return f"{label} ({counted})" if counted else label


def preset_codes(name: str, present_codes: Iterable[int]) -> Tuple[int, ...]:
    """Codes of the list checked by a preset, in list order.

    Args:
        name: A ``CLASS_PRESETS`` key, or ``WITHOUT_NOISE_PRESET`` (every
            present class except ``NOISE_CLASSES``).
        present_codes: Codes shown in the class list.

    Returns:
        The preset codes that are present; empty for an unknown preset.
    """
    present = [int(code) for code in present_codes]
    if name == WITHOUT_NOISE_PRESET:
        return tuple(code for code in present if code not in NOISE_CLASSES)
    wanted = set(CLASS_PRESETS.get(name, ()))
    return tuple(code for code in present if code in wanted)


def split_classes(classes: Iterable[Tuple[int, int]]) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
    """``(present, absent)`` classes of a layer: a class counted 0 is absent, an uncounted one (-1) is present.

    The present classes keep their order; the absent ones are folded away by the panel.
    """
    present, absent = [], []
    for code, count in classes:
        (absent if int(count) == 0 else present).append((int(code), int(count)))
    return present, absent


def weight_share(count: int, maximum: int) -> float:
    """Length (0-1) of the weight bar of a class against the most populated one; 0 without counts."""
    if count is None or maximum is None or int(count) <= 0 or int(maximum) <= 0:
        return 0.0
    return min(1.0, int(count) / int(maximum))


def value_condition(attribute: str, value: float, tolerance_percent: float,
                    bounds: Optional[Tuple[float, float]], join: str = JOIN_AND) -> Dict[str, Any]:
    """Condition of the value pipette: ``attribute between value - d and value + d``.

    ``d`` is ``tolerance_percent`` of the observed range of the attribute (``bounds``); without
    bounds, of the value itself (at least 1).
    """
    value = float(value)
    if bounds is not None and bounds[1] > bounds[0]:
        span = float(bounds[1]) - float(bounds[0])
    else:
        span = max(abs(value), 1.0)
    delta = round(max(0.0, float(tolerance_percent)) / 100.0 * span, 6)
    return parse_condition({"attribute": attribute, "op": OP_BETWEEN, "low": value - delta, "high": value + delta,
                            "join": join})


def zone_conditions(xmin: float, ymin: float, xmax: float, ymax: float) -> List[Dict[str, Any]]:
    """The two conditions of a rectangle drawn on the map: ``X between`` and ``Y between``, ANDed."""
    return parse_conditions([
        {"attribute": X_ATTRIBUTE, "op": OP_BETWEEN, "low": min(xmin, xmax), "high": max(xmin, xmax), "join": JOIN_AND},
        {"attribute": Y_ATTRIBUTE, "op": OP_BETWEEN, "low": min(ymin, ymax), "high": max(ymin, ymax), "join": JOIN_AND},
    ])


def inverted_codes(present_codes: Iterable[int], checked_codes: Iterable[int]) -> Tuple[int, ...]:
    """Codes of the list that are NOT checked (the "Invert" quick selection), in list order."""
    checked = {int(code) for code in checked_codes}
    return tuple(int(code) for code in present_codes if int(code) not in checked)


def picked_class_codes(checked_codes: Iterable[int], code: int, extend: bool) -> Tuple[int, ...]:
    """Classes checked after a pipette click: the picked class alone, or added to the others with Ctrl."""
    return tuple(sorted({int(code), *checked_codes})) if extend else (int(code),)


def _parse_box(value: Any) -> Optional[List[float]]:
    """``[xmin, ymin, xmax, ymax]`` of finite numbers (sides ordered), None when invalid."""
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    numbers = [_optional_float(item) for item in value]
    if any(number is None for number in numbers):
        return None
    xmin, ymin, xmax, ymax = numbers
    return [min(xmin, xmax), min(ymin, ymax), max(xmin, xmax), max(ymin, ymax)]


def _parse_code(value: Any) -> Optional[int]:
    number = _optional_float(value)
    return int(number) if number is not None and number.is_integer() and 0 <= number <= 255 else None


def _parse_object_item(value: Any) -> Optional[Dict[str, Any]]:
    """A clicked object: ``{"x", "y", "code", "box", "wkt", "truncated"}`` (layer CRS), None when invalid."""
    if not isinstance(value, dict):
        return None
    x, y, code, box = _optional_float(value.get("x")), _optional_float(value.get("y")), _parse_code(value.get("code")), \
        _parse_box(value.get("box"))
    if x is None or y is None or code is None or box is None:
        return None
    wkt = value.get("wkt")
    return {"x": x, "y": y, "code": code, "box": box, "wkt": wkt if isinstance(wkt, str) else "",
            "truncated": bool(value.get("truncated", False))}


def _parse_detected(value: Any) -> Optional[Dict[str, Any]]:
    """What the detection found: ``{"wkt", "boxes", "count", "area", "truncated"}``, None when nothing was read."""
    if not isinstance(value, dict):
        return None
    boxes = []
    for entry in value.get("boxes") or ():
        if isinstance(entry, (list, tuple)) and len(entry) == 5:
            code, box = _parse_code(entry[0]), _parse_box(entry[1:])
            if code is not None and box is not None:
                boxes.append([code, *box])
    count = _optional_float(value.get("count"))
    area = _optional_float(value.get("area"))
    wkt = value.get("wkt")
    return {"wkt": wkt if isinstance(wkt, str) else "", "boxes": boxes,
            "count": int(count) if count is not None and count >= 0 else None,
            "area": area if area is not None and area >= 0 else None, "truncated": bool(value.get("truncated", False))}


def parse_objects_state(value: Any) -> Dict[str, Any]:
    """Normalise the object detector part of a panel state (idempotent).

    ``{"target": "object" | "similar_objects", "ratio": [low, high], "items": [clicked objects],
    "detected": what was found for them or None}``.
    """
    value = value if isinstance(value, dict) else {}
    target = value.get("target")
    low, high = _parse_bounds(value.get("ratio"))
    ratio = [low, high] if low is not None and high is not None and low > 0 else list(DEFAULT_SIMILAR_RATIO)
    items = [item for item in (_parse_object_item(entry) for entry in value.get("items") or ()) if item is not None]
    return {
        "target": target if target in OBJECT_TARGETS else OBJECT_TARGET,
        "ratio": ratio,
        "items": items,
        "detected": _parse_detected(value.get("detected")) if items else None,
    }


def box_coordinate(value: float) -> str:
    """A bound of a box, :data:`BOX_DECIMALS` decimals without trailing zeros (``652000``, ``2.123456789``)."""
    text = f"{float(value):.{BOX_DECIMALS}f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-", "-0") else text


def box_clause(box: Sequence[float]) -> str:
    """``X >= .. AND X <= .. AND Y >= .. AND Y <= ..``: the points of a box ``[xmin, ymin, xmax, ymax]``."""
    xmin, ymin, xmax, ymax = box
    return (f"{X_ATTRIBUTE} >= {box_coordinate(xmin)} AND {X_ATTRIBUTE} <= {box_coordinate(xmax)} AND "
            f"{Y_ATTRIBUTE} >= {box_coordinate(ymin)} AND {Y_ATTRIBUTE} <= {box_coordinate(ymax)}")


def class_boxes(boxes: Iterable[Sequence[float]]) -> List[List[float]]:
    """One ``[code, xmin, ymin, xmax, ymax]`` box per class, covering its boxes, in class order."""
    merged: Dict[int, List[float]] = {}
    for code, xmin, ymin, xmax, ymax in boxes:
        box = merged.get(int(code))
        merged[int(code)] = [min(box[0], xmin), min(box[1], ymin), max(box[2], xmax), max(box[3], ymax)] if box \
            else [xmin, ymin, xmax, ymax]
    return [[code, *merged[code]] for code in sorted(merged)]


def object_expression(boxes: Sequence[Sequence[float]], limit: int = MAX_OBJECT_BOXES) -> str:
    """Subset of the points in the boxes of the objects, each with its class (``[code, xmin, ymin, xmax, ymax]``).

    The boxes of a class are grouped behind its class test (``Classification = 6 AND ((box) OR (box))``),
    the classes ORed in the order of their first object, each parenthesised when there are several;
    over ``limit`` objects (similar objects), one box per class (:func:`boxes_merged`). ``""`` without a box.
    """
    boxes = list(boxes)
    if len(boxes) > limit:
        boxes = class_boxes(boxes)
    groups: Dict[int, List[str]] = {}
    for entry in boxes:
        groups.setdefault(int(entry[0]), []).append(box_clause(entry[1:]))
    clauses = []
    for code, group in groups.items():
        inner = group[0] if len(group) == 1 else "(" + " OR ".join(f"({clause})" for clause in group) + ")"
        clauses.append(f"{CLASSIFICATION_ATTRIBUTE} = {code} AND {inner}")
    if len(clauses) == 1:
        return clauses[0]
    return " OR ".join(f"({clause})" for clause in clauses)


def boxes_merged(objects: Dict[str, Any], limit: int = MAX_OBJECT_BOXES) -> bool:
    """Whether the subset keeps one box per class for a parsed objects state: it shows the whole class in it."""
    return len(objects_boxes(objects)) > limit


def objects_boxes(objects: Dict[str, Any]) -> List[List[float]]:
    """Boxes the subset string keeps for a parsed objects state: those found, else those of the clicks."""
    if not objects["items"]:
        return []
    detected = objects["detected"]
    if detected is not None and detected["boxes"]:
        return detected["boxes"]
    return [[item["code"], *item["box"]] for item in objects["items"]]


def class_selection_summary(checked: int, shown: int, kept_points: Optional[int], total_points: Optional[int]) -> str:
    """Line under the class list: ``"3 of 12 classes · 9.8 M / 38.4 M points (25.5 %)"``.

    The points are those of the checked classes, when every class of the list has a count.
    """
    text = f"{checked} / {shown}"
    counted = format_point_counts(kept_points, total_points)
    return f"{text} · {counted}" if counted else text


def object_summary(count: int, area: Optional[float], truncated: bool, translate: Any = str, merged: bool = False) -> str:
    """Line under the class list while the detector holds objects: ``"3 object(s) · 125 m²"``, ``"… · cut"``.

    ``merged``: the subset keeps one box per class (:func:`boxes_merged`), said so: the preview and
    the filtered cloud show the whole class in that box, not the objects alone.
    """
    try:
        from ..selection_strip import objects_text
        text = objects_text(count, area, translate)
    except ImportError:  # the widgets package is not importable (tests of this module alone)
        text = translate("{0} object(s)").format(int(count))
    if truncated:
        text += " · " + translate("cut at the window read")
    if merged:
        text += " · " + translate("shown as the whole class in their box")
    return text


def attribute_available(attributes: Sequence[str], name: str) -> bool:
    """True when ``name`` is listed, or when no attribute is listed at all (unknown schema)."""
    return not attributes or name in attributes


def summary_bounds(summary: Any, name: str) -> Optional[Tuple[float, float]]:
    """Exact observed ``(minimum, maximum)`` of an attribute, None when unknown or invalid."""
    try:
        observed = summary.range_of(name)
    except AttributeError:
        return None
    if observed is None or observed.minimum is None or observed.maximum is None:
        return None
    low, high = float(observed.minimum), float(observed.maximum)
    if not (math.isfinite(low) and math.isfinite(high)) or low > high:
        return None
    return low, high


def compose_expression(base: str, hag_min: Optional[float], wrap: bool = False) -> str:
    """Append ``HeightAboveGround >= hag_min`` to ``base`` when a height is given.

    Args:
        base: Expression of the other criteria.
        hag_min: Minimum height above the DTM, None for no height clause.
        wrap: Parenthesise ``base`` (free user text may contain ``OR``).
    """
    base = (base or "").strip()
    if hag_min is None:
        return base
    clause = f"{HAG_ATTRIBUTE} >= {format_number(hag_min)}"
    if not base:
        return clause
    return f"({base}) AND {clause}" if wrap else f"{base} AND {clause}"


def _optional_float(value: Any) -> Bound:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _parse_bounds(value: Any) -> Tuple[Bound, Bound]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None, None
    low, high = _optional_float(value[0]), _optional_float(value[1])
    if low is not None and high is not None and low > high:
        low, high = high, low
    return low, high


def _parse_return(value: Any) -> Any:
    if isinstance(value, str) and value in RETURN_PRESETS:
        return value
    if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= MAX_RETURN_NUMBERS:
        return value
    return None


def return_presets_available(attributes: Sequence[str]) -> Tuple[str, ...]:
    """Return shortcuts usable with the attributes of a layer (every one when they are unknown).

    Last compares ``ReturnNumber`` with ``NumberOfReturns`` and needs both.
    """
    has_number = attribute_available(attributes, RETURN_NUMBER_ATTRIBUTE)
    has_count = attribute_available(attributes, NUMBER_OF_RETURNS_ATTRIBUTE)
    available = {RETURN_FIRST: has_number, RETURN_LAST: has_number and has_count, RETURN_SINGLE: has_count}
    return tuple(key for key in RETURN_PRESETS if available[key])


def return_preset_condition(key: str, join: str = JOIN_AND) -> Dict[str, Any]:
    """Parsed condition inserted by a return shortcut."""
    return pc_attributes.parse_condition(dict(RETURN_PRESETS[key], join=join))


def return_preset_of(condition: Any) -> Optional[str]:
    """Key of the return shortcut ``condition`` stands for, None for any other condition."""
    parsed = pc_attributes.parse_condition(condition)
    if parsed is None:
        return None
    for key, preset in RETURN_PRESETS.items():
        if (parsed["attribute"], parsed["op"], parsed["low"]) == (preset["attribute"], preset["op"], preset["low"]):
            return key
    return None


def legacy_conditions(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Conditions of a state saved before the condition list (``z``, ``intensity``, ``return`` keys).

    ``z`` and a checked ``intensity`` become ``between`` conditions, ``return``
    the condition of its shortcut (``ReturnNumber = n`` for a number); all joined by AND.
    """
    conditions: List[Dict[str, Any]] = []
    ranges = [(Z_ATTRIBUTE, state.get("z"))]
    if state.get("intensity_enabled"):
        ranges.append((INTENSITY_ATTRIBUTE, state.get("intensity")))
    for attribute, bounds in ranges:
        low, high = _parse_bounds(bounds)
        if low is not None or high is not None:
            conditions.append({"attribute": attribute, "op": OP_BETWEEN, "low": low, "high": high})
    choice = _parse_return(state.get("return"))
    if choice in RETURN_PRESETS:
        conditions.append(dict(RETURN_PRESETS[choice]))
    elif choice is not None:
        conditions.append({"attribute": RETURN_NUMBER_ATTRIBUTE, "op": OP_EQUAL, "low": float(choice)})
    return parse_conditions(conditions)


def drop_open_bounds(condition: Dict[str, Any], minimum: Bound, maximum: Bound) -> Dict[str, Any]:
    """Copy of a parsed condition without the bounds that keep every point.

    A ``between`` or ``>=`` bound at or below ``minimum``, a ``between`` or
    ``<=`` bound at or above ``maximum`` becomes None (the condition may then
    be incomplete); the other operators are left as they are.
    """
    result = dict(condition)
    op, low = result["op"], result["low"]
    if op == OP_BETWEEN:
        result["low"], result["high"] = normalize_range(low, result["high"], minimum, maximum)
    elif op == OP_GREATER_OR_EQUAL and not isinstance(low, str):
        result["low"] = normalize_range(low, None, minimum, maximum)[0]
    elif op == OP_LESS_OR_EQUAL and not isinstance(low, str):
        result["low"] = normalize_range(None, low, minimum, maximum)[1]
    return result


def parse_point_cloud_state(state: Any) -> Dict[str, Any]:
    """Normalise a saved panel state (see :meth:`PointCloudExploringPanel.state`).

    Missing or invalid entries get their default; a state without
    ``conditions`` (saved by an older version) has its ``z``, ``intensity``
    and ``return`` keys migrated to conditions. The function is idempotent.
    """
    state = state if isinstance(state, dict) else {}
    classes = set()
    for code in state.get("classes") or ():
        number = _optional_float(code)
        if number is not None and number.is_integer() and 0 <= number <= 255:
            classes.add(int(number))
    conditions = state.get("conditions")
    hag_min = _optional_float(state.get("hag_min"))
    hag_layer_id = state.get("hag_layer_id")
    pick_tolerance = _optional_float(state.get("pick_tolerance"))
    pick_attribute = state.get("pick_attribute")
    zone_wkt = state.get("zone_wkt")
    return {
        "zone_wkt": zone_wkt if isinstance(zone_wkt, str) else "",
        "pick_attribute": pick_attribute if isinstance(pick_attribute, str) and pick_attribute else Z_ATTRIBUTE,
        "pick_tolerance": DEFAULT_PICK_TOLERANCE if pick_tolerance is None or pick_tolerance < 0 else pick_tolerance,
        "layer_id": state.get("layer_id"),
        "classes_enabled": bool(state.get("classes_enabled", True)),
        "classes": sorted(classes),
        "ranges_enabled": bool(state.get("ranges_enabled", False)),
        "conditions": parse_conditions(conditions) if isinstance(conditions, (list, tuple)) else legacy_conditions(state),
        "hag_enabled": bool(state.get("hag_enabled", False)),
        "hag_min": DEFAULT_HAG_MIN if hag_min is None else hag_min,
        "hag_layer_id": hag_layer_id if isinstance(hag_layer_id, str) and hag_layer_id else None,
        "expression_enabled": bool(state.get("expression_enabled", False)),
        "expression": str(state.get("expression") or ""),
        "apply_to_tiles": bool(state.get("apply_to_tiles", False)),
        "objects": parse_objects_state(state.get("objects")),
    }


def _object_clause(parsed: Dict[str, Any]) -> str:
    """Subset clause of the detected objects of a parsed state while CLASSES is checked, ``""`` otherwise."""
    if not parsed["classes_enabled"]:
        return ""
    return object_expression(objects_boxes(parsed["objects"]))


def build_point_cloud_criteria(state: Any) -> PointCloudFilterCriteria:
    """Criteria of the checked group (the panel keeps one): classes, or attribute conditions.

    The state format still allows several checked groups (older saved states);
    they are combined here, the panel narrows them to one on restore.

    An AND chain of conditions gives ranges (``between``, ``>=``, ``<=``) and
    extra clauses (the other operators); a chain with an OR is one extra
    clause. Objects detected in CLASSES replace their classes by the box of
    each object, with its class (:func:`object_expression`). The height above
    the DTM is not part of the criteria (see :func:`build_point_cloud_expression`).
    """
    parsed = parse_point_cloud_state(state)
    objects = _object_clause(parsed)
    codes = parsed["classes"] if parsed["classes_enabled"] and not objects else ()
    ranges, extra_clauses = conditions_criteria(parsed["conditions"]) if parsed["ranges_enabled"] else ((), ())
    return PointCloudFilterCriteria(
        classification_codes=frozenset(codes),
        ranges=ranges,
        extra_clauses=((objects,) if objects else ()) + tuple(extra_clauses),
    )


def generated_expression(state: Any) -> str:
    """Expression of the classes and conditions of a state, without the typed one nor the height.

    A lone extra clause (an OR chain, ``ReturnNumber = 1``) is not parenthesised.
    """
    criteria = build_point_cloud_criteria(state)
    if len(criteria.extra_clauses) == 1 and not (criteria.classification_codes or criteria.ranges):
        return criteria.extra_clauses[0]
    return criteria.to_subset_string()


def hag_from_state(state: Any, available: bool = True) -> Optional[Tuple[str, float]]:
    """``(DTM layer id, minimum height)`` when the height filter is usable and on, else None.

    2026-10-18: HEIGHT / DTM is its own group, ANDed whatever the active group; it no
    longer needs ATTRIBUTES to be the active one.
    """
    parsed = parse_point_cloud_state(state)
    if not (available and parsed["hag_enabled"] and parsed["hag_layer_id"]):
        return None
    return parsed["hag_layer_id"], parsed["hag_min"]


def build_point_cloud_expression(state: Any, hag_available: bool = True) -> str:
    """Subset expression of a panel state.

    The typed expression when the EXPRESSION group is checked, else the
    criteria of the other groups; ``HeightAboveGround >= x`` is ANDed in
    both cases when the HEIGHT / DTM group is on (an OR chain is parenthesised first).
    """
    parsed = parse_point_cloud_state(state)
    if parsed["expression_enabled"]:
        base, wrap = parsed["expression"], True
    else:
        base = generated_expression(parsed)
        wrap = (parsed["ranges_enabled"] and conditions_have_or(parsed["conditions"])) or " OR " in _object_clause(parsed)
    hag = hag_from_state(parsed, hag_available)
    return compose_expression(base, None if hag is None else hag[1], wrap)


def _raster_layer_filter() -> Any:
    """``QgsMapLayerProxyModel`` filter keeping raster layers, None when unavailable."""
    try:
        try:
            from qgis.gui import QgsMapLayerProxyModel
        except ImportError:
            from qgis.core import QgsMapLayerProxyModel
        return QgsMapLayerProxyModel.Filter.RasterLayer
    except (ImportError, AttributeError):
        return None


# Rendered images have no elevations. Virtual/PostGIS inputs also lack a file
# PDAL can open directly. WCS stays excluded here until HAG materializes it
# to a local file, even though value raster exploring supports it.
NON_FILE_RASTER_PROVIDERS = ('wms', 'wcs', 'arcgismapserver', 'virtualraster', 'postgresraster')


def _dtm_rasters_only(combo: Any) -> None:
    """DTM list: PDAL-readable files only, excluding WCS and rendered services."""
    try:
        from ....adapters.qgis.point_cloud_capability import exclude_non_analysis_rasters
        exclude_non_analysis_rasters(combo)
    except ImportError:
        pass
    try:
        excluded = list(combo.excludedProviders())
        combo.setExcludedProviders(excluded + [key for key in NON_FILE_RASTER_PROVIDERS if key not in excluded])
    except (AttributeError, TypeError, RuntimeError):
        pass
    try:
        from qgis.core import QgsProject
        from ....core.domain.source_capability import classify
        excepted = list(combo.exceptedLayerList())
        # A GDAL provider can wrap rendered tiles or WCS instead of a file.
        # Classify its URI only: this picker must never read remote pixels.
        for layer in QgsProject.instance().mapLayers().values():
            if layer.providerType().lower() != 'gdal':
                continue
            capability = classify('gdal', layer.source(), is_raster=True)
            if (not capability.has_raw_values or capability.is_remote_service) and layer not in excepted:
                excepted.append(layer)
        combo.setExceptedLayerList(excepted)
    except (ImportError, AttributeError, TypeError, RuntimeError):
        pass


@contextmanager
def _signals_blocked(*widgets):
    """Block the signals of ``widgets`` for the duration of the block."""
    previous = [widget.blockSignals(True) for widget in widgets]
    try:
        yield
    finally:
        for widget, was_blocked in zip(widgets, previous):
            widget.blockSignals(was_blocked)


def _make_spin(parent: Any, decimals: int, tip: str) -> Any:
    spin = QDoubleSpinBox(parent)
    spin.setDecimals(decimals)
    spin.setRange(*spin_bounds(None, None, decimals))
    spin.setKeyboardTracking(False)
    spin.setToolTip(tip)
    spin.setAccessibleName(tip)
    spin.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    # The size hint covers the widest bound (±1e9): far too wide for a 440 px dock.
    spin.setMinimumWidth(SPIN_MIN_WIDTH)
    return spin


class ClassWeightDelegate(QStyledItemDelegate):
    """Draws, under the text of a class item, a bar as long as its share of the most populated class."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.maximum = 0

    def paint(self, painter, option, index):  # noqa: N802 - Qt override
        count = index.data(CLASS_COUNT_ROLE)
        try:
            share = weight_share(int(count), self.maximum)
        except (TypeError, ValueError):
            share = 0.0
        if share > 0:
            rect = option.rect
            left = rect.left() + 44  # after the check box and the swatch
            width = int((rect.width() - 48) * share)
            if width > 1:
                painter.save()
                colour = QColor(option.palette.highlight().color())
                colour.setAlpha(70 if index.data(Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked else 32)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(colour)
                painter.drawRoundedRect(QRect(left, rect.top() + 3, width, rect.height() - 6), 3, 3)
                painter.restore()
        super().paint(painter, option, index)


def _make_combo(parent: Any, minimum_width: int, tip: str) -> Any:
    combo = QComboBox(parent)
    combo.setToolTip(tip)
    combo.setAccessibleName(tip)
    # The size hint follows the longest item: the minimum keeps the row inside a narrow dock.
    combo.setMinimumWidth(minimum_width)
    return combo


# ---------------------------------------------------------------------------
# Widgets
# ---------------------------------------------------------------------------

class PointCloudConditionRow(QWidget):
    """One condition of the ATTRIBUTES group, on two lines for a narrow dock.

    ``[AND|OR] [attribute] [operator] [✕]`` then ``[low] – [high]`` for
    ``between``, ``[value|attribute] [value]`` for the other operators: the
    operand is a number, or another attribute (``ReturnNumber =
    NumberOfReturns``). The join combo is hidden on the first row.

    The panel gives the attribute choices and their observed bounds; the row
    edits one parsed condition (see ``core.domain.point_cloud_attributes``).

    Signals:
        changed(): The condition was edited.
        removeRequested(): The ✕ button was clicked.
    """

    changed = pyqtSignal()
    removeRequested = pyqtSignal()

    def __init__(self, choices: Sequence[Tuple[str, str]], bounds: Dict[str, Tuple[float, float]], parent=None):
        """Build the row.

        Args:
            choices: ``(attribute name, display label)`` of the attributes offered.
            bounds: Observed ``(minimum, maximum)`` per attribute name, when known.
            parent: Parent widget (the condition holder of the ATTRIBUTES group).
        """
        super().__init__(parent)
        self._bounds = dict(bounds)
        self.setObjectName("widget_point_cloud_condition")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        top = QHBoxLayout()
        top.setSpacing(4)
        self._join_combo = _make_combo(self, COMBO_MIN_WIDTH, self.tr("Link with the previous condition"))
        self._join_combo.setObjectName("comboBox_point_cloud_condition_join")
        self._join_combo.addItem(self.tr("AND"), JOIN_AND)
        self._join_combo.addItem(self.tr("OR"), JOIN_OR)
        self._attribute_combo = _make_combo(self, SPIN_MIN_WIDTH, self.tr("Attribute"))
        self._attribute_combo.setObjectName("comboBox_point_cloud_condition_attribute")
        self._attribute_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._op_combo = _make_combo(self, COMBO_MIN_WIDTH, self.tr("Comparison"))
        self._op_combo.setObjectName("comboBox_point_cloud_condition_operator")
        for op in OPERATORS:
            self._op_combo.addItem(self.tr("between") if op == OP_BETWEEN else OPERATOR_SYMBOLS[op], op)
        self._remove_button = QPushButton("✕", self)
        self._remove_button.setObjectName("pushButton_point_cloud_remove_condition")
        self._remove_button.setToolTip(self.tr("Remove this condition"))
        self._remove_button.setAccessibleName(self.tr("Remove this condition"))
        for widget in (self._join_combo, self._attribute_combo, self._op_combo, self._remove_button):
            top.addWidget(widget)
        layout.addLayout(top)

        bottom = QHBoxLayout()
        bottom.setSpacing(4)
        self._operand_combo = _make_combo(self, SPIN_MIN_WIDTH, self.tr("Compare with a value or another attribute"))
        self._operand_combo.setObjectName("comboBox_point_cloud_condition_operand")
        self._operand_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._operand_combo.addItem(self.tr("value"), None)
        self._low_spin = _make_spin(self, pc_attributes.DEFAULT_DECIMALS, self.tr("Value"))
        self._low_spin.setObjectName("doubleSpinBox_point_cloud_condition_low")
        self._dash = QLabel("–", self)
        self._high_spin = _make_spin(self, pc_attributes.DEFAULT_DECIMALS, self.tr("Highest value kept"))
        self._high_spin.setObjectName("doubleSpinBox_point_cloud_condition_high")
        for widget in (self._operand_combo, self._low_spin, self._dash, self._high_spin):
            bottom.addWidget(widget)
        layout.addLayout(bottom)

        for name, label in choices:
            self._attribute_combo.addItem(label, name)
            self._attribute_combo.setItemData(self._attribute_combo.count() - 1, name, Qt.ItemDataRole.ToolTipRole)
            self._operand_combo.addItem(label, name)

        self._join_combo.currentIndexChanged.connect(self._emit_changed)
        self._attribute_combo.currentIndexChanged.connect(self._on_attribute_changed)
        self._op_combo.currentIndexChanged.connect(self._on_op_changed)
        self._operand_combo.currentIndexChanged.connect(self._on_operand_changed)
        self._low_spin.valueChanged.connect(self._on_low_changed)
        self._high_spin.valueChanged.connect(self._on_high_changed)
        self._remove_button.clicked.connect(lambda _checked=False: self.removeRequested.emit())

    # === Public API ===

    def attribute(self) -> Optional[str]:
        """Name of the attribute of the condition."""
        return self._attribute_combo.currentData()

    def join(self) -> str:
        """``AND`` or ``OR``: link with the previous condition."""
        return self._join_combo.currentData() or JOIN_AND

    def set_first(self, first: bool) -> None:
        """Hide the join combo on the first row (nothing to link with); the first row is joined by AND."""
        if first:
            with _signals_blocked(self._join_combo):
                self._join_combo.setCurrentIndex(max(0, self._join_combo.findData(JOIN_AND)))
        self._join_combo.setVisible(not first)

    def set_condition(self, condition: Dict[str, Any]) -> None:
        """Show a parsed condition; its attribute and attribute operand must be offered. Does not emit."""
        widgets = (self._join_combo, self._attribute_combo, self._op_combo, self._operand_combo,
                   self._low_spin, self._high_spin)
        with _signals_blocked(*widgets):
            self._join_combo.setCurrentIndex(max(0, self._join_combo.findData(condition.get("join", JOIN_AND))))
            self._attribute_combo.setCurrentIndex(max(0, self._attribute_combo.findData(condition["attribute"])))
            self._calibrate()
            op = condition["op"]
            self._op_combo.setCurrentIndex(max(0, self._op_combo.findData(op)))
            low, high = condition.get("low"), condition.get("high")
            operand = low if isinstance(low, str) and op != OP_BETWEEN else None
            self._operand_combo.setCurrentIndex(max(0, self._operand_combo.findData(operand)) if operand else 0)
            if op == OP_BETWEEN:
                self._show_value(self._low_spin, low, at_maximum=False)
                self._show_value(self._high_spin, high, at_maximum=True)
            elif operand is None:
                self._show_value(self._low_spin, low, at_maximum=op in (OP_LESS_OR_EQUAL, OP_LESS))
        self._update_visibility()

    def condition(self) -> Dict[str, Any]:
        """The edited condition; a bound at the edge of the data means "no bound" (see :func:`drop_open_bounds`)."""
        name = self.attribute() or ""
        op = self._op_combo.currentData() or OP_BETWEEN
        operand = self._operand_combo.currentData()
        if op == OP_BETWEEN:
            low, high = float(self._low_spin.value()), float(self._high_spin.value())
        else:
            low, high = (operand if operand else float(self._low_spin.value())), None
        condition = {"attribute": name, "op": op, "low": low, "high": high, "join": self.join()}
        minimum, maximum = self._bounds.get(name) or (self._low_spin.minimum(), self._low_spin.maximum())
        return drop_open_bounds(condition, minimum, maximum)

    # === Internals ===

    def _emit_changed(self, *_args) -> None:
        self.changed.emit()

    def _calibrate(self) -> None:
        """Spin boxes on the decimals and the observed range of the attribute (rounded outwards)."""
        name = self.attribute() or ""
        info = attribute_info(name)
        bounds = self._bounds.get(name)
        low, high = spin_bounds(*(bounds or (None, None)), info.decimals)
        tip = (self.tr("Observed values: {0} to {1}").format(format_number(bounds[0]), format_number(bounds[1]))
               if bounds is not None else self.tr("No statistics for this attribute"))
        with _signals_blocked(self._low_spin, self._high_spin):
            for spin in (self._low_spin, self._high_spin):
                spin.setDecimals(info.decimals)
                spin.setRange(low, high)
                spin.setToolTip(tip)
            self._low_spin.setValue(low)
            self._high_spin.setValue(high)

    @staticmethod
    def _show_value(spin: Any, value: Any, at_maximum: bool) -> None:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            spin.setValue(float(value))
        else:
            spin.setValue(spin.maximum() if at_maximum else spin.minimum())

    def _update_visibility(self) -> None:
        between = self._op_combo.currentData() == OP_BETWEEN
        by_value = self._operand_combo.currentData() is None
        self._operand_combo.setVisible(not between)
        self._low_spin.setVisible(between or by_value)
        self._dash.setVisible(between)
        self._high_spin.setVisible(between)

    def _on_attribute_changed(self, *_args) -> None:
        # Another attribute: its own range, every value kept until a bound is moved.
        self._calibrate()
        with _signals_blocked(self._low_spin):
            op = self._op_combo.currentData()
            self._low_spin.setValue(self._low_spin.maximum() if op in (OP_LESS_OR_EQUAL, OP_LESS)
                                    else self._low_spin.minimum())
        self.changed.emit()

    def _on_op_changed(self, *_args) -> None:
        op = self._op_combo.currentData()
        with _signals_blocked(self._operand_combo, self._low_spin, self._high_spin):
            if op == OP_BETWEEN:
                self._operand_combo.setCurrentIndex(0)  # between compares with values only
                if self._low_spin.value() > self._high_spin.value():
                    self._high_spin.setValue(self._low_spin.value())
            elif op in (OP_LESS_OR_EQUAL, OP_LESS) and self._low_spin.value() <= self._low_spin.minimum():
                # An upper bound left at the minimum would keep (almost) nothing.
                self._low_spin.setValue(self._high_spin.value())
        self._update_visibility()
        self.changed.emit()

    def _on_operand_changed(self, *_args) -> None:
        self._update_visibility()
        self.changed.emit()

    def _on_low_changed(self, value: float) -> None:
        if self._op_combo.currentData() == OP_BETWEEN and value > self._high_spin.value():
            with _signals_blocked(self._high_spin):
                self._high_spin.setValue(value)
        self.changed.emit()

    def _on_high_changed(self, value: float) -> None:
        if value < self._low_spin.value():
            with _signals_blocked(self._low_spin):
                self._low_spin.setValue(value)
        self.changed.emit()


class PointCloudExploringPanel(QWidget):
    """EXPLORING panel of a point cloud: classes, attribute conditions, expression.

    Signals:
        criteriaChanged(): The criteria or the expression changed (debounced by 250 ms).
        applyToTilesToggled(bool): "Apply to the other tiles of the dataset" toggled.
    """

    criteriaChanged = pyqtSignal()
    applyToTilesToggled = pyqtSignal(bool)
    summaryChanged = pyqtSignal()  # point counts updated: the selection strip under EXPLORING follows
    groupChosen = pyqtSignal(str)  # the user made a group the active one ("classes", "ranges", "expression")
    # The objects of the detector must be read again (similar objects ratio edited), or were dropped
    # (the class list edited by hand): the controller reads them and calls set_detected_objects.
    objectsChanged = pyqtSignal()

    def __init__(self, parent=None):
        """Build the panel.

        Args:
            parent: Parent widget (the dock widget).
        """
        super().__init__(parent)
        self._summary: Optional[PointCloudLayerSummary] = None
        self._layer_id: Optional[str] = None
        self._condition_choices: List[Tuple[str, str]] = []  # (attribute name, display label)
        self._condition_bounds: Dict[str, Tuple[float, float]] = {}
        self._condition_rows: List[Any] = []
        self._hag_available = True
        self._hag_tooltip = ""
        self._custom_expression = ""
        self._zone_wkt = ""  # the shape drawn with the Zone tool (layer CRS), WKT; its box is in the conditions
        self._objects: Dict[str, Any] = parse_objects_state({})  # the object detector of the rail (CLASSES)
        self.setObjectName("widget_point_cloud_exploring_panel")
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(DEBOUNCE_MS)
        self._debounce.timeout.connect(self.criteriaChanged.emit)
        self._build_ui()
        self.reset()

    # === Construction ===

    def _make_group(self, title: str, object_name: str, checked: bool) -> Any:
        if QgsCollapsibleGroupBox is not None:
            group = QgsCollapsibleGroupBox(title, self)
            group.setSaveCollapsedState(False)
            group.setSaveCheckedState(False)
        else:
            group = QGroupBox(title, self)
        group.setObjectName(object_name)
        group.setFlat(True)
        group.setCheckable(True)
        group.setChecked(checked)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(GAP)
        return group

    @staticmethod
    def _menu_button(parent: Any, text: str, tip: str, object_name: str) -> Any:
        button = QToolButton(parent)
        button.setObjectName(object_name)
        button.setText(text)
        button.setToolTip(tip)
        button.setAccessibleName(tip)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.setMenu(QMenu(button))
        return button

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(GAP)
        layout.addWidget(self._build_classes_group())
        layout.addWidget(self._build_ranges_group())
        layout.addWidget(self._build_hag_group())
        layout.addWidget(self._build_expression_group())

        self._apply_tiles_check = QCheckBox(self.tr("Apply to the other tiles of the dataset"), self)
        self._apply_tiles_check.toggled.connect(self.applyToTilesToggled.emit)
        layout.addWidget(self._apply_tiles_check)
        self._counts = (None, None)
        self._current_subset = ""
        layout.addStretch()
        self._setup_exclusive_groups()  # last: criteria() reads widgets built above

    def _build_classes_group(self) -> Any:
        self._classes_group = self._make_group(self.tr("CLASSES"), "mGroupBox_point_cloud_classes", checked=True)
        self._classes_group.toggled.connect(self._changed)
        group_layout = self._classes_group.layout()

        preset_titles = {
            "Ground": self.tr("Ground"),
            "Vegetation": self.tr("Vegetation"),
            "Buildings": self.tr("Buildings"),
            "Above ground": self.tr("Above ground"),
            "Water": self.tr("Water"),
            WITHOUT_NOISE_PRESET: self.tr("Without noise"),
        }
        # One menu button (a button grid made the dock wider than 440 px), the same widget as the
        # "Thresholds" and "Insert" menus of the raster panel.
        head = QHBoxLayout()
        head.setSpacing(GAP)
        self._class_summary_label = QLabel("", self._classes_group)
        self._class_summary_label.setObjectName("label_point_cloud_class_summary")
        head.addWidget(self._class_summary_label, 1)
        self._quick_button = self._menu_button(self._classes_group, self.tr("Selection ▾"),
                                               self.tr("Quick class selection"),
                                               "toolButton_point_cloud_class_quick_selection")
        menu = self._quick_button.menu()
        self._preset_actions: Dict[str, Any] = {}
        for name in (*CLASS_PRESETS, WITHOUT_NOISE_PRESET):
            action = menu.addAction(preset_titles.get(name, name))
            action.triggered.connect(lambda _checked=False, n=name: self._on_quick_selection(("preset", n)))
            self._preset_actions[name] = action
        menu.addSeparator()
        for label, data in ((self.tr("All classes"), ("all", None)), (self.tr("No class"), ("none", None)),
                            (self.tr("Invert the selection"), ("invert", None))):
            action = menu.addAction(label)
            action.triggered.connect(lambda _checked=False, d=data: self._on_quick_selection(d))
        head.addWidget(self._quick_button)
        group_layout.addLayout(head)

        self._classes_list = QListWidget(self._classes_group)
        self._classes_list.setObjectName("listWidget_point_cloud_classes")
        self._classes_list.setMaximumHeight(240)
        self._classes_list.setAccessibleName(self.tr("Point classes"))
        self._classes_list.itemChanged.connect(self._drop_objects)  # first: the expression shown follows at once
        self._classes_list.itemChanged.connect(self._changed)
        self._classes_list.itemChanged.connect(self._update_class_summary)
        self._weight_delegate = ClassWeightDelegate(self._classes_list)
        self._classes_list.setItemDelegate(self._weight_delegate)
        group_layout.addWidget(self._classes_list)
        # Classes absent from the layer (counted 0): folded, so the list shows what the tile holds.
        self._absent_button = QToolButton(self._classes_group)
        self._absent_button.setObjectName("toolButton_point_cloud_absent_classes")
        self._absent_button.setCheckable(True)
        self._absent_button.setAutoRaise(True)
        self._absent_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._absent_button.setArrowType(Qt.ArrowType.RightArrow)
        self._absent_button.setToolTip(self.tr("Classes of the standard that hold no point of this layer"))
        self._absent_button.toggled.connect(self._on_absent_toggled)
        self._absent_button.setVisible(False)
        group_layout.addWidget(self._absent_button)
        self._absent_list = QListWidget(self._classes_group)
        self._absent_list.setObjectName("listWidget_point_cloud_absent_classes")
        self._absent_list.setMaximumHeight(160)
        self._absent_list.setAccessibleName(self.tr("Classes absent from the layer"))
        self._absent_list.itemChanged.connect(self._drop_objects)
        self._absent_list.itemChanged.connect(self._changed)
        self._absent_list.itemChanged.connect(self._update_class_summary)
        self._absent_list.setVisible(False)
        group_layout.addWidget(self._absent_list)
        group_layout.addWidget(self._build_object_ratio_row())
        return self._classes_group

    def _build_object_ratio_row(self) -> Any:
        """Similar objects of the detector: how far from the clicked objects' area an object may be.

        In a holder: expanding a QgsCollapsibleGroupBox shows again every direct child it hid,
        and the row is shown in the similar objects target only.
        """
        holder = QWidget(self._classes_group)
        holder.setObjectName("widget_point_cloud_similar_ratio_holder")
        holder_layout = QVBoxLayout(holder)
        holder_layout.setContentsMargins(0, 0, 0, 0)
        self._object_ratio_widget = QWidget(holder)
        self._object_ratio_widget.setObjectName("widget_point_cloud_similar_ratio")
        row = QHBoxLayout(self._object_ratio_widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(GAP)
        row.addWidget(QLabel(self.tr("Similar objects: area ×"), self._object_ratio_widget))
        self._object_low_spin = QDoubleSpinBox(self._object_ratio_widget)
        self._object_high_spin = QDoubleSpinBox(self._object_ratio_widget)
        for spin, value, name, tip in (
                (self._object_low_spin, DEFAULT_SIMILAR_RATIO[0], "doubleSpinBox_point_cloud_similar_low",
                 self.tr("Smallest similar object, as a share of the smallest clicked one")),
                (self._object_high_spin, DEFAULT_SIMILAR_RATIO[1], "doubleSpinBox_point_cloud_similar_high",
                 self.tr("Largest similar object, as a multiple of the largest clicked one"))):
            spin.setObjectName(name)
            spin.setRange(0.01, 100.0)
            spin.setDecimals(2)
            spin.setSingleStep(0.25)
            spin.setValue(value)
            spin.setKeyboardTracking(False)
            spin.setToolTip(tip)
            spin.setMinimumWidth(SPIN_MIN_WIDTH)
            spin.valueChanged.connect(self._on_object_ratio_changed)
        row.addWidget(self._object_low_spin)
        row.addWidget(QLabel(self.tr("to ×"), self._object_ratio_widget))
        row.addWidget(self._object_high_spin)
        row.addStretch(1)
        self._object_ratio_widget.setVisible(False)
        holder_layout.addWidget(self._object_ratio_widget)
        return holder

    def _on_absent_toggled(self, checked: bool) -> None:
        self._absent_list.setVisible(bool(checked) and self._absent_list.count() > 0)
        self._absent_button.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)

    def _build_ranges_group(self) -> Any:
        self._ranges_group = self._make_group(self.tr("ATTRIBUTES"), "mGroupBox_point_cloud_ranges", checked=False)
        self._ranges_group.toggled.connect(self._changed)
        group = self._ranges_group

        # Rows and buttons in holders: expanding a QgsCollapsibleGroupBox shows again every
        # direct child it hid when collapsing, even one hidden meanwhile (no return attribute).
        self._conditions_widget = QWidget(group)
        self._conditions_widget.setObjectName("widget_point_cloud_conditions")
        self._conditions_layout = QVBoxLayout(self._conditions_widget)
        self._conditions_layout.setContentsMargins(0, 0, 0, 0)
        self._conditions_layout.setSpacing(4)
        group.layout().addWidget(self._conditions_widget)

        actions_widget = QWidget(group)
        actions_widget.setObjectName("widget_point_cloud_condition_actions")
        actions = QHBoxLayout(actions_widget)
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(GAP)
        self._add_condition_button = QPushButton(self.tr("+ Condition"), actions_widget)
        self._add_condition_button.setObjectName("pushButton_point_cloud_add_condition")
        self._add_condition_button.setToolTip(self.tr("Add a condition on an attribute of the layer"))
        self._add_condition_button.clicked.connect(self._on_add_condition)
        actions.addWidget(self._add_condition_button)
        actions.addStretch()
        group.layout().addWidget(actions_widget)

        # The value pipette of the rail: which attribute a click reads, and the tolerance around it.
        pick_widget = QWidget(group)
        pick_widget.setObjectName("widget_point_cloud_value_pipette")
        pick = QHBoxLayout(pick_widget)
        pick.setContentsMargins(0, 0, 0, 0)
        pick.setSpacing(GAP)
        pick.addWidget(QLabel(self.tr("Pipette on"), pick_widget))
        self._pick_attribute_combo = _make_combo(pick_widget, SPIN_MIN_WIDTH,
                                                 self.tr("Attribute the value pipette of the rail reads under the click"))
        self._pick_attribute_combo.setObjectName("comboBox_point_cloud_pick_attribute")
        self._pick_attribute_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._pick_attribute_combo.currentIndexChanged.connect(self._on_pick_attribute_changed)
        pick.addWidget(self._pick_attribute_combo, 1)
        pick.addWidget(QLabel("±", pick_widget))
        self._pick_tolerance_spin = QDoubleSpinBox(pick_widget)
        self._pick_tolerance_spin.setObjectName("doubleSpinBox_point_cloud_pick_tolerance")
        self._pick_tolerance_spin.setRange(0.0, 100.0)
        self._pick_tolerance_spin.setDecimals(1)
        self._pick_tolerance_spin.setSuffix(" %")
        self._pick_tolerance_spin.setValue(DEFAULT_PICK_TOLERANCE)
        self._pick_tolerance_spin.setKeyboardTracking(False)
        self._pick_tolerance_spin.setMinimumWidth(SPIN_MIN_WIDTH)
        self._pick_tolerance_spin.setToolTip(self.tr("Tolerance around the picked value, in % of the observed range of the attribute"))
        pick.addWidget(self._pick_tolerance_spin)
        self._pick_widget = pick_widget
        group.layout().addWidget(pick_widget)

        # The returns: one choice, not a condition inserted in the list (its row is kept in step).
        returns_widget = QWidget(group)
        returns_widget.setObjectName("widget_point_cloud_returns")
        returns = QHBoxLayout(returns_widget)
        returns.setContentsMargins(0, 0, 0, 0)
        returns.setSpacing(GAP)
        returns.addWidget(QLabel(self.tr("Returns"), returns_widget))
        self._return_combo = _make_combo(returns_widget, COMBO_MIN_WIDTH,
                                         self.tr("Keep every return, or the first, last or single returns of the laser pulses"))
        self._return_combo.setObjectName("comboBox_point_cloud_returns")
        self._return_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._return_titles = {
            RETURN_ANY: self.tr("Any return"),
            RETURN_FIRST: self.tr("First return (ReturnNumber = 1)"),
            RETURN_LAST: self.tr("Last return (ReturnNumber = NumberOfReturns)"),
            RETURN_SINGLE: self.tr("Single return (NumberOfReturns = 1)"),
        }
        self._fill_return_combo(tuple(RETURN_PRESETS))
        self._return_combo.activated.connect(self._on_return_combo)
        returns.addWidget(self._return_combo, 1)
        self._returns_widget = returns_widget
        group.layout().addWidget(returns_widget)
        return group

    def _build_hag_group(self) -> Any:
        """HEIGHT / DTM: its own group, checkable, not exclusive (always ANDed), computed with PDAL."""
        group = self._make_group(self.tr("HEIGHT / DTM"), "mGroupBox_point_cloud_height", checked=False)
        self._hag_group = group
        self._hag_check = group  # the group check box is the switch (isChecked / toggled, as the box before)
        group.toggled.connect(self._on_hag_toggled)
        grid = QGridLayout()
        grid.setSpacing(GAP)
        note = QLabel(self.tr("Always combined (AND) with the active group"), group)
        note.setObjectName("label_point_cloud_height_note")
        note.setEnabled(False)
        note.setWordWrap(True)  # a one-line caption would widen the panel past a 440 px dock
        badge = QLabel(self.tr("PDAL · derived cloud"), group)
        badge.setObjectName("label_point_cloud_height_badge")
        badge.setToolTip(self.tr("The height is computed by PDAL into a derived point cloud, in a background task"))
        badge.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        badge.setEnabled(False)
        self._hag_badge = badge
        self._hag_spin = QDoubleSpinBox(group)
        self._hag_spin.setDecimals(2)
        self._hag_spin.setRange(0.0, 10000.0)
        self._hag_spin.setValue(DEFAULT_HAG_MIN)
        self._hag_spin.setPrefix("≥ ")
        self._hag_spin.setSuffix(" m")
        self._hag_spin.setKeyboardTracking(False)
        self._hag_spin.valueChanged.connect(self._changed)
        if QgsMapLayerComboBox is not None:
            self._hag_layer_combo = QgsMapLayerComboBox(group)
            raster_filter = _raster_layer_filter()
            if raster_filter is not None:
                self._hag_layer_combo.setFilters(raster_filter)
            _dtm_rasters_only(self._hag_layer_combo)  # PDAL hag_dem reads files: no basemap, no virtual raster
            self._hag_layer_combo.setAllowEmptyLayer(True)
            self._hag_layer_combo.setLayer(None)
            self._hag_layer_combo.layerChanged.connect(self._changed)
        else:
            self._hag_layer_combo = QComboBox(group)
        self._hag_layer_combo.setToolTip(self.tr("Digital terrain model the height is measured from"))
        self._hag_layer_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._hag_layer_combo.setMinimumWidth(SPIN_MIN_WIDTH)
        self._hag_spin.setMinimumWidth(SPIN_MIN_WIDTH)
        grid.addWidget(note, 0, 0)
        grid.addWidget(badge, 0, 1)
        grid.addWidget(self._hag_spin, 1, 0)
        grid.addWidget(self._hag_layer_combo, 1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 2)
        self._hag_tooltip = self.tr("Keep the points at least this high above the terrain model")
        group.setToolTip(self._hag_tooltip)
        group.layout().addLayout(grid)
        if hasattr(group, 'setCollapsed'):
            group.setCollapsed(True)
        return group

    def _on_hag_toggled(self, checked: bool) -> None:
        if hasattr(self._hag_group, 'setCollapsed'):
            self._hag_group.setCollapsed(not checked)
        self._changed()

    def _fill_return_combo(self, presets: Sequence[str]) -> None:
        with _signals_blocked(self._return_combo):
            self._return_combo.clear()
            self._return_combo.addItem(self._return_titles[RETURN_ANY], RETURN_ANY)
            for key in presets:
                self._return_combo.addItem(self._return_titles[key], key)

    def _on_return_combo(self, index: int) -> None:
        key = self._return_combo.itemData(index)
        if key in RETURN_PRESETS:
            self._apply_return_preset(key)
            return
        for row in list(self._condition_rows):
            if return_preset_of(row.condition()) is not None:
                self._drop_row(row)
        self._update_first_row()
        self._changed()

    def _sync_return_combo(self) -> None:
        """The combo says which return condition the list holds (none: any return)."""
        current = RETURN_ANY
        for row in self._condition_rows:
            key = return_preset_of(row.condition())
            if key is not None:
                current = key
                break
        with _signals_blocked(self._return_combo):
            self._return_combo.setCurrentIndex(max(0, self._return_combo.findData(current)))

    def _catalog(self) -> None:  # pragma: no cover - never called
        """Literal tr() calls of the attribute labels of the registry, for pylupdate.

        The labels come from ``core.domain.point_cloud_attributes`` and are
        translated at run time in this class context (see :meth:`_attribute_label`),
        as the texts of the module helpers given ``self.tr``.
        """
        self.tr("Intensity")
        self.tr("Return number")
        self.tr("Number of returns")
        self.tr("Classification")
        self.tr("Scan angle")
        self.tr("User data")
        self.tr("Point source ID")
        self.tr("GPS time")
        self.tr("Red")
        self.tr("Green")
        self.tr("Blue")
        self.tr("Infrared")
        self.tr("Scan direction")
        self.tr("Edge of flight line")
        self.tr("Synthetic")
        self.tr("Key point")
        self.tr("Withheld")
        self.tr("Overlap")
        self.tr("Scanner channel")
        self.tr("Classification flags")
        self.tr("Height above ground")
        # The line of the detected objects (object_summary, selection_strip.objects_text).
        self.tr("{0} object(s)")
        self.tr("cut at the window read")
        self.tr("shown as the whole class in their box")

    def _build_expression_group(self) -> Any:
        self._expression_group = self._make_group(self.tr("EXPRESSION"), "mGroupBox_point_cloud_expression", checked=False)
        self._expression_group.toggled.connect(self._on_expression_toggled)
        self._expression_edit = QPlainTextEdit(self._expression_group)
        self._expression_edit.setMaximumHeight(72)
        self._expression_edit.setAccessibleName(self.tr("Point cloud expression"))
        self._expression_edit.setToolTip(self.tr("Check the group to edit the expression by hand"))
        self._expression_edit.textChanged.connect(self._on_expression_edited)
        self._expression_group.layout().addWidget(self._expression_edit)
        return self._expression_group

    # === Public API ===

    def populate(self, summary: PointCloudLayerSummary) -> None:
        """Fill the panel from a ``PointCloudLayerSummary``.

        The current input is kept when ``summary`` describes the layer already
        shown (refresh); another layer starts from a reset panel.
        """
        same_layer = self._summary is not None and summary.layer_id == self._layer_id
        saved = self.state() if same_layer else None
        self._summary = summary
        self._layer_id = summary.layer_id
        attributes = tuple(summary.attributes)

        has_classes = attribute_available(attributes, CLASSIFICATION_ATTRIBUTE)
        self._fill_classes(summary.classes if has_classes else ())
        self._classes_group.setVisible(has_classes)

        names = condition_attributes(attributes, [item.name for item in summary.ranges])
        # X and Y are offered to the conditions too: the zone tool of the rail writes them.
        zone = [name for name in ZONE_ATTRIBUTES if attribute_available(attributes, name)]
        self._condition_choices = [(name, self._attribute_label(name)) for name in (*names, *zone)]
        bounds = ((name, summary_bounds(summary, name)) for name in (*names, *zone))
        self._condition_bounds = {name: value for name, value in bounds if value is not None}
        self._add_condition_button.setEnabled(bool(names))
        with _signals_blocked(self._pick_attribute_combo):
            self._pick_attribute_combo.clear()
            for name in names:
                self._pick_attribute_combo.addItem(self._attribute_label(name), name)
        self._pick_widget.setVisible(bool(names))
        presets = return_presets_available(attributes)
        self._fill_return_combo(presets)
        self._returns_widget.setVisible(bool(presets))

        if saved is not None:
            self.restore_state(saved)
        else:
            self.reset()
        self.set_current_subset(summary.current_subset or "")

    def criteria(self) -> PointCloudFilterCriteria:
        """Criteria of the checked CLASSES and ATTRIBUTES groups (height above DTM excluded)."""
        return build_point_cloud_criteria(self.state())

    def expression(self) -> str:
        """Subset expression to apply: typed one or generated one, plus the height above DTM."""
        return build_point_cloud_expression(self.state(), self._hag_available)

    def hag_settings(self) -> Optional[Tuple[str, float]]:
        """``(DTM layer id, minimum height)`` when the height above DTM filter is on, else None."""
        return hag_from_state(self.state(), self._hag_available)

    # === Value pipette and zone of the rail (tools of ATTRIBUTES) ===

    def pick_attribute(self) -> str:
        """Attribute the value pipette reads under a click (``Z`` by default)."""
        return self._pick_attribute_combo.currentData() or Z_ATTRIBUTE

    def set_pick_attribute(self, name: str) -> None:
        """Choose the attribute of the value pipette (ignored when the layer does not offer it). Does not emit."""
        index = self._pick_attribute_combo.findData(name)
        if index >= 0:
            with _signals_blocked(self._pick_attribute_combo):
                self._pick_attribute_combo.setCurrentIndex(index)

    def pick_attributes(self) -> List[str]:
        """Attributes the value pipette can read, in layer order."""
        return [self._pick_attribute_combo.itemData(i) for i in range(self._pick_attribute_combo.count())]

    def pick_tolerance(self) -> float:
        """Tolerance of the value pipette, in % of the observed range of the attribute."""
        return float(self._pick_tolerance_spin.value())

    def add_value_condition(self, attribute: str, value: float, extend: bool = False) -> bool:
        """A click of the value pipette: ``attribute between value - d and value + d`` in ATTRIBUTES.

        Replaces the condition already on that attribute; with ``extend`` (Ctrl+click) a new
        condition is added, ORed with the previous one. ATTRIBUTES becomes the active group.
        Returns False when the attribute is not offered.
        """
        if attribute not in dict(self._condition_choices):
            return False
        self.show_value_pipette_active()
        condition = value_condition(attribute, value, self.pick_tolerance(), self._condition_bounds.get(attribute),
                                    JOIN_OR if extend else JOIN_AND)
        if not extend:
            for row in self._condition_rows:
                if row.attribute() == attribute:
                    condition["join"] = row.join()
                    row.set_condition(condition)
                    self._changed()
                    return True
        self._append_row(condition)
        self._changed()
        return True

    def add_zone_conditions(self, xmin: float, ymin: float, xmax: float, ymax: float, wkt: str = "") -> bool:
        """A shape drawn with the Zone tool: ``X between`` and ``Y between`` in ATTRIBUTES (replacing the previous ones).

        Args:
            wkt: The shape itself (layer CRS), kept for the source geometry of the cross filter: a
                polygon or a circle then applies exactly to the targets, while the subset string of
                the cloud only knows the box.
        """
        if not all(name in dict(self._condition_choices) for name in ZONE_ATTRIBUTES):
            return False
        self.show_zone_active()
        for row in list(self._condition_rows):
            if row.attribute() in ZONE_ATTRIBUTES:
                self._drop_row(row)
        for condition in zone_conditions(xmin, ymin, xmax, ymax):
            self._append_row(condition)
        self._zone_wkt = str(wkt or "")
        self._update_first_row()
        self._changed()
        return True

    def zone_wkt(self) -> str:
        """WKT (layer CRS) of the shape that cuts the source geometry of the cross filter; ``""`` without one.

        The shape drawn with the Zone tool while its X / Y conditions are in ATTRIBUTES, the active
        group; else the objects of the detector while CLASSES is (:meth:`object_zone_wkt`).
        """
        if (self._zone_wkt and self._ranges_group.isChecked()
                and any(row.attribute() in ZONE_ATTRIBUTES for row in self._condition_rows)):
            return self._zone_wkt
        return self.object_zone_wkt()

    def show_value_pipette_active(self) -> None:
        """The value pipette went on the map: ATTRIBUTES becomes the active group, as a pick would make it."""
        if not self._ranges_group.isChecked():
            self._activate_group(self._ranges_group)

    def show_zone_active(self) -> None:
        """The zone tool went on the map: ATTRIBUTES becomes the active group."""
        self.show_value_pipette_active()

    def _on_pick_attribute_changed(self, _index: int) -> None:
        pass  # the pipette reads the combo when it clicks

    # === Object detector of the rail (a tool of CLASSES) ===

    def object_target(self) -> str:
        """What a click of the detector selects: :data:`OBJECT_TARGET` or :data:`SIMILAR_OBJECTS_TARGET`."""
        return self._objects["target"]

    def set_object_target(self, target: str) -> bool:
        """Adopt the target chosen in the rail menus; True when it changed. Does not emit ``objectsChanged``.

        The clicked objects stay: what was found for them is dropped until the controller reads them again.
        """
        target = target if target in OBJECT_TARGETS else OBJECT_TARGET
        if target == self._objects["target"]:
            return False
        self._objects["target"] = target
        self._object_ratio_widget.setVisible(target == SIMILAR_OBJECTS_TARGET)
        if self._objects["items"]:
            self._objects["detected"] = None
            self._update_class_summary()
            self._changed()
        return True

    def object_ratio(self) -> Tuple[float, float]:
        """``(low, high)`` area ratios of the similar objects."""
        low, high = self._objects["ratio"]
        return float(low), float(high)

    def object_items(self) -> List[Dict[str, Any]]:
        """The clicked objects (copies): ``{"x", "y", "code", "box", "wkt", "truncated"}``, layer CRS."""
        return [dict(item, box=list(item["box"])) for item in self._objects["items"]]

    def add_object(self, item: Dict[str, Any], extend: bool = False) -> bool:
        """An object found under a click of the detector (see :meth:`object_items`); Ctrl+click (``extend``) adds it.

        Its class is checked in CLASSES, which becomes the active group; the classes checked are
        those of the objects. False when the class is not listed (nothing changes).

        The objects kept while another group was the active one come back with CLASSES (they are
        its selection, as its checked classes): a Ctrl+click adds to them.
        """
        parsed = _parse_object_item(item)
        if parsed is None or parsed["code"] not in self._present_codes() or self._classes_group.isHidden():
            return False
        if not self._classes_group.isChecked():
            self._activate_group(self._classes_group)
        self._objects["items"] = [*(self._objects["items"] if extend else []), parsed]
        self._objects["detected"] = None
        self._check_codes(sorted({entry["code"] for entry in self._objects["items"]}))  # emits, summary updated
        return True

    def set_detected_objects(self, wkt: str, boxes: Sequence[Sequence[float]], count: Optional[int],
                             area: Optional[float] = None, truncated: bool = False) -> None:
        """What the controller found for the clicked objects (or the similar ones), for the subset and the targets.

        Args:
            wkt: Their geometry (layer CRS), the source geometry of the cross filter is cut by it.
            boxes: ``[code, xmin, ymin, xmax, ymax]`` of each object, for the subset string.
            count: Objects found (similar objects: those of the cloud), None when unknown.
            area: Their ground area in square metres, None when unknown.
            truncated: An object was cut at the window read, or the cloud at its points limit.
        """
        if not self._objects["items"]:
            return
        self._objects["detected"] = _parse_detected({"wkt": wkt, "boxes": [list(box) for box in boxes],
                                                     "count": count, "area": area, "truncated": truncated})
        self._update_class_summary()
        self._changed()
        self.summaryChanged.emit()

    def detected_objects(self) -> Optional[Tuple[Optional[int], Optional[float], bool, bool]]:
        """``(count, area in m², truncated, merged)`` of the objects while CLASSES is active; None otherwise.

        Not read yet (:meth:`objects_pending`): the clicked objects, without area. ``merged``: the subset
        keeps one box per class (:func:`boxes_merged`).
        """
        items = self._objects["items"]
        if not items or not self._classes_group.isChecked():
            return None
        merged = boxes_merged(self._objects)
        detected = self._objects["detected"]
        if detected is None:
            return len(items), None, any(item["truncated"] for item in items), merged
        return detected["count"], detected["area"], detected["truncated"], merged

    def objects_pending(self) -> bool:
        """Clicked objects whose detection is missing (a restored state, a read that failed): to be read again."""
        return bool(self._objects["items"]) and self._objects["detected"] is None

    def tiles_expression(self) -> str:
        """Subset for the other tiles of the dataset (:meth:`apply_to_tiles`).

        The boxes of the objects are in the coordinates of this tile (no point of another tile is in
        them): with objects, their classes go alone; :meth:`expression` otherwise.
        """
        if not self._objects["items"] or not self._classes_group.isChecked():
            return self.expression()
        state = self.state()
        state["objects"] = {}
        return build_point_cloud_expression(state, self._hag_available)

    def object_zone_wkt(self) -> str:
        """WKT (layer CRS) of the detected objects while CLASSES is the active group; ``""`` otherwise."""
        detected = self._objects["detected"]
        if detected is None or not self._objects["items"] or not self._classes_group.isChecked():
            return ""
        return detected["wkt"]

    def _drop_objects(self, *_args) -> None:
        """The class list was edited by hand (or by the class pipette): whole classes, no object any more."""
        if not self._objects["items"]:
            return
        self._objects["items"], self._objects["detected"] = [], None
        self._update_class_summary()
        self.objectsChanged.emit()  # the outline goes

    def _on_object_ratio_changed(self, _value: Any) -> None:
        low, high = float(self._object_low_spin.value()), float(self._object_high_spin.value())
        self._objects["ratio"] = [min(low, high), max(low, high)]
        if self._objects["target"] == SIMILAR_OBJECTS_TARGET and self._objects["items"]:
            self.objectsChanged.emit()

    def _restore_objects(self, objects: Dict[str, Any]) -> None:
        """The detector part of a restored state (parsed). Does not emit."""
        self._objects = parse_objects_state(objects)
        with _signals_blocked(self._object_low_spin, self._object_high_spin):
            self._object_low_spin.setValue(self._objects["ratio"][0])
            self._object_high_spin.setValue(self._objects["ratio"][1])
        self._object_ratio_widget.setVisible(self._objects["target"] == SIMILAR_OBJECTS_TARGET)

    def apply_to_tiles(self) -> bool:
        """Whether the filter should also go to the other tiles of the dataset."""
        return self._apply_tiles_check.isChecked()

    def set_hag_available(self, available: bool, reason: str = "") -> None:
        """Enable the height above DTM row, or disable it and explain why in its tooltip."""
        self._hag_available = bool(available)
        tooltip = self._hag_tooltip if available else (reason or self.tr("Height above the terrain is unavailable"))
        for widget in (self._hag_check, self._hag_spin, self._hag_layer_combo):
            widget.setEnabled(self._hag_available)
        self._hag_check.setToolTip(tooltip)
        self._hag_spin.setToolTip(tooltip)
        self._refresh_generated_expression()

    def set_point_counts(self, kept: Optional[int], total: Optional[int]) -> None:
        """Remember the kept / total point counts; the selection strip under EXPLORING shows them (``summaryChanged``)."""
        self._counts = (kept, total)
        self.summaryChanged.emit()

    def point_counts(self) -> Tuple[Optional[int], Optional[int]]:
        """Last ``(kept, total)`` point counts."""
        return getattr(self, '_counts', (None, None))

    def set_counts_inline(self, inline: bool) -> None:
        """Kept for the callers of FilterMate 5.0: the panel never shows the counts itself any more."""
        self._counts_inline = bool(inline)

    def set_current_subset(self, text: str) -> None:
        """Remember the subset string currently applied to the layer (shown by the strip tooltip)."""
        self._current_subset = (text or "").strip()
        self.summaryChanged.emit()

    def current_subset(self) -> str:
        """Subset string currently applied to the layer, ``""`` when none."""
        return getattr(self, '_current_subset', "")

    def reset(self) -> None:
        """Back to the defaults (no class, no condition, no height, no expression). Does not emit."""
        self.restore_state({"layer_id": self._layer_id})

    def state(self) -> Dict[str, Any]:
        """Input of the panel, to keep it per layer (see :meth:`restore_state`)."""
        layer = self._hag_layer_combo.currentLayer() if hasattr(self._hag_layer_combo, "currentLayer") else None
        expression_enabled = self._expression_group.isChecked()
        return {
            "layer_id": self._layer_id,
            "classes_enabled": self._classes_group.isChecked(),
            "classes": self._checked_codes(),
            "ranges_enabled": self._ranges_group.isChecked(),
            "conditions": [row.condition() for row in self._condition_rows],
            "hag_enabled": self._hag_check.isChecked(),
            "hag_min": float(self._hag_spin.value()),
            "hag_layer_id": layer.id() if layer is not None else None,
            "expression_enabled": expression_enabled,
            "expression": self._expression_edit.toPlainText() if expression_enabled else self._custom_expression,
            "apply_to_tiles": self._apply_tiles_check.isChecked(),
            "pick_attribute": self.pick_attribute(),
            "pick_tolerance": self.pick_tolerance(),
            "zone_wkt": self._zone_wkt,
            "objects": parse_objects_state(self._objects),  # a copy
        }

    def restore_state(self, state: Dict[str, Any]) -> None:
        """Restore a :meth:`state`; unknown classes, attributes and layers are ignored. Does not emit."""
        self._debounce.stop()
        parsed = parse_point_cloud_state(state)
        wanted = set(parsed["classes"])
        self._restore_objects(parsed["objects"])
        widgets = (self._classes_group, self._ranges_group, self._expression_group, self._classes_list,
                   self._absent_list, self._hag_group, self._hag_spin, self._hag_layer_combo, self._apply_tiles_check)
        with _signals_blocked(*widgets):
            self._classes_group.setChecked(parsed["classes_enabled"])
            self._ranges_group.setChecked(parsed["ranges_enabled"])
            for item in self._class_items():
                checked = int(item.data(Qt.ItemDataRole.UserRole)) in wanted
                item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            self._update_class_summary()
            self._hag_group.setChecked(parsed["hag_enabled"])
            if hasattr(self._hag_group, 'setCollapsed'):
                self._hag_group.setCollapsed(not parsed["hag_enabled"])
            self._hag_spin.setValue(parsed["hag_min"])
            self._restore_hag_layer(parsed["hag_layer_id"])
            self._apply_tiles_check.setChecked(parsed["apply_to_tiles"])
            self._expression_group.setChecked(parsed["expression_enabled"])
        with _signals_blocked(self._pick_tolerance_spin):
            self._pick_tolerance_spin.setValue(parsed["pick_tolerance"])
        self.set_pick_attribute(parsed["pick_attribute"])
        self._zone_wkt = parsed["zone_wkt"]
        self._set_conditions(parsed["conditions"])
        self._custom_expression = parsed["expression"]
        self._apply_expression_mode(parsed["expression_enabled"])
        self._enforce_single_group()

    # === One active group (as the vector exploring groups) ===

    def showEvent(self, event) -> None:  # noqa: N802 - Qt override
        """Apply the collapsed state of the groups again once shown.

        QgsCollapsibleGroupBox.setCollapsed only records the state while the box
        is hidden (another page of the coverage host, the vector groups shown):
        a group activated meanwhile came back one band high with its contents hidden.
        """
        super().showEvent(event)
        for group in (*self._exclusive_groups(), self._hag_group):
            if hasattr(group, 'setCollapsed') and group.isVisible():
                group.setCollapsed(group.isCollapsed())  # unchanged state: no collapsedStateChanged

    def _exclusive_groups(self) -> List[Any]:
        return [self._classes_group, self._ranges_group, self._expression_group]

    def _setup_exclusive_groups(self) -> None:
        """Classes, ranges and expression are exclusive: always exactly one active group.

        Connected after the groups' own handlers, so checking EXPRESSION still starts
        from the criteria of the group that was active.
        """
        self._switching_group = False
        for group in self._exclusive_groups():
            group.toggled.connect(lambda checked, g=group: self._on_exclusive_toggled(g, checked))
            if hasattr(group, 'collapsedStateChanged'):
                group.collapsedStateChanged.connect(lambda collapsed, g=group: self._on_exclusive_collapsed(g, collapsed))
        self._enforce_single_group()

    def _activate_group(self, active: Any) -> None:
        self._switching_group = True
        try:
            # The new group first: EXPRESSION then starts from the criteria still checked.
            if not active.isChecked():
                active.setChecked(True)
            for group in self._exclusive_groups():
                if group is not active and group.isChecked():
                    group.setChecked(False)  # their own handlers run (expression text kept, debounce)
                if hasattr(group, 'setCollapsed'):
                    group.setCollapsed(group is not active)
        finally:
            self._switching_group = False

    def _on_exclusive_toggled(self, group: Any, checked: bool) -> None:
        if self._switching_group:
            return
        if checked:
            self._activate_group(group)
            self.groupChosen.emit(self._group_key(group))
            return
        # Unchecking the active group would leave none: check it again, signals on, so its
        # own handler restores what the unchecking undid (EXPRESSION back to editable text).
        self._switching_group = True
        try:
            group.setChecked(True)
        finally:
            self._switching_group = False

    def _on_exclusive_collapsed(self, group: Any, collapsed: bool) -> None:
        # Expanding a group makes it the active one.
        if self._switching_group or collapsed or group.isChecked():
            return
        self._activate_group(group)
        self.groupChosen.emit(self._group_key(group))

    def _group_key(self, group: Any) -> str:
        return {id(self._classes_group): "classes", id(self._ranges_group): "ranges"}.get(id(group), "expression")

    def show_class_pipette_active(self) -> None:
        """The class pipette went on the map: CLASSES becomes the active group, as a pick would make it."""
        if not self._classes_group.isHidden() and not self._classes_group.isChecked():
            self._activate_group(self._classes_group)

    def _enforce_single_group(self) -> None:
        """After a restore: the first checked group in visual order stays, classes when none."""
        groups = self._exclusive_groups()
        shown = [group for group in groups if not group.isHidden()] or groups
        active = next((group for group in shown if group.isChecked()), shown[0])
        with _signals_blocked(*groups):
            for group in groups:
                group.setChecked(group is active)
                if hasattr(group, 'setCollapsed'):
                    group.setCollapsed(group is not active)
        self._apply_expression_mode(self._expression_group.isChecked())

    # === Change notification ===

    def _changed(self, *_args) -> None:
        self._refresh_generated_expression()
        if hasattr(self, '_return_combo'):
            self._sync_return_combo()
        self._debounce.start()

    # === Classes ===

    def _fill_classes(self, classes: Iterable[Tuple[int, int]]) -> None:
        classes = tuple(classes)
        if not classes:
            # Unknown classes: offer the standard ASPRS codes without counts.
            classes = tuple((code, -1) for code in sorted(ASPRS_CLASS_NAMES))
        present, absent = split_classes(classes)
        self._weight_delegate.maximum = max((count for _code, count in present), default=0)
        for widget, entries in ((self._classes_list, present), (self._absent_list, absent)):
            with _signals_blocked(widget):
                widget.clear()
                for code, count in entries:
                    item = QListWidgetItem(class_item_label(code, count))
                    pixmap = QPixmap(12, 12)
                    pixmap.fill(QColor(class_color(code)))
                    item.setIcon(QIcon(pixmap))
                    item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                    item.setCheckState(Qt.CheckState.Unchecked)
                    item.setData(Qt.ItemDataRole.UserRole, int(code))
                    item.setData(CLASS_COUNT_ROLE, int(count))
                    widget.addItem(item)
        self._absent_button.setText(self.tr("Other classes, absent from the layer ({0})").format(len(absent)))
        self._absent_button.setVisible(bool(absent))
        self._absent_list.setVisible(bool(absent) and self._absent_button.isChecked())
        codes = self._present_codes()
        for name, action in self._preset_actions.items():
            action.setEnabled(bool(preset_codes(name, codes)))
        self._update_class_summary()

    def _class_items(self) -> List[Any]:
        items = []
        for widget in (self._classes_list, self._absent_list):
            items.extend(widget.item(index) for index in range(widget.count()))
        return [item for item in items if item is not None]

    def _present_codes(self) -> List[int]:
        return [int(item.data(Qt.ItemDataRole.UserRole)) for item in self._class_items()]

    def _checked_codes(self) -> List[int]:
        return sorted(int(item.data(Qt.ItemDataRole.UserRole)) for item in self._class_items()
                      if item.checkState() == Qt.CheckState.Checked)

    def _check_codes(self, codes: Iterable[int]) -> None:
        wanted = set(codes)
        with _signals_blocked(self._classes_list, self._absent_list):
            for item in self._class_items():
                checked = int(item.data(Qt.ItemDataRole.UserRole)) in wanted
                item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        self._update_class_summary()
        self._changed()

    def checked_class_codes(self) -> List[int]:
        """Codes of the checked classes, sorted."""
        return self._checked_codes()

    def select_class(self, code: int, extend: bool = False) -> bool:
        """Check the class picked on the map (added to the checked ones with ``extend``); False when not listed.

        The whole class: the objects of the detector are dropped.
        """
        if int(code) not in self._present_codes() or self._classes_group.isHidden():
            return False
        if not self._classes_group.isChecked():
            extend = False  # classes left checked under another active group do not come back
            self._classes_group.setChecked(True)
        self._drop_objects()
        self._check_codes(picked_class_codes(self._checked_codes(), code, extend))
        return True

    def _set_all_classes(self, state: Any) -> None:
        self._check_codes(self._present_codes() if state == Qt.CheckState.Checked else ())

    def _apply_preset(self, name: str) -> None:
        self._check_codes(preset_codes(name, self._present_codes()))

    def _on_quick_selection(self, data: Any) -> None:
        if data is None:
            return
        self._drop_objects()  # whole classes from now on
        action, name = data
        if action == "preset":
            self._apply_preset(name)
        elif action == "all":
            self._set_all_classes(Qt.CheckState.Checked)
        elif action == "none":
            self._set_all_classes(Qt.CheckState.Unchecked)
        else:
            self._check_codes(inverted_codes(self._present_codes(), self._checked_codes()))

    def _class_counts(self) -> Tuple[int, int, Optional[int], Optional[int]]:
        """``(checked, shown, kept points, total points)``; the points are None when a class has no count."""
        items = self._class_items()
        checked = [item for item in items if item.checkState() == Qt.CheckState.Checked]
        counts = [int(item.data(CLASS_COUNT_ROLE)) for item in items]
        kept = None
        if items and all(count >= 0 for count in counts):
            kept = sum(int(item.data(CLASS_COUNT_ROLE)) for item in checked)
        total = sum(counts) if kept is not None else None
        return len(checked), len(items), kept, total

    def _update_class_summary(self, *_args) -> None:
        """Checked classes and the points they hold, under the list; the objects found while there are."""
        items = self._objects["items"]
        if items:
            detected = self._objects["detected"]
            count = detected["count"] if detected is not None and detected["count"] is not None else len(items)
            truncated = detected["truncated"] if detected is not None else any(item["truncated"] for item in items)
            area = detected["area"] if detected is not None else None
            merged = boxes_merged(self._objects)
            self._class_summary_label.setText(object_summary(count, area, truncated, self.tr, merged))
            tips = []
            if truncated:
                tips.append(self.tr("An object runs past the largest window read around the click and was cut there"))
            if merged:
                tips.append(self.tr("Too many objects for the subset of the cloud: the preview and the filtered cloud "
                                    "keep every point of their class in the box around them; the targets are cut by "
                                    "the objects themselves"))
            self._class_summary_label.setToolTip("\n".join(tips))
            return
        self._class_summary_label.setToolTip("")
        checked, shown, kept, total = self._class_counts()
        self._class_summary_label.setText(class_selection_summary(checked, shown, kept if checked else None, total))

    def class_point_counts(self) -> Tuple[Optional[int], Optional[int]]:
        """``(kept, total)`` points of the checked classes while CLASSES is the active group, else ``(None, None)``.

        Exact from the layer statistics; no class checked keeps no constraint (None), nor do detected
        objects (a part of their classes).
        """
        if not self._classes_group.isChecked() or self._objects["items"]:
            return None, None
        checked, _shown, kept, total = self._class_counts()
        return (kept, total) if checked and kept is not None else (None, None)

    # === Conditions ===

    def condition_attributes(self) -> List[str]:
        """Names of the attributes offered in the conditions, in layer order."""
        return [name for name, _label in self._condition_choices]

    def _attribute_label(self, name: str) -> str:
        """``"Intensity"``, ``"Z (m)"``: translated registry label, with the unit."""
        info = attribute_info(name)
        label = self.tr(info.label) if info.label != name else name
        return f"{label} ({info.unit})" if info.unit else label

    def _set_conditions(self, conditions: Sequence[Dict[str, Any]]) -> None:
        """Rows of parsed conditions; those on attributes not offered are dropped. Does not emit."""
        for row in list(self._condition_rows):
            self._drop_row(row)
        offered = set(self.condition_attributes())
        for condition in conditions:
            operand = condition["low"]
            if condition["attribute"] in offered and (not isinstance(operand, str) or operand in offered):
                self._append_row(condition)
        self._update_first_row()

    def _append_row(self, condition: Dict[str, Any]) -> Any:
        row = PointCloudConditionRow(self._condition_choices, self._condition_bounds, self._conditions_widget)
        row.set_condition(condition)
        row.changed.connect(self._changed)
        row.removeRequested.connect(lambda r=row: self._on_remove_condition(r))
        self._conditions_layout.addWidget(row)
        self._condition_rows.append(row)
        self._update_first_row()
        return row

    def _drop_row(self, row: Any) -> None:
        self._conditions_layout.removeWidget(row)
        self._condition_rows.remove(row)
        row.hide()
        row.deleteLater()

    def _update_first_row(self) -> None:
        for index, row in enumerate(self._condition_rows):
            row.set_first(index == 0)

    def _on_add_condition(self, *_args) -> None:
        """New ``between`` row on the first attribute not used yet, every value kept until edited."""
        names = [name for name in self.condition_attributes() if name not in ZONE_ATTRIBUTES]
        if not names:
            return
        used = {row.attribute() for row in self._condition_rows}
        name = next((name for name in names if name not in used), names[0])
        self._append_row({"attribute": name, "op": OP_BETWEEN, "low": None, "high": None, "join": JOIN_AND})
        self._changed()

    def _on_remove_condition(self, row: Any) -> None:
        if row in self._condition_rows:
            if row.attribute() in ZONE_ATTRIBUTES:
                self._zone_wkt = ""  # the box is edited by hand: the drawn shape no longer applies
            self._drop_row(row)
            self._update_first_row()
            self._changed()

    def _apply_return_preset(self, key: str) -> None:
        """Keep the return condition of ``key``; it replaces the one already there (one return choice)."""
        for row in self._condition_rows:
            if return_preset_of(row.condition()) is not None:
                row.set_condition(return_preset_condition(key, row.join()))
                break
        else:
            self._append_row(return_preset_condition(key))
        self._changed()

    # === Height above DTM ===

    def _restore_hag_layer(self, layer_id: Optional[str]) -> None:
        if not hasattr(self._hag_layer_combo, "setLayer"):
            return
        layer = None
        if layer_id:
            try:
                from qgis.core import QgsProject
                layer = QgsProject.instance().mapLayer(layer_id)
            except ImportError:
                layer = None
        self._hag_layer_combo.setLayer(layer)

    # === Expression ===

    def _apply_expression_mode(self, editable: bool) -> None:
        """Editable typed expression, or read-only view of the generated one."""
        self._expression_edit.setReadOnly(not editable)
        text = self._custom_expression if editable else generated_expression(self.state())
        with _signals_blocked(self._expression_edit):
            self._expression_edit.setPlainText(text)

    def _refresh_generated_expression(self) -> None:
        if not self._expression_group.isChecked():
            with _signals_blocked(self._expression_edit):
                self._expression_edit.setPlainText(generated_expression(self.state()))

    def _on_expression_toggled(self, checked: bool) -> None:
        if checked:
            # Start from the generated expression the first time.
            if not self._custom_expression.strip():
                self._custom_expression = generated_expression(self.state())
        else:
            self._custom_expression = self._expression_edit.toPlainText()
        self._apply_expression_mode(checked)
        self._debounce.start()

    def _on_expression_edited(self) -> None:
        if self._expression_group.isChecked():
            self._debounce.start()
