# -*- coding: utf-8 -*-
"""The Compare button of the action bar: the map before the operation Undo would undo, left of a line.

It reads the history Undo reads, chosen the same way (``FilterMateApp.update_undo_redo_buttons``): the turns of the
agent while AGENT is open, the history of the raster / point cloud source while one is current, the vector filters
of the dock otherwise. ``adapters/qgis/compare_swipe.py`` draws.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from qgis.core import QgsProject
from qgis.PyQt.QtCore import QCoreApplication, QObject, QPointF, QRectF, QSize, Qt
from qgis.PyQt.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from qgis.PyQt.QtWidgets import QPushButton

from ...adapters.qgis.compare_swipe import CompareSession
from ...core.domain.compare_states import BeforeState, from_cross_operation, from_history_entry

logger = logging.getLogger("FilterMate.compare")

BUTTON_NAME = "pushButton_action_compare"


def _tr(text: str) -> str:
    return QCoreApplication.translate("FilterMateDockWidget", text)


def compare_icon(size: int = 32, colour: QColor = QColor(90, 90, 90)) -> QIcon:
    """Half a frame filled, a line between the halves: the map before, the line, the map after."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    margin = size * 0.16
    frame = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
    fill = QColor(colour)
    fill.setAlpha(110)
    painter.fillRect(QRectF(frame.left(), frame.top(), frame.width() / 2, frame.height()), fill)
    painter.setPen(QPen(colour, max(1.0, size / 16)))
    painter.drawRect(frame)
    painter.setPen(QPen(colour, max(1.5, size / 11)))
    middle = frame.center().x()
    painter.drawLine(QPointF(middle, margin * 0.4), QPointF(middle, size - margin * 0.4))
    painter.end()
    return QIcon(pixmap)


def _layout_holding(layout, widget):
    """The layout that holds ``widget``, searched from ``layout`` down."""
    if layout is None:
        return None
    if layout.indexOf(widget) >= 0:
        return layout
    for index in range(layout.count()):
        child = layout.itemAt(index).layout()
        found = _layout_holding(child, widget)
        if found is not None:
            return found
    return None


class CompareController(QObject):
    """One button and the comparison it starts and stops."""

    def __init__(self, dockwidget, integration=None) -> None:
        super().__init__(dockwidget)
        self._dock = dockwidget
        self._integration = integration
        self.session: Optional[CompareSession] = None
        self.button = self._make_button()
        signal = getattr(dockwidget, "undoRedoStateRequested", None)
        if signal is not None:
            signal.connect(self.refresh)

    # --- the button --------------------------------------------------------------

    def _make_button(self) -> Optional[QPushButton]:
        redo = getattr(self._dock, "pushButton_action_redo_filter", None)
        if redo is None:
            return None
        parent = redo.parentWidget()
        layout = _layout_holding(parent.layout() if parent is not None else None, redo)
        if layout is None:
            return None
        button = QPushButton(parent)
        button.setObjectName(BUTTON_NAME)
        button.setCheckable(True)
        button.setFlat(redo.isFlat())
        button.setIcon(compare_icon())
        size = redo.iconSize()
        button.setIconSize(size if size.isValid() and size.width() > 0 else QSize(24, 24))
        button.setSizePolicy(redo.sizePolicy())
        button.setMinimumSize(redo.minimumSize())
        button.setMaximumSize(redo.maximumSize())
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setToolTip(_tr("Compare: the map before the last filter left of the line, as it is on its right; "
                              "the line follows the mouse"))
        button.setAccessibleName(_tr("Compare before and after the last filter"))
        layout.insertWidget(layout.indexOf(redo) + 1, button)
        button.toggled.connect(self._on_toggled)
        setattr(self._dock, BUTTON_NAME, button)
        return button

    # --- which history -----------------------------------------------------------

    def before_states(self) -> List[BeforeState]:
        """The states before the operation Undo would undo now, from the history it reads."""
        dock = self._dock
        agent_focus = getattr(dock, "agent_has_focus", None)
        if callable(agent_focus) and agent_focus():
            from ...adapters.agent.turn_checkpoint import HISTORY_KEY
            from ...adapters.public_api.operations import _api_service
            stack = _api_service().history.undo_stack(HISTORY_KEY)
            return from_cross_operation(stack[-1]) if stack else []
        coverage = getattr(self._integration, "coverage_controller", None) if self._integration is not None else None
        layer = getattr(coverage, "active_layer", None) if coverage is not None else None
        if layer is not None:
            try:
                operation = coverage.service.history.peek_undo(layer.id())
            except (AttributeError, RuntimeError):
                operation = None
            return from_cross_operation(operation) if operation is not None else []
        app = getattr(dock, "app", None)
        history = getattr(app, "history_manager", None) if app is not None else None
        entry = history.peek_undo() if history is not None else None
        states = from_history_entry(entry) if entry is not None else []
        # A vector source also filters raster and point cloud targets: their former sources are in the history of
        # the cross filters, keyed by the source layer.
        current = getattr(dock, "current_layer", None)
        if coverage is not None and current is not None:
            try:
                operation = coverage.service.history.peek_undo(current.id())
            except (AttributeError, RuntimeError):
                operation = None
            if operation is not None:
                known = {state.layer_id for state in states}
                states += [state for state in from_cross_operation(operation) if state.layer_id not in known]
        return states

    def _canvas(self):
        iface = getattr(self._dock, "iface", None)
        if iface is None:
            from qgis.utils import iface
        return iface.mapCanvas() if iface is not None else None

    # --- the comparison ----------------------------------------------------------

    def _on_toggled(self, on: bool) -> None:
        if on:
            self.start()
        else:
            self.stop()

    def start(self) -> int:
        """Compare now; the number of layers drawn as they were (0: nothing to compare, the button goes up)."""
        canvas = self._canvas()
        count = 0
        if canvas is not None:
            try:
                states = self.before_states()
            except Exception:  # a history that cannot be read compares nothing; the map is left alone
                logger.debug("Compare: history not read", exc_info=True)
                states = []
            if self.session is None:
                self.session = CompareSession(canvas, self)
            count = self.session.start(states, QgsProject.instance().mapLayers()) if states else 0
        if not count:
            self._say(_tr("Nothing to compare: no filter to undo here."))
            self._set_checked(False)
        return count

    def refresh(self) -> None:
        """The history Undo reads changed (a filter, an undo, AGENT opened): compare against the new state."""
        if self.session is not None and self.session.active:
            self.start()

    def stop(self) -> None:
        if self.session is not None:
            self.session.stop()
        self._set_checked(False)

    def teardown(self) -> None:
        self.stop()
        signal = getattr(self._dock, "undoRedoStateRequested", None)
        if signal is not None:
            try:
                signal.disconnect(self.refresh)
            except (TypeError, RuntimeError):
                pass

    def _set_checked(self, on: bool) -> None:
        if self.button is not None and self.button.isChecked() != on:
            self.button.blockSignals(True)
            self.button.setChecked(on)
            self.button.blockSignals(False)

    def _say(self, text: str) -> None:
        try:
            from ...infrastructure.feedback import show_info
            show_info(text)
        except Exception:
            logger.debug("Compare: %s", text)
