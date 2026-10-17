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
plus the height above a DTM computed with PDAL, always ANDed with the rest.
The return shortcuts (first, last, single) insert the matching condition.

The panel only reads a ``PointCloudLayerSummary`` (and the DTM layer combo);
the state handling - criteria and expression building, presets, migration of
older states, count formatting - is done by pure functions of this module and
of ``core.domain.point_cloud_attributes``, testable without Qt.
"""
import math
from contextlib import contextmanager
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from qgis.PyQt.QtCore import Qt, QTimer, pyqtSignal
    from qgis.PyQt.QtGui import QColor, QIcon, QPixmap
    from qgis.PyQt.QtWidgets import (
        QCheckBox, QComboBox, QDoubleSpinBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
        QListWidget, QListWidgetItem, QMenu, QPlainTextEdit, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
    )
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    QWidget = object

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
    conditions_have_or, parse_conditions,
)
from ....core.domain.point_cloud_filter_criteria import (
    PointCloudFilterCriteria, PointCloudLayerSummary, format_number,
)
from ....core.domain.point_cloud_support import (
    ASPRS_CLASS_NAMES, CLASS_PRESETS, NOISE_CLASSES, asprs_class_label,
)
from .histogram_widget import normalize_range, spin_bounds

Bound = Optional[float]

CLASSIFICATION_ATTRIBUTE = pc_attributes.CLASSIFICATION
Z_ATTRIBUTE = pc_attributes.Z
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


def inverted_codes(present_codes: Iterable[int], checked_codes: Iterable[int]) -> Tuple[int, ...]:
    """Codes of the list that are NOT checked (the "Invert" quick selection), in list order."""
    checked = {int(code) for code in checked_codes}
    return tuple(int(code) for code in present_codes if int(code) not in checked)


def picked_class_codes(checked_codes: Iterable[int], code: int, extend: bool) -> Tuple[int, ...]:
    """Classes checked after a pipette click: the picked class alone, or added to the others with Ctrl."""
    return tuple(sorted({int(code), *checked_codes})) if extend else (int(code),)


def class_selection_summary(checked: int, shown: int, kept_points: Optional[int], total_points: Optional[int]) -> str:
    """Line under the class list: ``"3 of 12 classes · 9.8 M / 38.4 M points (25.5 %)"``.

    The points are those of the checked classes, when every class of the list has a count.
    """
    text = f"{checked} / {shown}"
    counted = format_point_counts(kept_points, total_points)
    return f"{text} · {counted}" if counted else text


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
    return {
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
    }


def build_point_cloud_criteria(state: Any) -> PointCloudFilterCriteria:
    """Criteria of the checked group (the panel keeps one): classes, or attribute conditions.

    The state format still allows several checked groups (older saved states);
    they are combined here, the panel narrows them to one on restore.

    An AND chain of conditions gives ranges (``between``, ``>=``, ``<=``) and
    extra clauses (the other operators); a chain with an OR is one extra
    clause. The height above the DTM is not part of the criteria (see
    :func:`build_point_cloud_expression`).
    """
    parsed = parse_point_cloud_state(state)
    codes = parsed["classes"] if parsed["classes_enabled"] else ()
    ranges, extra_clauses = conditions_criteria(parsed["conditions"]) if parsed["ranges_enabled"] else ((), ())
    return PointCloudFilterCriteria(
        classification_codes=frozenset(codes),
        ranges=ranges,
        extra_clauses=extra_clauses,
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
    """``(DTM layer id, minimum height)`` when the height filter is usable and on, else None."""
    parsed = parse_point_cloud_state(state)
    if not (available and parsed["ranges_enabled"] and parsed["hag_enabled"] and parsed["hag_layer_id"]):
        return None
    return parsed["hag_layer_id"], parsed["hag_min"]


def build_point_cloud_expression(state: Any, hag_available: bool = True) -> str:
    """Subset expression of a panel state.

    The typed expression when the EXPRESSION group is checked, else the
    criteria of the other groups; ``HeightAboveGround >= x`` is ANDed in
    both cases when the height filter is on (an OR chain is parenthesised first).
    """
    parsed = parse_point_cloud_state(state)
    if parsed["expression_enabled"]:
        base, wrap = parsed["expression"], True
    else:
        base = generated_expression(parsed)
        wrap = parsed["ranges_enabled"] and conditions_have_or(parsed["conditions"])
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


# Raster providers without a file PDAL could open (filters.hag_dem reads the DTM through GDAL).
NON_FILE_RASTER_PROVIDERS = ('virtualraster', 'postgresraster')


def _dtm_rasters_only(combo: Any) -> None:
    """DTM list: hide the rasters PDAL cannot read (WMS / XYZ / WCS as in the layer lists, virtual, PostGIS)."""
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
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        return group

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self._build_classes_group())
        layout.addWidget(self._build_ranges_group())
        layout.addWidget(self._build_expression_group())

        self._apply_tiles_check = QCheckBox(self.tr("Apply to the other tiles of the dataset"), self)
        self._apply_tiles_check.toggled.connect(self.applyToTilesToggled.emit)
        layout.addWidget(self._apply_tiles_check)
        self._counts_label = QLabel("", self)
        self._counts_label.setVisible(False)
        layout.addWidget(self._counts_label)
        self._current_filter_label = QLabel("", self)
        self._current_filter_label.setWordWrap(True)
        layout.addWidget(self._current_filter_label)
        layout.addStretch()
        self.set_current_subset("")
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
        # One compact combo (a button grid made the dock wider than 440 px): the usual selections
        # of the raster "Usual thresholds" combo, for classes.
        self._quick_combo = _make_combo(self._classes_group, COMBO_MIN_WIDTH, self.tr("Quick class selection"))
        self._quick_combo.setObjectName("comboBox_point_cloud_class_quick_selection")
        self._quick_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._quick_combo.addItem(self.tr("Quick selection…"), None)
        for name in (*CLASS_PRESETS, WITHOUT_NOISE_PRESET):
            self._quick_combo.addItem(preset_titles.get(name, name), ("preset", name))
        self._quick_combo.addItem(self.tr("All classes"), ("all", None))
        self._quick_combo.addItem(self.tr("No class"), ("none", None))
        self._quick_combo.addItem(self.tr("Invert the selection"), ("invert", None))
        self._quick_combo.activated.connect(self._on_quick_selection)
        group_layout.addWidget(self._quick_combo)

        self._classes_list = QListWidget(self._classes_group)
        self._classes_list.setMaximumHeight(300)  # the whole ASPRS list, as in the mockup
        self._classes_list.setAccessibleName(self.tr("Point classes"))
        self._classes_list.itemChanged.connect(self._changed)
        self._classes_list.itemChanged.connect(self._update_class_summary)
        group_layout.addWidget(self._classes_list)
        self._class_summary_label = QLabel("", self._classes_group)
        self._class_summary_label.setObjectName("label_point_cloud_class_summary")
        group_layout.addWidget(self._class_summary_label)
        return self._classes_group

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
        actions.setSpacing(4)
        self._add_condition_button = QPushButton(self.tr("+ Condition"), actions_widget)
        self._add_condition_button.setObjectName("pushButton_point_cloud_add_condition")
        self._add_condition_button.setToolTip(self.tr("Add a condition on an attribute of the layer"))
        self._add_condition_button.clicked.connect(self._on_add_condition)
        # Return shortcuts in a menu: three more buttons would not fit a narrow dock.
        self._return_button = QPushButton(self.tr("Returns"), actions_widget)
        self._return_button.setObjectName("pushButton_point_cloud_return_presets")
        self._return_button.setToolTip(self.tr("Keep the first, last or single returns of the laser pulses"))
        menu = QMenu(self._return_button)
        titles = {
            RETURN_FIRST: self.tr("First return (ReturnNumber = 1)"),
            RETURN_LAST: self.tr("Last return (ReturnNumber = NumberOfReturns)"),
            RETURN_SINGLE: self.tr("Single return (NumberOfReturns = 1)"),
        }
        self._return_actions: Dict[str, Any] = {}
        for key in RETURN_PRESETS:
            action = menu.addAction(titles[key])
            action.triggered.connect(lambda _checked=False, k=key: self._apply_return_preset(k))
            self._return_actions[key] = action
        self._return_button.setMenu(menu)
        actions.addWidget(self._add_condition_button)
        actions.addWidget(self._return_button)
        actions.addStretch()
        group.layout().addWidget(actions_widget)

        # Height above the DTM: computed with PDAL, always ANDed with the conditions.
        grid = QGridLayout()
        grid.setSpacing(4)
        self._hag_check = QCheckBox(self.tr("Height above DTM ≥"), group)
        self._hag_check.toggled.connect(self._changed)
        self._hag_spin = QDoubleSpinBox(group)
        self._hag_spin.setDecimals(2)
        self._hag_spin.setRange(0.0, 10000.0)
        self._hag_spin.setValue(DEFAULT_HAG_MIN)
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
        # Own row: the long check box label would widen the first column of the grid.
        grid.addWidget(self._hag_check, 0, 0, 1, 2)
        grid.addWidget(self._hag_spin, 1, 0)
        grid.addWidget(self._hag_layer_combo, 1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 2)
        self._hag_tooltip = self.tr("Keep the points at least this high above the terrain model")
        self._hag_check.setToolTip(self._hag_tooltip)
        group.layout().addLayout(grid)
        return group

    def _catalog(self) -> None:  # pragma: no cover - never called
        """Literal tr() calls of the attribute labels of the registry, for pylupdate.

        The labels come from ``core.domain.point_cloud_attributes`` and are
        translated at run time in this class context (see :meth:`_attribute_label`).
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
        self._condition_choices = [(name, self._attribute_label(name)) for name in names]
        bounds = ((name, summary_bounds(summary, name)) for name in names)
        self._condition_bounds = {name: value for name, value in bounds if value is not None}
        self._add_condition_button.setEnabled(bool(names))
        presets = return_presets_available(attributes)
        for key, action in self._return_actions.items():
            action.setVisible(key in presets)
        self._return_button.setVisible(bool(presets))

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
        """Show ``Kept points: 9.8 M / 38.4 M (25.5 %)``; hidden without a kept count.

        With :meth:`set_counts_inline` False the counts only go to the selection strip
        under EXPLORING (``summaryChanged``), as in the FilterMate 5 mockup.
        """
        self._counts = (kept, total)
        text = format_point_counts(kept, total)
        self._counts_label.setText(self.tr("Kept points: {0}").format(text) if text else "")
        self._counts_label.setVisible(bool(text) and getattr(self, '_counts_inline', True))
        self.summaryChanged.emit()

    def point_counts(self) -> Tuple[Optional[int], Optional[int]]:
        """Last ``(kept, total)`` point counts shown."""
        return getattr(self, '_counts', (None, None))

    def set_counts_inline(self, inline: bool) -> None:
        """Whether the panel shows the counts itself (False: the selection strip does)."""
        self._counts_inline = bool(inline)
        if not inline:
            self._counts_label.setVisible(False)

    def set_current_subset(self, text: str) -> None:
        """Show the subset string currently applied to the layer."""
        text = text or ""
        self._current_filter_label.setText(self.tr("Current filter: {0}").format(text or self.tr("none")))
        self._current_filter_label.setToolTip(text)

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
        }

    def restore_state(self, state: Dict[str, Any]) -> None:
        """Restore a :meth:`state`; unknown classes, attributes and layers are ignored. Does not emit."""
        self._debounce.stop()
        parsed = parse_point_cloud_state(state)
        wanted = set(parsed["classes"])
        widgets = (self._classes_group, self._ranges_group, self._expression_group, self._classes_list,
                   self._hag_check, self._hag_spin, self._hag_layer_combo, self._apply_tiles_check)
        with _signals_blocked(*widgets):
            self._classes_group.setChecked(parsed["classes_enabled"])
            self._ranges_group.setChecked(parsed["ranges_enabled"])
            for item in self._class_items():
                checked = int(item.data(Qt.ItemDataRole.UserRole)) in wanted
                item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            self._update_class_summary()
            self._hag_check.setChecked(parsed["hag_enabled"])
            self._hag_spin.setValue(parsed["hag_min"])
            self._restore_hag_layer(parsed["hag_layer_id"])
            self._apply_tiles_check.setChecked(parsed["apply_to_tiles"])
            self._expression_group.setChecked(parsed["expression_enabled"])
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
        for group in self._exclusive_groups():
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
        self._debounce.start()

    # === Classes ===

    def _fill_classes(self, classes: Iterable[Tuple[int, int]]) -> None:
        classes = tuple(classes)
        if not classes:
            # Unknown classes: offer the standard ASPRS codes without counts.
            classes = tuple((code, -1) for code in sorted(ASPRS_CLASS_NAMES))
        with _signals_blocked(self._classes_list):
            self._classes_list.clear()
            for code, count in classes:
                item = QListWidgetItem(class_item_label(code, count))
                pixmap = QPixmap(12, 12)
                pixmap.fill(QColor(class_color(code)))
                item.setIcon(QIcon(pixmap))
                item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                item.setCheckState(Qt.CheckState.Unchecked)
                item.setData(Qt.ItemDataRole.UserRole, int(code))
                item.setData(CLASS_COUNT_ROLE, int(count))
                self._classes_list.addItem(item)
        present = self._present_codes()
        model = self._quick_combo.model()
        for index in range(self._quick_combo.count()):
            data = self._quick_combo.itemData(index)
            if data is not None and data[0] == "preset":
                model.item(index).setEnabled(bool(preset_codes(data[1], present)))
        self._update_class_summary()

    def _class_items(self) -> List[Any]:
        items = (self._classes_list.item(index) for index in range(self._classes_list.count()))
        return [item for item in items if item is not None]

    def _present_codes(self) -> List[int]:
        return [int(item.data(Qt.ItemDataRole.UserRole)) for item in self._class_items()]

    def _checked_codes(self) -> List[int]:
        return sorted(int(item.data(Qt.ItemDataRole.UserRole)) for item in self._class_items()
                      if item.checkState() == Qt.CheckState.Checked)

    def _check_codes(self, codes: Iterable[int]) -> None:
        wanted = set(codes)
        with _signals_blocked(self._classes_list):
            for item in self._class_items():
                checked = int(item.data(Qt.ItemDataRole.UserRole)) in wanted
                item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        self._update_class_summary()
        self._changed()

    def checked_class_codes(self) -> List[int]:
        """Codes of the checked classes, sorted."""
        return self._checked_codes()

    def select_class(self, code: int, extend: bool = False) -> bool:
        """Check the class picked on the map (added to the checked ones with ``extend``); False when not listed."""
        if int(code) not in self._present_codes() or self._classes_group.isHidden():
            return False
        if not self._classes_group.isChecked():
            extend = False  # classes left checked under another active group do not come back
            self._classes_group.setChecked(True)
        self._check_codes(picked_class_codes(self._checked_codes(), code, extend))
        return True

    def _set_all_classes(self, state: Any) -> None:
        self._check_codes(self._present_codes() if state == Qt.CheckState.Checked else ())

    def _apply_preset(self, name: str) -> None:
        self._check_codes(preset_codes(name, self._present_codes()))

    def _on_quick_selection(self, index: int) -> None:
        data = self._quick_combo.itemData(index)
        self._quick_combo.setCurrentIndex(0)  # a one-shot action, the combo stays on its title
        if data is None:
            return
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
        """Checked classes and the points they hold, under the list."""
        checked, shown, kept, total = self._class_counts()
        self._class_summary_label.setText(class_selection_summary(checked, shown, kept if checked else None, total))

    def class_point_counts(self) -> Tuple[Optional[int], Optional[int]]:
        """``(kept, total)`` points of the checked classes while CLASSES is the active group, else ``(None, None)``.

        Exact from the layer statistics; no class checked keeps no constraint (None).
        """
        if not self._classes_group.isChecked():
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
        names = self.condition_attributes()
        if not names:
            return
        used = {row.attribute() for row in self._condition_rows}
        name = next((name for name in names if name not in used), names[0])
        self._append_row({"attribute": name, "op": OP_BETWEEN, "low": None, "high": None, "join": JOIN_AND})
        self._changed()

    def _on_remove_condition(self, row: Any) -> None:
        if row in self._condition_rows:
            self._drop_row(row)
            self._update_first_row()
            self._changed()

    def _apply_return_preset(self, key: str) -> None:
        """Insert a return shortcut; it replaces the one already there (one return choice, as before)."""
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
