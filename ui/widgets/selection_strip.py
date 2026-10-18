# -*- coding: utf-8 -*-
"""
Selection strip between EXPLORING and FILTERING (FilterMate 5 mockup).

One line, tinted with the colour of the source layer kind, saying what the
EXPLORING selection hands over to FILTERING:

* vector: ``Selection → source geometry    3 features``
* raster: ``Selection → source geometry    200 – 260 · 38.9 %``
* point cloud: ``Kept points    18.9 M / 38.4 M (49.1 %)``

The texts are built by pure functions of this module (testable without Qt);
:class:`~ui.controllers.coverage_dock_extras.CoverageDockExtras` owns the widget,
translates the texts and refreshes it.
"""
import math
from decimal import Decimal
from typing import Callable, Optional

try:
    from qgis.PyQt.QtCore import Qt
    from qgis.PyQt.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy
    QT_AVAILABLE = True
except ImportError:  # pragma: no cover - unit tests without Qt
    QT_AVAILABLE = False
    QFrame = QLabel = object

STRIP_NAME = 'frame_selection_strip'
CAPTION_NAME = 'label_selection_strip_caption'
VALUE_NAME = 'label_selection_strip_value'
KIND_PROPERTY = 'fm_kind'  # 'vector' | 'raster' | 'point_cloud', read by mockup.qss

# Unit after the bounds of a terrain derivative (raster_exploring_panel.DERIVATIVE_SUFFIXES).
_DERIVATIVE_UNITS = {'slope_degrees': '°', 'slope_percent': '%', 'aspect': '°'}


def _identity(text: str) -> str:
    return text


def _number(value: float) -> str:
    """``200.0`` -> ``"200"``, ``0.25`` -> ``"0.25"``, at most 3 decimals."""
    text = f"{float(value):.3f}".rstrip('0').rstrip('.')
    return "0" if text in ("-0", "") else text


# ---------------------------------------------------------------------------
# Pure helpers (no Qt)
# ---------------------------------------------------------------------------

def vector_strip_value(groupbox: str, count: Optional[int], has_expression: bool = False,
                       translate: Callable[[str], str] = _identity) -> str:
    """Value of the vector strip.

    Args:
        groupbox: Active EXPLORING group (``single_selection``, ``multiple_selection``,
            ``custom_selection``).
        count: Features of the EXPLORING selection, None when unknown.
        has_expression: Whether the custom selection has an expression (count unknown).
        translate: Translation function of the caller.

    Without a selection the filter uses every feature of the source layer, except in
    single selection where it stops (see TaskParameterBuilder.get_and_validate_features).
    """
    if count or (count == 0 and groupbox == 'custom_selection' and has_expression):
        # A custom expression matching nothing filters the source down to nothing: "0 feature(s)".
        return translate("{0} feature(s)").format(f"{int(count):,}".replace(",", " "))
    if groupbox == 'single_selection':
        return translate("no feature selected")
    if groupbox == 'custom_selection' and has_expression and count is None:
        return translate("expression")
    return translate("whole layer")


def percent_text(ratio: float) -> str:
    """Fraction in [0, 1] as ``"38.9 %"``; two significant digits below 0.1 % (``"0.012 %"``), ``"–"`` for NaN.

    2026-10-18: the pools a pipette click selects on an orthophoto are about 0.01 % of
    its pixels, which "0.0 %" showed as nothing selected. The two notations meet at
    0.1 % without a jump ("0.099 %", then "0.1 %"); no trailing zero ("0.01 %").
    """
    percent = float(ratio) * 100
    if math.isnan(percent):
        return "–"
    percent = max(0.0, percent)
    if 0 < percent < 0.1:
        return f"{format(Decimal(f'{percent:.2g}'), 'f')} %"
    return f"{percent:.1f} %"


def raster_strip_value(selection, kept_ratio: Optional[float],
                       translate: Callable[[str], str] = _identity, detected=None) -> str:
    """Value of the raster strip: ``"200 – 260 · 38.9 %"``, ``"3 classes · 12.0 %"``, ``"… · 3 object(s) · 125 m²"``.

    Args:
        selection: The panel's ``RasterSelection`` (None: no constraint).
        kept_ratio: Share (0-1) of the pixels kept, None when unknown.
        translate: Translation function of the caller.
        detected: ``(count, area in m², truncated)`` of the object detection, None without one.
    """
    if selection is None:
        return translate("no constraint")
    mode = getattr(getattr(selection, 'mode', None), 'value', '')
    if mode == 'range':
        unit = _DERIVATIVE_UNITS.get(getattr(getattr(selection, 'derivative', None), 'value', ''), '')
        low, high = selection.minimum, selection.maximum
        if low is not None and high is not None:
            text = f"{_number(low)} – {_number(high)}"
        elif low is not None:
            text = f"≥ {_number(low)}"
        elif high is not None:
            text = f"≤ {_number(high)}"
        else:
            text = translate("no constraint")
        if unit and (low is not None or high is not None):
            text = f"{text} {unit}"
    elif mode == 'classes':
        count = len(getattr(selection, 'classes', ()) or ())
        text = translate("{0} class(es)").format(count)
    else:
        text = translate("raster expression")
    if kept_ratio is not None:
        text += f" · {percent_text(kept_ratio)}"
    if detected is not None:
        count, area = detected[0], detected[1] if len(detected) > 1 else None
        if count is not None:
            text += " · " + translate("{0} object(s)").format(int(count))
        area_text = _area_text(area)
        if area_text:
            text += f" · {area_text}"
    return text


