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
from enum import Enum
from typing import TYPE_CHECKING, Any, Collection, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from qgis.PyQt.QtCore import Qt, QTimer, pyqtSignal
    from qgis.PyQt.QtGui import QColor, QFontDatabase, QIcon, QPixmap
    from qgis.PyQt.QtWidgets import (
        QComboBox, QDoubleSpinBox, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
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

from ....core.domain.raster_filter_criteria import DERIVATIVE_BOUNDS, RasterDerivative, RasterSelection, RasterSelectionMode
from ..selection_strip import percent_text
from .histogram_widget import RangeHistogramWidget, normalize_range, spin_bounds

if TYPE_CHECKING:
    from ....adapters.qgis.coverage_layers.raster_adapter import RasterSummary

Bound = Optional[float]

INTEGER_DATA_TYPES = frozenset({"Byte", "Int8", "UInt16", "Int16", "UInt32", "Int32", "Int64", "UInt64"})
FLOAT_DECIMALS = 3
HISTORY_SIZE = 5
DEBOUNCE_MS = 250
SPIN_MIN_WIDTH = 64
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
    """Fraction in [0, 1] as ``"31.2 %"`` (``"0.012 %"`` for a few pixels); ``"–"`` when unknown."""
    if ratio is None:
        return "–"
    return percent_text(ratio)


def format_zone_statistics(minimum: Bound, maximum: Bound, mean: Bound, count: Optional[int],
                           decimals: int) -> str:
    """Statistics of a drawn rectangle, ``"min 198.400 · max 251.070 · mean 221.300 · 12450 px"``.

    Returns ``""`` when the zone holds no valid pixel (no minimum or maximum).
    """
    if minimum is None or maximum is None:
        return ""
    parts = [f"min {format_pixel_value(minimum, decimals)}", f"max {format_pixel_value(maximum, decimals)}"]
    if mean is not None:
        parts.append(f"mean {format_pixel_value(mean, max(decimals, 1))}")
    if count is not None and count > 0:
        parts.append(f"{int(count)} px")
    return " · ".join(parts)


def history_html(rows: Sequence[Tuple[str, str, int]], title: str) -> str:
    """Last picks as a two-column table (coordinates left, value right), ``""`` without picks.

    A band other than the first is named after the value (``198.400 · b2``).
    """
    if not rows:
        return ""
    from html import escape
    lines = [f'<tr><td colspan="2" style="color:#8a8a8a;font-size:small">{escape(title)}</td></tr>']
    for coordinates, value, band in rows:
        shown = value if band == 1 else f"{value} · b{band}"
        lines.append(f'<tr><td style="font-family:monospace">{escape(coordinates)}</td>'
                     f'<td align="right" style="font-family:monospace">{escape(shown)}</td></tr>')
    return '<table width="100%" cellspacing="0" cellpadding="1">' + "".join(lines) + "</table>"


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


# Unit shown after the bounds of a derivative.
DERIVATIVE_SUFFIXES = {
    RasterDerivative.SLOPE_DEGREES: " °",
    RasterDerivative.SLOPE_PERCENT: " %",
    RasterDerivative.ASPECT: " °",
}
DERIVATIVE_DECIMALS = 2


def format_derived_value(derivative: RasterDerivative, value: Optional[float], nodata_text: str = "NoData") -> str:
    """Value of a terrain derivative with its unit (``"12.3 °"``), ``nodata_text`` for None."""
    if value is None:
        return nodata_text
    return f"{float(value):.{DERIVATIVE_DECIMALS}f}{DERIVATIVE_SUFFIXES.get(derivative, '')}"


# Band layouts of a multiband image: band number of each colour (NIR: near infrared).
BAND_LAYOUTS = {
    "rgb": {"R": 1, "G": 2, "B": 3},
    "irc": {"NIR": 1, "R": 2, "G": 3},  # IGN infrared colour orthophoto
    "rgbn": {"R": 1, "G": 2, "B": 3, "NIR": 4},
}
# key, colours needed, raster calculator template ({R} -> "image@2"...).
SPECTRAL_PRESETS = (
    ("ndvi_vegetation", ("NIR", "R"), "({NIR} - {R}) / ({NIR} + {R}) > 0.3"),
    ("ndvi_bare", ("NIR", "R"), "({NIR} - {R}) / ({NIR} + {R}) < 0.1"),
    ("ndwi_water", ("G", "NIR"), "({G} - {NIR}) / ({G} + {NIR}) > 0.1"),
    ("exg_vegetation", ("R", "G", "B"), "(2 * {G} - {R} - {B}) / ({R} + {G} + {B}) > 0.1"),
)
DEFAULT_COLOR_TOLERANCE = 12.0  # percent of the value range, per band


class PipetteMode(Enum):
    """The PIPETTE group, exclusive like the selection modes; its selection is the result of the last picks."""

    PIPETTE = "pipette"


PIPETTE = PipetteMode.PIPETTE


def default_band_layout(band_names: Sequence[str], alpha_bands: Collection[int] = ()) -> str:
    """Layout guessed from the bands: four colour bands are red, green, blue and infrared, otherwise red, green, blue.

    An alpha band is not a colour (an RGBA image is RGB). An infrared colour image (IRC) cannot be told
    from RGB by its bands: the user picks it.
    """
    return "rgbn" if len(color_bands(band_names, alpha_bands)) >= 4 else "rgb"


def layouts_for(band_names: Sequence[str], alpha_bands: Collection[int] = ()) -> List[str]:
    """Layouts an image can have: RGB + infrared needs four colour bands (A11)."""
    return ["rgb", "irc", "rgbn"] if len(color_bands(band_names, alpha_bands)) >= 4 else ["rgb", "irc"]


def spectral_presets_for(layout: str) -> List[str]:
    """Keys of the presets whose colours exist in ``layout`` (e.g. no NDVI on a plain RGB image)."""
    colours = BAND_LAYOUTS.get(layout, {})
    return [key for key, needs, _template in SPECTRAL_PRESETS if all(c in colours for c in needs)]


def spectral_expression(key: str, layout: str, reference: str) -> str:
    """Raster calculator expression of a preset on ``layout``; ``""`` when the layout lacks a colour."""
    colours = BAND_LAYOUTS.get(layout, {})
    for name, needs, template in SPECTRAL_PRESETS:
        if name == key and all(c in colours for c in needs):
            return template.format(**{c: f'"{reference}@{colours[c]}"' for c in needs})
    return ""


def color_bands(band_names: Sequence[str], alpha_bands: Collection[int] = ()) -> List[int]:
    """Band numbers a picked colour is made of: up to four, an alpha band left out.

    Args:
        alpha_bands: Numbers of the alpha bands (RasterBandInfo.is_alpha, from the colour
            interpretation). 2026-10-17: QGIS names the bands "Band 4", a name holding
            "alpha" is only the fallback.
    """
    numbers = [number for number, name in enumerate(band_names, start=1)
               if number not in alpha_bands and "alpha" not in (name or "").lower()]
    return numbers[:4]


def tolerance_value(percent: float, span: float) -> float:
    """Tolerance in band units: ``percent`` of the value range."""
    return round(max(0.0, float(percent)) / 100.0 * float(span), 6)


def _number(value: float) -> str:
    """Number for an expression, exact enough that the clicked pixel keeps itself (no 6-digit rounding)."""
    return repr(float(value)) if float(value) != int(float(value)) else str(int(float(value)))


def color_similarity_expression(reference: str, bands: Sequence[int], samples: Sequence[Sequence[float]],
                                tolerance) -> str:
    """Expression keeping the pixels within the tolerance of a sampled colour, on every band; samples are ORed.

    ``(abs("img@1" - 12) <= 30 AND abs("img@2" - 100) <= 30 AND ...) OR (...)``

    Args:
        tolerance: One value for every band, or one per band (in ``bands`` order).
    """
    tolerances = list(tolerance) if isinstance(tolerance, (list, tuple)) else [tolerance] * len(bands)
    clauses = []
    for sample in samples:
        parts = [f'abs("{reference}@{band}" - {_number(value)}) <= {_number(tol)}'
                 for band, value, tol in zip(bands, sample, tolerances)]
        if parts:
            clauses.append("(" + " AND ".join(parts) + ")")
    return " OR ".join(clauses)


def derivative_presets(derivative: RasterDerivative) -> List[Tuple[str, Bound, Bound]]:
    """Usual thresholds of a derivative: ``(key, low, high)``, ``None`` bound = open side.

    The key names the threshold (``"flat"``, ``"east"``...): the widget translates it.
    Aspect has no north entry: it wraps around 0 and a range cannot.
    """
    if derivative is RasterDerivative.SLOPE_DEGREES:
        return [("flat", None, 5.0), ("gentle", 5.0, 15.0), ("moderate", 15.0, 30.0), ("steep", 30.0, None)]
    if derivative is RasterDerivative.SLOPE_PERCENT:
        return [("flat", None, 5.0), ("gentle", 5.0, 15.0), ("moderate", 15.0, 30.0), ("steep", 30.0, None)]
    if derivative is RasterDerivative.ASPECT:
        return [("east", 45.0, 135.0), ("south", 135.0, 225.0), ("west", 225.0, 315.0)]
    if derivative is RasterDerivative.HILLSHADE:
        return [("shadow", None, 50.0), ("lit", 150.0, None)]
    return []


def format_preset(label: str, low: Bound, high: Bound, suffix: str = "") -> str:
    """Combo text of a preset: ``"Flat (< 5 °)"``."""
    def number(value: float) -> str:
        return f"{value:g}"
    if low is None:
        span = f"< {number(high)}{suffix}"
    elif high is None:
        span = f"> {number(low)}{suffix}"
    else:
        span = f"{number(low)}–{number(high)}{suffix}"
    return f"{label} ({span})"


def _optional_float(value: Any) -> Bound:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _parse_picks(raw: Any) -> List[Any]:
    """Picks of a saved state: numbers or lists of numbers; anything else is dropped."""
    picks = []
    for pick in raw if isinstance(raw, list) else []:
        if isinstance(pick, list) and pick and all(_optional_float(v) is not None for v in pick):
            picks.append([float(v) for v in pick])
        elif _optional_float(pick) is not None:
            picks.append(float(pick) if float(pick) != int(float(pick)) else int(float(pick)))
    return picks


def parse_raster_state(state: Any) -> Dict[str, Any]:
    """Normalise a saved panel state; missing or invalid entries get their default.

    Returns:
        Dict with ``layer_id``, ``mode`` (RasterSelectionMode or PIPETTE), ``band`` (>= 1),
        ``minimum`` / ``maximum`` (ordered, None = unbounded), ``classes``
        (sorted ints), ``expression``, ``preview`` and ``derivative`` (RasterDerivative).
    """
    state = state if isinstance(state, dict) else {}
    raw_mode = state.get("mode", RasterSelectionMode.RANGE.value)
    try:
        mode = PIPETTE if raw_mode == PIPETTE.value else RasterSelectionMode(raw_mode)
    except ValueError:
        mode = RasterSelectionMode.RANGE
    try:
        band = max(1, int(state.get("band", 1)))
    except (TypeError, ValueError):
        band = 1
    try:
        derivative = RasterDerivative(state.get("derivative", RasterDerivative.VALUE.value))
    except ValueError:
        derivative = RasterDerivative.VALUE
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
        "expression": state.get("expression") if isinstance(state.get("expression"), str) else "",
        "preview": bool(state.get("preview", False)),
        "derivative": derivative,
        "layout": state.get("layout") if isinstance(state.get("layout"), str) and state.get("layout") in BAND_LAYOUTS else "",
        "pipette_selection": state.get("pipette_selection") if isinstance(state.get("pipette_selection"), dict) else None,
        "pipette_kind": state.get("pipette_kind") if state.get("pipette_kind") in ("color", "value", "classes", "preset") else "",
        "pipette_picks": _parse_picks(state.get("pipette_picks")),
    }


