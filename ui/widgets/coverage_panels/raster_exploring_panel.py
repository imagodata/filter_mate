# -*- coding: utf-8 -*-
"""
Raster EXPLORING Panel.

Shown in place of the vector exploring groups when the current layer is a
raster. The user picks pixels by value range (histogram + spin boxes), by
class (paletted rasters) or with a raster calculator expression; the three
checkable groups are exclusive like the vector ones. The resulting
:class:`RasterSelection` becomes the source geometry of FILTERING.

The panel never reads the layer: the controller feeds it a ``RasterSummary``,
histograms and picked pixel values, and listens to its signals. The state
handling (selection building, value formatting, range extension) is done by
pure functions of this module, testable without Qt.
"""
import math
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from qgis.PyQt.QtCore import Qt, QTimer, pyqtSignal
    from qgis.PyQt.QtGui import QColor, QFontDatabase, QIcon, QPixmap
    from qgis.PyQt.QtWidgets import (
        QCheckBox, QComboBox, QDoubleSpinBox, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
        QListWidget, QListWidgetItem, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
    )
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    QWidget = object

    def pyqtSignal(*_args):
        """Placeholder signal when Qt is unavailable."""
        return None

try:
    from qgis.gui import QgsCollapsibleGroupBox
except ImportError:
    QgsCollapsibleGroupBox = None

from ....core.domain.raster_filter_criteria import RasterSelection, RasterSelectionMode
from .histogram_widget import RangeHistogramWidget, normalize_range, spin_bounds

if TYPE_CHECKING:
    from ....adapters.qgis.coverage_layers.raster_adapter import RasterSummary

Bound = Optional[float]

INTEGER_DATA_TYPES = frozenset({"Byte", "Int8", "UInt16", "Int16", "UInt32", "Int32", "Int64", "UInt64"})
FLOAT_DECIMALS = 3
HISTORY_SIZE = 5
DEBOUNCE_MS = 250
DEFAULT_REFERENCE = "raster"
_STATUS_OK_COLOR = "#2e7d32"
_STATUS_ERROR_COLOR = "#c62828"


# ---------------------------------------------------------------------------
# Pure helpers (no Qt)
# ---------------------------------------------------------------------------

def decimals_for(data_type: str) -> int:
    """Decimals shown for a band: 0 for integer data types, 3 otherwise."""
    return 0 if data_type in INTEGER_DATA_TYPES else FLOAT_DECIMALS


def band_label(number: int, name: str, data_type: str) -> str:
    """Band combo entry, such as ``"1 — elevation (Float32)"``."""
    name = (name or "").strip()
    if name:
        return f"{number} — {name} ({data_type})"
    return f"{number} ({data_type})"


def format_class_value(value: float) -> str:
    """Class value without a useless ``.0`` (``3.0`` -> ``"3"``)."""
    value = float(value)
    return str(int(value)) if value.is_integer() else f"{value:g}"


def format_pixel_value(value: Optional[float], decimals: int, nodata_text: str = "NoData") -> str:
    """Pixel value with the band decimals, ``nodata_text`` for None."""
    if value is None:
        return nodata_text
    return f"{float(value):.{max(0, int(decimals))}f}"


def coordinate_decimals(pixel_size: float) -> int:
    """Decimals that resolve a tenth of a pixel (2 when the pixel size is unknown)."""
    try:
        size = abs(float(pixel_size))
    except (TypeError, ValueError):
        return 2
    if not math.isfinite(size) or size <= 0:
        return 2
    return max(0, math.ceil(-math.log10(size))) + 1


def format_percent(ratio: Optional[float]) -> str:
    """Fraction in [0, 1] as ``"31.2 %"``; ``"–"`` when unknown."""
    if ratio is None:
        return "–"
    return f"{float(ratio) * 100:.1f} %"


def extend_range(low: Bound, high: Bound, value: float) -> Tuple[Bound, Bound]:
    """Grow ``[low, high]`` so it contains ``value``.

    A range with no bound at all starts at ``[value, value]``: extending
    "every value" would otherwise be a no-op for a Ctrl+click on the map. A
    single unbounded side stays unbounded.
    """
    value = float(value)
    if low is None and high is None:
        return value, value
    if low is not None:
        low = min(low, value)
    if high is not None:
        high = max(high, value)
    return low, high