def _area_text(square_metres: Optional[float]) -> str:
    """``"125 m²"``, ``"3.4 ha"``, ``"2.15 km²"``; ``""`` when unknown."""
    try:
        value = float(square_metres)
    except (TypeError, ValueError):
        return ""
    if math.isnan(value) or value < 0:
        return ""
    if value < 10000:
        return f"{value:.0f} m²" if value >= 10 else f"{value:.1f} m²"
    if value < 1e6:
        return f"{value / 1e4:.1f} ha"
    return f"{value / 1e6:.2f} km²"


def objects_text(count: Optional[int], area: Optional[float], translate: Callable[[str], str] = _identity) -> str:
    """``"3 object(s) · 125 m²"``, without the area when unknown; ``""`` without a count."""
    if count is None:
        return ""
    text = translate("{0} object(s)").format(int(count))
    area_text = _area_text(area)
    return f"{text} · {area_text}" if area_text else text


def point_cloud_strip_value(kept: Optional[int], total: Optional[int], expression: str = "",
                            at_most: bool = False, translate: Callable[[str], str] = _identity,
                            detected=None) -> str:
    """Value of the point cloud strip.

    Args:
        kept: Points kept by the criteria when they can be counted (checked classes), else None.
        total: Points of the layer, None when unknown.
        expression: Subset expression of the criteria (shown when the points cannot be counted).
        at_most: The count is an upper bound (the height above the DTM filters further).
        translate: Translation function of the caller.
        detected: ``(count, area in m², truncated)`` of the object detector, None without objects:
            shown instead of their expression (one X / Y box per object).
    """
    from .coverage_panels.point_cloud_exploring_panel import format_count, format_point_counts
    if detected is not None and detected[0] is not None:
        return objects_text(detected[0], detected[1] if len(detected) > 1 else None, translate)
    if kept is not None and kept >= 0:
        counted = format_point_counts(kept, total)
        return f"≤ {counted}" if at_most else counted
    if (expression or "").strip():
        return expression.strip()
    counted = format_count(total) if total is not None else ""
    return f"{translate('all points')} · {counted}" if counted else translate("all points")


# ---------------------------------------------------------------------------
# Widget
# ---------------------------------------------------------------------------

if QT_AVAILABLE:

    class _ElidedLabel(QLabel):
        """Label eliding its text in the middle instead of widening the dock."""

        def __init__(self, parent=None):
            super().__init__(parent)
            self._full = ""
            self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            self.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        def set_full_text(self, text: str) -> None:
            self._full = text or ""
            self.setToolTip(self._full)
            self._elide()

        def full_text(self) -> str:
            return self._full

        def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
            super().resizeEvent(event)
            self._elide()

        def _elide(self) -> None:
            width = max(0, self.contentsRect().width())
            super().setText(self.fontMetrics().elidedText(self._full, Qt.TextElideMode.ElideMiddle, width)
                            if width else self._full)

    class SelectionStrip(QFrame):
        """Tinted line: a caption on the left, the selection value on the right (mono font)."""

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setObjectName(STRIP_NAME)
            self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            try:  # one title band high, like the section headers (spacing scale)
                from ..styles.mockup_design import SPACING
                self.setFixedHeight(SPACING['fm_band'])
            except (ImportError, KeyError):  # pragma: no cover
                pass
            layout = QHBoxLayout(self)
            layout.setContentsMargins(12, 0, 12, 0)
            layout.setSpacing(8)
            self._caption = QLabel(self)
            self._caption.setObjectName(CAPTION_NAME)
            self._value = _ElidedLabel(self)
            self._value.setObjectName(VALUE_NAME)
            layout.addWidget(self._caption)
            layout.addWidget(self._value, 1)

        def set_content(self, kind_value: str, caption: str, value: str, tooltip: str = "") -> None:
            """Show ``caption`` and ``value`` in the colours of ``kind_value``."""
            if self.property(KIND_PROPERTY) != kind_value:
                self.setProperty(KIND_PROPERTY, kind_value)
                for widget in (self, self._caption, self._value):
                    widget.setProperty(KIND_PROPERTY, kind_value)
                    widget.style().unpolish(widget)
                    widget.style().polish(widget)
            self._caption.setText(caption)
            self._value.set_full_text(value)
            self.setToolTip(tooltip)

        def caption(self) -> str:
            return self._caption.text()

        def value(self) -> str:
            return self._value.full_text()

        def kind(self) -> str:
            return self.property(KIND_PROPERTY) or ''
