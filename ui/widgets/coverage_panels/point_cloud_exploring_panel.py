# -*- coding: utf-8 -*-
"""
Point Cloud EXPLORING Panel.

Shown in place of the vector exploring groups when the current layer is a
point cloud. Unlike the raster panel, its checkable groups add up: the
classes, the attribute ranges (Z, intensity, return, height above the DTM)
and the free expression all restrict the kept points. The resulting subset
expression becomes the source of FILTERING.

The panel only reads a ``PointCloudLayerSummary`` (and the DTM layer combo);
the state handling - criteria and expression building, presets, count
formatting - is done by pure functions of this module, testable without Qt.
"""
import math
from contextlib import contextmanager
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from qgis.PyQt.QtCore import Qt, QTimer, pyqtSignal
    from qgis.PyQt.QtGui import QColor, QIcon, QPixmap
    from qgis.PyQt.QtWidgets import (
        QCheckBox, QComboBox, QDoubleSpinBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
        QListWidget, QListWidgetItem, QPlainTextEdit, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
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

from ....core.domain.point_cloud_filter_criteria import (
    PointCloudFilterCriteria, PointCloudLayerSummary, format_number,
)
from ....core.domain.point_cloud_support import (
    ASPRS_CLASS_NAMES, CLASS_PRESETS, NOISE_CLASSES, asprs_class_label,
)
from ..point_cloud_filter_widget import build_criteria
from .histogram_widget import normalize_range, spin_bounds

Bound = Optional[float]

CLASSIFICATION_ATTRIBUTE = "Classification"
Z_ATTRIBUTE = "Z"
INTENSITY_ATTRIBUTE = "Intensity"
RETURN_NUMBER_ATTRIBUTE = "ReturnNumber"
NUMBER_OF_RETURNS_ATTRIBUTE = "NumberOfReturns"
HAG_ATTRIBUTE = "HeightAboveGround"

WITHOUT_NOISE_PRESET = "Without noise"
RETURN_FIRST = "first"
RETURN_LAST = "last"
RETURN_SINGLE = "single"
RETURN_CLAUSES = {
    RETURN_FIRST: f"{RETURN_NUMBER_ATTRIBUTE} = 1",
    RETURN_LAST: f"{RETURN_NUMBER_ATTRIBUTE} = {NUMBER_OF_RETURNS_ATTRIBUTE}",
    RETURN_SINGLE: f"{NUMBER_OF_RETURNS_ATTRIBUTE} = 1",
}
DEFAULT_RETURN_NUMBERS = 5
MAX_RETURN_NUMBERS = 15
Z_DECIMALS = 3
INTENSITY_DECIMALS = 0
DEFAULT_HAG_MIN = 2.0
SPIN_MIN_WIDTH = 64
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


def return_choices(max_return: int, has_number_of_returns: bool) -> List[Any]:
    """Data of the return combo: Any (None), First, Last, Single, then ``1..max_return``.

    Last and Single compare with ``NumberOfReturns`` and are left out without it.
    """
    choices: List[Any] = [None, RETURN_FIRST]
    if has_number_of_returns:
        choices += [RETURN_LAST, RETURN_SINGLE]
    count = max(1, min(MAX_RETURN_NUMBERS, int(max_return)))
    return choices + list(range(1, count + 1))


def return_criteria(choice: Any) -> Tuple[Optional[int], Tuple[str, ...]]:
    """``(return_number, extra_clauses)`` of a return combo choice."""
    if choice in RETURN_CLAUSES:
        return None, (RETURN_CLAUSES[choice],)
    if isinstance(choice, int) and not isinstance(choice, bool) and 1 <= choice <= MAX_RETURN_NUMBERS:
        return choice, ()
    return None, ()


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
    if value in RETURN_CLAUSES:
        return value
    if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= MAX_RETURN_NUMBERS:
        return value
    return None


def parse_point_cloud_state(state: Any) -> Dict[str, Any]:
    """Normalise a saved panel state (see :meth:`PointCloudExploringPanel.state`).

    Missing or invalid entries get their default; the function is idempotent.
    """
    state = state if isinstance(state, dict) else {}
    classes = set()
    for code in state.get("classes") or ():
        number = _optional_float(code)
        if number is not None and number.is_integer() and 0 <= number <= 255:
            classes.add(int(number))
    hag_min = _optional_float(state.get("hag_min"))
    hag_layer_id = state.get("hag_layer_id")
    return {
        "layer_id": state.get("layer_id"),
        "classes_enabled": bool(state.get("classes_enabled", True)),
        "classes": sorted(classes),
        "ranges_enabled": bool(state.get("ranges_enabled", False)),
        "z": _parse_bounds(state.get("z")),
        "intensity_enabled": bool(state.get("intensity_enabled", False)),
        "intensity": _parse_bounds(state.get("intensity")),
        "return": _parse_return(state.get("return")),
        "hag_enabled": bool(state.get("hag_enabled", False)),
        "hag_min": DEFAULT_HAG_MIN if hag_min is None else hag_min,
        "hag_layer_id": hag_layer_id if isinstance(hag_layer_id, str) and hag_layer_id else None,
        "expression_enabled": bool(state.get("expression_enabled", False)),
        "expression": str(state.get("expression") or ""),
        "apply_to_tiles": bool(state.get("apply_to_tiles", False)),
    }


def build_point_cloud_criteria(state: Any) -> PointCloudFilterCriteria:
    """Criteria of the checked groups: classes, then Z / intensity / return.

    First, Last and Single returns go through ``extra_clauses``; the height
    above the DTM is not part of the criteria (see :func:`build_point_cloud_expression`).
    """
    parsed = parse_point_cloud_state(state)
    codes = parsed["classes"] if parsed["classes_enabled"] else ()
    z_range = intensity_range = None
    return_number, extra_clauses = None, ()
    if parsed["ranges_enabled"]:
        z_range = parsed["z"]
        intensity_range = parsed["intensity"] if parsed["intensity_enabled"] else None
        return_number, extra_clauses = return_criteria(parsed["return"])
    criteria = build_criteria(codes, z_range, intensity_range, return_number)
    if not extra_clauses:
        return criteria
    return PointCloudFilterCriteria(
        classification_codes=criteria.classification_codes,
        ranges=criteria.ranges,
        return_number=criteria.return_number,
        extra_clauses=extra_clauses,
    )


def hag_from_state(state: Any, available: bool = True) -> Optional[Tuple[str, float]]:
    """``(DTM layer id, minimum height)`` when the height filter is usable and on, else None."""
    parsed = parse_point_cloud_state(state)
    if not (available and parsed["ranges_enabled"] and parsed["hag_enabled"] and parsed["hag_layer_id"]):
        return None
    return parsed["hag_layer_id"], parsed["hag_min"]


def build_point_cloud_expression(state: Any, hag_available: bool = True) -> str:
    """Subset expression of a panel state.

    The typed expression when the EXPRESSION group is checked, else the
    criteria of the other groups; ``HeightAboveGround >= x`` is appended in
    both cases when the height filter is on.
    """
    parsed = parse_point_cloud_state(state)
    if parsed["expression_enabled"]:
        base, wrap = parsed["expression"], True
    else:
        base, wrap = build_point_cloud_criteria(parsed).to_subset_string(), False
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


@contextmanager
def _signals_blocked(*widgets):
    """Block the signals of ``widgets`` for the duration of the block."""
    previous = [widget.blockSignals(True) for widget in widgets]
    try:
        yield
    finally:
        for widget, was_blocked in zip(widgets, previous):
            widget.blockSignals(was_blocked)


# ---------------------------------------------------------------------------
# Widget
# ---------------------------------------------------------------------------

class PointCloudExploringPanel(QWidget):
    """EXPLORING panel of a point cloud: classes, attribute ranges, expression.

    Signals:
        criteriaChanged(): The criteria or the expression changed (debounced by 250 ms).
        applyToTilesToggled(bool): "Apply to the other tiles of the dataset" toggled.
    """

    criteriaChanged = pyqtSignal()
    applyToTilesToggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        """Build the panel.

        Args:
            parent: Parent widget (the dock widget).
        """
        super().__init__(parent)
        self._summary: Optional[PointCloudLayerSummary] = None
        self._layer_id: Optional[str] = None
        self._z_bounds: Optional[Tuple[float, float]] = None
        self._intensity_bounds: Optional[Tuple[float, float]] = None
        self._hag_available = True
        self._hag_tooltip = ""
        self._custom_expression = ""
        self.setObjectName("widget_point_cloud_exploring_panel")
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(DEBOUNCE_MS)
        self._debounce.timeout.connect(self.criteriaChanged.emit)
        self._build_ui()
        self._fill_returns(DEFAULT_RETURN_NUMBERS, True)
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
        presets = QGridLayout()
        presets.setSpacing(2)
        self._preset_buttons: Dict[str, Any] = {}
        for index, name in enumerate([*CLASS_PRESETS, WITHOUT_NOISE_PRESET]):
            button = QPushButton(preset_titles.get(name, name), self._classes_group)
            button.setToolTip(self.tr("Check only these classes"))
            button.clicked.connect(lambda _checked=False, n=name: self._apply_preset(n))
            # Two columns: three made the panel wider than a 440 px dock (the EXPLORING area scrolled sideways).
            presets.addWidget(button, index // 2, index % 2)
            self._preset_buttons[name] = button
        group_layout.addLayout(presets)

        buttons_row = QHBoxLayout()
        button_all = QPushButton(self.tr("All"), self._classes_group)
        button_none = QPushButton(self.tr("None"), self._classes_group)
        button_all.clicked.connect(lambda: self._set_all_classes(Qt.CheckState.Checked))
        button_none.clicked.connect(lambda: self._set_all_classes(Qt.CheckState.Unchecked))
        buttons_row.addWidget(button_all)
        buttons_row.addWidget(button_none)
        buttons_row.addStretch()
        group_layout.addLayout(buttons_row)
        # FilterMate 5 design: the class list only (the presets stay usable from the code / state).
        for button in (*self._preset_buttons.values(), button_all, button_none):
            button.setVisible(False)
        group_layout.setSpacing(0)

        self._classes_list = QListWidget(self._classes_group)
        self._classes_list.setMaximumHeight(300)  # the whole ASPRS list, as in the mockup
        self._classes_list.setAccessibleName(self.tr("Point classes"))
        self._classes_list.itemChanged.connect(self._changed)
        group_layout.addWidget(self._classes_list)
        return self._classes_group

    def _make_spin(self, parent: Any, decimals: int, tip: str) -> Any:
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

    def _build_ranges_group(self) -> Any:
        self._ranges_group = self._make_group(self.tr("ATTRIBUTE RANGES"), "mGroupBox_point_cloud_ranges", checked=False)
        self._ranges_group.toggled.connect(self._changed)
        group = self._ranges_group
        grid = QGridLayout()
        grid.setSpacing(4)

        self._z_label = QLabel(self.tr("Z (m)"), group)
        self._z_min = self._make_spin(group, Z_DECIMALS, self.tr("Lowest elevation kept"))
        self._z_max = self._make_spin(group, Z_DECIMALS, self.tr("Highest elevation kept"))
        grid.addWidget(self._z_label, 0, 0)
        grid.addWidget(self._z_min, 0, 1)
        grid.addWidget(QLabel("–", group), 0, 2)
        grid.addWidget(self._z_max, 0, 3)
        for widget in (self._z_label, self._z_min, self._z_max):
            widget.setEnabled(False)  # until populate() brings the elevation statistics

        self._intensity_check = QCheckBox(self.tr("Intensity"), group)
        self._intensity_min = self._make_spin(group, INTENSITY_DECIMALS, self.tr("Lowest intensity kept"))
        self._intensity_max = self._make_spin(group, INTENSITY_DECIMALS, self.tr("Highest intensity kept"))
        self._intensity_check.toggled.connect(self._on_intensity_toggled)
        grid.addWidget(self._intensity_check, 1, 0)
        grid.addWidget(self._intensity_min, 1, 1)
        grid.addWidget(QLabel("–", group), 1, 2)
        grid.addWidget(self._intensity_max, 1, 3)

        for low_spin, high_spin in ((self._z_min, self._z_max), (self._intensity_min, self._intensity_max)):
            low_spin.valueChanged.connect(lambda value, h=high_spin: self._on_low_spin_changed(value, h))
            high_spin.valueChanged.connect(lambda value, lo=low_spin: self._on_high_spin_changed(value, lo))

        self._return_label = QLabel(self.tr("Return"), group)
        self._return_combo = QComboBox(group)
        self._return_combo.setToolTip(self.tr("Echo of the laser pulse kept"))
        self._return_combo.currentIndexChanged.connect(self._changed)
        grid.addWidget(self._return_label, 2, 0)
        grid.addWidget(self._return_combo, 2, 1, 1, 3)

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
        grid.addWidget(self._hag_check, 3, 0, 1, 4)
        grid.addWidget(self._hag_spin, 4, 1)
        grid.addWidget(self._hag_layer_combo, 4, 2, 1, 2)
        self._hag_tooltip = self.tr("Keep the points at least this high above the terrain model")
        self._hag_check.setToolTip(self._hag_tooltip)

        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        group.layout().addLayout(grid)
        return group

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

        self._z_bounds = summary_bounds(summary, Z_ATTRIBUTE) if attribute_available(attributes, Z_ATTRIBUTE) else None
        self._calibrate(self._z_min, self._z_max, self._z_bounds, Z_DECIMALS)
        for widget in (self._z_label, self._z_min, self._z_max):
            widget.setEnabled(self._z_bounds is not None)
            widget.setToolTip("" if self._z_bounds is not None else self.tr("No elevation statistics for this layer"))

        has_intensity = attribute_available(attributes, INTENSITY_ATTRIBUTE)
        self._intensity_bounds = summary_bounds(summary, INTENSITY_ATTRIBUTE) if has_intensity else None
        self._calibrate(self._intensity_min, self._intensity_max, self._intensity_bounds, INTENSITY_DECIMALS)
        for widget in (self._intensity_check, self._intensity_min, self._intensity_max):
            widget.setVisible(has_intensity)
        self._intensity_check.setEnabled(self._intensity_bounds is not None)

        has_returns = attribute_available(attributes, RETURN_NUMBER_ATTRIBUTE)
        return_bounds = summary_bounds(summary, RETURN_NUMBER_ATTRIBUTE)
        max_return = int(return_bounds[1]) if return_bounds is not None else DEFAULT_RETURN_NUMBERS
        self._fill_returns(max_return, attribute_available(attributes, NUMBER_OF_RETURNS_ATTRIBUTE))
        self._return_label.setVisible(has_returns)
        self._return_combo.setVisible(has_returns)

        if saved is not None:
            self.restore_state(saved)
        else:
            self.reset()
        self.set_current_subset(summary.current_subset or "")

    def criteria(self) -> PointCloudFilterCriteria:
        """Criteria of the checked CLASSES and ATTRIBUTE RANGES groups (height above DTM excluded)."""
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
        """Show ``Kept points: 9.8 M / 38.4 M (25.5 %)``; hidden without a kept count."""
        text = format_point_counts(kept, total)
        self._counts_label.setText(self.tr("Kept points: {0}").format(text) if text else "")
        self._counts_label.setVisible(bool(text))

    def set_current_subset(self, text: str) -> None:
        """Show the subset string currently applied to the layer."""
        text = text or ""
        self._current_filter_label.setText(self.tr("Current filter: {0}").format(text or self.tr("none")))
        self._current_filter_label.setToolTip(text)

    def reset(self) -> None:
        """Back to the defaults (no class, full ranges, any return, no height, no expression). Does not emit."""
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
            "z": self._spin_range(self._z_min, self._z_max, self._z_bounds),
            "intensity_enabled": self._intensity_check.isChecked(),
            "intensity": self._spin_range(self._intensity_min, self._intensity_max, self._intensity_bounds),
            "return": self._return_combo.currentData(),
            "hag_enabled": self._hag_check.isChecked(),
            "hag_min": float(self._hag_spin.value()),
            "hag_layer_id": layer.id() if layer is not None else None,
            "expression_enabled": expression_enabled,
            "expression": self._expression_edit.toPlainText() if expression_enabled else self._custom_expression,
            "apply_to_tiles": self._apply_tiles_check.isChecked(),
        }

    def restore_state(self, state: Dict[str, Any]) -> None:
        """Restore a :meth:`state`; unknown classes, returns and layers are ignored. Does not emit."""
        self._debounce.stop()
        parsed = parse_point_cloud_state(state)
        wanted = set(parsed["classes"])
        widgets = (self._classes_group, self._ranges_group, self._expression_group, self._classes_list,
                   self._z_min, self._z_max, self._intensity_check, self._intensity_min, self._intensity_max,
                   self._return_combo, self._hag_check, self._hag_spin, self._hag_layer_combo,
                   self._apply_tiles_check)
        with _signals_blocked(*widgets):
            self._classes_group.setChecked(parsed["classes_enabled"])
            self._ranges_group.setChecked(parsed["ranges_enabled"])
            for item in self._class_items():
                checked = int(item.data(Qt.ItemDataRole.UserRole)) in wanted
                item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            self._show_spin_range(self._z_min, self._z_max, parsed["z"])
            self._intensity_check.setChecked(parsed["intensity_enabled"] and self._intensity_bounds is not None)
            self._show_spin_range(self._intensity_min, self._intensity_max, parsed["intensity"])
            self._set_intensity_spins_enabled(self._intensity_check.isChecked())
            index = self._return_index(parsed["return"])
            self._return_combo.setCurrentIndex(index if index >= 0 else 0)
            self._hag_check.setChecked(parsed["hag_enabled"])
            self._hag_spin.setValue(parsed["hag_min"])
            self._restore_hag_layer(parsed["hag_layer_id"])
            self._apply_tiles_check.setChecked(parsed["apply_to_tiles"])
            self._expression_group.setChecked(parsed["expression_enabled"])
        self._custom_expression = parsed["expression"]
        self._apply_expression_mode(parsed["expression_enabled"])

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
                self._classes_list.addItem(item)
        present = self._present_codes()
        for name, button in self._preset_buttons.items():
            button.setEnabled(bool(preset_codes(name, present)))

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
        self._changed()

    def _set_all_classes(self, state: Any) -> None:
        self._check_codes(self._present_codes() if state == Qt.CheckState.Checked else ())

    def _apply_preset(self, name: str) -> None:
        self._check_codes(preset_codes(name, self._present_codes()))

    # === Ranges ===

    def _calibrate(self, low_spin: Any, high_spin: Any, bounds: Optional[Tuple[float, float]], decimals: int) -> None:
        """Spin box range rounded outwards from the exact data bounds."""
        low, high = spin_bounds(*(bounds or (None, None)), decimals)
        with _signals_blocked(low_spin, high_spin):
            for spin in (low_spin, high_spin):
                spin.setDecimals(decimals)
                spin.setRange(low, high)
            low_spin.setValue(low)
            high_spin.setValue(high)

    @staticmethod
    def _spin_range(low_spin: Any, high_spin: Any, bounds: Optional[Tuple[float, float]]) -> Tuple[Bound, Bound]:
        """Bounds set by the spin boxes; a spin box at the data bound means "no bound"."""
        if bounds is None:
            return None, None
        return normalize_range(float(low_spin.value()), float(high_spin.value()), *bounds)

    @staticmethod
    def _show_spin_range(low_spin: Any, high_spin: Any, bounds: Tuple[Bound, Bound]) -> None:
        low, high = bounds
        low_spin.setValue(low_spin.minimum() if low is None else low)
        high_spin.setValue(high_spin.maximum() if high is None else high)

    def _on_low_spin_changed(self, value: float, high_spin: Any) -> None:
        if value > high_spin.value():
            with _signals_blocked(high_spin):
                high_spin.setValue(value)
        self._changed()

    def _on_high_spin_changed(self, value: float, low_spin: Any) -> None:
        if value < low_spin.value():
            with _signals_blocked(low_spin):
                low_spin.setValue(value)
        self._changed()

    def _set_intensity_spins_enabled(self, enabled: bool) -> None:
        self._intensity_min.setEnabled(enabled)
        self._intensity_max.setEnabled(enabled)

    def _on_intensity_toggled(self, checked: bool) -> None:
        self._set_intensity_spins_enabled(checked)
        self._changed()

    # === Return ===

    def _fill_returns(self, max_return: int, has_number_of_returns: bool) -> None:
        titles = {None: self.tr("Any"), RETURN_FIRST: self.tr("First"),
                  RETURN_LAST: self.tr("Last"), RETURN_SINGLE: self.tr("Single")}
        with _signals_blocked(self._return_combo):
            self._return_combo.clear()
            for choice in return_choices(max_return, has_number_of_returns):
                self._return_combo.addItem(titles.get(choice, str(choice)), choice)
            self._return_combo.setCurrentIndex(0)

    def _return_index(self, choice: Any) -> int:
        for index in range(self._return_combo.count()):
            if self._return_combo.itemData(index) == choice:
                return index
        return -1

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
        text = self._custom_expression if editable else self.criteria().to_subset_string()
        with _signals_blocked(self._expression_edit):
            self._expression_edit.setPlainText(text)

    def _refresh_generated_expression(self) -> None:
        if not self._expression_group.isChecked():
            with _signals_blocked(self._expression_edit):
                self._expression_edit.setPlainText(self.criteria().to_subset_string())

    def _on_expression_toggled(self, checked: bool) -> None:
        if checked:
            # Start from the generated expression the first time.
            if not self._custom_expression.strip():
                self._custom_expression = self.criteria().to_subset_string()
        else:
            self._custom_expression = self._expression_edit.toPlainText()
        self._apply_expression_mode(checked)
        self._debounce.start()

    def _on_expression_edited(self) -> None:
        if self._expression_group.isChecked():
            self._debounce.start()