def push_history(history: Sequence[Any], entry: Any, size: int = HISTORY_SIZE) -> List[Any]:
    """Return ``history`` with ``entry`` first, truncated to ``size`` items."""
    return [entry, *list(history)][:max(0, int(size))]


def sanitize_reference(name: str) -> str:
    """Layer name usable as a raster calculator reference (same rule as the adapter)."""
    return "".join(char if char.isalnum() or char == "_" else "_" for char in (name or "")) or DEFAULT_REFERENCE


def range_formula(band: int, low: Bound, high: Bound, reference: str) -> str:
    """Raster calculator formula of a value range, ``""`` when the range is unbounded."""
    if low is None and high is None:
        return ""
    if low is not None and high is not None and low > high:
        low, high = high, low
    return RasterSelection(band=max(1, int(band)), mode=RasterSelectionMode.RANGE,
                           minimum=low, maximum=high).to_calc_formula(reference)


def _optional_float(value: Any) -> Bound:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def parse_raster_state(state: Any) -> Dict[str, Any]:
    """Normalise a saved panel state; missing or invalid entries get their default.

    Returns:
        Dict with ``layer_id``, ``mode`` (RasterSelectionMode), ``band`` (>= 1),
        ``minimum`` / ``maximum`` (ordered, None = unbounded), ``classes``
        (sorted ints), ``expression`` and ``preview``.
    """
    state = state if isinstance(state, dict) else {}
    try:
        mode = RasterSelectionMode(state.get("mode", RasterSelectionMode.RANGE.value))
    except ValueError:
        mode = RasterSelectionMode.RANGE
    try:
        band = max(1, int(state.get("band", 1)))
    except (TypeError, ValueError):
        band = 1
    low, high = _optional_float(state.get("minimum")), _optional_float(state.get("maximum"))
    if low is not None and high is not None and low > high:
        low, high = high, low
    classes = set()
    for value in state.get("classes") or ():
        number = _optional_float(value)
        if number is not None:
            classes.add(int(round(number)))
    return {
        "layer_id": state.get("layer_id"),
        "mode": mode,
        "band": band,
        "minimum": low,
        "maximum": high,
        "classes": sorted(classes),
        "expression": str(state.get("expression") or ""),
        "preview": bool(state.get("preview", False)),
    }


def build_raster_selection(state: Any) -> Optional[RasterSelection]:
    """Selection described by a panel state (see :meth:`RasterExploringPanel.state`).

    Returns:
        The RasterSelection of the active mode, None when it keeps no constraint.
    """
    parsed = parse_raster_state(state)
    mode = parsed["mode"]
    if mode is RasterSelectionMode.RANGE:
        selection = RasterSelection(band=parsed["band"], mode=mode,
                                    minimum=parsed["minimum"], maximum=parsed["maximum"])
    elif mode is RasterSelectionMode.CLASSES:
        selection = RasterSelection(band=parsed["band"], mode=mode, classes=frozenset(parsed["classes"]))
    else:
        selection = RasterSelection(band=parsed["band"], mode=mode, expression=parsed["expression"].strip())
    return None if selection.is_empty else selection


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

