# -*- coding: utf-8 -*-
"""
Raster EXPLORING Panel.

Shown in place of the vector exploring groups when the current layer is a
raster. The panel is organised as the FilterMate 5 audit of 2026-10-18 asks:

* **BANDS** (not checkable, on top): one row per band with the active band
  (radio), whether the pipette compares the band (check box), its colour role
  (red, green, blue, near infrared), its name and type, and its value at the
  last click of the pixel picker. The roles are read from the renderer when it
  is a multiband colour one, guessed otherwise (and said so) until the user
  picks them or a shortcut (RGB, IRC, RGB + NIR).
  A map display control shows the active band in grey or up to three checked
  bands as a colour composite, while retaining the original layer style.
* **PIPETTE** (checkable): the settings of the two map tools of the rail, the
  pipette (similar pixels on the whole raster) and the object detector (the
  patch under the click): the target, the tolerance and the picks as chips.
* **VALUE RANGE** (checkable): the quantity the range applies to (pixel value,
  slope, aspect...), the histogram, the bounds and the usual thresholds.
* **RASTER EXPRESSION** (checkable): a three line expression, an "Insert"
  menu (band references, spectral indexes allowed by the roles, the current
  range); checking it starts from the expression of the group that was active.

The three checkable groups are exclusive like the vector ones. The resulting
:class:`RasterSelection` becomes the source geometry of FILTERING. A paletted
raster has no CLASSES group any more: a class value is a value like another,
the pipette picks it (its palette label names the chip).

The panel never reads the layer: the controller feeds it a ``RasterSummary``,
histograms and picked pixel values, and listens to its signals. The state
handling (selection building, value formatting, range extension, roles) is
done by pure functions of this module, testable without Qt. The share of
kept pixels and the detected objects go to the selection strip under
EXPLORING (``summaryChanged``): the panel shows no figure of its own.
"""
import math
from contextlib import contextmanager
from enum import Enum
from typing import TYPE_CHECKING, Any, Collection, Dict, List, Optional, Sequence, Tuple