def build_raster_selection(state: Any) -> Optional[RasterSelection]:
    """Selection described by a panel state (see :meth:`RasterExploringPanel.state`).

    Returns:
        The RasterSelection of the active mode, None when it keeps no constraint.
    """
    parsed = parse_raster_state(state)
    mode = parsed["mode"]
    if mode is PIPETTE:
        try:
            selection = RasterSelection.from_dict(parsed["pipette_selection"] or {})
        except (ValueError, TypeError):
            return None
        return None if not parsed["pipette_selection"] or selection.is_empty else selection
    if mode is RasterSelectionMode.RANGE:
        selection = RasterSelection(band=parsed["band"], mode=mode, derivative=parsed["derivative"],
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

    The map preview has no switch here: the preview button of the EXPLORING rail
    drives it (:meth:`set_preview_checked`).
    """

    bandChanged = pyqtSignal(int)
    selectionChanged = pyqtSignal()
    summaryChanged = pyqtSignal()  # kept ratio updated: the selection strip under EXPLORING follows
    modeChosen = pyqtSignal(str)  # the user made a group the active one (its value): its rail tool follows

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
        self._preview_on = False  # the rail preview button is down
        self._derivative = RasterDerivative.VALUE
        self._layout = "rgb"
        self._pipette_selection: Optional[RasterSelection] = None  # what the PIPETTE group selects
        self._pick_kind = ""  # "color", "value", "classes" or "preset": what the picks are
        self._picks: List[Any] = []  # colours (tuples), values or class codes picked, in order
        self._band_spans: Dict[int, float] = {}  # observed value range of each band (statistics of the layer)
        self._pipette_on = False  # the pipette tool is on the map
        self._low: Bound = None
        self._high: Bound = None
        self._decimals = FLOAT_DECIMALS
        self._coordinate_decimals = 2
        self._histograms: Dict[Tuple[int, RasterDerivative], Tuple[List[int], float, float]] = {}
        self._last_pixel: Optional[Tuple[float, float, Dict[int, Optional[float]], Dict[RasterDerivative, Optional[float]]]] = None
        # (x, y, band value, band, text of the derivative picked with it or None)
        self._history: List[Tuple[float, float, Optional[float], int, Optional[str]]] = []
        self._switching_mode = False
        self._kept_ratio: Optional[float] = None
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
        # Long band names must not widen the panel past a narrow dock.
        self._band_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self._band_combo.setMinimumContentsLength(8)
        self._band_combo.currentIndexChanged.connect(self._on_band_index_changed)
        band_row.addWidget(self._band_combo)
        layout.addLayout(band_row)

        derivative_row = QHBoxLayout()
        derivative_row.addWidget(QLabel(self.tr("Compute on"), self))
        self._derivative_combo = QComboBox(self)
        self._derivative_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._derivative_combo.setToolTip(self.tr(
            "Quantity the range applies to. Slope, aspect, hillshade and roughness read the band as a DTM."))
        self._derivative_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self._derivative_combo.setMinimumContentsLength(8)
        for derivative, label in ((RasterDerivative.VALUE, self.tr("Pixel value")),
                                  (RasterDerivative.SLOPE_DEGREES, self.tr("Slope (degrees)")),
                                  (RasterDerivative.SLOPE_PERCENT, self.tr("Slope (%)")),
                                  (RasterDerivative.ASPECT, self.tr("Aspect (degrees)")),
                                  (RasterDerivative.HILLSHADE, self.tr("Hillshade (0-255)")),
                                  (RasterDerivative.ROUGHNESS, self.tr("Roughness (TRI, mean difference)"))):
            self._derivative_combo.addItem(label, derivative.value)
        self._derivative_combo.currentIndexChanged.connect(self._on_derivative_index_changed)
        derivative_row.addWidget(self._derivative_combo)
        layout.addLayout(derivative_row)

        self._pixel_group = self._build_pixel_group()
        if hasattr(self._pixel_group, 'setCollapsed'):
            self._pixel_group.setCollapsed(True)  # opened by the first picked pixel
        layout.addWidget(self._pixel_group)
        layout.addWidget(self._build_pipette_group())
        layout.addWidget(self._build_range_group())
        layout.addWidget(self._build_classes_group())
        layout.addWidget(self._build_expression_group())
        layout.addStretch()

        self._mode_groups = {
            RasterSelectionMode.RANGE: self._range_group,
            RasterSelectionMode.CLASSES: self._classes_group,
            RasterSelectionMode.EXPRESSION: self._expression_group,
            PIPETTE: self._pipette_group,
        }
        for mode, group in self._mode_groups.items():
            group.toggled.connect(lambda checked, m=mode: self._on_group_toggled(m, checked))
            if hasattr(group, "collapsedStateChanged"):
                group.collapsedStateChanged.connect(lambda collapsed, m=mode: self._on_group_collapsed(m, collapsed))
        self._classes_group.setVisible(False)

    def _build_pipette_group(self) -> Any:
        """Everything the pipette needs, in one group: tolerance, last pick, band layout, spectral presets."""
        self._pipette_group = self._make_group(self.tr("PIPETTE"), "mGroupBox_raster_pipette", checkable=True)
        group_layout = self._pipette_group.layout()
        tolerance_row = QHBoxLayout()
        tolerance_row.addWidget(QLabel(self.tr("Tolerance ±"), self._pipette_group))
        self._tolerance_spin = QDoubleSpinBox(self._pipette_group)
        self._tolerance_spin.setRange(0.0, 100.0)
        self._tolerance_spin.setDecimals(1)
        self._tolerance_spin.setSuffix(" %")
        self._tolerance_spin.setValue(DEFAULT_COLOR_TOLERANCE)
        self._tolerance_spin.setKeyboardTracking(False)
        self._tolerance_spin.setToolTip(self.tr("Tolerance around the picked color or value, in % of the value range"))
        self._tolerance_spin.setAccessibleName(self.tr("Pipette tolerance"))
        self._tolerance_spin.valueChanged.connect(self._on_tolerance_changed)
        tolerance_row.addWidget(self._tolerance_spin)
        group_layout.addLayout(tolerance_row)
        self._sample_label = QLabel("", self._pipette_group)
        self._sample_label.setWordWrap(True)
        group_layout.addWidget(self._sample_label)
        # Multiband images (orthophotos): which band is which, then the usual indexes.
        layout_row = QHBoxLayout()
        self._layout_label = QLabel(self.tr("Bands"), self._pipette_group)
        layout_row.addWidget(self._layout_label)
        self._layout_combo = QComboBox(self._pipette_group)
        self._layout_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._layout_combo.setToolTip(self.tr("What the bands of the image are: the presets and the pipette use them"))
        self._layout_combo.setAccessibleName(self.tr("Band layout"))
        for key, label in (("rgb", self.tr("RGB (red, green, blue)")), ("irc", self.tr("IRC (infrared, red, green)")),
                           ("rgbn", self.tr("RGB + infrared"))):
            self._layout_combo.addItem(label, key)
        self._layout_combo.currentIndexChanged.connect(self._on_layout_index_changed)
        layout_row.addWidget(self._layout_combo)
        group_layout.addLayout(layout_row)
        self._spectral_combo = QComboBox(self._pipette_group)
        self._spectral_combo.setToolTip(self.tr("Write the expression of a usual index (vegetation, water...)"))
        self._spectral_combo.setAccessibleName(self.tr("Spectral presets"))
        self._spectral_combo.activated.connect(self._on_spectral_preset)
        group_layout.addWidget(self._spectral_combo)
        self._fill_spectral_presets()
        return self._pipette_group

    def show_pipette_active(self, active: bool) -> None:
        """The pipette is on (or off) the map: on, its group becomes the active one."""
        self._pipette_on = bool(active)
        if active:
            self._activate_mode(PIPETTE)

    def _build_pixel_group(self) -> Any:
        group = self._make_group(self.tr("PIXEL VALUE"), "mGroupBox_raster_pixel_value", checkable=False)
        group_layout = group.layout()
        self._pixel_value_label = QLabel("–", group)
        self._pixel_value_label.setObjectName("label_raster_pixel_value")
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setPointSizeF(max(font.pointSizeF(), 9.0) + 6.0)
        font.setBold(True)
        self._pixel_value_label.setFont(font)
        self._pixel_value_label.setAccessibleName(self.tr("Pixel value of the current band"))
        self._pixel_value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        # Value and coordinates on one line, as in the mockup: big value left, X / Y right.
        value_row = QHBoxLayout()
        value_row.setContentsMargins(0, 0, 0, 0)
        value_row.addWidget(self._pixel_value_label, 0, Qt.AlignmentFlag.AlignBottom)
        value_row.addStretch(1)
        self._pixel_coordinates_label = QLabel("", group)
        self._pixel_coordinates_label.setObjectName("label_raster_pixel_coordinates")
        self._pixel_coordinates_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._pixel_coordinates_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        value_row.addWidget(self._pixel_coordinates_label, 0, Qt.AlignmentFlag.AlignBottom)
        group_layout.addLayout(value_row)
        self._pixel_bands_label = QLabel("", group)
        self._pixel_bands_label.setWordWrap(True)
        group_layout.addWidget(self._pixel_bands_label)
        self._pixel_history_label = QLabel("", group)
        self._pixel_history_label.setTextFormat(Qt.TextFormat.RichText)
        self._pixel_history_label.setWordWrap(True)
        self._pixel_history_label.setToolTip(self.tr("Last {0} values picked").format(HISTORY_SIZE))
        group_layout.addWidget(self._pixel_history_label)
        self._hover_label = QLabel("", group)
        self._hover_label.setWordWrap(True)  # a long value line must not widen the panel past the dock
        self._hover_label.setToolTip(self.tr("Value of the current band under the cursor"))
        self._hover_label.setVisible(False)
        group_layout.addWidget(self._hover_label)
        self._zone_label = QLabel("", group)
        self._zone_label.setWordWrap(True)
        self._zone_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._zone_label.setToolTip(self.tr("Statistics of the current band in the last rectangle drawn on the map"))
        self._zone_label.setVisible(False)
        group_layout.addWidget(self._zone_label)
        help_label = QLabel(self.tr("Click on the map with the pixel picker. Ctrl+click extends the range to the value."), group)
        help_label.setObjectName("label_raster_pixel_help")
        help_label.setWordWrap(True)
        help_label.setEnabled(False)  # muted caption in every theme
        group_layout.insertWidget(group_layout.indexOf(self._pixel_bands_label), help_label)
        return group

    def show_picker_active(self, active: bool) -> None:
        """The pixel picker is on the map: the pixel group opens so the next click is seen."""
        if active and not self._pipette_on and hasattr(self._pixel_group, 'setCollapsed'):
            self._pixel_group.setCollapsed(False)  # the pipette shows its result in its own group

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
            spin.setMinimumWidth(SPIN_MIN_WIDTH)  # the size hint covers ±1e9
            spins_row.addWidget(QLabel(label, self._range_group))
            spins_row.addWidget(spin)
        self._min_spin.valueChanged.connect(self._on_min_spin_changed)
        self._max_spin.valueChanged.connect(self._on_max_spin_changed)
        group_layout.addLayout(spins_row)

        self._presets_combo = QComboBox(self._range_group)
        self._presets_combo.setToolTip(self.tr("Usual thresholds of the quantity"))
        self._presets_combo.setAccessibleName(self.tr("Usual thresholds"))
        self._presets_combo.activated.connect(self._on_preset_activated)
        group_layout.addWidget(self._presets_combo)
        self._fill_presets()

        self._kept_ratio_label = QLabel("", self._range_group)
        group_layout.addWidget(self._kept_ratio_label)
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
        self._use_range_button = QPushButton(self.tr("Use the range"), self._expression_group)
        self._use_range_button.setToolTip(self.tr("Write the current value range as an expression"))
        self._use_range_button.clicked.connect(self._use_range_as_expression)
        buttons_row.addWidget(self._use_range_button)
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
            self._set_layout(default_band_layout(*self._band_names_and_alpha()))
            self._pipette_selection, self._picks, self._pick_kind = None, [], ""
            self._band_spans = {}
        self._coordinate_decimals = coordinate_decimals(min(summary.pixel_size_x, summary.pixel_size_y))

        with _signals_blocked(self._band_combo):
            self._band_combo.clear()
            for info in summary.bands:
                self._band_combo.addItem(band_label(info.number, info.name, info.data_type), int(info.number))
        self._fill_classes(summary.classes)
        self._show_spectral_rows()
        if saved is not None:
            self.restore_state(saved)
        else:
            self.reset()

    def set_histogram(self, band: int, counts: Sequence[int], minimum: float, maximum: float,
                      derivative: RasterDerivative = RasterDerivative.VALUE) -> None:
        """Store the histogram of ``band`` for ``derivative``; shown at once when it is the current one.

        Does not emit ``selectionChanged``.
        """
        self._histograms[(int(band), derivative)] = ([int(count) for count in counts or ()],
                                                     float(minimum), float(maximum))
        if int(band) == self.current_band() and derivative is self._derivative:
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
        """Whether the map preview is asked (every mode has one: an expression or a colour is veiled)."""
        return self._preview_on

    def set_preview_checked(self, checked: bool) -> None:
        """Follow the preview button of the EXPLORING rail (the only switch of the map preview). Does not emit."""
        self._preview_on = bool(checked)

    def current_derivative(self) -> RasterDerivative:
        """Quantity the selection applies to: the one of the combo in range mode, the pixel value otherwise.

        Classes and expressions read pixel values, whatever the combo says; the pipette picks in the quantity.
        """
        return self._derivative if self._mode in (RasterSelectionMode.RANGE, PIPETTE) else RasterDerivative.VALUE

    def current_band(self) -> int:
        """1-based number of the selected band (1 when no band is listed)."""
        value = self._band_combo.currentData()
        return 1 if value is None else int(value)

    def set_reference(self, name: str) -> None:
        """Name of the layer in raster calculator formulas (``"mnt"`` -> ``"mnt@1"``)."""
        self._reference = name or DEFAULT_REFERENCE

    def set_kept_ratio(self, ratio: Optional[float]) -> None:
        """Show the fraction (0-1) of pixels kept by the selection, None when unknown."""
        self._kept_ratio = ratio
        self._kept_ratio_label.setText(self.tr("Selected pixels: {0}").format(format_percent(ratio)))
        self.summaryChanged.emit()

    def kept_ratio(self) -> Optional[float]:
        """Last fraction (0-1) of kept pixels shown, None when unknown."""
        return self._kept_ratio

    def set_expression_status(self, ok: bool, message: str) -> None:
        """Show the validation result of the raster expression."""
        self._expression_status.setText(message or "")
        color = _STATUS_OK_COLOR if ok else _STATUS_ERROR_COLOR
        self._expression_status.setStyleSheet(f"color: {color};" if message else "")

    def set_pixel_values(self, x: float, y: float, values: Dict[int, Optional[float]], extend: bool = False,
                         terrain: Optional[Dict[RasterDerivative, Optional[float]]] = None) -> None:
        """Show the values picked at ``(x, y)`` (one per band, None for NoData).

        Args:
            x: Map abscissa of the click (layer CRS).
            y: Map ordinate of the click.
            values: Band number -> value.
            extend: Ctrl+click; in RANGE mode the range grows to contain the
                picked value (the one of the quantity the range applies to) and
                ``selectionChanged`` is emitted.
            terrain: Slope, aspect... of the pixel, read when the range applies to one.
        """
        values = dict(values or {})
        terrain = dict(terrain or {})
        self._last_pixel = (float(x), float(y), values, terrain)
        band = self.current_band()
        shown = None
        if self._derivative.is_terrain:
            shown = format_derived_value(self._derivative, terrain.get(self._derivative), self.tr("NoData"))
        self._history = push_history(self._history, (float(x), float(y), values.get(band), band, shown))
        self._refresh_pixel_display()
        if not self._pipette_on and hasattr(self._pixel_group, 'setCollapsed'):
            self._pixel_group.setCollapsed(False)
        value = terrain.get(self._derivative) if self._derivative.is_terrain else values.get(band)
        if extend and value is not None and self._mode is RasterSelectionMode.RANGE:
            self._set_range(*extend_range(self._low, self._high, value))
            self._emit_now()

    def set_hover_value(self, x: Optional[float], y: Optional[float], value: Optional[float] = None,
                        derived: Optional[float] = None) -> None:
        """Show the value under the cursor; ``x`` None hides the line.

        The value is the one of the current band, or ``derived`` (slope, aspect...) when the range
        applies to a terrain derivative. Unlike :meth:`set_pixel_values`, nothing is added to the history.
        """
        if x is None or y is None:
            self._hover_label.setVisible(False)
            self._hover_label.setText("")
            return
        digits = self._coordinate_decimals
        if self._derivative.is_terrain:
            text = format_derived_value(self._derivative, derived, self.tr("NoData"))
        else:
            text = format_pixel_value(value, self._decimals, self.tr("NoData"))
        self._hover_label.setText(self.tr("Under the cursor: {0}  (X {1:.{3}f}  Y {2:.{3}f})").format(text, x, y, digits))
        if self._hover_label.isHidden():
            self._hover_label.setVisible(True)
            if hasattr(self._pixel_group, 'setCollapsed'):
                self._pixel_group.setCollapsed(False)  # once per hover session: the user may fold it again

    def set_zone_statistics(self, minimum: Bound, maximum: Bound, mean: Bound = None,
                            count: Optional[int] = None) -> None:
        """Show the statistics of a drawn rectangle; ``minimum`` None says the zone holds no pixel."""
        text = format_zone_statistics(minimum, maximum, mean, count, self._range_decimals())
        self._zone_label.setText(self.tr("Zone: {0}").format(text or self.tr("no pixel")))
        self._zone_label.setVisible(True)
        if hasattr(self._pixel_group, 'setCollapsed'):
            self._pixel_group.setCollapsed(False)

    def reset(self) -> None:
        """Back to the defaults: first band, no range, no class, no expression. Does not emit."""
        self._debounce.stop()
        self.set_hover_value(None, None)
        self._zone_label.setVisible(False)
        self._zone_label.setText("")
        self._pipette_selection, self._picks, self._pick_kind = None, [], ""
        self._sample_label.setText("")
        if self._band_combo.count():
            with _signals_blocked(self._band_combo):
                self._band_combo.setCurrentIndex(0)
        self._set_derivative(RasterDerivative.VALUE)
        self._apply_band()
        self._set_range(None, None)
        self._set_all_classes(Qt.CheckState.Unchecked, emit=False)
        with _signals_blocked(self._expression_edit):
            self._expression_edit.clear()
        self._preview_on = False
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
            "preview": self._preview_on,
            "derivative": self._derivative.value,
            "layout": self._layout,
            "pipette_selection": self._pipette_selection.to_dict() if self._pipette_selection is not None else None,
            "pipette_picks": [list(pick) if isinstance(pick, tuple) else pick for pick in self._picks],
            "pipette_kind": self._pick_kind,
        }

    def restore_state(self, state: Dict[str, Any]) -> None:
        """Restore a :meth:`state`; unknown bands and classes are ignored. Does not emit."""
        self._debounce.stop()
        parsed = parse_raster_state(state)
        index = self._band_combo.findData(parsed["band"])
        if index >= 0:
            with _signals_blocked(self._band_combo):
                self._band_combo.setCurrentIndex(index)
        self._set_derivative(parsed["derivative"])
        if parsed["layout"]:
            self._set_layout(parsed["layout"])
        self._pick_kind = parsed["pipette_kind"]
        self._picks = [tuple(pick) if self._pick_kind == "color" else pick for pick in parsed["pipette_picks"]]
        try:
            data = parsed["pipette_selection"]
            self._pipette_selection = RasterSelection.from_dict(data) if data else None
        except (ValueError, TypeError):
            self._pipette_selection = None
        self._show_pipette_result()
        self._apply_band()
        self._set_range(parsed["minimum"], parsed["maximum"])
        wanted = set(parsed["classes"])
        with _signals_blocked(self._classes_list):
            for item in self._class_items():
                checked = int(item.data(Qt.ItemDataRole.UserRole)) in wanted
                item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        with _signals_blocked(self._expression_edit):
            self._expression_edit.setText(parsed["expression"])
        self._preview_on = parsed["preview"]
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
        self._update_mode_controls()
        if emit and changed:
            self._emit_now()

    def _on_group_toggled(self, mode: RasterSelectionMode, checked: bool) -> None:
        if self._switching_mode:
            return
        if checked:
            self._activate_mode(mode)
            self.modeChosen.emit(mode.value)
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
        self.modeChosen.emit(mode.value)

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
        # The pixel readouts keep the band decimals; the range follows the quantity it applies to.
        range_decimals = DERIVATIVE_DECIMALS if self._derivative.is_terrain else self._decimals
        self._histogram.set_decimals(range_decimals)
        with _signals_blocked(self._min_spin, self._max_spin):
            self._min_spin.setDecimals(range_decimals)
            self._max_spin.setDecimals(range_decimals)
        self._show_band_histogram()

    def _show_band_histogram(self) -> None:
        counts, minimum, maximum = self._histograms.get((self.current_band(), self._derivative), ([], 0.0, 0.0))
        self._histogram.set_histogram(counts, minimum, maximum)
        low, high = spin_bounds(*self._data_bounds(), self._range_decimals())
        with _signals_blocked(self._min_spin, self._max_spin):
            for spin in (self._min_spin, self._max_spin):
                spin.setRange(low, high)

    def _range_decimals(self) -> int:
        return DERIVATIVE_DECIMALS if self._derivative.is_terrain else self._decimals

    def _data_bounds(self) -> Tuple[Bound, Bound]:
        cached = self._histograms.get((self.current_band(), self._derivative))
        if cached is None:
            return None, None
        return cached[1], cached[2]

    def _forget_picks(self) -> None:
        """Picks were read on another band or quantity: they and their selection no longer apply (A3)."""
        self._picks, self._pick_kind, self._pipette_selection = [], "", None
        self._show_pipette_result()

    def _on_band_index_changed(self, _index: int) -> None:
        self._forget_picks()
        self._apply_band()
        self._set_range(None, None)
        self._refresh_pixel_display()
        self._zone_label.setVisible(False)  # its statistics were those of the previous band
        self.bandChanged.emit(self.current_band())
        self._emit_now()

    # === Derivative ===

    def _set_derivative(self, derivative: RasterDerivative) -> None:
        """Adopt ``derivative`` in the combo and everything that depends on it, without emitting."""
        self._derivative = derivative
        index = self._derivative_combo.findData(derivative.value)
        with _signals_blocked(self._derivative_combo):
            self._derivative_combo.setCurrentIndex(max(0, index))
        suffix = DERIVATIVE_SUFFIXES.get(derivative, "")
        for spin in (self._min_spin, self._max_spin):
            spin.setSuffix(suffix)
        self._fill_presets()
        self._update_mode_controls()

    def _on_derivative_index_changed(self, _index: int) -> None:
        try:
            derivative = RasterDerivative(self._derivative_combo.currentData())
        except ValueError:
            derivative = RasterDerivative.VALUE
        self._set_derivative(derivative)
        self._forget_picks()
        self._apply_band()
        self._set_range(None, None)  # the old bounds were in another unit
        self._refresh_pixel_display()
        self._zone_label.setVisible(False)
        self.bandChanged.emit(self.current_band())  # the controller then sends the histogram
        self._emit_now()

    def _fill_presets(self) -> None:
        names = {"flat": self.tr("Flat"), "gentle": self.tr("Gentle"), "moderate": self.tr("Moderate"),
                 "steep": self.tr("Steep"), "east": self.tr("East"), "south": self.tr("South"),
                 "west": self.tr("West"), "shadow": self.tr("Shadow"), "lit": self.tr("Lit")}
        suffix = DERIVATIVE_SUFFIXES.get(self._derivative, "")
        presets = derivative_presets(self._derivative)
        with _signals_blocked(self._presets_combo):
            self._presets_combo.clear()
            self._presets_combo.addItem(self.tr("Usual thresholds…"), None)
            for key, low, high in presets:
                self._presets_combo.addItem(format_preset(names[key], low, high, suffix), (low, high))
        self._presets_combo.setVisible(bool(presets))

    def _on_preset_activated(self, index: int) -> None:
        bounds = self._presets_combo.itemData(index)
        if bounds is None:
            return
        self._set_range(*bounds)
        self._presets_combo.setCurrentIndex(0)
        self._activate_mode(RasterSelectionMode.RANGE, emit=False)  # a usual threshold is a range selection
        self._emit_now()

    def _update_mode_controls(self) -> None:
        """Enable what makes sense for the quantity: a derivative has no raster calculator expression."""
        terrain = self._derivative.is_terrain
        self._use_range_button.setEnabled(not terrain)
        self._derivative_combo.setEnabled(self._mode in (RasterSelectionMode.RANGE, PIPETTE))

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

    # === Spectral presets and colour pipette (multiband images) ===

    def _band_names_and_alpha(self) -> Tuple[List[str], set]:
        """Band names of the layer and the numbers of its alpha bands (colour interpretation)."""
        bands = self._summary.bands if self._summary is not None else []
        return [info.name for info in bands], {info.number for info in bands if getattr(info, "is_alpha", False)}

    def _set_layout(self, layout: str) -> None:
        allowed = layouts_for(*self._band_names_and_alpha())
        model = self._layout_combo.model()
        for index in range(self._layout_combo.count()):
            model.item(index).setEnabled(self._layout_combo.itemData(index) in allowed)
        self._layout = layout if layout in allowed else "rgb"
        with _signals_blocked(self._layout_combo):
            self._layout_combo.setCurrentIndex(max(0, self._layout_combo.findData(self._layout)))
        self._fill_spectral_presets()

    def _on_layout_index_changed(self, _index: int) -> None:
        self._set_layout(self._layout_combo.currentData())
        # Picked colours are band values: they stay. A preset read other bands: it is dropped.
        if self._pick_kind == "preset":
            self._forget_picks()

    def _show_spectral_rows(self) -> None:
        """Bands layout and spectral presets only make sense for an image of three bands or more: greyed out otherwise.

        (A collapsible group hides and shows its children as it folds: they are disabled, not hidden.)
        """
        usable = len(color_bands(*self._band_names_and_alpha())) >= 3
        tip = "" if usable else self.tr("Needs an image of three bands or more (red, green, blue...)")
        for widget in (self._layout_label, self._layout_combo, self._spectral_combo):
            widget.setEnabled(usable)
        self._layout_combo.setToolTip(tip or self.tr("What the bands of the image are: the presets and the pipette use them"))
        self._spectral_combo.setToolTip(tip or self.tr("Write the expression of a usual index (vegetation, water...)"))

    def _fill_spectral_presets(self) -> None:
        names = {"ndvi_vegetation": self.tr("Vegetation (NDVI > 0.3)"), "ndvi_bare": self.tr("No vegetation (NDVI < 0.1)"),
                 "ndwi_water": self.tr("Water (NDWI > 0.1)"), "exg_vegetation": self.tr("Vegetation (excess green)")}
        with _signals_blocked(self._spectral_combo):
            self._spectral_combo.clear()
            self._spectral_combo.addItem(self.tr("Spectral presets…"), None)
            for key in spectral_presets_for(self._layout):
                self._spectral_combo.addItem(names[key], key)

    def _on_spectral_preset(self, index: int) -> None:
        key = self._spectral_combo.itemData(index)
        name = self._spectral_combo.itemText(index)
        self._spectral_combo.setCurrentIndex(0)
        if key is None:
            return
        self._picks, self._pick_kind, self._preset_name = [], "preset", name
        self._set_pipette_selection(RasterSelection(band=self.current_band(), mode=RasterSelectionMode.EXPRESSION,
                                                    expression=spectral_expression(key, self._layout, self._reference)))

    def set_band_spans(self, spans: Dict[int, float]) -> None:
        """Observed value range of each band (``max - min``), the base of the pipette tolerance."""
        self._band_spans = {int(band): float(span) for band, span in (spans or {}).items() if span and span > 0}

    def _value_span(self, band: int = 0) -> float:
        """Value range of ``band`` (the current one by default): its statistics, its histogram, else its type."""
        band = band or self.current_band()
        if band in self._band_spans:
            return self._band_spans[band]
        cached = self._histograms.get((band, RasterDerivative.VALUE))
        if cached and cached[2] > cached[1]:
            return float(cached[2] - cached[1])
        info = self._band_info(band)
        kind = info.data_type if info is not None else "Byte"
        return 65535.0 if kind in ("UInt16", "Int16") else 255.0

    def _color_band_numbers(self) -> List[int]:
        return color_bands(*self._band_names_and_alpha())

    def set_color_sample(self, values: Dict[int, Optional[float]], extend: bool = False,
                         terrain: Optional[Dict[RasterDerivative, Optional[float]]] = None) -> None:
        """A pixel was clicked with the pipette: the PIPETTE group selects the pixels that look like it.

        An image of several bands selects a similar color (an expression); a classified raster selects
        the class; a single band (DTM, index) or a slope / aspect... selects a range around the value.

        Args:
            values: Band number -> value of the clicked pixel (None for NoData).
            extend: Ctrl+click; the color, class or value is added to the ones already picked.
            terrain: Slope, aspect... of the pixel, read when the pipette picks one.
        """
        bands = self._color_band_numbers()
        band = self.current_band()
        if len(bands) >= 2 and not self._derivative.is_terrain:
            kind, pick = "color", tuple(values.get(number) for number in bands)
            missing = any(value is None for value in pick)
        elif self._has_classes() and not self._derivative.is_terrain:
            value = values.get(band)
            kind, pick, missing = "classes", (None if value is None else int(round(value))), value is None
        else:
            value = (terrain or {}).get(self._derivative) if self._derivative.is_terrain else values.get(band)
            kind, pick, missing = "value", value, value is None
        flat = pick if isinstance(pick, tuple) else (pick,)
        missing = missing or any(value is None or not math.isfinite(value) for value in flat)
        if missing:
            self._sample_label.setText(self.tr("This pixel has no value (NoData): pick another one"))
            return
        if not extend or kind != self._pick_kind:
            self._picks = []
        self._pick_kind = kind
        if pick not in self._picks:
            self._picks.append(pick)
        self._apply_picks()

    def _apply_picks(self, debounced: bool = False) -> None:
        """Selection of the picks: a colour expression, the classes, or a range around the values.

        Args:
            debounced: Signal the change after the input settles (the tolerance spin box), not at once.
        """
        band = self.current_band()
        if self._pick_kind == "color":
            bands = self._color_band_numbers()
            tolerances = [tolerance_value(self._tolerance_spin.value(), self._value_span(number)) for number in bands]
            expression = color_similarity_expression(self._reference, bands, self._picks, tolerances)
            selection = RasterSelection(band=band, mode=RasterSelectionMode.EXPRESSION, expression=expression)
        elif self._pick_kind == "classes":
            selection = RasterSelection(band=band, mode=RasterSelectionMode.CLASSES, classes=frozenset(self._picks))
        else:
            low_bound, high_bound = self._data_bounds()
            known = low_bound is not None and high_bound is not None and high_bound > low_bound
            if known:
                span = high_bound - low_bound
            elif self._derivative.is_terrain:
                span = DERIVATIVE_BOUNDS.get(self._derivative, (0.0, 100.0))[1]  # no histogram yet: the natural range
            else:
                span = self._value_span(band)
            tolerance = tolerance_value(self._tolerance_spin.value(), span)
            low, high = normalize_range(min(self._picks) - tolerance, max(self._picks) + tolerance, low_bound, high_bound)
            selection = RasterSelection(band=band, mode=RasterSelectionMode.RANGE, derivative=self._derivative,
                                        minimum=low, maximum=high)
        self._set_pipette_selection(selection, debounced)

    def _set_pipette_selection(self, selection: Optional[RasterSelection], debounced: bool = False) -> None:
        self._pipette_selection = None if selection is None or selection.is_empty else selection
        self._show_pipette_result()
        if self._pipette_selection is None and self._picks:
            # A range over every value is no constraint (A7): say why nothing is selected.
            self._sample_label.setText(self.tr("The tolerance covers every value: lower it"))
        self._activate_mode(PIPETTE, emit=False)
        if debounced:
            self._schedule_selection_changed()
        else:
            self._emit_now()

    def _show_pipette_result(self) -> None:
        """One line under the tolerance: what the pipette selects (its expression as tooltip)."""
        selection = self._pipette_selection
        if selection is None:
            self._sample_label.setText("")
            self._sample_label.setToolTip("")
            return
        if selection.mode is RasterSelectionMode.RANGE:
            decimals = self._range_decimals()
            suffix = DERIVATIVE_SUFFIXES.get(selection.derivative, "")
            low = "−∞" if selection.minimum is None else f"{selection.minimum:.{decimals}f}"
            high = "+∞" if selection.maximum is None else f"{selection.maximum:.{decimals}f}"
            text = self.tr("Range {0} → {1}{2}").format(low, high, suffix)
        elif selection.mode is RasterSelectionMode.CLASSES:
            text = self.tr("Class(es) {0}").format(", ".join(str(code) for code in sorted(selection.classes)))
        elif self._pick_kind == "color":
            last = ", ".join(f"{value:g}" for value in self._picks[-1]) if self._picks else ""
            text = self.tr("{0} color(s), last: {1}").format(len(self._picks), last)
        elif self._pick_kind == "preset":
            text = getattr(self, "_preset_name", "")
        else:
            text = self.tr("Expression")
        self._sample_label.setText(text)
        self._sample_label.setToolTip(selection.describe())

    def _on_tolerance_changed(self, _value: float) -> None:
        # The selection follows at once, its signal once the wheel stops: each one may read the raster.
        if self._picks and self._pick_kind in ("color", "value"):
            self._apply_picks(debounced=True)

    # === Pixel value ===

    def _refresh_pixel_display(self) -> None:
        if self._last_pixel is None:
            self._pixel_value_label.setText("–")
            self._pixel_coordinates_label.setText("")
            self._pixel_bands_label.setText("")
            self._pixel_history_label.setText("")
            return
        x, y, values, terrain = self._last_pixel
        nodata = self.tr("NoData")
        if self._derivative.is_terrain:
            # Picked while the range applied to the pixel value: no derivative read for this pixel.
            self._pixel_value_label.setText(format_derived_value(self._derivative, terrain.get(self._derivative), nodata)
                                            if terrain else "–")
        else:
            self._pixel_value_label.setText(format_pixel_value(values.get(self.current_band()), self._decimals, nodata))
        digits = self._coordinate_decimals
        self._pixel_coordinates_label.setText(f"X {x:.{digits}f} · Y {y:.{digits}f}")
        lines = []
        for band in sorted(values):
            info = self._band_info(band)
            decimals = decimals_for(info.data_type) if info is not None else FLOAT_DECIMALS
            name = f"{band} — {info.name}" if info is not None and info.name else str(band)
            lines.append(f"{name}: {format_pixel_value(values[band], decimals, nodata)}")
        for derivative, value in terrain.items():
            name = self._derivative_combo.itemText(max(0, self._derivative_combo.findData(derivative.value)))
            lines.append(f"{name}: {format_derived_value(derivative, value, nodata)}")
        self._pixel_bands_label.setText("\n".join(lines))
        rows = []
        for hx, hy, value, band, shown in self._history:
            info = self._band_info(band)
            decimals = decimals_for(info.data_type) if info is not None else FLOAT_DECIMALS
            rows.append((f"{hx:.{digits}f} · {hy:.{digits}f}", shown or format_pixel_value(value, decimals, nodata), band))
        self._pixel_history_label.setText(history_html(rows, self.tr("LAST PICKS")))