class RasterExploringPanel(QWidget):
    """EXPLORING panel of a raster layer: band, pixel value, range, classes, expression.

    Signals:
        bandChanged(int): The user picked another band (the controller then
            sends its histogram with :meth:`set_histogram`).
        selectionChanged(): The selection changed; debounced by 250 ms for
            the spin boxes, the histogram, the class list and the expression.
        previewToggled(bool): The "Preview on the map" box was toggled.
    """

    bandChanged = pyqtSignal(int)
    selectionChanged = pyqtSignal()
    previewToggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        """Build the panel.

        Args:
            parent: Parent widget (the dock widget).
        """
        super().__init__(parent)
        self._summary: Optional['RasterSummary'] = None
        self._layer_id: Optional[str] = None
        self._reference = DEFAULT_REFERENCE
        self._mode = RasterSelectionMode.RANGE
        self._low: Bound = None
        self._high: Bound = None
        self._decimals = FLOAT_DECIMALS
        self._coordinate_decimals = 2
        self._histograms: Dict[int, Tuple[List[int], float, float]] = {}
        self._last_pixel: Optional[Tuple[float, float, Dict[int, Optional[float]]]] = None
        self._history: List[Tuple[float, float, Optional[float], int]] = []
        self._switching_mode = False
        self.setObjectName("widget_raster_exploring_panel")
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(DEBOUNCE_MS)
        self._debounce.timeout.connect(self.selectionChanged.emit)
        self._build_ui()
        self._activate_mode(RasterSelectionMode.RANGE, emit=False)

    # === Construction ===

    def _make_group(self, title: str, object_name: str, checkable: bool) -> Any:
        if QgsCollapsibleGroupBox is not None:
            group = QgsCollapsibleGroupBox(title, self)
            group.setSaveCollapsedState(False)
            group.setSaveCheckedState(False)
        else:
            group = QGroupBox(title, self)
        group.setObjectName(object_name)
        group.setFlat(True)
        group.setCheckable(checkable)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        return group

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        band_row = QHBoxLayout()
        band_row.addWidget(QLabel(self.tr("Band"), self))
        self._band_combo = QComboBox(self)
        self._band_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._band_combo.setToolTip(self.tr("Band whose values are selected"))
        self._band_combo.currentIndexChanged.connect(self._on_band_index_changed)
        band_row.addWidget(self._band_combo)
        layout.addLayout(band_row)

        layout.addWidget(self._build_pixel_group())
        layout.addWidget(self._build_range_group())
        layout.addWidget(self._build_classes_group())
        layout.addWidget(self._build_expression_group())
        layout.addStretch()

        self._mode_groups = {
            RasterSelectionMode.RANGE: self._range_group,
            RasterSelectionMode.CLASSES: self._classes_group,
            RasterSelectionMode.EXPRESSION: self._expression_group,
        }
        for mode, group in self._mode_groups.items():
            group.toggled.connect(lambda checked, m=mode: self._on_group_toggled(m, checked))
            if hasattr(group, "collapsedStateChanged"):
                group.collapsedStateChanged.connect(lambda collapsed, m=mode: self._on_group_collapsed(m, collapsed))
        self._classes_group.setVisible(False)

    def _build_pixel_group(self) -> Any:
        group = self._make_group(self.tr("PIXEL VALUE"), "mGroupBox_raster_pixel_value", checkable=False)
        group_layout = group.layout()
        self._pixel_value_label = QLabel("–", group)
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setPointSizeF(max(font.pointSizeF(), 9.0) + 6.0)
        font.setBold(True)
        self._pixel_value_label.setFont(font)
        self._pixel_value_label.setAccessibleName(self.tr("Pixel value of the current band"))
        self._pixel_value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        group_layout.addWidget(self._pixel_value_label)
        self._pixel_coordinates_label = QLabel("", group)
        self._pixel_coordinates_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        group_layout.addWidget(self._pixel_coordinates_label)
        self._pixel_bands_label = QLabel("", group)
        self._pixel_bands_label.setWordWrap(True)
        group_layout.addWidget(self._pixel_bands_label)
        self._pixel_history_label = QLabel("", group)
        self._pixel_history_label.setWordWrap(True)
        self._pixel_history_label.setToolTip(self.tr("Last {0} values picked").format(HISTORY_SIZE))
        group_layout.addWidget(self._pixel_history_label)
        help_label = QLabel(self.tr("Click on the map with the pixel picker. Ctrl+click extends the range to the value."), group)
        help_label.setWordWrap(True)
        help_font = help_label.font()
        help_font.setItalic(True)
        help_label.setFont(help_font)
        group_layout.addWidget(help_label)
        return group

    def _build_range_group(self) -> Any:
        self._range_group = self._make_group(self.tr("VALUE RANGE"), "mGroupBox_raster_value_range", checkable=True)
        group_layout = self._range_group.layout()
        self._histogram = RangeHistogramWidget(self._range_group)
        self._histogram.rangeChanged.connect(self._on_histogram_range_changed)
        group_layout.addWidget(self._histogram)

        spins_row = QHBoxLayout()
        self._min_spin = QDoubleSpinBox(self._range_group)
        self._max_spin = QDoubleSpinBox(self._range_group)
        for spin, label, tip in ((self._min_spin, self.tr("Min"), self.tr("Lowest value kept")),
                                 (self._max_spin, self.tr("Max"), self.tr("Highest value kept"))):
            spin.setDecimals(self._decimals)
            spin.setRange(*spin_bounds(None, None, self._decimals))
            spin.setKeyboardTracking(False)
            spin.setToolTip(tip)
            spin.setAccessibleName(tip)
            spin.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            spins_row.addWidget(QLabel(label, self._range_group))
            spins_row.addWidget(spin)
        self._min_spin.valueChanged.connect(self._on_min_spin_changed)
        self._max_spin.valueChanged.connect(self._on_max_spin_changed)
        group_layout.addLayout(spins_row)

        self._kept_ratio_label = QLabel("", self._range_group)
        group_layout.addWidget(self._kept_ratio_label)
        self._preview_check = QCheckBox(self.tr("Preview on the map (hide the other pixels)"), self._range_group)
        self._preview_check.toggled.connect(self.previewToggled.emit)
        group_layout.addWidget(self._preview_check)
        self.set_kept_ratio(None)
        return self._range_group

    def _build_classes_group(self) -> Any:
        self._classes_group = self._make_group(self.tr("CLASSES"), "mGroupBox_raster_classes", checkable=True)
        group_layout = self._classes_group.layout()
        self._classes_list = QListWidget(self._classes_group)
        self._classes_list.setMaximumHeight(200)
        self._classes_list.setAccessibleName(self.tr("Raster classes"))
        self._classes_list.itemChanged.connect(self._schedule_selection_changed)
        group_layout.addWidget(self._classes_list)
        buttons_row = QHBoxLayout()
        button_all = QPushButton(self.tr("All"), self._classes_group)
        button_none = QPushButton(self.tr("None"), self._classes_group)
        button_all.clicked.connect(lambda: self._set_all_classes(Qt.CheckState.Checked))
        button_none.clicked.connect(lambda: self._set_all_classes(Qt.CheckState.Unchecked))
        buttons_row.addWidget(button_all)
        buttons_row.addWidget(button_none)
        buttons_row.addStretch()
        group_layout.addLayout(buttons_row)
        return self._classes_group

    def _build_expression_group(self) -> Any:
        self._expression_group = self._make_group(self.tr("RASTER EXPRESSION"), "mGroupBox_raster_expression", checkable=True)
        group_layout = self._expression_group.layout()
        self._expression_edit = QLineEdit(self._expression_group)
        self._expression_edit.setPlaceholderText('"mnt@1" > 200 AND "pente@1" < 15')
        self._expression_edit.setToolTip(self.tr("Raster calculator expression; a pixel is kept where it is not 0"))
        self._expression_edit.setAccessibleName(self.tr("Raster expression"))
        self._expression_edit.textChanged.connect(self._schedule_selection_changed)
        group_layout.addWidget(self._expression_edit)
        self._expression_status = QLabel("", self._expression_group)
        self._expression_status.setWordWrap(True)
        group_layout.addWidget(self._expression_status)
        buttons_row = QHBoxLayout()
        buttons_row.addStretch()
        use_range = QPushButton(self.tr("Use the range"), self._expression_group)
        use_range.setToolTip(self.tr("Write the current value range as an expression"))
        use_range.clicked.connect(self._use_range_as_expression)
        buttons_row.addWidget(use_range)
        group_layout.addLayout(buttons_row)
        return self._expression_group

    # === Public API ===

    def set_summary(self, summary: 'RasterSummary') -> None:
        """Fill the bands and classes from a ``RasterSummary``.

        The current input is kept when ``summary`` describes the layer already
        shown (refresh); another layer starts from a reset panel.
        """
        same_layer = self._summary is not None and summary.layer_id == self._layer_id
        saved = self.state() if same_layer else None
        self._summary = summary
        self._layer_id = summary.layer_id
        if not same_layer:
            self._histograms.clear()
            self._reference = sanitize_reference(summary.layer_name)
        self._coordinate_decimals = coordinate_decimals(min(summary.pixel_size_x, summary.pixel_size_y))

        with _signals_blocked(self._band_combo):
            self._band_combo.clear()
            for info in summary.bands:
                self._band_combo.addItem(band_label(info.number, info.name, info.data_type), int(info.number))
        self._fill_classes(summary.classes)
        if saved is not None:
            self.restore_state(saved)
        else:
            self.reset()

    def set_histogram(self, band: int, counts: Sequence[int], minimum: float, maximum: float) -> None:
        """Store the histogram of ``band``; shown at once when it is the current band.

        Does not emit ``selectionChanged``.
        """
        self._histograms[int(band)] = ([int(count) for count in counts or ()], float(minimum), float(maximum))
        if int(band) == self.current_band():
            self._show_band_histogram()
            self._set_range(self._low, self._high)

    def selection(self) -> Optional[RasterSelection]:
        """Selection of the active group, None when it keeps no constraint."""
        return build_raster_selection(self.state())

    def set_selection(self, selection: RasterSelection) -> None:
        """Show ``selection`` (band, mode and its values). Does not emit."""
        state = self.state()
        state.update(selection.to_dict())
        self.restore_state(state)

    def active_mode(self) -> RasterSelectionMode:
        """Mode of the checked group."""
        return self._mode

    def preview_enabled(self) -> bool:
        """Whether the map preview is asked for a mode it supports (range or classes)."""
        return self._preview_check.isChecked() and self._mode is not RasterSelectionMode.EXPRESSION

    def current_band(self) -> int:
        """1-based number of the selected band (1 when no band is listed)."""
        value = self._band_combo.currentData()
        return 1 if value is None else int(value)

    def set_reference(self, name: str) -> None:
        """Name of the layer in raster calculator formulas (``"mnt"`` -> ``"mnt@1"``)."""
        self._reference = name or DEFAULT_REFERENCE

    def set_kept_ratio(self, ratio: Optional[float]) -> None:
        """Show the fraction (0-1) of pixels kept by the selection, None when unknown."""
        self._kept_ratio_label.setText(self.tr("Selected pixels: {0}").format(format_percent(ratio)))

    def set_expression_status(self, ok: bool, message: str) -> None:
        """Show the validation result of the raster expression."""
        self._expression_status.setText(message or "")
        color = _STATUS_OK_COLOR if ok else _STATUS_ERROR_COLOR
        self._expression_status.setStyleSheet(f"color: {color};" if message else "")

    def set_pixel_values(self, x: float, y: float, values: Dict[int, Optional[float]], extend: bool = False) -> None:
        """Show the values picked at ``(x, y)`` (one per band, None for NoData).

        Args:
            x: Map abscissa of the click (layer CRS).
            y: Map ordinate of the click.
            values: Band number -> value.
            extend: Ctrl+click; in RANGE mode the range grows to contain the
                value of the current band and ``selectionChanged`` is emitted.
        """
        values = dict(values or {})
        self._last_pixel = (float(x), float(y), values)
        band = self.current_band()
        self._history = push_history(self._history, (float(x), float(y), values.get(band), band))
        self._refresh_pixel_display()
        value = values.get(band)
        if extend and value is not None and self._mode is RasterSelectionMode.RANGE:
            self._set_range(*extend_range(self._low, self._high, value))
            self._emit_now()

    def reset(self) -> None:
        """Back to the defaults: first band, no range, no class, no expression. Does not emit."""
        self._debounce.stop()
        if self._band_combo.count():
            with _signals_blocked(self._band_combo):
                self._band_combo.setCurrentIndex(0)
        self._apply_band()
        self._set_range(None, None)
        self._set_all_classes(Qt.CheckState.Unchecked, emit=False)
        with _signals_blocked(self._expression_edit, self._preview_check):
            self._expression_edit.clear()
            self._preview_check.setChecked(False)
        self.set_expression_status(True, "")
        self.set_kept_ratio(None)
        self._last_pixel = None
        self._history = []
        self._refresh_pixel_display()
        self._activate_mode(self._default_mode(), emit=False)

    def state(self) -> Dict[str, Any]:
        """Input of the panel, to keep it per layer (see :meth:`restore_state`)."""
        return {
            "layer_id": self._layer_id,
            "mode": self._mode.value,
            "band": self.current_band(),
            "minimum": self._low,
            "maximum": self._high,
            "classes": self._checked_classes(),
            "expression": self._expression_edit.text(),
            "preview": self._preview_check.isChecked(),
        }

    def restore_state(self, state: Dict[str, Any]) -> None:
        """Restore a :meth:`state`; unknown bands and classes are ignored. Does not emit."""
        self._debounce.stop()
        parsed = parse_raster_state(state)
        index = self._band_combo.findData(parsed["band"])
        if index >= 0:
            with _signals_blocked(self._band_combo):
                self._band_combo.setCurrentIndex(index)
        self._apply_band()
        self._set_range(parsed["minimum"], parsed["maximum"])
        wanted = set(parsed["classes"])
        with _signals_blocked(self._classes_list):
            for item in self._class_items():
                checked = int(item.data(Qt.ItemDataRole.UserRole)) in wanted
                item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        with _signals_blocked(self._expression_edit, self._preview_check):
            self._expression_edit.setText(parsed["expression"])
            self._preview_check.setChecked(parsed["preview"])
        mode = parsed["mode"]
        if mode is RasterSelectionMode.CLASSES and not self._has_classes():
            mode = RasterSelectionMode.RANGE
        self._activate_mode(mode, emit=False)
        self._refresh_pixel_display()

    # === Modes (exclusive groups) ===

    def _has_classes(self) -> bool:
        return self._classes_list.count() > 0

    def _default_mode(self) -> RasterSelectionMode:
        return RasterSelectionMode.CLASSES if self._has_classes() else RasterSelectionMode.RANGE

    def _activate_mode(self, mode: RasterSelectionMode, emit: bool = True) -> None:
        """Check the group of ``mode``, uncheck and collapse the others."""
        self._switching_mode = True
        try:
            for group_mode, group in self._mode_groups.items():
                active = group_mode is mode
                with _signals_blocked(group):
                    group.setChecked(active)
                    if hasattr(group, "setCollapsed"):
                        group.setCollapsed(not active)
        finally:
            self._switching_mode = False
        changed = mode is not self._mode
        self._mode = mode
        if emit and changed:
            self._emit_now()

    def _on_group_toggled(self, mode: RasterSelectionMode, checked: bool) -> None:
        if self._switching_mode:
            return
        if checked:
            self._activate_mode(mode)
            return
        # Unchecking the active group leaves nothing selected: keep it checked,
        # as the vector exploring groups do.
        group = self._mode_groups[mode]
        with _signals_blocked(group):
            group.setChecked(True)

    def _on_group_collapsed(self, mode: RasterSelectionMode, collapsed: bool) -> None:
        # Expanding a group makes it the active one, as for the vector groups.
        if self._switching_mode or collapsed or mode is self._mode:
            return
        if mode is RasterSelectionMode.CLASSES and not self._has_classes():
            return
        self._activate_mode(mode)

    # === Selection change notification ===

    def _schedule_selection_changed(self, *_args) -> None:
        self._debounce.start()

    def _emit_now(self) -> None:
        self._debounce.stop()
        self.selectionChanged.emit()

    # === Band ===

    def _band_info(self, number: int) -> Any:
        if self._summary is None:
            return None
        for info in self._summary.bands:
            if int(info.number) == number:
                return info
        return None

    def _apply_band(self) -> None:
        """Adopt the decimals and the cached histogram of the current band."""
        info = self._band_info(self.current_band())
        self._decimals = decimals_for(info.data_type) if info is not None else FLOAT_DECIMALS
        self._histogram.set_decimals(self._decimals)
        with _signals_blocked(self._min_spin, self._max_spin):
            self._min_spin.setDecimals(self._decimals)
            self._max_spin.setDecimals(self._decimals)
        self._show_band_histogram()

    def _show_band_histogram(self) -> None:
        counts, minimum, maximum = self._histograms.get(self.current_band(), ([], 0.0, 0.0))
        self._histogram.set_histogram(counts, minimum, maximum)
        low, high = spin_bounds(*self._data_bounds(), self._decimals)
        with _signals_blocked(self._min_spin, self._max_spin):
            for spin in (self._min_spin, self._max_spin):
                spin.setRange(low, high)

    def _data_bounds(self) -> Tuple[Bound, Bound]:
        cached = self._histograms.get(self.current_band())
        if cached is None:
            return None, None
        return cached[1], cached[2]

    def _on_band_index_changed(self, _index: int) -> None:
        self._apply_band()
        self._set_range(None, None)
        self._refresh_pixel_display()
        self.bandChanged.emit(self.current_band())
        self._emit_now()

    # === Range ===

    def _set_range(self, low: Bound, high: Bound) -> None:
        """Store the range (normalised against the data) and show it everywhere, without emitting."""
        if low is not None and high is not None and low > high:
            low, high = high, low
        self._low, self._high = normalize_range(low, high, *self._data_bounds())
        self._histogram.set_range(self._low, self._high)
        with _signals_blocked(self._min_spin, self._max_spin):
            self._min_spin.setValue(self._min_spin.minimum() if self._low is None else self._low)
            self._max_spin.setValue(self._max_spin.maximum() if self._high is None else self._high)

    def _on_histogram_range_changed(self, _low: float, _high: float) -> None:
        self._set_range(*self._histogram.range())
        self._schedule_selection_changed()

    def _on_min_spin_changed(self, value: float) -> None:
        high = self._high
        if high is not None and value > high:
            high = value
        self._set_range(value, high)
        self._schedule_selection_changed()

    def _on_max_spin_changed(self, value: float) -> None:
        low = self._low
        if low is not None and value < low:
            low = value
        self._set_range(low, value)
        self._schedule_selection_changed()

    # === Classes ===

    def _fill_classes(self, classes: Iterable[Tuple[float, str, str]]) -> None:
        with _signals_blocked(self._classes_list):
            self._classes_list.clear()
            for value, label, color in classes or ():
                item = QListWidgetItem(f"{format_class_value(value)} — {label}")
                pixmap = QPixmap(12, 12)
                pixmap.fill(QColor(color))
                item.setIcon(QIcon(pixmap))
                item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                item.setCheckState(Qt.CheckState.Unchecked)
                item.setData(Qt.ItemDataRole.UserRole, int(round(float(value))))
                self._classes_list.addItem(item)
        self._classes_group.setVisible(self._has_classes())

    def _class_items(self) -> List[Any]:
        items = (self._classes_list.item(index) for index in range(self._classes_list.count()))
        return [item for item in items if item is not None]

    def _checked_classes(self) -> List[int]:
        return sorted(int(item.data(Qt.ItemDataRole.UserRole)) for item in self._class_items()
                      if item.checkState() == Qt.CheckState.Checked)

    def _set_all_classes(self, state: Any, emit: bool = True) -> None:
        with _signals_blocked(self._classes_list):
            for item in self._class_items():
                item.setCheckState(state)
        if emit:
            self._emit_now()

    # === Expression ===

    def _use_range_as_expression(self) -> None:
        formula = range_formula(self.current_band(), self._low, self._high, self._reference)
        if not formula:
            self.set_expression_status(False, self.tr("Set a value range first"))
            return
        with _signals_blocked(self._expression_edit):
            self._expression_edit.setText(formula)
        self.set_expression_status(True, "")
        self._emit_now()

    # === Pixel value ===

    def _refresh_pixel_display(self) -> None:
        if self._last_pixel is None:
            self._pixel_value_label.setText("–")
            self._pixel_coordinates_label.setText("")
            self._pixel_bands_label.setText("")
            self._pixel_history_label.setText("")
            return
        x, y, values = self._last_pixel
        nodata = self.tr("NoData")
        self._pixel_value_label.setText(format_pixel_value(values.get(self.current_band()), self._decimals, nodata))
        digits = self._coordinate_decimals
        self._pixel_coordinates_label.setText(f"X {x:.{digits}f}   Y {y:.{digits}f}")
        lines = []
        for band in sorted(values):
            info = self._band_info(band)
            decimals = decimals_for(info.data_type) if info is not None else FLOAT_DECIMALS
            name = f"{band} — {info.name}" if info is not None and info.name else str(band)
            lines.append(f"{name}: {format_pixel_value(values[band], decimals, nodata)}")
        self._pixel_bands_label.setText("\n".join(lines))
        history = []
        for hx, hy, value, band in self._history:
            info = self._band_info(band)
            decimals = decimals_for(info.data_type) if info is not None else FLOAT_DECIMALS
            history.append(f"{hx:.{digits}f}, {hy:.{digits}f}  →  {format_pixel_value(value, decimals, nodata)} (b{band})")
        self._pixel_history_label.setText(self.tr("Last values:") + "\n" + "\n".join(history) if history else "")
