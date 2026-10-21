# -*- coding: utf-8 -*-
"""
Range Histogram Widget.

Histogram of a raster band with two draggable handles delimiting a value
range, used by the raster EXPLORING panel. The pixel <-> value conversions and
the range arithmetic live in pure functions of this module so they can be
tested without Qt.

A bound set to None means "unbounded on that side": a handle dragged onto the
data minimum (or maximum) reports None, so a selection never cuts the pixels
that a sampled histogram missed.
"""
import math
from typing import List, Optional, Sequence, Tuple

try:
    from qgis.PyQt.QtCore import QPointF, QRectF, QSize, Qt, pyqtSignal
    from qgis.PyQt.QtGui import QBrush, QColor, QPainter, QPalette, QPen
    from qgis.PyQt.QtWidgets import QSizePolicy, QWidget
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    QWidget = object

    def pyqtSignal(*_args):
        """Placeholder signal when Qt is unavailable."""
        return None

Bound = Optional[float]

LOW_HANDLE = "low"
HIGH_HANDLE = "high"
SQRT_SCALE_RATIO = 10.0
SPIN_BOX_LIMIT = 1e9

# Plot geometry (pixels): side margin = half a handle, grip zone under the bars.
_MARGIN_X = 6.0
_MARGIN_TOP = 4.0
_GRIP_HEIGHT = 7.0
_BAR_GAP = 1.0


# ---------------------------------------------------------------------------
# Pure helpers (no Qt)
# ---------------------------------------------------------------------------

def value_at(x: float, width: float, minimum: float, maximum: float) -> float:
    """Return the data value under the pixel column ``x`` of a plot ``width`` pixels wide.

    Args:
        x: Abscissa relative to the left edge of the plot.
        width: Plot width in pixels.
        minimum: Value at ``x = 0``.
        maximum: Value at ``x = width``.

    Returns:
        Value clamped to ``[minimum, maximum]``; ``minimum`` for a degenerate plot.
    """
    if width <= 0 or not maximum > minimum:
        return float(minimum)
    ratio = min(max(float(x) / float(width), 0.0), 1.0)
    if ratio >= 1.0:
        return float(maximum)
    return float(minimum) + ratio * (float(maximum) - float(minimum))


def x_of(value: float, width: float, minimum: float, maximum: float) -> float:
    """Return the pixel abscissa of ``value`` (inverse of :func:`value_at`, clamped to the plot)."""
    if width <= 0 or not maximum > minimum:
        return 0.0
    ratio = (float(value) - float(minimum)) / (float(maximum) - float(minimum))
    return min(max(ratio, 0.0), 1.0) * float(width)


def bar_heights(counts: Sequence[int], height: float, sqrt_scale: bool = False) -> List[float]:
    """Return the pixel height of each bar, the highest bin filling ``height``.

    Args:
        counts: Pixel count of each bin (negative counts are drawn as 0).
        height: Height available for the bars.
        sqrt_scale: Use the square root of the counts so a single peak does
            not flatten the rest of the distribution.

    Returns:
        One height per bin; all zeros when every count is 0.
    """
    values = [max(0, int(count)) for count in counts]
    peak = max(values, default=0)
    if peak <= 0 or height <= 0:
        return [0.0] * len(values)
    if sqrt_scale:
        root = math.sqrt(peak)
        return [math.sqrt(value) / root * height for value in values]
    return [value / peak * height for value in values]


