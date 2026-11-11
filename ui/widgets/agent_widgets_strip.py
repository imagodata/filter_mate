# -*- coding: utf-8 -*-
"""The widgets the agent made, drawn above the line to ask: a range, ticked values, a number.

Widgets only: each one says what the user changed, the controller filters the layer and keeps the state.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from qgis.PyQt.QtCore import QCoreApplication, QRectF, Qt, QTimer, pyqtSignal
from qgis.PyQt.QtGui import QColor, QPainter
from qgis.PyQt.QtWidgets import (
    QDoubleSpinBox, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QScrollArea, QSizePolicy,
    QToolButton,
    QVBoxLayout, QWidget,
)

from ...core.agent.widgets import CATEGORIES, CHART, RANGE, VALUES
from ..styles.mockup_design import plugin_is_dark, tokens

APPLY_DELAY_MS = 400  # a value typed or ticked is applied once the user pauses
STRIP_MAX_HEIGHT = 260
VALUES_MAX_HEIGHT = 100
_VALUE_ROLE = Qt.ItemDataRole.UserRole


def _tr(text: str) -> str:
    return QCoreApplication.translate("AgentWidgets", text)


def default_title(widget: Dict[str, Any]) -> str:
    if widget["kind"] in (RANGE, VALUES, CHART):
        return widget["field"]
    aggregate = {"count": _tr("Count"), "sum": _tr("Sum"), "mean": _tr("Mean"), "min": _tr("Minimum"),
                 "max": _tr("Maximum")}[widget["aggregate"]]
    return f"{aggregate} · {widget['field']}" if widget["field"] else aggregate


def value_text(value: Any) -> str:
    return _tr("(empty)") if value is None else str(value)


def number_text(value: Optional[float]) -> str:
    if value is None:
        return "—"
    if float(value).is_integer() and abs(value) < 1e15:
        return f"{int(value):,}".replace(",", " ")
    return f"{value:,.2f}".replace(",", " ")


CHART_ROW = 16
HISTOGRAM_HEIGHT = 64


def short_number(value: float) -> str:
    """A bound of a histogram, short: 1 200, 0.35, 1.2e+07."""
    if abs(value) >= 1e7:
        return f"{value:.2g}"
    if float(value).is_integer():
        return f"{int(value):,}".replace(",", "\u202f")
    return f"{value:.3g}"


class ChartView(QWidget):
    """Bars drawn by hand: one row per value (categories), or a histogram."""

    def __init__(self, mode: str, parent=None) -> None:
        super().__init__(parent)
        self.mode = mode
        self.bars = []
        self.accent = QColor("#2f6db5")
        self.muted = QColor("#5f5f5f")
        font = self.font()
        if font.pointSizeF() > 0:
            font.setPointSizeF(font.pointSizeF() * 0.85)  # a chart is small print, as the layer name beside it
            self.setFont(font)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._fit()

    def row(self) -> int:
        return max(CHART_ROW, self.fontMetrics().height() + 4)

    def set_bars(self, bars) -> None:
        self.bars = list(bars or [])
        self._fit()
        self.update()

    def _fit(self) -> None:
        if self.mode == CATEGORIES:
            self.setFixedHeight(max(1, len(self.bars)) * self.row() + 2)
        else:
            self.setFixedHeight(HISTOGRAM_HEIGHT + self.fontMetrics().height() + 4)

    def label(self, bar) -> str:
        if bar.get("others"):
            return _tr("others")
        return value_text(bar.get("value"))

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt name
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.bars:
            painter.setPen(self.muted)
            painter.drawText(self.rect(), int(Qt.AlignmentFlag.AlignCenter), "—")
            painter.end()
            return
        top = max(bar["count"] for bar in self.bars) or 1
        width = self.width()
        metrics = self.fontMetrics()
        if self.mode == CATEGORIES:
            label_width = int(width * 0.38)
            count_width = metrics.horizontalAdvance("0000000")
            room = max(4, width - label_width - count_width - 8)
            line = self.row()
            for row, bar in enumerate(self.bars):
                y = row * line
                painter.setPen(self.muted if bar.get("others") else self.palette().text().color())
                text = metrics.elidedText(self.label(bar), Qt.TextElideMode.ElideRight, label_width - 4)
                painter.drawText(QRectF(0, y, label_width - 4, line), int(Qt.AlignmentFlag.AlignVCenter), text)
                length = room * bar["count"] / top
                color = QColor(self.muted if bar.get("others") else self.accent)
                painter.fillRect(QRectF(label_width, y + 3, max(1.0, length), line - 6), color)
                painter.setPen(self.muted)
                painter.drawText(QRectF(label_width + length + 4, y, count_width, line),
                                 int(Qt.AlignmentFlag.AlignVCenter), number_text(bar["count"]))
        else:
            step = width / len(self.bars)
            for index, bar in enumerate(self.bars):
                height = HISTOGRAM_HEIGHT * bar["count"] / top
                painter.fillRect(QRectF(index * step + 1, HISTOGRAM_HEIGHT - height, max(1.0, step - 2), height),
                                 self.accent)
            painter.setPen(self.muted)
            baseline = QRectF(0, HISTOGRAM_HEIGHT + 2, width, metrics.height())
            painter.drawText(baseline, int(Qt.AlignmentFlag.AlignLeft), short_number(self.bars[0]["low"]))
            painter.drawText(baseline, int(Qt.AlignmentFlag.AlignRight), short_number(self.bars[-1]["high"]))
        painter.end()


class WidgetCard(QFrame):
    """One widget: its title, a button to remove it, and its control."""

    changed = pyqtSignal(object)  # the widget with its new state
    remove_requested = pyqtSignal(str)

    def __init__(self, widget: Dict[str, Any], parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("frame_agent_widget")
        self.widget = dict(widget)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(APPLY_DELAY_MS)
        self._timer.timeout.connect(self._emit)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)
        head = QHBoxLayout()
        head.setSpacing(4)
        self.title = QLabel(widget["title"] or default_title(widget), self)
        self.title.setObjectName("label_agent_widget_title")
        self.title.setTextFormat(Qt.TextFormat.PlainText)
        self.title.setToolTip(widget["layer_name"])
        self.layer = QLabel(widget["layer_name"], self)
        self.layer.setObjectName("label_agent_widget_layer")
        self.layer.setTextFormat(Qt.TextFormat.PlainText)
        remove = QToolButton(self)
        remove.setObjectName("toolButton_agent_widget_remove")
        remove.setText("✕")
        remove.setAutoRaise(True)
        remove.setToolTip(_tr("Remove this widget; the filter it set stays until you change it"))
        remove.clicked.connect(lambda: self.remove_requested.emit(self.widget["id"]))
        head.addWidget(self.title)
        head.addWidget(self.layer, 1)
        self.value: Optional[QLabel] = None
        if widget["kind"] not in (RANGE, VALUES, CHART):  # a number fits on the line of its title
            self.value = QLabel("—", self)
            self.value.setObjectName("label_agent_widget_value")
            head.addWidget(self.value)
        head.addWidget(remove)
        layout.addLayout(head)
        self.error = QLabel(self)
        self.error.setObjectName("label_agent_widget_error")
        self.error.setWordWrap(True)
        self.error.setTextFormat(Qt.TextFormat.PlainText)
        self.error.hide()
        self.low: Optional[QDoubleSpinBox] = None
        self.high: Optional[QDoubleSpinBox] = None
        self.values: Optional[QListWidget] = None
        self.chart: Optional[ChartView] = None
        if widget["kind"] == CHART:
            self.chart = ChartView(widget["mode"], self)
            self.chart.setObjectName("widget_agent_chart")
            layout.addWidget(self.chart)
        elif widget["kind"] == RANGE:
            layout.addLayout(self._build_range())
        elif widget["kind"] == VALUES:
            layout.addWidget(self._build_values())
        layout.addWidget(self.error)

    def _spin(self) -> QDoubleSpinBox:
        widget = self.widget
        box = QDoubleSpinBox(self)
        box.setDecimals(0 if widget.get("integer") else 2)
        box.setRange(widget["minimum"], widget["maximum"])
        box.setSingleStep(max((widget["maximum"] - widget["minimum"]) / 100.0, 1.0 if widget.get("integer") else 0.01))
        box.setKeyboardTracking(False)
        box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return box

    def _build_range(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self.low, self.high = self._spin(), self._spin()
        self.low.setObjectName("doubleSpinBox_agent_widget_low")
        self.high.setObjectName("doubleSpinBox_agent_widget_high")
        self.low.setValue(self.widget["low"])
        self.high.setValue(self.widget["high"])
        self.low.valueChanged.connect(self._on_range)
        self.high.valueChanged.connect(self._on_range)
        row.addWidget(QLabel(_tr("from"), self))
        row.addWidget(self.low, 1)
        row.addWidget(QLabel(_tr("to"), self))
        row.addWidget(self.high, 1)
        return row

    def _build_values(self) -> QWidget:
        box = QWidget(self)
        column = QVBoxLayout(box)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(2)
        self.values = QListWidget(box)
        self.values.setObjectName("listWidget_agent_widget_values")
        self.values.setMaximumHeight(VALUES_MAX_HEIGHT)
        chosen = self.widget["chosen"]
        for value in self.widget["values"]:
            item = QListWidgetItem(value_text(value), self.values)
            item.setData(_VALUE_ROLE, value)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if value in chosen else Qt.CheckState.Unchecked)
        self.values.itemChanged.connect(self._on_values)
        buttons = QHBoxLayout()
        for text, state in ((_tr("All"), Qt.CheckState.Checked), (_tr("None"), Qt.CheckState.Unchecked)):
            button = QPushButton(text, box)
            button.setObjectName("pushButton_agent_widget_tick")
            button.setFlat(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, state=state: self._tick_all(state))
            buttons.addWidget(button)
        buttons.addStretch(1)
        column.addWidget(self.values)
        column.addLayout(buttons)
        return box

    def _tick_all(self, state) -> None:
        self.values.blockSignals(True)
        for row in range(self.values.count()):
            self.values.item(row).setCheckState(state)
        self.values.blockSignals(False)
        self._on_values()

    def _on_range(self, _value: float = 0.0) -> None:
        low, high = self.low.value(), self.high.value()
        if low > high:  # the bound moved past the other one drags it along
            other = self.high if self.sender() is self.low else self.low
            other.blockSignals(True)
            other.setValue(low if other is self.high else high)
            other.blockSignals(False)
        self.widget.update(low=self.low.value(), high=self.high.value())
        self._timer.start()

    def _on_values(self, _item=None) -> None:
        self.widget["chosen"] = [self.values.item(row).data(_VALUE_ROLE) for row in range(self.values.count())
                                 if self.values.item(row).checkState() == Qt.CheckState.Checked]
        self._timer.start()

    def _emit(self) -> None:
        self.changed.emit(dict(self.widget))

    def flush(self) -> None:
        """Apply now what waits for the pause (tests, and a widget about to go)."""
        if self._timer.isActive():
            self._timer.stop()
            self._emit()

    def set_value(self, text: str) -> None:
        if self.value is not None:
            self.value.setText(text)

    def set_bars(self, bars) -> None:
        if self.chart is not None:
            self.chart.set_bars(bars)

    def set_error(self, text: str) -> None:
        self.error.setText(text)
        self.error.setVisible(bool(text))


class WidgetsStrip(QFrame):
    """The cards of the widgets of the project; hidden when there is none."""

    changed = pyqtSignal(object)
    remove_requested = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("frame_agent_widgets")
        self.cards: Dict[str, WidgetCard] = {}
        self._shape = ()
        self._area = QScrollArea(self)
        self._area.setWidgetResizable(True)
        self._area.setFrameShape(QFrame.Shape.NoFrame)
        self._area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._inner = QWidget(self._area)
        self._column = QVBoxLayout(self._inner)
        self._column.setContentsMargins(0, 0, 0, 0)
        self._column.setSpacing(4)
        self._column.addStretch(1)
        self._area.setWidget(self._inner)
        self._area.setMaximumHeight(STRIP_MAX_HEIGHT)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._area)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.hide()

    def set_widgets(self, widgets: Sequence[Dict[str, Any]]) -> None:
        """Draw ``widgets``; a card the user is moving is not drawn again when only its state changed."""
        shape = tuple((widget["id"], widget["kind"], widget["title"], widget["field"], widget["layer_id"],
                       tuple(map(str, widget.get("values", ()))), widget.get("minimum"), widget.get("maximum"))
                      for widget in widgets)
        states = {widget["id"]: widget for widget in widgets}
        if shape == self._shape and all(card.widget == states.get(key) for key, card in self.cards.items()):
            return
        for card in self.cards.values():
            card.deleteLater()
        self.cards = {}
        for widget in widgets:
            card = WidgetCard(widget, self._inner)
            card.changed.connect(self.changed)
            card.remove_requested.connect(self.remove_requested)
            self._column.insertWidget(self._column.count() - 1, card)
            self.cards[widget["id"]] = card
        self._shape = shape
        self.setVisible(bool(widgets))
        self._fit()
        self.refresh_look()

    def _fit(self) -> None:
        self._inner.adjustSize()
        self._area.setMinimumHeight(min(self._inner.sizeHint().height(), STRIP_MAX_HEIGHT))

    def set_value(self, widget_id: str, text: str) -> None:
        card = self.cards.get(widget_id)
        if card is not None:
            card.set_value(text)

    def set_bars(self, widget_id: str, bars) -> None:
        card = self.cards.get(widget_id)
        if card is not None:
            card.set_bars(bars)
            self._fit()

    def set_error(self, widget_id: str, text: str) -> None:
        card = self.cards.get(widget_id)
        if card is not None:
            card.set_error(text)

    def refresh_look(self) -> None:
        palette = tokens(plugin_is_dark(self))
        for card in self.cards.values():
            if card.chart is not None:
                card.chart.accent = QColor(palette['fm_accent'])
                card.chart.muted = QColor(palette['fm_text_muted'])
                card.chart.update()
        self.setStyleSheet(
            f"QFrame#frame_agent_widget {{ border: 1px solid {palette['fm_group_border']}; border-radius: 6px; }}"
            "QLabel#label_agent_widget_title { font-weight: 600; }"
            f"QLabel#label_agent_widget_layer {{ color: {palette['fm_text_muted']}; font-size: 11px; }}"
            "QLabel#label_agent_widget_value { font-size: 15px; font-weight: 600; }"
            "QLabel#label_agent_widget_error { color: #c0392b; font-size: 11px; }"
            f"QPushButton#pushButton_agent_widget_tick {{ color: {palette['fm_accent']}; border: none; padding: 0 6px;"
            " font-size: 11px; }")