try:
    from qgis.PyQt.QtCore import Qt, QTimer, pyqtSignal
    from qgis.PyQt.QtGui import QColor, QFont, QFontDatabase, QIcon, QPixmap
    from qgis.PyQt.QtWidgets import (
        QButtonGroup, QCheckBox, QComboBox, QDoubleSpinBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
        QMenu, QPlainTextEdit, QPushButton, QRadioButton, QSizePolicy, QToolButton, QVBoxLayout, QWidget,
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
from .histogram_widget import RangeHistogramWidget, histogram_quantile, normalize_range, spin_bounds

try:
    from ...styles.mockup_design import SPACING as _SPACING
    GAP = int(_SPACING['fm_gap'])
except Exception:  # the design module is not importable (tests without the ui package)
    GAP = 6

if TYPE_CHECKING:
    from ....adapters.qgis.coverage_layers.raster_adapter import RasterSummary

Bound = Optional[float]

INTEGER_DATA_TYPES = frozenset({"Byte", "Int8", "UInt16", "Int16", "UInt32", "Int32", "Int64", "UInt64"})
FLOAT_DECIMALS = 3
HISTORY_SIZE = 5
DEBOUNCE_MS = 250
SPIN_MIN_WIDTH = 64
EXPRESSION_LINES = 3
DEFAULT_REFERENCE = "raster"
DISPLAY_MODES = ("original", "active", "selected")
_STATUS_OK_COLOR = "#2e7d32"
_STATUS_ERROR_COLOR = "#c62828"


# ---------------------------------------------------------------------------
# Pure helpers (no Qt)
# ---------------------------------------------------------------------------

def decimals_for(data_type: str) -> int:
    """Decimals shown for a band: 0 for integer data types, 3 otherwise."""
    return 0 if data_type in INTEGER_DATA_TYPES else FLOAT_DECIMALS


def band_label(number: int, name: str, data_type: str) -> str:
    """Band entry, such as ``"1 — elevation (Float32)"``."""
    name = (name or "").strip()
    if name:
        return f"{number} — {name} ({data_type})"
    return f"{number} ({data_type})"


def short_band_name(number: int, name: str) -> str:
    """Band name without the ``"Band n"`` QGIS prefix: ``"Band 1: idw"`` -> ``"idw"``, ``"Band 2"`` -> ``""``."""
    text = (name or "").strip()
    prefix = f"band {int(number)}"
    if text.lower().startswith(prefix):
        text = text[len(prefix):].lstrip(" :-—–")
    return text


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


ALL_BANDS = 0  # active band value of the "every band" mode


def all_bands_range_expression(bands: Sequence[int], low: Bound, high: Bound, reference: str) -> str:
    """Raster calculator expression keeping the pixels whose every band of ``bands`` is in ``[low, high]``.

    ``("o@1" >= 10 AND "o@1" <= 50) AND ("o@2" >= 10 AND "o@2" <= 50)``; ``""`` without a bound or a band.
    """
    parts = [range_formula(int(band), low, high, reference) for band in bands]
    parts = [part for part in parts if part]
    return " AND ".join(parts)


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


# Colour roles of the bands of an image. NIR: near infrared.
ROLE_RED, ROLE_GREEN, ROLE_BLUE, ROLE_NIR, ROLE_NONE = "R", "G", "B", "NIR", ""
ROLES = (ROLE_RED, ROLE_GREEN, ROLE_BLUE, ROLE_NIR)
# Band layouts of a multiband image: band number of each colour, in the order of the colour bands.
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
# What a pipette click selects: the pixels like it on the whole raster, or the object it falls in.
PICK_SIMILAR = "similar"
PICK_OBJECT = "object"
PICK_SIMILAR_OBJECTS = "similar_objects"  # every object of the raster like the clicked one (colour and size)
PICK_TARGETS = (PICK_SIMILAR, PICK_OBJECT, PICK_SIMILAR_OBJECTS)
DEFAULT_SIMILAR_RATIO = (0.5, 2.0)  # area of a similar object: half to twice the clicked one
CUSTOM_QUANTITY = "custom_expression"
# Words of a band name that say it is the near infrared one.
_NIR_WORDS = ("nir", "infra", "pir", "near-ir", "near ir")


class PipetteMode(Enum):
    """The PIPETTE group, exclusive like the selection modes; its selection is the result of the last picks."""

    PIPETTE = "pipette"


PIPETTE = PipetteMode.PIPETTE


def color_bands(band_names: Sequence[str], alpha_bands: Collection[int] = ()) -> List[int]:
    """Band numbers a picked colour is made of by default: up to four, an alpha band left out.

    Args:
        alpha_bands: Numbers of the alpha bands (RasterBandInfo.is_alpha, from the colour
            interpretation). 2026-10-17: QGIS names the bands "Band 4", a name holding
            "alpha" is only the fallback.
    """
    numbers = [number for number, name in enumerate(band_names, start=1)
               if number not in alpha_bands and "alpha" not in (name or "").lower()]
    return numbers[:4]


def default_band_layout(band_names: Sequence[str], alpha_bands: Collection[int] = ()) -> str:
    """Layout guessed from the bands: four colour bands are red, green, blue and infrared, otherwise red, green, blue.

    An alpha band is not a colour (an RGBA image is RGB). An infrared colour image (IRC) cannot be told
    from RGB by its bands: the user picks it.
    """
    return "rgbn" if len(color_bands(band_names, alpha_bands)) >= 4 else "rgb"


def layouts_for(band_names: Sequence[str], alpha_bands: Collection[int] = ()) -> List[str]:
    """Layouts an image can have: RGB + infrared needs four colour bands (A11)."""
    return ["rgb", "irc", "rgbn"] if len(color_bands(band_names, alpha_bands)) >= 4 else ["rgb", "irc"]


def roles_from_layout(layout: str, bands: Sequence[int]) -> Dict[int, str]:
    """Role of each band for a layout applied to ``bands`` (the colour bands, in order): ``{1: "NIR", 2: "R"...}``."""
    colours = BAND_LAYOUTS.get(layout, {})
    bands = [int(band) for band in bands]
    roles = {}
    for role, position in colours.items():
        if 0 < position <= len(bands):
            roles[bands[position - 1]] = role
    return roles


def layout_from_roles(roles: Dict[int, str]) -> str:
    """Layout key whose roles are exactly ``roles`` on consecutive colour bands; ``""`` for any other arrangement."""
    if not roles:
        return ""
    bands = sorted(int(band) for band, role in roles.items() if role)
    for key in ("rgb", "irc", "rgbn"):
        if roles_from_layout(key, bands) == {int(b): r for b, r in roles.items() if r}:
            return key
    return ""


def default_roles(band_names: Sequence[str], alpha_bands: Collection[int] = (),
                  renderer_bands: Optional[Dict[str, int]] = None) -> Tuple[Dict[int, str], bool]:
    """Colour role of each band and whether it was guessed.

    The multiband colour renderer of the layer says which band it draws in red, green and
    blue (``renderer_bands``, ``{"R": 1, "G": 2, "B": 3}``): those roles are known; the one
    colour band it does not draw, on a four band image, is the near infrared. Without such a
    renderer, a band whose name says infrared takes NIR and the others follow the usual
    layout; that guess is reported so the panel can say "guessed" until the user confirms.
    An image of fewer than three colour bands has no roles.
    """
    colours = color_bands(band_names, alpha_bands)
    if len(colours) < 3:
        return {}, False
    renderer_bands = {role: int(band) for role, band in (renderer_bands or {}).items()
                      if role in (ROLE_RED, ROLE_GREEN, ROLE_BLUE) and int(band) in colours}
    if len(renderer_bands) == 3:
        roles = {band: role for role, band in renderer_bands.items()}
        left = [band for band in colours if band not in roles]
        if len(left) == 1:
            roles[left[0]] = ROLE_NIR
        return roles, False
    named_nir = [number for number in colours
                 if any(word in (band_names[number - 1] or "").lower() for word in _NIR_WORDS)]
    if len(named_nir) == 1:
        others = [band for band in colours if band != named_nir[0]][:3]
        roles = {band: role for band, role in zip(others, (ROLE_RED, ROLE_GREEN, ROLE_BLUE))}
        roles[named_nir[0]] = ROLE_NIR
        return roles, True
    return roles_from_layout(default_band_layout(band_names, alpha_bands), colours), True


def _colours_of(layout_or_roles: Any) -> Dict[str, int]:
    """``{"R": band, ...}`` of a layout key or of a ``{band: role}`` dict."""
    if isinstance(layout_or_roles, dict):
        return {role: int(band) for band, role in layout_or_roles.items() if role}
    return dict(BAND_LAYOUTS.get(layout_or_roles, {}))


def spectral_presets_for(layout_or_roles: Any) -> List[str]:
    """Keys of the presets whose colours exist in a layout or in band roles (e.g. no NDVI on a plain RGB image)."""
    colours = _colours_of(layout_or_roles)
    return [key for key, needs, _template in SPECTRAL_PRESETS if all(c in colours for c in needs)]


def spectral_expression(key: str, layout_or_roles: Any, reference: str) -> str:
    """Raster calculator expression of a preset on a layout or on band roles; ``""`` when a colour is missing."""
    colours = _colours_of(layout_or_roles)
    for name, needs, template in SPECTRAL_PRESETS:
        if name == key and all(c in colours for c in needs):
            return template.format(**{c: f'"{reference}@{colours[c]}"' for c in needs})
    return ""


def spectral_quantity(key: str, layout_or_roles: Any, reference: str) -> str:
    """Numeric index of a spectral preset, before its threshold comparison."""
    expression = spectral_expression(key, layout_or_roles, reference)
    return expression.rsplit(" > ", 1)[0].rsplit(" < ", 1)[0]


def quantity_range_formula(expression: str, low: Bound, high: Bound) -> str:
    """Selection formula for thresholds on a numeric custom quantity."""
    if not expression.strip() or (low is None and high is None):
        return ""
    if low is not None and high is not None and low > high:
        low, high = high, low
    parts = []
    if low is not None:
        parts.append(f"({expression.strip()}) >= {_number(low)}")
    if high is not None:
        parts.append(f"({expression.strip()}) <= {_number(high)}")
    return "(" + " AND ".join(parts) + ")"


def tolerance_value(percent: float, span: float) -> float:
    """Tolerance in band units: ``percent`` of the value range."""
    return max(0.0, float(percent)) * max(0.0, float(span)) / 100.0


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
    """Menu text of a preset: ``"Flat (< 5 °)"``."""
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


def _parse_ratio(raw: Any) -> Tuple[float, float]:
    """``(low, high)`` area ratios of the similar objects of a saved state; the default pair for anything else."""
    if isinstance(raw, (list, tuple)) and len(raw) == 2:
        low, high = _optional_float(raw[0]), _optional_float(raw[1])
        if low is not None and high is not None and low > 0 and high > 0:
            return (min(low, high), max(low, high))
    return DEFAULT_SIMILAR_RATIO


def _parse_seeds(raw: Any) -> List[Tuple[float, float, Any]]:
    """Clicked points of a saved state, ``(x, y, pick)``: the pick (colour, value or class) read there.

    A point without a valid pick is dropped: its object would have no criterion of its own.
    """
    seeds: List[Tuple[float, float, Any]] = []
    for seed in raw if isinstance(raw, list) else []:
        if isinstance(seed, (list, tuple)) and len(seed) == 3:
            x, y = _optional_float(seed[0]), _optional_float(seed[1])
            picks = _parse_picks([seed[2]])
            if x is not None and y is not None and picks and all(s[:2] != (x, y) for s in seeds):
                pick = picks[0]
                seeds.append((x, y, tuple(pick) if isinstance(pick, list) else pick))
    return seeds


def format_area(square_metres: Optional[float]) -> str:
    """Ground area, ``"125 m²"``, ``"3.4 ha"`` or ``"2.15 km²"``; ``""`` when unknown."""
    if square_metres is None or not math.isfinite(square_metres) or square_metres < 0:
        return ""
    if square_metres < 10000:
        return f"{square_metres:.0f} m²" if square_metres >= 10 else f"{square_metres:.1f} m²"
    if square_metres < 1e6:
        return f"{square_metres / 1e4:.1f} ha"
    return f"{square_metres / 1e6:.2f} km²"


def _parse_picks(raw: Any) -> List[Any]:
    """Picks of a saved state: numbers or lists of numbers; anything else is dropped."""
    picks = []
    for pick in raw if isinstance(raw, list) else []:
        if isinstance(pick, list) and pick and all(_optional_float(v) is not None for v in pick):
            picks.append([float(v) for v in pick])
        elif _optional_float(pick) is not None:
            picks.append(float(pick) if float(pick) != int(float(pick)) else int(float(pick)))
    return picks


def _parse_roles(raw: Any) -> Dict[int, str]:
    """Band roles of a saved state: ``{band: role}`` with known roles and positive bands, each role once."""
    roles: Dict[int, str] = {}
    if not isinstance(raw, dict):
        return roles
    for band, role in raw.items():
        try:
            number = int(band)
        except (TypeError, ValueError):
            continue
        if number >= 1 and role in ROLES and role not in roles.values():
            roles[number] = role
    return roles


def _parse_bands(raw: Any) -> List[int]:
    """Band numbers of a saved state (the bands the pipette compares), positive, in order, each once."""
    bands: List[int] = []
    for value in raw if isinstance(raw, list) else []:
        number = _optional_float(value)
        if number is not None and number >= 1 and int(number) not in bands:
            bands.append(int(number))
    return bands


def display_channels(bands: Sequence[int], roles: Dict[int, str]) -> Tuple[int, ...]:
    """One grey band or three RGB channels (-1 for an unused channel).

    Three selected infrared/red/green bands form the usual false colour
    composite. Other combinations retain their RGB roles, then fill free
    channels in band order. More than three bands cannot be displayed at once.
    """
    bands = sorted(set(int(band) for band in bands if int(band) > 0))
    if not 1 <= len(bands) <= 3:
        return ()
    if len(bands) == 1:
        return tuple(bands)
    colours = {roles.get(band): band for band in bands if roles.get(band)}
    if all(role in colours for role in (ROLE_NIR, ROLE_RED, ROLE_GREEN)):
        return colours[ROLE_NIR], colours[ROLE_RED], colours[ROLE_GREEN]
    channels = [colours.get(role, -1) for role in (ROLE_RED, ROLE_GREEN, ROLE_BLUE)]
    for band in bands:
        if band not in channels:
            channels[channels.index(-1)] = band
    return tuple(channels)


def _bounded_setting(raw: Any, default: float, low: float, high: float) -> float:
    value = _optional_float(raw)
    return min(high, max(low, default if value is None else value))


def parse_raster_state(state: Any) -> Dict[str, Any]:
    """Normalise a saved panel state; missing or invalid entries get their default.

    Returns:
        Dict with ``layer_id``, ``mode`` (RasterSelectionMode or PIPETTE), ``band`` (>= 1),
        ``minimum`` / ``maximum`` (ordered, None = unbounded), ``classes``
        (sorted ints), ``expression``, ``preview``, ``derivative`` (RasterDerivative),
        ``layout`` (a saved layout key, ``""`` otherwise), ``roles`` (band -> role, from the
        saved roles or the saved layout), ``roles_chosen``, ``pipette_bands``, the pipette
        keys and ``pipette_on`` (the pipette tool was on the map when the layer was left).
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
    layout = state.get("layout") if isinstance(state.get("layout"), str) and state.get("layout") in BAND_LAYOUTS else ""
    roles = _parse_roles(state.get("roles"))
    if not roles and layout:
        bands = _parse_bands(state.get("pipette_bands")) or [1, 2, 3, 4]
        roles = roles_from_layout(layout, bands)
    return {
        "layer_id": state.get("layer_id"),
        "mode": mode,
        "band": band,
        "minimum": low,
        "maximum": high,
        "classes": sorted(classes),
        "expression": state.get("expression") if isinstance(state.get("expression"), str) else "",
        "preview": bool(state.get("preview", False)),
        "band_display": state.get("band_display") if state.get("band_display") in DISPLAY_MODES else "original",
        "derivative": derivative,
        "custom_quantity": bool(state.get("custom_quantity", False)),
        "quantity_expression": state.get("quantity_expression", "") if isinstance(state.get("quantity_expression", ""), str) else "",
        "layout": layout,
        "roles": roles,
        "roles_chosen": bool(state.get("roles_chosen", False)) or bool(layout and not state.get("roles")),
        "pipette_bands": _parse_bands(state.get("pipette_bands")),
        "pipette_selection": state.get("pipette_selection") if isinstance(state.get("pipette_selection"), dict) else None,
        "pipette_kind": state.get("pipette_kind") if state.get("pipette_kind") in ("color", "value", "classes", "preset") else "",
        "pipette_picks": _parse_picks(state.get("pipette_picks")),
        "pipette_seeds": _parse_seeds(state.get("pipette_seeds")),
        "pipette_target": state.get("pipette_target") if state.get("pipette_target") in PICK_TARGETS else PICK_SIMILAR,
        "pipette_similar": _parse_ratio(state.get("pipette_similar")),
        "pipette_shape": bool(state.get("pipette_shape", True)),  # states before the shape: on, the default
        "pipette_tolerance": _bounded_setting(state.get("pipette_tolerance"), DEFAULT_COLOR_TOLERANCE, 0.0, 100.0),
        "pipette_opening": int(_bounded_setting(state.get("pipette_opening"), 1, 0, 4)),
        "pipette_fill_holes": bool(state.get("pipette_fill_holes", True)),
        "pipette_on": bool(state.get("pipette_on", False)),
        # "Every band" mode of the range: the bounds apply to each of ``range_bands``, ANDed.
        "all_bands": bool(state.get("all_bands", False)),
        "range_bands": _parse_bands(state.get("range_bands")),
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
    if mode is RasterSelectionMode.RANGE and parsed["custom_quantity"]:
        expression = quantity_range_formula(parsed["quantity_expression"], parsed["minimum"], parsed["maximum"])
        selection = RasterSelection(band=parsed["band"], mode=RasterSelectionMode.EXPRESSION, expression=expression)
    elif mode is RasterSelectionMode.RANGE and parsed["all_bands"] and len(parsed["range_bands"]) > 1:
        expression = all_bands_range_expression(parsed["range_bands"], parsed["minimum"], parsed["maximum"],
                                                sanitize_reference(state.get("reference") or "") if isinstance(state, dict) else DEFAULT_REFERENCE)
        selection = RasterSelection(band=parsed["range_bands"][0], mode=RasterSelectionMode.EXPRESSION, expression=expression)
    elif mode is RasterSelectionMode.RANGE:
        selection = RasterSelection(band=parsed["band"], mode=mode, derivative=parsed["derivative"],
                                    minimum=parsed["minimum"], maximum=parsed["maximum"])
    elif mode is RasterSelectionMode.CLASSES:
        selection = RasterSelection(band=parsed["band"], mode=mode, classes=frozenset(parsed["classes"]))
    else:
        selection = RasterSelection(band=parsed["band"], mode=mode, expression=parsed["expression"].strip())
    return None if selection.is_empty else selection


def previous_group_formula(selection: Optional[RasterSelection], reference: str) -> str:
    """Expression EXPRESSION starts from when the user checks it: the one of the selection that was active.

    A range or classes become their raster calculator formula, a pipette colour its expression;
    a terrain derivative has no formula (``""``), nor has an empty selection.
    """
    if selection is None or selection.is_empty:
        return ""
    try:
        formula = selection.to_calc_formula(reference)
    except ValueError:
        return ""
    if selection.mode is RasterSelectionMode.EXPRESSION:
        return selection.expression.strip()
    return "" if formula in ("0", "1") else formula


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
    """EXPLORING panel of a raster layer: bands, pipette, range, expression.

    Signals:
        bandChanged(int): The user picked another active band or quantity (the controller
            then sends its histogram with :meth:`set_histogram`).
        selectionChanged(): The selection changed; debounced by 250 ms for
            the spin boxes, the histogram and the expression.
        summaryChanged(): The kept ratio or the detected objects changed: the strip follows.
        modeChosen(str): The user made a group the active one (its value): its rail tool follows.
        targetChanged(str): The user changed what the pipette selects (similar pixels or the
            clicked object) in the panel: the rail buttons follow.
        displayChanged(): The map display mode or its bands changed.

    The map preview has no switch here: the preview button of the EXPLORING rail
    drives it (:meth:`set_preview_checked`).
    """

    bandChanged = pyqtSignal(int)
    selectionChanged = pyqtSignal()
    summaryChanged = pyqtSignal()
    modeChosen = pyqtSignal(str)
    targetChanged = pyqtSignal(str)
    displayChanged = pyqtSignal()

    def __init__(self, parent=None):
        """Build the panel.

        Args:
            parent: Parent widget (the dock widget).
        """
        super().__init__(parent)
        self._summary: Optional['RasterSummary'] = None
        self._rendered_only = False
        self._stream_notice_text = ""
        self._layer_id: Optional[str] = None
        self._reference = DEFAULT_REFERENCE
        self._mode = RasterSelectionMode.RANGE
        self._preview_on = False  # the rail preview button is down
        self._derivative = RasterDerivative.VALUE
        self._custom_quantity = False
        self._active_band = 1
        self._all_bands = False  # the range applies to every colour band at once (ANDed)
        self._roles: Dict[int, str] = {}  # band -> colour role
        self._roles_guessed = False  # the roles were not read from the renderer nor chosen by the user
        self._pipette_bands: List[int] = []  # bands a picked colour is made of
        self._pipette_selection: Optional[RasterSelection] = None  # what the PIPETTE group selects
        self._pick_kind = ""  # "color", "value", "classes" or "preset": what the picks are
        self._picks: List[Any] = []  # colours (tuples), values or class codes picked, in order
        # (x, y, pick): where each pick was read (layer CRS) and what, the objects to detect
        self._seeds: List[Tuple[float, float, Any]] = []
        self._pick_target = PICK_SIMILAR  # PICK_OBJECT: a click selects the object under it only
        self._band_spans: Dict[int, float] = {}  # observed value range of each band (statistics of the layer)
        self._pipette_on = False  # the pipette tool is on the map
        self._detected: Optional[Tuple[Optional[int], Optional[float], bool]] = None  # last object detection
        self._low: Bound = None
        self._high: Bound = None
        self._decimals = FLOAT_DECIMALS
        self._coordinate_decimals = 2
        self._histograms: Dict[Tuple[int, Any], Tuple[List[int], float, float]] = {}
        self._last_pixel: Optional[Tuple[float, float, Dict[int, Optional[float]], Dict[RasterDerivative, Optional[float]]]] = None
        # (x, y, band value, band, text of the derivative picked with it or None)
        self._history: List[Tuple[float, float, Optional[float], int, Optional[str]]] = []
        self._switching_mode = False
        self._kept_ratio: Optional[float] = None
        self._band_rows: Dict[int, Dict[str, Any]] = {}  # band -> its row widgets
        self._preset_name = ""
        self.setObjectName("widget_raster_exploring_panel")
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(DEBOUNCE_MS)
        self._debounce.timeout.connect(self.selectionChanged.emit)
        self._quantity_debounce = QTimer(self)
        self._quantity_debounce.setSingleShot(True)
        self._quantity_debounce.setInterval(DEBOUNCE_MS)
        self._quantity_debounce.timeout.connect(self._on_quantity_expression_changed)
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
        self._stream_notice = QLabel("", self)
        self._stream_notice.setObjectName("label_raster_stream_notice")
        self._stream_notice.setWordWrap(True)
        self._stream_notice.hide()
        layout.addWidget(self._stream_notice)
        layout.addWidget(self._build_bands_group())
        layout.addWidget(self._build_pipette_group())
        layout.addWidget(self._build_range_group())
        layout.addWidget(self._build_expression_group())
        layout.addStretch()

        self._mode_groups = {
            PIPETTE: self._pipette_group,
            RasterSelectionMode.RANGE: self._range_group,
            RasterSelectionMode.EXPRESSION: self._expression_group,
        }
        for mode, group in self._mode_groups.items():
            group.toggled.connect(lambda checked, m=mode: self._on_group_toggled(m, checked))
            if hasattr(group, "collapsedStateChanged"):
                group.collapsedStateChanged.connect(lambda collapsed, m=mode: self._on_group_collapsed(m, collapsed))

    # --- BANDS ---

    def _build_bands_group(self) -> Any:
        group = self._make_group(self.tr("BANDS"), "mGroupBox_raster_bands", checkable=False)
        self._bands_group = group
        group_layout = group.layout()
        self._bands_holder = QWidget(group)
        self._bands_holder.setObjectName("widget_raster_bands")
        self._bands_grid = QGridLayout(self._bands_holder)
        self._bands_grid.setContentsMargins(0, 0, 0, 0)
        self._bands_grid.setHorizontalSpacing(GAP)
        self._bands_grid.setVerticalSpacing(0)
        group_layout.addWidget(self._bands_holder)
        display_row = QHBoxLayout()
        display_label = QLabel(self.tr("Map display"), group)
        display_row.addWidget(display_label)
        self._display_combo = QComboBox(group)
        self._display_combo.setObjectName("comboBox_raster_band_display")
        self._display_combo.addItem(self.tr("Layer style"), "original")
        self._display_combo.addItem(self.tr("Active band"), "active")
        self._display_combo.addItem(self.tr("Selected bands"), "selected")
        self._display_combo.setToolTip(self.tr("Display the active band in grey or the checked bands as a colour composite"))
        display_label.setBuddy(self._display_combo)
        display_row.addWidget(self._display_combo, 1)
        group_layout.addLayout(display_row)
        self._display_note = QLabel("", group)
        self._display_note.setObjectName("label_raster_band_display")
        self._display_note.setWordWrap(True)
        self._display_note.hide()
        group_layout.addWidget(self._display_note)
        self._display_combo.currentIndexChanged.connect(self._on_display_changed)
        self._active_group = QButtonGroup(self)
        self._active_group.setExclusive(True)
        # Layout shortcuts (RGB, IRC, RGB + NIR) live in the menu of every colour chip: one action per chip.
        self._shortcut_buttons: Dict[str, List[Any]] = {"rgb": [], "irc": [], "rgbn": []}

        # The last click (coordinates, slope... and the last picks) is the tooltip of the values; the
        # roles note ("guessed") is in the tooltip of the chips: the block is the band rows, nothing else.
        self._pixel_coordinates_label = QLabel("", group)  # kept for the benches: text of the last click, never shown
        self._pixel_coordinates_label.setObjectName("label_raster_pixel_coordinates")
        self._pixel_coordinates_label.setVisible(False)
        self._roles_note = QLabel("", group)
        self._roles_note.setObjectName("label_raster_roles_note")
        self._roles_note.setVisible(False)

        # Readouts of the off-rail tools (value under the cursor, statistics of a rectangle).
        self._hover_label = QLabel("", group)
        self._hover_label.setWordWrap(True)
        self._hover_label.setToolTip(self.tr("Value of the active band under the cursor"))
        self._hover_label.setVisible(False)
        group_layout.addWidget(self._hover_label)
        self._zone_label = QLabel("", group)
        self._zone_label.setWordWrap(True)
        self._zone_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._zone_label.setToolTip(self.tr("Statistics of the active band in the last rectangle drawn on the map"))
        self._zone_label.setVisible(False)
        group_layout.addWidget(self._zone_label)
        return group

    # Colour of each role chip (also the swatch of the picks).
    ROLE_COLOURS = {ROLE_RED: "#d9443a", ROLE_GREEN: "#4caf50", ROLE_BLUE: "#2f7fd8", ROLE_NIR: "#8e24aa"}
    CHIP_HEIGHT = 16
    ROW_CONTROL = 18  # height of the small controls of a band row
    # The radios, the checkboxes and the empty chips take the dock stylesheet (mockup.qss): the
    # 17 px indicator of every check box and radio, theme tokens instead of the QGIS palette (2026-10-18:
    # the inline QGIS palette styles kept the QGIS colours when the plugin theme differed from QGIS').

    def _rebuild_band_rows(self) -> None:
        """One row per band: active (radio), selected (checkbox), colour chip, name, value.

        A single band shows neither the active radio nor the selection checkbox; fewer than three
        colour bands show no chip. The chip is a menu: the role of the band, then the layouts
        that set every band at once.
        """
        for row in self._band_rows.values():
            for widget in row.values():
                if hasattr(widget, 'deleteLater'):
                    self._bands_grid.removeWidget(widget)
                    widget.setParent(None)
                    widget.deleteLater()
        for button in list(self._active_group.buttons()):
            self._active_group.removeButton(button)
        self._band_rows = {}
        self._shortcut_buttons = {"rgb": [], "irc": [], "rgbn": []}
        bands = self._summary.bands if self._summary is not None else []
        colours = len(self._colour_bands()) >= 3
        several = len(bands) > 1
        mono = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        offset = 0
        if several:
            # "Every band": the range applies to each colour band at once (the histogram shows the first one).
            every = QRadioButton(self.tr("Every band"), self._bands_holder)
            every.setObjectName("radioButton_raster_band_active_all")
            every.setToolTip(self.tr("The value range applies to every colour band at once (a pixel is kept when "
                                     "each band is in the range); the histogram shows the first one"))
            every.setFixedHeight(self.ROW_CONTROL + 2)
            every.toggled.connect(lambda checked: self._on_active_band_toggled(ALL_BANDS, checked))
            self._active_group.addButton(every, ALL_BANDS)
            self._bands_grid.addWidget(every, 0, 0, 1, 4)
            self._band_rows[ALL_BANDS] = {"radio": every}
            offset = 1
        for index, info in enumerate(bands, start=offset):
            number = int(info.number)
            radio = QRadioButton(self._bands_holder)
            radio.setObjectName(f"radioButton_raster_band_active_{number}")
            radio.setToolTip(self.tr("Active band: the one the range, the histogram and the picker read"))
            radio.toggled.connect(lambda checked, n=number: self._on_active_band_toggled(n, checked))
            radio.setFixedSize(self.ROW_CONTROL, self.ROW_CONTROL)  # a narrower cell clipped the round indicator
            radio.setVisible(several)
            self._active_group.addButton(radio, number)
            pipette = QCheckBox(self._bands_holder)
            pipette.setObjectName(f"checkBox_raster_band_selected_{number}")
            pipette.setToolTip(self.tr("Use this band for the pipette and the selected bands display"))
            pipette.setAccessibleName(self.tr("Select band {0}").format(number))
            pipette.setFixedSize(self.ROW_CONTROL, self.ROW_CONTROL)
            pipette.toggled.connect(lambda checked, n=number: self._on_pipette_band_toggled(n, checked))
            pipette.setVisible(several)
            chip = self._menu_button(self._bands_holder, "—",
                                     self.tr("Colour the band holds: the spectral indexes and the chips use it. Click to change it"),
                                     f"toolButton_raster_band_role_{number}")
            chip.setFixedHeight(self.CHIP_HEIGHT)
            chip.setVisible(colours)
            if colours:
                self._fill_chip_menu(chip, number)
            name = QLabel(self._band_text(info), self._bands_holder)
            name.setObjectName(f"label_raster_band_name_{number}")
            name.setToolTip(f"{info.name or ''} ({info.data_type})".strip())
            name.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            name.setFixedHeight(self.ROW_CONTROL + 2)
            kind = QLabel(info.data_type, self._bands_holder)
            kind.setEnabled(False)
            kind.setVisible(not several)  # the type is read at a glance on a single band, in a tooltip otherwise
            value = QLabel("–", self._bands_holder)
            value.setObjectName(f"label_raster_band_value_{number}")
            value.setFont(mono)
            value.setFixedHeight(self.ROW_CONTROL + 2)
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            value.setToolTip(self.tr("Value at the last click of the pipette"))
            widgets = {"radio": radio, "pipette": pipette, "chip": chip, "name": name, "kind": kind, "value": value}
            self._bands_grid.addWidget(radio, index, 0, Qt.AlignmentFlag.AlignHCenter)
            self._bands_grid.addWidget(pipette, index, 1, Qt.AlignmentFlag.AlignHCenter)
            self._bands_grid.addWidget(chip, index, 2, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self._bands_grid.addWidget(name, index, 3)
            self._bands_grid.addWidget(kind, index, 4)
            self._bands_grid.addWidget(value, index, 5)
            self._band_rows[number] = widgets
        self._bands_grid.setColumnStretch(3, 1)
        self._refresh_band_rows()
        self._refresh_head()

    def _fill_chip_menu(self, chip: Any, number: int) -> None:
        menu = chip.menu()
        for key in (ROLE_RED, ROLE_GREEN, ROLE_BLUE, ROLE_NIR, ROLE_NONE):
            action = menu.addAction(self._role_name(key) or self.tr("No colour"))
            colour = self.ROLE_COLOURS.get(key)
            if colour:
                pixmap = QPixmap(12, 12)
                pixmap.fill(QColor(colour))
                action.setIcon(QIcon(pixmap))
            action.triggered.connect(lambda _checked=False, n=number, k=key: self._on_role_changed(n, k))
        menu.addSeparator()
        for key, label, tip in (("rgb", self.tr("RGB"), self.tr("Bands 1, 2, 3 are red, green, blue")),
                                ("irc", self.tr("IRC"), self.tr("Bands 1, 2, 3 are infrared, red, green (IGN infrared colour orthophoto)")),
                                ("rgbn", self.tr("RGB + NIR"), self.tr("Bands 1, 2, 3, 4 are red, green, blue, near infrared"))):
            action = menu.addAction(self.tr("Every band: {0}").format(label))
            action.setToolTip(tip)
            action.setEnabled(key != "rgbn" or len(self._colour_bands()) >= 4)
            action.triggered.connect(lambda _checked=False, k=key: self._on_layout_shortcut(k))
            self._shortcut_buttons[key].append(action)

    def _style_chip(self, chip: Any, role: str) -> None:
        """A rounded colour chip with the role letters; dashed and empty without a role (mockup.qss)."""
        colour = self.ROLE_COLOURS.get(role)
        radius = self.CHIP_HEIGHT // 2
        chip.setProperty("fm_band_chip", "role" if colour else "empty")
        if colour:
            chip.setStyleSheet(
                f"QToolButton {{ background: {colour}; color: white; border: none; border-radius: {radius}px; "
                f"padding: 0 6px; font-size: 10px; font-weight: 600; min-width: 14px; }} "
                "QToolButton::menu-indicator { image: none; width: 0; }")
        else:
            chip.setStyleSheet("")
        chip.style().unpolish(chip)
        chip.style().polish(chip)
        chip.setText(self._role_short(role) if colour else "—")

    @staticmethod
    def _band_text(info: Any) -> str:
        short = short_band_name(info.number, info.name)
        return f"{info.number} — {short}" if short else str(info.number)

    def _refresh_band_rows(self) -> None:
        """Rows follow the active band, the pipette bands, the roles and the last pixel."""
        values = self._last_pixel[2] if self._last_pixel is not None else {}
        nodata = self.tr("NoData")
        for number, row in self._band_rows.items():
            if number == ALL_BANDS:
                with _signals_blocked(row["radio"]):
                    row["radio"].setChecked(self._all_bands)
                font = QFont(row["radio"].font())
                font.setBold(self._all_bands)
                row["radio"].setFont(font)
                continue
            info = self._band_info(number)
            active = number == self._active_band and not self._all_bands
            compared = number in self._pipette_bands
            with _signals_blocked(row["radio"], row["pipette"]):
                row["radio"].setChecked(active)
                row["pipette"].setChecked(compared)
                row["pipette"].setEnabled(not (info is not None and getattr(info, "is_alpha", False)))
            role = self._roles.get(number, ROLE_NONE)
            self._style_chip(row["chip"], role)
            guessed = self.tr(" Roles guessed, to confirm.") if self._roles_guessed else ""
            row["chip"].setToolTip((self._role_name(role) + ". " if role else "")
                                   + self.tr("Colour the band holds: the spectral indexes and the chips use it. Click to change it")
                                   + guessed)
            font = QFont(row["name"].font())
            font.setBold(active)
            row["name"].setFont(font)
            row["name"].setEnabled(not (info is not None and getattr(info, "is_alpha", False)))
            decimals = decimals_for(info.data_type) if info is not None else FLOAT_DECIMALS
            row["value"].setText(format_pixel_value(values.get(number), decimals, nodata) if values else "–")
            row["value"].setEnabled(bool(values))
            row["value"].setToolTip(self._pixel_coordinates_label.toolTip() or self.tr("Value at the last click of the pipette"))
        self._refresh_roles_note()
        self._refresh_display_note()

    def display_bands(self) -> Optional[Tuple[int, ...]]:
        """None for the original style, () for an invalid composite, otherwise its channels."""
        mode = self._display_combo.currentData()
        if self._rendered_only or mode == "original":
            return None
        if mode == "active":
            return (self.current_band(),)
        return display_channels(self._pipette_bands, self._roles)

    def _refresh_display_note(self) -> None:
        bands = self.display_bands()
        if bands is None:
            text = ""
        elif not bands:
            text = self.tr("Choose 1 to 3 bands for display.")
        elif len(bands) == 1:
            text = self.tr("Grey: band {0}").format(bands[0])
        else:
            text = self.tr("R: {0} · G: {1} · B: {2}").format(*(band if band > 0 else "—" for band in bands))
        self._display_note.setText(text)
        self._display_note.setVisible(bool(text))

    def _on_display_changed(self, _index: int = 0) -> None:
        self._refresh_display_note()
        self.displayChanged.emit()

    def set_display_status(self, message: str) -> None:
        """Show a sampling or rendering error next to the display control."""
        if message:
            self._display_note.setText(message)
            self._display_note.show()
        else:
            self._refresh_display_note()

    @staticmethod
    def _role_colour(role: str, info: Any) -> Optional[str]:
        if role == ROLE_RED:
            return "#d9443a"
        if role == ROLE_GREEN:
            return "#4caf50"
        if role == ROLE_BLUE:
            return "#2f7fd8"
        if role == ROLE_NIR:
            return "#8e24aa"
        if info is not None and getattr(info, "is_alpha", False):
            return None
        return "#9e9e9e"

    def _role_short(self, role: str) -> str:
        return {ROLE_RED: self.tr("R"), ROLE_GREEN: self.tr("G"), ROLE_BLUE: self.tr("B"),
                ROLE_NIR: self.tr("NIR")}.get(role, "—")

    def _role_name(self, role: str) -> str:
        return {ROLE_RED: self.tr("Red"), ROLE_GREEN: self.tr("Green"), ROLE_BLUE: self.tr("Blue"),
                ROLE_NIR: self.tr("Near infrared")}.get(role, "")

    def _refresh_roles_note(self) -> None:
        if len(self._colour_bands()) < 3:
            self._roles_note.setText("")
        else:
            self._roles_note.setText(self.tr("roles guessed, to confirm") if self._roles_guessed else "")
        self._refresh_head()

    def _refresh_head(self) -> None:
        """Nothing to lay out any more (2026-10-18): the notes are tooltips. Kept for the callers."""
        return None

    # --- PIPETTE ---

    def _build_pipette_group(self) -> Any:
        """The settings of the pipette and of the object detector: target, tolerance, picks."""
        self._pipette_group = self._make_group(self.tr("PIPETTE"), "mGroupBox_raster_pipette", checkable=True)
        group_layout = self._pipette_group.layout()
        target_row = QHBoxLayout()
        target_row.setSpacing(GAP)
        target_row.addWidget(QLabel(self.tr("Select"), self._pipette_group))
        self._target_buttons: Dict[str, Any] = {}
        self._target_group = QButtonGroup(self)
        self._target_group.setExclusive(True)
        for key, label, tip in ((PICK_SIMILAR, self.tr("Similar pixels"),
                                 self.tr("Every pixel of the raster close to the picked colour or value (the pipette of the rail)")),
                                (PICK_OBJECT, self.tr("Clicked object"),
                                 self.tr("Only the patch of such pixels the click falls in: a pool, a roof, a field "
                                         "(the object detector of the rail); Ctrl+click adds another object")),
                                (PICK_SIMILAR_OBJECTS, self.tr("Similar objects"),
                                 self.tr("Every object of the raster like the clicked one: the patches of such pixels "
                                         "whose area is within the ratios below (the similar objects tool of the rail); "
                                         "Ctrl+click adds another reference object"))):
            button = QRadioButton(label, self._pipette_group)
            button.setObjectName(f"radioButton_raster_pipette_{key}")
            button.setToolTip(tip)
            button.toggled.connect(lambda checked, k=key: self._on_target_button(k, checked))
            self._target_group.addButton(button)
            self._target_buttons[key] = button
            target_row.addWidget(button)
        target_row.addStretch(1)
        group_layout.addLayout(target_row)
        # Similar objects: how far from the clicked object's area a patch may be (shown in that target only).
        self._similar_widget = QWidget(self._pipette_group)
        self._similar_widget.setObjectName("widget_raster_similar_ratio")
        similar_row = QHBoxLayout(self._similar_widget)
        similar_row.setContentsMargins(0, 0, 0, 0)
        similar_row.setSpacing(GAP)
        similar_row.addWidget(QLabel(self.tr("Area ×"), self._similar_widget))
        self._similar_low_spin = QDoubleSpinBox(self._similar_widget)
        self._similar_high_spin = QDoubleSpinBox(self._similar_widget)
        for spin, value, tip in ((self._similar_low_spin, DEFAULT_SIMILAR_RATIO[0],
                                  self.tr("Smallest similar object, as a share of each clicked reference")),
                                 (self._similar_high_spin, DEFAULT_SIMILAR_RATIO[1],
                                  self.tr("Largest similar object, as a multiple of each clicked reference"))):
            spin.setRange(0.01, 100.0)
            spin.setDecimals(2)
            spin.setSingleStep(0.25)
            spin.setValue(value)
            spin.setKeyboardTracking(False)
            spin.setToolTip(tip)
            spin.setMinimumWidth(SPIN_MIN_WIDTH)
            spin.valueChanged.connect(self._on_similar_ratio_changed)
        similar_row.addWidget(self._similar_low_spin)
        similar_row.addWidget(QLabel(self.tr("to ×"), self._similar_widget))
        similar_row.addWidget(self._similar_high_spin)
        # Shape too: a road of the colour and area of a pool is not a pool (compactness within the same ratios).
        self._similar_shape_check = QCheckBox(self.tr("same shape"), self._similar_widget)
        self._similar_shape_check.setObjectName("checkBox_raster_similar_shape")
        self._similar_shape_check.setChecked(True)
        self._similar_shape_check.setToolTip(self.tr("Keep only the objects shaped like the clicked ones: their "
                                                     "compactness (4π × area / perimeter², 1 for a disc) within the "
                                                     "same ratios; off, a road of the area of a pool is a pool"))
        self._similar_shape_check.toggled.connect(self._on_similar_ratio_changed)
        similar_row.addWidget(self._similar_shape_check)
        similar_row.addStretch(1)
        self._similar_widget.setVisible(False)
        group_layout.addWidget(self._similar_widget)
        self._object_settings = QWidget(self._pipette_group)
        self._object_settings.setObjectName("widget_raster_object_settings")
        object_row = QHBoxLayout(self._object_settings)
        object_row.setContentsMargins(0, 0, 0, 0)
        object_row.setSpacing(GAP)
        object_row.addWidget(QLabel(self.tr("Separation"), self._object_settings))
        self._opening_combo = QComboBox(self._object_settings)
        self._opening_combo.setObjectName("comboBox_raster_object_opening")
        self._opening_combo.addItem(self.tr("Connected pixels"), 0)
        for radius in range(1, 5):
            self._opening_combo.addItem(self.tr("Bridge removal: {0} px").format(radius), radius)
        self._opening_combo.setCurrentIndex(1)
        self._opening_combo.setToolTip(self.tr("Separate objects joined by narrow bridges; higher values cut wider bridges"))
        self._opening_combo.currentIndexChanged.connect(self._on_object_settings_changed)
        object_row.addWidget(self._opening_combo, 1)
        self._fill_holes_check = QCheckBox(self.tr("Fill holes"), self._object_settings)
        self._fill_holes_check.setObjectName("checkBox_raster_object_fill_holes")
        self._fill_holes_check.setChecked(True)
        self._fill_holes_check.setToolTip(self.tr("Fill enclosed gaps in the clicked object; clear to preserve courtyards and inner rings"))
        self._fill_holes_check.toggled.connect(self._on_object_settings_changed)
        object_row.addWidget(self._fill_holes_check)
        self._object_settings.setVisible(False)
        group_layout.addWidget(self._object_settings)
        tolerance_row = QHBoxLayout()
        tolerance_row.setSpacing(GAP)
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
        self._quantity_label = QLabel("", self._pipette_group)
        self._quantity_label.setEnabled(False)
        self._quantity_label.setWordWrap(True)
        tolerance_row.addWidget(self._quantity_label, 1)
        group_layout.addLayout(tolerance_row)
        self._chips_widget = QWidget(self._pipette_group)
        self._chips_widget.setObjectName("widget_raster_pipette_picks")
        self._chips_layout = QVBoxLayout(self._chips_widget)
        self._chips_layout.setContentsMargins(0, 0, 0, 0)
        self._chips_layout.setSpacing(2)
        group_layout.addWidget(self._chips_widget)
        self._sample_label = QLabel("", self._pipette_group)
        self._sample_label.setObjectName("label_raster_pipette_status")
        self._sample_label.setWordWrap(True)
        group_layout.addWidget(self._sample_label)
        self._set_pick_target(PICK_SIMILAR)
        return self._pipette_group

    def _rebuild_chips(self) -> None:
        """One removable chip per pick: a colour swatch and its values, a class and its label, a value."""
        while self._chips_layout.count():
            item = self._chips_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        for index, pick in enumerate(self._picks):
            chip = QPushButton(self._chips_widget)
            chip.setObjectName(f"pushButton_raster_pick_{index}")
            chip.setFlat(True)
            chip.setToolTip(self.tr("Remove this pick"))
            chip.setText(f"{self._chip_text(pick)}   ✕")
            colour = self._chip_colour(pick)
            if colour is not None:
                pixmap = QPixmap(12, 12)
                pixmap.fill(QColor(colour))
                chip.setIcon(QIcon(pixmap))
            chip.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
            chip.clicked.connect(lambda _checked=False, i=index: self._remove_pick(i))
            self._chips_layout.addWidget(chip, 0, Qt.AlignmentFlag.AlignLeft)
        self._chips_widget.setVisible(bool(self._picks))

    def _chip_text(self, pick: Any) -> str:
        if self._pick_kind == "color" and isinstance(pick, tuple):
            return " · ".join(f"{value:g}" for value in pick)
        if self._pick_kind == "classes":
            label = self._class_label(pick)
            return f"{format_class_value(pick)} — {label}" if label else format_class_value(pick)
        if self._derivative.is_terrain:
            return format_derived_value(self._derivative, pick)
        return format_pixel_value(pick, self._decimals)

    def _chip_colour(self, pick: Any) -> Optional[str]:
        if self._pick_kind == "classes":
            return self._class_colour(pick)
        if self._pick_kind == "color" and isinstance(pick, tuple):
            by_role = {}
            for band, value in zip(self._pipette_bands, pick):
                role = self._roles.get(band, ROLE_NONE)
                if role in (ROLE_RED, ROLE_GREEN, ROLE_BLUE) and value is not None:
                    by_role[role] = value
            if len(by_role) == 3:
                span = max(1.0, max(self._value_span(band) for band in self._pipette_bands))
                channel = lambda role: int(round(255 * min(1.0, max(0.0, float(by_role[role]) / span))))  # noqa: E731
                return f"#{channel(ROLE_RED):02x}{channel(ROLE_GREEN):02x}{channel(ROLE_BLUE):02x}"
            return "#9e9e9e"
        return None

    def _class_label(self, code: Any) -> str:
        for value, label, _colour in (self._summary.classes if self._summary is not None else ()):
            if int(round(float(value))) == int(code):
                return label or ""
        return ""

    def _class_colour(self, code: Any) -> Optional[str]:
        for value, _label, colour in (self._summary.classes if self._summary is not None else ()):
            if int(round(float(value))) == int(code):
                return colour or None
        return None

    def _remove_pick(self, index: int) -> None:
        if not (0 <= index < len(self._picks)):
            return
        pick = self._picks.pop(index)
        self._seeds = [seed for seed in self._seeds if seed[2] != pick]  # the objects grown from it go too
        if self._picks:
            self._apply_picks()
        else:
            self._pick_kind = ""
            self._set_pipette_selection(None)

    def show_pipette_active(self, active: bool) -> None:
        """The pipette (or the detector) is on the map: on, its group becomes the active one."""
        self._pipette_on = bool(active)
        if active:
            self._activate_mode(PIPETTE)

    def show_picker_active(self, active: bool) -> None:
        """The pixel picker is on the map: the bands open so the next click is seen."""
        if active and hasattr(self._bands_group, 'setCollapsed'):
            self._bands_group.setCollapsed(False)

    # --- VALUE RANGE ---

    def _build_range_group(self) -> Any:
        self._range_group = self._make_group(self.tr("VALUE RANGE"), "mGroupBox_raster_value_range", checkable=True)
        group_layout = self._range_group.layout()
        quantity_row = QHBoxLayout()
        quantity_row.setSpacing(GAP)
        quantity_row.addWidget(QLabel(self.tr("Quantity"), self._range_group))
        self._derivative_combo = QComboBox(self._range_group)
        self._derivative_combo.setObjectName("comboBox_raster_derivative")
        self._derivative_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._derivative_combo.setToolTip(self.tr(
            "Quantity the range applies to. Slope, aspect, hillshade and roughness read the active band as a DTM."))
        self._derivative_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self._derivative_combo.setMinimumContentsLength(8)
        for derivative, label in ((RasterDerivative.VALUE, self.tr("Pixel value")),
                                  (RasterDerivative.SLOPE_DEGREES, self.tr("Slope (degrees)")),
                                  (RasterDerivative.SLOPE_PERCENT, self.tr("Slope (%)")),
                                  (RasterDerivative.ASPECT, self.tr("Aspect (degrees)")),
                                  (RasterDerivative.HILLSHADE, self.tr("Hillshade (0-255)")),
                                  (RasterDerivative.ROUGHNESS, self.tr("Roughness (TRI, mean difference)"))):
            self._derivative_combo.addItem(label, derivative.value)
        self._derivative_combo.addItem(self.tr("Custom expression"), CUSTOM_QUANTITY)
        self._derivative_combo.currentIndexChanged.connect(self._on_derivative_index_changed)
        quantity_row.addWidget(self._derivative_combo, 1)
        self._presets_button = self._menu_button(self._range_group, self.tr("Thresholds ▾"),
                                                 self.tr("Usual thresholds of the quantity"), "toolButton_raster_presets")
        quantity_row.addWidget(self._presets_button)
        group_layout.addLayout(quantity_row)

        self._quantity_edit = QPlainTextEdit(self._range_group)
        self._quantity_edit.setObjectName("plainTextEdit_raster_quantity_expression")
        self._quantity_edit.setPlaceholderText(self.tr('Numeric raster formula, e.g. ("raster@4" - "raster@1") / ("raster@4" + "raster@1")'))
        self._quantity_edit.setAccessibleName(self.tr("Custom derived value expression"))
        self._quantity_edit.setToolTip(self.tr("A numeric raster calculator expression. The histogram and thresholds use its computed values."))
        self._quantity_edit.setTabChangesFocus(True)
        self._quantity_edit.setFixedHeight(self._quantity_edit.fontMetrics().lineSpacing() * 2 + 12)
        self._quantity_edit.textChanged.connect(self._quantity_debounce.start)
        self._quantity_edit.setVisible(False)
        group_layout.addWidget(self._quantity_edit)
        self._quantity_status = QLabel("", self._range_group)
        self._quantity_status.setObjectName("label_raster_quantity_expression_status")
        self._quantity_status.setWordWrap(True)
        self._quantity_status.setVisible(False)
        group_layout.addWidget(self._quantity_status)

        self._histogram = RangeHistogramWidget(self._range_group)
        self._histogram.rangeChanged.connect(self._on_histogram_range_changed)
        group_layout.addWidget(self._histogram)
        self._histogram_status = QLabel("", self._range_group)
        self._histogram_status.setObjectName("label_raster_histogram_status")
        self._histogram_status.setWordWrap(True)
        group_layout.addWidget(self._histogram_status)

        spins_row = QHBoxLayout()
        spins_row.setSpacing(GAP)
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
        self._fill_presets()
        return self._range_group

    # --- RASTER EXPRESSION ---

    def _build_expression_group(self) -> Any:
        self._expression_group = self._make_group(self.tr("RASTER EXPRESSION"), "mGroupBox_raster_expression", checkable=True)
        group_layout = self._expression_group.layout()
        self._expression_edit = QPlainTextEdit(self._expression_group)
        self._expression_edit.setObjectName("plainTextEdit_raster_expression")
        self._expression_edit.setToolTip(self.tr("Raster calculator expression; a pixel is kept where it is not 0"))
        self._expression_edit.setAccessibleName(self.tr("Raster expression"))
        self._expression_edit.setTabChangesFocus(True)
        metrics = self._expression_edit.fontMetrics()
        self._expression_edit.setFixedHeight(metrics.lineSpacing() * EXPRESSION_LINES + 12)
        self._expression_edit.textChanged.connect(self._schedule_selection_changed)
        group_layout.addWidget(self._expression_edit)
        self._expression_histogram = RangeHistogramWidget(self._expression_group)
        self._expression_histogram.setObjectName("widget_raster_expression_histogram")
        self._expression_histogram.set_decimals(None)
        self._expression_histogram.setToolTip(self.tr("Computed expression values. Drag the handles to use this expression as a derived value with thresholds."))
        self._expression_histogram.rangeChanged.connect(self._on_expression_histogram_changed)
        group_layout.addWidget(self._expression_histogram)
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(GAP)
        self._insert_button = self._menu_button(self._expression_group, self.tr("Insert ▾"),
                                                self.tr("Insert a band reference, a usual spectral index or the current range"),
                                                "toolButton_raster_insert")
        buttons_row.addWidget(self._insert_button)
        self._as_quantity_button = QPushButton(self.tr("Use as derived value"), self._expression_group)
        self._as_quantity_button.setObjectName("pushButton_raster_expression_as_quantity")
        self._as_quantity_button.clicked.connect(self._use_expression_as_quantity)
        buttons_row.addWidget(self._as_quantity_button)
        self._expression_status = QLabel("", self._expression_group)
        self._expression_status.setObjectName("label_raster_expression_status")
        self._expression_status.setWordWrap(True)
        buttons_row.addWidget(self._expression_status, 1)
        group_layout.addLayout(buttons_row)
        self._fill_insert_menu()
        return self._expression_group

    def _fill_insert_menu(self) -> None:
        menu = self._insert_button.menu()
        menu.clear()
        bands = self._summary.bands if self._summary is not None else []
        if bands:
            menu.addSection(self.tr("Bands"))
            for info in bands:
                text = f'"{self._reference}@{info.number}"'
                short = short_band_name(info.number, info.name)
                action = menu.addAction(f"{text}  {short}".rstrip())
                action.triggered.connect(lambda _checked=False, t=text: self._insert_text(t))
        keys = spectral_presets_for(self._roles)
        if keys:
            menu.addSection(self.tr("Spectral indexes"))
            names = self._spectral_names()
            for key in keys:
                action = menu.addAction(names[key])
                action.triggered.connect(lambda _checked=False, k=key: self._insert_spectral(k))
        menu.addSection(self.tr("Range"))
        action = menu.addAction(self.tr("The current value range"))
        action.triggered.connect(self._use_range_as_expression)
        action.setEnabled(not self._derivative.is_terrain)

    def _spectral_names(self) -> Dict[str, str]:
        return {"ndvi_vegetation": self.tr("Vegetation (NDVI > 0.3)"), "ndvi_bare": self.tr("No vegetation (NDVI < 0.1)"),
                "ndwi_water": self.tr("Water (NDWI > 0.1)"), "exg_vegetation": self.tr("Vegetation (excess green)")}

    def _insert_text(self, text: str) -> None:
        self._activate_mode(RasterSelectionMode.EXPRESSION, emit=False)
        self._expression_edit.insertPlainText(text)
        self._expression_edit.setFocus()

    def _insert_spectral(self, key: str) -> None:
        expression = spectral_expression(key, self._roles, self._reference)
        if not expression:
            return
        self._activate_mode(RasterSelectionMode.EXPRESSION, emit=False)
        with _signals_blocked(self._expression_edit):
            self._expression_edit.setPlainText(expression)
        self.set_expression_status(True, "")
        self._emit_now()

    def _use_range_as_expression(self) -> None:
        if self._custom_quantity:
            formula = quantity_range_formula(self._quantity_edit.toPlainText(), self._low, self._high)
        elif self._all_bands:
            formula = all_bands_range_expression(self._range_bands(), self._low, self._high, self._reference)
        else:
            formula = range_formula(self.current_band(), self._low, self._high, self._reference)
        self._activate_mode(RasterSelectionMode.EXPRESSION, emit=False)
        if not formula:
            self.set_expression_status(False, self.tr("Set a value range first"))
            return
        with _signals_blocked(self._expression_edit):
            self._expression_edit.setPlainText(formula)
        self.set_expression_status(True, "")
        self._emit_now()

    def _use_expression_as_quantity(self, _checked=False) -> None:
        expression = self._expression_edit.toPlainText().strip()
        if expression:
            self._use_quantity(expression)

    def _use_quantity(self, expression: str) -> None:
        """Use a numeric expression for the range and request its histogram."""
        self._quantity_debounce.stop()
        self._all_bands = False
        self._custom_quantity = True
        with _signals_blocked(self._quantity_edit):
            self._quantity_edit.setPlainText(expression)
        self._set_derivative(RasterDerivative.VALUE)
        self._forget_picks()
        self._activate_mode(RasterSelectionMode.RANGE, emit=False)
        self._apply_band()
        self._set_range(None, None)
        self.bandChanged.emit(self.current_band())
        self.modeChosen.emit(RasterSelectionMode.RANGE.value)
        self._emit_now()

    def _on_quantity_expression_changed(self) -> None:
        if not self._custom_quantity:
            return
        self._forget_picks()
        self._set_range(None, None)
        self._show_band_histogram()
        self.bandChanged.emit(self.current_band())
        self._emit_now()

    def _on_expression_histogram_changed(self, _low: float, _high: float) -> None:
        bounds = self._expression_histogram.range()
        self._use_expression_as_quantity()
        self._set_range(*bounds)
        self._emit_now()

    # === Public API ===

    def set_summary(self, summary: 'RasterSummary') -> None:
        """Fill the bands from a ``RasterSummary``.

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
            self._pipette_selection, self._picks, self._pick_kind, self._seeds = None, [], "", []
            self._band_spans = {}
            self._detected = None
            self._last_pixel = None
            self._history = []
        self._coordinate_decimals = coordinate_decimals(min(summary.pixel_size_x, summary.pixel_size_y))
        self._default_bands()
        self._rebuild_band_rows()
        self._fill_insert_menu()
        if saved is not None:
            self.restore_state(saved)
        else:
            self.reset()

    def set_stream_notice(self, text: str) -> None:
        """Show a translated sampling notice supplied by the controller."""
        self._stream_notice_text = text or ""
        self._refresh_stream_notice()

    def _refresh_stream_notice(self) -> None:
        text = (self.tr("Rendered colors depend on style and scale.") + " " + self.tr(
            "Only color selection is available: numeric bands, indices, ranges, classes and derivatives are unavailable.")
            if self._rendered_only else "")
        text = " ".join(part for part in (text, self._stream_notice_text) if part)
        self._stream_notice.setText(text)
        self._stream_notice.setVisible(bool(text))

    def set_rendered_only(self, enabled: bool) -> None:
        """Restrict rendered services to RGB pipette selections on a local snapshot.

        Does not emit; call after set_summary. Tolerance and Ctrl+click keep
        producing regular RasterSelection expressions for cross filtering.
        """
        enabled = bool(enabled)
        changed = self._rendered_only != enabled
        self._rendered_only = enabled
        for widget in (self._bands_group, self._range_group, self._expression_group):
            widget.setVisible(not enabled)
            widget.setEnabled(not enabled)
        if changed:
            self._pipette_selection, self._picks, self._pick_kind, self._seeds = None, [], "", []
            self._rebuild_chips()
        if enabled:
            self._quantity_debounce.stop()
            self._custom_quantity = False
            self._all_bands = False
            self._active_band = 1
            self._set_derivative(RasterDerivative.VALUE)
            self._rendered_rgb_bands()
            self._activate_mode(PIPETTE, emit=False)
        elif changed:
            self._band_spans = {}
            self._default_bands()
            self._rebuild_band_rows()
            self._activate_mode(self._default_mode(), emit=False)
        self._refresh_stream_notice()

    def _rendered_rgb_bands(self) -> None:
        self._roles = {1: ROLE_RED, 2: ROLE_GREEN, 3: ROLE_BLUE}
        self._pipette_bands = [1, 2, 3]
        self._band_spans = {1: 255.0, 2: 255.0, 3: 255.0}

    def _default_bands(self) -> None:
        """Roles from the renderer (or guessed), every colour band compared by the pipette, first band active."""
        if self._rendered_only:
            self._rendered_rgb_bands()
            return
        names, alpha = self._band_names_and_alpha()
        renderer_bands = getattr(self._summary, "renderer_bands", None) if self._summary is not None else None
        self._roles, self._roles_guessed = default_roles(names, alpha, renderer_bands)
        self._pipette_bands = color_bands(names, alpha)
        numbers = [int(info.number) for info in (self._summary.bands if self._summary is not None else [])]
        if self._active_band not in numbers:
            self._active_band = numbers[0] if numbers else 1

    def set_histogram(self, band: int, counts: Sequence[int], minimum: float, maximum: float,
                      derivative: RasterDerivative = RasterDerivative.VALUE, expression: str = "") -> None:
        """Store the histogram of ``band`` for ``derivative``; shown at once when it is the current one.

        Does not emit ``selectionChanged``.
        """
        self._histograms[(int(band), expression or derivative)] = ([int(count) for count in counts or ()],
                                                     float(minimum), float(maximum))
        if int(band) == self.current_band() and (expression or derivative) == self._histogram_quantity():
            self._show_band_histogram()
            if self._mode is not RasterSelectionMode.EXPRESSION:
                self._set_range(self._low, self._high)

    def set_histogram_pending(self) -> None:
        """Say that the current histogram is computed away from the interface thread."""
        message = self.tr("Computing histogram…")
        self._histogram_status.setText(message)
        if self._mode is RasterSelectionMode.EXPRESSION:
            self._expression_status.setText(message)
            self._expression_status.setStyleSheet("")

    def current_quantity_expression(self) -> str:
        """Numeric formula whose values the current histogram displays, or empty for a band/terrain."""
        if self._mode is RasterSelectionMode.EXPRESSION:
            return self._expression_edit.toPlainText().strip()
        return self._quantity_edit.toPlainText().strip() if self._custom_quantity else ""

    def histogram_uses_expression(self) -> bool:
        return self._mode is RasterSelectionMode.EXPRESSION or self._custom_quantity

    def clear_expression_histogram(self) -> None:
        self.set_histogram(self.current_band(), [], 0.0, 0.0, expression=CUSTOM_QUANTITY)

    def _histogram_quantity(self):
        if self.histogram_uses_expression():
            return self.current_quantity_expression() or CUSTOM_QUANTITY
        return self.current_derivative()

    def histogram_range(self) -> Optional[Tuple[Bound, Bound]]:
        """Thresholds on the numeric custom histogram, for an estimated kept share."""
        return (self._low, self._high) if self._mode is RasterSelectionMode.RANGE and self._custom_quantity else None

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

        An expression reads pixel values, whatever the combo says; the pipette picks in the quantity.
        """
        return self._derivative if self._mode in (RasterSelectionMode.RANGE, PIPETTE) else RasterDerivative.VALUE

    def current_band(self) -> int:
        """1-based number of the active band (1 when no band is listed); the first colour band in "every band" mode."""
        if self._all_bands:
            bands = self._range_bands()
            return bands[0] if bands else 1
        return int(self._active_band) if self._active_band else 1

    def all_bands(self) -> bool:
        """Whether the value range applies to every colour band at once."""
        return self._all_bands

    def _range_bands(self) -> List[int]:
        """Bands the range applies to in "every band" mode: the colour bands (no alpha), every band failing that."""
        bands = self._colour_bands()
        if not bands:
            bands = [int(info.number) for info in (self._summary.bands if self._summary is not None else [])]
        return bands

    def band_roles(self) -> Dict[int, str]:
        """Colour role of each band (``{1: "NIR", 2: "R", 3: "G"}``); empty for a single band raster."""
        return dict(self._roles)

    def pipette_bands(self) -> List[int]:
        """Bands a picked colour is made of, in band order."""
        return list(self._pipette_bands)

    def set_reference(self, name: str) -> None:
        """Name of the layer in raster calculator formulas (``"mnt"`` -> ``"mnt@1"``)."""
        self._reference = name or DEFAULT_REFERENCE
        self._fill_insert_menu()

    def set_kept_ratio(self, ratio: Optional[float]) -> None:
        """Remember the fraction (0-1) of pixels kept by the selection, None when unknown; the strip shows it."""
        self._kept_ratio = ratio
        self.summaryChanged.emit()

    def kept_ratio(self) -> Optional[float]:
        """Last fraction (0-1) of kept pixels, None when unknown."""
        return self._kept_ratio

    def set_expression_status(self, ok: bool, message: str) -> None:
        """Show the validation result of the raster expression."""
        self._expression_status.setText(message or "")
        color = _STATUS_OK_COLOR if ok else _STATUS_ERROR_COLOR
        self._expression_status.setStyleSheet(f"color: {color};" if message else "")
        self._quantity_status.setText(message or "")
        self._quantity_status.setStyleSheet(f"color: {color};" if message else "")

    def set_pixel_values(self, x: float, y: float, values: Dict[int, Optional[float]], extend: bool = False,
                         terrain: Optional[Dict[RasterDerivative, Optional[float]]] = None) -> None:
        """Show the values picked at ``(x, y)`` (one per band, None for NoData) in the band rows.

        Args:
            x: Map abscissa of the click (layer CRS).
            y: Map ordinate of the click.
            values: Band number -> value.
            extend: Ctrl+click; in RANGE mode the range grows to contain the
                picked value (the one of the quantity the range applies to) and
                ``selectionChanged`` is emitted. The pipette never asks for it
                (Ctrl+click adds a pick): kept for the automation API.
            terrain: Slope, aspect... of the pixel, read when the range applies to one.
        """
        values = dict(values or {})
        terrain = dict(terrain or {})
        self._last_pixel = (float(x), float(y), values, terrain)
        band = self.current_band()
        shown = None
        if self._custom_quantity:
            shown = format_pixel_value(terrain.get("custom"), self._range_decimals(), self.tr("NoData"))
        elif self._derivative.is_terrain:
            shown = format_derived_value(self._derivative, terrain.get(self._derivative), self.tr("NoData"))
        self._history = push_history(self._history, (float(x), float(y), values.get(band), band, shown))
        self._refresh_pixel_display()
        if hasattr(self._bands_group, 'setCollapsed'):
            self._bands_group.setCollapsed(False)
        value = terrain.get("custom") if self._custom_quantity else terrain.get(self._derivative) if self._derivative.is_terrain else values.get(band)
        if extend and value is not None and self._mode is RasterSelectionMode.RANGE:
            self._set_range(*extend_range(self._low, self._high, value))
            self._emit_now()

    def set_hover_value(self, x: Optional[float], y: Optional[float], value: Optional[float] = None,
                        derived: Optional[float] = None) -> None:
        """Show the value under the cursor; ``x`` None hides the line.

        The value is the one of the active band, or ``derived`` (slope, aspect...) when the range
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
            if hasattr(self._bands_group, 'setCollapsed'):
                self._bands_group.setCollapsed(False)  # once per hover session: the user may fold it again

    def set_zone_statistics(self, minimum: Bound, maximum: Bound, mean: Bound = None,
                            count: Optional[int] = None) -> None:
        """Show the statistics of a drawn rectangle; ``minimum`` None says the zone holds no pixel."""
        text = format_zone_statistics(minimum, maximum, mean, count, self._range_decimals())
        self._zone_label.setText(self.tr("Zone: {0}").format(text or self.tr("no pixel")))
        self._zone_label.setVisible(True)
        if hasattr(self._bands_group, 'setCollapsed'):
            self._bands_group.setCollapsed(False)

    def reset(self) -> None:
        """Back to the defaults: first band, roles from the layer, no range, no pick, no expression. Does not emit."""
        self._debounce.stop()
        self._quantity_debounce.stop()
        self._custom_quantity = False
        with _signals_blocked(self._display_combo):
            self._display_combo.setCurrentIndex(0)
        with _signals_blocked(self._quantity_edit, self._tolerance_spin, self._opening_combo, self._fill_holes_check,
                              self._similar_low_spin, self._similar_high_spin, self._similar_shape_check):
            self._quantity_edit.clear()
            self._tolerance_spin.setValue(DEFAULT_COLOR_TOLERANCE)
            self._opening_combo.setCurrentIndex(1)
            self._fill_holes_check.setChecked(True)
            self._similar_low_spin.setValue(DEFAULT_SIMILAR_RATIO[0])
            self._similar_high_spin.setValue(DEFAULT_SIMILAR_RATIO[1])
            self._similar_shape_check.setChecked(True)
        self.set_hover_value(None, None)
        self._zone_label.setVisible(False)
        self._zone_label.setText("")
        self._pipette_selection, self._picks, self._pick_kind, self._seeds = None, [], "", []
        self._detected = None
        self._sample_label.setText("")
        self._active_band = 0
        self._all_bands = False
        self._default_bands()
        self._set_pick_target(PICK_SIMILAR)
        self._set_derivative(RasterDerivative.VALUE)
        self._apply_band()
        self._set_range(None, None)
        with _signals_blocked(self._expression_edit):
            self._expression_edit.clear()
        self._preview_on = False
        self._pipette_on = False
        self.set_expression_status(True, "")
        self._kept_ratio = None
        self._last_pixel = None
        self._history = []
        self._rebuild_chips()
        self._refresh_pixel_display()
        self._fill_insert_menu()
        self._activate_mode(self._default_mode(), emit=False)
        self.summaryChanged.emit()

    def state(self) -> Dict[str, Any]:
        """Input of the panel, to keep it per layer (see :meth:`restore_state`)."""
        return {
            "layer_id": self._layer_id,
            "mode": self._mode.value,
            "band": self.current_band(),
            "minimum": self._low,
            "maximum": self._high,
            "classes": [],
            "expression": self._expression_edit.toPlainText(),
            "preview": self._preview_on,
            "band_display": self._display_combo.currentData(),
            "derivative": self._derivative.value,
            "custom_quantity": self._custom_quantity,
            "quantity_expression": self._quantity_edit.toPlainText(),
            "layout": layout_from_roles(self._roles),
            "roles": {str(band): role for band, role in self._roles.items() if role},
            "roles_chosen": not self._roles_guessed,
            "pipette_bands": list(self._pipette_bands),
            "pipette_selection": self._pipette_selection.to_dict() if self._pipette_selection is not None else None,
            "pipette_picks": [list(pick) if isinstance(pick, tuple) else pick for pick in self._picks],
            "pipette_kind": self._pick_kind,
            "pipette_seeds": [[x, y, list(pick) if isinstance(pick, tuple) else pick] for x, y, pick in self._seeds],
            "pipette_target": self._pick_target,
            "pipette_similar": list(self.similar_ratio()),
            "pipette_shape": self.similar_shape(),
            "pipette_tolerance": self._tolerance_spin.value(),
            "pipette_opening": self._opening_combo.currentData(),
            "pipette_fill_holes": self._fill_holes_check.isChecked(),
            "pipette_on": self._pipette_on,
            "all_bands": self._all_bands,
            "range_bands": self._range_bands() if self._all_bands else [],
            "reference": self._reference,
        }

    def restore_state(self, state: Dict[str, Any]) -> None:
        """Restore a :meth:`state`; unknown bands and roles are ignored. Does not emit.

        The pipette tool itself is not put back on the map: the controller reads
        ``pipette_on`` and does it explicitly (:meth:`pipette_was_on`).
        """
        self._debounce.stop()
        self._quantity_debounce.stop()
        parsed = parse_raster_state(state)
        with _signals_blocked(self._display_combo):
            self._display_combo.setCurrentIndex(self._display_combo.findData(parsed["band_display"]))
        self._custom_quantity = parsed["custom_quantity"]
        with _signals_blocked(self._quantity_edit):
            self._quantity_edit.setPlainText(parsed["quantity_expression"])
        numbers = [int(info.number) for info in (self._summary.bands if self._summary is not None else [])]
        if parsed["band"] in numbers:
            self._active_band = parsed["band"]
        self._all_bands = bool(parsed["all_bands"]) and len(numbers) > 1
        roles = {band: role for band, role in parsed["roles"].items() if not numbers or band in numbers}
        if roles:
            self._roles = roles
            self._roles_guessed = not parsed["roles_chosen"]
        if "pipette_bands" in state:
            self._pipette_bands = [band for band in parsed["pipette_bands"] if not numbers or band in numbers]
        self._set_derivative(parsed["derivative"])
        self._pick_kind = parsed["pipette_kind"]
        self._picks = [tuple(pick) if self._pick_kind == "color" else pick for pick in parsed["pipette_picks"]]
        self._seeds = list(parsed["pipette_seeds"])
        with _signals_blocked(self._similar_low_spin, self._similar_high_spin, self._similar_shape_check,
                              self._tolerance_spin, self._opening_combo, self._fill_holes_check):
            self._similar_low_spin.setValue(parsed["pipette_similar"][0])
            self._similar_high_spin.setValue(parsed["pipette_similar"][1])
            self._similar_shape_check.setChecked(parsed["pipette_shape"])
            self._tolerance_spin.setValue(parsed["pipette_tolerance"])
            self._opening_combo.setCurrentIndex(self._opening_combo.findData(parsed["pipette_opening"]))
            self._fill_holes_check.setChecked(parsed["pipette_fill_holes"])
        self._set_pick_target(parsed["pipette_target"])
        try:
            data = parsed["pipette_selection"]
            self._pipette_selection = RasterSelection.from_dict(data) if data else None
        except (ValueError, TypeError):
            self._pipette_selection = None
        selection = self._pipette_selection
        if selection is not None:
            # A state saved before the shape: the selection follows the box (checked by default).
            from dataclasses import replace
            self._pipette_selection = replace(selection, shape=parsed["pipette_shape"],
                                              object_opening=parsed["pipette_opening"], fill_holes=parsed["pipette_fill_holes"])
        self._pipette_on = parsed["pipette_on"]
        if self._rendered_only:
            self._rendered_rgb_bands()
            self._all_bands = False
            self._custom_quantity = False
            self._active_band = 1
            self._set_derivative(RasterDerivative.VALUE)
        self._apply_band()
        self._set_range(parsed["minimum"], parsed["maximum"])
        with _signals_blocked(self._expression_edit):
            self._expression_edit.setPlainText(parsed["expression"])
        self._preview_on = parsed["preview"]
        mode = parsed["mode"]
        if mode is RasterSelectionMode.CLASSES:
            mode = RasterSelectionMode.RANGE  # no CLASSES group any more: a class is picked with the pipette
        self._activate_mode(mode, emit=False)
        self._rebuild_chips()
        self._show_pipette_result()
        self._refresh_pixel_display()
        self._fill_insert_menu()

    def pipette_was_on(self) -> bool:
        """Whether the pipette tool was on the map in the state last restored (or is on now)."""
        return self._pipette_on

    # === Modes (exclusive groups) ===

    def _has_classes(self) -> bool:
        return bool(self._summary is not None and self._summary.classes)

    def _default_mode(self) -> RasterSelectionMode:
        return PIPETTE if self._rendered_only else RasterSelectionMode.RANGE

    def _activate_mode(self, mode: RasterSelectionMode, emit: bool = True) -> None:
        """Check the group of ``mode``, uncheck and collapse the others."""
        if self._rendered_only:
            mode = PIPETTE
        if mode not in self._mode_groups:
            mode = RasterSelectionMode.RANGE
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
        if changed:
            self._show_band_histogram()
        if emit and changed:
            self._emit_now()

    def _on_group_toggled(self, mode: RasterSelectionMode, checked: bool) -> None:
        if self._switching_mode:
            return
        if checked:
            self._start_expression_from_previous(mode)
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
        self._start_expression_from_previous(mode)
        self._activate_mode(mode)
        self.modeChosen.emit(mode.value)

    def _start_expression_from_previous(self, mode: RasterSelectionMode) -> None:
        """EXPRESSION made active by the user with an empty text: it starts from the selection that was active."""
        if mode is not RasterSelectionMode.EXPRESSION or mode is self._mode:
            return
        formula = previous_group_formula(self.selection(), self._reference)
        if formula:
            with _signals_blocked(self._expression_edit):
                self._expression_edit.setPlainText(formula)

    # === Selection change notification ===

    def _schedule_selection_changed(self, *_args) -> None:
        self._debounce.start()

    def _emit_now(self) -> None:
        self._debounce.stop()
        self.selectionChanged.emit()

    # === Bands ===

    def _band_info(self, number: int) -> Any:
        if self._summary is None:
            return None
        for info in self._summary.bands:
            if int(info.number) == number:
                return info
        return None

    def _band_names_and_alpha(self) -> Tuple[List[str], set]:
        """Band names of the layer and the numbers of its alpha bands (colour interpretation)."""
        bands = self._summary.bands if self._summary is not None else []
        return [info.name for info in bands], {int(info.number) for info in bands if getattr(info, "is_alpha", False)}

    def _colour_bands(self) -> List[int]:
        return color_bands(*self._band_names_and_alpha())

    def _apply_band(self) -> None:
        """Adopt the decimals and the cached histogram of the active band."""
        info = self._band_info(self.current_band())
        self._decimals = decimals_for(info.data_type) if info is not None else FLOAT_DECIMALS
        # The pixel readouts keep the band decimals; the range follows the quantity it applies to.
        range_decimals = DERIVATIVE_DECIMALS if self._derivative.is_terrain else self._decimals
        self._histogram.set_decimals(range_decimals)
        with _signals_blocked(self._min_spin, self._max_spin):
            self._min_spin.setDecimals(range_decimals)
            self._max_spin.setDecimals(range_decimals)
        self._show_band_histogram()
        self._refresh_band_rows()
        if self._all_bands:
            self._range_group.setTitle(self.tr("VALUE RANGE — every band"))
        elif len(self._band_rows) > 1:
            self._range_group.setTitle(self.tr("VALUE RANGE — band {0}").format(self.current_band()))
        else:
            self._range_group.setTitle(self.tr("VALUE RANGE"))

    def _show_band_histogram(self) -> None:
        counts, minimum, maximum = self._histograms.get((self.current_band(), self._histogram_quantity()), ([], 0.0, 0.0))
        self._histogram.set_histogram(counts, minimum, maximum)
        if hasattr(self, "_expression_histogram"):
            self._expression_histogram.set_histogram(counts, minimum, maximum)
            self._expression_histogram.set_range(None, None)
        if self.current_quantity_expression():
            self._histogram.set_decimals(None)
            if maximum > minimum:
                decimals = min(12, max(FLOAT_DECIMALS, 3 - math.floor(math.log10(maximum - minimum))))
                with _signals_blocked(self._min_spin, self._max_spin):
                    self._min_spin.setDecimals(decimals)
                    self._max_spin.setDecimals(decimals)
        self._histogram_status.setText(
            self.tr("No histogram available") if not counts else
            self.tr("Constant value: {0}").format(f"{minimum:g}") if minimum == maximum else
            self.tr("{0} sampled pixels · {1} to {2}").format(sum(counts), f"{minimum:g}", f"{maximum:g}"))
        low, high = spin_bounds(*self._data_bounds(), self._range_decimals(), low=self._low, high=self._high)
        with _signals_blocked(self._min_spin, self._max_spin):
            for spin in (self._min_spin, self._max_spin):
                spin.setRange(low, high)
        self._fill_presets()

    def _range_decimals(self) -> int:
        if self.current_quantity_expression():
            return self._min_spin.decimals()
        return DERIVATIVE_DECIMALS if self._derivative.is_terrain else self._decimals

    def _data_bounds(self) -> Tuple[Bound, Bound]:
        cached = self._histograms.get((self.current_band(), self._histogram_quantity()))
        if cached is None or not cached[0]:
            return None, None
        return cached[1], cached[2]

    def _forget_picks(self, kinds: Sequence[str] = ("color", "value", "classes", "preset")) -> None:
        """Picks of ``kinds`` were read on another band, bands or quantity: they and their selection no longer apply."""
        if self._pick_kind and self._pick_kind not in kinds:
            return
        self._picks, self._pick_kind, self._pipette_selection, self._seeds = [], "", None, []
        self._detected = None
        self._rebuild_chips()
        self._show_pipette_result()

    def _on_active_band_toggled(self, number: int, checked: bool) -> None:
        if not checked:
            return
        if number == ALL_BANDS:
            if self._all_bands:
                return
            self._all_bands = True
            self._custom_quantity = False
            self._set_derivative(RasterDerivative.VALUE)  # a slope of every band at once has no meaning
        else:
            if number == self._active_band and not self._all_bands:
                return
            self._all_bands = False
            self._active_band = number
        self._forget_picks(("value", "classes"))
        self._apply_band()
        self._set_range(None, None)
        self._refresh_pixel_display()
        self._zone_label.setVisible(False)  # its statistics were those of the previous band
        self.bandChanged.emit(self.current_band())
        self.displayChanged.emit()
        self._emit_now()

    def _on_pipette_band_toggled(self, number: int, checked: bool) -> None:
        bands = [band for band in self._pipette_bands if band != number]
        if checked:
            bands.append(number)
        self._pipette_bands = sorted(bands)
        had_picks = bool(self._picks)
        self._forget_picks(("color", "value", "classes"))
        self._refresh_band_rows()
        self.displayChanged.emit()
        if had_picks and not self._picks:
            self._emit_now()

    def _on_role_changed(self, number: int, role: str = ROLE_NONE) -> None:
        if number not in self._band_rows:
            return
        role = role if role in ROLES else ROLE_NONE
        for other, other_role in list(self._roles.items()):
            if other != number and role and other_role == role:
                del self._roles[other]  # a colour is held by one band
        if role:
            self._roles[number] = role
        else:
            self._roles.pop(number, None)
        self._roles_guessed = False
        self._refresh_band_rows()
        self._fill_insert_menu()
        self._fill_presets()
        self._forget_picks(("preset",))
        self.displayChanged.emit()

    def _on_layout_shortcut(self, key: str) -> None:
        self._roles = roles_from_layout(key, self._colour_bands())
        self._roles_guessed = False
        self._refresh_band_rows()
        self._fill_insert_menu()
        self._fill_presets()
        self._forget_picks(("preset",))
        self.displayChanged.emit()

    # === Derivative ===

    def _set_derivative(self, derivative: RasterDerivative) -> None:
        """Adopt ``derivative`` in the combo and everything that depends on it, without emitting."""
        self._derivative = derivative
        index = self._derivative_combo.findData(CUSTOM_QUANTITY if self._custom_quantity else derivative.value)
        with _signals_blocked(self._derivative_combo):
            self._derivative_combo.setCurrentIndex(max(0, index))
        self._quantity_edit.setVisible(self._custom_quantity)
        self._quantity_status.setVisible(self._custom_quantity)
        suffix = DERIVATIVE_SUFFIXES.get(derivative, "")
        for spin in (self._min_spin, self._max_spin):
            spin.setSuffix(suffix)
        self._fill_presets()
        self._update_mode_controls()

    def _on_derivative_index_changed(self, _index: int) -> None:
        self._quantity_debounce.stop()
        self._custom_quantity = self._derivative_combo.currentData() == CUSTOM_QUANTITY
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
        self._fill_insert_menu()
        self.bandChanged.emit(self.current_band())  # the controller then sends the histogram
        self._emit_now()

    def _fill_presets(self) -> None:
        names = {"flat": self.tr("Flat"), "gentle": self.tr("Gentle"), "moderate": self.tr("Moderate"),
                 "steep": self.tr("Steep"), "east": self.tr("East"), "south": self.tr("South"),
                 "west": self.tr("West"), "shadow": self.tr("Shadow"), "lit": self.tr("Lit")}
        suffix = DERIVATIVE_SUFFIXES.get(self._derivative, "")
        presets = derivative_presets(self._derivative)
        menu = self._presets_button.menu()
        menu.clear()
        for key, low, high in presets:
            action = menu.addAction(format_preset(names[key], low, high, suffix))
            action.triggered.connect(lambda _checked=False, bounds=(low, high): self._on_preset_chosen(bounds))
        if presets:
            menu.addSeparator()
        menu.addSection(self.tr("Distribution (approximate)"))
        cached = self._histograms.get((self.current_band(), self._histogram_quantity()))
        for label, low, high in ((self.tr("Central 98% (P1–P99)"), 0.01, 0.99),
                                 (self.tr("Central 90% (P5–P95)"), 0.05, 0.95),
                                 (self.tr("Interquartile range (P25–P75)"), 0.25, 0.75),
                                 (self.tr("Upper quartile (≥ P75)"), 0.75, None)):
            action = menu.addAction(label)
            action.setEnabled(bool(cached and sum(cached[0]) and cached[2] > cached[1]))
            action.triggered.connect(lambda _checked=False, lo=low, hi=high: self._use_quantiles(lo, hi))
        action = menu.addAction(self.tr("All values"))
        action.triggered.connect(lambda _checked=False: self._on_preset_chosen((None, None)))
        keys = spectral_presets_for(self._roles)
        if keys:
            menu.addSection(self.tr("Derived spectral values"))
            for key in keys:
                action = menu.addAction(self._spectral_names()[key])
                action.triggered.connect(lambda _checked=False, k=key: self._use_spectral_quantity(k))
        self._presets_button.setVisible(True)

    def _use_quantiles(self, low: float, high: Bound) -> None:
        cached = self._histograms.get((self.current_band(), self._histogram_quantity()))
        if cached and cached[0]:
            counts, minimum, maximum = cached
            self._on_preset_chosen((histogram_quantile(counts, minimum, maximum, low),
                                    histogram_quantile(counts, minimum, maximum, high) if high is not None else None))

    def _use_spectral_quantity(self, key: str) -> None:
        expression = spectral_quantity(key, self._roles, self._reference)
        if not expression:
            return
        self._use_quantity(expression)
        bounds = (None, 0.1) if key == "ndvi_bare" else (0.3, None) if key == "ndvi_vegetation" else (0.1, None)
        self._on_preset_chosen(bounds)

    def _on_preset_chosen(self, bounds: Tuple[Bound, Bound]) -> None:
        self._set_range(*bounds)
        self._activate_mode(RasterSelectionMode.RANGE, emit=False)  # a usual threshold is a range selection
        self._emit_now()

    def _update_mode_controls(self) -> None:
        """Say in PIPETTE which quantity a value pick reads; the range menu entry needs a formula."""
        terrain = self._derivative.is_terrain
        if hasattr(self, "_quantity_label") and self._last_pixel is None:
            self._quantity_label.setText(
                self.tr("picks on: {0}").format(self._derivative_combo.currentText()) if terrain or self._custom_quantity else "")
        if hasattr(self, "_derivative_combo"):
            self._derivative_combo.setEnabled(not self._all_bands)
            self._derivative_combo.setToolTip(
                self.tr("A slope, aspect... reads one band as a DTM: choose a band in BANDS first") if self._all_bands
                else self.tr("Quantity the range applies to. Slope, aspect, hillshade and roughness read the active band as a DTM."))
        if hasattr(self, "_insert_button"):
            self._fill_insert_menu()

    # === Range ===

    def _set_range(self, low: Bound, high: Bound) -> None:
        """Store the range (normalised against the data) and show it everywhere, without emitting."""
        if low is not None and high is not None and low > high:
            low, high = high, low
        self._low, self._high = normalize_range(low, high, *self._data_bounds())
        self._histogram.set_range(self._low, self._high)
        limits = spin_bounds(*self._data_bounds(), self._range_decimals(), low=self._low, high=self._high)
        with _signals_blocked(self._min_spin, self._max_spin):
            self._min_spin.setRange(*limits)
            self._max_spin.setRange(*limits)
            self._min_spin.setValue(self._min_spin.minimum() if self._low is None else self._low)
            self._max_spin.setValue(self._max_spin.maximum() if self._high is None else self._high)
        if self._custom_quantity and self._mode is RasterSelectionMode.RANGE and hasattr(self, "_expression_edit"):
            formula = quantity_range_formula(self._quantity_edit.toPlainText(), self._low, self._high)
            with _signals_blocked(self._expression_edit):
                self._expression_edit.setPlainText(formula)

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

    # === Pipette and object detector ===

    def set_band_spans(self, spans: Dict[int, float]) -> None:
        """Observed value range of each band (``max - min``), the base of the pipette tolerance."""
        self._band_spans = {int(band): float(span) for band, span in (spans or {}).items() if span and span > 0}

    def _value_span(self, band: int = 0) -> float:
        """Value range of ``band`` (the active one by default): its statistics, its histogram, else its type."""
        band = band or self.current_band()
        if band in self._band_spans:
            return self._band_spans[band]
        cached = self._histograms.get((band, RasterDerivative.VALUE))
        if cached and cached[2] > cached[1]:
            return float(cached[2] - cached[1])
        info = self._band_info(band)
        kind = info.data_type if info is not None else "Byte"
        return 65535.0 if kind in ("UInt16", "Int16") else 255.0

    def set_color_sample(self, values: Dict[int, Optional[float]], extend: bool = False,
                         terrain: Optional[Dict[RasterDerivative, Optional[float]]] = None,
                         point: Optional[Tuple[float, float]] = None) -> None:
        """A pixel was clicked with the pipette or the detector: the PIPETTE group selects the pixels that look like it.

        Two or more pipette bands select a similar colour (an expression); a paletted raster
        selects the class under the click; a single band (DTM, index) or a slope / aspect...
        selects a range around the value.

        Args:
            values: Band number -> value of the clicked pixel (None for NoData).
            extend: Ctrl+click; the colour, class or value is added to the ones already picked.
            terrain: Slope, aspect... of the pixel, read when the pipette picks one.
            point: The clicked point (layer CRS): in object detection, the object grows from it.
        """
        bands = list(self._pipette_bands)
        band = bands[0] if len(bands) == 1 and not self._derivative.is_terrain and not self._custom_quantity else self.current_band()
        if self._custom_quantity:
            value = (terrain or {}).get("custom")
            kind, pick, missing = "value", value, value is None
        elif len(bands) >= 2 and not self._derivative.is_terrain:
            kind, pick = "color", tuple(values.get(number) for number in bands)
            missing = any(value is None for value in pick)
        elif self._has_classes() and not self._derivative.is_terrain:
            value = values.get(band)
            missing = value is None or not math.isfinite(value)
            kind, pick = "classes", (None if missing else int(round(value)))
        else:
            value = (terrain or {}).get(self._derivative) if self._derivative.is_terrain else values.get(band)
            kind, pick, missing = "value", value, value is None
        flat = pick if isinstance(pick, tuple) else (pick,)
        missing = missing or any(value is None or not math.isfinite(value) for value in flat)
        if missing:
            self._sample_label.setText(self.tr("This pixel has no value (NoData): pick another one"))
            return
        if not extend or kind != self._pick_kind:
            self._picks, self._seeds = [], []
        self._pick_kind = kind
        if pick not in self._picks:
            self._picks.append(pick)
        if point is not None:
            x, y = float(point[0]), float(point[1])
            if math.isfinite(x) and math.isfinite(y) and all(seed[:2] != (x, y) for seed in self._seeds):
                self._seeds.append((x, y, pick))  # another pool of the very same colour is another object
        self._apply_picks()

    def _apply_picks(self, debounced: bool = False) -> None:
        """Selection of the picks: a colour expression, the classes, or a range around the values.

        In object detection each click is an object of its own criterion (the pick read
        there), the selection itself keeping their union.

        Args:
            debounced: Signal the change after the input settles (the tolerance spin box), not at once.
        """
        if self._pick_kind == "preset":  # a spectral index: no pick to read again
            self._set_pipette_selection(self._pipette_selection, debounced)
            return
        objects: Tuple[RasterSelection, ...] = ()
        if self._pick_target in (PICK_OBJECT, PICK_SIMILAR_OBJECTS) and self._seeds:
            objects = tuple(self._picks_selection([pick], ((x, y),)) for x, y, pick in self._seeds)
        similar = self.similar_ratio() if objects and self._pick_target == PICK_SIMILAR_OBJECTS else ()
        selection = self._picks_selection(self._picks, tuple(seed[:2] for seed in self._seeds) if objects else (),
                                          objects, similar, bool(similar) and self.similar_shape())
        self._set_pipette_selection(selection, debounced)

    def _picks_selection(self, picks: Sequence[Any], seeds: Tuple[Tuple[float, float], ...] = (),
                         objects: Tuple[RasterSelection, ...] = (), similar: Tuple[float, float] = (),
                         shape: bool = False) -> RasterSelection:
        """Selection keeping what looks like ``picks`` (of the current kind), around ``seeds`` when given.

        Args:
            similar: Area ratios of the similar objects mode (empty otherwise).
            shape: The similar objects must be shaped like the clicked ones too.
        """
        bands = list(self._pipette_bands)
        band = bands[0] if len(bands) == 1 and not self._derivative.is_terrain and not self._custom_quantity else self.current_band()
        settings = dict(object_opening=int(self._opening_combo.currentData()), fill_holes=self._fill_holes_check.isChecked())
        if self._pick_kind == "color":
            bands = list(self._pipette_bands)
            tolerances = [tolerance_value(self._tolerance_spin.value(), self._value_span(number)) for number in bands]
            expression = color_similarity_expression(self._reference, bands, picks, tolerances)
            return RasterSelection(band=band, mode=RasterSelectionMode.EXPRESSION, expression=expression,
                                   seeds=seeds, objects=objects, similar=similar, shape=shape, **settings)
        if self._pick_kind == "classes":
            return RasterSelection(band=band, mode=RasterSelectionMode.CLASSES, classes=frozenset(picks),
                                   seeds=seeds, objects=objects, similar=similar, shape=shape, **settings)
        low_bound, high_bound = self._data_bounds()
        if band != self.current_band():
            cached = self._histograms.get((band, RasterDerivative.VALUE))
            low_bound, high_bound = (cached[1], cached[2]) if cached else (None, None)
        known = low_bound is not None and high_bound is not None and high_bound > low_bound
        if known:
            span = high_bound - low_bound
        elif self._custom_quantity:
            span = 1.0
        elif self._derivative.is_terrain:
            span = DERIVATIVE_BOUNDS.get(self._derivative, (0.0, 100.0))[1]  # no histogram yet: the natural range
        else:
            span = self._value_span(band)
        tolerance = tolerance_value(self._tolerance_spin.value(), span)
        if self._custom_quantity:
            quantity = self._quantity_edit.toPlainText().strip()
            expression = " OR ".join(f"(abs(({quantity}) - {_number(pick)}) <= {_number(tolerance)})" for pick in picks)
            return RasterSelection(band=band, mode=RasterSelectionMode.EXPRESSION, expression=expression,
                                   seeds=seeds, objects=objects, similar=similar, shape=shape, **settings)
        if len(picks) > 1 and not self._derivative.is_terrain:
            expression = color_similarity_expression(self._reference, [band], [(pick,) for pick in picks], tolerance)
            return RasterSelection(band=band, mode=RasterSelectionMode.EXPRESSION, expression=expression,
                                   seeds=seeds, objects=objects, similar=similar, shape=shape, **settings)
        low, high = normalize_range(min(picks) - tolerance, max(picks) + tolerance, low_bound, high_bound)
        return RasterSelection(band=band, mode=RasterSelectionMode.RANGE, derivative=self._derivative,
                               minimum=low, maximum=high, seeds=seeds, objects=objects, similar=similar, shape=shape, **settings)

    def _on_object_settings_changed(self, _value: Any) -> None:
        if self._pick_target in (PICK_OBJECT, PICK_SIMILAR_OBJECTS) and self._picks:
            self._apply_picks(debounced=True)

    def similar_ratio(self) -> Tuple[float, float]:
        """``(low, high)`` area ratios of the similar objects mode."""
        low, high = float(self._similar_low_spin.value()), float(self._similar_high_spin.value())
        return (min(low, high), max(low, high))

    def similar_shape(self) -> bool:
        """Whether the similar objects must be shaped like the clicked ones (compactness within the ratios)."""
        return bool(self._similar_shape_check.isChecked())

    def _on_similar_ratio_changed(self, _value: Any) -> None:
        if self._pick_target == PICK_SIMILAR_OBJECTS and self._picks and self._pick_kind in ("color", "value", "classes"):
            self._apply_picks(debounced=True)

    def _set_pipette_selection(self, selection: Optional[RasterSelection], debounced: bool = False) -> None:
        self._pipette_selection = None if selection is None or selection.is_empty else selection
        self._detected = None
        self._rebuild_chips()
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
        """The status line of the pipette: empty when the chips say it all; the expression as tooltip of the group."""
        selection = self._pipette_selection
        if selection is None:
            self._sample_label.setText("" if not self._picks else self._sample_label.text())
            self._pipette_group.setToolTip("")
            return
        self._sample_label.setText("")
        self._pipette_group.setToolTip(selection.describe())

    def show_detected_objects(self, count: Optional[int], area: Optional[float] = None, truncated: bool = False) -> None:
        """What object detection found for the current selection; ``count`` None: it could not be read.

        The figures go to the selection strip (:meth:`detected_objects`); the status line only
        says what went wrong.

        Args:
            count: Number of objects (separate patches) found under the clicks.
            area: Their ground area in square metres, None when unknown.
            truncated: An object went on past the largest window read and was cut.
        """
        selection = self._pipette_selection
        if selection is None or not selection.seeds:
            self._detected = None
            self.summaryChanged.emit()
            return
        self._detected = (count, area, bool(truncated))
        if count is None:
            text = self.tr("The object could not be read")
        elif count == 0:
            text = self.tr("No object under the click: raise the tolerance or click another pixel")
        elif truncated:
            text = self.tr("An object is larger than the window read and was cut: lower the tolerance")
        else:
            text = ""
        self._sample_label.setText(text)
        self.summaryChanged.emit()

    def detected_objects(self) -> Optional[Tuple[Optional[int], Optional[float], bool]]:
        """``(count, area in m², truncated)`` of the last object detection; None when there is none."""
        return self._detected

    def pick_target(self) -> str:
        """What a click of the pipette selects: :data:`PICK_SIMILAR`, :data:`PICK_OBJECT` or :data:`PICK_SIMILAR_OBJECTS`."""
        return self._pick_target

    def set_pick_target(self, target: str) -> None:
        """Adopt the target of the rail tool that went on the map (the detector or the pipette). Does not emit ``targetChanged``."""
        changed = self._set_pick_target(target)
        if changed and self._picks and self._pick_kind in ("color", "value", "classes"):
            self._apply_picks()  # the same picks, on the whole raster or as objects

    def _set_pick_target(self, target: str) -> bool:
        target = target if target in PICK_TARGETS else PICK_SIMILAR
        changed = target != self._pick_target
        self._pick_target = target
        button = self._target_buttons.get(target)
        if button is not None:
            with _signals_blocked(*self._target_buttons.values()):
                button.setChecked(True)
        if hasattr(self, "_similar_widget"):
            self._similar_widget.setVisible(target == PICK_SIMILAR_OBJECTS)
        if hasattr(self, "_object_settings"):
            self._object_settings.setVisible(target in (PICK_OBJECT, PICK_SIMILAR_OBJECTS))
            self._fill_holes_check.setVisible(target == PICK_OBJECT)
        return changed

    def _on_target_button(self, target: str, checked: bool) -> None:
        if not checked or target == self._pick_target:
            return
        self._set_pick_target(target)
        self.targetChanged.emit(self._pick_target)
        if self._picks and self._pick_kind in ("color", "value", "classes"):
            self._apply_picks()

    def _on_tolerance_changed(self, _value: float) -> None:
        # The selection follows at once, its signal once the wheel stops: each one may read the raster.
        if self._picks and self._pick_kind in ("color", "value"):
            self._apply_picks(debounced=True)

    # === Pixel readout ===

    def _refresh_pixel_display(self) -> None:
        if self._last_pixel is None:
            self._pixel_coordinates_label.setText("")
            self._pixel_coordinates_label.setToolTip("")
            self._quantity_label.setText("")
            self._refresh_band_rows()
            return
        x, y, _values, terrain = self._last_pixel
        digits = self._coordinate_decimals
        nodata = self.tr("NoData")
        parts = [f"X {x:.{digits}f} · Y {y:.{digits}f}"]
        for derivative, value in terrain.items():
            if derivative == "custom":
                parts.append(self.tr("Derived value: {0}").format(format_pixel_value(value, self._range_decimals(), nodata)))
                continue
            name = self._derivative_combo.itemText(max(0, self._derivative_combo.findData(derivative.value)))
            parts.append(f"{name}: {format_derived_value(derivative, value, nodata)}")
        self._pixel_coordinates_label.setText("  ·  ".join(parts))
        rows = []
        for hx, hy, value, band, shown in self._history:
            info = self._band_info(band)
            decimals = decimals_for(info.data_type) if info is not None else FLOAT_DECIMALS
            rows.append((f"{hx:.{digits}f} · {hy:.{digits}f}", shown or format_pixel_value(value, decimals, nodata), band))
        from html import escape
        tooltip = "<b>" + escape(parts[0]) + "</b>"
        if len(parts) > 1:
            tooltip += "<br>" + "<br>".join(escape(part) for part in parts[1:])
        tooltip += history_html(rows, self.tr("LAST PICKS"))
        self._pixel_coordinates_label.setToolTip(tooltip)
        # The quantity a value pick reads, with its value at the last click, in the PIPETTE group.
        if self._custom_quantity:
            self._quantity_label.setText(self.tr("Derived value: {0}").format(
                format_pixel_value(terrain.get("custom"), self._range_decimals(), nodata)))
        elif self._derivative.is_terrain:
            name = self._derivative_combo.currentText()
            self._quantity_label.setText(f"{name}: {format_derived_value(self._derivative, terrain.get(self._derivative), nodata)}")
        else:
            self._quantity_label.setText("")
        self._refresh_band_rows()