def needs_sqrt_scale(counts: Sequence[int], ratio: float = SQRT_SCALE_RATIO) -> bool:
    """Tell whether the highest bin dwarfs the others (peak > ``ratio`` x median of non-empty bins)."""
    non_empty = sorted(int(count) for count in counts if count > 0)
    if len(non_empty) < 2:
        return False
    return non_empty[-1] > ratio * non_empty[len(non_empty) // 2]


def bins_in_range(count: int, minimum: float, maximum: float, low: Bound, high: Bound) -> List[bool]:
    """Tell, for each of ``count`` equal bins over ``[minimum, maximum]``, whether its centre is kept."""
    if count <= 0:
        return []
    step = (float(maximum) - float(minimum)) / count
    keep = []
    for index in range(count):
        centre = float(minimum) + (index + 0.5) * step
        keep.append((low is None or centre >= low) and (high is None or centre <= high))
    return keep


def histogram_quantile(counts: Sequence[int], minimum: float, maximum: float, fraction: float) -> Bound:
    """Approximate a quantile by interpolating inside the occupied histogram bin."""
    weights = [max(0, int(count)) for count in counts]
    total = sum(weights)
    if not total or not (math.isfinite(minimum) and math.isfinite(maximum)) or maximum < minimum:
        return None
    fraction = min(1.0, max(0.0, float(fraction)))
    step = (maximum - minimum) / len(weights)
    target, cumulative = fraction * total, 0
    for index, count in enumerate(weights):
        if count and target <= cumulative + count:
            return minimum + (index + min(1.0, max(0.0, (target - cumulative) / count))) * step
        cumulative += count
    return maximum


def clamp_range(low: Bound, high: Bound, minimum: float, maximum: float) -> Tuple[Bound, Bound]:
    """Clamp the set bounds to ``[minimum, maximum]`` and order them (low <= high)."""
    if maximum < minimum:
        minimum, maximum = maximum, minimum
    if low is not None:
        low = min(max(float(low), minimum), maximum)
    if high is not None:
        high = min(max(float(high), minimum), maximum)
    if low is not None and high is not None and low > high:
        low, high = high, low
    return low, high


def normalize_range(low: Bound, high: Bound, minimum: Bound, maximum: Bound) -> Tuple[Bound, Bound]:
    """Drop the bounds that do not constrain the data.

    A lower bound at or below the data minimum (an upper bound at or above
    the data maximum) keeps every pixel on that side, so it becomes None.
    Unknown data bounds leave the range untouched.
    """
    if low is not None and minimum is not None and low <= minimum:
        low = None
    if high is not None and maximum is not None and high >= maximum:
        high = None
    return low, high


def snap(value: float, decimals: Optional[int], minimum: float, maximum: float) -> float:
    """Round an interior value to ``decimals``; the data bounds themselves are kept exact.

    Keeping the edges exact lets a handle dragged to the end of the plot mean
    "unbounded" (see :func:`normalize_range`) even when rounding would move it
    inside the data.
    """
    if decimals is None or value <= minimum or value >= maximum:
        return float(value)
    return min(max(round(float(value), int(decimals)), float(minimum)), float(maximum))


def spin_bounds(minimum: Bound, maximum: Bound, decimals: int,
                low: Bound = None, high: Bound = None) -> Tuple[float, float]:
    """Spin box range covering the data, rounded outwards to ``decimals``.

    QDoubleSpinBox rounds its bounds to its decimals; rounding outwards keeps
    the exact data bounds inside the range so that the extreme spin values
    still mean "every pixel" once passed through :func:`normalize_range`.
    Explicit selection bounds are included too: an approximate histogram
    must never clamp the displayed threshold to a different effective value.
    """
    if minimum is None or maximum is None:
        minimum, maximum = -SPIN_BOX_LIMIT, SPIN_BOX_LIMIT
    values = [float(minimum), float(maximum)] + [float(value) for value in (low, high) if value is not None]
    factor = 10 ** max(0, int(decimals))
    return math.floor(min(values) * factor) / factor, math.ceil(max(values) * factor) / factor


def nearest_handle(x: float, low_x: float, high_x: float) -> str:
    """Handle grabbed by a click at ``x``: the side it lies on, else the closest one."""
    if x <= low_x:
        return LOW_HANDLE
    if x >= high_x:
        return HIGH_HANDLE
    return LOW_HANDLE if (x - low_x) <= (high_x - x) else HIGH_HANDLE


def drag_handle(active: str, value: float, low: float, high: float) -> Tuple[str, float, float]:
    """Move the ``active`` handle to ``value``; past the other handle, both swap roles.

    Swapping (instead of blocking) means two handles on top of each other
    can always be pulled apart, whichever one was grabbed.

    Returns:
        ``(active handle, low, high)`` with ``low <= high``.
    """
    if active == LOW_HANDLE:
        if value <= high:
            return LOW_HANDLE, value, high
        return HIGH_HANDLE, high, value
    if value >= low:
        return HIGH_HANDLE, low, value
    return LOW_HANDLE, value, low


def _event_x(event) -> float:
    """Abscissa of a mouse event (``position()`` on Qt 6, ``pos()`` on Qt 5)."""
    position = event.position() if hasattr(event, "position") else event.pos()
    return float(position.x())


# ---------------------------------------------------------------------------
# Widget
# ---------------------------------------------------------------------------

class RangeHistogramWidget(QWidget):
    """Histogram with a draggable ``[low, high]`` range.

    Signals:
        rangeChanged(float, float): Emitted when a drag or a click ends with a
            new range. The arguments are the effective bounds (data bounds
            for an unbounded side); :meth:`range` gives the None-aware range.
    """

    rangeChanged = pyqtSignal(float, float)

    def __init__(self, parent=None):
        """Build an empty histogram.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._counts: List[int] = []
        self._minimum = 0.0
        self._maximum = 0.0
        self._low: Bound = None
        self._high: Bound = None
        self._decimals: Optional[int] = None
        self._sqrt_scale: Optional[bool] = None
        self._accent: Optional[QColor] = None
        self._drag_handle: Optional[str] = None
        self._press_range: Tuple[Bound, Bound] = (None, None)
        self.setMinimumSize(200, 72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self.setAccessibleName(self.tr("Value range histogram"))
        self.setToolTip(self.tr("Drag the handles, or click, to choose the range of values to keep"))

    # === Public API ===

    def set_histogram(self, counts: Sequence[int], minimum: float, maximum: float) -> None:
        """Show a histogram; the current range is kept, clamped to the new bounds.

        Args:
            counts: Pixel count of each bin, bins spread evenly over ``[minimum, maximum]``.
            minimum: Value of the left edge.
            maximum: Value of the right edge.
        """
        self._counts = [int(count) for count in counts or ()]
        self._minimum = float(minimum)
        self._maximum = float(maximum)
        if self._has_extent():
            self._low, self._high = normalize_range(
                *clamp_range(self._low, self._high, self._minimum, self._maximum),
                self._minimum, self._maximum)
        self._update_accessible_description()
        self.update()

    def set_range(self, low: Bound, high: Bound) -> None:
        """Set the range without emitting ``rangeChanged`` (None = unbounded side)."""
        if self._has_extent():
            low, high = normalize_range(*clamp_range(low, high, self._minimum, self._maximum),
                                        self._minimum, self._maximum)
        elif low is not None and high is not None and low > high:
            low, high = high, low
        self._low, self._high = low, high
        self._update_accessible_description()
        self.update()

    def range(self) -> Tuple[Bound, Bound]:
        """Return ``(low, high)``; None for a side that keeps every value."""
        return self._low, self._high

    def set_accent(self, color: 'QColor') -> None:
        """Colour of the bars inside the range (palette highlight by default)."""
        self._accent = QColor(color)
        self.update()

    def set_decimals(self, decimals: Optional[int]) -> None:
        """Round the dragged values to ``decimals`` (None = no rounding)."""
        self._decimals = decimals

    def set_sqrt_scale(self, enabled: Optional[bool]) -> None:
        """Force the square root scale on or off; None picks it from the data."""
        self._sqrt_scale = enabled
        self.update()

    def sizeHint(self):
        """Preferred size of the plot."""
        return QSize(280, 90)

    def minimumSizeHint(self):
        """Smallest readable size of the plot."""
        return QSize(200, 72)

    # === Geometry ===

    def _has_extent(self) -> bool:
        return self._maximum > self._minimum

    def _plot_rect(self) -> 'QRectF':
        width = max(1.0, float(self.width()) - 2 * _MARGIN_X)
        height = max(1.0, float(self.height()) - _MARGIN_TOP - _GRIP_HEIGHT)
        return QRectF(_MARGIN_X, _MARGIN_TOP, width, height)

    def _effective_range(self) -> Tuple[float, float]:
        low = self._minimum if self._low is None else self._low
        high = self._maximum if self._high is None else self._high
        return low, high

    # === Painting ===

    def paintEvent(self, event):
        """Draw the bars (accent inside the range, grey outside) and both handles."""
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            palette = self.palette()
            rect = self._plot_rect()
            painter.fillRect(rect, palette.color(QPalette.ColorRole.Base))
            accent = self._accent if self._accent is not None else palette.color(QPalette.ColorRole.Highlight)
            muted = palette.color(QPalette.ColorRole.Mid)
            if not self._counts or not self._has_extent():
                painter.setPen(palette.color(QPalette.ColorRole.WindowText))
                text = (self.tr("Constant value: {0}").format(f"{self._minimum:g}")
                        if sum(self._counts) and self._minimum == self._maximum else self.tr("No histogram"))
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
                return
            sqrt_scale = needs_sqrt_scale(self._counts) if self._sqrt_scale is None else self._sqrt_scale
            heights = bar_heights(self._counts, rect.height(), sqrt_scale)
            inside = bins_in_range(len(self._counts), self._minimum, self._maximum, self._low, self._high)
            bar_width = rect.width() / len(self._counts)
            gap = _BAR_GAP if bar_width > 3 * _BAR_GAP else 0.0
            for index, bar_height in enumerate(heights):
                if bar_height <= 0:
                    continue
                left = rect.left() + index * bar_width
                painter.fillRect(QRectF(left, rect.bottom() - bar_height, max(1.0, bar_width - gap), bar_height),
                                 accent if inside[index] else muted)
            self._paint_handles(painter, rect, palette)
        finally:
            painter.end()

    def _paint_handles(self, painter, rect, palette) -> None:
        color = palette.color(QPalette.ColorRole.WindowText)
        low, high = self._effective_range()
        for side, value in ((LOW_HANDLE, low), (HIGH_HANDLE, high)):
            x = rect.left() + x_of(value, rect.width(), self._minimum, self._maximum)
            painter.setPen(QPen(color, 2.0 if side == self._drag_handle else 1.5))
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            painter.setBrush(QBrush(color))
            painter.drawRect(QRectF(x - 3.0, rect.bottom() + 1.0, 6.0, _GRIP_HEIGHT - 2.0))

    def _update_accessible_description(self) -> None:
        low, high = self._effective_range()
        self.setAccessibleDescription(self.tr("Kept values from {0} to {1}").format(f"{low:g}", f"{high:g}"))

    # === Mouse ===

    def mousePressEvent(self, event):
        """Grab the handle closest to the click and move it there."""
        if event.button() != Qt.MouseButton.LeftButton or not self._has_extent():
            event.ignore()
            return
        rect = self._plot_rect()
        x = _event_x(event) - rect.left()
        low, high = self._effective_range()
        self._press_range = (self._low, self._high)
        self._drag_handle = nearest_handle(
            x, x_of(low, rect.width(), self._minimum, self._maximum),
            x_of(high, rect.width(), self._minimum, self._maximum))
        self._move_handle(x, rect.width())
        event.accept()

    def mouseMoveEvent(self, event):
        """Follow the mouse with the grabbed handle."""
        if self._drag_handle is None:
            event.ignore()
            return
        rect = self._plot_rect()
        self._move_handle(_event_x(event) - rect.left(), rect.width())
        event.accept()

    def mouseReleaseEvent(self, event):
        """Drop the handle and emit ``rangeChanged`` when the range moved."""
        if self._drag_handle is None:
            event.ignore()
            return
        rect = self._plot_rect()
        self._move_handle(_event_x(event) - rect.left(), rect.width())
        self._drag_handle = None
        self.update()
        event.accept()
        if (self._low, self._high) != self._press_range:
            low, high = self._effective_range()
            self.rangeChanged.emit(low, high)

    def _move_handle(self, x: float, width: float) -> None:
        value = snap(value_at(x, width, self._minimum, self._maximum), self._decimals, self._minimum, self._maximum)
        low, high = self._effective_range()
        self._drag_handle, low, high = drag_handle(self._drag_handle, value, low, high)
        self._low, self._high = normalize_range(low, high, self._minimum, self._maximum)
        self._update_accessible_description()
        self.update()
