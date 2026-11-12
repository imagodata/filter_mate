# -*- coding: utf-8 -*-
"""The Compare button of the action bar: the map before the operation Undo would undo, left of a line.

It reads the history Undo reads, chosen the same way (``FilterMateApp.update_undo_redo_buttons``): the turns of the
agent while AGENT is open, the history of the raster / point cloud source while one is current, the vector filters
of the dock otherwise, restricted to the layers Undo restores. It is available when Undo is, and ends with any
operation of the action bar, a change of the current layer or of project: what it shows is the state Undo would
bring back now. ``adapters/qgis/compare_swipe.py`` draws.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from qgis.core import QgsProject
from qgis.PyQt.QtCore import QCoreApplication, QEvent, QObject, QPointF, QRectF, QSize, Qt
from qgis.PyQt.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from qgis.PyQt.QtWidgets import QPushButton

from ...adapters.qgis.compare_swipe import CompareSession
from ...core.domain.compare_states import BeforeState, from_cross_operation, from_history_entry

logger = logging.getLogger("FilterMate.compare")

BUTTON_NAME = "pushButton_action_compare"
# Operations of the action bar: the state before changes with them, the comparison ends.
ENDING_BUTTONS = ("pushButton_action_filter", "pushButton_action_undo_filter", "pushButton_action_redo_filter",
                  "pushButton_action_unfilter")


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
        self._undo = getattr(dockwidget, "pushButton_action_undo_filter", None)
        self._connections = []
        if self.button is None:
            return
        if self._undo is not None:  # available when Undo is
            self.button.setEnabled(self._undo.isEnabled())
            self._undo.installEventFilter(self)
        self._connect(getattr(dockwidget, "undoRedoStateRequested", None), self.refresh)
        self._connect(getattr(dockwidget, "currentLayerChanged", None), self.stop)
        for name in ENDING_BUTTONS:
            button = getattr(dockwidget, name, None)
            self._connect(button.clicked if button is not None else None, self.stop)
        self._connect(QgsProject.instance().cleared, self.stop)

    def _connect(self, signal, slot) -> None:
        if signal is not None:
            signal.connect(slot)
            self._connections.append((signal, slot))

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
        index = layout.indexOf(redo)
        layout.insertWidget(index + 1, button, 0, layout.itemAt(index).alignment())
        button.toggled.connect(self._on_toggled)
        setattr(self._dock, BUTTON_NAME, button)
        return button

    def eventFilter(self, watched, event):  # noqa: N802 - Qt override
        if watched is self._undo and event.type() == QEvent.Type.EnabledChange and self.button is not None:
            try:
                enabled = self._undo.isEnabled()
                self.button.setEnabled(enabled)
                if not enabled:
                    self.stop()
            except RuntimeError:  # the dock is being deleted
                pass
        return False

    # --- which history -----------------------------------------------------------

    def before_states(self) -> List[BeforeState]:
        """The states Undo would bring back now, from the history it reads, for the layers it restores."""
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
        current = getattr(dock, "current_layer", None)
        if current is None:
            return []
        # The app is ``filter_mate_app`` (the initializer of the plugin), ``app`` on the former path.
        app = getattr(dock, "filter_mate_app", None) or getattr(dock, "app", None)
        history = getattr(app, "history_manager", None) if app is not None else None
        entry = history.peek_undo() if history is not None else None
        states = []
        if entry is not None:
            # Undo restores the source, and the layers to filter when their button is on (_handle_undo_redo).
            restored = {current.id()}
            button = getattr(dock, "pushButton_checkable_filtering_layers_to_filter", None)
            if button is not None and button.isChecked():
                restored.update(dock.get_layers_to_filter() or [])
            states = [state for state in from_history_entry(entry) if state.layer_id in restored]
        # A vector source also filters raster and point cloud targets: Undo replays that cross operation only when
        # it is the one the last run recorded (CoverageModeController, task 'undo').
        if coverage is not None:
            try:
                runs = (getattr(coverage, "_linked_runs", None) or {}).get(current.id()) or []
                operation = coverage.service.history.peek_undo(current.id())
                linked = bool(runs) and coverage._run_is_next(runs[-1], operation)
            except (AttributeError, RuntimeError):
                linked = False
            if linked:
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
                self.session.ended.connect(lambda: self._set_checked(False))
            count = self.session.start(states, QgsProject.instance().mapLayers())
        if not count:
            self._say(_tr("Nothing to compare: no filter to undo here."))
            self._set_checked(False)
        return count

    def refresh(self) -> None:
        """AGENT opened or closed, a turn of the agent done or undone: compare against what Undo reads now."""
        if self.session is not None and self.session.active:
            self.start()

    def stop(self, *_args) -> None:
        if self.session is not None:
            self.session.stop()
        self._set_checked(False)

    def teardown(self) -> None:
        for signal, slot in self._connections:
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
        self._connections = []
        try:
            if self._undo is not None:
                self._undo.removeEventFilter(self)
        except RuntimeError:
            pass
        if self.session is not None:
            self.session.close()
        self._set_checked(False)

    def _set_checked(self, on: bool) -> None:
        try:
            if self.button is not None and self.button.isChecked() != on:
                self.button.blockSignals(True)
                self.button.setChecked(on)
                self.button.blockSignals(False)
        except RuntimeError:  # the button was deleted with the dock
            pass

    def _say(self, text: str) -> None:
        try:
            from ...infrastructure.feedback import show_info
            show_info(text)
        except Exception:
            logger.debug("Compare: %s", text)
